"""Story 13.1 - HA Energy metadata for power/energy sensors."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from discovery.publisher import DiscoveryPublisher
from mapping.sensor import SensorMapper
from models.mapping import MappingResult, SensorCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-06-30T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Local technique")},
        eq_logics={eq.id: eq},
    )


def _eq_with_cmd(
    *,
    eq_id: int,
    cmd_id: int,
    generic_type: str | None,
    unit: str | None,
    current_value: object = None,
    eq_type_name: str = "virtual",
) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=eq_id,
        name=f"Sensor {eq_id}",
        object_id=1,
        eq_type_name=eq_type_name,
        cmds=[
            JeedomCmd(
                id=cmd_id,
                name=f"Cmd {cmd_id}",
                generic_type=generic_type,
                type="info",
                sub_type="numeric",
                unit=unit,
                current_value=current_value,
            )
        ],
    )


def test_power_w_sensor_gets_measurement_state_class_without_unit_conversion():
    eq = _eq_with_cmd(
        eq_id=13001,
        cmd_id=130011,
        generic_type="POWER",
        unit="W",
        current_value=1234,
    )

    mapping = SensorMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.reason_details == {
        "device_class": "power",
        "unit_of_measurement": "W",
        "state_class": "measurement",
    }
    assert mapping.commands["POWER"].current_value == 1234
    assert mapping.commands["POWER"].unit == "W"


def test_consumption_kwh_sensor_gets_total_increasing_state_class():
    eq = _eq_with_cmd(
        eq_id=13002,
        cmd_id=130021,
        generic_type="CONSUMPTION",
        unit="kWh",
        current_value=42.5,
    )

    mapping = SensorMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.reason_details == {
        "device_class": "energy",
        "unit_of_measurement": "kWh",
        "state_class": "total_increasing",
    }
    assert mapping.commands["CONSUMPTION"].current_value == 42.5
    assert mapping.commands["CONSUMPTION"].unit == "kWh"


def test_multi_sensor_wh_energy_gets_total_increasing_state_class():
    eq = _eq_with_cmd(
        eq_id=553,
        cmd_id=5171,
        generic_type=None,
        unit="Wh",
        current_value=9876,
        eq_type_name="msunpv",
    )

    mappings = SensorMapper().map_all(eq, _snapshot(eq))

    assert len(mappings) == 1
    assert mappings[0].reason_details["device_class"] == "energy"
    assert mappings[0].reason_details["unit_of_measurement"] == "Wh"
    assert mappings[0].reason_details["state_class"] == "total_increasing"


def test_non_power_energy_sensor_does_not_get_state_class():
    eq = _eq_with_cmd(
        eq_id=13003,
        cmd_id=130031,
        generic_type="TEMPERATURE",
        unit="°C",
    )

    mapping = SensorMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.reason_details == {
        "device_class": "temperature",
        "unit_of_measurement": "°C",
    }


async def test_publish_sensor_payload_includes_state_class_when_present():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(mqtt_bridge)
    eq = _eq_with_cmd(eq_id=13004, cmd_id=130041, generic_type="POWER", unit="W")
    snapshot = _snapshot(eq)
    mapping = SensorMapper().map(eq, snapshot)
    assert mapping is not None

    await publisher.publish_sensor(mapping, snapshot)

    payload = json.loads(mqtt_bridge.publish_message.call_args.args[1])
    assert payload["device_class"] == "power"
    assert payload["unit_of_measurement"] == "W"
    assert payload["state_class"] == "measurement"


async def test_publish_sensor_payload_omits_state_class_when_absent_or_none():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(mqtt_bridge)
    eq = _eq_with_cmd(eq_id=13005, cmd_id=130051, generic_type="TEMPERATURE", unit="°C")
    snapshot = _snapshot(eq)

    absent_mapping = MappingResult(
        ha_entity_type="sensor",
        confidence="sure",
        reason_code="sensor_temperature",
        jeedom_eq_id=eq.id,
        ha_unique_id=f"jeedom2ha_eq_{eq.id}",
        ha_name=eq.name,
        suggested_area="Local technique",
        commands={},
        capabilities=SensorCapabilities(has_state=True),
        reason_details={"device_class": "temperature", "unit_of_measurement": "°C"},
    )
    await publisher.publish_sensor(absent_mapping, snapshot)
    payload = json.loads(mqtt_bridge.publish_message.call_args.args[1])
    assert "state_class" not in payload

    none_mapping = MappingResult(
        ha_entity_type="sensor",
        confidence="sure",
        reason_code="sensor_temperature",
        jeedom_eq_id=eq.id,
        ha_unique_id=f"jeedom2ha_eq_{eq.id}",
        ha_name=eq.name,
        suggested_area="Local technique",
        commands={},
        capabilities=SensorCapabilities(has_state=True),
        reason_details={
            "device_class": "temperature",
            "unit_of_measurement": "°C",
            "state_class": None,
        },
    )
    await publisher.publish_sensor(none_mapping, snapshot)
    payload = json.loads(mqtt_bridge.publish_message.call_args.args[1])
    assert "state_class" not in payload
