"""Story 25.2 — GET /system/equipment_states : forme, parité avec l'arbre unitaire, lecture
seule, isolation des erreurs, cache et invalidations (AC1-AC14, AC17)."""

import asyncio
import copy
import json
import os
import re
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from aiohttp import web

import transport.http_server as http_server
from transport.http_server import create_app
from mapping.overrides import save_equipment_override
from models.published_scope import resolve_published_scope
from .story_25_2_corpus import NEVER_SYNCED, build_corpus_topology, light, populate_app

SECRET = "test_secret"
H = {"X-Local-Secret": SECRET}
URL = "/system/equipment_states"
EQ_IDS = sorted(build_corpus_topology().eq_logics)

EQUIPMENT_KEYS = {"jeedom_eq_id", "equipment_decision", "entities", "commands", "sync_status"}
COMMAND_KEYS = {"jeedom_cmd_id", "covered", "published_in_ha", "diagnostic"}
SYNC_KEYS = {"synced_should_publish", "current_should_publish", "override_pending", "published_in_ha"}
FORBIDDEN_KEYS = {"state", "blocked_mention", "by_state", "defects", "counts", "enabled",
                  "category", "to_apply", "blocked_count", "ignored", "rooms",
                  "override_types_allowed"}


@pytest.fixture
def app(tmp_path):
    app = create_app(local_secret=SECRET)
    populate_app(app, tmp_path)
    return app


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


async def _get(cli, query=""):
    resp = await cli.get(URL + query, headers=H)
    assert resp.status == 200
    return (await resp.json())["payload"]


def _walk_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_keys(item)


def _project(tree):
    return {
        "jeedom_eq_id": tree["jeedom_eq_id"],
        "equipment_decision": tree["equipment_decision"],
        "entities": [{"override_pending": e["override_pending"]} for e in tree["entities"]],
        "commands": [{k: c[k] for k in COMMAND_KEYS} for c in tree["commands"]],
        "sync_status": tree["sync_status"],
    }


# --- AC1 --------------------------------------------------------------------

async def test_ac1_auth_et_methode(cli):
    assert (await cli.get(URL)).status == 401
    resp = await cli.get(URL, headers={"X-Local-Secret": "mauvais"})
    assert resp.status == 401
    assert await resp.json() == {"status": "error", "message": "Unauthorized"}
    assert (await cli.post(URL, headers=H)).status == 405
    assert (await cli.get(URL, headers=H)).status == 200


async def test_ac1_route_enregistree(cli, app):
    assert any(r.resource.canonical == URL and r.method == "GET" for r in app.router.routes())


# --- AC2 / AC3 / AC5 --------------------------------------------------------

async def test_ac2_forme_et_liste_blanche(cli):
    payload = await _get(cli)
    assert payload["schema_version"] == 1 and payload["available"] is True
    meta = payload["meta"]
    assert meta["equipments_total"] == len(EQ_IDS) == meta["equipments_read"]
    assert meta["cache"]["hit"] is False and meta["action_in_progress"] is False
    assert {"generated_at", "generation"} <= set(meta)
    assert set(payload["equipments"]) == {str(i) for i in EQ_IDS}
    assert payload["unread"] == []
    for entry in payload["equipments"].values():
        assert set(entry) == EQUIPMENT_KEYS
        assert set(entry["sync_status"]) == SYNC_KEYS
        assert all(set(e) == {"override_pending"} for e in entry["entities"])
        assert all(set(c) == COMMAND_KEYS for c in entry["commands"])


@pytest.mark.parametrize("eq_id", EQ_IDS)
async def test_ac3_identique_a_la_projection_de_l_arbre_unitaire(cli, eq_id):
    payload = await _get(cli)
    unit = (await (await cli.get(f"/system/mapping_overrides/{eq_id}", headers=H)).json())["payload"]
    assert payload["equipments"][str(eq_id)] == _project(unit)


@pytest.mark.parametrize("raw_scope", [None, {"equipements": {"101": {"state": "exclude"}}},
                                       {"equipements": {"102": "exclude"}}])
async def test_ac3_parite_avec_un_perimetre_publie(cli, app, raw_scope):
    app["published_scope"] = resolve_published_scope(app["topology"], raw_scope)
    payload = await _get(cli)
    for eq_id in EQ_IDS:
        unit = (await (await cli.get(f"/system/mapping_overrides/{eq_id}", headers=H)).json())["payload"]
        assert payload["equipments"][str(eq_id)] == _project(unit)


async def test_ac3_ordre_natif_des_commandes(cli, app):
    payload = await _get(cli)
    for eq_id, eq in app["topology"].eq_logics.items():
        assert [c["jeedom_cmd_id"] for c in payload["equipments"][str(eq_id)]["commands"]] == \
            [c.id for c in eq.cmds]


async def test_ac5_aucune_decision_precalculee(cli):
    payload = await _get(cli)
    assert not (set(_walk_keys(payload)) & FORBIDDEN_KEYS)


def test_ac5_partition_d3_absente_du_demon():
    root = Path(__file__).resolve().parents[2]
    for path in root.rglob("*.py"):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert "COMMAND_CAUSE_CATEGORIES" not in text and "categoryOfCause" not in text, path


# --- AC6 : lecture seule -----------------------------------------------------

async def test_ac6_lecture_seule(cli, app, tmp_path):
    bridge = MagicMock()
    app["mqtt_bridge"] = bridge
    app["published_scope"] = {"equipements": []}
    def state():
        return {
            "publications": {i: (d, d.should_publish, d.reason, d.discovery_published, d.active_or_alive)
                             for i, d in app["publications"].items()},
            "pending": dict(app["pending_discovery_unpublish"]),
            "scope": copy.deepcopy(app["published_scope"]),
        }

    before = state()
    topology_before = app["topology"]
    overrides_file = tmp_path / "overrides.json"
    stat_before = overrides_file.stat().st_mtime_ns if overrides_file.exists() else None
    for query in ("", "", "?refresh=1"):
        await _get(cli, query)
    assert bridge.publish_message.call_count == 0
    assert not bridge.method_calls
    assert state() == before
    assert app["topology"] is topology_before
    assert (overrides_file.stat().st_mtime_ns if overrides_file.exists() else None) == stat_before


# --- AC7 / AC8 ---------------------------------------------------------------

async def test_ac7_isolation_des_erreurs(cli, app):
    real = http_server._build_mapping_override_tree

    def flaky(eq, *a, **kw):
        if eq.id == 102:
            raise RuntimeError("Eq-102 secret detail")
        return real(eq, *a, **kw)

    with patch.object(http_server, "_build_mapping_override_tree", flaky):
        resp = await cli.get(URL, headers=H)
        body = await resp.text()
    payload = json.loads(body)["payload"]
    assert resp.status == 200
    assert payload["unread"] == [{"eq_id": 102, "reason": "build_error"}]
    assert "102" not in payload["equipments"] and len(payload["equipments"]) == len(EQ_IDS) - 1
    assert payload["meta"]["equipments_read"] == payload["meta"]["equipments_total"] - 1
    assert "secret detail" not in body and "not_in_topology" not in body
    # un équipement fautif n'est pas mis en cache comme valide : reconstruit à l'appel suivant
    again = await _get(cli)
    assert again["meta"]["cache"]["hit"] is False and again["unread"] == []


async def test_ac7_equipement_jamais_synchronise_sans_entree_unread(cli, app):
    del app["topology"].eq_logics[107]
    payload = await _get(cli)
    assert "107" not in payload["equipments"] and payload["unread"] == []
    assert payload["meta"]["equipments_total"] == len(EQ_IDS) - 1


async def test_ac8_avant_premiere_synchro(aiohttp_client, tmp_path):
    app = create_app(local_secret=SECRET)
    app["data_dir"] = str(tmp_path)
    cli = await aiohttp_client(app)
    payload = await _get(cli)
    assert payload["available"] is False
    assert payload["equipments"] == {} and payload["unread"] == []
    assert app["equipment_states_cache"]["entry"] is None
    populate_app(app, tmp_path)
    after = await _get(cli)
    assert after["available"] is True and len(after["equipments"]) == len(EQ_IDS)


# --- AC9 : une passe, peu de lectures ---------------------------------------

async def test_ac9_une_seule_lecture_des_overrides_et_pas_de_types_allowed(cli):
    with patch.object(http_server, "list_overrides", wraps=http_server.list_overrides) as lo, \
         patch.object(http_server, "list_equipment_overrides",
                      wraps=http_server.list_equipment_overrides) as leo, \
         patch.object(http_server, "_projection_valid_override_types") as pvot:
        await _get(cli)
    assert lo.call_count == 1 and leo.call_count == 1
    pvot.assert_not_called()


# --- AC10 / AC14 : cache -----------------------------------------------------

async def test_ac10_hit_apres_build_et_refresh(cli, caplog):
    first = await _get(cli)
    second = await _get(cli)
    assert (first["meta"]["cache"]["hit"], second["meta"]["cache"]["hit"]) == (False, True)
    assert second["equipments"] == first["equipments"]
    assert second["meta"]["generated_at"] == first["meta"]["generated_at"]
    caplog.set_level("INFO")
    third = await _get(cli, "?refresh=1")
    assert third["meta"]["cache"]["hit"] is False
    assert third["meta"]["generation"] > second["meta"]["generation"]
    assert (await _get(cli))["meta"]["generation"] == third["meta"]["generation"]
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("[AGGREGATE]")]
    assert len(lines) == 1
    assert re.fullmatch(
        r"\[AGGREGATE\] build equipments=\d+ unread=\d+ build_ms=[\d.]+ bytes=\d+ generation=\d+",
        lines[0])
    assert "Eq-" not in lines[0]


async def test_ac10_plafond_de_300_secondes(cli):
    await _get(cli)
    cache = cli.app["equipment_states_cache"]
    assert http_server._EQUIPMENT_STATES_MAX_AGE_SECONDS == 300
    cache["entry"]["stored_at"] -= 301
    assert (await _get(cli))["meta"]["cache"]["hit"] is False


async def test_ac10_signature_du_fichier_d_overrides(cli, app, tmp_path):
    await _get(cli)
    save_equipment_override(101, {"publication_override": "exclude"}, str(tmp_path))  # hors handler
    after = await _get(cli)
    assert after["meta"]["cache"]["hit"] is False
    assert after["equipments"]["101"]["sync_status"]["override_pending"] is True


async def test_ac10_identite_de_la_topologie(cli, app):
    await _get(cli)
    app["topology"] = copy.copy(app["topology"])
    assert (await _get(cli))["meta"]["cache"]["hit"] is False


async def test_ac10_requetes_concurrentes_une_seule_construction(cli):
    real = http_server._build_equipment_states
    with patch.object(http_server, "_build_equipment_states", side_effect=real) as build:
        first, second = await asyncio.gather(cli.get(URL, headers=H), cli.get(URL, headers=H))
        a, b = (await first.json())["payload"], (await second.json())["payload"]
    assert build.call_count == 1
    assert a["equipments"] == b["equipments"]


async def test_ac10_cache_en_memoire_seulement(cli, tmp_path):
    before = sorted(os.listdir(tmp_path))
    await _get(cli)
    assert sorted(os.listdir(tmp_path)) == before


# --- AC11 : synchro ----------------------------------------------------------

async def test_ac11_get_synchro_get(cli, app):
    first = await _get(cli)
    assert first["equipments"]["101"]["sync_status"]["published_in_ha"] is True

    async def fake_sync(request):
        app["publications"][101].discovery_published = False
        app["publications"][101].active_or_alive = False
        return web.json_response({"status": "ok"})

    with patch.object(http_server, "_do_handle_action_sync_body", fake_sync):
        assert (await cli.post("/action/sync", json={}, headers=H)).status == 200
    after = await _get(cli)
    assert after["meta"]["cache"]["hit"] is False
    assert after["equipments"]["101"]["sync_status"]["published_in_ha"] is False


async def test_ac11_invalide_aussi_en_cas_d_echec_de_synchro(cli, app):
    await _get(cli)

    async def failing_sync(request):
        app["publications"].pop(101)
        raise RuntimeError("boom")

    with patch.object(http_server, "_do_handle_action_sync_body", failing_sync):
        await cli.post("/action/sync", json={}, headers=H)
    after = await _get(cli)
    assert after["meta"]["cache"]["hit"] is False
    assert after["equipments"]["101"]["sync_status"]["published_in_ha"] is False


async def test_ac11_aucune_construction_pendant_action_lock(cli, app):
    reached, release = asyncio.Event(), asyncio.Event()

    async def slow_sync(request):
        # nouvelle topologie, publications pas encore à jour : l'état « mixte » à ne jamais servir
        app["topology"] = copy.copy(app["topology"])
        reached.set()
        await release.wait()
        return web.json_response({"status": "ok"})

    with patch.object(http_server, "_do_handle_action_sync_body", slow_sync), \
         patch.object(http_server, "_build_equipment_states",
                      wraps=http_server._build_equipment_states) as build:
        task = asyncio.ensure_future(cli.post("/action/sync", json={}, headers=H))
        await reached.wait()
        during = await _get(cli)
        assert during["available"] is False and during["reason"] == "action_in_progress"
        assert during["equipments"] == {}
        assert build.call_count == 0 and app["equipment_states_cache"]["entry"] is None
        release.set()
        assert (await task).status == 200
        after = await _get(cli)
    assert build.call_count == 1 and after["available"] is True
    assert after["meta"]["action_in_progress"] is False


async def test_ac11_entree_valide_servie_pendant_action_lock(cli, app):
    await _get(cli)
    await app["action_lock"].acquire()
    try:
        during = await _get(cli)
    finally:
        app["action_lock"].release()
    assert during["available"] is True and during["meta"]["action_in_progress"] is True
    assert during["meta"]["cache"]["hit"] is True


async def test_ac11_resultat_perime_jamais_stocke(cli, app):
    real = http_server._build_equipment_states

    def build_then_invalidate(app_, data_dir):
        built = real(app_, data_dir)
        http_server._invalidate_equipment_states(app_)  # synchro terminée « pendant » la construction
        return built

    with patch.object(http_server, "_build_equipment_states", build_then_invalidate):
        stale = await _get(cli)
    assert stale["available"] is True
    assert app["equipment_states_cache"]["entry"] is None
    assert (await _get(cli))["meta"]["cache"]["hit"] is False


async def test_ac11_la_route_ne_prend_pas_le_verrou(cli, app):
    await _get(cli)
    assert not app["action_lock"].locked()


# --- AC12 : écritures d'override --------------------------------------------

async def test_ac12_publication_override_save_puis_get(cli):
    before = await _get(cli)
    assert before["equipments"]["101"]["sync_status"]["override_pending"] is False
    resp = await cli.post("/action/publication_override", headers=H, json={"payload": {
        "jeedom_eq_id": 101, "publication_policy": "exclude"}})
    assert resp.status == 200
    after = await _get(cli)
    assert after["meta"]["cache"]["hit"] is False
    assert after["equipments"]["101"]["sync_status"]["override_pending"] is True
    unit = (await (await cli.get("/system/mapping_overrides/101", headers=H)).json())["payload"]
    assert after["equipments"]["101"] == _project(unit)


async def test_ac12_mapping_override_save_et_reverts(cli):
    async def hit():
        return (await _get(cli))["meta"]["cache"]["hit"]

    await _get(cli)
    assert (await cli.post("/action/mapping_override", headers=H, json={"payload": {
        "jeedom_eq_id": 101, "jeedom_cmd_id": 1011, "ha_entity_type": "binary_sensor"}})).status == 200
    assert await hit() is False
    assert await hit() is True
    assert (await cli.post("/action/mapping_override_revert", headers=H, json={"payload": {
        "jeedom_eq_id": 101}})).status == 200
    assert await hit() is False
    assert await hit() is True
    assert (await cli.post("/action/publication_override_revert", headers=H, json={"payload": {
        "jeedom_eq_id": 105}})).status == 200
    after = await _get(cli)
    assert after["meta"]["cache"]["hit"] is False
    assert after["equipments"]["105"]["sync_status"]["override_pending"] is False


# --- AC13 : actions et republication ----------------------------------------

async def test_ac13_action_execute_invalide(cli, app):
    class Bridge:
        is_connected = True

        def publish_message(self, *a, **kw):
            return True

    app["mqtt_bridge"] = Bridge()
    app["published_scope"] = resolve_published_scope(app["topology"])
    await _get(cli)
    generation = app["equipment_states_cache"]["generation"]
    resp = await cli.post("/action/execute", headers=H, json={
        "intention": "supprimer", "portee": "equipement", "selection": [101], "deadline_s": 55.0})
    assert resp.status == 200
    assert app["equipment_states_cache"]["generation"] > generation
    assert app["equipment_states_cache"]["entry"] is None


async def test_ac13_republication_invalide(cli, app):
    cache = app["equipment_states_cache"]
    cache["entry"] = {"stale": True}
    generation = cache["generation"]
    await http_server._republish_all_from_cache(app, "ha_birth")
    assert cache["entry"] is None and cache["generation"] == generation + 1


def test_ac13_chemins_d_ecriture_de_l_etat_connus():
    """Énumère chaque endroit du démon qui écrit dans publications / pending_discovery_unpublish /
    published_scope ; un nouveau chemin non listé doit être examiné (invalidation) avant d'être ajouté."""
    root = Path(__file__).resolve().parents[2]
    pattern = re.compile(
        r'\[\s*"(publications|pending_discovery_unpublish|published_scope)"\s*\]\s*=(?!=)'
        r'|\[\s*"(publications|pending_discovery_unpublish|published_scope)"\s*\]\s*\.(update|pop|clear|setdefault)\('
        r'|\.get\("(publications|pending_discovery_unpublish)"\)\s*\.(update|pop|clear|setdefault)\(')
    found = {}
    for path in root.rglob("*.py"):
        if "tests" in path.parts:
            continue
        hits = [m.group(0) for m in pattern.finditer(path.read_text(encoding="utf-8"))]
        if hits:
            found[str(path.relative_to(root))] = len(hits)
    # transport/http_server.py : synchro (verrou → finally), /action/execute (verrou → finally),
    # create_app (initialisation). Aucun autre module n'écrit : sinon, ajouter l'invalidation.
    assert set(found) == {"transport/http_server.py"}, found
    src = (root / "transport/http_server.py").read_text(encoding="utf-8")
    assert src.count("_invalidate_equipment_states(request.app)") >= 5  # 1 synchro, 1 action, 3 overrides
    assert "_invalidate_equipment_states(app)" in src  # republication


# --- AC4 : fixtures versionnées pour la parité JS ----------------------------

PARITY_FIXTURE = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "story_25_2_parite_etat.json"


async def test_ac4_fixtures_de_parite_a_jour(cli, app):
    """Arbre unitaire complet / entrée agrégée de chaque équipement du corpus, consommés par
    tests/unit/test_story_25_2_parite_etat.node.test.js. Régénérer :
    JEEDOM2HA_UPDATE_SNAPSHOT=1 python3 -m pytest resources/daemon/tests/unit/test_story_25_2_route_agregee.py"""
    payload = await _get(cli)
    data = {}
    for eq_id in EQ_IDS:
        unit = (await (await cli.get(f"/system/mapping_overrides/{eq_id}", headers=H)).json())["payload"]
        data[str(eq_id)] = {
            "enabled": app["topology"].eq_logics[eq_id].is_enable,
            "tree": unit,
            "aggregated": payload["equipments"][str(eq_id)],
        }
    text = json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if os.environ.get("JEEDOM2HA_UPDATE_SNAPSHOT") == "1":
        PARITY_FIXTURE.write_text(text, encoding="utf-8")
    assert PARITY_FIXTURE.read_text(encoding="utf-8") == text
