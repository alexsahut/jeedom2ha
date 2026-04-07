"""Story 5.3 — tests backend de l'intention `supprimer`."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.mapping import LightCapabilities, MappingResult, PublicationDecision
from models.topology import EligibilityResult, JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
import transport.http_server as http_server


SECRET = "test-secret-5.3"
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
        should_publish=False,
        reason="sure",
        mapping_result=mapping,
        state_topic=f"jeedom2ha/{mapping.jeedom_eq_id}/state",
        active_or_alive=False,
        discovery_published=False,
    )


def _make_topology() -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-04-07T08:00:00Z",
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
            "has_pending_home_assistant_changes": False,
        },
        "pieces": [
            {
                "object_id": 1,
                "object_name": "Salon",
                "counts": {"total": 3, "include": 2, "exclude": 1, "exceptions": 0},
                "home_perimetre": "Incluse",
                "has_pending_home_assistant_changes": False,
            },
            {
                "object_id": 2,
                "object_name": "Cuisine",
                "counts": {"total": 1, "include": 1, "exclude": 0, "exceptions": 0},
                "home_perimetre": "Incluse",
                "has_pending_home_assistant_changes": False,
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
                "has_pending_home_assistant_changes": False,
            },
            {
                "eq_id": 11,
                "object_id": 1,
                "name": "Prise Salon",
                "effective_state": "include",
                "decision_source": "global",
                "is_exception": False,
                "has_pending_home_assistant_changes": False,
            },
            {
                "eq_id": 12,
                "object_id": 1,
                "name": "Lampe exclue",
                "effective_state": "exclude",
                "decision_source": "equipement",
                "is_exception": True,
                "has_pending_home_assistant_changes": False,
            },
            {
                "eq_id": 20,
                "object_id": 2,
                "name": "Lampe Cuisine",
                "effective_state": "include",
                "decision_source": "global",
                "is_exception": False,
                "has_pending_home_assistant_changes": False,
            },
        ],
    }


def _publisher_mock(*, unpublish_results: dict[int, bool] | None = None) -> MagicMock:
    publisher = MagicMock()
    unpublish_results = unpublish_results or {}

    async def unpublish_by_eq_id(eq_id: int, entity_type: str = "light") -> bool:  # noqa: ARG001
        return unpublish_results.get(eq_id, True)

    publisher.unpublish_by_eq_id = AsyncMock(side_effect=unpublish_by_eq_id)
    publisher.publish_light = AsyncMock(return_value=True)
    publisher.publish_cover = AsyncMock(return_value=True)
    publisher.publish_switch = AsyncMock(return_value=True)
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
    # All included equipment published in HA
    app["publications"] = {
        10: _published_decision(app["mappings"][10]),
        11: _published_decision(app["mappings"][11]),
        20: _published_decision(app["mappings"][20]),
    }
    return app


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


async def _post_action(cli, payload: dict):
    return await cli.post("/action/execute", json=payload, headers=VALID_HEADERS)


# --- Succès portée équipement ---


@pytest.mark.asyncio
async def test_supprimer_equipement_publie_success(cli, app):
    publisher = _publisher_mock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ):
        response = await _post_action(
            cli,
            {"intention": "supprimer", "portee": "equipement", "selection": [10]},
        )

    assert response.status == 200
    body = await response.json()
    payload = body["payload"]
    assert payload["intention"] == "supprimer"
    assert payload["portee"] == "equipement"
    assert payload["resultat"] == "succes"
    assert "supprimé" in payload["message"]
    assert "1 équipement" in payload["message"]
    # Le nom n'est PAS dans le message (il est dans perimetre_impacte.nom, préfixé côté frontend)
    assert "Lampe Salon" not in payload["message"]
    assert payload["scope_reel"]["equipements_supprimes"] == 1
    assert payload["scope_reel"]["supprimer_errors"] == 0
    assert payload["scope_reel"]["skips"] == 0
    assert payload["perimetre_impacte"]["nom"] == "Lampe Salon"
    publisher.unpublish_by_eq_id.assert_awaited_once_with(10, entity_type="light")
    assert app["publications"][10].active_or_alive is False
    assert app["publications"][10].discovery_published is False


# --- Idempotence : eq déjà non publié ---


@pytest.mark.asyncio
async def test_supprimer_equipement_deja_non_publie_idempotent(cli, app):
    app["publications"][10] = _unpublished_decision(app["mappings"][10])
    publisher = _publisher_mock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ):
        response = await _post_action(
            cli,
            {"intention": "supprimer", "portee": "equipement", "selection": [10]},
        )

    assert response.status == 200
    payload = (await response.json())["payload"]
    assert payload["resultat"] == "succes"
    assert "déjà à jour" in payload["message"]
    assert payload["scope_reel"]["equipements_supprimes"] == 0
    assert payload["scope_reel"]["supprimer_errors"] == 0
    assert payload["scope_reel"]["skips"] == 1
    publisher.unpublish_by_eq_id.assert_not_awaited()


# --- Portée pièce ---


@pytest.mark.asyncio
async def test_supprimer_piece_boucle_sur_tous_les_eq(cli, app):
    publisher = _publisher_mock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ):
        response = await _post_action(
            cli,
            {"intention": "supprimer", "portee": "piece", "selection": [1]},
        )

    assert response.status == 200
    payload = (await response.json())["payload"]
    assert payload["resultat"] == "succes"
    assert payload["perimetre_impacte"]["nom"] == "Salon"
    # eq 10, 11 published — eq 12 has no publication → skip
    assert payload["scope_reel"]["equipements_supprimes"] == 2
    assert payload["scope_reel"]["skips"] == 1
    assert publisher.unpublish_by_eq_id.await_count == 2
    assert app["publications"][10].discovery_published is False
    assert app["publications"][11].discovery_published is False


# --- Portée global ---


@pytest.mark.asyncio
async def test_supprimer_global_boucle_sur_tous_les_eq(cli, app):
    publisher = _publisher_mock()
    sleep_mock = AsyncMock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", sleep_mock
    ):
        response = await _post_action(
            cli,
            {"intention": "supprimer", "portee": "global", "selection": ["all"]},
        )

    assert response.status == 200
    payload = (await response.json())["payload"]
    assert payload["resultat"] == "succes"
    assert payload["perimetre_impacte"]["nom"] == "Parc global"
    assert payload["scope_reel"]["equipements_supprimes"] == 3
    assert payload["scope_reel"]["skips"] == 1  # eq 12 not published
    assert publisher.unpublish_by_eq_id.await_count == 3
    # Lissage entre chaque unpublish
    assert sleep_mock.await_count == 3


# --- Échec unpublish ---


@pytest.mark.asyncio
async def test_supprimer_echec_total(cli, app):
    publisher = _publisher_mock(unpublish_results={10: False})
    # Only eq 10 is published; others unpublished
    app["publications"][11] = _unpublished_decision(app["mappings"][11])
    app["publications"][20] = _unpublished_decision(app["mappings"][20])

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ):
        response = await _post_action(
            cli,
            {"intention": "supprimer", "portee": "equipement", "selection": [10]},
        )

    assert response.status == 200
    payload = (await response.json())["payload"]
    assert payload["resultat"] == "echec"
    assert payload["scope_reel"]["equipements_supprimes"] == 0
    assert payload["scope_reel"]["supprimer_errors"] == 1


@pytest.mark.asyncio
async def test_supprimer_succes_partiel(cli, app):
    publisher = _publisher_mock(unpublish_results={11: False})

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ):
        response = await _post_action(
            cli,
            {"intention": "supprimer", "portee": "piece", "selection": [1]},
        )

    assert response.status == 200
    payload = (await response.json())["payload"]
    assert payload["resultat"] == "succes_partiel"
    assert "supprimé" in payload["message"]
    assert payload["scope_reel"]["equipements_supprimes"] == 1
    assert payload["scope_reel"]["supprimer_errors"] == 1


# --- Guards ---


@pytest.mark.asyncio
async def test_supprimer_returns_409_when_topology_missing(cli, app):
    app["topology"] = None
    app["published_scope"] = None

    response = await _post_action(
        cli,
        {"intention": "supprimer", "portee": "global", "selection": ["all"]},
    )

    assert response.status == 409
    body = await response.json()
    assert body["payload"]["resultat"] == "echec"
    assert "synchronisation" in body["payload"]["message"].lower()


@pytest.mark.asyncio
async def test_supprimer_returns_503_when_bridge_down(cli, app):
    app["mqtt_bridge"].is_connected = False

    response = await _post_action(
        cli,
        {"intention": "supprimer", "portee": "global", "selection": ["all"]},
    )

    assert response.status == 503
    body = await response.json()
    assert body["payload"]["resultat"] == "echec"
    assert "connexion" in body["payload"]["message"].lower()


# --- Publications update ---


@pytest.mark.asyncio
async def test_supprimer_updates_publication_discovery_published_false(cli, app):
    publisher = _publisher_mock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ):
        await _post_action(
            cli,
            {"intention": "supprimer", "portee": "equipement", "selection": [10]},
        )

    decision = app["publications"][10]
    assert decision.discovery_published is False
    assert decision.active_or_alive is False
    assert decision.should_publish is False
    assert decision.mapping_result is not None
    assert decision.mapping_result.ha_entity_type == "light"


# --- Message lisible ---


def test_build_supprimer_message_succes():
    msg = http_server._build_supprimer_message(
        resultat="succes",
        equipements_supprimes=1,
        supprimer_errors=0,
    )
    assert "1 équipement supprimé" in msg


def test_build_supprimer_message_deja_a_jour():
    msg = http_server._build_supprimer_message(
        resultat="succes",
        equipements_supprimes=0,
        supprimer_errors=0,
    )
    assert "déjà à jour" in msg


def test_build_supprimer_message_partiel():
    msg = http_server._build_supprimer_message(
        resultat="succes_partiel",
        equipements_supprimes=2,
        supprimer_errors=1,
    )
    assert "2 supprimé(s)" in msg
    assert "1 n'ont pas pu" in msg


def test_build_supprimer_message_echec():
    msg = http_server._build_supprimer_message(
        resultat="echec",
        equipements_supprimes=0,
        supprimer_errors=1,
    )
    assert "connexion" in msg.lower()
