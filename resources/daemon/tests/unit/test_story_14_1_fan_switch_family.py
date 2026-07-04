"""Story 14.1 - Généralisation family="FAN" dans SwitchMapper.

Le trio FAN_STATE/FAN_ON/FAN_OFF (ex: eq67 pompe de filtration piscine,
plugin `pool`) est publié en `switch` HA, symétriquement au trio historique
SWITCH_STATE/SWITCH_ON/SWITCH_OFF (Story 8.x / 11.3).
"""

from __future__ import annotations

from unittest.mock import MagicMock

from mapping.binary_sensor import BinarySensorMapper
from mapping.switch import SwitchMapper
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-07-04T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Piscine")},
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


def _eq_fan_trio(eq_id: int = 67) -> JeedomEqLogic:
    """eq67 : pompe de filtration piscine, trio FAN_STATE/FAN_ON/FAN_OFF."""
    return JeedomEqLogic(
        id=eq_id,
        name="Filtration",
        object_id=1,
        eq_type_name="pool",
        cmds=[
            _cmd(382, "Filtration", "FAN_STATE", "info", "binary"),
            _cmd(383, "Filtration On", "FAN_ON", "action", "other"),
            _cmd(384, "Filtration Off", "FAN_OFF", "action", "other"),
        ],
    )


def _eq_switch_trio(eq_id: int = 583) -> JeedomEqLogic:
    """Groupe SWITCH_* historique — utilisé pour la non-régression."""
    return JeedomEqLogic(
        id=eq_id,
        name="Prise IQ EV",
        object_id=1,
        eq_type_name="zwave",
        cmds=[
            _cmd(5830, "Prise IQ EV", "SWITCH_STATE", "info", "binary"),
            _cmd(5831, "Prise IQ EV On", "SWITCH_ON", "action", "other"),
            _cmd(5832, "Prise IQ EV Off", "SWITCH_OFF", "action", "other"),
        ],
    )


# ---------------------------------------------------------------------------
# AC1/AC2 — trio FAN_* → switch, reason_code switch_fan_on_off_state
# ---------------------------------------------------------------------------

def test_fan_trio_maps_to_switch():
    mapper = SwitchMapper()
    eq = _eq_fan_trio()
    results = mapper.map_all(eq, _snapshot(eq))

    assert len(results) == 1
    mapping = results[0]
    assert mapping.ha_entity_type == "switch"
    assert mapping.confidence == "probable"
    assert mapping.reason_code == "switch_fan_on_off_state"
    assert "FAN_STATE" in mapping.commands
    assert "FAN_ON" in mapping.commands
    assert "FAN_OFF" in mapping.commands
    assert mapping.commands["FAN_STATE"].id == 382


def test_fan_trio_topics_follow_cmd_group_pattern():
    mapper = SwitchMapper()
    eq = _eq_fan_trio()
    mapping = mapper.map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.reason_details["state_topic"] == f"jeedom2ha/{eq.id}/382/state"
    assert mapping.reason_details["command_topic"] == f"jeedom2ha/{eq.id}/382/set"
    assert mapping.ha_unique_id == f"jeedom2ha_eq_{eq.id}_cmd_382"


def test_fan_incomplete_trio_returns_no_switch():
    """FAN_STATE seul (sans FAN_ON/FAN_OFF) ne doit pas produire de switch."""
    mapper = SwitchMapper()
    eq = JeedomEqLogic(
        id=68,
        name="Filtration incomplète",
        object_id=1,
        eq_type_name="pool",
        cmds=[_cmd(390, "Filtration", "FAN_STATE", "info", "binary")],
    )
    results = mapper.map_all(eq, _snapshot(eq))
    assert results == []


# ---------------------------------------------------------------------------
# AC4 — Non-régression : groupe SWITCH_* historique inchangé
# ---------------------------------------------------------------------------

def test_switch_trio_still_maps_with_switch_family():
    mapper = SwitchMapper()
    eq = _eq_switch_trio()
    results = mapper.map_all(eq, _snapshot(eq))

    assert len(results) == 1
    mapping = results[0]
    assert mapping.ha_entity_type == "switch"
    assert mapping.reason_code == "switch_switch_on_off_state"


def test_mixed_switch_and_fan_groups_both_mapped_independently():
    """Un eqLogic avec un groupe SWITCH_* ET un groupe FAN_* distincts (noms différents)
    doit produire deux MappingResult, chacun dans sa propre famille."""
    mapper = SwitchMapper()
    eq = JeedomEqLogic(
        id=700,
        name="Multi",
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            _cmd(1, "Prise A", "SWITCH_STATE", "info", "binary"),
            _cmd(2, "Prise A On", "SWITCH_ON", "action", "other"),
            _cmd(3, "Prise A Off", "SWITCH_OFF", "action", "other"),
            _cmd(4, "Pompe B", "FAN_STATE", "info", "binary"),
            _cmd(5, "Pompe B On", "FAN_ON", "action", "other"),
            _cmd(6, "Pompe B Off", "FAN_OFF", "action", "other"),
        ],
    )
    results = mapper.map_all(eq, _snapshot(eq))
    reason_codes = sorted(r.reason_code for r in results)
    assert reason_codes == ["switch_fan_on_off_state", "switch_switch_on_off_state"]


# ---------------------------------------------------------------------------
# AC3 — Anti-doublon binary_sensor : FAN_STATE consommé par le switch n'est
# jamais republié en binary_sensor
# ---------------------------------------------------------------------------

def test_fan_state_not_duplicated_as_binary_sensor():
    eq = JeedomEqLogic(
        id=67,
        name="Filtration",
        object_id=1,
        eq_type_name="pool",
        cmds=[
            _cmd(382, "Filtration", "FAN_STATE", "info", "binary"),
            _cmd(383, "Filtration On", "FAN_ON", "action", "other"),
            _cmd(384, "Filtration Off", "FAN_OFF", "action", "other"),
            # Deuxième commande binaire "vraie" pour déclencher le mode multi-domaine
            _cmd(385, "Alerte filtre", "FILTER_CLEAN_STATE", "info", "binary"),
        ],
    )
    binary_results = BinarySensorMapper().map_all(eq, _snapshot(eq))
    fan_state_ids = {r.reason_details.get("cmd_id") for r in binary_results}
    assert 382 not in fan_state_ids
    # La commande binaire non-switch (FILTER_CLEAN_STATE) reste publiée normalement
    assert any(r.reason_details.get("cmd_id") == 385 for r in binary_results)


# ---------------------------------------------------------------------------
# AC5 — CommandSynchronizer : FAN_ON / FAN_OFF routés sur channel /{cmd_id}/set
# ---------------------------------------------------------------------------

def test_command_synchronizer_routes_fan_on():
    from sync.command import CommandSynchronizer, ParsedTopic

    eq = _eq_fan_trio()
    mapping = SwitchMapper().map(eq, _snapshot(eq))
    assert mapping is not None

    app = MagicMock()
    app.get.return_value = None
    sync = CommandSynchronizer(app, MagicMock(), "http://localhost/api")

    translation, error = sync._translate_command(
        mapping, ParsedTopic(eq_id=eq.id, cmd_id=382, channel="set"), "ON"
    )

    assert error is None, f"Unexpected error: {error}"
    assert translation is not None
    assert translation.cmd_id == 383  # FAN_ON cmd id
    assert translation.command_family == "on_off"
    assert translation.optimistic_state_payload == "ON"


def test_command_synchronizer_routes_fan_off():
    from sync.command import CommandSynchronizer, ParsedTopic

    eq = _eq_fan_trio()
    mapping = SwitchMapper().map(eq, _snapshot(eq))
    assert mapping is not None

    app = MagicMock()
    app.get.return_value = None
    sync = CommandSynchronizer(app, MagicMock(), "http://localhost/api")

    translation, error = sync._translate_command(
        mapping, ParsedTopic(eq_id=eq.id, cmd_id=382, channel="set"), "OFF"
    )

    assert error is None, f"Unexpected error: {error}"
    assert translation is not None
    assert translation.cmd_id == 384  # FAN_OFF cmd id
    assert translation.command_family == "on_off"
    assert translation.optimistic_state_payload == "OFF"
