"""decision_export.py — Story 24.2 : export JSON versionné du contrat de décision.

Rôle :
    Rendre lisible, sans SSH, ce que le plugin a décidé pour chaque équipement, chaque
    commande et chaque scénario (décisions du dernier sync ou du dernier « Publier »).
    Le document est écrit dans ``data/jeedom2ha_decision_export.json`` (fichier séparé de
    ``jeedom2ha_cache.json``, qui reste inchangé) et rendu par ``GET /system/decision_export``.

Garde-fous :
    - Aucune décision n'est recalculée ici : le sync et « Publier » mémorisent le verdict
      d'``evaluate_equipment()`` (``make_equipment_record``) ; ce module le met en forme.
      Le résolveur par commande est ``select_covering_decision`` (CC-47), appelé à
      l'identique d'``evaluate_equipment()``.
    - Identifiants seulement : aucun nom (équipement, pièce, commande, scénario), aucun secret.
    - Les ``logical_id`` sont bruts (alignement hors plugin) : fichier réservé à
      l'administrateur (mode 600), jamais versé au dépôt ni écrit au journal.
    - Politique de version : un champ ajouté ne change pas ``schema_version`` ; un champ
      renommé, retiré ou de sens changé le porte à 2.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from discovery.publisher import DiscoveryPublisher
from mapping.button import ScenarioButtonMapper
from mapping.overrides import mapping_cmd_ids, parse_override_key
from models.evaluate_equipment import evaluate_equipment, select_covering_decision, step_for_decision

_LOGGER = logging.getLogger(__name__)

EXPORT_FILENAME = "jeedom2ha_decision_export.json"
SCHEMA_VERSION = 1

# Raisons propres à l'export (aucune n'existe dans le pipeline de décision).
REASON_SCENARIO_BUTTON = "scenario_button"      # code déjà produit par le sync pour un scénario actif
REASON_SCENARIO_INACTIVE = "scenario_inactive"  # scénario inactif : jamais de bouton dans HA
REASON_NO_SYNC_DECISION = "no_sync_decision"    # équipement sans verdict mémorisé (jamais synchronisé)
REASON_SCOPE_EXCLUDED = "excluded"              # hors périmètre publié (identique à `_scope_excluded_decision`)
STEP_SCOPE = "scope"                            # filtre de périmètre publié, appliqué après étape 4
STEP_ELIGIBILITY = "1"

DECISION_PUBLISHED = "published"
DECISION_PARTIAL = "partial"            # principal refusé, au moins un secondaire à publier (forme 579/585)
DECISION_NOT_PUBLISHED = "not_published"

STATE_STREAMED = "streamed"
STATE_OPTIMISTIC = "optimistic"
STATE_NONE = "none"

# Domaines HA dotés d'un command_topic : sans retour d'état en streaming, ils restent optimistes.
_ACTUATOR_TYPES = frozenset({"light", "cover", "switch", "climate", "alarm_control_panel"})

_PUBLICATION_VALUES = frozenset({"exclude", "force_publish"})


@dataclass
class DecisionMemo:
    """Verdicts mémorisés au sync et au « Publier » (RAM), source de l'export.

    ``equipments`` : eq_id -> enregistrement JSON-sérialisable (``make_equipment_record``).
    ``config`` : réglages de filtrage du dernier sync (``sync_config`` du payload PHP).
    """

    sync_at: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=lambda: {
        "excluded_plugins": [], "excluded_piece_ids": [],
    })
    equipments: Dict[int, Dict[str, Any]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Overrides appliqués / courants
# ---------------------------------------------------------------------------

def _empty_overrides() -> Dict[str, Any]:
    return {"publication": None, "commands": {}}


def _clean_publication(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value in _PUBLICATION_VALUES else None


def index_overrides(
    overrides: Optional[Dict[str, dict]],
    equipment_overrides: Optional[Dict[str, dict]],
) -> Dict[int, Dict[str, Any]]:
    """Regroupe les overrides persistés par eq_id, sous une forme canonique comparable.

    ``{eq_id: {"publication": str|None, "commands": {cmd_id: {"ha_type", "publication"}}}}``.
    Un eq_id sans override n'a pas d'entrée (lire avec ``.get(eq_id) or _empty_overrides()``).
    """
    indexed: Dict[int, Dict[str, Any]] = {}

    for key, entry in (equipment_overrides or {}).items():
        try:
            eq_id = int(key)
        except (TypeError, ValueError):
            continue
        publication = _clean_publication((entry or {}).get("publication_override"))
        if publication is not None:
            indexed.setdefault(eq_id, _empty_overrides())["publication"] = publication

    for key, entry in (overrides or {}).items():
        try:
            eq_id, cmd_id = parse_override_key(key)
        except ValueError:
            continue
        entry = entry or {}
        ha_type = entry.get("ha_entity_type")
        ha_type = ha_type if isinstance(ha_type, str) and ha_type else None
        publication = _clean_publication(entry.get("publication_override"))
        if ha_type is None and publication is None:
            continue
        indexed.setdefault(eq_id, _empty_overrides())["commands"][cmd_id] = {
            "ha_type": ha_type, "publication": publication,
        }
    return indexed


# ---------------------------------------------------------------------------
# Mémorisation (sync, « Publier »)
# ---------------------------------------------------------------------------

def _candidate_pairs(evaluation) -> List[Tuple[Any, Any]]:
    """[(mapping, décision)] : primaire d'abord, puis secondaires (ordre natif d'evaluate_equipment)."""
    primary = evaluation.mapping
    if primary is None:
        return []
    pairs = [(primary, evaluation.equipment_decision)]
    pairs.extend(zip(primary.additional_mappings or [], evaluation.secondary_decisions or []))
    return pairs


def make_equipment_record(
    evaluation,
    *,
    eligible: bool,
    scope_excluded: bool,
    applied_overrides: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Verdict mémorisable d'un équipement, construit depuis la sortie d'``evaluate_equipment()``.

    ``eligible=False`` : verdict d'éligibilité (étape 1). ``scope_excluded=True`` : le filtre de
    périmètre publié a refusé l'équipement après la décision (rien n'est publié, quelle que soit
    la décision d'étape 4) ; le verdict mémorisé est celui que le plugin a appliqué.
    """
    pairs = _candidate_pairs(evaluation)
    primary_decision = evaluation.equipment_decision

    if scope_excluded:
        decision, reason, step = DECISION_NOT_PUBLISHED, REASON_SCOPE_EXCLUDED, STEP_SCOPE
    else:
        if primary_decision.should_publish:
            decision = DECISION_PUBLISHED
        elif any(d.should_publish for _m, d in pairs[1:]):
            decision = DECISION_PARTIAL
        else:
            decision = DECISION_NOT_PUBLISHED
        reason = primary_decision.reason
        step = step_for_decision(primary_decision) if eligible else STEP_ELIGIBILITY

    # Même résolution par commande qu'evaluate_equipment() (CC-47) : un seul résolveur.
    candidates: Dict[int, List[Tuple[Any, Any]]] = {}
    for mapping, mapping_decision in pairs:
        for cmd_id in mapping_cmd_ids(mapping):
            candidates.setdefault(cmd_id, []).append((mapping, mapping_decision))
    covering = {
        cmd_id: select_covering_decision(entries, lambda entry: entry[1])[0]
        for cmd_id, entries in candidates.items()
    }

    commands: Dict[int, Dict[str, Any]] = {}
    for cd in evaluation.command_decisions:
        mapping = covering.get(cd.cmd_id)
        commands[cd.cmd_id] = {
            "covered": mapping is not None,
            "decision": DECISION_NOT_PUBLISHED if scope_excluded or not cd.should_publish else DECISION_PUBLISHED,
            "reason": REASON_SCOPE_EXCLUDED if scope_excluded else cd.reason,
            "step": STEP_SCOPE if scope_excluded else cd.step,
            "entity_unique_id": mapping.ha_unique_id if mapping is not None else None,
            "ha_type": mapping.ha_entity_type if mapping is not None else None,
        }

    return {
        "decision": decision,
        "reason": reason,
        "step": step,
        "commands": commands,
        "overrides": applied_overrides or _empty_overrides(),
    }


def make_ineligible_record(
    eq,
    snapshot,
    eligibility,
    *,
    applied_overrides: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Verdict d'un équipement inéligible (étape 1), par le chemin I1 d'``evaluate_equipment()``.

    L'éligibilité est consommée telle quelle (jamais recalculée) ; le registre de mappeurs n'est
    pas utilisé sur ce chemin.
    """
    evaluation = evaluate_equipment(eq, snapshot, eligibility, mapper_registry=None)
    return make_equipment_record(
        evaluation, eligible=False, scope_excluded=False, applied_overrides=applied_overrides,
    )


# ---------------------------------------------------------------------------
# Construction du document
# ---------------------------------------------------------------------------

def _utc_z(value: Optional[datetime] = None) -> str:
    return (value or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _entity_row(
    publisher: DiscoveryPublisher,
    mapping,
    role: str,
    decision,
    snapshot,
    eq_id: int,
    streamed: Set[Tuple[int, int, str]],
) -> Dict[str, Any]:
    """Une entité mappée : identifiants lus dans le payload de découverte réel (AC6)."""
    unique_id = mapping.ha_unique_id
    entity_id_expected = None
    try:
        payload = publisher.build_discovery_payload(mapping, snapshot)
    except Exception:  # un mapping hors contrat ne doit jamais empêcher l'export
        payload = None
    if payload:
        unique_id = payload.get("unique_id", unique_id)
        entity_id_expected = payload.get("default_entity_id")

    published = bool(getattr(decision, "discovery_published", False))
    ha_type = mapping.ha_entity_type
    if published and any((eq_id, cmd_id, ha_type) in streamed for cmd_id in mapping_cmd_ids(mapping)):
        state_source = STATE_STREAMED
    elif published and ha_type in _ACTUATOR_TYPES:
        state_source = STATE_OPTIMISTIC
    else:
        state_source = STATE_NONE
    return {
        "unique_id": unique_id,
        "ha_type": ha_type,
        "role": role,
        "entity_id_expected": entity_id_expected,
        "discovery_published": published,
        "state_source": state_source,
    }


def _equipment_entities(publisher, eq_id, mapping, publication, snapshot, streamed) -> List[Dict[str, Any]]:
    if mapping is None:
        return []
    rows = [_entity_row(publisher, mapping, "primary", publication, snapshot, eq_id, streamed)]
    for secondary in mapping.additional_mappings or []:
        rows.append(_entity_row(
            publisher, secondary, "secondary",
            getattr(secondary, "publication_decision_ref", None), snapshot, eq_id, streamed,
        ))
    return sorted(rows, key=lambda row: row["unique_id"])


def _override_view(applied: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "publication": applied.get("publication"),
        "types": {
            str(cmd_id): entry["ha_type"]
            for cmd_id, entry in sorted(applied.get("commands", {}).items())
            if entry.get("ha_type")
        },
    }


def _command_override(applied: Dict[str, Any], cmd_id: int) -> Optional[Dict[str, Any]]:
    entry = applied.get("commands", {}).get(cmd_id)
    if not entry:
        return None
    return {"ha_type": entry.get("ha_type"), "publication": entry.get("publication")}


def _equipment_row(eq, record, mapping, publication, snapshot, publisher, streamed, current_overrides):
    missing = record is None
    applied = (record or {}).get("overrides") or _empty_overrides()
    now_overrides = current_overrides.get(eq.id) or _empty_overrides()
    commands_memo = (record or {}).get("commands", {})

    commands = []
    seen_cmd_ids: Set[int] = set()
    for cmd in sorted(eq.cmds, key=lambda c: c.id):
        if cmd.id in seen_cmd_ids:  # commande en double dans le snapshot : une seule ligne par cmd_id
            continue
        seen_cmd_ids.add(cmd.id)
        memo = commands_memo.get(cmd.id)
        if memo is None:
            memo = {
                "covered": False, "decision": DECISION_NOT_PUBLISHED,
                "reason": REASON_NO_SYNC_DECISION, "step": None,
                "entity_unique_id": None, "ha_type": None,
            }
        commands.append({
            "cmd_id": cmd.id,
            "logical_id": cmd.logical_id,
            "generic_type": cmd.generic_type,
            "type": cmd.type,
            "sub_type": cmd.sub_type,
            "covered": memo["covered"],
            "decision": memo["decision"],
            "reason": memo["reason"],
            "step": memo["step"],
            "entity_unique_id": memo["entity_unique_id"],
            "ha_type": memo["ha_type"],
            "override": _command_override(applied, cmd.id),
        })

    return {
        "kind": "equipment",
        "key": f"eq:{eq.id}",
        "eq_id": eq.id,
        "logical_id": eq.logical_id,
        "plugin": eq.eq_type_name,
        "piece_id": eq.object_id,
        "enabled": eq.is_enable,
        "generic_type": eq.generic_type,
        "homekit_exposed": eq.homekit_exposed,
        "homekit_exposed_source": eq.homekit_exposed_source,
        "homekit_exposed_effective": eq.homekit_exposed_effective,
        "decision": DECISION_NOT_PUBLISHED if missing else record["decision"],
        "reason": REASON_NO_SYNC_DECISION if missing else record["reason"],
        "step": None if missing else record["step"],
        "exclusion_source": eq.exclusion_source if eq.is_excluded else None,
        "overrides": _override_view(applied),
        "pending_changes": now_overrides != applied,
        "entities": _equipment_entities(publisher, eq.id, mapping, publication, snapshot, streamed),
        "commands": commands,
    }


def _scenario_row(scenario, scenario_publication, snapshot, publisher) -> Dict[str, Any]:
    mapping = ScenarioButtonMapper().map(scenario)
    payload = None
    try:
        payload = publisher.build_discovery_payload(mapping, snapshot)
    except Exception:
        payload = None
    payload = payload or {}
    published = bool(scenario.is_active and getattr(scenario_publication, "discovery_published", False))
    return {
        "kind": "scenario",
        "key": f"scenario:{scenario.id}",
        "scenario_id": scenario.id,
        "active": scenario.is_active,
        "homekit_exposed": scenario.homekit_exposed,
        "homekit_exposed_source": scenario.homekit_exposed_source,
        "homekit_exposed_effective": scenario.homekit_exposed_effective,
        "decision": DECISION_PUBLISHED if scenario.is_active else DECISION_NOT_PUBLISHED,
        "reason": REASON_SCENARIO_BUTTON if scenario.is_active else REASON_SCENARIO_INACTIVE,
        "entity": {
            "unique_id": payload.get("unique_id", mapping.ha_unique_id),
            "ha_type": mapping.ha_entity_type,
            "entity_id_expected": payload.get("default_entity_id"),
            "discovery_published": published,
            "state_source": STATE_NONE,
        },
    }


def build_decision_export(
    *,
    snapshot,
    memo: DecisionMemo,
    mappings: Dict[int, Any],
    publications: Dict[int, Any],
    scenario_publications: Dict[int, Any],
    streaming_targets: Iterable[Dict[str, Any]],
    current_overrides: Dict[int, Dict[str, Any]],
    plugin_version: str,
    confidence_policy: str,
    generated_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Document ``schema_version: 1`` : tableaux triés par eq_id, cmd_id, scenario_id (comparables par diff)."""
    publisher = DiscoveryPublisher(None)  # constructeurs de payload purs : aucune I/O MQTT
    streamed = {
        (int(t["eq_id"]), int(t["cmd_id"]), str(t["ha_type"])) for t in streaming_targets
    }

    equipments = [
        _equipment_row(
            snapshot.eq_logics[eq_id], memo.equipments.get(eq_id), mappings.get(eq_id),
            publications.get(eq_id), snapshot, publisher, streamed, current_overrides,
        )
        for eq_id in sorted(snapshot.eq_logics)
    ]
    scenarios = [
        _scenario_row(snapshot.scenarios[sc_id], scenario_publications.get(sc_id), snapshot, publisher)
        for sc_id in sorted(snapshot.scenarios)
    ]
    config = memo.config
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_z(generated_at),
        "sync_at": memo.sync_at,
        "producer": {"plugin_version": plugin_version, "confidence_policy": confidence_policy},
        "config": {
            "excluded_plugins": list(config.get("excluded_plugins", [])),
            "excluded_piece_ids": list(config.get("excluded_piece_ids", [])),
        },
        "totals": {
            "equipments": len(equipments),
            "commands": sum(len(row["commands"]) for row in equipments),
            "scenarios": len(scenarios),
        },
        "equipments": equipments,
        "scenarios": scenarios,
    }


def normalize_export_config(sync_config: Any) -> Dict[str, Any]:
    """Réglages de filtrage du payload de sync -> identifiants seulement (plugins, pièces)."""
    sync_config = sync_config if isinstance(sync_config, dict) else {}
    plugins = sync_config.get("excluded_plugins")
    pieces = sync_config.get("excluded_piece_ids")
    clean_pieces = set()
    for value in pieces if isinstance(pieces, list) else []:
        if isinstance(value, bool):
            continue
        try:
            clean_pieces.add(int(value))
        except (TypeError, ValueError):
            continue
    return {
        "excluded_plugins": sorted({str(p) for p in plugins if isinstance(p, str) and p}
                                   if isinstance(plugins, list) else set()),
        "excluded_piece_ids": sorted(clean_pieces),
    }


# ---------------------------------------------------------------------------
# Écriture atomique
# ---------------------------------------------------------------------------

def write_decision_export(document: Dict[str, Any], data_dir: str) -> bool:
    """Écrit le document (fichier temporaire, fsync, ``os.replace``), mode 600.

    Ne lève jamais : un échec d'export ne doit pas faire échouer un sync ni un « Publier ».
    Le journal ne reçoit que le nombre d'équipements et le chemin, jamais le contenu.
    """
    if not os.path.isdir(data_dir):
        _LOGGER.warning("[EXPORT] data_dir introuvable : %s — export de décision non écrit", data_dir)
        return False
    path = os.path.join(data_dir, EXPORT_FILENAME)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=data_dir,
            prefix=".jeedom2ha_decision_export.", suffix=".tmp", delete=False,
        ) as temp_file:
            temp_path = temp_file.name
            json.dump(document, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
        temp_path = None
        _LOGGER.info(
            "[EXPORT] Export de décision écrit : %d équipements, %d scénarios (%s)",
            document["totals"]["equipments"], document["totals"]["scenarios"], path,
        )
        return True
    except Exception as exc:
        _LOGGER.error("[EXPORT] Échec écriture export de décision : %s", type(exc).__name__)
        return False
    finally:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
