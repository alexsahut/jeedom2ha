"""Integration-style test for namespace coexistence in state synchronization."""
from unittest.mock import MagicMock

from resources.daemon.models.mapping import MappingResult, PublicationDecision, SensorCapabilities
from resources.daemon.models.topology import JeedomCmd
from resources.daemon.sync.state import StateSynchronizer


def _sensor_mapping(cmd_id: int, unique_id: str, eq_id: int) -> MappingResult:
    return MappingResult(
        ha_entity_type="sensor",
        confidence="sure",
        reason_code="sensor_temperature",
        jeedom_eq_id=eq_id,
        ha_unique_id=unique_id,
        ha_name=f"Sensor {cmd_id}",
        commands={"TEMPERATURE": JeedomCmd(id=cmd_id, name="Temp", generic_type="TEMPERATURE", type="info", sub_type="numeric")},
        capabilities=SensorCapabilities(is_binary=False),
    )


def test_coexistence_sync_never_touches_non_jeedom2ha_topics():
    internal = _sensor_mapping(10, "uid-internal", 1)
    external = _sensor_mapping(11, "uid-external", 2)

    app = {
        "mappings": {
            "uid-internal": internal,
            "uid-external": external,
        },
        "publications": {
            "uid-internal": PublicationDecision(True, "sure", internal, state_topic="jeedom2ha/cmd/10/state", active_or_alive=True),
            "uid-external": PublicationDecision(True, "sure", external, state_topic="otherpublisher/cmd/11/state", active_or_alive=True),
        },
    }

    bridge = MagicMock()
    bridge.publish_message.return_value = True
    bridge.is_connected = True

    sync = StateSynchronizer(
        app=app,
        mqtt_bridge=bridge,
        jeedom_api_endpoint="http://127.0.0.1/core/api/jeeApi.php",
        jeedom_core_apikey="test-core-api-key",
        poll_interval=1.0,
    )

    runtime_index = sync._build_runtime_index()
    sync._apply_changes(
        [
            {"cmd_id": 10, "value": "22.4"},
            {"cmd_id": 11, "value": "30.0"},
        ],
        runtime_index,
    )

    bridge.publish_message.assert_called_once_with("jeedom2ha/cmd/10/state", "22.4", qos=1, retain=False)
