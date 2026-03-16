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
from typing import Dict, Optional

import paho.mqtt.client as mqtt
from aiohttp import web

from .mqtt_client import MqttBridge
from models.availability import (
    AVAILABILITY_OFFLINE,
    AVAILABILITY_ONLINE,
    availability_from_snapshot,
    build_local_availability_topic,
)
from models.topology import TopologySnapshot, assess_all
from models.mapping import MappingResult, PublicationDecision
from mapping.light import LightMapper
from mapping.cover import CoverMapper
from mapping.switch import SwitchMapper
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
    """Resolve runtime state topic for a published actuator mapping."""
    if mapping.ha_entity_type in ("light", "cover", "switch"):
        return f"jeedom2ha/{mapping.jeedom_eq_id}/state"

    return ""


def _apply_availability_metadata(
    decision: PublicationDecision,
    mapping: MappingResult,
    snapshot: TopologySnapshot,
) -> None:
    """Populate availability metadata on runtime publication decisions."""
    entity_availability = availability_from_snapshot(mapping.jeedom_eq_id, snapshot)
    decision.bridge_availability_topic = entity_availability.bridge_availability_topic
    decision.eqlogic_availability_topic = entity_availability.eqlogic_availability_topic
    decision.local_availability_supported = entity_availability.local_availability_supported
    decision.local_availability_state = entity_availability.local_availability_state
    decision.availability_reason = entity_availability.availability_reason


def _publish_local_availability_state(
    mqtt_bridge: MqttBridge,
    eq_id: int,
    decision: PublicationDecision,
) -> bool:
    """Publish retained local availability when a reliable eqLogic signal exists."""
    if not decision.local_availability_supported:
        return True

    topic = decision.eqlogic_availability_topic or build_local_availability_topic(eq_id)
    payload = str(decision.local_availability_state or "").lower()
    if payload not in (AVAILABILITY_ONLINE, AVAILABILITY_OFFLINE):
        _LOGGER.warning(
            "[AVAIL] Skip local availability publish for eq_id=%d (unsupported payload=%s)",
            eq_id,
            payload,
        )
        return False

    ok = mqtt_bridge.publish_message(topic, payload, qos=1, retain=True)
    if ok:
        _LOGGER.info("[AVAIL] Published retained local availability eq_id=%d topic=%s payload=%s", eq_id, topic, payload)
    else:
        _LOGGER.warning("[AVAIL] Failed to publish local availability eq_id=%d topic=%s", eq_id, topic)
    return ok


def _clear_local_availability_topic(
    mqtt_bridge: MqttBridge,
    eq_id: int,
    topic: Optional[str],
) -> bool:
    """Remove retained local availability topic payload to avoid orphan traces."""
    local_topic = topic or build_local_availability_topic(eq_id)
    ok = mqtt_bridge.publish_message(local_topic, "", qos=1, retain=True)
    if ok:
        _LOGGER.info("[AVAIL] Cleared retained local availability eq_id=%d topic=%s", eq_id, local_topic)
    else:
        _LOGGER.warning("[AVAIL] Failed to clear local availability eq_id=%d topic=%s", eq_id, local_topic)
    return ok


def _mark_local_availability_publish_failed(
    decision: PublicationDecision,
    mapping: MappingResult,
) -> PublicationDecision:
    """Build a safe runtime decision when local availability retained publish fails."""
    return PublicationDecision(
        should_publish=False,
        reason="local_availability_publish_failed",
        mapping_result=mapping,
        state_topic=decision.state_topic,
        active_or_alive=False,
        discovery_published=decision.discovery_published,
        bridge_availability_topic=decision.bridge_availability_topic,
        eqlogic_availability_topic=decision.eqlogic_availability_topic,
        local_availability_supported=decision.local_availability_supported,
        local_availability_state=decision.local_availability_state,
        availability_reason=decision.availability_reason,
    )


def _needs_discovery_unpublish(decision: Optional[PublicationDecision]) -> bool:
    """Return True when a discovery unpublish is still required for one entity."""
    if decision is None:
        return False
    if bool(getattr(decision, "discovery_published", False)):
        return True
    # Backward compatibility with pre-flag runtime decisions.
    return bool(getattr(decision, "should_publish", False))


def _defer_local_availability_cleanup(
    pending_cleanup: Dict[int, str],
    eq_id: int,
    topic: Optional[str],
) -> None:
    """Track one retained local availability topic cleanup to replay later."""
    resolved_topic = topic or build_local_availability_topic(eq_id)
    pending_cleanup[int(eq_id)] = resolved_topic
    _LOGGER.info(
        "[AVAIL] Deferred local availability cleanup eq_id=%d topic=%s",
        eq_id,
        resolved_topic,
    )


def _replay_deferred_local_availability_cleanup(
    mqtt_bridge: MqttBridge,
    pending_cleanup: Dict[int, str],
) -> None:
    """Replay deferred local availability cleanup when broker is connected."""
    if not pending_cleanup:
        return

    for pending_eq_id, pending_topic in list(pending_cleanup.items()):
        if _clear_local_availability_topic(mqtt_bridge, pending_eq_id, pending_topic):
            pending_cleanup.pop(pending_eq_id, None)


def _defer_discovery_unpublish(
    pending_unpublish: Dict[int, str],
    eq_id: int,
    entity_type: str,
) -> None:
    """Track one discovery unpublish to replay later when broker is connected."""
    normalized_entity_type = str(entity_type or "light")
    pending_unpublish[int(eq_id)] = normalized_entity_type
    _LOGGER.info(
        "[DISCOVERY] Deferred unpublish eq_id=%d entity_type=%s",
        eq_id,
        normalized_entity_type,
    )


async def _replay_deferred_discovery_unpublish(
    publisher: DiscoveryPublisher,
    pending_unpublish: Dict[int, str],
) -> None:
    """Replay deferred discovery unpublish messages when broker is connected."""
    if not pending_unpublish:
        return

    for pending_eq_id, pending_entity_type in list(pending_unpublish.items()):
        if await publisher.unpublish_by_eq_id(pending_eq_id, entity_type=pending_entity_type):
            pending_unpublish.pop(pending_eq_id, None)


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

    # 5. Map eligible eqLogics to HA entities (Stories 2.2 + 2.3 + 2.4)
    light_mapper = LightMapper()
    cover_mapper = CoverMapper()
    switch_mapper = SwitchMapper()
    mappings = {}       # Dict[int, MappingResult]
    publications = {}   # Dict[int, PublicationDecision]
    
    mapping_counters = {
        "lights_sure": 0,
        "lights_probable": 0,
        "lights_ambiguous": 0,
        "lights_published": 0,
        "lights_skipped": 0,
        "covers_sure": 0,
        "covers_probable": 0,
        "covers_ambiguous": 0,
        "covers_published": 0,
        "covers_skipped": 0,
        "switches_sure": 0,
        "switches_probable": 0,
        "switches_ambiguous": 0,
        "switches_published": 0,
        "switches_skipped": 0,
    }
    
    mqtt_bridge = request.app.get("mqtt_bridge")
    publisher = DiscoveryPublisher(mqtt_bridge) if mqtt_bridge else None
    pending_local_cleanup = request.app["pending_local_availability_cleanup"]
    pending_discovery_unpublish = request.app["pending_discovery_unpublish"]

    if mqtt_bridge and mqtt_bridge.is_connected and publisher:
        await _replay_deferred_discovery_unpublish(publisher, pending_discovery_unpublish)
    if mqtt_bridge and mqtt_bridge.is_connected:
        _replay_deferred_local_availability_cleanup(mqtt_bridge, pending_local_cleanup)
    
    for eq_id, result in eligibility.items():
        if not result.is_eligible:
            continue
        
        eq = snapshot.eq_logics.get(eq_id)
        if not eq:
            continue
        
        # Try light first, then cover, then switch (first mapper that returns non-None wins)
        mapping = light_mapper.map(eq, snapshot)
        if mapping is None:
            mapping = cover_mapper.map(eq, snapshot)
        if mapping is None:
            mapping = switch_mapper.map(eq, snapshot)
        
        if mapping is None:
            continue  # Not mapped by any mapper
        
        mappings[eq_id] = mapping
        previous_decision = request.app["publications"].get(eq_id)
        
        if mapping.ha_entity_type == "light":
            # Count by confidence
            if mapping.confidence == "sure":
                mapping_counters["lights_sure"] += 1
            elif mapping.confidence == "probable":
                mapping_counters["lights_probable"] += 1
            elif mapping.confidence == "ambiguous":
                mapping_counters["lights_ambiguous"] += 1
            
            # Decide publication
            decision = light_mapper.decide_publication(mapping)
            config_published = False
            decision.state_topic = _resolve_state_topic(mapping)
            decision.active_or_alive = False
            _apply_availability_metadata(decision, mapping, snapshot)
            publications[eq_id] = decision
            nouveaux_eq_ids.add(eq_id)
            
            if decision.should_publish:
                if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                    config_published = await publisher.publish_light(mapping, snapshot)
                else:
                    _LOGGER.warning(
                        "[MAPPING] Discovery publish unavailable for eq_id=%d (bridge missing/disconnected)",
                        eq_id,
                    )
                if not config_published:
                    decision = PublicationDecision(
                        should_publish=False,
                        reason="discovery_publish_failed",
                        mapping_result=mapping,
                        state_topic=decision.state_topic,
                        active_or_alive=False,
                        discovery_published=_needs_discovery_unpublish(previous_decision),
                        bridge_availability_topic=decision.bridge_availability_topic,
                        eqlogic_availability_topic=decision.eqlogic_availability_topic,
                        local_availability_supported=decision.local_availability_supported,
                        local_availability_state=decision.local_availability_state,
                        availability_reason=decision.availability_reason,
                    )
                    publications[eq_id] = decision
                else:
                    decision.discovery_published = True
                    local_ok = True
                    if decision.local_availability_supported:
                        local_ok = _publish_local_availability_state(mqtt_bridge, eq_id, decision)
                    if local_ok:
                        decision.active_or_alive = True
                        mapping_counters["lights_published"] += 1
                    else:
                        decision = _mark_local_availability_publish_failed(decision, mapping)
                        publications[eq_id] = decision
            if not decision.active_or_alive:
                mapping_counters["lights_skipped"] += 1

        elif mapping.ha_entity_type == "cover":
            # Count by confidence
            if mapping.confidence == "sure":
                mapping_counters["covers_sure"] += 1
            elif mapping.confidence == "probable":
                mapping_counters["covers_probable"] += 1
            elif mapping.confidence == "ambiguous":
                mapping_counters["covers_ambiguous"] += 1
            
            # Decide publication
            decision = cover_mapper.decide_publication(mapping)
            config_published = False
            decision.state_topic = _resolve_state_topic(mapping)
            decision.active_or_alive = False
            _apply_availability_metadata(decision, mapping, snapshot)
            publications[eq_id] = decision
            nouveaux_eq_ids.add(eq_id)
            
            if decision.should_publish:
                if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                    config_published = await publisher.publish_cover(mapping, snapshot)
                else:
                    _LOGGER.warning(
                        "[MAPPING] Discovery publish unavailable for eq_id=%d (bridge missing/disconnected)",
                        eq_id,
                    )
                if not config_published:
                    decision = PublicationDecision(
                        should_publish=False,
                        reason="discovery_publish_failed",
                        mapping_result=mapping,
                        state_topic=decision.state_topic,
                        active_or_alive=False,
                        discovery_published=_needs_discovery_unpublish(previous_decision),
                        bridge_availability_topic=decision.bridge_availability_topic,
                        eqlogic_availability_topic=decision.eqlogic_availability_topic,
                        local_availability_supported=decision.local_availability_supported,
                        local_availability_state=decision.local_availability_state,
                        availability_reason=decision.availability_reason,
                    )
                    publications[eq_id] = decision
                else:
                    decision.discovery_published = True
                    local_ok = True
                    if decision.local_availability_supported:
                        local_ok = _publish_local_availability_state(mqtt_bridge, eq_id, decision)
                    if local_ok:
                        decision.active_or_alive = True
                        mapping_counters["covers_published"] += 1
                    else:
                        decision = _mark_local_availability_publish_failed(decision, mapping)
                        publications[eq_id] = decision
            if not decision.active_or_alive:
                mapping_counters["covers_skipped"] += 1

        elif mapping.ha_entity_type == "switch":
            # Count by confidence
            if mapping.confidence == "sure":
                mapping_counters["switches_sure"] += 1
            elif mapping.confidence == "probable":
                mapping_counters["switches_probable"] += 1
            elif mapping.confidence == "ambiguous":
                mapping_counters["switches_ambiguous"] += 1

            # Decide publication
            decision = switch_mapper.decide_publication(mapping)
            config_published = False
            decision.state_topic = _resolve_state_topic(mapping)
            decision.active_or_alive = False
            _apply_availability_metadata(decision, mapping, snapshot)
            publications[eq_id] = decision
            nouveaux_eq_ids.add(eq_id)

            if decision.should_publish:
                if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                    config_published = await publisher.publish_switch(mapping, snapshot)
                else:
                    _LOGGER.warning(
                        "[MAPPING] Discovery publish unavailable for eq_id=%d (bridge missing/disconnected)",
                        eq_id,
                    )
                if not config_published:
                    decision = PublicationDecision(
                        should_publish=False,
                        reason="discovery_publish_failed",
                        mapping_result=mapping,
                        state_topic=decision.state_topic,
                        active_or_alive=False,
                        discovery_published=_needs_discovery_unpublish(previous_decision),
                        bridge_availability_topic=decision.bridge_availability_topic,
                        eqlogic_availability_topic=decision.eqlogic_availability_topic,
                        local_availability_supported=decision.local_availability_supported,
                        local_availability_state=decision.local_availability_state,
                        availability_reason=decision.availability_reason,
                    )
                    publications[eq_id] = decision
                else:
                    decision.discovery_published = True
                    local_ok = True
                    if decision.local_availability_supported:
                        local_ok = _publish_local_availability_state(mqtt_bridge, eq_id, decision)
                    if local_ok:
                        decision.active_or_alive = True
                        mapping_counters["switches_published"] += 1
                    else:
                        decision = _mark_local_availability_publish_failed(decision, mapping)
                        publications[eq_id] = decision
            if not decision.active_or_alive:
                mapping_counters["switches_skipped"] += 1

        previous_local_supported = bool(getattr(previous_decision, "local_availability_supported", False))
        previous_local_topic = getattr(previous_decision, "eqlogic_availability_topic", None)
        current_local_supported = bool(getattr(decision, "local_availability_supported", False))
        current_local_topic = getattr(decision, "eqlogic_availability_topic", None)
        should_clear_local = previous_local_supported and (
            (not current_local_supported) or (previous_local_topic != current_local_topic)
        )
        if should_clear_local:
            if mqtt_bridge and mqtt_bridge.is_connected:
                clear_ok = _clear_local_availability_topic(mqtt_bridge, eq_id, previous_local_topic)
                if clear_ok:
                    pending_local_cleanup.pop(eq_id, None)
                else:
                    _defer_local_availability_cleanup(pending_local_cleanup, eq_id, previous_local_topic)
            else:
                _LOGGER.warning(
                    "[AVAIL] Cannot clear stale local availability eq_id=%d (bridge missing/disconnected)",
                    eq_id,
                )
                _defer_local_availability_cleanup(pending_local_cleanup, eq_id, previous_local_topic)
            
    # Purge des équipements qui ne sont plus remontés ou plus éligibles
    eq_ids_supprimes = anciens_eq_ids - nouveaux_eq_ids
    for old_eq_id in eq_ids_supprimes:
        # Si c'était publié avant, on l'unpublish
        old_decision = request.app["publications"].get(old_eq_id)
        if _needs_discovery_unpublish(old_decision):
            entity_type = old_decision.mapping_result.ha_entity_type
            if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                unpublish_ok = await publisher.unpublish_by_eq_id(old_eq_id, entity_type=entity_type)
                if unpublish_ok:
                    pending_discovery_unpublish.pop(old_eq_id, None)
                    _LOGGER.info("[MAPPING] eq_id=%d est devenu inéligible ou supprimé → MQTT unpublish effectif", old_eq_id)
                else:
                    _LOGGER.warning(
                        "[MAPPING] Cannot unpublish discovery for eq_id=%d (publish failed) — deferring",
                        old_eq_id,
                    )
                    _defer_discovery_unpublish(pending_discovery_unpublish, old_eq_id, entity_type)
            else:
                _LOGGER.warning(
                    "[MAPPING] Cannot unpublish discovery for eq_id=%d (bridge missing/disconnected) — deferring",
                    old_eq_id,
                )
                _defer_discovery_unpublish(pending_discovery_unpublish, old_eq_id, entity_type)

            if bool(getattr(old_decision, "local_availability_supported", False)):
                if mqtt_bridge and mqtt_bridge.is_connected:
                    clear_ok = _clear_local_availability_topic(
                        mqtt_bridge,
                        old_eq_id,
                        getattr(old_decision, "eqlogic_availability_topic", None),
                    )
                    if clear_ok:
                        pending_local_cleanup.pop(old_eq_id, None)
                    else:
                        _defer_local_availability_cleanup(
                            pending_local_cleanup,
                            old_eq_id,
                            getattr(old_decision, "eqlogic_availability_topic", None),
                        )
                else:
                    _LOGGER.warning(
                        "[AVAIL] Cannot clear local availability during unpublish for eq_id=%d (bridge missing/disconnected)",
                        old_eq_id,
                    )
                    _defer_local_availability_cleanup(
                        pending_local_cleanup,
                        old_eq_id,
                        getattr(old_decision, "eqlogic_availability_topic", None),
                    )
                
        # Nettoyage de la RAM pour éviter les données obsolètes (fuite pour Diagnostics)
        request.app["mappings"].pop(old_eq_id, None)
        request.app["publications"].pop(old_eq_id, None)
    
    # Store detailed decisions in RAM for Epic 4 (diagnostic)
    request.app["mappings"].update(mappings)
    request.app["publications"].update(publications)
    
    _LOGGER.info(
        "[MAPPING] Summary: lights(sure=%d probable=%d ambiguous=%d published=%d skipped=%d) "
        "covers(sure=%d probable=%d ambiguous=%d published=%d skipped=%d) "
        "switches(sure=%d probable=%d ambiguous=%d published=%d skipped=%d)",
        mapping_counters["lights_sure"],
        mapping_counters["lights_probable"],
        mapping_counters["lights_ambiguous"],
        mapping_counters["lights_published"],
        mapping_counters["lights_skipped"],
        mapping_counters["covers_sure"],
        mapping_counters["covers_probable"],
        mapping_counters["covers_ambiguous"],
        mapping_counters["covers_published"],
        mapping_counters["covers_skipped"],
        mapping_counters["switches_sure"],
        mapping_counters["switches_probable"],
        mapping_counters["switches_ambiguous"],
        mapping_counters["switches_published"],
        mapping_counters["switches_skipped"],
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


async def _handle_system_diagnostics(request: web.Request) -> web.Response:
    """Handle GET /system/diagnostics — return coverage diagnostics."""
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response(
            {"status": "error", "message": "Unauthorized"},
            status=401,
        )

    topology = request.app.get("topology")
    if not topology:
        return web.json_response({
            "status": "error",
            "message": "Diagnostic indisponible : aucune donnée en mémoire (appelez /action/sync d'abord)."
        })

    eligibility = request.app.get("eligibility", {})
    mappings = request.app.get("mappings", {})
    publications = request.app.get("publications", {})
    
    equipments = []
    
    for eq_id, eq in topology.eq_logics.items():
        object_name = topology.get_suggested_area(eq_id) or "Aucun"
        
        status = "Non publié"
        confidence = "Ignoré"
        reason_code = "unknown"
        
        el_result = eligibility.get(eq_id)
        if el_result:
            reason_code = el_result.reason_code
            if not el_result.is_eligible:
                if el_result.reason_code == "excluded_eqlogic":
                    status = "Exclu"
                    confidence = "Ignoré"
                else:
                    status = "Non publié"
                    confidence = "Ignoré"
            else:
                map_result = mappings.get(eq_id)
                pub_decision = publications.get(eq_id)
                
                if map_result:
                    reason_code = map_result.reason_code
                    confidence_map = {
                        "sure": "Sûr",
                        "probable": "Probable",
                        "ambiguous": "Ambigu",
                        "ignore": "Ignoré",
                        "unknown": "Ignoré"
                    }
                    confidence = confidence_map.get(map_result.confidence, "Ignoré")
                    
                    if pub_decision and pub_decision.active_or_alive:
                        mapped_cmd_ids = {c.id for c in map_result.commands.values()}
                        coverable_cmds = {c.id for c in eq.cmds if c.generic_type}
                        unmapped = coverable_cmds - mapped_cmd_ids
                        
                        if unmapped:
                            status = "Partiellement publié"
                        else:
                            status = "Publié"
                        reason_code = pub_decision.reason
                    else:
                        status = "Non publié"
                        if pub_decision:
                            reason_code = pub_decision.reason
                else:
                    reason_code = "no_mapping"
                    confidence = "Ignoré"
                    status = "Non publié"
                    
        equipments.append({
            "eq_id": eq_id,
            "object_name": object_name,
            "name": eq.name,
            "status": status,
            "confidence": confidence,
            "reason_code": reason_code
        })
        
    return web.json_response({
        "action": "system.diagnostics",
        "status": "ok",
        "payload": {
            "equipments": equipments
        },
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
    app["pending_discovery_unpublish"] = {}  # Dict[int, str]
    app["pending_local_availability_cleanup"] = {}  # Dict[int, str]
    app.router.add_get("/system/status", _handle_system_status)
    app.router.add_post("/action/mqtt_test", _handle_mqtt_test)
    app.router.add_post("/action/mqtt_connect", _handle_mqtt_connect)
    app.router.add_post("/action/sync", _handle_action_sync)
    app.router.add_get("/system/diagnostics", _handle_system_diagnostics)
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
