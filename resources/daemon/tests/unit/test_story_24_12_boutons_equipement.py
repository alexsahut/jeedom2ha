"""Story 24.12 — un appui HA sur un bouton d'équipement déclenche SA commande Jeedom.

Constat (01/11, prouvé ici) : la discovery publie les boutons d'équipement sur
``jeedom2ha/<eq_id>/cmd`` (``ButtonMapper`` / ``FallbackMapper``) et le pont MQTT est
abonné à ``jeedom2ha/+/cmd``, mais ``CommandSynchronizer`` ne routait ce topic que pour
les boutons de scénario (``jeedom2ha/scenario_<id>/cmd``) : tout appui était rejeté
(``invalid_command_topic``) et aucune commande Jeedom n'était appelée.

Les topics de commande sont relus dans le payload de discovery réellement construit
(``DiscoveryPublisher``), jamais recopiés à la main : routage et discovery restent alignés.
Données fictives (CC-48).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

import pytest

from discovery.publisher import DiscoveryPublisher
from mapping.button import ScenarioButtonMapper
from mapping.registry import MapperRegistry
from models.mapping import MappingResult, PublicationDecision, SwitchCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, JeedomScenario, TopologySnapshot
from sync.command import CommandSynchronizer

BUTTON_ID = 9120     # équipement mono-entité : un seul bouton
MULTI_ID = 9121      # équipement multi-entité : switch principal + bouton secondaire
SWITCH_ID = 9122     # non-régression switch
COVER_ID = 9123      # non-régression cover


def _cmd(cmd_id, generic_type, type_="action", sub_type="other", name=None, value=None):
    return JeedomCmd(id=cmd_id, name=name or f"Cmd {cmd_id}", generic_type=generic_type,
                     type=type_, sub_type=sub_type, current_value=value)


def _eq(eq_id, cmds, name=None):
    return JeedomEqLogic(id=eq_id, name=name or f"Equipement {eq_id}", object_id=1,
                         eq_type_name="virtual", cmds=cmds)


def _snapshot(*eqs):
    return TopologySnapshot(
        timestamp="2026-11-12T00:00:00+00:00",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={eq.id: eq for eq in eqs},
    )


def _map(eq):
    return MapperRegistry().map(eq, _snapshot(eq))


def _button_eq():
    """Bouton seul : une action « other » typée, plus une info qui ne doit jamais être exécutée."""
    return _eq(BUTTON_ID, [_cmd(91201, "GENERIC_ACTION", name="Sonner")])


def _switch_trio(base, family="SWITCH", name="Prise"):
    return [
        _cmd(base, f"{family}_STATE", "info", "binary", name=name, value="0"),
        _cmd(base + 1, f"{family}_ON", name=f"{name} On"),
        _cmd(base + 2, f"{family}_OFF", name=f"{name} Off"),
    ]


def _multi_with_secondary_button():
    """Switch principal + bouton secondaire (même équipement, topic propre à la commande).

    Aucun mapper natif ne produit aujourd'hui de bouton secondaire ; il est construit ici
    comme la discovery le publierait (topic de nœud ``jeedom2ha/<eq>/<cmd>/set``), pour que
    le routage générique soit prouvé sur la forme multi-entité.
    """
    eq = _eq(MULTI_ID, [*_switch_trio(91211), _cmd(91219, "GENERIC_ACTION", name="Reset")])
    primary = MapperRegistry().map(eq, _snapshot(eq))
    assert primary.ha_entity_type == "switch"
    secondary = MappingResult(
        ha_entity_type="button",
        confidence="sure",
        reason_code="button_generic_action",
        jeedom_eq_id=MULTI_ID,
        ha_unique_id=f"jeedom2ha_eq_{MULTI_ID}_cmd_91219",
        ha_name="Reset",
        suggested_area="Salon",
        commands={"GENERIC_ACTION": eq.cmds[-1]},
        capabilities=SwitchCapabilities(has_on_off=True),
        reason_details={
            "node_id": f"jeedom2ha_{MULTI_ID}_91219",
            "command_topic": f"jeedom2ha/{MULTI_ID}/91219/set",
        },
    )
    primary.additional_mappings = [secondary]
    return eq, primary, secondary


def _command_topic(mapping, eq):
    """Topic de commande tel que la discovery le publie réellement."""
    payload = DiscoveryPublisher(MagicMock()).build_discovery_payload(mapping, _snapshot(eq))
    return payload["command_topic"]


def _decision(mapping):
    decision = PublicationDecision(
        should_publish=True, reason="sure", mapping_result=mapping,
        state_topic=(mapping.reason_details or {}).get("state_topic"),
        active_or_alive=True, discovery_published=True,
    )
    mapping.publication_decision_ref = decision
    return decision


def _cmd_sync(*primaries, scenario_publications=None):
    publications = {}
    for primary in primaries:
        publications[primary.jeedom_eq_id] = _decision(primary)
        for secondary in primary.additional_mappings or []:
            _decision(secondary)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app = {"publications": publications, "state_synchronizer": None,
           "scenario_publications": scenario_publications or {}}
    sync = CommandSynchronizer(app=app, mqtt_bridge=bridge,
                               jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
                               jeedom_core_apikey="core-apikey")
    sync._execute_exec_cmd = AsyncMock(return_value=True)
    sync._execute_scenario_start = AsyncMock(return_value=True)
    return sync, bridge


# --- reproduction du défaut (AC1, AC2) ------------------------------------------------

@pytest.mark.asyncio
async def test_press_on_a_single_entity_equipment_button_runs_its_action_once():
    eq = _button_eq()
    button = _map(eq)
    assert button.ha_entity_type == "button"
    topic = _command_topic(button, eq)
    assert topic == f"jeedom2ha/{BUTTON_ID}/cmd"
    sync, bridge = _cmd_sync(button)

    assert await sync.handle_command_message(topic, "PRESS") is True
    sync._execute_exec_cmd.assert_awaited_once_with(91201, {})
    bridge.publish_message.assert_not_called()  # bouton sans état : rien d'inventé


@pytest.mark.asyncio
async def test_press_on_a_secondary_button_runs_only_its_own_action_once():
    eq, primary, secondary = _multi_with_secondary_button()
    topic = _command_topic(secondary, eq)
    assert topic == f"jeedom2ha/{MULTI_ID}/91219/set"
    sync, _bridge = _cmd_sync(primary)

    assert await sync.handle_command_message(topic, "PRESS") is True
    sync._execute_exec_cmd.assert_awaited_once_with(91219, {})


@pytest.mark.asyncio
async def test_fallback_button_is_routed_too():
    """Bouton de repli (action sans type générique reconnu, sous-type « other »)."""
    eq = _eq(BUTTON_ID, [_cmd(91205, None, name="Action")])
    button = _map(eq)
    assert (button.ha_entity_type, button.reason_code) == ("button", "fallback_button_default")
    sync, _bridge = _cmd_sync(button)
    assert await sync.handle_command_message(_command_topic(button, eq), "PRESS") is True
    sync._execute_exec_cmd.assert_awaited_once_with(91205, {})


# --- garde-fous (AC3 à AC6) -----------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ["press", "ON", "OFF", "OPEN", "1", "", "PRESS PRESS"])
async def test_unexpected_payload_is_refused(payload, caplog):
    button = _map(_button_eq())
    sync, _bridge = _cmd_sync(button)
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(f"jeedom2ha/{BUTTON_ID}/cmd", payload) is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "reason_code=invalid_command_payload" in caplog.text


@pytest.mark.asyncio
async def test_payload_configured_in_the_discovery_is_honoured():
    button = _map(_button_eq())
    button.reason_details["payload_press"] = "GO"
    sync, _bridge = _cmd_sync(button)
    assert await sync.handle_command_message(f"jeedom2ha/{BUTTON_ID}/cmd", "PRESS") is False
    assert await sync.handle_command_message(f"jeedom2ha/{BUTTON_ID}/cmd", "GO") is True
    sync._execute_exec_cmd.assert_awaited_once_with(91201, {})


@pytest.mark.asyncio
async def test_missing_jeedom_command_sends_nothing(caplog):
    button = _map(_button_eq())
    button.commands = {}
    sync, _bridge = _cmd_sync(button)
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(f"jeedom2ha/{BUTTON_ID}/cmd", "PRESS") is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "reason_code=missing_action_command" in caplog.text


@pytest.mark.asyncio
async def test_unknown_equipment_sends_nothing():
    sync, _bridge = _cmd_sync(_map(_button_eq()))
    assert await sync.handle_command_message("jeedom2ha/9999/cmd", "PRESS") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_info_command_is_never_executed():
    button = _map(_button_eq())
    button.commands = {"GENERIC_ACTION": _cmd(91209, "GENERIC_ACTION", "info", "binary")}
    sync, _bridge = _cmd_sync(button)
    assert await sync.handle_command_message(f"jeedom2ha/{BUTTON_ID}/cmd", "PRESS") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("sub_type", ["slider", "message", "color", "select"])
async def test_action_needing_a_value_is_never_pressed(sub_type):
    """Un appui n'a pas de valeur : une action slider / message / couleur / liste est refusée."""
    button = _map(_button_eq())
    button.commands = {"GENERIC_ACTION": _cmd(91201, "GENERIC_ACTION", "action", sub_type)}
    sync, _bridge = _cmd_sync(button)
    assert await sync.handle_command_message(f"jeedom2ha/{BUTTON_ID}/cmd", "PRESS") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_several_candidate_actions_are_refused_rather_than_guessed(caplog):
    """Ex. un switch forcé en bouton : ON et OFF sont deux actions, aucune n'est devinée."""
    eq = _eq(SWITCH_ID, _switch_trio(91221))
    forced = replace(_map(eq), ha_entity_type="button")
    sync, _bridge = _cmd_sync(forced)
    with caplog.at_level(logging.INFO):
        assert await sync.handle_command_message(_command_topic(forced, eq), "PRESS") is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert "reason_code=ambiguous_button_action" in caplog.text


@pytest.mark.asyncio
async def test_equipment_topic_is_not_routed_to_a_secondary_button():
    _eq_unused, primary, _secondary = _multi_with_secondary_button()
    sync, _bridge = _cmd_sync(primary)
    # Aucune entité de l'équipement ne publie jeedom2ha/<eq>/cmd : rien n'est exécuté.
    assert await sync.handle_command_message(f"jeedom2ha/{MULTI_ID}/cmd", "PRESS") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_unpublished_button_sends_nothing():
    button = _map(_button_eq())
    sync, _bridge = _cmd_sync(button)
    sync._app["publications"][BUTTON_ID].should_publish = False
    assert await sync.handle_command_message(f"jeedom2ha/{BUTTON_ID}/cmd", "PRESS") is False
    sync._execute_exec_cmd.assert_not_awaited()


def _message(topic, payload, retain):
    message = MagicMock(topic=topic, payload=payload.encode())
    message.retain = retain
    return message


@pytest.mark.asyncio
@pytest.mark.parametrize("topic", [f"jeedom2ha/{BUTTON_ID}/cmd", f"jeedom2ha/{MULTI_ID}/91219/set"])
@pytest.mark.parametrize("retain", [True, 1])
async def test_retained_press_is_ignored(caplog, topic, retain):
    from transport.mqtt_client import MqttBridge

    bridge = MqttBridge()
    bridge._loop = asyncio.get_running_loop()
    handler = AsyncMock()
    bridge.set_command_handler(handler)
    with caplog.at_level(logging.INFO):
        bridge._on_message(None, None, _message(topic, "PRESS", retain))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
    handler.assert_not_awaited()
    assert "reason_code=retained_command_ignored" in caplog.text


@pytest.mark.asyncio
async def test_live_press_reaches_the_command_handler():
    from transport.mqtt_client import MqttBridge

    bridge = MqttBridge()
    bridge._loop = asyncio.get_running_loop()
    handler = AsyncMock()
    bridge.set_command_handler(handler)
    bridge._on_message(None, None, _message(f"jeedom2ha/{BUTTON_ID}/cmd", "PRESS", False))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    handler.assert_awaited_once_with(f"jeedom2ha/{BUTTON_ID}/cmd", "PRESS")


# --- non-régression (AC7) -------------------------------------------------------------

@pytest.mark.asyncio
async def test_scenario_button_is_unchanged():
    scenario = ScenarioButtonMapper().map(JeedomScenario(id=20, name="Tout eteindre"))
    decision = PublicationDecision(should_publish=True, reason="sure", mapping_result=scenario,
                                   active_or_alive=True, discovery_published=True)
    sync, _bridge = _cmd_sync(_map(_button_eq()), scenario_publications={20: decision})
    assert await sync.handle_command_message("jeedom2ha/scenario_20/cmd", "PRESS") is True
    sync._execute_scenario_start.assert_awaited_once_with(20)
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,cmd_id", [("ON", 91222), ("OFF", 91223)])
async def test_switch_is_unchanged(payload, cmd_id):
    eq = _eq(SWITCH_ID, _switch_trio(91221))
    switch = _map(eq)
    assert switch.ha_entity_type == "switch"
    sync, _bridge = _cmd_sync(switch)
    assert await sync.handle_command_message(_command_topic(switch, eq), payload) is True
    sync._execute_exec_cmd.assert_awaited_once_with(cmd_id, {})
    assert await sync.handle_command_message(_command_topic(switch, eq), "PRESS") is False


@pytest.mark.asyncio
async def test_multi_entity_primary_switch_is_unchanged():
    eq, primary, _secondary = _multi_with_secondary_button()
    sync, _bridge = _cmd_sync(primary)
    assert await sync.handle_command_message(_command_topic(primary, eq), "ON") is True
    sync._execute_exec_cmd.assert_awaited_once_with(91212, {})


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,cmd_id", [("OPEN", 91231), ("CLOSE", 91232), ("STOP", 91233)])
async def test_cover_is_unchanged(payload, cmd_id):
    eq = _eq(COVER_ID, [
        _cmd(91230, "FLAP_STATE", "info", "numeric", name="Etat", value="0"),
        _cmd(91231, "FLAP_UP", name="Monter"),
        _cmd(91232, "FLAP_DOWN", name="Descendre"),
        _cmd(91233, "FLAP_STOP", name="Stop"),
    ])
    cover = _map(eq)
    assert cover.ha_entity_type == "cover"
    sync, _bridge = _cmd_sync(cover)
    assert await sync.handle_command_message(f"jeedom2ha/{COVER_ID}/set", payload) is True
    sync._execute_exec_cmd.assert_awaited_once_with(cmd_id, {})
    assert await sync.handle_command_message(f"jeedom2ha/{COVER_ID}/cmd", "PRESS") is False
