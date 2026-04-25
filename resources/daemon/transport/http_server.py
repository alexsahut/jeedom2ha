"""Local HTTP API server for PHP → daemon communication.

Listens on 127.0.0.1 only, protected by a local_secret shared with the PHP plugin.
"""

import asyncio
import logging
import os
import socket
import ssl
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

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
from models.published_scope import resolve_published_scope
from models.decide_publication import decide_publication
from models.mapping import MappingResult, PublicationDecision, PublicationResult
from models.taxonomy import get_primary_status
from models.aggregation import build_summary
from models.cause_mapping import (
    reason_code_to_cause,
    build_cause_for_pending_unpublish,
    resolve_cause_ux,
)
from models.ui_contract_4d import (
    reason_code_to_perimetre,
    compute_ecart,
    build_ui_counters,
    compute_home_statut,
)
from models.actions_ha import build_actions_ha
from mapping.light import LightMapper
from mapping.cover import CoverMapper
from mapping.switch import SwitchMapper
from discovery.publisher import DiscoveryPublisher
from cache.disk_cache import save_publications_cache
from validation.ha_component_registry import validate_projection

# Résoudre le répertoire data/ relatif à ce fichier (data/ est un sibling de resources/)
_HTTP_SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.normpath(os.path.join(_HTTP_SERVER_DIR, "..", "..", "..", "data"))

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


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _make_publication_result(
    status: str,
    technical_reason_code: Optional[str] = None,
) -> PublicationResult:
    """Construire le sous-bloc technique de l'étape 5 (Story 5.2 PE).

    Owner exclusif : étape 5 du pipeline canonique.
    Ne doit jamais modifier la décision produit (étape 4).
    """
    return PublicationResult(
        status=status,
        technical_reason_code=technical_reason_code,
        attempted_at=datetime.now(timezone.utc).isoformat(),
    )


def _resolve_eq_ids_for_portee(
    portee: str,
    selection: list,
    topology: TopologySnapshot,
) -> list[int]:
    """Resolve eqLogic ids from the requested scope using the in-memory topology only."""
    if portee == "equipement":
        eq_ids: list[int] = []
        for raw_eq_id in selection:
            eq_id = _to_int(raw_eq_id, default=0)
            if eq_id <= 0:
                raise ValueError("Sélection équipement invalide.")
            eq_ids.append(eq_id)
        return eq_ids

    if portee == "piece":
        eq_ids = []
        seen_eq_ids = set()
        for raw_piece_id in selection:
            piece_id = _to_int(raw_piece_id, default=0)
            if piece_id <= 0 or piece_id not in topology.objects:
                raise ValueError(f"Pièce inconnue : {raw_piece_id}.")
            for eq_id, eq in topology.eq_logics.items():
                if eq.object_id == piece_id and eq_id not in seen_eq_ids:
                    eq_ids.append(eq_id)
                    seen_eq_ids.add(eq_id)
        return eq_ids

    if portee == "global":
        return list(topology.eq_logics.keys())

    raise ValueError(f"Portée non reconnue : {portee}.")


def _build_action_execute_response(
    *,
    payload: Dict[str, Any],
    http_status: int = 200,
    top_status: str = "ok",
) -> web.Response:
    return web.json_response(
        {
            "action": "action.execute",
            "status": top_status,
            "payload": payload,
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        status=http_status,
    )


def _normalize_action_execute_body(body: Dict[str, Any]) -> Dict[str, Any]:
    """Accept direct JSON calls and the PHP relay wrapper `{payload: ...}`."""
    wrapped_payload = body.get("payload")
    if (
        isinstance(wrapped_payload, dict)
        and "intention" in wrapped_payload
        and "portee" in wrapped_payload
    ):
        return wrapped_payload
    return body


def _scope_entry_is_included(
    eq_id: int,
    scope_entry: Optional[Dict[str, Any]],
    eligibility: Optional[Dict[int, Any]],
) -> bool:
    if scope_entry is not None:
        return scope_entry.get("effective_state") == "include"
    if eligibility and eq_id in eligibility:
        return bool(getattr(eligibility[eq_id], "is_eligible", False))
    return False


def _is_currently_published_in_ha(
    eq_id: int,
    decision: Optional[PublicationDecision],
    pending_discovery_unpublish: Dict[int, str],
) -> bool:
    if eq_id in pending_discovery_unpublish:
        return True
    if decision is None:
        return False
    return bool(
        getattr(decision, "active_or_alive", False)
        or getattr(decision, "discovery_published", False)
    )


def _should_attempt_publish(
    mapping: Optional[MappingResult],
    decision: Optional[PublicationDecision],
) -> bool:
    if mapping is None:
        return False
    if mapping.confidence not in ("sure", "probable"):
        return False
    if decision is None:
        return True
    return getattr(decision, "reason", "") not in (
        "ambiguous_skipped",
        "probable_skipped",
        "unknown_skipped",
        "ignore_skipped",
    )


async def _publish_mapping_for_action(
    publisher: DiscoveryPublisher,
    mapping: MappingResult,
    topology: TopologySnapshot,
) -> bool:
    if mapping.ha_entity_type == "light":
        return await publisher.publish_light(mapping, topology)
    if mapping.ha_entity_type == "cover":
        return await publisher.publish_cover(mapping, topology)
    if mapping.ha_entity_type == "switch":
        return await publisher.publish_switch(mapping, topology)
    return False


def _build_action_perimetre_impacte(
    *,
    portee: str,
    selection: list,
    topology: TopologySnapshot,
    eq_ids: list[int],
    equipements_inclus: int,
) -> Dict[str, Any]:
    if portee == "equipement":
        eq_id = eq_ids[0] if eq_ids else _to_int(selection[0], default=0)
        eq = topology.eq_logics.get(eq_id)
        return {
            "nom": eq.name if eq else f"Équipement #{eq_id}",
            "equipements_inclus": equipements_inclus,
        }

    if portee == "piece":
        piece_id = _to_int(selection[0], default=0)
        piece = topology.objects.get(piece_id)
        return {
            "nom": piece.name if piece else f"Pièce #{piece_id}",
            "equipements_inclus": equipements_inclus,
        }

    return {
        "nom": "Parc global",
        "equipements_inclus": equipements_inclus,
    }


def _build_publier_message(
    *,
    resultat: str,
    equipements_publies_ou_crees: int,
    publish_errors: int,
) -> str:
    if resultat == "succes_partiel":
        return (
            f"{equipements_publies_ou_crees} équipements mis à jour, "
            f"{publish_errors} n'ont pas pu être traités."
        )
    if resultat == "succes" and equipements_publies_ou_crees == 0:
        return "Configuration déjà à jour dans Home Assistant."
    if resultat == "succes":
        return f"{equipements_publies_ou_crees} équipements mis à jour dans Home Assistant."
    return "L'action n'a pas pu être exécutée. Vérifiez la connexion Home Assistant."


def _build_supprimer_message(
    *,
    resultat: str,
    equipements_supprimes: int,
    supprimer_errors: int,
) -> str:
    if resultat == "succes_partiel":
        return (
            f"{equipements_supprimes} supprimé(s), "
            f"{supprimer_errors} n'ont pas pu être traité(s)."
        )
    if resultat == "succes" and equipements_supprimes == 0:
        return "Configuration déjà à jour dans Home Assistant."
    if resultat == "succes":
        s = "s" if equipements_supprimes > 1 else ""
        return f"{equipements_supprimes} équipement{s} supprimé{s} de Home Assistant."
    return "L'action n'a pas pu être exécutée. Vérifiez la connexion Home Assistant."


def _build_operation_snapshot(
    *,
    resultat: str,
    intention: Optional[str] = None,
    portee: Optional[str] = None,
    message: Optional[str] = None,
    volume: Optional[int] = None,
) -> dict:
    return {
        "resultat": resultat,
        "intention": intention,
        "portee": portee,
        "message": message,
        "volume": volume,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _apply_pending_scope_flags(
    scope_contract: Dict[str, Any],
    publications: Dict[int, PublicationDecision],
    pending_discovery_unpublish: Dict[int, str],
) -> Dict[str, Any]:
    """Enrich canonical scope with pending HA changes without recalculating business resolution."""
    equipements = scope_contract.get("equipements", [])
    piece_pending: Dict[int, bool] = {}

    for eq_entry in equipements:
        eq_id = _to_int(eq_entry.get("eq_id"), default=0)
        desired_include = eq_entry.get("effective_state") == "include"
        decision = publications.get(eq_id)
        is_active = bool(decision and getattr(decision, "active_or_alive", False))
        if eq_id in pending_discovery_unpublish:
            # Unpublish deferred => still active in HA until replay.
            is_active = True
        has_pending = desired_include != is_active
        eq_entry["has_pending_home_assistant_changes"] = has_pending

        piece_id = _to_int(eq_entry.get("object_id"), default=0)
        piece_pending[piece_id] = piece_pending.get(piece_id, False) or has_pending

    for piece in scope_contract.get("pieces", []):
        piece_id = _to_int(piece.get("object_id"), default=0)
        piece["has_pending_home_assistant_changes"] = piece_pending.get(piece_id, False)

    global_section = scope_contract.get("global", {})
    global_section["has_pending_home_assistant_changes"] = any(piece_pending.values())
    scope_contract["global"] = global_section
    return scope_contract


def _needs_discovery_unpublish(decision: Optional[PublicationDecision]) -> bool:
    """Return True when a discovery unpublish is still required for one entity."""
    if decision is None:
        return False
    if bool(getattr(decision, "discovery_published", False)):
        return True
    # Story 5.2 PE : si publication_result existe, l'état de publication Discovery
    # est explicitement connu (success/failed/not_attempted). Sans discovery_published,
    # il n'y a donc rien à unpublish.
    mapping_result = getattr(decision, "mapping_result", None)
    if mapping_result is not None and getattr(mapping_result, "publication_result", None) is not None:
        return False
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


async def _detect_lifecycle_changes(
    eq_id: int,
    mapping,
    previous_decision,
    boot_cache: dict,
    is_first_sync: bool,
    publisher,
    pending_discovery_unpublish: dict,
) -> None:
    """Detect and handle rename, area change, and retyping for a single eq_id.

    Called once per eq_id in the mapping loop, before publish.
    Guardrail: never publishes — only unpublishes stale topics and logs.

    - Rename (runtime or boot): logs INFO [LIFECYCLE], no topic/unique_id change.
    - Area change (runtime): logs INFO [LIFECYCLE].
    - Retyping (runtime or boot): unpublishes old topic BEFORE new publish.
      If unpublish fails: defers into pending_discovery_unpublish and continues.
    """
    # --- Runtime detection (previous_decision from app["publications"]) ---
    if previous_decision is not None and getattr(previous_decision, "mapping_result", None) is not None:
        prev_mr = previous_decision.mapping_result
        # Retypage runtime: unpublish old topic if entity_type changed
        if prev_mr.ha_entity_type != mapping.ha_entity_type and _needs_discovery_unpublish(previous_decision):
            _LOGGER.info(
                "[LIFECYCLE] eq_id=%d: retypage détecté (%s → %s) → unpublish ancien topic",
                eq_id, prev_mr.ha_entity_type, mapping.ha_entity_type,
            )
            if publisher is not None:
                unpublish_ok = await publisher.unpublish_by_eq_id(eq_id, entity_type=prev_mr.ha_entity_type)
            else:
                unpublish_ok = False
            if not unpublish_ok:
                _defer_discovery_unpublish(pending_discovery_unpublish, eq_id, prev_mr.ha_entity_type)
        # Rename / area change logs (publication already handled by handler with fresh data)
        if prev_mr.ha_name != mapping.ha_name:
            _LOGGER.info(
                "[LIFECYCLE] eq_id=%d: rename détecté ('%s' → '%s')",
                eq_id, prev_mr.ha_name, mapping.ha_name,
            )
        if prev_mr.suggested_area != mapping.suggested_area:
            _LOGGER.info(
                "[LIFECYCLE] eq_id=%d: area change ('%s' → '%s')",
                eq_id, prev_mr.suggested_area, mapping.suggested_area,
            )

    # --- Boot detection (boot_cache loaded from disk) ---
    if is_first_sync:
        boot_entry = boot_cache.get(eq_id)
        if boot_entry:
            boot_type = boot_entry.get("entity_type", "")
            boot_name = boot_entry.get("ha_name", "")
            # Retypage au boot (guard: ne tenter unpublish que si réellement publié — Guardrail 5)
            if boot_type and boot_type != mapping.ha_entity_type and boot_entry.get("published", False):
                _LOGGER.info(
                    "[LIFECYCLE] eq_id=%d: retypage au boot (%s → %s) → unpublish ancien topic",
                    eq_id, boot_type, mapping.ha_entity_type,
                )
                if publisher is not None:
                    unpublish_ok = await publisher.unpublish_by_eq_id(eq_id, entity_type=boot_type)
                else:
                    unpublish_ok = False
                if not unpublish_ok:
                    _defer_discovery_unpublish(pending_discovery_unpublish, eq_id, boot_type)
            # Rename au boot
            if boot_name and boot_name != mapping.ha_name:
                _LOGGER.info(
                    "[LIFECYCLE] eq_id=%d: rename détecté depuis boot_cache ('%s' → '%s')",
                    eq_id, boot_name, mapping.ha_name,
                )


async def _republish_all_from_cache(app: web.Application, reason: str) -> None:
    """Republish all published entities from the RAM cache (app["publications"]).

    Called on:
      - homeassistant/status = online  (birth HA, reason="ha_birth")
      - MQTT broker reconnect          (reason="broker_reconnect")

    Guardrail: NEVER publishes from the disk cache (app["boot_cache"]).
               Only reads app["publications"] (live RAM cache).
    Lissage (Décision 8): delay = max(0.1, 10.0 / N) between each publish (batch only).

    For broker_reconnect, pending_discovery_unpublish is replayed FIRST (AC #11).
    """
    publications = app.get("publications", {})
    published_entries = [
        (eq_id, dec)
        for eq_id, dec in publications.items()
        if getattr(dec, "discovery_published", False)
    ]

    if not published_entries:
        if reason == "ha_birth":
            _LOGGER.info(
                "[BOOTSTRAP] Birth HA reçu — aucune entité publiée en mémoire, republication ignorée "
                "(la prochaine /action/sync publiera toutes les entités éligibles)"
            )
        return

    mqtt_bridge = app.get("mqtt_bridge")
    if not mqtt_bridge or not mqtt_bridge.is_connected:
        _LOGGER.warning(
            "[DISCOVERY] Republication annulée (reason=%s) — broker non connecté", reason
        )
        return

    publisher = DiscoveryPublisher(mqtt_bridge)

    # AC #11: rejouer les pending_discovery_unpublish AVANT la republication (reconnect uniquement)
    if reason == "broker_reconnect":
        pending_unpublish = app.get("pending_discovery_unpublish", {})
        await _replay_deferred_discovery_unpublish(publisher, pending_unpublish)

    topology = app.get("topology")
    nb_entites = len(published_entries)
    delay = max(0.1, 10.0 / nb_entites)

    _LOGGER.info(
        "[DISCOVERY] Republication batch (reason=%s) : %d entités, délai=%.2fs",
        reason, nb_entites, delay,
    )

    for eq_id, decision in published_entries:
        mapping = getattr(decision, "mapping_result", None)
        if mapping is None:
            continue
        entity_type = getattr(mapping, "ha_entity_type", "") or ""
        try:
            if entity_type == "light":
                ok = await publisher.publish_light(mapping, topology)
            elif entity_type == "cover":
                ok = await publisher.publish_cover(mapping, topology)
            elif entity_type == "switch":
                ok = await publisher.publish_switch(mapping, topology)
            else:
                ok = False
            if not ok:
                _LOGGER.error(
                    "[DISCOVERY] eq_id=%d entity_type=%s : échec publish — bridge indisponible",
                    eq_id, entity_type,
                )
        except Exception as exc:
            _LOGGER.error(
                "[DISCOVERY] eq_id=%d entity_type=%s : échec publish — %s",
                eq_id, entity_type, exc,
            )
        await asyncio.sleep(delay)


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
            # Legacy fields (do not remove for V1.1 backward compat)
            "version": _VERSION,
            "uptime": round(uptime, 2),
            "mqtt": mqtt_section,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            # New unified scope for bridge health
            "demon": {
                "version": _VERSION,
                "uptime": round(uptime, 2),
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            },
            "broker": mqtt_section,
            "derniere_synchro_terminee": request.app.get("derniere_synchro_terminee"),
            "derniere_operation_resultat": request.app.get("derniere_operation_resultat", "aucun"),
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

    # Story 5.1 — Task 4.3: injecter les callbacks de republication dans le bridge
    app = request.app

    async def _reconnect_cb():
        """Called when broker reconnects — republish from RAM cache if non-empty."""
        if app.get("publications"):
            await _republish_all_from_cache(app, "broker_reconnect")
        else:
            _LOGGER.info(
                "[BOOTSTRAP] Reconnect broker — aucune entité publiée en mémoire, republication ignorée"
            )

    async def _ha_birth_cb():
        """Called when homeassistant/status = online — republish from RAM cache."""
        await _republish_all_from_cache(app, "ha_birth")

    # Start the persistent bridge with new params and republication callbacks
    await bridge.start(params, on_reconnect_cb=_reconnect_cb, on_ha_birth_cb=_ha_birth_cb)

    return web.json_response({
        "action": "mqtt.connect",
        "status": "ok",
        "payload": {"state": bridge.state, "broker": bridge.broker_info},
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def _handle_action_sync(request: web.Request) -> web.Response:
    """Wrapper pour la synchronisation afin de capter l'état global en cas d'erreur inattendue."""
    try:
        return await _do_handle_action_sync(request)
    except Exception as e:
        request.app["derniere_operation_resultat"] = _build_operation_snapshot(
            resultat="echec",
            intention="sync",
            message="Synchronisation échouée — erreur inattendue.",
        )
        request.app["derniere_synchro_terminee"] = datetime.now(timezone.utc).isoformat()
        _LOGGER.error("[SYNC] Echec inattendu lors de la synchronisation", exc_info=True)
        raise

async def _do_handle_action_sync(request: web.Request) -> web.Response:
    """Handle POST /action/sync — synchronize Jeedom topology, assess eligibility, map and publish."""
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response(
            {"status": "error", "message": "Unauthorized"},
            status=401,
        )

    data = await request.json()
    payload = data.get("payload", {})

    # Story 4.3 — Extraire et valider confidence_policy avant de traiter la topologie
    sync_config = payload.get("sync_config", {})
    confidence_policy = sync_config.get("confidence_policy", "sure_probable")
    if confidence_policy not in ("sure_only", "sure_probable"):
        _LOGGER.warning("[SYNC] confidence_policy invalide '%s' → fallback sure_probable", confidence_policy)
        confidence_policy = "sure_probable"

    _LOGGER.info("[TOPOLOGY] Received sync request (confidence_policy=%s)", confidence_policy)

    # 1. Normalize and store snapshot
    snapshot = TopologySnapshot.from_jeedom_payload(payload)
    request.app["topology"] = snapshot

    # Story 1.1 — resolver canonique du périmètre publié (global -> piece -> equipement).
    published_scope_raw = payload.get("published_scope", {})
    published_scope_contract = resolve_published_scope(snapshot, raw_scope=published_scope_raw)
    
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
    # Story 5.1 — Task 7.1: si premier sync post-boot (mappings vide), initialiser
    # anciens_eq_ids depuis boot_cache (eq_id published=True) pour détecter suppressions
    # survenues pendant le downtime daemon (ghost-risk).
    is_first_sync = not request.app["mappings"]
    if is_first_sync:
        boot_cache = request.app.get("boot_cache", {})
        anciens_eq_ids = {eq_id for eq_id, entry in boot_cache.items() if entry.get("published")}
        if anciens_eq_ids:
            _LOGGER.info(
                "[CACHE] Premier sync post-boot : %d anciens eq_ids issus du cache disque",
                len(anciens_eq_ids),
            )
    else:
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

        # Story 5.2 — detect lifecycle changes (rename, area change, retyping)
        # Called once per eq_id, before publish, common to all type branches
        await _detect_lifecycle_changes(
            eq_id, mapping, previous_decision,
            boot_cache=request.app.get("boot_cache", {}),
            is_first_sync=is_first_sync,
            publisher=publisher,
            pending_discovery_unpublish=pending_discovery_unpublish,
        )
        # Pipeline canonique Story 5.1 :
        # étape 3 (validate_projection) puis étape 4 (decide_publication),
        # sans court-circuit pour les équipements éligibles mappés.
        projection_validity = validate_projection(mapping.ha_entity_type, mapping.capabilities)
        mapping.projection_validity = projection_validity
        mapping.pipeline_step_reached = 3
        decision = decide_publication(mapping, confidence_policy=confidence_policy)
        decision.mapping_result = mapping
        mapping.publication_decision_ref = decision
        mapping.pipeline_step_reached = 4

        if mapping.ha_entity_type == "light":
            # Count by confidence
            if mapping.confidence == "sure":
                mapping_counters["lights_sure"] += 1
            elif mapping.confidence == "probable":
                mapping_counters["lights_probable"] += 1
            elif mapping.confidence == "ambiguous":
                mapping_counters["lights_ambiguous"] += 1
            
            config_published = False
            decision.state_topic = _resolve_state_topic(mapping)
            decision.active_or_alive = False
            _apply_availability_metadata(decision, mapping, snapshot)
            publications[eq_id] = decision
            nouveaux_eq_ids.add(eq_id)
            
            # Étape 5 — résultat technique (Story 5.2 PE : sous-bloc séparé, décision étape 4 intacte)
            if decision.should_publish:
                if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                    config_published = await publisher.publish_light(mapping, snapshot)
                else:
                    config_published = False
                    _LOGGER.warning(
                        "[MAPPING] Discovery publish unavailable for eq_id=%d (bridge missing/disconnected)",
                        eq_id,
                    )
                if not config_published:
                    # Préserver le marqueur HA stale si l'entité était précédemment publiée
                    if _needs_discovery_unpublish(previous_decision):
                        decision.discovery_published = True
                    mapping.publication_result = _make_publication_result(
                        "failed", "discovery_publish_failed"
                    )
                else:
                    decision.discovery_published = True
                    local_ok = True
                    if decision.local_availability_supported:
                        local_ok = _publish_local_availability_state(mqtt_bridge, eq_id, decision)
                    if local_ok:
                        decision.active_or_alive = True
                        mapping.publication_result = _make_publication_result("success")
                        mapping_counters["lights_published"] += 1
                    else:
                        mapping.publication_result = _make_publication_result(
                            "failed", "local_availability_publish_failed"
                        )
            else:
                mapping.publication_result = _make_publication_result("not_attempted")
            mapping.pipeline_step_reached = 5
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
            
            config_published = False
            decision.state_topic = _resolve_state_topic(mapping)
            decision.active_or_alive = False
            _apply_availability_metadata(decision, mapping, snapshot)
            publications[eq_id] = decision
            nouveaux_eq_ids.add(eq_id)
            
            # Étape 5 — résultat technique (Story 5.2 PE : sous-bloc séparé, décision étape 4 intacte)
            if decision.should_publish:
                if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                    config_published = await publisher.publish_cover(mapping, snapshot)
                else:
                    config_published = False
                    _LOGGER.warning(
                        "[MAPPING] Discovery publish unavailable for eq_id=%d (bridge missing/disconnected)",
                        eq_id,
                    )
                if not config_published:
                    if _needs_discovery_unpublish(previous_decision):
                        decision.discovery_published = True
                    mapping.publication_result = _make_publication_result(
                        "failed", "discovery_publish_failed"
                    )
                else:
                    decision.discovery_published = True
                    local_ok = True
                    if decision.local_availability_supported:
                        local_ok = _publish_local_availability_state(mqtt_bridge, eq_id, decision)
                    if local_ok:
                        decision.active_or_alive = True
                        mapping.publication_result = _make_publication_result("success")
                        mapping_counters["covers_published"] += 1
                    else:
                        mapping.publication_result = _make_publication_result(
                            "failed", "local_availability_publish_failed"
                        )
            else:
                mapping.publication_result = _make_publication_result("not_attempted")
            mapping.pipeline_step_reached = 5
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

            config_published = False
            decision.state_topic = _resolve_state_topic(mapping)
            decision.active_or_alive = False
            _apply_availability_metadata(decision, mapping, snapshot)
            publications[eq_id] = decision
            nouveaux_eq_ids.add(eq_id)

            # Étape 5 — résultat technique (Story 5.2 PE : sous-bloc séparé, décision étape 4 intacte)
            if decision.should_publish:
                if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                    config_published = await publisher.publish_switch(mapping, snapshot)
                else:
                    config_published = False
                    _LOGGER.warning(
                        "[MAPPING] Discovery publish unavailable for eq_id=%d (bridge missing/disconnected)",
                        eq_id,
                    )
                if not config_published:
                    if _needs_discovery_unpublish(previous_decision):
                        decision.discovery_published = True
                    mapping.publication_result = _make_publication_result(
                        "failed", "discovery_publish_failed"
                    )
                else:
                    decision.discovery_published = True
                    local_ok = True
                    if decision.local_availability_supported:
                        local_ok = _publish_local_availability_state(mqtt_bridge, eq_id, decision)
                    if local_ok:
                        decision.active_or_alive = True
                        mapping.publication_result = _make_publication_result("success")
                        mapping_counters["switches_published"] += 1
                    else:
                        mapping.publication_result = _make_publication_result(
                            "failed", "local_availability_publish_failed"
                        )
            else:
                mapping.publication_result = _make_publication_result("not_attempted")
            mapping.pipeline_step_reached = 5
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
            
    # Story 4.3 — Task 2.7 : dépublication des équipements éligibles mais bloqués par la policy
    # Cas : était publié avec "probable" sous "sure_probable", maintenant "sure_only" → unpublish
    # Ces eq_ids sont dans nouveaux_eq_ids (toujours éligibles) donc NON couverts par eq_ids_supprimes
    for eq_id in nouveaux_eq_ids:
        previous_decision = request.app["publications"].get(eq_id)
        current_decision = publications.get(eq_id)
        if (previous_decision is not None
                and _needs_discovery_unpublish(previous_decision)
                and current_decision is not None
                and not current_decision.should_publish):
            entity_type = previous_decision.mapping_result.ha_entity_type
            _LOGGER.info(
                "[SYNC] eq_id=%d: policy change → dépublication (was=%s now=%s)",
                eq_id, previous_decision.reason, current_decision.reason,
            )
            if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                unpublish_ok = await publisher.unpublish_by_eq_id(eq_id, entity_type=entity_type)
                if unpublish_ok:
                    pending_discovery_unpublish.pop(eq_id, None)
                else:
                    _LOGGER.warning(
                        "[SYNC] Cannot unpublish eq_id=%d for policy change — deferring",
                        eq_id,
                    )
                    _defer_discovery_unpublish(pending_discovery_unpublish, eq_id, entity_type)
            else:
                _LOGGER.warning(
                    "[SYNC] Cannot unpublish eq_id=%d for policy change (bridge missing/disconnected) — deferring",
                    eq_id,
                )
                _defer_discovery_unpublish(pending_discovery_unpublish, eq_id, entity_type)
            # Nettoyer la disponibilité locale si elle était présente
            if bool(getattr(previous_decision, "local_availability_supported", False)):
                prev_local_topic = getattr(previous_decision, "eqlogic_availability_topic", None)
                if mqtt_bridge and mqtt_bridge.is_connected:
                    clear_ok = _clear_local_availability_topic(mqtt_bridge, eq_id, prev_local_topic)
                    if clear_ok:
                        pending_local_cleanup.pop(eq_id, None)
                    else:
                        _defer_local_availability_cleanup(pending_local_cleanup, eq_id, prev_local_topic)
                else:
                    _defer_local_availability_cleanup(pending_local_cleanup, eq_id, prev_local_topic)

    # Purge des équipements qui ne sont plus remontés ou plus éligibles
    eq_ids_supprimes = anciens_eq_ids - nouveaux_eq_ids
    for old_eq_id in eq_ids_supprimes:
        # Si c'était publié avant, on l'unpublish
        old_decision = request.app["publications"].get(old_eq_id)
        elig_entry = eligibility.get(old_eq_id)
        if elig_entry is None:
            cleanup_reason = "supprimé dans Jeedom"
        elif elig_entry.reason_code == "disabled_eqlogic":
            cleanup_reason = "désactivé dans Jeedom (disabled_eqlogic)"
        elif str(elig_entry.reason_code).startswith("excluded_"):
            cleanup_reason = f"exclu ({elig_entry.reason_code})"
        else:
            cleanup_reason = f"devenu inéligible ({elig_entry.reason_code})"

        # Story 5.1 — Task 7.1: au premier sync post-boot, old_decision peut être None
        # (entité présente dans boot_cache mais jamais dans publications RAM).
        # Dans ce cas, utiliser l'entity_type du boot_cache pour l'unpublish.
        if old_decision is None and is_first_sync:
            boot_cache = request.app.get("boot_cache", {})
            boot_entry = boot_cache.get(old_eq_id)
            if boot_entry and boot_entry.get("published"):
                boot_entity_type = boot_entry.get("entity_type") or "light"
                boot_cleanup_reason = "supprimé depuis downtime daemon" if elig_entry is None else cleanup_reason
                discovery_action = "discovery unpublish effectif"
                if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                    unpublish_ok = await publisher.unpublish_by_eq_id(old_eq_id, entity_type=boot_entity_type)
                    if unpublish_ok:
                        pending_discovery_unpublish.pop(old_eq_id, None)
                    else:
                        discovery_action = "discovery unpublish deferred"
                        _defer_discovery_unpublish(pending_discovery_unpublish, old_eq_id, boot_entity_type)
                else:
                    discovery_action = "discovery unpublish deferred"
                    _defer_discovery_unpublish(pending_discovery_unpublish, old_eq_id, boot_entity_type)
                avail_topic = build_local_availability_topic(old_eq_id)
                availability_action = "availability cleanup"
                if mqtt_bridge and mqtt_bridge.is_connected:
                    clear_ok = _clear_local_availability_topic(mqtt_bridge, old_eq_id, avail_topic)
                    if clear_ok:
                        pending_local_cleanup.pop(old_eq_id, None)
                    else:
                        availability_action = "availability cleanup deferred"
                        _defer_local_availability_cleanup(pending_local_cleanup, old_eq_id, avail_topic)
                else:
                    availability_action = "availability cleanup deferred"
                    _defer_local_availability_cleanup(pending_local_cleanup, old_eq_id, avail_topic)
                _LOGGER.info(
                    "[CLEANUP] eq_id=%d: %s → %s + %s (boot_cache, entity_type=%s)",
                    old_eq_id,
                    boot_cleanup_reason,
                    discovery_action,
                    availability_action,
                    boot_entity_type,
                )
            continue  # old_decision is None — skip the standard unpublish path below

        if _needs_discovery_unpublish(old_decision):
            entity_type = old_decision.mapping_result.ha_entity_type
            discovery_action = "discovery unpublish effectif"
            if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                unpublish_ok = await publisher.unpublish_by_eq_id(old_eq_id, entity_type=entity_type)
                if unpublish_ok:
                    pending_discovery_unpublish.pop(old_eq_id, None)
                else:
                    discovery_action = "discovery unpublish deferred"
                    _defer_discovery_unpublish(pending_discovery_unpublish, old_eq_id, entity_type)
            else:
                discovery_action = "discovery unpublish deferred"
                _defer_discovery_unpublish(pending_discovery_unpublish, old_eq_id, entity_type)
            avail_topic = build_local_availability_topic(old_eq_id)
            availability_action = "availability cleanup"
            if mqtt_bridge and mqtt_bridge.is_connected:
                clear_ok = _clear_local_availability_topic(
                    mqtt_bridge,
                    old_eq_id,
                    avail_topic,
                )
                if clear_ok:
                    pending_local_cleanup.pop(old_eq_id, None)
                else:
                    availability_action = "availability cleanup deferred"
                    _defer_local_availability_cleanup(
                        pending_local_cleanup,
                        old_eq_id,
                        avail_topic,
                    )
            else:
                availability_action = "availability cleanup deferred"
                _defer_local_availability_cleanup(
                    pending_local_cleanup,
                    old_eq_id,
                    avail_topic,
                )
            _LOGGER.info(
                "[CLEANUP] eq_id=%d: %s → %s + %s",
                old_eq_id,
                cleanup_reason,
                discovery_action,
                availability_action,
            )
                
        # Nettoyage de la RAM pour éviter les données obsolètes (fuite pour Diagnostics)
        request.app["mappings"].pop(old_eq_id, None)
        request.app["publications"].pop(old_eq_id, None)
    
    # Store detailed decisions in RAM for Epic 4 (diagnostic)
    request.app["mappings"].update(mappings)
    request.app["publications"].update(publications)
    request.app["published_scope"] = _apply_pending_scope_flags(
        published_scope_contract,
        request.app["publications"],
        request.app["pending_discovery_unpublish"],
    )

    # Story 5.1 — Task 1.2: persister le cache disque après chaque sync réussi
    save_publications_cache(request.app["publications"], _DATA_DIR)

    # Story 5.1 — Task 7.3: purger boot_cache après le premier sync (rôle accompli)
    if is_first_sync and request.app.get("boot_cache"):
        request.app["boot_cache"] = {}
        _LOGGER.info("[CACHE] boot_cache purgé après premier sync")

    # Story 5.1 — Task 2.1: signaler que le premier sync a été reçu (annule le watchdog)
    boot_sync_event = request.app.get("boot_sync_received")
    if boot_sync_event is not None and not boot_sync_event.is_set():
        boot_sync_event.set()

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
        "published_scope": request.app["published_scope"],
    }
    
    # Validation du statut global de l'operation de synchronisation
    # Story 5.2 PE : lire le résultat technique depuis publication_result (sous-bloc étape 5)
    def _publication_has_technical_failure(dec: PublicationDecision) -> bool:
        mr = getattr(dec, "mapping_result", None)
        if mr is not None:
            pr = getattr(mr, "publication_result", None)
            if pr is not None:
                return pr.status == "failed"
        # Aucun publication_result → pas de failure technique connue (Story 5.2 PE strict)
        return False

    _has_failures = any(
        _publication_has_technical_failure(d)
        for d in request.app["publications"].values()
    )
    _has_deferred = bool(request.app.get("pending_discovery_unpublish") or request.app.get("pending_local_availability_cleanup"))
    _has_successes = any(getattr(d, "active_or_alive", False) for d in request.app["publications"].values())

    _SYNC_MESSAGES = {
        "succes": "Synchronisation terminée.",
        "partiel": "Synchronisation terminée avec avertissements.",
        "echec": "Synchronisation échouée.",
    }
    if _has_failures or _has_deferred:
        _snap_res = "partiel" if _has_successes else "echec"
    else:
        # Même si rien n'est publié (0 éligibles), s'il n'y a eu aucune erreur, c'est un succès structurel
        _snap_res = "succes"
    request.app["derniere_operation_resultat"] = _build_operation_snapshot(
        resultat=_snap_res,
        intention="sync",
        message=_SYNC_MESSAGES[_snap_res],
    )
        
    request.app["derniere_synchro_terminee"] = datetime.now(timezone.utc).isoformat()
    
    return web.json_response({
        "action": "sync",
        "status": "ok",
        "payload": summary,
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


_DIAGNOSTIC_MESSAGES = {
    "no_commands": (
        "Cet équipement n'a aucune commande configurée dans Jeedom.",
        "Vérifiez que l'équipement possède des commandes actives dans Jeedom.",
        False,
    ),
    "excluded_plugin": (
        "Cet équipement est exclu car son plugin source figure dans la liste d'exclusions.",
        "Pour le publier, retirez son plugin de la liste d'exclusions dans la configuration.",
        False,
    ),
    "excluded_object": (
        "Cet équipement est exclu car sa pièce/objet figure dans la liste d'exclusions.",
        "Pour le publier, retirez sa pièce de la liste d'exclusions dans la configuration.",
        False,
    ),
    "no_supported_generic_type": (
        "Aucune commande de cet équipement n'a un type générique supporté vers Home Assistant dans la V1 du plugin.",
        "Ce type d'équipement n'est pas encore couvert par le périmètre V1 vers Home Assistant. "
        "Aucune action Jeedom ne permettra de le publier pour le moment.",
        True,
    ),
    "disabled": (
        "Cet équipement est désactivé dans Jeedom.",
        "Activez l'équipement dans sa page de configuration Jeedom pour qu'il devienne éligible.",
        False,
    ),
    "disabled_eqlogic": (
        "Cet équipement est désactivé dans Jeedom.",
        "Activez l'équipement dans sa page de configuration Jeedom pour qu'il devienne éligible.",
        False,
    ),
    "excluded_eqlogic": (
        "Cet équipement est exclu manuellement de la publication vers Home Assistant.",
        "Pour le publier, retirez-le de la liste d'exclusions dans la configuration du plugin.",
        False,
    ),
    "ambiguous_skipped": (
        "Plusieurs types d'entités Home Assistant sont possibles pour cet équipement. "
        "Le plugin ne publie pas en cas d'ambiguïté.",
        "Précisez les types génériques sur les commandes pour lever l'ambiguïté "
        "et permettre une publication fiable.",
        False,
    ),
    "probable_skipped": (
        "Cet équipement a un niveau de confiance 'probable' mais la politique de publication "
        "est configurée sur 'sûr uniquement'. Il n'est donc pas publié.",
        "Pour le publier, passez la politique de publication à 'sûr et probable' "
        "dans la configuration du plugin, puis relancez un rescan.",
        False,
    ),
    "no_mapping": (
        "Aucun type d'équipement Home Assistant ne correspond à cet équipement dans la V1 du plugin.",
        "Ce type d'équipement n'est pas encore supporté. "
        "Consultez la documentation du plugin pour connaître le périmètre V1 supporté.",
        True,
    ),
    "discovery_publish_failed": (
        "La publication MQTT de cet équipement a échoué lors du dernier sync.",
        "Vérifiez la connexion au broker MQTT et relancez un diagnostic après résolution.",
        False,
    ),
    "local_availability_publish_failed": (
        "La publication de la disponibilité locale de cet équipement a échoué.",
        "Vérifiez la connexion au broker MQTT et relancez un sync.",
        False,
    ),
    "no_generic_type_configured": (
        "Les commandes de cet équipement n'ont pas de types génériques configurés dans Jeedom.",
        "Configurez les types génériques sur les commandes via le plugin Jeedom concerné, "
        "puis relancez un rescan.",
        False,
    ),
    "low_confidence": (
        "La projection Home Assistant de cet équipement est valide, mais sa confiance est insuffisante pour la politique active.",
        "Assouplir la politique de confiance si vous souhaitez autoriser un mapping moins fiable.",
        False,
    ),
    "ha_component_not_in_product_scope": (
        "La projection de cet équipement est valide, mais son composant Home Assistant n'est pas ouvert dans le cycle courant.",
        "Aucune action côté Jeedom : ce composant n'est pas encore pris en charge dans le cycle courant.",
        False,
    ),
    "sure_mapping": (
        "Cet équipement est publié mais certaines commandes ne sont pas couvertes par le mapping V1.",
        "Configurez les types génériques manquants sur les commandes listées "
        "ci-dessous pour une couverture complète.",
        False,
    ),
    "sure": (
        "Cet équipement est publié mais certaines commandes ne sont pas couvertes par le mapping V1.",
        "Configurez les types génériques manquants sur les commandes pour une couverture complète.",
        False,
    ),
    "probable": (
        "Cet équipement est publié vers Home Assistant avec une correspondance probable.",
        "",
        False,
    ),
    "eligible": (
        "Cet équipement est éligible mais n'a pas été publié lors du dernier sync.",
        "Relancez un sync complet depuis l'interface du plugin.",
        False,
    ),
}

_DIAGNOSTIC_DEFAULT = (
    "Cause inconnue.",
    "Relancez un sync. Si le problème persiste, consultez les logs du démon.",
    False,
)


def _get_diagnostic_enrichment(reason_code: str) -> tuple:
    """Return (detail, remediation, v1_limitation) for a given reason_code."""
    return _DIAGNOSTIC_MESSAGES.get(reason_code, _DIAGNOSTIC_DEFAULT)


# Mapping statut UX → code machine stable pour l'export de diagnostic (Story 4.4 / Story 3.1)
_STATUS_CODE_MAP: dict = {
    "Publié":               "published",
    "Exclu":                "excluded",
    "Ambigu":               "ambiguous",
    "Non supporté":         "not_supported",
    "Incident infrastructure": "infra_incident",
}

# AC2 — Taxonomie fermée des reason_codes pour traceability.decision_trace
# Liste fermée : published, excluded, disabled_eqlogic, no_commands, ambiguous_skipped,
#                confidence_policy_skipped, no_generic_type_configured,
#                no_supported_generic_type, discovery_publish_failed
_CLOSED_REASON_MAP: dict = {
    # Eligibility — codes normalisés
    "excluded_eqlogic": "excluded",
    "excluded_plugin":  "excluded",   # Story 4.3
    "excluded_object":  "excluded",   # Story 4.3
    "excluded": "excluded",
    "disabled": "disabled_eqlogic",            # legacy alias (ancienne v1 du plugin)
    "disabled_eqlogic": "disabled_eqlogic",
    "no_commands": "no_commands",
    # Type générique — distinction "non configuré" vs "hors V1"
    "no_supported_generic_type": "no_generic_type_configured",  # commandes sans type générique
    "no_generic_type_configured": "no_generic_type_configured",  # idempotent
    # Publication / mapping
    "ambiguous_skipped": "ambiguous_skipped",
    "ambiguous": "ambiguous_skipped",           # legacy map_result.reason_code
    "probable_skipped": "confidence_policy_skipped",  # Story 4.3 — bloqué par politique de confiance sure_only
    "no_mapping": "no_supported_generic_type",  # types configurés hors périmètre V1
    "eligible": "no_supported_generic_type",    # éligible mais aucune décision de publication
    "discovery_publish_failed": "discovery_publish_failed",
    "local_availability_publish_failed": "discovery_publish_failed",  # famille infra
    # États publiés (garde-fou si status check ne les attrape pas)
    "sure_mapping": "published",
    "sure": "published",
    "probable_bounded": "published",
}

# AC5 — Types HA compatibles V1 (light, cover, switch, sensor, binary_sensor)
_V1_COMPATIBLE_TYPES: frozenset = frozenset({"light", "cover", "switch", "sensor", "binary_sensor"})

# Mapping confidence interne → taxonomie architecture
_CONFIDENCE_CLOSED: dict = {
    "sure": "sure",
    "probable": "probable",
    "ambiguous": "ambiguous",
    "ignore": "ignore",
    "unknown": "ambiguous",
}


def _build_traceability(eq, map_result, pub_decision, status: str, top_reason_code: str) -> dict:
    """Construit l'objet traceability complet pour un équipement (AC1).

    Politique de présence : tableaux peuvent être vides [], objets jamais omis.
    """
    # Section 1 — Commandes observées
    observed_commands = [
        {"id": c.id, "name": c.name, "generic_type": c.generic_type}
        for c in eq.cmds
    ]

    # Section 2 — Typage Jeedom (depuis mapping.commands)
    typing_trace = []
    if map_result and map_result.commands:
        for role, cmd in map_result.commands.items():
            typing_trace.append({
                "logical_role": role,
                "command_id": cmd.id,
                "configured_type": cmd.generic_type,
                "used_type": cmd.generic_type,  # configuré = utilisé en V1
            })

    # Section 3 — Logique de décision (taxonomie fermée, Story 5.2 PE)
    # Source canonique : publication_decision_ref (étape 4) quand disponible,
    # fallback sur pub_decision pour compatibilité backward (tests directs, action handler).
    canonical_decision = (
        getattr(map_result, "publication_decision_ref", None) if map_result else None
    ) or pub_decision
    canonical_reason = getattr(canonical_decision, "reason", top_reason_code) if canonical_decision else top_reason_code

    if status == "Publié":
        closed_reason = "published"
    else:
        mapped = _CLOSED_REASON_MAP.get(canonical_reason)
        if mapped is not None:
            closed_reason = mapped
        elif map_result is not None:
            # Mapping trouvé mais décision non reconnue — conserver la cause canonique telle quelle
            closed_reason = canonical_reason
        else:
            # Aucun mapping, cause non reconnue → fallback conservateur
            closed_reason = "no_commands"

    if map_result:
        confidence_value = _CONFIDENCE_CLOSED.get(map_result.confidence, "ambiguous")
        ha_entity_type = map_result.ha_entity_type
    else:
        confidence_value = "ignore"
        ha_entity_type = None

    decision_trace = {
        "ha_entity_type": ha_entity_type,
        "confidence": confidence_value,
        "reason_code": closed_reason,
    }

    # Section 4 — Résultat de publication (Story 5.2 PE : lire depuis publication_result si disponible)
    pub_result_obj = getattr(map_result, "publication_result", None) if map_result else None
    if pub_result_obj is not None:
        pub_result = pub_result_obj.status  # "success" | "failed" | "not_attempted"
    elif status == "Publié":
        pub_result = "success"
    elif closed_reason == "discovery_publish_failed":
        pub_result = "failed"
    else:
        pub_result = "not_attempted"

    publication_trace: Dict[str, Any] = {
        "last_discovery_publish_result": pub_result,
        "last_publish_timestamp": None,  # non persisté en V1
    }
    # Exposer le technical_reason_code quand disponible (Story 5.2 PE — dimension technique)
    if pub_result_obj is not None and pub_result_obj.technical_reason_code:
        publication_trace["technical_reason_code"] = pub_result_obj.technical_reason_code

    # Section 5 — Projection validity (Story 7.1 — ajout additif pur, jamais omis)
    # Source : map_result.projection_validity tel que produit par validate_projection() à l'étape 3.
    # Invariant : projection_validity est uniquement lu, jamais recalculé ici.
    _pv = getattr(map_result, "projection_validity", None) if map_result else None
    if _pv is not None:
        projection_validity_bloc: dict = {
            "is_valid": _pv.is_valid,
            "reason_code": _pv.reason_code,
            "missing_fields": _pv.missing_fields,
            "missing_capabilities": _pv.missing_capabilities,
        }
    else:
        # Étape 3 non exécutée (inéligible, pas de mapping, ou pipeline arrêté avant) :
        # skip explicite documenté — jamais une absence implicite.
        # Reason_code canonique pipeline-contract : skipped_no_mapping_candidate.
        projection_validity_bloc = {
            "is_valid": None,
            "reason_code": "skipped_no_mapping_candidate",
            "missing_fields": [],
            "missing_capabilities": [],
        }

    return {
        "observed_commands": observed_commands,
        "typing_trace": typing_trace,
        "decision_trace": decision_trace,
        "publication_trace": publication_trace,
        "projection_validity": projection_validity_bloc,
    }


def _get_technical_publication_failure_reason(
    map_result: Optional[MappingResult],
    pub_decision: Optional[PublicationDecision],
) -> Optional[str]:
    """Return a technical publication failure reason when stage 5 failed."""
    pub_result_obj = getattr(map_result, "publication_result", None) if map_result else None
    if pub_result_obj is not None and pub_result_obj.status == "failed":
        return pub_result_obj.technical_reason_code or "discovery_publish_failed"
    # Legacy fallback: old runtime states may only carry infra reason on decision.
    if pub_decision and pub_decision.reason in ("discovery_publish_failed", "local_availability_publish_failed"):
        return pub_decision.reason
    return None


def _compute_pipeline_step_visible(el_result, map_result, pub_decision) -> int:
    """Retourne l'étape visible du pipeline canonique (1-5) pour un équipement.

    Ordre de priorité canonique : 1 → 2 → 3 → 4 → 5.
    Une étape aval ne remplace jamais une étape amont comme point de blocage.

    - 1 : inéligibilité (el_result absent ou is_eligible=False)
    - 2 : éligible mais pas de mapping
    - 3 : projection HA invalide (projection_validity.is_valid=False)
    - 4 : décision de publication bloquée (should_publish=False)
    - 5 : publication tentée (succès ou échec technique)

    I7 : technical_reason_code (étape 5) n'influence jamais cette valeur.
    """
    if el_result is None or not el_result.is_eligible:
        return 1
    if map_result is None:
        return 2
    pv = map_result.projection_validity
    if pv is not None and pv.is_valid is False:
        return 3
    canonical_dec = getattr(map_result, "publication_decision_ref", None) or pub_decision
    if canonical_dec is None or not canonical_dec.should_publish:
        return 4
    return 5


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

    # Story 4.1-fix — Lookup pour déterminer la présence HA réelle.
    # has_pending_home_assistant_changes est un XOR (desired != actual) : il ne
    # peut PAS servir de proxy de présence HA (terrain 2026-03-27 : 69 faux positifs).
    # Les vrais signaux sont publications[eq_id].active_or_alive et pending_discovery_unpublish.
    pending_discovery_unpublish = request.app.get("pending_discovery_unpublish") or {}

    equipments = []
    rooms_equips: dict = {}  # (object_id, object_name) -> list[dict]

    for eq_id, eq in topology.eq_logics.items():
        object_name = topology.get_suggested_area(eq_id) or "Aucun"

        status = get_primary_status("unknown")  # fallback — surchargé ci-dessous
        confidence = "Ignoré"
        reason_code = "unknown"
        matched_commands = []
        unmatched_commands = []
        map_result = None
        pub_decision = None

        el_result = eligibility.get(eq_id)
        if el_result:
            reason_code = el_result.reason_code
            if not el_result.is_eligible:
                status = get_primary_status(reason_code)
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
                        reason_code = pub_decision.reason
                        mapped_cmd_ids = {c.id for c in map_result.commands.values()}
                        coverable_cmds = [c for c in eq.cmds if c.generic_type]
                        unmapped_cmds = [c for c in coverable_cmds if c.id not in mapped_cmd_ids]

                        matched_commands = [
                            {
                                "cmd_id": c.id,
                                "cmd_name": c.name,
                                "generic_type": c.generic_type,
                            }
                            for c in eq.cmds if c.id in mapped_cmd_ids
                        ]
                        if unmapped_cmds:
                            unmatched_commands = [
                                {
                                    "cmd_id": c.id,
                                    "cmd_name": c.name,
                                    "generic_type": c.generic_type,
                                }
                                for c in unmapped_cmds
                            ]
                        status = get_primary_status(reason_code)
                    else:
                        if pub_decision:
                            # Story 5.2 PE : reason_code = cause décisionnelle canonique (étapes 1–4)
                            # Le résultat technique (étape 5) ne remplace jamais la cause principale.
                            canonical_dec = (
                                getattr(map_result, "publication_decision_ref", None) if map_result else None
                            ) or pub_decision
                            reason_code = canonical_dec.reason
                            # En diagnostic global, un échec technique de l'étape 5 reste prioritaire
                            # pour la remédiation opératoire (infra MQTT).
                            technical_failure_reason = _get_technical_publication_failure_reason(
                                map_result,
                                pub_decision,
                            )
                            if technical_failure_reason:
                                reason_code = technical_failure_reason
                        status = get_primary_status(reason_code)
                else:
                    reason_code = "no_mapping"
                    confidence = "Ignoré"
                    status = get_primary_status(reason_code)

        # Enrich with human-readable detail and remediation
        if status == "Publié":
            detail = ""
            remediation = ""
            v1_limitation = False
        else:
            detail, remediation, v1_limitation = _get_diagnostic_enrichment(reason_code)

        # Collect detected generic_types for actionable diagnosis (no_supported_generic_type, ambiguous_skipped)
        detected_generic_types: list = []
        if reason_code in ("no_supported_generic_type", "ambiguous_skipped"):
            seen: set = set()
            for c in eq.cmds:
                if c.generic_type:
                    if c.generic_type not in seen:
                        seen.add(c.generic_type)
                        detected_generic_types.append(c.generic_type)
                unmatched_commands.append({
                    "cmd_id": c.id,
                    "cmd_name": c.name,
                    "generic_type": c.generic_type,
                })

        # AC5 — v1_compatibility: True si ha_entity_type dans le périmètre V1
        v1_compatibility = (
            map_result is not None
            and map_result.ha_entity_type in _V1_COMPATIBLE_TYPES
        )

        # AC1 — Traceability: chaîne de décision complète
        traceability = _build_traceability(eq, map_result, pub_decision, status, reason_code)
        # Story 6.1 — Étape visible du pipeline (1-5), calculée backend-first.
        # Lecture stricte côté frontend — ne jamais recalculer localement.
        pipeline_step_visible = _compute_pipeline_step_visible(el_result, map_result, pub_decision)
        # Story 6.2 — source canonique UX : decision_trace.reason_code + pipeline_step_visible.
        decision_reason_code = (
            traceability.get("decision_trace", {}).get("reason_code")
            if isinstance(traceability, dict)
            else None
        ) or ""

        # Story 4.4 — code machine stable pour l'export de diagnostic
        status_code = _STATUS_CODE_MAP.get(status, "not_published")

        # Story 4.1-fix — Contrat UI canonique 4D (additif — couche technique preservée ci-dessous)
        # statut reflète la présence HA réelle via publications + pending_discovery_unpublish,
        # PAS via has_pending_home_assistant_changes (XOR ambigü — voir diagnostic terrain).
        _pub = publications.get(eq_id)
        is_published_in_ha = bool(_pub and _pub.active_or_alive) or eq_id in pending_discovery_unpublish
        perimetre = reason_code_to_perimetre(reason_code)
        statut = "publie" if is_published_in_ha else "non_publie"
        ecart = compute_ecart(perimetre, statut)
        if ecart and perimetre == "inclus":
            cause_code, _, _ = reason_code_to_cause(reason_code)
            cause_ux = resolve_cause_ux(decision_reason_code, pipeline_step_visible)
            cause_label = cause_ux["cause_label"]
            cause_action = cause_ux["cause_action"]
        elif ecart and perimetre.startswith("exclu_"):
            cause_code, cause_label, cause_action = build_cause_for_pending_unpublish()
        else:
            cause_code, cause_label, cause_action = None, None, None
        ha_type = map_result.ha_entity_type if map_result else None

        # Story 5.1 — Signal actions_ha par équipement (AC 2, 3, 4, 5)
        # Le signal n'est généré que pour les équipements inclus.
        # est_publie_ha = is_published_in_ha (déjà calculé au-dessus).
        est_inclus = (perimetre == "inclus")
        # Story 5.6 — est_publiable : True uniquement si le pipeline a produit pub_decision.should_publish=True.
        # pub_decision=None → inéligible ou non-mappé → non publiable.
        # pub_decision.should_publish=False → ambiguous_skipped, probable_skipped, disabled_eqlogic → non publiable.
        est_publiable = bool(pub_decision and getattr(pub_decision, 'should_publish', False))
        mqtt_bridge = request.app.get("mqtt_bridge")
        bridge_ok = bool(mqtt_bridge and mqtt_bridge.is_connected)
        if est_inclus:
            actions_ha = build_actions_ha(
                est_publie_ha=is_published_in_ha,
                est_inclus=True,
                bridge_disponible=bridge_ok,
                est_publiable=est_publiable,
            )
        else:
            actions_ha = None

        eq_dict = {
            "eq_id": eq_id,
            "object_name": object_name,
            "name": eq.name,
            "eq_type_name": eq.eq_type_name,
            # Contrat UI canonique 4D (Story 4.1)
            "perimetre": perimetre,
            "statut": statut,
            "ecart": ecart,
            "cause_code": cause_code,
            "cause_label": cause_label,
            "cause_action": cause_action,
            "ha_type": ha_type,
            # Story 5.1 — Signal actions_ha (None si non inclus)
            "actions_ha": actions_ha,
            # Couche technique / support (backward compat — ne jamais supprimer)
            "status": status,
            "status_code": status_code,
            "confidence": confidence,
            "reason_code": reason_code,
            "detail": detail,
            "remediation": remediation,
            "v1_limitation": v1_limitation,
            "matched_commands": matched_commands,
            "unmatched_commands": unmatched_commands,
            "detected_generic_types": detected_generic_types,
            "v1_compatibility": v1_compatibility,
            "traceability": traceability,
            # Story 6.1 — Étape visible du pipeline (1-5), calculée backend-first.
            # Lecture stricte côté frontend — ne jamais recalculer localement.
            "pipeline_step_visible": pipeline_step_visible,
        }
        equipments.append(eq_dict)
        room_key = (eq.object_id, object_name)
        rooms_equips.setdefault(room_key, []).append(eq_dict)

    summary = build_summary(equipments)
    summary["compteurs"] = build_ui_counters(equipments)
    summary["home_statut"] = compute_home_statut(equipments)
    rooms = []
    for (object_id, object_name_val), room_eqs in rooms_equips.items():
        room_summary = build_summary(room_eqs)
        rooms.append({
            "object_id": object_id,
            "object_name": object_name_val,
            "summary": room_summary,
            "compteurs": build_ui_counters(room_eqs),
            "home_statut": compute_home_statut(room_eqs),
        })

    # Story 4.3 — Surface filtrée in-scope : équipements avec perimetre == "inclus" uniquement.
    # Filtre de population en sortie — ne modifie pas le pipeline ni le resolver canonique.
    in_scope_equipments = [eq for eq in equipments if eq.get("perimetre") == "inclus"]

    # Story 4.3 — Surface filtrée in-scope : équipements avec perimetre == "inclus" uniquement.
    # Filtre de population en sortie — ne modifie pas le pipeline ni le resolver canonique.
    in_scope_equipments = [eq for eq in equipments if eq.get("perimetre") == "inclus"]

    return web.json_response({
        "action": "system.diagnostics",
        "status": "ok",
        "payload": {
            "summary": summary,
            "rooms": rooms,
            "equipments": equipments,
            "in_scope_equipments": in_scope_equipments,
        },
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def _handle_system_published_scope(request: web.Request) -> web.Response:
    """Handle GET /system/published_scope — return canonical backend scope contract."""
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response(
            {"status": "error", "message": "Unauthorized"},
            status=401,
        )

    published_scope = request.app.get("published_scope")
    if not published_scope:
        return web.json_response({
            "status": "error",
            "message": "Contrat published_scope indisponible : appelez /action/sync d'abord.",
        })

    return web.json_response({
        "action": "system.published_scope",
        "status": "ok",
        "payload": published_scope,
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })



# ---------------------------------------------------------------------------
# Story 5.1 — Façade backend unique d'opérations HA
# ---------------------------------------------------------------------------

_INTENTIONS_VALIDES = frozenset(("publier", "supprimer"))
_PORTEES_VALIDES = frozenset(("global", "piece", "equipement"))


async def _handle_action_execute(request: web.Request) -> web.Response:
    """Handle POST /action/execute — façade unique des opérations HA.

    Paramètres attendus (JSON body) :
      intention : 'publier' | 'supprimer'
      portee    : 'global' | 'piece' | 'equipement'
      selection : liste non vide d'identifiants cible

    Story 5.1 = socle contractuel. L'exécution réelle est Story 5.2 (publier) / 5.3 (supprimer).
    La façade valide et accepte les appels mais retourne 'non_implemente' pour l'exécution.
    """
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response(
            {"status": "error", "message": "Unauthorized"},
            status=401,
        )

    try:
        raw_body = await request.json()
    except Exception:
        return web.json_response(
            {"status": "error", "message": "Corps de requête JSON invalide."},
            status=400,
        )

    body = _normalize_action_execute_body(raw_body)
    intention = body.get("intention")
    portee = body.get("portee")
    selection = body.get("selection")

    # Validation — intention
    if intention not in _INTENTIONS_VALIDES:
        return web.json_response(
            {
                "status": "error",
                "message": f"Intention non reconnue : '{intention}'. Valeurs acceptées : {', '.join(sorted(_INTENTIONS_VALIDES))}.",
            },
            status=400,
        )

    # Validation — portée
    if portee not in _PORTEES_VALIDES:
        return web.json_response(
            {
                "status": "error",
                "message": f"Portée non reconnue : '{portee}'. Valeurs acceptées : {', '.join(sorted(_PORTEES_VALIDES))}.",
            },
            status=400,
        )

    # Validation — sélection non vide
    if not selection or not isinstance(selection, list) or len(selection) == 0:
        return web.json_response(
            {
                "status": "error",
                "message": "Le champ 'selection' est obligatoire et doit être une liste non vide.",
            },
            status=400,
        )

    topology = request.app.get("topology")
    published_scope = request.app.get("published_scope")
    if topology is None or published_scope is None:
        return _build_action_execute_response(
            payload={
                "intention": intention,
                "portee": portee,
                "selection": selection,
                "resultat": "echec",
                "message": "Aucune synchronisation disponible. Lancez une synchronisation d'abord.",
                "perimetre_impacte": {
                    "nom": "Parc global" if portee == "global" else ("Pièce" if portee == "piece" else "Équipement"),
                    "equipements_inclus": 0,
                },
                "scope_reel": {
                    "equipements_inclus": 0,
                    "equipements_publies_ou_crees": 0,
                    "ecarts_resolus": 0,
                    "skips": 0,
                },
                "aucun_flux_supprimer_recree": True,
            },
            http_status=409,
            top_status="error",
        )

    mqtt_bridge = request.app.get("mqtt_bridge")
    if not mqtt_bridge or not mqtt_bridge.is_connected:
        return _build_action_execute_response(
            payload={
                "intention": intention,
                "portee": portee,
                "selection": selection,
                "resultat": "echec",
                "message": "L'action n'a pas pu être exécutée. Vérifiez la connexion Home Assistant.",
                "perimetre_impacte": _build_action_perimetre_impacte(
                    portee=portee,
                    selection=selection,
                    topology=topology,
                    eq_ids=[],
                    equipements_inclus=0,
                ),
                "scope_reel": {
                    "equipements_inclus": 0,
                    "equipements_publies_ou_crees": 0,
                    "ecarts_resolus": 0,
                    "skips": 0,
                },
                "aucun_flux_supprimer_recree": True,
            },
            http_status=503,
            top_status="error",
        )

    try:
        eq_ids = list(dict.fromkeys(_resolve_eq_ids_for_portee(portee, selection, topology)))
    except ValueError as exc:
        return web.json_response(
            {"status": "error", "message": str(exc)},
            status=400,
        )

    eligibility = request.app.get("eligibility") or {}
    mappings = request.app.get("mappings") or {}
    publications = request.app.get("publications")
    if publications is None:
        publications = {}
        request.app["publications"] = publications
    pending_discovery_unpublish = request.app.get("pending_discovery_unpublish")
    if pending_discovery_unpublish is None:
        pending_discovery_unpublish = {}
        request.app["pending_discovery_unpublish"] = pending_discovery_unpublish
    pending_local_cleanup = request.app.get("pending_local_availability_cleanup")
    if pending_local_cleanup is None:
        pending_local_cleanup = {}
        request.app["pending_local_availability_cleanup"] = pending_local_cleanup

    # --- Branche supprimer (Story 5.3) ---
    if intention == "supprimer":
        publisher = DiscoveryPublisher(mqtt_bridge)
        equipements_supprimes = 0
        supprimer_errors = 0
        skips = 0
        _action_delay = max(0.1, 10.0 / max(1, len(eq_ids)))

        for eq_id in eq_ids:
            previous_decision = publications.get(eq_id)

            if not _is_currently_published_in_ha(eq_id, previous_decision, pending_discovery_unpublish):
                skips += 1
                continue

            if previous_decision and previous_decision.mapping_result is not None:
                entity_type = previous_decision.mapping_result.ha_entity_type
            elif mappings.get(eq_id) is not None:
                entity_type = mappings[eq_id].ha_entity_type
            else:
                entity_type = "light"

            unpublish_ok = await publisher.unpublish_by_eq_id(eq_id, entity_type=entity_type)
            await asyncio.sleep(_action_delay)
            if not unpublish_ok:
                _defer_discovery_unpublish(pending_discovery_unpublish, eq_id, entity_type)
                supprimer_errors += 1
                continue

            pending_discovery_unpublish.pop(eq_id, None)

            previous_local_supported = bool(getattr(previous_decision, "local_availability_supported", False))
            previous_local_topic = getattr(previous_decision, "eqlogic_availability_topic", None)
            pending_local_topic = pending_local_cleanup.get(eq_id)
            if previous_local_supported or previous_local_topic or pending_local_topic:
                clear_ok = _clear_local_availability_topic(
                    mqtt_bridge,
                    eq_id,
                    previous_local_topic or pending_local_topic,
                )
                if clear_ok:
                    pending_local_cleanup.pop(eq_id, None)
                else:
                    _defer_local_availability_cleanup(
                        pending_local_cleanup,
                        eq_id,
                        previous_local_topic or pending_local_topic,
                    )
            else:
                pending_local_cleanup.pop(eq_id, None)

            if previous_decision and previous_decision.mapping_result is not None:
                publications[eq_id] = PublicationDecision(
                    should_publish=False,
                    reason=getattr(previous_decision, "reason", "excluded"),
                    mapping_result=previous_decision.mapping_result,
                    state_topic=previous_decision.state_topic,
                    active_or_alive=False,
                    discovery_published=False,
                    bridge_availability_topic=previous_decision.bridge_availability_topic,
                    eqlogic_availability_topic=previous_decision.eqlogic_availability_topic,
                    local_availability_supported=previous_decision.local_availability_supported,
                    local_availability_state=previous_decision.local_availability_state,
                    availability_reason=previous_decision.availability_reason,
                )
            elif mappings.get(eq_id) is not None:
                mapping = mappings[eq_id]
                resolved_decision = PublicationDecision(
                    should_publish=False,
                    reason="excluded",
                    mapping_result=mapping,
                    state_topic=_resolve_state_topic(mapping),
                    active_or_alive=False,
                    discovery_published=False,
                )
                _apply_availability_metadata(resolved_decision, mapping, topology)
                publications[eq_id] = resolved_decision

            equipements_supprimes += 1

        if supprimer_errors > 0 and equipements_supprimes == 0:
            resultat = "echec"
        elif supprimer_errors > 0 and equipements_supprimes > 0:
            resultat = "succes_partiel"
        else:
            resultat = "succes"

        perimetre = _build_action_perimetre_impacte(
            portee=portee,
            selection=selection,
            topology=topology,
            eq_ids=eq_ids,
            equipements_inclus=len(eq_ids),
        )

        request.app["published_scope"] = _apply_pending_scope_flags(
            published_scope,
            publications,
            pending_discovery_unpublish,
        )
        save_publications_cache(publications, _DATA_DIR)
        _supprimer_msg = _build_supprimer_message(
            resultat=resultat,
            equipements_supprimes=equipements_supprimes,
            supprimer_errors=supprimer_errors,
        )
        request.app["derniere_operation_resultat"] = _build_operation_snapshot(
            resultat="partiel" if resultat == "succes_partiel" else resultat,
            intention="supprimer",
            portee=portee,
            message=_supprimer_msg,
            volume=equipements_supprimes,
        )

        payload = {
            "intention": intention,
            "portee": portee,
            "selection": selection,
            "resultat": resultat,
            "message": _supprimer_msg,
            "perimetre_impacte": {
                "nom": perimetre["nom"],
                "equipements_publies": equipements_supprimes + supprimer_errors + skips,
            },
            "scope_reel": {
                "equipements_supprimes": equipements_supprimes,
                "supprimer_errors": supprimer_errors,
                "skips": skips,
            },
        }
        return _build_action_execute_response(payload=payload)

    # --- Branche publier (Story 5.2) ---
    scope_entries = {
        _to_int(entry.get("eq_id"), default=0): entry
        for entry in published_scope.get("equipements", [])
    }
    publisher = DiscoveryPublisher(mqtt_bridge)

    equipements_inclus = 0
    equipements_publies_ou_crees = 0
    ecarts_resolus = 0
    skips = 0
    publish_errors = 0
    _action_delay = max(0.1, 10.0 / max(1, len(eq_ids)))

    for eq_id in eq_ids:
        scope_entry = scope_entries.get(eq_id)
        mapping = mappings.get(eq_id)
        previous_decision = publications.get(eq_id)
        is_included = _scope_entry_is_included(eq_id, scope_entry, eligibility)

        if is_included:
            equipements_inclus += 1
            pending_discovery_unpublish.pop(eq_id, None)
            pending_local_cleanup.pop(eq_id, None)

            if not _should_attempt_publish(mapping, previous_decision):
                skips += 1
                continue

            publish_ok = await _publish_mapping_for_action(publisher, mapping, topology)
            await asyncio.sleep(_action_delay)
            if not publish_ok:
                failed_decision = PublicationDecision(
                    should_publish=False,
                    reason="discovery_publish_failed",
                    mapping_result=mapping,
                    state_topic=_resolve_state_topic(mapping),
                    active_or_alive=False,
                    discovery_published=False,
                )
                _apply_availability_metadata(failed_decision, mapping, topology)
                publications[eq_id] = failed_decision
                publish_errors += 1
                continue

            publish_reason = getattr(previous_decision, "reason", "") if previous_decision else ""
            if publish_reason in (
                "",
                "discovery_publish_failed",
                "local_availability_publish_failed",
                "ambiguous_skipped",
                "probable_skipped",
                "unknown_skipped",
                "ignore_skipped",
            ):
                publish_reason = mapping.confidence

            decision = PublicationDecision(
                should_publish=True,
                reason=publish_reason,
                mapping_result=mapping,
                state_topic=_resolve_state_topic(mapping),
                active_or_alive=False,
                discovery_published=True,
            )
            _apply_availability_metadata(decision, mapping, topology)

            local_ok = True
            if decision.local_availability_supported:
                local_ok = _publish_local_availability_state(mqtt_bridge, eq_id, decision)

            if not local_ok:
                publications[eq_id] = _mark_local_availability_publish_failed(decision, mapping)
                publish_errors += 1
                continue

            decision.active_or_alive = True
            publications[eq_id] = decision
            equipements_publies_ou_crees += 1
            continue

        if not _is_currently_published_in_ha(eq_id, previous_decision, pending_discovery_unpublish):
            continue

        if previous_decision and previous_decision.mapping_result is not None:
            entity_type = previous_decision.mapping_result.ha_entity_type
        elif mapping is not None:
            entity_type = mapping.ha_entity_type
        else:
            entity_type = "light"

        unpublish_ok = await publisher.unpublish_by_eq_id(eq_id, entity_type=entity_type)
        await asyncio.sleep(_action_delay)
        if not unpublish_ok:
            _defer_discovery_unpublish(pending_discovery_unpublish, eq_id, entity_type)
            continue

        pending_discovery_unpublish.pop(eq_id, None)

        previous_local_supported = bool(getattr(previous_decision, "local_availability_supported", False))
        previous_local_topic = getattr(previous_decision, "eqlogic_availability_topic", None)
        pending_local_topic = pending_local_cleanup.get(eq_id)
        if previous_local_supported or previous_local_topic or pending_local_topic:
            clear_ok = _clear_local_availability_topic(
                mqtt_bridge,
                eq_id,
                previous_local_topic or pending_local_topic,
            )
            if clear_ok:
                pending_local_cleanup.pop(eq_id, None)
            else:
                _defer_local_availability_cleanup(
                    pending_local_cleanup,
                    eq_id,
                    previous_local_topic or pending_local_topic,
                )
        else:
            pending_local_cleanup.pop(eq_id, None)

        if previous_decision and previous_decision.mapping_result is not None:
            publications[eq_id] = PublicationDecision(
                should_publish=False,
                reason=getattr(previous_decision, "reason", "excluded"),
                mapping_result=previous_decision.mapping_result,
                state_topic=previous_decision.state_topic,
                active_or_alive=False,
                discovery_published=False,
                bridge_availability_topic=previous_decision.bridge_availability_topic,
                eqlogic_availability_topic=previous_decision.eqlogic_availability_topic,
                local_availability_supported=previous_decision.local_availability_supported,
                local_availability_state=previous_decision.local_availability_state,
                availability_reason=previous_decision.availability_reason,
            )
        elif mapping is not None:
            resolved_decision = PublicationDecision(
                should_publish=False,
                reason="excluded",
                mapping_result=mapping,
                state_topic=_resolve_state_topic(mapping),
                active_or_alive=False,
                discovery_published=False,
            )
            _apply_availability_metadata(resolved_decision, mapping, topology)
            publications[eq_id] = resolved_decision

        ecarts_resolus += 1

    if publish_errors > 0 and equipements_publies_ou_crees == 0:
        resultat = "echec"
    elif publish_errors > 0 and equipements_publies_ou_crees > 0:
        resultat = "succes_partiel"
    else:
        resultat = "succes"

    request.app["published_scope"] = _apply_pending_scope_flags(
        published_scope,
        publications,
        pending_discovery_unpublish,
    )
    save_publications_cache(publications, _DATA_DIR)
    _publier_msg = _build_publier_message(
        resultat=resultat,
        equipements_publies_ou_crees=equipements_publies_ou_crees,
        publish_errors=publish_errors,
    )
    request.app["derniere_operation_resultat"] = _build_operation_snapshot(
        resultat="partiel" if resultat == "succes_partiel" else resultat,
        intention="publier",
        portee=portee,
        message=_publier_msg,
        volume=equipements_publies_ou_crees,
    )

    payload = {
        "intention": intention,
        "portee": portee,
        "selection": selection,
        "resultat": resultat,
        "message": _publier_msg,
        "perimetre_impacte": _build_action_perimetre_impacte(
            portee=portee,
            selection=selection,
            topology=topology,
            eq_ids=eq_ids,
            equipements_inclus=equipements_inclus,
        ),
        "scope_reel": {
            "equipements_inclus": equipements_inclus,
            "equipements_publies_ou_crees": equipements_publies_ou_crees,
            "ecarts_resolus": ecarts_resolus,
            "skips": skips,
        },
        "aucun_flux_supprimer_recree": True,
    }
    return _build_action_execute_response(payload=payload)


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
    app["published_scope"] = None  # Dict[str, Any] | None — canonical contract populated on sync
    app["pending_discovery_unpublish"] = {}  # Dict[int, str]
    app["pending_local_availability_cleanup"] = {}  # Dict[int, str]
    
    # Story 2.1 — Etat minimal de santé du pont
    app["derniere_operation_resultat"] = _build_operation_snapshot(resultat="aucun")
    app["derniere_synchro_terminee"] = None

    # Story 5.1 — Warm-start cache (populated in on_start() before HTTP server starts)
    app["boot_cache"] = {}       # Dict[int, dict] — chargé du disque au boot, purgé après 1er sync
    app["boot_sync_received"] = None  # asyncio.Event — initialisé dans on_start()
    app.router.add_get("/system/status", _handle_system_status)
    app.router.add_post("/action/mqtt_test", _handle_mqtt_test)
    app.router.add_post("/action/mqtt_connect", _handle_mqtt_connect)
    app.router.add_post("/action/sync", _handle_action_sync)
    app.router.add_get("/system/diagnostics", _handle_system_diagnostics)
    app.router.add_get("/system/published_scope", _handle_system_published_scope)
    # Story 5.1 — Façade backend unique des opérations HA
    app.router.add_post("/action/execute", _handle_action_execute)
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
