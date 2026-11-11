"""valve.py — Watering valve / faucet mapper for Jeedom -> Home Assistant (Story 24.8).

Frozen referential (Task 0, Homebridge generic types, none in the Jeedom core):
``IRRIG_STATE/ON/OFF``, ``FAUCET_STATE/ON/OFF``, ``VALVE_STATE/ON/OFF``.
``VALVE_SET_DURATION`` / ``VALVE_REMAINING_DURATION`` are out of scope (AC7): no timer,
no watering program, no flow. No position command exists: ``reports_position: false``.

Rules (decisions D2, D4, D5):
- one complete trio (info STATE + action ON + action OFF of the same family) = one
  ``valve`` entity; an equipment carrying several trios gives one valve per trio (zones);
- trio pairing uses the action's linked info command (Jeedom core "Valeur" of the action,
  exported by the plugin as ``linked_value``, see ``JeedomCmd.linked_value``):
  * a family with ONE STATE, ONE ON and ONE OFF is a valve even without links; but an ON
    or OFF whose link points to another command is refused (no valve);
  * a family with SEVERAL trios needs every ON and OFF linked to a STATE of the family,
    each STATE receiving exactly one ON and one OFF; otherwise the whole family gives no
    valve (never paired by id order: a wrong pairing would drive the wrong zone);
  * different STATE / ON / OFF counts: no valve for the family;
- an incomplete or refused trio gives NO valve (no order is guessed);
- ``device_class: water`` for IRRIG_* and FAUCET_*, none for VALVE_*.

The registry runs this mapper before every other one (``MapperRegistry.map_all``): the
valves replace the previous entities that used one of their commands, the other
entities of the equipment stay untouched.
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

# Readback keys of a valve (shared with ``sync.readback.STATE_KEYS``).
VALVE_STATE_KEYS: Tuple[str, ...] = tuple(f"{family}_STATE" for family in VALVE_FAMILIES)

# ``reason_details["valve_pairing"]``.
VALVE_PAIRING_LINKED = "linked"            # every action linked to its STATE
VALVE_PAIRING_SINGLE_TRIO = "single_trio"  # one trio, at least one action without link

ValveTrio = Tuple[str, Dict[str, JeedomCmd], str]


def _is_type(cmd: JeedomCmd, expected: str) -> bool:
    return (cmd.type or "").lower() == expected


def _sorted_by_id(cmds: List[JeedomCmd]) -> List[JeedomCmd]:
    return sorted(cmds, key=lambda c: int(c.id))


def _ids(cmds: List[JeedomCmd]) -> List[int]:
    return [int(c.id) for c in cmds]


def _refuse(eq: JeedomEqLogic, family: str, why: str, states, ons, offs) -> None:
    _LOGGER.warning(
        "[MAPPING] eq_id=%d: vanne %s refusée (%s) STATE=%s ON=%s OFF=%s "
        "liens ON=%s OFF=%s → aucune vanne pour cette famille",
        eq.id, family, why, _ids(states), _ids(ons), _ids(offs),
        [c.linked_value for c in ons], [c.linked_value for c in offs],
    )


def _family_trios(eq: JeedomEqLogic, family: str) -> List[ValveTrio]:
    state_key, on_key, off_key = f"{family}_STATE", f"{family}_ON", f"{family}_OFF"
    states = _sorted_by_id([c for c in eq.cmds if c.generic_type == state_key and _is_type(c, "info")])
    ons = _sorted_by_id([c for c in eq.cmds if c.generic_type == on_key and _is_type(c, "action")])
    offs = _sorted_by_id([c for c in eq.cmds if c.generic_type == off_key and _is_type(c, "action")])
    if not (states or ons or offs):
        return []
    if not states or not (len(states) == len(ons) == len(offs)):
        _refuse(eq, family, "trio incomplet ou nombres différents", states, ons, offs)
        return []

    if len(states) == 1:
        state, on, off = states[0], ons[0], offs[0]
        if any(c.linked_value is not None and c.linked_value != int(state.id) for c in (on, off)):
            _refuse(eq, family, "lien vers une autre commande", states, ons, offs)
            return []
        pairing = (
            VALVE_PAIRING_LINKED
            if on.linked_value is not None and off.linked_value is not None
            else VALVE_PAIRING_SINGLE_TRIO
        )
        return [(family, {state_key: state, on_key: on, off_key: off}, pairing)]

    # Several trios: every action must be linked to a STATE of the family, one ON and one
    # OFF per STATE. Never paired by id order.
    by_state: Dict[int, Dict[str, List[JeedomCmd]]] = {
        int(s.id): {on_key: [], off_key: []} for s in states
    }
    for key, actions in ((on_key, ons), (off_key, offs)):
        for action in actions:
            if action.linked_value not in by_state:
                _refuse(eq, family, "plusieurs trios et lien absent ou hors famille", states, ons, offs)
                return []
            by_state[action.linked_value][key].append(action)
    if any(len(links[on_key]) != 1 or len(links[off_key]) != 1 for links in by_state.values()):
        _refuse(eq, family, "plusieurs trios et liens non concordants", states, ons, offs)
        return []
    return [
        (family, {state_key: s, on_key: by_state[int(s.id)][on_key][0],
                  off_key: by_state[int(s.id)][off_key][0]}, VALVE_PAIRING_LINKED)
        for s in states
    ]


def valve_trios(eq: JeedomEqLogic) -> List[ValveTrio]:
    """Return the complete valve trios of an equipment, as ``(family, commands, pairing)``.

    ``commands`` maps ``<FAMILY>_STATE`` / ``_ON`` / ``_OFF`` to the Jeedom commands. A
    STATE must be an ``info``, ON/OFF must be ``action`` commands; a command of the wrong
    kind does not count. See the module docstring for the pairing rules.
    """
    trios: List[ValveTrio] = []
    for family in VALVE_FAMILIES:
        trios.extend(_family_trios(eq, family))
    return trios


class ValveMapper:
    """Maps every complete valve trio of an eqLogic to one HA ``valve`` entity."""

    def map_all(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> List[MappingResult]:
        return [
            self._map_trio(eq, snapshot, family, cmds, pairing)
            for family, cmds, pairing in valve_trios(eq)
        ]

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        mappings = self.map_all(eq, snapshot)
        return mappings[0] if mappings else None

    @staticmethod
    def _map_trio(
        eq: JeedomEqLogic,
        snapshot: TopologySnapshot,
        family: str,
        cmds: Dict[str, JeedomCmd],
        pairing: str,
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
            "[MAPPING] eq_id=%d: vanne %s (STATE=%d ON=%d OFF=%d, appariement=%s, device_class=%s)",
            eq.id, family, state_cmd.id, cmds[f"{family}_ON"].id, cmds[f"{family}_OFF"].id,
            pairing, device_class,
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
                "valve_pairing": pairing,
                "cmd_id": state_cmd.id,
                "object_id": node_id,
                "node_id": node_id,
                "state_topic": f"jeedom2ha/{eq.id}/{state_cmd.id}/state",
                "command_topic": f"jeedom2ha/{eq.id}/{state_cmd.id}/set",
            },
        )
