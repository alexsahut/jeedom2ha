"""light.py — Capability-based light mapper for Jeedom → Home Assistant.

Story 2.2: Maps Jeedom eqLogics with LIGHT_* generic types to HA light entities.
Capabilities (on/off, brightness) are detected independently and cumulated into
a single MappingResult per eqLogic.
"""
import logging
from typing import Dict, Optional

from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot
from models.mapping import LightCapabilities, MappingResult, PublicationDecision

_LOGGER = logging.getLogger(__name__)

# Bounded publication policy — Story 2.2 only.
# "probable" is allowed ONLY for the light cases explicitly listed in Task 1.4.
# Do NOT extrapolate this policy to Stories 2.3+.
LIGHT_PUBLICATION_POLICY = {
    "sure": True,
    "probable": True,     # bounded to light cases listed in Task 1.4
    "ambiguous": False,
    "unknown": False,
    "ignore": False,
}

# Confidence ordering for min() calculation
_CONFIDENCE_ORDER = {"sure": 0, "probable": 1, "ambiguous": 2, "unknown": 3, "ignore": 4}

# LIGHT_* generic types that are V1-unsupported (color)
_COLOR_GENERIC_TYPES = {"LIGHT_SET_COLOR", "LIGHT_COLOR", "LIGHT_COLOR_TEMP"}

# All recognized LIGHT_* generic types
_LIGHT_GENERIC_TYPES = {
    "LIGHT_STATE", "LIGHT_ON", "LIGHT_OFF",
    "LIGHT_BRIGHTNESS", "LIGHT_SLIDER",
    "LIGHT_SET_COLOR", "LIGHT_COLOR", "LIGHT_COLOR_TEMP",
}

# Generic types that strongly imply the equipment is NOT primarily a light
# (Heaters, Covers, Plugs, Sensors, Sirens)
_ANTI_LIGHT_GENERIC_TYPES = {
    "HEATING_STATE", "HEATING_ON", "HEATING_OFF", "HEATING_OTHER",
    "THERMOSTAT_STATE", "THERMOSTAT_MODE", "THERMOSTAT_SETPOINT",
    "WATER_HEATER_STATE", "WATER_HEATER_ON", "WATER_HEATER_OFF",
    "FLAP_STATE", "FLAP_UP", "FLAP_DOWN", "FLAP_STOP", "FLAP_SLIDER",
    "ENERGY_STATE", "ENERGY_ON", "ENERGY_OFF", "ENERGY_POWER", "POWER", "CONSUMPTION",
    "SMOKE", "MOTION", "PRESENCE", "OPENING", "OPENING_WINDOW", "OPENING_DOOR",
    "SIREN_STATE", "SIREN_ON", "SIREN_OFF",
    "ALARM_STATE", "ALARM_ENABLE", "ALARM_DISABLE",
    "LOCK_STATE", "LOCK_OPEN", "LOCK_CLOSE",
}

# Sub-type preference table for deduplication (Story 2.6)
# generic_type → preferred sub_type when a duplicate is detected
_LIGHT_DEDUP_PREFERENCE = {
    "LIGHT_STATE": "binary",      # state is an on/off info → binary wins
    "LIGHT_BRIGHTNESS": "numeric",  # brightness is a numeric info → numeric wins
}

# Keywords in equipment name that strongly imply it's not a light
_NON_LIGHT_KEYWORDS = {
    # Chauffage
    "chauffage", "radiateur", "thermostat", "heater", "chaudiere", "chaudière", "poele", "poêle",
    # Eau / Chauffe-eau
    "chauffe-eau", "eau", "water", "cumulus", "ballon",
    # Piscine
    "piscine", "pool", "filtration", "filtre", "pompe",
    # Prises (relays often using LIGHT_ON/OFF)
    "prise", "plug", "socket", 
    # Sécurité
    "fumée", "smoke", "incendie", "feu", "fire", "alarme", "sirene", "sirène",
    # Volets
    "volet", "store", "cover", "blind", "shutter", "garage", "portail",
}


def _min_confidence(*confidences: str) -> str:
    """Return the worst confidence among the given values.

    Semantic order: 'sure' (best=0) < 'probable' (1) < 'ambiguous' (2) < 'unknown' (3) < 'ignore' (worst=4)
    Uses max() on the order values to select the worst confidence.
    Example: _min_confidence('sure', 'probable') -> 'probable'  (NOT 'sure')
    WARNING: do NOT replace max() with min() — that would be a regression.
    """
    return max(confidences, key=lambda c: _CONFIDENCE_ORDER.get(c, 99))


class LightMapper:
    """Maps Jeedom light eqLogics to HA light entities.

    The mapping is capability-based and cumulative:
    - Phase 1: Detect on/off capability
    - Phase 2: Detect brightness capability
    - Phase 3: Compute global confidence = worst(per-capability confidences)
             = max() on semantic order values (sure=0 < probable=1 < ambiguous=2)
    """

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        """Map a single eqLogic to a light MappingResult.

        Returns None if the equipment contains no LIGHT_* commands.
        """
        # Collect LIGHT_* commands and detect ANTI_LIGHT_* commands
        light_cmds: Dict[str, JeedomCmd] = {}
        anti_light_cmds = set()
        _dedup_events: list = []  # resolved dedup metadata (Story 2.6)

        for cmd in eq.cmds:
            if cmd.generic_type and cmd.generic_type in _LIGHT_GENERIC_TYPES:
                if cmd.generic_type in light_cmds:
                    # Duplicate generic_type — attempt deterministic arbitration (Story 2.6)
                    existing = light_cmds[cmd.generic_type]
                    preferred = _LIGHT_DEDUP_PREFERENCE.get(cmd.generic_type)

                    if (existing.sub_type != cmd.sub_type
                            and preferred is not None
                            and (existing.sub_type == preferred or cmd.sub_type == preferred)):
                        # Sub-types differ and exactly one matches the preference → resolve
                        winner = cmd if cmd.sub_type == preferred else existing
                        loser = existing if winner is cmd else cmd
                        light_cmds[cmd.generic_type] = winner
                        _dedup_events.append({
                            "deduplicated": True,
                            "duplicate_type": cmd.generic_type,
                            "kept_cmd_id": winner.id,
                            "discarded_cmd_id": loser.id,
                            "criterion": "sub_type",
                        })
                        _LOGGER.info(
                            "[MAPPING] eq_id=%d: deduplicated %s "
                            "(kept cmd %d sub_type=%s, discarded cmd %d sub_type=%s)",
                            eq.id, cmd.generic_type,
                            winner.id, winner.sub_type,
                            loser.id, loser.sub_type,
                        )
                    else:
                        # Same sub_type, no rule, or neither matches preference → conservative: ambiguous
                        _LOGGER.warning(
                            "[MAPPING] eq_id=%d name='%s': duplicate command for generic_type '%s' "
                            "(cmd1=%s, cmd2=%s) → ambiguous",
                            eq.id, eq.name, cmd.generic_type,
                            existing.id, cmd.id,
                        )
                        capabilities = LightCapabilities()
                        return MappingResult(
                            ha_entity_type="light",
                            confidence="ambiguous",
                            reason_code="duplicate_generic_types",
                            jeedom_eq_id=eq.id,
                            ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                            ha_name=eq.name,
                            suggested_area=snapshot.get_suggested_area(eq.id),
                            commands=light_cmds,
                            capabilities=capabilities,
                            reason_details={"duplicate_type": cmd.generic_type},
                        )
                else:
                    light_cmds[cmd.generic_type] = cmd
            elif cmd.generic_type and cmd.generic_type in _ANTI_LIGHT_GENERIC_TYPES:
                anti_light_cmds.add(cmd.generic_type)

        if not light_cmds:
            return None  # Not a light
            
        # GUARDRAILS against false positives (Story 2.2 hardened)
        # 1. Equipment generic type explicitly set to something else (if provided by Jeedom v4)
        if eq.generic_type and eq.generic_type.lower() not in ("light", ""):
            _LOGGER.info(
                "[MAPPING] eq_id=%d name='%s': eq.generic_type is '%s' (not light) → ignore",
                eq.id, eq.name, eq.generic_type
            )
            return None

        # 2. Conflicting command generic types (Anti-affinity)
        if anti_light_cmds:
            _LOGGER.info(
                "[MAPPING] eq_id=%d name='%s': conflicting generic types found %s → ambiguous",
                eq.id, eq.name, list(anti_light_cmds)
            )
            capabilities = LightCapabilities()
            return MappingResult(
                ha_entity_type="light",
                confidence="ambiguous",
                reason_code="conflicting_generic_types",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands=light_cmds,
                capabilities=capabilities,
                reason_details={"conflicting_types": list(anti_light_cmds)},
            )
            
        # 3. Name heuristics (Detecting plugs, heaters, pumps misconfigured as lights)
        name_lower = eq.name.lower()
        matched_kw = next((kw for kw in _NON_LIGHT_KEYWORDS if kw in name_lower), None)
        if matched_kw:
            _LOGGER.info(
                "[MAPPING] eq_id=%d name='%s': name contains non-light keyword '%s' → ambiguous",
                eq.id, eq.name, matched_kw
            )
            capabilities = LightCapabilities()
            return MappingResult(
                ha_entity_type="light",
                confidence="ambiguous",
                reason_code="name_heuristic_rejection",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands=light_cmds,
                capabilities=capabilities,
                reason_details={"matched_keyword": matched_kw},
            )

        # Check if ONLY color commands exist (V1 unsupported)
        non_color_cmds = {gt for gt in light_cmds if gt not in _COLOR_GENERIC_TYPES}
        only_color = len(non_color_cmds) == 0

        if only_color:
            _LOGGER.info(
                "[MAPPING] eq_id=%d name='%s': only color commands found → ambiguous (V1 unsupported)",
                eq.id, eq.name,
            )
            capabilities = LightCapabilities()
            return MappingResult(
                ha_entity_type="light",
                confidence="ambiguous",
                reason_code="color_only_unsupported",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands=light_cmds,
                capabilities=capabilities,
                reason_details={"color_types": list(light_cmds.keys())},
            )

        # Phase 1: Detect On/Off capability
        has_on_off, on_off_confidence, on_off_reason = self._detect_on_off(light_cmds)

        # Phase 2: Detect Brightness capability
        has_brightness, brightness_confidence, brightness_reason = self._detect_brightness(light_cmds)

        # Check for orphan LIGHT_STATE — only state, no action commands
        if not has_on_off and not has_brightness:
            _LOGGER.info(
                "[MAPPING] eq_id=%d name='%s': LIGHT_STATE orphan → ambiguous",
                eq.id, eq.name,
            )
            capabilities = LightCapabilities()
            return MappingResult(
                ha_entity_type="light",
                confidence="ambiguous",
                reason_code="state_orphan",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands=light_cmds,
                capabilities=capabilities,
                reason_details={"available_types": list(light_cmds.keys())},
            )

        # Build capabilities
        capabilities = LightCapabilities(
            has_on_off=has_on_off,
            has_brightness=has_brightness,
            on_off_confidence=on_off_confidence if has_on_off else "unknown",
            brightness_confidence=brightness_confidence if has_brightness else "unknown",
        )

        # Phase 3: Global confidence = worst(per-capability) via max() on semantic order
        active_confidences = []
        if has_on_off:
            active_confidences.append(on_off_confidence)
        if has_brightness:
            active_confidences.append(brightness_confidence)

        global_confidence = _min_confidence(*active_confidences) if active_confidences else "unknown"

        # Apply dedup confidence floor: at least "probable" if any dedup occurred (Story 2.6)
        if _dedup_events:
            global_confidence = _min_confidence(global_confidence, "probable")

        # Build reason code
        if has_on_off and has_brightness:
            reason_code = "light_on_off_brightness"
        elif has_on_off:
            reason_code = "light_on_off_only"
        else:
            reason_code = "light_brightness_only"

        # Build reason details
        reason_details = {}
        if on_off_reason:
            reason_details["on_off"] = on_off_reason
        if brightness_reason:
            reason_details["brightness"] = brightness_reason
        # Enrich with dedup metadata (Story 2.6) — last event wins if multiple
        if _dedup_events:
            reason_details.update(_dedup_events[-1])

        _LOGGER.info(
            "[MAPPING] eq_id=%d name='%s': %s confidence=%s (on_off=%s/%s, brightness=%s/%s)",
            eq.id, eq.name, reason_code, global_confidence,
            has_on_off, on_off_confidence if has_on_off else "n/a",
            has_brightness, brightness_confidence if has_brightness else "n/a",
        )

        return MappingResult(
            ha_entity_type="light",
            confidence=global_confidence,
            reason_code=reason_code,
            jeedom_eq_id=eq.id,
            ha_unique_id=f"jeedom2ha_eq_{eq.id}",
            ha_name=eq.name,
            suggested_area=snapshot.get_suggested_area(eq.id),
            commands=light_cmds,
            capabilities=capabilities,
            reason_details=reason_details if reason_details else None,
        )

    def decide_publication(self, mapping: MappingResult) -> PublicationDecision:
        """Apply the bounded publication policy for Story 2.2.

        Returns a PublicationDecision indicating whether to publish.
        """
        should_publish = LIGHT_PUBLICATION_POLICY.get(mapping.confidence, False)

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

    def _detect_on_off(self, cmds: Dict[str, JeedomCmd]) -> tuple:
        """Detect On/Off capability from LIGHT_* commands.

        Returns (has_on_off: bool, confidence: str, reason: str).
        """
        has_state = "LIGHT_STATE" in cmds
        has_on = "LIGHT_ON" in cmds
        has_off = "LIGHT_OFF" in cmds
        has_slider = "LIGHT_SLIDER" in cmds

        if has_state and has_on and has_off:
            return True, "sure", "state+on+off"
        if has_state and has_on and not has_off:
            return True, "probable", "state+on (missing off)"
        if has_state and has_off and not has_on:
            return True, "probable", "state+off (missing on)"
        # Slider implies on/off via value 0
        if has_slider and not has_state and not has_on and not has_off:
            return True, "sure", "slider_implicit_on_off"
        if has_slider and has_state:
            # State + slider without explicit on/off: slider provides on/off
            return True, "sure", "slider_implicit_on_off"

        return False, "unknown", ""

    def _detect_brightness(self, cmds: Dict[str, JeedomCmd]) -> tuple:
        """Detect Brightness capability from LIGHT_* commands.

        Returns (has_brightness: bool, confidence: str, reason: str).
        """
        has_brightness_info = "LIGHT_BRIGHTNESS" in cmds
        has_slider = "LIGHT_SLIDER" in cmds
        has_state = "LIGHT_STATE" in cmds

        if has_brightness_info and has_slider:
            return True, "sure", "brightness_info+slider"
        if has_slider and not has_brightness_info:
            return True, "probable", "slider_without_brightness_info"

        # Fallback: LIGHT_STATE numeric as brightness source
        if has_state and not has_slider:
            state_cmd = cmds["LIGHT_STATE"]
            if state_cmd.sub_type == "numeric":
                return True, "probable", "state_numeric_as_brightness"

        return False, "unknown", ""
