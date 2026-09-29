"""Story 19.4 — « Publier » en mini-sync (tests d'acceptation rédigés par ClaudeBox).

« Publier » doit prendre la MÊME décision que le sync : `evaluate_equipment()` frais
(overrides relus au clic, politique de confiance du dernier sync), puis le post-traitement
partagé `apply_publication_decision()` et la dépublication par candidat.

- P1 (AC1) : une confiance `sure_mapping` acceptée par la décision est publiée.
- P2 (AC2, AC4) : une exclusion d'équipement posée après le sync est respectée au clic,
  et l'équipement déjà publié est dépublié.
- P3 (AC5) : deux clics successifs ⇒ aucune dépublication, mêmes topics, même contenu.
- P4 (AC6) : une exclusion de commande posée après le sync retire ce seul secondaire.
- P5 (C2) : un retypage (override de type) suivi d'un clic dépublie l'ancien topic.
- P6 : un équipement que le sync refuse (eq 6000, projection invalide) n'est pas publié.
- P7 : forme 579/585 (principal refusé, secondaires acceptés) : le clic publie les
  secondaires et leur disponibilité, jamais le principal.
- P8 : une dépublication reportée (pont coupé au sync) est rejouée par le clic au lieu
  d'être oubliée, sans toucher aux secondaires acceptés.
- P9, P10 (revue Codex P2, PR #180) : un secondaire accepté dont la publication échoue
  au clic fait compter l'équipement en erreur, que le principal soit accepté (P9) ou
  refusé (P10) ; le clic ne répond jamais « succès » ni « déjà à jour ».

Étaient en `xfail(strict=True)` avant le branchement du mini-sync (unité 4).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, patch

from mapping.overrides import save_equipment_override, save_override
from transport.http_server import create_app


def _load_sibling(filename: str):
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location(f"{path.stem}_publier", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


G = _load_sibling("test_story_19_4_guard_publisher_calls.py")


def _topic(entity_type: str, node: str) -> str:
    return f"homeassistant/{entity_type}/{node}/config"


def _published(bridge) -> list[str]:
    return [c["topic"] for c in bridge.calls if c["payload"] != ""]


def _deleted(bridge) -> list[str]:
    return [c["topic"] for c in bridge.calls if c["payload"] == ""]


def _avail(bridge, eq_id: int) -> list[str]:
    topic = f"jeedom2ha/{eq_id}/availability"
    return [c["payload"] for c in bridge.avail_calls if c["topic"] == topic]


def _reset(bridge) -> None:
    bridge.calls.clear()
    bridge.avail_calls.clear()


async def _client(aiohttp_client, tmp_path):
    app = create_app(local_secret=G.SECRET)
    app["data_dir"] = str(tmp_path)
    bridge = G.MqttRecordingBridge()
    app["mqtt_bridge"] = bridge
    return await aiohttp_client(app), app, bridge


async def _golden_sync(aiohttp_client, tmp_path):
    cli, app, bridge = await _client(aiohttp_client, tmp_path)
    await G._post_sync(cli, G._sync_body(G._load_golden_corpus(), request_id="golden"))
    _reset(bridge)
    return cli, app, bridge


async def _publier(cli, portee: str, selection: list) -> None:
    body = {"intention": "publier", "portee": portee, "selection": selection}
    with patch("transport.http_server.asyncio.sleep", new=AsyncMock()):
        resp = await cli.post("/action/execute", json=body, headers={"X-Local-Secret": G.SECRET})
    assert resp.status == 200, await resp.text()


def _cmd_id(app, eq_id: int, generic_type: str) -> int:
    return app["mappings"][eq_id].commands[generic_type].id


def _i11_sure_mapping_evaluation(*_args, **_kwargs):
    evaluation = G._i11_evaluation_with(principal_should_publish=True)
    evaluation.mapping.confidence = "sure_mapping"
    evaluation.equipment_decision.reason = "sure_mapping"
    return evaluation


def _i11_principal_refuse_evaluation(*_args, **_kwargs):
    return G._i11_evaluation_with(principal_should_publish=False)


async def _i11_sync_then_publier(aiohttp_client, tmp_path, evaluation_factory):
    cli, app, bridge = await _client(aiohttp_client, tmp_path)
    with patch("transport.http_server.evaluate_equipment", side_effect=evaluation_factory):
        await G._post_sync(cli, G._sync_body(G._i11_corpus(), request_id="i11-sync"))
        _reset(bridge)
        await _publier(cli, "equipement", [628])
    return bridge


async def test_p1_sure_mapping_publie_par_publier(aiohttp_client, tmp_path):
    bridge = await _i11_sync_then_publier(aiohttp_client, tmp_path, _i11_sure_mapping_evaluation)

    assert _topic("switch", "jeedom2ha_628_5977") in _published(bridge)
    assert _deleted(bridge) == []


async def test_p2_exclusion_equipement_posee_apres_le_sync(aiohttp_client, tmp_path):
    cli, app, bridge = await _golden_sync(aiohttp_client, tmp_path)
    save_equipment_override(1000, {"publication_override": "exclude"}, str(tmp_path))

    await _publier(cli, "equipement", [1000])

    assert _deleted(bridge) == [_topic("light", "jeedom2ha_1000")]
    assert _published(bridge) == []
    assert _avail(bridge, 1000)[-1:] == [""]


async def test_p3_deux_clics_idempotents(aiohttp_client, tmp_path):
    cli, app, bridge = await _golden_sync(aiohttp_client, tmp_path)
    await _publier(cli, "global", list(app["topology"].eq_logics.keys()))
    first = (list(bridge.calls), list(bridge.avail_calls))
    _reset(bridge)
    await _publier(cli, "global", list(app["topology"].eq_logics.keys()))
    second = (list(bridge.calls), list(bridge.avail_calls))

    assert _deleted(bridge) == []
    assert second == first


async def test_p4_exclusion_commande_secondaire_apres_le_sync(aiohttp_client, tmp_path):
    cli, app, bridge = await _golden_sync(aiohttp_client, tmp_path)
    save_override(553, 5137, {"publication_override": "exclude"}, str(tmp_path))

    await _publier(cli, "equipement", [553])

    assert _deleted(bridge) == [_topic("sensor", "jeedom2ha_553_5137")]
    assert _topic("sensor", "jeedom2ha_553_5137") not in _published(bridge)
    assert _topic("sensor", "jeedom2ha_553_5139") in _published(bridge)


async def test_p5_retypage_puis_publier_depublie_l_ancien_topic(aiohttp_client, tmp_path):
    cli, app, bridge = await _golden_sync(aiohttp_client, tmp_path)
    save_override(3000, _cmd_id(app, 3000, "ENERGY_ON"), {"ha_entity_type": "light"}, str(tmp_path))

    await _publier(cli, "equipement", [3000])

    assert _topic("switch", "jeedom2ha_3000") in _deleted(bridge)
    assert _topic("light", "jeedom2ha_3000") in _published(bridge)


async def test_p6_equipement_refuse_par_le_sync_jamais_publie(aiohttp_client, tmp_path):
    cli, app, bridge = await _golden_sync(aiohttp_client, tmp_path)

    await _publier(cli, "equipement", [6000])

    assert _published(bridge) == []


async def test_p7_forme_579_publier_publie_les_secondaires(aiohttp_client, tmp_path):
    bridge = await _i11_sync_then_publier(aiohttp_client, tmp_path, _i11_principal_refuse_evaluation)

    assert set(_published(bridge)) == {_topic("switch", f"jeedom2ha_628_{c}") for c in (5980, 5983, 6004)}
    assert _deleted(bridge) == []
    assert _avail(bridge, 628) == ["online"]


async def test_p8_report_en_attente_rejoue_par_publier(aiohttp_client, tmp_path):
    cli, app, bridge = await _client(aiohttp_client, tmp_path)
    accepted = lambda *_a, **_k: G._i11_evaluation_with(principal_should_publish=True)  # noqa: E731
    with patch("transport.http_server.evaluate_equipment", side_effect=accepted):
        await G._post_sync(cli, G._sync_body(G._i11_corpus(), request_id="p8-1"))
    bridge.is_connected = False
    with patch("transport.http_server.evaluate_equipment", side_effect=_i11_principal_refuse_evaluation):
        await G._post_sync(cli, G._sync_body(G._i11_corpus(), request_id="p8-2"))
        assert 628 in app["pending_discovery_unpublish"]
        bridge.is_connected = True
        _reset(bridge)
        await _publier(cli, "equipement", [628])

    assert _deleted(bridge) == [_topic("switch", "jeedom2ha_628_5977")]
    assert 628 not in app["pending_discovery_unpublish"]


class _FailingTopicsBridge(G.MqttRecordingBridge):
    """Faux pont dont la publication échoue pour les topics listés dans `failing`."""

    def __init__(self) -> None:
        super().__init__()
        self.failing: set[str] = set()

    def publish_message(self, topic, payload, qos=0, retain=False):
        if topic in self.failing and payload:
            return False
        return super().publish_message(topic, payload, qos, retain)


async def _publier_avec_echecs(aiohttp_client, tmp_path, evaluation_factory, failing) -> dict:
    app = create_app(local_secret=G.SECRET)
    app["data_dir"] = str(tmp_path)
    bridge = _FailingTopicsBridge()
    app["mqtt_bridge"] = bridge
    cli = await aiohttp_client(app)
    body = {"intention": "publier", "portee": "equipement", "selection": [628]}
    with patch("transport.http_server.evaluate_equipment", side_effect=evaluation_factory):
        await G._post_sync(cli, G._sync_body(G._i11_corpus(), request_id="i11-sync"))
        bridge.failing = set(failing)
        with patch("transport.http_server.asyncio.sleep", new=AsyncMock()):
            resp = await cli.post("/action/execute", json=body, headers={"X-Local-Secret": G.SECRET})
    assert resp.status == 200, await resp.text()
    return (await resp.json())["payload"]


def _i11_principal_accepte_evaluation(*_args, **_kwargs):
    return G._i11_evaluation_with(principal_should_publish=True)


async def test_p9_principal_accepte_secondaire_en_echec_compte_en_erreur(aiohttp_client, tmp_path):
    payload = await _publier_avec_echecs(
        aiohttp_client, tmp_path, _i11_principal_accepte_evaluation,
        failing={_topic("switch", "jeedom2ha_628_5980")},
    )

    assert payload["resultat"] == "echec"
    assert payload["scope_reel"]["equipements_publies_ou_crees"] == 0


async def test_p10_principal_refuse_secondaires_en_echec_compte_en_erreur(aiohttp_client, tmp_path):
    payload = await _publier_avec_echecs(
        aiohttp_client, tmp_path, _i11_principal_refuse_evaluation,
        failing={_topic("switch", f"jeedom2ha_628_{c}") for c in (5980, 5983, 6004)},
    )

    assert payload["resultat"] == "echec"
    assert payload["message"] != "Configuration déjà à jour dans Home Assistant."
