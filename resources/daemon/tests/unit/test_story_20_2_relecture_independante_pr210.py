"""Story 20.2 — relecture indépendante de la PR #210 (points 3 et 5).

Point 3 : l'aperçu d'un forçage à la portée équipement (`jeedom_cmd_id` absent,
`publication_policy` fourni) doit exposer `entities[]` pour TOUTES les entités du
mapping (principale et secondaires), pas seulement l'entité principale — champ additif
de `_handle_overrides_preview`, même vue que l'arbre (`_decision_view`).

Point 5 : `_handle_mapping_override_revert` (portée commande, `entity_scope=True`) sur un
équipement devenu inéligible (`evaluation.mapping is None`) ne doit jamais planter
(`mapping_cmd_ids(None)`) — 409 « Commande sans entité », jamais 500.
"""
import pytest

from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot

SECRET = "x5"


@pytest.fixture
def app():
    from transport.http_server import create_app
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _headers():
    return {"X-Local-Secret": SECRET}


def _cmd(cmd_id, name, cmd_type, sub_type, generic_type=None, unit=None, value=None):
    return JeedomCmd(
        id=cmd_id, name=name, type=cmd_type, sub_type=sub_type,
        generic_type=generic_type, unit=unit, current_value=value,
    )


def _metering_plug(eq_id=20200, is_enable=True):
    """Prise avec conso : primaire switch + capteur secondaire power — même fixture que
    la Story 19.3 (`test_story_19_3_p2_shared_command_priority.py`), deux entités."""
    eq = JeedomEqLogic(
        id=eq_id, name="Prise bureau", object_id=1, eq_type_name="prise", is_enable=is_enable,
        cmds=[
            _cmd(cmd_id=eq_id * 10 + 1, name="On", cmd_type="action", sub_type="other", generic_type="ENERGY_ON"),
            _cmd(cmd_id=eq_id * 10 + 2, name="Off", cmd_type="action", sub_type="other", generic_type="ENERGY_OFF"),
            _cmd(cmd_id=eq_id * 10 + 3, name="Etat", cmd_type="info", sub_type="binary", generic_type="ENERGY_STATE", value="1"),
            _cmd(cmd_id=eq_id * 10 + 4, name="Conso W", cmd_type="info", sub_type="numeric", unit="W", value=42),
        ],
    )
    snapshot = TopologySnapshot(
        timestamp="2026-10-06T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Bureau")},
        eq_logics={eq_id: eq},
    )
    return snapshot, eq


async def test_preview_equipment_force_publish_exposes_entities(cli, app):
    """POST /system/overrides/preview, portée équipement, forçage : `entities[]` porte les
    deux mappings (switch primaire + sensor secondaire), chacun avec `ha_entity_type`,
    `command_ids` et `decision` (même contrat que l'arbre)."""
    snapshot, eq = _metering_plug()
    app["topology"] = snapshot

    resp = await cli.post("/system/overrides/preview", headers=_headers(), json={"payload": {
        "jeedom_eq_id": eq.id, "publication_policy": "force_publish",
    }})
    assert resp.status == 200
    payload = (await resp.json())["payload"]
    entities = payload["overridden"]["entities"]
    assert len(entities) == 2
    types = {entity["ha_entity_type"] for entity in entities}
    assert types == {"switch", "sensor"}
    for entity in entities:
        assert isinstance(entity["command_ids"], list) and entity["command_ids"]
        assert entity["decision"] is not None
        assert "should_publish" in entity["decision"]


async def test_preview_entity_scope_has_no_entities_field(cli, app):
    """Portée entité (`jeedom_cmd_id` fourni) : comportement inchangé, pas de champ
    `entities[]` ajouté (champ additif réservé à la portée équipement)."""
    snapshot, eq = _metering_plug()
    app["topology"] = snapshot

    resp = await cli.post("/system/overrides/preview", headers=_headers(), json={"payload": {
        "jeedom_eq_id": eq.id, "jeedom_cmd_id": eq.cmds[0].id, "publication_policy": "force_publish",
    }})
    assert resp.status == 200
    payload = (await resp.json())["payload"]
    assert "entities" not in payload["overridden"]


async def test_revert_command_scope_on_ineligible_equipment_returns_409_not_500(cli, app, tmp_path):
    """Point 5 : un équipement désactivé (`is_enable=False`, inéligible) n'a aucun mapping
    (`evaluation.mapping is None`) — demander le retrait au mode auto d'une de ses commandes
    (portée entité, CC-19) doit répondre 409 « Commande sans entité », jamais 500."""
    snapshot, eq = _metering_plug(eq_id=20201, is_enable=False)
    app["topology"], app["data_dir"] = snapshot, str(tmp_path)

    resp = await cli.post("/action/publication_override_revert", headers=_headers(), json={"payload": {
        "jeedom_eq_id": eq.id, "jeedom_cmd_id": eq.cmds[0].id,
    }})
    assert resp.status == 409
    body = await resp.json()
    assert body["message"] == "Commande sans entité"
