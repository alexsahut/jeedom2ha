"""Story 19.3 — AC1 (CC-03) : la surface affiche le VRAI statut d'une commande, pas un
statut optimiste qui ignore une cause amont.

Trois causes distinctes doivent se refléter fidèlement dans `diagnostic.publication_reason`
et `diagnostic.should_publish` du triptyque (`GET /system/mapping_overrides/{eq_id}`) :
  a. équipement exclu par l'éligibilité amont (Story 4.3, CC-03 historique) ;
  b. override de publication utilisateur (exclusion équipement, Story 16.3) ;
  c. politique de confiance `sure_only` (Story 4.3) qui bloque un mapping `probable`.

Avant Story 19.3, `_build_mapping_override_tree` rejouait sa propre logique d'affichage au
lieu de consommer `evaluate_equipment()` — une cause amont pouvait être ignorée et la
surface annonçait « sera publié » à tort (CC-03).
"""

import pytest

from transport.http_server import create_app
from mapping.overrides import save_equipment_override
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd,
)

SECRET = "test_secret_19_3_ac1"


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


def _excluded_light(eq_id=90100):
    """Lampe exclue par l'utilisateur (Story 4.3) — exclusion_source="eqlogic"."""
    eq = JeedomEqLogic(
        id=eq_id, name="Lampe exclue", object_id=1, eq_type_name="light",
        is_excluded=True, exclusion_source="eqlogic",
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


# ---------------------------------------------------------------------------
# (a) Éligibilité amont négative (exclusion utilisateur)
# ---------------------------------------------------------------------------

async def test_tree_reflects_upstream_eligibility_exclusion(cli, app, tmp_path):
    """Un eqLogic exclu (Story 4.3) n'affiche jamais "sera publié" : chaque commande porte
    should_publish=False et publication_reason="excluded_eqlogic" (pas un diagnostic vide
    ni un statut optimiste)."""
    snapshot, eq = _excluded_light()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    resp = await cli.get(f"/system/mapping_overrides/{eq.id}", headers=_headers())
    assert resp.status == 200
    payload = (await resp.json())["payload"]

    assert payload["mapped"] is False
    for cmd in eq.cmds:
        row = _row(payload, cmd.id)
        assert row["diagnostic"] is not None
        assert row["diagnostic"]["should_publish"] is False
        assert row["diagnostic"]["publication_reason"] == "excluded_eqlogic"


# ---------------------------------------------------------------------------
# (b) Override de publication utilisateur (exclusion équipement, Story 16.3)
# ---------------------------------------------------------------------------

async def test_tree_reflects_equipment_publication_override_exclude(cli, app, tmp_path):
    """Un équipement éligible et mappé (sure), mais exclu par un override équipement
    persisté, affiche should_publish=False / publication_reason="publication_excluded_eqlogic"
    sur ses commandes couvertes — pas le statut "sure" natif optimiste."""
    snapshot, eq = _plain_light()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    save_equipment_override(eq.id, {"publication_override": "exclude"}, str(tmp_path))

    resp = await cli.get(f"/system/mapping_overrides/{eq.id}", headers=_headers())
    assert resp.status == 200
    payload = (await resp.json())["payload"]

    assert payload["mapped"] is True
    on_cmd_id = eq.cmds[0].id
    row = _row(payload, on_cmd_id)
    assert row["covered"] is True
    assert row["diagnostic"]["should_publish"] is False
    assert row["diagnostic"]["publication_reason"] == "publication_excluded_eqlogic"


# ---------------------------------------------------------------------------
# (c) Politique de confiance `sure_only` bloque un mapping `probable`
# ---------------------------------------------------------------------------

async def test_tree_respects_sure_only_confidence_policy(cli, app, tmp_path):
    """Un équipement dont le mapping natif est `probable` (corpus doré, eq 583 "IQ EV
    Charger") est publié en politique par défaut mais bloqué en `sure_only` — la surface
    doit refléter la politique APPLIQUÉE (état du dernier sync), pas un optimisme par défaut."""
    import json
    from pathlib import Path
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures" / "golden_corpus"
    corpus_payload = json.loads((fixtures_dir / "sync_payload.json").read_text(encoding="utf-8"))
    golden_snapshot = TopologySnapshot.from_jeedom_payload(corpus_payload)
    app["topology"] = golden_snapshot
    app["data_dir"] = str(tmp_path)
    ev_charger_cmd_id = 5997  # "Charge On", couvert par le mapping switch probable

    app["confidence_policy"] = "sure_probable"
    resp = await cli.get("/system/mapping_overrides/583", headers=_headers())
    payload = (await resp.json())["payload"]
    row = _row(payload, ev_charger_cmd_id)
    assert row["diagnostic"]["should_publish"] is True
    assert row["diagnostic"]["publication_reason"] == "probable"

    app["confidence_policy"] = "sure_only"
    resp = await cli.get("/system/mapping_overrides/583", headers=_headers())
    payload = (await resp.json())["payload"]
    row = _row(payload, ev_charger_cmd_id)
    assert row["diagnostic"]["should_publish"] is False
    assert row["diagnostic"]["publication_reason"] == "probable_skipped"
