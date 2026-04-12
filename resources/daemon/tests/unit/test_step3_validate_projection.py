"""Tests de l'étape 3 — Validation HA — Story 3.2.

Vérifie que validate_projection() retourne un ProjectionValidity correct
pour chaque combinaison type/capabilities connue.
Tests en isolation totale : aucune dépendance MQTT, daemon, pytest-asyncio.
Helpers locaux uniquement — pas de conftest.py.
"""
import copy

from models.mapping import (
    LightCapabilities,
    CoverCapabilities,
    SwitchCapabilities,
    MappingResult,
    ProjectionValidity,
)
from validation.ha_component_registry import validate_projection


# ---------------------------------------------------------------------------
# Helpers locaux — Task 2.1
# ---------------------------------------------------------------------------

def _light(has_on_off: bool = True) -> LightCapabilities:
    return LightCapabilities(has_on_off=has_on_off)


def _cover() -> CoverCapabilities:
    return CoverCapabilities()


def _switch(has_on_off: bool = True, has_state: bool = False) -> SwitchCapabilities:
    return SwitchCapabilities(has_on_off=has_on_off, has_state=has_state)


class _SensorLikeCapabilities:
    """Double minimal pour les composants à état (sensor/binary_sensor).

    Simule une capability avec has_state uniquement — composants connus
    mais non ouverts dans PRODUCT_SCOPE (validés en Task 2.8).
    """
    def __init__(self, has_state: bool = True):
        self.has_state = has_state


class _SelectLikeCapabilities:
    """Double minimal pour les composants à options (select).

    Simule une capability avec has_options uniquement — composant connu
    mais non ouvert dans PRODUCT_SCOPE (validé en Task 2.8).
    """
    def __init__(self, has_on_off: bool = True, has_options: bool = True):
        self.has_on_off = has_on_off
        self.has_options = has_options


# ---------------------------------------------------------------------------
# Task 2.2 — Cas nominal light (AC #1)
# ---------------------------------------------------------------------------

def test_validate_projection_light_with_command_is_valid():
    """LightCapabilities(has_on_off=True) → is_valid=True, aucune erreur.

    Démontre aussi que le sous-bloc projection_validity se remplit
    sans modifier les autres sous-blocs du MappingResult (AC #1).
    """
    caps = _light(has_on_off=True)
    result = validate_projection("light", caps)

    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_capabilities == []
    assert result.missing_fields == []

    # Démontre que le sous-bloc étape 3 se remplit sans modifier le sous-bloc mapping
    mr = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off_only",
        jeedom_eq_id=1,
        ha_unique_id="jeedom2ha_eq_1",
        ha_name="Lampe salon",
        capabilities=caps,
    )
    mr.projection_validity = result
    assert mr.projection_validity.is_valid is True
    assert mr.reason_code == "light_on_off_only"  # sous-bloc mapping inchangé


# ---------------------------------------------------------------------------
# Task 2.3 — Cas d'échec light sans commande (AC #2)
# ---------------------------------------------------------------------------

def test_validate_projection_light_without_command_is_invalid():
    """LightCapabilities(has_on_off=False) → is_valid=False, ha_missing_command_topic."""
    caps = _light(has_on_off=False)
    result = validate_projection("light", caps)

    assert result.is_valid is False
    assert result.reason_code == "ha_missing_command_topic"
    assert result.missing_capabilities == ["has_command"]
    assert result.missing_fields == ["command_topic"]


# ---------------------------------------------------------------------------
# Task 2.4 — Cas nominal cover read-only (AC #3)
# ---------------------------------------------------------------------------

def test_validate_projection_cover_without_command_is_valid():
    """CoverCapabilities() sans commande action → is_valid=True.

    L'architecture HA MQTT cover est documentée comme ne requérant pas
    command_topic (mode optimiste / read-only valide). Le registre 3.1
    a déjà modélisé cover avec required_capabilities=[], ce que cette
    story valide en exercice.
    """
    caps = _cover()
    result = validate_projection("cover", caps)

    # cover n'exige pas command_topic au stade validation structurelle
    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_capabilities == []
    assert result.missing_fields == []


# ---------------------------------------------------------------------------
# Task 2.5 — Cas nominal switch (AC #5)
# ---------------------------------------------------------------------------

def test_validate_projection_switch_with_on_off_is_valid():
    """SwitchCapabilities(has_on_off=True) → is_valid=True."""
    caps = _switch(has_on_off=True)
    result = validate_projection("switch", caps)

    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_capabilities == []
    assert result.missing_fields == []


# ---------------------------------------------------------------------------
# Task 2.6 — Cas d'échec switch sans commande (AC #5)
# ---------------------------------------------------------------------------

def test_validate_projection_switch_without_command_is_invalid():
    """SwitchCapabilities(has_on_off=False, has_state=True) → ha_missing_command_topic.

    has_state=True ne suffit pas à rendre switch valide : command_topic requis.
    """
    caps = _switch(has_on_off=False, has_state=True)
    result = validate_projection("switch", caps)

    assert result.is_valid is False
    assert result.reason_code == "ha_missing_command_topic"
    assert "has_command" in result.missing_capabilities
    assert "command_topic" in result.missing_fields


# ---------------------------------------------------------------------------
# Task 2.7 — Cas d'échec type inconnu (AC #4)
# ---------------------------------------------------------------------------

def test_validate_projection_unknown_component_is_invalid():
    """Type absent de HA_COMPONENT_REGISTRY → is_valid=False, ha_component_unknown."""
    caps = _light(has_on_off=True)
    result = validate_projection("unknown_component", caps)

    assert result.is_valid is False
    assert result.reason_code == "ha_component_unknown"
    assert result.missing_capabilities == []
    assert result.missing_fields == []


# ---------------------------------------------------------------------------
# Task 2.8 — Composants connus non ouverts dans PRODUCT_SCOPE (AR8)
# ---------------------------------------------------------------------------

def test_validate_projection_sensor_without_state_returns_ha_missing_state_topic():
    """sensor avec has_state=False → ha_missing_state_topic.

    sensor est connu dans HA_COMPONENT_REGISTRY mais non ouvert dans PRODUCT_SCOPE.
    La validation structurelle (étape 3) est distincte de la gouvernance d'ouverture
    (Story 3.3 / étape 4) : on peut valider sans publier.
    """
    caps = _SensorLikeCapabilities(has_state=False)
    result = validate_projection("sensor", caps)

    assert result.is_valid is False
    assert result.reason_code == "ha_missing_state_topic"
    assert "has_state" in result.missing_capabilities
    assert "state_topic" in result.missing_fields


def test_validate_projection_sensor_with_state_is_valid():
    """sensor avec has_state=True → is_valid=True (composant connu non ouvert)."""
    caps = _SensorLikeCapabilities(has_state=True)
    result = validate_projection("sensor", caps)

    assert result.is_valid is True
    assert result.reason_code is None


def test_validate_projection_select_without_options_returns_ha_missing_required_option():
    """select avec has_options=False → ha_missing_required_option (priorité max).

    select est connu dans HA_COMPONENT_REGISTRY mais non ouvert dans PRODUCT_SCOPE.
    La priorité du reason_code garantit que ha_missing_required_option est retourné
    même si has_command est aussi manquant.
    """
    caps = _SelectLikeCapabilities(has_on_off=True, has_options=False)
    result = validate_projection("select", caps)

    assert result.is_valid is False
    assert result.reason_code == "ha_missing_required_option"
    assert "has_options" in result.missing_capabilities


def test_validate_projection_select_without_command_and_options_priority_is_options():
    """select sans has_command ni has_options → reason_code = ha_missing_required_option.

    Vérifie la priorité stable : ha_missing_required_option > ha_missing_command_topic.
    """
    caps = _SelectLikeCapabilities(has_on_off=False, has_options=False)
    result = validate_projection("select", caps)

    assert result.is_valid is False
    assert result.reason_code == "ha_missing_required_option"
    assert "has_options" in result.missing_capabilities
    assert "has_command" in result.missing_capabilities


# ---------------------------------------------------------------------------
# Task 2.9 — Test de pureté minimale (AR7)
# ---------------------------------------------------------------------------

def test_validate_projection_does_not_mutate_capabilities():
    """validate_projection() ne mute pas l'objet capabilities passé en argument."""
    caps = _light(has_on_off=False)
    caps_before = copy.deepcopy(caps)

    validate_projection("light", caps)

    assert caps.has_on_off == caps_before.has_on_off
    assert caps.has_brightness == caps_before.has_brightness
    assert caps.on_off_confidence == caps_before.on_off_confidence
    assert caps.brightness_confidence == caps_before.brightness_confidence
