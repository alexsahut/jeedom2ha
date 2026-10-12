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
