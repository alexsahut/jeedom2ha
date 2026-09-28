"""Story 19.3 — corrections après relecture ClaudeBox (PR #176, reprise 1).

Les deux défauts bloquants ci-dessous n'apparaissent QU'avec le corpus doré complet
(59 équipements, `tests/fixtures/golden_corpus/sync_payload.json`) : un équipement
synthétique isolé ne les révèle pas, d'où leur absence des tests existants de la story.

P1-a (AC2/AC7) : `POST /system/overrides/preview` était muet (`auto: None`,
`overridden: None`, `covered` absent) pour un équipement inéligible ou sans mapping —
branche `auto_evaluation.mapping is None` de `_handle_overrides_preview`
(`transport/http_server.py`). Fix : `_view_for_ineligible_or_unmapped` expose la même vue
que le `diagnostic` de l'arbre pour cette commande (raison d'éligibilité,
`should_publish:false`) ; `auto` et `overridden` partagent la même vue puisqu'aucun
override ne peut changer une décision déjà tranchée au niveau 1/2 (I4).

P1-b : les commandes d'action (On/Off) des interrupteurs secondaires étaient
`covered:false` avec un diagnostic incohérent (`should_publish:true`,
`ha_entity_type:null`) — `_secondary_mapping_by_cmd` n'indexait que la commande d'état de
chaque secondaire (`reason_details["cmd_id"]`), jamais ses commandes d'action présentes
dans `secondary.commands`. Fix : indexation via `mapping_cmd_ids(secondary)`, la même
extraction que le primaire (`mapping/overrides.py`).
"""

import json
import re
from pathlib import Path

import pytest

from transport.http_server import create_app
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd,
)

SECRET = "test_secret_19_3_fix1"

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "golden_corpus"
SYNC_FIXTURE_PATH = FIXTURES_DIR / "sync_payload.json"

DESKTOP_JS_PATH = (
    Path(__file__).resolve().parents[4] / "desktop" / "js" / "jeedom2ha_mapping_override.js"
)


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _headers():
    return {"X-Local-Secret": SECRET}


def _golden_snapshot():
    payload = json.loads(SYNC_FIXTURE_PATH.read_text(encoding="utf-8"))
    return TopologySnapshot.from_jeedom_payload(payload)


def _reason_labels_from_js():
    """Extrait les clés de `REASON_LABELS` directement du fichier JS source (même méthode
    que `test_story_19_3_ac7_no_silent_diagnostic.py` : pas de duplication de la liste)."""
    text = DESKTOP_JS_PATH.read_text(encoding="utf-8")
    start = text.index("var REASON_LABELS = {")
    end = text.index("\n  };", start)
    block = text[start:end]
    return set(re.findall(r"^\s*(\w+):\s*'", block, flags=re.MULTILINE))


async def _tree(cli, eq_id):
    resp = await cli.get(f"/system/mapping_overrides/{eq_id}", headers=_headers())
    assert resp.status == 200, f"eq {eq_id} : statut HTTP inattendu {resp.status}"
    return (await resp.json())["payload"]


async def _preview(cli, eq_id, cmd_id, ha_entity_type):
    resp = await cli.post(
        "/system/overrides/preview",
        headers=_headers(),
        json={
            "payload": {
                "jeedom_eq_id": eq_id,
                "jeedom_cmd_id": cmd_id,
                "ha_entity_type": ha_entity_type,
            }
        },
    )
    assert resp.status == 200, f"eq {eq_id} cmd {cmd_id} : statut HTTP inattendu {resp.status}"
    return (await resp.json())["payload"]


# ---------------------------------------------------------------------------------------
# Test 1 (AC2) — corpus doré complet : cohérence aperçu/arbre par commande
# ---------------------------------------------------------------------------------------

async def test_golden_59_preview_auto_matches_tree_diagnostic_and_covered(cli, app, tmp_path):
    """Pour chacun des 59 équipements du corpus doré et chacune de ses commandes, l'aperçu
    (proposé avec le type natif de la commande, ou `sensor` si elle n'en a pas) renvoie un
    `auto` égal au `diagnostic` de l'arbre pour cette commande, et le même `covered`."""
    snapshot = _golden_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    mismatches = []
    for eq_id in snapshot.eq_logics:
        tree_payload = await _tree(cli, eq_id)
        for row in tree_payload["commands"]:
            cmd_id = row["jeedom_cmd_id"]
            native_type = row["diagnostic"]["ha_entity_type"] or row.get("attendu_ha") or "sensor"
            preview_payload = await _preview(cli, eq_id, cmd_id, native_type)

            if preview_payload["covered"] != row["covered"]:
                mismatches.append(
                    (eq_id, cmd_id, "covered", preview_payload["covered"], row["covered"])
                )
            if preview_payload["auto"] != row["diagnostic"]:
                mismatches.append(
                    (eq_id, cmd_id, "auto_vs_diagnostic", preview_payload["auto"], row["diagnostic"])
                )

    assert mismatches == [], f"{len(mismatches)} écart(s) aperçu/arbre : {mismatches[:10]}"


# ---------------------------------------------------------------------------------------
# Test 2 — corpus doré complet : invariants de cohérence covered/should_publish/labels
# ---------------------------------------------------------------------------------------

async def test_golden_59_invariants_covered_should_publish_and_reason_labels(cli, app, tmp_path):
    """Sur les 59 équipements du corpus doré : aucune ligne `covered:false` avec un
    diagnostic publié (`should_publish:true`), aucune ligne `should_publish:true` avec
    `ha_entity_type:null`, et chaque `publication_reason` bloquant a un libellé dans
    `REASON_LABELS` (même restriction aux raisons de blocage que
    `test_story_19_3_ac7_no_silent_diagnostic.py` : les raisons de succès `sure`/`probable`
    n'ont jamais de libellé, elles ne sont jamais affichées comme un refus)."""
    snapshot = _golden_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    labels = _reason_labels_from_js()

    uncovered_but_published = []
    published_without_type = []
    unlabeled_blocking_reasons = []
    for eq_id in snapshot.eq_logics:
        tree_payload = await _tree(cli, eq_id)
        for row in tree_payload["commands"]:
            diag = row["diagnostic"]
            if row["covered"] is False and diag["should_publish"] is True:
                uncovered_but_published.append((eq_id, row["jeedom_cmd_id"]))
            if diag["should_publish"] is True and diag["ha_entity_type"] is None:
                published_without_type.append((eq_id, row["jeedom_cmd_id"]))
            if diag["should_publish"] is False and diag["publication_reason"] not in labels:
                unlabeled_blocking_reasons.append(
                    (eq_id, row["jeedom_cmd_id"], diag["publication_reason"])
                )

    assert uncovered_but_published == [], (
        f"lignes covered:false avec diagnostic publié : {uncovered_but_published}"
    )
    assert published_without_type == [], (
        f"lignes should_publish:true avec ha_entity_type:null : {published_without_type}"
    )
    assert unlabeled_blocking_reasons == [], (
        f"raisons de blocage sans libellé français : {unlabeled_blocking_reasons}"
    )


# ---------------------------------------------------------------------------------------
# Test 3 — cas unitaires
# ---------------------------------------------------------------------------------------

async def test_unit_preview_disabled_equipment_exposes_eligibility_reason(cli, app, tmp_path):
    """P1-a : eq 5000 (« Ineligible disabled » du corpus doré) — `auto` et `overridden`
    exposent la raison d'éligibilité, jamais `None`."""
    snapshot = _golden_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    eq = snapshot.eq_logics[5000]
    cmd_id = eq.cmds[0].id
    payload = await _preview(cli, 5000, cmd_id, "switch")

    assert payload["mapped"] is False
    assert payload["covered"] is False
    for view in (payload["auto"], payload["overridden"]):
        assert view is not None
        assert view["should_publish"] is False
        assert view["publication_reason"] == "disabled_eqlogic"
        assert view["projection_validity"]["reason_code"] == "disabled_eqlogic"


async def test_unit_preview_excluded_equipment_exposes_eligibility_reason(cli, app, tmp_path):
    """P1-a : eq 5001 (« Ineligible excluded » du corpus doré) — `auto` et `overridden`
    exposent la raison d'éligibilité, jamais `None`."""
    snapshot = _golden_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    eq = snapshot.eq_logics[5001]
    cmd_id = eq.cmds[0].id
    payload = await _preview(cli, 5001, cmd_id, "switch")

    assert payload["mapped"] is False
    assert payload["covered"] is False
    for view in (payload["auto"], payload["overridden"]):
        assert view is not None
        assert view["should_publish"] is False
        assert view["publication_reason"] == "excluded_eqlogic"
        assert view["projection_validity"]["reason_code"] == "excluded_eqlogic"


def _eq628_two_groups():
    """Copie réduite (2 groupes suffisent à produire un secondaire, vérifié empiriquement)
    de la fixture eq628 multi-switch (Story 11.3/19.2,
    `test_story_19_2_decouplage_state_command_i11.py::_eq628`) : 1 principal (Filtration
    piscine, cmds 5977-5979) + 1 secondaire (Chauffage piscine, cmds 5980-5982)."""
    return JeedomEqLogic(
        id=628, name="Pilotage priorisation solaire", object_id=1, eq_type_name="virtual",
        cmds=[
            JeedomCmd(id=5977, name="Filtration piscine", type="info", sub_type="binary",
                      generic_type="SWITCH_STATE", current_value="1"),
            JeedomCmd(id=5978, name="Filtration piscine On", type="action", sub_type="other",
                      generic_type="SWITCH_ON"),
            JeedomCmd(id=5979, name="Filtration piscine Off", type="action", sub_type="other",
                      generic_type="SWITCH_OFF"),
            JeedomCmd(id=5980, name="Chauffage piscine", type="info", sub_type="binary",
                      generic_type="SWITCH_STATE", current_value="0"),
            JeedomCmd(id=5981, name="Chauffage piscine On", type="action", sub_type="other",
                      generic_type="SWITCH_ON"),
            JeedomCmd(id=5982, name="Chauffage piscine Off", type="action", sub_type="other",
                      generic_type="SWITCH_OFF"),
        ],
    )


async def test_unit_eq628_secondary_on_command_covered_as_switch(cli, app, tmp_path):
    """P1-b : la commande On (5981) du secondaire (Chauffage piscine, eq 628) est
    `covered:true` avec `ha_entity_type:"switch"` — pas `covered:false`/`ha_entity_type:null`
    (routage prouvé par la Story 19.2 : `jeedom2ha/628/5980/set` exécute 5981)."""
    eq = _eq628_two_groups()
    snapshot = TopologySnapshot(
        timestamp="2026-09-28T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Energie")},
        eq_logics={eq.id: eq},
    )
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    tree_payload = await _tree(cli, 628)
    row = next(r for r in tree_payload["commands"] if r["jeedom_cmd_id"] == 5981)
    assert row["covered"] is True
    assert row["diagnostic"]["ha_entity_type"] == "switch"

    preview_payload = await _preview(cli, 628, 5981, "switch")
    assert preview_payload["covered"] is True
    assert preview_payload["auto"]["ha_entity_type"] == "switch"
