"""Story 22.3 — pas de nom d'entité identique au nom de l'appareil.

Quand le nom d'entité égale le nom d'appareil (espaces et casse normalisés), le payload
publie ``"name": null`` : HA affiche alors le seul nom de l'appareil, sans doublon.
Identifiants et noms génériques uniquement (CC-48).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from discovery.publisher import DiscoveryPublisher
from mapping.button import ScenarioButtonMapper
from mapping.registry import MapperRegistry
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, JeedomScenario, TopologySnapshot


def _m(ha_name):
    return SimpleNamespace(ha_name=ha_name)


@pytest.fixture
def publisher():
    return DiscoveryPublisher(MagicMock())


def _snapshot(*eqs, scenarios=None):
    return TopologySnapshot(
        timestamp="2026-10-12T00:00:00+00:00",
        objects={10: JeedomObject(id=10, name="Zone-A")},
        eq_logics={eq.id: eq for eq in eqs},
        scenarios=scenarios or {},
    )


class TestEntityNameHelper:
    def test_equal_names_give_null(self, publisher):
        assert publisher._entity_name_for_payload(_m("Equip-1"), {"name": "Equip-1"}) is None

    def test_case_difference_gives_null(self, publisher):
        assert publisher._entity_name_for_payload(_m("EQUIP-1"), {"name": "equip-1"}) is None

    def test_extra_spaces_give_null(self, publisher):
        assert publisher._entity_name_for_payload(_m("  Equip   1 "), {"name": "Equip 1"}) is None

    def test_different_names_are_kept(self, publisher):
        assert publisher._entity_name_for_payload(_m("Puissance-X"), {"name": "Equip-1"}) == "Puissance-X"

    def test_empty_entity_name_with_named_device_is_kept(self, publisher):
        assert publisher._entity_name_for_payload(_m(""), {"name": "Equip-1"}) == ""


def test_scenario_button_name_is_null_and_ids_unchanged(publisher):
    sc = JeedomScenario(id=38, name="S38")
    snap = _snapshot(scenarios={38: sc})
    mapping = ScenarioButtonMapper().map(sc)
    payload = publisher._build_button_payload(mapping, snap)
    assert payload["name"] is None
    assert payload["device"]["name"] == "S38"
    assert payload["unique_id"] == mapping.ha_unique_id
    assert payload["object_id"] == "jeedom2ha_scenario_38"
    assert payload["default_entity_id"] == "button.jeedom2ha_scenario_38"
    assert payload["command_topic"] == "jeedom2ha/scenario_38/cmd"
    assert payload["device"]["identifiers"] == [mapping.ha_unique_id]


def _single_entity_eq(eq_id=240, name="Equip-240"):
    return JeedomEqLogic(
        id=eq_id, name=name, object_id=10, eq_type_name="virtual",
        cmds=[JeedomCmd(id=eq_id * 10 + 1, name="Cmd-Z", generic_type="TEMPERATURE",
                        type="info", sub_type="numeric", unit="°C")],
    )


def _multi_entity_eq(eq_id=579, name="Equip-579"):
    return JeedomEqLogic(
        id=eq_id, name=name, object_id=10, eq_type_name="zwave",
        cmds=[
            JeedomCmd(id=eq_id * 10 + 1, name="Etat", generic_type="ENERGY_STATE",
                      type="info", sub_type="binary"),
            JeedomCmd(id=eq_id * 10 + 2, name="On", generic_type="ENERGY_ON",
                      type="action", sub_type="other"),
            JeedomCmd(id=eq_id * 10 + 3, name="Off", generic_type="ENERGY_OFF",
                      type="action", sub_type="other"),
            JeedomCmd(id=eq_id * 10 + 4, name="Puissance-X", type="info",
                      sub_type="numeric", unit="W"),
            JeedomCmd(id=eq_id * 10 + 5, name="Energie-Y", type="info",
                      sub_type="numeric", unit="kWh"),
        ],
    )


def _payload(publisher, mapping, snap):
    return getattr(publisher, f"_build_{mapping.ha_entity_type}_payload")(mapping, snap)


def test_single_entity_equipment_named_like_device_has_null_name(publisher):
    eq = _single_entity_eq()
    snap = _snapshot(eq)
    primary = MapperRegistry().map(eq, snap)
    assert primary is not None and not primary.additional_mappings
    payload = _payload(publisher, primary, snap)
    assert payload["name"] is None
    assert payload["device"]["name"] == "Equip-240"
    assert payload["object_id"] == "jeedom2ha_240"
    assert payload["default_entity_id"] == "sensor.jeedom2ha_240"


def test_multi_entity_equipment_only_primary_is_null(publisher):
    eq = _multi_entity_eq()
    snap = _snapshot(eq)
    primary = MapperRegistry().map(eq, snap)
    mappings = [primary, *primary.additional_mappings]
    assert len(mappings) >= 3
    payloads = {m.ha_unique_id: _payload(publisher, m, snap) for m in mappings}
    names = sorted((p["name"] or "<null>") for p in payloads.values())
    # Entité principale : nom de l'appareil -> null ; mesures : nom de commande inchangé.
    assert names == ["<null>", "Energie-Y", "Puissance-X"]
    assert {p["device"]["name"] for p in payloads.values()} == {"Equip-579"}
