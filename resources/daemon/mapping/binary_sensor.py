"""binary_sensor.py — Mapper Jeedom Info binary vers Home Assistant binary_sensor."""

from __future__ import annotations

from typing import Dict, Optional

from models.mapping import MappingResult, SensorCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot

_BINARY_SENSOR_GENERIC_TYPE_MAP: Dict[str, Optional[str]] = {
    "BATTERY_CHARGING": "battery_charging",
    "CAMERA_RECORD_STATE": "running",
    "HEATING_STATE": "heat",
    "PRESENCE": "occupancy",
    "SMOKE": "smoke",
    "FILTER_CLEAN_STATE": "problem",
    "WATER_LEAK": "moisture",
    "LOCK_STATE": "lock",
    "BARRIER_STATE": "garage_door",
    "GARAGE_STATE": "garage_door",
    "OPENING": "door",
    "OPENING_WINDOW": "window",
    "DOCK_STATE": None,
    "SIREN_STATE": "sound",
    "ALARM_STATE": "safety",
    "ALARM_ENABLE_STATE": "safety",
    "FLOOD": "moisture",
    "SABOTAGE": "tamper",
    "SHOCK": "vibration",
    "THERMOSTAT_LOCK": "lock",
    "THERMOSTAT_STATE": None,
    "MEDIA_STATE": "running",
    "TIMER_STATE": "running",
}


def _is_binary_info_command(cmd: JeedomCmd) -> bool:
    if (cmd.type or "").lower() != "info":
        return False
    sub_type = (cmd.sub_type or "").lower()
    if "numeric" in sub_type:
        return False
    return "binary" in sub_type


class BinarySensorMapper:
    """Mappe un eqLogic Jeedom en HA binary_sensor via type générique Info binary."""

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        for cmd in eq.cmds:
            generic_type = cmd.generic_type
            if not generic_type or generic_type not in _BINARY_SENSOR_GENERIC_TYPE_MAP:
                continue
            if not _is_binary_info_command(cmd):
                continue

            device_class = _BINARY_SENSOR_GENERIC_TYPE_MAP[generic_type]
            return MappingResult(
                ha_entity_type="binary_sensor",
                confidence="sure",
                reason_code=f"binary_sensor_{generic_type.lower()}",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands={generic_type: cmd},
                capabilities=SensorCapabilities(has_state=True),
                reason_details={"device_class": device_class},
            )

        return None
