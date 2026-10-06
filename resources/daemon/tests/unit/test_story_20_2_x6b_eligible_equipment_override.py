"""Story 20.2 — reprise X6b (P2 relecture indépendante PR #215).

Un équipement INÉLIGIBLE n'a ni entité ni commande couverte dans l'arbre GET
(`_build_mapping_override_tree`) : la surface ne peut donc ni savoir qu'il est
inéligible, ni lire un éventuel override de publication équipement déjà posé.
Deux champs additifs à la racine de l'arbre, lus dans la MÊME source que
`evaluate_equipment` (jamais recalculés) :
  - `eligible` : le résultat d'éligibilité déjà évalué en amont.
  - `equipment_publication_override` : la valeur brute persistée
    (`"exclude"` / `"force_publish"` / `None`), avant résolution `_eqlogic`.
"""
import pytest

from mapping.overrides import save_equipment_override
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from transport.http_server import create_app

SECRET = "x6b"


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _headers():
    return {"X-Local-Secret": SECRET}


def _ineligible_eq(eq_id=588):
    """Équipement exclu par plugin (`excluded_plugin`), sans commande ni entité."""
    eq = JeedomEqLogic(id=eq_id, name="x", object_id=1, is_excluded=True, exclusion_source="plugin", cmds=[])
    snapshot = TopologySnapshot(
        timestamp="2026-10-06T00:00:00Z",
        objects={1: JeedomObject(id=1, name="r")},
        eq_logics={eq_id: eq},
    )
    return snapshot, eq


def _eligible_eq_with_entity(eq_id=589):
    """Équipement éligible, avec un mapping connu (lampe) — non-régression : les champs
    additifs ne doivent rien changer au reste de l'arbre quand une entité existe."""
    eq = JeedomEqLogic(id=eq_id, name="y", object_id=1, cmds=[
        JeedomCmd(id=eq_id * 10 + 1, name="Etat", type="info", sub_type="binary", generic_type="LIGHT_STATE"),
    ])
    snapshot = TopologySnapshot(
        timestamp="2026-10-06T00:00:00Z",
        objects={1: JeedomObject(id=1, name="r")},
        eq_logics={eq_id: eq},
    )
    return snapshot, eq


async def test_ineligible_equipment_without_override_exposes_eligible_false_and_null_override(cli, app, tmp_path):
    snapshot, eq = _ineligible_eq()
    app["topology"], app["data_dir"] = snapshot, str(tmp_path)

    resp = await cli.get(f"/system/mapping_overrides/{eq.id}", headers=_headers())
    assert resp.status == 200
    payload = (await resp.json())["payload"]
    assert payload["eligible"] is False
    assert payload["equipment_publication_override"] is None
    # Champs existants de l'arbre inchangés.
    assert payload["mapped"] is False
    assert payload["commands"] == []
    assert payload["entities"] == []


async def test_ineligible_equipment_with_persisted_equipment_override_exposes_raw_value(cli, app, tmp_path):
    snapshot, eq = _ineligible_eq(eq_id=590)
    app["topology"], app["data_dir"] = snapshot, str(tmp_path)
    save_equipment_override(eq.id, {"publication_override": "exclude"}, str(tmp_path))

    resp = await cli.get(f"/system/mapping_overrides/{eq.id}", headers=_headers())
    assert resp.status == 200
    payload = (await resp.json())["payload"]
    assert payload["eligible"] is False
    # Valeur BRUTE persistée ("exclude"), pas la version résolue `_eqlogic` du moteur de
    # publication — la surface fait elle-même le lien avec le veto d'équipement.
    assert payload["equipment_publication_override"] == "exclude"


async def test_eligible_equipment_with_entity_exposes_eligible_true_non_regression(cli, app, tmp_path):
    snapshot, eq = _eligible_eq_with_entity()
    app["topology"], app["data_dir"] = snapshot, str(tmp_path)
    save_equipment_override(eq.id, {"publication_override": "force_publish"}, str(tmp_path))

    resp = await cli.get(f"/system/mapping_overrides/{eq.id}", headers=_headers())
    assert resp.status == 200
    payload = (await resp.json())["payload"]
    assert payload["eligible"] is True
    assert payload["equipment_publication_override"] == "force_publish"
    assert payload["mapped"] is True
    assert len(payload["entities"]) == 1
