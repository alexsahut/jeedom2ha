"""Story 19.6 (bloc B) — action HA protégée (AC6) et sérialisée (AC8)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp.test_utils import make_mocked_request

import transport.http_server as http_server
from models.mapping import LightCapabilities, MappingResult, PublicationDecision
from models.topology import EligibilityResult, JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot


SECRET = "test-secret-19.6-lock"
VALID_HEADERS = {"X-Local-Secret": SECRET}


def _light_mapping(eq_id: int) -> MappingResult:
    return MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="light_on_off_state",
        jeedom_eq_id=eq_id,
        ha_unique_id=f"jeedom2ha_eq_{eq_id}",
        ha_name=f"Lumiere {eq_id}",
        suggested_area="Salon",
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


def _make_topology() -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-09-30T08:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics={
            10: JeedomEqLogic(id=10, name="Lampe Salon", object_id=1, is_enable=True, cmds=list(_light_mapping(10).commands.values())),
            11: JeedomEqLogic(id=11, name="Applique Salon", object_id=1, is_enable=True, cmds=list(_light_mapping(11).commands.values())),
        },
    )


def _build_app() -> "http_server.web.Application":
    app = http_server.create_app(local_secret=SECRET)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    app["topology"] = _make_topology()
    app["eligibility"] = {
        10: EligibilityResult(is_eligible=True, reason_code="eligible"),
        11: EligibilityResult(is_eligible=True, reason_code="eligible"),
    }
    app["mappings"] = {10: _light_mapping(10), 11: _light_mapping(11)}
    app["publications"] = {
        10: _published_decision(_light_mapping(10)),
        11: _published_decision(_light_mapping(11)),
    }
    app["published_scope"] = {
        "global": {
            "counts": {"total": 2, "include": 2, "exclude": 0, "exceptions": 0},
            "effective_state": "include",
            "has_pending_home_assistant_changes": False,
        },
        "pieces": [
            {
                "object_id": 1,
                "object_name": "Salon",
                "counts": {"total": 2, "include": 2, "exclude": 0, "exceptions": 0},
                "home_perimetre": "Incluse",
                "has_pending_home_assistant_changes": False,
            }
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
                "name": "Applique Salon",
                "effective_state": "include",
                "decision_source": "global",
                "is_exception": False,
                "has_pending_home_assistant_changes": False,
            },
        ],
    }
    return app


def _make_request(app, body: dict):
    request = make_mocked_request("POST", "/action/execute", headers=VALID_HEADERS, app=app)
    request.json = AsyncMock(return_value=body)
    return request


@pytest.mark.asyncio
async def test_ac6_action_completes_after_handler_cancellation():
    """AC6 : le handler est annulé (déconnexion simulée du client) pendant l'exécution ;
    la tâche protégée par `asyncio.shield` continue et publie/dépublie tous les équipements.

    Technique : le handler `_handle_action_execute` est invoqué directement (via une
    requête `make_mocked_request`) et sa coroutine est annulée explicitement pendant
    l'exécution — c'est une annulation de la coroutine handler elle-même, qui est la
    scène exacte que `asyncio.shield` protège, plutôt qu'une vraie coupure TCP au niveau
    socket (jugée trop fragile à reproduire de façon déterministe en test unitaire).
    """
    app = _build_app()
    request = _make_request(app, {"intention": "supprimer", "portee": "global", "selection": [10, 11], "deadline_s": 0.4})

    publisher = MagicMock()

    async def _slow_unpublish(*args, **kwargs):
        await asyncio.sleep(0.05)
        return True

    publisher.unpublish_by_eq_id = AsyncMock(side_effect=_slow_unpublish)

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        handler_task = asyncio.ensure_future(http_server._handle_action_execute(request))
        await asyncio.sleep(0.01)
        assert not handler_task.done()
        handler_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await handler_task

        # Le handler est annulé, mais la tâche protégée doit continuer en arrière-plan.
        await asyncio.sleep(0.3)

    assert publisher.unpublish_by_eq_id.await_count == 2
    assert app["publications"][10].should_publish is False
    assert app["publications"][11].should_publish is False


@pytest.mark.asyncio
async def test_ac8_second_request_rejected_while_action_in_progress():
    """AC8 : une seconde requête pendant une action en cours reçoit 409 immédiatement,
    sans toucher `publications` ; après la fin de la première, une nouvelle requête passe."""
    app = _build_app()

    publisher = MagicMock()

    async def _slow_unpublish(*args, **kwargs):
        await asyncio.sleep(0.1)
        return True

    publisher.unpublish_by_eq_id = AsyncMock(side_effect=_slow_unpublish)

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        request1 = _make_request(app, {"intention": "supprimer", "portee": "equipement", "selection": [10], "deadline_s": 0.4})
        task1 = asyncio.ensure_future(http_server._handle_action_execute(request1))
        await asyncio.sleep(0.02)
        assert app["action_lock"].locked()

        request2 = _make_request(app, {"intention": "supprimer", "portee": "equipement", "selection": [11], "deadline_s": 0.4})
        response2 = await http_server._handle_action_execute(request2)
        assert response2.status == 409
        body2 = response2.body if hasattr(response2, "body") else None

        import json as _json
        payload2 = _json.loads(response2.text)
        assert payload2["code"] == "action_in_progress"

        # La deuxième requête refusée n'a pas touché l'équipement 11.
        assert app["publications"][11].should_publish is True

        response1 = await task1
        assert response1.status == 200
        assert app["action_lock"].locked() is False

        # Une nouvelle requête, une fois l'action précédente terminée, doit passer.
        request3 = _make_request(app, {"intention": "supprimer", "portee": "equipement", "selection": [11], "deadline_s": 0.4})
        response3 = await http_server._handle_action_execute(request3)
        assert response3.status == 200
        assert app["publications"][11].should_publish is False


@pytest.mark.asyncio
async def test_ac8_lock_released_after_exception_in_action():
    """AC8 : le verrou est libéré même si l'action lève une exception."""
    app = _build_app()

    publisher = MagicMock()
    publisher.unpublish_by_eq_id = AsyncMock(side_effect=RuntimeError("boom"))

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        request = _make_request(app, {"intention": "supprimer", "portee": "equipement", "selection": [10], "deadline_s": 0.4})
        with pytest.raises(RuntimeError):
            await http_server._handle_action_execute(request)

    assert app["action_lock"].locked() is False

    # Le verrou libéré permet une nouvelle requête.
    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
        request2 = _make_request(app, {"intention": "supprimer", "portee": "equipement", "selection": [10], "deadline_s": 0.4})
        response2 = await http_server._handle_action_execute(request2)
        assert response2.status == 200


@pytest.mark.asyncio
async def test_ac8_lock_stays_held_during_protected_action_after_cancellation():
    """AC8 : après annulation du handler (déconnexion), le verrou reste tenu tant que
    l'action protégée tourne encore, puis il est libéré à sa fin."""
    app = _build_app()

    publisher = MagicMock()

    async def _slow_unpublish(*args, **kwargs):
        await asyncio.sleep(0.1)
        return True

    publisher.unpublish_by_eq_id = AsyncMock(side_effect=_slow_unpublish)

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        request = _make_request(app, {"intention": "supprimer", "portee": "equipement", "selection": [10], "deadline_s": 0.4})
        handler_task = asyncio.ensure_future(http_server._handle_action_execute(request))
        await asyncio.sleep(0.02)
        handler_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await handler_task

        # Juste après l'annulation du handler, l'action protégée tourne encore : verrou tenu.
        assert app["action_lock"].locked()

        await asyncio.sleep(0.2)

    assert app["action_lock"].locked() is False


@pytest.mark.asyncio
async def test_ac6_task_holds_strong_reference_until_done():
    """Revue PR #189 (tour 7, Codex P1) : la tâche protégée est référencée fortement
    dans `app["action_tasks"]` tant qu'elle tourne, puis retirée à sa fin — même après
    annulation du handler, pour éviter une collecte prématurée par le garbage collector."""
    app = _build_app()

    publisher = MagicMock()

    async def _slow_unpublish(*args, **kwargs):
        await asyncio.sleep(0.1)
        return True

    publisher.unpublish_by_eq_id = AsyncMock(side_effect=_slow_unpublish)

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        request = _make_request(app, {"intention": "supprimer", "portee": "equipement", "selection": [10], "deadline_s": 0.4})
        handler_task = asyncio.ensure_future(http_server._handle_action_execute(request))
        await asyncio.sleep(0.02)
        handler_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await handler_task

        # Juste après l'annulation du handler, la tâche protégée tourne encore :
        # elle doit rester dans l'ensemble de référence forte.
        assert len(app["action_tasks"]) == 1

        await asyncio.sleep(0.2)

    # La tâche est terminée : elle a été retirée de l'ensemble.
    assert len(app["action_tasks"]) == 0
