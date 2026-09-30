"""Story 19.6 (AC1bis) — démon : plafond des pauses de lissage borné par `deadline_s`."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.mapping import LightCapabilities, MappingResult, PublicationDecision
from models.topology import EligibilityResult, JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
import transport.http_server as http_server
from transport import action_pacing


SECRET = "test-secret-19.6"
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


def _make_parc(n: int, n_inclus: int | None = None):
    """Un parc plat de `n` équipements « lumière ». Les `n_inclus` premiers sont inclus,
    publiés et déclenchent une pause ; le reste (N total - n_inclus) est exclu du scope et
    jamais publié, pour reproduire un grand inventaire dont seule une partie fait une pause
    (mesure du 30/09 : N total 292, N à pause 94)."""
    n_inclus = n if n_inclus is None else n_inclus
    eq_logics = {}
    scope_equipements = []
    eligibility = {}
    mappings = {}
    publications = {}
    for i in range(n):
        eq_id = 100 + i
        inclus = i < n_inclus
        mapping = _light_mapping(eq_id)
        eq_logics[eq_id] = JeedomEqLogic(
            id=eq_id, name=f"Lampe {eq_id}", object_id=1, is_enable=True,
            cmds=list(mapping.commands.values()),
        )
        scope_equipements.append({
            "eq_id": eq_id, "object_id": 1, "name": f"Lampe {eq_id}",
            "effective_state": "include" if inclus else "exclude", "decision_source": "global",
            "is_exception": False, "has_pending_home_assistant_changes": False,
        })
        eligibility[eq_id] = EligibilityResult(
            is_eligible=inclus, reason_code="eligible" if inclus else "excluded_eqlogic",
        )
        mappings[eq_id] = mapping
        if inclus:
            publications[eq_id] = _published_decision(mapping)

    topology = TopologySnapshot(
        timestamp="2026-09-30T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics=eq_logics,
    )
    published_scope = {
        "global": {"counts": {"total": n, "include": n_inclus, "exclude": n - n_inclus, "exceptions": 0},
                   "effective_state": "include", "has_pending_home_assistant_changes": False},
        "pieces": [],
        "equipements": scope_equipements,
    }
    return topology, published_scope, eligibility, mappings, publications


def _build_app(n: int, n_inclus: int | None = None):
    topology, published_scope, eligibility, mappings, publications = _make_parc(n, n_inclus)
    app = http_server.create_app(local_secret=SECRET)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    app["topology"] = topology
    app["published_scope"] = published_scope
    app["eligibility"] = eligibility
    app["mappings"] = mappings
    app["publications"] = publications
    return app


def _publisher_mock() -> MagicMock:
    publisher = MagicMock()
    publisher.publish_light = AsyncMock(return_value=True)
    publisher.publish_cover = AsyncMock(return_value=True)
    publisher.publish_switch = AsyncMock(return_value=True)
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    return publisher


def _fake_clock():
    """Sommeil factice qui avance une horloge factice de la durée demandée (+ retard optionnel)."""
    state = {"now": 0.0}

    async def fake_sleep(duration, *, _retard=[0.0]):  # noqa: B006 - mutable default utilisé comme case
        state["now"] += duration + _retard[0]
        _retard[0] = 0.0

    def fake_monotonic():
        return state["now"]

    return state, fake_sleep, fake_monotonic


@pytest.fixture
def cli_factory(aiohttp_client):
    async def _make(app):
        return await aiohttp_client(app)

    return _make


async def _post_action(cli, payload: dict):
    return await cli.post("/action/execute", json=payload, headers=VALID_HEADERS)


# --- AC1bis : sans deadline_s, comportement inchangé ---


@pytest.mark.asyncio
async def test_publier_sans_deadline_s_pauses_inchangees(cli_factory):
    app = _build_app(5)
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    sleep_mock = AsyncMock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", sleep_mock
    ):
        response = await _post_action(cli, {"intention": "publier", "portee": "global", "selection": ["all"]})

    assert response.status == 200
    assert sleep_mock.await_count == 5  # une pause par équipement, y compris le dernier (Décision 8)


@pytest.mark.asyncio
async def test_supprimer_sans_deadline_s_pauses_inchangees(cli_factory):
    app = _build_app(5)
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    sleep_mock = AsyncMock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", sleep_mock
    ):
        response = await _post_action(cli, {"intention": "supprimer", "portee": "global", "selection": ["all"]})

    assert response.status == 200
    assert sleep_mock.await_count == 5


# --- AC1bis : deadline_s invalide -> 400 ---


@pytest.mark.asyncio
async def test_deadline_s_invalide_retourne_400(cli_factory):
    app = _build_app(3)
    cli = await cli_factory(app)

    response = await _post_action(
        cli, {"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": "abc"},
    )
    assert response.status == 400

    response = await _post_action(
        cli, {"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": -1},
    )
    assert response.status == 400

    response = await _post_action(
        cli, {"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": 0},
    )
    assert response.status == 400


# --- AC1bis : petite portée (sous le plafond), pauses identiques sauf la dernière ---


@pytest.mark.asyncio
async def test_publier_petite_portee_pauses_identiques_sauf_derniere(cli_factory):
    n = 5
    app = _build_app(n)
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    state, fake_sleep, fake_monotonic = _fake_clock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", fake_sleep
    ), patch("time.monotonic", fake_monotonic):
        response = await _post_action(
            cli, {"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )

    assert response.status == 200
    _action_delay = max(0.1, 10.0 / n)
    # n équipements, tous à pause -> n-1 pauses de _action_delay, la dernière supprimée.
    assert state["now"] == pytest.approx(_action_delay * (n - 1))


@pytest.mark.asyncio
async def test_supprimer_petite_portee_pauses_identiques_sauf_derniere(cli_factory):
    n = 5
    app = _build_app(n)
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    state, fake_sleep, fake_monotonic = _fake_clock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", fake_sleep
    ), patch("time.monotonic", fake_monotonic):
        response = await _post_action(
            cli, {"intention": "supprimer", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )

    assert response.status == 200
    _action_delay = max(0.1, 10.0 / n)
    assert state["now"] == pytest.approx(_action_delay * (n - 1))


# --- AC1bis : mesure du 30/09 (N total 292, N à pause 94) ---


@pytest.mark.asyncio
async def test_publier_mesure_30_09_pauses_identiques_sauf_derniere(cli_factory):
    n_total, n_pause = 292, 94
    app = _build_app(n_total, n_pause)
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    state, fake_sleep, fake_monotonic = _fake_clock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", fake_sleep
    ), patch("time.monotonic", fake_monotonic):
        response = await _post_action(
            cli, {"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )

    assert response.status == 200
    _action_delay = max(0.1, 10.0 / n_total)
    # 94 équipements à pause sur 292 -> plafond 15s sur 93 pauses de 0.1s = 9.3s < 15s :
    # aucune compression, seule la dernière pause (du dernier équipement à pause) disparaît.
    assert state["now"] == pytest.approx(_action_delay * (n_pause - 1), rel=1e-6)
    assert state["now"] < action_pacing.P_MAX_S


# --- AC1bis : grand parc, total des pauses plafonné ---


@pytest.mark.asyncio
async def test_publier_grand_parc_pauses_plafonnees(cli_factory):
    n = 1000
    app = _build_app(n)
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    state, fake_sleep, fake_monotonic = _fake_clock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", fake_sleep
    ), patch("time.monotonic", fake_monotonic):
        response = await _post_action(
            cli, {"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )

    assert response.status == 200
    assert state["now"] <= action_pacing.P_MAX_S + 1e-6


@pytest.mark.asyncio
async def test_supprimer_grand_parc_pauses_plafonnees(cli_factory):
    n = 1000
    app = _build_app(n)
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    state, fake_sleep, fake_monotonic = _fake_clock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", fake_sleep
    ), patch("time.monotonic", fake_monotonic):
        response = await _post_action(
            cli, {"intention": "supprimer", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )

    assert response.status == 200
    assert state["now"] <= action_pacing.P_MAX_S + 1e-6


# --- AC1bis : la dernière itération ne fait jamais de pause ---


@pytest.mark.asyncio
async def test_publier_derniere_iteration_sans_pause(cli_factory):
    app = _build_app(3)
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    sleep_mock = AsyncMock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", sleep_mock
    ):
        response = await _post_action(
            cli, {"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )

    assert response.status == 200
    # Revue Codex P2 (PR #189, 3e tour) : chaque itération cède aussi la main en tête de
    # boucle (asyncio.sleep(0), non compté dans les pauses) -> 3 cessions de tête + 2
    # pauses de lissage (la dernière itération jamais de pause) = 5.
    assert sleep_mock.await_count == 5


@pytest.mark.asyncio
async def test_supprimer_derniere_iteration_sans_pause(cli_factory):
    app = _build_app(3)
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    sleep_mock = AsyncMock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", sleep_mock
    ):
        response = await _post_action(
            cli, {"intention": "supprimer", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )

    assert response.status == 200
    assert sleep_mock.await_count == 5


# --- AC1 : ligne de journal présente ---


@pytest.mark.asyncio
async def test_publier_journalise_ligne_action(cli_factory, caplog):
    app = _build_app(3)
    cli = await cli_factory(app)
    publisher = _publisher_mock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ), caplog.at_level("INFO"):
        response = await _post_action(
            cli, {"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )

    assert response.status == 200
    assert any("[ACTION] intention=publier" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_supprimer_journalise_ligne_action(cli_factory, caplog):
    app = _build_app(3)
    cli = await cli_factory(app)
    publisher = _publisher_mock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ), caplog.at_level("INFO"):
        response = await _post_action(
            cli, {"intention": "supprimer", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )

    assert response.status == 200
    assert any("[ACTION] intention=supprimer" in rec.message for rec in caplog.records)


# --- Revue Codex P2 (PR #189, tour 6) : la ligne de journal doit couvrir toute la
# finalisation démon (apply_pending_scope_flags + save_publications_cache), pas seulement
# la boucle de traitement des équipements ---


@pytest.mark.asyncio
async def test_publier_duree_journalisee_couvre_la_finalisation(cli_factory, caplog):
    app = _build_app(3)
    cli = await cli_factory(app)
    publisher = _publisher_mock()

    def _slow_save(*args, **kwargs):
        import time as _time

        _time.sleep(0.05)

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ), patch(
        "transport.http_server.save_publications_cache", side_effect=_slow_save
    ), caplog.at_level("INFO"):
        response = await _post_action(
            cli, {"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )

    assert response.status == 200
    record = next(rec for rec in caplog.records if "[ACTION] intention=publier" in rec.message)
    duree = float(record.message.split("duree_s=")[1].split(" ")[0])
    assert duree >= 0.05


@pytest.mark.asyncio
async def test_supprimer_duree_journalisee_couvre_la_finalisation(cli_factory, caplog):
    app = _build_app(3)
    cli = await cli_factory(app)
    publisher = _publisher_mock()

    def _slow_save(*args, **kwargs):
        import time as _time

        _time.sleep(0.05)

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", new=AsyncMock()
    ), patch(
        "transport.http_server.save_publications_cache", side_effect=_slow_save
    ), caplog.at_level("INFO"):
        response = await _post_action(
            cli, {"intention": "supprimer", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )

    assert response.status == 200
    record = next(rec for rec in caplog.records if "[ACTION] intention=supprimer" in rec.message)
    duree = float(record.message.split("duree_s=")[1].split(" ")[0])
    assert duree >= 0.05


# --- Revue Codex P2 (PR #189) : un équipement sauté (non mappable) après le dernier
# équipement qui travaille ne doit plus provoquer de pause finale ---


@pytest.mark.asyncio
async def test_publier_equipement_non_mappable_apres_le_dernier_sans_pause(cli_factory):
    """Publiable (eq 100) suivi d'un inclus mais non mappable (eq 101, aucune commande
    reconnue par un mapper) : sans ce correctif, le décompte en borne supérieure comptait
    eq 101 comme un travail à venir et faisait dormir après eq 100 (jusqu'à 5s à 2
    équipements). Avec le correctif, la pause se fait avant le travail (jamais pour le
    premier) : ici eq 100 est le premier ET le dernier à travailler, donc aucune pause."""
    mapping_100 = _light_mapping(100)
    eq_logics = {
        100: JeedomEqLogic(
            id=100, name="Lampe 100", object_id=1, is_enable=True,
            cmds=list(mapping_100.commands.values()),
        ),
        101: JeedomEqLogic(id=101, name="Non mappable 101", object_id=1, is_enable=True, cmds=[]),
    }
    topology = TopologySnapshot(
        timestamp="2026-09-30T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Salon")},
        eq_logics=eq_logics,
    )
    scope_equipements = [
        {"eq_id": 100, "object_id": 1, "name": "Lampe 100", "effective_state": "include",
         "decision_source": "global", "is_exception": False, "has_pending_home_assistant_changes": False},
        {"eq_id": 101, "object_id": 1, "name": "Non mappable 101", "effective_state": "include",
         "decision_source": "global", "is_exception": False, "has_pending_home_assistant_changes": False},
    ]
    eligibility = {
        100: EligibilityResult(is_eligible=True, reason_code="eligible"),
        101: EligibilityResult(is_eligible=True, reason_code="eligible"),
    }
    published_scope = {
        "global": {"counts": {"total": 2, "include": 2, "exclude": 0, "exceptions": 0},
                   "effective_state": "include", "has_pending_home_assistant_changes": False},
        "pieces": [],
        "equipements": scope_equipements,
    }
    app = http_server.create_app(local_secret=SECRET)
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app["mqtt_bridge"] = bridge
    app["topology"] = topology
    app["published_scope"] = published_scope
    app["eligibility"] = eligibility
    app["mappings"] = {100: mapping_100}
    app["publications"] = {}
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    sleep_mock = AsyncMock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", sleep_mock
    ):
        response = await _post_action(
            cli, {"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )

    assert response.status == 200
    # Revue Codex P2 (PR #189, 3e tour) : eq 101 (sauté) cède quand même la main en tête
    # d'itération (sleep(0), non compté dans les pauses) -> 2 cessions de tête, aucune pause
    # de lissage (eq 100 est le premier ET le dernier à travailler).
    assert sleep_mock.await_count == 2
    sleep_mock.assert_any_await(0)


# --- Revue Codex P2 (PR #189, 2e tour) : plafond épuisé -> cession de la main quand même ---


@pytest.mark.asyncio
async def test_publier_plafond_epuise_cede_la_main(cli_factory):
    """Une fois le plafond consommé, `prochaine_pause` renvoie 0 : le démon doit quand même
    céder la main via `asyncio.sleep(0)`, sans quoi la boucle aiohttp reste monopolisée par
    une longue action et un `/system/status` concurrent est servi en retard ou pas du tout."""
    app = _build_app(5)
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    sleep_mock = AsyncMock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", sleep_mock
    ), patch("transport.action_pacing.prochaine_pause", return_value=0.0):
        response = await _post_action(
            cli, {"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )

    assert response.status == 200
    # 5 équipements, la dernière itération jamais de pause -> 4 points de coopération de
    # lissage, tous à une pause nulle mais chacun cède quand même la main (sleep(0)).
    # Revue Codex P2 (PR #189, 3e tour) : + 5 cessions de tête d'itération (une par
    # équipement, non comptées dans les pauses) = 9.
    assert sleep_mock.await_count == 9
    sleep_mock.assert_any_await(0)


@pytest.mark.asyncio
async def test_supprimer_plafond_epuise_cede_la_main(cli_factory):
    app = _build_app(5)
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    sleep_mock = AsyncMock()

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.http_server.asyncio.sleep", sleep_mock
    ), patch("transport.action_pacing.prochaine_pause", return_value=0.0):
        response = await _post_action(
            cli, {"intention": "supprimer", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )

    assert response.status == 200
    assert sleep_mock.await_count == 9
    sleep_mock.assert_any_await(0)


@pytest.mark.asyncio
async def test_publier_plafond_epuise_status_concurrent_servi_pendant_action(cli_factory):
    """Intégration : pendant une action « publier » dont le plafond est épuisé, une requête
    GET /system/status concurrente doit être servie avant la fin de l'action (pas de blocage
    de la boucle aiohttp faute de point de coopération)."""
    app = _build_app(30)
    app["mqtt_bridge"].state = "connected"
    app["mqtt_bridge"].broker_info = "localhost:1883"
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    order = []

    async def do_action():
        resp = await _post_action(
            cli, {"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )
        order.append("action")
        return resp

    async def do_status():
        resp = await cli.get("/system/status", headers=VALID_HEADERS)
        order.append("status")
        return resp

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.action_pacing.prochaine_pause", return_value=0.0
    ):
        action_resp, status_resp = await asyncio.gather(do_action(), do_status())

    assert action_resp.status == 200
    assert status_resp.status == 200
    assert order[0] == "status"


# --- Revue Codex P2 (PR #189, 3e tour) : grande portée surtout ignorée -> cession de la
# main aussi sur les itérations sautées (sans dépendre du plafond des pauses) ---


@pytest.mark.asyncio
async def test_publier_grande_portee_ignoree_status_concurrent_servi_pendant_action(cli_factory):
    """500 équipements, dont 1 seul inclus/publiable : les 499 autres sont ignorés (exclus
    du scope, jamais publiés) et, avant ce correctif, ne cédaient jamais la main. Un
    `GET /system/status` concurrent doit être servi avant la fin de l'action."""
    app = _build_app(500, 1)
    app["mqtt_bridge"].state = "connected"
    app["mqtt_bridge"].broker_info = "localhost:1883"
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    order = []

    async def do_action():
        resp = await _post_action(
            cli, {"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )
        order.append("action")
        return resp

    async def do_status():
        resp = await cli.get("/system/status", headers=VALID_HEADERS)
        order.append("status")
        return resp

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        action_resp, status_resp = await asyncio.gather(do_action(), do_status())

    assert action_resp.status == 200
    assert status_resp.status == 200
    assert order[0] == "status"


@pytest.mark.asyncio
async def test_supprimer_grande_portee_ignoree_status_concurrent_servi_pendant_action(cli_factory):
    """500 équipements, dont 1 seul inclus/publié : les 499 autres ne sont pas publiés dans
    HA (skip immédiat) et, avant ce correctif, ne cédaient jamais la main."""
    app = _build_app(500, 1)
    app["mqtt_bridge"].state = "connected"
    app["mqtt_bridge"].broker_info = "localhost:1883"
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    order = []

    async def do_action():
        resp = await _post_action(
            cli, {"intention": "supprimer", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )
        order.append("action")
        return resp

    async def do_status():
        resp = await cli.get("/system/status", headers=VALID_HEADERS)
        order.append("status")
        return resp

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        action_resp, status_resp = await asyncio.gather(do_action(), do_status())

    assert action_resp.status == 200
    assert status_resp.status == 200
    assert order[0] == "status"


@pytest.mark.asyncio
async def test_supprimer_plafond_epuise_status_concurrent_servi_pendant_action(cli_factory):
    app = _build_app(30)
    app["mqtt_bridge"].state = "connected"
    app["mqtt_bridge"].broker_info = "localhost:1883"
    cli = await cli_factory(app)
    publisher = _publisher_mock()
    order = []

    async def do_action():
        resp = await _post_action(
            cli, {"intention": "supprimer", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
        )
        order.append("action")
        return resp

    async def do_status():
        resp = await cli.get("/system/status", headers=VALID_HEADERS)
        order.append("status")
        return resp

    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher), patch(
        "transport.action_pacing.prochaine_pause", return_value=0.0
    ):
        action_resp, status_resp = await asyncio.gather(do_action(), do_status())

    assert action_resp.status == 200
    assert status_resp.status == 200
    assert order[0] == "status"
