"""switch.py — Capability-based switch mapper for Jeedom → Home Assistant.

Story 2.4: Maps Jeedom eqLogics with ENERGY_* generic types to HA switch entities.
Detects on/off and state capabilities, applies conservative device_class logic,
and applies anti-false-positive guardrails (anti-affinity, name heuristics,
eq.generic_type exclusion).
"""
import logging
from typing import Dict, Optional, Set

from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot
from models.mapping import SwitchCapabilities, MappingResult, PublicationDecision

_LOGGER = logging.getLogger(__name__)

# Bounded publication policy — Story 2.4 only.
# "probable" is allowed ONLY for the switch cases explicitly listed in Task 1.3.
SWITCH_PUBLICATION_POLICY = {
    "sure": True,
    "probable": True,      # bounded to switch cases listed in Task 1.3
    "ambiguous": False,
    "unknown": False,
    "ignore": False,
}

# Confidence ordering for min() calculation (same semantics as LightMapper and CoverMapper)
# WARNING: _min_confidence uses max() on these values — do NOT replace with min().
_CONFIDENCE_ORDER = {"sure": 0, "probable": 1, "ambiguous": 2, "unknown": 3, "ignore": 4}

# All recognized ENERGY_* generic types relevant to switch mapping (excludes POWER, CONSUMPTION)
_SWITCH_GENERIC_TYPES = {
    "ENERGY_STATE",
    "ENERGY_ON",
    "ENERGY_OFF",
}

# Generic types that strongly imply the equipment is NOT a switch
_ANTI_SWITCH_GENERIC_TYPES = {
    # Lumières — symétrique avec LightMapper
    "LIGHT_STATE", "LIGHT_ON", "LIGHT_OFF", "LIGHT_BRIGHTNESS", "LIGHT_SLIDER",
    # Volets
    "FLAP_STATE", "FLAP_UP", "FLAP_DOWN", "FLAP_STOP", "FLAP_SLIDER",
    "FLAP_BSO_STATE", "FLAP_BSO_UP", "FLAP_BSO_DOWN",
    # Chauffage
    "HEATING_STATE", "HEATING_ON", "HEATING_OFF",
    "THERMOSTAT_STATE", "THERMOSTAT_MODE", "THERMOSTAT_SETPOINT",
    # Alarme / serrure
    "SIREN_STATE", "SIREN_ON", "SIREN_OFF",
    "LOCK_STATE", "LOCK_OPEN", "LOCK_CLOSE",
}

# eq.generic_type values that explicitly allow switch mapping
_ALLOWED_EQ_GENERIC_TYPES = {"", "switch", "energy", "plug", "outlet", "prise"}

# Keywords in equipment name that strongly imply it is NOT a switch
_NON_SWITCH_KEYWORDS = {
    "lumière", "lumiere", "light", "lampe", "ampoule",
    "volet", "store", "cover", "blind", "shutter", "portail", "garage",
    "chauffage", "radiateur", "thermostat", "heater",
    "fumée", "smoke", "alarme", "sirene",
}

# eq_type_name substrings that confirm an outlet (prise électrique)
_OUTLET_TYPE_KEYWORDS = {"prise", "energie", "energy", "plug", "outlet"}


def _min_confidence(*confidences: str) -> str:
    """Return the worst confidence among the given values.

    Semantic order: 'sure' (best=0) < 'probable' (1) < 'ambiguous' (2) < 'unknown' (3) < 'ignore' (worst=4)
    Uses max() on the order values to select the worst confidence.
    WARNING: do NOT replace max() with min() — that would be a regression.
    """
    return max(confidences, key=lambda c: _CONFIDENCE_ORDER.get(c, 99))


class SwitchMapper:
    """Maps Jeedom switch eqLogics (ENERGY_*) to HA switch entities.

    The mapping is capability-based:
    - Phase 1: Detect On/Off capability from ENERGY_ON / ENERGY_OFF
    - Phase 2: Determine device_class from eq.eq_type_name (outlet vs None)
    - Phase 3: Global confidence = on_off_confidence
    """

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        """Map a single eqLogic to a switch MappingResult.

        Returns None if the equipment contains no ENERGY_* commands (ENERGY_ON/OFF/STATE).
        """
        # Collect ENERGY_* commands and detect ANTI_SWITCH_* commands
        energy_cmds: Dict[str, JeedomCmd] = {}
        anti_switch_cmds: Set[str] = set()

        for cmd in eq.cmds:
            if cmd.generic_type and cmd.generic_type in _SWITCH_GENERIC_TYPES:
                energy_cmds[cmd.generic_type] = cmd
            elif cmd.generic_type and cmd.generic_type in _ANTI_SWITCH_GENERIC_TYPES:
                anti_switch_cmds.add(cmd.generic_type)

        if not energy_cmds:
            return None  # Not a switch

        # GUARDRAILS against false positives

        # 1. Equipment generic type explicitly set to something other than switch-related
        if eq.generic_type and eq.generic_type.lower() not in _ALLOWED_EQ_GENERIC_TYPES:
            _LOGGER.info(
                "[MAPPING] eq_id=%d name='%s': eq.generic_type is '%s' (not switch) → ignore",
                eq.id, eq.name, eq.generic_type,
            )
            return None

        # 2. Conflicting command generic types (Anti-affinity)
        if anti_switch_cmds:
            _LOGGER.info(
                "[MAPPING] eq_id=%d name='%s': conflicting generic types found %s → ambiguous",
                eq.id, eq.name, list(anti_switch_cmds),
            )
            capabilities = SwitchCapabilities(device_class=None)
            return MappingResult(
                ha_entity_type="switch",
                confidence="ambiguous",
                reason_code="conflicting_generic_types",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands=energy_cmds,
                capabilities=capabilities,
                reason_details={"conflicting_types": list(anti_switch_cmds)},
            )

        # 3. Name heuristics
        name_lower = eq.name.lower()
        matched_kw = next((kw for kw in _NON_SWITCH_KEYWORDS if kw in name_lower), None)
        if matched_kw:
            _LOGGER.info(
                "[MAPPING] eq_id=%d name='%s': name contains non-switch keyword '%s' → ambiguous",
                eq.id, eq.name, matched_kw,
            )
            capabilities = SwitchCapabilities(device_class=None)
            return MappingResult(
                ha_entity_type="switch",
                confidence="ambiguous",
                reason_code="name_heuristic_rejection",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands=energy_cmds,
                capabilities=capabilities,
                reason_details={"matched_keyword": matched_kw},
            )

        # Phase 1: Detect On/Off capability
        has_on = "ENERGY_ON" in energy_cmds
        has_off = "ENERGY_OFF" in energy_cmds
        has_state = "ENERGY_STATE" in energy_cmds

        # Determine on_off_confidence and has_on_off
        if has_on and has_off and has_state:
            has_on_off = True
            on_off_confidence = "sure"
            reason_code_suffix = "on_off_state"
        elif has_on and has_off:
            has_on_off = True
            on_off_confidence = "probable"
            reason_code_suffix = "on_off_only"
        elif has_on and not has_off and not has_state:
            # ENERGY_ON seul
            has_on_off = True
            on_off_confidence = "probable"
            reason_code_suffix = "on_only"
        elif has_off and not has_on and not has_state:
            # ENERGY_OFF seul
            has_on_off = True
            on_off_confidence = "probable"
            reason_code_suffix = "off_only"
        elif has_state and not has_on and not has_off:
            # ENERGY_STATE seul — orphan sensor, not publishable as switch
            _LOGGER.info(
                "[MAPPING] eq_id=%d name='%s': ENERGY_STATE orphan → ambiguous",
                eq.id, eq.name,
            )
            has_on_off = False
            on_off_confidence = "ambiguous"
            reason_code_suffix = "state_orphan"
        else:
            # Unexpected combination (e.g. ON + STATE without OFF)
            has_on_off = True
            on_off_confidence = "probable"
            reason_code_suffix = "partial"

        if not has_on_off or on_off_confidence == "ambiguous":
            capabilities = SwitchCapabilities(
                has_on_off=False,
                has_state=has_state,
                on_off_confidence=on_off_confidence,
                device_class=None,
            )
            return MappingResult(
                ha_entity_type="switch",
                confidence="ambiguous",
                reason_code=f"switch_{reason_code_suffix}",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands=energy_cmds,
                capabilities=capabilities,
                reason_details={"available_types": list(energy_cmds.keys())},
            )

        # Phase 2: device_class — conservative rule based on eq_type_name only
        device_class = self._detect_device_class(eq)

        # Phase 3: Global confidence = on_off_confidence
        global_confidence = on_off_confidence

        reason_code = f"switch_{reason_code_suffix}"

        capabilities = SwitchCapabilities(
            has_on_off=has_on_off,
            has_state=has_state,
            on_off_confidence=on_off_confidence,
            device_class=device_class,
        )

        _LOGGER.info(
            "[MAPPING] eq_id=%d name='%s': %s confidence=%s "
            "(has_on_off=%s/%s, has_state=%s, device_class=%s)",
            eq.id, eq.name, reason_code, global_confidence,
            has_on_off, on_off_confidence,
            has_state,
            device_class,
        )

        return MappingResult(
            ha_entity_type="switch",
            confidence=global_confidence,
            reason_code=reason_code,
            jeedom_eq_id=eq.id,
            ha_unique_id=f"jeedom2ha_eq_{eq.id}",
            ha_name=eq.name,
            suggested_area=snapshot.get_suggested_area(eq.id),
            commands=energy_cmds,
            capabilities=capabilities,
            reason_details={"device_class_source": eq.eq_type_name or ""},
        )

    def decide_publication(self, mapping: MappingResult, confidence_policy: str = "sure_probable") -> PublicationDecision:
        """Apply the bounded publication policy for Story 2.4.

        confidence_policy: "sure_probable" (default) publie sure+probable.
        confidence_policy: "sure_only" bloque probable (Story 4.3).
        Returns a PublicationDecision indicating whether to publish.
        """
        policy = dict(SWITCH_PUBLICATION_POLICY)  # copie locale — ne jamais modifier la constante
        if confidence_policy == "sure_only":
            policy["probable"] = False
        should_publish = policy.get(mapping.confidence, False)

        if should_publish:
            reason = mapping.confidence
        elif mapping.confidence == "ambiguous":
            reason = "ambiguous_skipped"
        else:
            reason = f"{mapping.confidence}_skipped"

        _LOGGER.info(
            "[MAPPING] eq_id=%d publication_decision: should_publish=%s reason=%s confidence=%s",
            mapping.jeedom_eq_id, should_publish, reason, mapping.confidence,
        )

        return PublicationDecision(
            should_publish=should_publish,
            reason=reason,
            mapping_result=mapping,
        )

    # ------------------------------------------------------------------
    # Private detection methods
    # ------------------------------------------------------------------

    def _detect_device_class(self, eq: JeedomEqLogic) -> Optional[str]:
        """Determine device_class based on eq_type_name.

        Rule (conservative and frozen):
        - "outlet" only if eq.eq_type_name.lower() contains one of:
          "prise", "energie", "energy", "plug", "outlet"
        - None in all other cases — including "z2m", "mqtt", "jeelink" (generic plugins)

        > Règle de décision unique : If eq_type_name does not contain an explicit
        > outlet/energy indicator from the list above → device_class = None.
        > No other logic. No exceptions.
        """
        if not eq.eq_type_name:
            return None
        eq_type_lower = eq.eq_type_name.lower()
        for keyword in _OUTLET_TYPE_KEYWORDS:
            if keyword in eq_type_lower:
                _LOGGER.debug(
                    "[MAPPING] eq_id=%d eq_type_name='%s' → device_class='outlet' (keyword='%s')",
                    eq.id, eq.eq_type_name, keyword,
                )
                return "outlet"
        return None
