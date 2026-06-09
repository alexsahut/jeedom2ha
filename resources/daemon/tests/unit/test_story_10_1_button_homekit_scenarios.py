"""Story 10.1 — Button path for the 5 HomeKit scenarios (Jeedom scenario -> HA button).

Scénarios cibles confirmés par terrain ClawBox (2026-06-09):
  id=20  Tout éteindre
  id=38  ambiance cinema
  id=50  ambiance coucher
  id=57  Ambiance lumineuse
  id=150 Lumières terrasse
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from discovery.publisher import DiscoveryPublisher
from mapping.button import ScenarioButtonMapper
from models.topology import JeedomScenario, TopologySnapshot


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_FIVE_SCENARIOS = [
    {"id": 20,  "name": "Tout éteindre",    "is_active": True},
    {"id": 38,  "name": "ambiance cinema",  "is_active": True},
    {"id": 50,  "name": "ambiance coucher", "is_active": True},
    {"id": 57,  "name": "Ambiance lumineuse", "is_active": True},
    {"id": 150, "name": "Lumières terrasse", "is_active": True},
]


def _snapshot_with_scenarios(scenarios: list[dict]) -> TopologySnapshot:
    payload = {
        "timestamp": "2026-06-09T00:00:00Z",
        "objects": [],
        "eq_logics": [],
        "scenarios": scenarios,
    }
    return TopologySnapshot.from_jeedom_payload(payload)


# ---------------------------------------------------------------------------
# Task 1 — Topology parses scenarios
# ---------------------------------------------------------------------------

class TestTopologyScenarioParsing:

    def test_five_target_scenarios_parsed(self):
        snapshot = _snapshot_with_scenarios(_FIVE_SCENARIOS)
        assert len(snapshot.scenarios) == 5

    def test_scenario_fields_correct(self):
        snapshot = _snapshot_with_scenarios(_FIVE_SCENARIOS)
        sc = snapshot.scenarios[20]
        assert sc.id == 20
        assert sc.name == "Tout éteindre"
        assert sc.is_active is True

    def test_inactive_scenario_parsed_but_flagged(self):
        data = [{"id": 99, "name": "Inactif", "is_active": False}]
        snapshot = _snapshot_with_scenarios(data)
        assert snapshot.scenarios[99].is_active is False

    def test_empty_scenarios_key_missing(self):
        payload = {"timestamp": "2026-06-09T00:00:00Z", "objects": [], "eq_logics": []}
        snapshot = TopologySnapshot.from_jeedom_payload(payload)
        assert snapshot.scenarios == {}

    def test_malformed_scenario_skipped(self):
        data = [{"id": "bad", "name": "Broken"}, {"id": 20, "name": "OK", "is_active": True}]
        snapshot = _snapshot_with_scenarios(data)
        assert 20 in snapshot.scenarios
        assert len(snapshot.scenarios) == 1


# ---------------------------------------------------------------------------
# Task 2 — ScenarioButtonMapper produces correct MappingResult
# ---------------------------------------------------------------------------

class TestScenarioButtonMapper:

    def _map_scenario(self, sc_id: int, sc_name: str) -> object:
        mapper = ScenarioButtonMapper()
        scenario = JeedomScenario(id=sc_id, name=sc_name, is_active=True)
        return mapper.map(scenario)

    def test_ha_entity_type_is_button(self):
        result = self._map_scenario(20, "Tout éteindre")
        assert result.ha_entity_type == "button"

    def test_unique_id_uses_scenario_prefix(self):
        result = self._map_scenario(20, "Tout éteindre")
        assert result.ha_unique_id == "jeedom2ha_scenario_20"

    def test_ha_name_preserved(self):
        result = self._map_scenario(150, "Lumières terrasse")
        assert result.ha_name == "Lumières terrasse"

    def test_command_topic_uses_scenario_namespace(self):
        result = self._map_scenario(38, "ambiance cinema")
        assert result.reason_details["command_topic"] == "jeedom2ha/scenario_38/cmd"

    def test_node_id_in_reason_details(self):
        result = self._map_scenario(57, "Ambiance lumineuse")
        assert result.reason_details["node_id"] == "jeedom2ha_scenario_57"

    def test_source_kind_is_scenario(self):
        result = self._map_scenario(50, "ambiance coucher")
        assert result.reason_details["source_kind"] == "scenario"

    def test_confidence_is_sure(self):
        result = self._map_scenario(20, "Tout éteindre")
        assert result.confidence == "sure"

    def test_no_new_ha_type(self):
        """AC4 — scénarios restent button, pas de nouveau type."""
        mapper = ScenarioButtonMapper()
        for sc_dict in _FIVE_SCENARIOS:
            sc = JeedomScenario(**sc_dict)
            result = mapper.map(sc)
            assert result.ha_entity_type == "button"

    def test_jeedom_eq_id_matches_scenario_id(self):
        result = self._map_scenario(150, "Lumières terrasse")
        assert result.jeedom_eq_id == 150


# ---------------------------------------------------------------------------
# Task 2 — Publisher uses node_id for button topics
# ---------------------------------------------------------------------------

class TestPublisherButtonNodeId:

    def _make_publisher(self):
        bridge = MagicMock()
        bridge.publish_message = MagicMock(return_value=True)
        return DiscoveryPublisher(mqtt_bridge=bridge), bridge

    def _scenario_mapping(self, sc_id: int, sc_name: str):
        mapper = ScenarioButtonMapper()
        return mapper.map(JeedomScenario(id=sc_id, name=sc_name, is_active=True))

    def _empty_snapshot(self) -> TopologySnapshot:
        return TopologySnapshot.from_jeedom_payload(
            {"timestamp": "2026-06-09T00:00:00Z", "objects": [], "eq_logics": [], "scenarios": []}
        )

    def test_mqtt_topic_uses_scenario_node_id(self):
        publisher, bridge = self._make_publisher()
        mapping = self._scenario_mapping(20, "Tout éteindre")
        snapshot = self._empty_snapshot()

        asyncio.get_event_loop().run_until_complete(publisher.publish_button(mapping, snapshot))

        call_args = bridge.publish_message.call_args
        topic = call_args[0][0]
        assert topic == "homeassistant/button/jeedom2ha_scenario_20/config"

    def test_payload_object_id_uses_node_id(self):
        publisher, bridge = self._make_publisher()
        mapping = self._scenario_mapping(38, "ambiance cinema")
        snapshot = self._empty_snapshot()

        asyncio.get_event_loop().run_until_complete(publisher.publish_button(mapping, snapshot))

        call_args = bridge.publish_message.call_args
        payload = json.loads(call_args[0][1])
        assert payload["object_id"] == "jeedom2ha_scenario_38"

    def test_payload_command_topic_correct(self):
        publisher, bridge = self._make_publisher()
        mapping = self._scenario_mapping(50, "ambiance coucher")
        snapshot = self._empty_snapshot()

        asyncio.get_event_loop().run_until_complete(publisher.publish_button(mapping, snapshot))

        call_args = bridge.publish_message.call_args
        payload = json.loads(call_args[0][1])
        assert payload["command_topic"] == "jeedom2ha/scenario_50/cmd"

    def test_payload_unique_id_correct(self):
        publisher, bridge = self._make_publisher()
        mapping = self._scenario_mapping(57, "Ambiance lumineuse")
        snapshot = self._empty_snapshot()

        asyncio.get_event_loop().run_until_complete(publisher.publish_button(mapping, snapshot))

        call_args = bridge.publish_message.call_args
        payload = json.loads(call_args[0][1])
        assert payload["unique_id"] == "jeedom2ha_scenario_57"

    def test_eqlogic_button_still_uses_eq_node_id(self):
        """Non-regression: eqLogic buttons still use old node_id format."""
        from mapping.button import ButtonMapper
        from models.topology import JeedomCmd, JeedomEqLogic

        publisher, bridge = self._make_publisher()
        eq = JeedomEqLogic(
            id=999, name="Test Action", eq_type_name="virtual",
            cmds=[JeedomCmd(id=1, name="run", generic_type="SCENARIO_LAUNCH", type="action", sub_type="other")]
        )
        snapshot = TopologySnapshot.from_jeedom_payload(
            {"timestamp": "2026-06-09T00:00:00Z", "objects": [], "eq_logics": [], "scenarios": []}
        )
        mapping = ButtonMapper().map(eq, snapshot)
        assert mapping is not None

        asyncio.get_event_loop().run_until_complete(publisher.publish_button(mapping, snapshot))

        call_args = bridge.publish_message.call_args
        topic = call_args[0][0]
        assert topic == "homeassistant/button/jeedom2ha_999/config"

    def test_device_identifier_no_collision_with_eqlogic(self):
        """H1 fix — scenario device identifier must not collide with same-integer eqLogic."""
        publisher, bridge = self._make_publisher()
        mapping = self._scenario_mapping(20, "Tout éteindre")
        snapshot = self._empty_snapshot()

        asyncio.get_event_loop().run_until_complete(publisher.publish_button(mapping, snapshot))

        call_args = bridge.publish_message.call_args
        payload = json.loads(call_args[0][1])
        device_identifiers = payload["device"]["identifiers"]
        assert device_identifiers == ["jeedom2ha_scenario_20"]
        assert "jeedom2ha_20" not in device_identifiers


# ---------------------------------------------------------------------------
# Task 2 — CommandSynchronizer handles scenario command topics
# ---------------------------------------------------------------------------

try:
    from sync.command import CommandSynchronizer, _SCENARIO_CMD_TOPIC_RE
    _HAS_SYNC = True
except ModuleNotFoundError:
    _HAS_SYNC = False

_skip_no_sync = pytest.mark.skipif(not _HAS_SYNC, reason="aiohttp not installed")


class TestScenarioCommandHandling:

    def _make_synchronizer(self, scenario_publications=None):
        bridge = MagicMock()
        bridge.is_connected = True
        app = {
            "publications": {},
            "scenario_publications": scenario_publications or {},
        }
        return CommandSynchronizer(
            app=app,
            mqtt_bridge=bridge,
            jeedom_api_endpoint="http://localhost/core/api/jeeApi.php",
            jeedom_core_apikey="testkey",
        )

    @_skip_no_sync
    def test_scenario_topic_regex_matches(self):
        """Scenario command topic must be recognized by the scenario regex."""
        match = _SCENARIO_CMD_TOPIC_RE.match("jeedom2ha/scenario_20/cmd")
        assert match is not None
        assert int(match.group("scenario_id")) == 20

    def test_scenario_topic_does_not_match_eq_pattern(self):
        """Scenario topic must NOT match the eqLogic /set pattern."""
        import re
        SET_RE = re.compile(r"^jeedom2ha/(?P<eq_id>\d+)/set$")
        assert SET_RE.match("jeedom2ha/scenario_20/cmd") is None

    @_skip_no_sync
    def test_scenario_command_rejected_when_no_publication(self):
        sync = self._make_synchronizer(scenario_publications={})
        result = asyncio.get_event_loop().run_until_complete(
            sync.handle_command_message("jeedom2ha/scenario_20/cmd", "PRESS")
        )
        assert result is False

    @_skip_no_sync
    def test_scenario_command_calls_changestate(self):
        sc_mapping = ScenarioButtonMapper().map(JeedomScenario(id=20, name="Tout éteindre"))
        from models.mapping import PublicationDecision
        sc_decision = PublicationDecision(
            should_publish=True,
            reason="scenario_button",
            mapping_result=sc_mapping,
            active_or_alive=True,
        )
        sync = self._make_synchronizer(scenario_publications={20: sc_decision})

        with patch.object(sync, "_execute_scenario_start", new_callable=AsyncMock, return_value=True) as mock_start:
            result = asyncio.get_event_loop().run_until_complete(
                sync.handle_command_message("jeedom2ha/scenario_20/cmd", "PRESS")
            )

        assert result is True
        mock_start.assert_called_once_with(20)

    @_skip_no_sync
    def test_execute_scenario_start_builds_correct_payload(self):
        sync = self._make_synchronizer()
        captured = {}

        async def mock_post(url, json=None, **kwargs):
            captured["url"] = url
            captured["payload"] = json
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)
            mock_resp.json = AsyncMock(return_value={"result": "ok"})
            return mock_resp

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.post = mock_post
        sync._session = mock_session

        result = asyncio.get_event_loop().run_until_complete(sync._execute_scenario_start(20))

        assert result is True
        assert captured["payload"]["method"] == "scenario::changeState"
        assert captured["payload"]["params"]["id"] == 20
        assert captured["payload"]["params"]["state"] == "start"
        assert captured["payload"]["params"]["apikey"] == "testkey"
