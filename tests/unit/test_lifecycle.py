"""
test_lifecycle.py — Unit tests for the _detect_lifecycle_changes helper (Story 5.2).

AC covered:
  - AC #1, #2 — Rename runtime: log [LIFECYCLE].*rename détecté; topic/unique_id unchanged
  - AC #3    — Rename boot: log [LIFECYCLE].*rename détecté depuis boot_cache
  - AC #4, #5 — Area change: log [LIFECYCLE].*area change; unique_id unchanged
  - AC #6, #8 — Retypage runtime: unpublish_by_eq_id(X, old_type) called BEFORE publish;
                if unpublish fails → pending_discovery_unpublish populated; publish continues
  - AC #11   — INV-4: unique_id = "jeedom2ha_eq_{id}" invariant in all cases
"""
import asyncio
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mapping(entity_type="light", ha_name="Lampe", suggested_area="Salon", eq_id=1):
    """Minimal MappingResult-like object."""
    m = MagicMock()
    m.ha_entity_type = entity_type
    m.ha_name = ha_name
    m.suggested_area = suggested_area
    m.ha_unique_id = f"jeedom2ha_eq_{eq_id}"
    m.jeedom_eq_id = eq_id
    return m


def _make_previous_decision(entity_type="light", ha_name="Lampe", suggested_area="Salon",
                              discovery_published=True, should_publish=True):
    """Minimal PublicationDecision-like object with a mapping_result."""
    prev_mapping = MagicMock()
    prev_mapping.ha_entity_type = entity_type
    prev_mapping.ha_name = ha_name
    prev_mapping.suggested_area = suggested_area

    decision = MagicMock()
    decision.mapping_result = prev_mapping
    decision.discovery_published = discovery_published
    decision.should_publish = should_publish
    return decision


def _make_publisher(unpublish_ok=True):
    """Minimal async publisher mock."""
    publisher = MagicMock()
    publisher.unpublish_by_eq_id = AsyncMock(return_value=unpublish_ok)
    return publisher


async def _call_helper(eq_id=1, mapping=None, previous_decision=None, boot_cache=None,
                       is_first_sync=False, publisher=None, pending=None):
    """Convenience wrapper to call _detect_lifecycle_changes."""
    from resources.daemon.transport.http_server import _detect_lifecycle_changes

    if mapping is None:
        mapping = _make_mapping(eq_id=eq_id)
    if boot_cache is None:
        boot_cache = {}
    if pending is None:
        pending = {}

    await _detect_lifecycle_changes(
        eq_id=eq_id,
        mapping=mapping,
        previous_decision=previous_decision,
        boot_cache=boot_cache,
        is_first_sync=is_first_sync,
        publisher=publisher,
        pending_discovery_unpublish=pending,
    )
    return pending


# ---------------------------------------------------------------------------
# AC #1, #2 — Rename runtime
# ---------------------------------------------------------------------------

class TestRenameRuntime:
    """AC #1, #2, #11 — Rename détecté au runtime, unique_id inchangé."""

    async def test_rename_runtime_logs_lifecycle_message(self, caplog):
        """Rename runtime → log INFO [LIFECYCLE].*rename détecté."""
        prev = _make_previous_decision(ha_name="Lampe Salon")
        mapping = _make_mapping(ha_name="Plafonnier Salon", eq_id=5)

        with caplog.at_level(logging.INFO, logger="resources.daemon.transport.http_server"):
            await _call_helper(eq_id=5, mapping=mapping, previous_decision=prev)

        assert any(
            "[LIFECYCLE]" in r.message and "rename détecté" in r.message
            for r in caplog.records
        ), f"Expected rename log, got: {[r.message for r in caplog.records]}"

    async def test_rename_runtime_log_contains_old_and_new_names(self, caplog):
        """Log message must contain old and new name values."""
        prev = _make_previous_decision(ha_name="Lampe Salon")
        mapping = _make_mapping(ha_name="Plafonnier Salon", eq_id=5)

        with caplog.at_level(logging.INFO, logger="resources.daemon.transport.http_server"):
            await _call_helper(eq_id=5, mapping=mapping, previous_decision=prev)

        rename_logs = [r.message for r in caplog.records if "rename détecté" in r.message]
        assert rename_logs
        assert "Lampe Salon" in rename_logs[0]
        assert "Plafonnier Salon" in rename_logs[0]

    async def test_rename_runtime_unique_id_invariant(self):
        """AC #11 — unique_id in mapping is never modified by the helper."""
        prev = _make_previous_decision(ha_name="Avant")
        mapping = _make_mapping(ha_name="Après", eq_id=7)
        original_uid = mapping.ha_unique_id

        await _call_helper(eq_id=7, mapping=mapping, previous_decision=prev)

        assert mapping.ha_unique_id == original_uid
        assert mapping.ha_unique_id == "jeedom2ha_eq_7"

    async def test_no_rename_no_log(self, caplog):
        """Same name → no [LIFECYCLE] rename log."""
        prev = _make_previous_decision(ha_name="Lampe")
        mapping = _make_mapping(ha_name="Lampe", eq_id=1)

        with caplog.at_level(logging.INFO, logger="resources.daemon.transport.http_server"):
            await _call_helper(eq_id=1, mapping=mapping, previous_decision=prev)

        assert not any("rename" in r.message for r in caplog.records)

    async def test_no_previous_decision_no_rename_log(self, caplog):
        """No previous_decision (first sync) → no runtime rename log."""
        mapping = _make_mapping(ha_name="Lampe", eq_id=1)

        with caplog.at_level(logging.INFO, logger="resources.daemon.transport.http_server"):
            await _call_helper(eq_id=1, mapping=mapping, previous_decision=None)

        assert not any("rename détecté" in r.message and "boot_cache" not in r.message
                       for r in caplog.records)


# ---------------------------------------------------------------------------
# AC #4, #5 — Area change runtime
# ---------------------------------------------------------------------------

class TestAreaChangeRuntime:
    """AC #4, #5 — Area change détecté au runtime."""

    async def test_area_change_runtime_logs_lifecycle_message(self, caplog):
        """Area change → log INFO [LIFECYCLE].*area change."""
        prev = _make_previous_decision(suggested_area="Salon")
        mapping = _make_mapping(suggested_area="Séjour", eq_id=3)

        with caplog.at_level(logging.INFO, logger="resources.daemon.transport.http_server"):
            await _call_helper(eq_id=3, mapping=mapping, previous_decision=prev)

        assert any(
            "[LIFECYCLE]" in r.message and "area change" in r.message
            for r in caplog.records
        ), f"Expected area change log, got: {[r.message for r in caplog.records]}"

    async def test_area_change_log_contains_old_and_new_area(self, caplog):
        """Log must contain old and new area values."""
        prev = _make_previous_decision(suggested_area="Salon")
        mapping = _make_mapping(suggested_area="Séjour", eq_id=3)

        with caplog.at_level(logging.INFO, logger="resources.daemon.transport.http_server"):
            await _call_helper(eq_id=3, mapping=mapping, previous_decision=prev)

        area_logs = [r.message for r in caplog.records if "area change" in r.message]
        assert area_logs
        assert "Salon" in area_logs[0]
        assert "Séjour" in area_logs[0]

    async def test_area_change_unique_id_invariant(self):
        """AC #11 — unique_id unchanged on area change."""
        prev = _make_previous_decision(suggested_area="Salon")
        mapping = _make_mapping(suggested_area="Séjour", eq_id=3)
        original_uid = mapping.ha_unique_id

        await _call_helper(eq_id=3, mapping=mapping, previous_decision=prev)

        assert mapping.ha_unique_id == original_uid

    async def test_no_area_change_no_log(self, caplog):
        """Same area → no area change log."""
        prev = _make_previous_decision(suggested_area="Salon")
        mapping = _make_mapping(suggested_area="Salon", eq_id=1)

        with caplog.at_level(logging.INFO, logger="resources.daemon.transport.http_server"):
            await _call_helper(eq_id=1, mapping=mapping, previous_decision=prev)

        assert not any("area change" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# AC #6, #8 — Retypage runtime
# ---------------------------------------------------------------------------

class TestRetypageRuntime:
    """AC #6, #8 — Retypage runtime: unpublish old type AVANT publish new type."""

    async def test_retypage_runtime_calls_unpublish(self):
        """Retypage detected → publisher.unpublish_by_eq_id(eq_id, old_type) called."""
        publisher = _make_publisher(unpublish_ok=True)
        prev = _make_previous_decision(entity_type="light", discovery_published=True)
        mapping = _make_mapping(entity_type="switch", eq_id=10)

        await _call_helper(eq_id=10, mapping=mapping, previous_decision=prev, publisher=publisher)

        publisher.unpublish_by_eq_id.assert_called_once_with(10, entity_type="light")

    async def test_retypage_runtime_logs_retypage_message(self, caplog):
        """Retypage → log INFO [LIFECYCLE].*retypage détecté."""
        publisher = _make_publisher(unpublish_ok=True)
        prev = _make_previous_decision(entity_type="light", discovery_published=True)
        mapping = _make_mapping(entity_type="switch", eq_id=10)

        with caplog.at_level(logging.INFO, logger="resources.daemon.transport.http_server"):
            await _call_helper(eq_id=10, mapping=mapping, previous_decision=prev, publisher=publisher)

        assert any(
            "[LIFECYCLE]" in r.message and "retypage" in r.message
            for r in caplog.records
        )

    async def test_retypage_runtime_logs_contains_old_and_new_type(self, caplog):
        """Retypage log must mention old and new entity types."""
        publisher = _make_publisher(unpublish_ok=True)
        prev = _make_previous_decision(entity_type="light", discovery_published=True)
        mapping = _make_mapping(entity_type="switch", eq_id=10)

        with caplog.at_level(logging.INFO, logger="resources.daemon.transport.http_server"):
            await _call_helper(eq_id=10, mapping=mapping, previous_decision=prev, publisher=publisher)

        retypage_logs = [r.message for r in caplog.records if "retypage" in r.message]
        assert retypage_logs
        assert "light" in retypage_logs[0]
        assert "switch" in retypage_logs[0]

    async def test_retypage_runtime_unpublish_fail_defers(self):
        """AC #8 — unpublish fails → pending populated, no exception raised."""
        publisher = _make_publisher(unpublish_ok=False)
        prev = _make_previous_decision(entity_type="light", discovery_published=True)
        mapping = _make_mapping(entity_type="switch", eq_id=10)
        pending = {}

        await _call_helper(eq_id=10, mapping=mapping, previous_decision=prev,
                           publisher=publisher, pending=pending)

        assert pending.get(10) == "light"

    async def test_retypage_runtime_no_publisher_defers(self):
        """AC #8 — publisher=None → deferred into pending, no crash."""
        prev = _make_previous_decision(entity_type="light", discovery_published=True)
        mapping = _make_mapping(entity_type="switch", eq_id=10)
        pending = {}

        await _call_helper(eq_id=10, mapping=mapping, previous_decision=prev,
                           publisher=None, pending=pending)

        assert pending.get(10) == "light"

    async def test_no_retypage_if_not_published(self):
        """Retypage not triggered if entity was never published (discovery_published=False)."""
        publisher = _make_publisher(unpublish_ok=True)
        prev = _make_previous_decision(entity_type="light", discovery_published=False, should_publish=False)
        mapping = _make_mapping(entity_type="switch", eq_id=10)

        await _call_helper(eq_id=10, mapping=mapping, previous_decision=prev, publisher=publisher)

        publisher.unpublish_by_eq_id.assert_not_called()

    async def test_retypage_runtime_unique_id_invariant(self):
        """AC #11 — unique_id unchanged on retypage."""
        publisher = _make_publisher(unpublish_ok=True)
        prev = _make_previous_decision(entity_type="light", discovery_published=True)
        mapping = _make_mapping(entity_type="switch", eq_id=10)
        original_uid = mapping.ha_unique_id

        await _call_helper(eq_id=10, mapping=mapping, previous_decision=prev, publisher=publisher)

        assert mapping.ha_unique_id == original_uid
        assert mapping.ha_unique_id == "jeedom2ha_eq_10"


# ---------------------------------------------------------------------------
# AC #3 — Rename boot cache
# ---------------------------------------------------------------------------

class TestRenameBootCache:
    """AC #3 — Rename détecté depuis boot_cache."""

    async def test_rename_boot_logs_boot_cache_message(self, caplog):
        """boot_cache ha_name differs from new mapping → log [LIFECYCLE].*rename détecté depuis boot_cache."""
        boot_cache = {5: {"entity_type": "light", "published": True, "ha_name": "Lampe Salon"}}
        mapping = _make_mapping(ha_name="Plafonnier Salon", entity_type="light", eq_id=5)

        with caplog.at_level(logging.INFO, logger="resources.daemon.transport.http_server"):
            await _call_helper(eq_id=5, mapping=mapping, previous_decision=None,
                               boot_cache=boot_cache, is_first_sync=True)

        assert any(
            "[LIFECYCLE]" in r.message and "rename détecté depuis boot_cache" in r.message
            for r in caplog.records
        ), f"Expected boot rename log, got: {[r.message for r in caplog.records]}"

    async def test_rename_boot_log_contains_old_and_new_names(self, caplog):
        """Boot rename log must contain old and new names."""
        boot_cache = {5: {"entity_type": "light", "published": True, "ha_name": "Lampe Salon"}}
        mapping = _make_mapping(ha_name="Plafonnier Salon", entity_type="light", eq_id=5)

        with caplog.at_level(logging.INFO, logger="resources.daemon.transport.http_server"):
            await _call_helper(eq_id=5, mapping=mapping, previous_decision=None,
                               boot_cache=boot_cache, is_first_sync=True)

        rename_logs = [r.message for r in caplog.records if "rename détecté depuis boot_cache" in r.message]
        assert rename_logs
        assert "Lampe Salon" in rename_logs[0]
        assert "Plafonnier Salon" in rename_logs[0]

    async def test_rename_boot_empty_boot_name_no_log(self, caplog):
        """Boot cache entry with ha_name='' → no rename log (nothing to compare)."""
        boot_cache = {5: {"entity_type": "light", "published": True, "ha_name": ""}}
        mapping = _make_mapping(ha_name="Nouvelle Lampe", entity_type="light", eq_id=5)

        with caplog.at_level(logging.INFO, logger="resources.daemon.transport.http_server"):
            await _call_helper(eq_id=5, mapping=mapping, previous_decision=None,
                               boot_cache=boot_cache, is_first_sync=True)

        assert not any("rename détecté depuis boot_cache" in r.message for r in caplog.records)

    async def test_no_boot_rename_when_not_first_sync(self, caplog):
        """is_first_sync=False → boot path not executed, no boot rename log."""
        boot_cache = {5: {"entity_type": "light", "published": True, "ha_name": "Ancien Nom"}}
        mapping = _make_mapping(ha_name="Nouveau Nom", entity_type="light", eq_id=5)

        with caplog.at_level(logging.INFO, logger="resources.daemon.transport.http_server"):
            await _call_helper(eq_id=5, mapping=mapping, previous_decision=None,
                               boot_cache=boot_cache, is_first_sync=False)

        assert not any("boot_cache" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Retypage boot (also covered in test_boot_reconciliation.py as integration)
# ---------------------------------------------------------------------------

class TestRetypageBootUnit:
    """Unit tests for boot retypage detection path."""

    async def test_retypage_boot_calls_unpublish(self):
        """boot_cache entity_type differs → unpublish old type."""
        publisher = _make_publisher(unpublish_ok=True)
        boot_cache = {7: {"entity_type": "light", "published": True, "ha_name": "Lampe"}}
        mapping = _make_mapping(entity_type="switch", eq_id=7)

        await _call_helper(eq_id=7, mapping=mapping, previous_decision=None,
                           boot_cache=boot_cache, is_first_sync=True, publisher=publisher)

        publisher.unpublish_by_eq_id.assert_called_once_with(7, entity_type="light")

    async def test_retypage_boot_unpublish_fail_defers(self):
        """AC #8 — boot retypage unpublish fails → pending populated."""
        publisher = _make_publisher(unpublish_ok=False)
        boot_cache = {7: {"entity_type": "light", "published": True, "ha_name": "Lampe"}}
        mapping = _make_mapping(entity_type="switch", eq_id=7)
        pending = {}

        await _call_helper(eq_id=7, mapping=mapping, previous_decision=None,
                           boot_cache=boot_cache, is_first_sync=True,
                           publisher=publisher, pending=pending)

        assert pending.get(7) == "light"

    async def test_no_retypage_boot_when_not_first_sync(self):
        """is_first_sync=False → boot retypage path skipped."""
        publisher = _make_publisher(unpublish_ok=True)
        boot_cache = {7: {"entity_type": "light", "published": True, "ha_name": "Lampe"}}
        mapping = _make_mapping(entity_type="switch", eq_id=7)

        await _call_helper(eq_id=7, mapping=mapping, previous_decision=None,
                           boot_cache=boot_cache, is_first_sync=False, publisher=publisher)

        publisher.unpublish_by_eq_id.assert_not_called()

    async def test_no_retypage_boot_when_not_published(self):
        """Guardrail 5 boot: published=False in boot_cache → no unpublish attempted."""
        publisher = _make_publisher(unpublish_ok=True)
        boot_cache = {7: {"entity_type": "light", "published": False, "ha_name": "Lampe"}}
        mapping = _make_mapping(entity_type="switch", eq_id=7)

        await _call_helper(eq_id=7, mapping=mapping, previous_decision=None,
                           boot_cache=boot_cache, is_first_sync=True, publisher=publisher)

        publisher.unpublish_by_eq_id.assert_not_called()


# ---------------------------------------------------------------------------
# Scénario combiné : rename + retypage simultanés (runtime)
# ---------------------------------------------------------------------------

class TestRenameAndRetypageCombined:
    """Scénario angle mort : ha_name ET entity_type changent en même temps au runtime."""

    async def test_rename_and_retypage_combined_logs_both(self, caplog):
        """Rename + retypage → log [LIFECYCLE] rename ET [LIFECYCLE] retypage."""
        publisher = _make_publisher(unpublish_ok=True)
        prev = _make_previous_decision(entity_type="light", ha_name="Lampe Salon",
                                       discovery_published=True)
        mapping = _make_mapping(entity_type="switch", ha_name="Plafonnier Séjour", eq_id=20)

        with caplog.at_level(logging.INFO, logger="resources.daemon.transport.http_server"):
            await _call_helper(eq_id=20, mapping=mapping, previous_decision=prev,
                               publisher=publisher)

        messages = [r.message for r in caplog.records]
        assert any("[LIFECYCLE]" in m and "retypage" in m for m in messages), (
            f"Expected retypage log. Got: {messages}"
        )
        assert any("[LIFECYCLE]" in m and "rename détecté" in m for m in messages), (
            f"Expected rename log. Got: {messages}"
        )

    async def test_rename_and_retypage_combined_calls_unpublish(self):
        """Rename + retypage → unpublish de l'ancien type appelé."""
        publisher = _make_publisher(unpublish_ok=True)
        prev = _make_previous_decision(entity_type="light", ha_name="Lampe Salon",
                                       discovery_published=True)
        mapping = _make_mapping(entity_type="switch", ha_name="Plafonnier Séjour", eq_id=20)

        await _call_helper(eq_id=20, mapping=mapping, previous_decision=prev,
                           publisher=publisher)

        publisher.unpublish_by_eq_id.assert_called_once_with(20, entity_type="light")

    async def test_rename_and_retypage_combined_unique_id_invariant(self):
        """AC #11 — unique_id inchangé même lors d'un rename + retypage simultanés."""
        publisher = _make_publisher(unpublish_ok=True)
        prev = _make_previous_decision(entity_type="light", ha_name="Lampe Salon",
                                       discovery_published=True)
        mapping = _make_mapping(entity_type="switch", ha_name="Plafonnier Séjour", eq_id=20)
        original_uid = mapping.ha_unique_id

        await _call_helper(eq_id=20, mapping=mapping, previous_decision=prev,
                           publisher=publisher)

        assert mapping.ha_unique_id == original_uid
        assert mapping.ha_unique_id == "jeedom2ha_eq_20"
