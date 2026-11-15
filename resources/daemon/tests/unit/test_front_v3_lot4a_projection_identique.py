"""Front v3 — Lot 4a : PREUVE de non-régression de la projection des scénarios à la mise à jour.

Décision d'Alexandre (option B) : les scénarios déjà publiés le restent. Sur une installation mise
à jour, la migration inscrit tous les scénarios lisibles dans `publishedScenarios` ; le PHP envoie
alors `published: true` pour chacun. La trace MQTT complète d'une synchro (topic, payload brut octet
pour octet, qos, retain ; découverte, disponibilités et purge comprises) doit rester celle du code
de base.

La ligne de base `scenarios_upgrade_baseline.json` est capturée sur le code de base (bea9062) AVANT
toute modification du Lot 4a, avec la charge d'un PHP d'avant le Lot 4a (aucun champ de
publication). Elle ne se régénère que volontairement (`JEEDOM2HA_LOT4A_REGEN=1`).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from transport.http_server import create_app

from .front_v3_lot4a_corpus import (
    RetainingRecordingBridge,
    deleted_scenario_retained,
    legacy_scenarios,
    lot4a_scenarios,
    sync_body,
    upgrade_scenarios,
)

SECRET = "test-secret-lot4a"
H = {"X-Local-Secret": SECRET}
BASELINE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "front_v3_lot4a" / "scenarios_upgrade_baseline.json"
)


async def _trace(aiohttp_client, scenarios, request_id="lot4a-baseline") -> List[dict]:
    app = create_app(local_secret=SECRET)
    bridge = RetainingRecordingBridge(deleted_scenario_retained())
    app["mqtt_bridge"] = bridge
    cli = await aiohttp_client(app)
    resp = await cli.post("/action/sync", json=sync_body(scenarios, request_id), headers=H)
    assert resp.status == 200, await resp.text()
    return bridge.calls


def _baseline(trace: List[dict]) -> List[dict]:
    if not BASELINE_PATH.exists():
        if not os.environ.get("JEEDOM2HA_LOT4A_REGEN"):
            raise AssertionError(f"Ligne de base absente ({BASELINE_PATH}) : JEEDOM2HA_LOT4A_REGEN=1 pour la créer.")
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(trace, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


async def test_charge_d_avant_le_lot_4a_trace_identique(aiohttp_client):
    """PHP ancien (aucun champ `published`) : le démon publie comme avant, octet pour octet."""
    trace = await _trace(aiohttp_client, legacy_scenarios())
    assert trace == await _trace(aiohttp_client, legacy_scenarios()), "trace non déterministe"
    scenario_topics = {c["topic"] for c in trace if "scenario" in c["topic"]}
    assert len(scenario_topics) >= 9, "scène trop pauvre : 4 boutons, 4 disponibilités, 1 purge attendus"
    assert trace == _baseline(trace), "la projection vers Home Assistant a changé (topics ou payloads)"


async def test_scene_de_mise_a_jour_tous_publies_trace_identique(aiohttp_client):
    """Après migration (tous `published: true`, champs additifs) : trace identique octet pour octet."""
    trace = await _trace(aiohttp_client, upgrade_scenarios(), "lot4a-upgrade")
    assert trace == _baseline(trace), "la mise à jour change la projection vers Home Assistant"


# ---------------------------------------------------------------------------
# Comportement du démon : publié / non publié / champ absent, retrait, purge
# ---------------------------------------------------------------------------

def _topics(calls, empty=None):
    return [c["topic"] for c in calls if empty is None or (c["payload"] == "") is empty]


async def _app(aiohttp_client, retained=None):
    app = create_app(local_secret=SECRET)
    bridge = RetainingRecordingBridge(retained if retained is not None else deleted_scenario_retained())
    app["mqtt_bridge"] = bridge
    return app, bridge, await aiohttp_client(app)


async def _sync(cli, scenarios, request_id="lot4a"):
    resp = await cli.post("/action/sync", json=sync_body(scenarios, request_id), headers=H)
    assert resp.status == 200, await resp.text()
    return await resp.json()


def _cfg(sc_id):
    return f"homeassistant/button/jeedom2ha_scenario_{sc_id}/config"


def _avail(sc_id):
    return f"jeedom2ha/scenario_{sc_id}/availability"


async def test_non_publie_pas_de_bouton_et_retrait_par_unpublish(aiohttp_client):
    app, bridge, cli = await _app(aiohttp_client)
    result = await _sync(cli, lot4a_scenarios(published={20: True, 22: True}, is_new={23: True}))
    # 21 et 23 : jamais de configuration publiée, seulement le vidage du chemin `unpublish`.
    for sc_id in (21, 23):
        sent = [c for c in bridge.calls if c["topic"] in (_cfg(sc_id), _avail(sc_id))]
        assert sent and all(c["payload"] == "" and c["retain"] for c in sent), sc_id
        assert _cfg(sc_id) not in bridge.retained
    for sc_id in (20, 22):
        assert _cfg(sc_id) in bridge.retained
    # La purge reçoit tous les lisibles : seul le supprimé (99) est vidé par elle.
    assert _cfg(99) not in bridge.retained
    assert result["scenario_availability_complete"] is True
    decisions = app["scenario_publications"]
    assert decisions[21].should_publish is False and decisions[21].discovery_published is False
    assert decisions[21].reason == "scenario_not_selected"
    assert set(decisions) == {20, 21, 22, 23}

    # Synchro suivante, rien n'a changé : le retrait déjà confirmé n'émet plus rien.
    bridge.calls = []
    await _sync(cli, lot4a_scenarios(published={20: True, 22: True}), "lot4a-2")
    assert not [t for t in _topics(bridge.calls) if t in (_cfg(21), _avail(21), _cfg(23), _avail(23))]


async def test_retrait_d_un_scenario_publie_puis_republication(aiohttp_client):
    app, bridge, cli = await _app(aiohttp_client)
    await _sync(cli, upgrade_scenarios())
    assert _cfg(22) in bridge.retained

    bridge.calls = []
    published = {20: True, 21: True, 22: False, 23: True}
    await _sync(cli, lot4a_scenarios(published=published), "lot4a-retrait")
    assert _cfg(22) not in bridge.retained and _avail(22) not in bridge.retained
    assert {_cfg(22), _avail(22)} <= set(_topics(bridge.calls, empty=True))
    for sc_id in (20, 21, 23):
        assert _cfg(sc_id) in bridge.retained

    bridge.calls = []
    await _sync(cli, upgrade_scenarios(), "lot4a-retour")
    assert _cfg(22) in bridge.retained
    assert app["scenario_publications"][22].discovery_published is True


async def test_suppression_et_retrait_distingues(aiohttp_client):
    """23 supprimé de Jeedom → purge ; 22 retiré par l'utilisateur → unpublish ; les autres intacts."""
    _app_, bridge, cli = await _app(aiohttp_client)
    await _sync(cli, upgrade_scenarios())
    scenarios = [row for row in lot4a_scenarios(published={20: True, 21: True, 22: False}) if row["id"] != 23]
    bridge.calls = []
    await _sync(cli, scenarios, "lot4a-suppr")
    assert _cfg(22) not in bridge.retained and _cfg(23) not in bridge.retained
    assert _cfg(20) in bridge.retained and _cfg(21) in bridge.retained
    emptied = _topics(bridge.calls, empty=True)
    assert emptied.count(_cfg(22)) == 1, "le retrait ne doit pas être rejoué par la purge"


async def test_lecture_incomplete_retrait_fait_mais_aucune_purge(aiohttp_client):
    _app_, bridge, cli = await _app(aiohttp_client)
    body = sync_body(lot4a_scenarios(published={20: True, 21: False, 22: True, 23: True}), "lot4a-inc", complete=False)
    resp = await cli.post("/action/sync", json=body, headers=H)
    result = await resp.json()
    assert _cfg(21) not in bridge.retained
    assert _cfg(99) in bridge.retained, "lecture incomplète : la purge ne doit rien vider"
    assert result["scenario_availability_complete"] is False


async def test_broker_injoignable_retrait_rejoue_a_la_synchro_suivante(aiohttp_client):
    app, bridge, cli = await _app(aiohttp_client, retained={_cfg(21): "{}"})
    bridge.is_connected = False
    result = await _sync(cli, lot4a_scenarios(published={20: True, 21: False, 22: True, 23: True}), "lot4a-off")
    assert result["scenario_availability_complete"] is False
    assert app["scenario_publications"][21].reason == "scenario_not_selected_pending"
    assert bridge.calls == []

    bridge.is_connected = True
    result = await _sync(cli, lot4a_scenarios(published={20: True, 21: False, 22: True, 23: True}), "lot4a-on")
    assert _cfg(21) not in bridge.retained
    assert app["scenario_publications"][21].reason == "scenario_not_selected"
    assert result["scenario_availability_complete"] is True


async def test_republication_birth_et_appui_ignorent_un_non_publie(aiohttp_client):
    from sync.command import CommandSynchronizer
    from transport.http_server import _republish_all_from_cache

    app, bridge, cli = await _app(aiohttp_client)
    await _sync(cli, lot4a_scenarios(published={20: True, 21: True, 22: False, 23: True}))
    bridge.calls = []
    await _republish_all_from_cache(app, "ha_birth")
    republished = _topics(bridge.calls, empty=False)
    assert _cfg(20) in republished and _cfg(22) not in republished

    sync = CommandSynchronizer(app=app, mqtt_bridge=bridge,
                               jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
                               jeedom_core_apikey="k")
    assert await sync.handle_command_message("jeedom2ha/scenario_22/cmd", "PRESS") is False


async def test_statut_expose_la_liste_des_scenarios(aiohttp_client):
    _app_, _bridge, cli = await _app(aiohttp_client)
    await _sync(cli, lot4a_scenarios(published={20: True, 21: True, 22: False, 23: False}, is_new={23: True}))
    resp = await cli.get("/system/status", headers=H)
    rows = {row["id"]: row for row in (await resp.json())["payload"]["scenarios"]}
    assert rows[20] == {
        "id": 20, "name": "Scène soirée", "group": "Ambiances", "mode": "provoke",
        "has_trigger": False, "has_schedule": False, "manual": True, "is_active": True,
        "published": True, "is_new": False, "in_ha": True,
        "withdraw_pending": False, "ha_pending": False,  # front v3 (Lot 8) : champs additifs
        "ha_entity_id": "button.jeedom2ha_scenario_20",
    }
    assert rows[21]["is_active"] is False and rows[21]["in_ha"] is True
    assert rows[22]["published"] is False and rows[22]["ha_entity_id"] is None and rows[22]["in_ha"] is False
    assert rows[23]["is_new"] is True and rows[23]["mode"] == "provoke"


async def test_statut_champ_absent_publie_comme_avant(aiohttp_client):
    _app_, _bridge, cli = await _app(aiohttp_client)
    await _sync(cli, legacy_scenarios())
    resp = await cli.get("/system/status", headers=H)
    payload = (await resp.json())["payload"]
    assert all(row["published"] is True and row["in_ha"] is True for row in payload["scenarios"])
    assert all(row["group"] is None and row["mode"] is None for row in payload["scenarios"])
    assert payload["publication"]["scenarios_published"] == 4


async def test_export_de_decision_non_publie(aiohttp_client):
    from transport.http_server import _build_decision_export_document as build

    app, _bridge, cli = await _app(aiohttp_client)
    await _sync(cli, lot4a_scenarios(published={20: True, 21: True, 22: False, 23: True}))
    document = build(app, "/nonexistent", overrides=[], equipment_overrides=[])
    rows = {row["scenario_id"]: row for row in document["scenarios"]}
    assert rows[22]["decision"] == "not_published" and rows[22]["reason"] == "scenario_not_selected"
    assert rows[22]["entity"]["discovery_published"] is False
    assert rows[20]["decision"] == "published" and rows[20]["reason"] == "scenario_button"
