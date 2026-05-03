"""fallback.py - Terminal reserved mapper slot for Jeedom -> Home Assistant.

Story 8.1 wires the slot only. The real fallback projection belongs to
pe-epic-9 Story 9.4.
"""

from typing import Optional

from models.mapping import MappingResult
from models.topology import JeedomEqLogic, TopologySnapshot


class FallbackMapper:
    """Terminal reserved mapper slot. No-op in pe-epic-8."""

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        return None
