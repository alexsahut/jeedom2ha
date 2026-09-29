"""Story 19.4 — C1 : dépublication par candidat (tests d'acceptation rédigés par ClaudeBox).

Candidat de type eq 628 (fixture 19-2) : un principal switch et 3 secondaires switch,
chacun sous son propre topic `homeassistant/switch/jeedom2ha_628_<cmd>/config`.
`evaluate_equipment` est patché à chaque sync ; le vrai `DiscoveryPublisher` tourne
sur le faux pont du garde-fou (`MqttRecordingBridge`), qui enregistre la discovery et
la disponibilité locale.

- T1, T2, T4 : C1 corrigé (unité 3b-2) ; ils étaient en `xfail(strict=True)` avant.
- T3 : garde contre la régression (tout refusé ⇒ tout part).
- T5 : un secondaire qui partage le topic du principal n'est jamais dépublié seul.
- T6 : forme 579/585 (principal jamais publié) dont tous les candidats deviennent refusés.
- T7 : un report de dépublication par candidat n'écrase pas un report existant.
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


async def test_t1_principal_refuse_les_secondaires_acceptes_restent(aiohttp_client):
    """C1 (i) : le principal passe de publié à refusé, les secondaires restent acceptés."""
    cli, bridge = await _new_client(aiohttp_client)
    await _sync(cli, principal=True, request_id="t1-1")
    _reset(bridge)
    await _sync(cli, principal=False, request_id="t1-2")

    assert _deleted(bridge) == [PRINCIPAL_TOPIC]
    assert "" not in _avail_payloads(bridge), "la disponibilité ne doit pas être effacée"


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


def test_t5_secondaire_partageant_le_topic_du_principal_jamais_depublie_seul():
    """Multi-domaine, principal sans node_id : un secondaire du même type sans node_id
    a la même entrée que le principal (topic de niveau équipement). S'il devient refusé
    alors que le principal reste accepté, cette entrée ne doit pas être dépubliée."""
    from transport.http_server import _refused_candidate_entries

    def _shaped(refused):
        story_19_2 = G._load_sibling_module("test_story_19_2_decouplage_state_command_i11.py")
        primary, decision = story_19_2._build_multi_switch(
            principal_should_publish=True, refused_cmd_ids=frozenset(refused)
        )
        primary.reason_details.pop("node_id", None)
        by_cmd = {s.reason_details["cmd_id"]: s for s in primary.additional_mappings}
        by_cmd[6004].ha_entity_type = "sensor"
        by_cmd[5983].reason_details.pop("node_id", None)
        return decision

    previous, current = _shaped(()), _shaped((5983,))
    assert ("switch", "jeedom2ha_628") not in _refused_candidate_entries(previous, current)
    assert _refused_candidate_entries(previous, current) == []


async def test_t6_forme_579_tous_refuses_tout_part(aiohttp_client):
    """Principal jamais publié, secondaires publiés, puis tout refusé : les topics des
    secondaires sont effacés, et la disponibilité aussi."""
    cli, bridge = await _new_client(aiohttp_client)
    await _sync(cli, principal=False, request_id="t6-1")
    _reset(bridge)
    await _sync(cli, principal=False, refused=SECONDARY_CMDS, request_id="t6-2")

    assert {_topic(c) for c in SECONDARY_CMDS} <= set(_deleted(bridge))
    assert _avail_payloads(bridge)[-1:] == [""]


def test_t7_report_par_candidat_sans_ecrasement():
    """Un report existant (topic de niveau équipement) est conservé et complété."""
    from transport.http_server import _merge_deferred_candidate_unpublish, _pending_unpublish_parts

    pending = {628: {"entity_type": "switch", "node_ids": []}}
    _merge_deferred_candidate_unpublish(pending, 628, "switch", [("switch", "jeedom2ha_628_5980")])

    entity_type, node_ids = _pending_unpublish_parts(pending[628])
    assert entity_type == "switch"
    assert node_ids == [("switch", "jeedom2ha_628"), ("switch", "jeedom2ha_628_5980")]
