# Story 1.3 : Diagnostic d'éligibilité — l'utilisateur lit l'étape 1 comme point de blocage avec cause catégorisée et action de scope applicable

Status: done

## Story

En tant qu'utilisateur,
je veux voir, pour tout équipement bloqué à l'étape 1, l'étape de blocage explicitement identifiée et le motif d'exclusion canonique, avec une action de scope proposée lorsque mes propres réglages en sont la cause,
afin de pouvoir agir directement sur le bon levier sans avoir à deviner pourquoi l'équipement est absent de Home Assistant.

## Acceptance Criteria

1. **Given** un équipement inéligible à cause d'une exclusion de scope utilisateur (`excluded_eqlogic`, `excluded_plugin` ou `excluded_object`)
   **When** le diagnostic est consulté
   **Then** `reason_code_to_cause()` retourne un `cause_code` de forme `excluded_*` correspondant au type d'exclusion
   **And** un `cause_action` non-`None` est fourni pointant vers le réglage de scope concerné (FR10)
   **And** chaque code d'exclusion produit un `cause_code`, un `cause_label` et un `cause_action` distincts

2. **Given** un équipement inéligible avec `reason_code="disabled_eqlogic"`
   **When** le diagnostic est consulté
   **Then** `reason_code_to_cause()` retourne `cause_label="Équipement désactivé dans Jeedom"`
   **And** `cause_action="Activer l'équipement dans sa page de configuration Jeedom"` (entrée existante — vérifiée sans modification)

3. **Given** 100 % des équipements du corpus de test passés dans le pipeline
   **When** le diagnostic est consulté
   **Then** chaque équipement dispose d'un résultat de pipeline explicite — soit `EligibilityResult.is_eligible=False` (bloqué étape 1), soit un `MappingResult` non-`None` (atteint étape 2+)
   **And** aucun équipement ne produit un diagnostic vide ou ambigu (NFR3)
   **And** pour tout `reason_code` de l'étape 1, `reason_code_to_cause()` retourne un tuple non-vide (`cause_code`, `cause_label`) — les deux premiers champs sont toujours renseignés

4. **Given** la suite de tests vérifiant FR4
   **When** les tests s'exécutent
   **Then** le type `MappingResult` possède le champ `pipeline_step_reached: Optional[int]` (fondation FR4 — câblage effectif en Epic 5)
   **And** `EligibilityResult.is_eligible=False` permet d'inférer sans ambiguïté que l'étape bloquante est l'étape 1 — vérifiable en isolation sans MappingResult

## Tasks / Subtasks

- [x] Task 1 — Ajouter les entrées `excluded_*` dans `cause_mapping.py` (AC: #1)
  - [x] Ajouter `"excluded_eqlogic"` → `("excluded_eqlogic", "Équipement exclu du scope de synchronisation", "Retirer l'équipement de la liste d'exclusion dans les réglages jeedom2ha")`
  - [x] Ajouter `"excluded_plugin"` → `("excluded_plugin", "Plugin exclu du scope de synchronisation", "Retirer le plugin de la liste d'exclusion dans les réglages jeedom2ha")`
  - [x] Ajouter `"excluded_object"` → `("excluded_object", "Objet Jeedom exclu du scope de synchronisation", "Retirer l'objet de la liste d'exclusion dans les réglages jeedom2ha")`
  - [x] Insérer ces 3 entrées dans la section `# 15 entrées actives (direction 1)` de `_REASON_CODE_TO_CAUSE`, en tête (ordre canonique éligibilité : exclu > désactivé > ...)
  - [x] Mettre à jour le commentaire d'entête du module (compte des entrées actives : 12 → 15)

- [x] Task 2 — Ancrer `pipeline_step_reached` dans `MappingResult` (AC: #4)
  - [x] Dans `models/mapping.py`, ajouter `pipeline_step_reached: Optional[int] = None` à la fin de `MappingResult`, après `publication_decision_ref`
  - [x] Ne PAS modifier `__post_init__` — champ optionnel, câblage effectif en Epic 5 (Story 5.1)
  - [x] Sémantique documentée en commentaire inline : `# 2=mapping atteint ; 3=validation HA ; 4=décision publication ; 5=publié. None = non câblé (avant Epic 5)`

- [x] Task 3 — Créer `resources/daemon/tests/unit/test_step1_diagnostic.py` (AC: #1, #2, #3, #4)
  - [x] **AC1 — cause_mapping excluded_*** :
    - [x] `test_excluded_eqlogic_cause` : `reason_code_to_cause("excluded_eqlogic")` → `("excluded_eqlogic", "Équipement exclu du scope de synchronisation", "Retirer l'équipement...")`
    - [x] `test_excluded_plugin_cause` : `reason_code_to_cause("excluded_plugin")` → cause distincte avec cause_action non-None
    - [x] `test_excluded_object_cause` : `reason_code_to_cause("excluded_object")` → cause distincte avec cause_action non-None
    - [x] `test_excluded_codes_have_distinct_causes` : les 3 codes produisent des `cause_code` distincts
  - [x] **AC2 — vérification disabled_eqlogic dans le contexte step 1** :
    - [x] `test_disabled_eqlogic_cause_in_step1_context` : `reason_code_to_cause("disabled_eqlogic")` → `cause_label="Équipement désactivé dans Jeedom"`, `cause_action` non-None
  - [x] **AC3 + FR10 — couverture complète et cause_action FR10** :
    - [x] `test_all_step1_reason_codes_produce_explicit_cause` : boucler sur les 6 reason_codes de l'étape 1 et vérifier que `cause_code` et `cause_label` sont non-None pour tous
    - [x] `test_fr10_excluded_codes_have_cause_action` : les 3 codes `excluded_*` retournent un `cause_action` non-None (exclusion = choix utilisateur)
    - [x] `test_fr10_no_supported_generic_type_has_no_cause_action` : `reason_code_to_cause("no_supported_generic_type")` retourne `cause_action=None` (limitation plateforme, pas de choix utilisateur)
    - [x] `test_nfr3_ineligible_result_is_explicit` : `EligibilityResult(is_eligible=False, reason_code="excluded_eqlogic")` produit un résultat diagnostiquable sans ambiguïté — pas besoin de MappingResult
  - [x] **AC4 — fondation FR4** :
    - [x] `test_fr4_mapping_result_has_pipeline_step_field` : `MappingResult` possède le champ `pipeline_step_reached` (hasattr + isinstance check)
    - [x] `test_fr4_pipeline_step_none_before_wiring` : un `MappingResult` construit normalement (Epic 1-2 context) a `pipeline_step_reached=None` avant le câblage Epic 5
    - [x] `test_fr4_step1_blocker_inferred_without_mapping_result` : un `EligibilityResult(is_eligible=False)` + absence de MappingResult → inférence étape 1 sans ambiguïté

- [x] Task 4 — Vérifier la non-régression
  - [x] Lancer `pytest resources/daemon/tests/` depuis `resources/daemon/` : 316/316 PASS (ajouts additifs — aucune modification de contrat existant)

## Dev Notes

### Contexte de la story dans le pipeline

L'étape 1 — Éligibilité est posée par Story 1.2 (`assess_eligibility()` complète et correcte). La Story 1.3 ajoute la **couche diagnostic** : comment `EligibilityResult.reason_code` se traduit en `(cause_code, cause_label, cause_action)` consommable par l'UI et le contrat 4D.

Ce n'est pas un câblage du pipeline — le pipeline complet est en Epic 5. C'est la fermeture du contrat diagnostic pour l'étape 1 : tout `reason_code` de l'étape 1 doit avoir une entrée complète dans `cause_mapping.py`.

### Gap identifié dans `cause_mapping.py` — les 3 `excluded_*` sont absents

Le fichier `resources/daemon/models/cause_mapping.py` contient 12 entrées actives (direction 1) depuis Story 4.1. Les 3 codes d'exclusion de scope — `excluded_eqlogic`, `excluded_plugin`, `excluded_object` — qui sont générés par `assess_eligibility()` dans `models/topology.py` sont **absents de la table**.

Conséquence actuelle : `reason_code_to_cause("excluded_eqlogic")` retourne le fallback `(None, None, None)`. Cela viole AC1 et NFR3 (un équipement exclu produit un diagnostic vide).

Cette story est le **trigger dédié** pour modifier `cause_mapping.py` (le commentaire "ARTEFACT FIGÉ — Story 4.1. Ne pas modifier sans story dédiée." est respecté — Story 1.3 est la story dédiée).

### Entrées à ajouter dans `_REASON_CODE_TO_CAUSE`

```python
# --- Exclusions de scope utilisateur (étape 1 — ordre canonique : exclu > désactivé > ...) ---
"excluded_eqlogic": (
    "excluded_eqlogic",
    "Équipement exclu du scope de synchronisation",
    "Retirer l'équipement de la liste d'exclusion dans les réglages jeedom2ha",
),
"excluded_plugin": (
    "excluded_plugin",
    "Plugin exclu du scope de synchronisation",
    "Retirer le plugin de la liste d'exclusion dans les réglages jeedom2ha",
),
"excluded_object": (
    "excluded_object",
    "Objet Jeedom exclu du scope de synchronisation",
    "Retirer l'objet de la liste d'exclusion dans les réglages jeedom2ha",
),
```

Ces 3 codes ont `cause_action` non-`None` car l'exclusion relève d'un **choix utilisateur** (scope settings jeedom2ha). C'est le contrat FR10.

### Taxonomie complète de l'étape 1 — état post-Story 1.3

| `reason_code` | `cause_code` | `cause_label` | `cause_action` | Déjà présent ? |
|---|---|---|---|---|
| `"excluded_eqlogic"` | `"excluded_eqlogic"` | "Équipement exclu du scope..." | non-None | **À ajouter** |
| `"excluded_plugin"` | `"excluded_plugin"` | "Plugin exclu du scope..." | non-None | **À ajouter** |
| `"excluded_object"` | `"excluded_object"` | "Objet Jeedom exclu du scope..." | non-None | **À ajouter** |
| `"disabled_eqlogic"` | `"disabled_eqlogic"` | "Équipement désactivé dans Jeedom" | non-None | ✓ existant |
| `"no_commands"` | `"no_commands"` | "Équipement sans commandes exploitables" | non-None | ✓ existant |
| `"no_supported_generic_type"` | `"no_supported_generic_type"` | "Type non supporté en V1" | `None` | ✓ existant (action None = FR10) |

**Note NFR8 :** aucun code existant n'est modifié ni renommé.

**Note Epic 4 :** ces chaînes de reason_code et cause_code sont des candidats à la centralisation dans un registre/enum en Epic 4 (D5 — migration additive). Ne pas créer de constantes centralisées ici.

### `pipeline_step_reached` dans `MappingResult` — fondation FR4

FR4 exige que chaque équipement puisse exposer l'étape la plus avancée atteinte dans le pipeline. Pour l'étape 1 (inéligible), l'étape bloquante est inférable de `EligibilityResult.is_eligible=False` — pas besoin d'un champ additionnel.

Pour l'étape 2+, le `MappingResult` doit porter `pipeline_step_reached`. On ancre le champ ici (Story 1.3) comme contrat de transport, même si le câblage effectif intervient en Epic 5 (Story 5.1) où le pipeline orchestre les 5 étapes.

```python
# Dans models/mapping.py, fin de MappingResult :
pipeline_step_reached: Optional[int] = None
# 2 = mapping atteint ; 3 = validation HA exécutée ; 4 = décision publication ;
# 5 = publié. None = champ non câblé (avant Epic 5).
```

**Invariant :** `MappingResult` est créé uniquement pour des équipements éligibles (step 1 pass). Sa seule existence indique `pipeline_step_reached >= 2`. La valeur `None` pré-Epic 5 est acceptable — le champ est le contrat, pas encore sa valeur.

### Pattern de test à suivre

```python
"""Tests du contrat de diagnostic étape 1 — Story 1.3.

Vérifie que reason_code_to_cause() couvre tous les reason_codes de l'étape 1,
que FR10 est respecté (cause_action présent/absent selon choix utilisateur),
et que la fondation FR4 (pipeline_step_reached) est ancrée dans MappingResult.
Tests exécutables en isolation totale (NFR9).
"""
from models.cause_mapping import reason_code_to_cause
from models.mapping import MappingResult, LightCapabilities
from models.topology import (
    JeedomCmd, JeedomEqLogic, EligibilityResult,
)

STEP1_REASON_CODES = [
    "excluded_eqlogic",
    "excluded_plugin",
    "excluded_object",
    "disabled_eqlogic",
    "no_commands",
    "no_supported_generic_type",
]

def _make_minimal_mapping_result() -> MappingResult:
    """Helper — MappingResult minimal valide pour tester les champs structurels."""
    cmd = JeedomCmd(id=1, name="On", generic_type="LIGHT_ON", type="action", sub_type="other")
    return MappingResult(
        ha_entity_type="light",
        confidence="sure",
        reason_code="sure",
        jeedom_eq_id=1,
        ha_unique_id="jeedom2ha_eq_1",
        ha_name="Test Light",
        capabilities=LightCapabilities(has_on_off=True),
        commands={"LIGHT_ON": cmd},
    )
```

- Pas de `conftest.py` — helpers locaux au fichier
- Aucune dépendance MQTT, pytest-asyncio, ou runtime Jeedom
- Import direct depuis `models.cause_mapping` et `models.mapping`

### Dev Agent Guardrails

- **`cause_mapping.py` — modifier avec la story dédiée uniquement** — Story 1.3 est cette story. Insérer les 3 entrées `excluded_*` dans la section existante, mettre à jour le commentaire de décompte. Aucune autre modification du fichier.
- **`models/topology.py` — NE PAS MODIFIER** — `assess_eligibility()` est complète et correcte depuis Story 1.2. Aucune modification requise pour cette story.
- **`models/mapping.py` — modification minimaliste** — uniquement le champ `pipeline_step_reached: Optional[int] = None` à la fin de `MappingResult`. Ne pas toucher à `__post_init__`, ne pas changer l'ordre des champs existants.
- **`test_cause_mapping.py` — NE PAS MODIFIER** — c'est l'artefact figé de Story 4.1. Les nouveaux tests pour `excluded_*` vivent dans `test_step1_diagnostic.py`.
- **Portée stricte** : 2 fichiers production modifiés (`cause_mapping.py`, `models/mapping.py`) + 1 fichier test créé (`test_step1_diagnostic.py`).
- **Pas de terrain** : story pure logique Python. Aucun test MQTT, daemon ou box réelle.
- **NFR8 : zéro renommage** — aucun `reason_code` existant n'est modifié.
- **Epic 4 candidate** : les nouvelles chaînes `excluded_eqlogic/plugin/object` dans `cause_mapping.py` sont candidates à la centralisation dans un enum/registre en Epic 4. Ne pas créer de constantes ici.

### Project Structure Notes

**Fichiers modifiés :**
- `resources/daemon/models/cause_mapping.py` — ajout 3 entrées (15 entrées actives au total)
- `resources/daemon/models/mapping.py` — ajout champ `pipeline_step_reached` dans `MappingResult`

**Fichier créé :**
- `resources/daemon/tests/unit/test_step1_diagnostic.py`

Table mapping pipeline → code (pour référence, non modifiée) :

| Étape pipeline | Module | Fonction principale |
|---|---|---|
| 1. Éligibilité | `models/topology.py` | `assess_all()` / `assess_eligibility()` |
| Diagnostic step 1 | `models/cause_mapping.py` | `reason_code_to_cause()` |

### References

- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §Story 1.3] — User story, AC, dev notes canoniques
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §FR4] — restitution étape la plus avancée dans MappingResult
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §FR10] — cause_action présent si et seulement si exclusion relève d'un choix utilisateur
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §NFR3] — 100% équipements avec résultat explicite
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §NFR8] — 0 reason_code renommé
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §D5] — migration reason_code additive, nouveaux codes s'ajoutent
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §Mapping pipeline → code] — étape 1 : `models/topology.py` ; diagnostic : `models/cause_mapping.py`
- [Source: `resources/daemon/models/cause_mapping.py`] — table `_REASON_CODE_TO_CAUSE` — 12 entrées actives existantes, à étendre à 15
- [Source: `resources/daemon/models/mapping.py`] — `MappingResult` dataclass — `pipeline_step_reached` à ajouter après `publication_decision_ref`
- [Source: `resources/daemon/models/topology.py:102`] — `EligibilityResult` dataclass
- [Source: `resources/daemon/tests/unit/test_cause_mapping.py`] — pattern de test pour `reason_code_to_cause()` (artefact Story 4.1 — ne pas modifier)
- [Source: `resources/daemon/tests/unit/test_step1_eligibility.py`] — pattern de test étape 1, helpers `_make_eq()`, `_cmd_with_generic()`
- [Source: `resources/daemon/models/ui_contract_4d.py`] — `_EXCLUSION_REASON_TO_PERIMETRE` confirme que `excluded_eqlogic/plugin/object` sont les 3 codes d'exclusion canoniques

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Task 1 : 3 entrées `excluded_eqlogic/plugin/object` insérées dans `_REASON_CODE_TO_CAUSE` en tête de la section direction 1 (ordre canonique exclu > désactivé). Compteur module 12 → 15. `cause_action` non-None sur les 3 (contrat FR10 — choix utilisateur).
- Task 2 : champ `pipeline_step_reached: Optional[int] = None` ajouté à la fin de `MappingResult` après `publication_decision_ref`. Commentaire inline sémantique (2=mapping ; 3=validation HA ; 4=décision ; 5=publié ; None=avant Epic 5). `__post_init__` non touché.
- Task 3 : `test_step1_diagnostic.py` créé — 12 tests couvrant AC1 (excluded_* cause_code/label/action distincts), AC2 (disabled_eqlogic existant), AC3+FR10 (couverture 6 codes étape 1, cause_action FR10), AC4 (pipeline_step_reached fondation). Cycle RED (9 échecs) → GREEN (12/12 PASS).
- Task 4 : suite complète 316/316 PASS — zéro régression. Ajouts strictement additifs, aucun code existant modifié.

### File List

- `resources/daemon/models/cause_mapping.py` — 3 entrées `excluded_*` ajoutées, compteur mis à jour 12→15
- `resources/daemon/models/mapping.py` — champ `pipeline_step_reached: Optional[int] = None` ajouté dans `MappingResult`
- `resources/daemon/tests/unit/test_step1_diagnostic.py` — créé (12 tests)

## Change Log

- 2026-04-11 : Implémentation Story 1.3 — ajout `excluded_eqlogic/plugin/object` dans `cause_mapping.py` (15 entrées actives), ancrage `pipeline_step_reached` dans `MappingResult`, création `test_step1_diagnostic.py` (12 tests, 316/316 non-régression).
