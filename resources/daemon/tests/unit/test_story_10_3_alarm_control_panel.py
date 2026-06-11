"""Story 10.3 — AlarmControlPanelMapper et ouverture alarm_control_panel.

Tests en isolation totale : aucune dépendance MQTT, daemon ou Jeedom.
"""

from __future__ import annotations

from mapping.alarm_control_panel import AlarmControlPanelMapper
from models.mapping import AlarmCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot
from validation.ha_component_registry import validate_projection
from discovery.registry import PublisherRegistry
from discovery.publisher import DiscoveryPublisher
from unittest.mock import MagicMock


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
        eq_type_name="virtual",
        generic_type=None,
        cmds=cmds,
    )


def _alarm_eq_full() -> JeedomEqLogic:
    return _eq(
        12000,
        "Alarme maison",
        [
            _cmd(12001, "ALARM_STATE", type_="info", sub_type="binary"),
            _cmd(12002, "ALARM_ENABLE_STATE", type_="info", sub_type="binary"),
            _cmd(12003, "ALARM_ENABLE", type_="action", sub_type="other"),
            _cmd(12004, "ALARM_DISABLE", type_="action", sub_type="other"),
        ],
    )


def _alarm_eq_state_only() -> JeedomEqLogic:
    return _eq(
        12010,
        "Alarme etat seul",
        [
            _cmd(12011, "ALARM_STATE", type_="info", sub_type="binary"),
        ],
    )


def _alarm_eq_no_state() -> JeedomEqLogic:
    return _eq(
        12020,
        "Alarme sans etat",
        [
            _cmd(12021, "ALARM_ENABLE", type_="action", sub_type="other"),
            _cmd(12022, "ALARM_DISABLE", type_="action", sub_type="other"),
        ],
    )


def _alarm_eq_enable_state_primary() -> JeedomEqLogic:
    """eqLogic with only ALARM_ENABLE_STATE (no ALARM_STATE) — should still map."""
    return _eq(
        12030,
        "Alarme enable state",
        [
            _cmd(12031, "ALARM_ENABLE_STATE", type_="info", sub_type="binary"),
            _cmd(12032, "ALARM_ENABLE", type_="action", sub_type="other"),
        ],
    )


# ---------------------------------------------------------------------------
# AlarmControlPanelMapper — cas nominaux
# ---------------------------------------------------------------------------

def test_mapper_nominal_full_alarm_eq():
    """Cas nominal : eqLogic avec ALARM_STATE + ALARM_ENABLE + ALARM_DISABLE."""
    mapper = AlarmControlPanelMapper()
    eq = _alarm_eq_full()
    snapshot = _make_snapshot()

    result = mapper.map(eq, snapshot)

    assert result is not None
    assert result.ha_entity_type == "alarm_control_panel"
    assert result.confidence == "sure"
    assert result.reason_code == "alarm_control_panel_state_commands"
    assert result.jeedom_eq_id == 12000
    assert result.ha_unique_id == "jeedom2ha_eq_12000"
    assert result.ha_name == "Alarme maison"

    caps = result.capabilities
    assert isinstance(caps, AlarmCapabilities)
    assert caps.has_state is True
    assert caps.has_command is True

    assert "ALARM_STATE" in result.commands
    assert "ALARM_ENABLE" in result.commands
    assert "ALARM_DISABLE" in result.commands

    assert result.reason_details["state_topic"] == "jeedom2ha/12000/alarm/state"
    assert result.reason_details["command_topic"] == "jeedom2ha/12000/alarm/set"


def test_mapper_state_only_no_commands():
    """eqLogic avec ALARM_STATE uniquement — has_command=False."""
    mapper = AlarmControlPanelMapper()
    eq = _alarm_eq_state_only()
    snapshot = _make_snapshot()

    result = mapper.map(eq, snapshot)

    assert result is not None
    assert result.ha_entity_type == "alarm_control_panel"
    assert result.capabilities.has_state is True
    assert result.capabilities.has_command is False
    assert "ALARM_STATE" in result.commands
    assert "ALARM_ENABLE" not in result.commands
    assert "ALARM_DISABLE" not in result.commands


def test_mapper_returns_none_when_no_alarm_state():
    """eqLogic sans ALARM_STATE ni ALARM_ENABLE_STATE → mapper retourne None."""
    mapper = AlarmControlPanelMapper()
    eq = _alarm_eq_no_state()
    snapshot = _make_snapshot()

    result = mapper.map(eq, snapshot)

    assert result is None


def test_mapper_alarm_enable_state_as_primary():
    """ALARM_ENABLE_STATE seul suffit comme signal primaire."""
    mapper = AlarmControlPanelMapper()
    eq = _alarm_eq_enable_state_primary()
    snapshot = _make_snapshot()

    result = mapper.map(eq, snapshot)

    assert result is not None
    assert result.ha_entity_type == "alarm_control_panel"
    assert result.capabilities.has_state is True
    assert result.capabilities.has_command is True
    assert "ALARM_ENABLE_STATE" in result.commands


# ---------------------------------------------------------------------------
# validate_projection — alarm_control_panel
# ---------------------------------------------------------------------------

def test_validate_projection_alarm_nominal():
    """AlarmCapabilities(has_state=True, has_command=True) → is_valid=True."""
    result = validate_projection("alarm_control_panel", AlarmCapabilities(has_state=True, has_command=True))
    assert result.is_valid is True
    assert result.reason_code is None
    assert result.missing_fields == []
    assert result.missing_capabilities == []


def test_validate_projection_alarm_no_state():
    """AlarmCapabilities(has_state=False, has_command=True) → is_valid=False, ha_missing_state_topic."""
    result = validate_projection("alarm_control_panel", AlarmCapabilities(has_state=False, has_command=True))
    assert result.is_valid is False
    assert result.reason_code == "ha_missing_state_topic"
    assert "has_state" in result.missing_capabilities
    assert "state_topic" in result.missing_fields


def test_validate_projection_alarm_no_command():
    """AlarmCapabilities(has_state=True, has_command=False) → is_valid=False, ha_missing_command_topic."""
    result = validate_projection("alarm_control_panel", AlarmCapabilities(has_state=True, has_command=False))
    assert result.is_valid is False
    assert result.reason_code == "ha_missing_command_topic"
    assert "has_command" in result.missing_capabilities
    assert "command_topic" in result.missing_fields


# ---------------------------------------------------------------------------
# PublisherRegistry — alarm_control_panel registered
# ---------------------------------------------------------------------------

def test_publisher_registry_includes_alarm_control_panel():
    """PublisherRegistry.known_types() inclut alarm_control_panel (Story 10.3)."""
    assert "alarm_control_panel" in PublisherRegistry.known_types()


def test_publisher_registry_resolves_alarm_control_panel():
    """registry.resolve('alarm_control_panel') retourne publish_alarm_control_panel."""
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(mqtt_bridge=mqtt_bridge)
    registry = PublisherRegistry(publisher)

    resolved = registry.resolve("alarm_control_panel")

    assert resolved.__self__ is publisher
    assert resolved.__func__ is DiscoveryPublisher.publish_alarm_control_panel
