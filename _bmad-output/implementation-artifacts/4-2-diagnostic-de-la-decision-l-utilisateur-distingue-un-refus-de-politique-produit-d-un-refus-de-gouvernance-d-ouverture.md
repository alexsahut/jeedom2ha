# Story 4.2 : Diagnostic de la décision — l'utilisateur distingue un refus de politique produit d'un refus de gouvernance d'ouverture

Status: review

Epic: pe-epic-4 — Décision de publication explicite + contrat de testabilité/rétrocompatibilité garanti

## Story

En tant qu'utilisateur,
je veux voir, dans le diagnostic utilisateur, si un équipement non publié malgré une projection structurellement valide est bloqué par la politique de confiance (`low_confidence`) ou par la gouvernance d'ouverture (`ha_component_not_in_product_scope`),
afin d'agir sur le bon levier, de ne pas confondre les deux refus, et de comprendre clairement ce qui dépend de mon réglage ou du scope produit du cycle.

## Contexte / objectif produit

Story 4.1 a déjà isolé l'étape 4 en backend pur via `decide_publication()`. La séparation logique des deux refus existe donc côté moteur et ne doit pas être rouverte dans cette story.

En revanche, la traduction diagnostic visible n'est pas encore alignée sur ce contrat :

- `resources/daemon/models/cause_mapping.py` ne distingue pas encore correctement `low_confidence` côté `cause_code` / `cause_label` / `cause_action`, et ne couvre pas `ha_component_not_in_product_scope`.
- `resources/daemon/transport/http_server.py` enrichit encore le diagnostic via `_DIAGNOSTIC_MESSAGES` et ne couvre pas ce nouveau refus de gouvernance.
- `desktop/js/jeedom2ha.js` rend la colonne `Raison` via un dictionnaire local `reasonLabels[eq.reason_code]`, donc hors contrat `cause_label`.
- la section visible `Action recommandée` s'appuie aujourd'hui sur `eq.remediation`, pas sur `cause_action`.

Cette story doit donc produire une distinction visible et sémantique sur la surface diagnostic, sans dériver vers une refonte générale du diagnostic ni anticiper l'orchestration runtime d'Epic 5.

## Qualification méthodologique / guardrails

- Classification : surface critique
- L'implémentation peut rester backend-first, mais la story n'est pas backend-only
- Artefact visuel prescriptif requis avant développement
- Gate terrain bloquant requis avant done
- Validation centrée sur la surface diagnostic visible
- Ne pas rouvrir Story 4.1
- Ne pas dériver vers 4.3 au-delà du strict nécessaire
- Aucun `done` si le backend est correct mais que la distinction reste non perceptible dans la modal diagnostic
- Aucun `done` si les deux refus restent rendus par un wording générique, identique, ou confondable pour l'utilisateur

## Dépendances autorisées

- Story 4.1 — `done` : `decide_publication()` fournit déjà la séparation logique des reason codes d'étape 4.
- `pipeline-contract.md` V2 — contrat canonique de l'étape 4 et de la cause décisionnelle.
- `architecture-projection-engine.md` — sémantique canonique de `low_confidence` vs `ha_component_not_in_product_scope`.
- `architecture-delta-review-prd-final.md` — formulation FR24, distinction politique vs gouvernance, wording cible.
- `epics-projection-engine.md` — contrat story-level upstream.
- `ux-spec.md` / acquis Story 4.6 — la surface diagnostic existe déjà comme modal séparée avec colonnes figées `Piece / Nom / Ecart / Statut / Confiance / Raison`.

## Exclusions de scope

- Ne pas modifier la logique de `decide_publication()` ni ses tests story 4.1, sauf ajustement mécanique strictement non comportemental et explicitement justifié.
- Ne pas brancher l'orchestration runtime complète `http_server.py -> decide_publication()` ; ce sujet appartient à Story 5.1.
- Ne pas ouvrir la migration additive globale des codes de classe 2 et 3 ; cela appartient à Story 4.3.
- Ne pas refondre la modal diagnostic, ses colonnes, la séparation home/diagnostic, ni la structure 4D globale.
- Ne pas ajouter d'override inter-étapes, de nouveau hook produit, ni de sujet FR25 post-MVP.
- Ne pas transformer la story en refonte générale de `detail` / `remediation` pour tous les reason codes ; rester strictement focalisé sur `low_confidence` et `ha_component_not_in_product_scope`.

## Acceptance Criteria

1. **Given** un équipement dont la décision finale est `low_confidence`
   **When** le diagnostic est construit puis affiché dans la modal diagnostic existante
   **Then** le contrat diagnostic expose `cause_code = "low_confidence"`
   **And** le libellé visible dans `Raison` exprime explicitement une politique de confiance insuffisante pour la politique active
   **And** la surface visible n'emploie plus pour ce cas un wording générique de type `Aucun mapping compatible`
   **And** l'utilisateur peut identifier qu'un réglage de politique de confiance est le levier pertinent

2. **Given** un équipement dont la décision finale est `ha_component_not_in_product_scope`
   **When** le diagnostic est construit puis affiché dans la modal diagnostic existante
   **Then** le contrat diagnostic expose `cause_code = "not_in_product_scope"`
   **And** le libellé visible dans `Raison` exprime explicitement qu'il s'agit d'un composant non ouvert dans ce cycle
   **And** le diagnostic n'affiche ni fallback `Cause inconnue`, ni wording assimilable à un échec de mapping
   **And** l'utilisateur comprend qu'aucune action directe de configuration Jeedom ne débloque ce cas dans le cycle courant

3. **Given** les deux cas précédents apparaissent dans le même diagnostic ou dans une même session de validation
   **When** l'utilisateur lit la colonne `Raison` et la zone `Action recommandée`
   **Then** les deux refus sont visuellement distincts
   **And** ils sont sémantiquement distincts
   **And** ils sont non confondables pour un utilisateur du plugin
   **And** la différence perçue ne dépend pas d'une connaissance du `reason_code` interne

4. **Given** le backend renvoie des `cause_code`, `cause_label` et `cause_action` distincts pour les deux refus
   **When** la modal diagnostic rend la surface visible
   **Then** la lecture visible s'aligne sur cette traduction diagnostic
   **And** aucun `reason_code` brut n'est exposé à l'utilisateur
   **And** une implémentation qui laisse la modal sur un mapping JS générique identique pour les deux cas est non conforme

5. **Given** Story 4.1 est `done`
   **When** Story 4.2 est implémentée
   **Then** le comportement de `resources/daemon/models/decide_publication.py` reste inchangé
   **And** `resources/daemon/tests/unit/test_step4_decide_publication.py` continue de passer sans régression
   **And** la story n'introduit aucune réouverture fonctionnelle de la séparation interne étape 3 / étape 4

6. **Given** la story est testée automatiquement
   **When** les suites unitaires backend et frontend dédiées sont exécutées
   **Then** elles couvrent au minimum :
   **And** la traduction `reason_code -> cause_*` pour `low_confidence`
   **And** la traduction `reason_code -> cause_*` pour `ha_component_not_in_product_scope`
   **And** le rendu visible du diagnostic sur la vraie surface `Raison`
   **And** l'absence de faux positif où le backend est correct mais la surface visible reste ambiguë

7. **Given** la story touche une surface critique
   **When** son statut `done` est demandé
   **Then** un artefact visuel prescriptif a été produit et validé avant le code
   **And** un gate terrain bloquant a été exécuté avant `done`
   **And** ce gate valide explicitement la distinction visible entre politique produit et gouvernance d'ouverture sur la surface diagnostic

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [x] Task 1 — Produire l'artefact visuel prescriptif avant toute modification de code (AC: #1, #2, #3, #7)
  - [x] Documenter la même modal diagnostic existante avec les deux cas cibles : `low_confidence` et `ha_component_not_in_product_scope`
  - [x] Figer noir sur blanc le wording visible attendu dans `Raison`
  - [x] Figer noir sur blanc la lecture attendue dans `Action recommandée`
  - [x] Valider que l'artefact ne crée aucune nouvelle surface, aucun nouveau tableau, aucune dérive home/diagnostic
  - [x] Bloquer toute implémentation tant que cet artefact n'est pas validé

- [x] Task 2 — Mettre à jour la traduction diagnostic backend pour les deux refus d'étape 4 (AC: #1, #2, #4, #6)
  - [x] Modifier `resources/daemon/models/cause_mapping.py` pour que `low_confidence` produise un `cause_code`, un `cause_label` et un `cause_action` alignés avec la politique produit
  - [x] Ajouter `ha_component_not_in_product_scope` à `resources/daemon/models/cause_mapping.py` avec `cause_code = "not_in_product_scope"` et un `cause_label` explicite de gouvernance d'ouverture
  - [x] Définir pour ce cas une `cause_action` nulle ou explicitement non actionnable côté utilisateur, conformément à l'artefact visuel validé
  - [x] Ne toucher à aucun autre reason code que ces deux cas dans cette story

- [x] Task 3 — Réaligner l'enrichissement humain du diagnostic sans rouvrir l'orchestration (AC: #1, #2, #4)
  - [x] Ajouter dans `resources/daemon/transport/http_server.py` les enrichissements ciblés nécessaires pour éviter tout fallback `Cause inconnue` ou remediation contradictoire sur `ha_component_not_in_product_scope`
  - [x] Réaligner le cas `low_confidence` pour qu'il ne renvoie plus une lecture assimilable à un simple `no_mapping`
  - [x] Limiter strictement les changements à la traduction visible (`detail`, `remediation`, ou équivalent) pour ces deux reason codes
  - [x] Ne pas brancher ici `decide_publication()` dans le runtime global

- [x] Task 4 — Aligner la surface diagnostic visible sur le contrat `cause_*` (AC: #1, #2, #3, #4)
  - [x] Vérifier dans `desktop/js/jeedom2ha.js` le rendu actuel de `Raison` basé sur `reasonLabels[eq.reason_code]`
  - [x] Remplacer ou réaligner ce rendu pour que la lecture visible de `Raison` reflète le contrat diagnostic cible, sans exposer le `reason_code` brut
  - [x] Vérifier la section `Action recommandée` afin qu'elle reflète correctement le sens attendu pour ces deux cas, sans imposer une refonte générale de tous les cas existants
  - [x] Préserver la modal existante, ses colonnes, le ciblage et la séparation home/diagnostic
  - [x] Si un helper pur doit être extrait pour rendre ce rendu testable, le faire de manière minimale et locale, sans recréer une nouvelle architecture frontend

- [x] Task 5 — Ajouter les tests automatisés empêchant la fausse conformité (AC: #4, #5, #6)
  - [x] Étendre `resources/daemon/tests/unit/test_cause_mapping.py` pour couvrir les deux refus d'étape 4 avec leurs `cause_code`, `cause_label`, `cause_action`
  - [x] Ajouter un test backend ciblé sur l'enrichissement diagnostic des deux codes si `test_cause_mapping.py` seul ne suffit pas à verrouiller la lecture visible attendue
  - [x] Ajouter un test frontend story-level sur la surface diagnostic réelle ou un helper pur dérivé de cette surface, pour verrouiller :
    - [x] la différence visible des libellés
    - [x] l'absence de `reason_code` brut
    - [x] la différence de sens utilisateur entre politique et gouvernance
    - [x] l'échec explicite du cas "backend correct mais surface visible ambiguë"
  - [x] Conserver vertes les suites existantes liées à la modal diagnostic et à Story 4.1

- [x] Task 6 — Exécuter le gate terrain bloquant sur la surface visible (AC: #3, #7)
  - [x] Déployer en DEV/TEST ONLY via `scripts/deploy-to-box.sh`
  - [x] Valider la lecture sur la modal diagnostic réelle de la box Jeedom ou, si l'orchestration Epic 5 n'est pas encore branchée, via une fixture/payload de diagnostic contrôlé limitée à la validation de surface
  - [x] Vérifier que `low_confidence` et `ha_component_not_in_product_scope` sont lisibles comme deux refus distincts sans explication verbale additionnelle
  - [x] Bloquer `done` si la distinction n'est pas perceptible immédiatement dans `Raison` et `Action recommandée`

## Dev Notes

### Contexte pipeline et frontière de responsabilité

- Story 4.1 a déjà livré la séparation interne :
  - `low_confidence` = politique produit
  - `ha_component_not_in_product_scope` = gouvernance d'ouverture
- Story 4.2 ne doit pas requalifier cette logique ; elle doit la rendre visible et non ambiguë dans le diagnostic utilisateur.
- Le contrat canonique reste : backend calcule, frontend affiche sans réinterprétation métier inutile.

### Réalité actuelle du code — pièges à ne pas manquer

1. `resources/daemon/models/cause_mapping.py`
   - `low_confidence` renvoie encore `("no_mapping", "Aucun mapping compatible", ...)`
   - `ha_component_not_in_product_scope` n'y existe pas encore

2. `resources/daemon/transport/http_server.py`
   - `_DIAGNOSTIC_MESSAGES` couvre `low_confidence`
   - `_DIAGNOSTIC_MESSAGES` ne couvre pas `ha_component_not_in_product_scope`
   - sans correction ciblée, ce cas tombera sur un fallback type `Cause inconnue`

3. `desktop/js/jeedom2ha.js`
   - la colonne `Raison` visible de la modal repose encore sur `reasonLabels[eq.reason_code]`
   - la section `Action recommandée` repose sur `eq.remediation`
   - une implémentation backend-only ne suffira donc pas à satisfaire les AC visibles

### Direction d'implémentation recommandée

- Backend-first autorisé : commencer par rendre le contrat `cause_*` correct et stable pour les deux reason codes.
- Mais aucun arrêt au backend : la modal diagnostic doit ensuite afficher cette distinction de manière perceptible.
- Préférer une source de vérité unique pour la lecture visible de `Raison` :
  - idéalement `cause_label` backend
  - à défaut, un mapping de présentation unique explicitement aligné sur le contrat backend et borné à ces deux cas
- Pour `Action recommandée`, privilégier l'alignement sur `cause_action` lorsqu'il est pertinent pour ces deux cas, sans réécrire tout le système `detail/remediation`.

### Architecture compliance

- Ne pas modifier `resources/daemon/models/decide_publication.py`
- Ne pas modifier `resources/daemon/tests/unit/test_step4_decide_publication.py` hors régression éventuelle à vérifier
- Ne pas intégrer l'étape 4 dans `_handle_system_diagnostics` via orchestration runtime ; cela appartient à Story 5.1
- Ne pas ouvrir la migration exhaustive des nouveaux codes de classe 2 et 3 ; cela appartient à Story 4.3
- Rester additif et strictement focalisé sur les deux refus d'étape 4

### Library / framework requirements

- Python 3.9+ existant, aucune nouvelle dépendance
- JavaScript existant en jQuery / vanilla seulement, aucune librairie frontend nouvelle
- Réutiliser la modal diagnostic existante ; aucune nouvelle page, aucun nouveau composant de surface

### File structure requirements

Points de départ probables :

- `resources/daemon/models/cause_mapping.py`
- `resources/daemon/tests/unit/test_cause_mapping.py`
- `resources/daemon/transport/http_server.py` — enrichissement humain ciblé seulement
- `desktop/js/jeedom2ha.js`
- `tests/unit/` — nouveau test story-level diagnostic si nécessaire

Points explicitement à ne pas ouvrir dans cette story :

- `resources/daemon/models/decide_publication.py`
- `resources/daemon/tests/unit/test_step4_decide_publication.py`
- toute façade Epic 5 / opérations HA
- toute refonte home/diagnostic déjà figée par les stories UX antérieures

### Previous story intelligence

- Story 4.1 a explicitement laissé `ha_component_not_in_product_scope` comme string literal côté décision, avec centralisation de la traduction renvoyée à Story 4.2 / 4.3.
- Le pattern de 4.1 est très borné : module pur + tests unitaires isolés + aucun branchement runtime.
- Reprendre ce niveau de discipline : traduction ciblée, tests isolés, zéro dérive d'orchestration.

### Git intelligence summary

Historique récent pertinent :

- `b79668c` — Story 4.1 : fonction pure `decide_publication()` + tests isolés
- `32dd849` — Story 3.3 : gouvernance FR40
- `f0e39ed` — Story 3.2 : `validate_projection()` pure
- `a90a730` — Story 3.1 : registre statique HA

Le pattern de cycle est clair : une story = une frontière du pipeline, additive, testée, sans mélange de responsabilités.

### Dev Agent Guardrails

- Ne pas accepter une conformité basée uniquement sur `cause_mapping.py`
- Ne pas accepter une conformité basée uniquement sur `http_server.py`
- Ne pas accepter une conformité basée uniquement sur une copie de wording dans `reasonLabels`
- Refuser toute solution où `low_confidence` et `ha_component_not_in_product_scope` restent affichés avec le même sens utilisateur
- Refuser toute solution qui laisse la modal afficher un wording backend correct dans le payload mais non visible à l'utilisateur

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser exclusivement `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Project Structure Notes

- La surface diagnostic cible est la modal existante `Diagnostic de Couverture`
- Les colonnes restent `Piece / Nom / Ecart / Statut / Confiance / Raison`
- La séparation home / diagnostic reste verrouillée ; 4.2 n'a pas autorité pour la rouvrir
- Le backend reste source de vérité du contrat 4D ; la surface visible ne doit pas reconstruire la sémantique à partir de `reason_code`

## Test Notes

- Backend unitaire :
  - vérifier `reason_code_to_cause("low_confidence")`
  - vérifier `reason_code_to_cause("ha_component_not_in_product_scope")`
  - vérifier la stabilité additive des autres codes existants

- Backend diagnostic ciblé :
  - vérifier qu'aucun des deux cas ne produit `Cause inconnue`
  - vérifier que `detail` / `remediation` ou leur équivalent visible n'entrent pas en contradiction avec `cause_label` / `cause_action`

- Frontend story-level :
  - vérifier la colonne `Raison` visible sur la modal réelle ou sur un helper pur dérivé
  - vérifier que `low_confidence` et `ha_component_not_in_product_scope` n'ont pas le même texte visible
  - vérifier qu'aucun `reason_code` brut n'est exposé
  - vérifier que la distinction utilisateur reste perceptible même si l'on ignore complètement le code interne

- Non-régression :
  - conserver vertes les suites diagnostic existantes
  - confirmer l'absence de régression sur Story 4.1 et sur la modal diagnostic existante

- Gate terrain :
  - obligatoire avant `done`
  - porte sur la surface visible, pas sur une démonstration d'orchestration Epic 5
  - une fixture/payload contrôlé DEV/TEST est acceptable si nécessaire pour faire apparaître les deux cas sans rouvrir le runtime

## References

- [Source: `_bmad-output/implementation-artifacts/pe-epic-3-retro-2026-04-13.md` — AI-3 qualification story 4.2]
- [Source: `_bmad-output/planning-artifacts/pipeline-contract.md` — Étape 4, règles globales, cause canonique]
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` — classe 3, reason codes, scope produit]
- [Source: `_bmad-output/planning-artifacts/architecture-delta-review-prd-final.md` — FR24, distinction politique vs gouvernance]
- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md#Story 4.2`]
- [Source: `_bmad-output/project-context.md` — backend calcule, frontend affiche ; stack et guardrails]
- [Source: `resources/daemon/models/cause_mapping.py` — état actuel du contrat `cause_*`]
- [Source: `resources/daemon/transport/http_server.py` — enrichissement diagnostic actuel]
- [Source: `desktop/js/jeedom2ha.js` — modal diagnostic actuelle, `reasonLabels`, `Action recommandée`]
- [Source: `_bmad-output/implementation-artifacts/4-1-etape-4-decide-publication-arbitre-la-publication-a-partir-de-la-projection-validee-de-la-politique-de-confiance-et-du-product-scope.md`]
- [Source: `_bmad-output/implementation-artifacts/4-6-atterrissage-diagnostic-modal-in-scope-et-ouverture-ciblee-depuis-home.md` — surface diagnostic existante]

## Dev Agent Record

### Agent Model Used

gpt-5

### Debug Log References

- Story créée à partir du workflow BMAD `create-story`
- Analyse croisée : epic 4.2, story 4.1, contrat pipeline, architecture, surface diagnostic existante, code réel backend/frontend
- Worktree dédié créé : `story/4-2-decision-diagnostic` (préflight Git hors clone principal)
- Dry-run terrain validé via `./scripts/deploy-to-box.sh --dry-run`
- Artefact visuel prescriptif produit : `_bmad-output/implementation-artifacts/4-2-artefact-visuel-prescriptif-diagnostic-decision.md`
- Déploiement terrain exécuté : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon` → `Deploy complete.` ; healthcheck MQTT OK ; sync `total_eq=278 eligible=81 published=30`
- Inspection terrain du payload live : aucun cas `low_confidence` ni `ha_component_not_in_product_scope` présent dans les données courantes de la box au moment du gate
- Validation de surface réalisée via fixture contrôlée autorisée par la story ; rendu visible confirmé sur le chemin déployé `cause_label` / `cause_action` sans CTA de configuration parasite

### Implementation Plan

- Réaligner `resources/daemon/models/cause_mapping.py` pour que `low_confidence` et `ha_component_not_in_product_scope` exposent un contrat `cause_*` distinct, lisible et cohérent avec l'artefact visuel.
- Réaligner `resources/daemon/transport/http_server.py` pour éviter tout fallback `Cause inconnue` et toute remediation contradictoire sur ces deux reason codes.
- Réutiliser la modal diagnostic existante en lecture du contrat backend (`cause_label`, `cause_action`) avec fallback legacy strictement borné.
- Ajouter des tests backend ciblés sur `cause_mapping` et `/system/diagnostics`, puis un test frontend story-level sur la lecture visible dérivée de la vraie surface diagnostic.

### Completion Notes List

- Qualification méthodologique `surface critique` intégrée explicitement et non rediscutable
- AC rédigés pour empêcher la fausse conformité backend-only
- Gate terrain bloquant intégré comme condition de `done`
- `low_confidence` expose désormais une raison visible de politique active et une action d'assouplissement de politique
- `ha_component_not_in_product_scope` expose désormais une raison visible de gouvernance produit et une action explicitement non actionnable côté Jeedom
- La modal diagnostic lit prioritairement `cause_label` et `cause_action`, avec fallback legacy strictement borné
- Couverture ajoutée : tests unitaires backend `cause_mapping`, tests endpoint diagnostic ciblés, test frontend story-level sur la surface visible
- Non-régression validée : `node --test tests/unit/*.node.test.js` → 175 PASS ; `python3 -m pytest tests resources/daemon/tests -q` → 928 PASS ; `php tests/test_php_export_diagnostic_coherence.php` PASS ; `php tests/unit/test_story_5_1_php_relay.php` PASS

### File List

- `_bmad-output/implementation-artifacts/4-2-diagnostic-de-la-decision-l-utilisateur-distingue-un-refus-de-politique-produit-d-un-refus-de-gouvernance-d-ouverture.md`
- `_bmad-output/implementation-artifacts/4-2-artefact-visuel-prescriptif-diagnostic-decision.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `desktop/js/jeedom2ha.js`
- `desktop/js/jeedom2ha_diagnostic_helpers.js`
- `resources/daemon/models/cause_mapping.py`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/tests/unit/test_cause_mapping.py`
- `resources/daemon/tests/unit/test_diagnostic_endpoint.py`
- `tests/unit/test_story_4_2_diagnostic_decision.node.test.js`

### Change Log

- 2026-04-14 — Story 4.2 implémentée : distinction visible politique produit vs gouvernance d'ouverture dans le diagnostic, contrat backend `cause_*` réaligné, surface UI bornée au contrat backend, couverture automatisée et gate terrain exécutés
