# Story 5.5 : Compacité visuelle — reposition et simplification de la colonne Actions dans la table home

Status: done

## Story

En tant qu'utilisateur de la console home,
je veux que la colonne Actions soit positionnée immédiatement après la colonne Écart et que ses libellés soient courts et colorés différemment selon leur intention,
afin de lire la table plus rapidement et d'identifier les actions disponibles sans parcourir toute la ligne.

## Contexte

Constat terrain post-Story 5.1 : la colonne Actions est actuellement la **dernière colonne** du tableau home (position 10), après les cinq colonnes chiffrées (Total / Exclus / Inclus / Publiés / Écarts). Les libellés backend affichés verbatim (`"Créer dans Home Assistant"`, `"Republier dans Home Assistant"`, `"Supprimer de Home Assistant"`) sont trop longs. Le bouton Republier est visuellement identique au bouton Créer (tous deux `btn-success` vert). Ces trois points cumulés nuisent à la lisibilité et à la lecture rapide du tableau.

Cette story est **strictement frontend**. Elle ne touche ni le contrat backend, ni la logique de disponibilité des actions, ni la séparation home vs diagnostic.

## Scope

### In scope

- Déplacement de la colonne `Actions` : de la position 10 (dernière) à la position 5 (immédiatement après `Écart`)
- Simplification des libellés affichés (côté frontend seulement, sans modifier le contrat backend) :
  - `"Créer dans Home Assistant"` → affiché `"Créer"` (vert — `btn-success`)
  - `"Republier dans Home Assistant"` → affiché `"Republier"` (bleu — `btn-primary`)
  - `"Supprimer de Home Assistant"` → affiché `"Supprimer"` (rouge — `btn-danger`)
- Réduction de la densité visuelle des boutons (boutons déjà en `btn-xs` — vérifier l'encombrement réel et ajuster si nécessaire)
- Mise à jour des tests JS existants qui référencent l'ordre des colonnes ou les libellés

### Out of scope

- Tout changement backend
- Tout changement d'endpoint ou de contrat JSON
- Toute nouvelle action ou nouvelle logique de disponibilité
- Toute évolution de la logique de gating (`applyHAGating`)
- Toute refonte structurelle de la home
- Toute dérive vers le diagnostic
- Toute réouverture du modèle 4D
- Toute modification de la story 5.2 (logique de confirmation ou click handlers) — coordination de merge uniquement

## Dépendances

- **Story 5.1** — `done` : `renderActionButtons`, signal `actions_ha`, gating. Cette story n'en altère que le rendu visuel.
- **Story 5.2** — `ready-for-dev` : ajoute un bouton pièce dans `pieceColumns`. Coordination de merge obligatoire si les deux stories sont implémentées en parallèle — voir Dev Notes.

## Acceptance Criteria

### AC 1 — Colonne Actions positionnée immédiatement après Écart

**Given** la table home avec les colonnes standard
**When** un utilisateur charge la page
**Then** l'ordre exact des colonnes est : `Nom | Périmètre | Statut | Écart | Actions | Total | Exclus | Inclus | Publiés | Écarts`
**And** aucune autre colonne ne s'intercale entre `Écart` et `Actions`
**And** le nombre total de colonnes reste 10

### AC 2 — Libellés courts et couleurs différenciées

**Given** un équipement inclus non encore publié (`est_publie_ha = false`)
**When** la ligne équipement est rendue
**Then** le bouton d'action positive affiche `"Créer"` (et non `"Créer dans Home Assistant"`)
**And** ce bouton porte la classe `btn-success` (vert)

**Given** un équipement inclus déjà publié (`est_publie_ha = true`)
**When** la ligne équipement est rendue
**Then** le bouton d'action positive affiche `"Republier"` (et non `"Republier dans Home Assistant"`)
**And** ce bouton porte la classe `btn-primary` (bleu)

**Given** un équipement publié pour lequel l'action supprimer est disponible
**When** la ligne équipement est rendue
**Then** le bouton destructif affiche `"Supprimer"` (et non `"Supprimer de Home Assistant"`)
**And** ce bouton porte la classe `btn-danger` (rouge)

### AC 3 — Lisibilité métier du tableau préservée

**Given** le tableau home chargé avec des équipements
**When** un utilisateur parcourt les lignes
**Then** les colonnes métier `Nom / Périmètre / Statut / Écart` restent les quatre premières colonnes
**And** les colonnes chiffrées `Total / Exclus / Inclus / Publiés / Écarts` restent groupées à droite des Actions
**And** la hiérarchie visuelle parc → pièce → équipement est inchangée

### AC 4 — Actions visuellement secondaires par rapport aux colonnes métier

**Given** le tableau home avec actions affichées
**When** un utilisateur lit une ligne équipement
**Then** les colonnes `Nom`, `Périmètre`, `Statut`, `Écart` restent perceptivement dominantes (typographie, positionnement)
**And** les boutons d'action ne captent pas l'attention en premier sur une ligne standard

### AC 5 — Disponibilité des actions inchangée fonctionnellement

**Given** la matrice de disponibilité établie par Story 5.1 (bridge indisponible, équipement exclu, etc.)
**When** le gating est actif
**Then** les boutons restent désactivés (`disabled`) et les `title` d'indisponibilité sont inchangés
**And** `applyHAGating` continue de s'appliquer sur `[data-ha-action]` sans modification
**And** aucune règle de disponibilité n'est réinterprétée côté frontend

### AC 6 — Compacité visuelle améliorée

**Given** la table home rendue après cette story
**When** un utilisateur compare avec l'état antérieur
**Then** les boutons d'action n'occupent pas plus d'espace horizontal qu'avant (libellés plus courts)
**And** la table reste lisible sans scroll horizontal sur une résolution standard (≥ 1280px)

### AC 7 — Aucune régression sur la séparation home vs diagnostic

**Given** cette story implémentée
**When** un utilisateur utilise la home
**Then** aucun élément de la surface diagnostic n'apparaît dans la table home
**And** les invariants ux-spec §7 restent valides (pas de `Confiance`, pas de `Raison`, pas de `cause_code` visible)

### AC 8 — Gate terrain UX avant done

**Given** la story implémentée et les tests verts
**When** un utilisateur réel charge la console home
**Then** en moins de 3 secondes il repère la colonne Actions à droite d'Écart
**And** il lit les libellés courts sans ambiguïté sur l'intention
**And** il ne confond pas Créer (vert) avec Republier (bleu)

Ce gate est **bloquant avant de passer la story à `done`**.

## Tasks / Subtasks

- [x] Task 1 — Reposition colonne Actions dans le header et les tableaux de colonnes (AC: 1, 3)
  - [x] `renderTableHeader()` (`jeedom2ha_scope_summary.js:361`) : déplacer `<th>Actions</th>` de la position 10 à la position 5 (après `<th>Ecart</th>`)
  - [x] `globalColumns[]` (`jeedom2ha_scope_summary.js:524`) : déplacer le placeholder `''` de l'index 9 à l'index 4
  - [x] `pieceColumns[]` (`jeedom2ha_scope_summary.js:546`) : déplacer le placeholder `''` de l'index 9 à l'index 4
  - [x] `eqColumns[]` (`jeedom2ha_scope_summary.js:568`) : déplacer `renderActionButtons(eq.actions_ha, eq.eq_id)` de l'index 9 à l'index 4
  - [x] Vérifier que `colspan="10"` dans la ligne vide (`jeedom2ha_scope_summary.js:590`) reste correct (10 colonnes inchangé)

- [x] Task 2 — Simplification des libellés et couleur Republier (AC: 2, 6)
  - [x] Dans `renderActionButtons()` (`jeedom2ha_scope_summary.js:487`) : extraire le libellé court de `publier.label` en supprimant le suffixe `" dans Home Assistant"` ou `" de Home Assistant"`
  - [x] Détecter si le libellé court est `"Republier"` → appliquer `btn-primary` au lieu de `btn-success`
  - [x] Détecter si le libellé court est `"Créer"` → conserver `btn-success`
  - [x] Extraire le libellé court de `supprimer.label` en supprimant le suffixe `" de Home Assistant"`
  - [x] S'assurer que `supprimer` conserve `btn-danger` (aucun changement de couleur)
  - [x] Ne pas modifier les attributs `data-ha-action`, `data-eq-id`, ni la logique `disabled`/`title`

- [x] Task 3 — Tests JS (AC: 1, 2, 4, 5)
  - [x] Mettre à jour les tests existants référençant l'index de la colonne Actions ou les libellés verbatim dans `tests/unit/` (chercher `"Créer dans Home Assistant"`, `"Republier dans Home Assistant"`, `"Supprimer de Home Assistant"` dans les fichiers JS de test)
  - [x] Ajouter / mettre à jour un test : `renderTableHeader()` → `Actions` est à la 5e position
  - [x] Ajouter / mettre à jour un test : `renderActionButtons()` avec `label = "Créer dans Home Assistant"` → bouton affiche `"Créer"`, classe `btn-success`
  - [x] Ajouter / mettre à jour un test : `renderActionButtons()` avec `label = "Republier dans Home Assistant"` → bouton affiche `"Republier"`, classe `btn-primary`
  - [x] Ajouter / mettre à jour un test : `renderActionButtons()` avec `label = "Supprimer de Home Assistant"` → bouton affiche `"Supprimer"`, classe `btn-danger`
  - [x] Ajouter un test : bouton `disabled` avec `raison_indisponibilite` → `title` intact même avec libellé court
  - [x] Non-régression : 125 tests JS — 0 régression

- [x] Task 4 — Gate terrain UX (bloquant avant done) (AC: 8)
  - [x] Charger la console home en conditions réelles
  - [x] Vérifier que la colonne Actions est visuellement positionnée juste après Écart
  - [x] Vérifier les trois libellés courts : `Créer` (vert), `Republier` (bleu), `Supprimer` (rouge)
  - [x] Vérifier que les boutons désactivés ont toujours leur `title` d'indisponibilité
  - [x] Valider AC 8 : lecture en moins de 3 secondes, pas de confusion Créer / Republier

## Dev Notes

### Fichiers candidats à la modification

| Couche | Fichier | Modification attendue |
|---|---|---|
| Frontend JS | `desktop/js/jeedom2ha_scope_summary.js` | Reposition colonne (header + 3 tableaux), simplification libellés dans `renderActionButtons()` |
| Frontend CSS | `desktop/css/jeedom2ha.css` | Largeurs colonnes explicites, respiration inter-colonnes, conteneur flex `.j2ha-actions-ha` |
| Tests JS | `tests/unit/` | Mise à jour références index colonne + libellés verbatim |

**Aucun fichier backend** n'est modifié.

### État actuel du code (base pour la modification)

**Header courant** (`jeedom2ha_scope_summary.js:361-372`) :
```
Nom | Perimetre | Statut | Ecart | Total | Exclus | Inclus | Publies | Ecarts | Actions
                                                                                 ↑ pos 10
```

**Header cible** :
```
Nom | Perimetre | Statut | Ecart | Actions | Total | Exclus | Inclus | Publies | Ecarts
                                  ↑ pos 5
```

**`renderActionButtons()` courant** (ligne 487) :
- `publier.label` affiché tel quel depuis le backend → `"Créer dans Home Assistant"` ou `"Republier dans Home Assistant"`
- `supprimer.label` affiché tel quel → `"Supprimer de Home Assistant"`
- `publier` : toujours `btn-success` (vert), même quand le label est "Republier dans Home Assistant"

**Labels backend connus** (établis par Story 5.1, ne pas modifier) :
- `actions_ha.publier.label` = `"Créer dans Home Assistant"` quand `est_publie_ha = false`
- `actions_ha.publier.label` = `"Republier dans Home Assistant"` quand `est_publie_ha = true`
- `actions_ha.supprimer.label` = `"Supprimer de Home Assistant"` (invariant)

**Stratégie de simplification recommandée** : extraction du préfixe connu (avant ` dans` / ` de`), sans regex fragile. Exemple :

```js
function shortLabel(label) {
  var idx = label.indexOf(' dans ');
  if (idx >= 0) return label.substring(0, idx);
  idx = label.indexOf(' de ');
  if (idx >= 0) return label.substring(0, idx);
  return label;
}
```

Détecter `"Republier"` dans le libellé court pour appliquer `btn-primary`.

### Coordination avec Story 5.2

Story 5.2 (`ready-for-dev`) ajoute un bouton "Republier la pièce" dans `pieceColumns` (Task 3 de Story 5.2). Ce bouton est actuellement placé à l'index 9 (placeholder `''`). Après Story 5.5, ce placeholder passe à l'index 4.

**Si les deux stories sont implémentées en parallèle** → le merge de Story 5.2 doit utiliser l'index 4 (pas l'index 9) pour le bouton pièce.  
**Si Story 5.5 est fusionnée en premier** → Story 5.2 doit adapter son diff en conséquence (simple rebase).  
**Recommandation** : merger Story 5.5 avant Story 5.2 pour éviter les conflits sur `pieceColumns`.

### Guardrails — anti-dérive

- Ne pas toucher `applyHAGating` (`jeedom2ha.js:126`) — la logique de gating est hors scope
- Ne pas modifier les `data-ha-action` attributes — ils sont les points d'accroche du gating
- Ne pas modifier la logique `disponible` / `raison_indisponibilite`
- Ne pas modifier le contrat JSON retourné par `/system/diagnostics`
- Ne pas introduire de recalcul local de label côté frontend (le backend reste source de vérité)
- La simplification du libellé est **display-only** : le `data-ha-action` doit rester `"publier"` et non `"creer"` ou `"republier"`

### Guardrails UX

- La table reste 10 colonnes — la lisibilité métier repose sur cet ensemble
- Les colonnes `Nom / Périmètre / Statut / Écart` restent les 4 premières (piliers de lecture)
- La colonne `Actions` reste visuellement secondaire : boutons compacts (`btn-xs`), pas de surcharge typographique
- Aucun élément appartenant à la surface diagnostic (Confiance, Raison, cause_code) ne doit apparaître
- Les invariants ux-spec §7 restent valides après cette story

### Invariants à couvrir (non-régression)

- **I10** — Frontend en lecture seule pour le contrat backend (les libellés courts sont du display, pas du recalcul)
- **I4** — Backend source unique du contrat `actions_ha`
- Séparation home vs diagnostic (ux-spec §4)

### Project Structure Notes

- Tout le rendu de la table home passe par `jeedom2ha_scope_summary.js` — un seul fichier à modifier
- `desktop/js/jeedom2ha.js` n'est pas modifié (gating et click handlers globaux hors scope)
- `desktop/php/jeedom2ha.php` n'est pas modifié

### References

- [Source: `desktop/js/jeedom2ha_scope_summary.js:361-372`] — `renderTableHeader()` — header courant avec Actions en dernière position
- [Source: `desktop/js/jeedom2ha_scope_summary.js:487-510`] — `renderActionButtons()` — rendu courant avec libellés verbatim backend
- [Source: `desktop/js/jeedom2ha_scope_summary.js:524-535`] — `globalColumns[]` — placeholder Actions à l'index 9
- [Source: `desktop/js/jeedom2ha_scope_summary.js:546-557`] — `pieceColumns[]` — placeholder Actions à l'index 9
- [Source: `desktop/js/jeedom2ha_scope_summary.js:568-579`] — `eqColumns[]` — `renderActionButtons` à l'index 9
- [Source: `desktop/js/jeedom2ha_scope_summary.js:590`] — `colspan="10"` — invariant colonnes total
- [Source: `desktop/js/jeedom2ha.js:126`] — `applyHAGating` — logique de gating (hors scope, ne pas modifier)
- [Source: `resources/daemon/tests/unit/test_story_5_1_actions_ha.py:17-56`] — labels backend contractuels
- [Source: `_bmad-output/planning-artifacts/ux-spec.md#§4.1 Exclusif home`] — colonnes home contractuelles
- [Source: `_bmad-output/planning-artifacts/ux-spec.md#§7 Invariants visuels`] — invariants UX
- [Source: `_bmad-output/planning-artifacts/ux-spec.md#§10 Checklist terrain`] — critères gate UX

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Task 1 : `renderTableHeader()` — `<th>Actions</th>` déplacé position 10 → 5 (après Écart). `globalColumns[]`, `pieceColumns[]`, `eqColumns[]` : placeholder/renderActionButtons déplacés index 9 → 4. `colspan="10"` inchangé (10 colonnes).
- Task 2 : Helper `shortLabel()` ajouté (extraction préfixe avant ` dans ` / ` de `). `renderActionButtons()` utilise le libellé court pour l'affichage. `Republier` → `btn-primary`, `Créer` → `btn-success`, `Supprimer` → `btn-danger`. `data-ha-action`, `disabled`, `title` inchangés.
- Task 3 : Regex ordre colonnes mise à jour dans `test_scope_summary_presenter` et `test_story_4_5_home_landing`. Tests 5.1 libellés verbatim mis à jour → assertions sur libellés courts. 5 nouveaux tests Story 5.5 ajoutés. 125/125 tests — 0 régression.
- Task 4 : Gate terrain UX — à valider manuellement en conditions réelles (bloquant avant `done`).
- `renderTableHeader` ajouté aux exports publics du module pour permettre les tests unitaires.
- **Post-gate micro-polish (3 irritants UX)** : (1) `renderRoomStatusBadge` + `renderEquipmentStatutBadge` — `margin-right:6px` ajouté à tous les badges statut pour espacer de la colonne Écart. (2) + (3) `renderActionButtons` — conteneur passé en `display:flex;align-items:center;gap:6px;padding-right:8px;` pour alignement vertical et respiration droite. 125/125 JS PASS.

### File List

- `desktop/js/jeedom2ha_scope_summary.js`
- `desktop/css/jeedom2ha.css`
- `tests/unit/test_story_5_1_actions_ha_frontend.node.test.js`
- `tests/unit/test_scope_summary_presenter.node.test.js`
- `tests/unit/test_story_4_5_home_landing.node.test.js`

## Change Log

- 2026-04-06 — Story 5.5 implémentée : reposition colonne Actions (pos 10 → 5), libellés courts affichés (Créer/Republier/Supprimer), Republier en btn-primary. 125/125 JS PASS. Gate terrain UX en attente.
- 2026-04-06 — Micro-polish UX post-gate : espacement badges Statut/Écart (margin-right:6px), flexbox + gap sur conteneur actions, padding-right:8px respiration droite. 125/125 JS PASS.
- 2026-04-06 — Code review (Opus 4.6) : 0 HIGH, 1 MEDIUM corrigé (desktop/css/jeedom2ha.css ajouté à File List + Dev Notes). 125/125 JS PASS. Statut maintenu review (gate terrain AC 8 en attente).
- 2026-04-06 — **Gate terrain UX — PASS** : séparation visuelle colonnes métier rétablie ; colonne Actions positionnée juste après Écart ; badges Créer/Republier/Supprimer lisibles sans collage perceptif ; colonne Actions visuellement secondaire ; alignement jugé satisfaisant. Story passée `done`.
