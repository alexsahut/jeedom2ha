"""Story 25.8 (AC17, AC19, Q1 B) — `present_in_ha` rejoint la liste blanche des entités de la route agrégée.

Le chiffre « N entités seront retirées de Home Assistant » de la confirmation d'exclusion de pièce est le nombre
d'entités présentes (`present_in_ha`) des équipements de la pièce : sans ce champ la route agrégée ne dit pas ce qui est
réellement dans Home Assistant. C'est un ajout de champ ; la règle de priorité (D1) et le constructeur d'arbre ne
changent pas : la valeur est celle du GET unitaire, projetée sans recalcul. Corpus fictif de 25.2 (CC-48)."""

from __future__ import annotations

import pytest
from transport.http_server import create_app

from .story_25_2_corpus import PUBLISHED_IN_HA, build_corpus_topology, populate_app

SECRET = "test_secret"
H = {"X-Local-Secret": SECRET}
EQ_IDS = sorted(build_corpus_topology().eq_logics)


@pytest.fixture
def app(tmp_path):
    app = create_app(local_secret=SECRET)
    populate_app(app, tmp_path)
    return app


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


async def _states(cli):
    resp = await cli.get("/system/equipment_states?refresh=1", headers=H)
    assert resp.status == 200
    return (await resp.json())["payload"]["equipments"]


async def _unit(cli, eq_id):
    resp = await cli.get(f"/system/mapping_overrides/{eq_id}", headers=H)
    return (await resp.json())["payload"]


async def test_chaque_entite_porte_present_in_ha_booleen(cli):
    equipments = await _states(cli)
    seen = 0
    for entry in equipments.values():
        for entity in entry["entities"]:
            assert set(entity) == {"override_pending", "present_in_ha"}
            assert isinstance(entity["present_in_ha"], bool)
            seen += 1
    assert seen > 0


@pytest.mark.parametrize("eq_id", EQ_IDS)
async def test_valeur_identique_au_get_unitaire(cli, eq_id):
    equipments = await _states(cli)
    unit = await _unit(cli, eq_id)
    assert [e["present_in_ha"] for e in equipments[str(eq_id)]["entities"]] == \
        [e["present_in_ha"] for e in unit["entities"]]


async def test_entites_presentes_seulement_pour_les_equipements_publies(cli):
    equipments = await _states(cli)
    present_eq = {int(i) for i, entry in equipments.items() if any(e["present_in_ha"] for e in entry["entities"])}
    assert present_eq, "le corpus comporte des entités présentes"
    assert present_eq <= PUBLISHED_IN_HA


async def test_nombre_d_entites_presentes_par_piece_est_deterministe(cli):
    """Ce que la surface annonce : somme des entités présentes des équipements d'une pièce."""
    equipments = await _states(cli)
    topology = build_corpus_topology()
    by_room = {}
    for eq_id, eq in topology.eq_logics.items():
        entry = equipments[str(eq_id)]
        by_room.setdefault(eq.object_id, 0)
        by_room[eq.object_id] += sum(1 for e in entry["entities"] if e["present_in_ha"])
    again = await _states(cli)
    by_room_again = {}
    for eq_id, eq in topology.eq_logics.items():
        by_room_again.setdefault(eq.object_id, 0)
        by_room_again[eq.object_id] += sum(1 for e in again[str(eq_id)]["entities"] if e["present_in_ha"])
    assert by_room == by_room_again
    assert by_room[1] >= 2  # 101 et 102 sont présents dans la pièce 1
