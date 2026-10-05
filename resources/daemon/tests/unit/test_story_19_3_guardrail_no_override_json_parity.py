"""Story 19.3 — Garde-fou (Reprise 2) : pour un équipement SANS override, la réponse
JSON complète de la surface (`GET /system/mapping_overrides/{eq_id}`) et de l'aperçu
(`POST /system/overrides/preview`) est comparée champ par champ à la base pré-story
(`49dc70b`, sonde exécutée hors CI par `git worktree` — non reproduite ici pour rester
indépendant de l'historique git en CI, cf. rapport Reprise 2).

Résultat de la sonde manuelle : **un seul champ diffère**, l'objet `sync_status` (absent
en `49dc70b`, ajouté par AC6) — tous les autres champs (chaque `diagnostic` par commande,
`preview.auto`, `preview.overridden`, `native_generic_types`, `support_export`) sont
strictement identiques bit à bit. Ce test fige cette parité : si un champ préexistant
change de valeur sans que ce test soit mis à jour consciemment, c'est un signal qu'une
régression a été introduite hors du périmètre annoncé de la story (AR9 — aucune
duplication/altération de la logique de décision existante).
"""

import pytest

from transport.http_server import create_app
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd,
)

SECRET = "test_secret_19_3_guardrail"
EQ_ID = 90999


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _headers():
    return {"X-Local-Secret": SECRET}


def _plain_light():
    eq = JeedomEqLogic(
        id=EQ_ID, name="Lampe garde-fou", object_id=1, eq_type_name="light",
        cmds=[
            JeedomCmd(id=EQ_ID * 10 + 1, name="On", type="action", sub_type="other", generic_type="LIGHT_ON"),
            JeedomCmd(id=EQ_ID * 10 + 2, name="Off", type="action", sub_type="other", generic_type="LIGHT_OFF"),
            JeedomCmd(id=EQ_ID * 10 + 3, name="Etat", type="info", sub_type="binary", generic_type="LIGHT_STATE"),
        ],
    )
    snapshot = TopologySnapshot(
        timestamp="2026-09-28T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={EQ_ID: eq},
    )
    return snapshot, eq


_EXPECTED_COMMAND_DIAGNOSTIC = {
    "confidence": "sure",
    "ha_entity_type": "light",
    "projection_validity": {
        "is_valid": True,
        "missing_capabilities": [],
        "missing_fields": [],
        "reason_code": None,
    },
    "publication_reason": "sure",
    "reason_code": "light_on_off_only",
    "should_publish": True,
}


async def test_guardrail_tree_response_identical_to_pre_story_except_sync_status(cli, app, tmp_path):
    """La parité pré-story est conservée, sauf `sync_status` et les ajouts additifs
    de Story 20-2 (`equipment_decision`, `entities`) dont la forme est vérifiée ici."""
    snapshot, eq = _plain_light()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    resp = await cli.get(f"/system/mapping_overrides/{EQ_ID}", headers=_headers())
    payload = (await resp.json())["payload"]

    assert payload["mapped"] is True
    assert payload["eq_name"] == "Lampe garde-fou"
    assert set(payload.keys()) == {
        "jeedom_eq_id", "eq_name", "mapped", "equipment_decision", "entities",
        "sync_status", "commands",
    }
    assert payload["equipment_decision"] == _EXPECTED_COMMAND_DIAGNOSTIC
    assert payload["entities"] == [{
        "ha_entity_type": "light", "decision": _EXPECTED_COMMAND_DIAGNOSTIC,
        "publication_override": None,
        "reason_details": {"on_off": "state+on+off"}, "override_command_id": EQ_ID * 10 + 1,
        "override_pending": True,
    }]

    for row, cmd in zip(payload["commands"], eq.cmds):
        assert set(row.keys()) == {
            "jeedom_cmd_id", "cmd_name", "generic_type", "coverable", "covered",
            "attendu_ha", "effective_ha", "override_applied", "diagnostic",
        }
        assert row["jeedom_cmd_id"] == cmd.id
        assert row["covered"] is True
        assert row["override_applied"] is False
        assert row["attendu_ha"] == "light"
        assert row["effective_ha"] == "light"
        assert row["diagnostic"] == _EXPECTED_COMMAND_DIAGNOSTIC

    # AC6 — seul champ réellement nouveau par rapport à 49dc70b.
    assert payload["sync_status"] == {
        "synced_should_publish": None,
        "current_should_publish": True,
        "override_pending": False,
    }


async def test_guardrail_preview_response_identical_to_pre_story(cli, app, tmp_path):
    """Sonde 49dc70b (Reprise 2) : l'aperçu pour ce même équipement (sans override) est
    strictement identique champ à champ à la base pré-story — aucun champ nouveau, aucun
    champ modifié (AC2 : parité aperçu/surface préservée par le branchement sur
    evaluate_equipment())."""
    snapshot, eq = _plain_light()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    on_cmd_id = eq.cmds[0].id

    resp = await cli.post(
        "/system/overrides/preview",
        headers=_headers(),
        json={"payload": {"jeedom_eq_id": EQ_ID, "jeedom_cmd_id": on_cmd_id, "ha_entity_type": "light"}},
    )
    payload = (await resp.json())["payload"]

    assert set(payload.keys()) == {
        "jeedom_eq_id", "mapped", "covered", "auto", "overridden",
        "native_generic_types", "support_export",
    }
    assert payload["mapped"] is True
    assert payload["covered"] is True
    assert payload["auto"] == _EXPECTED_COMMAND_DIAGNOSTIC
    assert payload["overridden"] == dict(
        _EXPECTED_COMMAND_DIAGNOSTIC,
        type_override={"effective": "light", "native": "light", "source": "preview"},
    )
    assert payload["native_generic_types"] == {
        str(eq.cmds[0].id): "LIGHT_ON",
        str(eq.cmds[1].id): "LIGHT_OFF",
        str(eq.cmds[2].id): "LIGHT_STATE",
    }
    assert payload["support_export"] == {
        "preview_trace": {"effective": "light", "native": "light", "publication_override": None},
        "refusal_reasons": [],
    }
