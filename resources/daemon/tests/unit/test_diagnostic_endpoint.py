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
    assert "matched_commands" in eq_100
    assert len(eq_100["matched_commands"]) == 0  # No commands mocked in eq_logics[100] in this test
    
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


# ---------------------------------------------------------------------------
# Story 4.2 — Tests for enriched diagnostic fields
# ---------------------------------------------------------------------------

async def test_diagnostics_detail_and_remediation_no_commands(aiohttp_client):
    """no_commands => action requise, v1_limitation=False, detail/remediation non vides."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-17T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salle")},
        eq_logics={400: JeedomEqLogic(id=400, name="Eq Sans Cmds", object_id=1, is_enable=True)},
    )
    app["topology"] = snapshot
    app["eligibility"] = {400: EligibilityResult(is_eligible=False, reason_code="no_commands")}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 400)

    assert eq["reason_code"] == "no_commands"
    assert eq["detail"] != ""
    assert eq["remediation"] != ""
    assert eq["v1_limitation"] is False
    assert eq["unmatched_commands"] == []


async def test_diagnostics_detail_and_remediation_no_mapping(aiohttp_client):
    """no_mapping => hors périmètre V1, v1_limitation=True."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-17T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salle")},
        eq_logics={401: JeedomEqLogic(id=401, name="Thermostat", object_id=1, is_enable=True)},
    )
    app["topology"] = snapshot
    app["eligibility"] = {401: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {}   # aucun mapping => reason_code "no_mapping" calculé dans le handler

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 401)

    assert eq["status"] == "Non publié"
    assert eq["reason_code"] == "no_mapping"
    assert eq["v1_limitation"] is True
    assert eq["detail"] != ""
    assert eq["remediation"] != ""
    assert eq["unmatched_commands"] == []


async def test_diagnostics_detail_and_remediation_no_supported_generic_type(aiohttp_client):
    """no_supported_generic_type => hors périmètre V1, v1_limitation=True."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-17T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salle")},
        eq_logics={410: JeedomEqLogic(id=410, name="Eq Type Exotique", object_id=1, is_enable=True)},
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        410: EligibilityResult(is_eligible=False, reason_code="no_supported_generic_type")
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 410)

    assert eq["reason_code"] == "no_supported_generic_type"
    assert eq["v1_limitation"] is True
    assert eq["detail"] != ""
    assert eq["remediation"] != ""
    assert eq["unmatched_commands"] == []


async def test_diagnostics_detail_and_remediation_ambiguous(aiohttp_client):
    """ambiguous_skipped => action requise, le detail mentionne l'ambiguïté."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-17T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salle")},
        eq_logics={402: JeedomEqLogic(id=402, name="Eq Ambigu", object_id=1, is_enable=True)},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="ambiguous",
        reason_code="ambiguous",
        jeedom_eq_id=402,
        ha_unique_id="light_402",
        ha_name="Eq Ambigu",
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {402: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {402: mapping_res}
    app["publications"] = {
        402: PublicationDecision(
            should_publish=False,
            reason="ambiguous_skipped",
            mapping_result=mapping_res,
            active_or_alive=False,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 402)

    assert eq["reason_code"] == "ambiguous_skipped"
    assert eq["v1_limitation"] is False
    assert "ambigu" in eq["detail"].lower() or "ambiguïté" in eq["detail"].lower()
    assert eq["remediation"] != ""
    assert eq["unmatched_commands"] == []


async def test_diagnostics_detail_and_remediation_excluded(aiohttp_client):
    """excluded_eqlogic => neutre, detail mentionne l'exclusion manuelle."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-17T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salle")},
        eq_logics={403: JeedomEqLogic(id=403, name="Eq Exclu", object_id=1, is_excluded=True)},
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        403: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 403)

    assert eq["status"] == "Exclu"
    assert eq["reason_code"] == "excluded_eqlogic"
    assert eq["v1_limitation"] is False
    assert "exclu" in eq["detail"].lower()
    assert eq["unmatched_commands"] == []


async def test_diagnostics_unmatched_commands_present(aiohttp_client):
    """Partiellement publié => unmatched_commands renseigné avec cmd_id, cmd_name, generic_type."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    cmd_mapped = JeedomCmd(id=5001, name="On", generic_type="LIGHT_ON")
    cmd_unmatched = JeedomCmd(id=5002, name="Couleur", generic_type="LIGHT_COLOR")

    snapshot = TopologySnapshot(
        timestamp="2026-03-17T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salle")},
        eq_logics={
            404: JeedomEqLogic(
                id=404,
                name="Lumiere RGB",
                object_id=1,
                is_enable=True,
                cmds=[cmd_mapped, cmd_unmatched],
            )
        },
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_only",
        jeedom_eq_id=404,
        ha_unique_id="light_404",
        ha_name="Lumiere RGB",
        commands={"LIGHT_ON": cmd_mapped},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {404: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {404: mapping_res}
    app["publications"] = {
        404: PublicationDecision(
            should_publish=True,
            reason="sure_mapping",
            mapping_result=mapping_res,
            active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 404)

    assert eq["status"] == "Partiellement publié"
    assert len(eq["unmatched_commands"]) == 1
    unmatched = eq["unmatched_commands"][0]
    assert unmatched["cmd_id"] == 5002
    assert unmatched["cmd_name"] == "Couleur"
    assert unmatched["generic_type"] == "LIGHT_COLOR"
    assert eq["detail"] != ""
    assert eq["remediation"] != ""
    assert eq["v1_limitation"] is False
    assert len(eq["matched_commands"]) == 1
    assert eq["matched_commands"][0]["cmd_id"] == 5001


async def test_diagnostics_published_fields_empty(aiohttp_client):
    """Publié => detail='', remediation='', v1_limitation=False, unmatched_commands=[]."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    cmd = JeedomCmd(id=6001, name="On", generic_type="LIGHT_ON")
    snapshot = TopologySnapshot(
        timestamp="2026-03-17T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salle")},
        eq_logics={
            405: JeedomEqLogic(id=405, name="Lumiere OK", object_id=1, is_enable=True, cmds=[cmd])
        },
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=405,
        ha_unique_id="light_405",
        ha_name="Lumiere OK",
        commands={"LIGHT_ON": cmd},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {405: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {405: mapping_res}
    app["publications"] = {
        405: PublicationDecision(
            should_publish=True,
            reason="sure_mapping",
            mapping_result=mapping_res,
            active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 405)

    assert eq["status"] == "Publié"
    assert eq["detail"] == ""
    assert eq["remediation"] == ""
    assert eq["v1_limitation"] is False
    assert eq["unmatched_commands"] == []


# ---------------------------------------------------------------------------
# Story 4.2 — Post-terrain correctifs : nouveaux champs eq_type_name,
# detected_generic_types, et doctrine couleur infra
# ---------------------------------------------------------------------------

async def test_diagnostics_eq_type_name_present(aiohttp_client):
    """eq_type_name doit être présent dans chaque entrée du payload diagnostics."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-17T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salle")},
        eq_logics={
            500: JeedomEqLogic(id=500, name="Eq Zwave", object_id=1, is_enable=True, eq_type_name="openzwave")
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {500: EligibilityResult(is_eligible=False, reason_code="no_commands")}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 500)

    assert "eq_type_name" in eq
    assert eq["eq_type_name"] == "openzwave"


async def test_diagnostics_detected_generic_types_no_supported(aiohttp_client):
    """no_supported_generic_type => detected_generic_types renseigné avec les types des commandes."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    cmd1 = JeedomCmd(id=7001, name="Etat", generic_type="ENERGY_STATE")
    cmd2 = JeedomCmd(id=7002, name="Puissance", generic_type="ENERGY_POWER")

    snapshot = TopologySnapshot(
        timestamp="2026-03-17T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salle")},
        eq_logics={
            501: JeedomEqLogic(
                id=501, name="Prise Energie", object_id=1, is_enable=True,
                cmds=[cmd1, cmd2]
            )
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        501: EligibilityResult(is_eligible=False, reason_code="no_supported_generic_type")
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 501)

    assert eq["reason_code"] == "no_supported_generic_type"
    assert eq["v1_limitation"] is True
    assert "detected_generic_types" in eq
    assert len(eq["detected_generic_types"]) == 2
    assert "ENERGY_STATE" in eq["detected_generic_types"]
    assert "ENERGY_POWER" in eq["detected_generic_types"]


async def test_diagnostics_detected_generic_types_ambiguous(aiohttp_client):
    """ambiguous_skipped => detected_generic_types renseigné avec les types des commandes."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    cmd1 = JeedomCmd(id=8001, name="On", generic_type="LIGHT_ON")
    cmd2 = JeedomCmd(id=8002, name="Monter", generic_type="COVER_UP")

    snapshot = TopologySnapshot(
        timestamp="2026-03-17T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salle")},
        eq_logics={
            502: JeedomEqLogic(
                id=502, name="Eq Ambigu Multi", object_id=1, is_enable=True,
                cmds=[cmd1, cmd2]
            )
        },
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="ambiguous",
        reason_code="ambiguous",
        jeedom_eq_id=502,
        ha_unique_id="light_502",
        ha_name="Eq Ambigu Multi",
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {502: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {502: mapping_res}
    app["publications"] = {
        502: PublicationDecision(
            should_publish=False,
            reason="ambiguous_skipped",
            mapping_result=mapping_res,
            active_or_alive=False,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 502)

    assert eq["reason_code"] == "ambiguous_skipped"
    assert eq["v1_limitation"] is False
    assert "detected_generic_types" in eq
    assert len(eq["detected_generic_types"]) == 2
    assert "LIGHT_ON" in eq["detected_generic_types"]
    assert "COVER_UP" in eq["detected_generic_types"]


async def test_diagnostics_infra_family_doctrine(aiohttp_client):
    """discovery_publish_failed => v1_limitation=False, detail/remediation non vides (doctrine panne infra)."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    cmd = JeedomCmd(id=9001, name="On", generic_type="LIGHT_ON")
    snapshot = TopologySnapshot(
        timestamp="2026-03-17T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salle")},
        eq_logics={
            503: JeedomEqLogic(id=503, name="Lumiere Fail", object_id=1, is_enable=True, cmds=[cmd])
        },
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=503,
        ha_unique_id="light_503",
        ha_name="Lumiere Fail",
        commands={"LIGHT_ON": cmd},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {503: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {503: mapping_res}
    app["publications"] = {
        503: PublicationDecision(
            should_publish=False,
            reason="discovery_publish_failed",
            mapping_result=mapping_res,
            active_or_alive=False,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 503)

    assert eq["reason_code"] == "discovery_publish_failed"
    assert eq["v1_limitation"] is False
    assert eq["detail"] != ""
    assert eq["remediation"] != ""
    assert eq["detected_generic_types"] == []
