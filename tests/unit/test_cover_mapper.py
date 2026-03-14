"""test_cover_mapper.py — Unit tests for the capability-based cover mapper.

Story 2.3: Tests covering all mapping scenarios for FLAP_* generic types.
"""
import sys
import os
import pytest

# Add daemon to path for direct model imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'daemon'))

from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from mapping.cover import CoverMapper


@pytest.fixture
def mapper():
    return CoverMapper()


@pytest.fixture
def snapshot():
    """Minimal snapshot with one object for suggested_area testing."""
    return TopologySnapshot(
        timestamp="2026-03-14T02:00:00+01:00",
        objects={10: JeedomObject(id=10, name="Salon")},
        eq_logics={},
    )


def _make_eq(id=1, name="Volet Salon", object_id=10, cmds=None, generic_type=None):
    """Helper to create a JeedomEqLogic with given commands."""
    eq = JeedomEqLogic(
        id=id,
        name=name,
        object_id=object_id,
        eq_type_name="zwave",
        cmds=cmds or [],
    )
    if generic_type is not None:
        eq.generic_type = generic_type
    return eq


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
# Test: EqLogic without FLAP_* commands → returns None
# ==============================================================================

class TestNonCoverEquipment:
    def test_no_flap_commands_returns_none(self, mapper, snapshot):
        """EqLogic sans aucun FLAP_* → retourne None (pas un volet)."""
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
# Test: Open/Close detection (Phase 1)
# ==============================================================================

class TestOpenCloseDetection:
    def test_up_down_state_sure(self, mapper, snapshot):
        """FLAP_UP + FLAP_DOWN + FLAP_STATE → Open/Close sure."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="binary"),
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.ha_entity_type == "cover"
        assert result.confidence == "sure"
        assert result.capabilities.has_open_close is True
        assert result.capabilities.open_close_confidence == "sure"
        assert result.capabilities.has_position is False

    def test_up_down_no_state_probable(self, mapper, snapshot):
        """FLAP_UP + FLAP_DOWN (sans FLAP_STATE) → Open/Close probable."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "probable"
        assert result.capabilities.has_open_close is True
        assert result.capabilities.open_close_confidence == "probable"


# ==============================================================================
# Test: Stop detection (Phase 2)
# ==============================================================================

class TestStopDetection:
    def test_with_stop(self, mapper, snapshot):
        """FLAP_STATE + FLAP_UP + FLAP_DOWN + FLAP_STOP → has_stop=True."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="binary"),
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
            _cmd("FLAP_STOP", id=103, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "sure"
        assert result.capabilities.has_stop is True

    def test_without_stop(self, mapper, snapshot):
        """Sans FLAP_STOP → has_stop=False."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="binary"),
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.has_stop is False


# ==============================================================================
# Test: Position detection (Phase 3)
# ==============================================================================

class TestPositionDetection:
    def test_slider_plus_state_numeric_sure(self, mapper, snapshot):
        """FLAP_SLIDER + FLAP_STATE (numeric) → position sure."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="numeric"),
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
            _cmd("FLAP_SLIDER", id=103, type="action", sub_type="slider"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.has_position is True
        assert result.capabilities.position_confidence == "sure"

    def test_slider_without_numeric_state_probable(self, mapper, snapshot):
        """FLAP_SLIDER sans FLAP_STATE numérique → position probable."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
            _cmd("FLAP_SLIDER", id=103, type="action", sub_type="slider"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.has_position is True
        assert result.capabilities.position_confidence == "probable"

    def test_slider_alone_implicit_open_close(self, mapper, snapshot):
        """FLAP_SLIDER seul (sans UP/DOWN) → Open/Close sure (implicite via slider)."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_SLIDER", id=103, type="action", sub_type="slider"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.has_open_close is True
        assert result.capabilities.open_close_confidence == "sure"
        assert result.capabilities.has_position is True
        assert result.capabilities.position_confidence == "probable"


# ==============================================================================
# Test: BSO detection (Phase 4)
# ==============================================================================

class TestBSODetection:
    def test_bso_detected(self, mapper, snapshot):
        """FLAP_BSO_STATE + FLAP_BSO_UP + FLAP_BSO_DOWN → is_bso=True, confidence sure."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_BSO_STATE", id=100, type="info", sub_type="binary"),
            _cmd("FLAP_BSO_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_BSO_DOWN", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.is_bso is True
        assert result.confidence == "sure"

    def test_bso_without_state_probable(self, mapper, snapshot):
        """FLAP_BSO_UP + FLAP_BSO_DOWN (sans BSO_STATE) → probable."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_BSO_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_BSO_DOWN", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.is_bso is True
        assert result.confidence == "probable"

    def test_no_bso(self, mapper, snapshot):
        """Sans FLAP_BSO_* → is_bso=False."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="binary"),
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.is_bso is False


# ==============================================================================
# Test: Orphan state → ambiguous
# ==============================================================================

class TestOrphanState:
    def test_state_only_ambiguous(self, mapper, snapshot):
        """FLAP_STATE seul → confidence ambiguous (orphan)."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="binary"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "state_orphan"

    def test_flap_up_only_ambiguous(self, mapper, snapshot):
        """FLAP_UP seul (sans FLAP_DOWN) → aucun open/close ni position détectés → ambiguous (state_orphan)."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "state_orphan"


# ==============================================================================
# Test: Cumulated capabilities (Phase 5)
# ==============================================================================

class TestCumulatedCapabilities:
    def test_full_cover_sure(self, mapper, snapshot):
        """FLAP_STATE(numeric) + FLAP_UP + FLAP_DOWN + FLAP_STOP + FLAP_SLIDER → une seule entité cover, tout en sure."""
        eq = _make_eq(id=42, cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="numeric"),
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
            _cmd("FLAP_STOP", id=103, type="action", sub_type="other"),
            _cmd("FLAP_SLIDER", id=104, type="action", sub_type="slider"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.ha_entity_type == "cover"
        assert result.confidence == "sure"
        assert result.capabilities.has_open_close is True
        assert result.capabilities.open_close_confidence == "sure"
        assert result.capabilities.has_stop is True
        assert result.capabilities.has_position is True
        assert result.capabilities.position_confidence == "sure"

    def test_open_close_sure_position_probable_yields_probable(self, mapper, snapshot):
        """Open/Close sure + position probable → global probable."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="binary"),
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
            _cmd("FLAP_SLIDER", id=103, type="action", sub_type="slider"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.open_close_confidence == "sure"
        assert result.capabilities.position_confidence == "probable"
        assert result.confidence == "probable"


# ==============================================================================
# Test: False Positives Guardrails
# ==============================================================================

class TestFalsePositivesGuardrails:
    def test_explicit_non_cover_generic_type_returns_none(self, mapper, snapshot):
        """Si eq.generic_type est HEATER et commandes FLAP → retourne None."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="binary"),
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
        ], generic_type="HEATER")
        result = mapper.map(eq, snapshot)
        assert result is None

    def test_conflicting_generic_types_ambiguous(self, mapper, snapshot):
        """FLAP + LIGHT commandes → ambiguous via anti-affinité."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="binary"),
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
            _cmd("LIGHT_STATE", id=200, type="info", sub_type="binary"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "conflicting_generic_types"
        assert "LIGHT_STATE" in result.reason_details["conflicting_types"]

    def test_name_heuristic_rejection(self, mapper, snapshot):
        """Nom contenant 'lampe' avec FLAP → ambiguous."""
        eq = _make_eq(name="Lampe escalier", cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="binary"),
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "name_heuristic_rejection"
        assert result.reason_details["matched_keyword"] == "lampe"


# ==============================================================================
# Test: ID and area generation
# ==============================================================================

class TestIdGeneration:
    def test_ha_unique_id_format(self, mapper, snapshot):
        """ha_unique_id == jeedom2ha_eq_{id}."""
        eq = _make_eq(id=42, cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="binary"),
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.ha_unique_id == "jeedom2ha_eq_42"
        assert result.jeedom_eq_id == 42

    def test_suggested_area_from_snapshot(self, mapper, snapshot):
        """suggested_area extrait du snapshot (objet Jeedom)."""
        eq = _make_eq(id=42, object_id=10, cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="binary"),
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
        ])
        snapshot.eq_logics[42] = eq
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.suggested_area == "Salon"


# ==============================================================================
# Test: Publication decision (bounded policy)
# ==============================================================================

class TestPublicationDecision:
    def test_sure_publishes(self, mapper, snapshot):
        """Confidence sure → always publish."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="binary"),
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
        ])
        mapping = mapper.map(eq, snapshot)
        decision = mapper.decide_publication(mapping)
        assert decision.should_publish is True
        assert decision.reason == "sure"

    def test_probable_publishes(self, mapper, snapshot):
        """Confidence probable → publish (bounded to Story 2.3 cover cases)."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
        ])
        mapping = mapper.map(eq, snapshot)
        decision = mapper.decide_publication(mapping)
        assert decision.should_publish is True

    def test_ambiguous_skipped(self, mapper, snapshot):
        """Confidence ambiguous → never publish."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="binary"),
        ])
        mapping = mapper.map(eq, snapshot)
        decision = mapper.decide_publication(mapping)
        assert decision.should_publish is False
        assert decision.reason == "ambiguous_skipped"

    def test_decision_has_mapping_ref(self, mapper, snapshot):
        """PublicationDecision must reference its MappingResult."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_STATE", id=100, type="info", sub_type="binary"),
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
        ])
        mapping = mapper.map(eq, snapshot)
        decision = mapper.decide_publication(mapping)
        assert decision.mapping_result is mapping
