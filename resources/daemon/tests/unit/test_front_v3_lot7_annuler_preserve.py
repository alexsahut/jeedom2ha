"""Front v3 (Lot 7, revue Codex #406) — « Annuler » après « Publier quand même » rétablit EXACTEMENT l'état d'avant.

Entité à plusieurs commandes dont une commande sœur porte déjà une correction de type. Séquence réelle des routes, telle
que l'écran l'envoie : type + « Toujours » sur la commande du panneau, puis l'annulation (réglage de publication de CETTE
commande seul, `scope == "command"`, puis type précédent). Les fichiers de réglages sont identiques à l'état initial.
Le champ additif `publication_override_own` de l'arbre n'apparaît que s'il est posé. Données fictives (CC-48).
"""

import pytest

from transport.http_server import create_app
from mapping.overrides import (
    save_override, save_equipment_override, list_overrides, list_equipment_overrides,
)
from models.topology import TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd

SECRET = "test_secret_front_v3_lot7"


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _headers():
    return {"X-Local-Secret": SECRET}


def _light(app, tmp_path, eq_id=97100):
    eq = JeedomEqLogic(
        id=eq_id, name="Lampe fictive", object_id=1, eq_type_name="light",
        cmds=[
            JeedomCmd(id=eq_id * 10 + 1, name="On", type="action", sub_type="other", generic_type="LIGHT_ON"),
            JeedomCmd(id=eq_id * 10 + 2, name="Off", type="action", sub_type="other", generic_type="LIGHT_OFF"),
            JeedomCmd(id=eq_id * 10 + 3, name="Etat", type="info", sub_type="binary", generic_type="LIGHT_STATE"),
        ],
    )
    app["topology"] = TopologySnapshot(
        timestamp="2026-11-15T00:00:00Z", objects={1: JeedomObject(id=1, name="Salon")}, eq_logics={eq_id: eq},
    )
    app["data_dir"] = str(tmp_path)
    return eq, str(tmp_path)


async def _post(cli, path, payload):
    resp = await cli.post(path, headers=_headers(), json={"payload": payload})
    body = await resp.json()
    assert resp.status == 200, body
    return body["payload"]


async def _own_publication(cli, eq_id, cmd_id):
    resp = await cli.get(f"/system/mapping_overrides/{eq_id}", headers=_headers())
    assert resp.status == 200
    tree = (await resp.json())["payload"]
    row = next(r for r in tree["commands"] if r["jeedom_cmd_id"] == cmd_id)
    return row.get("publication_override_own"), row


async def _publish_anyway_then_undo(cli, eq, panel_cmd, chosen_type):
    """Écritures de l'écran : « Enregistrer et publier quand même », puis « Annuler » (mêmes routes, même ordre)."""
    previous_publication, row = await _own_publication(cli, eq.id, panel_cmd)
    previous_type = row["effective_ha"] if row["override_applied"] else None
    await _post(cli, "/action/mapping_override",
                {"jeedom_eq_id": eq.id, "jeedom_cmd_id": panel_cmd, "ha_entity_type": chosen_type})
    await _post(cli, "/action/publication_override",
                {"jeedom_eq_id": eq.id, "jeedom_cmd_id": panel_cmd, "publication_policy": "force_publish"})
    assert (await _own_publication(cli, eq.id, panel_cmd))[0] == "force_publish"
    # Annuler : réglage de publication de la commande, puis type précédent.
    if previous_publication is None:
        out = await _post(cli, "/action/publication_override_revert",
                          {"jeedom_eq_id": eq.id, "jeedom_cmd_id": panel_cmd, "scope": "command"})
        assert out == {"jeedom_eq_id": eq.id, "jeedom_cmd_id": panel_cmd, "scope": "command_publication",
                       "removed": True, "removed_commands": [panel_cmd]}
    elif previous_publication == "exclude":
        await _post(cli, "/action/publication_override",
                    {"jeedom_eq_id": eq.id, "jeedom_cmd_id": panel_cmd, "publication_policy": "exclude"})
    if previous_type is None:
        await _post(cli, "/action/mapping_override_revert", {"jeedom_eq_id": eq.id, "jeedom_cmd_id": panel_cmd})
    else:
        await _post(cli, "/action/mapping_override",
                    {"jeedom_eq_id": eq.id, "jeedom_cmd_id": panel_cmd, "ha_entity_type": previous_type})


async def test_undo_keeps_sibling_type_correction(cli, app, tmp_path):
    eq, data_dir = _light(app, tmp_path)
    sibling, panel = eq.cmds[0].id, eq.cmds[2].id
    save_override(eq.id, sibling, {"ha_entity_type": "switch"}, data_dir)
    before = (list_overrides(data_dir), list_equipment_overrides(data_dir))
    assert (await _own_publication(cli, eq.id, panel))[0] is None

    await _publish_anyway_then_undo(cli, eq, panel, "light")

    assert (list_overrides(data_dir), list_equipment_overrides(data_dir)) == before, "état final identique à l'état initial"
    assert list_overrides(data_dir)[f"{eq.id}:{sibling}"]["ha_entity_type"] == "switch", "correction sœur intacte"


async def test_undo_keeps_equipment_and_sibling_publication_settings(cli, app, tmp_path):
    eq, data_dir = _light(app, tmp_path)
    sibling, other, panel = eq.cmds[0].id, eq.cmds[1].id, eq.cmds[2].id
    save_override(eq.id, sibling, {"ha_entity_type": "switch"}, data_dir)
    save_override(eq.id, other, {"publication_override": "force_publish"}, data_dir)
    save_override(eq.id, panel, {"ha_entity_type": "switch"}, data_dir)
    save_equipment_override(eq.id, {"publication_override": "force_publish"}, data_dir)
    before = (list_overrides(data_dir), list_equipment_overrides(data_dir))

    await _publish_anyway_then_undo(cli, eq, panel, "light")

    assert (list_overrides(data_dir), list_equipment_overrides(data_dir)) == before


async def test_undo_restores_previous_own_exclusion(cli, app, tmp_path):
    eq, data_dir = _light(app, tmp_path)
    sibling, panel = eq.cmds[0].id, eq.cmds[2].id
    save_override(eq.id, sibling, {"ha_entity_type": "switch"}, data_dir)
    save_override(eq.id, panel, {"publication_override": "exclude"}, data_dir)
    before = (list_overrides(data_dir), list_equipment_overrides(data_dir))
    assert (await _own_publication(cli, eq.id, panel))[0] == "exclude"

    await _publish_anyway_then_undo(cli, eq, panel, "light")

    assert (list_overrides(data_dir), list_equipment_overrides(data_dir)) == before


async def test_canonical_revert_still_purges_whole_entity(cli, app, tmp_path):
    """Sans `scope`, le retour canonique (CC-19) est inchangé : c'est lui qui effaçait la correction sœur."""
    eq, data_dir = _light(app, tmp_path)
    sibling, panel = eq.cmds[0].id, eq.cmds[2].id
    save_override(eq.id, sibling, {"ha_entity_type": "switch"}, data_dir)
    save_override(eq.id, panel, {"publication_override": "force_publish"}, data_dir)
    await _post(cli, "/action/publication_override_revert", {"jeedom_eq_id": eq.id, "jeedom_cmd_id": panel})
    assert list_overrides(data_dir) == {}


async def test_scope_command_removes_only_publication_field(cli, app, tmp_path):
    eq, data_dir = _light(app, tmp_path)
    panel = eq.cmds[2].id
    save_override(eq.id, panel, {"ha_entity_type": "light", "publication_override": "force_publish"}, data_dir)
    out = await _post(cli, "/action/publication_override_revert",
                      {"jeedom_eq_id": eq.id, "jeedom_cmd_id": panel, "scope": "command"})
    assert out["removed"] is True
    entry = list_overrides(data_dir)[f"{eq.id}:{panel}"]
    assert entry["ha_entity_type"] == "light" and "publication_override" not in entry
    again = await _post(cli, "/action/publication_override_revert",
                        {"jeedom_eq_id": eq.id, "jeedom_cmd_id": panel, "scope": "command"})
    assert again["removed"] is False and again["removed_commands"] == []


@pytest.mark.parametrize("payload, status", [
    ({"jeedom_eq_id": 97100, "scope": "command"}, 400),
    ({"jeedom_eq_id": 97100, "scope": "command", "jeedom_cmd_id": "971003"}, 400),
    ({"jeedom_eq_id": "97100", "scope": "command", "jeedom_cmd_id": 971003}, 400),
    ({"jeedom_eq_id": 1, "scope": "command", "jeedom_cmd_id": 971003}, 404),
    ({"jeedom_eq_id": 97100, "scope": "command", "jeedom_cmd_id": 999}, 404),
])
async def test_scope_command_invalid(cli, app, tmp_path, payload, status):
    eq, data_dir = _light(app, tmp_path)
    save_override(eq.id, eq.cmds[2].id, {"publication_override": "force_publish"}, data_dir)
    resp = await cli.post("/action/publication_override_revert", headers=_headers(), json={"payload": payload})
    assert resp.status == status
    assert list_overrides(data_dir)[f"{eq.id}:{eq.cmds[2].id}"]["publication_override"] == "force_publish"


async def test_scope_command_requires_secret(cli, app, tmp_path):
    eq, data_dir = _light(app, tmp_path)
    save_override(eq.id, eq.cmds[2].id, {"publication_override": "force_publish"}, data_dir)
    resp = await cli.post("/action/publication_override_revert",
                          json={"payload": {"jeedom_eq_id": eq.id, "jeedom_cmd_id": eq.cmds[2].id, "scope": "command"}})
    assert resp.status == 401
    assert len(list_overrides(data_dir)) == 1
