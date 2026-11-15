"""story/select-mode — un mode Jeedom publié en HA ``select`` (entité secondaire, en ajout seulement).

Motif : une info texte dont la valeur est posée par au moins deux actions écrivant chacune une constante
différente. Trois sources : types génériques MODE_STATE / MODE_SET_STATE (ou rôles posés par « Corriger
le type »), action « liste » (listValue) reliée à l'info, actions reliées par updateCmdId / infoId.

AR13 dans le même incrément : entrée du registre, cas nominal et cas d'échec de validate_projection(),
non-régression du contrat 4D, ouverture dans PRODUCT_SCOPE.
"""

from __future__ import annotations

import json
from collections import Counter
from unittest.mock import AsyncMock

import pytest

from discovery.publisher import DiscoveryPublisher
from discovery.registry import PublisherRegistry
from mapping.overrides import apply_type_override, mode_roles_for
from mapping.registry import MapperRegistry
from mapping.select import SelectMapper, parse_list_value, written_value
from models.evaluate_equipment import evaluate_equipment
from models.mapping import (
    MappingResult,
    PublicationDecision,
    SelectCapabilities,
    SwitchCapabilities,
)
from models.topology import JeedomCmd, TopologySnapshot, assess_eligibility
from models.ui_contract_4d import compute_ecart, reason_code_to_perimetre
from sync.command import CommandSynchronizer
from sync.state import SELECT_UNKNOWN_PAYLOAD, StateSynchronizer
from transport.http_server import _build_mapping_override_tree, create_app
from validation.ha_component_registry import HA_COMPONENT_REGISTRY, PRODUCT_SCOPE, validate_projection

from .select_mode_corpus import (
    BASELINE_PATH,
    BORNE_ID,
    CLIM_ID,
    MODES_ID,
    ROUTEUR_ID,
    SERRURE_ID,
    VOITURE_ID,
    VOLET_ID,
    DOUBLON_ID,
    EXPRESSION_ID,
    SEUL_ETAT_ID,
    THERMOSTAT_ID,
    entity_commands,
    load_scene,
    mode_eq_logics,
    sync_body,
)
from .fix_switch_appariement_corpus import CHAUFFE_EAU_ID, chauffe_eau_cmds

SECRET = "test-secret-select"
H = {"X-Local-Secret": SECRET}


def _snapshot(eq_logics) -> TopologySnapshot:
    return TopologySnapshot.from_jeedom_payload({"objects": [{"id": 1, "name": "Buanderie"}], "eq_logics": eq_logics})


def _raw(eq_id, cmds, name="Chauffe-eau", eq_type="virtual"):
    return {"id": eq_id, "name": name, "eq_type": eq_type, "object_id": 1, "is_enable": True, "cmds": cmds}


def _heater():
    snapshot = _snapshot([_raw(CHAUFFE_EAU_ID, chauffe_eau_cmds())])
    return snapshot.eq_logics[CHAUFFE_EAU_ID], snapshot


def _mode_eq(eq_id):
    eq_raw = next(e for e in mode_eq_logics() if e["id"] == eq_id)
    snapshot = _snapshot([eq_raw])
    return snapshot.eq_logics[eq_id], snapshot


def _selects(results):
    return [r for r in results if r.ha_entity_type == "select"]


def _decision(mapping):
    decision = PublicationDecision(should_publish=True, reason="sure", mapping_result=mapping,
                                   active_or_alive=True, discovery_published=True)
    mapping.publication_decision_ref = decision
    return decision


# --- AR13 : registre, validate_projection, PRODUCT_SCOPE -------------------------------------

def test_select_is_known_and_open_in_the_same_increment():
    assert HA_COMPONENT_REGISTRY["select"] == {
        "required_fields": ["command_topic", "options", "platform", "availability"],
        "required_capabilities": ["has_command", "has_options"],
    }
    assert "select" in PRODUCT_SCOPE
    assert "select" in PublisherRegistry.known_types()


def test_validate_projection_nominal_case():
    caps = SelectCapabilities(has_state=True, has_command=True, has_options=True, options=["a", "b"])
    validity = validate_projection("select", caps)
    assert (validity.is_valid, validity.reason_code) == (True, None)


@pytest.mark.parametrize("caps,reason,missing", [
    (SelectCapabilities(has_state=True, has_command=True, has_options=False), "ha_missing_required_option", ["options"]),
    (SelectCapabilities(has_state=True, has_command=False, has_options=True), "ha_missing_command_topic", ["command_topic"]),
    (SwitchCapabilities(has_on_off=True, has_state=True), "ha_missing_required_option", ["options"]),
])
def test_validate_projection_failure_cases(caps, reason, missing):
    validity = validate_projection("select", caps)
    assert validity.is_valid is False
    assert validity.reason_code == reason
    assert validity.missing_fields == missing


@pytest.mark.parametrize("forced", ["switch", "light", "cover", "button", "valve", "lock", "climate",
                                    "alarm_control_panel", "binary_sensor"])
def test_a_mode_forced_to_another_type_is_refused(forced):
    caps = SelectCapabilities(has_state=True, has_command=True, has_options=True, options=["a", "b"])
    assert validate_projection(forced, caps).is_valid is False


def test_a_mode_read_as_a_sensor_stays_possible():
    caps = SelectCapabilities(has_state=True, has_command=True, has_options=True, options=["a", "b"])
    assert validate_projection("sensor", caps).is_valid is True


# --- Le chauffe-eau : source 3 (actions reliées) -------------------------------------------

def test_water_heater_mode_becomes_a_secondary_select():
    eq, snapshot = _heater()
    primary = MapperRegistry().map(eq, snapshot)
    assert primary.ha_entity_type == "switch"  # le relais reste l'entité principale
    selects = _selects(primary.additional_mappings)
    assert len(selects) == 1
    select = selects[0]
    assert select.ha_unique_id == "jeedom2ha_eq_554_select_5489"
    assert select.ha_name == "etat"
    assert select.confidence == "sure"
    assert select.reason_details["options"] == ["Absence", "manu", "auto"]  # casse gardée
    assert {o: e["cmd_id"] for o, e in select.reason_details["option_commands"].items()} == {
        "Absence": 5372, "manu": 5490, "auto": 5491,
    }
    assert select.reason_details["state_topic"] == "jeedom2ha/554/select_5489/state"
    assert select.reason_details["command_topic"] == "jeedom2ha/554/select_5489/set"
    assert validate_projection("select", select.capabilities).is_valid is True


def test_water_heater_keeps_every_previous_entity_unchanged():
    eq, snapshot = _heater()
    registry = MapperRegistry()
    before = registry._map_all_base(eq, snapshot)
    after = registry.map_all(eq, snapshot)
    assert after[:len(before)] == before
    assert [r.ha_entity_type for r in after[len(before):]] == ["select"]


# --- Source 1 : types génériques standard ----------------------------------------------------

def test_generic_mode_types_use_the_action_names_as_options():
    eq, snapshot = _mode_eq(THERMOSTAT_ID)
    select = _selects(MapperRegistry().map_all(eq, snapshot))[0]
    assert select.reason_code == "select_generic_mode"
    assert select.reason_details["options"] == ["Confort", "Eco", "Hors-gel"]


def test_generic_mode_keeps_only_the_linked_actions_when_some_are_linked():
    """Forme « Modes » : 7 actions MODE_SET_STATE reliées par infoId/value, 3 non reliées (« Rejouer »,
    « Retour mode précédent », « Aller au mode suivant ») : seules les reliées sont des options, avec
    la valeur qu'elles écrivent ; le nom n'est utilisé que si aucune action n'est reliée."""
    names = ["Jour", "Nuit", "Absent", "Vacances", "Soirée", "Cinéma", "Réveil"]
    cmds = [
        {"id": 70, "name": "Température", "generic_type": "TEMPERATURE", "type": "info", "sub_type": "numeric"},
        {"id": 71, "name": "Mode", "generic_type": "MODE_STATE", "type": "info", "sub_type": "string"},
        *[{"id": 72 + i, "name": n, "generic_type": "MODE_SET_STATE", "type": "action", "sub_type": "other",
           "virtual_info_id": "71", "virtual_value": n.lower()} for i, n in enumerate(names)],
        *[{"id": 90 + i, "name": n, "generic_type": "MODE_SET_STATE", "type": "action", "sub_type": "other"}
          for i, n in enumerate(["Rejouer", "Retour mode précédent", "Aller au mode suivant"])],
    ]
    snapshot = _snapshot([_raw(69, cmds, name="Modes maison", eq_type="mode")])
    select = _selects(MapperRegistry().map_all(snapshot.eq_logics[69], snapshot))[0]
    assert select.reason_details["options"] == [n.lower() for n in names]


def test_linked_action_without_constant_value_is_not_an_option(caplog):
    cmds = [
        {"id": 70, "name": "Température", "generic_type": "TEMPERATURE", "type": "info", "sub_type": "numeric"},
        {"id": 71, "name": "Mode", "generic_type": "MODE_STATE", "type": "info", "sub_type": "string"},
        {"id": 72, "name": "Jour", "generic_type": "MODE_SET_STATE", "type": "action", "sub_type": "other",
         "virtual_info_id": "71", "virtual_value": "jour"},
        {"id": 73, "name": "Nuit", "generic_type": "MODE_SET_STATE", "type": "action", "sub_type": "other",
         "virtual_info_id": "71", "virtual_value": "nuit"},
        {"id": 74, "name": "Calcul", "generic_type": "MODE_SET_STATE", "type": "action", "sub_type": "other",
         "virtual_info_id": "71", "virtual_value": "#71# + 1"},
    ]
    snapshot = _snapshot([_raw(69, cmds, name="Modes maison", eq_type="mode")])
    with caplog.at_level("WARNING"):
        select = _selects(MapperRegistry().map_all(snapshot.eq_logics[69], snapshot))[0]
    assert select.reason_details["options"] == ["jour", "nuit"]  # jamais « Calcul » par repli sur le nom
    assert any("sans valeur constante" in r.message and r.levelname == "WARNING" for r in caplog.records)


# --- Source 2 : action « liste » -------------------------------------------------------------

def test_list_action_gives_its_values_as_options():
    eq, snapshot = _mode_eq(CLIM_ID)
    results = MapperRegistry().map_all(eq, snapshot)
    assert results[0].ha_entity_type == "switch" and results[0].ha_name == "Prise climatiseur"  # inchangé
    select = _selects(results)[0]
    assert select.reason_code == "select_action_select"
    assert select.reason_details["options"] == ["Froid", "Chaud", "Auto"]  # les libellés
    assert select.reason_details["value_to_option"] == {"cool": "Froid", "heat": "Chaud", "auto": "Auto"}


@pytest.mark.parametrize("raw,expected", [
    ("a|A;b|B", [("a", "A"), ("b", "B")]), ("a;b", [("a", "a"), ("b", "b")]),
    ("a|A;", [("a", "A")]), ("", []), (None, []), ("|A;b", []),
])
def test_list_value_parsing(raw, expected):
    assert parse_list_value(raw) == expected


# --- Pas de devinette --------------------------------------------------------------------------

@pytest.mark.parametrize("eq_id", [DOUBLON_ID, EXPRESSION_ID, SEUL_ETAT_ID])
def test_no_select_when_options_are_not_certain(eq_id):
    eq, snapshot = _mode_eq(eq_id)
    assert _selects(MapperRegistry().map_all(eq, snapshot)) == []


@pytest.mark.parametrize("field,value,expected", [
    ("virtual_value", "manu", "manu"), ("virtual_value", "Mode Eco", "Mode Eco"), ("virtual_value", "1", "1"),
    ("virtual_value", "-2.5", "-2.5"), ("virtual_value", "#12# + 1", None), ("virtual_value", "a-b", None),
    ("virtual_value", '"x"', None), ("virtual_value", "  ", None),
    ("update_cmd_to_value", "Absence", "Absence"), ("update_cmd_to_value", "#slider#", None),
])
def test_only_constant_values_are_options(field, value, expected):
    link = "virtual_info_id" if field == "virtual_value" else "update_cmd_id"
    action = JeedomCmd(id=2, name="x", type="action", sub_type="other", **{link: 1, field: value})
    assert written_value(action, 1) == expected


def test_two_list_actions_on_the_same_info_are_refused():
    cmds = [
        {"id": 1, "name": "Mode", "type": "info", "sub_type": "string"},
        {"id": 2, "name": "A", "type": "action", "sub_type": "select", "linked_value": "1", "list_value": "a;b"},
        {"id": 3, "name": "B", "type": "action", "sub_type": "select", "linked_value": "1", "list_value": "c;d"},
        {"id": 4, "name": "Etat", "generic_type": "ENERGY_STATE", "type": "info", "sub_type": "binary"},
    ]
    snapshot = _snapshot([_raw(10, cmds)])
    assert SelectMapper().map_all(snapshot.eq_logics[10], snapshot) == []


# --- Découverte --------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_select_discovery_payload_and_topic():
    eq, snapshot = _heater()
    select = _selects(MapperRegistry().map_all(eq, snapshot))[0]

    class _B:
        def __init__(self):
            self.calls = []

        def publish_message(self, topic, payload, qos=1, retain=False):
            self.calls.append((topic, json.loads(payload), retain))
            return True

    bridge = _B()
    assert await DiscoveryPublisher(bridge).publish_select(select, snapshot) is True
    topic, payload, retain = bridge.calls[0]
    assert topic == "homeassistant/select/jeedom2ha_554_select_5489/config" and retain is True
    assert payload["unique_id"] == "jeedom2ha_eq_554_select_5489"
    assert payload["options"] == ["Absence", "manu", "auto"]
    assert payload["state_topic"] == "jeedom2ha/554/select_5489/state"
    assert payload["command_topic"] == "jeedom2ha/554/select_5489/set"
    assert payload["optimistic"] is False
    assert payload["default_entity_id"] == "select.jeedom2ha_554_select_5489"
    assert payload["device"]["identifiers"] == ["jeedom2ha_554"]


# --- État ----------------------------------------------------------------------------------------

class _StateBridge:
    def __init__(self):
        self.is_connected = True
        self.published = []

    def publish_message(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload))
        return True


@pytest.mark.asyncio
@pytest.mark.parametrize("value,expected", [
    ("manu", "manu"), ("Absence", "Absence"), ("auto", "auto"),
    ("Manu", SELECT_UNKNOWN_PAYLOAD), ("absence", SELECT_UNKNOWN_PAYLOAD), ("off", SELECT_UNKNOWN_PAYLOAD),
])
async def test_state_is_the_exact_option_or_unknown(value, expected):
    eq, snapshot = _heater()
    primary = MapperRegistry().map(eq, snapshot)
    _decision(primary)
    for secondary in primary.additional_mappings:
        _decision(secondary)
    bridge = _StateBridge()
    sync = StateSynchronizer(app={"publications": {CHAUFFE_EAU_ID: primary.publication_decision_ref}}, mqtt_bridge=bridge)
    assert sync.streams_actionable_type("select") is True
    assert await sync.handle_state_message(CHAUFFE_EAU_ID, 5489, value) is True
    assert bridge.published == [("jeedom2ha/554/select_5489/state", expected)]


def test_list_label_is_read_as_its_value():
    eq, snapshot = _mode_eq(CLIM_ID)
    select = _selects(MapperRegistry().map_all(eq, snapshot))[0]
    sync = StateSynchronizer(app={}, mqtt_bridge=_StateBridge())
    assert sync._translate_value(select, "heat") == "Chaud"  # valeur → libellé
    assert sync._translate_value(select, "Froid") == "Froid"
    assert sync._translate_value(select, "dry") == SELECT_UNKNOWN_PAYLOAD


def test_list_numbers_are_normalised():
    cmds = [
        {"id": 81, "name": "Programme", "type": "info", "sub_type": "string"},
        {"id": 82, "name": "Choisir", "type": "action", "sub_type": "select", "linked_value": "81",
         "list_value": "0|Arrêt;1|Marche;2|Auto"},
        {"id": 83, "name": "Etat", "generic_type": "ENERGY_STATE", "type": "info", "sub_type": "binary"},
    ]
    snapshot = _snapshot([_raw(80, cmds)])
    select = _selects(MapperRegistry().map_all(snapshot.eq_logics[80], snapshot))[0]
    sync = StateSynchronizer(app={}, mqtt_bridge=_StateBridge())
    assert sync._translate_value(select, "2.0") == "Auto"
    assert sync._translate_value(select, 1) == "Marche"
    assert sync._translate_value(select, "3") == SELECT_UNKNOWN_PAYLOAD


# --- Ordres --------------------------------------------------------------------------------------

def _cmd_sync(primary):
    decision = _decision(primary)
    for secondary in primary.additional_mappings:
        _decision(secondary)
    bridge = _StateBridge()
    sync = CommandSynchronizer(app={"publications": {primary.jeedom_eq_id: decision}, "state_synchronizer": None},
                               mqtt_bridge=bridge, jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
                               jeedom_core_apikey="core-apikey")
    sync._execute_exec_cmd = AsyncMock(return_value=True)
    return sync, bridge


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,cmd_id", [("manu", 5490), ("auto", 5491), ("Absence", 5372)])
async def test_an_option_runs_its_own_action(payload, cmd_id):
    eq, snapshot = _heater()
    sync, bridge = _cmd_sync(MapperRegistry().map(eq, snapshot))
    assert await sync.handle_command_message("jeedom2ha/554/select_5489/set", payload) is True
    sync._execute_exec_cmd.assert_awaited_once_with(cmd_id, {})
    assert bridge.published == []  # jamais d'état supposé


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ["MANU", "Manu", " manu", "ON", "", "None"])
async def test_other_payloads_are_refused(payload):
    eq, snapshot = _heater()
    sync, _bridge = _cmd_sync(MapperRegistry().map(eq, snapshot))
    assert await sync.handle_command_message("jeedom2ha/554/select_5489/set", payload) is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("topic", [
    "jeedom2ha/554/5489/set",            # ancien topic (identité par commande d'avant la relecture)
    "jeedom2ha/554/set",                 # topic du switch : « manu » n'y est pas un ordre On/Off
    "jeedom2ha/554/select_5530/set",     # select d'une autre info
    "jeedom2ha/553/select_5489/set",     # autre équipement
    "jeedom2ha/554/select_5489x/set",    # suffixe parasite
    "jeedom2ha/554/select_5489/set/x",
])
async def test_no_other_topic_ever_runs_a_select_action(topic):
    eq, snapshot = _heater()
    sync, _bridge = _cmd_sync(MapperRegistry().map(eq, snapshot))
    for payload in ("manu", "auto", "Absence"):
        assert await sync.handle_command_message(topic, payload) is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_the_switch_still_drives_the_relay_next_to_the_select():
    eq, snapshot = _heater()
    sync, _bridge = _cmd_sync(MapperRegistry().map(eq, snapshot))
    assert await sync.handle_command_message("jeedom2ha/554/set", "ON") is True
    assert sync._execute_exec_cmd.await_args.args[0] == 5706


@pytest.mark.asyncio
async def test_a_list_option_is_sent_as_select():
    eq, snapshot = _mode_eq(CLIM_ID)
    sync, _bridge = _cmd_sync(MapperRegistry().map(eq, snapshot))
    assert await sync.handle_command_message("jeedom2ha/9821/select_982104/set", "Chaud") is True
    sync._execute_exec_cmd.assert_awaited_once_with(982105, {"select": "heat"})


# --- Voie manuelle : « Corriger le type » → « Mode (état) » / « Mode (commande) » ---------------

def _manual_eq(info_generic=None, action_generic=None):
    cmds = [
        {"id": 41, "name": "Etat", "generic_type": "ENERGY_STATE", "type": "info", "sub_type": "binary"},
        {"id": 42, "name": "On", "generic_type": "ENERGY_ON", "type": "action", "sub_type": "other"},
        {"id": 43, "name": "Off", "generic_type": "ENERGY_OFF", "type": "action", "sub_type": "other"},
        {"id": 44, "name": "Programme", "generic_type": info_generic, "type": "info", "sub_type": "string"},
        {"id": 45, "name": "Jour", "generic_type": action_generic, "type": "action", "sub_type": "other"},
        {"id": 46, "name": "Nuit", "generic_type": action_generic, "type": "action", "sub_type": "other"},
    ]
    snapshot = _snapshot([_raw(40, cmds, name="Ventilation", eq_type="zwavejs")])
    return snapshot.eq_logics[40], snapshot


def _roles_overrides(*cmd_ids):
    return {f"40:{c}": {"source": "user", "ha_entity_type": "select"} for c in cmd_ids}


def _evaluate(eq, snapshot, overrides):
    return evaluate_equipment(eq, snapshot, assess_eligibility(eq), mapper_registry=MapperRegistry(),
                              persisted_overrides=overrides)


def _tree_rows(eq, snapshot, tmp_path, overrides=None):
    tree = _build_mapping_override_tree(eq, snapshot, str(tmp_path), overrides_cache=overrides or {},
                                        equipment_overrides_cache={})
    return {r["jeedom_cmd_id"]: r for r in tree["commands"]}


@pytest.mark.parametrize("info_generic,action_generic", [(None, None), ("MODE_STATE", None), (None, "MODE_SET_STATE")])
def test_nothing_is_recognised_without_both_roles(info_generic, action_generic):
    eq, snapshot = _manual_eq(info_generic, action_generic)
    assert _selects(MapperRegistry().map_all(eq, snapshot)) == []


def test_mode_state_typed_by_hand_when_the_actions_carry_mode_set_state(tmp_path):
    """Info sans MODE_STATE, actions en MODE_SET_STATE : « Mode (état) » sur l'info suffit."""
    eq, snapshot = _manual_eq(action_generic="MODE_SET_STATE")
    generic_before = [(c.id, c.generic_type) for c in eq.cmds]
    rows = _tree_rows(eq, snapshot, tmp_path)
    assert rows[44]["override_types_allowed"] == ["select"] and rows[44]["mode_role"] == "state"
    assert "mode_role" not in rows[41]
    overrides = _roles_overrides(44)
    assert mode_roles_for(eq, overrides) == {44: "state"}
    evaluation = _evaluate(eq, snapshot, overrides)
    assert evaluation.mapping.ha_entity_type == "switch"  # principal inchangé
    selects = _selects(evaluation.mapping.additional_mappings)
    assert len(selects) == 1 and selects[0].reason_details["options"] == ["Jour", "Nuit"]
    assert [(c.id, c.generic_type) for c in eq.cmds] == generic_before  # types Jeedom intacts
    assert snapshot.mode_roles == {}  # snapshot jamais muté


def test_mode_commands_typed_by_hand_one_by_one(tmp_path):
    """Info en MODE_STATE, actions sans type : « Mode (commande) » action par action ; chaque étape
    a un aperçu publiable (une option, puis deux)."""
    eq, snapshot = _manual_eq(info_generic="MODE_STATE")
    rows = _tree_rows(eq, snapshot, tmp_path)
    assert rows[45]["override_types_allowed"] == ["select"] and rows[45]["mode_role"] == "command"
    assert "select" not in rows[42]["override_types_allowed"]  # l'ordre On du relais n'est pas un mode
    one = _selects(_evaluate(eq, snapshot, _roles_overrides(45)).mapping.additional_mappings)
    assert one[0].reason_details["options"] == ["Jour"]
    two = _selects(_evaluate(eq, snapshot, _roles_overrides(45, 46)).mapping.additional_mappings)
    assert two[0].reason_details["options"] == ["Jour", "Nuit"]


def test_untyped_info_and_actions_offer_no_role(tmp_path):
    """Limite assumée : sans aucun côté reconnu, aucun aperçu ne serait publiable ; rien n'est proposé."""
    eq, snapshot = _manual_eq()
    rows = _tree_rows(eq, snapshot, tmp_path)
    assert all("mode_role" not in row for row in rows.values())


def test_a_mode_role_never_retypes_another_entity():
    eq, snapshot = _manual_eq()
    switch = MapperRegistry().map(eq, snapshot)
    patched = apply_type_override(switch, "/nonexistent", overrides={"40:42": {"source": "user", "ha_entity_type": "select"}})
    assert patched is switch


@pytest.mark.asyncio
async def test_preview_shows_the_select_a_mode_role_produces(aiohttp_client):
    eq_raw = {"id": 40, "name": "Ventilation", "eq_type": "zwavejs", "object_id": 1, "is_enable": True,
              "cmds": [{"id": c.id, "name": c.name, "generic_type": c.generic_type, "type": c.type, "sub_type": c.sub_type}
                       for c in _manual_eq(action_generic="MODE_SET_STATE")[0].cmds]}
    app = create_app(local_secret=SECRET)
    app["mqtt_bridge"] = _RawBridge()
    cli = await aiohttp_client(app)
    body = {"action": "sync", "payload": {"objects": [{"id": 1, "name": "Buanderie"}], "eq_logics": [eq_raw],
                                          "sync_config": {"confidence_policy": "sure_probable"}},
            "request_id": "p", "timestamp": "2026-11-15T00:00:00Z"}
    assert (await cli.post("/action/sync", json=body, headers=H)).status == 200
    resp = await cli.post("/system/overrides/preview", headers=H, json={"payload": {
        "jeedom_eq_id": 40, "jeedom_cmd_id": 44, "ha_entity_type": "select"}})
    payload = (await resp.json())["payload"]
    assert payload["covered"] is True
    assert payload["overridden"]["should_publish"] is True
    assert [e["ha_entity_type"] for e in payload["entities_after"] if e["will_publish"]].count("select") == 1


# --- Installation existante : seuls des select s'ajoutent -------------------------------------------

class _RawBridge:
    def __init__(self) -> None:
        self.is_connected = True
        self.state = "connected"
        self.broker_info = "broker.example.test:1883"
        self.calls = []

    def publish_message(self, topic, payload, qos=1, retain=False):
        self.calls.append({"topic": topic, "payload": payload, "qos": qos, "retain": retain})
        return True


async def _project(aiohttp_client):
    app = create_app(local_secret=SECRET)
    bridge = _RawBridge()
    app["mqtt_bridge"] = bridge
    cli = await aiohttp_client(app)
    resp = await cli.post("/action/sync", json=sync_body(load_scene(), "select"), headers=H)
    assert resp.status == 200, await resp.text()
    return app, cli, {"mqtt": bridge.calls, "entities": entity_commands(app["mappings"])}


@pytest.mark.asyncio
async def test_existing_installation_only_gains_selects(aiohttp_client):
    """Ligne de base capturée sur le correctif fix/switch-appariement-etat (b81d81d), même scène, formes réelles comprises."""
    base = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    _app, _cli, now = await _project(aiohttp_client)
    assert len(base["entities"]) > 80, "scène trop pauvre pour être une preuve"
    changed = {u for u in set(base["entities"]) | set(now["entities"])
               if base["entities"].get(u) != now["entities"].get(u)}
    assert changed == {"jeedom2ha_eq_554_select_5489", "jeedom2ha_eq_9820_select_982002",
                       "jeedom2ha_eq_9821_select_982104", f"jeedom2ha_eq_{MODES_ID}_select_983301"}
    assert all(u not in base["entities"] and now["entities"][u]["type"] == "select" for u in changed)

    def key(call):
        return json.dumps(call, sort_keys=True)
    b, a = Counter(map(key, base["mqtt"])), Counter(map(key, now["mqtt"]))
    assert list((b - a).elements()) == []  # aucun message existant ne change ni ne disparaît
    added = [json.loads(k) for k in (a - b).elements()]
    assert sorted(c["topic"] for c in added) == [
        "homeassistant/select/jeedom2ha_554_select_5489/config",
        "homeassistant/select/jeedom2ha_9820_select_982002/config",
        "homeassistant/select/jeedom2ha_9821_select_982104/config",
        f"homeassistant/select/jeedom2ha_{MODES_ID}_select_983301/config",
    ]
    assert [c for c in now["mqtt"] if c not in added] == base["mqtt"]  # ordre identique pour le reste
    # « Modes » : le bouton d'équipement (sur « Rejouer ») reste tel quel, le select s'ajoute.
    assert base["entities"][f"jeedom2ha_eq_{MODES_ID}"] == now["entities"][f"jeedom2ha_eq_{MODES_ID}"]
    # Formes réelles (volet, lumière, routeur à listes sur infos numériques, borne, serrure à état
    # texte) : aucun select, aucun doublon.
    for eq_id in (VOLET_ID, VOITURE_ID, ROUTEUR_ID, BORNE_ID, SERRURE_ID):
        mine = [u for u in now["entities"] if u == f"jeedom2ha_eq_{eq_id}" or u.startswith(f"jeedom2ha_eq_{eq_id}_")]
        assert mine and all(now["entities"][u]["type"] != "select" for u in mine), eq_id
    assert not any(c["topic"].startswith("homeassistant/select/") and c not in added for c in now["mqtt"])


@pytest.mark.asyncio
async def test_4d_contract_is_unchanged_for_the_scene(aiohttp_client):
    _app, cli, _now = await _project(aiohttp_client)
    resp = await cli.get("/system/diagnostics", headers=H)
    assert resp.status == 200
    equipments = {e["eq_id"]: e for e in (await resp.json())["payload"]["equipments"]}
    for eq in equipments.values():
        assert eq["perimetre"] == reason_code_to_perimetre(eq["reason_code"])
        assert eq["ecart"] is compute_ecart(eq["perimetre"], eq["statut"])
    heater = equipments[CHAUFFE_EAU_ID]
    assert (heater["perimetre"], heater["statut"], heater["ecart"], heater["ha_type"]) == ("inclus", "publie", False, "switch")
    clim = equipments[CLIM_ID]
    assert (clim["statut"], clim["ha_type"]) == ("publie", "switch")


def test_no_select_when_its_actions_are_already_buttons():
    """MODE_SET_STATE déjà publiées en bouton : la projection d'avant est gardée telle quelle, et aucun
    select ne reprend ces actions (jamais deux entités qui pilotent la même commande)."""
    cmds = [
        {"id": 51, "name": "Mode", "generic_type": "MODE_STATE", "type": "info", "sub_type": "string"},
        {"id": 52, "name": "Jour", "generic_type": "MODE_SET_STATE", "type": "action", "sub_type": "other"},
        {"id": 53, "name": "Nuit", "generic_type": "MODE_SET_STATE", "type": "action", "sub_type": "other"},
    ]
    snapshot = _snapshot([_raw(50, cmds, name="Programmateur", eq_type="zwavejs")])
    registry = MapperRegistry()
    before = registry._map_all_base(snapshot.eq_logics[50], snapshot)
    assert before and before[0].ha_entity_type == "button"
    assert registry.map_all(snapshot.eq_logics[50], snapshot) == before


def test_a_taken_unique_id_is_never_reused():
    eq, snapshot = _heater()
    assert SelectMapper().map_all(eq, snapshot, taken_unique_ids={"jeedom2ha_eq_554_select_5489"}) == []
    assert SelectMapper().map_all(eq, snapshot, carried_cmd_ids={5490}) == []  # une action portée : rien
    assert SelectMapper().map_all(eq, snapshot, carried_cmd_ids={5489}) == []  # l'info portée : rien


# --- « Modes » (forme réelle relue en prod, plugin mode) ---------------------------------------------

_MODE_NAMES = ["Absent", "Normal", "Vacances scolaires", "Travail", "Soirée", "Nuit", "Réveil"]


def _real_modes_cmds():
    return [
        {"id": 3775, "name": "Rejouer", "generic_type": "MODE_SET_STATE", "type": "action", "sub_type": "other"},
        {"id": 651, "name": "Mode", "logical_id": "currentMode", "generic_type": "MODE_STATE", "type": "info",
         "sub_type": "string", "current_value": "Normal"},
        {"id": 1730, "name": "previousMode", "generic_type": "DONT", "type": "info", "sub_type": "string"},
        {"id": 3376, "name": "lock_state", "type": "info", "sub_type": "binary"},
        *[{"id": cid, "name": n, "generic_type": "MODE_SET_STATE", "type": "action", "sub_type": "other",
           "linked_value": "651"} for cid, n in zip((657, 658, 659, 1657, 1654, 1655, 1658), _MODE_NAMES)],
        {"id": 652, "name": "Retour mode précédent", "generic_type": "MODE_SET_STATE", "type": "action",
         "sub_type": "other", "linked_value": ""},
        {"id": 3375, "name": "Aller au mode suivant", "generic_type": "MODE_SET_STATE", "type": "action",
         "sub_type": "other"},
        {"id": 3377, "name": "lock", "type": "action", "sub_type": "other", "linked_value": "3376"},
        {"id": 3378, "name": "unlock", "type": "action", "sub_type": "other", "linked_value": "3376"},
    ]


def _real_modes():
    snapshot = _snapshot([_raw(104, _real_modes_cmds(), name="Modes", eq_type="mode")])
    return snapshot.eq_logics[104], snapshot


def test_real_modes_get_a_select_of_the_seven_linked_modes_and_keep_the_replay_button():
    eq, snapshot = _real_modes()
    registry = MapperRegistry()
    before = registry._map_all_base(eq, snapshot)
    assert [(r.ha_entity_type, r.ha_unique_id) for r in before] == [("button", "jeedom2ha_eq_104")]
    assert [c.id for c in before[0].commands.values()] == [3775]  # « Rejouer », non reliée
    results = registry.map_all(eq, snapshot)
    assert results[:1] == before  # le bouton reste tel quel, aucun retrait
    select = results[1]
    assert (select.ha_entity_type, select.ha_unique_id) == ("select", "jeedom2ha_eq_104_select_651")
    assert select.reason_details["options"] == _MODE_NAMES  # les NOMS des 7 actions reliées
    ids = {e["cmd_id"] for e in select.reason_details["option_commands"].values()}
    assert ids == {657, 658, 659, 1657, 1654, 1655, 1658}
    assert not ids & {3775, 652, 3375, 3377, 3378}  # jamais Rejouer, Retour, Suivant, lock, unlock


@pytest.mark.asyncio
async def test_real_modes_state_is_the_current_mode_or_unknown():
    eq, snapshot = _real_modes()
    primary = MapperRegistry().map(eq, snapshot)
    _decision(primary)
    for secondary in primary.additional_mappings:
        _decision(secondary)
    bridge = _StateBridge()
    sync = StateSynchronizer(app={"publications": {104: primary.publication_decision_ref}}, mqtt_bridge=bridge)
    assert await sync.handle_state_message(104, 651, "Normal") is True
    assert await sync.handle_state_message(104, 651, "Inconnu") is True
    assert bridge.published == [("jeedom2ha/104/select_651/state", "Normal"),
                                ("jeedom2ha/104/select_651/state", SELECT_UNKNOWN_PAYLOAD)]


@pytest.mark.asyncio
async def test_real_modes_option_runs_its_action():
    eq, snapshot = _real_modes()
    sync, _bridge = _cmd_sync(MapperRegistry().map(eq, snapshot))
    assert await sync.handle_command_message("jeedom2ha/104/select_651/set", "Vacances scolaires") is True
    sync._execute_exec_cmd.assert_awaited_once_with(659, {})


def test_core_value_link_with_a_non_constant_written_value_is_still_refused(caplog):
    """La règle « nom de l'action » ne vaut que pour la « Valeur » du cœur seule : une action qui
    porte aussi un updateCmdId vers l'info avec une valeur calculée reste refusée."""
    cmds = _real_modes_cmds()
    for cmd in cmds:
        if cmd["id"] == 657:
            cmd.update({"update_cmd_id": "651", "update_cmd_to_value": "#slider#"})
    snapshot = _snapshot([_raw(104, cmds, name="Modes", eq_type="mode")])
    with caplog.at_level("WARNING"):
        select = _selects(MapperRegistry().map_all(snapshot.eq_logics[104], snapshot))[0]
    assert "Absent" not in select.reason_details["options"]
    assert any("sans valeur constante" in r.message for r in caplog.records)


@pytest.mark.parametrize("sub_type", ["numeric", "binary"])
def test_real_modes_name_fallback_needs_a_text_info(sub_type, caplog):
    """Le repli sur le nom de l'action n'existe que pour une info texte : la forme réelle de « Modes »
    avec l'info 651 en numérique ou en binaire ne donne aucun select (les 7 actions sont refusées)."""
    cmds = _real_modes_cmds()
    for cmd in cmds:
        if cmd["id"] == 651:
            cmd["sub_type"] = sub_type
            cmd.pop("current_value")
    snapshot = _snapshot([_raw(104, cmds, name="Modes", eq_type="mode")])
    with caplog.at_level("WARNING"):
        results = MapperRegistry().map_all(snapshot.eq_logics[104], snapshot)
    assert _selects(results) == []
    assert [(r.ha_entity_type, r.ha_unique_id) for r in results] == [("button", "jeedom2ha_eq_104")]
    assert any("sans valeur constante" in r.message for r in caplog.records)


def test_modes_taken_by_a_switch_leave_no_select_of_the_unlinked_actions():
    """Cas reproduit en relecture : les 7 actions de mode reliées à 651 sont prises par un interrupteur
    (typées autrement que MODE_SET_STATE). Les actions MODE_SET_STATE restantes (« Rejouer »,
    « Retour mode précédent », « Aller au mode suivant ») ne sont reliées à rien : elles ne deviennent
    pas un select à 3 choix parasites, car une action de l'équipement est reliée au mode."""
    cmds = _real_modes_cmds()
    for cmd in cmds:
        if cmd.get("linked_value") == "651":
            cmd["generic_type"] = {657: "ENERGY_ON", 658: "ENERGY_OFF"}.get(cmd["id"])
    snapshot = _snapshot([_raw(104, cmds, name="Modes", eq_type="mode")])
    results = MapperRegistry().map_all(snapshot.eq_logics[104], snapshot)
    assert [r.ha_entity_type for r in results] == ["switch"]
    assert _selects(results) == []


def test_unlinked_mode_fallback_keeps_the_action_names_without_any_link():
    """Comportement voulu de la branche « aucune action reliée » conservé : sans aucun lien dans
    l'équipement, le type générique « Mode » donne les noms des actions (thermostat de démonstration)."""
    eq, snapshot = _mode_eq(THERMOSTAT_ID)
    assert not any(c.linked_info_ids() for c in eq.cmds)
    select = _selects(MapperRegistry().map_all(eq, snapshot))[0]
    assert select.reason_details["options"] == ["Confort", "Eco", "Hors-gel"]


@pytest.mark.asyncio
async def test_real_modes_select_takes_the_command_name_not_its_logical_id():
    """Le nom du select est le NOM de la commande info (« Mode »), jamais son logicalId
    (« currentMode ») : même rendu que les autres entités secondaires (binary_sensor secondaire)."""
    eq, snapshot = _real_modes()
    assert eq.cmds[[c.id for c in eq.cmds].index(651)].logical_id == "currentMode"
    select = _selects(MapperRegistry().map_all(eq, snapshot))[0]
    assert select.ha_name == "Mode"

    class _B:
        def __init__(self):
            self.calls = []

        def publish_message(self, topic, payload, qos=1, retain=False):
            self.calls.append((topic, json.loads(payload), retain))
            return True

    bridge = _B()
    assert await DiscoveryPublisher(bridge).publish_select(select, snapshot) is True
    payload = bridge.calls[0][1]
    assert payload["name"] == "Mode"
    assert "currentMode" not in json.dumps(payload)


def test_outside_mode_types_a_constant_value_is_still_required():
    """Hors du couple MODE_STATE / MODE_SET_STATE, un lien par la « Valeur » du cœur sans valeur écrite
    ne donne jamais d'option (pas de repli sur le nom)."""
    cmds = [
        {"id": 1, "name": "Programme", "type": "info", "sub_type": "string"},
        {"id": 2, "name": "Jour", "type": "action", "sub_type": "other", "linked_value": "1"},
        {"id": 3, "name": "Nuit", "type": "action", "sub_type": "other", "linked_value": "1"},
        {"id": 4, "name": "Etat", "generic_type": "ENERGY_STATE", "type": "info", "sub_type": "binary"},
    ]
    snapshot = _snapshot([_raw(10, cmds)])
    assert _selects(MapperRegistry().map_all(snapshot.eq_logics[10], snapshot)) == []
