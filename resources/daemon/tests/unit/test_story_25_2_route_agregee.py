"""Story 25.2 — GET /system/equipment_states : route agrégée en lecture seule + cache.

Fixtures fictives uniquement (CC-48). Le corpus est partagé avec l'instantané du GET unitaire.
"""

import asyncio
import copy
import json
import os
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import transport.http_server as http_server
from transport.http_server import create_app
from .corpus_25_2 import (
    ALL_EQ_IDS, PENDING_EQ, PUBLISHED_EQ, SECRET, apply_corpus,
)
from .test_story_19_6_action_lock_shield import _build_app as _build_action_app
from .test_story_19_6_action_lock_shield import _make_request as _make_action_request

H = {"X-Local-Secret": SECRET}
ROUTE = "/system/equipment_states"
PARITY_FIXTURE = Path(__file__).resolve().parents[3].parent / "tests" / "fixtures" / "story_25_2_etat_parite.json"

EQ_KEYS = {"jeedom_eq_id", "equipment_decision", "entities", "commands", "sync_status"}
CMD_KEYS = {"jeedom_cmd_id", "covered", "published_in_ha", "diagnostic"}
SYNC_KEYS = {"synced_should_publish", "current_should_publish", "override_pending", "published_in_ha"}
FORBIDDEN_KEYS = {
    "state", "blocked_mention", "by_state", "defects", "counts", "enabled", "category",
    "to_apply", "blocked_count", "ignored", "rooms", "override_types_allowed",
}


@pytest.fixture
def app(tmp_path):
    return apply_corpus(create_app(local_secret=SECRET), tmp_path)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


async def _get(cli, query=""):
    resp = await cli.get(ROUTE + query, headers=H)
    assert resp.status == 200
    return (await resp.json())["payload"]


async def _unit_tree(cli, eq_id):
    resp = await cli.get(f"/system/mapping_overrides/{eq_id}", headers=H)
    return (await resp.json())["payload"]


def _project(tree):
    """Projection de référence écrite indépendamment du code testé."""
    return {
        "jeedom_eq_id": tree["jeedom_eq_id"],
        "equipment_decision": tree["equipment_decision"],
        "entities": [{"override_pending": e["override_pending"]} for e in tree["entities"]],
        "commands": [{k: c[k] for k in CMD_KEYS} for c in tree["commands"]],
        "sync_status": {k: tree["sync_status"][k] for k in SYNC_KEYS},
    }


def _walk_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_keys(item)


# --- AC1 ---------------------------------------------------------------------

async def test_ac1_auth_and_methods(cli):
    assert (await cli.get(ROUTE, headers=H)).status == 200
    resp = await cli.get(ROUTE)
    assert resp.status == 401
    assert await resp.json() == {"status": "error", "message": "Unauthorized"}
    assert (await cli.get(ROUTE, headers={"X-Local-Secret": "x"})).status == 401
    assert (await cli.post(ROUTE, headers=H)).status == 405


# --- AC2 ---------------------------------------------------------------------

async def test_ac2_shape_and_whitelist(cli):
    payload = await _get(cli)
    assert payload["schema_version"] == 1 and payload["available"] is True
    assert set(payload) == {"schema_version", "available", "meta", "equipments", "unread"}
    assert set(payload["meta"]) == {
        "generated_at", "generation", "cache", "equipments_total", "equipments_read", "action_in_progress",
    }
    assert set(payload["meta"]["cache"]) == {"hit", "build_ms"}
    assert sorted(payload["equipments"], key=int) == [str(i) for i in sorted(ALL_EQ_IDS)]
    assert payload["unread"] == []
    assert payload["meta"]["equipments_total"] == payload["meta"]["equipments_read"] == len(ALL_EQ_IDS)
    for entry in payload["equipments"].values():
        assert set(entry) == EQ_KEYS
        assert set(entry["sync_status"]) == SYNC_KEYS
        assert all(set(e) == {"override_pending"} for e in entry["entities"])
        assert all(set(c) == CMD_KEYS for c in entry["commands"])


# --- AC3 ---------------------------------------------------------------------

async def test_ac3_equals_projection_of_unit_tree(cli):
    payload = await _get(cli)
    for eq_id in ALL_EQ_IDS:
        tree = await _unit_tree(cli, eq_id)
        assert payload["equipments"][str(eq_id)] == _project(tree), f"eq {eq_id}"
        # ordre natif des commandes conservé
        assert [c["jeedom_cmd_id"] for c in payload["equipments"][str(eq_id)]["commands"]] == [
            c["jeedom_cmd_id"] for c in tree["commands"]
        ]


async def test_ac3_whitelist_fields_exist_in_unit_tree(cli):
    tree = await _unit_tree(cli, ALL_EQ_IDS[0])
    assert EQ_KEYS <= set(tree)
    assert CMD_KEYS <= set(tree["commands"][0])
    assert SYNC_KEYS <= set(tree["sync_status"])
    assert "override_pending" in tree["entities"][0]


# --- AC4 (fixture partagée avec le test Node de parité) -------------------------

async def test_ac4_parity_fixture_is_up_to_date(cli):
    """Les arbres complets et leurs entrées agrégées consommés par le test Node sont ceux du démon."""
    payload = await _get(cli)
    data = {
        str(eq_id): {"tree": await _unit_tree(cli, eq_id), "aggregate": payload["equipments"][str(eq_id)]}
        for eq_id in ALL_EQ_IDS
    }
    if os.environ.get("J2HA_UPDATE_SNAPSHOT") == "1":
        PARITY_FIXTURE.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    assert json.loads(PARITY_FIXTURE.read_text(encoding="utf-8")) == json.loads(json.dumps(data))


# --- AC5 ---------------------------------------------------------------------

async def test_ac5_no_precomputed_decision(cli):
    payload = await _get(cli)
    assert not (set(_walk_keys(payload)) & FORBIDDEN_KEYS)


def test_ac5_partition_d3_absent_from_daemon():
    root = Path(http_server.__file__).resolve().parents[1]
    for path in root.rglob("*.py"):
        if "tests" in path.relative_to(root).parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert "COMMAND_CAUSE_CATEGORIES" not in text and "categoryOfCause" not in text, path


# --- AC6 ---------------------------------------------------------------------

async def test_ac6_read_only(app, cli, tmp_path):
    bridge = MagicMock()
    app["mqtt_bridge"] = bridge
    candidates = list(Path(tmp_path).iterdir())
    assert candidates, "le corpus doit avoir écrit un fichier d'overrides"
    before_mtimes = {p: p.stat().st_mtime_ns for p in candidates}
    before = {
        k: copy.deepcopy(app[k])
        for k in ("publications", "pending_discovery_unpublish", "published_scope")
    }
    topology = app["topology"]
    for query in ("", "", "?refresh=1"):
        await _get(cli, query)
    assert bridge.mock_calls == []
    for key, value in before.items():
        assert app[key] == value
    assert app["topology"] is topology
    assert {p: p.stat().st_mtime_ns for p in Path(tmp_path).iterdir()} == before_mtimes


# --- AC7 ---------------------------------------------------------------------

async def test_ac7_build_error_is_isolated_and_not_cached(app, cli):
    real = http_server._build_mapping_override_tree

    def flaky(eq, *args, **kwargs):
        if eq.id == PUBLISHED_EQ:
            raise RuntimeError("détail secret Eq A")
        return real(eq, *args, **kwargs)

    with patch.object(http_server, "_build_mapping_override_tree", side_effect=flaky):
        payload = await _get(cli)
    assert payload["unread"] == [{"eq_id": PUBLISHED_EQ, "reason": "build_error"}]
    assert str(PUBLISHED_EQ) not in payload["equipments"]
    assert "secret" not in json.dumps(payload)
    assert payload["meta"]["equipments_read"] == payload["meta"]["equipments_total"] - 1
    assert len(payload["equipments"]) == len(ALL_EQ_IDS) - 1
    # un équipement jamais synchronisé est simplement absent, sans `unread` (pas de not_in_topology)
    assert "not_in_topology" not in json.dumps(payload)
    # le fautif est reconstruit à la génération suivante (l'entrée fautive n'est pas « valide » à jamais)
    http_server._invalidate_equipment_states_cache(app)
    payload = await _get(cli)
    assert payload["unread"] == [] and str(PUBLISHED_EQ) in payload["equipments"]


# --- AC8 ---------------------------------------------------------------------

async def test_ac8_before_first_sync(aiohttp_client, tmp_path):
    app = create_app(local_secret=SECRET)
    app["data_dir"] = str(tmp_path)
    cli = await aiohttp_client(app)
    payload = await _get(cli)
    assert payload["available"] is False and payload["equipments"] == {} and payload["unread"] == []
    apply_corpus(app, tmp_path)  # « première synchro »
    payload = await _get(cli)
    assert payload["available"] is True and len(payload["equipments"]) == len(ALL_EQ_IDS)


# --- AC9 ---------------------------------------------------------------------

async def test_ac9_single_overrides_load_and_no_override_types(app, cli):
    counts = {"cmd": 0, "eq": 0}
    real_cmd, real_eq = http_server.list_overrides, http_server.list_equipment_overrides

    def count_cmd(*a, **k):
        counts["cmd"] += 1
        return real_cmd(*a, **k)

    def count_eq(*a, **k):
        counts["eq"] += 1
        return real_eq(*a, **k)

    with patch.object(http_server, "list_overrides", side_effect=count_cmd), \
            patch.object(http_server, "list_equipment_overrides", side_effect=count_eq), \
            patch.object(http_server, "_projection_valid_override_types") as types_mock:
        await _get(cli)
    assert counts == {"cmd": 1, "eq": 1}
    types_mock.assert_not_called()


# --- AC10 / AC14 -------------------------------------------------------------

async def test_ac10_hit_then_miss_conditions(app, cli, tmp_path):
    first = await _get(cli)
    second = await _get(cli)
    assert first["meta"]["cache"]["hit"] is False and second["meta"]["cache"]["hit"] is True
    assert first["meta"]["generation"] == second["meta"]["generation"]
    assert first["equipments"] == second["equipments"]

    # (b) signature du fichier d'overrides (écriture hors handler)
    from mapping.overrides import save_override
    save_override(PUBLISHED_EQ, PUBLISHED_EQ * 10 + 3, {"ha_entity_type": "switch"}, str(tmp_path))
    third = await _get(cli)
    assert third["meta"]["cache"]["hit"] is False and third["meta"]["generation"] > second["meta"]["generation"]

    # (c) identité de la topologie
    app["topology"] = copy.copy(app["topology"])
    assert (await _get(cli))["meta"]["cache"]["hit"] is False

    # (d) plafond de sécurité
    assert (await _get(cli))["meta"]["cache"]["hit"] is True
    app["equipment_states_cache"]["entry"]["built_at"] -= http_server._EQUIPMENT_STATES_TTL_SECONDS + 1
    assert (await _get(cli))["meta"]["cache"]["hit"] is False


def test_ac10_ttl_is_300_seconds():
    assert http_server._EQUIPMENT_STATES_TTL_SECONDS == 300


async def test_ac10_concurrent_requests_build_once(app, cli):
    real = http_server._build_equipment_states_entry
    with patch.object(http_server, "_build_equipment_states_entry", side_effect=real) as build:
        first, second = await asyncio.gather(_get(cli), _get(cli))
    assert build.call_count == 1
    assert first["equipments"] == second["equipments"]


async def test_ac14_refresh_bypasses_cache_and_logs_one_line(app, cli, caplog):
    await _get(cli)
    caplog.set_level("INFO")
    cached = await _get(cli)
    refreshed = await _get(cli, "?refresh=1")
    assert cached["meta"]["cache"]["hit"] is True
    assert refreshed["meta"]["cache"]["hit"] is False
    assert refreshed["meta"]["generation"] > cached["meta"]["generation"]
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("[AGGREGATE]")]
    assert len(lines) == 1
    assert re.fullmatch(
        r"\[AGGREGATE\] build equipments=\d+ unread=\d+ build_ms=\d+ bytes=\d+ generation=\d+", lines[0]
    )
    assert "Eq " not in lines[0]


# --- AC11 --------------------------------------------------------------------

async def test_ac11_sync_invalidates_on_every_exit(app, cli):
    await _get(cli)
    assert app["equipment_states_cache"]["entry"] is not None

    async def fake_body(request):
        app["publications"].pop(PUBLISHED_EQ)  # la synchro change `published_in_ha`
        return http_server.web.json_response({"status": "ok"})

    with patch.object(http_server, "_do_handle_action_sync_body", side_effect=fake_body):
        assert (await cli.post("/action/sync", headers=H)).status == 200
    assert app["equipment_states_cache"]["entry"] is None
    payload = await _get(cli)
    assert payload["equipments"][str(PUBLISHED_EQ)]["sync_status"]["synced_should_publish"] is None

    async def failing_body(request):
        raise RuntimeError("échec de synchro")

    with patch.object(http_server, "_do_handle_action_sync_body", side_effect=failing_body):
        await cli.post("/action/sync", headers=H)
    assert app["equipment_states_cache"]["entry"] is None


async def test_ac11_stale_build_is_returned_but_never_stored(app, cli):
    real = http_server._build_equipment_states_entry

    def build_then_invalidate(*args, **kwargs):
        built = real(*args, **kwargs)
        http_server._invalidate_equipment_states_cache(app)  # synchro terminée pendant la construction
        return built

    with patch.object(http_server, "_build_equipment_states_entry", side_effect=build_then_invalidate):
        payload = await _get(cli)
    assert payload["available"] is True
    assert app["equipment_states_cache"]["entry"] is None


async def test_ac11_no_build_while_action_lock_is_held(app, cli):
    await app["action_lock"].acquire()
    try:
        with patch.object(http_server, "_build_equipment_states_entry") as build:
            payload = await _get(cli)
            assert payload["available"] is False and payload["reason"] == "action_in_progress"
            assert payload["equipments"] == {}
            assert (await _get(cli, "?refresh=1"))["available"] is False
            build.assert_not_called()
    finally:
        app["action_lock"].release()
    assert app["action_lock"].locked() is False
    payload = await _get(cli)
    assert payload["available"] is True and payload["meta"]["action_in_progress"] is False


async def test_ac11_valid_entry_served_during_action_lock(app, cli):
    before = await _get(cli)
    await app["action_lock"].acquire()
    try:
        with patch.object(http_server, "_build_equipment_states_entry") as build:
            served = await _get(cli, "?refresh=1")
            build.assert_not_called()
    finally:
        app["action_lock"].release()
    assert served["meta"]["action_in_progress"] is True and served["meta"]["cache"]["hit"] is True
    assert served["equipments"] == before["equipments"]


async def test_ac11_no_mixed_state_during_suspended_sync(app, cli):
    """Synchro suspendue entre la mutation de `topology` et celle de `publications` : rien n'est construit."""
    await _get(cli)
    suspended, resume = asyncio.Event(), asyncio.Event()

    async def slow_body(request):
        app["topology"] = copy.copy(app["topology"])  # nouvelle topologie, anciennes publications
        suspended.set()
        await resume.wait()
        app["publications"].pop(PUBLISHED_EQ)
        return http_server.web.json_response({"status": "ok"})

    with patch.object(http_server, "_do_handle_action_sync_body", side_effect=slow_body):
        sync_task = asyncio.ensure_future(cli.post("/action/sync", headers=H))
        await suspended.wait()
        with patch.object(http_server, "_build_equipment_states_entry") as build:
            payload = await _get(cli)
            build.assert_not_called()
        assert payload["available"] is False and payload["reason"] == "action_in_progress"
        resume.set()
        assert (await sync_task).status == 200
    payload = await _get(cli)
    assert payload["equipments"][str(PUBLISHED_EQ)]["sync_status"]["synced_should_publish"] is None


# --- AC12 --------------------------------------------------------------------

async def test_ac12_override_writes_invalidate(app, cli):
    before = await _get(cli)
    assert before["equipments"][str(PUBLISHED_EQ)]["sync_status"]["override_pending"] is False
    resp = await cli.post("/action/publication_override", headers=H, json={"payload": {
        "jeedom_eq_id": PUBLISHED_EQ, "publication_policy": "exclude"}})
    assert resp.status == 200
    after = await _get(cli)
    assert after["meta"]["cache"]["hit"] is False
    assert after["equipments"][str(PUBLISHED_EQ)]["sync_status"]["override_pending"] is True
    assert after["equipments"][str(PUBLISHED_EQ)] == _project(await _unit_tree(cli, PUBLISHED_EQ))

    resp = await cli.post("/action/publication_override_revert", headers=H, json={"payload": {
        "jeedom_eq_id": PUBLISHED_EQ}})
    assert resp.status == 200
    assert (await _get(cli))["equipments"][str(PUBLISHED_EQ)]["sync_status"]["override_pending"] is False

    resp = await cli.post("/action/mapping_override", headers=H, json={"payload": {
        "jeedom_eq_id": PUBLISHED_EQ, "jeedom_cmd_id": PUBLISHED_EQ * 10 + 3, "ha_entity_type": "switch"}})
    assert resp.status == 200
    assert (await _get(cli))["meta"]["cache"]["hit"] is False
    await _get(cli)
    resp = await cli.post("/action/mapping_override_revert", headers=H, json={"payload": {
        "jeedom_eq_id": PUBLISHED_EQ, "jeedom_cmd_id": PUBLISHED_EQ * 10 + 3}})
    assert resp.status == 200
    assert (await _get(cli))["meta"]["cache"]["hit"] is False


async def test_ac12_pending_scenario_matches_corpus(cli):
    payload = await _get(cli)
    assert payload["equipments"][str(PENDING_EQ)]["sync_status"]["override_pending"] is True


# --- AC13 --------------------------------------------------------------------

async def test_ac13_action_execute_invalidates():
    app = _build_action_app()
    request = _make_action_request(app, {
        "intention": "supprimer", "portee": "equipement", "selection": [10], "deadline_s": 0.4})
    publisher = MagicMock()
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    app["data_dir"] = "/nonexistent-25-2"
    state = {"cache_entry_before": "sentinel"}
    app["equipment_states_cache"]["entry"] = state
    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), \
            patch.object(http_server, "save_publications_cache"):
        response = await http_server._handle_action_execute(request)
    assert response.status == 200
    assert app["equipment_states_cache"]["entry"] is None


async def test_ac13_republish_replay_invalidates():
    app = _build_action_app()
    app["equipment_states_cache"]["entry"] = {"sentinel": True}
    app["pending_discovery_unpublish"] = {10: "light"}
    with patch.object(http_server, "DiscoveryPublisher") as publisher_cls, \
            patch.object(http_server, "PublisherRegistry") as registry_cls:
        publisher_cls.return_value.unpublish_by_eq_id = AsyncMock(return_value=True)
        registry_cls.return_value.publish = AsyncMock(return_value=True)
        with patch.object(http_server.asyncio, "sleep", new=AsyncMock()):
            await http_server._republish_all_from_cache(app, "broker_reconnect")
    assert app["pending_discovery_unpublish"] == {}
    assert app["equipment_states_cache"]["entry"] is None


def test_ac13_every_state_write_path_is_known():
    """Un futur chemin d'écriture de l'état (publications / pending / scope / topology) doit être connu ici."""
    source = Path(http_server.__file__).read_text(encoding="utf-8")
    pattern = re.compile(
        r'(?:app|request\.app)\["(publications|published_scope|pending_discovery_unpublish|topology|eligibility)"\]'
        r'(?: =|\.(?:update|pop|clear|setdefault)\()'
    )
    functions = []
    for match in pattern.finditer(source):
        head = source[: match.start()]
        name = re.findall(r"^(?:async )?def (\w+)", head, flags=re.M)[-1]
        functions.append(name)
    known = {
        "create_app",                         # initialisation
        "_do_handle_action_sync_body",        # synchro : invalidée par `_run_sync` (finally)
        "_handle_action_execute",             # Publier / Supprimer : invalidée par `_run_action` (finally)
    }
    assert set(functions) <= known, set(functions) - known
    # écritures par alias (`pending_discovery_unpublish.pop(...)`) : confinées aux fonctions invalidantes
    alias = re.compile(r"pending_(?:discovery_)?unpublish\.pop\(|pending_discovery_unpublish\.pop\(")
    owners = {
        re.findall(r"^(?:async )?def (\w+)", source[: m.start()], flags=re.M)[-1]
        for m in alias.finditer(source)
    }
    covered = {
        "_replay_deferred_discovery_unpublish",   # appelée par `_republish_all_from_cache` (invalide)
        "_unpublish_refused_candidates",          # synchro / action
        "_replay_pending_for_action",             # action
        "_do_handle_action_sync_body",
        "_handle_action_execute",
        "_run_action_body",
        "_run_action",
    }
    assert owners <= covered, owners - covered
    # chaque point d'invalidation attendu est bien câblé
    assert source.count("_invalidate_equipment_states_cache(") == 7  # def + 6 sites (sync, action, replay, 3 overrides)
