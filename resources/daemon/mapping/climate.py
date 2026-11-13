"""climate.py — Mapper Jeedom thermostat vers Home Assistant climate.

Détecte THERMOSTAT_SET_SETPOINT (action/slider) comme signal primaire.
THERMOSTAT_TEMPERATURE (info/numeric) est capturé si présent.
Portée : compatibilité minimale utile — pas d'équivalence HVAC exhaustive.

Story 24.15 — ``climate`` complet, comportement standard du plugin Jeedom « thermostat »
(et de tout équipement portant les mêmes types génériques) :
- consigne courante ``THERMOSTAT_SETPOINT``, température ``THERMOSTAT_TEMPERATURE``,
  mode ``THERMOSTAT_MODE``, chauffe ``THERMOSTAT_STATE`` (infos) ;
- D1 A : HA expose ``heat`` / ``off``. L'ordre d'arrêt est la commande
  ``THERMOSTAT_SET_MODE`` d'identifiant logique ``off`` (jamais reconnue par son nom) ;
  les autres ordres de mode deviennent des ``preset_modes`` (noms lus des commandes, aucun
  codé en dur). Sans info de mode : ni état de mode, ni arrêt, ni preset ;
- D3 : bornes ``minValue`` / ``maxValue`` de l'ordre de consigne, gardées seulement si les
  deux sont des nombres finis et ``min < max`` ;
- D4 A : le verrou (``THERMOSTAT_LOCK`` + ``THERMOSTAT_SET_LOCK`` / ``_UNLOCK``) est un
  ``switch`` « Verrouillage » séparé, de catégorie configuration, jamais un ``lock`` ;
- D5 : ``THERMOSTAT_TEMPERATURE_OUTDOOR`` et ``THERMOSTAT_STATE_NAME`` sont ignorées.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from models.mapping import ClimateCapabilities, MappingResult, SwitchCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot

_LOGGER = logging.getLogger(__name__)

# Story 24.15 — types génériques du cœur Jeedom lus par le climate.
THERMOSTAT_SET_SETPOINT = "THERMOSTAT_SET_SETPOINT"
THERMOSTAT_SETPOINT = "THERMOSTAT_SETPOINT"
THERMOSTAT_TEMPERATURE = "THERMOSTAT_TEMPERATURE"
THERMOSTAT_MODE = "THERMOSTAT_MODE"
THERMOSTAT_SET_MODE = "THERMOSTAT_SET_MODE"
THERMOSTAT_STATE = "THERMOSTAT_STATE"
THERMOSTAT_LOCK = "THERMOSTAT_LOCK"
THERMOSTAT_SET_LOCK = "THERMOSTAT_SET_LOCK"
THERMOSTAT_SET_UNLOCK = "THERMOSTAT_SET_UNLOCK"
# Rôle (clé de ``commands``) de l'ordre d'arrêt ; un ordre de mode nommé a le rôle
# ``THERMOSTAT_SET_MODE_<id>``.
THERMOSTAT_SET_MODE_OFF = "THERMOSTAT_SET_MODE_OFF"
# Identifiant logique de l'ordre d'arrêt du plugin « thermostat » (D1 : jamais un nom).
OFF_LOGICAL_ID = "off"
# Valeur réservée de HA pour « aucun preset » : jamais un nom de preset.
HA_PRESET_NONE = "none"

# Canaux d'état (topics ``jeedom2ha/<eq>/<canal>``) et d'ordre (``jeedom2ha/<eq>/<canal>/set``).
CHANNEL_SETPOINT = "setpoint"
CHANNEL_CURRENT_TEMPERATURE = "current_temperature"
CHANNEL_MODE = "mode"
CHANNEL_PRESET = "preset"
CHANNEL_ACTION = "action"
CLIMATE_STATE_CHANNELS = (
    CHANNEL_SETPOINT, CHANNEL_CURRENT_TEMPERATURE, CHANNEL_MODE, CHANNEL_PRESET, CHANNEL_ACTION,
)
COMMAND_CHANNEL_TEMPERATURE = "temperature"
COMMAND_CHANNEL_MODE = "mode"
COMMAND_CHANNEL_PRESET = "preset"
CLIMATE_COMMAND_CHANNELS = (COMMAND_CHANNEL_TEMPERATURE, COMMAND_CHANNEL_MODE, COMMAND_CHANNEL_PRESET)

# D3 — pas de la consigne (parité Homebridge).
SETPOINT_STEP = 0.5

# D4 A — nom de l'interrupteur de verrouillage (entité secondaire de l'appareil).
LOCK_SWITCH_NAME = "Verrouillage"

_UNITS = {"°C": "C", "°F": "F"}


def climate_state_topic(eq_id: int, channel: str) -> str:
    """Topic d'état d'un canal du climate (même forme que ``sync.readback.channel_topic``)."""
    return f"jeedom2ha/{eq_id}/{channel}"


def climate_command_topic(eq_id: int, channel: str) -> str:
    """Topic d'ordre d'un canal du climate."""
    return f"jeedom2ha/{eq_id}/{channel}/set"


def _is_setpoint_action(cmd: JeedomCmd) -> bool:
    if cmd.generic_type != "THERMOSTAT_SET_SETPOINT":
        return False
    if (cmd.type or "").lower() != "action":
        return False

    # Terrain: certains thermostats Jeedom exposent THERMOSTAT_SET_SETPOINT avec
    # sub_type vide (au lieu de "slider"). On accepte explicitement ce cas.
    sub_type = (cmd.sub_type or "").strip().lower()
    return sub_type in {"", "slider"}


def _is_temperature_info(cmd: JeedomCmd) -> bool:
    if cmd.generic_type != "THERMOSTAT_TEMPERATURE":
        return False
    return (cmd.type or "").lower() == "info"


def _is_info(cmd: JeedomCmd, generic_type: str) -> bool:
    return cmd.generic_type == generic_type and (cmd.type or "").lower() == "info"


def _is_order(cmd: JeedomCmd, generic_type: str) -> bool:
    """Ordre sans valeur (sous-type ``other``, ou vide comme le relevé terrain de 10.2)."""
    return (
        cmd.generic_type == generic_type
        and (cmd.type or "").lower() == "action"
        and (cmd.sub_type or "").strip().lower() in {"", "other"}
    )


def _setpoint_bounds(setpoint_cmd: JeedomCmd) -> Optional[tuple]:
    """D3 — ``(min, max)`` de l'ordre de consigne, seulement si les deux sont valides."""
    low, high = setpoint_cmd.min_value, setpoint_cmd.max_value
    if low is None or high is None or not low < high:
        return None
    return low, high


def _temperature_unit(*cmds: Optional[JeedomCmd]) -> Optional[str]:
    """``C`` / ``F`` d'après l'unité de la première commande qui en porte une ; sinon None."""
    for cmd in cmds:
        unit = (getattr(cmd, "unit", None) or "").strip()
        if unit:
            return _UNITS.get(unit)
    return None


def _split_mode_orders(eq: JeedomEqLogic, orders: List[JeedomCmd]):
    """D1 — ``(ordre d'arrêt | None, {nom de preset: ordre})``.

    L'arrêt est l'unique ordre d'identifiant logique ``off`` (plusieurs : aucun arrêt).
    Un preset porte le nom de sa commande, tel quel ; un nom vide, ``none`` (réservé par HA),
    égal au nom de l'arrêt ou porté par plusieurs commandes est écarté (WARNING), jamais
    deviné.
    """
    offs = [c for c in orders if c.logical_id == OFF_LOGICAL_ID]
    off_cmd = offs[0] if len(offs) == 1 else None
    if len(offs) > 1:
        _LOGGER.warning(
            "[MAPPING] eq_id=%d: thermostat, plusieurs ordres d'arrêt %s → aucun arrêt",
            eq.id, [c.id for c in offs],
        )
    names: Dict[str, List[JeedomCmd]] = {}
    for cmd in orders:
        if cmd.logical_id == OFF_LOGICAL_ID:
            continue
        names.setdefault(cmd.name or "", []).append(cmd)
    presets: Dict[str, JeedomCmd] = {}
    for name, cmds in names.items():
        refused = (
            not name.strip()
            or name == HA_PRESET_NONE
            or (off_cmd is not None and name == off_cmd.name)
            or len(cmds) > 1
        )
        if refused:
            _LOGGER.warning(
                "[MAPPING] eq_id=%d: thermostat, ordre(s) de mode %s écarté(s) des presets "
                "(nom vide, réservé, égal à l'arrêt ou en double)",
                eq.id, [c.id for c in cmds],
            )
            continue
        presets[name] = cmds[0]
    return off_cmd, presets


def _lock_switch(eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
    """D4 A — interrupteur « Verrouillage » : une info de verrou et ses deux ordres, uniques."""
    infos = [c for c in eq.cmds if _is_info(c, THERMOSTAT_LOCK)]
    locks = [c for c in eq.cmds if _is_order(c, THERMOSTAT_SET_LOCK)]
    unlocks = [c for c in eq.cmds if _is_order(c, THERMOSTAT_SET_UNLOCK)]
    if not (infos or locks or unlocks):
        return None
    if len(infos) != 1 or len(locks) != 1 or len(unlocks) != 1:
        _LOGGER.info(
            "[MAPPING] eq_id=%d: verrou du thermostat incomplet ou ambigu (info=%s verrouiller=%s "
            "déverrouiller=%s) → pas d'interrupteur de verrouillage",
            eq.id, [c.id for c in infos], [c.id for c in locks], [c.id for c in unlocks],
        )
        return None
    info = infos[0]
    node_id = f"jeedom2ha_{eq.id}_{info.id}"
    return MappingResult(
        ha_entity_type="switch",
        confidence="sure",
        reason_code="climate_thermostat_lock",
        jeedom_eq_id=eq.id,
        ha_unique_id=f"jeedom2ha_eq_{eq.id}_cmd_{info.id}",
        ha_name=LOCK_SWITCH_NAME,
        suggested_area=snapshot.get_suggested_area(eq.id),
        commands={
            THERMOSTAT_LOCK: info,
            THERMOSTAT_SET_LOCK: locks[0],
            THERMOSTAT_SET_UNLOCK: unlocks[0],
        },
        capabilities=SwitchCapabilities(has_on_off=True, has_state=True, on_off_confidence="sure"),
        reason_details={
            "cmd_id": info.id,
            "object_id": node_id,
            "node_id": node_id,
            "state_topic": f"jeedom2ha/{eq.id}/{info.id}/state",
            "command_topic": f"jeedom2ha/{eq.id}/{info.id}/set",
            "entity_category": "config",
            "thermostat_lock": True,
        },
    )


class ClimateMapper:
    """Mappe un eqLogic thermostat Jeedom en HA climate via THERMOSTAT_SET_SETPOINT."""

    def map_all(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> List[MappingResult]:
        """Story 24.15 — le climate, puis l'interrupteur de verrouillage s'il existe (D4 A)."""
        climate = self.map(eq, snapshot)
        if climate is None:
            return []
        lock_switch = _lock_switch(eq, snapshot)
        return [climate] if lock_switch is None else [climate, lock_switch]

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        setpoint_cmd: Optional[JeedomCmd] = None
        temp_cmd: Optional[JeedomCmd] = None
        setpoint_info: Optional[JeedomCmd] = None
        mode_info: Optional[JeedomCmd] = None
        state_info: Optional[JeedomCmd] = None
        mode_orders: List[JeedomCmd] = []

        for cmd in eq.cmds:
            if setpoint_cmd is None and _is_setpoint_action(cmd):
                setpoint_cmd = cmd
            elif temp_cmd is None and _is_temperature_info(cmd):
                temp_cmd = cmd
            elif setpoint_info is None and _is_info(cmd, THERMOSTAT_SETPOINT):
                setpoint_info = cmd
            elif mode_info is None and _is_info(cmd, THERMOSTAT_MODE):
                mode_info = cmd
            elif state_info is None and _is_info(cmd, THERMOSTAT_STATE):
                state_info = cmd
            elif _is_order(cmd, THERMOSTAT_SET_MODE):
                mode_orders.append(cmd)

        if setpoint_cmd is None:
            return None

        eq_id = eq.id
        commands: Dict[str, JeedomCmd] = {THERMOSTAT_SET_SETPOINT: setpoint_cmd}
        if temp_cmd is not None:
            commands[THERMOSTAT_TEMPERATURE] = temp_cmd
        if setpoint_info is not None:
            commands[THERMOSTAT_SETPOINT] = setpoint_info
        if state_info is not None:
            commands[THERMOSTAT_STATE] = state_info

        off_cmd, presets = (None, {})
        if mode_info is not None:
            commands[THERMOSTAT_MODE] = mode_info
            off_cmd, presets = _split_mode_orders(eq, mode_orders)
            if off_cmd is not None:
                commands[THERMOSTAT_SET_MODE_OFF] = off_cmd
            for preset_cmd in presets.values():
                commands[f"{THERMOSTAT_SET_MODE}_{preset_cmd.id}"] = preset_cmd

        reason_details: dict = {
            "temperature_command_topic": climate_command_topic(eq_id, COMMAND_CHANNEL_TEMPERATURE),
        }
        if setpoint_info is not None:
            reason_details["temperature_state_topic"] = climate_state_topic(eq_id, CHANNEL_SETPOINT)
        if temp_cmd is not None:
            reason_details["current_temperature_topic"] = climate_state_topic(
                eq_id, CHANNEL_CURRENT_TEMPERATURE
            )
        if off_cmd is not None:
            reason_details["off_mode_name"] = off_cmd.name
        if presets:
            reason_details["preset_modes"] = list(presets)
            reason_details["preset_commands"] = {name: cmd.id for name, cmd in presets.items()}
        bounds = _setpoint_bounds(setpoint_cmd)
        if bounds is not None:
            reason_details["min_temp"], reason_details["max_temp"] = bounds
        unit = _temperature_unit(setpoint_info, temp_cmd, setpoint_cmd)
        if unit is not None:
            reason_details["temperature_unit"] = unit

        return MappingResult(
            ha_entity_type="climate",
            confidence="sure",
            reason_code="climate_thermostat_setpoint",
            jeedom_eq_id=eq_id,
            ha_unique_id=f"jeedom2ha_eq_{eq_id}",
            ha_name=eq.name,
            suggested_area=snapshot.get_suggested_area(eq_id),
            commands=commands,
            capabilities=ClimateCapabilities(
                has_setpoint=True,
                has_current_temperature=(temp_cmd is not None),
                has_setpoint_state=(setpoint_info is not None),
                has_mode=(mode_info is not None),
                has_off=(off_cmd is not None),
                has_presets=bool(presets),
                has_action=(state_info is not None),
            ),
            reason_details=reason_details,
        )
