"""Local HTTP API server for PHP → daemon communication.

Listens on 127.0.0.1 only, protected by a local_secret shared with the PHP plugin.
"""

import asyncio
import logging
import socket
import ssl
import time
import uuid
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from aiohttp import web

from .mqtt_client import MqttBridge
from models.topology import TopologySnapshot, assess_all
from models.mapping import MappingResult, PublicationDecision
from mapping.light import LightMapper
from mapping.cover import CoverMapper
from mapping.switch import SwitchMapper
from mapping.sensor import SensorMapper
from discovery.publisher import DiscoveryPublisher

_LOGGER = logging.getLogger(__name__)

_VERSION = "0.2.0"


def _check_secret(request: web.Request, local_secret: str) -> bool:
    """Validate the local_secret from request header."""
    provided = request.headers.get("X-Local-Secret", "")
    if not provided or not local_secret:
        return False
    return provided == local_secret


def _resolve_state_topic(mapping: MappingResult) -> str:
    """Resolve runtime state topic for a published mapping.

    The result is stored in the runtime publication registry and then reused by
    incremental sync as source of truth.
    """
    if mapping.ha_entity_type in ("sensor", "binary_sensor"):
        info_cmd = next((cmd for cmd in mapping.commands.values() if getattr(cmd, "type", "info") == "info"), None)
        cmd = info_cmd or next(iter(mapping.commands.values()), None)
        if cmd is None:
            return ""
        return f"jeedom2ha/cmd/{cmd.id}/state"

    if mapping.ha_entity_type in ("light", "cover", "switch"):
        return f"jeedom2ha/{mapping.jeedom_eq_id}/state"

    return ""


async def _handle_system_status(request: web.Request) -> web.Response:
    """Handle GET /system/status — liveness probe."""
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response(
            {"status": "error", "message": "Unauthorized"},
            status=401,
        )

    uptime = time.monotonic() - request.app["start_time"]

    mqtt_bridge = request.app.get("mqtt_bridge")
    mqtt_section = {
        "connected": mqtt_bridge.is_connected if mqtt_bridge else False,
        "state": mqtt_bridge.state if mqtt_bridge else "disconnected",
        "broker": mqtt_bridge.broker_info if mqtt_bridge else "",
    }

    payload = {
        "action": "system.status",
        "status": "ok",
        "payload": {
            "version": _VERSION,
            "uptime": round(uptime, 2),
            "mqtt": mqtt_section,
        },
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return web.json_response(payload)


def _sync_mqtt_connect(host, port, user, password, tls_enabled, tls_verify) -> dict:
    """Synchronous MQTT connection test. Returns {ok, error_code?, message}.

    Designed to be called via run_in_executor from an async handler.
    Never logs passwords — errors are categorized for user display.
    """
    # V1 — CA système uniquement (pas de CA custom ni mTLS)
    # Unique client_id per test to avoid broker disconnecting a previous test session
    # with the same client_id (would cause ConnectionResetError on rapid successive tests)
    client_id = f"jeedom2ha_test_{uuid.uuid4().hex[:8]}"
    try:
        # paho-mqtt 2.0+
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id=client_id,
            clean_session=True,
        )
    except AttributeError:
        # paho-mqtt < 2.0
        client = mqtt.Client(client_id=client_id, clean_session=True)
    connect_result = {"rc": None}

    def on_connect(_client, _userdata, _flags, rc):
        connect_result["rc"] = rc

    client.on_connect = on_connect

    try:
        if tls_enabled:
            ctx = ssl.create_default_context()
            if not tls_verify:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            client.tls_set_context(ctx)
        if user:
            _LOGGER.debug("[MQTT] username_pw_set called for user=%s", user)
            client.username_pw_set(username=user, password=password)

        client.connect(host, port, keepalive=10)
        client.loop_start()

        # Wait for on_connect callback (max 5s)
        deadline = time.monotonic() + 5.0
        while connect_result["rc"] is None and time.monotonic() < deadline:
            time.sleep(0.1)

        client.loop_stop()
        try:
            client.disconnect()
        except Exception:
            pass

        if connect_result["rc"] is None:
            return {
                "ok": False,
                "error_code": "timeout",
                "message": "Délai dépassé : le broker ne répond pas",
            }
        if connect_result["rc"] == 0:
            return {"ok": True, "message": "Connexion réussie"}
        if connect_result["rc"] == 5:
            return {
                "ok": False,
                "error_code": "auth_failed",
                "message": "Authentification refusée : vérifiez identifiant et mot de passe",
            }
        return {
            "ok": False,
            "error_code": "unknown_error",
            "message": f"Broker refusé (code {connect_result['rc']})",
        }
    except (socket.gaierror, socket.herror):
        return {
            "ok": False,
            "error_code": "host_unreachable",
            "message": "Hôte introuvable : vérifiez l'adresse du broker",
        }
    except ConnectionRefusedError:
        return {
            "ok": False,
            "error_code": "port_refused",
            "message": "Port refusé : le broker n'écoute pas sur ce port",
        }
    except (ssl.SSLError, ssl.CertificateError):
        return {
            "ok": False,
            "error_code": "tls_error",
            "message": "Erreur TLS : certificat invalide ou protocole non supporté",
        }
    except (socket.timeout, TimeoutError):
        return {
            "ok": False,
            "error_code": "timeout",
            "message": "Délai dépassé : le broker ne répond pas",
        }
    except Exception as e:
        # Log the exception type only — never log credentials that may appear in str(e)
        _LOGGER.warning("[MQTT] Unexpected error during connection test: %s", type(e).__name__)
        return {
            "ok": False,
            "error_code": "unknown_error",
            "message": f"Erreur inattendue ({type(e).__name__}) — consultez les logs du démon",
        }


async def _handle_mqtt_test(request: web.Request) -> web.Response:
    """Handle POST /action/mqtt_test — one-shot MQTT connection test."""
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response(
            {"status": "error", "message": "Unauthorized"},
            status=401,
        )

    data = await request.json()
    payload = data.get("payload", {})
    host = payload.get("host", "")
    port_raw = payload.get("port", 1883)

    # Validation d'entrée explicite
    if not host:
        return web.json_response({
            "action": "mqtt.test",
            "status": "error",
            "error_code": "missing_host",
            "message": "Hôte MQTT manquant",
        })
    try:
        port = int(port_raw)
        if not (1 <= port <= 65535):
            raise ValueError()
    except (ValueError, TypeError):
        return web.json_response({
            "action": "mqtt.test",
            "status": "error",
            "error_code": "invalid_port",
            "message": f"Port MQTT invalide : {port_raw}",
        })

    # Support "username" (direct curl / docs format) and "user" (PHP callDaemon format)
    # "username" takes priority when both are present
    user = payload.get("username") or payload.get("user", "")
    password = payload.get("password", "")
    tls_enabled = bool(payload.get("tls", False))
    tls_verify = bool(payload.get("tls_verify", True))

    _LOGGER.info("[MQTT] Testing connection to %s:%s (TLS: %s)", host, port, tls_enabled)
    _LOGGER.debug(
        "[MQTT] Test params — username=%s password_present=%s tls=%s tls_verify=%s",
        user or "(anonymous)", bool(password), tls_enabled, tls_verify,
    )

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        _sync_mqtt_connect,
        host,
        port,
        user,
        password,
        tls_enabled,
        tls_verify,
    )

    status = "ok" if result["ok"] else "error"
    payload = {
        "action": "mqtt.test",
        "status": status,
        "payload": {"connected": result["ok"]},
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error_code": result.get("error_code"),
        "message": result["message"],
    }
    if result["ok"]:
        _LOGGER.info("[MQTT] Connection test succeeded")
    else:
        _LOGGER.warning("[MQTT] Connection test failed: %s", result["message"])

    return web.json_response(payload)


async def _handle_mqtt_connect(request: web.Request) -> web.Response:
    """Handle POST /action/mqtt_connect — initiate persistent MQTT connection."""
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response(
            {"status": "error", "message": "Unauthorized"},
            status=401,
        )

    data = await request.json()
    # Envelope format: params may be under "payload" key (callDaemon wrapping)
    params = data.get("payload", data)
    host = params.get("host", "")
    if not host:
        return web.json_response({
            "action": "mqtt.connect",
            "status": "error",
            "message": "Paramètre 'host' requis",
        })

    # Stop existing bridge if any (config change without daemon restart)
    bridge = request.app["mqtt_bridge"]
    await bridge.stop()

    # Start the persistent bridge with new params
    await bridge.start(params)

    return web.json_response({
        "action": "mqtt.connect",
        "status": "ok",
        "payload": {"state": bridge.state, "broker": bridge.broker_info},
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def _handle_action_sync(request: web.Request) -> web.Response:
    """Handle POST /action/sync — synchronize Jeedom topology, assess eligibility, map and publish."""
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response(
            {"status": "error", "message": "Unauthorized"},
            status=401,
        )

    data = await request.json()
    payload = data.get("payload", {})
    
    _LOGGER.info("[TOPOLOGY] Received sync request")
    
    # 1. Normalize and store snapshot
    snapshot = TopologySnapshot.from_jeedom_payload(payload)
    request.app["topology"] = snapshot
    
    # 2. Assess eligibility
    eligibility = assess_all(snapshot)
    request.app["eligibility"] = eligibility
    
    # 3. Build eligibility summary
    eligible_count = sum(1 for res in eligibility.values() if res.is_eligible)
    ineligible_count = len(eligibility) - eligible_count
    
    breakdown = {}
    for res in eligibility.values():
        if not res.is_eligible:
            breakdown[res.reason_code] = breakdown.get(res.reason_code, 0) + 1
            
    total_cmds = sum(len(eq.cmds) for eq in snapshot.eq_logics.values())
    
    _LOGGER.info(
        "[TOPOLOGY] Sync complete: %d eligible, %d ineligible",
        eligible_count, ineligible_count
    )
    
    # 4. Nettoyage (RAM + MQTT) des anciens équipements disparus ou devenus inéligibles
    anciens_uids = set(request.app["mappings"].keys())
    nouveaux_uids = set()

    # 5. Map eligible eqLogics to HA entities (Stories 2.2 + 2.3 + 2.4 + 2.5)
    light_mapper = LightMapper()
    cover_mapper = CoverMapper()
    switch_mapper = SwitchMapper()
    sensor_mapper = SensorMapper()
    mappings = {}       # Dict[str, MappingResult]
    publications = {}   # Dict[str, PublicationDecision]
    
    mapping_counters = {}
    for cat in ["lights", "covers", "switches", "sensors", "binary_sensors"]:
        for conf in ["sure", "probable", "ambiguous", "published", "skipped"]:
            mapping_counters[f"{cat}_{conf}"] = 0

    entity_to_counter_group = {
        "light": "lights",
        "cover": "covers",
        "switch": "switches",
        "sensor": "sensors",
        "binary_sensor": "binary_sensors",
    }

    def _counter_group(entity_type: str) -> str:
        return entity_to_counter_group.get(entity_type, f"{entity_type}s")

    def _inc_counter(entity_type: str, status: str) -> None:
        group = _counter_group(entity_type)
        key = f"{group}_{status}"
        mapping_counters[key] = mapping_counters.get(key, 0) + 1
    
    mqtt_bridge = request.app.get("mqtt_bridge")
    publisher = DiscoveryPublisher(mqtt_bridge) if mqtt_bridge else None
    
    async def _process_mapping(mapping: MappingResult, mapper):
        if mapping.confidence == "sure":
            _inc_counter(mapping.ha_entity_type, "sure")
        elif mapping.confidence == "probable":
            _inc_counter(mapping.ha_entity_type, "probable")
        elif mapping.confidence == "ambiguous":
            _inc_counter(mapping.ha_entity_type, "ambiguous")
        else:
            _inc_counter(mapping.ha_entity_type, mapping.confidence)

        decision = mapper.decide_publication(mapping)
        runtime_state_topic = _resolve_state_topic(mapping)
        norm_val = None
        cmd = None
        config_published = False

        # Story 2.5 strictness: invalid initial state blocks BOTH discovery config and state
        # publication, with explicit diagnostic reason.
        if decision.should_publish and mapping.ha_entity_type in ("sensor", "binary_sensor"):
            cmd = next(iter(mapping.commands.values()))
            raw_val = cmd.current_value

            is_valid = True
            if mapping.ha_entity_type == "sensor":
                try:
                    if raw_val is not None:
                        norm_val = float(raw_val)
                except (ValueError, TypeError):
                    is_valid = False
            else:  # binary_sensor
                norm_val = sensor_mapper.normalize_binary_value(raw_val)
                if norm_val is None and raw_val is not None:
                    is_valid = False

            if not is_valid:
                mapping.reason_code = "invalid_initial_state"
                reason_details = dict(mapping.reason_details or {})
                reason_details["invalid_initial_state"] = {
                    "ha_entity_type": mapping.ha_entity_type,
                    "cmd_id": cmd.id,
                    "raw_value": raw_val,
                }
                mapping.reason_details = reason_details
                decision = PublicationDecision(
                    should_publish=False,
                    reason="invalid_initial_state",
                    mapping_result=mapping,
                )
                _LOGGER.warning(
                    "[MAPPING] Strict rejection of %s due to invalid initial state: %s",
                    mapping.ha_unique_id,
                    raw_val,
                )

        if decision.should_publish:
            if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                # Dispatch publisher call
                if mapping.ha_entity_type == "light":
                    config_published = await publisher.publish_light(mapping, snapshot)
                elif mapping.ha_entity_type == "cover":
                    config_published = await publisher.publish_cover(mapping, snapshot)
                elif mapping.ha_entity_type == "switch":
                    config_published = await publisher.publish_switch(mapping, snapshot)
                elif mapping.ha_entity_type == "sensor":
                    config_published = await publisher.publish_sensor(mapping, snapshot)
                elif mapping.ha_entity_type == "binary_sensor":
                    config_published = await publisher.publish_binary_sensor(mapping, snapshot)

                # AC 2.8 strict order: state can be published only after successful config publish.
                if (
                    mapping.ha_entity_type in ("sensor", "binary_sensor")
                    and norm_val is not None
                    and config_published
                    and cmd is not None
                ):
                    state_topic = f"jeedom2ha/cmd/{cmd.id}/state"
                    mqtt_bridge.publish_message(state_topic, str(norm_val), qos=1, retain=True)
                elif mapping.ha_entity_type in ("sensor", "binary_sensor") and norm_val is not None and not config_published:
                    _LOGGER.warning(
                        "[MAPPING] Skipping initial state for %s because discovery config publish failed",
                        mapping.ha_unique_id,
                    )
            else:
                _LOGGER.warning(
                    "[MAPPING] Discovery publish unavailable for %s (bridge missing/disconnected)",
                    mapping.ha_unique_id,
                )

        if decision.should_publish and not config_published:
            decision = PublicationDecision(
                should_publish=False,
                reason="discovery_publish_failed",
                mapping_result=mapping,
            )
            _LOGGER.warning(
                "[MAPPING] Runtime gating disabled for %s because discovery publish did not succeed",
                mapping.ha_unique_id,
            )

        decision.state_topic = runtime_state_topic
        decision.active_or_alive = bool(decision.should_publish and config_published)

        nouveaux_uids.add(mapping.ha_unique_id)
        mappings[mapping.ha_unique_id] = mapping
        publications[mapping.ha_unique_id] = decision

        if decision.active_or_alive:
            _inc_counter(mapping.ha_entity_type, "published")
        else:
            _inc_counter(mapping.ha_entity_type, "skipped")


    for eq_id, result in eligibility.items():
        if not result.is_eligible:
            continue
        
        eq = snapshot.eq_logics.get(eq_id)
        if not eq:
            continue
        
        # Actuators (Light, Cover, Switch) -> mutually exclusive
        actuator_mapping = light_mapper.map(eq, snapshot)
        used_mapper = light_mapper
        if not actuator_mapping:
            actuator_mapping = cover_mapper.map(eq, snapshot)
            used_mapper = cover_mapper
        if not actuator_mapping:
            actuator_mapping = switch_mapper.map(eq, snapshot)
            used_mapper = switch_mapper
        
        if actuator_mapping:
            await _process_mapping(actuator_mapping, used_mapper)
            
        # Sensors -> multiple valid sensors per eqLogic
        sensor_mappings = sensor_mapper.map(eq, snapshot)
        for s_mapping in sensor_mappings:
            await _process_mapping(s_mapping, sensor_mapper)

            
    # Purge des équipements et capteurs qui ne sont plus remontés ou plus éligibles
    uids_supprimes = anciens_uids - nouveaux_uids
    for old_uid in uids_supprimes:
        # Si c'était publié avant, on l'unpublish
        old_decision = request.app["publications"].get(old_uid)
        if old_decision and old_decision.should_publish:
            entity_type = old_decision.mapping_result.ha_entity_type
            if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                if entity_type in ("sensor", "binary_sensor"):
                    await publisher.unpublish_entity(old_uid, entity_type=entity_type)
                else:
                    await publisher.unpublish_by_eq_id(
                        old_decision.mapping_result.jeedom_eq_id,
                        entity_type=entity_type,
                    )
                _LOGGER.info("[MAPPING] entity %s est devenu inéligible ou supprimé → MQTT unpublish effectif", old_uid)
                
        # Nettoyage de la RAM pour éviter les données obsolètes (fuite pour Diagnostics)
        request.app["mappings"].pop(old_uid, None)
        request.app["publications"].pop(old_uid, None)
    
    # Store detailed decisions in RAM for Epic 4 (diagnostic)
    request.app["mappings"].update(mappings)
    request.app["publications"].update(publications)
    
    _LOGGER.info(
        "[MAPPING] Summary: lights(S:%d P:%d A:%d | pub:%d skip:%d) "
        "covers(S:%d P:%d A:%d | pub:%d skip:%d) "
        "switches(S:%d P:%d A:%d | pub:%d skip:%d) "
        "sensors(S:%d P:%d A:%d | pub:%d skip:%d)",
        mapping_counters["lights_sure"], mapping_counters["lights_probable"], mapping_counters["lights_ambiguous"], mapping_counters["lights_published"], mapping_counters["lights_skipped"],
        mapping_counters["covers_sure"], mapping_counters["covers_probable"], mapping_counters["covers_ambiguous"], mapping_counters["covers_published"], mapping_counters["covers_skipped"],
        mapping_counters["switches_sure"], mapping_counters["switches_probable"], mapping_counters["switches_ambiguous"], mapping_counters["switches_published"], mapping_counters["switches_skipped"],
        mapping_counters["sensors_sure"] + mapping_counters.get("binary_sensors_sure", 0), 
        mapping_counters["sensors_probable"] + mapping_counters.get("binary_sensors_probable", 0), 
        mapping_counters["sensors_ambiguous"] + mapping_counters.get("binary_sensors_ambiguous", 0), 
        mapping_counters["sensors_published"] + mapping_counters.get("binary_sensors_published", 0), 
        mapping_counters["sensors_skipped"] + mapping_counters.get("binary_sensors_skipped", 0),
    )
    
    summary = {
        "total_objects": len(snapshot.objects),
        "total_eq_logics": len(snapshot.eq_logics),
        "total_cmds": total_cmds,
        "eligible_count": eligible_count,
        "ineligible_count": ineligible_count,
        "ineligible_breakdown": breakdown,
        "mapping_summary": mapping_counters,
    }
    
    return web.json_response({
        "action": "sync",
        "status": "ok",
        "payload": summary,
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def create_app(local_secret: str) -> web.Application:
    """Create the aiohttp application with routes and auth context."""
    app = web.Application()
    app["local_secret"] = local_secret
    app["start_time"] = time.monotonic()
    # Pre-initialize bridge to avoid DeprecationWarning when re-assigning app keys later
    app["mqtt_bridge"] = MqttBridge()
    # Pre-initialize mapping/publication containers (Story 2.2 — aiohttp guard-rail)
    app["topology"] = None       # TopologySnapshot | None — populated on first sync
    app["eligibility"] = None    # Dict[int, EligibilityResult] | None — populated on first sync
    app["mappings"] = {}       # Dict[int, MappingResult]
    app["publications"] = {}   # Dict[int, PublicationDecision]
    app.router.add_get("/system/status", _handle_system_status)
    app.router.add_post("/action/mqtt_test", _handle_mqtt_test)
    app.router.add_post("/action/mqtt_connect", _handle_mqtt_connect)
    app.router.add_post("/action/sync", _handle_action_sync)
    return app


async def start_server(
    app: web.Application,
    host: str = "127.0.0.1",
    port: int = 55080,
) -> web.AppRunner:
    """Start the HTTP server. Returns the runner for later cleanup."""
    app["start_time"] = time.monotonic()

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    _LOGGER.info("[API] HTTP server started on %s:%d", host, port)
    return runner


async def stop_server(runner: web.AppRunner) -> None:
    """Stop the HTTP server and clean up."""
    if runner is not None:
        await runner.cleanup()
        _LOGGER.info("[API] HTTP server stopped")
