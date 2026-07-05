"""Story 15.2 - Diagnostic endpoint exposes streaming status per matched command + global summary."""

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


class _FakeStateSynchronizer:
    """Stub mirroring StateSynchronizer's public read-only surface (sync/state.py).

    ``list_state_targets()`` returns dicts with eq_id/cmd_id/ha_type/state_topic
    (real contract, sync/state.py ~L137-183) — ``targets`` here is the list of
    (eq_id, cmd_id) tuples to expose as streamed.
    """

    def __init__(self, targets, is_active=True):
        self._targets = targets
        self.is_active = is_active

    def list_state_targets(self):
        return [
            {"eq_id": eq_id, "cmd_id": cmd_id, "ha_type": "sensor", "state_topic": f"jeedom2ha/{eq_id}/state"}
            for eq_id, cmd_id in self._targets
        ]


def _mapped_sensor(eq_id, cmd, reason_details=None):
    return MappingResult(
        ha_entity_type="sensor",
        confidence="sure",
        reason_code="sensor_power",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Sensor {eq_id}",
        commands={cmd.generic_type or str(cmd.id): cmd},
        capabilities=SensorCapabilities(has_state=True),
        reason_details=reason_details or {},
    )


async def test_matched_command_gets_streaming_badge_when_in_state_targets(cli, app):
    cmd = JeedomCmd(id=7001, name="Temperature", generic_type="TEMP", type="info")
    snapshot = TopologySnapshot(
        timestamp="2026-07-05T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={706: JeedomEqLogic(id=706, name="Sensor Temp", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = _mapped_sensor(706, cmd)
    app["topology"] = snapshot
    app["eligibility"] = {706: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {706: mapping_res}
    app["publications"] = {
        706: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping_res, active_or_alive=True,
        )
    }
    app["state_synchronizer"] = _FakeStateSynchronizer(targets=[(706, 7001)], is_active=True)

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 706)

    matched = eq["matched_commands"][0]
    assert matched["cmd_id"] == 7001
    assert matched["streaming"] is True


async def test_matched_command_omits_streaming_when_not_in_state_targets(cli, app):
    cmd = JeedomCmd(id=7002, name="Temperature", generic_type="TEMP", type="info")
    snapshot = TopologySnapshot(
        timestamp="2026-07-05T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={707: JeedomEqLogic(id=707, name="Sensor Temp 2", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = _mapped_sensor(707, cmd)
    app["topology"] = snapshot
    app["eligibility"] = {707: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {707: mapping_res}
    app["publications"] = {
        707: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping_res, active_or_alive=True,
        )
    }
    # (707, 7002) not part of the streamed targets -> command must not carry the badge.
    app["state_synchronizer"] = _FakeStateSynchronizer(targets=[(999, 1)], is_active=True)

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 707)

    matched = eq["matched_commands"][0]
    assert "streaming" not in matched


async def test_diagnostics_reports_no_streaming_without_state_synchronizer(cli, app):
    """No state_synchronizer registered on app -> no crash, honest empty/false values."""
    cmd = JeedomCmd(id=7003, name="Temperature", generic_type="TEMP", type="info")
    snapshot = TopologySnapshot(
        timestamp="2026-07-05T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={708: JeedomEqLogic(id=708, name="Sensor Temp 3", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = _mapped_sensor(708, cmd)
    app["topology"] = snapshot
    app["eligibility"] = {708: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {708: mapping_res}
    app["publications"] = {
        708: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping_res, active_or_alive=True,
        )
    }
    # app["state_synchronizer"] intentionally left unset (None default from create_app-less bootstrap).

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 708)

    matched = eq["matched_commands"][0]
    assert "streaming" not in matched
    assert data["payload"]["summary"]["streaming_actif"] is False
    assert data["payload"]["summary"]["streaming_cibles_count"] == 0


async def test_summary_exposes_global_streaming_indicators(cli, app):
    cmd_a = JeedomCmd(id=7004, name="Temperature", generic_type="TEMP", type="info")
    cmd_b = JeedomCmd(id=7005, name="Humidite", generic_type="HUMIDITY", type="info")
    snapshot = TopologySnapshot(
        timestamp="2026-07-05T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            709: JeedomEqLogic(id=709, name="Sensor A", object_id=1, is_enable=True, cmds=[cmd_a]),
            710: JeedomEqLogic(id=710, name="Sensor B", object_id=1, is_enable=True, cmds=[cmd_b]),
        },
    )
    mapping_a = _mapped_sensor(709, cmd_a)
    mapping_b = _mapped_sensor(710, cmd_b)
    app["topology"] = snapshot
    app["eligibility"] = {
        709: EligibilityResult(is_eligible=True, reason_code="eligible"),
        710: EligibilityResult(is_eligible=True, reason_code="eligible"),
    }
    app["mappings"] = {709: mapping_a, 710: mapping_b}
    app["publications"] = {
        709: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping_a, active_or_alive=True,
        ),
        710: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping_b, active_or_alive=True,
        ),
    }
    app["state_synchronizer"] = _FakeStateSynchronizer(
        targets=[(709, 7004), (710, 7005)], is_active=True,
    )

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    assert data["payload"]["summary"]["streaming_actif"] is True
    assert data["payload"]["summary"]["streaming_cibles_count"] == 2


async def test_energy_badge_non_regression_alongside_streaming(cli, app):
    """Story 15.1's state_class/unit_of_measurement badge keeps working independently."""
    cmd = JeedomCmd(id=7006, name="Puissance", generic_type="POWER", type="info", unit="W")
    snapshot = TopologySnapshot(
        timestamp="2026-07-05T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Local technique")},
        eq_logics={711: JeedomEqLogic(id=711, name="Sensor W", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = _mapped_sensor(
        711, cmd,
        {"device_class": "power", "unit_of_measurement": "W", "state_class": "measurement"},
    )
    app["topology"] = snapshot
    app["eligibility"] = {711: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {711: mapping_res}
    app["publications"] = {
        711: PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping_res, active_or_alive=True,
        )
    }
    app["state_synchronizer"] = _FakeStateSynchronizer(targets=[(711, 7006)], is_active=True)

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 711)
    matched = eq["matched_commands"][0]

    assert matched["state_class"] == "measurement"
    assert matched["unit_of_measurement"] == "W"
    assert matched["streaming"] is True
