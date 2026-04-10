"""Story 5.3 — tests d'intégration backend autour de l'intention `supprimer`."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import transport.http_server as http_server
from models.mapping import LightCapabilities, MappingResult, PublicationDecision
from models.topology import EligibilityResult, JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot


SECRET = "test-secret-5.3-integration"
VALID_HEADERS = {"X-Local-Secret": SECRET}


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


def _make_topology() -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-04-07T08:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            10: JeedomEqLogic(id=10, name="Lampe Salon", object_id=1, is_enable=True),
            11: JeedomEqLogic(id=11, name="Prise Salon", object_id=1, is_enable=True),
        },
    )


def _make_published_scope() -> dict:
    return {
        "global": {
            "counts": {"total": 2, "include": 2, "exclude": 0, "exceptions": 0},
            "effective_state": "include",
            "has_pending_home_assistant_changes": False,
        },
        "pieces": [
            {
                "object_id": 1,
                "object_name": "Salon",
                "counts": {"total": 2, "include": 2, "exclude": 0, "exceptions": 0},
                "home_perimetre": "Incluse",
                "has_pending_home_assistant_changes": False,
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
                "has_pending_home_assistant_changes": False,
            },
            {
                "eq_id": 11,
                "object_id": 1,
                "name": "Prise Salon",
                "effective_state": "include",
                "decision_source": "global",
                "is_exception": False,
                "has_pending_home_assistant_changes": False,
            },
        ],
    }


def _publisher_mock() -> MagicMock:
    publisher = MagicMock()
    publisher.publish_light = AsyncMock(return_value=True)
    publisher.publish_cover = AsyncMock(return_value=True)
    publisher.publish_switch = AsyncMock(return_value=True)
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    return publisher


@pytest.fixture
def app():
    app = http_server.create_app(local_secret=SECRET)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    app["topology"] = _make_topology()
    app["published_scope"] = _make_published_scope()
    app["eligibility"] = {
        10: EligibilityResult(is_eligible=True, reason_code="eligible"),
        11: EligibilityResult(is_eligible=True, reason_code="eligible"),
    }
    app["mappings"] = {
        10: _light_mapping(10),
        11: _light_mapping(11),
    }
    app["publications"] = {
        10: _published_decision(app["mappings"][10]),
        11: _published_decision(app["mappings"][11]),
    }
    return app


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


async def _post_action(cli, payload: dict):
    return await cli.post("/action/execute", json=payload, headers=VALID_HEADERS)


async def _get_diagnostics(cli):
    response = await cli.get("/system/diagnostics", headers=VALID_HEADERS)
    assert response.status == 200
    body = await response.json()
    return {eq["eq_id"]: eq for eq in body["payload"]["equipments"]}


@pytest.mark.asyncio
async def test_actions_ha_switches_from_republier_to_creer_after_supprimer(cli):
    """After supprimer, the label must switch from Republier to Créer."""
    before = await _get_diagnostics(cli)
    assert before[10]["statut"] == "publie"
    assert before[10]["actions_ha"]["publier"]["label"] == "Republier dans Home Assistant"
    assert before[10]["actions_ha"]["supprimer"]["disponible"] is True

    publisher = _publisher_mock()
    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        response = await _post_action(
            cli,
            {"intention": "supprimer", "portee": "equipement", "selection": [10]},
        )

    assert response.status == 200
    payload = (await response.json())["payload"]
    assert payload["resultat"] == "succes"

    after = await _get_diagnostics(cli)
    assert after[10]["statut"] == "non_publie"
    assert after[10]["actions_ha"]["publier"]["label"] == "Créer dans Home Assistant"
    assert after[10]["actions_ha"]["supprimer"]["disponible"] is False


@pytest.mark.asyncio
async def test_4d_contract_and_reason_code_preserved_after_supprimer(cli):
    """Supprimer must not alter the 4D contract or reason_code."""
    before = await _get_diagnostics(cli)
    assert before[10]["perimetre"] == "inclus"
    assert before[10]["reason_code"] == "sure"

    publisher = _publisher_mock()
    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        await _post_action(
            cli,
            {"intention": "supprimer", "portee": "equipement", "selection": [10]},
        )

    after = await _get_diagnostics(cli)
    assert after[10]["perimetre"] == "inclus"
    assert after[10]["reason_code"] == "sure"
    assert after[10]["ecart"] is True


@pytest.mark.asyncio
async def test_supprimer_then_publier_round_trip(cli):
    """Validate the Supprimer → Créer round trip via API."""
    publisher = _publisher_mock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        # Step 1: Supprimer
        response = await _post_action(
            cli,
            {"intention": "supprimer", "portee": "equipement", "selection": [10]},
        )
    assert response.status == 200
    assert (await response.json())["payload"]["resultat"] == "succes"

    mid = await _get_diagnostics(cli)
    assert mid[10]["statut"] == "non_publie"
    assert mid[10]["actions_ha"]["publier"]["label"] == "Créer dans Home Assistant"

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        # Step 2: Créer (publier)
        response = await _post_action(
            cli,
            {"intention": "publier", "portee": "equipement", "selection": [10]},
        )
    assert response.status == 200
    assert (await response.json())["payload"]["resultat"] == "succes"

    after = await _get_diagnostics(cli)
    assert after[10]["statut"] == "publie"
    assert after[10]["actions_ha"]["publier"]["label"] == "Republier dans Home Assistant"
    assert after[10]["actions_ha"]["supprimer"]["disponible"] is True
