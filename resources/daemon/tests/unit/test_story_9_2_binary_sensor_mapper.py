"""Story 9.2 - BinarySensorMapper + publish_binary_sensor + PublisherRegistry known_types."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from discovery.publisher import DiscoveryPublisher
from discovery.registry import PublisherRegistry
from mapping.binary_sensor import BinarySensorMapper
from models.mapping import SensorCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from validation.ha_component_registry import validate_projection


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-05-06T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={eq.id: eq},
    )


def _eq_with_cmd(
    eq_id: int,
    name: str,
    cmd_id: int,
    generic_type: str,
    *,
    type_: str = "info",
    sub_type: str = "binary",
) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=eq_id,
        name=name,
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            JeedomCmd(
                id=cmd_id,
                name=generic_type,
                generic_type=generic_type,
                type=type_,
                sub_type=sub_type,
            )
        ],
    )


# ---------------------------------------------------------------------------
# BinarySensorMapper — cas nominaux
# ---------------------------------------------------------------------------

def test_binary_sensor_mapper_presence_nominal():
    eq = _eq_with_cmd(8000, "Detecteur presence salon", 80001, "PRESENCE")

    mapping = BinarySensorMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.ha_entity_type == "binary_sensor"
    assert mapping.confidence == "sure"
    assert mapping.reason_code == "binary_sensor_presence"
    assert mapping.capabilities == SensorCapabilities(has_state=True)
    assert mapping.reason_details == {"device_class": "occupancy"}


def test_binary_sensor_mapper_opening_nominal():
    eq = _eq_with_cmd(8001, "Capteur ouverture porte entree", 80011, "OPENING")

    mapping = BinarySensorMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.reason_code == "binary_sensor_opening"
    assert mapping.reason_details == {"device_class": "door"}


def test_binary_sensor_mapper_smoke_nominal():
    eq = _eq_with_cmd(8002, "Detecteur fumee cuisine", 80021, "SMOKE")

    mapping = BinarySensorMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.reason_code == "binary_sensor_smoke"
    assert mapping.reason_details == {"device_class": "smoke"}


# ---------------------------------------------------------------------------
# BinarySensorMapper — cas négatifs / exclusions
# ---------------------------------------------------------------------------

def test_binary_sensor_mapper_returns_none_when_no_binary_info():
    eq = _eq_with_cmd(8100, "Capteur texte", 81001, "GENERIC_INFO", sub_type="string")

    mapping = BinarySensorMapper().map(eq, _snapshot(eq))

    assert mapping is None


def test_binary_sensor_mapper_excludes_numeric_subtype():
    eq = _eq_with_cmd(8101, "Capteur temperature", 81011, "TEMPERATURE", sub_type="numeric")

    mapping = BinarySensorMapper().map(eq, _snapshot(eq))

    assert mapping is None


def test_binary_sensor_mapper_excludes_action_commands():
    eq = _eq_with_cmd(8102, "Commande action", 81021, "PRESENCE", type_="action")

    mapping = BinarySensorMapper().map(eq, _snapshot(eq))

    assert mapping is None


def test_binary_sensor_mapper_returns_none_when_generic_type_not_in_map():
    eq = _eq_with_cmd(8103, "Capteur inconnu", 81031, "UNKNOWN_BINARY_TYPE")

    mapping = BinarySensorMapper().map(eq, _snapshot(eq))

    assert mapping is None


# ---------------------------------------------------------------------------
# Validation de projection
# ---------------------------------------------------------------------------

def test_binary_sensor_mapping_projection_validation_is_valid():
    eq = _eq_with_cmd(8003, "Capteur inondation cave", 80031, "FLOOD")
    mapping = BinarySensorMapper().map(eq, _snapshot(eq))
    assert mapping is not None

    result = validate_projection(mapping.ha_entity_type, mapping.capabilities)

    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_fields == []
    assert result.missing_capabilities == []


# ---------------------------------------------------------------------------
# Coexistence binary + numeric → BinarySensorMapper gagne
# ---------------------------------------------------------------------------

def test_binary_sensor_wins_over_sensor_when_both_present():
    presence_cmd = JeedomCmd(
        id=80041,
        name="PRESENCE",
        generic_type="PRESENCE",
        type="info",
        sub_type="binary",
    )
    temperature_cmd = JeedomCmd(
        id=80042,
        name="TEMPERATURE",
        generic_type="TEMPERATURE",
        type="info",
        sub_type="numeric",
    )
    eq = JeedomEqLogic(
        id=8004,
        name="Capteur mixte presence temperature",
        object_id=1,
        eq_type_name="virtual",
        cmds=[presence_cmd, temperature_cmd],
    )
    snapshot = _snapshot(eq)

    mapping = BinarySensorMapper().map(eq, snapshot)

    assert mapping is not None
    assert mapping.ha_entity_type == "binary_sensor"
    assert mapping.reason_code == "binary_sensor_presence"


# ---------------------------------------------------------------------------
# publish_binary_sensor
# ---------------------------------------------------------------------------

async def test_publish_binary_sensor_payload_contains_required_fields_and_topic():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(mqtt_bridge)

    eq = _eq_with_cmd(8000, "Detecteur presence salon", 80001, "PRESENCE")
    snapshot = _snapshot(eq)
    mapping = BinarySensorMapper().map(eq, snapshot)
    assert mapping is not None

    published = await publisher.publish_binary_sensor(mapping, snapshot)

    assert published is True
    mqtt_bridge.publish_message.assert_called_once()
    topic, payload_json = mqtt_bridge.publish_message.call_args.args[:2]
    kwargs = mqtt_bridge.publish_message.call_args.kwargs

    assert topic == "homeassistant/binary_sensor/jeedom2ha_8000/config"
    assert kwargs == {"qos": 1, "retain": True}

    payload = json.loads(payload_json)
    assert payload["name"] == "Detecteur presence salon"
    assert payload["unique_id"] == "jeedom2ha_eq_8000"
    assert payload["object_id"] == "jeedom2ha_8000"
    assert payload["state_topic"] == "jeedom2ha/8000/state"
    assert payload["platform"] == "mqtt"
    assert payload["device_class"] == "occupancy"
    assert "device" in payload
    assert ("availability_topic" in payload) or ("availability" in payload)
    assert "unit_of_measurement" not in payload


async def test_publish_binary_sensor_device_class_absent_when_none():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(mqtt_bridge)

    eq = _eq_with_cmd(8010, "Base etat", 80101, "DOCK_STATE")
    snapshot = _snapshot(eq)
    mapping = BinarySensorMapper().map(eq, snapshot)
    assert mapping is not None
    assert mapping.reason_details == {"device_class": None}

    await publisher.publish_binary_sensor(mapping, snapshot)

    _, payload_json = mqtt_bridge.publish_message.call_args.args[:2]
    payload = json.loads(payload_json)
    assert "device_class" not in payload


async def test_publish_binary_sensor_topic_format():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(mqtt_bridge)

    eq = _eq_with_cmd(8001, "Capteur ouverture", 80011, "OPENING")
    snapshot = _snapshot(eq)
    mapping = BinarySensorMapper().map(eq, snapshot)
    assert mapping is not None

    await publisher.publish_binary_sensor(mapping, snapshot)

    topic, _ = mqtt_bridge.publish_message.call_args.args[:2]
    assert topic == "homeassistant/binary_sensor/jeedom2ha_8001/config"


# ---------------------------------------------------------------------------
# PublisherRegistry.known_types
# ---------------------------------------------------------------------------

def test_publisher_registry_known_types_includes_binary_sensor():
    assert PublisherRegistry.known_types() == ["light", "cover", "switch", "sensor", "binary_sensor", "button"]
