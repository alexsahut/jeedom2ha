"""Story 12.4 (FR49, CC-64) — alarme : état diffusé vers HA, armement par mode, code de désarmement.

Identifiants, noms et libellés de mode fictifs uniquement (CC-48) : aucun identifiant ni libellé de
la maison. Couvre : table de vérité de ``alarm_state`` (AC1), mapper et clés Homebridge (AC4, AC5),
diffusion (AC2), republication à la naissance de HA et à la reconnexion au broker (AC3, CC-08),
commandes par mode (AC4), code de désarmement (AC6), discovery sans code (AC6) et non-régression
du virtuel générique (AC7).
"""
from __future__ import annotations

import json
import time
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from discovery.publisher import DiscoveryPublisher
from mapping.alarm_control_panel import (
    AlarmControlPanelMapper,
    alarm_arm_targets,
    alarm_supported_features,
    parse_mode_config_value,
)
from models.mapping import PublicationDecision
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from sync import alarm_code
from sync.alarm_code import ALARM_CODE, ALARM_LOCKOUT, AlarmDisarmLockout, set_alarm_code
from sync.command import CommandSynchronizer, CommandTranslation
from sync.readback import alarm_readback_commands, alarm_state, normalize_alarm_mode_label
from sync.state import StateSynchronizer
from transport import http_server
from transport.http_server import create_app

EQ = 7100           # alarme du plugin « alarm » (ids d'exemple)
VIRTUAL = 7200      # virtuel générique
ENABLE, STATUS, IMMEDIATE, MODE = 71001, 71002, 71003, 71004
ARMED, RELEASED = 71005, 71006
MODE_A, MODE_B, MODE_C, MODE_D = 71011, 71012, 71013, 71014
LABELS = {"armed_home": "Mode Jour", "armed_away": "mode   total", "armed_night": "mode nuit"}
CONFIG = {
    "SetModePresent": f"{MODE_C}|Mode Jour",
    "SetModeAbsent": f"{MODE_A}|mode   total",
    "SetModeNuit": f"{MODE_B}|mode nuit",
}
SECRET = "test-secret-12-4"
HEADERS = {"X-Local-Secret": SECRET}
CODE = "8213-sentinelle"


@pytest.fixture(autouse=True)
def _immediate_alarm_state(monkeypatch):
    """Story 12.5 — ces tests vérifient le calcul de l'état, pas le regroupement : fenêtre à 0."""
    monkeypatch.setattr("sync.state.ALARM_STATE_COALESCE_S", 0)


@pytest.fixture(autouse=True)
def _no_code():
    """Le code vit dans le démon (objet global) : chaque test part sans code et le rend sans code."""
    ALARM_CODE.clear()
    ALARM_LOCKOUT.reset()
    clock = ALARM_LOCKOUT.clock
    yield
    ALARM_CODE.clear()
    ALARM_LOCKOUT.reset()
    ALARM_LOCKOUT.clock = clock


def _cmd(cmd_id, generic_type, type_="action", sub_type="other", value=None, logical_id=None):
    return JeedomCmd(id=cmd_id, name=f"Cmd {cmd_id}", generic_type=generic_type, type=type_,
                     sub_type=sub_type, current_value=value, logical_id=logical_id)


def _alarm_eq(config=None, eq_type="alarm", enable="1", status="0", immediate="0", mode="mode nuit"):
    return JeedomEqLogic(
        id=EQ, name="Alarme essai", object_id=1, eq_type_name=eq_type,
        alarm_mode_config=dict(CONFIG if config is None else config),
        cmds=[
            _cmd(ENABLE, "ALARM_ENABLE_STATE", "info", "binary", enable, "enable"),
            _cmd(STATUS, "ALARM_STATE", "info", "binary", status, "state"),
            _cmd(IMMEDIATE, None, "info", "binary", immediate, "immediatState"),
            _cmd(MODE, "ALARM_MODE", "info", "string", mode, "mode"),
            _cmd(ARMED, "ALARM_ARMED"),
            _cmd(RELEASED, "ALARM_RELEASED"),
            _cmd(MODE_A, "ALARM_SET_MODE"),
            _cmd(MODE_B, "ALARM_SET_MODE"),
            _cmd(MODE_C, "ALARM_SET_MODE"),
            _cmd(MODE_D, "ALARM_SET_MODE"),
        ],
    )


def _virtual_eq(enable="1", status="0"):
    return JeedomEqLogic(
        id=VIRTUAL, name="Alarme virtuelle", object_id=1, eq_type_name="virtual",
        cmds=[
            _cmd(72001, "ALARM_STATE", "info", "binary", status),
            _cmd(72002, "ALARM_ENABLE_STATE", "info", "binary", enable),
            _cmd(72003, "ALARM_ENABLE"),
            _cmd(72004, "ALARM_DISABLE"),
        ],
    )


def _snapshot(*eqs):
    return TopologySnapshot(timestamp="2026-11-23T00:00:00Z", objects={1: JeedomObject(id=1, name="Zone")},
                            eq_logics={eq.id: eq for eq in eqs})


def _map(eq):
    return AlarmControlPanelMapper().map(eq, _snapshot(eq))


class _Bridge:
    def __init__(self):
        self.is_connected = True
        self.published = []

    def publish_message(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return True


def _decision(mapping):
    decision = PublicationDecision(
        should_publish=True, reason="sure", mapping_result=mapping,
        state_topic=mapping.reason_details["state_topic"], active_or_alive=True, discovery_published=True,
    )
    mapping.publication_decision_ref = decision
    return decision


def _discovery(eq):
    return DiscoveryPublisher(MagicMock())._build_alarm_control_panel_payload(_map(eq), _snapshot(eq))


# --- AC1 : table de vérité ------------------------------------------------------------------

@pytest.mark.parametrize("status,enable,immediate,mode,expected", [
    # 1. Statut = 1 : déclenchée, quoi qu'il en soit du reste (Actif jamais lu compris)
    ("1", "1", "1", "mode nuit", "triggered"),
    ("1", "0", "0", None, "triggered"),
    ("1", None, None, None, "triggered"),
    (1, None, None, None, "triggered"),
    ("true", "1", "0", None, "triggered"),
    # 2. Actif = 0 : désarmée (Immédiat et Mode ignorés)
    ("0", "0", "1", "Mode Jour", "disarmed"),
    (None, "0", None, None, "disarmed"),
    ("0", "false", "0", None, "disarmed"),
    # 3. Immédiat = 1 : délai d'entrée
    ("0", "1", "1", "Mode Jour", "pending"),
    (None, "1", "1", None, "pending"),
    # 4. Mode : libellés des clés Homebridge, casse et espaces normalisés
    ("0", "1", "0", "Mode Jour", "armed_home"),
    ("0", "1", "0", "  mode   jour ", "armed_home"),
    ("0", "1", "0", "MODE TOTAL", "armed_away"),
    ("0", "1", "0", "mode nuit", "armed_night"),
    ("0", "1", "0", "Mode\tNuit", "armed_night"),
    # 5. mode inconnu, vide ou absent : armed_away (Homebridge / HomeKit)
    ("0", "1", "0", "mode inconnu", "armed_away"),
    ("0", "1", "0", "", "armed_away"),
    ("0", "1", None, None, "armed_away"),
    # 6. Actif jamais lu ou illisible : rien d'inventé
    ("0", None, "0", "mode nuit", None),
    ("0", "", "0", "mode nuit", None),
    ("0", "2", "0", "mode nuit", None),
    ("0", "abc", "1", "mode nuit", None),
    (None, None, None, None, None),
])
def test_alarm_state_truth_table(status, enable, immediate, mode, expected):
    assert alarm_state(status, enable, immediate, mode, LABELS) == expected


def test_alarm_state_without_mode_configuration_is_armed_away():
    assert alarm_state("0", "1", "0", "Mode Jour", None) == "armed_away"
    assert alarm_state("0", "1", "0", "Mode Jour", {}) == "armed_away"


def test_alarm_state_never_publishes_arming():
    seen = {alarm_state(s, e, i, m, LABELS)
            for s in ("0", "1", None) for e in ("0", "1", None) for i in ("0", "1", None)
            for m in (None, "Mode Jour", "mode total", "mode nuit", "x")}
    assert "arming" not in seen
    assert seen <= {None, "disarmed", "armed_home", "armed_away", "armed_night", "pending", "triggered"}


def test_mode_label_normalization():
    assert normalize_alarm_mode_label("  Mode   SOIR ") == "mode soir"
    assert normalize_alarm_mode_label("") is None
    assert normalize_alarm_mode_label(None) is None


# --- AC4 / AC5 : mapper, clés Homebridge -------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("71011|mode total", (71011, "mode total")),
    ("71011|a|b", (71011, "a|b")),
    (" 71011 |x", (71011, "x")),
    ("71011|", None), ("71011", None), ("abc|x", None), ("0|x", None), ("-3|x", None),
    ("#71011#|x", None), ("", None), (None, None), (71011, None),
])
def test_parse_mode_config_value(raw, expected):
    assert parse_mode_config_value(raw) == expected


def test_mapper_reads_the_four_infos_and_the_three_modes():
    mapping = _map(_alarm_eq())
    cmds = {k: c.id for k, c in mapping.commands.items()}
    assert cmds == {
        "ALARM_ENABLE_STATE": ENABLE, "ALARM_STATE": STATUS, "ALARM_IMMEDIATE_STATE": IMMEDIATE,
        "ALARM_MODE": MODE, "ALARM_ARMED": ARMED, "ALARM_RELEASED": RELEASED,
        "ALARM_SET_MODE_HOME": MODE_C, "ALARM_SET_MODE_AWAY": MODE_A, "ALARM_SET_MODE_NIGHT": MODE_B,
    }
    assert mapping.reason_details["supported_features"] == ["arm_home", "arm_away", "arm_night"]
    assert mapping.reason_details["alarm_mode_labels"] == LABELS
    assert mapping.capabilities.has_state and mapping.capabilities.has_command
    assert [c.id for _ch, c in alarm_readback_commands(mapping)] == [ENABLE, STATUS, IMMEDIATE, MODE]


def test_immediate_info_only_for_the_alarm_plugin():
    mapping = _map(_alarm_eq(eq_type="virtual"))
    assert "ALARM_IMMEDIATE_STATE" not in mapping.commands


@pytest.mark.parametrize("value,why", [
    ("99999|mode", "id absent de l'équipement"),
    (f"{ARMED}|mode", "action d'un autre generic type"),
    (f"{MODE}|mode", "info, pas une action"),
    ("pas-un-id", "format invalide"),
])
def test_a_mode_command_is_kept_only_if_it_is_an_alarm_set_mode_action_of_the_equipment(value, why):
    mapping = _map(_alarm_eq(config={"SetModePresent": value, "SetModeAbsent": f"{MODE_A}|mode total"}))
    assert "ALARM_SET_MODE_HOME" not in mapping.commands, why
    assert mapping.reason_details["supported_features"] == ["arm_away"]


def test_partial_configuration_announces_only_the_available_armings():
    mapping = _map(_alarm_eq(config={"SetModeNuit": f"{MODE_B}|mode nuit"}))
    assert mapping.reason_details["supported_features"] == ["arm_night"]
    assert set(alarm_arm_targets(mapping.commands)) == {"armed_night"}


def test_without_mode_configuration_arming_is_the_generic_armed_command():
    mapping = _map(_alarm_eq(config={}))
    assert mapping.reason_details["supported_features"] == ["arm_away"]
    assert alarm_arm_targets(mapping.commands)["armed_away"].id == ARMED
    assert "alarm_mode_labels" not in mapping.reason_details


def test_topology_payload_carries_the_mode_keys_read_only():
    snapshot = TopologySnapshot.from_jeedom_payload({"eq_logics": [{
        "id": EQ, "name": "Alarme", "eq_type": "alarm", "cmds": [],
        "alarm_mode_config": {"SetModePresent": "1|a", "SetModeAbsent": "", "SetModeNuit": ["x"], "Autre": "2|b"},
    }, {"id": EQ + 1, "name": "Lampe", "eq_type": "virtual", "cmds": []}]})
    assert snapshot.eq_logics[EQ].alarm_mode_config == {"SetModePresent": "1|a"}
    assert snapshot.eq_logics[EQ + 1].alarm_mode_config == {}


# --- AC2 : diffusion ---------------------------------------------------------------------------

def _state_sync(mapping):
    bridge = _Bridge()
    decision = _decision(mapping)
    sync = StateSynchronizer(app={"publications": {mapping.jeedom_eq_id: decision}}, mqtt_bridge=bridge)
    return sync, bridge, decision


@pytest.mark.asyncio
async def test_initial_state_is_published_retained_on_the_declared_topic():
    sync, bridge, decision = _state_sync(_map(_alarm_eq(mode="Mode Jour")))
    assert await sync.publish_initial_states(decision) == 1
    assert bridge.published == [(f"jeedom2ha/{EQ}/alarm/state", "armed_home", 1, True)]


@pytest.mark.asyncio
@pytest.mark.parametrize("cmd_id,value,expected", [
    (ENABLE, "0", "disarmed"),
    (STATUS, "1", "triggered"),
    (IMMEDIATE, "1", "pending"),
    (MODE, "mode total", "armed_away"),
    (MODE, "Mode Jour", "armed_home"),
])
async def test_each_of_the_four_infos_recomputes_and_publishes_the_state(cmd_id, value, expected):
    sync, bridge, _decision_ = _state_sync(_map(_alarm_eq(mode="mode nuit")))
    assert await sync.handle_state_message(EQ, cmd_id, value) is True
    assert bridge.published == [(f"jeedom2ha/{EQ}/alarm/state", expected, 1, True)]


@pytest.mark.asyncio
async def test_the_other_infos_are_read_from_their_last_event():
    sync, bridge, _d = _state_sync(_map(_alarm_eq(enable="0", mode="mode nuit")))
    await sync.handle_state_message(EQ, ENABLE, "1")        # armée, mode nuit (topologie)
    await sync.handle_state_message(EQ, IMMEDIATE, "1")     # délai d'entrée
    await sync.handle_state_message(EQ, STATUS, "1")        # déclenchée
    await sync.handle_state_message(EQ, STATUS, "0")        # retour : Immédiat toujours à 1
    await sync.handle_state_message(EQ, IMMEDIATE, "0")
    await sync.handle_state_message(EQ, ENABLE, "0")
    assert [p[1] for p in bridge.published] == [
        "armed_night", "pending", "triggered", "pending", "armed_night", "disarmed"]


@pytest.mark.asyncio
async def test_never_read_enable_invents_nothing_and_resets_ha_to_unknown_once():
    """Revue Codex de 12.4 : Actif jamais lu -> aucun état inventé ; HA est ramené à ``unknown``
    (payload ``None``, un état retenu d'un run précédent peut être au broker), une seule fois."""
    sync, bridge, decision = _state_sync(_map(_alarm_eq(enable=None)))
    assert await sync.publish_initial_states(decision) == 1
    assert await sync.handle_state_message(EQ, MODE, "Mode Jour") is False   # déjà inconnu : rien
    assert bridge.published == [(f"jeedom2ha/{EQ}/alarm/state", "None", 1, True)]


def test_the_four_infos_are_registered_as_state_listeners():
    sync, _bridge, _d = _state_sync(_map(_alarm_eq()))
    targets = sync.list_state_targets()
    assert sorted(t["cmd_id"] for t in targets) == sorted([ENABLE, STATUS, IMMEDIATE, MODE])
    assert {t["state_topic"] for t in targets} == {f"jeedom2ha/{EQ}/alarm/state"}
    assert sync.streams_actionable_type("alarm_control_panel") is True


@pytest.mark.asyncio
async def test_click_publication_uses_the_fresh_values():
    sync, bridge, decision = _state_sync(_map(_alarm_eq(enable="0")))
    published, failed = await sync.publish_click_states(
        decision, {ENABLE: "1", STATUS: "0", IMMEDIATE: "0", MODE: "mode total"}, fresh_since=0.0)
    assert (published, failed) == (1, 0)
    assert bridge.published == [(f"jeedom2ha/{EQ}/alarm/state", "armed_away", 1, True)]


# --- AC3 : CC-08, naissance de HA et reconnexion au broker --------------------------------------

def _raw_cmd(cmd_id, generic_type, type_="action", sub_type="other", value=None, logical_id=None):
    return {"id": cmd_id, "name": f"cmd {cmd_id}", "generic_type": generic_type, "type": type_,
            "sub_type": sub_type, "current_value": value, "logical_id": logical_id}


def _sync_body():
    alarm = {
        "id": EQ, "name": "Alarme essai", "object_id": 1, "is_enable": True, "is_visible": True,
        "eq_type": "alarm", "is_excluded": False, "status": {"timeout": 0}, "alarm_mode_config": CONFIG,
        "cmds": [_raw_cmd(ENABLE, "ALARM_ENABLE_STATE", "info", "binary", "1"),
                 _raw_cmd(STATUS, "ALARM_STATE", "info", "binary", "0"),
                 _raw_cmd(IMMEDIATE, None, "info", "binary", "0", "immediatState"),
                 _raw_cmd(MODE, "ALARM_MODE", "info", "string", "mode total"),
                 _raw_cmd(ARMED, "ALARM_ARMED"), _raw_cmd(RELEASED, "ALARM_RELEASED"),
                 _raw_cmd(MODE_A, "ALARM_SET_MODE"), _raw_cmd(MODE_B, "ALARM_SET_MODE"),
                 _raw_cmd(MODE_C, "ALARM_SET_MODE")],
    }
    light = {
        "id": 7300, "name": "Lampe", "object_id": 1, "is_enable": True, "is_visible": True, "eq_type": "virtual",
        "is_excluded": False, "status": {"timeout": 0},
        "cmds": [_raw_cmd(73001, "LIGHT_ON"), _raw_cmd(73002, "LIGHT_OFF"),
                 _raw_cmd(73003, "LIGHT_STATE", "info", "binary", "1")],
    }
    payload = {"timestamp": "2026-11-23T00:00:00Z", "objects": [{"id": 1, "name": "Zone"}],
               "eq_logics": [alarm, light], "scenarios": [], "scenarios_complete": True,
               "sync_config": {"confidence_policy": "sure_probable"}}
    return {"action": "sync", "payload": payload, "request_id": "t12-4", "timestamp": "2026-11-23T00:00:00Z"}


def _bridge_mock():
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    bridge.start = AsyncMock()
    bridge.stop = AsyncMock()
    bridge.state = "connected"
    bridge.broker_info = "broker.example.invalid:1883"
    return bridge


@pytest.fixture
def app(tmp_path):
    application = create_app(local_secret=SECRET)
    application["data_dir"] = str(tmp_path)
    application["mqtt_bridge"] = _bridge_mock()
    application["state_synchronizer"] = StateSynchronizer(app=application, mqtt_bridge=application["mqtt_bridge"])
    return application


@pytest.fixture
async def cli(aiohttp_client, app):
    with patch("transport.http_server.asyncio.sleep", new=AsyncMock()):
        yield await aiohttp_client(app)


async def _connect(cli, app, extra=None):
    body = {"payload": {"host": "broker.example.invalid", "port": 1883, **(extra or {})}}
    resp = await cli.post("/action/mqtt_connect", json=body, headers=HEADERS)
    assert resp.status == 200
    kwargs = app["mqtt_bridge"].start.call_args.kwargs
    return app["mqtt_bridge"].start.call_args.args[0], kwargs["on_reconnect_cb"], kwargs["on_ha_birth_cb"]


def _calls(bridge):
    return [(c.args[0], c.args[1], c.kwargs) for c in bridge.publish_message.call_args_list]


async def test_sync_publishes_the_alarm_state(cli, app):
    resp = await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)
    assert resp.status == 200, await resp.text()
    states = [c for c in _calls(app["mqtt_bridge"]) if c[0] == f"jeedom2ha/{EQ}/alarm/state"]
    assert states == [(f"jeedom2ha/{EQ}/alarm/state", "armed_away", {"qos": 1, "retain": True})]


@pytest.mark.parametrize("which", ["reconnect", "birth"])
async def test_ha_birth_and_broker_reconnect_republish_the_alarm_state_after_its_discovery(cli, app, which):
    assert (await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)).status == 200
    _params, on_reconnect, on_birth = await _connect(cli, app)
    # Un événement reçu depuis la synchro est repris (dernière valeur connue).
    await app["state_synchronizer"].handle_state_message(EQ, ENABLE, "0")
    bridge = app["mqtt_bridge"]
    bridge.publish_message.reset_mock()
    await (on_reconnect if which == "reconnect" else on_birth)()
    topics = [c[0] for c in _calls(bridge)]
    state_topic = f"jeedom2ha/{EQ}/alarm/state"
    assert topics.count(state_topic) == 1
    assert topics.index(state_topic) > topics.index(f"homeassistant/alarm_control_panel/jeedom2ha_{EQ}/config")
    assert [c for c in _calls(bridge) if c[0] == state_topic] == [(state_topic, "disarmed", {"qos": 1, "retain": True})]
    # Aucun autre type ne republie son état (la lumière garde son comportement d'avant).
    assert "jeedom2ha/7300/state" not in topics


# --- AC4 : commandes par mode --------------------------------------------------------------------

def _cmd_sync(mapping, state_sync=None):
    decision = _decision(mapping)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app = {"publications": {mapping.jeedom_eq_id: decision}, "state_synchronizer": state_sync}
    sync = CommandSynchronizer(app=app, mqtt_bridge=bridge,
                               jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
                               jeedom_core_apikey="core-apikey")
    sync._execute_exec_cmd = AsyncMock(return_value=True)
    # Story 12.5 — lectures fraîches avant un armement : Statut et Immédiat relus à 0 (armement
    # permis) ; Mode et Actif en échec, donc comportement de 12.4 pour la commande envoyée.
    sync._read_info_value = AsyncMock(
        side_effect=lambda cmd_id: (True, "0") if cmd_id in (STATUS, IMMEDIATE, 72001) else (False, None)
    )
    return sync, bridge


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,cmd_id", [
    ("ARM_HOME", MODE_C), ("ARM_AWAY", MODE_A), ("ARM_NIGHT", MODE_B), ("DISARM", RELEASED)])
async def test_orders_by_mode(payload, cmd_id):
    sync, bridge = _cmd_sync(_map(_alarm_eq()))
    assert await sync.handle_command_message(f"jeedom2ha/{EQ}/alarm/set", payload) is True
    sync._execute_exec_cmd.assert_awaited_once_with(cmd_id, {})
    bridge.publish_message.assert_not_called()  # jamais d'état optimiste


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ["ARM_VACATION", "ARM_CUSTOM_BYPASS", "TRIGGER", "arm_away", "", "ON", "{}"])
async def test_unknown_payloads_are_refused(payload):
    sync, _bridge = _cmd_sync(_map(_alarm_eq()))
    assert await sync.handle_command_message(f"jeedom2ha/{EQ}/alarm/set", payload) is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_an_arming_not_announced_is_refused():
    sync, _bridge = _cmd_sync(_map(_alarm_eq(config={"SetModeNuit": f"{MODE_B}|mode nuit"})))
    for payload in ("ARM_HOME", "ARM_AWAY"):
        assert await sync.handle_command_message(f"jeedom2ha/{EQ}/alarm/set", payload) is False
    sync._execute_exec_cmd.assert_not_awaited()
    assert await sync.handle_command_message(f"jeedom2ha/{EQ}/alarm/set", "ARM_NIGHT") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_B, {})


@pytest.mark.asyncio
async def test_without_mode_configuration_arm_away_runs_the_generic_arm_command():
    sync, _bridge = _cmd_sync(_map(_alarm_eq(config={})))
    assert await sync.handle_command_message(f"jeedom2ha/{EQ}/alarm/set", "ARM_AWAY") is True
    sync._execute_exec_cmd.assert_awaited_once_with(ARMED, {})
    assert await sync.handle_command_message(f"jeedom2ha/{EQ}/alarm/set", "ARM_HOME") is False


@pytest.mark.asyncio
async def test_a_foreign_command_slipped_into_the_mapping_is_refused():
    mapping = _map(_alarm_eq())
    mapping.commands["ALARM_SET_MODE_HOME"] = _cmd(99999, "ALARM_SET_MODE")  # pas une commande retenue
    mapping.commands["ALARM_SET_MODE_AWAY"] = _cmd(MODE_A, "ENERGY_ON")      # mauvais generic type
    sync, _bridge = _cmd_sync(mapping)
    assert await sync.handle_command_message(f"jeedom2ha/{EQ}/alarm/set", "ARM_AWAY") is False
    sync._execute_exec_cmd.assert_not_awaited()


def test_confirmation_policy_is_never_optimistic():
    mapping = _map(_alarm_eq())
    translation = CommandTranslation(cmd_id=MODE_A, options={}, command_family="alarm_arm")
    streamed = StateSynchronizer(app={}, mqtt_bridge=_Bridge())
    sync, _b = _cmd_sync(mapping, state_sync=streamed)
    assert sync._select_confirmation_policy(mapping, mapping.publication_decision_ref, translation) \
        == "real_state_confirmation"
    sync, _b = _cmd_sync(mapping, state_sync=None)
    assert sync._select_confirmation_policy(mapping, mapping.publication_decision_ref, translation) == "stateless"


# --- AC6 : code de désarmement -----------------------------------------------------------------

def _coded(action, code):
    return json.dumps({"action": action, "code": code})


@pytest.mark.asyncio
async def test_code_good_disarms(caplog):
    set_alarm_code(CODE)
    sync, _bridge = _cmd_sync(_map(_alarm_eq()))
    with caplog.at_level(logging.DEBUG):
        assert await sync.handle_command_message(f"jeedom2ha/{EQ}/alarm/set", _coded("DISARM", CODE)) is True
    sync._execute_exec_cmd.assert_awaited_once_with(RELEASED, {})
    assert CODE not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,reason", [
    (_coded("DISARM", "0000"), "alarm_code_invalid"),
    (_coded("DISARM", CODE + " "), "alarm_code_invalid"),
    (_coded("DISARM", CODE.upper() + "x"), "alarm_code_invalid"),
    (_coded("DISARM", ""), "alarm_code_missing"),
    (_coded("DISARM", None), "alarm_code_missing"),
    (json.dumps({"action": "DISARM"}), "alarm_code_missing"),
    ("DISARM", "alarm_code_missing"),
])
async def test_code_wrong_or_missing_is_refused_with_a_warning_without_the_code(caplog, payload, reason):
    set_alarm_code(CODE)
    sync, _bridge = _cmd_sync(_map(_alarm_eq()))
    with caplog.at_level(logging.DEBUG):
        assert await sync.handle_command_message(f"jeedom2ha/{EQ}/alarm/set", payload) is False
    sync._execute_exec_cmd.assert_not_awaited()
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING and f"reason_code={reason}" in r.getMessage()]
    assert len(warnings) == 1
    assert CODE not in caplog.text and "0000" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [_coded("ARM_AWAY", ""), _coded("ARM_AWAY", None), "ARM_AWAY"])
async def test_with_a_code_arming_stays_free(payload):
    set_alarm_code(CODE)
    sync, _bridge = _cmd_sync(_map(_alarm_eq()))
    assert await sync.handle_command_message(f"jeedom2ha/{EQ}/alarm/set", payload) is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_A, {})


@pytest.mark.asyncio
async def test_without_a_configured_code_disarm_needs_no_code():
    sync, _bridge = _cmd_sync(_map(_alarm_eq()))
    assert await sync.handle_command_message(f"jeedom2ha/{EQ}/alarm/set", "DISARM") is True
    sync._execute_exec_cmd.assert_awaited_once_with(RELEASED, {})


def test_comparison_is_constant_time_and_the_vault_never_shows_the_code():
    set_alarm_code(CODE)
    with patch("sync.alarm_code.hmac.compare_digest", wraps=alarm_code.hmac.compare_digest) as spy:
        assert alarm_code.alarm_code_matches(CODE) is True
        assert alarm_code.alarm_code_matches("autre") is False
    assert spy.call_count == 2
    assert CODE not in repr(ALARM_CODE) and CODE not in str(ALARM_CODE)
    set_alarm_code("   ")
    assert alarm_code.alarm_code_configured() is False


async def test_the_code_arrives_in_the_local_body_and_never_reaches_the_broker_settings(cli, app, caplog):
    with caplog.at_level(logging.DEBUG):
        params, _r, _b = await _connect(cli, app, {"alarm_disarm_code": CODE, "password": "mqtt-pass"})
    assert alarm_code.alarm_code_configured() is True
    assert "alarm_disarm_code" not in params and params["password"] == "mqtt-pass"
    assert CODE not in caplog.text
    # Sans la clé : pas de code (un démon relancé sans code repart sans code).
    await _connect(cli, app)
    assert alarm_code.alarm_code_configured() is False


def test_the_code_is_never_on_the_daemon_command_line():
    """Le démon n'a aucun argument de ligne de commande pour le code (visible par ``ps``)."""
    import main
    config = main.Jeedom2haConfig()
    parser = getattr(config, "_BaseConfig__parser")
    options = [opt for action in parser._actions for opt in action.option_strings]
    assert options and not any("alarm" in opt or "code" in opt for opt in options)
    source = open(main.__file__, encoding="utf-8").read()
    assert "alarm" not in source.lower()


# --- AC6 : discovery -----------------------------------------------------------------------------

def test_discovery_without_code():
    payload = _discovery(_alarm_eq())
    assert payload["supported_features"] == ["arm_home", "arm_away", "arm_night"]
    assert "value_template" not in payload
    assert payload["payload_arm_night"] == "ARM_NIGHT"
    for key in ("code", "code_disarm_required", "code_arm_required", "command_template"):
        assert key not in payload


def test_discovery_with_code_publishes_only_its_presence():
    set_alarm_code(CODE)
    payload = _discovery(_alarm_eq())
    assert payload["code"] == "REMOTE_CODE"
    assert payload["code_disarm_required"] is True
    assert payload["code_arm_required"] is False
    assert "action" in payload["command_template"] and "code" in payload["command_template"]
    assert CODE not in json.dumps(payload)


async def test_published_discovery_never_contains_the_code(cli, app):
    await _connect(cli, app, {"alarm_disarm_code": CODE})
    assert (await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)).status == 200
    calls = _calls(app["mqtt_bridge"])
    config = [c for c in calls if c[0] == f"homeassistant/alarm_control_panel/jeedom2ha_{EQ}/config"]
    assert len(config) == 1 and json.loads(config[0][1])["code"] == "REMOTE_CODE"
    assert all(CODE not in str(c[1]) for c in calls)


# --- AC7 : non-régression du virtuel générique ---------------------------------------------------

@pytest.mark.asyncio
async def test_generic_virtual_alarm_still_works():
    mapping = _map(_virtual_eq())
    assert mapping.reason_details["supported_features"] == ["arm_away"]
    assert "alarm_mode_labels" not in mapping.reason_details
    sync, bridge, decision = _state_sync(mapping)
    assert await sync.publish_initial_states(decision) == 1
    await sync.handle_state_message(VIRTUAL, 72002, "0")
    await sync.handle_state_message(VIRTUAL, 72002, "1")
    await sync.handle_state_message(VIRTUAL, 72001, "1")
    assert [p[1] for p in bridge.published] == ["armed_away", "disarmed", "armed_away", "triggered"]
    cmd, _b = _cmd_sync(_map(_virtual_eq()))
    assert await cmd.handle_command_message(f"jeedom2ha/{VIRTUAL}/alarm/set", "ARM_AWAY") is True
    assert await cmd.handle_command_message(f"jeedom2ha/{VIRTUAL}/alarm/set", "DISARM") is True
    assert [c.args for c in cmd._execute_exec_cmd.await_args_list] == [(72003, {}), (72004, {})]
    assert await cmd.handle_command_message(f"jeedom2ha/{VIRTUAL}/alarm/set", "ARM_HOME") is False


def test_alarm_supported_features_helper_is_the_single_source():
    mapping = _map(_virtual_eq())
    assert alarm_supported_features(mapping.commands) == mapping.reason_details["supported_features"]


# --- Revue Codex de 12.4 : retour à ``unknown`` ---------------------------------------------------
# Source : Home Assistant, homeassistant/components/mqtt/alarm_control_panel.py, _state_message_received :
# ``if payload == PAYLOAD_NONE: self._attr_alarm_state = None`` avec PAYLOAD_NONE = "None"
# (homeassistant/components/mqtt/const.py) ; un payload vide est ignoré.

def _status_only_virtual(status="1"):
    return JeedomEqLogic(
        id=VIRTUAL, name="Alarme virtuelle", object_id=1, eq_type_name="virtual",
        cmds=[_cmd(72001, "ALARM_STATE", "info", "binary", status),
              _cmd(72003, "ALARM_ENABLE"), _cmd(72004, "ALARM_DISABLE")],
    )


def test_unknown_payload_is_the_one_home_assistant_reads_as_unknown():
    from sync.state import ALARM_UNKNOWN_PAYLOAD
    assert ALARM_UNKNOWN_PAYLOAD == "None"


@pytest.mark.asyncio
async def test_status_only_virtual_going_back_to_0_resets_ha_to_unknown():
    """Le cas Codex P2 : un virtuel à ALARM_STATE seul passe de 1 à 0 -> HA ne reste pas sur ``triggered``."""
    sync, bridge, decision = _state_sync(_map(_status_only_virtual(status="1")))
    assert await sync.publish_initial_states(decision) == 1
    assert await sync.handle_state_message(VIRTUAL, 72001, "0") is True
    assert await sync.handle_state_message(VIRTUAL, 72001, "0") is False   # déjà inconnu : pas de doublon
    assert await sync.handle_state_message(VIRTUAL, 72001, "1") is True
    topic = f"jeedom2ha/{VIRTUAL}/alarm/state"
    assert bridge.published == [(topic, "triggered", 1, True), (topic, "None", 1, True), (topic, "triggered", 1, True)]


@pytest.mark.asyncio
@pytest.mark.parametrize("unreadable", [None, "", "abc", "2"])
async def test_enable_becoming_unreadable_resets_ha_to_unknown(unreadable):
    sync, bridge, _d = _state_sync(_map(_alarm_eq(enable="1", mode="mode nuit")))
    await sync.handle_state_message(EQ, MODE, "mode nuit")
    await sync.handle_state_message(EQ, ENABLE, unreadable)
    await sync.handle_state_message(EQ, ENABLE, "0")
    assert [p[1] for p in bridge.published] == ["armed_night", "None", "disarmed"]
    assert all(p[3] is True for p in bridge.published)   # retained, comme les autres états


@pytest.mark.asyncio
async def test_still_unknown_after_a_restart_resets_ha_at_the_first_event():
    """Après un redémarrage, rien n'est connu de ce run : le premier calcul inconnu publie ``None``."""
    sync, bridge, _d = _state_sync(_map(_alarm_eq(enable=None)))
    assert await sync.handle_state_message(EQ, STATUS, "0") is True
    assert bridge.published == [(f"jeedom2ha/{EQ}/alarm/state", "None", 1, True)]


@pytest.mark.asyncio
async def test_republication_of_an_unknown_alarm_publishes_unknown_too():
    sync, bridge, decision = _state_sync(_map(_status_only_virtual(status="0")))
    assert await sync.republish_alarm_states(decision) == 1
    published, failed = await sync.publish_click_states(decision, {72001: "0"}, fresh_since=0.0)
    assert (published, failed) == (1, 0)
    assert [p[1] for p in bridge.published] == ["None", "None"]


@pytest.mark.asyncio
async def test_other_types_never_get_the_unknown_payload():
    sync, bridge, _d = _state_sync(_map(_alarm_eq()))
    mapping = MagicMock(ha_entity_type="sensor")
    assert sync._alarm_needs_unknown(mapping, "jeedom2ha/1/state") is False


# --- Revue de 12.4 : code configuré mais illisible ------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [_coded("DISARM", CODE), _coded("DISARM", "1234"), "DISARM", _coded("DISARM", "")])
async def test_unreadable_code_refuses_every_disarm_with_a_warning(caplog, payload):
    set_alarm_code(None, unreadable=True)
    sync, _bridge = _cmd_sync(_map(_alarm_eq()))
    with caplog.at_level(logging.DEBUG):
        assert await sync.handle_command_message(f"jeedom2ha/{EQ}/alarm/set", payload) is False
    sync._execute_exec_cmd.assert_not_awaited()
    warnings = [r for r in caplog.records
                if r.levelno == logging.WARNING and "reason_code=alarm_code_unreadable" in r.getMessage()]
    assert len(warnings) == 1
    assert CODE not in caplog.text


@pytest.mark.asyncio
async def test_unreadable_code_keeps_arming_free():
    set_alarm_code(None, unreadable=True)
    sync, _bridge = _cmd_sync(_map(_alarm_eq()))
    assert await sync.handle_command_message(f"jeedom2ha/{EQ}/alarm/set", "ARM_AWAY") is True
    sync._execute_exec_cmd.assert_awaited_once_with(MODE_A, {})


def test_unreadable_code_keeps_the_discovery_requiring_the_code():
    set_alarm_code(None, unreadable=True)
    assert alarm_code.alarm_code_configured() is True and alarm_code.alarm_code_unreadable() is True
    assert alarm_code.alarm_code_matches("") is False and alarm_code.alarm_code_matches("1234") is False
    payload = _discovery(_alarm_eq())
    assert payload["code"] == "REMOTE_CODE" and payload["code_disarm_required"] is True
    # Un indicateur « illisible » l'emporte sur un code qui arriverait quand même.
    set_alarm_code(CODE, unreadable=True)
    assert alarm_code.alarm_code_matches(CODE) is False


async def test_the_unreadable_flag_arrives_in_the_local_body(cli, app, caplog):
    with caplog.at_level(logging.DEBUG):
        params, _r, _b = await _connect(cli, app, {"alarm_disarm_code_unreadable": True})
    assert "alarm_disarm_code_unreadable" not in params
    assert alarm_code.alarm_code_unreadable() is True and alarm_code.alarm_code_configured() is True
    assert any(r.levelno == logging.WARNING and "illisible" in r.getMessage() for r in caplog.records)
    # Seul ``true`` compte ; un démon relancé sans l'indicateur repart sans code.
    await _connect(cli, app, {"alarm_disarm_code_unreadable": "yes"})
    assert alarm_code.alarm_code_configured() is False


# --- Revue de 12.4 : limite d'essais ----------------------------------------------------------------

class _Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


async def _disarm(sync, code, eq=EQ):
    return await sync.handle_command_message(f"jeedom2ha/{eq}/alarm/set", _coded("DISARM", code))


@pytest.mark.asyncio
async def test_five_wrong_codes_lock_the_disarm_for_five_minutes(caplog):
    clock = _Clock()
    ALARM_LOCKOUT.clock = clock
    set_alarm_code("4321")
    sync, _bridge = _cmd_sync(_map(_alarm_eq()))
    with caplog.at_level(logging.DEBUG):
        for _ in range(5):
            assert await _disarm(sync, "0000") is False
        assert await _disarm(sync, "4321") is False          # verrouillé : même le bon code est refusé
        clock.now += 299.0
        assert await _disarm(sync, "4321") is False
    sync._execute_exec_cmd.assert_not_awaited()
    locked = [r for r in caplog.records if r.levelno == logging.WARNING and "reason_code=alarm_code_locked" in r.getMessage()]
    assert len(locked) == 2
    assert any(r.levelno == logging.WARNING and "verrouillé" in r.getMessage() for r in caplog.records)
    assert "4321" not in caplog.text and "0000" not in caplog.text
    clock.now += 1.0                                        # 300 s : le verrou expire
    assert await _disarm(sync, "4321") is True
    sync._execute_exec_cmd.assert_awaited_once_with(RELEASED, {})


@pytest.mark.asyncio
async def test_lockout_expiry_resets_the_counter():
    clock = _Clock()
    ALARM_LOCKOUT.clock = clock
    set_alarm_code("4321")
    sync, _bridge = _cmd_sync(_map(_alarm_eq()))
    for _ in range(5):
        await _disarm(sync, "0000")
    clock.now += 300.0
    for _ in range(4):                                      # compteur reparti de zéro : 4 essais faux de plus
        assert await _disarm(sync, "0000") is False
    assert await _disarm(sync, "4321") is True


@pytest.mark.asyncio
async def test_a_good_code_resets_the_counter():
    ALARM_LOCKOUT.clock = _Clock()
    set_alarm_code("4321")
    sync, _bridge = _cmd_sync(_map(_alarm_eq()))
    for _ in range(4):
        await _disarm(sync, "0000")
    assert await _disarm(sync, "4321") is True
    for _ in range(4):
        assert await _disarm(sync, "0000") is False
    assert await _disarm(sync, "4321") is True             # jamais 5 faux d'affilée : jamais verrouillé
    assert sync._execute_exec_cmd.await_count == 2


@pytest.mark.asyncio
async def test_the_lockout_is_per_equipment():
    ALARM_LOCKOUT.clock = _Clock()
    set_alarm_code("4321")
    sync, _bridge = _cmd_sync(_map(_alarm_eq()))
    for _ in range(5):
        await _disarm(sync, "0000")
    other, _b = _cmd_sync(_map(_virtual_eq()))
    assert await _disarm(other, "4321", eq=VIRTUAL) is True
    assert await _disarm(sync, "4321") is False


@pytest.mark.asyncio
async def test_missing_codes_and_armings_do_not_count_as_failures():
    ALARM_LOCKOUT.clock = _Clock()
    set_alarm_code("4321")
    sync, _bridge = _cmd_sync(_map(_alarm_eq()))
    for _ in range(6):
        assert await sync.handle_command_message(f"jeedom2ha/{EQ}/alarm/set", "DISARM") is False
        assert await sync.handle_command_message(f"jeedom2ha/{EQ}/alarm/set", "ARM_AWAY") is True
    assert await _disarm(sync, "4321") is True


def test_lockout_unit_with_an_injected_clock():
    clock = _Clock()
    lockout = AlarmDisarmLockout(max_failures=5, lock_seconds=300, clock=clock)
    assert [lockout.record_failure(1) for _ in range(5)] == [False, False, False, False, True]
    assert lockout.is_locked(1) and not lockout.is_locked(2)
    clock.now += 300
    assert not lockout.is_locked(1)
    assert lockout.record_failure(1) is False


def test_a_new_code_clears_the_lockout():
    ALARM_LOCKOUT.clock = _Clock()
    for _ in range(5):
        ALARM_LOCKOUT.record_failure(EQ)
    assert ALARM_LOCKOUT.is_locked(EQ)
    set_alarm_code("1357")
    assert not ALARM_LOCKOUT.is_locked(EQ)


# --- Revue de 12.4 : deux clés Homebridge au même libellé -------------------------------------------

def test_duplicate_mode_labels_warn_without_changing_the_behaviour(caplog):
    config = {"SetModePresent": f"{MODE_C}|Mode Jour", "SetModeAbsent": f"{MODE_A}|  mode JOUR ",
              "SetModeNuit": f"{MODE_B}|mode nuit"}
    with caplog.at_level(logging.WARNING, logger="mapping.alarm_control_panel"):
        mapping = _map(_alarm_eq(config=config))
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert "SetModePresent" in message and "SetModeAbsent" in message and "SetModeNuit" not in message
    assert "Mode Jour" not in message                       # libellés jamais écrits
    # Comportement inchangé : les trois armements, état du premier dans l'ordre Présent, Absent, Nuit.
    assert mapping.reason_details["supported_features"] == ["arm_home", "arm_away", "arm_night"]
    assert alarm_state("0", "1", "0", "mode jour", {"armed_home": "Mode Jour", "armed_away": "mode JOUR"}) == "armed_home"


def test_distinct_mode_labels_do_not_warn(caplog):
    with caplog.at_level(logging.WARNING, logger="mapping.alarm_control_panel"):
        _map(_alarm_eq())
    assert [r for r in caplog.records if r.levelno == logging.WARNING] == []


# --- Revue Codex de 12.4 (2e passe) : un événement à None n'est pas « aucun événement » --------------

@pytest.mark.asyncio
async def test_enable_none_event_is_kept_for_the_next_event_of_another_info():
    """Actif=1 en topologie, puis Actif=None, puis Mode : l'état reste inconnu (pas de retour à la topologie)."""
    sync, bridge, _d = _state_sync(_map(_alarm_eq(enable="1", mode="mode total")))
    await sync.handle_state_message(EQ, ENABLE, None)
    await sync.handle_state_message(EQ, MODE, "mode nuit")
    await sync.handle_state_message(EQ, STATUS, "0")
    await sync.handle_state_message(EQ, IMMEDIATE, "0")
    assert [p[1] for p in bridge.published] == ["None"]          # jamais armed_away / armed_night
    await sync.handle_state_message(EQ, ENABLE, "1")              # Actif relu : l'état revient
    assert [p[1] for p in bridge.published] == ["None", "armed_night"]


@pytest.mark.asyncio
async def test_republication_after_enable_none_stays_unknown():
    sync, bridge, decision = _state_sync(_map(_alarm_eq(enable="1", mode="mode total")))
    await sync.handle_state_message(EQ, ENABLE, None)
    bridge.published.clear()
    assert await sync.republish_alarm_states(decision) == 1
    assert bridge.published == [(f"jeedom2ha/{EQ}/alarm/state", "None", 1, True)]


@pytest.mark.asyncio
@pytest.mark.parametrize("cmd_id,topology,later,expected", [
    # Statut=1 en topologie, Statut=None : jamais « triggered » ressuscité par un autre événement.
    (STATUS, {"status": "1"}, (ENABLE, "1"), "armed_night"),
    # Immédiat=1 en topologie, Immédiat=None : jamais « pending » ressuscité.
    (IMMEDIATE, {"immediate": "1"}, (ENABLE, "1"), "armed_night"),
    # Mode « Mode Jour » en topologie, Mode=None : mode inconnu -> armed_away (règle 5), jamais armed_home.
    (MODE, {"mode": "Mode Jour"}, (ENABLE, "1"), "armed_away"),
])
async def test_none_event_of_status_immediate_or_mode_is_kept_too(cmd_id, topology, later, expected):
    kwargs = {"enable": "1", "status": "0", "immediate": "0", "mode": "mode nuit", **topology}
    sync, bridge, decision = _state_sync(_map(_alarm_eq(**kwargs)))
    await sync.handle_state_message(EQ, cmd_id, None)
    await sync.handle_state_message(EQ, *later)
    assert bridge.published[-1][1] == expected
    bridge.published.clear()
    await sync.republish_alarm_states(decision)
    assert [p[1] for p in bridge.published] == [expected]


# --- Revue Codex de 12.4 (3e passe) : magasin unique des quatre infos de l'alarme ----------------
# Pour CHAQUE chemin qui lit une valeur d'alarme : Actif=1 dans la topologie -> lecture ``None`` par ce
# chemin -> événement Mode -> toujours inconnu ; puis la republication (naissance HA / reconnexion).

async def _none_by_event(sync, decision):
    await sync.handle_state_message(EQ, ENABLE, None)


async def _none_by_event_while_mqtt_down(sync, decision):
    sync._mqtt_bridge.is_connected = False
    assert await sync.handle_state_message(EQ, ENABLE, None) is False   # rejeté, mais lu
    sync._mqtt_bridge.is_connected = True


async def _none_by_click(sync, decision):
    published, failed = await sync.publish_click_states(
        decision, {ENABLE: None, STATUS: "0", IMMEDIATE: "0", MODE: "mode total"}, fresh_since=time.monotonic())
    assert (published, failed) == (1, 0)


async def _none_by_click_then_later_click_without_enable(sync, decision):
    await _none_by_click(sync, decision)
    # Un second clic qui ne relit pas Actif ne fait pas revenir la topologie.
    await sync.publish_click_states(decision, {MODE: "mode total"}, fresh_since=time.monotonic())


async def _none_by_fresh_read(sync, decision):
    sync.reconcile_fresh_read(decision, time.monotonic(), {ENABLE: None})


async def _none_by_sync_topology(sync, decision):
    decision.mapping_result.commands["ALARM_ENABLE_STATE"].current_value = None
    sync.reconcile_fresh_read(decision, time.monotonic())
    await sync.publish_initial_states(decision)


async def _none_by_event_older_than_a_sync_is_replaced_but_newer_is_kept(sync, decision):
    read_at = time.monotonic()
    await sync.handle_state_message(EQ, ENABLE, None)                  # reçu APRÈS la lecture de la synchro
    sync.reconcile_fresh_read(decision, read_at)                       # topologie (Actif=1) plus ancienne
    await sync.publish_initial_states(decision)


@pytest.mark.asyncio
@pytest.mark.parametrize("read_none", [
    _none_by_event, _none_by_event_while_mqtt_down, _none_by_click, _none_by_click_then_later_click_without_enable,
    _none_by_fresh_read, _none_by_sync_topology, _none_by_event_older_than_a_sync_is_replaced_but_newer_is_kept,
], ids=lambda f: f.__name__.lstrip("_"))
async def test_a_none_read_by_any_path_keeps_the_alarm_unknown(read_none):
    sync, bridge, decision = _state_sync(_map(_alarm_eq(enable="1", mode="mode total")))
    sync.reconcile_fresh_read(decision, time.monotonic())             # 1re synchro : Actif=1
    assert await sync.publish_initial_states(decision) == 1
    assert bridge.published[-1][1] == "armed_away"
    await read_none(sync, decision)
    await sync.handle_state_message(EQ, MODE, "mode nuit")
    await sync.handle_state_message(EQ, STATUS, "0")
    await sync.handle_state_message(EQ, IMMEDIATE, "0")
    assert bridge.published[-1][1] == "None"
    assert "armed_night" not in [p[1] for p in bridge.published]
    bridge.published.clear()
    assert await sync.republish_alarm_states(decision) == 1           # naissance HA / reconnexion
    assert [p[1] for p in bridge.published] == ["None"]
    # Seule une lecture plus récente d'Actif rend un état.
    await sync.handle_state_message(EQ, ENABLE, "1")
    assert bridge.published[-1][1] == "armed_night"


@pytest.mark.asyncio
async def test_after_a_restart_the_store_is_rebuilt_from_the_sync_topology():
    """Redémarrage : un nouveau démon n'a aucune lecture ; la 1re synchro (Actif=None) fait foi."""
    sync, bridge, decision = _state_sync(_map(_alarm_eq(enable=None, mode="mode total")))
    sync.reconcile_fresh_read(decision, time.monotonic())
    await sync.publish_initial_states(decision)
    await sync.handle_state_message(EQ, MODE, "mode nuit")
    assert [p[1] for p in bridge.published] == ["None"]


@pytest.mark.asyncio
async def test_an_event_received_before_the_equipment_is_published_is_kept_by_the_sync():
    """Événement reçu avant que l'alarme soit au registre, mais après la lecture de la synchro."""
    mapping = _map(_alarm_eq(enable="1", mode="mode total"))
    bridge = _Bridge()
    app = {"publications": {}}
    sync = StateSynchronizer(app=app, mqtt_bridge=bridge)
    read_at = time.monotonic()
    await sync.handle_state_message(EQ, ENABLE, None)                  # pas encore publiée : rejeté
    decision = _decision(mapping)
    app["publications"][EQ] = decision
    sync.reconcile_fresh_read(decision, read_at)
    await sync.publish_initial_states(decision)
    assert [p[1] for p in bridge.published] == ["None"]


@pytest.mark.parametrize("which", ["reconnect", "birth"])
async def test_full_sync_with_unreadable_enable_then_mode_event_and_republication(cli, app, which):
    """Bout en bout par /action/sync : Actif=1, puis synchro avec Actif illisible, puis Mode, puis CC-08."""
    assert (await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)).status == 200
    body = _sync_body()
    for raw in body["payload"]["eq_logics"][0]["cmds"]:
        if raw["id"] == ENABLE:
            raw["current_value"] = None
    assert (await cli.post("/action/sync", json=body, headers=HEADERS)).status == 200
    _params, on_reconnect, on_birth = await _connect(cli, app)
    bridge = app["mqtt_bridge"]
    state_topic = f"jeedom2ha/{EQ}/alarm/state"
    assert [c[1] for c in _calls(bridge) if c[0] == state_topic][-1] == "None"
    await app["state_synchronizer"].handle_state_message(EQ, MODE, "mode nuit")
    bridge.publish_message.reset_mock()
    await (on_reconnect if which == "reconnect" else on_birth)()
    assert [c[1] for c in _calls(bridge) if c[0] == state_topic] == ["None"]


# --- Revue Codex de 12.4 (4e passe) : « lu à null » au clic, du relais PHP jusqu'au démon ------------

import shutil  # noqa: E402
import subprocess  # noqa: E402
from pathlib import Path  # noqa: E402

_REPO = Path(__file__).resolve().parents[4]
_STATE_TOPIC = f"jeedom2ha/{EQ}/alarm/state"

# Vrai relais PHP : lecture au clic (Actif lu à null, Mode lu, Statut non lu car l'échéance est
# dépassée), puis appel de /action/execute avec le même câblage que l'ajax. Imprime le payload.
_PHP_CLICK = r"""
define('JEEDOM2HA_AJAX_FUNCTIONS_ONLY', true);
require_once $argv[1] . '/core/ajax/jeedom2ha.ajax.php';
$cmds = array(
    array('cmd_id' => %(enable)d, 'type' => 'info', 'alarm_info' => true, 'value' => null),
    array('cmd_id' => %(mode)d, 'type' => 'info', 'alarm_info' => true, 'value' => 'mode total'),
    array('cmd_id' => %(status)d, 'type' => 'info', 'alarm_info' => true, 'value' => null),
);
$clock = 0.0;
$readNull = new ArrayObject();
$values = _jeedom2ha_collect_click_values('equipement', array('%(eq)d'),
    function ($p) { return array(); }, function () { return array(); },
    function ($eqId) use ($cmds) { return $cmds; },
    function ($c) use ($readNull, &$clock) { $clock += 1.0; return jeedom2ha_alarm_click_read($c, $c['value'], $readNull); },
    function ($m) {}, function () use (&$clock) { return $clock; }, 1.5);
$sent = null;
jeedom2ha_dispatch_action_relay('publier',
    array('intention' => 'publier', 'portee' => 'equipement', 'selection' => array(%(eq)d)),
    function ($t, $a) { return array('status' => 'ok'); },
    function () use ($values) { return $values; },
    function (array $p, $t) use ($readNull, &$sent) { $sent = jeedom2ha_alarm_add_click_null_reads($p, $readNull); return array('status' => 'ok'); },
    function ($r) {}, function ($l, $m) {}, function () { return 0.0; });
unset($sent['deadline_s']);
echo json_encode($sent);
""" % {"enable": ENABLE, "mode": MODE, "status": STATUS, "eq": EQ}


def _php_click_payload():
    if shutil.which("php") is None:
        pytest.skip("php indisponible")
    out = subprocess.run(["php", "-r", _PHP_CLICK, "--", str(_REPO)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


async def _publier(cli, body):
    with patch("transport.http_server.asyncio.sleep", new=AsyncMock()):
        resp = await cli.post("/action/execute", json=body, headers=HEADERS)
    assert resp.status == 200, await resp.text()


def _alarm_states(bridge):
    return [c[1] for c in _calls(bridge) if c[0] == _STATE_TOPIC]


def test_the_php_relay_sends_read_null_alarm_infos_apart():
    payload = _php_click_payload()
    assert payload["current_values"] == {str(MODE): "mode total"}      # inchangé : les null restent omis
    assert payload["current_values_null"] == [ENABLE]                 # Statut, non lu, n'y est pas


@pytest.mark.parametrize("which", ["reconnect", "birth"])
async def test_end_to_end_click_reading_enable_at_null_keeps_the_alarm_unknown(cli, app, which):
    """Du payload PHP réel jusqu'au démon : Actif=1 (synchro) -> clic lit Actif à null -> Mode -> inconnu."""
    payload = _php_click_payload()
    assert (await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)).status == 200
    bridge = app["mqtt_bridge"]
    assert _alarm_states(bridge)[-1] == "armed_away"
    await _publier(cli, payload)
    assert _alarm_states(bridge)[-1] == "None"
    await app["state_synchronizer"].handle_state_message(EQ, MODE, "mode nuit")
    await app["state_synchronizer"].handle_state_message(EQ, STATUS, "0")
    assert _alarm_states(bridge)[-1] == "None"
    _params, on_reconnect, on_birth = await _connect(cli, app)
    bridge.publish_message.reset_mock()
    await (on_reconnect if which == "reconnect" else on_birth)()
    assert _alarm_states(bridge) == ["None"]


async def test_a_command_not_read_at_the_click_keeps_its_previous_read(cli, app):
    """Ancien relais (ou échéance dépassée) : Actif absent des deux listes = non lu -> lecture précédente."""
    assert (await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)).status == 200
    await _publier(cli, {"intention": "publier", "portee": "equipement", "selection": [EQ],
                         "current_values": {str(MODE): "mode nuit"}})
    assert _alarm_states(app["mqtt_bridge"])[-1] == "armed_night"


async def test_a_click_reading_only_null_alarm_infos_still_republishes_unknown(cli, app):
    """Tout lu à null : `current_values` vide (PHP `[]`), la liste des null suffit."""
    assert (await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)).status == 200
    await _publier(cli, {"intention": "publier", "portee": "equipement", "selection": [EQ],
                         "current_values": [], "current_values_null": [ENABLE]})
    assert _alarm_states(app["mqtt_bridge"])[-1] == "None"
    await app["state_synchronizer"].handle_state_message(EQ, MODE, "mode nuit")
    assert _alarm_states(app["mqtt_bridge"])[-1] == "None"


@pytest.mark.parametrize("raw,expected", [
    ([1, "2", 3.0], {1, 2, 3}), ([True, None, "x", {}], set()), ("1,2", set()), (None, set()), ({"1": 1}, set()),
])
def test_click_null_reads_parsing(raw, expected):
    assert set(http_server._parse_click_null_reads(raw)) == expected


def test_a_read_null_only_concerns_alarm_infos():
    """La liste ne touche que les infos d'alarme : une autre commande n'entre jamais dans le magasin."""
    sync, _bridge, decision = _state_sync(_map(_alarm_eq()))
    sync.record_alarm_click_reads(decision, time.monotonic(), {}, [ENABLE, 99999, ARMED])
    assert set(sync._alarm_reads) == {(EQ, ENABLE)}
    assert sync._alarm_reads[(EQ, ENABLE)][1] is None


# --- Revue Codex de 12.4 (5e passe) : un échec de publication d'état n'est jamais avalé -------------

class _FailingBridge(_Bridge):
    """Broker connecté qui refuse les publications d'état de l'alarme."""

    def publish_message(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return not topic.endswith("/alarm/state")


def _failing_state_sync(mapping):
    bridge = _FailingBridge()
    decision = _decision(mapping)
    sync = StateSynchronizer(app={"publications": {mapping.jeedom_eq_id: decision}}, mqtt_bridge=bridge)
    return sync, bridge, decision


def _warnings(caplog, reason):
    return [r for r in caplog.records if r.levelno == logging.WARNING and f"reason_code={reason}" in r.getMessage()]


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["1", None])
async def test_event_publication_failure_is_logged_and_retried(caplog, value):
    sync, bridge, _d = _failing_state_sync(_map(_alarm_eq(enable="1")))
    with caplog.at_level(logging.DEBUG):
        assert await sync.handle_state_message(EQ, ENABLE, value) is False
    assert len(_warnings(caplog, "mqtt_publish_failed")) == 1
    # Rien n'est retenu comme publié : l'événement suivant republie (un état inconnu compris).
    bridge.publish_message = lambda *a, **k: True
    assert await sync.handle_state_message(EQ, STATUS, "0") is True


@pytest.mark.asyncio
@pytest.mark.parametrize("enable", ["1", None])
async def test_sync_publication_failure_is_logged(caplog, enable):
    sync, _bridge, decision = _failing_state_sync(_map(_alarm_eq(enable=enable)))
    sync.reconcile_fresh_read(decision, time.monotonic())
    with caplog.at_level(logging.DEBUG):
        assert await sync.publish_initial_states(decision) == 0
    assert len(_warnings(caplog, "alarm_state_publish_failed")) == 1


@pytest.mark.asyncio
async def test_sync_failure_logging_does_not_touch_the_other_types(caplog):
    """Les autres types gardent le comportement de la synchro (aucun journal d'échec, Story 19.5 AC9)."""
    from models.mapping import MappingResult
    sync = StateSynchronizer(app={}, mqtt_bridge=_FailingBridge())
    candidate = MagicMock(spec=MappingResult)
    candidate.ha_entity_type = "sensor"
    with caplog.at_level(logging.DEBUG):
        assert sync._alarm_needs_unknown(candidate, "jeedom2ha/1/state") is False
    assert _warnings(caplog, "alarm_state_publish_failed") == []


@pytest.mark.asyncio
@pytest.mark.parametrize("values", [{ENABLE: "1", MODE: "mode nuit"}, {ENABLE: None}])
async def test_click_with_values_publication_failure_is_counted(caplog, values):
    sync, _bridge, decision = _failing_state_sync(_map(_alarm_eq()))
    with caplog.at_level(logging.DEBUG):
        assert await sync.publish_click_states(decision, values, fresh_since=time.monotonic()) == (0, 1)
    assert len(_warnings(caplog, "initial_state_publish_failed")) == 1


@pytest.mark.asyncio
async def test_click_with_only_null_alarm_reads_publication_failure_is_counted(caplog):
    sync, _bridge, decision = _failing_state_sync(_map(_alarm_eq()))
    sync.record_alarm_click_reads(decision, time.monotonic(), {}, [ENABLE])
    with caplog.at_level(logging.DEBUG):
        assert await sync.publish_alarm_click_states(decision) == (0, 1)
    assert len(_warnings(caplog, "initial_state_publish_failed")) == 1


@pytest.mark.asyncio
async def test_republication_failure_is_counted_and_logged(caplog):
    sync, _bridge, decision = _failing_state_sync(_map(_alarm_eq()))
    with caplog.at_level(logging.DEBUG):
        assert await sync.republish_alarm_states_counted(decision) == (0, 1)
        assert await sync.republish_alarm_states(decision) == 0
    assert len(_warnings(caplog, "alarm_state_republish_failed")) == 2


def _fail_alarm_state(bridge):
    def publish(topic, payload, qos=0, retain=False):
        return not topic.endswith("/alarm/state")
    bridge.publish_message = MagicMock(side_effect=publish)


async def test_end_to_end_click_reading_only_null_alarm_infos_counts_the_failure(cli, app, caplog):
    """Le cas Codex : clic qui ne lit qu'Actif à null, publication d'état en échec -> équipement en erreur."""
    assert (await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)).status == 200
    _fail_alarm_state(app["mqtt_bridge"])
    with patch("transport.http_server.asyncio.sleep", new=AsyncMock()), caplog.at_level(logging.WARNING):
        resp = await cli.post("/action/execute", headers=HEADERS, json={
            "intention": "publier", "portee": "equipement", "selection": [EQ],
            "current_values": [], "current_values_null": [ENABLE]})
    body = (await resp.json())
    body = body.get("payload", body)
    assert body["scope_reel"]["equipements_publies_ou_crees"] == 0
    assert body["resultat"] in ("echec", "succes_partiel")
    assert len(_warnings(caplog, "initial_state_publish_failed")) == 1


async def test_end_to_end_click_with_values_counts_the_failure(cli, app, caplog):
    assert (await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)).status == 200
    _fail_alarm_state(app["mqtt_bridge"])
    with patch("transport.http_server.asyncio.sleep", new=AsyncMock()), caplog.at_level(logging.WARNING):
        resp = await cli.post("/action/execute", headers=HEADERS, json={
            "intention": "publier", "portee": "equipement", "selection": [EQ],
            "current_values": {str(MODE): "mode nuit"}, "current_values_null": [ENABLE]})
    body = (await resp.json())
    body = body.get("payload", body)
    assert body["scope_reel"]["equipements_publies_ou_crees"] == 0


async def test_end_to_end_sync_failure_is_logged(cli, app, caplog):
    _fail_alarm_state(app["mqtt_bridge"])
    with caplog.at_level(logging.WARNING):
        assert (await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)).status == 200
    assert len(_warnings(caplog, "alarm_state_publish_failed")) == 1


@pytest.mark.parametrize("which", ["reconnect", "birth"])
async def test_end_to_end_republication_failure_is_logged_as_an_error(cli, app, caplog, which):
    assert (await cli.post("/action/sync", json=_sync_body(), headers=HEADERS)).status == 200
    _params, on_reconnect, on_birth = await _connect(cli, app)
    _fail_alarm_state(app["mqtt_bridge"])
    with caplog.at_level(logging.DEBUG):
        await (on_reconnect if which == "reconnect" else on_birth)()
    assert len(_warnings(caplog, "alarm_state_republish_failed")) == 1
    errors = [r for r in caplog.records if r.levelno == logging.ERROR and "état d'alarme échouée" in r.getMessage()]
    assert len(errors) == 1
    assert not any("état d'alarme republié" in r.getMessage() for r in caplog.records)
