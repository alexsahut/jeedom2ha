"""Story 19.6 (AC7) — enveloppe de charge du démon : appels_MQTT*c_mqtt + eq_portee*c_eq
+ eq_parc*c_parc <= budget_travail (39s = deadline_s(55) - plafond_pauses(15) - marge_reveil(1)).

Revue Codex/ClaudeBox (PR #189) : les trois coûts sont mesurés dans le chemin réel, pas
simulés :
- c_eq   : `evaluate_equipment()` réel avec le vrai `MapperRegistry` (pas de MagicMock), sur
  un équipement multi-capteurs (dimmer + metering) qui produit réellement 3 candidats
  (light principal + 2 sensors secondaires, cf. Story 11.4).
- c_mqtt : `DiscoveryPublisher` réel (pas d'AsyncMock), avec un faux pont MQTT dont
  `publish_message` est synchrone (comme paho), compte les appels et bloque
  `LATENCE_MQTT_S` avant de retourner. paho ne fait que mettre le message en file
  d'attente (`publish()` retourne avant l'envoi réseau) ; 5 ms est donc une borne
  prudente pour un aller-retour loopback local, largement au-dessus du coût réel de mise
  en file.
- c_parc : `save_publications_cache()` réel, écrit dans `tmp_path` (jamais `/tmp`).

Chaque coût unitaire retient le MAXIMUM des mesures (pas le minimum), avec une marge
explicite `MARGE_MESURE` (x1.5) et le facteur machine `MACHINE_FACTOR` (x3, la box de
terrain est présumée <= 3x plus lente que la VM de mesure).

Scénarios lourds -> marqueur `load`, exclus de la suite par défaut (voir pyproject.toml).
"""

from __future__ import annotations

import time
from typing import Optional

import pytest

from models.evaluate_equipment import evaluate_equipment
from models.mapping import PublicationDecision
from models.topology import EligibilityResult, JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from mapping.registry import MapperRegistry
from cache.disk_cache import save_publications_cache
from discovery.publisher import DiscoveryPublisher
from sync.state import StateSynchronizer
import transport.http_server as http_server
from transport import action_pacing

pytestmark = pytest.mark.load

SECRET = "test-secret-19.6-load"
VALID_HEADERS = {"X-Local-Secret": SECRET}

MACHINE_FACTOR = 3.0  # box de terrain présumée <= 3x plus lente que la VM de mesure.
MARGE_MESURE = 1.5  # marge explicite au-dessus du maximum observé (bruit de mesure).
LATENCE_MQTT_S = 0.005  # borne prudente d'un aller-retour loopback (paho ne fait que publier en file).
MEASURE_ITERATIONS = 20


def _cmd(cmd_id, name, cmd_type, sub_type, generic_type=None, unit=None, value=None):
    return JeedomCmd(
        id=cmd_id, name=name, type=cmd_type, sub_type=sub_type,
        generic_type=generic_type, unit=unit, current_value=value,
    )


def _multi_capteur_eq(eq_id: int) -> JeedomEqLogic:
    """Équipement multi-capteurs réel (Story 11.4) : dimmer actionnable + 2 mesures de
    consommation -> le vrai `MapperRegistry` produit 3 candidats (light + 2 sensors)."""
    base = eq_id * 100
    return JeedomEqLogic(
        id=eq_id, name=f"Dimmer {eq_id}", object_id=1, eq_type_name="zwave",
        cmds=[
            _cmd(base + 1, "On", "action", "other", "LIGHT_ON"),
            _cmd(base + 2, "Off", "action", "other", "LIGHT_OFF"),
            _cmd(base + 3, "Etat", "info", "binary", "LIGHT_STATE", value="1"),
            _cmd(base + 4, "Variateur", "action", "slider", "LIGHT_SLIDER"),
            _cmd(base + 5, "Puissance", "info", "numeric", "POWER", "W", 42),
            _cmd(base + 6, "Consommation", "info", "numeric", "CONSUMPTION", "kWh", 3.5),
        ],
    )


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-09-30T00:00:00Z", objects={1: JeedomObject(id=1, name="Salon")}, eq_logics={eq.id: eq},
    )


def _time_call(fn) -> float:
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


def _measure_c_eq() -> float:
    """MAX (pas min) sur `MEASURE_ITERATIONS` appels réels d'`evaluate_equipment()`, vrai
    `MapperRegistry`, sur l'équipement multi-capteurs (forme la plus coûteuse : 3 candidats,
    overrides)."""
    eq = _multi_capteur_eq(1)
    topology = _snapshot(eq)
    result = EligibilityResult(is_eligible=True, reason_code="eligible")
    overrides = {1: {"ha_name": "Override"}}
    registry = MapperRegistry()
    return max(
        _time_call(lambda: evaluate_equipment(
            eq, topology, result, mapper_registry=registry, confidence_policy="strict",
            persisted_overrides=overrides, persisted_equipment_overrides=overrides,
        ))
        for _ in range(MEASURE_ITERATIONS)
    )


def _measure_c_parc(n: int, data_dir: str) -> float:
    """MAX (pas min) sur 5 écritures réelles de `save_publications_cache()`, dans
    `data_dir` (jamais `/tmp`), avec un registre de cardinalité `n`."""
    publications = {}
    for i in range(n):
        eq_id = 100 + i
        eq = _multi_capteur_eq(eq_id)
        mapping = evaluate_equipment(
            eq, _snapshot(eq), EligibilityResult(is_eligible=True, reason_code="eligible"),
            mapper_registry=MapperRegistry(), confidence_policy="strict",
            persisted_overrides={}, persisted_equipment_overrides={},
        ).mapping
        publications[eq_id] = PublicationDecision(
            should_publish=True, reason="sure", mapping_result=mapping,
            state_topic=f"jeedom2ha/{eq_id}/state", active_or_alive=True, discovery_published=True,
        )
    best = max(_time_call(lambda: save_publications_cache(publications, data_dir)) for _ in range(5))
    return best / n  # coût par équipement du parc


class _FakeMqttBridge:
    """Faux pont MQTT synchrone (comme paho) : compte les appels et bloque
    `LATENCE_MQTT_S`, pour mesurer le coût MQTT de bout en bout via le vrai
    `DiscoveryPublisher` (pas d'`AsyncMock` qui court-circuiterait le chemin réel)."""

    def __init__(self) -> None:
        self.is_connected = True
        self.call_count = 0

    def publish_message(self, topic, payload, qos=1, retain=True):
        self.call_count += 1
        time.sleep(LATENCE_MQTT_S)
        return True


# --- AC7 : mesure des trois coûts unitaires + déclaration de l'enveloppe ---


def test_ac7_couts_mesures_et_enveloppe_respectee(tmp_path):
    c_eq_mesure = _measure_c_eq()
    c_parc_mesure = _measure_c_parc(500, str(tmp_path))
    c_eq = c_eq_mesure * MARGE_MESURE * MACHINE_FACTOR
    c_parc = c_parc_mesure * MARGE_MESURE * MACHINE_FACTOR
    c_mqtt = LATENCE_MQTT_S * MARGE_MESURE * MACHINE_FACTOR

    budget_travail = action_pacing.budget_travail(55.0)
    assert budget_travail == pytest.approx(39.0)

    print(f"\n[AC7] c_eq_mesure={c_eq_mesure:.6f}s c_parc_mesure={c_parc_mesure:.6f}s "
          f"c_eq={c_eq:.6f}s c_parc={c_parc:.6f}s c_mqtt={c_mqtt:.6f}s")

    # Revue Codex P1 (PR #189, 2e tour) : le vrai « Publier » exécute aussi
    # `publish_click_states()` (état au clic) pour chaque candidat streamé (les 2 sensors
    # secondaires du dimmer multi-capteurs ; le light principal n'est pas streamé, cf.
    # `StateSynchronizer.streams_actionable_type`). Appels MQTT par équipement mesurés
    # (test_ac7_parc_typique_90_pct_enveloppe_sous_deadline, faux pont MQTT réel) = 3
    # discovery + 2 état = 5 (la disponibilité locale n'ajoute aucun appel ici : fixture
    # sans `local_availability_supported`).
    APPELS_MQTT_PAR_EQUIPEMENT = 5

    # Scénario mixte à la frontière : portée courante (30/09 : 94 évalués sur 292, 3 entités
    # HA par équipement multi-capteurs) + un grand parc (1000) dont 1 seul équipement cible.
    appels_mqtt, eq_portee, eq_parc = 94 * APPELS_MQTT_PAR_EQUIPEMENT, 94, 1000
    cout = appels_mqtt * c_mqtt + eq_portee * c_eq + eq_parc * c_parc
    assert cout <= budget_travail, f"enveloppe dépassée (mixte): {cout:.3f}s > {budget_travail}s"

    # Petite portée sur très grand inventaire (parc dominant).
    appels_mqtt, eq_portee, eq_parc = APPELS_MQTT_PAR_EQUIPEMENT, 1, 5000
    cout = appels_mqtt * c_mqtt + eq_portee * c_eq + eq_parc * c_parc
    assert cout <= budget_travail, f"enveloppe dépassée (grand inventaire): {cout:.3f}s > {budget_travail}s"

    # N_max : parc typique (équipement multi-capteurs, 3 entités HA/équipement) à 90% de
    # l'enveloppe -> calculé à partir des coûts mesurés ci-dessus.
    n_max = int((0.90 * budget_travail) / (APPELS_MQTT_PAR_EQUIPEMENT * c_mqtt + c_eq + c_parc))
    print(f"[AC7] N_max (parc typique multi-capteurs, 90% enveloppe) = {n_max}")
    assert n_max > 0


# --- AC7 : rejeu bout-en-bout (handler réel, vrai DiscoveryPublisher, faux pont MQTT) ---


def _multi_capteur_parc(n: int, n_inclus: int | None = None):
    n_inclus = n if n_inclus is None else n_inclus
    eq_logics, scope_equipements, eligibility, mappings, publications = {}, [], {}, {}, {}
    registry = MapperRegistry()
    for i in range(n):
        eq_id = 100 + i
        inclus = i < n_inclus
        eq = _multi_capteur_eq(eq_id)
        eq_logics[eq_id] = eq
        scope_equipements.append({
            "eq_id": eq_id, "object_id": 1, "name": f"Dimmer {eq_id}",
            "effective_state": "include" if inclus else "exclude", "decision_source": "global",
            "is_exception": False, "has_pending_home_assistant_changes": False,
        })
        eligibility[eq_id] = EligibilityResult(is_eligible=inclus, reason_code="eligible" if inclus else "excluded_eqlogic")
        if inclus:
            evaluation = evaluate_equipment(
                eq, _snapshot(eq), eligibility[eq_id], mapper_registry=registry, confidence_policy="strict",
                persisted_overrides={}, persisted_equipment_overrides={},
            )
            mappings[eq_id] = evaluation.mapping
            publications[eq_id] = PublicationDecision(
                should_publish=True, reason="sure", mapping_result=evaluation.mapping,
                state_topic=f"jeedom2ha/{eq_id}/state", active_or_alive=True, discovery_published=True,
            )
    topology = TopologySnapshot(timestamp="2026-09-30T00:00:00Z", objects={1: JeedomObject(id=1, name="Salon")}, eq_logics=eq_logics)
    published_scope = {
        "global": {"counts": {"total": n, "include": n_inclus, "exclude": n - n_inclus, "exceptions": 0},
                   "effective_state": "include", "has_pending_home_assistant_changes": False},
        "pieces": [], "equipements": scope_equipements,
    }
    return topology, published_scope, eligibility, mappings, publications


def _build_app(n: int, n_inclus: int, tmp_path) -> tuple:
    topology, published_scope, eligibility, mappings, publications = _multi_capteur_parc(n, n_inclus)
    app = http_server.create_app(local_secret=SECRET)
    bridge = _FakeMqttBridge()
    app["mqtt_bridge"] = bridge
    app["topology"] = topology
    app["published_scope"] = published_scope
    app["eligibility"] = eligibility
    app["mappings"] = mappings
    app["publications"] = publications
    app["data_dir"] = str(tmp_path)
    # Revue Codex P1 (PR #189, 2e tour) : un vrai `StateSynchronizer` branché sur le faux
    # pont MQTT, pour que `publish_click_states()` (état au clic) soit exercé et compté
    # comme dans le vrai « Publier », pas seulement la découverte.
    app["state_synchronizer"] = StateSynchronizer(app, bridge)
    return app, bridge


def _current_values_for(n_inclus: int) -> dict:
    """Une valeur `current_values` par commande info de chaque équipement inclus (Etat,
    Puissance, Consommation), comme le relais PHP réel au clic « Publier »."""
    values: dict = {}
    for i in range(n_inclus):
        eq_id = 100 + i
        base = eq_id * 100
        values[base + 3] = "1"  # Etat (LIGHT_STATE)
        values[base + 5] = 42  # Puissance (POWER)
        values[base + 6] = 3.5  # Consommation (CONSUMPTION)
    return values


@pytest.fixture
def cli_factory(aiohttp_client):
    async def _make(app):
        return await aiohttp_client(app)
    return _make


async def _run_publier(cli, deadline_s: float = 55.0, current_values: Optional[dict] = None):
    start = time.perf_counter()
    payload = {"intention": "publier", "portee": "global", "selection": ["all"], "deadline_s": deadline_s}
    if current_values:
        payload["current_values"] = current_values
    response = await cli.post("/action/execute", json=payload, headers=VALID_HEADERS)
    duration = time.perf_counter() - start
    return response, duration


@pytest.mark.asyncio
async def test_ac7_rejeu_mesure_30_09_sous_deadline(cli_factory, tmp_path):
    """292 au total, 94 évalués/publiés (mesure terrain du 30/09) : le parcours réel
    (évaluation réelle + vrai DiscoveryPublisher + faux pont MQTT avec latence réelle)
    reste sous deadline_s."""
    n_total, n_pause = 292, 94
    app, bridge = _build_app(n_total, n_pause, tmp_path)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(http_server, "DiscoveryPublisher", lambda mqtt_bridge: DiscoveryPublisher(mqtt_bridge))
        cli = await cli_factory(app)
        response, duration = await _run_publier(cli, current_values=_current_values_for(n_pause))
    print(f"\n[AC7] mesure 30/09 (292/94) : duration={duration:.3f}s appels_mqtt={bridge.call_count} "
          f"(par équipement={bridge.call_count / n_pause:.2f})")
    assert response.status == 200
    assert duration < 55.0


@pytest.mark.asyncio
async def test_ac7_petite_portee_grand_inventaire_sous_deadline(cli_factory, tmp_path):
    """1 équipement ciblé sur un inventaire de 5000 (parc dominant)."""
    n_total, n_inclus = 5000, 1
    app, bridge = _build_app(n_total, n_inclus, tmp_path)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(http_server, "DiscoveryPublisher", lambda mqtt_bridge: DiscoveryPublisher(mqtt_bridge))
        cli = await cli_factory(app)
        response, duration = await _run_publier(cli, current_values=_current_values_for(n_inclus))
    print(f"\n[AC7] petite portée / grand inventaire (1/5000) : duration={duration:.3f}s appels_mqtt={bridge.call_count}")
    assert response.status == 200
    assert duration < 55.0


@pytest.mark.asyncio
async def test_ac7_scenario_mixte_sous_deadline(cli_factory, tmp_path):
    """Scénario mixte : portée courante (94) + grand parc (1000)."""
    n_total, n_inclus = 1000, 94
    app, bridge = _build_app(n_total, n_inclus, tmp_path)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(http_server, "DiscoveryPublisher", lambda mqtt_bridge: DiscoveryPublisher(mqtt_bridge))
        cli = await cli_factory(app)
        response, duration = await _run_publier(cli, current_values=_current_values_for(n_inclus))
    print(f"\n[AC7] scénario mixte (94/1000) : duration={duration:.3f}s appels_mqtt={bridge.call_count}")
    assert response.status == 200
    assert duration < 55.0


@pytest.mark.asyncio
async def test_ac7_parc_typique_90_pct_enveloppe_sous_deadline(cli_factory, tmp_path):
    """Parc typique (équipement multi-capteurs) dimensionné à `N_max` (90% de l'enveloppe),
    calculé à partir des coûts mesurés (cf. `test_ac7_couts_mesures_et_enveloppe_respectee`)."""
    c_eq = _measure_c_eq() * MARGE_MESURE * MACHINE_FACTOR
    c_parc = _measure_c_parc(500, str(tmp_path)) * MARGE_MESURE * MACHINE_FACTOR
    c_mqtt = LATENCE_MQTT_S * MARGE_MESURE * MACHINE_FACTOR
    budget_travail = action_pacing.budget_travail(55.0)
    # Revue Codex P1 (PR #189, 2e tour) : appels MQTT par équipement multi-capteurs = 3
    # discovery (light + 2 sensors) + 2 état au clic (les 2 sensors streamés ; le light
    # n'est pas streamé, cf. StateSynchronizer.streams_actionable_type) ; la disponibilité
    # locale n'est pas publiée ici (`local_availability_supported` absent du fixture, comme
    # en discovery seule) et n'ajoute donc aucun appel supplémentaire mesuré.
    APPELS_MQTT_PAR_EQUIPEMENT = 5
    n_max = int((0.90 * budget_travail) / (APPELS_MQTT_PAR_EQUIPEMENT * c_mqtt + c_eq + c_parc))
    assert n_max > 0

    app, bridge = _build_app(n_max, n_max, tmp_path)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(http_server, "DiscoveryPublisher", lambda mqtt_bridge: DiscoveryPublisher(mqtt_bridge))
        cli = await cli_factory(app)
        response, duration = await _run_publier(cli, current_values=_current_values_for(n_max))
    print(f"\n[AC7] parc typique à 90% enveloppe : N_max={n_max} duration={duration:.3f}s "
          f"appels_mqtt={bridge.call_count} (par équipement={bridge.call_count / n_max:.2f})")
    assert response.status == 200
    assert duration < 55.0
