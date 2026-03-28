# Story 4.2 : Vocabulaire d'exclusion par source — disparition du concept exception

Status: done

## Story

En tant qu'utilisateur Jeedom,
je veux que les exclusions soient exprimées par leur source (pièce, plugin, équipement),
afin de comprendre immédiatement qui a exclu cet équipement, sans vocabulaire d'héritage ni d'exception.

## Dépendances autorisées

- **Story 1.1** (done) — resolver canonique `inherit/include/exclude`, `effective_state`, `has_pending_home_assistant_changes`.
- **Story 1.3** (done) — exclusions équipement et visibilité des exclus dans la console.
- **Story 4.1** (done — PR #52) — contrat 4D backend : champs `perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action` par équipement dans `/system/diagnostics` + champ `compteurs` dans `payload.summary` et chaque entrée `payload.rooms`.

Aucune dépendance en avant. Story 4.3 et Story 4.4 peuvent s'appuyer sur le vocabulaire stabilisé ici.

## Acceptance Criteria

### AC 1 — Badge source d'exclusion : exclu_par_piece

**Given** un équipement avec `perimetre` = `exclu_par_piece` dans le contrat diagnostics (Story 4.1)
**When** la console l'affiche dans la liste d'équipements d'une pièce
**Then** le badge affiché est `Exclu par la pièce`
**And** les termes `Hérite de la pièce`, `Exception locale`, `inherit`, `decision_source` n'apparaissent pas dans le HTML rendu

### AC 2 — Badge source d'exclusion : exclu_sur_equipement

**Given** un équipement avec `perimetre` = `exclu_sur_equipement` dans le contrat diagnostics
**When** la console l'affiche
**Then** le badge affiché est `Exclu sur cet équipement`

### AC 3 — Badge source d'exclusion : exclu_par_plugin

**Given** un équipement avec `perimetre` = `exclu_par_plugin` dans le contrat diagnostics
**When** la console l'affiche
**Then** le badge affiché est `Exclu par le plugin`

### AC 4 — Équipement inclus : aucun badge source d'exclusion

**Given** un équipement avec `perimetre` = `inclus` dans le contrat diagnostics
**When** la console l'affiche
**Then** aucun badge source d'exclusion n'est rendu (la source d'exclusion ne s'applique pas aux équipements inclus)

### AC 5 — Audit de la famille "exception / héritage" dans la synthèse périmètre

**Given** la surface `jeedom2ha_scope_summary.js` — synthèse périmètre (compteurs globaux, tableau pièces, liste équipements par pièce)
**When** l'ensemble des termes visibles générés par ce fichier est audité
**Then** aucun des termes de la **famille exception/héritage** n'est présent :
  - `Hérite de la pièce` (ancienne terminologie héritage)
  - `Exception locale` (ancienne terminologie exception)
  - `Exceptions` (en tant que libellé de compteur ou en-tête de colonne)
  - `is_exception` (champ technique interne)
  - `decision_source` (champ technique interne)
**And** ces termes n'apparaissent pas non plus dans les attributs HTML ou les classes CSS dynamiques générées par ce fichier

> **Portée et limites de cet AC :**
> — Surface couverte : `jeedom2ha_scope_summary.js` uniquement. Le panneau diagnostic utilisateur (filtrage in-scope, confiance) est hors scope de 4.2 et sera traité par Story 4.3.
> — Autres termes interdits §6.2 hors scope de 4.2 : `include`/`exclude` en anglais dans `renderEquipmentState`, `Ambigu`/`Partiellement publié`/`Non supporté` dans `getAggregatedStatusLabel` — ces termes subsistent intentionnellement dans des fonctions non modifiées par cette story. Ils seront éliminés par Stories 4.3 et 4.4. Story 4.2 ne les adresse pas et ne prétend pas les adresser.

### AC 6 — Compteurs canoniques : remplacement de Exceptions par Écarts

**Given** les compteurs par pièce ou globaux affichés dans la console
**When** ils sont rendus
**Then** le compteur `Exceptions` n'existe pas (ni colonne, ni stat globale)
**And** les quatre compteurs affichés sont strictement : `Total`, `Inclus`, `Exclus`, `Écarts`
**And** les valeurs proviennent du champ `compteurs` du contrat diagnostics 4.1 (`compteurs.total`, `compteurs.inclus`, `compteurs.exclus`, `compteurs.ecarts`) — jamais calculées localement par le frontend

### AC 7 — Graceful degradation : daemon indisponible

**Given** le daemon est arrêté (`diagnostic_rooms` et `diagnostic_summary` sont vides/null)
**When** la console affiche le périmètre
**Then** les compteurs `Total`, `Inclus`, `Exclus` sont affichés depuis le fallback scope (anciens champs `include`/`exclude`)
**And** `Écarts` affiche `—` (non disponible sans diagnostics)
**And** aucun badge `perimetre_label` n'est affiché (absence normale sans données diagnostics)
**And** aucun terme interdit n'apparaît malgré le fallback

### AC 8 — Non-régression des tests

**Given** la migration de vocabulaire JS
**When** la suite de tests complète est exécutée
**Then** les tests JS passent (tous — nombre à ajuster après migration, attendu ~73 ou + selon les nouveaux tests créés)
**And** la suite de tests pytest complète passe (aucun fichier Python modifié par cette story — baseline indicatif au moment de la story : 169 tests)
**And** aucun test ne référence `is_exception`, `decision_source`, `exceptions` (compteur), `Hérite de la pièce`, `Exception locale` dans ses assertions ou ses fixtures

## Tasks / Subtasks

- [x] Task 1 — Remplacer `buildDecisionSourceLabel` par `buildPerimetreLabel` dans `jeedom2ha_scope_summary.js` (AC 1, 2, 3, 4, 5)
  - [x] 1.1 Supprimer la fonction `buildDecisionSourceLabel(decisionSource, isException)` entièrement
  - [x] 1.2 Créer la fonction `buildPerimetreLabel(perimetre)` (table de correspondance pure — voir Dev Notes) :
    - `"exclu_par_piece"` → `"Exclu par la pièce"`
    - `"exclu_par_plugin"` → `"Exclu par le plugin"`
    - `"exclu_sur_equipement"` → `"Exclu sur cet équipement"`
    - `"inclus"` ou toute autre valeur ou chaîne vide → `""` (pas de badge)
  - [x] 1.3 Dans `buildEquipmentModel(entry, equipDiag)` :
    - Supprimer la lecture de `entry.decision_source` et `entry.is_exception`
    - Supprimer le champ `decision_source_label` du modèle équipement retourné
    - Ajouter `perimetre_label: buildPerimetreLabel(readString(diag.perimetre, ''))` — `perimetre` est lu depuis `eqDiag` (le contrat diagnostics 4D fourni par Story 4.1, déjà passé en paramètre `equipDiag`)
  - [x] 1.4 Dans `renderPieceEquipements()` :
    - Remplacer le bloc conditionnel `if (equipement.decision_source_label !== '')` par `if (equipement.perimetre_label !== '')`
    - Supprimer toute la logique `isException` qui conditionnait le style du badge (`label-info` vs fond gris)
    - Appliquer un style badge uniforme pour tous les badges source d'exclusion (gris neutre, style identique à l'ancienne variante "Hérite de la pièce", sans différenciation par type)
    - Utiliser `escapeHtml(equipement.perimetre_label)` pour le contenu du badge

- [x] Task 2 — Migrer les compteurs vers le contrat diagnostics 4.1 (AC 6, 7)
  - [x] 2.1 Créer la fonction `buildCompteurs(rawCompteurs)` qui lit les clés `total`, `inclus`, `exclus`, `ecarts` depuis la structure `compteurs` du contrat diagnostics (Story 4.1) — retourne `{ total, inclus, exclus, ecarts }` avec `null` si la valeur est absente
  - [x] 2.2 Créer la fonction `buildCompteursFallback(rawScopeCounts)` qui adapte l'ancienne structure scope pour le cas daemon-down : `total` ← `rawScopeCounts.total`, `inclus` ← `rawScopeCounts.include`, `exclus` ← `rawScopeCounts.exclude`, `ecarts` ← `null` (non disponible sans diagnostics)
  - [x] 2.3 Dans `createModel()`, lors de la boucle sur `diagRooms`, extraire également `dr.compteurs` en parallèle du `dr.summary` déjà extrait — stocker dans un index `diagRoomCompteursByObjectId` indexé par `object_id` (même logique de normalisation que pour `diagRoomByObjectId`)
  - [x] 2.4 Dans la construction de `normalizedPiece` (boucle pieces) :
    - Récupérer `var diagCompteurs = diagRoomCompteursByObjectId[String(piece.object_id)] || null`
    - Calculer `counts: diagCompteurs ? buildCompteurs(diagCompteurs) : buildCompteursFallback(piece.counts)`
  - [x] 2.5 Dans le `return` de `createModel()` :
    - Calculer `global_counts` en priorité depuis `diagSummary && diagSummary.compteurs` (global compteurs ajouté par Story 4.1 Task 3.3)
    - Fallback : `buildCompteursFallback(globalSection.counts)` si `diagSummary.compteurs` est absent

- [x] Task 3 — Mettre à jour le rendu HTML (AC 5, 6)
  - [x] 3.1 Dans `render()`, ligne globale stats : remplacer `renderStat('Exceptions', model.global_counts.exceptions)` → `renderStat('Écarts', model.global_counts.ecarts)`
  - [x] 3.2 Dans `render()`, en-tête tableau pièces : remplacer `'<th style="width:110px;">{{Exceptions}}</th>'` → `'<th style="width:110px;">{{Écarts}}</th>'`
  - [x] 3.3 Dans la boucle de rendu des pièces : remplacer `toDisplayCount(piece.counts.exceptions)` → `toDisplayCount(piece.counts.ecarts)`
  - [x] 3.4 Mettre à jour les références aux clés du modèle : `model.global_counts.include` → `.inclus`, `.exclude` → `.exclus` dans les appels `renderStat` existants (lignes `renderStat('Inclus', ...)` et `renderStat('Exclus', ...)`)
  - [x] 3.5 Mettre à jour la colonne pièce : `toDisplayCount(piece.counts.include)` → `.inclus`, `piece.counts.exclude` → `.exclus`
  - [x] 3.6 Vérifier dans tout le fichier JS que les chaînes `"exceptions"` (minuscule), `"Exceptions"`, `"Exception"`, `"is_exception"`, `"decision_source"`, `"Hérite de la pièce"`, `"Exception locale"` n'apparaissent plus dans le code actif (peuvent subsister dans des commentaires historiques datés — acceptable uniquement si clairement marqués comme supprimés)

- [x] Task 4 — Mettre à jour les tests existants (AC 8)
  - [x] 4.1 Dans `tests/unit/test_scope_summary_presenter.node.test.js` :
    - Supprimer le test `"story-1.5: badge Exception locale visuellement distinct de Hérite de la pièce"` (ligne ~357) — il teste un comportement désormais interdit
    - Dans tous les payloads de test (`response` fixtures), supprimer les champs `is_exception` et `decision_source` des entrées `equipements`
    - Supprimer le champ `exceptions` des structures `counts` dans les fixtures scope
    - Ajouter le champ `perimetre` dans `diagEquipments` / `diagnostic_rooms[i]` pour les équipements exclus (valeurs : `exclu_par_piece`, `exclu_par_plugin`, `exclu_sur_equipement` selon le cas)
    - Ajouter le champ `compteurs: { total, inclus, exclus, ecarts }` dans les entrées de `diagnostic_rooms` et dans `diagnostic_summary`
    - Mettre à jour les assertions : remplacer `assert.match(html, /Hérite de la pièce/)` par `assert.match(html, /Exclu par la pièce/)` et `assert.match(html, /Exception locale/)` par `assert.match(html, /Exclu sur cet équipement/)` (ou `doesNotMatch` là où on veut s'assurer de l'absence)
    - Ajouter pour chaque test existant une assertion `assert.doesNotMatch(html, /[Ee]xception/)` pour fixer l'invariant no-exception
  - [x] 4.2 Dans `tests/unit/test_story_3_4_ai5_frontend_passthrough.node.test.js` :
    - Supprimer les champs `is_exception` et `decision_source` des fixtures équipements (ils ne font plus partie du contrat consommé)
    - Supprimer le champ `exceptions` des structures `counts` scope
    - Ajouter `compteurs` dans `diagnostic_summary` et `diagnostic_rooms` si le test en a besoin pour les assertions de compteurs
    - Vérifier la non-régression : ces tests vérifient le passthrough lecture seule du contrat métier backend (status_code, detail, remediation, v1_limitation) — ce comportement doit rester intact

- [x] Task 5 — Créer `tests/unit/test_story_4_2_vocab_exclusion.node.test.js` (AC 1–6, 8)
  - [x] 5.1 Test unitaire `buildPerimetreLabel` — 5 cas :
    - `"exclu_par_piece"` → `"Exclu par la pièce"`
    - `"exclu_par_plugin"` → `"Exclu par le plugin"`
    - `"exclu_sur_equipement"` → `"Exclu sur cet équipement"`
    - `"inclus"` → `""` (pas de badge)
    - `""` → `""` (fallback sécuritaire)
  - [x] 5.2 Test invariant no-exception — payload complet avec équipements exclus et inclus → vérifier que le HTML rendu ne contient pas les chaînes : `"Exception locale"`, `"Hérite de la pièce"`, `"Exceptions"` (header ou stat), `"is_exception"`, `"decision_source"`
  - [x] 5.3 Test compteurs canoniques — payload avec `compteurs: { total: 5, inclus: 3, exclus: 2, ecarts: 1 }` dans `diagnostic_summary` et `diagnostic_rooms` → vérifier que `Écarts` apparaît dans le rendu, `Exceptions` n'apparaît pas
  - [x] 5.4 Test graceful degradation (daemon down) — payload sans `diagnostic_summary.compteurs` (null/absent) → vérifier que le rendu n'échoue pas et n'affiche pas de terme interdit
  - [x] 5.5 Test badge style uniforme — équipement `exclu_par_piece` et équipement `exclu_sur_equipement` → les deux utilisent le même style badge (pas de `label-info` conditionnel selon le type d'exclusion)

- [x] Task 6 — Exécuter la suite de tests complète (AC 8)
  - [x] 6.1 `node --test tests/unit/*.node.test.js` → tous les tests JS PASS (81/81)
  - [x] 6.2 `pytest resources/daemon/tests/` → suite complète PASS sans régression — 173 passed (aucun fichier Python modifié)

## Dev Notes

### Périmètre strict de Story 4.2

Cette story est **exclusivement frontend JavaScript + tests unitaires JS**. Elle ne touche à aucun fichier Python, PHP, template Jinja, ni fichier de configuration.

| Frontière | Story 4.2 | Responsable |
|---|---|---|
| Contrat backend 4D (`perimetre`, `statut`, `ecart`, `cause_*`) | **Lecture seule — figé Story 4.1** | — |
| Affichage badge `statut` binaire (Publié / Non publié) | **Hors scope** | Story 4.4 |
| Affichage indicateur écart + `cause_label` | **Hors scope** | Story 4.4 |
| Refonte complète de l'affichage équipement (4 dimensions) | **Hors scope** | Story 4.4 |
| Filtrage diagnostic in-scope (`perimetre = inclus` côté backend) | **Hors scope** | Story 4.3 |
| Traitement de `Partiellement publié` | **Hors scope** | Story 4.3 |
| Vocabulaire `Ambigu`, `Non supporté` dans `getAggregatedStatusLabel` | **Hors scope** | Story 4.4 |
| Opérations HA (Republier, Supprimer/Recréer) | **Hors scope** | Epic 5 |
| `taxonomy.py`, `aggregation.py`, `published_scope.py` | **Lecture seule — figés** | — |
| `cause_mapping.py`, `ui_contract_4d.py`, `http_server.py` | **Lecture seule — figés Story 4.1** | — |

### Contrat API vs Story 4.2 — frontend uniquement

**Story 4.2 est une story purement frontend. Aucun changement backend n'est attendu.**

Le contrat API — champs `perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action` par équipement, et `compteurs` par pièce et global — a été **produit et figé par Story 4.1**. La réponse `/system/diagnostics` expose déjà ces valeurs correctement.

Les AC de l'epic amont (Story 4.2 dans `epics-post-mvp-v1-1-pilotable.md`) formulent certains critères côté contrat API (`perimetre` = `exclu_par_piece`, etc.). Ces critères sont **déjà satisfaits par Story 4.1**. Story 4.2 n'a qu'à consommer ces valeurs dans le frontend pour les afficher avec les bons libellés.

Résumé :

| Couche | Story 4.2 | Responsable |
|---|---|---|
| Backend Python (pipeline, API) | Aucune modification | Figé Story 4.1 |
| Frontend JS (`jeedom2ha_scope_summary.js`) | Seul lieu de modification | Story 4.2 |
| Tests unitaires JS (`tests/unit/`) | Migration + nouveaux invariants | Story 4.2 |
| Tests pytest (`resources/daemon/tests/`) | Zéro modification — régression uniquement | Story 4.2 (vérification) |

### Table buildPerimetreLabel — source de vérité

Implémenter dans `jeedom2ha_scope_summary.js`, fonction locale pure, sans dépendance externe.

```
Valeur perimetre (backend)   → Libellé UI affiché
─────────────────────────────────────────────────
"exclu_par_piece"            → "Exclu par la pièce"
"exclu_par_plugin"           → "Exclu par le plugin"
"exclu_sur_equipement"       → "Exclu sur cet équipement"
"inclus"                     → "" (pas de badge — la source d'exclusion est sans objet)
toute autre valeur ou ""     → "" (pas de badge — sécuritaire, silent fail)
```

Cette table est la seule source de vérité pour les labels de source d'exclusion côté UI. Elle :
- Ne lit pas `reason_code`
- Ne lit pas `cause_code`
- Ne lit pas `decision_source` ni `is_exception`
- Ne reconstruit aucune logique d'héritage

### Accès aux champs dans la réponse JS

Le contrat diagnostics ajouté par Story 4.1 est accessible dans les variables déjà extraites par `createModel()` :

| Champ Story 4.1 | Emplacement dans la réponse JSON backend | Variable JS (déjà extraite) |
|---|---|---|
| `perimetre` (par équipement) | `payload.equipments[i].perimetre` | `diagEquipments[eq_id].perimetre` (accessible via `eqDiag` passé à `buildEquipmentModel`) |
| `compteurs` (par pièce) | `payload.rooms[i].compteurs` | `dr.compteurs` dans la boucle sur `diagRooms` — **À EXTRAIRE** (pas encore indexé) |
| `compteurs` (global) | `payload.summary.compteurs` | `diagSummary.compteurs` (`diagSummary` déjà extrait à la ligne 145-146) |

**Point clé :** `diagSummary` dans le JS correspond à `safeResponse.diagnostic_summary = payload.summary`. Ce champ a été enrichi de `compteurs` par Story 4.1 Task 3.3. Il suffit de lire `diagSummary.compteurs`.

**Point de vigilance :** le `diagRoomByObjectId` actuel ne stocke que `dr.summary`. Il faut créer en parallèle un `diagRoomCompteursByObjectId` qui stocke `dr.compteurs`. Ne pas modifier la structure de `diagRoomByObjectId` existante pour éviter de casser la non-régression Story 3.4.

### Structure compteurs cible dans le modèle JS

Après migration, le modèle produit par `createModel()` utilise les clés nouvelles :

```
// Avant Story 4.2 (ancienne structure)
model.global_counts = { total: N, include: N, exclude: N, exceptions: N }
model.pieces[i].counts = { total: N, include: N, exclude: N, exceptions: N }

// Après Story 4.2 (nouvelle structure)
model.global_counts = { total: N, inclus: N, exclus: N, ecarts: N }
model.pieces[i].counts = { total: N, inclus: N, exclus: N, ecarts: N }
```

Toutes les références à `.include`, `.exclude`, `.exceptions` dans `render()` doivent être mises à jour en conséquence (`.inclus`, `.exclus`, `.ecarts`).

### Graceful degradation — daemon indisponible

Quand le daemon est arrêté, `diagnostic_rooms` est vide et `diagnostic_summary` ne contient pas `compteurs`. Comportement attendu :

- `buildCompteursFallback(piece.counts)` traduit `include` → `inclus`, `exclude` → `exclus`, fixe `ecarts` à `null`
- `toDisplayCount(null)` retourne `'&mdash;'` (déjà implémenté) — affiché comme `—` pour `Écarts`
- `eqDiag.perimetre` est absent → `buildPerimetreLabel("")` retourne `""` → pas de badge perimetre_label
- Le fallback n'affiche aucun terme interdit

Ce pattern est cohérent avec le comportement Story 3.4 : les badges diagnostics n'apparaissent que quand le daemon est disponible.

### Comportement attendu du badge perimetre_label

Badge rendu pour un équipement exclu (style uniforme, gris neutre) :
```html
<span class="label" style="margin-left:8px;background-color:#777;color:#fff;">Exclu par la pièce</span>
```

- **Pas de `label-info`** (bleu) — l'ancienne distinction visuelle entre "Exception locale" (bleu) et "Hérite de la pièce" (gris) est supprimée. Story 4.2 utilise un style uniforme pour toutes les sources d'exclusion.
- **Pas de badge pour `perimetre = inclus`** — seuls les équipements exclus affichent un badge source.
- Si `perimetre_label === ''` (inclus ou inconnu) → pas de `<span>` rendu.

### Ce que Story 4.2 NE change PAS

**Position retenue sur le périmètre de la migration de vocabulaire :**

Story 4.2 couvre uniquement la famille **"exception / héritage / Exceptions"** : disparition de `Hérite de la pièce`, `Exception locale`, du compteur `Exceptions`, des champs internes `decision_source` et `is_exception`, et migration des compteurs vers les nouvelles clés (`inclus`, `exclus`, `ecarts`).

Les autres termes interdits par §6.2 qui subsistent dans `jeedom2ha_scope_summary.js` après Story 4.2 sont intentionnels :

| Terme qui subsiste | Fonction concernée | Traité par |
|---|---|---|
| `include` / `exclude` (anglais dans le badge) | `renderEquipmentState(effective_state)` | Story 4.4 (refonte affichage équipement 4D) |
| `Ambigu` | `getAggregatedStatusLabel("ambiguous")` | Story 4.4 |
| `Partiellement publié` | `getAggregatedStatusLabel("partially_published")` | Story 4.3 |
| `Non supporté` | `getAggregatedStatusLabel("not_supported")` | Story 4.4 |

Cette coexistence temporaire est acceptable : Story 4.2 crée une étape de migration focalisée. L'invariant de test Story 4.2 couvre uniquement la famille exception/héritage (AC 5), pas ces termes.

Les éléments suivants restent donc inchangés dans `jeedom2ha_scope_summary.js` :

- `renderEquipmentState(effective_state)` — conservé tel quel, y compris les labels `include`/`exclude` en anglais. Story 4.4 refonde l'affichage équipement dans sa globalité.
- `getAggregatedStatusLabel(statusCode)` — conservé tel quel. L'élimination de `Ambigu`, `Partiellement publié`, `Non supporté` est gérée par Stories 4.3 et 4.4.
- `renderCountsByStatus(counts)` — conservé tel quel.
- Toute la section Story 3.4 (`status_code`, `detail`, `remediation`, `v1_limitation`) — inchangée.
- `has_pending_home_assistant_changes` badge — inchangé.

### Invariants de test à respecter (critères de done)

1. **Invariant no-exception** : Pour tout payload valide rendu par `render()`, le HTML produit ne contient JAMAIS l'une des chaînes suivantes :
   - `"Exception locale"` (exact)
   - `"Hérite de la pièce"` (exact)
   - `"Exceptions"` (avec majuscule — libellé d'en-tête ou de stat)
   - `">exceptions<"` (valeur dans un attribut ou cellule)
2. **Invariant compteurs** : La chaîne `"{{Exceptions}}"` ou `"Exceptions"` n'apparaît plus dans le code JS actif. La chaîne `"{{Écarts}}"` est présente dans l'en-tête de colonne du tableau pièces et comme label de stat globale.
3. **Invariant badge source** : Un équipement avec `eqDiag.perimetre = "exclu_par_piece"` doit afficher exactement `"Exclu par la pièce"` dans le HTML rendu.
4. **Invariant style uniforme** : Un équipement exclu ne doit pas utiliser la classe `label-info` pour son badge source d'exclusion — tous les badges source utilisent le style gris neutre.

### Fichiers à créer / modifier

| Fichier | Action |
|---|---|
| `desktop/js/jeedom2ha_scope_summary.js` | **MODIFIER** — supprimer vocabulaire interdit, ajouter `buildPerimetreLabel`, `buildCompteurs`, `buildCompteursFallback`, mettre à jour `buildEquipmentModel`, `createModel`, `render`, `renderPieceEquipements` |
| `tests/unit/test_scope_summary_presenter.node.test.js` | **MODIFIER** — migration fixtures (supprimer `is_exception`, `decision_source`, `exceptions`), mise à jour assertions, ajout invariant no-exception |
| `tests/unit/test_story_3_4_ai5_frontend_passthrough.node.test.js` | **MODIFIER** — supprimer champs obsolètes des fixtures, vérifier non-régression passthrough Story 3.4 |
| `tests/unit/test_story_4_2_vocab_exclusion.node.test.js` | **CRÉER** — tests dédiés `buildPerimetreLabel` + invariants no-exception + compteurs canoniques |

**Fichiers à ne PAS toucher :**
- `resources/daemon/models/cause_mapping.py` (figé Story 4.1)
- `resources/daemon/models/ui_contract_4d.py` (figé Story 4.1)
- `resources/daemon/transport/http_server.py` (figé Story 4.1)
- `resources/daemon/models/taxonomy.py` (figé Story 3.1)
- `resources/daemon/models/aggregation.py` (figé Story 3.3)
- `resources/daemon/models/published_scope.py` (figé Story 1.1)
- Tout fichier `.php`, `.jinja`, `.twig`, `.html`
- `tests/unit/test_cause_mapping.py`, `test_ui_contract_4d.py`, `test_diagnostic_endpoint.py` (figés Story 4.1)

### Dev Agent Guardrails

1. **Ne pas modifier le contrat backend** — Story 4.1 a figé `perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`. Story 4.2 consomme uniquement ces champs, ne les redéfinit pas.
2. **Ne pas recalculer `perimetre` côté frontend** — `buildPerimetreLabel` reçoit la valeur `perimetre` directement depuis le backend (via `eqDiag`). Elle ne reconstruit pas la logique depuis `decision_source` ou `is_exception`.
3. **Ne pas recalculer les compteurs** — les valeurs `inclus`, `exclus`, `ecarts` viennent de `compteurs` (backend pré-calculé Story 4.1). Le frontend ne compte pas les équipements localement.
4. **Ne pas ajouter `statut`/`ecart`/`cause_label`** — ces affichages sont hors scope Story 4.2, réservés à Story 4.4.
5. **Ne pas filtrer les équipements** — le filtrage `perimetre = inclus` est réservé à Story 4.3.
6. **`reason_code` reste invisible** — `buildPerimetreLabel` lit uniquement `perimetre`, jamais `reason_code`.
7. **`cause_code` reste invisible** — `buildPerimetreLabel` lit uniquement `perimetre`, jamais `cause_code`.
8. **Aucune logique métier frontend inventée** — chaque libellé affiché provient du backend ou de la table `buildPerimetreLabel` documentée ci-dessus.
9. **Non-régression Story 3.4 obligatoire** — les sections `status_code`, `detail`, `remediation`, `v1_limitation`, `diagnostic_summary` et `renderCountsByStatus` ne sont pas modifiées. Le mécanisme de fallback daemon-down de Story 3.4 reste intact.
10. **`buildCounts()` peut coexister** — si le refactoring est risqué, `buildCounts(rawCounts)` peut rester pour un usage interne scope (compatibilité), mais ne doit plus être exposé dans le modèle final avec les anciennes clés `include`/`exclude`/`exceptions`.

### Project Structure Notes

- Tous les fichiers JS sont dans `desktop/js/`
- Tous les tests unitaires JS sont dans `tests/unit/` — format `*.node.test.js`, runner : Node.js `--test`
- Le module `Jeedom2haScopeSummary` est exporté en UMD (voir ligne 1-7 du fichier JS) — ne pas casser le pattern d'export
- Les tests importent le module via `require('../../../desktop/js/jeedom2ha_scope_summary.js')` — pas de changement d'import nécessaire

### References

- [Source: `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md#6.2`] — Vocabulaire recommandé + termes interdits
- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-26.md#D2`] — Disparition du concept exception
- [Source: `_bmad-output/implementation-artifacts/4-1-contrat-backend-du-modele-perimetre-statut-ecart-cause.md#Contrat JSON cible par équipement`] — Structure JSON cible, valeurs perimetre autorisées
- [Source: `_bmad-output/implementation-artifacts/4-1-contrat-backend-du-modele-perimetre-statut-ecart-cause.md#Dérivation du champ perimetre`] — Table reason_code → perimetre
- [Source: `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md#Story 4.2 Acceptance Criteria`] — AC upstream
- [Source: `desktop/js/jeedom2ha_scope_summary.js`] — État pré-Story 4.2 (référence pour l'état de départ)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_Aucun incident bloquant._

### Completion Notes List

**Story 4.2 implémentée le 2026-03-28.**

Changements frontend JS uniquement, zéro modification backend.

- `buildDecisionSourceLabel` + `buildCounts` remplacées par `buildPerimetreLabel`, `buildCompteurs`, `buildCompteursFallback`
- `buildEquipmentModel` : `decision_source_label` → `perimetre_label` (lu depuis `diag.perimetre`, jamais depuis `entry.decision_source`)
- `createModel` : `diagRoomCompteursByObjectId` ajouté pour indexer `dr.compteurs` par pièce ; `global_counts` et `piece.counts` utilisent `buildCompteurs` (diag) ou `buildCompteursFallback` (scope)
- `render` : `Exceptions` → `Écarts` (stat globale + en-tête colonne + valeur pièce) ; `.include`/`.exclude` → `.inclus`/`.exclus`
- `renderPieceEquipements` : badge source d'exclusion uniforme gris `background-color:#777`, conditionnel sur `perimetre_label !== ''`, sans `label-info` ni logique `isException`
- `buildPerimetreLabel` exportée pour tests unitaires directs
- Fallback daemon-down préservé : `ecarts = null` → `toDisplayCount` affiche `—`
- Condition badge "Exclue" pièce corrigée : `exclus === total` (anciennement `exclude`)

Termes supprimés du code actif : `Hérite de la pièce`, `Exception locale`, `Exceptions`, `is_exception`, `decision_source`, `buildDecisionSourceLabel`

Limites hors scope de 4.2 (intentionnelles) :
- `include`/`exclude` (anglais) dans `renderEquipmentState` → Story 4.4
- `Ambigu`/`Partiellement publié`/`Non supporté` dans `getAggregatedStatusLabel` → Stories 4.3/4.4

### File List

- `desktop/js/jeedom2ha_scope_summary.js` (modifié)
- `tests/unit/test_scope_summary_presenter.node.test.js` (modifié — migration fixtures + assertions, suppression test story-1.5 badge Exception, ajout invariant no-exception)
- `tests/unit/test_story_3_4_ai5_frontend_passthrough.node.test.js` (modifié — suppression champs obsolètes fixtures)
- `tests/unit/test_story_4_2_vocab_exclusion.node.test.js` (créé — 9 tests dédiés buildPerimetreLabel + invariants + compteurs + graceful degradation + style uniforme)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (mis à jour)

## Senior Developer Review (AI)

**Reviewer :** Alexandre (via Claude Opus 4.6)
**Date :** 2026-03-28
**Verdict : PASS**

### Résumé

Code review adversariale complète — 0 finding (0 CRITICAL, 0 HIGH, 0 MEDIUM, 0 LOW).

### Points de contrôle vérifiés

| Contrôle | Résultat |
|----------|----------|
| AC 1 — Badge `exclu_par_piece` → `Exclu par la pièce` | IMPLEMENTED |
| AC 2 — Badge `exclu_sur_equipement` → `Exclu sur cet équipement` | IMPLEMENTED |
| AC 3 — Badge `exclu_par_plugin` → `Exclu par le plugin` | IMPLEMENTED |
| AC 4 — `inclus` → aucun badge | IMPLEMENTED |
| AC 5 — Audit famille "exception / héritage" éliminée du JS | IMPLEMENTED |
| AC 6 — Compteurs `Total / Inclus / Exclus / Écarts` depuis contrat diagnostics | IMPLEMENTED |
| AC 7 — Graceful degradation daemon-down | IMPLEMENTED |
| AC 8 — Non-régression tests (81/81 JS PASS, 0 fichier Python modifié) | IMPLEMENTED |

### Vérifications complémentaires

- **Git vs Story File List** : concordance parfaite (5/5 fichiers)
- **Tasks [x] auditées** : 14/14 sous-tâches réellement complétées, aucune fausse revendication
- **Backend inchangé** : git confirme 0 modification dans `resources/daemon/`, `core/`
- **Non-régression Story 3.4** : 12/12 tests AI-5 PASS, fonctions `getAggregatedStatusLabel`, `renderCountsByStatus`, champs `status_code/detail/remediation/v1_limitation` intacts
- **Sécurité** : `escapeHtml` appliqué sur `perimetre_label`, pas de XSS
- **Dérive de scope** : aucune — `renderEquipmentState`, `getAggregatedStatusLabel` non touchés (réservés Stories 4.3/4.4)
- **Termes interdits** : grep exhaustif confirme absence totale de `buildDecisionSourceLabel`, `decision_source`, `is_exception`, `Hérite de la pièce`, `Exception locale`, `Exceptions`, `exceptions` dans le JS actif

### Change Log

- 2026-03-28 : Code review PASS — story passée de `review` à `done`
