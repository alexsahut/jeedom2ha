"""sensor.py — Mapper Jeedom Info numeric vers Home Assistant sensor.

Story 11.1 PE — support multi-sensor borné : un eqLogic « routeur solaire »
(MSunPV) expose plusieurs commandes info numériques comme autant de `sensor` HA
distincts rattachés au même device Jeedom, sans régression sur le comportement
mono-sensor historique des autres équipements.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from models.mapping import MappingResult, SensorCapabilities
from models.topology import (
    MULTI_SENSOR_EQ_TYPES,
    JeedomCmd,
    JeedomEqLogic,
    TopologySnapshot,
    is_reliable_unit_sensor_command,
)

_SENSOR_GENERIC_TYPE_MAP: Dict[str, Tuple[Optional[str], Optional[str]]] = {
    "TEMPERATURE": ("temperature", "°C"),
    "HUMIDITY": ("humidity", "%"),
    "POWER": ("power", "W"),
    "ENERGY_POWER": ("power", "W"),
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


# Story 11.1 — eq_type_name (plugin source) éligibles au mapping multi-sensor borné.
# Source de vérité unique dans models.topology (partagée avec assess_eligibility),
# pour que l'éligibilité et le mapping restent cohérents. Restreint à MSunPV
# (garde-fou AC 4 — pas de régression mono-entité).
_MULTI_SENSOR_EQ_TYPES = MULTI_SENSOR_EQ_TYPES

# Story 11.1 — inférence honnête d'un device_class HA à partir de l'unité Jeedom,
# pour les commandes info numériques sans generic_type standard. Toute unité non
# listée ne reçoit AUCUN device_class (publication honnête plutôt que classe fausse).
_UNIT_DEVICE_CLASS: Dict[str, str] = {
    "W": "power",
    "kW": "power",
    "Wh": "energy",
    "kWh": "energy",
    "V": "voltage",
    "A": "current",
}


def _derive_state_class(device_class: Optional[str], unit_of_measurement: Optional[str]) -> Optional[str]:
    if device_class == "power" and unit_of_measurement == "W":
        return "measurement"
    if device_class == "energy" and unit_of_measurement in {"Wh", "kWh"}:
        return "total_increasing"
    return None


def _sensor_reason_details(
    device_class: Optional[str],
    unit_of_measurement: Optional[str],
    extra: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    details: Dict[str, object] = {
        "device_class": device_class,
        "unit_of_measurement": unit_of_measurement,
    }
    state_class = _derive_state_class(device_class, unit_of_measurement)
    if state_class is not None:
        details["state_class"] = state_class
    if extra:
        details.update(extra)
    return details


def _is_numeric_info_command(cmd: JeedomCmd) -> bool:
    if (cmd.type or "").lower() != "info":
        return False

    sub_type = (cmd.sub_type or "").lower()
    if "binary" in sub_type:
        return False
    return "numeric" in sub_type


def _is_multi_sensor_eq(eq: JeedomEqLogic) -> bool:
    if _has_structural_multi_entity_sensor_shape(eq):
        return True
    return (eq.eq_type_name or "").lower() in _MULTI_SENSOR_EQ_TYPES


_ACTIONABLE_LIGHT_GENERIC_TYPES = {"LIGHT_ON", "LIGHT_OFF", "LIGHT_SLIDER", "LIGHT_BRIGHTNESS"}


def _has_structural_multi_entity_sensor_shape(eq: JeedomEqLogic) -> bool:
    switch_types = {"ENERGY_STATE", "ENERGY_ON", "ENERGY_OFF", "SWITCH_STATE", "SWITCH_ON", "SWITCH_OFF"}
    has_switch_shape = any(cmd.generic_type in switch_types for cmd in eq.cmds)
    numeric_count = sum(1 for cmd in eq.cmds if _is_numeric_info_command(cmd))
    if has_switch_shape and numeric_count >= 2:
        return True
    # Story 11.4 — lumière actionnable + compagnon(s) de mesure power/energy (sans
    # forme prise ENERGY_*/SWITCH_*) : les compagnons deviennent des sensors HA
    # command-scoped rattachés au device commun, pour éviter la collision d'unique_id
    # avec le light primaire (jeedom2ha_eq_<id>).
    if (
        not has_switch_shape
        and _has_actionable_light_shape(eq)
        and _has_power_or_energy_companion(eq)
        and _eq_generic_type_allows_light(eq)
    ):
        return True
    return False


def _has_actionable_light_shape(eq: JeedomEqLogic) -> bool:
    return any(cmd.generic_type in _ACTIONABLE_LIGHT_GENERIC_TYPES for cmd in eq.cmds)


def _eq_generic_type_allows_light(eq: JeedomEqLogic) -> bool:
    # Miroir du garde LightMapper (light.py) : un eq.generic_type non-light fait
    # renvoyer None au LightMapper, donc le light n'est jamais publié. Dans ce cas le
    # compagnon power/energy doit rester un sensor mono eq-scoped (jeedom2ha_eq_<id>)
    # plutôt que basculer en command-scoped — sinon le changement de node_id à type
    # sensor constant laisse un topic fantôme retenu (aucun unpublish de retypage).
    generic_type = (eq.generic_type or "").lower()
    return generic_type in ("", "light")


def _has_power_or_energy_companion(eq: JeedomEqLogic) -> bool:
    for cmd in eq.cmds:
        if not _is_numeric_info_command(cmd):
            continue
        if SensorMapper._derive_sensor_metadata(cmd)[0] in {"power", "energy"}:
            return True
    return False


def _is_actionable_readback_consumed_by_switch(cmd: JeedomCmd, eq: JeedomEqLogic) -> bool:
    generic_type = cmd.generic_type
    if generic_type == "ENERGY_STATE":
        has_action = any(other.generic_type in {"ENERGY_ON", "ENERGY_OFF"} for other in eq.cmds)
        state_cmds = [other for other in eq.cmds if other.generic_type == "ENERGY_STATE"]
        return has_action and bool(state_cmds) and state_cmds[-1].id == cmd.id
    if generic_type == "SWITCH_STATE":
        key = _switch_group_key(cmd.name)
        group_types = {
            other.generic_type
            for other in eq.cmds
            if _switch_group_key(other.name) == key
        }
        return {"SWITCH_STATE", "SWITCH_ON", "SWITCH_OFF"}.issubset(group_types)
    return False


def _switch_group_key(name: str) -> str:
    normalized = (name or "").strip().lower()
    normalized = normalized.removesuffix(" on").removesuffix(" off")
    normalized = normalized.removesuffix("_on").removesuffix("_off")
    normalized = normalized.removesuffix("-on").removesuffix("-off")
    return " ".join(normalized.split())


class SensorMapper:
    """Mappe un eqLogic Jeedom en HA sensor via type générique Info numeric."""

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        """API historique : retourne le mapping sensor principal (ou None).

        Conserve la compatibilité des consommateurs attendant un mapping unique
        par eqLogic. Le support multi-sensor passe par ``map_all``.
        """
        mappings = self.map_all(eq, snapshot)
        return mappings[0] if mappings else None

    def map_all(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> List[MappingResult]:
        """API additive Story 11.1 : retourne 0..N mappings sensor pour l'eqLogic.

        - Cas standard : au plus un mapping (premier generic_type connu), strictement
          identique au comportement mono-sensor historique.
        - Cas multi-sensor borné (MSunPV) : un mapping par commande info numérique,
          chacun avec identifiants/topic distincts dérivés de l'ID cmd Jeedom.
        """
        if _is_multi_sensor_eq(eq):
            return self._map_multi_sensor(eq, snapshot)

        primary = self._map_single(eq, snapshot)
        return [primary] if primary is not None else []

    def _map_single(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
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
                reason_details=_sensor_reason_details(device_class, unit_of_measurement),
            )

        for cmd in eq.cmds:
            if cmd.generic_type is not None:
                continue
            if not _is_numeric_info_command(cmd):
                continue
            if not is_reliable_unit_sensor_command(cmd):
                continue

            device_class, unit_of_measurement = self._derive_sensor_metadata(cmd)
            if device_class not in {"power", "energy"}:
                continue
            reason_code = "sensor_unit_power" if device_class == "power" else "sensor_unit_energy"
            return MappingResult(
                ha_entity_type="sensor",
                confidence="sure",
                reason_code=reason_code,
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}_cmd_{cmd.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands={str(cmd.id): cmd},
                capabilities=SensorCapabilities(has_state=True),
                reason_details=_sensor_reason_details(
                    device_class,
                    unit_of_measurement,
                    {
                        "cmd_id": cmd.id,
                        "object_id": f"jeedom2ha_{eq.id}_{cmd.id}",
                        "node_id": f"jeedom2ha_{eq.id}_{cmd.id}",
                        "state_topic": f"jeedom2ha/{eq.id}/{cmd.id}/state",
                    },
                ),
            )

        return None

    def _map_multi_sensor(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> List[MappingResult]:
        suggested_area = snapshot.get_suggested_area(eq.id)
        mappings: List[MappingResult] = []

        for cmd in eq.cmds:
            if not _is_numeric_info_command(cmd):
                continue
            if _is_actionable_readback_consumed_by_switch(cmd, eq):
                continue

            device_class, unit_of_measurement = self._derive_sensor_metadata(cmd)
            mappings.append(
                MappingResult(
                    ha_entity_type="sensor",
                    confidence="sure",
                    reason_code="sensor_multi_routeur_solaire",
                    jeedom_eq_id=eq.id,
                    # Identité par commande (IDs Jeedom stables), device commun à l'eqLogic.
                    ha_unique_id=f"jeedom2ha_eq_{eq.id}_cmd_{cmd.id}",
                    ha_name=cmd.name,
                    suggested_area=suggested_area,
                    commands={str(cmd.id): cmd},
                    capabilities=SensorCapabilities(has_state=True),
                    reason_details=_sensor_reason_details(
                        device_class,
                        unit_of_measurement,
                        {
                            "cmd_id": cmd.id,
                            "object_id": f"jeedom2ha_{eq.id}_{cmd.id}",
                            "node_id": f"jeedom2ha_{eq.id}_{cmd.id}",
                            "state_topic": f"jeedom2ha/{eq.id}/{cmd.id}/state",
                        },
                    ),
                )
            )

        return mappings

    @staticmethod
    def _derive_sensor_metadata(cmd: JeedomCmd) -> Tuple[Optional[str], Optional[str]]:
        """Déduit (device_class, unit) pour une commande multi-sensor.

        Préfère le mapping generic_type standard ; à défaut, infère le device_class
        depuis l'unité Jeedom. Aucune classe inventée quand l'unité est inconnue.
        """
        generic_type = cmd.generic_type
        if generic_type and generic_type in _SENSOR_GENERIC_TYPE_MAP:
            return _SENSOR_GENERIC_TYPE_MAP[generic_type]

        unit = cmd.unit or None
        device_class = _UNIT_DEVICE_CLASS.get(unit) if unit and is_reliable_unit_sensor_command(cmd) else None
        return device_class, unit
