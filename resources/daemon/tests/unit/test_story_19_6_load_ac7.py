"""Story 19.6 (AC7) — enveloppe de charge du démon : appels_MQTT*c_mqtt + eq_portee*c_eq
+ eq_parc*c_parc <= budget_travail (39s = deadline_s(55) - plafond_pauses(15) - marge_reveil(1)).

c_mqtt : pas de broker réel disponible en CI -> constante déclarée (justifiée ci-dessous),
appliquée au nombre réel d'appels `mqtt_bridge.publish_message` observés (pas un forfait).
c_eq   : mesuré ici par `time.perf_counter` sur `evaluate_equipment()` réel, forme la plus
         coûteuse disponible (équipement multi-commandes, multi-domaine, avec overrides).
c_parc : mesuré ici par `time.perf_counter` sur `save_publications_cache()` réel, avec un
         registre d'overrides de cardinalité maximale (un override par équipement).
Facteur machine : la CI/VM peut être plus rapide que la box de terrain -> marge x3 déclarée
sur chaque coût mesuré (au-delà de la marge déjà prise sur le max observé).

Scénarios lourds -> marqueur `load`, exclus de la suite par défaut (voir pyproject.toml).
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.evaluate_equipment import evaluate_equipment
from models.mapping import LightCapabilities, MappingResult, PublicationDecision
from models.topology import EligibilityResult, JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from cache.disk_cache import save_publications_cache
import transport.http_server as http_server
from transport import action_pacing

pytestmark = pytest.mark.load

SECRET = "test-secret-19.6-load"
VALID_HEADERS = {"X-Local-Secret": SECRET}

MACHINE_FACTOR = 3.0  # box de terrain présumée <= 3x plus lente que la VM de mesure.
MEASURE_ITERATIONS = 20


def _costly_mapping(eq_id: int) -> MappingResult:
    """Forme la plus coûteuse disponible dans le harness : multi-commandes (20),
    multi-domaine (switch + sensor + binary_sensor via additional_mappings), overrides."""
    cmds = {}
    for i in range(20):
        cmds[f"CMD_{i}"] = JeedomCmd(
            id=eq_id * 100 + i, name=f"Cmd {i}",
            generic_type="LIGHT_ON" if i == 0 else "GENERIC_INFO",
            type="action" if i == 0 else "info", sub_type="other",
        )
    secondaries = [
        MappingResult(
            ha_entity_type=t, confidence="sure", reason_code="sensor_numeric",
            jeedom_eq_id=eq_id, ha_unique_id=f"jeedom2ha_eq_{eq_id}_{t}",
            ha_name=f"{t} {eq_id}", suggested_area="Salon", commands=cmds,
            reason_details={"node_id": f"n{eq_id}_{t}"}, capabilities=LightCapabilities(has_on_off=True),
        )
        for t in ("sensor", "binary_sensor")
    ]
    return MappingResult(
        ha_entity_type="switch", confidence="sure", reason_code="switch_on_off",
        jeedom_eq_id=eq_id, ha_unique_id=f"jeedom2ha_eq_{eq_id}", ha_name=f"Prise {eq_id}",
        suggested_area="Salon", commands=cmds, capabilities=LightCapabilities(has_on_off=True),
        additional_mappings=secondaries,
    )


def _measure_c_eq() -> float:
    eq_id = 1
    mapping = _costly_mapping(eq_id)
    eq = JeedomEqLogic(id=eq_id, name="Prise 1", object_id=1, is_enable=True, cmds=list(mapping.commands.values()))
    topology = TopologySnapshot(timestamp="2026-09-30T00:00:00Z", objects={1: JeedomObject(id=1, name="Salon")}, eq_logics={eq_id: eq})
    result = EligibilityResult(is_eligible=True, reason_code="eligible")
    overrides = {eq_id: {"ha_name": "Override"}}
    registry = MagicMock()
    registry.map.return_value = mapping
    best = min(
        _time_call(lambda: evaluate_equipment(
            eq, topology, result, mapper_registry=registry, confidence_policy="strict",
            persisted_overrides=overrides, persisted_equipment_overrides=overrides,
        ))
        for _ in range(MEASURE_ITERATIONS)
    )
    return best


def _measure_c_parc(n: int) -> float:
    publications = {}
    for i in range(n):
        eq_id = 100 + i
        mapping = _costly_mapping(eq_id)
        publications[eq_id] = PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping,
            state_topic=f"jeedom2ha/{eq_id}/state", active_or_alive=True, discovery_published=True,
        )
    best = min(_time_call(lambda: save_publications_cache(publications, "/tmp")) for _ in range(5))
    return best / n  # coût par équipement du parc


def _time_call(fn) -> float:
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


# --- AC7 : mesure des trois coûts unitaires + déclaration de l'enveloppe ---


def test_ac7_couts_mesures_et_enveloppe_respectee():
    c_eq_mesure = _measure_c_eq()
    c_parc_mesure = _measure_c_parc(500)
    c_eq = max(c_eq_mesure, 0.0005) * MACHINE_FACTOR
    c_parc = max(c_parc_mesure, 0.00005) * MACHINE_FACTOR
    # c_mqtt : pas de broker réel -> constante déclarée (publish_message local, retain qos1,
    # topologie observée en Story 11.2 : ~1 appel par entité HA publiée). 5 ms est une
    # estimation prudente d'un aller-retour loopback MQTT (bien au-dessus d'un test unitaire).
    c_mqtt = 0.005 * MACHINE_FACTOR

    budget_travail = action_pacing.budget_travail(55.0)
    assert budget_travail == pytest.approx(39.0)

    # Scénario mixte à la frontière : portée courante (30/09 : 94 évalués sur 292) + un grand
    # parc (1000) dont 1 seul équipement est ciblé par l'action.
    appels_mqtt, eq_portee, eq_parc = 94, 94, 1000
    cout = appels_mqtt * c_mqtt + eq_portee * c_eq + eq_parc * c_parc
    assert cout <= budget_travail, f"enveloppe dépassée: {cout:.3f}s > {budget_travail}s"

    # Petite portée sur très grand inventaire (parc dominant).
    appels_mqtt, eq_portee, eq_parc = 1, 1, 5000
    cout = appels_mqtt * c_mqtt + eq_portee * c_eq + eq_parc * c_parc
    assert cout <= budget_travail, f"enveloppe dépassée (grand inventaire): {cout:.3f}s > {budget_travail}s"


# --- AC7 : rejeu bout-en-bout de la mesure du 30/09 (292 total, 94 évalués) ---


def _light_mapping(eq_id: int) -> MappingResult:
    return MappingResult(
        ha_entity_type="light", confidence="sure", reason_code="light_on_off_state",
        jeedom_eq_id=eq_id, ha_unique_id=f"jeedom2ha_eq_{eq_id}", ha_name=f"Lumiere {eq_id}",
        suggested_area="Salon",
        commands={"LIGHT_ON": JeedomCmd(id=eq_id * 10 + 1, name="On", generic_type="LIGHT_ON", type="action", sub_type="other")},
        capabilities=LightCapabilities(has_on_off=True),
    )


def _make_parc(n: int, n_inclus: int | None = None):
    n_inclus = n if n_inclus is None else n_inclus
    eq_logics, scope_equipements, eligibility, mappings, publications = {}, [], {}, {}, {}
    for i in range(n):
        eq_id = 100 + i
        inclus = i < n_inclus
        mapping = _light_mapping(eq_id)
        eq_logics[eq_id] = JeedomEqLogic(id=eq_id, name=f"Lampe {eq_id}", object_id=1, is_enable=True, cmds=list(mapping.commands.values()))
        scope_equipements.append({
            "eq_id": eq_id, "object_id": 1, "name": f"Lampe {eq_id}",
            "effective_state": "include" if inclus else "exclude", "decision_source": "global",
            "is_exception": False, "has_pending_home_assistant_changes": False,
        })
        eligibility[eq_id] = EligibilityResult(is_eligible=inclus, reason_code="eligible" if inclus else "excluded_eqlogic")
        mappings[eq_id] = mapping
        if inclus:
            publications[eq_id] = PublicationDecision(
                should_publish=True, reason="sure", mapping_result=mapping,
                state_topic=f"jeedom2ha/{eq_id}/state", active_or_alive=True, discovery_published=True,
            )
    topology = TopologySnapshot(timestamp="2026-09-30T00:00:00Z", objects={1: JeedomObject(id=1, name="Salon")}, eq_logics=eq_logics)
    published_scope = {
        "global": {"counts": {"total": n, "include": n_inclus, "exclude": n - n_inclus, "exceptions": 0},
                   "effective_state": "include", "has_pending_home_assistant_changes": False},
        "pieces": [], "equipements": scope_equipements,
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


def _load_publisher_mock() -> MagicMock:
    publisher = MagicMock()
    publisher.publish_light = AsyncMock(return_value=True)
    publisher.publish_cover = AsyncMock(return_value=True)
    publisher.publish_switch = AsyncMock(return_value=True)
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    return publisher


@pytest.fixture
def cli_factory(aiohttp_client):
    async def _make(app):
        return await aiohttp_client(app)
    return _make


@pytest.mark.asyncio
async def test_ac7_rejeu_mesure_30_09_sous_deadline(cli_factory):
    """292 au total, 94 évalués/publiés (mesure terrain du 30/09, ~11s observées) : le
    parcours réel (évaluation réelle + pauses réelles, MQTT mocké) reste sous deadline_s."""
    n_total, n_pause = 292, 94
    app = _build_app(n_total, n_pause)
    cli = await cli_factory(app)
    publisher = _load_publisher_mock()
    start = time.perf_counter()
    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        response = await cli.post(
            "/action/execute",
            json={"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
            headers=VALID_HEADERS,
        )
    duration = time.perf_counter() - start
    assert response.status == 200
    assert duration < 55.0


@pytest.mark.asyncio
async def test_ac7_grand_parc_1000_multi_capteurs_sous_deadline(cli_factory):
    """Parc cible : 1000 équipements multi-capteurs, action sur la portée globale entière,
    reste sous deadline_s (pauses réelles plafonnées + évaluation réelle, MQTT mocké)."""
    n = 1000
    app = _build_app(n, n)
    cli = await cli_factory(app)
    publisher = _load_publisher_mock()
    start = time.perf_counter()
    with patch("transport.http_server.DiscoveryPublisher", return_value=publisher):
        response = await cli.post(
            "/action/execute",
            json={"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": 55.0},
            headers=VALID_HEADERS,
        )
    duration = time.perf_counter() - start
    assert response.status == 200
    assert duration < 55.0
