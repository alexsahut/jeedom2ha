"""Story 11.3 - IQ EV + pilotage priorisation solaire multi-switch.

Les équipements virtuels énergie peuvent porter plusieurs switches logiques sur
un même eqLogic Jeedom. Chaque switch logique doit garder ses commandes On/Off,
son readback, ses topics discovery/command/state et ses listeners distincts.
"""

from __future__ import annotations

import pytest

from discovery.publisher import DiscoveryPublisher
from mapping.registry import MapperRegistry
from mapping.switch import SwitchMapper
from models.mapping import PublicationDecision
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot
from sync.command import CommandSynchronizer
from sync.state import StateSynchronizer


class _FakeBridge:
    def __init__(self, connected: bool = True):
        self.is_connected = connected
        self.published: list[tuple[str, str, int, bool]] = []

    def publish_message(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return True


class _NoopResponse:
    status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def text(self):
        return "OK"

    async def json(self, content_type=None):
        return {"result": True}


class _NoopSession:
    def __init__(self):
        self.calls: list[tuple[int, dict]] = []
        self.closed = False

    def post(self, url, json=None):
        params = (json or {}).get("params", {})
        self.calls.append((int(params["id"]), dict(params.get("options") or {})))
        return _NoopResponse()


def _cmd(cmd_id, name, generic_type, type_="info", sub_type="binary", current_value="0"):
    return JeedomCmd(
        id=cmd_id,
        name=name,
        generic_type=generic_type,
        type=type_,
        sub_type=sub_type,
        current_value=current_value,
    )


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(timestamp="2026-06-20T00:00:00", eq_logics={eq.id: eq})


def _iq_ev_eq() -> JeedomEqLogic:
    return JeedomEqLogic(
        id=583,
        name="IQ EV Charger",
        eq_type_name="virtual",
        cmds=[
            _cmd(6009, "Charge solaire (état)", "SWITCH_STATE", current_value="1"),
            _cmd(5999, "Charge solaire On", "SWITCH_ON", type_="action", sub_type="other"),
            _cmd(6001, "Charge solaire Off", "SWITCH_OFF", type_="action", sub_type="other"),
            _cmd(6010, "Charge manuelle (état)", "SWITCH_STATE", current_value="0"),
            _cmd(6000, "Charge manuelle On", "SWITCH_ON", type_="action", sub_type="other"),
            _cmd(6021, "Charge manuelle Off", "SWITCH_OFF", type_="action", sub_type="other"),
        ],
    )


def _priorisation_eq() -> JeedomEqLogic:
    triples = [
        (5977, 5978, 5979, "Filtration piscine"),
        (5980, 5981, 5982, "Chauffage piscine"),
        (5983, 5984, 5985, "Chauffage SPA"),
        (6004, 6005, 6006, "Charge voiture"),
    ]
    cmds = []
    for state_id, on_id, off_id, name in triples:
        cmds.extend([
            _cmd(state_id, name, "SWITCH_STATE", current_value="0"),
            _cmd(on_id, f"{name} On", "SWITCH_ON", type_="action", sub_type="other"),
            _cmd(off_id, f"{name} Off", "SWITCH_OFF", type_="action", sub_type="other"),
        ])
    return JeedomEqLogic(id=628, name="Pilotage priorisation solaire", eq_type_name="virtual", cmds=cmds)


def _decision(mapping, published=True):
    decision = PublicationDecision(
        should_publish=published,
        reason=mapping.confidence,
        mapping_result=mapping,
        state_topic=(mapping.reason_details or {}).get("state_topic") or f"jeedom2ha/{mapping.jeedom_eq_id}/state",
        active_or_alive=True,
        discovery_published=published,
    )
    mapping.publication_decision_ref = decision
    return decision


def _decisions_for_mapping(primary):
    decisions = {}
    for candidate in [primary, *primary.additional_mappings]:
        decision = _decision(candidate)
        decisions[(candidate.reason_details or {}).get("node_id", candidate.jeedom_eq_id)] = decision
    return decisions


def test_iq_ev_maps_two_distinct_switches_from_one_eqlogic():
    eq = _iq_ev_eq()
    results = SwitchMapper().map_all(eq, _snapshot(eq))

    assert len(results) == 2
    assert [r.ha_name for r in results] == ["Charge solaire", "Charge manuelle"]
    assert [r.ha_unique_id for r in results] == [
        "jeedom2ha_eq_583_cmd_6009",
        "jeedom2ha_eq_583_cmd_6010",
    ]
    assert [r.commands["ENERGY_STATE"].id for r in results] == [6009, 6010]
    assert [r.commands["ENERGY_ON"].id for r in results] == [5999, 6000]
    assert [r.commands["ENERGY_OFF"].id for r in results] == [6001, 6021]
    assert [r.reason_details["state_topic"] for r in results] == [
        "jeedom2ha/583/6009/state",
        "jeedom2ha/583/6010/state",
    ]
    assert [r.reason_details["command_topic"] for r in results] == [
        "jeedom2ha/583/6009/set",
        "jeedom2ha/583/6010/set",
    ]


def test_priorisation_maps_four_distinct_switches_from_one_eqlogic():
    eq = _priorisation_eq()
    primary = MapperRegistry().map(eq, _snapshot(eq))

    assert primary is not None
    all_mappings = [primary, *primary.additional_mappings]
    assert [m.ha_name for m in all_mappings] == [
        "Filtration piscine",
        "Chauffage piscine",
        "Chauffage SPA",
        "Charge voiture",
    ]
    assert [m.reason_details["cmd_id"] for m in all_mappings] == [5977, 5980, 5983, 6004]
    assert [m.reason_details["node_id"] for m in all_mappings] == [
        "jeedom2ha_628_5977",
        "jeedom2ha_628_5980",
        "jeedom2ha_628_5983",
        "jeedom2ha_628_6004",
    ]


@pytest.mark.asyncio
async def test_multi_switch_discovery_uses_node_scoped_topics_and_payload_topics():
    eq = _iq_ev_eq()
    mapping = SwitchMapper().map_all(eq, _snapshot(eq))[0]
    bridge = _FakeBridge()
    publisher = DiscoveryPublisher(bridge)

    ok = await publisher.publish_switch(mapping, _snapshot(eq))

    assert ok is True
    topic, payload_json, qos, retain = bridge.published[0]
    assert topic == "homeassistant/switch/jeedom2ha_583_6009/config"
    assert qos == 1
    assert retain is True
    assert '"object_id": "jeedom2ha_583_6009"' in payload_json
    assert '"command_topic": "jeedom2ha/583/6009/set"' in payload_json
    assert '"state_topic": "jeedom2ha/583/6009/state"' in payload_json


def test_multi_switch_state_targets_are_per_readback_command():
    eq = _iq_ev_eq()
    primary = MapperRegistry().map(eq, _snapshot(eq))
    decisions = _decisions_for_mapping(primary)
    sync = StateSynchronizer(app={"publications": decisions}, mqtt_bridge=_FakeBridge())

    assert sync.list_state_targets() == [
        {
            "eq_id": 583,
            "cmd_id": 6009,
            "ha_type": "switch",
            "state_topic": "jeedom2ha/583/6009/state",
        },
        {
            "eq_id": 583,
            "cmd_id": 6010,
            "ha_type": "switch",
            "state_topic": "jeedom2ha/583/6010/state",
        },
    ]


@pytest.mark.asyncio
async def test_multi_switch_state_update_and_initial_snapshot_use_own_topic():
    eq = _iq_ev_eq()
    primary = MapperRegistry().map(eq, _snapshot(eq))
    decisions = _decisions_for_mapping(primary)
    bridge = _FakeBridge()
    sync = StateSynchronizer(app={"publications": decisions}, mqtt_bridge=bridge)

    assert await sync.handle_state_message(eq_id=583, cmd_id=6010, value="1") is True
    assert bridge.published == [("jeedom2ha/583/6010/state", "ON", 1, True)]

    bridge.published.clear()
    count = await sync.publish_initial_states(primary.publication_decision_ref)

    assert count == 2
    assert bridge.published == [
        ("jeedom2ha/583/6009/state", "ON", 1, True),
        ("jeedom2ha/583/6010/state", "OFF", 1, True),
    ]


@pytest.mark.asyncio
async def test_multi_switch_command_topic_executes_matching_on_off_command():
    eq = _iq_ev_eq()
    primary = MapperRegistry().map(eq, _snapshot(eq))
    decisions = _decisions_for_mapping(primary)
    session = _NoopSession()
    sync = CommandSynchronizer(
        app={"publications": decisions, "state_synchronizer": StateSynchronizer({}, _FakeBridge())},
        mqtt_bridge=_FakeBridge(),
        jeedom_api_endpoint="http://jeedom/core/api/jeeApi.php",
        jeedom_core_apikey="secret",
    )
    sync._session = session

    assert await sync.handle_command_message("jeedom2ha/583/6010/set", "ON") is True
    assert await sync.handle_command_message("jeedom2ha/583/6010/set", "OFF") is True

    assert [cmd_id for cmd_id, _ in session.calls] == [6000, 6021]
