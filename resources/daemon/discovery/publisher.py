"""publisher.py — MQTT Discovery publisher for Home Assistant.

Story 2.2: Publishes light entity discovery payloads to the MQTT broker.
Story 2.3: Extended for cover entity discovery payloads.
Story 2.4: Extended for switch entity discovery payloads.
Uses single-component discovery (homeassistant/{entity_type}/...).
"""
import json
import logging
from typing import Optional

from models.availability import (
    availability_from_snapshot,
    build_discovery_availability_fields,
)
from models.mapping import MappingResult
from models.topology import TopologySnapshot

_LOGGER = logging.getLogger(__name__)

_SW_VERSION = "0.2.0"


class DiscoveryPublisher:
    """Publishes MQTT Discovery payloads for Home Assistant.

    Uses the MqttBridge for MQTT operations.
    """

    def __init__(self, mqtt_bridge, topic_prefix: str = "homeassistant"):
        """Initialize DiscoveryPublisher.

        Args:
            mqtt_bridge: MqttBridge instance (from transport/mqtt_client.py).
            topic_prefix: MQTT discovery prefix (default: "homeassistant").
        """
        self._mqtt_bridge = mqtt_bridge
        self._topic_prefix = topic_prefix

    async def publish_light(self, mapping: MappingResult, snapshot: TopologySnapshot) -> bool:
        """Publish a light discovery config to MQTT.

        Args:
            mapping: MappingResult with capabilities and confidence.
            snapshot: TopologySnapshot to extract device info.

        Returns:
            True if publish succeeded, False otherwise.
        """
        topic = self._build_topic(mapping.jeedom_eq_id, entity_type="light")
        payload = self._build_light_payload(mapping, snapshot)
        payload_json = json.dumps(payload, ensure_ascii=False)

        _LOGGER.info(
            "[DISCOVERY] Publishing light config: topic=%s eq_id=%d name='%s' confidence=%s",
            topic, mapping.jeedom_eq_id, mapping.ha_name, mapping.confidence,
        )
        _LOGGER.debug("[DISCOVERY] Payload: %s", payload_json)

        ok = self._mqtt_bridge.publish_message(topic, payload_json, qos=1, retain=True)
        if not ok:
            _LOGGER.error(
                "[DISCOVERY] Failed to publish light config for eq_id=%d (bridge unavailable)",
                mapping.jeedom_eq_id,
            )
        return ok

    async def publish_cover(self, mapping: MappingResult, snapshot: TopologySnapshot) -> bool:
        """Publish a cover discovery config to MQTT.

        Args:
            mapping: MappingResult with CoverCapabilities and confidence.
            snapshot: TopologySnapshot to extract device info.

        Returns:
            True if publish succeeded, False otherwise.
        """
        topic = self._build_topic(mapping.jeedom_eq_id, entity_type="cover")
        payload = self._build_cover_payload(mapping, snapshot)
        payload_json = json.dumps(payload, ensure_ascii=False)

        _LOGGER.info(
            "[DISCOVERY] Publishing cover config: topic=%s eq_id=%d name='%s' confidence=%s",
            topic, mapping.jeedom_eq_id, mapping.ha_name, mapping.confidence,
        )
        _LOGGER.debug("[DISCOVERY] Payload: %s", payload_json)

        ok = self._mqtt_bridge.publish_message(topic, payload_json, qos=1, retain=True)
        if not ok:
            _LOGGER.error(
                "[DISCOVERY] Failed to publish cover config for eq_id=%d (bridge unavailable)",
                mapping.jeedom_eq_id,
            )
        return ok

    async def publish_switch(self, mapping: MappingResult, snapshot: TopologySnapshot) -> bool:
        """Publish a switch discovery config to MQTT.

        Args:
            mapping: MappingResult with SwitchCapabilities and confidence.
            snapshot: TopologySnapshot to extract device info.

        Returns:
            True if publish succeeded, False otherwise.
        """
        topic = self._build_topic(mapping.jeedom_eq_id, entity_type="switch")
        payload = self._build_switch_payload(mapping, snapshot)
        payload_json = json.dumps(payload, ensure_ascii=False)

        _LOGGER.info(
            "[DISCOVERY] Publishing switch config: topic=%s eq_id=%d name='%s' confidence=%s",
            topic, mapping.jeedom_eq_id, mapping.ha_name, mapping.confidence,
        )
        _LOGGER.debug("[DISCOVERY] Payload: %s", payload_json)

        ok = self._mqtt_bridge.publish_message(topic, payload_json, qos=1, retain=True)
        if not ok:
            _LOGGER.error(
                "[DISCOVERY] Failed to publish switch config for eq_id=%d (bridge unavailable)",
                mapping.jeedom_eq_id,
            )
        return ok

    async def unpublish(self, ha_unique_id: str) -> bool:
        """Remove a discovery config by publishing empty payload with retain.

        Args:
            ha_unique_id: The unique ID to derive the topic from.
                          Expected format: jeedom2ha_eq_{id}

        Returns:
            True if unpublish succeeded, False otherwise.
        """
        # Feature héritée et fragile (Axe 6 de la Code Review).
        # On extrait eq_id depuis la chaîne. Pour un usage robuste au runtime,
        # utiliser plutôt unpublish_by_eq_id().
        try:
            eq_id = int(ha_unique_id.split("_")[-1])
        except (ValueError, IndexError):
            _LOGGER.error("[DISCOVERY] Cannot parse eq_id from unique_id: %s", ha_unique_id)
            return False

        return await self.unpublish_by_eq_id(eq_id)

    async def unpublish_by_eq_id(self, eq_id: int, entity_type: str = "light") -> bool:
        """Remove a discovery config by eq_id (robust method, avoids parsing string ID)."""
        topic = self._build_topic(eq_id, entity_type=entity_type)
        _LOGGER.info("[DISCOVERY] Unpublishing: topic=%s", topic)

        ok = self._mqtt_bridge.publish_message(topic, "", qos=1, retain=True)
        if not ok:
            _LOGGER.error("[DISCOVERY] Failed to unpublish %s (bridge unavailable)", topic)
        return ok

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_topic(self, eq_id: int, entity_type: str = "light") -> str:
        """Build the MQTT discovery topic for an entity."""
        return f"{self._topic_prefix}/{entity_type}/jeedom2ha_{eq_id}/config"

    def _build_device_block(self, mapping: MappingResult, snapshot: TopologySnapshot) -> dict:
        """Build the common device block for discovery payloads."""
        eq_id = mapping.jeedom_eq_id
        eq = snapshot.eq_logics.get(eq_id)
        eq_type_name = eq.eq_type_name if eq else ""
        manufacturer = f"Jeedom ({eq_type_name})" if eq_type_name else "Jeedom"

        device = {
            "identifiers": [f"jeedom2ha_{eq_id}"],
            "name": mapping.ha_name,
            "manufacturer": manufacturer,
            "model": eq_type_name or "Unknown",
            "via_device": "jeedom2ha_bridge",
        }

        if mapping.suggested_area:
            device["suggested_area"] = mapping.suggested_area

        return device

    def _build_availability_fields(self, mapping: MappingResult, snapshot: TopologySnapshot) -> dict:
        """Build availability payload fields (bridge-only or bridge+local)."""
        entity_availability = availability_from_snapshot(mapping.jeedom_eq_id, snapshot)
        return build_discovery_availability_fields(entity_availability)

    def _build_light_payload(self, mapping: MappingResult, snapshot: TopologySnapshot) -> dict:
        """Build the MQTT Discovery JSON payload for a light entity.

        Includes brightness fields only if has_brightness=True.
        """
        eq_id = mapping.jeedom_eq_id
        device = self._build_device_block(mapping, snapshot)

        payload = {
            "name": mapping.ha_name,
            "unique_id": mapping.ha_unique_id,
            "object_id": f"jeedom2ha_{eq_id}",
            "state_topic": f"jeedom2ha/{eq_id}/state",
            "command_topic": f"jeedom2ha/{eq_id}/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device": device,
            "origin": {
                "name": "jeedom2ha",
                "sw_version": _SW_VERSION,
            },
        }
        payload.update(self._build_availability_fields(mapping, snapshot))

        # Add brightness fields if capability detected
        if mapping.capabilities.has_brightness:
            payload["brightness_state_topic"] = f"jeedom2ha/{eq_id}/brightness"
            payload["brightness_command_topic"] = f"jeedom2ha/{eq_id}/brightness/set"
            payload["brightness_scale"] = 100
            payload["supported_color_modes"] = ["brightness"]
            payload["color_mode"] = True

        return payload

    def _build_cover_payload(self, mapping: MappingResult, snapshot: TopologySnapshot) -> dict:
        """Build the MQTT Discovery JSON payload for a cover entity.

        Includes conditional fields based on capabilities:
        - stop → payload_stop
        - position → position_topic, set_position_topic, position_open/closed
        - BSO → device_class = "blind" instead of "shutter"
        """
        eq_id = mapping.jeedom_eq_id
        device = self._build_device_block(mapping, snapshot)
        caps = mapping.capabilities

        # Default device_class: shutter (volet roulant) or blind (BSO)
        device_class = "blind" if caps.is_bso else "shutter"

        payload = {
            "name": mapping.ha_name,
            "unique_id": mapping.ha_unique_id,
            "object_id": f"jeedom2ha_{eq_id}",
            "command_topic": f"jeedom2ha/{eq_id}/set",
            "payload_open": "OPEN",
            "payload_close": "CLOSE",
            "state_topic": f"jeedom2ha/{eq_id}/state",
            "state_open": "open",
            "state_closed": "closed",
            "device_class": device_class,
            "device": device,
            "origin": {
                "name": "jeedom2ha",
                "sw_version": _SW_VERSION,
            },
        }
        payload.update(self._build_availability_fields(mapping, snapshot))

        # Conditional: Stop
        if caps.has_stop:
            payload["payload_stop"] = "STOP"

        # Conditional: Position
        if caps.has_position:
            payload["position_topic"] = f"jeedom2ha/{eq_id}/position"
            payload["set_position_topic"] = f"jeedom2ha/{eq_id}/position/set"
            payload["position_open"] = 100
            payload["position_closed"] = 0

        return payload

    def _build_switch_payload(self, mapping: MappingResult, snapshot: TopologySnapshot) -> dict:
        """Build the MQTT Discovery JSON payload for a switch entity.

        Includes device_class="outlet" only if capabilities.device_class == "outlet".
        The device_class field is ABSENT (not null) when None — per HA MQTT switch schema.
        No icon field is ever added.
        """
        eq_id = mapping.jeedom_eq_id
        device = self._build_device_block(mapping, snapshot)
        caps = mapping.capabilities

        payload = {
            "name": mapping.ha_name,
            "unique_id": mapping.ha_unique_id,
            "object_id": f"jeedom2ha_{eq_id}",
            "command_topic": f"jeedom2ha/{eq_id}/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "state_topic": f"jeedom2ha/{eq_id}/state",
            "state_on": "ON",
            "state_off": "OFF",
            "device": device,
            "origin": {
                "name": "jeedom2ha",
                "sw_version": _SW_VERSION,
            },
        }
        payload.update(self._build_availability_fields(mapping, snapshot))

        # Conditional: device_class — add ONLY if confirmed outlet, NEVER add null or "switch"
        if caps.device_class == "outlet":
            payload["device_class"] = "outlet"

        return payload
