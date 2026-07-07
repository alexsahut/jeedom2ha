"""registry.py - Ordered registry for Jeedom -> Home Assistant mappers."""

from typing import Any, Dict, Iterator, List, Optional

from mapping.alarm_control_panel import AlarmControlPanelMapper
from mapping.binary_sensor import BinarySensorMapper
from mapping.button import ButtonMapper
from mapping.climate import ClimateMapper
from mapping.cover import CoverMapper
from mapping.fallback import FallbackMapper
from mapping.light import LightMapper
from mapping.presence_switch import PresenceSwitchMapper
from mapping.sensor import SensorMapper
from mapping.switch import SwitchMapper
from models.mapping import MappingResult
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot
from validation.ha_component_registry import PRODUCT_SCOPE, validate_projection


class MapperRegistry:
    """Ordered HA mapper registry with a terminal reserved fallback slot."""

    def __init__(self) -> None:
        self._mappers = [
            LightMapper(),
            CoverMapper(),
            SwitchMapper(),
            ClimateMapper(),
            AlarmControlPanelMapper(),
            PresenceSwitchMapper(),
            BinarySensorMapper(),
            SensorMapper(),
            ButtonMapper(),
            FallbackMapper(),
        ]

    @property
    def mappers(self) -> List[object]:
        return list(self._mappers)

    def __iter__(self) -> Iterator[object]:
        return iter(self._mappers)

    def __len__(self) -> int:
        return len(self._mappers)

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        """Mapping principal (back-compat) : premier MappingResult ou None.

        Story 11.1 — les mappings secondaires éventuels (multi-sensor) sont rattachés
        au mapping principal via ``additional_mappings`` pour que les consommateurs
        mono-mapping par eqLogic restent inchangés.
        """
        results = self.map_all(eq, snapshot)
        if not results:
            return None
        primary = results[0]
        if len(results) > 1:
            primary.additional_mappings = results[1:]
        return primary

    def map_all(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> List[MappingResult]:
        """API additive Story 11.1 : retourne tous les mappings du premier mapper
        qui reconnaît l'eqLogic.

        Un mapper peut exposer ``map_all`` (multi-entité) ; sinon on retombe sur son
        ``map`` historique (mono-entité). L'ordre du registry est préservé : on
        s'arrête au premier mapper qui produit au moins un résultat.

        Story 11.3 — exception structurelle : quand les mappers dédiés produisent
        plusieurs entités pour le même eqLogic (multi-switch et/ou multi-domaine),
        on agrège ces résultats au lieu d'utiliser une allowlist d'IDs.
        """
        structural_results = self._map_structural_multi_entity(eq, snapshot)
        if len(structural_results) > 1:
            return structural_results

        for mapper in self._mappers:
            results = self._invoke_mapper(mapper, eq, snapshot)
            if results:
                return results
        return []

    def _map_structural_multi_entity(
        self, eq: JeedomEqLogic, snapshot: TopologySnapshot
    ) -> List[MappingResult]:
        """Agrège les résultats structurellement multi-entités.

        Ordre : switch(es), puis sensors, puis binary_sensors. Les mappers concernés
        garantissent eux-mêmes qu'ils ne passent en mode multi que sur une structure
        riche (pas un simple switch ENERGY_* + une mesure annexe).
        """
        switch_mapper = next(m for m in self._mappers if isinstance(m, SwitchMapper))
        sensor_mapper = next(m for m in self._mappers if isinstance(m, SensorMapper))
        binary_mapper = next(m for m in self._mappers if isinstance(m, BinarySensorMapper))

        switch_results = self._invoke_mapper(switch_mapper, eq, snapshot)
        if not switch_results:
            return []

        sensor_results = self._invoke_mapper(sensor_mapper, eq, snapshot)
        binary_results = self._invoke_mapper(binary_mapper, eq, snapshot)
        secondary_count = len(sensor_results) + len(binary_results)

        if (
            len(switch_results) > 1
            or secondary_count > 1
            or self._has_power_or_energy_sensor(sensor_results)
        ):
            return [*switch_results, *sensor_results, *binary_results]
        return []

    @staticmethod
    def _has_power_or_energy_sensor(results: List[MappingResult]) -> bool:
        for result in results:
            reason_details = result.reason_details or {}
            if reason_details.get("device_class") in {"power", "energy"}:
                return True
        return False

    @staticmethod
    def _invoke_mapper(
        mapper: object, eq: JeedomEqLogic, snapshot: TopologySnapshot
    ) -> List[MappingResult]:
        map_all = getattr(mapper, "map_all", None)
        if callable(map_all):
            return list(map_all(eq, snapshot))
        result = mapper.map(eq, snapshot)  # type: ignore[attr-defined]
        return [result] if result is not None else []


def resolve_expected_ha(
    eq: JeedomEqLogic,
    snapshot: TopologySnapshot,
    cmd: Optional[JeedomCmd] = None,
    *,
    registry: Optional["MapperRegistry"] = None,
) -> Dict[str, Any]:
    """Résout, en LECTURE seule, "l'attendu Home Assistant" pour une commande (AC1, Story 16.2).

    Source de vérité runtime = moteur de mapping (`MapperRegistry`) + registre HA
    (`HA_COMPONENT_REGISTRY` via `validate_projection`) — **PAS** le YAML de planning
    `ha-projection-reference.yaml` (tranché SCP 2026-07-07, Option 1). Aucune table
    dupliquée en dur : les composants compatibles sont dérivés des capabilities réellement
    détectées par le moteur, confrontées au registre HA.

    Retour (structure ouverte à enrichissement 16b — champs label `None` en 16a) :
        {
          "eq_id", "cmd_id", "generic_type",
          "proposed_ha_entity_type": <candidat moteur | None>,   # proposition auto (AC1)
          "compatible_ha_components": [<types PRODUCT_SCOPE validables>],
          "secondary_ha_entity_types": [<types des mappings multi-entités>],
          "label_fr": None, "family_fr": None, "subtype": None,   # remplis en 16b
        }

    - Couvre `FallbackMapper` (le moteur retourne alors son candidat) et le multi-entités
      (`additional_mappings` → `secondary_ha_entity_types`) : l'attendu n'est pas toujours
      1 commande → 1 composant.
    - Si `cmd` n'a pas de `generic_type`, la proposition auto reste calculée au niveau
      eqLogic par le moteur existant (`map()`), conforme à AC1.
    """
    registry = registry or MapperRegistry()
    mapping = registry.map(eq, snapshot)

    if mapping is None:
        proposed: Optional[str] = None
        compatible: List[str] = []
        secondary: List[str] = []
    else:
        proposed = mapping.ha_entity_type
        compatible = [
            ha_type
            for ha_type in PRODUCT_SCOPE
            if validate_projection(ha_type, mapping.capabilities).is_valid
        ]
        secondary = [m.ha_entity_type for m in (mapping.additional_mappings or [])]

    return {
        "eq_id": eq.id,
        "cmd_id": getattr(cmd, "id", None),
        "generic_type": getattr(cmd, "generic_type", None),
        "proposed_ha_entity_type": proposed,
        "compatible_ha_components": compatible,
        "secondary_ha_entity_types": secondary,
        "label_fr": None,
        "family_fr": None,
        "subtype": None,
    }
