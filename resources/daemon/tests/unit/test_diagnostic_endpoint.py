"""Unit tests for the diagnostic endpoint."""

import pytest
from aiohttp import web
from unittest.mock import MagicMock

from transport.http_server import create_app
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd, EligibilityResult
)
from models.mapping import MappingResult, PublicationDecision, LightCapabilities

@pytest.fixture
def app():
    return create_app(local_secret="test_secret")

@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)

async def test_diagnostics_unauthorized(cli):
    resp = await cli.get("/system/diagnostics")
    assert resp.status == 401

async def test_diagnostics_no_topology(cli):
    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "error"
    assert data["message"] == "Diagnostic indisponible : aucune donnée en mémoire (appelez /action/sync d'abord)."

async def test_diagnostics_with_data(cli, app):
    # Mock some runtime data
    snapshot = TopologySnapshot(
        timestamp="2026-03-16T12:00:00Z",
        objects={
            1: JeedomObject(id=1, name="Salon")
        },
        eq_logics={
            100: JeedomEqLogic(id=100, name="Lumiere", object_id=1, is_enable=True),
            101: JeedomEqLogic(id=101, name="Prise Exclue", object_id=1, is_excluded=True),
            102: JeedomEqLogic(id=102, name="Volet Sans Cmd", object_id=1, is_enable=True)
        }
    )
    
    eligibility = {
        100: EligibilityResult(is_eligible=True, reason_code="eligible"),
        101: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
        102: EligibilityResult(is_eligible=False, reason_code="no_commands"),
    }
    
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=100,
        ha_unique_id="light_100",
        ha_name="Lumiere",
        capabilities=LightCapabilities(has_on_off=True)
    )
    mappings = {
        100: mapping_res
    }
    
    publications = {
        100: PublicationDecision(
            should_publish=True,
            reason="sure_mapping",
            mapping_result=mapping_res,
            active_or_alive=True
        )
    }

    app["topology"] = snapshot
    app["eligibility"] = eligibility
    app["mappings"] = mappings
    app["publications"] = publications

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    assert resp.status == 200
    data = await resp.json()
    
    assert data["status"] == "ok"
    equipments = data["payload"]["equipments"]
    assert len(equipments) == 3
    
    eq_100 = next(e for e in equipments if e["eq_id"] == 100)
    assert eq_100["object_name"] == "Salon"
    assert eq_100["name"] == "Lumiere"
    assert eq_100["status"] == "Publié"
    assert eq_100["confidence"] == "Sûr"
    assert eq_100["reason_code"] == "sure_mapping"
    
    eq_101 = next(e for e in equipments if e["eq_id"] == 101)
    assert eq_101["status"] == "Exclu"
    assert eq_101["confidence"] == "Ignoré"
    assert eq_101["reason_code"] == "excluded_eqlogic"
    
    eq_102 = next(e for e in equipments if e["eq_id"] == 102)
    assert eq_102["status"] == "Non publié"
    assert eq_102["confidence"] == "Ignoré"
    assert eq_102["reason_code"] == "no_commands"

async def test_diagnostics_partial_or_not_published(cli, app):
    # Test valid eligibility but not published
    snapshot = TopologySnapshot(
        timestamp="2026-03-16T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={200: JeedomEqLogic(id=200, name="Lumiere Fail", object_id=1, is_enable=True)}
    )
    eligibility = {200: EligibilityResult(is_eligible=True, reason_code="eligible")}
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="ambiguous",
        reason_code="light_ambiguous",
        jeedom_eq_id=200,
        ha_unique_id="light_200",
        ha_name="Lumiere",
        capabilities=LightCapabilities(has_on_off=True)
    )
    app["topology"] = snapshot
    app["eligibility"] = eligibility
    app["mappings"] = {200: mapping_res}
    
    # Not published
    app["publications"] = {
        200: PublicationDecision(
            should_publish=False,
            reason="ambiguous_skipped",
            mapping_result=mapping_res,
            active_or_alive=False
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    equipments = data["payload"]["equipments"]
    eq_200 = equipments[0]
    
    assert eq_200["status"] == "Non publié"
    assert eq_200["confidence"] == "Ambigu"
    assert eq_200["reason_code"] == "ambiguous_skipped"

async def test_diagnostics_partiellement_publie(cli, app):
    # Test valid eligibility, published but has unmapped commands with generic_type
    cmd_mapped = JeedomCmd(id=3001, name="On", generic_type="LIGHT_ON")
    cmd_unmapped = JeedomCmd(id=3002, name="Color", generic_type="LIGHT_COLOR")
    
    snapshot = TopologySnapshot(
        timestamp="2026-03-16T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={300: JeedomEqLogic(id=300, name="Lumiere Partielle", object_id=1, is_enable=True, cmds=[cmd_mapped, cmd_unmapped])}
    )
    eligibility = {300: EligibilityResult(is_eligible=True, reason_code="eligible")}
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_only",
        jeedom_eq_id=300,
        ha_unique_id="light_300",
        ha_name="Lumiere",
        commands={"LIGHT_ON": cmd_mapped},
        capabilities=LightCapabilities(has_on_off=True)
    )
    app["topology"] = snapshot
    app["eligibility"] = eligibility
    app["mappings"] = {300: mapping_res}
    
    app["publications"] = {
        300: PublicationDecision(
            should_publish=True,
            reason="sure_mapping",
            mapping_result=mapping_res,
            active_or_alive=True
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    equipments = data["payload"]["equipments"]
    eq_300 = equipments[0]
    
    assert eq_300["status"] == "Partiellement publié"
    assert eq_300["confidence"] == "Sûr"
    assert eq_300["reason_code"] == "sure_mapping"
