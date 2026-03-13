"""publisher.py — MQTT Discovery publisher for Home Assistant.

Story 2.2: Publishes light entity discovery payloads to the MQTT broker.
Uses single-component discovery (homeassistant/light/...) as documented
exception for Story 2.2. Device discovery will be adopted in Story 2.3+.
"""
import json
import logging
from typing import Optional

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
        topic = self._build_topic(mapping.jeedom_eq_id)
        payload = self._build_light_payload(mapping, snapshot)
        payload_json = json.dumps(payload, ensure_ascii=False)

        _LOGGER.info(
            "[DISCOVERY] Publishing light config: topic=%s eq_id=%d name='%s' confidence=%s",
            topic, mapping.jeedom_eq_id, mapping.ha_name, mapping.confidence,
        )
        _LOGGER.debug("[DISCOVERY] Payload: %s", payload_json)

        try:
            self._mqtt_bridge._client.publish(topic, payload_json, qos=1, retain=True)
            return True
        except Exception as e:
            _LOGGER.error(
                "[DISCOVERY] Failed to publish light config for eq_id=%d: %s",
                mapping.jeedom_eq_id, e,
            )
            return False

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

    async def unpublish_by_eq_id(self, eq_id: int) -> bool:
        """Remove a discovery config by eq_id (robust method, avoids parsing string ID)."""
        topic = self._build_topic(eq_id)
        _LOGGER.info("[DISCOVERY] Unpublishing: topic=%s", topic)

        try:
            self._mqtt_bridge._client.publish(topic, "", qos=1, retain=True)
            return True
        except Exception as e:
            _LOGGER.error("[DISCOVERY] Failed to unpublish %s: %s", topic, e)
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_topic(self, eq_id: int) -> str:
        """Build the MQTT discovery topic for a light entity."""
        return f"{self._topic_prefix}/light/jeedom2ha_{eq_id}/config"

    def _build_light_payload(self, mapping: MappingResult, snapshot: TopologySnapshot) -> dict:
        """Build the MQTT Discovery JSON payload for a light entity.

        Includes brightness fields only if has_brightness=True.
        """
        eq_id = mapping.jeedom_eq_id

        # Retrieve eq info from snapshot for device metadata
        eq = snapshot.eq_logics.get(eq_id)
        eq_type_name = eq.eq_type_name if eq else ""
        manufacturer = f"Jeedom ({eq_type_name})" if eq_type_name else "Jeedom"

        # Build device block
        device = {
            "identifiers": [f"jeedom2ha_{eq_id}"],
            "name": mapping.ha_name,
            "manufacturer": manufacturer,
            "model": eq_type_name or "Unknown",
            "via_device": "jeedom2ha_bridge",
        }

        # suggested_area only if present
        if mapping.suggested_area:
            device["suggested_area"] = mapping.suggested_area

        payload = {
            "name": mapping.ha_name,
            "unique_id": mapping.ha_unique_id,
            "object_id": f"jeedom2ha_{eq_id}",
            "state_topic": f"jeedom2ha/{eq_id}/state",
            "command_topic": f"jeedom2ha/{eq_id}/set",
            "payload_on": "ON",
            "payload_off": "OFF",
            "availability_topic": "jeedom2ha/bridge/status",
            "device": device,
            "origin": {
                "name": "jeedom2ha",
                "sw_version": _SW_VERSION,
            },
        }

        # Add brightness fields if capability detected
        if mapping.capabilities.has_brightness:
            payload["brightness_state_topic"] = f"jeedom2ha/{eq_id}/brightness"
            payload["brightness_command_topic"] = f"jeedom2ha/{eq_id}/brightness/set"
            payload["brightness_scale"] = 100
            payload["supported_color_modes"] = ["brightness"]
            payload["color_mode"] = True

        return payload
