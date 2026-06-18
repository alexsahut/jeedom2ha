"""Jeedom -> HA runtime state synchronization (Story 12.1, vague 1).

Mirror of ``CommandSynchronizer`` for the reverse direction: an inbound Jeedom
info-command value is published on the MQTT ``state_topic`` already declared at
discovery, so published ``sensor`` / ``binary_sensor`` entities stop showing
``unknown`` in Home Assistant.

Strict vague-1 scope: only ``sensor`` and ``binary_sensor`` entities are fed.
Actionable domains (switch/light/cover/climate/alarm_control_panel) are NOT
streamed here — ``is_active`` stays False so ``CommandSynchronizer`` keeps its
existing optimistic behavior unchanged (AC#4, AC#9).
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional, Tuple

from models.mapping import MappingResult, PublicationDecision

_LOGGER = logging.getLogger(__name__)

_VAGUE1_TYPES = ("sensor", "binary_sensor")

# Jeedom binary info values that mean "on". Anything else is "off".
# Matches the HA MQTT binary_sensor defaults (payload_on=ON / payload_off=OFF),
# which the discovery payload does not override (discovery/publisher.py).
_BINARY_TRUE = {"1", "true", "on", "open", "opened"}


class StateSynchronizer:
    """Publish inbound Jeedom info values on the discovery-declared state_topic."""

    def __init__(
        self,
        app: Mapping[str, Any],
        mqtt_bridge: Any,
    ) -> None:
        self._app = app
        self._mqtt_bridge = mqtt_bridge

    @property
    def is_active(self) -> bool:
        """Whether reliable runtime state is provided for ACTIONABLE domains.

        Vague 1 streams ``sensor`` / ``binary_sensor`` only and never vouches for
        light/switch/cover state, so this stays False to preserve
        ``CommandSynchronizer``'s optimistic path (AC#4, AC#9). A later wave that
        streams actionable info commands flips this.
        """
        return False

    async def handle_state_message(self, eq_id: Any, cmd_id: Any, value: Any) -> bool:
        """Resolve the state_topic for one (eq_id, cmd_id) and publish ``value``.

        Returns True when a value was published on a discovery-declared state_topic,
        False otherwise (unknown/unpublished entity, out-of-scope type, no usable
        value, or MQTT unavailable). Never reconstructs a topic by hand and never
        publishes for an entity that was not published in discovery (AC#5).
        """
        try:
            eq_id_int = int(eq_id)
            cmd_id_int = int(cmd_id)
        except (TypeError, ValueError):
            self._log(logging.INFO, eq_id=eq_id, cmd_id=cmd_id,
                      reason_code="invalid_state_identifiers", action="reject_state")
            return False

        if not self._mqtt_bridge or not getattr(self._mqtt_bridge, "is_connected", False):
            self._log(logging.INFO, eq_id=eq_id_int, cmd_id=cmd_id_int,
                      reason_code="mqtt_unavailable", action="reject_state")
            return False

        resolved = self._resolve_state_target(eq_id_int, cmd_id_int)
        if resolved is None:
            self._log(logging.INFO, eq_id=eq_id_int, cmd_id=cmd_id_int,
                      reason_code="state_target_not_found", action="reject_state")
            return False

        mapping, state_topic = resolved

        payload = self._translate_value(mapping, value)
        if payload is None:
            self._log(logging.INFO, eq_id=eq_id_int, cmd_id=cmd_id_int,
                      reason_code="empty_state_value", action="skip_state")
            return False

        ok = self._mqtt_bridge.publish_message(state_topic, payload, qos=1, retain=True)
        if not ok:
            self._log(logging.WARNING, eq_id=eq_id_int, cmd_id=cmd_id_int,
                      reason_code="mqtt_publish_failed", action="publish_state",
                      state_topic=state_topic)
            return False

        self._log(logging.INFO, eq_id=eq_id_int, cmd_id=cmd_id_int,
                  reason_code="state_published", action="publish_state",
                  state_topic=state_topic, ha_type=mapping.ha_entity_type)
        return True

    def list_state_targets(self) -> list:
        """Enumerate the published vague-1 ``(eq_id, cmd_id)`` info commands.

        Authoritative source for the PHP listener registration (Story 12.1, R1):
        only entities whose discovery succeeded are returned, so PHP listens on
        exactly the published set (state ⊆ discovery, AC#5). Each entry carries
        eq_id, cmd_id, ha_type and the discovery-declared state_topic.
        """
        publications = self._app.get("publications", {}) if hasattr(self._app, "get") else {}
        if not isinstance(publications, Mapping):
            return []

        targets: list = []
        seen: set = set()
        for decision in publications.values():
            mapping = getattr(decision, "mapping_result", None)
            if mapping is None or not getattr(decision, "should_publish", False):
                continue
            eq_id = getattr(mapping, "jeedom_eq_id", None)
            if eq_id is None:
                continue
            try:
                eq_id_int = int(eq_id)
            except (TypeError, ValueError):
                continue
            for candidate in self._iter_vague1_candidates(mapping):
                cand_decision = getattr(candidate, "publication_decision_ref", None) or decision
                if not getattr(cand_decision, "discovery_published", False):
                    continue
                cmd_id = self._candidate_cmd_id(candidate)
                if cmd_id is None:
                    continue
                key = (eq_id_int, cmd_id)
                if key in seen:
                    continue
                state_topic = self._candidate_state_topic(candidate, cand_decision, eq_id_int)
                if not state_topic or not str(state_topic).startswith("jeedom2ha/"):
                    continue
                seen.add(key)
                targets.append({
                    "eq_id": eq_id_int,
                    "cmd_id": cmd_id,
                    "ha_type": candidate.ha_entity_type,
                    "state_topic": str(state_topic),
                })
        return targets

    async def publish_initial_states(self, decision: PublicationDecision) -> int:
        """Publish the current Jeedom value (snapshot) for a just-published eqLogic.

        AC#2 — at (re)publication of a vague-1 entity, emit its current known value
        right away instead of waiting for the next change, when one is available.
        AC#5 — only entities whose discovery actually succeeded are fed (gated on each
        candidate's ``publication_decision_ref.discovery_published``). Must run AFTER
        discovery so HA does not drop the state. Returns the count published.
        """
        mapping = getattr(decision, "mapping_result", None)
        if mapping is None:
            return 0
        if not self._mqtt_bridge or not getattr(self._mqtt_bridge, "is_connected", False):
            return 0

        eq_id = getattr(mapping, "jeedom_eq_id", None)
        count = 0
        for candidate in self._iter_vague1_candidates(mapping):
            cand_decision = getattr(candidate, "publication_decision_ref", None) or decision
            if not getattr(cand_decision, "discovery_published", False):
                continue
            state_topic = self._candidate_state_topic(candidate, cand_decision, eq_id)
            if not state_topic or not str(state_topic).startswith("jeedom2ha/"):
                continue
            payload = self._translate_value(candidate, self._candidate_current_value(candidate))
            if payload is None:
                continue
            if self._mqtt_bridge.publish_message(state_topic, payload, qos=1, retain=True):
                count += 1
                self._log(logging.INFO, eq_id=eq_id,
                          cmd_id=self._candidate_cmd_id(candidate),
                          reason_code="initial_state_published", action="publish_snapshot",
                          state_topic=state_topic, ha_type=candidate.ha_entity_type)
        return count

    @staticmethod
    def _candidate_current_value(candidate: MappingResult) -> Any:
        """Read the current Jeedom value carried by the candidate's info command."""
        commands = getattr(candidate, "commands", None) or {}
        for cmd in commands.values():
            return getattr(cmd, "current_value", None)
        return None

    def _resolve_state_target(
        self,
        eq_id: int,
        cmd_id: int,
    ) -> Optional[Tuple[MappingResult, str]]:
        """Find the published vague-1 entity for (eq_id, cmd_id) and its state_topic.

        Reads the topic from the publication registry (``app["publications"]``);
        never rebuilds it (AC#5: state ⊆ discovery). Supports mono-entity
        (``jeedom2ha/{eq}/state``) and multi-sensor (``jeedom2ha/{eq}/{cmd}/state``).
        """
        publications = self._app.get("publications", {}) if hasattr(self._app, "get") else {}
        if not isinstance(publications, Mapping):
            return None

        for decision in publications.values():
            mapping = getattr(decision, "mapping_result", None)
            if mapping is None or getattr(mapping, "jeedom_eq_id", None) != eq_id:
                continue
            if not getattr(decision, "should_publish", False):
                continue

            for candidate in self._iter_vague1_candidates(mapping):
                if self._candidate_cmd_id(candidate) != cmd_id:
                    continue
                cand_decision = getattr(candidate, "publication_decision_ref", None) or decision
                if not getattr(cand_decision, "discovery_published", False):
                    return None
                state_topic = self._candidate_state_topic(candidate, cand_decision, eq_id)
                if not state_topic or not str(state_topic).startswith("jeedom2ha/"):
                    return None
                return candidate, str(state_topic)

        return None

    @staticmethod
    def _iter_vague1_candidates(mapping: MappingResult):
        """Yield the primary mapping plus its secondaries, vague-1 types only."""
        for candidate in [mapping, *(getattr(mapping, "additional_mappings", None) or [])]:
            if getattr(candidate, "ha_entity_type", None) in _VAGUE1_TYPES:
                yield candidate

    @staticmethod
    def _candidate_cmd_id(candidate: MappingResult) -> Optional[int]:
        """Resolve the Jeedom info cmd id a candidate entity is fed from.

        Multi-sensor secondaries carry ``reason_details["cmd_id"]`` (sensor.py);
        mono-entity candidates expose their single info command in ``commands``.
        """
        reason_details = getattr(candidate, "reason_details", None) or {}
        raw = reason_details.get("cmd_id")
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None

        commands = getattr(candidate, "commands", None) or {}
        for cmd in commands.values():
            cmd_id = getattr(cmd, "id", None)
            if cmd_id is not None:
                try:
                    return int(cmd_id)
                except (TypeError, ValueError):
                    continue
        return None

    @staticmethod
    def _candidate_state_topic(
        candidate: MappingResult,
        decision: PublicationDecision,
        eq_id: int,
    ) -> Optional[str]:
        reason_details = getattr(candidate, "reason_details", None) or {}
        topic = reason_details.get("state_topic")
        if topic:
            return topic
        decision_topic = getattr(decision, "state_topic", None)
        if decision_topic:
            return decision_topic
        return f"jeedom2ha/{eq_id}/state"

    def _translate_value(self, mapping: MappingResult, value: Any) -> Optional[str]:
        """Translate a Jeedom info value to the MQTT state payload.

        sensor      -> the raw value as a string (no invention, no rounding).
        binary_sensor -> ON/OFF honoring the discovery payload defaults (AC#6).
        Returns None when there is no usable value (leave HA as-is, never fabricate).
        """
        if value is None:
            return None
        text = str(value).strip()
        if text == "":
            return None

        if mapping.ha_entity_type == "binary_sensor":
            return "ON" if text.lower() in _BINARY_TRUE else "OFF"
        return text

    def _log(self, level: int, eq_id: Any, cmd_id: Any, reason_code: str,
             action: str, **extra: Any) -> None:
        details = " ".join(f"{key}={value}" for key, value in extra.items())
        suffix = f" {details}" if details else ""
        _LOGGER.log(
            level,
            "[SYNC-STATE] eq_id=%s cmd_id=%s reason_code=%s action=%s%s",
            eq_id, cmd_id, reason_code, action, suffix,
        )
