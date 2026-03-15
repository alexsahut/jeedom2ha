"""HA -> Jeedom command synchronization (Story 3.2)."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple

import aiohttp

from models.mapping import MappingResult, PublicationDecision

_LOGGER = logging.getLogger(__name__)

_SET_TOPIC_RE = re.compile(r"^jeedom2ha/(?P<eq_id>\d+)/set$")
_BRIGHTNESS_TOPIC_RE = re.compile(r"^jeedom2ha/(?P<eq_id>\d+)/brightness/set$")
_POSITION_TOPIC_RE = re.compile(r"^jeedom2ha/(?P<eq_id>\d+)/position/set$")


@dataclass(frozen=True)
class ParsedTopic:
    """Canonical parsed command topic."""

    eq_id: int
    channel: str


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
            if not getattr(decision, "should_publish", False):
                continue
            found_publishable = True
            if not bool(getattr(decision, "active_or_alive", False)):
                continue
            found_alive = True

            expected_topics = self._expected_command_topics(mapping)
            if topic not in expected_topics.values():
                continue

            return decision, mapping, None

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
            topics["set"] = f"jeedom2ha/{eq_id}/set"

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
                    cmd = commands.get("LIGHT_ON") or commands.get("ENERGY_ON")
                else:
                    cmd = commands.get("LIGHT_OFF") or commands.get("ENERGY_OFF")
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

        commands = mapping.commands or {}
        if mapping.ha_entity_type in ("light", "switch"):
            for key in ("LIGHT_STATE", "ENERGY_STATE"):
                cmd = commands.get(key)
                if cmd is not None and str(getattr(cmd, "type", "info")).lower() == "info":
                    return True
            return False

        if mapping.ha_entity_type == "cover":
            for key in ("FLAP_STATE", "FLAP_BSO_STATE"):
                cmd = commands.get(key)
                if cmd is not None and str(getattr(cmd, "type", "info")).lower() == "info":
                    return True
            return False

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
