"""test_sensor_mapper.py — Unit tests for the capability-based sensor mapper.

Story 2.5: Mapping & Exposition des Capteurs (Numériques & Binaires).
"""
import sys
import os
import pytest
from typing import List

# Add daemon to path for direct model imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'daemon'))

from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from models.mapping import MappingResult
from mapping.sensor import SensorMapper


@pytest.fixture
def mapper():
    return SensorMapper()


@pytest.fixture
def snapshot():
    """Minimal snapshot with one object for suggested_area testing."""
    return TopologySnapshot(
        timestamp="2026-03-14T10:00:00+01:00",
        objects={10: JeedomObject(id=10, name="Salon")},
        eq_logics={},
    )


def _make_eq(id=1, name="MultiSensor Salon", object_id=10, cmds=None, generic_type=None, eq_type_name="zwave"):
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


def _cmd(generic_type, id=100, type="info", sub_type="numeric", name=None, unit="", current_value=None):
    """Helper to create a JeedomCmd info."""
    return JeedomCmd(
        id=id,
        name=name or generic_type,
        generic_type=generic_type,
        type=type,
        sub_type=sub_type,
        unit=unit,
        current_value=current_value,
    )


# ==============================================================================
# Test: Basic structure & multisensor
# ==============================================================================

class TestSensorMapperStructure:
    def test_no_info_commands_returns_empty_list(self, mapper, snapshot):
        eq = _make_eq(cmds=[
            _cmd("ENERGY_ON", type="action", sub_type="other"),
        ])
        result = mapper.map(eq, snapshot)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_multiple_sensors_returned(self, mapper, snapshot):
        eq = _make_eq(cmds=[
            _cmd("TEMPERATURE", id=101, unit="°C"),
            _cmd("HUMIDITY", id=102, unit="%"),
        ])
        snapshot.eq_logics[eq.id] = eq
        results = mapper.map(eq, snapshot)
        assert len(results) == 2
        assert results[0].ha_entity_type == "sensor"
        assert results[1].ha_entity_type == "sensor"
        assert results[0].ha_unique_id == "jeedom2ha_cmd_101"
        assert results[1].ha_unique_id == "jeedom2ha_cmd_102"
        assert results[0].suggested_area == "Salon"
        assert results[1].suggested_area == "Salon"
        # Commands dict should only contain the specific command mapped
        assert list(results[0].commands.values())[0].id == 101
        assert list(results[1].commands.values())[0].id == 102


# ==============================================================================
# Test: Binary sensors and normalization
# ==============================================================================

class TestBinarySensors:
    def test_opening_sensor(self, mapper, snapshot):
        eq = _make_eq(cmds=[
            _cmd("OPENING", sub_type="binary", current_value=1)
        ])
        results = mapper.map(eq, snapshot)
        assert len(results) == 1
        res = results[0]
        assert res.ha_entity_type == "binary_sensor"
        assert res.capabilities.is_binary is True
        assert res.capabilities.device_class == "opening"
        assert mapper.normalize_binary_value(1) == "ON"
        assert mapper.normalize_binary_value(0) == "OFF"

    def test_motion_sensor(self, mapper, snapshot):
        eq = _make_eq(cmds=[
            _cmd("MOTION", sub_type="binary")
        ])
        results = mapper.map(eq, snapshot)
        assert len(results) == 1
        assert results[0].capabilities.device_class == "motion"

    def test_normalization_values(self, mapper, snapshot):
        # valid ON
        for v in [1, "1", "true", "True", "ON", "on", "open"]:
            assert mapper.normalize_binary_value(v) == "ON"
        # valid OFF
        for v in [0, "0", "false", "False", "OFF", "off", "closed"]:
            assert mapper.normalize_binary_value(v) == "OFF"
        # invalid
        for v in ["2", "unknown", None, 3.14]:
            assert mapper.normalize_binary_value(v) is None


# ==============================================================================
# Test: Numeric sensors and metadata
# ==============================================================================

class TestNumericSensors:
    def test_temperature_sensor_valid(self, mapper, snapshot):
        eq = _make_eq(cmds=[
            _cmd("TEMPERATURE", unit="°C")
        ])
        results = mapper.map(eq, snapshot)
        assert len(results) == 1
        res = results[0]
        assert res.ha_entity_type == "sensor"
        assert res.capabilities.device_class == "temperature"
        assert res.capabilities.unit_of_measurement == "°C"
        assert res.confidence in ("sure", "probable")

    def test_temperature_sensor_invalid_unit(self, mapper, snapshot):
        eq = _make_eq(cmds=[
            _cmd("TEMPERATURE", unit="%")
        ])
        results = mapper.map(eq, snapshot)
        assert len(results) == 1
        # unit should be omitted or rejected if totally incoherent
        # Requirements says: "unit_of_measurement est copié UNIQUEMENT si == '°C' ou '°F'. Sinon pas d'unité."
        assert results[0].capabilities.unit_of_measurement is None

    def test_consumption_sensor_total_increasing(self, mapper, snapshot):
        eq = _make_eq(cmds=[
            _cmd("CONSUMPTION", name="conso totale", unit="kWh")
        ])
        results = mapper.map(eq, snapshot)
        assert len(results) == 1
        assert results[0].capabilities.device_class == "energy"
        assert results[0].capabilities.unit_of_measurement == "kWh"
        assert results[0].capabilities.state_class == "total_increasing"

    def test_consumption_sensor_no_state_class(self, mapper, snapshot):
        eq = _make_eq(cmds=[
            _cmd("CONSUMPTION", name="conso courante", unit="W") # Maybe misconfigured Jeedom, should not be total_increasing
        ])
        results = mapper.map(eq, snapshot)
        assert len(results) == 1
        assert results[0].capabilities.state_class is None


# ==============================================================================
# Test: Publication Policy
# ==============================================================================

class TestPublicationDecision:
    def test_sure_publishes(self, mapper, snapshot):
        eq = _make_eq(cmds=[_cmd("TEMPERATURE")])
        res = mapper.map(eq, snapshot)[0]
        res.confidence = "sure"
        decision = mapper.decide_publication(res)
        assert decision.should_publish is True

    def test_probable_publishes(self, mapper, snapshot):
        eq = _make_eq(cmds=[_cmd("TEMPERATURE")])
        res = mapper.map(eq, snapshot)[0]
        res.confidence = "probable"
        decision = mapper.decide_publication(res)
        assert decision.should_publish is True

    def test_ambiguous_skipped(self, mapper, snapshot):
        eq = _make_eq(cmds=[_cmd("TEMPERATURE")])
        res = mapper.map(eq, snapshot)[0]
        res.confidence = "ambiguous"
        decision = mapper.decide_publication(res)
        assert decision.should_publish is False
