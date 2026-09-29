"""Story 19.4 unité 3a — `_collect_candidate_node_ids` : la contribution d'un
SEUL candidat (principal ou secondaire) à `_collect_unpublish_node_ids`, sans
changer le résultat de cette dernière (préparation de l'unité 3b : node_ids
par candidat).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from mapping.registry import MapperRegistry
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from transport.http_server import (
    _collect_candidate_node_ids,
    _collect_unpublish_node_ids,
    create_app,
)

SECRET = "test-secret-19-4-candidate-node-ids"
GOLDEN_CORPUS_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "golden_corpus" / "sync_payload.json"
)


def _load_golden_corpus() -> dict[str, Any]:
    with GOLDEN_CORPUS_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _connected_bridge_into(app) -> None:
    from unittest.mock import MagicMock

    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    app["mqtt_bridge"] = bridge


def _assert_decomposition_matches(mapping) -> list[list[Any]]:
    """Concaténer les contributions par candidat doit reproduire exactement
    `_collect_unpublish_node_ids(mapping)` — c'est l'invariant que l'unité 3b
    exploitera pour construire des appels `unpublish_by_eq_id` par candidat."""
    secondaries = list(getattr(mapping, "additional_mappings", None) or [])
    candidates = [mapping, *secondaries]
    contributions = [_collect_candidate_node_ids(mapping, c) for c in candidates]
    flattened = [item for contribution in contributions for item in contribution]
    assert flattened == _collect_unpublish_node_ids(mapping)
    return contributions


@pytest.fixture
async def synced_mappings(aiohttp_client):
    """Toutes les `MappingResult` publiées par un sync réel du corpus doré."""
    app = create_app(local_secret=SECRET)
    _connected_bridge_into(app)
    cli = await aiohttp_client(app)
    corpus = _load_golden_corpus()
    body = {
        "action": "sync",
        "payload": {
            "objects": corpus["objects"],
            "eq_logics": corpus["eq_logics"],
            "sync_config": corpus.get("sync_config", {"confidence_policy": "sure_probable"}),
        },
        "request_id": "19-4-candidate-node-ids",
        "timestamp": "2026-09-29T00:00:00Z",
    }
    resp = await cli.post("/action/sync", json=body, headers={"X-Local-Secret": SECRET})
    assert resp.status == 200, await resp.text()
    return app["mappings"]


async def test_decomposition_matches_for_every_golden_corpus_mapping(synced_mappings):
    """Égalité exacte avec l'ancien résultat, pour chaque mapping publié par le
    sync du corpus doré."""
    assert synced_mappings, "corpus doré vide : la fixture a dérivé"
    for mapping in synced_mappings.values():
        _assert_decomposition_matches(mapping)


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-09-28T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Energie")},
        eq_logics={eq.id: eq},
    )


def _eq628_multi_switch() -> Any:
    """Fixture 19-2 (eq628, Story 11.3/19.2) : 1 principal + 3 secondaires
    homogènes (tous SWITCH_STATE) — cas per-cmd_id, pas de node_id explicite."""
    eq = JeedomEqLogic(
        id=628,
        name="Pilotage priorisation solaire",
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            JeedomCmd(id=5977, name="Filtration piscine", type="info", sub_type="binary", generic_type="SWITCH_STATE"),
            JeedomCmd(id=5978, name="Filtration On", type="action", sub_type="other", generic_type="SWITCH_ON"),
            JeedomCmd(id=5979, name="Filtration Off", type="action", sub_type="other", generic_type="SWITCH_OFF"),
            JeedomCmd(id=5980, name="Chauffage piscine", type="info", sub_type="binary", generic_type="SWITCH_STATE"),
            JeedomCmd(id=5981, name="Chauffage On", type="action", sub_type="other", generic_type="SWITCH_ON"),
            JeedomCmd(id=5982, name="Chauffage Off", type="action", sub_type="other", generic_type="SWITCH_OFF"),
            JeedomCmd(id=5983, name="Chauffage SPA", type="info", sub_type="binary", generic_type="SWITCH_STATE"),
            JeedomCmd(id=5984, name="SPA On", type="action", sub_type="other", generic_type="SWITCH_ON"),
            JeedomCmd(id=5985, name="SPA Off", type="action", sub_type="other", generic_type="SWITCH_OFF"),
        ],
    )
    return MapperRegistry().map(eq, _snapshot(eq))


def test_decomposition_matches_for_19_2_eq628_fixture():
    mapping = _eq628_multi_switch()
    assert mapping.additional_mappings, "eq628 fixture drifted: secondaires attendus"
    _assert_decomposition_matches(mapping)


def test_mono_entity_primary_contributes_nothing():
    eq = JeedomEqLogic(
        id=7000,
        name="Capteur",
        object_id=1,
        eq_type_name="virtual",
        cmds=[JeedomCmd(id=70001, name="Temp", type="info", sub_type="numeric", generic_type="TEMPERATURE")],
    )
    mapping = MapperRegistry().map(eq, _snapshot(eq))
    assert not getattr(mapping, "additional_mappings", None)
    assert _collect_candidate_node_ids(mapping, mapping) == []
    assert _collect_unpublish_node_ids(mapping) == []


def test_eq583_multi_domain_one_contribution_per_candidate_no_duplicates(synced_mappings):
    """583 (corpus doré) est multi-domaine (switch + sensor) : chaque candidat
    contribue un tuple `(type, node_id)` distinct, sans doublon."""
    mapping = synced_mappings[583]
    secondaries = list(getattr(mapping, "additional_mappings", None) or [])
    assert secondaries, "eq583 fixture drifted: secondaires attendus"
    candidates = [mapping, *secondaries]
    contributions = _assert_decomposition_matches(mapping)
    assert len(contributions) == len(candidates)
    assert all(len(c) == 1 for c in contributions), "un seul candidat mono-entité par contribution"
    flattened = [c[0] for c in contributions]
    assert len(flattened) == len(set(flattened)), f"doublon détecté : {flattened}"
    assert all(isinstance(item, tuple) and len(item) == 2 for item in flattened)


def test_eq553_homogeneous_one_contribution_per_candidate_no_duplicates(synced_mappings):
    """553 (MSunPV, corpus doré) est homogène (multi-sensor) : chaque candidat
    contribue au plus un `node_id` (chaîne), sans doublon."""
    mapping = synced_mappings[553]
    secondaries = list(getattr(mapping, "additional_mappings", None) or [])
    assert secondaries, "eq553 fixture drifted: secondaires attendus"
    candidates = [mapping, *secondaries]
    contributions = _assert_decomposition_matches(mapping)
    assert len(contributions) == len(candidates)
    assert all(len(c) <= 1 for c in contributions), "un seul node_id par contribution homogène"
    flattened = [c[0] for c in contributions if c]
    assert len(flattened) == len(set(flattened)), f"doublon détecté : {flattened}"
    assert all(isinstance(item, str) for item in flattened)
