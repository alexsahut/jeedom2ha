"""Story 19.0 — Task 4 : harnais de parité sur le corpus doré (AC3, revue Alexandre PR #167).

Exécute `evaluate_equipment()` et le pipeline classique (`decide_publication()` appelé
directement + `_publish_additional_sensors` pour les secondaires) sur le même corpus
doré (`fixtures/golden_corpus/sync_payload.json`, 59 eqLogics couvrant lights/covers/
switches/ambiguous/ineligible/blocked/sensors/binary_sensors) et vérifie qu'aucun écart
n'apparaît, à TROIS granularités (primaire, secondaires, commande) et pour :

  a. décisions primaires seules, sans override, politique `sure_probable` (défaut) ;
  b. décisions SECONDAIRES par équipement multi-sensor (5 eqs concernés sur le corpus :
     553/554/583/628/457, jusqu'à 13 secondaires par eq) ;
  c. niveau COMMANDE : chaque cmd_id d'une entité couverte porte bien la décision de
     publication de cette entité ;
  d. jeu représentatif d'overrides persistés (type_override, exclusion eqLogic, exclusion
     command, force_publish eqLogic) sélectionné pour couvrir chaque code d'override ;
  e. politique `sure_only` (bascule config, Story 4.3) — les cas confidence=probable
     doivent passer à `probable_skipped` dans les DEUX chemins.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# NOTE : le paquet racine `tests/` (rootdir) et `resources/daemon/tests/` portent
# le même nom `tests`, ce qui rend `tests.tools...` ambigu selon l'ordre de
# résolution de `pythonpath`. On importe donc le harnais par chemin direct
# plutôt que via un import de paquet, pour rester indépendant de cet ordre.
_TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from parity_harness_19_0 import compute_parity_report  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "golden_corpus"
SYNC_FIXTURE_PATH = FIXTURES_DIR / "sync_payload.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_ac3_parity_harness_golden_corpus_no_discrepancy():
    """Cas (a) — décisions primaires + secondaires + commandes, sans override, politique par défaut."""
    payload = _load_json(SYNC_FIXTURE_PATH)

    discrepancies = compute_parity_report(payload)

    assert discrepancies == [], (
        "Écart(s) détecté(s) entre evaluate_equipment() et le pipeline classique "
        f"sur le corpus doré (aucun override, sure_probable) : {discrepancies}"
    )


def test_ac3_parity_harness_golden_corpus_covers_eligible_equipments():
    """Garde-fou : le harnais doit réellement comparer un nombre significatif
    d'équipements (sinon un test qui "passe" pourrait masquer un corpus vide
    ou une éligibilité cassée en amont)."""
    payload = _load_json(SYNC_FIXTURE_PATH)

    from models.topology import TopologySnapshot, assess_all

    snapshot = TopologySnapshot.from_jeedom_payload(payload)
    eligibility = assess_all(snapshot)
    eligible_count = sum(1 for res in eligibility.values() if res.is_eligible)

    assert eligible_count > 10, (
        f"Corpus doré : seulement {eligible_count} équipement(s) éligible(s), "
        "harnais de parité insuffisamment représentatif"
    )


def test_parity_harness_covers_secondaries():
    """Garde-fou (revue Alexandre) : le corpus doré doit inclure des équipements multi-sensor,
    sinon la couverture des secondaires (c) est nulle et un écart secondaire pourrait passer
    inaperçu."""
    payload = _load_json(SYNC_FIXTURE_PATH)

    from mapping.registry import MapperRegistry
    from models.topology import TopologySnapshot, assess_all

    snapshot = TopologySnapshot.from_jeedom_payload(payload)
    eligibility = assess_all(snapshot)
    registry = MapperRegistry()

    total_secondaries = 0
    eqs_with_secondaries = 0
    for eq_id, res in eligibility.items():
        if not res.is_eligible:
            continue
        mapping = registry.map(snapshot.eq_logics[eq_id], snapshot)
        if mapping is None:
            continue
        nb = len(mapping.additional_mappings or [])
        if nb > 0:
            eqs_with_secondaries += 1
            total_secondaries += nb

    assert eqs_with_secondaries >= 3 and total_secondaries >= 20, (
        f"Corpus doré : seulement {eqs_with_secondaries} eq multi-sensor "
        f"({total_secondaries} secondaires au total) — couverture parité insuffisante"
    )


def test_parity_harness_covers_field_multi_entity_regressions():
    """Le corpus golden protège les équipements terrain multi-entités critiques.

    Une couverture seulement quantitative laisserait disparaître silencieusement une
    famille entière ; ces cinq eq_ids couvrent MSunPV, chauffe-eau, IQ EV, pilotage
    solaire et lumière+consommation.
    """
    payload = _load_json(SYNC_FIXTURE_PATH)
    from mapping.registry import MapperRegistry
    from models.topology import TopologySnapshot, assess_all

    snapshot = TopologySnapshot.from_jeedom_payload(payload)
    eligibility = assess_all(snapshot)
    registry = MapperRegistry()
    expected = {553, 554, 583, 628, 457}
    observed = {}
    for eq_id in expected:
        assert eligibility[eq_id].is_eligible, f"eq{eq_id} doit rester éligible dans le golden"
        mapping = registry.map(snapshot.eq_logics[eq_id], snapshot)
        assert mapping is not None, f"eq{eq_id} doit rester mappé dans le golden"
        observed[eq_id] = len(mapping.additional_mappings or [])

    assert all(count > 0 for count in observed.values()), (
        "Chaque équipement terrain critique doit conserver au moins un secondaire : "
        f"{observed}"
    )


def test_parity_harness_sure_only_policy():
    """Cas (e) — politique `sure_only` (Story 4.3). Les équipements `probable` doivent basculer
    en `probable_skipped` dans les deux chemins ; zéro écart attendu."""
    payload = _load_json(SYNC_FIXTURE_PATH)

    discrepancies = compute_parity_report(payload, confidence_policy="sure_only")

    assert discrepancies == [], (
        "Écart(s) sous politique sure_only entre evaluate_equipment() et le pipeline classique : "
        f"{discrepancies}"
    )


# ---------------------------------------------------------------------------
# Jeu représentatif d'overrides — cas (d) revue Alexandre
# ---------------------------------------------------------------------------
# eq_id/cmd_id choisis sur le corpus doré pour couvrir CHAQUE type d'override attendu.
# Sélection dérivée du corpus (cf. `test_parity_harness_representative_overrides` pour la
# vérification que ces IDs existent bien) :
#   - eq=1000 (light "sure"), cmd=10001 → override de TYPE (light → cover)
#   - eq=1005 (light "sure")            → exclusion EQUIPMENT (publication_override=exclude)
#   - eq=3000 (switch "sure"), cmd=30001 → exclusion COMMAND
#   - eq=6001 (light "sure")            → force_publish EQUIPMENT
_REPRESENTATIVE_OVERRIDES = {
    "1000:10001": {"source": "user", "ha_entity_type": "cover"},
    "3000:30001": {"source": "user", "publication_override": "exclude"},
}
_REPRESENTATIVE_EQUIPMENT_OVERRIDES = {
    "1005": {"source": "user", "publication_override": "exclude"},
    "6001": {"source": "user", "publication_override": "force_publish"},
}


def test_parity_harness_representative_overrides_exist_in_corpus():
    """Garde-fou (revue Alexandre) : les eq/cmd IDs choisis pour le jeu d'overrides
    représentatif doivent exister dans le corpus doré. Si le corpus évolue, ce test échoue
    en premier et pointe l'incohérence — le harnais de parité ne compare pas silencieusement
    du vide (`nothing overrides nothing`)."""
    payload = _load_json(SYNC_FIXTURE_PATH)

    from models.topology import TopologySnapshot
    snapshot = TopologySnapshot.from_jeedom_payload(payload)

    for key in _REPRESENTATIVE_OVERRIDES:
        eq_str, cmd_str = key.split(":")
        eq_id, cmd_id = int(eq_str), int(cmd_str)
        eq = snapshot.eq_logics.get(eq_id)
        assert eq is not None, f"eq_id={eq_id} absent du corpus doré (override {key!r})"
        cmd_ids = {c.id for c in eq.cmds}
        assert cmd_id in cmd_ids, (
            f"cmd_id={cmd_id} absent de eq_id={eq_id} dans le corpus doré (override {key!r})"
        )

    for key in _REPRESENTATIVE_EQUIPMENT_OVERRIDES:
        eq_id = int(key)
        assert snapshot.eq_logics.get(eq_id) is not None, (
            f"eq_id={eq_id} absent du corpus doré (equipment_override {key!r})"
        )


def test_parity_harness_representative_overrides():
    """Cas (d) — jeu d'overrides persistés représentatif appliqué aux DEUX chemins :
    type_override + exclusion command + exclusion eqLogic + force_publish. Zéro écart attendu."""
    payload = _load_json(SYNC_FIXTURE_PATH)

    discrepancies = compute_parity_report(
        payload,
        overrides=_REPRESENTATIVE_OVERRIDES,
        equipment_overrides=_REPRESENTATIVE_EQUIPMENT_OVERRIDES,
    )

    assert discrepancies == [], (
        "Écart(s) avec overrides représentatifs entre evaluate_equipment() et le pipeline "
        f"classique : {discrepancies}"
    )


def test_parity_harness_overrides_actually_bite():
    """Garde-fou (revue Alexandre) : les overrides représentatifs doivent réellement changer
    la décision d'au moins un équipement — sinon le cas (d) revient au cas (a) et ne teste
    rien de plus. On compare la décision avec/sans overrides sur les eq ciblés."""
    payload = _load_json(SYNC_FIXTURE_PATH)

    from mapping.overrides import apply_type_override, resolve_publication_override
    from mapping.registry import MapperRegistry
    from models.decide_publication import decide_publication
    from models.topology import TopologySnapshot, assess_all
    from validation.ha_component_registry import validate_projection

    snapshot = TopologySnapshot.from_jeedom_payload(payload)
    eligibility = assess_all(snapshot)

    def _decision(eq_id: int, with_overrides: bool):
        eq = snapshot.eq_logics[eq_id]
        registry = MapperRegistry()
        mapping = registry.map(eq, snapshot)
        overrides = _REPRESENTATIVE_OVERRIDES if with_overrides else {}
        eq_overrides = _REPRESENTATIVE_EQUIPMENT_OVERRIDES if with_overrides else {}
        mapping = apply_type_override(mapping, "", overrides=overrides)
        pv = validate_projection(mapping.ha_entity_type, mapping.capabilities)
        mapping.projection_validity = pv
        pub_override = None
        for cmd in (mapping.commands or {}).values():
            resolved = resolve_publication_override(eq_id, cmd.id, overrides, eq_overrides)
            if resolved is not None:
                pub_override = resolved
                break
        return decide_publication(mapping, confidence_policy="sure_probable",
                                  publication_override=pub_override)

    # eq=1005 : exclusion EQUIPMENT → should_publish devient False, reason 'publication_excluded_eqlogic'.
    assert eligibility[1005].is_eligible
    decision_1005_without = _decision(1005, with_overrides=False)
    decision_1005_with = _decision(1005, with_overrides=True)
    assert decision_1005_without.should_publish is True, "eq=1005 doit être publiable sans override"
    assert decision_1005_with.reason == "publication_excluded_eqlogic", (
        f"eq=1005 avec override d'exclusion eqLogic devrait passer à publication_excluded_eqlogic, "
        f"pas {decision_1005_with.reason!r}"
    )

    # eq=6001 : force_publish EQUIPMENT — au moins reason devient 'publication_forced'
    # (l'override peut coïncider avec la publication naturelle, mais le reason doit refléter le forçage).
    assert eligibility[6001].is_eligible
    decision_6001_with = _decision(6001, with_overrides=True)
    assert decision_6001_with.reason == "publication_forced", (
        f"eq=6001 avec force_publish devrait porter reason=publication_forced, "
        f"pas {decision_6001_with.reason!r}"
    )
