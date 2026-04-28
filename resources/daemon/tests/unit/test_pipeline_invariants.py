"""Tests transversaux des invariants du pipeline canonique (Story 4.4).

Objectif:
- valider le contrat (pas les détails d'implémentation),
- rester isolé (pas de MQTT, UI, runtime daemon),
- couvrir les anti-contrats critiques.

Note de terminologie (I6):
- Conceptuellement, le pipeline manipule des `reason_code`.
- Techniquement, `PublicationDecision` expose encore un champ `reason`.
- Dans ce fichier, `decision.reason` est traité comme le porteur du
  `reason_code` canonique de décision.
"""

from __future__ import annotations

from typing import Optional

from mapping.light import LightMapper
from models.decide_publication import decide_publication
from models.mapping import (
    LightCapabilities,
    MappingResult,
    ProjectionValidity,
)
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot, assess_eligibility
from validation.ha_component_registry import PRODUCT_SCOPE
from validation.ha_component_registry import validate_projection


def _cmd_with_generic(generic_type: str = "LIGHT_ON") -> JeedomCmd:
    return JeedomCmd(
        id=1,
        name="Cmd",
        generic_type=generic_type,
        type="action",
        sub_type="other",
    )


def _eligible_eq() -> JeedomEqLogic:
    return JeedomEqLogic(
        id=1,
        name="Eq eligible",
        is_enable=True,
        is_excluded=False,
        cmds=[_cmd_with_generic("LIGHT_ON")],
    )


def _eligible_light_eq_nominal() -> JeedomEqLogic:
    return JeedomEqLogic(
        id=11,
        name="Lampe salon",
        is_enable=True,
        is_excluded=False,
        cmds=[
            _cmd_with_generic("LIGHT_ON"),
            JeedomCmd(
                id=2,
                name="Off",
                generic_type="LIGHT_OFF",
                type="action",
                sub_type="other",
            ),
            JeedomCmd(
                id=3,
                name="State",
                generic_type="LIGHT_STATE",
                type="info",
                sub_type="binary",
            ),
        ],
    )


def _ineligible_eq_disabled() -> JeedomEqLogic:
    return JeedomEqLogic(
        id=2,
        name="Eq disabled",
        is_enable=False,
        is_excluded=False,
        cmds=[_cmd_with_generic("LIGHT_ON")],
    )


def _valid_pv() -> ProjectionValidity:
    return ProjectionValidity(
        is_valid=True,
        reason_code=None,
        missing_fields=[],
        missing_capabilities=[],
    )


def _invalid_pv(reason_code: str) -> ProjectionValidity:
    return ProjectionValidity(
        is_valid=False,
        reason_code=reason_code,
        missing_fields=[],
        missing_capabilities=[],
    )


def _make_mapping(
    *,
    ha_entity_type: str = "light",
    confidence: str = "sure",
    reason_code: str = "light_on_off",
    projection_validity: Optional[ProjectionValidity] = None,
) -> MappingResult:
    mapping = MappingResult(
        ha_entity_type=ha_entity_type,
        confidence=confidence,
        reason_code=reason_code,
        jeedom_eq_id=1,
        ha_unique_id="jeedom2ha_eq_1",
        ha_name="Eq test",
        capabilities=LightCapabilities(has_on_off=True),
    )
    mapping.projection_validity = projection_validity
    return mapping


def _contract_eval_for_ineligible(eq: JeedomEqLogic) -> tuple[object, None, None, None]:
    """Mini-harness contractuel pour I1 uniquement.

    Si l'équipement est inéligible à l'étape 1, aucun sous-bloc aval n'est produit.
    """
    eligibility = assess_eligibility(eq)
    if eligibility.is_eligible:
        raise AssertionError("Helper réservé aux cas inéligibles")
    return eligibility, None, None, None


def _contract_eval_for_eligible(eq: JeedomEqLogic) -> tuple[object, MappingResult, ProjectionValidity, object]:
    """Mini-harness contractuel pour I5/I7 (étapes 1→4, sans runtime)."""
    eligibility = assess_eligibility(eq)
    if not eligibility.is_eligible:
        raise AssertionError("Helper réservé aux cas éligibles")

    mapping = LightMapper().map(
        eq,
        TopologySnapshot(timestamp="2026-04-15T00:00:00Z", objects={}, eq_logics={}),
    )
    if mapping is None:
        raise AssertionError("Mapping absent pour un cas nominal éligible")

    projection_validity = validate_projection(mapping.ha_entity_type, mapping.capabilities)
    mapping.projection_validity = projection_validity
    decision = decide_publication(mapping, product_scope=list(PRODUCT_SCOPE))
    mapping.publication_decision_ref = decision
    return eligibility, mapping, projection_validity, decision


# ---------------------------------------------------------------------------
# Priorité demandée — cas structurants de l'ordre canonique
# ---------------------------------------------------------------------------


def test_i4_ambiguous_plus_out_of_scope_keeps_step2_cause():
    """I4 prioritaire: étape 2 prime sur étape 4.

    ambiguous + hors scope -> reason_code canonique de décision = ambiguous_skipped.
    """
    eligibility = assess_eligibility(_eligible_eq())
    assert eligibility.is_eligible is True

    mapping = _make_mapping(
        ha_entity_type="climate",  # hors PRODUCT_SCOPE
        confidence="ambiguous",    # échec étape 2
        projection_validity=_valid_pv(),
    )

    decision = decide_publication(mapping, product_scope=list(PRODUCT_SCOPE))

    assert decision.should_publish is False
    assert decision.reason == "ambiguous_skipped"
    assert decision.reason != "ha_component_not_in_product_scope"


def test_i2_invalid_projection_never_publishes():
    """I2 prioritaire: is_valid=False implique toujours should_publish=False."""
    eligibility = assess_eligibility(_eligible_eq())
    assert eligibility.is_eligible is True

    for reason_code in (
        "ha_missing_command_topic",
        "ha_missing_state_topic",
        "ha_missing_required_option",
        "ha_component_unknown",
    ):
        mapping = _make_mapping(
            ha_entity_type="light",
            confidence="sure",
            projection_validity=_invalid_pv(reason_code),
        )
        decision = decide_publication(mapping, product_scope=list(PRODUCT_SCOPE))
        assert decision.should_publish is False


def test_i4_invalid_projection_plus_out_of_scope_keeps_step3_cause():
    """I4 prioritaire: étape 3 prime sur étape 4.

    invalid_projection + hors scope -> cause conservée = reason_code étape 3.
    """
    eligibility = assess_eligibility(_eligible_eq())
    assert eligibility.is_eligible is True

    mapping = _make_mapping(
        ha_entity_type="climate",  # hors PRODUCT_SCOPE
        confidence="sure",
        projection_validity=_invalid_pv("ha_missing_state_topic"),
    )

    decision = decide_publication(mapping, product_scope=list(PRODUCT_SCOPE))

    assert decision.should_publish is False
    assert decision.reason == "ha_missing_state_topic"
    assert decision.reason != "ha_component_not_in_product_scope"


# ---------------------------------------------------------------------------
# Invariants et anti-contrats complémentaires
# ---------------------------------------------------------------------------


def test_i1_ineligible_cuts_pipeline_no_downstream_blocks():
    """I1: un équipement inéligible sort du pipeline (aucun sous-bloc aval)."""
    eligibility, mapping, projection_validity, publication_decision = _contract_eval_for_ineligible(
        _ineligible_eq_disabled()
    )

    assert eligibility.is_eligible is False
    assert mapping is None
    assert projection_validity is None
    assert publication_decision is None


def test_i5_eligible_traverses_mapping_validation_and_decision_blocks():
    """I5: tout équipement éligible produit les 3 sous-blocs aval."""
    eligibility, mapping, projection_validity, publication_decision = _contract_eval_for_eligible(
        _eligible_light_eq_nominal()
    )

    assert eligibility.is_eligible is True
    assert mapping is not None
    assert projection_validity is not None
    assert publication_decision is not None
    assert mapping.projection_validity is projection_validity
    assert mapping.publication_decision_ref is publication_decision


def test_i3_publish_true_requires_all_conditions():
    """I3: should_publish=True uniquement si toutes les conditions sont réunies."""
    mapping = _make_mapping(
        ha_entity_type="light",
        confidence="sure_mapping",
        projection_validity=_valid_pv(),
    )

    decision = decide_publication(mapping, product_scope=list(PRODUCT_SCOPE))

    assert decision.should_publish is True
    assert mapping.confidence in {"sure", "probable", "sure_mapping"}
    assert mapping.projection_validity is not None
    assert mapping.projection_validity.is_valid is True
    assert mapping.ha_entity_type in PRODUCT_SCOPE


def test_i6_reason_field_never_null_or_empty():
    """I6: le champ technique `reason` (porteur du reason_code) n'est jamais implicite."""
    cases = [
        # étape 2
        _make_mapping(confidence="ambiguous", projection_validity=_valid_pv()),
        _make_mapping(confidence="unknown", projection_validity=_valid_pv()),
        # étape 3
        _make_mapping(confidence="sure", projection_validity=_invalid_pv("ha_missing_command_topic")),
        # étape 4a
        _make_mapping(ha_entity_type="climate", confidence="sure", projection_validity=_valid_pv()),
        # étape 4b
        _make_mapping(ha_entity_type="light", confidence="probable", projection_validity=_valid_pv()),
        # nominal
        _make_mapping(ha_entity_type="light", confidence="sure", projection_validity=_valid_pv()),
    ]

    policies = [
        "sure_probable",
        "sure_probable",
        "sure_probable",
        "sure_probable",
        "sure_only",
        "sure_probable",
    ]

    for mapping, policy in zip(cases, policies):
        decision = decide_publication(
            mapping,
            confidence_policy=policy,
            product_scope=list(PRODUCT_SCOPE),
        )
        assert decision.reason is not None
        assert decision.reason != ""


def test_anti_contract_no_publish_without_validation_block():
    """Anti-contrat: publication interdite si la validation étape 3 est absente."""
    mapping = _make_mapping(
        ha_entity_type="light",
        confidence="sure",
        projection_validity=None,  # validation absente
    )

    decision = decide_publication(mapping, product_scope=list(PRODUCT_SCOPE))

    assert decision.should_publish is False
    assert decision.reason == "skipped_no_mapping_candidate"


def test_anti_contract_no_silent_fallback_reason_code():
    """Anti-contrat: aucun fallback silencieux, un reason explicite est imposé."""
    mapping = _make_mapping(
        ha_entity_type="light",
        confidence="unexpected_confidence",
        projection_validity=_valid_pv(),
    )

    decision = decide_publication(mapping, product_scope=list(PRODUCT_SCOPE))

    assert decision.should_publish is False
    assert decision.reason == "no_mapping"


def test_i7_technical_failure_never_overwrites_decision_reason():
    """I7: un résultat technique étape 5 ne modifie jamais la cause décisionnelle (1-4)."""
    _, mapping, _, decision = _contract_eval_for_eligible(_eligible_light_eq_nominal())
    assert decision.should_publish is True
    assert decision.reason in {"sure", "probable", "sure_mapping"}
    decision_reason_before = decision.reason

    # Simulation minimale de l'étape 5 (sans runtime):
    # un échec technique est enregistré séparément, sans écraser la décision produit.
    technical_result_reason_code = "discovery_publish_failed"
    mapping.reason_code = technical_result_reason_code

    assert mapping.reason_code == "discovery_publish_failed"
    assert decision.reason == decision_reason_before
    assert decision.reason != technical_result_reason_code
