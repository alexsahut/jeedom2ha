"""Story 9.4 - FallbackMapper §11 dégradation élégante terminale.

Tests en isolation totale : aucune dépendance MQTT, daemon ou Jeedom.
"""

from __future__ import annotations

import pytest

from mapping.fallback import FallbackMapper
from models.cause_mapping import reason_code_to_cause
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot


def _make_snapshot() -> TopologySnapshot:
    return TopologySnapshot(timestamp="2026-05-06T00:00:00", objects={}, eq_logics={})


def _make_cmd(
    cmd_id: int = 1,
    type_: str = "info",
    sub_type: str = "string",
    generic_type: str | None = "GENERIC_INFO",
) -> JeedomCmd:
    return JeedomCmd(
        id=cmd_id,
        name=generic_type or "cmd",
        generic_type=generic_type,
        type=type_,
        sub_type=sub_type,
    )


def _make_eq(
    eq_id: int = 42,
    name: str = "Test eq",
    cmds: list | None = None,
) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=eq_id,
        name=name,
        eq_type_name="virtual",
        generic_type=None,
        cmds=cmds or [],
    )


# ─── Cas sensor ───────────────────────────────────────────────────────────────

def test_info_string_produces_sensor_ambiguous():
    fallback = FallbackMapper()
    eq = _make_eq(cmds=[_make_cmd(type_="info", sub_type="string", generic_type="GENERIC_INFO")])
    result = fallback.map(eq, _make_snapshot())

    assert result is not None
    assert result.ha_entity_type == "sensor"
    assert result.confidence == "ambiguous"
    assert result.reason_code == "fallback_sensor_default"


def test_info_color_produces_sensor_ambiguous():
    fallback = FallbackMapper()
    eq = _make_eq(cmds=[_make_cmd(type_="info", sub_type="color", generic_type="COLOR")])
    result = fallback.map(eq, _make_snapshot())

    assert result is not None
    assert result.ha_entity_type == "sensor"
    assert result.confidence == "ambiguous"
    assert result.reason_code == "fallback_sensor_default"


def test_info_with_action_info_wins():
    """Si eq a Info et Action, Info est prioritaire → sensor."""
    fallback = FallbackMapper()
    eq = _make_eq(cmds=[
        _make_cmd(cmd_id=1, type_="action", sub_type="slider", generic_type="VOLUME_SET"),
        _make_cmd(cmd_id=2, type_="info", sub_type="string", generic_type="GENERIC_INFO"),
    ])
    result = fallback.map(eq, _make_snapshot())

    assert result is not None
    assert result.ha_entity_type == "sensor"
    assert result.reason_code == "fallback_sensor_default"


def test_sensor_capabilities_has_state():
    fallback = FallbackMapper()
    eq = _make_eq(cmds=[_make_cmd(type_="info", sub_type="string", generic_type="GENERIC_INFO")])
    result = fallback.map(eq, _make_snapshot())

    assert result is not None
    assert result.capabilities.has_state is True
    assert result.reason_details == {}


def test_sensor_commands_use_generic_type_as_key():
    fallback = FallbackMapper()
    eq = _make_eq(cmds=[_make_cmd(type_="info", sub_type="string", generic_type="COLOR")])
    result = fallback.map(eq, _make_snapshot())

    assert result is not None
    assert "COLOR" in result.commands


def test_sensor_commands_fallback_key_when_no_generic_type():
    """generic_type=None → clé 'fallback' pour éviter {None: cmd}."""
    fallback = FallbackMapper()
    eq = _make_eq(cmds=[_make_cmd(type_="info", sub_type="string", generic_type=None)])
    result = fallback.map(eq, _make_snapshot())

    assert result is not None
    assert result.ha_entity_type == "sensor"
    assert "fallback" in result.commands


# ─── Cas button ───────────────────────────────────────────────────────────────

def test_action_slider_no_info_produces_button_ambiguous():
    fallback = FallbackMapper()
    eq = _make_eq(cmds=[_make_cmd(type_="action", sub_type="slider", generic_type="VOLUME_SET")])
    result = fallback.map(eq, _make_snapshot())

    assert result is not None
    assert result.ha_entity_type == "button"
    assert result.confidence == "ambiguous"
    assert result.reason_code == "fallback_button_default"


def test_action_string_no_info_produces_button_ambiguous():
    fallback = FallbackMapper()
    eq = _make_eq(cmds=[_make_cmd(type_="action", sub_type="string", generic_type="SET_TEXT")])
    result = fallback.map(eq, _make_snapshot())

    assert result is not None
    assert result.ha_entity_type == "button"
    assert result.confidence == "ambiguous"


def test_button_reason_details_contains_command_topic():
    fallback = FallbackMapper()
    eq_id = 12345
    eq = _make_eq(eq_id=eq_id, cmds=[
        _make_cmd(type_="action", sub_type="slider", generic_type="VOLUME_SET")
    ])
    result = fallback.map(eq, _make_snapshot())

    assert result is not None
    assert result.reason_details.get("command_topic") == f"jeedom2ha/{eq_id}/cmd"


def test_button_capabilities_has_on_off():
    fallback = FallbackMapper()
    eq = _make_eq(cmds=[_make_cmd(type_="action", sub_type="string", generic_type="SET_TEXT")])
    result = fallback.map(eq, _make_snapshot())

    assert result is not None
    assert result.capabilities.has_on_off is True


# ─── Cas None ─────────────────────────────────────────────────────────────────

def test_event_type_returns_none():
    """type='event' → ni Info ni Action → FallbackMapper retourne None."""
    fallback = FallbackMapper()
    eq = _make_eq(cmds=[_make_cmd(type_="event", sub_type="other", generic_type="JEEDOM_CHANNEL")])
    assert fallback.map(eq, _make_snapshot()) is None


def test_no_commands_returns_none():
    fallback = FallbackMapper()
    eq = _make_eq(cmds=[])
    assert fallback.map(eq, _make_snapshot()) is None


# ─── cause_mapping — 3 codes §11 ──────────────────────────────────────────────

def test_cause_fallback_sensor_default_no_action():
    code, label, action = reason_code_to_cause("fallback_sensor_default")
    assert code == "fallback_sensor_default"
    assert label is not None and "dégradation élégante" in label
    assert action is None


def test_cause_fallback_button_default_no_action():
    code, label, action = reason_code_to_cause("fallback_button_default")
    assert code == "fallback_button_default"
    assert label is not None
    assert action is None


def test_cause_no_projection_possible_no_action():
    code, label, action = reason_code_to_cause("no_projection_possible")
    assert code == "no_projection_possible"
    assert label is not None
    assert action is None
