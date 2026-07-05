"""Story 15.3 - Diagnostic endpoint exposes fan_switch_parity for FAN-family switches."""

from __future__ import annotations

import pytest

from transport.http_server import create_app
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd, EligibilityResult
)
from models.mapping import MappingResult, PublicationDecision, SwitchCapabilities, SensorCapabilities


@pytest.fixture
def app():
    return create_app(local_secret="test_secret")


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _mapped_switch(eq_id, cmds, reason_code):
    return MappingResult(
        ha_entity_type="switch",
        confidence="sure",
        reason_code=reason_code,
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Switch {eq_id}",
        commands={cmd.generic_type or str(cmd.id): cmd for cmd in cmds},
        capabilities=SwitchCapabilities(has_on_off=True, has_state=True),
        reason_details={},
    )


def _mapped_sensor(eq_id, cmd):
    return MappingResult(
        ha_entity_type="sensor",
        confidence="sure",
        reason_code="sensor_power",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Sensor {eq_id}",
        commands={cmd.generic_type or str(cmd.id): cmd},
        capabilities=SensorCapabilities(has_state=True),
        reason_details={},
    )


async def test_fan_family_switch_gets_parity_badge_when_published(cli, app):
    cmd = JeedomCmd(id=8001, name="Filtration", generic_type="FAN_STATE", type="info")
    snapshot = TopologySnapshot(
        timestamp="2026-07-05T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Piscine")},
        eq_logics={801: JeedomEqLogic(id=801, name="Pompe filtration", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = _mapped_switch(801, [cmd], "switch_fan_on_off_state")
    app["topology"] = snapshot
    app["eligibility"] = {801: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {801: mapping_res}
    app["publications"] = {
        801: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping_res, active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 801)

    assert eq["fan_switch_parity"] is True
    # AC#3 trap: reason_code is overwritten by publication confidence, not the family marker.
    assert eq["reason_code"] == "sure"


async def test_standard_family_switch_has_no_parity_badge(cli, app):
    cmd = JeedomCmd(id=8002, name="Prise", generic_type="ENERGY_STATE", type="info")
    snapshot = TopologySnapshot(
        timestamp="2026-07-05T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={802: JeedomEqLogic(id=802, name="Prise standard", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = _mapped_switch(802, [cmd], "switch_switch_on_off_state")
    app["topology"] = snapshot
    app["eligibility"] = {802: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {802: mapping_res}
    app["publications"] = {
        802: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping_res, active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 802)

    assert "fan_switch_parity" not in eq


async def test_non_switch_equipment_has_no_parity_badge(cli, app):
    cmd = JeedomCmd(id=8003, name="Temperature", generic_type="TEMP", type="info")
    snapshot = TopologySnapshot(
        timestamp="2026-07-05T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={803: JeedomEqLogic(id=803, name="Sensor Temp", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = _mapped_sensor(803, cmd)
    app["topology"] = snapshot
    app["eligibility"] = {803: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {803: mapping_res}
    app["publications"] = {
        803: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping_res, active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 803)

    assert "fan_switch_parity" not in eq


async def test_fan_family_switch_gets_parity_badge_even_when_not_published(cli, app):
    """The new field must survive independently of the reason_code overwrite trap (AC#3):
    it must be correct whether or not the equipment ends up active_or_alive."""
    cmd = JeedomCmd(id=8004, name="Filtration", generic_type="FAN_STATE", type="info")
    snapshot = TopologySnapshot(
        timestamp="2026-07-05T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Piscine")},
        eq_logics={804: JeedomEqLogic(id=804, name="Pompe filtration inactive", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = _mapped_switch(804, [cmd], "switch_fan_on_off_state")
    app["topology"] = snapshot
    app["eligibility"] = {804: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {804: mapping_res}
    app["publications"] = {
        804: PublicationDecision(
            should_publish=False, reason="ambiguous", mapping_result=mapping_res, active_or_alive=False,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 804)

    # reason_code is reassigned in this branch too (canonical decision cause) -
    # fan_switch_parity must stay correct regardless, since it is captured independently.
    assert eq["fan_switch_parity"] is True
    assert eq["reason_code"] != "switch_fan_on_off_state"


async def test_fan_parity_non_regression_alongside_energy_and_streaming(cli, app):
    """Stories 15.1/15.2 fields keep working on the same payload as the new 15.3 field."""
    fan_cmd = JeedomCmd(id=8005, name="Filtration", generic_type="FAN_STATE", type="info")
    power_cmd = JeedomCmd(id=8006, name="Puissance", generic_type="POWER", type="info", unit="W")
    snapshot = TopologySnapshot(
        timestamp="2026-07-05T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Local technique")},
        eq_logics={
            805: JeedomEqLogic(id=805, name="Pompe filtration", object_id=1, is_enable=True, cmds=[fan_cmd]),
            806: JeedomEqLogic(id=806, name="Sensor W", object_id=1, is_enable=True, cmds=[power_cmd]),
        },
    )
    fan_mapping = _mapped_switch(805, [fan_cmd], "switch_fan_on_off_state")
    power_mapping = MappingResult(
        ha_entity_type="sensor",
        confidence="sure",
        reason_code="sensor_power",
        jeedom_eq_id=806,
        ha_unique_id="jeedom2ha_eq_806",
        ha_name="Sensor W",
        commands={"POWER": power_cmd},
        capabilities=SensorCapabilities(has_state=True),
        reason_details={"device_class": "power", "unit_of_measurement": "W", "state_class": "measurement"},
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        805: EligibilityResult(is_eligible=True, reason_code="eligible"),
        806: EligibilityResult(is_eligible=True, reason_code="eligible"),
    }
    app["mappings"] = {805: fan_mapping, 806: power_mapping}
    app["publications"] = {
        805: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=fan_mapping, active_or_alive=True,
        ),
        806: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=power_mapping, active_or_alive=True,
        ),
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    fan_eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 805)
    power_eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 806)

    assert fan_eq["fan_switch_parity"] is True
    assert "fan_switch_parity" not in power_eq
    matched = power_eq["matched_commands"][0]
    assert matched["state_class"] == "measurement"
    assert matched["unit_of_measurement"] == "W"
