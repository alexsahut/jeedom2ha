# Story 6.1 : Diagnostic par étape de pipeline — l'utilisateur consulte pour chaque équipement l'étape de blocage et la cause principale canonique unique, ordonnée par pipeline

Status: done

Epic: `pe-epic-6` — Le diagnostic est explicable et actionnable

## Story

En tant qu'utilisateur du diagnostic,
je veux voir pour chaque équipement l'étape de pipeline qui bloque ou aboutit, ainsi que la cause principale canonique unique associée,
afin de comprendre immédiatement où regarder, sans jamais confondre la décision canonique des étapes 1-4 avec le résultat technique de l'étape 5.

## Contexte / Objectif produit

Le gate de readiness `pe-epic-6` est levé au `2026-04-19` :

- P-1 / P-2 soldés : contrat canonique de traceabilité et aliasing sécurisés.
- P-3 soldé : tests I7 non permissifs en place.
- P-4 soldé : artefact UX prescriptif annoncé prêt avant `create-story` 6-1 / 6-3.
- Gate terrain `pe-epic-5` validé selon un niveau de preuve réaliste.

Cette story 6.1 est strictement bornée a la **visibilité de l'étape** et de la **cause canonique unique** sur la surface diagnostic :

- un équipement = une étape visible,
- un équipement = une cause canonique principale,
- l'ordre de lecture suit le pipeline canonique `1 -> 2 -> 3 -> 4 -> 5`,
- le cas `step 5 failed` montre **deux blocs séparés** : `Décision pipeline` et `Résultat technique`.

Point de vigilance déjà observable dans le code :

- `mapping.pipeline_step_reached` existe déjà côté backend, mais n'est pas encore sérialisé comme contrat diagnostic stable.
- `/system/diagnostics` peut encore faire remonter un `reason_code` technique au top-level quand l'étape 5 échoue.
- la surface frontend du diagnostic contient des fallbacks legacy bornés ; 6.1 ne doit pas dépendre d'un mapping métier local JS pour déterminer l'étape ou la cause principale.

## Scope

### In scope

- enrichissement **backend-first** et **additif** du contrat diagnostic pour rendre l'étape visible par équipement ;
- calcul canonique de l'étape visible a partir de la cause décisionnelle et du résultat technique existants, sans rouvrir le pipeline ;
- séparation explicite du cas `step 5 failed` en deux blocs de lecture ;
- consommation frontend en lecture stricte du backend, sans mapping métier local ;
- couverture automatisée ciblée par étape + gate terrain bloquant avant `done`.

### Out of scope

- ajout du sous-bloc `projection_validity` dans `traceability` : **Story 6.2** ;
- extension large du catalogue `cause_label` / `cause_action` ou refonte du wording métier : **Story 6.3** ;
- modification de la source canonique de la cause ;
- refonte du contrat 4D existant ;
- réouverture des décisions P-1 / P-2 / P-3 / P-4 ;
- toute logique "smart" côté frontend pour reconstituer localement une étape ou une cause.

### Frontière explicite avec 6.2 et 6.3

- **6.1** livre la visibilité d'étape, la sélection de la cause canonique unique et la séparation décision / technique sur `step 5 failed`.
- **6.2** porte l'ajout pur de `projection_validity` dans la trace diagnostic.
- **6.3** porte la traduction stable et exhaustive `cause canonique -> cause_label / cause_action`.
- 6.1 peut réutiliser les sorties existantes de `reason_code_to_cause()` si nécessaire pour afficher une cause déjà disponible, mais ne doit pas transformer cette story en chantier de taxonomie ou de wording.

## Acceptance Criteria

1. **AC1 — Étape visible**
   **Given** un équipement visible dans la surface diagnostic
   **When** l'utilisateur lit son diagnostic
   **Then** une seule étape visible parmi `1` a `5` est affichée
   **And** cette étape est cohérente avec `traceability.decision_trace.reason_code`
   **And** l'UI ne déduit pas elle-même cette étape depuis des tables locales de `reason_code`.

2. **AC2 — Cause canonique unique**
   **Given** un équipement diagnostiqué
   **When** la cause principale est affichée
   **Then** elle est dérivée exclusivement de `traceability.decision_trace.reason_code`
   **And** cette valeur reste alimentée par `publication_decision_ref.reason`
   **And** `technical_reason_code` ne peut jamais devenir la cause canonique principale.

3. **AC3 — Ordonnancement pipeline**
   **Given** un équipement présentant plusieurs insuffisances latentes possibles
   **When** le diagnostic est construit
   **Then** l'étape affichée correspond au premier blocage pertinent dans l'ordre canonique :
   `step 1 = éligibilité`, `step 2 = mapping`, `step 3 = validation HA`, `step 4 = décision de publication`, `step 5 = publication / résultat technique`
   **And** une étape aval ne remplace jamais une étape amont comme point de blocage principal.

4. **AC4 — Cas `step 5 failed` séparé**
   **Given** `traceability.decision_trace.reason_code = "published"`
   **And** `traceability.publication_trace.last_discovery_publish_result = "failed"`
   **When** l'utilisateur consulte le diagnostic
   **Then** l'étape visible est l'étape 5
   **And** le rendu affiche un bloc `Décision pipeline` montrant que la décision canonique est positive
   **And** le rendu affiche séparément un bloc `Résultat technique` montrant l'échec technique et son `technical_reason_code`
   **And** aucune fusion visuelle ou sémantique n'est faite entre les deux blocs.

5. **AC5 — Additif / non destructif**
   **Given** le contrat 4D existant, les champs historiques et les consommateurs actuels
   **When** la story est livrée
   **Then** aucun champ historique n'est supprimé, renommé ou déplacé
   **And** l'enrichissement reste backend-first
   **And** les surfaces existantes continuent de fonctionner sans recalcul métier local supplémentaire.

6. **AC6 — UX conforme**
   **Given** l'artefact UX prescriptif `pe-epic-6` et la surface diagnostic existante
   **When** la story est rendue
   **Then** le mapping `étape -> cause -> rendu` respecte strictement l'artefact UX
   **And** le cas `step 5 failed` présente bien deux blocs séparés
   **And** la story reste bornée a la visibilité d'étape et de cause canonique, sans dériver vers la traduction exhaustive 6.3.

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup termine.`

- [x] Task 1 — Formaliser le contrat backend additif de visibilité d'étape (AC: #1, #3, #5)
  - [x] Dans `resources/daemon/transport/http_server.py`, introduire un calcul canonique de l'étape visible par équipement, sous forme d'un champ ou sous-objet additif stable sérialisé dans `/system/diagnostics`.
  - [x] Faire porter ce calcul par le backend a partir des sources canoniques existantes (`publication_decision_ref.reason`, `traceability.decision_trace.reason_code`, `publication_trace.last_discovery_publish_result`, `pipeline_step_reached` si utile), jamais par le frontend.
  - [x] Garantir qu'un seul point de vérité de l'étape visible existe dans la réponse diagnostic.
  - [x] Préserver intégralement le contrat 4D et les champs historiques.

- [x] Task 2 — Verrouiller la cause canonique unique et l'invariant I7 (AC: #2, #3, #4, #5)
  - [x] Vérifier que la cause principale visible de 6.1 dérive exclusivement de `traceability.decision_trace.reason_code`.
  - [x] Interdire explicitement tout usage de `publication_trace.technical_reason_code` comme source de cause principale.
  - [x] Si un champ top-level historique reste orienté "opérationnel", faire en sorte que la nouvelle lecture 6.1 n'en dépende jamais pour la cause canonique.
  - [x] Conserver `publication_decision_ref.reason` comme source canonique de la décision pipeline.

- [x] Task 3 — Rendre le cas `step 5 failed` lisible en deux blocs séparés (AC: #1, #2, #4, #6)
  - [x] Fournir côté backend les informations nécessaires pour afficher distinctement :
    - `Décision pipeline`
    - `Résultat technique`
  - [x] Pour le cas `decision_trace.reason_code = "published"` + `publication_trace.last_discovery_publish_result = "failed"`, afficher la décision positive sans la dégrader en incident technique.
  - [x] Afficher le `technical_reason_code` uniquement dans le bloc technique.
  - [x] Refuser tout badge, libellé ou résumé unique qui fusionnerait les deux dimensions.

- [x] Task 4 — Propager le contrat sans recalcul dans les couches de relais (AC: #1, #5)
  - [x] Mettre a jour `core/ajax/jeedom2ha.ajax.php` si nécessaire pour faire transiter les nouveaux champs additifs sans transformation métier.
  - [x] Vérifier que l'export support et les surfaces existantes conservent leurs champs historiques.
  - [x] Interdire tout recalcul PHP de l'étape visible ou de la cause canonique.

- [x] Task 5 — Implémenter le rendu UI diagnostic en lecture stricte backend (AC: #1, #4, #6)
  - [x] Réutiliser la surface diagnostic existante (`desktop/js/jeedom2ha.js`, helpers voisins, CSS existante) sans recréer de surface parallèle.
  - [x] Afficher l'étape visible fournie par le backend pour chaque équipement.
  - [x] Pour `step 5 failed`, afficher deux blocs séparés `Décision pipeline` / `Résultat technique`.
  - [x] Refuser toute déduction locale de l'étape ou de la cause depuis `status_code`, `reason_code`, `technical_reason_code` ou des tables JS legacy.

- [x] Task 6 — Couvrir les cas backend minimum par des tests ciblés (AC: #1, #2, #3, #4, #5)
  - [x] Ajouter ou mettre a jour une suite dédiée type `resources/daemon/tests/unit/test_story_6_1_pipeline_step_diagnostic.py`.
  - [x] Couvrir au minimum les cas :
    - `step 1`
    - `step 2`
    - `step 3`
    - `step 4`
    - `step 5 success`
    - `step 5 failed` avec séparation décision / technique
  - [x] Ajouter des assertions cassantes si un `technical_reason_code` devient la cause canonique principale.
  - [x] Vérifier la non-régression du contrat historique (`reason_code`, `cause_code`, `cause_label`, `cause_action`, `traceability`, export).

- [x] Task 7 — Couvrir le rendu JS/PHP sans mapping métier local (AC: #1, #4, #5, #6)
  - [x] Ajouter ou mettre a jour des tests JS ciblés sur la modal diagnostic et/ou ses helpers (`tests/unit/test_story_4_6_diagnostic_modal.node.test.js`, nouveau fichier story 6.1 si nécessaire).
  - [x] Vérifier que l'étape visible affichée provient du backend et qu'aucun fallback JS local ne devient source métier.
  - [x] Vérifier que le cas `step 5 failed` rend bien deux blocs séparés.
  - [x] Ajouter un contrôle de relay PHP si un nouveau champ additif transite par `core/ajax/jeedom2ha.ajax.php`.

- [x] Task 8 — Gate terrain bloquant avant `done` (AC: #4, #6)
  - [x] Vérifier en navigation réelle du diagnostic que l'étape visible est lisible pour des équipements réels.
  - [x] Vérifier au moins un cas réel ou fixture contrôlée de `step 5 failed` avec deux blocs séparés `Décision pipeline` / `Résultat technique`.
  - [x] Vérifier qu'aucun cas observé n'affiche une cause technique comme cause principale.
  - [x] Documenter les `eq_id` observés, la date, le contexte de test et le verdict terrain dans la story avant passage a `done`.

## Dev Notes

### Fondations opposables

- Rappel opposable : la cause canonique provient de `publication_decision_ref.reason`.
- Exposition opposable : la cause canonique est lue via `traceability.decision_trace.reason_code`.
- Invariant critique **I7** : un `technical_reason_code` de l'étape 5 ne doit jamais alimenter la cause canonique principale.
- Le pipeline reste ordonné et stable : `1 -> 2 -> 3 -> 4 -> 5`.

### Etat actuel du code a garder en tête

- `resources/daemon/models/mapping.py` porte déjà `pipeline_step_reached`.
- `resources/daemon/transport/http_server.py` positionne déjà `pipeline_step_reached` pendant le sync, mais cette information n'est pas encore exposée comme contrat diagnostic stable.
- `_build_traceability()` conserve `decision_trace` et `publication_trace`, avec `technical_reason_code` déjà isolé dans `publication_trace`.
- `_handle_system_diagnostics()` peut encore promouvoir un motif technique au top-level `reason_code` quand l'étape 5 échoue ; la lecture 6.1 ne doit pas utiliser ce chemin comme source canonique principale.
- `desktop/js/jeedom2ha_diagnostic_helpers.js` contient un fallback legacy borné pour les libellés ; 6.1 ne doit pas s'appuyer dessus pour déterminer l'étape ni la cause dominante.

### Backend-first implementation guidance

- Commencer par le backend et stabiliser un **contrat additif** de visibilité d'étape avant toute retouche UI.
- Faire calculer l'étape visible par un helper pur côté backend, idéalement proche de la sérialisation diagnostic, pour éviter toute divergence entre surfaces.
- La surface UI doit être une lecture stricte du backend : affichage, pas interprétation.
- Si un nommage additif est introduit, il doit être choisi une seule fois et rester stable sur toute la surface diagnostic.

### Frontière explicite avec 6.2 et 6.3

- **Ne pas rouvrir 6.2** : pas d'ajout opportuniste du sous-bloc `projection_validity` dans `traceability` dans cette story.
- **Ne pas rouvrir 6.3** : pas de chantier de complétude du catalogue `cause_label` / `cause_action`.
- Si une lisibilité minimale exige de réutiliser une traduction existante, se limiter a l'existant ; toute extension de taxonomie doit être renvoyée vers 6.3.

### Fichiers / zones candidates

- Backend diagnostic : `resources/daemon/transport/http_server.py`
- Modèle si strictement nécessaire : `resources/daemon/models/mapping.py`
- Relay PHP : `core/ajax/jeedom2ha.ajax.php`
- Frontend diagnostic : `desktop/js/jeedom2ha.js`
- Helpers diagnostic : `desktop/js/jeedom2ha_diagnostic_helpers.js`
- Styles si strictement nécessaires pour les deux blocs `step 5 failed` : `desktop/css/jeedom2ha.css`

### Stratégie de test ciblée

- Backend Python :
  - `resources/daemon/tests/unit/test_diagnostic_endpoint.py`
  - `resources/daemon/tests/unit/test_story_5_2_integration.py`
  - `resources/daemon/tests/unit/test_pipeline_invariants.py`
  - `resources/daemon/tests/unit/test_step1_diagnostic.py`
  - `resources/daemon/tests/unit/test_step2_mapping_failure.py`
  - `resources/daemon/tests/unit/test_step4_decide_publication.py`
  - nouvelle suite story 6.1 dédiée si la lisibilité est meilleure
- Frontend JS :
  - `tests/unit/test_story_4_6_diagnostic_modal.node.test.js`
  - `tests/unit/test_story_5_2_frontend.node.test.js`
  - nouveau test story 6.1 si le rendu par étape mérite une suite dédiée
- Objectif opposable :
  - 1 cas `step 1`
  - 1 cas `step 2`
  - 1 cas `step 3`
  - 1 cas `step 4`
  - 1 cas `step 5 success`
  - 1 cas `step 5 failed` avec séparation décision / technique

### Latest Technical Information

- Aucune recherche web externe n'est requise pour cette story.
- Le scope est ancré sur des contrats internes, des surfaces existantes et des invariants déjà stabilisés dans le repo.
- Aucun upgrade de dépendance ni changement de stack n'est attendu pour 6.1.

### Dev Agent Guardrails

- Ne pas rouvrir P-1 / P-2.
- Ne pas rouvrir P-3.
- Ne pas rouvrir P-4.
- Ne pas modifier la source canonique de la cause.
- Ne pas introduire de mapping frontend local métier.
- Ne pas exposer `technical_reason_code` comme cause principale.
- Ne pas fusionner décision pipeline et incident technique.
- Ne pas dériver vers 6.3 au-delà du strict nécessaire.
- Rester backend-first.
- Garder la story bornée a la visibilité de l'étape et de la cause canonique.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique inchangé : `main -> beta -> stable -> Jeedom Market`.

### Project Context Reference

- `_bmad-output/project-context.md` s'applique en entier pour cette story.
- En cas de doute d'implémentation, préférer l'option la plus restrictive et la plus additive.

### Project Structure Notes

- Réutiliser la modal diagnostic existante et ses helpers ; ne pas recréer une surface parallèle.
- Préserver la structure actuelle du contrat 4D et ses champs historiques.
- Si un helper pur est ajouté pour l'étape visible, le placer au plus près du diagnostic backend existant plutôt que dans une nouvelle couche métier dispersée.

## References

- `_bmad-output/planning-artifacts/epics-projection-engine.md`
  - Epic 6, Story 6.1
  - FR31 a FR35
  - notes UX indiquant qu'une story touchant l'étape visible requiert un artefact visuel prescriptif et un gate terrain
- `_bmad-output/planning-artifacts/prd.md`
  - Feature 0 et Feature 6
  - exigence : étape de pipeline visible, cause principale canonique unique, contrat diagnostic stable
- `_bmad-output/planning-artifacts/architecture-projection-engine.md`
  - D1, D7, D8
  - P1, P2, P7
  - table `Mapping pipeline -> code`
- `_bmad-output/planning-artifacts/pipeline-contract.md`
  - règle globale 2 : cause décisionnelle canonique unique
  - règle globale 9 : décision pipeline vs résultat technique
  - invariants I4 et I7
- `_bmad-output/implementation-artifacts/5-2-resultat-de-publication-tracable-le-resultat-technique-est-enregistre-separement-de-la-decision-produit-et-ne-masque-pas-la-cause-principale-canonique.md`
  - séparation décision / technique déjà livrée
  - correctifs post-review I7
- `_bmad-output/implementation-artifacts/pe-epic-5-retro-2026-04-19.md`
  - gate de readiness `pe-epic-6`
  - P-1 / P-2 / P-3 / P-4 soldés
- `_bmad-output/implementation-artifacts/4-6-atterrissage-diagnostic-modal-in-scope-et-ouverture-ciblee-depuis-home.md`
  - surface diagnostic existante a réutiliser
- `_bmad-output/project-context.md`
  - règles projet daemon / PHP / JS / tests / déploiement terrain

### Références demandées par le brief mais absentes du repo au 2026-04-19

- `_bmad-output/implementation-artifacts/pe-epic-6-traceability-contract.md`
  - **absent du repo lors de la création de cette story**
  - jusqu'a matérialisation, utiliser comme équivalents opérationnels :
    - `_bmad-output/planning-artifacts/pipeline-contract.md`
    - `_bmad-output/implementation-artifacts/5-2-resultat-de-publication-tracable-le-resultat-technique-est-enregistre-separement-de-la-decision-produit-et-ne-masque-pas-la-cause-principale-canonique.md`
    - `_bmad-output/implementation-artifacts/pe-epic-5-retro-2026-04-19.md`
- `_bmad-output/planning-artifacts/ux-epic-6-diagnostic-enrichi.md`
  - **absent du repo lors de la création de cette story**
  - jusqu'a matérialisation, utiliser comme équivalents opérationnels :
    - `_bmad-output/planning-artifacts/epics-projection-engine.md`
    - `_bmad-output/implementation-artifacts/4-6-atterrissage-diagnostic-modal-in-scope-et-ouverture-ciblee-depuis-home.md`
    - `_bmad-output/implementation-artifacts/4-2-artefact-visuel-prescriptif-diagnostic-decision.md`
    - `_bmad-output/implementation-artifacts/pe-epic-5-retro-2026-04-19.md`

## Gate Terrain

Gate terrain **bloquant avant `done`** :

- vérifier la navigation réelle du diagnostic ;
- vérifier au moins un cas `step 5 failed` avec deux blocs séparés `Décision pipeline` / `Résultat technique` ;
- vérifier qu'aucun cas observé n'affiche une cause technique comme cause principale ;
- consigner dans la story :
  - date,
  - environnement,
  - `eq_id` observés,
  - verdict,
  - éventuel niveau de preuve / limite explicite.

### Gate terrain — Validation UX/UI réelle — Story 6.1

**Date** : 2026-04-21
**Environnement** : box Jeedom `192.168.1.21` (broker Mosquitto local `127.0.0.1:1883` ; port `1884` utilisé temporairement pour simulation contrôlée du step 5 failed, restauré en fin de test).
**Branche testée** : `pe-6.1-diagnostic-pipeline-step`
**Distribution d'étapes observée** : step 1 = 197 / step 2 = 38 / step 3 = 10 / step 4 = 3 / step 5 = 30 (total 278 eq, 99 in_scope, 30 publiés).
**Méthode** : gate terrain guidé test par test (SM / QA terrain), un seul test proposé à la fois, retour utilisateur obligatoire avant test suivant.

#### Cas testés et verdicts

| # | Cas | `eq_id` | Verdict | Observation clé |
|---|-----|---------|---------|-----------------|
| 0 | Préflight dry-run | — | PASS | `./scripts/deploy-to-box.sh --dry-run` — SSH OK, sudo OK, 4 fichiers story 6.1 listés |
| 0bis | Déploiement canonique | — | PASS | `--cleanup-discovery --restart-daemon` — 278 eq, 81 éligibles, 30 publiés, MQTT `connected` |
| 1 | Step 5 success — lecture générale | buanderie plafond | PASS | Stepper 5 étapes clair et lisible, étape 5 surlignée, cause canonique `published` affichée sans code technique, aucune erreur console |
| 2 | Step 2 — mapping non trouvé | `Buanderie / capteur` (cmds `#4292-4297`) | PASS | Cause "Aucun mapping compatible" (canonique, phrasé humain) ; `Résultat de publication : Non tenté` en ligne secondaire discrète → I7 OK |
| 3 | Step 3 — validation HA invalide | `Garage / CHACON_porte-garage` (cmds `#2210-2212`) | PASS avec observation | Stepper étape 3 OK ; cause "Mapping ambigu" issue de `decision_trace.reason_code = ambiguous_skipped` — léger écart sémantique étape/cause (stepper pointe Validation HA alors que la cause évoque la décision d'ambiguïté). Contrat AC2/I7 strictement respecté. À remonter comme suggestion d'affinement UX pour 6.2/6.3 |
| 4 | Step 4 — décision négative | `terrasse / lames pergola (virt)` `eq_id 380` | PASS | Cause "Mapping ambigu" (`ambiguous_skipped`) ; libellé identique au cas step 3 mais le **stepper seul distingue visuellement les deux cas** — valeur UX de la story 6.1 concrètement démontrée |
| 5 | Step 5 failed — deux blocs (AC4) | `buanderie plafond` `eq_id 391` (cas contrôlé) | **PASS ★** | Deux blocs visuellement séparés : bloc vert "**Décision pipeline / Publiée** / Cause canonique: `published`" + bloc rouge "**Résultat technique / Échec** / Code technique: `discovery_publish_failed`". Cause en tête = "Publication MQTT échouée" (libellé humain synthétique, pas code technique brut) → I7 respecté. Badge "Incident infrastructure" + action recommandée concrète ("Vérifier la connexion au broker MQTT et relancer un diagnostic après résolution") |

#### Invariants transversaux validés

- **AC1** — étape visible fournie par le backend et lisible via stepper horizontal `1 → 2 → 3 → 4 → 5` : **PASS** sur 5 cas (steps 2, 3, 4, 5 success, 5 failed)
- **AC2** — cause canonique unique issue de `traceability.decision_trace.reason_code` uniquement : **PASS** sur 5 cas
- **AC4** — séparation `Décision pipeline` / `Résultat technique` pour `step 5 failed` : **PASS** (cas contrôlé ; qualité UX excellente)
- **AC5** — contrat additif / pas de régression sur l'existant : **PASS** (équipements précédemment publiés conservent leurs badges `Aligne / Publié / Sûr` et leurs blocs historiques)
- **I7** — `technical_reason_code` (`discovery_publish_failed`) jamais affiché comme cause canonique principale : **PASS** sur les 5 cas ; `technical_reason_code` n'apparaît que dans le bloc "Résultat technique" dédié

#### Cas contrôlé — simulation step 5 failed

- **Méthode** : bascule temporaire `mqttPort` plugin `1883 → 1884` via `config::save('mqttPort', '1884', 'jeedom2ha')`, restart daemon (`jeedom2ha::deamon_start()`), `POST /action/sync`, observation UI, puis restauration `mqttPort = 1883` + restart + re-sync.
- **Durée totale** : ~5 minutes.
- **Impact résiduel** : aucun — état nominal restauré et vérifié (`failed_publish = 0`, MQTT `connected`, 30 topics discovery republiés, distribution d'étapes identique).
- **Justification** : aucun cas `step 5 failed` naturel disponible (MQTT nominal sur la box). Simulation ciblée sur le plugin uniquement, réversible, validée — aucune perturbation du broker ni des autres intégrations HA.

#### Limites explicites

- **AC3** (ordonnancement pipeline) : non testé terrain isolément — mais le stepper horizontal `1 → 2 → 3 → 4 → 5` est visible et correctement ordonné dans toutes les captures (Tests 1-5). Couverture automatisée dans `test_story_6_1_pipeline_step_diagnostic.py`.
- **Observation UX cause identique aux steps 3 et 4** : le libellé "Mapping ambigu — plusieurs types possibles" apparaît sur les deux étapes (backend calcule l'étape bloquante la plus précoce selon `projection_validity.is_valid is False` avant `should_publish = False`). Contrat strictement respecté, mais suggestion d'affinement de libellé pour distinguer visuellement les deux cas au niveau de la cause — à instruire en **6.2/6.3**, hors scope 6.1.

#### Verdict gate terrain : **PASS**

Story 6.1 validée en UX/UI réel. Tous les AC terrain (AC1, AC2, AC4, AC5) et l'invariant **I7** sont respectés sur 5 cas couvrant 4 étapes distinctes (steps 2, 3, 4, 5 success + 5 failed). La valeur UX apportée par le stepper est concrètement démontrée (Test 4 vs Test 3 : le stepper est le facteur différenciant unique et clair quand la cause canonique est identique).

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (Claude Code)

### Debug Log References

- Story créée via le workflow BMAD `create-story`.
- Analyse exhaustive effectuée sur les artefacts epic / PRD / architecture / pipeline / readiness / stories fondatrices du diagnostic.
- Implémentation 2026-04-21 : branche `pe-6.1-diagnostic-pipeline-step`, cycle rouge-vert-refactor complet.

### Completion Notes List

- **Backend** : `_compute_pipeline_step_visible(el_result, map_result, pub_decision) -> int` ajouté dans `http_server.py`. Helper pur, déterministe, retourne 1-5 selon l'étape canonique bloquante. I7 garanti : `technical_reason_code` n'influence jamais ce calcul.
- **Backend** : champ `pipeline_step_visible` ajouté dans `eq_dict` de `_handle_system_diagnostics` — additif, aucun champ historique touché.
- **PHP** : `pipeline_step_visible` ajouté dans l'allowlist d'export de `_jeedom2ha_build_export_equipment`. Relay `getDiagnostics` passe-through sans recalcul.
- **Frontend** : `buildDetailRow` dans `jeedom2ha.js` lit `eq.pipeline_step_visible` strictement depuis le backend — affiche les 5 étapes avec la courante surlignée. Aucune déduction locale.
- **Frontend** : cas `step 5 failed` rendu en deux blocs séparés (`Décision pipeline` / `Résultat technique`) via `isStep5Failed(pipelineStep, pubResult)`.
- **Helpers** : `isStep5Failed` et `getCanonicalDiagnosticCause` ajoutés dans `jeedom2ha_diagnostic_helpers.js` — purs, testables en Node.js.
- **Tests backend** : `test_story_6_1_pipeline_step_diagnostic.py` — 10 tests (steps 1-5, I7, non-régression contrat historique). 436/436 pytest PASS.
- **Tests JS** : `test_story_6_1_pipeline_step.node.test.js` — 14 tests (AC1/AC2/AC4/AC5, I7). 189/189 JS PASS.
- **Gate terrain** : Task 0 et Task 8 exécutés le 2026-04-21 sur box Jeedom `192.168.1.21`. Gate guidé test par test (SM / QA terrain). Verdict terrain : **PASS**. 5 cas testés couvrant steps 2, 3, 4, 5 success, 5 failed. `step 5 failed` validé via cas contrôlé (bascule `mqttPort` temporaire, restaurée). Observation UX non bloquante remontée pour 6.2/6.3 (libellé "Mapping ambigu" identique aux steps 3 et 4 — le stepper reste le facteur différenciant). Détails et `eq_id` consignés dans la section "Gate terrain — Validation UX/UI réelle".

### File List

- `_bmad-output/implementation-artifacts/6-1-diagnostic-par-etape-de-pipeline-l-utilisateur-consulte-pour-chaque-equipement-l-etape-de-blocage-et-la-cause-principale-canonique-unique-ordonnee-par-pipeline.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/tests/unit/test_story_6_1_pipeline_step_diagnostic.py`
- `desktop/js/jeedom2ha.js`
- `desktop/js/jeedom2ha_diagnostic_helpers.js`
- `core/ajax/jeedom2ha.ajax.php`
- `tests/unit/test_story_6_1_pipeline_step.node.test.js`

## Change Log

- **2026-04-21** : Implémentation story 6.1 (claude-sonnet-4-6, branche `pe-6.1-diagnostic-pipeline-step`)
  - Backend : helper `_compute_pipeline_step_visible` + champ `pipeline_step_visible` dans le contrat diagnostic
  - PHP : ajout dans l'allowlist export (`_jeedom2ha_build_export_equipment`)
  - Frontend : rendu étape pipeline + deux blocs séparés `step 5 failed` dans `buildDetailRow`
  - Helpers : `isStep5Failed`, `getCanonicalDiagnosticCause` dans `jeedom2ha_diagnostic_helpers.js`
  - Tests : 10 pytest + 14 JS — 436/436 pytest PASS, 189/189 JS PASS, zéro régression
  - Gate terrain (Tasks 0 et 8) : en attente de validation sur box Jeedom — bloquant avant `done`
- **2026-04-21** : Gate terrain validé (claude-opus-4-7 en SM / QA terrain, box Jeedom `192.168.1.21`)
  - 5 cas testés : steps 2 (`Buanderie/capteur`), 3 (`Garage/CHACON_porte-garage`), 4 (`terrasse/lames pergola (virt)` eq_id 380), 5 success (`buanderie plafond`), 5 failed (`buanderie plafond` eq_id 391 cas contrôlé)
  - AC1/AC2/AC4/AC5/I7 validés ; AC3 couvert par stepper visible + tests automatisés
  - Simulation step 5 failed : bascule temporaire `mqttPort 1883 → 1884` via `config::save`, restart daemon, sync, observation deux blocs UI, restauration complète (`failed_publish=0` vérifié post-restore)
  - Observation UX non bloquante : libellé "Mapping ambigu" identique sur steps 3 et 4 → affinement à instruire en 6.2/6.3
  - Verdict : **PASS** — story passée `done` après merge PR #98
