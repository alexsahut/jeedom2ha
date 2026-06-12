"""Story 10.7 - PresenceSwitchMapper : PRESENCE + SET_ON + SET_OFF → switch."""

from __future__ import annotations

from unittest.mock import MagicMock

from mapping.binary_sensor import BinarySensorMapper
from mapping.presence_switch import PresenceSwitchMapper
from mapping.registry import MapperRegistry
from models.mapping import SwitchCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-06-11T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={eq.id: eq},
    )


def _cmd(cmd_id: int, name: str, generic_type: str, type_: str, sub_type: str = "") -> JeedomCmd:
    return JeedomCmd(
        id=cmd_id,
        name=name,
        generic_type=generic_type,
        type=type_,
        sub_type=sub_type,
    )


def _eq_presence_actionnable(eq_id: int = 9700, name: str = "iPhone Alex") -> JeedomEqLogic:
    """Équipement PRESENCE + SET_ON + SET_OFF — cas nominal switch."""
    return JeedomEqLogic(
        id=eq_id,
        name=name,
        object_id=1,
        eq_type_name="mobile",
        cmds=[
            _cmd(97001, "PRESENCE", "PRESENCE", "info", "binary"),
            _cmd(97002, "Présent", "SET_ON", "action", "other"),
            _cmd(97003, "Absent", "SET_OFF", "action", "other"),
        ],
    )


def _eq_presence_readonly(eq_id: int = 8000, name: str = "Detecteur salon") -> JeedomEqLogic:
    """Équipement PRESENCE seule, sans actions — fallback binary_sensor."""
    return JeedomEqLogic(
        id=eq_id,
        name=name,
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            _cmd(80001, "PRESENCE", "PRESENCE", "info", "binary"),
        ],
    )


# ---------------------------------------------------------------------------
# AC1 — Cas nominal : PRESENCE + SET_ON + SET_OFF → switch
# ---------------------------------------------------------------------------

def test_presence_switch_mapper_nominal():
    eq = _eq_presence_actionnable()
    mapping = PresenceSwitchMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.ha_entity_type == "switch"
    assert mapping.confidence == "sure"
    assert mapping.reason_code == "presence_switch_set_on_off"
    assert mapping.jeedom_eq_id == 9700
    assert mapping.ha_unique_id == "jeedom2ha_eq_9700"
    assert mapping.ha_name == "iPhone Alex"
    assert "PRESENCE" in mapping.commands
    assert "SET_ON" in mapping.commands
    assert "SET_OFF" in mapping.commands
    assert isinstance(mapping.capabilities, SwitchCapabilities)
    assert mapping.capabilities.has_on_off is True
    assert mapping.capabilities.has_state is True
    assert mapping.capabilities.on_off_confidence == "sure"
    assert mapping.capabilities.device_class is None


# ---------------------------------------------------------------------------
# AC2 — Fallback : PRESENCE seule → PresenceSwitchMapper retourne None
# ---------------------------------------------------------------------------

def test_presence_switch_mapper_readonly_returns_none():
    eq = _eq_presence_readonly()
    mapping = PresenceSwitchMapper().map(eq, _snapshot(eq))
    assert mapping is None


def test_presence_readonly_falls_back_to_binary_sensor():
    """BinarySensorMapper reprend le relais sur PRESENCE seule."""
    eq = _eq_presence_readonly()
    snap = _snapshot(eq)

    assert PresenceSwitchMapper().map(eq, snap) is None
    fallback = BinarySensorMapper().map(eq, snap)
    assert fallback is not None
    assert fallback.ha_entity_type == "binary_sensor"
    assert fallback.reason_code == "binary_sensor_presence"


# ---------------------------------------------------------------------------
# AC2 — Garde-fous : SET_ON seul ou SET_OFF seul → None
# ---------------------------------------------------------------------------

def test_presence_switch_mapper_set_on_only_returns_none():
    eq = JeedomEqLogic(
        id=9701,
        name="iPhone Bob",
        object_id=1,
        eq_type_name="mobile",
        cmds=[
            _cmd(97011, "PRESENCE", "PRESENCE", "info", "binary"),
            _cmd(97012, "Présent", "SET_ON", "action", "other"),
        ],
    )
    assert PresenceSwitchMapper().map(eq, _snapshot(eq)) is None


def test_presence_switch_mapper_set_off_only_returns_none():
    eq = JeedomEqLogic(
        id=9702,
        name="iPhone Carol",
        object_id=1,
        eq_type_name="mobile",
        cmds=[
            _cmd(97021, "PRESENCE", "PRESENCE", "info", "binary"),
            _cmd(97022, "Absent", "SET_OFF", "action", "other"),
        ],
    )
    assert PresenceSwitchMapper().map(eq, _snapshot(eq)) is None


def test_presence_switch_mapper_no_presence_cmd_returns_none():
    """Pas de commande PRESENCE info binary → None."""
    eq = JeedomEqLogic(
        id=9703,
        name="Autre eq",
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            _cmd(97031, "Présent", "SET_ON", "action", "other"),
            _cmd(97032, "Absent", "SET_OFF", "action", "other"),
        ],
    )
    assert PresenceSwitchMapper().map(eq, _snapshot(eq)) is None


# ---------------------------------------------------------------------------
# AC3 — Ordre dans le registry : PresenceSwitchMapper avant BinarySensorMapper
# ---------------------------------------------------------------------------

def test_registry_presence_switch_before_binary_sensor():
    reg = MapperRegistry()
    mapper_types = [type(m).__name__ for m in reg.mappers]

    assert "PresenceSwitchMapper" in mapper_types, "PresenceSwitchMapper absent du registry"
    assert "BinarySensorMapper" in mapper_types, "BinarySensorMapper absent du registry"

    idx_presence = mapper_types.index("PresenceSwitchMapper")
    idx_binary = mapper_types.index("BinarySensorMapper")
    assert idx_presence < idx_binary, (
        f"PresenceSwitchMapper (slot {idx_presence}) doit précéder "
        f"BinarySensorMapper (slot {idx_binary})"
    )


def test_registry_switch_before_presence_switch():
    """SwitchMapper (ENERGY_*) doit précéder PresenceSwitchMapper."""
    reg = MapperRegistry()
    mapper_types = [type(m).__name__ for m in reg.mappers]

    idx_switch = mapper_types.index("SwitchMapper")
    idx_presence = mapper_types.index("PresenceSwitchMapper")
    assert idx_switch < idx_presence, (
        f"SwitchMapper (slot {idx_switch}) doit précéder "
        f"PresenceSwitchMapper (slot {idx_presence})"
    )


# ---------------------------------------------------------------------------
# AC1/AC3 — Dispatch registry end-to-end : équipement PRESENCE actionnable
# ---------------------------------------------------------------------------

def test_registry_dispatches_presence_actionnable_to_switch():
    eq = _eq_presence_actionnable()
    mapping = MapperRegistry().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.ha_entity_type == "switch"
    assert mapping.reason_code == "presence_switch_set_on_off"


def test_registry_dispatches_presence_readonly_to_binary_sensor():
    eq = _eq_presence_readonly()
    mapping = MapperRegistry().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.ha_entity_type == "binary_sensor"


# ---------------------------------------------------------------------------
# AC1 — CommandSynchronizer : SET_ON / SET_OFF routés sur channel /set
# (fix code-review : command.py ne connaissait que LIGHT_ON/ENERGY_ON)
# ---------------------------------------------------------------------------

def test_command_synchronizer_set_on_routed_for_presence_switch():
    """CommandSynchronizer doit router ON → SET_ON pour un presence_switch."""
    from sync.command import CommandSynchronizer

    eq = _eq_presence_actionnable()
    mapping = PresenceSwitchMapper().map(eq, _snapshot(eq))
    assert mapping is not None

    decision = MagicMock()
    decision.state_topic = f"jeedom2ha/{eq.id}/state"

    app = MagicMock()
    app.get.return_value = None

    sync = CommandSynchronizer(app, MagicMock(), "http://localhost/api")
    from sync.command import ParsedTopic
    translation, error = sync._translate_command(mapping, ParsedTopic(eq_id=eq.id, channel="set"), "ON")

    assert error is None, f"Unexpected error: {error}"
    assert translation is not None
    assert translation.cmd_id == 97002  # SET_ON cmd id
    assert translation.command_family == "on_off"
    assert translation.optimistic_state_payload == "ON"


def test_command_synchronizer_set_off_routed_for_presence_switch():
    """CommandSynchronizer doit router OFF → SET_OFF pour un presence_switch."""
    from sync.command import CommandSynchronizer

    eq = _eq_presence_actionnable()
    mapping = PresenceSwitchMapper().map(eq, _snapshot(eq))
    assert mapping is not None

    decision = MagicMock()
    decision.state_topic = f"jeedom2ha/{eq.id}/state"

    app = MagicMock()
    app.get.return_value = None

    sync = CommandSynchronizer(app, MagicMock(), "http://localhost/api")
    from sync.command import ParsedTopic
    translation, error = sync._translate_command(mapping, ParsedTopic(eq_id=eq.id, channel="set"), "OFF")

    assert error is None, f"Unexpected error: {error}"
    assert translation is not None
    assert translation.cmd_id == 97003  # SET_OFF cmd id
    assert translation.command_family == "on_off"
    assert translation.optimistic_state_payload == "OFF"
