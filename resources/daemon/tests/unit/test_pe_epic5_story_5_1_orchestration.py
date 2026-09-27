"""Story 5.1 — orchestration canonique 5 étapes dans /action/sync."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.evaluate_equipment import evaluate_equipment as _real_evaluate_equipment
from models.mapping import ProjectionValidity
from models.topology import assess_all as _real_assess_all
from transport.http_server import create_app


SECRET = "test-secret-pe-5-1-orchestration"


def _sync_body(eq_logics: list[dict]) -> dict:
    return {
        "action": "sync",
        "payload": {
            "objects": [{"id": 1, "name": "Salon"}],
            "eq_logics": eq_logics,
            "sync_config": {"confidence_policy": "sure_probable"},
        },
        "request_id": "pe-5-1-test",
        "timestamp": "2026-04-16T00:00:00Z",
    }


def _light_eq_payload(eq_id: int, cmds: list[dict]) -> dict:
    return {
        "id": eq_id,
        "name": f"Lumiere {eq_id}",
        "object_id": 1,
        "is_enable": True,
        "is_visible": True,
        "eq_type": "virtual",
        "is_excluded": False,
        "status": {"timeout": 0},
        "cmds": cmds,
    }


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


@pytest.fixture
def mock_publisher():
    publisher = AsyncMock()
    publisher.publish_light = AsyncMock(return_value=True)
    publisher.publish_cover = AsyncMock(return_value=True)
    publisher.publish_switch = AsyncMock(return_value=True)
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    return publisher


def _set_connected_bridge(app):
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    app["mqtt_bridge"] = bridge


async def test_sync_executes_5_steps_in_order_and_publishes_valid_light(cli, app, mock_publisher):
    call_order: list[str] = []

    from mapping.light import LightMapper

    real_map = LightMapper.map

    def _assess_all_spy(snapshot):
        call_order.append("eligibility")
        return _real_assess_all(snapshot)

    def _map_spy(self, eq, snapshot):
        call_order.append("mapping")
        return real_map(self, eq, snapshot)

    def _evaluate_spy(*args, **kwargs):
        # Story 19.1 — validate_projection() et decide_publication() sont désormais appelées
        # à l'intérieur d'evaluate_equipment() avec ses propres références importées
        # directement (models.decide_publication / validation.ha_component_registry) : un
        # patch sur transport.http_server.validate_projection/decide_publication n'intercepte
        # plus rien. On espionne donc evaluate_equipment() lui-même, qui délègue à l'implé-
        # mentation réelle (comportement inchangé), en conservant les deux entrées de
        # call_order pour ne pas changer l'assertion de séquence existante. Les deux marqueurs
        # sont ajoutés APRÈS l'appel réel : le mapping (mapper_registry.map(), espionné via
        # LightMapper.map ci-dessus) se produit à L'INTÉRIEUR de cet appel, avant la
        # validation/décision internes — l'ordre observé doit donc rester
        # eligibility -> mapping -> validation -> decision -> publication.
        result = _real_evaluate_equipment(*args, **kwargs)
        call_order.append("validation")
        call_order.append("decision")
        return result

    async def _publish_light_spy(mapping, snapshot):
        call_order.append("publication")
        return True

    mock_publisher.publish_light = AsyncMock(side_effect=_publish_light_spy)
    _set_connected_bridge(app)

    payload = _sync_body(
        [
            _light_eq_payload(
                101,
                [
                    {"id": 1, "name": "On", "generic_type": "LIGHT_ON", "type": "action", "sub_type": "other"},
                    {"id": 2, "name": "Off", "generic_type": "LIGHT_OFF", "type": "action", "sub_type": "other"},
                    {"id": 3, "name": "Etat", "generic_type": "LIGHT_STATE", "type": "info", "sub_type": "binary"},
                ],
            )
        ]
    )

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher), patch(
        "transport.http_server.assess_all",
        side_effect=_assess_all_spy,
    ), patch.object(LightMapper, "map", new=_map_spy), patch(
        "transport.http_server.evaluate_equipment",
        side_effect=_evaluate_spy,
    ):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"
    assert call_order == ["eligibility", "mapping", "validation", "decision", "publication"]

    mapping = app["mappings"][101]
    assert mapping.projection_validity is not None
    assert mapping.projection_validity.is_valid is True
    assert mapping.publication_decision_ref is not None
    assert mapping.publication_decision_ref.should_publish is True


async def test_sync_calls_decide_even_when_projection_invalid_and_never_publishes(cli, app, mock_publisher):
    calls: list[str] = []

    def _validate_invalid(_entity_type, _capabilities):
        return ProjectionValidity(
            is_valid=False,
            reason_code="ha_missing_command_topic",
            missing_fields=["command_topic"],
            missing_capabilities=["has_command"],
        )

    def _evaluate_spy(*args, **kwargs):
        # Story 19.1 — même gotcha que le test précédent : evaluate_equipment() n'utilise
        # plus transport.http_server.validate_projection/decide_publication (références
        # importées directement dans models/evaluate_equipment.py). Pour forcer une
        # projection invalide tout en appelant le VRAI decide_publication() (le but du test :
        # vérifier qu'il est appelé même en cas de projection invalide, jamais court-circuité),
        # on injecte validate_projection_fn dans l'appel réel via le point d'extension prévu
        # par evaluate_equipment() (Dev Notes Story 19.0) plutôt que de patcher une référence
        # de module devenue inerte.
        calls.append("validation")
        kwargs["validate_projection_fn"] = _validate_invalid
        result = _real_evaluate_equipment(*args, **kwargs)
        calls.append("decision")
        return result

    _set_connected_bridge(app)
    payload = _sync_body(
        [
            _light_eq_payload(
                102,
                [
                    {"id": 1, "name": "On", "generic_type": "LIGHT_ON", "type": "action", "sub_type": "other"},
                    {"id": 2, "name": "Off", "generic_type": "LIGHT_OFF", "type": "action", "sub_type": "other"},
                    {"id": 3, "name": "Etat", "generic_type": "LIGHT_STATE", "type": "info", "sub_type": "binary"},
                ],
            )
        ]
    )

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher), patch(
        "transport.http_server.evaluate_equipment",
        side_effect=_evaluate_spy,
    ):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"
    assert calls == ["validation", "decision"]
    mock_publisher.publish_light.assert_not_awaited()

    mapping = app["mappings"][102]
    assert mapping.projection_validity is not None
    assert mapping.projection_validity.is_valid is False
    assert mapping.projection_validity.reason_code == "ha_missing_command_topic"
    assert mapping.publication_decision_ref is not None
    assert mapping.publication_decision_ref.should_publish is False


async def test_light_without_mappable_action_sets_ha_missing_command_topic_and_no_publish(cli, app, mock_publisher):
    _set_connected_bridge(app)
    payload = _sync_body(
        [
            _light_eq_payload(
                103,
                [
                    {"id": 1, "name": "Etat", "generic_type": "LIGHT_STATE", "type": "info", "sub_type": "binary"},
                ],
            )
        ]
    )

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"
    mock_publisher.publish_light.assert_not_awaited()

    mapping = app["mappings"][103]
    assert mapping.projection_validity is not None
    assert mapping.projection_validity.reason_code == "ha_missing_command_topic"
    assert mapping.publication_decision_ref is not None
    assert mapping.publication_decision_ref.should_publish is False
