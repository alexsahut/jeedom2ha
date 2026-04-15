# Story 4.4 : Suite de tests de non-régression des 5 étapes — le mainteneur peut tester chaque étape du pipeline en isolation

Status: done

Epic: pe-epic-4 — Décision de publication explicite + contrat de testabilité/rétrocompatibilité garanti

Story Key (sprint-status): `4-4-suite-de-tests-de-non-regression-des-5-etapes-le-mainteneur-peut-tester-chaque-etape-du-pipeline-en-isolation`

## Story

En tant que mainteneur,  
je veux une suite de tests contractuels du pipeline canonique (étapes 1 à 4 + invariant transversal conceptuel sur l’étape 5),  
afin de détecter immédiatement toute dérive d’ordre d’évaluation, de cause canonique ou de règles de publication.

## Description

Cette story appartient au cycle **Moteur de Projection Explicable** et intervient après les stories 4.1, 4.2, 4.3 (toutes livrées).  
Elle documente une implémentation **déjà réalisée** sans fichier BMAD préalable, et rétablit la traçabilité de review.

Portée réelle implémentée :

- tests contractuels du pipeline, centrés sur les invariants critiques,
- exécution en isolation (sans MQTT, sans UI, sans runtime daemon),
- réutilisation des tests d’étapes existants,
- ajout d’un unique fichier transversal : `test_pipeline_invariants.py`.

Source canonique utilisée :

- `_bmad-output/planning-artifacts/pipeline-contract.md` (V2).

## Acceptance Criteria

1. **Given** le contrat pipeline V2  
   **When** la suite des invariants est exécutée  
   **Then** les invariants I1, I2, I3, I4, I5, I6, I7 sont couverts par des tests explicites.

2. **Given** l’ordre canonique des causes  
   **When** un cas `ambiguous + out_of_scope` est évalué  
   **Then** la cause retenue reste l’étape 2 (`ambiguous_skipped`) et n’est pas écrasée par l’étape 4.

3. **Given** une projection invalide (`is_valid=False`)  
   **When** la décision de publication est évaluée  
   **Then** `should_publish=False` est garanti (I2), quel que soit le reason_code d’invalidité.

4. **Given** un cas `invalid_projection + out_of_scope`  
   **When** la décision est évaluée  
   **Then** la cause retenue reste celle de l’étape 3 et n’est pas écrasée par l’étape 4.

5. **Given** les anti-contrats pipeline  
   **When** la suite est exécutée  
   **Then** elle interdit explicitement :
   - l’écrasement d’une cause amont,
   - le fallback silencieux,
   - un reason implicite/nul,
   - la publication sans validation.

6. **Given** la suite de tests pipeline (étapes + invariants)  
   **When** elle est exécutée  
   **Then** tous les tests passent sans modification de code de production.

7. **Given** la nature de cette story (tests uniquement)  
   **When** l’implémentation est auditée  
   **Then** aucun fichier de production n’a été modifié.

8. **Given** une décision produit calculée aux étapes 1–4  
   **When** un résultat technique d’étape 5 (ex: `discovery_publish_failed`) est enregistré  
   **Then** la cause décisionnelle (`PublicationDecision.reason`) reste inchangée et n’est jamais écrasée.

## Tasks / Subtasks

- [x] Task 1 — Auditer la base de tests existante par étape (1 à 4) et le contrat pipeline
  - [x] Vérification des fichiers `test_step1_eligibility.py`, `test_step2_mapping_candidat.py`, `test_step2_mapping_failure.py`, `test_step3_validate_projection.py`, `test_step4_decide_publication.py`, `test_pipeline_contract.py`
  - [x] Validation que la convention de naming existante est conservée

- [x] Task 2 — Ajouter la couche transversale d’invariants (Option A)
  - [x] Création du fichier `resources/daemon/tests/unit/test_pipeline_invariants.py`
  - [x] Implémentation prioritaire des 3 cas structurants demandés :
    - [x] I4 `ambiguous + out_of_scope`
    - [x] I2 `invalid_projection -> never publish`
    - [x] I4 `invalid_projection + out_of_scope`

- [x] Task 3 — Compléter les invariants/anti-contrats restants
  - [x] I1, I3, I5, I6, I7 (I7 traité par verrou explicite de non-écrasement)
  - [x] Anti-contrats : no overwrite amont, no silent fallback, no implicit reason, no publish without validation

- [x] Task 4 — Exécuter les validations pytest
  - [x] `python3 -m pytest resources/daemon/tests/unit/test_pipeline_invariants.py -q`
  - [x] `python3 -m pytest resources/daemon/tests/unit/test_step1_eligibility.py resources/daemon/tests/unit/test_step2_mapping_candidat.py resources/daemon/tests/unit/test_step2_mapping_failure.py resources/daemon/tests/unit/test_step3_validate_projection.py resources/daemon/tests/unit/test_step4_decide_publication.py resources/daemon/tests/unit/test_pipeline_contract.py -q`

- [x] Task 5 — Vérifier le périmètre story
  - [x] Confirmation : aucun changement de production
  - [x] Confirmation : aucun invariant n’a nécessité une correction fonctionnelle

## Dev Notes

### Stratégie retenue

**Option A** confirmée :

- conservation stricte des fichiers de tests par étape déjà présents,
- ajout d’un seul fichier transversal d’invariants.

### Convention de naming

Aucune dérive introduite :

- `test_step3_validate_projection.py` conservé,
- `test_step4_decide_publication.py` conservé,
- étape 2 conservée via `test_step2_mapping_candidat.py` + `test_step2_mapping_failure.py`,
- pas de création de `test_step2_mapping.py`.

### Implémentation réalisée

- ajout unique : `resources/daemon/tests/unit/test_pipeline_invariants.py`,
- fixtures/helpers locaux minimaux dans le fichier,
- aucun couplage MQTT/UI/runtime.

### Traitement de I7

I7 est couvert par un **test explicite de non-écrasement** :

- une cause technique étape 5 (ex: `discovery_publish_failed`) est enregistrée séparément,
- `PublicationDecision.reason` (cause décisionnelle étapes 1–4) reste immuable.

### Guardrail de gouvernance du contrat

Cette suite protège le **contrat du pipeline**, pas son implémentation.  
Toute évolution doit soit respecter ces tests, soit faire évoluer explicitement le contrat canonique (`pipeline-contract.md` V2).

### Clarification `reason_code` vs `reason`

Conformément au contrat :

- niveau conceptuel : `reason_code`,
- niveau technique code actuel : `PublicationDecision.reason`.

La suite documente explicitement que `decision.reason` porte le reason_code canonique de décision.

## Tests

### Fichiers existants réutilisés

- `resources/daemon/tests/unit/test_step1_eligibility.py`
- `resources/daemon/tests/unit/test_step2_mapping_candidat.py`
- `resources/daemon/tests/unit/test_step2_mapping_failure.py`
- `resources/daemon/tests/unit/test_step3_validate_projection.py`
- `resources/daemon/tests/unit/test_step4_decide_publication.py`
- `resources/daemon/tests/unit/test_pipeline_contract.py`

### Fichier ajouté

- `resources/daemon/tests/unit/test_pipeline_invariants.py`

### Logique de test

- priorisation des cas d’ordre canonique (I4/I2/I4),
- verrouillage des invariants structurants (I1, I3, I5, I6, I7),
- anti-contrats explicites,
- exécution isolée du runtime.

## Dev Agent Record

### Agent Model Used

gpt-5 Codex

### Debug Log References

- `python3 -m pytest resources/daemon/tests/unit/test_pipeline_invariants.py -q`
- `python3 -m pytest resources/daemon/tests/unit/test_step1_eligibility.py resources/daemon/tests/unit/test_step2_mapping_candidat.py resources/daemon/tests/unit/test_step2_mapping_failure.py resources/daemon/tests/unit/test_step3_validate_projection.py resources/daemon/tests/unit/test_step4_decide_publication.py resources/daemon/tests/unit/test_pipeline_contract.py -q`

### Completion Notes List

- Story reconstituée a posteriori pour traçabilité BMAD (implémentation déjà faite).
- Cas critiques implémentés en priorité :
  - `test_i4_ambiguous_plus_out_of_scope_keeps_step2_cause`
  - `test_i2_invalid_projection_never_publishes`
  - `test_i4_invalid_projection_plus_out_of_scope_keeps_step3_cause`
- Invariants couverts : I1, I2, I3, I4, I5, I6, I7.
- Anti-contrats couverts :
  - pas d’écrasement amont,
  - pas de fallback silencieux,
  - pas de reason implicite,
  - pas de publication sans validation.
- Résultats réels :
  - suite invariants : **10 passed**
  - suite pipeline ciblée : **76 passed**
- Confirmation explicite :
  - aucun changement de prod,
  - aucun invariant n’a requis une modification fonctionnelle.

### File List

- `_bmad-output/implementation-artifacts/stories/4-4-suite-de-tests-de-non-regression-des-5-etapes-le-mainteneur-peut-tester-chaque-etape-du-pipeline-en-isolation.md` (créé)
- `resources/daemon/tests/unit/test_pipeline_invariants.py` (déjà créé lors de l’implémentation story)
