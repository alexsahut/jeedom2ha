# Story 3.3 : Agrégations pièce et global cohérentes

Status: done

---

## User Story

En tant qu'utilisateur de la console,
je veux des agrégations pièce/global cohérentes avec les statuts individuels,
afin d'avoir une lecture fiable de mon périmètre sans contradiction entre la synthèse et le détail.

---

## Contexte et Objectif

La Story 3.1 a figé la taxonomie principale des statuts par équipement (`published`, `excluded`, `ambiguous`, `not_supported`, `infra_incident`).
La Story 3.2 a stabilisé les `reason_code`.

L'objectif de cette story est de construire un moteur d'agrégation **strictement backend** qui calcule les synthèses au niveau **pièce** et au niveau **global**, en se basant sur les équipements qu'ils contiennent.

Cette story garantit que :
1. Les compteurs agrégés constituent la **vérité absolue** et exhaustive.
2. Le **statut agrégé principal** (`primary_aggregated_status`) n'est qu'un résumé calculé selon une règle de priorité stricte et déterministe.
3. Le frontend (Story 3.4) n'aura aucune logique métier à implémenter pour déterminer l'état d'une pièce ou du parc global.

### Clarification de la dépendance à Story 3.2
Story 3.3 **ne dépend d'aucune logique sémantique de la Story 3.2**.
L'agrégation `counts_by_reason` consiste uniquement à grouper et compter les chaînes de caractères brutes du champ `reason_code` produites par le backend. Que la Story 3.2 ajoute ou modifie des reason codes n'a aucun impact sur l'algorithme d'agrégation de 3.3. **La dépendance est donc strictement de niveau donnée (data-level), non-bloquante, et le contrat est totalement découplé.**

---

## Acceptance Criteria

### AC 1 — La vérité réside dans les compteurs, gérés exclusivement par le backend
**Given** les données de diagnostic backend d'un niveau (pièce ou global)
**When** les agrégations sont générées
**Then** un objet `summary` est produit avec les champs `total_equipments`, `counts_by_status`, `counts_by_reason` et `primary_aggregated_status`
**And** la somme des valeurs de `counts_by_status` est strictement égale à `total_equipments`
**And** `not_supported` et `excluded` sont comptés séparément, sans fusion
**And** le frontend n'effectue aucun calcul pour déduire ces données.

### AC 2 — Règle de priorité stricte du statut principal
**Given** une pièce ou un global contenant plusieurs équipements de statuts différents
**When** le backend détermine le `primary_aggregated_status`
**Then** il applique strictement l'ordre suivant : `infra_incident` > `ambiguous` > `partially_published` > `not_supported` > `excluded` > `published` > `empty`
**And** ce statut ne masque jamais la présence d'un incident d'infrastructure ou d'une ambiguïté s'ils existent dans l'agrégat.

### AC 3 — Sémantique exacte de "Partiellement publié"
**Given** une pièce contenant des équipements
**When** le backend détermine le statut principal
**Then** il retourne `partially_published` SI ET SEULEMENT SI il y a au moins 1 équipement `published` ET au moins 1 équipement `excluded` ou `not_supported` (en l'absence de statuts plus prioritaires comme incident ou ambiguïté).

### AC 4 — Gestion déterministe des cas sans équipements (Vides)
**Given** une pièce sans aucun équipement, ou un parc global sans aucun équipement
**When** le backend génère la synthèse
**Then** tous les compteurs valent `0`
**And** le `primary_aggregated_status` vaut `"empty"` (état neutre distinct de `"not_published"` ou `"excluded"`).

### AC 5 — Cohérence symétrique Pièce / Global
**Given** le moteur d'agrégation
**When** il calcule les synthèses
**Then** l'algorithme appliqué pour calculer la synthèse du "global" est **strictement identique** à l'algorithme appliqué pour une "pièce" (même structure de sortie, mêmes règles de priorité).

### AC 6 — Stabilité du payload individuel (Non-régression)
**Given** l'ajout de l'objet `summary` dans le payload `/system/diagnostics`
**When** la requête est appelée
**Then** la structure existante des équipements individuels reste strictement inchangée.

---

## Tasks / Subtasks

- [x] Task 1 — Créer le module d'agrégation pur (Backend) (AC 1, 2, 3, 4, 5)
  - [x] 1.1 Créer un helper purement logique (ex: `resources/daemon/models/aggregation.py` ou équivalent) qui prend une liste de dictionnaires d'équipements en entrée.
  - [x] 1.2 Implémenter le calcul de `total_equipments`, `counts_by_status` (initialisé aux 5 statuts de 3.1 à 0) et `counts_by_reason` (incrément dynamique).
  - [x] 1.3 Implémenter la fonction de calcul du `primary_aggregated_status` respectant strictement la hiérarchie de priorité définie dans les Dev Notes.
  - [x] 1.4 Assurer la gestion du cas vide (0 équipement) avec retour du statut `"empty"`.

- [x] Task 2 — Intégrer les agrégations dans le payload `/system/diagnostics` (AC 1, 6)
  - [x] 2.1 Mettre à jour `_handle_system_diagnostics` dans `http_server.py`.
  - [x] 2.2 Appliquer la fonction d'agrégation sur la liste complète des équipements pour créer `summary` à la racine (niveau global).
  - [x] 2.3 Grouper les équipements par `object_id` / `object_name` (pièces) et appliquer la fonction d'agrégation pour chaque pièce. Exposer la liste des pièces et leurs `summary` dans le payload de réponse.
  - [x] 2.4 Assurer que la structure de la clé `"equipments"` existante reste intacte.

- [x] Task 3 — Ajouter la couverture de tests rigoureuse (Action Item AI-6) (AC 1-6)
  - [x] 3.1 Test unitaire de la règle de priorité : vérifier l'ordre `infra_incident` > `ambiguous` > `partially_published` > `not_supported` > `excluded` > `published`.
  - [x] 3.2 Test unitaire des mixités complexes : Ex: 0 published, 1 excluded, 1 not_supported -> retourne `not_supported` (règle 4).
  - [x] 3.3 Test unitaire du `partially_published` : Vérifier qu'il faut au moins 1 `published` et 1 exclusion/non-support pour l'activer.
  - [x] 3.4 Test unitaire des cas vides : Pièce vide et Global vide retournent des compteurs à 0 et le statut `empty`.
  - [x] 3.5 Test de contrat : Valider la structure JSON finale (`summary` global, `rooms` avec `summary`, et stabilité de `equipments`).

- [x] Task 4 — Durcir l'invariant sum(counts_by_status) == total_equipments (AC 1, correction post-review)
  - [x] 4.1 Normaliser tout `status_code` non canonique vers `not_supported` dans `build_summary()`.
  - [x] 4.2 Ajouter des tests unitaires couvrant le cas d'un `status_code` inattendu et la stabilité de l'invariant en présence de valeurs non canoniques.

---

## Dev Notes

### Contexte actif et contraintes de cadrage
- Le cycle actif est **Post-MVP Phase 1 - V1.1 Pilotable**.
- Cette story appartient à **Epic 3** et doit rester **backend-first**.
- Elle prépare le terrain pour la **Story 3.4 (UI)** en lui fournissant un contrat prêt à consommer, sans obliger le frontend à compter quoi que ce soit.

### Algorithme de calcul du `primary_aggregated_status`

Cet algorithme est **déterministe** et **immuable**. Il prend en entrée les valeurs de `counts_by_status` et retourne le premier statut validant sa condition (IF / ELIF) :

1.  Si `total_equipments == 0` → retour `"empty"`
2.  Si `counts_by_status['infra_incident'] > 0` → retour `"infra_incident"` (identifiant canonique strict, rejeter toute variante comme `infrastructure_incident`)
3.  Si `counts_by_status['ambiguous'] > 0` → retour `"ambiguous"`
4.  Si `counts_by_status['published'] > 0` ET `(counts_by_status['excluded'] > 0 OR counts_by_status['not_supported'] > 0)` → retour `"partially_published"`
5.  Si `counts_by_status['not_supported'] > 0` → retour `"not_supported"`
6.  Si `counts_by_status['excluded'] > 0` → retour `"excluded"`
7.  Sinon (ne reste que du published) → retour `"published"`

*Note sur la règle 5 : Si une pièce contient 0 publié, 1 excluded, 1 not_supported, elle est classée `not_supported`. C'est normal : le manque de support produit est une information prioritaire à remonter par rapport à une exclusion volontaire.*

### Clarification sur l'usage des `reason_code`
Story 3.3 se contente d'utiliser les `reason_code` générés par le backend comme des clés de dictionnaire opaques pour peupler `counts_by_reason`. Elle n'a besoin de connaître ni leur sens, ni leur liste exhaustive. Elle n'est donc pas couplée aux potentielles évolutions de wording de Story 3.2.

### Structure exacte du contrat JSON attendu

Le payload `/system/diagnostics` doit désormais inclure :

**ATTENTION :** Les noms de champs ci-dessous (`summary`, `rooms`, `total_equipments`, `counts_by_status`, `counts_by_reason`, `primary_aggregated_status`) ne sont pas de simples exemples illustratifs. Ils constituent le **contrat cible attendu** pour l'implémentation `dev-story` et doivent être implémentés tels quels.

```json
{
  "action": "system.diagnostics",
  "status": "ok",
  "payload": {
    "summary": {
      "primary_aggregated_status": "partially_published",
      "total_equipments": 8,
      "counts_by_status": {
        "published": 5,
        "excluded": 2,
        "ambiguous": 1,
        "not_supported": 0,
        "infra_incident": 0
      },
      "counts_by_reason": {
        "sure": 5,
        "excluded_eqlogic": 2,
        "ambiguous_skipped": 1
      }
    },
    "rooms": [
      {
        "object_id": 5,
        "object_name": "Salon",
        "summary": { /* ... même structure de summary ... */ }
      }
      // ...
    ],
    "equipments": [
      // ... liste existante INCHANGÉE ...
    ]
  }
}
```

### Dev Agent Guardrails

- **Ne pas faire :**
  - Implémenter le rendu UI de ces agrégats. C'est le rôle de Story 3.4.
  - Modifier la taxonomie des statuts (Story 3.1) ou la logique des raisons (Story 3.2).
  - Introduire des agrégations côté JS.
  - Rendre le statut `Partiel` sans les compteurs qui l'expliquent.
- **Faire :**
  - Implémenter la logique d'agrégation (compteurs + statut prioritaire) purement en Python.
  - Étendre le contrat de données backend pour exposer ces agrégats.
  - Écrire des tests unitaires robustes qui couvrent les règles de priorité et les cas limites.

## Testing Requirements

- **Invariants V1.1 touchés :**
  - Backend source unique des statuts.
  - Déterminisme et explicabilité.
  - Cohérence sémantique entre les niveaux de lecture.
- **Action Item Rétro Epic 2 :**
  - **AI-6 — Tests d'agrégation cohérents avec les statuts individuels (Story 3.3)** : Cet action item est au cœur de la story. Les tests unitaires Python doivent être écrits en même temps que le code de la logique d'agrégation. Chaque règle de priorité et chaque cas de mixité doit être couvert par un test de cohérence.
- **Tests unitaires obligatoires (Python) :**
  - Tester la fonction d'agrégation avec un jeu de données pour chaque règle de priorité (ex: un équipement `Incident` doit forcer le statut agrégé `Incident infrastructure`).
  - Tester les cas où tous les équipements ont le même statut (`100% Publié`, `100% Exclu`).
  - Tester le cas mixte `Publié`/`Exclu` qui doit résulter en `Partiellement publié` avec les bons compteurs.
  - Tester le cas d'une pièce vide (doit retourner un état neutre et des compteurs à zéro).
- **Tests de contrat / non-régression obligatoires :**
  - Ajouter un test qui valide la structure du nouveau payload d'agrégation.
  - S'assurer que les suites de tests pour 3.1 et 3.2 restent vertes.
  - Vérifier que l'ajout des agrégats ne modifie pas les données de statuts individuels déjà présentes dans le contrat.
- **Tests UI :**
  - **Non requis** pour cette story. Le travail est purement backend.

## Dependencies and Sequencing

- **Dépendances amont :** Story 3.1 (fournit la taxonomie des statuts), Story 3.2 (dépendance *data-level* et *non-bloquante* pour l'algorithme, fournit uniquement les clés brutes `reason_code` à compter).
- **Dépendance aval :** Story 3.4 (consommera le contrat d'agrégation pour l'afficher dans l'UI).
- Cette story est autonome et ne dépend pas des Epics 1, 2 ou 4.

## Risks / Points de vigilance

- **Complexité des règles :** Les règles de priorité doivent rester simples et documentées pour ne pas devenir une boîte noire. La hiérarchie proposée est conçue pour être simple.
- **Performance :** L'agrégation doit être performante, même sur de grandes installations. La logique doit être optimisée pour éviter des boucles inutiles. Étant calculée une fois par sync, l'impact devrait être maîtrisé.
- **Dérive sémantique :** Le plus grand risque est de créer une synthèse qui masque la réalité. La combinaison `statut prioritaire + compteurs détaillés` est le garde-fou principal contre ce risque.

## Références

- **Sources actives de vérité:**
  - `_bmad-output/planning-artifacts/active-cycle-manifest.md`
  - `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md` (Epic 3, Story 3.3)
  - `_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md` (Avertissement sur le statut `Partiel`)
  - `_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md` (Backend source unique)
  - `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
  - `_bmad-output/implementation-artifacts/epic-2-retro-2026-03-25.md` (Action Item AI-6)
- **Contexte secondaire autorisé:**
  - `_bmad-output/implementation-artifacts/3-1-taxonomie-principale-de-statuts-d-equipement.md` (si créé)
  - `_bmad-output/implementation-artifacts/3-2-reason-code-stables-raison-lisible-et-action-recommandee.md` (si créé)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6 (claude-sonnet-4-6), Claude Opus 4.6 (claude-opus-4-6) — correction post-review

### Debug Log References

- Approche : module pur `models/aggregation.py` + intégration minimaliste dans `http_server.py`
- RED/GREEN/REFACTOR appliqué : tests écrits en premier (ModuleNotFoundError confirmé), puis module créé
- 524 tests verts en fin d'implémentation (stories 3.1, 3.2, existants + Story 3.3)
- Identifiant canonique `infra_incident` vérifié dans `_STATUS_CODE_MAP` existant (ligne 1347 de http_server.py)

### Completion Notes List

- **Task 1** : `resources/daemon/models/aggregation.py` créé avec `build_summary()` et `compute_primary_aggregated_status()`. Algorithme strictement conforme à la hiérarchie des Dev Notes. Statut `empty` retourné si `total_equipments == 0`. `counts_by_status` initialisé avec les 5 statuts canoniques de 3.1. `counts_by_reason` agrégeant les `reason_code` bruts sans logique sémantique (découplé de 3.2).
- **Task 2** : `_handle_system_diagnostics` étendu avec `rooms_equips` dict tracé en parallèle du loop existant. Appel unique de `build_summary(equipments)` pour le global, et un appel par pièce. Clé `equipments` strictement inchangée (AC 6 validé par les 27 tests préexistants).
- **Task 3** : 23 tests unitaires dans `test_aggregation.py` (règles de priorité, cas vides, stabilité, counts_by_reason). 6 tests de contrat dans `test_diagnostic_endpoint.py` (présence des 3 clés payload, structure summary, structure rooms, non-régression equipments, stabilité somme counts, partially_published pièce réelle).
- **AC 5 (symétrie pièce/global)** : garanti par l'appel à la même fonction `build_summary()` dans les deux cas.
- **Action Item AI-6** : couverture exhaustive — une règle par test de priorité, cas mixtes, cas vides, tests de contrat.
- **Task 4 (post-review)** : normalisation défensive des `status_code` non canoniques vers `not_supported` dans `build_summary()`. Garantit l'invariant `sum(counts_by_status) == total_equipments` même en cas de donnée inattendue. 2 tests unitaires ajoutés (status_code inconnu seul, status_code inconnu en mixité). 128 tests verts, 0 régression.

### File List

- `resources/daemon/models/aggregation.py` (nouveau)
- `resources/daemon/transport/http_server.py` (modifié — import + `_handle_system_diagnostics`)
- `resources/daemon/tests/unit/test_aggregation.py` (nouveau — 23 tests unitaires)
- `resources/daemon/tests/unit/test_diagnostic_endpoint.py` (modifié — 6 tests de contrat ajoutés)
- `_bmad-output/implementation-artifacts/3-3-agregations-piece-et-global-coherentes.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-26: Création de la story 3.3.
- 2026-03-26: Implémentation Story 3.3 — module d'agrégation, intégration endpoint, tests (524 verts, 0 régression).
- 2026-03-26: Correction post-review — normalisation défensive des status_code non canoniques (128 tests verts, 0 régression).
- 2026-03-26: Closeout — code review PASS, smoke test terrain PASS, PR mergée, story passée à done.

---
**Story revision date:** 2026-03-26
**Cycle:** Post-MVP Phase 1 - V1.1 Pilotable
**Status:** done