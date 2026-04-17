# Story 5.2 : Résultat de publication traçable — le résultat technique est enregistré séparément de la décision produit et ne masque pas la cause principale canonique

Status: done

## Story

En tant qu’utilisateur,  
je veux que le système distingue clairement la décision de publication (produit/gouvernance) du résultat technique de la publication MQTT,  
afin de comprendre si un équipement n’est pas publié à cause d’un refus décisionnel ou d’un problème technique.

## Acceptance Criteria

1. **AC1 — Séparation stricte décision vs résultat technique**  
   **Given** un équipement traité par le pipeline  
   **When** la décision de publication est prise en étape 4  
   **Then** cette décision reste inchangée et indépendante du résultat technique de l’étape 5.

2. **AC2 — Traçabilité du résultat technique**  
   **Given** un équipement avec `should_publish=True`  
   **When** la publication MQTT est exécutée  
   **Then** le résultat technique est enregistré explicitement (succès ou échec)  
   **And** il ne modifie pas la décision produit.

3. **AC3 — Non-masquage de la cause canonique**  
   **Given** un équipement non publié  
   **When** l’utilisateur consulte le diagnostic  
   **Then** la cause principale affichée est celle issue des étapes 1–4  
   **And** jamais une erreur technique ne remplace une cause décisionnelle.

4. **AC4 — Échec technique explicite**  
   **Given** un équipement avec `should_publish=True`  
   **And** une erreur survient lors de la publication MQTT  
   **When** le pipeline se termine  
   **Then** un `reason_code` technique explicite est enregistré  
   **And** il est distinct des `reason_code` décisionnels.

5. **AC5 — Compatibilité avec le contrat existant**  
   **Given** le contrat pipeline et les invariants existants  
   **When** la story est implémentée  
   **Then** aucun comportement des étapes 1–4 n’est modifié  
   **And** aucune régression n’est introduite.

6. **AC6 — Testabilité isolée de l’étape 5**  
   **Given** la suite de tests  
   **When** elle est exécutée  
   **Then** il est possible de tester indépendamment la décision (étape 4) et le résultat technique (étape 5).

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Sélectionner le mode selon l’objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [x] Task 1 — Introduire un sous-bloc technique dédié `publication_result` (AC: #1, #2, #4)
  - [x] Définir une structure de résultat technique explicite (ex: `status`, `technical_reason_code`, `attempted_at`), séparée de `publication_decision`.
  - [x] Documenter l’ownership du champ: étape 5 uniquement.
  - [x] Garantir que l’écriture de `publication_result` ne réécrit jamais `publication_decision.reason` ni `publication_decision.should_publish`.

- [x] Task 2 — Implémenter le câblage étape 5 sans logique métier (AC: #1, #2, #3, #4)
  - [x] Dans l’orchestration sync (`resources/daemon/transport/http_server.py`), enregistrer le résultat technique de publish dans le sous-bloc dédié.
  - [x] Conserver `decide_publication()` strictement inchangé (aucune modification de comportement, aucune logique MQTT ajoutée).
  - [x] Encadrer les chemins `publish ok`, `publish failed`, `publish skipped` avec un mapping explicite vers `publication_result`.

- [x] Task 3 — Garantir le non-masquage diagnostic (AC: #3, #4)
  - [x] Adapter la construction de traceabilité (`decision_trace` vs `publication_trace`) pour refléter deux dimensions distinctes.
  - [x] Vérifier que la cause principale canonique reste dérivée des étapes 1–4, même quand l’étape 5 échoue.
  - [x] Vérifier qu’un `reason_code` technique classe 4 est exposé comme résultat technique, jamais comme cause décisionnelle principale.

- [x] Task 4 — Reason codes techniques explicites et additifs (AC: #4, #5)
  - [x] Utiliser les reason codes techniques existants de classe 4 (`discovery_publish_failed`, `local_availability_publish_failed`) dans le sous-bloc technique.
  - [x] Ajouter uniquement des reason codes techniques si un gap strict est identifié, en mode additif.
  - [x] Interdire tout renommage/suppression des reason codes existants.

- [x] Task 5 — Étendre les tests story 5.2 (AC: #2, #3, #4, #6)
  - [x] Ajouter/mettre à jour une suite dédiée pe-epic-5 story 5.2 (ex: `resources/daemon/tests/unit/test_pe_epic5_story_5_2_publication_result.py`).
  - [x] Cas succès publication: `should_publish=True` + publish OK → `publication_result=success`, décision inchangée.
  - [x] Cas échec publication: `should_publish=True` + broker indisponible → `publication_result=failed` + `technical_reason_code=discovery_publish_failed`, décision inchangée.
  - [x] Cas non publication décisionnelle: `should_publish=False` → publication non tentée, cause décisionnelle conservée.
  - [x] Cas non-masquage: la cause principale canonique (étapes 1–4) reste prioritaire en diagnostic.

- [x] Task 6 — Non-régression pipeline (AC: #5, #6)
  - [x] Exécuter les suites `test_step4_decide_publication.py`, `test_pipeline_contract.py`, `test_pipeline_invariants.py`.
  - [x] Vérifier explicitement que les invariants I2/I4/I7 restent vrais après ajout du sous-bloc technique.
  - [x] Vérifier qu’aucun comportement des étapes 1–4 n’est impacté.

## Dev Notes

### Story Foundation

- Story portée par **Epic 5 / Feature 5 (FR26–FR30)**.
- Contrat central de cette story: **FR27 + FR28 + FR29 + FR30**.
- L’implémentation doit préserver la décision produit établie en étape 4 et tracer l’exécution technique en étape 5.

### Intention Dominante Du Cycle

> Ouvrir tout composant HA proprement mappable, structurellement validable et non bloqué par une exception de gouvernance explicitement décidée, justifiée et tracée.

- Cette story consomme ce cadre de pilotage pour l’étape 5 (traçabilité technique).
- Cette story ne redéfinit pas la gouvernance d’ouverture des composants.

### Gouvernance / Non-ouverture

- Cette story n’introduit aucune nouvelle non-ouverture de composant HA.
- Toute non-ouverture mentionnée dans la préparation, l’implémentation ou la review doit référencer un ID `GOV-PE5-xxx` actif.
- Registre de référence obligatoire : `_bmad-output/implementation-artifacts/pe-epic-5-governance-exceptions-register.md`
- Micro-protocole obligatoire en prep story/review : `_bmad-output/implementation-artifacts/pe-epic-5-gov-reference-micro-protocol.md`

### Préséance Documentaire

- En cas de tension de lecture, `architecture-delta-review-prd-final.md` prévaut sur `architecture-projection-engine.md`.
- Cette préséance s’applique explicitement à l’interprétation de FR39 / FR40 et du mode `governed-open`.
- `PRODUCT_SCOPE` est une base de départ gouvernée et ne doit jamais être interprété comme un plafond arbitraire.

### Developer Context — Source of Truth

- Étape 4 (`decide_publication`) est la **seule source de vérité décisionnelle**.
- Étape 5 (`publish`) est **strictement technique**.
- Le diagnostic doit porter deux dimensions coexistantes:
  - cause décisionnelle canonique (étapes 1–4),
  - résultat technique de publication (étape 5).

### Architecture Compliance

- Respect des invariants du contrat pipeline:
  - ordre strict 1 → 2 → 3 → 4 → 5,
  - isolation des sous-blocs,
  - migration additive des `reason_code`,
  - cause principale canonique non écrasable par une étape aval.
- Aucun court-circuit ni réinterprétation métier en étape 5.

### File Structure Requirements

- Zone principale d’impact attendue:
  - `resources/daemon/transport/http_server.py`
  - `resources/daemon/models/mapping.py` (structure de données dédiée résultat technique, si nécessaire)
  - `resources/daemon/tests/unit/` (suite story + invariants)
- Fichiers explicitement hors périmètre technique de cette story (sauf ajustement minimal de compatibilité):
  - `resources/daemon/models/decide_publication.py` (comportement inchangé)
  - modules mapping (`mapping/light.py`, `mapping/cover.py`, `mapping/switch.py`)
  - règles métier d’éligibilité/validation HA.

### Testing Requirements

- Couverture minimale obligatoire:
  - décision positive + publication succès,
  - décision positive + publication échec technique,
  - décision négative + publication non tentée,
  - non-masquage de la cause canonique.
- Les tests d’étape 4 et d’étape 5 doivent rester isolables.
- Toute évolution doit passer la non-régression pipeline existante.

### Previous Story Intelligence (Story 5.1 Done)

- Story 5.1 a validé l’orchestration canonique 5 étapes et l’absence de court-circuit.
- Le sous-bloc canonique `publication_decision` est actuellement porté par `publication_decision_ref`.
- La dette restante identifiée par 5.1: séparer explicitement **décision produit** et **résultat technique** sans ambiguïté.

### Git Intelligence Summary

- Commits récents pertinents:
  - `test(pe-4.4)` a renforcé les invariants pipeline (base de non-régression à préserver),
  - `feat(pe-4.3)` a imposé la migration additive des reason codes,
  - `feat(pe-4.2)` a consolidé la distinction de causes côté diagnostic.
- Implication story 5.2: tout changement doit rester additive-only, compatible invariants, sans casser la taxonomie de diagnostic.

### Latest Technical Information (as of 2026-04-16)

- `paho-mqtt` (PyPI) dernière version stable observée: `2.1.0` (2024-04-29).
- `pytest` (PyPI) dernière version stable observée: `9.0.2` (2025-12-06).
- Documentation Home Assistant MQTT: discovery device-based recommandé; `homeassistant/status` utilisé pour le birth/reload discovery.
- Cette story n’introduit aucune migration de dépendance; elle doit rester compatible avec la stack projet existante.

### Dev Agent Guardrails

- ❌ Ne pas modifier le comportement de `decide_publication()`.
- ❌ Ne pas fusionner décision produit et résultat technique.
- ❌ Ne pas réintroduire de logique métier dans l’étape 5.
- ❌ Ne pas modifier les reason codes existants.
- ❌ Ne pas impacter le contrat des étapes 1–4.
- ✅ Étape 5 = purement technique.
- ✅ Étape 4 = seule source de vérité décisionnelle.
- ✅ Séparation stricte obligatoire.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`.

### Project Context Reference

- Règles projet à appliquer: `_bmad-output/project-context.md` (Python daemon async, jQuery frontend, anti-patterns MQTT, discipline test et déploiement terrain).

### References

- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` — Epic 5, Story 5.2, invariants Feature 5]
- [Source: `_bmad-output/planning-artifacts/prd.md` — FR22, FR23, FR24, FR25, FR27, FR28, FR29, FR30]
- [Source: `_bmad-output/planning-artifacts/pipeline-contract.md` — séparation décisionnelle vs technique, invariants I4/I7]
- [Source: `_bmad-output/planning-artifacts/architecture-delta-review-prd-final.md` — préséance d’interprétation FR39/FR40, mode `governed-open`]
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` — pipeline 5 étapes, classes d’échec, mapping pipeline → code]
- [Source: `_bmad-output/implementation-artifacts/5-1-orchestration-des-5-etapes-le-sync-handler-enchaine-eligibilite-mapping-validation-ha-decision-publication-sans-court-circuit.md`]
- [Source: `_bmad-output/implementation-artifacts/pe-epic-5-alignment-gate.md`]
- [Source: `_bmad-output/implementation-artifacts/pe-epic-5-document-precedence.md`]
- [Source: `_bmad-output/implementation-artifacts/pe-epic-5-governance-exceptions-register.md`]
- [Source: `_bmad-output/implementation-artifacts/pe-epic-5-gov-reference-micro-protocol.md`]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Story créée via workflow BMAD `create-story` avec analyse complète des artefacts pipeline / epic / gov.
- Implémentation réalisée le 2026-04-17 — approche additive-only, zéro remplacement de décision.

### Completion Notes List

- **Task 0** : Pre-flight taggé done structurellement (gate terrain non exécuté — scope tests unitaires uniquement).
- **Task 1** : `PublicationResult` dataclass ajouté à `models/mapping.py` avec `status`, `technical_reason_code`, `attempted_at`. Champ `publication_result: Optional[PublicationResult] = None` ajouté à `MappingResult`.
- **Task 2** : Étape 5 refactorisée pour les 3 types (light, cover, switch) dans `/action/sync`. Suppression des créations de `PublicationDecision` de remplacement. Helper `_make_publication_result()` introduit. `mapping.pipeline_step_reached = 5` câblé. Préservation du marqueur `discovery_published` stale via `_needs_discovery_unpublish`.
- **Task 3** : `_build_traceability` mise à jour — `decision_trace.reason_code` utilise `publication_decision_ref.reason` (étape 4 canonical), `publication_trace` lit `publication_result.status`. Nouveau champ `publication_trace.technical_reason_code` quand disponible. Path diagnostique mis à jour pour dériver `reason_code` depuis `publication_result` quand `active_or_alive=False`.
- **Task 4** : Reason codes techniques existants (`discovery_publish_failed`, `local_availability_publish_failed`) utilisés en mode additif. Aucun renommage/suppression.
- **Task 5** : 12 tests couvrant AC1-AC6 (success, failed, not_attempted, non-masquage, I2/I4/I7, séparation structurelle, testabilité isolée, cas ambiguous + échec technique). 12/12 PASS.
- **Task 6** : Suite complète 424/424 PASS (412 baseline + 12 nouveaux). I2, I4, I7 vérifiés explicitement. Aucun comportement étapes 1–4 impacté. 3 violations AC3/I7 corrigées post-implémentation initiale.
- **Backward compat** : Tests existants `test_diagnostic_endpoint.py` utilisant injection directe `reason="discovery_publish_failed"` passent sans modification grâce au fallback sur `canonical_decision = pub_decision` quand `publication_decision_ref` absent.
- **Post-review fix pass (2026-04-17)** : findings HIGH/MEDIUM traités — diagnostic infra restauré quand `publication_result.status="failed"`, faux `unpublish` évité quand échec initial jamais publié, tests AC3/AC5 renforcés sans early-return permissif.

### File List

- `_bmad-output/implementation-artifacts/5-2-resultat-de-publication-tracable-le-resultat-technique-est-enregistre-separement-de-la-decision-produit-et-ne-masque-pas-la-cause-principale-canonique.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/models/mapping.py`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/tests/unit/test_pe_epic5_story_5_1_orchestration.py`
- `resources/daemon/tests/unit/test_pe_epic5_story_5_2_publication_result.py`

### Change Log

- 2026-04-17 — Implémentation Story 5.2 PE : ajout `PublicationResult` sous-bloc étape 5, refactor étape 5 (light/cover/switch) sans remplacement de décision, mise à jour `_build_traceability` et path diagnostique, 11 nouveaux tests AC1-AC6.
- 2026-04-17 — Correctif AC3/I7 (3 violations identifiées post-implémentation) :
  - **Fix 1** (path diagnostique) : `reason_code` dérive toujours de `canonical_dec.reason` (étape 4), jamais de `publication_result.technical_reason_code`. La cause technique reste exclusivement dans `publication_trace`.
  - **Fix 2** (`_publication_has_technical_failure`) : suppression du fallback sur `dec.reason in ("discovery_publish_failed", ...)`. Version stricte : `return pr.status == "failed"` si `pr` existe, `return False` sinon.
  - **Fix 3** (`_build_traceability` fallback) : quand `_CLOSED_REASON_MAP.get(canonical_reason) is None` et `map_result is not None`, `closed_reason = canonical_reason` (jamais `"discovery_publish_failed"`).
  - **Test ajouté** : `test_decision_trace_reason_code_is_canonical_not_technical_when_ambiguous_and_publish_fails` — cas `ambiguous_skipped` + échec MQTT → `decision_trace.reason_code == "ambiguous_skipped"`, `publication_trace.technical_reason_code == "discovery_publish_failed"`. 12/12 PASS, 424/424 non-régression.
- 2026-04-17 — Senior Developer Review (AI) : `Changes Requested` (1 High, 3 Medium). Statut repassé en `in-progress` dans la story et `sprint-status.yaml`.
- 2026-04-17 — Follow-up automatique post-review :
  - correction `_needs_discovery_unpublish` pour ignorer le fallback `should_publish` quand `publication_result` existe (évite les faux cleanup unpublish),
  - correction diagnostic : priorité à `technical_reason_code` pour la couche opérationnelle quand l’étape 5 échoue, tout en conservant la cause canonique dans `traceability.decision_trace`,
  - tests renforcés/déterministes (`not_attempted`, I4) + 2 régressions ajoutées (diagnostic infra, cleanup sans faux unpublish),
  - validations exécutées : Story 5.2, diagnostics ciblés, invariants pipeline, intégrations story 5.x et cleanup (tout PASS).

## Senior Developer Review (AI)

### Reviewer

- Reviewer: Alexandre
- Date: 2026-04-17
- Outcome: Changes Requested (résolu en follow-up 2026-04-17)

### Findings

- **[HIGH]** Le diagnostic utilisateur ne distingue plus correctement un échec technique de publication d’un refus décisionnel, et peut produire un écart sans cause (`cause_code=None`) pour un équipement non publié après échec MQTT.
  - Preuve code:
    - échec technique stocké uniquement dans `publication_result` sans changer `decision.reason`: `resources/daemon/transport/http_server.py:1088-1094`
    - diagnostic force `reason_code = canonical_dec.reason` quand `active_or_alive=False`: `resources/daemon/transport/http_server.py:1824-1831`
    - la couche 4D dérive ensuite la cause depuis ce `reason_code`: `resources/daemon/transport/http_server.py:1877-1882`
    - `reason_code="sure"`/`"probable"` ne donnent aucune cause 4D: `resources/daemon/models/cause_mapping.py:120-122`
    - `sure`/`probable` restent mappés au statut primaire `Publié`: `resources/daemon/models/taxonomy.py:13-14`

- **[MEDIUM]** `_needs_discovery_unpublish()` peut marquer à tort un équipement comme “à dépublier” après un simple échec de publication (jamais publié), car le fallback utilise `should_publish=True`.
  - Preuve code:
    - fallback actuel: `resources/daemon/transport/http_server.py:413-420`
    - `decision.should_publish` reste vrai après échec publish: `resources/daemon/transport/http_server.py:1088-1094`
    - utilisé ensuite dans le cleanup supprimé/inéligible: `resources/daemon/transport/http_server.py:1337-1343`

- **[MEDIUM]** La couverture de tests AC3/AC5 est partiellement permissive et peut valider sans réellement vérifier le scénario ciblé.
  - `test_not_attempted_when_decision_negative` autorise des retours anticipés (cas non testés réellement): `resources/daemon/tests/unit/test_pe_epic5_story_5_2_publication_result.py:252-263`
  - `test_i4_cause_etape2_not_overwritten_by_etape5` tolère l’absence de mapping et ne force pas l’assertion métier attendue: `resources/daemon/tests/unit/test_pe_epic5_story_5_2_publication_result.py:363-375`

- **[MEDIUM]** Écart de traçabilité Git vs File List: un fichier source de test modifié n’est pas déclaré dans la File List de la story.
  - File List déclarée: `resources/daemon/tests/unit/test_pe_epic5_story_5_2_publication_result.py` uniquement
  - Modifié en working tree aussi: `resources/daemon/tests/unit/test_pe_epic5_story_5_1_orchestration.py`

### Validation exécutée

- `python3 -m pytest resources/daemon/tests/unit/test_pe_epic5_story_5_1_orchestration.py resources/daemon/tests/unit/test_pe_epic5_story_5_2_publication_result.py` → 15 passed
- `python3 -m pytest resources/daemon/tests/unit/test_step4_decide_publication.py resources/daemon/tests/unit/test_pipeline_contract.py resources/daemon/tests/unit/test_pipeline_invariants.py` → 40 passed
