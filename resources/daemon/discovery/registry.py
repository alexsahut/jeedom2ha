"""registry.py - Dispatch registry from ha_entity_type to discovery publishers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict

from discovery.publisher import DiscoveryPublisher
from models.mapping import MappingResult, PublicationResult
from models.topology import TopologySnapshot

PublishMethod = Callable[[MappingResult, TopologySnapshot], Awaitable[bool]]

_LOGGER = logging.getLogger(__name__)


class UnknownPublisherError(KeyError):
    """Raised when no discovery publisher is registered for an HA entity type."""

    technical_reason_code = "publisher_not_registered"

    def __init__(self, ha_entity_type: str) -> None:
        self.ha_entity_type = ha_entity_type
        super().__init__(ha_entity_type)


class PublisherRegistry:
    """Fixed dispatch table for existing discovery publishers."""

    _known_types = ["light", "cover", "switch", "sensor", "binary_sensor", "button"]

    def __init__(self, publisher: DiscoveryPublisher) -> None:
        self._publishers: Dict[str, PublishMethod] = {
            "light": publisher.publish_light,
            "cover": publisher.publish_cover,
            "switch": publisher.publish_switch,
            "sensor": publisher.publish_sensor,
            "binary_sensor": publisher.publish_binary_sensor,
            "button": publisher.publish_button,
        }

    @classmethod
    def known_types(cls) -> list[str]:
        """Return the static list of known publisher types without instantiation."""
        return list(cls._known_types)

    @property
    def publishers(self) -> Dict[str, PublishMethod]:
        return dict(self._publishers)

    def resolve(self, ha_entity_type: str) -> PublishMethod:
        try:
            return self._publishers[ha_entity_type]
        except KeyError:
            _LOGGER.error(
                "[DISCOVERY] No publisher registered for ha_entity_type=%s",
                ha_entity_type,
            )
            raise UnknownPublisherError(ha_entity_type) from None

    async def publish(self, mapping: MappingResult, snapshot: TopologySnapshot) -> bool:
        try:
            publish_method = self.resolve(mapping.ha_entity_type)
        except UnknownPublisherError as exc:
            mapping.publication_result = PublicationResult(
                status="failed",
                technical_reason_code=exc.technical_reason_code,
                attempted_at=datetime.now(timezone.utc).isoformat(),
            )
            return False
        return await publish_method(mapping, snapshot)
