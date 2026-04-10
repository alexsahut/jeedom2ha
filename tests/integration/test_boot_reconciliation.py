"""
test_boot_reconciliation.py — Integration tests for boot reconciliation (Stories 5.1 + 5.2).

Tests the full flow:
  - daemon restarts with a disk cache
  - /action/sync received with modified topology
  - correct publish/unpublish decisions based on diff boot_cache vs new topology

AC #5 (5.1): reconciliation cases:
  - new eq_id (absent from cache) → publish discovery
  - eq_id unchanged (same entity_type) → republish discovery (refresh retained)
  - eq_id disappeared (in cache, absent from new topology) → unpublish
  - eq_id with is_enable=false (was published) → unpublish (INV-11)
  - eq_id excluded → unpublish if was published

AC #7.3 (5.1): boot_cache is cleared after first sync

AC #7 (5.2): retypage at boot — entity_type changed during downtime
  - boot_cache entity_type="light", first sync maps eq_id as switch
    → unpublish_by_eq_id(eq_id, "light") BEFORE publish switch

AC #8 (5.2): unpublish fails at boot retypage → pending_discovery_unpublish populated,
  publish of new type continues normally
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


LOCAL_SECRET = "test-secret-integration"


def _make_sync_payload(eq_logics=None, objects=None):
    """Build a minimal /action/sync payload."""
    return {
        "payload": {
            "objects": objects or [{"id": 1, "name": "Salon", "father_id": None, "isVisible": True}],
            "eq_logics": eq_logics or [],
            "sync_config": {"confidence_policy": "sure_probable"},
        }
    }


def _make_eq_logic(eq_id, name="Lampe", is_enable=True, is_excluded=False, generic_types=None):
    """Build a minimal eqLogic entry."""
    generic_types = generic_types or ["LIGHT_STATE", "LIGHT_ON", "LIGHT_OFF"]
    cmds = [
        {"id": eq_id * 10 + i, "name": gt, "generic_type": gt,
         "type": "info" if "STATE" in gt else "action", "sub_type": "binary",
         "current_value": None, "unit": None, "is_visible": True, "is_historized": False}
        for i, gt in enumerate(generic_types)
    ]
    return {
        "id": eq_id,
        "name": name,
        "object_id": 1,
        "is_enable": is_enable,
        "is_visible": True,
        "eq_type": "virtualComponents",
        "generic_type": None,
        "is_excluded": is_excluded,
        "status": {},
        "cmds": cmds,
    }


@pytest.fixture
def http_app():
    from resources.daemon.transport.http_server import create_app
    return create_app(local_secret=LOCAL_SECRET)


@pytest.fixture
async def http_client(http_app, aiohttp_client):
    return await aiohttp_client(http_app)


def _post_sync_headers():
    return {"X-Local-Secret": LOCAL_SECRET, "Content-Type": "application/json"}


class TestBootReconciliationFirstSync:
    """AC #5 — reconciliation boot_cache vs new topology on first /action/sync."""

    async def test_new_eq_id_not_in_cache_gets_published(self, http_app, http_client):
        """New eq_id (absent from boot_cache) → publish discovery."""
        # Set up boot_cache with eq_id 100 only
        http_app["boot_cache"] = {}  # empty cache (cold start)

        # Mock the MQTT bridge as connected
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_message = MagicMock(return_value=True)
        http_app["mqtt_bridge"] = mock_bridge

        eq_logic = _make_eq_logic(eq_id=200, name="Nouvelle Lampe")
        payload = _make_sync_payload(eq_logics=[eq_logic])

        resp = await http_client.post(
            "/action/sync",
            json=payload,
            headers=_post_sync_headers(),
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "ok"

        # Verify eq_id 200 is now in publications
        assert 200 in http_app["publications"]
        decision = http_app["publications"][200]
        assert getattr(decision, "discovery_published", False) is True

    async def test_eq_id_disappeared_from_topology_gets_unpublished(self, http_app, http_client):
        """AC #5: eq_id in boot_cache (published) but absent from topology → unpublish (ghost-risk)."""
        # Boot cache has eq_id 999 as published
        http_app["boot_cache"] = {999: {"entity_type": "light", "published": True}}
        # mappings is empty (first sync)
        assert not http_app["mappings"]

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_message = MagicMock(return_value=True)
        http_app["mqtt_bridge"] = mock_bridge

        # Topology does NOT include eq_id 999
        eq_logic = _make_eq_logic(eq_id=100, name="Existing Lamp")
        payload = _make_sync_payload(eq_logics=[eq_logic])

        resp = await http_client.post(
            "/action/sync",
            json=payload,
            headers=_post_sync_headers(),
        )
        assert resp.status == 200

        # eq_id 999 should have been unpublished (empty retained payload)
        publish_calls = mock_bridge.publish_message.call_args_list
        unpublish_topics = [
            call.args[0] for call in publish_calls
            if len(call.args) >= 2 and call.args[1] == ""
        ]
        assert any("999" in topic for topic in unpublish_topics), (
            f"Expected unpublish for eq_id 999, got calls: {publish_calls}"
        )

    async def test_boot_cache_purged_after_first_sync(self, http_app, http_client):
        """AC #7.3: boot_cache is cleared (RAM) after first sync."""
        http_app["boot_cache"] = {123: {"entity_type": "light", "published": True}}

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_message = MagicMock(return_value=True)
        http_app["mqtt_bridge"] = mock_bridge

        payload = _make_sync_payload(eq_logics=[_make_eq_logic(eq_id=123)])

        resp = await http_client.post(
            "/action/sync",
            json=payload,
            headers=_post_sync_headers(),
        )
        assert resp.status == 200

        # boot_cache must be empty after first sync
        assert http_app["boot_cache"] == {}

    async def test_boot_cache_not_used_after_first_sync(self, http_app, http_client):
        """Second sync uses app['mappings'], not boot_cache."""
        http_app["boot_cache"] = {999: {"entity_type": "light", "published": True}}

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_message = MagicMock(return_value=True)
        http_app["mqtt_bridge"] = mock_bridge

        eq_logic = _make_eq_logic(eq_id=100)
        payload = _make_sync_payload(eq_logics=[eq_logic])

        # First sync: boot_cache used, then purged
        await http_client.post("/action/sync", json=payload, headers=_post_sync_headers())
        assert http_app["boot_cache"] == {}
        mock_bridge.publish_message.reset_mock()

        # Second sync: only eq_id 100 in mappings, no boot_cache involvement
        payload2 = _make_sync_payload(eq_logics=[eq_logic])
        await http_client.post("/action/sync", json=payload2, headers=_post_sync_headers())

        # No unexpected unpublish for eq_id 999 on second sync
        publish_calls = mock_bridge.publish_message.call_args_list
        unpublish_topics = [
            call.args[0] for call in publish_calls
            if len(call.args) >= 2 and call.args[1] == ""
        ]
        # eq_id 999 should not be unpublished again (already handled in first sync)
        unexpected = [t for t in unpublish_topics if "999" in t]
        assert not unexpected, f"Unexpected unpublish for 999 on second sync: {unexpected}"

    async def test_boot_sync_received_event_set_after_first_sync(self, http_app, http_client):
        """Story 5.1 — watchdog event is set after first sync."""
        http_app["boot_sync_received"] = asyncio.Event()
        assert not http_app["boot_sync_received"].is_set()

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_message = MagicMock(return_value=True)
        http_app["mqtt_bridge"] = mock_bridge

        payload = _make_sync_payload(eq_logics=[_make_eq_logic(eq_id=1)])
        await http_client.post("/action/sync", json=payload, headers=_post_sync_headers())

        assert http_app["boot_sync_received"].is_set()

    async def test_cache_saved_to_disk_after_sync(self, http_app, http_client, tmp_path):
        """AC #1: disk cache is written after /action/sync."""
        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_message = MagicMock(return_value=True)
        http_app["mqtt_bridge"] = mock_bridge
        http_app["boot_sync_received"] = asyncio.Event()

        eq_logic = _make_eq_logic(eq_id=42)
        payload = _make_sync_payload(eq_logics=[eq_logic])

        # Patch _DATA_DIR to tmp_path
        with patch("resources.daemon.transport.http_server._DATA_DIR", str(tmp_path)):
            await http_client.post("/action/sync", json=payload, headers=_post_sync_headers())

        cache_file = tmp_path / "jeedom2ha_cache.json"
        assert cache_file.exists()
        with open(cache_file, encoding="utf-8") as f:
            data = json.load(f)
        assert "42" in data


def _make_switch_eq_logic(eq_id, name="Prise"):
    """Build a minimal eqLogic that maps as switch (ENERGY_ON + ENERGY_OFF + ENERGY_STATE)."""
    cmds = [
        {"id": eq_id * 10 + 0, "name": "on", "generic_type": "ENERGY_ON",
         "type": "action", "sub_type": "other",
         "current_value": None, "unit": None, "is_visible": True, "is_historized": False},
        {"id": eq_id * 10 + 1, "name": "off", "generic_type": "ENERGY_OFF",
         "type": "action", "sub_type": "other",
         "current_value": None, "unit": None, "is_visible": True, "is_historized": False},
        {"id": eq_id * 10 + 2, "name": "state", "generic_type": "ENERGY_STATE",
         "type": "info", "sub_type": "binary",
         "current_value": None, "unit": None, "is_visible": True, "is_historized": False},
    ]
    return {
        "id": eq_id,
        "name": name,
        "object_id": 1,
        "is_enable": True,
        "is_visible": True,
        "eq_type": "virtualComponents",
        "generic_type": None,
        "is_excluded": False,
        "status": {},
        "cmds": cmds,
    }


class TestBootRetypageReconciliation:
    """AC #7, #8 (5.2) — Retypage detected at boot via boot_cache comparison."""

    async def test_retypage_boot_unpublishes_old_type_before_new_publish(self, http_app, http_client):
        """AC #7 — boot_cache light + first sync switch → unpublish light BEFORE publish switch."""
        eq_id = 55

        # Boot cache says eq was a light (published)
        http_app["boot_cache"] = {
            eq_id: {"entity_type": "light", "published": True, "ha_name": "Lampe"},
        }

        call_order = []

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True

        def _track_publish(topic, payload, **kwargs):
            if payload == "":
                call_order.append(("unpublish", topic))
            else:
                call_order.append(("publish", topic))
            return True

        mock_bridge.publish_message = MagicMock(side_effect=_track_publish)
        http_app["mqtt_bridge"] = mock_bridge

        # First sync maps eq_id as switch
        payload = _make_sync_payload(eq_logics=[_make_switch_eq_logic(eq_id=eq_id)])

        resp = await http_client.post(
            "/action/sync",
            json=payload,
            headers=_post_sync_headers(),
        )
        assert resp.status == 200

        # Filter calls for this eq_id
        unpublish_calls = [(action, topic) for action, topic in call_order
                          if str(eq_id) in topic and action == "unpublish"]
        publish_calls = [(action, topic) for action, topic in call_order
                         if str(eq_id) in topic and action == "publish"]

        # Unpublish of light must have occurred
        assert any("light" in topic for _, topic in unpublish_calls), (
            f"Expected light unpublish for eq_id={eq_id}. Calls: {call_order}"
        )

        # If both occurred, unpublish must come FIRST
        if publish_calls:
            first_unpublish_idx = next(
                (i for i, (a, t) in enumerate(call_order) if str(eq_id) in t and a == "unpublish"),
                None,
            )
            first_publish_idx = next(
                (i for i, (a, t) in enumerate(call_order) if str(eq_id) in t and a == "publish"),
                None,
            )
            assert first_unpublish_idx is not None
            assert first_publish_idx is not None
            assert first_unpublish_idx < first_publish_idx, (
                f"Unpublish must precede publish. Call order: {call_order}"
            )

    async def test_retypage_boot_logs_lifecycle_message(self, http_app, http_client, caplog):
        """AC #7 — retypage at boot emits [LIFECYCLE] log."""
        import logging as _logging
        eq_id = 56

        http_app["boot_cache"] = {
            eq_id: {"entity_type": "light", "published": True, "ha_name": "Lampe"},
        }

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_message = MagicMock(return_value=True)
        http_app["mqtt_bridge"] = mock_bridge

        payload = _make_sync_payload(eq_logics=[_make_switch_eq_logic(eq_id=eq_id)])

        with caplog.at_level(_logging.INFO, logger="resources.daemon.transport.http_server"):
            resp = await http_client.post(
                "/action/sync",
                json=payload,
                headers=_post_sync_headers(),
            )

        assert resp.status == 200
        assert any(
            "[LIFECYCLE]" in r.message and "retypage" in r.message and "boot" in r.message
            for r in caplog.records
        ), f"Expected boot retypage log. Got: {[r.message for r in caplog.records if '[LIFECYCLE]' in r.message]}"

    async def test_retypage_boot_unpublish_fail_defers_and_publish_continues(self, http_app, http_client):
        """AC #8 — broker fails on unpublish → pending_discovery_unpublish populated, switch published."""
        eq_id = 57

        http_app["boot_cache"] = {
            eq_id: {"entity_type": "light", "published": True, "ha_name": "Lampe"},
        }

        # Simulate: unpublish (empty payload) fails, regular publish succeeds
        def _selective_publish(topic, payload, **kwargs):
            if payload == "":
                return False  # Broker fails for unpublish
            return True

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_message = MagicMock(side_effect=_selective_publish)
        http_app["mqtt_bridge"] = mock_bridge

        payload = _make_sync_payload(eq_logics=[_make_switch_eq_logic(eq_id=eq_id)])

        resp = await http_client.post(
            "/action/sync",
            json=payload,
            headers=_post_sync_headers(),
        )
        assert resp.status == 200

        # Pending unpublish must be populated for eq_id
        pending = http_app["pending_discovery_unpublish"]
        assert pending.get(eq_id) == "light", (
            f"Expected pending unpublish for eq_id={eq_id} with 'light'. Got: {pending}"
        )

        # Switch must have been published (publish call with non-empty payload for switch topic)
        publish_calls = mock_bridge.publish_message.call_args_list
        switch_publish = [
            call for call in publish_calls
            if len(call.args) >= 2 and call.args[1] != "" and "switch" in call.args[0]
            and str(eq_id) in call.args[0]
        ]
        assert switch_publish, (
            f"Expected switch publish for eq_id={eq_id}. Calls: {publish_calls}"
        )

    async def test_no_retypage_boot_when_type_unchanged(self, http_app, http_client):
        """No retypage when boot_cache entity_type matches new mapping type."""
        eq_id = 58

        # Boot cache already says 'light'
        http_app["boot_cache"] = {
            eq_id: {"entity_type": "light", "published": True, "ha_name": "Lampe"},
        }

        mock_bridge = MagicMock()
        mock_bridge.is_connected = True
        mock_bridge.publish_message = MagicMock(return_value=True)
        http_app["mqtt_bridge"] = mock_bridge

        # First sync also maps as light
        payload = _make_sync_payload(eq_logics=[_make_eq_logic(eq_id=eq_id)])

        resp = await http_client.post(
            "/action/sync",
            json=payload,
            headers=_post_sync_headers(),
        )
        assert resp.status == 200

        # No light discovery unpublish should have been done specifically for retypage
        publish_calls = mock_bridge.publish_message.call_args_list
        retypage_unpublish = [
            call for call in publish_calls
            if len(call.args) >= 2 and call.args[1] == ""
            and "light" in call.args[0] and str(eq_id) in call.args[0]
        ]
        # light might be republished (retained refresh), but not unpublished via retypage
        # The eq_id is still alive so no suppression unpublish either
        assert not retypage_unpublish, (
            f"Unexpected retypage unpublish for eq_id={eq_id}: {retypage_unpublish}"
        )
