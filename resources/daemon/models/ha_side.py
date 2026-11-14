"""ha_side.py — Front v2, Lot 3 : le « côté Home Assistant » d'un équipement, en lecture seule.

Champs additifs pour l'interface (contrat « Front v2 — section 4 ») :

- ``entity_ha_fields`` : identifiant, nom, appareil, classe, unité, pilotable et capacités
  d'une entité, LUS dans le payload de découverte réel (``DiscoveryPublisher.build_discovery_payload``,
  le même constructeur que la publication et l'export de décision) — jamais une seconde formule ;
- ``command_fields`` : type, sous-type et état relié d'une commande Jeedom ;
- ``build_hints`` : conseils prudents (« Publié mais améliorable ») ; en cas de doute, aucun ;
- ``preview_entities`` / ``entity_id_changes`` : aperçu en entités d'un override, à partir des
  évaluations déjà calculées par l'aperçu ;
- ``publication_counts`` / ``ha_status`` : dénombrement de ce qui est publié, birth de HA.

Aucune fonction de ce module ne publie, n'écrit sur disque ni ne modifie un mapping ou une
décision : la projection vers Home Assistant est inchangée par construction.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from discovery.publisher import DiscoveryPublisher
from export.decision_export import _FAN_SPEED_GENERIC_TYPES
from mapping.overrides import mapping_cmd_ids

# Constructeurs de payload purs : aucune I/O MQTT (même usage que l'export de décision).
_PUBLISHER = DiscoveryPublisher(None)

HINT_ACTIONS_NOT_LINKED = "actions_not_linked_to_state"
HINT_BINARY_STATE_WITHOUT_ORDERS = "binary_state_without_orders"
HINT_SPEED_NOT_CARRIED = "speed_not_carried"
HINT_NAME_TYPE_MISMATCH = "name_type_mismatch"

# Familles on/off/état du mapper `switch` (mapping/switch.py et mapping/binary_sensor.py).
_SWITCH_FAMILIES = ("ENERGY", "SWITCH", "FAN")

# État binaire -> ordres qui pourraient le piloter. Liste fermée : un état absent de cette
# table ne donne jamais de conseil « sans ordres » (prudence).
_ORDERS_FOR_BINARY_STATE: Dict[str, frozenset] = {
    "BARRIER_STATE": frozenset({"GB_OPEN", "GB_CLOSE", "GB_TOGGLE"}),
    "GARAGE_STATE": frozenset({"GB_OPEN", "GB_CLOSE", "GB_TOGGLE"}),
    "LOCK_STATE": frozenset({"LOCK_OPEN", "LOCK_CLOSE"}),
    "ENERGY_STATE": frozenset({"ENERGY_ON", "ENERGY_OFF"}),
    "SWITCH_STATE": frozenset({"SWITCH_ON", "SWITCH_OFF"}),
    "FAN_STATE": frozenset({"FAN_ON", "FAN_OFF"}),
    "IRRIG_STATE": frozenset({"IRRIG_ON", "IRRIG_OFF"}),
    "FAUCET_STATE": frozenset({"FAUCET_ON", "FAUCET_OFF"}),
    "VALVE_STATE": frozenset({"VALVE_ON", "VALVE_OFF"}),
}

_FAN_ONOFF_GENERIC_TYPES = frozenset({"FAN_STATE", "FAN_ON", "FAN_OFF"})


# ---------------------------------------------------------------------------
# Payload réel
# ---------------------------------------------------------------------------

def discovery_payload(mapping, snapshot) -> Optional[dict]:
    """Payload de découverte réel d'un mapping, ``None`` si non constructible (jamais d'exception)."""
    if mapping is None or snapshot is None:
        return None
    try:
        return _PUBLISHER.build_discovery_payload(mapping, snapshot)
    except Exception:  # un mapping hors contrat ne doit jamais casser une lecture
        return None


def discovery_prefix() -> str:
    """Préfixe de découverte réellement utilisé par le publisher."""
    return getattr(_PUBLISHER, "_topic_prefix", "homeassistant")


def _is_command_key(key: str) -> bool:
    return key.endswith("command_topic") or key == "set_position_topic"


def is_controllable(payload: Optional[dict]) -> Optional[bool]:
    """Pilotable = au moins un topic de commande présent dans le payload. ``None`` sans payload."""
    if payload is None:
        return None
    return any(_is_command_key(key) and value for key, value in payload.items())


def _is_read_key(key: str) -> bool:
    return key.endswith("state_topic") or key in ("position_topic", "current_temperature_topic", "action_topic")


def capabilities_from_payload(ha_entity_type: str, payload: Optional[dict]) -> Optional[List[str]]:
    """Ce que Home Assistant pourra faire de l'entité, lu dans les clés du payload."""
    if payload is None:
        return None
    caps: List[str] = []

    def add(cap: str) -> None:
        if cap not in caps:
            caps.append(cap)

    has_command = bool(payload.get("command_topic"))
    if ha_entity_type in ("light", "switch") and has_command:
        add("on_off")
    if payload.get("brightness_command_topic"):
        add("brightness")
    if ha_entity_type in ("cover", "valve") and has_command:
        add("open_close")
    if ha_entity_type == "cover" and payload.get("payload_stop"):
        add("stop")
    if payload.get("set_position_topic"):
        add("position")
    if payload.get("tilt_command_topic"):
        add("tilt")
    if payload.get("temperature_command_topic"):
        add("temperature")
    if payload.get("mode_command_topic") or payload.get("preset_mode_command_topic"):
        add("mode")
    if ha_entity_type == "alarm_control_panel" and has_command:
        add("mode")
    if ha_entity_type == "lock" and has_command:
        add("lock")
    if ha_entity_type == "button" and has_command:
        add("press")
    if any(_is_read_key(key) and value for key, value in payload.items()):
        add("read")
    return caps


def entity_ha_fields(mapping, snapshot) -> Dict[str, Any]:
    """Champs ``ha_*`` d'une entité, lus dans son payload de découverte réel.

    ``ha_name`` est la valeur publiée telle quelle : ``None`` quand le nom de l'entité double
    celui de l'appareil (convention HA : l'entité prend alors le nom de l'appareil).
    """
    payload = discovery_payload(mapping, snapshot)
    if payload is None:
        return {
            "ha_unique_id": getattr(mapping, "ha_unique_id", None),
            "ha_default_entity_id": None,
            "ha_name": None,
            "ha_device_name": None,
            "ha_device_class": None,
            "ha_unit": None,
            "ha_controllable": None,
            "ha_capabilities": None,
        }
    device = payload.get("device") or {}
    return {
        "ha_unique_id": payload.get("unique_id", mapping.ha_unique_id),
        "ha_default_entity_id": payload.get("default_entity_id"),
        "ha_name": payload.get("name"),
        "ha_device_name": device.get("name"),
        "ha_device_class": payload.get("device_class"),
        "ha_unit": payload.get("unit_of_measurement"),
        "ha_controllable": is_controllable(payload),
        "ha_capabilities": capabilities_from_payload(mapping.ha_entity_type, payload),
    }


def command_fields(cmd) -> Dict[str, Any]:
    """Type, sous-type et état relié (« Valeur » du cœur Jeedom) d'une commande."""
    linked = getattr(cmd, "linked_value", None)
    return {
        "cmd_type": "action" if (getattr(cmd, "type", "") or "").lower() == "action" else "info",
        "cmd_sub_type": getattr(cmd, "sub_type", None),
        "linked_state_cmd_id": linked if isinstance(linked, int) and not isinstance(linked, bool) else None,
    }


# ---------------------------------------------------------------------------
# Évaluation -> entités
# ---------------------------------------------------------------------------

def _entities_with_decisions(evaluation) -> List[tuple]:
    """``(mapping, décision)`` de chaque entité de l'évaluation (principale d'abord)."""
    mapping = getattr(evaluation, "mapping", None)
    if mapping is None:
        return []
    rows = [(mapping, evaluation.equipment_decision)]
    for secondary in mapping.additional_mappings or []:
        rows.append((secondary, secondary.publication_decision_ref))
    return rows


def _will_publish(decision) -> bool:
    return bool(decision is not None and getattr(decision, "should_publish", False))


def preview_entities(evaluation, snapshot) -> List[Dict[str, Any]]:
    """Entités d'une évaluation déjà calculée, sous la forme de l'aperçu (lecture seule)."""
    rows = []
    for mapping, decision in _entities_with_decisions(evaluation):
        fields = entity_ha_fields(mapping, snapshot)
        rows.append({
            "ha_entity_type": mapping.ha_entity_type,
            "ha_unique_id": fields["ha_unique_id"],
            "ha_name": fields["ha_name"],
            "ha_default_entity_id": fields["ha_default_entity_id"],
            "ha_controllable": fields["ha_controllable"],
            "ha_capabilities": fields["ha_capabilities"],
            "will_publish": _will_publish(decision),
            "reason": getattr(decision, "reason", None),
        })
    return rows


def entity_id_changes(before: Iterable[dict], after: Iterable[dict]) -> List[Dict[str, Optional[str]]]:
    """Identifiants d'entité qui changent dans HA entre deux aperçus.

    Seules les entités qui seront publiées comptent (une entité non publiée n'a pas
    d'identifiant dans HA). Appariement par ``ha_unique_id`` : même identifiant unique et
    identifiant d'entité différent -> ``{from, to}`` ; entité qui disparaît -> ``to: None`` ;
    entité qui apparaît -> ``from: None``.
    """
    def index(rows):
        return {
            row.get("ha_unique_id"): row.get("ha_default_entity_id")
            for row in rows
            if row.get("will_publish") and row.get("ha_default_entity_id")
        }

    old, new = index(before), index(after)
    changes = []
    for uid in sorted(set(old) | set(new), key=str):
        if old.get(uid) != new.get(uid):
            changes.append({"from": old.get(uid), "to": new.get(uid)})
    return changes


# ---------------------------------------------------------------------------
# Conseils
# ---------------------------------------------------------------------------

def _hint(code: str, cmd_ids: Iterable[int], details: Dict[str, Any]) -> Dict[str, Any]:
    return {"code": code, "cmd_ids": sorted(set(cmd_ids)), "details": details}


def build_hints(eq, evaluation) -> List[Dict[str, Any]]:
    """Conseils prudents d'un équipement, dérivés de l'évaluation déjà calculée.

    Au plus un conseil par code. En cas de doute, aucun conseil.
    """
    entities = _entities_with_decisions(evaluation)
    carried = {cid for mapping, _ in entities for cid in mapping_cmd_ids(mapping)}
    cmds_by_id = {cmd.id: cmd for cmd in eq.cmds}
    actions = [cmd for cmd in eq.cmds if (cmd.type or "").lower() == "action"]
    action_types = {cmd.generic_type for cmd in actions if cmd.generic_type}

    def carried_states(published_type: str) -> List[Any]:
        states = []
        for mapping, decision in entities:
            if mapping.ha_entity_type != published_type or not _will_publish(decision):
                continue
            for cid in mapping_cmd_ids(mapping):
                cmd = cmds_by_id.get(cid)
                if cmd is not None and (cmd.type or "").lower() == "info":
                    states.append(cmd)
        return states

    hints: List[Dict[str, Any]] = []
    published_binary_states = carried_states("binary_sensor")

    # 1. Ordres On / Off présents mais portés par aucune entité, états publiés en lecture seule.
    families, orders, states = [], [], []
    for family in _SWITCH_FAMILIES:
        family_orders = [
            cmd for cmd in actions
            if cmd.generic_type in (f"{family}_ON", f"{family}_OFF") and cmd.id not in carried
        ]
        family_states = [cmd for cmd in published_binary_states if cmd.generic_type == f"{family}_STATE"]
        if family_orders and family_states:
            families.append(family)
            orders.extend(family_orders)
            states.extend(family_states)
    if orders:
        hints.append(_hint(HINT_ACTIONS_NOT_LINKED, (cmd.id for cmd in orders), {
            "families": families,
            "outputs": len({cmd.id for cmd in states}),
            "state_cmd_ids": sorted({cmd.id for cmd in states}),
            "unlinked_order_cmd_ids": sorted(
                cmd.id for cmd in orders if command_fields(cmd)["linked_state_cmd_id"] is None
            ),
        }))

    # 2. État binaire publié en lecture seule, et AUCUN ordre de sa famille sur l'équipement.
    lonely = [
        cmd for cmd in published_binary_states
        if cmd.generic_type in _ORDERS_FOR_BINARY_STATE
        and not (_ORDERS_FOR_BINARY_STATE[cmd.generic_type] & action_types)
    ]
    if lonely:
        hints.append(_hint(HINT_BINARY_STATE_WITHOUT_ORDERS, (cmd.id for cmd in lonely), {
            "generic_types": sorted({cmd.generic_type for cmd in lonely}),
        }))

    # 3. Ventilateur publié en interrupteur (marche / arrêt) alors que la vitesse existe.
    fan_switch_published = any(
        mapping.ha_entity_type == "switch" and _will_publish(decision)
        and any(
            getattr(cmds_by_id.get(cid), "generic_type", None) in _FAN_ONOFF_GENERIC_TYPES
            for cid in mapping_cmd_ids(mapping)
        )
        for mapping, decision in entities
    )
    speed_cmds = [cmd for cmd in eq.cmds if cmd.generic_type in _FAN_SPEED_GENERIC_TYPES]
    if fan_switch_published and speed_cmds:
        hints.append(_hint(HINT_SPEED_NOT_CARRIED, (cmd.id for cmd in speed_cmds), {
            "carried_as": "switch",
        }))

    # 4. Le nom de l'équipement contredit le type détecté (`name_heuristic_rejection`).
    for mapping, _decision in entities:
        if mapping.reason_code == "name_heuristic_rejection":
            hints.append(_hint(HINT_NAME_TYPE_MISMATCH, mapping_cmd_ids(mapping), {
                "ha_entity_type": mapping.ha_entity_type,
                "matched_keyword": (mapping.reason_details or {}).get("matched_keyword"),
            }))
            break
    return hints


# ---------------------------------------------------------------------------
# Statut
# ---------------------------------------------------------------------------

def ha_status(birth_seen_at: Optional[str]) -> Dict[str, Any]:
    return {"birth_seen_at": birth_seen_at, "discovery_prefix": discovery_prefix()}


def _published(decision) -> bool:
    return bool(getattr(decision, "discovery_published", False))


def publication_counts(present_entries_by_eq: Dict[int, set], scenario_publications: Optional[dict]) -> Dict[str, int]:
    """Dénombrement de ce qui est dans HA d'après la mémoire vive du démon.

    ``present_entries_by_eq`` : pour chaque équipement présent dans HA (même prédicat que
    ``sync_status.published_in_ha``, dépublication différée comprise), l'ensemble des topics de
    découverte ``(type, node_id)`` encore présents — calculé par l'appelant avec les helpers de
    publication existants. Un ensemble évite tout double compte (entité publiée ET en attente de
    dépublication). Un équipement présent compte au moins une entité.
    """
    equipments = len(present_entries_by_eq)
    entities = sum(max(1, len(entries)) for entries in present_entries_by_eq.values())
    scenarios = sum(1 for decision in (scenario_publications or {}).values() if _published(decision))
    return {
        "equipments_published": equipments,
        "entities_published": entities,
        "scenarios_published": scenarios,
    }
