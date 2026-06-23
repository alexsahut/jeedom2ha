"""Jeedom -> HA runtime state synchronization (Story 12.1 vague 1, Story 12.2 vague 2).

Mirror of ``CommandSynchronizer`` for the reverse direction: an inbound Jeedom
info-command value is published on the MQTT ``state_topic`` already declared at
discovery, so published entities stop showing ``unknown`` in Home Assistant.

Streamed scope:
- vague 1 (Story 12.1): ``sensor`` + ``binary_sensor``.
- vague 2 (Story 12.2): adds the actionable ``switch`` (real on/off readback).
  ``button`` is intentionally excluded: it is command-only and declares no
  ``state_topic`` (discovery/publisher.py), so HA never shows it ``unknown`` and
  there is nothing to stream.

``is_active`` reports that a reliable actionable state is streamed, but the
type-scoped ``streams_actionable_type`` is what ``CommandSynchronizer`` must
honor: only ``switch`` flips to real-state confirmation in vague 2, while
``light`` / ``cover`` keep their optimistic path (no false readback — AC#6).
Domains not yet streamed (climate, alarm_control_panel, cover, light) are
governed later waves (FR49).
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional, Tuple

from models.mapping import MappingResult, PublicationDecision

_LOGGER = logging.getLogger(__name__)

_VAGUE1_TYPES = ("sensor", "binary_sensor")
# Vague 2 actionable domains streamed with real readback state. ``button`` is NOT
# here: it is stateless in HA (no state_topic). Later waves extend this set (FR49).
_VAGUE2_ACTIONABLE = ("switch",)
_STREAMED_TYPES = _VAGUE1_TYPES + _VAGUE2_ACTIONABLE

# Readback (info) command keys per actionable type — used to pick the state
# command, NOT the action commands (e.g. switch ENERGY_ON/ENERGY_OFF).
# switch carries two readback shapes: ENERGY_STATE (energy switch) and PRESENCE
# (Story 10.7 presence switch). Both must stream, and the set must stay in sync
# with CommandSynchronizer._has_reliable_state, otherwise a presence switch has
# its optimistic publish suppressed while no real state is ever streamed.
_READBACK_KEYS = {
    "switch": ("ENERGY_STATE", "SWITCH_STATE", "PRESENCE"),
    "light": ("LIGHT_STATE",),
    "cover": ("FLAP_STATE", "FLAP_BSO_STATE"),
}

# Types whose value is translated to ON/OFF (vs raw passthrough for sensor).
_ONOFF_TYPES = ("binary_sensor", "switch")

# Jeedom binary info values that mean "on". Anything else is "off".
# Matches the HA MQTT binary_sensor/switch defaults (payload_on=ON / payload_off=OFF),
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
        """Whether reliable runtime state is streamed for at least one ACTIONABLE domain.

        Vague 2 (Story 12.2) streams ``switch`` real state, so this is True.
        ``CommandSynchronizer`` must still gate per type via
        ``streams_actionable_type`` (light/cover are NOT streamed and keep their
        optimistic path — AC#6, AC#10).
        """
        return bool(_VAGUE2_ACTIONABLE)

    def streams_actionable_type(self, ha_type: Any) -> bool:
        """True only for actionable types this synchronizer actually streams.

        Authoritative scope for ``CommandSynchronizer._has_reliable_state``: a type
        not streamed here must NOT be treated as having reliable runtime state,
        otherwise its optimistic publish would be suppressed while no real state is
        ever produced (regression). Vague 2 = ``switch`` only.
        """
        return ha_type in _VAGUE2_ACTIONABLE

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
        """Enumerate the published streamed ``(eq_id, cmd_id)`` info commands.

        Streamed = sensor/binary_sensor (vague 1) + switch (vague 2). Authoritative
        source for the PHP listener registration (Story 12.1, R1): only entities
        whose discovery succeeded are returned, so PHP listens on exactly the
        published set (state ⊆ discovery). ``button`` is excluded automatically
        (no state_topic). Each entry carries eq_id, cmd_id, ha_type, state_topic.
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
            for candidate in self._iter_streamed_candidates(mapping):
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
        for candidate in self._iter_streamed_candidates(mapping):
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
        """Read the current Jeedom value from the candidate's readback info command.

        Mono sensor/binary_sensor expose a single info command (the value). An
        actionable type (switch) is resolved ONLY via its readback key
        (``ENERGY_STATE``): a switch without readback (``on_off_only``) has no
        runtime state, so this returns None rather than reading an action command.
        """
        commands = getattr(candidate, "commands", None) or {}
        readback_keys = _READBACK_KEYS.get(getattr(candidate, "ha_entity_type", None))
        if readback_keys is not None:
            for key in readback_keys:
                cmd = commands.get(key)
                if cmd is not None:
                    return getattr(cmd, "current_value", None)
            return None
        for cmd in commands.values():
            if str(getattr(cmd, "type", "info")).lower() == "info":
                return getattr(cmd, "current_value", None)
        for cmd in commands.values():
            return getattr(cmd, "current_value", None)
        return None

    def _resolve_state_target(
        self,
        eq_id: int,
        cmd_id: int,
    ) -> Optional[Tuple[MappingResult, str]]:
        """Find the published streamed entity for (eq_id, cmd_id) and its state_topic.

        Reads the topic from the publication registry (``app["publications"]``);
        never rebuilds it (state ⊆ discovery). Supports mono-entity / switch
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

            for candidate in self._iter_streamed_candidates(mapping):
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
    def _iter_streamed_candidates(mapping: MappingResult):
        """Yield the primary mapping plus its secondaries, streamed types only.

        Streamed = vague 1 (sensor/binary_sensor) + vague 2 actionable (switch).
        ``button`` and not-yet-streamed actionable domains are skipped.
        """
        for candidate in [mapping, *(getattr(mapping, "additional_mappings", None) or [])]:
            if getattr(candidate, "ha_entity_type", None) in _STREAMED_TYPES:
                yield candidate

    @staticmethod
    def _coerce_cmd_id(cmd: Any) -> Optional[int]:
        cmd_id = getattr(cmd, "id", None)
        if cmd_id is None:
            return None
        try:
            return int(cmd_id)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _candidate_cmd_id(cls, candidate: MappingResult) -> Optional[int]:
        """Resolve the Jeedom info (readback) cmd id a candidate entity is fed from.

        Order of resolution:
        1. Multi-sensor secondaries carry ``reason_details["cmd_id"]`` (sensor.py).
        2. Actionable types expose several commands: resolve ONLY via the READBACK
           info command (e.g. switch ``ENERGY_STATE``). A switch without readback
           (``on_off_only``) returns None — it must NOT become a state target on an
           action command (ENERGY_ON/OFF carry no runtime state — AC#1).
        3. Otherwise the first ``info``-typed command (mono sensor/binary_sensor).
        4. Fallback: the first command carrying an id.
        """
        reason_details = getattr(candidate, "reason_details", None) or {}
        raw = reason_details.get("cmd_id")
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None

        commands = getattr(candidate, "commands", None) or {}
        readback_keys = _READBACK_KEYS.get(getattr(candidate, "ha_entity_type", None))
        if readback_keys is not None:
            for key in readback_keys:
                cmd_id = cls._coerce_cmd_id(commands.get(key))
                if cmd_id is not None:
                    return cmd_id
            return None

        for cmd in commands.values():
            if str(getattr(cmd, "type", "info")).lower() != "info":
                continue
            cmd_id = cls._coerce_cmd_id(cmd)
            if cmd_id is not None:
                return cmd_id

        for cmd in commands.values():
            cmd_id = cls._coerce_cmd_id(cmd)
            if cmd_id is not None:
                return cmd_id
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

        sensor                 -> the raw value as a string (no invention, no rounding).
        binary_sensor / switch -> ON/OFF honoring the discovery payload defaults
                                  (payload_on=ON / payload_off=OFF — AC#4/AC#6).
        Returns None when there is no usable value (leave HA as-is, never fabricate).
        """
        if value is None:
            return None
        text = str(value).strip()
        if text == "":
            return None

        if mapping.ha_entity_type in _ONOFF_TYPES:
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
