"""cover.py — Capability-based cover mapper for Jeedom → Home Assistant.

Story 2.3: Maps Jeedom eqLogics with FLAP_* generic types to HA cover entities.
Capabilities (open/close, stop, position, BSO) are detected independently and
cumulated into a single MappingResult per eqLogic.
"""
import logging
from typing import Dict, Optional, Set

from models.topology import JeedomCmd, JeedomEqLogic, TopologySnapshot
from models.mapping import CoverCapabilities, MappingResult, PublicationDecision

_LOGGER = logging.getLogger(__name__)

# Bounded publication policy — Story 2.3 only.
# "probable" is allowed ONLY for the cover cases explicitly listed in Task 1.3.
COVER_PUBLICATION_POLICY = {
    "sure": True,
    "probable": True,     # bounded to cover cases listed in Task 1.3
    "ambiguous": False,
    "unknown": False,
    "ignore": False,
}

# Confidence ordering for min() calculation (same semantics as LightMapper)
_CONFIDENCE_ORDER = {"sure": 0, "probable": 1, "ambiguous": 2, "unknown": 3, "ignore": 4}

# All recognized FLAP_* generic types
_FLAP_GENERIC_TYPES = {
    "FLAP_STATE", "FLAP_UP", "FLAP_DOWN", "FLAP_STOP", "FLAP_SLIDER",
    "FLAP_BSO_STATE", "FLAP_BSO_UP", "FLAP_BSO_DOWN",
}

# Generic types that strongly imply the equipment is NOT a cover
_ANTI_COVER_GENERIC_TYPES = {
    "LIGHT_STATE", "LIGHT_ON", "LIGHT_OFF", "LIGHT_BRIGHTNESS", "LIGHT_SLIDER",
    "HEATING_STATE", "HEATING_ON", "HEATING_OFF",
    "THERMOSTAT_STATE", "THERMOSTAT_MODE", "THERMOSTAT_SETPOINT",
    "ENERGY_STATE", "ENERGY_ON", "ENERGY_OFF",
    "SIREN_STATE", "SIREN_ON", "SIREN_OFF",
    "LOCK_STATE", "LOCK_OPEN", "LOCK_CLOSE",
}

# Allowed eq.generic_type values for covers
_ALLOWED_EQ_GENERIC_TYPES = {"shutter", "cover", "blind", "flap", ""}

# Sub-type preference table for deduplication (Story 2.6)
# generic_type → preferred sub_type when a duplicate is detected
_COVER_DEDUP_PREFERENCE = {
    "FLAP_STATE": "binary",   # state is an open/close info → binary wins
}

# Keywords in equipment name that strongly imply it's not a cover
_NON_COVER_KEYWORDS = {
    "lumière", "lumiere", "light", "lampe", "ampoule",
    "chauffage", "radiateur", "thermostat", "heater",
    "prise", "plug", "socket",
    "fumée", "smoke", "alarme", "sirene",
}


def _min_confidence(*confidences: str) -> str:
    """Return the worst confidence among the given values.

    Semantic order: 'sure' (best=0) < 'probable' (1) < 'ambiguous' (2) < 'unknown' (3) < 'ignore' (worst=4)
    Uses max() on the order values to select the worst confidence.
    WARNING: do NOT replace max() with min() — that would be a regression.
    """
    return max(confidences, key=lambda c: _CONFIDENCE_ORDER.get(c, 99))


class CoverMapper:
    """Maps Jeedom cover eqLogics (FLAP_*) to HA cover entities.

    The mapping is capability-based and cumulative:
    - Phase 1: Detect open/close capability
    - Phase 2: Detect stop capability
    - Phase 3: Detect position capability
    - Phase 4: Detect BSO (Brise-Soleil Orientable)
    - Phase 5: Compute global confidence = worst(per-capability) via max() on semantic order
    """

    def map(self, eq: JeedomEqLogic, snapshot: TopologySnapshot) -> Optional[MappingResult]:
        """Map a single eqLogic to a cover MappingResult.

        Returns None if the equipment contains no FLAP_* commands.
        """
        # Collect FLAP_* commands and detect ANTI_COVER_* commands
        flap_cmds: Dict[str, JeedomCmd] = {}
        anti_cover_cmds: Set[str] = set()
        _dedup_events: list = []  # resolved dedup metadata (Story 2.6)

        for cmd in eq.cmds:
            if cmd.generic_type and cmd.generic_type in _FLAP_GENERIC_TYPES:
                if cmd.generic_type in flap_cmds:
                    # Duplicate generic_type — attempt deterministic arbitration (Story 2.6)
                    existing = flap_cmds[cmd.generic_type]
                    preferred = _COVER_DEDUP_PREFERENCE.get(cmd.generic_type)

                    if (existing.sub_type != cmd.sub_type
                            and preferred is not None
                            and (existing.sub_type == preferred or cmd.sub_type == preferred)):
                        # Sub-types differ and exactly one matches the preference → resolve
                        winner = cmd if cmd.sub_type == preferred else existing
                        loser = existing if winner is cmd else cmd
                        flap_cmds[cmd.generic_type] = winner
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
                        capabilities = CoverCapabilities()
                        return MappingResult(
                            ha_entity_type="cover",
                            confidence="ambiguous",
                            reason_code="duplicate_generic_types",
                            jeedom_eq_id=eq.id,
                            ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                            ha_name=eq.name,
                            suggested_area=snapshot.get_suggested_area(eq.id),
                            commands=flap_cmds,
                            capabilities=capabilities,
                            reason_details={"duplicate_type": cmd.generic_type},
                        )
                else:
                    flap_cmds[cmd.generic_type] = cmd
            elif cmd.generic_type and cmd.generic_type in _ANTI_COVER_GENERIC_TYPES:
                anti_cover_cmds.add(cmd.generic_type)

        if not flap_cmds:
            return None  # Not a cover

        # GUARDRAILS against false positives
        # 1. Equipment generic type explicitly set to something other than cover-related
        if eq.generic_type and eq.generic_type.lower() not in _ALLOWED_EQ_GENERIC_TYPES:
            _LOGGER.info(
                "[MAPPING] eq_id=%d name='%s': eq.generic_type is '%s' (not cover) → ignore",
                eq.id, eq.name, eq.generic_type,
            )
            return None

        # 2. Conflicting command generic types (Anti-affinity)
        if anti_cover_cmds:
            _LOGGER.info(
                "[MAPPING] eq_id=%d name='%s': conflicting generic types found %s → ambiguous",
                eq.id, eq.name, list(anti_cover_cmds),
            )
            capabilities = CoverCapabilities()
            return MappingResult(
                ha_entity_type="cover",
                confidence="ambiguous",
                reason_code="conflicting_generic_types",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands=flap_cmds,
                capabilities=capabilities,
                reason_details={"conflicting_types": list(anti_cover_cmds)},
            )

        # 3. Name heuristics
        name_lower = eq.name.lower()
        matched_kw = next((kw for kw in _NON_COVER_KEYWORDS if kw in name_lower), None)
        if matched_kw:
            _LOGGER.info(
                "[MAPPING] eq_id=%d name='%s': name contains non-cover keyword '%s' → ambiguous",
                eq.id, eq.name, matched_kw,
            )
            capabilities = CoverCapabilities()
            return MappingResult(
                ha_entity_type="cover",
                confidence="ambiguous",
                reason_code="name_heuristic_rejection",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands=flap_cmds,
                capabilities=capabilities,
                reason_details={"matched_keyword": matched_kw},
            )

        # Phase 1: Detect Open/Close capability
        has_open_close, oc_confidence, oc_reason = self._detect_open_close(flap_cmds)

        # Phase 2: Detect Stop capability
        has_stop = "FLAP_STOP" in flap_cmds

        # Phase 3: Detect Position capability
        has_position, pos_confidence, pos_reason = self._detect_position(flap_cmds)

        # Phase 4: Detect BSO
        is_bso = any(gt.startswith("FLAP_BSO_") for gt in flap_cmds)

        # Check for orphan FLAP_STATE — only state, no action commands
        if not has_open_close and not has_position:
            _LOGGER.info(
                "[MAPPING] eq_id=%d name='%s': FLAP_STATE orphan → ambiguous",
                eq.id, eq.name,
            )
            capabilities = CoverCapabilities()
            return MappingResult(
                ha_entity_type="cover",
                confidence="ambiguous",
                reason_code="state_orphan",
                jeedom_eq_id=eq.id,
                ha_unique_id=f"jeedom2ha_eq_{eq.id}",
                ha_name=eq.name,
                suggested_area=snapshot.get_suggested_area(eq.id),
                commands=flap_cmds,
                capabilities=capabilities,
                reason_details={"available_types": list(flap_cmds.keys())},
            )

        # Build capabilities
        capabilities = CoverCapabilities(
            has_open_close=has_open_close,
            has_stop=has_stop,
            has_position=has_position,
            is_bso=is_bso,
            open_close_confidence=oc_confidence if has_open_close else "unknown",
            position_confidence=pos_confidence if has_position else "unknown",
        )

        # Phase 5: Global confidence = worst(per-capability) via max() on semantic order
        active_confidences = []
        if has_open_close:
            active_confidences.append(oc_confidence)
        if has_position:
            active_confidences.append(pos_confidence)

        global_confidence = _min_confidence(*active_confidences) if active_confidences else "unknown"

        # Apply dedup confidence floor: at least "probable" if any dedup occurred (Story 2.6)
        if _dedup_events:
            global_confidence = _min_confidence(global_confidence, "probable")

        # Build reason code
        parts = []
        if has_open_close:
            parts.append("open_close")
        if has_stop:
            parts.append("stop")
        if has_position:
            parts.append("position")
        if is_bso:
            parts.append("bso")
        reason_code = "cover_" + "_".join(parts) if parts else "cover_unknown"

        # Build reason details
        reason_details = {}
        if oc_reason:
            reason_details["open_close"] = oc_reason
        if pos_reason:
            reason_details["position"] = pos_reason
        # Enrich with dedup metadata (Story 2.6) — last event wins if multiple
        if _dedup_events:
            reason_details.update(_dedup_events[-1])

        _LOGGER.info(
            "[MAPPING] eq_id=%d name='%s': %s confidence=%s (open_close=%s/%s, stop=%s, "
            "position=%s/%s, bso=%s) details=%s",
            eq.id, eq.name, reason_code, global_confidence,
            has_open_close, oc_confidence if has_open_close else "n/a",
            has_stop,
            has_position, pos_confidence if has_position else "n/a",
            is_bso,
            reason_details if reason_details else "{}",
        )

        return MappingResult(
            ha_entity_type="cover",
            confidence=global_confidence,
            reason_code=reason_code,
            jeedom_eq_id=eq.id,
            ha_unique_id=f"jeedom2ha_eq_{eq.id}",
            ha_name=eq.name,
            suggested_area=snapshot.get_suggested_area(eq.id),
            commands=flap_cmds,
            capabilities=capabilities,
            reason_details=reason_details if reason_details else None,
        )

    def decide_publication(self, mapping: MappingResult) -> PublicationDecision:
        """Apply the bounded publication policy for Story 2.3.

        Returns a PublicationDecision indicating whether to publish.
        """
        should_publish = COVER_PUBLICATION_POLICY.get(mapping.confidence, False)

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

    def _detect_open_close(self, cmds: Dict[str, JeedomCmd]) -> tuple:
        """Detect Open/Close capability from FLAP_* commands.

        Returns (has_open_close: bool, confidence: str, reason: str).
        """
        has_state = "FLAP_STATE" in cmds
        has_up = "FLAP_UP" in cmds
        has_down = "FLAP_DOWN" in cmds
        has_slider = "FLAP_SLIDER" in cmds
        has_bso_state = "FLAP_BSO_STATE" in cmds
        has_bso_up = "FLAP_BSO_UP" in cmds
        has_bso_down = "FLAP_BSO_DOWN" in cmds

        # Standard FLAP_UP + FLAP_DOWN + FLAP_STATE → sure
        if has_up and has_down and has_state:
            return True, "sure", "up+down+state"
        # Standard FLAP_UP + FLAP_DOWN (sans FLAP_STATE) → probable
        if has_up and has_down and not has_state:
            return True, "probable", "up+down (missing state)"

        # BSO: FLAP_BSO_UP + FLAP_BSO_DOWN + FLAP_BSO_STATE → sure
        if has_bso_up and has_bso_down and has_bso_state:
            return True, "sure", "bso_up+bso_down+bso_state"
        # BSO: FLAP_BSO_UP + FLAP_BSO_DOWN (sans FLAP_BSO_STATE) → probable
        if has_bso_up and has_bso_down and not has_bso_state:
            return True, "probable", "bso_up+bso_down (missing bso_state)"

        # FLAP_SLIDER seul (sans UP/DOWN) → sure (slider manages open/close via 0/100)
        if has_slider and not has_up and not has_down:
            return True, "sure", "slider_implicit_open_close"

        return False, "unknown", ""

    def _detect_position(self, cmds: Dict[str, JeedomCmd]) -> tuple:
        """Detect Position capability from FLAP_* commands.

        Returns (has_position: bool, confidence: str, reason: str).
        """
        has_slider = "FLAP_SLIDER" in cmds
        has_state = "FLAP_STATE" in cmds

        if not has_slider:
            return False, "unknown", ""

        # FLAP_SLIDER + FLAP_STATE (numeric) → sure
        if has_state:
            state_cmd = cmds["FLAP_STATE"]
            if state_cmd.sub_type == "numeric":
                return True, "sure", "slider+state_numeric"

        # FLAP_SLIDER sans FLAP_STATE numérique → probable
        return True, "probable", "slider_without_numeric_state"
