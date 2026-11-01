"""HA -> Jeedom command synchronization (Story 3.2)."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple

import aiohttp

from models.availability import AVAILABILITY_OFFLINE
from models.mapping import MappingResult, PublicationDecision
from sync.readback import CHANNEL_STATE, has_reliable_channel
from sync.readback import barrier_mode, barrier_state, is_barrier_state_command  # Story 24.7

_LOGGER = logging.getLogger(__name__)

_SET_TOPIC_RE = re.compile(r"^jeedom2ha/(?P<eq_id>\d+)/set$")
_NODE_SET_TOPIC_RE = re.compile(r"^jeedom2ha/(?P<eq_id>\d+)/(?P<cmd_id>\d+)/set$")
_BRIGHTNESS_TOPIC_RE = re.compile(r"^jeedom2ha/(?P<eq_id>\d+)/brightness/set$")
_POSITION_TOPIC_RE = re.compile(r"^jeedom2ha/(?P<eq_id>\d+)/position/set$")
_SCENARIO_CMD_TOPIC_RE = re.compile(r"^jeedom2ha/scenario_(?P<scenario_id>\d+)/cmd$")

# Story 24.7 — gate / garage cover (``barrier_mode`` set by CoverMapper, M1).
# States from which an order may be sent, per mode and direction.
# D3 bis — toggle: the direction after a stop (253) lives in a Jeedom scenario's memory,
# invisible here, so a toggle is only sent from a settled end position.
_BARRIER_TOGGLE_ALLOWED = {
    "OPEN": ("closed",),
    "CLOSE": ("open",),
}
# D3 bis — direct GB_OPEN / GB_CLOSE: refused towards the position already reached or
# already being reached, and when the state is unknown.
_BARRIER_DIRECT_ALLOWED = {
    "OPEN": ("closed", "closing", "stopped"),
    "CLOSE": ("open", "opening", "stopped"),
}
# B1 — after a toggle was sent (or its RPC timed out / failed), any new toggle of the same
# equipment is refused until a state event differing from the value read at send time
# arrives, or this delay expires (seconds).
BARRIER_TOGGLE_IN_FLIGHT_TIMEOUT_S = 60.0


def _barrier_refusal_reason(requested: str, state: Optional[str]) -> str:
    if state is None:
        return "barrier_state_unknown"
    if state in ("opening", "closing"):
        return "barrier_in_motion"
    if state == "stopped":
        return "barrier_stopped_direction_unknown"
    return "barrier_already_open" if requested == "OPEN" else "barrier_already_closed"


# I-1 — the only events that prove the toggle had its expected effect, per direction.
_BARRIER_EXPECTED_EFFECT = {
    "OPEN": ("opening", "open"),
    "CLOSE": ("closing", "closed"),
}


@dataclass
class _BarrierToggleInFlight:
    """B1 — one toggle of an equipment, from its guard until the expected state change.

    ``sent_at is None`` while the guard is still running (I-3 marker armed before any
    await, so a concurrent order of the same equipment is refused, whatever the transport).
    Kept in memory only: a daemon restart forgets it.
    """

    requested: str
    state_cmd_id: Optional[int] = None
    sent_state: Optional[str] = None
    sent_at: Optional[float] = None
    expires_at: Optional[float] = None


@dataclass(frozen=True)
class ParsedTopic:
    """Canonical parsed command topic."""

    eq_id: int
    channel: str
    cmd_id: Optional[int] = None


@dataclass(frozen=True)
class CommandTranslation:
    """Resolved Jeedom command payload for one HA command message."""

    cmd_id: int
    options: Dict[str, str]
    command_family: str
    optimistic_state_payload: Optional[str] = None


class CommandSynchronizer:
    """Process MQTT command topics and execute Jeedom cmd::execCmd with runtime gating."""

    def __init__(
        self,
        app: Mapping[str, Any],
        mqtt_bridge: Any,
        jeedom_api_endpoint: str,
        jeedom_core_apikey: str = "",
        request_timeout: float = 2.0,
    ) -> None:
        self._app = app
        self._mqtt_bridge = mqtt_bridge
        self._jeedom_api_endpoint = jeedom_api_endpoint
        self._jeedom_core_api_key = jeedom_core_apikey
        self._request_timeout = max(0.5, float(request_timeout))
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_exec_error_reason: str = ""

    async def stop(self) -> None:
        """Close the underlying HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def handle_command_message(self, topic: str, payload: str) -> bool:
        """Handle one MQTT command message."""
        # Scenario button path (Story 10.1): jeedom2ha/scenario_{id}/cmd
        match = _SCENARIO_CMD_TOPIC_RE.match(topic)
        if match:
            return await self._handle_scenario_command(int(match.group("scenario_id")), topic)

        parsed, parse_reason = self._parse_topic(topic)
        if parsed is None:
            self._log_cmd(
                logging.INFO,
                eq_id="-",
                topic=topic,
                reason_code=parse_reason or "invalid_command_topic",
                action="reject_command",
            )
            return False

        if not self._mqtt_bridge or not getattr(self._mqtt_bridge, "is_connected", False):
            self._log_cmd(
                logging.INFO,
                eq_id=parsed.eq_id,
                topic=topic,
                reason_code="mqtt_unavailable",
                action="reject_command",
            )
            return False

        decision, mapping, resolve_reason = self._resolve_runtime_target(parsed.eq_id, topic)
        if decision is None or mapping is None:
            self._log_cmd(
                logging.INFO,
                eq_id=parsed.eq_id,
                topic=topic,
                reason_code=resolve_reason or "runtime_target_not_found",
                action="reject_command",
            )
            return False

        translation, translation_reason = self._translate_command(mapping, parsed, payload)
        if translation is None:
            self._log_cmd(
                logging.INFO,
                eq_id=parsed.eq_id,
                topic=topic,
                reason_code=translation_reason or "invalid_command_payload",
                action="reject_command",
            )
            return False

        if translation.command_family == "barrier_toggle":
            # Story 24.7 — B1 (in-flight lock) + I3 (fresh read) right before sending.
            refusal = await self._guard_barrier_toggle(mapping, parsed.eq_id, payload.strip().upper())
            if refusal is not None:
                self._log_cmd(
                    logging.INFO,
                    eq_id=parsed.eq_id,
                    topic=topic,
                    reason_code=refusal,
                    action="reject_command",
                )
                return False

        executed = await self._execute_exec_cmd(translation.cmd_id, translation.options)
        if not executed:
            reason = self._last_exec_error_reason or "jeedom_rpc_error"
            self._log_cmd(
                logging.WARNING,
                eq_id=parsed.eq_id,
                topic=topic,
                reason_code=reason,
                action="execute_command",
            )
            return False

        self._log_cmd(
            logging.INFO,
            eq_id=parsed.eq_id,
            topic=topic,
            reason_code="command_executed",
            action="execute_command",
            cmd_id=translation.cmd_id,
        )

        policy = self._select_confirmation_policy(mapping, decision, translation)
        self._log_cmd(
            logging.INFO,
            eq_id=parsed.eq_id,
            topic=topic,
            reason_code=policy,
            action="select_confirmation_policy",
        )

        if policy == "optimistic_controlled" and translation.optimistic_state_payload:
            self._publish_optimistic_state(parsed.eq_id, topic, decision, translation.optimistic_state_payload)

        return True

    def _parse_topic(self, topic: str) -> Tuple[Optional[ParsedTopic], Optional[str]]:
        if not topic.startswith("jeedom2ha/"):
            return None, "topic_outside_jeedom2ha_namespace"

        match = _SET_TOPIC_RE.match(topic)
        if match:
            return ParsedTopic(eq_id=int(match.group("eq_id")), channel="set"), None

        match = _NODE_SET_TOPIC_RE.match(topic)
        if match:
            return ParsedTopic(
                eq_id=int(match.group("eq_id")),
                channel="set",
                cmd_id=int(match.group("cmd_id")),
            ), None

        match = _BRIGHTNESS_TOPIC_RE.match(topic)
        if match:
            return ParsedTopic(eq_id=int(match.group("eq_id")), channel="brightness"), None

        match = _POSITION_TOPIC_RE.match(topic)
        if match:
            return ParsedTopic(eq_id=int(match.group("eq_id")), channel="position"), None

        return None, "invalid_command_topic"

    def _resolve_runtime_target(
        self,
        eq_id: int,
        topic: str,
    ) -> Tuple[Optional[PublicationDecision], Optional[MappingResult], Optional[str]]:
        publications = self._app.get("publications", {}) if hasattr(self._app, "get") else {}
        if not isinstance(publications, Mapping):
            return None, None, "missing_publication_registry"

        found_eq = False
        found_publishable = False
        found_alive = False

        for decision in publications.values():
            mapping = getattr(decision, "mapping_result", None)
            if mapping is None:
                continue
            if getattr(mapping, "jeedom_eq_id", None) != eq_id:
                continue

            found_eq = True

            # P3 fix (ClaudeBox review, 3a408db) — the reason codes below must
            # reflect the CANDIDATE that actually exposes the requested topic,
            # never unconditionally the principal: a refused principal with a
            # published-but-not-alive targeted secondary must report
            # "entity_not_alive", not "entity_not_published". We only fall
            # back to the principal's own decision when no candidate at all
            # exposes this topic (matched_topic stays False below).
            matched_topic = False

            for candidate in [mapping, *(getattr(mapping, "additional_mappings", None) or [])]:
                # P1-bis fix (ClaudeBox review round 2, PR #174) — the principal's
                # own decision comes straight from `decision` (app["publications"]),
                # never from mapping.publication_decision_ref: actions no longer
                # repoint the principal's ref on the "publier" success path, so a
                # stale ref there must not shadow the fresh runtime decision.
                candidate_decision = (
                    decision
                    if candidate is mapping
                    else (getattr(candidate, "publication_decision_ref", None) or decision)
                )
                expected_topics = self._expected_command_topics(candidate)
                if topic not in expected_topics.values():
                    continue

                matched_topic = True
                if getattr(candidate_decision, "should_publish", False):
                    found_publishable = True
                    if bool(getattr(candidate_decision, "active_or_alive", False)):
                        found_alive = True

                # I11: routing is decided on the candidate's OWN decision, never
                # on the principal's — a secondary published under a refused
                # principal must still be routed, and a refused secondary under a
                # published principal must never inherit the principal's routing.
                if not getattr(candidate_decision, "should_publish", False):
                    continue
                if not bool(getattr(candidate_decision, "active_or_alive", False)):
                    continue

                if (
                    bool(getattr(candidate_decision, "local_availability_supported", False))
                    and str(getattr(candidate_decision, "local_availability_state", "")).lower() == AVAILABILITY_OFFLINE
                ):
                    return None, None, "entity_unavailable"

                return candidate_decision, candidate, None

            if not matched_topic and getattr(decision, "should_publish", False):
                found_publishable = True
                if bool(getattr(decision, "active_or_alive", False)):
                    found_alive = True

        if not found_eq:
            return None, None, "unknown_runtime_entity"
        if not found_publishable:
            return None, None, "entity_not_published"
        if not found_alive:
            return None, None, "entity_not_alive"
        return None, None, "topic_not_published_by_discovery"

    def _expected_command_topics(self, mapping: MappingResult) -> Dict[str, str]:
        eq_id = mapping.jeedom_eq_id
        topics: Dict[str, str] = {}

        if mapping.ha_entity_type in ("light", "switch", "cover"):
            reason_details = mapping.reason_details or {}
            command_topic = reason_details.get("command_topic")
            topics["set"] = (
                command_topic
                if isinstance(command_topic, str) and command_topic
                else f"jeedom2ha/{eq_id}/set"
            )

        if mapping.ha_entity_type == "light" and bool(getattr(mapping.capabilities, "has_brightness", False)):
            topics["brightness"] = f"jeedom2ha/{eq_id}/brightness/set"

        if mapping.ha_entity_type == "cover" and bool(getattr(mapping.capabilities, "has_position", False)):
            topics["position"] = f"jeedom2ha/{eq_id}/position/set"

        return topics

    def _translate_command(
        self,
        mapping: MappingResult,
        parsed: ParsedTopic,
        raw_payload: str,
    ) -> Tuple[Optional[CommandTranslation], Optional[str]]:
        commands = mapping.commands or {}
        payload = str(raw_payload).strip()
        payload_upper = payload.upper()

        if parsed.channel == "set":
            if mapping.ha_entity_type in ("light", "switch"):
                if payload_upper not in ("ON", "OFF"):
                    return None, "invalid_command_payload"
                if payload_upper == "ON":
                    cmd = (commands.get("LIGHT_ON") or commands.get("ENERGY_ON")
                           or commands.get("SWITCH_ON") or commands.get("FAN_ON")
                           or commands.get("SET_ON"))
                else:
                    cmd = (commands.get("LIGHT_OFF") or commands.get("ENERGY_OFF")
                           or commands.get("SWITCH_OFF") or commands.get("FAN_OFF")
                           or commands.get("SET_OFF"))
                if cmd is None:
                    return None, "missing_action_command"
                try:
                    cmd_id = int(cmd.id)
                except (TypeError, ValueError):
                    return None, "missing_action_command"
                return CommandTranslation(
                    cmd_id=cmd_id,
                    options={},
                    command_family="on_off",
                    optimistic_state_payload=payload_upper,
                ), None

            if barrier_mode(mapping) is not None:
                # Story 24.7 — portail / garage (D3 bis).
                return self._translate_barrier_command(mapping, parsed, payload_upper)

            if mapping.ha_entity_type == "cover":
                command_by_payload = {
                    "OPEN": "FLAP_UP",
                    "CLOSE": "FLAP_DOWN",
                    "STOP": "FLAP_STOP",
                }
                command_key = command_by_payload.get(payload_upper)
                if not command_key:
                    return None, "invalid_command_payload"
                cmd = commands.get(command_key)
                if cmd is None:
                    return None, "missing_action_command"
                try:
                    cmd_id = int(cmd.id)
                except (TypeError, ValueError):
                    return None, "missing_action_command"
                return CommandTranslation(cmd_id=cmd_id, options={}, command_family="cover_motion"), None

            return None, "invalid_command_payload"

        if parsed.channel == "brightness":
            slider = self._normalize_slider_payload(payload)
            if slider is None:
                return None, "invalid_command_payload"
            cmd = commands.get("LIGHT_SLIDER")
            if cmd is None:
                return None, "missing_action_command"
            try:
                cmd_id = int(cmd.id)
            except (TypeError, ValueError):
                return None, "missing_action_command"
            return CommandTranslation(
                cmd_id=cmd_id,
                options={"slider": str(slider)},
                command_family="slider",
            ), None

        if parsed.channel == "position":
            slider = self._normalize_slider_payload(payload)
            if slider is None:
                return None, "invalid_command_payload"
            cmd = commands.get("FLAP_SLIDER")
            if cmd is None:
                return None, "missing_action_command"
            try:
                cmd_id = int(cmd.id)
            except (TypeError, ValueError):
                return None, "missing_action_command"
            return CommandTranslation(
                cmd_id=cmd_id,
                options={"slider": str(slider)},
                command_family="slider",
            ), None

        return None, "invalid_command_topic"

    def _translate_barrier_command(
        self,
        mapping: MappingResult,
        parsed: ParsedTopic,
        payload_upper: str,
    ) -> Tuple[Optional[CommandTranslation], Optional[str]]:
        """Story 24.7 (D3 bis) — OPEN / CLOSE of a gate or garage ``cover``.

        - ``toggle_on_state`` (``GB_TOGGLE`` present; ``GB_OPEN`` / ``GB_CLOSE`` ignored): the
          translation only names the toggle; the guard runs in ``_guard_barrier_toggle``
          right before sending, on a FRESH Jeedom read (I3), behind the in-flight lock (B1).
        - ``direct`` (``GB_OPEN`` + ``GB_CLOSE``, no toggle): guarded by the last known state
          (OPEN refused from open / opening, CLOSE from closed / closing, unknown refused).
        No stop (no ``GB_STOP`` command, discovery publishes ``payload_stop: null``).
        """
        commands = mapping.commands or {}
        if payload_upper not in ("OPEN", "CLOSE"):
            if payload_upper == "STOP":
                return None, "missing_action_command"
            return None, "invalid_command_payload"

        state_cmd = next((c for c in commands.values() if is_barrier_state_command(c)), None)
        if state_cmd is None:
            return None, "barrier_without_state"

        mode = barrier_mode(mapping)
        if mode == "toggle_on_state":
            cmd = commands.get("GB_TOGGLE")
            if cmd is None:
                return None, "missing_action_command"
            family = "barrier_toggle"
        else:
            cmd = commands.get("GB_OPEN") if payload_upper == "OPEN" else commands.get("GB_CLOSE")
            if cmd is None:
                return None, "missing_action_command"
            raw_value = self._last_known_barrier_value(parsed.eq_id, state_cmd)
            state = barrier_state(raw_value)
            if state not in _BARRIER_DIRECT_ALLOWED[payload_upper]:
                reason = _barrier_refusal_reason(payload_upper, state)
                self._log_barrier_refusal(parsed.eq_id, reason, payload_upper, state, raw_value)
                return None, reason
            family = "cover_motion"

        try:
            cmd_id = int(cmd.id)
        except (TypeError, ValueError):
            return None, "missing_action_command"
        return CommandTranslation(cmd_id=cmd_id, options={}, command_family=family), None

    def _log_barrier_refusal(
        self, eq_id: int, reason: str, requested: str, state: Optional[str], raw_value: Any,
    ) -> None:
        self._log_cmd(
            logging.WARNING,
            eq_id=eq_id,
            topic=f"jeedom2ha/{eq_id}/set",
            reason_code=reason,
            action="refuse_barrier_order",
            requested=requested,
            last_state=state or "unknown",
            raw_value=raw_value,
        )

    def _barrier_state_cmd(self, mapping: MappingResult) -> Any:
        return next(
            (c for c in (mapping.commands or {}).values() if is_barrier_state_command(c)), None
        )

    def _barrier_lock_refusal(self, eq_id: int) -> Optional[str]:
        """B1 / I-1 / I-2 — refusal reason while a previous toggle of ``eq_id`` holds the lock.

        - guard still running (``sent_at`` None): ``barrier_toggle_in_flight``;
        - released ONLY by the expected effect (OPEN: 254/255, CLOSE: 252/0) received
          after the send; any other event (late older value, out of table, empty) keeps it;
        - before the delay: ``barrier_toggle_in_flight``;
        - after the delay without the expected effect: NOT released (``barrier_no_effect``)
          until an event received after the send differs from the state read at send time.
        """
        lock = self._barrier_in_flight().get(eq_id)
        if lock is None:
            return None
        if lock.sent_at is None:
            return "barrier_toggle_in_flight"
        event_state = self._barrier_event_state_since(eq_id, lock)
        if event_state in _BARRIER_EXPECTED_EFFECT[lock.requested]:
            self._barrier_in_flight().pop(eq_id, None)
            return None
        if time.monotonic() < float(lock.expires_at or 0.0):
            return "barrier_toggle_in_flight"
        # Relecture 3 (résidu I-2) : après le délai, seul un événement reçu APRÈS l'expiration peut
        # libérer le verrou ; un événement antérieur et retardé (ex. 252 arrivé juste après un OPEN)
        # ne doit pas le lever à l'expiration.
        late_state = self._barrier_event_state_since(eq_id, lock, since=float(lock.expires_at or 0.0))
        if late_state is not None and late_state != lock.sent_state:
            self._barrier_in_flight().pop(eq_id, None)
            return None
        return "barrier_no_effect"

    def _barrier_event_state_since(
        self, eq_id: int, lock: _BarrierToggleInFlight, since: Optional[float] = None
    ) -> Optional[str]:
        """Barrier state of the last Jeedom event received AFTER the send (or after ``since``), else None."""
        state_sync = self._app.get("state_synchronizer") if hasattr(self._app, "get") else None
        reader = getattr(state_sync, "last_event", None)
        if not callable(reader) or lock.state_cmd_id is None:
            return None
        try:
            event = reader(eq_id, lock.state_cmd_id)
        except Exception:
            return None
        if not (isinstance(event, tuple) and len(event) == 2):
            return None
        if lock.sent_at is None or not event[0] > lock.sent_at:
            return None
        if since is not None and not event[0] > since:
            return None
        return barrier_state(event[1])

    def _barrier_in_flight(self) -> Dict[int, _BarrierToggleInFlight]:
        locks = getattr(self, "_barrier_in_flight_locks", None)
        if locks is None:
            locks = {}
            self._barrier_in_flight_locks = locks
        return locks

    async def _guard_barrier_toggle(
        self, mapping: MappingResult, eq_id: int, requested: str,
    ) -> Optional[str]:
        """B1 + I3 + I-3 — returns a refusal reason, or None when the toggle may be sent now.

        Atomic per equipment: the lock check and the arming of the "in progress" marker run
        with no await in between, so two concurrent orders cannot both pass. The marker is
        removed on refusal; on success it becomes the in-flight lock BEFORE the RPC, so a
        timeout / RPC error of the send still locks the equipment.
        """
        refusal = self._barrier_lock_refusal(eq_id)
        if refusal is not None:
            self._log_barrier_refusal(eq_id, refusal, requested, None, None)
            return refusal
        locks = self._barrier_in_flight()
        marker = _BarrierToggleInFlight(requested=requested)
        locks[eq_id] = marker

        def _refuse(reason: str, state: Optional[str], raw: Any) -> str:
            if locks.get(eq_id) is marker:
                locks.pop(eq_id, None)
            self._log_barrier_refusal(eq_id, reason, requested, state, raw)
            return reason

        state_cmd = self._barrier_state_cmd(mapping)
        state_cmd_id = self._coerce_int(getattr(state_cmd, "id", None))
        if state_cmd_id is None:
            return _refuse("barrier_without_state", None, None)
        try:
            ok, raw_value = await self._read_info_value(state_cmd_id)
        except asyncio.CancelledError:
            # Nothing was sent: never leave a stale "in progress" marker behind.
            if locks.get(eq_id) is marker:
                locks.pop(eq_id, None)
            raise
        except Exception:
            ok, raw_value = False, None
        if not ok:
            return _refuse("barrier_state_read_failed", None, None)
        state = barrier_state(raw_value)
        if state not in _BARRIER_TOGGLE_ALLOWED[requested]:
            return _refuse(_barrier_refusal_reason(requested, state), state, raw_value)
        now = time.monotonic()
        marker.state_cmd_id = state_cmd_id
        marker.sent_state = state
        marker.sent_at = now
        marker.expires_at = now + float(BARRIER_TOGGLE_IN_FLIGHT_TIMEOUT_S)
        return None

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    async def _read_info_value(self, cmd_id: int) -> Tuple[bool, Any]:
        """I3 — fresh read of a Jeedom info command through the API the daemon already uses.

        ``cmd::execCmd`` on an ``info`` command returns its value (``{"value": …}``) without
        acting on anything. Returns ``(False, None)`` on any failure (refusal upstream).
        """
        if not self._jeedom_api_endpoint or not self._jeedom_core_api_key:
            return False, None
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._request_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        request_payload = {
            "jsonrpc": "2.0",
            "id": "jeedom2ha-barrier-read",
            "method": "cmd::execCmd",
            "params": {
                "apikey": self._jeedom_core_api_key,
                "id": int(cmd_id),
                "options": {},
            },
        }
        try:
            assert self._session is not None
            async with self._session.post(self._jeedom_api_endpoint, json=request_payload) as response:
                if response.status != 200:
                    return False, None
                payload = await response.json(content_type=None)
        except Exception:
            return False, None
        if not isinstance(payload, Mapping) or payload.get("error"):
            return False, None
        result = payload.get("result")
        if isinstance(result, Mapping):
            result = result.get("value")
        if result is None:
            return False, None
        return True, result

    def _last_known_barrier_value(self, eq_id: int, state_cmd: Any) -> Any:
        """Last known barrier value: last Jeedom event received, else the topology value."""
        state_sync = self._app.get("state_synchronizer") if hasattr(self._app, "get") else None
        reader = getattr(state_sync, "last_event_value", None)
        if callable(reader):
            try:
                value = reader(eq_id, getattr(state_cmd, "id", None))
            except Exception:
                value = None
            if value is not None:
                return value
        return getattr(state_cmd, "current_value", None)

    def _normalize_slider_payload(self, payload: str) -> Optional[int]:
        if payload == "":
            return None
        try:
            value = int(payload)
        except (TypeError, ValueError):
            return None
        if value < 0 or value > 100:
            return None
        return value

    def _select_confirmation_policy(
        self,
        mapping: MappingResult,
        decision: PublicationDecision,
        translation: CommandTranslation,
    ) -> str:
        if translation.command_family == "on_off" and mapping.ha_entity_type in ("light", "switch"):
            if self._has_reliable_state(mapping, decision):
                return "real_state_confirmation"
            return "optimistic_controlled"

        if translation.command_family == "barrier_toggle" and mapping.ha_entity_type == "cover":
            # Story 24.7 — a toggle is only ever sent with a numeric barrier state.
            if self._has_reliable_state(mapping, decision):
                return "real_state_confirmation"
            return "stateless"

        if translation.command_family == "cover_motion" and mapping.ha_entity_type == "cover":
            if self._has_reliable_state(mapping, decision):
                return "real_state_confirmation"
            return "stateless"

        return "stateless"

    def _has_reliable_state(self, mapping: MappingResult, decision: PublicationDecision) -> bool:
        if not getattr(decision, "state_topic", ""):
            return False

        state_sync = self._app.get("state_synchronizer") if hasattr(self._app, "get") else None
        if not self._is_state_sync_active(state_sync):
            return False

        # Scope-aware (Story 12.2): a type the synchronizer does NOT stream must not
        # be treated as reliable, else its optimistic publish is suppressed while no
        # real state ever arrives (regression). Streamed: switch, light, cover.
        if not self._state_sync_streams_type(state_sync, mapping.ha_entity_type):
            return False

        # Story 23.3 — reliability is evaluated per channel and shared with discovery
        # (``optimistic``) and StateSynchronizer through ``sync.readback``. Only the ON/OFF
        # (open/closed) channel decides whether the optimistic publish is suppressed:
        # a brightness / position info command alone never makes it reliable (Q4).
        return has_reliable_channel(mapping.ha_entity_type, mapping, CHANNEL_STATE)

    @staticmethod
    def _state_sync_streams_type(state_sync: Any, ha_type: Any) -> bool:
        """Whether the state sync actually streams reliable state for ``ha_type``.

        Backward-compatible: a synchronizer without ``streams_actionable_type``
        (older or fake services) keeps the prior behavior (an active sync is treated
        as reliable for the type). The real ``StateSynchronizer`` (Story 12.2)
        returns True for ``switch`` only, so light/cover keep their optimistic path.
        """
        checker = getattr(state_sync, "streams_actionable_type", None)
        if not callable(checker):
            return True
        try:
            return bool(checker(ha_type))
        except Exception:
            return False

    def _is_state_sync_active(self, state_sync: Any) -> bool:
        """Return True only when a state sync service is really active and usable."""
        if state_sync is None:
            return False

        explicit_flag = getattr(state_sync, "is_active", None)
        if callable(explicit_flag):
            try:
                return bool(explicit_flag())
            except Exception:
                return False
        if explicit_flag is not None:
            return bool(explicit_flag)

        task = getattr(state_sync, "_task", None)
        if task is None:
            return False
        if hasattr(task, "done"):
            try:
                if task.done():
                    return False
            except Exception:
                return False

        endpoint = getattr(state_sync, "_jeedom_api_endpoint", "")
        core_apikey = getattr(state_sync, "_jeedom_core_apikey", "")
        return bool(endpoint and core_apikey)

    def _publish_optimistic_state(
        self,
        eq_id: int,
        topic: str,
        decision: PublicationDecision,
        payload: str,
    ) -> None:
        state_topic = getattr(decision, "state_topic", None)
        if not state_topic or not str(state_topic).startswith("jeedom2ha/"):
            self._log_cmd(
                logging.WARNING,
                eq_id=eq_id,
                topic=topic,
                reason_code="missing_state_topic_runtime",
                action="skip_optimistic_state",
            )
            return

        ok = self._mqtt_bridge.publish_message(state_topic, payload, qos=1, retain=False)
        if ok:
            self._log_cmd(
                logging.INFO,
                eq_id=eq_id,
                topic=topic,
                reason_code="optimistic_controlled",
                action="publish_immediate_state",
                state_topic=state_topic,
            )
        else:
            self._log_cmd(
                logging.WARNING,
                eq_id=eq_id,
                topic=topic,
                reason_code="mqtt_publish_failed",
                action="publish_immediate_state",
                state_topic=state_topic,
            )

    async def _execute_exec_cmd(self, cmd_id: int, options: Dict[str, str]) -> bool:
        self._last_exec_error_reason = ""

        if not self._jeedom_api_endpoint or not self._jeedom_core_api_key:
            self._last_exec_error_reason = "jeedom_rpc_error"
            return False

        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._request_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)

        request_payload = {
            "jsonrpc": "2.0",
            "id": "jeedom2ha-command-sync",
            "method": "cmd::execCmd",
            "params": {
                "apikey": self._jeedom_core_api_key,
                "id": int(cmd_id),
                "options": dict(options),
            },
        }

        try:
            assert self._session is not None
            async with self._session.post(self._jeedom_api_endpoint, json=request_payload) as response:
                if response.status != 200:
                    self._last_exec_error_reason = "jeedom_rpc_error"
                    return False
                payload = await response.json(content_type=None)
        except asyncio.TimeoutError:
            self._last_exec_error_reason = "jeedom_rpc_timeout"
            return False
        except aiohttp.ClientError:
            self._last_exec_error_reason = "jeedom_rpc_error"
            return False
        except Exception:
            self._last_exec_error_reason = "jeedom_rpc_error"
            return False

        if isinstance(payload, Mapping) and payload.get("error"):
            self._last_exec_error_reason = "jeedom_rpc_error"
            return False

        return True

    async def _handle_scenario_command(self, scenario_id: int, topic: str) -> bool:
        """Handle a button press for a Jeedom scenario (Story 10.1)."""
        if not self._mqtt_bridge or not getattr(self._mqtt_bridge, "is_connected", False):
            self._log_cmd(logging.INFO, eq_id=f"scenario_{scenario_id}", topic=topic,
                          reason_code="mqtt_unavailable", action="reject_scenario_command")
            return False

        scenario_publications = self._app.get("scenario_publications", {}) if hasattr(self._app, "get") else {}
        decision = scenario_publications.get(scenario_id)
        if decision is None or not getattr(decision, "should_publish", False):
            self._log_cmd(logging.INFO, eq_id=f"scenario_{scenario_id}", topic=topic,
                          reason_code="unknown_runtime_entity", action="reject_scenario_command")
            return False

        executed = await self._execute_scenario_start(scenario_id)
        if not executed:
            reason = self._last_exec_error_reason or "jeedom_rpc_error"
            self._log_cmd(logging.WARNING, eq_id=f"scenario_{scenario_id}", topic=topic,
                          reason_code=reason, action="execute_scenario_command")
            return False

        self._log_cmd(logging.INFO, eq_id=f"scenario_{scenario_id}", topic=topic,
                      reason_code="scenario_started", action="execute_scenario_command")
        return True

    async def _execute_scenario_start(self, scenario_id: int) -> bool:
        """Call scenario::changeState run on Jeedom for a scenario button (Story 10.1)."""
        self._last_exec_error_reason = ""

        if not self._jeedom_api_endpoint or not self._jeedom_core_api_key:
            self._last_exec_error_reason = "jeedom_rpc_error"
            return False

        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._request_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)

        request_payload = {
            "jsonrpc": "2.0",
            "id": "jeedom2ha-scenario-start",
            "method": "scenario::changeState",
            "params": {
                "apikey": self._jeedom_core_api_key,
                "id": scenario_id,
                "state": "run",
            },
        }

        try:
            assert self._session is not None
            async with self._session.post(self._jeedom_api_endpoint, json=request_payload) as response:
                if response.status != 200:
                    self._last_exec_error_reason = "jeedom_rpc_error"
                    return False
                result = await response.json(content_type=None)
        except asyncio.TimeoutError:
            self._last_exec_error_reason = "jeedom_rpc_timeout"
            return False
        except aiohttp.ClientError:
            self._last_exec_error_reason = "jeedom_rpc_error"
            return False
        except Exception:
            self._last_exec_error_reason = "jeedom_rpc_error"
            return False

        if isinstance(result, Mapping) and result.get("error"):
            self._last_exec_error_reason = "jeedom_rpc_error"
            return False

        return True

    def _log_cmd(
        self,
        level: int,
        eq_id: Any,
        topic: str,
        reason_code: str,
        action: str,
        **extra: Any,
    ) -> None:
        details = " ".join(f"{key}={value}" for key, value in extra.items())
        suffix = f" {details}" if details else ""
        _LOGGER.log(
            level,
            "[SYNC-CMD] eq_id=%s topic=%s reason_code=%s action=%s%s",
            eq_id,
            topic,
            reason_code,
            action,
            suffix,
        )
