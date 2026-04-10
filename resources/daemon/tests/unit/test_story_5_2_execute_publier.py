"""Story 5.2 — tests backend de l'intention `publier`."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.mapping import LightCapabilities, MappingResult, PublicationDecision
from models.topology import EligibilityResult, JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
import transport.http_server as http_server


SECRET = "test-secret-5.2"
VALID_HEADERS = {"X-Local-Secret": SECRET}


def _light_mapping(eq_id: int) -> MappingResult:
    return MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off_state",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Lumiere {eq_id}",
        suggested_area="Salon" if eq_id in (10, 11, 12) else "Cuisine",
        commands={
            "LIGHT_ON": JeedomCmd(id=eq_id * 10 + 1, name="On", generic_type="LIGHT_ON", type="action", sub_type="other"),
            "LIGHT_OFF": JeedomCmd(id=eq_id * 10 + 2, name="Off", generic_type="LIGHT_OFF", type="action", sub_type="other"),
            "LIGHT_STATE": JeedomCmd(id=eq_id * 10 + 3, name="Etat", generic_type="LIGHT_STATE", type="info", sub_type="binary"),
        },
        capabilities=LightCapabilities(has_on_off=True),
    )


def _published_decision(mapping: MappingResult) -> PublicationDecision:
    return PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=mapping,
        state_topic=f"jeedom2ha/{mapping.jeedom_eq_id}/state",
        active_or_alive=True,
        discovery_published=True,
    )


def _unpublished_decision(mapping: MappingResult) -> PublicationDecision:
    return PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=mapping,
        state_topic=f"jeedom2ha/{mapping.jeedom_eq_id}/state",
        active_or_alive=False,
        discovery_published=False,
    )


def _make_topology() -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-04-06T08:00:00Z",
        objects={
            1: JeedomObject(id=1, name="Salon"),
            2: JeedomObject(id=2, name="Cuisine"),
        },
        eq_logics={
            10: JeedomEqLogic(id=10, name="Lampe Salon", object_id=1, is_enable=True),
            11: JeedomEqLogic(id=11, name="Prise Salon", object_id=1, is_enable=True),
            12: JeedomEqLogic(id=12, name="Lampe exclue", object_id=1, is_enable=True, is_excluded=True, exclusion_source="eqlogic"),
            20: JeedomEqLogic(id=20, name="Lampe Cuisine", object_id=2, is_enable=True),
        },
    )


def _make_published_scope() -> dict:
    return {
        "global": {
            "counts": {"total": 4, "include": 3, "exclude": 1, "exceptions": 0},
            "effective_state": "include",
            "has_pending_home_assistant_changes": True,
        },
        "pieces": [
            {
                "object_id": 1,
                "object_name": "Salon",
                "counts": {"total": 3, "include": 2, "exclude": 1, "exceptions": 0},
                "home_perimetre": "Incluse",
                "has_pending_home_assistant_changes": True,
            },
            {
                "object_id": 2,
                "object_name": "Cuisine",
                "counts": {"total": 1, "include": 1, "exclude": 0, "exceptions": 0},
                "home_perimetre": "Incluse",
                "has_pending_home_assistant_changes": True,
            },
        ],
        "equipements": [
            {
                "eq_id": 10,
                "object_id": 1,
                "name": "Lampe Salon",
                "effective_state": "include",
                "decision_source": "global",
                "is_exception": False,
                "has_pending_home_assistant_changes": True,
            },
            {
                "eq_id": 11,
                "object_id": 1,
                "name": "Prise Salon",
                "effective_state": "include",
                "decision_source": "global",
                "is_exception": False,
                "has_pending_home_assistant_changes": True,
            },
            {
                "eq_id": 12,
                "object_id": 1,
                "name": "Lampe exclue",
                "effective_state": "exclude",
                "decision_source": "equipement",
                "is_exception": True,
                "has_pending_home_assistant_changes": True,
            },
            {
                "eq_id": 20,
                "object_id": 2,
                "name": "Lampe Cuisine",
                "effective_state": "include",
                "decision_source": "global",
                "is_exception": False,
                "has_pending_home_assistant_changes": True,
            },
        ],
    }


def _publisher_mock(*, publish_results: dict[int, bool] | None = None) -> MagicMock:
    publisher = MagicMock()
    publish_results = publish_results or {}

    async def publish_light(mapping: MappingResult, snapshot: TopologySnapshot) -> bool:  # noqa: ARG001
        return publish_results.get(mapping.jeedom_eq_id, True)

    publisher.publish_light = AsyncMock(side_effect=publish_light)
    publisher.publish_cover = AsyncMock(return_value=True)
    publisher.publish_switch = AsyncMock(return_value=True)
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    return publisher


@pytest.fixture
def topology() -> TopologySnapshot:
    return _make_topology()


@pytest.fixture
def app(topology: TopologySnapshot):
    app = http_server.create_app(local_secret=SECRET)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    app["topology"] = topology
    app["published_scope"] = _make_published_scope()
    app["eligibility"] = {
        10: EligibilityResult(is_eligible=True, reason_code="eligible"),
        11: EligibilityResult(is_eligible=True, reason_code="eligible"),
        12: EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic"),
        20: EligibilityResult(is_eligible=True, reason_code="eligible"),
    }
    app["mappings"] = {
        10: _light_mapping(10),
        11: _light_mapping(11),
        12: _light_mapping(12),
        20: _light_mapping(20),
    }
    app["publications"] = {
        10: _unpublished_decision(app["mappings"][10]),
        11: _published_decision(app["mappings"][11]),
        12: _published_decision(app["mappings"][12]),
        20: _published_decision(app["mappings"][20]),
    }
    return app


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


async def _post_action(cli, payload: dict, *, wrapped: bool = False):
    body = {"payload": payload} if wrapped else payload
    return await cli.post("/action/execute", json=body, headers=VALID_HEADERS)


def test_resolve_eq_ids_for_portee_equipement(topology: TopologySnapshot):
    assert http_server._resolve_eq_ids_for_portee("equipement", [10, "11"], topology) == [10, 11]


def test_resolve_eq_ids_for_portee_piece(topology: TopologySnapshot):
    assert http_server._resolve_eq_ids_for_portee("piece", [1], topology) == [10, 11, 12]


def test_resolve_eq_ids_for_portee_global(topology: TopologySnapshot):
    assert http_server._resolve_eq_ids_for_portee("global", ["all"], topology) == [10, 11, 12, 20]


@pytest.mark.asyncio
async def test_publier_wrapped_payload_equipement_success(cli, app):
    publisher = _publisher_mock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ):
        response = await _post_action(
            cli,
            {"intention": "publier", "portee": "equipement", "selection": [10]},
            wrapped=True,
        )

    assert response.status == 200
    body = await response.json()
    payload = body["payload"]
    assert payload["intention"] == "publier"
    assert payload["portee"] == "equipement"
    assert payload["resultat"] == "succes"
    assert payload["message"] == "1 équipements mis à jour dans Home Assistant."
    assert payload["scope_reel"]["equipements_inclus"] == 1
    assert payload["scope_reel"]["equipements_publies_ou_crees"] == 1
    assert payload["scope_reel"]["ecarts_resolus"] == 0
    assert payload["scope_reel"]["skips"] == 0
    assert payload["aucun_flux_supprimer_recree"] is True
    assert payload["perimetre_impacte"]["nom"] == "Lampe Salon"
    assert app["mappings"][10].ha_unique_id == "jeedom2ha_eq_10"
    assert publisher.publish_light.await_args.args[0].ha_unique_id == "jeedom2ha_eq_10"
    assert app["publications"][10].active_or_alive is True
    assert app["publications"][10].discovery_published is True
    eq10_scope = next(eq for eq in app["published_scope"]["equipements"] if eq["eq_id"] == 10)
    assert eq10_scope["has_pending_home_assistant_changes"] is False
    assert app["published_scope"]["global"]["has_pending_home_assistant_changes"] is True


@pytest.mark.asyncio
async def test_publier_piece_scope_enforces_unpublish_for_excluded_equipment(cli, app):
    publisher = _publisher_mock()
    sleep_mock = AsyncMock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", sleep_mock
    ):
        response = await _post_action(
            cli,
            {"intention": "publier", "portee": "piece", "selection": [1]},
        )

    assert response.status == 200
    payload = (await response.json())["payload"]
    assert payload["resultat"] == "succes"
    assert payload["message"] == "2 équipements mis à jour dans Home Assistant."
    assert payload["perimetre_impacte"]["nom"] == "Salon"
    assert payload["scope_reel"]["equipements_inclus"] == 2
    assert payload["scope_reel"]["equipements_publies_ou_crees"] == 2
    assert payload["scope_reel"]["ecarts_resolus"] == 1
    publisher.unpublish_by_eq_id.assert_awaited_once_with(12, entity_type="light")
    assert app["publications"][12].active_or_alive is False
    assert app["publications"][12].discovery_published is False
    # Lissage : 2 publish + 1 unpublish = 3 appels sleep
    assert sleep_mock.await_count == 3


@pytest.mark.asyncio
async def test_publier_returns_idempotent_success_when_no_change_and_no_error(cli, app):
    app["mappings"].pop(10)
    app["mappings"].pop(11)
    app["publications"][11] = _unpublished_decision(_light_mapping(11))
    app["publications"][12] = _unpublished_decision(_light_mapping(12))

    publisher = _publisher_mock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ):
        response = await _post_action(
            cli,
            {"intention": "publier", "portee": "piece", "selection": [1]},
        )

    assert response.status == 200
    payload = (await response.json())["payload"]
    assert payload["resultat"] == "succes"
    assert payload["message"] == "Configuration déjà à jour dans Home Assistant."
    assert payload["scope_reel"]["equipements_publies_ou_crees"] == 0
    assert payload["scope_reel"]["ecarts_resolus"] == 0
    assert payload["scope_reel"]["skips"] == 2
    publisher.publish_light.assert_not_awaited()
    publisher.unpublish_by_eq_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_publier_returns_partial_success_when_one_publish_fails(cli, app):
    publisher = _publisher_mock(publish_results={11: False})

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ):
        response = await _post_action(
            cli,
            {"intention": "publier", "portee": "piece", "selection": [1]},
        )

    assert response.status == 200
    payload = (await response.json())["payload"]
    assert payload["resultat"] == "succes_partiel"
    assert payload["message"] == "1 équipements mis à jour, 1 n'ont pas pu être traités."
    assert payload["scope_reel"]["equipements_publies_ou_crees"] == 1
    assert payload["scope_reel"]["ecarts_resolus"] == 1
    assert app["publications"][10].active_or_alive is True
    assert app["publications"][11].active_or_alive is False


@pytest.mark.asyncio
async def test_publier_returns_error_when_all_publish_fail(cli, app):
    publisher = _publisher_mock(publish_results={20: False})

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ):
        response = await _post_action(
            cli,
            {"intention": "publier", "portee": "equipement", "selection": [20]},
        )

    assert response.status == 200
    payload = (await response.json())["payload"]
    assert payload["resultat"] == "echec"
    assert payload["message"] == "L'action n'a pas pu être exécutée. Vérifiez la connexion Home Assistant."
    assert payload["scope_reel"]["equipements_publies_ou_crees"] == 0
    assert app["publications"][20].active_or_alive is False


@pytest.mark.asyncio
async def test_publier_returns_409_when_topology_is_missing(cli, app):
    app["topology"] = None
    app["published_scope"] = None

    response = await _post_action(
        cli,
        {"intention": "publier", "portee": "global", "selection": ["all"]},
    )

    assert response.status == 409
    body = await response.json()
    assert body["payload"]["resultat"] == "echec"
    assert body["payload"]["message"] == "Aucune synchronisation disponible. Lancez une synchronisation d'abord."


@pytest.mark.asyncio
async def test_publier_returns_503_when_bridge_is_down(cli, app):
    app["mqtt_bridge"].is_connected = False

    response = await _post_action(
        cli,
        {"intention": "publier", "portee": "global", "selection": ["all"]},
    )

    assert response.status == 503
    body = await response.json()
    assert body["payload"]["resultat"] == "echec"
    assert body["payload"]["message"] == "L'action n'a pas pu être exécutée. Vérifiez la connexion Home Assistant."


@pytest.mark.asyncio
async def test_publier_returns_400_for_unknown_piece(aiohttp_client):
    app = http_server.create_app(local_secret=SECRET)
    app["mqtt_bridge"]._state = "connected"
    app["topology"] = _make_topology()
    app["published_scope"] = _make_published_scope()
    client = await aiohttp_client(app)

    response = await _post_action(
        client,
        {"intention": "publier", "portee": "piece", "selection": [999]},
    )

    assert response.status == 400
    body = await response.json()
    assert body["status"] == "error"
    assert "pièce" in body["message"].lower() or "piece" in body["message"].lower()
