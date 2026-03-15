"""Unit tests for incremental state synchronization (Story 3.1)."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from resources.daemon.models.mapping import MappingResult, PublicationDecision, SensorCapabilities, SwitchCapabilities
from resources.daemon.models.topology import JeedomCmd
from resources.daemon.sync.state import StateSynchronizer


def _sensor_mapping(cmd_id: int = 10, unique_id: str = "jeedom2ha_cmd_10") -> MappingResult:
    return MappingResult(
        ha_entity_type="sensor",
        confidence="sure",
        reason_code="sensor_temperature",
        jeedom_eq_id=1,
        ha_unique_id=unique_id,
        ha_name="Temp",
        commands={"TEMPERATURE": JeedomCmd(id=cmd_id, name="Temp", generic_type="TEMPERATURE", type="info", sub_type="numeric")},
        capabilities=SensorCapabilities(is_binary=False, unit_of_measurement="°C", state_class="measurement"),
    )


def _switch_mapping(cmd_id: int = 20, unique_id: str = "jeedom2ha_eq_2") -> MappingResult:
    return MappingResult(
        ha_entity_type="switch",
        confidence="sure",
        reason_code="switch_on_off_state",
        jeedom_eq_id=2,
        ha_unique_id=unique_id,
        ha_name="Prise",
        commands={"ENERGY_STATE": JeedomCmd(id=cmd_id, name="Etat", generic_type="ENERGY_STATE", type="info", sub_type="binary")},
        capabilities=SwitchCapabilities(has_on_off=True, has_state=True, on_off_confidence="sure"),
    )


def _make_sync(app=None, mqtt_bridge=None, core_apikey: str = "test-core-api-key") -> StateSynchronizer:
    app = app or {"publications": {}, "mappings": {}}
    bridge = mqtt_bridge or MagicMock()
    bridge.publish_message.return_value = True
    bridge.is_connected = True
    return StateSynchronizer(
        app=app,
        mqtt_bridge=bridge,
        jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
        jeedom_core_apikey=core_apikey,
        poll_interval=1.0,
    )


def test_build_runtime_index_keeps_only_published_and_alive():
    mapping_ok = _sensor_mapping(cmd_id=10, unique_id="uid-ok")
    mapping_not_published = _sensor_mapping(cmd_id=11, unique_id="uid-nopub")
    mapping_not_alive = _sensor_mapping(cmd_id=12, unique_id="uid-dead")

    app = {
        "mappings": {
            "uid-ok": mapping_ok,
            "uid-nopub": mapping_not_published,
            "uid-dead": mapping_not_alive,
        },
        "publications": {
            "uid-ok": PublicationDecision(True, "sure", mapping_ok, state_topic="jeedom2ha/custom/10/state", active_or_alive=True),
            "uid-nopub": PublicationDecision(False, "ambiguous_skipped", mapping_not_published, state_topic="jeedom2ha/custom/11/state", active_or_alive=True),
            "uid-dead": PublicationDecision(True, "sure", mapping_not_alive, state_topic="jeedom2ha/custom/12/state", active_or_alive=False),
        },
    }

    sync = _make_sync(app=app)
    index = sync._build_runtime_index()

    assert list(index.keys()) == [10]
    assert index[10].state_topic == "jeedom2ha/custom/10/state"


def test_apply_changes_publishes_only_known_published_entity(caplog):
    mapping = _switch_mapping(cmd_id=20, unique_id="uid-20")
    app = {
        "mappings": {"uid-20": mapping},
        "publications": {
            "uid-20": PublicationDecision(True, "sure", mapping, state_topic="jeedom2ha/runtime/switch/20", active_or_alive=True)
        },
    }
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    bridge.is_connected = True

    sync = _make_sync(app=app, mqtt_bridge=bridge)
    runtime_index = sync._build_runtime_index()

    with caplog.at_level("INFO"):
        published = sync._apply_changes(
            [
                {"cmd_id": 20, "value": "1"},
                {"cmd_id": 999, "value": "1"},
            ],
            runtime_index,
        )

    assert published == 1
    bridge.publish_message.assert_called_once_with("jeedom2ha/runtime/switch/20", "ON", qos=1, retain=False)
    assert "reason_code=cmd_not_published_or_not_alive" in caplog.text


def test_state_topic_comes_from_runtime_registry_not_pattern_rebuild():
    mapping = _sensor_mapping(cmd_id=10, unique_id="uid-10")
    runtime_topic = "jeedom2ha/special/runtime/topic/10"
    app = {
        "mappings": {"uid-10": mapping},
        "publications": {
            "uid-10": PublicationDecision(True, "sure", mapping, state_topic=runtime_topic, active_or_alive=True)
        },
    }
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    bridge.is_connected = True

    sync = _make_sync(app=app, mqtt_bridge=bridge)
    runtime_index = sync._build_runtime_index()
    sync._apply_changes([{"cmd_id": 10, "value": "21.5"}], runtime_index)

    bridge.publish_message.assert_called_once_with(runtime_topic, "21.5", qos=1, retain=False)


def test_missing_runtime_state_topic_is_skipped_without_fallback(caplog):
    mapping = _sensor_mapping(cmd_id=10, unique_id="uid-10")
    app = {
        "mappings": {"uid-10": mapping},
        "publications": {
            "uid-10": PublicationDecision(True, "sure", mapping, state_topic=None, active_or_alive=True)
        },
    }
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    bridge.is_connected = True

    sync = _make_sync(app=app, mqtt_bridge=bridge)
    with caplog.at_level("WARNING"):
        runtime_index = sync._build_runtime_index()
        published = sync._apply_changes([{"cmd_id": 10, "value": "21.5"}], runtime_index)

    assert runtime_index == {}
    assert published == 0
    bridge.publish_message.assert_not_called()
    assert "reason_code=missing_state_topic_runtime" in caplog.text


def test_rejects_publish_outside_jeedom2ha_namespace(caplog):
    mapping = _sensor_mapping(cmd_id=10, unique_id="uid-10")
    app = {
        "mappings": {"uid-10": mapping},
        "publications": {
            "uid-10": PublicationDecision(True, "sure", mapping, state_topic="thirdparty/sensor/10", active_or_alive=True)
        },
    }
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    bridge.is_connected = True

    sync = _make_sync(app=app, mqtt_bridge=bridge)
    runtime_index = sync._build_runtime_index()

    with caplog.at_level("WARNING"):
        published = sync._apply_changes([{"cmd_id": 10, "value": "23.4"}], runtime_index)

    assert published == 0
    bridge.publish_message.assert_not_called()
    assert "reason_code=topic_outside_jeedom2ha_namespace" in caplog.text


def test_state_safety_invalid_value_is_skipped_with_reason(caplog):
    mapping = _sensor_mapping(cmd_id=10, unique_id="uid-10")
    app = {
        "mappings": {"uid-10": mapping},
        "publications": {
            "uid-10": PublicationDecision(True, "sure", mapping, state_topic="jeedom2ha/sensor/10", active_or_alive=True)
        },
    }
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    bridge.is_connected = True

    sync = _make_sync(app=app, mqtt_bridge=bridge)
    runtime_index = sync._build_runtime_index()

    with caplog.at_level("WARNING"):
        published = sync._apply_changes([{"cmd_id": 10, "value": "not-a-number"}], runtime_index)

    assert published == 0
    bridge.publish_message.assert_not_called()
    assert "reason_code=invalid_state_value" in caplog.text


def test_debounce_keeps_last_value_for_same_cmd():
    mapping = _switch_mapping(cmd_id=20, unique_id="uid-20")
    app = {
        "mappings": {"uid-20": mapping},
        "publications": {
            "uid-20": PublicationDecision(True, "sure", mapping, state_topic="jeedom2ha/switch/20", active_or_alive=True)
        },
    }
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    bridge.is_connected = True

    sync = _make_sync(app=app, mqtt_bridge=bridge)
    runtime_index = sync._build_runtime_index()

    published = sync._apply_changes(
        [
            {"cmd_id": 20, "value": "0"},
            {"cmd_id": 20, "value": "1"},
        ],
        runtime_index,
    )

    assert published == 1
    bridge.publish_message.assert_called_once_with("jeedom2ha/switch/20", "ON", qos=1, retain=False)


def test_state_sync_does_not_mutate_runtime_registries():
    mapping = _switch_mapping(cmd_id=20, unique_id="uid-20")
    app = {
        "mappings": {"uid-20": mapping},
        "publications": {
            "uid-20": PublicationDecision(True, "sure", mapping, state_topic="jeedom2ha/switch/20", active_or_alive=True)
        },
    }
    app_before = deepcopy(app)

    sync = _make_sync(app=app)
    runtime_index = sync._build_runtime_index()
    sync._apply_changes([{"cmd_id": 20, "value": "1"}], runtime_index)

    assert app["mappings"].keys() == app_before["mappings"].keys()
    assert app["publications"].keys() == app_before["publications"].keys()


def test_real_event_changes_cmd_update_payload_is_parsed_and_published():
    mapping = _switch_mapping(cmd_id=20, unique_id="uid-20")
    app = {
        "mappings": {"uid-20": mapping},
        "publications": {
            "uid-20": PublicationDecision(True, "sure", mapping, state_topic="jeedom2ha/switch/20", active_or_alive=True)
        },
    }
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    bridge.is_connected = True

    sync = _make_sync(app=app, mqtt_bridge=bridge)
    runtime_index = sync._build_runtime_index()

    published = sync._apply_changes(
        [
            {
                "datetime": "2026-03-14 10:00:00",
                "name": "cmd::update",
                "option": {"cmd_id": "20", "value": "1", "display_value": "On"},
            }
        ],
        runtime_index,
    )

    assert published == 1
    bridge.publish_message.assert_called_once_with("jeedom2ha/switch/20", "ON", qos=1, retain=False)


def test_non_cmd_update_events_are_ignored_without_warning_spam(caplog):
    mapping = _switch_mapping(cmd_id=20, unique_id="uid-20")
    app = {
        "mappings": {"uid-20": mapping},
        "publications": {
            "uid-20": PublicationDecision(True, "sure", mapping, state_topic="jeedom2ha/switch/20", active_or_alive=True)
        },
    }
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    bridge.is_connected = True

    sync = _make_sync(app=app, mqtt_bridge=bridge)
    runtime_index = sync._build_runtime_index()

    with caplog.at_level("WARNING"):
        published = sync._apply_changes(
            [
                {"name": "eqLogic::update", "option": {"eqLogic_id": "42"}},
                {"name": "scenario::update", "option": {"scenario_id": "7"}},
                {"name": "jeeObject::summary::update", "option": {"object_id": "1"}},
            ],
            runtime_index,
        )

    assert published == 0
    bridge.publish_message.assert_not_called()
    assert "reason_code=invalid_event_payload" not in caplog.text


def test_malformed_cmd_update_payload_is_skipped_with_reason_code(caplog):
    mapping = _switch_mapping(cmd_id=20, unique_id="uid-20")
    app = {
        "mappings": {"uid-20": mapping},
        "publications": {
            "uid-20": PublicationDecision(True, "sure", mapping, state_topic="jeedom2ha/switch/20", active_or_alive=True)
        },
    }
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    bridge.is_connected = True

    sync = _make_sync(app=app, mqtt_bridge=bridge)
    runtime_index = sync._build_runtime_index()

    with caplog.at_level("WARNING"):
        published = sync._apply_changes(
            [
                {"name": "cmd::update", "option": {"value": "1"}},
            ],
            runtime_index,
        )

    assert published == 0
    bridge.publish_message.assert_not_called()
    assert "reason_code=invalid_event_payload" in caplog.text


@pytest.mark.asyncio
async def test_fetch_changes_uses_core_apikey_for_event_changes_calls():
    class _FakeResponse:
        status = 200

        def __init__(self, payload):
            self._payload = payload

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def json(self, content_type=None):  # noqa: ARG002 - aiohttp signature compatibility
            return self._payload

    class _FakeSession:
        closed = False

        def __init__(self):
            self.requests = []

        def post(self, endpoint, json):
            self.requests.append((endpoint, json))
            return _FakeResponse({"result": []})

        async def close(self):
            self.closed = True

    fake_session = _FakeSession()
    sync = _make_sync(core_apikey="core-api-key-expected")
    sync._session = fake_session

    await sync._fetch_changes()

    assert len(fake_session.requests) == 1
    endpoint, payload = fake_session.requests[0]
    assert endpoint == "http://127.0.0.1/core/api/jeeApi.php"
    assert payload["params"]["apikey"] == "core-api-key-expected"


@pytest.mark.asyncio
async def test_missing_core_apikey_disables_incremental_sync_without_crash(caplog):
    mapping = _switch_mapping(cmd_id=20, unique_id="uid-20")
    app = {
        "mappings": {"uid-20": mapping},
        "publications": {
            "uid-20": PublicationDecision(True, "sure", mapping, state_topic="jeedom2ha/switch/20", active_or_alive=True)
        },
    }
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    bridge.is_connected = True

    sync = _make_sync(app=app, mqtt_bridge=bridge, core_apikey="")

    with caplog.at_level("WARNING"):
        published = await sync.run_once()

    assert published == 0
    bridge.publish_message.assert_not_called()
    assert "reason_code=missing_jeedom_core_apikey" in caplog.text
    assert "action=disable_incremental_sync" in caplog.text


def test_extract_event_datetime_parses_jeedom_epoch_float_string():
    sync = _make_sync()

    change = {
        "datetime": "1773522118.696700",
        "name": "cmd::update",
        "option": {"cmd_id": "20", "value": "1"},
    }

    parsed = sync._extract_event_datetime(change)

    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.tzinfo.utcoffset(parsed) == timezone.utc.utcoffset(parsed)
    assert abs(parsed.timestamp() - 1773522118.696700) < 1e-6


def test_format_cursor_uses_epoch_float_string_for_jeedom_api():
    sync = _make_sync()
    dt = datetime.fromtimestamp(1773522118.696700, tz=timezone.utc)

    formatted = sync._format_cursor(dt)

    assert isinstance(formatted, str)
    assert formatted.count(".") == 1
    assert abs(float(formatted) - 1773522118.696700) < 1e-6


@pytest.mark.asyncio
async def test_run_once_does_not_replay_same_batch_on_next_poll():
    mapping = _switch_mapping(cmd_id=20, unique_id="uid-20")
    app = {
        "mappings": {"uid-20": mapping},
        "publications": {
            "uid-20": PublicationDecision(True, "sure", mapping, state_topic="jeedom2ha/switch/20", active_or_alive=True)
        },
    }
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    bridge.is_connected = True
    sync = _make_sync(app=app, mqtt_bridge=bridge)

    event_ts = 1773522118.696700

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
            self.cursors = []

        def post(self, endpoint, json):  # noqa: ARG002
            cursor_raw = str(json["params"]["datetime"])
            self.cursors.append(cursor_raw)
            try:
                cursor_val = float(cursor_raw)
            except (TypeError, ValueError):
                cursor_val = None

            if cursor_val is None or cursor_val <= event_ts:
                payload = {
                    "result": [
                        {
                            "datetime": f"{event_ts:.6f}",
                            "name": "cmd::update",
                            "option": {"cmd_id": "20", "value": "1"},
                        }
                    ]
                }
            else:
                payload = {"result": []}
            return _FakeResponse(payload)

        async def close(self):
            self.closed = True

    fake_session = _FakeSession()
    sync._session = fake_session
    sync._cursor = datetime.fromtimestamp(event_ts - 1, tz=timezone.utc)

    first_published = await sync.run_once()
    second_published = await sync.run_once()

    assert first_published == 1
    assert second_published == 0
    assert len(fake_session.cursors) == 2
    assert float(fake_session.cursors[1]) > event_ts
    bridge.publish_message.assert_called_once_with("jeedom2ha/switch/20", "ON", qos=1, retain=False)
