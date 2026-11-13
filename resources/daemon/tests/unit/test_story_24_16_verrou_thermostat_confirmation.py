"""Story 24.16 — verrou de thermostat confirmé par l'état réel (identifiants synthétiques).

Constat de recette (24-15, AC12) : l'ordre sur l'interrupteur « Verrouillage » journalisait
``optimistic_controlled`` alors que son état ``THERMOSTAT_LOCK`` était streamé. Forme de
production reproduite ici : climate principal + interrupteur de verrou secondaire, décisions
issues d'une vraie synchro (``/action/sync``), synchroniseur d'état actif.
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

import transport.http_server as http_server
from mapping.registry import MapperRegistry
from models.mapping import PublicationDecision, SwitchCapabilities, MappingResult
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from sync.command import CommandSynchronizer, CommandTranslation
from sync.state import StateSynchronizer

# Thermostat du corpus doré (identifiants synthétiques).
EQ = 11000
LOCK = 110009
SET_LOCK = 110010
SET_UNLOCK = 110012
LOCK_SET_TOPIC = f"jeedom2ha/{EQ}/{LOCK}/set"
LOCK_STATE_TOPIC = f"jeedom2ha/{EQ}/{LOCK}/state"

_GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden_corpus" / "sync_payload.json"


class _Bridge:
    def __init__(self):
        self.is_connected = True
        self.published = []

    def publish_message(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return True


def _payload(lock_value="0"):
    payload = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    for eq in payload["eq_logics"]:
        if eq["id"] != EQ:
            continue
        for cmd in eq["cmds"]:
            if cmd["id"] == LOCK:
                cmd["current_value"] = lock_value
    return payload


async def _synced_app(aiohttp_client, lock_value="0", with_state_sync=True):
    """Vraie synchro : les décisions (principal ET secondaires) viennent du pipeline réel."""
    app = http_server.create_app(local_secret="s")
    bridge = _Bridge()
    app["mqtt_bridge"] = bridge
    if with_state_sync:
        app["state_synchronizer"] = StateSynchronizer(app, bridge)
    cli = await aiohttp_client(app)
    body = {"action": "sync", "payload": _payload(lock_value), "request_id": "r",
            "timestamp": "2026-11-13T00:00:00Z"}
    resp = await cli.post("/action/sync", json=body, headers={"X-Local-Secret": "s"})
    assert resp.status == 200
    return app, bridge


def _cmd_sync(app):
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    sync = CommandSynchronizer(app=app, mqtt_bridge=bridge,
                               jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
                               jeedom_core_apikey="core-apikey")
    sync._execute_exec_cmd = AsyncMock(return_value=True)
    return sync, bridge


def _lock_switch(app):
    mapping = app["publications"][EQ].mapping_result
    assert mapping.ha_entity_type == "climate"
    switches = [m for m in mapping.additional_mappings or []
                if (m.reason_details or {}).get("thermostat_lock")]
    assert len(switches) == 1
    return mapping, switches[0]


def _policies(caplog):
    return [r.getMessage() for r in caplog.records
            if "action=select_confirmation_policy" in r.getMessage()]


# --- AC1 : forme de production ------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("payload,cmd_id", [("ON", SET_LOCK), ("OFF", SET_UNLOCK)])
async def test_production_shape_lock_order_is_confirmed_by_the_real_state(
        aiohttp_client, caplog, payload, cmd_id):
    app, _bridge = await _synced_app(aiohttp_client)
    _climate, switch = _lock_switch(app)
    # Le constat : la décision du secondaire issue de la synchro ne porte pas de state_topic.
    assert switch.publication_decision_ref is not None
    assert switch.publication_decision_ref.should_publish is True
    sync, cmd_bridge = _cmd_sync(app)
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(LOCK_SET_TOPIC, payload) is True
    sync._execute_exec_cmd.assert_awaited_once_with(cmd_id, {})
    policies = _policies(caplog)
    assert len(policies) == 1
    assert "reason_code=real_state_confirmation" in policies[0]
    assert "optimistic_controlled" not in caplog.text
    # AC2 : aucun message publié sur le topic d'état après l'ordre.
    cmd_bridge.publish_message.assert_not_called()


@pytest.mark.asyncio
async def test_production_shape_lock_state_is_streamed_on_its_own_topic(aiohttp_client):
    app, bridge = await _synced_app(aiohttp_client, lock_value="1")
    assert (LOCK_STATE_TOPIC, "ON", 1, True) in bridge.published
    state_sync = app["state_synchronizer"]
    bridge.published.clear()
    assert await state_sync.handle_state_message(EQ, LOCK, "0") is True
    assert bridge.published == [(LOCK_STATE_TOPIC, "OFF", 1, True)]


# --- AC2 : jamais d'état supposé ----------------------------------------------------------

@pytest.mark.asyncio
async def test_without_state_synchronizer_the_lock_is_stateless(aiohttp_client, caplog):
    app, _bridge = await _synced_app(aiohttp_client, with_state_sync=False)
    sync, cmd_bridge = _cmd_sync(app)
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(LOCK_SET_TOPIC, "ON") is True
    policies = _policies(caplog)
    assert len(policies) == 1 and "reason_code=stateless" in policies[0]
    assert "optimistic_controlled" not in caplog.text
    cmd_bridge.publish_message.assert_not_called()


@pytest.mark.asyncio
async def test_without_lock_info_the_lock_is_stateless(aiohttp_client):
    app, _bridge = await _synced_app(aiohttp_client)
    _climate, switch = _lock_switch(app)
    sync, _cmd_bridge = _cmd_sync(app)
    bare = copy.copy(switch)
    bare.commands = {k: v for k, v in switch.commands.items() if k != "THERMOSTAT_LOCK"}
    translation = CommandTranslation(cmd_id=SET_LOCK, options={}, command_family="on_off")
    assert sync._select_confirmation_policy(bare, switch.publication_decision_ref,
                                            translation) == "stateless"


# --- AC3 : valeur vide ou non reconnue ----------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["", "   ", "abc", "2"])
async def test_empty_or_unknown_lock_value_publishes_nothing(aiohttp_client, value):
    app, bridge = await _synced_app(aiohttp_client, lock_value=value)
    assert [p for p in bridge.published if p[0] == LOCK_STATE_TOPIC] == []
    bridge.published.clear()
    assert await app["state_synchronizer"].handle_state_message(EQ, LOCK, value) is False
    assert bridge.published == []


@pytest.mark.asyncio
@pytest.mark.parametrize("value,expected", [("1", "ON"), ("0", "OFF"), ("true", "ON"),
                                            ("off", "OFF")])
async def test_known_lock_values_are_streamed(aiohttp_client, value, expected):
    app, bridge = await _synced_app(aiohttp_client)
    bridge.published.clear()
    assert await app["state_synchronizer"].handle_state_message(EQ, LOCK, value) is True
    assert bridge.published == [(LOCK_STATE_TOPIC, expected, 1, True)]


# --- AC4 : ordres inchangés ---------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ["TOGGLE", "", "1", "verrou"])
async def test_invalid_lock_payload_is_refused(aiohttp_client, caplog, payload):
    app, _bridge = await _synced_app(aiohttp_client)
    sync, _cmd_bridge = _cmd_sync(app)
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(LOCK_SET_TOPIC, payload) is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "reason_code=invalid_command_payload" in caplog.text


@pytest.mark.asyncio
async def test_missing_lock_order_is_refused(aiohttp_client, caplog):
    app, _bridge = await _synced_app(aiohttp_client)
    _climate, switch = _lock_switch(app)
    switch.commands = {k: v for k, v in switch.commands.items() if k != "THERMOSTAT_SET_LOCK"}
    sync, _cmd_bridge = _cmd_sync(app)
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(LOCK_SET_TOPIC, "ON") is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "reason_code=missing_action_command" in caplog.text


# --- AC5 : les autres switch gardent leur politique ---------------------------------------

def _plain_switch(state_cmd: bool):
    eq_id = 16000
    cmds = [JeedomCmd(id=160002, name="On", generic_type="ENERGY_ON", type="action", sub_type="other"),
            JeedomCmd(id=160003, name="Off", generic_type="ENERGY_OFF", type="action", sub_type="other")]
    if state_cmd:
        cmds.insert(0, JeedomCmd(id=160001, name="Etat", generic_type="ENERGY_STATE", type="info",
                                 sub_type="binary", current_value="0"))
    eq = JeedomEqLogic(id=eq_id, name="Prise", object_id=1, eq_type_name="virtual", cmds=cmds)
    snapshot = TopologySnapshot(timestamp="2026-11-13T00:00:00+00:00",
                                objects={1: JeedomObject(id=1, name="Piece")},
                                eq_logics={eq_id: eq})
    mapping = MapperRegistry().map(eq, snapshot)
    assert mapping is not None and mapping.ha_entity_type == "switch"
    decision = PublicationDecision(
        should_publish=True, reason="sure", mapping_result=mapping,
        state_topic=http_server._resolve_state_topic(mapping),
        active_or_alive=True, discovery_published=True,
    )
    return mapping, decision


@pytest.mark.parametrize("state_cmd,expected", [(False, "optimistic_controlled"),
                                                (True, "real_state_confirmation")])
def test_ordinary_switch_policy_is_unchanged(state_cmd, expected):
    mapping, decision = _plain_switch(state_cmd)
    state_sync = StateSynchronizer(app={}, mqtt_bridge=_Bridge())
    sync, _bridge = _cmd_sync({"publications": {mapping.jeedom_eq_id: decision},
                               "state_synchronizer": state_sync})
    translation = CommandTranslation(cmd_id=160002, options={}, command_family="on_off",
                                     optimistic_state_payload="ON")
    assert sync._select_confirmation_policy(mapping, decision, translation) == expected


def test_secondary_ordinary_switch_without_decision_topic_is_unchanged():
    """Un switch ordinaire dont la décision n'a pas de state_topic garde sa politique actuelle."""
    mapping = MappingResult(
        ha_entity_type="switch", confidence="sure", reason_code="switch_secondary",
        jeedom_eq_id=16001, ha_unique_id="u", ha_name="n",
        commands={"ENERGY_STATE": JeedomCmd(id=1, name="e", generic_type="ENERGY_STATE",
                                            type="info", sub_type="binary")},
        capabilities=SwitchCapabilities(has_on_off=True, has_state=True),
        reason_details={"state_topic": "jeedom2ha/16001/1/state"},
    )
    decision = PublicationDecision(should_publish=True, reason="sure", mapping_result=mapping)
    state_sync = StateSynchronizer(app={}, mqtt_bridge=_Bridge())
    sync, _bridge = _cmd_sync({"publications": {}, "state_synchronizer": state_sync})
    translation = CommandTranslation(cmd_id=2, options={}, command_family="on_off",
                                     optimistic_state_payload="ON")
    assert sync._select_confirmation_policy(mapping, decision, translation) == \
        "optimistic_controlled"
