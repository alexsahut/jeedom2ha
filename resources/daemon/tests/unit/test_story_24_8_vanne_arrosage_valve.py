"""Story 24.8 — vanne d'arrosage projetée en ``valve`` (décisions D1 à D6).

Identifiants et noms synthétiques uniquement (CC-48). Couvre : ouverture gouvernée de
``valve`` (AR13 : registre, cas nominal et cas d'échec, PRODUCT_SCOPE), mono-vanne, deux
zones sur un même équipement (D2, appariement par ordre d'id), trio incomplet ou ambigu
(aucune vanne, projection d'avant), vanne ajoutée aux entités existantes, payload
(D4/D5, ``default_entity_id`` 22-1), traduction des ordres OPEN/CLOSE, état 0/1 avec
``invertBinary``, override pe-epic-16, export de décision et non-régression switch/cover.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

import transport.http_server as http_server
from discovery.publisher import DiscoveryPublisher
from discovery.registry import PublisherRegistry
from export import decision_export
from mapping.overrides import apply_type_override, save_override
from mapping.registry import MapperRegistry, resolve_expected_ha
from mapping.valve import ValveMapper, valve_trios
from models.mapping import (
    CoverCapabilities,
    PublicationDecision,
    SensorCapabilities,
    SwitchCapabilities,
    ValveCapabilities,
)
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from sync import readback
from sync.command import CommandSynchronizer, CommandTranslation
from sync.state import StateSynchronizer
from validation.ha_component_registry import (
    HA_COMPONENT_REGISTRY,
    PRODUCT_SCOPE,
    validate_projection,
)

MONO_ID = 8001     # vanne seule (virtuel)
ZONES_ID = 8002    # deux zones sur le même équipement
MIXED_ID = 8003    # vanne + une mesure sans type générique déjà publiée en sensor


def _cmd(cmd_id, generic_type, type_="action", sub_type="other", value=None, unit=None,
         invert=False, name=None):
    return JeedomCmd(id=cmd_id, name=name or f"Cmd {cmd_id}", generic_type=generic_type,
                     type=type_, sub_type=sub_type, current_value=value, unit=unit,
                     invert_binary=invert)


def _state(cmd_id, family="IRRIG", value="0", invert=False):
    return _cmd(cmd_id, f"{family}_STATE", "info", "binary", value, invert=invert,
                name=f"Etat {cmd_id}")


def _eq(eq_id, cmds, name=None, eq_type="virtual"):
    return JeedomEqLogic(id=eq_id, name=name or f"Equipement {eq_id}", object_id=1,
                         eq_type_name=eq_type, cmds=cmds)


def _snapshot(*eqs):
    return TopologySnapshot(
        timestamp="2026-11-11T00:00:00+00:00",
        objects={1: JeedomObject(id=1, name="Jardin")},
        eq_logics={eq.id: eq for eq in eqs},
    )


def _mono_eq(family="IRRIG", value="0", invert=False):
    """Vanne seule : STATE / ON / OFF, ids non triés comme sur un virtuel réel."""
    return _eq(MONO_ID, [
        _cmd(80015, f"{family}_ON"),
        _cmd(80018, f"{family}_OFF"),
        _state(80019, family, value, invert),
    ])


def _zones_eq():
    """Deux zones : trios 80021-80023 et 80024-80026 (STATE / ON / OFF)."""
    return _eq(ZONES_ID, [
        _state(80021), _cmd(80022, "IRRIG_ON"), _cmd(80023, "IRRIG_OFF"),
        _state(80024, value="1"), _cmd(80025, "IRRIG_ON"), _cmd(80026, "IRRIG_OFF"),
    ], eq_type="zwavejs")


def _power_cmd():
    return _cmd(80030, None, "info", "numeric", "12", unit="W", name="Puissance")


def _mixed_eq():
    """Une vanne + une mesure de puissance sans type générique (publiée en sensor)."""
    return _eq(MIXED_ID, [
        _state(80031), _cmd(80032, "IRRIG_ON"), _cmd(80033, "IRRIG_OFF"), _power_cmd(),
    ], eq_type="zwavejs")


def _all(eq):
    return MapperRegistry().map_all(eq, _snapshot(eq))


def _map(eq):
    return MapperRegistry().map(eq, _snapshot(eq))


def _pre_story_projection(eq):
    """Projection d'avant la story : la même chaîne de mappers, sans la passe vanne."""
    registry = MapperRegistry()
    return registry._apply_entity_name_rule(eq, registry._map_all_raw(eq, _snapshot(eq)))


def _shape(result):
    return (result.ha_entity_type, result.confidence, result.reason_code, result.ha_unique_id,
            result.ha_name, sorted((k, c.id) for k, c in result.commands.items()),
            result.reason_details)


def _payload(mapping, eq):
    return DiscoveryPublisher(MagicMock()).build_discovery_payload(mapping, _snapshot(eq))


class _Bridge:
    def __init__(self):
        self.is_connected = True
        self.published = []

    def publish_message(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return True


def _decision(mapping, state_topic=None):
    decision = PublicationDecision(
        should_publish=True, reason="sure", mapping_result=mapping,
        state_topic=state_topic or (mapping.reason_details or {}).get("state_topic"),
        active_or_alive=True, discovery_published=True,
    )
    mapping.publication_decision_ref = decision
    return decision


# --- AC1 : ouverture gouvernée (AR13) -------------------------------------------------

def test_valve_is_known_and_open_in_the_same_increment():
    assert HA_COMPONENT_REGISTRY["valve"] == {
        "required_fields": ["state_topic", "command_topic", "platform", "availability"],
        "required_capabilities": ["has_state", "has_command"],
    }
    assert PRODUCT_SCOPE[-1] == "valve"
    assert PublisherRegistry.known_types()[-1] == "valve"


def test_validate_projection_nominal_case():
    validity = validate_projection("valve", ValveCapabilities(has_open_close=True, has_state=True))
    assert validity.is_valid is True
    assert validity.reason_code is None


@pytest.mark.parametrize("caps,reason,missing", [
    (ValveCapabilities(has_open_close=True, has_state=False),
     "ha_missing_state_topic", ["has_state"]),
    (ValveCapabilities(has_open_close=False, has_state=True),
     "ha_missing_command_topic", ["has_command"]),
    (ValveCapabilities(), "ha_missing_state_topic", ["has_state", "has_command"]),
])
def test_validate_projection_failure_cases(caps, reason, missing):
    validity = validate_projection("valve", caps)
    assert validity.is_valid is False
    assert validity.reason_code == reason
    assert validity.missing_capabilities == missing


# --- AC2 / D2 : mapping -------------------------------------------------------------

def test_single_valve_equipment():
    results = _all(_mono_eq())
    assert len(results) == 1
    valve = results[0]
    assert valve.ha_entity_type == "valve"
    assert valve.confidence == "sure"
    assert valve.reason_code == "valve_irrig_open_close_state"
    assert valve.ha_unique_id == f"jeedom2ha_eq_{MONO_ID}_cmd_80019"
    assert valve.ha_name == f"Equipement {MONO_ID}"  # une seule entité : nom de l'équipement
    assert {k: c.id for k, c in valve.commands.items()} == {
        "IRRIG_STATE": 80019, "IRRIG_ON": 80015, "IRRIG_OFF": 80018}
    assert valve.capabilities == ValveCapabilities(
        has_open_close=True, has_state=True, has_position=False, device_class="water")
    assert valve.reason_details == {
        "valve_family": "IRRIG",
        "valve_pairing": "id_order",
        "cmd_id": 80019,
        "object_id": f"jeedom2ha_{MONO_ID}_80019",
        "node_id": f"jeedom2ha_{MONO_ID}_80019",
        "state_topic": f"jeedom2ha/{MONO_ID}/80019/state",
        "command_topic": f"jeedom2ha/{MONO_ID}/80019/set",
    }


def test_two_zones_give_two_valves_paired_by_id_order():
    results = _all(_zones_eq())
    assert [r.ha_entity_type for r in results] == ["valve", "valve"]
    assert [{k: c.id for k, c in r.commands.items()} for r in results] == [
        {"IRRIG_STATE": 80021, "IRRIG_ON": 80022, "IRRIG_OFF": 80023},
        {"IRRIG_STATE": 80024, "IRRIG_ON": 80025, "IRRIG_OFF": 80026},
    ]
    assert [r.ha_unique_id for r in results] == [
        f"jeedom2ha_eq_{ZONES_ID}_cmd_80021", f"jeedom2ha_eq_{ZONES_ID}_cmd_80024"]
    # Plusieurs entités : chacune garde le nom de sa commande d'état.
    assert [r.ha_name for r in results] == ["Etat 80021", "Etat 80024"]
    primary = _map(_zones_eq())
    assert primary.additional_mappings == [results[1]]


def test_pairing_follows_id_order_whatever_the_command_order():
    eq = _eq(ZONES_ID, [
        _cmd(80026, "IRRIG_OFF"), _cmd(80025, "IRRIG_ON"), _state(80024),
        _cmd(80023, "IRRIG_OFF"), _cmd(80022, "IRRIG_ON"), _state(80021),
    ])
    trios = valve_trios(eq)
    assert [(f, {k: c.id for k, c in cmds.items()}) for f, cmds in trios] == [
        ("IRRIG", {"IRRIG_STATE": 80021, "IRRIG_ON": 80022, "IRRIG_OFF": 80023}),
        ("IRRIG", {"IRRIG_STATE": 80024, "IRRIG_ON": 80025, "IRRIG_OFF": 80026}),
    ]


@pytest.mark.parametrize("family,device_class", [
    ("IRRIG", "water"), ("FAUCET", "water"), ("VALVE", None)])
def test_families_and_device_class(family, device_class):
    valve = _map(_mono_eq(family=family))
    assert valve.ha_entity_type == "valve"
    assert valve.reason_details["valve_family"] == family
    assert valve.capabilities.device_class == device_class


@pytest.mark.parametrize("cmds", [
    # OFF manquant
    [_state(1), _cmd(2, "IRRIG_ON")],
    # STATE manquant : pas d'état, jamais de vanne optimiste devinée
    [_cmd(2, "IRRIG_ON"), _cmd(3, "IRRIG_OFF")],
    # STATE seul
    [_state(1)],
    # deux STATE, deux ON, un OFF : on ne sait pas quelle zone est incomplète
    [_state(1), _cmd(2, "IRRIG_ON"), _cmd(3, "IRRIG_OFF"), _state(4), _cmd(5, "IRRIG_ON")],
    # STATE de type action, ON de type info : mauvais genres, ils ne comptent pas
    [_cmd(1, "IRRIG_STATE"), _cmd(2, "IRRIG_ON"), _cmd(3, "IRRIG_OFF")],
    [_state(1), _cmd(2, "IRRIG_ON", "info", "binary"), _cmd(3, "IRRIG_OFF")],
    # familles mélangées : un trio n'est jamais fait de deux familles
    [_state(1, family="IRRIG"), _cmd(2, "FAUCET_ON"), _cmd(3, "VALVE_OFF")],
])
def test_incomplete_or_ambiguous_trio_gives_no_valve_and_keeps_the_previous_projection(cmds):
    eq = _eq(MONO_ID, cmds)
    assert ValveMapper().map_all(eq, _snapshot(eq)) == []
    assert [_shape(r) for r in _all(eq)] == [_shape(r) for r in _pre_story_projection(eq)]
    assert all(r.ha_entity_type != "valve" for r in _all(eq))


def test_duration_commands_are_out_of_scope():
    eq = _eq(MONO_ID, _mono_eq().cmds + [
        _cmd(80040, "VALVE_SET_DURATION", "action", "slider"),
        _cmd(80041, "VALVE_REMAINING_DURATION", "info", "numeric", "0"),
    ])
    valve = next(r for r in _all(eq) if r.ha_entity_type == "valve")
    assert set(valve.commands) == {"IRRIG_STATE", "IRRIG_ON", "IRRIG_OFF"}


def test_valve_is_added_to_the_entities_the_equipment_already_had():
    eq = _mixed_eq()
    without_valve = _eq(MIXED_ID, [_power_cmd()], eq_type="zwavejs")
    before = _pre_story_projection(without_valve)
    results = _all(eq)
    assert [r.ha_entity_type for r in results] == ["sensor", "valve"]
    # L'entité existante est strictement celle d'avant (identifiants, nom, commandes).
    assert _shape(results[0]) == _shape(before[0])
    assert results[0].ha_name == f"Equipement {MIXED_ID}"
    assert results[1].ha_unique_id == f"jeedom2ha_eq_{MIXED_ID}_cmd_80031"
    assert results[1].ha_name == "Etat 80031"
    primary = _map(eq)
    assert primary.ha_entity_type == "sensor"
    assert [m.ha_entity_type for m in primary.additional_mappings] == ["valve"]


def test_valve_commands_are_not_reused_by_the_other_entities():
    # Sans la vanne, le repli prendrait la commande d'état ; la vanne la consomme.
    eq = _eq(MONO_ID, _mono_eq().cmds + [_cmd(80050, None, "info", "string", "x")])
    results = _all(eq)
    assert [r.ha_entity_type for r in results] == ["sensor", "valve"]
    assert [c.id for c in results[0].commands.values()] == [80050]


# --- AC4 / D4 / D5 : discovery -------------------------------------------------------

def test_valve_discovery_payload():
    eq = _mono_eq()
    payload = _payload(_map(eq), eq)
    assert payload["unique_id"] == f"jeedom2ha_eq_{MONO_ID}_cmd_80019"
    assert payload["object_id"] == f"jeedom2ha_{MONO_ID}_80019"
    assert payload["default_entity_id"] == f"valve.jeedom2ha_{MONO_ID}_80019"
    assert payload["command_topic"] == f"jeedom2ha/{MONO_ID}/80019/set"
    assert payload["state_topic"] == f"jeedom2ha/{MONO_ID}/80019/state"
    assert (payload["payload_open"], payload["payload_close"]) == ("OPEN", "CLOSE")
    assert (payload["state_open"], payload["state_closed"]) == ("open", "closed")
    assert payload["reports_position"] is False
    assert payload["optimistic"] is False
    assert payload["device_class"] == "water"
    assert payload["name"] is None  # une seule entité : nom de l'appareil
    for key in ("position_topic", "set_position_topic", "payload_stop"):
        assert key not in payload
    assert payload["device"]["identifiers"] == [f"jeedom2ha_{MONO_ID}"]
    assert json.loads(json.dumps(payload)) == payload


def test_valve_family_has_no_device_class():
    eq = _mono_eq(family="VALVE")
    assert "device_class" not in _payload(_map(eq), eq)


@pytest.mark.asyncio
async def test_publish_valve_uses_one_node_scoped_topic_per_valve():
    bridge = _Bridge()
    publisher = DiscoveryPublisher(bridge)
    eq = _zones_eq()
    for valve in _all(eq):
        assert await PublisherRegistry(publisher).publish(valve, _snapshot(eq)) is True
    assert [t for t, *_ in bridge.published] == [
        f"homeassistant/valve/jeedom2ha_{ZONES_ID}_80021/config",
        f"homeassistant/valve/jeedom2ha_{ZONES_ID}_80024/config",
    ]
    assert all(retain for *_, retain in bridge.published)


def test_unpublish_covers_every_entity_in_its_own_domain():
    primary = _map(_mixed_eq())
    assert http_server._collect_unpublish_node_ids(primary) == [
        ("sensor", primary.reason_details["node_id"]),
        ("valve", f"jeedom2ha_{MIXED_ID}_80031"),
    ]


def test_runtime_state_topic_is_the_valve_topic():
    valve = _map(_mono_eq())
    assert http_server._resolve_state_topic(valve) == f"jeedom2ha/{MONO_ID}/80019/state"


# --- D4 : ordres --------------------------------------------------------------------

def _cmd_sync(primary, state_sync=None):
    decision = _decision(primary)
    for secondary in primary.additional_mappings:
        _decision(secondary)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app = {"publications": {primary.jeedom_eq_id: decision}, "state_synchronizer": state_sync}
    sync = CommandSynchronizer(app=app, mqtt_bridge=bridge,
                               jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
                               jeedom_core_apikey="core-apikey")
    sync._execute_exec_cmd = AsyncMock(return_value=True)
    return sync, bridge


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,cmd_id", [("OPEN", 80015), ("CLOSE", 80018), ("open", 80015)])
async def test_open_close_are_translated_to_the_trio_actions(payload, cmd_id):
    sync, bridge = _cmd_sync(_map(_mono_eq()))
    assert await sync.handle_command_message(f"jeedom2ha/{MONO_ID}/80019/set", payload) is True
    sync._execute_exec_cmd.assert_awaited_once_with(cmd_id, {})
    bridge.publish_message.assert_not_called()  # optimistic: false, jamais d'état inventé


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ["STOP", "ON", "OFF", "50", ""])
async def test_other_payloads_are_refused(payload):
    sync, _bridge = _cmd_sync(_map(_mono_eq()))
    assert await sync.handle_command_message(f"jeedom2ha/{MONO_ID}/80019/set", payload) is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("topic,payload,cmd_id", [
    (f"jeedom2ha/{ZONES_ID}/80021/set", "OPEN", 80022),
    (f"jeedom2ha/{ZONES_ID}/80021/set", "CLOSE", 80023),
    (f"jeedom2ha/{ZONES_ID}/80024/set", "OPEN", 80025),
    (f"jeedom2ha/{ZONES_ID}/80024/set", "CLOSE", 80026),
])
async def test_each_zone_only_drives_its_own_trio(topic, payload, cmd_id):
    sync, _bridge = _cmd_sync(_map(_zones_eq()))
    assert await sync.handle_command_message(topic, payload) is True
    sync._execute_exec_cmd.assert_awaited_once_with(cmd_id, {})


@pytest.mark.asyncio
async def test_valve_secondary_is_routed_next_to_the_existing_entity():
    sync, _bridge = _cmd_sync(_map(_mixed_eq()))
    assert await sync.handle_command_message(f"jeedom2ha/{MIXED_ID}/80031/set", "OPEN") is True
    sync._execute_exec_cmd.assert_awaited_once_with(80032, {})
    # Le topic d'équipement n'est publié par aucune entité pilotable.
    assert await sync.handle_command_message(f"jeedom2ha/{MIXED_ID}/set", "OPEN") is False


@pytest.mark.asyncio
async def test_no_order_without_its_jeedom_command():
    valve = _map(_mono_eq())
    del valve.commands["IRRIG_ON"]
    sync, _bridge = _cmd_sync(valve)
    assert await sync.handle_command_message(f"jeedom2ha/{MONO_ID}/80019/set", "OPEN") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirmation_uses_the_real_state_when_it_is_streamed():
    state_sync = StateSynchronizer(app={}, mqtt_bridge=_Bridge())
    valve = _map(_mono_eq())
    sync, _bridge = _cmd_sync(valve, state_sync=state_sync)
    translation = CommandTranslation(cmd_id=80015, options={}, command_family="valve_open_close")
    policy = sync._select_confirmation_policy(valve, valve.publication_decision_ref, translation)
    assert policy == "real_state_confirmation"
    assert state_sync.streams_actionable_type("valve") is True


# --- D4 : état ------------------------------------------------------------------------

@pytest.mark.parametrize("value,invert,expected", [
    ("1", False, "open"), ("0", False, "closed"), (1, False, "open"), (0, False, "closed"),
    ("1.0", False, "open"), (True, False, "open"), ("on", False, "open"),
    ("1", True, "closed"), ("0", True, "open"), (1, True, "closed"),
])
def test_valve_state_table(value, invert, expected):
    assert readback.valve_state(value, invert_binary=invert) == expected


@pytest.mark.parametrize("value", [None, "", "2", "50", "abc", "-1", "0.5", "nan"])
def test_valve_state_outside_table_is_never_invented(value):
    assert readback.valve_state(value) is None
    assert readback.valve_state(value, invert_binary=True) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("value,invert,expected", [
    ("1", False, "open"), ("0", False, "closed"), ("1", True, "closed"), ("0", True, "open"),
])
async def test_state_event_published_on_the_valve_state_topic(value, invert, expected):
    valve = _map(_mono_eq(invert=invert))
    decision = _decision(valve)
    bridge = _Bridge()
    sync = StateSynchronizer(app={"publications": {MONO_ID: decision}}, mqtt_bridge=bridge)
    assert sync.list_state_targets() == [{
        "eq_id": MONO_ID, "cmd_id": 80019, "ha_type": "valve",
        "state_topic": f"jeedom2ha/{MONO_ID}/80019/state",
    }]
    assert await sync.handle_state_message(MONO_ID, 80019, value) is True
    assert bridge.published == [(f"jeedom2ha/{MONO_ID}/80019/state", expected, 1, True)]


@pytest.mark.asyncio
async def test_unknown_state_value_publishes_nothing():
    decision = _decision(_map(_mono_eq()))
    bridge = _Bridge()
    sync = StateSynchronizer(app={"publications": {MONO_ID: decision}}, mqtt_bridge=bridge)
    assert await sync.handle_state_message(MONO_ID, 80019, "7") is False
    assert bridge.published == []


@pytest.mark.asyncio
async def test_initial_states_of_two_zones():
    primary = _map(_zones_eq())
    decision = _decision(primary)
    _decision(primary.additional_mappings[0])
    bridge = _Bridge()
    sync = StateSynchronizer(app={"publications": {ZONES_ID: decision}}, mqtt_bridge=bridge)
    assert await sync.publish_initial_states(decision) == 2
    assert bridge.published == [
        (f"jeedom2ha/{ZONES_ID}/80021/state", "closed", 1, True),
        (f"jeedom2ha/{ZONES_ID}/80024/state", "open", 1, True),
    ]


def test_invert_binary_is_read_from_the_topology_payload():
    snapshot = TopologySnapshot.from_jeedom_payload({"eq_logics": [{
        "id": MONO_ID, "name": "Eq", "cmds": [
            {"id": 1, "name": "A", "generic_type": "IRRIG_STATE", "type": "info",
             "sub_type": "binary", "invert_binary": True},
            {"id": 2, "name": "B", "generic_type": "IRRIG_ON", "type": "action"},
            {"id": 3, "name": "C", "generic_type": "IRRIG_OFF", "type": "action",
             "invert_binary": "0"},
        ],
    }]})
    cmds = snapshot.eq_logics[MONO_ID].cmds
    assert [c.invert_binary for c in cmds] == [True, False, False]


# --- AC6 : override pe-epic-16 ------------------------------------------------------

@pytest.mark.parametrize("forced", [
    "switch", "light", "cover", "button", "alarm_control_panel", "climate", "number", "select"])
def test_valve_forced_to_another_actuator_is_refused(forced):
    validity = validate_projection(forced, ValveCapabilities(has_open_close=True, has_state=True))
    assert validity.is_valid is False


@pytest.mark.parametrize("forced", ["sensor", "binary_sensor"])
def test_valve_read_as_a_sensor_stays_possible(forced):
    assert validate_projection(
        forced, ValveCapabilities(has_open_close=True, has_state=True)).is_valid is True


@pytest.mark.parametrize("caps", [
    SwitchCapabilities(has_on_off=True, has_state=True),
    CoverCapabilities(has_open_close=True),
    SensorCapabilities(has_state=True),
])
def test_other_families_forced_to_valve_are_refused(caps):
    validity = validate_projection("valve", caps)
    assert validity.is_valid is False
    assert validity.reason_code == "ha_missing_command_topic"


def test_override_on_the_valve_state_command_is_judged_by_validate_projection(tmp_path):
    valve = _map(_mono_eq())
    save_override(MONO_ID, 80019, {"ha_entity_type": "switch", "source": "user"}, str(tmp_path))
    forced = apply_type_override(valve, str(tmp_path))
    assert forced.ha_entity_type == "switch"
    assert validate_projection(forced.ha_entity_type, forced.capabilities).is_valid is False


def test_expected_ha_lists_valve_and_the_honest_readings():
    eq = _mono_eq()
    expected = resolve_expected_ha(eq, _snapshot(eq), eq.cmds[2])
    assert expected["proposed_ha_entity_type"] == "valve"
    assert expected["compatible_ha_components"] == ["sensor", "binary_sensor", "valve"]


# --- export de décision -------------------------------------------------------------

def test_decision_export_row_reads_the_valve_payload():
    eq = _mono_eq()
    valve = _map(eq)
    decision = _decision(valve)
    row = decision_export._entity_row(
        DiscoveryPublisher(MagicMock()), valve, "primary", decision, _snapshot(eq), MONO_ID,
        streamed={(MONO_ID, 80019, "valve")},
    )
    assert row == {
        "unique_id": f"jeedom2ha_eq_{MONO_ID}_cmd_80019",
        "ha_type": "valve",
        "role": "primary",
        "entity_id_expected": f"valve.jeedom2ha_{MONO_ID}_80019",
        "discovery_published": True,
        "state_source": "streamed",
    }
    row = decision_export._entity_row(
        DiscoveryPublisher(MagicMock()), valve, "primary", decision, _snapshot(eq), MONO_ID,
        streamed=set(),
    )
    assert row["state_source"] == "optimistic"


# --- non-régression switch / cover ---------------------------------------------------

@pytest.mark.parametrize("cmds", [
    [_cmd(1, "ENERGY_ON"), _cmd(2, "ENERGY_OFF"), _cmd(3, "ENERGY_STATE", "info", "binary", "1")],
    [_cmd(1, "SWITCH_ON", name="Pompe On"), _cmd(2, "SWITCH_OFF", name="Pompe Off"),
     _cmd(3, "SWITCH_STATE", "info", "binary", "1", name="Pompe"),
     _cmd(4, "SWITCH_ON", name="Spot On"), _cmd(5, "SWITCH_OFF", name="Spot Off"),
     _cmd(6, "SWITCH_STATE", "info", "binary", "0", name="Spot")],
    [_cmd(1, "FLAP_UP"), _cmd(2, "FLAP_DOWN"), _cmd(3, "FLAP_STOP"),
     _cmd(4, "FLAP_STATE", "info", "numeric", "50")],
    [_cmd(1, "GB_TOGGLE"), _cmd(2, "GARAGE_STATE", "info", "numeric", "0")],
])
def test_switch_and_cover_projection_is_unchanged(cmds):
    eq = _eq(MONO_ID, cmds)
    assert [_shape(r) for r in _all(eq)] == [_shape(r) for r in _pre_story_projection(eq)]
    assert all(r.ha_entity_type != "valve" for r in _all(eq))
