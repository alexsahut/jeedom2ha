"""Story 19.4b — CC-30 et CC-31 (revue Codex de `7fabeb0`, tests d'acceptation rédigés par ClaudeBox).

Forme 579/585 (fixture eq628 de 19-2) : le principal est refusé, ses 3 secondaires switch
sont publiés chacun sous `homeassistant/switch/jeedom2ha_628_<cmd>/config`.

CC-30 — un équipement de cette forme qui sort du sync, ou qu'on supprime, doit voir ses
secondaires dépubliés et sa disponibilité effacée (le principal seul ne suffit pas) :
- U1 : l'équipement disparaît de Jeedom ;
- U2 : il sort du périmètre publié (scope `exclude`) ;
- U3 : il est désactivé dans Jeedom ;
- U4 : action « Supprimer » ;
- U5 : premier sync après un redémarrage du démon (cache disque).

CC-31 — une dépublication reportée (publication MQTT vide en échec, pont connecté) n'est
pas une résolution : « Publier » la compte en erreur, jamais en « succès » :
- V1 : tous les candidats deviennent refusés au clic ;
- V2 : un seul secondaire devient refusé au clic ;
- V3 : l'équipement est hors périmètre au clic.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, patch

from cache.disk_cache import load_publications_cache
from transport.http_server import create_app


def _load_sibling(filename: str):
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location(f"{path.stem}_19_4b", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


G = _load_sibling("test_story_19_4_guard_publisher_calls.py")

SECONDARY_CMDS = (5980, 5983, 6004)
PRINCIPAL_TOPIC = "homeassistant/switch/jeedom2ha_628_5977/config"
AVAIL_TOPIC = "jeedom2ha/628/availability"
HEADERS = {"X-Local-Secret": G.SECRET}


def _topic(cmd_id: int) -> str:
    return f"homeassistant/switch/jeedom2ha_628_{cmd_id}/config"


SECONDARY_TOPICS = {_topic(c) for c in SECONDARY_CMDS}


class _FailingDeletesBridge(G.MqttRecordingBridge):
    """Faux pont dont l'effacement (payload vide) échoue pour les topics de `failing`."""

    def __init__(self) -> None:
        super().__init__()
        self.failing: set[str] = set()

    def publish_message(self, topic, payload, qos=0, retain=False):
        if topic in self.failing and payload == "":
            return False
        return super().publish_message(topic, payload, qos, retain)


def _evaluation(principal: bool, refused=()):
    def _factory(*_args, **_kwargs):
        return G._i11_evaluation_with(
            principal_should_publish=principal, refused_cmd_ids=frozenset(refused)
        )

    return _factory


def _corpus(**eq_overrides) -> dict:
    corpus = G._i11_corpus()
    corpus["eq_logics"][0].update(eq_overrides)
    return corpus


async def _app(aiohttp_client, tmp_path, bridge=None):
    app = create_app(local_secret=G.SECRET)
    app["data_dir"] = str(tmp_path)
    bridge = bridge or _FailingDeletesBridge()
    app["mqtt_bridge"] = bridge
    return await aiohttp_client(app), app, bridge


async def _sync(cli, corpus: dict, request_id: str, *, principal=False, refused=(), scope=None) -> None:
    body = G._sync_body(corpus, request_id=request_id)
    if scope is not None:
        body["payload"]["published_scope"] = scope
    with patch("transport.http_server.evaluate_equipment", side_effect=_evaluation(principal, refused)):
        await G._post_sync(cli, body)


async def _action(cli, intention: str, portee: str, selection: list, *, principal=False, refused=()) -> dict:
    body = {"intention": intention, "portee": portee, "selection": selection}
    with patch("transport.http_server.evaluate_equipment", side_effect=_evaluation(principal, refused)):
        with patch("transport.http_server.asyncio.sleep", new=AsyncMock()):
            resp = await cli.post("/action/execute", json=body, headers=HEADERS)
    assert resp.status == 200, await resp.text()
    return (await resp.json())["payload"]


def _published(bridge) -> set[str]:
    return {c["topic"] for c in bridge.calls if c["payload"] != ""}


def _deleted(bridge) -> set[str]:
    return {c["topic"] for c in bridge.calls if c["payload"] == ""}


def _avail(bridge) -> list[str]:
    return [c["payload"] for c in bridge.avail_calls if c["topic"] == AVAIL_TOPIC]


def _reset(bridge) -> None:
    bridge.calls.clear()
    bridge.avail_calls.clear()


async def _forme_579_publiee(aiohttp_client, tmp_path):
    """Sync 1 : principal refusé, 3 secondaires publiés, disponibilité `online`."""
    cli, app, bridge = await _app(aiohttp_client, tmp_path)
    await _sync(cli, _corpus(), "s-1")
    assert _published(bridge) == SECONDARY_TOPICS
    assert PRINCIPAL_TOPIC not in _published(bridge)
    assert _avail(bridge)[-1:] == ["online"]
    _reset(bridge)
    return cli, app, bridge


# ---------------------------------------------------------------------------
# CC-30 — la purge et « Supprimer » dépublient les secondaires de la forme 579/585
# ---------------------------------------------------------------------------


async def test_u1_equipement_disparu_ses_secondaires_partent(aiohttp_client, tmp_path):
    cli, app, bridge = await _forme_579_publiee(aiohttp_client, tmp_path)
    corpus = G._i11_corpus()
    corpus["eq_logics"] = []

    await _sync(cli, corpus, "u1-2")

    assert SECONDARY_TOPICS <= _deleted(bridge)
    assert _avail(bridge)[-1:] == [""]


async def test_u2_sorti_du_perimetre_ses_secondaires_partent(aiohttp_client, tmp_path):
    cli, app, bridge = await _forme_579_publiee(aiohttp_client, tmp_path)
    scope = {"equipements": {"628": {"raw_state": "exclude", "source": "equipement"}}}

    await _sync(cli, _corpus(), "u2-2", scope=scope)

    assert SECONDARY_TOPICS <= _deleted(bridge)
    assert _avail(bridge)[-1:] == [""]
    assert app["publications"][628].reason == "excluded"


async def test_u3_desactive_ses_secondaires_partent(aiohttp_client, tmp_path):
    cli, app, bridge = await _forme_579_publiee(aiohttp_client, tmp_path)

    await _sync(cli, _corpus(is_enable=False), "u3-2")

    assert SECONDARY_TOPICS <= _deleted(bridge)
    assert _avail(bridge)[-1:] == [""]


async def test_u4_supprimer_efface_les_secondaires(aiohttp_client, tmp_path):
    cli, app, bridge = await _forme_579_publiee(aiohttp_client, tmp_path)

    payload = await _action(cli, "supprimer", "equipement", [628])

    assert SECONDARY_TOPICS <= _deleted(bridge)
    assert _avail(bridge)[-1:] == [""]
    assert payload["resultat"] == "succes"


async def test_u5_premier_sync_apres_redemarrage_purge_depuis_le_cache(aiohttp_client, tmp_path):
    await _forme_579_publiee(aiohttp_client, tmp_path)
    boot_cache = load_publications_cache(str(tmp_path))
    assert boot_cache[628]["secondaries_published"] is True

    cli, app, bridge = await _app(aiohttp_client, tmp_path)
    app["boot_cache"] = boot_cache
    corpus = G._i11_corpus()
    corpus["eq_logics"] = []
    await _sync(cli, corpus, "u5-boot")

    assert SECONDARY_TOPICS <= _deleted(bridge)
    assert _avail(bridge)[-1:] == [""]


# ---------------------------------------------------------------------------
# CC-31 — une dépublication reportée n'est pas une résolution
# ---------------------------------------------------------------------------


async def test_v1_tout_refuse_au_clic_effacement_en_echec_compte_en_erreur(aiohttp_client, tmp_path):
    cli, app, bridge = await _app(aiohttp_client, tmp_path)
    await _sync(cli, _corpus(), "v1-1", principal=True)
    bridge.failing = SECONDARY_TOPICS | {PRINCIPAL_TOPIC}

    payload = await _action(
        cli, "publier", "equipement", [628], principal=False, refused=SECONDARY_CMDS
    )

    assert 628 in app["pending_discovery_unpublish"]
    assert payload["resultat"] == "echec"
    assert payload["message"] != "Configuration déjà à jour dans Home Assistant."


async def test_v2_un_secondaire_refuse_au_clic_effacement_en_echec(aiohttp_client, tmp_path):
    cli, app, bridge = await _app(aiohttp_client, tmp_path)
    await _sync(cli, _corpus(), "v2-1", principal=True)
    bridge.failing = {_topic(5980)}

    payload = await _action(cli, "publier", "equipement", [628], principal=True, refused=(5980,))

    assert 628 in app["pending_discovery_unpublish"]
    assert payload["resultat"] == "echec"
    assert payload["scope_reel"]["equipements_publies_ou_crees"] == 0


async def test_v3_hors_perimetre_au_clic_effacement_en_echec(aiohttp_client, tmp_path):
    cli, app, bridge = await _app(aiohttp_client, tmp_path)
    await _sync(cli, _corpus(), "v3-1", principal=True)
    for entry in app["published_scope"]["equipements"]:
        if int(entry["eq_id"]) == 628:
            entry["effective_state"] = "exclude"
    bridge.failing = SECONDARY_TOPICS | {PRINCIPAL_TOPIC}

    payload = await _action(cli, "publier", "equipement", [628], principal=True)

    assert 628 in app["pending_discovery_unpublish"]
    assert payload["resultat"] == "echec"
    assert payload["message"] != "Configuration déjà à jour dans Home Assistant."
