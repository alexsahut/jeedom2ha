"""presence_switch.py — Mapper Jeedom Présence actionnable → Home Assistant switch.

Story 10.7: détecte la combinaison info PRESENCE + actions SET_ON + SET_OFF
et produit un switch unique. Fallback vers BinarySensorMapper si les actions
sont absentes (retourne None).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from mapping.pairing import PAIRING_AMBIGUOUS, SWITCH_PAIRING_AMBIGUOUS, pair_on_off
from models.mapping import MappingResult, SwitchCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot

_LOGGER = logging.getLogger(__name__)


class PresenceSwitchMapper:
    """Mappe un eqLogic Jeedom PRESENCE actionnable en HA switch.

    Critères d'activation (les trois doivent être réunis) :
    1. Commande info binary de generic_type PRESENCE
    2. Commande action de generic_type SET_ON
    3. Commande action de generic_type SET_OFF

    Retourne None si l'une des trois conditions manque, laissant
    BinarySensorMapper prendre le relais pour les PRESENCE lecture seule.
    """

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        presence_cmd: Optional[JeedomCmd] = None
        # fix/switch-appariement-etat — toutes les actions de chaque sens, dans l'ordre Jeedom.
        set_on_cmds: List[JeedomCmd] = []
        set_off_cmds: List[JeedomCmd] = []

        for cmd in eq.cmds:
            gt = cmd.generic_type or ""
            t = (cmd.type or "").lower()
            st = (cmd.sub_type or "").lower()

            if gt == "PRESENCE" and t == "info" and "binary" in st:
                presence_cmd = cmd
            elif gt == "SET_ON" and t == "action":
                set_on_cmds.append(cmd)
            elif gt == "SET_OFF" and t == "action":
                set_off_cmds.append(cmd)

        if presence_cmd is None or not set_on_cmds or not set_off_cmds:
            return None

        # fix/switch-appariement-etat — une seule paire : comportement d'avant ; plusieurs : la paire
        # reliée à l'info PRESENCE, sinon pas de switch (raison dédiée, jamais pilotable).
        pairing = pair_on_off(set_on_cmds, set_off_cmds, presence_cmd, on_key="SET_ON", off_key="SET_OFF")
        if pairing.status == PAIRING_AMBIGUOUS:
            _LOGGER.warning(
                "[MAPPING] eq_id=%d: plusieurs ordres SET_ON/SET_OFF et aucun relié de façon univoque à "
                "la présence %s (candidats %s) → pas de switch (%s)",
                eq.id, presence_cmd.id, pairing.candidates, SWITCH_PAIRING_AMBIGUOUS,
            )
            commands = {"PRESENCE": presence_cmd}
            for cmd in [*set_on_cmds, *set_off_cmds]:
                commands[f"{cmd.generic_type}#{cmd.id}"] = cmd
            return MappingResult(
                ha_entity_type="switch",
                confidence="ambiguous",
                reason_code=SWITCH_PAIRING_AMBIGUOUS,
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands=commands,
                capabilities=SwitchCapabilities(
                    has_on_off=False, has_state=True, on_off_confidence="ambiguous", device_class=None,
                ),
                reason_details={"pairing_candidates": pairing.candidates, "state_cmd_id": presence_cmd.id},
            )
        set_on_cmd, set_off_cmd = pairing.on, pairing.off

        return MappingResult(
            ha_entity_type="switch",
            confidence="sure",
            reason_code="presence_switch_set_on_off",
            jeedom_eq_id=eq.id,
            ha_unique_id=f"jeedom2ha_eq_{eq.id}",
            ha_name=eq.name,
            suggested_area=snapshot.get_suggested_area(eq.id),
            commands={
                "PRESENCE": presence_cmd,
                "SET_ON": set_on_cmd,
                "SET_OFF": set_off_cmd,
            },
            capabilities=SwitchCapabilities(
                has_on_off=True,
                has_state=True,
                on_off_confidence="sure",
                device_class=None,
            ),
            reason_details={},
        )
