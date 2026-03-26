"""Integration-style tests for Story 5.3 cleanup and boot reconciliation."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.availability import build_local_availability_topic
from transport.http_server import create_app


def _light_eq_payload(eq_id: int, *, is_enable: bool = True, timeout: int = 0) -> dict:
    return {
        "id": eq_id,
        "name": f"Eq {eq_id}",
        "object_id": 1,
        "is_enable": is_enable,
        "is_visible": True,
        "eq_type": "virtual",
        "is_excluded": False,
        "status": {"timeout": timeout},
        "cmds": [
            {"id": eq_id * 10 + 1, "name": "On", "generic_type": "LIGHT_ON", "type": "action", "sub_type": "other"},
            {"id": eq_id * 10 + 2, "name": "Off", "generic_type": "LIGHT_OFF", "type": "action", "sub_type": "other"},
            {"id": eq_id * 10 + 3, "name": "State", "generic_type": "LIGHT_STATE", "type": "info", "sub_type": "binary"},
        ],
    }


def _sync_request(eq_logics: list[dict]) -> dict:
    return {
        "action": "sync",
        "payload": {
            "objects": [{"id": 1, "name": "Salon"}],
            "eq_logics": eq_logics,
            "sync_config": {"confidence_policy": "sure_probable"},
        },
        "request_id": "req-test-boot",
        "timestamp": "2026-03-22T10:00:00Z",
    }


def _mock_publisher() -> MagicMock:
    publisher = MagicMock()
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    publisher.publish_light = AsyncMock(return_value=True)
    publisher.publish_cover = AsyncMock(return_value=True)
    publisher.publish_switch = AsyncMock(return_value=True)
    return publisher


@pytest.mark.asyncio
async def test_deleted_equipment_is_unpublished_and_removed_from_diagnostics(aiohttp_client):
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    publisher = _mock_publisher()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.save_publications_cache"
    ):
        first_response = await cli.post(
            "/action/sync",
            json=_sync_request([_light_eq_payload(355)]),
            headers={"X-Local-Secret": "test_secret"},
        )
        delete_response = await cli.post(
            "/action/sync",
            json=_sync_request([]),
            headers={"X-Local-Secret": "test_secret"},
        )

    assert first_response.status == 200
    assert delete_response.status == 200
    publisher.unpublish_by_eq_id.assert_awaited_once_with(355, entity_type="light")
    bridge.publish_message.assert_any_call(build_local_availability_topic(355), "", qos=1, retain=True)

    diagnostics = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
    diagnostics_payload = await diagnostics.json()
    assert diagnostics.status == 200
    assert diagnostics_payload["payload"]["equipments"] == []


@pytest.mark.asyncio
async def test_first_sync_reconciles_boot_cache_and_cleans_availability(aiohttp_client, caplog):
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)
    app["boot_cache"] = {355: {"entity_type": "light", "published": True}}

    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    publisher = _mock_publisher()

    with caplog.at_level("INFO"), patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.save_publications_cache"
    ):
        response = await cli.post(
            "/action/sync",
            json=_sync_request([]),
            headers={"X-Local-Secret": "test_secret"},
        )

    assert response.status == 200
    publisher.unpublish_by_eq_id.assert_awaited_once_with(355, entity_type="light")
    bridge.publish_message.assert_any_call(build_local_availability_topic(355), "", qos=1, retain=True)
    assert "[CLEANUP] eq_id=355" in caplog.text
    assert "boot_cache" in caplog.text
    assert app["boot_cache"] == {}


@pytest.mark.asyncio
async def test_disabled_equipment_is_unpublished_then_republished_after_reactivation(aiohttp_client):
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)

    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    publisher = _mock_publisher()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.save_publications_cache"
    ):
        publish_response = await cli.post(
            "/action/sync",
            json=_sync_request([_light_eq_payload(355, is_enable=True)]),
            headers={"X-Local-Secret": "test_secret"},
        )
        disable_response = await cli.post(
            "/action/sync",
            json=_sync_request([_light_eq_payload(355, is_enable=False)]),
            headers={"X-Local-Secret": "test_secret"},
        )

        diagnostics = await cli.get("/system/diagnostics", headers={"X-Local-Secret": "test_secret"})
        diagnostics_payload = await diagnostics.json()

        reactivate_response = await cli.post(
            "/action/sync",
            json=_sync_request([_light_eq_payload(355, is_enable=True)]),
            headers={"X-Local-Secret": "test_secret"},
        )

    assert publish_response.status == 200
    assert disable_response.status == 200
    assert reactivate_response.status == 200
    publisher.unpublish_by_eq_id.assert_awaited_once_with(355, entity_type="light")
    assert publisher.publish_light.await_count == 2

    eq = next(item for item in diagnostics_payload["payload"]["equipments"] if item["eq_id"] == 355)
    # Story 3.1 : disabled_eqlogic → "Non supporté" (pas "Non publié")
    assert eq["status"] == "Non supporté"
    assert eq["reason_code"] == "disabled_eqlogic"
    assert app["publications"][355].should_publish is True
