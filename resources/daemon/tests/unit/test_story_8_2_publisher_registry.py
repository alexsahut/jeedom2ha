"""Story 8.2 - PublisherRegistry dispatch table for discovery publishers."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from discovery.publisher import DiscoveryPublisher
from discovery.registry import PublisherRegistry, UnknownPublisherError
from models.mapping import LightCapabilities, MappingResult
from models.topology import TopologySnapshot


def _make_publisher() -> DiscoveryPublisher:
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    return DiscoveryPublisher(mqtt_bridge=mqtt_bridge)


def _make_snapshot() -> TopologySnapshot:
    return TopologySnapshot(timestamp="2026-05-03T00:00:00Z", objects={}, eq_logics={})


def _make_mapping(ha_entity_type: str, eq_id: int = 10) -> MappingResult:
    return MappingResult(
        ha_entity_type=ha_entity_type,
        confidence="sure",
        reason_code="light_on_off_state",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Equipement {eq_id}",
        capabilities=LightCapabilities(has_on_off=True),
    )


def test_ac1_registry_contains_exact_current_publishers():
    registry = PublisherRegistry(_make_publisher())

    assert set(registry.publishers.keys()) == {"light", "cover", "switch", "sensor"}


def test_known_types_classmethod_returns_static_types_without_instance():
    assert PublisherRegistry.known_types() == ["light", "cover", "switch", "sensor"]


def test_known_types_matches_publishers_dict():
    """Garantit que _known_types et _publishers sont en sync — détecte tout oubli de maintenance."""
    registry = PublisherRegistry(_make_publisher())
    assert set(PublisherRegistry.known_types()) == set(registry.publishers.keys())


def test_ac1_ac4_registry_excludes_binary_sensor_and_button():
    registry = PublisherRegistry(_make_publisher())
    keys = set(registry.publishers.keys())

    assert "binary_sensor" not in keys
    assert "button" not in keys


def test_ac2_resolve_light_returns_same_bound_method_as_discovery_publisher():
    publisher = _make_publisher()
    registry = PublisherRegistry(publisher)

    resolved = registry.resolve("light")

    assert resolved.__self__ is publisher
    assert resolved.__func__ is DiscoveryPublisher.publish_light


def test_ac2_resolve_cover_returns_same_bound_method_as_discovery_publisher():
    publisher = _make_publisher()
    registry = PublisherRegistry(publisher)

    resolved = registry.resolve("cover")

    assert resolved.__self__ is publisher
    assert resolved.__func__ is DiscoveryPublisher.publish_cover


def test_ac2_resolve_switch_returns_same_bound_method_as_discovery_publisher():
    publisher = _make_publisher()
    registry = PublisherRegistry(publisher)

    resolved = registry.resolve("switch")

    assert resolved.__self__ is publisher
    assert resolved.__func__ is DiscoveryPublisher.publish_switch


def test_ac2_resolve_sensor_returns_same_bound_method_as_discovery_publisher():
    publisher = _make_publisher()
    registry = PublisherRegistry(publisher)

    resolved = registry.resolve("sensor")

    assert resolved.__self__ is publisher
    assert resolved.__func__ is DiscoveryPublisher.publish_sensor


def test_ac3_resolve_unknown_type_raises_explicit_error_and_logs(caplog):
    registry = PublisherRegistry(_make_publisher())
    caplog.set_level(logging.ERROR)

    with pytest.raises(UnknownPublisherError) as exc_info:
        registry.resolve("binary_sensor")

    assert exc_info.value.ha_entity_type == "binary_sensor"
    assert exc_info.value.technical_reason_code == "publisher_not_registered"
    assert "No publisher registered for ha_entity_type=binary_sensor" in caplog.text


@pytest.mark.asyncio
async def test_ac3_publish_unknown_type_sets_failed_publication_result():
    registry = PublisherRegistry(_make_publisher())
    mapping = _make_mapping("binary_sensor", eq_id=42)

    published = await registry.publish(mapping, _make_snapshot())

    assert published is False
    assert mapping.publication_result is not None
    assert mapping.publication_result.status == "failed"
    assert mapping.publication_result.technical_reason_code == "publisher_not_registered"
    assert mapping.publication_result.attempted_at is not None


@pytest.mark.asyncio
async def test_delegates_known_type_to_registered_publish_method():
    publisher = _make_publisher()
    publisher.publish_light = AsyncMock(return_value=True)
    registry = PublisherRegistry(publisher)
    mapping = _make_mapping("light", eq_id=10)
    snapshot = _make_snapshot()

    published = await registry.publish(mapping, snapshot)

    assert published is True
    publisher.publish_light.assert_awaited_once_with(mapping, snapshot)
