"""Story 5.2 — tests d'intégration backend autour de l'intention `publier`."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import transport.http_server as http_server
from models.mapping import LightCapabilities, MappingResult, PublicationDecision
from models.topology import EligibilityResult, JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot


SECRET = "test-secret-5.2-integration"
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


def _unpublished_decision(mapping: MappingResult) -> PublicationDecision:
    return PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=mapping,
        state_topic=f"jeedom2ha/{mapping.jeedom_eq_id}/state",
        active_or_alive=False,
        discovery_published=False,
    )


def _make_topology() -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-04-06T08:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            10: JeedomEqLogic(id=10, name="Lampe Salon", object_id=1, is_enable=True),
            11: JeedomEqLogic(id=11, name="Prise Salon", object_id=1, is_enable=True),
            12: JeedomEqLogic(id=12, name="Lampe exclue", object_id=1, is_enable=True, is_excluded=True, exclusion_source="eqlogic"),
        },
    )


def _make_published_scope() -> dict:
    return {
        "global": {
            "counts": {"total": 3, "include": 2, "exclude": 1, "exceptions": 0},
            "effective_state": "include",
            "has_pending_home_assistant_changes": True,
        },
        "pieces": [
            {
                "object_id": 1,
                "object_name": "Salon",
                "counts": {"total": 3, "include": 2, "exclude": 1, "exceptions": 0},
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
            {
                "eq_id": 12,
                "object_id": 1,
                "name": "Lampe exclue",
                "effective_state": "exclude",
                "decision_source": "equipement",
                "is_exception": True,
                "has_pending_home_assistant_changes": True,
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
        12: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
    }
    app["mappings"] = {
        10: _light_mapping(10),
        11: _light_mapping(11),
        12: _light_mapping(12),
    }
    app["publications"] = {
        10: _unpublished_decision(app["mappings"][10]),
        11: _published_decision(app["mappings"][11]),
        12: _published_decision(app["mappings"][12]),
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
async def test_actions_ha_switches_from_creer_to_republier_after_publish(cli):
    before = await _get_diagnostics(cli)
    assert before[10]["statut"] == "non_publie"
    assert before[10]["actions_ha"]["publier"]["label"] == "Créer dans Home Assistant"

    publisher = _publisher_mock()
    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        response = await _post_action(
            cli,
            {"intention": "publier", "portee": "equipement", "selection": [10]},
        )

    assert response.status == 200
    after = await _get_diagnostics(cli)
    assert after[10]["statut"] == "publie"
    assert after[10]["actions_ha"]["publier"]["label"] == "Republier dans Home Assistant"


@pytest.mark.asyncio
async def test_scope_enforcement_resolves_excluded_gap_without_altering_4d_contract(cli):
    before = await _get_diagnostics(cli)
    assert before[12]["perimetre"] == "exclu_sur_equipement"
    assert before[12]["statut"] == "publie"
    assert before[12]["ecart"] is True
    assert before[12]["reason_code"] == "excluded_eqlogic"

    publisher = _publisher_mock()
    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        response = await _post_action(
            cli,
            {"intention": "publier", "portee": "piece", "selection": [1]},
        )

    assert response.status == 200
    publisher.unpublish_by_eq_id.assert_awaited_once_with(12, entity_type="light")

    after = await _get_diagnostics(cli)
    assert after[12]["perimetre"] == "exclu_sur_equipement"
    assert after[12]["statut"] == "non_publie"
    assert after[12]["ecart"] is False
    assert after[12]["reason_code"] == "excluded_eqlogic"
