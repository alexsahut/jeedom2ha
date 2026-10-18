"""Story 25.2 (AC15, Q10) — budget de la route agrégée sur un parc synthétique de 292 équipements.

Mesure synthétique uniquement (CC-48 : aucune mesure sur la box réelle ; AC16 est exécuté par
ClaudeBox). Vrai `MapperRegistry`, vrai `evaluate_equipment` (aucun MagicMock). Méthode de 19-6 :
chaque durée retient le MAXIMUM des mesures, multiplié par `MARGE_MESURE` (1,5) et
`MACHINE_FACTOR` (3 : box de terrain présumée <= 3x plus lente que la VM de mesure).

Budgets (décision Q10) : construction à froid <= 4 000 ms (projetée), appel à chaud <= 50 ms
(projeté), charge utile <= 1 500 000 octets. Le rapport de gain sur la boucle actuelle
(292 x `_build_mapping_override_tree` sans les optimisations de l'AC9) est consigné.

Marqueur `load` : exclu de la suite par défaut (voir pyproject.toml), lancer avec -m load.
"""

from __future__ import annotations

import time

import pytest

import transport.http_server as http_server
from mapping.overrides import save_equipment_override, save_override
from models.evaluate_equipment import evaluate_equipment
from models.topology import (
    JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot, assess_eligibility,
)
from mapping.registry import MapperRegistry
from .story_25_2_corpus import light, multi_sensor, untyped

pytestmark = pytest.mark.load

SECRET = "test-secret-25.2-load"
H = {"X-Local-Secret": SECRET}
MACHINE_FACTOR = 3.0
MARGE_MESURE = 1.5
MEASURE_ITERATIONS = 5
N_EQUIPMENTS = 292
BUDGET_COLD_MS = 4000
BUDGET_HIT_MS = 50
BUDGET_BYTES = 1_500_000


def _many_commands(eq_id, object_id):
    """Forme la plus coûteuse déclarée : beaucoup de commandes (24) autour d'un dimmer."""
    eq = multi_sensor(eq_id, object_id)
    base = eq_id * 10
    for i in range(7, 31):
        eq.cmds.append(JeedomCmd(id=base + i, name=f"Mesure {i}", type="info", sub_type="numeric",
                                 generic_type="POWER" if i % 2 else None, unit="W", current_value=i))
    return eq


def _parc(n):
    shapes = [
        lambda i, o: light(i, o),
        lambda i, o: multi_sensor(i, o),
        lambda i, o: _many_commands(i, o),
        lambda i, o: untyped(i, o),
        lambda i, o: JeedomEqLogic(id=i, name=f"Eq-{i}", object_id=o, cmds=[]),
        lambda i, o: light(i, o, is_enable=False),
    ]
    eqs = [shapes[k % len(shapes)](1000 + k, 1 + (k % 20)) for k in range(n)]
    return TopologySnapshot(
        timestamp="2026-10-18T12:00:00Z",
        objects={o: JeedomObject(id=o, name=f"Piece-{o}") for o in range(1, 21)},
        eq_logics={eq.id: eq for eq in eqs},
    )


def _app(tmp_path):
    app = http_server.create_app(local_secret=SECRET)
    topology = _parc(N_EQUIPMENTS)
    registry = MapperRegistry()
    eligibility = {i: assess_eligibility(eq) for i, eq in topology.eq_logics.items()}
    publications = {}
    for k, (eq_id, eq) in enumerate(topology.eq_logics.items()):
        evaluation = evaluate_equipment(
            eq, topology, eligibility[eq_id], mapper_registry=registry, confidence_policy="strict",
            persisted_overrides={}, persisted_equipment_overrides={},
        )
        decision = evaluation.equipment_decision
        decision.mapping_result = evaluation.mapping
        decision.discovery_published = decision.active_or_alive = (k % 3 == 0)
        publications[eq_id] = decision
    app["topology"], app["eligibility"], app["publications"] = topology, eligibility, publications
    app["data_dir"] = str(tmp_path)
    for k, eq_id in enumerate(list(topology.eq_logics)[:20]):  # quelques overrides posés
        save_equipment_override(eq_id, {"publication_override": "exclude"}, str(tmp_path))
        save_override(eq_id, eq_id * 10 + 1, {"ha_entity_type": "binary_sensor"}, str(tmp_path))
    return app


def _current_loop_ms(app):
    """Boucle actuelle : un `_build_mapping_override_tree` par équipement, sans optimisation."""
    snapshot, data_dir = app["topology"], app["data_dir"]
    start = time.perf_counter()
    for eq_id, eq in snapshot.eq_logics.items():
        http_server._build_mapping_override_tree(
            eq, snapshot, data_dir, synced_decision=app["publications"].get(eq_id))
    return (time.perf_counter() - start) * 1000


async def test_ac15_budgets_route_agregee(aiohttp_client, tmp_path):
    app = _app(tmp_path)
    cli = await aiohttp_client(app)

    colds, hits, sizes = [], [], []
    for _ in range(MEASURE_ITERATIONS):
        start = time.perf_counter()
        resp = await cli.get("/system/equipment_states?refresh=1", headers=H)
        body = await resp.read()
        colds.append((time.perf_counter() - start) * 1000)
        sizes.append(len(body))
        payload = (await resp.json())["payload"]
        assert payload["meta"]["cache"]["hit"] is False
        assert payload["meta"]["equipments_read"] == N_EQUIPMENTS and payload["unread"] == []
    for _ in range(MEASURE_ITERATIONS * 4):
        start = time.perf_counter()
        resp = await cli.get("/system/equipment_states", headers=H)
        await resp.read()
        hits.append((time.perf_counter() - start) * 1000)
        assert (await resp.json())["payload"]["meta"]["cache"]["hit"] is True
    loops = [_current_loop_ms(app) for _ in range(MEASURE_ITERATIONS)]

    cold_ms = max(colds) * MARGE_MESURE * MACHINE_FACTOR
    hit_ms = max(hits) * MARGE_MESURE * MACHINE_FACTOR
    loop_ms = max(loops) * MARGE_MESURE * MACHINE_FACTOR
    nbytes = max(sizes)
    c_eq = max(colds) / N_EQUIPMENTS * MARGE_MESURE * MACHINE_FACTOR
    print(
        f"\n[25.2 AC15] equipements={N_EQUIPMENTS} c_eq={c_eq:.2f}ms "
        f"build_cold_ms(max brut)={max(colds):.1f} projete={cold_ms:.1f} "
        f"hit_ms(max brut)={max(hits):.1f} projete={hit_ms:.1f} bytes={nbytes} "
        f"boucle_actuelle(max brut)={max(loops):.1f} projetee={loop_ms:.1f} "
        f"gain_cold={max(loops) / max(colds):.2f}x"
    )
    assert cold_ms <= BUDGET_COLD_MS, f"construction à froid projetée {cold_ms:.0f} ms > {BUDGET_COLD_MS}"
    assert hit_ms <= BUDGET_HIT_MS, f"appel à chaud projeté {hit_ms:.0f} ms > {BUDGET_HIT_MS}"
    assert nbytes <= BUDGET_BYTES, f"charge utile {nbytes} octets > {BUDGET_BYTES}"
