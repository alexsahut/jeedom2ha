"""test_switch_mapper.py — Unit tests for the capability-based switch mapper.

Story 2.4: Tests covering all mapping scenarios for ENERGY_* generic types.
"""
import sys
import os
import pytest

# Add daemon to path for direct model imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'daemon'))

from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from mapping.switch import SwitchMapper


@pytest.fixture
def mapper():
    return SwitchMapper()


@pytest.fixture
def snapshot():
    """Minimal snapshot with one object for suggested_area testing."""
    return TopologySnapshot(
        timestamp="2026-03-14T10:00:00+01:00",
        objects={10: JeedomObject(id=10, name="Cuisine")},
        eq_logics={},
    )


def _make_eq(id=1, name="Prise Cuisine", object_id=10, cmds=None, generic_type=None, eq_type_name="zwave"):
    """Helper to create a JeedomEqLogic with given commands."""
    eq = JeedomEqLogic(
        id=id,
        name=name,
        object_id=object_id,
        eq_type_name=eq_type_name,
        cmds=cmds or [],
    )
    if generic_type is not None:
        eq.generic_type = generic_type
    return eq


def _cmd(generic_type, id=100, type="action", sub_type="other", name=None):
    """Helper to create a JeedomCmd."""
    return JeedomCmd(
        id=id,
        name=name or generic_type,
        generic_type=generic_type,
        type=type,
        sub_type=sub_type,
    )


# ==============================================================================
# Test: EqLogic without ENERGY_* commands → returns None
# ==============================================================================

class TestNonSwitchEquipment:
    def test_no_energy_commands_returns_none(self, mapper, snapshot):
        """EqLogic sans aucun ENERGY_* → retourne None (pas un switch)."""
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

    def test_flap_commands_only_returns_none(self, mapper, snapshot):
        """EqLogic avec FLAP_* uniquement (sans ENERGY_*) → retourne None."""
        eq = _make_eq(cmds=[
            _cmd("FLAP_UP", id=101, type="action", sub_type="other"),
            _cmd("FLAP_DOWN", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is None


# ==============================================================================
# Test: On/Off detection — Phase 1
# ==============================================================================

class TestOnOffDetection:
    def test_on_off_state_sure(self, mapper, snapshot):
        """ENERGY_ON + ENERGY_OFF + ENERGY_STATE → confidence=sure, has_on_off=True, has_state=True."""
        eq = _make_eq(cmds=[
            _cmd("ENERGY_STATE", id=100, type="info", sub_type="binary"),
            _cmd("ENERGY_ON", id=101, type="action", sub_type="other"),
            _cmd("ENERGY_OFF", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.ha_entity_type == "switch"
        assert result.confidence == "sure"
        assert result.capabilities.has_on_off is True
        assert result.capabilities.has_state is True
        assert result.capabilities.on_off_confidence == "sure"

    def test_on_off_without_state_probable(self, mapper, snapshot):
        """ENERGY_ON + ENERGY_OFF (sans ENERGY_STATE) → confidence=probable, has_state=False."""
        eq = _make_eq(cmds=[
            _cmd("ENERGY_ON", id=101, type="action", sub_type="other"),
            _cmd("ENERGY_OFF", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "probable"
        assert result.capabilities.has_on_off is True
        assert result.capabilities.has_state is False
        assert result.capabilities.on_off_confidence == "probable"

    def test_on_only_probable(self, mapper, snapshot):
        """ENERGY_ON seul → confidence=probable."""
        eq = _make_eq(cmds=[
            _cmd("ENERGY_ON", id=101, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "probable"
        assert result.capabilities.has_on_off is True

    def test_off_only_probable(self, mapper, snapshot):
        """ENERGY_OFF seul → confidence=probable."""
        eq = _make_eq(cmds=[
            _cmd("ENERGY_OFF", id=102, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "probable"
        assert result.capabilities.has_on_off is True

    def test_state_only_orphan_ambiguous(self, mapper, snapshot):
        """ENERGY_STATE seul → confidence=ambiguous, pas de publication."""
        eq = _make_eq(cmds=[
            _cmd("ENERGY_STATE", id=100, type="info", sub_type="binary"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.ha_entity_type == "switch"
        assert result.confidence == "ambiguous"
        assert result.capabilities.has_on_off is False


# ==============================================================================
# Test: device_class — Phase 2 (based on eq_type_name)
# ==============================================================================

class TestDeviceClass:
    def test_device_class_outlet_prise(self, mapper, snapshot):
        """eq_type_name contenant 'prise' → device_class='outlet'."""
        eq = _make_eq(
            cmds=[
                _cmd("ENERGY_ON", id=101, type="action", sub_type="other"),
                _cmd("ENERGY_OFF", id=102, type="action", sub_type="other"),
            ],
            eq_type_name="plugin_prise_gestion",
        )
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.device_class == "outlet"

    def test_device_class_outlet_energie(self, mapper, snapshot):
        """eq_type_name contenant 'energie' → device_class='outlet'."""
        eq = _make_eq(
            cmds=[
                _cmd("ENERGY_ON", id=101, type="action", sub_type="other"),
                _cmd("ENERGY_OFF", id=102, type="action", sub_type="other"),
                _cmd("ENERGY_STATE", id=100, type="info", sub_type="binary"),
            ],
            eq_type_name="plugin_energie_gestion",
        )
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.device_class == "outlet"

    def test_device_class_outlet_energy_en(self, mapper, snapshot):
        """eq_type_name contenant 'energy' (anglais) → device_class='outlet'."""
        eq = _make_eq(
            cmds=[_cmd("ENERGY_ON", id=101), _cmd("ENERGY_OFF", id=102)],
            eq_type_name="EnergySoc",
        )
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.device_class == "outlet"

    def test_device_class_outlet_plug(self, mapper, snapshot):
        """eq_type_name contenant 'plug' → device_class='outlet'."""
        eq = _make_eq(
            cmds=[_cmd("ENERGY_ON", id=101), _cmd("ENERGY_OFF", id=102)],
            eq_type_name="smart_plug",
        )
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.device_class == "outlet"

    def test_device_class_outlet_keyword(self, mapper, snapshot):
        """eq_type_name contenant 'outlet' → device_class='outlet'."""
        eq = _make_eq(
            cmds=[_cmd("ENERGY_ON", id=101), _cmd("ENERGY_OFF", id=102)],
            eq_type_name="outlet_manager",
        )
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.device_class == "outlet"

    def test_device_class_none_generic_plugin_z2m(self, mapper, snapshot):
        """eq_type_name = 'z2m' → device_class=None (plugin générique)."""
        eq = _make_eq(
            cmds=[_cmd("ENERGY_ON", id=101), _cmd("ENERGY_OFF", id=102)],
            eq_type_name="z2m",
        )
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.device_class is None

    def test_device_class_none_mqtt(self, mapper, snapshot):
        """eq_type_name = 'mqtt' → device_class=None."""
        eq = _make_eq(
            cmds=[_cmd("ENERGY_ON", id=101), _cmd("ENERGY_OFF", id=102)],
            eq_type_name="mqtt",
        )
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.device_class is None

    def test_device_class_none_jeelink(self, mapper, snapshot):
        """eq_type_name = 'jeelink' → device_class=None."""
        eq = _make_eq(
            cmds=[_cmd("ENERGY_ON", id=101), _cmd("ENERGY_OFF", id=102)],
            eq_type_name="jeelink",
        )
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.device_class is None

    def test_device_class_none_zwave(self, mapper, snapshot):
        """eq_type_name = 'zwave' → device_class=None."""
        eq = _make_eq(
            cmds=[_cmd("ENERGY_ON", id=101), _cmd("ENERGY_OFF", id=102)],
            eq_type_name="zwave",
        )
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.capabilities.device_class is None


# ==============================================================================
# Test: Anti-affinity guardrails
# ==============================================================================

class TestAntiAffinity:
    def test_anti_affinity_light_ambiguous(self, mapper, snapshot):
        """ENERGY_ON + OFF + LIGHT_ON → ambiguous (anti-affinité LIGHT)."""
        eq = _make_eq(cmds=[
            _cmd("ENERGY_ON", id=101, type="action", sub_type="other"),
            _cmd("ENERGY_OFF", id=102, type="action", sub_type="other"),
            _cmd("LIGHT_ON", id=200, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "conflicting_generic_types"
        assert "LIGHT_ON" in result.reason_details["conflicting_types"]

    def test_anti_affinity_flap_ambiguous(self, mapper, snapshot):
        """ENERGY_ON + OFF + FLAP_UP → ambiguous (anti-affinité FLAP)."""
        eq = _make_eq(cmds=[
            _cmd("ENERGY_ON", id=101, type="action", sub_type="other"),
            _cmd("ENERGY_OFF", id=102, type="action", sub_type="other"),
            _cmd("FLAP_UP", id=201, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "conflicting_generic_types"
        assert "FLAP_UP" in result.reason_details["conflicting_types"]

    def test_anti_affinity_heating_ambiguous(self, mapper, snapshot):
        """ENERGY_ON + OFF + HEATING_ON → ambiguous (anti-affinité HEATING)."""
        eq = _make_eq(cmds=[
            _cmd("ENERGY_ON", id=101, type="action", sub_type="other"),
            _cmd("ENERGY_OFF", id=102, type="action", sub_type="other"),
            _cmd("HEATING_ON", id=300, type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"


# ==============================================================================
# Test: eq.generic_type exclusion
# ==============================================================================

class TestEqGenericTypeExclusion:
    def test_heater_generic_type_returns_none(self, mapper, snapshot):
        """eq.generic_type = 'HEATER' avec ENERGY_ON + OFF → retourne None."""
        eq = _make_eq(
            cmds=[
                _cmd("ENERGY_ON", id=101, type="action", sub_type="other"),
                _cmd("ENERGY_OFF", id=102, type="action", sub_type="other"),
            ],
            generic_type="HEATER",
        )
        result = mapper.map(eq, snapshot)
        assert result is None

    def test_non_switch_generic_type_returns_none(self, mapper, snapshot):
        """eq.generic_type = 'camera' avec ENERGY_ON → retourne None."""
        eq = _make_eq(
            cmds=[_cmd("ENERGY_ON", id=101)],
            generic_type="camera",
        )
        result = mapper.map(eq, snapshot)
        assert result is None

    def test_allowed_switch_generic_type(self, mapper, snapshot):
        """eq.generic_type = 'switch' avec ENERGY_ON + OFF → publiable."""
        eq = _make_eq(
            cmds=[
                _cmd("ENERGY_ON", id=101),
                _cmd("ENERGY_OFF", id=102),
            ],
            generic_type="switch",
        )
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence in ("sure", "probable")

    def test_empty_generic_type_allowed(self, mapper, snapshot):
        """eq.generic_type = '' (empty) → publiable."""
        eq = _make_eq(
            cmds=[_cmd("ENERGY_ON", id=101)],
            generic_type="",
        )
        result = mapper.map(eq, snapshot)
        assert result is not None


# ==============================================================================
# Test: Name heuristics
# ==============================================================================

class TestNameHeuristics:
    def test_volet_garage_name_ambiguous(self, mapper, snapshot):
        """Nom 'Volet garage' + ENERGY_ON + OFF → ambiguous (heuristique nom)."""
        eq = _make_eq(
            name="Volet garage",
            cmds=[
                _cmd("ENERGY_ON", id=101),
                _cmd("ENERGY_OFF", id=102),
            ],
        )
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"
        assert result.reason_code == "name_heuristic_rejection"
        assert result.reason_details["matched_keyword"] in ("volet", "garage")

    def test_lumiere_name_ambiguous(self, mapper, snapshot):
        """Nom 'Lumière salon' + ENERGY_ON → ambiguous."""
        eq = _make_eq(
            name="Lumière salon",
            cmds=[_cmd("ENERGY_ON", id=101)],
        )
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence == "ambiguous"

    def test_prise_name_not_rejected(self, mapper, snapshot):
        """Nom 'Prise cuisine' + ENERGY_ON + OFF → NOT rejected (mot 'prise' absent de _NON_SWITCH_KEYWORDS)."""
        eq = _make_eq(
            name="Prise cuisine",
            cmds=[
                _cmd("ENERGY_ON", id=101),
                _cmd("ENERGY_OFF", id=102),
            ],
        )
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence in ("sure", "probable")

    def test_plug_name_not_rejected(self, mapper, snapshot):
        """Nom 'Smart plug salon' + ENERGY_ON + OFF → NOT rejected."""
        eq = _make_eq(
            name="Smart plug salon",
            cmds=[
                _cmd("ENERGY_ON", id=101),
                _cmd("ENERGY_OFF", id=102),
            ],
        )
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.confidence in ("sure", "probable")


# ==============================================================================
# Test: ID and area generation
# ==============================================================================

class TestIdAndAreaGeneration:
    def test_ha_unique_id_format(self, mapper, snapshot):
        """ha_unique_id == jeedom2ha_eq_{id}."""
        eq = _make_eq(id=99, cmds=[
            _cmd("ENERGY_ON", id=101),
            _cmd("ENERGY_OFF", id=102),
        ])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.ha_unique_id == "jeedom2ha_eq_99"
        assert result.jeedom_eq_id == 99

    def test_suggested_area_from_snapshot(self, mapper, snapshot):
        """suggested_area extrait du snapshot (objet Jeedom)."""
        eq = _make_eq(id=55, object_id=10, cmds=[
            _cmd("ENERGY_ON", id=101),
            _cmd("ENERGY_OFF", id=102),
        ])
        snapshot.eq_logics[55] = eq
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.suggested_area == "Cuisine"

    def test_ha_entity_type_switch(self, mapper, snapshot):
        """ha_entity_type == 'switch'."""
        eq = _make_eq(cmds=[_cmd("ENERGY_ON", id=101), _cmd("ENERGY_OFF", id=102)])
        result = mapper.map(eq, snapshot)
        assert result is not None
        assert result.ha_entity_type == "switch"


# ==============================================================================
# Test: Publication decision (bounded policy)
# ==============================================================================

class TestPublicationDecision:
    def test_sure_publishes(self, mapper, snapshot):
        """Confidence sure → always publish."""
        eq = _make_eq(cmds=[
            _cmd("ENERGY_STATE", id=100, type="info", sub_type="binary"),
            _cmd("ENERGY_ON", id=101),
            _cmd("ENERGY_OFF", id=102),
        ])
        mapping = mapper.map(eq, snapshot)
        decision = mapper.decide_publication(mapping)
        assert decision.should_publish is True
        assert decision.reason == "sure"

    def test_probable_publishes(self, mapper, snapshot):
        """Confidence probable → publish (bounded to Story 2.4 switch cases)."""
        eq = _make_eq(cmds=[
            _cmd("ENERGY_ON", id=101),
            _cmd("ENERGY_OFF", id=102),
        ])
        mapping = mapper.map(eq, snapshot)
        decision = mapper.decide_publication(mapping)
        assert decision.should_publish is True
        assert decision.reason == "probable"

    def test_ambiguous_skipped(self, mapper, snapshot):
        """Confidence ambiguous → never publish."""
        eq = _make_eq(cmds=[
            _cmd("ENERGY_STATE", id=100, type="info", sub_type="binary"),
        ])
        mapping = mapper.map(eq, snapshot)
        decision = mapper.decide_publication(mapping)
        assert decision.should_publish is False
        assert decision.reason == "ambiguous_skipped"

    def test_decision_has_mapping_ref(self, mapper, snapshot):
        """PublicationDecision must reference its MappingResult."""
        eq = _make_eq(cmds=[
            _cmd("ENERGY_ON", id=101),
            _cmd("ENERGY_OFF", id=102),
        ])
        mapping = mapper.map(eq, snapshot)
        decision = mapper.decide_publication(mapping)
        assert decision.mapping_result is mapping
