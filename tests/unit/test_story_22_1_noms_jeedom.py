"""Story 22.1 — noms Home Assistant = noms Jeedom (CC-36).

Couvre AC1 (device.name unique par équipement), AC2 (règle du nom d'entité),
AC3 (renommage → republication), AC5 (default_entity_id = <domaine>.<object_id>).
Identifiants et noms génériques uniquement (CC-48).
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from discovery.publisher import DiscoveryPublisher
from discovery.registry import PublisherRegistry
from mapping.registry import MapperRegistry
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot


def _snapshot(*eqs: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-10-12T00:00:00+00:00",
        objects={10: JeedomObject(id=10, name="Zone-A")},
        eq_logics={eq.id: eq for eq in eqs},
    )


def _info(cmd_id, name, **kw):
    return JeedomCmd(id=cmd_id, name=name, type="info", sub_type="numeric", **kw)


def _multi_entity_eq(eq_id=579, name="Equip-579"):
    """Forme 579 : prise (switch) + plusieurs mesures nommées d'après des commandes."""
    return JeedomEqLogic(
        id=eq_id, name=name, object_id=10, eq_type_name="zwave",
        cmds=[
            JeedomCmd(id=eq_id * 10 + 1, name="Etat", generic_type="ENERGY_STATE",
                      type="info", sub_type="binary"),
            JeedomCmd(id=eq_id * 10 + 2, name="On", generic_type="ENERGY_ON",
                      type="action", sub_type="other"),
            JeedomCmd(id=eq_id * 10 + 3, name="Off", generic_type="ENERGY_OFF",
                      type="action", sub_type="other"),
            _info(eq_id * 10 + 4, "Puissance-X", unit="W"),
            _info(eq_id * 10 + 5, "Energie-Y", unit="kWh"),
        ],
    )


def _single_cmd_sensor_eq(eq_id=67, name="Equip-67"):
    """Équipement à une seule entité nommée d'après une commande (F3, 16 des 29)."""
    return JeedomEqLogic(
        id=eq_id, name=name, object_id=10, eq_type_name="virtual",
        cmds=[_info(eq_id * 10 + 1, "Cmd-Z", generic_type="TEMPERATURE", unit="°C")],
    )


def _all_mappings(eq, snapshot):
    primary = MapperRegistry().map(eq, snapshot)
    assert primary is not None
    return [primary, *primary.additional_mappings]


def _payload_of(publisher, mapping, snapshot):
    builder = getattr(publisher, f"_build_{mapping.ha_entity_type}_payload")
    return builder(mapping, snapshot)


@pytest.fixture
def publisher():
    return DiscoveryPublisher(MagicMock())


class TestDeviceNameAndEntityNameRule:
    def test_device_name_identical_for_all_entities_of_multi_entity_equipment(self, publisher):
        eq = _multi_entity_eq()
        snap = _snapshot(eq)
        mappings = _all_mappings(eq, snap)
        assert len(mappings) >= 3
        payloads = [_payload_of(publisher, m, snap) for m in mappings]
        assert {p["device"]["name"] for p in payloads} == {"Equip-579"}
        assert {tuple(p["device"]["identifiers"]) for p in payloads} == {("jeedom2ha_579",)}

    def test_multi_entity_sensors_keep_command_names(self, publisher):
        eq = _multi_entity_eq()
        snap = _snapshot(eq)
        names = {
            m.ha_unique_id: _payload_of(publisher, m, snap)["name"]
            for m in _all_mappings(eq, snap)
            if m.ha_entity_type == "sensor"
        }
        assert sorted(names.values()) == ["Energie-Y", "Puissance-X"]

    def test_single_entity_takes_equipment_name_not_command_name(self, publisher):
        eq = _single_cmd_sensor_eq()
        snap = _snapshot(eq)
        mappings = _all_mappings(eq, snap)
        assert len(mappings) == 1
        payload = _payload_of(publisher, mappings[0], snap)
        assert payload["name"] == "Equip-67"
        assert payload["device"]["name"] == "Equip-67"

    def test_accents_are_kept(self, publisher):
        eq = _single_cmd_sensor_eq(name="Équipement été")
        snap = _snapshot(eq)
        payload = _payload_of(publisher, _all_mappings(eq, snap)[0], snap)
        assert payload["device"]["name"] == "Équipement été"
        assert payload["name"] == "Équipement été"

    def test_scenario_button_keeps_scenario_name_for_device(self, publisher):
        from mapping.button import ScenarioButtonMapper
        from models.topology import JeedomScenario

        sc = JeedomScenario(id=110, name="S110", is_active=True) if hasattr(
            JeedomScenario, "is_active") else JeedomScenario(id=110, name="S110")
        snap = TopologySnapshot(
            timestamp="t", objects={}, eq_logics={}, scenarios={110: sc})
        mapping = ScenarioButtonMapper().map(sc)
        payload = publisher._build_button_payload(mapping, snap)
        assert payload["device"]["name"] == "S110"
        assert payload["name"] == "S110"


class TestDefaultEntityId:
    def test_every_payload_default_entity_id_is_domain_dot_object_id(self, publisher):
        cases = []
        for eq in (_multi_entity_eq(), _single_cmd_sensor_eq()):
            snap = _snapshot(eq)
            cases += [(m, snap) for m in _all_mappings(eq, snap)]
        assert cases
        for mapping, snap in cases:
            payload = _payload_of(publisher, mapping, snap)
            assert payload["default_entity_id"] == (
                f"{mapping.ha_entity_type}.{payload['object_id']}"
            )

    def test_secondary_entities_have_own_object_id(self, publisher):
        eq = _multi_entity_eq()
        snap = _snapshot(eq)
        ids = {
            _payload_of(publisher, m, snap)["default_entity_id"]
            for m in _all_mappings(eq, snap)
        }
        assert "sensor.jeedom2ha_579_5794" in ids
        assert "sensor.jeedom2ha_579_5795" in ids
        assert len(ids) == len(_all_mappings(eq, snap))

    def test_unique_id_object_id_and_topic_unchanged(self, publisher):
        eq = _single_cmd_sensor_eq()
        snap = _snapshot(eq)
        mapping = _all_mappings(eq, snap)[0]
        payload = _payload_of(publisher, mapping, snap)
        assert payload["unique_id"] == mapping.ha_unique_id
        assert payload["object_id"] == "jeedom2ha_67"
        assert payload["state_topic"] == "jeedom2ha/67/state"

    @pytest.mark.parametrize("domain", [
        "light", "cover", "switch", "sensor", "binary_sensor",
        "button", "climate", "alarm_control_panel",
    ])
    def test_each_publisher_domain(self, publisher, domain):
        from models.mapping import (
            AlarmCapabilities, ClimateCapabilities, CoverCapabilities,
            LightCapabilities, MappingResult, SensorCapabilities, SwitchCapabilities,
        )
        caps = {
            "light": LightCapabilities(has_on_off=True),
            "cover": CoverCapabilities(has_open_close=True),
            "switch": SwitchCapabilities(has_on_off=True),
            "sensor": SensorCapabilities(has_state=True),
            "binary_sensor": SensorCapabilities(has_state=True),
            "button": SensorCapabilities(has_state=False),
            "climate": ClimateCapabilities(),
            "alarm_control_panel": AlarmCapabilities(),
        }[domain]
        eq = JeedomEqLogic(id=7, name="Equip-7", object_id=10)
        snap = _snapshot(eq)
        mapping = MappingResult(
            ha_entity_type=domain, confidence="sure", reason_code="t",
            jeedom_eq_id=7, ha_unique_id="jeedom2ha_eq_7", ha_name="X",
            capabilities=caps,
        )
        payload = _payload_of(publisher, mapping, snap)
        assert payload["default_entity_id"] == f"{domain}.jeedom2ha_7"
        assert payload["device"]["name"] == "Equip-7"


class TestRenameRepublish:
    @pytest.mark.asyncio
    async def test_rename_in_jeedom_is_republished_with_new_device_name(self):
        bridge = MagicMock()
        bridge.publish_message = MagicMock(return_value=True)
        bridge.is_connected = True
        registry = PublisherRegistry(DiscoveryPublisher(bridge))

        eq = _multi_entity_eq(name="Nom-avant")
        snap = _snapshot(eq)
        for m in _all_mappings(eq, snap):
            assert await registry.publish(m, snap)
        before = {json.loads(c[0][1])["device"]["name"] for c in bridge.publish_message.call_args_list}
        assert before == {"Nom-avant"}

        bridge.publish_message.reset_mock()
        eq2 = _multi_entity_eq(name="Nom-apres")
        snap2 = _snapshot(eq2)
        for m in _all_mappings(eq2, snap2):
            assert await registry.publish(m, snap2)
        calls = bridge.publish_message.call_args_list
        assert calls
        after = {json.loads(c[0][1])["device"]["name"] for c in calls}
        assert after == {"Nom-apres"}
        # unique_id et topics inchangés par le renommage
        assert all("jeedom2ha_579" in c[0][0] for c in calls)
