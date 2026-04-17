"""Story 5.1 — orchestration canonique 5 étapes dans /action/sync."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.decide_publication import decide_publication as _real_decide_publication
from models.mapping import ProjectionValidity
from models.topology import assess_all as _real_assess_all
from transport.http_server import create_app
from validation.ha_component_registry import validate_projection as _real_validate_projection


SECRET = "test-secret-pe-5-1-orchestration"


def _sync_body(eq_logics: list[dict]) -> dict:
    return {
        "action": "sync",
        "payload": {
            "objects": [{"id": 1, "name": "Salon"}],
            "eq_logics": eq_logics,
            "sync_config": {"confidence_policy": "sure_probable"},
        },
        "request_id": "pe-5-1-test",
        "timestamp": "2026-04-16T00:00:00Z",
    }


def _light_eq_payload(eq_id: int, cmds: list[dict]) -> dict:
    return {
        "id": eq_id,
        "name": f"Lumiere {eq_id}",
        "object_id": 1,
        "is_enable": True,
        "is_visible": True,
        "eq_type": "virtual",
        "is_excluded": False,
        "status": {"timeout": 0},
        "cmds": cmds,
    }


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


@pytest.fixture
def mock_publisher():
    publisher = AsyncMock()
    publisher.publish_light = AsyncMock(return_value=True)
    publisher.publish_cover = AsyncMock(return_value=True)
    publisher.publish_switch = AsyncMock(return_value=True)
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    return publisher


def _set_connected_bridge(app):
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    app["mqtt_bridge"] = bridge


async def test_sync_executes_5_steps_in_order_and_publishes_valid_light(cli, app, mock_publisher):
    call_order: list[str] = []

    from mapping.light import LightMapper

    real_map = LightMapper.map

    def _assess_all_spy(snapshot):
        call_order.append("eligibility")
        return _real_assess_all(snapshot)

    def _map_spy(self, eq, snapshot):
        call_order.append("mapping")
        return real_map(self, eq, snapshot)

    def _validate_spy(entity_type, capabilities):
        call_order.append("validation")
        return _real_validate_projection(entity_type, capabilities)

    def _decide_spy(mapping, confidence_policy="sure_probable", product_scope=None):
        call_order.append("decision")
        return _real_decide_publication(
            mapping,
            confidence_policy=confidence_policy,
            product_scope=product_scope,
        )

    async def _publish_light_spy(mapping, snapshot):
        call_order.append("publication")
        return True

    mock_publisher.publish_light = AsyncMock(side_effect=_publish_light_spy)
    _set_connected_bridge(app)

    payload = _sync_body(
        [
            _light_eq_payload(
                101,
                [
                    {"id": 1, "name": "On", "generic_type": "LIGHT_ON", "type": "action", "sub_type": "other"},
                    {"id": 2, "name": "Off", "generic_type": "LIGHT_OFF", "type": "action", "sub_type": "other"},
                    {"id": 3, "name": "Etat", "generic_type": "LIGHT_STATE", "type": "info", "sub_type": "binary"},
                ],
            )
        ]
    )

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher), patch(
        "transport.http_server.assess_all",
        side_effect=_assess_all_spy,
    ), patch.object(LightMapper, "map", new=_map_spy), patch(
        "transport.http_server.validate_projection",
        side_effect=_validate_spy,
    ), patch(
        "transport.http_server.decide_publication",
        side_effect=_decide_spy,
    ):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"
    assert call_order == ["eligibility", "mapping", "validation", "decision", "publication"]

    mapping = app["mappings"][101]
    assert mapping.projection_validity is not None
    assert mapping.projection_validity.is_valid is True
    assert mapping.publication_decision_ref is not None
    assert mapping.publication_decision_ref.should_publish is True


async def test_sync_calls_decide_even_when_projection_invalid_and_never_publishes(cli, app, mock_publisher):
    calls: list[str] = []

    def _validate_invalid(_entity_type, _capabilities):
        calls.append("validation")
        return ProjectionValidity(
            is_valid=False,
            reason_code="ha_missing_command_topic",
            missing_fields=["command_topic"],
            missing_capabilities=["has_command"],
        )

    def _decide_spy(mapping, confidence_policy="sure_probable", product_scope=None):
        calls.append("decision")
        return _real_decide_publication(
            mapping,
            confidence_policy=confidence_policy,
            product_scope=product_scope,
        )

    _set_connected_bridge(app)
    payload = _sync_body(
        [
            _light_eq_payload(
                102,
                [
                    {"id": 1, "name": "On", "generic_type": "LIGHT_ON", "type": "action", "sub_type": "other"},
                    {"id": 2, "name": "Off", "generic_type": "LIGHT_OFF", "type": "action", "sub_type": "other"},
                    {"id": 3, "name": "Etat", "generic_type": "LIGHT_STATE", "type": "info", "sub_type": "binary"},
                ],
            )
        ]
    )

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher), patch(
        "transport.http_server.validate_projection",
        side_effect=_validate_invalid,
    ), patch(
        "transport.http_server.decide_publication",
        side_effect=_decide_spy,
    ):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"
    assert calls == ["validation", "decision"]
    mock_publisher.publish_light.assert_not_awaited()

    mapping = app["mappings"][102]
    assert mapping.projection_validity is not None
    assert mapping.projection_validity.is_valid is False
    assert mapping.projection_validity.reason_code == "ha_missing_command_topic"
    assert mapping.publication_decision_ref is not None
    assert mapping.publication_decision_ref.should_publish is False


async def test_light_without_mappable_action_sets_ha_missing_command_topic_and_no_publish(cli, app, mock_publisher):
    _set_connected_bridge(app)
    payload = _sync_body(
        [
            _light_eq_payload(
                103,
                [
                    {"id": 1, "name": "Etat", "generic_type": "LIGHT_STATE", "type": "info", "sub_type": "binary"},
                ],
            )
        ]
    )

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"
    mock_publisher.publish_light.assert_not_awaited()

    mapping = app["mappings"][103]
    assert mapping.projection_validity is not None
    assert mapping.projection_validity.reason_code == "ha_missing_command_topic"
    assert mapping.publication_decision_ref is not None
    assert mapping.publication_decision_ref.should_publish is False
