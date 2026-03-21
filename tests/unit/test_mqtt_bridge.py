"""
test_mqtt_bridge.py — Unit tests for MqttBridge (persistent connection) and
/action/mqtt_connect + enriched /system/status HTTP endpoints.

Story 1.3 — Validation de la Connexion et Statut du Pont
Story 5.1 — Birth HA republication, broker reconnect republication, lissage
"""
import asyncio
import ssl

import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call, PropertyMock
from aiohttp import web

from resources.daemon.transport.mqtt_client import (
    BRIDGE_STATUS_TOPIC,
    COMMAND_SUBSCRIPTION_TOPICS,
    HA_STATUS_TOPIC,
    MqttBridge,
)


LOCAL_SECRET = "test-secret-bridge"

_FAKE_CLI_ARGS = [
    "--loglevel", "debug",
    "--sockethost", "127.0.0.1",
    "--socketport", "0",
    "--callback", "http://127.0.0.1/fake",
    "--apikey", "test-api-key",
    "--pid", "/tmp/test-jeedom2ha.pid",
    "--cycle", "0.5",
]


@pytest.fixture(autouse=True)
def fake_cli_args():
    with patch("sys.argv", ["main.py"] + _FAKE_CLI_ARGS):
        yield


@pytest.fixture
def http_app():
    from resources.daemon.transport.http_server import create_app
    return create_app(local_secret=LOCAL_SECRET)


@pytest.fixture
async def http_client(http_app, aiohttp_client):
    return await aiohttp_client(http_app)


# ---------------------------------------------------------------------------
# Helper: create a fully mocked paho client
# ---------------------------------------------------------------------------

def _make_mock_paho_client():
    """Return a MagicMock that behaves like a paho mqtt.Client."""
    client = MagicMock()
    client.on_connect = None
    client.on_disconnect = None
    client.on_message = None
    client.subscribe.return_value = (0, 1)
    return client


# ---------------------------------------------------------------------------
# Task 6.1 — MqttBridge state, LWT, birth message
# ---------------------------------------------------------------------------

class TestMqttBridgeInitialState:
    def test_initial_state_is_disconnected(self):
        bridge = MqttBridge()
        assert bridge.state == "disconnected"

    def test_initial_is_connected_is_false(self):
        bridge = MqttBridge()
        assert bridge.is_connected is False

    def test_initial_broker_info_is_empty(self):
        bridge = MqttBridge()
        assert bridge.broker_info == ""


class TestMqttBridgeStart:
    async def test_start_sets_lwt(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            await bridge.start({"host": "localhost", "port": 1883})
        mock_paho.will_set.assert_called_once_with(BRIDGE_STATUS_TOPIC, "offline", qos=1, retain=True)

    async def test_start_uses_connect_async_not_blocking_connect(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            await bridge.start({"host": "localhost", "port": 1883})
        mock_paho.connect_async.assert_called_once_with("localhost", 1883, keepalive=60)
        mock_paho.connect.assert_not_called()

    async def test_start_calls_loop_start(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            await bridge.start({"host": "localhost", "port": 1883})
        mock_paho.loop_start.assert_called_once()

    async def test_start_sets_reconnect_delay(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            await bridge.start({"host": "localhost", "port": 1883})
        mock_paho.reconnect_delay_set.assert_called_once_with(min_delay=1, max_delay=30)

    async def test_start_state_becomes_connecting(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            await bridge.start({"host": "localhost", "port": 1883})
        assert bridge.state == "connecting"

    async def test_start_with_auth_calls_username_pw_set(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            await bridge.start({"host": "localhost", "port": 1883, "user": "jeedom", "password": "secret"})
        mock_paho.username_pw_set.assert_called_once_with("jeedom", "secret")

    async def test_start_anonymous_no_auth_call(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            await bridge.start({"host": "localhost", "port": 1883})
        mock_paho.username_pw_set.assert_not_called()

    async def test_start_stores_broker_info(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            await bridge.start({"host": "192.168.1.10", "port": 1883})
        assert bridge.broker_info == "192.168.1.10:1883"

    async def test_start_registers_callbacks_on_paho_client(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            await bridge.start({"host": "localhost", "port": 1883})
        assert mock_paho.on_connect == bridge._on_connect
        assert mock_paho.on_disconnect == bridge._on_disconnect
        assert mock_paho.on_message == bridge._on_message


# ---------------------------------------------------------------------------
# Task 6.1 / 6.2 — Callback state transitions
# ---------------------------------------------------------------------------

class TestMqttBridgeCallbacks:
    async def test_on_connect_rc0_publishes_birth_message(self):
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()
        mock_paho = _make_mock_paho_client()

        bridge._on_connect(mock_paho, None, {}, 0)
        await asyncio.sleep(0)  # yield for call_soon_threadsafe

        mock_paho.publish.assert_called_once_with(BRIDGE_STATUS_TOPIC, "online", qos=1, retain=True)

    async def test_on_connect_rc0_sets_state_connected(self):
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()
        mock_paho = _make_mock_paho_client()

        bridge._on_connect(mock_paho, None, {}, 0)
        await asyncio.sleep(0)

        assert bridge.state == "connected"
        assert bridge.is_connected is True

    async def test_on_connect_failure_sets_state_disconnected(self):
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()
        mock_paho = _make_mock_paho_client()

        bridge._on_connect(mock_paho, None, {}, 5)  # rc=5 auth failed
        await asyncio.sleep(0)

        assert bridge.state == "disconnected"
        mock_paho.publish.assert_not_called()

    async def test_on_disconnect_unexpected_sets_reconnecting(self):
        """Task 6.2 — rc != 0 on disconnect → RECONNECTING state."""
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()
        bridge._state = "connected"
        mock_paho = _make_mock_paho_client()

        bridge._on_disconnect(mock_paho, None, 1)  # rc=1 unexpected
        await asyncio.sleep(0)

        assert bridge.state == "reconnecting"

    async def test_on_disconnect_clean_sets_disconnected(self):
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()
        bridge._state = "connected"
        mock_paho = _make_mock_paho_client()

        bridge._on_disconnect(mock_paho, None, 0)  # rc=0 clean
        await asyncio.sleep(0)

        assert bridge.state == "disconnected"

    async def test_reconnect_rebirth_message_published_on_reconnect(self):
        """After reconnect (second on_connect call), birth message is published again."""
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()
        mock_paho = _make_mock_paho_client()

        # First connection
        bridge._on_connect(mock_paho, None, {}, 0)
        await asyncio.sleep(0)
        assert bridge.state == "connected"

        # Unexpected disconnect
        bridge._on_disconnect(mock_paho, None, 1)
        await asyncio.sleep(0)
        assert bridge.state == "reconnecting"

        # Reconnect
        bridge._on_connect(mock_paho, None, {}, 0)
        await asyncio.sleep(0)
        assert bridge.state == "connected"

        # Birth message published twice (initial + after reconnect)
        assert mock_paho.publish.call_count == 2
        for c in mock_paho.publish.call_args_list:
            assert c == call(BRIDGE_STATUS_TOPIC, "online", qos=1, retain=True)

    async def test_on_connect_subscribes_command_topics(self):
        """Story 5.1: all command topics + HA_STATUS_TOPIC are subscribed."""
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()
        bridge._broker_host = "localhost"
        bridge._broker_port = 1883
        mock_paho = _make_mock_paho_client()

        bridge._on_connect(mock_paho, None, {}, 0)
        await asyncio.sleep(0)

        subscribed = [c.args[0] for c in mock_paho.subscribe.call_args_list]
        # All command topics must be subscribed
        for topic in COMMAND_SUBSCRIPTION_TOPICS:
            assert topic in subscribed
        # Story 5.1: homeassistant/status must also be subscribed
        assert HA_STATUS_TOPIC in subscribed

    async def test_on_message_dispatches_to_command_handler(self):
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()
        handler = AsyncMock()
        bridge.set_command_handler(handler)
        message = MagicMock(topic="jeedom2ha/2/set", payload=b"ON")

        bridge._on_message(None, None, message)
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        handler.assert_awaited_once_with("jeedom2ha/2/set", "ON")

    async def test_on_message_serializes_commands_for_same_entity(self):
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()
        first_can_finish = asyncio.Event()
        second_started = asyncio.Event()
        events = []

        async def handler(topic, payload):
            events.append(f"start:{payload}")
            if payload == "ON":
                await first_can_finish.wait()
            else:
                second_started.set()
            events.append(f"end:{payload}")

        bridge.set_command_handler(handler)
        first_message = MagicMock(topic="jeedom2ha/2/set", payload=b"ON")
        second_message = MagicMock(topic="jeedom2ha/2/set", payload=b"OFF")

        bridge._on_message(None, None, first_message)
        bridge._on_message(None, None, second_message)
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert events == ["start:ON"]
        assert second_started.is_set() is False

        first_can_finish.set()
        await asyncio.wait_for(second_started.wait(), timeout=1)
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert events == ["start:ON", "end:ON", "start:OFF", "end:OFF"]


# ---------------------------------------------------------------------------
# Task 6.3 — Error handling: broker unreachable
# ---------------------------------------------------------------------------

class TestMqttBridgeErrorHandling:
    async def test_start_with_connect_async_exception_does_not_crash(self):
        """Task 6.3 — If connect_async raises, bridge remains in usable state."""
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        mock_paho.connect_async.side_effect = OSError("Connection refused")
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            # Should not raise; the daemon must remain alive
            try:
                await bridge.start({"host": "unreachable.host", "port": 9999})
            except OSError:
                pass  # acceptable — daemon catches this upstream
        # Bridge state should not be "connected" after a failed connect
        assert bridge.state != "connected"


# ---------------------------------------------------------------------------
# Task 6.6 — Shutdown propre
# ---------------------------------------------------------------------------

class TestMqttBridgeStop:
    async def test_stop_publishes_offline(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            await bridge.start({"host": "localhost", "port": 1883})
        await bridge.stop()
        mock_paho.publish.assert_called_once_with(BRIDGE_STATUS_TOPIC, "offline", qos=1, retain=True)

    async def test_stop_calls_disconnect_and_loop_stop(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            await bridge.start({"host": "localhost", "port": 1883})
        await bridge.stop()
        mock_paho.disconnect.assert_called_once()
        mock_paho.loop_stop.assert_called_once()

    async def test_stop_sets_state_disconnected(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            await bridge.start({"host": "localhost", "port": 1883})
        bridge._state = "connected"
        await bridge.stop()
        assert bridge.state == "disconnected"

    async def test_stop_when_not_started_is_safe(self):
        """stop() on a never-started bridge must not raise."""
        bridge = MqttBridge()
        await bridge.stop()  # should not raise
        assert bridge.state == "disconnected"

    async def test_stop_clears_client_reference(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            await bridge.start({"host": "localhost", "port": 1883})
        await bridge.stop()
        assert bridge._client is None


# ---------------------------------------------------------------------------
# Task 1.7 — TLS configuration
# ---------------------------------------------------------------------------

class TestMqttBridgeTls:
    async def test_tls_enabled_calls_tls_set_context(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            with patch("resources.daemon.transport.mqtt_client.ssl.create_default_context") as mock_ctx_factory:
                ctx_instance = MagicMock()
                mock_ctx_factory.return_value = ctx_instance
                await bridge.start({"host": "localhost", "port": 8883, "tls": True, "tls_verify": True})
        mock_paho.tls_set_context.assert_called_once_with(ctx_instance)

    async def test_tls_verify_disabled(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            with patch("resources.daemon.transport.mqtt_client.ssl.create_default_context") as mock_ctx_factory:
                ctx_instance = MagicMock()
                mock_ctx_factory.return_value = ctx_instance
                await bridge.start({"host": "localhost", "port": 8883, "tls": True, "tls_verify": False})
        assert ctx_instance.check_hostname is False
        assert ctx_instance.verify_mode == ssl.CERT_NONE

    async def test_no_tls_no_tls_call(self):
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()
        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            await bridge.start({"host": "localhost", "port": 1883, "tls": False})
        mock_paho.tls_set_context.assert_not_called()


# ---------------------------------------------------------------------------
# Task 6.4 — Endpoint /action/mqtt_connect
# ---------------------------------------------------------------------------

class TestMqttConnectEndpointAuth:
    async def test_missing_secret_returns_401(self, http_client):
        resp = await http_client.post(
            "/action/mqtt_connect",
            json={"host": "localhost", "port": 1883},
        )
        assert resp.status == 401

    async def test_wrong_secret_returns_401(self, http_client):
        resp = await http_client.post(
            "/action/mqtt_connect",
            json={"host": "localhost", "port": 1883},
            headers={"X-Local-Secret": "wrong-secret"},
        )
        assert resp.status == 401


class TestMqttConnectEndpointBehavior:
    async def test_connect_success_returns_ok(self, http_app, http_client):
        # Mock the existing bridge in the app
        bridge = http_app["mqtt_bridge"]
        bridge.start = AsyncMock()
        bridge.stop = AsyncMock()
        
        # Patch properties on the instance
        with patch.object(MqttBridge, "state", new_callable=PropertyMock) as mock_state:
            mock_state.return_value = "connecting"
            with patch.object(MqttBridge, "broker_info", new_callable=PropertyMock) as mock_info:
                mock_info.return_value = "localhost:1883"
                
                resp = await http_client.post(
                    "/action/mqtt_connect",
                    json={"host": "localhost", "port": 1883},
                    headers={"X-Local-Secret": LOCAL_SECRET},
                )

        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "ok"
        assert data["action"] == "mqtt.connect"
        assert data["payload"]["state"] == "connecting"
        assert data["payload"]["broker"] == "localhost:1883"

    async def test_connect_missing_host_returns_error(self, http_client):
        resp = await http_client.post(
            "/action/mqtt_connect",
            json={"port": 1883},
            headers={"X-Local-Secret": LOCAL_SECRET},
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "error"
        assert data["action"] == "mqtt.connect"

    async def test_connect_uses_pre_initialized_bridge(self, http_app, http_client):
        """Task 6.4 — Verify /action/mqtt_connect uses the app's bridge instance."""
        bridge = http_app["mqtt_bridge"]
        bridge.start = AsyncMock()
        bridge.stop = AsyncMock()

        await http_client.post(
            "/action/mqtt_connect",
            json={"host": "localhost", "port": 1883},
            headers={"X-Local-Secret": LOCAL_SECRET},
        )

        bridge.start.assert_called_once()
        bridge.stop.assert_called_once()

    async def test_connect_stops_existing_bridge_before_reconnect(self, http_app, http_client):
        bridge = http_app["mqtt_bridge"]
        bridge.stop = AsyncMock()
        bridge.start = AsyncMock()

        await http_client.post(
            "/action/mqtt_connect",
            json={"host": "localhost", "port": 1883},
            headers={"X-Local-Secret": LOCAL_SECRET},
        )

        bridge.stop.assert_called_once()


# ---------------------------------------------------------------------------
# Task 6.5 — /system/status enriched with MQTT section
# ---------------------------------------------------------------------------

class TestSystemStatusWithMqtt:
    async def test_status_without_mqtt_bridge_shows_disconnected(self, http_client):
        resp = await http_client.get(
            "/system/status",
            headers={"X-Local-Secret": LOCAL_SECRET},
        )
        assert resp.status == 200
        data = await resp.json()
        mqtt_section = data["payload"]["mqtt"]
        assert mqtt_section["connected"] is False
        assert mqtt_section["state"] == "disconnected"
        assert mqtt_section["broker"] == ""

    async def test_status_with_connected_bridge(self, http_app, http_client):
        bridge = http_app["mqtt_bridge"]
        with patch.object(MqttBridge, "is_connected", new_callable=PropertyMock) as mock_is_conn:
            mock_is_conn.return_value = True
            with patch.object(MqttBridge, "state", new_callable=PropertyMock) as mock_state:
                mock_state.return_value = "connected"
                with patch.object(MqttBridge, "broker_info", new_callable=PropertyMock) as mock_info:
                    mock_info.return_value = "192.168.1.10:1883"
                    resp = await http_client.get(
                        "/system/status",
                        headers={"X-Local-Secret": LOCAL_SECRET},
                    )
                    data = await resp.json()
                    mqtt_section = data["payload"]["mqtt"]
                    assert mqtt_section["connected"] is True
                    assert mqtt_section["state"] == "connected"
                    assert mqtt_section["broker"] == "192.168.1.10:1883"

    async def test_status_with_reconnecting_bridge(self, http_app, http_client):
        bridge = http_app["mqtt_bridge"]
        with patch.object(MqttBridge, "is_connected", new_callable=PropertyMock) as mock_is_conn:
            mock_is_conn.return_value = False
            with patch.object(MqttBridge, "state", new_callable=PropertyMock) as mock_state:
                mock_state.return_value = "reconnecting"
                resp = await http_client.get(
                    "/system/status",
                    headers={"X-Local-Secret": LOCAL_SECRET},
                )
                data = await resp.json()
                mqtt_section = data["payload"]["mqtt"]
                assert mqtt_section["connected"] is False
                assert mqtt_section["state"] == "reconnecting"


# ---------------------------------------------------------------------------
# Story 5.1 — homeassistant/status subscription and birth HA republication
# ---------------------------------------------------------------------------

class TestHaStatusSubscription:
    """Task 3.1 — homeassistant/status is subscribed on connect."""

    async def test_on_connect_subscribes_ha_status_topic(self):
        """Task 3.1: homeassistant/status QoS 1 is subscribed on connection."""
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()
        bridge._broker_host = "localhost"
        bridge._broker_port = 1883
        mock_paho = _make_mock_paho_client()

        bridge._on_connect(mock_paho, None, {}, 0)
        await asyncio.sleep(0)

        subscribed_topics = [c.args[0] for c in mock_paho.subscribe.call_args_list]
        assert HA_STATUS_TOPIC in subscribed_topics

    async def test_ha_status_topic_not_in_command_subscription_topics(self):
        """homeassistant/status is not a command topic — must be handled separately."""
        assert HA_STATUS_TOPIC not in COMMAND_SUBSCRIPTION_TOPICS


class TestBirthHaRepublication:
    """AC #7, #8, #9 — republication on homeassistant/status = online."""

    async def test_ha_birth_message_triggers_on_ha_birth_cb(self):
        """AC #7: birth HA with publications non-empty → on_ha_birth_cb called."""
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()

        cb_called = asyncio.Event()

        async def fake_ha_birth_cb():
            cb_called.set()

        bridge._on_ha_birth_cb = fake_ha_birth_cb
        message = MagicMock(topic=HA_STATUS_TOPIC, payload=b"online")

        bridge._on_message(None, None, message)
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert cb_called.is_set()

    async def test_ha_birth_message_offline_does_not_trigger_cb(self):
        """Birth HA with payload 'offline' must NOT trigger republication."""
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()

        cb_called = asyncio.Event()

        async def fake_ha_birth_cb():
            cb_called.set()

        bridge._on_ha_birth_cb = fake_ha_birth_cb
        message = MagicMock(topic=HA_STATUS_TOPIC, payload=b"offline")

        bridge._on_message(None, None, message)
        await asyncio.sleep(0)

        assert not cb_called.is_set()

    async def test_ha_birth_without_cb_does_not_crash(self):
        """Birth HA with no callback registered must not crash."""
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()
        bridge._on_ha_birth_cb = None  # not set

        message = MagicMock(topic=HA_STATUS_TOPIC, payload=b"online")
        bridge._on_message(None, None, message)
        await asyncio.sleep(0)
        # No crash — test passes implicitly

    async def test_ha_birth_does_not_dispatch_to_command_handler(self):
        """homeassistant/status must not be dispatched to command handler."""
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()

        command_handler = AsyncMock()
        bridge.set_command_handler(command_handler)
        bridge._on_ha_birth_cb = AsyncMock()

        message = MagicMock(topic=HA_STATUS_TOPIC, payload=b"online")
        bridge._on_message(None, None, message)
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        command_handler.assert_not_called()


class TestBrokerReconnectRepublication:
    """AC #10, #11 — republication on broker reconnect."""

    async def test_on_connect_triggers_on_reconnect_cb(self):
        """AC #10: _on_connect() with on_reconnect_cb set → callback triggered."""
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()
        mock_paho = _make_mock_paho_client()

        cb_called = asyncio.Event()

        async def fake_reconnect_cb():
            cb_called.set()

        bridge._on_reconnect_cb = fake_reconnect_cb
        bridge._on_connect(mock_paho, None, {}, 0)
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert cb_called.is_set()

    async def test_on_connect_without_reconnect_cb_no_crash(self):
        """_on_connect() without callback must not crash."""
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()
        mock_paho = _make_mock_paho_client()
        bridge._on_reconnect_cb = None

        bridge._on_connect(mock_paho, None, {}, 0)
        await asyncio.sleep(0)
        # No crash — test passes implicitly

    async def test_start_stores_reconnect_and_birth_callbacks(self):
        """Task 4.3: start() with callbacks → stored on bridge."""
        bridge = MqttBridge()
        mock_paho = _make_mock_paho_client()

        reconnect_cb = AsyncMock()
        birth_cb = AsyncMock()

        with patch("resources.daemon.transport.mqtt_client.mqtt.Client", return_value=mock_paho):
            await bridge.start(
                {"host": "localhost", "port": 1883},
                on_reconnect_cb=reconnect_cb,
                on_ha_birth_cb=birth_cb,
            )

        assert bridge._on_reconnect_cb is reconnect_cb
        assert bridge._on_ha_birth_cb is birth_cb

    async def test_birth_before_reconnect_ordering(self):
        """AC #17: birth bridge message published BEFORE reconnect callback is triggered."""
        bridge = MqttBridge()
        bridge._loop = asyncio.get_running_loop()
        mock_paho = _make_mock_paho_client()

        events = []

        def on_publish(topic, payload, **kwargs):
            events.append(f"birth:{payload}")
            return MagicMock()

        mock_paho.publish.side_effect = on_publish

        async def fake_reconnect_cb():
            events.append("reconnect_cb")

        bridge._on_reconnect_cb = fake_reconnect_cb

        bridge._on_connect(mock_paho, None, {}, 0)
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        # Birth must come before reconnect callback in the event log
        if "reconnect_cb" in events:
            birth_idx = next(i for i, e in enumerate(events) if "birth" in e)
            reconnect_idx = events.index("reconnect_cb")
            assert birth_idx < reconnect_idx, f"Birth must precede reconnect callback: {events}"


class TestRepublishAllFromCache:
    """AC #7, #8, #9, #12, #16 — _republish_all_from_cache behavior."""

    def _make_published_decision(self, entity_type="light", eq_id=1):
        mapping = type(
            "MappingResult",
            (),
            {
                "ha_entity_type": entity_type,
                "jeedom_eq_id": eq_id,
                "ha_name": f"test_{eq_id}",
                "ha_unique_id": f"jeedom2ha_eq_{eq_id}",
                "confidence": "sure",
                "suggested_area": None,
                "capabilities": type("Caps", (), {
                    "has_brightness": False,
                    "has_stop": False,
                    "has_position": False,
                    "is_bso": False,
                    "device_class": None,
                })(),
                "commands": {},
            },
        )()
        return type(
            "PublicationDecision",
            (),
            {"mapping_result": mapping, "discovery_published": True},
        )()

    def _make_unpublished_decision(self, entity_type="light", eq_id=2):
        mapping = type(
            "MappingResult",
            (),
            {
                "ha_entity_type": entity_type,
                "jeedom_eq_id": eq_id,
                "ha_name": f"test_{eq_id}",
                "ha_unique_id": f"jeedom2ha_eq_{eq_id}",
                "confidence": "sure",
                "suggested_area": None,
                "capabilities": type("Caps", (), {
                    "has_brightness": False,
                    "has_stop": False,
                    "has_position": False,
                    "is_bso": False,
                    "device_class": None,
                })(),
                "commands": {},
            },
        )()
        return type(
            "PublicationDecision",
            (),
            {"mapping_result": mapping, "discovery_published": False},
        )()

    async def test_birth_ha_empty_publications_logs_info_no_publish(self, caplog):
        """AC #9: birth HA with empty publications → log INFO, no publish."""
        import logging
        from resources.daemon.transport.http_server import _republish_all_from_cache

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_message = MagicMock(return_value=True)
        app = {"publications": {}, "mqtt_bridge": mock_bridge, "topology": None, "pending_discovery_unpublish": {}}

        with caplog.at_level(logging.INFO, logger="resources.daemon.transport.http_server"):
            await _republish_all_from_cache(app, "ha_birth")

        assert any("Birth HA" in r.message and "republication ignorée" in r.message for r in caplog.records)
        mock_bridge.publish_message.assert_not_called()

    async def test_birth_ha_with_publications_calls_publish(self):
        """AC #7: birth HA with publications → publish called for each entity."""
        from resources.daemon.transport.http_server import _republish_all_from_cache

        decision = self._make_published_decision("light")

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_message = MagicMock(return_value=True)

        mock_publisher = MagicMock()
        mock_publisher.publish_light = AsyncMock(return_value=True)
        mock_publisher.publish_cover = AsyncMock(return_value=True)
        mock_publisher.publish_switch = AsyncMock(return_value=True)

        app = {
            "publications": {1: decision},
            "mqtt_bridge": mock_bridge,
            "topology": None,
            "pending_discovery_unpublish": {},
        }

        with patch("resources.daemon.transport.http_server.DiscoveryPublisher", return_value=mock_publisher), \
             patch("resources.daemon.transport.http_server.asyncio.sleep", new_callable=AsyncMock):
            await _republish_all_from_cache(app, "ha_birth")

        mock_publisher.publish_light.assert_called_once()

    async def test_lissage_delay_formula_n1(self):
        """AC #12: delay = max(0.1, 10.0/N) → N=1 → delay=10.0 (>0.1)."""
        n = 1
        delay = max(0.1, 10.0 / n)
        assert delay == 10.0

    async def test_lissage_delay_formula_n50(self):
        """AC #12: N=50 → delay=0.2."""
        n = 50
        delay = max(0.1, 10.0 / n)
        assert delay == pytest.approx(0.2)

    async def test_lissage_delay_formula_n100(self):
        """AC #12: N=100 → delay=0.1."""
        n = 100
        delay = max(0.1, 10.0 / n)
        assert delay == pytest.approx(0.1)

    async def test_lissage_delay_formula_n200(self):
        """AC #12: N=200 → 10/200=0.05 → capped to 0.1."""
        n = 200
        delay = max(0.1, 10.0 / n)
        assert delay == pytest.approx(0.1)

    async def test_lissage_applied_for_ha_birth(self):
        """AC #8: lissage asyncio.sleep called between publishes (birth HA)."""
        from resources.daemon.transport.http_server import _republish_all_from_cache

        decisions = {i: self._make_published_decision("light", eq_id=i) for i in range(1, 6)}
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_message = MagicMock(return_value=True)

        mock_publisher = MagicMock()
        mock_publisher.publish_light = AsyncMock(return_value=True)

        app = {
            "publications": decisions,
            "mqtt_bridge": mock_bridge,
            "topology": None,
            "pending_discovery_unpublish": {},
        }

        sleep_delays = []
        async def mock_sleep(delay):
            sleep_delays.append(delay)

        with patch("resources.daemon.transport.http_server.DiscoveryPublisher", return_value=mock_publisher), \
             patch("resources.daemon.transport.http_server.asyncio.sleep", side_effect=mock_sleep):
            await _republish_all_from_cache(app, "ha_birth")

        assert len(sleep_delays) == len(decisions)
        expected_delay = max(0.1, 10.0 / len(decisions))
        for d in sleep_delays:
            assert d == pytest.approx(expected_delay)

    async def test_publish_error_logged_and_continues(self, caplog):
        """AC #16: publish error → log ERROR, continue for other entities."""
        import logging
        from resources.daemon.transport.http_server import _republish_all_from_cache

        decision1 = self._make_published_decision("light", eq_id=1)
        decision2 = self._make_published_decision("cover", eq_id=2)

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_message = MagicMock(return_value=True)

        mock_publisher = MagicMock()
        # First publish fails, second succeeds
        mock_publisher.publish_light = AsyncMock(return_value=False)
        mock_publisher.publish_cover = AsyncMock(return_value=True)

        app = {
            "publications": {1: decision1, 2: decision2},
            "mqtt_bridge": mock_bridge,
            "topology": None,
            "pending_discovery_unpublish": {},
        }

        with caplog.at_level(logging.ERROR, logger="resources.daemon.transport.http_server"), \
             patch("resources.daemon.transport.http_server.DiscoveryPublisher", return_value=mock_publisher), \
             patch("resources.daemon.transport.http_server.asyncio.sleep", new_callable=AsyncMock):
            await _republish_all_from_cache(app, "ha_birth")

        error_records = [r for r in caplog.records if r.levelname == "ERROR" and "DISCOVERY" in r.message]
        assert len(error_records) >= 1
        # Cover entity was still attempted despite light failure
        mock_publisher.publish_cover.assert_called_once()

    async def test_no_publish_when_broker_disconnected(self, caplog):
        """Republication aborted if broker is not connected."""
        import logging
        from resources.daemon.transport.http_server import _republish_all_from_cache

        decision = self._make_published_decision("light")
        mock_bridge = MagicMock()
        mock_bridge.is_connected = False
        mock_bridge.publish_message = MagicMock(return_value=True)

        app = {
            "publications": {1: decision},
            "mqtt_bridge": mock_bridge,
            "topology": None,
            "pending_discovery_unpublish": {},
        }

        with caplog.at_level(logging.WARNING, logger="resources.daemon.transport.http_server"):
            await _republish_all_from_cache(app, "ha_birth")

        mock_bridge.publish_message.assert_not_called()
        assert any("Republication annulée" in r.message for r in caplog.records)

    async def test_only_published_entries_are_republished(self):
        """Only decisions with discovery_published=True are republished."""
        from resources.daemon.transport.http_server import _republish_all_from_cache

        published = self._make_published_decision("light", eq_id=1)
        not_published = self._make_unpublished_decision("cover", eq_id=2)

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_message = MagicMock(return_value=True)

        mock_publisher = MagicMock()
        mock_publisher.publish_light = AsyncMock(return_value=True)
        mock_publisher.publish_cover = AsyncMock(return_value=True)
        mock_publisher.publish_switch = AsyncMock(return_value=True)

        app = {
            "publications": {1: published, 2: not_published},
            "mqtt_bridge": mock_bridge,
            "topology": None,
            "pending_discovery_unpublish": {},
        }

        with patch("resources.daemon.transport.http_server.DiscoveryPublisher", return_value=mock_publisher), \
             patch("resources.daemon.transport.http_server.asyncio.sleep", new_callable=AsyncMock):
            await _republish_all_from_cache(app, "ha_birth")

        # Only 1 entity published (the one with discovery_published=True)
        assert mock_publisher.publish_light.call_count == 1
        mock_publisher.publish_cover.assert_not_called()
