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

- vague 3 (Story 23.3): adds ``light`` (ON/OFF + brightness) and ``cover``
  (open/closed + position). One entity can be fed by several Jeedom commands
  (light: ``LIGHT_STATE`` + ``LIGHT_BRIGHTNESS``) and one command can feed several
  topics (numeric ``FLAP_STATE`` -> ``state`` + ``position``). Which command feeds
  which topic is defined once in ``sync.readback`` and shared with discovery
  (``optimistic``) and ``CommandSynchronizer``.

``is_active`` reports that a reliable actionable state is streamed, but the
type-scoped ``streams_actionable_type`` is what ``CommandSynchronizer`` must
honor: a streamed type flips to real-state confirmation only when the entity has
a real readback info command (reliability is evaluated per channel); otherwise it
keeps its optimistic / stateless path (no false readback — AC#6).
Domains not yet streamed (climate, alarm_control_panel) are governed later waves
(FR49).
"""

from __future__ import annotations

import logging
import time
import math
import re
from typing import Any, Dict, List, Mapping, NamedTuple, Optional, Set, Tuple

from models.mapping import MappingResult, PublicationDecision
from sync.readback import (
    BRIGHTNESS_KEYS,
    CHANNEL_BRIGHTNESS,
    CHANNEL_POSITION,
    CHANNEL_STATE,
    STATE_KEYS,
    channel_topic,
    readback_commands,
)

_LOGGER = logging.getLogger(__name__)

_VAGUE1_TYPES = ("sensor", "binary_sensor")
# Vague 2 actionable domains streamed with real readback state. ``button`` is NOT
# here: it is stateless in HA (no state_topic). Later waves extend this set (FR49).
_VAGUE2_ACTIONABLE = ("switch",)
# Vague 3 (Story 23.3): light + cover real state (ON/OFF, brightness, open/closed, position).
_VAGUE3_ACTIONABLE = ("light", "cover")
_ACTIONABLE_STREAMED = _VAGUE2_ACTIONABLE + _VAGUE3_ACTIONABLE
_STREAMED_TYPES = _VAGUE1_TYPES + _ACTIONABLE_STREAMED

# Readback (info) command keys per actionable type — used to pick the state
# command, NOT the action commands (e.g. switch ENERGY_ON/ENERGY_OFF).
# switch carries two readback shapes: ENERGY_STATE (energy switch) and PRESENCE
# (Story 10.7 presence switch). Both must stream, and the set must stay in sync
# with CommandSynchronizer._has_reliable_state, otherwise a presence switch has
# its optimistic publish suppressed while no real state is ever streamed.
# Story 23.3: derived from ``sync.readback`` (single source shared with discovery and
# CommandSynchronizer); ``light`` also lists its brightness info command.
_READBACK_KEYS = {
    "switch": STATE_KEYS["switch"],
    "light": STATE_KEYS["light"] + BRIGHTNESS_KEYS,
    "cover": STATE_KEYS["cover"],
}

# Strict shape of the retained channel topics this module may empty (never anything else).
_CHANNEL_TOPIC_RE = re.compile(r"jeedom2ha/\d+/(?:state|brightness|position)")

# Retained channel topics a type may have published; purged when the channel loses its
# readback (Story 23.3, Q7).
_PURGEABLE_CHANNELS = {
    "light": (CHANNEL_STATE, CHANNEL_BRIGHTNESS),
    "cover": (CHANNEL_STATE, CHANNEL_POSITION),
}

# Types whose value is translated to ON/OFF (vs raw passthrough for sensor).
_ONOFF_TYPES = ("binary_sensor", "switch")

# Jeedom binary info values that mean "on". Anything else is "off".
# Matches the HA MQTT binary_sensor/switch defaults (payload_on=ON / payload_off=OFF),
# which the discovery payload does not override (discovery/publisher.py).
_BINARY_TRUE = {"1", "true", "on", "open", "opened"}
# Explicit "off" values for a cover state: anything unrecognised publishes nothing
# (no value invented).
_BINARY_FALSE = {"0", "false", "off", "closed", "close"}


class _Binding(NamedTuple):
    """One ``Jeedom info command -> MQTT topic`` feed of a streamed candidate."""

    channel: str
    cmd: Any
    cmd_id: Optional[int]
    topic: str
    current_value: Any


class StateSynchronizer:
    """Publish inbound Jeedom info values on the discovery-declared state_topic."""

    def __init__(
        self,
        app: Mapping[str, Any],
        mqtt_bridge: Any,
    ) -> None:
        self._app = app
        self._mqtt_bridge = mqtt_bridge
        # Story 19.5 (AC8) — last (monotonic time, value) seen per (eq_id, cmd_id),
        # recorded for EVERY inbound event regardless of whether it was published or
        # rejected (state_target_not_found), so a click's fresh read never wins over
        # a more recent Jeedom event received while the click was in flight.
        self._pending_click_values: Dict[Tuple[int, int], Tuple[float, Any]] = {}
        # Story 23.3 (Q7) — retained light/cover channel topics known to exist at the
        # broker: read once per process (``_ensure_retained_scan``) then kept up to date
        # with our own retained publishes. A stale one is emptied only if it is in here.
        self._retained_channel_topics: Set[str] = set()
        self._retained_scan_done = False

    @property
    def is_active(self) -> bool:
        """Whether reliable runtime state is streamed for at least one ACTIONABLE domain.

        Vague 2 (Story 12.2) streams ``switch`` real state, vague 3 (Story 23.3)
        ``light`` / ``cover``. ``CommandSynchronizer`` must still gate per type via
        ``streams_actionable_type`` and per channel via ``sync.readback`` (an entity
        without a real readback command keeps its optimistic path — AC#6, AC#10).
        """
        return bool(_ACTIONABLE_STREAMED)

    def streams_actionable_type(self, ha_type: Any) -> bool:
        """True only for actionable types this synchronizer actually streams.

        Authoritative scope for ``CommandSynchronizer._has_reliable_state``: a type
        not streamed here must NOT be treated as having reliable runtime state,
        otherwise its optimistic publish would be suppressed while no real state is
        ever produced (regression). Streamed: ``switch``, ``light``, ``cover``.
        """
        return ha_type in _ACTIONABLE_STREAMED

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

        # Story 19.5 (AC8) — record BEFORE any other guard: an event rejected below
        # (mqtt unavailable, unresolved target) must still count as "more recent than
        # the click" for `publish_click_states`.
        self._pending_click_values[(eq_id_int, cmd_id_int)] = (time.monotonic(), value)

        if not self._mqtt_bridge or not getattr(self._mqtt_bridge, "is_connected", False):
            self._log(logging.INFO, eq_id=eq_id_int, cmd_id=cmd_id_int,
                      reason_code="mqtt_unavailable", action="reject_state")
            return False

        resolved = self._resolve_state_targets(eq_id_int, cmd_id_int)
        if not resolved:
            self._log(logging.INFO, eq_id=eq_id_int, cmd_id=cmd_id_int,
                      reason_code="state_target_not_found", action="reject_state")
            return False

        # Story 23.3 (Q5): one Jeedom command may feed several topics (numeric
        # FLAP_STATE -> state + position). Each topic gets its own translation.
        published = 0
        failed = 0
        for mapping, binding in resolved:
            payload = self._translate_value(mapping, value, binding.channel, binding.cmd)
            if payload is None:
                self._log(logging.INFO, eq_id=eq_id_int, cmd_id=cmd_id_int,
                          reason_code="empty_state_value", action="skip_state",
                          state_topic=binding.topic)
                continue

            ok = self._mqtt_bridge.publish_message(binding.topic, payload, qos=1, retain=True)
            if not ok:
                failed += 1
                self._log(logging.WARNING, eq_id=eq_id_int, cmd_id=cmd_id_int,
                          reason_code="mqtt_publish_failed", action="publish_state",
                          state_topic=binding.topic)
                continue

            published += 1
            self._remember_retained(binding.topic)
            self._log(logging.INFO, eq_id=eq_id_int, cmd_id=cmd_id_int,
                      reason_code="state_published", action="publish_state",
                      state_topic=binding.topic, ha_type=mapping.ha_entity_type)
        return published > 0 and failed == 0

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
            if mapping is None:
                continue
            eq_id = getattr(mapping, "jeedom_eq_id", None)
            if eq_id is None:
                continue
            try:
                eq_id_int = int(eq_id)
            except (TypeError, ValueError):
                continue
            for candidate in self._iter_streamed_candidates(mapping):
                # I11: filtered on the candidate's OWN decision, never on the
                # principal's. A secondary published under a refused principal
                # must still stream (and a refused secondary under a published
                # principal must never inherit the principal's publication).
                # P1-bis fix (ClaudeBox review round 2, PR #174): the principal's
                # own decision comes straight from `decision`, never from a
                # possibly-stale mapping.publication_decision_ref (actions no
                # longer repoint it on the "publier" success path).
                cand_decision = (
                    decision
                    if candidate is mapping
                    else (getattr(candidate, "publication_decision_ref", None) or decision)
                )
                if not getattr(cand_decision, "should_publish", False):
                    continue
                if not getattr(cand_decision, "discovery_published", False):
                    continue
                # One entry per distinct Jeedom command (one PHP listener each); the
                # entry's topic is the command's first channel topic (Story 23.3).
                for binding in self._candidate_bindings(candidate, cand_decision, eq_id_int):
                    if binding.cmd_id is None:
                        continue
                    key = (eq_id_int, binding.cmd_id)
                    if key in seen:
                        continue
                    seen.add(key)
                    targets.append({
                        "eq_id": eq_id_int,
                        "cmd_id": binding.cmd_id,
                        "ha_type": candidate.ha_entity_type,
                        "state_topic": binding.topic,
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
        published, _failed = await self._publish_initial_states_loop(
            decision, lambda eq_id, binding: binding.current_value,
        )
        return published

    async def publish_click_states(
        self,
        decision: PublicationDecision,
        fresh_values: Mapping[int, Any],
        fresh_since: float,
    ) -> Tuple[int, int]:
        """Publish the state initial with the value read at "Publier" click time.

        Story 19.5. Mirrors ``publish_initial_states`` (same discovery gate, same
        `_translate_value`), but the value source differs:
        - AC8: an event received (published or rejected) for the same (eq_id, cmd_id)
          AFTER ``fresh_since`` wins over the click's value.
        - AC2: otherwise ``fresh_values[cmd_id]`` (the PHP-read click value); NEVER the
          last-sync topology value (`app["topology"]` is never read here).
        - Otherwise no state is published for that candidate (no error, AC2/résiduel AC6).
        Returns (published_count, failed_count) — a failed publish (AC10) is NOT logged
        here as `initial_state_published`, but as a WARNING by the caller-visible count.
        """
        def _resolve(eq_id: Any, binding: _Binding) -> Any:
            if binding.cmd_id is None:
                return None
            pending = self._pending_click_values.get((eq_id, binding.cmd_id))
            if pending is not None and pending[0] > fresh_since:
                return pending[1]
            return fresh_values.get(binding.cmd_id)

        return await self._publish_initial_states_loop(
            decision, _resolve,
            failure_reason_code="initial_state_publish_failed",
            no_value_reason_code="initial_state_no_click_value",
        )

    async def _publish_initial_states_loop(
        self,
        decision: PublicationDecision,
        value_resolver: Any,
        failure_reason_code: Optional[str] = None,
        no_value_reason_code: Optional[str] = None,
    ) -> Tuple[int, int]:
        """Shared candidate loop for `publish_initial_states` / `publish_click_states`.

        Counts publications AND failures (AC10); logging a failure WARNING only when
        ``failure_reason_code`` is given (the sync path, `publish_initial_states`,
        keeps its exact pre-19.5 behaviour: no failure logging, AC9). A candidate
        without a value is skipped; it is logged at DEBUG only when
        ``no_value_reason_code`` is given (résiduel AC6, click path only).
        """
        mapping = getattr(decision, "mapping_result", None)
        if mapping is None:
            return 0, 0
        if not self._mqtt_bridge or not getattr(self._mqtt_bridge, "is_connected", False):
            return 0, 0

        eq_id = getattr(mapping, "jeedom_eq_id", None)
        published = 0
        failed = 0
        if any(
            getattr(c, "ha_entity_type", None) in _PURGEABLE_CHANNELS
            for c in self._iter_streamed_candidates(mapping)
        ):
            await self._ensure_retained_scan()
        for candidate in self._iter_streamed_candidates(mapping):
            # P1-bis fix (ClaudeBox review round 2, PR #174): see list_state_targets.
            cand_decision = (
                decision
                if candidate is mapping
                else (getattr(candidate, "publication_decision_ref", None) or decision)
            )
            if not getattr(cand_decision, "discovery_published", False):
                continue
            state_topic = self._candidate_state_topic(candidate, cand_decision, eq_id)
            if not state_topic or not str(state_topic).startswith("jeedom2ha/"):
                continue
            # Story 23.3 (Q7): a light/cover channel that lost its readback must not
            # keep a stale retained real state next to the optimistic path.
            self._purge_invalid_retained(candidate, str(state_topic), eq_id)
            for binding in self._candidate_bindings(candidate, cand_decision, eq_id):
                raw_value = value_resolver(eq_id, binding)
                if raw_value is None:
                    if no_value_reason_code:
                        self._log(logging.DEBUG, eq_id=eq_id, cmd_id=binding.cmd_id,
                                  reason_code=no_value_reason_code, action="skip_snapshot",
                                  state_topic=binding.topic)
                    continue
                payload = self._translate_value(
                    candidate, raw_value, binding.channel, binding.cmd,
                )
                if payload is None:
                    continue
                if self._mqtt_bridge.publish_message(binding.topic, payload, qos=1, retain=True):
                    published += 1
                    self._remember_retained(binding.topic)
                    self._log(logging.INFO, eq_id=eq_id, cmd_id=binding.cmd_id,
                              reason_code="initial_state_published", action="publish_snapshot",
                              state_topic=binding.topic, ha_type=candidate.ha_entity_type)
                else:
                    failed += 1
                    if failure_reason_code:
                        self._log(logging.WARNING, eq_id=eq_id, cmd_id=binding.cmd_id,
                                  reason_code=failure_reason_code, action="publish_snapshot",
                                  state_topic=binding.topic)
        return published, failed

    async def _ensure_retained_scan(self) -> None:
        """Read once per process which light/cover channel topics are retained.

        Story 23.3 (Q7). The broker is the source of truth (same approach as the
        scenario button purge): only what was actually read can be emptied, so the
        steady state costs no MQTT publish per equipment. A short window only
        under-reports; a bridge without collection (or one busy) leaves the scan
        undone and it is retried at the next publication.
        """
        if self._retained_scan_done:
            return
        collect = getattr(self._mqtt_bridge, "collect_retained_topics", None)
        if collect is None:
            return
        try:
            retained = await collect("jeedom2ha/#")
        except Exception:
            _LOGGER.exception("[SYNC-STATE] Retained channel scan failed, no stale purge")
            return
        if not isinstance(retained, list):
            return
        self._retained_scan_done = True
        for topic in retained:
            if isinstance(topic, str) and _CHANNEL_TOPIC_RE.fullmatch(topic):
                self._retained_channel_topics.add(topic)

    def _remember_retained(self, topic: str) -> None:
        """Track a retained channel topic we just published (real state -> purgeable)."""
        if _CHANNEL_TOPIC_RE.fullmatch(topic):
            self._retained_channel_topics.add(topic)

    def _purge_invalid_retained(
        self,
        candidate: MappingResult,
        state_topic: str,
        eq_id: Any,
    ) -> None:
        """Empty the retained topics of light/cover channels that have no real readback.

        Story 23.3 (Q7). Real states are published ``retain=True``, optimistic ones
        ``retain=False``: an entity that lost its readback command after publishing a
        real state would otherwise get that stale value back from the broker. Runs at
        (re)publication and rescan only (never on a state event), strictly on
        ``jeedom2ha/<eq>/state|brightness|position`` topics derived from the registry
        state topic, and only for topics known to be retained (scan + our own
        publishes), so an entity that keeps its readback or never had one costs nothing.
        """
        channels = _PURGEABLE_CHANNELS.get(getattr(candidate, "ha_entity_type", None))
        if not channels or not state_topic.startswith("jeedom2ha/"):
            return
        live = {name for name, _cmd in readback_commands(candidate.ha_entity_type, candidate)}
        for channel in channels:
            if channel in live:
                continue
            topic = channel_topic(state_topic, channel)
            if topic not in self._retained_channel_topics:
                continue
            if self._mqtt_bridge.publish_message(topic, "", qos=1, retain=True):
                self._retained_channel_topics.discard(topic)
                self._log(logging.INFO, eq_id=eq_id, cmd_id=None,
                          reason_code="stale_retained_state_purged", action="purge_state",
                          state_topic=topic)
            else:
                self._log(logging.WARNING, eq_id=eq_id, cmd_id=None,
                          reason_code="stale_retained_state_purge_failed", action="purge_state",
                          state_topic=topic)

    @staticmethod
    def _candidate_current_value(candidate: MappingResult) -> Any:
        """Read the current Jeedom value from the candidate's readback info command.

        Mono sensor/binary_sensor expose a single info command (the value). An
        actionable type (switch) is resolved ONLY via its readback key
        (``ENERGY_STATE``): a switch without readback (``on_off_only``) has no
        runtime state, so this returns None rather than reading an action command.
        """
        commands = getattr(candidate, "commands", None) or {}
        ha_type = getattr(candidate, "ha_entity_type", None)
        if ha_type in _READBACK_KEYS:
            for _channel, cmd in readback_commands(ha_type, candidate):
                return getattr(cmd, "current_value", None)
            return None
        for cmd in commands.values():
            if str(getattr(cmd, "type", "info")).lower() == "info":
                return getattr(cmd, "current_value", None)
        for cmd in commands.values():
            return getattr(cmd, "current_value", None)
        return None

    def _resolve_state_targets(
        self,
        eq_id: int,
        cmd_id: int,
    ) -> List[Tuple[MappingResult, "_Binding"]]:
        """Find the published streamed entity for (eq_id, cmd_id) and ALL its topics.

        Reads the topics from the publication registry (``app["publications"]``);
        never rebuilds them (state ⊆ discovery). Supports mono-entity / switch / light /
        cover (``jeedom2ha/{eq}/state`` + ``…/brightness`` / ``…/position``) and
        multi-sensor (``jeedom2ha/{eq}/{cmd}/state``). Story 23.3 (Q5): one command
        can feed several topics, hence a list (empty when nothing matches).
        """
        publications = self._app.get("publications", {}) if hasattr(self._app, "get") else {}
        if not isinstance(publications, Mapping):
            return []

        for decision in publications.values():
            mapping = getattr(decision, "mapping_result", None)
            if mapping is None or getattr(mapping, "jeedom_eq_id", None) != eq_id:
                continue

            for candidate in self._iter_streamed_candidates(mapping):
                # I11: the candidate targeted by cmd_id carries its own decision —
                # filter on it, never on the principal's should_publish (l.263-264
                # in the pre-fix version evaluated the principal before even
                # locating the candidate).
                # P1-bis fix (ClaudeBox review round 2, PR #174): see list_state_targets.
                cand_decision = (
                    decision
                    if candidate is mapping
                    else (getattr(candidate, "publication_decision_ref", None) or decision)
                )
                bindings = [
                    b for b in self._candidate_bindings(candidate, cand_decision, eq_id)
                    if b.cmd_id == cmd_id
                ]
                if not bindings:
                    continue
                if not getattr(cand_decision, "should_publish", False):
                    return []
                if not getattr(cand_decision, "discovery_published", False):
                    return []
                return [(candidate, b) for b in bindings]

        return []

    def _candidate_bindings(
        self,
        candidate: MappingResult,
        decision: PublicationDecision,
        eq_id: Any,
    ) -> List["_Binding"]:
        """Enumerate the ``info command -> topic`` feeds of one streamed candidate.

        Actionable types (switch / light / cover) come from ``sync.readback`` (state
        first, then brightness / position); only topics under ``jeedom2ha/`` are kept.
        Sensors, binary sensors and command-scoped secondaries keep the legacy single
        feed (one info command -> one state topic).
        """
        state_topic = self._candidate_state_topic(candidate, decision, eq_id)
        if not state_topic or not str(state_topic).startswith("jeedom2ha/"):
            return []
        state_topic = str(state_topic)
        ha_type = getattr(candidate, "ha_entity_type", None)
        reason_details = getattr(candidate, "reason_details", None) or {}
        if ha_type in _READBACK_KEYS and reason_details.get("cmd_id") is None:
            bindings: List[_Binding] = []
            for channel, cmd in readback_commands(ha_type, candidate):
                cmd_id = self._coerce_cmd_id(cmd)
                if cmd_id is None:
                    continue
                bindings.append(_Binding(
                    channel, cmd, cmd_id,
                    channel_topic(state_topic, channel),
                    getattr(cmd, "current_value", None),
                ))
            return bindings
        return [_Binding(
            CHANNEL_STATE, None, self._candidate_cmd_id(candidate), state_topic,
            self._candidate_current_value(candidate),
        )]

    @staticmethod
    def _iter_streamed_candidates(mapping: MappingResult):
        """Yield the primary mapping plus its secondaries, streamed types only.

        Streamed = vague 1 (sensor/binary_sensor) + actionable switch / light / cover.
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
           info command (e.g. switch ``ENERGY_STATE``; for light/cover the first
           channel, see ``_candidate_bindings`` for all). A switch without readback
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
        ha_type = getattr(candidate, "ha_entity_type", None)
        if ha_type in _READBACK_KEYS:
            # First channel (state) command; the full list is ``_candidate_bindings``.
            for _channel, cmd in readback_commands(ha_type, candidate):
                return cls._coerce_cmd_id(cmd)
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

    def _translate_value(
        self,
        mapping: MappingResult,
        value: Any,
        channel: str = CHANNEL_STATE,
        cmd: Any = None,
    ) -> Optional[str]:
        """Translate a Jeedom info value to the MQTT payload of one channel.

        sensor                 -> the raw value as a string (no invention, no rounding).
        binary_sensor / switch -> ON/OFF honoring the discovery payload defaults
                                  (payload_on=ON / payload_off=OFF — AC#4/AC#6).
        light                  -> ``state``: ON/OFF (numeric readback: > 0 is ON);
                                  ``brightness``: integer 0-100.
        cover                  -> ``state``: open/closed (numeric readback: closed at 0,
                                  open otherwise — Q3); ``position``: integer 0-100.
        Returns None when there is no usable value (leave HA as-is, never fabricate).
        """
        if value is None:
            return None
        text = str(value).strip()
        if text == "":
            return None

        ha_type = mapping.ha_entity_type
        if channel in (CHANNEL_BRIGHTNESS, CHANNEL_POSITION):
            level = self._parse_percent(text)
            return None if level is None else str(level)

        if ha_type == "cover":
            if str(getattr(cmd, "sub_type", "")).lower() == "numeric":
                level = self._parse_percent(text)
                if level is None:
                    return None
                return "closed" if level == 0 else "open"
            lowered = text.lower()
            if lowered in _BINARY_TRUE:
                return "open"
            if lowered in _BINARY_FALSE:
                return "closed"
            return None

        if ha_type == "light" and str(getattr(cmd, "sub_type", "")).lower() == "numeric":
            # A numeric LIGHT_STATE is a dimmer level: above 0 = ON (never the
            # binary table, where "50" would read OFF). Not a brightness source (Q4).
            try:
                level = float(text.replace(",", "."))
            except ValueError:
                return None
            if not math.isfinite(level):
                return None
            return "ON" if level > 0 else "OFF"

        if ha_type in _ONOFF_TYPES or ha_type == "light":
            return "ON" if text.lower() in _BINARY_TRUE else "OFF"
        return text

    @staticmethod
    def _parse_percent(text: str) -> Optional[int]:
        """Parse a 0-100 level; out of range / non numeric -> None (nothing published).

        Fractions are rounded half up (``50.5`` -> ``51``) since the discovery scale
        is the integer ``brightness_scale = 100`` / ``position_open = 100``.
        """
        try:
            number = float(text.replace(",", "."))
        except ValueError:
            return None
        if not math.isfinite(number) or number < 0 or number > 100:
            return None
        return int(math.floor(number + 0.5))

    def _log(self, level: int, eq_id: Any, cmd_id: Any, reason_code: str,
             action: str, **extra: Any) -> None:
        details = " ".join(f"{key}={value}" for key, value in extra.items())
        suffix = f" {details}" if details else ""
        _LOGGER.log(
            level,
            "[SYNC-STATE] eq_id=%s cmd_id=%s reason_code=%s action=%s%s",
            eq_id, cmd_id, reason_code, action, suffix,
        )
