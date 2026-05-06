"""button.py — Mapper Jeedom Action ponctuelle vers Home Assistant button."""

from __future__ import annotations

from typing import Optional

from models.mapping import MappingResult, SwitchCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot


def _is_action_other_command(cmd: JeedomCmd) -> bool:
    if (cmd.type or "").lower() != "action":
        return False
    if cmd.generic_type is None:
        return False
    return (cmd.sub_type or "").lower() == "other"


class ButtonMapper:
    """Mappe un eqLogic Jeedom en HA button via commande Action ponctuelle (sub_type "other")."""

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        for cmd in eq.cmds:
            if not _is_action_other_command(cmd):
                continue

            generic_type = cmd.generic_type
            return MappingResult(
                ha_entity_type="button",
                confidence="sure",
                reason_code=f"button_{generic_type.lower()}",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands={generic_type: cmd},
                capabilities=SwitchCapabilities(has_on_off=True),
                reason_details={"command_topic": f"jeedom2ha/{eq.id}/cmd"},
            )

        return None
