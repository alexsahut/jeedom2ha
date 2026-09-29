# Story 19.5: Publier l'état initial avec la valeur courante au clic « Publier » (CC-29)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un utilisateur,
I want que le bouton « Publier » publie l'état initial des entités avec leur
valeur Jeedom courante au moment du clic — comme le fait déjà le sync via
`StateSynchronizer.publish_initial_states()` (`resources/daemon/sync/state.py:199`,
appelé après `apply_publication_decision` dans `_do_handle_action_sync`,
`resources/daemon/transport/http_server.py:1868`),
so that une entité publiée ou republiée par un clic affiche dans Home Assistant
sa valeur Jeedom actuelle, au lieu de rester `unknown` ou d'afficher un état
retenu périmé jusqu'à son prochain changement.

**Parcours : complet.**

### Les deux formes réelles de CC-29 (relevées à `5873425`)

Les états sont publiés **retenus** (`retain=True`, `sync/state.py:125` et
`:231`). « Suppr. » n'efface que les topics discovery `.../config`
(`DiscoveryPublisher.unpublish_by_eq_id`, `discovery/publisher.py:305-345`) et
la disponibilité locale, **jamais** les topics d'état. D'où deux cas :

- **(a) Aucun état retenu** — entité jamais streamée : première publication par
  « Publier » (inclusion, override), ou topic d'état nouveau. L'entité reste
  `unknown` jusqu'à son premier changement.
- **(b) État retenu périmé** — après « Suppr. », les évènements de l'équipement
  sont rejetés (`state_target_not_found`, `sync/state.py:111-115`) ; au
  « Republier », HA relit le dernier état retenu, qui est faux si la valeur a
  changé entre-temps. L'entité n'est **pas** `unknown` : elle affiche une valeur
  périmée comme si elle était actuelle.

### Portée

Seuls les types streamés reçoivent un état : `sensor`, `binary_sensor`, `switch`
(`_STREAMED_TYPES`, `sync/state.py:31-35`). Les lumières et volets (chemin
optimiste) et les boutons (sans état dans HA) sont **hors périmètre** et restent
tels quels.

## Acceptance Criteria

**AC1 — État initial publié au clic, principal et secondaires**

**Given** un équipement inclus dans le périmètre d'un clic « Publier », dont un
candidat streamé (principal ou secondaire) a une valeur Jeedom au clic
(`getCache('value', null)` non nul)
**When** l'utilisateur clique sur « Publier »
**Then** l'état initial de ce candidat est publié, retenu, sur son `state_topic`,
**après** sa discovery, avec la valeur relevée au clic
**And** un test couvre un principal et un secondaire (y compris un secondaire
publié sous un principal refusé, I11).

**AC2 — Jamais la valeur du dernier sync**

**Given** une commande absente de `current_values` (ou à `null`), alors que la
topologie du dernier sync porte pour elle une `current_value` non nulle
**When** « Publier » s'exécute
**Then** aucun état n'est publié pour cette commande
**And** un test fige ce cas précis (la valeur du sync ne doit jamais fuir).

**AC3 — Même traduction que le sync**

**Given** une valeur Jeedom brute
**When** elle est publiée en état initial par « Publier »
**Then** elle passe par la même fonction de traduction que le sync
(`StateSynchronizer._translate_value`, aucune réimplémentation)
**And** un test de parité compare les deux chemins sur un cas numérique
(`sensor`) et un cas binaire (`binary_sensor` ou `switch`).

**AC4 — Refusé ou hors périmètre : aucun état**

**Given** un candidat refusé par la décision, ou un équipement exclu par le
filtre de scope (`_scope_entry_is_included`)
**When** « Publier » s'exécute
**Then** aucun état initial n'est publié pour lui (garde par candidat identique
au sync : `discovery_published` de sa propre décision)
**And** un test couvre les deux cas.

**AC5 — Équipement déjà publié : état republié avec la valeur du clic**

**Given** un équipement déjà publié, toujours accepté, inclus dans le clic
**When** « Publier » s'exécute
**Then** son état est republié avec la valeur du clic
**And** la discovery reste idempotente (Story 19.4 AC5), sans effet sur les
autres candidats.

**AC6 — Relais PHP en lecture seule, testé**

**Given** l'action `executeHaAction` (`core/ajax/jeedom2ha.ajax.php:606-622`)
**When** elle construit `current_values`
**Then** elle ne fait que lire `getCache('value', null)` sur les commandes de
type info des équipements visés — jamais `execCmd()`, aucune décision, aucun
filtrage métier, aucune traduction
**And** la lecture est une fonction pure testée en CI
(`JEEDOM2HA_AJAX_FUNCTIONS_ONLY`, motif de `tests/unit/test_story_5_1_php_relay.php`)
avec des objets factices : valeurs `null` omises, commandes action ignorées,
aucun appel à `execCmd`.

**AC7 — Sans `current_values` : comportement 19-4 inchangé**

**Given** un payload `/action/execute` sans `current_values`, ou avec `[]`
(`json_encode` d'un tableau PHP vide)
**When** « Publier » s'exécute
**Then** aucun état initial n'est publié, comme en 19-4
**And** les tests 19-4 existants passent sans modification de leurs fixtures.

**AC8 — Un évènement reçu pendant le clic l'emporte sur la valeur du clic**

**Given** « Publier » dort `max(0.1, 10/n)` s par équipement
(`http_server.py:3863`, `:3925`) : la valeur lue au clic peut être publiée
plusieurs secondes plus tard
**When** un évènement Jeedom pour la même commande arrive au démon après le
début de la requête « Publier » (qu'il ait été publié ou rejeté
`state_target_not_found` parce que l'entité n'était pas encore publiée)
**Then** l'état initial publie la valeur de cet évènement, jamais la valeur plus
ancienne du clic
**And** un test couvre les deux sous-cas (évènement publié, évènement rejeté).
La fenêtre résiduelle entre la lecture PHP et la réception de la requête par le
démon (quelques millisecondes) est déclarée, non traitée.

**AC9 — Le sync ne change pas**

**Given** l'appel existant du sync (`http_server.py:1868`)
**When** la story est livrée
**Then** `publish_initial_states(decision)` sans argument nouveau garde
exactement son comportement actuel
**And** les tests Story 12.1 / 19.2 existants passent sans modification.

## UI Impact

- **UI Impact :** Oui — `core/ajax/jeedom2ha.ajax.php` (action `executeHaAction`)
  est modifié. Le bouton ne change pas d'apparence, mais son effet observable
  change : après un clic, les entités streamées affichent leur valeur Jeedom
  actuelle. Passage par `ready-for-UX-validation` avant `done`
  (`docs/bmad-parcours-rapide-complet.md`), avec preuve par clic réel.

## Impact sur la production et retour arrière

- **Changement de comportement volontaire**, approuvé par Alexandre le
  2026-09-29 à 23:46 : « Publier » publie désormais des états retenus.
- **La décision de publication ne change pas** (AC4) : seul un état est ajouté
  après une décision déjà prise, comme au sync.
- **Risque principal : un état faux retenu.** Couvert par AC2 (jamais la valeur
  du sync) et AC8 (un évènement plus récent l'emporte). Un état faux se corrige
  au changement suivant ou au sync suivant.
- **Durée** : la lecture PHP s'ajoute avant l'appel au démon. Le « Republier »
  global dépasse déjà probablement le délai de lecture de 15 s du relais
  (`http_server.py:3863` × 266 inclus ≈ 27 s ; `jeedom2ha.ajax.php:617`,
  CC-32, préexistant depuis 5.2) : cette story ne doit pas l'aggraver côté démon,
  et la preuve ne passe pas par le global.
- **Retour arrière** : redéploiement du SHA précédent. Sans `current_values`, le
  démon se comporte comme en 19-4 (AC7). Aucune migration, aucun override touché.
  Les états retenus publiés restent sur le broker ; ils sont remplacés au
  changement suivant.

## Preuve terrain

La preuve doit **discriminer** : « Suppr. » puis « Republier » ne suffit pas,
puisque sans 19-5 HA relit déjà l'état retenu (forme (b)).

1. Choisir une petite pièce avec au moins un `sensor` dont la valeur change
   souvent (puissance, température), sans automatisation HA (HA n'en a aucune
   aujourd'hui).
2. Inventaire avant (registre HA, `core.restore_state`, topics).
3. « Suppr. » sur la pièce ; attendre que la valeur Jeedom du capteur change.
4. « Republier » sur la pièce.
5. Critères :
   - journal du démon : une ligne `initial_state_published` par candidat streamé
     de la pièce, datée du clic (« Publier » n'en émet jamais avant 19-5) ;
   - HA : l'entité affiche la **nouvelle** valeur Jeedom, pas l'état retenu
     d'avant « Suppr. » ;
   - types non streamés de la pièce : inchangés ;
   - inventaire après identique en nombre et en `entity_id` ; 0 ERROR.

**Gate d'inventaire obligatoire (convention repo, `sprint-status.yaml`)** :
inventaire avant/après déploiement (0 erreur), en plus de la preuve par clic
réel.

## Invariants concernés

I2, I4, I6, I7 (aucune logique de décision modifiée). I11 : chaque candidat
garde sa propre décision et son propre état initial (Story 19.2).

## Points visés

- **CC-29** — fermé par cette story (AC1 à AC9 et preuve terrain).
- **CC-32** (hors périmètre, préexistant) : délai du « Republier » global,
  suivi à part.

## Tasks / Subtasks

<!-- Story terrain : daemon / MQTT / publication / bouton Publier / box réelle → Task 0 Pre-flight terrain injectée. -->

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY)
  - [ ] Dry-run : `./scripts/deploy-to-box.sh --dry-run` (CI verte du SHA exigée).
  - [ ] Identifier en lecture seule une petite pièce conforme à la preuve
    terrain (capteur à valeur changeante, types streamés).
  - [ ] **Interdiction explicite (DANGER) :** ne jamais invoquer
    `--cleanup-discovery` ni `--stop-daemon-cleanup`
    (`scripts/deploy-to-box.sh:97,99`) pendant cette recherche ni pendant la
    vérification post-correction — ces flags republient des messages MQTT
    retained **vides** sur les topics discovery, effaçant les entités déjà
    publiées et rendant impossible de distinguer un effet **causé par cette
    story** d'un effet causé par le script lui-même. Déploiement standard
    uniquement.

- [ ] Task 1 — Relais PHP : lecture des valeurs au clic (AC6, AC7)
  - [ ] Fonction pure (chargeable sous `JEEDOM2HA_AJAX_FUNCTIONS_ONLY`) qui prend
    des équipements et rend `{cmd_id: valeur}` pour leurs commandes info, via
    `getCache('value', null)` (motif de `getFullTopology`,
    `core/class/jeedom2ha.class.php:729`), en omettant les `null`.
  - [ ] Dans `executeHaAction`, pour `intention = publier` seulement : résoudre
    les équipements visés (équipement : les ids ; pièce : `eqLogic::byObjectId` ;
    global : tous) et ajouter `current_values` au payload. Aucune décision :
    le démon ignore ce qui ne le concerne pas.
  - [ ] Test PHP en CI (objets factices), ajouté à `.github/workflows/test.yml`
    s'il n'est pas pris par le motif existant.

- [ ] Task 2 — Démon (AC1-AC5, AC7-AC9)
  - [ ] `publish_initial_states(decision, fresh_values=None, fresh_since=None)` :
    `fresh_values is None` ⇒ comportement actuel inchangé (AC9). Sinon, pour
    chaque candidat : valeur d'un évènement reçu après `fresh_since` (AC8), sinon
    `fresh_values[cmd_id]` (clé via `_coerce_cmd_id`), sinon **aucun état**
    (AC2). Ne jamais muter `app["topology"]`.
  - [ ] `handle_state_message` (`sync/state.py:90`) retient, pour chaque
    (eq, cmd) reçu, la valeur et l'instant monotone, **avant** la résolution de
    la cible (les évènements rejetés comptent, AC8).
  - [ ] `_handle_action_execute` : relever `fresh_since = time.monotonic()` à
    l'entrée ; normaliser `current_values` (dict, clés coercées en int ; `[]`,
    absent ou invalide ⇒ `None`, AC7).
  - [ ] Branche « Publier » (boucle `http_server.py:3865`) : appeler
    `publish_initial_states(decision, fresh_values, fresh_since)` juste après
    `apply_publication_decision` (l.3895) et **avant** le `sleep` (l.3925), avec
    le garde du sync (`state_sync is not None and mqtt_bridge.is_connected`,
    l.1866-1868), seulement si `fresh_values is not None`.

- [ ] Task 3 — Tests (AC1-AC9)
  - [ ] `resources/daemon/tests/unit/test_story_19_5_etat_initial_publier.py` :
    AC1 (principal, secondaire, secondaire sous principal refusé), AC2 (valeur
    du sync présente mais non fournie ⇒ rien), AC3 (parité), AC4, AC5, AC7
    (absent et `[]`), AC8 (évènement publié, évènement rejeté), AC9.
  - [ ] Test PHP de la fonction de lecture (AC6).
  - [ ] Suite complète `python3 -m pytest -q` et `node --test tests/unit/*.node.test.js` :
    0 régression ; garde-fou 19-4 inchangé (écarts déclarés s'il y en a).

- [ ] Task 4 — Preuve terrain et gate d'inventaire
  - [ ] Dérouler la section « Preuve terrain » ; documenter la preuve par clic
    réel avant `ready-for-UX-validation` → `done`.

## Dev Notes

### Contexte pipeline

- Cette story ne touche ni `evaluate_equipment()` ni la décision de
  publication : elle ajoute un état après une décision déjà prise, comme le sync.
- La Story 19.4 avait choisi de ne pas publier d'état au clic (« mieux vaut
  `unknown` explicite qu'une valeur silencieusement obsolète ») : la topologie du
  dernier sync n'est jamais rafraîchie par le flux d'évènements. Cette story lève
  la réserve avec une valeur lue au clic (AC2) et la priorité aux évènements
  plus récents (AC8).

### Dev Agent Guardrails

- Ne jamais lire la valeur de l'état initial de « Publier » dans la topologie du
  dernier sync ; ne jamais muter `app["topology"]`.
- Aucune logique de décision de publication dans cette story (AC4).
- Réutiliser `publish_initial_states()` et `_translate_value` : aucune
  réimplémentation (AC3).
- PHP : `getCache('value', null)` seulement, jamais `execCmd()`.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh`.
- Référence : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.

### Pointeurs (relevés à `5873425`)

- `resources/daemon/sync/state.py` : `_STREAMED_TYPES` l.31-35 ;
  `handle_state_message` l.90 (rejet `state_target_not_found` l.111-115,
  publication retenue l.125) ; `publish_initial_states` l.199 (publication
  retenue l.231) ; `_candidate_current_value` l.240.
- `resources/daemon/transport/http_server.py` : appel du sync l.1866-1868 ;
  branche supprimer à partir de l.3701 ; branche « Publier » l.3838-4016
  (délai l.3863, boucle l.3865, `apply_publication_decision` l.3895, `sleep`
  l.3925) ; `_handle_action_state_update` l.4078 (appel l.4113).
- `resources/daemon/discovery/publisher.py` : `unpublish_by_eq_id` l.305-345
  (topics `.../config` seulement).
- `core/ajax/jeedom2ha.ajax.php` : `executeHaAction` l.606-622, `callDaemon`
  avec délai 15 s l.617.
- `core/class/jeedom2ha.class.php` : `'current_value' => $cmd->getCache('value', null)` l.729.
- `tests/unit/test_story_5_1_php_relay.php` : motif de test PHP sous
  `JEEDOM2HA_AJAX_FUNCTIONS_ONLY`.

### Project Structure Notes

- `core/ajax/jeedom2ha.ajax.php` [MODIFIÉ], `resources/daemon/sync/state.py`
  [MODIFIÉ], `resources/daemon/transport/http_server.py` [MODIFIÉ],
  `resources/daemon/tests/unit/test_story_19_5_etat_initial_publier.py`
  [NOUVEAU], test PHP [NOUVEAU].

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic-19] —
  Story 19.5 ajoutée par correct-course, CC-29.
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-09-29-cc29-publier-etat-initial.md] —
  décision d'Alexandre (29/09, 23:46), impact, approche retenue.
- [Source: _bmad-output/implementation-artifacts/19-4-publier-mini-sync-contrat-decision-cc18.md] —
  choix documenté de ne pas publier d'état initial, réserve levée ici.

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

- **correct-course + create-story** — 2026-09-29 (23:51) — statut résultant :
  `ready-for-dev`. Créée par `clawcode` en session détachée, documentation
  seulement.
- **Relecture ClaudeBox** — 2026-09-30 : preuve terrain rendue discriminante
  (états retenus, formes (a) et (b)) ; conception « injecter dans la
  topologie » remplacée par `fresh_values` (AC2) ; course avec les évènements
  (AC8) ; sync inchangé (AC9) ; portée limitée aux types streamés ; test PHP
  (AC6) ; pointeurs corrigés (`deploy-to-box.sh:97,99`).

### File List

### Change Log

- 2026-09-29 — `correct-course` (CC-29) + `create-story` — statut `ready-for-dev`.
- 2026-09-30 — relecture ClaudeBox (AC2 renforcé, AC8 et AC9 ajoutés, preuve terrain discriminante).
