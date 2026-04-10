"""
test_mqtt_config.py — Unit tests for the daemon's /action/mqtt_test endpoint.

Tests the MQTT connection test endpoint with paho-mqtt mocked,
covering success and all categorized error types.
"""
import json
import socket
import ssl

import pytest
from unittest.mock import patch, MagicMock
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

LOCAL_SECRET = "test-secret-mqtt"


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


def _wrap_mqtt_payload(payload):
    return {
        "action": "mqtt.test",
        "payload": payload,
        "request_id": "test-req-id",
        "timestamp": "2024-03-13T12:00:00Z",
    }


def _make_mqtt_test_payload(
    host="localhost", port=1883, user="", password="",
    tls=False, tls_verify=True,
):
    payload = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "tls": tls,
        "tls_verify": tls_verify,
    }
    return _wrap_mqtt_payload(payload)


class TestMqttTestEndpointAuth:
    """Test /action/mqtt_test authentication."""

    async def test_missing_secret_returns_401(self, http_client):
        resp = await http_client.post(
            "/action/mqtt_test",
            json=_make_mqtt_test_payload(),
        )
        assert resp.status == 401

    async def test_wrong_secret_returns_401(self, http_client):
        resp = await http_client.post(
            "/action/mqtt_test",
            json=_make_mqtt_test_payload(),
            headers={"X-Local-Secret": "wrong"},
        )
        assert resp.status == 401


class TestMqttTestSuccess:
    """Test successful MQTT connection."""

    async def test_successful_connection(self, http_client):
        """Given valid broker params, connection test returns ok."""
        with patch(
            "resources.daemon.transport.http_server._sync_mqtt_connect"
        ) as mock_connect:
            mock_connect.return_value = {
                "ok": True,
                "message": "Connexion réussie",
            }
            resp = await http_client.post(
                "/action/mqtt_test",
                json=_make_mqtt_test_payload(),
                headers={"X-Local-Secret": LOCAL_SECRET},
            )
        assert resp.status == 200
        data = await resp.json()
        assert data["action"] == "mqtt.test"
        assert data["status"] == "ok"
        assert data["payload"]["connected"] is True
        assert data["message"] == "Connexion réussie"
        assert "request_id" in data
        assert "timestamp" in data


class TestMqttTestErrors:
    """Test categorized MQTT connection errors."""

    async def _test_error(self, http_client, mock_return, expected_error_code):
        with patch(
            "resources.daemon.transport.http_server._sync_mqtt_connect"
        ) as mock_connect:
            mock_connect.return_value = mock_return
            resp = await http_client.post(
                "/action/mqtt_test",
                json=_make_mqtt_test_payload(),
                headers={"X-Local-Secret": LOCAL_SECRET},
            )
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "error"
        assert data["payload"]["connected"] is False
        assert data["error_code"] == expected_error_code
        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0
        return data

    async def test_host_unreachable(self, http_client):
        await self._test_error(
            http_client,
            {"ok": False, "error_code": "host_unreachable",
             "message": "Hôte introuvable : vérifiez l'adresse du broker"},
            "host_unreachable",
        )

    async def test_port_refused(self, http_client):
        await self._test_error(
            http_client,
            {"ok": False, "error_code": "port_refused",
             "message": "Port refusé : le broker n'écoute pas sur ce port"},
            "port_refused",
        )

    async def test_auth_failed(self, http_client):
        await self._test_error(
            http_client,
            {"ok": False, "error_code": "auth_failed",
             "message": "Authentification refusée : vérifiez identifiant et mot de passe"},
            "auth_failed",
        )

    async def test_tls_error(self, http_client):
        await self._test_error(
            http_client,
            {"ok": False, "error_code": "tls_error",
             "message": "Erreur TLS : certificat invalide ou protocole non supporté"},
            "tls_error",
        )

    async def test_timeout(self, http_client):
        await self._test_error(
            http_client,
            {"ok": False, "error_code": "timeout",
             "message": "Délai dépassé : le broker ne répond pas"},
            "timeout",
        )

    async def test_unknown_error(self, http_client):
        await self._test_error(
            http_client,
            {"ok": False, "error_code": "unknown_error",
             "message": "Erreur inattendue : something went wrong"},
            "unknown_error",
        )

    async def test_missing_host_returns_error(self, http_client):
        """Host missing in payload returns missing_host error."""
        resp = await http_client.post(
            "/action/mqtt_test",
            json=_wrap_mqtt_payload({"port": 1883}),
            headers={"X-Local-Secret": LOCAL_SECRET},
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["error_code"] == "missing_host"

    async def test_invalid_port_returns_error(self, http_client):
        """Invalid port in payload returns invalid_port error."""
        resp = await http_client.post(
            "/action/mqtt_test",
            json=_wrap_mqtt_payload({"host": "localhost", "port": "not-a-number"}),
            headers={"X-Local-Secret": LOCAL_SECRET},
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["error_code"] == "invalid_port"


class TestSyncMqttConnect:
    """Test the synchronous _sync_mqtt_connect function directly."""

    def test_successful_connect(self):
        from resources.daemon.transport.http_server import _sync_mqtt_connect
        mock_client = MagicMock()
        connect_calls = []

        def fake_connect(host, port, keepalive=60):
            connect_calls.append((host, port))

        def fake_loop_start():
            # Simulate on_connect callback
            mock_client.on_connect(mock_client, None, {}, 0)

        mock_client.connect = fake_connect
        mock_client.loop_start = fake_loop_start
        mock_client.loop_stop = MagicMock()
        mock_client.disconnect = MagicMock()

        with patch("resources.daemon.transport.http_server.mqtt.Client", return_value=mock_client):
            result = _sync_mqtt_connect("localhost", 1883, "", "", False, True)

        assert result["ok"] is True
        assert result["message"] == "Connexion réussie"
        assert connect_calls == [("localhost", 1883)]

    def test_host_unreachable_gaierror(self):
        from resources.daemon.transport.http_server import _sync_mqtt_connect
        mock_client = MagicMock()
        mock_client.connect.side_effect = socket.gaierror("Name resolution failed")

        with patch("resources.daemon.transport.http_server.mqtt.Client", return_value=mock_client):
            result = _sync_mqtt_connect("nonexistent.host", 1883, "", "", False, True)

        assert result["ok"] is False
        assert result["error_code"] == "host_unreachable"

    def test_port_refused(self):
        from resources.daemon.transport.http_server import _sync_mqtt_connect
        mock_client = MagicMock()
        mock_client.connect.side_effect = ConnectionRefusedError("Connection refused")

        with patch("resources.daemon.transport.http_server.mqtt.Client", return_value=mock_client):
            result = _sync_mqtt_connect("localhost", 9999, "", "", False, True)

        assert result["ok"] is False
        assert result["error_code"] == "port_refused"

    def test_auth_failed_rc5(self):
        from resources.daemon.transport.http_server import _sync_mqtt_connect
        mock_client = MagicMock()

        def fake_loop_start():
            mock_client.on_connect(mock_client, None, {}, 5)

        mock_client.loop_start = fake_loop_start
        mock_client.loop_stop = MagicMock()
        mock_client.disconnect = MagicMock()

        with patch("resources.daemon.transport.http_server.mqtt.Client", return_value=mock_client):
            result = _sync_mqtt_connect("localhost", 1883, "user", "wrong", False, True)

        assert result["ok"] is False
        assert result["error_code"] == "auth_failed"

    def test_tls_error(self):
        from resources.daemon.transport.http_server import _sync_mqtt_connect
        mock_client = MagicMock()
        mock_client.connect.side_effect = ssl.SSLError("SSL handshake failed")

        with patch("resources.daemon.transport.http_server.mqtt.Client", return_value=mock_client):
            result = _sync_mqtt_connect("localhost", 8883, "", "", True, True)

        assert result["ok"] is False
        assert result["error_code"] == "tls_error"

    def test_timeout(self):
        from resources.daemon.transport.http_server import _sync_mqtt_connect
        mock_client = MagicMock()
        mock_client.connect.side_effect = socket.timeout("Connection timed out")

        with patch("resources.daemon.transport.http_server.mqtt.Client", return_value=mock_client):
            result = _sync_mqtt_connect("localhost", 1883, "", "", False, True)

        assert result["ok"] is False
        assert result["error_code"] == "timeout"

    def test_unknown_exception(self):
        from resources.daemon.transport.http_server import _sync_mqtt_connect
        mock_client = MagicMock()
        mock_client.connect.side_effect = OSError("Unexpected OS error")

        with patch("resources.daemon.transport.http_server.mqtt.Client", return_value=mock_client):
            result = _sync_mqtt_connect("localhost", 1883, "", "", False, True)

        assert result["ok"] is False
        assert result["error_code"] == "unknown_error"
        # Message contains exception type (not str(e) which may contain credentials)
        assert "OSError" in result["message"]

    def test_tls_with_verify_disabled(self):
        from resources.daemon.transport.http_server import _sync_mqtt_connect
        mock_client = MagicMock()

        def fake_loop_start():
            mock_client.on_connect(mock_client, None, {}, 0)

        mock_client.loop_start = fake_loop_start
        mock_client.loop_stop = MagicMock()
        mock_client.disconnect = MagicMock()

        with patch("resources.daemon.transport.http_server.mqtt.Client", return_value=mock_client) as mock_cls:
            with patch("resources.daemon.transport.http_server.ssl.create_default_context") as mock_ctx:
                ctx_instance = MagicMock()
                mock_ctx.return_value = ctx_instance
                result = _sync_mqtt_connect("localhost", 8883, "", "", True, False)

        assert result["ok"] is True
        # Verify TLS context was created with verification disabled
        assert ctx_instance.check_hostname is False
        assert ctx_instance.verify_mode == ssl.CERT_NONE
        mock_client.tls_set_context.assert_called_once_with(ctx_instance)

    def test_password_not_in_error_message(self):
        """Ensure password never leaks into error messages."""
        from resources.daemon.transport.http_server import _sync_mqtt_connect
        mock_client = MagicMock()
        secret_password = "super_secret_p@ssw0rd!"
        mock_client.connect.side_effect = OSError(f"Error with {secret_password}")

        with patch("resources.daemon.transport.http_server.mqtt.Client", return_value=mock_client):
            result = _sync_mqtt_connect("localhost", 1883, "user", secret_password, False, True)

        assert result["ok"] is False
        assert result["error_code"] == "unknown_error"
        # Password must NOT appear in the user-facing message
        assert secret_password not in result["message"]


class TestMqttCredentialsParsing:
    """Tests for correct credential parsing and username_pw_set call order."""

    async def test_username_field_passed_to_sync_connect(self, http_client):
        """Payload with 'username' key must be forwarded to _sync_mqtt_connect as user."""
        with patch(
            "resources.daemon.transport.http_server._sync_mqtt_connect"
        ) as mock_connect:
            mock_connect.return_value = {"ok": True, "message": "Connexion réussie"}
            resp = await http_client.post(
                "/action/mqtt_test",
                json=_wrap_mqtt_payload({
                    "host": "127.0.0.1",
                    "port": 1883,
                    "username": "jeedom",
                    "password": "secret",
                    "tls": False,
                    "tls_verify": False,
                }),
                headers={"X-Local-Secret": LOCAL_SECRET},
            )
        assert resp.status == 200
        mock_connect.assert_called_once()
        call_args = mock_connect.call_args[0]
        assert call_args[2] == "jeedom", "user arg must be 'jeedom' when 'username' key is sent"
        assert call_args[3] == "secret", "password arg must be forwarded"

    async def test_user_field_fallback_passed_to_sync_connect(self, http_client):
        """Payload with 'user' key (PHP callDaemon format) must also be forwarded correctly."""
        with patch(
            "resources.daemon.transport.http_server._sync_mqtt_connect"
        ) as mock_connect:
            mock_connect.return_value = {"ok": True, "message": "Connexion réussie"}
            resp = await http_client.post(
                "/action/mqtt_test",
                json=_wrap_mqtt_payload({
                    "host": "127.0.0.1",
                    "port": 1883,
                    "user": "jeedom",
                    "password": "secret",
                    "tls": False,
                    "tls_verify": True,
                }),
                headers={"X-Local-Secret": LOCAL_SECRET},
            )
        assert resp.status == 200
        mock_connect.assert_called_once()
        call_args = mock_connect.call_args[0]
        assert call_args[2] == "jeedom", "user arg must be 'jeedom' when 'user' key is sent"
        assert call_args[3] == "secret"

    async def test_username_takes_priority_over_user(self, http_client):
        """When both 'username' and 'user' are present, 'username' wins."""
        with patch(
            "resources.daemon.transport.http_server._sync_mqtt_connect"
        ) as mock_connect:
            mock_connect.return_value = {"ok": True, "message": "Connexion réussie"}
            await http_client.post(
                "/action/mqtt_test",
                json=_wrap_mqtt_payload({
                    "host": "127.0.0.1",
                    "port": 1883,
                    "username": "from_username",
                    "user": "from_user",
                    "password": "secret",
                    "tls": False,
                    "tls_verify": True,
                }),
                headers={"X-Local-Secret": LOCAL_SECRET},
            )
        call_args = mock_connect.call_args[0]
        assert call_args[2] == "from_username", "'username' must take priority over 'user'"

    def test_username_pw_set_called_before_connect(self):
        """username_pw_set must be called BEFORE connect, with named arguments."""
        from resources.daemon.transport.http_server import _sync_mqtt_connect
        mock_client = MagicMock()
        call_order = []

        def track_username_pw_set(*args, **kwargs):
            call_order.append("username_pw_set")

        def track_connect(*args, **kwargs):
            call_order.append("connect")

        def fake_loop_start():
            mock_client.on_connect(mock_client, None, {}, 0)

        mock_client.username_pw_set = MagicMock(side_effect=track_username_pw_set)
        mock_client.connect = MagicMock(side_effect=track_connect)
        mock_client.loop_start = fake_loop_start
        mock_client.loop_stop = MagicMock()
        mock_client.disconnect = MagicMock()

        with patch("resources.daemon.transport.http_server.mqtt.Client", return_value=mock_client):
            result = _sync_mqtt_connect("127.0.0.1", 1883, "jeedom", "secret", False, True)

        assert result["ok"] is True
        mock_client.username_pw_set.assert_called_once_with(username="jeedom", password="secret")
        assert call_order == ["username_pw_set", "connect"], (
            f"Expected username_pw_set before connect, got: {call_order}"
        )

    def test_username_pw_set_not_called_when_no_user(self):
        """When user is empty, username_pw_set must NOT be called (anonymous)."""
        from resources.daemon.transport.http_server import _sync_mqtt_connect
        mock_client = MagicMock()

        def fake_loop_start():
            mock_client.on_connect(mock_client, None, {}, 0)

        mock_client.loop_start = fake_loop_start
        mock_client.loop_stop = MagicMock()
        mock_client.disconnect = MagicMock()

        with patch("resources.daemon.transport.http_server.mqtt.Client", return_value=mock_client):
            result = _sync_mqtt_connect("127.0.0.1", 1883, "", "", False, True)

        assert result["ok"] is True
        mock_client.username_pw_set.assert_not_called()

    def test_password_not_in_sync_connect_logs(self, caplog):
        """Password must never appear in log records from _sync_mqtt_connect."""
        import logging
        from resources.daemon.transport.http_server import _sync_mqtt_connect
        mock_client = MagicMock()
        secret = "tmgFd7bXGBuTgEikEM31DwCX5LCT0S4F"
        mock_client.connect.side_effect = ConnectionRefusedError("refused")

        with patch("resources.daemon.transport.http_server.mqtt.Client", return_value=mock_client):
            with caplog.at_level(logging.DEBUG):
                _sync_mqtt_connect("127.0.0.1", 1883, "jeedom", secret, False, True)

        for record in caplog.records:
            assert secret not in record.getMessage(), (
                f"Password leaked in log: {record.getMessage()}"
            )
