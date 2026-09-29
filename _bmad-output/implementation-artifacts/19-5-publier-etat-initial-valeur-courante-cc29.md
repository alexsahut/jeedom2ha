# Story 19.5: Publier l'état initial avec la valeur courante au clic « Publier » (CC-29)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un utilisateur,
I want que le bouton « Publier » publie l'état initial des entités avec leur
valeur Jeedom courante au moment du clic — comme le fait déjà le sync via
`StateSynchronizer.publish_initial_states()` (`resources/daemon/sync/state.py:199`,
appelé après `apply_publication_decision` dans `_do_handle_action_sync`,
`resources/daemon/transport/http_server.py:1868`) — au lieu de laisser l'entité en
`unknown` jusqu'à son premier changement d'état,
so that une entité republiée (ex. après « Suppr. » puis « Republier » sur une
pièce) réapparaît dans Home Assistant avec sa vraie valeur, pas `unknown`.

**Parcours : complet.**

## Acceptance Criteria

**AC1 — Équipement publié pour la première fois par « Publier » : état initial publié**

**Given** un équipement inclus dans le périmètre d'un clic « Publier », dont la
commande info a une valeur Jeedom fraîche (`getCache('value', null)` non nul au
moment du clic)
**When** l'utilisateur clique sur « Publier »
**Then** l'état initial (principal et secondaires concernés) est publié sur le
`state_topic` MQTT après la discovery, avec la valeur retenue au moment du clic
**And** un test explicite vérifie que l'entité est publiée avec la bonne valeur,
pas `unknown`.

**AC2 — Valeur absente au clic : aucun état publié**

**Given** une commande dont `getCache('value', null)` est `null`/absente au moment
du clic « Publier »
**When** l'action s'exécute
**Then** aucun état n'est publié pour cette commande (jamais de valeur inventée ou
par défaut)
**And** un test explicite vérifie l'absence de publication d'état pour ce cas.

**AC3 — Même traduction que le sync**

**Given** une valeur Jeedom brute pour une commande donnée
**When** elle est publiée en état initial par « Publier »
**Then** la traduction appliquée (mapping de valeur → état HA) est strictement la
même fonction que celle utilisée par `publish_initial_states()` au sync — aucune
réimplémentation locale
**And** un test de parité vérifie l'égalité entre les deux chemins pour au moins
un cas numérique et un cas booléen.

**AC4 — Équipement refusé ou hors périmètre : aucun état publié**

**Given** un équipement refusé par `evaluate_equipment()` ou exclu par le filtre
de scope (`_scope_entry_is_included`) lors du clic « Publier »
**When** l'action s'exécute
**Then** aucun état initial n'est publié pour cet équipement (garde identique à
celui du sync)
**And** un test explicite couvre ce cas.

**AC5 — Équipement déjà publié : état republié avec la valeur fraîche**

**Given** un équipement déjà publié dans HA, toujours valide, inclus dans le
périmètre d'un nouveau clic « Publier »
**When** l'action s'exécute
**Then** son état est republié avec la valeur fraîche relevée au clic (pas
seulement les équipements nouvellement publiés)
**And** un test explicite vérifie ce comportement, sans effet de bord sur les
autres candidats (idempotence de la discovery, cohérent avec Story 19.4 AC5).

**AC6 — Le relais PHP est en lecture seule**

**Given** l'action `executeHaAction` du relais PHP (`core/ajax/jeedom2ha.ajax.php:606`)
**When** elle construit le payload `current_values`
**Then** elle se limite à lire `getCache('value', null)` pour les commandes info
des équipements de la sélection — aucune logique de décision, de filtrage ou de
transformation de valeur côté PHP (cohérent avec le commentaire Story 5.1,
« Aucun calcul local »)
**And** un test/relecture de code vérifie l'absence de toute logique métier
ajoutée dans `jeedom2ha.ajax.php`.

**AC7 — Absence de `current_values` : comportement 19-4 inchangé**

**Given** un payload `/action/execute` sans clé `current_values` (rétrocompatibilité
avec un relais PHP non mis à jour, ou tout appelant existant)
**When** l'action « Publier » s'exécute
**Then** le comportement reste strictement celui de la Story 19.4 (pas d'état
initial publié, aucune régression)
**And** le test de garde-fou 19-4 existant continue de passer sans modification
de son fixture.

## UI Impact

- **UI Impact :** Oui — `core/ajax/jeedom2ha.ajax.php` (action `executeHaAction`)
  est modifié pour ajouter `current_values` au payload transmis au démon. Le
  bouton « Publier » ne change pas d'apparence, mais son effet observable change :
  les entités republiées afficheront leur valeur immédiatement au lieu de
  `unknown`. Cette story passe donc par le statut `ready-for-UX-validation` avant
  `done` (cf. `docs/bmad-parcours-rapide-complet.md`), avec une preuve par clic
  réel documentant ce comportement.

## Impact sur la production et retour arrière

Changement de comportement réel et volontaire, approuvé par Alexandre le
2026-09-29 à 23:46 : des entités republiées par « Publier » afficheront désormais
leur valeur Jeedom courante au lieu de rester `unknown` jusqu'au prochain
changement d'état ou sync. Le relais PHP transmet une donnée supplémentaire
(`current_values`) au démon ; le démon ne modifie sa décision de publication en
rien (AC4), il ajoute uniquement un appel à la publication d'état déjà existant
pour le sync. Retour arrière : revert de la story/PR — le payload PHP redevient
strict (Story 5.1), le démon ignore `current_values` s'il n'est pas fourni (AC7),
aucune migration de données, aucun override perdu.

## Preuve terrain

Preuve terrain obligatoire : sur une petite pièce, « Suppr. » puis « Republier »
via l'UI Jeedom — inventaire des entités avant/après (identique en nombre et en
`entity_id`), et vérification que les entités reviennent avec leur valeur
courante (pas `unknown`) dans Home Assistant. 0 erreur pendant l'opération.

**Gate d'inventaire obligatoire (convention repo, `sprint-status.yaml`) :** cette
story modifie un comportement de publication réelle vers Home Assistant — elle ne
peut passer à `done` qu'après le gate obligatoire d'inventaire des entités
avant/après déploiement (0 erreur), en plus de la preuve par clic réel (UI Impact
`Oui`, ci-dessus).

## Invariants concernés

I2, I4, I6, I7 (aucune logique de décision de publication modifiée — uniquement
l'ajout d'un état publié après une décision déjà prise, comme au sync). I11 doit
rester respecté (chaque candidat/secondaire garde sa propre décision et son
propre état initial, cohérent avec Story 19.2 et la publication par candidat déjà
en place pour le sync).

## Points visés

- **CC-29** — fermée par cette story (AC1 à AC7, preuve terrain « Suppr. » puis
  « Republier »).

## Tasks / Subtasks

<!-- Story terrain : daemon / MQTT / publication / bouton Publier / box réelle → Task 0 Pre-flight terrain injectée. -->

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY)
  - [ ] Dry-run standard avant tout déploiement (`./scripts/deploy-to-box.sh`, guardé
    par la CI verte du SHA), inventaire des topics avant/après.
  - [ ] Identifier une petite pièce réelle sans risque pour le cycle
    « Suppr. » → « Republier » (lecture seule le temps de la recherche du cas).
  - [ ] **Interdiction explicite (DANGER) :** ne jamais invoquer
    `--cleanup-discovery` ni `--stop-daemon-cleanup`
    (`scripts/deploy-to-box.sh:95,97`) pendant cette recherche ni pendant la
    vérification post-correction — ces flags republient des messages MQTT
    retained **vides** sur les topics discovery, effaçant les entités déjà
    publiées et rendant impossible de distinguer un effet **causé par cette
    story** d'un effet causé par le script lui-même. Déploiement standard
    uniquement.

- [ ] Task 1 — Relais PHP : lecture des valeurs courantes au clic (AC6, AC7)
  - [ ] Dans `executeHaAction` (`core/ajax/jeedom2ha.ajax.php:606-622`), pour la
    branche « Publier » uniquement, lire `getCache('value', null)` (motif
    identique à `getFullTopology`, `core/class/jeedom2ha.class.php:729`) pour les
    commandes info des équipements de la sélection, et les ajouter au payload
    sous `current_values: {cmd_id: valeur}`.
  - [ ] Ne rien ajouter d'autre : pas de filtrage, pas de traduction, pas de
    décision côté PHP.
  - [ ] Vérifier qu'un payload sans sélection valide ou sans commande info
    produit `current_values` vide ou absent, sans erreur.

- [ ] Task 2 — Démon : publication de l'état initial dans la branche « Publier » (AC1-AC5)
  - [ ] Dans la branche « Publier » (`resources/daemon/transport/http_server.py`,
    autour de la boucle `for eq_id in eq_ids` commençant l.3860), injecter les
    valeurs de `current_values` dans la topologie utilisée par
    `_evaluate_for_action` avant l'évaluation, pour les commandes concernées
    uniquement.
  - [ ] Après la discovery (mêmes points d'appel que `apply_publication_decision`
    dans cette branche), appeler `state_synchronizer.publish_initial_states(decision)`
    avec le même garde que le sync (`state_sync is not None and mqtt_bridge and
    mqtt_bridge.is_connected`, cf. `http_server.py:1866-1868`).
  - [ ] Vérifier qu'un candidat refusé (AC4) ou une commande sans valeur fraîche
    (AC2) ne déclenche aucune publication d'état.
  - [ ] Vérifier l'absence de `current_values` dans le payload : comportement
    19-4 strictement inchangé (AC7), sans branchement conditionnel fragile.

- [ ] Task 3 — Tests (AC1-AC7)
  - [ ] `test_story_19_5_*.py` (préfixe dédié) couvrant AC1, AC2, AC4, AC5, AC7.
  - [ ] Test de parité de traduction (AC3) contre `publish_initial_states()` du
    sync, au moins un cas numérique et un cas booléen.
  - [ ] Relecture ciblée de `jeedom2ha.ajax.php` pour AC6 (absence de logique
    métier), documentée dans les Dev Notes ou un test si un outil de lint le
    permet.
  - [ ] Suite complète `python3 -m pytest -q` et `node --test tests/unit/*.node.test.js` :
    0 régression.

- [ ] Task 4 — Preuve terrain et gate d'inventaire
  - [ ] Cycle réel « Suppr. » puis « Republier » sur une petite pièce, inventaire
    avant/après, valeurs constatées non `unknown` dans HA.
  - [ ] Documenter la preuve par clic réel avant passage
    `ready-for-UX-validation` → `done`.

## Dev Notes

### Contexte pipeline

- Cette story ne touche pas `evaluate_equipment()` ni la logique de décision de
  publication : elle ajoute uniquement un appel de publication d'état déjà
  existant (`publish_initial_states`, Story 12.1) au chemin « Publier », avec les
  mêmes gardes que le sync.
- Le choix initial de ne pas publier d'état pour « Publier » était documenté dans
  la Story 19.4 (« mieux vaut `unknown` explicite qu'une valeur silencieusement
  obsolète ») : cette story lève cette réserve en fournissant une valeur
  fraîchement lue au moment du clic (pas celle, potentiellement périmée, du
  dernier sync), ce qui répond à l'objection initiale.

### Dev Agent Guardrails

- Ne jamais lire la valeur depuis la topologie du dernier sync pour l'état
  initial de « Publier » — uniquement `current_values` transmis au clic.
- Ne jamais ajouter de logique de décision de publication dans cette story :
  `evaluate_equipment()` et le filtre de scope restent les seules sources de la
  décision (AC4).
- Réutiliser strictement `publish_initial_states()` — pas de réimplémentation
  parallèle de la traduction de valeur (AC3).

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh`.
- Référence : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.

### Project Structure Notes

- Fichiers à toucher (probable) :
  `core/ajax/jeedom2ha.ajax.php` [MODIFIÉ — action `executeHaAction`, l.606-622],
  `resources/daemon/transport/http_server.py` [MODIFIÉ — branche « Publier »,
  boucle `for eq_id in eq_ids`, à partir de l.3860],
  `resources/daemon/tests/unit/test_story_19_5_*.py` [NOUVEAU].

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic-19] —
  Story 19.5 ajoutée par correct-course, CC-29.
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-09-29-cc29-publier-etat-initial.md] —
  décision d'Alexandre (29/09, 23:46), impact, approche retenue.
- [Source: resources/daemon/transport/http_server.py#L1868] —
  `publish_initial_states(decision)` appelé après la discovery dans le sync.
- [Source: resources/daemon/sync/state.py#L199] —
  `StateSynchronizer.publish_initial_states`, fonction réutilisée par cette story.
- [Source: resources/daemon/transport/http_server.py#L3837-L3951] —
  branche « Publier » actuelle (Story 19.4), aucun appel à
  `publish_initial_states`.
- [Source: core/class/jeedom2ha.class.php#L729] —
  `current_value => $cmd->getCache('value', null)`, motif de lecture réutilisé
  par le relais PHP.
- [Source: core/ajax/jeedom2ha.ajax.php#L606-L622] —
  `executeHaAction`, relais strict actuel (Story 5.1, « Aucun calcul local »).
- [Source: _bmad-output/implementation-artifacts/19-4-publier-mini-sync-contrat-decision-cc18.md] —
  choix documenté de ne pas publier d'état initial, réserve levée par cette
  story.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- **correct-course + create-story** — 2026-09-29 (23:51) — statut résultant :
  `ready-for-dev`. Story documentaire créée par `clawcode` en session détachée,
  à la demande directe du mainteneur (décision du 29/09 23:46), documentation
  seulement — aucun code touché dans cette session.

### File List

### Change Log

- 2026-09-29 — `correct-course` (CC-29) + `create-story` — statut `ready-for-dev`.
