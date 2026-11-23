"""Story 24.18 — synchro légère : seule l'activation d'un scénario publié a changé.

Action minimale du démon ``POST /action/scenario_activation`` : met à jour la disponibilité
retenue des seuls boutons concernés, exactement comme la synchro complète (AC7), refuse dans
le doute (``full_sync_required``, AC8), ne touche ni ``sync_at`` ni ``sync_origin`` (AC9).
Données synthétiques, identifiants numériques seulement (CC-48).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

SECRET = "secret-24-18"
H = {"X-Local-Secret": SECRET}


def _bridge():
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.state = "connected"
    bridge.published = []
    bridge.fail_topics = set()

    def _publish(topic, payload, qos=1, retain=False):
        if topic in bridge.fail_topics:
            return False
        bridge.published.append((topic, payload, qos, retain))
        return True

    bridge.publish_message.side_effect = _publish
    bridge.collect_retained_topics = AsyncMock(return_value=[])
    return bridge


async def _client(aiohttp_client, bridge, tmp_path):
    from transport.http_server import create_app

    app = create_app(local_secret=SECRET)
    app["mqtt_bridge"] = bridge
    app["data_dir"] = str(tmp_path)
    return app, await aiohttp_client(app)


def _cmd(cmd_id, generic_type, sub_type="numeric", cmd_type="info", unit=None):
    return {
        "id": cmd_id, "name": f"C{cmd_id}", "generic_type": generic_type, "type": cmd_type,
        "sub_type": sub_type, "current_value": 1, "unit": unit, "is_visible": True,
        "is_historized": False,
    }


def _scenarios(states, unpublished=()):
    rows = []
    for sc_id, active in states.items():
        row = {"id": sc_id, "name": f"S{sc_id}", "is_active": active}
        if unpublished:
            row["published"] = sc_id not in unpublished
        rows.append(row)
    return rows


def _body(states, unpublished=()):
    return {
        "action": "sync",
        "payload": {
            "objects": [],
            "eq_logics": [{
                "id": 5, "name": "E5", "object_id": None, "is_enable": True, "is_visible": True,
                "eq_type": "virtual", "is_excluded": False, "status": {},
                "cmds": [_cmd(51, "TEMPERATURE", unit="°C")],
            }],
            "scenarios": _scenarios(states, unpublished),
            "scenarios_complete": True,
        },
        "request_id": "t-24-18", "timestamp": "2026-11-23T00:00:00Z",
    }


def _light(states):
    return {
        "action": "scenario_activation",
        "payload": {"scenarios": [{"id": k, "is_active": v} for k, v in states.items()]},
        "request_id": "t-24-18-light", "timestamp": "2026-11-23T00:00:00Z",
    }


async def _sync(cli, body, mode="service"):
    resp = await cli.post("/action/sync", json=body, headers=dict(H, **{"X-Jeedom2ha-Sync-Mode": mode}))
    assert resp.status == 200
    return await resp.json()


async def _post_light(cli, states, expect=200, headers=None):
    resp = await cli.post("/action/scenario_activation", json=_light(states), headers=H if headers is None else headers)
    assert resp.status == expect
    return await resp.json()


async def _export(cli):
    resp = await cli.get("/system/decision_export", headers=H)
    assert resp.status == 200
    data = await resp.json()
    return data.get("payload", data)


def _avail(sc_id):
    return f"jeedom2ha/scenario_{sc_id}/availability"


def _scenario_messages(published, sc_id):
    return [m for m in published if f"scenario_{sc_id}" in m[0]]


def _scenario_row(export, sc_id):
    return next(r for r in export["scenarios"] if r["scenario_id"] == sc_id)


# ---------------------------------------------------------------------------
# AC7 / AC9 — seule l'activation change : même effet dans HA que la synchro complète
# ---------------------------------------------------------------------------

async def test_light_publishes_only_the_availability_of_the_toggled_scenario(aiohttp_client, tmp_path):
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True, 2: False}), mode="boot")
    before = await _export(cli)
    bridge.published.clear()

    data = await _post_light(cli, {1: False, 2: False})

    assert data["status"] == "ok" and data["result"] == "applied" and data["scenario_ids"] == [1]
    assert bridge.published == [(_avail(1), "offline", 1, True)]
    assert app["scenario_publications"][1].active_or_alive is False
    assert app["topology"].scenarios[1].is_active is False
    after = await _export(cli)
    assert after["sync_at"] == before["sync_at"]
    assert after["sync_origin"] == "boot"
    assert after["scenario_activation_at"]
    assert _scenario_row(after, 1)["active"] is False
    assert _scenario_row(after, 1)["decision"] == "published"
    assert _scenario_row(after, 2) == _scenario_row(before, 2)


async def test_light_and_full_sync_give_the_same_messages_for_the_scenario(aiohttp_client, tmp_path):
    """AC7 — les messages du scénario basculé sont ceux qu'une synchro complète publierait."""
    bridge_full = _bridge()
    _app_full, cli_full = await _client(aiohttp_client, bridge_full, tmp_path / "full")
    await _sync(cli_full, _body({1: True, 2: False}))
    bridge_full.published.clear()
    await _sync(cli_full, _body({1: False, 2: True}))
    full_avail = {m for m in bridge_full.published if m[0] in (_avail(1), _avail(2))}

    bridge_light = _bridge()
    app_light, cli_light = await _client(aiohttp_client, bridge_light, tmp_path / "light")
    await _sync(cli_light, _body({1: True, 2: False}))
    config_before = [m for m in bridge_light.published if m[0].endswith("/config") and "scenario_1" in m[0]]
    bridge_light.published.clear()
    await _post_light(cli_light, {1: False, 2: True})

    assert set(bridge_light.published) == full_avail
    # La configuration du bouton n'est pas republiée : la synchro complète la republierait à l'identique.
    config_full = [m for m in bridge_full.published if m[0].endswith("/config") and "scenario_1" in m[0]]
    assert config_full == config_before
    # Mémoire identique à celle de la synchro complète pour les scénarios.
    full_dec = _app_full["scenario_publications"]
    for sc_id in (1, 2):
        assert app_light["scenario_publications"][sc_id].active_or_alive == full_dec[sc_id].active_or_alive
        assert app_light["topology"].scenarios[sc_id].is_active == _app_full["topology"].scenarios[sc_id].is_active


def _strip_export(doc):
    doc = dict(doc)
    for key in ("generated_at", "sync_at", "sync_origin", "scenario_activation_at"):
        doc.pop(key, None)
    return doc


async def test_light_equals_full_sync_on_export_and_status_rows(aiohttp_client, tmp_path):
    """Revue 24.18 (M5) — équivalence stricte avec la synchro complète : messages MQTT, export (hors horodatages et
    origine) et lignes de statut des scénarios, publiés et non publiés compris."""
    from transport.http_server import _scenario_status_rows

    start = {1: True, 2: False, 3: True}
    end = {1: False, 2: True, 3: False}
    unpublished = (3,)

    bridge_full = _bridge()
    app_full, cli_full = await _client(aiohttp_client, bridge_full, tmp_path / "full")
    await _sync(cli_full, _body(start, unpublished))
    bridge_full.published.clear()
    await _sync(cli_full, _body(end, unpublished))
    full_scenario_msgs = {m for m in bridge_full.published if "scenario_" in m[0] and m[0].endswith("/availability")}

    bridge_light = _bridge()
    app_light, cli_light = await _client(aiohttp_client, bridge_light, tmp_path / "light")
    await _sync(cli_light, _body(start, unpublished))
    bridge_light.published.clear()
    data = await _post_light(cli_light, end)

    assert data["result"] == "applied" and data["scenario_ids"] == [1, 2, 3]
    assert set(bridge_light.published) == full_scenario_msgs
    assert not [m for m in bridge_light.published if "scenario_3" in m[0]]
    assert _strip_export(await _export(cli_light)) == _strip_export(await _export(cli_full))
    assert _scenario_status_rows(app_light) == _scenario_status_rows(app_full)


async def test_light_rewrites_export_file_and_invalidates_states_cache(aiohttp_client, tmp_path):
    """Revue 24.18 (M1) — le fichier d'export est réécrit et le cache des états agrégés invalidé."""
    import json

    from export.decision_export import EXPORT_FILENAME
    from transport.http_server import _EQUIPMENT_STATES_CACHE_KEY

    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True}))
    generation = app[_EQUIPMENT_STATES_CACHE_KEY].get("generation", 0)
    await _post_light(cli, {1: False})
    with open(tmp_path / EXPORT_FILENAME, encoding="utf-8") as handle:
        document = json.load(handle)
    row = next(r for r in document["scenarios"] if r["scenario_id"] == 1)
    assert row["active"] is False
    assert document["scenario_activation_at"]
    assert app[_EQUIPMENT_STATES_CACHE_KEY].get("generation", 0) > generation


async def test_unchanged_states_publish_nothing(aiohttp_client, tmp_path):
    bridge = _bridge()
    _app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True, 2: False}))
    before = await _export(cli)
    bridge.published.clear()

    data = await _post_light(cli, {1: True, 2: False})

    assert data["status"] == "ok" and data["result"] == "unchanged"
    assert bridge.published == []
    assert (await _export(cli)).get("scenario_activation_at") == before.get("scenario_activation_at")


async def test_full_sync_resets_scenario_activation_at(aiohttp_client, tmp_path):
    bridge = _bridge()
    _app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True}))
    await _post_light(cli, {1: False})
    assert (await _export(cli))["scenario_activation_at"]
    await _sync(cli, _body({1: False}))
    assert (await _export(cli))["scenario_activation_at"] is None


async def test_republication_after_light_uses_the_new_activation(aiohttp_client, tmp_path, monkeypatch):
    """Naissance de HA / reconnexion : la disponibilité republiée suit le chemin léger."""
    from discovery.publisher import DiscoveryPublisher
    from discovery.registry import PublisherRegistry
    import transport.http_server as server
    from transport.http_server import _republish_scenarios_from_cache

    monkeypatch.setattr(server.asyncio, "sleep", AsyncMock())  # lissage de la republication sans attente réelle

    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True}))
    await _post_light(cli, {1: False})
    bridge.published.clear()
    registry = PublisherRegistry(DiscoveryPublisher(bridge))
    await _republish_scenarios_from_cache(app, registry, bridge, app["topology"], "test")
    assert (_avail(1), "offline", 1, True) in bridge.published


async def test_press_on_scenario_deactivated_by_light_is_refused(aiohttp_client, tmp_path):
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True}))
    await _post_light(cli, {1: False})
    decision = app["scenario_publications"][1]
    assert decision.should_publish is True and decision.active_or_alive is False


# ---------------------------------------------------------------------------
# AC8 — refus « dans le doute » : rien n'est écrit
# ---------------------------------------------------------------------------

async def _assert_refused(cli, app, bridge, states, reason):
    snapshot_states = {k: v.is_active for k, v in app["topology"].scenarios.items()} if app.get("topology") else None
    bridge.published.clear()
    data = await _post_light(cli, states)
    assert data["status"] == "error" and data["code"] == "full_sync_required"
    assert data["reason"] == reason
    assert bridge.published == []
    if snapshot_states is not None:
        assert {k: v.is_active for k, v in app["topology"].scenarios.items()} == snapshot_states


async def test_refused_without_previous_full_sync(aiohttp_client, tmp_path):
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _assert_refused(cli, app, bridge, {1: False}, "no_previous_sync")


async def test_refused_when_scenario_set_differs(aiohttp_client, tmp_path):
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True, 2: True}))
    await _assert_refused(cli, app, bridge, {1: False}, "scenario_set_mismatch")
    await _assert_refused(cli, app, bridge, {1: False, 2: True, 3: True}, "scenario_set_mismatch")


async def test_unpublished_scenario_updates_status_without_any_mqtt(aiohttp_client, tmp_path):
    """Revue 24.18 (I1, option A) : un scénario non publié qui bascule met à jour l'instantané (écran des scénarios,
    export) comme la synchro complète, sans aucun message MQTT et sans synchro complète."""
    from transport.http_server import _scenario_status_rows

    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True, 2: True}, unpublished=(2,)))
    before = await _export(cli)
    bridge.published.clear()

    data = await _post_light(cli, {1: True, 2: False})

    assert data["status"] == "ok" and data["result"] == "applied" and data["scenario_ids"] == [2]
    assert bridge.published == []
    row = next(r for r in _scenario_status_rows(app) if r["id"] == 2)
    assert row["is_active"] is False and row["published"] is False and row["in_ha"] is False
    assert app["scenario_publications"][2].active_or_alive is False
    after = await _export(cli)
    assert _scenario_row(after, 2)["active"] is False
    assert _scenario_row(after, 2)["decision"] == "not_published"
    assert after["sync_at"] == before["sync_at"]


async def test_unpublished_scenario_needs_no_broker(aiohttp_client, tmp_path):
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True, 2: True}, unpublished=(2,)))
    bridge.is_connected = False
    data = await _post_light(cli, {1: True, 2: False})
    assert data["result"] == "applied" and app["topology"].scenarios[2].is_active is False


async def test_refused_when_only_published_scenarios_are_sent(aiohttp_client, tmp_path):
    """L'ensemble reçu doit être celui de tous les scénarios lisibles, publiés ou non."""
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True, 2: True}, unpublished=(2,)))
    await _assert_refused(cli, app, bridge, {1: False}, "scenario_set_mismatch")


async def test_refused_while_a_withdrawal_is_pending(aiohttp_client, tmp_path):
    """Retrait d'un non publié non confirmé (`scenario_not_selected_pending`) : synchro complète."""
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True, 2: True}, unpublished=(2,)))
    app["scenario_publications"][2].reason = "scenario_not_selected_pending"
    await _assert_refused(cli, app, bridge, {1: True, 2: False}, "scenario_not_confirmed")


def test_scenario_list_is_capped():
    from transport.http_server import SCENARIO_ACTIVATION_MAX_SCENARIOS, _parse_scenario_activation_states

    rows = [{"id": i, "is_active": True} for i in range(1, SCENARIO_ACTIVATION_MAX_SCENARIOS + 1)]
    assert _parse_scenario_activation_states({"payload": {"scenarios": rows}}) is not None
    rows.append({"id": SCENARIO_ACTIVATION_MAX_SCENARIOS + 1, "is_active": True})
    assert _parse_scenario_activation_states({"payload": {"scenarios": rows}}) is None


async def test_refused_after_failed_scenario_publication(aiohttp_client, tmp_path):
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True, 2: True}))
    app["scenario_publication_failed_ids"].add(2)
    await _assert_refused(cli, app, bridge, {1: False, 2: True}, "previous_publication_failed")


async def test_refused_after_failed_equipment_publication(aiohttp_client, tmp_path):
    """Revue 24.18 — un équipement non publié par la dernière synchro : la synchro complète le rejouerait."""
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True}))
    publication_result = app["publications"][5].mapping_result.publication_result
    original = publication_result.status
    try:
        object.__setattr__(publication_result, "status", "failed")
        await _assert_refused(cli, app, bridge, {1: False}, "previous_publication_failed")
    finally:
        object.__setattr__(publication_result, "status", original)


async def test_refused_with_deferred_operations(aiohttp_client, tmp_path):
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True}))
    app["pending_discovery_unpublish"][99] = "sensor"
    await _assert_refused(cli, app, bridge, {1: False}, "deferred_operations")
    app["pending_discovery_unpublish"].clear()
    app["pending_local_availability_cleanup"][99] = "jeedom2ha/99/availability"
    await _assert_refused(cli, app, bridge, {1: False}, "deferred_operations")


async def test_refused_with_pending_settings(aiohttp_client, tmp_path, monkeypatch):
    """Réglage en attente : la synchro complète l'appliquerait (décision du 13/11), donc refus."""
    import transport.http_server as server

    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True}))
    monkeypatch.setattr(server, "list_equipment_overrides", lambda _d: {"5": {"publication_override": "exclude"}})
    await _assert_refused(cli, app, bridge, {1: False}, "pending_overrides")


async def test_settings_applied_by_the_last_full_sync_do_not_block(aiohttp_client, tmp_path, monkeypatch):
    """Un réglage déjà appliqué par la dernière synchro complète n'est pas « en attente »."""
    import transport.http_server as server

    monkeypatch.setattr(server, "list_equipment_overrides", lambda _d: {"5": {"publication_override": "exclude"}})
    bridge = _bridge()
    _app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True}))
    data = await _post_light(cli, {1: False})
    assert data["status"] == "ok" and data["result"] == "applied"


async def test_override_of_an_equipment_absent_from_jeedom_does_not_block(aiohttp_client, tmp_path, monkeypatch):
    """Même règle que ``pending_changes`` de l'export : seuls les équipements de l'instantané comptent."""
    import transport.http_server as server

    bridge = _bridge()
    _app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True}))
    monkeypatch.setattr(server, "list_equipment_overrides", lambda _d: {"777": {"publication_override": "exclude"}})
    data = await _post_light(cli, {1: False})
    assert data["status"] == "ok" and data["result"] == "applied"


# ---------------------------------------------------------------------------
# Échecs : rien de perdu, la synchro complète suivante rattrape
# ---------------------------------------------------------------------------

async def test_broker_unavailable(aiohttp_client, tmp_path):
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True}))
    bridge.is_connected = False
    bridge.published.clear()
    data = await _post_light(cli, {1: False})
    assert data["status"] == "error" and data["code"] == "broker_unavailable"
    assert bridge.published == []
    assert app["topology"].scenarios[1].is_active is True


async def test_publish_failure_keeps_memory_aligned_with_ha(aiohttp_client, tmp_path):
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True, 2: True}))
    bridge.published.clear()
    bridge.fail_topics.add(_avail(2))
    data = await _post_light(cli, {1: False, 2: False})
    assert data["status"] == "error" and data["code"] == "publish_failed" and data["scenario_ids"] == [2]
    # Le 1 a été publié : mémoire alignée ; le 2 non : mémoire inchangée et marqué en attente.
    assert app["topology"].scenarios[1].is_active is False
    assert app["topology"].scenarios[2].is_active is True
    assert app["scenario_publications"][2].active_or_alive is True
    assert 2 in app["scenario_publication_failed_ids"]
    # Une synchro complète rattrape tout.
    bridge.fail_topics.clear()
    result = await _sync(cli, _body({1: False, 2: False}))
    assert result["scenario_availability_complete"] is True
    assert (_avail(2), "offline", 1, True) in bridge.published
    assert not app["scenario_publication_failed_ids"]


# ---------------------------------------------------------------------------
# Garde de la route
# ---------------------------------------------------------------------------

async def test_unauthorized(aiohttp_client, tmp_path):
    _app, cli = await _client(aiohttp_client, _bridge(), tmp_path)
    await _post_light(cli, {1: False}, expect=401, headers={})


async def test_bad_payload(aiohttp_client, tmp_path):
    _app, cli = await _client(aiohttp_client, _bridge(), tmp_path)
    await _sync(cli, _body({1: True}))
    for scenarios in (None, "x", [{"id": "1", "is_active": True}], [{"id": 1, "is_active": "yes"}],
                      [{"id": True, "is_active": True}], [{"id": 0, "is_active": True}],
                      [{"id": 1, "is_active": True}, {"id": 1, "is_active": False}]):
        resp = await cli.post("/action/scenario_activation", headers=H,
                              json={"action": "scenario_activation", "payload": {"scenarios": scenarios}})
        assert resp.status == 400, scenarios


async def test_operation_in_progress(aiohttp_client, tmp_path, monkeypatch):
    import transport.http_server as server

    monkeypatch.setattr(server, "_SYNC_ACTION_LOCK_WAIT_SECONDS", 0.05)
    bridge = _bridge()
    app, cli = await _client(aiohttp_client, bridge, tmp_path)
    await _sync(cli, _body({1: True}))
    await app["action_lock"].acquire()
    try:
        bridge.published.clear()
        data = await _post_light(cli, {1: False}, expect=409)
        assert data["code"] == "action_in_progress"
        assert bridge.published == []
    finally:
        app["action_lock"].release()
    await asyncio.sleep(0)
