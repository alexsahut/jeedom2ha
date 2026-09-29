"""Story 19.4 — garde-fou du publisher factice (C5, note §8 unité #1), sur le code ACTUEL.

Fige la séquence d'appels publish/unpublish (via un `DiscoveryPublisher` factice qui
journalise chaque appel) pour 4 scénarios de référence, comparée à une trace JSON
stockée sous `tests/fixtures/story_19_4_guard/`. Ce test doit être VERT sur le code
actuel (avant tout correctif de refactor de `apply_publication_decision()`) : c'est
la ligne de base contre laquelle chaque unité de refactor à venir devra se comparer,
tout écart devant être déclaré explicitement.

Scénarios (voir `_bmad-output/implementation-artifacts/19-4-note-conception.md` §8) :
  - S1 : 1 sync du corpus doré sur état vide.
  - S2 : 2 syncs successifs du même corpus — le 2e ne doit produire AUCUN unpublish.
  - S3 : S1 puis un clic "Publier" sur la portée globale.
  - S4 : fixture façon eq 579/585 (principal `ambiguous_skipped`, secondaires
    acceptés) — 2 syncs + 1 clic "Publier" ne doivent produire AUCUN unpublish, et
    les secondaires doivent être publiés à chaque passage.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from transport.http_server import create_app

SECRET = "test-secret-19-4-guard"
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "story_19_4_guard"
GOLDEN_CORPUS_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "golden_corpus" / "sync_payload.json"
)


def _load_golden_corpus() -> dict[str, Any]:
    with GOLDEN_CORPUS_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _sync_body(corpus: dict[str, Any], *, request_id: str) -> dict:
    return {
        "action": "sync",
        "payload": {
            "objects": corpus["objects"],
            "eq_logics": corpus["eq_logics"],
            "sync_config": corpus.get("sync_config", {"confidence_policy": "sure_probable"}),
        },
        "request_id": request_id,
        "timestamp": "2026-09-29T00:00:00Z",
    }


def _connected_bridge() -> MagicMock:
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    return bridge


def _connected_bridge_into(app) -> None:
    app["mqtt_bridge"] = _connected_bridge()


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


def _normalize_node_ids(node_ids: Any) -> Any:
    """`node_ids` peut être `None`, une liste d'int (cmd_id) ou de tuples
    `(entity_type, node_id)` pour les secondaires hétérogènes (registry.py)."""
    if node_ids is None:
        return None
    normalized = []
    for item in node_ids:
        if isinstance(item, (tuple, list)):
            normalized.append(list(item))
        else:
            normalized.append(item)
    return sorted(normalized, key=repr)


def _mapping_fingerprint(mapping: Any) -> dict[str, Any]:
    """Identité stable d'un `MappingResult` publié : pas d'horodatage, pas de
    référence d'objet — juste ce qui doit rester identique entre deux passages."""
    reason_details = dict(mapping.reason_details or {})
    reason_details.pop("state_topic", None)
    return {
        "jeedom_eq_id": mapping.jeedom_eq_id,
        "ha_entity_type": mapping.ha_entity_type,
        "ha_unique_id": mapping.ha_unique_id,
        "reason_code": mapping.reason_code,
        "confidence": mapping.confidence,
        "reason_details": reason_details,
    }


_KNOWN_TYPES = [
    "light", "cover", "switch", "sensor",
    "binary_sensor", "button", "climate", "alarm_control_panel",
]


class RecordingPublisher:
    """Faux `DiscoveryPublisher` : journalise chaque `publish_<type>` et
    `unpublish_by_eq_id`, sans toucher MQTT. Un seul objet remplace la classe
    `transport.http_server.DiscoveryPublisher` (patch `return_value=...`),
    exactement comme `test_story_19_1_sync_migration_parity.py`."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        for entity_type in _KNOWN_TYPES:
            setattr(self, f"publish_{entity_type}", self._make_publish(entity_type))

    def _make_publish(self, entity_type: str):
        async def _publish(mapping: Any, snapshot: Any) -> bool:
            self.calls.append({
                "op": "publish",
                "entity_type": entity_type,
                "mapping": _mapping_fingerprint(mapping),
            })
            return True

        return _publish

    async def unpublish_by_eq_id(self, eq_id: int, entity_type: str = "light",
                                  node_ids: Any = None) -> bool:
        self.calls.append({
            "op": "unpublish",
            "entity_type": entity_type,
            "eq_id": eq_id,
            "node_ids": _normalize_node_ids(node_ids),
        })
        return True


async def _post_sync(cli, body: dict) -> None:
    resp = await cli.post("/action/sync", json=body, headers={"X-Local-Secret": SECRET})
    assert resp.status == 200, await resp.text()


async def _post_publier_global(cli, app) -> None:
    topology = app["topology"]
    body = {
        "intention": "publier",
        "portee": "global",
        "selection": list(topology.eq_logics.keys()),
    }
    resp = await cli.post("/action/execute", json=body, headers={"X-Local-Secret": SECRET})
    assert resp.status == 200, await resp.text()


def _reference_path(name: str) -> Path:
    return FIXTURES_DIR / f"{name}.json"


def _assert_trace_matches_reference(name: str, trace: list[dict[str, Any]]) -> None:
    """Compare la trace obtenue à la trace de référence stockée. Si le fichier de
    référence n'existe pas encore, l'écrit (première génération de la baseline) —
    sinon, exige une égalité stricte et signale tout écart explicitement."""
    ref_path = _reference_path(name)
    if not ref_path.exists():
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return
    reference = json.loads(ref_path.read_text(encoding="utf-8"))
    assert trace == reference, (
        f"Trace publisher divergente pour {name} : le refactor a changé le "
        f"comportement observable publish/unpublish par rapport à la baseline 19-4."
    )


async def test_s1_un_sync_corpus_dore(cli, app):
    """S1 — 1 sync du corpus doré sur état vide : trace de référence."""
    recorder = RecordingPublisher()
    corpus = _load_golden_corpus()
    _connected_bridge_into(app)

    with patch("transport.http_server.DiscoveryPublisher", return_value=recorder):
        await _post_sync(cli, _sync_body(corpus, request_id="s1"))

    _assert_trace_matches_reference("s1_sync_corpus_dore", recorder.calls)


async def test_s2_deux_syncs_zero_unpublish(cli, app):
    """S2 — 2 syncs successifs du même corpus : le 2e ne doit produire aucun
    unpublish (pas de faux-positif de transition publié -> refusé)."""
    corpus = _load_golden_corpus()
    _connected_bridge_into(app)

    recorder1 = RecordingPublisher()
    with patch("transport.http_server.DiscoveryPublisher", return_value=recorder1):
        await _post_sync(cli, _sync_body(corpus, request_id="s2-a"))

    recorder2 = RecordingPublisher()
    with patch("transport.http_server.DiscoveryPublisher", return_value=recorder2):
        await _post_sync(cli, _sync_body(corpus, request_id="s2-b"))

    unpublishes = [c for c in recorder2.calls if c["op"] == "unpublish"]
    assert unpublishes == [], f"unpublish inattendu au 2e sync identique : {unpublishes}"
    _assert_trace_matches_reference("s2_second_sync_calls", recorder2.calls)


async def test_s3_sync_puis_publier_global(cli, app):
    """S3 — S1 puis un clic "Publier" sur la portée globale (mêmes équipements,
    déjà publiés) : ne doit pas introduire de comportement publisher inattendu."""
    corpus = _load_golden_corpus()
    _connected_bridge_into(app)

    with patch("transport.http_server.DiscoveryPublisher", return_value=RecordingPublisher()):
        await _post_sync(cli, _sync_body(corpus, request_id="s3-sync"))

    recorder = RecordingPublisher()
    with patch("transport.http_server.DiscoveryPublisher", return_value=recorder):
        await _post_publier_global(cli, app)

    _assert_trace_matches_reference("s3_publier_global_after_sync", recorder.calls)


_I11_EQ_ID = 628


def _i11_eq_payload() -> dict:
    """Payload JSON minimal pour eq 628 — seule l'éligibilité (assess_all) en
    dépend réellement ici : `evaluate_equipment` est patché pour ce test."""
    cmds = [
        {"id": 1, "name": "Filtration On", "generic_type": "SWITCH_ON", "type": "action", "sub_type": "other"},
        {"id": 2, "name": "Filtration Off", "generic_type": "SWITCH_OFF", "type": "action", "sub_type": "other"},
        {"id": 3, "name": "Filtration Etat", "generic_type": "SWITCH_STATE", "type": "info", "sub_type": "binary"},
    ]
    return {
        "id": _I11_EQ_ID, "name": "Pilotage priorisation solaire", "object_id": 1,
        "is_enable": True, "is_visible": True, "eq_type": "virtual",
        "is_excluded": False, "status": {"timeout": 0}, "cmds": cmds,
    }


def _load_sibling_module(filename: str):
    """Charge un module de test voisin par chemin de fichier, sans passer par
    l'import `tests.unit....` : `tests` est un nom de paquet ambigu ici (il existe
    à la fois à la racine du repo et sous `resources/daemon/`)."""
    path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _i11_evaluation():
    """Reconstruit à chaque appel la forme eq 579/585 (principal `ambiguous_skipped`,
    secondaires acceptés) via les mêmes fixtures/helpers que la story 19-2."""
    story_19_2 = _load_sibling_module("test_story_19_2_decouplage_state_command_i11.py")
    primary, primary_decision = story_19_2._build_multi_switch(principal_should_publish=False)
    from models.evaluate_equipment import EquipmentEvaluation

    secondary_decisions = [s.publication_decision_ref for s in primary.additional_mappings]
    return EquipmentEvaluation(
        equipment_decision=primary_decision,
        secondary_decisions=secondary_decisions,
        command_decisions=[],
        mapping=primary,
    )


def _i11_corpus() -> dict[str, Any]:
    return {"objects": [{"id": 1, "name": "Salon"}], "eq_logics": [_i11_eq_payload()]}


async def test_s4_candidat_i11_deux_syncs_et_publier(cli, app):
    """S4 — fixture façon eq 579/585 (19-2) : principal `ambiguous_skipped`,
    secondaires acceptés. D1 : aucun changement attendu — 2 syncs + 1 clic
    "Publier" ne doivent produire aucun unpublish, et les secondaires doivent
    être republiés à chaque sync (la garde per-candidat ne concerne que les
    futures transitions publié -> refusé, pas ce cas déjà `ambiguous_skipped`)."""
    _connected_bridge_into(app)

    def _evaluate_side_effect(*_args, **_kwargs):
        return _i11_evaluation()

    recorder1 = RecordingPublisher()
    with patch("transport.http_server.DiscoveryPublisher", return_value=recorder1), patch(
        "transport.http_server.evaluate_equipment", side_effect=_evaluate_side_effect
    ):
        await _post_sync(cli, _sync_body(_i11_corpus(), request_id="s4-sync-1"))

    recorder2 = RecordingPublisher()
    with patch("transport.http_server.DiscoveryPublisher", return_value=recorder2), patch(
        "transport.http_server.evaluate_equipment", side_effect=_evaluate_side_effect
    ):
        await _post_sync(cli, _sync_body(_i11_corpus(), request_id="s4-sync-2"))

    unpublishes_2 = [c for c in recorder2.calls if c["op"] == "unpublish"]
    assert unpublishes_2 == [], f"unpublish inattendu au 2e sync du candidat I11 : {unpublishes_2}"
    secondary_publishes_2 = [c for c in recorder2.calls if c["op"] == "publish"]
    assert secondary_publishes_2, "les secondaires acceptés doivent être republiés à chaque sync"

    recorder3 = RecordingPublisher()
    with patch("transport.http_server.DiscoveryPublisher", return_value=recorder3):
        await _post_publier_global(cli, app)

    unpublishes_3 = [c for c in recorder3.calls if c["op"] == "unpublish"]
    assert unpublishes_3 == [], f"unpublish inattendu au clic Publier du candidat I11 : {unpublishes_3}"

    _assert_trace_matches_reference("s4_candidat_i11_sync1", recorder1.calls)
    _assert_trace_matches_reference("s4_candidat_i11_sync2", recorder2.calls)
    _assert_trace_matches_reference("s4_candidat_i11_publier", recorder3.calls)
