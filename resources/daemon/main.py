# jeedom2ha daemon
# Entry point for the Jeedom to Home Assistant asynchronous bridge daemon.
# This daemon communicates with the Jeedom PHP core via HTTP local API,
# and publishes entities to Home Assistant via MQTT Discovery.

import asyncio
import json
import logging
import os
import sys
from urllib.parse import urlparse, urlunparse

# Ensure resources/daemon/ is always in sys.path so `transport.http_server` can be
# imported both when Jeedom launches this as a script (sys.path[0] = resources/daemon/)
# and when imported as a package during tests (sys.path[0] = project root).
_DAEMON_DIR = os.path.dirname(os.path.abspath(__file__))
if _DAEMON_DIR not in sys.path:
    sys.path.insert(0, _DAEMON_DIR)

from jeedomdaemon.base_daemon import BaseDaemon
from jeedomdaemon.base_config import BaseConfig

from transport.http_server import create_app, start_server, stop_server
from sync.command import CommandSynchronizer
from sync.state import StateSynchronizer
from cache.disk_cache import load_publications_cache

# Résoudre le répertoire data/ relatif au daemon (data/ est un sibling de resources/)
_DAEMON_DATA_DIR = os.path.normpath(os.path.join(_DAEMON_DIR, "..", "..", "data"))

# plugin_info/info.json et VERSION sont à la racine du plugin, relatifs au daemon
# (même pattern que _DAEMON_DATA_DIR ci-dessus).
_PLUGIN_INFO_PATH = os.path.normpath(os.path.join(_DAEMON_DIR, "..", "..", "plugin_info", "info.json"))
_VERSION_FILE_PATH = os.path.normpath(os.path.join(_DAEMON_DIR, "..", "..", "VERSION"))

_UNKNOWN_VERSION = "inconnu"

_LOGGER = logging.getLogger(__name__)


def _read_plugin_version(info_json_path: str = _PLUGIN_INFO_PATH) -> str:
    """Read ``pluginVersion`` from plugin_info/info.json.

    Falls back to ``_UNKNOWN_VERSION`` if the file is absent, unreadable, not
    valid JSON, or valid JSON whose root is not an object (e.g. a list or a
    string) — the daemon must never crash on a missing/corrupt file.
    """
    try:
        with open(info_json_path, "r", encoding="utf-8") as fh:
            info = json.load(fh)
        if not isinstance(info, dict):
            return _UNKNOWN_VERSION
        return str(info.get("pluginVersion", _UNKNOWN_VERSION))
    except (OSError, ValueError):
        return _UNKNOWN_VERSION


def _read_deploy_sha(version_file_path: str = _VERSION_FILE_PATH) -> str:
    """Read the deployed commit SHA from the optional VERSION file at the
    plugin root, written by scripts/deploy-to-box.sh on deploy as
    ``key=value`` lines (``version=``, ``sha=``, ``deployed_at=``,
    ``git_status=`` — see jeedom2ha_render_version_content).

    Falls back to ``_UNKNOWN_VERSION`` if the file is absent, unreadable, or
    has no ``sha=`` line.
    """
    try:
        with open(version_file_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("sha="):
                    sha = line[len("sha="):].strip()
                    return sha or _UNKNOWN_VERSION
        return _UNKNOWN_VERSION
    except OSError:
        return _UNKNOWN_VERSION


_VERSION = _read_plugin_version()
_DEPLOY_SHA = _read_deploy_sha()


async def _boot_watchdog(app: dict, timeout_s: float = 90.0) -> None:
    """Watch for the first /action/sync after daemon boot.

    If no valid sync is received within timeout_s seconds, log a WARNING.
    Cancels itself as soon as app["boot_sync_received"] is set by the sync handler.

    Guardrail: never publishes anything — only logs.
    """
    try:
        sync_event = app.get("boot_sync_received")
        if sync_event is None:
            return
        await asyncio.wait_for(sync_event.wait(), timeout=timeout_s)
    except asyncio.TimeoutError:
        if not app.get("publications"):
            _LOGGER.warning(
                "[BOOTSTRAP] Aucune topologie reçue depuis Jeedom après %ds — "
                "aucune publication en attente",
                int(timeout_s),
            )


def _derive_jeedom_api_endpoint(callback_url: str) -> str:
    """Build the local Jeedom JSON-RPC endpoint from daemon callback URL."""
    if not callback_url:
        return ""

    parsed = urlparse(callback_url)
    if not parsed.scheme or not parsed.netloc:
        return ""

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            "/core/api/jeeApi.php",
            "",
            "",
            "",
        )
    )


def _load_secrets_file(path: str) -> dict[str, str]:
    """Read a ``KEY=VALUE`` secrets file (one entry per line) into a dict.

    Blank lines and lines without ``=`` are ignored. Values are not stripped
    of surrounding whitespace beyond the trailing newline, to tolerate secrets
    containing leading/trailing significant characters.
    """
    secrets: dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or "=" not in line:
                continue
            key, _, value = line.partition("=")
            secrets[key.strip()] = value
    return secrets


class Jeedom2haConfig(BaseConfig):
    """Custom configuration adding --apiport and --localsecret for the local HTTP API.

    CC-08 hygiène des clés : ``apikey``/``localsecret``/``jeedomcoreapikey`` ne
    sont plus nécessairement fournis en argv (visibles via ``ps aux``). Quand
    ``--secretsfile`` est fourni, ces trois valeurs sont relues depuis ce
    fichier (permissions 0600, hors arborescence versionnée du plugin) et
    injectées dans les args parsées, en mémoire uniquement — jamais visible
    dans la ligne de commande du process.
    """

    def __init__(self):
        super().__init__()
        self.add_argument("--apiport", type=int, default=55080)
        self.add_argument("--localsecret", type=str, default="")
        self.add_argument("--jeedomcoreapikey", type=str, default="")
        self.add_argument("--secretsfile", type=str, default="")

    def parse(self, args=None):
        super().parse(args)
        secretsfile = getattr(self._args, "secretsfile", "") or ""
        if not secretsfile:
            return
        secrets = _load_secrets_file(secretsfile)
        for key in ("apikey", "localsecret", "jeedomcoreapikey"):
            if key in secrets:
                setattr(self._args, key, secrets[key])


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
        self._command_synchronizer = None

    async def on_start(self):
        """Called once after daemon connects to Jeedom.

        Initializes the local HTTP API server.
        Boot sequence (Story 5.1):
          1. Load disk cache → app["boot_cache"]
          2. Initialize boot_sync_received Event
          3. Start boot watchdog (90s)
          4. Start HTTP server
        """
        _LOGGER.info("[DAEMON] jeedom2ha daemon v%s (sha %s) starting", _VERSION, _DEPLOY_SHA)

        local_secret = self._config.localsecret
        if not local_secret:
            _LOGGER.warning("[DAEMON] No local_secret provided — HTTP API will reject all requests")

        self._app = create_app(local_secret=local_secret)

        # Story 5.1 — Task 1.3: Load disk cache before MQTT connects
        boot_cache = load_publications_cache(_DAEMON_DATA_DIR)
        self._app["boot_cache"] = boot_cache

        # Story 5.1 — Task 2.1: Initialize boot sync event and start watchdog
        self._app["boot_sync_received"] = asyncio.Event()
        asyncio.create_task(_boot_watchdog(self._app, timeout_s=90))
        jeedom_api_endpoint = _derive_jeedom_api_endpoint(getattr(self._config, "callback", ""))
        plugin_apikey = getattr(self._config, "apikey", "")
        core_apikey = getattr(self._config, "jeedomcoreapikey", "")
        self._app["jeedom_api"] = {
            "endpoint": jeedom_api_endpoint,
            "apikey": plugin_apikey,
            "core_apikey": core_apikey,
        }
        self._command_synchronizer = CommandSynchronizer(
            app=self._app,
            mqtt_bridge=self._app.get("mqtt_bridge"),
            jeedom_api_endpoint=jeedom_api_endpoint,
            jeedom_core_apikey=core_apikey,
            request_timeout=2.0,
        )
        self._app["command_synchronizer"] = self._command_synchronizer
        # Story 12.1 — streaming d'état Jeedom → HA (vague 1 sensor/binary_sensor).
        # Le bridge est un objet stable créé dans create_app ; is_connected bascule
        # à la connexion. CommandSynchronizer consulte app["state_synchronizer"].
        self._app["state_synchronizer"] = StateSynchronizer(
            app=self._app,
            mqtt_bridge=self._app.get("mqtt_bridge"),
        )
        mqtt_bridge = self._app.get("mqtt_bridge")
        if mqtt_bridge is not None:
            mqtt_bridge.set_command_handler(self._command_synchronizer.handle_command_message)
        try:
            self._http_runner = await start_server(
                self._app,
                host="127.0.0.1",
                port=self._config.apiport,
            )
        except Exception:
            if self._command_synchronizer is not None:
                try:
                    await self._command_synchronizer.stop()
                except Exception:
                    _LOGGER.exception("[DAEMON] Failed to stop command synchronizer during startup rollback")
            self._command_synchronizer = None
            self._http_runner = None
            if mqtt_bridge is not None:
                mqtt_bridge.set_command_handler(None)
            self._app = None
            raise

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
            command_sync = self._command_synchronizer or self._app.get("command_synchronizer")
            if command_sync is not None:
                await command_sync.stop()
                self._command_synchronizer = None
            mqtt_bridge = self._app.get("mqtt_bridge")
            if mqtt_bridge is not None:
                mqtt_bridge.set_command_handler(None)
                await mqtt_bridge.stop()
        # 2. Stop HTTP server
        await stop_server(self._http_runner)
        self._http_runner = None
        self._app = None


if __name__ == "__main__":
    Jeedom2haDaemon().run()
