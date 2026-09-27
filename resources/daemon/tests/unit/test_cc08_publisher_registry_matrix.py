"""CC-08 — matrice de couverture PublisherRegistry.

known_types() × {sync, action publier, republication} × {primaire, secondaire}

Chaque cellule est un test explicite et individuellement identifiable (id de
paramétrage = nom du type HA) : un échec de dispatch pour un type donné pointe
directement vers la cellule concernée, pas de boucle silencieuse partagée.

Les trois chemins testés appellent tous, en dernier ressort, la même
``PublisherRegistry.publish()`` :
  - sync            : appel direct (ligne ``publisher_registry.publish(...)``
                       dans la boucle de sync, identique pour ``_publish_additional_sensors``) ;
  - action publier   : ``_publish_mapping_for_action`` ;
  - republication    : ``_republish_all_from_cache``.

Un type non enregistré dans PublisherRegistry doit échouer explicitement
(``publication_result.status == "failed"``, jamais un ``False`` silencieux
sans diagnostic) sur les trois chemins.
"""
from __future__ import annotations

import asyncio
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from discovery.publisher import DiscoveryPublisher
from discovery.registry import PublisherRegistry
from models.mapping import MappingResult, SensorCapabilities
from models.topology import TopologySnapshot
from transport.http_server import _publish_mapping_for_action, _republish_all_from_cache

KNOWN_TYPES = PublisherRegistry.known_types()


def _publication_decision(should_publish: bool):
    """Lightweight stand-in for a secondary's `publication_decision_ref` (last-sync
    decision), sufficient for the `should_publish` gate checked by both republication
    paths (revue Codex P1)."""
    return type("PublicationDecision", (), {"should_publish": should_publish})()


def _mapping(
    entity_type: str,
    eq_id: int,
    *,
    additional=None,
    should_publish: Optional[bool] = None,
) -> MappingResult:
    """`should_publish` sets `publication_decision_ref` to simulate the last-sync
    decision for a secondary (cf. `_secondary_publishable` in http_server.py).
    Left `None` (default) to simulate a secondary never synced (no known decision)."""
    mapping = MappingResult(
        ha_entity_type=entity_type,
        confidence="sure",
        reason_code=f"{entity_type}_test",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Test {entity_type} {eq_id}",
        capabilities=SensorCapabilities(),
        additional_mappings=additional or [],
    )
    if should_publish is not None:
        mapping.publication_decision_ref = _publication_decision(should_publish)
    return mapping


def _snapshot() -> TopologySnapshot:
    return TopologySnapshot(timestamp="2026-09-27T00:00:00+00:00")


def _distinct_primary_type(secondary_type: str) -> str:
    """Pick a known type distinct from ``secondary_type`` to carry the primary.

    Avoids the same publish_<type> mock being awaited twice (primary + secondary)
    when the secondary's type happens to match a hardcoded primary type.
    """
    for candidate in KNOWN_TYPES:
        if candidate != secondary_type:
            return candidate
    raise AssertionError("KNOWN_TYPES must contain at least two distinct types")


def _registry_with_patched_publishers() -> tuple[PublisherRegistry, DiscoveryPublisher]:
    """Real DiscoveryPublisher instance whose publish_<type> methods are all mocked.

    Using the real class (not a stub) guarantees every known_type actually has
    a callable method on the object PublisherRegistry dispatches to.
    """
    mqtt_bridge = MagicMock()
    publisher = DiscoveryPublisher(mqtt_bridge)
    for known_type in KNOWN_TYPES:
        method_name = f"publish_{known_type}"
        assert hasattr(publisher, method_name), (
            f"DiscoveryPublisher.{method_name} missing for known_type={known_type!r}"
        )
        setattr(publisher, method_name, AsyncMock(return_value=True))
    return PublisherRegistry(publisher), publisher


class TestSyncPathMatrix:
    """Sync path: PublisherRegistry.publish() appelé directement (primaire et secondaire)."""

    @pytest.mark.parametrize("entity_type", KNOWN_TYPES, ids=KNOWN_TYPES)
    async def test_sync_publishes_primary(self, entity_type):
        registry, publisher = _registry_with_patched_publishers()
        mapping = _mapping(entity_type, eq_id=1)
        snapshot = _snapshot()

        ok = await registry.publish(mapping, snapshot)

        assert ok is True
        getattr(publisher, f"publish_{entity_type}").assert_awaited_once_with(mapping, snapshot)

    @pytest.mark.parametrize("entity_type", KNOWN_TYPES, ids=KNOWN_TYPES)
    async def test_sync_publishes_secondary(self, entity_type):
        registry, publisher = _registry_with_patched_publishers()
        secondary = _mapping(entity_type, eq_id=2)
        snapshot = _snapshot()

        ok = await registry.publish(secondary, snapshot)

        assert ok is True
        getattr(publisher, f"publish_{entity_type}").assert_awaited_once_with(secondary, snapshot)

    async def test_sync_unregistered_type_fails_explicitly(self):
        registry, _publisher = _registry_with_patched_publishers()
        mapping = _mapping("unknown_type", eq_id=99)
        snapshot = _snapshot()

        ok = await registry.publish(mapping, snapshot)

        assert ok is False
        assert mapping.publication_result is not None
        assert mapping.publication_result.status == "failed"
        assert mapping.publication_result.technical_reason_code == "publisher_not_registered"


class TestActionPublierPathMatrix:
    """Action « publier » : _publish_mapping_for_action (primaire + additional_mappings)."""

    @pytest.mark.parametrize("entity_type", KNOWN_TYPES, ids=KNOWN_TYPES)
    async def test_publier_publishes_primary(self, entity_type):
        registry, publisher = _registry_with_patched_publishers()
        mapping = _mapping(entity_type, eq_id=1)
        snapshot = _snapshot()

        ok = await _publish_mapping_for_action(registry, mapping, snapshot)

        assert ok is True
        getattr(publisher, f"publish_{entity_type}").assert_awaited_once_with(mapping, snapshot)

    @pytest.mark.parametrize("entity_type", KNOWN_TYPES, ids=KNOWN_TYPES)
    async def test_publier_publishes_secondary(self, entity_type):
        registry, publisher = _registry_with_patched_publishers()
        primary_type = _distinct_primary_type(entity_type)
        secondary = _mapping(entity_type, eq_id=2, should_publish=True)
        primary = _mapping(primary_type, eq_id=1, additional=[secondary])
        snapshot = _snapshot()

        ok = await _publish_mapping_for_action(registry, primary, snapshot)

        assert ok is True
        getattr(publisher, f"publish_{entity_type}").assert_awaited_once_with(secondary, snapshot)
        getattr(publisher, f"publish_{primary_type}").assert_awaited_once_with(primary, snapshot)

    async def test_publier_unregistered_primary_fails_explicitly(self):
        registry, _publisher = _registry_with_patched_publishers()
        mapping = _mapping("unknown_type", eq_id=99)
        snapshot = _snapshot()

        ok = await _publish_mapping_for_action(registry, mapping, snapshot)

        assert ok is False
        assert mapping.publication_result.status == "failed"
        assert mapping.publication_result.technical_reason_code == "publisher_not_registered"

    async def test_publier_unregistered_secondary_fails_explicitly_without_masking(self):
        registry, publisher = _registry_with_patched_publishers()
        secondary = _mapping("unknown_type", eq_id=2, should_publish=True)
        primary = _mapping("switch", eq_id=1, additional=[secondary])
        snapshot = _snapshot()

        ok = await _publish_mapping_for_action(registry, primary, snapshot)

        assert ok is False
        assert secondary.publication_result.status == "failed"
        assert secondary.publication_result.technical_reason_code == "publisher_not_registered"
        publisher.publish_switch.assert_awaited_once_with(primary, snapshot)

    async def test_publier_secondary_failure_does_not_short_circuit_remaining_secondaries(self):
        """Un secondaire en échec ne doit pas empêcher la publication des suivants."""
        registry, publisher = _registry_with_patched_publishers()
        failing = _mapping("unknown_type", eq_id=2, should_publish=True)
        ok_secondary = _mapping("sensor", eq_id=3, should_publish=True)
        primary = _mapping("switch", eq_id=1, additional=[failing, ok_secondary])
        snapshot = _snapshot()

        ok = await _publish_mapping_for_action(registry, primary, snapshot)

        assert ok is False
        publisher.publish_sensor.assert_awaited_once_with(ok_secondary, snapshot)

    async def test_publier_secondary_refused_at_last_sync_is_not_republished(self):
        """Revue Codex (P1) : un secondaire dont la décision du dernier sync refuse
        la publication (should_publish=False) ne doit pas être republié par l'action
        « publier », même si le primaire l'est."""
        registry, publisher = _registry_with_patched_publishers()
        refused = _mapping("sensor", eq_id=2, should_publish=False)
        primary = _mapping("switch", eq_id=1, additional=[refused])
        snapshot = _snapshot()

        ok = await _publish_mapping_for_action(registry, primary, snapshot)

        assert ok is True
        publisher.publish_sensor.assert_not_awaited()
        publisher.publish_switch.assert_awaited_once_with(primary, snapshot)

    async def test_publier_secondary_without_known_decision_is_not_republished(self):
        """Revue Codex (P1) : un secondaire jamais synchronisé (publication_decision_ref
        absent) ne doit pas être publié par l'action « publier » — une décision inconnue
        n'est jamais traitée comme une autorisation implicite."""
        registry, publisher = _registry_with_patched_publishers()
        never_synced = _mapping("sensor", eq_id=2)  # should_publish=None (pas de décision)
        primary = _mapping("switch", eq_id=1, additional=[never_synced])
        snapshot = _snapshot()

        ok = await _publish_mapping_for_action(registry, primary, snapshot)

        assert ok is True
        publisher.publish_sensor.assert_not_awaited()
        publisher.publish_switch.assert_awaited_once_with(primary, snapshot)


class TestRepublicationPathMatrix:
    """Republication (_republish_all_from_cache) : primaire + additional_mappings."""

    @pytest.fixture(autouse=True)
    def _no_real_throttle_delay(self, monkeypatch):
        """_republish_all_from_cache espace ses publications d'un vrai asyncio.sleep
        (10s / nb_entites, throttle MQTT réel — ne pas y toucher). On neutralise
        uniquement le sleep ici pour que la matrice ne coûte pas plusieurs minutes
        de CI par cellule ; le code de production n'est pas modifié."""
        monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    def _app(self, decision, registry: PublisherRegistry | None = None):
        mqtt_bridge = MagicMock()
        mqtt_bridge.is_connected = True
        return {
            "publications": {decision.mapping_result.jeedom_eq_id: decision},
            "mqtt_bridge": mqtt_bridge,
            "topology": _snapshot(),
            "pending_discovery_unpublish": {},
        }

    def _decision(self, mapping):
        return type(
            "PublicationDecision",
            (),
            {"mapping_result": mapping, "discovery_published": True},
        )()

    @pytest.mark.parametrize("entity_type", KNOWN_TYPES, ids=KNOWN_TYPES)
    async def test_republication_publishes_primary(self, entity_type, monkeypatch):
        registry, publisher = _registry_with_patched_publishers()
        monkeypatch.setattr(
            "transport.http_server.PublisherRegistry", lambda _publisher: registry
        )
        monkeypatch.setattr(
            "transport.http_server.DiscoveryPublisher", lambda _bridge: publisher
        )
        mapping = _mapping(entity_type, eq_id=1)
        app = self._app(self._decision(mapping))

        await _republish_all_from_cache(app, "ha_birth")

        getattr(publisher, f"publish_{entity_type}").assert_awaited_once_with(
            mapping, app["topology"]
        )

    @pytest.mark.parametrize("entity_type", KNOWN_TYPES, ids=KNOWN_TYPES)
    async def test_republication_publishes_secondary(self, entity_type, monkeypatch):
        registry, publisher = _registry_with_patched_publishers()
        monkeypatch.setattr(
            "transport.http_server.PublisherRegistry", lambda _publisher: registry
        )
        monkeypatch.setattr(
            "transport.http_server.DiscoveryPublisher", lambda _bridge: publisher
        )
        primary_type = _distinct_primary_type(entity_type)
        secondary = _mapping(entity_type, eq_id=2, should_publish=True)
        primary = _mapping(primary_type, eq_id=1, additional=[secondary])
        app = self._app(self._decision(primary))

        await _republish_all_from_cache(app, "ha_birth")

        getattr(publisher, f"publish_{entity_type}").assert_awaited_once_with(
            secondary, app["topology"]
        )
        getattr(publisher, f"publish_{primary_type}").assert_awaited_once_with(
            primary, app["topology"]
        )

    async def test_republication_unregistered_primary_fails_explicitly_and_logs(
        self, monkeypatch, caplog
    ):
        import logging

        registry, publisher = _registry_with_patched_publishers()
        monkeypatch.setattr(
            "transport.http_server.PublisherRegistry", lambda _publisher: registry
        )
        monkeypatch.setattr(
            "transport.http_server.DiscoveryPublisher", lambda _bridge: publisher
        )
        mapping = _mapping("unknown_type", eq_id=99)
        app = self._app(self._decision(mapping))

        with caplog.at_level(logging.ERROR, logger="transport.http_server"):
            await _republish_all_from_cache(app, "ha_birth")

        assert mapping.publication_result.status == "failed"
        assert mapping.publication_result.technical_reason_code == "publisher_not_registered"
        assert any("échec publish" in r.message for r in caplog.records)

    async def test_republication_unregistered_secondary_fails_explicitly_without_masking(
        self, monkeypatch
    ):
        registry, publisher = _registry_with_patched_publishers()
        monkeypatch.setattr(
            "transport.http_server.PublisherRegistry", lambda _publisher: registry
        )
        monkeypatch.setattr(
            "transport.http_server.DiscoveryPublisher", lambda _bridge: publisher
        )
        secondary = _mapping("unknown_type", eq_id=2, should_publish=True)
        primary = _mapping("switch", eq_id=1, additional=[secondary])
        app = self._app(self._decision(primary))

        await _republish_all_from_cache(app, "ha_birth")

        assert secondary.publication_result.status == "failed"
        assert secondary.publication_result.technical_reason_code == "publisher_not_registered"
        publisher.publish_switch.assert_awaited_once_with(primary, app["topology"])

    async def test_republication_secondary_refused_at_last_sync_is_not_republished(
        self, monkeypatch
    ):
        """Revue Codex (P1) : un secondaire dont la décision du dernier sync refuse
        la publication (should_publish=False) ne doit pas être republié, même si le
        primaire l'est."""
        registry, publisher = _registry_with_patched_publishers()
        monkeypatch.setattr(
            "transport.http_server.PublisherRegistry", lambda _publisher: registry
        )
        monkeypatch.setattr(
            "transport.http_server.DiscoveryPublisher", lambda _bridge: publisher
        )
        refused = _mapping("sensor", eq_id=2, should_publish=False)
        primary = _mapping("switch", eq_id=1, additional=[refused])
        app = self._app(self._decision(primary))

        await _republish_all_from_cache(app, "ha_birth")

        publisher.publish_sensor.assert_not_awaited()
        publisher.publish_switch.assert_awaited_once_with(primary, app["topology"])

    async def test_republication_secondary_without_known_decision_is_not_republished(
        self, monkeypatch
    ):
        """Revue Codex (P1) : un secondaire jamais synchronisé (publication_decision_ref
        absent) ne doit pas être republié — une décision inconnue n'est jamais traitée
        comme une autorisation implicite."""
        registry, publisher = _registry_with_patched_publishers()
        monkeypatch.setattr(
            "transport.http_server.PublisherRegistry", lambda _publisher: registry
        )
        monkeypatch.setattr(
            "transport.http_server.DiscoveryPublisher", lambda _bridge: publisher
        )
        never_synced = _mapping("sensor", eq_id=2)  # should_publish=None (pas de décision)
        primary = _mapping("switch", eq_id=1, additional=[never_synced])
        app = self._app(self._decision(primary))

        await _republish_all_from_cache(app, "ha_birth")

        publisher.publish_sensor.assert_not_awaited()
        publisher.publish_switch.assert_awaited_once_with(primary, app["topology"])

    async def test_republication_delay_counts_primary_and_publishable_secondaries_only(
        self, monkeypatch
    ):
        """Revue Codex (P2) : le délai de lissage doit compter primaires + secondaires
        publiables — un secondaire refusé (ignoré, non publié) ne doit pas gonfler le
        compte utilisé pour calculer le délai."""
        registry, publisher = _registry_with_patched_publishers()
        monkeypatch.setattr(
            "transport.http_server.PublisherRegistry", lambda _publisher: registry
        )
        monkeypatch.setattr(
            "transport.http_server.DiscoveryPublisher", lambda _bridge: publisher
        )
        sleep_calls: list[float] = []

        async def _fake_sleep(delay):
            sleep_calls.append(delay)

        monkeypatch.setattr(asyncio, "sleep", _fake_sleep)

        publishable = _mapping("sensor", eq_id=2, should_publish=True)
        refused = _mapping("binary_sensor", eq_id=3, should_publish=False)
        primary = _mapping("switch", eq_id=1, additional=[publishable, refused])
        app = self._app(self._decision(primary))

        await _republish_all_from_cache(app, "ha_birth")

        # 1 primaire + 1 secondaire publiable = 2 entités → delay = 10.0 / 2 = 5.0.
        # Le secondaire refusé est ignoré, donc pas de sleep additionnel pour lui.
        assert sleep_calls == [pytest.approx(5.0), pytest.approx(5.0)]
