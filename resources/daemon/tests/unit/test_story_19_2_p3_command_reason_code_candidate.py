"""Story 19.2 — P3 (revue ClaudeBox, commit 3a408db) : les reason codes de
diagnostic de ``_resolve_runtime_target`` doivent refléter la décision du
CANDIDAT (principal ou secondaire) qui expose réellement le topic ciblé,
jamais inconditionnellement celle du principal.

Avant le fix, ``found_publishable``/``found_alive`` n'étaient dérivés QUE de
la décision du principal, avant même la boucle sur les candidats. Un
principal refusé (``should_publish=False``) dont un secondaire ciblé était
publié-mais-non-alive produisait donc le mauvais diagnostic
``entity_not_published`` (hérité du principal) au lieu de ``entity_not_alive``
(l'état réel du secondaire visé) — la commande était bien refusée dans les
deux cas (le routage per-candidate, lui, était déjà correct), mais le
diagnostic renvoyé à l'appelant/aux logs était trompeur.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from mapping.registry import MapperRegistry
from models.mapping import PublicationDecision
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from sync.command import CommandSynchronizer

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


def _map_eq628():
    topology = TopologySnapshot(
        timestamp="2026-09-28T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Energie")},
        eq_logics={
            628: JeedomEqLogic(
                id=628,
                name="Pilotage priorisation solaire",
                object_id=1,
                eq_type_name="virtual",
                cmds=[JeedomCmd(id=c, name=n, type=t, sub_type=st, generic_type=g) for c, n, t, st, g in _EQ628_CMDS],
            )
        },
    )
    mapping = MapperRegistry().map(topology.eq_logics[628], topology)
    assert mapping is not None and mapping.additional_mappings, "eq628 fixture drifted: expected secondaries"
    return mapping


@pytest.mark.asyncio
async def test_refused_principal_with_published_not_alive_secondary_reports_entity_not_alive(caplog):
    """Cas exact du bug P3 : principal refusé (excluded), secondaire ciblé
    publié mais non alive (ex : panne MQTT ponctuelle post-discovery) — le
    reason code doit être celui du secondaire visé, pas celui du principal."""
    mapping = _map_eq628()
    secondary = next(s for s in mapping.additional_mappings if s.reason_details["cmd_id"] == 5980)

    refused_principal = PublicationDecision(
        should_publish=False,
        reason="excluded",
        mapping_result=mapping,
        state_topic=mapping.reason_details["state_topic"],
        active_or_alive=False,
        discovery_published=False,
    )
    mapping.publication_decision_ref = refused_principal

    published_not_alive_secondary = PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=secondary,
        state_topic=secondary.reason_details["state_topic"],
        active_or_alive=False,
        discovery_published=True,
    )
    secondary.publication_decision_ref = published_not_alive_secondary

    app = {"publications": {628: refused_principal}}
    bridge = MagicMock()
    bridge.is_connected = True

    sync = CommandSynchronizer(
        app=app,
        mqtt_bridge=bridge,
        jeedom_api_endpoint="http://jeedom.test/core/api/jeeApi.php",
        jeedom_core_apikey="core-apikey",
    )
    sync._execute_exec_cmd = AsyncMock(return_value=True)

    with caplog.at_level("INFO"):
        ok = await sync.handle_command_message(secondary.reason_details["command_topic"], "ON")

    assert ok is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "reason_code=entity_not_alive" in caplog.text
    assert "reason_code=entity_not_published" not in caplog.text
