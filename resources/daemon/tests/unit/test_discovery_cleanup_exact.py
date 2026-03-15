"""Non-regression tests for exact discovery cleanup retained payload behavior."""
from unittest.mock import MagicMock

import pytest

from resources.daemon.discovery.publisher import DiscoveryPublisher


@pytest.mark.asyncio
async def test_unpublish_entity_uses_exact_topic_with_empty_retained_payload():
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(bridge)

    await publisher.unpublish_entity("jeedom2ha_cmd_123", entity_type="sensor")

    bridge.publish_message.assert_called_once_with(
        "homeassistant/sensor/jeedom2ha_cmd_123/config",
        "",
        qos=1,
        retain=True,
    )


@pytest.mark.asyncio
async def test_unpublish_by_eq_id_uses_exact_topic_without_wildcard():
    bridge = MagicMock()
    bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(bridge)

    await publisher.unpublish_by_eq_id(42, entity_type="light")

    topic = bridge.publish_message.call_args[0][0]
    assert topic == "homeassistant/light/jeedom2ha_42/config"
    assert "#" not in topic
    assert "+" not in topic
