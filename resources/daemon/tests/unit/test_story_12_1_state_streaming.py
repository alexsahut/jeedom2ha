"""Unit tests for Jeedom -> HA runtime state streaming (Story 12.1, vague 1)."""
from __future__ import annotations

import pytest

from resources.daemon.models.mapping import (
    LightCapabilities,
    MappingResult,
    PublicationDecision,
    SensorCapabilities,
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


def _mono_sensor_decision(eq_id=100, cmd_id=4001, current_value="230.5", published=True):
    cmd = JeedomCmd(id=cmd_id, name="Tension", generic_type="POWER", type="info",
                    sub_type="numeric", current_value=current_value, unit="V")
    mapping = MappingResult(
        ha_entity_type="sensor",
        confidence="sure",
        reason_code="sensor_power",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name="Tension",
        commands={"POWER": cmd},
        capabilities=SensorCapabilities(has_state=True),
        reason_details={"device_class": "voltage", "unit_of_measurement": "V"},
    )
    decision = PublicationDecision(
        should_publish=published, reason="sure", mapping_result=mapping,
        state_topic=f"jeedom2ha/{eq_id}/state", discovery_published=published,
    )
    mapping.publication_decision_ref = decision
    return decision


def _multi_sensor_decision(eq_id=553, cmd_ids=(5301, 5302), values=("231", "12.4")):
    """eq553-like multi-sensor: a primary sensor + one secondary, each per-cmd."""
    primary_cmd = JeedomCmd(id=cmd_ids[0], name="Tension reseau", type="info",
                            sub_type="numeric", current_value=values[0], unit="V")
    primary = MappingResult(
        ha_entity_type="sensor",
        confidence="sure",
        reason_code="sensor_multi_routeur_solaire",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}_cmd_{cmd_ids[0]}",
        ha_name="Tension reseau",
        commands={str(cmd_ids[0]): primary_cmd},
        capabilities=SensorCapabilities(has_state=True),
        reason_details={
            "cmd_id": cmd_ids[0],
            "object_id": f"jeedom2ha_{eq_id}_{cmd_ids[0]}",
            "node_id": f"jeedom2ha_{eq_id}_{cmd_ids[0]}",
            "state_topic": f"jeedom2ha/{eq_id}/{cmd_ids[0]}/state",
        },
    )
    sec_cmd = JeedomCmd(id=cmd_ids[1], name="Courant", type="info",
                        sub_type="numeric", current_value=values[1], unit="A")
    secondary = MappingResult(
        ha_entity_type="sensor",
        confidence="sure",
        reason_code="sensor_multi_routeur_solaire",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}_cmd_{cmd_ids[1]}",
        ha_name="Courant",
        commands={str(cmd_ids[1]): sec_cmd},
        capabilities=SensorCapabilities(has_state=True),
        reason_details={
            "cmd_id": cmd_ids[1],
            "object_id": f"jeedom2ha_{eq_id}_{cmd_ids[1]}",
            "node_id": f"jeedom2ha_{eq_id}_{cmd_ids[1]}",
            "state_topic": f"jeedom2ha/{eq_id}/{cmd_ids[1]}/state",
        },
    )
    primary.additional_mappings = [secondary]
    decision = PublicationDecision(
        should_publish=True, reason="sure", mapping_result=primary,
        state_topic=f"jeedom2ha/{eq_id}/{cmd_ids[0]}/state", discovery_published=True,
    )
    primary.publication_decision_ref = decision
    secondary.publication_decision_ref = PublicationDecision(
        should_publish=True, reason="sure", mapping_result=secondary,
        state_topic=f"jeedom2ha/{eq_id}/{cmd_ids[1]}/state", discovery_published=True,
    )
    return decision


def _binary_decision(eq_id=200, cmd_id=6001, current_value="1", published=True):
    cmd = JeedomCmd(id=cmd_id, name="Presence", generic_type="PRESENCE", type="info",
                    sub_type="binary", current_value=current_value)
    mapping = MappingResult(
        ha_entity_type="binary_sensor",
        confidence="sure",
        reason_code="binary_sensor_presence",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name="Presence",
        commands={"PRESENCE": cmd},
        capabilities=SensorCapabilities(has_state=True),
        reason_details={"device_class": "motion"},
    )
    decision = PublicationDecision(
        should_publish=published, reason="sure", mapping_result=mapping,
        state_topic=f"jeedom2ha/{eq_id}/state", discovery_published=published,
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


def _sync(publications, bridge):
    return StateSynchronizer(app={"publications": publications}, mqtt_bridge=bridge)


# --- Topic resolution (AC#1, AC#5) ---

@pytest.mark.asyncio
async def test_mono_sensor_publishes_on_eq_level_state_topic():
    decision = _mono_sensor_decision(eq_id=100, cmd_id=4001)
    bridge = _FakeBridge()
    sync = _sync({100: decision}, bridge)

    ok = await sync.handle_state_message(eq_id=100, cmd_id=4001, value="231.0")

    assert ok is True
    assert bridge.published == [("jeedom2ha/100/state", "231.0", 1, True)]


@pytest.mark.asyncio
async def test_multi_sensor_publishes_on_per_cmd_state_topic():
    decision = _multi_sensor_decision(eq_id=553, cmd_ids=(5301, 5302))
    bridge = _FakeBridge()
    sync = _sync({553: decision}, bridge)

    # Secondary command (eq553 "Courant") must hit its own per-cmd topic.
    ok = await sync.handle_state_message(eq_id=553, cmd_id=5302, value="13.1")

    assert ok is True
    assert bridge.published == [("jeedom2ha/553/5302/state", "13.1", 1, True)]


@pytest.mark.asyncio
async def test_multi_sensor_primary_command_uses_its_own_topic():
    decision = _multi_sensor_decision(eq_id=553, cmd_ids=(5301, 5302))
    bridge = _FakeBridge()
    sync = _sync({553: decision}, bridge)

    ok = await sync.handle_state_message(eq_id=553, cmd_id=5301, value="232")

    assert ok is True
    assert bridge.published == [("jeedom2ha/553/5301/state", "232", 1, True)]


# --- binary_sensor on/off (AC#6) ---

@pytest.mark.parametrize("raw,expected", [("1", "ON"), ("0", "OFF"), ("true", "ON"),
                                          ("false", "OFF"), (1, "ON"), (0, "OFF")])
@pytest.mark.asyncio
async def test_binary_sensor_translates_on_off(raw, expected):
    decision = _binary_decision(eq_id=200, cmd_id=6001)
    bridge = _FakeBridge()
    sync = _sync({200: decision}, bridge)

    ok = await sync.handle_state_message(eq_id=200, cmd_id=6001, value=raw)

    assert ok is True
    assert bridge.published == [("jeedom2ha/200/state", expected, 1, True)]


# --- Borne vague 1 (AC#4) ---

@pytest.mark.asyncio
async def test_actionable_light_is_not_fed_by_state_sync():
    decision = _light_decision(eq_id=300, cmd_id=7004)
    bridge = _FakeBridge()
    sync = _sync({300: decision}, bridge)

    ok = await sync.handle_state_message(eq_id=300, cmd_id=7004, value="1")

    assert ok is False
    assert bridge.published == []


# --- state ⊆ discovery (AC#5) ---

@pytest.mark.asyncio
async def test_unpublished_entity_is_never_fed():
    decision = _mono_sensor_decision(eq_id=100, cmd_id=4001, published=False)
    bridge = _FakeBridge()
    sync = _sync({100: decision}, bridge)

    ok = await sync.handle_state_message(eq_id=100, cmd_id=4001, value="231")

    assert ok is False
    assert bridge.published == []


@pytest.mark.asyncio
async def test_secondary_with_failed_discovery_is_never_fed():
    """A multi-sensor secondary whose own discovery failed must not stream state,
    even if the parent decision is should_publish (state ⊆ discovery, per-candidate)."""
    decision = _multi_sensor_decision(eq_id=553, cmd_ids=(5301, 5302))
    secondary = decision.mapping_result.additional_mappings[0]
    secondary.publication_decision_ref.discovery_published = False
    bridge = _FakeBridge()
    sync = _sync({553: decision}, bridge)

    # Secondary (discovery failed) is rejected; primary keeps streaming.
    assert await sync.handle_state_message(eq_id=553, cmd_id=5302, value="13.1") is False
    assert await sync.handle_state_message(eq_id=553, cmd_id=5301, value="232") is True
    assert bridge.published == [("jeedom2ha/553/5301/state", "232", 1, True)]


@pytest.mark.asyncio
async def test_unknown_eq_or_cmd_is_rejected():
    decision = _mono_sensor_decision(eq_id=100, cmd_id=4001)
    bridge = _FakeBridge()
    sync = _sync({100: decision}, bridge)

    assert await sync.handle_state_message(eq_id=999, cmd_id=4001, value="1") is False
    assert await sync.handle_state_message(eq_id=100, cmd_id=4999, value="1") is False
    assert bridge.published == []


# --- No usable value / transport gating (AC#7) ---

@pytest.mark.asyncio
async def test_empty_value_is_not_published():
    decision = _mono_sensor_decision(eq_id=100, cmd_id=4001)
    bridge = _FakeBridge()
    sync = _sync({100: decision}, bridge)

    assert await sync.handle_state_message(eq_id=100, cmd_id=4001, value=None) is False
    assert await sync.handle_state_message(eq_id=100, cmd_id=4001, value="  ") is False
    assert bridge.published == []


@pytest.mark.asyncio
async def test_mqtt_disconnected_rejects_state():
    decision = _mono_sensor_decision(eq_id=100, cmd_id=4001)
    bridge = _FakeBridge(connected=False)
    sync = _sync({100: decision}, bridge)

    assert await sync.handle_state_message(eq_id=100, cmd_id=4001, value="231") is False
    assert bridge.published == []


# --- Initial snapshot (AC#2) ---

@pytest.mark.asyncio
async def test_initial_snapshot_publishes_current_values_after_discovery():
    decision = _multi_sensor_decision(eq_id=553, cmd_ids=(5301, 5302), values=("231", "12.4"))
    bridge = _FakeBridge()
    sync = _sync({553: decision}, bridge)

    count = await sync.publish_initial_states(decision)

    assert count == 2
    assert ("jeedom2ha/553/5301/state", "231", 1, True) in bridge.published
    assert ("jeedom2ha/553/5302/state", "12.4", 1, True) in bridge.published


@pytest.mark.asyncio
async def test_initial_snapshot_skips_entities_not_discovery_published():
    decision = _mono_sensor_decision(eq_id=100, cmd_id=4001, current_value="230")
    decision.discovery_published = False
    decision.mapping_result.publication_decision_ref.discovery_published = False
    bridge = _FakeBridge()
    sync = _sync({100: decision}, bridge)

    count = await sync.publish_initial_states(decision)

    assert count == 0
    assert bridge.published == []


@pytest.mark.asyncio
async def test_initial_snapshot_skips_when_no_current_value():
    decision = _mono_sensor_decision(eq_id=100, cmd_id=4001, current_value=None)
    bridge = _FakeBridge()
    sync = _sync({100: decision}, bridge)

    count = await sync.publish_initial_states(decision)

    assert count == 0
    assert bridge.published == []


# --- is_active contract / non-regression with CommandSynchronizer (AC#8, AC#9) ---

def test_real_state_sync_is_inactive_in_vague1():
    sync = _sync({}, _FakeBridge())
    assert sync.is_active is False


def test_command_sync_sees_real_state_sync_as_inactive():
    """Real StateSynchronizer must satisfy CommandSynchronizer's is_active contract
    and keep it on the optimistic path (vague 1 does not stream actionable state)."""
    state_sync = _sync({}, _FakeBridge())
    cmd_sync = CommandSynchronizer(app={}, mqtt_bridge=_FakeBridge(),
                                   jeedom_api_endpoint="http://x/api")
    assert cmd_sync._is_state_sync_active(state_sync) is False


# --- list_state_targets: authoritative PHP listener registration (R1, AC#5) ---

def test_list_state_targets_multi_sensor_yields_one_entry_per_cmd():
    decision = _multi_sensor_decision(eq_id=553, cmd_ids=(5301, 5302))
    sync = _sync({553: decision}, _FakeBridge())

    targets = sync.list_state_targets()

    assert targets == [
        {"eq_id": 553, "cmd_id": 5301, "ha_type": "sensor",
         "state_topic": "jeedom2ha/553/5301/state"},
        {"eq_id": 553, "cmd_id": 5302, "ha_type": "sensor",
         "state_topic": "jeedom2ha/553/5302/state"},
    ]


def test_list_state_targets_includes_mono_and_binary_excludes_light():
    sync = _sync({
        100: _mono_sensor_decision(eq_id=100, cmd_id=4001),
        200: _binary_decision(eq_id=200, cmd_id=6001),
        300: _light_decision(eq_id=300, cmd_id=7004),
    }, _FakeBridge())

    targets = sync.list_state_targets()

    keys = {(t["eq_id"], t["cmd_id"], t["ha_type"]) for t in targets}
    assert (100, 4001, "sensor") in keys
    assert (200, 6001, "binary_sensor") in keys
    assert all(t["ha_type"] in ("sensor", "binary_sensor") for t in targets)
    assert not any(t["eq_id"] == 300 for t in targets)


def test_list_state_targets_excludes_unpublished_entities():
    sync = _sync({
        100: _mono_sensor_decision(eq_id=100, cmd_id=4001, published=False),
    }, _FakeBridge())

    assert sync.list_state_targets() == []
