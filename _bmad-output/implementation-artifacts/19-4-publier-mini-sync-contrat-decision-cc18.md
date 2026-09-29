# Story 19.4: "Publier" en mini-sync sur le contrat de décision (CC-18)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un utilisateur,
I want que le bouton "Publier" — orchestré par `_handle_action_execute` (`resources/daemon/transport/http_server.py:3018`), qui appelle `_scope_entry_is_included` (l.448-457) puis `_should_attempt_publish` (l.475-490) puis `_publish_mapping_for_action` (l.505+, lequel gate chaque secondaire via `_secondary_publishable`, l.493-502) — réévalue la publication via `evaluate_equipment()` avec les entrées courantes, exactement comme le sync, et dépublie explicitement ce qui devient refusé,
so that "Publier" accepte les mêmes équipements que le sync (ex. confiance `sure_mapping`), refuse les mêmes équipements exclus par override, et ne laisse jamais un équipement (principal ou secondaire) publié à tort par un simple ajout sans nettoyage ni réévaluation fraîche.

**Parcours : complet.**

## Acceptance Criteria

**AC1 — "Publier" accepte ce que le sync accepte (mini-sync, pas de règle divergente)**

**Given** un équipement de confiance `sure_mapping` que le sync publie normalement, mais que le bouton "Publier" refuse aujourd'hui — bug confirmé par lecture directe : `_should_attempt_publish` (`http_server.py:475-490`) code en dur `mapping.confidence not in ("sure", "probable")`, omettant silencieusement `"sure_mapping"` (présent dans `_PUBLISHABLE_CONFIDENCES` de `decide_publication.py:57`) et ignorant totalement le `confidence_policy` configuré ; elle vérifie en plus le `reason` de la **précédente** décision de sync contre un tuple fixe incluant deux codes jamais produits en pratique par `decide_publication` (`unknown_skipped`, `ignore_skipped` — code mort)
**When** l'utilisateur clique sur "Publier" pour cet équipement/cette pièce
**Then** `_should_attempt_publish` appelle `evaluate_equipment()` avec les entrées courantes (overrides persistés à cet instant, politique de confiance stockée), comme le fait le sync — plus de tuple de confiance codé en dur, plus de dépendance à un `reason` de sync antérieur potentiellement obsolète
**And** l'équipement `sure_mapping` devient publiable via "Publier"
**And** un test explicite reproduit ce cas précis et vérifie la publication effective.

**AC2 — "Publier" refuse ce que le sync refuse (bug symétrique corrigé)**

**Given** un équipement refusé par le sync via un override d'exclusion (ex. `publication_excluded_eqlogic`/`publication_excluded_command`, Story 16.3)
**When** l'utilisateur tente de publier cette pièce via le bouton "Publier"
**Then** cet équipement reste refusé par "Publier", exactement comme par le sync (CC-18, second sens de la divergence)
**And** un test explicite reproduit ce cas et vérifie l'absence de publication.

**AC3 — Un seul filtre de scope, jamais de réimplémentation locale (correction de la formulation initiale)**

**Given** une fonction pure de filtre de scope unique, appliquée après `evaluate_equipment()` par le sync et par « Publier »
**When** cette story est implémentée
**Then** cette fonction est le filtre de scope unique, sans réimplémentation locale, et est appliquée après la décision par le sync comme par « Publier »
**And** le changement de sync est documenté dans l'impact et le rollback ; l'effet est nul si 19-1 relève zéro état explicite
**And** un golden vérifie l'égalité de l'ensemble global filtré entre les deux chemins.

**AC4 — Mini-sync = écrit la décision ET dépublie ce qui devient refusé**

**Given** un équipement précédemment publié qui, à la réévaluation par "Publier", devient refusé (ex. override d'exclusion ajouté entre-temps)
**When** l'utilisateur clique sur "Publier"
**Then** la nouvelle décision est écrite dans `app["publications"]`
**And** l'équipement passé de publié à refusé est **explicitement dépublié** (nettoyage symétrique à celui déjà fait au sync pour les équipements disparus) — jamais laissé publié par un simple comportement d'ajout
**And** un test explicite vérifie qu'un équipement démarrant "publié" puis "refusé après override" est bien dépublié par l'action "Publier" (pas seulement absent du nouvel ajout).

**AC5 — Pas de simple ajout : "Publier" est un mini-sync complet sur son périmètre**

**Given** l'action "Publier" sur une pièce/un équipement
**When** elle s'exécute
**Then** elle réévalue l'ensemble du périmètre concerné (pas seulement les équipements pas encore publiés) — comportement mini-sync, jamais un simple ajout incrémental
**And** un test vérifie qu'un équipement déjà publié et toujours valide n'est ni dépublié ni republié inutilement (idempotence), tandis qu'un équipement devenu invalide est bien dépublié (AC4).

**AC6 — `_secondary_publishable` réévalue aussi, ne lit plus une décision figée du dernier sync**

**Given** l'état actuel constaté : `_secondary_publishable` (`http_server.py:493-502`) autorise la republication d'un secondaire uniquement si `secondary.publication_decision_ref.should_publish` est `True` — une valeur **mise en cache lors du dernier sync**, jamais réévaluée par "Publier" lui-même
**When** un override modifie l'éligibilité d'un secondaire **entre** le dernier sync et le clic sur "Publier" (sans qu'un nouveau sync n'ait eu lieu depuis)
**Then** `_secondary_publishable` (ou son équivalent après refactoring) s'appuie sur la décision **fraîchement recalculée** par `evaluate_equipment()` pour ce secondaire, jamais sur le `publication_decision_ref` figé du dernier sync
**And** un test explicite reproduit ce cas (override ajouté après le dernier sync, avant le clic sur "Publier") et vérifie que le secondaire suit la décision fraîche, pas la décision mise en cache.

**AC7 — Parité à 4 points d'appel (sync, "Publier", surface pièce, aperçu)**

**Given** un même équipement/override, évalué successivement par le sync (Story 19.1), le bouton "Publier" (cette story), la surface de navigation par pièce et l'aperçu à blanc (Story 19.3)
**When** les 4 points d'appel sont tous branchés sur `evaluate_equipment()`
**Then** un test de parité croisée (au moins un cas de confiance `sure_mapping` et un cas d'exclusion par override) vérifie que les 4 points d'appel produisent **exactement** la même décision pour ce même équipement/override — c'est la preuve concrète de la "vérité unique" visée par l'epic, pas seulement une parité sync-vs-Publier isolée
**And** golden 59 et `test_cc08_publisher_registry_matrix.py` couvrent cette parité, sans échappement conditionnel.

## UI Impact

- **UI Impact:** Oui — requalifié depuis la formulation initiale ("Non"). Le bouton "Publier" ne change pas d'apparence, mais son **effet observable** change réellement : des équipements aujourd'hui publiés (à tort) resteront visibles jusqu'ici, et disparaîtront de Home Assistant après un clic sur "Publier" une fois la dépublication explicite (AC4) implémentée — un utilisateur peut légitimement se demander pourquoi une entité disparaît sans avoir rien supprimé explicitement. Cette story passe donc par le statut `ready-for-UX-validation` avant `done` (cf. `docs/bmad-parcours-rapide-complet.md`), avec une preuve par clic réel documentant ce comportement (dépublication visible) en plus des preuves terrain (i)/(ii).

## Impact sur la production et retour arrière

Changement de comportement réel et volontaire : des équipements `sure_mapping` aujourd'hui refusés par "Publier" deviendront publiables (AC1) ; des équipements exclus par override, aujourd'hui potentiellement publiés à tort par "Publier", seront refusés (AC2) ; des équipements publiés devenus invalides seront explicitement dépubliés au clic sur "Publier" (AC4), alors qu'ils ne l'étaient pas avant ; des secondaires dont l'éligibilité a changé depuis le dernier sync suivront désormais leur décision fraîche plutôt qu'une décision figée (AC6). Le sync applique également le filtre de scope pur après la décision ; effet nul si 19-1 a relevé zéro état explicite. C'est une correction de bug assumée (CC-18), pas une régression. Retour arrière : revert de la story/PR — le filtre partagé, `_should_attempt_publish` et `_secondary_publishable` reviennent à leur logique actuelle (avec CC-18 réintroduit), sans migration de données ; aucun override existant n'est perdu par le revert.

**Précisions ajoutées en review (unité 6, mesure avant fusion du 29/09) :**

- Un revert **ne republie pas** les équipements dépubliés entre-temps par le filtre de scope (AC3) : la mesure terrain A′ du 29/09 relève **zéro** équipement dépublié par ce filtre à ce jour (aucun état explicite exclu n'a de topic publié, principal ou secondaire), donc il n'y a aujourd'hui rien à republier en cas de revert — cette précision documente le comportement pour une future transition de scope, pas un effet déjà observé.
- « Publier » ne publie **pas d'état initial** (CC-29, hors périmètre de cette story) : une entité publiée pour la première fois par un clic sur « Publier » reste `unknown` côté Home Assistant jusqu'à son premier changement d'état. C'est un comportement voulu, pas un oubli : la valeur courante relevée au moment du sync le plus récent pourrait déjà être périmée au moment du clic, donc mieux vaut `unknown` explicite qu'une valeur silencieusement obsolète.

## Preuve terrain

Preuve terrain obligatoire : (ii) exclusion UI équipement sans risque, cliquer « Publier » sur une pièce, constater la non-publication, puis le retour auto. Pour (i)/(iii), aucun mapper `sure_mapping` n'existe dans `main` : fallback par test assumé et documenté. **Écart vérifié avec `origin/main` :** `decide_publication.py:57` n'est pas l'unique référence globale à `sure_mapping` (on en trouve aussi dans `cause_mapping.py`, `http_server.py` et des tests), mais c'est la référence de politique de publication pertinente ici.

**Gate d'inventaire obligatoire (convention repo, `sprint-status.yaml`) :** cette story modifie un comportement de publication/dépublication réelle vers Home Assistant — elle ne peut passer à `done` qu'après le gate obligatoire d'inventaire des entités avant/après déploiement (0 erreur), en plus de la preuve par clic réel (UI Impact `Oui`, ci-dessus) et des preuves (i)/(ii)/(iii).

## Invariants concernés

I2, I4, I6, I7 (mêmes garanties que le sync, puisque "Publier" consomme désormais `evaluate_equipment()`). I11 doit rester respecté (chaque candidat/secondaire garde sa propre décision lors du mini-sync, cohérent avec Story 19.2 — en particulier via la correction AC6 de `_secondary_publishable`).

## Points fermés

- **CC-18** — fermé par cette story (AC1, AC2, preuve terrain (i) et (ii)) : "Publier" accepte désormais ce que le sync accepte, et refuse ce que le sync refuse.
- **CC-04** — partiellement fermé. Volet contrat : décision canonique par commande (19-0 AC1) et deux temporalités (19-3 AC6). Volet UI (jargon, gabarit, surface unique) : étape 4.
- **CC-14 P1** (parité simulation/sync + pas de silence) — fermé par 19-0 AC1 + 19-3 AC7 + 19-4 AC7 ; P0 fait à l'étape 1 ; P2 hors périmètre.

## Tasks / Subtasks

<!-- Story terrain : daemon / MQTT / publication / bouton Publier / box réelle → Task 0 Pre-flight terrain injectée. -->

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY)
  - [ ] Dry-run : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Identifier, via le rapport de parité (Story 19.1) ou une recherche manuelle en lecture seule, des cas réels correspondant aux preuves (i), (ii) et (iii)
  - [ ] **Interdiction explicite (DANGER) :** ne jamais invoquer `--cleanup-discovery` ni `--stop-daemon-cleanup` (`scripts/deploy-to-box.sh:95,97`) pendant cette recherche de cas réels ni pendant la vérification post-correction — ces flags republient des messages MQTT retained **vides** sur les topics discovery, effaçant les entités déjà publiées et rendant impossible de distinguer une dépublication **causée par la correction** d'une dépublication causée par le script lui-même. Déploiement standard uniquement.

- [x] Task 1 — Brancher les 4 fonctions du chemin "Publier" sur `evaluate_equipment()` (AC1, AC2, AC6)
  - [x] Réévaluer avec la topologie, `app["confidence_policy"]` et les overrides persistés courants, jamais `app["mappings"]` ; `_should_attempt_publish` (`http_server.py:475-490`) ne conserve ni tuple de confiance codé en dur ni `reason` de sync antérieur. — Fait : `_evaluate_for_action()` (unité 4) ; `_should_attempt_publish` supprimée (unité 5). Tests P1, R1.
  - [x] `_secondary_publishable` (`http_server.py:493-502`) : remplacer la lecture de `publication_decision_ref.should_publish` (décision **figée** du dernier sync) par la décision **fraîchement recalculée** pour ce secondaire (AC6) — Fait : « Publier » ne l'appelle plus ; chaque secondaire suit sa décision fraîche (`evaluation.secondary_decisions`, publiées par `_publish_additional_sensors` comme au sync). `_secondary_publishable` ne sert plus qu'à `_republish_all_from_cache` (republication depuis le cache, qui relit par nature la dernière décision). Tests P4, P7.
  - [x] `_publish_mapping_for_action` (`http_server.py:505+`) et `_handle_action_execute` (`http_server.py:3018`) : adapter l'orchestration pour consommer les décisions fraîches ci-dessus, sans dupliquer de logique de décision propre ; supprimer le couplage des secondaires au succès du principal (`http_server.py:516-518`). — Fait : `_handle_action_execute` passe par `apply_publication_decision()`, partagé avec le sync ; `_publish_mapping_for_action` supprimée (unité 5).
  - [x] Vérifier que la résolution des overrides est identique à celle du sync (mêmes fonctions `list_overrides`/`list_equipment_overrides`, pas de logique parallèle) — relus au clic par ces mêmes fonctions. Tests P2, P4, P5.

- [x] Task 2 — Filtre de scope pur unique (AC3)
  - [x] Appliquer le filtre partagé après `evaluate_equipment()` au sync et à « Publier », sans logique locale concurrente. — Fait (unité 5) : `_scope_entry_is_included` puis `_scope_excluded_decision()` dans les deux chemins ; la surface applique le même filtre. `_apply_pending_scope_flags` reste inchangée : elle ne décide pas l'inclusion, elle calcule seulement les drapeaux « changements en attente » affichés. Tests Q1 à Q3, Q5.
  - [x] Documenter le changement sync dans l'impact/rollback et vérifier, par golden, l'égalité de l'ensemble global filtré ; effet nul si 19-1 mesure zéro état explicite. — Golden Q4 (corpus de 59 équipements) ; mesure A′ = 0 avant fusion.

- [x] Task 3 — Mini-sync complet avec dépublication explicite (AC4, AC5)
  - [x] Écrire la nouvelle décision dans `app["publications"]` pour l'ensemble du périmètre réévalué — `apply_publication_decision()`. Tests P2, Q1.
  - [x] Dépublier explicitement (MQTT + `app["publications"]`) tout équipement passant de publié à refusé, symétriquement au nettoyage déjà fait au sync pour les équipements disparus — `_unpublish_refused_candidates()`, par candidat, partagée avec le sync. Tests P2, P4, P5, P8 ; T1 à T8.
  - [x] Vérifier l'idempotence pour les équipements déjà publiés et toujours valides (AC5) — Test P3.

- [x] Task 4 — Test de parité croisée à 4 points d'appel (AC7)
  - [x] Écrire un test comparant sync / "Publier" / surface pièce / aperçu sur au moins un cas `sure_mapping` et un cas d'exclusion par override, dans golden 59 et `test_cc08_publisher_registry_matrix.py`. — R1 (`sure_mapping`) et R2 (exclusion par override) dans `test_story_19_4_scope_et_parite.py` ; golden 59 : Q4 ; la matrice CC-08 porte désormais sur `apply_publication_decision()`, partagé par le sync et « Publier ».

- [ ] Task 5 — Preuve terrain (ii) et fallback documenté (i)/(iii)
  - [ ] Exclure un équipement sans risque dans l'UI, cliquer « Publier » sur une pièce, constater la non-publication puis le retour auto.
  - [ ] Documenter les tests de fallback pour (i)/(iii), car aucun mapper `sure_mapping` n'existe dans `main`.
  - [ ] Documenter la preuve par clic réel de la dépublication visible (UI Impact `Oui`), avant passage `ready-for-UX-validation` → `done`

- [x] Task 6 — Tests (AC1-AC7)
  - [x] `test_story_19_4_guard_publisher_calls.py`, `test_story_19_4_c1_per_candidate.py`, `test_story_19_4_publier_mini_sync.py`, `test_story_19_4_scope_et_parite.py` (préfixe `test_story_19_4_*`)
  - [x] `test_cc08_publisher_registry_matrix.py` (parité AC7)
  - [x] Suite complète `python3 -m pytest -q` : **1961 passed** (1958 + T8, P9, P10 de l'unité 7), `node --test tests/unit/*.node.test.js` : **305 passed** — 0 régression

## Dev Notes

### Contexte pipeline

- Cette story dépend de Story 19.1 (sync migré, `evaluate_equipment()` déjà en production sur le sync) et bénéficie de Story 19.2 (découplage I11) pour garantir que le mini-sync de "Publier" respecte aussi le découplage par candidat.
- CC-18 est une divergence à double sens : trop permissif dans un cas (exclusion ignorée), trop restrictif dans l'autre (`sure_mapping` refusé) — les deux sens doivent être corrigés et prouvés séparément (AC1/preuve (i) vs AC2/preuve (ii)).

### Dev Agent Guardrails

- "Publier" ne doit plus contenir de logique de décision ou de scope propre — uniquement des appels à `evaluate_equipment()` et à la fonction de filtre de scope partagée.
- La dépublication explicite (AC4) doit réutiliser le mécanisme de nettoyage déjà existant au sync pour les équipements disparus, pas une nouvelle implémentation parallèle.
- Ne jamais transformer "Publier" en simple "ajout" : c'est un mini-sync sur son périmètre, avec réévaluation complète.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh`.
- Référence : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.

### Project Structure Notes

- Fichiers à toucher (probable) : `resources/daemon/transport/http_server.py` [MODIFIÉ — `_should_attempt_publish` (l.475-490), `_secondary_publishable` (l.493-502), `_publish_mapping_for_action` (l.505+), `_handle_action_execute` (l.3018), `_apply_pending_scope_flags` (l.630, consolidé sur `_scope_entry_is_included` l.448-457) + dépublication explicite], `resources/daemon/tests/unit/test_story_19_4_*.py` [NOUVEAU].

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic-19] — CC-18, règle "Publier" actée (mini-sync + dépublication explicite), règle de scope actée.
- [Source: _bmad-output/implementation-artifacts/19-0-contrat-pur-command-decision-evaluate-equipment.md] — `evaluate_equipment()` consommé par cette story.
- [Source: _bmad-output/implementation-artifacts/19-1-sync-migre-contrat-decision-sans-changement-comportement.md] — outil de parité, cas réels potentiels pour les preuves (i)/(ii).
- [Source: _bmad-output/implementation-artifacts/16-3-overrides-publication-exclusion-explicite.md] — reason_codes `publication_excluded_*`, mécanisme de nettoyage au sync pour équipements disparus.
- [Source: resources/daemon/transport/http_server.py#L448-L457] — `_scope_entry_is_included`, unique filtre d'inclusion de scope réel.
- [Source: resources/daemon/transport/http_server.py#L475-L502] — `_should_attempt_publish`/`_secondary_publishable`, logique de confiance/secondaire à corriger.
- [Source: resources/daemon/transport/http_server.py#L630] — `_apply_pending_scope_flags`, réimplémentation locale de l'inclusion de scope à consolider (AC3).
- [Source: resources/daemon/transport/http_server.py#L3018] — `_handle_action_execute`, orchestrateur du chemin "Publier".
- [Source: resources/daemon/models/decide_publication.py#L57] — `_PUBLISHABLE_CONFIDENCES`, référence de confiance omise par le bug CC-18.
- [Source: _bmad-output/implementation-artifacts/19-3-surface-piece-apercu-contrat-decision-cc03-cc19.md] — surface pièce/aperçu consommés par le test de parité croisée (AC7).

## Dev Agent Record

### Agent Model Used

claude-cli/claude-sonnet-5 (unités 3b à 6, dev-story + review + mesure avant fusion).

### Debug Log References

### Completion Notes List

- **create-story** — 2026-09-27 — statut résultant : `ready-for-dev`. Story documentaire créée directement (skill officielle non exposée cette session).
- **Unité 3b-1** (`fd93c5b`, `e6b851d`) — extraction pure de `apply_publication_decision()` + tests de dépublication par candidat (C1), préalable au correctif de sync.
- **Unité 3b/C1** (`34ef7ed`, `f0bb4c2`) — C1 : dépublication par candidat dans le sync ; écarts de garde-fou déclarés **S5/S6** (détail ci-dessous).
- **Unité 4** (`f203c74`, `3508e98`) — « Publier » en mini-sync : `evaluate_equipment()` frais + `apply_publication_decision()` + dépublication par candidat (AC1, AC2, AC4-AC6) ; garde-fou écart déclaré **S3/S4** (phase Publier sous patch `evaluate_equipment` + trace MQTT).
- **Unité 5** (`118fe35`) — AC3 : filtre de scope pur appliqué au sync ; AC7 : parité vérifiée aux 4 points d'appel (sync, Publier, surface pièce, aperçu) ; retrait de l'ancien chemin « publier » (code mort après migration).
- **Écarts de garde-fou déclarés** (détail : `resources/daemon/tests/fixtures/story_19_4_guard/README.md`) — assumés et testés, pas des régressions :
  - **S3** (unité 4) : l'eq 6000 (`ha_missing_command_topic`), que le sync refuse, n'est plus publié par « Publier » : 81 ⇒ 80 appels, MQTT 81 ⇒ 80, disponibilité 47 ⇒ 46.
  - **S4** (unité 4) : sur la forme 579/585, « Publier » publie les 3 secondaires acceptés et leur disponibilité `online` (0 ⇒ 3 appels, 0 ⇒ 1 message), toujours sans `unpublish`.
  - **S5** (unité 3b) : passage `sure_probable` ⇒ `sure_only` : toujours 18 appels `unpublish` (un par équipement), mais 583 et 457 gardent leurs secondaires `sure` ; effacements MQTT 30 ⇒ 23, disponibilité 48 ⇒ 46.
  - **S6** (unité 3b) : le secondaire refusé `jeedom2ha_628_5980` est dépublié seul ; disponibilité inchangée.
- **Unité 7** (revue Codex de la PR #180, correctifs préparés par ClaudeBox) — P1 : le domaine HA entre dans l'identité d'un secondaire (`_candidate_key`), un secondaire retypé sous le même `cmd_id` ne laisse plus de topic fantôme (test T8) ; P2 : « Publier » compte en erreur un équipement dont un secondaire accepté n'a pas pu être publié, principal accepté ou refusé (tests P9, P10) ; corrections de ce document et du corps de la PR.
- **Tests** : 1961 tests Python (`python3 -m pytest -q`, testpaths `tests` + `resources/daemon/tests`) et 305 tests node (`node --test tests/unit/*.node.test.js`) — tous verts, 0 régression, rejoués au moment de cette review.
- **Unité 6** (`371e525`, `07180fa`) — mesure A′ avant fusion, box en lecture seule stricte : **0** équipement exclu (scope) avec un topic discovery publié, principal ou secondaire — cf. section « Rejeu avant fusion » de `19-4-mesure-terrain-2026-09-29.md`.

### File List

`git diff --stat origin/main...HEAD` après l'unité 7 (41 fichiers, 21381 insertions, 446 suppressions) :

- `resources/daemon/transport/http_server.py` [MODIFIÉ — 907 lignes touchées]
- `resources/daemon/tests/unit/test_story_19_4_guard_publisher_calls.py` [NOUVEAU]
- `resources/daemon/tests/unit/test_story_19_4_c1_per_candidate.py` [NOUVEAU]
- `resources/daemon/tests/unit/test_story_19_4_publier_mini_sync.py` [NOUVEAU]
- `resources/daemon/tests/unit/test_story_19_4_scope_et_parite.py` [NOUVEAU]
- `resources/daemon/tests/unit/test_story_19_4_candidate_node_ids.py` [NOUVEAU]
- `resources/daemon/tests/unit/test_cc08_publisher_registry_matrix.py` [MODIFIÉ — parité AC7]
- `resources/daemon/tests/unit/test_story_11_2_eq554_multi_domain.py` [MODIFIÉ]
- `resources/daemon/tests/unit/test_story_5_2_execute_publier.py` [MODIFIÉ]
- `resources/daemon/tests/unit/test_story_5_2_integration.py` [MODIFIÉ]
- `resources/daemon/tests/unit/test_story_5_3_integration.py` [MODIFIÉ]
- `resources/daemon/tests/fixtures/story_19_4_guard/` [NOUVEAU — 26 fichiers : traces de référence S1 à S6 + README]
- `_bmad-output/implementation-artifacts/19-4-note-conception.md` [NOUVEAU]
- `_bmad-output/implementation-artifacts/19-4-mesure-terrain-2026-09-29.md` [NOUVEAU, complété unité 6]
- `_bmad-output/implementation-artifacts/19-4-publier-mini-sync-contrat-decision-cc18.md` [MODIFIÉ — ce document]
- `_bmad-output/implementation-artifacts/sprint-status.yaml` [MODIFIÉ — statut `review`]

## Change Log

- 2026-09-27 — `create-story` — statut `ready-for-dev`.
- 2026-09-29 — unités 3b à 5 (C1, mini-sync « Publier », AC3/AC7) implémentées et testées, tête `118fe35`.
- 2026-09-29 (soir) — unité 6 : rejeu mesure A′ (0, tous topics), documentation Tasks 1-4/6, Dev Agent Record, statut `review`.
- 2026-09-29 (soir) — unité 7 : correctifs de la revue Codex (P1 domaine HA dans l'identité des secondaires, P2 échecs des secondaires propagés au résultat de « Publier »), sous-tâches cochées, écarts S3 à S6 corrigés.
