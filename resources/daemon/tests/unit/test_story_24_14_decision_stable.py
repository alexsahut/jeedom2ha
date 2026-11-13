"""Story 24.14 — décision de publication stable entre deux synchros (démon).

Couvre AC1 (déterminisme), AC2-AC4 (D1 A : bouton de scénario stable, disponibilité propre,
appui refusé), AC5 (purge des seuls supprimés), AC7 (une seule raison, quel que soit le
chemin), AC8 (instantané et mémo indissociables) et AC9 (origine de la synchro).
Données synthétiques, identifiants numériques seulement (CC-48).
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
from itertools import product
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from discovery.publisher import DiscoveryPublisher
from mapping.button import ScenarioButtonMapper
from models.mapping import PublicationDecision
from models.topology import MULTI_SENSOR_EQ_TYPES, TopologySnapshot, assess_eligibility

SECRET = "secret-24-14"
H = {"X-Local-Secret": SECRET}
EXCLUSION_REASONS = {"excluded_eqlogic", "excluded_plugin", "excluded_object"}
# Alias historique : l'éligibilité dit `no_supported_generic_type`, le contrat de décision
# (export, états agrégés, trace) dit `no_generic_type_configured` (evaluate_equipment, chemin I1).
ALIAS = {"no_supported_generic_type": "no_generic_type_configured"}


def _bridge(retained=None):
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.state = "connected"
    bridge.published = []

    def _publish(topic, payload, qos=1, retain=False):
        bridge.published.append((topic, payload, qos, retain))
        return True

    bridge.publish_message.side_effect = _publish
    bridge.collect_retained_topics = AsyncMock(return_value=retained if retained is not None else [])
    return bridge


async def _client(aiohttp_client, bridge):
    from transport.http_server import create_app

    app = create_app(local_secret=SECRET)
    app["mqtt_bridge"] = bridge
    return app, await aiohttp_client(app)


def _cmd(cmd_id, generic_type=None, unit=None, sub_type="numeric", cmd_type="info"):
    return {
        "id": cmd_id, "name": f"C{cmd_id}", "generic_type": generic_type, "type": cmd_type,
        "sub_type": sub_type, "current_value": 1, "unit": unit, "is_visible": True,
        "is_historized": False,
    }


def _eq(eq_id, *, enable=True, cmds=None, exclusion=None, eq_type="virtual"):
    data = {
        "id": eq_id, "name": f"E{eq_id}", "object_id": None, "is_enable": enable,
        "is_visible": True, "eq_type": eq_type, "is_excluded": exclusion is not None,
        "status": {}, "cmds": cmds if cmds is not None else [],
    }
    if exclusion is not None:
        data["exclusion_source"] = exclusion
    return data


def _body(eq_logics=None, scenarios=None, complete=True):
    return {
        "action": "sync",
        "payload": {
            "objects": [], "eq_logics": eq_logics or [],
            "scenarios": scenarios or [], "scenarios_complete": complete,
        },
        "request_id": "t-24-14", "timestamp": "2026-11-12T00:00:00Z",
    }


async def _sync(cli, body, mode=None, expect=200):
    headers = dict(H)
    if mode is not None:
        headers["X-Jeedom2ha-Sync-Mode"] = mode
    resp = await cli.post("/action/sync", json=body, headers=headers)
    assert resp.status == expect
    return await resp.json()


async def _export(cli):
    resp = await cli.get("/system/decision_export", headers=H)
    assert resp.status == 200
    data = await resp.json()
    return data.get("payload", data)


def _strip_times(doc):
    doc = json.loads(json.dumps(doc))
    doc.pop("generated_at", None)
    doc.pop("sync_at", None)
    return doc


def _scenario_topic(sc_id):
    return f"homeassistant/button/jeedom2ha_scenario_{sc_id}/config"


def _scenario_avail(sc_id):
    return f"jeedom2ha/scenario_{sc_id}/availability"


# ---------------------------------------------------------------------------
# AC1 — déterminisme
# ---------------------------------------------------------------------------

def _mixed_body():
    return _body(
        eq_logics=[
            _eq(1, cmds=[_cmd(11, "LIGHT_STATE", sub_type="binary"), _cmd(12, "LIGHT_ON", sub_type="other", cmd_type="action"),
                         _cmd(13, "LIGHT_OFF", sub_type="other", cmd_type="action")]),
            _eq(2, enable=False, cmds=[_cmd(21, "TEMPERATURE")]),
            _eq(3, cmds=[_cmd(31)]),
            _eq(4, exclusion="plugin", cmds=[_cmd(41, "TEMPERATURE")]),
            _eq(5, cmds=[_cmd(51, "TEMPERATURE", unit="°C")]),
        ],
        scenarios=[{"id": 1, "name": "S1", "is_active": True}, {"id": 2, "name": "S2", "is_active": False}],
    )


async def test_ac1_same_payload_twice_gives_same_mqtt_and_same_export(aiohttp_client):
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge)

    await _sync(cli, _mixed_body())
    first_export = _strip_times(await _export(cli))
    bridge.published.clear()
    await _sync(cli, _mixed_body())
    second = list(bridge.published)
    second_export = _strip_times(await _export(cli))
    bridge.published.clear()
    await _sync(cli, _mixed_body())
    third = list(bridge.published)
    third_export = _strip_times(await _export(cli))

    # Mêmes topics et mêmes charges, au caractère près, dans le même ordre.
    assert second == third
    assert first_export == second_export == third_export
    # Aucun topic de configuration n'est vidé en régime établi.
    assert [t for (t, p, q, r) in third if p == "" and t.endswith("/config")] == []


# ---------------------------------------------------------------------------
# AC2 / AC3 — [D1 A] bouton stable, disponibilité propre au scénario
# ---------------------------------------------------------------------------

async def test_ac2_ac3_toggle_never_empties_config_and_only_changes_availability(aiohttp_client):
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge)
    configs, availability = [], []
    for active in (True, False, True):
        bridge.published.clear()
        await _sync(cli, _body(scenarios=[{"id": 30, "name": "S30", "is_active": active}]))
        assert (_scenario_topic(30), "", 1, True) not in bridge.published
        configs += [json.loads(p) for (t, p, q, r) in bridge.published if t == _scenario_topic(30)]
        availability += [(p, q, r) for (t, p, q, r) in bridge.published if t == _scenario_avail(30)]

    assert len(configs) == 3 and configs[0] == configs[1] == configs[2]
    assert configs[0]["unique_id"] == "jeedom2ha_scenario_30"
    assert configs[0]["default_entity_id"] == "button.jeedom2ha_scenario_30"
    assert configs[0]["command_topic"] == "jeedom2ha/scenario_30/cmd"
    # Publiée retenue (qos 1) à chaque synchro : online -> offline -> online.
    assert availability == [("online", 1, True), ("offline", 1, True), ("online", 1, True)]


def test_ac3_button_payload_has_two_availabilities_never_the_homonym_equipment():
    snapshot = TopologySnapshot.from_jeedom_payload({
        "objects": [],
        "eq_logics": [_eq(40, cmds=[_cmd(401, "TEMPERATURE")]) | {"status": {"timeout": 1}}],
        "scenarios": [{"id": 40, "name": "S40", "is_active": False}],
    })
    mapping = ScenarioButtonMapper().map(snapshot.scenarios[40])
    payload = DiscoveryPublisher(MagicMock())._build_button_payload(mapping, snapshot)

    assert payload["availability"] == [
        {"topic": "jeedom2ha/bridge/status"},
        {"topic": "jeedom2ha/scenario_40/availability"},
    ]
    assert payload["availability_mode"] == "all"
    assert payload["payload_available"] == "online" and payload["payload_not_available"] == "offline"
    assert "jeedom2ha/40/availability" not in json.dumps(payload)


# ---------------------------------------------------------------------------
# AC4 — [D1 A] appui refusé sur un scénario inactif, sans JSON-RPC
# ---------------------------------------------------------------------------

def _command_sync(decisions):
    from sync.command import CommandSynchronizer

    bridge = MagicMock()
    bridge.is_connected = True
    sync = CommandSynchronizer(
        app={"publications": {}, "scenario_publications": decisions},
        mqtt_bridge=bridge,
        jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
        jeedom_core_apikey="k",
    )
    session = MagicMock()
    session.closed = False
    sync._session = session
    return sync, session


def _decision(sc_id, active):
    return PublicationDecision(
        should_publish=True, reason="scenario_button",
        mapping_result=ScenarioButtonMapper().map(
            TopologySnapshot.from_jeedom_payload({"scenarios": [{"id": sc_id, "name": "S", "is_active": active}]})
            .scenarios[sc_id]
        ),
        active_or_alive=active,
    )


def test_ac4_press_on_inactive_scenario_is_refused_without_any_rpc(caplog):
    caplog.set_level(logging.INFO)
    sync, session = _command_sync({50: _decision(50, False)})

    result = asyncio.run(sync.handle_command_message("jeedom2ha/scenario_50/cmd", "PRESS"))

    assert result is False
    session.post.assert_not_called()
    records = [r for r in caplog.records if "[SYNC-CMD]" in r.getMessage()]
    assert records and all(r.levelno == logging.INFO for r in records)
    assert "reason_code=scenario_inactive" in records[-1].getMessage()


def test_ac4_press_on_active_scenario_still_runs_it():
    sync, _session = _command_sync({51: _decision(51, True)})
    with patch.object(sync, "_execute_scenario_start", new_callable=AsyncMock, return_value=True) as start:
        result = asyncio.run(sync.handle_command_message("jeedom2ha/scenario_51/cmd", "PRESS"))
    assert result is True
    start.assert_awaited_once_with(51)


# ---------------------------------------------------------------------------
# AC5 — la purge ne retire que les supprimés ; liste incomplète : rien
# ---------------------------------------------------------------------------

async def test_ac5_only_deleted_scenarios_are_removed(aiohttp_client):
    bridge = _bridge(retained=[_scenario_topic(60), _scenario_topic(61), _scenario_topic(62)])
    app, cli = await _client(aiohttp_client, bridge)

    await _sync(cli, _body(scenarios=[{"id": 60, "name": "S", "is_active": True},
                                      {"id": 61, "name": "S", "is_active": False}]))

    empties = sorted(t for (t, p, q, r) in bridge.published if p == "" and r is True)
    assert empties == sorted([_scenario_topic(62), _scenario_avail(62)])


async def test_ac5_incomplete_list_removes_nothing(aiohttp_client):
    bridge = _bridge(retained=[_scenario_topic(60), _scenario_topic(62)])
    app, cli = await _client(aiohttp_client, bridge)

    await _sync(cli, _body(scenarios=[{"id": 60, "name": "S", "is_active": False}], complete=False))

    assert [t for (t, p, q, r) in bridge.published if p == ""] == []
    bridge.collect_retained_topics.assert_not_awaited()


# ---------------------------------------------------------------------------
# AC6 — export des scénarios
# ---------------------------------------------------------------------------

async def test_ac6_export_every_readable_scenario_published(aiohttp_client):
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge)
    await _sync(cli, _body(scenarios=[{"id": 70, "name": "S", "is_active": True},
                                      {"id": 71, "name": "S", "is_active": False}]))
    rows = {row["scenario_id"]: row for row in (await _export(cli))["scenarios"]}

    for sc_id, active in ((70, True), (71, False)):
        assert rows[sc_id]["decision"] == "published"
        assert rows[sc_id]["reason"] == "scenario_button"
        assert rows[sc_id]["active"] is active
        assert rows[sc_id]["entity"]["discovery_published"] is True


# ---------------------------------------------------------------------------
# AC7 — une seule raison, quel que soit le chemin
# ---------------------------------------------------------------------------

_EXCLUSIONS = (None, "eqlogic", "plugin", "object")
_COMMANDS = {
    "none": [],
    "generic": [_cmd(0, "TEMPERATURE", unit="°C")],
    "untyped": [_cmd(0)],
    "reliable_unit": [_cmd(0, unit="W")],
}


def _expected_reason(exclusion, enable, commands):
    """Ordre documenté : Exclu > Désactivé > Sans commandes > Sans type générique."""
    if exclusion is not None:
        return f"excluded_{exclusion}"
    if not enable:
        return "disabled_eqlogic"
    if commands == "none":
        return "no_commands"
    if commands == "untyped":
        return "no_supported_generic_type"
    return None  # éligible


def _matrix():
    rows = []
    eq_id = 100
    for exclusion, enable, commands in product(_EXCLUSIONS, (True, False), _COMMANDS):
        eq_id += 1
        cmds = [dict(c, id=eq_id * 10 + i) for i, c in enumerate(_COMMANDS[commands])]
        rows.append((eq_id, _eq(eq_id, enable=enable, cmds=cmds, exclusion=exclusion),
                     _expected_reason(exclusion, enable, commands)))
    # eqType multi-capteurs : éligible sans type générique s'il porte une info numérique.
    eq_id += 1
    multi = next(iter(sorted(MULTI_SENSOR_EQ_TYPES)))
    rows.append((eq_id, _eq(eq_id, cmds=[_cmd(eq_id * 10)], eq_type=multi), None))
    eq_id += 1
    rows.append((eq_id, _eq(eq_id, enable=False, cmds=[_cmd(eq_id * 10)], eq_type=multi), "disabled_eqlogic"))
    return rows


async def test_ac7_same_reason_in_every_view(aiohttp_client):
    rows = _matrix()
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge)
    await _sync(cli, _body(eq_logics=[eq for _, eq, _ in rows]))

    export = {row["eq_id"]: row for row in (await _export(cli))["equipments"]}
    diag_resp = await cli.get("/system/diagnostics", headers=H)
    diag = {row["eq_id"]: row for row in (await diag_resp.json())["payload"]["equipments"]}
    states_resp = await cli.get("/system/equipment_states?refresh=1", headers=H)
    states = (await states_resp.json())["payload"]["equipments"]
    snapshot = app["topology"]
    memo = app["decision_memo"].equipments

    for eq_id, _eq_data, expected in rows:
        eligibility = assess_eligibility(snapshot.eq_logics[eq_id])
        if expected is None:
            assert eligibility.is_eligible, eq_id
            assert export[eq_id]["reason"] not in EXCLUSION_REASONS | {"disabled_eqlogic", "no_commands"}
            continue
        contract = ALIAS.get(expected, expected)
        assert eligibility.reason_code == expected, eq_id
        assert diag[eq_id]["reason_code"] == expected, eq_id
        # La trace de décision du diagnostic nomme la famille `excluded` pour toute exclusion
        # (vocabulaire de trace antérieur, inchangé) ; le `reason_code` du diagnostic porte la source.
        trace = diag[eq_id]["traceability"]["decision_trace"]["reason_code"]
        assert trace == ("excluded" if expected in EXCLUSION_REASONS else contract), eq_id
        assert export[eq_id]["reason"] == contract, eq_id
        assert memo[eq_id]["reason"] == contract, eq_id
        assert states[str(eq_id)]["equipment_decision"]["publication_reason"] == contract, eq_id


@pytest.mark.parametrize("origin", ["boot", "rescan", "service"])
async def test_ac7_ac9_toggle_between_two_syncs_reason_follows_whatever_the_trigger(aiohttp_client, origin):
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge)

    await _sync(cli, _body(eq_logics=[_eq(80, cmds=[_cmd(801)])]), mode=origin)
    first = await _export(cli)
    assert first["sync_origin"] == origin
    assert first["equipments"][0]["reason"] == "no_generic_type_configured"

    await _sync(cli, _body(eq_logics=[_eq(80, enable=False, cmds=[_cmd(801)])]), mode=origin)
    second = await _export(cli)
    assert second["sync_origin"] == origin
    assert second["equipments"][0]["enabled"] is False
    assert second["equipments"][0]["reason"] == "disabled_eqlogic"


async def test_ac9_unknown_or_missing_header_is_a_service_sync(aiohttp_client):
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge)
    await _sync(cli, _body(eq_logics=[_eq(81, cmds=[_cmd(811)])]))
    assert (await _export(cli))["sync_origin"] == "service"
    await _sync(cli, _body(eq_logics=[_eq(81, cmds=[_cmd(811)])]), mode="anything")
    assert (await _export(cli))["sync_origin"] == "service"


# ---------------------------------------------------------------------------
# AC8 — instantané et mémo indissociables
# ---------------------------------------------------------------------------

async def test_ac8_failed_sync_leaves_the_previous_snapshot_intact(aiohttp_client):
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge)
    good = _body(
        eq_logics=[_eq(90, cmds=[_cmd(901, "TEMPERATURE", unit="°C")]), _eq(91, cmds=[_cmd(911)])],
        scenarios=[{"id": 9, "name": "S", "is_active": True}],
    )
    await _sync(cli, good)
    before = {
        "topology": app["topology"],
        "eligibility": app["eligibility"],
        "mappings": dict(app["mappings"]),
        "publications": dict(app["publications"]),
        "scenario_publications": dict(app["scenario_publications"]),
        "memo": copy.deepcopy(app["decision_memo"].equipments),
        "sync_at": app["decision_memo"].sync_at,
    }
    export_before = _strip_times(await _export(cli))

    changed = _body(
        eq_logics=[_eq(90, enable=False, cmds=[_cmd(901, "TEMPERATURE", unit="°C")])],
        scenarios=[{"id": 9, "name": "S", "is_active": False}, {"id": 10, "name": "S", "is_active": True}],
    )
    with patch.object(DiscoveryPublisher, "purge_orphan_scenario_buttons",
                      new=AsyncMock(side_effect=RuntimeError("injected"))):
        await _sync(cli, changed, expect=500)

    assert app["topology"] is before["topology"]
    assert app["eligibility"] is before["eligibility"]
    assert dict(app["mappings"]) == before["mappings"]
    assert dict(app["publications"]) == before["publications"]
    assert dict(app["scenario_publications"]) == before["scenario_publications"]
    assert app["decision_memo"].equipments == before["memo"]
    assert app["decision_memo"].sync_at == before["sync_at"]
    assert _strip_times(await _export(cli)) == export_before


async def test_ac8_invariant_disabled_implies_exclusion_or_disabled_reason(aiohttp_client):
    rows = _matrix()
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge)
    await _sync(cli, _body(eq_logics=[eq for _, eq, _ in rows]))
    for row in (await _export(cli))["equipments"]:
        if row["enabled"] is False:
            assert row["reason"] in EXCLUSION_REASONS | {"disabled_eqlogic"}, row["eq_id"]


# ---------------------------------------------------------------------------
# Revue P2 — échec de publication d'une disponibilité de scénario, republication
# ---------------------------------------------------------------------------

def _failing_bridge(failing_topic):
    """Broker qui refuse la publication d'un seul topic (les autres réussissent)."""
    bridge = _bridge()

    def _publish(topic, payload, qos=1, retain=False):
        bridge.published.append((topic, payload, qos, retain))
        return topic != failing_topic

    bridge.publish_message.side_effect = _publish
    return bridge


async def test_p2_failed_scenario_availability_is_reported_as_incomplete(aiohttp_client):
    bridge = _failing_bridge(_scenario_avail(41))
    app, cli = await _client(aiohttp_client, bridge)
    scenarios = [{"id": 40, "name": "S40", "is_active": True}, {"id": 41, "name": "S41", "is_active": False}]

    data = await _sync(cli, _body(scenarios=scenarios), mode="service")

    # La synchro aboutit mais signale le manque : le cron ne mémorise pas son empreinte.
    assert data["status"] == "ok"
    assert data["scenario_availability_complete"] is False
    assert data["operation_result"] != "succes"

    # Nouvel essai (broker rétabli) : complet.
    bridge.publish_message.side_effect = lambda t, p, qos=1, retain=False: bridge.published.append((t, p, qos, retain)) or True
    data = await _sync(cli, _body(scenarios=scenarios), mode="service")
    assert data["scenario_availability_complete"] is True
    assert data["operation_result"] == "succes"


async def test_p2_failed_scenario_config_is_reported_as_incomplete(aiohttp_client):
    bridge = _failing_bridge(_scenario_topic(42))
    app, cli = await _client(aiohttp_client, bridge)
    data = await _sync(cli, _body(scenarios=[{"id": 42, "name": "S42", "is_active": True}]))
    assert data["scenario_availability_complete"] is False
    # Pas de disponibilité sans configuration publiée.
    assert [t for (t, p, q, r) in bridge.published if t == _scenario_avail(42)] == []


async def test_p2_broker_down_with_scenarios_is_incomplete_without_scenarios_complete(aiohttp_client):
    bridge = _bridge()
    bridge.is_connected = False
    app, cli = await _client(aiohttp_client, bridge)
    data = await _sync(cli, _body(scenarios=[{"id": 43, "name": "S43", "is_active": True}]))
    assert data["scenario_availability_complete"] is False
    data = await _sync(cli, _body(scenarios=[]))
    assert data["scenario_availability_complete"] is True


async def test_p2_reconnect_republishes_scenario_buttons_and_availability(aiohttp_client):
    from transport.http_server import _republish_all_from_cache

    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge)
    await _sync(cli, _body(
        eq_logics=[_eq(5, cmds=[_cmd(51, "TEMPERATURE", unit="°C")])],
        scenarios=[{"id": 44, "name": "S44", "is_active": True}, {"id": 45, "name": "S45", "is_active": False}],
    ))
    first_config = next(json.loads(p) for (t, p, q, r) in bridge.published if t == _scenario_topic(45))
    bridge.published.clear()

    with patch("transport.http_server.asyncio.sleep", new=AsyncMock()):
        await _republish_all_from_cache(app, "broker_reconnect")

    published = {(t, p) for (t, p, q, r) in bridge.published if r is True}
    assert (_scenario_avail(44), "online") in published
    assert (_scenario_avail(45), "offline") in published
    configs = [json.loads(p) for (t, p, q, r) in bridge.published if t == _scenario_topic(45)]
    assert configs == [first_config]
    # Jamais la disponibilité de l'équipement de même id, jamais un vidage.
    assert all(p != "" for (t, p, q, r) in bridge.published)
    assert "jeedom2ha/44/availability" not in {t for (t, p, q, r) in bridge.published}


# ---------------------------------------------------------------------------
# Revue P2 (2) — synchro partielle côté équipement, parc de scénarios seuls
# ---------------------------------------------------------------------------

async def test_p2_equipment_publish_failure_makes_the_sync_not_successful(aiohttp_client):
    bridge = _bridge()

    def _publish(topic, payload, qos=1, retain=False):
        bridge.published.append((topic, payload, qos, retain))
        return "/sensor/" not in topic  # la configuration de l'équipement est refusée

    bridge.publish_message.side_effect = _publish
    app, cli = await _client(aiohttp_client, bridge)
    data = await _sync(cli, _body(eq_logics=[_eq(5, cmds=[_cmd(51, "TEMPERATURE", unit="°C")])]), mode="service")
    # Le cron du plugin ne mémorise l'empreinte que sur `succes` : ici, nouvel essai au pas suivant.
    assert data["status"] == "ok"
    assert data["operation_result"] in ("partiel", "echec")
    assert data["scenario_availability_complete"] is True


async def test_p2_scenarios_only_park_is_republished(aiohttp_client):
    from transport.http_server import _republish_all_from_cache

    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge)
    await _sync(cli, _body(scenarios=[{"id": 46, "name": "S46", "is_active": False}]))
    assert not any(getattr(d, "discovery_published", False) for d in app["publications"].values())
    bridge.published.clear()

    with patch("transport.http_server.asyncio.sleep", new=AsyncMock()):
        await _republish_all_from_cache(app, "broker_reconnect")

    topics = [(t, p) for (t, p, q, r) in bridge.published]
    assert any(t == _scenario_topic(46) and p for (t, p) in topics)
    assert (_scenario_avail(46), "offline") in topics


async def test_p2_reconnect_callback_republishes_a_scenarios_only_park(aiohttp_client):
    bridge = _bridge()
    bridge.stop = AsyncMock()
    bridge.start = AsyncMock()
    bridge.broker_info = ""
    app, cli = await _client(aiohttp_client, bridge)
    await _sync(cli, _body(scenarios=[{"id": 47, "name": "S47", "is_active": True}]))
    resp = await cli.post("/action/mqtt_connect", json={"payload": {"host": "broker.test"}}, headers=H)
    assert resp.status == 200
    on_reconnect = bridge.start.call_args.kwargs["on_reconnect_cb"]
    bridge.published.clear()

    with patch("transport.http_server.asyncio.sleep", new=AsyncMock()):
        await on_reconnect()

    topics = [(t, p) for (t, p, q, r) in bridge.published]
    assert any(t == _scenario_topic(47) and p for (t, p) in topics)
    assert (_scenario_avail(47), "online") in topics
