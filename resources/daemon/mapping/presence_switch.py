"""presence_switch.py — Mapper Jeedom Présence actionnable → Home Assistant switch.

Story 10.7: détecte la combinaison info PRESENCE + actions SET_ON + SET_OFF
et produit un switch unique. Fallback vers BinarySensorMapper si les actions
sont absentes (retourne None).
"""

from __future__ import annotations

from typing import Dict, Optional

from models.mapping import MappingResult, SwitchCapabilities
from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot


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
        set_on_cmd: Optional[JeedomCmd] = None
        set_off_cmd: Optional[JeedomCmd] = None

        for cmd in eq.cmds:
            gt = cmd.generic_type or ""
            t = (cmd.type or "").lower()
            st = (cmd.sub_type or "").lower()

            if gt == "PRESENCE" and t == "info" and "binary" in st:
                presence_cmd = cmd
            elif gt == "SET_ON" and t == "action":
                set_on_cmd = cmd
            elif gt == "SET_OFF" and t == "action":
                set_off_cmd = cmd

        if presence_cmd is None or set_on_cmd is None or set_off_cmd is None:
            return None

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
