"""binary_sensor.py — Mapper Jeedom Info binary vers Home Assistant binary_sensor.

Story 11.2 PE — support multi-domaine : un eqLogic structurellement multi-entité
expose ses commandes info binaires
comme autant de `binary_sensor` HA distincts rattachés au même device, sans
régression sur le comportement mono-binaire historique des autres équipements.
Les commandes binaires portant un generic_type de readback switch sont exclues : elles sont
déjà projetées par le `switch` (anti-doublon).
"""

from __future__ import annotations

from typing import Dict, List, Optional

from models.mapping import MappingResult, SensorCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot

# Story 11.2 — generic_types portés par le switch ; leurs commandes binaires ne
# doivent jamais être dupliquées en binary_sensor.
_SWITCH_OWNED_GENERIC_TYPES = frozenset({
    "ENERGY_STATE", "ENERGY_ON", "ENERGY_OFF",
    "SWITCH_STATE", "SWITCH_ON", "SWITCH_OFF",
})

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
    "SWITCH_STATE": None,
}


def _is_binary_info_command(cmd: JeedomCmd) -> bool:
    if (cmd.type or "").lower() != "info":
        return False
    sub_type = (cmd.sub_type or "").lower()
    if "numeric" in sub_type:
        return False
    return "binary" in sub_type


def _is_multi_domain_eq(eq: JeedomEqLogic) -> bool:
    switch_types = {"ENERGY_STATE", "ENERGY_ON", "ENERGY_OFF", "SWITCH_STATE", "SWITCH_ON", "SWITCH_OFF"}
    has_switch_shape = any(cmd.generic_type in switch_types for cmd in eq.cmds)
    binary_candidates = [
        cmd for cmd in eq.cmds
        if _is_binary_info_command(cmd) and cmd.generic_type not in _SWITCH_OWNED_GENERIC_TYPES
    ]
    numeric_count = sum(
        1 for cmd in eq.cmds
        if (cmd.type or "").lower() == "info"
        and "numeric" in (cmd.sub_type or "").lower()
        and "binary" not in (cmd.sub_type or "").lower()
    )
    switch_state_count = sum(1 for cmd in eq.cmds if cmd.generic_type in {"SWITCH_STATE", "ENERGY_STATE"})
    return has_switch_shape and (bool(binary_candidates) or numeric_count >= 2 or switch_state_count >= 2)


class BinarySensorMapper:
    """Mappe un eqLogic Jeedom en HA binary_sensor via type générique Info binary."""

    def map_all(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> List[MappingResult]:
        """API additive Story 11.2 : retourne 0..N mappings binary_sensor.

        - Cas standard : au plus un mapping (premier generic_type connu), strictement
          identique au comportement mono-binaire historique.
        - Cas multi-domaine structurel : un mapping par commande info binaire,
          chacun avec identité distincte dérivée de l'ID cmd Jeedom. Les commandes
          ENERGY_* (portées par le switch) sont exclues.
        """
        if _is_multi_domain_eq(eq):
            return self._map_multi_domain(eq, snapshot)

        primary = self.map(eq, snapshot)
        return [primary] if primary is not None else []

    def _map_multi_domain(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> List[MappingResult]:
        suggested_area = snapshot.get_suggested_area(eq.id)
        mappings: List[MappingResult] = []

        for cmd in eq.cmds:
            if not _is_binary_info_command(cmd):
                continue
            if cmd.id in _switch_readback_cmd_ids(eq):
                continue  # déjà projeté par le switch — pas de doublon

            device_class = _BINARY_SENSOR_GENERIC_TYPE_MAP.get(cmd.generic_type)
            mappings.append(
                MappingResult(
                    ha_entity_type="binary_sensor",
                    confidence="sure",
                    reason_code="binary_sensor_multi_domain",
                    jeedom_eq_id=eq.id,
                    # Identité par commande (IDs Jeedom stables), device commun à l'eqLogic.
                    ha_unique_id=f"jeedom2ha_eq_{eq.id}_cmd_{cmd.id}",
                    ha_name=cmd.name,
                    suggested_area=suggested_area,
                    commands={str(cmd.id): cmd},
                    capabilities=SensorCapabilities(has_state=True),
                    reason_details={
                        "device_class": device_class,
                        "cmd_id": cmd.id,
                        "object_id": f"jeedom2ha_{eq.id}_{cmd.id}",
                        "node_id": f"jeedom2ha_{eq.id}_{cmd.id}",
                        "state_topic": f"jeedom2ha/{eq.id}/{cmd.id}/state",
                    },
                )
            )

        return mappings

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


def _switch_readback_cmd_ids(eq: JeedomEqLogic) -> set[int]:
    """Return state cmd ids consumed by complete ENERGY_*/SWITCH_* switch trios."""
    consumed: set[int] = set()
    energy_state = None
    has_energy_on = False
    has_energy_off = False
    switch_groups: Dict[str, Dict[str, JeedomCmd]] = {}

    for cmd in eq.cmds:
        if cmd.generic_type == "ENERGY_STATE":
            energy_state = cmd
        elif cmd.generic_type == "ENERGY_ON":
            has_energy_on = True
        elif cmd.generic_type == "ENERGY_OFF":
            has_energy_off = True
        elif cmd.generic_type in {"SWITCH_STATE", "SWITCH_ON", "SWITCH_OFF"}:
            key = _switch_group_key(cmd.name)
            switch_groups.setdefault(key, {})[cmd.generic_type] = cmd

    if energy_state is not None and has_energy_on and has_energy_off:
        consumed.add(int(energy_state.id))

    for group in switch_groups.values():
        if {"SWITCH_STATE", "SWITCH_ON", "SWITCH_OFF"}.issubset(group):
            consumed.add(int(group["SWITCH_STATE"].id))

    return consumed


def _switch_group_key(name: str) -> str:
    import re

    normalized = (name or "").strip().lower()
    normalized = re.sub(r"\s+(on|off)$", "", normalized)
    normalized = re.sub(r"[_\-\s]+(on|off)$", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized
