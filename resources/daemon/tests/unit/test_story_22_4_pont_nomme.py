"""Story 22.4 — le pont jeedom2ha apparaît sous son nom dans Home Assistant.

Le démon publie l'appareil ``jeedom2ha_bridge`` (cible du ``via_device`` de chaque appareil)
avec une entité ``binary_sensor`` de connectivité « État du pont ».

Identifiants numériques factices et libellés génériques uniquement (CC-48).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from discovery.publisher import DiscoveryPublisher
from export import decision_export as dx
from models.availability import AVAILABILITY_OFFLINE, AVAILABILITY_ONLINE, BRIDGE_AVAILABILITY_TOPIC
from transport import http_server
from transport.http_server import create_app

SECRET = "test-secret-22-4-sentinelle"
HEADERS = {"X-Local-Secret": SECRET}
PIECE = 10
BRIDGE_TOPIC = "homeassistant/binary_sensor/jeedom2ha_bridge/config"
BROKER_HOST = "broker.example.invalid"
BROKER_PORT = 18830


# --- Charge de découverte (AC1) ------------------------------------------------

def test_bridge_payload_fields():
    payload = DiscoveryPublisher.build_bridge_payload("1.2.0")
    assert payload["unique_id"] == "jeedom2ha_bridge_status"
    assert payload["name"] == "État du pont"
    assert payload["device_class"] == "connectivity"
    assert payload["state_topic"] == BRIDGE_AVAILABILITY_TOPIC == "jeedom2ha/bridge/status"
    # Valeurs réellement publiées par le démon sur ce topic (birth / LWT / stop).
    assert payload["payload_on"] == AVAILABILITY_ONLINE == "online"
    assert payload["payload_off"] == AVAILABILITY_OFFLINE == "offline"
    assert payload["device"] == {
        "identifiers": ["jeedom2ha_bridge"],
        "name": "Jeedom (jeedom2ha)",
        "manufacturer": "jeedom2ha",
        "model": "Pont Jeedom → Home Assistant",
        "sw_version": "1.2.0",
    }
    assert payload["origin"]["name"] == "jeedom2ha"
    assert payload["default_entity_id"] == "binary_sensor.jeedom2ha_bridge_status"


def test_bridge_payload_has_no_availability_and_no_self_via_device():
    payload = DiscoveryPublisher.build_bridge_payload("1.2.0")
    for key in ("availability_topic", "availability", "availability_mode",
                "payload_available", "payload_not_available"):
        assert key not in payload
    assert "via_device" not in payload["device"]


@pytest.mark.parametrize("version", [None, "", "inconnu"])
def test_bridge_payload_omits_unknown_sw_version(version):
    assert "sw_version" not in DiscoveryPublisher.build_bridge_payload(version)["device"]


async def test_publish_bridge_is_retained_on_its_own_topic():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message = MagicMock(return_value=True)
    publisher = DiscoveryPublisher(mqtt_bridge)
    assert publisher.bridge_topic() == BRIDGE_TOPIC
    assert await publisher.publish_bridge("1.2.0") is True
    mqtt_bridge.publish_message.assert_called_once()
    args, kwargs = mqtt_bridge.publish_message.call_args
    assert args[0] == BRIDGE_TOPIC
    assert json.loads(args[1]) == DiscoveryPublisher.build_bridge_payload("1.2.0")
    assert kwargs == {"qos": 1, "retain": True}


async def test_publish_bridge_reports_failure():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message = MagicMock(return_value=False)
    assert await DiscoveryPublisher(mqtt_bridge).publish_bridge("1.2.0") is False


def test_equipment_unpublish_paths_never_target_bridge_topic():
    """« Supprimer de HA » passe par l'id d'équipement : le topic du pont est hors d'atteinte."""
    publisher = DiscoveryPublisher(MagicMock())
    for entity_type in ("light", "switch", "cover", "sensor", "binary_sensor", "button"):
        for eq_id in (0, 1, 501, 99999):
            assert publisher._build_topic(eq_id, entity_type=entity_type) != BRIDGE_TOPIC


async def test_unpublish_by_unique_id_refuses_bridge_unique_id():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message = MagicMock(return_value=True)
    assert await DiscoveryPublisher(mqtt_bridge).unpublish("jeedom2ha_bridge_status") is False
    mqtt_bridge.publish_message.assert_not_called()


# --- Démon : connexion MQTT, birth HA, exclusions (AC1, AC2, AC3) -------------------

def _cmd(cmd_id, generic_type, type_="action", sub_type="other"):
    return {"id": cmd_id, "name": f"cmd {cmd_id}", "generic_type": generic_type, "type": type_,
            "sub_type": sub_type}


def _eq_raw(eq_id):
    return {
        "id": eq_id, "name": f"EQ {eq_id}", "object_id": PIECE, "is_enable": True, "is_visible": True,
        "eq_type": "virtual", "is_excluded": False, "status": {"timeout": 0},
        "cmds": [_cmd(eq_id * 10 + 1, "LIGHT_ON"), _cmd(eq_id * 10 + 2, "LIGHT_OFF"),
                 _cmd(eq_id * 10 + 3, "LIGHT_STATE", "info", "binary")],
    }


def _sync_body():
    payload = {
        "timestamp": "2026-11-01T00:00:00Z",
        "objects": [{"id": PIECE, "name": "Zone générique"}],
        "eq_logics": [_eq_raw(501), _eq_raw(502)],
        "scenarios": [],
        "scenarios_complete": True,
        "sync_config": {"confidence_policy": "sure_probable"},
    }
    return {"action": "sync", "payload": payload, "request_id": "t22-4", "timestamp": "2026-11-01T00:00:00Z"}


def _bridge_mock():
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    bridge.start = AsyncMock()
    bridge.stop = AsyncMock()
    bridge.state = "connected"
    bridge.broker_info = f"{BROKER_HOST}:{BROKER_PORT}"
    return bridge


@pytest.fixture(autouse=True)
def _no_republish_delay():
    """Lissage de la republication (10 s / N) neutralisé, comme dans les autres tests du démon."""
    with patch("transport.http_server.asyncio.sleep", new=AsyncMock()):
        yield


@pytest.fixture
def app(tmp_path):
    application = create_app(local_secret=SECRET)
    application["data_dir"] = str(tmp_path)
    application["mqtt_bridge"] = _bridge_mock()
    application["plugin_version"] = "9.9.9"
    return application


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _published_topics(bridge):
    return [c.args[0] for c in bridge.publish_message.call_args_list]


def _bridge_calls(bridge):
    return [c for c in bridge.publish_message.call_args_list if c.args[0] == BRIDGE_TOPIC]


async def _connect(cli, app):
    resp = await cli.post("/action/mqtt_connect", json={"payload": {"host": BROKER_HOST, "port": BROKER_PORT}},
                          headers=HEADERS)
    assert resp.status == 200
    kwargs = app["mqtt_bridge"].start.call_args.kwargs
    return kwargs["on_reconnect_cb"], kwargs["on_ha_birth_cb"]


async def test_first_connection_publishes_bridge_before_any_sync(cli, app):
    on_reconnect, _ = await _connect(cli, app)
    await on_reconnect()
    bridge = app["mqtt_bridge"]
    assert _published_topics(bridge) == [BRIDGE_TOPIC]
    payload = json.loads(_bridge_calls(bridge)[0].args[1])
    assert payload == DiscoveryPublisher.build_bridge_payload("9.9.9")
    assert _bridge_calls(bridge)[0].kwargs == {"qos": 1, "retain": True}
    # CC-48 : aucune valeur de broker dans la charge.
    raw = _bridge_calls(bridge)[0].args[1]
    assert BROKER_HOST not in raw and str(BROKER_PORT) not in raw
    assert app.get("publications", {}) == {}


async def test_reconnect_and_ha_birth_republish_bridge_first(cli, app):
    resp = await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)
    assert resp.status == 200
    on_reconnect, on_ha_birth = await _connect(cli, app)
    bridge = app["mqtt_bridge"]
    for callback in (on_reconnect, on_ha_birth):
        bridge.publish_message.reset_mock()
        await callback()
        topics = _published_topics(bridge)
        assert topics[0] == BRIDGE_TOPIC
        assert topics.count(BRIDGE_TOPIC) == 1
        assert len(topics) > 1  # les équipements suivent, inchangés


async def test_bridge_not_published_when_broker_disconnected(cli, app):
    # `cli` d'abord : sous Python 3.9, la fixture `app` seule est créée hors boucle (RuntimeError en CI).
    del cli
    app["mqtt_bridge"].is_connected = False
    assert await http_server._publish_bridge_discovery(app) is False
    app["mqtt_bridge"].publish_message.assert_not_called()


async def test_bridge_publish_error_does_not_block_equipment_republication(cli, app):
    await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)
    on_reconnect, _ = await _connect(cli, app)
    bridge = app["mqtt_bridge"]

    def _publish(topic, payload, qos=1, retain=False):
        if topic == BRIDGE_TOPIC:
            raise RuntimeError("boom")
        return True

    bridge.publish_message = MagicMock(side_effect=_publish)
    await on_reconnect()
    assert any(t != BRIDGE_TOPIC for t in _published_topics(bridge))


async def test_via_device_and_ids_of_equipments_unchanged(cli, app):
    """AC2 : chaque appareil publié pointe toujours sur ``jeedom2ha_bridge``, ids inchangés."""
    resp = await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)
    assert resp.status == 200
    bridge_id = DiscoveryPublisher.build_bridge_payload("9.9.9")["device"]["identifiers"][0]
    configs = [
        json.loads(c.args[1]) for c in app["mqtt_bridge"].publish_message.call_args_list
        if c.args[0].endswith("/config") and c.args[1]
    ]
    assert configs, "la sync doit publier au moins une découverte d'équipement"
    by_unique_id = {p["unique_id"]: p for p in configs}
    assert set(by_unique_id) >= {"jeedom2ha_eq_501", "jeedom2ha_eq_502"}
    for unique_id, payload in by_unique_id.items():
        assert payload["device"]["via_device"] == bridge_id == "jeedom2ha_bridge"
        eq_id = unique_id.rsplit("_", 1)[-1]
        assert payload["device"]["identifiers"] == [f"jeedom2ha_{eq_id}"]
    # La sync elle-même ne publie pas le pont (publié à la connexion MQTT).
    assert not _bridge_calls(app["mqtt_bridge"])


async def test_bridge_stays_out_of_counters_export_and_states(cli, app, tmp_path):
    """AC3 : le pont n'est pas un équipement."""
    first = await (await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)).json()
    on_reconnect, on_ha_birth = await _connect(cli, app)
    await on_reconnect()
    await on_ha_birth()
    assert _bridge_calls(app["mqtt_bridge"])

    second = await (await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)).json()
    first_payload, second_payload = first.get("payload", first), second.get("payload", second)
    counter_keys = ("total_eq_logics", "total_cmds", "eligible_count", "ineligible_count",
                    "ineligible_breakdown", "mapping_summary", "published_scope")
    for key in counter_keys:
        assert key in first_payload, key
        assert second_payload[key] == first_payload[key], key
    assert first_payload["total_eq_logics"] == 2
    assert "jeedom2ha_bridge" not in json.dumps(second_payload)

    assert set(app["publications"]) == {501, 502}

    export_raw = (tmp_path / dx.EXPORT_FILENAME).read_text(encoding="utf-8")
    assert "jeedom2ha_bridge" not in export_raw
    assert {r["eq_id"] for r in json.loads(export_raw)["equipments"]} == {501, 502}

    for route in ("/system/equipment_states", "/system/published_scope", "/system/diagnostics"):
        resp = await cli.get(route, headers=HEADERS)
        assert resp.status == 200, route
        body = await resp.text()
        assert "jeedom2ha_bridge" not in body, route
        assert "État du pont" not in body, route


@pytest.mark.parametrize("portee,selection", [("equipement", [501]), ("piece", [PIECE])])
async def test_supprimer_equipment_or_piece_keeps_bridge(cli, app, portee, selection):
    await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)
    on_reconnect, _ = await _connect(cli, app)
    await on_reconnect()
    bridge = app["mqtt_bridge"]
    bridge.publish_message.reset_mock()
    resp = await cli.post("/action/execute",
                          json={"intention": "supprimer", "portee": portee, "selection": selection},
                          headers=HEADERS)
    assert resp.status == 200
    topics = _published_topics(bridge)
    assert any(t.endswith("/config") for t in topics), "la suppression doit vider au moins un topic"
    assert BRIDGE_TOPIC not in topics
