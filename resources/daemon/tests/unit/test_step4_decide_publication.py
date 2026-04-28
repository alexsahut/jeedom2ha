"""Tests de l'étape 4 — Décision de publication — Story 4.1.

Vérifie que decide_publication() retourne un PublicationDecision correct pour
chaque combinaison de (mapping.confidence, projection_validity, product_scope,
confidence_policy).

Isolation totale :
  - Aucune dépendance MQTT, broker, daemon, pytest-asyncio.
  - Aucun conftest.py — helpers locaux définis dans ce fichier uniquement.
  - Pas d'effets de bord : decide_publication() est une fonction pure.

Invariants couverts :
  I2 : is_valid=False → should_publish=False garanti
  I3 : should_publish=True → toutes conditions (confidence publishable, is_valid, in scope)
  I4 : premier échec dans l'ordre étapes 2→3→4 = cause canonique unique
  I6 : reason jamais None ni vide sur tous les chemins de retour
  I7 : aucune logique technique (MQTT, broker) dans decide_publication — vérifié structurellement
"""

from typing import Optional

from models.mapping import (
    CoverCapabilities,
    LightCapabilities,
    MappingResult,
    ProjectionValidity,
    PublicationDecision,
    SwitchCapabilities,
)
from models.decide_publication import decide_publication
from validation.ha_component_registry import PRODUCT_SCOPE


# ---------------------------------------------------------------------------
# Helpers locaux — Task 2.3
# ---------------------------------------------------------------------------

def _make_mapping(
    ha_entity_type: str = "light",
    confidence: str = "sure",
    reason_code: str = "light_on_off",
    projection_validity: Optional[ProjectionValidity] = None,
) -> MappingResult:
    """Construit un MappingResult minimal pour les tests d'étape 4."""
    pv = projection_validity if projection_validity is not None else _valid_pv()
    mr = MappingResult(
        ha_entity_type=ha_entity_type,
        confidence=confidence,
        reason_code=reason_code,
        jeedom_eq_id=1,
        ha_unique_id="jeedom2ha_eq_1",
        ha_name="Test eq",
        capabilities=LightCapabilities(has_on_off=True),
    )
    mr.projection_validity = pv
    return mr


def _valid_pv() -> ProjectionValidity:
    """ProjectionValidity valide — is_valid=True."""
    return ProjectionValidity(
        is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[]
    )


def _failed_pv(reason_code: str = "ha_missing_state_topic") -> ProjectionValidity:
    """ProjectionValidity invalide — is_valid=False avec reason_code."""
    return ProjectionValidity(
        is_valid=False, reason_code=reason_code, missing_fields=[], missing_capabilities=[]
    )


# ---------------------------------------------------------------------------
# Task 2.4 — Cas nominaux (AC #1, #2)
# ---------------------------------------------------------------------------

def test_nominal_sure_publishes():
    """confidence=sure, is_valid=True, in scope → should_publish=True, reason="sure"."""
    mapping = _make_mapping(ha_entity_type="light", confidence="sure")
    result = decide_publication(mapping)

    assert result.should_publish is True
    assert result.reason == "sure"


def test_nominal_probable_sure_probable_policy_publishes():
    """confidence=probable, policy=sure_probable → should_publish=True, reason="probable"."""
    mapping = _make_mapping(ha_entity_type="light", confidence="probable")
    result = decide_publication(mapping, confidence_policy="sure_probable")

    assert result.should_publish is True
    assert result.reason == "probable"


# ---------------------------------------------------------------------------
# Task 2.5 — Cas d'échec mapping étape 2 (AC #6)
# ---------------------------------------------------------------------------

def test_mapping_failed_ambiguous_skipped():
    """confidence="ambiguous" → should_publish=False, reason="ambiguous_skipped"."""
    mapping = _make_mapping(confidence="ambiguous")
    result = decide_publication(mapping)

    assert result.should_publish is False
    assert result.reason == "ambiguous_skipped"


def test_mapping_failed_no_mapping():
    """confidence="unknown" → should_publish=False, reason="no_mapping"."""
    mapping = _make_mapping(confidence="unknown")
    result = decide_publication(mapping)

    assert result.should_publish is False
    assert result.reason == "no_mapping"


# ---------------------------------------------------------------------------
# Task 2.6 — Cas d'échec validation HA étape 3 (AC #5)
# ---------------------------------------------------------------------------

def test_projection_invalid_propagates_reason_code():
    """is_valid=False, reason_code="ha_missing_state_topic" → reason="ha_missing_state_topic"."""
    mapping = _make_mapping(
        confidence="sure",
        projection_validity=_failed_pv("ha_missing_state_topic"),
    )
    result = decide_publication(mapping)

    assert result.reason == "ha_missing_state_topic"
    assert result.should_publish is False


def test_projection_invalid_does_not_publish():
    """I2 : is_valid=False → should_publish=False toujours, quel que soit le reste."""
    for reason_code in [
        "ha_missing_state_topic",
        "ha_missing_command_topic",
        "ha_missing_required_option",
        "ha_component_unknown",
    ]:
        mapping = _make_mapping(
            confidence="sure",
            projection_validity=_failed_pv(reason_code),
        )
        result = decide_publication(mapping)
        assert result.should_publish is False, (
            f"I2 violé pour reason_code={reason_code!r} : should_publish devrait être False"
        )


# ---------------------------------------------------------------------------
# Task 2.7 — Cas d'échec scope/policy (AC #3, #4)
# ---------------------------------------------------------------------------

def test_component_not_in_scope():
    """ha_entity_type non dans scope → reason="ha_component_not_in_product_scope"."""
    mapping = _make_mapping(
        ha_entity_type="light",
        confidence="sure",
    )
    result = decide_publication(mapping, product_scope=[])

    assert result.should_publish is False
    assert result.reason == "ha_component_not_in_product_scope"


def test_low_confidence_sure_only_policy():
    """confidence=probable, policy=sure_only → should_publish=False, reason="probable_skipped"."""
    mapping = _make_mapping(ha_entity_type="light", confidence="probable")
    result = decide_publication(mapping, confidence_policy="sure_only")

    assert result.should_publish is False
    assert result.reason == "probable_skipped"


# ---------------------------------------------------------------------------
# Task 2.8 — Tests de priorité des causes — CRITIQUE I4 (AC #7, #8)
# ---------------------------------------------------------------------------

def test_i4_step2_wins_over_step4_ambiguous_plus_out_of_scope():
    """I4 — ambiguous + hors scope → "ambiguous_skipped" (étape 2 prime).

    L'étape 4 (ha_component_not_in_product_scope) ne peut pas écraser
    la cause de l'étape 2 (ambiguous_skipped).
    """
    mapping = _make_mapping(
        ha_entity_type="climate",  # hors PRODUCT_SCOPE
        confidence="ambiguous",
    )
    result = decide_publication(mapping, product_scope=list(PRODUCT_SCOPE))

    assert result.reason == "ambiguous_skipped", (
        f"I4 violé : attendu 'ambiguous_skipped', obtenu {result.reason!r}"
    )
    assert result.reason != "ha_component_not_in_product_scope"
    assert result.should_publish is False


def test_i4_step3_wins_over_step4_invalid_plus_out_of_scope():
    """I4 — is_valid=False + hors scope → reason_code étape 3 (étape 3 prime).

    L'étape 4 (ha_component_not_in_product_scope) ne peut pas écraser
    la cause de l'étape 3 (projection invalide).
    """
    mapping = _make_mapping(
        ha_entity_type="climate",  # hors PRODUCT_SCOPE
        confidence="sure",
        projection_validity=_failed_pv("ha_missing_state_topic"),
    )
    result = decide_publication(mapping, product_scope=list(PRODUCT_SCOPE))

    assert result.reason == "ha_missing_state_topic", (
        f"I4 violé : attendu 'ha_missing_state_topic', obtenu {result.reason!r}"
    )
    assert result.reason != "ha_component_not_in_product_scope"
    assert result.should_publish is False


# ---------------------------------------------------------------------------
# Task 2.9 — Tests d'invariants (AC #9, #10)
# ---------------------------------------------------------------------------

def test_i6_reason_never_null_on_all_failure_paths():
    """I6 — reason jamais None ni vide sur tous les chemins d'échec."""
    failure_cases = [
        # Étape 2
        _make_mapping(confidence="ambiguous"),
        _make_mapping(confidence="unknown"),
        _make_mapping(confidence="failed"),
        # Étape 3
        _make_mapping(confidence="sure", projection_validity=_failed_pv("ha_missing_state_topic")),
        _make_mapping(confidence="sure", projection_validity=_failed_pv("ha_missing_command_topic")),
        _make_mapping(confidence="sure", projection_validity=_failed_pv("ha_component_unknown")),
        # Étape 4a
        _make_mapping(ha_entity_type="climate", confidence="sure"),  # hors scope
        # Étape 4b
        _make_mapping(ha_entity_type="light", confidence="probable"),
    ]
    product_scopes = [
        list(PRODUCT_SCOPE), list(PRODUCT_SCOPE), list(PRODUCT_SCOPE),
        list(PRODUCT_SCOPE), list(PRODUCT_SCOPE), list(PRODUCT_SCOPE),
        list(PRODUCT_SCOPE),
        list(PRODUCT_SCOPE),
    ]
    policies = [
        "sure_probable", "sure_probable", "sure_probable",
        "sure_probable", "sure_probable", "sure_probable",
        "sure_probable",
        "sure_only",
    ]

    for mapping, scope, policy in zip(failure_cases, product_scopes, policies):
        result = decide_publication(mapping, confidence_policy=policy, product_scope=scope)
        assert result.reason is not None, (
            f"I6 violé : reason est None pour confidence={mapping.confidence!r}"
        )
        assert result.reason != "", (
            f"I6 violé : reason est vide pour confidence={mapping.confidence!r}"
        )


def test_i3_should_publish_true_requires_all_conditions():
    """I3 — should_publish=True seulement si toutes les conditions sont remplies.

    Conditions :
      - mapping.confidence ∈ {"sure", "probable", "sure_mapping"}
      - projection_validity.is_valid is True
      - ha_entity_type ∈ product_scope
    """
    # Cas nominal — toutes les conditions remplies
    mapping = _make_mapping(ha_entity_type="light", confidence="sure")
    result = decide_publication(mapping)

    assert result.should_publish is True
    # Vérification I3
    assert mapping.confidence in {"sure", "probable", "sure_mapping"}
    assert mapping.projection_validity is not None
    assert mapping.projection_validity.is_valid is True
    assert mapping.ha_entity_type in PRODUCT_SCOPE


def test_i3_should_publish_true_covers_sure_mapping_confidence():
    """I3 — sure_mapping est une confidence publishable valide (cas nominal)."""
    mapping = _make_mapping(ha_entity_type="light", confidence="sure_mapping")
    result = decide_publication(mapping)

    assert result.should_publish is True
    assert result.reason == "sure_mapping"


# ---------------------------------------------------------------------------
# Task 2.10 — Test de déterminisme
# ---------------------------------------------------------------------------

def test_determinism_same_inputs_same_output():
    """Appeler decide_publication() deux fois avec les mêmes entrées produit des résultats identiques."""
    mapping = _make_mapping(ha_entity_type="light", confidence="sure")

    result1 = decide_publication(mapping)
    result2 = decide_publication(mapping)

    assert result1.should_publish == result2.should_publish
    assert result1.reason == result2.reason


def test_determinism_failure_path():
    """Déterminisme sur un chemin d'échec — même résultat à chaque appel."""
    mapping = _make_mapping(
        ha_entity_type="light",
        confidence="sure",
        projection_validity=_failed_pv("ha_missing_state_topic"),
    )

    result1 = decide_publication(mapping)
    result2 = decide_publication(mapping)

    assert result1.should_publish == result2.should_publish
    assert result1.reason == result2.reason


# ---------------------------------------------------------------------------
# Test défensif anti-contrat (documenté, non nominal) — projection_validity=None
# ---------------------------------------------------------------------------

def test_defensive_projection_validity_none_fallback():
    """Fallback anti-contrat : projection_validity=None → reason="skipped_no_mapping_candidate".

    Ce chemin viole l'invariant pipeline (étape 3 toujours exécutée avant étape 4
    pour tout équipement ayant passé le mapping). Il ne doit pas survenir en production.
    Ce test documente uniquement le comportement défensif.
    """
    mr = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=1,
        ha_unique_id="jeedom2ha_eq_1",
        ha_name="Test eq",
        capabilities=LightCapabilities(has_on_off=True),
    )
    # projection_validity laissé à None — fallback anti-contrat
    assert mr.projection_validity is None

    result = decide_publication(mr)

    assert result.should_publish is False
    assert result.reason == "skipped_no_mapping_candidate"


# ---------------------------------------------------------------------------
# Tests additionnels — cas limites spécifiés AI-5
# ---------------------------------------------------------------------------

def test_edge_pv_is_valid_none_treated_as_not_valid():
    """pv.is_valid=None (skip explicite étape 3) → should_publish=False."""
    pv = ProjectionValidity(
        is_valid=None, reason_code="skipped_upstream_failure",
        missing_fields=[], missing_capabilities=[]
    )
    mapping = _make_mapping(confidence="sure", projection_validity=pv)
    result = decide_publication(mapping)

    assert result.should_publish is False
    assert result.reason == "skipped_upstream_failure"


def test_edge_product_scope_empty_blocks_all():
    """product_scope=[] → tout composant est hors scope → ha_component_not_in_product_scope."""
    mapping = _make_mapping(ha_entity_type="light", confidence="sure")
    result = decide_publication(mapping, product_scope=[])

    assert result.should_publish is False
    assert result.reason == "ha_component_not_in_product_scope"


def test_edge_sure_mapping_confidence_is_publishable():
    """confidence="sure_mapping" est dans _PUBLISHABLE_CONFIDENCES — traité comme publishable."""
    mapping = _make_mapping(ha_entity_type="switch", confidence="sure_mapping")
    result = decide_publication(mapping)

    # sure_mapping avec is_valid=True et in scope → should_publish=True
    assert result.should_publish is True
    assert result.reason == "sure_mapping"
