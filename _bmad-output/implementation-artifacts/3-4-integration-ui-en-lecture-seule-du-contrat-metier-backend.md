# Story 3.4 : Intégration UI en lecture seule du contrat métier backend

Status: done

---

## User Story

En tant qu'utilisateur Jeedom,
je veux que l'interface affiche fidèlement le contrat métier calculé par le backend,
afin de ne pas subir une seconde interprétation locale des statuts.

---

## Contexte et Objectif

### Situation actuelle

Les stories 3.1, 3.2 et 3.3 ont construit un contrat backend complet et cohérent :

| Story | Contrat livré | Artefact clé |
|---|---|---|
| 3.1 | Taxonomie fermée à 5 statuts (`published`, `excluded`, `ambiguous`, `not_supported`, `infra_incident`) | `resources/daemon/models/taxonomy.py` |
| 3.2 | `reason_code` stables, `detail` lisible, `remediation`, `v1_limitation` | `_DIAGNOSTIC_MESSAGES` dans `http_server.py` |
| 3.3 | Agrégations pièce/global (`summary`, `rooms`, `primary_aggregated_status`, `counts_by_status`, `counts_by_reason`) | `resources/daemon/models/aggregation.py` |

L'UI actuelle exploite partiellement ce contrat :
- `getStatusLabel()` mappe déjà les 5 statuts vers des badges colorés (livré en 3.1).
- `reasonLabels` mappe déjà les `reason_code` vers des labels français (livré en 3.2).
- Le **diagnostic modal** (`getDiagnostics`) affiche le statut, la raison et les détails par équipement — mais dans une modale séparée, pas dans la console principale.
- La **vue scope summary** (`getPublishedScopeForConsole` → `/system/published_scope`) montre l'inclusion/exclusion par pièce et par équipement, mais **ne montre pas** les agrégations de statut backend (3.3), ni la raison principale, ni l'action recommandée.

### Objectif de Story 3.4

Faire remonter le contrat métier backend (statut, raison, action recommandée, agrégations) dans la console principale de la vue par pièce, **en lecture seule**, sans inventer de logique locale.

Le résultat : l'utilisateur voit dans la console quotidienne les mêmes informations que le support verrait dans le payload backend, sans divergence.

### Ce que cette story ne fait pas

| Frontière | Story 3.4 | Responsable |
|---|---|---|
| Taxonomie des 5 statuts | **Lecture seule** — `taxonomy.py` inchangé | Story 3.1 (figé) |
| `reason_code`, `detail`, `remediation` | **Lecture seule** — consommé tel quel | Story 3.2 (figé) |
| Algorithme d'agrégation | **Lecture seule** — `build_summary()` inchangé | Story 3.3 (figé) |
| Opérations HA (`Republier`, `Supprimer/Recréer`) | **Hors scope** | Epic 4 |
| Extension fonctionnelle (`button`, `number`, `select`, `climate`) | **Hors scope** | Phases B+ |
| Preview complète / remédiation guidée avancée | **Hors scope** | Phases C+ |
| Santé avancée du pont | **Hors scope** | Phase C |
| Refonte d'écran ou nouveau layout | **Hors scope** | N/A |
| Logique métier ajoutée dans JS/PHP | **Interdit** | N/A |

---

## Dépendances autorisées

- **Story 3.1** (done — PR #44) : taxonomie des 5 statuts, `taxonomy.py`, `getStatusLabel()`, garde-fous AI-1/AI-2/AI-3.
- **Story 3.2** (done — PR #46) : `reason_code` stables, `detail`, `remediation`, `v1_limitation`, `reasonLabels` JS, gardes-fous AI-3 couches 3 et 4.
- **Story 3.3** (review) : `build_summary()`, `primary_aggregated_status`, `counts_by_status`, `counts_by_reason`, payload `summary` + `rooms` dans `/system/diagnostics`.
- Aucune dépendance en avant.

---

## Scope

### In-scope

1. Enrichir la vue scope summary (console principale) avec les agrégations backend par pièce et global.
2. Afficher le contrat par équipement (statut + raison principale + action recommandée) dans la console, consommé depuis le backend.
3. Afficher explicitement les limitations Home Assistant quand `v1_limitation=true`.
4. Assurer la séparation visuelle des 4 dimensions : état de projection, raison principale, action recommandée, santé du pont.
5. Audit de non-recomposition : vérifier qu'aucune logique JS ne reconstruit de statut ou de raison à partir d'indices incomplets.
6. Filet de sécurité frontend dynamique (AI-5).

### Out-of-scope (interdit en 3.4)

- Modification de `taxonomy.py`, `aggregation.py`, `_DIAGNOSTIC_MESSAGES` → figés par 3.1/3.2/3.3.
- Ajout de nouveaux `reason_code`, statuts ou règles d'agrégation.
- Opérations HA `Republier` / `Supprimer-Recréer` → Epic 4.
- Refonte complète de layout ou nouvel écran.
- Logique de recomposition de statut dans le frontend.
- Preview complète, remédiation guidée avancée, santé avancée.

---

## Acceptance Criteria

### AC 1 — L'UI présente fidèlement le contrat backend sans inventer de logique

**Given** un payload backend contenant `status`, `reason_code`, `detail`, `remediation`, `v1_limitation` et les indicateurs d'agrégation (`summary`, `rooms`)
**When** l'UI affiche un équipement dans la console
**Then** elle présente ces données telles quelles
**And** elle n'invente ni nouvelle raison ni nouvelle règle métier
**And** elle ne recalcule pas de statut à partir d'autres champs

### AC 2 — Un changement de wording backend est reflété sans recalcul

**Given** un changement de `detail` ou `remediation` dans `_DIAGNOSTIC_MESSAGES` (backend)
**When** le payload mis à jour est servi par `/system/diagnostics`
**Then** l'UI reflète le nouveau wording sans recalcul ni logique parallèle
**And** aucun libellé statique frontend ne vient contredire le texte backend

### AC 3 — Cohérence backend/UI pour le support

**Given** un cas de non-publication complexe (ex: ambiguïté de mapping, limitation HA, incident infra)
**When** le support compare le payload JSON de `/system/diagnostics` et l'affichage UI
**Then** les deux surfaces racontent exactement la même histoire (même statut, même raison, même action recommandée)

### AC 4 — Agrégations pièce/global affichées depuis le backend

**Given** le payload `/system/diagnostics` contenant `summary` (global) et `rooms[].summary` (par pièce)
**When** la console affiche la vue par pièce
**Then** chaque pièce montre le `primary_aggregated_status` sous forme de badge backend
**And** les compteurs `counts_by_status` sont visibles (au moins en accès rapide)
**And** le niveau global affiche son propre `primary_aggregated_status` et compteurs
**And** le frontend ne recalcule aucun de ces agrégats

### AC 5 — Séparation visuelle des 4 dimensions

**Given** l'affichage d'un équipement dans la console
**When** l'utilisateur le lit
**Then** les informations suivantes sont visuellement séparées :
- état de projection (badge statut : `Publié`, `Exclu`, `Ambigu`, `Non supporté`, `Incident infrastructure`)
- raison principale (texte `detail` du backend)
- action recommandée (texte `remediation` du backend, si non vide)
- santé du pont (déjà dans le bandeau, Story 2.2 — pas de duplication)

### AC 6 — Limitations Home Assistant explicites

**Given** un équipement dont le backend retourne `v1_limitation=true`
**When** l'UI affiche cet équipement
**Then** un indicateur visible mentionne explicitement "Limitation Home Assistant" (pas seulement "Hors périmètre V1")
**And** le texte du `detail` backend contenant "Home Assistant" est affiché tel quel

### AC 7 — Non-régression des tests existants

**Given** l'ajout de l'affichage du contrat métier dans la console
**When** la suite de tests est exécutée
**Then** les tests des stories 3.1, 3.2 et 3.3 restent verts
**And** les tests de synchronisation backend/frontend (AI-3 couches 1-4) restent verts
**And** les tests existants du scope summary et du bandeau de santé restent verts

---

## Principe directeur : ce qui vient du backend vs ce que l'UI a le droit de faire

Ce tableau est le contrat de non-empiètement le plus important de la story.

| Donnée | Source unique | Droit de l'UI | Interdit à l'UI |
|---|---|---|---|
| `status_code` (code canonique, 5 valeurs) | Backend (`taxonomy.py` + `_STATUS_CODE_MAP`) | Mapper vers un badge coloré de présentation | Recalculer un statut à partir d'autres champs |
| `detail` (raison lisible) | Backend (`_DIAGNOSTIC_MESSAGES`) | **Afficher tel quel comme raison principale visible** | Reformuler, tronquer sémantiquement, remplacer par un label local, ou substituer par un mapping de `reason_code` |
| `reason_code` | Backend (`_DIAGNOSTIC_MESSAGES`) | Utiliser pour contrat, tests, debug, agrégation `counts_by_reason`, compatibilité `reasonLabels` modale diagnostic | **Ne pas utiliser comme source du wording affiché dans la console principale** si `detail` est fourni |
| `remediation` (action recommandée) | Backend (`_DIAGNOSTIC_MESSAGES`) | **Afficher tel quel si non vide** | Inventer une action si le champ est vide |
| `v1_limitation` | Backend | Afficher un badge "Limitation Home Assistant" si `true` | Décider localement si une limitation existe |
| `primary_aggregated_status` (pièce/global) | Backend (`aggregation.py`) | Mapper vers un badge | Recalculer en comptant les enfants |
| `counts_by_status` | Backend (`aggregation.py`) | Afficher les compteurs | Recalculer en re-comptant |
| `counts_by_reason` | Backend (`aggregation.py`) | Afficher si pertinent | Recalculer |
| Suffixe `(partiel)` | Call site renderer (déjà en place depuis 3.1) | Concaténer quand `status_code == "published"` ET `unmatched_commands.length > 0` | Transformer en statut principal séparé |

**Formatage autorisé** : l'UI peut formater visuellement (badges, icônes, couleurs, mise en page). Elle ne peut pas inférer du sens métier que le backend n'a pas fourni.

---

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [x] Task 1 — Enrichir la vue scope summary avec les agrégations backend (AC 4, AC 5)
  - [x] 1.1 Déterminer la stratégie d'alimentation en données d'agrégation pour la vue scope summary. Deux options :
    - **Option A** : le scope summary JS appelle en plus `/system/diagnostics` (via le relay PHP existant `getDiagnostics`) et merge côté client les données d'agrégation (`summary`, `rooms`) avec les données de scope existantes.
    - **Option B** : le relay PHP (`jeedom2ha.ajax.php`) enrichit la réponse de `getPublishedScopeForConsole` avec les agrégations issues de `/system/diagnostics` avant de renvoyer au JS.
    - **Critère de choix** : l'Option B est préférable car elle évite un second appel HTTP depuis le poller JS et garde la logique de merge côté backend/relay. Mais si le relay PHP est trop contraint (cf. feedback AI-4 profils PHP), l'Option A est acceptable.
    - **Décision retenue** : Option B implémentée dans `core/ajax/jeedom2ha.ajax.php` — merge soft-fail (si daemon absent, vue scope-only inchangée).
  - [x] 1.2 Modifier `jeedom2ha_scope_summary.js` — fonction `createModel()` : intégrer les champs `primary_aggregated_status` et `counts_by_status` pour chaque pièce et pour le global.
  - [x] 1.3 Modifier `jeedom2ha_scope_summary.js` — fonction `render()` : afficher un badge de statut agrégé par pièce (utiliser `getStatusLabel()` existant ou un mapper dédié pour les statuts agrégés incluant `partially_published` et `empty`).
  - [x] 1.4 Afficher les compteurs `counts_by_status` par pièce de façon compacte (ex: chips ou mini-badges).
  - [x] 1.5 Afficher le `primary_aggregated_status` global et les compteurs dans la zone de synthèse globale.

- [x] Task 2 — Afficher le contrat métier par équipement dans la console (AC 1, AC 2, AC 3, AC 5, AC 6)
  - [x] 2.1 Pour chaque équipement listé dans la vue pièce (scope summary ou détail), afficher :
    - Badge statut (via `getAggregatedStatusLabel()` nouveau, consomme `status_code` canonique)
    - Raison principale : **le champ `detail` du backend, affiché tel quel** (ne pas substituer par un label dérivé de `reason_code` via `reasonLabels`)
    - Action recommandée (`remediation` du backend, affiché tel quel si non vide)
  - [x] 2.2 Afficher un badge "Limitation Home Assistant" quand `v1_limitation == true`.
  - [x] 2.3 Assurer que le `detail` et la `remediation` sont affichés tels quels depuis le backend, sans reformulation JS.
  - [x] 2.4 Vérifier que le suffixe `(partiel)` existant (3.1) reste géré au call site du renderer et ne contredit pas le statut backend.

- [x] Task 3 — Audit de non-recomposition côté frontend (AC 1, AC 3)
  - [x] 3.1 Auditer `jeedom2ha.js` et `jeedom2ha_scope_summary.js` pour identifier toute logique qui :
    - reconstruit un statut à partir de champs bruts (ex: déduire "ambigu" depuis confidence),
    - invente une raison non présente dans le payload backend,
    - recalcule un agrégat local contradictoire avec `counts_by_status`.
  - [x] 3.2 Si une telle logique est trouvée : la supprimer et la remplacer par la consommation directe du champ backend correspondant.
  - [x] 3.3 Documenter le résultat de l'audit dans les completion notes (nombre de points identifiés, corrections apportées ou "audit clean — aucune recomposition trouvée").

- [x] Task 4 — Filet de sécurité frontend dynamique (AI-5) (AC 1, AC 4, AC 7)
  - [x] 4.1 Choisir le type de filet de sécurité : test `node:test` automatisé (Option test automatisé).
  - [x] 4.2 Implémenter le filet choisi.
  - [x] 4.3 Si un test automatisé est choisi, il doit vérifier au minimum :
    - Présence du badge `primary_aggregated_status` dans le HTML rendu pour une pièce.
    - Présence des compteurs `counts_by_status` dans le HTML rendu.
    - Présence du `detail` backend pour un équipement rendu.
    - Absence de recalcul (le test passe un payload avec des valeurs spécifiques et vérifie qu'elles apparaissent telles quelles dans le HTML).
  - [x] 4.4 Protocole terrain documenté en complément pour le rafraîchissement dynamique.

- [x] Task 5 — Mapper les statuts agrégés backend vers des labels/badges UI (AC 4, AC 5)
  - [x] 5.1 Le backend retourne des statuts agrégés supplémentaires non couverts par `getStatusLabel()` : `partially_published` et `empty`. Créer un mapper dédié `getAggregatedStatusLabel(statusCode)` dans `jeedom2ha_scope_summary.js`.
  - [x] 5.2 Labels et couleurs implémentés :
    - `published` → `Publié` (vert)
    - `excluded` → `Exclu` (gris)
    - `ambiguous` → `Ambigu` (orange)
    - `not_supported` → `Non supporté` (gris sombre)
    - `infra_incident` → `Incident infrastructure` (rouge)
    - `partially_published` → `Partiellement publié` (bleu label-info)
    - `empty` → `Vide` (gris neutre)
  - [x] 5.3 Ce mapper ne contient **aucune logique métier** — il ne fait que traduire une clé en label + classe CSS. La logique de détermination du statut reste dans `aggregation.py`.

- [x] Task 6 — Non-régression (AC 7)
  - [x] 6.1 Exécuter la suite complète de tests : `pytest` (stories 3.1, 3.2, 3.3 + tests existants). → 128/128 PASS
  - [x] 6.2 Exécuter les tests JS existants (node:test si présents). → 61/61 PASS (avant AI-5), 72/72 PASS (après AI-5)
  - [x] 6.3 Vérifier que les gardes-fous AI-3 (4 couches) restent verts. → Inclus dans les 61 JS existants
  - [x] 6.4 Vérifier que le bandeau de santé (Story 2.2) et le gating (Story 2.3) restent fonctionnels. → test_ha_gating + test_story_2_4 PASS

---

## Dev Notes

### Contexte actif et contraintes de cadrage

- Le cycle actif est **Post-MVP Phase 1 - V1.1 Pilotable**.
- Cette story appartient à **Epic 3 — Moteur de statuts, raisons lisibles et explicabilité backend**.
- Elle est la dernière story de l'Epic 3 et prépare le terrain pour l'Epic 4 (opérations HA).
- Elle doit rester **backend-first** : le backend a déjà tout calculé, l'UI consomme.

### Architecture de données existante à consommer

**Endpoint `/system/diagnostics`** (backend → relay PHP → JS) :

```json
{
  "action": "system.diagnostics",
  "status": "ok",
  "payload": {
    "summary": {
      "primary_aggregated_status": "partially_published",
      "total_equipments": 8,
      "counts_by_status": {
        "published": 5, "excluded": 2, "ambiguous": 1,
        "not_supported": 0, "infra_incident": 0
      },
      "counts_by_reason": { "sure": 5, "excluded_eqlogic": 2, "ambiguous_skipped": 1 }
    },
    "rooms": [
      {
        "object_id": 5, "object_name": "Salon",
        "summary": { "primary_aggregated_status": "...", "total_equipments": 3, "counts_by_status": {...}, "counts_by_reason": {...} }
      }
    ],
    "equipments": [
      {
        "eq_id": 42, "name": "Lampe Salon", "object_name": "Salon",
        "status_code": "published",
        "reason_code": "sure",
        "detail": "",
        "remediation": "",
        "v1_limitation": false,
        "matched_commands": [...], "unmatched_commands": [...]
      }
    ]
  }
}
```

**Clarification sur les champs du payload équipement :**

| Champ | Nature | Rôle pour Story 3.4 |
|---|---|---|
| `status_code` | **Code canonique backend** (`"published"`, `"excluded"`, `"ambiguous"`, `"not_supported"`, `"infra_incident"`) | **Champ contractuel principal du statut.** L'UI mappe ce code vers un badge/libellé de présentation. Utilisé aussi par `build_summary()` pour les agrégations |
| `reason_code` | Code stable du motif de diagnostic (`"sure"`, `"excluded_eqlogic"`, etc.) | Identifiant pour contrat, tests, debug, agrégation `counts_by_reason` ; **pas la source du wording affiché** |
| `detail` | Texte lisible produit par `_DIAGNOSTIC_MESSAGES` | **Source de vérité pour la raison principale affichée** à l'utilisateur — afficher tel quel |
| `remediation` | Texte lisible produit par `_DIAGNOSTIC_MESSAGES` | **Source de vérité pour l'action recommandée affichée** — afficher tel quel si non vide |
| `v1_limitation` | Booléen | Afficher un badge "Limitation Home Assistant" si `true` |

**Champs secondaires** (présents dans le payload, non contractuels pour Story 3.4) :

| Champ | Nature | Note |
|---|---|---|
| `status` | Label français dérivé (`"Publié"`, `"Exclu"`, etc.) — retourné par `get_primary_status()` | Champ de commodité hérité. **Non recommandé comme source contractuelle.** Le code canonique est `status_code`. Si `getStatusLabel()` consomme actuellement ce champ, Story 3.4 peut le migrer vers `status_code` |
| `confidence` | Label français (`"Sûr"`, `"Probable"`, `"Ambigu"`, `"Ignoré"`) | Informatif pour le diagnostic technique. N'intervient pas dans la détermination du statut principal ni de la raison principale |

**Endpoint `/system/published_scope`** (scope actuel, inchangé) :

```json
{
  "status": "ok",
  "published_scope": {
    "global": { "counts": {"total": 12, "include": 8, "exclude": 3, "exceptions": 1}, "has_pending_ha_changes": false },
    "pieces": [{ "object_id": 5, "object_name": "Salon", "counts": {...}, "has_pending_ha_changes": false }],
    "equipements": [{ "eq_id": 42, "object_id": 5, "name": "Lampe Salon", "effective_state": "include", "decision_source": "inherit", "is_exception": false, "has_pending_ha_changes": false }]
  }
}
```

### Fichiers à modifier (estimé)

| Fichier | Type de modification |
|---|---|
| `desktop/js/jeedom2ha_scope_summary.js` | Enrichir `createModel()` et `render()` avec agrégations backend |
| `desktop/js/jeedom2ha.js` | Ajouter le fetch de données diagnostiques pour enrichir la vue scope, ou adapter le relay PHP |
| `core/ajax/jeedom2ha.ajax.php` | Si Option B : enrichir `getPublishedScopeForConsole` avec les données d'agrégation |
| `desktop/php/jeedom2ha.php` | Adaptations HTML mineures pour les badges/compteurs d'agrégation (si nécessaire) |
| `desktop/js/tests/` ou équivalent | Test AI-5 (node:test) |

### Polling et rafraîchissement

- Le scope summary se rafraîchit toutes les 10 secondes (`refreshPublishedScopeSummary`).
- Le bandeau santé se rafraîchit toutes les 5 secondes (`refreshBridgeStatus`).
- La navigation (pièces ouvertes, scroll) est préservée entre les rafraîchissements (`_captureNavState` / `_restoreNavState`).
- Story 3.4 doit respecter ce pattern : les nouvelles données (agrégations, raisons) doivent être rafraîchies dans le même cycle de polling existant, sans ajouter de timer supplémentaire.

### Dev Agent Guardrails

#### Guardrail principal — Lecture seule du contrat backend

Le frontend **consomme** le contrat des stories 3.1, 3.2, 3.3. Il ne le **modifie** pas.

Concrètement :
- **Ne pas modifier** : `taxonomy.py`, `aggregation.py`, `_DIAGNOSTIC_MESSAGES`, `_STATUS_CODE_MAP`, `build_summary()`.
- **Ne pas ajouter** : de nouveaux `reason_code`, statuts, ou règles d'agrégation.
- **Ne pas recalculer** : de statut agrégé en JS en comptant les enfants.
- **Ne pas reformuler** : les textes `detail` ou `remediation` — les afficher tels quels.
- **Ne pas substituer** : `detail` par un mapping de `reason_code` via `reasonLabels` comme raison principale affichée dans la console. La source de vérité du wording visible est `detail`, pas `reasonLabels`.
- **Ne pas conditionner** : l'affichage sur une logique métier locale (ex: "si confidence < 0.5 alors afficher orange").

#### Guardrail — Séparation visuelle des 4 dimensions

- L'état de projection (badge statut) est un élément visuel distinct.
- La raison principale (texte `detail`) est un texte séparé du badge.
- L'action recommandée (`remediation`) est un texte distinct de la raison.
- La santé du pont reste dans le bandeau global (Story 2.2) — ne pas la dupliquer au niveau équipement.
- Ne pas faire porter tout le sens par un seul badge.

#### Guardrail — Rouge réservé à l'infrastructure

- `label-danger` (rouge) uniquement pour `infra_incident` et `Incident infrastructure`.
- `Ambigu` et `Non supporté` ne sont jamais rouges.
- Hériter strictement des couleurs déjà définies dans `getStatusLabel()` (Story 3.1).

#### Guardrail — Pas de refonte d'écran

- Story 3.4 enrichit les vues existantes (scope summary, détails équipement).
- Elle ne crée pas de nouvel écran, onglet ou modale.
- Elle ne remplace pas la modale diagnostic existante — elle ajoute des données dans la console principale.

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

#### Guardrail AI-5 — Filet de sécurité frontend dynamique

- Toute logique dynamique (rafraîchissement des agrégations dans le polling) doit avoir un filet de sécurité.
- Préférer un test `node:test` (pattern validé Story 2.3).
- Le filet doit prouver que les données backend arrivent dans le DOM rendu sans transformation métier.

### Project Structure Notes

- Tests Python : `resources/daemon/tests/unit/` (pytest)
- Tests JS : pattern `node:test` utilisé depuis Story 2.3
- Ajax relay : `core/ajax/jeedom2ha.ajax.php` (stub PHP sans dépendance Jeedom pour les tests)
- JS principal : `desktop/js/jeedom2ha.js` (~710 lignes)
- JS scope summary : `desktop/js/jeedom2ha_scope_summary.js` (~259 lignes)
- Le relay PHP `jeedom2ha.ajax.php` appelle le daemon via HTTP local (`/system/diagnostics`, `/system/published_scope`, etc.)

### References

- **Sources actives de vérité :**
  - `_bmad-output/planning-artifacts/active-cycle-manifest.md`
  - `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md` (Epic 3, Story 3.4)
  - `_bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md` (FR12-FR14, FR23-FR25)
  - `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md` (sections 4.2, 5.2, 6.1-6.4)
  - `_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md` (section 8.4 — gouvernance backend-first)
  - `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
  - `_bmad-output/implementation-artifacts/epic-2-retro-2026-03-25.md` (AI-5)
- **Contexte secondaire autorisé :**
  - `_bmad-output/implementation-artifacts/3-1-taxonomie-principale-de-statuts-d-equipement.md`
  - `_bmad-output/implementation-artifacts/3-2-reason-code-stables-raison-lisible-et-action-recommandee.md`
  - `_bmad-output/implementation-artifacts/3-3-agregations-piece-et-global-coherentes.md`

---

## Testing Requirements

### Invariants V1.1 touchés

- Backend source unique des statuts et raisons (pas de logique métier migrée dans le frontend).
- Cohérence sémantique entre niveaux de lecture (pièce, global, équipement).
- Séparation stricte entre infrastructure et configuration côté UI.

### Tests obligatoires

**Tests de non-régression (Python — existants) :**
- Suite `pytest` complète : stories 3.1, 3.2, 3.3 + tests pré-existants.
- Gardes-fous AI-3 couches 1-4 restent verts.

**Tests de non-régression (JS — existants) :**
- Tests `node:test` existants (Story 2.3+).
- Tests de synchronisation `reasonLabels` (AI-3 couche 4).

**Test nouveau obligatoire — Filet de sécurité AI-5 (JS — `node:test`) :**
- Vérifie que le HTML rendu par la vue scope summary contient les données d'agrégation backend sans recalcul.
- Passe un payload mock avec des valeurs spécifiques (ex: `primary_aggregated_status: "ambiguous"`, `counts_by_status: {published: 3, ambiguous: 1}`) et vérifie que ces valeurs exactes apparaissent dans le HTML produit.
- Vérifie que le `detail` backend d'un équipement apparaît tel quel dans le HTML.

**Tests UI terrain (si le test automatisé ne couvre pas le polling) :**
- Protocole terrain prescriptif :
  1. État initial : daemon démarré, au moins 3 équipements (1 published, 1 excluded, 1 ambiguous).
  2. Action : ouvrir la page plugin, observer la console par pièce.
  3. Vérification : les badges d'agrégation pièce/global correspondent au payload `/system/diagnostics`. La raison principale affichée correspond au `detail` backend. Le rafraîchissement automatique (≤ 10s) met à jour les données.
  4. Contre-vérification : comparer visuellement le JSON de `/system/diagnostics` (accessible via diagnostic export) avec l'affichage console.

### Tests non requis pour cette story

- Tests de la logique d'agrégation (Story 3.3).
- Tests des reason codes (Story 3.2).
- Tests de la taxonomie (Story 3.1).
- Tests des opérations HA (Epic 4).

---

## Risques / Points de vigilance

| Risque | Impact | Mitigation |
|---|---|---|
| Le frontend recompose un statut au lieu de le consommer | Divergence backend/UI, dette support | Audit Task 3, test AI-5 |
| Le frontend invente une raison pour un code absent | Message incorrect affiché | AI-3 couche 4 (test de sync `reasonLabels`) empêche déjà ce cas |
| Les agrégations sont recalculées en JS au lieu d'être lues du backend | Incohérence avec le payload, bug subtil | AC 4 explicite, test AI-5 vérifie les valeurs exactes |
| Le polling 10s surcharge le daemon avec un appel supplémentaire | Latence perçue | Privilégier Option B (merge côté relay PHP) pour éviter un second appel HTTP |
| Le suffixe `(partiel)` diverge du `primary_aggregated_status` pièce | Confusion utilisateur | Le suffixe est un détail de présentation au niveau équipement, l'agrégation pièce est un statut séparé — documenter la distinction |
| Dérive vers une refonte d'écran | Scope creep | Guardrail "pas de refonte" + AC bornés à l'enrichissement des vues existantes |

---

## Réduction de dette support

Story 3.4 supprime la divergence backend/UI dans la lecture des statuts et raisons :

- **Avant 3.4** : le support devait comparer manuellement le payload JSON du diagnostic avec l'affichage UI pour identifier les incohérences. L'UI n'affichait pas la raison principale ni l'action recommandée dans la console quotidienne.
- **Après 3.4** : le contrat métier backend (statut + raison + action + agrégations) est directement visible dans la console. Le support et l'utilisateur voient la même information. Le temps de qualification d'un "pourquoi non publié" diminue significativement car la raison est affichée sans navigation vers la modale diagnostic.

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (2026-03-26)

### Debug Log References

Aucune déviation bloquante. Un test deepEqual existant a nécessité une mise à jour pour refléter les nouveaux champs du modèle équipement (`status_code`, `detail`, `remediation`, `v1_limitation`).

### Completion Notes List

**Task 0 — Pre-flight** : lecture complète du code JS/PHP. Stratégie retenue : Option B (merge relay PHP). Audit anti-recomposition préliminaire : aucune recomposition de statut dans la console, `getStatusLabel()` de la modale scoped à la modale uniquement.

**Task 1 — Wiring** : `core/ajax/jeedom2ha.ajax.php` — action `getPublishedScopeForConsole` enrichie avec un appel soft-fail à `/system/diagnostics`. Si le daemon est absent, la vue scope-only reste inchangée. Le payload enrichi contient `diagnostic_summary`, `diagnostic_rooms`, `diagnostic_equipments` (indexé par `eq_id`).

**Task 2 — Affichage équipement** : `renderPieceEquipements()` affiche dans le detail accordion : badge statut (`status_code` → `getAggregatedStatusLabel`), raison principale (`detail` tel quel), action recommandée (`remediation` tel quel si non vide), badge "Limitation Home Assistant" si `v1_limitation=true`. Séparation visuelle des 4 dimensions respectée.

**Task 3 — Audit anti-recomposition** : console clean. Badge local "Exclue" (scope counts) conservé en fallback uniquement quand `diagnostic_summary` est null — court-circuité par `primary_aggregated_status` dès que le daemon répond. Aucune suppression de logique nécessaire.

**Task 5 — Mapper** : `getAggregatedStatusLabel(statusCode)` ajoutée dans `jeedom2ha_scope_summary.js` — 7 codes couverts, aucune logique métier, exportée pour les tests.

**Task 4/6 — Tests** :
- Non-régression : 128/128 pytest ✓, 61/61 JS existants ✓
- Filet AI-5 : 11 tests `node:test` dans `test_story_3_4_ai5_frontend_passthrough.node.test.js`
- Suite totale : 72/72 JS ✓

**Micro-fix post-review — object_id: null (pièce "Aucun")** :
- Constat terrain : la pièce "Aucun" n'affichait pas son badge diagnostic. Cause racine : le scope retourne `object_id: 0` pour cette pièce, mais le diagnostic retourne `object_id: null` — les clés d'index ne correspondaient pas (`"0"` vs `"null"`).
- Fix : normalisation dans `createModel()` — `object_id: null` du diagnostic est mappé vers `0` avant indexation, cohérent avec le contrat scope.
- Test AI-5.12 ajouté : reproduit le décalage terrain réel (scope `object_id: 0`, diag `object_id: null`) et vérifie que la pièce reçoit son `diagnostic_summary`.
- Suite totale après fix : 73/73 JS ✓, 128/128 pytest ✓

**Invariants respectés** :
- Backend-first : `status_code`, `detail`, `remediation`, `v1_limitation`, `primary_aggregated_status`, `counts_by_status` consommés tels quels depuis le payload.
- `taxonomy.py`, `aggregation.py`, `_DIAGNOSTIC_MESSAGES` non modifiés.
- Rouge (`label-danger`) réservé à `infra_incident` uniquement.
- Pas de refonte d'écran, pas de nouvelle route backend.
- Dégradation gracieuse : sans daemon, vue scope-only inchangée.

### File List

- `core/ajax/jeedom2ha.ajax.php` — modifié : enrichissement `getPublishedScopeForConsole` avec données diagnostic (Option B)
- `desktop/js/jeedom2ha_scope_summary.js` — modifié : `getAggregatedStatusLabel`, `renderCountsByStatus`, `buildEquipmentModel` (champs diagnostic), `createModel` (données diagnostic), `render` (global diagnostic summary + piece badge), `renderPieceEquipements` (statut/detail/remediation/v1_limitation), export `getAggregatedStatusLabel`
- `tests/unit/test_story_3_4_ai5_frontend_passthrough.node.test.js` — nouveau : filet AI-5 (12 tests, dont AI-5.12 pour object_id:null)
- `tests/unit/test_scope_summary_presenter.node.test.js` — modifié : mise à jour deepEqual pour inclure les nouveaux champs modèle équipement

---
**Story revision date:** 2026-03-26
**Cycle:** Post-MVP Phase 1 - V1.1 Pilotable
**Status:** done
