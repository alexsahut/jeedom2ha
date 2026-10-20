"""Story 25.2 (AC15, Q10) — budget de la route agrégée sur un parc synthétique de 292 équipements.

Mesure synthétique uniquement (CC-48 : aucune mesure sur la box réelle ; AC16 est exécuté par
ClaudeBox). Vrai `MapperRegistry`, vrai `evaluate_equipment` (aucun MagicMock). Projection de 19-6 :
la durée retenue est multipliée par `MARGE_MESURE` (1,5) et `MACHINE_FACTOR` (3 : box de terrain
présumée <= 3x plus lente que la VM de mesure).

Méthode de mesure (robuste aux pics du runner, sans relever les budgets) :
- un échauffement (une construction à froid, un appel à chaud) non compté ;
- chaque mesure est précédée de `gc.collect()` puis `gc.freeze()` (`_Chrono`) et prise GC ACTIF :
  le tas laissé par les tests précédents est gelé (une passe complète du GC sur ce tas coûtait jusqu'à
  ~1 s sur une seule construction, 4,4x la valeur normale), mais les allocations de la route restent
  collectées comme en production ;
- la durée retenue pour le budget est le maximum HORS PIC ISOLÉ (`_max_hors_pic` : la plus haute
  mesure écartée, la deuxième plus haute retenue) sur `COLD_ITERATIONS` constructions — un
  quantile élevé, donc toujours conservateur, mais qu'un seul pic (voisin bruyant) ne fait pas
  basculer ;
- le pire cas brut reste borné par un garde-fou explicite, plus large : `max × MARGE_MESURE ×
  MACHINE_FACTOR <= PLAFOND_PIRE_CAS_FACTEUR × budget`.

Budgets (décision Q10) : construction à froid <= 4 000 ms (projetée), appel à chaud <= 50 ms
(projeté), charge utile <= 1 500 000 octets. Le rapport de gain sur la boucle actuelle
(292 x `_build_mapping_override_tree` sans les optimisations de l'AC9) est consigné.

Marqueur `load` : exclu de la suite par défaut (voir pyproject.toml), lancer avec -m load.
"""

from __future__ import annotations

import gc
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
MEASURE_ITERATIONS = 5  # boucle actuelle (consignée seulement : ~10 s par passe)
COLD_ITERATIONS = 9
HIT_ITERATIONS = 36
# Garde-fou du pire cas : même projection appliquée au maximum brut, plafond = 2 x budget. Il attrape
# une dérive qui ne se manifesterait que par intermittence, sans échouer sur un pic isolé du runner.
PLAFOND_PIRE_CAS_FACTEUR = 2.0
N_EQUIPMENTS = 292
BUDGET_COLD_MS = 4000
BUDGET_HIT_MS = 50
BUDGET_BYTES = 1_500_000
# Story 25.8 (Q1 B) : seuil de vigilance de la charge utile (la box a mesuré 1 342 346 octets en 25.4) ; le dépasser est
# consigné par la preuve terrain (le champ `present_in_ha` est conservé), le budget ci-dessus reste le seuil bloquant.
VIGILANCE_BYTES = 1_350_000


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


def _max_hors_pic(values):
    """Maximum hors pic isolé : la plus haute mesure est écartée, la suivante est retenue."""
    return sorted(values)[-2]


def _mediane(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


class _Chrono:
    """Mesure GC ACTIF (comportement de production), tas hérité des tests précédents gelé.

    `gc.collect()` puis `gc.freeze()` déplacent les objets déjà vivants (tas laissé par les tests 19-6)
    vers la génération permanente : le GC ne les parcourt plus, mais il collecte normalement tout ce
    que la route alloue pendant la mesure. Une régression qui augmente les allocations ou le coût du GC
    reste donc visible (relevé Codex sur la PR). `gc.unfreeze()` rétablit l'état à la sortie.
    """

    def __enter__(self):
        gc.collect()
        gc.freeze()
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.ms = (time.perf_counter() - self._start) * 1000
        gc.unfreeze()
        return False


def _current_loop_ms(app):
    """Boucle actuelle : un `_build_mapping_override_tree` par équipement, sans optimisation."""
    snapshot, data_dir = app["topology"], app["data_dir"]
    with _Chrono() as chrono:
        for eq_id, eq in snapshot.eq_logics.items():
            http_server._build_mapping_override_tree(
                eq, snapshot, data_dir, synced_decision=app["publications"].get(eq_id))
    return chrono.ms


def _projete(ms):
    return ms * MARGE_MESURE * MACHINE_FACTOR


async def test_ac15_budgets_route_agregee(aiohttp_client, tmp_path):
    app = _app(tmp_path)
    cli = await aiohttp_client(app)

    # Échauffement non compté : première connexion, premiers chemins de code, premier cache.
    await (await cli.get("/system/equipment_states?refresh=1", headers=H)).read()
    await (await cli.get("/system/equipment_states", headers=H)).read()

    colds, hits, sizes = [], [], []
    for _ in range(COLD_ITERATIONS):
        with _Chrono() as chrono:
            resp = await cli.get("/system/equipment_states?refresh=1", headers=H)
            body = await resp.read()
        colds.append(chrono.ms)
        sizes.append(len(body))
        payload = (await resp.json())["payload"]
        assert payload["meta"]["cache"]["hit"] is False
        assert payload["meta"]["equipments_read"] == N_EQUIPMENTS and payload["unread"] == []
    for _ in range(HIT_ITERATIONS):
        with _Chrono() as chrono:
            resp = await cli.get("/system/equipment_states", headers=H)
            await resp.read()
        hits.append(chrono.ms)
        assert (await resp.json())["payload"]["meta"]["cache"]["hit"] is True
    loops = [_current_loop_ms(app) for _ in range(MEASURE_ITERATIONS)]

    cold_ms = _projete(_max_hors_pic(colds))
    hit_ms = _projete(_max_hors_pic(hits))
    cold_pire_ms = _projete(max(colds))
    hit_pire_ms = _projete(max(hits))
    loop_ms = _projete(_max_hors_pic(loops))
    nbytes = max(sizes)
    c_eq = cold_ms / N_EQUIPMENTS
    print(
        f"\n[25.2 AC15] equipements={N_EQUIPMENTS} c_eq={c_eq:.2f}ms "
        f"build_cold_ms(mediane brute)={_mediane(colds):.1f} (retenue brute)={_max_hors_pic(colds):.1f} "
        f"projete={cold_ms:.1f} (max brut)={max(colds):.1f} pire_cas_projete={cold_pire_ms:.1f} "
        f"hit_ms(retenue brute)={_max_hors_pic(hits):.1f} projete={hit_ms:.1f} "
        f"(max brut)={max(hits):.1f} pire_cas_projete={hit_pire_ms:.1f} bytes={nbytes} "
        f"boucle_actuelle(retenue brute)={_max_hors_pic(loops):.1f} projetee={loop_ms:.1f} "
        f"gain_cold={_max_hors_pic(loops) / _max_hors_pic(colds):.2f}x"
    )
    assert cold_ms <= BUDGET_COLD_MS, f"construction à froid projetée {cold_ms:.0f} ms > {BUDGET_COLD_MS}"
    assert hit_ms <= BUDGET_HIT_MS, f"appel à chaud projeté {hit_ms:.0f} ms > {BUDGET_HIT_MS}"
    plafond_cold = PLAFOND_PIRE_CAS_FACTEUR * BUDGET_COLD_MS
    plafond_hit = PLAFOND_PIRE_CAS_FACTEUR * BUDGET_HIT_MS
    assert cold_pire_ms <= plafond_cold, (
        f"pire cas de construction à froid projeté {cold_pire_ms:.0f} ms > plafond {plafond_cold:.0f}")
    assert hit_pire_ms <= plafond_hit, f"pire cas à chaud projeté {hit_pire_ms:.0f} ms > plafond {plafond_hit:.0f}"
    assert nbytes <= BUDGET_BYTES, f"charge utile {nbytes} octets > {BUDGET_BYTES}"
    if nbytes > VIGILANCE_BYTES:
        print(f"[25.8 Q1] ATTENTION charge utile {nbytes} octets > seuil de vigilance {VIGILANCE_BYTES}")
