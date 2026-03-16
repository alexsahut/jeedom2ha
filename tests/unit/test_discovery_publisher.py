"""test_discovery_publisher.py — Unit tests for MQTT Discovery publisher.

Story 2.2: Tests covering payload structure validations for light discovery.
Story 2.3: Extended for cover entity discovery payload validation.
Story 2.4: Extended for switch entity discovery payload validation.
"""
import json
import sys
import os
import pytest
from unittest.mock import MagicMock, AsyncMock

# Add daemon to path for direct model imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'daemon'))

from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from models.mapping import LightCapabilities, CoverCapabilities, SwitchCapabilities, MappingResult
from discovery.publisher import DiscoveryPublisher


@pytest.fixture
def mock_mqtt_bridge():
    """Mock MqttBridge with a mock publish_message method."""
    bridge = MagicMock()
    bridge.publish_message = MagicMock(return_value=True)
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


@pytest.fixture
def snapshot_with_local_availability():
    eq = JeedomEqLogic(
        id=42,
        name="Plafonnier Salon",
        object_id=10,
        eq_type_name="zwave",
    )
    eq.local_availability_supported = True
    eq.local_availability_state = "offline"
    eq.local_availability_reason = "timeout_one"
    return TopologySnapshot(
        timestamp="2026-03-13T20:00:00+01:00",
        objects={10: JeedomObject(id=10, name="Salon")},
        eq_logics={42: eq},
    )


def _make_mapping(
    eq_id=42, name="Plafonnier Salon", confidence="sure",
    has_on_off=True, has_brightness=False, suggested_area="Salon",
):
    """Helper to create a light MappingResult."""
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


def _make_cover_mapping(
    eq_id=42, name="Volet Salon", confidence="sure",
    has_open_close=True, has_stop=False, has_position=False,
    is_bso=False, suggested_area="Salon",
):
    """Helper to create a cover MappingResult."""
    capabilities = CoverCapabilities(
        has_open_close=has_open_close,
        has_stop=has_stop,
        has_position=has_position,
        is_bso=is_bso,
        open_close_confidence="sure" if has_open_close else "unknown",
        position_confidence="sure" if has_position else "unknown",
    )

    return MappingResult(
        ha_entity_type="cover",
        confidence=confidence,
        reason_code="cover_open_close",
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

        mock_mqtt_bridge.publish_message.assert_called_once()
        call_args = mock_mqtt_bridge.publish_message.call_args
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

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
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

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
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

        topic = mock_mqtt_bridge.publish_message.call_args[0][0]
        assert topic == "homeassistant/light/jeedom2ha_42/config"

    @pytest.mark.asyncio
    async def test_custom_topic_prefix(self, mock_mqtt_bridge, snapshot):
        """Topic prefix customisable."""
        publisher = DiscoveryPublisher(mock_mqtt_bridge, topic_prefix="custom_ha")
        mapping = _make_mapping(eq_id=42)
        await publisher.publish_light(mapping, snapshot)

        topic = mock_mqtt_bridge.publish_message.call_args[0][0]
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

        call_kwargs = mock_mqtt_bridge.publish_message.call_args
        # publish_message(topic, payload, qos=1, retain=True)
        assert call_kwargs[1]["retain"] is True or call_kwargs[0][3] is True


# ==============================================================================
# Test: Unpublish
# ==============================================================================

class TestUnpublish:
    @pytest.mark.asyncio
    async def test_unpublish_sends_empty_payload(self, publisher, mock_mqtt_bridge):
        """Unpublish envoie payload vide avec retain=True."""
        await publisher.unpublish("jeedom2ha_eq_42")

        mock_mqtt_bridge.publish_message.assert_called_once()
        call_args = mock_mqtt_bridge.publish_message.call_args
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

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert "jeedom2ha_42" in payload["device"]["identifiers"]

    @pytest.mark.asyncio
    async def test_device_via_device(self, publisher, snapshot, mock_mqtt_bridge):
        """device.via_device = jeedom2ha_bridge."""
        mapping = _make_mapping()
        await publisher.publish_light(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert payload["device"]["via_device"] == "jeedom2ha_bridge"

    @pytest.mark.asyncio
    async def test_device_manufacturer(self, publisher, snapshot, mock_mqtt_bridge):
        """device.manufacturer = Jeedom (eq_type_name)."""
        mapping = _make_mapping()
        await publisher.publish_light(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
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

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert payload["origin"]["name"] == "jeedom2ha"

    @pytest.mark.asyncio
    async def test_origin_sw_version(self, publisher, snapshot, mock_mqtt_bridge):
        """origin.sw_version présent."""
        mapping = _make_mapping()
        await publisher.publish_light(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
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

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert payload["availability_topic"] == "jeedom2ha/bridge/status"

    @pytest.mark.asyncio
    async def test_light_availability_can_be_composed_with_local_topic(
        self,
        publisher,
        snapshot_with_local_availability,
        mock_mqtt_bridge,
    ):
        mapping = _make_mapping()
        await publisher.publish_light(mapping, snapshot_with_local_availability)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert payload["availability"] == [
            "jeedom2ha/bridge/status",
            "jeedom2ha/42/availability",
        ]
        assert payload["availability_mode"] == "all"
        assert payload["payload_available"] == "online"
        assert payload["payload_not_available"] == "offline"
        assert "availability_topic" not in payload


# ==============================================================================
# Test: Suggested area absent when None
# ==============================================================================

class TestSuggestedArea:
    @pytest.mark.asyncio
    async def test_suggested_area_absent_when_none(self, publisher, snapshot, mock_mqtt_bridge):
        """suggested_area absent du device si l'objet Jeedom est None."""
        mapping = _make_mapping(suggested_area=None)
        await publisher.publish_light(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert "suggested_area" not in payload["device"]

    @pytest.mark.asyncio
    async def test_suggested_area_present_when_set(self, publisher, snapshot, mock_mqtt_bridge):
        """suggested_area présent dans device quand l'objet existe."""
        mapping = _make_mapping(suggested_area="Salon")
        await publisher.publish_light(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert payload["device"]["suggested_area"] == "Salon"


# ==============================================================================
# Test: Cover payload structure (Story 2.3)
# ==============================================================================

class TestCoverBasicPayload:
    @pytest.mark.asyncio
    async def test_cover_payload_has_required_fields(self, publisher, snapshot, mock_mqtt_bridge):
        """Payload cover basique contient tous les champs requis."""
        mapping = _make_cover_mapping()
        await publisher.publish_cover(mapping, snapshot)

        mock_mqtt_bridge.publish_message.assert_called_once()
        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])

        assert payload["command_topic"] == "jeedom2ha/42/set"
        assert payload["payload_open"] == "OPEN"
        assert payload["payload_close"] == "CLOSE"
        assert payload["state_topic"] == "jeedom2ha/42/state"
        assert payload["state_open"] == "open"
        assert payload["state_closed"] == "closed"
        assert payload["device_class"] == "shutter"
        assert "device" in payload
        assert "origin" in payload
        assert payload["availability_topic"] == "jeedom2ha/bridge/status"

    @pytest.mark.asyncio
    async def test_cover_payload_with_composed_availability(
        self,
        publisher,
        snapshot_with_local_availability,
        mock_mqtt_bridge,
    ):
        mapping = _make_cover_mapping()
        await publisher.publish_cover(mapping, snapshot_with_local_availability)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert payload["availability"] == [
            "jeedom2ha/bridge/status",
            "jeedom2ha/42/availability",
        ]
        assert payload["availability_mode"] == "all"
        assert payload["payload_available"] == "online"
        assert payload["payload_not_available"] == "offline"
        assert "availability_topic" not in payload

    @pytest.mark.asyncio
    async def test_cover_no_stop_no_position(self, publisher, snapshot, mock_mqtt_bridge):
        """Cover basique sans stop ni position → pas de champs optionnels."""
        mapping = _make_cover_mapping(has_stop=False, has_position=False)
        await publisher.publish_cover(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert "payload_stop" not in payload
        assert "position_topic" not in payload
        assert "set_position_topic" not in payload


class TestCoverStopPayload:
    @pytest.mark.asyncio
    async def test_cover_with_stop(self, publisher, snapshot, mock_mqtt_bridge):
        """Payload cover avec stop contient payload_stop."""
        mapping = _make_cover_mapping(has_stop=True)
        await publisher.publish_cover(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert payload["payload_stop"] == "STOP"


class TestCoverPositionPayload:
    @pytest.mark.asyncio
    async def test_cover_with_position(self, publisher, snapshot, mock_mqtt_bridge):
        """Payload cover avec position contient les champs position."""
        mapping = _make_cover_mapping(has_position=True)
        await publisher.publish_cover(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert payload["position_topic"] == "jeedom2ha/42/position"
        assert payload["set_position_topic"] == "jeedom2ha/42/position/set"
        assert payload["position_open"] == 100
        assert payload["position_closed"] == 0


class TestCoverBSOPayload:
    @pytest.mark.asyncio
    async def test_bso_device_class_blind(self, publisher, snapshot, mock_mqtt_bridge):
        """Payload BSO a device_class: 'blind' au lieu de 'shutter'."""
        mapping = _make_cover_mapping(is_bso=True)
        await publisher.publish_cover(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert payload["device_class"] == "blind"


class TestCoverTopicFormat:
    @pytest.mark.asyncio
    async def test_cover_topic_format(self, publisher, snapshot, mock_mqtt_bridge):
        """Topic = homeassistant/cover/jeedom2ha_{id}/config."""
        mapping = _make_cover_mapping(eq_id=42)
        await publisher.publish_cover(mapping, snapshot)

        topic = mock_mqtt_bridge.publish_message.call_args[0][0]
        assert topic == "homeassistant/cover/jeedom2ha_42/config"


class TestCoverRetainFlag:
    @pytest.mark.asyncio
    async def test_cover_publish_with_retain(self, publisher, snapshot, mock_mqtt_bridge):
        """Cover publish avec retain=True."""
        mapping = _make_cover_mapping()
        await publisher.publish_cover(mapping, snapshot)

        call_kwargs = mock_mqtt_bridge.publish_message.call_args
        assert call_kwargs[1]["retain"] is True or call_kwargs[0][3] is True


class TestCoverUnpublish:
    @pytest.mark.asyncio
    async def test_unpublish_cover_sends_empty_on_cover_topic(self, publisher, mock_mqtt_bridge):
        """Unpublish cover envoie payload vide avec retain=True sur le topic cover."""
        await publisher.unpublish_by_eq_id(42, entity_type="cover")

        mock_mqtt_bridge.publish_message.assert_called_once()
        call_args = mock_mqtt_bridge.publish_message.call_args
        topic = call_args[0][0]
        payload_val = call_args[0][1]
        assert topic == "homeassistant/cover/jeedom2ha_42/config"
        assert payload_val == ""
        assert call_args[1]["retain"] is True or call_args[0][3] is True


class TestCoverSuggestedArea:
    @pytest.mark.asyncio
    async def test_cover_suggested_area_absent_when_none(self, publisher, snapshot, mock_mqtt_bridge):
        """suggested_area absent du device cover si l'objet Jeedom est None."""
        mapping = _make_cover_mapping(suggested_area=None)
        await publisher.publish_cover(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert "suggested_area" not in payload["device"]


# ==============================================================================
# Helpers for Switch tests (Story 2.4)
# ==============================================================================

def _make_switch_mapping(
    eq_id=42, name="Prise Cuisine", confidence="sure",
    has_on_off=True, has_state=True, device_class=None,
    suggested_area="Cuisine",
):
    """Helper to create a switch MappingResult."""
    capabilities = SwitchCapabilities(
        has_on_off=has_on_off,
        has_state=has_state,
        on_off_confidence="sure" if confidence == "sure" else "probable",
        device_class=device_class,
    )

    return MappingResult(
        ha_entity_type="switch",
        confidence=confidence,
        reason_code="switch_on_off_state",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=name,
        suggested_area=suggested_area,
        commands={},
        capabilities=capabilities,
    )


# ==============================================================================
# Test: Switch — basic payload structure (Story 2.4)
# ==============================================================================

class TestSwitchBasicPayload:
    @pytest.mark.asyncio
    async def test_switch_payload_has_required_fields(self, publisher, snapshot, mock_mqtt_bridge):
        """Payload switch basique contient tous les champs requis."""
        mapping = _make_switch_mapping()
        await publisher.publish_switch(mapping, snapshot)

        mock_mqtt_bridge.publish_message.assert_called_once()
        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])

        assert payload["command_topic"] == "jeedom2ha/42/set"
        assert payload["payload_on"] == "ON"
        assert payload["payload_off"] == "OFF"
        assert payload["state_topic"] == "jeedom2ha/42/state"
        assert payload["state_on"] == "ON"
        assert payload["state_off"] == "OFF"
        assert payload["availability_topic"] == "jeedom2ha/bridge/status"
        assert "device" in payload
        assert "origin" in payload
        assert "name" in payload
        assert "unique_id" in payload

    @pytest.mark.asyncio
    async def test_switch_payload_with_composed_availability(
        self,
        publisher,
        snapshot_with_local_availability,
        mock_mqtt_bridge,
    ):
        mapping = _make_switch_mapping()
        await publisher.publish_switch(mapping, snapshot_with_local_availability)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert payload["availability"] == [
            "jeedom2ha/bridge/status",
            "jeedom2ha/42/availability",
        ]
        assert payload["availability_mode"] == "all"
        assert payload["payload_available"] == "online"
        assert payload["payload_not_available"] == "offline"
        assert "availability_topic" not in payload

    @pytest.mark.asyncio
    async def test_switch_payload_no_device_class_when_none(self, publisher, snapshot, mock_mqtt_bridge):
        """Payload switch avec device_class=None → champ 'device_class' ABSENT du payload."""
        mapping = _make_switch_mapping(device_class=None)
        await publisher.publish_switch(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert "device_class" not in payload

    @pytest.mark.asyncio
    async def test_switch_payload_device_class_outlet(self, publisher, snapshot, mock_mqtt_bridge):
        """Payload switch avec device_class='outlet' → champ 'device_class' présent et = 'outlet'."""
        mapping = _make_switch_mapping(device_class="outlet")
        await publisher.publish_switch(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert payload["device_class"] == "outlet"

    @pytest.mark.asyncio
    async def test_switch_payload_no_icon_field(self, publisher, snapshot, mock_mqtt_bridge):
        """Payload switch ne contient jamais de champ 'icon'."""
        for dc in [None, "outlet"]:
            mock_mqtt_bridge.publish_message.reset_mock()
            mapping = _make_switch_mapping(device_class=dc)
            await publisher.publish_switch(mapping, snapshot)
            payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
            assert "icon" not in payload


class TestSwitchTopicFormat:
    @pytest.mark.asyncio
    async def test_switch_topic_format(self, publisher, snapshot, mock_mqtt_bridge):
        """Topic = homeassistant/switch/jeedom2ha_{id}/config."""
        mapping = _make_switch_mapping(eq_id=42)
        await publisher.publish_switch(mapping, snapshot)

        topic = mock_mqtt_bridge.publish_message.call_args[0][0]
        assert topic == "homeassistant/switch/jeedom2ha_42/config"


class TestSwitchRetainFlag:
    @pytest.mark.asyncio
    async def test_switch_publish_with_retain(self, publisher, snapshot, mock_mqtt_bridge):
        """Switch publish avec retain=True."""
        mapping = _make_switch_mapping()
        await publisher.publish_switch(mapping, snapshot)

        call_kwargs = mock_mqtt_bridge.publish_message.call_args
        assert call_kwargs[1]["retain"] is True or call_kwargs[0][3] is True


class TestSwitchUnpublish:
    @pytest.mark.asyncio
    async def test_unpublish_switch_sends_empty_on_switch_topic(self, publisher, mock_mqtt_bridge):
        """Unpublish switch envoie payload vide avec retain=True sur le topic switch."""
        await publisher.unpublish_by_eq_id(42, entity_type="switch")

        mock_mqtt_bridge.publish_message.assert_called_once()
        call_args = mock_mqtt_bridge.publish_message.call_args
        topic = call_args[0][0]
        payload_val = call_args[0][1]
        assert topic == "homeassistant/switch/jeedom2ha_42/config"
        assert payload_val == ""
        assert call_args[1]["retain"] is True or call_args[0][3] is True


class TestSwitchSuggestedArea:
    @pytest.mark.asyncio
    async def test_switch_suggested_area_absent_when_none(self, publisher, snapshot, mock_mqtt_bridge):
        """suggested_area absent du device switch si None."""
        mapping = _make_switch_mapping(suggested_area=None)
        await publisher.publish_switch(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert "suggested_area" not in payload["device"]

    @pytest.mark.asyncio
    async def test_switch_suggested_area_present_when_set(self, publisher, snapshot, mock_mqtt_bridge):
        """suggested_area présent dans device switch quand défini."""
        mapping = _make_switch_mapping(suggested_area="Cuisine")
        await publisher.publish_switch(mapping, snapshot)

        payload = json.loads(mock_mqtt_bridge.publish_message.call_args[0][1])
        assert payload["device"]["suggested_area"] == "Cuisine"
