"""Story 11.4 — Lumière actionnable + mesure de consommation → projection multi-entité.

Un eqLogic light (LIGHT_*) portant aussi POWER/CONSUMPTION doit publier
1 entité `light` + 1..n `sensor` power/energy sous un device HA commun, au lieu
d'être skippé en `ambiguous` (faux positif anti-light).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from discovery.publisher import DiscoveryPublisher
from mapping.light import LightMapper
from mapping.registry import MapperRegistry
from mapping.sensor import SensorMapper
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from transport.http_server import _collect_unpublish_node_ids


def _cmd(cmd_id, name, cmd_type, sub_type, generic_type=None, unit=None, value=None):
    return JeedomCmd(
        id=cmd_id,
        name=name,
        type=cmd_type,
        sub_type=sub_type,
        generic_type=generic_type,
        unit=unit,
        current_value=value,
    )


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-07-19T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Chambre parents")},
        eq_logics={eq.id: eq},
    )


def _dimmer_with_metering(eq_id: int = 457) -> JeedomEqLogic:
    """Fibaro Dimmer type : LIGHT_* actionnable + POWER (W) + CONSUMPTION (kWh)."""
    return JeedomEqLogic(
        id=eq_id,
        name="Chambre parents",
        object_id=1,
        eq_type_name="zwave",
        cmds=[
            _cmd(45701, "On", "action", "other", "LIGHT_ON"),
            _cmd(45702, "Off", "action", "other", "LIGHT_OFF"),
            _cmd(45703, "Etat", "info", "binary", "LIGHT_STATE", value="1"),
            _cmd(45704, "Variateur", "action", "slider", "LIGHT_SLIDER"),
            _cmd(45705, "Puissance", "info", "numeric", "POWER", "W", 42),
            _cmd(45706, "Consommation", "info", "numeric", "CONSUMPTION", "kWh", 3.5),
        ],
    )


def _dimmer_energy_plug(eq_id: int = 458) -> JeedomEqLogic:
    """AC3 — light + ENERGY_STATE/ON/OFF reste une prise (ambiguous), comportement inchangé."""
    return JeedomEqLogic(
        id=eq_id,
        name="Prise lampe salon",
        object_id=1,
        eq_type_name="zwave",
        cmds=[
            _cmd(45801, "On", "action", "other", "LIGHT_ON"),
            _cmd(45802, "Off", "action", "other", "LIGHT_OFF"),
            _cmd(45803, "Etat", "info", "binary", "LIGHT_STATE", value="1"),
            _cmd(45804, "On prise", "action", "other", "ENERGY_ON"),
            _cmd(45805, "Off prise", "action", "other", "ENERGY_OFF"),
            _cmd(45806, "Etat prise", "info", "binary", "ENERGY_STATE", value="1"),
        ],
    )


# --- AC2 : light mapper — POWER/CONSUMPTION ne sont plus des conflits ---------

def test_light_mapper_ignores_power_consumption_companions():
    eq = _dimmer_with_metering()

    result = LightMapper().map(eq, _snapshot(eq))

    assert result is not None
    assert result.ha_entity_type == "light"
    assert result.confidence in ("sure", "probable")
    assert result.reason_code != "conflicting_generic_types"
    # Les compagnons de mesure ne sont pas embarqués dans les commandes du light.
    assert "POWER" not in result.commands
    assert "CONSUMPTION" not in result.commands


# --- AC2 : ENERGY_POWER mappé explicitement (power/W), sans dépendre de l'unité ---

def test_energy_power_maps_to_power_without_relying_on_unit():
    # Une commande ENERGY_POWER sans unité Jeedom doit tout de même dériver
    # un device_class `power` via le mapping generic_type explicite.
    cmd = _cmd(45707, "Puissance instantanée", "info", "numeric", "ENERGY_POWER")

    device_class, unit = SensorMapper._derive_sensor_metadata(cmd)

    assert device_class == "power"
    assert unit == "W"


# --- Anti-fantôme : eq.generic_type non-light → reste mono eq-scoped ----------

def test_non_light_eq_generic_type_stays_mono_eq_scoped_sensor():
    # LIGHT_* + POWER/CONSUMPTION mais eq.generic_type="switch" : LightMapper renvoie
    # None (garde eq.generic_type), donc le light n'est jamais publié. Le compagnon de
    # mesure doit rester un sensor mono eq-scoped `jeedom2ha_eq_<id>` — surtout PAS
    # basculer en command-scoped, sinon le changement de node_id à type sensor constant
    # laisse un topic fantôme retenu (le lifecycle n'unpublish qu'au retypage).
    eq = _dimmer_with_metering(459)
    eq.generic_type = "switch"

    results = SensorMapper().map_all(eq, _snapshot(eq))

    assert len(results) == 1
    assert results[0].ha_entity_type == "sensor"
    assert results[0].ha_unique_id == "jeedom2ha_eq_459"


# --- AC3 : light + ENERGY_STATE reste ambiguous (prise) ----------------------

def test_light_with_energy_state_stays_ambiguous_plug():
    eq = _dimmer_energy_plug()

    result = LightMapper().map(eq, _snapshot(eq))

    assert result is not None
    assert result.confidence == "ambiguous"
    assert result.reason_code == "conflicting_generic_types"
    assert "ENERGY_STATE" in result.reason_details["conflicting_types"]


# --- AC1 : registry — light primaire + sensors power/energy, device commun ---

def test_registry_aggregates_light_primary_with_power_and_energy_sensors():
    eq = _dimmer_with_metering()

    results = MapperRegistry().map_all(eq, _snapshot(eq))

    assert [r.ha_entity_type for r in results] == ["light", "sensor", "sensor"]

    light = results[0]
    assert light.ha_unique_id == "jeedom2ha_eq_457"

    sensors = {r.reason_details["device_class"]: r for r in results[1:]}
    assert set(sensors) == {"power", "energy"}

    power = sensors["power"]
    assert power.ha_unique_id == "jeedom2ha_eq_457_cmd_45705"
    assert power.reason_details["unit_of_measurement"] == "W"
    assert power.reason_details["state_class"] == "measurement"

    energy = sensors["energy"]
    assert energy.ha_unique_id == "jeedom2ha_eq_457_cmd_45706"
    assert energy.reason_details["unit_of_measurement"] == "kWh"
    assert energy.reason_details["state_class"] == "total_increasing"

    # Aucune collision d'unique_id entre light et sensors.
    unique_ids = [r.ha_unique_id for r in results]
    assert len(unique_ids) == len(set(unique_ids))


def test_registry_map_keeps_light_primary_and_attaches_secondary_sensors():
    eq = _dimmer_with_metering()

    primary = MapperRegistry().map(eq, _snapshot(eq))

    assert primary is not None
    assert primary.ha_entity_type == "light"
    assert primary.ha_unique_id == "jeedom2ha_eq_457"
    assert [m.ha_unique_id for m in (primary.additional_mappings or [])] == [
        "jeedom2ha_eq_457_cmd_45705",
        "jeedom2ha_eq_457_cmd_45706",
    ]


def test_registry_energy_plug_light_stays_ambiguous_skipped():
    """AC3/AC4 — light + ENERGY_STATE reste ambiguous (prise), comportement inchangé :
    pas de promotion en multi-entité light + sensor."""
    eq = _dimmer_energy_plug()

    results = MapperRegistry().map_all(eq, _snapshot(eq))

    assert len(results) == 1
    assert results[0].ha_entity_type == "light"
    assert results[0].confidence == "ambiguous"


# --- AC5 : dépublication domain-aware (light + sensors), pas de ghost --------

def test_unpublish_collects_light_primary_and_sensor_secondaries():
    eq = _dimmer_with_metering()
    primary = MapperRegistry().map(eq, _snapshot(eq))

    entries = _collect_unpublish_node_ids(primary)

    # Hétérogène (light + sensor) → tuples (entity_type, node_id) couvrant TOUT.
    assert set(entries) == {
        ("light", "jeedom2ha_457"),
        ("sensor", "jeedom2ha_457_45705"),
        ("sensor", "jeedom2ha_457_45706"),
    }


# --- AC1 : discovery — device commun light + sensors -------------------------

async def test_light_and_sensors_share_common_device():
    mqtt_bridge = MagicMock()
    mqtt_bridge.publish_message.return_value = True
    publisher = DiscoveryPublisher(mqtt_bridge)
    eq = _dimmer_with_metering()
    results = MapperRegistry().map_all(eq, _snapshot(eq))

    light, power_sensor, energy_sensor = results

    assert await publisher.publish_light(light, _snapshot(eq)) is True
    light_payload = json.loads(mqtt_bridge.publish_message.call_args.args[1])
    assert light_payload["device"]["identifiers"] == ["jeedom2ha_457"]

    assert await publisher.publish_sensor(power_sensor, _snapshot(eq)) is True
    power_payload = json.loads(mqtt_bridge.publish_message.call_args.args[1])
    assert power_payload["device"]["identifiers"] == ["jeedom2ha_457"]
    assert power_payload["device_class"] == "power"
    assert power_payload["state_class"] == "measurement"
