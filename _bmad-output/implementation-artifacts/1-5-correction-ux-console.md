# Story 1.5 : Correction UX console — lisibilité et navigation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur Jeedom,
je veux que la console de périmètre publié présente les pièces sous forme pliable/dépliable, affiche les badges d'exclusion et d'exception de manière visuellement distincte, et préserve ma position de navigation lors des rafraîchissements automatiques,
afin de pouvoir naviguer et analyser le périmètre sans être submergé par un mur d'équipements et sans perdre mon contexte à chaque refresh.

## Story Context

- **Cycle actif :** Post-MVP Phase 1 - V1.1 Pilotable
- **Type :** mini-story corrective UX console — dette mesurable identifiée en rétrospective Epic 1 (2026-03-23)
- **Priorité :** bloquante avant Epic 2
- **Source :** action item #1 de `_bmad-output/implementation-artifacts/epic-1-retro-2026-03-23.md`
- **Dépendances amont :** Stories 1.1, 1.2, 1.3, 1.4 (toutes done)
- **Contrainte centrale :** correction de lisibilité et d'usage uniquement — aucune modification du contrat backend `published_scope`, aucune logique métier frontend

**Cadrage UX de cette mini-story :** cette story corrige la lisibilité et la navigation de la console existante. Elle ne tranche pas le design complet et définitif de la console V1.1 et ne remplace pas les futurs travaux epic-level sur la santé du pont (Epic 2), les statuts lisibles (Epic 3) et les opérations HA (Epic 4).

## Acceptance Criteria

1. **AC1 — Pièces repliées par défaut**
   **Given** la console chargée avec N pièces et leurs équipements
   **When** l'utilisateur consulte la vue des pièces pour la première fois, ou après un rafraîchissement manuel
   **Then** chaque pièce n'affiche que sa ligne synthèse (nom + compteurs) ; les équipements sont masqués
   **And** un indicateur visuel signale qu'un clic sur l'en-tête rend les équipements accessibles

2. **AC2 — Toggle déplier / replier une pièce**
   **Given** la console affichant les pièces repliées
   **When** l'utilisateur clique sur l'en-tête d'une pièce
   **Then** les équipements de cette pièce s'affichent
   **When** l'utilisateur clique à nouveau
   **Then** les équipements se masquent

3. **AC3 — Badge `exclude` visuellement distinct**
   **Given** un équipement avec état `exclude`
   **When** l'utilisateur déplie la pièce correspondante
   **Then** le badge d'état `exclude` est visuellement distinct du badge `include` et communique un état inactif ou désactivé
   **And** le badge `exclude` n'utilise pas la couleur rouge réservée aux incidents d'infrastructure

4. **AC4 — Badge `Exception locale` visuellement distinct de `Hérite de la pièce`**
   **Given** une pièce contenant à la fois un équipement avec source de décision par exception et un équipement héritant de la règle de la pièce
   **When** l'utilisateur déplie la pièce
   **Then** les deux badges ont des styles visuellement différents, permettant de distinguer d'un coup d'œil les équipements en exception

5. **AC5 — Rafraîchissement automatique préserve le contexte de navigation**
   **Given** l'utilisateur ayant déplié une ou plusieurs pièces et scrollé dans la page
   **When** le rafraîchissement automatique (intervalle 10s) se déclenche
   **Then** la position de scroll de la fenêtre est restaurée après la mise à jour du DOM
   **And** les pièces précédemment dépliées restent dépliées

6. **AC6 — Rafraîchissement manuel repart de l'état initial**
   **Given** l'utilisateur ayant déplié des pièces
   **When** l'utilisateur clique sur le bouton `Rafraîchir`
   **Then** la console revient à l'état initial : toutes les pièces repliées, aucune restauration d'état

7. **AC7 — Invariants Stories 1.1–1.4 inchangés**
   **Given** la console après implémentation de Story 1.5
   **When** l'utilisateur inspecte le rendu
   **Then** les libellés `Changements à appliquer` restent visibles aux 3 niveaux (global, pièce, équipement) selon les mêmes conditions qu'avant
   **And** les libellés `Hérite de la pièce` et `Exception locale` restent présents sur les équipements concernés
   **And** les compteurs global et par pièce restent corrects
   **And** aucune logique métier n'est introduite côté frontend

## Tasks / Subtasks

- [x] Task 1 — Pliage par défaut et toggle des pièces dans `jeedom2ha_scope_summary.js` (AC: 1, 2)
  - [x] 1.1 La fonction `render()` doit générer les lignes de pièces de manière à ce que chaque pièce produise une ligne synthèse cliquable (nom + compteurs + indicateur toggle) et une ligne de détail équipements masquée par défaut
  - [x] 1.2 Chaque ligne de pièce doit porter l'identifiant de la pièce dans le DOM généré, de sorte que le code de `jeedom2ha.js` puisse associer un clic sur le résumé à la ligne de détail correspondante
  - [x] 1.3 `render()` reste purement génératrice de HTML statique — aucune logique d'événement, d'état ou de toggle dans ce module ; le libellé `Changements à appliquer` doit rester visible dans la ligne synthèse même quand la pièce est repliée

- [x] Task 2 — Gestionnaire de toggle et préservation de l'état de navigation dans `jeedom2ha.js` (AC: 2, 5, 6)
  - [x] 2.1 Ajouter un gestionnaire de clic sur les lignes synthèse de pièces dans `#div_scopeSummaryContent` : un clic affiche ou masque la ligne de détail correspondante
  - [x] 2.2 Avant chaque rafraîchissement automatique (setInterval 10s), capturer en mémoire volatile l'état courant : quelles pièces sont dépliées et la position de scroll de la fenêtre
  - [x] 2.3 Après la mise à jour du DOM par un rafraîchissement automatique, restaurer l'état capturé : redéplier les pièces précédemment dépliées et rétablir la position de scroll
  - [x] 2.4 Le bouton `#bt_refreshScopeSummary` déclenche un rafraîchissement sans restauration d'état : la console revient à l'état initial (toutes pièces repliées)
  - [x] 2.5 La capture et la restauration d'état sont la responsabilité exclusive de `jeedom2ha.js` ; `jeedom2ha_scope_summary.js` ne connaît pas l'état de navigation

- [x] Task 3 — Amélioration visuelle des badges dans `jeedom2ha_scope_summary.js` (AC: 3, 4)
  - [x] 3.1 Dans la fonction de rendu de l'état d'équipement, appliquer un style visuel à `exclude` qui communique un état inactif ou désactivé — distinct du vert `include`, distinct du gris neutre des états par défaut, et sans utiliser la couleur rouge réservée aux incidents d'infrastructure (UX delta review section 9.4)
  - [x] 3.2 Dans la fonction de rendu du détail des équipements, `Exception locale` doit avoir un style visuellement différent de `Hérite de la pièce` pour permettre une lecture immédiate des équipements qui dévient de la règle de leur pièce

- [x] Task 4 — Tests unitaires du présentateur (AC: 1, 2, 3, 4, 7)
  - [x] 4.1 Dans `tests/unit/test_scope_summary_presenter.node.test.js`, mettre à jour les assertions HTML pour refléter la nouvelle structure de rendu des pièces : lignes de détail masquées par défaut, identifiants de pièces présents dans le DOM, indicateur toggle visible
  - [x] 4.2 Ajouter des assertions ciblées vérifiant que le badge `exclude` communique un état inactif sans couleur rouge, et que le badge `Exception locale` est visuellement distinct de `Hérite de la pièce`
  - [x] 4.3 Vérifier la non-régression : `Changements à appliquer` visible aux 3 niveaux, compteurs corrects, `has_contract: false` rendu sans structure pièce — les 8 tests existants doivent passer après mise à jour des assertions structurelles mécaniquement cassées par les nouveaux attributs

## Dev Notes

### Contexte actif et contraintes de cadrage

- Cycle actif obligatoire : **Post-MVP Phase 1 - V1.1 Pilotable**
- Mini-story corrective UX console — action item bloquant avant Epic 2 (rétrospective Epic 1, 2026-03-23)
- Sources actives de vérité :
  - `_bmad-output/planning-artifacts/active-cycle-manifest.md`
  - `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Contexte secondaire utilisé :
  - `_bmad-output/implementation-artifacts/epic-1-retro-2026-03-23.md`
  - `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md`

### Invariants non renégociables

- `published_scope` est le contrat backend canonique — aucune modification backend dans cette story
- Le backend reste la source unique de vérité : compteurs, états, flags pending — lus tels quels, sans recalcul ni agrégat frontend
- `createModel()` n'est pas modifié : le modèle de données reste identique à Story 1.4 ; seule la couche de rendu est concernée
- Les libellés `Changements à appliquer`, `Hérite de la pièce` et `Exception locale` issus des Stories 1.2–1.4 doivent rester fonctionnels et visibles sans altération
- Cette story n'introduit aucun concept d'Epic 2 (santé pont), Epic 3 (statuts/raisons lisibles) ou Epic 4 (opérations HA)

### État réel de la console — constat terrain post-Story 1.4

Trois problèmes concrets ont été identifiés sur la box réelle après la clôture de Story 1.4 :

**Mur d'équipements.** Le rendu actuel affiche en permanence toutes les lignes de détail d'équipements pour toutes les pièces. Avec plusieurs pièces contenant chacune plusieurs équipements, la console devient un scroll interminable sans synthèse intermédiaire, contrairement à la direction UX retenue (Direction 3 — accordéon détail à la demande).

**Badges indiscernables.** L'état `exclude` utilise le même style neutre que `inherit`. Les badges `Exception locale` et `Hérite de la pièce` utilisent également le même style. Il est impossible de distinguer visuellement en un coup d'œil les équipements exclus des inclus, ou les équipements en exception des équipements qui héritent normalement.

**Refresh qui casse le scroll.** Le rafraîchissement automatique toutes les 10 secondes remplace intégralement le contenu du container `#div_scopeSummaryContent`. Cette opération de remplacement DOM remet la position de scroll à zéro et réinitialise tout état visuel, coupant l'utilisateur de sa navigation en cours.

### Direction de conception

Cette story touche deux fichiers JavaScript et leur suite de tests. Le backend, le relai PHP et la structure HTML du conteneur `desktop/php/jeedom2ha.php` ne sont pas modifiés.

**`jeedom2ha_scope_summary.js` — rendu et badges.** Le module de présentation génère du HTML statique. La modification consiste à encoder dans ce HTML les informations nécessaires au toggle (identifiant de pièce, état masqué initial des lignes de détail) et à distinguer visuellement les états et sources de décision. L'interface publique exposée par ce module (`createModel` et `render`) reste inchangée.

**`jeedom2ha.js` — toggle et état de navigation.** La gestion du toggle (clic, masquage/affichage) et la préservation de l'état (scroll, pièces dépliées) relèvent exclusivement de ce fichier. La clé est de séparer le refresh automatique, qui doit restaurer l'état, du refresh manuel, qui doit le réinitialiser.

**Contrainte de palette visuelle.** La spec UX (ux-delta-review section 9.4) fige : "Rouge uniquement pour un incident d'infrastructure." Les états d'équipement ne doivent pas utiliser la couleur rouge (`label-danger`). Le badge `Changements à appliquer` utilise déjà l'orange (`label-warning`), ce qui doit être pris en compte pour éviter toute confusion visuelle avec l'état `exclude`.

### Dev Agent Guardrails

- **Aucune modification backend** : daemon Python, relai PHP (`core/class/`, `core/ajax/`), modèles de données — intacts
- **`createModel()` ne change pas** : le modèle reste identique à Story 1.4 ; les assertions de modèle des tests existants ne doivent pas être touchées
- **Pas de logique métier frontend** : le toggle est purement présentationnel ; les compteurs, états et flags viennent du backend
- **Rouge interdit pour les badges d'état** : `label-danger` ne doit pas être utilisé pour les états d'équipement ou les sources de décision — rouge réservé infrastructure per UX spec
- **`label-warning` déjà occupé** par `Changements à appliquer` — ne pas créer d'ambiguïté en l'utilisant pour `exclude`
- **`Changements à appliquer` ne doit pas régresser** : son rendu aux 3 niveaux (global, pièce, équipement) doit rester identique à Story 1.4 ; en particulier, le badge pièce doit rester visible dans la ligne synthèse même quand la pièce est repliée
- **Interface publique du module `jeedom2ha_scope_summary.js` inchangée** : `{ createModel, render }` reste le seul export

### Previous Story Intelligence — ce que l'Epic 1 a figé

- **Story 1.2** : le pattern de rendu est établi — `createModel()` produit un modèle depuis le payload backend, `render()` génère le HTML, `jeedom2ha.js` injecte dans `#div_scopeSummaryContent`. Le setInterval 10s est dans `jeedom2ha.js`. Aucun recalcul métier frontend.
- **Story 1.3** : a introduit `renderPieceEquipements()` et les badges `Hérite de la pièce` / `Exception locale` dans la zone de rendu du détail. La structure actuelle est deux lignes de tableau par pièce : une ligne résumé (nom + compteurs) et une ligne détail (équipements).
- **Story 1.4** : a introduit le badge `Changements à appliquer` (`label-warning`) aux 3 niveaux. Les tests ont été étendus à 8 cas JS. Les `deepEqual` existants ont été mis à jour mécaniquement pour inclure le nouveau champ avec valeur par défaut — ce même pattern s'applique si la structure HTML change.
- **Leçon critique retro** : les tests automatisés valident les contrats ; seul le terrain révèle la qualité perçue. Cette story est la réponse directe à ce constat.

### Testing Requirements

**Catégorie de couverture requise :** Story 1.5 modifie le rendu visible → **tests UI ciblés obligatoires** (test-strategy V1.1, section 5).

**Tests du présentateur** (`tests/unit/test_scope_summary_presenter.node.test.js`) :
- Les assertions HTML qui vérifient la structure des lignes de pièces vont casser mécaniquement suite aux nouveaux attributs et au masquage par défaut — c'est attendu, pas une régression
- Mettre à jour ces assertions pour refléter le nouveau rendu, puis ajouter des assertions sur les styles visuels des badges `exclude` et `Exception locale`
- Non-régression Story 1.4 : vérifier que `Changements à appliquer` s'affiche aux 3 niveaux selon les mêmes conditions

**Non-régression backend** : les suites Python (`tests/unit/test_published_scope.py`, `tests/unit/test_published_scope_http.py`) ne sont pas touchées par cette story et doivent rester vertes.

**Tests E2E :** non requis pour cette story (correction visuelle sans nouveau contrat backend).

### Project Structure Notes

**Fichiers à modifier :**
- `desktop/js/jeedom2ha_scope_summary.js` — rendu pièces (masquage par défaut, identifiants, toggle affordance) + badges `exclude` et `Exception locale`
- `desktop/js/jeedom2ha.js` — gestionnaire de toggle, capture/restauration d'état de navigation, séparation refresh auto / refresh manuel
- `tests/unit/test_scope_summary_presenter.node.test.js` — mise à jour assertions HTML + nouveaux tests badges

**Fichiers à NE PAS modifier :**
- `resources/daemon/models/published_scope.py`
- `resources/daemon/transport/http_server.py`
- `core/class/jeedom2ha.class.php`
- `core/ajax/jeedom2ha.ajax.php`
- `desktop/php/jeedom2ha.php`

### Dépendances et séquençage

- Dépendances amont : Stories 1.1, 1.2, 1.3, 1.4 (toutes done)
- Dépendances aval : aucune — correctif autonome
- **Bloquant pour Epic 2** : Epic 2 ne démarre qu'après clôture de cette story
- Cette story ne crée aucune dépendance vers Epic 2, 3 ou 4

### Risques / Points de vigilance

- **Tests cassés mécaniquement attendus** : les assertions sur la structure HTML des lignes de pièces vont casser suite aux nouveaux attributs — les mettre à jour est une tâche normale, pas une régression fonctionnelle
- **Badge `Changements à appliquer` dans la ligne résumé** : ce badge doit rester visible même quand la pièce est repliée ; ne pas le déplacer dans la ligne de détail masquée
- **Séparation claire refresh auto / refresh manuel** : le distinguo est comportemental (avec vs sans restauration d'état) — veiller à ce que les deux chemins ne se confondent pas
- **Contrainte palette couleur** : valider que le style retenu pour `exclude` respecte à la fois la distinction avec `include` (vert) et l'absence de rouge (réservé infrastructure)

### Hors scope explicite

| Élément | Raison |
|---------|--------|
| Nom lisible d'équipement (au lieu d'ID brut) | Story backlog distincte — requiert vérification du contrat backend avant implémentation |
| Drill-down commande par commande | Hors scope V1.1 |
| Navigation type Homebridge | Backlog futur optionnel |
| Bandeau santé du pont | Epic 2 |
| Statuts principaux / raisons lisibles / actions recommandées | Epic 3 |
| Bouton `Appliquer à HA`, flux republier / supprimer | Epic 4 |
| Extension du contrat backend `published_scope` | Aucune modification backend dans cette story |
| Nouveau panneau ou écran séparé | Correction de la console existante uniquement |
| Persistance de l'état collapse entre sessions | Hors scope V1.1 |
| Filtres globaux ou vue transversale des équipements | Hors scope cette story |

### References

- Sources actives de vérité :
  - `_bmad-output/planning-artifacts/active-cycle-manifest.md`
  - `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Sources secondaires utilisées :
  - `_bmad-output/implementation-artifacts/epic-1-retro-2026-03-23.md` — action item #1
  - `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md` — sections 2, 9.4, 11
- Points d'ancrage codebase :
  - `desktop/js/jeedom2ha_scope_summary.js` — rendu et badges (fichier principal)
  - `desktop/js/jeedom2ha.js` — toggle, état de navigation (fichier secondaire)
  - `tests/unit/test_scope_summary_presenter.node.test.js` — suite de tests à mettre à jour
  - `desktop/php/jeedom2ha.php` — container HTML de référence (lecture seule)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

Aucun blocage — implémentation directe sans itération.

### Completion Notes List

- **Task 1 (AC1, AC2)** : `render()` dans `jeedom2ha_scope_summary.js` génère désormais deux lignes par pièce — `<tr class="j2ha-piece-summary" data-piece-id="...">` (toujours visible, indicateur toggle `&#9654;`, badge pending inclus) et `<tr class="j2ha-piece-detail" data-piece-id="..." style="display:none;">` (masquée par défaut). Interface publique `{ createModel, render }` inchangée.
- **Task 2 (AC2, AC5, AC6)** : `jeedom2ha.js` ajoute `_captureNavState()` et `_restoreNavState(navState)`. `renderPublishedScopeSummary(result, navState)` accepte l'état de navigation. `refreshPublishedScopeSummary(preserveNavState)` capture l'état avant le rechargement si `preserveNavState=true`. Le `setInterval` 10s passe `true`, le bouton manuel ne passe rien (falsy → réinitialisation). Le toggle est géré par délégation jQuery sur `#div_scopeSummaryContent` — persiste entre les rechargements.
- **Task 3 (AC3, AC4)** : `exclude` → `label label-default` + `style="text-decoration:line-through;"` (inactif/barré, sans rouge, sans vert, sans orange). `Exception locale` → `label label-info` (bleu informatif, distinct du gris neutre `label-default` de `Hérite de la pièce`).
- **Task 4 (AC1–4, AC7)** : 4 nouveaux tests ajoutés (structure accordéon, badge `exclude`, badge `Exception locale` vs `Hérite de la pièce`, badge pending dans ligne synthèse). Les 8 tests existants passent sans modification — les assertions HTML ne ciblaient pas les classes de lignes de tableau, donc aucune casse mécanique.
- **Non-régression** : 12/12 tests JS PASS, 42/42 tests Python PASS.
- **Limites résiduelles** : la restauration de scroll est best-effort (dépend du reflow DOM après chargement) ; aucune persistance entre sessions (hors scope V1.1 explicitement).

### File List

- `desktop/js/jeedom2ha_scope_summary.js`
- `desktop/js/jeedom2ha.js`
- `tests/unit/test_scope_summary_presenter.node.test.js`
- `_bmad-output/implementation-artifacts/1-5-correction-ux-console.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
