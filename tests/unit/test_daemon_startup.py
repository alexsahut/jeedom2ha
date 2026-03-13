"""
test_daemon_startup.py — Unit tests for Jeedom2haDaemon class instantiation and lifecycle.

Tests the daemon skeleton: class creation, on_start/on_stop/on_message callbacks,
and custom CLI argument (--apiport).
"""
import pytest
from unittest.mock import patch


# Fake CLI args to satisfy BaseConfig.parse() without real CLI
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
    """Inject fake CLI args so BaseConfig.parse() succeeds without real CLI."""
    with patch("sys.argv", ["main.py"] + _FAKE_CLI_ARGS):
        yield


class TestDaemonInstantiation:
    """Test that Jeedom2haDaemon can be created and has expected interface."""

    def test_daemon_class_exists_and_inherits_base_daemon(self):
        """Given jeedomdaemon is available,
        When we import Jeedom2haDaemon,
        Then it should be a subclass of BaseDaemon."""
        from jeedomdaemon.base_daemon import BaseDaemon
        from resources.daemon.main import Jeedom2haDaemon

        assert issubclass(Jeedom2haDaemon, BaseDaemon)

    def test_daemon_can_be_instantiated(self):
        """Given the daemon class exists,
        When we instantiate it,
        Then it should not raise."""
        from resources.daemon.main import Jeedom2haDaemon

        daemon = Jeedom2haDaemon()
        assert daemon is not None

    def test_daemon_has_on_start_callback(self):
        """Given a daemon instance,
        When we check for on_start,
        Then it should be a callable async method."""
        from resources.daemon.main import Jeedom2haDaemon
        import asyncio

        daemon = Jeedom2haDaemon()
        assert hasattr(daemon, "on_start")
        assert asyncio.iscoroutinefunction(daemon.on_start)

    def test_daemon_has_on_stop_callback(self):
        """Given a daemon instance,
        When we check for on_stop,
        Then it should be a callable async method."""
        from resources.daemon.main import Jeedom2haDaemon
        import asyncio

        daemon = Jeedom2haDaemon()
        assert hasattr(daemon, "on_stop")
        assert asyncio.iscoroutinefunction(daemon.on_stop)

    def test_daemon_has_on_message_callback(self):
        """Given a daemon instance,
        When we check for on_message,
        Then it should be a callable async method."""
        from resources.daemon.main import Jeedom2haDaemon
        import asyncio

        daemon = Jeedom2haDaemon()
        assert hasattr(daemon, "on_message")
        assert asyncio.iscoroutinefunction(daemon.on_message)

    def test_daemon_config_has_apiport_argument(self):
        """Given the daemon's custom config,
        When we check the parsed config,
        Then --apiport should be available with default 55080."""
        from resources.daemon.main import Jeedom2haDaemon

        daemon = Jeedom2haDaemon()
        assert hasattr(daemon._config, "apiport")
        assert daemon._config.apiport == 55080

    def test_daemon_config_custom_apiport(self):
        """Given custom --apiport CLI arg,
        When daemon is instantiated,
        Then config should reflect the custom port."""
        from resources.daemon.main import Jeedom2haDaemon

        with patch("sys.argv", ["main.py"] + _FAKE_CLI_ARGS + ["--apiport", "9999"]):
            daemon = Jeedom2haDaemon()
            assert daemon._config.apiport == 9999


class TestDaemonOnStart:
    """Test on_start callback behavior."""

    async def test_on_start_runs_without_error(self):
        """Given a daemon instance,
        When on_start is called with a mocked HTTP server,
        Then it should complete without raising and assign the runner."""
        from unittest.mock import AsyncMock, MagicMock
        from resources.daemon.main import Jeedom2haDaemon

        daemon = Jeedom2haDaemon()
        mock_runner = MagicMock()
        with patch("resources.daemon.main.start_server", new_callable=AsyncMock, return_value=mock_runner):
            await daemon.on_start()
        assert daemon._http_runner is mock_runner

    async def test_on_start_calls_start_server_with_localhost(self):
        """Given a daemon instance,
        When on_start is called,
        Then start_server must be called with host='127.0.0.1'."""
        from unittest.mock import AsyncMock, MagicMock, call
        from resources.daemon.main import Jeedom2haDaemon

        daemon = Jeedom2haDaemon()
        with patch("resources.daemon.main.start_server", new_callable=AsyncMock, return_value=MagicMock()) as mock_start:
            await daemon.on_start()
        args, kwargs = mock_start.call_args
        assert kwargs.get("host", args[1] if len(args) > 1 else None) == "127.0.0.1"


class TestDaemonOnStop:
    """Test on_stop callback behavior."""

    async def test_on_stop_runs_without_error(self):
        """Given a daemon instance,
        When on_stop is called,
        Then it should complete without raising."""
        from resources.daemon.main import Jeedom2haDaemon

        daemon = Jeedom2haDaemon()
        await daemon.on_stop()


class TestDaemonOnMessage:
    """Test on_message callback behavior."""

    async def test_on_message_accepts_dict(self):
        """Given a daemon instance,
        When on_message is called with a message dict,
        Then it should complete without raising."""
        from resources.daemon.main import Jeedom2haDaemon

        daemon = Jeedom2haDaemon()
        await daemon.on_message({"action": "test", "apikey": "fake"})
