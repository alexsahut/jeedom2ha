"""mapping.py — Data models for the mapping and publication pipeline.

Introduced in Story 2.2 for capability-based light mapping.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from models.topology import JeedomCmd


@dataclass
class LightCapabilities:
    """Cumulated light capabilities detected from Jeedom commands.

    Each capability is detected independently and then merged into a single
    entity — never two entities for the same eqLogic.
    """
    has_on_off: bool = False
    has_brightness: bool = False
    on_off_confidence: str = "unknown"       # "sure", "probable", "ambiguous"
    brightness_confidence: str = "unknown"   # "sure", "probable", "ambiguous"


@dataclass
class MappingResult:
    """Result of mapping a single Jeedom eqLogic to a Home Assistant entity.

    One MappingResult per eqLogic, with cumulated capabilities.
    """
    ha_entity_type: str                       # "light"
    confidence: str                           # global: worst(per-capability) = max() on semantic order
    reason_code: str                          # e.g. "light_on_off_brightness", "light_on_off_only"
    jeedom_eq_id: int
    ha_unique_id: str                         # "jeedom2ha_eq_{id}"
    ha_name: str
    suggested_area: Optional[str] = None
    commands: Dict[str, JeedomCmd] = field(default_factory=dict)   # generic_type -> JeedomCmd
    capabilities: LightCapabilities = field(default_factory=LightCapabilities)
    reason_details: Optional[Dict[str, Any]] = None


@dataclass
class PublicationDecision:
    """Whether a mapping result should be published via MQTT Discovery."""
    should_publish: bool
    reason: str                               # e.g. "sure", "probable_bounded", "ambiguous_skipped"
    mapping_result: MappingResult = field(default=None)  # type: ignore[assignment]
