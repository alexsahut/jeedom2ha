"""Story 19.3 — AC3 / CC-19 : un seul « Revenir au mode automatique » au niveau ÉQUIPEMENT
purge TOUS les overrides de cet équipement — override équipement ET tous les overrides TYPE
par commande (`eq:cmd`) — via les primitives CRUD existantes uniquement.

Avant ce fix, `POST /action/mapping_override_revert` sans `jeedom_cmd_id` ne supprimait que
`equipment_overrides[eq_id]` : un override TYPE par commande survivait, laissant l'UI dans un
état incohérent (bug historique CC-19).
"""

import pytest

from transport.http_server import create_app
from mapping.overrides import (
    save_override, save_equipment_override, list_overrides, list_equipment_overrides,
)
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd,
)

SECRET = "test_secret_19_3_ac3"


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _headers():
    return {"X-Local-Secret": SECRET}


def _plain_light(eq_id=90300):
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


async def test_ac3_equipment_revert_purges_both_command_type_and_publication_overrides(cli, app, tmp_path):
    """Un équipement porte à la fois un override TYPE sur ON, un override TYPE sur OFF, et
    un override de publication équipement (exclude). Un seul revert « équipement complet »
    (sans jeedom_cmd_id) doit tout purger."""
    snapshot, eq = _plain_light()
    app["topology"] = snapshot
    data_dir = str(tmp_path)
    app["data_dir"] = data_dir
    on_cmd_id, off_cmd_id = eq.cmds[0].id, eq.cmds[1].id

    save_override(eq.id, on_cmd_id, {"ha_entity_type": "switch"}, data_dir)
    save_override(eq.id, off_cmd_id, {"ha_entity_type": "switch"}, data_dir)
    save_equipment_override(eq.id, {"publication_override": "exclude"}, data_dir)

    assert len(list_overrides(data_dir)) == 2
    assert len(list_equipment_overrides(data_dir)) == 1

    resp = await cli.post(
        "/action/publication_override_revert",
        headers=_headers(),
        json={"payload": {"jeedom_eq_id": eq.id}},
    )
    assert resp.status == 200
    body = (await resp.json())["payload"]
    assert body["scope"] == "equipment"
    assert sorted(body["removed_commands"]) == sorted([on_cmd_id, off_cmd_id])

    remaining_cmd_overrides = list_overrides(data_dir)
    remaining_eq_overrides = list_equipment_overrides(data_dir)
    assert remaining_cmd_overrides == {}
    assert remaining_eq_overrides == {}


async def test_ac3_equipment_revert_leaves_other_equipment_overrides_untouched(cli, app, tmp_path):
    """Le revert d'un équipement ne touche jamais les overrides d'un AUTRE équipement."""
    snapshot, eq = _plain_light(eq_id=90310)
    other_snapshot, other_eq = _plain_light(eq_id=90320)
    snapshot.eq_logics[other_eq.id] = other_eq
    app["topology"] = snapshot
    data_dir = str(tmp_path)
    app["data_dir"] = data_dir

    save_override(eq.id, eq.cmds[0].id, {"ha_entity_type": "switch"}, data_dir)
    save_override(other_eq.id, other_eq.cmds[0].id, {"ha_entity_type": "switch"}, data_dir)
    save_equipment_override(other_eq.id, {"publication_override": "exclude"}, data_dir)

    resp = await cli.post(
        "/action/mapping_override_revert",
        headers=_headers(),
        json={"payload": {"jeedom_eq_id": eq.id}},
    )
    assert resp.status == 200

    remaining_cmd_overrides = list_overrides(data_dir)
    assert f"{eq.id}:{eq.cmds[0].id}" not in remaining_cmd_overrides
    assert f"{other_eq.id}:{other_eq.cmds[0].id}" in remaining_cmd_overrides
    assert str(other_eq.id) in list_equipment_overrides(data_dir)
