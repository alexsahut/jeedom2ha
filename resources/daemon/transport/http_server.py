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
from discovery.publisher import DiscoveryPublisher

_LOGGER = logging.getLogger(__name__)

_VERSION = "0.2.0"


def _check_secret(request: web.Request, local_secret: str) -> bool:
    """Validate the local_secret from request header."""
    provided = request.headers.get("X-Local-Secret", "")
    if not provided or not local_secret:
        return False
    return provided == local_secret


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
    anciens_eq_ids = set(request.app["mappings"].keys())
    nouveaux_eq_ids = set()

    # 5. Map eligible eqLogics to HA entities (Story 2.2)
    mapper = LightMapper()
    mappings = {}       # Dict[int, MappingResult]
    publications = {}   # Dict[int, PublicationDecision]
    
    mapping_counters = {
        "lights_sure": 0,
        "lights_probable": 0,
        "lights_ambiguous": 0,
        "lights_published": 0,
        "lights_skipped": 0,
    }
    
    mqtt_bridge = request.app.get("mqtt_bridge")
    publisher = DiscoveryPublisher(mqtt_bridge) if mqtt_bridge else None
    
    for eq_id, result in eligibility.items():
        if not result.is_eligible:
            continue
        
        eq = snapshot.eq_logics.get(eq_id)
        if not eq:
            continue
        
        mapping = mapper.map(eq, snapshot)
        if mapping is None:
            continue  # Not a light
        
        mappings[eq_id] = mapping
        
        # Count by confidence
        if mapping.confidence == "sure":
            mapping_counters["lights_sure"] += 1
        elif mapping.confidence == "probable":
            mapping_counters["lights_probable"] += 1
        elif mapping.confidence == "ambiguous":
            mapping_counters["lights_ambiguous"] += 1
        
        # Decide publication
        decision = mapper.decide_publication(mapping)
        publications[eq_id] = decision
        nouveaux_eq_ids.add(eq_id)
        
        if decision.should_publish:
            mapping_counters["lights_published"] += 1
            # Publish via MQTT Discovery if bridge is connected
            if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                await publisher.publish_light(mapping, snapshot)
        else:
            mapping_counters["lights_skipped"] += 1
            
    # Purge des équipements qui ne sont plus remontés ou plus éligibles
    eq_ids_supprimes = anciens_eq_ids - nouveaux_eq_ids
    for old_eq_id in eq_ids_supprimes:
        # Si c'était publié avant, on l'unpublish
        old_decision = request.app["publications"].get(old_eq_id)
        if old_decision and old_decision.should_publish:
            if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                await publisher.unpublish_by_eq_id(old_eq_id)
                _LOGGER.info("[MAPPING] eq_id=%d est devenu inéligible ou supprimé → MQTT unpublish effectif", old_eq_id)
                
        # Nettoyage de la RAM pour éviter les données obsolètes (fuite pour Diagnostics)
        request.app["mappings"].pop(old_eq_id, None)
        request.app["publications"].pop(old_eq_id, None)
    
    # Store detailed decisions in RAM for Epic 4 (diagnostic)
    request.app["mappings"].update(mappings)
    request.app["publications"].update(publications)
    
    _LOGGER.info(
        "[MAPPING] Summary: sure=%d probable=%d ambiguous=%d published=%d skipped=%d",
        mapping_counters["lights_sure"],
        mapping_counters["lights_probable"],
        mapping_counters["lights_ambiguous"],
        mapping_counters["lights_published"],
        mapping_counters["lights_skipped"],
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
