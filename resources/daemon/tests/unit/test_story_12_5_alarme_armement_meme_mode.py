"""Story 12.5 (correctif FR49) — armer dans le mode courant ; plus d'ancien mode affiché à l'armement.

Écart 1 : un armement dont le mode visé est déjà le mode courant de l'alarme désarmée exécute la
commande d'activation (le cœur Jeedom ignore une commande de mode dont l'info liée est déjà dans
l'état visé) ; déjà armée dans ce mode : rien ; autres cas : inchangé. Revue I1 : seulement si le
libellé de la clé SetMode* est aussi le nom de la commande de mode visée.
Décision du porteur du projet : aucun armement d'une alarme déclenchée ou en délai d'entrée (Statut
ou Immédiat relus à 1), ni quand cette relecture échoue.
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
    ARMED, ENABLE, EQ, IMMEDIATE, MODE, MODE_A, MODE_B, MODE_C, STATUS, VIRTUAL,
    _Bridge, _alarm_eq, _cmd_sync, _map, _snapshot, _state_sync, _virtual_eq,
)

TOPIC = f"jeedom2ha/{EQ}/alarm/set"
STATE_TOPIC = f"jeedom2ha/{EQ}/alarm/state"
# Libellés de la story 12.4 : Présent « Mode Jour » (MODE_C), Absent « mode   total » (MODE_A),
# Nuit « mode nuit » (MODE_B). Comme dans le plugin alarm, chaque commande de mode porte le nom
# de son mode (casse différente exprès : la comparaison est normalisée).
MODE_NAMES = {MODE_C: "Mode Jour", MODE_A: "Mode Total", MODE_B: "Mode Nuit"}
# Statut et Immédiat relus à 0 : armement permis (sauf valeur donnée par le test).
SAFE = {STATUS: "0", IMMEDIATE: "0"}


def _named_eq(names=None, **kwargs):
    eq = _alarm_eq(**kwargs)
    for cmd in eq.cmds:
        if cmd.id in (names if names is not None else MODE_NAMES):
            cmd.name = (names if names is not None else MODE_NAMES)[cmd.id]
    return eq


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


def _sync_with_reads(values, eq=None, safe=True):
    sync, bridge = _cmd_sync(_map(eq if eq is not None else _named_eq()))
    sync._read_info_value = _reader({**SAFE, **values} if safe else dict(values))
    return sync, bridge


def _mode_calls(sync):
    """Lectures faites après le contrôle Statut / Immédiat."""
    return [c for c in sync._read_info_value.calls if c not in (STATUS, IMMEDIATE)]


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
    assert _mode_calls(sync) == [MODE]  # Actif inutile quand le mode diffère


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
async def test_mode_read_exception_sends_the_mode_command_unchanged():
    sync, _bridge = _cmd_sync(_map(_named_eq()))

    async def read(cmd_id):
        if cmd_id in SAFE:
            return True, SAFE[cmd_id]
        raise RuntimeError("boom")

    sync._read_info_value = read
    assert await sync.handle_command_message(TOPIC, "ARM_HOME") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_C, {})


@pytest.mark.asyncio
async def test_never_decides_on_a_stored_value():
    """Lecture fraîche en échec : la valeur de topologie (même mode, désarmée) n'est pas utilisée."""
    sync, _bridge = _sync_with_reads({}, eq=_named_eq(enable="0", mode="Mode Jour"))
    assert await sync.handle_command_message(TOPIC, "ARM_HOME") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_C, {})


@pytest.mark.asyncio
async def test_same_mode_disarmed_without_enable_command_sends_the_mode_command_with_a_warning(caplog):
    eq = _named_eq()
    eq.cmds = [c for c in eq.cmds if c.id != ARMED]
    sync, _bridge = _sync_with_reads({MODE: "Mode Jour", ENABLE: "0"}, eq=eq)
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(TOPIC, "ARM_HOME") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_C, {})
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("alarm_same_mode_without_enable_command" in r.getMessage() for r in warnings)


@pytest.mark.asyncio
@pytest.mark.parametrize("names,why", [
    ({MODE_C: "Mode Total", MODE_A: "Mode Jour", MODE_B: "Mode Nuit"}, "clé Présent sur la commande d'un autre mode"),
    ({MODE_C: "Cmd sans rapport", MODE_A: "Mode Total", MODE_B: "Mode Nuit"}, "nom de commande sans rapport"),
])
async def test_inconsistent_homebridge_configuration_keeps_the_12_4_behaviour(names, why, caplog):
    """Revue I1 — le libellé de SetModePresent (« Mode Jour ») n'est pas le nom de la commande visée."""
    sync, _bridge = _sync_with_reads({MODE: "Mode Jour", ENABLE: "0"}, eq=_named_eq(names=names))
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(TOPIC, "ARM_HOME") is True, why
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_C, {})
    assert _mode_calls(sync) == []  # incohérence vue avant toute lecture du mode
    # revue m4 : repli signalé en INFO, sans libellé ni nom de commande
    mismatch = [r for r in caplog.records if "alarm_same_mode_config_mismatch" in r.getMessage()]
    assert len(mismatch) == 1 and mismatch[0].levelno == logging.INFO
    assert "Jour" not in caplog.text and "Total" not in caplog.text and "rapport" not in caplog.text


@pytest.mark.asyncio
async def test_consistent_configuration_logs_no_mismatch(caplog):
    sync, _bridge = _sync_with_reads({MODE: "mode nuit", ENABLE: "0"})
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(TOPIC, "ARM_HOME") is True
    assert "alarm_same_mode_config_mismatch" not in caplog.text


@pytest.mark.asyncio
async def test_without_mode_configuration_reads_no_mode():
    sync, _bridge = _sync_with_reads({MODE: "Mode Jour", ENABLE: "0"}, eq=_named_eq(config={}))
    assert await sync.handle_command_message(TOPIC, "ARM_AWAY") is True
    sync._execute_exec_cmd.assert_awaited_once_with(ARMED, {})
    assert _mode_calls(sync) == []


@pytest.mark.asyncio
async def test_without_mode_info_reads_no_mode():
    eq = _named_eq()
    eq.cmds = [c for c in eq.cmds if c.id != MODE]
    sync, _bridge = _sync_with_reads({ENABLE: "0"}, eq=eq)
    assert await sync.handle_command_message(TOPIC, "ARM_HOME") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_C, {})
    assert _mode_calls(sync) == []


@pytest.mark.asyncio
async def test_disarm_is_unchanged_and_reads_nothing():
    sync, _bridge = _sync_with_reads({MODE: "Mode Jour", ENABLE: "1", STATUS: "1"})
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
    sync._read_info_value = _reader({72001: "0"})
    assert await sync.handle_command_message(f"jeedom2ha/{VIRTUAL}/alarm/set", "ARM_AWAY") is True
    sync._execute_exec_cmd.assert_awaited_once_with(72003, {})
    assert sync._read_info_value.calls == [72001]  # Statut seulement : le virtuel n'a pas d'Immédiat


def test_alarm_enable_command_helper():
    mapping = _map(_alarm_eq())
    assert alarm_enable_command(mapping.commands).id == ARMED
    assert alarm_enable_command(_map(_virtual_eq()).commands).id == 72003
    assert alarm_enable_command({}) is None
    info = JeedomCmd(id=1, name="x", generic_type="ALARM_ARMED", type="info", sub_type="binary")
    assert alarm_enable_command({"ALARM_ARMED": info}) is None


# --- Décision du porteur du projet : pas d'armement d'une alarme déclenchée ou en délai d'entrée ---

def _refusal_sync(values, eq=None, published="triggered"):
    """Commande + état : un état d'alarme déjà publié dans ce run, à republier après un refus."""
    mapping = _map(eq if eq is not None else _named_eq())
    state_sync, state_bridge, _decision = _state_sync(mapping)
    if published is not None:
        state_sync._alarm_published[STATE_TOPIC] = published
    sync, bridge = _cmd_sync(mapping, state_sync=state_sync)
    sync._read_info_value = _reader(values)
    return sync, state_bridge


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ["ARM_HOME", "ARM_AWAY", "ARM_NIGHT"])
@pytest.mark.parametrize("values,reason,published", [
    ({STATUS: "1", IMMEDIATE: "0"}, "alarm_arm_refused_triggered", "triggered"),
    ({STATUS: "1"}, "alarm_arm_refused_triggered", "triggered"),          # Immédiat inutile
    ({STATUS: "0", IMMEDIATE: "1"}, "alarm_arm_refused_pending", "pending"),
    ({STATUS: "0"}, "alarm_arm_refused_state_unreadable", "pending"),     # Immédiat : lecture en échec
    ({IMMEDIATE: "0"}, "alarm_arm_refused_state_unreadable", "triggered"),  # Statut : lecture en échec
    ({STATUS: None, IMMEDIATE: "0"}, "alarm_arm_refused_state_unreadable", "triggered"),
    ({STATUS: "0", IMMEDIATE: "abc"}, "alarm_arm_refused_state_unreadable", "pending"),
])
async def test_arming_a_triggered_or_pending_alarm_is_refused(payload, values, reason, published, caplog):
    sync, state_bridge = _refusal_sync({**values, MODE: "Mode Jour", ENABLE: "0"}, published=published)
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(TOPIC, payload) is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert _mode_calls(sync) == []  # rien d'autre n'est lu
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1 and reason in warnings[0]
    # ni valeur ni libellé dans le journal
    assert "Jour" not in caplog.text and "abc" not in caplog.text
    # HA retrouve l'état réel déjà publié (retained), rien d'inventé
    assert [(t, p, r) for t, p, _q, r in state_bridge.published] == [(STATE_TOPIC, published, True)]


@pytest.mark.asyncio
async def test_refusal_with_no_published_state_publishes_nothing():
    sync, state_bridge = _refusal_sync({STATUS: "1"}, published=None)
    assert await sync.handle_command_message(TOPIC, "ARM_AWAY") is False
    assert state_bridge.published == []


@pytest.mark.asyncio
async def test_generic_arming_of_a_triggered_alarm_is_refused_too():
    sync, _state_bridge = _refusal_sync({STATUS: "1"}, eq=_named_eq(config={}))
    assert await sync.handle_command_message(TOPIC, "ARM_AWAY") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_virtual_triggered_is_refused_and_without_immediate_info_nothing_else_is_read(caplog):
    sync, _bridge = _cmd_sync(_map(_virtual_eq()))
    sync._read_info_value = _reader({72001: "1"})
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(f"jeedom2ha/{VIRTUAL}/alarm/set", "ARM_AWAY") is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "alarm_arm_refused_triggered" in caplog.text


@pytest.mark.asyncio
async def test_status_read_exception_refuses():
    sync, _bridge = _cmd_sync(_map(_named_eq()))
    sync._read_info_value = AsyncMock(side_effect=RuntimeError("boom"))
    assert await sync.handle_command_message(TOPIC, "ARM_HOME") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("values", [
    {STATUS: "", IMMEDIATE: "0"},
    {STATUS: "0", IMMEDIATE: "   "},
    {STATUS: "", IMMEDIATE: "1"},     # Statut évalué d'abord, comme une lecture séquentielle
])
async def test_an_empty_status_or_immediate_has_its_own_refusal(values, caplog):
    """Revue I-a — info jamais écrite (vide) : refus distinct, pas « illisible »."""
    sync, _state_bridge = _refusal_sync(values)
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(TOPIC, "ARM_AWAY") is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "alarm_arm_refused_state_empty" in caplog.text
    assert "alarm_arm_refused_state_unreadable" not in caplog.text


@pytest.mark.asyncio
async def test_a_virtual_never_written_is_refused_as_empty(caplog):
    sync, _bridge = _cmd_sync(_map(_virtual_eq()))
    sync._read_info_value = _reader({72001: ""})
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(f"jeedom2ha/{VIRTUAL}/alarm/set", "ARM_AWAY") is False
    assert "alarm_arm_refused_state_empty" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("values,reason", [
    ({STATUS: "1", IMMEDIATE: "1"}, "alarm_arm_refused_triggered"),        # priorité au déclenchement
    ({IMMEDIATE: "1"}, "alarm_arm_refused_state_unreadable"),              # Statut en échec d'abord
    ({STATUS: "0", IMMEDIATE: "1"}, "alarm_arm_refused_pending"),
])
async def test_parallel_reads_give_the_sequential_result(values, reason, caplog):
    sync, _state_bridge = _refusal_sync(values)
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(TOPIC, "ARM_HOME") is False
    assert reason in caplog.text


@pytest.mark.asyncio
async def test_status_and_immediate_are_read_in_parallel():
    """Revue m3 — les deux lectures sont en vol en même temps (délai maximal : une seule requête)."""
    sync, _bridge = _cmd_sync(_map(_named_eq()))
    in_flight, peak = [0], [0]

    async def read(cmd_id):
        in_flight[0] += 1
        peak[0] = max(peak[0], in_flight[0])
        await asyncio.sleep(0.05)
        in_flight[0] -= 1
        return True, SAFE.get(cmd_id, "x")

    sync._read_info_value = read
    await sync.handle_command_message(TOPIC, "ARM_AWAY")
    assert peak[0] == 2


def _alarm_plugin_eq_without_status_generic_type(logical_id):
    eq = _named_eq()
    for cmd in eq.cmds:
        if cmd.id == STATUS:
            cmd.generic_type = None
            cmd.logical_id = logical_id
    return eq


@pytest.mark.asyncio
async def test_alarm_plugin_status_is_found_by_its_logical_id(caplog):
    """Revue m1 — un generic type retiré sur Statut ne contourne pas AC10."""
    eq = _alarm_plugin_eq_without_status_generic_type("state")
    sync, _bridge = _cmd_sync(_map(eq))
    assert "ALARM_STATE" not in sync._app["publications"][EQ].mapping_result.commands
    sync._app["topology"] = _snapshot(eq)
    sync._read_info_value = _reader({STATUS: "1", IMMEDIATE: "0"})
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(TOPIC, "ARM_AWAY") is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "alarm_arm_refused_triggered" in caplog.text

    sync._read_info_value = _reader({STATUS: "0", IMMEDIATE: "0", MODE: "mode nuit", ENABLE: "0"})
    assert await sync.handle_command_message(TOPIC, "ARM_AWAY") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_A, {})


@pytest.mark.asyncio
@pytest.mark.parametrize("with_topology", [True, False])
async def test_alarm_plugin_without_identifiable_status_refuses_arming(with_topology, caplog):
    eq = _alarm_plugin_eq_without_status_generic_type("autre")
    sync, _bridge = _cmd_sync(_map(eq))
    if with_topology:
        sync._app["topology"] = _snapshot(eq)
    sync._read_info_value = _reader({STATUS: "0", IMMEDIATE: "0"})
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(TOPIC, "ARM_AWAY") is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert sync._read_info_value.calls == []
    assert "alarm_arm_refused_no_status_info" in caplog.text


@pytest.mark.asyncio
async def test_virtual_without_status_info_is_not_refused():
    """Hors plugin alarm, une info absente n'est pas lue et ne bloque pas (comportement de la passe 2)."""
    eq = _virtual_eq()
    eq.cmds = [c for c in eq.cmds if c.id != 72001]
    sync, _bridge = _cmd_sync(_map(eq))
    sync._app["topology"] = _snapshot(eq)
    sync._read_info_value = _reader({})
    assert await sync.handle_command_message(f"jeedom2ha/{VIRTUAL}/alarm/set", "ARM_AWAY") is True
    assert sync._read_info_value.calls == []


@pytest.mark.asyncio
async def test_disarming_a_triggered_alarm_is_still_possible():
    sync, _bridge = _refusal_sync({STATUS: "1"})
    assert await sync.handle_command_message(TOPIC, "DISARM") is True
    sync._execute_exec_cmd.assert_awaited_once()


# --- Écart 2 : regroupement -------------------------------------------------------------------

def _coalescing_sync(window=0.2, eq=None):
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
    await asyncio.sleep(0.35)
    assert [(t, p, r) for t, p, _q, r in bridge.published] == [(STATE_TOPIC, "armed_home", True)]


@pytest.mark.asyncio
async def test_window_is_fixed_from_the_first_event():
    sync, bridge, _decision = _coalescing_sync(window=0.3)
    await sync.handle_state_message(EQ, ENABLE, "1")
    await asyncio.sleep(0.15)
    await sync.handle_state_message(EQ, MODE, "Mode Jour")
    # 0,38 s après le premier événement : publié (fenêtre fixe à 0,3 s) ; une fenêtre glissante
    # n'aurait publié qu'à 0,45 s.
    await asyncio.sleep(0.23)
    assert [p[1] for p in bridge.published] == ["armed_home"]
    await sync.handle_state_message(EQ, ENABLE, "0")
    await asyncio.sleep(0.5)
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
        await asyncio.sleep(0.35)
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
        await asyncio.sleep(0.35)
    assert any(r.levelno == logging.WARNING and "mqtt_publish_failed" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_broker_down_at_flush_publishes_nothing(caplog):
    sync, bridge, _decision = _coalescing_sync()
    await sync.handle_state_message(EQ, ENABLE, "1")
    bridge.is_connected = False
    with caplog.at_level(logging.INFO):
        await asyncio.sleep(0.35)
    assert bridge.published == []
    assert "mqtt_unavailable" in caplog.text


@pytest.mark.asyncio
async def test_unpublished_meanwhile_publishes_nothing():
    sync, bridge, _decision = _coalescing_sync()
    await sync.handle_state_message(EQ, ENABLE, "1")
    sync._app["publications"].clear()
    await asyncio.sleep(0.35)
    assert bridge.published == []


@pytest.mark.asyncio
async def test_unknown_is_still_published_once():
    sync, bridge, _decision = _coalescing_sync()
    await sync.handle_state_message(EQ, ENABLE, "1")
    await asyncio.sleep(0.35)
    await sync.handle_state_message(EQ, ENABLE, None)
    await asyncio.sleep(0.35)
    await sync.handle_state_message(EQ, MODE, "mode nuit")
    await asyncio.sleep(0.35)
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
async def test_after_the_shutdown_flush_alarm_states_are_published_at_once():
    """Revue M2 — après le vidage de l'arrêt, plus aucun minuteur : publication immédiate."""
    sync, bridge, _decision = _coalescing_sync(window=5.0)
    sync.flush_pending_states()
    await sync.handle_state_message(EQ, ENABLE, "1")
    assert [p[1] for p in bridge.published] == ["armed_away"]
    assert sync._alarm_pending == {}


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
