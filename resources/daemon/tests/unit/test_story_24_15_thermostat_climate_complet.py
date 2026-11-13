"""Story 24.15 — Thermostat : ``climate`` complet (état, consigne, mode).

Décisions : D1 A (``heat`` / ``off`` + presets ; arrêt reconnu par son identifiant logique,
jamais par son nom), D2 (``hvac_action`` d'après ``THERMOSTAT_STATE``, l'arrêt prime),
D3 (bornes de l'ordre de consigne, pas de 0,5, refus hors bornes), D4 A (``switch``
« Verrouillage » séparé, catégorie configuration), D5 (température extérieure ignorée).

Identifiants synthétiques, aucun nom réel (CC-48).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

import transport.http_server as http_server
from discovery.publisher import DiscoveryPublisher
from export import decision_export
from mapping.climate import ClimateMapper
from mapping.registry import MapperRegistry
from models.mapping import (
    ClimateCapabilities,
    CoverCapabilities,
    LightCapabilities,
    PublicationDecision,
    SwitchCapabilities,
)
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from sync import readback
from sync.command import CommandSynchronizer, CommandTranslation
from sync.state import StateSynchronizer
from validation.ha_component_registry import HA_COMPONENT_REGISTRY, validate_projection

EQ = 1500

SET_SETPOINT = 15001
SETPOINT = 15002
TEMPERATURE = 15003
OUTDOOR = 15004
MODE = 15005
MODE_A = 15006
MODE_B = 15007
MODE_C = 15008
MODE_OFF = 15009
STATE = 15010
STATE_NAME = 15011
LOCK = 15012
SET_LOCK = 15013
SET_UNLOCK = 15014
NO_TYPE = 15015


def _cmd(cmd_id, generic_type, type_="action", sub_type="other", value=None, name=None,
         logical_id=None, unit=None, min_value=None, max_value=None):
    return JeedomCmd(id=cmd_id, name=name or f"Cmd {cmd_id}", generic_type=generic_type,
                     type=type_, sub_type=sub_type, current_value=value, logical_id=logical_id,
                     unit=unit, min_value=min_value, max_value=max_value)


def _thermostat(*, mode_value="Mode A", state_value="1", setpoint_value="19.5",
                temperature_value="20.1", lock_value="0", with_off=True, with_mode=True,
                with_state=True, with_setpoint_info=True, with_lock=True,
                min_value=7.0, max_value=30.0, off_name="Off", off_logical_id="off",
                mode_names=("Mode A", "Mode B", "Mode C deux mots"), unit="°C"):
    """Thermostat du plugin Jeedom « thermostat » : toutes ses commandes typées."""
    cmds = [_cmd(SET_SETPOINT, "THERMOSTAT_SET_SETPOINT", sub_type="slider", name="Consigne",
                 logical_id="thermostat", min_value=min_value, max_value=max_value)]
    if with_setpoint_info:
        cmds.append(_cmd(SETPOINT, "THERMOSTAT_SETPOINT", "info", "numeric", setpoint_value,
                         unit=unit))
    cmds.append(_cmd(TEMPERATURE, "THERMOSTAT_TEMPERATURE", "info", "numeric",
                     temperature_value, unit=unit))
    cmds.append(_cmd(OUTDOOR, "THERMOSTAT_TEMPERATURE_OUTDOOR", "info", "numeric", "8", unit=unit))
    if with_mode:
        cmds.append(_cmd(MODE, "THERMOSTAT_MODE", "info", "string", mode_value))
    for cmd_id, name in zip((MODE_A, MODE_B, MODE_C), mode_names):
        cmds.append(_cmd(cmd_id, "THERMOSTAT_SET_MODE", name=name, logical_id="modeAction"))
    if with_off:
        cmds.append(_cmd(MODE_OFF, "THERMOSTAT_SET_MODE", name=off_name, logical_id=off_logical_id))
    if with_state:
        cmds.append(_cmd(STATE, "THERMOSTAT_STATE", "info", "binary", state_value))
    cmds.append(_cmd(STATE_NAME, "THERMOSTAT_STATE_NAME", "info", "string", "Statut"))
    if with_lock:
        cmds.append(_cmd(LOCK, "THERMOSTAT_LOCK", "info", "binary", lock_value))
        cmds.append(_cmd(SET_LOCK, "THERMOSTAT_SET_LOCK"))
        cmds.append(_cmd(SET_UNLOCK, "THERMOSTAT_SET_UNLOCK"))
    cmds.append(_cmd(NO_TYPE, None, "info", "numeric", "3"))
    return JeedomEqLogic(id=EQ, name=f"Thermostat {EQ}", object_id=1,
                         eq_type_name="thermostat", cmds=cmds)


def _snapshot(eq):
    return TopologySnapshot(
        timestamp="2026-11-13T00:00:00+00:00",
        objects={1: JeedomObject(id=1, name="Piece")},
        eq_logics={eq.id: eq},
    )


def _map(eq=None):
    eq = eq or _thermostat()
    return MapperRegistry().map(eq, _snapshot(eq))


def _payload(mapping, eq=None):
    eq = eq or _thermostat()
    return DiscoveryPublisher(MagicMock()).build_discovery_payload(mapping, _snapshot(eq))


def _decision(mapping):
    decision = PublicationDecision(
        should_publish=True, reason="sure", mapping_result=mapping,
        state_topic=http_server._resolve_state_topic(mapping),
        active_or_alive=True, discovery_published=True,
    )
    mapping.publication_decision_ref = decision
    return decision


def _published(mapping):
    decision = _decision(mapping)
    for secondary in mapping.additional_mappings or []:
        _decision(secondary)
    return decision


class _Bridge:
    def __init__(self):
        self.is_connected = True
        self.published = []

    def publish_message(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return True


def _topic(channel):
    return f"jeedom2ha/{EQ}/{channel}"


# --- AC2 : mapper ---------------------------------------------------------------------

def test_full_thermostat_is_a_climate_with_every_capability():
    mapping = _map()
    assert mapping.ha_entity_type == "climate"
    assert mapping.ha_unique_id == f"jeedom2ha_eq_{EQ}"  # AC7 : unique_id inchangé
    caps = mapping.capabilities
    assert isinstance(caps, ClimateCapabilities)
    assert (caps.has_setpoint, caps.has_setpoint_state, caps.has_current_temperature,
            caps.has_mode, caps.has_off, caps.has_presets, caps.has_action) == (True,) * 7
    details = mapping.reason_details
    assert details["preset_modes"] == ["Mode A", "Mode B", "Mode C deux mots"]
    assert details["off_mode_name"] == "Off"
    assert details["preset_commands"] == {"Mode A": MODE_A, "Mode B": MODE_B,
                                          "Mode C deux mots": MODE_C}
    assert details["min_temp"] == 7.0 and details["max_temp"] == 30.0
    assert details["temperature_unit"] == "C"


def test_ignored_commands_are_not_captured():
    mapping = _map()
    used = {c.id for c in mapping.commands.values()}
    # D5 : extérieure ignorée ; statut texte jamais lu ; commande sans type ignorée.
    assert not used & {OUTDOOR, STATE_NAME, NO_TYPE}
    # Le verrou appartient à l'interrupteur séparé, pas au climate.
    assert not used & {LOCK, SET_LOCK, SET_UNLOCK}


def test_off_is_recognised_by_its_logical_id_whatever_its_name():
    mapping = _map(_thermostat(off_name="Arret complet"))
    assert mapping.capabilities.has_off is True
    assert mapping.reason_details["off_mode_name"] == "Arret complet"
    assert "Arret complet" not in mapping.reason_details["preset_modes"]


def test_a_mode_named_off_without_the_off_logical_id_is_a_preset():
    mapping = _map(_thermostat(off_logical_id="modeAction"))
    assert mapping.capabilities.has_off is False
    assert "off_mode_name" not in mapping.reason_details
    assert "Off" in mapping.reason_details["preset_modes"]


def test_arbitrary_mode_names_are_kept_as_is():
    names = ("Économie", "nuit  longue", "MAJUSCULES")
    mapping = _map(_thermostat(mode_names=names, mode_value="Économie"))
    assert mapping.reason_details["preset_modes"] == list(names)


def test_preset_none_and_duplicated_names_are_dropped(caplog):
    with caplog.at_level(logging.WARNING):
        mapping = _map(_thermostat(mode_names=("none", "Double", "Double")))
    assert mapping.reason_details.get("preset_modes", []) == []
    assert mapping.capabilities.has_presets is False
    assert "preset" in caplog.text


def test_without_mode_info_no_mode_state_no_off_no_preset():
    mapping = _map(_thermostat(with_mode=False))
    caps = mapping.capabilities
    assert (caps.has_mode, caps.has_off, caps.has_presets) == (False, False, False)


def test_without_state_info_no_action():
    assert _map(_thermostat(with_state=False)).capabilities.has_action is False


def test_without_setpoint_info_no_setpoint_state():
    mapping = _map(_thermostat(with_setpoint_info=False))
    assert mapping.ha_entity_type == "climate"
    assert mapping.capabilities.has_setpoint_state is False


def test_without_set_setpoint_it_is_not_a_climate():
    eq = _thermostat()
    eq.cmds = [c for c in eq.cmds if c.generic_type != "THERMOSTAT_SET_SETPOINT"]
    assert ClimateMapper().map(eq, _snapshot(eq)) is None


@pytest.mark.parametrize("bounds", [(None, None), (7.0, None), (None, 30.0), (30.0, 7.0),
                                    (20.0, 20.0)])
def test_invalid_bounds_are_not_kept(bounds):
    mapping = _map(_thermostat(min_value=bounds[0], max_value=bounds[1]))
    assert "min_temp" not in mapping.reason_details
    assert "max_temp" not in mapping.reason_details


@pytest.mark.parametrize("unit,expected", [("°C", "C"), ("°F", "F"), ("%", None), (None, None)])
def test_temperature_unit_only_for_celsius_or_fahrenheit(unit, expected):
    assert _map(_thermostat(unit=unit)).reason_details.get("temperature_unit") == expected


# --- D4 A : interrupteur « Verrouillage » ---------------------------------------------

def test_lock_is_a_separate_config_switch():
    mapping = _map()
    assert len(mapping.additional_mappings) == 1
    switch = mapping.additional_mappings[0]
    assert switch.ha_entity_type == "switch"
    assert switch.ha_name == "Verrouillage"
    assert switch.ha_unique_id == f"jeedom2ha_eq_{EQ}_cmd_{LOCK}"
    assert {k: c.id for k, c in switch.commands.items()} == {
        "THERMOSTAT_LOCK": LOCK, "THERMOSTAT_SET_LOCK": SET_LOCK,
        "THERMOSTAT_SET_UNLOCK": SET_UNLOCK}
    assert switch.reason_details["entity_category"] == "config"
    assert isinstance(switch.capabilities, SwitchCapabilities)
    assert validate_projection("switch", switch.capabilities).is_valid
    assert all(m.ha_entity_type != "lock" for m in [mapping, *mapping.additional_mappings])


def test_incomplete_lock_gives_no_switch():
    eq = _thermostat()
    eq.cmds = [c for c in eq.cmds if c.generic_type != "THERMOSTAT_SET_UNLOCK"]
    assert _map(eq).additional_mappings == []


def test_lock_switch_payload():
    switch = _map().additional_mappings[0]
    payload = _payload(switch)
    assert payload["entity_category"] == "config"
    assert payload["name"] == "Verrouillage"
    assert payload["state_topic"] == f"jeedom2ha/{EQ}/{LOCK}/state"
    assert payload["command_topic"] == f"jeedom2ha/{EQ}/{LOCK}/set"
    assert payload["default_entity_id"] == f"switch.jeedom2ha_{EQ}_{LOCK}"


# --- AC3 / AC7 : payload ----------------------------------------------------------------

def test_full_climate_payload():
    payload = _payload(_map())
    assert payload["unique_id"] == f"jeedom2ha_eq_{EQ}"
    assert payload["default_entity_id"] == f"climate.jeedom2ha_{EQ}"
    assert payload["name"] is None  # entité seule nommée comme l'appareil (22.3)
    assert payload["optimistic"] is False
    assert payload["modes"] == ["heat", "off"]
    assert payload["mode_state_topic"] == _topic("mode")
    assert payload["mode_command_topic"] == _topic("mode/set")
    assert payload["preset_modes"] == ["Mode A", "Mode B", "Mode C deux mots"]
    assert payload["preset_mode_state_topic"] == _topic("preset")
    assert payload["preset_mode_command_topic"] == _topic("preset/set")
    assert payload["action_topic"] == _topic("action")
    assert payload["temperature_state_topic"] == _topic("setpoint")
    assert payload["temperature_command_topic"] == _topic("temperature/set")
    assert payload["current_temperature_topic"] == _topic("current_temperature")
    assert (payload["min_temp"], payload["max_temp"]) == (7.0, 30.0)
    assert (payload["temp_step"], payload["precision"]) == (0.5, 0.1)
    assert payload["temperature_unit"] == "C"
    # AC8 : l'ancien topic d'état de la consigne n'est plus déclaré.
    assert f"jeedom2ha/{EQ}/temperature/state" not in json.dumps(payload)


def test_minimal_climate_payload_declares_no_invented_topic():
    eq = _thermostat(with_mode=False, with_state=False, with_setpoint_info=False,
                     min_value=None, max_value=None, unit=None)
    payload = _payload(_map(eq), eq)
    assert payload["modes"] == ["heat"]
    assert payload["optimistic"] is False
    for key in ("mode_state_topic", "mode_command_topic", "preset_modes",
                "preset_mode_state_topic", "preset_mode_command_topic", "action_topic",
                "temperature_state_topic", "min_temp", "max_temp", "temperature_unit"):
        assert key not in payload, key
    assert payload["temperature_command_topic"] == _topic("temperature/set")


def test_without_off_order_only_heat_and_no_mode_command():
    payload = _payload(_map(_thermostat(with_off=False)))
    assert payload["modes"] == ["heat"]
    assert payload["mode_state_topic"] == _topic("mode")
    assert "mode_command_topic" not in payload


def test_registry_entry_and_fr40_proof():
    assert "temperature_command_topic" in HA_COMPONENT_REGISTRY["climate"]["required_fields"]
    assert validate_projection("climate", ClimateCapabilities(has_setpoint=True)).is_valid
    assert not validate_projection("climate", ClimateCapabilities(has_mode=True)).is_valid


# --- D1 / D2 : traduction de l'état -----------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("Off", "off"), ("Mode A", "heat"), ("Aucun", "heat"), ("Inconnu", "heat"), ("", None),
    (None, None), ("off", "heat"),  # casse différente : pas le nom de l'ordre d'arrêt
])
def test_hvac_mode_table(value, expected):
    assert readback.climate_hvac_mode(value, "Off") == expected


def test_hvac_mode_without_off_order_is_always_heat():
    assert readback.climate_hvac_mode("Off", None) == "heat"


@pytest.mark.parametrize("value,expected", [
    ("Mode B", "Mode B"), ("Aucun", "none"), ("Off", "none"), ("mode b", "none"), ("", None),
])
def test_preset_table(value, expected):
    assert readback.climate_preset(value, ["Mode A", "Mode B"]) == expected


@pytest.mark.parametrize("state,mode,expected", [
    ("1", "Mode A", "heating"), ("0", "Mode A", "idle"), ("on", None, "heating"),
    ("false", None, "idle"), ("1", "Off", "off"), ("0", "Off", "off"),
    ("x", "Mode A", None), (None, "Mode A", None), ("x", "Off", "off"),
])
def test_hvac_action_table(state, mode, expected):
    assert readback.climate_action(state, mode, "Off") == expected


# --- AC4 / AC5 : streaming et état initial ---------------------------------------------

def _state_sync(mapping=None):
    mapping = mapping or _map()
    bridge = _Bridge()
    sync = StateSynchronizer(app={"publications": {EQ: _published(mapping)}}, mqtt_bridge=bridge)
    return sync, bridge, mapping


def test_climate_is_streamed_and_listened():
    sync, _bridge, _mapping = _state_sync()
    assert sync.streams_actionable_type("climate") is True
    targets = {(t["cmd_id"], t["ha_type"]) for t in sync.list_state_targets()}
    assert targets == {(SETPOINT, "climate"), (TEMPERATURE, "climate"), (MODE, "climate"),
                       (STATE, "climate"), (LOCK, "switch")}


@pytest.mark.asyncio
async def test_mode_change_republishes_mode_preset_and_action():
    sync, bridge, _mapping = _state_sync()
    assert await sync.handle_state_message(EQ, MODE, "Mode B") is True
    assert sorted(bridge.published) == sorted([
        (_topic("mode"), "heat", 1, True),
        (_topic("preset"), "Mode B", 1, True),
        (_topic("action"), "heating", 1, True),
    ])


@pytest.mark.asyncio
async def test_off_mode_wins_over_the_heating_state():
    sync, bridge, _mapping = _state_sync()
    assert await sync.handle_state_message(EQ, MODE, "Off") is True
    assert sorted(bridge.published) == sorted([
        (_topic("mode"), "off", 1, True),
        (_topic("preset"), "none", 1, True),
        (_topic("action"), "off", 1, True),
    ])
    bridge.published.clear()
    # La chauffe est lue par rapport au dernier mode reçu (événement), pas à la topologie.
    assert await sync.handle_state_message(EQ, STATE, "1") is True
    assert bridge.published == [(_topic("action"), "off", 1, True)]


@pytest.mark.asyncio
async def test_manual_setpoint_mode_is_heat_with_no_preset():
    sync, bridge, _mapping = _state_sync()
    await sync.handle_state_message(EQ, STATE, "0")
    bridge.published.clear()
    assert await sync.handle_state_message(EQ, MODE, "Aucun") is True
    assert sorted(bridge.published) == sorted([
        (_topic("mode"), "heat", 1, True),
        (_topic("preset"), "none", 1, True),
        (_topic("action"), "idle", 1, True),
    ])


@pytest.mark.asyncio
async def test_empty_mode_publishes_nothing():
    sync, bridge, _mapping = _state_sync()
    assert await sync.handle_state_message(EQ, MODE, "") is False
    assert bridge.published == []


@pytest.mark.asyncio
@pytest.mark.parametrize("cmd_id,value,channel,expected", [
    (STATE, "0", "action", "idle"), (STATE, "1", "action", "heating"),
    (SETPOINT, "20,5", "setpoint", "20.5"), (SETPOINT, "21", "setpoint", "21"),
    (TEMPERATURE, "19.37", "current_temperature", "19.37"),
])
async def test_single_channel_events(cmd_id, value, channel, expected):
    sync, bridge, _mapping = _state_sync()
    assert await sync.handle_state_message(EQ, cmd_id, value) is True
    assert bridge.published == [(_topic(channel), expected, 1, True)]


@pytest.mark.asyncio
@pytest.mark.parametrize("cmd_id,value", [
    (STATE, "2"), (SETPOINT, "abc"), (TEMPERATURE, "nan"), (TEMPERATURE, "inf"), (SETPOINT, ""),
])
async def test_unreadable_values_publish_nothing(cmd_id, value):
    sync, bridge, _mapping = _state_sync()
    assert await sync.handle_state_message(EQ, cmd_id, value) is False
    assert bridge.published == []


@pytest.mark.asyncio
async def test_outdoor_temperature_is_not_streamed():
    sync, bridge, _mapping = _state_sync()
    assert await sync.handle_state_message(EQ, OUTDOOR, "5") is False
    assert bridge.published == []


@pytest.mark.asyncio
async def test_lock_state_is_streamed_on_the_switch():
    sync, bridge, _mapping = _state_sync()
    assert await sync.handle_state_message(EQ, LOCK, "1") is True
    assert bridge.published == [(f"jeedom2ha/{EQ}/{LOCK}/state", "ON", 1, True)]
    bridge.published.clear()
    assert await sync.handle_state_message(EQ, LOCK, "abc") is False
    assert bridge.published == []


@pytest.mark.asyncio
async def test_initial_states_are_published_after_discovery():
    mapping = _map(_thermostat(mode_value="Mode C deux mots", state_value="0"))
    decision = _published(mapping)
    bridge = _Bridge()
    sync = StateSynchronizer(app={"publications": {EQ: decision}}, mqtt_bridge=bridge)
    assert await sync.publish_initial_states(decision) == 6
    assert sorted(bridge.published) == sorted([
        (_topic("setpoint"), "19.5", 1, True),
        (_topic("current_temperature"), "20.1", 1, True),
        (_topic("mode"), "heat", 1, True),
        (_topic("preset"), "Mode C deux mots", 1, True),
        (_topic("action"), "idle", 1, True),
        (f"jeedom2ha/{EQ}/{LOCK}/state", "OFF", 1, True),
    ])


@pytest.mark.asyncio
async def test_initial_states_skip_unknown_values():
    mapping = _map(_thermostat(mode_value="", state_value=None, setpoint_value=None,
                               temperature_value="abc", lock_value=None))
    decision = _published(mapping)
    bridge = _Bridge()
    sync = StateSynchronizer(app={"publications": {EQ: decision}}, mqtt_bridge=bridge)
    assert await sync.publish_initial_states(decision) == 0
    assert bridge.published == []


@pytest.mark.asyncio
async def test_retained_channel_without_source_is_emptied(tmp_path):
    bridge = _Bridge()
    full = _map()
    sync = StateSynchronizer(app={"publications": {EQ: _published(full)}}, mqtt_bridge=bridge,
                             data_dir=str(tmp_path))
    await sync.publish_initial_states(full.publication_decision_ref)
    sync.flush_retained_channels()
    # Le thermostat perd son info de chauffe et son info de mode : canaux vidés à la republication.
    reduced = _map(_thermostat(with_state=False, with_mode=False))
    sync._app["publications"] = {EQ: _published(reduced)}
    bridge.published.clear()
    await sync.publish_initial_states(reduced.publication_decision_ref)
    emptied = {t for (t, p, _q, r) in bridge.published if p == "" and r}
    assert emptied == {_topic("mode"), _topic("preset"), _topic("action")}


# --- AC6 : ordres -------------------------------------------------------------------------

def _cmd_sync(mapping=None, state_sync=None):
    mapping = mapping or _map()
    decision = _published(mapping)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app = {"publications": {EQ: decision}, "state_synchronizer": state_sync}
    sync = CommandSynchronizer(app=app, mqtt_bridge=bridge,
                               jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
                               jeedom_core_apikey="core-apikey")
    sync._execute_exec_cmd = AsyncMock(return_value=True)
    return sync, bridge


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,slider", [
    ("20.5", "20.5"), ("20,5", "20.5"), ("20.3", "20.5"), ("20.2", "20"), ("21", "21"),
    ("7", "7"), ("30", "30"),
])
async def test_setpoint_order_is_rounded_to_half_a_degree(payload, slider):
    sync, bridge = _cmd_sync()
    assert await sync.handle_command_message(_topic("temperature/set"), payload) is True
    sync._execute_exec_cmd.assert_awaited_once_with(SET_SETPOINT, {"slider": slider})
    bridge.publish_message.assert_not_called()  # optimistic: false


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ["35", "6.5", "30.3", "abc", "", "inf", "nan", "-inf"])
async def test_setpoint_out_of_range_or_unreadable_is_refused(payload, caplog):
    sync, _bridge = _cmd_sync()
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(_topic("temperature/set"), payload) is False
    sync._execute_exec_cmd.assert_not_awaited()
    if payload in ("35", "6.5", "30.3"):
        assert "reason_code=setpoint_out_of_range" in caplog.text


@pytest.mark.asyncio
async def test_setpoint_without_bounds_accepts_any_finite_value():
    sync, _bridge = _cmd_sync(_map(_thermostat(min_value=None, max_value=None)))
    assert await sync.handle_command_message(_topic("temperature/set"), "45") is True
    sync._execute_exec_cmd.assert_awaited_once_with(SET_SETPOINT, {"slider": "45"})


@pytest.mark.asyncio
async def test_off_order_goes_to_the_off_command():
    sync, _bridge = _cmd_sync()
    assert await sync.handle_command_message(_topic("mode/set"), "off") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_OFF, {})


@pytest.mark.asyncio
async def test_off_without_off_order_is_refused():
    sync, _bridge = _cmd_sync(_map(_thermostat(with_off=False)))
    assert await sync.handle_command_message(_topic("mode/set"), "off") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_heat_while_heating_sends_nothing(caplog):
    sync, _bridge = _cmd_sync(_map(_thermostat(mode_value="Mode A")))
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(_topic("mode/set"), "heat") is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "reason_code=mode_already_heat" in caplog.text


@pytest.mark.asyncio
async def test_heat_from_off_resends_the_current_setpoint():
    sync, _bridge = _cmd_sync(_map(_thermostat(mode_value="Off", setpoint_value="19.5")))
    assert await sync.handle_command_message(_topic("mode/set"), "heat") is True
    sync._execute_exec_cmd.assert_awaited_once_with(SET_SETPOINT, {"slider": "19.5"})


@pytest.mark.asyncio
async def test_heat_from_off_reads_the_last_event_first():
    state_sync = StateSynchronizer(app={}, mqtt_bridge=_Bridge())
    sync, _bridge = _cmd_sync(_map(_thermostat(mode_value="Mode A", setpoint_value="19.5")),
                              state_sync=state_sync)
    state_sync._pending_click_values[(EQ, MODE)] = (0.0, "Off")
    state_sync._pending_click_values[(EQ, SETPOINT)] = (0.0, "17")
    assert await sync.handle_command_message(_topic("mode/set"), "heat") is True
    sync._execute_exec_cmd.assert_awaited_once_with(SET_SETPOINT, {"slider": "17"})


@pytest.mark.asyncio
@pytest.mark.parametrize("mode_value,setpoint_value", [("", "19.5"), ("Off", None), ("Off", "x")])
async def test_heat_with_unknown_mode_or_setpoint_is_refused(mode_value, setpoint_value):
    sync, _bridge = _cmd_sync(_map(_thermostat(mode_value=mode_value,
                                               setpoint_value=setpoint_value)))
    assert await sync.handle_command_message(_topic("mode/set"), "heat") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ["cool", "auto", "HEAT", "Off", "", "fan_only"])
async def test_other_mode_payloads_are_refused(payload):
    sync, _bridge = _cmd_sync(_map(_thermostat(mode_value="Off")))
    assert await sync.handle_command_message(_topic("mode/set"), payload) is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,cmd_id", [("Mode B", MODE_B), ("Mode C deux mots", MODE_C)])
async def test_preset_order_goes_to_the_command_of_that_name(payload, cmd_id):
    sync, _bridge = _cmd_sync()
    assert await sync.handle_command_message(_topic("preset/set"), payload) is True
    sync._execute_exec_cmd.assert_awaited_once_with(cmd_id, {})


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ["mode b", "none", "Off", "Inconnu", ""])
async def test_other_preset_payloads_are_refused(payload):
    sync, _bridge = _cmd_sync()
    assert await sync.handle_command_message(_topic("preset/set"), payload) is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_preset_never_uses_a_command_of_another_equipment():
    mapping = _map()
    mapping.reason_details["preset_commands"]["Mode B"] = 99999  # id étranger
    sync, _bridge = _cmd_sync(mapping)
    assert await sync.handle_command_message(_topic("preset/set"), "Mode B") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_undeclared_climate_topics_are_refused():
    sync, _bridge = _cmd_sync(_map(_thermostat(with_mode=False)))
    assert await sync.handle_command_message(_topic("preset/set"), "Mode A") is False
    assert await sync.handle_command_message(_topic("mode/set"), "off") is False
    assert await sync.handle_command_message(f"jeedom2ha/{EQ}/set", "20") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,cmd_id", [("ON", SET_LOCK), ("OFF", SET_UNLOCK)])
async def test_lock_switch_orders(payload, cmd_id):
    sync, bridge = _cmd_sync()
    assert await sync.handle_command_message(f"jeedom2ha/{EQ}/{LOCK}/set", payload) is True
    sync._execute_exec_cmd.assert_awaited_once_with(cmd_id, {})


@pytest.mark.asyncio
async def test_confirmation_is_the_real_state_never_optimistic():
    state_sync = StateSynchronizer(app={}, mqtt_bridge=_Bridge())
    mapping = _map()
    sync, bridge = _cmd_sync(mapping, state_sync=state_sync)
    decision = mapping.publication_decision_ref
    for family in ("climate_setpoint", "climate_mode", "climate_preset"):
        translation = CommandTranslation(cmd_id=1, options={}, command_family=family)
        assert sync._select_confirmation_policy(mapping, decision, translation) == \
            "real_state_confirmation"
    bare = _map(_thermostat(with_setpoint_info=False, with_mode=False))
    _published(bare)
    translation = CommandTranslation(cmd_id=1, options={}, command_family="climate_setpoint")
    assert sync._select_confirmation_policy(bare, bare.publication_decision_ref, translation) == \
        "stateless"
    switch = mapping.additional_mappings[0]
    translation = CommandTranslation(cmd_id=SET_LOCK, options={}, command_family="on_off")
    assert sync._select_confirmation_policy(switch, switch.publication_decision_ref,
                                            translation) == "real_state_confirmation"


def _message(topic, payload, retain):
    message = MagicMock(topic=topic, payload=payload.encode())
    message.retain = retain
    return message


@pytest.mark.asyncio
@pytest.mark.parametrize("topic", [_topic("temperature/set"), _topic("mode/set"),
                                   _topic("preset/set")])
async def test_retained_climate_command_is_ignored(caplog, topic):
    from transport.mqtt_client import MqttBridge

    bridge = MqttBridge()
    bridge._loop = asyncio.get_running_loop()
    handler = AsyncMock()
    bridge.set_command_handler(handler)
    with caplog.at_level(logging.INFO):
        bridge._on_message(None, None, _message(topic, "off", True))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
    handler.assert_not_awaited()
    assert "reason_code=retained_command_ignored" in caplog.text


# --- AC9 : override et export -------------------------------------------------------------

_CLIMATE_CAPS = ClimateCapabilities(has_setpoint=True, has_setpoint_state=True, has_mode=True,
                                    has_off=True, has_presets=True, has_action=True)


@pytest.mark.parametrize("forced", ["switch", "light", "cover", "button", "valve", "lock",
                                    "alarm_control_panel", "number", "select"])
def test_thermostat_forced_to_another_actuator_is_refused(forced):
    assert validate_projection(forced, _CLIMATE_CAPS).is_valid is False


@pytest.mark.parametrize("caps", [
    SwitchCapabilities(has_on_off=True, has_state=True),
    LightCapabilities(has_on_off=True),
    CoverCapabilities(has_open_close=True),
])
def test_other_families_forced_to_climate_are_refused(caps):
    assert validate_projection("climate", caps).is_valid is False


def test_decision_export_reports_a_streamed_climate():
    eq = _thermostat()
    mapping = _map(eq)
    decision = _published(mapping)
    sync = StateSynchronizer(app={"publications": {EQ: decision}}, mqtt_bridge=_Bridge())
    streamed = {(t["eq_id"], t["cmd_id"], t["ha_type"]) for t in sync.list_state_targets()}
    row = decision_export._entity_row(
        DiscoveryPublisher(MagicMock()), mapping, "primary", decision, _snapshot(eq), EQ,
        streamed=streamed,
    )
    assert row["state_source"] == "streamed"
    assert row["entity_id_expected"] == f"climate.jeedom2ha_{EQ}"


# --- AC8 : cycle de vie -------------------------------------------------------------------

def test_runtime_state_topic_and_discovery_topics():
    mapping = _map()
    assert http_server._resolve_state_topic(mapping) == f"jeedom2ha/{EQ}/state"
    entries = http_server._collect_unpublish_node_ids(mapping)
    assert ("switch", f"jeedom2ha_{EQ}_{LOCK}") in entries


@pytest.mark.asyncio
async def test_boot_in_place_update_does_not_unpublish_the_climate():
    boot = {EQ: {"entity_type": "climate", "ha_name": f"Thermostat {EQ}",
                 "published": True, "node_ids": []}}
    publisher = MagicMock()
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    await http_server._detect_lifecycle_changes(EQ, _map(), None, boot, True, publisher, {})
    publisher.unpublish_by_eq_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_runtime_in_place_update_does_not_unpublish_the_climate():
    previous = ClimateMapper().map(_thermostat(with_lock=False), _snapshot(_thermostat()))
    publisher = MagicMock()
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    await http_server._detect_lifecycle_changes(
        EQ, _map(), _published(previous), {}, False, publisher, {})
    publisher.unpublish_by_eq_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_publish_climate_and_lock_switch_topics():
    bridge = MagicMock()
    bridge.publish_message = MagicMock(return_value=True)
    publisher = DiscoveryPublisher(bridge)
    mapping = _map()
    assert await publisher.publish_climate(mapping, _snapshot(_thermostat())) is True
    assert await publisher.publish_switch(mapping.additional_mappings[0],
                                          _snapshot(_thermostat())) is True
    topics = [call.args[0] for call in bridge.publish_message.call_args_list]
    assert topics == [f"homeassistant/climate/jeedom2ha_{EQ}/config",
                      f"homeassistant/switch/jeedom2ha_{EQ}_{LOCK}/config"]


# --- Revue Codex (PR #377) : lecture fraîche contre événements stockés ; espaces des noms --

@pytest.mark.asyncio
async def test_fresh_sync_replaces_an_older_stored_event():
    # Événement ancien : arrêt. Puis une synchro relit le thermostat en « Mode A ».
    sync, bridge, _mapping = _state_sync(_map(_thermostat(mode_value="Off")))
    await sync.handle_state_message(EQ, MODE, "Off")
    fresh = _map(_thermostat(mode_value="Mode A"))
    decision = _published(fresh)
    sync._app["publications"] = {EQ: decision}
    sync.reconcile_fresh_read(decision, time.monotonic())
    bridge.published.clear()
    # Un événement de chauffe ultérieur : l'action suit le mode frais, pas l'ancien arrêt.
    assert await sync.handle_state_message(EQ, STATE, "1") is True
    assert bridge.published == [(_topic("action"), "heating", 1, True)]


def test_an_event_later_than_the_fresh_read_is_kept():
    sync, _bridge, mapping = _state_sync()
    read_at = time.monotonic()
    sync._pending_click_values[(EQ, MODE)] = (read_at + 1.0, "Off")
    sync.reconcile_fresh_read(mapping.publication_decision_ref, read_at)
    assert sync.last_event_value(EQ, MODE) == "Off"
    assert sync.last_event_value(EQ, SETPOINT) == "19.5"


@pytest.mark.asyncio
async def test_heat_after_a_fresh_sync_sends_the_fresh_setpoint():
    state_sync = StateSynchronizer(app={}, mqtt_bridge=_Bridge())
    state_sync._pending_click_values[(EQ, SETPOINT)] = (time.monotonic(), "17")  # ancien
    fresh = _map(_thermostat(mode_value="Off", setpoint_value="19.5"))
    sync, _bridge = _cmd_sync(fresh, state_sync=state_sync)
    state_sync.reconcile_fresh_read(fresh.publication_decision_ref, time.monotonic())
    assert await sync.handle_command_message(_topic("mode/set"), "heat") is True
    sync._execute_exec_cmd.assert_awaited_once_with(SET_SETPOINT, {"slider": "19.5"})


@pytest.mark.asyncio
async def test_publier_click_values_replace_older_stored_events():
    sync, bridge, mapping = _state_sync()
    sync._pending_click_values[(EQ, MODE)] = (time.monotonic(), "Off")  # ancien
    fresh_since = time.monotonic()
    await sync.publish_click_states(mapping.publication_decision_ref,
                                    {MODE: "Mode B", STATE: "1"}, fresh_since)
    bridge.published.clear()
    assert await sync.handle_state_message(EQ, STATE, "1") is True
    assert bridge.published == [(_topic("action"), "heating", 1, True)]


@pytest.mark.asyncio
async def test_sync_request_replaces_older_stored_events(aiohttp_client):
    payload = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures" / "golden_corpus" / "sync_payload.json")
        .read_text(encoding="utf-8"))
    app = http_server.create_app(local_secret="s")
    bridge = _Bridge()
    app["mqtt_bridge"] = bridge
    state_sync = StateSynchronizer(app, bridge)
    app["state_synchronizer"] = state_sync
    state_sync._pending_click_values[(11000, 110004)] = (time.monotonic(), "Off")  # ancien
    cli = await aiohttp_client(app)
    body = {"action": "sync", "payload": payload, "request_id": "r",
            "timestamp": "2026-11-13T00:00:00Z"}
    resp = await cli.post("/action/sync", json=body, headers={"X-Local-Secret": "s"})
    assert resp.status == 200
    assert state_sync.last_event_value(11000, 110004) == "Mode A"


@pytest.mark.asyncio
async def test_preset_with_spaces_is_recognised():
    names = (" Mode espace ", "Mode B", "Mode C")
    sync, bridge, mapping = _state_sync(_map(_thermostat(mode_names=names, mode_value="Mode B")))
    assert mapping.reason_details["preset_modes"] == list(names)
    assert await sync.handle_state_message(EQ, MODE, " Mode espace ") is True
    assert (_topic("preset"), " Mode espace ", 1, True) in bridge.published
    assert (_topic("mode"), "heat", 1, True) in bridge.published
    cmd_sync, _cmd_bridge = _cmd_sync(_map(_thermostat(mode_names=names)))
    assert await cmd_sync.handle_command_message(_topic("preset/set"), " Mode espace ") is True
    cmd_sync._execute_exec_cmd.assert_awaited_once_with(MODE_A, {})


@pytest.mark.asyncio
async def test_off_name_with_spaces_is_compared_exactly():
    sync, bridge, _mapping = _state_sync(_map(_thermostat(off_name=" Arret ")))
    assert await sync.handle_state_message(EQ, MODE, " Arret ") is True
    assert (_topic("mode"), "off", 1, True) in bridge.published
