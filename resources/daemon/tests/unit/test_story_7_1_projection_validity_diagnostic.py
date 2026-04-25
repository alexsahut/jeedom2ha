"""Story 7.1 — projection_validity dans le contrat diagnostic.

Couvre les cas canoniques définis par les AC de la story 7.1 :
- AC2/AC3 : cas nominal (is_valid=True)
- AC2/AC3 : cas invalide (is_valid=False)
- AC2/AC3 : cas skipped explicite (map_result sans projection_validity)
- AC2/AC3 : cas skipped sur inéligible (no map_result)
- AC6     : non-régression — champs historiques préservés
- AC7     : story non-ouvrante — PRODUCT_SCOPE et cause_action intacts
- AC8     : cohérence projection_validity.is_valid=False → should_publish=False
"""

from __future__ import annotations

import pytest

from transport.http_server import create_app
from models.mapping import (
    LightCapabilities,
    MappingResult,
    ProjectionValidity,
    PublicationDecision,
    PublicationResult,
)
from models.topology import (
    EligibilityResult,
    JeedomEqLogic,
    JeedomObject,
    TopologySnapshot,
)


SECRET = "test-secret-7-1"
HEADERS = {"X-Local-Secret": SECRET}


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _topology(eq_id: int):
    eq = JeedomEqLogic(id=eq_id, name=f"Eq{eq_id}", object_id=1, is_enable=True)
    return (
        TopologySnapshot(
            timestamp="2026-04-25T10:00:00Z",
            objects={1: JeedomObject(id=1, name="Salon")},
            eq_logics={eq_id: eq},
        ),
        eq,
    )


def _light_mapping(eq_id: int) -> MappingResult:
    return MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Eq{eq_id}",
        capabilities=LightCapabilities(has_on_off=True),
    )


async def _fetch_eq(cli, app, eq_id: int, *, eligibility, mappings=None, publications=None):
    topo, _ = _topology(eq_id)
    app["topology"] = topo
    app["eligibility"] = eligibility
    app["mappings"] = mappings or {}
    app["publications"] = publications or {}
    resp = await cli.get("/system/diagnostics", headers=HEADERS)
    assert resp.status == 200
    data = await resp.json()
    eqs = data["payload"]["equipments"]
    return next(e for e in eqs if e["eq_id"] == eq_id)


# ---------------------------------------------------------------------------
# AC2/AC3 — Cas nominal (étape 3 exécutée, is_valid=True)
# ---------------------------------------------------------------------------

async def test_projection_validity_nominal_present(cli, app):
    """Cas nominal : projection_validity dans traceability avec is_valid=True."""
    mapping = _light_mapping(10)
    pv = ProjectionValidity(is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[])
    mapping.projection_validity = pv
    pub = PublicationDecision(should_publish=True, reason="sure", mapping_result=mapping, active_or_alive=True)
    mapping.publication_decision_ref = pub
    mapping.publication_result = PublicationResult(status="success")

    eq = await _fetch_eq(
        cli, app, 10,
        eligibility={10: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={10: mapping},
        publications={10: pub},
    )

    pv_bloc = eq["traceability"]["projection_validity"]
    assert pv_bloc["is_valid"] is True
    assert pv_bloc["reason_code"] is None
    assert pv_bloc["missing_fields"] == []
    assert pv_bloc["missing_capabilities"] == []


async def test_projection_validity_nominal_schema_keys(cli, app):
    """Cas nominal : les 4 clés canoniques sont présentes dans le sous-bloc."""
    mapping = _light_mapping(11)
    pv = ProjectionValidity(is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[])
    mapping.projection_validity = pv
    pub = PublicationDecision(should_publish=True, reason="sure", mapping_result=mapping, active_or_alive=True)
    mapping.publication_decision_ref = pub

    eq = await _fetch_eq(
        cli, app, 11,
        eligibility={11: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={11: mapping},
        publications={11: pub},
    )

    pv_bloc = eq["traceability"]["projection_validity"]
    for key in ("is_valid", "reason_code", "missing_fields", "missing_capabilities"):
        assert key in pv_bloc, f"Clé absente du sous-bloc projection_validity : {key}"


# ---------------------------------------------------------------------------
# AC2/AC3 — Cas invalide (is_valid=False, champs d'échec renseignés)
# ---------------------------------------------------------------------------

async def test_projection_validity_invalid_exposed(cli, app):
    """Cas invalide : is_valid=False avec champs d'échec structurel exposés."""
    mapping = _light_mapping(20)
    pv = ProjectionValidity(
        is_valid=False,
        reason_code="ha_missing_state_topic",
        missing_fields=["state_topic"],
        missing_capabilities=["has_on_off"],
    )
    mapping.projection_validity = pv
    blocked = PublicationDecision(
        should_publish=False,
        reason="ha_missing_state_topic",
        mapping_result=mapping,
        active_or_alive=False,
    )
    mapping.publication_decision_ref = blocked

    eq = await _fetch_eq(
        cli, app, 20,
        eligibility={20: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={20: mapping},
        publications={20: blocked},
    )

    pv_bloc = eq["traceability"]["projection_validity"]
    assert pv_bloc["is_valid"] is False
    assert pv_bloc["reason_code"] == "ha_missing_state_topic"
    assert "state_topic" in pv_bloc["missing_fields"]
    assert "has_on_off" in pv_bloc["missing_capabilities"]


async def test_projection_validity_pipeline_step_3_when_invalid(cli, app):
    """Cohérence : projection invalide → pipeline_step_visible == 3."""
    mapping = _light_mapping(21)
    pv = ProjectionValidity(
        is_valid=False,
        reason_code="ha_missing_state_topic",
        missing_fields=["state_topic"],
        missing_capabilities=[],
    )
    mapping.projection_validity = pv
    blocked = PublicationDecision(
        should_publish=False,
        reason="ha_missing_state_topic",
        mapping_result=mapping,
        active_or_alive=False,
    )
    mapping.publication_decision_ref = blocked

    eq = await _fetch_eq(
        cli, app, 21,
        eligibility={21: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={21: mapping},
        publications={21: blocked},
    )

    assert eq["pipeline_step_visible"] == 3
    assert eq["traceability"]["projection_validity"]["is_valid"] is False


# ---------------------------------------------------------------------------
# AC2/AC3 — Cas skipped (mapping présent mais projection_validity=None)
# ---------------------------------------------------------------------------

async def test_projection_validity_skipped_when_not_executed(cli, app):
    """Cas skipped : mapping présent mais étape 3 non exécutée → skip explicite."""
    mapping = _light_mapping(30)
    # projection_validity laissé à None — étape 3 non exécutée
    blocked = PublicationDecision(
        should_publish=False,
        reason="ambiguous_skipped",
        mapping_result=mapping,
        active_or_alive=False,
    )
    mapping.publication_decision_ref = blocked

    eq = await _fetch_eq(
        cli, app, 30,
        eligibility={30: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={30: mapping},
        publications={30: blocked},
    )

    pv_bloc = eq["traceability"]["projection_validity"]
    assert pv_bloc["is_valid"] is None, "Skip explicite attendu (is_valid=None)"
    assert pv_bloc["reason_code"] == "skipped_no_mapping_candidate"
    assert pv_bloc["missing_fields"] == []
    assert pv_bloc["missing_capabilities"] == []


# ---------------------------------------------------------------------------
# AC2/AC3 — Cas skipped sur inéligible (pas de map_result)
# ---------------------------------------------------------------------------

async def test_projection_validity_skipped_when_ineligible(cli, app):
    """Cas inéligible : pas de mapping → projection_validity expose un skip additif."""
    eq = await _fetch_eq(
        cli, app, 40,
        eligibility={40: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")},
    )

    pv_bloc = eq["traceability"]["projection_validity"]
    assert pv_bloc["is_valid"] is None
    assert pv_bloc["reason_code"] == "skipped_no_mapping_candidate"
    assert pv_bloc["missing_fields"] == []
    assert pv_bloc["missing_capabilities"] == []


async def test_projection_validity_skipped_when_no_mapping(cli, app):
    """Cas éligible sans mapping (étape 2) → projection_validity skip additif."""
    eq = await _fetch_eq(
        cli, app, 41,
        eligibility={41: EligibilityResult(is_eligible=True, reason_code="eligible")},
        # no mapping entry
    )

    pv_bloc = eq["traceability"]["projection_validity"]
    assert pv_bloc["is_valid"] is None
    assert pv_bloc["reason_code"] == "skipped_no_mapping_candidate"


# ---------------------------------------------------------------------------
# AC6 — Non-régression : champs historiques préservés
# ---------------------------------------------------------------------------

async def test_historical_traceability_keys_preserved(cli, app):
    """AC6 — Les clés historiques de traceability restent inchangées."""
    mapping = _light_mapping(50)
    pv = ProjectionValidity(is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[])
    mapping.projection_validity = pv
    pub = PublicationDecision(should_publish=True, reason="sure", mapping_result=mapping, active_or_alive=True)
    mapping.publication_decision_ref = pub
    mapping.publication_result = PublicationResult(status="success")

    eq = await _fetch_eq(
        cli, app, 50,
        eligibility={50: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={50: mapping},
        publications={50: pub},
    )

    tr = eq["traceability"]
    for key in ("observed_commands", "typing_trace", "decision_trace", "publication_trace"):
        assert key in tr, f"Clé historique de traceability absente : {key}"

    # Le nouveau sous-bloc est bien présent en plus
    assert "projection_validity" in tr


async def test_historical_eq_contract_fields_preserved(cli, app):
    """AC6 — Les champs historiques 4D du contrat équipement restent inchangés."""
    mapping = _light_mapping(51)
    pv = ProjectionValidity(is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[])
    mapping.projection_validity = pv
    pub = PublicationDecision(should_publish=True, reason="sure", mapping_result=mapping, active_or_alive=True)
    mapping.publication_decision_ref = pub

    eq = await _fetch_eq(
        cli, app, 51,
        eligibility={51: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={51: mapping},
        publications={51: pub},
    )

    for field in ("perimetre", "statut", "ecart", "cause_code", "cause_label", "cause_action",
                  "traceability", "pipeline_step_visible"):
        assert field in eq, f"Champ 4D historique absent : {field}"


# ---------------------------------------------------------------------------
# AC7 — Story non-ouvrante : cause_action inchangée
# ---------------------------------------------------------------------------

async def test_no_new_cause_action_introduced(cli, app):
    """AC7 — Aucun nouveau cause_action ne doit apparaître."""
    mapping = _light_mapping(60)
    pv = ProjectionValidity(is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[])
    mapping.projection_validity = pv
    pub = PublicationDecision(should_publish=True, reason="sure", mapping_result=mapping, active_or_alive=True)
    mapping.publication_decision_ref = pub
    mapping.publication_result = PublicationResult(status="success")

    eq = await _fetch_eq(
        cli, app, 60,
        eligibility={60: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={60: mapping},
        publications={60: pub},
    )

    # Équipement publié → pas d'écart → cause_action doit être None
    assert eq["cause_action"] is None
    assert eq["cause_label"] is None


# ---------------------------------------------------------------------------
# AC8 — Cohérence projection_validity ↔ décision
# ---------------------------------------------------------------------------

async def test_ac8_invalid_projection_implies_no_publish(cli, app):
    """AC8 — projection_validity.is_valid=False ne peut jamais coexister avec should_publish=True."""
    mapping = _light_mapping(70)
    pv = ProjectionValidity(
        is_valid=False,
        reason_code="ha_missing_state_topic",
        missing_fields=["state_topic"],
        missing_capabilities=[],
    )
    mapping.projection_validity = pv
    blocked = PublicationDecision(
        should_publish=False,
        reason="ha_missing_state_topic",
        mapping_result=mapping,
        active_or_alive=False,
    )
    mapping.publication_decision_ref = blocked

    eq = await _fetch_eq(
        cli, app, 70,
        eligibility={70: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={70: mapping},
        publications={70: blocked},
    )

    pv_bloc = eq["traceability"]["projection_validity"]
    assert pv_bloc["is_valid"] is False

    # L'équipement ne doit pas être publié
    assert eq["statut"] == "non_publie"


async def test_ac8_valid_projection_can_lead_to_publication(cli, app):
    """AC8 — projection_validity.is_valid=True peut mener à une publication positive."""
    mapping = _light_mapping(71)
    pv = ProjectionValidity(is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[])
    mapping.projection_validity = pv
    pub = PublicationDecision(should_publish=True, reason="sure", mapping_result=mapping, active_or_alive=True)
    mapping.publication_decision_ref = pub
    mapping.publication_result = PublicationResult(status="success")

    eq = await _fetch_eq(
        cli, app, 71,
        eligibility={71: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={71: mapping},
        publications={71: pub},
    )

    pv_bloc = eq["traceability"]["projection_validity"]
    assert pv_bloc["is_valid"] is True
    assert eq["statut"] == "publie"
