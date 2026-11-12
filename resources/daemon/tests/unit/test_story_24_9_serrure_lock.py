"""Story 24.9 — serrure projetée en ``lock`` (décisions D1 à D4).

Identifiants et noms synthétiques uniquement (CC-48). Couvre : ouverture gouvernée de
``lock`` (AR13 : registre, cas nominal et cas d'échec, PRODUCT_SCOPE), éligibilité (AC3 :
état + au moins un ordre ; état seul ou ordres seuls : projection d'avant), polarité D1
(cas général, ``nuki``, plugin à polarité non établie, valeur non reconnue), remplacement
explicite D3 (``binary_sensor`` de classe ``lock``, bouton sur ``LOCK_OPEN`` / ``LOCK_CLOSE``,
aucun ``unique_id`` réutilisé), payload D2 (``default_entity_id`` 22-1), ordres AC4
(LOCK/UNLOCK -> LOCK_CLOSE/LOCK_OPEN, aucun déverrouillage sans ``LOCK_OPEN``), état
streamé, override pe-epic-16, export de décision, D4 (rien sur Assist), cycle de vie
(dépublication à chaud et au redémarrage) et refus 24.12 de l'appui bouton conservé.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

import transport.http_server as http_server
from discovery.publisher import DiscoveryPublisher
from discovery.registry import PublisherRegistry
from export import decision_export
from mapping.lock import LockMapper, lock_commands, lock_polarity
from mapping.overrides import apply_type_override, save_override
from mapping.registry import MapperRegistry, resolve_expected_ha
from models.mapping import (
    CoverCapabilities,
    LockCapabilities,
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

LOCK_ID = 9001    # serrure virtuelle : état binaire + verrouiller + déverrouiller
NUKI_ID = 9002    # serrure d'un plugin à polarité 0/1/2
MIXED_ID = 9003   # prise (switch) + serrure sur le même équipement


def _cmd(cmd_id, generic_type, type_="action", sub_type="other", value=None, name=None, link=None):
    return JeedomCmd(id=cmd_id, name=name or f"Cmd {cmd_id}", generic_type=generic_type,
                     type=type_, sub_type=sub_type, current_value=value, linked_value=link)


def _state(cmd_id, value="1", sub_type="binary"):
    return _cmd(cmd_id, "LOCK_STATE", "info", sub_type, value, name=f"Etat {cmd_id}")


def _eq(eq_id, cmds, name=None, eq_type="virtual"):
    return JeedomEqLogic(id=eq_id, name=name or f"Equipement {eq_id}", object_id=1,
                         eq_type_name=eq_type, cmds=cmds)


def _snapshot(*eqs):
    return TopologySnapshot(
        timestamp="2026-11-12T00:00:00+00:00",
        objects={1: JeedomObject(id=1, name="Entree")},
        eq_logics={eq.id: eq for eq in eqs},
    )


def _lock_eq(value="1", open_=True, close=True, eq_type="virtual", eq_id=LOCK_ID):
    """Serrure : LOCK_CLOSE 90011, LOCK_OPEN 90012, LOCK_STATE 90013 (ids non triés)."""
    cmds = []
    if close:
        cmds.append(_cmd(90011, "LOCK_CLOSE"))
    if open_:
        cmds.append(_cmd(90012, "LOCK_OPEN"))
    cmds.append(_state(90013, value))
    return _eq(eq_id, cmds, eq_type=eq_type)


def _nuki_eq(value="0"):
    """Serrure nuki : état numérique 0/1/2."""
    return _eq(NUKI_ID, [
        _cmd(90021, "LOCK_OPEN"), _cmd(90022, "LOCK_CLOSE"),
        _state(90023, value, sub_type="numeric"),
    ], eq_type="nuki")


def _mixed_eq():
    """Une prise (ENERGY_*) et une serrure sur le même équipement."""
    return _eq(MIXED_ID, [
        _cmd(90031, "ENERGY_STATE", "info", "binary", "1"), _cmd(90032, "ENERGY_ON"),
        _cmd(90033, "ENERGY_OFF"),
        _state(90034), _cmd(90035, "LOCK_OPEN"), _cmd(90036, "LOCK_CLOSE"),
    ])


def _all(eq):
    return MapperRegistry().map_all(eq, _snapshot(eq))


def _map(eq):
    return MapperRegistry().map(eq, _snapshot(eq))


def _pre_story_projection(eq):
    """Projection d'avant la story : la même chaîne de mappers, sans les passes dédiées."""
    registry = MapperRegistry()
    return registry._apply_entity_name_rule(eq, registry._map_all_raw(eq, _snapshot(eq)))


def _shape(result):
    return (result.ha_entity_type, result.confidence, result.reason_code, result.ha_unique_id,
            result.ha_name, sorted((k, c.id) for k, c in result.commands.items()),
            result.reason_details)


def _cmd_ids(result):
    return {c.id for c in result.commands.values()}


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

def test_lock_is_known_and_open_in_the_same_increment():
    assert HA_COMPONENT_REGISTRY["lock"] == {
        "required_fields": ["state_topic", "command_topic", "platform", "availability"],
        "required_capabilities": ["has_state", "has_command"],
    }
    assert PRODUCT_SCOPE[-1] == "lock"
    assert PublisherRegistry.known_types()[-1] == "lock"


def test_validate_projection_nominal_case():
    for caps in (LockCapabilities(has_state=True, has_command=True, has_lock=True, has_unlock=True),
                 LockCapabilities(has_state=True, has_command=True, has_lock=True)):
        validity = validate_projection("lock", caps)
        assert validity.is_valid is True
        assert validity.reason_code is None


@pytest.mark.parametrize("caps,reason,missing", [
    (LockCapabilities(has_state=False, has_command=True), "ha_missing_state_topic", ["has_state"]),
    (LockCapabilities(has_state=True, has_command=False), "ha_missing_command_topic", ["has_command"]),
    (LockCapabilities(), "ha_missing_state_topic", ["has_state", "has_command"]),
])
def test_validate_projection_failure_cases(caps, reason, missing):
    validity = validate_projection("lock", caps)
    assert validity.is_valid is False
    assert validity.reason_code == reason
    assert validity.missing_capabilities == missing


def test_lock_types_stay_out_of_switch_cover_and_light():
    # AC1 : LOCK_* restent dans les listes « anti » des autres mappers.
    eq = _lock_eq()
    assert {r.ha_entity_type for r in _pre_story_projection(eq)} == {"binary_sensor"}


# --- AC3 / D1 : éligibilité et polarité ----------------------------------------------

def test_lock_equipment_is_published_as_a_lock():
    results = _all(_lock_eq())
    assert len(results) == 1
    lock = results[0]
    assert lock.ha_entity_type == "lock"
    assert lock.confidence == "sure"
    assert lock.reason_code == "lock_state_open_close"
    assert lock.ha_unique_id == f"jeedom2ha_eq_{LOCK_ID}_cmd_90013"
    assert lock.ha_name == f"Equipement {LOCK_ID}"  # une seule entité : nom de l'équipement
    assert {k: c.id for k, c in lock.commands.items()} == {
        "LOCK_STATE": 90013, "LOCK_OPEN": 90012, "LOCK_CLOSE": 90011}
    assert lock.capabilities == LockCapabilities(
        has_state=True, has_command=True, has_lock=True, has_unlock=True)
    assert lock.reason_details == {
        "lock_polarity": "standard",
        "cmd_id": 90013,
        "object_id": f"jeedom2ha_{LOCK_ID}_90013",
        "node_id": f"jeedom2ha_{LOCK_ID}_90013",
        "state_topic": f"jeedom2ha/{LOCK_ID}/90013/state",
        "command_topic": f"jeedom2ha/{LOCK_ID}/90013/set",
    }


@pytest.mark.parametrize("open_,close,has_lock,has_unlock", [
    (False, True, True, False),
    (True, False, False, True),
])
def test_one_order_is_enough(open_, close, has_lock, has_unlock):
    lock = _map(_lock_eq(open_=open_, close=close))
    assert lock.ha_entity_type == "lock"
    assert (lock.capabilities.has_lock, lock.capabilities.has_unlock) == (has_lock, has_unlock)
    assert ("LOCK_OPEN" in lock.commands) is has_unlock


@pytest.mark.parametrize("cmds", [
    # état seul : lecture seule d'avant (binary_sensor)
    [_state(1)],
    # ordres seuls : jamais d'état inventé
    [_cmd(2, "LOCK_OPEN"), _cmd(3, "LOCK_CLOSE")],
    # deux états : on ne sait pas lequel suit quelle serrure
    [_state(1), _state(4), _cmd(2, "LOCK_OPEN"), _cmd(3, "LOCK_CLOSE")],
    # deux ordres de déverrouillage
    [_state(1), _cmd(2, "LOCK_OPEN"), _cmd(5, "LOCK_OPEN"), _cmd(3, "LOCK_CLOSE")],
    # état de type action, ordres de type info : mauvais genres, ils ne comptent pas
    [_cmd(1, "LOCK_STATE"), _cmd(2, "LOCK_OPEN"), _cmd(3, "LOCK_CLOSE")],
    [_state(1), _cmd(2, "LOCK_OPEN", "info", "binary"), _cmd(3, "LOCK_CLOSE", "info", "binary")],
    # un ordre qui porte une valeur (curseur) n'est pas un ordre de serrure
    [_state(1), _cmd(2, "LOCK_OPEN", "action", "slider")],
    # action liée à une autre commande
    [_state(1), _cmd(2, "LOCK_OPEN", link=99), _cmd(3, "LOCK_CLOSE", link=1)],
])
def test_no_lock_keeps_the_previous_projection(cmds):
    eq = _eq(LOCK_ID, cmds)
    assert LockMapper().map_all(eq, _snapshot(eq)) == []
    assert [_shape(r) for r in _all(eq)] == [_shape(r) for r in _pre_story_projection(eq)]
    assert all(r.ha_entity_type != "lock" for r in _all(eq))


@pytest.mark.parametrize("links", [{}, {90011: 90013}, {90011: 90013, 90012: 90013}])
def test_actions_linked_to_the_state_or_unlinked_are_accepted(links):
    eq = _eq(LOCK_ID, [_cmd(90011, "LOCK_CLOSE", link=links.get(90011)),
                       _cmd(90012, "LOCK_OPEN", link=links.get(90012)), _state(90013)])
    assert set(lock_commands(eq)) == {"LOCK_STATE", "LOCK_OPEN", "LOCK_CLOSE"}


@pytest.mark.parametrize("eq_type,polarity", [
    ("virtual", "standard"), ("zwavejs", "standard"), ("", "standard"),
    ("nuki", "nuki"), ("Nuki", "nuki"), ("jeelink", None),
])
def test_polarity_comes_from_the_plugin_only(eq_type, polarity):
    assert lock_polarity(_eq(LOCK_ID, [], eq_type=eq_type)) == polarity


def test_polarity_is_never_deduced_from_a_name():
    eq = _lock_eq()
    eq.name = "nuki"
    eq.cmds[2].name = "Nuki etat"
    assert _map(eq).reason_details["lock_polarity"] == "standard"


def test_unknown_polarity_is_not_a_lock(caplog):
    eq = _lock_eq(eq_type="jeelink")
    with caplog.at_level("WARNING"):
        assert lock_commands(eq) is None
    assert "polarité non établie" in caplog.text
    assert [_shape(r) for r in _all(eq)] == [_shape(r) for r in _pre_story_projection(eq)]


@pytest.mark.parametrize("value,expected", [
    ("1", "LOCKED"), (1, "LOCKED"), (True, "LOCKED"), ("true", "LOCKED"), ("on", "LOCKED"),
    ("1.0", "LOCKED"), (" 1 ", "LOCKED"),
    ("0", "UNLOCKED"), (0, "UNLOCKED"), (False, "UNLOCKED"), ("false", "UNLOCKED"),
    ("off", "UNLOCKED"), ("0.0", "UNLOCKED"),
])
def test_standard_polarity_table(value, expected):
    assert readback.lock_state(value, "standard") == expected


@pytest.mark.parametrize("value,expected", [
    ("0", "LOCKED"), (0, "LOCKED"), ("1", "UNLOCKED"), (1, "UNLOCKED"), ("2", "JAMMED"),
    ("2.0", "JAMMED"),
])
def test_nuki_polarity_table(value, expected):
    assert readback.lock_state(value, "nuki") == expected


@pytest.mark.parametrize("value,polarity", [
    (None, "standard"), ("", "standard"), ("2", "standard"), ("-1", "standard"),
    ("0.5", "standard"), ("abc", "standard"), ("locked", "standard"), ("nan", "standard"),
    (None, "nuki"), ("3", "nuki"), ("255", "nuki"), ("1.5", "nuki"), ("true", "nuki"),
    ("on", "nuki"), ("-1", "nuki"), ("inf", "nuki"), ("nan", "nuki"),
    ("1", None), ("0", None), ("1", "autre"),
])
def test_unrecognised_value_or_polarity_publishes_no_state(value, polarity):
    assert readback.lock_state(value, polarity) is None


# --- D3 / AC6 : remplacement explicite --------------------------------------------------

def test_lock_replaces_the_read_only_binary_sensor(caplog):
    eq = _lock_eq()
    before = _pre_story_projection(eq)
    assert [(r.ha_entity_type, r.ha_unique_id, _cmd_ids(r)) for r in before] == [
        ("binary_sensor", f"jeedom2ha_eq_{LOCK_ID}", {90013})]
    with caplog.at_level("WARNING"):
        results = _all(eq)
    assert [r.ha_entity_type for r in results] == ["lock"]
    assert "binary_sensor" in caplog.text and "remplacée par la serrure" in caplog.text


def test_lock_replaces_a_button_on_its_orders():
    # Avant la story, l'état numérique ne donnait pas de binary_sensor : un bouton « sure »
    # prenait LOCK_OPEN sous jeedom2ha_eq_<id>.
    eq = _nuki_eq()
    before = _pre_story_projection(eq)
    assert [(r.ha_entity_type, r.ha_unique_id, _cmd_ids(r)) for r in before] == [
        ("button", f"jeedom2ha_eq_{NUKI_ID}", {90021})]
    results = _all(eq)
    assert [(r.ha_entity_type, r.ha_unique_id) for r in results] == [
        ("lock", f"jeedom2ha_eq_{NUKI_ID}_cmd_90023")]


@pytest.mark.parametrize("eq_factory", [_lock_eq, _nuki_eq, _mixed_eq])
def test_no_unique_id_is_silently_reused(eq_factory):
    eq = eq_factory()
    before = {(r.ha_entity_type, r.ha_unique_id): _cmd_ids(r) for r in _pre_story_projection(eq)}
    for result in _all(eq):
        key = (result.ha_entity_type, result.ha_unique_id)
        if key in before:  # une entité d'avant gardée l'est avec exactement ses commandes
            assert _cmd_ids(result) == before[key]
    lock = next(r for r in _all(eq) if r.ha_entity_type == "lock")
    assert lock.ha_unique_id not in {uid for _t, uid in before}


def test_lock_is_added_next_to_the_entities_it_does_not_replace():
    eq = _mixed_eq()
    before = _pre_story_projection(eq)
    assert [r.ha_entity_type for r in before] == ["switch"]
    results = _all(eq)
    assert [r.ha_entity_type for r in results] == ["switch", "lock"]
    assert _shape(results[0]) == _shape(before[0])
    assert results[1].ha_name == "Etat 90034"  # plusieurs entités : nom de la commande d'état
    primary = _map(eq)
    assert [m.ha_entity_type for m in primary.additional_mappings] == ["lock"]


def test_valve_and_lock_on_the_same_equipment():
    eq = _eq(LOCK_ID, _lock_eq().cmds + [
        _cmd(90041, "IRRIG_STATE", "info", "binary", "0"), _cmd(90042, "IRRIG_ON"),
        _cmd(90043, "IRRIG_OFF")])
    assert [r.ha_entity_type for r in _all(eq)] == ["valve", "lock"]


# --- D2 / AC5 : discovery ----------------------------------------------------------

def test_lock_discovery_payload():
    eq = _lock_eq()
    payload = _payload(_map(eq), eq)
    assert payload["unique_id"] == f"jeedom2ha_eq_{LOCK_ID}_cmd_90013"
    assert payload["object_id"] == f"jeedom2ha_{LOCK_ID}_90013"
    assert payload["default_entity_id"] == f"lock.jeedom2ha_{LOCK_ID}_90013"
    assert payload["command_topic"] == f"jeedom2ha/{LOCK_ID}/90013/set"
    assert payload["state_topic"] == f"jeedom2ha/{LOCK_ID}/90013/state"
    assert (payload["payload_lock"], payload["payload_unlock"]) == ("LOCK", "UNLOCK")
    assert (payload["state_locked"], payload["state_unlocked"], payload["state_jammed"]) == (
        "LOCKED", "UNLOCKED", "JAMMED")
    assert payload["optimistic"] is False
    assert payload["name"] is None  # une seule entité : nom de l'appareil
    assert payload["device"]["identifiers"] == [f"jeedom2ha_{LOCK_ID}"]
    assert json.loads(json.dumps(payload)) == payload


def test_payload_has_no_code_no_open_and_nothing_about_assist():
    # D2 : pas de code ; pas d'ordre « ouvrir la porte » ; D4 : aucune clé d'exposition.
    eq = _lock_eq()
    payload = _payload(_map(eq), eq)
    for key in ("code", "code_format", "payload_open", "state_open", "state_opening",
                "command_template", "value_template"):
        assert key not in payload
    assert not [k for k in payload if "expos" in k.lower() or "assist" in k.lower()]


@pytest.mark.asyncio
async def test_publish_lock_uses_its_node_scoped_topic():
    bridge = _Bridge()
    eq = _lock_eq()
    assert await PublisherRegistry(DiscoveryPublisher(bridge)).publish(_map(eq), _snapshot(eq)) is True
    assert [(t, retain) for t, _p, _q, retain in bridge.published] == [
        (f"homeassistant/lock/jeedom2ha_{LOCK_ID}_90013/config", True)]


def test_unpublish_covers_every_entity_in_its_own_domain():
    primary = _map(_mixed_eq())
    assert ("lock", f"jeedom2ha_{MIXED_ID}_90034") in http_server._collect_unpublish_node_ids(primary)


def test_runtime_state_topic_is_the_lock_topic():
    assert http_server._resolve_state_topic(_map(_lock_eq())) == f"jeedom2ha/{LOCK_ID}/90013/state"


# --- AC4 : ordres -------------------------------------------------------------------

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
@pytest.mark.parametrize("payload,cmd_id", [("LOCK", 90011), ("UNLOCK", 90012)])
async def test_lock_unlock_are_translated_to_lock_close_and_lock_open(payload, cmd_id):
    sync, bridge = _cmd_sync(_map(_lock_eq()))
    assert await sync.handle_command_message(f"jeedom2ha/{LOCK_ID}/90013/set", payload) is True
    sync._execute_exec_cmd.assert_awaited_once_with(cmd_id, {})
    bridge.publish_message.assert_not_called()  # optimistic: false, jamais d'état inventé


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ["OPEN", "unlock", "lock", "ON", "OFF", "1", "", "PRESS"])
async def test_other_payloads_are_refused(payload):
    sync, _bridge = _cmd_sync(_map(_lock_eq()))
    assert await sync.handle_command_message(f"jeedom2ha/{LOCK_ID}/90013/set", payload) is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_unlock_without_a_lock_open_command():
    lock = _map(_lock_eq(open_=False))
    sync, _bridge = _cmd_sync(lock)
    assert await sync.handle_command_message(f"jeedom2ha/{LOCK_ID}/90013/set", "UNLOCK") is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert await sync.handle_command_message(f"jeedom2ha/{LOCK_ID}/90013/set", "LOCK") is True
    sync._execute_exec_cmd.assert_awaited_once_with(90011, {})


@pytest.mark.asyncio
async def test_an_order_never_uses_a_command_of_another_type():
    lock = _map(_lock_eq())
    lock.commands["LOCK_OPEN"] = _cmd(90099, "ENERGY_ON")  # commande étrangère : refusée
    sync, _bridge = _cmd_sync(lock)
    assert await sync.handle_command_message(f"jeedom2ha/{LOCK_ID}/90013/set", "UNLOCK") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_equipment_topic_is_not_a_lock_topic():
    sync, _bridge = _cmd_sync(_map(_lock_eq()))
    assert await sync.handle_command_message(f"jeedom2ha/{LOCK_ID}/set", "UNLOCK") is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_lock_secondary_is_routed_next_to_the_switch():
    sync, _bridge = _cmd_sync(_map(_mixed_eq()))
    assert await sync.handle_command_message(f"jeedom2ha/{MIXED_ID}/90034/set", "LOCK") is True
    sync._execute_exec_cmd.assert_awaited_once_with(90036, {})


@pytest.mark.asyncio
async def test_confirmation_uses_the_real_state_when_it_is_streamed():
    state_sync = StateSynchronizer(app={}, mqtt_bridge=_Bridge())
    lock = _map(_lock_eq())
    sync, _bridge = _cmd_sync(lock, state_sync=state_sync)
    translation = CommandTranslation(cmd_id=90011, options={}, command_family="lock_lock_unlock")
    assert sync._select_confirmation_policy(
        lock, lock.publication_decision_ref, translation) == "real_state_confirmation"
    assert state_sync.streams_actionable_type("lock") is True


@pytest.mark.asyncio
async def test_equipment_button_press_on_lock_commands_is_still_refused():
    # 24.12 inchangé : un bouton forcé sur une commande LOCK_* n'est jamais exécuté.
    button = _pre_story_projection(_nuki_eq())[0]
    assert button.ha_entity_type == "button"
    translation, reason = CommandSynchronizer._translate_button_command(button, "PRESS")
    assert translation is None and reason == "button_sensitive_family_refused"


# --- D1 : état streamé ------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("eq_factory,cmd_id,value,expected", [
    (_lock_eq, 90013, "1", "LOCKED"), (_lock_eq, 90013, "0", "UNLOCKED"),
    (_nuki_eq, 90023, "0", "LOCKED"), (_nuki_eq, 90023, "1", "UNLOCKED"),
    (_nuki_eq, 90023, "2", "JAMMED"),
])
async def test_state_event_published_on_the_lock_state_topic(eq_factory, cmd_id, value, expected):
    lock = _map(eq_factory())
    eq_id = lock.jeedom_eq_id
    bridge = _Bridge()
    sync = StateSynchronizer(app={"publications": {eq_id: _decision(lock)}}, mqtt_bridge=bridge)
    assert sync.list_state_targets() == [{
        "eq_id": eq_id, "cmd_id": cmd_id, "ha_type": "lock",
        "state_topic": f"jeedom2ha/{eq_id}/{cmd_id}/state",
    }]
    assert await sync.handle_state_message(eq_id, cmd_id, value) is True
    assert bridge.published == [(f"jeedom2ha/{eq_id}/{cmd_id}/state", expected, 1, True)]


@pytest.mark.asyncio
@pytest.mark.parametrize("eq_factory,cmd_id,value", [
    (_lock_eq, 90013, "2"), (_lock_eq, 90013, "abc"), (_nuki_eq, 90023, "3"),
])
async def test_unknown_state_value_publishes_nothing(eq_factory, cmd_id, value):
    lock = _map(eq_factory())
    bridge = _Bridge()
    sync = StateSynchronizer(app={"publications": {lock.jeedom_eq_id: _decision(lock)}},
                             mqtt_bridge=bridge)
    assert await sync.handle_state_message(lock.jeedom_eq_id, cmd_id, value) is False
    assert bridge.published == []


@pytest.mark.asyncio
async def test_initial_state_is_the_real_one():
    lock = _map(_lock_eq(value="0"))
    decision = _decision(lock)
    bridge = _Bridge()
    sync = StateSynchronizer(app={"publications": {LOCK_ID: decision}}, mqtt_bridge=bridge)
    assert await sync.publish_initial_states(decision) == 1
    assert bridge.published == [(f"jeedom2ha/{LOCK_ID}/90013/state", "UNLOCKED", 1, True)]


@pytest.mark.asyncio
async def test_no_initial_state_without_a_recognised_value():
    lock = _map(_lock_eq(value="7"))
    decision = _decision(lock)
    bridge = _Bridge()
    sync = StateSynchronizer(app={"publications": {LOCK_ID: decision}}, mqtt_bridge=bridge)
    assert await sync.publish_initial_states(decision) == 0
    assert bridge.published == []


# --- override pe-epic-16 ------------------------------------------------------------

_LOCK_CAPS = LockCapabilities(has_state=True, has_command=True, has_lock=True, has_unlock=True)


@pytest.mark.parametrize("forced", [
    "switch", "light", "cover", "button", "valve", "alarm_control_panel", "climate", "number",
    "select"])
def test_lock_forced_to_another_actuator_is_refused(forced):
    assert validate_projection(forced, _LOCK_CAPS).is_valid is False


@pytest.mark.parametrize("forced", ["sensor", "binary_sensor"])
def test_lock_read_as_a_sensor_stays_possible(forced):
    assert validate_projection(forced, _LOCK_CAPS).is_valid is True


@pytest.mark.parametrize("caps", [
    SwitchCapabilities(has_on_off=True, has_state=True),
    CoverCapabilities(has_open_close=True),
    SensorCapabilities(has_state=True),
    ValveCapabilities(has_open_close=True, has_state=True),
])
def test_other_families_forced_to_lock_are_refused(caps):
    validity = validate_projection("lock", caps)
    assert validity.is_valid is False
    assert validity.reason_code == "ha_missing_command_topic"


def test_override_on_the_lock_state_command_is_judged_by_validate_projection(tmp_path):
    lock = _map(_lock_eq())
    save_override(LOCK_ID, 90013, {"ha_entity_type": "switch", "source": "user"}, str(tmp_path))
    forced = apply_type_override(lock, str(tmp_path))
    assert forced.ha_entity_type == "switch"
    assert validate_projection(forced.ha_entity_type, forced.capabilities).is_valid is False


def test_expected_ha_lists_lock_and_the_honest_readings():
    eq = _lock_eq()
    expected = resolve_expected_ha(eq, _snapshot(eq), eq.cmds[2])
    assert expected["proposed_ha_entity_type"] == "lock"
    assert expected["compatible_ha_components"] == ["sensor", "binary_sensor", "lock"]


# --- export de décision ---------------------------------------------------------------

def test_decision_export_row_reads_the_lock_payload():
    eq = _lock_eq()
    lock = _map(eq)
    decision = _decision(lock)
    row = decision_export._entity_row(
        DiscoveryPublisher(MagicMock()), lock, "primary", decision, _snapshot(eq), LOCK_ID,
        streamed={(LOCK_ID, 90013, "lock")},
    )
    assert row == {
        "unique_id": f"jeedom2ha_eq_{LOCK_ID}_cmd_90013",
        "ha_type": "lock",
        "role": "primary",
        "entity_id_expected": f"lock.jeedom2ha_{LOCK_ID}_90013",
        "discovery_published": True,
        "state_source": "streamed",
    }


# --- AC6 : cycle de vie (dépublication de l'entité remplacée) ------------------------

def _published(mapping):
    decision = _decision(mapping)
    for secondary in mapping.additional_mappings:
        _decision(secondary)
    return decision


@pytest.mark.asyncio
async def test_runtime_retype_unpublishes_the_binary_sensor():
    previous = _pre_story_projection(_lock_eq())[0]
    publisher = MagicMock()
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    await http_server._detect_lifecycle_changes(
        LOCK_ID, _map(_lock_eq()), _published(previous), {}, False, publisher, {})
    publisher.unpublish_by_eq_id.assert_awaited_once_with(
        LOCK_ID, entity_type="binary_sensor", node_ids=[])


@pytest.mark.asyncio
async def test_boot_retype_unpublishes_the_button_and_defers_on_failure():
    boot = {NUKI_ID: {"entity_type": "button", "ha_name": f"Equipement {NUKI_ID}",
                      "published": True, "node_ids": []}}
    publisher = MagicMock()
    publisher.unpublish_by_eq_id = AsyncMock(return_value=False)
    pending = {}
    await http_server._detect_lifecycle_changes(
        NUKI_ID, _map(_nuki_eq()), None, boot, True, publisher, pending)
    publisher.unpublish_by_eq_id.assert_awaited_once_with(
        NUKI_ID, entity_type="button", node_ids=[])
    assert NUKI_ID in pending


@pytest.mark.asyncio
async def test_boot_kept_primary_does_not_unpublish_the_new_lock():
    current = _map(_mixed_eq())
    boot = {MIXED_ID: {"entity_type": "switch", "ha_name": f"Equipement {MIXED_ID}",
                       "published": True, "node_ids": [
                           ("switch", f"jeedom2ha_{MIXED_ID}"),
                           ("lock", current.additional_mappings[0].reason_details["node_id"])]}}
    publisher = MagicMock()
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    await http_server._detect_lifecycle_changes(MIXED_ID, current, None, boot, True, publisher, {})
    publisher.unpublish_by_eq_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_boot_removed_secondary_is_unpublished():
    # Cache disque d'avant : switch + un binary_sensor secondaire sur LOCK_STATE.
    boot = {MIXED_ID: {"entity_type": "switch", "ha_name": f"Equipement {MIXED_ID}",
                       "published": True, "node_ids": [
                           ("switch", f"jeedom2ha_{MIXED_ID}"),
                           ("binary_sensor", f"jeedom2ha_{MIXED_ID}_90034")]}}
    publisher = MagicMock()
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    await http_server._detect_lifecycle_changes(
        MIXED_ID, _map(_mixed_eq()), None, boot, True, publisher, {})
    publisher.unpublish_by_eq_id.assert_awaited_once_with(
        MIXED_ID, entity_type="switch", node_ids=[("binary_sensor", f"jeedom2ha_{MIXED_ID}_90034")])


# --- non-régression ------------------------------------------------------------------

@pytest.mark.parametrize("cmds", [
    [_cmd(1, "ENERGY_ON"), _cmd(2, "ENERGY_OFF"), _cmd(3, "ENERGY_STATE", "info", "binary", "1")],
    [_cmd(1, "FLAP_UP"), _cmd(2, "FLAP_DOWN"), _cmd(3, "FLAP_STOP"),
     _cmd(4, "FLAP_STATE", "info", "numeric", "50")],
    [_cmd(1, "THERMOSTAT_LOCK", "info", "binary", "1")],
    [_cmd(1, "OPENING", "info", "binary", "0")],
])
def test_other_equipments_are_unchanged(cmds):
    eq = _eq(LOCK_ID, cmds)
    assert [_shape(r) for r in _all(eq)] == [_shape(r) for r in _pre_story_projection(eq)]
    assert all(r.ha_entity_type != "lock" for r in _all(eq))
