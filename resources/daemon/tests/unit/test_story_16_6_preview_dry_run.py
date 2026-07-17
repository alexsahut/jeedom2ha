"""Story 16.6 — Preview / dry-run avant application d'un override.

Lecture seule : l'endpoint `POST /system/overrides/preview` calcule le résultat
"auto" (moteur brut) ET "avec override" (override PROPOSÉ appliqué en mémoire),
fait passer le résultat surchargé par `validate_projection` AVANT toute sauvegarde,
et ne déclenche AUCUNE publication MQTT ni écriture disque pendant le dry-run.
"""

from unittest.mock import MagicMock

import pytest

from transport.http_server import create_app
from models.topology import (
    TopologySnapshot, JeedomObject, JeedomEqLogic, JeedomCmd,
)


@pytest.fixture
def app():
    return create_app(local_secret="test_secret")


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


async def _preview(cli, body):
    return await cli.post(
        "/system/overrides/preview",
        headers={"X-Local-Secret": "test_secret"},
        json={"payload": body},
    )


async def test_preview_returns_auto_and_overridden(cli, app):
    """AC1 — preview retourne le résultat auto ET le résultat avec override proposé."""
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    resp = await _preview(cli, {
        "jeedom_eq_id": 200,
        "jeedom_cmd_id": 2001,
        "ha_entity_type": "switch",
    })
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"
    payload = data["payload"]
    assert payload["auto"]["ha_entity_type"] == "light"
    assert payload["overridden"]["ha_entity_type"] == "switch"
    assert payload["overridden"]["type_override"]["native"] == "light"
    assert payload["overridden"]["type_override"]["effective"] == "switch"
    # generic_type natif jamais muté (non-régression Homebridge)
    assert payload["native_generic_types"]["2001"] == "LIGHT_STATE"
    assert payload["native_generic_types"]["2002"] == "LIGHT_SLIDER"


async def test_preview_no_mqtt_publish(cli, app):
    """AC2 — aucune publication MQTT (discovery ni state) pendant le dry-run."""
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    bridge = MagicMock()
    app["mqtt_bridge"] = bridge
    resp = await _preview(cli, {
        "jeedom_eq_id": 200,
        "jeedom_cmd_id": 2001,
        "ha_entity_type": "switch",
    })
    assert resp.status == 200
    # Le bridge MQTT ne doit avoir subi AUCUN appel de publication.
    assert not bridge.publish.called
    assert not bridge.method_calls, f"appels MQTT inattendus: {bridge.method_calls}"


async def test_preview_incompatible_override_exposes_validation_failure(cli, app):
    """AC3 — override incompatible : la validation HA échoue et est visible avant sauvegarde."""
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    resp = await _preview(cli, {
        "jeedom_eq_id": 200,
        "jeedom_cmd_id": 2001,
        "ha_entity_type": "climate",  # exige has_setpoint, absent d'une lampe
    })
    assert resp.status == 200
    payload = (await resp.json())["payload"]
    validity = payload["overridden"]["projection_validity"]
    assert validity["is_valid"] is False
    assert validity["reason_code"] == "ha_missing_temperature_command_topic"
    assert payload["overridden"]["should_publish"] is False
    # AC4 — export support : raison de refus exposée quand override impliqué.
    assert "ha_missing_temperature_command_topic" in payload["support_export"]["refusal_reasons"]
    assert payload["support_export"]["preview_trace"]["effective"] == "climate"


async def test_preview_does_not_persist_override(cli, app, monkeypatch):
    """AC1 — dry-run n'écrit RIEN : save_override/save_equipment_override jamais appelés."""
    import transport.http_server as hs

    def _boom(*args, **kwargs):
        raise AssertionError("save_override ne doit jamais être appelé en preview")

    # Garde-fou : si l'endpoint tente une persistance, le test échoue.
    monkeypatch.setattr(hs, "save_override", _boom, raising=False)
    monkeypatch.setattr(hs, "save_equipment_override", _boom, raising=False)

    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    resp = await _preview(cli, {
        "jeedom_eq_id": 200,
        "jeedom_cmd_id": 2001,
        "ha_entity_type": "switch",
    })
    assert resp.status == 200


async def test_preview_publication_override_exclude(cli, app):
    """AC1/AC4 — override de PUBLICATION proposé (exclude) : should_publish False + trace support."""
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    resp = await _preview(cli, {
        "jeedom_eq_id": 200,
        "jeedom_cmd_id": 2001,
        "publication_policy": "exclude",
    })
    assert resp.status == 200
    payload = (await resp.json())["payload"]
    # Type inchangé (pas d'override de type), mais publication forcée à exclude.
    assert payload["overridden"]["ha_entity_type"] == "light"
    assert payload["overridden"]["should_publish"] is False
    assert payload["overridden"]["publication_reason"] == "publication_excluded_command"


async def test_preview_unknown_equipment_returns_404(cli, app):
    """Robustesse — équipement absent de la topologie → 404 explicite."""
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    resp = await _preview(cli, {
        "jeedom_eq_id": 999,
        "jeedom_cmd_id": 1,
        "ha_entity_type": "switch",
    })
    assert resp.status == 404


async def test_preview_requires_secret(cli, app):
    """Sécurité — endpoint protégé par X-Local-Secret."""
    snapshot, _ = _light_snapshot()
    app["topology"] = snapshot
    resp = await cli.post("/system/overrides/preview", json={"payload": {"jeedom_eq_id": 200}})
    assert resp.status == 401
