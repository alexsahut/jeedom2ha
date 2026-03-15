"""Unit tests for HA -> Jeedom command synchronization (Story 3.2)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

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


class _FakeStateSynchronizer:
    def __init__(self, active: bool):
        self.is_active = active


def _light_mapping(
    eq_id: int = 1,
    *,
    has_brightness: bool = True,
    with_state_info: bool = True,
) -> MappingResult:
    commands = {
        "LIGHT_ON": JeedomCmd(id=1001, name="On", generic_type="LIGHT_ON", type="action", sub_type="other"),
        "LIGHT_OFF": JeedomCmd(id=1002, name="Off", generic_type="LIGHT_OFF", type="action", sub_type="other"),
    }
    if has_brightness:
        commands["LIGHT_SLIDER"] = JeedomCmd(
            id=1003,
            name="Dimmer",
            generic_type="LIGHT_SLIDER",
            type="action",
            sub_type="slider",
        )
    if with_state_info:
        commands["LIGHT_STATE"] = JeedomCmd(
            id=1004,
            name="State",
            generic_type="LIGHT_STATE",
            type="info",
            sub_type="binary",
        )

    return MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off_brightness" if has_brightness else "light_on_off_only",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Light {eq_id}",
        commands=commands,
        capabilities=LightCapabilities(
            has_on_off=True,
            has_brightness=has_brightness,
            on_off_confidence="sure",
            brightness_confidence="sure" if has_brightness else "unknown",
        ),
    )


def _switch_mapping(eq_id: int = 2, *, with_state_info: bool = True) -> MappingResult:
    commands = {
        "ENERGY_ON": JeedomCmd(id=2001, name="On", generic_type="ENERGY_ON", type="action", sub_type="other"),
        "ENERGY_OFF": JeedomCmd(id=2002, name="Off", generic_type="ENERGY_OFF", type="action", sub_type="other"),
    }
    if with_state_info:
        commands["ENERGY_STATE"] = JeedomCmd(
            id=2003,
            name="State",
            generic_type="ENERGY_STATE",
            type="info",
            sub_type="binary",
        )

    return MappingResult(
        ha_entity_type="switch",
        confidence="sure",
        reason_code="switch_on_off_state" if with_state_info else "switch_on_off_only",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Switch {eq_id}",
        commands=commands,
        capabilities=SwitchCapabilities(
            has_on_off=True,
            has_state=with_state_info,
            on_off_confidence="sure",
            device_class="outlet",
        ),
    )


def _cover_mapping(
    eq_id: int = 3,
    *,
    has_stop: bool = True,
    has_position: bool = True,
    with_state_info: bool = True,
) -> MappingResult:
    commands = {
        "FLAP_UP": JeedomCmd(id=3001, name="Up", generic_type="FLAP_UP", type="action", sub_type="other"),
        "FLAP_DOWN": JeedomCmd(id=3002, name="Down", generic_type="FLAP_DOWN", type="action", sub_type="other"),
    }
    if has_stop:
        commands["FLAP_STOP"] = JeedomCmd(id=3003, name="Stop", generic_type="FLAP_STOP", type="action", sub_type="other")
    if has_position:
        commands["FLAP_SLIDER"] = JeedomCmd(
            id=3004,
            name="Position",
            generic_type="FLAP_SLIDER",
            type="action",
            sub_type="slider",
        )
    if with_state_info:
        commands["FLAP_STATE"] = JeedomCmd(
            id=3005,
            name="State",
            generic_type="FLAP_STATE",
            type="info",
            sub_type="numeric",
        )

    return MappingResult(
        ha_entity_type="cover",
        confidence="sure",
        reason_code="cover_open_close_stop_position",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Cover {eq_id}",
        commands=commands,
        capabilities=CoverCapabilities(
            has_open_close=True,
            has_stop=has_stop,
            has_position=has_position,
            is_bso=False,
            open_close_confidence="sure",
            position_confidence="sure" if has_position else "unknown",
        ),
    )


def _decision(mapping: MappingResult, *, alive: bool = True, should_publish: bool = True) -> PublicationDecision:
    return PublicationDecision(
        should_publish=should_publish,
        reason="sure" if should_publish else "skipped",
        mapping_result=mapping,
        state_topic=f"jeedom2ha/{mapping.jeedom_eq_id}/state",
        active_or_alive=alive,
    )


def _make_sync(app: dict, bridge: MagicMock) -> CommandSynchronizer:
    return CommandSynchronizer(
        app=app,
        mqtt_bridge=bridge,
        jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
        jeedom_core_apikey="core-apikey",
    )


@pytest.mark.asyncio
async def test_rejects_topic_outside_jeedom2ha_namespace(caplog):
    mapping = _switch_mapping(eq_id=2)
    app = {
        "mappings": {mapping.ha_unique_id: mapping},
        "publications": {mapping.ha_unique_id: _decision(mapping)},
        "state_synchronizer": _FakeStateSynchronizer(active=True),
    }
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True

    sync = _make_sync(app, bridge)
    sync._execute_exec_cmd = AsyncMock(return_value=True)

    with caplog.at_level("INFO"):
        ok = await sync.handle_command_message("thirdparty/2/set", "ON")

    assert ok is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "reason_code=topic_outside_jeedom2ha_namespace" in caplog.text


@pytest.mark.asyncio
async def test_gating_rejects_non_alive_entity_before_rpc(caplog):
    mapping = _switch_mapping(eq_id=2)
    app = {
        "mappings": {mapping.ha_unique_id: mapping},
        "publications": {mapping.ha_unique_id: _decision(mapping, alive=False)},
        "state_synchronizer": object(),
    }
    bridge = MagicMock()
    bridge.is_connected = True

    sync = _make_sync(app, bridge)
    sync._execute_exec_cmd = AsyncMock(return_value=True)

    with caplog.at_level("INFO"):
        ok = await sync.handle_command_message("jeedom2ha/2/set", "ON")

    assert ok is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "reason_code=entity_not_alive" in caplog.text


@pytest.mark.asyncio
async def test_empty_publication_registry_rejects_command_until_runtime_is_rehydrated(caplog):
    mapping = _switch_mapping(eq_id=2, with_state_info=True)
    app = {
        "mappings": {mapping.ha_unique_id: mapping},
        "publications": {},
        "state_synchronizer": _FakeStateSynchronizer(active=True),
    }
    bridge = MagicMock()
    bridge.is_connected = True

    sync = _make_sync(app, bridge)
    sync._execute_exec_cmd = AsyncMock(return_value=True)

    with caplog.at_level("INFO"):
        ok = await sync.handle_command_message("jeedom2ha/2/set", "ON")

    assert ok is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "reason_code=unknown_runtime_entity" in caplog.text


@pytest.mark.asyncio
async def test_switch_on_translation_uses_energy_on_and_empty_options():
    mapping = _switch_mapping(eq_id=2, with_state_info=True)
    app = {
        "mappings": {mapping.ha_unique_id: mapping},
        "publications": {mapping.ha_unique_id: _decision(mapping)},
        "state_synchronizer": _FakeStateSynchronizer(active=True),
    }
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True

    sync = _make_sync(app, bridge)
    sync._execute_exec_cmd = AsyncMock(return_value=True)

    ok = await sync.handle_command_message("jeedom2ha/2/set", "ON")

    assert ok is True
    sync._execute_exec_cmd.assert_awaited_once_with(2001, {})
    bridge.publish_message.assert_not_called()


@pytest.mark.asyncio
async def test_brightness_translation_uses_slider_option_string():
    mapping = _light_mapping(eq_id=1, has_brightness=True, with_state_info=True)
    app = {
        "mappings": {mapping.ha_unique_id: mapping},
        "publications": {mapping.ha_unique_id: _decision(mapping)},
        "state_synchronizer": _FakeStateSynchronizer(active=True),
    }
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True

    sync = _make_sync(app, bridge)
    sync._execute_exec_cmd = AsyncMock(return_value=True)

    ok = await sync.handle_command_message("jeedom2ha/1/brightness/set", "42")

    assert ok is True
    sync._execute_exec_cmd.assert_awaited_once_with(1003, {"slider": "42"})
    bridge.publish_message.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_slider_payload_is_rejected_without_rpc(caplog):
    mapping = _light_mapping(eq_id=1, has_brightness=True, with_state_info=True)
    app = {
        "mappings": {mapping.ha_unique_id: mapping},
        "publications": {mapping.ha_unique_id: _decision(mapping)},
        "state_synchronizer": _FakeStateSynchronizer(active=True),
    }
    bridge = MagicMock()
    bridge.is_connected = True

    sync = _make_sync(app, bridge)
    sync._execute_exec_cmd = AsyncMock(return_value=True)

    with caplog.at_level("INFO"):
        ok = await sync.handle_command_message("jeedom2ha/1/brightness/set", "101")

    assert ok is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "reason_code=invalid_command_payload" in caplog.text


@pytest.mark.asyncio
async def test_missing_action_command_is_rejected_without_rpc(caplog):
    mapping = _light_mapping(eq_id=1, has_brightness=False, with_state_info=True)
    mapping.commands.pop("LIGHT_OFF")
    app = {
        "mappings": {mapping.ha_unique_id: mapping},
        "publications": {mapping.ha_unique_id: _decision(mapping)},
        "state_synchronizer": _FakeStateSynchronizer(active=True),
    }
    bridge = MagicMock()
    bridge.is_connected = True

    sync = _make_sync(app, bridge)
    sync._execute_exec_cmd = AsyncMock(return_value=True)

    with caplog.at_level("INFO"):
        ok = await sync.handle_command_message("jeedom2ha/1/set", "OFF")

    assert ok is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "reason_code=missing_action_command" in caplog.text


@pytest.mark.asyncio
async def test_optimistic_controlled_publishes_state_only_when_allowed():
    mapping = _switch_mapping(eq_id=2, with_state_info=False)
    app = {
        "mappings": {mapping.ha_unique_id: mapping},
        "publications": {mapping.ha_unique_id: _decision(mapping)},
        "state_synchronizer": None,
    }
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True

    sync = _make_sync(app, bridge)
    sync._execute_exec_cmd = AsyncMock(return_value=True)

    ok = await sync.handle_command_message("jeedom2ha/2/set", "ON")

    assert ok is True
    sync._execute_exec_cmd.assert_awaited_once_with(2001, {})
    bridge.publish_message.assert_called_once_with("jeedom2ha/2/state", "ON", qos=1, retain=False)


@pytest.mark.asyncio
async def test_cover_without_reliable_feedback_is_stateless():
    mapping = _cover_mapping(eq_id=3, has_stop=True, has_position=True, with_state_info=False)
    app = {
        "mappings": {mapping.ha_unique_id: mapping},
        "publications": {mapping.ha_unique_id: _decision(mapping)},
        "state_synchronizer": None,
    }
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True

    sync = _make_sync(app, bridge)
    sync._execute_exec_cmd = AsyncMock(return_value=True)

    ok = await sync.handle_command_message("jeedom2ha/3/set", "OPEN")

    assert ok is True
    sync._execute_exec_cmd.assert_awaited_once_with(3001, {})
    bridge.publish_message.assert_not_called()


@pytest.mark.asyncio
async def test_topic_must_match_exact_discovery_contract(caplog):
    mapping = _light_mapping(eq_id=1, has_brightness=False, with_state_info=True)
    app = {
        "mappings": {mapping.ha_unique_id: mapping},
        "publications": {mapping.ha_unique_id: _decision(mapping)},
        "state_synchronizer": _FakeStateSynchronizer(active=True),
    }
    bridge = MagicMock()
    bridge.is_connected = True

    sync = _make_sync(app, bridge)
    sync._execute_exec_cmd = AsyncMock(return_value=True)

    with caplog.at_level("INFO"):
        ok = await sync.handle_command_message("jeedom2ha/1/brightness/set", "20")

    assert ok is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "reason_code=topic_not_published_by_discovery" in caplog.text


@pytest.mark.asyncio
async def test_rpc_timeout_is_reported_and_never_publishes_immediate_state(caplog):
    mapping = _switch_mapping(eq_id=2, with_state_info=False)
    app = {
        "mappings": {mapping.ha_unique_id: mapping},
        "publications": {mapping.ha_unique_id: _decision(mapping)},
        "state_synchronizer": None,
    }
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True

    sync = _make_sync(app, bridge)

    async def _timeout_stub(cmd_id, options):  # noqa: ARG001
        sync._last_exec_error_reason = "jeedom_rpc_timeout"
        return False

    sync._execute_exec_cmd = AsyncMock(side_effect=_timeout_stub)

    with caplog.at_level("WARNING"):
        ok = await sync.handle_command_message("jeedom2ha/2/set", "ON")

    assert ok is False
    bridge.publish_message.assert_not_called()
    assert "reason_code=jeedom_rpc_timeout" in caplog.text


@pytest.mark.asyncio
async def test_execute_exec_cmd_uses_cmd_exec_cmd_contract():
    class _FakeResponse:
        status = 200

        def __init__(self, payload):
            self._payload = payload

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def json(self, content_type=None):  # noqa: ARG002
            return self._payload

    class _FakeSession:
        closed = False

        def __init__(self):
            self.requests = []

        def post(self, endpoint, json):
            self.requests.append((endpoint, json))
            return _FakeResponse({"result": {"ok": True}})

        async def close(self):
            self.closed = True

    mapping = _switch_mapping(eq_id=2, with_state_info=True)
    app = {
        "mappings": {mapping.ha_unique_id: mapping},
        "publications": {mapping.ha_unique_id: _decision(mapping)},
        "state_synchronizer": _FakeStateSynchronizer(active=True),
    }
    bridge = MagicMock()
    bridge.is_connected = True
    sync = _make_sync(app, bridge)
    fake_session = _FakeSession()
    sync._session = fake_session

    ok_action = await sync._execute_exec_cmd(2001, {})
    ok_slider = await sync._execute_exec_cmd(2001, {"slider": "37"})

    assert ok_action is True
    assert ok_slider is True
    assert len(fake_session.requests) == 2

    endpoint, payload_action = fake_session.requests[0]
    assert endpoint == "http://127.0.0.1/core/api/jeeApi.php"
    assert payload_action["method"] == "cmd::execCmd"
    assert payload_action["params"]["apikey"] == "core-apikey"
    assert payload_action["params"]["id"] == 2001
    assert payload_action["params"]["options"] == {}

    _, payload_slider = fake_session.requests[1]
    assert payload_slider["method"] == "cmd::execCmd"
    assert payload_slider["params"]["apikey"] == "core-apikey"
    assert payload_slider["params"]["id"] == 2001
    assert payload_slider["params"]["options"] == {"slider": "37"}


@pytest.mark.asyncio
async def test_state_sync_present_but_inactive_is_not_considered_reliable():
    mapping = _switch_mapping(eq_id=2, with_state_info=True)
    app = {
        "mappings": {mapping.ha_unique_id: mapping},
        "publications": {mapping.ha_unique_id: _decision(mapping)},
        "state_synchronizer": _FakeStateSynchronizer(active=False),
    }
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True

    sync = _make_sync(app, bridge)
    sync._execute_exec_cmd = AsyncMock(return_value=True)

    ok = await sync.handle_command_message("jeedom2ha/2/set", "ON")

    assert ok is True
    sync._execute_exec_cmd.assert_awaited_once_with(2001, {})
    bridge.publish_message.assert_called_once_with("jeedom2ha/2/state", "ON", qos=1, retain=False)
