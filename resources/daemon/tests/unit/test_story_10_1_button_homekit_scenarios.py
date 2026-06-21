"""Story 10.1 - Verification de couverture button pour 5 scenarios HomeKit cibles."""

from __future__ import annotations

import pytest

from mapping.registry import MapperRegistry
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from validation.ha_component_registry import PRODUCT_SCOPE

HOMEKIT_SCENARIOS = [
    "Tout eteindre",
    "Tout éteindre",
    "ambiance cinema",
    "ambiance coucher",
    "Ambiance lumineuse",
    "Lumieres terrasse",
    "Lumières terrasse",
]


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-06-09T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Maison")},
        eq_logics={eq.id: eq},
    )


def _scenario_eq(eq_id: int, name: str) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=eq_id,
        name=name,
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            JeedomCmd(
                id=(eq_id * 10) + 1,
                name="scenario_action",
                generic_type="GENERIC_ACTION",
                type="action",
                sub_type="other",
            )
        ],
    )


@pytest.mark.parametrize("idx,scenario_name", list(enumerate(HOMEKIT_SCENARIOS, start=1)))
def test_story_10_1_all_homekit_scenarios_land_on_button(idx: int, scenario_name: str):
    registry = MapperRegistry()
    eq = _scenario_eq(10100 + idx, scenario_name)

    mapping = registry.map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.ha_entity_type == "button"
    assert mapping.confidence == "sure"
    assert mapping.reason_code == "button_generic_action"
    assert mapping.reason_details == {"command_topic": f"jeedom2ha/{eq.id}/cmd"}


def test_story_10_1_product_scope_remains_button_only_for_this_wave():
    assert PRODUCT_SCOPE == ["light", "cover", "switch", "sensor", "binary_sensor", "button"]
    assert "climate" not in PRODUCT_SCOPE
    assert "alarm_control_panel" not in PRODUCT_SCOPE
