"""Story 16.7 — cross-type override discovery build must not crash.

A type override (D11) keeps the *detected* capabilities dataclass unchanged and only
forces `ha_entity_type`. The discovery payload builders must therefore tolerate a
capabilities object whose concrete type does not match the forced entity type
(e.g. a native light forced to `switch` still carries `LightCapabilities`).

Regression: the terrain gate for pe-epic-16 surfaced
`AttributeError: 'LightCapabilities' object has no attribute 'device_class'`
raised by `_build_switch_payload` on a light-forced-to-switch override.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from discovery.publisher import DiscoveryPublisher
from models.mapping import (
    CoverCapabilities,
    LightCapabilities,
    MappingResult,
    SwitchCapabilities,
)
from models.topology import TopologySnapshot


def _make_publisher() -> DiscoveryPublisher:
    return DiscoveryPublisher(mqtt_bridge=MagicMock())


def _make_snapshot() -> TopologySnapshot:
    return TopologySnapshot(timestamp="2026-07-17T00:00:00Z", objects={}, eq_logics={})


def _make_mapping(ha_entity_type: str, capabilities, eq_id: int = 42) -> MappingResult:
    return MappingResult(
        ha_entity_type=ha_entity_type,
        confidence="sure",
        reason_code="override_forced",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Equipement {eq_id}",
        capabilities=capabilities,
        reason_details={"override_applied": True, "override_source": "user"},
    )


def test_light_capabilities_forced_to_switch_builds_without_crash():
    publisher = _make_publisher()
    mapping = _make_mapping("switch", LightCapabilities(has_on_off=True))
    payload = publisher._build_switch_payload(mapping, _make_snapshot())
    # LightCapabilities has no device_class → outlet field must be absent.
    assert "device_class" not in payload
    assert payload["command_topic"] == "jeedom2ha/42/set"


def test_cover_capabilities_forced_to_switch_builds_without_crash():
    publisher = _make_publisher()
    mapping = _make_mapping("switch", CoverCapabilities(has_position=True, has_stop=True))
    payload = publisher._build_switch_payload(mapping, _make_snapshot())
    assert "device_class" not in payload


def test_switch_capabilities_forced_to_light_builds_without_crash():
    publisher = _make_publisher()
    mapping = _make_mapping("light", SwitchCapabilities(has_on_off=True, device_class="outlet"))
    payload = publisher._build_light_payload(mapping, _make_snapshot())
    # SwitchCapabilities has no has_brightness → brightness fields absent, no crash.
    assert "brightness_state_topic" not in payload
    assert payload["command_topic"] == "jeedom2ha/42/set"


def test_light_capabilities_forced_to_cover_builds_without_crash():
    publisher = _make_publisher()
    mapping = _make_mapping("cover", LightCapabilities(has_on_off=True))
    payload = publisher._build_cover_payload(mapping, _make_snapshot())
    # LightCapabilities lacks is_bso/has_stop/has_position → shutter default, no extras.
    assert payload["device_class"] == "shutter"
    assert "payload_stop" not in payload
    assert "position_topic" not in payload


def test_outlet_switch_still_emits_device_class():
    publisher = _make_publisher()
    mapping = _make_mapping("switch", SwitchCapabilities(has_on_off=True, device_class="outlet"))
    payload = publisher._build_switch_payload(mapping, _make_snapshot())
    assert payload["device_class"] == "outlet"
