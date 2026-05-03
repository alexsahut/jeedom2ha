"""Story 8.3 - http_server._run_sync registry-driven dispatch."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mapping.registry import MapperRegistry as RealMapperRegistry
from models.mapping import (
    LightCapabilities,
    MappingResult,
    ProjectionValidity,
    PublicationDecision,
    PublicationResult,
    SensorCapabilities,
)
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot
from transport import http_server
from transport.http_server import create_app


SECRET = "test-secret-story-8-3-dispatch"


def _cmd(cmd_id: int, generic_type: str, *, type_: str = "action", sub_type: str = "other") -> dict:
    return {
        "id": cmd_id,
        "name": generic_type,
        "generic_type": generic_type,
        "type": type_,
        "sub_type": sub_type,
    }


def _eq_payload(eq_id: int, name: str, cmds: list[dict], *, eq_type: str = "virtual") -> dict:
    return {
        "id": eq_id,
        "name": name,
        "object_id": 1,
        "is_enable": True,
        "is_visible": True,
        "eq_type": eq_type,
        "is_excluded": False,
        "status": {"timeout": 0},
        "cmds": cmds,
    }


def _light_eq(eq_id: int = 101) -> dict:
    return _eq_payload(
        eq_id,
        f"Lumiere {eq_id}",
        [
            _cmd(eq_id * 10 + 1, "LIGHT_ON"),
            _cmd(eq_id * 10 + 2, "LIGHT_OFF"),
            _cmd(eq_id * 10 + 3, "LIGHT_STATE", type_="info", sub_type="binary"),
        ],
    )


def _cover_eq(eq_id: int = 201) -> dict:
    return _eq_payload(
        eq_id,
        f"Volet {eq_id}",
        [
            _cmd(eq_id * 10 + 1, "FLAP_UP"),
            _cmd(eq_id * 10 + 2, "FLAP_DOWN"),
            _cmd(eq_id * 10 + 3, "FLAP_STATE", type_="info", sub_type="numeric"),
        ],
    )


def _switch_eq(eq_id: int = 301) -> dict:
    return _eq_payload(
        eq_id,
        f"Prise {eq_id}",
        [
            _cmd(eq_id * 10 + 1, "ENERGY_ON"),
            _cmd(eq_id * 10 + 2, "ENERGY_OFF"),
            _cmd(eq_id * 10 + 3, "ENERGY_STATE", type_="info", sub_type="binary"),
        ],
        eq_type="prise",
    )


def _unmapped_eq(eq_id: int = 401) -> dict:
    return _eq_payload(
        eq_id,
        f"Temperature {eq_id}",
        [_cmd(eq_id * 10 + 1, "TEMPERATURE", type_="info", sub_type="numeric")],
    )


def _sync_body(eq_logics: list[dict]) -> dict:
    return {
        "action": "sync",
        "payload": {
            "objects": [{"id": 1, "name": "Salon"}],
            "eq_logics": eq_logics,
            "sync_config": {"confidence_policy": "sure_probable"},
        },
        "request_id": "story-8-3-test",
        "timestamp": "2026-05-03T00:00:00Z",
    }


def _connected_bridge(app):
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    app["mqtt_bridge"] = bridge
    return bridge


def _discovery_publisher_mock():
    publisher = MagicMock()
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    return publisher


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


class _RecordingPublisherRegistry:
    instances: list["_RecordingPublisherRegistry"] = []

    def __init__(self, _publisher):
        self.publishers = {
            "light": object(),
            "cover": object(),
            "switch": object(),
        }
        self.published_types: list[str] = []
        _RecordingPublisherRegistry.instances.append(self)

    async def publish(self, mapping, snapshot):
        self.published_types.append(mapping.ha_entity_type)
        return True


async def test_run_sync_uses_mapper_registry_and_preserves_current_mapping_types(cli, app):
    _connected_bridge(app)
    real_registry = RealMapperRegistry()
    mapper_registry = MagicMock()
    mapper_registry.map.side_effect = real_registry.map
    _RecordingPublisherRegistry.instances = []

    with patch("transport.http_server.MapperRegistry", return_value=mapper_registry), patch(
        "transport.http_server.PublisherRegistry",
        _RecordingPublisherRegistry,
    ), patch(
        "transport.http_server.DiscoveryPublisher",
        return_value=_discovery_publisher_mock(),
    ), patch(
        "transport.http_server.save_publications_cache",
    ):
        response = await cli.post(
            "/action/sync",
            json=_sync_body([_light_eq(), _cover_eq(), _switch_eq(), _unmapped_eq()]),
            headers={"X-Local-Secret": SECRET},
        )

    assert response.status == 200
    assert mapper_registry.map.call_count == 4
    assert app["mappings"][101].ha_entity_type == "light"
    assert app["mappings"][201].ha_entity_type == "cover"
    assert app["mappings"][301].ha_entity_type == "switch"
    assert 401 not in app["mappings"]


async def test_run_sync_publishes_light_cover_and_switch_through_publisher_registry(cli, app):
    _connected_bridge(app)
    _RecordingPublisherRegistry.instances = []

    with patch("transport.http_server.PublisherRegistry", _RecordingPublisherRegistry), patch(
        "transport.http_server.DiscoveryPublisher",
        return_value=_discovery_publisher_mock(),
    ), patch(
        "transport.http_server.save_publications_cache",
    ):
        response = await cli.post(
            "/action/sync",
            json=_sync_body([_light_eq(), _cover_eq(), _switch_eq()]),
            headers={"X-Local-Secret": SECRET},
        )

    assert response.status == 200
    assert len(_RecordingPublisherRegistry.instances) == 1
    assert _RecordingPublisherRegistry.instances[0].published_types == ["light", "cover", "switch"]


async def test_unknown_publisher_reason_is_preserved_without_discovery_failure_overwrite(cli, app):
    _connected_bridge(app)

    sensor_mapping = MappingResult(
        ha_entity_type="sensor",
        confidence="sure",
        reason_code="sensor_state",
        jeedom_eq_id=501,
        ha_unique_id="jeedom2ha_eq_501",
        ha_name="Temperature 501",
        capabilities=SensorCapabilities(has_state=True),
    )
    mapper_registry = MagicMock()
    mapper_registry.map.return_value = sensor_mapping

    class _UnknownPublisherRegistry:
        def __init__(self, _publisher):
            self.publishers = {"light": object(), "cover": object(), "switch": object()}

        async def publish(self, mapping, snapshot):
            mapping.publication_result = PublicationResult(
                status="failed",
                technical_reason_code="publisher_not_registered",
                attempted_at="2026-05-03T00:00:00+00:00",
            )
            return False

    with patch("transport.http_server.MapperRegistry", return_value=mapper_registry), patch(
        "transport.http_server.PublisherRegistry",
        _UnknownPublisherRegistry,
    ), patch(
        "transport.http_server.DiscoveryPublisher",
        return_value=_discovery_publisher_mock(),
    ), patch(
        "transport.http_server.validate_projection",
        return_value=ProjectionValidity(is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[]),
    ), patch(
        "transport.http_server.decide_publication",
        return_value=PublicationDecision(should_publish=True, reason="sure"),
    ), patch(
        "transport.http_server.save_publications_cache",
    ):
        response = await cli.post(
            "/action/sync",
            json=_sync_body([_unmapped_eq(501)]),
            headers={"X-Local-Secret": SECRET},
        )

    assert response.status == 200
    mapping = app["mappings"][501]
    decision = app["publications"][501]
    assert mapping.publication_result is not None
    assert mapping.publication_result.status == "failed"
    assert mapping.publication_result.technical_reason_code == "publisher_not_registered"
    assert decision.active_or_alive is False


def test_prepare_publication_bookkeeping_populates_common_runtime_fields_once():
    eq_id = 601
    mapping = MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off_state",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Lumiere {eq_id}",
        capabilities=LightCapabilities(has_on_off=True),
    )
    decision = PublicationDecision(should_publish=True, reason="sure", mapping_result=mapping)
    snapshot = TopologySnapshot(
        timestamp="2026-05-03T00:00:00Z",
        objects={},
        eq_logics={
            eq_id: JeedomEqLogic(
                id=eq_id,
                name=f"Lumiere {eq_id}",
                local_availability_supported=True,
                local_availability_state="online",
                local_availability_reason="timeout_zero",
            )
        },
    )
    publications = {}
    nouveaux_eq_ids = set()

    http_server._prepare_publication_bookkeeping(
        eq_id,
        mapping,
        decision,
        snapshot,
        publications,
        nouveaux_eq_ids,
    )

    assert decision.state_topic == f"jeedom2ha/{eq_id}/state"
    assert decision.active_or_alive is False
    assert decision.local_availability_supported is True
    assert publications == {eq_id: decision}
    assert nouveaux_eq_ids == {eq_id}


def test_mapping_counters_are_built_from_registry_publishers_with_legacy_compatible_keys():
    registry = MagicMock()
    registry.publishers = {
        "light": object(),
        "cover": object(),
        "switch": object(),
        "fan": object(),
    }

    counters = http_server._build_mapping_counters_from_publisher_registry(registry)

    assert counters == {
        "lights_sure": 0,
        "lights_probable": 0,
        "lights_ambiguous": 0,
        "lights_published": 0,
        "lights_skipped": 0,
        "covers_sure": 0,
        "covers_probable": 0,
        "covers_ambiguous": 0,
        "covers_published": 0,
        "covers_skipped": 0,
        "switches_sure": 0,
        "switches_probable": 0,
        "switches_ambiguous": 0,
        "switches_published": 0,
        "switches_skipped": 0,
        "fans_sure": 0,
        "fans_probable": 0,
        "fans_ambiguous": 0,
        "fans_published": 0,
        "fans_skipped": 0,
    }


async def test_mapping_summary_uses_dynamic_counter_keys_and_semantic_values(cli, app):
    _connected_bridge(app)
    _RecordingPublisherRegistry.instances = []

    with patch("transport.http_server.PublisherRegistry", _RecordingPublisherRegistry), patch(
        "transport.http_server.DiscoveryPublisher",
        return_value=_discovery_publisher_mock(),
    ), patch(
        "transport.http_server.save_publications_cache",
    ):
        response = await cli.post(
            "/action/sync",
            json=_sync_body([_light_eq(), _cover_eq(), _switch_eq()]),
            headers={"X-Local-Secret": SECRET},
        )

    assert response.status == 200
    data = await response.json()
    summary = data["payload"]["mapping_summary"]
    assert summary["lights_sure"] == 1
    assert summary["covers_sure"] == 1
    assert summary["switches_sure"] == 1
    assert summary["lights_published"] == 1
    assert summary["covers_published"] == 1
    assert summary["switches_published"] == 1
    assert summary["lights_skipped"] == 0
    assert summary["covers_skipped"] == 0
    assert summary["switches_skipped"] == 0
