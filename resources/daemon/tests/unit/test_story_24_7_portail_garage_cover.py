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


# --- mapping : éligibilité (D4), classe (D2), consommation (AC3) --------------------

def test_gate_with_open_close_and_numeric_state_is_a_gate_cover():
    mapping = _map(_gate_eq())
    assert mapping.ha_entity_type == "cover"
    assert mapping.confidence == "sure"
    assert mapping.reason_code == "cover_barrier_open_close"
    assert mapping.reason_details["cover_device_class"] == "gate"
    assert mapping.reason_details["barrier_mode"] == "direct"
    # Toutes les commandes sont consommées : aucune entité secondaire (pas de doublon).
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


def test_open_close_without_state_is_a_probable_gate_cover():
    eq = _eq(GATE_ID, [_cmd(70011, "GB_OPEN"), _cmd(70012, "GB_CLOSE")])
    mapping = _map(eq)
    assert mapping.ha_entity_type == "cover"
    assert mapping.confidence == "probable"
    assert mapping.reason_details["cover_device_class"] == "gate"


def test_toggle_alone_without_state_is_not_a_cover_and_stays_a_button():
    eq = _garage_eq(with_state=False)
    assert CoverMapper().map(eq, _snapshot(eq)) is None
    mapping = _map(eq)
    assert mapping.ha_entity_type == "button"
    assert mapping == ButtonMapper().map(eq, _snapshot(eq))


def test_toggle_with_binary_state_keeps_the_current_behaviour():
    eq = _garage_eq(state_sub="binary", state_value="1")
    assert CoverMapper().map(eq, _snapshot(eq)) is None
    mapping = _map(eq)
    assert mapping.ha_entity_type != "cover"
    # Comportement inchangé : même résultat que la chaîne sans le cas barrière.
    assert mapping.ha_entity_type in ("binary_sensor", "button")


def test_binary_state_alone_stays_a_garage_door_binary_sensor():
    eq = _eq(GARAGE_ID, [_cmd(70022, "GARAGE_STATE", "info", "binary", "1")])
    mapping = _map(eq)
    assert mapping.ha_entity_type == "binary_sensor"
    assert mapping.reason_details["device_class"] == "garage_door"


def test_open_close_with_binary_state_keeps_the_current_behaviour():
    eq = _gate_eq(state_sub="binary", state_value="1")
    assert CoverMapper().map(eq, _snapshot(eq)) is None


@pytest.mark.parametrize("cmds", [
    [_cmd(1, "GB_TOGGLE"), _cmd(2, "GB_TOGGLE"), _cmd(3, "BARRIER_STATE", "info", "numeric", "0")],
    [_cmd(1, "GB_TOGGLE"), _cmd(3, "BARRIER_STATE", "info", "numeric", "0"),
     _cmd(4, "GARAGE_STATE", "info", "numeric", "0")],
    [_cmd(1, "GB_OPEN"), _cmd(2, "GB_CLOSE"), _cmd(5, "LIGHT_ON")],
    [_cmd(1, "GB_OPEN")],
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
    assert "barrier_mode" not in (mapping.reason_details or {})
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


def test_gate_without_state_stays_optimistic():
    eq = _eq(GATE_ID, [_cmd(70011, "GB_OPEN"), _cmd(70012, "GB_CLOSE")])
    payload = _payload(_map(eq))
    assert payload["device_class"] == "gate"
    assert payload["optimistic"] is True


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
    ("255", "open"), (255, "open"), ("255.0", "open"), (0, "closed"),
])
def test_barrier_value_table(value, expected):
    assert readback.barrier_state(value) == expected


@pytest.mark.parametrize("value", [None, "", "1", "100", "251", "256", "-1", "254.5", "abc",
                                   "nan", "inf", True])
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


# --- commandes (D3) -----------------------------------------------------------------

def _cmd_sync(mapping, state_sync=None):
    decision = _decision(mapping)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app = {"publications": {mapping.ha_unique_id: decision}, "state_synchronizer": state_sync}
    sync = CommandSynchronizer(app=app, mqtt_bridge=bridge,
                               jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
                               jeedom_core_apikey="core-apikey")
    sync._execute_exec_cmd = AsyncMock(return_value=True)
    return sync, bridge


@pytest.mark.asyncio
@pytest.mark.parametrize("state_value", ["0", "252", "253", "254", "255", None])
@pytest.mark.parametrize("payload,cmd_id", [("OPEN", 70011), ("CLOSE", 70012)])
async def test_gate_orders_are_direct_whatever_the_state(payload, cmd_id, state_value):
    sync, bridge = _cmd_sync(_map(_gate_eq(state_value=state_value)))
    assert await sync.handle_command_message(f"jeedom2ha/{GATE_ID}/set", payload) is True
    sync._execute_exec_cmd.assert_awaited_once_with(cmd_id, {})
    bridge.publish_message.assert_not_called()  # pas d'état optimiste (D5)


@pytest.mark.asyncio
async def test_gate_stop_is_refused():
    sync, _bridge = _cmd_sync(_map(_gate_eq()))
    assert await sync.handle_command_message(f"jeedom2ha/{GATE_ID}/set", "STOP") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,state_value,allowed", [
    ("OPEN", "0", True), ("OPEN", "253", True),
    ("OPEN", "255", False), ("OPEN", "252", False), ("OPEN", "254", False),
    ("CLOSE", "255", True), ("CLOSE", "253", True),
    ("CLOSE", "0", False), ("CLOSE", "252", False), ("CLOSE", "254", False),
    ("OPEN", None, False), ("CLOSE", None, False), ("OPEN", "1", False), ("CLOSE", "", False),
])
async def test_garage_toggle_is_sent_only_in_the_right_direction(payload, state_value, allowed):
    sync, bridge = _cmd_sync(_map(_garage_eq(state_value=state_value)))
    ok = await sync.handle_command_message(f"jeedom2ha/{GARAGE_ID}/set", payload)
    assert ok is allowed
    if allowed:
        sync._execute_exec_cmd.assert_awaited_once_with(70021, {})
    else:
        sync._execute_exec_cmd.assert_not_awaited()
    bridge.publish_message.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("state_value,reason", [
    (None, "barrier_state_unknown"), ("252", "barrier_in_motion"),
    ("254", "barrier_in_motion"), ("255", "barrier_already_open"),
])
async def test_garage_refusal_is_logged(caplog, state_value, reason):
    sync, _bridge = _cmd_sync(_map(_garage_eq(state_value=state_value)))
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(f"jeedom2ha/{GARAGE_ID}/set", "OPEN") is False
    assert f"reason_code={reason} action=refuse_barrier_toggle" in caplog.text
    assert f"reason_code={reason} action=reject_command" in caplog.text


@pytest.mark.asyncio
async def test_last_jeedom_event_wins_over_the_topology_value():
    # Topologie : fermé (0). Événement Jeedom reçu depuis : ouvert (255).
    mapping = _map(_garage_eq(state_value="0"))
    state_sync = StateSynchronizer(app={"publications": {}}, mqtt_bridge=_Bridge())
    await state_sync.handle_state_message(GARAGE_ID, 70022, "255")
    sync, _bridge = _cmd_sync(mapping, state_sync)
    assert await sync.handle_command_message(f"jeedom2ha/{GARAGE_ID}/set", "OPEN") is False
    assert await sync.handle_command_message(f"jeedom2ha/{GARAGE_ID}/set", "CLOSE") is True
    sync._execute_exec_cmd.assert_awaited_once_with(70021, {})


@pytest.mark.asyncio
async def test_refusal_is_not_replayed_when_the_state_changes_later():
    # Refus pendant le mouvement : aucun ordre mis en attente ; l'état qui arrive ensuite
    # ne déclenche rien, un nouvel ordre de HA est nécessaire.
    mapping = _map(_garage_eq(state_value="254"))
    state_sync = StateSynchronizer(app={"publications": {}}, mqtt_bridge=_Bridge())
    sync, _bridge = _cmd_sync(mapping, state_sync)
    assert await sync.handle_command_message(f"jeedom2ha/{GARAGE_ID}/set", "CLOSE") is False
    await state_sync.handle_state_message(GARAGE_ID, 70022, "255")
    sync._execute_exec_cmd.assert_not_awaited()
    assert await sync.handle_command_message(f"jeedom2ha/{GARAGE_ID}/set", "CLOSE") is True
    sync._execute_exec_cmd.assert_awaited_once_with(70021, {})


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
