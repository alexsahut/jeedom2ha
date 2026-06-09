"""climate.py — Mapper Jeedom thermostat vers Home Assistant climate.

Détecte THERMOSTAT_SET_SETPOINT (action/slider) comme signal primaire.
THERMOSTAT_TEMPERATURE (info/numeric) est capturé si présent.
Portée : compatibilité minimale utile — pas d'équivalence HVAC exhaustive.
"""

from __future__ import annotations

from typing import Optional

from models.mapping import ClimateCapabilities, MappingResult
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot


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


class ClimateMapper:
    """Mappe un eqLogic thermostat Jeedom en HA climate via THERMOSTAT_SET_SETPOINT."""

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        setpoint_cmd: Optional[JeedomCmd] = None
        temp_cmd: Optional[JeedomCmd] = None

        for cmd in eq.cmds:
            if setpoint_cmd is None and _is_setpoint_action(cmd):
                setpoint_cmd = cmd
            elif temp_cmd is None and _is_temperature_info(cmd):
                temp_cmd = cmd

        if setpoint_cmd is None:
            return None

        eq_id = eq.id
        commands = {"THERMOSTAT_SET_SETPOINT": setpoint_cmd}
        if temp_cmd is not None:
            commands["THERMOSTAT_TEMPERATURE"] = temp_cmd

        reason_details: dict = {
            "temperature_command_topic": f"jeedom2ha/{eq_id}/temperature/set",
            "temperature_state_topic": f"jeedom2ha/{eq_id}/temperature/state",
        }
        if temp_cmd is not None:
            reason_details["current_temperature_topic"] = f"jeedom2ha/{eq_id}/current_temperature"

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
            ),
            reason_details=reason_details,
        )
