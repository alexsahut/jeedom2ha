"""lock.py — Lock mapper for Jeedom -> Home Assistant (Story 24.9).

Frozen referential (Task 0): ``LOCK_STATE`` (info), ``LOCK_OPEN`` / ``LOCK_CLOSE``
(actions), Jeedom core generic types. ``LOCK_OPEN`` unlocks, ``LOCK_CLOSE`` locks.

Rules (decisions D1 to D4):
- one ``lock`` per equipment: exactly ONE ``LOCK_STATE`` info, at most one
  ``LOCK_OPEN`` and one ``LOCK_CLOSE`` action of sub-type ``other`` (an order carries no
  value), at least one of them (AC3); several states or several actions of the same
  kind: no lock (never guessed which one drives which lock);
- an action whose linked info (Jeedom core « Valeur », ``JeedomCmd.linked_value``)
  points to another command than the ``LOCK_STATE``: no lock;
- polarity of ``LOCK_STATE`` (D1, Homebridge parity, ``LockCurrentState``):
  * general case: true value (``1``, ``true``, ``on``) = locked, false value (``0``,
    ``false``, ``off``) = unlocked;
  * ``nuki`` plugin: ``0`` = locked, ``1`` = unlocked, ``2`` = jammed;
  * ``jeelink`` plugin: Homebridge reads it with the ``nuki`` polarity when it relays a
    ``nuki`` equipment, which the plugin cannot see: polarity not established, no lock;
  * any other value: no state published (``sync.readback.lock_state``);
- never deduced from a name;
- no ``code``, ``optimistic: false``; the plugin never touches the Assist exposure (D4).

The registry runs this mapper before every other one (``MapperRegistry.map_all``): the
lock replaces the previous entities that used one of its commands (the read-only
``binary_sensor`` of class ``lock``, a button on ``LOCK_OPEN`` / ``LOCK_CLOSE``), the
other entities of the equipment stay untouched (D3, Q10 A).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from models.mapping import LockCapabilities, MappingResult
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot

_LOGGER = logging.getLogger(__name__)

LOCK_STATE = "LOCK_STATE"
LOCK_OPEN = "LOCK_OPEN"
LOCK_CLOSE = "LOCK_CLOSE"
LOCK_GENERIC_TYPES = (LOCK_STATE, LOCK_OPEN, LOCK_CLOSE)

# Readback keys of a lock (shared with ``sync.readback.STATE_KEYS``).
LOCK_STATE_KEYS = (LOCK_STATE,)

# ``reason_details["lock_polarity"]`` (D1).
LOCK_POLARITY_STANDARD = "standard"  # true = locked, false = unlocked
LOCK_POLARITY_NUKI = "nuki"          # 0 = locked, 1 = unlocked, 2 = jammed
LOCK_POLARITIES = (LOCK_POLARITY_STANDARD, LOCK_POLARITY_NUKI)

# Plugins whose polarity is the nuki one; plugins whose polarity cannot be established.
_NUKI_PLUGINS = frozenset({"nuki"})
_UNKNOWN_POLARITY_PLUGINS = frozenset({"jeelink"})


def lock_polarity(eq: JeedomEqLogic) -> Optional[str]:
    """Polarity of the ``LOCK_STATE`` of an equipment, from its plugin only (D1).

    None when it cannot be established (``jeelink``): the equipment is not a lock.
    """
    plugin = (eq.eq_type_name or "").strip().lower()
    if plugin in _NUKI_PLUGINS:
        return LOCK_POLARITY_NUKI
    if plugin in _UNKNOWN_POLARITY_PLUGINS:
        return None
    return LOCK_POLARITY_STANDARD


def _is_type(cmd: JeedomCmd, expected: str) -> bool:
    return (cmd.type or "").lower() == expected


def _is_order(cmd: JeedomCmd) -> bool:
    return _is_type(cmd, "action") and (cmd.sub_type or "").lower() == "other"


def _refuse(eq: JeedomEqLogic, why: str, states, opens, closes) -> None:
    _LOGGER.warning(
        "[MAPPING] eq_id=%d: serrure refusée (%s) LOCK_STATE=%s LOCK_OPEN=%s LOCK_CLOSE=%s "
        "→ aucune serrure, projection d'avant gardée",
        eq.id, why, [c.id for c in states], [c.id for c in opens], [c.id for c in closes],
    )


def lock_commands(eq: JeedomEqLogic) -> Optional[Dict[str, JeedomCmd]]:
    """Return the commands of the lock of an equipment, or None if it is not a lock.

    Keys: ``LOCK_STATE`` (always) and ``LOCK_OPEN`` / ``LOCK_CLOSE`` (at least one).
    See the module docstring for the rules.
    """
    states = [c for c in eq.cmds if c.generic_type == LOCK_STATE and _is_type(c, "info")]
    opens = [c for c in eq.cmds if c.generic_type == LOCK_OPEN and _is_order(c)]
    closes = [c for c in eq.cmds if c.generic_type == LOCK_CLOSE and _is_order(c)]
    if not (states or opens or closes):
        return None
    if len(states) != 1:
        # Aucun état (jamais d'état affiché sans retour réel) ou plusieurs états.
        _refuse(eq, "un et un seul état LOCK_STATE attendu", states, opens, closes)
        return None
    if not (opens or closes):
        return None  # AC3 : état seul, la lecture seule d'avant est gardée
    if len(opens) > 1 or len(closes) > 1:
        _refuse(eq, "plusieurs actions de même sens", states, opens, closes)
        return None
    state = states[0]
    actions = [*opens, *closes]
    if any(c.linked_value is not None and c.linked_value != int(state.id) for c in actions):
        _refuse(eq, "lien vers une autre commande", states, opens, closes)
        return None
    if lock_polarity(eq) is None:
        _refuse(eq, f"polarité non établie pour le plugin {eq.eq_type_name}", states, opens, closes)
        return None
    cmds: Dict[str, JeedomCmd] = {LOCK_STATE: state}
    if opens:
        cmds[LOCK_OPEN] = opens[0]
    if closes:
        cmds[LOCK_CLOSE] = closes[0]
    return cmds


class LockMapper:
    """Maps the lock of an eqLogic (LOCK_STATE + LOCK_OPEN / LOCK_CLOSE) to a HA ``lock``."""

    def map_all(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> List[MappingResult]:
        cmds = lock_commands(eq)
        if cmds is None:
            return []
        return [self._map_lock(eq, snapshot, cmds)]

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        mappings = self.map_all(eq, snapshot)
        return mappings[0] if mappings else None

    @staticmethod
    def _map_lock(eq: JeedomEqLogic, snapshot: TopologySnapshot, cmds: Dict[str, JeedomCmd]) -> MappingResult:
        state_cmd = cmds[LOCK_STATE]
        polarity = lock_polarity(eq)
        capabilities = LockCapabilities(
            has_state=True,
            has_command=True,
            has_lock=LOCK_CLOSE in cmds,
            has_unlock=LOCK_OPEN in cmds,
        )
        node_id = f"jeedom2ha_{eq.id}_{state_cmd.id}"
        _LOGGER.info(
            "[MAPPING] eq_id=%d: serrure (LOCK_STATE=%d LOCK_CLOSE=%s LOCK_OPEN=%s, polarité=%s)",
            eq.id, state_cmd.id, getattr(cmds.get(LOCK_CLOSE), "id", None),
            getattr(cmds.get(LOCK_OPEN), "id", None), polarity,
        )
        return MappingResult(
            ha_entity_type="lock",
            confidence="sure",
            reason_code="lock_state_open_close",
            jeedom_eq_id=eq.id,
            ha_unique_id=f"jeedom2ha_eq_{eq.id}_cmd_{state_cmd.id}",
            ha_name=state_cmd.name,
            suggested_area=snapshot.get_suggested_area(eq.id),
            commands=dict(cmds),
            capabilities=capabilities,
            reason_details={
                "lock_polarity": polarity,
                "cmd_id": state_cmd.id,
                "object_id": node_id,
                "node_id": node_id,
                "state_topic": f"jeedom2ha/{eq.id}/{state_cmd.id}/state",
                "command_topic": f"jeedom2ha/{eq.id}/{state_cmd.id}/set",
            },
        )
