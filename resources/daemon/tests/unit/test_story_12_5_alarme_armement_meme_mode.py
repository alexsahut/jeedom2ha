"""Story 12.5 (correctif FR49) — armer dans le mode courant ; plus d'ancien mode affiché à l'armement.

Écart 1 : un armement dont le mode visé est déjà le mode courant de l'alarme désarmée exécute la
commande d'activation (le cœur Jeedom ignore une commande de mode dont l'info liée est déjà dans
l'état visé) ; déjà armée dans ce mode : rien ; autres cas : inchangé.
Écart 2 : les changements des infos d'une alarme sont regroupés sur une courte fenêtre avant
publication (une seule publication, état final).

Identifiants et libellés fictifs (CC-48), réutilisés de la story 12.4.
"""
from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock

import pytest

from mapping.alarm_control_panel import alarm_enable_command
from models.mapping import MappingResult, PublicationDecision, SensorCapabilities
from models.topology import JeedomCmd
from sync import state as state_module
from .test_story_12_4_alarme_etat_mode import (
    ARMED, ENABLE, EQ, MODE, MODE_A, MODE_B, MODE_C, VIRTUAL,
    _Bridge, _alarm_eq, _cmd_sync, _map, _state_sync, _virtual_eq,
)

TOPIC = f"jeedom2ha/{EQ}/alarm/set"
STATE_TOPIC = f"jeedom2ha/{EQ}/alarm/state"
# Libellés de la story 12.4 : Présent « Mode Jour » (MODE_C), Absent « mode   total » (MODE_A),
# Nuit « mode nuit » (MODE_B).


def _reader(values):
    """Lecture fraîche simulée : ``values`` = {cmd_id: valeur}, absent = lecture en échec."""
    calls = []

    async def read(cmd_id):
        calls.append(cmd_id)
        if cmd_id not in values:
            return False, None
        return True, values[cmd_id]

    read.calls = calls
    return read


def _sync_with_reads(values, eq=None):
    sync, bridge = _cmd_sync(_map(eq if eq is not None else _alarm_eq()))
    sync._read_info_value = _reader(values)
    return sync, bridge


# --- Écart 1 -----------------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("payload,mode_value", [
    ("ARM_HOME", "Mode Jour"), ("ARM_AWAY", "MODE TOTAL"), ("ARM_NIGHT", "  mode   nuit ")])
async def test_same_mode_disarmed_runs_the_enable_command(payload, mode_value, caplog):
    sync, bridge = _sync_with_reads({MODE: mode_value, ENABLE: "0"})
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(TOPIC, payload) is True
    sync._execute_exec_cmd.assert_awaited_once_with(ARMED, {})
    bridge.publish_message.assert_not_called()  # jamais d'état supposé
    assert "alarm_same_mode_enable" in caplog.text
    # aucun libellé de mode dans le journal
    assert "Jour" not in caplog.text and "nuit" not in caplog.text and "total" not in caplog.text.lower()


@pytest.mark.asyncio
async def test_same_mode_already_armed_does_nothing(caplog):
    sync, bridge = _sync_with_reads({MODE: "Mode Jour", ENABLE: "1"})
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(TOPIC, "ARM_HOME") is True
    sync._execute_exec_cmd.assert_not_awaited()
    bridge.publish_message.assert_not_called()
    assert "alarm_already_armed_in_mode" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("enable", ["0", "1"])
async def test_other_mode_sends_the_mode_command_unchanged(enable):
    sync, _bridge = _sync_with_reads({MODE: "mode nuit", ENABLE: enable})
    assert await sync.handle_command_message(TOPIC, "ARM_HOME") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_C, {})
    assert sync._read_info_value.calls == [MODE]  # Actif inutile quand le mode diffère


@pytest.mark.asyncio
@pytest.mark.parametrize("mode_value", ["mode inconnu", "", "   ", None])
async def test_unknown_or_null_mode_sends_the_mode_command_unchanged(mode_value):
    sync, _bridge = _sync_with_reads({MODE: mode_value, ENABLE: "0"})
    assert await sync.handle_command_message(TOPIC, "ARM_AWAY") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_A, {})


@pytest.mark.asyncio
async def test_mode_read_failure_sends_the_mode_command_unchanged():
    sync, _bridge = _sync_with_reads({ENABLE: "0"})
    assert await sync.handle_command_message(TOPIC, "ARM_NIGHT") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_B, {})


@pytest.mark.asyncio
@pytest.mark.parametrize("values", [
    {MODE: "Mode Jour"},                  # Actif : lecture en échec
    {MODE: "Mode Jour", ENABLE: None},    # Actif null
    {MODE: "Mode Jour", ENABLE: "abc"},   # Actif illisible
])
async def test_unreadable_enable_sends_the_mode_command_unchanged(values):
    sync, _bridge = _sync_with_reads(values)
    assert await sync.handle_command_message(TOPIC, "ARM_HOME") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_C, {})


@pytest.mark.asyncio
async def test_read_exception_sends_the_mode_command_unchanged():
    sync, _bridge = _cmd_sync(_map(_alarm_eq()))
    sync._read_info_value = AsyncMock(side_effect=RuntimeError("boom"))
    assert await sync.handle_command_message(TOPIC, "ARM_HOME") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_C, {})


@pytest.mark.asyncio
async def test_never_decides_on_a_stored_value():
    """Lecture fraîche en échec : la valeur de topologie (même mode, désarmée) n'est pas utilisée."""
    sync, _bridge = _sync_with_reads({}, eq=_alarm_eq(enable="0", mode="Mode Jour"))
    assert await sync.handle_command_message(TOPIC, "ARM_HOME") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_C, {})


@pytest.mark.asyncio
async def test_same_mode_disarmed_without_enable_command_sends_the_mode_command_with_a_warning(caplog):
    eq = _alarm_eq()
    eq.cmds = [c for c in eq.cmds if c.id != ARMED]
    sync, _bridge = _sync_with_reads({MODE: "Mode Jour", ENABLE: "0"}, eq=eq)
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(TOPIC, "ARM_HOME") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_C, {})
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("alarm_same_mode_without_enable_command" in r.getMessage() for r in warnings)


@pytest.mark.asyncio
async def test_without_mode_configuration_nothing_is_read():
    sync, _bridge = _sync_with_reads({MODE: "Mode Jour", ENABLE: "0"}, eq=_alarm_eq(config={}))
    assert await sync.handle_command_message(TOPIC, "ARM_AWAY") is True
    sync._execute_exec_cmd.assert_awaited_once_with(ARMED, {})
    assert sync._read_info_value.calls == []


@pytest.mark.asyncio
async def test_without_mode_info_nothing_is_read():
    eq = _alarm_eq()
    eq.cmds = [c for c in eq.cmds if c.id != MODE]
    sync, _bridge = _sync_with_reads({ENABLE: "0"}, eq=eq)
    assert await sync.handle_command_message(TOPIC, "ARM_HOME") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_C, {})
    assert sync._read_info_value.calls == []


@pytest.mark.asyncio
async def test_disarm_is_unchanged_and_reads_nothing():
    sync, _bridge = _sync_with_reads({MODE: "Mode Jour", ENABLE: "1"})
    assert await sync.handle_command_message(TOPIC, "DISARM") is True
    assert sync._read_info_value.calls == []


@pytest.mark.asyncio
async def test_same_mode_enable_failure_is_reported():
    sync, _bridge = _sync_with_reads({MODE: "Mode Jour", ENABLE: "0"})
    sync._execute_exec_cmd = AsyncMock(return_value=False)
    assert await sync.handle_command_message(TOPIC, "ARM_HOME") is False
    sync._execute_exec_cmd.assert_awaited_once_with(ARMED, {})


@pytest.mark.asyncio
async def test_generic_virtual_is_unchanged():
    sync, _bridge = _cmd_sync(_map(_virtual_eq()))
    sync._read_info_value = _reader({})
    assert await sync.handle_command_message(f"jeedom2ha/{VIRTUAL}/alarm/set", "ARM_AWAY") is True
    sync._execute_exec_cmd.assert_awaited_once_with(72003, {})
    assert sync._read_info_value.calls == []


def test_alarm_enable_command_helper():
    mapping = _map(_alarm_eq())
    assert alarm_enable_command(mapping.commands).id == ARMED
    assert alarm_enable_command(_map(_virtual_eq()).commands).id == 72003
    assert alarm_enable_command({}) is None
    info = JeedomCmd(id=1, name="x", generic_type="ALARM_ARMED", type="info", sub_type="binary")
    assert alarm_enable_command({"ALARM_ARMED": info}) is None


# --- Écart 2 : regroupement -------------------------------------------------------------------

def _coalescing_sync(window=0.05, eq=None):
    mapping = _map(eq if eq is not None else _alarm_eq(enable="0", mode="mode total"))
    sync, bridge, decision = _state_sync(mapping)
    sync.alarm_coalesce_s = window
    return sync, bridge, decision


def test_default_window_is_short_and_positive():
    assert 0 < state_module.ALARM_STATE_COALESCE_S <= 0.5


@pytest.mark.asyncio
async def test_arming_publishes_only_the_final_state():
    sync, bridge, _decision = _coalescing_sync()
    assert await sync.handle_state_message(EQ, ENABLE, "1") is True
    await asyncio.sleep(0.01)
    assert await sync.handle_state_message(EQ, MODE, "Mode Jour") is True
    assert bridge.published == []  # rien avant la fin de la fenêtre
    await asyncio.sleep(0.1)
    assert [(t, p, r) for t, p, _q, r in bridge.published] == [(STATE_TOPIC, "armed_home", True)]


@pytest.mark.asyncio
async def test_window_is_fixed_from_the_first_event():
    sync, bridge, _decision = _coalescing_sync(window=0.06)
    await sync.handle_state_message(EQ, ENABLE, "1")
    await asyncio.sleep(0.04)
    await sync.handle_state_message(EQ, MODE, "Mode Jour")
    await asyncio.sleep(0.04)  # 0,08 s après le premier événement : publié, pas reporté
    assert [p[1] for p in bridge.published] == ["armed_home"]
    await sync.handle_state_message(EQ, ENABLE, "0")
    await asyncio.sleep(0.1)
    assert [p[1] for p in bridge.published] == ["armed_home", "disarmed"]


@pytest.mark.asyncio
async def test_other_types_are_published_immediately():
    sensor_bridge = _Bridge()
    sync, _bridge, _decision = _coalescing_sync()
    sync._mqtt_bridge = sensor_bridge
    # un capteur ordinaire : la fenêtre ne s'applique pas (chemin d'avant)
    cmd = JeedomCmd(id=99001, name="T", generic_type="TEMPERATURE", type="info", sub_type="numeric")
    mapping = MappingResult(ha_entity_type="sensor", confidence="sure", reason_code="x", jeedom_eq_id=99,
                            ha_unique_id="jeedom2ha_eq_99", ha_name="T", commands={"TEMPERATURE": cmd},
                            capabilities=SensorCapabilities())
    sensor_decision = PublicationDecision(should_publish=True, reason="sure", mapping_result=mapping,
                                          state_topic="jeedom2ha/99/state", active_or_alive=True,
                                          discovery_published=True)
    mapping.publication_decision_ref = sensor_decision
    sync._app["publications"][99] = sensor_decision
    assert await sync.handle_state_message(99, 99001, "21.5") is True
    assert [(t, p) for t, p, _q, _r in sensor_bridge.published] == [("jeedom2ha/99/state", "21.5")]


@pytest.mark.asyncio
async def test_failed_publication_is_still_a_warning(caplog):
    class _Failing(_Bridge):
        def publish_message(self, topic, payload, qos=0, retain=False):
            super().publish_message(topic, payload, qos, retain)
            return False

    sync, _bridge, _decision = _coalescing_sync()
    sync._mqtt_bridge = _Failing()
    with caplog.at_level(logging.INFO):
        await sync.handle_state_message(EQ, ENABLE, "1")
        await asyncio.sleep(0.1)
    failures = [r for r in caplog.records if r.levelno == logging.WARNING
                and "mqtt_publish_failed" in r.getMessage()]
    assert len(failures) == 1 and STATE_TOPIC in failures[0].getMessage()


@pytest.mark.asyncio
async def test_an_exception_at_flush_is_a_warning(caplog):
    class _Raising(_Bridge):
        def publish_message(self, topic, payload, qos=0, retain=False):
            raise RuntimeError("broker")

    sync, _bridge, _decision = _coalescing_sync()
    sync._mqtt_bridge = _Raising()
    with caplog.at_level(logging.INFO):
        await sync.handle_state_message(EQ, ENABLE, "1")
        await asyncio.sleep(0.1)
    assert any(r.levelno == logging.WARNING and "mqtt_publish_failed" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_broker_down_at_flush_publishes_nothing(caplog):
    sync, bridge, _decision = _coalescing_sync()
    await sync.handle_state_message(EQ, ENABLE, "1")
    bridge.is_connected = False
    with caplog.at_level(logging.INFO):
        await asyncio.sleep(0.1)
    assert bridge.published == []
    assert "mqtt_unavailable" in caplog.text


@pytest.mark.asyncio
async def test_unpublished_meanwhile_publishes_nothing():
    sync, bridge, _decision = _coalescing_sync()
    await sync.handle_state_message(EQ, ENABLE, "1")
    sync._app["publications"].clear()
    await asyncio.sleep(0.1)
    assert bridge.published == []


@pytest.mark.asyncio
async def test_unknown_is_still_published_once():
    sync, bridge, _decision = _coalescing_sync()
    await sync.handle_state_message(EQ, ENABLE, "1")
    await asyncio.sleep(0.1)
    await sync.handle_state_message(EQ, ENABLE, None)
    await asyncio.sleep(0.1)
    await sync.handle_state_message(EQ, MODE, "mode nuit")
    await asyncio.sleep(0.1)
    assert [p[1] for p in bridge.published] == ["armed_away", "None"]


@pytest.mark.asyncio
async def test_shutdown_flushes_the_pending_state_now():
    sync, bridge, _decision = _coalescing_sync(window=5.0)
    await sync.handle_state_message(EQ, ENABLE, "1")
    await sync.handle_state_message(EQ, MODE, "mode nuit")
    sync.flush_pending_states()
    assert [p[1] for p in bridge.published] == ["armed_night"]
    await asyncio.sleep(0.01)
    sync.flush_pending_states()  # plus rien en attente
    assert [p[1] for p in bridge.published] == ["armed_night"]


@pytest.mark.asyncio
async def test_zero_window_keeps_the_immediate_behaviour():
    sync, bridge, _decision = _coalescing_sync(window=0)
    await sync.handle_state_message(EQ, ENABLE, "1")
    await sync.handle_state_message(EQ, MODE, "Mode Jour")
    assert [p[1] for p in bridge.published] == ["armed_away", "armed_home"]


def test_main_flushes_pending_states_at_shutdown():
    import inspect
    import main
    source = inspect.getsource(main)
    assert "flush_pending_states()" in source
