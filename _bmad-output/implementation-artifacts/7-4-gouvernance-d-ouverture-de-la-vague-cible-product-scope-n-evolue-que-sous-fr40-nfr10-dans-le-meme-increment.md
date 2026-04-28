# Story 7.4 : Gouvernance d'ouverture de la vague cible — `PRODUCT_SCOPE` n'évolue que sous FR40 / NFR10 dans le même incrément

Status: done

## Story

En tant que mainteneur de jeedom2ha,
je veux ouvrir `sensor` et `binary_sensor` dans `PRODUCT_SCOPE` uniquement après avoir réuni les trois preuves FR40 dans ce même incrément,
afin que l'ouverture produit soit gouvernée, testable, non arbitraire — et que le verrou CI `test_product_scope_has_governance_proof` la valide automatiquement.

## Contexte

### Positionnement dans la séquence pe-epic-7

| Story | Transition d'état | Moyen |
|-------|------------------|-------|
| 7.2 (done) | ∅ → `connu` | `HA_COMPONENT_REGISTRY` + `SensorCapabilities` |
| 7.3 (done) | `connu` → `validable` | tests unitaires `validate_projection()` — 14 tests, corpus 1164 |
| **7.4 (cette story)** | `validable` → `ouvert` | `PRODUCT_SCOPE` + contrat FR40 + mise à jour des tests impactés |

### Mécanisme de gouvernance déjà en place (héritage Story 3.3)

`test_step3_governance_fr40.py` contient le verrou CI AR13 :

```python
_GOVERNED_SCOPE = {
    "light": "test_governance_fr40_proof_light",
    "cover": "test_governance_fr40_proof_cover",
    "switch": "test_governance_fr40_proof_switch",
}

@pytest.mark.parametrize("component", PRODUCT_SCOPE)
def test_product_scope_has_governance_proof(component):
    assert component in HA_COMPONENT_REGISTRY       # condition 1 FR40
    assert component in _GOVERNED_SCOPE              # condition 2 FR40 (preuve nommée)
    assert _GOVERNED_SCOPE[component]                # nom non vide
```

**Ce test est le gardien CI FR40.** Si `sensor` ou `binary_sensor` entre dans `PRODUCT_SCOPE` sans être dans `_GOVERNED_SCOPE`, il échoue immédiatement avec message explicite. Ce fichier est la source d'autorité de la condition 2 de FR40.

### Interface `decide_publication()` (Story 4.1 / models/decide_publication.py)

```python
def decide_publication(
    mapping: MappingResult,
    confidence_policy: str = "sure_probable",
    product_scope: Optional[List[str]] = None,
) -> PublicationDecision:
```

Ordre d'évaluation (I4) :
1. Niveau 1 — étape 2 : confidence ∈ {"sure", "probable", "sure_mapping"} ?
2. Niveau 2 — étape 3 : `projection_validity.is_valid is True` ?
3. Niveau 3 — étape 4a : `ha_entity_type in product_scope` ?
4. Niveau 4 — étape 4b : confiance conforme à la politique ?
5. Niveau 5 — nominal : `PublicationDecision(should_publish=True, reason=confidence)`

### Tests impactés par l'extension de PRODUCT_SCOPE

**À corriger fonctionnellement :** trois fichiers utilisent `sensor` comme exemple de composant "hors PRODUCT_SCOPE" pour prouver les invariants I4/I6. Après cette story, `sensor` est dans le scope — ces cas deviennent invalides et doivent passer à `"climate"` (présent dans `HA_COMPONENT_REGISTRY`, absent de `PRODUCT_SCOPE`).

| Fichier | Lignes | Invariant | Action |
|---------|--------|-----------|--------|
| `test_step4_decide_publication.py` | 187, 206, 235 | I4, I6 | `sensor` → `climate` |
| `test_pipeline_invariants.py` | 170, 211, 280 | I4, I6 | `sensor` → `climate` |

**À mettre à jour (commentaires stales) :**

| Fichier | Lignes | Commentaire à mettre à jour |
|---------|--------|----------------------------|
| `test_step3_validate_projection.py` | 182, 207 | "non ouvert dans PRODUCT_SCOPE" → mentionner ouverture Story 7.4 |

**Non impactés** (assertions indépendantes de PRODUCT_SCOPE) :
- `test_step3_validate_projection.py` assertions — testent `validate_projection()` pure, pas `PRODUCT_SCOPE`
- `test_cause_mapping.py`, `test_story_6_3_honest_cause_mapping.py` — testent la traduction `reason_code → cause`, statique
- `test_diagnostic_endpoint.py` — injecte `PublicationDecision` manuellement, pas de lien PRODUCT_SCOPE
- Tous les fichiers `test_story_7_*.py` — tests d'isolation pure

### État du corpus

Baseline 7.3 : **1164 passed** (référence de non-régression).

Après cette story :
- `test_product_scope_has_governance_proof` : 3 cas → 5 cas (+2 runs paramétrés)
- `test_governance_fr40_proof_sensor` et `test_governance_fr40_proof_binary_sensor` : +2 fonctions
- `test_story_7_4_governance_product_scope.py` : ~8 nouveaux tests
- Corpus attendu : ≥ 1176 passed, 0 régression

## Acceptance Criteria

### AC1 — PRODUCT_SCOPE étendu à la vague cible

**Given** `ha_component_registry.py` après modification
**When** `PRODUCT_SCOPE` est inspecté
**Then** `PRODUCT_SCOPE == ["light", "cover", "switch", "sensor", "binary_sensor"]`
**And** `len(PRODUCT_SCOPE) == 5`

### AC2 — Verrou CI FR40 : sensor et binary_sensor dans `_GOVERNED_SCOPE`

**Given** `test_step3_governance_fr40.py` après modification
**When** le test paramétré `test_product_scope_has_governance_proof` s'exécute sur les 5 types
**Then** il passe pour `sensor` et `binary_sensor` sans erreur
**And** `_GOVERNED_SCOPE["sensor"] = "test_governance_fr40_proof_sensor"`
**And** `_GOVERNED_SCOPE["binary_sensor"] = "test_governance_fr40_proof_binary_sensor"`

### AC3 — Preuves de gouvernance FR40 pour la vague

**Given** `test_governance_fr40_proof_sensor()` dans `test_step3_governance_fr40.py`
**When** il s'exécute
**Then** `validate_projection("sensor", SensorCapabilities(has_state=True))` → `is_valid=True`
**And** `validate_projection("sensor", SensorCapabilities(has_state=False))` → `is_valid=False, reason_code="ha_missing_state_topic"`

**Given** `test_governance_fr40_proof_binary_sensor()` dans `test_step3_governance_fr40.py`
**When** il s'exécute
**Then** `validate_projection("binary_sensor", SensorCapabilities(has_state=True))` → `is_valid=True`
**And** `validate_projection("binary_sensor", SensorCapabilities(has_state=False))` → `is_valid=False, reason_code="ha_missing_state_topic"`

### AC4 — `decide_publication()` autorise la vague cible

**Given** un `MappingResult` avec `ha_entity_type="sensor"`, `confidence="sure"`, `projection_validity.is_valid=True`
**When** `decide_publication()` est appelée avec `confidence_policy="sure_probable"`
**Then** `should_publish=True` et `reason="sure"`

**Given** un `MappingResult` avec `ha_entity_type="binary_sensor"`, `confidence="sure"`, `projection_validity.is_valid=True`
**When** `decide_publication()` est appelée avec `confidence_policy="sure_probable"`
**Then** `should_publish=True` et `reason="sure"`

### AC5 — Tests I4/I6 réparés : type hors scope réel

**Given** `test_step4_decide_publication.py` et `test_pipeline_invariants.py` après modification
**When** les cas qui testaient `sensor` comme "hors PRODUCT_SCOPE" sont relus
**Then** ils utilisent `"climate"` (composant dans `HA_COMPONENT_REGISTRY`, absent de `PRODUCT_SCOPE`)
**And** les invariants I4 et I6 sont toujours couverts avec une prémisse valide
**And** tous les tests de ces fichiers passent

### AC6 — Non-régression corpus complet

**Given** tous les changements de cette story appliqués
**When** `python3 -m pytest` est exécuté depuis `resources/daemon/`
**Then** corpus ≥ 1176 passed, 0 régression, 0 warning ERROR

## Tasks / Subtasks

- [x] Task 1 — Modifier `PRODUCT_SCOPE` dans `ha_component_registry.py` (AC: #1)
  - [x] Ligne 64 : `PRODUCT_SCOPE = ["light", "cover", "switch", "sensor", "binary_sensor"]`
  - [x] Mettre à jour le commentaire de version sur la même ligne

- [x] Task 2 — Mettre à jour `test_step3_governance_fr40.py` (AC: #2, #3)
  - [x] Ajouter `SensorCapabilities` aux imports depuis `models.mapping`
  - [x] Ajouter `"sensor": "test_governance_fr40_proof_sensor"` à `_GOVERNED_SCOPE`
  - [x] Ajouter `"binary_sensor": "test_governance_fr40_proof_binary_sensor"` à `_GOVERNED_SCOPE`
  - [x] Implémenter `test_governance_fr40_proof_sensor()` : nominal `has_state=True` → `is_valid=True` + échec `has_state=False` → `is_valid=False, reason_code="ha_missing_state_topic"`
  - [x] Implémenter `test_governance_fr40_proof_binary_sensor()` : même structure

- [x] Task 3 — Corriger les tests I4/I6 impactés (AC: #5)
  - [x] `test_step4_decide_publication.py` ligne 187 : `sensor` → `climate` (commentaire `# hors PRODUCT_SCOPE`)
  - [x] `test_step4_decide_publication.py` ligne 206 : `sensor` → `climate` (commentaire `# hors PRODUCT_SCOPE`)
  - [x] `test_step4_decide_publication.py` ligne 235 : `sensor` → `climate` (commentaire `# hors scope`)
  - [x] `test_pipeline_invariants.py` ligne 170 : `sensor` → `climate` (commentaire `# hors PRODUCT_SCOPE`)
  - [x] `test_pipeline_invariants.py` ligne 211 : `sensor` → `climate` (commentaire `# hors PRODUCT_SCOPE`)
  - [x] `test_pipeline_invariants.py` ligne 280 : `sensor` → `climate` (commentaire `# étape 4a`)
  - [x] `test_step3_validate_projection.py` ligne 182 : mettre à jour commentaire ("non ouvert → ouvert depuis Story 7.4")
  - [x] `test_step3_validate_projection.py` ligne 207 : même mise à jour commentaire pour `select`

- [x] Task 4 — Créer `test_story_7_4_governance_product_scope.py` (AC: #1, #4, #6)
  - [x] `test_product_scope_wave_opening_complete()` — PRODUCT_SCOPE contient les 5 types attendus
  - [x] `test_decide_publication_authorizes_sensor_sure()` — sensor + sure + is_valid=True → should_publish=True
  - [x] `test_decide_publication_authorizes_binary_sensor_sure()` — binary_sensor + sure + is_valid=True → should_publish=True
  - [x] `test_decide_publication_sensor_probable_sure_probable_policy()` — sensor + probable + sure_probable → should_publish=True
  - [x] `test_decide_publication_sensor_probable_sure_only_policy()` — sensor + probable + sure_only → should_publish=False, reason="probable_skipped" (le gate politique fonctionne toujours)
  - [x] `test_governance_gate_sensor_not_in_scope_when_scope_empty()` — sensor + scope=[] → ha_component_not_in_product_scope (démontre que le mécanisme d'exclusion explicite reste fonctionnel)
  - [x] `test_fr40_condition1_sensor_binary_sensor_in_registry()` — les deux types ont required_fields + required_capabilities dans HA_COMPONENT_REGISTRY
  - [x] `test_fr40_condition3_nfr10_non_regression_existing_scope()` — light/cover/switch toujours autorisés par decide_publication (4D non-régression)

- [x] Task 5 — Valider la non-régression corpus complet (AC: #6)
  - [x] `python3 -m pytest resources/daemon/tests/unit/test_story_7_4_governance_product_scope.py -v` → 8/8 PASS
  - [x] `python3 -m pytest resources/daemon/tests/unit/test_step3_governance_fr40.py -v` → 12/12 PASS (5 types paramétrés dont sensor/binary_sensor)
  - [x] `python3 -m pytest resources/daemon/tests/unit/test_step4_decide_publication.py resources/daemon/tests/unit/test_pipeline_invariants.py -v` → 29/29 PASS
  - [x] `python3 -m pytest` (corpus complet depuis racine projet) → 1176 passed, 0 régression

## Dev Notes

### Fichiers à modifier

```
resources/daemon/validation/ha_component_registry.py   → PRODUCT_SCOPE (1 ligne)
resources/daemon/tests/unit/test_step3_governance_fr40.py  → _GOVERNED_SCOPE + 2 proof fonctions
resources/daemon/tests/unit/test_step4_decide_publication.py  → 3 remplacement sensor→climate
resources/daemon/tests/unit/test_pipeline_invariants.py  → 3 remplacements sensor→climate
resources/daemon/tests/unit/test_step3_validate_projection.py  → 2 mises à jour de commentaires
```

### Fichier à créer

```
resources/daemon/tests/unit/test_story_7_4_governance_product_scope.py
```

### Imports pour `test_step3_governance_fr40.py`

Ajouter `SensorCapabilities` à l'import existant :
```python
from models.mapping import LightCapabilities, CoverCapabilities, SwitchCapabilities, SensorCapabilities
```

### Structure minimale de `test_story_7_4_governance_product_scope.py`

```python
"""Tests story 7.4 — gouvernance d'ouverture de la vague cible.

Prouve que sensor et binary_sensor satisfont FR40 et sont autorisés par
decide_publication() après ouverture dans PRODUCT_SCOPE.
Tests en isolation totale : aucun daemon, réseau, asyncio.
"""

from typing import Optional

from models.mapping import MappingResult, ProjectionValidity, LightCapabilities, SensorCapabilities
from models.decide_publication import decide_publication
from validation.ha_component_registry import PRODUCT_SCOPE, HA_COMPONENT_REGISTRY


def _make_mapping(
    ha_entity_type: str = "sensor",
    confidence: str = "sure",
    projection_validity: Optional[ProjectionValidity] = None,
) -> MappingResult:
    pv = projection_validity if projection_validity is not None else ProjectionValidity(
        is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[]
    )
    mr = MappingResult(
        ha_entity_type=ha_entity_type,
        confidence=confidence,
        reason_code="sensor_state",
        jeedom_eq_id=1,
        ha_unique_id="jeedom2ha_eq_1",
        ha_name="Test sensor",
        capabilities=SensorCapabilities(has_state=True),
    )
    mr.projection_validity = pv
    return mr
```

### Remplacement sensor → climate : pourquoi climate ?

`climate` est dans `HA_COMPONENT_REGISTRY` (`required_capabilities=[]`, `required_fields=["availability"]`) mais absent de `PRODUCT_SCOPE` pour ce cycle. Il satisfait exactement la propriété attendue : composant connu, non ouvert. Les invariants I4 et I6 restent couverts avec une prémisse exacte.

Pour I4 (étape 2 / 3 prime sur étape 4) : les tests utilisent `confidence="ambiguous"` (échec étape 2) ou `projection_validity invalid` (échec étape 3) — le scope du composant n'est jamais atteint dans la résolution. Le remplacement sensor→climate ne change pas la valeur de l'assertion.

Pour I6 (`reason` jamais null) : climate + `is_valid=True` + `confidence="sure"` + `confidence_policy="sure_probable"` → `ha_component_not_in_product_scope` (step 4a) — non null. Couvre la même branche qu'avant le remplacement.

### Preuves de gouvernance : pattern exact à reproduire

```python
def test_governance_fr40_proof_sensor():
    result_nominal = validate_projection("sensor", SensorCapabilities(has_state=True))
    assert result_nominal.is_valid is True
    assert result_nominal.reason_code is None

    result_fail = validate_projection("sensor", SensorCapabilities(has_state=False))
    assert result_fail.is_valid is False
    assert result_fail.reason_code == "ha_missing_state_topic"
```

Même structure pour `binary_sensor` — `sensor` et `binary_sensor` partagent `SensorCapabilities`.

### Dev Agent Guardrails

- **Ne pas modifier `validate_projection()`** ni `HA_COMPONENT_REGISTRY` — correcte, hors scope
- **`PRODUCT_SCOPE` : une seule ligne à modifier** (ligne 64 de `ha_component_registry.py`)
- **`_GOVERNED_SCOPE` doit rester en égalité stricte avec `set(PRODUCT_SCOPE)`** après modification — c'est le contrat AR13
- **Ne pas toucher les tests `test_story_7_1`, `7_2`, `7_3`** — baseline de non-régression
- **climate** est le remplacement correct pour "hors PRODUCT_SCOPE" — vérifier que `"climate"` est bien dans `HA_COMPONENT_REGISTRY` avant de l'utiliser (ligne 56 de `ha_component_registry.py`)
- **Tests synchrones uniquement** — aucun `pytest.mark.asyncio`, aucune fixture daemon
- **`SensorCapabilities` est partagée pour sensor et binary_sensor** — pas de dataclass séparée
- **Corpus attendu ≥ 1176** — si le run donne moins, chercher un fichier non exécuté

### Project Structure Notes

- Modification code : `resources/daemon/validation/ha_component_registry.py` ligne 64 uniquement
- Nouveau fichier : `resources/daemon/tests/unit/test_story_7_4_governance_product_scope.py`
- Fichiers test modifiés : 5 (voir tableau Tasks)
- Aucune modification `http_server.py`, `cause_mapping.py`, `models/`, `mapping/`, `transport/`

### References

- [Source: `resources/daemon/validation/ha_component_registry.py` — `PRODUCT_SCOPE` ligne 64, `HA_COMPONENT_REGISTRY`, commentaire AR13 lignes 65-68]
- [Source: `resources/daemon/tests/unit/test_step3_governance_fr40.py` — `_GOVERNED_SCOPE` lignes 48-55, `test_product_scope_has_governance_proof` lignes 78-110, `test_governance_fr40_proof_light/cover/switch` lignes 117-175]
- [Source: `resources/daemon/models/decide_publication.py` — interface `decide_publication()`, ordre I4 niveaux 1-5]
- [Source: `resources/daemon/tests/unit/test_step4_decide_publication.py` — helper `_make_mapping()`, `_valid_pv()`, lignes 187/206/235 à modifier]
- [Source: `resources/daemon/tests/unit/test_pipeline_invariants.py` — lignes 170/211/280 à modifier]
- [Source: `resources/daemon/tests/unit/test_step3_validate_projection.py` — lignes 182/207 (commentaires stales)]
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` — Epic 7 Story 7.4, FR39/FR40/NFR10/AR13]
- [Source: `_bmad-output/implementation-artifacts/7-3-validation-de-projection-de-la-vague-cible-cas-nominaux-et-cas-d-echec-representatifs-rendent-les-types-validables.md` — baseline 1164 passed, contrat SensorCapabilities, chemin `_resolve_capability`]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 — 2026-04-28

### Debug Log References

Aucun blocage. 3 tests snapshots (test_ha_component_registry, test_story_7_2, test_story_7_3) non mentionnés dans Dev Notes mais impactés par l'extension de PRODUCT_SCOPE — mis à jour pour refléter le nouvel état post-Story-7.4.

### Completion Notes List

- PRODUCT_SCOPE étendu à 5 types : light, cover, switch, sensor, binary_sensor (1 ligne modifiée)
- Verrou CI FR40 mis à jour : _GOVERNED_SCOPE + 2 fonctions de preuve (sensor, binary_sensor) dans test_step3_governance_fr40.py — test paramétré passe maintenant sur 5 types
- 6 occurrences sensor→climate dans test_step4_decide_publication.py et test_pipeline_invariants.py (invariants I4/I6 couverts avec prémisse exacte)
- 2 commentaires stales mis à jour dans test_step3_validate_projection.py
- 3 assertions snapshot PRODUCT_SCOPE mises à jour (test_ha_component_registry, test_story_7_2_wave_registry, test_story_7_3_projection_validation_wave)
- Nouveau fichier : test_story_7_4_governance_product_scope.py — 8 tests couvrant AC1/AC4/AC5/FR40/NFR10
- Corpus final : 1176 passed, 0 régression (baseline 7.3 = 1164 ; +12 tests = 1176)

### File List

resources/daemon/validation/ha_component_registry.py
resources/daemon/tests/unit/test_step3_governance_fr40.py
resources/daemon/tests/unit/test_step4_decide_publication.py
resources/daemon/tests/unit/test_pipeline_invariants.py
resources/daemon/tests/unit/test_step3_validate_projection.py
resources/daemon/tests/unit/test_ha_component_registry.py
resources/daemon/tests/unit/test_story_7_2_wave_registry.py
resources/daemon/tests/unit/test_story_7_3_projection_validation_wave.py
resources/daemon/tests/unit/test_story_7_4_governance_product_scope.py (nouveau)
_bmad-output/implementation-artifacts/sprint-status.yaml

## Change Log

- 2026-04-28 — Implémentation Story 7.4 : ouverture PRODUCT_SCOPE à sensor/binary_sensor sous FR40 ; verrou CI mis à jour ; +12 tests ; corpus 1176 passed, 0 régression
- 2026-04-28 — Code review fixes (M1/L1/L2/L3, tests-only) :
  - M1 : `test_product_scope_unchanged` renommé en `test_product_scope_snapshot_with_wave_open` dans `test_story_7_2_wave_registry.py` et `test_story_7_3_projection_validation_wave.py` (le nom "unchanged" devenait trompeur post-7.4)
  - L1/L2 : helper `_make_mapping` du fichier 7.4 paramètre désormais `capabilities` et `reason_code` selon `ha_entity_type` via `_default_capabilities()` + `_REASON_CODE_BY_TYPE` (cohérence type/capabilities pour light/cover/switch dans le test NFR10)
  - L3 : ajout `test_decide_publication_binary_sensor_probable_sure_only_policy` — symétrie de couverture sensor/binary_sensor sur le gate `sure_only`
  - Corpus final : 1177 passed (+1 vs baseline review), 0 régression — aucun changement produit, périmètre strictement test
