"""sensor.py — Mapper Jeedom Info numeric vers Home Assistant sensor."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from models.mapping import MappingResult, SensorCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot

_SENSOR_GENERIC_TYPE_MAP: Dict[str, Tuple[Optional[str], Optional[str]]] = {
    "TEMPERATURE": ("temperature", "°C"),
    "HUMIDITY": ("humidity", "%"),
    "POWER": ("power", "W"),
    "CONSUMPTION": ("energy", "kWh"),
    "VOLTAGE": ("voltage", "V"),
    "AIR_QUALITY": ("aqi", None),
    "BRIGHTNESS": ("illuminance", "lx"),
    "UV": ("irradiance", None),
    "CO2": ("carbon_dioxide", "ppm"),
    "CO": ("carbon_monoxide", "ppm"),
    "NOISE": ("sound_pressure", "dB"),
    "PRESSURE": ("atmospheric_pressure", "hPa"),
    "DEPTH": ("distance", "m"),
    "DISTANCE": ("distance", "m"),
    "BATTERY": ("battery", "%"),
    "VOLUME": (None, None),
    "WEATHER_TEMPERATURE": ("temperature", "°C"),
    "WEATHER_HUMIDITY": ("humidity", "%"),
    "WEATHER_PRESSURE": ("atmospheric_pressure", "hPa"),
    "WIND_SPEED": ("wind_speed", "km/h"),
    "WEATHER_WIND_SPEED": ("wind_speed", "km/h"),
    "RAIN_TOTAL": ("precipitation", "mm"),
    "RAIN_CURRENT": ("precipitation_intensity", "mm/h"),
    "THERMOSTAT_TEMPERATURE": ("temperature", "°C"),
    "THERMOSTAT_SETPOINT": ("temperature", "°C"),
    "THERMOSTAT_HUMIDITY": ("humidity", "%"),
    "THERMOSTAT_TEMPERATURE_OUTDOOR": ("temperature", "°C"),
    "FAN_SPEED_STATE": (None, "rpm"),
    "ROTATION_STATE": (None, "rpm"),
}


def _is_numeric_info_command(cmd: JeedomCmd) -> bool:
    if (cmd.type or "").lower() != "info":
        return False

    sub_type = (cmd.sub_type or "").lower()
    if "binary" in sub_type:
        return False
    return "numeric" in sub_type


class SensorMapper:
    """Mappe un eqLogic Jeedom en HA sensor via type générique Info numeric."""

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        for cmd in eq.cmds:
            generic_type = cmd.generic_type
            if not generic_type or generic_type not in _SENSOR_GENERIC_TYPE_MAP:
                continue
            if not _is_numeric_info_command(cmd):
                continue

            device_class, unit_of_measurement = _SENSOR_GENERIC_TYPE_MAP[generic_type]
            return MappingResult(
                ha_entity_type="sensor",
                confidence="sure",
                reason_code=f"sensor_{generic_type.lower()}",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands={generic_type: cmd},
                capabilities=SensorCapabilities(has_state=True),
                reason_details={
                    "device_class": device_class,
                    "unit_of_measurement": unit_of_measurement,
                },
            )

        return None
