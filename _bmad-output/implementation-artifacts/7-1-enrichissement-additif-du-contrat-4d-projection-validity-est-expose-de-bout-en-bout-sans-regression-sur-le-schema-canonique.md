# Story 7.1 : Enrichissement additif du contrat 4D — `projection_validity` est exposé de bout en bout sans régression sur le schéma canonique

Status: done

<!-- Créée le 2026-04-23 — première story exécutable de pe-epic-7 après correct-course approuvé du 2026-04-22 -->
<!-- 6.2 re-homée = artefact historique non exécutable ; 7.1 reprend son intention structurelle non livrée -->

## Story

En tant que mainteneur de jeedom2ha,
je veux exposer le sous-bloc `projection_validity` de bout en bout dans le contrat 4D et dans le diagnostic par enrichissement additif pur,
afin de rendre visible la réalité structurelle de la projection Home Assistant avant toute future ouverture produit ou toute future promesse d'action utilisateur.

## Contexte / Objectif produit

### Séquencement opposable

- `pe-epic-6` est clôturé proprement sur la valeur réellement livrée : explicabilité par étape + sémantique honnête.
- La story `6.2` a été re-homée vers `pe-epic-7` comme **artefact historique** ; elle n'est plus une source de travail exécutable.
- Le correct-course approuvé du `2026-04-22` impose que la **première story exécutable de `pe-epic-7` soit 7.1**.
- 7.1 reprend l'intention structurelle non livrée de la 6.2 initialement planifiée : **exposer `projection_validity` dans le contrat 4D par ajout additif pur**.

### Réalité produit à préserver

- Cette story n'est **pas** une story UX.
- Cette story n'introduit **aucune** nouvelle action utilisateur.
- Cette story ne modifie **pas** `PRODUCT_SCOPE`.
- Cette story ne rouvre **pas** la sémantique 6.3 sur `cause_label` / `cause_action`.
- La règle d'équipe reste non négociable : **on n'expose une action que si elle est faisable et supportée par le produit ; sinon, on n'en expose pas.**

### Réalité actuelle du code à exploiter

- `ProjectionValidity` existe déjà dans `models/mapping.py`.
- `validate_projection()` est déjà appelé dans l'orchestration avant `decide_publication()`.
- `mapping.projection_validity` est donc déjà produit dans le pipeline pour les équipements éligibles mappés.
- Le point d'écart principal est le contrat diagnostic : `_build_traceability()` n'expose pas encore le sous-bloc `projection_validity` dans la structure 4D.
- Le contrat existant transporte déjà `traceability` et `pipeline_step_visible` côté endpoint ; 7.1 doit donc être traitée comme un **ajout de contrat backend-first**, pas comme une couche UX.

### Objectif produit de 7.1

Rendre visible, dans le diagnostic canonique, la réalité structurelle de la projection HA :

- ce qui a été validé en étape 3 ;
- ce qui a échoué structurellement ;
- ce qui a été **skippé explicitement** ;
- sans faux guidage, sans nouveau CTA, sans ouverture implicite de périmètre produit.

## Scope

### In scope

- enrichissement additif du contrat 4D avec le sous-bloc `projection_validity` ;
- propagation end-to-end du sous-bloc dans le diagnostic ;
- présence explicite de `projection_validity`, y compris en cas de skip ;
- stabilité stricte du schéma historique hors ajout additif documenté ;
- tests backend de schéma, de présence, de skip explicite et de non-régression ;
- éventuelle propagation frontend en lecture stricte uniquement si elle est nécessaire pour préserver le contrat d'affichage, sans nouveau wording d'action.

### Out of scope

- toute modification de `cause_action` ;
- toute nouvelle logique de remédiation utilisateur ;
- toute modification de `PRODUCT_SCOPE` ;
- toute ouverture de nouveaux types HA ;
- toute modification des `reason_code` existants ;
- toute refonte UX, wording ou CTA ;
- toute logique métier recalculée côté frontend ;
- toute story de gouvernance d'ouverture (périmètre 7.4) ;
- toute story d'actionnabilité réelle (périmètre 7.5) ;
- tout chantier global de diagnostic dépassant l'ajout contractuel ciblé `projection_validity`.

## Acceptance Criteria

### AC1 — Enrichissement additif pur du contrat 4D

**Given** la sortie de diagnostic d'une opération de sync et le baseline canonique avant 7.1  
**When** le schéma exposé est comparé avant / après implémentation  
**Then** tous les champs historiques restent présents avec les mêmes noms, types et sémantiques  
**And** aucun champ existant n'est supprimé, renommé ou déplacé  
**And** le diff de schéma ne montre que des ajouts additifs documentés, dont `traceability.projection_validity`  
**And** les champs déjà stabilisés (`perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`, `traceability`, `pipeline_step_visible`) restent inchangés en contrat.  
_[Source : FR34, FR44, AR11, NFR12]_

### AC2 — Présence end-to-end de `projection_validity`

**Given** un équipement présent dans le payload diagnostic canonique  
**When** le contrat exposé est inspecté  
**Then** le sous-bloc `traceability.projection_validity` est présent de bout en bout dans la réponse backend  
**And** `projection_validity` est strictement dérivé du pipeline existant  
**And** `projection_validity` est une projection du pipeline, jamais une reconstitution  
**And** son absence implicite n'est jamais autorisée pour un cas de skip  
**And** lorsqu'aucune validation HA réelle n'a pu être exécutée, le sous-bloc expose un skip explicite sous forme additive documentée (`is_valid: null` et `reason_code` de skip, ou équivalent documenté sans rupture de schéma)  
**And** pour les équipements arrêtés avant l'étape 3, `projection_validity` ne doit pas être construit à partir d'une logique métier, mais uniquement exposé sous forme de statut de skip dérivé du pipeline  
**And** aucune logique de reconstruction ou de simulation de l'étape 3 n'est autorisée  
**And** si un équipement a été arrêté à l'étape 1, l'exposition diagnostique éventuelle du sous-bloc reste purement additive et ne doit pas violer l'invariant I1 sur `MappingResult`.  
_[Source : AR2, AR11, P1, pipeline-contract I1 / I5]_

### AC3 — Cas nominaux et cas skipped couverts

**Given** un équipement ayant atteint l'étape 3  
**When** le diagnostic est inspecté  
**Then** `projection_validity` expose un sous-bloc complet avec `is_valid`, `missing_fields`, `missing_capabilities`, `reason_code` reflétant le résultat réel de validation

**Given** un équipement éligible bloqué avant validation HA effective  
**When** le diagnostic est inspecté  
**Then** `projection_validity` est tout de même présent avec des valeurs explicites de skip  
**And** ce skip explicite ne repose sur aucun calcul artificiel de validation HA  
**And** le contrat ne laisse jamais un trou implicite là où le pipeline a produit un skip documenté  
**And** au minimum un cas nominal et un cas skipped sont couverts par les tests story 7.1.  
_[Source : Story 7.1 epic, AR2, D8, P1]_

### AC4 — Zéro dérive UX / action utilisateur

**Given** le diff de code et le contrat exposé après implémentation  
**When** les champs 4D visibles sont revus  
**Then** aucun nouveau `cause_action` n'est introduit  
**And** aucun nouveau CTA n'apparaît  
**And** aucune nouvelle promesse d'action utilisateur n'est ajoutée  
**And** aucun changement opportuniste de `cause_label` ni de la sémantique 6.3 n'est embarqué dans la story  
**And** `cause_mapping.py` n'est pas rouvert pour autre chose qu'une contrainte strictement nécessaire de transport additif, laquelle doit alors être explicitement justifiée en review.  
_[Source : FR32, FR33, correct-course 2026-04-22, rétro pe-epic-6]_

### AC5 — Frontend en lecture stricte uniquement

**Given** un besoin de propagation jusqu'à la surface diagnostic ou export  
**When** du code PHP ou JS est touché  
**Then** il se limite à transporter ou afficher le sous-bloc déjà calculé par le backend  
**And** aucun recalcul métier local n'est introduit  
**And** aucune table locale `reason_code -> libellé/action` n'est créée ou réintroduite  
**And** aucun nouveau wording d'action n'est ajouté côté frontend.  
_[Source : invariant backend-first du contrat 4D, stories 3.4 / 6.1 / 6.3]_

### AC6 — Non-régression stricte

**Given** le corpus de non-régression du diagnostic et les suites ciblées du pipeline  
**When** les tests concernés sont exécutés  
**Then** le contrat historique reste stable hors ajout additif documenté  
**And** le corpus de non-régression du diagnostic passe  
**And** aucun invariant pipeline n'est cassé, notamment I1, I4, I5 et I7  
**And** les cas nominal, invalide et skipped autour de `projection_validity` sont tous verrouillés par des tests automatisés.  
_[Source : FR41, FR44, NFR11, NFR12, pipeline-contract I1 / I4 / I5 / I7]_

### AC7 — Story strictement non-ouvrante

**Given** le code, les tests et les fichiers modifiés par 7.1  
**When** la story est relue comme incrément produit  
**Then** `PRODUCT_SCOPE` n'est pas modifié  
**And** aucun type HA supplémentaire n'est rendu "ouvert"  
**And** aucun changement de registre ou de gouvernance FR40 / NFR10 n'est glissé implicitement  
**And** la story ne peut pas être utilisée pour faire passer une ouverture implicite sous couvert de visibilité diagnostique.  
_[Source : FR39, FR40, NFR10, AR13, delta review point 4]_

### AC8 — Cohérence `projection_validity` ↔ décision

**Given** un équipement avec `projection_validity` exposé  
**When** `projection_validity.is_valid = False`  
**Then** `decision.should_publish = False`  
**And** aucun cas ne doit exister où une projection invalide mène à une publication positive  
**And** cette cohérence verrouille l'alignement entre l'étape 3 et l'étape 4 sans réintroduire de recalcul dans le diagnostic.  
_[Source : pipeline-contract I2, AR9, D7]_

## Tasks / Subtasks

- [x] Task 1 — Exposer `projection_validity` dans le contrat diagnostic par ajout pur (AC: #1, #2, #3)
  - [x] Enrichir `_build_traceability()` pour sérialiser `projection_validity` sans déplacer ni renommer les blocs existants.
  - [x] Réutiliser `MappingResult.projection_validity` lorsqu'il est déjà présent.
  - [x] Définir et documenter la représentation explicite des cas skipped dans le contrat diagnostic, sans trou implicite.
  - [x] Préserver à l'identique `observed_commands`, `typing_trace`, `decision_trace`, `publication_trace`, `perimetre`, `statut`, `ecart`, `cause_*` et `pipeline_step_visible`.

- [x] Task 2 — Propager le sous-bloc end-to-end sans dérive UX (AC: #2, #4, #5)
  - [x] Vérifier que `eq_dict["traceability"]` transporte le nouveau sous-bloc sans traduction locale.
  - [x] Ne toucher `core/ajax/jeedom2ha.ajax.php` que si l'export normalisé perd le sous-bloc additif.
  - [x] Si `desktop/js/jeedom2ha.js` ou `desktop/js/jeedom2ha_diagnostic_helpers.js` doivent être touchés pour préserver le contrat affiché, limiter le changement au transport / affichage strict.
  - [x] Ne pas introduire de nouveau libellé d'action, de CTA, ni de logique locale d'interprétation.

- [x] Task 3 — Couvrir les cas nominaux, invalides et skipped par des tests dédiés (AC: #2, #3, #6, #8)
  - [x] Créer une suite de tests story 7.1 couvrant au minimum : cas nominal étape 3, cas invalide étape 3, cas skipped explicite avant validation HA.
  - [x] Étendre `tests/unit/test_diagnostic_endpoint.py` pour verrouiller la présence du sous-bloc et son schéma additif.
  - [x] Étendre `tests/unit/test_story_6_1_pipeline_step_diagnostic.py` et/ou `tests/unit/test_pipeline_contract.py` pour préserver I1 / I5 et la séparation diagnostic vs pipeline interne.
  - [x] Verrouiller explicitement la cohérence `projection_validity.is_valid=False -> should_publish=False` sans modifier `decide_publication()`.
  - [x] Étendre `tests/unit/test_diagnostic_export.py` ou la suite d'export pertinente pour vérifier que l'ajout reste compatible avec l'export existant.

- [x] Task 4 — Verrouiller la non-régression canonique et la frontière de périmètre (AC: #1, #4, #6, #7)
  - [x] Exécuter le corpus de non-régression concerné par le contrat diagnostic 4D.
  - [x] Vérifier qu'aucune modification n'affecte `PRODUCT_SCOPE`, les `reason_code` historiques, `cause_mapping.py` ou la sémantique 6.3.
  - [x] Documenter le diff de schéma attendu comme strictement additif et lister explicitement les champs ajoutés.
  - [x] Confirmer que 7.1 prépare 7.2 / 7.3 / 7.4 / 7.5 sans préfigurer leur code.

## Dev Notes

### Fondations opposables

- 7.1 reprend l'intention structurelle non livrée de la 6.2 initialement planifiée.
- La 6.2 re-homée n'est plus une source de travail exécutable ; elle reste un artefact historique de sequencing.
- `projection_validity` doit être traité comme un **ajout de contrat**, pas comme une couche UX.
- Cette story prépare 7.2 / 7.3 / 7.4 / 7.5, mais ne doit en préfigurer aucune au niveau code.
- La sémantique honnête posée en 6.3 reste intangible dans 7.1.

### État actuel du code à exploiter

- `models/mapping.py` porte déjà `ProjectionValidity` et le champ `projection_validity` dans `MappingResult`.
- `transport/http_server.py` appelle déjà `validate_projection()` puis assigne `mapping.projection_validity` avant `decide_publication()`.
- `_build_traceability()` est l'endroit canonique où le contrat diagnostic additif doit être enrichi.
- La construction de `eq_dict` transporte déjà `traceability` et `pipeline_step_visible`; il faut réutiliser ce chemin plutôt qu'en créer un nouveau.
- `core/ajax/jeedom2ha.ajax.php` transporte déjà `traceability` comme bloc opaque ; ne le modifier que si un trou d'export réel est démontré.
- Le frontend lit déjà le contrat backend ; aucune interprétation locale supplémentaire ne doit être ajoutée.
- `projection_validity` ne doit jamais influencer le pipeline ; il est uniquement exposé, pas utilisé pour recalculer.
- Aucune logique ne doit être déplacée depuis `validate_projection()` vers le diagnostic.
- Aucun fallback ni recalcul de validation n'est autorisé dans `http_server.py`.
- Le diagnostic reflète le pipeline ; il ne le reconstruit pas.

### Fichiers / zones candidates

- `transport/http_server.py` — cible principale pour propager le sous-bloc additif dans `_build_traceability()` et, si nécessaire, dans l'assemblage du payload.
- `models/mapping.py` — référence structurelle ; aucun changement attendu sauf nécessité contractuelle démontrée.
- `tests/unit/test_diagnostic_endpoint.py` — verrouillage de présence / schéma de `projection_validity`.
- `tests/unit/test_story_6_1_pipeline_step_diagnostic.py` — continuité des cas step 3 / step 4 / step 5 et invariants pipeline.
- `tests/unit/test_diagnostic_export.py` — non-régression export / contrat historique.
- `tests/unit/test_pipeline_contract.py` — verrouillage des invariants de sous-blocs si une aide de sérialisation est introduite.
- `core/ajax/jeedom2ha.ajax.php` — touchable seulement si le transport export du bloc additif l'exige réellement.
- `desktop/js/jeedom2ha.js` et `desktop/js/jeedom2ha_diagnostic_helpers.js` — touchables uniquement en lecture stricte si un affichage existant perd le bloc additif.

### Stratégie de test ciblée

- cas nominal : un équipement ayant réellement passé `validate_projection()` expose `projection_validity` complet ;
- cas invalide : un équipement avec invalidité HA expose les champs d'échec structurel attendus ;
- cas skipped : un équipement n'ayant pas produit de validation HA explicite expose un skip documenté, jamais une absence implicite ;
- cas étape 1 : si le contrat diagnostic choisit d'exposer un skip additif pour les inéligibles, vérifier qu'I1 reste vrai côté pipeline interne ;
- non-régression : comparer le schéma diagnostique avant / après et verrouiller que seuls les ajouts documentés apparaissent.

### Décisions d'implémentation à respecter

- `http_server.py` peut être touché **uniquement** pour propager le sous-bloc additif `projection_validity` si nécessaire.
- Le frontend ne doit faire **aucune** interprétation locale.
- Aucun calcul métier ne doit être déplacé hors du backend.
- Aucun changement d'intention produit ne doit être inféré à partir de la seule visibilité de `projection_validity`.
- `projection_validity` est une projection du pipeline existant, jamais une reconstitution de l'étape 3.
- Le diagnostic reflète le pipeline ; il ne le reconstruit pas.

## Guardrails

- Ne pas toucher `PRODUCT_SCOPE`.
- Ne pas modifier `cause_action`.
- Ne pas modifier les `reason_code`.
- Ne pas créer de nouveau CTA.
- Ne pas glisser de wording UX supplémentaire.
- Ne pas faire de story hybride 7.1 + 7.5.
- Ne pas rouvrir la sémantique 6.3.
- Ne pas introduire de logique métier frontend.
- Ne pas transformer 7.1 en chantier global de diagnostic.
- Ne pas simuler l'exécution de l'étape 3 dans `MappingResult` pour les équipements arrêtés à l'étape 1.
- Si un skip additif est exposé pour un équipement inéligible, il doit être synthétisé au niveau du contrat diagnostic sans casser I1.
- Ne pas modifier `cause_mapping.py` ni les surfaces `cause_label` / `cause_action` pour des raisons opportunistes.
- Interdiction de recalculer `projection_validity` en dehors de `validate_projection()`.
- Interdiction de déduire `projection_validity` à partir de `reason_code` ou de la décision.
- Interdiction de créer une dépendance inverse (`diagnostic -> pipeline`).

## References

- [Source: `_bmad-output/planning-artifacts/active-cycle-manifest.md` — sections 4, 6, 9]
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` — AR1, AR2, AR11 ; Epic 6 ; Story 6.2 ; Story 6.3 ; Epic 7 ; Story 7.1 ; Stories 7.2 à 7.5]
- [Source: `_bmad-output/planning-artifacts/prd.md` — FR32, FR33, FR34, FR39, FR40, FR42, FR44 ; NFR10, NFR11, NFR12]
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` — D1, D4, D7, D8 ; P1 ; P7 ; structure projet delta moteur de projection]
- [Source: `_bmad-output/planning-artifacts/architecture-delta-review-prd-final.md` — points 2, 3 et 4 sur étape 4, NFR10 et `PRODUCT_SCOPE`]
- [Source: `_bmad-output/planning-artifacts/pipeline-contract.md` — étapes 1 à 4 ; règle 3 ; invariants I1, I4, I5, I7]
- [Source: `_bmad-output/implementation-artifacts/6-2-diagnostic-enrichissement-cause-et-actions-l-utilisateur-comprend-clairement-le-probleme-et-comment-le-corriger.md` — disposition opposable et contexte historique]
- [Source: `_bmad-output/implementation-artifacts/6-3-traduction-cause-canonique-cause-label-cause-action-stables-action-proposee-uniquement-si-une-remediation-utilisateur-existe.md` — guardrails sémantiques à ne pas rouvrir]
- [Source: `_bmad-output/implementation-artifacts/pe-epic-6-retro-2026-04-22.md` — accord d'équipe non négociable et distinction explicable / actionnable]
- [Source: `models/mapping.py` — `ProjectionValidity`, `MappingResult`]
- [Source: `transport/http_server.py` — orchestration étape 3 / `_build_traceability()` / assemblage diagnostic]
- [Source: `core/ajax/jeedom2ha.ajax.php` — transport export du contrat]
- [Source: `desktop/js/jeedom2ha.js`, `desktop/js/jeedom2ha_diagnostic_helpers.js` — lecture stricte frontend]
- [Source: `tests/unit/test_diagnostic_endpoint.py`, `tests/unit/test_diagnostic_export.py`, `tests/unit/test_story_6_1_pipeline_step_diagnostic.py`, `tests/unit/test_pipeline_contract.py`]

## Definition of Done

- [x] `projection_validity` est présent dans le contrat 4D par ajout additif pur.
- [x] Les cas nominal et skipped sont couverts par des tests automatisés.
- [x] La non-régression complète du schéma et du diagnostic est démontrée.
- [x] Aucun changement n'affecte `cause_action`.
- [x] Aucun changement n'affecte `PRODUCT_SCOPE`.
- [x] Aucune promesse d'action utilisateur n'est ajoutée.
- [x] Si du PHP ou du JS est touché, il reste en lecture stricte uniquement.
- [x] Aucun invariant pipeline critique n'est cassé.
- [x] `projection_validity` est uniquement issu du pipeline, sans aucune simulation.
- [x] La cohérence entre `projection_validity` et la décision est validée (AC8).
- [x] Aucun code introduit ne modifie le comportement de `decide_publication()`.
- [x] La story est prête à permettre 7.2 ensuite, sans ambiguïté de périmètre.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Préflight : branche dédiée `story/pe-7.1-projection-validity-contract`, `_build_traceability()` identifié dans `resources/daemon/transport/http_server.py`.
- RED : tests story 7.1 et garde-fous endpoint/export échouent sur absence de `traceability.projection_validity`.
- GREEN : sérialisation additive via `_build_projection_validity_trace()`, sans modification de `validate_projection()` ni `decide_publication()`.
- Validation : suites ciblées et suite daemon unit complète PASS.

### Completion Notes List

- Ajout contractuel strict : `traceability.projection_validity` expose `is_valid`, `reason_code`, `missing_fields`, `missing_capabilities`.
- Cas nominal/invalide : le diagnostic lit uniquement `MappingResult.projection_validity`.
- Cas skipped : représentation explicite `is_valid: null` avec `reason_code: skipped_projection_validation_not_reached` ou `skipped_projection_validation_not_executed`, synthétisée au niveau diagnostic uniquement.
- Aucun changement frontend/PHP, aucun CTA, aucun wording UX, aucun recalcul local.
- `PRODUCT_SCOPE`, `cause_action`, `cause_mapping.py`, `decide_publication()` et les reason_code existants ne sont pas modifiés par 7.1.

### File List

- `resources/daemon/transport/http_server.py`
- `resources/daemon/tests/unit/test_story_7_1_projection_validity_diagnostic.py`
- `resources/daemon/tests/unit/test_diagnostic_endpoint.py`
- `resources/daemon/tests/unit/test_diagnostic_export.py`
- `resources/daemon/tests/unit/test_pipeline_contract.py`
- `_bmad-output/implementation-artifacts/7-1-enrichissement-additif-du-contrat-4d-projection-validity-est-expose-de-bout-en-bout-sans-regression-sur-le-schema-canonique.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-04-24 — Implémentation Story 7.1 : exposition additive de `traceability.projection_validity`, tests nominal/invalide/skipped/export, non-régression daemon unit complète.
- 2026-04-24 — Code review PASS (claude-opus-4-7) : purge du drift 6.2/6.3 de la branche (cause_mapping.py, resolve_cause_ux, frontend JS, test_story_4_2 wording) ; ajout des invariants I1/I5 dans test_pipeline_contract.py ; 438/438 pytest PASS. Story passée done.
