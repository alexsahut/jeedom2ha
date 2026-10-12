"""Story 21.1 (bloc B, CC-47) — résolution par commande d'une commande portée par plusieurs
entités : une entité PUBLIÉE l'emporte sur un principal refusé.

Forme de l'équipement de terrain concerné (identifiants synthétiques, aucun nom réel) : le
principal `switch` ne couvre que l'état (`ENERGY_STATE`, sans ordre On/Off) → `ambiguous`,
refusé ; le chemin multi-entité publie le même état en `binary_sensor` secondaire (`sure`).

Défaut d'AFFICHAGE et de décompte seulement : `command_decisions` n'est lu que par l'arbre et
l'aperçu, jamais par le sync (`equipment_decision` et `secondary_decisions` restent inchangés).
"""

import pytest

from mapping.registry import MapperRegistry
from models.evaluate_equipment import evaluate_equipment, select_covering_decision
from models.topology import (
    JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot, assess_eligibility,
)
from transport.http_server import create_app

SECRET = "test_secret"
STATE_CMD = 9001


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _cmd(cmd_id, name, cmd_type, sub_type, generic_type=None, unit=None, value=None):
    return JeedomCmd(
        id=cmd_id, name=name, type=cmd_type, sub_type=sub_type,
        generic_type=generic_type, unit=unit, current_value=value,
    )


def _snapshot(eq):
    return TopologySnapshot(
        timestamp="2026-10-11T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Zone")},
        eq_logics={eq.id: eq},
    )


def _state_plus_sensors(eq_id=900):
    """Forme « 579 » : état seul (primaire switch refusé) + capteurs, multi-entité."""
    return JeedomEqLogic(
        id=eq_id, name="eq", object_id=1, eq_type_name="type",
        cmds=[
            _cmd(STATE_CMD, "Etat", "info", "binary", "ENERGY_STATE", value="1"),
            _cmd(9002, "Puissance", "info", "numeric", "POWER", "W", 5),
            _cmd(9003, "Autre", "info", "numeric", None, "W", 5),
            _cmd(9004, "Libre", "info", "string", None),
        ],
    )


def _single_state_only(eq_id=901):
    """Équipement à UNE seule entité dont la seule commande est un état sans ordre On/Off."""
    return JeedomEqLogic(
        id=eq_id, name="eq", object_id=1, eq_type_name="type",
        cmds=[_cmd(9101, "Etat", "info", "binary", "ENERGY_STATE", value="1")],
    )


def _evaluate(eq):
    snapshot = _snapshot(eq)
    return evaluate_equipment(
        eq, snapshot, assess_eligibility(eq), mapper_registry=MapperRegistry(),
    ), snapshot


def _decision(evaluation, cmd_id):
    return next(d for d in evaluation.command_decisions if d.cmd_id == cmd_id)


def _headers():
    return {"X-Local-Secret": SECRET}


def _row(payload, cmd_id):
    return next(c for c in payload["commands"] if c["jeedom_cmd_id"] == cmd_id)


# ---------------------------------------------------------------------------
# evaluate_equipment() — décision par commande
# ---------------------------------------------------------------------------

def test_shape_precondition_primary_refused_secondary_published():
    """Garde-fou de la fixture : la forme visée existe bien dans le mapper actuel."""
    evaluation, _ = _evaluate(_state_plus_sensors())
    assert evaluation.mapping.ha_entity_type == "switch"
    assert evaluation.equipment_decision.should_publish is False
    assert evaluation.equipment_decision.reason == "ambiguous_skipped"
    binary = [
        (m, d) for m, d in zip(evaluation.mapping.additional_mappings, evaluation.secondary_decisions)
        if m.ha_entity_type == "binary_sensor"
    ]
    assert len(binary) == 1
    assert binary[0][1].should_publish is True


def test_command_published_by_secondary_beats_refused_primary():
    evaluation, _ = _evaluate(_state_plus_sensors())
    decision = _decision(evaluation, STATE_CMD)
    assert decision.should_publish is True
    assert decision.reason == "sure"
    assert decision.step == "4"


def test_publication_decisions_unchanged_by_resolution():
    """AC9 : la résolution par commande n'altère ni la décision de l'équipement ni celles
    des secondaires (seules lues par le sync)."""
    evaluation, _ = _evaluate(_state_plus_sensors())
    assert evaluation.equipment_decision.should_publish is False
    assert evaluation.equipment_decision.reason == "ambiguous_skipped"
    assert [d.should_publish for d in evaluation.secondary_decisions] == [True, True, True]


def test_no_published_entity_keeps_primary_cause():
    """Équipement à une seule entité, état seul : comportement inchangé (cause du principal)."""
    evaluation, _ = _evaluate(_single_state_only())
    decision = _decision(evaluation, 9101)
    assert decision.should_publish is False
    assert decision.reason == "ambiguous_skipped"


def test_uncovered_command_stays_uncovered():
    evaluation, _ = _evaluate(_state_plus_sensors())
    decision = _decision(evaluation, 9004)
    assert decision.should_publish is False
    assert decision.reason_details == {"covered": False}


def test_select_covering_decision_priority():
    class D:
        def __init__(self, name, publish):
            self.name, self.should_publish = name, publish

    refused, pub_a, pub_b = D("primary", False), D("a", True), D("b", True)
    pick = lambda items: select_covering_decision(items, lambda d: d)  # noqa: E731
    # primaire refusé, deux secondaires publiés : le premier publié (ordre natif)
    assert pick([refused, pub_a, pub_b]) is pub_a
    # primaire publié + secondaire publié : le primaire garde la priorité
    assert pick([pub_b, pub_a]) is pub_b
    # aucune entité publiée : le primaire
    assert pick([refused, D("s", False)]) is refused


# ---------------------------------------------------------------------------
# Arbre et aperçu — cohérents avec la décision par commande
# ---------------------------------------------------------------------------

async def test_tree_row_reflects_published_secondary(cli, app, tmp_path):
    eq = _state_plus_sensors()
    app["topology"] = _snapshot(eq)
    app["data_dir"] = str(tmp_path)
    resp = await cli.get(f"/system/mapping_overrides/{eq.id}", headers=_headers())
    assert resp.status == 200
    payload = (await resp.json())["payload"]

    row = _row(payload, STATE_CMD)
    assert row["covered"] is True
    assert row["attendu_ha"] == "binary_sensor"
    assert row["effective_ha"] == "binary_sensor"
    assert row["diagnostic"]["ha_entity_type"] == "binary_sensor"
    assert row["diagnostic"]["should_publish"] is True
    # Le principal reste refusé dans la vue équipement/entités (rien ne change en publication).
    assert payload["equipment_decision"]["should_publish"] is False
    switch = next(e for e in payload["entities"] if e["ha_entity_type"] == "switch")
    assert switch["decision"]["should_publish"] is False
    assert _row(payload, 9004)["covered"] is False


async def test_tree_single_entity_state_only_unchanged(cli, app, tmp_path):
    eq = _single_state_only()
    app["topology"] = _snapshot(eq)
    app["data_dir"] = str(tmp_path)
    resp = await cli.get(f"/system/mapping_overrides/{eq.id}", headers=_headers())
    row = _row((await resp.json())["payload"], 9101)
    assert row["diagnostic"]["should_publish"] is False
    assert row["diagnostic"]["publication_reason"] == "ambiguous_skipped"
    assert row["diagnostic"]["ha_entity_type"] == "switch"


async def test_preview_targets_published_secondary(cli, app):
    """L'aperçu ciblant la commande partagée évalue l'entité qui la publie (même source)."""
    eq = _state_plus_sensors()
    app["topology"] = _snapshot(eq)
    resp = await cli.post(
        "/system/overrides/preview", headers=_headers(),
        json={"payload": {
            "jeedom_eq_id": eq.id, "jeedom_cmd_id": STATE_CMD, "ha_entity_type": "binary_sensor",
        }},
    )
    assert resp.status == 200
    auto = (await resp.json())["payload"]["auto"]
    assert auto["ha_entity_type"] == "binary_sensor"
    assert auto["should_publish"] is True


# ---------------------------------------------------------------------------
# AC11 (Q4 A) — libellé honnête de la cause « état sans ordre On/Off »
# ---------------------------------------------------------------------------

def test_cause_ux_state_only_label_is_honest():
    from models.cause_mapping import resolve_cause_ux

    for decision_reason in ("ambiguous", "ambiguous_skipped"):
        for step in (3, 4):
            cause = resolve_cause_ux(decision_reason, step, mapping_reason_code="switch_state_orphan")
            assert "rien à piloter" in cause["cause_label"]
            assert "binary_sensor" in cause["cause_action"]
            assert "Forcer" in cause["cause_action"]
            assert "types génériques" not in cause["cause_action"]


def test_cause_ux_other_ambiguities_unchanged():
    from models.cause_mapping import resolve_cause_ux

    for mapping_reason in (None, "switch_duplicate_generic_types", "light_ambiguous"):
        cause = resolve_cause_ux("ambiguous_skipped", 4, mapping_reason_code=mapping_reason)
        assert "types génériques" in cause["cause_action"]
    # sans le paramètre : appel historique inchangé
    assert resolve_cause_ux("ambiguous_skipped", 4) == resolve_cause_ux(
        "ambiguous_skipped", 4, mapping_reason_code=None
    )
