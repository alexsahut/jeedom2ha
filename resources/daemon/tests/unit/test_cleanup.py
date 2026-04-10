"""Unit tests for Story 5.3 cleanup hardening."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from models.availability import AVAILABILITY_OFFLINE, build_local_availability_topic
from models.mapping import LightCapabilities, MappingResult, PublicationDecision
from models.topology import JeedomCmd
from transport.http_server import create_app


def _light_mapping(eq_id: int = 355) -> MappingResult:
    return MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off_state",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Light {eq_id}",
        commands={
            "LIGHT_ON": JeedomCmd(id=eq_id * 10 + 1, name="On", generic_type="LIGHT_ON", type="action", sub_type="other"),
            "LIGHT_OFF": JeedomCmd(id=eq_id * 10 + 2, name="Off", generic_type="LIGHT_OFF", type="action", sub_type="other"),
            "LIGHT_STATE": JeedomCmd(id=eq_id * 10 + 3, name="State", generic_type="LIGHT_STATE", type="info", sub_type="binary"),
        },
        capabilities=LightCapabilities(has_on_off=True),
    )


def _published_decision(
    mapping: MappingResult,
    *,
    local_availability_supported: bool = True,
    local_availability_state: str = "online",
) -> PublicationDecision:
    return PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=mapping,
        state_topic=f"jeedom2ha/{mapping.jeedom_eq_id}/state",
        active_or_alive=True,
        discovery_published=True,
        eqlogic_availability_topic=build_local_availability_topic(mapping.jeedom_eq_id),
        local_availability_supported=local_availability_supported,
        local_availability_state=local_availability_state,
    )


def _light_eq_payload(
    eq_id: int,
    *,
    is_enable: bool = True,
    is_excluded: bool = False,
    exclusion_source: str | None = None,
    timeout: int | None = 0,
    cmds: list[dict] | None = None,
) -> dict:
    return {
        "id": eq_id,
        "name": f"Eq {eq_id}",
        "object_id": 1,
        "is_enable": is_enable,
        "is_visible": True,
        "eq_type": "virtual",
        "is_excluded": is_excluded,
        "exclusion_source": exclusion_source,
        "status": {} if timeout is None else {"timeout": timeout},
        "cmds": cmds
        or [
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
        "request_id": "req-test-cleanup",
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
async def test_standard_cleanup_clears_local_availability_even_when_local_support_flag_is_false(aiohttp_client):
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)
    mapping = _light_mapping(eq_id=355)
    app["mappings"][355] = mapping
    app["publications"][355] = _published_decision(mapping, local_availability_supported=False)

    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    publisher = _mock_publisher()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
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
    assert app["pending_discovery_unpublish"] == {}
    assert app["pending_local_availability_cleanup"] == {}
    assert 355 not in app["mappings"]
    assert 355 not in app["publications"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("eq_logics", "expected_reason"),
    [
        ([], "supprimé dans Jeedom"),
        ([_light_eq_payload(355, is_enable=False)], "désactivé dans Jeedom (disabled_eqlogic)"),
        ([_light_eq_payload(355, is_excluded=True, exclusion_source="eqlogic")], "exclu (excluded_eqlogic)"),
        (
            [
                _light_eq_payload(
                    355,
                    cmds=[
                        {"id": 3551, "name": "Raw", "generic_type": "", "type": "info", "sub_type": "numeric"},
                    ],
                )
            ],
            "devenu inéligible (no_supported_generic_type)",
        ),
    ],
)
async def test_cleanup_logs_classify_deleted_disabled_excluded_and_ineligible_cases(
    aiohttp_client,
    caplog,
    eq_logics,
    expected_reason,
):
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)
    mapping = _light_mapping(eq_id=355)
    app["mappings"][355] = mapping
    app["publications"][355] = _published_decision(mapping)

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
            json=_sync_request(eq_logics),
            headers={"X-Local-Secret": "test_secret"},
        )

    assert response.status == 200
    publisher.unpublish_by_eq_id.assert_awaited_once_with(355, entity_type="light")
    assert "[CLEANUP] eq_id=355" in caplog.text
    assert expected_reason in caplog.text


@pytest.mark.asyncio
async def test_deferred_unpublish_and_availability_cleanup_are_replayed_after_broker_reconnect(aiohttp_client):
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)
    mapping = _light_mapping(eq_id=355)
    app["mappings"][355] = mapping
    app["publications"][355] = _published_decision(mapping, local_availability_supported=False)

    bridge = MagicMock()
    bridge.is_connected = False
    app["mqtt_bridge"] = bridge
    first_publisher = _mock_publisher()

    with patch("transport.http_server.DiscoveryPublisher", return_value=first_publisher), patch(
        "transport.http_server.save_publications_cache"
    ):
        first_response = await cli.post(
            "/action/sync",
            json=_sync_request([]),
            headers={"X-Local-Secret": "test_secret"},
        )

    assert first_response.status == 200
    first_publisher.unpublish_by_eq_id.assert_not_awaited()
    assert app["pending_discovery_unpublish"] == {355: "light"}
    assert app["pending_local_availability_cleanup"] == {355: build_local_availability_topic(355)}

    bridge.is_connected = True
    bridge.publish_message.return_value = True
    bridge.reset_mock()
    replay_publisher = _mock_publisher()

    with patch("transport.http_server.DiscoveryPublisher", return_value=replay_publisher), patch(
        "transport.http_server.save_publications_cache"
    ):
        replay_response = await cli.post(
            "/action/sync",
            json=_sync_request([]),
            headers={"X-Local-Secret": "test_secret"},
        )

    assert replay_response.status == 200
    replay_publisher.unpublish_by_eq_id.assert_awaited_once_with(355, entity_type="light")
    bridge.publish_message.assert_any_call(build_local_availability_topic(355), "", qos=1, retain=True)
    assert app["pending_discovery_unpublish"] == {}
    assert app["pending_local_availability_cleanup"] == {}


@pytest.mark.asyncio
async def test_runtime_offline_keeps_discovery_and_publishes_offline_local_availability(aiohttp_client):
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)
    mapping = _light_mapping(eq_id=355)
    app["mappings"][355] = mapping
    app["publications"][355] = _published_decision(mapping)

    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    publisher = _mock_publisher()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.save_publications_cache"
    ):
        response = await cli.post(
            "/action/sync",
            json=_sync_request([_light_eq_payload(355, timeout=1)]),
            headers={"X-Local-Secret": "test_secret"},
        )

    assert response.status == 200
    publisher.unpublish_by_eq_id.assert_not_awaited()
    bridge.publish_message.assert_any_call(build_local_availability_topic(355), AVAILABILITY_OFFLINE, qos=1, retain=True)
    assert app["publications"][355].local_availability_state == AVAILABILITY_OFFLINE


@pytest.mark.asyncio
async def test_disabled_eqlogic_unpublishes_instead_of_publishing_runtime_offline(aiohttp_client):
    app = create_app(local_secret="test_secret")
    cli = await aiohttp_client(app)
    mapping = _light_mapping(eq_id=355)
    app["mappings"][355] = mapping
    app["publications"][355] = _published_decision(mapping)

    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    publisher = _mock_publisher()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.save_publications_cache"
    ):
        response = await cli.post(
            "/action/sync",
            json=_sync_request([_light_eq_payload(355, is_enable=False)]),
            headers={"X-Local-Secret": "test_secret"},
        )

    assert response.status == 200
    publisher.unpublish_by_eq_id.assert_awaited_once_with(355, entity_type="light")
    assert call(build_local_availability_topic(355), AVAILABILITY_OFFLINE, qos=1, retain=True) not in bridge.publish_message.mock_calls
