# Story 19.4: "Publier" en mini-sync sur le contrat de décision (CC-18)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un utilisateur,
I want que le bouton "Publier" (`_should_attempt_publish`) réévalue la publication via `evaluate_equipment()` avec les entrées courantes, exactement comme le sync, et dépublie explicitement ce qui devient refusé,
so that "Publier" accepte les mêmes équipements que le sync (ex. confiance `sure_mapping`), refuse les mêmes équipements exclus par override, et ne laisse jamais un équipement publié à tort par un simple ajout sans nettoyage.

## Acceptance Criteria

**AC1 — "Publier" accepte ce que le sync accepte (mini-sync, pas de règle divergente)**

**Given** un équipement de confiance `sure_mapping` que le sync publie normalement, mais que le bouton "Publier" refuse aujourd'hui (CC-18, divergence de règle de confiance)
**When** l'utilisateur clique sur "Publier" pour cet équipement/cette pièce
**Then** `_should_attempt_publish` appelle `evaluate_equipment()` avec les entrées courantes (overrides persistés à cet instant, politique de confiance stockée), comme le fait le sync
**And** l'équipement `sure_mapping` devient publiable via "Publier"
**And** un test explicite reproduit ce cas précis et vérifie la publication effective.

**AC2 — "Publier" refuse ce que le sync refuse (bug symétrique corrigé)**

**Given** un équipement refusé par le sync via un override d'exclusion (ex. `publication_excluded_eqlogic`/`publication_excluded_command`, Story 16.3)
**When** l'utilisateur tente de publier cette pièce via le bouton "Publier"
**Then** cet équipement reste refusé par "Publier", exactement comme par le sync (CC-18, second sens de la divergence)
**And** un test explicite reproduit ce cas et vérifie l'absence de publication.

**AC3 — Même filtre de scope que le sync**

**Given** `published_scope` résolu par `resolve_published_scope`
**When** le bouton "Publier" détermine le périmètre à publier
**Then** il applique le **même** filtre de scope partagé que le sync (une seule fonction de filtre partagée, cf. epic) — jamais une logique de scope dupliquée ou divergente
**And** un test vérifie que le filtre appliqué par "Publier" est celui de la fonction partagée (pas une réimplémentation locale).

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

## UI Impact

- **UI Impact:** Non — le bouton "Publier" existe déjà côté UI ; cette story change son comportement interne (backend), pas son apparence ni son interaction. (Si le dev-story constate un changement d'affichage nécessaire, par exemple un message de confirmation de dépublication, il doit requalifier `UI Impact` à `Oui` et faire passer la story par `ready-for-UX-validation` — à trancher explicitement en dev-story si le cas se présente.)

## Impact sur la production et retour arrière

Changement de comportement réel et volontaire : des équipements `sure_mapping` aujourd'hui refusés par "Publier" deviendront publiables (AC1) ; des équipements exclus par override, aujourd'hui potentiellement publiés à tort par "Publier", seront refusés (AC2) ; des équipements publiés devenus invalides seront explicitement dépubliés au clic sur "Publier" (AC4), alors qu'ils ne l'étaient pas avant. C'est une correction de bug assumée (CC-18), pas une régression. Retour arrière : revert de la story/PR — `_should_attempt_publish` revient à sa logique de confiance/scope propre actuelle (avec CC-18 réintroduit), sans migration de données ; aucun override existant n'est perdu par le revert.

## Preuve terrain

Deux preuves terrain distinctes, recherchées en priorité comme cas réels sur la box (192.168.1.21) en lecture seule (via l'outil de parité de Story 19.1 si applicable) ; à défaut de cas réel, repli explicite par test avec mention documentée de ce repli :
- (i) un équipement de confiance `sure_mapping` refusé aujourd'hui par le bouton "Publier" devient publiable après la correction.
- (ii) un équipement refusé par le sync (ex. `publication_excluded_*`) reste refusé par "Publier" sur une pièce (le bug symétrique corrigé).

## Invariants concernés

I2, I4, I6, I7 (mêmes garanties que le sync, puisque "Publier" consomme désormais `evaluate_equipment()`). I8 doit rester respecté (chaque candidat/secondaire garde sa propre décision lors du mini-sync, cohérent avec Story 19.2).

## Points fermés

- **CC-18** — fermé par cette story (AC1, AC2, preuve terrain (i) et (ii)) : "Publier" accepte désormais ce que le sync accepte, et refuse ce que le sync refuse.
- **CC-04**, **CC-14** (P1) — non couverts par le contexte technique fourni pour cette story (aucune information reliant explicitement CC-04/CC-14 au bouton "Publier" ou au filtre de scope) : **restent ouverts**. À rattacher explicitement lors d'un futur `correct-course` si leur contenu s'avère couvert par cette convergence, sinon à traiter comme un incrément séparé.

## Tasks / Subtasks

<!-- Story terrain : daemon / MQTT / publication / bouton Publier / box réelle → Task 0 Pre-flight terrain injectée. -->

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY)
  - [ ] Dry-run : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Identifier, via le rapport de parité (Story 19.1) ou une recherche manuelle en lecture seule, des cas réels correspondant aux preuves (i) et (ii)

- [ ] Task 1 — Brancher `_should_attempt_publish` sur `evaluate_equipment()` (AC1, AC2)
  - [ ] Remplacer la logique de confiance/exclusion propre à "Publier" par un appel à `evaluate_equipment()` avec les entrées courantes (overrides persistés à cet instant, politique stockée)
  - [ ] Vérifier que la résolution des overrides est identique à celle du sync (mêmes fonctions `list_overrides`/`list_equipment_overrides`, pas de logique parallèle)

- [ ] Task 2 — Appliquer le même filtre de scope partagé que le sync (AC3)
  - [ ] Identifier ou créer la fonction de filtre de scope partagée (cf. epic — `resolve_published_scope` appliqué en aval, une seule implémentation consommée par sync ET "Publier")
  - [ ] Brancher "Publier" sur cette fonction partagée, retirer toute logique de scope locale à `_should_attempt_publish`

- [ ] Task 3 — Mini-sync complet avec dépublication explicite (AC4, AC5)
  - [ ] Écrire la nouvelle décision dans `app["publications"]` pour l'ensemble du périmètre réévalué
  - [ ] Dépublier explicitement (MQTT + `app["publications"]`) tout équipement passant de publié à refusé, symétriquement au nettoyage déjà fait au sync pour les équipements disparus
  - [ ] Vérifier l'idempotence pour les équipements déjà publiés et toujours valides (AC5)

- [ ] Task 4 — Preuve terrain (i) et (ii)
  - [ ] Rechercher des cas réels sur la box ; documenter le résultat observé
  - [ ] Si aucun cas réel trouvé pour (i) et/ou (ii), écrire le test de repli correspondant et le documenter explicitement comme tel dans les Completion Notes

- [ ] Task 5 — Tests (AC1-AC5)
  - [ ] `test_story_19_4_publier_mini_sync_cc18.py` (préfixe `test_story_19_4_*`)
  - [ ] Suite complète `pytest tests/unit -q` : 0 régression

## Dev Notes

### Contexte pipeline

- Cette story dépend de Story 19.1 (sync migré, `evaluate_equipment()` déjà en production sur le sync) et bénéficie de Story 19.2 (découplage I8) pour garantir que le mini-sync de "Publier" respecte aussi le découplage par candidat.
- CC-18 est une divergence à double sens : trop permissif dans un cas (exclusion ignorée), trop restrictif dans l'autre (`sure_mapping` refusé) — les deux sens doivent être corrigés et prouvés séparément (AC1/preuve (i) vs AC2/preuve (ii)).

### Dev Agent Guardrails

- "Publier" ne doit plus contenir de logique de décision ou de scope propre — uniquement des appels à `evaluate_equipment()` et à la fonction de filtre de scope partagée.
- La dépublication explicite (AC4) doit réutiliser le mécanisme de nettoyage déjà existant au sync pour les équipements disparus, pas une nouvelle implémentation parallèle.
- Ne jamais transformer "Publier" en simple "ajout" : c'est un mini-sync sur son périmètre, avec réévaluation complète.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh`.
- Référence : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.

### Project Structure Notes

- Fichiers à toucher (probable) : `resources/daemon/transport/http_server.py` [MODIFIÉ — `_should_attempt_publish`, câblage `evaluate_equipment()` + filtre de scope partagé + dépublication explicite], fonction de filtre de scope partagée [NOUVEAU ou refactoring de `resolve_published_scope`/`_apply_pending_scope_flags`], `resources/daemon/tests/unit/test_story_19_4_*.py` [NOUVEAU].

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic-19] — CC-18, règle "Publier" actée (mini-sync + dépublication explicite), règle de scope actée.
- [Source: _bmad-output/implementation-artifacts/19-0-contrat-pur-command-decision-evaluate-equipment.md] — `evaluate_equipment()` consommé par cette story.
- [Source: _bmad-output/implementation-artifacts/19-1-sync-migre-contrat-decision-sans-changement-comportement.md] — outil de parité, cas réels potentiels pour les preuves (i)/(ii).
- [Source: _bmad-output/implementation-artifacts/16-3-overrides-publication-exclusion-explicite.md] — reason_codes `publication_excluded_*`, mécanisme de nettoyage au sync pour équipements disparus.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- **create-story** — 2026-09-27 — statut résultant : `ready-for-dev`. Story documentaire créée directement (skill officielle non exposée cette session).

### File List
