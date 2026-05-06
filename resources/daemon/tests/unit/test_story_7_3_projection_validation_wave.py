"""Tests story 7.3 — validation de projection de la vague cible.

Prouve que sensor et binary_sensor sont structurellement validables
via validate_projection() — état 'validable' selon AR6.
Tests en isolation totale : aucun daemon, MQTT, asyncio.
"""

from models.mapping import (
    LightCapabilities,
    CoverCapabilities,
    SwitchCapabilities,
    SensorCapabilities,
    ProjectionValidity,
)
from validation.ha_component_registry import validate_projection, PRODUCT_SCOPE


class _SensorLikeCapabilities:
    """Double minimal — simule le fallback getattr path dans _resolve_capability."""

    def __init__(self, has_state: bool = True):
        self.has_state = has_state


# ---------------------------------------------------------------------------
# Task 1 — Cas nominaux sensor/binary_sensor (AC: #1, #4)
# ---------------------------------------------------------------------------

def test_sensor_with_has_state_true_is_valid():
    result = validate_projection("sensor", SensorCapabilities(has_state=True))
    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_capabilities == []
    assert result.missing_fields == []


def test_binary_sensor_with_has_state_true_is_valid():
    result = validate_projection("binary_sensor", SensorCapabilities(has_state=True))
    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_capabilities == []
    assert result.missing_fields == []


def test_projection_validity_completeness_on_success():
    result = validate_projection("sensor", SensorCapabilities(has_state=True))
    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_fields == []
    assert result.missing_capabilities == []


# ---------------------------------------------------------------------------
# Task 2 — Cas d'échec capability et fields (AC: #2, #4)
# ---------------------------------------------------------------------------

def test_sensor_with_has_state_false_is_invalid():
    result = validate_projection("sensor", SensorCapabilities(has_state=False))
    assert result.is_valid is False
    assert result.reason_code == "ha_missing_state_topic"
    assert result.missing_capabilities == ["has_state"]
    assert result.missing_fields == ["state_topic"]


def test_binary_sensor_with_has_state_false_is_invalid():
    result = validate_projection("binary_sensor", SensorCapabilities(has_state=False))
    assert result.is_valid is False
    assert result.reason_code == "ha_missing_state_topic"
    assert result.missing_capabilities == ["has_state"]
    assert result.missing_fields == ["state_topic"]


def test_projection_validity_completeness_on_failure():
    result = validate_projection("sensor", SensorCapabilities(has_state=False))
    assert result.is_valid is False
    assert result.reason_code is not None
    assert len(result.missing_capabilities) > 0
    assert len(result.missing_fields) > 0


# ---------------------------------------------------------------------------
# Task 3 — Composant inconnu (AC: #3)
# ---------------------------------------------------------------------------

def test_unknown_component_returns_false_with_ha_component_unknown():
    result = validate_projection("unknown_component", SensorCapabilities(has_state=True))
    assert result.is_valid is False  # pas None — contrat validate_projection()
    assert result.reason_code == "ha_component_unknown"
    assert result.missing_capabilities == []
    assert result.missing_fields == []


# ---------------------------------------------------------------------------
# Task 4 — Non-régression et compatibilité doubles (AC: #5, #6, #7)
# ---------------------------------------------------------------------------

def test_light_nominal_non_regression():
    result = validate_projection("light", LightCapabilities(has_on_off=True))
    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_capabilities == []
    assert result.missing_fields == []


def test_light_failure_non_regression():
    result = validate_projection("light", LightCapabilities(has_on_off=False))
    assert result.is_valid is False
    assert result.reason_code == "ha_missing_command_topic"
    assert result.missing_capabilities == ["has_command"]
    assert result.missing_fields == ["command_topic"]


def test_cover_nominal_non_regression():
    result = validate_projection("cover", CoverCapabilities())
    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_capabilities == []
    assert result.missing_fields == []


def test_switch_nominal_non_regression():
    result = validate_projection("switch", SwitchCapabilities(has_on_off=True))
    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_capabilities == []
    assert result.missing_fields == []


def test_sensor_like_double_with_state_true_works():
    """Fallback getattr path dans _resolve_capability."""
    caps = _SensorLikeCapabilities(has_state=True)
    result = validate_projection("sensor", caps)
    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_capabilities == []
    assert result.missing_fields == []


def test_sensor_like_double_with_state_false_works():
    """Fallback getattr path retourne is_valid=False avec reason_code canonique."""
    caps = _SensorLikeCapabilities(has_state=False)
    result = validate_projection("sensor", caps)
    assert result.is_valid is False
    assert result.reason_code == "ha_missing_state_topic"
    assert result.missing_capabilities == ["has_state"]
    assert result.missing_fields == ["state_topic"]


def test_product_scope_snapshot_with_wave_open():
    """Snapshot du PRODUCT_SCOPE après ouverture de la vague cible (Story 7.4).

    Story 7.3 ne touchait pas à PRODUCT_SCOPE (validable ≠ ouvert) ; cette assertion
    fige la valeur actuelle (5 types). AR13 reste appliqué par
    test_product_scope_has_governance_proof (test_step3_governance_fr40.py).
    """
    assert PRODUCT_SCOPE == ["light", "cover", "switch", "sensor", "binary_sensor", "button"]
