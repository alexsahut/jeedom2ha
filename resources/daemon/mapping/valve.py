"""valve.py — Watering valve / faucet mapper for Jeedom -> Home Assistant (Story 24.8).

Frozen referential (Task 0, Homebridge generic types, none in the Jeedom core):
``IRRIG_STATE/ON/OFF``, ``FAUCET_STATE/ON/OFF``, ``VALVE_STATE/ON/OFF``.
``VALVE_SET_DURATION`` / ``VALVE_REMAINING_DURATION`` are out of scope (AC7): no timer,
no watering program, no flow. No position command exists: ``reports_position: false``.

Rules (decisions D2, D4, D5):
- one complete trio (info STATE + action ON + action OFF of the same family) = one
  ``valve`` entity; an equipment carrying several trios gives one valve per trio (zones);
- an incomplete trio gives NO valve (no order is guessed): the equipment keeps exactly
  the projection it had before the story;
- trio pairing: Jeedom links an action to its info command through the action's
  ``value`` field, but the topology model (``JeedomCmd``) does not expose it. Pairing is
  therefore done by ascending command id inside each family (n-th STATE with n-th ON and
  n-th OFF). When the three counts differ the pairing is ambiguous and the whole family
  gives no valve (we cannot tell which zone is incomplete);
- ``device_class: water`` for IRRIG_* and FAUCET_*, none for VALVE_*.

The registry runs this mapper before every other one and adds its valves to the
entities the equipment already had (``MapperRegistry.map_all``): the valve is additive.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from models.mapping import MappingResult, ValveCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot

_LOGGER = logging.getLogger(__name__)

# Families in a stable order (also the order of the produced entities).
VALVE_FAMILIES: Tuple[str, ...] = ("IRRIG", "FAUCET", "VALVE")
# D5 — families projected with ``device_class: water``.
WATER_FAMILIES = frozenset({"IRRIG", "FAUCET"})

# Every generic type of a valve trio (readback keys are the *_STATE ones).
VALVE_STATE_KEYS: Tuple[str, ...] = tuple(f"{family}_STATE" for family in VALVE_FAMILIES)
VALVE_ON_KEYS: Tuple[str, ...] = tuple(f"{family}_ON" for family in VALVE_FAMILIES)
VALVE_OFF_KEYS: Tuple[str, ...] = tuple(f"{family}_OFF" for family in VALVE_FAMILIES)

VALVE_PAIRING_BY_ID_ORDER = "id_order"


def _is_type(cmd: JeedomCmd, expected: str) -> bool:
    return (cmd.type or "").lower() == expected


def _sorted_by_id(cmds: List[JeedomCmd]) -> List[JeedomCmd]:
    return sorted(cmds, key=lambda c: int(c.id))


def valve_trios(eq: JeedomEqLogic) -> List[Tuple[str, Dict[str, JeedomCmd]]]:
    """Return the complete valve trios of an equipment, as ``(family, commands)``.

    ``commands`` maps ``<FAMILY>_STATE`` / ``_ON`` / ``_OFF`` to the Jeedom commands.
    A STATE must be an ``info``, ON/OFF must be ``action`` commands; a command of the
    wrong kind does not count. A family whose STATE / ON / OFF counts differ gives no
    trio at all (ambiguous pairing, nothing guessed).
    """
    trios: List[Tuple[str, Dict[str, JeedomCmd]]] = []
    for family in VALVE_FAMILIES:
        state_key, on_key, off_key = f"{family}_STATE", f"{family}_ON", f"{family}_OFF"
        states = _sorted_by_id([c for c in eq.cmds if c.generic_type == state_key and _is_type(c, "info")])
        ons = _sorted_by_id([c for c in eq.cmds if c.generic_type == on_key and _is_type(c, "action")])
        offs = _sorted_by_id([c for c in eq.cmds if c.generic_type == off_key and _is_type(c, "action")])
        if not (states or ons or offs):
            continue
        if not (len(states) == len(ons) == len(offs)):
            _LOGGER.info(
                "[MAPPING] eq_id=%d: trio de vanne %s incomplet ou ambigu "
                "(STATE=%d ON=%d OFF=%d) → aucune vanne publiée pour cette famille",
                eq.id, family, len(states), len(ons), len(offs),
            )
            continue
        for state_cmd, on_cmd, off_cmd in zip(states, ons, offs):
            trios.append((family, {state_key: state_cmd, on_key: on_cmd, off_key: off_cmd}))
    return trios


class ValveMapper:
    """Maps every complete valve trio of an eqLogic to one HA ``valve`` entity."""

    def map_all(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> List[MappingResult]:
        return [self._map_trio(eq, snapshot, family, cmds) for family, cmds in valve_trios(eq)]

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        mappings = self.map_all(eq, snapshot)
        return mappings[0] if mappings else None

    @staticmethod
    def _map_trio(
        eq: JeedomEqLogic,
        snapshot: TopologySnapshot,
        family: str,
        cmds: Dict[str, JeedomCmd],
    ) -> MappingResult:
        state_cmd = cmds[f"{family}_STATE"]
        device_class = "water" if family in WATER_FAMILIES else None
        capabilities = ValveCapabilities(
            has_open_close=True,
            has_state=True,
            has_position=False,
            device_class=device_class,
        )
        node_id = f"jeedom2ha_{eq.id}_{state_cmd.id}"
        _LOGGER.info(
            "[MAPPING] eq_id=%d: vanne %s (STATE=%d ON=%d OFF=%d, device_class=%s)",
            eq.id, family, state_cmd.id, cmds[f"{family}_ON"].id, cmds[f"{family}_OFF"].id,
            device_class,
        )
        return MappingResult(
            ha_entity_type="valve",
            confidence="sure",
            reason_code=f"valve_{family.lower()}_open_close_state",
            jeedom_eq_id=eq.id,
            ha_unique_id=f"jeedom2ha_eq_{eq.id}_cmd_{state_cmd.id}",
            ha_name=state_cmd.name,
            suggested_area=snapshot.get_suggested_area(eq.id),
            commands=dict(cmds),
            capabilities=capabilities,
            reason_details={
                "valve_family": family,
                "valve_pairing": VALVE_PAIRING_BY_ID_ORDER,
                "cmd_id": state_cmd.id,
                "object_id": node_id,
                "node_id": node_id,
                "state_topic": f"jeedom2ha/{eq.id}/{state_cmd.id}/state",
                "command_topic": f"jeedom2ha/{eq.id}/{state_cmd.id}/set",
            },
        )
