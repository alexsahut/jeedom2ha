"""Story 23.3 (vague 3) — runtime state streaming for light and cover.

Synthetic identifiers only (CC-48). Covers: translation (ON/OFF, brightness, open/closed,
position), several topics per command and several commands per entity, per-channel
reliability shared by discovery / state / command sync, conditional ``optimistic`` in
discovery, retained purge on republication, and the /action/state_update route.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from discovery.publisher import DiscoveryPublisher
from models.mapping import (
    CoverCapabilities,
    LightCapabilities,
    MappingResult,
    PublicationDecision,
)
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from sync import readback
from sync.command import CommandSynchronizer
from sync.state import _READBACK_KEYS, StateSynchronizer
from transport.http_server import create_app

SECRET = "test-secret-23.3"


class _FakeBridge:
    def __init__(self, connected=True, publish_ok=True):
        self.is_connected = connected
        self._publish_ok = publish_ok
        self.published: list[tuple[str, str, int, bool]] = []

    def publish_message(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return self._publish_ok


def _cmd(cmd_id, generic_type, type_="info", sub_type="binary", value=None):
    return JeedomCmd(id=cmd_id, name=generic_type, generic_type=generic_type,
                     type=type_, sub_type=sub_type, current_value=value)


def _decision(mapping, eq_id, published=True):
    decision = PublicationDecision(
        should_publish=published, reason="sure", mapping_result=mapping,
        state_topic=f"jeedom2ha/{eq_id}/state", discovery_published=published,
    )
    mapping.publication_decision_ref = decision
    return decision


def _light(eq_id=300, *, state=True, brightness=True, state_sub="binary",
           state_value="1", brightness_value="40", published=True, has_brightness=None):
    commands = {
        "LIGHT_ON": _cmd(eq_id * 10 + 1, "LIGHT_ON", "action", "other"),
        "LIGHT_OFF": _cmd(eq_id * 10 + 2, "LIGHT_OFF", "action", "other"),
    }
    if state:
        commands["LIGHT_STATE"] = _cmd(eq_id * 10 + 3, "LIGHT_STATE",
                                       sub_type=state_sub, value=state_value)
    if brightness:
        commands["LIGHT_SLIDER"] = _cmd(eq_id * 10 + 4, "LIGHT_SLIDER", "action", "slider")
        commands["LIGHT_BRIGHTNESS"] = _cmd(eq_id * 10 + 5, "LIGHT_BRIGHTNESS",
                                            sub_type="numeric", value=brightness_value)
    caps = LightCapabilities(
        has_on_off=True,
        has_brightness=brightness if has_brightness is None else has_brightness,
        on_off_confidence="sure",
    )
    mapping = MappingResult(
        ha_entity_type="light", confidence="sure", reason_code="light_on_off_brightness",
        jeedom_eq_id=eq_id, ha_unique_id=f"jeedom2ha_eq_{eq_id}", ha_name=f"Light {eq_id}",
        commands=commands, capabilities=caps,
    )
    return _decision(mapping, eq_id, published)


def _cover(eq_id=400, *, state="FLAP_STATE", state_sub="numeric", position=True,
           state_value="50", published=True):
    commands = {
        "FLAP_UP": _cmd(eq_id * 10 + 1, "FLAP_UP", "action", "other"),
        "FLAP_DOWN": _cmd(eq_id * 10 + 2, "FLAP_DOWN", "action", "other"),
    }
    if state:
        commands[state] = _cmd(eq_id * 10 + 3, state, sub_type=state_sub, value=state_value)
    if position:
        commands["FLAP_SLIDER"] = _cmd(eq_id * 10 + 4, "FLAP_SLIDER", "action", "slider")
    caps = CoverCapabilities(has_open_close=True, has_position=position,
                             open_close_confidence="sure")
    mapping = MappingResult(
        ha_entity_type="cover", confidence="sure", reason_code="cover_open_close_position",
        jeedom_eq_id=eq_id, ha_unique_id=f"jeedom2ha_eq_{eq_id}", ha_name=f"Cover {eq_id}",
        commands=commands, capabilities=caps,
    )
    return _decision(mapping, eq_id, published)


def _sync(decisions, bridge=None):
    publications = {d.mapping_result.jeedom_eq_id: d for d in decisions}
    return StateSynchronizer(app={"publications": publications},
                             mqtt_bridge=bridge or _FakeBridge())


# --- light: ON/OFF + brightness ---------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("value,expected", [("1", "ON"), ("0", "OFF"), ("on", "ON"), ("off", "OFF")])
async def test_light_state_translated_to_on_off(value, expected):
    bridge = _FakeBridge()
    sync = _sync([_light(300)], bridge)
    assert await sync.handle_state_message(300, 3003, value) is True
    assert bridge.published == [("jeedom2ha/300/state", expected, 1, True)]


@pytest.mark.asyncio
@pytest.mark.parametrize("value,expected", [("0", "OFF"), ("1", "ON"), ("50", "ON"), ("0.0", "OFF")])
async def test_numeric_light_state_is_a_level_not_a_binary(value, expected):
    bridge = _FakeBridge()
    sync = _sync([_light(300, brightness=False, state_sub="numeric")], bridge)
    await sync.handle_state_message(300, 3003, value)
    assert bridge.published == [("jeedom2ha/300/state", expected, 1, True)]


@pytest.mark.asyncio
@pytest.mark.parametrize("value,expected", [
    ("0", "0"), ("1", "1"), ("50", "50"), ("100", "100"), ("50.4", "50"), ("50.5", "51"),
    ("42,0", "42"),
])
async def test_light_brightness_integer_0_100(value, expected):
    bridge = _FakeBridge()
    sync = _sync([_light(300)], bridge)
    assert await sync.handle_state_message(300, 3005, value) is True
    assert bridge.published == [("jeedom2ha/300/brightness", expected, 1, True)]


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["101", "-1", "abc", "nan", "inf", "", None])
async def test_light_brightness_invalid_publishes_nothing(value):
    bridge = _FakeBridge()
    sync = _sync([_light(300)], bridge)
    assert await sync.handle_state_message(300, 3005, value) is False
    assert bridge.published == []


@pytest.mark.asyncio
async def test_brightness_does_not_touch_state_topic():
    bridge = _FakeBridge()
    sync = _sync([_light(300)], bridge)
    await sync.handle_state_message(300, 3005, "0")
    assert [p[0] for p in bridge.published] == ["jeedom2ha/300/brightness"]


def test_light_with_both_commands_has_two_listeners():
    targets = _sync([_light(300)]).list_state_targets()
    assert targets == [
        {"eq_id": 300, "cmd_id": 3003, "ha_type": "light", "state_topic": "jeedom2ha/300/state"},
        {"eq_id": 300, "cmd_id": 3005, "ha_type": "light",
         "state_topic": "jeedom2ha/300/brightness"},
    ]


def test_light_with_state_only_has_one_listener():
    targets = _sync([_light(300, brightness=False)]).list_state_targets()
    assert [t["cmd_id"] for t in targets] == [3003]


def test_light_with_brightness_only_has_brightness_listener_only():
    targets = _sync([_light(300, state=False)]).list_state_targets()
    assert [(t["cmd_id"], t["state_topic"]) for t in targets] == [
        (3005, "jeedom2ha/300/brightness")]


def test_light_without_any_readback_has_no_listener():
    assert _sync([_light(300, state=False, brightness=False)]).list_state_targets() == []


def test_light_brightness_needs_the_brightness_capability():
    # discovery declares no brightness topic without ``has_brightness``: no listener either.
    targets = _sync([_light(300, has_brightness=False)]).list_state_targets()
    assert [t["cmd_id"] for t in targets] == [3003]


def test_unpublished_light_is_not_a_target():
    assert _sync([_light(300, published=False)]).list_state_targets() == []


@pytest.mark.asyncio
async def test_light_initial_states_publish_state_and_brightness():
    bridge = _FakeBridge()
    decision = _light(300, state_value="1", brightness_value="75")
    sync = _sync([decision], bridge)
    assert await sync.publish_initial_states(decision) == 2
    assert ("jeedom2ha/300/state", "ON", 1, True) in bridge.published
    assert ("jeedom2ha/300/brightness", "75", 1, True) in bridge.published


# --- cover: open/closed + position ------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("value,state,position", [
    ("0", "closed", "0"), ("50", "open", "50"), ("100", "open", "100"),
])
async def test_numeric_flap_state_feeds_state_and_position(value, state, position):
    bridge = _FakeBridge()
    sync = _sync([_cover(400)], bridge)
    assert await sync.handle_state_message(400, 4003, value) is True
    assert bridge.published == [
        ("jeedom2ha/400/state", state, 1, True),
        ("jeedom2ha/400/position", position, 1, True),
    ]


@pytest.mark.asyncio
async def test_numeric_flap_state_out_of_range_publishes_nothing():
    bridge = _FakeBridge()
    sync = _sync([_cover(400)], bridge)
    assert await sync.handle_state_message(400, 4003, "150") is False
    assert await sync.handle_state_message(400, 4003, "abc") is False
    assert bridge.published == []


@pytest.mark.asyncio
@pytest.mark.parametrize("value,expected", [
    ("1", "open"), ("open", "open"), ("0", "closed"), ("closed", "closed"),
])
async def test_binary_flap_state_feeds_state_only(value, expected):
    bridge = _FakeBridge()
    sync = _sync([_cover(400, state_sub="binary")], bridge)
    assert await sync.handle_state_message(400, 4003, value) is True
    assert bridge.published == [("jeedom2ha/400/state", expected, 1, True)]


@pytest.mark.asyncio
async def test_binary_flap_state_unrecognised_value_publishes_nothing():
    bridge = _FakeBridge()
    sync = _sync([_cover(400, state_sub="binary")], bridge)
    assert await sync.handle_state_message(400, 4003, "moving") is False
    assert bridge.published == []


@pytest.mark.asyncio
async def test_bso_state_feeds_state_without_position():
    bridge = _FakeBridge()
    sync = _sync([_cover(400, state="FLAP_BSO_STATE", state_sub="binary", position=False)], bridge)
    assert await sync.handle_state_message(400, 4003, "1") is True
    assert bridge.published == [("jeedom2ha/400/state", "open", 1, True)]


@pytest.mark.asyncio
async def test_cover_without_position_capability_publishes_state_only():
    bridge = _FakeBridge()
    sync = _sync([_cover(400, position=False)], bridge)
    await sync.handle_state_message(400, 4003, "30")
    assert [p[0] for p in bridge.published] == ["jeedom2ha/400/state"]


def test_shared_command_is_one_listener_with_state_topic():
    assert _sync([_cover(400)]).list_state_targets() == [
        {"eq_id": 400, "cmd_id": 4003, "ha_type": "cover", "state_topic": "jeedom2ha/400/state"},
    ]


def test_cover_without_flap_state_has_no_listener():
    assert _sync([_cover(400, state=None)]).list_state_targets() == []


def test_action_command_is_never_a_state_target():
    decision = _cover(400)
    decision.mapping_result.commands["FLAP_STATE"].type = "action"
    assert _sync([decision]).list_state_targets() == []


@pytest.mark.asyncio
async def test_cover_initial_states_publish_state_and_position():
    bridge = _FakeBridge()
    decision = _cover(400, state_value="0")
    sync = _sync([decision], bridge)
    assert await sync.publish_initial_states(decision) == 2
    assert bridge.published == [
        ("jeedom2ha/400/state", "closed", 1, True),
        ("jeedom2ha/400/position", "0", 1, True),
    ]


@pytest.mark.asyncio
async def test_partial_publish_failure_is_not_reported_as_success():
    class _Flaky(_FakeBridge):
        def publish_message(self, topic, payload, qos=0, retain=False):
            self.published.append((topic, payload, qos, retain))
            return not topic.endswith("/position")

    sync = _sync([_cover(400)], _Flaky())
    assert await sync.handle_state_message(400, 4003, "50") is False


# --- per-channel reliability, shared by discovery / state / command sync -----

def _cmd_sync_for(decisions):
    state_sync = _sync(decisions)
    cmd_sync = CommandSynchronizer(app={"state_synchronizer": state_sync},
                                   mqtt_bridge=_FakeBridge(), jeedom_api_endpoint="http://x/api")
    return cmd_sync


def test_brightness_alone_does_not_make_on_off_reliable():
    decision = _light(300, state=False)
    assert _cmd_sync_for([decision])._has_reliable_state(decision.mapping_result, decision) is False
    assert readback.has_reliable_channel("light", decision.mapping_result, "brightness") is True
    assert readback.has_reliable_channel("light", decision.mapping_result, "state") is False


def test_light_state_makes_on_off_reliable():
    decision = _light(300, brightness=False)
    assert _cmd_sync_for([decision])._has_reliable_state(decision.mapping_result, decision) is True


def test_command_sync_and_state_sync_agree_on_every_streamed_entity():
    # Drift guard: whenever the command sync suppresses the optimistic publish, the
    # state sync has a real listener on the state topic of that entity (and vice versa).
    variants = [
        _light(301), _light(302, state=False), _light(303, brightness=False),
        _light(304, state=False, brightness=False),
        _cover(401), _cover(402, state=None), _cover(403, state="FLAP_BSO_STATE",
                                                     state_sub="binary", position=False),
    ]
    for decision in variants:
        eq_id = decision.mapping_result.jeedom_eq_id
        reliable = _cmd_sync_for([decision])._has_reliable_state(decision.mapping_result, decision)
        state_listeners = [
            t for t in _sync([decision]).list_state_targets()
            if t["state_topic"] == f"jeedom2ha/{eq_id}/state"
        ]
        assert reliable == bool(state_listeners), eq_id


def test_readback_keys_cover_every_readback_channel_key():
    assert set(readback.STATE_KEYS["light"]) | set(readback.BRIGHTNESS_KEYS) == set(
        _READBACK_KEYS["light"])
    assert set(readback.STATE_KEYS["cover"]) == set(_READBACK_KEYS["cover"])
    assert set(readback.STATE_KEYS["switch"]) == set(_READBACK_KEYS["switch"])


# --- discovery: conditional optimistic --------------------------------------

@pytest.fixture
def snapshot():
    eq = JeedomEqLogic(id=42, name="Synthetic", object_id=10, eq_type_name="virtual")
    return TopologySnapshot(timestamp="2026-10-12T00:00:00+00:00",
                            objects={10: JeedomObject(id=10, name="Room")}, eq_logics={42: eq})


async def _discovery_payload(mapping, snapshot, kind):
    bridge = MagicMock()
    bridge.publish_message = MagicMock(return_value=True)
    bridge.is_connected = True
    publisher = DiscoveryPublisher(bridge)
    await getattr(publisher, f"publish_{kind}")(mapping, snapshot)
    return json.loads(bridge.publish_message.call_args[0][1])


@pytest.mark.asyncio
@pytest.mark.parametrize("kwargs,optimistic", [
    ({}, False),
    ({"brightness": False}, False),
    ({"state": False}, True),                                  # brightness-only stays optimistic (Q4)
    ({"state": False, "brightness": False}, True),
])
async def test_light_discovery_optimistic_only_without_real_state(snapshot, kwargs, optimistic):
    mapping = _light(42, **kwargs).mapping_result
    payload = await _discovery_payload(mapping, snapshot, "light")
    assert payload["optimistic"] is optimistic
    assert payload["state_topic"] == "jeedom2ha/42/state"  # Q1 (b): topic kept


@pytest.mark.asyncio
@pytest.mark.parametrize("kwargs,optimistic", [
    ({}, False),
    ({"state": "FLAP_BSO_STATE", "state_sub": "binary", "position": False}, False),
    ({"state": None}, True),
])
async def test_cover_discovery_optimistic_only_without_real_state(snapshot, kwargs, optimistic):
    mapping = _cover(42, **kwargs).mapping_result
    payload = await _discovery_payload(mapping, snapshot, "cover")
    assert payload["optimistic"] is optimistic
    assert payload["state_topic"] == "jeedom2ha/42/state"


# --- retained purge at (re)publication (Q7) ---------------------------------

class _ScanBridge(_FakeBridge):
    """Bridge able to read the retained topics (``collect_retained_topics``)."""

    def __init__(self, retained, **kwargs):
        super().__init__(**kwargs)
        self._retained = retained
        self.collect_calls = 0

    async def collect_retained_topics(self, topic_filter, window_s=1.5):
        self.collect_calls += 1
        return list(self._retained)


@pytest.mark.asyncio
async def test_stale_retained_found_at_broker_is_emptied_once():
    bridge = _ScanBridge(["jeedom2ha/300/state", "jeedom2ha/300/brightness"])
    decision = _light(300, state=False, brightness=False)
    sync = _sync([decision], bridge)
    await sync.publish_initial_states(decision)
    assert sorted(bridge.published) == [
        ("jeedom2ha/300/brightness", "", 1, True),
        ("jeedom2ha/300/state", "", 1, True),
    ]
    await sync.publish_initial_states(decision)
    assert len(bridge.published) == 2          # emptied once, not at every sync
    assert bridge.collect_calls == 1           # broker read once per process


@pytest.mark.asyncio
async def test_nothing_retained_means_no_purge_publication():
    bridge = _ScanBridge([])
    decision = _light(300, state=False, brightness=False)
    await _sync([decision], bridge).publish_initial_states(decision)
    assert bridge.published == []


@pytest.mark.asyncio
async def test_bridge_without_collection_costs_nothing():
    bridge = _FakeBridge()
    decision = _light(300, state=False, brightness=False)
    await _sync([decision], bridge).publish_initial_states(decision)
    assert bridge.published == []


@pytest.mark.asyncio
async def test_entity_keeping_its_readback_is_never_purged():
    bridge = _ScanBridge(["jeedom2ha/300/state", "jeedom2ha/300/brightness"])
    decision = _light(300)
    await _sync([decision], bridge).publish_initial_states(decision)
    assert all(p[1] != "" for p in bridge.published)


@pytest.mark.asyncio
async def test_only_strict_jeedom2ha_channel_topics_are_ever_emptied():
    bridge = _ScanBridge([
        "other/300/state", "jeedom2ha/300/set", "jeedom2ha/300/brightness/set",
        "jeedom2ha/300/availability", "jeedom2ha/300/5/state", "jeedom2ha/bridge/state",
    ])
    decision = _light(300, state=False, brightness=False)
    await _sync([decision], bridge).publish_initial_states(decision)
    assert bridge.published == []


@pytest.mark.asyncio
async def test_real_to_unreliable_transition_purges_what_we_published():
    bridge = _FakeBridge()                                     # no broker read needed
    decision = _cover(400)
    sync = _sync([decision], bridge)
    await sync.publish_initial_states(decision)               # real: state + position
    assert [p[1] for p in bridge.published] == ["open", "50"]

    del decision.mapping_result.commands["FLAP_STATE"]        # readback removed
    bridge.published.clear()
    await sync.publish_initial_states(decision)
    assert sorted(bridge.published) == [
        ("jeedom2ha/400/position", "", 1, True),
        ("jeedom2ha/400/state", "", 1, True),
    ]


@pytest.mark.asyncio
async def test_failed_purge_is_retried_at_next_publication():
    bridge = _ScanBridge(["jeedom2ha/300/state"], publish_ok=False)
    decision = _light(300, state=False, brightness=False)
    sync = _sync([decision], bridge)
    await sync.publish_initial_states(decision)
    bridge._publish_ok = True
    bridge.published.clear()
    await sync.publish_initial_states(decision)
    assert bridge.published == [("jeedom2ha/300/state", "", 1, True)]


@pytest.mark.asyncio
async def test_state_event_never_purges():
    bridge = _ScanBridge(["jeedom2ha/300/state"])
    decision = _light(300, state=False, brightness=False)
    sync = _sync([decision], bridge)
    await sync.handle_state_message(300, 3003, "1")
    assert bridge.published == []


# --- non-regression: sensors keep their own topics --------------------------

def test_light_never_writes_on_command_scoped_sensor_topic():
    decision = _light(300)
    targets = _sync([decision]).list_state_targets()
    assert all(t["state_topic"].count("/") == 2 for t in targets)


# --- route ------------------------------------------------------------------

@pytest.fixture
def route_bridge():
    return _FakeBridge()


@pytest.fixture
def app(route_bridge):
    app = create_app(local_secret=SECRET)
    app["mqtt_bridge"] = route_bridge
    app["publications"] = {300: _light(300), 400: _cover(400)}
    app["state_synchronizer"] = StateSynchronizer(app=app, mqtt_bridge=route_bridge)
    return app


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


async def test_state_update_route_publishes_cover_state_and_position(cli, route_bridge):
    resp = await cli.post("/action/state_update", headers={"X-Local-Secret": SECRET},
                          json={"eq_id": 400, "cmd_id": 4003, "value": "0"})
    assert resp.status == 200
    assert (await resp.json()) == {"status": "ok", "published": True}
    assert route_bridge.published == [
        ("jeedom2ha/400/state", "closed", 1, True),
        ("jeedom2ha/400/position", "0", 1, True),
    ]


async def test_state_listeners_route_lists_light_and_cover_commands(cli):
    resp = await cli.get("/system/state_listeners", headers={"X-Local-Secret": SECRET})
    assert resp.status == 200
    body = await resp.json()
    pairs = {(t["eq_id"], t["cmd_id"]) for t in body["listeners"]}
    assert pairs == {(300, 3003), (300, 3005), (400, 4003)}


async def test_command_then_real_state_without_optimistic_publication(app, route_bridge):
    # With a real LIGHT_STATE the command sync must not publish an optimistic state:
    # the only state publication is the one produced by the Jeedom event.
    decision = app["publications"][300]
    cmd_sync = CommandSynchronizer(app=app, mqtt_bridge=route_bridge,
                                   jeedom_api_endpoint="http://x/api")
    translation_policy = cmd_sync._select_confirmation_policy(
        decision.mapping_result, decision,
        type("T", (), {"command_family": "on_off"})(),
    )
    assert translation_policy == "real_state_confirmation"
    assert await app["state_synchronizer"].handle_state_message(300, 3003, "0") is True
    assert route_bridge.published == [("jeedom2ha/300/state", "OFF", 1, True)]


@pytest.mark.asyncio
async def test_failed_purge_is_counted_as_failed_republication():
    bridge = _ScanBridge(["jeedom2ha/300/state"], publish_ok=False)
    decision = _light(300, state=False, brightness=False)
    sync = _sync([decision], bridge)
    published, failed = await sync.publish_click_states(decision, {}, 0.0)
    assert (published, failed) == (0, 1)
