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
