"""Story 24.17 — interrupteurs secondaires confirmés par l'état réel (identifiants synthétiques).

Constat hérité de 24-16 : la décision d'un mapping secondaire ne portait jamais de
``state_topic`` ; un ``switch`` secondaire dont l'état est streamé sur son topic propre tombait
en ``optimistic_controlled`` et journalisait ``missing_state_topic_runtime`` à chaque ordre.

Décisions d'Alexandre : D1 A (topic propre posé à la source sur les décisions secondaires,
``switch`` / ``valve`` / ``lock`` seulement, jamais le repli ``jeedom2ha/<eq>/state``) et D2-a
(``FAN_STATE`` est un canal d'état fiable d'un ``switch``). Forme de production : vraie synchro
``/action/sync`` du corpus doré, synchroniseur d'état actif.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import transport.http_server as http_server
from models.mapping import LightCapabilities, MappingResult, PublicationDecision, SwitchCapabilities
from sync.command import CommandSynchronizer, CommandTranslation
from sync.readback import CHANNEL_STATE, STATE_KEYS, has_reliable_channel
from sync.state import StateSynchronizer

_GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden_corpus" / "sync_payload.json"
_SECRET = "s"

# Secondaires SWITCH_* du corpus doré : eq -> (principal, [secondaires]).
CORPUS = {583: (5987, [6009, 6010]), 628: (5977, [5980, 5983, 6004])}
SECONDARY_CASES = [(eq, state) for eq, (_p, states) in CORPUS.items() for state in states]

# Équipements synthétiques ajoutés à la synchro (AC4, AC5).
VALVES = 17000      # deux vannes : la seconde est secondaire
LOCKED = 17100      # prise (principal) + serrure (secondaire)
FAN_ONLY = 17200    # trio FAN_* seul (principal)
MIXED_FAN = 17300   # trio SWITCH_* (principal) + trio FAN_* (secondaire)


def _cmd(cmd_id, generic_type, type_="action", sub_type="other", value=None, name=None, link=None):
    cmd = {"id": cmd_id, "name": name or f"Cmd {cmd_id}", "type": type_, "sub_type": sub_type,
           "generic_type": generic_type}
    if value is not None:
        cmd["current_value"] = value
    if link is not None:
        cmd["linked_value"] = link
    return cmd


def _eq(eq_id, cmds):
    return {"id": eq_id, "name": f"Equipement {eq_id}", "object_id": 1, "is_enable": True,
            "is_visible": True, "is_excluded": False, "eq_type": "virtual", "generic_type": None,
            "status": {"timeout": 0}, "cmds": cmds}


def _synthetic_eqs():
    return [
        _eq(VALVES, [
            _cmd(170001, "IRRIG_STATE", "info", "binary", "0", name="Zone A"),
            _cmd(170002, "IRRIG_ON", link=170001, name="Zone A on"),
            _cmd(170003, "IRRIG_OFF", link=170001, name="Zone A off"),
            _cmd(170004, "IRRIG_STATE", "info", "binary", "1", name="Zone B"),
            _cmd(170005, "IRRIG_ON", link=170004, name="Zone B on"),
            _cmd(170006, "IRRIG_OFF", link=170004, name="Zone B off"),
        ]),
        _eq(LOCKED, [
            _cmd(171001, "ENERGY_STATE", "info", "binary", "1", name="Etat prise"),
            _cmd(171002, "ENERGY_ON", name="On prise"),
            _cmd(171003, "ENERGY_OFF", name="Off prise"),
            _cmd(171004, "LOCK_STATE", "info", "binary", "1", name="Etat serrure"),
            _cmd(171005, "LOCK_OPEN", name="Ouvrir"),
            _cmd(171006, "LOCK_CLOSE", name="Fermer"),
        ]),
        _eq(FAN_ONLY, [
            _cmd(172001, "FAN_STATE", "info", "binary", "1", name="Marche"),
            _cmd(172002, "FAN_ON", name="Marche on"),
            _cmd(172003, "FAN_OFF", name="Marche off"),
        ]),
        _eq(MIXED_FAN, [
            _cmd(173001, "SWITCH_STATE", "info", "binary", "0", name="Sortie"),
            _cmd(173002, "SWITCH_ON", name="Sortie on"),
            _cmd(173003, "SWITCH_OFF", name="Sortie off"),
            _cmd(173004, "FAN_STATE", "info", "binary", "1", name="Brassage"),
            _cmd(173005, "FAN_ON", name="Brassage on"),
            _cmd(173006, "FAN_OFF", name="Brassage off"),
        ]),
    ]


def _payload(*, synthetic=False, excluded=()):
    payload = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    if synthetic:
        payload["eq_logics"].extend(_synthetic_eqs())
    if excluded:
        payload["published_scope"]["equipements"] = {
            str(eq_id): {"raw_state": "exclude", "source": "equipement"} for eq_id in excluded}
    return payload


class _Bridge:
    def __init__(self):
        self.is_connected = True
        self.published = []

    def publish_message(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return True


async def _post_sync(cli, payload, request_id="r"):
    body = {"action": "sync", "payload": payload, "request_id": request_id,
            "timestamp": "2026-11-13T00:00:00Z"}
    resp = await cli.post("/action/sync", json=body, headers={"X-Local-Secret": _SECRET})
    assert resp.status == 200, await resp.text()


async def _synced(aiohttp_client, tmp_path, *, with_state_sync=True, synthetic=False):
    """Vraie synchro : les décisions (principal ET secondaires) viennent du pipeline réel."""
    app = http_server.create_app(local_secret=_SECRET)
    app["data_dir"] = str(tmp_path)
    bridge = _Bridge()
    app["mqtt_bridge"] = bridge
    if with_state_sync:
        app["state_synchronizer"] = StateSynchronizer(app, bridge)
    cli = await aiohttp_client(app)
    await _post_sync(cli, _payload(synthetic=synthetic))
    return cli, app, bridge


async def _publier(cli, eq_id):
    body = {"intention": "publier", "portee": "equipement", "selection": [eq_id]}
    with patch("transport.http_server.asyncio.sleep", new=AsyncMock()):
        resp = await cli.post("/action/execute", json=body, headers={"X-Local-Secret": _SECRET})
    assert resp.status == 200, await resp.text()


def _cmd_sync(app):
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    sync = CommandSynchronizer(app=app, mqtt_bridge=bridge,
                               jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
                               jeedom_core_apikey="core-apikey")
    sync._execute_exec_cmd = AsyncMock(return_value=True)
    return sync, bridge


def _candidate(app, eq_id, state_cmd_id):
    """Le mapping (principal ou secondaire) dont l'entité est indexée par ``state_cmd_id``."""
    primary = app["publications"][eq_id].mapping_result
    for candidate in [primary, *(primary.additional_mappings or [])]:
        if (candidate.reason_details or {}).get("cmd_id") == state_cmd_id:
            return primary, candidate
    raise AssertionError(f"aucune entité {state_cmd_id} sur l'équipement {eq_id}")


def _decision_of(app, eq_id, candidate):
    primary = app["publications"][eq_id].mapping_result
    return app["publications"][eq_id] if candidate is primary else candidate.publication_decision_ref


def _policies(caplog):
    return [r.getMessage() for r in caplog.records
            if "action=select_confirmation_policy" in r.getMessage()]


async def _order(app, topic, payload, caplog):
    sync, cmd_bridge = _cmd_sync(app)
    caplog.clear()
    with caplog.at_level(logging.INFO):
        handled = await sync.handle_command_message(topic, payload)
    return handled, sync, cmd_bridge


def _assert_confirmed(handled, sync, cmd_bridge, caplog):
    assert handled is True
    sync._execute_exec_cmd.assert_awaited_once()
    policies = _policies(caplog)
    assert len(policies) == 1
    assert "reason_code=real_state_confirmation" in policies[0]
    assert "missing_state_topic_runtime" not in caplog.text
    assert "optimistic_controlled" not in caplog.text
    cmd_bridge.publish_message.assert_not_called()


# --- T1 / AC1 : forme de production -----------------------------------------------------------

@pytest.mark.asyncio
async def test_t1_production_shape_order_on_secondary_6009_is_confirmed(aiohttp_client, tmp_path, caplog):
    """T1 (rouge avant correctif) : ordre sur jeedom2ha/583/6009/set après une vraie synchro."""
    _cli, app, _bridge = await _synced(aiohttp_client, tmp_path)
    handled, sync, cmd_bridge = await _order(app, "jeedom2ha/583/6009/set", "ON", caplog)
    _assert_confirmed(handled, sync, cmd_bridge, caplog)


@pytest.mark.asyncio
@pytest.mark.parametrize("eq_id,state_cmd_id", SECONDARY_CASES)
async def test_ac1_on_then_off_on_each_corpus_secondary_is_confirmed(
        aiohttp_client, tmp_path, caplog, eq_id, state_cmd_id):
    _cli, app, _bridge = await _synced(aiohttp_client, tmp_path)
    _primary, secondary = _candidate(app, eq_id, state_cmd_id)
    topic = f"jeedom2ha/{eq_id}/{state_cmd_id}/set"
    for payload, key in (("ON", "SWITCH_ON"), ("OFF", "SWITCH_OFF")):
        handled, sync, cmd_bridge = await _order(app, topic, payload, caplog)
        _assert_confirmed(handled, sync, cmd_bridge, caplog)
        sync._execute_exec_cmd.assert_awaited_once_with(secondary.commands[key].id, {})


@pytest.mark.asyncio
@pytest.mark.parametrize("eq_id,state_cmd_id", SECONDARY_CASES)
async def test_ac1_secondary_state_is_streamed_on_its_own_topic(
        aiohttp_client, tmp_path, eq_id, state_cmd_id):
    _cli, app, bridge = await _synced(aiohttp_client, tmp_path)
    bridge.published.clear()
    assert await app["state_synchronizer"].handle_state_message(eq_id, state_cmd_id, "1") is True
    assert bridge.published == [(f"jeedom2ha/{eq_id}/{state_cmd_id}/state", "ON", 1, True)]


# --- AC2 : topic propre seulement -------------------------------------------------------------

@pytest.mark.asyncio
async def test_ac2_secondary_decisions_carry_their_own_topic_or_nothing(aiohttp_client, tmp_path):
    _cli, app, _bridge = await _synced(aiohttp_client, tmp_path, synthetic=True)
    seen_switch = 0
    for eq_id, decision in app["publications"].items():
        primary = decision.mapping_result
        for secondary in (primary.additional_mappings if primary else None) or []:
            ref = secondary.publication_decision_ref
            assert ref is not None
            own = (secondary.reason_details or {}).get("state_topic")
            assert ref.state_topic != f"jeedom2ha/{eq_id}/state"
            if secondary.ha_entity_type in ("switch", "valve", "lock"):
                assert ref.state_topic == own
                assert ref.state_topic.startswith(f"jeedom2ha/{eq_id}/")
                seen_switch += secondary.ha_entity_type == "switch"
            else:
                assert not ref.state_topic
    # 5 SWITCH_* du corpus + le verrou de thermostat + le trio FAN_* synthétique.
    assert seen_switch >= 7
    for eq_id, state_cmd_id in SECONDARY_CASES:
        _primary, secondary = _candidate(app, eq_id, state_cmd_id)
        assert secondary.publication_decision_ref.state_topic == \
            f"jeedom2ha/{eq_id}/{state_cmd_id}/state"


def test_ac2_types_without_own_topic_never_get_the_fallback():
    light = MappingResult(
        ha_entity_type="light", confidence="sure", reason_code="override", jeedom_eq_id=18000,
        ha_unique_id="u", ha_name="n", commands={}, capabilities=LightCapabilities(),
        reason_details={"cmd_id": 1},
    )
    # Le repli de _resolve_state_topic désigne le topic du principal : interdit sur un secondaire.
    assert http_server._resolve_state_topic(light) == "jeedom2ha/18000/state"
    assert http_server._secondary_own_state_topic(light) == ""
    decision = http_server._reset_secondary_runtime_state(light, discovery_published=False)
    assert decision.state_topic == ""
    # Même un topic propre déclaré n'est retenu que pour switch / valve / lock.
    light.reason_details["state_topic"] = "jeedom2ha/18000/1/state"
    assert http_server._secondary_own_state_topic(light) == ""


# --- AC3 : tous les chemins -------------------------------------------------------------------

def _corpus_topics(app):
    return {(eq, cmd): _candidate(app, eq, cmd)[1].publication_decision_ref.state_topic
            for eq, cmd in SECONDARY_CASES}


@pytest.mark.asyncio
async def test_ac3_publier_keeps_the_own_topic_and_the_policy(aiohttp_client, tmp_path, caplog):
    cli, app, _bridge = await _synced(aiohttp_client, tmp_path)
    before = _corpus_topics(app)
    await _publier(cli, 583)
    await _publier(cli, 628)
    assert _corpus_topics(app) == before
    handled, sync, cmd_bridge = await _order(app, "jeedom2ha/628/6004/set", "OFF", caplog)
    _assert_confirmed(handled, sync, cmd_bridge, caplog)


@pytest.mark.asyncio
async def test_ac3_second_sync_without_change_is_stable(aiohttp_client, tmp_path, caplog):
    cli, app, _bridge = await _synced(aiohttp_client, tmp_path)
    before = _corpus_topics(app)
    await _post_sync(cli, _payload(), request_id="r2")  # « Relire Jeedom » = même synchro
    assert _corpus_topics(app) == before
    handled, sync, cmd_bridge = await _order(app, "jeedom2ha/583/6010/set", "ON", caplog)
    _assert_confirmed(handled, sync, cmd_bridge, caplog)


@pytest.mark.asyncio
async def test_ac3_scope_exclusion_then_reinclusion(aiohttp_client, tmp_path, caplog):
    cli, app, _bridge = await _synced(aiohttp_client, tmp_path)
    before = _corpus_topics(app)
    await _post_sync(cli, _payload(excluded=(583,)), request_id="excl")
    assert app["publications"][583].reason == "excluded"
    _primary, secondary = _candidate(app, 583, 6009)
    ref = secondary.publication_decision_ref
    assert ref.state_topic == "jeedom2ha/583/6009/state"
    assert ref.discovery_published is False and ref.active_or_alive is False
    # Exclu : aucun ordre routé.
    handled, sync, _cmd_bridge = await _order(app, "jeedom2ha/583/6009/set", "ON", caplog)
    assert handled is False
    sync._execute_exec_cmd.assert_not_awaited()

    await _post_sync(cli, _payload(), request_id="incl")
    assert _corpus_topics(app) == before
    handled, sync, cmd_bridge = await _order(app, "jeedom2ha/583/6009/set", "ON", caplog)
    _assert_confirmed(handled, sync, cmd_bridge, caplog)


@pytest.mark.asyncio
async def test_ac3_supprimer_then_publier(aiohttp_client, tmp_path, caplog):
    cli, app, _bridge = await _synced(aiohttp_client, tmp_path)
    body = {"intention": "supprimer", "portee": "equipement", "selection": [628]}
    with patch("transport.http_server.asyncio.sleep", new=AsyncMock()):
        resp = await cli.post("/action/execute", json=body, headers={"X-Local-Secret": _SECRET})
    assert resp.status == 200, await resp.text()
    _primary, secondary = _candidate(app, 628, 5983)
    assert secondary.publication_decision_ref.state_topic == "jeedom2ha/628/5983/state"
    assert secondary.publication_decision_ref.discovery_published is False
    await _publier(cli, 628)
    handled, sync, cmd_bridge = await _order(app, "jeedom2ha/628/5983/set", "ON", caplog)
    _assert_confirmed(handled, sync, cmd_bridge, caplog)


def test_ac3_copied_decision_receives_the_own_topic():
    """Décision recopiée (``dataclasses.replace``) d'une décision sans topic : le topic propre est posé."""
    secondary = MappingResult(
        ha_entity_type="switch", confidence="probable", reason_code="switch_switch_on_off_state",
        jeedom_eq_id=18100, ha_unique_id="u", ha_name="n", commands={},
        capabilities=SwitchCapabilities(has_on_off=True, has_state=True),
        reason_details={"cmd_id": 2, "state_topic": "jeedom2ha/18100/2/state"},
    )
    secondary.publication_decision_ref = PublicationDecision(
        should_publish=True, reason="probable", mapping_result=secondary)
    decision = http_server._reset_secondary_runtime_state(secondary, discovery_published=True,
                                                          active_or_alive=True)
    assert decision.state_topic == "jeedom2ha/18100/2/state"
    assert decision.should_publish is True and decision.reason == "probable"
    # Jamais synchronisé : décision neuve refusée, avec le topic propre.
    secondary.publication_decision_ref = None
    fresh = http_server._reset_secondary_runtime_state(secondary, discovery_published=False)
    assert fresh.state_topic == "jeedom2ha/18100/2/state" and fresh.should_publish is False


# --- AC4 : valve et lock secondaires ----------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("with_state_sync,expected", [(True, "real_state_confirmation"),
                                                       (False, "stateless")])
async def test_ac4_secondary_valve_and_lock(aiohttp_client, tmp_path, caplog, with_state_sync, expected):
    _cli, app, _bridge = await _synced(aiohttp_client, tmp_path, with_state_sync=with_state_sync,
                                       synthetic=True)
    valves, valve = _candidate(app, VALVES, 170004)
    assert valves.ha_entity_type == "valve" and valve.ha_entity_type == "valve" and valve is not valves
    locked, lock = _candidate(app, LOCKED, 171004)
    assert locked.ha_entity_type == "switch" and lock.ha_entity_type == "lock"
    for topic, payload in ((f"jeedom2ha/{VALVES}/170004/set", "OPEN"),
                           (f"jeedom2ha/{VALVES}/170004/set", "CLOSE"),
                           (f"jeedom2ha/{LOCKED}/171004/set", "LOCK"),
                           (f"jeedom2ha/{LOCKED}/171004/set", "UNLOCK")):
        handled, sync, cmd_bridge = await _order(app, topic, payload, caplog)
        assert handled is True, caplog.text
        policies = _policies(caplog)
        assert len(policies) == 1 and f"reason_code={expected}" in policies[0]
        assert "optimistic_controlled" not in caplog.text
        assert "missing_state_topic_runtime" not in caplog.text
        cmd_bridge.publish_message.assert_not_called()


@pytest.mark.asyncio
async def test_ac4_secondary_valve_without_state_info_is_stateless(aiohttp_client, tmp_path):
    _cli, app, _bridge = await _synced(aiohttp_client, tmp_path, synthetic=True)
    _valves, valve = _candidate(app, VALVES, 170004)
    bare = copy.copy(valve)
    bare.commands = {k: v for k, v in valve.commands.items() if k != "IRRIG_STATE"}
    sync, _cmd_bridge = _cmd_sync(app)
    translation = CommandTranslation(cmd_id=170005, options={}, command_family="valve_open_close")
    assert sync._select_confirmation_policy(bare, valve.publication_decision_ref,
                                            translation) == "stateless"


# --- AC5 : trio FAN_* (D2-a) ------------------------------------------------------------------

def test_ac5_fan_state_is_a_reliable_switch_channel():
    assert "FAN_STATE" in STATE_KEYS["switch"]
    # Les clés antérieures restent, dans le même ordre.
    assert STATE_KEYS["switch"][:4] == ("ENERGY_STATE", "SWITCH_STATE", "PRESENCE", "THERMOSTAT_LOCK")


@pytest.mark.asyncio
@pytest.mark.parametrize("eq_id,state_cmd_id,secondary", [(FAN_ONLY, 172001, False),
                                                          (MIXED_FAN, 173004, True)])
async def test_ac5_fan_trio_primary_and_secondary_are_confirmed(
        aiohttp_client, tmp_path, caplog, eq_id, state_cmd_id, secondary):
    _cli, app, _bridge = await _synced(aiohttp_client, tmp_path, synthetic=True)
    primary, fan = _candidate(app, eq_id, state_cmd_id)
    assert fan.ha_entity_type == "switch" and "FAN_STATE" in fan.commands
    assert (fan is not primary) is secondary
    assert has_reliable_channel("switch", fan, CHANNEL_STATE) is True
    for payload in ("ON", "OFF"):
        handled, sync, cmd_bridge = await _order(app, f"jeedom2ha/{eq_id}/{state_cmd_id}/set",
                                                 payload, caplog)
        _assert_confirmed(handled, sync, cmd_bridge, caplog)


@pytest.mark.asyncio
async def test_ac5_fan_trio_state_is_streamed_on_its_own_topic(aiohttp_client, tmp_path):
    _cli, app, bridge = await _synced(aiohttp_client, tmp_path, synthetic=True)
    # État initial publié à la synchro (FAN_STATE est désormais la clé de relecture du trio).
    assert (f"jeedom2ha/{MIXED_FAN}/173004/state", "ON", 1, True) in bridge.published
    assert (f"jeedom2ha/{FAN_ONLY}/172001/state", "ON", 1, True) in bridge.published
    bridge.published.clear()
    assert await app["state_synchronizer"].handle_state_message(MIXED_FAN, 173004, "0") is True
    assert bridge.published == [(f"jeedom2ha/{MIXED_FAN}/173004/state", "OFF", 1, True)]


# --- AC6 : secondaire sans état fiable --------------------------------------------------------

@pytest.mark.asyncio
async def test_ac6_secondary_without_reliable_state_publishes_on_its_own_topic_only(
        aiohttp_client, tmp_path, caplog):
    _cli, app, _bridge = await _synced(aiohttp_client, tmp_path)
    _primary, secondary = _candidate(app, 583, 6009)
    secondary.commands = {k: v for k, v in secondary.commands.items() if k != "SWITCH_STATE"}
    handled, sync, cmd_bridge = await _order(app, "jeedom2ha/583/6009/set", "ON", caplog)
    assert handled is True
    policies = _policies(caplog)
    assert len(policies) == 1 and "reason_code=optimistic_controlled" in policies[0]
    assert "missing_state_topic_runtime" not in caplog.text
    topics = [c.args[0] for c in cmd_bridge.publish_message.call_args_list]
    assert topics == ["jeedom2ha/583/6009/state"]
    assert "jeedom2ha/583/state" not in topics


def test_ac6_secondary_without_own_topic_publishes_nothing(caplog):
    light = MappingResult(
        ha_entity_type="light", confidence="sure", reason_code="override", jeedom_eq_id=18200,
        ha_unique_id="u", ha_name="n", commands={}, capabilities=LightCapabilities(),
        reason_details={"cmd_id": 1},
    )
    decision = http_server._reset_secondary_runtime_state(light, discovery_published=True,
                                                          active_or_alive=True)
    sync, bridge = _cmd_sync({"publications": {}})
    with caplog.at_level(logging.INFO):
        sync._publish_optimistic_state(18200, "jeedom2ha/18200/1/set", decision, "ON")
    bridge.publish_message.assert_not_called()
    assert "missing_state_topic_runtime" in caplog.text


@pytest.mark.asyncio
async def test_ac6_without_state_synchronizer_no_real_state_confirmation(aiohttp_client, tmp_path, caplog):
    _cli, app, _bridge = await _synced(aiohttp_client, tmp_path, with_state_sync=False)
    handled, _sync, cmd_bridge = await _order(app, "jeedom2ha/583/6009/set", "ON", caplog)
    assert handled is True
    assert "real_state_confirmation" not in caplog.text
    # Comme un principal du même type : état supposé sur le seul topic propre.
    topics = [c.args[0] for c in cmd_bridge.publish_message.call_args_list]
    assert topics == ["jeedom2ha/583/6009/state"]


# --- AC7 : rien d'autre ne change -------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("eq_id", sorted(CORPUS))
async def test_ac7_corpus_primaries_unchanged(aiohttp_client, tmp_path, caplog, eq_id):
    _cli, app, _bridge = await _synced(aiohttp_client, tmp_path)
    principal_state = CORPUS[eq_id][0]
    assert app["publications"][eq_id].state_topic == f"jeedom2ha/{eq_id}/{principal_state}/state"
    handled, sync, cmd_bridge = await _order(app, f"jeedom2ha/{eq_id}/{principal_state}/set",
                                             "ON", caplog)
    _assert_confirmed(handled, sync, cmd_bridge, caplog)


@pytest.mark.asyncio
async def test_ac7_thermostat_lock_still_confirmed(aiohttp_client, tmp_path, caplog):
    _cli, app, _bridge = await _synced(aiohttp_client, tmp_path)
    handled, sync, cmd_bridge = await _order(app, "jeedom2ha/11000/110009/set", "ON", caplog)
    _assert_confirmed(handled, sync, cmd_bridge, caplog)


@pytest.mark.asyncio
async def test_ac7_refused_secondary_under_published_principal_is_not_routed(
        aiohttp_client, tmp_path, caplog):
    """I11 : un secondaire refusé n'hérite jamais du routage de son principal."""
    _cli, app, _bridge = await _synced(aiohttp_client, tmp_path)
    _primary, secondary = _candidate(app, 583, 6009)
    secondary.publication_decision_ref = dataclasses.replace(
        secondary.publication_decision_ref, should_publish=False, reason="excluded")
    assert app["publications"][583].should_publish is True
    handled, sync, _cmd_bridge = await _order(app, "jeedom2ha/583/6009/set", "ON", caplog)
    assert handled is False
    sync._execute_exec_cmd.assert_not_awaited()


@pytest.mark.asyncio
async def test_ac7_discovery_of_secondaries_unchanged(aiohttp_client, tmp_path):
    """La discovery d'un switch secondaire déclare toujours son topic propre, sans ``optimistic``."""
    _cli, app, _bridge = await _synced(aiohttp_client, tmp_path)
    _primary, secondary = _candidate(app, 628, 5980)
    assert secondary.reason_details["state_topic"] == "jeedom2ha/628/5980/state"
    assert secondary.reason_details["command_topic"] == "jeedom2ha/628/5980/set"
    assert secondary.ha_unique_id == "jeedom2ha_eq_628_cmd_5980"
