"""
test_http_server.py — Unit tests for the daemon's local HTTP API server.

Tests the /system/status endpoint, local_secret authentication,
and server lifecycle (start/stop).
"""
import pytest
from unittest.mock import patch
from aiohttp import web

_FAKE_CLI_ARGS = [
    "--loglevel", "debug",
    "--sockethost", "127.0.0.1",
    "--socketport", "0",
    "--callback", "http://127.0.0.1/fake",
    "--apikey", "test-api-key",
    "--pid", "/tmp/test-jeedom2ha.pid",
    "--cycle", "0.5",
]

LOCAL_SECRET = "test-secret-abc123"


@pytest.fixture(autouse=True)
def fake_cli_args():
    with patch("sys.argv", ["main.py"] + _FAKE_CLI_ARGS):
        yield


@pytest.fixture
def http_app():
    """Create the aiohttp app from our HTTP server module."""
    from resources.daemon.transport.http_server import create_app

    return create_app(local_secret=LOCAL_SECRET)


@pytest.fixture
async def http_client(http_app, aiohttp_client):
    """Create a test client for the HTTP API."""
    return await aiohttp_client(http_app)


class TestSystemStatusEndpoint:
    """Test the /system/status endpoint."""

    async def test_status_returns_200_with_valid_secret(self, http_client):
        """Given a valid local_secret,
        When GET /system/status is called,
        Then it should return 200 with structured payload."""
        resp = await http_client.get(
            "/system/status",
            headers={"X-Local-Secret": LOCAL_SECRET},
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["action"] == "system.status"
        assert data["status"] == "ok"
        assert "payload" in data
        assert "version" in data["payload"]
        assert "uptime" in data["payload"]
        assert "request_id" in data
        assert "timestamp" in data

    async def test_status_payload_version(self, http_client):
        """Given a valid request,
        When GET /system/status returns,
        Then payload.version should be '0.1.0'."""
        resp = await http_client.get(
            "/system/status",
            headers={"X-Local-Secret": LOCAL_SECRET},
        )
        data = await resp.json()
        assert data["payload"]["version"] == "0.2.0"

    async def test_status_payload_uptime_is_number(self, http_client):
        """Given a valid request,
        When GET /system/status returns,
        Then payload.uptime should be a non-negative number."""
        resp = await http_client.get(
            "/system/status",
            headers={"X-Local-Secret": LOCAL_SECRET},
        )
        data = await resp.json()
        assert isinstance(data["payload"]["uptime"], (int, float))
        assert data["payload"]["uptime"] >= 0


class TestLocalSecretAuth:
    """Test local_secret authentication."""

    async def test_missing_secret_returns_401(self, http_client):
        """Given no local_secret header,
        When GET /system/status is called,
        Then it should return 401."""
        resp = await http_client.get("/system/status")
        assert resp.status == 401

    async def test_wrong_secret_returns_401(self, http_client):
        """Given an invalid local_secret,
        When GET /system/status is called,
        Then it should return 401."""
        resp = await http_client.get(
            "/system/status",
            headers={"X-Local-Secret": "wrong-secret"},
        )
        assert resp.status == 401

    async def test_empty_secret_returns_401(self, http_client):
        """Given an empty local_secret,
        When GET /system/status is called,
        Then it should return 401."""
        resp = await http_client.get(
            "/system/status",
            headers={"X-Local-Secret": ""},
        )
        assert resp.status == 401


class TestSyncAction:
    """Test the /action/sync endpoint."""

    @pytest.fixture
    def mock_mqtt(self, http_app):
        with patch("resources.daemon.transport.mqtt_client.MqttBridge", autospec=True) as mock_cls:
            bridge = mock_cls.return_value
            bridge.is_connected = True
            bridge.publish_message.return_value = True
            # Inject into the app already created by http_app fixture
            http_app["mqtt_bridge"] = bridge
            yield bridge

    async def test_sync_no_secret(self, http_client):
        resp = await http_client.post("/action/sync", json={})
        assert resp.status == 401

    async def test_sync_publishes_sensor_and_state(self, http_client, mock_mqtt):
        """Test that sync correctly calls publisher for sensors and publishes initial state."""
        payload = {
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
                            "id": "10",
                            "generic_type": "TEMPERATURE",
                            "name": "Temp",
                            "type": "info",
                            "sub_type": "numeric",
                            "is_historized": "0",
                            "unit": "°C",
                            "current_value": 21.5
                        }
                    ]
                }
            ],
            "objects": [
                {"id": "1", "name": "Jardin"}
            ]
        }

        resp = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload}
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "ok"
        assert data["payload"]["mapping_summary"]["sensors_sure"] == 1
        assert data["payload"]["mapping_summary"]["sensors_published"] == 1

        # Check MQTT calls
        publish_calls = mock_mqtt.publish_message.call_args_list
        # Should be two calls: config then state
        assert len(publish_calls) >= 2
        
        # 1. Config call
        config_call = [c for c in publish_calls if c.args[0].endswith("/config")]
        assert len(config_call) == 1
        assert config_call[0].args[0] == "homeassistant/sensor/jeedom2ha_cmd_10/config"
        
        # 2. State call
        state_call = [c for c in publish_calls if c.args[0].endswith("/state")]
        assert len(state_call) == 1
        assert state_call[0].args[0] == "jeedom2ha/cmd/10/state"
        assert state_call[0].args[1] == "21.5"


    async def test_sync_unpublishes_deleted_sensor(self, http_client, mock_mqtt):
        """Test unpublish (by ha_unique_id) when a sensor disappears."""
        # 1. First sync with a sensor
        payload1 = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "1",
                    "name": "Test",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "cmds": [
                        {"id": "100", "name": "A", "type": "info", "sub_type": "numeric", "generic_type": "TEMPERATURE", "current_value": 25.0},
                    ]
                }
            ],
            "objects": [{"id": "1", "name": "Jardin"}]
        }
        await http_client.post("/action/sync", headers={"X-Local-Secret": LOCAL_SECRET}, json={"payload": payload1})
        mock_mqtt.publish_message.reset_mock()

        # 2. Second sync: sensor is missing
        payload2 = {
            "version": "1.0",
            "eq_logics": [], # Empty eq_logics
            "objects": [{"id": "1", "name": "Jardin"}]
        }
        await http_client.post("/action/sync", headers={"X-Local-Secret": LOCAL_SECRET}, json={"payload": payload2})

        # Should unpublish
        publish_calls = mock_mqtt.publish_message.call_args_list
        assert len(publish_calls) == 1
        call = publish_calls[0]
        topic, payload_json = call.args[0], call.args[1]
        assert topic == "homeassistant/sensor/jeedom2ha_cmd_100/config"
        assert payload_json == "" # Empty payload for deletion

    async def test_sync_unpublishes_deleted_light_using_eq_id_topic(self, http_client, mock_mqtt):
        """Actuators must still unpublish on eq_id-based discovery topics."""
        payload1 = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "2",
                    "name": "Lampe Salon",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "cmds": [
                        {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "LIGHT_STATE", "current_value": 0},
                        {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "LIGHT_ON"},
                        {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "LIGHT_OFF"},
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Salon"}],
        }
        await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload1},
        )
        mock_mqtt.publish_message.reset_mock()

        payload2 = {
            "version": "1.0",
            "eq_logics": [],
            "objects": [{"id": "1", "name": "Salon"}],
        }
        await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload2},
        )

        publish_calls = mock_mqtt.publish_message.call_args_list
        assert len(publish_calls) == 1
        call = publish_calls[0]
        topic, payload_json = call.args[0], call.args[1]
        assert topic == "homeassistant/light/jeedom2ha_2/config"
        assert payload_json == ""

    async def test_sync_does_not_publish_initial_state_if_discovery_fails(self, http_client, mock_mqtt):
        """Initial state publish requires a successful discovery config publish."""
        # First publish_message call is config publish (forced failure).
        mock_mqtt.publish_message.side_effect = [False]

        payload = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "3",
                    "name": "Temp Bureau",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "cmds": [
                        {
                            "id": "310",
                            "generic_type": "TEMPERATURE",
                            "name": "Temp",
                            "type": "info",
                            "sub_type": "numeric",
                            "unit": "°C",
                            "current_value": 19.4,
                        }
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Bureau"}],
        }

        resp = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload},
        )
        assert resp.status == 200

        publish_calls = mock_mqtt.publish_message.call_args_list
        assert len(publish_calls) == 1
        assert publish_calls[0].args[0] == "homeassistant/sensor/jeedom2ha_cmd_310/config"

    async def test_sync_mixed_switch_sensor_binary_sensor_returns_200(self, http_client, mock_mqtt):
        """Mixed sync payload (switch + sensor + binary_sensor) must not crash."""
        payload = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "187",
                    "name": "Machine à laver",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "cmds": [
                        {"id": "1871", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                        {"id": "1872", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                        {"id": "1873", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE", "current_value": 1},
                    ],
                },
                {
                    "id": "188",
                    "name": "Température Buanderie",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "cmds": [
                        {"id": "1881", "name": "Temp", "type": "info", "sub_type": "numeric", "generic_type": "TEMPERATURE", "unit": "°C", "current_value": 22.7},
                    ],
                },
                {
                    "id": "189",
                    "name": "Porte Buanderie",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "cmds": [
                        {"id": "1891", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "OPENING", "current_value": 1},
                    ],
                },
            ],
            "objects": [{"id": "1", "name": "Buanderie"}],
        }

        resp = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload},
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "ok"
        summary = data["payload"]["mapping_summary"]
        assert summary["switches_sure"] == 1
        assert summary["sensors_sure"] == 1
        assert summary["binary_sensors_sure"] == 1
