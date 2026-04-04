# ARTEFACT — Story 5.1 : tests d'intégration backend.
"""Tests d'intégration — signal actions_ha dans le contrat API, gating pont, matrice complète."""

import pytest

from transport.http_server import create_app
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd, EligibilityResult
)
from models.mapping import MappingResult, PublicationDecision, LightCapabilities


SECRET = "test-secret-integration-5.1"


def _make_snapshot(eq_logics, objects=None):
    if objects is None:
        objects = {1: JeedomObject(id=1, name="Salon")}
    return TopologySnapshot(
        timestamp="2026-04-04T00:00:00Z",
        objects=objects,
        eq_logics=eq_logics,
    )


def _light_mapping(eq_id, reason_code="sure", confidence="sure"):
    return MappingResult(
        ha_entity_type="light",
        confidence=confidence,
        reason_code=reason_code,
        jeedom_eq_id=eq_id,
        ha_unique_id=f"light_{eq_id}",
        ha_name=f"Lumiere {eq_id}",
        capabilities=LightCapabilities(has_on_off=True),
    )


def _published_decision(mapping_res, active=True):
    return PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=mapping_res,
        active_or_alive=active,
    )


def _unpublished_decision(mapping_res):
    return PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=mapping_res,
        active_or_alive=False,
    )


def _set_bridge_connected(app, connected=True):
    """Helper — force l'état du bridge pour le test."""
    app["mqtt_bridge"]._state = "connected" if connected else "disconnected"


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


# ---------------------------------------------------------------------------
# AC 2 — Signal actions_ha présent dans le contrat API par équipement
# ---------------------------------------------------------------------------

async def test_actions_ha_present_pour_equipement_inclus(cli, app):
    """Le signal actions_ha est présent pour les équipements inclus."""
    eq = JeedomEqLogic(id=42, name="Lumière Salon", object_id=1, is_enable=True)
    m42 = _light_mapping(42)
    app["topology"] = _make_snapshot({42: eq})
    app["eligibility"] = {42: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {42: m42}
    app["publications"] = {42: _published_decision(m42)}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": SECRET})
    assert resp.status == 200
    body = await resp.json()
    equips = body["payload"]["equipments"]
    assert len(equips) == 1
    eq_dict = equips[0]
    assert "actions_ha" in eq_dict
    actions = eq_dict["actions_ha"]
    assert actions is not None
    assert "publier" in actions
    assert "supprimer" in actions
    # Shape complète
    for key in ("publier", "supprimer"):
        assert set(actions[key].keys()) == {"label", "disponible", "raison_indisponibilite", "niveau_confirmation"}


async def test_actions_ha_null_pour_equipement_exclu(cli, app):
    """Le signal actions_ha est null pour les équipements exclus."""
    eq = JeedomEqLogic(id=50, name="Exclu", object_id=1, is_enable=True, is_excluded=True)
    app["topology"] = _make_snapshot({50: eq})
    app["eligibility"] = {50: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")}
    app["mappings"] = {}
    app["publications"] = {}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": SECRET})
    body = await resp.json()
    eq_dict = body["payload"]["equipments"][0]
    assert eq_dict["actions_ha"] is None


# ---------------------------------------------------------------------------
# AC 3 — Label contextuel correct dans le contrat API
# ---------------------------------------------------------------------------

async def test_label_creer_pour_non_publie(cli, app):
    """est_publie_ha=False → label 'Créer dans Home Assistant'."""
    eq = JeedomEqLogic(id=60, name="Non publiée", object_id=1, is_enable=True)
    m60 = _light_mapping(60)
    app["topology"] = _make_snapshot({60: eq})
    app["eligibility"] = {60: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {60: m60}
    app["publications"] = {60: _unpublished_decision(m60)}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": SECRET})
    body = await resp.json()
    actions = body["payload"]["equipments"][0]["actions_ha"]
    assert actions["publier"]["label"] == "Créer dans Home Assistant"


async def test_label_republier_pour_publie(cli, app):
    """est_publie_ha=True → label 'Republier dans Home Assistant'."""
    eq = JeedomEqLogic(id=61, name="Publiée", object_id=1, is_enable=True)
    m61 = _light_mapping(61)
    app["topology"] = _make_snapshot({61: eq})
    app["eligibility"] = {61: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {61: m61}
    app["publications"] = {61: _published_decision(m61)}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": SECRET})
    body = await resp.json()
    actions = body["payload"]["equipments"][0]["actions_ha"]
    assert actions["publier"]["label"] == "Republier dans Home Assistant"


# ---------------------------------------------------------------------------
# AC 4 — Matrice de disponibilité complète dans le contrat API
# ---------------------------------------------------------------------------

async def test_matrice_non_publie_inclus(cli, app):
    """Non publié + inclus → publier actif, supprimer grisé."""
    eq = JeedomEqLogic(id=70, name="Non pub", object_id=1, is_enable=True)
    m70 = _light_mapping(70)
    app["topology"] = _make_snapshot({70: eq})
    app["eligibility"] = {70: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {70: m70}
    app["publications"] = {70: _unpublished_decision(m70)}
    _set_bridge_connected(app)

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": SECRET})
    body = await resp.json()
    actions = body["payload"]["equipments"][0]["actions_ha"]
    assert actions["publier"]["disponible"] is True
    assert actions["supprimer"]["disponible"] is False
    assert actions["supprimer"]["raison_indisponibilite"] is not None


async def test_matrice_publie_inclus(cli, app):
    """Publié + inclus → publier actif, supprimer actif."""
    eq = JeedomEqLogic(id=71, name="Publiée", object_id=1, is_enable=True)
    m71 = _light_mapping(71)
    app["topology"] = _make_snapshot({71: eq})
    app["eligibility"] = {71: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {71: m71}
    app["publications"] = {71: _published_decision(m71)}
    _set_bridge_connected(app)

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": SECRET})
    body = await resp.json()
    actions = body["payload"]["equipments"][0]["actions_ha"]
    assert actions["publier"]["disponible"] is True
    assert actions["supprimer"]["disponible"] is True
    assert actions["supprimer"]["raison_indisponibilite"] is None


# ---------------------------------------------------------------------------
# AC 5 — Gating par état du pont (bridge indisponible → tout grisé)
# ---------------------------------------------------------------------------

async def test_bridge_indisponible_grise_tout(cli, app):
    """Bridge déconnecté → toutes actions grisées avec raison."""
    eq = JeedomEqLogic(id=80, name="Bridge off", object_id=1, is_enable=True)
    m80 = _light_mapping(80)
    app["topology"] = _make_snapshot({80: eq})
    app["eligibility"] = {80: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {80: m80}
    app["publications"] = {80: _published_decision(m80)}
    # Le bridge par défaut dans create_app est un MqttBridge() non connecté
    # (is_connected = False par défaut)

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": SECRET})
    body = await resp.json()
    actions = body["payload"]["equipments"][0]["actions_ha"]
    # Bridge MqttBridge() par défaut n'est pas connecté
    assert actions["publier"]["disponible"] is False
    assert actions["supprimer"]["disponible"] is False
    assert actions["publier"]["raison_indisponibilite"] is not None
    assert actions["supprimer"]["raison_indisponibilite"] is not None


# ---------------------------------------------------------------------------
# AC 7 — Cohérence actions_ha ↔ 4D
# ---------------------------------------------------------------------------

async def test_coherence_4d_non_publie(cli, app):
    """statut=non_publie implique label Créer et supprimer grisé."""
    eq = JeedomEqLogic(id=90, name="Cohérence", object_id=1, is_enable=True)
    m90 = _light_mapping(90)
    app["topology"] = _make_snapshot({90: eq})
    app["eligibility"] = {90: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {90: m90}
    app["publications"] = {90: _unpublished_decision(m90)}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": SECRET})
    body = await resp.json()
    eq_dict = body["payload"]["equipments"][0]
    assert eq_dict["statut"] == "non_publie"
    assert "Créer" in eq_dict["actions_ha"]["publier"]["label"]


async def test_coherence_4d_publie(cli, app):
    """statut=publie implique label Republier et supprimer actif."""
    eq = JeedomEqLogic(id=91, name="Cohérence pub", object_id=1, is_enable=True)
    m91 = _light_mapping(91)
    app["topology"] = _make_snapshot({91: eq})
    app["eligibility"] = {91: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {91: m91}
    app["publications"] = {91: _published_decision(m91)}
    _set_bridge_connected(app)

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": SECRET})
    body = await resp.json()
    eq_dict = body["payload"]["equipments"][0]
    assert eq_dict["statut"] == "publie"
    assert "Republier" in eq_dict["actions_ha"]["publier"]["label"]
    assert eq_dict["actions_ha"]["supprimer"]["disponible"] is True


# ---------------------------------------------------------------------------
# AC 8 — Contrat 4D existant non modifié par l'ajout de actions_ha
# ---------------------------------------------------------------------------

async def test_4d_intact_apres_ajout_actions_ha(cli, app):
    """Les champs 4D sont intacts et non modifiés par le signal actions_ha."""
    eq = JeedomEqLogic(id=100, name="4D intact", object_id=1, is_enable=True)
    m100 = _light_mapping(100)
    app["topology"] = _make_snapshot({100: eq})
    app["eligibility"] = {100: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {100: m100}
    app["publications"] = {100: _published_decision(m100)}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": SECRET})
    body = await resp.json()
    eq_dict = body["payload"]["equipments"][0]
    # Champs 4D toujours présents et corrects
    assert "perimetre" in eq_dict
    assert "statut" in eq_dict
    assert "ecart" in eq_dict
    assert "cause_code" in eq_dict
    assert "cause_label" in eq_dict
    assert "cause_action" in eq_dict
    assert "ha_type" in eq_dict
    # Champs techniques toujours présents
    assert "status" in eq_dict
    assert "status_code" in eq_dict
    assert "confidence" in eq_dict
    assert "reason_code" in eq_dict
    # actions_ha n'a pas écrasé ou remplacé les champs 4D
    assert eq_dict["perimetre"] == "inclus"
    assert eq_dict["statut"] == "publie"


async def test_inherit_absent_des_reponses(cli, app):
    """'inherit' n'apparaît toujours pas dans les réponses API."""
    eq = JeedomEqLogic(id=101, name="Non-reg check", object_id=1, is_enable=True)
    m101 = _light_mapping(101)
    app["topology"] = _make_snapshot({101: eq})
    app["eligibility"] = {101: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {101: m101}
    app["publications"] = {101: _published_decision(m101)}

    resp = await cli.get("/system/diagnostics", headers={"X-Local-Secret": SECRET})
    body = await resp.json()
    import json
    raw = json.dumps(body)
    assert "inherit" not in raw.lower()
