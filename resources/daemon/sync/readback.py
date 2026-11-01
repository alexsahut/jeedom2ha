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

from typing import Any, Dict, List, Optional, Tuple

CHANNEL_STATE = "state"
CHANNEL_BRIGHTNESS = "brightness"
CHANNEL_POSITION = "position"

# ON/OFF (or open/closed) readback keys per actionable type. ``switch`` carries two
# shapes: ENERGY_STATE/SWITCH_STATE and PRESENCE (Story 10.7).
STATE_KEYS: Dict[str, Tuple[str, ...]] = {
    "switch": ("ENERGY_STATE", "SWITCH_STATE", "PRESENCE"),
    "light": ("LIGHT_STATE",),
    "cover": ("FLAP_STATE", "FLAP_BSO_STATE"),
}
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


def barrier_state(value: Any) -> Optional[str]:
    """Translate a barrier value to its cover state; anything else -> None (never invented)."""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        number = float(text.replace(",", "."))
    except ValueError:
        return None
    if not number.is_integer():
        return None
    return BARRIER_STATE_TABLE.get(int(number))


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
