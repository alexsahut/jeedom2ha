"""Story 19.3 — AC2 : l'aperçu (`POST /system/overrides/preview`) et la surface
(`GET /system/mapping_overrides/{eq_id}`) sont cohérents pour le même override, et la
`confidence_policy` appliquée vient exclusivement de l'état applicatif du dernier sync
(`app["confidence_policy"]`), jamais du corps de la requête (écart relevé PR #169).

Dev Notes (Story 19.3) — test de conflit inter-commandes : un override TYPE persisté sur
une commande SŒUR (même mapping) ne doit pas l'emporter par accident d'ordre d'itération
sur l'override réellement PROPOSÉ (aperçu) d'une autre commande. Les overrides persistés ne
sont jamais mutés par un appel de preview (lecture seule stricte).
"""

import pytest

from transport.http_server import create_app
from mapping.overrides import save_override, list_overrides
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd,
)

SECRET = "test_secret_19_3_ac2"


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _headers():
    return {"X-Local-Secret": SECRET}


def _row(payload, cmd_id):
    return next(c for c in payload["commands"] if c["jeedom_cmd_id"] == cmd_id)


def _plain_light(eq_id=90200):
    """Lampe éligible et mappée `sure` (switch simple ON/OFF/STATE)."""
    eq = JeedomEqLogic(
        id=eq_id, name="Lampe simple", object_id=1, eq_type_name="light",
        cmds=[
            JeedomCmd(id=eq_id * 10 + 1, name="On", type="action", sub_type="other", generic_type="LIGHT_ON"),
            JeedomCmd(id=eq_id * 10 + 2, name="Off", type="action", sub_type="other", generic_type="LIGHT_OFF"),
            JeedomCmd(id=eq_id * 10 + 3, name="Etat", type="info", sub_type="binary", generic_type="LIGHT_STATE"),
        ],
    )
    snapshot = TopologySnapshot(
        timestamp="2026-09-28T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={eq_id: eq},
    )
    return snapshot, eq


async def _preview(cli, body):
    return await cli.post(
        "/system/overrides/preview", headers=_headers(), json={"payload": body}
    )


# ---------------------------------------------------------------------------
# Cohérence aperçu (vue "auto") / surface, pour le même état persisté
# ---------------------------------------------------------------------------

async def test_ac2_preview_auto_view_matches_tree_diagnostic(cli, app, tmp_path):
    """La vue `auto` du preview (état effectif actuel) est strictement identique au
    diagnostic de la même commande dans le triptyque — même code de décision, jamais deux
    logiques d'affichage divergentes."""
    snapshot, eq = _plain_light()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    on_cmd_id = eq.cmds[0].id

    tree_resp = await cli.get(f"/system/mapping_overrides/{eq.id}", headers=_headers())
    tree_payload = (await tree_resp.json())["payload"]
    tree_diag = _row(tree_payload, on_cmd_id)["diagnostic"]

    preview_resp = await _preview(cli, {
        "jeedom_eq_id": eq.id, "jeedom_cmd_id": on_cmd_id, "ha_entity_type": "light",
    })
    auto = (await preview_resp.json())["payload"]["auto"]

    assert auto["ha_entity_type"] == tree_diag["ha_entity_type"]
    assert auto["should_publish"] == tree_diag["should_publish"]
    assert auto["publication_reason"] == tree_diag["publication_reason"]


# ---------------------------------------------------------------------------
# `confidence_policy` vient de l'app, jamais du payload
# ---------------------------------------------------------------------------

async def test_ac2_confidence_policy_ignores_payload_uses_app_state(cli, app):
    """Un payload de preview qui tente d'imposer sa propre `confidence_policy` est ignoré :
    seule `app["confidence_policy"]` (politique du dernier sync) fait foi. Corpus doré,
    eq 583 "IQ EV Charger" (mapping `probable`)."""
    import json
    from pathlib import Path
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures" / "golden_corpus"
    corpus_payload = json.loads((fixtures_dir / "sync_payload.json").read_text(encoding="utf-8"))
    app["topology"] = TopologySnapshot.from_jeedom_payload(corpus_payload)
    app["confidence_policy"] = "sure_only"

    resp = await _preview(cli, {
        "jeedom_eq_id": 583,
        "jeedom_cmd_id": 5997,
        "ha_entity_type": "switch",
        # Champ intrus : n'existe dans aucun contrat documenté du endpoint et ne doit
        # jamais être lu — la politique appliquée doit rester celle de l'app (sure_only).
        "confidence_policy": "sure_probable",
    })
    assert resp.status == 200
    over = (await resp.json())["payload"]["overridden"]
    assert over["should_publish"] is False
    assert over["publication_reason"] == "probable_skipped"


# ---------------------------------------------------------------------------
# Conflit inter-commandes (Dev Notes, Story 19.3)
# ---------------------------------------------------------------------------

async def test_ac2_proposed_override_wins_over_sibling_persisted_override(cli, app, tmp_path):
    """Un override TYPE persisté sur la commande ON (sœur, même mapping) ne doit pas
    l'emporter sur l'override PROPOSÉ de la commande OFF visée par ce preview — et
    l'override persisté sur ON reste inchangé sur disque après l'appel."""
    snapshot, eq = _plain_light()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    on_cmd_id, off_cmd_id = eq.cmds[0].id, eq.cmds[1].id

    save_override(eq.id, on_cmd_id, {"ha_entity_type": "switch"}, str(tmp_path))
    overrides_before = list_overrides(str(tmp_path))

    resp = await _preview(cli, {
        "jeedom_eq_id": eq.id, "jeedom_cmd_id": off_cmd_id, "ha_entity_type": "cover",
    })
    assert resp.status == 200
    over = (await resp.json())["payload"]["overridden"]

    # Le proposé (OFF → cover) gagne, pas le persisté de la sœur (ON → switch).
    assert over["ha_entity_type"] == "cover"

    overrides_after = list_overrides(str(tmp_path))
    assert overrides_after == overrides_before
