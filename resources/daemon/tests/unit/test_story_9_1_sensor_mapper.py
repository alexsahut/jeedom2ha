"""Story 9.1 - SensorMapper + publish_sensor + PublisherRegistry known_types."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from discovery.publisher import DiscoveryPublisher
from discovery.registry import PublisherRegistry
from mapping.sensor import SensorMapper
from models.mapping import SensorCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from validation.ha_component_registry import validate_projection


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-05-05T00:00:00Z",
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
    sub_type: str = "numeric",
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


def test_sensor_mapper_temperature_nominal():
    eq = _eq_with_cmd(7000, "Capteur temperature salon", 70001, "TEMPERATURE")

    mapping = SensorMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.ha_entity_type == "sensor"
    assert mapping.confidence == "sure"
    assert mapping.reason_code == "sensor_temperature"
    assert mapping.capabilities == SensorCapabilities(has_state=True)
    assert mapping.reason_details == {
        "device_class": "temperature",
        "unit_of_measurement": "°C",
    }


def test_sensor_mapper_humidity_nominal():
    eq = _eq_with_cmd(7001, "Capteur humidite sdb", 70011, "HUMIDITY")

    mapping = SensorMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.reason_code == "sensor_humidity"
    assert mapping.reason_details == {
        "device_class": "humidity",
        "unit_of_measurement": "%",
    }


def test_sensor_mapper_power_nominal():
    eq = _eq_with_cmd(7002, "Compteur puissance elec", 70021, "POWER")

    mapping = SensorMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.reason_code == "sensor_power"
    assert mapping.reason_details == {
        "device_class": "power",
        "unit_of_measurement": "W",
    }


def test_sensor_mapper_returns_none_when_no_matching_info_numeric():
    eq = _eq_with_cmd(7100, "Capteur texte", 71001, "GENERIC_INFO", sub_type="string")

    mapping = SensorMapper().map(eq, _snapshot(eq))

    assert mapping is None


def test_sensor_mapper_excludes_binary_subtype_even_if_generic_is_known():
    eq = _eq_with_cmd(7101, "Capteur binaire reserve story 9.2", 71011, "TEMPERATURE", sub_type="binary")

    mapping = SensorMapper().map(eq, _snapshot(eq))

    assert mapping is None


def test_sensor_mapper_excludes_action_commands():
    eq = _eq_with_cmd(7102, "Commande action", 71021, "TEMPERATURE", type_="action")

    mapping = SensorMapper().map(eq, _snapshot(eq))

    assert mapping is None


def test_sensor_mapping_projection_validation_is_valid():
    eq = _eq_with_cmd(7003, "Capteur CO2", 70031, "CO2")
    mapping = SensorMapper().map(eq, _snapshot(eq))
    assert mapping is not None

    result = validate_projection(mapping.ha_entity_type, mapping.capabilities)

    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_fields == []
    assert result.missing_capabilities == []


async def test_publish_sensor_payload_contains_required_fields_and_topic():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(mqtt_bridge)

    eq = _eq_with_cmd(7004, "Capteur luminosite", 70041, "BRIGHTNESS")
    snapshot = _snapshot(eq)
    mapping = SensorMapper().map(eq, snapshot)
    assert mapping is not None

    published = await publisher.publish_sensor(mapping, snapshot)

    assert published is True
    mqtt_bridge.publish_message.assert_called_once()
    topic, payload_json = mqtt_bridge.publish_message.call_args.args[:2]
    kwargs = mqtt_bridge.publish_message.call_args.kwargs

    assert topic == "homeassistant/sensor/jeedom2ha_7004/config"
    assert kwargs == {"qos": 1, "retain": True}

    payload = json.loads(payload_json)
    assert payload["name"] == "Capteur luminosite"
    assert payload["unique_id"] == "jeedom2ha_eq_7004"
    assert payload["object_id"] == "jeedom2ha_7004"
    assert payload["state_topic"] == "jeedom2ha/7004/state"
    assert payload["platform"] == "mqtt"
    assert payload["device_class"] == "illuminance"
    assert payload["unit_of_measurement"] == "lx"
    assert "device" in payload
    assert ("availability_topic" in payload) or ("availability" in payload)


def test_publisher_registry_known_types_includes_sensor():
    assert "sensor" in PublisherRegistry.known_types()
    assert PublisherRegistry.known_types() == ["light", "cover", "switch", "sensor", "binary_sensor"]
