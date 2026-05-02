"""registry.py - Ordered registry for Jeedom -> Home Assistant mappers."""

from typing import Iterator, List, Optional

from mapping.cover import CoverMapper
from mapping.fallback import FallbackMapper
from mapping.light import LightMapper
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
        for mapper in self._mappers:
            result = mapper.map(eq, snapshot)
            if result is not None:
                return result
        return None
