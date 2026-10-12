"""Story 21.1 — bloc A (CC-44) : cycle de vie du bouton HA d'un scénario.

Couvre AC 1 à 6 bis : retrait d'un scénario inactif, réactivation, purge « le
broker fait foi » (topics retenus) avec garde-fous, absence de report via
``pending_discovery_unpublish`` (clé ``eq_id``), disponibilité/appareil du bouton
en pont seul. Identifiants numériques uniquement (CC-48).
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from discovery.publisher import DiscoveryPublisher
from mapping.button import ScenarioButtonMapper
from models.topology import TopologySnapshot
from transport.mqtt_client import MqttBridge

SECRET = "test_secret"


def _topic(sc_id) -> str:
    return f"homeassistant/button/jeedom2ha_scenario_{sc_id}/config"


def _fake_bridge(connected=True, retained=None):
    """Bridge simulé : enregistre les publish_message, sert les topics retenus."""
    bridge = MagicMock()
    bridge.is_connected = connected
    bridge.state = "connected" if connected else "disconnected"
    bridge.published = []

    def _publish(topic, payload, qos=1, retain=False):
        bridge.published.append((topic, payload, qos, retain))
        return True

    bridge.publish_message.side_effect = _publish
    bridge.collect_retained_topics = AsyncMock(return_value=retained)
    return bridge


def _sync_body(scenarios=None, eq_logics=None, with_scenarios_key=True, complete=True):
    payload = {"objects": [], "eq_logics": eq_logics or []}
    if with_scenarios_key:
        payload["scenarios"] = scenarios or []
        payload["scenarios_complete"] = complete
    return {
        "action": "sync",
        "payload": payload,
        "request_id": "t-21-1",
        "timestamp": "2026-10-11T00:00:00Z",
    }


async def _sync(cli, **kwargs):
    resp = await cli.post(
        "/action/sync", json=_sync_body(**kwargs), headers={"X-Local-Secret": SECRET}
    )
    assert resp.status == 200
    return await resp.json()


async def _client(aiohttp_client, bridge):
    from transport.http_server import create_app

    app = create_app(local_secret=SECRET)
    app["mqtt_bridge"] = bridge
    cli = await aiohttp_client(app)
    return app, cli


def _empties(bridge):
    """Topics vidés (payload vide retenu qos 1)."""
    return [t for (t, p, q, r) in bridge.published if p == "" and q == 1 and r is True]


def _configs(bridge):
    return {t: json.loads(p) for (t, p, q, r) in bridge.published if p}


# ---------------------------------------------------------------------------
# AC 1 / AC 2 — inactif dépublié, actif publié, réactivation
# ---------------------------------------------------------------------------

async def test_inactive_scenario_is_unpublished_active_is_published(aiohttp_client):
    bridge = _fake_bridge(retained=[])
    app, cli = await _client(aiohttp_client, bridge)

    await _sync(cli, scenarios=[
        {"id": 20, "name": "S20", "is_active": True},
        {"id": 72, "name": "S72", "is_active": False},
    ])

    assert _topic(72) in _empties(bridge)
    assert _topic(20) not in _empties(bridge)
    assert _topic(20) in _configs(bridge)
    assert _topic(72) not in _configs(bridge)
    # Un inactif n'est pas enregistré comme bouton actif (appui rejeté).
    assert 20 in app["scenario_publications"]
    assert 72 not in app["scenario_publications"]


async def test_reactivated_scenario_is_republished_same_identity(aiohttp_client):
    bridge = _fake_bridge(retained=[])
    app, cli = await _client(aiohttp_client, bridge)

    await _sync(cli, scenarios=[{"id": 72, "name": "S72", "is_active": True}])
    first = _configs(bridge)[_topic(72)]
    await _sync(cli, scenarios=[{"id": 72, "name": "S72", "is_active": False}])
    assert _topic(72) in _empties(bridge)
    assert 72 not in app["scenario_publications"]

    bridge.published.clear()
    await _sync(cli, scenarios=[{"id": 72, "name": "S72", "is_active": True}])
    again = _configs(bridge)[_topic(72)]
    assert again["unique_id"] == first["unique_id"] == "jeedom2ha_scenario_72"
    assert again["command_topic"] == first["command_topic"] == "jeedom2ha/scenario_72/cmd"
    assert 72 in app["scenario_publications"]
    assert _topic(72) not in _empties(bridge)


# ---------------------------------------------------------------------------
# AC 3 — le broker fait foi
# ---------------------------------------------------------------------------

async def test_broker_ghosts_are_purged_active_kept(aiohttp_client):
    # 72 inactif (snapshot), 129 et 32 inconnus du snapshot, 20 actif.
    bridge = _fake_bridge(retained=[_topic(20), _topic(72), _topic(129), _topic(32)])
    app, cli = await _client(aiohttp_client, bridge)

    await _sync(cli, scenarios=[
        {"id": 20, "name": "S20", "is_active": True},
        {"id": 72, "name": "S72", "is_active": False},
    ])

    empties = _empties(bridge)
    assert _topic(129) in empties and _topic(32) in empties and _topic(72) in empties
    assert _topic(20) not in empties
    # Chaque topic est vidé une seule fois (72 : boucle + purge ne doublonnent pas).
    assert len(empties) == len(set(empties)) == 3
    bridge.collect_retained_topics.assert_awaited_once()


async def test_purge_never_touches_topics_outside_strict_pattern(aiohttp_client):
    junk = [
        "homeassistant/button/jeedom2ha_eq_20/config",
        "homeassistant/light/jeedom2ha_scenario_9/config",
        "other_prefix/button/jeedom2ha_scenario_9/config",
        "homeassistant/button/jeedom2ha_scenario_9/state",
        "homeassistant/button/jeedom2ha_scenario_x/config",
        "homeassistant/button/jeedom2ha_scenario_/config",
        "homeassistant/button/jeedom2ha_scenario_9/extra/config",
        "homeassistant/button/other_scenario_9/config",
        "homeassistant/button/jeedom2ha_scenario_-3/config",
        "homeassistant/button/jeedom2ha_scenario_9/config\n",  # `$` l'aurait accepté
    ]
    bridge = _fake_bridge(retained=junk + [_topic(129)])
    app, cli = await _client(aiohttp_client, bridge)

    await _sync(cli, scenarios=[{"id": 20, "name": "S20", "is_active": True}])

    assert _empties(bridge) == [_topic(129)]


@pytest.mark.parametrize("retained", [None, [], "garbage"])
async def test_empty_failed_or_invalid_collection_purges_nothing(aiohttp_client, retained):
    bridge = _fake_bridge(retained=retained)
    app, cli = await _client(aiohttp_client, bridge)

    data = await _sync(cli, scenarios=[{"id": 20, "name": "S20", "is_active": True}])

    assert data["status"] == "ok"
    assert _empties(bridge) == []


async def test_collection_exception_purges_nothing_and_sync_succeeds(aiohttp_client):
    bridge = _fake_bridge(retained=[_topic(129)])
    bridge.collect_retained_topics = AsyncMock(side_effect=RuntimeError("boom"))
    app, cli = await _client(aiohttp_client, bridge)

    data = await _sync(cli, scenarios=[{"id": 20, "name": "S20", "is_active": True}])

    assert data["status"] == "ok"
    assert _empties(bridge) == []


async def test_missing_scenarios_section_triggers_no_purge(aiohttp_client):
    bridge = _fake_bridge(retained=[_topic(20), _topic(129)])
    app, cli = await _client(aiohttp_client, bridge)

    await _sync(cli, with_scenarios_key=False)

    assert _empties(bridge) == []
    bridge.collect_retained_topics.assert_not_awaited()


async def test_scenarios_section_not_a_list_triggers_no_purge(aiohttp_client):
    bridge = _fake_bridge(retained=[_topic(129)])
    app, cli = await _client(aiohttp_client, bridge)
    body = _sync_body()
    body["payload"]["scenarios"] = None
    resp = await cli.post("/action/sync", json=body, headers={"X-Local-Secret": SECRET})
    assert resp.status == 200

    assert _empties(bridge) == []
    bridge.collect_retained_topics.assert_not_awaited()


async def test_unparsable_scenario_entry_triggers_no_purge(aiohttp_client):
    """Une entrée illisible ne doit jamais faire passer un actif pour un fantôme."""
    bridge = _fake_bridge(retained=[_topic(7), _topic(129)])
    app, cli = await _client(aiohttp_client, bridge)

    await _sync(cli, scenarios=[
        {"id": 20, "name": "S20", "is_active": True},
        {"id": "not-an-int", "name": "?", "is_active": True},
    ])

    assert _empties(bridge) == []
    bridge.collect_retained_topics.assert_not_awaited()


@pytest.mark.parametrize("complete", [False, None])
async def test_scenarios_not_declared_complete_triggers_no_purge(aiohttp_client, complete):
    """Le producteur PHP a ignoré un scénario illisible (ou ne déclare rien) : pas de purge."""
    bridge = _fake_bridge(retained=[_topic(20), _topic(129)])
    app, cli = await _client(aiohttp_client, bridge)
    body = _sync_body(scenarios=[{"id": 21, "name": "S21", "is_active": True}])
    if complete is None:
        del body["payload"]["scenarios_complete"]
    else:
        body["payload"]["scenarios_complete"] = complete
    resp = await cli.post("/action/sync", json=body, headers={"X-Local-Secret": SECRET})
    assert resp.status == 200

    assert _empties(bridge) == []
    bridge.collect_retained_topics.assert_not_awaited()


async def test_present_but_empty_scenarios_section_purges_ghosts(aiohttp_client):
    """Section présente et vide (plus aucun scénario) : les fantômes sont retirés."""
    bridge = _fake_bridge(retained=[_topic(129)])
    app, cli = await _client(aiohttp_client, bridge)

    await _sync(cli, scenarios=[])

    assert _empties(bridge) == [_topic(129)]


async def test_active_scenario_whose_publication_fails_is_never_purged(aiohttp_client):
    bridge = _fake_bridge(retained=[_topic(20), _topic(129)])

    def _publish(topic, payload, qos=1, retain=False):
        bridge.published.append((topic, payload, qos, retain))
        return payload == ""  # la publication d'une config échoue, les vidages passent

    bridge.publish_message.side_effect = _publish
    app, cli = await _client(aiohttp_client, bridge)

    await _sync(cli, scenarios=[{"id": 20, "name": "S20", "is_active": True}])

    assert _topic(20) not in _empties(bridge)
    assert _empties(bridge) == [_topic(129)]
    assert app["scenario_publications"][20].discovery_published is False


async def test_logs_report_collected_count_and_emptied_ids_only(aiohttp_client, caplog):
    import logging

    caplog.set_level(logging.INFO)
    bridge = _fake_bridge(retained=[_topic(20), _topic(72), _topic(129), "homeassistant/button/jeedom2ha_eq_5/config"])
    app, cli = await _client(aiohttp_client, bridge)

    await _sync(cli, scenarios=[
        {"id": 20, "name": "NomReelSecret", "is_active": True},
        {"id": 72, "name": "AutreNomReel", "is_active": False},
    ])

    # Seules les lignes `[SCENARIO]` / retrait sont concernées (le log de publication
    # existant `[DISCOVERY] Publishing button config` affiche déjà le nom, hors périmètre).
    text = "\n".join(
        r.getMessage() for r in caplog.records
        if "[SCENARIO]" in r.getMessage() or "Unpublishing" in r.getMessage()
    )
    assert "Retained button topics collected: 4 (3 scenario button(s))" in text
    assert "ids=[72, 129]" in text
    assert "NomReelSecret" not in text and "AutreNomReel" not in text


async def test_logs_report_zero_collected_topics(aiohttp_client, caplog):
    import logging

    caplog.set_level(logging.INFO)
    bridge = _fake_bridge(retained=[])
    app, cli = await _client(aiohttp_client, bridge)

    await _sync(cli, scenarios=[{"id": 20, "name": "S20", "is_active": True}])

    assert "Retained button topics collected: 0 (0 scenario button(s))" in caplog.text


# ---------------------------------------------------------------------------
# AC 4 — broker déconnecté, pas de report, collision d'id
# ---------------------------------------------------------------------------

async def test_disconnected_broker_no_purge_no_deferral(aiohttp_client):
    bridge = _fake_bridge(connected=False, retained=[_topic(129)])
    app, cli = await _client(aiohttp_client, bridge)

    await _sync(cli, scenarios=[
        {"id": 20, "name": "S20", "is_active": True},
        {"id": 72, "name": "S72", "is_active": False},
    ])

    assert bridge.published == []
    bridge.collect_retained_topics.assert_not_awaited()
    # Rien n'est reporté dans le mécanisme indexé par eq_id (C5).
    assert not app["pending_discovery_unpublish"]
    assert not app["pending_local_availability_cleanup"]


async def test_scenario_unpublish_does_not_touch_equipment_with_same_id(aiohttp_client):
    bridge = _fake_bridge(retained=[_topic(10)])
    app, cli = await _client(aiohttp_client, bridge)
    sentinel = {"entity_type": "light", "node_ids": []}
    app["pending_discovery_unpublish"][10] = sentinel

    await _sync(cli, scenarios=[{"id": 10, "name": "S10", "is_active": False}])

    empties = _empties(bridge)
    # Chacun suit son propre chemin : le report de l'équipement 10 est rejoué comme
    # avant (topic light), le scénario 10 est vidé une seule fois (topic button).
    assert empties.count(_topic(10)) == 1
    assert "homeassistant/light/jeedom2ha_10/config" in empties
    assert 10 not in app["pending_discovery_unpublish"]


# ---------------------------------------------------------------------------
# AC 5 — appui sur un bouton (non-régression)
# ---------------------------------------------------------------------------

async def test_press_accepted_for_active_rejected_for_inactive(aiohttp_client):
    bridge = _fake_bridge(retained=[])
    app, cli = await _client(aiohttp_client, bridge)
    await _sync(cli, scenarios=[
        {"id": 20, "name": "S20", "is_active": True},
        {"id": 72, "name": "S72", "is_active": False},
    ])
    pubs = app["scenario_publications"]
    assert pubs[20].should_publish is True
    assert 72 not in pubs  # → `_handle_scenario_command` rejette (unknown_runtime_entity)


# ---------------------------------------------------------------------------
# AC 6 bis — disponibilité et appareil : pont seul
# ---------------------------------------------------------------------------

def _snapshot(with_homonym: bool) -> TopologySnapshot:
    eq_logics = []
    if with_homonym:
        eq_logics.append({
            "id": 110, "name": "E110", "object_id": None, "is_enable": True,
            "is_visible": True, "eq_type": "zigbee", "is_excluded": False,
            "status": {"timeout": 1},  # support local + hors ligne
            "cmds": [],
        })
    return TopologySnapshot.from_jeedom_payload({
        "objects": [], "eq_logics": eq_logics,
        "scenarios": [{"id": 110, "name": "S110", "is_active": True}],
    })


def _button_payload(snapshot: TopologySnapshot) -> dict:
    publisher = DiscoveryPublisher(MagicMock())
    mapping = ScenarioButtonMapper().map(snapshot.scenarios[110])
    return publisher._build_button_payload(mapping, snapshot)


def test_scenario_button_ignores_homonym_equipment_availability_and_device():
    with_eq = _button_payload(_snapshot(with_homonym=True))
    text = json.dumps(with_eq)

    assert "jeedom2ha/110/availability" not in text
    assert "zigbee" not in text
    assert with_eq["availability_topic"] == "jeedom2ha/bridge/status"
    assert "availability" not in with_eq  # aucune entrée locale
    assert with_eq["device"]["manufacturer"] == "Jeedom"
    assert with_eq["device"]["model"] == "Unknown"
    assert with_eq["device"]["identifiers"] == ["jeedom2ha_scenario_110"]


# Charge utile d'un bouton de scénario sans équipement homonyme, figée AVANT cette PR
# (générée depuis `main` 078416a) : elle ne doit pas bouger, hors cas de collision d'id.
def _frozen_pre_pr_scenario_button_payload() -> dict:
    from discovery.publisher import _SW_VERSION

    return {
        "availability_topic": "jeedom2ha/bridge/status",
        "command_topic": "jeedom2ha/scenario_110/cmd",
        # Story 22.1 (Q7 B) : seul champ additif réaligné, avec device.name des équipements.
        "default_entity_id": "button.jeedom2ha_scenario_110",
        "device": {
            "identifiers": ["jeedom2ha_scenario_110"],
            "manufacturer": "Jeedom",
            "model": "Unknown",
            "name": "S110",
            "via_device": "jeedom2ha_bridge",
        },
        # Story 22.3 : nom d'entité identique au nom d'appareil -> null (convention HA).
        "name": None,
        "object_id": "jeedom2ha_scenario_110",
        "origin": {"name": "jeedom2ha", "sw_version": _SW_VERSION},
        "platform": "mqtt",
        "unique_id": "jeedom2ha_scenario_110",
    }


def test_scenario_button_payload_matches_frozen_pre_pr_reference_without_homonym():
    assert _button_payload(_snapshot(with_homonym=False)) == _frozen_pre_pr_scenario_button_payload()


def test_scenario_button_payload_with_homonym_equals_the_same_reference():
    """Avec un homonyme, le bouton retombe sur la même charge de référence (pont seul)."""
    assert _button_payload(_snapshot(with_homonym=True)) == _frozen_pre_pr_scenario_button_payload()


def test_equipment_button_still_uses_local_availability():
    """Le bouton d'un équipement (source_kind absent) garde son comportement."""
    snapshot = _snapshot(with_homonym=True)
    publisher = DiscoveryPublisher(MagicMock())
    mapping = ScenarioButtonMapper().map(snapshot.scenarios[110])
    mapping.reason_details = {"command_topic": "jeedom2ha/110/cmd"}  # pas de source_kind
    mapping.ha_unique_id = "jeedom2ha_eq_110"
    payload = publisher._build_button_payload(mapping, snapshot)
    assert "jeedom2ha/110/availability" in json.dumps(payload)
    assert payload["device"]["manufacturer"] == "Jeedom (zigbee)"


# ---------------------------------------------------------------------------
# Lecture des topics retenus (MqttBridge.collect_retained_topics)
# ---------------------------------------------------------------------------

def _msg(topic, payload=b"{}", retain=True):
    return SimpleNamespace(topic=topic, payload=payload, retain=retain)


async def test_collect_retained_returns_none_when_disconnected():
    bridge = MqttBridge()
    assert await bridge.collect_retained_topics("homeassistant/button/+/config", 0.01) is None


async def test_collect_retained_gathers_matching_retained_messages_only():
    import asyncio

    bridge = MqttBridge()
    bridge._state = "connected"
    bridge._loop = asyncio.get_running_loop()
    bridge._command_handler = MagicMock()
    client = MagicMock()
    client.subscribe.return_value = (0, 1)
    client.unsubscribe.return_value = (0, 2)
    bridge._client = client

    flt = "homeassistant/button/+/config"

    async def _deliver():
        await asyncio.sleep(0.01)
        bridge._on_message(client, None, _msg(_topic(72)))
        bridge._on_message(client, None, _msg(_topic(9), payload=b""))  # vide : ignoré
        bridge._on_message(client, None, _msg("homeassistant/light/x/config"))  # hors filtre
        bridge._on_message(client, None, _msg(_topic(5), retain=False))  # non retenu : ignoré
        bridge._on_message(client, None, _msg("jeedom2ha/20/cmd", payload=b"x"))

    task = asyncio.create_task(_deliver())
    topics = await bridge.collect_retained_topics(flt, 0.1)
    await task
    await asyncio.sleep(0)  # laisse passer le dispatch call_soon_threadsafe

    assert topics == [_topic(72)]
    client.subscribe.assert_called_once_with(flt, qos=1)
    client.unsubscribe.assert_called_once_with(flt)
    assert bridge._retained_collector is None


async def test_command_message_keeps_its_normal_path_outside_and_during_collection():
    import asyncio

    bridge = MqttBridge()
    bridge._state = "connected"
    bridge._loop = asyncio.get_running_loop()
    handler = MagicMock(return_value=None)
    bridge.set_command_handler(handler)
    client = MagicMock()
    client.subscribe.return_value = (0, 1)
    bridge._client = client

    # Hors collecte : le chemin normal est inchangé.
    bridge._on_message(client, None, _msg("jeedom2ha/scenario_20/cmd", payload=b"press", retain=False))
    await asyncio.sleep(0)
    handler.assert_called_once_with("jeedom2ha/scenario_20/cmd", "press")

    # Pendant la collecte : un topic de config n'est jamais transmis au gestionnaire de commandes.
    handler.reset_mock()

    async def _deliver():
        await asyncio.sleep(0.01)
        bridge._on_message(client, None, _msg(_topic(72)))

    task = asyncio.create_task(_deliver())
    assert await bridge.collect_retained_topics("homeassistant/button/+/config", 0.05) == [_topic(72)]
    await task
    await asyncio.sleep(0)
    handler.assert_not_called()


async def test_live_command_matching_the_collection_filter_is_still_dispatched():
    """Story 23.3 (R1-1): only RETAINED messages are collection traffic; a live
    (non-retained) command on a topic matching the filter must reach the handler."""
    import asyncio

    bridge = MqttBridge()
    bridge._state = "connected"
    bridge._loop = asyncio.get_running_loop()
    handler = MagicMock(return_value=None)
    bridge.set_command_handler(handler)
    client = MagicMock()
    client.subscribe.return_value = (0, 1)
    client.unsubscribe.return_value = (0, 2)
    bridge._client = client

    async def _deliver():
        await asyncio.sleep(0.01)
        bridge._on_message(client, None, _msg("jeedom2ha/1/set", payload=b"ON", retain=False))
        bridge._on_message(client, None, _msg("jeedom2ha/1/brightness/set", payload=b"40", retain=False))
        bridge._on_message(client, None, _msg("jeedom2ha/1/position/set", payload=b"10", retain=False))
        bridge._on_message(client, None, _msg("jeedom2ha/1/state", payload=b"ON", retain=True))

    task = asyncio.create_task(_deliver())
    topics = await bridge.collect_retained_topics("jeedom2ha/#", 0.1)
    await task
    await asyncio.sleep(0)

    assert topics == ["jeedom2ha/1/state"]
    assert [c.args for c in handler.call_args_list] == [
        ("jeedom2ha/1/set", "ON"),
        ("jeedom2ha/1/brightness/set", "40"),
        ("jeedom2ha/1/position/set", "10"),
    ]


async def test_collect_retained_unsubscribes_even_when_an_exception_occurs(monkeypatch):
    import asyncio

    bridge = MqttBridge()
    bridge._state = "connected"
    bridge._loop = asyncio.get_running_loop()
    client = MagicMock()
    client.subscribe.return_value = (0, 1)
    bridge._client = client

    async def _boom(_delay):
        raise RuntimeError("boom during window")

    monkeypatch.setattr("transport.mqtt_client.asyncio.sleep", _boom)
    with pytest.raises(RuntimeError):
        await bridge.collect_retained_topics("homeassistant/button/+/config", 1.0)

    client.unsubscribe.assert_called_once_with("homeassistant/button/+/config")
    assert bridge._retained_collector is None


async def test_concurrent_collection_returns_none_and_purges_nothing():
    import asyncio

    bridge = MqttBridge()
    bridge._state = "connected"
    bridge._loop = asyncio.get_running_loop()
    client = MagicMock()
    client.subscribe.return_value = (0, 1)
    bridge._client = client

    first = asyncio.create_task(bridge.collect_retained_topics("homeassistant/button/+/config", 0.1))
    await asyncio.sleep(0.01)  # la première collecte est en cours
    assert await bridge.collect_retained_topics("homeassistant/button/+/config", 0.01) is None
    purged = await DiscoveryPublisher(bridge).purge_orphan_scenario_buttons({20})
    assert purged == []
    client.publish.assert_not_called()
    assert await first == []
    # Un seul abonnement / désabonnement : le second appel n'a rien touché.
    client.subscribe.assert_called_once()
    client.unsubscribe.assert_called_once()


async def test_collect_retained_subscribe_failure_returns_none():
    import asyncio

    bridge = MqttBridge()
    bridge._state = "connected"
    bridge._loop = asyncio.get_running_loop()
    client = MagicMock()
    client.subscribe.return_value = (4, None)  # erreur
    bridge._client = client

    assert await bridge.collect_retained_topics("x/+/config", 0.01) is None
    assert bridge._retained_collector is None
