"""Readback contract shared by discovery, state streaming and command sync (Story 23.3).

Single source of truth for "which Jeedom info command feeds which MQTT state topic"
of an actionable entity (switch / light / cover). Discovery (``optimistic``),
``StateSynchronizer`` (what is streamed) and ``CommandSynchronizer`` (when the
optimistic publish is suppressed) all read it, so they cannot drift apart.

Reliability is evaluated PER CHANNEL, never globally:
- ``state``      : ON/OFF (light, switch) or open/closed (cover);
- ``brightness`` : light brightness 0-100;
- ``position``   : cover position 0-100.
A brightness-only light does NOT have a reliable ON/OFF channel (Q4: no ON/OFF is
invented from a brightness value), and a position never makes ``state`` reliable on
its own.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

from mapping.valve import VALVE_STATE_KEYS  # Story 24.8
from mapping.lock import LOCK_POLARITY_NUKI, LOCK_POLARITY_STANDARD, LOCK_STATE_KEYS  # Story 24.9
from mapping.climate import (  # Story 24.15
    CHANNEL_ACTION,
    CHANNEL_CURRENT_TEMPERATURE,
    CHANNEL_MODE,
    CHANNEL_PRESET,
    CHANNEL_SETPOINT,
    HA_PRESET_NONE,
    THERMOSTAT_LOCK,
    THERMOSTAT_MODE,
    THERMOSTAT_SETPOINT,
    THERMOSTAT_STATE,
    THERMOSTAT_TEMPERATURE,
)

CHANNEL_STATE = "state"
CHANNEL_BRIGHTNESS = "brightness"
CHANNEL_POSITION = "position"

# ON/OFF (or open/closed) readback keys per actionable type. ``switch`` carries two
# shapes: ENERGY_STATE/SWITCH_STATE and PRESENCE (Story 10.7).
STATE_KEYS: Dict[str, Tuple[str, ...]] = {
    "switch": ("ENERGY_STATE", "SWITCH_STATE", "PRESENCE"),
    "light": ("LIGHT_STATE",),
    "cover": ("FLAP_STATE", "FLAP_BSO_STATE"),
    # Story 24.8 — open/closed of a valve: the STATE of its trio (single source:
    # ``mapping.valve.VALVE_STATE_KEYS``, Homebridge types frozen in Task 0).
    "valve": VALVE_STATE_KEYS,
    # Story 24.9 — locked/unlocked/jammed of a lock: its LOCK_STATE (mapping.lock).
    "lock": LOCK_STATE_KEYS,
}
# Story 24.15 (D4 A) — the lock of a thermostat is a ``switch`` fed by ``THERMOSTAT_LOCK``
# (only the « Verrouillage » switch of ``mapping.climate`` carries this key).
STATE_KEYS["switch"] = STATE_KEYS["switch"] + (THERMOSTAT_LOCK,)
# Story 24.17 (D2-a) — a FAN_* trio published as ``switch`` (14.1) is fed by its FAN_STATE.
STATE_KEYS["switch"] = STATE_KEYS["switch"] + ("FAN_STATE",)
# Story 24.15 — info commands of a ``climate`` (channels: ``climate_readback_commands``).
CLIMATE_READBACK_KEYS: Tuple[str, ...] = (
    THERMOSTAT_SETPOINT, THERMOSTAT_TEMPERATURE, THERMOSTAT_MODE, THERMOSTAT_STATE,
)
BRIGHTNESS_KEYS: Tuple[str, ...] = ("LIGHT_BRIGHTNESS",)
# LIGHT_BRIGHTNESS feeds the brightness; a numeric LIGHT_STATE is the fallback (see
# ``readback_commands``). A numeric FLAP_STATE is the cover position (``_detect_position`` in mapping/cover.py).
POSITION_KEYS: Tuple[str, ...] = ("FLAP_STATE",)
# Story 24.7 — state of a gate / garage ``cover``: a NUMERIC info at the barrier
# convention (0 closed, 252 closing, 253 stopped, 254 opening, 255 open). Only read
# when the cover has no FLAP_* state; a binary one is never a cover readback (D1).
BARRIER_STATE_KEYS: Tuple[str, ...] = ("BARRIER_STATE", "GARAGE_STATE")


def is_info_command(cmd: Any) -> bool:
    """A readback command must be an ``info``; a missing ``type`` defaults to info."""
    return cmd is not None and str(getattr(cmd, "type", "info")).lower() == "info"


def _first_info(commands: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[Any]:
    for key in keys:
        cmd = commands.get(key)
        if is_info_command(cmd):
            return cmd
    return None


def _is_numeric(cmd: Any) -> bool:
    return str(getattr(cmd, "sub_type", "")).lower() == "numeric"


def readback_commands(ha_type: Any, mapping: Any) -> List[Tuple[str, Any]]:
    """Return the ``(channel, info_command)`` pairs that feed a candidate's topics.

    Order is stable: ``state`` first, then ``brightness`` / ``position``. A channel is
    present only if discovery declares its topic AND an ``info`` command can feed it.
    """
    commands = getattr(mapping, "commands", None) or {}
    caps = getattr(mapping, "capabilities", None)
    channels: List[Tuple[str, Any]] = []

    if ha_type == "climate":
        return climate_readback_commands(mapping)  # Story 24.15

    state_keys = STATE_KEYS.get(ha_type)
    if state_keys is None:
        return channels

    state_cmd = _first_info(commands, state_keys)
    if state_cmd is None and ha_type == "cover":
        barrier_cmd = _first_info(commands, BARRIER_STATE_KEYS)
        if barrier_cmd is not None and _is_numeric(barrier_cmd):
            state_cmd = barrier_cmd  # Story 24.7 (D1)
    if state_cmd is not None:
        channels.append((CHANNEL_STATE, state_cmd))

    if ha_type == "light" and getattr(caps, "has_brightness", False):
        brightness_cmd = _first_info(commands, BRIGHTNESS_KEYS)
        if brightness_cmd is None and state_cmd is not None and _is_numeric(state_cmd):
            # A numeric LIGHT_STATE is the dimmer level (mapping/light.py
            # ``state_numeric_as_brightness``): it feeds the brightness topic too, like a
            # numeric FLAP_STATE feeds the cover position. A binary one never does.
            brightness_cmd = state_cmd
        if brightness_cmd is not None:
            channels.append((CHANNEL_BRIGHTNESS, brightness_cmd))

    if ha_type == "cover" and getattr(caps, "has_position", False):
        position_cmd = _first_info(commands, POSITION_KEYS)
        if position_cmd is not None and _is_numeric(position_cmd):
            channels.append((CHANNEL_POSITION, position_cmd))

    return channels


def is_barrier_state_command(cmd: Any) -> bool:
    """Story 24.7 — a numeric BARRIER_STATE / GARAGE_STATE info (barrier convention)."""
    return (
        is_info_command(cmd)
        and getattr(cmd, "generic_type", None) in BARRIER_STATE_KEYS
        and _is_numeric(cmd)
    )


# Story 24.7 (D1) — barrier numeric value -> HA MQTT cover state payload (defaults of
# ``state_closed`` / ``state_closing`` / ``state_stopped`` / ``state_opening`` / ``state_open``).
BARRIER_STATE_TABLE: Dict[int, str] = {
    0: "closed",
    252: "closing",
    253: "stopped",
    254: "opening",
    255: "open",
}


BARRIER_MODES: Tuple[str, ...] = ("direct", "toggle_on_state")


def barrier_mode(mapping: Any) -> Optional[str]:
    """Story 24.7 (M1) — the single source of the barrier nature of a ``cover``.

    ``reason_details["barrier_mode"]`` set by ``CoverMapper._map_barrier``; read by the
    discovery (``device_class``, no stop) and the command sync (order routing). None for
    every other mapping (FLAP_* covers, overrides from another type).
    """
    if getattr(mapping, "ha_entity_type", None) != "cover":
        return None
    mode = (getattr(mapping, "reason_details", None) or {}).get("barrier_mode")
    return mode if mode in BARRIER_MODES else None


# M-3 — only a plain decimal integer (optionally ``.0`` / ``,0``) is a barrier value:
# no sign, no exponent (``2.55e2``), no fraction.
_BARRIER_VALUE_RE = re.compile(r"(\d+)(?:[.,]0+)?")


def barrier_state(value: Any) -> Optional[str]:
    """Translate a barrier value to its cover state; anything else -> None (never invented)."""
    if value is None or isinstance(value, bool):
        return None
    match = _BARRIER_VALUE_RE.fullmatch(str(value).strip())
    if match is None:
        return None
    return BARRIER_STATE_TABLE.get(int(match.group(1)))


# Story 24.8 (D4) — binary STATE of a valve -> HA MQTT valve state (``state_open: open`` /
# ``state_closed: closed``). Anything else publishes nothing (never invented).
_VALVE_OPEN_VALUES = frozenset({"1", "true", "on", "open", "opened"})
_VALVE_CLOSED_VALUES = frozenset({"0", "false", "off", "closed", "close"})


def valve_state(value: Any, invert_binary: bool = False) -> Optional[str]:
    """Translate a valve STATE value to ``open`` / ``closed``; unknown -> None.

    ``invert_binary`` is the Jeedom display option ``invertBinary`` of the STATE command
    (exported in the topology as ``invert_binary``): applied to the result (1, or any
    number > 0, then means closed). A numeric state reads 0 = closed, > 0 = open.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        value = "1" if value else "0"
    text = str(value).strip().lower()
    if text in _VALVE_OPEN_VALUES:
        is_open = True
    elif text in _VALVE_CLOSED_VALUES:
        is_open = False
    else:
        # Numeric state: 0 = closed, > 0 = open (e.g. a flow or an opening level);
        # negative or non-finite -> nothing.
        try:
            number = float(text.replace(",", "."))
        except ValueError:
            return None
        if not math.isfinite(number) or number < 0:
            return None
        is_open = number > 0
    if invert_binary:
        is_open = not is_open
    return "open" if is_open else "closed"


# Story 24.9 (D1) — LOCK_STATE value -> HA MQTT lock state (``state_locked: LOCKED`` /
# ``state_unlocked: UNLOCKED`` / ``state_jammed: JAMMED``), Homebridge polarity
# (``LockCurrentState``). Anything else publishes nothing (never invented).
_LOCK_TRUE_VALUES = frozenset({"1", "true", "on"})
_LOCK_FALSE_VALUES = frozenset({"0", "false", "off"})
_LOCK_NUKI_TABLE = {"0": "LOCKED", "1": "UNLOCKED", "2": "JAMMED"}


def lock_state(value: Any, polarity: Any) -> Optional[str]:
    """Translate a ``LOCK_STATE`` value to ``LOCKED`` / ``UNLOCKED`` / ``JAMMED``; else None.

    ``standard`` polarity (general case): true value = locked, false value = unlocked.
    ``nuki`` polarity: 0 = locked, 1 = unlocked, 2 = jammed. An unknown polarity, or a
    value outside these tables, gives None: no state is published.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        value = "1" if value else "0"
    text = str(value).strip().lower()
    if polarity == LOCK_POLARITY_NUKI:
        # Integer forms only ("1", "1.0"); never a rounding of another number.
        try:
            number = float(text.replace(",", "."))
        except ValueError:
            return None
        if not math.isfinite(number) or number != int(number):
            return None
        return _LOCK_NUKI_TABLE.get(str(int(number)))
    if polarity != LOCK_POLARITY_STANDARD:
        return None
    if text in _LOCK_TRUE_VALUES:
        return "LOCKED"
    if text in _LOCK_FALSE_VALUES:
        return "UNLOCKED"
    try:
        number = float(text.replace(",", "."))
    except ValueError:
        return None
    if number == 1:
        return "LOCKED"
    if number == 0:
        return "UNLOCKED"
    return None


def climate_readback_commands(mapping: Any) -> List[Tuple[str, Any]]:
    """Story 24.15 — ``(channel, info_command)`` feeds of a ``climate``.

    ``setpoint`` <- ``THERMOSTAT_SETPOINT``, ``current_temperature`` <- ``THERMOSTAT_TEMPERATURE``,
    ``mode`` / ``preset`` <- ``THERMOSTAT_MODE``, ``action`` <- ``THERMOSTAT_STATE`` AND
    ``THERMOSTAT_MODE`` (a mode change republishes the action: the stop wins, D2). A channel
    is present only when the discovery declares its topic (capabilities of the mapper).
    """
    commands = getattr(mapping, "commands", None) or {}
    caps = getattr(mapping, "capabilities", None)
    channels: List[Tuple[str, Any]] = []
    setpoint_cmd = commands.get(THERMOSTAT_SETPOINT)
    if getattr(caps, "has_setpoint_state", False) and is_info_command(setpoint_cmd):
        channels.append((CHANNEL_SETPOINT, setpoint_cmd))
    temperature_cmd = commands.get(THERMOSTAT_TEMPERATURE)
    if getattr(caps, "has_current_temperature", False) and is_info_command(temperature_cmd):
        channels.append((CHANNEL_CURRENT_TEMPERATURE, temperature_cmd))
    mode_cmd = commands.get(THERMOSTAT_MODE)
    if not (getattr(caps, "has_mode", False) and is_info_command(mode_cmd)):
        mode_cmd = None
    if mode_cmd is not None:
        channels.append((CHANNEL_MODE, mode_cmd))
        if getattr(caps, "has_presets", False):
            channels.append((CHANNEL_PRESET, mode_cmd))
    state_cmd = commands.get(THERMOSTAT_STATE)
    if getattr(caps, "has_action", False) and is_info_command(state_cmd):
        channels.append((CHANNEL_ACTION, state_cmd))
        if mode_cmd is not None:
            channels.append((CHANNEL_ACTION, mode_cmd))
    return channels


def climate_number(value: Any) -> Optional[str]:
    """Story 24.15 — a temperature or setpoint value: finite number, ``,`` read as ``.``."""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(",", ".")
    try:
        number = float(text)
    except ValueError:
        return None
    return text if math.isfinite(number) else None


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def climate_hvac_mode(value: Any, off_mode_name: Optional[str]) -> Optional[str]:
    """Story 24.15 (D1) — ``THERMOSTAT_MODE`` value -> ``off`` / ``heat``; blank -> None.

    ``off`` only when the value is exactly the name of the stop order (identified by its
    logical id in the mapper); any other value (a named mode, « no mode », unknown) is
    ``heat``: the thermostat regulates.
    """
    if _is_blank(value):
        return None
    if off_mode_name is not None and str(value) == off_mode_name:
        return "off"
    return "heat"


def climate_preset(value: Any, preset_modes: Any) -> Optional[str]:
    """Story 24.15 (D1) — ``THERMOSTAT_MODE`` value -> its preset, else ``none``; blank -> None."""
    if _is_blank(value):
        return None
    text = str(value)
    return text if text in list(preset_modes or []) else HA_PRESET_NONE


_CLIMATE_HEATING_VALUES = frozenset({"1", "true", "on"})
_CLIMATE_IDLE_VALUES = frozenset({"0", "false", "off"})


def climate_action(state_value: Any, mode_value: Any, off_mode_name: Optional[str]) -> Optional[str]:
    """Story 24.15 (D2) — ``off`` when the mode is the stop, else ``THERMOSTAT_STATE``:
    true -> ``heating``, false -> ``idle``; anything else -> None (nothing published).
    """
    if climate_hvac_mode(mode_value, off_mode_name) == "off":
        return "off"
    if state_value is None:
        return None
    if isinstance(state_value, bool):
        return "heating" if state_value else "idle"
    text = str(state_value).strip().lower()
    if text in _CLIMATE_HEATING_VALUES:
        return "heating"
    if text in _CLIMATE_IDLE_VALUES:
        return "idle"
    try:
        number = float(text.replace(",", "."))
    except ValueError:
        return None
    if number == 1:
        return "heating"
    if number == 0:
        return "idle"
    return None


def has_reliable_channel(ha_type: Any, mapping: Any, channel: str) -> bool:
    """True when ``channel`` of the candidate is fed by a real Jeedom info command."""
    return any(name == channel for name, _cmd in readback_commands(ha_type, mapping))


def channel_topic(state_topic: str, channel: str) -> str:
    """Derive the brightness/position topic from the registry ``state_topic``.

    Discovery declares ``jeedom2ha/{eq}/state``, ``…/brightness`` and ``…/position``
    side by side; the secondary topics are derived from the registry topic, not
    rebuilt from ``eq_id`` by hand.
    """
    if channel == CHANNEL_STATE:
        return state_topic
    base, _sep, _last = state_topic.rpartition("/")
    return f"{base}/{channel}"
