"""fallback.py - Terminal broadband mapper slot for Jeedom -> Home Assistant.

Story 8.1 wired the slot. Story 9.4 activates the §11 degradation elegante logic:
  Info command → sensor ambiguous
  Action command (no Info) → button ambiguous
  Neither → None (no_projection_possible)
"""

from typing import Optional

from models.mapping import MappingResult, SensorCapabilities, SwitchCapabilities
from models.topology import JeedomEqLogic, TopologySnapshot


def _has_info_command(eq: JeedomEqLogic) -> bool:
    return any((cmd.type or "").lower() == "info" for cmd in eq.cmds)


def _has_action_command(eq: JeedomEqLogic) -> bool:
    return any((cmd.type or "").lower() == "action" for cmd in eq.cmds)


class FallbackMapper:
    """Terminal broadband mapper — §11 dégradation élégante (Story 9.4)."""

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        if _has_info_command(eq):
            cmd = next(c for c in eq.cmds if (c.type or "").lower() == "info")
            return MappingResult(
                ha_entity_type="sensor",
                confidence="ambiguous",
                reason_code="fallback_sensor_default",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands={cmd.generic_type or "fallback": cmd},
                capabilities=SensorCapabilities(has_state=True),
                reason_details={},
            )

        if _has_action_command(eq):
            cmd = next(c for c in eq.cmds if (c.type or "").lower() == "action")
            return MappingResult(
                ha_entity_type="button",
                confidence="ambiguous",
                reason_code="fallback_button_default",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands={cmd.generic_type or "fallback": cmd},
                capabilities=SwitchCapabilities(has_on_off=True),
                reason_details={"command_topic": f"jeedom2ha/{eq.id}/cmd"},
            )

        return None
