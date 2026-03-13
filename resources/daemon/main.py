# jeedom2ha daemon
# Entry point for the Jeedom to Home Assistant asynchronous bridge daemon.
# This daemon communicates with the Jeedom PHP core via HTTP local API,
# and publishes entities to Home Assistant via MQTT Discovery.

import logging
import os
import sys

# Ensure resources/daemon/ is always in sys.path so `transport.http_server` can be
# imported both when Jeedom launches this as a script (sys.path[0] = resources/daemon/)
# and when imported as a package during tests (sys.path[0] = project root).
_DAEMON_DIR = os.path.dirname(os.path.abspath(__file__))
if _DAEMON_DIR not in sys.path:
    sys.path.insert(0, _DAEMON_DIR)

from jeedomdaemon.base_daemon import BaseDaemon
from jeedomdaemon.base_config import BaseConfig

from transport.http_server import create_app, start_server, stop_server

_LOGGER = logging.getLogger(__name__)

_VERSION = "0.1.0"


class Jeedom2haConfig(BaseConfig):
    """Custom configuration adding --apiport and --localsecret for the local HTTP API."""

    def __init__(self):
        super().__init__()
        self.add_argument("--apiport", type=int, default=55080)
        self.add_argument("--localsecret", type=str, default="")


class Jeedom2haDaemon(BaseDaemon):
    """Jeedom2HA bridge daemon.

    Inherits from jeedomdaemon's BaseDaemon and adds:
    - A local HTTP API server for PHP → daemon communication
    - (Future) MQTT client for publishing HA discovery payloads
    """

    def __init__(self):
        super().__init__(
            config=Jeedom2haConfig(),
            on_start_cb=self.on_start,
            on_message_cb=self.on_message,
            on_stop_cb=self.on_stop,
        )
        self._http_runner = None
        self._app = None  # stored for access in on_stop()

    async def on_start(self):
        """Called once after daemon connects to Jeedom.

        Initializes the local HTTP API server.
        """
        _LOGGER.info("[DAEMON] jeedom2ha daemon v%s starting", _VERSION)

        local_secret = self._config.localsecret
        if not local_secret:
            _LOGGER.warning("[DAEMON] No local_secret provided — HTTP API will reject all requests")

        self._app = create_app(local_secret=local_secret)
        self._http_runner = await start_server(
            self._app,
            host="127.0.0.1",
            port=self._config.apiport,
        )

    async def on_message(self, message: list):
        """Handle incoming messages from Jeedom PHP core.

        Stub — will be implemented in future stories for action dispatching.
        """
        _LOGGER.debug("[DAEMON] Received message from Jeedom: %s", message)

    async def on_stop(self):
        """Called on daemon shutdown. Clean up resources.

        Shutdown order is critical:
        1. Stop MQTT bridge first (publish offline, disconnect cleanly)
        2. Stop HTTP server last
        """
        _LOGGER.info("[DAEMON] jeedom2ha daemon stopping")
        # 1. Stop MQTT bridge (publish offline before TCP connection drops)
        if self._app is not None:
            mqtt_bridge = self._app.get("mqtt_bridge")
            if mqtt_bridge is not None:
                await mqtt_bridge.stop()
        # 2. Stop HTTP server
        await stop_server(self._http_runner)
        self._http_runner = None
        self._app = None


if __name__ == "__main__":
    Jeedom2haDaemon().run()
