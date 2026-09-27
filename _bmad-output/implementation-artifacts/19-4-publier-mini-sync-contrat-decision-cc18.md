# Story 19.4: "Publier" en mini-sync sur le contrat de décision (CC-18)

Status: ready-for-dev

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

**Given** l'état réel du code (vérifié par lecture directe, pas supposé) : `resolve_published_scope` (`models/published_scope.py:77`) résout `app["published_scope"]` une fois par sync (`http_server.py:1335`), mais **aucun** chemin du sync ne filtre ensuite une publication sur ce scope — le sync ne connaît aujourd'hui aucun gate de scope. Le seul filtre d'inclusion réel, `_scope_entry_is_included` (`http_server.py:448-457`, `scope_entry["effective_state"] == "include"` ou repli sur l'éligibilité), n'est appelé **que** par la boucle "Publier" (l.3310). Un **troisième** endroit, `_apply_pending_scope_flags` (l.630), réimplémente la **même** comparaison `effective_state == "include"` en ligne (l.641) au lieu d'appeler `_scope_entry_is_included` — c'est la duplication locale réelle à corriger, pas une divergence supposée avec le sync
**When** cette story est implémentée
**Then** `_scope_entry_is_included` reste l'unique fonction d'inclusion de scope, continue d'être utilisée par "Publier" **sans réimplémentation**, et `_apply_pending_scope_flags` est corrigé pour **appeler** `_scope_entry_is_included` au lieu de dupliquer la comparaison en ligne
**And** aucune fausse affirmation n'est faite sur un quelconque "même filtre que le sync" au sens d'un filtre déjà partagé : le sync n'a et n'aura toujours aucun gate de scope à l'issue de cette story (hors périmètre) — seule la consolidation `_apply_pending_scope_flags`/`_scope_entry_is_included` est en jeu ici
**And** un test vérifie que `_apply_pending_scope_flags` et le chemin "Publier" produisent la **même** valeur d'inclusion pour un même `scope_entry`/`eligibility` en passant tous deux par `_scope_entry_is_included` (pas une réimplémentation locale divergente).

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
**And** ce test peut être écrit dans cette story si Story 19.3 est déjà `done` au moment du dev-story de 19.4 ; sinon il est documenté comme dépendance à couvrir dès que les deux stories sont branchées (à ne pas laisser silencieusement non couvert).

## UI Impact

- **UI Impact:** Oui — requalifié depuis la formulation initiale ("Non"). Le bouton "Publier" ne change pas d'apparence, mais son **effet observable** change réellement : des équipements aujourd'hui publiés (à tort) resteront visibles jusqu'ici, et disparaîtront de Home Assistant après un clic sur "Publier" une fois la dépublication explicite (AC4) implémentée — un utilisateur peut légitimement se demander pourquoi une entité disparaît sans avoir rien supprimé explicitement. Cette story passe donc par le statut `ready-for-UX-validation` avant `done` (cf. `docs/bmad-parcours-rapide-complet.md`), avec une preuve par clic réel documentant ce comportement (dépublication visible) en plus des preuves terrain (i)/(ii).

## Impact sur la production et retour arrière

Changement de comportement réel et volontaire : des équipements `sure_mapping` aujourd'hui refusés par "Publier" deviendront publiables (AC1) ; des équipements exclus par override, aujourd'hui potentiellement publiés à tort par "Publier", seront refusés (AC2) ; des équipements publiés devenus invalides seront explicitement dépubliés au clic sur "Publier" (AC4), alors qu'ils ne l'étaient pas avant ; des secondaires dont l'éligibilité a changé depuis le dernier sync suivront désormais leur décision fraîche plutôt qu'une décision figée (AC6). C'est une correction de bug assumée (CC-18), pas une régression. Retour arrière : revert de la story/PR — `_should_attempt_publish`/`_secondary_publishable`/`_apply_pending_scope_flags` reviennent à leur logique propre actuelle (avec CC-18 réintroduit), sans migration de données ; aucun override existant n'est perdu par le revert.

## Preuve terrain

Trois preuves terrain distinctes, recherchées en priorité comme cas réels sur la box (192.168.1.21) en lecture seule (via l'outil de parité de Story 19.1 si applicable) ; à défaut de cas réel, repli explicite par test avec mention documentée de ce repli :
- (i) un équipement de confiance `sure_mapping` refusé aujourd'hui par le bouton "Publier" devient publiable après la correction.
- (ii) un équipement refusé par le sync (ex. `publication_excluded_*`) reste refusé par "Publier" sur une pièce (le bug symétrique corrigé).
- (iii) **preuve par absence** : après correction, chercher explicitement un équipement `sure_mapping` sur la box qui **resterait** refusé par "Publier" malgré une confiance publiable par le sync — cette recherche doit rapporter **zéro** cas restant (constat négatif documenté, pas seulement un cas positif isolé en (i)) ; à défaut d'un périmètre suffisant sur la box pour garantir cette absence, repli documenté sur un test exhaustif couvrant toutes les valeurs de `confidence` publiables (`sure`, `probable`, `sure_mapping`).

**Gate d'inventaire obligatoire (convention repo, `sprint-status.yaml`) :** cette story modifie un comportement de publication/dépublication réelle vers Home Assistant — elle ne peut passer à `done` qu'après le gate obligatoire d'inventaire des entités avant/après déploiement (0 erreur), en plus de la preuve par clic réel (UI Impact `Oui`, ci-dessus) et des preuves (i)/(ii)/(iii).

## Invariants concernés

I2, I4, I6, I7 (mêmes garanties que le sync, puisque "Publier" consomme désormais `evaluate_equipment()`). I11 doit rester respecté (chaque candidat/secondaire garde sa propre décision lors du mini-sync, cohérent avec Story 19.2 — en particulier via la correction AC6 de `_secondary_publishable`).

## Points fermés

- **CC-18** — fermé par cette story (AC1, AC2, preuve terrain (i) et (ii)) : "Publier" accepte désormais ce que le sync accepte, et refuse ce que le sync refuse.
- **CC-04**, **CC-14** (P1) — non couverts par le contexte technique fourni pour cette story (aucune information reliant explicitement CC-04/CC-14 au bouton "Publier" ou au filtre de scope) : **restent ouverts**. Recherche exhaustive confirmée (grep `_bmad-output/` pour "CC-14") : aucun contenu ne relie CC-14 à la divergence de filtre de scope corrigée par AC3/AC7 — la parité sync/Publier/surface/aperçu établie par cette story (AC7) **ne constitue pas une preuve de fermeture de CC-14** et ne doit jamais être présentée comme telle sans définition source explicite de CC-14. À rattacher explicitement lors d'un futur `correct-course` uniquement si le mainteneur fournit cette définition, sinon à traiter comme un incrément séparé.

## Tasks / Subtasks

<!-- Story terrain : daemon / MQTT / publication / bouton Publier / box réelle → Task 0 Pre-flight terrain injectée. -->

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY)
  - [ ] Dry-run : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Identifier, via le rapport de parité (Story 19.1) ou une recherche manuelle en lecture seule, des cas réels correspondant aux preuves (i), (ii) et (iii)
  - [ ] **Interdiction explicite (DANGER) :** ne jamais invoquer `--cleanup-discovery` ni `--stop-daemon-cleanup` (`scripts/deploy-to-box.sh:95,97`) pendant cette recherche de cas réels ni pendant la vérification post-correction — ces flags republient des messages MQTT retained **vides** sur les topics discovery, effaçant les entités déjà publiées et rendant impossible de distinguer une dépublication **causée par la correction** d'une dépublication causée par le script lui-même. Déploiement standard uniquement.

- [ ] Task 1 — Brancher les 4 fonctions du chemin "Publier" sur `evaluate_equipment()` (AC1, AC2, AC6)
  - [ ] `_should_attempt_publish` (`http_server.py:475-490`) : remplacer le tuple de confiance codé en dur et la vérification du `reason` de sync antérieur par un appel à `evaluate_equipment()` avec les entrées courantes (overrides persistés à cet instant, `confidence_policy` stocké)
  - [ ] `_secondary_publishable` (`http_server.py:493-502`) : remplacer la lecture de `publication_decision_ref.should_publish` (décision **figée** du dernier sync) par la décision **fraîchement recalculée** pour ce secondaire (AC6)
  - [ ] `_publish_mapping_for_action` (`http_server.py:505+`) et `_handle_action_execute` (`http_server.py:3018`) : adapter l'orchestration pour consommer les décisions fraîches ci-dessus, sans dupliquer de logique de décision propre
  - [ ] Vérifier que la résolution des overrides est identique à celle du sync (mêmes fonctions `list_overrides`/`list_equipment_overrides`, pas de logique parallèle)

- [ ] Task 2 — Consolider le filtre de scope, éliminer la réimplémentation locale (AC3)
  - [ ] Ne **pas** chercher un filtre de scope "déjà partagé avec le sync" (le sync n'en applique aucun aujourd'hui, constaté par lecture directe — hors périmètre de cette story)
  - [ ] Corriger `_apply_pending_scope_flags` (`http_server.py:630`, comparaison en ligne l.641) pour qu'il **appelle** `_scope_entry_is_included` (`http_server.py:448-457`) au lieu de réimplémenter la même comparaison `effective_state == "include"`
  - [ ] Vérifier que "Publier" (l.3310) continue d'utiliser cette même fonction, sans changement de comportement sur ce point précis

- [ ] Task 3 — Mini-sync complet avec dépublication explicite (AC4, AC5)
  - [ ] Écrire la nouvelle décision dans `app["publications"]` pour l'ensemble du périmètre réévalué
  - [ ] Dépublier explicitement (MQTT + `app["publications"]`) tout équipement passant de publié à refusé, symétriquement au nettoyage déjà fait au sync pour les équipements disparus
  - [ ] Vérifier l'idempotence pour les équipements déjà publiés et toujours valides (AC5)

- [ ] Task 4 — Test de parité croisée à 4 points d'appel (AC7)
  - [ ] Écrire un test comparant sync / "Publier" / surface pièce / aperçu sur au moins un cas `sure_mapping` et un cas d'exclusion par override
  - [ ] Si Story 19.3 n'est pas encore `done` au moment du dev-story, documenter explicitement cette dépendance non couverte dans les Completion Notes plutôt que de l'omettre silencieusement

- [ ] Task 5 — Preuve terrain (i), (ii) et (iii)
  - [ ] Rechercher des cas réels sur la box ; documenter le résultat observé
  - [ ] Rechercher explicitement l'absence de cas résiduel `sure_mapping` refusé par "Publier" (preuve (iii))
  - [ ] Si aucun cas réel trouvé pour (i), (ii) et/ou (iii), écrire le test de repli correspondant et le documenter explicitement comme tel dans les Completion Notes
  - [ ] Documenter la preuve par clic réel de la dépublication visible (UI Impact `Oui`), avant passage `ready-for-UX-validation` → `done`

- [ ] Task 6 — Tests (AC1-AC7)
  - [ ] `test_story_19_4_publier_mini_sync_cc18.py` (préfixe `test_story_19_4_*`)
  - [ ] Suite complète `pytest tests/unit -q` : 0 régression

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

### Debug Log References

### Completion Notes List

- **create-story** — 2026-09-27 — statut résultant : `ready-for-dev`. Story documentaire créée directement (skill officielle non exposée cette session).

### File List
