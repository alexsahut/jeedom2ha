"""Tests story 7.4 — gouvernance d'ouverture de la vague cible.

Prouve que sensor et binary_sensor satisfont FR40 et sont autorisés par
decide_publication() après ouverture dans PRODUCT_SCOPE.
Tests en isolation totale : aucun daemon, réseau, asyncio.
"""

from typing import Optional

from models.mapping import MappingResult, ProjectionValidity, SensorCapabilities
from models.decide_publication import decide_publication
from validation.ha_component_registry import PRODUCT_SCOPE, HA_COMPONENT_REGISTRY


def _make_mapping(
    ha_entity_type: str = "sensor",
    confidence: str = "sure",
    projection_validity: Optional[ProjectionValidity] = None,
) -> MappingResult:
    pv = projection_validity if projection_validity is not None else ProjectionValidity(
        is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[]
    )
    mr = MappingResult(
        ha_entity_type=ha_entity_type,
        confidence=confidence,
        reason_code="sensor_state",
        jeedom_eq_id=1,
        ha_unique_id="jeedom2ha_eq_1",
        ha_name="Test sensor",
        capabilities=SensorCapabilities(has_state=True),
    )
    mr.projection_validity = pv
    return mr


# ---------------------------------------------------------------------------
# AC1 — PRODUCT_SCOPE contient les 5 types attendus
# ---------------------------------------------------------------------------

def test_product_scope_wave_opening_complete():
    """PRODUCT_SCOPE == ["light", "cover", "switch", "sensor", "binary_sensor"]."""
    assert set(PRODUCT_SCOPE) == {"light", "cover", "switch", "sensor", "binary_sensor"}
    assert len(PRODUCT_SCOPE) == 5


# ---------------------------------------------------------------------------
# AC4 — decide_publication() autorise sensor et binary_sensor
# ---------------------------------------------------------------------------

def test_decide_publication_authorizes_sensor_sure():
    """sensor + sure + is_valid=True → should_publish=True, reason="sure"."""
    mapping = _make_mapping(ha_entity_type="sensor", confidence="sure")
    result = decide_publication(mapping, confidence_policy="sure_probable")
    assert result.should_publish is True
    assert result.reason == "sure"


def test_decide_publication_authorizes_binary_sensor_sure():
    """binary_sensor + sure + is_valid=True → should_publish=True, reason="sure"."""
    mapping = _make_mapping(ha_entity_type="binary_sensor", confidence="sure")
    result = decide_publication(mapping, confidence_policy="sure_probable")
    assert result.should_publish is True
    assert result.reason == "sure"


def test_decide_publication_sensor_probable_sure_probable_policy():
    """sensor + probable + sure_probable → should_publish=True (policy permissive)."""
    mapping = _make_mapping(ha_entity_type="sensor", confidence="probable")
    result = decide_publication(mapping, confidence_policy="sure_probable")
    assert result.should_publish is True
    assert result.reason == "probable"


def test_decide_publication_sensor_probable_sure_only_policy():
    """sensor + probable + sure_only → should_publish=False (gate politique actif)."""
    mapping = _make_mapping(ha_entity_type="sensor", confidence="probable")
    result = decide_publication(mapping, confidence_policy="sure_only")
    assert result.should_publish is False
    assert result.reason == "probable_skipped"


# ---------------------------------------------------------------------------
# AC5 — mécanisme d'exclusion explicite reste fonctionnel
# ---------------------------------------------------------------------------

def test_governance_gate_sensor_not_in_scope_when_scope_empty():
    """sensor + scope=[] → ha_component_not_in_product_scope (exclusion explicite)."""
    mapping = _make_mapping(ha_entity_type="sensor", confidence="sure")
    result = decide_publication(mapping, product_scope=[])
    assert result.should_publish is False
    assert result.reason == "ha_component_not_in_product_scope"


# ---------------------------------------------------------------------------
# FR40 condition 1 — registre
# ---------------------------------------------------------------------------

def test_fr40_condition1_sensor_binary_sensor_in_registry():
    """sensor et binary_sensor ont required_fields + required_capabilities dans HA_COMPONENT_REGISTRY."""
    for component in ("sensor", "binary_sensor"):
        assert component in HA_COMPONENT_REGISTRY, f"{component} absent du registre"
        spec = HA_COMPONENT_REGISTRY[component]
        assert "required_fields" in spec
        assert "required_capabilities" in spec
        assert "has_state" in spec["required_capabilities"]


# ---------------------------------------------------------------------------
# NFR10 — non-régression du périmètre existant
# ---------------------------------------------------------------------------

def test_fr40_condition3_nfr10_non_regression_existing_scope():
    """light, cover et switch restent autorisés par decide_publication (non-régression 4D)."""
    for component in ("light", "cover", "switch"):
        mapping = _make_mapping(ha_entity_type=component, confidence="sure")
        result = decide_publication(mapping, confidence_policy="sure_probable")
        assert result.should_publish is True, f"{component} non autorisé après Story 7.4"
        assert result.reason == "sure"
