"""Story 7.2 — vague cible HA connue mais non ouverte.

Couvre la declaration explicite de sensor/binary_sensor dans le registre,
la frontiere de vague pe-epic-7 et la dataclass SensorCapabilities.
Tests en isolation totale : aucune dependance MQTT, daemon ou Jeedom.
"""

from __future__ import annotations

import inspect

from models.mapping import SensorCapabilities
from validation.ha_component_registry import (
    HA_COMPONENT_REGISTRY,
    PRODUCT_SCOPE,
    _CAPABILITY_TO_REASON,
    _resolve_capability,
    validate_projection,
)


WAVE_TARGETS = ("sensor", "binary_sensor")
NON_WAVE_TYPES = ("button", "number", "select", "climate")

EXPECTED_NON_WAVE_REGISTRY = {
    "button": {
        "required_fields": ["command_topic", "platform", "availability"],
        "required_capabilities": ["has_command"],
    },
    "number": {
        "required_fields": ["command_topic", "platform", "availability"],
        "required_capabilities": ["has_command"],
    },
    "select": {
        "required_fields": ["command_topic", "options", "platform", "availability"],
        "required_capabilities": ["has_command", "has_options"],
    },
    "climate": {
        "required_fields": ["availability"],
        "required_capabilities": [],
    },
}


def test_wave_target_types_in_registry():
    """AC1 — sensor et binary_sensor sont connus dans le registre."""
    for component in WAVE_TARGETS:
        assert component in HA_COMPONENT_REGISTRY


def test_wave_types_have_exact_d3_constraints():
    """AC1 — contraintes D3 exactes, sans enrichissement opportuniste."""
    expected = {
        "required_fields": ["state_topic", "platform", "availability"],
        "required_capabilities": ["has_state"],
    }

    for component in WAVE_TARGETS:
        assert HA_COMPONENT_REGISTRY[component] == expected


def test_has_state_reason_mapping_is_declared():
    """Task 1 — has_state est relie au reason_code canonique attendu."""
    assert _CAPABILITY_TO_REASON["has_state"] == (
        "ha_missing_state_topic",
        ["state_topic"],
    )


def test_non_wave_registry_entries_unchanged():
    """AC2 — les types hors vague restent strictement inchanges."""
    for component in NON_WAVE_TYPES:
        assert HA_COMPONENT_REGISTRY[component] == EXPECTED_NON_WAVE_REGISTRY[component]


def test_non_wave_types_not_in_product_scope():
    """AC2/AC5 — les types hors vague ne sont pas ouverts."""
    for component in NON_WAVE_TYPES:
        assert component not in PRODUCT_SCOPE


def test_product_scope_unchanged():
    """AC5 — aucune ouverture produit dans cette story."""
    assert PRODUCT_SCOPE == ["light", "cover", "switch"]
    for component in WAVE_TARGETS:
        assert component not in PRODUCT_SCOPE


def test_sensor_capabilities_dataclass_defaults():
    """AC3 — SensorCapabilities modelise explicitement has_state."""
    caps = SensorCapabilities()

    assert caps.has_state is False


def test_resolve_capability_has_state_sensor():
    """AC3 — has_state est resolu par la dataclass SensorCapabilities."""
    assert _resolve_capability("has_state", SensorCapabilities(has_state=True)) is True
    assert _resolve_capability("has_state", SensorCapabilities(has_state=False)) is False


def test_resolve_capability_uses_sensor_isinstance_path():
    """AC3 — verrouille le chemin typé avant le fallback getattr."""
    source = inspect.getsource(_resolve_capability)

    assert "isinstance(capabilities, SensorCapabilities)" in source


def test_validate_projection_sensor_nominal():
    """AC4 — sensor avec etat est validable en isolation."""
    result = validate_projection("sensor", SensorCapabilities(has_state=True))

    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_capabilities == []
    assert result.missing_fields == []


def test_validate_projection_sensor_no_state():
    """AC4 — sensor sans etat echoue avec ha_missing_state_topic."""
    result = validate_projection("sensor", SensorCapabilities(has_state=False))

    assert result.is_valid is False
    assert result.reason_code == "ha_missing_state_topic"
    assert result.missing_capabilities == ["has_state"]
    assert result.missing_fields == ["state_topic"]


def test_validate_projection_binary_sensor_nominal():
    """AC4 — binary_sensor avec etat est validable en isolation."""
    result = validate_projection("binary_sensor", SensorCapabilities(has_state=True))

    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_capabilities == []
    assert result.missing_fields == []


def test_validate_projection_binary_sensor_no_state():
    """AC4 — binary_sensor sans etat echoue avec ha_missing_state_topic."""
    result = validate_projection("binary_sensor", SensorCapabilities(has_state=False))

    assert result.is_valid is False
    assert result.reason_code == "ha_missing_state_topic"
    assert result.missing_capabilities == ["has_state"]
    assert result.missing_fields == ["state_topic"]
