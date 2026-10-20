"""Story 24.2 — export JSON versionné du contrat de décision (démon).

Identifiants génériques et noms sentinelles uniquement (CC-48) : aucun nom réel.
"""

from __future__ import annotations

import copy
import json
import os
import stat
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from export import decision_export as dx
from models.evaluate_equipment import evaluate_equipment
from models.topology import TopologySnapshot, assess_all
from mapping.registry import MapperRegistry
from transport.http_server import create_app

SECRET = "test-secret-24-2-sentinelle-secret"
ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "resources" / "daemon" / "tests" / "fixtures" / "golden_corpus" / "sync_payload.json"
HEADERS = {"X-Local-Secret": SECRET}

# Sentinelles : aucun de ces fragments ne doit apparaître dans le document (AC5).
SENTINELS = ["EQNAME_SENTINEL", "CMDNAME_SENTINEL", "SCNAME_SENTINEL", "ROOMNAME_SENTINEL"]


def _cmd(cmd_id, generic_type, type_="action", sub_type="other", logical_id=None):
    return {
        "id": cmd_id, "name": f"CMDNAME_SENTINEL_{cmd_id}", "generic_type": generic_type,
        "type": type_, "sub_type": sub_type, "logical_id": logical_id,
    }


def _eq(eq_id, cmds, *, eq_type="virtual", enabled=True, excluded=None, **extra):
    eq = {
        "id": eq_id, "name": f"EQNAME_SENTINEL_{eq_id}", "object_id": 10, "is_enable": enabled,
        "is_visible": True, "eq_type": eq_type, "is_excluded": excluded is not None,
        "status": {"timeout": 0}, "cmds": cmds,
    }
    if excluded:
        eq["exclusion_source"] = excluded
    eq.update(extra)
    return eq


LIGHT_CMDS = [
    _cmd(11, "LIGHT_ON", logical_id="ab:01"),
    _cmd(12, "LIGHT_OFF"),
    _cmd(13, "LIGHT_STATE", "info", "binary"),
    _cmd(14, None, "info", "string"),  # non couverte
]


def _payload():
    return {
        "timestamp": "2026-10-20T00:00:00Z",
        "objects": [{"id": 10, "name": "ROOMNAME_SENTINEL"}],
        "eq_logics": [
            _eq(1, LIGHT_CMDS, logical_id="eq-logical", homekit_exposed=True, homekit_exposed_source="equipement"),
            _eq(2, [_cmd(21, "LIGHT_ON")], excluded="plugin", eq_type="zwave"),
            _eq(3, [_cmd(31, "LIGHT_ON")], enabled=False),
            _eq(4, [_cmd(41, None, "info", "string")]),
            _eq(5, [_cmd(51, "LIGHT_ON"), _cmd(52, "LIGHT_OFF"), _cmd(53, "LIGHT_STATE", "info", "binary")]),
        ],
        "scenarios": [
            {"id": 5, "name": "SCNAME_SENTINEL_5", "is_active": True,
             "homekit_exposed": True, "homekit_exposed_source": "scenario_configuration"},
            {"id": 6, "name": "SCNAME_SENTINEL_6", "is_active": False,
             "homekit_exposed": False, "homekit_exposed_source": "scenario_configuration"},
        ],
        "scenarios_complete": True,
        "sync_config": {
            "confidence_policy": "sure_probable",
            "excluded_plugins": ["zwave"],
            "excluded_piece_ids": [10, "7"],
        },
    }


def _body(payload):
    return {"action": "sync", "payload": payload, "request_id": "t24-2", "timestamp": "2026-10-20T00:00:00Z"}


def _bridge():
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    return bridge


@pytest.fixture
def data_dir(tmp_path):
    return tmp_path


@pytest.fixture
def app(data_dir):
    application = create_app(local_secret=SECRET)
    application["data_dir"] = str(data_dir)
    application["mqtt_bridge"] = _bridge()
    application["plugin_version"] = "9.9.9"
    return application


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


async def _sync(cli, payload=None):
    resp = await cli.post("/action/sync", json=_body(payload or _payload()), headers=HEADERS)
    assert resp.status == 200
    return resp


def _file_doc(data_dir):
    return json.loads((Path(data_dir) / dx.EXPORT_FILENAME).read_text(encoding="utf-8"))


async def _route_doc(cli):
    resp = await cli.get("/system/decision_export", headers=HEADERS)
    assert resp.status == 200
    body = await resp.json()
    assert body["status"] == "ok"
    return body["payload"]


def _eq_row(doc, eq_id):
    return next(r for r in doc["equipments"] if r["eq_id"] == eq_id)


# --- AC1 -------------------------------------------------------------------

async def test_ac1_file_written_after_sync_mode_600_no_temp_left(cli, data_dir):
    await _sync(cli)
    path = Path(data_dir) / dx.EXPORT_FILENAME
    assert path.exists()
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert [p.name for p in Path(data_dir).iterdir() if p.name.endswith(".tmp")] == []
    doc = _file_doc(data_dir)
    assert doc["schema_version"] == 1
    assert doc["totals"] == {"equipments": 5, "commands": 4 + 1 + 1 + 1 + 3, "scenarios": 2}


async def test_ac1_cache_file_is_unchanged_in_format_and_content(cli, app, data_dir):
    from cache.disk_cache import save_publications_cache

    await _sync(cli)
    reference = Path(data_dir) / "reference"
    reference.mkdir()
    save_publications_cache(app["publications"], str(reference))
    assert (Path(data_dir) / "jeedom2ha_cache.json").read_text() == \
        (reference / "jeedom2ha_cache.json").read_text()


def test_ac1_write_is_atomic_failure_keeps_previous_file(tmp_path, monkeypatch):
    previous = {"totals": {"equipments": 1, "scenarios": 0}, "marker": "ancien"}
    assert dx.write_decision_export(previous, str(tmp_path)) is True
    boom = {"totals": {"equipments": 1, "scenarios": 0}, "x": object()}  # non sérialisable
    assert dx.write_decision_export(boom, str(tmp_path)) is False
    assert json.loads((tmp_path / dx.EXPORT_FILENAME).read_text())["marker"] == "ancien"
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_ac1_write_uses_replace(tmp_path, monkeypatch):
    calls = []
    real = os.replace
    monkeypatch.setattr(dx.os, "replace", lambda a, b: calls.append((a, b)) or real(a, b))
    assert dx.write_decision_export({"totals": {"equipments": 0, "scenarios": 0}}, str(tmp_path))
    assert len(calls) == 1 and calls[0][1].endswith(dx.EXPORT_FILENAME)


async def test_ac1_publier_rewrites_the_file(cli, app, data_dir):
    await _sync(cli)
    path = Path(data_dir) / dx.EXPORT_FILENAME
    path.unlink()
    resp = await cli.post(
        "/action/execute",
        json={"intention": "publier", "portee": "global", "selection": ["all"]},
        headers=HEADERS,
    )
    assert resp.status == 200
    assert path.exists()


async def test_ac1_supprimer_rewrites_the_file_and_entities_leave_ha(cli, app, data_dir):
    await _sync(cli)
    assert _eq_row(_file_doc(data_dir), 1)["entities"][0]["discovery_published"] is True
    resp = await cli.post(
        "/action/execute",
        json={"intention": "supprimer", "portee": "global", "selection": ["all"]},
        headers=HEADERS,
    )
    assert resp.status == 200
    row = _eq_row(_file_doc(data_dir), 1)
    assert row["entities"][0]["discovery_published"] is False
    assert row["decision"] == "published"  # le verdict du sync n'est pas recalculé par « Supprimer »


# --- AC2 -------------------------------------------------------------------

async def test_ac2_route_requires_secret(cli):
    resp = await cli.get("/system/decision_export")
    assert resp.status == 401


async def test_ac2_route_before_sync_gives_explicit_error(cli):
    resp = await cli.get("/system/decision_export", headers=HEADERS)
    body = await resp.json()
    assert body["status"] == "error"
    assert "appelez /action/sync" in body["message"]


async def test_ac2_route_returns_same_document_as_file(cli, data_dir):
    await _sync(cli)
    from_route = await _route_doc(cli)
    from_file = _file_doc(data_dir)
    from_route.pop("generated_at")
    from_file.pop("generated_at")
    assert from_route == from_file


# --- AC4 -------------------------------------------------------------------

async def test_ac4_covers_every_equipment_command_and_scenario(cli):
    await _sync(cli)
    doc = await _route_doc(cli)
    assert [r["eq_id"] for r in doc["equipments"]] == [1, 2, 3, 4, 5]
    assert [r["scenario_id"] for r in doc["scenarios"]] == [5, 6]
    keys = [r["key"] for r in doc["equipments"]] + [r["key"] for r in doc["scenarios"]]
    assert len(keys) == len(set(keys)) and "eq:5" in keys and "scenario:5" in keys
    for row in doc["equipments"]:
        assert [c["cmd_id"] for c in row["commands"]] == sorted(c["cmd_id"] for c in row["commands"])
        assert all(c["reason"] for c in row["commands"])

    light = _eq_row(doc, 1)
    assert light["decision"] == "published" and light["step"] == "4"
    assert light["logical_id"] == "eq-logical"
    by_cmd = {c["cmd_id"]: c for c in light["commands"]}
    assert by_cmd[11]["logical_id"] == "ab:01" and by_cmd[12]["logical_id"] is None
    assert by_cmd[14]["covered"] is False and by_cmd[14]["reason"] == "command_not_covered"
    assert by_cmd[14]["entity_unique_id"] is None and by_cmd[14]["ha_type"] is None
    assert by_cmd[11]["covered"] is True and by_cmd[11]["entity_unique_id"] == light["entities"][0]["unique_id"]
    assert light["homekit_exposed"] is True and light["homekit_exposed_source"] == "equipement"

    excluded = _eq_row(doc, 2)
    assert excluded["decision"] == "not_published" and excluded["reason"] == "excluded_plugin"
    assert excluded["exclusion_source"] == "plugin" and excluded["step"] == "1"
    assert excluded["commands"][0]["reason"] == "excluded_plugin" and excluded["entities"] == []
    assert _eq_row(doc, 3)["reason"] == "disabled_eqlogic"
    assert _eq_row(doc, 4)["decision"] == "not_published"

    active, inactive = doc["scenarios"]
    assert active["active"] is True and active["decision"] == "published"
    assert active["reason"] == "scenario_button" and active["homekit_exposed"] is True
    assert active["entity"]["unique_id"] == "jeedom2ha_scenario_5"
    assert active["entity"]["entity_id_expected"] == "button.jeedom2ha_scenario_5"
    assert active["entity"]["discovery_published"] is True
    assert inactive["active"] is False and inactive["decision"] == "not_published"
    assert inactive["reason"] == "scenario_inactive" and inactive["entity"]["discovery_published"] is False
    assert inactive["homekit_exposed"] is False


async def test_ac4_config_and_producer(cli):
    await _sync(cli)
    doc = await _route_doc(cli)
    assert doc["config"] == {"excluded_plugins": ["zwave"], "excluded_piece_ids": [7, 10]}
    assert doc["producer"] == {"plugin_version": "9.9.9", "confidence_policy": "sure_probable"}
    assert doc["sync_at"].endswith("Z") and doc["generated_at"].endswith("Z")


async def test_ac4_old_payload_without_filter_config_gives_empty_config(cli):
    payload = _payload()
    payload["sync_config"] = {"confidence_policy": "sure_probable"}
    await _sync(cli, payload)
    doc = await _route_doc(cli)
    assert doc["config"] == {"excluded_plugins": [], "excluded_piece_ids": []}


def test_ac4_duplicate_command_ids_give_one_row_per_cmd_id():
    payload = _payload()
    payload["eq_logics"][0]["cmds"] = LIGHT_CMDS + [_cmd(11, "LIGHT_ON")]
    snapshot = TopologySnapshot.from_jeedom_payload(payload)
    doc = dx.build_decision_export(
        snapshot=snapshot, memo=dx.DecisionMemo(), mappings={}, publications={}, scenario_publications={},
        streaming_targets=[], current_overrides={}, plugin_version="x", confidence_policy="sure_probable",
    )
    ids = [c["cmd_id"] for c in _eq_row(doc, 1)["commands"]]
    assert ids == sorted(set(ids)) == [11, 12, 13, 14]
    assert doc["totals"]["commands"] == sum(len(r["commands"]) for r in doc["equipments"])


# --- AC5 -------------------------------------------------------------------

async def test_ac5_no_name_no_secret_in_document_or_file(cli, app, data_dir):
    await _sync(cli)
    texts = [json.dumps(await _route_doc(cli)), (Path(data_dir) / dx.EXPORT_FILENAME).read_text()]
    forbidden = SENTINELS + [SECRET, "password", "apikey", "api_key", "token", "mqtt_user"]
    for text in texts:
        for fragment in forbidden:
            assert fragment.lower() not in text.lower(), fragment


# --- AC6 -------------------------------------------------------------------

async def test_ac6_ids_equal_the_discovery_payload(cli, app):
    await _sync(cli)
    doc = await _route_doc(cli)
    published = {}
    for call in app["mqtt_bridge"].publish_message.call_args_list:
        topic, raw = call.args[0], call.args[1]
        if topic.startswith("homeassistant/") and topic.endswith("/config") and raw:
            payload = json.loads(raw)
            published[payload["unique_id"]] = payload
    rows = [e for r in doc["equipments"] for e in r["entities"] if e["discovery_published"]]
    rows += [s["entity"] for s in doc["scenarios"] if s["entity"]["discovery_published"]]
    assert rows, "au moins une entité publiée attendue"
    for entity in rows:
        payload = published[entity["unique_id"]]
        assert entity["entity_id_expected"] == payload["default_entity_id"]
        assert entity["entity_id_expected"] == f"{entity['ha_type']}.{payload['object_id']}"
    assert {e["unique_id"] for e in rows} == set(published)


# --- AC7 -------------------------------------------------------------------

def _golden_body():
    corpus = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return {
        "objects": corpus["objects"], "eq_logics": corpus["eq_logics"],
        "sync_config": corpus.get("sync_config", {"confidence_policy": "sure_probable"}),
    }


_DIAGNOSTIC_ALIASES = {
    "no_projection_possible": "no_mapping",            # libellé UX du diagnostic pour « éligible, non mappé »
    "no_supported_generic_type": "no_generic_type_configured",  # alias de la taxonomie fermée (19.0)
}


async def test_ac7_parity_with_evaluate_equipment_and_diagnostics_on_golden_corpus(cli, app):
    await _sync(cli, _golden_body())
    doc = await _route_doc(cli)
    diag = await (await cli.get("/system/diagnostics", headers=HEADERS)).json()
    diag_by_eq = {e["eq_id"]: e for e in diag["payload"]["equipments"]}

    snapshot = TopologySnapshot.from_jeedom_payload(_golden_body())
    eligibility = assess_all(snapshot)
    registry = MapperRegistry()
    assert len(doc["equipments"]) == len(snapshot.eq_logics) >= 50
    for row in doc["equipments"]:
        eq = snapshot.eq_logics[row["eq_id"]]
        evaluation = evaluate_equipment(
            eq, snapshot, eligibility[eq.id], mapper_registry=registry,
            confidence_policy="sure_probable", persisted_overrides={}, persisted_equipment_overrides={},
        )
        expected = {cd.cmd_id: cd for cd in evaluation.command_decisions}
        assert {c["cmd_id"] for c in row["commands"]} == set(expected)
        for cmd in row["commands"]:
            cd = expected[cmd["cmd_id"]]
            assert cmd["decision"] == ("published" if cd.should_publish else "not_published")
            assert (cmd["reason"], cmd["step"]) == (cd.reason, cd.step)
        diag_reason = diag_by_eq[row["eq_id"]]["reason_code"]
        assert row["reason"] == _DIAGNOSTIC_ALIASES.get(diag_reason, diag_reason), row["eq_id"]
        published_in_diag = diag_by_eq[row["eq_id"]]["statut"] == "publie"
        entity_published = any(e["discovery_published"] for e in row["entities"])
        assert published_in_diag == entity_published, row["eq_id"]


async def test_ac7_covering_entity_follows_select_covering_decision_for_secondaries(cli):
    """Une commande portée par plusieurs entités prend celle de la première entité publiée (CC-47)."""
    await _sync(cli, _golden_body())
    doc = await _route_doc(cli)
    multi = [r for r in doc["equipments"] if len(r["entities"]) > 1]
    assert multi, "le corpus doré porte au moins un équipement multi-entités"
    for row in multi:
        unique_ids = {e["unique_id"] for e in row["entities"]}
        for cmd in row["commands"]:
            if cmd["covered"]:
                assert cmd["entity_unique_id"] in unique_ids


# --- AC8 -------------------------------------------------------------------

async def test_ac8_deterministic(cli, app):
    await _sync(cli, _golden_body())
    first = await _route_doc(cli)
    second = await _route_doc(cli)
    first.pop("generated_at")
    second.pop("generated_at")
    assert json.dumps(first, sort_keys=False) == json.dumps(second, sort_keys=False)


async def test_ac8_resync_same_topology_same_document(cli, app):
    await _sync(cli, _golden_body())
    first = await _route_doc(cli)
    await _sync(cli, _golden_body())
    second = await _route_doc(cli)
    for doc in (first, second):
        doc.pop("generated_at")
        doc.pop("sync_at")
    assert first == second


# --- Overrides / pending_changes ----------------------------------------------

async def test_overrides_applied_and_pending_changes(cli, app, data_dir):
    from mapping.overrides import save_equipment_override

    await _sync(cli)
    assert _eq_row(await _route_doc(cli), 1)["pending_changes"] is False
    assert save_equipment_override(1, {"publication_override": "exclude"}, str(data_dir)) is True
    row = _eq_row(await _route_doc(cli), 1)
    assert row["pending_changes"] is True
    assert row["overrides"]["publication"] is None  # pas encore appliqué
    assert row["decision"] == "published"
    await _sync(cli)
    row = _eq_row(await _route_doc(cli), 1)
    assert row["pending_changes"] is False
    assert row["overrides"]["publication"] == "exclude"
    assert row["decision"] == "not_published" and row["reason"] == "publication_excluded_eqlogic"


# --- state_source ---------------------------------------------------------------

async def test_state_source_streamed_optimistic_none(cli, app):
    state_sync = MagicMock()
    state_sync.is_active = True
    state_sync.list_state_targets = MagicMock(return_value=[
        {"eq_id": 1, "cmd_id": 13, "ha_type": "light", "state_topic": "jeedom2ha/1/state"},
    ])
    app["state_synchronizer"] = state_sync
    state_sync.publish_initial_states = MagicMock(side_effect=lambda decision: _async(0))
    await _sync(cli)
    doc = await _route_doc(cli)
    assert _eq_row(doc, 1)["entities"][0]["state_source"] == "streamed"
    assert _eq_row(doc, 5)["entities"][0]["state_source"] == "optimistic"
    assert doc["scenarios"][0]["entity"]["state_source"] == "none"


async def _async(value):
    return value


# --- Mémorisation sans effet sur la publication --------------------------------------

async def test_ac9_publication_unchanged_with_and_without_export(cli, app, monkeypatch):
    await _sync(cli, _golden_body())
    with_export = sorted(
        (c.args[0], c.args[1]) for c in app["mqtt_bridge"].publish_message.call_args_list
    )

    import transport.http_server as hs

    app2 = create_app(local_secret=SECRET)
    app2["mqtt_bridge"] = _bridge()
    monkeypatch.setattr(hs, "_refresh_decision_export", lambda *a, **k: None)
    from aiohttp.test_utils import TestClient, TestServer

    async with TestClient(TestServer(app2)) as client2:
        resp = await client2.post("/action/sync", json=_body(_golden_body()), headers=HEADERS)
        assert resp.status == 200
    without_export = sorted(
        (c.args[0], c.args[1]) for c in app2["mqtt_bridge"].publish_message.call_args_list
    )
    assert with_export == without_export


async def test_export_failure_never_breaks_sync(cli, app, monkeypatch):
    import transport.http_server as hs

    monkeypatch.setattr(hs, "write_decision_export", lambda *a, **k: (_ for _ in ()).throw(OSError("disque plein")))
    resp = await _sync(cli)
    body = await resp.json()
    assert body["status"] == "ok"


async def test_memorization_failure_never_breaks_sync_nor_publier(cli, app, monkeypatch):
    """Revue PR #320 : un verdict impossible à mémoriser n'interrompt ni le sync ni « Publier »."""
    import transport.http_server as hs

    def _boom(*_a, **_k):
        raise RuntimeError("enregistrement en échec")

    monkeypatch.setattr(hs, "make_equipment_record", _boom)
    monkeypatch.setattr(hs, "make_ineligible_record", _boom)
    body = await (await _sync(cli)).json()
    assert body["status"] == "ok"
    assert any(
        c.args[0].startswith("homeassistant/") and c.args[0].endswith("/config")
        for c in app["mqtt_bridge"].publish_message.call_args_list
    )
    resp = await cli.post(
        "/action/execute",
        json={"intention": "publier", "portee": "global", "selection": ["all"]},
        headers=HEADERS,
    )
    assert resp.status == 200
    doc = await _route_doc(cli)
    assert {r["reason"] for r in doc["equipments"]} == {"no_sync_decision"}


# --- Fonctions pures ---------------------------------------------------------------

def test_index_overrides_canonical_form_ignores_unknown_values():
    indexed = dx.index_overrides(
        {"7:70": {"ha_entity_type": "switch", "publication_override": "force_publish", "source": "user"},
         "bad": {"ha_entity_type": "x"}, "7:71": {"publication_override": "n_importe_quoi"}},
        {"7": {"publication_override": "exclude"}, "x": {"publication_override": "exclude"}},
    )
    assert indexed == {7: {"publication": "exclude",
                           "commands": {70: {"ha_type": "switch", "publication": "force_publish"}}}}


def test_normalize_export_config_keeps_identifiers_only():
    assert dx.normalize_export_config(None) == {"excluded_plugins": [], "excluded_piece_ids": []}
    assert dx.normalize_export_config({
        "excluded_plugins": ["b", "a", "a", 3, ""], "excluded_piece_ids": [2, "1", True, None, "x"],
    }) == {"excluded_plugins": ["a", "b"], "excluded_piece_ids": [1, 2]}


def test_build_without_memo_record_gives_explicit_no_sync_decision():
    snapshot = TopologySnapshot.from_jeedom_payload(_payload())
    doc = dx.build_decision_export(
        snapshot=snapshot, memo=dx.DecisionMemo(), mappings={}, publications={}, scenario_publications={},
        streaming_targets=[], current_overrides={}, plugin_version="x", confidence_policy="sure_probable",
    )
    row = _eq_row(doc, 1)
    assert row["decision"] == "not_published" and row["reason"] == "no_sync_decision" and row["step"] is None
    assert all(c["reason"] == "no_sync_decision" and c["covered"] is False for c in row["commands"])


def test_document_is_not_mutated_by_json_roundtrip():
    snapshot = TopologySnapshot.from_jeedom_payload(_payload())
    doc = dx.build_decision_export(
        snapshot=snapshot, memo=dx.DecisionMemo(), mappings={}, publications={}, scenario_publications={},
        streaming_targets=[], current_overrides={}, plugin_version="x", confidence_policy="sure_probable",
    )
    assert json.loads(json.dumps(doc)) == copy.deepcopy(doc)


# --- AC10 -------------------------------------------------------------------------

def test_ac10_schema_documented_with_version_policy():
    text = (ROOT / "docs" / "dev-decision-export.md").read_text(encoding="utf-8")
    for fragment in ("schema_version", "Politique de version", "GET /system/decision_export", "getDecisionExport",
                     "pending_changes", "state_source", "entity_id_expected", "discovery_published",
                     "jeedom2ha_decision_export.json", "Identifiants seulement"):
        assert fragment in text, fragment
    # chaque champ du document réel est décrit dans la documentation
    snapshot = TopologySnapshot.from_jeedom_payload(_payload())
    doc = dx.build_decision_export(
        snapshot=snapshot, memo=dx.DecisionMemo(), mappings={}, publications={}, scenario_publications={},
        streaming_targets=[], current_overrides={}, plugin_version="x", confidence_policy="sure_probable",
    )
    names = set(doc) | set(doc["equipments"][0]) | set(doc["equipments"][0]["commands"][0]) | set(doc["scenarios"][0])
    names |= set(doc["scenarios"][0]["entity"])
    for name in names:
        assert f"`{name}`" in text or f"`{name}[]`" in text or f"{name}[]" in text, name


def test_ac10_documented_reasons_exist_in_code():
    assert dx.REASON_SCENARIO_INACTIVE == "scenario_inactive"
    assert dx.REASON_SCENARIO_BUTTON == "scenario_button"
    assert dx.STEP_SCOPE == "scope" and dx.REASON_SCOPE_EXCLUDED == "excluded"
