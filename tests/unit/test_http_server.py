"""
test_http_server.py — Unit tests for the daemon's local HTTP API server.

Tests the /system/status endpoint, local_secret authentication,
and server lifecycle (start/stop).
"""
import pytest
from unittest.mock import MagicMock, patch
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
    @pytest.fixture
    def mock_mqtt(self, http_app):
        bridge = MagicMock()
        bridge.is_connected = True
        bridge.publish_message.return_value = True
        http_app["mqtt_bridge"] = bridge
        return bridge

    async def test_sync_no_secret_returns_401(self, http_client):
        resp = await http_client.post("/action/sync", json={})
        assert resp.status == 401

    async def test_sync_populates_runtime_gating_fields_for_switch(self, http_client, http_app, mock_mqtt):
        payload = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "2",
                    "name": "Prise Salon",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "cmds": [
                        {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                        {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                        {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Salon"}],
        }

        resp = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload},
        )

        assert resp.status == 200
        decision = http_app["publications"][2]
        assert decision.should_publish is True
        assert decision.active_or_alive is True
        assert decision.state_topic == "jeedom2ha/2/state"
        mock_mqtt.publish_message.assert_called_once()

    async def test_sync_disables_runtime_gating_when_discovery_publish_fails(self, http_client, http_app, mock_mqtt):
        mock_mqtt.publish_message.return_value = False
        payload = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "2",
                    "name": "Prise Salon",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "cmds": [
                        {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                        {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                        {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Salon"}],
        }

        resp = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload},
        )

        assert resp.status == 200
        decision = http_app["publications"][2]
        assert decision.should_publish is False
        assert decision.active_or_alive is False
        assert decision.reason == "discovery_publish_failed"
        assert decision.state_topic == "jeedom2ha/2/state"

    async def test_sync_publishes_local_availability_retained_when_timeout_is_reliable(
        self,
        http_client,
        http_app,
        mock_mqtt,
    ):
        payload = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "2",
                    "name": "Prise Salon",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "status": {"timeout": "1"},
                    "cmds": [
                        {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                        {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                        {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Salon"}],
        }

        resp = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload},
        )
        assert resp.status == 200

        publish_calls = mock_mqtt.publish_message.call_args_list
        topics = [call.args[0] for call in publish_calls]
        assert "homeassistant/switch/jeedom2ha_2/config" in topics
        assert "jeedom2ha/2/availability" in topics

        availability_calls = [call for call in publish_calls if call.args[0] == "jeedom2ha/2/availability"]
        assert len(availability_calls) == 1
        assert availability_calls[0].args[1] == "offline"
        assert availability_calls[0].kwargs["retain"] is True

    async def test_sync_marks_runtime_not_alive_when_local_availability_publish_fails(
        self,
        http_client,
        http_app,
        mock_mqtt,
    ):
        payload = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "2",
                    "name": "Prise Salon",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "status": {"timeout": "1"},
                    "cmds": [
                        {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                        {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                        {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Salon"}],
        }

        def publish_side_effect(topic, payload_value, qos=1, retain=False):  # noqa: ARG001
            if topic == "jeedom2ha/2/availability":
                return False
            return True

        mock_mqtt.publish_message.side_effect = publish_side_effect

        resp = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload},
        )
        assert resp.status == 200

        decision = http_app["publications"][2]
        assert decision.should_publish is False
        assert decision.active_or_alive is False
        assert decision.reason == "local_availability_publish_failed"
        assert decision.local_availability_supported is True
        assert decision.local_availability_state == "offline"

        availability_calls = [
            call for call in mock_mqtt.publish_message.call_args_list
            if call.args[0] == "jeedom2ha/2/availability"
        ]
        assert len(availability_calls) == 1

    async def test_sync_does_not_publish_local_availability_when_timeout_not_reliable(
        self,
        http_client,
        http_app,
        mock_mqtt,
    ):
        payload = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "2",
                    "name": "Prise Salon",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "status": {"timeout": "unknown"},
                    "cmds": [
                        {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                        {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                        {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Salon"}],
        }

        resp = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload},
        )
        assert resp.status == 200

        topics = [call.args[0] for call in mock_mqtt.publish_message.call_args_list]
        assert "homeassistant/switch/jeedom2ha_2/config" in topics
        assert "jeedom2ha/2/availability" not in topics

    async def test_sync_downgrade_to_bridge_only_cleans_local_availability_topic(
        self,
        http_client,
        http_app,
        mock_mqtt,
    ):
        payload_local = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "2",
                    "name": "Prise Salon",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "status": {"timeout": "0"},
                    "cmds": [
                        {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                        {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                        {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Salon"}],
        }
        payload_bridge_only = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "2",
                    "name": "Prise Salon",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "status": {},
                    "cmds": [
                        {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                        {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                        {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Salon"}],
        }

        resp_first = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_local},
        )
        assert resp_first.status == 200

        resp_second = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_bridge_only},
        )
        assert resp_second.status == 200

        availability_calls = [
            call for call in mock_mqtt.publish_message.call_args_list
            if call.args[0] == "jeedom2ha/2/availability"
        ]
        assert len(availability_calls) >= 2
        assert availability_calls[0].args[1] == "online"
        assert availability_calls[-1].args[1] == ""
        assert availability_calls[-1].kwargs["retain"] is True

    async def test_sync_unpublish_cleans_local_availability_topic(
        self,
        http_client,
        http_app,
        mock_mqtt,
    ):
        payload_present = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "2",
                    "name": "Prise Salon",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "status": {"timeout": "0"},
                    "cmds": [
                        {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                        {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                        {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Salon"}],
        }
        payload_removed = {"version": "1.0", "eq_logics": [], "objects": [{"id": "1", "name": "Salon"}]}

        resp_first = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_present},
        )
        assert resp_first.status == 200

        resp_second = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_removed},
        )
        assert resp_second.status == 200

        availability_calls = [
            call for call in mock_mqtt.publish_message.call_args_list
            if call.args[0] == "jeedom2ha/2/availability"
        ]
        assert len(availability_calls) >= 2
        assert availability_calls[0].args[1] == "online"
        assert availability_calls[-1].args[1] == ""
        assert availability_calls[-1].kwargs["retain"] is True

    async def test_sync_downgrade_cleanup_is_deferred_when_broker_disconnected_then_replayed(
        self,
        http_client,
        http_app,
        mock_mqtt,
    ):
        payload_local = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "2",
                    "name": "Prise Salon",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "status": {"timeout": "0"},
                    "cmds": [
                        {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                        {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                        {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Salon"}],
        }
        payload_bridge_only = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "2",
                    "name": "Prise Salon",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "status": {},
                    "cmds": [
                        {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                        {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                        {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Salon"}],
        }

        resp_first = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_local},
        )
        assert resp_first.status == 200

        mock_mqtt.is_connected = False
        resp_second = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_bridge_only},
        )
        assert resp_second.status == 200
        assert http_app["pending_local_availability_cleanup"] == {2: "jeedom2ha/2/availability"}

        mock_mqtt.publish_message.reset_mock()
        mock_mqtt.is_connected = True
        resp_third = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_bridge_only},
        )
        assert resp_third.status == 200

        availability_calls = [
            call for call in mock_mqtt.publish_message.call_args_list
            if call.args[0] == "jeedom2ha/2/availability"
        ]
        assert len(availability_calls) == 1
        assert availability_calls[0].args[1] == ""
        assert availability_calls[0].kwargs["retain"] is True
        assert http_app["pending_local_availability_cleanup"] == {}

    async def test_sync_unpublish_discovery_is_deferred_when_broker_disconnected_then_replayed(
        self,
        http_client,
        http_app,
        mock_mqtt,
    ):
        payload_present = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "2",
                    "name": "Prise Salon",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "status": {},
                    "cmds": [
                        {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                        {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                        {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Salon"}],
        }
        payload_removed = {"version": "1.0", "eq_logics": [], "objects": [{"id": "1", "name": "Salon"}]}

        resp_first = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_present},
        )
        assert resp_first.status == 200

        mock_mqtt.is_connected = False
        resp_second = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_removed},
        )
        assert resp_second.status == 200
        assert http_app["pending_discovery_unpublish"] == {2: "switch"}
        assert http_app["pending_local_availability_cleanup"] == {}

        mock_mqtt.publish_message.reset_mock()
        mock_mqtt.is_connected = True
        resp_third = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_removed},
        )
        assert resp_third.status == 200

        discovery_unpublish_calls = [
            call for call in mock_mqtt.publish_message.call_args_list
            if call.args[0] == "homeassistant/switch/jeedom2ha_2/config"
        ]
        assert len(discovery_unpublish_calls) == 1
        assert discovery_unpublish_calls[0].args[1] == ""
        assert discovery_unpublish_calls[0].kwargs["retain"] is True
        assert http_app["pending_discovery_unpublish"] == {}

    async def test_sync_unpublish_cleanup_is_deferred_when_broker_disconnected_then_replayed(
        self,
        http_client,
        http_app,
        mock_mqtt,
    ):
        payload_present = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "2",
                    "name": "Prise Salon",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "status": {"timeout": "0"},
                    "cmds": [
                        {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                        {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                        {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Salon"}],
        }
        payload_removed = {"version": "1.0", "eq_logics": [], "objects": [{"id": "1", "name": "Salon"}]}

        resp_first = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_present},
        )
        assert resp_first.status == 200

        mock_mqtt.is_connected = False
        resp_second = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_removed},
        )
        assert resp_second.status == 200
        assert http_app["pending_discovery_unpublish"] == {2: "switch"}
        assert http_app["pending_local_availability_cleanup"] == {2: "jeedom2ha/2/availability"}

        mock_mqtt.publish_message.reset_mock()
        mock_mqtt.is_connected = True
        resp_third = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_removed},
        )
        assert resp_third.status == 200

        availability_calls = [
            call for call in mock_mqtt.publish_message.call_args_list
            if call.args[0] == "jeedom2ha/2/availability"
        ]
        discovery_unpublish_calls = [
            call for call in mock_mqtt.publish_message.call_args_list
            if call.args[0] == "homeassistant/switch/jeedom2ha_2/config"
        ]
        assert len(discovery_unpublish_calls) == 1
        assert discovery_unpublish_calls[0].args[1] == ""
        assert discovery_unpublish_calls[0].kwargs["retain"] is True
        assert len(availability_calls) == 1
        assert availability_calls[0].args[1] == ""
        assert availability_calls[0].kwargs["retain"] is True
        assert http_app["pending_discovery_unpublish"] == {}
        assert http_app["pending_local_availability_cleanup"] == {}

    async def test_sync_ineligible_entity_unpublish_is_deferred_when_broker_disconnected_then_replayed(
        self,
        http_client,
        http_app,
        mock_mqtt,
    ):
        payload_present = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "2",
                    "name": "Prise Salon",
                    "object_id": "1",
                    "is_enable": "1",
                    "eq_type": "virtual",
                    "status": {},
                    "cmds": [
                        {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                        {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                        {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Salon"}],
        }
        payload_ineligible = {
            "version": "1.0",
            "eq_logics": [
                {
                    "id": "2",
                    "name": "Prise Salon",
                    "object_id": "1",
                    "is_enable": "0",
                    "eq_type": "virtual",
                    "status": {},
                    "cmds": [
                        {"id": "210", "name": "Etat", "type": "info", "sub_type": "binary", "generic_type": "ENERGY_STATE"},
                        {"id": "211", "name": "On", "type": "action", "sub_type": "other", "generic_type": "ENERGY_ON"},
                        {"id": "212", "name": "Off", "type": "action", "sub_type": "other", "generic_type": "ENERGY_OFF"},
                    ],
                }
            ],
            "objects": [{"id": "1", "name": "Salon"}],
        }

        resp_first = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_present},
        )
        assert resp_first.status == 200

        mock_mqtt.is_connected = False
        resp_second = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_ineligible},
        )
        assert resp_second.status == 200
        assert http_app["pending_discovery_unpublish"] == {2: "switch"}

        mock_mqtt.publish_message.reset_mock()
        mock_mqtt.is_connected = True
        resp_third = await http_client.post(
            "/action/sync",
            headers={"X-Local-Secret": LOCAL_SECRET},
            json={"payload": payload_ineligible},
        )
        assert resp_third.status == 200

        discovery_unpublish_calls = [
            call for call in mock_mqtt.publish_message.call_args_list
            if call.args[0] == "homeassistant/switch/jeedom2ha_2/config"
        ]
        assert len(discovery_unpublish_calls) == 1
        assert discovery_unpublish_calls[0].args[1] == ""
        assert discovery_unpublish_calls[0].kwargs["retain"] is True
        assert http_app["pending_discovery_unpublish"] == {}
        assert http_app["pending_local_availability_cleanup"] == {}
