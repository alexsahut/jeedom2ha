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
# principal redevient routable (le fix P1 rafraîchit mapping.publication_decision_ref
# aussi sur le chemin de succès, pas seulement sur les chemins d'échec).
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

    # La ref du principal a bien été rafraîchie (pas seulement publications[eq_id]).
    assert mapping.publication_decision_ref is app["publications"][628]
    assert mapping.publication_decision_ref.should_publish is True
    assert mapping.publication_decision_ref.active_or_alive is True

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
