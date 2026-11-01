"""Story 24.6 — classement ``parity_class`` / ``parity_alert`` des ventilateurs et aspirateurs.

Identifiants numériques factices et libellés génériques uniquement (CC-48).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from export import decision_export as dx
from transport.http_server import create_app

SECRET = "test-secret-24-6-sentinelle"
HEADERS = {"X-Local-Secret": SECRET}
PIECE = 10
DAEMON_ROOT = Path(__file__).resolve().parents[2]

FE = dx.PARITY_CLASS_FUNCTIONAL_EQUIVALENT
ALERT = dx.PARITY_ALERT_FAN_SPEED_PRESENT


# --- Fonction pure (D1, D2) --------------------------------------------------

def _row(generic_type, decision="published", ha_type="switch"):
    return {"generic_type": generic_type, "decision": decision, "ha_type": ha_type}


FAN_TRIO = [_row("FAN_STATE"), _row("FAN_ON"), _row("FAN_OFF")]


def test_constants_are_the_documented_values():
    assert FE == "functional_equivalent"
    assert ALERT == "fan_speed_present"


@pytest.mark.parametrize("effective", [False, None])
def test_not_effectively_exposed_is_null_without_alert(effective):
    assert dx.compute_parity_class(effective, FAN_TRIO) == (None, None)
    assert dx.compute_parity_class(effective, FAN_TRIO + [_row("FAN_SPEED", "not_published", None)]) == (None, None)


def test_exposed_fan_trio_published_in_switch_is_functional_equivalent():
    assert dx.compute_parity_class(True, FAN_TRIO) == (FE, None)


def test_vacuum_with_battery_is_functional_equivalent():
    rows = FAN_TRIO + [_row("BATTERY", ha_type="sensor")]
    assert dx.compute_parity_class(True, rows) == (FE, None)


@pytest.mark.parametrize("single", ["FAN_STATE", "FAN_ON", "FAN_OFF"])
def test_one_fan_command_published_in_switch_is_enough(single):
    rows = [_row(gt, "not_published", None) for gt in ("FAN_STATE", "FAN_ON", "FAN_OFF") if gt != single]
    rows.append(_row(single))
    assert dx.compute_parity_class(True, rows) == (FE, None)


@pytest.mark.parametrize("speed", ["FAN_SPEED", "FAN_SPEED_STATE", "ROTATION", "ROTATION_STATE"])
@pytest.mark.parametrize("decision,ha_type", [("published", "sensor"), ("not_published", None)])
def test_speed_type_on_exposed_equipment_raises_alert(speed, decision, ha_type):
    rows = FAN_TRIO + [_row(speed, decision, ha_type)]
    assert dx.compute_parity_class(True, rows) == (None, ALERT)


def test_speed_without_fan_trio_still_raises_alert():
    assert dx.compute_parity_class(True, [_row("ROTATION", "not_published", None)]) == (None, ALERT)


def test_fan_trio_not_published_is_null():
    rows = [_row(gt, "not_published", None) for gt in ("FAN_STATE", "FAN_ON", "FAN_OFF")]
    assert dx.compute_parity_class(True, rows) == (None, None)


def test_fan_trio_published_in_another_domain_is_null():
    # un override de type qui sortirait le trio de `switch` n'est plus un équivalent de switch
    rows = [_row(gt, ha_type="light") for gt in ("FAN_STATE", "FAN_ON", "FAN_OFF")]
    assert dx.compute_parity_class(True, rows) == (None, None)


@pytest.mark.parametrize("family", [
    ["SWITCH_STATE", "SWITCH_ON", "SWITCH_OFF"],
    ["LIGHT_STATE", "LIGHT_ON", "LIGHT_OFF"],
    ["DOCK_STATE", "DOCK"],
])
def test_other_families_are_null(family):
    assert dx.compute_parity_class(True, [_row(gt) for gt in family]) == (None, None)


def test_no_commands_is_null():
    assert dx.compute_parity_class(True, []) == (None, None)


# --- Export de bout en bout (AC1, AC4, AC5) ---------------------------------

def _cmd(cmd_id, generic_type, type_="action", sub_type="other"):
    return {"id": cmd_id, "name": f"cmd {cmd_id}", "generic_type": generic_type, "type": type_,
            "sub_type": sub_type}


def _fan_cmds(eq_id):
    return [
        _cmd(eq_id * 10 + 1, "FAN_STATE", "info", "binary"),
        _cmd(eq_id * 10 + 2, "FAN_ON"),
        _cmd(eq_id * 10 + 3, "FAN_OFF"),
    ]


def _eq_raw(eq_id, cmds, *, exposed, enabled=True, excluded=None, eq_type="virtual"):
    eq = {
        "id": eq_id, "name": f"EQ {eq_id}", "object_id": PIECE, "is_enable": enabled, "is_visible": True,
        "eq_type": eq_type, "is_excluded": excluded is not None, "status": {"timeout": 0},
        "homekit_exposed": exposed, "homekit_exposed_source": "equipement", "cmds": cmds,
    }
    if excluded:
        eq["exclusion_source"] = excluded
    return eq


def _payload():
    return {
        "timestamp": "2026-11-01T00:00:00Z",
        "objects": [{"id": PIECE, "name": "Zone générique"}],
        "eq_logics": [
            _eq_raw(601, _fan_cmds(601), exposed=True, eq_type="pool"),           # ventilateur sans vitesse
            _eq_raw(602, _fan_cmds(602) + [_cmd(6024, "BATTERY", "info", "numeric")],
                    exposed=True),                                                # aspirateur avec batterie
            _eq_raw(603, _fan_cmds(603), exposed=True, enabled=False,
                    excluded="object"),                                           # désactivé exposé (forme 165)
            _eq_raw(604, _fan_cmds(604) + [_cmd(6044, "FAN_SPEED", "action", "slider")],
                    exposed=True),                                                # ventilateur à vitesse
            _eq_raw(605, _fan_cmds(605), exposed=False),                          # non exposé
            _eq_raw(606, _fan_cmds(606), exposed=None),                           # exposition inconnue
            _eq_raw(607, _fan_cmds(607), exposed=True, excluded="eqlogic"),       # non publié
            _eq_raw(608, [_cmd(6081, "SWITCH_STATE", "info", "binary"), _cmd(6082, "SWITCH_ON"),
                          _cmd(6083, "SWITCH_OFF")], exposed=True),               # autre famille
            _eq_raw(609, _fan_cmds(609) + [_cmd(6094, "ROTATION_STATE", "info", "numeric")],
                    exposed=False),                                               # vitesse, non exposé
            _eq_raw(610, _fan_cmds(610) + [_cmd(6104, "ROTATION", "action", "slider")],
                    exposed=True, enabled=False),                                 # vitesse, exposition non effective
        ],
        "scenarios": [{"id": 7, "name": "sc", "is_active": True, "homekit_exposed": True}],
        "scenarios_complete": True,
        "sync_config": {"confidence_policy": "sure_probable"},
    }


def _body(payload):
    return {"action": "sync", "payload": payload, "request_id": "t24-6", "timestamp": "2026-11-01T00:00:00Z"}


@pytest.fixture
def bridge():
    mock = MagicMock()
    mock.is_connected = True
    mock.publish_message = MagicMock(return_value=True)
    return mock


@pytest.fixture
def app(tmp_path, bridge):
    application = create_app(local_secret=SECRET)
    application["data_dir"] = str(tmp_path)
    application["mqtt_bridge"] = bridge
    application["plugin_version"] = "9.9.9"
    return application


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


async def _export(cli, tmp_path):
    resp = await cli.post("/action/sync", json=_body(_payload()), headers=HEADERS)
    assert resp.status == 200
    return json.loads((tmp_path / dx.EXPORT_FILENAME).read_text(encoding="utf-8"))


def _rows(doc):
    return {r["eq_id"]: r for r in doc["equipments"]}


async def test_export_parity_class_on_every_equipment(cli, tmp_path):
    doc = await _export(cli, tmp_path)
    assert doc["schema_version"] == 1
    rows = _rows(doc)
    assert all("parity_class" in r for r in rows.values())
    assert {eq_id: r["parity_class"] for eq_id, r in rows.items()} == {
        601: FE, 602: FE,
        603: None, 604: None, 605: None, 606: None, 607: None, 608: None, 609: None, 610: None,
    }
    # pas de champ de parité sur les scénarios (D1)
    assert all("parity_class" not in s and "parity_alert" not in s for s in doc["scenarios"])


async def test_export_parity_alert_only_on_exposed_speed_equipment(cli, tmp_path):
    rows = _rows(await _export(cli, tmp_path))
    assert rows[604]["parity_alert"] == ALERT
    assert [eq_id for eq_id, r in rows.items() if "parity_alert" in r] == [604]


async def test_functional_equivalents_stay_switch(cli, tmp_path):
    # AC5 / AC3 : ventilateur et aspirateur restent publiés en `switch`, aucun `fan` ni `vacuum`
    rows = _rows(await _export(cli, tmp_path))
    for eq_id in (601, 602):
        assert rows[eq_id]["decision"] == "published"
        fan_types = {c["ha_type"] for c in rows[eq_id]["commands"] if c["generic_type"].startswith("FAN_")}
        assert fan_types == {"switch"}
    all_types = {e["ha_type"] for r in rows.values() for e in r["entities"]}
    assert not all_types & {"fan", "vacuum"}


async def test_disabled_exposed_equipment_keeps_its_decision(cli, tmp_path):
    row = _rows(await _export(cli, tmp_path))[603]
    assert row["homekit_exposed"] is True
    assert row["homekit_exposed_effective"] is False
    assert row["decision"] == "not_published"
    assert row["parity_class"] is None and "parity_alert" not in row


# --- Non-régression (AC3) ----------------------------------------------------

async def test_mqtt_publications_do_not_depend_on_parity_class(cli, tmp_path, bridge, monkeypatch):
    await _export(cli, tmp_path)
    reference = [c.args for c in bridge.publish_message.call_args_list]
    assert reference  # le premier sync publie bien la découverte

    bridge.publish_message.reset_mock()
    monkeypatch.setattr(dx, "compute_parity_class", lambda *_a, **_k: (None, None))
    await _export(cli, tmp_path)
    assert [c.args for c in bridge.publish_message.call_args_list] == reference


def test_parity_class_is_read_only_outside_the_export():
    # seul l'export appelle le classement : ni mapping, ni publication, ni périmètre
    offenders = []
    for path in DAEMON_ROOT.rglob("*.py"):
        if "tests" in path.parts or path.name == "decision_export.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        if "compute_parity_class" in names:
            offenders.append(path.name)
    assert offenders == []
