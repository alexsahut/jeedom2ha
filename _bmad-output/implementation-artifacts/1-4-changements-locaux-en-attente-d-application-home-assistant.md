# Story 1.4: Changements locaux en attente d'application Home Assistant

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur Jeedom,
je veux distinguer une décision locale de périmètre d'une action effectivement appliquée à Home Assistant,
afin de ne pas croire qu'un toggle modifie instantanément HA.

## Story Context

- Cycle actif obligatoire: **Post-MVP Phase 1 - V1.1 Pilotable**
- Dépendances autorisées: Story 1.1, Story 1.2, Story 1.3
- Statut des dépendances: Story 1.1 = done, Story 1.2 = done, Story 1.3 = done
- Story productrice backend de référence: `1-1-resolver-canonique-du-perimetre-publie`
- Story productrice UI synthèse: `1-2-vue-globale-et-synthese-par-piece-sans-recalcul-frontend`
- Story productrice explicabilité équipement: `1-3-exceptions-equipement-et-visibilite-continue-des-exclus`
- Positionnement dans l'epic: Story 1.4 est la dernière story d'Epic 1
- Réduction de dette support: réduit les tickets issus de la confusion "j'ai exclu mais HA n'a pas encore changé"
- Rappel de workflow: aucun agent ne doit deviner la source de vérité; la stratégie de test V1.1 fait partie des sources actives

## Acceptance Criteria

1. **AC1 - Visibilité d'un changement local en attente au niveau pertinent**
   **Given** une modification locale d'inclusion ou d'exclusion
   **When** l'utilisateur revient sur la console
   **Then** un état `changements à appliquer à Home Assistant` est visible au niveau pertinent

2. **AC2 - Non-confusion entre décision locale et effet HA effectif**
   **Given** des changements locaux non encore appliqués
   **When** l'utilisateur consulte la synthèse globale ou la pièce
   **Then** l'UI n'affiche pas ces changements comme déjà effectifs côté Home Assistant

3. **AC3 - Cohérence de l'état en attente à travers la navigation**
   **Given** des changements locaux en attente et aucune opération Home Assistant encore confirmée
   **When** l'utilisateur recharge la console ou navigue entre les niveaux `global`, `pièce` et `équipement`
   **Then** l'état `changements à appliquer` reste visible de manière cohérente
   **And** il dépend uniquement du payload backend de périmètre en attente, sans recalcul métier frontend

### Vocabulaire visible canonique

Les AC issus du breakdown utilisent deux formes:
- forme longue: `changements à appliquer à Home Assistant` (AC1)
- forme courte: `changements à appliquer` (AC3)

**Libellé UI canonique retenu:** `Changements à appliquer`

Ce libellé est le seul à utiliser dans les Tasks, Dev Notes, tests et rendu. Il correspond à la forme courte des AC. La forme longue sert de définition produit; la forme courte sert de libellé d'affichage dans la console.

### Matrice d'affichage

L'expression "au niveau pertinent" (AC1) se résout par la matrice suivante, sans ambiguïté:

| Niveau | Champ backend lu | Affichage libellé `Changements à appliquer` | Condition |
|---|---|---|---|
| Global | `global.has_pending_home_assistant_changes` | Oui | flag == `true` |
| Pièce | `pieces[i].has_pending_home_assistant_changes` | Oui | flag == `true` |
| Équipement | `equipements[i].has_pending_home_assistant_changes` | Oui | flag == `true` |
| Tout niveau | champ absent ou `false` | Non (rien affiché) | flag != `true` |
| Avant premier sync | `has_contract: false` | Non (rien affiché) | pas de contrat |

Chaque niveau lit **son propre flag** depuis le payload backend. Aucun agrégat ni recalcul frontend.

## Tasks / Subtasks

- [x] Task 1 - Exposer le flag pending dans le modèle scope summary aux trois niveaux (AC: 1, 2, 3)
  - [x] 1.1 Dans `createModel()` de `desktop/js/jeedom2ha_scope_summary.js`, lire `has_pending_home_assistant_changes` depuis le payload backend au niveau global, pièce et équipement
  - [x] 1.2 Inclure ce booléen dans la structure de modèle retournée, tel quel, sans le recalculer ni le redériver
  - [x] 1.3 Quand `has_contract: false` (avant premier sync), le modèle ne doit exposer aucun flag pending; aucun indicateur `Changements à appliquer` ne doit apparaître

- [x] Task 2 - Rendre le libellé `Changements à appliquer` au niveau équipement (AC: 1)
  - [x] 2.1 Pour chaque équipement où `has_pending_home_assistant_changes == true`, afficher le libellé canonique `Changements à appliquer`
  - [x] 2.2 Pour chaque équipement où `has_pending_home_assistant_changes` est absent ou `false`, ne rien afficher
  - [x] 2.3 Le libellé `Changements à appliquer` ne doit pas être confondu avec l'état effectif (`include / exclude`), la source de décision (`Hérite de la pièce` / `Exception locale`), ni un bouton d'action

- [x] Task 3 - Rendre le libellé `Changements à appliquer` au niveau pièce (AC: 1, 2)
  - [x] 3.1 Pour chaque pièce où `has_pending_home_assistant_changes == true` dans le payload backend, afficher le libellé canonique `Changements à appliquer`
  - [x] 3.2 Lire le flag directement depuis le champ pièce du payload (déjà agrégé par le backend); ne pas itérer les équipements côté frontend pour recalculer le flag pièce
  - [x] 3.3 Le libellé pièce ne doit pas modifier ni interférer avec les compteurs `include / exclude` déjà affichés par Story 1.2

- [x] Task 4 - Rendre le libellé `Changements à appliquer` au niveau global (AC: 2, 3)
  - [x] 4.1 Quand `global.has_pending_home_assistant_changes == true` dans le payload backend, afficher le libellé canonique `Changements à appliquer` dans le résumé global
  - [x] 4.2 Quand le flag global est absent ou `false`, ne rien afficher
  - [x] 4.3 Le libellé global ne doit pas devenir un bandeau de santé (sujet Epic 2); il doit rester un indicateur d'état transitionnel normal

- [x] Task 5 - Préserver la cohérence backend-first sans dérive vers Epic 3 ou Epic 4 (AC: 1, 2, 3)
  - [x] 5.1 Rafraîchir l'état pending uniquement à partir du payload backend renvoyé après synchronisation ou refresh, sans delta local optimiste
  - [x] 5.2 Garder intacts le résumé global, les synthèses par pièce et le détail équipement déjà livrés par Stories 1.2 et 1.3
  - [x] 5.3 Ne pas introduire de bouton d'action, de parcours de confirmation, ni de workflow orienté `appliquer les changements à Home Assistant`; réservé à Epic 4
  - [x] 5.4 Ne pas introduire de nouveau `statut`, `raison principale` ou `action recommandée`; réservé à Epic 3
  - [x] 5.5 Ne pas confondre le libellé `Changements à appliquer` avec le bandeau de santé minimale; réservé à Epic 2

- [x] Task 6 - Ajouter les preuves de test V1.1 ciblées sur le libellé `Changements à appliquer` (AC: 1, 2, 3)
  - [x] 6.1 Étendre `tests/unit/test_scope_summary_presenter.node.test.js` pour prouver que `has_pending_home_assistant_changes` est correctement modélisé et que le libellé `Changements à appliquer` est rendu aux trois niveaux quand le flag est `true`
  - [x] 6.2 Ajouter un cas de test mixte: équipement avec `has_pending_home_assistant_changes: true` + équipement avec `has_pending_home_assistant_changes: false` dans la même pièce; vérifier que le libellé apparaît uniquement sur l'équipement pending et sur la pièce, pas sur l'équipement non-pending
  - [x] 6.3 Ajouter un cas de test sans pending (`has_pending_home_assistant_changes: false` partout): vérifier qu'aucun libellé `Changements à appliquer` n'apparaît à aucun niveau
  - [x] 6.4 Ajouter un cas de test `has_contract: false`: vérifier qu'aucun libellé `Changements à appliquer` n'apparaît
  - [x] 6.5 Vérifier que les tests existants de Story 1.2 et Story 1.3 passent en non-régression (2 assertions `deepEqual` adaptées mécaniquement pour inclure `has_pending_home_assistant_changes: false` dans le modèle attendu — ajout d'un champ avec valeur par défaut, sans modification de comportement fonctionnel)

## Dev Notes

### Contexte actif et contraintes de cadrage

- Le cycle actif de référence est **Post-MVP Phase 1 - V1.1 Pilotable**
- Les sources actives de vérité pour cette story sont:
  - `_bmad-output/planning-artifacts/active-cycle-manifest.md`
  - `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Contexte secondaire autorisé et utilisé:
  - `_bmad-output/implementation-artifacts/1-1-resolver-canonique-du-perimetre-publie.md`
  - `_bmad-output/implementation-artifacts/1-2-vue-globale-et-synthese-par-piece-sans-recalcul-frontend.md`
  - `_bmad-output/implementation-artifacts/1-3-exceptions-equipement-et-visibilite-continue-des-exclus.md`
- Aucun agent ne doit deviner la source de vérité
- La stratégie de test V1.1 est une source active, pas un contexte secondaire
- Ne pas rouvrir le cadrage produit, ne pas modifier les epics, ne pas réinterpréter les invariants déjà figés dans le breakdown validé
- Story 1.1 = done, Story 1.2 = done, Story 1.3 = done
- Story 1.4 est la dernière story de l'Epic 1

### Invariants non renégociables à reprendre tels quels

- Le modèle canonique du périmètre publié reste `global -> pièce -> équipement`
- Les états supportés restent `inherit / include / exclude`
- La résolution suit explicitement `équipement > pièce > global`
- Le backend reste l'unique source de calcul de la décision effective et du flag `has_pending_home_assistant_changes`
- **La décision locale de périmètre et l'application effective à Home Assistant restent deux concepts distincts** — c'est l'invariant central de cette story
- Story 1.4 ne crée pas de nouveau contrat backend: elle rend visible un flag déjà calculé, déjà relayé, et déjà transmis au frontend
- Aucun calcul de `has_pending_home_assistant_changes` ne doit être introduit dans `desktop/js/jeedom2ha.js` ou dans un autre fichier JS
- Les frontières hors scope V1.1 restent gelées: pas d'extension fonctionnelle, pas de preview complète, pas de remédiation guidée avancée, pas de santé avancée, pas d'alignement Homebridge

### Contrat backend à consommer pour Story 1.4

Le champ `has_pending_home_assistant_changes` est déjà intégralement en place dans la chaîne backend → frontend. Story 1.4 doit le rendre visible sans le modifier.

**Niveau global**
- `has_pending_home_assistant_changes` (booléen): `true` quand au moins une pièce a un pending change
- Calculé dans `_apply_pending_scope_flags()` de `resources/daemon/transport/http_server.py` comme `any(piece_pending.values())`

**Niveau pièce**
- `has_pending_home_assistant_changes` (booléen): `true` quand au moins un équipement de la pièce a un pending change
- Calculé comme agrégat OR des flags équipement de la pièce

**Niveau équipement**
- `has_pending_home_assistant_changes` (booléen): `true` quand `desired_include != is_active`
  - `desired_include` = `effective_state == "include"` (issu du resolver canonique)
  - `is_active` = l'équipement est actuellement publié et actif dans HA (basé sur `PublicationDecision.active_or_alive`)
  - Inclut la gestion des unpublish différés (`pending_discovery_unpublish`)

**Chaîne de transmission déjà en place (ne pas modifier):**
1. `resources/daemon/models/published_scope.py` → initialise les flags à `False`
2. `resources/daemon/transport/http_server.py` → calcule les flags réels via `_apply_pending_scope_flags()`
3. `core/class/jeedom2ha.class.php` → relai transparent via `getPublishedScopeForConsole()`
4. `core/ajax/jeedom2ha.ajax.php` → expose via action `getPublishedScopeForConsole`
5. `desktop/js/jeedom2ha.js` → appelle l'AJAX via `refreshPublishedScopeSummary()`
6. `desktop/js/jeedom2ha_scope_summary.js` → reçoit dans `createModel()` mais **ne rend pas encore le flag**

**Story 1.4 intervient uniquement sur le point 6**: modéliser et rendre visible le flag déjà reçu.

Notes de contrat:
- Le relai PHP est transparent et ne transforme pas le payload; Story 1.4 n'a pas besoin de modifier `core/class/` ni `core/ajax/`
- Le daemon n'a pas besoin de modification; le flag est déjà calculé correctement
- L'état "avant premier sync" (`has_contract: false`) est déjà géré par Stories 1.2/1.3 et doit rester intact
- Story 1.4 ne crée pas de nouveau contrat backend, pas de nouvel endpoint, pas de nouvelle opération HA
- Si une incohérence documentaire est détectée dans la chaîne existante pendant le dev, elle doit être signalée et traitée comme un correctif ciblé, pas comme un élargissement de scope

### Dev Agent Guardrails

- Cette story est strictement bornée à la **visibilité du flag `has_pending_home_assistant_changes`** dans la console, aux trois niveaux
- Le seul fichier JS à modifier pour le rendu est `desktop/js/jeedom2ha_scope_summary.js`; le fichier `desktop/js/jeedom2ha.js` ne doit pas être modifié sauf nécessité technique minimale non-métier
- Le périmètre de modification attendu est **exclusivement frontend**: modèle + rendu dans le scope summary presenter
- Aucune modification backend n'est attendue: ni dans le daemon Python, ni dans le relai PHP, ni dans l'endpoint AJAX
- Le libellé UI canonique est **`Changements à appliquer`** — c'est le seul libellé à utiliser dans le rendu, les tests et les assertions; il correspond à la forme courte des AC du breakdown validé
- L'indicateur est **purement présentationnel**: le libellé `Changements à appliquer` est affiché si et seulement si `has_pending_home_assistant_changes == true` au niveau considéré; rien n'est affiché si `false` ou absent
- Ne pas introduire de bouton, de lien, de workflow, ni de parcours de confirmation orienté "appliquer à HA" — Epic 4
- Ne pas introduire de `statut`, `raison principale`, `action recommandée` — Epic 3
- Ne pas introduire de bandeau de santé, d'indicateur démon/broker — Epic 2
- Toute logique de présentation ajoutée côté JS doit rester pure, déterministe et testée: lecture directe d'un booléen backend, aucun recalcul ni agrégat frontend

### Previous Story Intelligence

- **Story 1.1** a livré le resolver backend canonique `published_scope` et a figé les champs incluant `has_pending_home_assistant_changes` à tous les niveaux
- **Story 1.1** a préparé `_apply_pending_scope_flags()` qui compare `effective_state` (voulu) avec `active_or_alive` (publié dans HA) pour calculer le flag
- **Story 1.2** a branché la console sur `published_scope` via un relai PHP/AJAX en lecture stricte, avec état explicite avant premier sync
- **Story 1.2** a verrouillé qu'aucun compteur ni aucune décision métier ne doivent être recalculés dans le frontend
- **Story 1.3** a ajouté le détail équipement (`effective_state`, `decision_source`, `is_exception`) dans le rendu par pièce, mais a explicitement laissé `has_pending_home_assistant_changes` hors de son scope UI (cf. Task 4.3 de Story 1.3)
- **Story 1.3** a confirmé que le flag `has_pending_home_assistant_changes` est présent dans le contrat, transmis au frontend, mais non rendu — c'est précisément le travail réservé à Story 1.4
- Les derniers commits confirment la séquence à prolonger:
  - `feat(story-1.1): add canonical published scope resolver`
  - `feat(story-1.2): add backend-driven global and room scope summaries`
  - `feat(story-1.3): render equipment exceptions from backend scope`
- Pattern de rendu établi par Stories 1.2 et 1.3: le présentateur `jeedom2ha_scope_summary.js` construit un modèle depuis le payload backend, puis un render() produit le HTML — Story 1.4 doit prolonger ce pattern
- Pattern de test établi: `tests/unit/test_scope_summary_presenter.node.test.js` utilise des fixtures JSON et vérifie le modèle + le HTML produit — Story 1.4 doit prolonger ce pattern

### Testing Requirements

**Alignement avec l'addendum de stratégie de test V1.1** (`test-strategy-post-mvp-v1-1-pilotable.md`):
- Cette story **ne crée pas de nouveau contrat backend** et **ne crée pas de nouvelle opération HA**
- Elle rend visible un flag backend déjà calculé, déjà relayé et déjà couvert par les tests existants
- Les tests d'intégration backend ne sont donc pas requis en création de nouveau comportement, mais les suites backend/PHP existantes sur le flag `has_pending_home_assistant_changes` doivent **rester vertes en non-régression**
- Les tests UI sont **requis**, car la story modifie un contrat visible critique (l'état pending devient lisible aux trois niveaux)

**Invariants V1.1 explicitement touchés:**
- séparation entre périmètre local décidé et application effective à Home Assistant (invariant central de cette story)
- modèle canonique `global -> pièce -> équipement`
- backend source unique du flag pending
- absence de recalcul métier frontend

**Champs de contrat stables par niveau** (ne pas confondre les niveaux):
- Global: `counts`, `has_pending_home_assistant_changes`
- Pièce: `object_id`, `object_name`, `counts`, `has_pending_home_assistant_changes`
- Équipement: `eq_id`, `object_id`, `effective_state`, `decision_source`, `is_exception`, `has_pending_home_assistant_changes`
- Le champ `has_pending_home_assistant_changes` est le seul présent aux trois niveaux; les autres champs sont spécifiques à leur niveau

**Tests unitaires obligatoires** (présentateur `jeedom2ha_scope_summary.js`):
- prouver que `createModel()` extrait `has_pending_home_assistant_changes` au niveau global, pièce et équipement
- prouver que `render()` affiche le libellé `Changements à appliquer` uniquement quand le flag est `true` au niveau considéré
- couvrir le cas mixte: un équipement pending + un équipement non-pending dans la même pièce → libellé sur l'équipement pending et sur la pièce, absent sur l'équipement non-pending
- couvrir le cas sans pending (`false` partout) → aucun libellé `Changements à appliquer` à aucun niveau
- couvrir le cas `has_contract: false` → aucun libellé, aucune erreur

**Tests de contrat et de non-régression obligatoires:**
- non-régression des suites backend existantes: `tests/unit/test_published_scope.py`, `tests/unit/test_published_scope_http.py` doivent rester vertes
- non-régression du relai PHP: `tests/test_php_published_scope_relay.php` doit rester vert
- non-régression des preuves Story 1.2 (synthèse globale, compteurs) et Story 1.3 (détail équipement, libellés `Hérite de la pièce` / `Exception locale`)
- preuve qu'aucune logique de décision, d'agrégat frontend ou d'action HA n'est introduite dans le code JS

**Tests UI ciblés** (requis — contrat visible critique modifié):
- vérifier un cas avec au moins un équipement pending et un non-pending dans la même pièce: le libellé `Changements à appliquer` apparaît sur l'équipement pending et sur la pièce, pas sur l'équipement non-pending
- vérifier que le libellé global `Changements à appliquer` apparaît quand le flag global est `true`, absent quand `false`
- vérifier qu'un refresh remplace le rendu depuis le backend recalculé, sans état résiduel
- ces tests UI ciblés se matérialisent dans les assertions HTML de `tests/unit/test_scope_summary_presenter.node.test.js`

**Pas de campagne E2E exhaustive** requise par défaut pour cette story

### Project Structure Notes

- Alignement avec la structure projet existante:
  - backend canonique dans `resources/daemon/models/` et `resources/daemon/transport/` (pas de modification Story 1.4)
  - relai Jeedom côté `core/class/` et `core/ajax/` (pas de modification Story 1.4)
  - rendu console côté `desktop/js/`
- Fichier à modifier:
  - `desktop/js/jeedom2ha_scope_summary.js` — ajout de la modélisation et du rendu de l'indicateur pending
- Fichiers de test à étendre:
  - `tests/unit/test_scope_summary_presenter.node.test.js` — ajout des cas pending
- Fichiers à ne PAS modifier:
  - `resources/daemon/models/published_scope.py` — le flag est déjà initialisé
  - `resources/daemon/transport/http_server.py` — le flag est déjà calculé
  - `core/class/jeedom2ha.class.php` — le relai est déjà transparent
  - `core/ajax/jeedom2ha.ajax.php` — l'endpoint existe déjà
  - `desktop/js/jeedom2ha.js` — pas de logique métier dans ce fichier
  - `desktop/php/jeedom2ha.php` — pas de modification backend nécessaire

### Dependencies and Sequencing

- Dépendances autorisées: Story 1.1, Story 1.2, Story 1.3
- Dépendances en avant: interdites
- Cette story reste strictement dans le périmètre Epic 1 et ne dépend pas des Epics 2, 3 ou 4 pour fonctionner nominalement
- Story 1.4 est la dernière story de l'Epic 1; après sa complétion et sa validation, l'Epic 1 pourra être considéré pour clôture (retrospective optionnelle)
- Story 4.2 (flux republier non destructif) dépend de Story 1.4; le flag pending visible prépare le contexte mais Story 1.4 ne doit pas anticiper Epic 4

### Risks / Points de vigilance

- Recalculer `has_pending_home_assistant_changes` côté frontend au lieu de lire le flag backend
- Introduire un bouton ou lien d'action "Appliquer" qui empiéterait sur Epic 4
- Confondre l'indicateur pending avec un indicateur de santé (Epic 2) ou un statut/raison (Epic 3)
- Présenter l'état pending comme un dysfonctionnement ou une erreur, alors qu'il est un état transitionnel normal
- Modifier les fichiers backend (daemon, PHP) alors que la chaîne complète est déjà en place
- Casser les compteurs de synthèse ou les libellés d'explicabilité déjà livrés par Stories 1.2 et 1.3
- Oublier de tester le cas `has_contract: false` (avant premier sync) qui ne doit pas afficher d'indicateur pending

### References

- Sources actives de vérité:
  - `_bmad-output/planning-artifacts/active-cycle-manifest.md`
  - `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md` (Epic 1, Story 1.4)
  - `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Contexte secondaire autorisé:
  - `_bmad-output/implementation-artifacts/1-1-resolver-canonique-du-perimetre-publie.md`
  - `_bmad-output/implementation-artifacts/1-2-vue-globale-et-synthese-par-piece-sans-recalcul-frontend.md`
  - `_bmad-output/implementation-artifacts/1-3-exceptions-equipement-et-visibilite-continue-des-exclus.md`
- Points d'ancrage codebase (lecture seule pour contexte):
  - `resources/daemon/models/published_scope.py` — initialisation des flags
  - `resources/daemon/transport/http_server.py` — calcul des flags (`_apply_pending_scope_flags`)
  - `core/class/jeedom2ha.class.php` — relai transparent (`getPublishedScopeForConsole`)
  - `core/ajax/jeedom2ha.ajax.php` — endpoint AJAX
  - `desktop/js/jeedom2ha.js` — appel AJAX (`refreshPublishedScopeSummary`)
  - `desktop/js/jeedom2ha_scope_summary.js` — modèle + rendu (fichier à modifier)
  - `tests/unit/test_scope_summary_presenter.node.test.js` — tests du présentateur (fichier à étendre)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Cycle RED-GREEN confirmé : 4 tests échouants → 8/8 verts après implémentation
- PHP non disponible dans l'environnement local ; test relay vérifié par absence de modifications PHP/Python

### Completion Notes List

- Task 1: `buildEquipmentModel()` étendu avec `has_pending_home_assistant_changes` (readBoolean, défaut false). `createModel()` expose `global_pending` et `has_pending_home_assistant_changes` par pièce. Modèle entièrement passthrough backend, aucun recalcul frontend.
- Task 2: `renderPieceEquipements()` ajoute `<span class="label label-warning">Changements à appliquer</span>` sur chaque équipement où le flag est `true`.
- Task 3: La cellule nom de pièce dans le tableau inclut le libellé si `has_pending_home_assistant_changes == true`. Flag lu directement depuis le champ pièce du payload, pas itération des équipements.
- Task 4: `render()` insère le libellé global après le bloc stats quand `model.global_pending === true`.
- Task 5: Aucun bouton, aucune action, aucun statut, aucun bandeau santé ajoutés. Aucun fichier backend modifié. Les Stories 1.2/1.3 restent intacts.
- Task 6: 5 nouveaux tests ajoutés dans `test_scope_summary_presenter.node.test.js` (modèle aux 3 niveaux, rendu aux 3 niveaux, cas mixte, cas sans pending, cas `has_contract: false`). Les `deepEqual` existants mis à jour pour inclure le nouveau champ. 8/8 tests JS verts + 42/42 tests Python non-régression verts.

### File List

- `desktop/js/jeedom2ha_scope_summary.js` — modifié (buildEquipmentModel, createModel, render, renderPieceEquipements)
- `tests/unit/test_scope_summary_presenter.node.test.js` — modifié (update deepEqual + 5 nouveaux tests Story 1.4)

## Change Log

- 2026-03-23 — Implémentation complète Story 1.4 : flag `has_pending_home_assistant_changes` rendu visible aux 3 niveaux (global, pièce, équipement) avec le libellé canonique `Changements à appliquer`. Ajout de 5 tests unitaires JS ciblés. 8/8 tests JS + 42 tests Python verts en non-régression.
