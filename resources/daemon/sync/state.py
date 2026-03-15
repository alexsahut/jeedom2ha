"""Incremental Jeedom -> Home Assistant state synchronization.

This module polls Jeedom `event::changes` and republishes eligible state updates
to MQTT state topics that are already present in the runtime publication registry.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urlparse, urlunparse

import aiohttp

from models.mapping import MappingResult

_LOGGER = logging.getLogger(__name__)


def derive_jeedom_api_endpoint(callback_url: str) -> str:
    """Build the local Jeedom JSON-RPC endpoint from daemon callback URL."""
    if not callback_url:
        return ""

    parsed = urlparse(callback_url)
    if not parsed.scheme or not parsed.netloc:
        return ""

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            "/core/api/jeeApi.php",
            "",
            "",
            "",
        )
    )


@dataclass(frozen=True)
class RuntimeStateTarget:
    """Resolved runtime target for one Jeedom command state update."""

    cmd_id: int
    state_topic: str
    entity_type: str
    active_or_alive: bool
    publication_uid: str


class StateSynchronizer:
    """Poll `event::changes` and publish incremental states for known entities."""

    def __init__(
        self,
        app: Mapping[str, Any],
        mqtt_bridge: Any,
        jeedom_api_endpoint: str,
        jeedom_core_apikey: str = "",
        poll_interval: float = 1.0,
        request_timeout: float = 2.0,
        jeedom_apikey: Optional[str] = None,
    ) -> None:
        self._app = app
        self._mqtt_bridge = mqtt_bridge
        self._jeedom_api_endpoint = jeedom_api_endpoint
        self._jeedom_core_apikey = jeedom_core_apikey or (jeedom_apikey or "")
        self._poll_interval = max(0.2, float(poll_interval))
        self._request_timeout = max(0.5, float(request_timeout))

        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._cursor = datetime.now(timezone.utc)
        self._session: Optional[aiohttp.ClientSession] = None
        self._api_warning_logged = False

    async def start(self) -> None:
        """Start background state synchronization loop."""
        if self._task and not self._task.done():
            return

        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop(), name="state-synchronizer")
        _LOGGER.info("[SYNC] StateSynchronizer started interval=%.1fs", self._poll_interval)

    async def stop(self) -> None:
        """Stop background state synchronization loop."""
        if self._task is None:
            return

        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None
        _LOGGER.info("[SYNC] StateSynchronizer stopped")

    @property
    def is_active(self) -> bool:
        """True only when sync loop is running and Jeedom core API config is usable."""
        if not self._jeedom_api_endpoint or not self._jeedom_core_apikey:
            return False
        return self._task is not None and not self._task.done()

    async def run_once(self) -> int:
        """Run one synchronization cycle. Exposed to ease testing."""
        runtime_index = self._build_runtime_index()
        if not runtime_index:
            return 0

        if not self._mqtt_bridge or not getattr(self._mqtt_bridge, "is_connected", False):
            self._log_sync(
                logging.INFO,
                cmd_id="-",
                reason_code="mqtt_unavailable",
                action="skip_batch",
            )
            return 0

        changes = await self._fetch_changes()
        if not changes:
            return 0

        return self._apply_changes(changes, runtime_index)

    async def _run_loop(self) -> None:
        """Background synchronization loop with resilient retries."""
        try:
            while not self._stop_event.is_set():
                try:
                    await self.run_once()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    _LOGGER.exception("[SYNC] Unhandled error in synchronization loop")

                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self._poll_interval)
                except asyncio.TimeoutError:
                    pass
        finally:
            if self._session and not self._session.closed:
                await self._session.close()
            self._session = None

    def _build_runtime_index(self) -> Dict[int, RuntimeStateTarget]:
        """Build cmd_id -> runtime state target from current publication registry."""
        publications = self._app.get("publications", {}) if hasattr(self._app, "get") else {}
        mappings = self._app.get("mappings", {}) if hasattr(self._app, "get") else {}

        if not isinstance(publications, Mapping):
            return {}

        runtime_index: Dict[int, RuntimeStateTarget] = {}
        for publication_uid, decision in publications.items():
            if not getattr(decision, "should_publish", False):
                continue
            if not bool(getattr(decision, "active_or_alive", True)):
                continue

            mapping: Optional[MappingResult] = getattr(decision, "mapping_result", None)
            if mapping is None and isinstance(mappings, Mapping):
                mapping = mappings.get(publication_uid)
            if mapping is None:
                self._log_sync(
                    logging.WARNING,
                    cmd_id="-",
                    reason_code="missing_mapping_runtime",
                    action="skip_runtime_entry",
                    publication_uid=publication_uid,
                )
                continue

            state_topic = getattr(decision, "state_topic", None)
            if not state_topic:
                self._log_sync(
                    logging.WARNING,
                    cmd_id="-",
                    reason_code="missing_state_topic_runtime",
                    action="skip_runtime_entry",
                    publication_uid=publication_uid,
                )
                continue

            cmd_ids = self._extract_cmd_ids(mapping)
            if not cmd_ids:
                self._log_sync(
                    logging.WARNING,
                    cmd_id="-",
                    reason_code="missing_cmd_runtime",
                    action="skip_runtime_entry",
                    publication_uid=publication_uid,
                )
                continue

            for cmd_id in cmd_ids:
                runtime_index[cmd_id] = RuntimeStateTarget(
                    cmd_id=cmd_id,
                    state_topic=state_topic,
                    entity_type=mapping.ha_entity_type,
                    active_or_alive=True,
                    publication_uid=str(publication_uid),
                )

        return runtime_index

    async def _fetch_changes(self) -> List[Dict[str, Any]]:
        """Fetch incremental Jeedom changes from event::changes."""
        if not self._jeedom_api_endpoint:
            if not self._api_warning_logged:
                self._api_warning_logged = True
                self._log_sync(
                    logging.WARNING,
                    cmd_id="-",
                    reason_code="missing_jeedom_api_endpoint",
                    action="disable_incremental_sync",
                )
            return []

        if not self._jeedom_core_apikey:
            if not self._api_warning_logged:
                self._api_warning_logged = True
                self._log_sync(
                    logging.WARNING,
                    cmd_id="-",
                    reason_code="missing_jeedom_core_apikey",
                    action="disable_incremental_sync",
                )
            return []

        self._api_warning_logged = False
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._request_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)

        request_payload = {
            "jsonrpc": "2.0",
            "id": "jeedom2ha-state-sync",
            "method": "event::changes",
            "params": {
                "apikey": self._jeedom_core_apikey,
                "datetime": self._format_cursor(self._cursor),
            },
        }

        try:
            assert self._session is not None  # narrowed by guard above
            async with self._session.post(self._jeedom_api_endpoint, json=request_payload) as response:
                if response.status != 200:
                    _LOGGER.warning(
                        "[SYNC] Jeedom API call failed status=%s endpoint=%s",
                        response.status,
                        self._jeedom_api_endpoint,
                    )
                    return []
                payload = await response.json(content_type=None)
        except asyncio.TimeoutError:
            _LOGGER.warning("[SYNC] event::changes timeout after %.1fs", self._request_timeout)
            return []
        except aiohttp.ClientError as exc:
            _LOGGER.warning("[SYNC] event::changes client error: %s", exc)
            return []

        changes = self._extract_changes(payload)
        self._advance_cursor(changes)
        return changes

    def _extract_changes(self, payload: Any) -> List[Dict[str, Any]]:
        """Extract list of changes from Jeedom JSON-RPC responses."""
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, Mapping)]

        if not isinstance(payload, Mapping):
            return []

        if payload.get("error"):
            _LOGGER.warning("[SYNC] Jeedom API returned error for event::changes: %s", payload.get("error"))
            return []

        result = payload.get("result", payload.get("changes", []))
        if isinstance(result, list):
            return [item for item in result if isinstance(item, Mapping)]

        if isinstance(result, Mapping):
            for key in ("changes", "events", "result"):
                nested = result.get(key)
                if isinstance(nested, list):
                    return [item for item in nested if isinstance(item, Mapping)]

        return []

    def _advance_cursor(self, changes: List[Dict[str, Any]]) -> None:
        """Advance incremental cursor to avoid reprocessing already seen events."""
        if not changes:
            return

        max_dt: Optional[datetime] = None
        for change in changes:
            evt_dt = self._extract_event_datetime(change)
            if evt_dt and (max_dt is None or evt_dt > max_dt):
                max_dt = evt_dt

        if max_dt is None:
            max_dt = datetime.now(timezone.utc)

        if max_dt <= self._cursor:
            max_dt = self._cursor
        self._cursor = max_dt + timedelta(microseconds=1)

    def _apply_changes(
        self,
        changes: List[Dict[str, Any]],
        runtime_index: Dict[int, RuntimeStateTarget],
    ) -> int:
        """Apply one change batch after runtime gating and debouncing."""
        debounced: Dict[int, Dict[str, Any]] = {}
        for change in changes:
            if not self._is_cmd_update_event(change):
                self._log_sync(
                    logging.DEBUG,
                    cmd_id="-",
                    reason_code="event_not_cmd_update",
                    action="skip_event",
                    event_name=change.get("name", "-"),
                )
                continue

            cmd_id = self._extract_cmd_id(change)
            if cmd_id is None:
                self._log_sync(
                    logging.WARNING,
                    cmd_id="-",
                    reason_code="invalid_event_payload",
                    action="skip_event",
                    event_name=change.get("name", "-"),
                )
                continue
            debounced[cmd_id] = dict(change)

        published_count = 0
        for cmd_id, change in debounced.items():
            target = runtime_index.get(cmd_id)
            if target is None or not target.active_or_alive:
                self._log_sync(
                    logging.INFO,
                    cmd_id=cmd_id,
                    reason_code="cmd_not_published_or_not_alive",
                    action="skip_event",
                )
                continue

            topic = target.state_topic
            if not topic.startswith("jeedom2ha/"):
                self._log_sync(
                    logging.WARNING,
                    cmd_id=cmd_id,
                    reason_code="topic_outside_jeedom2ha_namespace",
                    action="skip_event",
                    state_topic=topic,
                )
                continue

            value = self._extract_value(change)
            payload = self._normalize_state_value(target.entity_type, value)
            if payload is None:
                self._log_sync(
                    logging.WARNING,
                    cmd_id=cmd_id,
                    reason_code="invalid_state_value",
                    action="skip_event",
                    raw_value=value,
                )
                continue

            if not self._mqtt_bridge or not getattr(self._mqtt_bridge, "is_connected", False):
                self._log_sync(
                    logging.INFO,
                    cmd_id=cmd_id,
                    reason_code="mqtt_unavailable",
                    action="skip_event",
                )
                continue

            ok = self._mqtt_bridge.publish_message(topic, payload, qos=1, retain=False)
            if ok:
                published_count += 1
                self._log_sync(
                    logging.INFO,
                    cmd_id=cmd_id,
                    reason_code="published",
                    action="publish_state",
                    state_topic=topic,
                )
            else:
                self._log_sync(
                    logging.WARNING,
                    cmd_id=cmd_id,
                    reason_code="mqtt_publish_failed",
                    action="publish_state",
                    state_topic=topic,
                )

        return published_count

    def _is_cmd_update_event(self, change: Mapping[str, Any]) -> bool:
        """Return True only for cmd::update events (or legacy cmd payloads without name)."""
        name = change.get("name")
        if name is None:
            # Legacy/alternative payloads used in local tests may not carry event name.
            return True
        return str(name) == "cmd::update"

    def _extract_cmd_ids(self, mapping: MappingResult) -> List[int]:
        """Extract runtime Jeedom cmd IDs for one mapped entity."""
        commands = list((mapping.commands or {}).values())
        if not commands:
            return []

        info_cmd_ids = []
        all_cmd_ids = []
        for cmd in commands:
            cmd_id = getattr(cmd, "id", None)
            if cmd_id is None:
                continue
            try:
                cmd_id_int = int(cmd_id)
            except (TypeError, ValueError):
                continue
            all_cmd_ids.append(cmd_id_int)
            if str(getattr(cmd, "type", "info")).lower() == "info":
                info_cmd_ids.append(cmd_id_int)

        source = info_cmd_ids if info_cmd_ids else all_cmd_ids
        seen = set()
        unique_cmd_ids = []
        for cmd_id in source:
            if cmd_id not in seen:
                seen.add(cmd_id)
                unique_cmd_ids.append(cmd_id)
        return unique_cmd_ids

    def _extract_cmd_id(self, change: Mapping[str, Any]) -> Optional[int]:
        """Extract Jeedom command ID from a change payload."""
        option = change.get("option")
        if isinstance(option, Mapping) and "cmd_id" in option:
            raw = option.get("cmd_id")
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None

        for key in ("cmd_id", "cmdId", "id", "cmd"):
            if key not in change:
                continue
            raw = change.get(key)
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None
        return None

    def _extract_value(self, change: Mapping[str, Any]) -> Any:
        """Extract raw state value from a change payload."""
        option = change.get("option")
        if isinstance(option, Mapping) and "value" in option:
            return option.get("value")

        for key in ("value", "state", "cmd_value"):
            if key in change:
                return change.get(key)
        return None

    def _normalize_state_value(self, entity_type: str, raw_value: Any) -> Optional[str]:
        """Normalize state value conservatively according to entity type."""
        if raw_value is None:
            return None

        if entity_type == "sensor":
            try:
                return str(float(raw_value))
            except (TypeError, ValueError):
                return None

        if entity_type in ("binary_sensor", "switch", "light"):
            bool_value = self._normalize_boolean(raw_value)
            if bool_value is None:
                return None
            return "ON" if bool_value else "OFF"

        if entity_type == "cover":
            text = str(raw_value).strip().lower()
            if text in {"1", "on", "open", "opened", "opening", "true"}:
                return "open"
            if text in {"0", "off", "close", "closed", "closing", "false"}:
                return "closed"
            return None

        return None

    def _normalize_boolean(self, raw_value: Any) -> Optional[bool]:
        """Normalize Jeedom-like values into boolean states."""
        if isinstance(raw_value, bool):
            return raw_value
        if isinstance(raw_value, (int, float)):
            if raw_value == 1:
                return True
            if raw_value == 0:
                return False
            return None

        text = str(raw_value).strip().lower()
        if text in {"1", "on", "true", "yes", "open", "opened", "active"}:
            return True
        if text in {"0", "off", "false", "no", "close", "closed", "inactive"}:
            return False
        return None

    def _extract_event_datetime(self, change: Mapping[str, Any]) -> Optional[datetime]:
        """Extract event datetime as timezone-aware UTC datetime."""
        for key in ("datetime", "date", "timestamp", "ts"):
            if key not in change:
                continue
            raw = change.get(key)
            if raw is None:
                return None

            if isinstance(raw, (int, float)):
                return datetime.fromtimestamp(float(raw), tz=timezone.utc)

            text = str(raw).strip()
            if not text:
                return None

            # Jeedom event::changes often carries datetime as epoch float string
            # (e.g. "1773522118.696700").
            try:
                epoch_value = float(text)
            except ValueError:
                epoch_value = None
            if epoch_value is not None:
                if epoch_value > 1e11:  # tolerate millisecond precision payloads
                    epoch_value = epoch_value / 1000.0
                return datetime.fromtimestamp(epoch_value, tz=timezone.utc)

            if " " in text and "T" not in text:
                text = text.replace(" ", "T")
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"

            try:
                parsed = datetime.fromisoformat(text)
            except ValueError:
                return None

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)

        return None

    def _format_cursor(self, dt: datetime) -> str:
        """Format cursor for Jeedom event::changes datetime param."""
        return f"{dt.astimezone(timezone.utc).timestamp():.6f}"

    def _log_sync(
        self,
        level: int,
        cmd_id: Any,
        reason_code: str,
        action: str,
        **extra: Any,
    ) -> None:
        """Emit structured [SYNC] runtime logs."""
        details = " ".join(f"{key}={value}" for key, value in extra.items())
        suffix = f" {details}" if details else ""
        _LOGGER.log(
            level,
            "[SYNC] cmd_id=%s reason_code=%s action=%s%s",
            cmd_id,
            reason_code,
            action,
            suffix,
        )
