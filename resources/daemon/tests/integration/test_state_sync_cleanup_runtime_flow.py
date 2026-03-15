"""Integration tests for Story 3.1 cleanup/runtime interactions."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from resources.daemon.sync.state import StateSynchronizer
from resources.daemon.transport.http_server import create_app

LOCAL_SECRET = "test-secret-story-3-1"


@pytest.fixture
def http_app():
    app = create_app(local_secret=LOCAL_SECRET)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    return app


@pytest.fixture
async def http_client(http_app, aiohttp_client):
    return await aiohttp_client(http_app)


@pytest.mark.asyncio
async def test_removed_entity_cleanup_remains_exact_and_state_sync_does_not_recreate(
    http_client,
    http_app,
    caplog,
):
    """AC #8 evidence on a realistic flow touched by Story 3.1.

    1) /action/sync publishes a sensor.
    2) /action/sync with empty topology removes it (exact retained cleanup).
    3) StateSynchronizer receives a late event for removed cmd -> ignored,
       with no alternative cleanup/purge and no entity recreation.
    """
    bridge = http_app["mqtt_bridge"]

    payload_with_sensor = {
        "version": "1.0",
        "eq_logics": [
            {
                "id": "1",
                "name": "Temp Ext",
                "object_id": "1",
                "is_enable": "1",
                "eq_type": "virtual",
                "cmds": [
                    {
                        "id": "100",
                        "generic_type": "TEMPERATURE",
                        "name": "Temp",
                        "type": "info",
                        "sub_type": "numeric",
                        "is_historized": "0",
                        "unit": "°C",
                        "current_value": 21.5,
                    }
                ],
            }
        ],
        "objects": [{"id": "1", "name": "Jardin"}],
    }

    resp_first = await http_client.post(
        "/action/sync",
        headers={"X-Local-Secret": LOCAL_SECRET},
        json={"payload": payload_with_sensor},
    )
    assert resp_first.status == 200
    bridge.publish_message.reset_mock()

    payload_without_sensor = {
        "version": "1.0",
        "eq_logics": [],
        "objects": [{"id": "1", "name": "Jardin"}],
    }
    resp_second = await http_client.post(
        "/action/sync",
        headers={"X-Local-Secret": LOCAL_SECRET},
        json={"payload": payload_without_sensor},
    )
    assert resp_second.status == 200

    cleanup_calls = bridge.publish_message.call_args_list
    assert len(cleanup_calls) == 1
    cleanup_call = cleanup_calls[0]
    cleanup_topic = cleanup_call.args[0]
    cleanup_payload = cleanup_call.args[1]
    assert cleanup_topic == "homeassistant/sensor/jeedom2ha_cmd_100/config"
    assert cleanup_payload == ""
    assert cleanup_call.kwargs["retain"] is True
    assert "#" not in cleanup_topic
    assert "+" not in cleanup_topic
    bridge.publish_message.reset_mock()

    state_sync = StateSynchronizer(
        app=http_app,
        mqtt_bridge=bridge,
        jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
        jeedom_core_apikey="test-core-api-key",
        poll_interval=1.0,
    )
    runtime_index = state_sync._build_runtime_index()
    assert 100 not in runtime_index

    with caplog.at_level("INFO"):
        published = state_sync._apply_changes([{"cmd_id": 100, "value": "22.0"}], runtime_index)

    assert published == 0
    bridge.publish_message.assert_not_called()
    assert "reason_code=cmd_not_published_or_not_alive" in caplog.text


@pytest.mark.asyncio
async def test_discovery_failure_does_not_leave_runtime_published_alive_for_late_changes(
    http_client,
    http_app,
    caplog,
):
    """Story 3.1 blocker: runtime registry must follow real discovery success."""
    bridge = http_app["mqtt_bridge"]
    bridge.publish_message.side_effect = [False]

    payload_with_sensor = {
        "version": "1.0",
        "eq_logics": [
            {
                "id": "2",
                "name": "Temp Bureau",
                "object_id": "1",
                "is_enable": "1",
                "eq_type": "virtual",
                "cmds": [
                    {
                        "id": "200",
                        "generic_type": "TEMPERATURE",
                        "name": "Temp",
                        "type": "info",
                        "sub_type": "numeric",
                        "is_historized": "0",
                        "unit": "°C",
                        "current_value": 20.0,
                    }
                ],
            }
        ],
        "objects": [{"id": "1", "name": "Bureau"}],
    }

    resp = await http_client.post(
        "/action/sync",
        headers={"X-Local-Secret": LOCAL_SECRET},
        json={"payload": payload_with_sensor},
    )
    assert resp.status == 200

    decision = http_app["publications"]["jeedom2ha_cmd_200"]
    assert decision.should_publish is False
    assert decision.active_or_alive is False

    bridge.publish_message.reset_mock()
    bridge.publish_message.side_effect = None
    bridge.publish_message.return_value = True

    state_sync = StateSynchronizer(
        app=http_app,
        mqtt_bridge=bridge,
        jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
        jeedom_core_apikey="test-core-api-key",
        poll_interval=1.0,
    )
    runtime_index = state_sync._build_runtime_index()
    assert 200 not in runtime_index

    with caplog.at_level("INFO"):
        published = state_sync._apply_changes([{"cmd_id": 200, "value": "20.4"}], runtime_index)

    assert published == 0
    bridge.publish_message.assert_not_called()
    assert "reason_code=cmd_not_published_or_not_alive" in caplog.text
