"""Unit tests for Jeedom -> HA runtime state streaming (Story 12.2, vague 2).

Vague 2 extends the streamed scope to the actionable ``switch`` (real on/off
readback via ``ENERGY_STATE``). ``button`` stays out of scope: it is stateless in
HA (no state_topic), so nothing is ever streamed for it. The optimistic-publish
path of the non-streamed actionable types (``light`` / ``cover``) must be
preserved (AC#6, AC#10): ``is_active`` is True but ``streams_actionable_type``
gates per type, and ``CommandSynchronizer._has_reliable_state`` honors it.
"""
from __future__ import annotations

import pytest

from resources.daemon.models.mapping import (
    CoverCapabilities,
    LightCapabilities,
    MappingResult,
    PublicationDecision,
    SwitchCapabilities,
)
from resources.daemon.models.topology import JeedomCmd
from resources.daemon.sync.command import CommandSynchronizer
from resources.daemon.sync.state import StateSynchronizer


class _FakeBridge:
    def __init__(self, connected: bool = True, publish_ok: bool = True):
        self.is_connected = connected
        self._publish_ok = publish_ok
        self.published: list[tuple[str, str, int, bool]] = []

    def publish_message(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return self._publish_ok


def _switch_decision(eq_id=554, state_cmd_id=5543, current_value="1", published=True):
    """eq554-like switch: ENERGY_ON/ENERGY_OFF actions + ENERGY_STATE info readback."""
    commands = {
        "ENERGY_ON": JeedomCmd(id=5541, name="On", generic_type="ENERGY_ON",
                               type="action", sub_type="other"),
        "ENERGY_OFF": JeedomCmd(id=5542, name="Off", generic_type="ENERGY_OFF",
                                type="action", sub_type="other"),
        "ENERGY_STATE": JeedomCmd(id=state_cmd_id, name="State",
                                  generic_type="ENERGY_STATE", type="info",
                                  sub_type="binary", current_value=current_value),
    }
    mapping = MappingResult(
        ha_entity_type="switch",
        confidence="sure",
        reason_code="switch_on_off_state",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Switch {eq_id}",
        commands=commands,
        capabilities=SwitchCapabilities(has_on_off=True, has_state=True,
                                        on_off_confidence="sure", device_class="outlet"),
    )
    decision = PublicationDecision(
        should_publish=published, reason="sure", mapping_result=mapping,
        state_topic=f"jeedom2ha/{eq_id}/state", discovery_published=published,
    )
    mapping.publication_decision_ref = decision
    return decision


def _switch_no_readback_decision(eq_id=560, published=True):
    """on_off_only switch: ENERGY_ON/ENERGY_OFF actions, NO ENERGY_STATE readback.

    Has no runtime state to stream; must never become a state target on an action
    command (CommandSynchronizer keeps it on the optimistic path)."""
    commands = {
        "ENERGY_ON": JeedomCmd(id=5601, name="On", generic_type="ENERGY_ON",
                               type="action", sub_type="other"),
        "ENERGY_OFF": JeedomCmd(id=5602, name="Off", generic_type="ENERGY_OFF",
                                type="action", sub_type="other"),
    }
    mapping = MappingResult(
        ha_entity_type="switch",
        confidence="probable",
        reason_code="switch_on_off_only",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Switch {eq_id}",
        commands=commands,
        capabilities=SwitchCapabilities(has_on_off=True, has_state=False,
                                        on_off_confidence="probable"),
    )
    decision = PublicationDecision(
        should_publish=published, reason="probable", mapping_result=mapping,
        state_topic=f"jeedom2ha/{eq_id}/state", discovery_published=published,
    )
    mapping.publication_decision_ref = decision
    return decision


def _button_decision(eq_id=700, cmd_id=7001):
    """Button: action-only, stateless (no state_topic) — must never stream state."""
    cmd = JeedomCmd(id=cmd_id, name="Trigger", generic_type="ACTION",
                    type="action", sub_type="other")
    mapping = MappingResult(
        ha_entity_type="button",
        confidence="sure",
        reason_code="button_action",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name="Bouton",
        commands={"ACTION": cmd},
        capabilities=SwitchCapabilities(has_on_off=True),
        reason_details={"command_topic": f"jeedom2ha/{eq_id}/cmd"},
    )
    decision = PublicationDecision(
        should_publish=True, reason="sure", mapping_result=mapping,
        state_topic="", discovery_published=True,
    )
    mapping.publication_decision_ref = decision
    return decision


def _light_decision(eq_id=300, cmd_id=7004):
    cmd = JeedomCmd(id=cmd_id, name="State", generic_type="LIGHT_STATE", type="info",
                    sub_type="binary", current_value="1")
    mapping = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name="Lampe",
        commands={"LIGHT_STATE": cmd},
        capabilities=LightCapabilities(has_on_off=True, on_off_confidence="sure"),
    )
    decision = PublicationDecision(
        should_publish=True, reason="sure", mapping_result=mapping,
        state_topic=f"jeedom2ha/{eq_id}/state", discovery_published=True,
    )
    mapping.publication_decision_ref = decision
    return decision


def _cover_mapping(eq_id=400, cmd_id=4005):
    return MappingResult(
        ha_entity_type="cover",
        confidence="sure",
        reason_code="cover_open_close_state",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name="Volet",
        commands={
            "FLAP_UP": JeedomCmd(id=4001, name="Up", generic_type="FLAP_UP",
                                 type="action", sub_type="other"),
            "FLAP_STATE": JeedomCmd(id=cmd_id, name="State", generic_type="FLAP_STATE",
                                    type="info", sub_type="numeric"),
        },
        capabilities=CoverCapabilities(has_open_close=True, open_close_confidence="sure"),
    )


def _sync(publications, bridge):
    return StateSynchronizer(app={"publications": publications}, mqtt_bridge=bridge)


def _cmd_sync():
    return CommandSynchronizer(app={}, mqtt_bridge=_FakeBridge(),
                               jeedom_api_endpoint="http://x/api")


# --- switch streaming on eq-level state_topic, ON/OFF translation (AC#1, AC#4) ---

@pytest.mark.asyncio
async def test_switch_publishes_on_off_on_eq_level_state_topic():
    decision = _switch_decision(eq_id=554, state_cmd_id=5543)
    bridge = _FakeBridge()
    sync = _sync({554: decision}, bridge)

    ok = await sync.handle_state_message(eq_id=554, cmd_id=5543, value="1")

    assert ok is True
    assert bridge.published == [("jeedom2ha/554/state", "ON", 1, True)]


@pytest.mark.parametrize("raw,expected", [("1", "ON"), ("0", "OFF"), ("true", "ON"),
                                          ("false", "OFF"), (1, "ON"), (0, "OFF"),
                                          ("on", "ON"), ("off", "OFF")])
@pytest.mark.asyncio
async def test_switch_translates_on_off(raw, expected):
    decision = _switch_decision(eq_id=554, state_cmd_id=5543)
    bridge = _FakeBridge()
    sync = _sync({554: decision}, bridge)

    ok = await sync.handle_state_message(eq_id=554, cmd_id=5543, value=raw)

    assert ok is True
    assert bridge.published == [("jeedom2ha/554/state", expected, 1, True)]


# --- switch readback uses ENERGY_STATE, not the action commands (AC#1) ---

@pytest.mark.asyncio
async def test_switch_action_cmd_id_is_not_a_state_target():
    """A value addressed to ENERGY_ON/ENERGY_OFF (actions) must be rejected: only
    the readback ENERGY_STATE info command feeds the switch state."""
    decision = _switch_decision(eq_id=554, state_cmd_id=5543)
    bridge = _FakeBridge()
    sync = _sync({554: decision}, bridge)

    assert await sync.handle_state_message(eq_id=554, cmd_id=5541, value="1") is False
    assert bridge.published == []


# --- initial snapshot reads the readback command (AC#2) ---

@pytest.mark.asyncio
async def test_switch_initial_snapshot_publishes_current_state():
    decision = _switch_decision(eq_id=554, state_cmd_id=5543, current_value="1")
    bridge = _FakeBridge()
    sync = _sync({554: decision}, bridge)

    count = await sync.publish_initial_states(decision)

    assert count == 1
    assert bridge.published == [("jeedom2ha/554/state", "ON", 1, True)]


@pytest.mark.asyncio
async def test_switch_initial_snapshot_skips_when_no_state_value():
    decision = _switch_decision(eq_id=554, state_cmd_id=5543, current_value=None)
    bridge = _FakeBridge()
    sync = _sync({554: decision}, bridge)

    assert await sync.publish_initial_states(decision) == 0
    assert bridge.published == []


# --- list_state_targets: switch in, button out (AC#3, AC#5) ---

def test_list_state_targets_includes_switch_state_cmd():
    sync = _sync({554: _switch_decision(eq_id=554, state_cmd_id=5543)}, _FakeBridge())

    targets = sync.list_state_targets()

    assert targets == [
        {"eq_id": 554, "cmd_id": 5543, "ha_type": "switch",
         "state_topic": "jeedom2ha/554/state"},
    ]


def test_list_state_targets_excludes_button():
    sync = _sync({
        554: _switch_decision(eq_id=554, state_cmd_id=5543),
        700: _button_decision(eq_id=700, cmd_id=7001),
    }, _FakeBridge())

    targets = sync.list_state_targets()

    assert not any(t["eq_id"] == 700 for t in targets)
    assert {(t["eq_id"], t["ha_type"]) for t in targets} == {(554, "switch")}


# --- switch without readback (on_off_only) is not a state target (AC#1) ---

def test_switch_without_readback_is_not_a_state_target():
    sync = _sync({560: _switch_no_readback_decision(eq_id=560)}, _FakeBridge())

    assert sync.list_state_targets() == []


@pytest.mark.asyncio
async def test_switch_without_readback_streams_nothing():
    """A value addressed to an action command of an on_off_only switch must never
    publish state (no readback = no runtime state — no faux readback)."""
    decision = _switch_no_readback_decision(eq_id=560)
    bridge = _FakeBridge()
    sync = _sync({560: decision}, bridge)

    assert await sync.handle_state_message(eq_id=560, cmd_id=5601, value="1") is False
    assert await sync.publish_initial_states(decision) == 0
    assert bridge.published == []


# --- state ⊆ discovery (AC#5) ---

@pytest.mark.asyncio
async def test_unpublished_switch_is_never_fed():
    decision = _switch_decision(eq_id=554, state_cmd_id=5543, published=False)
    bridge = _FakeBridge()
    sync = _sync({554: decision}, bridge)

    assert await sync.handle_state_message(eq_id=554, cmd_id=5543, value="1") is False
    assert bridge.published == []


# --- button is stateless: never streamed (AC#5) ---

@pytest.mark.asyncio
async def test_button_state_message_is_rejected():
    decision = _button_decision(eq_id=700, cmd_id=7001)
    bridge = _FakeBridge()
    sync = _sync({700: decision}, bridge)

    assert await sync.handle_state_message(eq_id=700, cmd_id=7001, value="1") is False
    assert bridge.published == []


# --- is_active / scope-aware streaming contract (AC#6, AC#8, AC#10) ---

def test_is_active_is_true_in_vague2():
    assert _sync({}, _FakeBridge()).is_active is True


@pytest.mark.parametrize("ha_type,streamed", [
    ("switch", True),
    ("light", False),
    ("cover", False),
    ("button", False),
    ("sensor", False),
    ("binary_sensor", False),
])
def test_streams_actionable_type_scope(ha_type, streamed):
    """Only the actionable types actually streamed (vague 2 = switch) return True.
    sensor/binary_sensor are streamed but are NOT actionable, so they are False
    here — this gate is exclusively about suppressing the optimistic command path."""
    assert _sync({}, _FakeBridge()).streams_actionable_type(ha_type) is streamed


# --- CommandSynchronizer honors the per-type scope (AC#6, AC#10) ---

def test_command_sync_switch_has_reliable_state():
    state_sync = _sync({}, _FakeBridge())
    cmd_sync = _cmd_sync()
    cmd_sync._app = {"state_synchronizer": state_sync}
    decision = _switch_decision(eq_id=554, state_cmd_id=5543)

    assert cmd_sync._has_reliable_state(decision.mapping_result, decision) is True


def test_command_sync_light_keeps_optimistic_path():
    """light is not streamed in vague 2 -> not reliable -> optimistic publish kept."""
    state_sync = _sync({}, _FakeBridge())
    cmd_sync = _cmd_sync()
    cmd_sync._app = {"state_synchronizer": state_sync}
    decision = _light_decision(eq_id=300, cmd_id=7004)

    assert cmd_sync._has_reliable_state(decision.mapping_result, decision) is False


def test_command_sync_cover_keeps_optimistic_path():
    state_sync = _sync({}, _FakeBridge())
    cmd_sync = _cmd_sync()
    cmd_sync._app = {"state_synchronizer": state_sync}
    mapping = _cover_mapping(eq_id=400, cmd_id=4005)
    decision = PublicationDecision(
        should_publish=True, reason="sure", mapping_result=mapping,
        state_topic="jeedom2ha/400/state", discovery_published=True,
    )

    assert cmd_sync._has_reliable_state(mapping, decision) is False
