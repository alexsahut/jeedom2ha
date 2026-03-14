"""mqtt_client.py — Persistent MQTT bridge client for jeedom2ha.

Manages a long-lived MQTT connection with automatic reconnection (paho built-in),
LWT (Last Will and Testament), and birth messages.

Threading model: paho-mqtt runs its own network thread via loop_start().
Callbacks (on_connect, on_disconnect) execute in the paho thread.
State updates are marshalled back to the asyncio event loop via
loop.call_soon_threadsafe() so the rest of the daemon never touches
thread-unsafe structures from a non-async context.
"""
import asyncio
import logging
import ssl

import paho.mqtt.client as mqtt

_LOGGER = logging.getLogger(__name__)

BRIDGE_STATUS_TOPIC = "jeedom2ha/bridge/status"


class MqttBridge:
    """Persistent MQTT connection with LWT, birth message, and auto-reconnect.

    Lifecycle:
        await bridge.start(config)  — non-blocking, returns after initiating connect
        await bridge.stop()         — graceful: publishes offline, disconnects
    """

    def __init__(self):
        self._client = None
        self._state = "disconnected"  # disconnected | connecting | connected | reconnecting
        self._loop = None
        self._broker_host = ""
        self._broker_port = 0

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def start(self, config: dict):
        """Initiate persistent MQTT connection. Non-blocking — returns immediately.

        Args:
            config: dict with keys host, port, user, password, tls, tls_verify
        """
        self._loop = asyncio.get_running_loop()
        self._broker_host = config["host"]
        self._broker_port = int(config.get("port", 1883))

        # paho-mqtt 2.0+ compat: try new API, fall back to v1
        try:
            self._client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
                client_id="jeedom2ha_bridge",
                clean_session=True,
            )
        except AttributeError:
            self._client = mqtt.Client(client_id="jeedom2ha_bridge", clean_session=True)

        # LWT — broker publishes "offline" automatically on unclean disconnect
        self._client.will_set(BRIDGE_STATUS_TOPIC, "offline", qos=1, retain=True)
        _LOGGER.debug(
            "[MQTT] LWT configured: topic=%s payload=offline qos=1 retain=True",
            BRIDGE_STATUS_TOPIC,
        )

        # Register callbacks (called from paho thread)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        # Built-in exponential backoff reconnection (NFR6: < 30s)
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        # TLS (V1 — system CA only, no custom CA or mTLS)
        if config.get("tls", False):
            ctx = ssl.create_default_context()
            if not config.get("tls_verify", True):
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            self._client.tls_set_context(ctx)

        # Authentication
        user = config.get("user", "")
        if user:
            _LOGGER.debug("[MQTT] Setting credentials for user=%s", user)
            self._client.username_pw_set(user, config.get("password", ""))

        self._state = "connecting"
        _LOGGER.info(
            "[MQTT] Initiating persistent connection to %s:%d",
            self._broker_host,
            self._broker_port,
        )
        # Non-blocking connect — loop_start() drives the network thread
        self._client.connect_async(self._broker_host, self._broker_port, keepalive=60)
        self._client.loop_start()

    async def stop(self):
        """Graceful shutdown: publish offline status, disconnect, stop network thread."""
        if self._client is None:
            return
        _LOGGER.info("[MQTT] Stopping bridge, publishing offline status")
        try:
            msg_info = self._client.publish(BRIDGE_STATUS_TOPIC, "offline", qos=1, retain=True)
            # Ensure the offline message is sent before severing TCP connection (Fix for Finding 1)
            msg_info.wait_for_publish(timeout=2.0)
            self._client.disconnect()
        except Exception:
            pass
        self._client.loop_stop()
        self._client = None
        self._state = "disconnected"

    # ------------------------------------------------------------------
    # paho callbacks — executed in the paho network thread
    # ------------------------------------------------------------------

    def _on_connect(self, client, userdata, flags, rc):
        """Called by paho on connection result (paho thread)."""
        if rc == 0:
            _LOGGER.info(
                "[MQTT] Connected to broker %s:%d",
                self._broker_host,
                self._broker_port,
            )
            # Birth message — signals bridge availability to HA
            client.publish(BRIDGE_STATUS_TOPIC, "online", qos=1, retain=True)
            if self._loop is not None:
                self._loop.call_soon_threadsafe(self._set_state, "connected")
        else:
            _LOGGER.warning("[MQTT] Connection refused by broker (rc=%d)", rc)
            if self._loop is not None:
                self._loop.call_soon_threadsafe(self._set_state, "disconnected")

    def _on_disconnect(self, client, userdata, rc):
        """Called by paho on disconnect (paho thread). rc=0 = clean, rc!=0 = unexpected."""
        if rc != 0:
            _LOGGER.info("[MQTT] Unexpected disconnect (rc=%d), auto-reconnect in progress", rc)
            if self._loop is not None:
                self._loop.call_soon_threadsafe(self._set_state, "reconnecting")
        else:
            _LOGGER.info("[MQTT] Clean disconnect")
            if self._loop is not None:
                self._loop.call_soon_threadsafe(self._set_state, "disconnected")

    def _set_state(self, new_state: str):
        """State transition — must be called from asyncio thread via call_soon_threadsafe."""
        self._state = new_state

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> str:
        """Current connection state string."""
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == "connected"

    @property
    def broker_info(self) -> str:
        """'host:port' string, empty if not yet configured."""
        return f"{self._broker_host}:{self._broker_port}" if self._broker_host else ""

    def publish_message(self, topic: str, payload: str, qos: int = 1, retain: bool = False) -> bool:
        """Publish an MQTT message safely.

        Returns True if the message was queued, False if the client is not available.
        This is the safe public API for publishing — never access _client directly from outside.
        """
        if self._client is None:
            _LOGGER.warning("[MQTT] publish_message called but _client is None (bridge stopped?), topic=%s", topic)
            return False
        try:
            self._client.publish(topic, payload, qos=qos, retain=retain)
            return True
        except Exception as e:
            _LOGGER.error("[MQTT] publish_message failed on topic=%s: %s", topic, e)
            return False
