"""Story 11.1.bis — Multi-sensor lifecycle : dépublication exhaustive (anti-ghosts HA).

La suppression / exclusion / désactivation / retype d'un eqLogic multi-sensor
(ex. MSunPV eq553) doit effacer TOUS ses topics discovery retained : le topic
node-scoped du primaire ET chacun des secondaires. Aucun fantôme ne doit subsister.
Garde-fou : un eqLogic mono-entité efface toujours exactement un topic.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cache.disk_cache import load_publications_cache, save_publications_cache
from discovery.publisher import DiscoveryPublisher
from mapping.registry import MapperRegistry
from mapping.sensor import SensorMapper
from models.mapping import PublicationDecision
from models.topology import (
    JeedomCmd,
    JeedomEqLogic,
    JeedomObject,
    TopologySnapshot,
)
from transport.http_server import _collect_unpublish_node_ids, create_app

_SECRET = "test-secret-story-11-1-bis"

# Inventaire fidèle terrain : aucune commande ne porte de generic_type (cf. 11.1).
_MSUNPV_CMDS = [
    (5138, "Puissance panneaux", None, "W"),
    (5137, "Puissance reseau", None, "W"),
    (5139, "Routage cumulus", None, "%"),
    (5140, "Routage radiateur", None, "%"),
    (5177, "Etat sortie 1 (CE %)", None, "%"),
    (5171, "Production panneaux journaliere", None, "Wh"),
    (5170, "Production injectee journaliere", None, "Wh"),
    (5169, "Consommation reseau journaliere", None, "Wh"),
]
_MSUNPV_CMD_IDS = [c[0] for c in _MSUNPV_CMDS]


def _msunpv_eq(eq_id: int = 553) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=eq_id,
        name="MSunPV / RouteurSolaire",
        object_id=1,
        eq_type_name="msunpv",
        cmds=[
            JeedomCmd(id=cmd_id, name=name, generic_type=gt, type="info", sub_type="numeric", unit=unit)
            for cmd_id, name, gt, unit in _MSUNPV_CMDS
        ],
    )


def _mono_eq() -> JeedomEqLogic:
    return JeedomEqLogic(
        id=7000,
        name="Capteur temperature salon",
        object_id=1,
        eq_type_name="virtual",
        cmds=[JeedomCmd(id=70001, name="Temp", generic_type="TEMPERATURE", type="info", sub_type="numeric")],
    )


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-06-17T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Local technique")},
        eq_logics={eq.id: eq},
    )


# ---------------------------------------------------------------------------
# Task 1 — collecte des node_ids à dépublier (AC 1)
# ---------------------------------------------------------------------------


def test_collect_node_ids_multi_sensor_returns_all_per_command_topics():
    eq = _msunpv_eq()
    primary = MapperRegistry().map(eq, _snapshot(eq))

    node_ids = _collect_unpublish_node_ids(primary)

    # Primaire + 7 secondaires = 8 topics node-scoped, dérivés des IDs cmd Jeedom.
    expected = {f"jeedom2ha_553_{cmd_id}" for cmd_id in _MSUNPV_CMD_IDS}
    assert set(node_ids) == expected
    assert len(node_ids) == 8


def test_collect_node_ids_mono_entity_returns_empty():
    eq = _mono_eq()
    primary = MapperRegistry().map(eq, _snapshot(eq))
    # Mono-entité historique : pas de node_id → dépublication eq-level (un seul topic).
    assert _collect_unpublish_node_ids(primary) == []


def test_collect_node_ids_handles_none():
    assert _collect_unpublish_node_ids(None) == []


# ---------------------------------------------------------------------------
# Task 2 — dépublication exhaustive (AC 2, 4, 5)
# ---------------------------------------------------------------------------


async def test_unpublish_multi_sensor_erases_primary_and_all_secondaries():
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(bridge)

    node_ids = [f"jeedom2ha_553_{cmd_id}" for cmd_id in _MSUNPV_CMD_IDS]
    ok = await publisher.unpublish_by_eq_id(553, entity_type="sensor", node_ids=node_ids)
    assert ok is True

    erased = {call.args[0] for call in bridge.publish_message.call_args_list}
    expected = {f"homeassistant/sensor/{nid}/config" for nid in node_ids}
    assert erased == expected
    # Tous les payloads sont vides + retained (effacement discovery).
    for call in bridge.publish_message.call_args_list:
        assert call.args[1] == ""
        assert call.kwargs.get("retain") is True
    # Aucun topic eq-level orphelin (jeedom2ha_553/config jamais publié pour multi-sensor).
    assert "homeassistant/sensor/jeedom2ha_553/config" not in erased


async def test_unpublish_mono_entity_erases_exactly_one_topic():
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(bridge)

    ok = await publisher.unpublish_by_eq_id(7000, entity_type="sensor", node_ids=[])
    assert ok is True
    assert bridge.publish_message.call_count == 1
    assert bridge.publish_message.call_args.args[0] == "homeassistant/sensor/jeedom2ha_7000/config"


async def test_unpublish_partial_failure_is_reported_honestly():
    bridge = MagicMock()

    def _publish(topic, *_a, **_k):
        # Un secondaire échoue à être effacé.
        return not topic.endswith("jeedom2ha_553_5140/config")

    bridge.publish_message = MagicMock(side_effect=_publish)
    publisher = DiscoveryPublisher(bridge)

    node_ids = [f"jeedom2ha_553_{cmd_id}" for cmd_id in _MSUNPV_CMD_IDS]
    ok = await publisher.unpublish_by_eq_id(553, entity_type="sensor", node_ids=node_ids)
    # Honnêteté : un secondaire non effacé ne doit pas déclarer un faux succès global.
    assert ok is False
    # Mais on a quand même tenté d'effacer TOUS les topics (pas d'arrêt au premier échec).
    assert bridge.publish_message.call_count == 8


async def test_unpublish_backward_compatible_default_signature():
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(bridge)
    # Appel historique sans node_ids → comportement mono-topic inchangé.
    ok = await publisher.unpublish_by_eq_id(42, entity_type="light")
    assert ok is True
    assert bridge.publish_message.call_args.args[0] == "homeassistant/light/jeedom2ha_42/config"


# ---------------------------------------------------------------------------
# Task 1 — persistance des node_ids dans le cache disque (AC 1)
# ---------------------------------------------------------------------------


def test_disk_cache_persists_and_reloads_secondary_node_ids(tmp_path):
    eq = _msunpv_eq()
    primary = MapperRegistry().map(eq, _snapshot(eq))
    decision = PublicationDecision(
        should_publish=True, reason="sure", mapping_result=primary, discovery_published=True
    )
    save_publications_cache({553: decision}, str(tmp_path))

    reloaded = load_publications_cache(str(tmp_path))
    assert 553 in reloaded
    expected = {f"jeedom2ha_553_{cmd_id}" for cmd_id in _MSUNPV_CMD_IDS}
    assert set(reloaded[553]["node_ids"]) == expected


def test_disk_cache_backward_compatible_without_node_ids(tmp_path):
    import json
    import os

    legacy = {"42": {"entity_type": "light", "published": True, "ha_name": "X", "suggested_area": None}}
    with open(os.path.join(str(tmp_path), "jeedom2ha_cache.json"), "w", encoding="utf-8") as f:
        json.dump(legacy, f)

    reloaded = load_publications_cache(str(tmp_path))
    assert reloaded[42]["node_ids"] == []  # défaut BC


# ---------------------------------------------------------------------------
# Task 3 — couverture des déclencheurs de cycle de vie via /action/execute (AC 2, 3, 6)
# ---------------------------------------------------------------------------


def _sync_body():
    return {
        "action": "sync",
        "payload": {
            "objects": [{"id": 1, "name": "Local technique"}],
            "eq_logics": [
                {
                    "id": 553,
                    "name": "MSunPV / RouteurSolaire",
                    "object_id": 1,
                    "is_enable": True,
                    "is_visible": True,
                    "eq_type": "msunpv",
                    "is_excluded": False,
                    "status": {"timeout": 0},
                    "cmds": [
                        {"id": c, "name": n, "generic_type": g, "type": "info", "sub_type": "numeric", "unit": u}
                        for c, n, g, u in _MSUNPV_CMDS
                    ],
                }
            ],
            "sync_config": {"confidence_policy": "sure_probable"},
        },
        "request_id": "story-11-1-bis-test",
        "timestamp": "2026-06-17T00:00:00Z",
    }


async def test_action_supprimer_erases_all_multi_sensor_topics(aiohttp_client):
    app = create_app(local_secret=_SECRET)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    app["mqtt_bridge"] = bridge
    client = await aiohttp_client(app)

    with patch("transport.http_server.save_publications_cache"):
        resp = await client.post("/action/sync", json=_sync_body(), headers={"X-Local-Secret": _SECRET})
        assert resp.status == 200

        bridge.publish_message.reset_mock()

        supprimer_body = {
            "action": "execute",
            "payload": {"intention": "supprimer", "portee": "equipement", "selection": [553]},
            "request_id": "supprimer-553",
            "timestamp": "2026-06-17T00:01:00Z",
        }
        resp2 = await client.post("/action/execute", json=supprimer_body, headers={"X-Local-Secret": _SECRET})
        assert resp2.status == 200

    erased_empty = {
        call.args[0]
        for call in bridge.publish_message.call_args_list
        if call.args[0].startswith("homeassistant/sensor/jeedom2ha_553_") and call.args[1] == ""
    }
    expected = {f"homeassistant/sensor/jeedom2ha_553_{cmd_id}/config" for cmd_id in _MSUNPV_CMD_IDS}
    assert erased_empty == expected, "tous les topics multi-sensor doivent être effacés (zéro ghost)"
