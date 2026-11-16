"""story/barrier-state-sensor — capteur compagnon « État » des covers barrière (story 24.7).

Une porte de garage ou un portail publié en ``cover`` reçoit ``stopped`` (253), mais Home Assistant
n'a pas d'état « arrêté » pour une cover. Un ``sensor`` ``device_class: enum`` en lecture seule,
rattaché au même appareil, affiche les 5 états de la convention barrière avec les mêmes clés et la même
table que la cover. Exception assumée à « une commande = une entité », limitée à ce cas.

Couvre : forme fidèle du « Garage » (bascule + 5 forçages invisibles) et du « Portail » (ordres directs
et bascule) relevés en production, portail en mode direct, cas sans compagnon (volet FLAP_*, barrière à
état binaire, barrière non éligible, équipement exclu, cover exclue ou retypée par l'utilisateur),
payload de découverte, synchro d'état (253 → ``stopped``), aucune commande, et une scène représentative
contre une ligne de base capturée sur main (8e881e0) : seuls ces capteurs s'ajoutent.
"""

from __future__ import annotations

import json
from collections import Counter
from unittest.mock import AsyncMock

import pytest

from discovery.publisher import DiscoveryPublisher
from mapping.barrier_state_sensor import BARRIER_STATE_OPTIONS, is_barrier_state_sensor
from mapping.registry import MapperRegistry
from models.evaluate_equipment import evaluate_equipment
from models.mapping import PublicationDecision
from models.topology import TopologySnapshot, assess_eligibility
from models.ui_contract_4d import compute_ecart, reason_code_to_perimetre
from sync.command import CommandSynchronizer
from sync.readback import BARRIER_STATE_TABLE
from sync.state import StateSynchronizer
from transport.http_server import create_app

from .barrier_state_corpus import (
    BARRIER_COVER_IDS,
    BARRIER_STATE_ID_OFFSET,
    BARRIERE_NON_ELIGIBLE_ID,
    BASELINE_PATH,
    GARAGE_BINAIRE_ID,
    PORTAIL_EXCLU_ID,
    VOLET_FLAP_ID,
    load_scene,
    sync_body,
    entity_commands,
)

SECRET = "test-secret-barrier"
H = {"X-Local-Secret": SECRET}

GARAGE = 199     # forme réelle « Garage » (virtual)
PORTAIL = 496    # forme réelle « Portail » (virtual)


def _snapshot(eq_logics) -> TopologySnapshot:
    return TopologySnapshot.from_jeedom_payload({"objects": [{"id": 1, "name": "Extérieur"}], "eq_logics": eq_logics})


def _raw(eq_id, cmds, name, eq_type="virtual", **extra):
    raw = {"id": eq_id, "name": name, "eq_type": eq_type, "object_id": 1, "is_enable": True, "cmds": cmds}
    raw.update(extra)
    return raw


def _c(cmd_id, name, generic_type, cmd_type, sub_type, **extra):
    entry = {"id": cmd_id, "name": name, "generic_type": generic_type, "type": cmd_type, "sub_type": sub_type}
    entry.update(extra)
    return entry


def _garage_cmds(state_value="0"):
    """Forme relevée en production : 1626 « Etat » GARAGE_STATE numérique, 1624 GB_TOGGLE, et cinq actions
    invisibles sans type générique (1627 à 1631) qui écrivent 254 / 252 / 253 / 255 / 0 dans 1626 (infoId)."""
    forcings = [(1627, "Ouverture", "254"), (1628, "Fermeture", "252"), (1629, "Arrêt", "253"),
                (1630, "Ouvert", "255"), (1631, "Fermé", "0")]
    return [
        _c(1624, "Ouvrir/Fermer", "GB_TOGGLE", "action", "other"),
        _c(1626, "Etat", "GARAGE_STATE", "info", "numeric", current_value=state_value),
        *[_c(cid, name, None, "action", "other", is_visible=False, virtual_info_id="1626", virtual_value=value)
          for cid, name, value in forcings],
    ]


def _portail_cmds():
    """Forme relevée en production : 4543 BARRIER_STATE numérique, 4545 GB_OPEN, 4546 GB_CLOSE, 4542 GB_TOGGLE."""
    return [
        _c(4542, "Ouvrir/Fermer", "GB_TOGGLE", "action", "other"),
        _c(4543, "Etat", "BARRIER_STATE", "info", "numeric", current_value="255"),
        _c(4545, "Ouvrir", "GB_OPEN", "action", "other"),
        _c(4546, "Fermer", "GB_CLOSE", "action", "other"),
    ]


def _garage():
    snapshot = _snapshot([_raw(GARAGE, _garage_cmds(), "Garage")])
    return snapshot.eq_logics[GARAGE], snapshot


def _portail():
    snapshot = _snapshot([_raw(PORTAIL, _portail_cmds(), "Portail")])
    return snapshot.eq_logics[PORTAIL], snapshot


def _decision(mapping):
    decision = PublicationDecision(should_publish=True, reason="sure", mapping_result=mapping,
                                   active_or_alive=True, discovery_published=True)
    mapping.publication_decision_ref = decision
    return decision


class _Bridge:
    def __init__(self):
        self.is_connected = True
        self.published = []

    def publish_message(self, topic, payload, qos=1, retain=False):
        self.published.append((topic, payload))
        return True


def _state_sync(primary):
    decision = _decision(primary)
    for secondary in primary.additional_mappings:
        _decision(secondary)
    bridge = _Bridge()
    return StateSynchronizer(app={"publications": {primary.jeedom_eq_id: decision}}, mqtt_bridge=bridge), bridge


# --- Mapping : la cover reste identique, le capteur s'ajoute ---------------------------------------

def test_real_garage_keeps_its_cover_and_gains_the_state_sensor():
    eq, snapshot = _garage()
    registry = MapperRegistry()
    before = registry._map_all_base(eq, snapshot)
    assert [(r.ha_entity_type, r.ha_unique_id) for r in before] == [("cover", "jeedom2ha_eq_199")]
    results = registry.map_all(eq, snapshot)
    assert results[:1] == before  # la cover : même objet, mêmes commandes, même nom
    assert {k: c.id for k, c in results[0].commands.items()} == {"GB_TOGGLE": 1624, "GARAGE_STATE": 1626}
    assert len(results) == 2
    sensor = results[1]
    assert (sensor.ha_entity_type, sensor.ha_unique_id, sensor.ha_name) == (
        "sensor", "jeedom2ha_eq_199_cmd_1626_barrier_state", "État")
    assert {k: c.id for k, c in sensor.commands.items()} == {"GARAGE_STATE": 1626}  # aucune action
    assert sensor.reason_details == {
        "cmd_id": 1626,
        "object_id": "jeedom2ha_199_1626_barrier_state",
        "node_id": "jeedom2ha_199_1626_barrier_state",
        "state_topic": "jeedom2ha/199/1626/barrier_state",
        "device_class": "enum",
        "options": ["closed", "closing", "stopped", "opening", "open"],
        "barrier_companion_of": "jeedom2ha_eq_199",
    }
    # Mêmes clés que la cover, même table de traduction (une seule source).
    assert BARRIER_STATE_OPTIONS == list(BARRIER_STATE_TABLE.values())
    assert set(BARRIER_STATE_OPTIONS) == {"closed", "opening", "closing", "stopped", "open"}
    # Les 5 actions de forçage (1627 à 1631) restent sans entité, comme avant.
    assert not any(c.id in range(1627, 1632) for r in results for c in r.commands.values())


def test_real_portail_with_direct_orders_and_toggle_gains_the_state_sensor():
    """Forme réelle du « Portail » : la bascule est prioritaire (mode toggle_on_state), la cover reste
    identique, et seul le capteur « État » sur 4543 s'ajoute."""
    eq, snapshot = _portail()
    registry = MapperRegistry()
    before = registry._map_all_base(eq, snapshot)
    results = registry.map_all(eq, snapshot)
    assert results[:1] == before and before[0].ha_entity_type == "cover"
    assert before[0].reason_details["barrier_mode"] == "toggle_on_state"
    assert before[0].reason_details["cover_device_class"] == "gate"
    assert [(r.ha_entity_type, r.ha_unique_id) for r in results[1:]] == [
        ("sensor", "jeedom2ha_eq_496_cmd_4543_barrier_state")]
    assert results[1].reason_details["state_topic"] == "jeedom2ha/496/4543/barrier_state"


def test_direct_mode_portail_gains_the_state_sensor():
    cmds = [
        _c(71, "Etat", "BARRIER_STATE", "info", "numeric"),
        _c(72, "Ouvrir", "GB_OPEN", "action", "other"),
        _c(73, "Fermer", "GB_CLOSE", "action", "other"),
    ]
    snapshot = _snapshot([_raw(70, cmds, "Portail allée")])
    results = MapperRegistry().map_all(snapshot.eq_logics[70], snapshot)
    assert results[0].reason_details["barrier_mode"] == "direct"
    assert [(r.ha_entity_type, r.ha_unique_id) for r in results] == [
        ("cover", "jeedom2ha_eq_70"), ("sensor", "jeedom2ha_eq_70_cmd_71_barrier_state")]


# --- Cas sans compagnon -----------------------------------------------------------------------------

@pytest.mark.parametrize("cmds", [
    # volet FLAP_* (cover non barrière)
    [_c(1, "Etat", "FLAP_STATE", "info", "numeric"), _c(2, "Monter", "FLAP_UP", "action", "other"),
     _c(3, "Descendre", "FLAP_DOWN", "action", "other"), _c(4, "Stop", "FLAP_STOP", "action", "other")],
    # barrière à état binaire : reste un binary_sensor garage_door
    [_c(1, "Etat", "GARAGE_STATE", "info", "binary"), _c(2, "Ouvrir/Fermer", "GB_TOGGLE", "action", "other")],
    # barrière non éligible (GB_OPEN seul)
    [_c(1, "Etat", "BARRIER_STATE", "info", "numeric"), _c(2, "Ouvrir", "GB_OPEN", "action", "other")],
    # état numérique sans aucune action barrière
    [_c(1, "Etat", "BARRIER_STATE", "info", "numeric")],
])
def test_no_state_sensor_without_a_barrier_cover(cmds):
    snapshot = _snapshot([_raw(10, cmds, "Equipement")])
    registry = MapperRegistry()
    eq = snapshot.eq_logics[10]
    assert registry.map_all(eq, snapshot) == registry._map_all_base(eq, snapshot)
    assert not any(is_barrier_state_sensor(r) for r in registry.map_all(eq, snapshot))


def test_binary_barrier_stays_a_garage_door_binary_sensor():
    cmds = [_c(1, "Etat", "GARAGE_STATE", "info", "binary"), _c(2, "Ouvrir/Fermer", "GB_TOGGLE", "action", "other")]
    snapshot = _snapshot([_raw(10, cmds, "Garage atelier")])
    results = MapperRegistry().map_all(snapshot.eq_logics[10], snapshot)
    assert [r.ha_entity_type for r in results] == ["binary_sensor"]


def test_ineligible_equipment_excluded_by_its_object_produces_nothing():
    """Forme du portail exclu par son objet : BARRIER_STATE binaire, zwavejs, équipement exclu."""
    cmds = [_c(4076, "Etat", "BARRIER_STATE", "info", "binary"), _c(4077, "Ouvrir", "GB_OPEN", "action", "other"),
            _c(4078, "Fermer", "GB_CLOSE", "action", "other")]
    snapshot = _snapshot([_raw(455, cmds, "Portail", eq_type="zwavejs", is_excluded=True, exclusion_source="object")])
    eq = snapshot.eq_logics[455]
    evaluation = evaluate_equipment(eq, snapshot, assess_eligibility(eq), mapper_registry=MapperRegistry())
    assert evaluation.mapping is None and evaluation.secondary_decisions == []
    assert evaluation.equipment_decision.should_publish is False


# --- La cover exclue, refusée ou retypée : pas de compagnon publié ----------------------------------

def _evaluate(eq, snapshot, overrides=None, equipment_overrides=None):
    return evaluate_equipment(eq, snapshot, assess_eligibility(eq), mapper_registry=MapperRegistry(),
                              persisted_overrides=overrides or {},
                              persisted_equipment_overrides=equipment_overrides or {})


def test_published_cover_publishes_its_state_sensor():
    eq, snapshot = _garage()
    evaluation = _evaluate(eq, snapshot)
    assert evaluation.equipment_decision.should_publish is True
    assert [d.should_publish for d in evaluation.secondary_decisions] == [True]
    assert [m.ha_unique_id for m in evaluation.mapping.additional_mappings] == [
        "jeedom2ha_eq_199_cmd_1626_barrier_state"]


def test_equipment_excluded_by_the_user_publishes_neither():
    eq, snapshot = _garage()
    evaluation = _evaluate(eq, snapshot, equipment_overrides={"199": {"publication_override": "exclude"}})
    assert evaluation.equipment_decision.should_publish is False
    assert [d.should_publish for d in evaluation.secondary_decisions] == [False]


def test_cover_excluded_by_its_toggle_command_takes_its_state_sensor_along():
    """L'exclusion porte sur la bascule (1624), que le capteur ne porte pas : il suit quand même la cover,
    avec la même raison."""
    eq, snapshot = _garage()
    evaluation = _evaluate(eq, snapshot, overrides={"199:1624": {"publication_override": "exclude"}})
    cover_decision = evaluation.equipment_decision
    assert cover_decision.should_publish is False
    (sensor_decision,) = evaluation.secondary_decisions
    assert sensor_decision.should_publish is False
    assert sensor_decision.reason == cover_decision.reason
    assert sensor_decision.reason_details["barrier_companion_of"] == "jeedom2ha_eq_199"
    sensor = evaluation.mapping.additional_mappings[0]
    assert sensor.publication_decision_ref is sensor_decision and sensor_decision.mapping_result is sensor


@pytest.mark.parametrize("cmd_id,forced", [(1626, "sensor"), (1624, "button")])
def test_cover_retyped_by_the_user_has_no_state_sensor(cmd_id, forced):
    """« Corriger le type » sur une commande de la cover : la cover n'est plus une barrière, le capteur
    disparaît ; il ne prend jamais lui-même l'override (posé sur l'état, il vise la cover)."""
    eq, snapshot = _garage()
    evaluation = _evaluate(eq, snapshot, overrides={f"199:{cmd_id}": {"ha_entity_type": forced}})
    assert evaluation.mapping.ha_entity_type == forced
    assert evaluation.mapping.additional_mappings == []
    assert evaluation.secondary_decisions == []


# --- Découverte ---------------------------------------------------------------------------------------

class _ConfigBridge:
    def __init__(self):
        self.calls = []

    def publish_message(self, topic, payload, qos=1, retain=False):
        self.calls.append((topic, json.loads(payload), retain))
        return True


@pytest.mark.asyncio
async def test_state_sensor_discovery_payload():
    eq, snapshot = _garage()
    cover, sensor = MapperRegistry().map_all(eq, snapshot)
    bridge = _ConfigBridge()
    publisher = DiscoveryPublisher(bridge)
    assert await publisher.publish_cover(cover, snapshot) is True
    assert await publisher.publish_sensor(sensor, snapshot) is True
    (cover_topic, cover_payload, _), (topic, payload, retain) = bridge.calls
    assert cover_topic == "homeassistant/cover/jeedom2ha_199/config"
    assert topic == "homeassistant/sensor/jeedom2ha_199_1626_barrier_state/config" and retain is True
    assert payload["name"] == "État"
    assert payload["unique_id"] == "jeedom2ha_eq_199_cmd_1626_barrier_state"
    assert payload["default_entity_id"] == "sensor.jeedom2ha_199_1626_barrier_state"
    assert payload["state_topic"] == "jeedom2ha/199/1626/barrier_state"
    assert payload["device_class"] == "enum"
    assert payload["options"] == ["closed", "closing", "stopped", "opening", "open"]
    assert payload["device"] == cover_payload["device"]  # même appareil que la cover
    for key in ("availability", "availability_topic", "availability_mode"):  # même disponibilité
        assert payload.get(key) == cover_payload.get(key)
    assert not any(k.startswith("command") for k in payload)  # lecture seule
    assert "unit_of_measurement" not in payload and "state_class" not in payload


@pytest.mark.asyncio
async def test_other_sensors_never_gain_options():
    """Les options ne s'écrivent que pour un capteur enum : un capteur de mesure reste identique."""
    cmds = [_c(1, "Température", "TEMPERATURE", "info", "numeric", unit="°C")]
    snapshot = _snapshot([_raw(10, cmds, "Sonde")])
    (sensor,) = MapperRegistry().map_all(snapshot.eq_logics[10], snapshot)
    bridge = _ConfigBridge()
    await DiscoveryPublisher(bridge).publish_sensor(sensor, snapshot)
    assert "options" not in bridge.calls[0][1]


# --- Synchro d'état -----------------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("value,state", [("0", "closed"), ("252", "closing"), ("253", "stopped"),
                                         ("254", "opening"), ("255", "open"), ("253.0", "stopped")])
async def test_each_barrier_value_publishes_the_same_state_on_cover_and_sensor(value, state):
    eq, snapshot = _garage()
    sync, bridge = _state_sync(MapperRegistry().map(eq, snapshot))
    assert await sync.handle_state_message(199, 1626, value) is True
    assert bridge.published == [("jeedom2ha/199/state", state), ("jeedom2ha/199/1626/barrier_state", state)]


@pytest.mark.asyncio
async def test_stopped_reaches_the_sensor_and_the_cover_keeps_its_behaviour():
    eq, snapshot = _garage()
    sync, bridge = _state_sync(MapperRegistry().map(eq, snapshot))
    assert await sync.handle_state_message(199, 1626, 253) is True
    assert ("jeedom2ha/199/1626/barrier_state", "stopped") in bridge.published
    assert ("jeedom2ha/199/state", "stopped") in bridge.published  # la cover reçoit ce qu'elle recevait
    assert sync.last_event_value(199, 1626) == 253


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["100", "1", "2.55e2", "-0", "", "ouvert", None])
async def test_a_value_outside_the_convention_publishes_nothing(value):
    eq, snapshot = _garage()
    sync, bridge = _state_sync(MapperRegistry().map(eq, snapshot))
    assert await sync.handle_state_message(199, 1626, value) is False
    assert bridge.published == []


@pytest.mark.asyncio
async def test_initial_state_reaches_the_sensor():
    snapshot = _snapshot([_raw(GARAGE, _garage_cmds(state_value="253"), "Garage")])
    primary = MapperRegistry().map(snapshot.eq_logics[GARAGE], snapshot)
    sync, bridge = _state_sync(primary)
    assert await sync.publish_initial_states(primary.publication_decision_ref) == 2
    assert bridge.published == [("jeedom2ha/199/state", "stopped"), ("jeedom2ha/199/1626/barrier_state", "stopped")]


def test_the_listener_list_keeps_one_entry_for_the_state_command():
    eq, snapshot = _garage()
    sync, _bridge = _state_sync(MapperRegistry().map(eq, snapshot))
    assert [(t["eq_id"], t["cmd_id"]) for t in sync.list_state_targets()] == [(199, 1626)]


# --- Lecture seule : aucune commande ------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("topic", ["jeedom2ha/199/1626/barrier_state", "jeedom2ha/199/1626/barrier_state/set",
                                   "jeedom2ha/199/1626/set"])
async def test_the_state_sensor_runs_no_command(topic):
    eq, snapshot = _garage()
    primary = MapperRegistry().map(eq, snapshot)
    decision = _decision(primary)
    for secondary in primary.additional_mappings:
        _decision(secondary)
    sync = CommandSynchronizer(app={"publications": {199: decision}, "state_synchronizer": None},
                               mqtt_bridge=_Bridge(), jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
                               jeedom_core_apikey="core-apikey")
    sync._execute_exec_cmd = AsyncMock(return_value=True)
    for payload in ("stopped", "open", "OPEN", "ON"):
        assert await sync.handle_command_message(topic, payload) is False
    sync._execute_exec_cmd.assert_not_awaited()


# --- Installation existante : seuls les capteurs « État » s'ajoutent ----------------------------------

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
    resp = await cli.post("/action/sync", json=sync_body(load_scene(), "barrier"), headers=H)
    assert resp.status == 200, await resp.text()
    return app, cli, {"mqtt": bridge.calls, "entities": entity_commands(app["mappings"])}


def _companion_id(eq_id):
    return f"jeedom2ha_eq_{eq_id}_cmd_{eq_id * 100 + BARRIER_STATE_ID_OFFSET[eq_id]}_barrier_state"


@pytest.mark.asyncio
async def test_existing_installation_only_gains_barrier_state_sensors(aiohttp_client):
    """Ligne de base capturée sur main (8e881e0), même scène : corpus doré, modes, formes réelles, et les
    portes de garage / portails sous toutes les formes de la story 24.7."""
    base = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    _app, _cli, now = await _project(aiohttp_client)
    assert len(base["entities"]) > 100, "scène trop pauvre pour être une preuve"
    changed = {u for u in set(base["entities"]) | set(now["entities"])
               if base["entities"].get(u) != now["entities"].get(u)}
    assert changed == {_companion_id(eq_id) for eq_id in BARRIER_COVER_IDS}
    assert all(u not in base["entities"] and now["entities"][u]["type"] == "sensor" for u in changed)

    def key(call):
        return json.dumps(call, sort_keys=True)
    b, a = Counter(map(key, base["mqtt"])), Counter(map(key, now["mqtt"]))
    assert list((b - a).elements()) == []  # aucun message existant ne change ni ne disparaît
    added = [json.loads(k) for k in (a - b).elements()]
    assert sorted(c["topic"] for c in added) == sorted(
        f"homeassistant/sensor/jeedom2ha_{eq_id}_{eq_id * 100 + BARRIER_STATE_ID_OFFSET[eq_id]}_barrier_state/config"
        for eq_id in BARRIER_COVER_IDS)
    assert [c for c in now["mqtt"] if c not in added] == base["mqtt"]  # ordre identique pour le reste
    for call in added:
        payload = json.loads(call["payload"])
        assert (payload["name"], payload["device_class"]) == ("État", "enum")
        assert payload["options"] == ["closed", "closing", "stopped", "opening", "open"]
    # Les covers barrière restent identiques ; les autres formes n'ont aucun compagnon.
    for eq_id in BARRIER_COVER_IDS:
        assert base["entities"][f"jeedom2ha_eq_{eq_id}"] == now["entities"][f"jeedom2ha_eq_{eq_id}"]
    for eq_id in (PORTAIL_EXCLU_ID, GARAGE_BINAIRE_ID, BARRIERE_NON_ELIGIBLE_ID, VOLET_FLAP_ID):
        mine = {u: v for u, v in now["entities"].items()
                if u == f"jeedom2ha_eq_{eq_id}" or u.startswith(f"jeedom2ha_eq_{eq_id}_")}
        assert mine == {u: v for u, v in base["entities"].items()
                        if u == f"jeedom2ha_eq_{eq_id}" or u.startswith(f"jeedom2ha_eq_{eq_id}_")}, eq_id
    assert not any(str(PORTAIL_EXCLU_ID) in c["topic"] for c in now["mqtt"])


@pytest.mark.asyncio
async def test_4d_contract_is_unchanged_for_the_scene(aiohttp_client):
    _app, cli, _now = await _project(aiohttp_client)
    resp = await cli.get("/system/diagnostics", headers=H)
    assert resp.status == 200
    equipments = {e["eq_id"]: e for e in (await resp.json())["payload"]["equipments"]}
    for eq in equipments.values():
        assert eq["perimetre"] == reason_code_to_perimetre(eq["reason_code"])
        assert eq["ecart"] is compute_ecart(eq["perimetre"], eq["statut"])
    for eq_id in BARRIER_COVER_IDS:
        assert (equipments[eq_id]["statut"], equipments[eq_id]["ha_type"]) == ("publie", "cover")
