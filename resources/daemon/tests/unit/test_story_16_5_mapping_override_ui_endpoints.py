"""Story 16.5 — Endpoints backend consommés par l'UI de configuration par équipement.

Trois routes câblent le contrat HTTP du triptyque natif/override/diagnostic :
- GET  /system/mapping_overrides/{eq_id}   → arbre par commande (lecture seule)
- POST /action/mapping_override            → persistance d'un override de type (save_override)
- POST /action/mapping_override_revert     → retour au mode auto (remove_override / equipment)

Invariants vérifiés : `generic_type` natif jamais muté (D10), distinction stricte
diagnostic-métier (HTTP 200) vs erreur technique/auth/ID (401/404), aucune publication MQTT.
"""

from unittest.mock import MagicMock

import pytest

from transport.http_server import create_app
from mapping.overrides import list_overrides
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


def _light_snapshot(eq_id=200, state_id=2001, slider_id=2002):
    state = JeedomCmd(id=state_id, name="Etat", generic_type="LIGHT_STATE")
    slider = JeedomCmd(id=slider_id, name="Slider", generic_type="LIGHT_SLIDER")
    eq = JeedomEqLogic(id=eq_id, name="Lampe", object_id=1, is_enable=True,
                       cmds=[state, slider])
    snapshot = TopologySnapshot(
        timestamp="2026-07-17T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={eq_id: eq},
    )
    return snapshot, eq


def _headers():
    return {"X-Local-Secret": SECRET}


# ---------------------------------------------------------------------------
# GET /system/mapping_overrides/{eq_id}
# ---------------------------------------------------------------------------

async def test_get_tree_returns_command_rows_with_native_and_attendu(cli, app, tmp_path):
    """AC4 — l'arbre expose par commande : generic_type natif, attendu HA, diagnostic."""
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    resp = await cli.get("/system/mapping_overrides/200", headers=_headers())
    assert resp.status == 200
    payload = (await resp.json())["payload"]
    assert payload["jeedom_eq_id"] == 200
    assert payload["mapped"] is True
    rows = {c["jeedom_cmd_id"]: c for c in payload["commands"]}
    assert rows[2001]["generic_type"] == "LIGHT_STATE"
    assert rows[2001]["attendu_ha"] == "light"
    assert rows[2001]["override_applied"] is False
    assert rows[2001]["effective_ha"] == "light"
    assert rows[2001]["diagnostic"] is not None
    assert rows[2001]["diagnostic"]["ha_entity_type"] == "light"


async def test_get_tree_reflects_persisted_override(cli, app, tmp_path):
    """AC4 — un override persisté apparaît en effective_ha + override_source, natif intact."""
    from mapping.overrides import save_override
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    save_override(200, 2001, {"ha_entity_type": "switch"}, str(tmp_path))

    resp = await cli.get("/system/mapping_overrides/200", headers=_headers())
    payload = (await resp.json())["payload"]
    rows = {c["jeedom_cmd_id"]: c for c in payload["commands"]}
    assert rows[2001]["override_applied"] is True
    assert rows[2001]["override_source"] == "user"
    assert rows[2001]["effective_ha"] == "switch"
    # generic_type natif jamais muté (D10)
    assert rows[2001]["generic_type"] == "LIGHT_STATE"


async def test_get_tree_unknown_eq_returns_404(cli, app):
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    resp = await cli.get("/system/mapping_overrides/999", headers=_headers())
    assert resp.status == 404


async def test_get_tree_requires_secret(cli, app):
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    resp = await cli.get("/system/mapping_overrides/200")
    assert resp.status == 401


async def test_get_tree_non_int_eq_returns_400(cli, app):
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    resp = await cli.get("/system/mapping_overrides/abc", headers=_headers())
    assert resp.status == 400


# ---------------------------------------------------------------------------
# POST /action/mapping_override
# ---------------------------------------------------------------------------

async def test_save_override_persists_and_returns_ok(cli, app, tmp_path):
    """AC9 — la sauvegarde écrit bien l'override via save_override."""
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)

    resp = await cli.post(
        "/action/mapping_override",
        headers=_headers(),
        json={"payload": {"jeedom_eq_id": 200, "jeedom_cmd_id": 2001, "ha_entity_type": "switch"}},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"
    assert data["payload"]["override_applied"] is True
    persisted = list_overrides(str(tmp_path))
    assert persisted["200:2001"]["ha_entity_type"] == "switch"
    assert persisted["200:2001"]["source"] == "user"


async def test_save_override_unknown_cmd_returns_404(cli, app, tmp_path):
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    resp = await cli.post(
        "/action/mapping_override",
        headers=_headers(),
        json={"payload": {"jeedom_eq_id": 200, "jeedom_cmd_id": 9999, "ha_entity_type": "switch"}},
    )
    assert resp.status == 404
    # rien persisté
    assert list_overrides(str(tmp_path)) == {}


async def test_save_override_unknown_eq_returns_404(cli, app, tmp_path):
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    resp = await cli.post(
        "/action/mapping_override",
        headers=_headers(),
        json={"payload": {"jeedom_eq_id": 999, "jeedom_cmd_id": 2001, "ha_entity_type": "switch"}},
    )
    assert resp.status == 404


async def test_save_override_missing_type_returns_400(cli, app, tmp_path):
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    resp = await cli.post(
        "/action/mapping_override",
        headers=_headers(),
        json={"payload": {"jeedom_eq_id": 200, "jeedom_cmd_id": 2001}},
    )
    assert resp.status == 400


async def test_save_override_requires_secret(cli, app, tmp_path):
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    resp = await cli.post(
        "/action/mapping_override",
        json={"payload": {"jeedom_eq_id": 200, "jeedom_cmd_id": 2001, "ha_entity_type": "switch"}},
    )
    assert resp.status == 401
    assert list_overrides(str(tmp_path)) == {}


async def test_save_override_never_publishes_mqtt(cli, app, tmp_path):
    """La sauvegarde d'override ne déclenche AUCUNE publication MQTT."""
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    bridge = MagicMock()
    app["mqtt_bridge"] = bridge
    resp = await cli.post(
        "/action/mapping_override",
        headers=_headers(),
        json={"payload": {"jeedom_eq_id": 200, "jeedom_cmd_id": 2001, "ha_entity_type": "switch"}},
    )
    assert resp.status == 200
    assert not bridge.method_calls, f"appels MQTT inattendus: {bridge.method_calls}"


# ---------------------------------------------------------------------------
# POST /action/mapping_override_revert
# ---------------------------------------------------------------------------

async def test_revert_command_removes_override(cli, app, tmp_path):
    """AC10 — retour au mode auto par commande : l'override est supprimé."""
    from mapping.overrides import save_override
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    save_override(200, 2001, {"ha_entity_type": "switch"}, str(tmp_path))

    resp = await cli.post(
        "/action/mapping_override_revert",
        headers=_headers(),
        json={"payload": {"jeedom_eq_id": 200, "jeedom_cmd_id": 2001}},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["payload"]["removed"] is True
    assert data["payload"]["scope"] == "command"
    assert list_overrides(str(tmp_path)) == {}


async def test_revert_equipment_scope_when_no_cmd(cli, app, tmp_path):
    """AC10 — sans jeedom_cmd_id, le retour au mode auto porte sur l'équipement."""
    from mapping.overrides import save_equipment_override, list_equipment_overrides
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    save_equipment_override(200, {"publication_override": "exclude"}, str(tmp_path))

    resp = await cli.post(
        "/action/mapping_override_revert",
        headers=_headers(),
        json={"payload": {"jeedom_eq_id": 200}},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["payload"]["scope"] == "equipment"
    assert data["payload"]["removed"] is True
    assert list_equipment_overrides(str(tmp_path)) == {}


async def test_revert_unknown_eq_returns_404(cli, app, tmp_path):
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    resp = await cli.post(
        "/action/mapping_override_revert",
        headers=_headers(),
        json={"payload": {"jeedom_eq_id": 999, "jeedom_cmd_id": 2001}},
    )
    assert resp.status == 404


async def test_revert_requires_secret(cli, app, tmp_path):
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    app["data_dir"] = str(tmp_path)
    resp = await cli.post(
        "/action/mapping_override_revert",
        json={"payload": {"jeedom_eq_id": 200, "jeedom_cmd_id": 2001}},
    )
    assert resp.status == 401
