"""Story 11.3 — generic SWITCH_* multi-switch mapping.

IQ EV (eq583) and Pilotage priorisation solaire (eq628) are validation targets,
not semantic allowlists. SWITCH_* trios are grouped structurally by command-name
prefix and entity identity is derived from the SWITCH_STATE command id.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from discovery.publisher import DiscoveryPublisher
from mapping.binary_sensor import BinarySensorMapper
from mapping.registry import MapperRegistry
from mapping.sensor import SensorMapper
from mapping.switch import SwitchMapper
from models.decide_publication import decide_publication
from models.mapping import ProjectionValidity, PublicationDecision
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from sync.command import CommandSynchronizer
from sync.state import StateSynchronizer


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
        timestamp="2026-06-19T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Energie")},
        eq_logics={eq.id: eq},
    )


def _eq583() -> JeedomEqLogic:
    return JeedomEqLogic(
        id=583,
        name="IQ EV Charger",
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            _cmd(5986, "Branché", "info", "binary", "SWITCH_STATE", value="1"),
            _cmd(5988, "Connecté", "info", "binary", "SWITCH_STATE", value="1"),
            _cmd(5987, "Charge", "info", "binary", "SWITCH_STATE", value="0"),
            _cmd(5997, "Charge On", "action", "other", "SWITCH_ON"),
            _cmd(5998, "Charge Off", "action", "other", "SWITCH_OFF"),
            _cmd(6009, "Charge solaire", "info", "binary", "SWITCH_STATE", value="1"),
            _cmd(5999, "Charge solaire On", "action", "other", "SWITCH_ON"),
            _cmd(6001, "Charge solaire Off", "action", "other", "SWITCH_OFF"),
            _cmd(6010, "Charge manuelle", "info", "binary", "SWITCH_STATE", value="0"),
            _cmd(6000, "Charge manuelle On", "action", "other", "SWITCH_ON"),
            _cmd(6021, "Charge manuelle Off", "action", "other", "SWITCH_OFF"),
            _cmd(5991, "Puissance", "info", "numeric", "GENERIC_INFO", "W", "1200"),
            _cmd(5992, "Energie session", "info", "numeric", "GENERIC_INFO", "Wh", "42"),
            _cmd(5993, "Energie jour", "info", "numeric", "GENERIC_INFO", "Wh", "84"),
            _cmd(5989, "Etat connecteur", "info", "string", "GENERIC_INFO"),
            _cmd(6002, "Rafraichir", "action", "other"),
        ],
    )


def _eq628() -> JeedomEqLogic:
    return JeedomEqLogic(
        id=628,
        name="Pilotage priorisation solaire",
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            _cmd(5977, "Filtration piscine", "info", "binary", "SWITCH_STATE", value="1"),
            _cmd(5978, "Filtration piscine On", "action", "other", "SWITCH_ON"),
            _cmd(5979, "Filtration piscine Off", "action", "other", "SWITCH_OFF"),
            _cmd(5980, "Chauffage piscine", "info", "binary", "SWITCH_STATE", value="0"),
            _cmd(5981, "Chauffage piscine On", "action", "other", "SWITCH_ON"),
            _cmd(5982, "Chauffage piscine Off", "action", "other", "SWITCH_OFF"),
            _cmd(5983, "Chauffage SPA", "info", "binary", "SWITCH_STATE", value="0"),
            _cmd(5984, "Chauffage SPA On", "action", "other", "SWITCH_ON"),
            _cmd(5985, "Chauffage SPA Off", "action", "other", "SWITCH_OFF"),
            _cmd(6004, "Charge voiture", "info", "binary", "SWITCH_STATE", value="1"),
            _cmd(6005, "Charge voiture On", "action", "other", "SWITCH_ON"),
            _cmd(6006, "Charge voiture Off", "action", "other", "SWITCH_OFF"),
            _cmd(5976, "Rafraichir", "action", "other"),
        ],
    )


def test_eq583_maps_three_switches_three_sensors_two_binary_sensors():
    eq = _eq583()
    results = MapperRegistry().map_all(eq, _snapshot(eq))

    assert len(results) == 8
    assert [r.ha_entity_type for r in results].count("switch") == 3
    assert [r.ha_entity_type for r in results].count("sensor") == 3
    assert [r.ha_entity_type for r in results].count("binary_sensor") == 2

    switches = [r for r in results if r.ha_entity_type == "switch"]
    assert {r.reason_details["cmd_id"] for r in switches} == {5987, 6009, 6010}
    assert all(r.confidence == "probable" for r in switches)
    assert all(r.reason_details["node_id"] == f"jeedom2ha_583_{r.reason_details['cmd_id']}" for r in switches)

    binaries = BinarySensorMapper().map_all(eq, _snapshot(eq))
    assert {m.reason_details["cmd_id"] for m in binaries} == {5986, 5988}


def test_eq628_maps_four_structural_switches_only():
    eq = _eq628()
    results = MapperRegistry().map_all(eq, _snapshot(eq))

    assert len(results) == 4
    assert all(r.ha_entity_type == "switch" for r in results)
    assert {r.reason_details["cmd_id"] for r in results} == {5977, 5980, 5983, 6004}
    assert SensorMapper().map_all(eq, _snapshot(eq)) == []
    assert BinarySensorMapper().map_all(eq, _snapshot(eq)) == []


def test_generic_switch_star_multi_switch_is_not_id_scoped_and_respects_confidence_policy():
    eq = JeedomEqLogic(
        id=9009,
        name="Generic multi switch",
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            _cmd(90091, "Load A", "info", "binary", "SWITCH_STATE"),
            _cmd(90092, "Load A On", "action", "other", "SWITCH_ON"),
            _cmd(90093, "Load A Off", "action", "other", "SWITCH_OFF"),
            _cmd(90094, "Load B", "info", "binary", "SWITCH_STATE"),
            _cmd(90095, "Load B On", "action", "other", "SWITCH_ON"),
            _cmd(90096, "Load B Off", "action", "other", "SWITCH_OFF"),
        ],
    )

    mappings = SwitchMapper().map_all(eq, _snapshot(eq))

    assert len(mappings) == 2
    assert {m.reason_details["cmd_id"] for m in mappings} == {90091, 90094}
    assert all(m.confidence == "probable" for m in mappings)
    for mapping in mappings:
        mapping.projection_validity = ProjectionValidity(True, None, [], [])
    assert all(not decide_publication(m, confidence_policy="sure_only").should_publish for m in mappings)
    assert all(decide_publication(m, confidence_policy="sure_probable").should_publish for m in mappings)


async def test_publish_switch_multi_uses_per_command_topic_and_state_topic():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(mqtt_bridge)
    eq = _eq628()
    mapping = SwitchMapper().map_all(eq, _snapshot(eq))[0]

    assert await publisher.publish_switch(mapping, _snapshot(eq)) is True

    topic, payload_json = mqtt_bridge.publish_message.call_args.args[:2]
    payload = json.loads(payload_json)
    assert topic == "homeassistant/switch/jeedom2ha_628_5977/config"
    assert payload["unique_id"] == "jeedom2ha_eq_628_cmd_5977"
    assert payload["object_id"] == "jeedom2ha_628_5977"
    assert payload["command_topic"] == "jeedom2ha/628/5977/set"
    assert payload["state_topic"] == "jeedom2ha/628/5977/state"
    assert payload["device"]["identifiers"] == ["jeedom2ha_628"]


def test_state_synchronizer_lists_every_multi_switch_state_topic():
    eq = _eq628()
    primary = MapperRegistry().map(eq, _snapshot(eq))
    decision = PublicationDecision(
        should_publish=True,
        reason="probable",
        mapping_result=primary,
        state_topic=primary.reason_details["state_topic"],
        discovery_published=True,
    )
    primary.publication_decision_ref = decision
    for secondary in primary.additional_mappings:
        sec_decision = PublicationDecision(
            should_publish=True,
            reason="probable",
            mapping_result=secondary,
            state_topic=secondary.reason_details["state_topic"],
            discovery_published=True,
        )
        secondary.publication_decision_ref = sec_decision

    targets = StateSynchronizer({"publications": {628: decision}}, MagicMock()).list_state_targets()

    assert {(t["cmd_id"], t["state_topic"]) for t in targets} == {
        (5977, "jeedom2ha/628/5977/state"),
        (5980, "jeedom2ha/628/5980/state"),
        (5983, "jeedom2ha/628/5983/state"),
        (6004, "jeedom2ha/628/6004/state"),
    }


async def test_command_synchronizer_routes_multi_switch_node_command_topic():
    eq = _eq628()
    primary = MapperRegistry().map(eq, _snapshot(eq))
    decision = PublicationDecision(
        should_publish=True,
        reason="probable",
        mapping_result=primary,
        state_topic=primary.reason_details["state_topic"],
        active_or_alive=True,
        discovery_published=True,
    )
    primary.publication_decision_ref = decision
    for secondary in primary.additional_mappings:
        sec_decision = PublicationDecision(
            should_publish=True,
            reason="probable",
            mapping_result=secondary,
            state_topic=secondary.reason_details["state_topic"],
            active_or_alive=True,
            discovery_published=True,
        )
        secondary.publication_decision_ref = sec_decision

    bridge = MagicMock()
    bridge.is_connected = True
    sync = CommandSynchronizer(
        {"publications": {628: decision}},
        bridge,
        jeedom_api_endpoint="http://jeedom.test/core/api/jeeApi.php",
    )
    executed = []

    async def _fake_exec(cmd_id, options):
        executed.append((cmd_id, options))
        return True

    sync._execute_exec_cmd = _fake_exec  # type: ignore[method-assign]

    ok = await sync.handle_command_message("jeedom2ha/628/5980/set", "ON")

    assert ok is True
    assert executed == [(5981, {})]
