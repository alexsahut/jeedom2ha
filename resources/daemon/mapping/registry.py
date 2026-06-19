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
from models.topology import MULTI_DOMAIN_EQ_IDS, JeedomEqLogic, TopologySnapshot


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

        Story 11.2 — exception bornée : pour un eqLogic de l'allowlist multi-domaine,
        on AGRÈGE plusieurs domaines (switch + sensor + binary_sensor) au lieu de
        s'arrêter au premier mapper. Le switch reste primaire (back-compat).
        """
        if eq.id in MULTI_DOMAIN_EQ_IDS:
            return self._map_multi_domain(eq, snapshot)

        for mapper in self._mappers:
            results = self._invoke_mapper(mapper, eq, snapshot)
            if results:
                return results
        return []

    def _map_multi_domain(
        self, eq: JeedomEqLogic, snapshot: TopologySnapshot
    ) -> List[MappingResult]:
        """Agrège les domaines d'un eqLogic multi-domaine (allowlist Story 11.2).

        Ordre : switch primaire (identité eqLogic historique préservée), puis
        sensors par commande, puis binary_sensors par commande. Tous rattachés au
        même device Jeedom. Aucun débordement : seuls les IDs de l'allowlist passent ici.
        """
        results: List[MappingResult] = []
        for mapper in self._mappers:
            if isinstance(mapper, (SwitchMapper, SensorMapper, BinarySensorMapper)):
                results.extend(self._invoke_mapper(mapper, eq, snapshot))
        return results

    @staticmethod
    def _invoke_mapper(
        mapper: object, eq: JeedomEqLogic, snapshot: TopologySnapshot
    ) -> List[MappingResult]:
        map_all = getattr(mapper, "map_all", None)
        if callable(map_all):
            return list(map_all(eq, snapshot))
        result = mapper.map(eq, snapshot)  # type: ignore[attr-defined]
        return [result] if result is not None else []
