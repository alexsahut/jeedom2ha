"""Story 16.8 — l'arbre et la preview exposent le diagnostic des capteurs SECONDAIRES.

Contexte multi-sensor (Story 11.1) : un eqLogic produit un mapping PRIMAIRE plus des
capteurs secondaires (`additional_mappings`) publiés au sync mais absents du mapping
primaire. Avant ce fix, les endpoints override n'évaluaient que le primaire :
  - GET /system/mapping_overrides/{eq_id} → la ligne d'une commande secondaire portait
    `diagnostic: null` (cellule vide dans l'UI, alors que le capteur EST publié).
  - POST /system/overrides/preview → un override sur une commande secondaire était appliqué
    contre le primaire (no-op) → la preview affichait le type PRIMAIRE, pas le type réel.

Fixture : prise avec conso (primaire `switch` + capteur secondaire `sensor` power, cmd 133004),
identique à la Story 13.3.
"""

import pytest

from transport.http_server import create_app
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd,
)

SECRET = "test_secret"


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _cmd(cmd_id, name, cmd_type, sub_type, generic_type=None, unit=None, value=None):
    return JeedomCmd(
        id=cmd_id, name=name, type=cmd_type, sub_type=sub_type,
        generic_type=generic_type, unit=unit, current_value=value,
    )


def _metering_plug(eq_id=13300):
    """Prise avec conso : primaire switch + capteur secondaire power (cmd 133004)."""
    eq = JeedomEqLogic(
        id=eq_id, name="Prise bureau", object_id=1, eq_type_name="prise",
        cmds=[
            _cmd(133001, "On", "action", "other", "ENERGY_ON"),
            _cmd(133002, "Off", "action", "other", "ENERGY_OFF"),
            _cmd(133003, "Etat", "info", "binary", "ENERGY_STATE", value="1"),
            _cmd(133004, "Conso W", "info", "numeric", None, "W", 42),
        ],
    )
    snapshot = TopologySnapshot(
        timestamp="2026-07-20T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Bureau")},
        eq_logics={eq_id: eq},
    )
    return snapshot, eq


def _smoke_detector(eq_id=54300):
    """DAAF : primaire SMOKE (binary_sensor) + commande température NON couverte.

    Le mapper binary_sensor ne produit pas de capteur secondaire pour la température
    (pas d'agrégation multi-entité sur un primaire binary_sensor) : la commande
    température (cmd 543006) n'est couverte NI par le primaire NI par un secondaire.
    C'est exactement le cas #871 (flash vert trompeur puis cellule vide).
    """
    eq = JeedomEqLogic(
        id=eq_id, name="DAAF cuisine", object_id=1, eq_type_name="daaf",
        cmds=[
            _cmd(543001, "Fumée", "info", "binary", "SMOKE", value="0"),
            _cmd(543006, "Température", "info", "numeric", "TEMPERATURE", "°C", 21),
        ],
    )
    snapshot = TopologySnapshot(
        timestamp="2026-07-20T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Cuisine")},
        eq_logics={eq_id: eq},
    )
    return snapshot, eq


def _headers():
    return {"X-Local-Secret": SECRET}


def _row(payload, cmd_id):
    return next(c for c in payload["commands"] if c["jeedom_cmd_id"] == cmd_id)


# ---------------------------------------------------------------------------
# GET /system/mapping_overrides/{eq_id} — diagnostic des secondaires
# ---------------------------------------------------------------------------

async def test_tree_exposes_secondary_sensor_diagnostic(cli, app, tmp_path):
    """La commande secondaire (cmd 133004) porte son diagnostic réel, pas `null`."""
    snapshot, _ = _metering_plug()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    resp = await cli.get("/system/mapping_overrides/13300", headers=_headers())
    assert resp.status == 200
    payload = (await resp.json())["payload"]

    secondary = _row(payload, 133004)
    assert secondary["diagnostic"] is not None
    assert secondary["diagnostic"]["ha_entity_type"] == "sensor"
    assert secondary["diagnostic"]["should_publish"] is True
    # L'attendu HA de la commande secondaire est SON propre type, pas l'attendu équipement.
    assert secondary["attendu_ha"] == "sensor"


async def test_tree_primary_command_still_diagnosed(cli, app, tmp_path):
    """Non-régression : la commande primaire (cmd 133003) garde son diagnostic switch."""
    snapshot, _ = _metering_plug()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    resp = await cli.get("/system/mapping_overrides/13300", headers=_headers())
    payload = (await resp.json())["payload"]

    primary = _row(payload, 133003)
    assert primary["diagnostic"] is not None
    assert primary["diagnostic"]["ha_entity_type"] == "switch"


# ---------------------------------------------------------------------------
# POST /system/overrides/preview — cible le bon mapping secondaire
# ---------------------------------------------------------------------------

async def _preview(cli, body):
    return await cli.post(
        "/system/overrides/preview", headers=_headers(), json={"payload": body}
    )


async def test_preview_targets_secondary_sensor_not_primary(cli, app):
    """Override sur la commande secondaire → la preview évalue le SECONDAIRE (sensor)."""
    snapshot, _ = _metering_plug()
    app["topology"] = snapshot

    resp = await _preview(cli, {
        "jeedom_eq_id": 13300,
        "jeedom_cmd_id": 133004,
        "ha_entity_type": "sensor",
    })
    assert resp.status == 200
    payload = (await resp.json())["payload"]

    # Avant le fix : `overridden` valait "switch" (le primaire). Désormais "sensor".
    assert payload["auto"]["ha_entity_type"] == "sensor"
    assert payload["overridden"]["ha_entity_type"] == "sensor"
    assert payload["overridden"]["should_publish"] is True


async def test_preview_primary_command_unchanged(cli, app):
    """Non-régression : override sur une commande primaire évalue toujours le primaire."""
    snapshot, _ = _metering_plug()
    app["topology"] = snapshot

    resp = await _preview(cli, {
        "jeedom_eq_id": 13300,
        "jeedom_cmd_id": 133003,
        "ha_entity_type": "switch",
    })
    payload = (await resp.json())["payload"]
    assert payload["auto"]["ha_entity_type"] == "switch"
    assert payload["overridden"]["ha_entity_type"] == "switch"


# ---------------------------------------------------------------------------
# AC12 « jamais vide » — commande NON couverte (ni primaire, ni secondaire)
# ---------------------------------------------------------------------------

async def test_covered_flag_true_on_primary_and_secondary(cli, app, tmp_path):
    """Les commandes réellement couvertes (primaire + secondaire) portent covered=true."""
    snapshot, _ = _metering_plug()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    resp = await cli.get("/system/mapping_overrides/13300", headers=_headers())
    payload = (await resp.json())["payload"]

    assert _row(payload, 133003)["covered"] is True  # primaire switch
    assert _row(payload, 133004)["covered"] is True  # secondaire sensor


async def test_tree_uncovered_command_flagged_with_command_not_covered_diagnostic(cli, app, tmp_path):
    """La température d'un DAAF (non couverte) porte covered=false ET un diagnostic non-null
    (Story 19.3, AC7 — chaque commande a une CommandDecision, jamais de diagnostic `None`).
    Avant Story 19.3, ce diagnostic était `None` : `evaluate_equipment()` produit désormais
    une `CommandDecision(reason="command_not_covered")` pour toute commande non couverte."""
    snapshot, _ = _smoke_detector()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    resp = await cli.get("/system/mapping_overrides/54300", headers=_headers())
    assert resp.status == 200
    payload = (await resp.json())["payload"]

    primary = _row(payload, 543001)
    assert primary["covered"] is True
    assert primary["diagnostic"] is not None

    temperature = _row(payload, 543006)
    assert temperature["covered"] is False
    assert temperature["diagnostic"] is not None
    assert temperature["diagnostic"]["should_publish"] is False
    assert temperature["diagnostic"]["publication_reason"] == "command_not_covered"


async def test_preview_uncovered_command_is_honest(cli, app):
    """Preview sur une commande non couverte → covered=false, overridden=null (pas de vert trompeur)."""
    snapshot, _ = _smoke_detector()
    app["topology"] = snapshot

    resp = await _preview(cli, {
        "jeedom_eq_id": 54300,
        "jeedom_cmd_id": 543006,
        "ha_entity_type": "sensor",
    })
    assert resp.status == 200
    payload = (await resp.json())["payload"]

    assert payload["covered"] is False
    assert payload["overridden"] is None
