"""Local HTTP API server for PHP → daemon communication.

Listens on 127.0.0.1 only, protected by a local_secret shared with the PHP plugin.
"""

import asyncio
import dataclasses
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
from models.topology import TopologySnapshot, assess_all, assess_eligibility
from models.published_scope import resolve_published_scope
from models.decide_publication import (
    DEFAULT_CONFIDENCE_POLICY,
    VALID_CONFIDENCE_POLICIES,
    decide_publication,
)
from models.evaluate_equipment import evaluate_equipment, merge_override_layer
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
from mapping.registry import MapperRegistry, resolve_expected_ha
from mapping.button import ScenarioButtonMapper
from mapping.overrides import (
    apply_type_override,
    list_equipment_overrides,
    list_overrides,
    mapping_cmd_ids,
    parse_override_key,
    remove_equipment_override,
    remove_override,
    resolve_publication_override,
    save_override,
)
from discovery.publisher import DiscoveryPublisher
from discovery.registry import PublisherRegistry
from cache.disk_cache import save_publications_cache
from validation.ha_component_registry import validate_projection

# Résoudre le répertoire data/ relatif à ce fichier (data/ est un sibling de resources/)
_HTTP_SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.normpath(os.path.join(_HTTP_SERVER_DIR, "..", "..", "..", "data"))

_LOGGER = logging.getLogger(__name__)

_VERSION = "0.2.0"

_MAPPING_COUNTER_BUCKETS = ("sure", "probable", "ambiguous", "published", "skipped")

# Story 19.3 (P3, relecture ClaudeBox PR #176 tour 2) — alias local vers la source unique
# (`models/decide_publication.py`), pour ne pas réécrire tous les appelants internes de ce
# module. Avant ce correctif, `_DEFAULT_CONFIDENCE_POLICY` était défini ICI en dur alors que
# `evaluate_equipment()` et `decide_publication()` gardaient encore le même littéral
# `"sure_probable"` dupliqué chacun de leur côté — un risque de divergence silencieuse si
# l'un changeait sans les autres.
_DEFAULT_CONFIDENCE_POLICY = DEFAULT_CONFIDENCE_POLICY
_VALID_CONFIDENCE_POLICIES = VALID_CONFIDENCE_POLICIES


def _check_secret(request: web.Request, local_secret: str) -> bool:
    """Validate the local_secret from request header."""
    provided = request.headers.get("X-Local-Secret", "")
    if not provided or not local_secret:
        return False
    return provided == local_secret


# Types without state_topic: command-only entities (no persistent state in HA).
# Extended when new command-only types are added to PublisherRegistry.
_TYPES_WITHOUT_STATE_TOPIC = {"button"}


def _resolve_state_topic(mapping: MappingResult) -> str:
    """Resolve runtime state topic for a published actuator mapping."""
    if (mapping.ha_entity_type in PublisherRegistry.known_types()
            and mapping.ha_entity_type not in _TYPES_WITHOUT_STATE_TOPIC):
        reason_details = mapping.reason_details or {}
        state_topic = reason_details.get("state_topic")
        if mapping.ha_entity_type == "switch" and isinstance(state_topic, str) and state_topic:
            return state_topic
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


def _resolve_publication_override_for_mapping(
    mapping: MappingResult,
    overrides_cache: Dict[str, dict],
    equipment_overrides_cache: Dict[str, dict],
) -> Optional[str]:
    """Resolve `publication_override` for a mapping (Story 16.3, AC1/AC2).

    Thin wrapper around `resolve_publication_override(eq_id, cmd_id, ...)` : the equipment-level
    rules (exclusion veto, force_publish default) don't depend on `cmd_id`, but the low-level
    function still expects one — so this loops `mapping_cmd_ids(mapping)` (same deterministic
    first-match order as `apply_type_override`) and falls back to a sentinel `-1` (never a real
    Jeedom cmd_id) when a mapping carries none, so equipment-level checks still run.
    """
    eq_id = mapping.jeedom_eq_id
    for cmd_id in mapping_cmd_ids(mapping) or [-1]:
        override = resolve_publication_override(
            eq_id, cmd_id, overrides_cache, equipment_overrides_cache
        )
        if override is not None:
            return override
    return None


async def _publish_additional_sensors(
    *,
    primary_mapping: MappingResult,
    secondary_decisions: list[PublicationDecision],
    snapshot: TopologySnapshot,
    publisher_registry: Optional[PublisherRegistry],
    mqtt_bridge,
    mapping_counters: Dict[str, int],
) -> None:
    """Publier les sensors secondaires d'un eqLogic multi-sensor (Story 11.1 PE).

    Les décisions secondaires sont celles déjà produites par `evaluate_equipment()` :
    cette étape ne doit surtout pas rejouer validation/override/décision en parallèle.
    Elle ne fait que la publication technique et alimente les compteurs.
    Honnêteté du diagnostic : si un secondaire devant être publié échoue, le résultat
    technique du mapping primaire passe à "failed" pour ne pas afficher un faux succès.

    """
    bridge_ready = bool(mqtt_bridge and getattr(mqtt_bridge, "is_connected", False))
    eq_id = primary_mapping.jeedom_eq_id

    secondaries = primary_mapping.additional_mappings or []
    if len(secondaries) != len(secondary_decisions):
        raise RuntimeError(
            "Contrat evaluate_equipment invalide : nombre de décisions secondaires différent "
            "du nombre de mappings secondaires"
        )

    for secondary, sec_decision in zip(secondaries, secondary_decisions):
        if sec_decision.mapping_result is not secondary:
            raise RuntimeError(
                "Contrat evaluate_equipment invalide : décision secondaire sans mapping identique"
            )

        # P2 fix (ClaudeBox review, 3a408db) : `active_or_alive` vaut True par défaut
        # (models/mapping.py) et n'était jamais remis à False avant la tentative — un
        # secondaire dont la discovery a échoué restait donc routé. Même modèle que
        # `_prepare_publication_bookkeeping` pour le principal : False avant tentative
        # (y compris pour un secondaire refusé), True seulement en cas de succès.
        sec_decision.active_or_alive = False

        if secondary.confidence in ("sure", "probable", "ambiguous"):
            _increment_mapping_counter(mapping_counters, secondary, secondary.confidence)

        if not sec_decision.should_publish:
            secondary.publication_result = _make_publication_result("not_attempted")
            secondary.pipeline_step_reached = 5
            continue

        published = False
        if publisher_registry and bridge_ready:
            published = await publisher_registry.publish(secondary, snapshot)
        else:
            _LOGGER.warning(
                "[MAPPING] Discovery publish unavailable for eq_id=%d sensor cmd=%s (bridge missing/disconnected)",
                eq_id, (secondary.reason_details or {}).get("cmd_id"),
            )

        if published:
            sec_decision.discovery_published = True
            sec_decision.active_or_alive = True
            secondary.publication_result = _make_publication_result("success")
            _increment_mapping_counter(mapping_counters, secondary, "published")
        else:
            if secondary.publication_result is None:
                secondary.publication_result = _make_publication_result(
                    "failed", "discovery_publish_failed"
                )
            # Diagnostic honnête : un secondaire raté invalide le succès global de l'eqLogic.
            if primary_mapping.publication_result is not None and (
                primary_mapping.publication_result.status == "success"
            ):
                primary_mapping.publication_result = _make_publication_result(
                    "failed", "multi_sensor_partial_publish_failed"
                )
        secondary.pipeline_step_reached = 5


def _mapping_counter_prefix(ha_entity_type: str) -> str:
    """Return the legacy-compatible summary prefix for one HA entity type."""
    if ha_entity_type.endswith(("s", "x", "ch", "sh")):
        return f"{ha_entity_type}es"
    return f"{ha_entity_type}s"


def _mapping_counter_key(ha_entity_type: str, bucket: str) -> str:
    return f"{_mapping_counter_prefix(ha_entity_type)}_{bucket}"


def _build_mapping_counters_from_publisher_registry(
    publisher_registry: Optional[PublisherRegistry] = None,
) -> Dict[str, int]:
    """Build mapping counters from registered discovery publisher entity types."""
    if publisher_registry is not None:
        ha_entity_types = publisher_registry.publishers.keys()
    else:
        ha_entity_types = PublisherRegistry.known_types()
    return {
        _mapping_counter_key(ha_entity_type, bucket): 0
        for ha_entity_type in ha_entity_types
        for bucket in _MAPPING_COUNTER_BUCKETS
    }


def _increment_mapping_counter(
    counters: Dict[str, int],
    mapping: MappingResult,
    bucket: str,
) -> None:
    key = _mapping_counter_key(mapping.ha_entity_type, bucket)
    if key in counters:
        counters[key] += 1


def _mapping_counter_prefixes(counters: Dict[str, int]) -> list[str]:
    prefixes: list[str] = []
    for key in counters.keys():
        for bucket in _MAPPING_COUNTER_BUCKETS:
            suffix = f"_{bucket}"
            if key.endswith(suffix):
                prefix = key[: -len(suffix)]
                if prefix not in prefixes:
                    prefixes.append(prefix)
                break
    return prefixes


def _format_mapping_counter_summary(counters: Dict[str, int]) -> str:
    groups = []
    for prefix in _mapping_counter_prefixes(counters):
        group = " ".join(
            f"{bucket}={counters.get(f'{prefix}_{bucket}', 0)}"
            for bucket in _MAPPING_COUNTER_BUCKETS
        )
        groups.append(f"{prefix}({group})")
    return " ".join(groups)


def _prepare_publication_bookkeeping(
    eq_id: int,
    mapping: MappingResult,
    decision: PublicationDecision,
    snapshot: TopologySnapshot,
    publications: Dict[int, PublicationDecision],
    nouveaux_eq_ids: set[int],
) -> None:
    """Populate common runtime publication bookkeeping before discovery publish."""
    decision.state_topic = _resolve_state_topic(mapping)
    decision.active_or_alive = False
    _apply_availability_metadata(decision, mapping, snapshot)
    publications[eq_id] = decision
    nouveaux_eq_ids.add(eq_id)


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


def _scope_excluded_decision(
    mapping: MappingResult,
    topology: TopologySnapshot,
) -> PublicationDecision:
    """Story 19.4 (AC3) — décision d'un équipement exclu par le filtre de scope.

    Le filtre de scope (`_scope_entry_is_included`) s'applique APRÈS la décision
    (`evaluate_equipment()`), dans le sync comme dans « Publier » : un équipement hors
    périmètre publié n'est jamais publié, quelle que soit la décision de mapping. Le
    principal est refusé (`excluded`) et l'état d'exécution des secondaires est remis à
    « non publié » (leur verdict d'étape 4 reste intact, cf. `_sync_publication_decision_refs`).
    """
    decision = PublicationDecision(
        should_publish=False,
        reason="excluded",
        mapping_result=mapping,
        state_topic=_resolve_state_topic(mapping),
        active_or_alive=False,
        discovery_published=False,
    )
    _apply_availability_metadata(decision, mapping, topology)
    _sync_publication_decision_refs(mapping, decision)
    return decision


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


def _secondary_publishable(secondary: MappingResult) -> bool:
    """Return True when the secondary's step-4 verdict (``evaluate_equipment``,
    last full sync) allows publication.

    P1-bis fix (ClaudeBox review round 2, PR #174) — ``should_publish``/``reason``
    are the step-4 verdict and are never written by an action anymore (see
    ``_reset_secondary_runtime_state``), so this keeps reading the true verdict
    from the last full sync even after a "supprimer" action has turned the
    secondary's runtime state (``discovery_published``/``active_or_alive``) off.
    In the absence of any decision (never synced), the secondary must not be
    (re)published outside of a full sync — an unknown decision is treated as
    refused, never as an implicit allow.
    """
    decision_ref = getattr(secondary, "publication_decision_ref", None)
    return bool(decision_ref is not None and getattr(decision_ref, "should_publish", False))


def _reset_secondary_runtime_state(
    secondary: MappingResult,
    *,
    discovery_published: bool,
    active_or_alive: bool = False,
) -> PublicationDecision:
    """Update ONLY the runtime state (``discovery_published``/``active_or_alive``)
    of one secondary mapping's ``publication_decision_ref``, via a fresh
    ``dataclasses.replace()`` copy (never mutates the previous decision object in
    place — other consumers may still hold a reference to it), then repoints the
    secondary's ref to that copy.

    P1-bis fix (ClaudeBox review round 2, PR #174) — ``should_publish`` and
    ``reason`` are the step-4 verdict (``evaluate_equipment``, full sync only)
    and must NEVER be touched by an action: an earlier version of this helper
    forced ``should_publish=False`` on every secondary during "supprimer", which
    made ``_secondary_publishable`` refuse to republish them on a later
    "publier" — only the principal came back, the secondaries stayed missing
    from HA until the next full sync. Reusing the previous decision via
    ``dataclasses.replace`` preserves the step-4 verdict untouched.

    When the secondary was never synced (no previous decision to preserve), a
    conservative refused decision is built instead — nothing to preserve, and an
    unknown verdict must never be treated as an implicit allow.
    """
    previous = getattr(secondary, "publication_decision_ref", None)
    if previous is None:
        decision = PublicationDecision(
            should_publish=False,
            reason="no_sync_decision",
            mapping_result=secondary,
            state_topic=_resolve_state_topic(secondary),
            active_or_alive=active_or_alive,
            discovery_published=discovery_published,
        )
    else:
        decision = dataclasses.replace(
            previous,
            mapping_result=secondary,
            discovery_published=discovery_published,
            active_or_alive=active_or_alive,
        )
    secondary.publication_decision_ref = decision
    return decision


def _sync_publication_decision_refs(
    mapping: MappingResult,
    decision: PublicationDecision,
    *,
    secondary_discovery_published: Optional[bool] = False,
    secondary_active_or_alive: bool = False,
) -> None:
    """P1 fix (ClaudeBox review, commit 3a408db) — single helper called by every
    action path in this module that replaces ``publications[eq_id]`` with a
    refused/failed ``decision`` for the principal ``mapping``.

    Before this fix, only ``publications[eq_id]`` was updated: ``mapping.
    publication_decision_ref`` — consulted by the I11-decoupled readers
    (``sync/state.py``, ``sync/command.py``) — kept pointing at the stale
    published decision until the next full sync, so a deleted/excluded
    equipment kept streaming state and routing commands. This helper kept
    ``publications[eq_id]`` and ``mapping.publication_decision_ref`` consistent
    in one place for the principal.

    P1-ter fix (ClaudeBox review round 3, PR #174) — the principal's ref is
    NEVER repointed by an action path anymore. ``mapping.publication_decision_ref``
    is the "step-4 canonical" source read by ``/system/diagnostics``
    (``_compute_pipeline_step_visible``, ``traceability.decision_trace``); only a
    full sync (``evaluate_equipment.py``) may set it, otherwise a delete/exclude
    action leaves it stuck on a stale refused decision and a later successful
    "publier" action (which already never repoints it, see the comment at its
    call site) never clears the stale pointer, so diagnostics keep reporting the
    equipment as blocked at step 4 even once it is actually published again. The
    I11-decoupled readers already resolve the principal's decision from
    ``publications[eq_id]``, not from this ref, so this helper only still touches
    secondaries' RUNTIME state, via ``_reset_secondary_runtime_state``
    (``should_publish``/``reason`` are preserved).

    ``secondary_discovery_published=None`` skips the secondary loop entirely
    (P3 fix): kept for callers that already recorded each secondary's real
    per-candidate outcome (Story 19.4 : l'ancien chemin « publier »
    ``_publish_mapping_for_action`` a été supprimé, « Publier » passe désormais
    par ``apply_publication_decision()`` comme le sync).
    """
    if secondary_discovery_published is None:
        return
    for secondary in mapping.additional_mappings or []:
        _reset_secondary_runtime_state(
            secondary,
            discovery_published=secondary_discovery_published,
            active_or_alive=secondary_active_or_alive,
        )


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


def _node_id_of(m):
    rd = getattr(m, "reason_details", None) or {}
    nid = rd.get("node_id")
    return nid if isinstance(nid, str) and nid else None


def _entity_type_of(m) -> str:
    return str(getattr(m, "ha_entity_type", "") or "")


def _collect_candidate_node_ids(mapping_result, candidate) -> list:
    """Collect the node-scoped identifier contribution of ONE candidate — the
    primary `mapping_result` itself, or one of its `additional_mappings` — to
    the exhaustive unpublish list built by `_collect_unpublish_node_ids`.

    Returns, in the exact same shape that function returns for this single
    candidate: a `(entity_type, node_id)` tuple when the eqLogic is
    multi-domaine (heterogeneous entity types across candidates); a bare
    `node_id` string when homogeneous and the candidate carries one; or `[]`
    when the candidate contributes nothing (mono-entity primary, or a
    secondary without `node_id` in the homogeneous case).

    Unit 3b: an empty `[]` contribution from a SECONDARY must never on its own
    trigger an `unpublish_by_eq_id` call with empty `node_ids` — that call
    targets the eq-level topic, i.e. the primary's topic, not the secondary's.
    """
    if mapping_result is None:
        return []

    secondaries = list(getattr(mapping_result, "additional_mappings", None) or [])
    all_types = {_entity_type_of(mapping_result)} | {_entity_type_of(s) for s in secondaries}
    is_primary = candidate is mapping_result

    # Multi-domaine hétérogène : porter le type par entité (anti-fantôme cross-domaine).
    if len(all_types) > 1:
        eq_id = getattr(mapping_result, "jeedom_eq_id", None)
        if is_primary:
            nid = _node_id_of(mapping_result) or f"jeedom2ha_{eq_id}"
        else:
            nid = _node_id_of(candidate) or f"jeedom2ha_{getattr(candidate, 'jeedom_eq_id', eq_id)}"
        return [(_entity_type_of(candidate), nid)]

    # Homogène (mono / multi-sensor) : contrat list[str] historique (Story 11.1.bis).
    nid = _node_id_of(candidate)
    return [nid] if nid else []


def _collect_unpublish_node_ids(mapping_result) -> list:
    """Collect node-scoped topic identifiers to unpublish for one eqLogic (Story 11.1.bis).

    Multi-sensor eqLogics publish every entity (primary AND secondaries) under a
    node-scoped topic ``homeassistant/<type>/<node_id>/config``. To depublish
    exhaustively (anti-ghosts), gather the primary node_id plus each secondary node_id
    from the stored mapping result — no topology re-parsing required.

    Returns an empty list for mono-entity eqLogics (no node_id), so the caller falls
    back to the historical single eq-level unpublish (no over-deletion).

    Story 11.2 — cas MULTI-DOMAINE (switch + sensor + binary_sensor sous un même
    eqLogic) : les entités s'étalent sur plusieurs domaines HA, donc un node_id seul
    (+ un entity_type unique côté appelant) ne suffit plus. On renvoie alors une liste
    de tuples ``(entity_type, node_id)`` couvrant TOUTES les entités, y compris le
    switch primaire au topic eq-level (node_id pseudo ``jeedom2ha_<eq_id>``). Le cas
    homogène (mono / multi-sensor) conserve strictement le contrat list[str] historique.

    Story 19.4 unité 3a — concaténation, dans l'ordre (principal puis secondaires),
    des contributions individuelles de `_collect_candidate_node_ids`.
    """
    if mapping_result is None:
        return []

    secondaries = list(getattr(mapping_result, "additional_mappings", None) or [])
    node_ids: list = []
    for candidate in (mapping_result, *secondaries):
        node_ids.extend(_collect_candidate_node_ids(mapping_result, candidate))
    return node_ids


def _candidate_key(mapping_result, candidate) -> tuple:
    """Stable identity of one candidate across two syncs (Story 19.4, C1).

    The primary is ``("principal",)``; a secondary is identified by its Jeedom
    ``cmd_id`` (and its node_id as a tie-breaker), never by object identity: each
    sync rebuilds fresh mapping objects. Its HA domain is part of the identity
    (revue Codex P1, PR #180) : a secondary retyped under the same cmd_id/node_id
    (switch ⇒ sensor) is a new candidate, so the old domain's topic is unpublished.
    The primary's retyping is handled by `_detect_lifecycle_changes`.
    """
    if candidate is mapping_result:
        return ("principal",)
    rd = getattr(candidate, "reason_details", None) or {}
    return ("secondary", rd.get("cmd_id"), _node_id_of(candidate), _entity_type_of(candidate))


def _published_candidates(mapping_result, principal_decision) -> dict:
    """Candidates whose step-4 verdict allows publication, keyed by `_candidate_key`."""
    candidates: dict = {}
    if mapping_result is None:
        return candidates
    if principal_decision is not None and getattr(principal_decision, "should_publish", False):
        candidates[_candidate_key(mapping_result, mapping_result)] = mapping_result
    for secondary in getattr(mapping_result, "additional_mappings", None) or []:
        ref = getattr(secondary, "publication_decision_ref", None)
        if ref is not None and getattr(ref, "should_publish", False):
            candidates[_candidate_key(mapping_result, secondary)] = secondary
    return candidates


def _candidate_topic_entries(mapping_result, candidate) -> list:
    """Explicit ``(entity_type, node_id)`` entries for ONE candidate's discovery topic.

    A mono-entity primary (empty contribution) maps to its eq-level topic, i.e. the
    pseudo node_id ``jeedom2ha_<eq_id>`` (same topic as ``_build_topic`` without
    node_id). A secondary with an empty contribution has no topic of its own and
    yields nothing: it must never be turned into the eq-level (primary's) topic.
    """
    contribution = _collect_candidate_node_ids(mapping_result, candidate)
    eq_id = getattr(mapping_result, "jeedom_eq_id", None)
    entity_type = _entity_type_of(candidate)
    if not contribution:
        if candidate is mapping_result:
            return [(entity_type, f"jeedom2ha_{eq_id}")]
        return []
    entries = []
    for entry in contribution:
        if isinstance(entry, (tuple, list)) and len(entry) == 2:
            entries.append((str(entry[0]), str(entry[1])))
        else:
            entries.append((entity_type, str(entry)))
    return entries


def _refused_candidate_entries(previous_decision, current_decision) -> list:
    """Topic entries of candidates published at the previous sync and refused now.

    Entries still used by a currently accepted candidate are never returned (a
    secondary can share the primary's eq-level topic in the multi-domain case).
    """
    previous_mapping = getattr(previous_decision, "mapping_result", None)
    current_mapping = getattr(current_decision, "mapping_result", None)
    previously = _published_candidates(previous_mapping, previous_decision)
    currently = _published_candidates(current_mapping, current_decision)
    protected = set()
    for candidate in currently.values():
        protected.update(_candidate_topic_entries(current_mapping, candidate))
    entries: list = []
    for key, candidate in previously.items():
        if key in currently:
            continue
        for entry in _candidate_topic_entries(previous_mapping, candidate):
            if entry not in protected and entry not in entries:
                entries.append(entry)
    return entries


def _merge_deferred_candidate_unpublish(
    pending_unpublish: Dict[int, object], eq_id: int, entity_type: str, entries: list,
) -> None:
    """Defer a per-candidate unpublish without overwriting a pending entry.

    Existing entries are kept and made explicit (``(type, node_id)``; an eq-level
    entry becomes the pseudo node_id), then the new entries are added.
    """
    merged: list = []
    existing = pending_unpublish.get(int(eq_id))
    if existing is not None:
        existing_type, existing_ids = _pending_unpublish_parts(existing)
        if not existing_ids:
            merged.append((existing_type, f"jeedom2ha_{eq_id}"))
        for entry in existing_ids:
            if isinstance(entry, (tuple, list)) and len(entry) == 2:
                merged.append((str(entry[0]), str(entry[1])))
            else:
                merged.append((existing_type, str(entry)))
    for entry in entries:
        if entry not in merged:
            merged.append(entry)
    _defer_discovery_unpublish(pending_unpublish, eq_id, entity_type, node_ids=merged)


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


def _pending_unpublish_parts(value) -> tuple:
    """Normalize a pending-unpublish entry to (entity_type, node_ids).

    Backward-compatible: legacy entries stored a bare entity_type string; Story 11.1.bis
    entries store a dict {"entity_type": str, "node_ids": [...]} to carry multi-sensor
    secondaries across a deferred replay.
    """
    if isinstance(value, dict):
        entity_type = str(value.get("entity_type") or "light")
        node_ids = value.get("node_ids") or []
        return entity_type, list(node_ids)
    return str(value or "light"), []


def _defer_discovery_unpublish(
    pending_unpublish: Dict[int, object],
    eq_id: int,
    entity_type: str,
    node_ids: Optional[list] = None,
) -> None:
    """Track one discovery unpublish to replay later when broker is connected.

    Story 11.1.bis — preserve multi-sensor node_ids so the deferred replay erases the
    primary AND every secondary topic (no residual ghost after a reconnect).
    """
    normalized_entity_type = str(entity_type or "light")
    pending_unpublish[int(eq_id)] = {
        "entity_type": normalized_entity_type,
        "node_ids": list(node_ids or []),
    }
    _LOGGER.info(
        "[DISCOVERY] Deferred unpublish eq_id=%d entity_type=%s node_ids=%d",
        eq_id,
        normalized_entity_type,
        len(node_ids or []),
    )


async def _replay_deferred_discovery_unpublish(
    publisher: DiscoveryPublisher,
    pending_unpublish: Dict[int, object],
) -> None:
    """Replay deferred discovery unpublish messages when broker is connected."""
    if not pending_unpublish:
        return

    for pending_eq_id, pending_value in list(pending_unpublish.items()):
        entity_type, node_ids = _pending_unpublish_parts(pending_value)
        if await publisher.unpublish_by_eq_id(pending_eq_id, entity_type=entity_type, node_ids=node_ids):
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

    Story 16.2 (code-review) : `mapping` is received here AFTER `apply_type_override()` has
    already run. This is intentional — the first sync cycle after a user applies (or removes)
    an HA-type override legitimately IS a retyping event and must unpublish the stale topic
    the same way a native mapper retype would (see test_override_qui_change_ha_entity_type_declenche_le_retypage_lifecycle).
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
            prev_node_ids = _collect_unpublish_node_ids(prev_mr)
            if publisher is not None:
                unpublish_ok = await publisher.unpublish_by_eq_id(
                    eq_id, entity_type=prev_mr.ha_entity_type, node_ids=prev_node_ids
                )
            else:
                unpublish_ok = False
            if not unpublish_ok:
                _defer_discovery_unpublish(
                    pending_discovery_unpublish, eq_id, prev_mr.ha_entity_type, node_ids=prev_node_ids
                )
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
                boot_node_ids = boot_entry.get("node_ids", []) or []
                if publisher is not None:
                    unpublish_ok = await publisher.unpublish_by_eq_id(
                        eq_id, entity_type=boot_type, node_ids=boot_node_ids
                    )
                else:
                    unpublish_ok = False
                if not unpublish_ok:
                    _defer_discovery_unpublish(
                        pending_discovery_unpublish, eq_id, boot_type, node_ids=boot_node_ids
                    )
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
    publisher_registry = PublisherRegistry(publisher)

    # AC #11: rejouer les pending_discovery_unpublish AVANT la republication (reconnect uniquement)
    if reason == "broker_reconnect":
        pending_unpublish = app.get("pending_discovery_unpublish", {})
        await _replay_deferred_discovery_unpublish(publisher, pending_unpublish)

    topology = app.get("topology")

    # Revue Codex (P2) : le lissage doit espacer TOUTES les publications MQTT
    # effectivement émises dans ce batch — primaires + secondaires publiables (cf.
    # _secondary_publishable) — pas seulement les primaires, sinon un eqLogic
    # multi-sensor republie ses N secondaires sans aucun délai entre eux.
    nb_entites = len(published_entries)
    for _eq_id, decision in published_entries:
        mapping = getattr(decision, "mapping_result", None)
        if mapping is None:
            continue
        nb_entites += sum(
            1
            for secondary in getattr(mapping, "additional_mappings", None) or []
            if _secondary_publishable(secondary)
        )
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
            ok = await publisher_registry.publish(mapping, topology)
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

        # CC-08 — un eqLogic multi-domaine (switch/lumière + sensors/binary_sensors)
        # porte ses entités secondaires dans additional_mappings ; sans republication
        # dédiée, un reconnect/birth HA laisse ces entités absentes de HA.
        #
        # Revue Codex (P1) : ne republier un secondaire que si sa décision du dernier
        # sync l'y autorise (cf. _secondary_publishable) — sinon on republierait un
        # secondaire explicitement refusé par decide_publication().
        for secondary in getattr(mapping, "additional_mappings", None) or []:
            secondary_type = getattr(secondary, "ha_entity_type", "") or ""
            if not _secondary_publishable(secondary):
                _LOGGER.info(
                    "[DISCOVERY] eq_id=%d entity_type=%s (secondaire) : republication ignorée "
                    "— dernière décision de sync inconnue ou refusée",
                    eq_id, secondary_type,
                )
                continue
            try:
                sec_ok = await publisher_registry.publish(secondary, topology)
                if not sec_ok:
                    _LOGGER.error(
                        "[DISCOVERY] eq_id=%d entity_type=%s (secondaire) : échec publish — bridge indisponible",
                        eq_id, secondary_type,
                    )
            except Exception as exc:
                _LOGGER.error(
                    "[DISCOVERY] eq_id=%d entity_type=%s (secondaire) : échec publish — %s",
                    eq_id, secondary_type, exc,
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

async def _unpublish_refused_candidates(
    eq_id: int,
    previous_decision,
    current_decision,
    *,
    publisher,
    mqtt_bridge,
    pending_discovery_unpublish: Dict[int, object],
    pending_local_cleanup: Dict[int, str],
) -> bool:
    """Story 4.3 (Task 2.7) + Story 19.4 (C1) — dépublie les candidats devenus refusés.

    Partagée par le sync et par « Publier » (mini-sync). Compare les candidats publiés
    dans `previous_decision` à ceux acceptés dans `current_decision` :
    - plus aucun candidat accepté : comportement historique (tout l'équipement, puis la
      disponibilité locale) ;
    - sinon : seuls les candidats refusés sont dépubliés (un appel par équipement) et la
      disponibilité locale reste, car d'autres candidats l'utilisent encore.

    Retourne True si une dépublication a été tentée (ou reportée), False sinon.
    """
    if previous_decision is None or current_decision is None:
        return False
    previous_mapping = getattr(previous_decision, "mapping_result", None)
    if not _published_candidates(previous_mapping, previous_decision):
        return False
    current_mapping = getattr(current_decision, "mapping_result", None)
    if _published_candidates(current_mapping, current_decision):
        entries = _refused_candidate_entries(previous_decision, current_decision)
        if not entries:
            return False
        entity_type = previous_mapping.ha_entity_type
        _LOGGER.info(
            "[SYNC] eq_id=%d: %d candidat(s) refusé(s) → dépublication ciblée",
            eq_id, len(entries),
        )
        if publisher and mqtt_bridge and mqtt_bridge.is_connected:
            if not await publisher.unpublish_by_eq_id(eq_id, entity_type=entity_type, node_ids=entries):
                _LOGGER.warning("[SYNC] Cannot unpublish refused candidates of eq_id=%d — deferring", eq_id)
                _merge_deferred_candidate_unpublish(pending_discovery_unpublish, eq_id, entity_type, entries)
        else:
            _LOGGER.warning(
                "[SYNC] Cannot unpublish refused candidates of eq_id=%d (bridge missing/disconnected) — deferring",
                eq_id,
            )
            _merge_deferred_candidate_unpublish(pending_discovery_unpublish, eq_id, entity_type, entries)
        return True
    entity_type = previous_decision.mapping_result.ha_entity_type
    node_ids = _collect_unpublish_node_ids(previous_decision.mapping_result)
    _LOGGER.info(
        "[SYNC] eq_id=%d: policy change → dépublication (was=%s now=%s)",
        eq_id, previous_decision.reason, current_decision.reason,
    )
    if publisher and mqtt_bridge and mqtt_bridge.is_connected:
        unpublish_ok = await publisher.unpublish_by_eq_id(eq_id, entity_type=entity_type, node_ids=node_ids)
        if unpublish_ok:
            pending_discovery_unpublish.pop(eq_id, None)
        else:
            _LOGGER.warning(
                "[SYNC] Cannot unpublish eq_id=%d for policy change — deferring",
                eq_id,
            )
            _defer_discovery_unpublish(pending_discovery_unpublish, eq_id, entity_type, node_ids=node_ids)
    else:
        _LOGGER.warning(
            "[SYNC] Cannot unpublish eq_id=%d for policy change (bridge missing/disconnected) — deferring",
            eq_id,
        )
        _defer_discovery_unpublish(pending_discovery_unpublish, eq_id, entity_type, node_ids=node_ids)
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
    return True


async def apply_publication_decision(
    eq_id,
    mapping,
    evaluation,
    previous_decision,
    snapshot,
    *,
    is_first_sync,
    boot_cache,
    publisher,
    publisher_registry,
    mqtt_bridge,
    pending_discovery_unpublish,
    mapping_counters,
    publications,
    nouveaux_eq_ids,
):
    await _detect_lifecycle_changes(
        eq_id, mapping, previous_decision,
        boot_cache=boot_cache,
        is_first_sync=is_first_sync,
        publisher=publisher,
        pending_discovery_unpublish=pending_discovery_unpublish,
    )
    decision = evaluation.equipment_decision

    if mapping.confidence in ("sure", "probable", "ambiguous"):
        _increment_mapping_counter(mapping_counters, mapping, mapping.confidence)

    _prepare_publication_bookkeeping(
        eq_id,
        mapping,
        decision,
        snapshot,
        publications,
        nouveaux_eq_ids,
    )

    config_published = False
    # Étape 5 — résultat technique (Story 5.2 PE : sous-bloc séparé, décision étape 4 intacte)
    if decision.should_publish:
        if publisher_registry and mqtt_bridge and mqtt_bridge.is_connected:
            config_published = await publisher_registry.publish(mapping, snapshot)
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
            if mapping.publication_result is None:
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
                _increment_mapping_counter(mapping_counters, mapping, "published")
            else:
                mapping.publication_result = _make_publication_result(
                    "failed", "local_availability_publish_failed"
                )
    else:
        mapping.publication_result = _make_publication_result("not_attempted")
    mapping.pipeline_step_reached = 5
    if not decision.active_or_alive:
        _increment_mapping_counter(mapping_counters, mapping, "skipped")

    # Story 11.1 PE — publication des sensors secondaires (multi-sensor borné).
    # Le device HA est commun à l'eqLogic ; chaque sensor a ses propres
    # identifiants/topic. La décision/bookkeeping primaire reste inchangée.
    if mapping.additional_mappings:
        await _publish_additional_sensors(
            primary_mapping=mapping,
            secondary_decisions=evaluation.secondary_decisions,
            snapshot=snapshot,
            publisher_registry=publisher_registry,
            mqtt_bridge=mqtt_bridge,
            mapping_counters=mapping_counters,
        )

        # Correctif 19-2b : si le principal n'a pas publié la disponibilité locale
        # (refusé ou échec discovery) mais qu'au moins un secondaire a été publié,
        # l'availability_mode="all" du secondaire exige quand même le topic
        # jeedom2ha/<eq>/availability, sinon il reste unavailable dans HA.
        if (
            not decision.discovery_published
            and decision.local_availability_supported
            and any(
                sec_decision.discovery_published
                for sec_decision in evaluation.secondary_decisions
            )
        ):
            _publish_local_availability_state(mqtt_bridge, eq_id, decision)

    return decision, config_published


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
    confidence_policy = sync_config.get("confidence_policy", _DEFAULT_CONFIDENCE_POLICY)
    if confidence_policy not in _VALID_CONFIDENCE_POLICIES:
        _LOGGER.warning(
            "[SYNC] confidence_policy invalide '%s' → fallback %s",
            confidence_policy, _DEFAULT_CONFIDENCE_POLICY,
        )
        confidence_policy = _DEFAULT_CONFIDENCE_POLICY

    _LOGGER.info("[TOPOLOGY] Received sync request (confidence_policy=%s)", confidence_policy)
    request.app["confidence_policy"] = confidence_policy
    data_dir = _resolve_data_dir(request)

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
    mapper_registry = MapperRegistry()
    mappings = {}       # Dict[int, MappingResult]
    publications = {}   # Dict[int, PublicationDecision]

    mqtt_bridge = request.app.get("mqtt_bridge")
    publisher = DiscoveryPublisher(mqtt_bridge) if mqtt_bridge else None
    publisher_registry = PublisherRegistry(publisher) if publisher else None
    mapping_counters = _build_mapping_counters_from_publisher_registry(publisher_registry)
    pending_local_cleanup = request.app["pending_local_availability_cleanup"]
    pending_discovery_unpublish = request.app["pending_discovery_unpublish"]

    if mqtt_bridge and mqtt_bridge.is_connected and publisher:
        await _replay_deferred_discovery_unpublish(publisher, pending_discovery_unpublish)
    if mqtt_bridge and mqtt_bridge.is_connected:
        _replay_deferred_local_availability_cleanup(mqtt_bridge, pending_local_cleanup)

    # Story 16.2 code-review — charger les overrides UNE SEULE FOIS pour tout le cycle
    # de sync (au lieu d'une relecture disque par équipement/capteur secondaire).
    overrides_cache = list_overrides(data_dir)
    # Story 16.3 — même principe pour les overrides de politique de publication (équipement).
    equipment_overrides_cache = list_equipment_overrides(data_dir)

    # Story 19.4 (AC3) — filtre de scope unique, appliqué APRÈS la décision, comme « Publier ».
    scope_entries = {
        _to_int(entry.get("eq_id"), default=0): entry
        for entry in published_scope_contract.get("equipements", [])
    }
    scope_excluded_eq_ids: set[int] = set()

    for eq_id, result in eligibility.items():
        if not result.is_eligible:
            continue

        eq = snapshot.eq_logics.get(eq_id)
        if not eq:
            continue

        # Story 19.1 — étapes 2 à 4 (mapping, override de type, validation projection,
        # décision de publication) déléguées à evaluate_equipment() (Story 19.0). Le
        # MapperRegistry reste injecté (une seule instance par sync, cf. plus haut),
        # jamais recréé à l'intérieur de la fonction pure.
        evaluation = evaluate_equipment(
            eq,
            snapshot,
            result,
            mapper_registry=mapper_registry,
            confidence_policy=confidence_policy,
            persisted_overrides=overrides_cache,
            persisted_equipment_overrides=equipment_overrides_cache,
        )
        mapping = evaluation.mapping
        if mapping is None:
            continue  # Not mapped by any mapper

        mappings[eq_id] = mapping
        previous_decision = request.app["publications"].get(eq_id)

        # Story 19.4 (AC3) — hors périmètre publié : jamais publié, quelle que soit la
        # décision. L'équipement n'entre pas dans `nouveaux_eq_ids` : la purge plus bas
        # (équipements retirés) dépublie ce qui l'était encore et efface sa disponibilité.
        if not _scope_entry_is_included(eq_id, scope_entries.get(eq_id), eligibility):
            publications[eq_id] = _scope_excluded_decision(mapping, snapshot)
            scope_excluded_eq_ids.add(eq_id)
            continue

        # Story 5.2 — detect lifecycle changes (rename, area change, retyping)
        # Called once per eq_id, before publish, common to all type branches
        decision, config_published = await apply_publication_decision(
            eq_id,
            mapping,
            evaluation,
            previous_decision,
            snapshot,
            is_first_sync=is_first_sync,
            boot_cache=request.app.get("boot_cache", {}),
            publisher=publisher,
            publisher_registry=publisher_registry,
            mqtt_bridge=mqtt_bridge,
            pending_discovery_unpublish=pending_discovery_unpublish,
            mapping_counters=mapping_counters,
            publications=publications,
            nouveaux_eq_ids=nouveaux_eq_ids,
        )

        # Story 12.1 — snapshot initial : publier la valeur courante connue de Jeedom
        # sur le state_topic des entités vague 1 APRÈS la discovery (sinon HA l'ignore).
        state_sync = request.app.get("state_synchronizer")
        if state_sync is not None and mqtt_bridge and mqtt_bridge.is_connected:
            await state_sync.publish_initial_states(decision)

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
            
    # Story 4.3 (Task 2.7) + Story 19.4 (C1) — dépublication des candidats devenus refusés
    # (`_unpublish_refused_candidates`, partagée avec « Publier »).
    # Ces eq_ids sont dans nouveaux_eq_ids (toujours éligibles) donc NON couverts par eq_ids_supprimes
    for eq_id in nouveaux_eq_ids:
        await _unpublish_refused_candidates(
            eq_id,
            request.app["publications"].get(eq_id),
            publications.get(eq_id),
            publisher=publisher,
            mqtt_bridge=mqtt_bridge,
            pending_discovery_unpublish=pending_discovery_unpublish,
            pending_local_cleanup=pending_local_cleanup,
        )

    # Purge des équipements qui ne sont plus remontés ou plus éligibles
    eq_ids_supprimes = anciens_eq_ids - nouveaux_eq_ids
    for old_eq_id in eq_ids_supprimes:
        # Si c'était publié avant, on l'unpublish
        old_decision = request.app["publications"].get(old_eq_id)
        elig_entry = eligibility.get(old_eq_id)
        if elig_entry is None:
            cleanup_reason = "supprimé dans Jeedom"
        elif old_eq_id in scope_excluded_eq_ids:
            cleanup_reason = "exclu du périmètre publié (scope)"
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
                boot_node_ids = boot_entry.get("node_ids", []) or []
                boot_cleanup_reason = "supprimé depuis downtime daemon" if elig_entry is None else cleanup_reason
                discovery_action = "discovery unpublish effectif"
                if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                    unpublish_ok = await publisher.unpublish_by_eq_id(
                        old_eq_id, entity_type=boot_entity_type, node_ids=boot_node_ids
                    )
                    if unpublish_ok:
                        pending_discovery_unpublish.pop(old_eq_id, None)
                    else:
                        discovery_action = "discovery unpublish deferred"
                        _defer_discovery_unpublish(
                            pending_discovery_unpublish, old_eq_id, boot_entity_type, node_ids=boot_node_ids
                        )
                else:
                    discovery_action = "discovery unpublish deferred"
                    _defer_discovery_unpublish(
                        pending_discovery_unpublish, old_eq_id, boot_entity_type, node_ids=boot_node_ids
                    )
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
            node_ids = _collect_unpublish_node_ids(old_decision.mapping_result)
            discovery_action = "discovery unpublish effectif"
            if publisher and mqtt_bridge and mqtt_bridge.is_connected:
                unpublish_ok = await publisher.unpublish_by_eq_id(old_eq_id, entity_type=entity_type, node_ids=node_ids)
                if unpublish_ok:
                    pending_discovery_unpublish.pop(old_eq_id, None)
                else:
                    discovery_action = "discovery unpublish deferred"
                    _defer_discovery_unpublish(pending_discovery_unpublish, old_eq_id, entity_type, node_ids=node_ids)
            else:
                discovery_action = "discovery unpublish deferred"
                _defer_discovery_unpublish(pending_discovery_unpublish, old_eq_id, entity_type, node_ids=node_ids)
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
    
    # Story 10.1 — Publish Jeedom scenarios as HA button entities
    scenario_mapper = ScenarioButtonMapper()
    scenario_publications: Dict[int, PublicationDecision] = {}
    for scenario_id, scenario in snapshot.scenarios.items():
        if not scenario.is_active:
            continue
        sc_mapping = scenario_mapper.map(scenario)
        sc_decision = PublicationDecision(
            should_publish=True,
            reason="scenario_button",
            mapping_result=sc_mapping,
            active_or_alive=True,
            discovery_published=False,
        )
        sc_mapping.publication_decision_ref = sc_decision
        scenario_publications[scenario_id] = sc_decision
        if publisher_registry and mqtt_bridge and mqtt_bridge.is_connected:
            ok = await publisher_registry.publish(sc_mapping, snapshot)
            if ok:
                sc_decision.discovery_published = True
            else:
                _LOGGER.warning("[SCENARIO] Failed to publish button for scenario_id=%d", scenario_id)
    # Purge scenarios that disappeared or became inactive since last sync (M1 fix).
    stale_scenario_ids = set(request.app["scenario_publications"]) - set(scenario_publications)
    for stale_id in stale_scenario_ids:
        request.app["scenario_publications"].pop(stale_id, None)
        _LOGGER.info("[SCENARIO] Purged stale scenario_id=%d from scenario_publications", stale_id)
    request.app["scenario_publications"].update(scenario_publications)

    # Store detailed decisions in RAM for Epic 4 (diagnostic)
    request.app["mappings"].update(mappings)
    request.app["publications"].update(publications)
    request.app["published_scope"] = _apply_pending_scope_flags(
        published_scope_contract,
        request.app["publications"],
        request.app["pending_discovery_unpublish"],
    )

    # Story 5.1 — Task 1.2: persister le cache disque après chaque sync réussi
    save_publications_cache(request.app["publications"], data_dir)

    # Story 5.1 — Task 7.3: purger boot_cache après le premier sync (rôle accompli)
    if is_first_sync and request.app.get("boot_cache"):
        request.app["boot_cache"] = {}
        _LOGGER.info("[CACHE] boot_cache purgé après premier sync")

    # Story 5.1 — Task 2.1: signaler que le premier sync a été reçu (annule le watchdog)
    boot_sync_event = request.app.get("boot_sync_received")
    if boot_sync_event is not None and not boot_sync_event.is_set():
        boot_sync_event.set()

    _LOGGER.info("[MAPPING] Summary: %s", _format_mapping_counter_summary(mapping_counters))
    
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
    "no_projection_possible": (
        "Aucune commande Info ou Action exploitable — projection impossible même en dégradation.",
        "Vérifiez que l'équipement possède des commandes Info ou Action dans Jeedom.",
        False,
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
#                no_supported_generic_type, discovery_publish_failed, no_projection_possible
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
    "no_projection_possible": "no_projection_possible",  # Story 9.5 fix — éligible sans commande exploitable
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
            "missing_fields": list(_pv.missing_fields),
            "missing_capabilities": list(_pv.missing_capabilities),
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


def _enrich_command_drilldown(eq, snapshot, map_result, matched_commands, unmatched_commands):
    """Story 16.4 — enrichit, en LECTURE SEULE, chaque entrée du drill-down commande.

    Additif sur les entrées déjà produites (`matched_commands` / `unmatched_commands`) :
    ajoute `attendu_ha` (type HA natif projeté par le moteur), `mapping_decision`
    (décision effective) et `retained` (retenue vs rejetée). Quand un override de TYPE
    (Story 16.2) a été appliqué, ajoute `type_override` avec la décision native ET la
    décision surchargée (AC2). N'altère aucun champ 4D eq-level.
    """
    reason_details = (map_result.reason_details or {}) if map_result else {}
    override_applied = bool(reason_details.get("override_applied"))
    effective_type = map_result.ha_entity_type if map_result else None

    if override_applied:
        # Décision native = moteur brut (registry.map n'applique PAS les overrides).
        native_type = resolve_expected_ha(eq, snapshot).get("proposed_ha_entity_type")
        override_source = reason_details.get("override_source")
    else:
        native_type = effective_type
        override_source = None

    for entry in matched_commands:
        entry["retained"] = True
        entry["attendu_ha"] = native_type
        entry["mapping_decision"] = effective_type
        if override_applied:
            entry["type_override"] = {
                "source": override_source,
                "native": native_type,
                "effective": effective_type,
            }

    for entry in unmatched_commands:
        entry["retained"] = False
        entry["attendu_ha"] = None
        entry["mapping_decision"] = None


def _build_publication_override_diag(reason_code, pub_decision):
    """Story 16.4 (AC4) — expose l'état d'override de PUBLICATION (Story 16.3) sans
    introduire de nouveau reason_code.

    Consomme EXACTEMENT les reason_codes 16.3 (`publication_excluded_eqlogic` /
    `publication_excluded_command` / `publication_forced`) portés par `reason_code`,
    et les `reason_details` 16.3 (`publication_override_applied`, `override_source`,
    `underlying_confidence`) portés par `pub_decision`. Retourne None si aucun override
    de publication n'a été appliqué (pas de clé nulle).
    """
    pub_reason_details = (pub_decision.reason_details or {}) if pub_decision else {}
    if not pub_reason_details.get("publication_override_applied"):
        return None
    return {
        "reason_code": reason_code,
        "override_source": pub_reason_details.get("override_source"),
        "underlying_confidence": pub_reason_details.get("underlying_confidence"),
    }


def _secondary_mapping_by_cmd(primary_mapping):
    """Index {cmd_id: MappingResult} des capteurs/interrupteurs secondaires (Story 11.1
    multi-sensor), TOUTES les commandes qu'ils couvrent confondues.

    Un secondaire couvre non seulement sa commande d'état (`reason_details["cmd_id"]`) mais
    aussi, pour un interrupteur secondaire, ses commandes d'action (On/Off) présentes dans
    `secondary.commands` — routées et prouvées par la Story 19.2. Utilise `mapping_cmd_ids()`
    (même extraction que le primaire, `mapping/overrides.py`) pour ne PAS dupliquer une
    seconde définition de « quelles commandes appartiennent à ce mapping » (Story 19.3,
    correction relecture ClaudeBox PR #176, P1-b) : c'est la même fonction que celle utilisée
    par `covered`, le diagnostic de l'arbre et la cible de l'aperçu (`_resolve_command_mapping`).
    Premier gagnant si collision (setdefault), ordre natif préservé.
    """
    index: Dict[int, object] = {}
    if primary_mapping is None:
        return index
    for secondary in (primary_mapping.additional_mappings or []):
        for cmd_id in mapping_cmd_ids(secondary):
            index.setdefault(cmd_id, secondary)
    return index


def _resolve_command_mapping(evaluation, cmd_id):
    """Retrouve LE `MappingResult` (primaire ou secondaire) qui couvre `cmd_id` au sein
    d'une `EquipmentEvaluation` déjà décidée — `None` si l'équipement n'a pas de mapping
    (inéligible ou `no_mapping`) ou si `cmd_id` n'est couvert par AUCUN des deux.

    Priorité EXACTEMENT celle du contrat (`evaluate_equipment()`, AC1, `covered.setdefault`
    primaire PUIS secondaires dans l'ordre) : le primaire gagne toujours sur un secondaire
    pour une commande partagée. Source UNIQUE utilisée par l'arbre (`covered`, `diag_mapping`,
    `attendu_ha`, `effective_ha`) ET par l'aperçu — Story 19.3, correction relecture ClaudeBox
    PR #176 tour 2 (P2). Avant ce correctif, l'aperçu (`_target_mapping_for_cmd`) résolvait
    SECONDAIRE d'abord, à l'inverse du contrat et de l'arbre (qui, eux, dupliquaient chacun
    leur propre logique primaire-d'abord) : un piège pour toute commande partagée entre le
    primaire et un secondaire, latent depuis que l'index des secondaires couvre TOUTES leurs
    commandes (P1-b). Sans effet sur le corpus doré (aucune commande partagée).

    `cmd_id=None` cible toujours le mapping primaire (vue équipement).
    """
    primary_mapping = evaluation.mapping
    if primary_mapping is None:
        return None
    if isinstance(cmd_id, int):
        if cmd_id in set(mapping_cmd_ids(primary_mapping)):
            return primary_mapping
        return _secondary_mapping_by_cmd(primary_mapping).get(cmd_id)
    return primary_mapping


def _decision_view(decision, mapping):
    """Reconstruit la vue JSON-safe historique (contrat `_preview_mapping_view`, Story 16.6)
    à partir d'une décision + son mapping DÉJÀ résolus par `evaluate_equipment()` — ne relance
    JAMAIS `validate_projection`/`decide_publication` (Story 19.3, Dev Notes : aucune
    duplication de la logique de décision, AR9/I4). `mapping=None` couvre le cas d'une
    commande non couverte ou d'un équipement inéligible : `decision` reste toujours renseignée
    (AC7 — jamais `None`), seuls les champs dérivés du mapping deviennent `None`/vides.
    """
    if decision is None:
        return None
    if mapping is None:
        return {
            "ha_entity_type": None,
            "confidence": None,
            "reason_code": None,
            "projection_validity": {
                "is_valid": False,
                "reason_code": decision.reason,
                "missing_capabilities": [],
                "missing_fields": [],
            },
            "should_publish": decision.should_publish,
            "publication_reason": decision.reason,
        }
    validity = mapping.projection_validity
    return {
        "ha_entity_type": mapping.ha_entity_type,
        "confidence": mapping.confidence,
        "reason_code": mapping.reason_code,
        "projection_validity": {
            "is_valid": validity.is_valid if validity else False,
            "reason_code": validity.reason_code if validity else None,
            "missing_capabilities": list(validity.missing_capabilities) if validity else [],
            "missing_fields": list(validity.missing_fields) if validity else [],
        },
        "should_publish": decision.should_publish,
        "publication_reason": decision.reason,
    }


def _view_from_evaluation(evaluation, cmd_id):
    """Vue JSON-safe (contrat `_decision_view`) pour `cmd_id` au sein d'une évaluation —
    `None` si non couvert (le caller décide alors du `covered: False`), jamais un mapping
    ré-évalué (Story 19.3, AC1/AC2)."""
    target_mapping = _resolve_command_mapping(evaluation, cmd_id)
    if target_mapping is None:
        return None
    decision = target_mapping.publication_decision_ref or evaluation.equipment_decision
    return _decision_view(decision, target_mapping)


def _view_for_ineligible_or_unmapped(evaluation, cmd_id):
    """Vue JSON-safe résolue via `command_decisions` (jamais un mapping ré-évalué) — Story
    19.3, correction relecture ClaudeBox PR #176. Deux appelants :

    P1-a : équipement dont `evaluation.mapping is None` (inéligible, I1, ou `no_mapping`,
    étape 2). Ni `evaluate_equipment()` ni `decide_publication()` ne consultent jamais un
    override (TYPE ou politique) avant ce point de sortie précoce (I4 : le premier échec 1→2
    fait foi, jamais réévalué en aval) : la décision exposée ici est donc IDENTIQUE pour la vue
    AUTO et la vue AVEC override proposé — un seul appel suffit, jamais de second
    `evaluate_equipment` à rejouer pour ce cas.

    Écart corpus doré (`auto_target is None`, `_handle_overrides_preview`) : équipement mappé
    mais `cmd_id` non couvert NI par le primaire NI par un secondaire (`command_not_covered`).
    Sans ce helper, l'aperçu retombait sur la vue du mapping PRIMAIRE (équipement) au lieu de
    la décision propre à cette commande, divergeant du diagnostic de l'arbre pour la même
    commande (eq 230/554/583 du corpus doré 59 équipements).

    Dans les deux cas : mêmes champs que le diagnostic de l'arbre (`_build_mapping_override_
    tree`, branche `diag_mapping=None`), jamais `None` (AC7)."""
    if isinstance(cmd_id, int):
        for command_decision in evaluation.command_decisions:
            if command_decision.cmd_id == cmd_id:
                return _decision_view(command_decision, None)
    return _decision_view(evaluation.equipment_decision, None)


async def _handle_overrides_preview(request: web.Request) -> web.Response:
    """POST /system/overrides/preview — Story 16.6 : dry-run d'un override (lecture seule).

    Calcule la vue AUTO (état effectif ACTUEL — overrides déjà persistés inclus, aucun
    proposé — donc cohérente avec ce que montre déjà la surface, Story 19.3 AC2) et la vue
    AVEC l'override PROPOSÉ (fusionné EN MÉMOIRE avec les overrides persistés via
    `evaluate_equipment()`, jamais sauvegardé). Aucune publication MQTT, aucune écriture
    disque. Zéro effet de bord : ni `save_override`, ni écriture `data_dir`, ni `publish*`.

    Story 19.3 (AC2) : passe par `evaluate_equipment()` — plus de rejeu direct de
    `validate_projection`/`decide_publication` dans ce module (parité stricte avec la surface,
    même code de décision). Une éligibilité amont négative (CC-03) donne ici aussi
    `mapped: False`, jamais un mapping fantôme. `confidence_policy` vient exclusivement de
    `app["confidence_policy"]` (politique du dernier sync) — jamais du payload de requête,
    qui pourrait mentir par rapport à la politique réellement appliquée en publication.
    """
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"status": "error", "message": "Invalid JSON"}, status=400)
    payload = data.get("payload", {}) if isinstance(data, dict) else {}

    eq_id = payload.get("jeedom_eq_id")
    if not isinstance(eq_id, int):
        return web.json_response(
            {"status": "error", "message": "jeedom_eq_id (int) requis"}, status=400
        )

    proposed_type = payload.get("ha_entity_type")
    proposed_cmd_id = payload.get("jeedom_cmd_id")
    proposed_policy = payload.get("publication_policy")
    if proposed_type is None and proposed_policy is None:
        return web.json_response(
            {"status": "error", "message": "ha_entity_type ou publication_policy requis"},
            status=400,
        )
    if proposed_type is not None and (not isinstance(proposed_type, str) or not proposed_type):
        return web.json_response(
            {"status": "error", "message": "ha_entity_type doit être une chaîne non vide"},
            status=400,
        )
    if proposed_policy is not None and proposed_policy not in ("exclude", "force_publish"):
        return web.json_response(
            {"status": "error", "message": "publication_policy invalide (exclude|force_publish)"},
            status=400,
        )

    snapshot = request.app.get("topology")
    eq = snapshot.eq_logics.get(eq_id) if snapshot else None
    if eq is None:
        return web.json_response(
            {"status": "error", "message": f"Équipement {eq_id} introuvable"}, status=404
        )

    # AC2 (Story 19.3) : politique de confiance = celle de l'état applicatif (dernier sync),
    # jamais celle du payload (écart relevé PR #169).
    confidence_policy = request.app.get("confidence_policy") or _DEFAULT_CONFIDENCE_POLICY
    if confidence_policy not in _VALID_CONFIDENCE_POLICIES:
        confidence_policy = _DEFAULT_CONFIDENCE_POLICY

    native_generic_types = {str(c.id): c.generic_type for c in eq.cmds}
    data_dir = _resolve_data_dir(request)
    eligibility = assess_eligibility(eq)
    mapper_registry = MapperRegistry()
    persisted_overrides = list_overrides(data_dir)
    persisted_equipment_overrides = list_equipment_overrides(data_dir)

    # 1. AUTO — état effectif ACTUEL (overrides déjà persistés inclus, aucun proposé) : ce
    # qu'affiche déjà la surface pour cet équipement (AC2). Une éligibilité négative (I1) ou
    # un `no_mapping` (étape 2) se traduisent tous deux par `evaluation.mapping is None`.
    auto_evaluation = evaluate_equipment(
        eq, snapshot, eligibility,
        mapper_registry=mapper_registry,
        confidence_policy=confidence_policy,
        persisted_overrides=persisted_overrides,
        persisted_equipment_overrides=persisted_equipment_overrides,
    )
    if auto_evaluation.mapping is None:
        # P1-a (relecture ClaudeBox PR #176) : jamais muet — expose la VRAIE décision du
        # contrat (raison d'éligibilité ou `no_mapping`, `should_publish:false`), la même vue
        # que le `diagnostic` de l'arbre pour cette commande (AC2/AC7). `auto` et `overridden`
        # partagent la même vue : aucun override ne peut changer une décision déjà tranchée au
        # niveau 1/2 (I4), voir `_view_for_ineligible_or_unmapped`. `covered` toujours présent.
        no_mapping_view = _view_for_ineligible_or_unmapped(auto_evaluation, proposed_cmd_id)
        return web.json_response({
            "status": "ok",
            "payload": {
                "jeedom_eq_id": eq_id,
                "mapped": False,
                "covered": False,
                "auto": no_mapping_view,
                "overridden": no_mapping_view,
                "native_generic_types": native_generic_types,
            },
        })

    # AC12 « jamais vide » : une commande ciblée qui n'est couverte NI par le primaire NI par
    # un capteur secondaire n'a pas de mapping à évaluer. On répond honnêtement
    # `covered:false` / `overridden:null` : l'UI montre « non couvert ». `auto` doit exposer
    # la décision PROPRE à cette commande (`command_not_covered`, via `command_decisions`),
    # pas la vue du mapping primaire — sinon l'aperçu divergerait du diagnostic de l'arbre pour
    # cette même commande (relecture ClaudeBox PR #176, écart découvert sur le corpus doré 59
    # équipements : eq 230/554/583). `_view_for_ineligible_or_unmapped` fait exactement cette
    # résolution par `cmd_id` dans `command_decisions`, `mapping=None` — même contrat que la
    # branche `diag_mapping=None` de `_build_mapping_override_tree`.
    auto_target = _resolve_command_mapping(auto_evaluation, proposed_cmd_id)
    if auto_target is None:
        return web.json_response({
            "status": "ok",
            "payload": {
                "jeedom_eq_id": eq_id,
                "mapped": True,
                "covered": False,
                "auto": _view_for_ineligible_or_unmapped(auto_evaluation, proposed_cmd_id),
                "overridden": None,
                "native_generic_types": native_generic_types,
            },
        })

    # 2. Overrides PROPOSÉS, construits depuis le corps de requête — une seule entrée par clé
    # `eq_id:cmd_id` pouvant porter `ha_entity_type` ET/OU `publication_override` (schéma v2).
    cmd_ids = mapping_cmd_ids(auto_target)
    key_cmd = proposed_cmd_id if isinstance(proposed_cmd_id, int) else (cmd_ids[0] if cmd_ids else None)
    proposed_overrides: Dict[str, dict] = {}
    if proposed_type is not None and key_cmd is not None:
        proposed_overrides[f"{eq_id}:{key_cmd}"] = {
            "ha_entity_type": proposed_type,
            "source": "preview",
        }
    proposed_equipment_overrides: Dict[str, dict] = {}
    if proposed_policy is not None:
        if isinstance(proposed_cmd_id, int):
            proposed_overrides.setdefault(f"{eq_id}:{proposed_cmd_id}", {})["publication_override"] = proposed_policy
        else:
            proposed_equipment_overrides[str(eq_id)] = {"publication_override": proposed_policy}

    # 3. Résultat AVEC override : fusion persisté+proposé (AC2). Le helper de priorité
    # (`evaluate_equipment._apply_type_override_with_proposed_priority`) garantit que CE
    # `cmd_id` proposé gagne même si un `cmd_id` frère du même mapping porte déjà un override
    # persisté — test « conflit inter-commandes » (Dev Notes, Story 19.3).
    over_evaluation = evaluate_equipment(
        eq, snapshot, eligibility,
        mapper_registry=mapper_registry,
        confidence_policy=confidence_policy,
        persisted_overrides=persisted_overrides,
        persisted_equipment_overrides=persisted_equipment_overrides,
        proposed_overrides=proposed_overrides,
        proposed_equipment_overrides=proposed_equipment_overrides,
    )
    over_target = _resolve_command_mapping(over_evaluation, proposed_cmd_id)

    auto_view = _view_from_evaluation(auto_evaluation, proposed_cmd_id)
    over_view = _view_from_evaluation(over_evaluation, proposed_cmd_id)

    # Champ d'affichage `publication_override` (chaîne brute, ex. "exclude_eqlogic") — lecture
    # SEULE via `resolve_publication_override` (même fusion que `evaluate_equipment`, via
    # `merge_override_layer`) : n'influence jamais `should_publish`/`publication_reason`
    # (qui viennent exclusivement de `over_view`, ci-dessus) — sert uniquement à afficher QUEL
    # override a été résolu (trace UX, Story 16.6 AC4).
    merged_cmd_overrides = merge_override_layer(persisted_overrides, proposed_overrides)
    merged_equipment_overrides = merge_override_layer(
        persisted_equipment_overrides, proposed_equipment_overrides
    )
    pub_override = None
    if over_target is not None:
        pub_override = _resolve_publication_override_for_mapping(
            over_target, merged_cmd_overrides, merged_equipment_overrides
        )

    over_reason_details = (over_target.reason_details if over_target is not None else None) or {}
    if over_reason_details.get("override_applied"):
        over_view["type_override"] = {
            "source": over_reason_details.get("override_source"),
            "native": auto_target.ha_entity_type,
            "effective": over_target.ha_entity_type,
        }
    if pub_override is not None:
        over_view["publication_override"] = pub_override

    # 4. Export support (AC4, Story 16.6) : trace de preview + raisons de refus (aucun nouveau
    # reason_code — les codes viennent tous d'`evaluate_equipment`/`decide_publication`).
    refusal_reasons = []
    if not over_view["projection_validity"]["is_valid"] and over_view["projection_validity"]["reason_code"]:
        refusal_reasons.append(over_view["projection_validity"]["reason_code"])
    if not over_view["should_publish"] and over_view["publication_reason"]:
        if over_view["publication_reason"] not in refusal_reasons:
            refusal_reasons.append(over_view["publication_reason"])
    support_export = {
        "preview_trace": {
            "native": auto_target.ha_entity_type,
            "effective": over_target.ha_entity_type if over_target is not None else auto_target.ha_entity_type,
            "publication_override": pub_override,
        },
        "refusal_reasons": refusal_reasons,
    }

    return web.json_response({
        "status": "ok",
        "payload": {
            "jeedom_eq_id": eq_id,
            "mapped": True,
            "covered": True,
            "auto": auto_view,
            "overridden": over_view,
            "native_generic_types": native_generic_types,
            "support_export": support_export,
        },
    })


def _resolve_data_dir(request: web.Request) -> str:
    """Point unique de résolution de la persistance (overrides et cache de publication).

    Le sync et les routes HTTP utilisent le data_dir applicatif, sinon _DATA_DIR.
    """
    return request.app.get("data_dir") or _DATA_DIR


def _build_mapping_override_tree(
    eq,
    snapshot,
    data_dir,
    confidence_policy=_DEFAULT_CONFIDENCE_POLICY,
    synced_decision=None,
    scope_included=True,
):
    """Story 16.5 (AC4/AC5) — arbre par commande de l'état d'override courant (lecture seule).

    Pour chaque commande de l'équipement (ordre natif Jeedom), expose le `generic_type`
    natif (jamais muté, D10), l'attendu HA calculé par le moteur, le type effectif après
    override persisté, l'état d'override, et le diagnostic effectif (projection + publication).
    N'écrit rien.

    Story 19.3 :
      AC1 (CC-03) : consomme `evaluate_equipment()` au lieu de rejouer sa propre logique
      d'affichage — une éligibilité amont négative (I1) ou un override d'exclusion (Story
      16.3) se traduisent ici par `should_publish=False` avec le VRAI reason_code retenu par
      I4, jamais par un « sera publié » optimiste qui ignore la cause amont.
      AC7 : chaque commande obtient sa `CommandDecision` (jamais `None`) via
      `evaluation.command_decisions`, y compris les commandes non couvertes.
      AC6 : `sync_status` compare la dernière décision SYNCÉE (`synced_decision`, fournie par
      l'appelant depuis `app["publications"]`) à la décision COURANTE (avec overrides
      persistés actuels) — `override_pending=True` signale un override sauvegardé mais pas
      encore appliqué par un sync (badge « pas encore appliqué »).
      Story 19.4 (AC3) : le sync applique le filtre de scope après la décision ; la décision
      COURANTE comparée ici l'applique donc aussi (`scope_included`), sinon un équipement hors
      périmètre afficherait à tort « pas encore appliqué » alors que le sync ne le publiera jamais.

    Story 19.3 (P2, relecture ClaudeBox PR #176 tour 2) : la résolution primaire/secondaire
    par commande passe désormais par `_resolve_command_mapping()`, la même fonction que
    l'aperçu — plus de logique `is_covered`/`is_secondary` dupliquée ici (qui coïncidait déjà
    avec la priorité primaire-d'abord du contrat, mais était une SECONDE implémentation à
    maintenir en cohérence avec l'aperçu).
    """
    overrides_cache = list_overrides(data_dir)
    equipment_overrides_cache = list_equipment_overrides(data_dir)
    proposed_eq = resolve_expected_ha(eq, snapshot).get("proposed_ha_entity_type")

    eligibility = assess_eligibility(eq)
    evaluation = evaluate_equipment(
        eq, snapshot, eligibility,
        mapper_registry=MapperRegistry(),
        confidence_policy=confidence_policy,
        persisted_overrides=overrides_cache,
        persisted_equipment_overrides=equipment_overrides_cache,
    )
    mapped = evaluation.mapping is not None
    command_decision_by_cmd = {d.cmd_id: d for d in evaluation.command_decisions}

    commands = []
    for cmd in eq.cmds:
        key = f"{eq.id}:{cmd.id}"
        entry = overrides_cache.get(key) or {}
        override_type = entry.get("ha_entity_type")
        override_applied = bool(override_type)
        diag_mapping = _resolve_command_mapping(evaluation, cmd.id)
        is_covered = diag_mapping is not None

        if is_covered:
            attendu_ha = diag_mapping.ha_entity_type
            row_effective = diag_mapping.ha_entity_type
        else:
            attendu_ha = proposed_eq
            row_effective = override_type if override_applied else attendu_ha

        row = {
            "jeedom_cmd_id": cmd.id,
            "cmd_name": cmd.name,
            "generic_type": cmd.generic_type,
            "coverable": bool(cmd.generic_type),
            "covered": is_covered,
            "attendu_ha": attendu_ha,
            "effective_ha": row_effective,
            "override_applied": override_applied,
        }
        if override_applied:
            row["override_source"] = entry.get("source", "user")
        row["diagnostic"] = _decision_view(command_decision_by_cmd.get(cmd.id), diag_mapping)
        commands.append(row)

    current_should_publish = bool(
        mapped and evaluation.equipment_decision.should_publish and scope_included
    )
    synced_should_publish = synced_decision.should_publish if synced_decision is not None else None
    override_pending = synced_should_publish is not None and synced_should_publish != current_should_publish

    return {
        "jeedom_eq_id": eq.id,
        "eq_name": eq.name,
        "mapped": mapped,
        "sync_status": {
            "synced_should_publish": synced_should_publish,
            "current_should_publish": current_should_publish,
            "override_pending": override_pending,
        },
        "commands": commands,
    }


async def _handle_mapping_overrides_get(request: web.Request) -> web.Response:
    """GET /system/mapping_overrides/{eq_id} — Story 16.5 (AC4/5) : arbre par commande.

    Lecture seule : statuts + `generic_type` natif + attendu HA + effectif + diagnostic
    par commande, pour peupler le triptyque à l'ouverture de l'onglet. Aucune écriture.
    """
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)

    raw_eq_id = request.match_info.get("eq_id", "")
    try:
        eq_id = int(raw_eq_id)
    except (TypeError, ValueError):
        return web.json_response(
            {"status": "error", "message": "jeedom_eq_id (int) requis"}, status=400
        )

    snapshot = request.app.get("topology")
    eq = snapshot.eq_logics.get(eq_id) if snapshot else None
    if eq is None:
        return web.json_response(
            {"status": "error", "message": f"Équipement {eq_id} introuvable"}, status=404
        )

    data_dir = _resolve_data_dir(request)
    confidence_policy = request.app.get("confidence_policy") or _DEFAULT_CONFIDENCE_POLICY
    synced_decision = (request.app.get("publications") or {}).get(eq_id)
    published_scope = request.app.get("published_scope")
    scope_included = True
    if published_scope:
        scope_entry = next(
            (
                entry for entry in published_scope.get("equipements", [])
                if _to_int(entry.get("eq_id"), default=0) == eq_id
            ),
            None,
        )
        scope_included = _scope_entry_is_included(eq_id, scope_entry, request.app.get("eligibility"))
    payload = _build_mapping_override_tree(
        eq, snapshot, data_dir, confidence_policy, synced_decision, scope_included=scope_included
    )
    return web.json_response({"status": "ok", "payload": payload})


async def _handle_mapping_override_save(request: web.Request) -> web.Response:
    """POST /action/mapping_override — Story 16.5 (AC9) : persiste un override de type.

    Appelle `overrides.save_override(...)` (câblage HTTP du gap identifié). Valide
    `jeedom_eq_id`/`jeedom_cmd_id` contre le référentiel équipement (404 si inconnu).
    Ne touche JAMAIS le `generic_type` natif (D10). Jamais appelé par le pipeline de sync.
    """
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"status": "error", "message": "Invalid JSON"}, status=400)
    payload = data.get("payload", {}) if isinstance(data, dict) else {}

    eq_id = payload.get("jeedom_eq_id")
    cmd_id = payload.get("jeedom_cmd_id")
    ha_entity_type = payload.get("ha_entity_type")
    if not isinstance(eq_id, int) or isinstance(eq_id, bool):
        return web.json_response(
            {"status": "error", "message": "jeedom_eq_id (int) requis"}, status=400
        )
    if not isinstance(cmd_id, int) or isinstance(cmd_id, bool):
        return web.json_response(
            {"status": "error", "message": "jeedom_cmd_id (int) requis"}, status=400
        )
    if not isinstance(ha_entity_type, str) or not ha_entity_type:
        return web.json_response(
            {"status": "error", "message": "ha_entity_type doit être une chaîne non vide"},
            status=400,
        )

    snapshot = request.app.get("topology")
    eq = snapshot.eq_logics.get(eq_id) if snapshot else None
    if eq is None:
        return web.json_response(
            {"status": "error", "message": f"Équipement {eq_id} introuvable"}, status=404
        )
    if not any(c.id == cmd_id for c in eq.cmds):
        return web.json_response(
            {"status": "error", "message": f"Commande {cmd_id} introuvable pour l'équipement {eq_id}"},
            status=404,
        )

    data_dir = _resolve_data_dir(request)
    try:
        save_override(eq_id, cmd_id, {"ha_entity_type": ha_entity_type}, data_dir)
    except ValueError as exc:
        return web.json_response(
            {"status": "error", "message": str(exc)}, status=500
        )

    _LOGGER.info(
        "[OVERRIDES] Override HA sauvegardé via UI eq_id=%d cmd_id=%d type=%s",
        eq_id, cmd_id, ha_entity_type,
    )
    return web.json_response({
        "status": "ok",
        "payload": {
            "jeedom_eq_id": eq_id,
            "jeedom_cmd_id": cmd_id,
            "ha_entity_type": ha_entity_type,
            "override_applied": True,
        },
    })


async def _handle_mapping_override_revert(request: web.Request) -> web.Response:
    """POST /action/mapping_override_revert — Story 16.5 (AC10) : retour au mode auto.

    Supprime l'override de commande (`remove_override`) ou d'équipement
    (`remove_equipment_override`) selon la présence de `jeedom_cmd_id`. Ne touche
    jamais le `generic_type` natif (D10).

    Fix CC-19 (Story 19.3, AC3) : le retour « équipement complet » (`jeedom_cmd_id`
    absent) ne doit pas se limiter à l'override équipement (`equipment_overrides[eq_id]`) —
    il doit AUSSI purger tout override TYPE par commande (`overrides[eq_id:cmd_id]`)
    appartenant à cet équipement. Avant ce fix, un override TYPE par commande survivait au
    « Revenir au mode automatique », laissant l'UI dans un état incohérent. La purge
    n'utilise que les primitives CRUD existantes (`list_overrides`/`remove_override`/
    `remove_equipment_override`) — jamais de réécriture manuelle du JSON.
    """
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"status": "error", "message": "Invalid JSON"}, status=400)
    payload = data.get("payload", {}) if isinstance(data, dict) else {}

    eq_id = payload.get("jeedom_eq_id")
    cmd_id = payload.get("jeedom_cmd_id")
    if not isinstance(eq_id, int) or isinstance(eq_id, bool):
        return web.json_response(
            {"status": "error", "message": "jeedom_eq_id (int) requis"}, status=400
        )
    if cmd_id is not None and (not isinstance(cmd_id, int) or isinstance(cmd_id, bool)):
        return web.json_response(
            {"status": "error", "message": "jeedom_cmd_id doit être un int ou absent"},
            status=400,
        )

    snapshot = request.app.get("topology")
    eq = snapshot.eq_logics.get(eq_id) if snapshot else None
    if eq is None:
        return web.json_response(
            {"status": "error", "message": f"Équipement {eq_id} introuvable"}, status=404
        )

    data_dir = _resolve_data_dir(request)
    if isinstance(cmd_id, int):
        removed = remove_override(eq_id, cmd_id, data_dir)
        scope = "command"
        removed_commands = [cmd_id] if removed else []
    else:
        # CC-19 (Story 19.3, AC3) — purger tous les overrides TYPE par commande de cet
        # équipement avant de supprimer l'override équipement, sinon ils survivent au retour
        # au mode automatique (bug historique : seul `equipment_overrides` était nettoyé).
        parsed_keys = (parse_override_key(key) for key in list_overrides(data_dir))
        eq_cmd_ids = sorted(cid for eid, cid in parsed_keys if eid == eq_id)
        removed_commands = [cid for cid in eq_cmd_ids if remove_override(eq_id, cid, data_dir)]
        removed = remove_equipment_override(eq_id, data_dir)
        scope = "equipment"

    _LOGGER.info(
        "[OVERRIDES] Retour mode auto via UI eq_id=%d scope=%s removed=%s removed_commands=%s",
        eq_id, scope, removed, removed_commands,
    )
    return web.json_response({
        "status": "ok",
        "payload": {
            "jeedom_eq_id": eq_id,
            "scope": scope,
            "removed": removed,
            "removed_commands": removed_commands,
        },
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

    # Story 4.1-fix — Lookup pour déterminer la présence HA réelle.
    # has_pending_home_assistant_changes est un XOR (desired != actual) : il ne
    # peut PAS servir de proxy de présence HA (terrain 2026-03-27 : 69 faux positifs).
    # Les vrais signaux sont publications[eq_id].active_or_alive et pending_discovery_unpublish.
    pending_discovery_unpublish = request.app.get("pending_discovery_unpublish") or {}

    # Story 15.2 — Lecture seule de StateSynchronizer.list_state_targets() (Story 12.1/12.2)
    # pour exposer le statut de streaming runtime déjà résolu, sans réouvrir sync/state.py.
    state_sync = request.app.get("state_synchronizer")
    if state_sync is not None:
        streaming_targets = {
            (t["eq_id"], t["cmd_id"]) for t in state_sync.list_state_targets()
        }
    else:
        streaming_targets = set()

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
        family_reason_code = None

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
                    family_reason_code = map_result.reason_code
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

                        reason_details = map_result.reason_details or {}
                        matched_commands = []
                        for c in eq.cmds:
                            if c.id not in mapped_cmd_ids:
                                continue
                            entry = {
                                "cmd_id": c.id,
                                "cmd_name": c.name,
                                "generic_type": c.generic_type,
                            }
                            state_class = reason_details.get("state_class")
                            if state_class:
                                entry["state_class"] = state_class
                                unit_of_measurement = reason_details.get("unit_of_measurement")
                                if unit_of_measurement:
                                    entry["unit_of_measurement"] = unit_of_measurement
                            if (eq_id, c.id) in streaming_targets:
                                entry["streaming"] = True
                            matched_commands.append(entry)
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
                    reason_code = "no_projection_possible"
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

        # Story 16.4 — drill-down commande override-aware (lecture seule, additif).
        _enrich_command_drilldown(eq, topology, map_result, matched_commands, unmatched_commands)
        publication_override = _build_publication_override_diag(reason_code, pub_decision)

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
        # Story 15.3 — Visibilité parité FAN -> switch (epic 14), lecture seule.
        if family_reason_code == "switch_fan_on_off_state":
            eq_dict["fan_switch_parity"] = True
        # Story 16.4 (AC4) — override de publication (Story 16.3) exposé additivement,
        # uniquement s'il a été appliqué (aucune clé nulle sinon).
        if publication_override is not None:
            eq_dict["publication_override"] = publication_override
        equipments.append(eq_dict)
        room_key = (eq.object_id, object_name)
        rooms_equips.setdefault(room_key, []).append(eq_dict)

    summary = build_summary(equipments)
    summary["compteurs"] = build_ui_counters(equipments)
    summary["home_statut"] = compute_home_statut(equipments)
    # Story 15.2 — Visibilité globale de la capacité streaming (epic 12), lecture seule.
    summary["streaming_actif"] = bool(state_sync.is_active) if state_sync is not None else False
    summary["streaming_cibles_count"] = len(streaming_targets)
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


async def _handle_system_state_listeners(request: web.Request) -> web.Response:
    """Handle GET /system/state_listeners — published vague-1 (eq_id, cmd_id) targets.

    Story 12.1 (R1): authoritative list the PHP plugin uses to register a Jeedom
    listener on exactly the published sensor/binary_sensor info commands. Mapping
    authority stays single-sourced in the daemon (state ⊆ discovery, AC#5).
    """
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response(
            {"status": "error", "message": "Unauthorized"},
            status=401,
        )

    state_sync = request.app.get("state_synchronizer")
    listeners = state_sync.list_state_targets() if state_sync is not None else []
    return web.json_response({
        "action": "system.state_listeners",
        "status": "ok",
        "listeners": listeners,
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })



# ---------------------------------------------------------------------------
# Story 5.1 — Façade backend unique d'opérations HA
# ---------------------------------------------------------------------------

_INTENTIONS_VALIDES = frozenset(("publier", "supprimer"))
_PORTEES_VALIDES = frozenset(("global", "piece", "equipement"))


def _evaluate_for_action(
    eq_id: int,
    topology,
    eligibility,
    *,
    mapper_registry,
    confidence_policy: str,
    persisted_overrides,
    persisted_equipment_overrides,
):
    """Story 19.4 — `evaluate_equipment()` frais pour une action (« Publier »).

    Même appel que le sync, sur la topologie et l'éligibilité du dernier sync (pas de nouveau
    payload Jeedom), avec les overrides relus au clic. None si l'équipement est inconnu ou
    inéligible.
    """
    result = (eligibility or {}).get(eq_id)
    eq = topology.eq_logics.get(eq_id) if topology is not None else None
    if result is None or eq is None or not getattr(result, "is_eligible", False):
        return None
    return evaluate_equipment(
        eq,
        topology,
        result,
        mapper_registry=mapper_registry,
        confidence_policy=confidence_policy,
        persisted_overrides=persisted_overrides,
        persisted_equipment_overrides=persisted_equipment_overrides,
    )


async def _replay_pending_for_action(
    eq_id: int,
    *,
    publisher,
    mqtt_bridge,
    pending_discovery_unpublish: Dict[int, object],
    pending_local_cleanup: Dict[int, str],
) -> None:
    """Story 19.4 — rejoue, avant de republier, les nettoyages reportés de CET équipement.

    Même ordre que le sync (rejeu en début de cycle, puis publication) : un report encore
    en attente est exécuté au lieu d'être oublié, puis la décision fraîche republie ce qui
    doit l'être.
    """
    pending_value = pending_discovery_unpublish.get(eq_id)
    if pending_value is not None and mqtt_bridge and mqtt_bridge.is_connected:
        entity_type, node_ids = _pending_unpublish_parts(pending_value)
        if await publisher.unpublish_by_eq_id(eq_id, entity_type=entity_type, node_ids=node_ids):
            pending_discovery_unpublish.pop(eq_id, None)
    pending_topic = pending_local_cleanup.get(eq_id)
    if pending_topic is not None and mqtt_bridge and mqtt_bridge.is_connected:
        if _clear_local_availability_topic(mqtt_bridge, eq_id, pending_topic):
            pending_local_cleanup.pop(eq_id, None)


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
                node_ids = _collect_unpublish_node_ids(previous_decision.mapping_result)
            elif mappings.get(eq_id) is not None:
                entity_type = mappings[eq_id].ha_entity_type
                node_ids = _collect_unpublish_node_ids(mappings[eq_id])
            else:
                entity_type = "light"
                node_ids = []

            unpublish_ok = await publisher.unpublish_by_eq_id(eq_id, entity_type=entity_type, node_ids=node_ids)
            await asyncio.sleep(_action_delay)
            if not unpublish_ok:
                _defer_discovery_unpublish(pending_discovery_unpublish, eq_id, entity_type, node_ids=node_ids)
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
                new_decision = PublicationDecision(
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
                publications[eq_id] = new_decision
                _sync_publication_decision_refs(previous_decision.mapping_result, new_decision)
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
                _sync_publication_decision_refs(mapping, resolved_decision)

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
        save_publications_cache(publications, _resolve_data_dir(request))
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

    # --- Branche publier (Story 5.2 ; Story 19.4 : mini-sync) ---
    # « Publier » prend la MÊME décision que le sync : `evaluate_equipment()` frais (overrides
    # relus une fois par clic, politique de confiance du dernier sync), puis le post-traitement
    # partagé `apply_publication_decision()` et la dépublication par candidat. Le filtre de
    # scope (`_scope_entry_is_included`) s'applique après la décision (AC3).
    scope_entries = {
        _to_int(entry.get("eq_id"), default=0): entry
        for entry in published_scope.get("equipements", [])
    }
    publisher = DiscoveryPublisher(mqtt_bridge)
    publisher_registry = PublisherRegistry(publisher)
    data_dir = _resolve_data_dir(request)
    overrides_cache = list_overrides(data_dir)
    equipment_overrides_cache = list_equipment_overrides(data_dir)
    mapper_registry = MapperRegistry()
    confidence_policy = request.app.get("confidence_policy") or _DEFAULT_CONFIDENCE_POLICY
    if confidence_policy not in _VALID_CONFIDENCE_POLICIES:
        confidence_policy = _DEFAULT_CONFIDENCE_POLICY
    boot_cache = request.app.get("boot_cache", {})

    equipements_inclus = 0
    equipements_publies_ou_crees = 0
    ecarts_resolus = 0
    skips = 0
    publish_errors = 0
    _action_delay = max(0.1, 10.0 / max(1, len(eq_ids)))

    for eq_id in eq_ids:
        scope_entry = scope_entries.get(eq_id)
        previous_decision = publications.get(eq_id)
        evaluation = _evaluate_for_action(
            eq_id,
            topology,
            eligibility,
            mapper_registry=mapper_registry,
            confidence_policy=confidence_policy,
            persisted_overrides=overrides_cache,
            persisted_equipment_overrides=equipment_overrides_cache,
        )
        mapping = evaluation.mapping if evaluation is not None else None
        if mapping is None:
            mapping = mappings.get(eq_id)
        is_included = _scope_entry_is_included(eq_id, scope_entry, eligibility)

        if is_included:
            equipements_inclus += 1
            if evaluation is None or evaluation.mapping is None:
                skips += 1
                continue

            await _replay_pending_for_action(
                eq_id,
                publisher=publisher,
                mqtt_bridge=mqtt_bridge,
                pending_discovery_unpublish=pending_discovery_unpublish,
                pending_local_cleanup=pending_local_cleanup,
            )
            decision, config_published = await apply_publication_decision(
                eq_id,
                evaluation.mapping,
                evaluation,
                previous_decision,
                topology,
                is_first_sync=False,
                boot_cache=boot_cache,
                publisher=publisher,
                publisher_registry=publisher_registry,
                mqtt_bridge=mqtt_bridge,
                pending_discovery_unpublish=pending_discovery_unpublish,
                mapping_counters={},
                publications=publications,
                nouveaux_eq_ids=set(),
            )
            mappings[eq_id] = evaluation.mapping
            if await _unpublish_refused_candidates(
                eq_id,
                previous_decision,
                decision,
                publisher=publisher,
                mqtt_bridge=mqtt_bridge,
                pending_discovery_unpublish=pending_discovery_unpublish,
                pending_local_cleanup=pending_local_cleanup,
            ):
                ecarts_resolus += 1
            await asyncio.sleep(_action_delay)

            # Revue Codex P2 (PR #180) : un secondaire accepté dont la publication a
            # échoué (`_publish_additional_sensors` : `active_or_alive` n'est vrai qu'en
            # cas de succès) fait compter l'équipement en erreur, comme l'ancien chemin.
            secondary_failed = any(
                sec.should_publish and not sec.active_or_alive
                for sec in evaluation.secondary_decisions or []
            )
            if decision.should_publish:
                if config_published and decision.active_or_alive and not secondary_failed:
                    equipements_publies_ou_crees += 1
                else:
                    publish_errors += 1
            elif secondary_failed:
                publish_errors += 1
            elif any(
                getattr(getattr(s, "publication_decision_ref", None), "discovery_published", False)
                for s in evaluation.mapping.additional_mappings or []
            ):
                equipements_publies_ou_crees += 1
            else:
                skips += 1
            continue

        if not _is_currently_published_in_ha(eq_id, previous_decision, pending_discovery_unpublish):
            continue

        if previous_decision and previous_decision.mapping_result is not None:
            entity_type = previous_decision.mapping_result.ha_entity_type
            node_ids = _collect_unpublish_node_ids(previous_decision.mapping_result)
        elif mapping is not None:
            entity_type = mapping.ha_entity_type
            node_ids = _collect_unpublish_node_ids(mapping)
        else:
            entity_type = "light"
            node_ids = []

        unpublish_ok = await publisher.unpublish_by_eq_id(eq_id, entity_type=entity_type, node_ids=node_ids)
        await asyncio.sleep(_action_delay)
        if not unpublish_ok:
            _defer_discovery_unpublish(pending_discovery_unpublish, eq_id, entity_type, node_ids=node_ids)
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
            new_decision = PublicationDecision(
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
            publications[eq_id] = new_decision
            _sync_publication_decision_refs(previous_decision.mapping_result, new_decision)
        elif mapping is not None:
            publications[eq_id] = _scope_excluded_decision(mapping, topology)

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
    save_publications_cache(publications, _resolve_data_dir(request))
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


def _normalize_state_update_body(body: Any) -> Dict[str, Any]:
    """Accept direct JSON calls and the PHP relay wrapper `{payload: {...}}`."""
    if not isinstance(body, dict):
        return {}
    wrapped = body.get("payload")
    if isinstance(wrapped, dict) and ("eq_id" in wrapped or "cmd_id" in wrapped):
        return wrapped
    return body


async def _handle_action_state_update(request: web.Request) -> web.Response:
    """Story 12.1 — inbound Jeedom info value → MQTT state_topic (vague 1).

    Event-driven channel: a Jeedom ``#listener#`` on the info commands of published
    sensor/binary_sensor eqLogics relays (eq_id, cmd_id, value) here via
    ``callDaemon()``. The daemon resolves the discovery-declared state_topic from
    the publication registry and publishes, so HA entities leave ``unknown``.
    """
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        raw_body = await request.json()
    except Exception:
        return web.json_response(
            {"status": "error", "message": "Corps de requête JSON invalide."}, status=400
        )

    body = _normalize_state_update_body(raw_body)
    eq_id = body.get("eq_id")
    cmd_id = body.get("cmd_id")
    value = body.get("value")
    if eq_id is None or cmd_id is None:
        return web.json_response(
            {"status": "error", "message": "Champs 'eq_id' et 'cmd_id' obligatoires."},
            status=400,
        )

    state_sync = request.app.get("state_synchronizer")
    if state_sync is None:
        return web.json_response(
            {"status": "error", "message": "State synchronizer indisponible."}, status=503
        )

    published = await state_sync.handle_state_message(eq_id, cmd_id, value)
    return web.json_response({"status": "ok", "published": bool(published)})


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
    app["scenario_publications"] = {}  # Dict[int, PublicationDecision] — scénarios Story 10.1
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
    app.router.add_post("/system/overrides/preview", _handle_overrides_preview)
    # Story 16.5 — UI de configuration par équipement : arbre par commande (GET),
    # persistance override (POST) et retour au mode auto (POST).
    app.router.add_get("/system/mapping_overrides/{eq_id}", _handle_mapping_overrides_get)
    app.router.add_post("/action/mapping_override", _handle_mapping_override_save)
    app.router.add_post("/action/mapping_override_revert", _handle_mapping_override_revert)
    app.router.add_get("/system/published_scope", _handle_system_published_scope)
    # Story 5.1 — Façade backend unique des opérations HA
    app.router.add_post("/action/execute", _handle_action_execute)
    # Story 12.1 — canal inbound Jeedom → daemon pour le streaming d'état (vague 1)
    app.router.add_post("/action/state_update", _handle_action_state_update)
    app.router.add_get("/system/state_listeners", _handle_system_state_listeners)
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
