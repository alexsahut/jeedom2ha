"""Story 5.4 — tests backend : _build_operation_snapshot et contrat /system/status."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import transport.http_server as http_server
from transport.http_server import _build_operation_snapshot, create_app
from models.mapping import LightCapabilities, MappingResult, PublicationDecision
from models.topology import EligibilityResult, JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot


SECRET = "test-secret-5.4"
VALID_HEADERS = {"X-Local-Secret": SECRET}


# ---------------------------------------------------------------------------
# Helpers communs
# ---------------------------------------------------------------------------

def _make_topology() -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-04-09T08:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={10: JeedomEqLogic(id=10, name="Lampe Salon", object_id=1, is_enable=True)},
    )


def _light_mapping(eq_id: int) -> MappingResult:
    return MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off_state",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Lumiere {eq_id}",
        suggested_area="Salon",
        commands={
            "LIGHT_ON": JeedomCmd(id=eq_id * 10 + 1, name="On", generic_type="LIGHT_ON", type="action", sub_type="other"),
            "LIGHT_OFF": JeedomCmd(id=eq_id * 10 + 2, name="Off", generic_type="LIGHT_OFF", type="action", sub_type="other"),
            "LIGHT_STATE": JeedomCmd(id=eq_id * 10 + 3, name="Etat", generic_type="LIGHT_STATE", type="info", sub_type="binary"),
        },
        capabilities=LightCapabilities(has_on_off=True),
    )


def _published_decision(mapping: MappingResult) -> PublicationDecision:
    return PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=mapping,
        state_topic=f"jeedom2ha/{mapping.jeedom_eq_id}/state",
        active_or_alive=True,
        discovery_published=True,
    )


def _make_published_scope() -> dict:
    return {
        "global": {
            "counts": {"total": 1, "include": 1, "exclude": 0, "exceptions": 0},
            "effective_state": "include",
            "has_pending_home_assistant_changes": True,
        },
        "pieces": [
            {
                "object_id": 1,
                "object_name": "Salon",
                "counts": {"total": 1, "include": 1, "exclude": 0, "exceptions": 0},
                "home_perimetre": "Incluse",
                "has_pending_home_assistant_changes": True,
            }
        ],
        "equipements": [
            {
                "eq_id": 10,
                "object_id": 1,
                "name": "Lampe Salon",
                "effective_state": "include",
                "decision_source": "global",
                "is_exception": False,
                "has_pending_home_assistant_changes": True,
            }
        ],
    }


def _make_app_with_eq10() -> http_server.web.Application:
    app = create_app(local_secret=SECRET)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    app["topology"] = _make_topology()
    app["published_scope"] = _make_published_scope()
    app["eligibility"] = {10: EligibilityResult(is_eligible=True, reason_code="eligible")}
    mapping = _light_mapping(10)
    app["mappings"] = {10: mapping}
    app["publications"] = {10: _published_decision(mapping)}
    return app


# ---------------------------------------------------------------------------
# AC 1, 4 — _build_operation_snapshot : structure
# ---------------------------------------------------------------------------

def test_build_operation_snapshot_retourne_six_champs():
    """_build_operation_snapshot retourne un dict avec exactement les 6 champs requis."""
    snap = _build_operation_snapshot(
        resultat="succes",
        intention="publier",
        portee="global",
        message="12 équipements mis à jour.",
        volume=12,
    )
    assert set(snap.keys()) == {"resultat", "intention", "portee", "message", "volume", "timestamp"}


def test_build_operation_snapshot_resultat_partiel_inchange():
    """_build_operation_snapshot ne normalise pas 'partiel' — la normalisation est faite avant l'appel."""
    snap = _build_operation_snapshot(
        resultat="partiel",
        intention="publier",
        portee="piece",
        message="3 mis à jour, 2 n'ont pas pu être traités.",
        volume=3,
    )
    assert snap["resultat"] == "partiel"
    assert snap["intention"] == "publier"
    assert snap["volume"] == 3


def test_build_operation_snapshot_champs_optionnels_none():
    """Champs optionnels valent None si non fournis."""
    snap = _build_operation_snapshot(resultat="aucun")
    assert snap["resultat"] == "aucun"
    assert snap["intention"] is None
    assert snap["portee"] is None
    assert snap["message"] is None
    assert snap["volume"] is None


def test_build_operation_snapshot_timestamp_iso_utc():
    """Le timestamp est une string ISO au format UTC."""
    snap = _build_operation_snapshot(resultat="succes")
    ts = snap["timestamp"]
    assert isinstance(ts, str)
    assert "T" in ts
    assert ts.endswith("+00:00")


# ---------------------------------------------------------------------------
# AC 4 — État initial via /system/status
# ---------------------------------------------------------------------------

async def test_system_status_init_derniere_operation_est_objet(aiohttp_client):
    """/system/status au démarrage : derniere_operation_resultat est un objet (non une string)."""
    app = create_app(local_secret=SECRET)
    cli = await aiohttp_client(app)

    resp = await cli.get("/system/status", headers=VALID_HEADERS)
    assert resp.status == 200
    data = await resp.json()
    op = data["payload"]["derniere_operation_resultat"]

    assert isinstance(op, dict), f"Attendu dict, obtenu {type(op)}: {op}"
    assert op["resultat"] == "aucun"
    assert op["intention"] is None
    assert op["portee"] is None
    assert op["message"] is None
    assert op["volume"] is None


# ---------------------------------------------------------------------------
# AC 3 — Non-régression /system/status
# ---------------------------------------------------------------------------

async def test_system_status_champs_existants_inchanges(aiohttp_client):
    """Non-régression : demon, broker, derniere_synchro_terminee toujours présents dans le payload."""
    app = create_app(local_secret=SECRET)
    cli = await aiohttp_client(app)

    resp = await cli.get("/system/status", headers=VALID_HEADERS)
    assert resp.status == 200
    payload = (await resp.json())["payload"]

    assert "demon" in payload
    assert "broker" in payload
    assert "derniere_synchro_terminee" in payload
    assert "derniere_operation_resultat" in payload


# ---------------------------------------------------------------------------
# AC 1 — Snapshot après publier
# ---------------------------------------------------------------------------

async def test_snapshot_apres_publier_global(aiohttp_client):
    """Après publier global : snapshot avec intention='publier', portee='global', volume≥0, message non null."""
    app = _make_app_with_eq10()
    cli = await aiohttp_client(app)

    publisher = MagicMock()
    publisher.publish_light = AsyncMock(return_value=True)

    with (
        patch("transport.http_server.DiscoveryPublisher", return_value=publisher),
        patch("transport.http_server.asyncio.sleep", new=AsyncMock()),
        patch("transport.http_server.save_publications_cache"),
    ):
        response = await cli.post(
            "/action/execute",
            json={"intention": "publier", "portee": "global", "selection": ["all"]},
            headers=VALID_HEADERS,
        )

    assert response.status == 200
    op = app["derniere_operation_resultat"]
    assert isinstance(op, dict)
    assert op["intention"] == "publier"
    assert op["portee"] == "global"
    assert op["resultat"] in ("succes", "partiel", "echec")
    assert op["message"] is not None
    assert isinstance(op["volume"], int) and op["volume"] >= 0


# ---------------------------------------------------------------------------
# AC 1 — Snapshot après supprimer
# ---------------------------------------------------------------------------

async def test_snapshot_apres_supprimer_equipement(aiohttp_client):
    """Après supprimer équipement : snapshot avec intention='supprimer', volume=equipements_supprimes."""
    app = _make_app_with_eq10()
    cli = await aiohttp_client(app)

    publisher = MagicMock()
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)

    with (
        patch("transport.http_server.DiscoveryPublisher", return_value=publisher),
        patch("transport.http_server.asyncio.sleep", new=AsyncMock()),
        patch("transport.http_server.save_publications_cache"),
    ):
        response = await cli.post(
            "/action/execute",
            json={"intention": "supprimer", "portee": "equipement", "selection": [10]},
            headers=VALID_HEADERS,
        )

    assert response.status == 200
    op = app["derniere_operation_resultat"]
    assert isinstance(op, dict)
    assert op["intention"] == "supprimer"
    assert op["portee"] == "equipement"
    assert op["resultat"] in ("succes", "partiel", "echec")
    assert op["message"] is not None
    assert op["volume"] == 1  # 1 équipement supprimé avec succès


# ---------------------------------------------------------------------------
# AC 2 — Snapshot après sync
# ---------------------------------------------------------------------------

async def test_snapshot_apres_sync_intention_et_portee_null(aiohttp_client):
    """Après sync : intention='sync', portee=null, volume=null, message non null."""
    app = create_app(local_secret=SECRET)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    app["topology"] = _make_topology()
    app["eligibility"] = {10: EligibilityResult(is_eligible=True, reason_code="eligible")}
    app["mappings"] = {10: _light_mapping(10)}
    app["publications"] = {}

    cli = await aiohttp_client(app)

    publisher = MagicMock()
    publisher.publish_light = AsyncMock(return_value=True)

    with (
        patch("transport.http_server.DiscoveryPublisher", return_value=publisher),
        patch("transport.http_server.asyncio.sleep", new=AsyncMock()),
        patch("transport.http_server.save_publications_cache"),
    ):
        response = await cli.post("/action/sync", json={}, headers=VALID_HEADERS)

    assert response.status == 200
    op = app["derniere_operation_resultat"]
    assert isinstance(op, dict)
    assert op["intention"] == "sync"
    assert op["portee"] is None
    assert op["volume"] is None
    assert op["message"] is not None
    assert op["resultat"] in ("succes", "partiel", "echec")
