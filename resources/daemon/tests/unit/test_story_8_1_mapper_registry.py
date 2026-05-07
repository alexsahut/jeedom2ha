"""Story 8.1 - MapperRegistry deterministic dispatch.

Tests en isolation totale : aucune dependance MQTT, daemon ou Jeedom.
"""

from __future__ import annotations

from mapping.binary_sensor import BinarySensorMapper
from mapping.button import ButtonMapper
from mapping.cover import CoverMapper
from mapping.fallback import FallbackMapper
from mapping.light import LightMapper
from mapping.registry import MapperRegistry
from mapping.sensor import SensorMapper
from mapping.switch import SwitchMapper
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot


def _make_snapshot() -> TopologySnapshot:
    return TopologySnapshot(timestamp="2026-05-02T00:00:00", objects={}, eq_logics={})


def _cmd(
    cmd_id: int,
    generic_type: str,
    type_: str = "action",
    sub_type: str = "other",
) -> JeedomCmd:
    return JeedomCmd(
        id=cmd_id,
        name=generic_type,
        generic_type=generic_type,
        type=type_,
        sub_type=sub_type,
    )


def _eq(
    eq_id: int,
    name: str,
    cmds: list[JeedomCmd],
    eq_type_name: str = "",
    generic_type: str | None = None,
) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=eq_id,
        name=name,
        eq_type_name=eq_type_name,
        generic_type=generic_type,
        cmds=cmds,
    )


def _light_eq() -> JeedomEqLogic:
    return _eq(
        10,
        "Lampe salon",
        [
            _cmd(101, "LIGHT_ON", type_="action", sub_type="other"),
            _cmd(102, "LIGHT_OFF", type_="action", sub_type="other"),
            _cmd(103, "LIGHT_STATE", type_="info", sub_type="binary"),
        ],
    )


def _cover_eq() -> JeedomEqLogic:
    return _eq(
        20,
        "Volet salon",
        [
            _cmd(201, "FLAP_UP", type_="action", sub_type="other"),
            _cmd(202, "FLAP_DOWN", type_="action", sub_type="other"),
            _cmd(203, "FLAP_STATE", type_="info", sub_type="numeric"),
        ],
    )


def _switch_eq() -> JeedomEqLogic:
    return _eq(
        30,
        "Prise cuisine",
        [
            _cmd(301, "ENERGY_ON", type_="action", sub_type="other"),
            _cmd(302, "ENERGY_OFF", type_="action", sub_type="other"),
            _cmd(303, "ENERGY_STATE", type_="info", sub_type="binary"),
        ],
        eq_type_name="prise",
    )


def _unknown_eq() -> JeedomEqLogic:
    return _eq(
        40,
        "Equipement non mappe",
        [_cmd(401, "GENERIC_INFO", type_="info", sub_type="string")],
    )


def _sensor_eq() -> JeedomEqLogic:
    return _eq(
        50,
        "Temperature salon",
        [_cmd(501, "TEMPERATURE", type_="info", sub_type="numeric")],
    )


def _hardcoded_cascade(eq: JeedomEqLogic, snapshot: TopologySnapshot):
    mapping = LightMapper().map(eq, snapshot)
    if mapping is None:
        mapping = CoverMapper().map(eq, snapshot)
    if mapping is None:
        mapping = SwitchMapper().map(eq, snapshot)
    if mapping is None:
        mapping = BinarySensorMapper().map(eq, snapshot)
    if mapping is None:
        mapping = SensorMapper().map(eq, snapshot)
    if mapping is None:
        mapping = ButtonMapper().map(eq, snapshot)
    if mapping is None:
        mapping = FallbackMapper().map(eq, snapshot)
    return mapping


def test_ac1_mapper_registry_exposes_canonical_order():
    registry = MapperRegistry()

    assert [type(mapper) for mapper in registry.mappers] == [
        LightMapper,
        CoverMapper,
        SwitchMapper,
        BinarySensorMapper,
        SensorMapper,
        ButtonMapper,
        FallbackMapper,
    ]


def test_ac2_fallback_mapper_with_info_returns_sensor():
    """FallbackMapper produit sensor pour eq avec commande Info (Story 9.4)."""
    fallback = FallbackMapper()
    eq = _eq(
        40,
        "Capteur non mappe",
        [_cmd(401, "GENERIC_INFO", type_="info", sub_type="string")],
    )
    result = fallback.map(eq, _make_snapshot())
    assert result is not None
    assert result.ha_entity_type == "sensor"
    assert result.confidence == "ambiguous"
    assert result.reason_code == "fallback_sensor_default"


def test_ac2_fallback_mapper_without_info_action_returns_none():
    """FallbackMapper retourne None si aucune commande Info ni Action (Story 9.4)."""
    fallback = FallbackMapper()
    eq = _eq(
        99,
        "Commande event",
        [_cmd(991, "JEEDOM_CHANNEL", type_="event", sub_type="other")],
    )
    assert fallback.map(eq, _make_snapshot()) is None


def test_ac3_registry_matches_hardcoded_cascade_for_light():
    snapshot = _make_snapshot()
    eq = _light_eq()

    cascade_result = _hardcoded_cascade(eq, snapshot)
    registry_result = MapperRegistry().map(eq, snapshot)

    assert cascade_result is not None
    assert registry_result is not None
    assert cascade_result.ha_entity_type == "light"
    assert registry_result.ha_entity_type == "light"


def test_ac3_registry_matches_hardcoded_cascade_for_cover():
    snapshot = _make_snapshot()
    eq = _cover_eq()

    cascade_result = _hardcoded_cascade(eq, snapshot)
    registry_result = MapperRegistry().map(eq, snapshot)

    assert cascade_result is not None
    assert registry_result is not None
    assert cascade_result.ha_entity_type == "cover"
    assert registry_result.ha_entity_type == "cover"


def test_ac3_registry_matches_hardcoded_cascade_for_switch():
    snapshot = _make_snapshot()
    eq = _switch_eq()

    cascade_result = _hardcoded_cascade(eq, snapshot)
    registry_result = MapperRegistry().map(eq, snapshot)

    assert cascade_result is not None
    assert registry_result is not None
    assert cascade_result.ha_entity_type == "switch"
    assert registry_result.ha_entity_type == "switch"


def test_ac3_registry_matches_hardcoded_cascade_for_unknown_eq_now_fallback():
    """_unknown_eq (Info string) is captured by FallbackMapper → sensor ambiguous (Story 9.4)."""
    snapshot = _make_snapshot()
    eq = _unknown_eq()

    cascade_result = _hardcoded_cascade(eq, snapshot)
    registry_result = MapperRegistry().map(eq, snapshot)

    assert cascade_result is not None
    assert registry_result is not None
    assert cascade_result.ha_entity_type == "sensor"
    assert registry_result.ha_entity_type == "sensor"
    assert cascade_result.confidence == "ambiguous"
    assert registry_result.confidence == "ambiguous"


def test_ac3_registry_matches_hardcoded_cascade_for_sensor():
    snapshot = _make_snapshot()
    eq = _sensor_eq()

    cascade_result = _hardcoded_cascade(eq, snapshot)
    registry_result = MapperRegistry().map(eq, snapshot)

    assert cascade_result is not None
    assert registry_result is not None
    assert cascade_result.ha_entity_type == "sensor"
    assert registry_result.ha_entity_type == "sensor"
