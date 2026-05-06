"""Story 9.3 - ButtonMapper + publish_button + PRODUCT_SCOPE gate FR40/NFR10."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from discovery.publisher import DiscoveryPublisher
from discovery.registry import PublisherRegistry
from mapping.button import ButtonMapper
from models.mapping import SwitchCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from validation.ha_component_registry import validate_projection


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-05-06T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={eq.id: eq},
    )


def _eq_with_cmd(
    eq_id: int,
    name: str,
    cmd_id: int,
    generic_type: str,
    *,
    type_: str = "action",
    sub_type: str = "other",
) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=eq_id,
        name=name,
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            JeedomCmd(
                id=cmd_id,
                name=generic_type,
                generic_type=generic_type,
                type=type_,
                sub_type=sub_type,
            )
        ],
    )


def _eq_with_cmds(eq_id: int, name: str, cmds: list[JeedomCmd]) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=eq_id,
        name=name,
        object_id=1,
        eq_type_name="virtual",
        cmds=cmds,
    )


# ---------------------------------------------------------------------------
# ButtonMapper — cas nominaux (AC1)
# ---------------------------------------------------------------------------

def test_button_mapper_generic_action_nominal():
    eq = _eq_with_cmd(9000, "Scenario alarme", 90001, "GENERIC_ACTION")

    mapping = ButtonMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.ha_entity_type == "button"
    assert mapping.confidence == "sure"
    assert mapping.reason_code == "button_generic_action"
    assert mapping.capabilities == SwitchCapabilities(has_on_off=True)
    assert mapping.reason_details == {"command_topic": "jeedom2ha/9000/cmd"}


def test_button_mapper_media_pause_nominal():
    eq = _eq_with_cmd(9001, "Lecteur salon", 90011, "MEDIA_PAUSE")

    mapping = ButtonMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.ha_entity_type == "button"
    assert mapping.reason_code == "button_media_pause"
    assert mapping.reason_details == {"command_topic": "jeedom2ha/9001/cmd"}


def test_button_mapper_siren_on_nominal():
    eq = _eq_with_cmd(9002, "Sirene garage", 90021, "SIREN_ON")

    mapping = ButtonMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.reason_code == "button_siren_on"


# ---------------------------------------------------------------------------
# ButtonMapper — cas négatifs (AC1)
# ---------------------------------------------------------------------------

def test_button_mapper_rejects_action_slider():
    eq = _eq_with_cmd(9010, "Thermostat", 90101, "THERMOSTAT_SET_SETPOINT", sub_type="slider")

    mapping = ButtonMapper().map(eq, _snapshot(eq))

    assert mapping is None


def test_button_mapper_rejects_action_string():
    eq = _eq_with_cmd(9011, "Equipement texte", 90111, "GENERIC_ACTION", sub_type="string")

    mapping = ButtonMapper().map(eq, _snapshot(eq))

    assert mapping is None


def test_button_mapper_rejects_info_other():
    eq = _eq_with_cmd(9012, "Info equipement", 90121, "GENERIC_INFO", type_="info", sub_type="other")

    mapping = ButtonMapper().map(eq, _snapshot(eq))

    assert mapping is None


def test_button_mapper_rejects_action_other_without_generic_type():
    cmd = JeedomCmd(id=90131, name="sans_type", generic_type=None, type="action", sub_type="other")
    eq = _eq_with_cmds(9013, "Equipement sans type", [cmd])

    mapping = ButtonMapper().map(eq, _snapshot(eq))

    assert mapping is None


def test_button_mapper_returns_none_when_no_action_other_command():
    eq = _eq_with_cmd(9014, "Capteur temperature", 90141, "TEMPERATURE", type_="info", sub_type="numeric")

    mapping = ButtonMapper().map(eq, _snapshot(eq))

    assert mapping is None


# ---------------------------------------------------------------------------
# ButtonMapper — prise de première commande action "other" (AC4)
# ---------------------------------------------------------------------------

def test_button_mapper_picks_first_action_other_command():
    cmds = [
        JeedomCmd(id=90151, name="MEDIA_PAUSE", generic_type="MEDIA_PAUSE", type="action", sub_type="other"),
        JeedomCmd(id=90152, name="MEDIA_RESUME", generic_type="MEDIA_RESUME", type="action", sub_type="other"),
    ]
    eq = _eq_with_cmds(9015, "Lecteur multi-commandes", cmds)

    mapping = ButtonMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.reason_code == "button_media_pause"
    assert "MEDIA_PAUSE" in mapping.commands


# ---------------------------------------------------------------------------
# validate_projection — gate FR40/NFR10 (AC5)
# ---------------------------------------------------------------------------

def test_validate_projection_button_nominal():
    result = validate_projection("button", SwitchCapabilities(has_on_off=True))

    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_fields == []
    assert result.missing_capabilities == []


def test_validate_projection_button_failure_missing_command():
    result = validate_projection("button", SwitchCapabilities(has_on_off=False))

    assert result.is_valid is False
    assert result.reason_code == "ha_missing_command_topic"
    assert "command_topic" in result.missing_fields
    assert "has_command" in result.missing_capabilities


# ---------------------------------------------------------------------------
# publish_button (AC3)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_button_payload_required_fields():
    bridge = MagicMock()
    bridge.publish_message = MagicMock(return_value=True)
    publisher = DiscoveryPublisher(mqtt_bridge=bridge)

    eq = _eq_with_cmd(9020, "Scenario test", 90201, "GENERIC_ACTION")
    snap = _snapshot(eq)
    mapping = ButtonMapper().map(eq, snap)

    result = await publisher.publish_button(mapping, snap)

    assert result is True
    bridge.publish_message.assert_called_once()
    call_args = bridge.publish_message.call_args
    topic = call_args[0][0]
    payload = json.loads(call_args[0][1])

    assert topic == "homeassistant/button/jeedom2ha_9020/config"
    assert payload["command_topic"] == "jeedom2ha/9020/cmd"
    assert payload["platform"] == "mqtt"
    assert "name" in payload
    assert "unique_id" in payload
    assert "object_id" in payload
    assert "device" in payload
    assert "availability_topic" in payload


@pytest.mark.asyncio
async def test_publish_button_has_no_state_topic():
    bridge = MagicMock()
    bridge.publish_message = MagicMock(return_value=True)
    publisher = DiscoveryPublisher(mqtt_bridge=bridge)

    eq = _eq_with_cmd(9021, "Bouton test", 90211, "SIREN_ON")
    snap = _snapshot(eq)
    mapping = ButtonMapper().map(eq, snap)

    await publisher.publish_button(mapping, snap)

    payload = json.loads(bridge.publish_message.call_args[0][1])
    assert "state_topic" not in payload


@pytest.mark.asyncio
async def test_publish_button_topic_format():
    bridge = MagicMock()
    bridge.publish_message = MagicMock(return_value=True)
    publisher = DiscoveryPublisher(mqtt_bridge=bridge)

    eq = _eq_with_cmd(9022, "Bouton camera", 90221, "CAMERA_STOP")
    snap = _snapshot(eq)
    mapping = ButtonMapper().map(eq, snap)

    await publisher.publish_button(mapping, snap)

    topic = bridge.publish_message.call_args[0][0]
    assert topic == "homeassistant/button/jeedom2ha_9022/config"


# ---------------------------------------------------------------------------
# PublisherRegistry — known_types inclut button (AC3, AC4)
# ---------------------------------------------------------------------------

def test_known_types_includes_button():
    assert "button" in PublisherRegistry.known_types()
    assert PublisherRegistry.known_types() == [
        "light", "cover", "switch", "sensor", "binary_sensor", "button"
    ]
