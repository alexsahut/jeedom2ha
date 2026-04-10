"""mapping.py — Data models for the mapping and publication pipeline.

Introduced in Story 2.2 for capability-based light mapping.
Extended in Story 2.3 for cover mapping.
Extended in Story 2.4 for switch mapping.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

from models.availability import BRIDGE_AVAILABILITY_TOPIC, AVAILABILITY_UNKNOWN
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
class CoverCapabilities:
    """Cumulated cover capabilities detected from Jeedom FLAP_* commands.

    Each capability is detected independently and cumulated into a single
    cover entity per eqLogic. Story 2.3.
    """
    has_open_close: bool = False
    has_stop: bool = False
    has_position: bool = False
    is_bso: bool = False                     # Brise-Soleil Orientable
    open_close_confidence: str = "unknown"   # "sure", "probable", "ambiguous"
    position_confidence: str = "unknown"     # "sure", "probable"


@dataclass
class SwitchCapabilities:
    """Switch capabilities detected from Jeedom ENERGY_* commands.

    Story 2.4 — one SwitchCapabilities per eqLogic.
    """
    has_on_off: bool = False
    has_state: bool = False              # ENERGY_STATE present among cmds
    on_off_confidence: str = "unknown"   # "sure", "probable", "ambiguous"
    device_class: Optional[str] = None   # "outlet" if confirmed by eq_type_name, None otherwise


MappingCapabilities = Union[LightCapabilities, CoverCapabilities, SwitchCapabilities]


@dataclass
class ProjectionValidity:
    """Résultat de validation HA pour un candidat de mapping (étape 3 du pipeline).

    Sémantique de is_valid :
    - None  : sous-bloc skipped — étape 3 non exécutée (upstream a échoué)
    - True  : candidat valide, projection autorisée
    - False : candidat invalide, publication bloquée

    Introduit en Story 1.1 — câblage effectif en Epic 3.
    """
    is_valid: Optional[bool]           # True/False/None (None = skipped)
    reason_code: Optional[str]         # None si valide
    missing_fields: List[str]          # champs HA requis non satisfaits
    missing_capabilities: List[str]    # capabilities moteur absentes


@dataclass
class MappingResult:
    """Result of mapping a single Jeedom eqLogic to a Home Assistant entity.

    One MappingResult per eqLogic, with cumulated capabilities.

    ``capabilities`` is a REQUIRED field even though it has a sentinel default of None.
    Always pass it explicitly — omitting it raises ValueError at construction time.
    """
    ha_entity_type: str                       # "light", "cover"
    confidence: str                           # global: worst(per-capability) = max() on semantic order
    reason_code: str                          # e.g. "light_on_off_brightness", "cover_open_close"
    jeedom_eq_id: int
    ha_unique_id: str                         # "jeedom2ha_eq_{id}"
    ha_name: str
    suggested_area: Optional[str] = None
    commands: Dict[str, JeedomCmd] = field(default_factory=dict)   # generic_type -> JeedomCmd
    # Sentinel default=None so dataclass field ordering is respected.
    # __post_init__ enforces that callers always provide an explicit value.
    capabilities: Optional[Union[LightCapabilities, CoverCapabilities, "SwitchCapabilities"]] = None
    reason_details: Optional[Dict[str, object]] = None
    projection_validity: Optional[ProjectionValidity] = None
    publication_decision_ref: Optional["PublicationDecision"] = None

    def __post_init__(self) -> None:
        if self.capabilities is None:
            raise ValueError(
                "MappingResult requires an explicit 'capabilities' argument "
                "(LightCapabilities or CoverCapabilities). "
                "Do not rely on the default — it is a sentinel, not a usable value."
            )


@dataclass
class PublicationDecision:
    """Whether a mapping result should be published via MQTT Discovery."""
    should_publish: bool
    reason: str                               # e.g. "sure", "probable_bounded", "ambiguous_skipped"
    mapping_result: MappingResult = field(default=None)  # type: ignore[assignment]
    state_topic: Optional[str] = None
    active_or_alive: bool = True
    discovery_published: bool = False
    bridge_availability_topic: str = BRIDGE_AVAILABILITY_TOPIC
    eqlogic_availability_topic: Optional[str] = None
    local_availability_supported: bool = False
    local_availability_state: str = AVAILABILITY_UNKNOWN
    availability_reason: str = "bridge_only_no_reliable_signal"
