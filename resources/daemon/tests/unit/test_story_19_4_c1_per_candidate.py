"""Story 19.4 — C1 : dépublication par candidat (tests d'acceptation rédigés par ClaudeBox).

Candidat de type eq 628 (fixture 19-2) : un principal switch et 3 secondaires switch,
chacun sous son propre topic `homeassistant/switch/jeedom2ha_628_<cmd>/config`.
`evaluate_equipment` est patché à chaque sync ; le vrai `DiscoveryPublisher` tourne
sur le faux pont du garde-fou (`MqttRecordingBridge`), qui enregistre la discovery et
la disponibilité locale.

- T1, T2, T4 : `xfail(strict=True)` tant que C1 n'est pas corrigé (unité 3b-2).
- T3 : garde contre la régression, vert aujourd'hui (tout refusé ⇒ tout part).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

from transport.http_server import create_app


def _load_sibling(filename: str):
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location(f"{path.stem}_c1", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


G = _load_sibling("test_story_19_4_guard_publisher_calls.py")

XFAIL_C1 = "C1 : dépublication par candidat, corrigée à l'unité 3b-2"
SECONDARY_CMDS = (5980, 5983, 6004)
PRINCIPAL_TOPIC = "homeassistant/switch/jeedom2ha_628_5977/config"
AVAIL_TOPIC = "jeedom2ha/628/availability"


def _topic(cmd_id: int) -> str:
    return f"homeassistant/switch/jeedom2ha_628_{cmd_id}/config"


ALL_TOPICS = {PRINCIPAL_TOPIC} | {_topic(c) for c in SECONDARY_CMDS}


async def _new_client(aiohttp_client):
    app = create_app(local_secret=G.SECRET)
    bridge = G.MqttRecordingBridge()
    app["mqtt_bridge"] = bridge
    return await aiohttp_client(app), bridge


async def _sync(cli, *, principal: bool, refused=(), request_id: str) -> None:
    def _evaluation(*_args, **_kwargs):
        return G._i11_evaluation_with(
            principal_should_publish=principal, refused_cmd_ids=frozenset(refused)
        )

    with patch("transport.http_server.evaluate_equipment", side_effect=_evaluation):
        await G._post_sync(cli, G._sync_body(G._i11_corpus(), request_id=request_id))


def _deleted(bridge) -> list[str]:
    return [c["topic"] for c in bridge.calls if c["payload"] == ""]


def _avail_payloads(bridge) -> list[str]:
    return [c["payload"] for c in bridge.avail_calls if c["topic"] == AVAIL_TOPIC]


def _reset(bridge) -> None:
    bridge.calls.clear()
    bridge.avail_calls.clear()


async def test_sanity_sync1_publie_les_4_topics(aiohttp_client):
    """Contrôle de la fixture : tout accepté ⇒ les 4 topics publiés, dispo `online`."""
    cli, bridge = await _new_client(aiohttp_client)
    await _sync(cli, principal=True, request_id="s-1")
    published = {c["topic"] for c in bridge.calls if c["payload"] != ""}
    assert published == ALL_TOPICS
    assert _avail_payloads(bridge) == ["online"]


@pytest.mark.xfail(strict=True, reason=XFAIL_C1)
async def test_t1_principal_refuse_les_secondaires_acceptes_restent(aiohttp_client):
    """C1 (i) : le principal passe de publié à refusé, les secondaires restent acceptés."""
    cli, bridge = await _new_client(aiohttp_client)
    await _sync(cli, principal=True, request_id="t1-1")
    _reset(bridge)
    await _sync(cli, principal=False, request_id="t1-2")

    assert _deleted(bridge) == [PRINCIPAL_TOPIC]
    assert "" not in _avail_payloads(bridge), "la disponibilité ne doit pas être effacée"


@pytest.mark.xfail(strict=True, reason=XFAIL_C1)
async def test_t2_secondaire_refuse_seul_lui_part(aiohttp_client):
    """C1 (ii) : le principal reste accepté, le secondaire 5980 passe d'accepté à refusé."""
    cli, bridge = await _new_client(aiohttp_client)
    await _sync(cli, principal=True, request_id="t2-1")
    _reset(bridge)
    await _sync(cli, principal=True, refused=(5980,), request_id="t2-2")

    assert _deleted(bridge) == [_topic(5980)]
    assert "" not in _avail_payloads(bridge)


async def test_t3_tout_refuse_tout_part(aiohttp_client):
    """Garde : principal et secondaires refusés ⇒ les 4 topics et la dispo sont effacés."""
    cli, bridge = await _new_client(aiohttp_client)
    await _sync(cli, principal=True, request_id="t3-1")
    _reset(bridge)
    await _sync(cli, principal=False, refused=SECONDARY_CMDS, request_id="t3-2")

    assert set(_deleted(bridge)) == ALL_TOPICS
    assert _avail_payloads(bridge)[-1:] == [""]


@pytest.mark.xfail(strict=True, reason=XFAIL_C1)
async def test_t4_pont_coupe_puis_rejeu_seul_le_principal_part(aiohttp_client):
    """C1 (i) avec pont déconnecté au sync 2 : le rejeu au sync 3 ne doit effacer que
    le principal ; aucun secondaire accepté n'est effacé, même temporairement."""
    cli, bridge = await _new_client(aiohttp_client)
    await _sync(cli, principal=True, request_id="t4-1")
    _reset(bridge)

    bridge.is_connected = False
    await _sync(cli, principal=False, request_id="t4-2")
    bridge.is_connected = True
    await _sync(cli, principal=False, request_id="t4-3")

    assert _deleted(bridge) == [PRINCIPAL_TOPIC]
    assert "" not in _avail_payloads(bridge)
