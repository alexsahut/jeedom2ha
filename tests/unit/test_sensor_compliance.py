"""test_sensor_compliance.py — Strict compliance tests for Story 2.5.

Focuses on:
- MQTT Contract (unique_id, object_id, topics, payloads).
- Discovery vs State publication order.
- Negative paths: blocking BOTH discovery and state on invalid data.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from aiohttp import web
import json

from resources.daemon.transport.http_server import create_app
from resources.daemon.models.topology import TopologySnapshot
from resources.daemon.mapping.sensor import SensorMapper

LOCAL_SECRET = "test_secret"

@pytest.fixture
def http_app():
    # Mocking necessary bits for create_app logic
    with patch("resources.daemon.transport.http_server.MqttBridge", autospec=True) as mock_bridge_class:
        app = create_app(local_secret=LOCAL_SECRET)
        # Inject the mock returned by the class constructor
        mock_instance = mock_bridge_class.return_value
        mock_instance.is_connected = True
        app["mqtt_bridge"] = mock_instance
        yield app


@pytest.fixture
def mock_mqtt(http_app):
    return http_app["mqtt_bridge"]

@pytest.fixture
async def http_client(http_app, aiohttp_client):
    return await aiohttp_client(http_app)


class TestSensorCompliance:
    
    async def test_mqtt_contract_payload_and_topics(self, http_client, mock_mqtt):
        """Prouve le contrat MQTT exact pour un sensor numérique."""
        payload = {
            "version": "1.0",
            "eq_logics": [{
                "id": "42",
                "name": "Capteur",
                "object_id": "1",
                "is_enable": "1",
                "eq_type": "virtual",
                "cmds": [{
                    "id": "1001",
                    "name": "Temp",
                    "type": "info",
                    "sub_type": "numeric",
                    "generic_type": "TEMPERATURE",
                    "unit": "°C",
                    "current_value": 22.5
                }]
            }],
            "objects": [{"id": "1", "name": "Maison"}]
        }
        
        await http_client.post("/action/sync", headers={"X-Local-Secret": LOCAL_SECRET}, json={"payload": payload})
        
        # Check topics and unique_id/object_id
        publish_calls = mock_mqtt.publish_message.call_args_list
        config_call = [c for c in publish_calls if c.args[0].endswith("/config")][0]
        topic = config_call.args[0]
        payload_dict = json.loads(config_call.args[1])
        
        assert topic == "homeassistant/sensor/jeedom2ha_cmd_1001/config"
        assert payload_dict["unique_id"] == "jeedom2ha_cmd_1001"
        assert payload_dict["object_id"] == "jeedom2ha_cmd_1001"
        assert payload_dict["state_topic"] == "jeedom2ha/cmd/1001/state"
        assert payload_dict["device"]["identifiers"] == ["jeedom2ha_42"]
        assert payload_dict["unit_of_measurement"] == "°C"
        assert payload_dict["device_class"] == "temperature"

    async def test_binary_sensor_contract_and_payloads(self, http_client, mock_mqtt):
        """Prouve payload_on/off pour binary_sensor."""
        payload = {
            "version": "1.0",
            "eq_logics": [{
                "id": "43",
                "name": "Porte",
                "object_id": "1",
                "is_enable": "1",
                "eq_type": "virtual",
                "cmds": [{
                    "id": "2001",
                    "name": "Etat",
                    "type": "info",
                    "sub_type": "binary",
                    "generic_type": "OPENING",
                    "current_value": 1
                }]
            }],
            "objects": [{"id": "1", "name": "Maison"}]
        }
        
        await http_client.post("/action/sync", headers={"X-Local-Secret": LOCAL_SECRET}, json={"payload": payload})
        
        config_call = [c for c in mock_mqtt.publish_message.call_args_list if "binary_sensor" in c.args[0]][0]
        payload_dict = json.loads(config_call.args[1])
        
        assert payload_dict["payload_on"] == "ON"
        assert payload_dict["payload_off"] == "OFF"
        assert payload_dict["device_class"] == "opening"

    async def test_publication_order_config_then_state(self, http_client, mock_mqtt):
        """Prouve que la discovery (config) est envoyée AVANT l'état initial."""
        payload = {
            "version": "1.0",
            "eq_logics": [{
                "id": "44",
                "name": "TestOrder",
                "object_id": "1",
                "is_enable": "1",
                "eq_type": "virtual",
                "cmds": [{
                    "id": "3001",
                    "name": "Val",
                    "type": "info",
                    "sub_type": "numeric",
                    "generic_type": "TEMPERATURE",
                    "unit": "°C",
                    "current_value": 18.0
                }]
            }],
            "objects": [{"id": "1", "name": "Maison"}]
        }
        
        await http_client.post("/action/sync", headers={"X-Local-Secret": LOCAL_SECRET}, json={"payload": payload})
        
        # Verify sequence of calls
        calls = mock_mqtt.publish_message.call_args_list
        # Filter only related to cmd 3001
        relevant_calls = [c for c in calls if "3001" in c.args[0]]
        assert len(relevant_calls) == 2
        
        # First call must be config
        assert relevant_calls[0].args[0].endswith("/config")
        # Second call must be state
        assert relevant_calls[1].args[0].endswith("/state")
        assert relevant_calls[1].args[1] == "18.0"

    async def test_negative_path_invalid_unit_blocks_all(self, http_client, mock_mqtt):
        """Prouve que l'unité invalide bloque Config ET State."""
        payload = {
            "version": "1.0",
            "eq_logics": [{
                "id": "45",
                "name": "InvalidUnit",
                "object_id": "1",
                "is_enable": "1",
                "eq_type": "virtual",
                "cmds": [{
                    "id": "4001",
                    "name": "Temp",
                    "type": "info",
                    "sub_type": "numeric",
                    "generic_type": "TEMPERATURE",
                    "unit": "INVALID_UNIT", # Incoherent
                    "current_value": 20.0
                }]
            }],
            "objects": [{"id": "1", "name": "Maison"}]
        }
        
        resp = await http_client.post("/action/sync", headers={"X-Local-Secret": LOCAL_SECRET}, json={"payload": payload})
        assert resp.status == 200
        data = await resp.json()
        
        # Verify diagnostic
        assert data["payload"]["mapping_summary"]["sensors_skipped"] >= 1
        
        # Verify NO MQTT calls for this cmd
        relevant_calls = [c for c in mock_mqtt.publish_message.call_args_list if "4001" in c.args[0]]
        assert len(relevant_calls) == 0

    async def test_negative_path_non_numeric_blocks_all(self, http_client, mock_mqtt):
        """Prouve que la valeur non numérique bloque Config ET State."""
        payload = {
            "version": "1.0",
            "eq_logics": [{
                "id": "46",
                "name": "NonNumeric",
                "object_id": "1",
                "is_enable": "1",
                "eq_type": "virtual",
                "cmds": [{
                    "id": "5001",
                    "name": "Temp",
                    "type": "info",
                    "sub_type": "numeric",
                    "generic_type": "TEMPERATURE",
                    "unit": "°C",
                    "current_value": "NOT_A_NUMBER"
                }]
            }],
            "objects": [{"id": "1", "name": "Maison"}]
        }
        
        resp = await http_client.post("/action/sync", headers={"X-Local-Secret": LOCAL_SECRET}, json={"payload": payload})
        data = await resp.json()
        
        assert data["payload"]["mapping_summary"]["sensors_skipped"] >= 1
        relevant_calls = [c for c in mock_mqtt.publish_message.call_args_list if "5001" in c.args[0]]
        assert len(relevant_calls) == 0

        decision = http_client.app["publications"]["jeedom2ha_cmd_5001"]
        mapping = http_client.app["mappings"]["jeedom2ha_cmd_5001"]
        assert decision.should_publish is False
        assert decision.reason == "invalid_initial_state"
        assert mapping.reason_code == "invalid_initial_state"
        assert mapping.reason_details["invalid_initial_state"]["cmd_id"] == 5001

    async def test_negative_path_binary_conversion_blocks_all(self, http_client, mock_mqtt):
        """Prouve que l'échec de conversion binaire bloque Config ET State."""
        payload = {
            "version": "1.0",
            "eq_logics": [{
                "id": "47",
                "name": "BinaryFail",
                "object_id": "1",
                "is_enable": "1",
                "eq_type": "virtual",
                "cmds": [{
                    "id": "6001",
                    "name": "Etat",
                    "type": "info",
                    "sub_type": "binary",
                    "generic_type": "OPENING",
                    "current_value": "GARBAGE"
                }]
            }],
            "objects": [{"id": "1", "name": "Maison"}]
        }
        
        resp = await http_client.post("/action/sync", headers={"X-Local-Secret": LOCAL_SECRET}, json={"payload": payload})
        data = await resp.json()
        
        assert data["payload"]["mapping_summary"]["binary_sensors_skipped"] >= 1

        relevant_calls = [c for c in mock_mqtt.publish_message.call_args_list if "6001" in c.args[0]]
        assert len(relevant_calls) == 0

        decision = http_client.app["publications"]["jeedom2ha_cmd_6001"]
        mapping = http_client.app["mappings"]["jeedom2ha_cmd_6001"]
        assert decision.should_publish is False
        assert decision.reason == "invalid_initial_state"
        assert mapping.reason_code == "invalid_initial_state"
        assert mapping.reason_details["invalid_initial_state"]["cmd_id"] == 6001
