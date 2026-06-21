"""registry.py - Ordered registry for Jeedom -> Home Assistant mappers."""

from typing import Iterator, List, Optional

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
from models.topology import JeedomEqLogic, TopologySnapshot


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

        if len(switch_results) > 1 or secondary_count > 1:
            return [*switch_results, *sensor_results, *binary_results]
        return []

    @staticmethod
    def _invoke_mapper(
        mapper: object, eq: JeedomEqLogic, snapshot: TopologySnapshot
    ) -> List[MappingResult]:
        map_all = getattr(mapper, "map_all", None)
        if callable(map_all):
            return list(map_all(eq, snapshot))
        result = mapper.map(eq, snapshot)  # type: ignore[attr-defined]
        return [result] if result is not None else []
