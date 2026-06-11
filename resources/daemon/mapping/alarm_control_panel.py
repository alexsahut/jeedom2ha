"""alarm_control_panel.py — Mapper Jeedom alarme vers HA alarm_control_panel.

Signal primaire : ALARM_STATE (info/binary) ou ALARM_ENABLE_STATE (info/binary).
Commandes armer : ALARM_ENABLE (virtuel générique) ou ALARM_ARMED (plugin alarme natif).
Commandes désarmer : ALARM_DISABLE (virtuel générique) ou ALARM_RELEASED (plugin alarme natif).
Portée : compatibilité minimale utile — état armé/désarmé + commandes armer/désarmer.
"""

from __future__ import annotations
from typing import Optional
from models.mapping import AlarmCapabilities, MappingResult
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot

_STATE_GENERIC_TYPES = {"ALARM_STATE", "ALARM_ENABLE_STATE"}
# ALARM_ENABLE = plugin virtuel générique ; ALARM_ARMED = plugin alarme natif Jeedom (Homebridge parity)
_ARM_GENERIC_TYPES = {"ALARM_ENABLE", "ALARM_ARMED"}
# ALARM_DISABLE = plugin virtuel générique ; ALARM_RELEASED = plugin alarme natif Jeedom
_DISARM_GENERIC_TYPES = {"ALARM_DISABLE", "ALARM_RELEASED"}


def _is_binary_info_cmd(cmd: JeedomCmd) -> bool:
    if (cmd.type or "").lower() != "info":
        return False
    sub_type = (cmd.sub_type or "").lower()
    if "numeric" in sub_type:
        return False
    return "binary" in sub_type


def _is_action_cmd(cmd: JeedomCmd) -> bool:
    return (cmd.type or "").lower() == "action"


class AlarmControlPanelMapper:
    """Mappe un eqLogic alarme Jeedom en HA alarm_control_panel."""

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        state_cmd: Optional[JeedomCmd] = None
        arm_cmd: Optional[JeedomCmd] = None
        disarm_cmd: Optional[JeedomCmd] = None

        for cmd in eq.cmds:
            gt = cmd.generic_type
            if not gt:
                continue
            if state_cmd is None and gt in _STATE_GENERIC_TYPES and _is_binary_info_cmd(cmd):
                state_cmd = cmd
            elif arm_cmd is None and gt in _ARM_GENERIC_TYPES and _is_action_cmd(cmd):
                arm_cmd = cmd
            elif disarm_cmd is None and gt in _DISARM_GENERIC_TYPES and _is_action_cmd(cmd):
                disarm_cmd = cmd

        if state_cmd is None:
            return None

        has_command = arm_cmd is not None or disarm_cmd is not None
        eq_id = eq.id
        commands = {state_cmd.generic_type: state_cmd}
        if arm_cmd is not None:
            commands[arm_cmd.generic_type] = arm_cmd
        if disarm_cmd is not None:
            commands[disarm_cmd.generic_type] = disarm_cmd

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
            reason_details={
                "state_topic": f"jeedom2ha/{eq_id}/alarm/state",
                "command_topic": f"jeedom2ha/{eq_id}/alarm/set",
            },
        )
