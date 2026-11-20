"""story/system-health — appareil « Santé de Jeedom » (lecture seule, désactivé par défaut).

Couvre : mapper pur (démons, compteurs, version, identifiants invalides, doublons, valeurs illisibles), charge de
découverte (diagnostic, aucune commande, appareil et disponibilité du pont), espaces de noms sans collision possible
avec les équipements, scénarios, select, capteurs « État » et le pont, route ``/action/system_health`` (secret,
validation, publication, mise à jour d'état, retrait d'un plugin disparu, purge à la désactivation, broker
indisponible), aucune commande exécutable, et hors du circuit des équipements. Plugins et noms fictifs (CC-48).
"""

from __future__ import annotations

import json
import re
from unittest.mock import AsyncMock

import pytest

from discovery import publisher as discovery_publisher
from discovery.system_health import SystemHealthPublisher
from mapping.system_health import (
    SYSTEM_DEVICE_ID,
    SystemHealthEntity,
    build_system_health_payload,
    daemon_key,
    map_system_health,
    system_config_topic_pattern,
)
from models.availability import BRIDGE_AVAILABILITY_TOPIC
from sync.command import CommandSynchronizer
from transport.http_server import create_app
from transport.mqtt_client import COMMAND_SUBSCRIPTION_TOPICS

SECRET = "test-secret-system-health"
H = {"X-Local-Secret": SECRET}

SNAPSHOT = {
    "daemons": [
        {"id": "plugin_zeta", "name": "Zêta", "running": True},
        {"id": "plugin_alpha", "name": "Alpha", "running": False},
    ],
    "updates": 3,
    "messages": 2,
    "core_version": "4.5.1",
}


class _Broker:
    """Faux broker : retient les messages retenus, relit les configurations comme ``collect_retained_topics``."""

    def __init__(self, connected=True, collect=True):
        self.is_connected = connected
        self.calls = []
        self.retained = {}
        if not collect:
            self.collect_retained_topics = None

    def publish_message(self, topic, payload, qos=1, retain=False):
        self.calls.append((topic, payload, retain))
        if retain:
            if payload == "":
                self.retained.pop(topic, None)
            else:
                self.retained[topic] = payload
        return True

    async def collect_retained_topics(self, topic_filter, window_s=1.5):
        self.collects = getattr(self, "collects", []) + [topic_filter]
        regex = "^" + re.escape(topic_filter).replace(r"\+", "[^/]+").replace(r"\#", ".*") + "$"
        return [t for t in self.retained if re.match(regex, t)]


# --- Mapper pur -----------------------------------------------------------------------------------

def test_mapper_one_running_binary_sensor_per_daemon_then_three_sensors():
    entities = map_system_health(SNAPSHOT)
    assert [(e.component, e.key, e.name, e.state) for e in entities] == [
        ("binary_sensor", "daemon_plugin_alpha", "Alpha", "OFF"),
        ("binary_sensor", "daemon_plugin_zeta", "Zêta", "ON"),
        ("sensor", "daemons_running", "Démons en service", "1"),
        ("sensor", "daemons_stopped", "Démons arrêtés", "1"),
        ("sensor", "updates", "Mises à jour disponibles", "3"),
        ("sensor", "messages", "Messages", "2"),
        ("sensor", "core_version", "Version du cœur", "4.5.1"),
    ]
    assert all(e.device_class == "running" for e in entities if e.component == "binary_sensor")
    assert all(e.device_class is None for e in entities if e.component == "sensor")
    assert [e.key for e in entities if e.state_class == "measurement"] == ["daemons_running", "daemons_stopped"]


def test_mapper_identities():
    by_key = {e.key: e for e in map_system_health(SNAPSHOT)}
    assert by_key["daemon_plugin_alpha"].unique_id == "jeedom2ha_system_daemon_plugin_alpha"
    assert by_key["updates"].unique_id == "jeedom2ha_system_updates"
    assert by_key["messages"].unique_id == "jeedom2ha_system_messages"
    assert by_key["core_version"].unique_id == "jeedom2ha_system_core_version"
    assert by_key["updates"].state_topic == "jeedom2ha/system/updates/state"
    assert by_key["daemon_plugin_alpha"].config_topic() == (
        "homeassistant/binary_sensor/jeedom2ha_system_daemon_plugin_alpha/config")


def test_mapper_without_daemons_still_declares_the_five_sensors_with_zero_and_zero():
    entities = map_system_health({"daemons": [], "updates": 0, "messages": 0, "core_version": "4.4.0"})
    assert [e.key for e in entities] == ["daemons_running", "daemons_stopped", "updates", "messages", "core_version"]
    assert [e.state for e in entities] == ["0", "0", "0", "0", "4.4.0"]


@pytest.mark.parametrize("snapshot", [{}, None, [], {"updates": "texte", "messages": -1, "core_version": {"x": 1}},
                                      {"updates": True, "messages": None, "core_version": ""}])
def test_unreadable_values_publish_no_state(snapshot):
    entities = map_system_health(snapshot)
    assert [(e.key, e.state) for e in entities] == [("daemons_running", "0"), ("daemons_stopped", "0"),
                                                    ("updates", None), ("messages", None), ("core_version", None)]


@pytest.mark.parametrize("plugin_id,key", [
    ("zwavejs", "daemon_zwavejs"), ("RFPlayer2", "daemon_rfplayer2"), ("mqtt-2", "daemon_mqtt_2"),
    ("", None), ("a/b", None), ("x+y", None), ("../etc", None), (None, None), ("é", None), ("a" * 65, None),
])
def test_daemon_key_is_mqtt_and_identifier_safe(plugin_id, key):
    assert daemon_key(plugin_id) == key


def test_invalid_or_duplicate_daemons_are_ignored():
    entities = map_system_health({"daemons": [
        {"id": "plugin_a", "name": "Premier", "running": True},
        {"id": "PLUGIN_A", "name": "Doublon", "running": False},
        {"id": "a/b", "name": "Topic", "running": True},
        "pas un objet",
        {"id": "plugin_b", "name": "", "running": "ok"},
    ]})
    daemons = [e for e in entities if e.component == "binary_sensor"]
    assert [(e.key, e.name, e.state) for e in daemons] == [
        ("daemon_plugin_a", "Premier", "ON"), ("daemon_plugin_b", "plugin_b", "OFF")]  # running doit être vrai


# --- Agrégats « démons en service X/Y » ----------------------------------------------------------

def _aggregates(entities):
    by_key = {e.key: e.state for e in entities}
    daemons = [e.state for e in entities if e.component == "binary_sensor"]
    return int(by_key["daemons_running"]), int(by_key["daemons_stopped"]), daemons


def test_aggregates_match_the_binary_sensors_five_ok_and_one_nok():
    rows = [{"id": f"plugin_{i}", "name": f"P{i}", "running": True} for i in range(5)]
    rows.append({"id": "plugin_arret", "name": "Arrêté", "running": False})
    running, stopped, daemons = _aggregates(map_system_health({"daemons": rows}))
    assert (running, stopped) == (5, 1)
    assert running == daemons.count("ON") and stopped == daemons.count("OFF")
    assert running + stopped == len(daemons)  # Y = exactement le périmètre des binary_sensor


@pytest.mark.parametrize("running_value", [False, None, "ok", 1, "true"])
def test_a_daemon_whose_state_is_unreadable_counts_as_stopped(running_value):
    """Côté plugin, une exception dans deamon_info() donne running faux (tests PHP) ; côté démon, toute valeur qui
    n'est pas exactement vrai est « OFF » et compte comme arrêté."""
    entities = map_system_health({"daemons": [{"id": "plugin_ok", "name": "OK", "running": True},
                                              {"id": "plugin_err", "name": "Err", "running": running_value}]})
    running, stopped, daemons = _aggregates(entities)
    assert (running, stopped) == (1, 1) and daemons == ["OFF", "ON"]


def test_duplicate_or_invalid_daemons_are_outside_the_aggregates_too():
    entities = map_system_health({"daemons": [{"id": "plugin_a", "running": True}, {"id": "PLUGIN_A", "running": False},
                                              {"id": "a/b", "running": False}]})
    assert _aggregates(entities) == (1, 0, ["ON"])


@pytest.mark.asyncio
async def test_a_daemon_state_change_updates_the_three_values():
    broker = _Broker()
    publisher = SystemHealthPublisher(broker)
    await publisher.apply(SNAPSHOT)  # alpha arrêté, zêta en service : 1 / 1
    broker.calls.clear()
    started = dict(SNAPSHOT, daemons=[dict(d, running=True) for d in SNAPSHOT["daemons"]])
    await publisher.apply(started)
    states = {t: p for t, p, _r in broker.calls if t.endswith("/state")}
    assert states["jeedom2ha/system/daemon_plugin_alpha/state"] == "ON"
    assert states["jeedom2ha/system/daemons_running/state"] == "2"
    assert states["jeedom2ha/system/daemons_stopped/state"] == "0"


# --- Charge de découverte -----------------------------------------------------------------------

def test_discovery_payload_is_read_only_diagnostic_on_one_device():
    for entity in map_system_health(SNAPSHOT):
        payload = build_system_health_payload(entity)
        assert payload["entity_category"] == "diagnostic"
        assert not any(k.startswith("command") for k in payload), entity.key  # aucune commande
        assert payload["unique_id"] == payload["object_id"] == entity.unique_id
        assert payload["default_entity_id"] == f"{entity.component}.{entity.unique_id}"
        assert payload["state_topic"] == entity.state_topic
        assert payload["availability_topic"] == BRIDGE_AVAILABILITY_TOPIC  # indisponible quand le pont l'est
        assert payload["device"] == {
            "identifiers": ["jeedom2ha_system"], "name": "Santé de Jeedom", "manufacturer": "jeedom2ha",
            "model": "Santé de Jeedom", "via_device": discovery_publisher.BRIDGE_DEVICE_ID,
        }
        assert payload["origin"]["sw_version"] == discovery_publisher._SW_VERSION
    daemon = build_system_health_payload(SystemHealthEntity("binary_sensor", "daemon_x", "X", "ON", "running"))
    assert (daemon["device_class"], daemon["payload_on"], daemon["payload_off"]) == ("running", "ON", "OFF")
    sensor = build_system_health_payload(SystemHealthEntity("sensor", "updates", "Mises à jour", "1"))
    assert "device_class" not in sensor and "unit_of_measurement" not in sensor and "state_class" not in sensor
    for entity in map_system_health(SNAPSHOT):
        if entity.key in ("daemons_running", "daemons_stopped"):
            aggregate = build_system_health_payload(entity)
            assert aggregate["state_class"] == "measurement" and aggregate["entity_category"] == "diagnostic"
            assert "unit_of_measurement" not in aggregate and "device_class" not in aggregate


# --- Espaces de noms : aucune collision possible ------------------------------------------------

EXISTING_IDENTITIES = [
    # équipement principal, secondaire par commande, select, capteur « État » d'une barrière
    ("jeedom2ha_eq_199", "jeedom2ha_199", "jeedom2ha/199/state"),
    ("jeedom2ha_eq_199_cmd_1626", "jeedom2ha_199_1626", "jeedom2ha/199/1626/state"),
    ("jeedom2ha_eq_554_select_5489", "jeedom2ha_554_select_5489", "jeedom2ha/554/select_5489/state"),
    ("jeedom2ha_eq_199_cmd_1626_barrier_state", "jeedom2ha_199_1626_barrier_state", "jeedom2ha/199/1626/barrier_state"),
    # scénario, pont
    ("jeedom2ha_scenario_20", "jeedom2ha_scenario_20", "jeedom2ha/scenario_20/availability"),
    ("jeedom2ha_bridge_status", "jeedom2ha_bridge", BRIDGE_AVAILABILITY_TOPIC),
]


def test_no_collision_with_existing_namespaces():
    system = system_config_topic_pattern()
    for unique_id, node_id, state_topic in EXISTING_IDENTITIES:
        assert not unique_id.startswith("jeedom2ha_system_") and not node_id.startswith("jeedom2ha_system")
        assert not state_topic.startswith("jeedom2ha/system/")
        for component in ("binary_sensor", "sensor", "button", "select", "switch", "cover"):
            assert not system.fullmatch(f"homeassistant/{component}/{node_id}/config")
    # Les équipements n'ont que des identifiants numériques derrière le préfixe : « system » n'en est jamais un.
    for entity in map_system_health(SNAPSHOT):
        assert not re.fullmatch(r"jeedom2ha_eq_[0-9]+.*", entity.unique_id)
        assert not re.fullmatch(r"jeedom2ha_scenario_[0-9]+", entity.unique_id)
        assert entity.state_topic.split("/")[1] == "system"
        assert system.fullmatch(entity.config_topic())


def _matches(topic_filter, topic):
    regex = "^" + re.escape(topic_filter).replace(r"\+", "[^/]+").replace(r"\#", ".*") + "$"
    return re.match(regex, topic) is not None


def test_system_state_topics_are_never_command_subscriptions():
    for entity in map_system_health(SNAPSHOT):
        assert not any(_matches(f, entity.state_topic) for f in COMMAND_SUBSCRIPTION_TOPICS), entity.key


def test_scenario_purge_never_touches_system_topics():
    scenario = re.compile(r"homeassistant/button/(jeedom2ha_scenario_([0-9]+))/config")
    assert not any(scenario.fullmatch(e.config_topic()) for e in map_system_health(SNAPSHOT))


@pytest.mark.asyncio
@pytest.mark.parametrize("topic", ["jeedom2ha/system/updates/set", "jeedom2ha/system/set",
                                   "jeedom2ha/system/daemon_plugin_alpha/set", "jeedom2ha/system/cmd"])
async def test_no_command_is_executable_on_system_topics(topic):
    sync = CommandSynchronizer(app={"publications": {}, "state_synchronizer": None}, mqtt_bridge=_Broker(),
                               jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php", jeedom_core_apikey="k")
    sync._execute_exec_cmd = AsyncMock(return_value=True)
    sync._handle_scenario_command = AsyncMock(return_value=True)
    for payload in ("ON", "OFF", "1", "PRESS"):
        assert await sync.handle_command_message(topic, payload) is False
    sync._execute_exec_cmd.assert_not_awaited()
    sync._handle_scenario_command.assert_not_awaited()


# --- Publication, mise à jour, retrait, purge ---------------------------------------------------

@pytest.mark.asyncio
async def test_publisher_publishes_configs_then_retained_states():
    broker = _Broker()
    result = await SystemHealthPublisher(broker).apply(SNAPSHOT)
    assert result == {"entities": 7, "removed": [], "failed": 0}
    configs = [t for t, p, r in broker.calls if t.endswith("/config")]
    assert configs == [
        "homeassistant/binary_sensor/jeedom2ha_system_daemon_plugin_alpha/config",
        "homeassistant/binary_sensor/jeedom2ha_system_daemon_plugin_zeta/config",
        "homeassistant/sensor/jeedom2ha_system_daemons_running/config",
        "homeassistant/sensor/jeedom2ha_system_daemons_stopped/config",
        "homeassistant/sensor/jeedom2ha_system_updates/config",
        "homeassistant/sensor/jeedom2ha_system_messages/config",
        "homeassistant/sensor/jeedom2ha_system_core_version/config",
    ]
    states = {t: p for t, p, r in broker.calls if not t.endswith("/config")}
    assert states == {
        "jeedom2ha/system/daemon_plugin_alpha/state": "OFF",
        "jeedom2ha/system/daemon_plugin_zeta/state": "ON",
        "jeedom2ha/system/daemons_running/state": "1",
        "jeedom2ha/system/daemons_stopped/state": "1",
        "jeedom2ha/system/updates/state": "3",
        "jeedom2ha/system/messages/state": "2",
        "jeedom2ha/system/core_version/state": "4.5.1",
    }
    assert all(r is True for _t, _p, r in broker.calls)  # tout est retenu


@pytest.mark.asyncio
async def test_state_update_and_disappeared_plugin_is_removed():
    broker = _Broker()
    publisher = SystemHealthPublisher(broker)
    await publisher.apply(SNAPSHOT)
    broker.calls.clear()
    changed = dict(SNAPSHOT, daemons=[{"id": "plugin_zeta", "name": "Zêta", "running": False}], messages=0)
    result = await publisher.apply(changed)
    assert result["removed"] == ["daemon_plugin_alpha"]
    assert ("jeedom2ha/system/daemon_plugin_zeta/state", "OFF", True) in broker.calls
    assert ("jeedom2ha/system/messages/state", "0", True) in broker.calls
    assert ("homeassistant/binary_sensor/jeedom2ha_system_daemon_plugin_alpha/config", "", True) in broker.calls
    assert ("jeedom2ha/system/daemon_plugin_alpha/state", "", True) in broker.calls
    assert "homeassistant/binary_sensor/jeedom2ha_system_daemon_plugin_alpha/config" not in broker.retained


@pytest.mark.asyncio
async def test_unreadable_value_keeps_the_entity_without_inventing_a_state():
    broker = _Broker()
    await SystemHealthPublisher(broker).apply(dict(SNAPSHOT, updates=None))
    assert "homeassistant/sensor/jeedom2ha_system_updates/config" in broker.retained
    assert not any(t == "jeedom2ha/system/updates/state" for t, _p, _r in broker.calls)


@pytest.mark.asyncio
async def test_purge_empties_everything_even_after_a_daemon_restart():
    broker = _Broker()
    await SystemHealthPublisher(broker).apply(SNAPSHOT)
    # Autre entité retenue, d'une autre famille : jamais touchée.
    broker.publish_message("homeassistant/sensor/jeedom2ha_199_1626/config", "{}", retain=True)
    broker.publish_message("homeassistant/button/jeedom2ha_scenario_20/config", "{}", retain=True)
    broker.calls.clear()
    fresh = SystemHealthPublisher(broker)  # démon redémarré : rien en mémoire, le broker fait foi
    result = await fresh.purge()
    assert result["purge_complete"] is True
    assert result["removed"] == ["core_version", "daemon_plugin_alpha", "daemon_plugin_zeta", "daemons_running",
                                 "daemons_stopped", "messages", "updates"]
    assert sorted(broker.retained) == ["homeassistant/button/jeedom2ha_scenario_20/config",
                                       "homeassistant/sensor/jeedom2ha_199_1626/config"]
    assert all(p == "" for _t, p, _r in broker.calls)
    assert {t for t, _p, _r in broker.calls if not t.endswith("/config")} == {
        f"jeedom2ha/system/{k}/state" for k in result["removed"]}


class _FailingEmptyBroker(_Broker):
    """Broker qui refuse les vidages (charge vide) : un retrait ne peut pas aboutir."""

    def publish_message(self, topic, payload, qos=1, retain=False):
        if payload == "":
            self.calls.append((topic, payload, retain))
            return False
        return super().publish_message(topic, payload, qos, retain)


@pytest.mark.asyncio
async def test_unreadable_broker_makes_the_publication_incomplete_so_it_is_retried():
    """Revue P2 : broker illisible = retrait des plugins disparus non vérifié -> échec compté (le cron renverra)."""
    broker = _Broker(collect=False)
    result = await SystemHealthPublisher(broker).apply(SNAPSHOT)
    assert result["failed"] == 1 and result["removed"] == []


@pytest.mark.asyncio
async def test_a_failed_removal_makes_the_publication_incomplete():
    """Revue P2 : un plugin disparu dont la configuration ne peut pas être vidée -> échec compté, jamais « ok »."""
    broker = _FailingEmptyBroker()
    publisher = SystemHealthPublisher(broker)
    assert (await publisher.apply(SNAPSHOT))["failed"] == 0
    without_alpha = dict(SNAPSHOT, daemons=[d for d in SNAPSHOT["daemons"] if d["id"] != "plugin_alpha"])
    result = await publisher.apply(without_alpha)
    assert result["failed"] == 1 and result["removed"] == []
    assert ("binary_sensor", "daemon_plugin_alpha") in publisher.published  # encore à retirer au prochain envoi


@pytest.mark.asyncio
async def test_route_reports_an_incomplete_removal_as_not_ok(aiohttp_client):
    broker = _FailingEmptyBroker()
    _app, cli = await _client(aiohttp_client, broker)
    assert (await (await cli.post("/action/system_health", json={"enabled": True, "snapshot": SNAPSHOT},
                                  headers=H)).json())["status"] == "ok"
    without_alpha = dict(SNAPSHOT, daemons=[d for d in SNAPSHOT["daemons"] if d["id"] != "plugin_alpha"])
    body = await (await cli.post("/action/system_health", json={"enabled": True, "snapshot": without_alpha},
                                 headers=H)).json()
    assert body["status"] == "error" and body["failed"] == 1  # le cron ne mémorise pas l'empreinte


@pytest.mark.asyncio
async def test_purge_is_incomplete_when_the_broker_cannot_be_read():
    broker = _Broker(collect=False)
    publisher = SystemHealthPublisher(broker)
    await publisher.apply(SNAPSHOT)
    result = await publisher.purge()
    assert result["purge_complete"] is False  # le cron réessaiera
    assert len(result["removed"]) == 7  # ce qui était connu est quand même vidé


# --- Route /action/system_health ----------------------------------------------------------------

async def _client(aiohttp_client, broker):
    app = create_app(local_secret=SECRET)
    app["mqtt_bridge"] = broker
    return app, await aiohttp_client(app)


@pytest.mark.asyncio
async def test_route_requires_the_secret_and_a_valid_body(aiohttp_client):
    _app, cli = await _client(aiohttp_client, _Broker())
    assert (await cli.post("/action/system_health", json={"enabled": False})).status == 401
    for body in ({}, {"enabled": "1"}, {"enabled": True}, {"enabled": True, "snapshot": []}, []):
        assert (await cli.post("/action/system_health", json=body, headers=H)).status == 400, body
    assert (await cli.post("/action/system_health", data="pas du json", headers=H)).status == 400


@pytest.mark.asyncio
async def test_route_publishes_and_purges_outside_the_equipment_circuit(aiohttp_client):
    broker = _Broker()
    app, cli = await _client(aiohttp_client, broker)
    resp = await cli.post("/action/system_health", json={"enabled": True, "snapshot": SNAPSHOT}, headers=H)
    assert resp.status == 200
    assert (await resp.json()) == {"status": "ok", "entities": 7, "removed": [], "failed": 0}
    assert len([t for t in broker.retained if t.startswith("homeassistant/")]) == 7
    # Hors du circuit des équipements : ni publications, ni mappings, ni topologie.
    assert app["publications"] == {} and app["mappings"] == {} and app["topology"] is None
    resp = await cli.post("/action/system_health", json={"enabled": False}, headers=H)
    assert resp.status == 200
    body = await resp.json()
    assert body["status"] == "ok" and body["purge_complete"] is True and len(body["removed"]) == 7
    assert broker.retained == {}


@pytest.mark.asyncio
async def test_route_refuses_when_the_broker_is_unavailable(aiohttp_client):
    _app, cli = await _client(aiohttp_client, _Broker(connected=False))
    resp = await cli.post("/action/system_health", json={"enabled": True, "snapshot": SNAPSHOT}, headers=H)
    assert resp.status == 503


def test_system_device_identity():
    assert SYSTEM_DEVICE_ID == "jeedom2ha_system"
    assert not re.fullmatch(r"jeedom2ha_[0-9]+", SYSTEM_DEVICE_ID)  # appareils d'équipements : jeedom2ha_<id>


# --- Case décochée (le défaut) : trace MQTT strictement identique à main -----------------------

class _RawBridge:
    def __init__(self) -> None:
        self.is_connected = True
        self.state = "connected"
        self.broker_info = "broker.example.test:1883"
        self.calls = []

    def publish_message(self, topic, payload, qos=1, retain=False):
        self.calls.append({"topic": topic, "payload": payload, "qos": qos, "retain": retain})
        return True


@pytest.mark.asyncio
async def test_disabled_by_default_the_mqtt_trace_is_strictly_identical_to_main(aiohttp_client):
    """Ligne de base capturée sur main (0b826bb), même scène que la story des capteurs « État » (corpus doré, modes,
    formes réelles, portails). Case décochée, le cron n'appelle jamais la route : la synchro publie exactement les
    mêmes messages, dans le même ordre, et les mêmes entités ; aucun topic de l'appareil « Santé de Jeedom »."""
    from pathlib import Path

    from .barrier_state_corpus import entity_commands, load_scene, sync_body

    baseline = Path(__file__).resolve().parent.parent / "fixtures" / "system_health" / "projection_baseline.json"
    base = json.loads(baseline.read_text(encoding="utf-8"))
    app = create_app(local_secret=SECRET)
    bridge = _RawBridge()
    app["mqtt_bridge"] = bridge
    cli = await aiohttp_client(app)
    resp = await cli.post("/action/sync", json=sync_body(load_scene(), "system-health"), headers=H)
    assert resp.status == 200, await resp.text()
    assert len(base["mqtt"]) > 150 and len(base["entities"]) > 100, "scène trop pauvre pour être une preuve"
    assert bridge.calls == base["mqtt"]
    assert entity_commands(app["mappings"]) == base["entities"]
    assert not any("jeedom2ha_system" in c["topic"] or c["topic"].startswith("jeedom2ha/system/") for c in bridge.calls)
    assert app["system_health_published"] == set()


# --- Revue P2 : republication après redémarrage du broker / retour de HA ------------------------

async def _connected(aiohttp_client, broker):
    broker.start = AsyncMock()
    broker.stop = AsyncMock()
    broker.state = "connected"
    broker.broker_info = "broker.example.invalid:18830"
    app, cli = await _client(aiohttp_client, broker)
    resp = await cli.post("/action/mqtt_connect", json={"payload": {"host": "broker.example.invalid", "port": 18830}},
                          headers=H)
    assert resp.status == 200
    kwargs = broker.start.call_args.kwargs
    return app, cli, kwargs["on_reconnect_cb"], kwargs["on_ha_birth_cb"]


@pytest.mark.asyncio
@pytest.mark.parametrize("which", ["broker_reconnect", "ha_birth"])
async def test_device_is_republished_after_a_broker_restart_without_retained_messages(aiohttp_client, which):
    broker = _Broker()
    app, cli, reconnect_cb, birth_cb = await _connected(aiohttp_client, broker)
    assert (await cli.post("/action/system_health", json={"enabled": True, "snapshot": SNAPSHOT}, headers=H)).status == 200
    expected = {t: p for t, p in broker.retained.items() if "system" in t}
    assert len([t for t in expected if t.endswith("/config")]) == 7
    # Mosquitto redémarre SANS persistance : plus aucun message retenu.
    broker.retained.clear()
    broker.calls.clear()
    await (reconnect_cb() if which == "broker_reconnect" else birth_cb())
    assert {t: p for t, p in broker.retained.items() if "system" in t} == expected  # configurations ET états
    assert app["publications"] == {}  # aucun équipement publié : l'appareil revient quand même


@pytest.mark.asyncio
async def test_nothing_is_republished_when_disabled_or_purged(aiohttp_client):
    broker = _Broker()
    _app, cli, reconnect_cb, _birth = await _connected(aiohttp_client, broker)
    await reconnect_cb()
    assert not any("system" in t for t, _p, _r in broker.calls)  # jamais activée : rien
    await cli.post("/action/system_health", json={"enabled": True, "snapshot": SNAPSHOT}, headers=H)
    await cli.post("/action/system_health", json={"enabled": False}, headers=H)
    broker.retained.clear()
    broker.calls.clear()
    await reconnect_cb()
    assert not any("system" in t for t, _p, _r in broker.calls)  # purgée : rien ne revient


# --- Revue P3.1 : une seule collecte par envoi --------------------------------------------------

@pytest.mark.asyncio
async def test_one_retained_collection_per_send():
    """Une seule fenêtre de collecte (1,5 s sur le vrai pont) par envoi, au lieu de deux (3 s) : filtre unique
    ``<prefix>/+/+/config`` puis tri par le motif strict de l'appareil."""
    broker = _Broker()
    publisher = SystemHealthPublisher(broker)
    await publisher.apply(SNAPSHOT)
    assert broker.collects == ["homeassistant/+/+/config"]
    await publisher.purge()
    assert broker.collects == ["homeassistant/+/+/config"] * 2


@pytest.mark.asyncio
async def test_single_collection_still_sorts_out_other_entities():
    broker = _Broker()
    broker.publish_message("homeassistant/switch/jeedom2ha_system_daemon_x/config", "{}", retain=True)  # autre domaine
    broker.publish_message("homeassistant/sensor/jeedom2ha_199_1626/config", "{}", retain=True)
    broker.publish_message("homeassistant/sensor/autre_integration_system/config", "{}", retain=True)
    await SystemHealthPublisher(broker).apply(SNAPSHOT)
    assert "homeassistant/switch/jeedom2ha_system_daemon_x/config" in broker.retained
    assert "homeassistant/sensor/jeedom2ha_199_1626/config" in broker.retained
    assert "homeassistant/sensor/autre_integration_system/config" in broker.retained


@pytest.mark.asyncio
async def test_concurrent_collection_makes_the_send_fail_and_be_retried():
    """Revue P3.2 : une collecte déjà en cours (purge des scénarios) fait renvoyer None : envoi compté en échec."""
    broker = _Broker()
    broker.collect_retained_topics = AsyncMock(return_value=None)
    assert (await SystemHealthPublisher(broker).apply(SNAPSHOT))["failed"] == 1
