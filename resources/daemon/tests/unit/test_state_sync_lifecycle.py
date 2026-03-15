"""Lifecycle robustness tests for Story 3.1 state synchronizer integration."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_FAKE_CLI_ARGS = [
    "--loglevel", "debug",
    "--sockethost", "127.0.0.1",
    "--socketport", "0",
    "--callback", "http://127.0.0.1/fake",
    "--apikey", "test-plugin-api-key",
    "--jeedomcoreapikey", "test-core-api-key",
    "--pid", "/tmp/test-jeedom2ha.pid",
    "--cycle", "0.5",
]


@pytest.fixture(autouse=True)
def fake_cli_args():
    with patch("sys.argv", ["main.py"] + _FAKE_CLI_ARGS):
        yield


@pytest.mark.asyncio
async def test_on_start_rolls_back_state_sync_when_http_start_fails():
    from resources.daemon.main import Jeedom2haDaemon

    daemon = Jeedom2haDaemon()
    fake_app = {"mqtt_bridge": MagicMock()}
    fake_sync = MagicMock()
    fake_sync.start = AsyncMock()
    fake_sync.stop = AsyncMock()

    with patch("resources.daemon.main.create_app", return_value=fake_app), \
         patch("resources.daemon.main.StateSynchronizer", return_value=fake_sync), \
         patch("resources.daemon.main.start_server", new_callable=AsyncMock, side_effect=RuntimeError("http startup failed")):
        with pytest.raises(RuntimeError):
            await daemon.on_start()

    fake_sync.start.assert_awaited_once()
    fake_sync.stop.assert_awaited_once()
    assert daemon._http_runner is None
    assert daemon._state_synchronizer is None
    assert daemon._app is None


@pytest.mark.asyncio
async def test_on_start_wires_plugin_and_core_apikeys_separately():
    from resources.daemon.main import Jeedom2haDaemon

    daemon = Jeedom2haDaemon()
    fake_bridge = MagicMock()
    fake_bridge.stop = AsyncMock()
    fake_app = {"mqtt_bridge": fake_bridge}
    fake_sync = MagicMock()
    fake_sync.start = AsyncMock()
    fake_sync.stop = AsyncMock()
    fake_runner = MagicMock()

    with patch("resources.daemon.main.create_app", return_value=fake_app), \
         patch("resources.daemon.main.StateSynchronizer", return_value=fake_sync) as mock_sync_cls, \
         patch("resources.daemon.main.start_server", new_callable=AsyncMock, return_value=fake_runner), \
         patch("resources.daemon.main.stop_server", new_callable=AsyncMock):
        await daemon.on_start()
        await daemon.on_stop()

    assert fake_app["jeedom_api"]["apikey"] == "test-plugin-api-key"
    assert fake_app["jeedom_api"]["core_apikey"] == "test-core-api-key"
    assert mock_sync_cls.call_args.kwargs["jeedom_core_apikey"] == "test-core-api-key"
