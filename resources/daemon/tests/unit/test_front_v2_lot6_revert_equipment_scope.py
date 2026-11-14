"""Front v2 (Lot 6) — `POST /action/publication_override_revert` avec `scope == "equipment"` :
retire SEULEMENT le réglage de publication de l'équipement, sans toucher aux réglages des
commandes (type HA, publication). Sans `scope`, le retour complet (CC-19) est inchangé.
Données fictives (CC-48)."""

import pytest

from transport.http_server import create_app
from mapping.overrides import (
    save_override, save_equipment_override, list_overrides, list_equipment_overrides,
)
from models.topology import TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd

SECRET = "test_secret_front_v2_lot6"


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _headers():
    return {"X-Local-Secret": SECRET}


def _light(app, tmp_path, eq_id=96100):
    eq = JeedomEqLogic(
        id=eq_id, name="Lampe fictive", object_id=1, eq_type_name="light",
        cmds=[
            JeedomCmd(id=eq_id * 10 + 1, name="On", type="action", sub_type="other", generic_type="LIGHT_ON"),
            JeedomCmd(id=eq_id * 10 + 2, name="Off", type="action", sub_type="other", generic_type="LIGHT_OFF"),
            JeedomCmd(id=eq_id * 10 + 3, name="Etat", type="info", sub_type="binary", generic_type="LIGHT_STATE"),
        ],
    )
    app["topology"] = TopologySnapshot(
        timestamp="2026-11-14T00:00:00Z", objects={1: JeedomObject(id=1, name="Salon")}, eq_logics={eq_id: eq},
    )
    app["data_dir"] = str(tmp_path)
    return eq, str(tmp_path)


async def test_scope_equipment_keeps_command_settings(cli, app, tmp_path):
    eq, data_dir = _light(app, tmp_path)
    save_override(eq.id, eq.cmds[0].id, {"ha_entity_type": "switch"}, data_dir)
    save_override(eq.id, eq.cmds[2].id, {"publication_override": "force_publish"}, data_dir)
    save_equipment_override(eq.id, {"publication_override": "exclude"}, data_dir)
    before = list_overrides(data_dir)

    resp = await cli.post("/action/publication_override_revert", headers=_headers(),
                          json={"payload": {"jeedom_eq_id": eq.id, "scope": "equipment"}})
    assert resp.status == 200
    body = (await resp.json())["payload"]
    assert body == {"jeedom_eq_id": eq.id, "scope": "equipment_publication", "removed": True, "removed_commands": []}
    assert list_overrides(data_dir) == before, "réglages des commandes intacts"
    assert list_equipment_overrides(data_dir) == {}


async def test_scope_equipment_keeps_other_equipment_fields(cli, app, tmp_path):
    eq, data_dir = _light(app, tmp_path)
    save_equipment_override(eq.id, {"publication_override": "exclude", "ha_entity_type": "switch"}, data_dir)
    resp = await cli.post("/action/publication_override_revert", headers=_headers(),
                          json={"payload": {"jeedom_eq_id": eq.id, "scope": "equipment"}})
    assert resp.status == 200
    remaining = list_equipment_overrides(data_dir)[str(eq.id)]
    assert "publication_override" not in remaining and remaining["ha_entity_type"] == "switch"


async def test_scope_equipment_nothing_to_remove(cli, app, tmp_path):
    eq, data_dir = _light(app, tmp_path)
    resp = await cli.post("/action/publication_override_revert", headers=_headers(),
                          json={"payload": {"jeedom_eq_id": eq.id, "scope": "equipment"}})
    assert resp.status == 200
    assert (await resp.json())["payload"]["removed"] is False


@pytest.mark.parametrize("payload, status", [
    ({"jeedom_eq_id": 96100, "scope": "command"}, 400),
    ({"jeedom_eq_id": 96100, "scope": "equipment", "jeedom_cmd_id": 961001}, 400),
    ({"jeedom_eq_id": "96100", "scope": "equipment"}, 400),
    ({"jeedom_eq_id": 1, "scope": "equipment"}, 404),
])
async def test_scope_equipment_invalid(cli, app, tmp_path, payload, status):
    eq, data_dir = _light(app, tmp_path)
    save_override(eq.id, eq.cmds[0].id, {"ha_entity_type": "switch"}, data_dir)
    resp = await cli.post("/action/publication_override_revert", headers=_headers(), json={"payload": payload})
    assert resp.status == status
    assert len(list_overrides(data_dir)) == 1, "rien n'est retiré sur une requête refusée"


async def test_without_scope_canonical_revert_unchanged(cli, app, tmp_path):
    eq, data_dir = _light(app, tmp_path)
    save_override(eq.id, eq.cmds[0].id, {"ha_entity_type": "switch"}, data_dir)
    save_equipment_override(eq.id, {"publication_override": "exclude"}, data_dir)
    resp = await cli.post("/action/publication_override_revert", headers=_headers(),
                          json={"payload": {"jeedom_eq_id": eq.id}})
    assert resp.status == 200
    assert (await resp.json())["payload"]["scope"] == "equipment"
    assert list_overrides(data_dir) == {} and list_equipment_overrides(data_dir) == {}


async def test_scope_equipment_requires_secret(cli, app, tmp_path):
    eq, data_dir = _light(app, tmp_path)
    save_equipment_override(eq.id, {"publication_override": "exclude"}, data_dir)
    resp = await cli.post("/action/publication_override_revert", json={"payload": {"jeedom_eq_id": eq.id, "scope": "equipment"}})
    assert resp.status == 401
    assert len(list_equipment_overrides(data_dir)) == 1
