# Story 19.0: Contrat pur `CommandDecision` / `evaluate_equipment()`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un mainteneur,
I want une fonction pure `evaluate_equipment()` et un type `CommandDecision` (une décision par `cmd_id`) qui formalisent une décision de publication unique et partageable,
so that les 4 points d'appel du pipeline (sync, navigation par pièce, aperçu, bouton "Publier") pourront à terme consommer exactement la même logique de décision au lieu de la recalculer chacun différemment.

## Acceptance Criteria

**AC1 — `CommandDecision` par `cmd_id`, y compris les commandes non couvertes**

**Given** un équipement dont certaines commandes sont mappées, éligibles ou explicitement overridées, et d'autres non couvertes par le mapping
**When** `evaluate_equipment()` est appelé
**Then** la sortie contient une `CommandDecision` pour **chaque** `cmd_id` de l'équipement, y compris les commandes non couvertes
**And** chaque `CommandDecision` porte un `reason` non-null (I6), y compris pour les commandes non couvertes (ex. `reason="cmd_not_mapped"` ou équivalent explicite)
**And** un test unitaire vérifie que le nombre de `CommandDecision` produites est strictement égal au nombre de `cmd_id` connus de l'équipement en entrée.

**AC2 — Éligibilité jamais recalculée en interne (racine de CC-03)**

**Given** un résultat d'éligibilité déjà calculé en amont (paramètre d'entrée de `evaluate_equipment()`)
**When** `evaluate_equipment()` évalue la décision
**Then** la fonction **consomme** ce résultat d'éligibilité tel quel et ne le recalcule jamais elle-même
**And** un test explicite prouve qu'un mock d'éligibilité "refusée" fourni en entrée produit une décision refusée, sans que `evaluate_equipment()` n'appelle une quelconque fonction d'éligibilité en interne (vérifié par spy/mock : zéro appel à `assess_eligibility` ou équivalent depuis `evaluate_equipment()`).

**AC3 — Fusion unique overrides persistés + overrides proposés (optionnel)**

**Given** des overrides persistés et, en option, des overrides proposés (non encore sauvegardés — cas de l'aperçu/preview)
**When** `evaluate_equipment()` est appelé avec les deux jeux d'overrides
**Then** la fusion overrides persistés + overrides proposés est effectuée en **un seul point** de la fonction (pas de fusion dupliquée par point d'appel)
**And** un test vérifie que fournir uniquement des overrides persistés produit un résultat identique à l'appel actuel de `decide_publication()` sur le même cas (parité de référence, préparatoire à Story 19.1).

**AC4 — Non-mutation stricte des objets d'entrée**

**Given** un équipement/snapshot topologie, un résultat d'éligibilité, une politique de confiance et des overrides passés en entrée
**When** `evaluate_equipment()` s'exécute, y compris en mode "avec overrides proposés" (cas preview)
**Then** aucun objet d'entrée n'est muté (vérifié par comparaison `deepcopy` avant/après dans les tests) — en particulier, `evaluate_equipment()` ne reproduit **jamais** le comportement actuel de `_preview_mapping_view` qui mute `mapping.projection_validity` en place
**And** un test de régression dédié échoue si un futur changement réintroduit une mutation en place.

**AC5 — I1-I7 respectés, `published_scope` hors périmètre**

**Given** les invariants I1-I7 déjà en vigueur dans `decide_publication()` (Story 16.3)
**When** `evaluate_equipment()` est implémenté
**Then** I2 (projection invalide ⇒ jamais publié, même avec override), I4 (premier échec dans l'ordre 1→2→3→4 fait foi, jamais écrasé en aval), I6 (`reason` non-null) et I7 (aucune logique MQTT/broker/cache dans la fonction) sont vérifiés par des tests dédiés, portés de `test_step4_decide_publication.py`
**And** `evaluate_equipment()` ne prend **aucun** paramètre `published_scope` — un test explicite vérifie que la signature de la fonction ne contient pas ce paramètre (le filtre de scope reste hors périmètre de cette story, appliqué en aval par une fonction de filtre partagée définie ultérieurement).

## UI Impact

- **UI Impact:** Non — fonction pure côté daemon, aucun branchement dans un point d'appel existant, aucun changement visible par l'utilisateur.

## Impact sur la production et retour arrière

Aucun changement de comportement en production : `evaluate_equipment()` est une **nouvelle** fonction pure, non appelée par aucun point d'appel existant à l'issue de cette story. `decide_publication()`, le sync, la navigation par pièce, l'aperçu et le bouton "Publier" continuent de fonctionner exactement comme avant, sans modification. Retour arrière : revert de la story/PR (suppression du nouveau module), sans migration de données, sans impact sur `data/ha_overrides.json` ni sur l'état MQTT publié.

## Preuve terrain

Aucune preuve terrain requise — fonction pure, aucun branchement dans le pipeline exécuté en production. Preuve exclusivement par tests unitaires (AC1-AC5) et par un harnais de parité (comparaison programmatique `evaluate_equipment()` vs `decide_publication()` actuel sur un corpus de cas synthétiques et sur `tests/fixtures/golden_corpus/`), sans aucun déploiement sur la box.

## Invariants concernés

I1, I2, I4, I6, I7 (vérifiés par tests dédiés). I3, I5, I8 non concernés par cette story (I8 relève de Story 19.2 ; I3/I5 hors du périmètre de cette fonction, à ne pas régresser ailleurs).

## Points fermés

Aucun CC-xx fermé par cette story : c'est une fondation pure, non branchée. CC-03, CC-18, CC-19, CC-04, CC-14 restent tous ouverts et sont traités par les stories 19.1 à 19.4.

## Tasks / Subtasks

- [ ] Task 1 — Définir `CommandDecision` (AC1, AC4)
  - [ ] Nouveau type de données `CommandDecision` (dataclass ou équivalent), un par `cmd_id`, portant au minimum `cmd_id`, `should_publish`, `reason`, `reason_details` (cohérent avec `PublicationDecision.reason_details` existant, Story 16.3)
  - [ ] S'assurer qu'aucune commande connue de l'équipement n'est omise, y compris les commandes non mappées

- [ ] Task 2 — Implémenter `evaluate_equipment()` (AC1-AC5)
  - [ ] Signature : équipement/snapshot topologie, résultat d'éligibilité déjà calculé (paramètre obligatoire, jamais recalculé en interne), politique de confiance, overrides persistés, overrides proposés (paramètre optionnel), registre de mappeurs injectable
  - [ ] Sortie : décision principale + décisions secondaires + liste de `CommandDecision` (une par `cmd_id`)
  - [ ] Point unique de fusion overrides persistés + overrides proposés
  - [ ] Aucune mutation des objets d'entrée (deepcopy défensif si nécessaire, jamais de mutation en place façon `_preview_mapping_view` actuel)
  - [ ] Aucun paramètre `published_scope`

- [ ] Task 3 — Réutiliser la logique existante de `decide_publication()` sans duplication de règles (AC5)
  - [ ] `evaluate_equipment()` s'appuie sur (ou encapsule) `decide_publication()` existant pour la décision principale/secondaire, sans dupliquer les niveaux 1-4 déjà actés (I1-I7)
  - [ ] Aucune logique MQTT/broker/cache introduite (I7)

- [ ] Task 4 — Harnais de parité (préparatoire à Story 19.1)
  - [ ] Script/outil de test (non exposé en production) qui exécute `evaluate_equipment()` et `decide_publication()` sur le même corpus (`tests/fixtures/golden_corpus/`) et rapporte tout écart
  - [ ] Documenter dans cette story les écarts constatés (attendus : aucun, sinon les lister explicitement)

- [ ] Task 5 — Tests (AC1-AC5)
  - [ ] `test_story_19_0_evaluate_equipment_contract.py` (préfixe `test_story_19_0_*`) : couverture AC1-AC5, y compris les tests de non-mutation (deepcopy) et le test de signature (absence de `published_scope`)
  - [ ] Suite complète `pytest tests/unit -q` : 0 régression vs. baseline actuelle

## Dev Notes

### Contexte pipeline

- Pipeline canonique 5 étapes (D1/D7) : `assess_all (éligibilité) → map (2) → validate_projection (3) → decide_publication (4) → publish (5)`. `evaluate_equipment()` se substitue à terme à l'étape 4 pour les 4 points d'appel, mais cette story ne fait que la définir — aucun branchement.
- 4 points d'appel actuels destinés à converger (hors périmètre de cette story, cf. 19.1-19.4) : sync (`_do_handle_action_sync` → `decide_publication`, `resources/daemon/models/decide_publication.py`), navigation par pièce (`_build_mapping_override_tree`, Story 16.8), aperçu (`_handle_overrides_preview`), bouton "Publier" (`_should_attempt_publish`).
- `_preview_mapping_view` mute aujourd'hui `mapping.projection_validity` en place — comportement à ne **jamais** reproduire dans `evaluate_equipment()` (AC4).

### Dev Agent Guardrails

- Ne pas introduire de nouveau chemin parallèle : `evaluate_equipment()` doit rester une extension/encapsulation de la logique actée en Story 16.3 (`decide_publication`), pas une réécriture divergente des règles I1-I7.
- Aucune dépendance vers MQTT/broker/cache (I7).
- Ne jamais ajouter `published_scope` comme paramètre d'entrée — c'est un filtre appliqué en aval (cf. epic, Story 19.4).

### Project Structure Notes

- Fichiers à toucher (probable, à confirmer en dev-story) : nouveau module (ex. `resources/daemon/models/evaluate_equipment.py` ou extension de `decide_publication.py`), `resources/daemon/tests/unit/test_story_19_0_*.py` [NOUVEAU].
- Aucun fichier de point d'appel existant (`transport/http_server.py`, `sync/state.py`, `sync/command.py`) ne doit être modifié par cette story — le branchement est hors périmètre (Story 19.1+).

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic-19] — epic canonique, contexte CC-03/CC-18/CC-19/CC-04/CC-14, invariants I1-I8.
- [Source: resources/daemon/models/decide_publication.py] — `decide_publication()`, invariants I1-I7 existants.
- [Source: resources/daemon/models/mapping.py] — `PublicationDecision`, `reason_details` (Story 16.3).
- [Source: _bmad-output/implementation-artifacts/16-3-overrides-publication-exclusion-explicite.md] — précédent direct pour I2/I4/I6/I7 et le style `reason_details`.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- **create-story** — 2026-09-27 — statut résultant : `ready-for-dev`. Story documentaire créée directement (skill officielle `bmad-create-story` non exposée dans cette session — cf. journal `/tmp/jeedom2ha-etape3-stories.log`), en répliquant fidèlement `template.md` et les conventions de `16-3-overrides-publication-exclusion-explicite.md`.

### File List
