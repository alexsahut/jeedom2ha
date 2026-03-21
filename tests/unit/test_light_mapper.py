"""test_light_mapper.py — Unit tests for the capability-based light mapper.

Story 2.2: Tests covering all mapping scenarios for LIGHT_* generic types.
"""
import sys
import os
import pytest

# Add daemon to path for direct model imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'daemon'))

from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from mapping.light import LightMapper


@pytest.fixture
def mapper():
    return LightMapper()


@pytest.fixture
def snapshot():
    """Minimal snapshot with one object for suggested_area testing."""
    return TopologySnapshot(
        timestamp="2026-03-13T20:00:00+01:00",
        objects={10: JeedomObject(id=10, name="Salon")},
        eq_logics={},
    )


def _make_eq(id=1, name="Test Light", object_id=10, cmds=None):
    """Helper to create a JeedomEqLogic with given commands."""
    return JeedomEqLogic(
        id=id,
        name=name,
        object_id=object_id,
        eq_type_name="zwave",
        cmds=cmds or [],
    )


def _cmd(generic_type, id=100, type="info", sub_type="binary", name=None):
    """Helper to create a JeedomCmd."""
    return JeedomCmd(
        id=id,
        name=name or generic_type,
        generic_type=generic_type,
        type=type,
        sub_type=sub_type,
    )


# ==============================================================================
# Test: EqLogic without LIGHT_* commands → returns None
# ==============================================================================

class TestNonLightEquipment:
    def test_no_light_commands_returns_none(self, mapper, snapshot):
        """EqLogic sans aucun LIGHT_* → retourne None (pas une lumière)."""
        eq = _make_eq(cmds=[
            _cmd("TEMPERATURE", id=100, type="info", sub_type="numeric"),
            _cmd("HUMIDITY", id=101, type="info", sub_type="numeric"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is None

    def test_empty_commands_returns_none(self, mapper, snapshot):
        """EqLogic sans commandes → retourne None."""
        eq = _make_eq(cmds=[])
        result = mapper.map(eq, snapshot)
        assert result is None


# ==============================================================================
# Test: On/Off detection (Phase 1)
# ==============================================================================

class TestOnOffDetection:
    def test_state_on_off_sure(self, mapper, snapshot):
        """LIGHT_STATE + LIGHT_ON + LIGHT_OFF → On/Off sure."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "sure"
        assert result.capabilities.has_on_off is True
        assert result.capabilities.on_off_confidence == "sure"
        assert result.capabilities.has_brightness is False

    def test_state_on_missing_off_probable(self, mapper, snapshot):
        """LIGHT_STATE + LIGHT_ON (sans LIGHT_OFF) → On/Off probable."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "probable"
        assert result.capabilities.has_on_off is True
        assert result.capabilities.on_off_confidence == "probable"

    def test_state_off_missing_on_probable(self, mapper, snapshot):
        """LIGHT_STATE + LIGHT_OFF (sans LIGHT_ON) → On/Off probable."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "probable"
        assert result.capabilities.has_on_off is True
        assert result.capabilities.on_off_confidence == "probable"


# ==============================================================================
# Test: Brightness detection (Phase 2)
# ==============================================================================

class TestBrightnessDetection:
    def test_brightness_info_plus_slider_sure(self, mapper, snapshot):
        """LIGHT_BRIGHTNESS (info) + LIGHT_SLIDER (action) → brightness sure."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_BRIGHTNESS", id=100, type="info", sub_type="numeric"),
            _cmd("LIGHT_SLIDER", id=101, type="action", sub_type="slider"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.has_brightness is True
        assert result.capabilities.brightness_confidence == "sure"

    def test_slider_without_brightness_info_probable(self, mapper, snapshot):
        """LIGHT_STATE + LIGHT_SLIDER (sans LIGHT_BRIGHTNESS) → brightness probable."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_SLIDER", id=101, type="action", sub_type="slider"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.has_brightness is True
        assert result.capabilities.brightness_confidence == "probable"


# ==============================================================================
# Test: Cumulated capabilities (Phase 3)
# ==============================================================================

class TestCumulatedCapabilities:
    def test_full_light_sure(self, mapper, snapshot):
        """LIGHT_STATE + ON + OFF + BRIGHTNESS + SLIDER → une seule entité sure."""
        eq = _make_eq(id=42, cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
            _cmd("LIGHT_BRIGHTNESS", id=103, type="info", sub_type="numeric"),
            _cmd("LIGHT_SLIDER", id=104, type="action", sub_type="slider"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.ha_entity_type == "light"
        assert result.confidence == "sure"
        assert result.capabilities.has_on_off is True
        assert result.capabilities.has_brightness is True
        assert result.capabilities.on_off_confidence == "sure"
        assert result.capabilities.brightness_confidence == "sure"
        assert result.reason_code == "light_on_off_brightness"

    def test_partial_cumulated_probable(self, mapper, snapshot):
        """LIGHT_STATE + LIGHT_ON + LIGHT_SLIDER → both probable, global probable."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_SLIDER", id=104, type="action", sub_type="slider"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.has_on_off is True
        assert result.capabilities.on_off_confidence == "probable"
        assert result.capabilities.has_brightness is True
        assert result.capabilities.brightness_confidence == "probable"
        assert result.confidence == "probable"

    def test_on_off_sure_brightness_probable_yields_probable(self, mapper, snapshot):
        """On/Off sure + brightness probable → global probable (min)."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
            _cmd("LIGHT_SLIDER", id=104, type="action", sub_type="slider"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.on_off_confidence == "sure"
        assert result.capabilities.brightness_confidence == "probable"
        assert result.confidence == "probable"


# ==============================================================================
# Test: Ambiguous / edge cases
# ==============================================================================

class TestAmbiguousCases:
    def test_color_only_ambiguous(self, mapper, snapshot):
        """LIGHT_SET_COLOR seul → confidence ambiguous (V1 non supporté)."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_SET_COLOR", id=100, type="action", sub_type="color"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "color_only_unsupported"

    def test_state_orphan_ambiguous(self, mapper, snapshot):
        """LIGHT_STATE seul → confidence ambiguous."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "state_orphan"


# ==============================================================================
# Test: False Positives Guardrails
# ==============================================================================

class TestFalsePositivesGuardrails:
    def test_explicit_non_light_generic_type_returns_none(self, mapper, snapshot):
        """Si l'équipement a un eq.generic_type différent de 'light', on ignore."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        eq.generic_type = "HEATER"  # Explicitly not a light
        result = mapper.map(eq, snapshot)
        assert result is None

    def test_conflicting_generic_types_ambiguous(self, mapper, snapshot):
        """LIGHT_ON + HEATING_STATE → ambiguous (conflit de domaines)."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
            _cmd("HEATING_STATE", id=200, type="info", sub_type="binary"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "conflicting_generic_types"
        assert "HEATING_STATE" in result.reason_details["conflicting_types"]

    def test_name_heuristic_rejection(self, mapper, snapshot):
        """Nom contenant 'prise' ou 'chauffage' avec des commandes lumière → ambiguous."""
        eq = _make_eq(id=99, name="Prise TV Salon", cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "name_heuristic_rejection"
        assert result.reason_details["matched_keyword"] == "prise"

    def test_bureau_with_light_cmds_not_ambiguous(self, mapper, snapshot):
        """Given équipement nommé "lampe bureau" avec LIGHT_STATE/ON/OFF,
        When le mapper évalue,
        Then confidence in ("sure", "probable") — "eau" ne matche pas comme mot entier dans "bureau".
        """
        eq = _make_eq(name="lampe bureau", cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence in ("sure", "probable")

    def test_eau_standalone_still_ambiguous(self, mapper, snapshot):
        """Given équipement nommé "eau chaude salon" avec LIGHT_STATE/ON/OFF,
        When le mapper évalue,
        Then confidence == "ambiguous" et reason_code == "name_heuristic_rejection" — "eau" est un mot entier.
        """
        eq = _make_eq(name="eau chaude salon", cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "name_heuristic_rejection"
        assert result.reason_details["matched_keyword"] == "eau"

    def test_chauffe_eau_still_ambiguous(self, mapper, snapshot):
        """Given équipement nommé "chauffe-eau garage" avec LIGHT_STATE/ON/OFF,
        When le mapper évalue,
        Then confidence == "ambiguous" et reason_code == "name_heuristic_rejection".
        Ne pas asserter matched_keyword exact : "chauffe-eau" ou "eau" peuvent tous deux matcher via word boundary.
        """
        eq = _make_eq(name="chauffe-eau garage", cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "name_heuristic_rejection"

    def test_bateau_not_ambiguous(self, mapper, snapshot):
        """Given équipement nommé "bateau salon" avec LIGHT_STATE/ON/OFF,
        When le mapper évalue,
        Then confidence in ("sure", "probable") — "eau" ne matche pas comme mot entier dans "bateau".
        """
        eq = _make_eq(name="bateau salon", cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence in ("sure", "probable")

    def test_smoke_detector_with_light_led_ambiguous(self, mapper, snapshot):
        """Détecteur de fumée avec une LED type LIGHT_STATE → ambiguous (conflit SMOKE)."""
        eq = _make_eq(name="Détecteur Fumée Couloir", cmds=[
            _cmd("SMOKE", id=300, type="info", sub_type="binary"),
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "conflicting_generic_types"


# ==============================================================================
# Test: Mixed commands (LIGHT + non-LIGHT neutral)
# ==============================================================================

class TestMixedCommands:
    def test_light_and_temperature_only_light_retained(self, mapper, snapshot):
        """EqLogic avec LIGHT_* + TEMPERATURE → seules LIGHT_* retenues."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
            _cmd("TEMPERATURE", id=200, type="info", sub_type="numeric"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "sure"
        assert "TEMPERATURE" not in result.commands


# ==============================================================================
# Test: ID and area generation
# ==============================================================================

class TestIdGeneration:
    def test_ha_unique_id_format(self, mapper, snapshot):
        """ha_unique_id == jeedom2ha_eq_{id}."""
        eq = _make_eq(id=42, cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.ha_unique_id == "jeedom2ha_eq_42"
        assert result.jeedom_eq_id == 42

    def test_suggested_area_from_snapshot(self, mapper, snapshot):
        """suggested_area extrait du snapshot (objet Jeedom)."""
        eq = _make_eq(id=42, object_id=10, cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        # Add eq to snapshot for get_suggested_area
        snapshot.eq_logics[42] = eq
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.suggested_area == "Salon"

    def test_suggested_area_none_when_no_object(self, mapper):
        """suggested_area == None quand pas d'objet Jeedom."""
        snapshot = TopologySnapshot(
            timestamp="2026-03-13T20:00:00+01:00",
            objects={},
            eq_logics={},
        )
        eq = _make_eq(id=42, object_id=None, cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.suggested_area is None


# ==============================================================================
# Test: Publication decision (bounded policy)
# ==============================================================================

class TestPublicationDecision:
    def test_sure_publishes(self, mapper, snapshot):
        """Confidence sure → always publish."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        mapping = mapper.map(eq, snapshot)
        decision = mapper.decide_publication(mapping)
        assert decision.should_publish is True
        assert decision.reason == "sure"

    def test_probable_publishes(self, mapper, snapshot):
        """Confidence probable → publish (bounded to Story 2.2 light cases)."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
        ])
        mapping = mapper.map(eq, snapshot)
        decision = mapper.decide_publication(mapping)
        assert decision.should_publish is True

    def test_ambiguous_skipped(self, mapper, snapshot):
        """Confidence ambiguous → never publish."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_SET_COLOR", id=100, type="action", sub_type="color"),
        ])
        mapping = mapper.map(eq, snapshot)
        decision = mapper.decide_publication(mapping)
        assert decision.should_publish is False
        assert decision.reason == "ambiguous_skipped"

    def test_decision_has_mapping_ref(self, mapper, snapshot):
        """PublicationDecision must reference its MappingResult."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        mapping = mapper.map(eq, snapshot)
        decision = mapper.decide_publication(mapping)
        assert decision.mapping_result is mapping


# ==============================================================================
# Test: State numeric as brightness fallback
# ==============================================================================

class TestStateNumericFallback:
    def test_state_numeric_as_brightness_probable(self, mapper, snapshot):
        """LIGHT_STATE (numeric sub_type) sans slider → brightness probable via fallback."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="numeric"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.has_brightness is True
        assert result.capabilities.brightness_confidence == "probable"
        assert result.reason_code == "light_on_off_brightness"

    def test_state_binary_no_brightness(self, mapper, snapshot):
        """LIGHT_STATE (binary) sans slider → pas de brightness."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.has_brightness is False
        assert result.reason_code == "light_on_off_only"


# ==============================================================================
# Test: Déduplication (Story 2.6)
# ==============================================================================

class TestDeduplication:
    def test_light_state_duplicate_binary_numeric_resolved(self, mapper, snapshot):
        """2× LIGHT_STATE (binary + numeric) → binary gagne, confidence=probable, deduplicated=True."""
        eq = _make_eq(id=510, cmds=[
            _cmd("LIGHT_STATE", id=4655, type="info", sub_type="binary"),
            _cmd("LIGHT_STATE", id=4658, type="info", sub_type="numeric"),
            _cmd("LIGHT_ON", id=4659, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=4660, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "probable"
        # reason_code : code métier standard, pas un code dedup
        assert result.reason_code == "light_on_off_only"
        assert result.reason_details is not None
        assert result.reason_details["deduplicated"] is True
        assert result.reason_details["kept_cmd_id"] == 4655
        assert result.reason_details["discarded_cmd_id"] == 4658
        assert result.reason_details["criterion"] == "sub_type"
        # Le gagnant (binary) est dans les commandes résolues
        assert result.commands["LIGHT_STATE"].id == 4655
        assert result.commands["LIGHT_STATE"].sub_type == "binary"

    def test_light_state_duplicate_same_subtype_ambiguous(self, mapper, snapshot):
        """2× LIGHT_STATE (numeric + numeric) → même sub_type → ambiguous (comportement actuel)."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="numeric"),
            _cmd("LIGHT_STATE", id=200, type="info", sub_type="numeric"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "duplicate_generic_types"

    def test_light_state_duplicate_no_preferred_match_ambiguous(self, mapper, snapshot):
        """2× LIGHT_STATE (string + other) → aucun ne correspond à 'binary' → ambiguous conservatif."""
        eq = _make_eq(cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="string"),
            _cmd("LIGHT_STATE", id=200, type="info", sub_type="other"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "duplicate_generic_types"

    def test_nominal_light_no_duplicate_no_regression(self, mapper, snapshot):
        """Cas nominal sans doublon → confidence=sure (pas de régression)."""
        eq = _make_eq(id=42, cmds=[
            _cmd("LIGHT_STATE", id=100, type="info", sub_type="binary"),
            _cmd("LIGHT_ON", id=101, type="action", sub_type="other"),
            _cmd("LIGHT_OFF", id=102, type="action", sub_type="other"),
            _cmd("LIGHT_BRIGHTNESS", id=103, type="info", sub_type="numeric"),
            _cmd("LIGHT_SLIDER", id=104, type="action", sub_type="slider"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "sure"
        assert result.reason_code == "light_on_off_brightness"
        # Pas de metadata dedup dans reason_details
        assert result.reason_details is None or "deduplicated" not in result.reason_details
