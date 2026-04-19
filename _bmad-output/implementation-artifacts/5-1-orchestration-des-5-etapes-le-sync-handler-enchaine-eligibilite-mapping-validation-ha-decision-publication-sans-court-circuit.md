# Story 5.1 : Orchestration des 5 étapes — le sync handler enchaîne éligibilité → mapping → validation HA → décision → publication sans court-circuit

Status: review

## Story

En tant qu'utilisateur,  
je veux que l'opération de synchronisation exécute les cinq étapes du pipeline en séquence pour chaque équipement éligible, avec `validate_projection()` appelée entre le mapping et `decide_publication()`,  
afin de garantir qu'aucune publication MQTT ne contourne la validation structurelle HA.

## Acceptance Criteria

1. **Given** un équipement éligible avec mapping valide et projection HA valide  
   **When** le sync handler s'exécute  
   **Then** les 5 étapes sont exécutées dans l'ordre canonique  
   **And** l'équipement est publié vers Home Assistant.

2. **Given** un équipement pour lequel `validate_projection()` retourne `is_valid=False`  
   **When** le sync handler s'exécute  
   **Then** `decide_publication()` est quand même appelée (aucun court-circuit)  
   **And** `should_publish=False`  
   **And** aucune publication MQTT n'est effectuée.

3. **Given** un équipement éligible traité par la sync  
   **When** le pipeline termine  
   **Then** le `MappingResult` contient toujours les 3 sous-blocs canoniques (`mapping`, `projection_validity`, `publication_decision`)  
   **And** dans l'implémentation actuelle, le sous-bloc canonique `publication_decision` est porté par le champ `publication_decision_ref`  
   **And** aucun trou implicite n'est introduit.

4. **Given** un cas d'intégration `light` sans commande action mappable  
   **When** la sync s'exécute  
   **Then** `projection_validity.reason_code="ha_missing_command_topic"`  
   **And** `publication_decision.should_publish=False`.

5. **Given** la suite de tests story + non-régression  
   **When** elle est exécutée  
   **Then** les tests unitaires/integration de l'orchestration passent  
   **And** il n'y a pas de régression sur les invariants pipeline existants.

6. **Given** un arbitrage de non-ouverture composant utilisé dans les tests/story notes (ex: `sensor`)  
   **When** il est référencé  
   **Then** l'arbitrage cite explicitement un ID `GOV-PE5-xxx` actif (micro-protocole opposable).

## Tasks / Subtasks

- [x] Task 0 — Pré-flight gouvernance et préséance documentaire (AC: #6)
  - [x] 0.1 — Vérifier la préséance documentaire active (`pe-epic-5-document-precedence.md`) pour FR39/FR40 et lecture `governed-open`.
  - [x] 0.2 — Vérifier le registre d'exceptions actif (`pe-epic-5-governance-exceptions-register.md`).
  - [x] 0.3 — Si un cas de non-ouverture est utilisé, tracer l'ID GOV explicite dans le record story/PR.

- [x] Task 1 — Implémenter l'orchestration canonique 5 étapes dans le sync handler (AC: #1, #2)
  - [x] 1.1 — Dans `resources/daemon/transport/http_server.py`, enchaîner explicitement : éligibilité → mapping → `validate_projection()` → `decide_publication()` → publication.
  - [x] 1.2 — Garantir l'appel de `decide_publication()` même quand `projection_validity.is_valid=False`.
  - [x] 1.3 — Interdire tout court-circuit qui sauterait l'étape 4 pour un équipement éligible.

- [x] Task 2 — Garantir la complétude traceability du `MappingResult` (AC: #3)
  - [x] 2.1 — Vérifier que les sous-blocs `mapping`, `projection_validity`, `publication_decision` sont toujours présents pour tout équipement éligible traité (`publication_decision` étant porté par `publication_decision_ref` côté implémentation).
  - [x] 2.2 — Conserver les statuts explicites de skip lorsque nécessaire, sans champ implicite absent.

- [x] Task 3 — Ajouter les tests d'orchestration story 5.1 (AC: #1, #2, #3, #4)
  - [x] 3.1 — Créer une suite dédiée (suggestion: `resources/daemon/tests/unit/test_pe_epic5_story_5_1_orchestration.py`).
  - [x] 3.2 — Tester le chemin nominal 5 étapes complet.
  - [x] 3.3 — Tester le chemin invalidité HA (`is_valid=False`) avec appel obligatoire de `decide_publication()`.
  - [x] 3.4 — Tester le cas `ha_missing_command_topic` et absence de publication.
  - [x] 3.5 — Vérifier la présence des 3 sous-blocs canoniques dans les résultats.

- [x] Task 4 — Non-régression et vérification finale (AC: #5)
  - [x] 4.1 — Exécuter les tests story 5.1.
  - [x] 4.2 — Exécuter la non-régression pipeline (`test_pipeline_contract.py`, `test_pipeline_invariants.py`).
  - [x] 4.3 — Vérifier absence de régression sur les stories pe-epic-3 / pe-epic-4.

- [x] Task 5 — Mises à jour de traçabilité livraison
  - [x] 5.1 — Compléter `Dev Agent Record` (logs, notes, fichiers modifiés).
  - [x] 5.2 — Passage en `review` effectué, puis synchronisation `sprint-status.yaml` vers `done` exécutée lors du closeout post-review.

## Dev Notes

### Contrat d'orchestration à respecter

- Ordre canonique strict: Étape 1 → Étape 2 → Étape 3 → Étape 4 → Étape 5.
- L'étape 3 (`validate_projection`) décide la validité structurelle HA.
- L'étape 4 (`decide_publication`) arbitre la publication (policy + gouvernance), sans revalider HA.
- Le `MappingResult` porte 3 sous-blocs canoniques (`mapping`, `projection_validity`, `publication_decision`) même si le pipeline comporte 5 étapes.
- Clarification contractuelle closeout : dans cette implémentation, le sous-bloc canonique `publication_decision` est matérialisé par `mapping.publication_decision_ref` (alias de contrat, sans impact fonctionnel).

### Dev Agent Guardrails

- Ne pas réouvrir le fond de pe-epic-4.
- Ne pas fusionner décision produit et résultat technique de publication (la séparation détaillée sera consolidée en story 5.2).
- Ne pas introduire de non-ouverture implicite "hors scope" dans les tests/commentaires.
- Toute non-ouverture mentionnée doit référencer un ID `GOV-PE5-xxx` actif.

### Références GOV explicites (si utilisées en arbitrage)

- `sensor` → `GOV-PE5-001`
- `binary_sensor` → `GOV-PE5-002`
- `button` → `GOV-PE5-003`
- `number` → `GOV-PE5-004`
- `select` → `GOV-PE5-005`
- `climate` → `GOV-PE5-006`

### Project Structure Notes

- Zone principale d'impact: `resources/daemon/transport/http_server.py`
- Fonctions/modules déjà disponibles:
  - `resources/daemon/validation/ha_component_registry.py`
  - `resources/daemon/models/decide_publication.py`
  - `resources/daemon/models/mapping.py`
- Tests à étendre côté `resources/daemon/tests/unit/` (suite story dédiée recommandée).

### References

- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` — Epic 5, Story 5.1]
- [Source: `_bmad-output/planning-artifacts/pipeline-contract.md` — contrat global, invariants I2/I3/I4/I5]
- [Source: `_bmad-output/planning-artifacts/prd.md` — FR26..FR30, NFR2, NFR3]
- [Source: `_bmad-output/planning-artifacts/architecture-delta-review-prd-final.md` — lecture governed-open FR39/FR40]
- [Source: `_bmad-output/implementation-artifacts/pe-epic-5-governance-exceptions-register.md`]
- [Source: `_bmad-output/implementation-artifacts/pe-epic-5-document-precedence.md`]
- [Source: `_bmad-output/implementation-artifacts/pe-epic-5-gov-reference-micro-protocol.md`]
- [Source: `_bmad-output/implementation-artifacts/pe-epic-5-alignment-gate.md`]

## Dev Agent Record

### Agent Model Used

gpt-5-codex

### Implementation Plan

- Pré-flight gouvernance: validation de la préséance documentaire active, du registre d'exceptions actif et du micro-protocole GOV.
- Câblage runtime: injecter `validate_projection()` (étape 3) puis `decide_publication()` (étape 4) dans la boucle sync, sans court-circuit pour un équipement éligible mappé.
- Traceabilité canonique: renseigner systématiquement `mapping.projection_validity` et `mapping.publication_decision_ref` avant toute tentative de publication MQTT.
- Vérification: ajouter une suite dédiée Story 5.1, puis exécuter tests story, non-régression pipeline et suite globale.

### Debug Log References

- Pré-flight GOV exécuté sur:
  - `_bmad-output/implementation-artifacts/pe-epic-5-document-precedence.md`
  - `_bmad-output/implementation-artifacts/pe-epic-5-governance-exceptions-register.md`
  - `_bmad-output/implementation-artifacts/pe-epic-5-gov-reference-micro-protocol.md`
  - `_bmad-output/implementation-artifacts/pe-epic-5-alignment-gate.md`
- Commandes de validation exécutées:
  - `python3 -m pytest resources/daemon/tests/unit/test_pe_epic5_story_5_1_orchestration.py resources/daemon/tests/unit/test_pipeline_contract.py resources/daemon/tests/unit/test_pipeline_invariants.py resources/daemon/tests/unit/test_step3_validate_projection.py resources/daemon/tests/unit/test_step4_decide_publication.py`
  - `python3 -m pytest`

### Completion Notes List

- Orchestration sync alignée au pipeline canonique 5 étapes: éligibilité → mapping → validation HA → décision → publication.
- `validate_projection()` est appelée systématiquement pour chaque mapping éligible traité, avant la décision.
- `decide_publication()` est appelée systématiquement même quand `projection_validity.is_valid=False`.
- La publication MQTT reste conditionnée strictement par `decision.should_publish`.
- `MappingResult` conserve les 3 sous-blocs canoniques pour les équipements éligibles mappés:
  - `mapping` (bloc principal)
  - `projection_validity`
  - `publication_decision` (via `publication_decision_ref`)
- Cas `light` sans commande action mappable vérifié: `projection_validity.reason_code="ha_missing_command_topic"` et `publication_decision.should_publish=False`.
- Aucune nouvelle règle produit implicite introduite; aucune ouverture de composant hors périmètre Story 5.1.
- Story validée par tests ciblés et non-régression globale (953 tests passants).
- Closeout post-review appliqué: ambiguïté `publication_decision` / `publication_decision_ref` levée au niveau documentaire, sans changement runtime.

### File List

- `_bmad-output/implementation-artifacts/5-1-orchestration-des-5-etapes-le-sync-handler-enchaine-eligibilite-mapping-validation-ha-decision-publication-sans-court-circuit.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/tests/unit/test_pe_epic5_story_5_1_orchestration.py`

## Change Log

- 2026-04-16: Implémentation Story 5.1 réalisée (orchestration canonique 5 étapes, tests dédiés, non-régression complète), statut passé à `review`.
- 2026-04-16: Closeout documentaire post-review (clarification alias contractuel `publication_decision` ↔ `publication_decision_ref`, tâche 5.2 réalignée), statut passé à `done`.
