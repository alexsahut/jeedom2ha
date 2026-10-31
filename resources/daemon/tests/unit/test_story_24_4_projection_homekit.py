"""Story 24.4 — projection par défaut des équipements effectivement exposés à HomeKit.

Identifiants numériques factices et libellés génériques uniquement (CC-48).
"""

from __future__ import annotations

import itertools
import json
from unittest.mock import MagicMock

import pytest

from export import decision_export as dx
from models.published_scope import (
    DECISION_SOURCE_EXCEPTION_HOMEKIT,
    resolve_published_scope,
)
from models.topology import (
    JeedomCmd,
    JeedomEqLogic,
    JeedomScenario,
    TopologySnapshot,
    assess_eligibility,
    compute_homekit_exposed_effective,
)
from transport.http_server import create_app

SECRET = "test-secret-24-4-sentinelle"
HEADERS = {"X-Local-Secret": SECRET}
PIECE = 10

EXPOSED = [True, False, None]
ENABLED = [True, False]


def _eq(eq_id=1, *, exposed=None, enabled=True, excluded=None, piece=PIECE):
    return JeedomEqLogic(
        id=eq_id, name=f"EQ {eq_id}", object_id=piece, is_enable=enabled,
        is_excluded=excluded is not None, exclusion_source=excluded,
        cmds=[JeedomCmd(id=eq_id * 10, name="c", generic_type="LIGHT_ON", type="action", sub_type="other")],
        homekit_exposed=exposed,
    )


def _snapshot(*eqs):
    return TopologySnapshot(timestamp="t", eq_logics={e.id: e for e in eqs})


def _entry(eq, scope):
    return next(e for e in scope["equipements"] if e["eq_id"] == eq.id)


# --- Table de vérité (AC11, AC4) -------------------------------------------

@pytest.mark.parametrize("enabled,exposed,expected", [
    (True, True, True),
    (True, False, False),
    (True, None, None),
    (False, True, False),
    (False, False, False),
    (False, None, False),
])
def test_truth_table(enabled, exposed, expected):
    assert compute_homekit_exposed_effective(exposed, enabled) is expected
    assert _eq(exposed=exposed, enabled=enabled).homekit_exposed_effective is expected
    assert JeedomScenario(id=1, name="s", is_active=enabled, homekit_exposed=exposed
                          ).homekit_exposed_effective is expected


# --- Éligibilité (AC1, AC3, AC4, AC12) --------------------------------------

@pytest.mark.parametrize("exposed,enabled", list(itertools.product(EXPOSED, ENABLED)))
def test_eligibility_object_exclusion_matrix(exposed, enabled):
    result = assess_eligibility(_eq(exposed=exposed, enabled=enabled, excluded="object"))
    if exposed is True and enabled:
        assert result.is_eligible and result.reason_code == "eligible"
    else:
        # non exposé, inconnu, désactivé : comportement actuel (Exclu > Désactivé), AC4 / AC12
        assert not result.is_eligible and result.reason_code == "excluded_object"


@pytest.mark.parametrize("source,reason", [("eqlogic", "excluded_eqlogic"), ("plugin", "excluded_plugin")])
@pytest.mark.parametrize("exposed,enabled", list(itertools.product(EXPOSED, ENABLED)))
def test_eligibility_explicit_exclusions_always_win(exposed, enabled, source, reason):
    result = assess_eligibility(_eq(exposed=exposed, enabled=enabled, excluded=source))
    assert not result.is_eligible and result.reason_code == reason


@pytest.mark.parametrize("exposed", EXPOSED)
def test_eligibility_disabled_outside_excluded_piece_keeps_disabled(exposed):
    result = assess_eligibility(_eq(exposed=exposed, enabled=False))
    assert result.reason_code == "disabled_eqlogic"


def test_eligibility_exposed_without_exclusion_unchanged():
    assert assess_eligibility(_eq(exposed=True)).reason_code == "eligible"
    no_cmds = _eq(exposed=True)
    no_cmds.cmds = []
    assert assess_eligibility(no_cmds).reason_code == "no_commands"  # AC6 : pas de forçage
    untyped = _eq(exposed=True)
    untyped.cmds[0].generic_type = None
    assert assess_eligibility(untyped).reason_code == "no_supported_generic_type"


# --- Résolveur de périmètre (AC1, AC2, AC3, AC4, AC12) -----------------------

def _piece_excluded_scope(**extra):
    scope = {"pieces": {str(PIECE): {"raw_state": "exclude", "source": "user"}}}
    scope.update(extra)
    return scope


@pytest.mark.parametrize("exposed,enabled", list(itertools.product(EXPOSED, ENABLED)))
@pytest.mark.parametrize("legacy", [False, True])
def test_scope_piece_excluded_matrix(exposed, enabled, legacy):
    eq = _eq(exposed=exposed, enabled=enabled, excluded="object" if legacy else None)
    scope = resolve_published_scope(_snapshot(eq), _piece_excluded_scope() if not legacy else {})
    entry = _entry(eq, scope)
    if exposed is True and enabled:
        assert entry["effective_state"] == "include"
        assert entry["decision_source"] == DECISION_SOURCE_EXCEPTION_HOMEKIT == "exception_homekit"
        assert entry["is_exception"] is True
        assert scope["global"]["counts"]["exceptions"] == 1
    else:
        assert entry["effective_state"] == "exclude"
        assert entry["decision_source"] == "piece"
        assert entry["is_exception"] is False
        assert scope["global"]["counts"]["exceptions"] == 0


@pytest.mark.parametrize("exposed", EXPOSED)
def test_scope_explicit_equipment_exclusion_wins(exposed):
    eq = _eq(exposed=exposed)
    for scope_raw in (
        _piece_excluded_scope(equipements={str(eq.id): {"raw_state": "exclude", "source": "user"}}),
        {"equipements": {str(eq.id): {"raw_state": "exclude", "source": "user"}}},
    ):
        entry = _entry(eq, resolve_published_scope(_snapshot(eq), scope_raw))
        assert entry["effective_state"] == "exclude"
        assert entry["decision_source"] != DECISION_SOURCE_EXCEPTION_HOMEKIT


@pytest.mark.parametrize("source", ["eqlogic", "plugin"])
def test_scope_legacy_equipment_or_plugin_exclusion_wins(source):
    eq = _eq(exposed=True, excluded=source)
    entry = _entry(eq, resolve_published_scope(_snapshot(eq), {}))
    assert entry["effective_state"] == "exclude"


@pytest.mark.parametrize("exposed", EXPOSED)
def test_scope_global_exclude_is_respected(exposed):
    eq = _eq(exposed=exposed)
    for scope_raw in ({"global": {"raw_state": "exclude"}},
                      _piece_excluded_scope(**{"global": {"raw_state": "exclude"}})):
        entry = _entry(eq, resolve_published_scope(_snapshot(eq), scope_raw))
        assert entry["effective_state"] == "exclude"
        assert entry["is_exception"] is False  # pas une exception HomeKit


def test_scope_other_equipment_in_same_piece_stays_excluded_and_piece_unchanged():
    exposed, other = _eq(1, exposed=True), _eq(2, exposed=False)
    scope = resolve_published_scope(_snapshot(exposed, other), _piece_excluded_scope())
    assert _entry(exposed, scope)["effective_state"] == "include"
    assert _entry(other, scope)["effective_state"] == "exclude"
    piece = scope["pieces"][0]
    assert piece["home_perimetre"] == "Exclue"  # état de la pièce lui-même inchangé
    assert piece["counts"]["exceptions"] == 1


def test_scope_explicit_equipment_include_in_excluded_piece_keeps_existing_source():
    eq = _eq(exposed=False)
    entry = _entry(eq, resolve_published_scope(
        _snapshot(eq), _piece_excluded_scope(equipements={str(eq.id): {"raw_state": "include", "source": "user"}})
    ))
    assert entry["decision_source"] == "exception_equipement"


# --- Sync / « Publier » / aperçu : même calcul (AC1, AC12) -------------------

def _cmd(cmd_id, generic_type, type_="action", sub_type="other"):
    return {"id": cmd_id, "name": f"cmd {cmd_id}", "generic_type": generic_type, "type": type_,
            "sub_type": sub_type}


def _eq_raw(eq_id, *, exposed, enabled=True, excluded=None):
    eq = {
        "id": eq_id, "name": f"EQ {eq_id}", "object_id": PIECE, "is_enable": enabled, "is_visible": True,
        "eq_type": "virtual", "is_excluded": excluded is not None, "status": {"timeout": 0},
        "homekit_exposed": exposed, "homekit_exposed_source": "equipement",
        "cmds": [_cmd(eq_id * 10 + 1, "LIGHT_ON"), _cmd(eq_id * 10 + 2, "LIGHT_OFF"),
                 _cmd(eq_id * 10 + 3, "LIGHT_STATE", "info", "binary")],
    }
    if excluded:
        eq["exclusion_source"] = excluded
    return eq


def _payload():
    return {
        "timestamp": "2026-10-21T00:00:00Z",
        "objects": [{"id": PIECE, "name": "Zone générique"}],
        "eq_logics": [
            _eq_raw(501, exposed=True, excluded="object"),                  # relevé
            _eq_raw(502, exposed=False, excluded="object"),                 # reste exclu
            _eq_raw(503, exposed=None, excluded="object"),                  # signal inconnu
            _eq_raw(165, exposed=True, enabled=False, excluded="object"),   # désactivé : non relevé
            _eq_raw(550, exposed=True, excluded="eqlogic"),                 # exclusion explicite
        ],
        "scenarios": [],
        "scenarios_complete": True,
        "sync_config": {"confidence_policy": "sure_probable"},
    }


def _body(payload):
    return {"action": "sync", "payload": payload, "request_id": "t24-4", "timestamp": "2026-10-21T00:00:00Z"}


@pytest.fixture
def app(tmp_path):
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    application = create_app(local_secret=SECRET)
    application["data_dir"] = str(tmp_path)
    application["mqtt_bridge"] = bridge
    application["plugin_version"] = "9.9.9"
    return application


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _row(doc, eq_id):
    return next(r for r in doc["equipments"] if r["eq_id"] == eq_id)


async def test_sync_publier_and_export_agree(cli, app, tmp_path):
    payload = _payload()
    resp = await cli.post("/action/sync", json=_body(payload), headers=HEADERS)
    assert resp.status == 200
    doc = json.loads((tmp_path / dx.EXPORT_FILENAME).read_text(encoding="utf-8"))

    # Même calcul que le résolveur et l'éligibilité partagés (point de calcul unique).
    snapshot = TopologySnapshot.from_jeedom_payload(payload)
    scope = resolve_published_scope(snapshot, {})
    states = {e["eq_id"]: e for e in scope["equipements"]}
    assert states[501]["decision_source"] == "exception_homekit"
    for eq_id in (502, 503, 165, 550):
        assert states[eq_id]["effective_state"] == "exclude"

    assert _row(doc, 501)["decision"] == "published"
    assert _row(doc, 501)["reason"] != "excluded_object"
    assert _row(doc, 502)["reason"] == "excluded_object"
    assert _row(doc, 503)["reason"] == "excluded_object"
    assert _row(doc, 165)["reason"] == "excluded_object"  # AC12 / Q4-4
    assert _row(doc, 550)["reason"] == "excluded_eqlogic"  # AC3
    # AC5 : chaque commande de l'équipement exposé a une raison non vide.
    assert all(c["reason"] for c in _row(doc, 501)["commands"])
    assert all(c["reason"] for c in doc["equipments"][0]["commands"])

    # « Publier » : mêmes verdicts.
    before = {r["eq_id"]: (r["decision"], r["reason"]) for r in doc["equipments"]}
    resp = await cli.post("/action/execute",
                          json={"intention": "publier", "portee": "global", "selection": ["all"]},
                          headers=HEADERS)
    assert resp.status == 200
    doc2 = json.loads((tmp_path / dx.EXPORT_FILENAME).read_text(encoding="utf-8"))
    after = {r["eq_id"]: (r["decision"], r["reason"]) for r in doc2["equipments"]}
    assert after[501][0] == "published"
    for eq_id in (502, 503, 165, 550):
        assert after[eq_id][0] == "not_published"
        assert after[eq_id][1] == before[eq_id][1]


async def test_published_scope_route_matches_resolver(cli):
    payload = _payload()
    await cli.post("/action/sync", json=_body(payload), headers=HEADERS)
    resp = await cli.get("/system/published_scope", headers=HEADERS)
    assert resp.status == 200
    body = await resp.json()
    entries = {e["eq_id"]: e for e in body["payload"]["equipements"]}
    assert entries[501]["decision_source"] == "exception_homekit"
    assert entries[501]["is_exception"] is True
    assert entries[165]["is_exception"] is False


# --- Export (AC11) ---------------------------------------------------------

async def test_export_four_truth_table_lines_and_unchanged_fields(cli, tmp_path):
    payload = _payload()
    payload["eq_logics"] = [
        _eq_raw(1, exposed=True),                    # true / true  -> true
        _eq_raw(2, exposed=False),                   # true / false -> false
        _eq_raw(3, exposed=None),                    # true / null  -> null
        _eq_raw(165, exposed=True, enabled=False),   # false / true -> false (cas de la baseline)
        _eq_raw(550, exposed=True, enabled=False, excluded="object"),
    ]
    payload["scenarios"] = [
        {"id": 7, "name": "sc", "is_active": True, "homekit_exposed": True},
        {"id": 8, "name": "sc", "is_active": False, "homekit_exposed": True},
    ]
    await cli.post("/action/sync", json=_body(payload), headers=HEADERS)
    doc = json.loads((tmp_path / dx.EXPORT_FILENAME).read_text(encoding="utf-8"))
    assert doc["schema_version"] == 1
    assert [_row(doc, i)["homekit_exposed_effective"] for i in (1, 2, 3, 165, 550)] == [
        True, False, None, False, False]
    # le réglage et sa provenance gardent leur sens
    assert _row(doc, 165)["homekit_exposed"] is True
    assert _row(doc, 165)["enabled"] is False
    assert _row(doc, 165)["homekit_exposed_source"] == "equipement"
    sc = {r["scenario_id"]: r for r in doc["scenarios"]}
    assert sc[7]["homekit_exposed_effective"] is True
    assert sc[8]["homekit_exposed_effective"] is False and sc[8]["homekit_exposed"] is True
