"""Story 7.1 — projection_validity exposed in diagnostic traceability.

The diagnostic reflects the pipeline; it does not rebuild it.
"""

from __future__ import annotations

import pytest

from models.mapping import (
    LightCapabilities,
    MappingResult,
    ProjectionValidity,
    PublicationDecision,
    PublicationResult,
)
from models.topology import EligibilityResult, JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from transport.http_server import create_app


SECRET = "test-secret-7-1"
HEADERS = {"X-Local-Secret": SECRET}


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _light_mapping(eq_id: int) -> MappingResult:
    cmd = JeedomCmd(id=eq_id * 10, name="On", generic_type="LIGHT_ON")
    return MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Eq{eq_id}",
        commands={"LIGHT_ON": cmd},
        capabilities=LightCapabilities(has_on_off=True),
    )


async def _diagnostic_equipments(cli, app):
    resp = await cli.get("/system/diagnostics", headers=HEADERS)
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"
    return data["payload"]["equipments"]


async def test_7_1_every_equipment_exposes_projection_validity_additively(cli, app):
    valid_mapping = _light_mapping(7101)
    valid_mapping.projection_validity = ProjectionValidity(
        is_valid=True,
        reason_code=None,
        missing_fields=[],
        missing_capabilities=[],
    )
    decision = PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=valid_mapping,
        active_or_alive=True,
    )
    valid_mapping.publication_decision_ref = decision
    valid_mapping.publication_result = PublicationResult(status="success")

    app["topology"] = TopologySnapshot(
        timestamp="2026-04-24T10:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            7101: JeedomEqLogic(id=7101, name="Nominal", object_id=1, is_enable=True),
            7102: JeedomEqLogic(id=7102, name="Excluded", object_id=1, is_excluded=True),
        },
    )
    app["eligibility"] = {
        7101: EligibilityResult(is_eligible=True, reason_code="eligible"),
        7102: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
    }
    app["mappings"] = {7101: valid_mapping}
    app["publications"] = {7101: decision}

    equipments = await _diagnostic_equipments(cli, app)

    for eq in equipments:
        traceability = eq["traceability"]
        assert "observed_commands" in traceability
        assert "typing_trace" in traceability
        assert "decision_trace" in traceability
        assert "publication_trace" in traceability
        assert "projection_validity" in traceability
        assert "pipeline_step_visible" in eq

        projection_validity = traceability["projection_validity"]
        assert set(projection_validity) == {
            "is_valid",
            "reason_code",
            "missing_fields",
            "missing_capabilities",
        }


async def test_7_1_nominal_projection_validity_reflects_mapping_result(cli, app):
    mapping = _light_mapping(7110)
    mapping.projection_validity = ProjectionValidity(
        is_valid=True,
        reason_code=None,
        missing_fields=[],
        missing_capabilities=[],
    )
    decision = PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=mapping,
        active_or_alive=True,
    )
    mapping.publication_decision_ref = decision

    app["topology"] = TopologySnapshot(
        timestamp="2026-04-24T10:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={7110: JeedomEqLogic(id=7110, name="Nominal", object_id=1, is_enable=True)},
    )
    app["eligibility"] = {7110: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {7110: mapping}
    app["publications"] = {7110: decision}

    eq = (await _diagnostic_equipments(cli, app))[0]

    assert eq["traceability"]["projection_validity"] == {
        "is_valid": True,
        "reason_code": None,
        "missing_fields": [],
        "missing_capabilities": [],
    }


async def test_7_1_invalid_projection_blocks_positive_publication(cli, app):
    mapping = _light_mapping(7120)
    mapping.projection_validity = ProjectionValidity(
        is_valid=False,
        reason_code="ha_missing_state_topic",
        missing_fields=["state_topic"],
        missing_capabilities=["has_state"],
    )
    decision = PublicationDecision(
        should_publish=False,
        reason="ha_missing_state_topic",
        mapping_result=mapping,
        active_or_alive=False,
    )
    mapping.publication_decision_ref = decision

    app["topology"] = TopologySnapshot(
        timestamp="2026-04-24T10:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={7120: JeedomEqLogic(id=7120, name="Invalid", object_id=1, is_enable=True)},
    )
    app["eligibility"] = {7120: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {7120: mapping}
    app["publications"] = {7120: decision}

    eq = (await _diagnostic_equipments(cli, app))[0]

    assert eq["traceability"]["projection_validity"] == {
        "is_valid": False,
        "reason_code": "ha_missing_state_topic",
        "missing_fields": ["state_topic"],
        "missing_capabilities": ["has_state"],
    }
    assert app["publications"][7120].should_publish is False
    assert eq["pipeline_step_visible"] == 3
    assert eq["status_code"] != "published"


async def test_7_1_skipped_projection_validity_is_explicit_without_mapping_result(cli, app):
    app["topology"] = TopologySnapshot(
        timestamp="2026-04-24T10:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={7130: JeedomEqLogic(id=7130, name="Excluded", object_id=1, is_excluded=True)},
    )
    app["eligibility"] = {7130: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")}
    app["mappings"] = {}
    app["publications"] = {}

    eq = (await _diagnostic_equipments(cli, app))[0]

    assert app["mappings"].get(7130) is None
    assert eq["pipeline_step_visible"] == 1
    assert eq["traceability"]["projection_validity"] == {
        "is_valid": None,
        "reason_code": "skipped_projection_validation_not_reached",
        "missing_fields": [],
        "missing_capabilities": [],
    }
