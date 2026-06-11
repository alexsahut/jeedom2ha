"""publisher.py — MQTT Discovery publisher for Home Assistant.

Story 2.2: Publishes light entity discovery payloads to the MQTT broker.
Story 2.3: Extended for cover entity discovery payloads.
Story 2.4: Extended for switch entity discovery payloads.
Story 9.1: Extended for sensor entity discovery payloads.
Story 9.2: Extended for binary_sensor entity discovery payloads.
Story 9.3: Extended for button entity discovery payloads.
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

    async def publish_sensor(self, mapping: MappingResult, snapshot: TopologySnapshot) -> bool:
        """Publish a sensor discovery config to MQTT.

        Args:
            mapping: MappingResult with SensorCapabilities and reason_details (device_class, unit_of_measurement).
            snapshot: TopologySnapshot to extract device info.

        Returns:
            True if publish succeeded, False otherwise.
        """
        topic = self._build_topic(mapping.jeedom_eq_id, entity_type="sensor")
        payload = self._build_sensor_payload(mapping, snapshot)
        payload_json = json.dumps(payload, ensure_ascii=False)

        _LOGGER.info(
            "[DISCOVERY] Publishing sensor config: topic=%s eq_id=%d name='%s' confidence=%s",
            topic, mapping.jeedom_eq_id, mapping.ha_name, mapping.confidence,
        )
        _LOGGER.debug("[DISCOVERY] Payload: %s", payload_json)

        ok = self._mqtt_bridge.publish_message(topic, payload_json, qos=1, retain=True)
        if not ok:
            _LOGGER.error(
                "[DISCOVERY] Failed to publish sensor config for eq_id=%d (bridge unavailable)",
                mapping.jeedom_eq_id,
            )
        return ok

    async def publish_binary_sensor(self, mapping: MappingResult, snapshot: TopologySnapshot) -> bool:
        """Publish a binary_sensor discovery config to MQTT.

        Args:
            mapping: MappingResult with SensorCapabilities and reason_details (device_class).
            snapshot: TopologySnapshot to extract device info.

        Returns:
            True if publish succeeded, False otherwise.
        """
        topic = self._build_topic(mapping.jeedom_eq_id, entity_type="binary_sensor")
        payload = self._build_binary_sensor_payload(mapping, snapshot)
        payload_json = json.dumps(payload, ensure_ascii=False)

        _LOGGER.info(
            "[DISCOVERY] Publishing binary_sensor config: topic=%s eq_id=%d name='%s' confidence=%s",
            topic, mapping.jeedom_eq_id, mapping.ha_name, mapping.confidence,
        )
        _LOGGER.debug("[DISCOVERY] Payload: %s", payload_json)

        ok = self._mqtt_bridge.publish_message(topic, payload_json, qos=1, retain=True)
        if not ok:
            _LOGGER.error(
                "[DISCOVERY] Failed to publish binary_sensor config for eq_id=%d (bridge unavailable)",
                mapping.jeedom_eq_id,
            )
        return ok

    async def publish_button(self, mapping: MappingResult, snapshot: TopologySnapshot) -> bool:
        """Publish a button discovery config to MQTT.

        Args:
            mapping: MappingResult with SwitchCapabilities and reason_details (command_topic).
            snapshot: TopologySnapshot to extract device info.

        Returns:
            True if publish succeeded, False otherwise.
        """
        reason_details = mapping.reason_details or {}
        node_id = reason_details.get("node_id") if isinstance(reason_details.get("node_id"), str) else None
        topic = self._build_topic(mapping.jeedom_eq_id, entity_type="button", node_id=node_id)
        payload = self._build_button_payload(mapping, snapshot)
        payload_json = json.dumps(payload, ensure_ascii=False)

        _LOGGER.info(
            "[DISCOVERY] Publishing button config: topic=%s eq_id=%d name='%s' confidence=%s",
            topic, mapping.jeedom_eq_id, mapping.ha_name, mapping.confidence,
        )
        _LOGGER.debug("[DISCOVERY] Payload: %s", payload_json)

        ok = self._mqtt_bridge.publish_message(topic, payload_json, qos=1, retain=True)
        if not ok:
            _LOGGER.error(
                "[DISCOVERY] Failed to publish button config for eq_id=%d (bridge unavailable)",
                mapping.jeedom_eq_id,
            )
        return ok

    async def publish_climate(self, mapping: MappingResult, snapshot: TopologySnapshot) -> bool:
        """Publish a climate discovery config to MQTT.

        Args:
            mapping: MappingResult with ClimateCapabilities and reason_details.
            snapshot: TopologySnapshot to extract device info.

        Returns:
            True if publish succeeded, False otherwise.
        """
        topic = self._build_topic(mapping.jeedom_eq_id, entity_type="climate")
        payload = self._build_climate_payload(mapping, snapshot)
        payload_json = json.dumps(payload, ensure_ascii=False)

        _LOGGER.info(
            "[DISCOVERY] Publishing climate config: topic=%s eq_id=%d name='%s' confidence=%s",
            topic, mapping.jeedom_eq_id, mapping.ha_name, mapping.confidence,
        )
        _LOGGER.debug("[DISCOVERY] Payload: %s", payload_json)

        ok = self._mqtt_bridge.publish_message(topic, payload_json, qos=1, retain=True)
        if not ok:
            _LOGGER.error(
                "[DISCOVERY] Failed to publish climate config for eq_id=%d (bridge unavailable)",
                mapping.jeedom_eq_id,
            )
        return ok

    async def publish_alarm_control_panel(self, mapping: MappingResult, snapshot: TopologySnapshot) -> bool:
        """Publish an alarm_control_panel discovery config to MQTT.

        Args:
            mapping: MappingResult with AlarmCapabilities and reason_details.
            snapshot: TopologySnapshot to extract device info.

        Returns:
            True if publish succeeded, False otherwise.
        """
        topic = self._build_topic(mapping.jeedom_eq_id, entity_type="alarm_control_panel")
        payload = self._build_alarm_control_panel_payload(mapping, snapshot)
        payload_json = json.dumps(payload, ensure_ascii=False)

        _LOGGER.info(
            "[DISCOVERY] Publishing alarm_control_panel config: topic=%s eq_id=%d name='%s' confidence=%s",
            topic, mapping.jeedom_eq_id, mapping.ha_name, mapping.confidence,
        )
        _LOGGER.debug("[DISCOVERY] Payload: %s", payload_json)

        ok = self._mqtt_bridge.publish_message(topic, payload_json, qos=1, retain=True)
        if not ok:
            _LOGGER.error(
                "[DISCOVERY] Failed to publish alarm_control_panel config for eq_id=%d (bridge unavailable)",
                mapping.jeedom_eq_id,
            )
        return ok

    async def unpublish(self, ha_unique_id: str) -> bool:
        """Remove a discovery config by publishing empty payload with retain.

        Args:
            ha_unique_id: The unique ID to derive the topic from.
                          Formats: jeedom2ha_eq_{id} (eqLogic) or jeedom2ha_scenario_{id} (scenario).

        Returns:
            True if unpublish succeeded, False otherwise.
        """
        # Scenario unique_ids use their full id as node_id (e.g. jeedom2ha_scenario_20).
        if ha_unique_id.startswith("jeedom2ha_scenario_"):
            topic = self._build_topic(0, entity_type="button", node_id=ha_unique_id)
            _LOGGER.info("[DISCOVERY] Unpublishing scenario: topic=%s", topic)
            ok = self._mqtt_bridge.publish_message(topic, "", qos=1, retain=True)
            if not ok:
                _LOGGER.error("[DISCOVERY] Failed to unpublish scenario %s (bridge unavailable)", ha_unique_id)
            return ok

        # Legacy eqLogic path: extract integer eq_id from jeedom2ha_eq_{id} or jeedom2ha_{id}.
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

    def _build_topic(self, eq_id: int, entity_type: str = "light", node_id: Optional[str] = None) -> str:
        """Build the MQTT discovery topic for an entity."""
        path_part = node_id if node_id else f"jeedom2ha_{eq_id}"
        return f"{self._topic_prefix}/{entity_type}/{path_part}/config"

    def _build_device_block(self, mapping: MappingResult, snapshot: TopologySnapshot) -> dict:
        """Build the common device block for discovery payloads."""
        eq_id = mapping.jeedom_eq_id
        eq = snapshot.eq_logics.get(eq_id)
        eq_type_name = eq.eq_type_name if eq else ""
        manufacturer = f"Jeedom ({eq_type_name})" if eq_type_name else "Jeedom"

        # Scenario buttons use ha_unique_id as device identifier to avoid collision
        # with eqLogics that may share the same integer id (Story 10.1).
        reason_details = mapping.reason_details or {}
        source_kind = reason_details.get("source_kind", "eqlogic")
        device_id = mapping.ha_unique_id if source_kind == "scenario" else f"jeedom2ha_{eq_id}"

        device = {
            "identifiers": [device_id],
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

    def _build_sensor_payload(self, mapping: MappingResult, snapshot: TopologySnapshot) -> dict:
        """Build the MQTT Discovery JSON payload for a sensor entity."""
        eq_id = mapping.jeedom_eq_id
        device = self._build_device_block(mapping, snapshot)
        reason_details = mapping.reason_details or {}
        device_class = reason_details.get("device_class")
        unit_of_measurement = reason_details.get("unit_of_measurement")

        payload = {
            "name": mapping.ha_name,
            "unique_id": mapping.ha_unique_id,
            "object_id": f"jeedom2ha_{eq_id}",
            "state_topic": f"jeedom2ha/{eq_id}/state",
            "platform": "mqtt",
            "device": device,
            "origin": {
                "name": "jeedom2ha",
                "sw_version": _SW_VERSION,
            },
        }
        payload.update(self._build_availability_fields(mapping, snapshot))

        if device_class is not None:
            payload["device_class"] = device_class
        if unit_of_measurement is not None:
            payload["unit_of_measurement"] = unit_of_measurement

        return payload

    def _build_binary_sensor_payload(self, mapping: MappingResult, snapshot: TopologySnapshot) -> dict:
        """Build the MQTT Discovery JSON payload for a binary_sensor entity."""
        eq_id = mapping.jeedom_eq_id
        device = self._build_device_block(mapping, snapshot)
        reason_details = mapping.reason_details or {}
        device_class = reason_details.get("device_class")

        payload = {
            "name": mapping.ha_name,
            "unique_id": mapping.ha_unique_id,
            "object_id": f"jeedom2ha_{eq_id}",
            "state_topic": f"jeedom2ha/{eq_id}/state",
            "platform": "mqtt",
            "device": device,
            "origin": {
                "name": "jeedom2ha",
                "sw_version": _SW_VERSION,
            },
        }
        payload.update(self._build_availability_fields(mapping, snapshot))

        if device_class is not None:
            payload["device_class"] = device_class

        return payload

    def _build_climate_payload(self, mapping: MappingResult, snapshot: TopologySnapshot) -> dict:
        """Build the MQTT Discovery JSON payload for a climate (thermostat) entity.

        Minimal useful payload: temperature setpoint + current temperature when available.
        Scope: residential thermostat, no advanced HVAC modes (Story 10.2 guardrail).
        """
        eq_id = mapping.jeedom_eq_id
        device = self._build_device_block(mapping, snapshot)
        reason_details = mapping.reason_details or {}

        payload = {
            "name": mapping.ha_name,
            "unique_id": mapping.ha_unique_id,
            "object_id": f"jeedom2ha_{eq_id}",
            "temperature_command_topic": reason_details.get(
                "temperature_command_topic", f"jeedom2ha/{eq_id}/temperature/set"
            ),
            "temperature_state_topic": reason_details.get(
                "temperature_state_topic", f"jeedom2ha/{eq_id}/temperature/state"
            ),
            "modes": ["heat", "off"],
            "platform": "mqtt",
            "device": device,
            "origin": {
                "name": "jeedom2ha",
                "sw_version": _SW_VERSION,
            },
        }
        payload.update(self._build_availability_fields(mapping, snapshot))

        current_temperature_topic = reason_details.get("current_temperature_topic")
        if current_temperature_topic:
            payload["current_temperature_topic"] = current_temperature_topic

        return payload

    def _build_alarm_control_panel_payload(self, mapping: MappingResult, snapshot: TopologySnapshot) -> dict:
        """Build the MQTT Discovery JSON payload for an alarm_control_panel entity.

        Minimal useful payload: state + arming/disarming commands.
        Scope: armed_away / disarmed states only (Story 10.3 guardrail).
        """
        eq_id = mapping.jeedom_eq_id
        device = self._build_device_block(mapping, snapshot)

        payload = {
            "name": mapping.ha_name,
            "unique_id": mapping.ha_unique_id,
            "object_id": f"jeedom2ha_{eq_id}",
            "state_topic": f"jeedom2ha/{eq_id}/alarm/state",
            "command_topic": f"jeedom2ha/{eq_id}/alarm/set",
            "value_template": "{{ 'armed_away' if value == '1' else 'disarmed' }}",
            "payload_disarm": "DISARM",
            "payload_arm_home": "ARM_HOME",
            "payload_arm_away": "ARM_AWAY",
            "platform": "mqtt",
            "device": device,
            "origin": {
                "name": "jeedom2ha",
                "sw_version": _SW_VERSION,
            },
        }
        payload.update(self._build_availability_fields(mapping, snapshot))

        return payload

    def _build_button_payload(self, mapping: MappingResult, snapshot: TopologySnapshot) -> dict:
        """Build the MQTT Discovery JSON payload for a button entity.

        No state_topic: button is command-only (no persistent state in HA).
        command_topic uses /cmd (not /set) to distinguish from switch/light actuators.
        Supports node_id override in reason_details for scenario buttons (Story 10.1).
        """
        eq_id = mapping.jeedom_eq_id
        device = self._build_device_block(mapping, snapshot)
        reason_details = mapping.reason_details or {}
        command_topic = reason_details.get("command_topic", f"jeedom2ha/{eq_id}/cmd")
        object_id = reason_details.get("node_id") or f"jeedom2ha_{eq_id}"

        payload = {
            "name": mapping.ha_name,
            "unique_id": mapping.ha_unique_id,
            "object_id": object_id,
            "command_topic": command_topic,
            "platform": "mqtt",
            "device": device,
            "origin": {
                "name": "jeedom2ha",
                "sw_version": _SW_VERSION,
            },
        }
        payload.update(self._build_availability_fields(mapping, snapshot))

        return payload
