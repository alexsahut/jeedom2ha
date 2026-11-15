"""fix/switch-appariement-etat — le switch choisit la paire On / Off reliée à l'info d'état retenue.

Cas réel (anonymisé) : un chauffe-eau virtuel porte deux paires ENERGY_ON / ENERGY_OFF. La paire
« On_5701 / Off_5702 » pilote le relais et met à jour l'état « activé » (``updateCmdId`` du cœur) ;
la paire « Manu / auto » change seulement le mode (info « etat », ``infoId`` du plugin virtual).
Avant ce correctif, le mapper gardait la dernière action vue : le switch changeait le mode au lieu
du relais.

Règles :
- une paire reliée sans ambiguïté → retenue ;
- une seule paire, reliée ou non → comportement d'avant, inchangé ;
- plusieurs paires sans lien univoque → pas de switch, raison ``switch_pairing_ambiguous``.
"""

from __future__ import annotations

import json
from collections import Counter
from unittest.mock import AsyncMock, MagicMock

import pytest

from mapping.pairing import SWITCH_PAIRING_AMBIGUOUS, pair_on_off
from mapping.presence_switch import PresenceSwitchMapper
from mapping.registry import MapperRegistry
from models.cause_mapping import resolve_cause_ux
from models.evaluate_equipment import evaluate_equipment
from models.mapping import PublicationDecision
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot, assess_eligibility
from models.ui_contract_4d import compute_ecart, reason_code_to_perimetre
from sync.command import CommandSynchronizer
from transport.http_server import create_app
from validation.ha_component_registry import validate_projection

from .fix_switch_appariement_corpus import (
    BASELINE_PATH,
    CHAUFFE_EAU_ID,
    CHAUFFE_EAU_SANS_LIEN_ID,
    chauffe_eau_cmds,
    entity_commands,
    load_scene,
    sync_body,
)

SECRET = "test-secret-appariement"
H = {"X-Local-Secret": SECRET}


def _snapshot_of(eq_logics) -> TopologySnapshot:
    return TopologySnapshot.from_jeedom_payload({
        "objects": [{"id": 1, "name": "Local technique"}, {"id": 2, "name": "Entrée"}],
        "eq_logics": eq_logics,
    })


def _eq_raw(eq_id, cmds, name="Chauffe-eau", eq_type="virtual"):
    return {"id": eq_id, "name": name, "eq_type": eq_type, "object_id": 1, "is_enable": True, "cmds": cmds}


def _chauffe_eau(links=True, overrides=None):
    cmds = chauffe_eau_cmds(links=links)
    for cmd in cmds:
        cmd.update((overrides or {}).get(cmd["id"], {}))
    snapshot = _snapshot_of([_eq_raw(CHAUFFE_EAU_ID, cmds)])
    return snapshot.eq_logics[CHAUFFE_EAU_ID], snapshot


def _roles(mapping):
    return {role: int(cmd.id) for role, cmd in mapping.commands.items()}


# --- Lecture des liens (modèle JeedomCmd, en ajout seulement) ---------------------------------

def test_links_are_read_from_the_topology_payload():
    eq, _ = _chauffe_eau()
    by_id = {c.id: c for c in eq.cmds}
    assert by_id[5706].update_cmd_id == 5708 and by_id[5706].update_cmd_to_value == "1"
    assert by_id[5490].virtual_info_id == 5489 and by_id[5490].virtual_value == "manu"
    assert by_id[5372].virtual_value == "Absence"  # casse gardée
    assert by_id[5706].linked_info_ids() == frozenset({5708})
    assert by_id[5490].linked_info_ids() == frozenset({5489})
    assert by_id[5708].linked_info_ids() == frozenset()


@pytest.mark.parametrize("raw,expected", [
    ({"update_cmd_id": "#12#"}, 12), ({"update_cmd_id": 12}, 12), ({"update_cmd_id": ""}, None),
    ({"update_cmd_id": "#12# + 1"}, None), ({"update_cmd_id": True}, None), ({}, None),
])
def test_unreadable_link_is_never_guessed(raw, expected):
    cmd = {"id": 1, "name": "x", "type": "action", "sub_type": "other", **raw}
    snapshot = _snapshot_of([_eq_raw(10, [cmd])])
    assert snapshot.eq_logics[10].cmds[0].update_cmd_id == expected


def test_payload_without_link_fields_keeps_the_defaults():
    """PHP d'avant : aucune clé de lien, les champs valent None (lecture identique à avant)."""
    eq, _ = _chauffe_eau(links=False)
    for cmd in eq.cmds:
        assert cmd.update_cmd_id is None and cmd.virtual_info_id is None
        assert cmd.update_cmd_to_value is None and cmd.virtual_value is None
        assert cmd.linked_info_ids() == frozenset()


# --- Lot A : le cas du chauffe-eau ------------------------------------------------------------

def test_water_heater_switch_drives_the_relay_not_the_mode():
    eq, snapshot = _chauffe_eau()
    switch = MapperRegistry().map(eq, snapshot)
    assert switch.ha_entity_type == "switch"
    assert switch.ha_unique_id == "jeedom2ha_eq_554"  # identité inchangée
    assert switch.confidence == "sure"
    assert switch.reason_code == "switch_on_off_state"
    assert _roles(switch) == {"ENERGY_STATE": 5708, "ENERGY_ON": 5706, "ENERGY_OFF": 5707}


@pytest.mark.parametrize("link_field", ["linked_value", "update_cmd_id"])
def test_core_value_field_is_also_a_link(link_field):
    """Le champ « Valeur » du cœur (``linked_value``) relie aussi une action à son info."""
    eq, snapshot = _chauffe_eau(links=False, overrides={
        5706: {link_field: "5708"}, 5707: {link_field: "#5708#"},
        5490: {"linked_value": "5489"}, 5491: {"virtual_info_id": "5489"},
    })
    assert _roles(MapperRegistry().map(eq, snapshot))["ENERGY_ON"] == 5706


def test_mode_pair_unlinked_but_relay_pair_linked_is_enough():
    """Seule la paire reliée à l'état compte : l'autre peut n'avoir aucun lien."""
    eq, snapshot = _chauffe_eau(links=False, overrides={5706: {"update_cmd_id": "5708"}, 5707: {"update_cmd_id": "5708"}})
    assert _roles(MapperRegistry().map(eq, snapshot)) == {"ENERGY_STATE": 5708, "ENERGY_ON": 5706, "ENERGY_OFF": 5707}


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,cmd_id", [("ON", 5706), ("OFF", 5707)])
async def test_home_assistant_order_reaches_the_relay(payload, cmd_id):
    eq, snapshot = _chauffe_eau()
    switch = MapperRegistry().map(eq, snapshot)
    decision = PublicationDecision(should_publish=True, reason="sure", mapping_result=switch,
                                   active_or_alive=True, discovery_published=True)
    switch.publication_decision_ref = decision
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    sync = CommandSynchronizer(app={"publications": {CHAUFFE_EAU_ID: decision}, "state_synchronizer": None},
                               mqtt_bridge=bridge, jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
                               jeedom_core_apikey="core-apikey")
    sync._execute_exec_cmd = AsyncMock(return_value=True)
    assert await sync.handle_command_message(f"jeedom2ha/{CHAUFFE_EAU_ID}/set", payload) is True
    sync._execute_exec_cmd.assert_awaited_once()
    assert sync._execute_exec_cmd.await_args.args[0] == cmd_id


# --- Une seule paire : comportement d'avant ---------------------------------------------------

def _prise(on_extra=None, off_extra=None):
    cmds = [
        {"id": 11, "name": "Etat", "generic_type": "ENERGY_STATE", "type": "info", "sub_type": "binary"},
        {"id": 12, "name": "Mode", "type": "info", "sub_type": "string"},
        {"id": 13, "name": "On", "generic_type": "ENERGY_ON", "type": "action", "sub_type": "other", **(on_extra or {})},
        {"id": 14, "name": "Off", "generic_type": "ENERGY_OFF", "type": "action", "sub_type": "other", **(off_extra or {})},
    ]
    snapshot = _snapshot_of([_eq_raw(10, cmds, name="Prise", eq_type="zwavejs")])
    return snapshot.eq_logics[10], snapshot


@pytest.mark.parametrize("on_extra,off_extra", [
    (None, None),                                            # aucun lien
    ({"update_cmd_id": "11"}, {"linked_value": "11"}),       # reliée à l'état
    ({"virtual_info_id": "12"}, None),                       # reliée ailleurs : pas de devinette, inchangé
    ({"update_cmd_id": "12"}, {"update_cmd_id": "12"}),
])
def test_single_pair_keeps_the_previous_behaviour(on_extra, off_extra):
    eq, snapshot = _prise(on_extra, off_extra)
    switch = MapperRegistry().map(eq, snapshot)
    assert (switch.ha_entity_type, switch.confidence, switch.reason_code) == ("switch", "sure", "switch_on_off_state")
    assert _roles(switch) == {"ENERGY_STATE": 11, "ENERGY_ON": 13, "ENERGY_OFF": 14}


# --- Plusieurs paires, aucun lien univoque : pas de devinette ---------------------------------

@pytest.mark.parametrize("overrides", [
    {},                                                                   # aucun lien (PHP d'avant)
    {5706: {"update_cmd_id": "5708"}, 5490: {"update_cmd_id": "5708"},    # deux On reliés à l'état
     5707: {"update_cmd_id": "5708"}},
    {5706: {"update_cmd_id": "5708"}},                                    # aucun Off relié
    {5706: {"update_cmd_id": "5489"}, 5707: {"update_cmd_id": "5489"},    # tout relié au mode
     5490: {"update_cmd_id": "5489"}, 5491: {"update_cmd_id": "5489"}},
])
def test_ambiguous_pairs_are_not_published_as_a_switch(overrides):
    eq, snapshot = _chauffe_eau(links=False, overrides=overrides)
    switch = MapperRegistry().map(eq, snapshot)
    assert switch.ha_entity_type == "switch"
    assert switch.confidence == "ambiguous"
    assert switch.reason_code == SWITCH_PAIRING_AMBIGUOUS
    assert switch.capabilities.has_on_off is False
    # Aucune clé routable : rien ne peut être envoyé au relais ni au mode.
    assert not {"ENERGY_ON", "ENERGY_OFF"} & set(switch.commands)
    assert set(_roles(switch).values()) == {5708, 5706, 5707, 5490, 5491}
    assert switch.reason_details["pairing_candidates"] == {
        "ENERGY_ON": [5706, 5490], "ENERGY_OFF": [5707, 5491],
    }
    assert validate_projection("switch", switch.capabilities).reason_code == "ha_missing_command_topic"


def _evaluate(eq, snapshot, equipment_overrides=None):
    return evaluate_equipment(eq, snapshot, assess_eligibility(eq), mapper_registry=MapperRegistry(),
                              persisted_equipment_overrides=equipment_overrides)


def test_ambiguous_equipment_keeps_its_secondary_entities_and_names_the_cause():
    eq, snapshot = _chauffe_eau(links=False)
    evaluation = _evaluate(eq, snapshot)
    assert evaluation.equipment_decision.should_publish is False
    assert evaluation.equipment_decision.reason == "ambiguous_skipped"
    assert evaluation.mapping.reason_code == SWITCH_PAIRING_AMBIGUOUS
    assert all(d.should_publish for d in evaluation.secondary_decisions)  # capteurs inchangés
    by_cmd = {d.cmd_id: d for d in evaluation.command_decisions}
    for cmd_id in (5706, 5707, 5490, 5491, 5708):
        assert by_cmd[cmd_id].reason == "ambiguous_skipped"  # plus « sans équivalent »
    cause = resolve_cause_ux("ambiguous_skipped", 2, SWITCH_PAIRING_AMBIGUOUS)
    assert "On/Off" in cause["cause_label"]
    assert "Commande information à mettre à jour" in cause["cause_action"]
    assert "commande d'état liée" in cause["cause_action"] and "Valeur" not in cause["cause_action"]


def test_forcing_the_publication_never_pilots_an_ambiguous_switch():
    eq, snapshot = _chauffe_eau(links=False)
    forced = {str(CHAUFFE_EAU_ID): {"source": "user", "publication_override": "force_publish"}}
    decision = _evaluate(eq, snapshot, forced).equipment_decision
    assert decision.should_publish is False
    assert decision.reason == "ha_missing_command_topic"


# --- Présence actionnable (SET_ON / SET_OFF) : même règle -------------------------------------

def _presence(links):
    cmds = [
        {"id": 21, "name": "Présent", "generic_type": "PRESENCE", "type": "info", "sub_type": "binary"},
        {"id": 22, "name": "Vacances", "type": "info", "sub_type": "binary"},
        {"id": 23, "name": "Arriver", "generic_type": "SET_ON", "type": "action", "sub_type": "other",
         **({"update_cmd_id": "21"} if links else {})},
        {"id": 24, "name": "Partir", "generic_type": "SET_OFF", "type": "action", "sub_type": "other",
         **({"update_cmd_id": "21"} if links else {})},
        {"id": 25, "name": "Vacances on", "generic_type": "SET_ON", "type": "action", "sub_type": "other",
         **({"update_cmd_id": "22"} if links else {})},
        {"id": 26, "name": "Vacances off", "generic_type": "SET_OFF", "type": "action", "sub_type": "other",
         **({"update_cmd_id": "22"} if links else {})},
    ]
    snapshot = _snapshot_of([_eq_raw(20, cmds, name="Présence")])
    return snapshot.eq_logics[20], snapshot


def test_presence_switch_keeps_the_pair_linked_to_presence():
    eq, snapshot = _presence(links=True)
    switch = PresenceSwitchMapper().map(eq, snapshot)
    assert switch.confidence == "sure"
    assert _roles(switch) == {"PRESENCE": 21, "SET_ON": 23, "SET_OFF": 24}


def test_presence_switch_without_links_is_ambiguous():
    eq, snapshot = _presence(links=False)
    switch = PresenceSwitchMapper().map(eq, snapshot)
    assert (switch.confidence, switch.reason_code) == ("ambiguous", SWITCH_PAIRING_AMBIGUOUS)
    assert switch.capabilities.has_on_off is False
    assert not {"SET_ON", "SET_OFF"} & set(switch.commands)


def test_pairing_function_rules():
    def c(cmd_id, link=None):
        return JeedomCmd(id=cmd_id, name=str(cmd_id), type="action", update_cmd_id=link)
    state = JeedomCmd(id=1, name="s")
    assert pair_on_off([c(2)], [c(3)], None).status == "single"
    assert pair_on_off([], [c(3)], state).off.id == 3
    linked = pair_on_off([c(2, 1), c(4, 9)], [c(3, 1), c(5)], state)
    assert (linked.status, linked.on.id, linked.off.id) == ("linked", 2, 3)
    assert pair_on_off([c(2, 1), c(4, 1)], [c(3, 1)], state).status == "ambiguous"
    assert pair_on_off([c(2, 1), c(4, 9)], [], state).on.id == 2
    assert pair_on_off([c(2), c(4)], [c(3)], None).status == "ambiguous"


# --- Projection d'une installation existante (scène représentative) ----------------------------

class _RawBridge:
    def __init__(self) -> None:
        self.is_connected = True
        self.state = "connected"
        self.broker_info = "broker.example.test:1883"
        self.calls = []

    def publish_message(self, topic, payload, qos=1, retain=False):
        self.calls.append({"topic": topic, "payload": payload, "qos": qos, "retain": retain})
        return True


async def _project(aiohttp_client, links):
    app = create_app(local_secret=SECRET)
    bridge = _RawBridge()
    app["mqtt_bridge"] = bridge
    cli = await aiohttp_client(app)
    resp = await cli.post("/action/sync", json=sync_body(load_scene(links), "appariement"), headers=H)
    assert resp.status == 200, await resp.text()
    return app, cli, {"mqtt": bridge.calls, "entities": entity_commands(app["mappings"])}


def _baseline():
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _mqtt_delta(before, after):
    """(retirés, ajoutés) en multiensemble : l'ordre n'est comparé qu'hors des équipements visés."""
    def key(call):
        return json.dumps(call, sort_keys=True)
    b, a = Counter(map(key, before)), Counter(map(key, after))
    return [json.loads(k) for k in (b - a).elements()], [json.loads(k) for k in (a - b).elements()]


def _outside(calls, eq_ids):
    marks = [f"jeedom2ha_{i}" for i in eq_ids] + [f"jeedom2ha/{i}/" for i in eq_ids]
    return [c for c in calls if not any(m in c["topic"] for m in marks)]


def _changed(before, after):
    return {uid for uid in set(before) | set(after) if before.get(uid) != after.get(uid)}


@pytest.mark.asyncio
async def test_existing_installation_only_the_multi_pair_switches_change(aiohttp_client):
    """Ligne de base capturée sur main (e332b8f) avec la même scène, liens exportés compris.

    Avec liens : seules les commandes du switch du chauffe-eau changent (trace MQTT identique,
    aucun topic ni payload ne bouge) ; le second chauffe-eau, sans lien, n'est plus un switch.
    """
    base = _baseline()["with_links"]
    _app, _cli, now = await _project(aiohttp_client, links=True)
    assert len(base["entities"]) > 80, "scène trop pauvre pour être une preuve"
    assert _changed(base["entities"], now["entities"]) == {"jeedom2ha_eq_554", "jeedom2ha_eq_9810"}
    assert base["entities"]["jeedom2ha_eq_554"]["commands"] == {"ENERGY_OFF": 5491, "ENERGY_ON": 5490, "ENERGY_STATE": 5708}
    assert now["entities"]["jeedom2ha_eq_554"] == {
        "type": "switch", "confidence": "sure",
        "commands": {"ENERGY_OFF": 5707, "ENERGY_ON": 5706, "ENERGY_STATE": 5708},
    }
    assert now["entities"]["jeedom2ha_eq_9810"]["confidence"] == "ambiguous"
    removed, added = _mqtt_delta(base["mqtt"], now["mqtt"])
    assert added == []
    assert [c["topic"] for c in removed] == [f"homeassistant/switch/jeedom2ha_{CHAUFFE_EAU_SANS_LIEN_ID}/config"]
    # Ordre et contenu identiques, message par message, pour tout le reste de l'installation.
    assert _outside(now["mqtt"], [CHAUFFE_EAU_SANS_LIEN_ID]) == _outside(base["mqtt"], [CHAUFFE_EAU_SANS_LIEN_ID])


@pytest.mark.asyncio
async def test_existing_installation_without_link_fields(aiohttp_client):
    """Charge sans aucun lien (PHP d'avant) : les deux chauffe-eau perdent leur switch, rien d'autre."""
    base = _baseline()["without_links"]
    _app, _cli, now = await _project(aiohttp_client, links=False)
    assert _changed(base["entities"], now["entities"]) == {"jeedom2ha_eq_554", "jeedom2ha_eq_9810"}
    removed, added = _mqtt_delta(base["mqtt"], now["mqtt"])
    assert added == []
    others = [CHAUFFE_EAU_ID, CHAUFFE_EAU_SANS_LIEN_ID]
    assert _outside(now["mqtt"], others) == _outside(base["mqtt"], others)
    assert sorted(c["topic"] for c in removed) == [
        f"homeassistant/switch/jeedom2ha_{CHAUFFE_EAU_ID}/config",
        f"homeassistant/switch/jeedom2ha_{CHAUFFE_EAU_SANS_LIEN_ID}/config",
    ]


# --- Non-régression du contrat 4D ------------------------------------------------------------

@pytest.mark.asyncio
async def test_4d_contract_is_unchanged_for_the_scene(aiohttp_client):
    app, cli, _now = await _project(aiohttp_client, links=True)
    resp = await cli.get("/system/diagnostics", headers=H)
    assert resp.status == 200
    equipments = {e["eq_id"]: e for e in (await resp.json())["payload"]["equipments"]}
    for eq in equipments.values():
        assert eq["perimetre"] == reason_code_to_perimetre(eq["reason_code"])
        assert eq["ecart"] is compute_ecart(eq["perimetre"], eq["statut"])
    heater = equipments[CHAUFFE_EAU_ID]
    assert (heater["perimetre"], heater["statut"], heater["ecart"], heater["ha_type"]) == ("inclus", "publie", False, "switch")
    ambiguous = equipments[CHAUFFE_EAU_SANS_LIEN_ID]
    assert ambiguous["perimetre"] == "inclus"
    assert ambiguous["ecart"] is compute_ecart("inclus", ambiguous["statut"])


# --- Relecture : un seul sens en double, et ordre des infos d'état --------------------------------

def _two_on_one_off(off_extra):
    cmds = [
        {"id": 31, "name": "Etat", "generic_type": "ENERGY_STATE", "type": "info", "sub_type": "binary"},
        {"id": 32, "name": "Mode", "type": "info", "sub_type": "string"},
        {"id": 33, "name": "On", "generic_type": "ENERGY_ON", "type": "action", "sub_type": "other", "update_cmd_id": "31"},
        {"id": 34, "name": "Manu", "generic_type": "ENERGY_ON", "type": "action", "sub_type": "other", "virtual_info_id": "32"},
        {"id": 35, "name": "Off", "generic_type": "ENERGY_OFF", "type": "action", "sub_type": "other", **off_extra},
    ]
    snapshot = _snapshot_of([_eq_raw(30, cmds, name="Ballon")])
    return snapshot.eq_logics[30], snapshot


@pytest.mark.parametrize("off_extra", [{}, {"update_cmd_id": "31"}])
def test_single_order_kept_when_the_other_side_is_chosen_by_its_link(off_extra):
    """Deux On (un relié à l'état), un seul Off non relié (ou relié) : le switch existant est gardé."""
    eq, snapshot = _two_on_one_off(off_extra)
    switch = MapperRegistry().map(eq, snapshot)
    assert (switch.confidence, switch.reason_code) == ("sure", "switch_on_off_state")
    assert _roles(switch) == {"ENERGY_STATE": 31, "ENERGY_ON": 33, "ENERGY_OFF": 35}


def test_single_order_linked_to_another_info_stays_ambiguous():
    eq, snapshot = _two_on_one_off({"update_cmd_id": "32"})
    switch = MapperRegistry().map(eq, snapshot)
    assert (switch.confidence, switch.reason_code) == ("ambiguous", SWITCH_PAIRING_AMBIGUOUS)


@pytest.mark.parametrize("state_order", [(5530, 5708), (5708, 5530)])
def test_state_targeted_by_linked_actions_whatever_the_order(state_order):
    """Deux ENERGY_STATE (« Routage réel » numérique et « activé ») : l'état retenu est celui que
    visent les actions reliées, quel que soit l'ordre des commandes dans Jeedom."""
    cmds = chauffe_eau_cmds()
    states = {c["id"]: c for c in cmds if c["id"] in state_order}
    others = [c for c in cmds if c["id"] not in state_order]
    ordered = [states[state_order[0]], *others, states[state_order[1]]]
    snapshot = _snapshot_of([_eq_raw(CHAUFFE_EAU_ID, ordered)])
    switch = MapperRegistry().map(snapshot.eq_logics[CHAUFFE_EAU_ID], snapshot)
    assert (switch.confidence, switch.reason_code) == ("sure", "switch_on_off_state")
    assert _roles(switch) == {"ENERGY_STATE": 5708, "ENERGY_ON": 5706, "ENERGY_OFF": 5707}


def test_state_choice_without_links_keeps_the_last_one_seen():
    """Sans lien, rien n'est deviné : l'état reste le dernier vu (comportement d'avant), et le
    switch à plusieurs paires reste ambigu."""
    from mapping.pairing import choose_state
    s1, s2 = JeedomCmd(id=1, name="a"), JeedomCmd(id=2, name="b")
    on1, on2 = JeedomCmd(id=3, name="c"), JeedomCmd(id=4, name="d")
    assert choose_state([s1, s2], [on1, on2], []).id == 2
    assert choose_state([s1, s2], [on1], []).id == 2  # une seule paire : inchangé
