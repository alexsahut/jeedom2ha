"""Story 13.3 - metering plugs keep their switch and expose secondary sensors."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from discovery.publisher import DiscoveryPublisher
from mapping.registry import MapperRegistry
from mapping.sensor import SensorMapper
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot


def _cmd(cmd_id, name, cmd_type, sub_type, generic_type=None, unit=None, value=None):
    return JeedomCmd(
        id=cmd_id,
        name=name,
        type=cmd_type,
        sub_type=sub_type,
        generic_type=generic_type,
        unit=unit,
        current_value=value,
    )


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-07-01T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Bureau")},
        eq_logics={eq.id: eq},
    )


def _metering_plug(eq_id: int = 13300) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=eq_id,
        name="Prise bureau",
        object_id=1,
        eq_type_name="prise",
        cmds=[
            _cmd(133001, "On", "action", "other", "ENERGY_ON"),
            _cmd(133002, "Off", "action", "other", "ENERGY_OFF"),
            _cmd(133003, "Etat", "info", "binary", "ENERGY_STATE", value="1"),
            _cmd(133004, "Conso W", "info", "numeric", None, "W", 42),
        ],
    )


def test_registry_returns_primary_switch_then_single_power_sensor():
    eq = _metering_plug()

    results = MapperRegistry().map_all(eq, _snapshot(eq))

    assert [result.ha_entity_type for result in results] == ["switch", "sensor"]

    switch = results[0]
    assert switch.ha_unique_id == "jeedom2ha_eq_13300"
    assert switch.reason_details.get("object_id") is None
    assert switch.commands["ENERGY_ON"].id == 133001
    assert switch.commands["ENERGY_OFF"].id == 133002
    assert switch.commands["ENERGY_STATE"].id == 133003

    sensor = results[1]
    assert sensor.ha_unique_id == "jeedom2ha_eq_13300_cmd_133004"
    assert sensor.commands == {"133004": eq.cmds[3]}
    assert sensor.reason_details["object_id"] == "jeedom2ha_13300_133004"
    assert sensor.reason_details["node_id"] == "jeedom2ha_13300_133004"
    assert sensor.reason_details["state_topic"] == "jeedom2ha/13300/133004/state"
    assert sensor.reason_details["device_class"] == "power"
    assert sensor.reason_details["unit_of_measurement"] == "W"
    assert sensor.reason_details["state_class"] == "measurement"


def test_registry_map_keeps_switch_primary_unique_id_and_attaches_secondary_sensor():
    eq = _metering_plug()

    primary = MapperRegistry().map(eq, _snapshot(eq))

    assert primary is not None
    assert primary.ha_entity_type == "switch"
    assert primary.ha_unique_id == "jeedom2ha_eq_13300"
    assert primary.additional_mappings
    assert [mapping.ha_unique_id for mapping in primary.additional_mappings] == [
        "jeedom2ha_eq_13300_cmd_133004"
    ]


def test_sensor_mapper_excludes_actionable_energy_state_readback():
    eq = JeedomEqLogic(
        id=13310,
        name="Prise atelier",
        object_id=1,
        eq_type_name="prise",
        cmds=[
            _cmd(133101, "On", "action", "other", "ENERGY_ON"),
            _cmd(133102, "Off", "action", "other", "ENERGY_OFF"),
            _cmd(133103, "Etat", "info", "numeric", "ENERGY_STATE", "W", 1),
            _cmd(133104, "Conso W", "info", "numeric", None, "W", 42),
        ],
    )

    mappings = SensorMapper().map_all(eq, _snapshot(eq))

    assert [mapping.reason_details["cmd_id"] for mapping in mappings] == [133104]
    assert all("ENERGY_STATE" not in mapping.commands for mapping in mappings)


def test_switch_with_unreliable_unit_stays_single_primary_switch():
    eq = JeedomEqLogic(
        id=13320,
        name="Prise cave",
        object_id=1,
        eq_type_name="prise",
        cmds=[
            _cmd(133201, "On", "action", "other", "ENERGY_ON"),
            _cmd(133202, "Off", "action", "other", "ENERGY_OFF"),
            _cmd(133203, "Etat", "info", "binary", "ENERGY_STATE"),
            _cmd(133204, "Humidite", "info", "numeric", None, "%", 55),
        ],
    )

    results = MapperRegistry().map_all(eq, _snapshot(eq))

    assert len(results) == 1
    assert results[0].ha_entity_type == "switch"
    assert results[0].ha_unique_id == "jeedom2ha_eq_13320"


async def test_secondary_sensor_discovery_uses_command_identity_and_common_device():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(mqtt_bridge)
    eq = _metering_plug()
    sensor = MapperRegistry().map_all(eq, _snapshot(eq))[1]

    assert await publisher.publish_sensor(sensor, _snapshot(eq)) is True

    topic, payload_json = mqtt_bridge.publish_message.call_args.args[:2]
    payload = json.loads(payload_json)
    assert topic == "homeassistant/sensor/jeedom2ha_13300_133004/config"
    assert payload["unique_id"] == "jeedom2ha_eq_13300_cmd_133004"
    assert payload["object_id"] == "jeedom2ha_13300_133004"
    assert payload["state_topic"] == "jeedom2ha/13300/133004/state"
    assert payload["device_class"] == "power"
    assert payload["state_class"] == "measurement"
    assert payload["device"]["identifiers"] == ["jeedom2ha_13300"]
