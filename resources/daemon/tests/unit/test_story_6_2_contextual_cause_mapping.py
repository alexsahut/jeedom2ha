"""Story 6.2 — contextualisation UX des causes (backend-first).

Objectifs couverts :
- mapping pur reason_code + pipeline_step -> cause_label / cause_action
- différenciation explicite step 3 vs step 4 pour une même cause canonique
- fallback explicite (jamais None)
- invariants pipeline (I4 cause unique, I7 séparation décision/technique)
"""

from __future__ import annotations

import pytest

from models.cause_mapping import reason_code_to_cause, resolve_cause_ux
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
from transport.http_server import create_app


SECRET = "test-secret-6-2"
HEADERS = {"X-Local-Secret": SECRET}


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _eq(eq_id: int) -> JeedomEqLogic:
    return JeedomEqLogic(id=eq_id, name=f"Eq{eq_id}", object_id=1, is_enable=True)


def _topology(eq_id: int) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-04-21T10:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={eq_id: _eq(eq_id)},
    )


def _light_mapping(eq_id: int) -> MappingResult:
    return MappingResult(
        ha_entity_type="light",
        confidence="ambiguous",
        reason_code="ambiguous",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Eq{eq_id}",
        capabilities=LightCapabilities(has_on_off=True),
    )


async def _get_eq(cli, app, eq_id: int, *, eligibility, mapping, decision):
    app["topology"] = _topology(eq_id)
    app["eligibility"] = {eq_id: eligibility}
    app["mappings"] = {eq_id: mapping}
    app["publications"] = {eq_id: decision}
    resp = await cli.get("/system/diagnostics", headers=HEADERS)
    assert resp.status == 200
    data = await resp.json()
    return next(e for e in data["payload"]["equipments"] if e["eq_id"] == eq_id)


def test_resolve_cause_ux_ambiguous_step_3():
    resolved = resolve_cause_ux("ambiguous_skipped", 3)
    # Story 6.3 — libellé exprimant le problème structurel de projection
    assert "Projection HA" in resolved["cause_label"]
    assert resolved["cause_action"] is not None  # action réelle possible dans Jeedom


def test_resolve_cause_ux_ambiguous_step_4():
    # Story 6.3 — faux CTA éliminé : cause_action = None pour step 4
    resolved = resolve_cause_ux("ambiguous_skipped", 4)
    assert resolved["cause_action"] is None
    assert "Choisir manuellement" not in (resolved.get("cause_action") or "")
    assert resolved["cause_label"]  # libellé non vide


def test_resolve_cause_ux_explicit_fallback_never_none():
    resolved = resolve_cause_ux("__unknown_reason__", 99)
    assert isinstance(resolved["cause_label"], str) and resolved["cause_label"]
    assert isinstance(resolved["cause_action"], str) and resolved["cause_action"]


def test_non_regression_reason_code_mapping_unchanged():
    assert reason_code_to_cause("ambiguous_skipped") == (
        "ambiguous_skipped",
        "Mapping ambigu — plusieurs types possibles",
        "Préciser les types génériques sur les commandes pour lever l'ambiguïté",
    )


async def test_step_3_and_step_4_same_reason_code_different_ux(cli, app):
    # Step 3: projection invalide + reason canonique identique (ambiguous_skipped)
    mapping_step3 = _light_mapping(6301)
    mapping_step3.projection_validity = ProjectionValidity(
        is_valid=False,
        reason_code="ha_missing_required_option",
        missing_fields=["state_topic"],
        missing_capabilities=[],
    )
    decision_step3 = PublicationDecision(
        should_publish=False,
        reason="ambiguous_skipped",
        mapping_result=mapping_step3,
        active_or_alive=False,
    )
    mapping_step3.publication_decision_ref = decision_step3

    eq_step3 = await _get_eq(
        cli,
        app,
        6301,
        eligibility=EligibilityResult(is_eligible=True, reason_code="eligible"),
        mapping=mapping_step3,
        decision=decision_step3,
    )
    assert eq_step3["pipeline_step_visible"] == 3
    assert eq_step3["traceability"]["decision_trace"]["reason_code"] == "ambiguous_skipped"
    # Story 6.3 — libellé structural de projection
    assert "Projection HA" in eq_step3["cause_label"]
    assert eq_step3["cause_action"] is not None  # action réelle dans Jeedom

    # Step 4: projection valide + même reason canonique (ambiguous_skipped)
    mapping_step4 = _light_mapping(6302)
    mapping_step4.projection_validity = ProjectionValidity(
        is_valid=True,
        reason_code=None,
        missing_fields=[],
        missing_capabilities=[],
    )
    decision_step4 = PublicationDecision(
        should_publish=False,
        reason="ambiguous_skipped",
        mapping_result=mapping_step4,
        active_or_alive=False,
    )
    mapping_step4.publication_decision_ref = decision_step4

    eq_step4 = await _get_eq(
        cli,
        app,
        6302,
        eligibility=EligibilityResult(is_eligible=True, reason_code="eligible"),
        mapping=mapping_step4,
        decision=decision_step4,
    )
    assert eq_step4["pipeline_step_visible"] == 4
    assert eq_step4["traceability"]["decision_trace"]["reason_code"] == "ambiguous_skipped"
    # Story 6.3 — faux CTA éliminé : cause_action = None pour step 4
    assert eq_step4["cause_action"] is None
    assert "Choisir manuellement" not in (eq_step4.get("cause_action") or "")
    assert eq_step4["cause_label"] != eq_step3["cause_label"]  # AC5 — libellés distincts

    # I4 — cause unique : un seul cause_label, pas de multi-cause.
    assert isinstance(eq_step4["cause_label"], str)
    assert "causes" not in eq_step4


async def test_endpoint_fallback_when_decision_reason_not_mapped(cli, app):
    mapping = _light_mapping(6303)
    mapping.projection_validity = ProjectionValidity(
        is_valid=True,
        reason_code=None,
        missing_fields=[],
        missing_capabilities=[],
    )
    decision = PublicationDecision(
        should_publish=False,
        reason="__unknown_reason__",
        mapping_result=mapping,
        active_or_alive=False,
    )
    mapping.publication_decision_ref = decision

    eq = await _get_eq(
        cli,
        app,
        6303,
        eligibility=EligibilityResult(is_eligible=True, reason_code="eligible"),
        mapping=mapping,
        decision=decision,
    )
    assert eq["pipeline_step_visible"] == 4
    assert isinstance(eq["cause_label"], str) and eq["cause_label"]
    assert isinstance(eq["cause_action"], str) and eq["cause_action"]


async def test_i7_separation_decision_and_technical_still_respected(cli, app):
    mapping = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=6304,
        ha_unique_id="jeedom2ha_eq_6304",
        ha_name="Eq6304",
        capabilities=LightCapabilities(has_on_off=True),
    )
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
        active_or_alive=False,
    )
    mapping.publication_decision_ref = decision
    mapping.publication_result = PublicationResult(
        status="failed",
        technical_reason_code="discovery_publish_failed",
    )

    eq = await _get_eq(
        cli,
        app,
        6304,
        eligibility=EligibilityResult(is_eligible=True, reason_code="eligible"),
        mapping=mapping,
        decision=decision,
    )

    assert eq["pipeline_step_visible"] == 5
    dt = eq["traceability"]["decision_trace"]
    assert dt["reason_code"] == "published"
    assert dt["reason_code"] != "discovery_publish_failed"
    pt = eq["traceability"]["publication_trace"]
    assert pt["technical_reason_code"] == "discovery_publish_failed"
