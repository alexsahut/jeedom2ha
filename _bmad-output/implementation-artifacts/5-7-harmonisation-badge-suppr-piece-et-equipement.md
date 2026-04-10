# Story 5.7 : Harmonisation badge « Suppr. » pièce et équipement

Status: done

## Story

En tant qu'utilisateur Jeedom,
je veux que le badge de suppression ait la même apparence visuelle — libellé, tooltip, couleur et taille — sur les lignes pièce et les lignes équipement,
afin de ne pas percevoir d'incohérence entre les deux niveaux de l'interface.

## Contexte / Objectif produit

Dette UX identifiée post-Story 5.3 : le badge Supprimer s'affiche différemment selon le niveau d'affichage.

| Dimension | Niveau équipement | Niveau pièce | Cohérent ? |
|---|---|---|---|
| Libellé | **"Supprimer"** (via `shortLabel` → coupe à `" de "`) | **"Suppr."** (hardcodé) | ❌ |
| Tooltip | Absent | Absent | — (les deux manquent) |
| Classe Bootstrap couleur | `btn-danger` | `btn-danger` | ✅ |
| Classe Bootstrap taille | `btn-xs` | `btn-xs` | ✅ |
| Classe délégation JS | `j2ha-action-ha-btn` | `j2ha-piece-action-btn` | Intentionnel ✅ |

**Deux problèmes à corriger :** libellé incohérent + tooltip absent sur les deux niveaux.  
**Une différence intentionnelle à conserver :** la classe de délégation JS (`j2ha-action-ha-btn` vs `j2ha-piece-action-btn`) — elle sert à router les click handlers vers des blocs distincts dans `jeedom2ha.js`. Ne pas unifier ces classes.

**Invariant architectural** : aucun recalcul métier dans le frontend. Le contrat backend reste source de vérité. Cette story ne touche qu'à la présentation (libellé + tooltip).

## Périmètre

### Ce que harmonise cette story (checklist complète)

| Propriété du badge | Avant | Après | Commentaire |
|---|---|---|---|
| Libellé affiché | Équipement: "Supprimer" / Pièce: "Suppr." | Les deux: "Suppr." | Unifié via `shortLabel` |
| Tooltip | Absent sur les deux | Les deux: "Supprimer de Home Assistant" | Ajouté uniquement sur l'état nominal (`disponible=true`) |
| Classe couleur Bootstrap | `btn-danger` (les deux) | `btn-danger` (les deux) | Déjà cohérent — inchangé |
| Classe taille Bootstrap | `btn-xs` (les deux) | `btn-xs` (les deux) | Déjà cohérent — inchangé |
| Classe délégation JS | `j2ha-action-ha-btn` / `j2ha-piece-action-btn` | Inchangé | Différence intentionnelle — routing click handlers |
| Rendu quand `disponible=false` | Bouton masqué (équipement, fix Story 5.3) | Inchangé | Non rouvert |
| CSS disabled / gated | `cursor:not-allowed; opacity:0.5` (Story 5.6) | Inchangé | Non rouvert |

### In scope

1. **`shortLabel()` dans `desktop/js/jeedom2ha_scope_summary.js`** — ajouter le cas `"Supprimer"` → `"Suppr."` dans une table de raccourcis. `shortLabel` est la **source de vérité unique du libellé court "Suppr."** — elle ne centralise pas l'ensemble du composant badge (classes CSS, attributs data, délégation), seulement la transformation de label.
2. **`renderPieceSupprimerButton(piece)`** — remplacer le label hardcodé `"Suppr."` par `shortLabel('Supprimer de Home Assistant')` ; ajouter `title="Supprimer de Home Assistant"` sur le bouton nominal (rendu uniquement si `counts.publies > 0`).
3. **`renderActionButtons(actionsHa, eqId)`** — ajouter `title="` + `escapeHtml(supprimer.label)` + `"` sur le bouton Supprimer (chemin nominal uniquement — `supprimer.disponible === true`). Le libellé court "Suppr." est produit automatiquement via `shortLabel` déjà appelé ligne 516.
4. **Export de `renderPieceActionButtons`** — voir position explicite ci-dessous.
5. **Tests JS** — mettre à jour l'assertion existante `'>Supprimer<'` → `'>Suppr.<'` ; ajouter assertions tooltip.

### Position sur l'export `renderPieceActionButtons`

**Décision : exporter `renderPieceActionButtons`.**

Justification :
- `renderPieceSupprimerButton` est interne. Tester le badge pièce via `render()` obligerait à construire un modèle complet avec topology, counts, statuts 4D — coût de setup disproportionné pour un test de label/tooltip.
- `renderPieceActionButtons` est déjà appelée par `render()` — l'exporter n'ajoute **aucun comportement** au runtime. La surface publique du module s'élargit d'une fonction, mais sans effet de bord.
- Les consommateurs runtime (code Jeedom frontend) n'utilisent que `render()` — l'export n'a pas d'impact observable en production.
- Conclusion : export minimal, justifié, impact nul côté production.

### Out of scope

| Élément | Responsable |
|---|---|
| Backend `actions_ha.py` / `http_server.py` | Hors scope — aucun changement backend |
| `_LABEL_SUPPRIMER` dans `actions_ha.py` | Figé : "Supprimer de Home Assistant" |
| Logique de publication / suppression | Invariant acquis Epic 5 |
| Flux de confirmation (modale, textes) | Story 5.3 — ne pas toucher |
| Autres boutons (`publier`, `republier`) | Hors scope |
| CSS disabled / gated | Story 5.6 — règles déjà en place, ne pas rouvrir |
| Tooltip sur badge en état disabled/gated | Story 5.6 — `raison_indisponibilite` sur `publier` déjà géré, `supprimer` masqué quand `disponible=false` — aucun tooltip à ajouter dans cet état |

## Acceptance Criteria

**AC 1 — Libellé équipement : "Suppr."**
**Given** un équipement inclus avec `supprimer.disponible = true`
**When** `renderActionButtons` génère le HTML du badge Supprimer
**Then** le bouton contient le texte `>Suppr.<`
**And** ne contient plus `>Supprimer<`

**AC 2 — Libellé pièce : "Suppr." via source unifiée**
**Given** une pièce avec `counts.publies > 0`
**When** `renderPieceActionButtons` (ou `render()`) génère le HTML du badge Supprimer de la pièce
**Then** le bouton contient le texte `>Suppr.<`
**And** ce libellé est produit par `shortLabel('Supprimer de Home Assistant')` — non hardcodé dans la string de retour

**AC 3 — Tooltip badge équipement (état nominal uniquement)**
**Given** un équipement inclus avec `supprimer.disponible = true` et `supprimer.label = "Supprimer de Home Assistant"`
**When** le badge est rendu par `renderActionButtons`
**Then** le bouton porte l'attribut `title="Supprimer de Home Assistant"`
*Note : cet AC couvre uniquement le chemin nominal. Le comportement de l'état gated/disabled est régi par Story 5.6 et inchangé.*

**AC 4 — Tooltip badge pièce (état nominal uniquement)**
**Given** une pièce avec `counts.publies > 0`
**When** `renderPieceSupprimerButton` génère le HTML
**Then** le bouton porte l'attribut `title="Supprimer de Home Assistant"`
*Note : même périmètre que AC 3 — tooltip uniquement sur le badge rendu en nominal.*

**AC 5 — Homogénéité visuelle Bootstrap pièce ↔ équipement**
**Given** les badges Supprimer rendus au niveau pièce et au niveau équipement
**When** on inspecte les classes CSS présentes sur les deux boutons
**Then** les deux portent exactement `btn btn-xs btn-danger`
**And** aucun des deux ne porte une classe de taille ou de couleur différente
*Note d'invariant : la différence de classe de délégation (`j2ha-action-ha-btn` vs `j2ha-piece-action-btn`) est intentionnelle et doit être conservée.*

**AC 6 — États disabled/masqués inchangés**
**Given** un équipement avec `supprimer.disponible = false`
**When** `renderActionButtons` est appelé
**Then** le bouton Supprimer n'est pas rendu (comportement Story 5.3 bug fix — inchangé)
**And** `applyHAGating` continue de gater les boutons rendus lors d'un bridge down (invariant Story 2.3 — inchangé)
**And** les règles CSS Story 5.6 (`cursor:not-allowed; opacity:0.5`) restent inchangées

**AC 7 — Gate terrain PASS**
**Given** les fichiers JS déployés sur la box Jeedom réelle
**When** la page plugin est ouverte
**Then** les badges Supprimer affichent « Suppr. » sur les lignes pièce ET équipement
**And** un survol du badge affiche le tooltip « Supprimer de Home Assistant »
**And** les classes visuelles `btn-danger btn-xs` sont identiques sur les deux niveaux

**AC 8 — Baseline tests maintenue**
**Given** les changements de cette story
**When** la suite de tests est exécutée
**Then** ≥ 270 pytest PASS, 0 fail
**And** ≥ 145 JS PASS, 0 fail (incluant les tests mis à jour et nouveaux)

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Sélectionner le mode selon l'objectif de la story :
    - Déploiement JS sans redémarrage daemon (cas nominal pour un micro-correctif visuel) : `./scripts/deploy-to-box.sh`
    - Si la box nécessite un redémarrage explicite : `./scripts/deploy-to-box.sh --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.`

- [x] Task 1 — Étendre `shortLabel` pour "Supprimer" → "Suppr." (AC 1, 2)
  - [x] Dans `desktop/js/jeedom2ha_scope_summary.js`, modifier `shortLabel` en ajoutant une `LABEL_SHORT_MAP` :
    ```js
    function shortLabel(label) {
      var LABEL_SHORT_MAP = { 'Supprimer': 'Suppr.' };
      var result = label;
      var idx = label.indexOf(' dans ');
      if (idx >= 0) result = label.substring(0, idx);
      else { idx = label.indexOf(' de '); if (idx >= 0) result = label.substring(0, idx); }
      return LABEL_SHORT_MAP[result] || result;
    }
    ```
  - [x] `LABEL_SHORT_MAP` déclarée à l'intérieur de `shortLabel` — ne pas polluer le scope de la closure ou le scope global
  - [x] Vérifier que "Créer dans Home Assistant" → "Créer" et "Republier dans Home Assistant" → "Republier" sont inchangés

- [x] Task 2 — Ajouter tooltip sur le badge Supprimer équipement (AC 3)
  - [x] Dans `renderActionButtons` (ligne ~514), sur le bouton `data-ha-action="supprimer"`, ajouter `title` :
    ```js
    if (supprimer && supprimer.label && supprimer.disponible) {
      html += '<button class="btn btn-xs btn-danger j2ha-action-ha-btn" data-ha-action="supprimer"'
        + ' data-eq-id="' + escapeHtml(String(eqId)) + '"'
        + ' title="' + escapeHtml(supprimer.label) + '"'
        + '>' + escapeHtml(shortLabel(supprimer.label)) + '</button>';
    }
    ```
  - [x] Le tooltip utilise `supprimer.label` (valeur backend) — pas une constante locale (invariant I17)
  - [x] Ce chemin n'est atteint que si `supprimer.disponible === true` — pas de tooltip en état disabled/masqué

- [x] Task 3 — Unifier la source du label dans `renderPieceSupprimerButton` + tooltip (AC 2, 4)
  - [x] Remplacer le label hardcodé par `shortLabel('Supprimer de Home Assistant')` :
    ```js
    function renderPieceSupprimerButton(piece) {
      var publies = (piece && piece.counts && isFiniteNumber(piece.counts.publies)) ? piece.counts.publies : 0;
      if (publies <= 0) { return ''; }
      var label = shortLabel('Supprimer de Home Assistant');
      return ' <button class="btn btn-xs btn-danger j2ha-piece-action-btn" data-ha-action="supprimer"'
        + ' data-portee="piece"'
        + ' data-piece-id="' + escapeHtml(String(piece.object_id)) + '"'
        + ' data-piece-name="' + escapeHtml(piece.object_name) + '"'
        + ' data-piece-publies="' + escapeHtml(String(publies)) + '"'
        + ' title="Supprimer de Home Assistant"'
        + '>' + escapeHtml(label) + '</button>';
    }
    ```
  - [x] Le tooltip pièce est hardcodé `"Supprimer de Home Assistant"` car la pièce ne reçoit pas d'objet `actions_ha` — pas de `supprimer.label` disponible à ce niveau
  - [x] Classes CSS conservées identiques : `btn btn-xs btn-danger j2ha-piece-action-btn` (pas de changement)

- [x] Task 4 — Exporter `renderPieceActionButtons` (AC 8, testabilité)
  - [x] Ajouter `renderPieceActionButtons: renderPieceActionButtons,` dans le bloc `return { ... }` (ligne ~640)
  - [x] Ne pas exporter `renderPieceSupprimerButton` individuellement (reste interne à la closure)
  - [x] Justification documentée : permet des tests unitaires ciblés du badge pièce sans construire un modèle complet pour `render()` ; impact nul sur les consommateurs runtime qui utilisent uniquement `render()`

- [x] Task 5 — Mettre à jour les tests JS existants et ajouter les nouvelles assertions (AC 1–5, 8)
  - [x] **`tests/unit/test_story_5_1_actions_ha_frontend.node.test.js`** (describe `5.5 / AC2`, ligne ~205) :
    - Remplacer : `assert.ok(html.includes('>Supprimer<'), 'Libellé court "Supprimer" attendu')`
    - Par : `assert.ok(html.includes('>Suppr.<'), 'Libellé court "Suppr." attendu')`
    - Ajouter : `assert.ok(html.includes('title="Supprimer de Home Assistant"'), 'Tooltip badge Supprimer attendu')`
  - [x] Créer **`tests/unit/test_story_5_7_badge_suppr_harmonie.node.test.js`** :
    - `shortLabel('Supprimer de Home Assistant')` → `"Suppr."` (test unitaire helper, source de vérité)
    - `shortLabel('Créer dans Home Assistant')` → `"Créer"` (non-régression)
    - `shortLabel('Republier dans Home Assistant')` → `"Republier"` (non-régression)
    - `renderActionButtons` badge Supprimer nominal : `>Suppr.<` présent, `title="Supprimer de Home Assistant"` présent, classe `btn-danger` présente
    - `renderActionButtons` avec `supprimer.disponible = false` : `data-ha-action="supprimer"` absent (AC 6 — non-régression masquage)
    - `renderPieceActionButtons` badge Supprimer nominal (`counts.publies > 0`) : `>Suppr.<` présent, `title="Supprimer de Home Assistant"` présent, classe `btn-danger` présente
    - `renderPieceActionButtons` sans publiés (`counts.publies = 0`) : `data-ha-action="supprimer"` absent

- [x] Task 6 — Validation non-régression (AC 8)
  - [x] `node --test tests/unit/*.node.test.js` → ≥ 145 PASS, 0 FAIL — **153 PASS obtenu**
  - [x] `python3 -m pytest resources/daemon/tests/ -q` → ≥ 270 PASS, 0 FAIL — **270 PASS obtenu**

- [x] Task 7 — Gate terrain (AC 7 — bloquant avant done)
  - [x] Déployer : `./scripts/deploy-to-box.sh`
  - [x] Ouvrir le plugin Jeedom2HA dans Jeedom
  - [x] Vérifier badge équipement : libellé "Suppr." visible, classes `btn-danger btn-xs`
  - [x] Vérifier badge pièce : libellé "Suppr." visible, classes `btn-danger btn-xs`
  - [x] Vérifier tooltip badge équipement : survol → "Supprimer de Home Assistant"
  - [x] Vérifier tooltip badge pièce : survol → "Supprimer de Home Assistant"
  - [x] Vérifier états disabled/bridge down : comportement inchangé (AC 6)

## Dev Notes

### Diagnostic précis — pourquoi "Supprimer" au lieu de "Suppr." au niveau équipement

```js
// shortLabel actuel (ligne 487)
function shortLabel(label) {
  var idx = label.indexOf(' dans ');
  if (idx >= 0) return label.substring(0, idx);    // "Créer dans HA" → "Créer" ✅
  idx = label.indexOf(' de ');
  if (idx >= 0) return label.substring(0, idx);    // "Supprimer de HA" → "Supprimer" ← bug
  return label;
}
// _LABEL_SUPPRIMER (backend) = "Supprimer de Home Assistant"
// Résultat actuel : "Supprimer" → doit devenir "Suppr."
```

### Source de vérité unique — périmètre exact

`shortLabel` est la **source de vérité unique de la transformation `"Supprimer"` → `"Suppr."`**.  
Elle NE centralise PAS :
- les classes CSS du badge (chaque fonction garde ses propres classes `btn btn-xs btn-danger`)
- les attributs `data-*` (propres à chaque contexte : `data-eq-id` vs `data-piece-id`)
- la classe de délégation JS (intentionnellement différente)
- la disponibilité ou la visibilité du badge

Ce que `shortLabel` fait exactement : prend un label backend complet et retourne sa forme abrégée pour l'affichage. C'est une fonction de présentation pure.

### Tooltip — périmètre exact (nominal uniquement)

Le tooltip `title="Supprimer de Home Assistant"` est ajouté **uniquement sur le badge rendu en état nominal** (`disponible=true`).

- **Équipement** : le badge n'est rendu que si `supprimer.disponible === true` (Story 5.3 bug fix) → le tooltip est donc toujours sur un badge actif.
- **Pièce** : le badge n'est rendu que si `counts.publies > 0` → même garantie.

**Ce que cette story NE rouvre PAS** (Story 5.6, figé) :
- Tooltip sur bouton `publier` disabled avec `raison_indisponibilite` — déjà en place
- CSS `cursor:not-allowed; opacity:0.5` sur `.j2ha-action-ha-btn[disabled]` et `.j2ha-ha-gated` — inchangé
- Gating via `applyHAGating` — inchangé

### Différences intentionnelles conservées

| Propriété | Équipement | Pièce | Raison |
|---|---|---|---|
| Classe délégation | `j2ha-action-ha-btn` | `j2ha-piece-action-btn` | Routing click handlers distincts dans `jeedom2ha.js` (lignes 544-589 équipement, 591-620 pièce) |
| Attribut `title` source | `escapeHtml(supprimer.label)` (valeur backend) | Hardcodé `"Supprimer de Home Assistant"` | La pièce ne reçoit pas d'objet `actions_ha` — pas de `supprimer.label` disponible |

### Invariants à respecter

- **I17** — Frontend en lecture seule : aucun recalcul de disponibilité. `shortLabel` est purement présentationnelle.
- **Story 5.3 bug fix** — masquage du badge Supprimer quand `disponible=false` : non modifié.
- **Story 5.6** — règles CSS disabled/gated : non modifiées.
- **`shortLabel` non-régression** — "Créer dans HA" → "Créer", "Republier dans HA" → "Republier" inchangés.
- **Classe de délégation** — `j2ha-action-ha-btn` (équipement) et `j2ha-piece-action-btn` (pièce) : non unifiées.

### Fichiers à toucher

| Fichier | Modification |
|---|---|
| `desktop/js/jeedom2ha_scope_summary.js` | `shortLabel` (+ LABEL_SHORT_MAP) ; `renderActionButtons` (+ tooltip) ; `renderPieceSupprimerButton` (source unifiée + tooltip) ; export `renderPieceActionButtons` |
| `tests/unit/test_story_5_1_actions_ha_frontend.node.test.js` | Ligne ~210 : assertion "Supprimer" → "Suppr." + assertion tooltip |
| `tests/unit/test_story_5_7_badge_suppr_harmonie.node.test.js` | Nouveau fichier |

**Ne pas toucher :**
- `resources/daemon/models/actions_ha.py` — `_LABEL_SUPPRIMER` reste "Supprimer de Home Assistant"
- `resources/daemon/transport/http_server.py` — aucun changement backend
- `desktop/css/jeedom2ha.css` — règles disabled Story 5.6 en place
- `desktop/js/jeedom2ha.js` — handlers confirmation forte Story 5.3 en place

### Dev Agent Guardrails

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Guardrail — Ne pas recalculer la disponibilité en frontend

`supprimer.disponible` est lu exclusivement depuis le contrat backend. Ne jamais ajouter de condition type `if (est_publie_ha)` ou `if (counts.publies > 0)` dans `renderActionButtons` — ce calcul n'appartient pas à cette story.

### Guardrail — `shortLabel` : modifier mais pas casser

Le test describe `5.5 / AC2` dans `test_story_5_1_actions_ha_frontend.node.test.js` couvre trois cas : "Créer", "Republier", "Supprimer". Seule l'assertion sur "Supprimer" est à mettre à jour (`'>Supprimer<'` → `'>Suppr.<'`). Les deux autres doivent passer sans modification.

### Guardrail — Ne pas unifier les classes de délégation

Ne pas remplacer `j2ha-piece-action-btn` par `j2ha-action-ha-btn` sur le badge pièce. Les deux classes sont des sélecteurs de délégation distincts dans `jeedom2ha.js` — les fusionner casserait le routing des click handlers.

### Project Structure Notes

- `jeedom2ha_scope_summary.js` : pattern UMD/IIFE — `LABEL_SHORT_MAP` déclarée à l'intérieur de `shortLabel`, pas dans la closure parente ni en global
- `renderPieceActionButtons` (ligne ~548) appelle `renderPieceSupprimerButton` et `renderPiecePublishButton` — son export est le point d'entrée de test recommandé pour le badge pièce
- Tests JS : style `describe` + `it` + `assert.ok` — voir `test_story_5_1_actions_ha_frontend.node.test.js` lignes 182-228 pour le pattern exact à reproduire

### References

- [Source: `desktop/js/jeedom2ha_scope_summary.js#487-493`] — `shortLabel` actuel
- [Source: `desktop/js/jeedom2ha_scope_summary.js#497-520`] — `renderActionButtons` (ligne 514 : badge équipement)
- [Source: `desktop/js/jeedom2ha_scope_summary.js#534-546`] — `renderPieceSupprimerButton` (label hardcodé actuel)
- [Source: `desktop/js/jeedom2ha_scope_summary.js#548-553`] — `renderPieceActionButtons` (à exporter)
- [Source: `desktop/js/jeedom2ha_scope_summary.js#640-650`] — exports du module
- [Source: `desktop/js/jeedom2ha.js#544-620`] — click handlers Supprimer équipement et pièce (classes de délégation)
- [Source: `resources/daemon/models/actions_ha.py#16`] — `_LABEL_SUPPRIMER = "Supprimer de Home Assistant"`
- [Source: `tests/unit/test_story_5_1_actions_ha_frontend.node.test.js#205-213`] — assertion à mettre à jour

## Dev Agent Record

### Code Review

- 2026-04-08 — APPROVE — claude-sonnet-4-6 — micro-story frontend UX/UI uniquement, scope conforme, 0 finding bloquant, gate terrain PASS confirmé

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- ✅ Task 1 : `shortLabel` étendue via `LABEL_SHORT_MAP = { 'Supprimer': 'Suppr.' }` déclarée en local dans la fonction. Non-régression "Créer" et "Republier" vérifiée par tests.
- ✅ Task 2 : `renderActionButtons` — `title="<supprimer.label>"` ajouté sur le chemin nominal uniquement (`supprimer.disponible === true`). Invariant I17 respecté (valeur backend directe, pas de constante locale).
- ✅ Task 3 : `renderPieceSupprimerButton` — label hardcodé remplacé par `shortLabel('Supprimer de Home Assistant')` ; `title="Supprimer de Home Assistant"` ajouté (hardcodé car la pièce ne reçoit pas `actions_ha`).
- ✅ Task 4 : `renderPieceActionButtons` exportée depuis le bloc `return {}`. Aucun impact runtime (consommateurs utilisent uniquement `render()`).
- ✅ Task 5 : assertion `'>Supprimer<'` → `'>Suppr.<'` + assertion tooltip ajoutées dans `test_story_5_1_actions_ha_frontend`. Nouveau fichier `test_story_5_7_badge_suppr_harmonie.node.test.js` créé (14 tests couvrant AC 1–6).
- ✅ Task 6 : 153 JS PASS (≥ 145 ✅), 270 pytest PASS (≥ 270 ✅), 0 régression.
- ✅ Task 0 : dry-run PASS (SSH OK, 1 fichier concerné) ; `deploy-to-box.sh` terminé avec `Deploy complete.` — sync backend : 278 eq, 81 eligibles, 30 publiés.
- ✅ Task 7 : gate terrain PASS 2026-04-08 — badge équipement "Suppr." + tooltip OK, badge pièce "Suppr." + tooltip OK, classes `btn-danger btn-xs` identiques, états disabled/bridge down inchangés.

### File List

- `desktop/js/jeedom2ha_scope_summary.js` — `shortLabel` (+LABEL_SHORT_MAP) ; `renderActionButtons` (+tooltip supprimer) ; `renderPieceSupprimerButton` (shortLabel + tooltip) ; export `renderPieceActionButtons`
- `tests/unit/test_story_5_1_actions_ha_frontend.node.test.js` — assertion "Supprimer"→"Suppr." + tooltip
- `tests/unit/test_story_5_7_badge_suppr_harmonie.node.test.js` — nouveau (14 tests Story 5.7)

## Change Log

- 2026-04-08 — Implémentation Story 5.7 : harmonisation badge Suppr. pièce ↔ équipement — shortLabel LABEL_SHORT_MAP, tooltip nominal, export renderPieceActionButtons, 14 nouveaux tests (153 JS PASS, 270 pytest PASS)
