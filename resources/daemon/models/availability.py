"""Availability contract helpers shared across daemon components (Story 3.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

AVAILABILITY_ONLINE = "online"
AVAILABILITY_OFFLINE = "offline"
AVAILABILITY_UNKNOWN = "unknown"

BRIDGE_AVAILABILITY_TOPIC = "jeedom2ha/bridge/status"
LOCAL_AVAILABILITY_TOPIC_TEMPLATE = "jeedom2ha/{eq_id}/availability"
AVAILABILITY_MODE_ALL = "all"


@dataclass(frozen=True)
class EntityAvailability:
    """Normalized availability contract for one published entity."""

    bridge_availability_topic: str = BRIDGE_AVAILABILITY_TOPIC
    eqlogic_availability_topic: Optional[str] = None
    local_availability_supported: bool = False
    local_availability_state: str = AVAILABILITY_UNKNOWN
    availability_reason: str = "bridge_only_no_reliable_signal"


def build_local_availability_topic(eq_id: int) -> str:
    """Build the frozen local availability topic contract for one eqLogic."""
    return LOCAL_AVAILABILITY_TOPIC_TEMPLATE.format(eq_id=int(eq_id))


def availability_from_eqlogic(eq_id: int, eqlogic: Any) -> EntityAvailability:
    """Create normalized availability metadata from one normalized eqLogic model."""
    if eqlogic is None:
        return EntityAvailability(availability_reason="missing_eqlogic")

    supported = bool(getattr(eqlogic, "local_availability_supported", False))
    state_raw = str(getattr(eqlogic, "local_availability_state", AVAILABILITY_UNKNOWN) or AVAILABILITY_UNKNOWN).lower()
    state = state_raw if state_raw in (AVAILABILITY_ONLINE, AVAILABILITY_OFFLINE) else AVAILABILITY_UNKNOWN
    reason = str(getattr(eqlogic, "local_availability_reason", "bridge_only_no_reliable_signal") or "bridge_only_no_reliable_signal")

    if not supported:
        return EntityAvailability(
            local_availability_supported=False,
            local_availability_state=AVAILABILITY_UNKNOWN,
            availability_reason=reason,
        )

    return EntityAvailability(
        eqlogic_availability_topic=build_local_availability_topic(eq_id),
        local_availability_supported=True,
        local_availability_state=state,
        availability_reason=reason,
    )


def availability_from_snapshot(eq_id: int, snapshot: Any) -> EntityAvailability:
    """Resolve availability metadata from a topology snapshot."""
    if snapshot is None:
        return EntityAvailability(availability_reason="missing_snapshot")
    eq_logics = getattr(snapshot, "eq_logics", None)
    if not isinstance(eq_logics, dict):
        return EntityAvailability(availability_reason="missing_eqlogic_registry")
    return availability_from_eqlogic(eq_id, eq_logics.get(eq_id))


def build_discovery_availability_fields(entity_availability: EntityAvailability) -> Dict[str, Any]:
    """Build Home Assistant MQTT availability fields for one discovery payload."""
    if not entity_availability.local_availability_supported or not entity_availability.eqlogic_availability_topic:
        return {"availability_topic": entity_availability.bridge_availability_topic}

    return {
        "availability": [
            entity_availability.bridge_availability_topic,
            entity_availability.eqlogic_availability_topic,
        ],
        "availability_mode": AVAILABILITY_MODE_ALL,
        "payload_available": AVAILABILITY_ONLINE,
        "payload_not_available": AVAILABILITY_OFFLINE,
    }
