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
            reason="sure",
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
    assert data["payload"]["summary"]["home_statut"] == "Partiellement publiee"
    assert data["payload"]["rooms"][0]["home_statut"] == "Partiellement publiee"

    eq_100 = next(e for e in equipments if e["eq_id"] == 100)
    assert eq_100["object_name"] == "Salon"
    assert eq_100["name"] == "Lumiere"
    assert eq_100["status"] == "Publié"
    assert eq_100["confidence"] == "Sûr"
    assert eq_100["reason_code"] == "sure"
    assert "matched_commands" in eq_100
    assert len(eq_100["matched_commands"]) == 0  # No commands mocked in eq_logics[100] in this test

    eq_101 = next(e for e in equipments if e["eq_id"] == 101)
    assert eq_101["status"] == "Exclu"
    assert eq_101["confidence"] == "Ignoré"
    assert eq_101["reason_code"] == "excluded_eqlogic"

    eq_102 = next(e for e in equipments if e["eq_id"] == 102)
    assert eq_102["status"] == "Non supporté"
    assert eq_102["confidence"] == "Ignoré"
    assert eq_102["reason_code"] == "no_commands"


async def test_diagnostics_home_statut_zero_inclus(cli, app):
    snapshot = TopologySnapshot(
        timestamp="2026-03-16T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Garage")},
        eq_logics={
            150: JeedomEqLogic(id=150, name="Eq Exclu 1", object_id=1, is_excluded=True),
            151: JeedomEqLogic(id=151, name="Eq Exclu 2", object_id=1, is_excluded=True),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        150: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
        151: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()

    assert data["payload"]["summary"]["home_statut"] == "Non publiee"
    assert data["payload"]["rooms"][0]["home_statut"] == "Non publiee"
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
    
    assert eq_200["status"] == "Ambigu"
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
            reason="sure",
            mapping_result=mapping_res,
            active_or_alive=True
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    equipments = data["payload"]["equipments"]
    eq_300 = equipments[0]

    # Story 3.1 : "Partiellement publié" supprimé — publication partielle → "Publié" + unmatched_commands
    assert eq_300["status"] == "Publié"
    assert eq_300["confidence"] == "Sûr"
    assert eq_300["reason_code"] == "sure"


# ---------------------------------------------------------------------------
# Story 4.2 — Tests for enriched diagnostic fields
# ---------------------------------------------------------------------------

async def test_diagnostics_story_4_2_low_confidence_exposes_policy_cause(aiohttp_client):
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    cmd = JeedomCmd(id=4601, name="On", generic_type="LIGHT_ON")
    snapshot = TopologySnapshot(
        timestamp="2026-04-14T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={4600: JeedomEqLogic(id=4600, name="Lampe Buffet", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="probable",
        reason_code="light_on_off",
        jeedom_eq_id=4600,
        ha_unique_id="light_4600",
        ha_name="Lampe Buffet",
        commands={"LIGHT_ON": cmd},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {4600: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {4600: mapping_res}
    app["publications"] = {
        4600: PublicationDecision(
            should_publish=False,
            reason="low_confidence",
            mapping_result=mapping_res,
            active_or_alive=False,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 4600)

    assert eq["reason_code"] == "low_confidence"
    assert eq["cause_code"] == "low_confidence"
    assert eq["cause_label"] == "Confiance insuffisante pour la politique active"
    assert eq["cause_action"] == (
        "Assouplir la politique de confiance si vous souhaitez autoriser un mapping moins fiable."
    )
    assert "politique active" in eq["detail"]
    assert eq["detail"] != "Cause inconnue."
    assert eq["remediation"] == (
        "Assouplir la politique de confiance si vous souhaitez autoriser un mapping moins fiable."
    )


async def test_diagnostics_story_4_2_not_in_product_scope_exposes_governance_cause(aiohttp_client):
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    cmd = JeedomCmd(id=4701, name="Etat", generic_type="LIGHT_STATE")
    snapshot = TopologySnapshot(
        timestamp="2026-04-14T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={4700: JeedomEqLogic(id=4700, name="Détecteur multi-capteurs", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_state_only",
        jeedom_eq_id=4700,
        ha_unique_id="light_4700",
        ha_name="Détecteur multi-capteurs",
        commands={"LIGHT_STATE": cmd},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {4700: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {4700: mapping_res}
    app["publications"] = {
        4700: PublicationDecision(
            should_publish=False,
            reason="ha_component_not_in_product_scope",
            mapping_result=mapping_res,
            active_or_alive=False,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 4700)

    assert eq["reason_code"] == "ha_component_not_in_product_scope"
    assert eq["cause_code"] == "not_in_product_scope"
    # Story 6.3 — class 3 : libellé gouvernance non arbitraire
    assert eq["cause_label"] == "Type d'entité HA reconnu — hors périmètre d'ouverture du cycle courant"
    # Story 6.3 — class 3 : cause_action = None (aucune action utilisateur directe)
    assert eq["cause_action"] is None
    assert "cycle courant" in eq["detail"]
    assert eq["detail"] != "Cause inconnue."
    # remediation provient de _DIAGNOSTIC_MESSAGES (http_server.py, inchangé)
    assert eq["remediation"] == (
        "Aucune action côté Jeedom : ce composant n'est pas encore pris en charge dans le cycle courant."
    )
    assert eq["cause_label"] != "Aucun mapping compatible"

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
    """no_projection_possible (Story 9.4) => aucune commande exploitable, v1_limitation=False."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-17T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salle")},
        eq_logics={401: JeedomEqLogic(id=401, name="Thermostat", object_id=1, is_enable=True)},
    )
    app["topology"] = snapshot
    app["eligibility"] = {401: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {}   # aucun mapping => reason_code "no_projection_possible" (Story 9.4)

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 401)

    assert eq["status"] == "Non supporté"
    assert eq["reason_code"] == "no_projection_possible"
    assert eq["v1_limitation"] is False
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
            reason="sure",
            mapping_result=mapping_res,
            active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 404)

    # Story 3.1 : publication partielle → "Publié" avec unmatched_commands (pas "Partiellement publié")
    assert eq["status"] == "Publié"
    assert len(eq["unmatched_commands"]) == 1
    unmatched = eq["unmatched_commands"][0]
    assert unmatched["cmd_id"] == 5002
    assert unmatched["cmd_name"] == "Couleur"
    assert unmatched["generic_type"] == "LIGHT_COLOR"
    assert eq["detail"] == ""
    assert eq["remediation"] == ""
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
            reason="sure",
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


# ---------------------------------------------------------------------------
# Story 4.2bis — AC1: Contrat Backend Structuré (Traceability)
# AC2: Taxonomie normative des reason_codes
# AC5: Correction v1_compatibility (Binary Sensor)
# ---------------------------------------------------------------------------

_CLOSED_REASON_CODES = {
    "published", "excluded", "disabled_eqlogic", "no_commands",
    "ambiguous_skipped", "no_generic_type_configured",
    "no_supported_generic_type", "discovery_publish_failed",
}


async def test_diagnostics_traceability_schema_published(aiohttp_client):
    """AC1 — traceability complet pour un équipement publié; AC5 v1_compatibility light."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    cmd = JeedomCmd(id=9100, name="On", generic_type="LIGHT_ON")
    snapshot = TopologySnapshot(
        timestamp="2026-03-18T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={600: JeedomEqLogic(id=600, name="Lumiere V1", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=600,
        ha_unique_id="light_600",
        ha_name="Lumiere V1",
        commands={"LIGHT_ON": cmd},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {600: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {600: mapping_res}
    app["publications"] = {
        600: PublicationDecision(
            should_publish=True,
            reason="sure",
            mapping_result=mapping_res,
            active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 600)

    # AC1: structure traceability obligatoire
    assert "traceability" in eq
    tr = eq["traceability"]
    assert "observed_commands" in tr
    assert "typing_trace" in tr
    assert "decision_trace" in tr
    assert "publication_trace" in tr

    # observed_commands: toutes les commandes
    assert len(tr["observed_commands"]) == 1
    oc = tr["observed_commands"][0]
    assert oc["id"] == 9100
    assert oc["name"] == "On"
    assert oc["generic_type"] == "LIGHT_ON"

    # typing_trace: depuis mapping.commands
    assert len(tr["typing_trace"]) == 1
    tt = tr["typing_trace"][0]
    assert tt["logical_role"] == "LIGHT_ON"
    assert tt["command_id"] == 9100
    assert tt["configured_type"] == "LIGHT_ON"
    assert tt["used_type"] == "LIGHT_ON"

    # decision_trace: taxonomie fermée
    dt = tr["decision_trace"]
    assert dt["ha_entity_type"] == "light"
    assert dt["confidence"] == "sure"
    assert dt["reason_code"] == "published"  # AC2: published pour équipement publié
    assert dt["reason_code"] in _CLOSED_REASON_CODES

    # publication_trace
    pt = tr["publication_trace"]
    assert pt["last_discovery_publish_result"] == "success"
    assert pt["last_discovery_publish_result"] in ("success", "failed", "not_attempted")
    assert "last_publish_timestamp" in pt

    # AC5: v1_compatibility True pour light
    assert eq["v1_compatibility"] is True


async def test_diagnostics_traceability_excluded(aiohttp_client):
    """AC1 — traceability présent avec valeurs neutres pour équipement exclu."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-18T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={601: JeedomEqLogic(id=601, name="Eq Exclu V1", object_id=1, is_excluded=True)},
    )
    app["topology"] = snapshot
    app["eligibility"] = {601: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 601)

    tr = eq["traceability"]
    assert tr["observed_commands"] == []
    assert tr["typing_trace"] == []

    dt = tr["decision_trace"]
    assert dt["ha_entity_type"] is None
    assert dt["confidence"] == "ignore"
    assert dt["reason_code"] == "excluded"  # AC2: excluded_eqlogic → excluded
    assert dt["reason_code"] in _CLOSED_REASON_CODES

    assert tr["publication_trace"]["last_discovery_publish_result"] == "not_attempted"
    assert eq["v1_compatibility"] is False


async def test_diagnostics_v1_compatibility_binary_sensor(aiohttp_client):
    """AC5 — v1_compatibility=True pour binary_sensor."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    cmd = JeedomCmd(id=9200, name="Etat", generic_type="OPENING")
    snapshot = TopologySnapshot(
        timestamp="2026-03-18T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Entrée")},
        eq_logics={700: JeedomEqLogic(id=700, name="Porte", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = MappingResult(
        ha_entity_type="binary_sensor",
        confidence="sure",
        reason_code="binary_sensor_opening",
        jeedom_eq_id=700,
        ha_unique_id="binary_sensor_700",
        ha_name="Porte",
        commands={"OPENING": cmd},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {700: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {700: mapping_res}
    app["publications"] = {
        700: PublicationDecision(
            should_publish=True,
            reason="sure_mapping",
            mapping_result=mapping_res,
            active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 700)

    # AC5: binary_sensor fait partie du périmètre V1
    assert eq["v1_compatibility"] is True
    dt = eq["traceability"]["decision_trace"]
    assert dt["ha_entity_type"] == "binary_sensor"
    assert dt["reason_code"] == "published"


async def test_diagnostics_reason_code_normalization_no_generic_type(aiohttp_client):
    """AC2 — decision_trace.reason_code: no_supported_generic_type → no_generic_type_configured."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-18T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={800: JeedomEqLogic(id=800, name="Eq No GT", object_id=1, is_enable=True)},
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        800: EligibilityResult(is_eligible=False, reason_code="no_supported_generic_type")
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 800)

    # Top-level reason_code inchangé (rétro-compat 4.1/4.2)
    assert eq["reason_code"] == "no_supported_generic_type"
    # decision_trace.reason_code normalisé vers taxonomie fermée
    dt = eq["traceability"]["decision_trace"]
    assert dt["reason_code"] == "no_generic_type_configured"
    assert dt["reason_code"] in _CLOSED_REASON_CODES


async def test_diagnostics_reason_code_normalization_no_mapping(aiohttp_client):
    """AC2 — decision_trace.reason_code: no_projection_possible → no_commands (fallback conservateur)."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-18T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={801: JeedomEqLogic(id=801, name="Thermostat", object_id=1, is_enable=True)},
    )
    app["topology"] = snapshot
    app["eligibility"] = {801: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {}  # no mapping → reason_code="no_projection_possible" (Story 9.4)

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 801)

    assert eq["reason_code"] == "no_projection_possible"  # top-level Story 9.4
    dt = eq["traceability"]["decision_trace"]
    assert dt["reason_code"] == "no_commands"  # fallback conservateur (_build_traceability)
    assert dt["reason_code"] in _CLOSED_REASON_CODES


async def test_diagnostics_traceability_discovery_failed(aiohttp_client):
    """AC1 — publication_trace.last_discovery_publish_result='failed' quand discovery_publish_failed."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    cmd = JeedomCmd(id=9300, name="On", generic_type="LIGHT_ON")
    snapshot = TopologySnapshot(
        timestamp="2026-03-18T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={802: JeedomEqLogic(id=802, name="Lumiere KO", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=802,
        ha_unique_id="light_802",
        ha_name="Lumiere KO",
        commands={"LIGHT_ON": cmd},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {802: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {802: mapping_res}
    app["publications"] = {
        802: PublicationDecision(
            should_publish=False,
            reason="discovery_publish_failed",
            mapping_result=mapping_res,
            active_or_alive=False,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 802)

    pt = eq["traceability"]["publication_trace"]
    assert pt["last_discovery_publish_result"] == "failed"
    dt = eq["traceability"]["decision_trace"]
    assert dt["reason_code"] == "discovery_publish_failed"
    assert dt["reason_code"] in _CLOSED_REASON_CODES


# ---------------------------------------------------------------------------
# Story 4.2bis retouches — AC2 taxonomie fermée : cas legacy
# AC5 : non publié mais V1-compatible
# typing_trace : configured_type vs used_type
# ---------------------------------------------------------------------------

async def test_diagnostics_reason_code_disabled_legacy(aiohttp_client):
    """AC2 — reason_code legacy 'disabled' → 'disabled_eqlogic' dans decision_trace."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-18T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={900: JeedomEqLogic(id=900, name="Eq Disabled Legacy", object_id=1, is_enable=False)},
    )
    app["topology"] = snapshot
    app["eligibility"] = {900: EligibilityResult(is_eligible=False, reason_code="disabled")}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 900)

    assert eq["reason_code"] == "disabled"  # top-level inchangé
    dt = eq["traceability"]["decision_trace"]
    assert dt["reason_code"] == "disabled_eqlogic"
    assert dt["reason_code"] in _CLOSED_REASON_CODES


async def test_diagnostics_reason_code_local_availability_publish_failed(aiohttp_client):
    """AC2 — 'local_availability_publish_failed' → 'discovery_publish_failed' dans decision_trace."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    cmd = JeedomCmd(id=9500, name="On", generic_type="LIGHT_ON")
    snapshot = TopologySnapshot(
        timestamp="2026-03-18T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={901: JeedomEqLogic(id=901, name="Lumiere Avail KO", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=901,
        ha_unique_id="light_901",
        ha_name="Lumiere Avail KO",
        commands={"LIGHT_ON": cmd},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {901: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {901: mapping_res}
    app["publications"] = {
        901: PublicationDecision(
            should_publish=False,
            reason="local_availability_publish_failed",
            mapping_result=mapping_res,
            active_or_alive=False,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 901)

    assert eq["reason_code"] == "local_availability_publish_failed"  # top-level inchangé
    dt = eq["traceability"]["decision_trace"]
    assert dt["reason_code"] == "discovery_publish_failed"  # normalisé dans la famille infra
    assert dt["reason_code"] in _CLOSED_REASON_CODES
    # H2 review fix: publication_trace cohérent avec decision_trace
    pt = eq["traceability"]["publication_trace"]
    assert pt["last_discovery_publish_result"] == "failed"


async def test_diagnostics_reason_code_unknown_fallback(aiohttp_client):
    """AC2 — reason_code 'unknown' (pas d'eligibility) → code fermé dans decision_trace."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-18T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={902: JeedomEqLogic(id=902, name="Eq Sans Eligibility", object_id=1, is_enable=True)},
    )
    app["topology"] = snapshot
    app["eligibility"] = {}  # no eligibility result for this eq

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 902)

    dt = eq["traceability"]["decision_trace"]
    assert dt["reason_code"] in _CLOSED_REASON_CODES, (
        f"decision_trace.reason_code '{dt['reason_code']}' n'est pas dans la taxonomie fermée"
    )


async def test_diagnostics_v1_compatibility_not_published_but_v1(aiohttp_client):
    """AC5 — v1_compatibility=True même pour équipement non publié (ambiguous_skipped) mais V1-compatible."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    cmd = JeedomCmd(id=9600, name="On", generic_type="LIGHT_ON")
    snapshot = TopologySnapshot(
        timestamp="2026-03-18T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={903: JeedomEqLogic(id=903, name="Lumiere Ambigue", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="ambiguous",
        reason_code="ambiguous",
        jeedom_eq_id=903,
        ha_unique_id="light_903",
        ha_name="Lumiere Ambigue",
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {903: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {903: mapping_res}
    app["publications"] = {
        903: PublicationDecision(
            should_publish=False,
            reason="ambiguous_skipped",
            mapping_result=mapping_res,
            active_or_alive=False,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 903)

    # Story 3.1 : ambiguous_skipped → "Ambigu" (pas "Non publié")
    assert eq["status"] == "Ambigu"
    # AC5 : même non publié, si un type V1-compatible a été détecté, v1_compatibility=True
    assert eq["v1_compatibility"] is True


async def test_diagnostics_typing_trace_configured_vs_used(aiohttp_client):
    """AC1 — typing_trace expose bien configured_type et used_type séparément."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    cmd = JeedomCmd(id=9700, name="Slider", generic_type="LIGHT_SLIDER")
    snapshot = TopologySnapshot(
        timestamp="2026-03-18T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={904: JeedomEqLogic(id=904, name="Lumiere Slider", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off_brightness",
        jeedom_eq_id=904,
        ha_unique_id="light_904",
        ha_name="Lumiere Slider",
        commands={"LIGHT_SLIDER": cmd},
        capabilities=LightCapabilities(has_on_off=True, has_brightness=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {904: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {904: mapping_res}
    app["publications"] = {
        904: PublicationDecision(
            should_publish=True,
            reason="sure",
            mapping_result=mapping_res,
            active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 904)

    tr = eq["traceability"]
    assert len(tr["typing_trace"]) == 1
    tt = tr["typing_trace"][0]
    # Les deux champs doivent être présents et distincts (ou identiques si pas de déviation)
    assert "configured_type" in tt
    assert "used_type" in tt
    assert tt["configured_type"] == "LIGHT_SLIDER"
    assert tt["used_type"] == "LIGHT_SLIDER"
    assert tt["logical_role"] == "LIGHT_SLIDER"


# ---------------------------------------------------------------------------
# Story 3.3 — Tests de contrat du payload agrégé
# ---------------------------------------------------------------------------

async def test_diagnostics_payload_has_summary_rooms_equipments(aiohttp_client):
    """Le payload doit contenir les trois clés summary, rooms, equipments."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-26T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            500: JeedomEqLogic(id=500, name="Lumiere", object_id=1, is_enable=True),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {500: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    assert resp.status == 200
    data = await resp.json()
    payload = data["payload"]

    assert "summary" in payload
    assert "rooms" in payload
    assert "equipments" in payload


async def test_diagnostics_summary_structure(aiohttp_client):
    """Le summary global doit avoir tous les champs du contrat 3.3."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-26T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            501: JeedomEqLogic(id=501, name="Prise", object_id=1, is_enable=True),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {501: EligibilityResult(is_eligible=False, reason_code="no_commands")}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    summary = data["payload"]["summary"]

    assert "primary_aggregated_status" in summary
    assert "total_equipments" in summary
    assert "counts_by_status" in summary
    assert "counts_by_reason" in summary
    assert isinstance(summary["total_equipments"], int)
    assert isinstance(summary["counts_by_status"], dict)
    assert isinstance(summary["counts_by_reason"], dict)


async def test_diagnostics_rooms_structure(aiohttp_client):
    """Chaque entrée rooms doit contenir object_id, object_name, summary."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-26T00:00:00Z",
        objects={2: JeedomObject(id=2, name="Cuisine")},
        eq_logics={
            502: JeedomEqLogic(id=502, name="Detecteur", object_id=2, is_enable=True),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {502: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    rooms = data["payload"]["rooms"]

    assert len(rooms) == 1
    room = rooms[0]
    assert "object_id" in room
    assert "object_name" in room
    assert "summary" in room
    room_summary = room["summary"]
    assert "primary_aggregated_status" in room_summary
    assert "total_equipments" in room_summary
    assert "counts_by_status" in room_summary
    assert "counts_by_reason" in room_summary


async def test_diagnostics_individual_equipments_unchanged(aiohttp_client):
    """AC 6 — La structure des équipements individuels est inchangée après l'ajout des agrégats."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-26T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            503: JeedomEqLogic(id=503, name="Lumiere Test", object_id=1, is_enable=True),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {503: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    equipments = data["payload"]["equipments"]

    assert len(equipments) == 1
    eq = equipments[0]
    # Tous les champs existants doivent être présents
    expected_fields = {
        "eq_id", "object_name", "name", "eq_type_name", "status", "status_code",
        "confidence", "reason_code", "detail", "remediation", "v1_limitation",
        "matched_commands", "unmatched_commands", "detected_generic_types",
        "v1_compatibility", "traceability",
    }
    assert expected_fields.issubset(set(eq.keys()))
    assert eq["eq_id"] == 503
    assert eq["status"] == "Exclu"
    assert eq["status_code"] == "excluded"
    assert eq["reason_code"] == "excluded_eqlogic"


async def test_diagnostics_global_summary_counts_match_equipments(aiohttp_client):
    """La somme des counts_by_status global == total_equipments."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-26T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            504: JeedomEqLogic(id=504, name="A", object_id=1, is_enable=True),
            505: JeedomEqLogic(id=505, name="B", object_id=1, is_excluded=True),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        504: EligibilityResult(is_eligible=False, reason_code="no_commands"),
        505: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    summary = data["payload"]["summary"]

    assert summary["total_equipments"] == 2
    assert sum(summary["counts_by_status"].values()) == summary["total_equipments"]


async def test_diagnostics_room_summary_partial_published(aiohttp_client):
    """Une pièce avec publié + exclu → primary_aggregated_status = partially_published."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=506,
        ha_unique_id="light_506",
        ha_name="Lumiere Pub",
        capabilities=LightCapabilities(has_on_off=True),
    )

    snapshot = TopologySnapshot(
        timestamp="2026-03-26T00:00:00Z",
        objects={3: JeedomObject(id=3, name="Bureau")},
        eq_logics={
            506: JeedomEqLogic(id=506, name="Lumiere Pub", object_id=3, is_enable=True),
            507: JeedomEqLogic(id=507, name="Prise Exclue", object_id=3, is_excluded=True),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        506: EligibilityResult(is_eligible=True, reason_code="eligible"),
        507: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
    }
    app["mappings"] = {506: mapping_res}
    app["publications"] = {
        506: PublicationDecision(
            should_publish=True,
            reason="sure",
            mapping_result=mapping_res,
            active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    rooms = data["payload"]["rooms"]

    assert len(rooms) == 1
    bureau = rooms[0]
    assert bureau["object_name"] == "Bureau"
    assert bureau["summary"]["primary_aggregated_status"] == "partially_published"
    assert bureau["summary"]["counts_by_status"]["published"] == 1
    assert bureau["summary"]["counts_by_status"]["excluded"] == 1


# ---------------------------------------------------------------------------
# Story 4.1 — Contrat UI canonique 4D : perimetre / statut / ecart / cause
# ---------------------------------------------------------------------------

async def test_diagnostics_4d_fields_present_published(aiohttp_client):
    """Task 6.1 — Champs UI canoniques présents pour un équipement publié."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    cmd = JeedomCmd(id=4100, name="On", generic_type="LIGHT_ON")
    snapshot = TopologySnapshot(
        timestamp="2026-03-27T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={4100: JeedomEqLogic(id=4100, name="Lumiere Pub 4D", object_id=1, is_enable=True, cmds=[cmd])},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=4100,
        ha_unique_id="light_4100",
        ha_name="Lumiere Pub 4D",
        commands={"LIGHT_ON": cmd},
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {4100: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {4100: mapping_res}
    app["publications"] = {
        4100: PublicationDecision(
            should_publish=True,
            reason="sure",
            mapping_result=mapping_res,
            active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 4100)

    # Task 6.1 — Champs UI canoniques présents
    assert "perimetre" in eq
    assert "statut" in eq
    assert "ecart" in eq
    assert "cause_code" in eq
    assert "cause_label" in eq
    assert "cause_action" in eq
    assert "ha_type" in eq

    # Cas 1 : inclus + publié + aligné
    assert eq["perimetre"] == "inclus"
    assert eq["statut"] == "publie"
    assert eq["ecart"] is False
    assert eq["cause_code"] is None
    assert eq["cause_label"] is None
    assert eq["cause_action"] is None
    assert eq["ha_type"] == "light"


async def test_diagnostics_4d_compteurs_in_summary_and_rooms(aiohttp_client):
    """Task 6.2 — compteurs présents dans payload.summary et chaque entrée payload.rooms."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-27T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            4200: JeedomEqLogic(id=4200, name="Eq Inclu", object_id=1, is_enable=True),
            4201: JeedomEqLogic(id=4201, name="Eq Exclu", object_id=1, is_excluded=True),
        },
    )
    app["topology"] = snapshot
    app["eligibility"] = {
        4200: EligibilityResult(is_eligible=False, reason_code="no_commands"),
        4201: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    payload = data["payload"]

    # summary global — compteurs présents
    assert "compteurs" in payload["summary"]
    cpt = payload["summary"]["compteurs"]
    assert "total" in cpt
    assert "inclus" in cpt
    assert "exclus" in cpt
    assert "ecarts" in cpt
    assert cpt["total"] == 2
    assert cpt["inclus"] + cpt["exclus"] == cpt["total"]  # invariant

    # rooms — compteurs présents dans chaque entrée
    assert len(payload["rooms"]) == 1
    room = payload["rooms"][0]
    assert "compteurs" in room
    room_cpt = room["compteurs"]
    assert "total" in room_cpt
    assert "inclus" in room_cpt
    assert "exclus" in room_cpt
    assert "ecarts" in room_cpt
    assert room_cpt["inclus"] + room_cpt["exclus"] == room_cpt["total"]


async def test_diagnostics_4d_technical_fields_preserved(aiohttp_client):
    """Task 6.3 — Non-régression : champs techniques conservés après ajout du contrat 4D."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-27T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={4300: JeedomEqLogic(id=4300, name="Eq Exclu Tech", object_id=1, is_excluded=True)},
    )
    app["topology"] = snapshot
    app["eligibility"] = {4300: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 4300)

    # Couche technique intacte (backward compat)
    assert "status_code" in eq
    assert "reason_code" in eq
    assert "detail" in eq
    assert "remediation" in eq
    assert "v1_limitation" in eq
    assert "matched_commands" in eq
    assert "unmatched_commands" in eq
    assert eq["status_code"] == "excluded"
    assert eq["reason_code"] == "excluded_eqlogic"


async def test_diagnostics_4d_direction2_exclu_still_active(aiohttp_client):
    """Task 6.4 — Direction 2 : équipement exclu encore présent dans HA (active_or_alive=True).

    Fix terrain 2026-03-27 : le vrai signal de présence HA est publications[eq_id].active_or_alive,
    PAS has_pending_home_assistant_changes (XOR ambigü).
    """
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-27T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Entrée")},
        eq_logics={4400: JeedomEqLogic(id=4400, name="Lampe Entrée Exclue", object_id=1, is_excluded=True)},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=4400,
        ha_unique_id="light_4400",
        ha_name="Lampe Entrée Exclue",
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {4400: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")}
    # L'équipement est exclu mais sa publication est encore active dans HA
    app["publications"] = {
        4400: PublicationDecision(
            should_publish=False,
            reason="excluded_eqlogic",
            mapping_result=mapping_res,
            active_or_alive=True,
        )
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 4400)

    # Direction 2 : exclu mais encore présent dans HA
    assert eq["perimetre"] == "exclu_sur_equipement"
    assert eq["statut"] == "publie"
    assert eq["ecart"] is True
    assert eq["cause_code"] == "pending_unpublish"
    assert eq["cause_label"] == "Changement en attente d'application"
    assert eq["cause_action"] == "Republier pour appliquer le changement"

    # Couche technique inchangée
    assert eq["status_code"] == "excluded"
    assert eq["reason_code"] == "excluded_eqlogic"


async def test_diagnostics_4d_direction2_pending_unpublish(aiohttp_client):
    """Direction 2 variante : équipement exclu avec deferred discovery unpublish.

    Quand l'unpublish échoue et est reporté dans pending_discovery_unpublish,
    l'équipement est encore retained dans HA → statut=publie, ecart=true.
    """
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-27T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Entrée")},
        eq_logics={4401: JeedomEqLogic(id=4401, name="Prise Exclue Deferred", object_id=1, is_excluded=True)},
    )
    app["topology"] = snapshot
    app["eligibility"] = {4401: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")}
    # Pas de publication active, mais un unpublish deferred → encore dans HA
    app["pending_discovery_unpublish"] = {4401: "switch"}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 4401)

    assert eq["perimetre"] == "exclu_sur_equipement"
    assert eq["statut"] == "publie"
    assert eq["ecart"] is True
    assert eq["cause_code"] == "pending_unpublish"


async def test_diagnostics_4d_inclus_non_publie_has_pending_not_publie(aiohttp_client):
    """Garde-fou terrain : un équipement inclus non publié avec has_pending=True
    doit avoir statut='non_publie', PAS 'publie'.

    C'est exactement le bug terrain 2026-03-27 (69 faux positifs).
    has_pending=True signifie 'desired!=actual', pas 'présent dans HA'.
    """
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-27T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={4500: JeedomEqLogic(id=4500, name="Capteur Ambigu", object_id=1, is_enable=True)},
    )
    mapping_res = MappingResult(
        ha_entity_type="light",
        confidence="ambiguous",
        reason_code="ambiguous",
        jeedom_eq_id=4500,
        ha_unique_id="light_4500",
        ha_name="Capteur Ambigu",
        capabilities=LightCapabilities(has_on_off=True),
    )
    app["topology"] = snapshot
    app["eligibility"] = {4500: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {4500: mapping_res}
    # Publication non active (ambiguous → skipped)
    app["publications"] = {
        4500: PublicationDecision(
            should_publish=False,
            reason="ambiguous_skipped",
            mapping_result=mapping_res,
            active_or_alive=False,
        )
    }
    # Même si published_scope dit has_pending=True (le XOR), statut doit être non_publie
    app["published_scope"] = {
        "equipements": [{"eq_id": 4500, "has_pending_home_assistant_changes": True}]
    }

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 4500)

    # GARDE-FOU : statut=non_publie malgré has_pending=True
    assert eq["perimetre"] == "inclus"
    assert eq["statut"] == "non_publie", (
        "Bug terrain 2026-03-27 : un inclus non publié avec has_pending=True "
        "ne doit PAS avoir statut='publie'. has_pending est un XOR, pas un indicateur de présence HA."
    )
    assert eq["ecart"] is True
    assert eq["cause_code"] == "ambiguous_skipped"


async def test_diagnostics_4d_exclu_aligne_not_in_ha(aiohttp_client):
    """Cas 3 aligné : exclu + pas dans HA → statut=non_publie, ecart=false."""
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    snapshot = TopologySnapshot(
        timestamp="2026-03-27T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={4600: JeedomEqLogic(id=4600, name="Thermostat Exclu", object_id=1, is_excluded=True)},
    )
    app["topology"] = snapshot
    app["eligibility"] = {4600: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")}
    # Pas de publication, pas de pending_discovery_unpublish

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    data = await resp.json()
    eq = next(e for e in data["payload"]["equipments"] if e["eq_id"] == 4600)

    assert eq["perimetre"] == "exclu_sur_equipement"
    assert eq["statut"] == "non_publie"
    assert eq["ecart"] is False
    assert eq["cause_code"] is None
