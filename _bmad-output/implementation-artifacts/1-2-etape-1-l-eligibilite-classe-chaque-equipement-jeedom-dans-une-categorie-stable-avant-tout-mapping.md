# Story 1.2 : Étape 1 — L'éligibilité classe chaque équipement Jeedom dans une catégorie stable avant tout mapping

Status: done

## Story

En tant qu'utilisateur,
je veux que le système détermine si chaque équipement est éligible avant toute tentative de mapping, en classant les causes d'inéligibilité dans des catégories distinctes et stables,
afin de savoir précisément quels équipements entrent dans le pipeline et pourquoi les autres n'y entrent pas.

## Acceptance Criteria

1. **Given** un équipement Jeedom satisfaisant toutes les règles de scope
   **When** le pipeline évalue l'éligibilité
   **Then** l'équipement est classé éligible et transmis à l'étape de mapping
   **And** le résultat porte `is_eligible=True` et `reason_code="eligible"`
   **And** l'éligibilité est deterministe : deux appels identiques produisent le même résultat (NFR1)

2. **Given** un équipement exclu par les règles de scope utilisateur (par équipement, plugin ou objet Jeedom)
   **When** le pipeline évalue l'éligibilité
   **Then** l'équipement est classé inéligible avec un `reason_code` de catégorie `excluded_*` correspondant à la source d'exclusion (`excluded_eqlogic` / `excluded_plugin` / `excluded_object`)
   **And** l'équipement n'entre pas dans l'étape de mapping

3. **Given** un équipement avec `is_enable=False` dans Jeedom
   **When** le pipeline évalue l'éligibilité
   **Then** l'équipement est classé inéligible avec `reason_code="disabled_eqlogic"`
   **And** l'équipement n'entre pas dans l'étape de mapping

4. **Given** un équipement sans aucune commande (`cmds=[]`)
   **When** le pipeline évalue l'éligibilité
   **Then** l'équipement est classé inéligible avec `reason_code="no_commands"`

5. **Given** un équipement dont toutes les commandes ont `generic_type=None`
   **When** le pipeline évalue l'éligibilité
   **Then** l'équipement est classé inéligible avec `reason_code="no_supported_generic_type"` (code existant — équivalent stable de `no_generic_type` per FR9/NFR8)
   **And** ce cas est distinct d'un équipement éligible pour lequel aucun mapping ne peut être produit (FR8)

6. **Given** la suite de tests de l'étape 1
   **When** les cas de test sont exécutés
   **Then** il existe au moins un cas nominal (équipement éligible) et un cas d'échec par catégorie (inéligible avec cause explicite) exécutables en isolation, sans dépendance MQTT ni runtime Jeedom (NFR9)

## Tasks / Subtasks

- [x] Task 1 — Créer `resources/daemon/tests/unit/test_step1_eligibility.py` avec les cas nominaux (AC: #1, #6)
  - [x] Test `test_eligibility_nominal_eligible` : équipement avec `is_enable=True`, `cmds=[cmd avec generic_type]`, `is_excluded=False` → `is_eligible=True, reason_code="eligible"`
  - [x] Test `test_eligibility_eligible_confidence_unknown` : confirmer que `confidence="unknown"` pour un équipement éligible (incertitude sur le mapping qui suit, pas sur l'éligibilité)
  - [x] Test `test_assess_all_batch` : `assess_all(snapshot)` retourne un dict `{eq_id: EligibilityResult}` pour tous les équipements du snapshot

- [x] Task 2 — Cas d'exclusion de scope (AC: #2)
  - [x] Test `test_eligibility_excluded_eqlogic` : `is_excluded=True, exclusion_source="eqlogic"` → `reason_code="excluded_eqlogic"`, `is_eligible=False`
  - [x] Test `test_eligibility_excluded_plugin` : `is_excluded=True, exclusion_source="plugin"` → `reason_code="excluded_plugin"`, `is_eligible=False`
  - [x] Test `test_eligibility_excluded_object` : `is_excluded=True, exclusion_source="object"` → `reason_code="excluded_object"`, `is_eligible=False`
  - [x] Test `test_eligibility_excluded_source_absent_defaults_eqlogic` : `is_excluded=True, exclusion_source=None` → `reason_code="excluded_eqlogic"` (rétro-compatibilité)

- [x] Task 3 — Cas d'inéligibilité hors exclusion (AC: #3, #4, #5)
  - [x] Test `test_eligibility_disabled_eqlogic` : `is_enable=False` → `reason_code="disabled_eqlogic"`, `is_eligible=False`, `confidence="sure"`
  - [x] Test `test_eligibility_no_commands` : `cmds=[]` → `reason_code="no_commands"`, `is_eligible=False`, `confidence="sure"`
  - [x] Test `test_eligibility_no_generic_type` : commandes présentes mais toutes `generic_type=None` → `reason_code="no_supported_generic_type"`, `is_eligible=False`, `confidence="sure"`
  - [x] Test `test_eligibility_partial_generic_type_is_eligible` : au moins une commande avec `generic_type non-None` même si d'autres sont None → `is_eligible=True` (l'éligibilité ne requiert qu'UN generic_type)

- [x] Task 4 — Tests de priorité d'évaluation (ordre canonique : exclu > désactivé > sans cmds > sans generic_type)
  - [x] Test `test_priority_excluded_over_disabled` : équipement à la fois exclu et désactivé → `reason_code="excluded_eqlogic"` (exclu gagne)
  - [x] Test `test_priority_disabled_over_no_commands` : équipement désactivé sans commandes → `reason_code="disabled_eqlogic"` (désactivé gagne)
  - [x] Test `test_priority_no_commands_over_no_generic_type` : équipement actif, non-exclu, sans commandes (et donc sans generic_type implicitement) → `reason_code="no_commands"` (no_commands gagne)

- [x] Task 5 — Vérifier la non-régression
  - [x] Lancer `pytest resources/daemon/tests/` depuis `resources/daemon/` : tous les tests existants PASS (aucune modification de production)

## Dev Notes

### Contexte pipeline

L'étape 1 — Éligibilité est le filtre d'entrée du pipeline canonique à 5 étapes (Feature 0). Elle s'exécute avant tout mapping. Tout équipement inéligible ne passe jamais à l'étape 2. Tout équipement éligible reçoit `is_eligible=True` et sa cause d'éligibilité est `"eligible"` — c'est la valeur stable du `reason_code` pour les cas nominaux.

**Table de mapping pipeline → code (archi §Mapping pipeline → code) :**

| Étape pipeline | Module | Fonction principale |
|---|---|---|
| 1. Éligibilité | `models/topology.py` | `assess_all()` / `assess_eligibility()` |
| 2. Mapping candidat | `mapping/light.py`, `cover.py`, `switch.py` | `LightMapper.map()`, etc. |

### `assess_eligibility()` est déjà implémentée — NE PAS LA MODIFIER

La fonction `assess_eligibility(eq: JeedomEqLogic) -> EligibilityResult` dans `resources/daemon/models/topology.py:204` est complète et correcte. Elle implémente l'ordre canonique de priorité fondation V1.1 :

```
exclu → désactivé → sans commandes → sans generic_type → éligible
```

La Story 1.2 livre uniquement des **tests exhaustifs** — aucune modification du code de production.

### Taxonomie des catégories d'éligibilité (FR9 — stable, pas de chaînes libres)

| `reason_code` | Catégorie sémantique | `is_eligible` | `confidence` |
|---|---|---|---|
| `"eligible"` | Équipement éligible — entre dans le mapping | `True` | `"unknown"` |
| `"excluded_eqlogic"` | Exclusion individuelle (réglage jeedom2ha) | `False` | `"sure"` |
| `"excluded_plugin"` | Exclusion par plugin | `False` | `"sure"` |
| `"excluded_object"` | Exclusion par objet Jeedom | `False` | `"sure"` |
| `"disabled_eqlogic"` | Équipement désactivé dans Jeedom (`is_enable=False`) | `False` | `"sure"` |
| `"no_commands"` | Aucune commande rattachée à l'équipement | `False` | `"sure"` |
| `"no_supported_generic_type"` | Toutes les commandes sans `generic_type` | `False` | `"sure"` |

**Note NFR8 :** `"no_supported_generic_type"` est le code existant V1.1 — équivalent fonctionnel de `no_generic_type` mentionné dans l'epic. Ce code n'est PAS renommé (NFR8 : 0 renommage). Les tests assertent le code existant.

**Note pour Epic 4 :** ces chaînes de reason_code sont des candidats à la centralisation dans un registre/enum en Epic 4 (migration additive). Ne pas créer de constantes centralisées maintenant.

### `EligibilityResult` — dataclass existante

```python
# resources/daemon/models/topology.py:102
@dataclass
class EligibilityResult:
    is_eligible: bool
    reason_code: str          # code stable (ex: "excluded_eqlogic")
    confidence: str = "unknown"   # "sure" pour inéligible, "unknown" pour éligible
    reason_details: Optional[Dict[str, Any]] = None
```

`confidence="unknown"` pour un équipement éligible = incertitude sur le mapping (étape 2), pas sur l'éligibilité elle-même. C'est délibéré : l'éligibilité est certaine, mais le mapping peut encore échouer.

### Distinction FR8 : inéligible (étape 1) vs éligible-mais-non-projetable (étapes 2-3)

Cette distinction est fondamentale et doit apparaître dans les tests :
- **Inéligible étape 1** → `is_eligible=False`, `reason_code` in `{excluded_*, disabled_eqlogic, no_commands, no_supported_generic_type}` → l'équipement n'entre pas dans le mapping
- **Éligible mais non-projetable (étape 2)** → `is_eligible=True` → l'équipement ENTRE dans le mapping mais le mapper retourne `confidence="ambiguous"` ou `reason_code="no_mapping"`
- **Éligible mais invalide HA (étape 3)** → `is_eligible=True` → le mapping a réussi mais `validate_projection()` retourne `is_valid=False`

### Pattern de test à suivre (héritage story 1.1 + test_exclusion_filtering.py)

```python
"""Tests de l'étape 1 — Éligibilité — Story 1.2.

Vérifie que assess_eligibility() classe chaque équipement dans une catégorie
stable et distincte. Tests exécutables en isolation (NFR9).
"""
from models.topology import (
    JeedomCmd, JeedomEqLogic,
    assess_eligibility, assess_all, EligibilityResult,
    TopologySnapshot,
)

def _make_eq(id=1, is_excluded=False, exclusion_source=None,
             is_enable=True, cmds=None) -> JeedomEqLogic:
    return JeedomEqLogic(
        id=id, name="Test",
        is_excluded=is_excluded,
        exclusion_source=exclusion_source,
        is_enable=is_enable,
        cmds=cmds or [],
    )

def _cmd_with_generic(gt="LIGHT_ON") -> JeedomCmd:
    return JeedomCmd(id=1, name="On", generic_type=gt, type="action", sub_type="other")

def _cmd_no_generic() -> JeedomCmd:
    return JeedomCmd(id=2, name="Info", generic_type=None, type="info", sub_type="other")
```

- Pas de `conftest.py` — helpers locaux au fichier
- Nommage `test_eligibility_<sujet>_<scenario>()`
- Import direct depuis `models.topology` (pas d'imports circulaires)
- Aucune dépendance MQTT, pytest-asyncio, ou runtime Jeedom dans ce fichier

### Dev Agent Guardrails

- **`models/topology.py` — NE PAS MODIFIER** — l'implémentation de `assess_eligibility()` est complète (fondation V1.1). Si un défaut de comportement est constaté sur un AC, le remonter dans les notes de complétion sans modifier le code.
- **Portée stricte** : uniquement `resources/daemon/tests/unit/test_step1_eligibility.py` créé.
- **Pas de constantes centralisées** pour les reason_codes — Epic 4 candidate, pas cette story.
- **Pas de terrain** : cette story est pure logique Python sans MQTT, sans daemon, sans box réelle.
- **NFR9 : isolation absolue** — aucun test ne doit importer depuis `transport/`, `discovery/`, ou `sync/`.

### Project Structure Notes

**Fichier créé :** `resources/daemon/tests/unit/test_step1_eligibility.py`

Aucun autre fichier — `models/topology.py` n'est pas modifié.

La table `mapping pipeline → code` de l'architecture (§Structure projet) référence `models/topology.py` pour l'étape 1 avec `assess_all()` — c'est exactement le code couvert par cette story.

### References

- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §Story 1.2] — User story, AC, dev notes canoniques
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §Pipeline 5 étapes] — Étape 1 : entrée TopologySnapshot, sortie EligibilityResult
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §P2] — Isolation des sous-blocs : mapping lit EligibilityResult, ne le modifie pas
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §Mapping pipeline → code] — `models/topology.py` → `assess_all()`
- [Source: `resources/daemon/models/topology.py:102`] — `EligibilityResult` dataclass
- [Source: `resources/daemon/models/topology.py:204`] — `assess_eligibility()` implémentation complète
- [Source: `resources/daemon/tests/unit/test_exclusion_filtering.py`] — Pattern de test + helpers `_make_eq()`
- [Source: `resources/daemon/tests/unit/test_pipeline_contract.py`] — Tests NFR1 déterminisme sur `assess_eligibility()` (Story 1.1)
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §FR8] — Distinction inéligible vs éligible-non-projetable
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §NFR8] — 0 renommage reason_code existant

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_Aucun défaut de comportement constaté — assess_eligibility() conforme à tous les ACs._

### Completion Notes List

- 14 tests créés dans `test_step1_eligibility.py` couvrant les 5 ACs et NFR9 (isolation absolue)
- Ordre canonique d'évaluation confirmé : exclu > désactivé > sans cmds > sans generic_type
- `confidence="unknown"` pour éligible validé (délibéré : incertitude sur étape 2, pas sur étape 1)
- `assess_all()` sur snapshot multi-équipements retourne bien `{eq_id: EligibilityResult}`
- NFR8 respecté : `"no_supported_generic_type"` asserté tel quel (0 renommage)
- Non-régression : 304/304 tests PASS (290 existants + 14 nouveaux), 0 modification de production

### File List

- `resources/daemon/tests/unit/test_step1_eligibility.py` (créé)

## Senior Developer Review (AI)

**Reviewer :** Claude Opus 4.6 — 2026-04-10
**Verdict :** APPROVE

### AC Validation

| AC | Verdict |
|----|---------|
| #1 — éligible → `is_eligible=True, reason_code="eligible"`, déterminisme NFR1 | IMPLEMENTED |
| #2 — exclusion scope → `excluded_*` (3 sources + rétro-compat) | IMPLEMENTED |
| #3 — désactivé → `disabled_eqlogic` | IMPLEMENTED |
| #4 — sans commandes → `no_commands` | IMPLEMENTED |
| #5 — sans generic_type → `no_supported_generic_type`, distinction FR8 | IMPLEMENTED |
| #6 — suite isolée, nominal + échec par catégorie, NFR9 | IMPLEMENTED |

### Task Audit

Toutes les tasks [x] vérifiées : code correspond aux claims.

### Test Results

- 14/14 nouveaux tests PASS (0.01s)
- 304/304 total PASS (60.50s) — 0 régression
- NFR9 isolation : unique import = `models.topology`, 0 dépendance MQTT/asyncio/Jeedom
- 0 modification de code de production

### Findings

- **0 HIGH, 0 MEDIUM**
- **1 LOW (non bloquant, observation)** : 4 tests d'exclusion dupliquent fonctionnellement `test_exclusion_filtering.py:84-113` (Story 4.3). Overlap délibéré — couverture exhaustive par étape pipeline. À garder en tête si la taxonomie d'exclusion évolue (2 fichiers à maintenir).
