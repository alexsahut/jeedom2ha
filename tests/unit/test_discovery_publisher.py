"""test_discovery_publisher.py — Unit tests for MQTT Discovery publisher.

Story 2.2: Tests covering payload structure validations for light discovery.
"""
import json
import sys
import os
import pytest
from unittest.mock import MagicMock, AsyncMock

# Add daemon to path for direct model imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'daemon'))

from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from models.mapping import LightCapabilities, MappingResult
from discovery.publisher import DiscoveryPublisher


@pytest.fixture
def mock_mqtt_bridge():
    """Mock MqttBridge with a mock _client.publish."""
    bridge = MagicMock()
    bridge._client = MagicMock()
    bridge._client.publish = MagicMock()
    bridge.is_connected = True
    return bridge


@pytest.fixture
def publisher(mock_mqtt_bridge):
    return DiscoveryPublisher(mock_mqtt_bridge)


@pytest.fixture
def snapshot():
    """Snapshot with one object and one eqLogic."""
    eq = JeedomEqLogic(
        id=42,
        name="Plafonnier Salon",
        object_id=10,
        eq_type_name="zwave",
    )
    return TopologySnapshot(
        timestamp="2026-03-13T20:00:00+01:00",
        objects={10: JeedomObject(id=10, name="Salon")},
        eq_logics={42: eq},
    )


def _make_mapping(
    eq_id=42, name="Plafonnier Salon", confidence="sure",
    has_on_off=True, has_brightness=False, suggested_area="Salon",
):
    """Helper to create a MappingResult."""
    capabilities = LightCapabilities(
        has_on_off=has_on_off,
        has_brightness=has_brightness,
        on_off_confidence="sure" if has_on_off else "unknown",
        brightness_confidence="sure" if has_brightness else "unknown",
    )

    reason_code = "light_on_off_brightness" if has_brightness else "light_on_off_only"

    return MappingResult(
        ha_entity_type="light",
        confidence=confidence,
        reason_code=reason_code,
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=name,
        suggested_area=suggested_area,
        commands={},
        capabilities=capabilities,
    )


# ==============================================================================
# Test: On/Off payload structure
# ==============================================================================

class TestOnOffPayload:
    @pytest.mark.asyncio
    async def test_on_off_payload_has_required_fields(self, publisher, snapshot, mock_mqtt_bridge):
        """Payload On/Off contient tous les champs requis."""
        mapping = _make_mapping(has_brightness=False)
        await publisher.publish_light(mapping, snapshot)

        mock_mqtt_bridge._client.publish.assert_called_once()
        call_args = mock_mqtt_bridge._client.publish.call_args
        topic = call_args[0][0]
        payload = json.loads(call_args[0][1])

        # Required fields
        assert "state_topic" in payload
        assert payload["state_topic"] == "jeedom2ha/42/state"
        assert "command_topic" in payload
        assert payload["command_topic"] == "jeedom2ha/42/set"
        assert payload["payload_on"] == "ON"
        assert payload["payload_off"] == "OFF"
        assert "device" in payload
        assert "origin" in payload

    @pytest.mark.asyncio
    async def test_on_off_no_brightness_fields(self, publisher, snapshot, mock_mqtt_bridge):
        """Payload On/Off seul NE contient PAS de brightness fields."""
        mapping = _make_mapping(has_brightness=False)
        await publisher.publish_light(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge._client.publish.call_args[0][1])
        assert "brightness_state_topic" not in payload
        assert "brightness_command_topic" not in payload
        assert "brightness_scale" not in payload
        assert "supported_color_modes" not in payload
        assert "color_mode" not in payload


# ==============================================================================
# Test: On/Off + Brightness payload structure
# ==============================================================================

class TestBrightnessPayload:
    @pytest.mark.asyncio
    async def test_brightness_payload_has_all_fields(self, publisher, snapshot, mock_mqtt_bridge):
        """Payload On/Off+Brightness contient les champs brightness."""
        mapping = _make_mapping(has_brightness=True)
        await publisher.publish_light(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge._client.publish.call_args[0][1])
        assert payload["brightness_state_topic"] == "jeedom2ha/42/brightness"
        assert payload["brightness_command_topic"] == "jeedom2ha/42/brightness/set"
        assert payload["brightness_scale"] == 100
        assert payload["supported_color_modes"] == ["brightness"]
        assert payload["color_mode"] is True


# ==============================================================================
# Test: Topic format
# ==============================================================================

class TestTopicFormat:
    @pytest.mark.asyncio
    async def test_topic_format(self, publisher, snapshot, mock_mqtt_bridge):
        """Topic = homeassistant/light/jeedom2ha_{id}/config."""
        mapping = _make_mapping(eq_id=42)
        await publisher.publish_light(mapping, snapshot)

        topic = mock_mqtt_bridge._client.publish.call_args[0][0]
        assert topic == "homeassistant/light/jeedom2ha_42/config"

    @pytest.mark.asyncio
    async def test_custom_topic_prefix(self, mock_mqtt_bridge, snapshot):
        """Topic prefix customisable."""
        publisher = DiscoveryPublisher(mock_mqtt_bridge, topic_prefix="custom_ha")
        mapping = _make_mapping(eq_id=42)
        await publisher.publish_light(mapping, snapshot)

        topic = mock_mqtt_bridge._client.publish.call_args[0][0]
        assert topic == "custom_ha/light/jeedom2ha_42/config"


# ==============================================================================
# Test: Retain flag
# ==============================================================================

class TestRetainFlag:
    @pytest.mark.asyncio
    async def test_publish_with_retain(self, publisher, snapshot, mock_mqtt_bridge):
        """Publish avec retain=True."""
        mapping = _make_mapping()
        await publisher.publish_light(mapping, snapshot)

        call_kwargs = mock_mqtt_bridge._client.publish.call_args
        # publish(topic, payload, qos=1, retain=True)
        assert call_kwargs[1]["retain"] is True or call_kwargs[0][3] is True


# ==============================================================================
# Test: Unpublish
# ==============================================================================

class TestUnpublish:
    @pytest.mark.asyncio
    async def test_unpublish_sends_empty_payload(self, publisher, mock_mqtt_bridge):
        """Unpublish envoie payload vide avec retain=True."""
        await publisher.unpublish("jeedom2ha_eq_42")

        mock_mqtt_bridge._client.publish.assert_called_once()
        call_args = mock_mqtt_bridge._client.publish.call_args
        topic = call_args[0][0]
        payload = call_args[0][1]
        assert topic == "homeassistant/light/jeedom2ha_42/config"
        assert payload == ""
        # retain=True
        assert call_args[1]["retain"] is True or call_args[0][3] is True


# ==============================================================================
# Test: Device block
# ==============================================================================

class TestDeviceBlock:
    @pytest.mark.asyncio
    async def test_device_identifiers(self, publisher, snapshot, mock_mqtt_bridge):
        """device.identifiers contient jeedom2ha_{id}."""
        mapping = _make_mapping(eq_id=42)
        await publisher.publish_light(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge._client.publish.call_args[0][1])
        assert "jeedom2ha_42" in payload["device"]["identifiers"]

    @pytest.mark.asyncio
    async def test_device_via_device(self, publisher, snapshot, mock_mqtt_bridge):
        """device.via_device = jeedom2ha_bridge."""
        mapping = _make_mapping()
        await publisher.publish_light(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge._client.publish.call_args[0][1])
        assert payload["device"]["via_device"] == "jeedom2ha_bridge"

    @pytest.mark.asyncio
    async def test_device_manufacturer(self, publisher, snapshot, mock_mqtt_bridge):
        """device.manufacturer = Jeedom (eq_type_name)."""
        mapping = _make_mapping()
        await publisher.publish_light(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge._client.publish.call_args[0][1])
        assert payload["device"]["manufacturer"] == "Jeedom (zwave)"


# ==============================================================================
# Test: Origin block
# ==============================================================================

class TestOriginBlock:
    @pytest.mark.asyncio
    async def test_origin_name(self, publisher, snapshot, mock_mqtt_bridge):
        """origin.name = jeedom2ha."""
        mapping = _make_mapping()
        await publisher.publish_light(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge._client.publish.call_args[0][1])
        assert payload["origin"]["name"] == "jeedom2ha"

    @pytest.mark.asyncio
    async def test_origin_sw_version(self, publisher, snapshot, mock_mqtt_bridge):
        """origin.sw_version présent."""
        mapping = _make_mapping()
        await publisher.publish_light(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge._client.publish.call_args[0][1])
        assert "sw_version" in payload["origin"]


# ==============================================================================
# Test: Availability
# ==============================================================================

class TestAvailability:
    @pytest.mark.asyncio
    async def test_availability_topic(self, publisher, snapshot, mock_mqtt_bridge):
        """availability_topic = jeedom2ha/bridge/status."""
        mapping = _make_mapping()
        await publisher.publish_light(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge._client.publish.call_args[0][1])
        assert payload["availability_topic"] == "jeedom2ha/bridge/status"


# ==============================================================================
# Test: Suggested area absent when None
# ==============================================================================

class TestSuggestedArea:
    @pytest.mark.asyncio
    async def test_suggested_area_absent_when_none(self, publisher, snapshot, mock_mqtt_bridge):
        """suggested_area absent du device si l'objet Jeedom est None."""
        mapping = _make_mapping(suggested_area=None)
        await publisher.publish_light(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge._client.publish.call_args[0][1])
        assert "suggested_area" not in payload["device"]

    @pytest.mark.asyncio
    async def test_suggested_area_present_when_set(self, publisher, snapshot, mock_mqtt_bridge):
        """suggested_area présent dans device quand l'objet existe."""
        mapping = _make_mapping(suggested_area="Salon")
        await publisher.publish_light(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge._client.publish.call_args[0][1])
        assert payload["device"]["suggested_area"] == "Salon"
