"""Story 24.7 — portail et garage projetés en ``cover`` (décisions D1 à D6).

Identifiants et noms synthétiques uniquement (CC-48). Couvre : éligibilité (D4), classe
d'appareil gate/garage (D2), état numérique de la convention barrière (D1), ordres directs
ou bascule conditionnée par le dernier état connu (D3), ``optimistic: false`` (D5),
consommation des commandes sans doublon binary_sensor/button (AC3), ``default_entity_id``
(AC4), retypage button -> cover (D6), override vers button (AC8) et non-régression FLAP_*.
"""
from __future__ import annotations

import json
import logging
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

import pytest

import transport.http_server as http_server
from discovery.publisher import DiscoveryPublisher
from mapping.button import ButtonMapper
from mapping.cover import CoverMapper
from mapping.overrides import apply_type_override, save_override
from mapping.registry import MapperRegistry
from models.mapping import CoverCapabilities, PublicationDecision
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from sync import readback
from sync.command import CommandSynchronizer
from sync.state import StateSynchronizer
from validation.ha_component_registry import PRODUCT_SCOPE, validate_projection

GATE_ID = 7001
GARAGE_ID = 7002


def _cmd(cmd_id, generic_type, type_="action", sub_type="other", value=None):
    return JeedomCmd(id=cmd_id, name=f"Cmd {cmd_id}", generic_type=generic_type,
                     type=type_, sub_type=sub_type, current_value=value)


def _eq(eq_id, cmds, name=None):
    return JeedomEqLogic(id=eq_id, name=name or f"Equipement {eq_id}", object_id=1,
                         eq_type_name="virtual", cmds=cmds)


def _snapshot(*eqs):
    return TopologySnapshot(
        timestamp="2026-11-01T00:00:00+00:00",
        objects={1: JeedomObject(id=1, name="Exterieur")},
        eq_logics={eq.id: eq for eq in eqs},
    )


def _gate_eq(state_sub="numeric", state_value="255"):
    """Portail : GB_OPEN + GB_CLOSE + GB_TOGGLE + BARRIER_STATE numérique."""
    return _eq(GATE_ID, [
        _cmd(70011, "GB_OPEN"),
        _cmd(70012, "GB_CLOSE"),
        _cmd(70013, "GB_TOGGLE"),
        _cmd(70014, "BARRIER_STATE", "info", state_sub, state_value),
    ])


def _garage_eq(state_sub="numeric", state_value="0", with_state=True):
    """Garage : GB_TOGGLE + GARAGE_STATE numérique (ni GB_OPEN ni GB_CLOSE)."""
    cmds = [_cmd(70021, "GB_TOGGLE")]
    if with_state:
        cmds.append(_cmd(70022, "GARAGE_STATE", "info", state_sub, state_value))
    return _eq(GARAGE_ID, cmds)


def _direct_eq(state_value="0"):
    """Ouvrant à boutons directs : GB_OPEN + GB_CLOSE + BARRIER_STATE numérique, sans bascule."""
    return _eq(GATE_ID, [
        _cmd(70011, "GB_OPEN"),
        _cmd(70012, "GB_CLOSE"),
        _cmd(70014, "BARRIER_STATE", "info", "numeric", state_value),
    ])


def _map(eq):
    return MapperRegistry().map(eq, _snapshot(eq))


class _Bridge:
    def __init__(self):
        self.is_connected = True
        self.published = []

    def publish_message(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return True


def _decision(mapping):
    decision = PublicationDecision(
        should_publish=True, reason="sure", mapping_result=mapping,
        state_topic=f"jeedom2ha/{mapping.jeedom_eq_id}/state",
        active_or_alive=True, discovery_published=True,
    )
    mapping.publication_decision_ref = decision
    return decision


def _payload(mapping):
    eq = _gate_eq() if mapping.jeedom_eq_id == GATE_ID else _garage_eq()
    return DiscoveryPublisher(MagicMock()).build_discovery_payload(mapping, _snapshot(eq))


# --- mapping : éligibilité (D4 bis), mode (D3 bis), classe (D2), consommation (AC3) --

def test_gate_with_toggle_open_close_and_state_uses_the_toggle_mode():
    mapping = _map(_gate_eq())
    assert mapping.ha_entity_type == "cover"
    assert mapping.confidence == "sure"
    assert mapping.reason_code == "cover_barrier_toggle_state"
    assert mapping.reason_details == {
        "barrier_mode": "toggle_on_state", "cover_device_class": "gate",
        "barrier_state": "BARRIER_STATE",
    }
    # GB_OPEN / GB_CLOSE ignorés pour l'ordre mais consommés : aucun button en double.
    assert set(mapping.commands) == {"GB_OPEN", "GB_CLOSE", "GB_TOGGLE", "BARRIER_STATE"}
    assert not mapping.additional_mappings
    caps = mapping.capabilities
    assert isinstance(caps, CoverCapabilities)
    assert caps.has_open_close and not caps.has_stop and not caps.has_position


def test_garage_with_toggle_and_numeric_state_is_a_garage_cover():
    mapping = _map(_garage_eq())
    assert mapping.ha_entity_type == "cover"
    assert mapping.confidence == "sure"
    assert mapping.reason_code == "cover_barrier_toggle_state"
    assert mapping.reason_details["cover_device_class"] == "garage"
    assert mapping.reason_details["barrier_mode"] == "toggle_on_state"
    assert set(mapping.commands) == {"GB_TOGGLE", "GARAGE_STATE"}
    assert not mapping.additional_mappings


def test_open_close_without_toggle_and_with_state_uses_the_direct_mode():
    mapping = _map(_direct_eq())
    assert mapping.ha_entity_type == "cover"
    assert mapping.reason_code == "cover_barrier_open_close"
    assert mapping.reason_details["barrier_mode"] == "direct"
    assert mapping.reason_details["cover_device_class"] == "gate"


# Comportement EXACT de main (relevé sur origin/main, story 24.7 non appliquée).
_MAIN_BEHAVIOUR = {
    "toggle_binary_state": ("binary_sensor", "sure", "binary_sensor_garage_state",
                            ["GARAGE_STATE"], {"device_class": "garage_door"}),
    "gate_binary_state": ("binary_sensor", "sure", "binary_sensor_barrier_state",
                          ["BARRIER_STATE"], {"device_class": "garage_door"}),
    "open_close_without_state": ("button", "sure", "button_gb_open", ["GB_OPEN"],
                                 {"command_topic": f"jeedom2ha/{GATE_ID}/cmd"}),
    "toggle_without_state": ("button", "sure", "button_gb_toggle", ["GB_TOGGLE"],
                             {"command_topic": f"jeedom2ha/{GARAGE_ID}/cmd"}),
}


def _shape(name):
    if name == "toggle_binary_state":
        return _garage_eq(state_sub="binary", state_value="1")
    if name == "gate_binary_state":
        return _gate_eq(state_sub="binary", state_value="1")
    if name == "open_close_without_state":
        return _eq(GATE_ID, [_cmd(70011, "GB_OPEN"), _cmd(70012, "GB_CLOSE")])
    return _garage_eq(with_state=False)


@pytest.mark.parametrize("name", sorted(_MAIN_BEHAVIOUR))
def test_ineligible_shapes_keep_exactly_the_main_behaviour(name):
    eq = _shape(name)
    assert CoverMapper().map(eq, _snapshot(eq)) is None
    mapping = _map(eq)
    ha_type, confidence, reason_code, commands, details = _MAIN_BEHAVIOUR[name]
    assert (mapping.ha_entity_type, mapping.confidence, mapping.reason_code) == (
        ha_type, confidence, reason_code)
    assert sorted(mapping.commands) == commands
    assert mapping.reason_details == details
    assert not mapping.additional_mappings


@pytest.mark.parametrize("cmds", [
    [_cmd(1, "GB_TOGGLE"), _cmd(2, "GB_TOGGLE"), _cmd(3, "BARRIER_STATE", "info", "numeric", "0")],
    [_cmd(1, "GB_TOGGLE"), _cmd(3, "BARRIER_STATE", "info", "numeric", "0"),
     _cmd(4, "GARAGE_STATE", "info", "numeric", "0")],
    [_cmd(1, "GB_OPEN"), _cmd(2, "GB_CLOSE"), _cmd(5, "LIGHT_ON"),
     _cmd(3, "BARRIER_STATE", "info", "numeric", "0")],
    [_cmd(1, "GB_OPEN"), _cmd(3, "BARRIER_STATE", "info", "numeric", "0")],
    [_cmd(3, "BARRIER_STATE", "info", "numeric", "0")],
])
def test_ambiguous_barrier_shapes_are_never_a_cover(cmds):
    eq = _eq(GATE_ID, cmds)
    assert CoverMapper().map(eq, _snapshot(eq)) is None


def test_no_name_heuristic_is_used():
    # Un nom quelconque (même « lumière ») ne change rien à la décision barrière.
    eq = _eq(GATE_ID, _gate_eq().cmds, name="Lumiere prise alarme")
    assert CoverMapper().map(eq, _snapshot(eq)).ha_entity_type == "cover"


def test_flap_equipment_with_gb_commands_keeps_the_flap_path():
    eq = _eq(GATE_ID, [_cmd(1, "FLAP_UP"), _cmd(2, "FLAP_DOWN"),
                       _cmd(3, "FLAP_STATE", "info", "binary", "1"), _cmd(4, "GB_TOGGLE")])
    mapping = CoverMapper().map(eq, _snapshot(eq))
    assert mapping.reason_code == "cover_open_close"
    assert readback.barrier_mode(mapping) is None
    assert "GB_TOGGLE" not in mapping.commands


def test_product_scope_unchanged():
    assert PRODUCT_SCOPE == ["light", "cover", "switch", "sensor", "binary_sensor", "button",
                             "climate", "alarm_control_panel"]


# --- discovery : payload (D2, D5, AC4) ----------------------------------------------

def test_gate_discovery_payload():
    payload = _payload(_map(_gate_eq()))
    assert payload["device_class"] == "gate"
    assert payload["unique_id"] == f"jeedom2ha_eq_{GATE_ID}"
    assert payload["object_id"] == f"jeedom2ha_{GATE_ID}"
    assert payload["default_entity_id"] == f"cover.jeedom2ha_{GATE_ID}"
    assert payload["command_topic"] == f"jeedom2ha/{GATE_ID}/set"
    assert payload["state_topic"] == f"jeedom2ha/{GATE_ID}/state"
    assert payload["payload_open"] == "OPEN" and payload["payload_close"] == "CLOSE"
    assert payload["payload_stop"] is None  # pas d'arrêt : STOP retiré des fonctions HA
    assert (payload["state_open"], payload["state_closed"]) == ("open", "closed")
    assert (payload["state_opening"], payload["state_closing"], payload["state_stopped"]) == (
        "opening", "closing", "stopped")
    assert payload["optimistic"] is False
    assert "position_topic" not in payload and "set_position_topic" not in payload
    assert json.loads(json.dumps(payload))["payload_stop"] is None


def test_garage_discovery_payload():
    payload = _payload(_map(_garage_eq()))
    assert payload["device_class"] == "garage"
    assert payload["default_entity_id"] == f"cover.jeedom2ha_{GARAGE_ID}"
    assert payload["optimistic"] is False


def test_barrier_nature_has_a_single_source():
    # M1 : découverte et commande lisent toutes deux reason_details["barrier_mode"].
    mapping = _map(_garage_eq())
    stripped = replace(mapping, reason_details={"cover_device_class": "garage"})
    assert readback.barrier_mode(stripped) is None
    payload = DiscoveryPublisher(MagicMock()).build_discovery_payload(
        stripped, _snapshot(_garage_eq()))
    assert payload["device_class"] == "shutter"
    assert "payload_stop" not in payload


def test_flap_discovery_payload_is_unchanged():
    eq = _eq(GATE_ID, [_cmd(1, "FLAP_UP"), _cmd(2, "FLAP_DOWN"),
                       _cmd(3, "FLAP_STATE", "info", "binary", "1")])
    payload = DiscoveryPublisher(MagicMock()).build_discovery_payload(
        CoverMapper().map(eq, _snapshot(eq)), _snapshot(eq))
    assert payload["device_class"] == "shutter"
    for key in ("payload_stop", "state_opening", "state_closing", "state_stopped"):
        assert key not in payload


# --- état (D1) ----------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("0", "closed"), ("252", "closing"), ("253", "stopped"), ("254", "opening"),
    ("255", "open"), (255, "open"), ("255.0", "open"), ("255,0", "open"), (255.0, "open"),
    (" 254 ", "opening"), (0, "closed"),
])
def test_barrier_value_table(value, expected):
    assert readback.barrier_state(value) == expected


@pytest.mark.parametrize("value", [None, "", "1", "100", "251", "256", "-1", "254.5", "abc",
                                   "nan", "inf", True, "2.55e2", "255e0", "+255", "0x0",
                                   "255.5", "25 5"])
def test_barrier_value_outside_table_is_never_invented(value):
    assert readback.barrier_state(value) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("value,expected", [("0", "closed"), ("254", "opening"), ("255", "open")])
async def test_state_event_published_on_the_cover_state_topic(value, expected):
    decision = _decision(_map(_garage_eq()))
    bridge = _Bridge()
    sync = StateSynchronizer(app={"publications": {GARAGE_ID: decision}}, mqtt_bridge=bridge)
    assert sync.list_state_targets() == [{
        "eq_id": GARAGE_ID, "cmd_id": 70022, "ha_type": "cover",
        "state_topic": f"jeedom2ha/{GARAGE_ID}/state",
    }]
    assert await sync.handle_state_message(GARAGE_ID, 70022, value) is True
    assert bridge.published == [(f"jeedom2ha/{GARAGE_ID}/state", expected, 1, True)]


@pytest.mark.asyncio
async def test_state_value_outside_table_publishes_nothing():
    decision = _decision(_map(_gate_eq()))
    bridge = _Bridge()
    sync = StateSynchronizer(app={"publications": {GATE_ID: decision}}, mqtt_bridge=bridge)
    assert await sync.handle_state_message(GATE_ID, 70014, "100") is False
    assert bridge.published == []
    assert sync.last_event_value(GATE_ID, 70014) == "100"


@pytest.mark.asyncio
async def test_initial_state_uses_the_barrier_table():
    decision = _decision(_map(_gate_eq(state_value="255")))
    bridge = _Bridge()
    sync = StateSynchronizer(app={"publications": {GATE_ID: decision}}, mqtt_bridge=bridge)
    assert await sync.publish_initial_states(decision) == 1
    assert bridge.published == [(f"jeedom2ha/{GATE_ID}/state", "open", 1, True)]


def test_binary_barrier_state_is_never_a_cover_readback():
    commands = {"GB_TOGGLE": _cmd(1, "GB_TOGGLE"),
                "GARAGE_STATE": _cmd(2, "GARAGE_STATE", "info", "binary", "1")}
    mapping = MagicMock(commands=commands, capabilities=CoverCapabilities(has_open_close=True))
    assert readback.readback_commands("cover", mapping) == []


# --- commandes (D3 bis, B1, I3) -----------------------------------------------------

def _cmd_sync(mapping, state_sync=None, fresh=None, fresh_ok=True):
    """CommandSynchronizer avec RPC simulés. ``fresh`` : valeur relue dans Jeedom (I3)."""
    decision = _decision(mapping)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app = {"publications": {mapping.ha_unique_id: decision}, "state_synchronizer": state_sync}
    sync = CommandSynchronizer(app=app, mqtt_bridge=bridge,
                               jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
                               jeedom_core_apikey="core-apikey")
    sync._execute_exec_cmd = AsyncMock(return_value=True)
    sync._read_info_value = AsyncMock(return_value=(fresh_ok, fresh))
    return sync, bridge


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,state_value,allowed", [
    ("OPEN", "0", True), ("OPEN", "252", True), ("OPEN", "253", True),
    ("OPEN", "254", False), ("OPEN", "255", False), ("OPEN", None, False), ("OPEN", "7", False),
    ("CLOSE", "255", True), ("CLOSE", "254", True), ("CLOSE", "253", True),
    ("CLOSE", "252", False), ("CLOSE", "0", False), ("CLOSE", None, False),
])
async def test_direct_mode_is_guarded_by_the_state(payload, state_value, allowed):
    sync, bridge = _cmd_sync(_map(_direct_eq(state_value=state_value)))
    ok = await sync.handle_command_message(f"jeedom2ha/{GATE_ID}/set", payload)
    assert ok is allowed
    if allowed:
        sync._execute_exec_cmd.assert_awaited_once_with(70011 if payload == "OPEN" else 70012, {})
    else:
        sync._execute_exec_cmd.assert_not_awaited()
    sync._read_info_value.assert_not_awaited()
    bridge.publish_message.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ["OPEN", "CLOSE"])
async def test_gate_with_toggle_never_calls_gb_open_or_gb_close(payload):
    fresh = "0" if payload == "OPEN" else "255"
    sync, _bridge = _cmd_sync(_map(_gate_eq(state_value=fresh)), fresh=fresh)
    assert await sync.handle_command_message(f"jeedom2ha/{GATE_ID}/set", payload) is True
    sync._execute_exec_cmd.assert_awaited_once_with(70013, {})  # GB_TOGGLE uniquement
    sync._read_info_value.assert_awaited_once_with(70014)


@pytest.mark.asyncio
async def test_stop_is_refused():
    sync, _bridge = _cmd_sync(_map(_gate_eq()), fresh="255")
    assert await sync.handle_command_message(f"jeedom2ha/{GATE_ID}/set", "STOP") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,fresh,allowed", [
    ("OPEN", "0", True), ("OPEN", 0, True), ("OPEN", "253", False),
    ("OPEN", "255", False), ("OPEN", "252", False), ("OPEN", "254", False),
    ("CLOSE", "255", True), ("CLOSE", "253", False),
    ("CLOSE", "0", False), ("CLOSE", "252", False), ("CLOSE", "254", False),
    ("OPEN", "1", False), ("CLOSE", "", False),
])
async def test_toggle_is_sent_only_from_a_settled_end_position(payload, fresh, allowed):
    sync, bridge = _cmd_sync(_map(_garage_eq()), fresh=fresh)
    ok = await sync.handle_command_message(f"jeedom2ha/{GARAGE_ID}/set", payload)
    assert ok is allowed
    if allowed:
        sync._execute_exec_cmd.assert_awaited_once_with(70021, {})
    else:
        sync._execute_exec_cmd.assert_not_awaited()
    bridge.publish_message.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("fresh,reason", [
    ("252", "barrier_in_motion"), ("254", "barrier_in_motion"),
    ("253", "barrier_stopped_direction_unknown"), ("255", "barrier_already_open"),
    ("9", "barrier_state_unknown"),
])
async def test_toggle_refusal_is_logged(caplog, fresh, reason):
    sync, _bridge = _cmd_sync(_map(_garage_eq()), fresh=fresh)
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(f"jeedom2ha/{GARAGE_ID}/set", "OPEN") is False
    assert f"reason_code={reason} action=refuse_barrier_order" in caplog.text
    assert f"reason_code={reason} action=reject_command" in caplog.text


@pytest.mark.asyncio
async def test_failed_fresh_read_refuses_the_toggle(caplog):
    sync, _bridge = _cmd_sync(_map(_garage_eq(state_value="0")), fresh=None, fresh_ok=False)
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(f"jeedom2ha/{GARAGE_ID}/set", "OPEN") is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "reason_code=barrier_state_read_failed" in caplog.text
    # Rien n'est parti : pas de verrou.
    sync._read_info_value = AsyncMock(return_value=(True, "0"))
    assert await sync.handle_command_message(f"jeedom2ha/{GARAGE_ID}/set", "OPEN") is True


@pytest.mark.asyncio
async def test_fresh_read_wins_over_event_and_topology():
    # Topologie : fermé (0) ; événement : fermé (0) ; Jeedom relu : ouvert (255).
    state_sync = StateSynchronizer(app={"publications": {}}, mqtt_bridge=_Bridge())
    await state_sync.handle_state_message(GARAGE_ID, 70022, "0")
    sync, _bridge = _cmd_sync(_map(_garage_eq(state_value="0")), state_sync, fresh="255")
    assert await sync.handle_command_message(f"jeedom2ha/{GARAGE_ID}/set", "OPEN") is False
    assert await sync.handle_command_message(f"jeedom2ha/{GARAGE_ID}/set", "CLOSE") is True
    sync._execute_exec_cmd.assert_awaited_once_with(70021, {})


@pytest.mark.asyncio
async def test_two_open_in_a_row_send_a_single_toggle(caplog):
    sync, _bridge = _cmd_sync(_map(_garage_eq()), StateSynchronizer(
        app={"publications": {}}, mqtt_bridge=_Bridge()), fresh="0")
    topic = f"jeedom2ha/{GARAGE_ID}/set"
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(topic, "OPEN") is True
        assert await sync.handle_command_message(topic, "OPEN") is False
    sync._execute_exec_cmd.assert_awaited_once_with(70021, {})
    assert "reason_code=barrier_toggle_in_flight" in caplog.text


@pytest.mark.asyncio
async def test_rpc_timeout_still_locks_the_equipment():
    sync, _bridge = _cmd_sync(_map(_garage_eq()), StateSynchronizer(
        app={"publications": {}}, mqtt_bridge=_Bridge()), fresh="0")
    topic = f"jeedom2ha/{GARAGE_ID}/set"

    async def _timeout(cmd_id, options):  # noqa: ARG001
        sync._last_exec_error_reason = "jeedom_rpc_timeout"
        return False

    sync._execute_exec_cmd = AsyncMock(side_effect=_timeout)
    assert await sync.handle_command_message(topic, "OPEN") is False
    sync._execute_exec_cmd = AsyncMock(return_value=True)
    assert await sync.handle_command_message(topic, "OPEN") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_state_events_release_the_lock():
    state_sync = StateSynchronizer(app={"publications": {}}, mqtt_bridge=_Bridge())
    sync, _bridge = _cmd_sync(_map(_garage_eq()), state_sync, fresh="0")
    topic = f"jeedom2ha/{GARAGE_ID}/set"
    assert await sync.handle_command_message(topic, "OPEN") is True
    # Même valeur que celle lue à l'envoi : le verrou tient.
    await state_sync.handle_state_message(GARAGE_ID, 70022, "0")
    assert await sync.handle_command_message(topic, "OPEN") is False
    # 254 puis 255 : le verrou est levé ; l'état relu (255) autorise alors la fermeture.
    await state_sync.handle_state_message(GARAGE_ID, 70022, "254")
    await state_sync.handle_state_message(GARAGE_ID, 70022, "255")
    sync._read_info_value = AsyncMock(return_value=(True, "255"))
    assert await sync.handle_command_message(topic, "CLOSE") is True
    assert sync._execute_exec_cmd.await_count == 2


def _locked_garage():
    state_sync = StateSynchronizer(app={"publications": {}}, mqtt_bridge=_Bridge())
    sync, _bridge = _cmd_sync(_map(_garage_eq()), state_sync, fresh="0")
    return sync, state_sync, f"jeedom2ha/{GARAGE_ID}/set"


@pytest.mark.asyncio
@pytest.mark.parametrize("late_value", ["252", "100", "", None, "2.55e2", "0"])
async def test_only_the_expected_effect_releases_the_lock(late_value):
    # OPEN depuis 0 : seul 254 ou 255 prouve l'effet ; un 252 retardé, une valeur hors
    # table, vide ou None ne lèvent pas le verrou (I-1).
    sync, state_sync, topic = _locked_garage()
    assert await sync.handle_command_message(topic, "OPEN") is True
    await state_sync.handle_state_message(GARAGE_ID, 70022, late_value)
    assert await sync.handle_command_message(topic, "OPEN") is False
    assert sync._execute_exec_cmd.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("effect", ["254", "255"])
async def test_expected_effect_of_open_releases_the_lock(effect):
    sync, state_sync, topic = _locked_garage()
    assert await sync.handle_command_message(topic, "OPEN") is True
    await state_sync.handle_state_message(GARAGE_ID, 70022, effect)
    sync._read_info_value = AsyncMock(return_value=(True, "255"))
    assert await sync.handle_command_message(topic, "CLOSE") is True
    assert sync._execute_exec_cmd.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("effect,held", [("252", False), ("0", False), ("254", True),
                                         ("255", True)])
async def test_expected_effect_of_close(effect, held):
    state_sync = StateSynchronizer(app={"publications": {}}, mqtt_bridge=_Bridge())
    sync, _bridge = _cmd_sync(_map(_garage_eq()), state_sync, fresh="255")
    topic = f"jeedom2ha/{GARAGE_ID}/set"
    assert await sync.handle_command_message(topic, "CLOSE") is True
    await state_sync.handle_state_message(GARAGE_ID, 70022, effect)
    sync._read_info_value = AsyncMock(return_value=(True, "0"))
    assert await sync.handle_command_message(topic, "OPEN") is (not held)


@pytest.mark.asyncio
async def test_no_effect_after_the_delay_keeps_refusing(monkeypatch, caplog):
    import sync.command as command_module

    assert command_module.BARRIER_TOGGLE_IN_FLIGHT_TIMEOUT_S == 60.0
    sync, state_sync, topic = _locked_garage()
    assert await sync.handle_command_message(topic, "OPEN") is True
    now = command_module.time.monotonic()
    monkeypatch.setattr(command_module.time, "monotonic", lambda: now + 61.0)
    with caplog.at_level(logging.WARNING):
        assert await sync.handle_command_message(topic, "OPEN") is False
    assert "reason_code=barrier_no_effect action=refuse_barrier_order" in caplog.text
    # Une valeur identique à celle lue à l'envoi ne lève toujours rien.
    state_sync._pending_click_values[(GARAGE_ID, 70022)] = (now + 62.0, "0")
    assert await sync.handle_command_message(topic, "OPEN") is False
    # Un état de la table différent de celui lu à l'envoi lève le verrou.
    state_sync._pending_click_values[(GARAGE_ID, 70022)] = (now + 63.0, "253")
    sync._read_info_value = AsyncMock(return_value=(True, "0"))
    assert await sync.handle_command_message(topic, "OPEN") is True
    assert sync._execute_exec_cmd.await_count == 2


@pytest.mark.asyncio
async def test_no_effect_lock_released_by_254(monkeypatch):
    import sync.command as command_module

    sync, state_sync, topic = _locked_garage()
    assert await sync.handle_command_message(topic, "OPEN") is True
    now = command_module.time.monotonic()
    monkeypatch.setattr(command_module.time, "monotonic", lambda: now + 61.0)
    assert await sync.handle_command_message(topic, "OPEN") is False
    state_sync._pending_click_values[(GARAGE_ID, 70022)] = (now + 62.0, "254")
    sync._read_info_value = AsyncMock(return_value=(True, "255"))
    assert await sync.handle_command_message(topic, "CLOSE") is True


@pytest.mark.asyncio
async def test_concurrent_orders_send_a_single_toggle():
    import asyncio

    sync, _state_sync, topic = _locked_garage()
    gate = asyncio.Event()

    async def _slow_read(cmd_id):  # noqa: ARG001
        await gate.wait()
        return True, "0"

    sync._read_info_value = AsyncMock(side_effect=_slow_read)
    first = asyncio.create_task(sync.handle_command_message(topic, "OPEN"))
    second = asyncio.create_task(sync.handle_command_message(topic, "OPEN"))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    gate.set()
    results = await asyncio.gather(first, second)
    assert sorted(results) == [False, True]
    sync._execute_exec_cmd.assert_awaited_once_with(70021, {})


@pytest.mark.asyncio
async def test_refused_guard_removes_its_marker():
    sync, _state_sync, topic = _locked_garage()
    sync._read_info_value = AsyncMock(return_value=(True, "254"))
    assert await sync.handle_command_message(topic, "OPEN") is False
    sync._read_info_value = AsyncMock(return_value=(True, "0"))
    assert await sync.handle_command_message(topic, "OPEN") is True


@pytest.mark.asyncio
async def test_lock_is_per_equipment():
    garage = _map(_garage_eq())
    other = _map(_eq(7003, [_cmd(70031, "GB_TOGGLE"),
                            _cmd(70032, "GARAGE_STATE", "info", "numeric", "0")]))
    sync, _bridge = _cmd_sync(garage, fresh="0")
    sync._app["publications"][other.ha_unique_id] = _decision(other)
    assert await sync.handle_command_message(f"jeedom2ha/{GARAGE_ID}/set", "OPEN") is True
    assert await sync.handle_command_message("jeedom2ha/7003/set", "OPEN") is True


@pytest.mark.asyncio
async def test_refusal_is_not_replayed_when_the_state_changes_later():
    state_sync = StateSynchronizer(app={"publications": {}}, mqtt_bridge=_Bridge())
    sync, _bridge = _cmd_sync(_map(_garage_eq()), state_sync, fresh="254")
    assert await sync.handle_command_message(f"jeedom2ha/{GARAGE_ID}/set", "CLOSE") is False
    await state_sync.handle_state_message(GARAGE_ID, 70022, "255")
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_fresh_read_uses_cmd_exec_cmd_on_the_info_command():
    class _Resp:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def json(self, content_type=None):  # noqa: ARG002
            return {"jsonrpc": "2.0", "result": {"value": "255", "collectDate": "x"}}

    class _Session:
        closed = False

        def __init__(self):
            self.calls = []

        def post(self, endpoint, json):
            self.calls.append((endpoint, json))
            return _Resp()

    sync = CommandSynchronizer(app={}, mqtt_bridge=MagicMock(),
                               jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
                               jeedom_core_apikey="core-apikey")
    sync._session = _Session()
    assert await sync._read_info_value(70022) == (True, "255")
    _endpoint, body = sync._session.calls[0]
    assert body["method"] == "cmd::execCmd"
    assert body["params"]["id"] == 70022 and body["params"]["options"] == {}


def test_command_and_state_sync_agree_on_reliability():
    for mapping in (_map(_gate_eq()), _map(_garage_eq())):
        decision = _decision(mapping)
        state_sync = StateSynchronizer(app={"publications": {1: decision}}, mqtt_bridge=_Bridge())
        sync, _bridge = _cmd_sync(mapping, state_sync)
        assert sync._has_reliable_state(mapping, decision) is True
        assert state_sync.list_state_targets()


# --- cycle de vie (D6) et override (AC8) --------------------------------------------

@pytest.mark.asyncio
async def test_button_to_cover_retype_empties_the_button_discovery():
    eq = _garage_eq()
    previous = ButtonMapper().map(eq, _snapshot(eq))
    previous_decision = PublicationDecision(should_publish=True, reason="sure",
                                            mapping_result=previous, discovery_published=True)
    publisher = AsyncMock()
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    pending: dict = {}
    await http_server._detect_lifecycle_changes(
        GARAGE_ID, _map(eq), previous_decision, boot_cache={}, is_first_sync=False,
        publisher=publisher, pending_discovery_unpublish=pending,
    )
    publisher.unpublish_by_eq_id.assert_awaited_once_with(GARAGE_ID, entity_type="button", node_ids=[])
    assert pending == {}


@pytest.mark.asyncio
async def test_button_to_cover_retype_at_boot_empties_the_button_discovery():
    eq = _gate_eq()
    publisher = AsyncMock()
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    boot_cache = {GATE_ID: {"entity_type": "button", "ha_name": eq.name, "published": True,
                            "node_ids": []}}
    await http_server._detect_lifecycle_changes(
        GATE_ID, _map(eq), None, boot_cache=boot_cache, is_first_sync=True,
        publisher=publisher, pending_discovery_unpublish={},
    )
    publisher.unpublish_by_eq_id.assert_awaited_once_with(GATE_ID, entity_type="button", node_ids=[])


def test_button_topic_is_the_one_emptied():
    publisher = DiscoveryPublisher(MagicMock())
    assert publisher._build_topic(GATE_ID, entity_type="button") == (
        f"homeassistant/button/jeedom2ha_{GATE_ID}/config")
    assert publisher._build_topic(GATE_ID, entity_type="cover") == (
        f"homeassistant/cover/jeedom2ha_{GATE_ID}/config")


def test_override_can_send_the_gate_back_to_a_button(tmp_path):
    save_override(GATE_ID, 70013, {"ha_entity_type": "button"}, str(tmp_path))
    mapping = apply_type_override(_map(_gate_eq()), str(tmp_path))
    assert mapping.ha_entity_type == "button"
    assert validate_projection("button", mapping.capabilities).is_valid
    payload = DiscoveryPublisher(MagicMock()).build_discovery_payload(mapping, _snapshot(_gate_eq()))
    assert payload["default_entity_id"] == f"button.jeedom2ha_{GATE_ID}"
    assert payload["command_topic"] == f"jeedom2ha/{GATE_ID}/cmd"
    assert "device_class" not in payload


def test_removing_the_override_gives_the_cover_back(tmp_path):
    mapping = apply_type_override(_map(_gate_eq()), str(tmp_path))
    assert mapping.ha_entity_type == "cover"
    assert validate_projection("cover", mapping.capabilities).is_valid


# --- commandes retenues (I4) --------------------------------------------------------

def _message(topic, payload, retain):
    message = MagicMock(topic=topic, payload=payload.encode())
    message.retain = retain
    return message


@pytest.mark.asyncio
@pytest.mark.parametrize("topic", [
    f"jeedom2ha/{GARAGE_ID}/set", "jeedom2ha/12/34/set", "jeedom2ha/12/position/set",
    "jeedom2ha/12/brightness/set", "jeedom2ha/scenario_5/cmd",
])
@pytest.mark.parametrize("retain", [True, 1])
async def test_retained_command_is_ignored(caplog, topic, retain):
    import asyncio

    from transport.mqtt_client import MqttBridge

    bridge = MqttBridge()
    bridge._loop = asyncio.get_running_loop()
    handler = AsyncMock()
    bridge.set_command_handler(handler)
    with caplog.at_level(logging.INFO):
        bridge._on_message(None, None, _message(topic, "OPEN", retain))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
    handler.assert_not_awaited()
    assert "reason_code=retained_command_ignored" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("retain", [False, 0])
async def test_live_command_is_still_dispatched(retain):
    import asyncio

    from transport.mqtt_client import MqttBridge

    bridge = MqttBridge()
    bridge._loop = asyncio.get_running_loop()
    handler = AsyncMock()
    bridge.set_command_handler(handler)
    bridge._on_message(None, None, _message(f"jeedom2ha/{GARAGE_ID}/set", "OPEN", retain))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    handler.assert_awaited_once_with(f"jeedom2ha/{GARAGE_ID}/set", "OPEN")


@pytest.mark.asyncio
async def test_retained_ha_birth_message_is_still_honoured():
    import asyncio

    from transport.mqtt_client import MqttBridge

    bridge = MqttBridge()
    bridge._loop = asyncio.get_running_loop()
    bridge._trigger_ha_birth_republish = MagicMock()
    bridge._on_ha_birth_cb = MagicMock()
    bridge.set_command_handler(AsyncMock())
    bridge._on_message(None, None, _message("homeassistant/status", "online", True))
    await asyncio.sleep(0)
    bridge._trigger_ha_birth_republish.assert_called_once()


@pytest.mark.asyncio
async def test_late_event_before_expiry_does_not_release_after_the_delay(monkeypatch):
    # Relecture 3 (résidu I-2) : un 252 retardé reçu AVANT l'expiration, puis aucun
    # mouvement pendant 60 s : à l'expiration, le verrou reste (barrier_no_effect).
    import sync.command as command_module

    sync, state_sync, topic = _locked_garage()
    assert await sync.handle_command_message(topic, "OPEN") is True
    now = command_module.time.monotonic()
    state_sync._pending_click_values[(GARAGE_ID, 70022)] = (now + 1.0, "252")
    monkeypatch.setattr(command_module.time, "monotonic", lambda: now + 61.0)
    assert await sync.handle_command_message(topic, "OPEN") is False
    assert sync._execute_exec_cmd.await_count == 1
