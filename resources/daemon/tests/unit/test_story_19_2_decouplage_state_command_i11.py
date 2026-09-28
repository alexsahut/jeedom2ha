"""Story 19.2 — Invariant I11 decoupling: state streaming and command routing are
decided per candidate (principal or secondary), never inherited from the principal.

Reuses the eq628 multi-switch fixture (Story 11.3, ``test_story_11_3_iq_ev_pilotage``)
because it produces a real principal + several secondaries, each carrying its own
``reason_details['state_topic']``/``command_topic`` — the exact shape ``sync/state.py``
and ``sync/command.py`` consume via ``publication_decision_ref``.

AC1 — state streaming decoupled: principal refused / secondary published -> the
      secondary's state is still streamed (list_state_targets + handle_state_message).
AC2 — command routing decoupled: same scenario -> the secondary's command is still
      routed (handle_command_message).
AC3 — non-regression: covered separately by running
      test_story_13_3_metering_plug_secondary_sensors.py unmodified.
AC4 — anti-forced-coupling: principal published / one secondary refused -> that
      refused secondary is NEITHER streamed NOR routed (no "publish everything").
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from mapping.registry import MapperRegistry
from models.mapping import PublicationDecision
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from sync.command import CommandSynchronizer
from sync.state import StateSynchronizer


def _cmd(cmd_id, name, cmd_type, sub_type, generic_type=None, unit=None, value=None):
    return JeedomCmd(
        id=cmd_id,
        name=name,
        type=cmd_type,
        sub_type=sub_type,
        generic_type=generic_type,
        unit=unit,
        current_value=value,
    )


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-09-28T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Energie")},
        eq_logics={eq.id: eq},
    )


def _eq628() -> JeedomEqLogic:
    """Same fixture as test_story_11_3_iq_ev_pilotage: 1 principal + 3 secondaries,
    all structurally-equivalent SWITCH_* trios (multi-switch, Story 11.3)."""
    return JeedomEqLogic(
        id=628,
        name="Pilotage priorisation solaire",
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            _cmd(5977, "Filtration piscine", "info", "binary", "SWITCH_STATE", value="1"),
            _cmd(5978, "Filtration piscine On", "action", "other", "SWITCH_ON"),
            _cmd(5979, "Filtration piscine Off", "action", "other", "SWITCH_OFF"),
            _cmd(5980, "Chauffage piscine", "info", "binary", "SWITCH_STATE", value="0"),
            _cmd(5981, "Chauffage piscine On", "action", "other", "SWITCH_ON"),
            _cmd(5982, "Chauffage piscine Off", "action", "other", "SWITCH_OFF"),
            _cmd(5983, "Chauffage SPA", "info", "binary", "SWITCH_STATE", value="0"),
            _cmd(5984, "Chauffage SPA On", "action", "other", "SWITCH_ON"),
            _cmd(5985, "Chauffage SPA Off", "action", "other", "SWITCH_OFF"),
            _cmd(6004, "Charge voiture", "info", "binary", "SWITCH_STATE", value="1"),
            _cmd(6005, "Charge voiture On", "action", "other", "SWITCH_ON"),
            _cmd(6006, "Charge voiture Off", "action", "other", "SWITCH_OFF"),
            _cmd(5976, "Rafraichir", "action", "other"),
        ],
    )


def _decision_for(mapping, *, should_publish: bool) -> PublicationDecision:
    decision = PublicationDecision(
        should_publish=should_publish,
        reason="sure" if should_publish else "ambiguous_skipped",
        mapping_result=mapping,
        state_topic=mapping.reason_details["state_topic"],
        active_or_alive=True,
        discovery_published=should_publish,
    )
    mapping.publication_decision_ref = decision
    return decision


def _build_multi_switch(*, principal_should_publish: bool, refused_cmd_ids: frozenset[int] = frozenset()):
    """Build the eq628 principal + secondaries, each with its OWN decision.

    ``refused_cmd_ids`` overrides should_publish=False for the listed secondary
    SWITCH_STATE cmd ids (5980/5983/6004); every other candidate (principal
    included, governed by ``principal_should_publish``) is published.
    """
    eq = _eq628()
    primary = MapperRegistry().map(eq, _snapshot(eq))
    assert primary is not None and primary.additional_mappings, "eq628 fixture drifted: expected 3 secondaries"

    primary_decision = _decision_for(primary, should_publish=principal_should_publish)

    for secondary in primary.additional_mappings:
        cmd_id = secondary.reason_details["cmd_id"]
        _decision_for(secondary, should_publish=cmd_id not in refused_cmd_ids)

    return primary, primary_decision


class _FakeBridge:
    def __init__(self):
        self.is_connected = True
        self.published: list[tuple[str, str, int, bool]] = []

    def publish_message(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return True


# --- AC1 — state streaming decoupled from the principal's decision ---

def test_ac1_secondary_listed_as_state_target_despite_refused_principal():
    primary, primary_decision = _build_multi_switch(principal_should_publish=False)
    bridge = _FakeBridge()
    sync = StateSynchronizer({"publications": {628: primary_decision}}, bridge)

    target_cmd_ids = {t["cmd_id"] for t in sync.list_state_targets()}

    # Every published secondary is listed; the refused principal (5977) is not.
    assert target_cmd_ids == {5980, 5983, 6004}
    assert 5977 not in target_cmd_ids


@pytest.mark.asyncio
async def test_ac1_secondary_state_streamed_despite_refused_principal():
    primary, primary_decision = _build_multi_switch(principal_should_publish=False)
    bridge = _FakeBridge()
    sync = StateSynchronizer({"publications": {628: primary_decision}}, bridge)

    ok = await sync.handle_state_message(eq_id=628, cmd_id=5980, value="1")

    assert ok is True
    assert ("jeedom2ha/628/5980/state", "ON", 1, True) in bridge.published

    # The refused principal itself must still not stream (sanity check, not AC1's point).
    ok_principal = await sync.handle_state_message(eq_id=628, cmd_id=5977, value="1")
    assert ok_principal is False


# --- AC2 — command routing decoupled from the principal's decision ---

@pytest.mark.asyncio
async def test_ac2_secondary_command_routed_despite_refused_principal():
    primary, primary_decision = _build_multi_switch(principal_should_publish=False)
    bridge = MagicMock()
    bridge.is_connected = True

    sync = CommandSynchronizer(
        app={"publications": {628: primary_decision}, "state_synchronizer": None},
        mqtt_bridge=bridge,
        jeedom_api_endpoint="http://jeedom.test/core/api/jeeApi.php",
        jeedom_core_apikey="core-apikey",
    )
    sync._execute_exec_cmd = AsyncMock(return_value=True)

    ok = await sync.handle_command_message("jeedom2ha/628/5980/set", "ON")

    assert ok is True
    # "Chauffage piscine" SWITCH_ON command id is 5981.
    sync._execute_exec_cmd.assert_awaited_once_with(5981, {})


# --- AC4 — no forced coupling: a refused secondary stays refused ---

def test_ac4_refused_secondary_never_streamed_state():
    primary, primary_decision = _build_multi_switch(
        principal_should_publish=True,
        refused_cmd_ids=frozenset({5980}),
    )
    bridge = _FakeBridge()
    sync = StateSynchronizer({"publications": {628: primary_decision}}, bridge)

    target_cmd_ids = {t["cmd_id"] for t in sync.list_state_targets()}

    # Principal + the other two published secondaries stream; the refused one does not.
    assert target_cmd_ids == {5977, 5983, 6004}
    assert 5980 not in target_cmd_ids


@pytest.mark.asyncio
async def test_ac4_refused_secondary_never_streamed_state_via_handle_message():
    primary, primary_decision = _build_multi_switch(
        principal_should_publish=True,
        refused_cmd_ids=frozenset({5980}),
    )
    bridge = _FakeBridge()
    sync = StateSynchronizer({"publications": {628: primary_decision}}, bridge)

    ok = await sync.handle_state_message(eq_id=628, cmd_id=5980, value="1")

    assert ok is False
    assert bridge.published == []


@pytest.mark.asyncio
async def test_ac4_refused_secondary_never_routed_command():
    primary, primary_decision = _build_multi_switch(
        principal_should_publish=True,
        refused_cmd_ids=frozenset({5980}),
    )
    bridge = MagicMock()
    bridge.is_connected = True

    sync = CommandSynchronizer(
        app={"publications": {628: primary_decision}, "state_synchronizer": None},
        mqtt_bridge=bridge,
        jeedom_api_endpoint="http://jeedom.test/core/api/jeeApi.php",
        jeedom_core_apikey="core-apikey",
    )
    sync._execute_exec_cmd = AsyncMock(return_value=True)

    ok = await sync.handle_command_message("jeedom2ha/628/5980/set", "ON")

    assert ok is False
    sync._execute_exec_cmd.assert_not_awaited()

    # The principal and the other published secondaries stay routable (no
    # "all-or-nothing" side effect from the refused secondary).
    ok_principal = await sync.handle_command_message("jeedom2ha/628/5977/set", "ON")
    assert ok_principal is True
