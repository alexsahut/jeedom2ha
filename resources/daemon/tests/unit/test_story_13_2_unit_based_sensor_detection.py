"""Story 13.2 - unit-based W/Wh/kWh sensor detection without generic_type."""

from __future__ import annotations

from mapping.sensor import SensorMapper
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot, assess_eligibility


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-07-01T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Local technique")},
        eq_logics={eq.id: eq},
    )


def _eq_with_unit(
    *,
    unit: str | None,
    eq_id: int = 13200,
    cmd_id: int = 132001,
    current_value: object = None,
    cmd_name: str | None = None,
    eq_type_name: str = "virtual",
    is_excluded: bool = False,
    exclusion_source: str | None = None,
) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=eq_id,
        name=f"Mesure {eq_id}",
        object_id=1,
        eq_type_name=eq_type_name,
        is_excluded=is_excluded,
        exclusion_source=exclusion_source,
        cmds=[
            JeedomCmd(
                id=cmd_id,
                name=cmd_name or f"Mesure {cmd_id}",
                generic_type=None,
                type="info",
                sub_type="numeric",
                unit=unit,
                current_value=current_value,
            )
        ],
    )


def test_eligibility_without_generic_type_accepts_w_unit():
    eq = _eq_with_unit(unit="W")

    result = assess_eligibility(eq)

    assert result.is_eligible is True
    assert result.reason_code == "eligible"


def test_eligibility_keeps_unknown_unit_ineligible():
    eq = _eq_with_unit(unit="bananes")

    result = assess_eligibility(eq)

    assert result.is_eligible is False
    assert result.reason_code == "no_supported_generic_type"


def test_eligibility_keeps_non_cumulative_kwh_ineligible():
    eq = _eq_with_unit(unit="kWh", cmd_name="Mesure instantanee")

    result = assess_eligibility(eq)

    assert result.is_eligible is False
    assert result.reason_code == "no_supported_generic_type"


def test_eligibility_exclusion_stays_prioritary_with_reliable_unit():
    eq = _eq_with_unit(unit="kWh", cmd_name="Energie jour", is_excluded=True, exclusion_source="plugin")

    result = assess_eligibility(eq)

    assert result.is_eligible is False
    assert result.reason_code == "excluded_plugin"


def test_sensor_without_generic_type_w_maps_to_power_metadata():
    eq = _eq_with_unit(unit="W", current_value=456)

    mapping = SensorMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.reason_code == "sensor_unit_power"
    assert mapping.ha_unique_id == "jeedom2ha_eq_13200_cmd_132001"
    assert mapping.commands["132001"].current_value == 456
    assert mapping.reason_details == {
        "device_class": "power",
        "unit_of_measurement": "W",
        "state_class": "measurement",
        "cmd_id": 132001,
        "object_id": "jeedom2ha_13200_132001",
        "node_id": "jeedom2ha_13200_132001",
        "state_topic": "jeedom2ha/13200/132001/state",
    }


def test_sensor_without_generic_type_kwh_maps_to_energy_metadata_when_cumulative():
    eq = _eq_with_unit(unit="kWh", current_value=12.3, cmd_name="Energie jour")

    mapping = SensorMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.reason_code == "sensor_unit_energy"
    assert mapping.reason_details["device_class"] == "energy"
    assert mapping.reason_details["unit_of_measurement"] == "kWh"
    assert mapping.reason_details["state_class"] == "total_increasing"
    assert mapping.commands["132001"].current_value == 12.3


def test_accented_energy_session_maps_to_total_increasing():
    eq = _eq_with_unit(unit="Wh", current_value=42, cmd_name="Énergie session")

    mapping = SensorMapper().map(eq, _snapshot(eq))

    assert mapping is not None
    assert mapping.reason_code == "sensor_unit_energy"
    assert mapping.reason_details["device_class"] == "energy"
    assert mapping.reason_details["unit_of_measurement"] == "Wh"
    assert mapping.reason_details["state_class"] == "total_increasing"


def test_sensor_without_generic_type_kwh_without_cumulative_semantics_is_rejected():
    eq = _eq_with_unit(unit="kWh", current_value=12.3, cmd_name="Mesure instantanee")

    assert SensorMapper().map(eq, _snapshot(eq)) is None


def test_sensor_without_generic_type_rejects_ambiguous_units():
    for unit in ("%", "H", "bananes", None):
        eq = _eq_with_unit(unit=unit)

        assert SensorMapper().map(eq, _snapshot(eq)) is None


def test_msunpv_multi_sensor_behavior_is_preserved_for_percent_and_wh():
    eq = JeedomEqLogic(
        id=553,
        name="MSunPV / RouteurSolaire",
        object_id=1,
        eq_type_name="msunpv",
        cmds=[
            JeedomCmd(id=5139, name="Routage cumulus", generic_type=None, type="info", sub_type="numeric", unit="%"),
            JeedomCmd(id=5171, name="Production journaliere", generic_type=None, type="info", sub_type="numeric", unit="Wh"),
        ],
    )

    mappings = {m.reason_details["cmd_id"]: m for m in SensorMapper().map_all(eq, _snapshot(eq))}

    assert set(mappings) == {5139, 5171}
    assert mappings[5139].reason_code == "sensor_multi_routeur_solaire"
    assert mappings[5139].reason_details["device_class"] is None
    assert mappings[5139].reason_details["unit_of_measurement"] == "%"
    assert "state_class" not in mappings[5139].reason_details
    assert mappings[5171].reason_code == "sensor_multi_routeur_solaire"
    assert mappings[5171].reason_details["device_class"] == "energy"
    assert mappings[5171].reason_details["state_class"] == "total_increasing"
