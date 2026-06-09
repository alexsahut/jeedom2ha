"""Story 10.2 - ClimateMapper + publish_climate + PRODUCT_SCOPE gate FR40/NFR10."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from discovery.publisher import DiscoveryPublisher
from discovery.registry import PublisherRegistry
from mapping.climate import ClimateMapper
from models.mapping import ClimateCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from validation.ha_component_registry import validate_projection


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-06-09T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon"), 2: JeedomObject(id=2, name="Chambre")},
        eq_logics={eq.id: eq},
    )


def _thermostat_eq(
    eq_id: int,
    name: str,
    *,
    with_temperature: bool = True,
    with_state: bool = True,
    object_id: int = 1,
    setpoint_sub_type: str = "slider",
) -> JeedomEqLogic:
    cmds = [
        JeedomCmd(
            id=eq_id * 10 + 1,
            name="Consigne",
            generic_type="THERMOSTAT_SET_SETPOINT",
            type="action",
            sub_type=setpoint_sub_type,
        )
    ]
    if with_temperature:
        cmds.append(
            JeedomCmd(
                id=eq_id * 10 + 2,
                name="Température",
                generic_type="THERMOSTAT_TEMPERATURE",
                type="info",
                sub_type="numeric",
            )
        )
    if with_state:
        cmds.append(
            JeedomCmd(
                id=eq_id * 10 + 3,
                name="Actif",
                generic_type="THERMOSTAT_STATE",
                type="info",
                sub_type="binary",
            )
        )
    return JeedomEqLogic(
        id=eq_id,
        name=name,
        object_id=object_id,
        eq_type_name="thermostat",
        cmds=cmds,
    )


# ---------------------------------------------------------------------------
# ClimateMapper — cas nominaux (AC2)
# ---------------------------------------------------------------------------

def test_climate_mapper_nominal_with_temperature():
    eq = _thermostat_eq(5100, "Thermostat chambre Arthur", with_temperature=True)

    mapping = ClimateMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.ha_entity_type == "climate"
    assert mapping.confidence == "sure"
    assert mapping.reason_code == "climate_thermostat_setpoint"
    assert mapping.jeedom_eq_id == 5100
    assert mapping.ha_unique_id == "jeedom2ha_eq_5100"
    assert mapping.ha_name == "Thermostat chambre Arthur"
    assert isinstance(mapping.capabilities, ClimateCapabilities)
    assert mapping.capabilities.has_setpoint is True
    assert mapping.capabilities.has_current_temperature is True
    assert "THERMOSTAT_SET_SETPOINT" in mapping.commands
    assert "THERMOSTAT_TEMPERATURE" in mapping.commands
    assert mapping.reason_details["temperature_command_topic"] == "jeedom2ha/5100/temperature/set"
    assert mapping.reason_details["temperature_state_topic"] == "jeedom2ha/5100/temperature/state"
    assert mapping.reason_details["current_temperature_topic"] == "jeedom2ha/5100/current_temperature"


def test_climate_mapper_nominal_setpoint_only():
    eq = _thermostat_eq(5101, "Thermostat Galerie", with_temperature=False)

    mapping = ClimateMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.ha_entity_type == "climate"
    assert mapping.capabilities.has_setpoint is True
    assert mapping.capabilities.has_current_temperature is False
    assert "THERMOSTAT_SET_SETPOINT" in mapping.commands
    assert "THERMOSTAT_TEMPERATURE" not in mapping.commands
    assert "current_temperature_topic" not in (mapping.reason_details or {})


def test_climate_mapper_nominal_seven_thermostats():
    names = [
        "Thermostat chambre Arthur",
        "Thermostat chambre Margaux",
        "Thermostat chambre parent",
        "Thermostat Galerie",
        "Thermostat RDC",
        "Thermostat SDB",
        "Thermostat SPA",
    ]
    for i, name in enumerate(names):
        eq = _thermostat_eq(5200 + i, name)
        mapping = ClimateMapper().map(eq, _snapshot(eq))
        assert mapping is not None, f"Mapper should match {name}"
        assert mapping.ha_entity_type == "climate"


def test_mapper_registry_prioritizes_climate_over_binary_sensor_for_thermostat_state():
    from mapping.registry import MapperRegistry

    eq = _thermostat_eq(5209, "Thermostat prioritaire", with_temperature=True, with_state=True)

    mapping = MapperRegistry().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.ha_entity_type == "climate"


# ---------------------------------------------------------------------------
# ClimateMapper — cas d'échec / non-correspondance (AC2)
# ---------------------------------------------------------------------------

def test_climate_mapper_rejects_info_numeric_only():
    """Un capteur temperature sans consigne ne doit pas être mappé climate."""
    eq = JeedomEqLogic(
        id=5300,
        name="Capteur température",
        object_id=1,
        eq_type_name="zwave",
        cmds=[
            JeedomCmd(
                id=53001,
                name="Température",
                generic_type="THERMOSTAT_TEMPERATURE",
                type="info",
                sub_type="numeric",
            )
        ],
    )
    mapping = ClimateMapper().map(eq, _snapshot(eq))
    assert mapping is None


def test_climate_mapper_accepts_setpoint_with_empty_subtype_from_terrain():
    """Terrain réel: certains thermostats ont sub_type vide sur THERMOSTAT_SET_SETPOINT."""
    eq = _thermostat_eq(
        5301,
        "Thermostat terrain sub_type vide",
        with_temperature=True,
        setpoint_sub_type="",
    )

    mapping = ClimateMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.ha_entity_type == "climate"


def test_climate_mapper_rejects_setpoint_with_unsupported_subtype():
    """On borne l'ouverture: un sub_type explicite non supporté reste rejeté."""
    eq = _thermostat_eq(
        5303,
        "Commande consigne mal typée",
        with_temperature=False,
        setpoint_sub_type="other",
    )

    mapping = ClimateMapper().map(eq, _snapshot(eq))

    assert mapping is None


def test_climate_mapper_rejects_no_commands():
    eq = JeedomEqLogic(id=5302, name="Équipement vide", object_id=1, eq_type_name="virtual", cmds=[])
    mapping = ClimateMapper().map(eq, _snapshot(eq))
    assert mapping is None


# ---------------------------------------------------------------------------
# publish_climate (AC2 / AC3)
# ---------------------------------------------------------------------------

def _make_climate_mapping(eq_id: int = 5100, with_temperature: bool = True):
    from models.mapping import MappingResult

    reason_details = {
        "temperature_command_topic": f"jeedom2ha/{eq_id}/temperature/set",
        "temperature_state_topic": f"jeedom2ha/{eq_id}/temperature/state",
    }
    if with_temperature:
        reason_details["current_temperature_topic"] = f"jeedom2ha/{eq_id}/current_temperature"

    return MappingResult(
        ha_entity_type="climate",
        confidence="sure",
        reason_code="climate_thermostat_setpoint",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name="Thermostat RDC",
        capabilities=ClimateCapabilities(has_setpoint=True, has_current_temperature=with_temperature),
        reason_details=reason_details,
    )


def _make_snapshot_for(eq_id: int) -> TopologySnapshot:
    from models.topology import JeedomEqLogic
    eq = JeedomEqLogic(id=eq_id, name="Thermostat RDC", object_id=1, eq_type_name="thermostat", cmds=[])
    return TopologySnapshot(
        timestamp="2026-06-09T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={eq_id: eq},
    )


@pytest.mark.asyncio
async def test_publish_climate_with_current_temperature():
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    publisher = DiscoveryPublisher(bridge)

    mapping = _make_climate_mapping(eq_id=5100, with_temperature=True)
    snapshot = _make_snapshot_for(5100)

    result = await publisher.publish_climate(mapping, snapshot)

    assert result is True
    bridge.publish_message.assert_called_once()
    call_args = bridge.publish_message.call_args
    topic = call_args[0][0]
    payload_json = call_args[0][1]
    payload = json.loads(payload_json)

    assert topic == "homeassistant/climate/jeedom2ha_5100/config"
    assert payload["unique_id"] == "jeedom2ha_eq_5100"
    assert payload["temperature_command_topic"] == "jeedom2ha/5100/temperature/set"
    assert payload["temperature_state_topic"] == "jeedom2ha/5100/temperature/state"
    assert payload["current_temperature_topic"] == "jeedom2ha/5100/current_temperature"
    assert "modes" in payload
    assert "off" in payload["modes"]


@pytest.mark.asyncio
async def test_publish_climate_without_current_temperature():
    bridge = MagicMock()
    bridge.publish_message = MagicMock(return_value=True)
    publisher = DiscoveryPublisher(bridge)

    mapping = _make_climate_mapping(eq_id=5101, with_temperature=False)
    snapshot = _make_snapshot_for(5101)

    result = await publisher.publish_climate(mapping, snapshot)

    assert result is True
    payload = json.loads(bridge.publish_message.call_args[0][1])
    assert "current_temperature_topic" not in payload


@pytest.mark.asyncio
async def test_publish_climate_returns_false_on_bridge_failure():
    bridge = MagicMock()
    bridge.publish_message = MagicMock(return_value=False)
    publisher = DiscoveryPublisher(bridge)

    mapping = _make_climate_mapping(5102)
    snapshot = _make_snapshot_for(5102)

    result = await publisher.publish_climate(mapping, snapshot)

    assert result is False


# ---------------------------------------------------------------------------
# PublisherRegistry — climate enregistré (AC2)
# ---------------------------------------------------------------------------

def test_publisher_registry_includes_climate():
    known = PublisherRegistry.known_types()
    assert "climate" in known


def test_publisher_registry_resolves_climate():
    bridge = MagicMock()
    bridge.publish_message = MagicMock(return_value=True)
    publisher = DiscoveryPublisher(bridge)
    registry = PublisherRegistry(publisher)

    method = registry.resolve("climate")
    assert method is not None
    assert callable(method)


# ---------------------------------------------------------------------------
# validate_projection — gate FR40/NFR10 (AC3)
# ---------------------------------------------------------------------------

def test_validate_projection_climate_nominal():
    result = validate_projection("climate", ClimateCapabilities(has_setpoint=True))

    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_fields == []
    assert result.missing_capabilities == []


def test_validate_projection_climate_failure_missing_setpoint():
    result = validate_projection("climate", ClimateCapabilities(has_setpoint=False))

    assert result.is_valid is False
    assert result.reason_code == "ha_missing_temperature_command_topic"
    assert "temperature_command_topic" in result.missing_fields
    assert "has_setpoint" in result.missing_capabilities


# ---------------------------------------------------------------------------
# Non-régression — types historiques non affectés (AC3)
# ---------------------------------------------------------------------------

def test_validate_projection_non_regression_existing_types():
    from models.mapping import LightCapabilities, SwitchCapabilities, SensorCapabilities

    assert validate_projection("light",  LightCapabilities(has_on_off=True)).is_valid is True
    assert validate_projection("switch", SwitchCapabilities(has_on_off=True)).is_valid is True
    assert validate_projection("sensor", SensorCapabilities(has_state=True)).is_valid is True
