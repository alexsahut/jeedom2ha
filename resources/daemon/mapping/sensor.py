"""sensor.py — Capability-based sensor mapper for Home Assistant.

Story 2.5: Mapping & Exposition des Capteurs (Numériques & Binaires).
Returns a list of MappingResults since one Jeedom EqLogic can hold multiple sensors.
"""
from typing import List, Optional, Any, Dict

from models.topology import JeedomEqLogic, JeedomCmd, TopologySnapshot
from models.mapping import MappingResult, SensorCapabilities, PublicationDecision

_SENSOR_PUBLICATION_POLICY = {
    "sure": True,
    "probable": True,
    "ambiguous": False,
    "unknown": False,
    "ignore": False,
}

# Scope garanti et optionnel
_NUMERIC_SENSORS = {
    "TEMPERATURE", "HUMIDITY", "POWER", "CONSUMPTION", "BATTERY", 
    "LUMINOSITY", "CO2", "PRESSURE"
}

_BINARY_SENSORS = {
    "OPENING", "MOTION", "PRESENCE", "SMOKE", "WATER", "BATTERY_STATE"
}

_SUPPORTED_GENERIC_TYPES = _NUMERIC_SENSORS | _BINARY_SENSORS


# Dictionnaires d'affinité pour les métadonnées fiables
# Structure: GENERIC_TYPE -> (device_class, set(valid_units))
_NUMERIC_AFFINITIES: Dict[str, tuple[str, set[str]]] = {
    "TEMPERATURE": ("temperature", {"°C", "°F"}),
    "HUMIDITY": ("humidity", {"%"}),
    "POWER": ("power", {"W", "kW"}),
    "CONSUMPTION": ("energy", {"Wh", "kWh"}),
    "BATTERY": ("battery", {"%"}),
    "LUMINOSITY": ("illuminance", {"lx", "lux"}),
    "CO2": ("carbon_dioxide", {"ppm"}),
    "PRESSURE": ("atmospheric_pressure", {"hPa", "mbar"}),
}

_BINARY_AFFINITIES: Dict[str, str] = {
    "OPENING": "opening",
    "MOTION": "motion",
    "PRESENCE": "presence",
    "SMOKE": "smoke",
    "WATER": "moisture",
    "BATTERY_STATE": "battery",
}


class SensorMapper:
    """Extracts sensor and binary_sensor capabilities from Jeedom commands."""

    def normalize_binary_value(self, val: Any) -> Optional[str]:
        """Convert known binary representations to strict 'ON'/'OFF'."""
        if val is None:
            return None
            
        if isinstance(val, bool):
            return "ON" if val else "OFF"
            
        if isinstance(val, (int, float)):
            if val == 1:
                return "ON"
            elif val == 0:
                return "OFF"
            return None
            
        if isinstance(val, str):
            v_lower = val.lower().strip()
            if v_lower in ("1", "true", "on", "open"):
                return "ON"
            if v_lower in ("0", "false", "off", "closed"):
                return "OFF"
                
        return None

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> List[MappingResult]:
        """Map Jeedom equipment to multiple sensor capabilities if relevant."""
        results = []

        for cmd in eq.cmds:
            if cmd.type != "info":
                continue

            gtype = cmd.generic_type
            if not gtype or gtype not in _SUPPORTED_GENERIC_TYPES:
                continue

            # It's a supported sensor
            is_binary = gtype in _BINARY_SENSORS
            
            # Sub-type checks for safety
            if is_binary and cmd.sub_type != "binary":
                continue # Incoherent
            elif not is_binary and cmd.sub_type != "numeric":
                continue # Incoherent

            capabilities = SensorCapabilities(is_binary=is_binary)
            confidence = "sure"
            reason_code = f"sensor_{gtype.lower()}"
            reason_details = {"generic_type": gtype}

            # Map Metadata
            if is_binary:
                capabilities.device_class = _BINARY_AFFINITIES.get(gtype)
            else:
                affinity = _NUMERIC_AFFINITIES.get(gtype)
                if affinity:
                    expected_dc, expected_units = affinity
                    capabilities.device_class = expected_dc

                    # Unit validation
                    unit = cmd.unit.strip() if cmd.unit else None
                    if unit in expected_units:
                        capabilities.unit_of_measurement = unit
                    elif unit:
                        # Unit provided but incoherent with generic_type -> ambiguity
                        confidence = "ambiguous"
                        reason_code = "incoherent_metadata"
                        reason_details["unit"] = unit

                    # Special rule for CONSUMPTION
                    if gtype == "CONSUMPTION":
                        name_lower = cmd.name.lower()
                        unit_lower = unit.lower() if unit else ""
                        if ("total" in name_lower or "index" in name_lower or 
                            unit_lower in ("wh", "kwh")):
                            capabilities.state_class = "total_increasing"

            if confidence == "sure" and not eq.eq_type_name:
                confidence = "probable" # Fallback if eq_type_name isn't strong? Actually AC says nothing about this downgrading for sensors. Let's keep it 'sure' or 'probable' based on something or just 'sure'. AC: "confidence sure, probable, ambiguous. Rejeter si unité incohérente". I'll default to sure if unit is correct or absent when valid.
                
            # Create MappingResult for this specific command
            ha_unique_id = f"jeedom2ha_cmd_{cmd.id}"
            ha_name = f"{eq.name} {cmd.name}"
            
            res = MappingResult(
                ha_entity_type="binary_sensor" if is_binary else "sensor",
                confidence=confidence,
                reason_code=reason_code,
                jeedom_eq_id=eq.id,
                ha_unique_id=ha_unique_id,
                ha_name=ha_name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands={ha_unique_id: cmd}, # Storing the command using ha_unique_id as key or generic_type? Let's use generic_type for consistency with others, or simply "sensor"
                capabilities=capabilities,
                reason_details=reason_details
            )
            # Override commands dict to follow pattern
            res.commands = {"sensor": cmd}
            results.append(res)

        return results

    def decide_publication(self, mapping: MappingResult) -> PublicationDecision:
        """Decide if this sensor should be published based on confidence and policy."""
        should_publish = _SENSOR_PUBLICATION_POLICY.get(mapping.confidence, False)
        
        reason = mapping.confidence
        if not should_publish:
            reason = f"{mapping.confidence}_skipped"
            
        return PublicationDecision(
            should_publish=should_publish,
            reason=reason,
            mapping_result=mapping
        )
