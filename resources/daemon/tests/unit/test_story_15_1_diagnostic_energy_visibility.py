"""Story 15.1 - Diagnostic endpoint exposes state_class/unit_of_measurement per matched command."""

from __future__ import annotations

import pytest

from transport.http_server import create_app
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd, EligibilityResult
)
from models.mapping import MappingResult, PublicationDecision, SensorCapabilities


@pytest.fixture
def app():
    return create_app(local_secret="test_secret")


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _mapped_sensor(eq_id, cmd, reason_details):
    return MappingResult(
        ha_entity_type="sensor",
        confidence="sure",
        reason_code="sensor_power",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Sensor {eq_id}",
        commands={cmd.generic_type or str(cmd.id): cmd},
        capabilities=SensorCapabilities(has_state=True),
        reason_details=reason_details,
    )


async def test_matched_command_exposes_state_class_and_unit_when_present(cli, app):
    cmd = JeedomCmd(id=6001, name="Puissance", generic_type="POWER", type="info", unit="W")
    snapshot = TopologySnapshot(
        timestamp="2026-07-05T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Local technique")},
        eq_logics={606: JeedomEqLogic(id=606, name="Sensor W", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = _mapped_sensor(
        606, cmd,
        {"device_class": "power", "unit_of_measurement": "W", "state_class": "measurement"},
    )
    app["topology"] = snapshot
    app["eligibility"] = {606: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {606: mapping_res}
    app["publications"] = {
        606: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping_res, active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 606)

    assert len(eq["matched_commands"]) == 1
    matched = eq["matched_commands"][0]
    assert matched["cmd_id"] == 6001
    assert matched["state_class"] == "measurement"
    assert matched["unit_of_measurement"] == "W"


async def test_matched_command_omits_state_class_when_absent(cli, app):
    """Cas kW connu : device_class=power sans state_class (limite _derive_state_class)."""
    cmd = JeedomCmd(id=6002, name="Puissance kW", generic_type="POWER", type="info", unit="kW")
    snapshot = TopologySnapshot(
        timestamp="2026-07-05T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Local technique")},
        eq_logics={607: JeedomEqLogic(id=607, name="Sensor kW", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = _mapped_sensor(
        607, cmd,
        {"device_class": "power", "unit_of_measurement": "kW"},
    )
    app["topology"] = snapshot
    app["eligibility"] = {607: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {607: mapping_res}
    app["publications"] = {
        607: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping_res, active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 607)

    assert len(eq["matched_commands"]) == 1
    matched = eq["matched_commands"][0]
    assert matched["cmd_id"] == 6002
    assert "state_class" not in matched
    assert "unit_of_measurement" not in matched


async def test_matched_command_energy_wh_gets_total_increasing(cli, app):
    cmd = JeedomCmd(id=6003, name="Consommation", generic_type="CONSUMPTION", type="info", unit="Wh")
    snapshot = TopologySnapshot(
        timestamp="2026-07-05T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Local technique")},
        eq_logics={608: JeedomEqLogic(id=608, name="Sensor Wh", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = _mapped_sensor(
        608, cmd,
        {"device_class": "energy", "unit_of_measurement": "Wh", "state_class": "total_increasing"},
    )
    app["topology"] = snapshot
    app["eligibility"] = {608: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {608: mapping_res}
    app["publications"] = {
        608: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping_res, active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 608)

    matched = eq["matched_commands"][0]
    assert matched["state_class"] == "total_increasing"
    assert matched["unit_of_measurement"] == "Wh"


async def test_matched_command_non_sensor_entity_unaffected(cli, app):
    """Non-régression : une entité light (reason_details sans state_class) reste inchangée."""
    from models.mapping import LightCapabilities

    cmd = JeedomCmd(id=6006, name="On", generic_type="LIGHT_ON", type="action")
    snapshot = TopologySnapshot(
        timestamp="2026-07-05T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={610: JeedomEqLogic(id=610, name="Lumiere", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_only",
        jeedom_eq_id=610,
        ha_unique_id="light_610",
        ha_name="Lumiere",
        commands={"LIGHT_ON": cmd},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {610: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {610: mapping_res}
    app["publications"] = {
        610: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping_res, active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 610)

    matched = eq["matched_commands"][0]
    assert matched["cmd_id"] == 6006
    assert matched["cmd_name"] == "On"
    assert matched["generic_type"] == "LIGHT_ON"
    assert "state_class" not in matched
    assert "unit_of_measurement" not in matched
