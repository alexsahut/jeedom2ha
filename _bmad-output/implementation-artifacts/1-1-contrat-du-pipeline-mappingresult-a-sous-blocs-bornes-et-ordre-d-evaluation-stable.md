# Story 1.1 : Contrat du pipeline — MappingResult à sous-blocs bornés et ordre d'évaluation stable

Status: done

## Story

En tant que mainteneur,
je veux que le `MappingResult` contienne trois sous-blocs strictement bornés (`mapping`, `projection_validity`, `publication_decision`) évalués dans un ordre stable et fixe,
afin que chaque étape soit développable et testable en isolation et que le diagnostic reçoive toujours une trace complète et non ambiguë.

## Acceptance Criteria

1. **Given** le type `MappingResult` est défini
   **When** un équipement traverse le pipeline
   **Then** le `MappingResult` contient toujours les trois sous-blocs : `mapping` (champs existants de l'étape 2), `projection_validity` (étape 3), `publication_decision` (étape 4)
   **And** chaque sous-bloc est écrit exclusivement par l'étape correspondante — aucune autre étape ne le modifie
   **And** si une étape précédente a échoué, les sous-blocs suivants sont présents avec un statut explicite (`is_valid: None, reason_code: "skipped_no_mapping_candidate"`) — jamais absents

2. **Given** le pipeline évalue un équipement
   **When** une étape bloque l'évaluation
   **Then** le pipeline retient cette étape bloquante comme cause principale canonique
   **And** l'évaluation s'arrête à cette étape mais les sous-blocs suivants sont remplis avec un statut skipped explicite — pas de trou implicite dans le diagnostic (AR2)

3. **Given** un jeu de test pour le contrat du pipeline
   **When** le test exécute la fonction `assess_eligibility()` deux fois avec des entrées identiques
   **Then** la sortie (`EligibilityResult`, `is_eligible`, `reason_code`) est identique aux deux passages (NFR1 — déterminisme)

## Tasks / Subtasks

- [x] Task 1 — Définir le type `MappingCapabilities` dans `models/mapping.py` (AC: #1)
  - [x] Ajouter après les imports : `MappingCapabilities = Union[LightCapabilities, CoverCapabilities, SwitchCapabilities]`
  - [x] Ce type est le contrat d'entrée de `validate_projection()` définie en Epic 3 — le définir ici comme point d'ancrage du contrat

- [x] Task 2 — Définir le dataclass `ProjectionValidity` dans `models/mapping.py` (AC: #1, #2)
  - [x] Ajouter un dataclass `ProjectionValidity` entre `SwitchCapabilities` et `MappingResult` avec : `is_valid: Optional[bool]`, `reason_code: Optional[str]`, `missing_fields: List[str]`, `missing_capabilities: List[str]`
  - [x] Sémantique : `is_valid=None` = sous-bloc skipped (étape 3 non exécutée) ; `is_valid=True/False` = résultat de validation effective

- [x] Task 3 — Étendre `MappingResult` avec les deux nouveaux sous-blocs (AC: #1, #2)
  - [x] Ajouter `projection_validity: Optional[ProjectionValidity] = None` dans `MappingResult` APRÈS les champs existants
  - [x] Ajouter `publication_decision_ref: Optional["PublicationDecision"] = None` dans `MappingResult` APRÈS les champs existants (nommer avec `_ref` pour éviter la collision de nom avec le champ existant de `PublicationDecision`)
  - [x] Ne PAS modifier `__post_init__` — ces champs restent `None` jusqu'au câblage effectif en Epic 5
  - [x] Les champs existants de `MappingResult` (`ha_entity_type`, `confidence`, `reason_code`, `capabilities`, `commands`, etc.) constituent le sous-bloc `mapping` (étape 2) — pas de modification

- [x] Task 4 — Écrire les tests du contrat du pipeline (AC: #1, #2, #3)
  - [x] Créer `resources/daemon/tests/unit/test_pipeline_contract.py`
  - [x] Test structurel : vérifier que `MappingResult` possède les attributs `projection_validity` et `publication_decision_ref` (isinstance + hasattr)
  - [x] Test type `ProjectionValidity` — cas nominal : `is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[]`
  - [x] Test type `ProjectionValidity` — cas skip : `is_valid=None, reason_code="skipped_no_mapping_candidate", missing_fields=[], missing_capabilities=[]`
  - [x] Test type `ProjectionValidity` — cas invalide : `is_valid=False, reason_code="ha_missing_command_topic", missing_fields=["command_topic"], missing_capabilities=["has_command"]`
  - [x] Test trace complète (AR2) : construire un `MappingResult` complet avec les 3 sous-blocs renseignés → vérifier qu'aucun champ attendu n'est absent
  - [x] Test déterminisme (NFR1) : appeler `assess_eligibility()` deux fois avec le même `JeedomEqLogic` → `EligibilityResult` identique (même `is_eligible`, même `reason_code`, même `confidence`)

- [x] Task 5 — Vérifier la non-régression
  - [x] Lancer `pytest resources/daemon/tests/` depuis `resources/daemon/` : tous les tests existants PASS (les nouveaux champs sont optionnels, les instanciations existantes non modifiées)

## Dev Notes

### Contrat de données du pipeline — vue d'ensemble

**Trois sous-blocs du `MappingResult` après cette story (D1) :**

| Sous-bloc | Champs portés | Étape pipeline | Statut si upstream échoue |
|---|---|---|---|
| `mapping` | `ha_entity_type`, `confidence`, `reason_code`, `capabilities`, `commands` | 2 — Mapping candidat | *équipement non passé dans le mapping* |
| `projection_validity` | `is_valid`, `reason_code`, `missing_fields`, `missing_capabilities` | 3 — Validation HA (Epic 3) | `is_valid=None`, `reason_code="skipped_no_mapping_candidate"` |
| `publication_decision_ref` | `should_publish`, `reason`, `active_or_alive`, `discovery_published` | 4 — Décision publication (Epic 4) | `should_publish=False`, `reason="no_mapping"` |

**État après Story 1.1 :** types définis, champs ajoutés dans `MappingResult` avec default=None. Le pipeline en production n'est PAS encore câblé — les deux nouveaux champs valent `None` sur toutes les instances existantes. Le câblage effectif du sync handler est en Epic 5 (Story 5.1).

### Fichier à modifier — `resources/daemon/models/mapping.py`

C'est le **seul fichier à modifier** dans cette story. Voici l'ordre d'insertion :

1. **`MappingCapabilities`** — type alias après les imports existants (avant les dataclasses) :
   ```python
   MappingCapabilities = Union[LightCapabilities, CoverCapabilities, SwitchCapabilities]
   ```

2. **`ProjectionValidity`** — nouveau dataclass à insérer entre `SwitchCapabilities` et `MappingResult` :
   ```python
   @dataclass
   class ProjectionValidity:
       is_valid: Optional[bool]           # True/False/None (None = skipped)
       reason_code: Optional[str]         # None si valide
       missing_fields: List[str]          # champs HA requis non satisfaits
       missing_capabilities: List[str]    # capabilities moteur absentes
   ```

3. **Extension `MappingResult`** — deux champs à ajouter en fin de la classe (APRÈS `reason_details`) :
   ```python
   projection_validity: Optional[ProjectionValidity] = None
   publication_decision_ref: Optional["PublicationDecision"] = None
   ```
   **Important :** Ces champs ont `default=None`. La validation dans `__post_init__` ne doit PAS les vérifier — ils restent optionnels jusqu'à l'orchestration complète en Epic 5.

4. **Imports à compléter** — vérifier que `List` et `Optional` sont bien importés depuis `typing`. Ils le sont déjà dans le fichier existant.

### Sentinel skip canonique (P3)

Le `reason_code` de pipeline skip est `"skipped_no_mapping_candidate"`. Préfixe `skipped_` per P3 (classe skip transverse). Ce code n'est PAS à ajouter à `cause_mapping.py` dans cette story — c'est la migration D5, portée par Epic 4.

### Forward reference et `from __future__ import annotations`

Le fichier `models/mapping.py` contient déjà `from __future__ import annotations` (ligne 7). Avec cette import, TOUTES les annotations sont automatiquement des chaînes différées — les forward refs fonctionnent nativement. L'annotation `Optional["PublicationDecision"]` peut même s'écrire `Optional[PublicationDecision]` sans guillemets supplémentaires, puisque `from __future__ import annotations` gère la résolution.

### MappingCapabilities vs capabilities concrètes

`MappingCapabilities = Union[LightCapabilities, CoverCapabilities, SwitchCapabilities]` est un **type alias**, pas un nouveau dataclass. Le champ `capabilities` existant dans `MappingResult` est déjà typé `Optional[Union[LightCapabilities, CoverCapabilities, "SwitchCapabilities"]]` — le type alias rend ce type expressément nommé pour `validate_projection()` et les stories Epic 3.

### Dev Agent Guardrails

- **`transport/http_server.py` — NE PAS TOUCHER** — le câblage du sync handler est Epic 5 (Story 5.1). La `_do_handle_action_sync` continue de fonctionner comme aujourd'hui.
- **`models/cause_mapping.py` — NE PAS TOUCHER** — l'ajout des nouveaux `reason_code` (`ha_missing_*`, `skipped_*`) est la migration D5 portée par Epic 4.
- **`validation/` — NE PAS CRÉER** — le module de validation est créé en Epic 3.
- **`PublicationDecision` — NE PAS MODIFIER** — la suppression future du champ `mapping_result` (back-reference) est une décision de refactoring Epic 5, pas de cette story.
- **`__post_init__` de `MappingResult`** — laisser intact. Ne pas ajouter de validation sur `projection_validity` ou `publication_decision_ref`.
- **Portée stricte :** uniquement `models/mapping.py` modifié + `tests/unit/test_pipeline_contract.py` créé.

### Patterns de test à suivre

Les tests existants (ex: `test_ui_contract_4d.py`, `test_cause_mapping.py`) sont des modules pytest purs, sans fixtures complexes. Reproduire le même style :
- Pas de `conftest.py` — utiliser des helpers locaux au fichier
- Nommage `test_<sujet>_<scenario>()` clair et descriptif
- Import direct depuis les modules sous test (`from models.mapping import MappingResult, ProjectionValidity, ...`)

Exemple de structure pour `test_pipeline_contract.py` :
```python
"""Tests du contrat de pipeline — Story 1.1.

Vérifie la structure MappingResult à 3 sous-blocs, les types ProjectionValidity
et MappingCapabilities, et le déterminisme de assess_eligibility() (NFR1).
"""
from models.mapping import (
    MappingResult, ProjectionValidity, MappingCapabilities,
    LightCapabilities, CoverCapabilities, SwitchCapabilities,
)
from models.topology import JeedomEqLogic, JeedomCmd, assess_eligibility
```

### Project Structure Notes

**Fichier modifié :** `resources/daemon/models/mapping.py`

**Fichier créé :** `resources/daemon/tests/unit/test_pipeline_contract.py`

Aucun autre fichier — scope strictement limité à la définition du contrat de données.

La table `mapping pipeline → code` de l'architecture (§ Structure projet — delta) référence `models/mapping.py` pour D1 — c'est exactement ce que cette story livre.

### References

- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §D1] — Sous-blocs bornés + tableau sous-blocs
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §D4] — Signature `validate_projection` + `ProjectionValidity` + `MappingCapabilities`
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §P1] — Traversée complète + invariant trace sans trou
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §P2] — Isolation des sous-blocs (lecture seule sur blocs précédents)
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §P3] — Nommage reason_codes (`skipped_*` préfixe pipeline skip)
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` §Structure projet] — Table pipeline → code
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` §Story 1.1] — User story, AC, dev notes canoniques
- [Source: `resources/daemon/models/mapping.py`] — Structure actuelle de `MappingResult` et `PublicationDecision`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

Aucun — implémentation directe sans blocage.

### Completion Notes List

- Task 1 : `MappingCapabilities = Union[LightCapabilities, CoverCapabilities, SwitchCapabilities]` ajouté après les dataclasses de capabilities dans `models/mapping.py`. Import `List` ajouté dans `from typing`.
- Task 2 : dataclass `ProjectionValidity` (4 champs : `is_valid`, `reason_code`, `missing_fields`, `missing_capabilities`) inséré entre `SwitchCapabilities` et `MappingResult`.
- Task 3 : `MappingResult` étendu de `projection_validity: Optional[ProjectionValidity] = None` et `publication_decision_ref: Optional["PublicationDecision"] = None`. `__post_init__` non modifié. Pipeline en production inchangé (champs optionnels).
- Task 4 : 11 tests dans `test_pipeline_contract.py` — 3 cas `ProjectionValidity`, type alias `MappingCapabilities`, 2 champs struct, trace complète AR2, 3 variantes déterminisme NFR1. 11/11 PASS.
- Task 5 : 290/290 PASS — zéro régression.

### File List

- `resources/daemon/models/mapping.py` — modifié (T1, T2, T3)
- `resources/daemon/tests/unit/test_pipeline_contract.py` — créé (T4)

## Change Log

- 2026-04-10 : Story 1.1 implémentée — `MappingCapabilities`, `ProjectionValidity` et deux sous-blocs optionnels dans `MappingResult`. 11 tests pipeline contract ajoutés. 290/290 PASS.
