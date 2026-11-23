"""alarm_control_panel.py — Mapper Jeedom alarme vers HA alarm_control_panel.

Signal primaire : ALARM_STATE (info/binary) ou ALARM_ENABLE_STATE (info/binary).
Commandes armer : ALARM_ENABLE (virtuel générique) ou ALARM_ARMED (plugin alarme natif).
Commandes désarmer : ALARM_DISABLE (virtuel générique) ou ALARM_RELEASED (plugin alarme natif).

FR49 (CC-64) — état et armement par mode :
- infos lues pour l'état (``sync.readback.alarm_state``) : ALARM_STATE (déclenchée),
  ALARM_ENABLE_STATE (active), ALARM_MODE (libellé du mode) et, pour le plugin ``alarm``,
  l'info de logicalId ``immediatState`` (délai d'entrée en cours, sans generic type) ;
- modes d'armement : les clés ``SetModePresent`` / ``SetModeAbsent`` / ``SetModeNuit`` posées
  par Homebridge sur l'eqLogic (« id|libellé »). Une commande de mode n'est retenue que si son
  id est une commande de l'équipement, de type action et de generic type ALARM_SET_MODE ;
- sans mode retenu, l'armement reste ALARM_ARMED / ALARM_ENABLE (``armed_away``).
Aucun identifiant ni libellé de la maison n'est écrit ici : tout vient de la topologie.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping, Optional, Tuple

from models.mapping import AlarmCapabilities, MappingResult
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot

_LOGGER = logging.getLogger(__name__)

ALARM_STATE = "ALARM_STATE"
ALARM_ENABLE_STATE = "ALARM_ENABLE_STATE"
ALARM_MODE = "ALARM_MODE"
ALARM_SET_MODE = "ALARM_SET_MODE"
# Clé de rôle (pas un generic type) de l'info « Immédiat » du plugin alarm : Jeedom ne lui
# donne aucun generic type, et on n'en écrit jamais côté Jeedom (il alimente Homebridge).
ALARM_IMMEDIATE_STATE = "ALARM_IMMEDIATE_STATE"
ALARM_PLUGIN = "alarm"
IMMEDIATE_LOGICAL_ID = "immediatState"

HA_ARMED_HOME = "armed_home"
HA_ARMED_AWAY = "armed_away"
HA_ARMED_NIGHT = "armed_night"

# (clé de configuration Homebridge, état HA, clé de rôle dans ``commands``, feature HA, payload HA)
MODE_SLOTS: Tuple[Tuple[str, str, str, str, str], ...] = (
    ("SetModePresent", HA_ARMED_HOME, "ALARM_SET_MODE_HOME", "arm_home", "ARM_HOME"),
    ("SetModeAbsent", HA_ARMED_AWAY, "ALARM_SET_MODE_AWAY", "arm_away", "ARM_AWAY"),
    ("SetModeNuit", HA_ARMED_NIGHT, "ALARM_SET_MODE_NIGHT", "arm_night", "ARM_NIGHT"),
)
# Payload HA d'armement -> état HA visé.
ARM_PAYLOADS: Dict[str, str] = {slot[4]: slot[1] for slot in MODE_SLOTS}
PAYLOAD_DISARM = "DISARM"

_STATE_GENERIC_TYPES = {ALARM_STATE, ALARM_ENABLE_STATE}
# ALARM_ENABLE = plugin virtuel générique ; ALARM_ARMED = plugin alarme natif Jeedom (Homebridge parity)
_ARM_GENERIC_TYPES = {"ALARM_ENABLE", "ALARM_ARMED"}
# ALARM_DISABLE = plugin virtuel générique ; ALARM_RELEASED = plugin alarme natif Jeedom
_DISARM_GENERIC_TYPES = {"ALARM_DISABLE", "ALARM_RELEASED"}

# Infos qui alimentent l'état publié, dans l'ordre de lecture (sync.readback).
ALARM_READBACK_KEYS: Tuple[str, ...] = (ALARM_ENABLE_STATE, ALARM_STATE, ALARM_IMMEDIATE_STATE, ALARM_MODE)


def _is_binary_info_cmd(cmd: JeedomCmd) -> bool:
    if (cmd.type or "").lower() != "info":
        return False
    sub_type = (cmd.sub_type or "").lower()
    if "numeric" in sub_type:
        return False
    return "binary" in sub_type


def _is_info_cmd(cmd: Any) -> bool:
    return str(getattr(cmd, "type", "") or "").lower() == "info"


def _is_action_cmd(cmd: Any) -> bool:
    return str(getattr(cmd, "type", "") or "").lower() == "action"


def _cmd_id(cmd: Any) -> Optional[int]:
    try:
        return int(getattr(cmd, "id", None))
    except (TypeError, ValueError):
        return None


def parse_mode_config_value(raw: Any) -> Optional[Tuple[int, str]]:
    """« id|libellé » -> (id, libellé) ; toute autre forme -> None (jamais deviné)."""
    if not isinstance(raw, str):
        return None
    head, sep, label = raw.partition("|")
    if not sep or not label.strip():
        return None
    head = head.strip()
    if not head.isdigit():
        return None
    cmd_id = int(head)
    if cmd_id <= 0:
        return None
    return cmd_id, label


def _comparable_label(label: str) -> str:
    """Même normalisation que ``sync.readback.normalize_alarm_mode_label`` (casse, espaces)."""
    return " ".join(label.split()).casefold()


def _warn_duplicate_mode_labels(eq_id: Any, config: Mapping[str, Any], mode_labels: Mapping[str, str]) -> None:
    """Revue de 12.4 — deux clés Homebridge au même libellé de mode : WARNING, comportement inchangé.

    L'état se lit par libellé : le premier mode dans l'ordre Présent, Absent, Nuit l'emporte
    (``sync.readback.alarm_state``). Les libellés ne sont pas écrits dans le journal.
    """
    keys_by_label: Dict[str, List[str]] = {}
    for key, ha_state, _role, _feature, _payload in MODE_SLOTS:
        label = mode_labels.get(ha_state)
        if label is None:
            continue
        keys_by_label.setdefault(_comparable_label(label), []).append(key)
    for keys in keys_by_label.values():
        if len(keys) > 1:
            _LOGGER.warning(
                "[MAPPING] eq_id=%s : alarme, les clés Homebridge %s portent le même libellé de mode ; "
                "l'état affiché sera celui de %s (premier dans l'ordre Présent, Absent, Nuit)",
                eq_id, ", ".join(keys), keys[0],
            )


def is_mode_command(cmd: Any) -> bool:
    """Une commande de mode valable : action de generic type ALARM_SET_MODE avec un id."""
    return (
        cmd is not None
        and _is_action_cmd(cmd)
        and getattr(cmd, "generic_type", None) == ALARM_SET_MODE
        and _cmd_id(cmd) is not None
    )


def alarm_arm_targets(commands: Mapping[str, Any]) -> Dict[str, Any]:
    """État HA d'armement -> commande Jeedom à lancer (source unique discovery / commandes).

    Les commandes de mode retenues par le mapper l'emportent ; sans aucune, l'armement
    générique (ALARM_ENABLE / ALARM_ARMED) arme en ``armed_away`` (comportement d'avant FR49).
    """
    commands = commands or {}
    targets: Dict[str, Any] = {}
    for _key, ha_state, role, _feature, _payload in MODE_SLOTS:
        cmd = commands.get(role)
        if is_mode_command(cmd):
            targets[ha_state] = cmd
    if targets:
        return targets
    for generic_type in ("ALARM_ENABLE", "ALARM_ARMED"):
        cmd = commands.get(generic_type)
        if cmd is not None and _is_action_cmd(cmd) and getattr(cmd, "generic_type", None) == generic_type:
            return {HA_ARMED_AWAY: cmd}
    return {}


def alarm_disarm_command(commands: Mapping[str, Any]) -> Optional[Any]:
    """ALARM_RELEASED (plugin alarm) ou ALARM_DISABLE (virtuel), action de ce generic type."""
    commands = commands or {}
    for generic_type in ("ALARM_RELEASED", "ALARM_DISABLE"):
        cmd = commands.get(generic_type)
        if cmd is not None and _is_action_cmd(cmd) and getattr(cmd, "generic_type", None) == generic_type:
            return cmd
    return None


def alarm_enable_command(commands: Mapping[str, Any]) -> Optional[Any]:
    """Story 12.5 — ALARM_ARMED (plugin alarm) ou ALARM_ENABLE (virtuel), action de ce generic type.

    Commande d'activation, présente dans ``commands`` même quand des modes sont retenus : elle
    arme l'alarme dans son mode courant (armement dans le mode déjà courant, story 12.5).
    """
    commands = commands or {}
    for generic_type in ("ALARM_ARMED", "ALARM_ENABLE"):
        cmd = commands.get(generic_type)
        if cmd is not None and _is_action_cmd(cmd) and getattr(cmd, "generic_type", None) == generic_type:
            return cmd
    return None


def alarm_supported_features(commands: Mapping[str, Any]) -> List[str]:
    """``supported_features`` HA : seulement les armements réellement disponibles."""
    targets = alarm_arm_targets(commands)
    return [feature for _key, ha_state, _role, feature, _payload in MODE_SLOTS if ha_state in targets]


def alarm_mode_labels(mapping: Any) -> Dict[str, str]:
    """État HA -> libellé de mode (clés Homebridge), lu dans ``reason_details`` du mapping."""
    labels = (getattr(mapping, "reason_details", None) or {}).get("alarm_mode_labels") or {}
    return {k: v for k, v in labels.items() if isinstance(k, str) and isinstance(v, str)}


class AlarmControlPanelMapper:
    """Mappe un eqLogic alarme Jeedom en HA alarm_control_panel."""

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        state_cmd: Optional[JeedomCmd] = None
        arm_cmd: Optional[JeedomCmd] = None
        disarm_cmd: Optional[JeedomCmd] = None
        info_by_key: Dict[str, JeedomCmd] = {}

        for cmd in eq.cmds:
            gt = cmd.generic_type
            if (
                ALARM_IMMEDIATE_STATE not in info_by_key
                and (eq.eq_type_name or "") == ALARM_PLUGIN
                and getattr(cmd, "logical_id", None) == IMMEDIATE_LOGICAL_ID
                and _is_binary_info_cmd(cmd)
            ):
                info_by_key[ALARM_IMMEDIATE_STATE] = cmd
            if not gt:
                continue
            if gt in _STATE_GENERIC_TYPES and _is_binary_info_cmd(cmd):
                if state_cmd is None:
                    state_cmd = cmd
                info_by_key.setdefault(gt, cmd)
            elif gt == ALARM_MODE and _is_info_cmd(cmd):
                info_by_key.setdefault(ALARM_MODE, cmd)
            elif arm_cmd is None and gt in _ARM_GENERIC_TYPES and _is_action_cmd(cmd):
                arm_cmd = cmd
            elif disarm_cmd is None and gt in _DISARM_GENERIC_TYPES and _is_action_cmd(cmd):
                disarm_cmd = cmd

        if state_cmd is None:
            return None

        eq_id = eq.id
        commands: Dict[str, JeedomCmd] = {state_cmd.generic_type: state_cmd}
        for key in ALARM_READBACK_KEYS:
            if key in info_by_key:
                commands.setdefault(key, info_by_key[key])
        if arm_cmd is not None:
            commands[arm_cmd.generic_type] = arm_cmd
        if disarm_cmd is not None:
            commands[disarm_cmd.generic_type] = disarm_cmd

        # FR49 — modes d'armement désignés par les clés Homebridge de l'eqLogic.
        cmds_by_id = {c.id: c for c in eq.cmds}
        mode_labels: Dict[str, str] = {}
        config = getattr(eq, "alarm_mode_config", None) or {}
        for key, ha_state, role, _feature, _payload in MODE_SLOTS:
            parsed = parse_mode_config_value(config.get(key))
            if parsed is None:
                continue
            mode_cmd_id, label = parsed
            mode_labels[ha_state] = label
            mode_cmd = cmds_by_id.get(mode_cmd_id)
            if is_mode_command(mode_cmd):
                commands[role] = mode_cmd

        has_command = bool(alarm_arm_targets(commands)) or alarm_disarm_command(commands) is not None
        reason_details: Dict[str, Any] = {
            "state_topic": f"jeedom2ha/{eq_id}/alarm/state",
            "command_topic": f"jeedom2ha/{eq_id}/alarm/set",
            "supported_features": alarm_supported_features(commands),
        }
        if mode_labels:
            reason_details["alarm_mode_labels"] = mode_labels
            _warn_duplicate_mode_labels(eq_id, config, mode_labels)

        return MappingResult(
            ha_entity_type="alarm_control_panel",
            confidence="sure",
            reason_code="alarm_control_panel_state_commands",
            jeedom_eq_id=eq_id,
            ha_unique_id=f"jeedom2ha_eq_{eq_id}",
            ha_name=eq.name,
            suggested_area=snapshot.get_suggested_area(eq_id),
            commands=commands,
            capabilities=AlarmCapabilities(has_state=True, has_command=has_command),
            reason_details=reason_details,
        )
