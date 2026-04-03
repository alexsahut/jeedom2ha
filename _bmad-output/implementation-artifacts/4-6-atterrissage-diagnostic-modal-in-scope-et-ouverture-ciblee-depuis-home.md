# Story 4.6 : Atterrissage diagnostic — modal in-scope et ouverture ciblée depuis la home

Status: done

Epic: Epic 4 — Recadrage UX : modèle utilisateur Périmètre / Statut / Écart / Cause (correctif prioritaire post-rétro)

## Story

En tant qu'utilisateur du diagnostic V1.1,  
je veux retrouver la grande modal diagnostic existante comme surface séparée d'explicabilité détaillée des cas inclus, avec une ouverture ciblée depuis la home,  
afin d'analyser un cas sans que le diagnostic redevienne une seconde home.

## Contexte / Objectif produit

Cette story referme le paquet minimal correctif Epic 4 en restaurant **la responsabilité de la surface diagnostic** et le flux obligatoire home -> diagnostic.

Constat verrouillé :

1. La grande modal diagnostic existe déjà dans `desktop/js/jeedom2ha.js` et doit être **réutilisée**, pas remplacée.
2. Le diagnostic doit rester :
   - une liste filtrable ;
   - limitée aux équipements in-scope (`perimetre = inclus`) ;
   - repliée par défaut à l'entrée générale ;
   - ancrée sur la logique diagnostic actuelle pour la colonne `Statut`.
3. Le détail commandes actuel est explicitement conservé tel quel.
4. Le flux depuis la home est contractuel :
   - même modal ;
   - ciblage de l'équipement ;
   - scroll ;
   - dépliage ;
   - focus temporaire visible.
5. Le `Statut` synthétique de pièce porté par la home reste une information **home-only** et ne doit pas contaminer la modal diagnostic.

## Objectif produit

Faire percevoir immédiatement que :

- `diagnostic = explicabilite detaillee des cas du perimetre inclus` ;
- le diagnostic ne remonte ni la synthèse du parc, ni les exclus, ni la santé globale ;
- un clic sur `Ecart` dans la home amène visiblement au bon cas.

## Scope

### In scope

1. Réutilisation de la grande modal diagnostic existante.
2. Entrée générale via le bouton `Diagnostic` du plugin :
   - même modal ;
   - liste filtrable ;
   - uniquement les équipements in-scope ;
   - lignes repliées par défaut.
3. Colonnes diagnostic exactes et ordonnées : `Piece / Nom / Ecart / Statut / Confiance / Raison`.
4. Préservation de la logique diagnostic actuelle pour la colonne `Statut`.
5. Préservation du détail commandes existant tel quel au dépliage.
6. Ouverture ciblée depuis la home :
   - même modal ;
   - équipement ciblé ;
   - scroll automatique ;
   - dépliage automatique ;
   - focus temporaire visible.
7. Fallback propre si l'équipement ciblé n'est pas trouvable dans la population in-scope : ouverture générale sans état incohérent.

### Out of scope

| Élément hors scope | Responsable / remarque |
|---|---|
| Refonte du shell home ou du tableau hiérarchique home | Story 4.5 |
| Nouvelle page diagnostic séparée du modal existant | Interdit |
| Réintroduction des exclus dans le diagnostic standard | Interdit |
| Ajout de bandeau santé, compteurs globaux ou synthèse de parc dans le diagnostic | Interdit |
| Remap de la colonne `Statut` diagnostic vers la logique home | Interdit |
| Réutilisation du `Statut` synthétique de pièce home dans la modal diagnostic | Interdit |
| Refonte du détail commandes existant | Interdit |
| Refonte du contrat 4D, du filtrage in-scope backend ou de l'export support | Hors scope, acquis Epic 4 |
| Toute logique Epic 5 | Epic 5 gelé |

## Dépendances autorisées

- Story 4.3 — `done` : population in-scope, confiance réservée au diagnostic, export complet préservé.
- Story 4.4 — `done` : contrat UI 4D déjà intégré côté UI.
- Story 4.5 — `ready-for-dev` : point d'entrée badge `Ecart` home borné et stable ; le `Statut` synthétique de pièce reste borné à la home et n'est pas consommé par 4.6.
- `ux-spec.md` V3 — référence d'acceptation principale.

Aucune dépendance Epic 5.  
Aucune dépendance backend nouvelle n'est requise par défaut pour le ciblage : `eq_id`, la modal existante et la population in-scope sont déjà disponibles.

## Acceptance Criteria

### AC 1 — Entrée générale = même modal diagnostic, liste filtrable, repliée

**Given** l'utilisateur clique sur `Diagnostic` dans le plugin  
**When** le diagnostic s'ouvre  
**Then** il s'ouvre dans la grande modal existante `Diagnostic de Couverture`  
**And** il affiche :
- une zone `Recherche / filtres`
- un tableau principal
- uniquement les équipements in-scope

**And** toutes les lignes sont repliées par défaut à l'ouverture générale

### AC 2 — Colonnes diagnostic exactes et ordre figé

**Given** la vue générale du diagnostic  
**When** le tableau principal est affiché  
**Then** les colonnes sont exactement :
- `Piece`
- `Nom`
- `Ecart`
- `Statut`
- `Confiance`
- `Raison`

**And** aucun compteur global, aucune synthèse parc et aucun bandeau `Sante` n'apparaissent dans la modal

### AC 3 — Colonne `Statut` diagnostic préservée

**Given** une ligne diagnostic  
**When** la colonne `Statut` est affichée  
**Then** elle conserve la logique diagnostic actuelle  
**And** elle n'est pas remappée artificiellement vers la logique synthétique de la home  
**And** aucun signal `Statut` synthétique de pièce propre à la home n'est injecté dans la modal

### AC 4 — Détail commandes existant conservé tel quel

**Given** une ligne diagnostic dépliée  
**When** l'utilisateur ouvre le détail  
**Then** le détail commandes existant est affiché tel quel  
**And** aucune surcouche de résumé n'est injectée au-dessus  
**And** aucun nouveau bloc théorique de cas n'est ajouté

### AC 5 — Invariant in-scope-only maintenu

**Given** un équipement exclu visible en home  
**When** l'utilisateur ouvre le diagnostic standard  
**Then** cet équipement n'apparaît pas dans la liste principale du diagnostic  
**And** la modal continue de ne porter que sur les équipements inclus

### AC 6 — Ouverture ciblée contractuelle depuis la home

**Given** l'utilisateur clique sur le badge `Ecart` d'un équipement home  
**When** le diagnostic s'ouvre  
**Then** c'est la **même modal diagnostic** que l'entrée générale  
**And** la ligne correspondant à l'`eq_id` ciblé est rendue visible  
**And** la modal scrolle automatiquement jusqu'à cette ligne si nécessaire  
**And** la ligne est dépliée automatiquement  
**And** une mise en évidence visuelle temporaire est appliquée à la ligne cible

### AC 7 — Fallback propre si la cible n'est pas trouvée

**Given** un clic home porte une cible absente de la population in-scope  
**When** le diagnostic s'ouvre  
**Then** la modal s'ouvre en mode général  
**And** aucune erreur JS n'est levée  
**And** aucun état de focus incohérent n'est laissé à l'écran

### AC 8 — Repli par défaut conservé hors arrivée ciblée

**Given** l'utilisateur ouvre le diagnostic par le bouton général  
**When** la modal apparaît ou qu'une recherche filtre la liste  
**Then** aucune ligne ne reste ouverte par défaut  
**And** le dépliage reste un choix utilisateur tant qu'il n'y a pas d'arrivée ciblée

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [ ] Task 1 — Reprendre la modal diagnostic existante sans recréer de surface (AC: 1, 2, 8)
  - [ ] Identifier dans `desktop/js/jeedom2ha.js` le flux d'ouverture actuel de `Diagnostic de Couverture`.
  - [ ] Le refactorer pour accepter un mode d'ouverture général et un mode d'ouverture ciblé, tout en gardant la même modal.
  - [ ] Préserver la recherche / filtres et la largeur actuelle de la grande modal.

- [ ] Task 2 — Réaligner le tableau principal diagnostic sur `ux-spec.md` V3 (AC: 1, 2, 3, 5)
  - [ ] Vérifier que la population affichée reste strictement `in_scope_equipments`.
  - [ ] Mettre les colonnes dans l'ordre contractuel `Piece / Nom / Ecart / Statut / Confiance / Raison`.
  - [ ] Conserver la logique de statut actuelle du diagnostic au lieu de la remapper vers la home.
  - [ ] Refuser toute reprise du signal synthétique `Statut` pièce porté par la home dans la modal diagnostic.
  - [ ] Vérifier que ni les exclus, ni les compteurs home, ni la santé globale ne réapparaissent dans la modal.

- [ ] Task 3 — Préserver le détail commandes existant (AC: 4)
  - [ ] Conserver le comportement de dépliage actuel par ligne.
  - [ ] Réutiliser `buildDetailRow(eq)` et le contenu de détail existant comme base à préserver.
  - [ ] Refuser tout ajout de bloc résumé, de carte intermédiaire ou de reconstruction théorique au-dessus du détail.

- [ ] Task 4 — Implémenter l'ouverture ciblée depuis la home (AC: 6, 7)
  - [ ] Consommer l'identifiant cible porté par la Story 4.5.
  - [ ] À l'ouverture ciblée :
    - retrouver la ligne concernée ;
    - ouvrir la même modal ;
    - scroller vers la ligne ;
    - déplier la ligne ;
    - appliquer un focus temporaire visible puis l'effacer proprement.
  - [ ] Gérer explicitement le fallback si la cible n'est pas présente.

- [ ] Task 5 — Tests story-level et gate terrain (AC: 1 à 8)
  - [ ] Ajouter les tests automatisés nécessaires sur le rendu/tableau diagnostic, la population in-scope, la logique de repli, le ciblage et le fallback.
  - [ ] Si la structure actuelle de `desktop/js/jeedom2ha.js` bloque la testabilité, extraire **uniquement** les helpers purs de rendu/targeting nécessaires dans un module JS voisin, sans recréer l'architecture UI.
  - [ ] Exécuter la checklist terrain `ux-spec.md` section 10.2 sur :
    - séparation perçue home / diagnostic ;
    - compréhension immédiate de la modal comme surface d'analyse ;
    - retour immédiat au cas ciblé depuis la home.

## Dev Notes

### Contraintes `ux-spec.md` à intégrer explicitement

1. `diagnostic = explicabilite detaillee des cas du perimetre inclus`.
2. Le diagnostic standard montre uniquement les équipements inclus.
3. La grande modal existante est conservée.
4. Les colonnes diagnostic sont figées et ordonnées.
5. La colonne `Statut` du diagnostic conserve sa logique actuelle.
6. Toutes les lignes sont repliées par défaut à l'entrée générale.
7. Le détail commandes existant est conservé tel quel.
8. Le clic badge `Ecart` home doit ouvrir la même modal, avec scroll, dépliage et focus temporaire visibles.
9. Le `Statut` synthétique de pièce appartient à la home ; il n'apparaît jamais dans la modal diagnostic.

### Notes d'architecture / design

1. Le flux modal actuel vit déjà dans `desktop/js/jeedom2ha.js` ; il faut le refactorer, pas le remplacer.
2. Les données nécessaires au ciblage existent déjà :
   - `eq_id`
   - population `in_scope_equipments`
   - détails diagnostic par équipement
3. Le ciblage home -> diagnostic peut donc être traité côté frontend sans rouvrir le contrat 4D ni créer une mini-story backend dédiée.
4. Le détail actuel (`buildDetailRow`) constitue la base à préserver ; tout redesign théorique est interdit.
5. La séparation home / diagnostic doit être assurée par le contenu visible et par le comportement d'ouverture, pas par une duplication de surfaces.
6. Le signal synthétique `Statut` pièce éventuellement introduit/clarifié par 4.5 ne doit pas être repris par la modal ; la modal conserve sa propre sémantique de `Statut`.

### Previous Story Intelligence

1. Story 4.3 a déjà figé le diagnostic in-scope et la confiance réservée au diagnostic.
2. Story 4.4 a gardé la couche technique utile (`status_code`, `reason_code`, `matched_commands`, `unmatched_commands`) ; cette story doit la **reloger dans la bonne surface**, pas la supprimer.
3. La modal existante dispose déjà :
   - d'une recherche ;
   - d'un tableau ;
   - d'un accordéon par ligne ;
   - d'une largeur adaptée grand écran.

### Git Intelligence Summary

- `e2c59a8 feat(story-4.4): integrer l'UI du nouveau modele console et diagnostic`
- `8c57808 feat(story-4.3): freeze tested terrain candidate`

Lecture utile :
- 4.3 a verrouillé la population in-scope ;
- 4.4 a conservé le détail technique utile ;
- le correctif à faire ici porte sur le **message dominant**, la structure de colonnes et le flux de ciblage, pas sur le pipeline backend.

## Impacts backend vs frontend

| Couche | Impact attendu | Fichiers candidats |
|---|---|---|
| Frontend JS | Refactor du flux modal, colonnes diagnostic, ciblage scroll/depliage/focus, fallback | `desktop/js/jeedom2ha.js` |
| Frontend JS secondaire | Aucun changement majeur attendu, hors éventuels attributs cibles déjà fournis par 4.5 | `desktop/js/jeedom2ha_scope_summary.js` |
| PHP relay | Aucun changement attendu par défaut | `core/ajax/jeedom2ha.ajax.php` |
| Backend Python | Aucun changement attendu par défaut | `resources/daemon/transport/http_server.py` |
| Tests JS | Nouveaux tests diagnostic ciblé + non-régression modal existante | `tests/unit/` |

## Stratégie de test story-level

### Invariants à couvrir

- I14 — diagnostic utilisateur filtré in-scope.
- I15 — confiance visible uniquement en diagnostic.
- I17 — pas d'interprétation frontend du contrat métier.
- Le `Statut` synthétique de pièce home reste absent de la modal diagnostic.
- Invariants `ux-spec.md` sections 5, 6.4, 6.5, 6.6, 7, 8.

### Tests unitaires / UI ciblés obligatoires

- Ouverture générale : même modal, lignes repliées, aucun exclu affiché.
- Colonnes exactes et ordonnées.
- Colonne `Statut` diagnostic inchangée dans sa logique.
- Aucun `Statut` synthétique de pièce home n'apparaît dans la modal.
- Aucun bandeau santé, compteur global ou synthèse home dans la modal.
- Détail commandes existant conservé sans bloc résumé ajouté.
- Ouverture ciblée : target trouvé, scroll, dépliage, focus temporaire.
- Fallback cible absente : ouverture générale propre, sans erreur JS.

### Tests de non-régression obligatoires

- La recherche/filtrage actuelle de la modal continue de fonctionner.
- Les lignes restent repliées par défaut hors arrivée ciblée.
- Les exclus restent absents du diagnostic standard.
- Le détail commandes existant n'est pas remplacé.

### Gate terrain obligatoire avant `done`

- Vérifier la checklist `ux-spec.md` section 10.2 pour la modal diagnostic.
- Vérifier en terrain :
  - qu'un utilisateur comprend que le diagnostic est une surface distincte ;
  - qu'il retrouve immédiatement le cas cible depuis la home ;
  - qu'il ne perçoit pas de duplication confuse avec la home.

## Guardrails anti-dérive

1. Pas de nouvelle page ou sous-surface diagnostic théorique.
2. Pas de réapparition des exclus dans le diagnostic standard.
3. Pas de santé globale ou de synthèse parc dans la modal.
4. Pas de remap du `Statut` diagnostic vers la logique home.
5. Pas de réemploi du `Statut` synthétique de pièce home dans la modal.
6. Pas de refonte du détail commandes existant.
7. Pas de dépendance Epic 5.
8. Pas de backend refactor si le frontend peut cibler proprement avec `eq_id`.
9. Pas de focus invisible : si le ciblage ne peut pas être perçu, la story n'est pas conforme.

## Définition de done

- [ ] AC 1 à AC 8 validés.
- [ ] L'entrée générale ouvre la même modal, repliée par défaut.
- [ ] Les colonnes diagnostic sont exactes et ordonnées.
- [ ] Les exclus restent absents du diagnostic standard.
- [ ] Le détail commandes existant est conservé tel quel.
- [ ] Le clic badge `Ecart` home retrouve visiblement le bon cas avec scroll, dépliage et focus temporaire.
- [ ] Le fallback cible absente est propre et sans erreur.
- [ ] La checklist terrain `ux-spec.md` section 10.2 est positive avant `done`.

## References

- `_bmad-output/planning-artifacts/active-cycle-manifest.md` — sections 4, 6, 8.
- `_bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md` — sections 6, 8.1, 8.3, 9, 12.
- `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md` — sections 5.6, 8.3, 8.4.
- `_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md` — sections 8.3, 8.5, 8.6, 8.7.
- `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md` — sections 4, 5, 6, 7, 9.
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-29.md` — sections 4, 6, 8.
- `_bmad-output/implementation-artifacts/epic-4-retro-2026-03-29.md` — sections `Verdict`, `AI-2`, `AI-3`, `Chemin critique validé`, `Évaluation de readiness`.
- `_bmad-output/implementation-artifacts/4-4-integration-ui-du-nouveau-modele-console-et-diagnostic.md` — sections `Contrat de surfaces UI`, `Impact backend vs frontend`, `Stratégie de test story-level`, `Guardrails anti-dérive`.
- `_bmad-output/planning-artifacts/ux-spec.md` — sections 2, 3.2, 4.2, 4.3, 5.1, 5.2, 5.3, 6.4, 6.5, 6.6, 7, 8, 9.2, 10, 11, 12.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — bloc Epic 4 post-rétro.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4.6

### Debug Log References

- `node --check desktop/js/jeedom2ha_diagnostic_helpers.js` (PASS)
- `node --check desktop/js/jeedom2ha.js` (PASS)
- `node --test tests/unit/test_story_4_6_diagnostic_modal.node.test.js` (PASS — 19/19)
- `node --test tests/unit/test_story_4_6_diagnostic_modal.node.test.js tests/unit/test_scope_summary_presenter.node.test.js tests/unit/test_story_4_4_integration_ui_4d.node.test.js tests/unit/test_story_4_5_home_landing.node.test.js tests/unit/test_story_4_2_vocab_exclusion.node.test.js tests/unit/test_story_4_3_diagnostic_in_scope.node.test.js tests/unit/test_story_3_4_ai5_frontend_passthrough.node.test.js` (PASS — 63/63)
- Micro-fix highlight CSS (2026-04-03) : `node --test …/test_story_4_6_diagnostic_modal.node.test.js … (PASS — 63/63)`

### Completion Notes List

- Nouveau module pur `desktop/js/jeedom2ha_diagnostic_helpers.js` : `filterInScopeEquipments`, `getDiagnosticColumns`, `getEcartBadgeHtml`, `findTargetEquipmentIndex`.
- `desktop/js/jeedom2ha.js` — refactor du modal diagnostic : filtre in-scope, 6 colonnes `Piece|Nom|Ecart|Statut|Confiance|Raison`, `data-eq-id` sur chaque ligne, Raison lisible sans reason_code interne, colspan 5→6 dans buildDetailRow (conservé tel quel).
- Ouverture ciblée depuis la home : consomme `window.jeedom2haHomeDiagnosticTarget`, scroll + dépliage + highlight temporaire `j2ha-diag-target-highlight` (2,5 s), fallback propre si cible absente.
- `desktop/css/jeedom2ha.css` : ajout de `.j2ha-diag-target-highlight` (fond jaune clair, transition 0,5 s).
- `desktop/php/jeedom2ha.php` : inclusion du nouveau module helpers avant `jeedom2ha.js`.
- 19 tests Story 4.6 PASS ; 63/63 total suite PASS (non-régression 4.2/4.3/4.4/4.5 OK).
- Gate terrain obligatoire avant done : checklist ux-spec.md section 10.2 à exécuter.
- Micro-fix highlight (2026-04-03) : cause racine = `background-color` posé sur `<tr>` recouvert par les `<td>` Bootstrap/Jeedom ; transition non jouée au retrait car portée par la classe supprimée. Fix CSS-only : `#div_diagnosticTable td { transition: background-color 0.5s; }` + `.j2ha-diag-target-highlight > td { background-color: #fff9c4 !important; }`. Aucun changement JS. 63/63 PASS.

### File List

- `desktop/js/jeedom2ha_diagnostic_helpers.js` (nouveau)
- `desktop/js/jeedom2ha.js`
- `desktop/css/jeedom2ha.css`
- `desktop/php/jeedom2ha.php`
- `tests/unit/test_story_4_6_diagnostic_modal.node.test.js` (nouveau)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/4-6-atterrissage-diagnostic-modal-in-scope-et-ouverture-ciblee-depuis-home.md`
