"""Story 6.1 — pipeline_step_visible dans le diagnostic endpoint.

Couvre les 6 cas canoniques + invariant I7 :
- step 1 : inéligibilité
- step 2 : éligible mais pas de mapping
- step 3 : projection HA invalide
- step 4 : décision de publication bloquée
- step 5 success : publication MQTT réussie
- step 5 failed : publication MQTT échouée — deux blocs séparés
- I7 : technical_reason_code ne devient jamais la cause canonique principale
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
    JeedomCmd,
    JeedomEqLogic,
    JeedomObject,
    TopologySnapshot,
)


SECRET = "test-secret-6-1"
HEADERS = {"X-Local-Secret": SECRET}


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _topology(*eq_logics):
    eq_dict = {eq.id: eq for eq in eq_logics}
    return TopologySnapshot(
        timestamp="2026-04-21T10:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics=eq_dict,
    )


def _eq(eq_id: int, **kwargs) -> JeedomEqLogic:
    return JeedomEqLogic(id=eq_id, name=f"Eq{eq_id}", object_id=1, is_enable=True, **kwargs)


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


async def _get_eq(cli, app, eq_id: int, *, eligibility, mappings=None, publications=None):
    app["topology"] = _topology(_eq(eq_id))
    app["eligibility"] = eligibility
    app["mappings"] = mappings or {}
    app["publications"] = publications or {}
    resp = await cli.get("/system/diagnostics", headers=HEADERS)
    assert resp.status == 200
    data = await resp.json()
    equipments = data["payload"]["equipments"]
    return next(e for e in equipments if e["eq_id"] == eq_id)


# ---------------------------------------------------------------------------
# Step 1 — Inéligibilité
# ---------------------------------------------------------------------------

async def test_pipeline_step_1_excluded(cli, app):
    eq = await _get_eq(
        cli, app, 10,
        eligibility={10: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")},
    )
    assert eq["pipeline_step_visible"] == 1


async def test_pipeline_step_1_disabled(cli, app):
    eq = await _get_eq(
        cli, app, 11,
        eligibility={11: EligibilityResult(is_eligible=False, reason_code="disabled_eqlogic")},
    )
    assert eq["pipeline_step_visible"] == 1


# ---------------------------------------------------------------------------
# Step 2 — Éligible mais pas de mapping
# ---------------------------------------------------------------------------

async def test_pipeline_step_2_no_mapping(cli, app):
    eq = await _get_eq(
        cli, app, 20,
        eligibility={20: EligibilityResult(is_eligible=True, reason_code="eligible")},
        # no entry in mappings → step 2
    )
    assert eq["pipeline_step_visible"] == 2


# ---------------------------------------------------------------------------
# Step 3 — Projection HA invalide
# ---------------------------------------------------------------------------

async def test_pipeline_step_3_projection_invalid(cli, app):
    mapping = _light_mapping(30)
    mapping.projection_validity = ProjectionValidity(
        is_valid=False,
        reason_code="missing_required_field",
        missing_fields=["state_topic"],
        missing_capabilities=[],
    )
    invalid_decision = PublicationDecision(
        should_publish=False,
        reason="missing_required_field",
        mapping_result=mapping,
        active_or_alive=False,
    )
    mapping.publication_decision_ref = invalid_decision

    eq = await _get_eq(
        cli, app, 30,
        eligibility={30: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={30: mapping},
        publications={30: invalid_decision},
    )
    assert eq["pipeline_step_visible"] == 3


# ---------------------------------------------------------------------------
# Step 4 — Décision de publication bloquée
# ---------------------------------------------------------------------------

async def test_pipeline_step_4_ambiguous_skipped(cli, app):
    mapping = _light_mapping(40)
    mapping.confidence = "ambiguous"
    pv = ProjectionValidity(is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[])
    mapping.projection_validity = pv
    blocked_decision = PublicationDecision(
        should_publish=False,
        reason="ambiguous_skipped",
        mapping_result=mapping,
        active_or_alive=False,
    )
    mapping.publication_decision_ref = blocked_decision

    eq = await _get_eq(
        cli, app, 40,
        eligibility={40: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={40: mapping},
        publications={40: blocked_decision},
    )
    assert eq["pipeline_step_visible"] == 4


async def test_pipeline_step_4_out_of_product_scope(cli, app):
    mapping = _light_mapping(41)
    pv = ProjectionValidity(is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[])
    mapping.projection_validity = pv
    blocked_decision = PublicationDecision(
        should_publish=False,
        reason="ha_component_not_in_product_scope",
        mapping_result=mapping,
        active_or_alive=False,
    )
    mapping.publication_decision_ref = blocked_decision

    eq = await _get_eq(
        cli, app, 41,
        eligibility={41: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={41: mapping},
        publications={41: blocked_decision},
    )
    assert eq["pipeline_step_visible"] == 4


# ---------------------------------------------------------------------------
# Step 5 — Publication tentée (success)
# ---------------------------------------------------------------------------

async def test_pipeline_step_5_success(cli, app):
    mapping = _light_mapping(50)
    pv = ProjectionValidity(is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[])
    mapping.projection_validity = pv
    pub_decision = PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=mapping,
        active_or_alive=True,
    )
    mapping.publication_decision_ref = pub_decision
    mapping.publication_result = PublicationResult(status="success")

    eq = await _get_eq(
        cli, app, 50,
        eligibility={50: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={50: mapping},
        publications={50: pub_decision},
    )
    assert eq["pipeline_step_visible"] == 5


# ---------------------------------------------------------------------------
# Step 5 — Publication tentée (failed) — deux blocs séparés
# ---------------------------------------------------------------------------

async def test_pipeline_step_5_failed(cli, app):
    mapping = _light_mapping(60)
    pv = ProjectionValidity(is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[])
    mapping.projection_validity = pv
    pub_decision = PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=mapping,
        active_or_alive=False,
    )
    mapping.publication_decision_ref = pub_decision
    mapping.publication_result = PublicationResult(
        status="failed",
        technical_reason_code="discovery_publish_failed",
    )

    eq = await _get_eq(
        cli, app, 60,
        eligibility={60: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={60: mapping},
        publications={60: pub_decision},
    )
    assert eq["pipeline_step_visible"] == 5

    tr = eq["traceability"]
    # Bloc Décision pipeline : cause canonique = décision positive
    assert tr["decision_trace"]["reason_code"] == "published"

    # Bloc Résultat technique : échec technique visible mais séparé
    assert tr["publication_trace"]["last_discovery_publish_result"] == "failed"
    assert tr["publication_trace"]["technical_reason_code"] == "discovery_publish_failed"


# ---------------------------------------------------------------------------
# Invariant I7 — technical_reason_code ne devient jamais la cause canonique
# ---------------------------------------------------------------------------

async def test_i7_technical_reason_never_canonical_cause(cli, app):
    """I7 : traceability.decision_trace.reason_code ne peut pas être
    un technical_reason_code d'étape 5 (ex: discovery_publish_failed).
    La cause canonique reste alimentée par publication_decision_ref.reason.
    """
    mapping = _light_mapping(70)
    pv = ProjectionValidity(is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[])
    mapping.projection_validity = pv
    pub_decision = PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=mapping,
        active_or_alive=False,
    )
    mapping.publication_decision_ref = pub_decision
    mapping.publication_result = PublicationResult(
        status="failed",
        technical_reason_code="discovery_publish_failed",
    )

    eq = await _get_eq(
        cli, app, 70,
        eligibility={70: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={70: mapping},
        publications={70: pub_decision},
    )

    # I7 strict : la cause canonique dans decision_trace ne doit jamais valoir
    # un technical_reason_code de l'étape 5.
    canonical = eq["traceability"]["decision_trace"]["reason_code"]
    assert canonical != "discovery_publish_failed", (
        f"I7 violé : decision_trace.reason_code = '{canonical}' "
        "contient un technical_reason_code de l'étape 5"
    )
    assert canonical != "local_availability_publish_failed", (
        f"I7 violé : decision_trace.reason_code = '{canonical}' "
        "contient un technical_reason_code de l'étape 5"
    )
    # Assertion positive : quand la décision canonique est "sure" et la publication a été tentée,
    # decision_trace.reason_code doit valoir exactement "published" (mapping figé _CLOSED_REASON_MAP).
    # Sans ce garde-fou, un futur technical_reason_code inconnu (ex: "mqtt_retained_failed") passerait
    # à travers la liste noire au-dessus.
    assert canonical == "published", (
        f"I7 : decision_trace.reason_code attendu = 'published' "
        f"pour un cas step 5 failed avec décision canonique 'sure', obtenu = '{canonical}'"
    )

    # Le champ pipeline_step_visible doit être 5 (publication tentée)
    assert eq["pipeline_step_visible"] == 5


# ---------------------------------------------------------------------------
# Non-régression — contrat historique préservé
# ---------------------------------------------------------------------------

async def test_historical_contract_preserved_on_published_eq(cli, app):
    """AC5 — Les champs historiques ne doivent pas disparaître."""
    mapping = _light_mapping(80)
    pv = ProjectionValidity(is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[])
    mapping.projection_validity = pv
    pub_decision = PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=mapping,
        active_or_alive=True,
    )
    mapping.publication_decision_ref = pub_decision
    mapping.publication_result = PublicationResult(status="success")

    eq = await _get_eq(
        cli, app, 80,
        eligibility={80: EligibilityResult(is_eligible=True, reason_code="eligible")},
        mappings={80: mapping},
        publications={80: pub_decision},
    )

    # Champs historiques obligatoirement présents
    for field in ("reason_code", "status", "confidence", "detail", "remediation",
                  "traceability", "perimetre", "statut", "ecart"):
        assert field in eq, f"Champ historique manquant : {field}"

    # Champ 6.1
    assert "pipeline_step_visible" in eq

    # Story 7.1 — projection_validity présent dans traceability (ajout additif pur)
    assert "projection_validity" in eq["traceability"], (
        "Story 7.1 : sous-bloc projection_validity absent de traceability"
    )
    pv = eq["traceability"]["projection_validity"]
    for key in ("is_valid", "reason_code", "missing_fields", "missing_capabilities"):
        assert key in pv, f"Story 7.1 : clé '{key}' absente du sous-bloc projection_validity"
