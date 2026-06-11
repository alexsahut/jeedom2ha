"""Story 10.5 — Parité génériques alarme : ALARM_ARMED / ALARM_RELEASED.

Vérifie que le mapper reconnaît les génériques natifs du plugin alarme Jeedom
(ALARM_ARMED / ALARM_RELEASED) en plus des génériques virtuels (ALARM_ENABLE / ALARM_DISABLE).
Non-régression Story 10.3 incluse.
"""

from __future__ import annotations

import pytest

from mapping.alarm_control_panel import AlarmControlPanelMapper
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot


def _make_snapshot() -> TopologySnapshot:
    return TopologySnapshot(timestamp="2026-06-09T00:00:00Z", objects={}, eq_logics={})


def _cmd(
    cmd_id: int,
    generic_type: str,
    type_: str = "action",
    sub_type: str = "other",
) -> JeedomCmd:
    return JeedomCmd(
        id=cmd_id,
        name=generic_type,
        generic_type=generic_type,
        type=type_,
        sub_type=sub_type,
    )


def _eq(eq_id: int, name: str, cmds: list) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=eq_id,
        name=name,
        eq_type_name="alarm",
        generic_type=None,
        cmds=cmds,
    )


def _alarm_eq_armed_released_full() -> JeedomEqLogic:
    """Fixture réaliste box réelle : eq_id=230, plugin alarme natif Jeedom."""
    return _eq(
        230,
        "Alarme maison",
        [
            _cmd(2301, "ALARM_ENABLE_STATE", type_="info", sub_type="binary"),
            _cmd(2302, "ALARM_STATE", type_="info", sub_type="binary"),
            _cmd(2303, "ALARM_ARMED", type_="action", sub_type="other"),
            _cmd(2304, "ALARM_RELEASED", type_="action", sub_type="other"),
            _cmd(2305, "ALARM_SET_MODE", type_="action", sub_type="other"),
            _cmd(2306, "ALARM_MODE", type_="info", sub_type="string"),
        ],
    )


def _alarm_eq_armed_only() -> JeedomEqLogic:
    """ALARM_ENABLE_STATE + ALARM_ARMED uniquement (sans ALARM_RELEASED)."""
    return _eq(
        231,
        "Alarme maison armed only",
        [
            _cmd(2311, "ALARM_ENABLE_STATE", type_="info", sub_type="binary"),
            _cmd(2312, "ALARM_ARMED", type_="action", sub_type="other"),
        ],
    )


def _alarm_eq_released_only() -> JeedomEqLogic:
    """ALARM_ENABLE_STATE + ALARM_RELEASED uniquement (sans ALARM_ARMED)."""
    return _eq(
        232,
        "Alarme maison released only",
        [
            _cmd(2321, "ALARM_ENABLE_STATE", type_="info", sub_type="binary"),
            _cmd(2322, "ALARM_RELEASED", type_="action", sub_type="other"),
        ],
    )


def _alarm_eq_both_generics() -> JeedomEqLogic:
    """ALARM_ENABLE_STATE + ALARM_ENABLE + ALARM_ARMED (les deux présents — ALARM_ENABLE prioritaire)."""
    return _eq(
        233,
        "Alarme maison both arm generics",
        [
            _cmd(2331, "ALARM_ENABLE_STATE", type_="info", sub_type="binary"),
            _cmd(2332, "ALARM_ENABLE", type_="action", sub_type="other"),
            _cmd(2333, "ALARM_ARMED", type_="action", sub_type="other"),
            _cmd(2334, "ALARM_DISABLE", type_="action", sub_type="other"),
            _cmd(2335, "ALARM_RELEASED", type_="action", sub_type="other"),
        ],
    )


# ---------------------------------------------------------------------------
# AC1 — ALARM_ARMED reconnu comme commande d'armement
# ---------------------------------------------------------------------------

def test_armed_cmd_detected_as_arm():
    """AC1 : ALARM_ARMED → commande armer détectée, has_command=True."""
    mapper = AlarmControlPanelMapper()
    eq = _alarm_eq_armed_only()
    result = mapper.map(eq, _make_snapshot())

    assert result is not None
    assert result.ha_entity_type == "alarm_control_panel"
    assert result.capabilities.has_state is True
    assert result.capabilities.has_command is True
    assert "ALARM_ARMED" in result.commands


# ---------------------------------------------------------------------------
# AC2 — ALARM_RELEASED reconnu comme commande de désarmement
# ---------------------------------------------------------------------------

def test_released_cmd_detected_as_disarm():
    """AC2 : ALARM_RELEASED → commande désarmer détectée, has_command=True."""
    mapper = AlarmControlPanelMapper()
    eq = _alarm_eq_released_only()
    result = mapper.map(eq, _make_snapshot())

    assert result is not None
    assert result.capabilities.has_state is True
    assert result.capabilities.has_command is True
    assert "ALARM_RELEASED" in result.commands


# ---------------------------------------------------------------------------
# AC3 — Mapping nominal complet sur fixture réaliste box réelle
# ---------------------------------------------------------------------------

def test_nominal_full_armed_released():
    """AC3 : fixture box réelle eq_id=230 → mapping complet alarm_control_panel."""
    mapper = AlarmControlPanelMapper()
    eq = _alarm_eq_armed_released_full()
    result = mapper.map(eq, _make_snapshot())

    assert result is not None
    assert result.ha_entity_type == "alarm_control_panel"
    assert result.confidence == "sure"
    assert result.jeedom_eq_id == 230
    assert result.ha_unique_id == "jeedom2ha_eq_230"
    assert result.ha_name == "Alarme maison"

    caps = result.capabilities
    assert caps.has_state is True
    assert caps.has_command is True

    # État primaire
    assert "ALARM_ENABLE_STATE" in result.commands or "ALARM_STATE" in result.commands

    # Commandes armer/désarmer via fallback génériques
    assert "ALARM_ARMED" in result.commands
    assert "ALARM_RELEASED" in result.commands

    # Topics MQTT
    assert result.reason_details["state_topic"] == "jeedom2ha/230/alarm/state"
    assert result.reason_details["command_topic"] == "jeedom2ha/230/alarm/set"


# ---------------------------------------------------------------------------
# AC5 — Priorité : ALARM_ENABLE avant ALARM_ARMED quand les deux sont présents
# ---------------------------------------------------------------------------

def test_alarm_enable_takes_priority_over_armed():
    """AC5 : si ALARM_ENABLE ET ALARM_ARMED présents, ALARM_ENABLE est préféré."""
    mapper = AlarmControlPanelMapper()
    eq = _alarm_eq_both_generics()
    result = mapper.map(eq, _make_snapshot())

    assert result is not None
    assert "ALARM_ENABLE" in result.commands
    assert "ALARM_ARMED" not in result.commands
    assert "ALARM_DISABLE" in result.commands
    assert "ALARM_RELEASED" not in result.commands


# ---------------------------------------------------------------------------
# AC4 — Non-régression Story 10.3 : ALARM_ENABLE / ALARM_DISABLE toujours reconnus
# ---------------------------------------------------------------------------

def _alarm_eq_legacy_full() -> JeedomEqLogic:
    """Fixture 10.3 inchangée : ALARM_STATE + ALARM_ENABLE + ALARM_DISABLE."""
    return _eq(
        12000,
        "Alarme maison (legacy)",
        [
            _cmd(12001, "ALARM_STATE", type_="info", sub_type="binary"),
            _cmd(12003, "ALARM_ENABLE", type_="action", sub_type="other"),
            _cmd(12004, "ALARM_DISABLE", type_="action", sub_type="other"),
        ],
    )


def test_non_regression_alarm_enable_disable_still_works():
    """AC4 : ALARM_ENABLE / ALARM_DISABLE (Story 10.3) toujours reconnus."""
    mapper = AlarmControlPanelMapper()
    eq = _alarm_eq_legacy_full()
    result = mapper.map(eq, _make_snapshot())

    assert result is not None
    assert result.capabilities.has_state is True
    assert result.capabilities.has_command is True
    assert "ALARM_STATE" in result.commands
    assert "ALARM_ENABLE" in result.commands
    assert "ALARM_DISABLE" in result.commands
