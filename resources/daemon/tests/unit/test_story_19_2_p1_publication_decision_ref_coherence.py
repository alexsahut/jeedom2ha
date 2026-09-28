"""Story 19.2 — P1 (revue ClaudeBox, commit 3a408db) : cohérence de
``publication_decision_ref`` (principal ET secondaires) à travers les actions
``supprimer``/``publier``, jamais seulement ``app["publications"]``.

Avant le fix, seul ``publications[eq_id]`` était remplacé par la décision
refusée/échouée ; ``mapping.publication_decision_ref`` — consulté par les
lecteurs I11 (``sync/state.py``, ``sync/command.py``) — continuait de pointer
sur l'ancienne décision jusqu'à la prochaine synchro complète. Un équipement
supprimé/exclu pouvait donc continuer à streamer son état et à router ses
commandes ; à l'inverse, une republication réussie après un échec précédent
restait bloquée tant que la synchro complète n'avait pas rafraîchi la
référence.

Test 1 pilote les vrais endpoints HTTP (``/action/sync`` puis
``/action/execute``) pour prouver le comportement de bout en bout. Tests 2/3
construisent l'état applicatif à la main (comme test_story_5_2), plus rapide
pour isoler un seul embranchement de ``_handle_action_execute``. Test 4 cible
directement ``_publish_additional_sensors`` (fix P2).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import transport.http_server as http_server
from mapping.registry import MapperRegistry
from models.mapping import PublicationDecision
from models.topology import EligibilityResult, JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from sync.command import CommandSynchronizer
from sync.state import StateSynchronizer
from transport.http_server import create_app

_SECRET = "test-secret-story-19-2-p1"
_JEEDOM_API = "http://jeedom.test/core/api/jeeApi.php"


# ---------------------------------------------------------------------------
# Fixtures partagées — eq553 (MSunPV, multi-sensor, sans commande) pilote via
# /action/sync réel ; eq628 (multi-switch, Story 11.3) pilote état + commande.
# ---------------------------------------------------------------------------

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

# Capture terrain eq554 (Story 11.2, multi-domaine) — (id, name, type, sub_type,
# generic_type, unit). Dupliquée localement (plutôt qu'importée depuis
# test_story_11_2_eq554_multi_domain) pour garder ce fichier P1-bis autonome.
_EQ554_CMDS = [
    (5205, "Routage", "info", "numeric", None, "%"),
    (5530, "Routage réel", "info", "numeric", "ENERGY_STATE", "%"),
    (5706, "On_5701", "action", "other", "ENERGY_ON", None),
    (5707, "Off_5702", "action", "other", "ENERGY_OFF", None),
    (5204, "Rafraichir", "action", "other", None, None),
    (5206, "Puissance", "info", "numeric", None, "W"),
    (5489, "etat", "info", "string", None, None),
    (5372, "Absence", "action", "other", None, None),
    (5490, "Manu", "action", "other", "ENERGY_ON", None),
    (5491, "auto", "action", "other", "ENERGY_OFF", None),
    (5510, "chauffe complète dans la journée", "info", "binary", None, None),
    (5531, "Routage chauffe complete", "info", "numeric", None, "%"),
    (5535, "CE Kwh chauffe complete", "info", "numeric", None, "kWh"),
    (5532, "Routage 24H jusqua 22H36 hier", "info", "numeric", None, "%"),
    (5533, "Routage aujourdhui", "info", "numeric", None, "%"),
    (5534, "CE kWh 24H jusqua 22H36 hier", "info", "numeric", None, "kWh"),
    (5527, "CE kWh depuis 22H36 hier", "info", "numeric", None, "kWh"),
    (5542, "eq H de chauffe hier", "info", "numeric", None, "H"),
    (5538, "eq H de chauffe aujourdhui", "info", "numeric", None, "H"),
    (5543, "mediane chauffe complete sur 7 jours", "info", "numeric", None, "%"),
    (5708, "activé", "info", "binary", "ENERGY_STATE", None),
]


def _eq554_eq_payload(eq_id: int = 554) -> dict:
    return {
        "id": eq_id,
        "name": "Chauffe-eau",
        "object_id": 1,
        "is_enable": True,
        "is_visible": True,
        "eq_type": "virtual",
        "is_excluded": False,
        "status": {"timeout": 0},
        "cmds": [
            {"id": c, "name": n, "generic_type": g, "type": t, "sub_type": st, "unit": u}
            for c, n, t, st, g, u in _EQ554_CMDS
        ],
    }

_EQ628_CMDS = [
    (5977, "Filtration piscine", "info", "binary", "SWITCH_STATE"),
    (5978, "Filtration piscine On", "action", "other", "SWITCH_ON"),
    (5979, "Filtration piscine Off", "action", "other", "SWITCH_OFF"),
    (5980, "Chauffage piscine", "info", "binary", "SWITCH_STATE"),
    (5981, "Chauffage piscine On", "action", "other", "SWITCH_ON"),
    (5982, "Chauffage piscine Off", "action", "other", "SWITCH_OFF"),
    (5983, "Chauffage SPA", "info", "binary", "SWITCH_STATE"),
    (5984, "Chauffage SPA On", "action", "other", "SWITCH_ON"),
    (5985, "Chauffage SPA Off", "action", "other", "SWITCH_OFF"),
    (6004, "Charge voiture", "info", "binary", "SWITCH_STATE"),
    (6005, "Charge voiture On", "action", "other", "SWITCH_ON"),
    (6006, "Charge voiture Off", "action", "other", "SWITCH_OFF"),
    (5976, "Rafraichir", "action", "other", None),
]


def _msunpv_eq_payload(eq_id: int = 553) -> dict:
    return {
        "id": eq_id,
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


def _eq628_eq_payload(eq_id: int = 628) -> dict:
    return {
        "id": eq_id,
        "name": "Pilotage priorisation solaire",
        "object_id": 1,
        "is_enable": True,
        "is_visible": True,
        "eq_type": "virtual",
        "is_excluded": False,
        "status": {"timeout": 0},
        "cmds": [
            {"id": c, "name": n, "type": t, "sub_type": st, "generic_type": g}
            for c, n, t, st, g in _EQ628_CMDS
        ],
    }


def _sync_body(eq_payloads: list[dict]) -> dict:
    return {
        "action": "sync",
        "payload": {
            "objects": [{"id": 1, "name": "Local technique"}],
            "eq_logics": eq_payloads,
            "sync_config": {"confidence_policy": "sure_probable"},
        },
        "request_id": "story-19-2-p1-test",
        "timestamp": "2026-09-28T00:00:00Z",
    }


def _eq628_topology() -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-09-28T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Energie")},
        eq_logics={
            628: JeedomEqLogic(
                id=628,
                name="Pilotage priorisation solaire",
                object_id=1,
                eq_type_name="virtual",
                cmds=[
                    JeedomCmd(id=c, name=n, type=t, sub_type=st, generic_type=g)
                    for c, n, t, st, g in _EQ628_CMDS
                ],
            )
        },
    )


def _map_eq628():
    topology = _eq628_topology()
    mapping = MapperRegistry().map(topology.eq_logics[628], topology)
    assert mapping is not None and mapping.additional_mappings, "eq628 fixture drifted: expected secondaries"
    return topology, mapping


def _published_switch_decision(mapping) -> PublicationDecision:
    decision = PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=mapping,
        state_topic=mapping.reason_details["state_topic"],
        active_or_alive=True,
        discovery_published=True,
    )
    mapping.publication_decision_ref = decision
    return decision


@pytest.fixture
def bridge() -> MagicMock:
    b = MagicMock()
    b.is_connected = True
    b.publish_message = MagicMock(return_value=True)
    return b


# ---------------------------------------------------------------------------
# Test 1 — bout en bout "supprimer" : multi-capteur (état) + multi-switch (commande)
# ---------------------------------------------------------------------------


async def test_e2e_supprimer_stops_state_streaming_and_command_routing(aiohttp_client, bridge):
    app = create_app(local_secret=_SECRET)
    app["mqtt_bridge"] = bridge
    client = await aiohttp_client(app)

    with patch("transport.http_server.save_publications_cache"):
        resp = await client.post(
            "/action/sync",
            json=_sync_body([_msunpv_eq_payload(), _eq628_eq_payload()]),
            headers={"X-Local-Secret": _SECRET},
        )
        assert resp.status == 200

        bridge.publish_message.reset_mock()

        supprimer_body = {
            "action": "execute",
            "payload": {"intention": "supprimer", "portee": "equipement", "selection": [553, 628]},
            "request_id": "supprimer-553-628",
            "timestamp": "2026-09-28T00:01:00Z",
        }
        resp2 = await client.post("/action/execute", json=supprimer_body, headers={"X-Local-Secret": _SECRET})
        assert resp2.status == 200

    # -- Etat : plus aucune cible, plus aucune publication pour l'ex-multi-capteur --
    state_sync = StateSynchronizer(app, bridge)
    assert state_sync.list_state_targets() == []

    bridge.publish_message.reset_mock()
    ok_state = await state_sync.handle_state_message(eq_id=553, cmd_id=5137, value="42")
    assert ok_state is False
    bridge.publish_message.assert_not_called()

    # -- Commande : le multi-switch supprimé ne doit plus rien router --
    cmd_sync = CommandSynchronizer(
        app=app,
        mqtt_bridge=bridge,
        jeedom_api_endpoint=_JEEDOM_API,
        jeedom_core_apikey="core-apikey",
    )
    cmd_sync._execute_exec_cmd = AsyncMock(return_value=True)
    ok_cmd = await cmd_sync.handle_command_message("jeedom2ha/628/5980/set", "ON")
    assert ok_cmd is False
    cmd_sync._execute_exec_cmd.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test 2 — dépublication via écart hors périmètre à l'intérieur de "publier"
# (branche `ecarts_resolus`, distincte de "supprimer") : mêmes assertions.
# ---------------------------------------------------------------------------


async def test_publier_out_of_scope_ecart_stops_state_streaming_and_command_routing(aiohttp_client, bridge):
    topology, mapping = _map_eq628()
    principal_decision = _published_switch_decision(mapping)
    for secondary in mapping.additional_mappings:
        _published_switch_decision(secondary)

    app = create_app(local_secret=_SECRET)
    app["mqtt_bridge"] = bridge
    app["topology"] = topology
    app["mappings"] = {628: mapping}
    app["publications"] = {628: principal_decision}
    app["eligibility"] = {628: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")}
    app["published_scope"] = {
        "global": {
            "counts": {"total": 1, "include": 0, "exclude": 1, "exceptions": 0},
            "effective_state": "exclude",
            "has_pending_home_assistant_changes": True,
        },
        "pieces": [
            {
                "object_id": 1,
                "object_name": "Energie",
                "counts": {"total": 1, "include": 0, "exclude": 1, "exceptions": 0},
                "home_perimetre": "Incluse",
                "has_pending_home_assistant_changes": True,
            },
        ],
        "equipements": [
            {
                "eq_id": 628,
                "object_id": 1,
                "name": "Pilotage priorisation solaire",
                "effective_state": "exclude",
                "decision_source": "equipement",
                "is_exception": True,
                "has_pending_home_assistant_changes": True,
            },
        ],
    }
    client = await aiohttp_client(app)

    publisher = MagicMock()
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ):
        resp = await client.post(
            "/action/execute",
            json={
                "action": "execute",
                "payload": {"intention": "publier", "portee": "equipement", "selection": [628]},
                "request_id": "publier-ecart-628",
                "timestamp": "2026-09-28T00:02:00Z",
            },
            headers={"X-Local-Secret": _SECRET},
        )
        assert resp.status == 200

    body = (await resp.json())["payload"]
    assert body["scope_reel"]["ecarts_resolus"] == 1

    state_sync = StateSynchronizer(app, bridge)
    assert state_sync.list_state_targets() == []

    cmd_sync = CommandSynchronizer(
        app=app,
        mqtt_bridge=bridge,
        jeedom_api_endpoint=_JEEDOM_API,
        jeedom_core_apikey="core-apikey",
    )
    cmd_sync._execute_exec_cmd = AsyncMock(return_value=True)
    ok_cmd = await cmd_sync.handle_command_message("jeedom2ha/628/5980/set", "ON")
    assert ok_cmd is False
    cmd_sync._execute_exec_cmd.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test 3 — "publier" réussi après un échec de publication précédent : le
# principal redevient routable. Depuis le fix P1-bis, les lecteurs I11 (state.py,
# command.py) résolvent le principal directement depuis app["publications"][eq_id]
# — plus jamais via mapping.publication_decision_ref, qui n'est plus repointée sur
# le chemin de succès "publier" (seule la decision runtime canonique change).
# ---------------------------------------------------------------------------


async def test_publier_success_after_prior_failure_restores_principal_command_routing(aiohttp_client, bridge):
    topology, mapping = _map_eq628()

    failed_decision = PublicationDecision(
        should_publish=False,
        reason="discovery_publish_failed",
        mapping_result=mapping,
        state_topic=mapping.reason_details["state_topic"],
        active_or_alive=False,
        discovery_published=False,
    )
    # Etat post-fix simule apres un premier "publier" en echec : la ref est deja
    # repointee sur la decision refusee (comme le fait _sync_publication_decision_refs).
    mapping.publication_decision_ref = failed_decision
    for secondary in mapping.additional_mappings:
        secondary.publication_decision_ref = PublicationDecision(
            should_publish=False,
            reason="discovery_publish_failed",
            mapping_result=secondary,
            state_topic=secondary.reason_details["state_topic"],
            active_or_alive=False,
            discovery_published=False,
        )

    app = create_app(local_secret=_SECRET)
    app["mqtt_bridge"] = bridge
    app["topology"] = topology
    app["mappings"] = {628: mapping}
    app["publications"] = {628: failed_decision}
    app["eligibility"] = {628: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["published_scope"] = {
        "global": {
            "counts": {"total": 1, "include": 1, "exclude": 0, "exceptions": 0},
            "effective_state": "include",
            "has_pending_home_assistant_changes": True,
        },
        "pieces": [
            {
                "object_id": 1,
                "object_name": "Energie",
                "counts": {"total": 1, "include": 1, "exclude": 0, "exceptions": 0},
                "home_perimetre": "Incluse",
                "has_pending_home_assistant_changes": True,
            },
        ],
        "equipements": [
            {
                "eq_id": 628,
                "object_id": 1,
                "name": "Pilotage priorisation solaire",
                "effective_state": "include",
                "decision_source": "global",
                "is_exception": False,
                "has_pending_home_assistant_changes": True,
            },
        ],
    }
    client = await aiohttp_client(app)

    publisher = MagicMock()
    publisher.publish_switch = AsyncMock(return_value=True)
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ):
        resp = await client.post(
            "/action/execute",
            json={
                "action": "execute",
                "payload": {"intention": "publier", "portee": "equipement", "selection": [628]},
                "request_id": "publier-retry-628",
                "timestamp": "2026-09-28T00:03:00Z",
            },
            headers={"X-Local-Secret": _SECRET},
        )
        assert resp.status == 200

    body = (await resp.json())["payload"]
    assert body["scope_reel"]["equipements_publies_ou_crees"] == 1

    # P1-bis (revue ClaudeBox round 2) : les lecteurs I11 résolvent désormais le
    # principal directement depuis app["publications"][eq_id] (la decision "runtime"),
    # jamais depuis mapping.publication_decision_ref — le fix ne repointe plus cette
    # ref sur le chemin de succès "publier". On vérifie donc le comportement
    # (app["publications"][628] vivante et routable), pas l'identité de la ref.
    assert app["publications"][628].should_publish is True
    assert app["publications"][628].active_or_alive is True

    cmd_sync = CommandSynchronizer(
        app=app,
        mqtt_bridge=bridge,
        jeedom_api_endpoint=_JEEDOM_API,
        jeedom_core_apikey="core-apikey",
    )
    cmd_sync._execute_exec_cmd = AsyncMock(return_value=True)
    ok_cmd = await cmd_sync.handle_command_message("jeedom2ha/628/5977/set", "ON")
    assert ok_cmd is True
    # "Filtration piscine" SWITCH_ON command id is 5978.
    cmd_sync._execute_exec_cmd.assert_awaited_once_with(5978, {})


# ---------------------------------------------------------------------------
# Test 4 — P2 : un secondaire dont la publication discovery échoue ne doit
# jamais être routé (active_or_alive remis à False avant la tentative).
# ---------------------------------------------------------------------------


async def test_p2_secondary_discovery_publish_failure_blocks_command_routing(bridge):
    _topology, mapping = _map_eq628()
    principal_decision = _published_switch_decision(mapping)

    secondary_decisions = [_published_switch_decision(secondary) for secondary in mapping.additional_mappings]
    failing_cmd_id = mapping.additional_mappings[0].reason_details["cmd_id"]

    async def _publish(candidate, _snapshot):
        return candidate.reason_details["cmd_id"] != failing_cmd_id

    publisher_registry = MagicMock()
    publisher_registry.publish = AsyncMock(side_effect=_publish)

    await http_server._publish_additional_sensors(
        primary_mapping=mapping,
        secondary_decisions=secondary_decisions,
        snapshot=_topology,
        publisher_registry=publisher_registry,
        mqtt_bridge=bridge,
        mapping_counters={},
    )

    failing_secondary = next(
        s for s in mapping.additional_mappings if s.reason_details["cmd_id"] == failing_cmd_id
    )
    assert failing_secondary.publication_decision_ref.active_or_alive is False

    cmd_sync = CommandSynchronizer(
        app={"publications": {628: principal_decision}},
        mqtt_bridge=bridge,
        jeedom_api_endpoint=_JEEDOM_API,
        jeedom_core_apikey="core-apikey",
    )
    cmd_sync._execute_exec_cmd = AsyncMock(return_value=True)

    ok_failed = await cmd_sync.handle_command_message(f"jeedom2ha/628/{failing_cmd_id}/set", "ON")
    assert ok_failed is False
    cmd_sync._execute_exec_cmd.assert_not_awaited()

    # Sanity : un secondaire dont la publication a réussi reste routable (pas
    # d'effet de bord "tout ou rien" provoqué par l'échec de l'autre).
    other_secondary = next(
        s for s in mapping.additional_mappings if s.reason_details["cmd_id"] != failing_cmd_id
    )
    other_topic = f"jeedom2ha/628/{other_secondary.reason_details['cmd_id']}/set"
    ok_other = await cmd_sync.handle_command_message(other_topic, "ON")
    assert ok_other is True


# ---------------------------------------------------------------------------
# P1-bis (revue ClaudeBox round 2, PR #174) — régression bloquante : un
# "supprimer" puis "publier" au même périmètre ne republiait, avant ce fix,
# que le PRINCIPAL. `_sync_publication_decision_refs` remettait le
# ``should_publish`` de chaque SECONDAIRE à False lors du "supprimer" ; comme
# `_secondary_publishable` lit ce même flag pour autoriser la republication,
# les secondaires restaient refusés indéfiniment — régression vs Story 11.2
# (PR #127, revue Codex P2 : "re-inclusion without full sync → entities
# missing on HA side"). Ces 3 tests pilotent le flux HTTP réel
# (/action/sync -> /action/execute) pour prouver le comportement de bout en
# bout, sans mocker DiscoveryPublisher (le bridge MagicMock suffit).
# ---------------------------------------------------------------------------


async def test_supprimer_puis_publier_eq553_republie_tous_les_secondaires(aiohttp_client, bridge):
    """Multi-capteur sans commande (eq553, 8 entités sensor) : "publier" après
    "supprimer" doit republier les 8 topics discovery (principal + 7
    secondaires) et les 8 cibles d'état doivent redevenir streamables.
    """
    app = create_app(local_secret=_SECRET)
    app["mqtt_bridge"] = bridge
    client = await aiohttp_client(app)

    with patch("transport.http_server.save_publications_cache"):
        resp = await client.post(
            "/action/sync",
            json=_sync_body([_msunpv_eq_payload()]),
            headers={"X-Local-Secret": _SECRET},
        )
        assert resp.status == 200

        supprimer_body = {
            "action": "execute",
            "payload": {"intention": "supprimer", "portee": "equipement", "selection": [553]},
            "request_id": "supprimer-553-r2",
            "timestamp": "2026-09-28T00:04:00Z",
        }
        resp_del = await client.post("/action/execute", json=supprimer_body, headers={"X-Local-Secret": _SECRET})
        assert resp_del.status == 200

        bridge.publish_message.reset_mock()

        publier_body = {
            "action": "execute",
            "payload": {"intention": "publier", "portee": "equipement", "selection": [553]},
            "request_id": "publier-553-r2",
            "timestamp": "2026-09-28T00:05:00Z",
        }
        resp_pub = await client.post("/action/execute", json=publier_body, headers={"X-Local-Secret": _SECRET})
        assert resp_pub.status == 200

    republished = {
        call.args[0]
        for call in bridge.publish_message.call_args_list
        if call.args[0].startswith("homeassistant/sensor/jeedom2ha_553_")
        and call.args[0].endswith("/config")
        and call.args[1]
    }
    expected = {f"homeassistant/sensor/jeedom2ha_553_{cmd_id}/config" for cmd_id in _MSUNPV_CMD_IDS}
    assert republished == expected, "les 8 topics discovery (principal + 7 secondaires) doivent être republiés"

    state_sync = StateSynchronizer(app, bridge)
    targets = state_sync.list_state_targets()
    assert len(targets) == 8, "les 8 cibles d'état (principal + 7 secondaires) doivent redevenir streamables"


async def test_supprimer_puis_publier_eq554_republie_switch_sensors_et_binary(aiohttp_client, bridge):
    """Multi-domaine (eq554, 1 switch + 12 sensors + 1 binary_sensor = 14
    entités) : "publier" après "supprimer" doit republier les 14 entités, pas
    seulement le switch principal.
    """
    app = create_app(local_secret=_SECRET)
    app["mqtt_bridge"] = bridge
    client = await aiohttp_client(app)

    with patch("transport.http_server.save_publications_cache"):
        resp = await client.post(
            "/action/sync",
            json=_sync_body([_eq554_eq_payload()]),
            headers={"X-Local-Secret": _SECRET},
        )
        assert resp.status == 200

        supprimer_body = {
            "action": "execute",
            "payload": {"intention": "supprimer", "portee": "equipement", "selection": [554]},
            "request_id": "supprimer-554-r2",
            "timestamp": "2026-09-28T00:06:00Z",
        }
        resp_del = await client.post("/action/execute", json=supprimer_body, headers={"X-Local-Secret": _SECRET})
        assert resp_del.status == 200

        bridge.publish_message.reset_mock()

        publier_body = {
            "action": "execute",
            "payload": {"intention": "publier", "portee": "equipement", "selection": [554]},
            "request_id": "publier-554-r2",
            "timestamp": "2026-09-28T00:07:00Z",
        }
        resp_pub = await client.post("/action/execute", json=publier_body, headers={"X-Local-Secret": _SECRET})
        assert resp_pub.status == 200

    def _republished_topics(prefix: str) -> set[str]:
        return {
            call.args[0]
            for call in bridge.publish_message.call_args_list
            if call.args[0].startswith(prefix) and call.args[0].endswith("/config") and call.args[1]
        }

    sensor_topics = _republished_topics("homeassistant/sensor/jeedom2ha_554_")
    binary_topics = _republished_topics("homeassistant/binary_sensor/jeedom2ha_554_")
    switch_topics = _republished_topics("homeassistant/switch/jeedom2ha_554")

    assert len(sensor_topics) == 12, "les 12 sensors secondaires doivent être republiés"
    assert binary_topics == {"homeassistant/binary_sensor/jeedom2ha_554_5510/config"}
    assert switch_topics == {"homeassistant/switch/jeedom2ha_554/config"}


async def test_diagnostics_echec_publication_eq553_apres_supprimer_identique_a_main(aiohttp_client, bridge):
    """P1-ter (revue ClaudeBox round 3, PR #174) : le diagnostic
    (``pipeline_step_visible``, ``traceability.decision_trace.reason_code``, et
    le garde-fou historique ``reason_code``/``status_code``/``statut`` pour un
    échec de publication) pour eq553 ne doit JAMAIS diverger de main à travers
    la séquence sync -> supprimer -> publier (réussi) -> publier (échoué,
    bridge en panne).

    Avant ce fix, ``_sync_publication_decision_refs`` (appelée par
    "supprimer") et le chemin d'échec de disponibilité locale de "publier"
    repointaient ``mapping.publication_decision_ref`` — source canonique
    étape 4 lue par ``/system/diagnostics`` via ``_compute_pipeline_step_visible``
    et ``traceability.decision_trace.reason_code`` — sur la décision runtime de
    l'action. Résultat : le diagnostic restait bloqué à l'étape 4 après
    "supprimer", y compris pour un équipement republié avec succès juste après
    (``pipeline_step_visible`` ne remontait jamais à 5). Sur main comme après ce
    fix, ``mapping.publication_decision_ref`` n'est écrit QUE par une synchro
    complète (``evaluate_equipment.py``) — jamais par une action — donc le
    diagnostic reste à l'étape 5 / ``reason_code="published"`` tout du long
    (limitation déjà présente sur main, pas introduite par ce fix ; les
    lecteurs I11 résolvent déjà le principal depuis ``publications[eq_id]``,
    pas depuis cette ref).
    """
    app = create_app(local_secret=_SECRET)
    app["mqtt_bridge"] = bridge
    client = await aiohttp_client(app)

    async def _diag_eq553() -> dict:
        resp_diag = await client.get("/system/diagnostics", headers={"X-Local-Secret": _SECRET})
        assert resp_diag.status == 200
        diag_body = await resp_diag.json()
        return next(eq for eq in diag_body["payload"]["equipments"] if eq["eq_id"] == 553)

    def _assert_step5_published(eq_diag: dict) -> None:
        assert eq_diag["pipeline_step_visible"] == 5
        assert eq_diag["traceability"]["decision_trace"]["reason_code"] == "published"

    with patch("transport.http_server.save_publications_cache"):
        resp = await client.post(
            "/action/sync",
            json=_sync_body([_msunpv_eq_payload()]),
            headers={"X-Local-Secret": _SECRET},
        )
        assert resp.status == 200
        _assert_step5_published(await _diag_eq553())

        supprimer_body = {
            "action": "execute",
            "payload": {"intention": "supprimer", "portee": "equipement", "selection": [553]},
            "request_id": "supprimer-553-diag",
            "timestamp": "2026-09-28T00:08:00Z",
        }
        resp_del = await client.post("/action/execute", json=supprimer_body, headers={"X-Local-Secret": _SECRET})
        assert resp_del.status == 200
        _assert_step5_published(await _diag_eq553())

        publier_ok_body = {
            "action": "execute",
            "payload": {"intention": "publier", "portee": "equipement", "selection": [553]},
            "request_id": "publier-553-diag-ok",
            "timestamp": "2026-09-28T00:08:30Z",
        }
        resp_pub_ok = await client.post("/action/execute", json=publier_ok_body, headers={"X-Local-Secret": _SECRET})
        assert resp_pub_ok.status == 200
        _assert_step5_published(await _diag_eq553())

        bridge.publish_message.return_value = False  # panne bridge simulée

        publier_body = {
            "action": "execute",
            "payload": {"intention": "publier", "portee": "equipement", "selection": [553]},
            "request_id": "publier-553-diag",
            "timestamp": "2026-09-28T00:09:00Z",
        }
        resp_pub = await client.post("/action/execute", json=publier_body, headers={"X-Local-Secret": _SECRET})
        assert resp_pub.status == 200

    eq553_diag = await _diag_eq553()
    _assert_step5_published(eq553_diag)
    assert eq553_diag["reason_code"] == "discovery_publish_failed"
    assert eq553_diag["status_code"] == "infra_incident"
    assert eq553_diag["statut"] == "non_publie"
