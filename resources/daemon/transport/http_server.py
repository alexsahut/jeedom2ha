"""Local HTTP API server for PHP → daemon communication.

Listens on 127.0.0.1 only, protected by a local_secret shared with the PHP plugin.
"""

import asyncio
import logging
import socket
import ssl
import time
import uuid
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from aiohttp import web

_LOGGER = logging.getLogger(__name__)

_VERSION = "0.1.0"


def _check_secret(request: web.Request, local_secret: str) -> bool:
    """Validate the local_secret from request header."""
    provided = request.headers.get("X-Local-Secret", "")
    if not provided or not local_secret:
        return False
    return provided == local_secret


async def _handle_system_status(request: web.Request) -> web.Response:
    """Handle GET /system/status — liveness probe."""
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response(
            {"status": "error", "message": "Unauthorized"},
            status=401,
        )

    uptime = time.monotonic() - request.app["start_time"]
    payload = {
        "action": "system.status",
        "status": "ok",
        "payload": {
            "version": _VERSION,
            "uptime": round(uptime, 2),
        },
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return web.json_response(payload)


def _sync_mqtt_connect(host, port, user, password, tls_enabled, tls_verify) -> dict:
    """Synchronous MQTT connection test. Returns {ok, error_code?, message}.

    Designed to be called via run_in_executor from an async handler.
    Never logs passwords — errors are categorized for user display.
    """
    # V1 — CA système uniquement (pas de CA custom ni mTLS)
    try:
        # paho-mqtt 2.0+
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id="jeedom2ha_test",
            clean_session=True,
        )
    except AttributeError:
        # paho-mqtt < 2.0
        client = mqtt.Client(client_id="jeedom2ha_test", clean_session=True)
    connect_result = {"rc": None}

    def on_connect(_client, _userdata, _flags, rc):
        connect_result["rc"] = rc

    client.on_connect = on_connect

    try:
        if tls_enabled:
            ctx = ssl.create_default_context()
            if not tls_verify:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            client.tls_set_context(ctx)
        if user:
            client.username_pw_set(user, password)

        client.connect(host, port, keepalive=10)
        client.loop_start()

        # Wait for on_connect callback (max 5s)
        deadline = time.monotonic() + 5.0
        while connect_result["rc"] is None and time.monotonic() < deadline:
            time.sleep(0.1)

        client.loop_stop()
        try:
            client.disconnect()
        except Exception:
            pass

        if connect_result["rc"] is None:
            return {
                "ok": False,
                "error_code": "timeout",
                "message": "Délai dépassé : le broker ne répond pas",
            }
        if connect_result["rc"] == 0:
            return {"ok": True, "message": "Connexion réussie"}
        if connect_result["rc"] == 5:
            return {
                "ok": False,
                "error_code": "auth_failed",
                "message": "Authentification refusée : vérifiez identifiant et mot de passe",
            }
        return {
            "ok": False,
            "error_code": "unknown_error",
            "message": f"Broker refusé (code {connect_result['rc']})",
        }
    except (socket.gaierror, socket.herror):
        return {
            "ok": False,
            "error_code": "host_unreachable",
            "message": "Hôte introuvable : vérifiez l'adresse du broker",
        }
    except ConnectionRefusedError:
        return {
            "ok": False,
            "error_code": "port_refused",
            "message": "Port refusé : le broker n'écoute pas sur ce port",
        }
    except (ssl.SSLError, ssl.CertificateError):
        return {
            "ok": False,
            "error_code": "tls_error",
            "message": "Erreur TLS : certificat invalide ou protocole non supporté",
        }
    except (socket.timeout, TimeoutError):
        return {
            "ok": False,
            "error_code": "timeout",
            "message": "Délai dépassé : le broker ne répond pas",
        }
    except Exception as e:
        # Log the exception type only — never log credentials that may appear in str(e)
        _LOGGER.warning("[MQTT] Unexpected error during connection test: %s", type(e).__name__)
        return {
            "ok": False,
            "error_code": "unknown_error",
            "message": f"Erreur inattendue ({type(e).__name__}) — consultez les logs du démon",
        }


async def _handle_mqtt_test(request: web.Request) -> web.Response:
    """Handle POST /action/mqtt_test — one-shot MQTT connection test."""
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response(
            {"status": "error", "message": "Unauthorized"},
            status=401,
        )

    data = await request.json()
    payload = data.get("payload", {})
    host = payload.get("host", "")
    port_raw = payload.get("port", 1883)

    # Validation d'entrée explicite
    if not host:
        return web.json_response({
            "action": "mqtt.test",
            "status": "error",
            "error_code": "missing_host",
            "message": "Hôte MQTT manquant",
        })
    try:
        port = int(port_raw)
        if not (1 <= port <= 65535):
            raise ValueError()
    except (ValueError, TypeError):
        return web.json_response({
            "action": "mqtt.test",
            "status": "error",
            "error_code": "invalid_port",
            "message": f"Port MQTT invalide : {port_raw}",
        })

    _LOGGER.info("[MQTT] Testing connection to %s:%s (TLS: %s)", host, port, payload.get("tls", False))

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        _sync_mqtt_connect,
        host,
        port,
        payload.get("user", ""),
        payload.get("password", ""),
        bool(payload.get("tls", False)),
        bool(payload.get("tls_verify", True)),
    )

    status = "ok" if result["ok"] else "error"
    payload = {
        "action": "mqtt.test",
        "status": status,
        "payload": {"connected": result["ok"]},
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error_code": result.get("error_code"),
        "message": result["message"],
    }
    if result["ok"]:
        _LOGGER.info("[MQTT] Connection test succeeded")
    else:
        _LOGGER.warning("[MQTT] Connection test failed: %s", result["message"])

    return web.json_response(payload)


def create_app(local_secret: str) -> web.Application:
    """Create the aiohttp application with routes and auth context."""
    app = web.Application()
    app["local_secret"] = local_secret
    app["start_time"] = time.monotonic()
    app.router.add_get("/system/status", _handle_system_status)
    app.router.add_post("/action/mqtt_test", _handle_mqtt_test)
    return app


async def start_server(
    app: web.Application,
    host: str = "127.0.0.1",
    port: int = 55080,
) -> web.AppRunner:
    """Start the HTTP server. Returns the runner for later cleanup."""
    app["start_time"] = time.monotonic()

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    _LOGGER.info("[API] HTTP server started on %s:%d", host, port)
    return runner


async def stop_server(runner: web.AppRunner) -> None:
    """Stop the HTTP server and clean up."""
    if runner is not None:
        await runner.cleanup()
        _LOGGER.info("[API] HTTP server stopped")
