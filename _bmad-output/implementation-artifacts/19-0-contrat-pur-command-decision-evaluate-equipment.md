# Story 19.0: Contrat pur `CommandDecision` / `evaluate_equipment()`

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un mainteneur,
I want une fonction pure `evaluate_equipment()` et un type `CommandDecision` (une décision par `cmd_id`) qui formalisent une décision de publication unique et partageable,
so that les 4 points d'appel du pipeline (sync, navigation par pièce, aperçu, bouton "Publier") pourront à terme consommer exactement la même logique de décision au lieu de la recalculer chacun différemment.

**Parcours : complet.**

## Acceptance Criteria

**AC1 — `CommandDecision` par `cmd_id`, y compris les commandes non couvertes**

**Given** un équipement dont certaines commandes sont mappées, éligibles ou explicitement overridées, et d'autres non couvertes par le mapping
**When** `evaluate_equipment()` est appelé
**Then** la sortie contient une `CommandDecision` pour **chaque** `cmd_id` de l'équipement, y compris les commandes non couvertes
**And** chaque `CommandDecision` porte un `reason` non-null (I6), y compris pour les commandes non couvertes (raison explicite « commande non couverte »)
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
**And** I3 (un `cmd_id`/candidat avec `should_publish=True` a passé les 4 premières étapes positivement) est vérifié par un test dédié sur la sortie de `evaluate_equipment()` (confidence `sure`/`probable`/`sure_mapping` + `is_valid=True` + `ha_entity_type` dans `PRODUCT_SCOPE` ⇒ `should_publish=True`, et réciproquement)
**And** I5 (tout équipement éligible produit ses 3 sous-blocs) est vérifié par un test dédié : `evaluate_equipment()` calcule le mapping avec le registre injecté, fusionne les overrides, valide puis décide — sans mapping ni projection fournis en entrée — et produit toujours une `CommandDecision`/décision de publication, jamais `None`, jamais une décision omise
**And** I1 (équipement inéligible) produit une décision refusée de niveau 1 avec un code de raison d'éligibilité, sans mapping ni projection, et une `CommandDecision` refusée par `cmd_id` ; un test dédié le vérifie.
**And** `evaluate_equipment()` ne prend **aucun** paramètre `published_scope` — un test explicite vérifie que la signature de la fonction ne contient pas ce paramètre (le filtre de scope reste hors périmètre de cette story, appliqué en aval par une fonction de filtre partagée définie ultérieurement).

## UI Impact

- **UI Impact:** Non — fonction pure côté daemon, aucun branchement dans un point d'appel existant, aucun changement visible par l'utilisateur.

## Impact sur la production et retour arrière

Aucun changement de comportement en production : `evaluate_equipment()` est une **nouvelle** fonction pure, non appelée par aucun point d'appel existant à l'issue de cette story. `decide_publication()`, le sync, la navigation par pièce, l'aperçu et le bouton "Publier" continuent de fonctionner exactement comme avant, sans modification. Retour arrière : revert de la story/PR (suppression du nouveau module), sans migration de données, sans impact sur `data/ha_overrides.json` ni sur l'état MQTT publié.

## Preuve terrain

Aucune preuve terrain requise — fonction pure, aucun branchement dans le pipeline exécuté en production. Preuve exclusivement par tests unitaires (AC1-AC5) et par un harnais de parité (comparaison programmatique `evaluate_equipment()` vs `decide_publication()` actuel sur un corpus de cas synthétiques et sur `tests/fixtures/golden_corpus/`), sans aucun déploiement sur la box. Précision : il n'existe aujourd'hui **aucun** outil dédié d'export en lecture seule de la topologie Jeedom (aucun CLI/fonction de dump) — le seul précédent comparable est un test golden-file (`resources/daemon/tests/unit/test_story_8_4_golden_file.py`, fixtures `tests/fixtures/golden_corpus/sync_payload.json`/`expected_sync_snapshot.json`) qui construit son instantané via les réponses HTTP `/sync`/`/diagnostics`, pas via un export dédié. Le harnais de parité de cette story doit donc s'appuyer sur ces mêmes fixtures existantes, jamais sur un accès direct à la box.

## Invariants concernés

I1, I2, I3, I4, I5, I6, I7 : vérifiés par des tests dédiés sur la sortie de `evaluate_equipment()` (AC5). I11 : non concerné (story 19.2).

## Points fermés

Aucun CC-xx fermé par cette story : c'est une fondation pure, non branchée. CC-03 et CC-19 sont fermés par Story 19.3, CC-18 par Story 19.4 (cf. `epics-projection-engine.md#Epic-19`). CC-04 — partiellement fermé. Volet contrat : décision canonique par commande (19-0 AC1) et deux temporalités (19-3 AC6). Volet UI (jargon, gabarit, surface unique) : étape 4. CC-14 P1 (parité simulation/sync + pas de silence) — fermé par 19-0 AC1 + 19-3 AC7 + 19-4 AC7 ; P0 fait à l'étape 1 ; P2 hors périmètre.

## Tasks / Subtasks

- [x] Task 1 — Définir `CommandDecision` (AC1, AC4)
  - [x] Nouveau type de données `CommandDecision` (dataclass ou équivalent), un par `cmd_id`, portant au minimum `cmd_id`, `should_publish`, `reason`, `reason_details`, `step` (1|2|2b|3|4, niveau I4 du premier échec), avec la taxonomie `publication_forced`, `publication_excluded_eqlogic`, `publication_excluded_command`, `sure_mapping`; alias `no_supported_generic_type` → `no_generic_type_configured` (`http_server.py:1949`), et raison explicite pour commande non couverte.
  - [x] S'assurer qu'aucune commande connue de l'équipement n'est omise, y compris les commandes non mappées

- [x] Task 2 — Implémenter `evaluate_equipment()` (AC1-AC5)
  - [x] Signature : équipement/snapshot topologie, résultat d'éligibilité déjà calculé (paramètre obligatoire, jamais recalculé en interne), politique de confiance, overrides persistés, overrides proposés (paramètre optionnel), registre de mappeurs injectable ; pour un équipement éligible, calculer mapping → fusion overrides → validation → décision, sans mapping ni projection en entrée.
  - [x] Sortie : décision principale + décisions secondaires + liste de `CommandDecision` (une par `cmd_id`)
  - [x] Point unique de fusion overrides persistés + overrides proposés
  - [x] Aucune mutation des objets d'entrée (deepcopy défensif si nécessaire, jamais de mutation en place façon `_preview_mapping_view` actuel) : `apply_type_override` retourne le même objet sans override (`overrides.py:366-369,399`), alors que le sync modifie aujourd'hui `additional_mappings[index]` (`http_server.py:253`), `projection_validity` / `publication_decision_ref` (`http_server.py:1430/1441`).
  - [x] Aucun paramètre `published_scope`

- [x] Task 3 — Réutiliser la logique existante de `decide_publication()` sans duplication de règles (AC5)
  - [x] `evaluate_equipment()` s'appuie sur (ou encapsule) `decide_publication()` existant pour la décision principale/secondaire, sans dupliquer les niveaux 1-4 déjà actés (I1-I7)
  - [x] Aucune logique MQTT/broker/cache introduite (I7)

- [x] Task 4 — Harnais de parité (préparatoire à Story 19.1)
  - [x] Script/outil de test (non exposé en production) qui exécute `evaluate_equipment()` et `decide_publication()` sur le même corpus (`tests/fixtures/golden_corpus/`) et rapporte tout écart — `resources/daemon/tests/tools/parity_harness_19_0.py` (`compute_parity_report()`), consommé par `resources/daemon/tests/unit/test_story_19_0_parity_golden_corpus.py`.
  - [x] Documenter dans cette story les écarts constatés (attendus : aucun, sinon les lister explicitement) — **aucun écart constaté** : `compute_parity_report()` exécuté sur `tests/fixtures/golden_corpus/sync_payload.json` (59 eqLogics, 57 éligibles / 2 inéligibles) retourne une liste vide (`test_ac3_parity_harness_golden_corpus_no_discrepancy`).

- [x] Task 5 — Tests (AC1-AC5)
  - [x] `test_story_19_0_evaluate_equipment_contract.py` (préfixe `test_story_19_0_*`) : couverture AC1-AC5, y compris les tests de non-mutation (deepcopy) et le test de signature (absence de `published_scope`)
  - [x] Suite complète `pytest tests/unit -q` : 0 régression vs. baseline actuelle

## Dev Notes

### Contexte pipeline

- Pipeline canonique 5 étapes (D1/D7) : `assess_all (éligibilité) → map (2) → validate_projection (3) → decide_publication (4) → publish (5)`. **Précision (corrige une formulation antérieure imprécise) :** `evaluate_equipment()` n'est **pas** un simple remplacement de l'étape 4 — elle **encapsule** `decide_publication()` (Task 3) pour la décision principale/secondaire, **et ajoute** une granularité nouvelle qui n'existait pas avant cette story : une `CommandDecision` par `cmd_id` (AC1), y compris pour les commandes non couvertes. Cette story ne fait que définir cette fonction élargie — aucun branchement dans un point d'appel réel (celui-ci arrive en Story 19.1+).
- 4 points d'appel actuels destinés à converger (hors périmètre de cette story, cf. 19.1-19.4) : sync (`_do_handle_action_sync` → `decide_publication`, `resources/daemon/models/decide_publication.py`), navigation par pièce (`_build_mapping_override_tree`, Story 16.8), aperçu (`_handle_overrides_preview`), bouton "Publier" (`_should_attempt_publish`).
- **Non-mutation (AC4) — pointeur exact :** `_preview_mapping_view` (`resources/daemon/transport/http_server.py:2202`) mute aujourd'hui `mapping.projection_validity` en place à la ligne `resources/daemon/transport/http_server.py:2210` (juste après le calcul de `validate_projection(...)` en l.2209, avant l'appel à `decide_publication` en l.2211) — c'est précisément ce comportement que `evaluate_equipment()` ne doit **jamais** reproduire ; le test de régression dédié (AC4) doit cibler cette ligne comme cas de référence.
- **Registre de mappeurs injectable (Task 2) — état actuel :** `MapperRegistry` (`resources/daemon/mapping/registry.py:20`) a aujourd'hui un constructeur sans paramètre (`__init__(self) -> None`, l.23-35) qui code en dur une liste ordonnée de 10 mappeurs ; les appelants instancient directement `MapperRegistry()`. `evaluate_equipment()` doit accepter cette instance en **paramètre injectable** (jamais l'instancier elle-même en interne), pour permettre un registre de test/mock dans le harnais de parité (Task 4) sans dépendre d'une instanciation globale.
- **`decide_publication()`/`validate_projection()` injectables (coordination avec Story 19.1) :** signatures actuelles — `decide_publication(mapping, confidence_policy="sure_probable", product_scope=None, publication_override=None)` (`resources/daemon/models/decide_publication.py:60`) et `validate_projection(ha_entity_type, capabilities)` (`resources/daemon/validation/ha_component_registry.py:155`). `evaluate_equipment()` doit accepter ces deux fonctions en paramètres injectables optionnels (valeur par défaut = les fonctions réelles ci-dessus), afin que Story 19.1 puisse substituer des doublures instrumentées dans son harnais de parité sans modifier `evaluate_equipment()` elle-même.

### Dev Agent Guardrails

- Ne pas introduire de nouveau chemin parallèle : `evaluate_equipment()` doit rester une extension/encapsulation de la logique actée en Story 16.3 (`decide_publication`), pas une réécriture divergente des règles I1-I7.
- Aucune dépendance vers MQTT/broker/cache (I7).
- Ne jamais ajouter `published_scope` comme paramètre d'entrée — c'est un filtre appliqué en aval (cf. epic, Story 19.4).

### Project Structure Notes

- Fichiers à toucher (probable, à confirmer en dev-story) : nouveau module (ex. `resources/daemon/models/evaluate_equipment.py` ou extension de `decide_publication.py`), `resources/daemon/tests/unit/test_story_19_0_*.py` [NOUVEAU].
- Aucun fichier de point d'appel existant (`transport/http_server.py`, `sync/state.py`, `sync/command.py`) ne doit être modifié par cette story — le branchement est hors périmètre (Story 19.1+).

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic-19] — epic canonique, contexte CC-03/CC-18/CC-19/CC-04/CC-14, invariants I1-I7 + I11.
- [Source: resources/daemon/models/decide_publication.py] — `decide_publication()`, invariants I1-I7 existants.
- [Source: resources/daemon/models/mapping.py] — `PublicationDecision`, `reason_details` (Story 16.3).
- [Source: _bmad-output/implementation-artifacts/16-3-overrides-publication-exclusion-explicite.md] — précédent direct pour I2/I4/I6/I7 et le style `reason_details`.

## Dev Agent Record

### Agent Model Used

clawcode (Claude, agent de code jeedom2ha) — session autonome en arrière-plan, worktree dédié `story/19-0-contrat-pur-command-decision`.

### Debug Log References

- TDD strict : `test_i7_no_mqtt_broker_or_disk_io_in_module_source` a d'abord échoué (faux positif — recherche naïve de sous-chaîne `"mqtt"` matchant le docstring du module, pas du code exécutable). Corrigé par une inspection AST (`ast.parse`/`ast.walk`, nœuds `Import`/`ImportFrom`/`Call`/`Attribute`/`Name` uniquement) qui ignore docstrings/commentaires.
- Aucun autre échec de test bloquant — TDD mené test par test, incrément par incrément.

### Completion Notes List

- **create-story** — 2026-09-27 — statut résultant : `ready-for-dev`. Story documentaire créée directement (skill officielle `bmad-create-story` non exposée dans cette session — cf. journal `/tmp/jeedom2ha-etape3-stories.log`), en répliquant fidèlement `template.md` et les conventions de `16-3-overrides-publication-exclusion-explicite.md`.
- **dev-story** — 2026-09-27 — statut résultant : `ready-for-review`. Skill officielle `bmad-dev-story` non exposée dans cette session d'exécution autonome (outillage identique à la limitation déjà notée pour `create-story` ci-dessus) ; le workflow dev-story (TDD strict test-par-test, mise à jour Tasks/Subtasks + Dev Agent Record, aucune modification des points d'appel existants) a été suivi manuellement en répliquant sa discipline, conformément à la convention déjà établie sur cette story pour `create-story`.
- **alignement de statut** — 2026-09-28 — statut résultant : `done`. PR #167 fusionnée (`8f19575`), relue par ClaudeBox ; pas de preuve terrain requise par la story (voir section « Preuve terrain » ci-dessus).
- `CommandDecision` + `evaluate_equipment()` implémentés dans un nouveau module pur (`resources/daemon/models/evaluate_equipment.py`), sans aucune instanciation interne de `MapperRegistry` (injecté), sans I/O (I7), avec `decide_publication()`/`validate_projection()` réutilisés tels quels (injectables, valeur par défaut = implémentations réelles) — aucune duplication des règles I1-I7.
- Non-mutation (AC4) : `eq`, `snapshot`, `eligibility` deep-copiés en entrée ; toute mise à jour de `MappingResult`/`PublicationDecision` passe par `dataclasses.replace()`, jamais par affectation d'attribut en place — vérifié par un test de régression dédié ciblant explicitement le bug `_preview_mapping_view` (`http_server.py:2210`).
- Fusion overrides (AC3) : un unique point de fusion (`_merge_override_layer`), overrides proposés prioritaires sur les persistés, dicts d'entrée jamais mutés. Fusion **champ par champ** à une même clé (schéma v2 : une entrée peut porter à la fois `ha_entity_type` et `publication_override`) — corrigé suite à la revue bot Codex, cf. note ci-dessous.
- Harnais de parité (Task 4) : `resources/daemon/tests/tools/parity_harness_19_0.py` (`compute_parity_report()`) exécute le pipeline classique (`decide_publication()` appelé directement, réplique fidèle de `_do_handle_action_sync` hors MQTT/publisher) et `evaluate_equipment()` (overrides persistés seuls) sur le corpus doré `tests/fixtures/golden_corpus/sync_payload.json` — **aucun écart constaté** sur les 57 équipements éligibles (2 inéligibles, 59 au total).
- 35 tests unitaires dédiés (`test_story_19_0_evaluate_equipment_contract.py`) + 2 tests de parité golden-corpus (`test_story_19_0_parity_golden_corpus.py`) — tous verts. Suite complète (voir File List / commit final pour le décompte exact `pytest`/Node/PHP/`bash -n`).
- Aucun fichier de point d'appel modifié — `http_server.py`, `state.py`, `command.py` strictement intacts (vérifié par `git diff --stat`, cf. commit final).
- **Revue bot Codex (PR #167, commit `7e43533`)** — 2 remarques P2 (`COMMENTED`, non bloquantes), les deux confirmées réelles et corrigées :
  1. `_merge_override_layer` remplaçait l'entrée entière d'une clé `proposed` plutôt que fusionner ses champs avec l'entrée `persisted` correspondante ; un override "proposé" partiel (ex. seulement `publication_override`) pouvait donc faire disparaître silencieusement un champ persisté non recouvert (ex. `ha_entity_type`) au lieu de le fusionner (schéma v2, `mapping/overrides.py`). Corrigé par une fusion champ par champ (`base.update(entry)` par clé) ; couvert par `test_ac3_merge_is_field_level_not_full_entry_replacement`.
  2. `decision.mapping_result` (dans `_decide_for_mapping`) restait figé sur le mapping intermédiaire de l'étape 3 (`pipeline_step_reached=3`, secondaires non finalisées), au lieu du mapping final de l'étape 4 — `EquipmentEvaluation.equipment_decision.mapping_result` pouvait donc présenter un état obsolète par rapport à `EquipmentEvaluation.mapping`. Corrigé en introduisant `_finalize_decision_mapping_result` (posée après finalisation des secondaires) ; couvert par `test_thread1_equipment_decision_mapping_result_reflects_final_mapping`. Limite structurelle assumée et documentée dans le code : une boucle auto-référente `mapping.publication_decision_ref.mapping_result is mapping` n'est pas représentable avec des dataclasses immuables (`dataclasses.replace`), contrairement au pipeline classique qui mute les deux objets en place ; `pipeline_step_reached=4` et `additional_mappings` finalisées restent en revanche garantis cohérents des deux côtés.

### File List

- `resources/daemon/models/evaluate_equipment.py` — NOUVEAU — `CommandDecision`, `EquipmentEvaluation`, `evaluate_equipment()`.
- `resources/daemon/tests/unit/test_story_19_0_evaluate_equipment_contract.py` — NOUVEAU — 35 tests (AC1-AC5, I1-I7, signature, non-mutation, 2 tests dédiés à la revue bot Codex).
- `resources/daemon/tests/tools/__init__.py` — NOUVEAU — package vide (convention `tests/unit`, `tests/integration`).
- `resources/daemon/tests/tools/parity_harness_19_0.py` — NOUVEAU — harnais de parité (Task 4).
- `resources/daemon/tests/unit/test_story_19_0_parity_golden_corpus.py` — NOUVEAU — 2 tests de parité sur corpus doré (AC3).
