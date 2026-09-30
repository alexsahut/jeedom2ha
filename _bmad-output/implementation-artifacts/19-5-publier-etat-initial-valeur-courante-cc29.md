# Story 19.5: Publier l'état initial avec la valeur courante au clic « Publier » (CC-29)

Status: ready-for-UX-validation

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
aucun appel à `execCmd`
**And** la portée est développée en équipements **avant** la lecture : l'UI
envoie des ids d'équipements (`equipement`), `[pieceId]` (`piece`) ou `['all']`
(`global`) (`desktop/js/jeedom2ha.js:544`, `:589`, `:637`), avec un test par portée
(Codex P1, revue du 29/09). Résiduel déclaré (Codex P2, revue du 30/09) :
l'expansion `piece` suit l'état Jeedom courant, alors que le démon développe la
même pièce depuis la topologie du dernier sync (`_resolve_eq_ids_for_portee`,
`http_server.py:386-397`). Un équipement changé de pièce depuis le dernier sync
n'a donc pas de valeur au clic : il ne reçoit **aucun** état (AC2, pas d'erreur,
un journal DEBUG `initial_state_no_click_value`), jusqu'au sync suivant qui
réaligne les deux côtés. Un test démon fige ce cas.

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
démon (quelques millisecondes) est déclarée, non traitée. La garantie ne vaut
que pour une commande **déjà écoutée** au moment du clic (listener Jeedom
enregistré) : une commande publiée pour la première fois n'a pas d'écouteur
avant AC11, donc aucun évènement pendant le clic (résiduel déclaré, forme (a)
seulement).

**AC9 — Le sync ne change pas**

**Given** l'appel existant du sync (`http_server.py:1868`)
**When** la story est livrée
**Then** `publish_initial_states(decision)` sans argument nouveau garde
exactement son comportement actuel (valeurs de la topologie, retour = nombre
publié)
**And** les tests Story 12.1 / 19.2 existants passent sans modification.

**AC10 — Un état initial non publié compte comme une erreur du clic**

**Given** une discovery réussie mais une publication MQTT d'état initial en
échec (`publish_message` rend `False`, pont annoncé connecté)
**When** « Publier » s'exécute
**Then** l'équipement est compté dans `publish_errors`, comme un secondaire en
échec (`secondary_failed`, `http_server.py:3930-3945`), le résultat du clic
devient `succes_partiel` ou `echec`, et un journal WARNING
`initial_state_publish_failed` nomme l'équipement et la commande
**And** un test fige ce cas (Codex P2, revue du 30/09). Une commande sans valeur
(AC2) n'est **pas** un échec.

**AC11 — Écouteurs réalignés après « Publier »**

**Given** un candidat publié pour la première fois par le clic : aucun listener
Jeedom ne relaie ses changements, car `jeedom2ha::syncStateListeners()`
(`core/class/jeedom2ha.class.php:407-451`) n'est appelé qu'après un sync
(`core/ajax/jeedom2ha.ajax.php:437-442`) ou au démarrage (class l.377-382)
**When** `executeHaAction` reçoit une réponse du démon pour `intention = publier`
**Then** le relais appelle `jeedom2ha::syncStateListeners()`, dans un
`try/catch` qui journalise un WARNING comme après un sync, sans changer la
réponse renvoyée à l'UI ; les changements suivants du candidat sont relayés
**And** `syncStateListeners()` récupère et valide les cibles
(`GET /system/state_listeners`) **avant** de supprimer les listeners existants.
Aujourd'hui il les supprime d'abord (`core/class/jeedom2ha.class.php:408-417`) :
un GET en échec couperait toute remontée d'état du plugin jusqu'au réalignement
suivant. En cas d'échec (exception, réponse invalide), les listeners existants
sont **conservés** et un WARNING est journalisé. Une liste valide mais vide
supprime tout, comme aujourd'hui. Le sync et le démarrage en bénéficient aussi
(Codex P1, revue du 30/09)
**And** des tests PHP sans cœur Jeedom vérifient l'appel pour `publier`, son
absence pour `supprimer` et quand le démon ne répond pas, ainsi que l'ordre
« récupérer, valider, puis purger » et la conservation sur échec (Codex P1,
revue du 30/09)
**And** le réalignement a un budget court après « Publier » : GET
`/system/state_listeners` avec un délai de 3 s et **une seule** tentative
(`callDaemon` en fait aujourd'hui deux de 15 s pour un GET, class l.544-559 ;
paramètre optionnel, défaut inchangé), pour rester sous le délai client de
20 s (`desktop/js/jeedom2ha.js:343`). Un test couvre `/system/state_listeners`
indisponible après une action réussie : réponse inchangée, listeners conservés
(Codex P2, revue du 30/09). Si le relais abandonne sur délai (CC-32), les écouteurs ne sont
pas réalignés avant le sync suivant : déclaré.

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
- **Écouteurs** (AC11) : chaque « Publier » recrée les listeners d'état du
  plugin, comme chaque sync aujourd'hui, mais seulement après avoir obtenu les
  nouvelles cibles ; sur échec, l'ensemble précédent est gardé. Un évènement
  survenu pendant les quelques millisecondes de la recréation est perdu jusqu'au
  changement suivant (même risque que le sync, déclaré). Aucun listener d'un
  autre plugin n'est touché (`listener::byClass('jeedom2ha')`).

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

- **CC-29** — fermé par cette story (AC1 à AC11 et preuve terrain).
- **CC-32** (hors périmètre, préexistant) : délai du « Republier » global,
  suivi à part.

## Tasks / Subtasks

<!-- Story terrain : daemon / MQTT / publication / bouton Publier / box réelle → Task 0 Pre-flight terrain injectée. -->

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY)
  - [x] Dry-run : `./scripts/deploy-to-box.sh --dry-run` (CI verte du SHA exigée).
    **Écart** : pas de dry-run séparé. La garde CI du script a vérifié le SHA
    exact au déploiement réel, en plus de la vérification ClaudeBox.
  - [x] Identifier en lecture seule une petite pièce conforme à la preuve
    terrain (capteur à valeur changeante, types streamés) : « escalier »
    (objet 9), capteur 4238 de l'eq 468.
  - [x] **Interdiction explicite (DANGER) :** ne jamais invoquer
    `--cleanup-discovery` ni `--stop-daemon-cleanup`
    (`scripts/deploy-to-box.sh:97,99`) pendant cette recherche ni pendant la
    vérification post-correction — ces flags republient des messages MQTT
    retained **vides** sur les topics discovery, effaçant les entités déjà
    publiées et rendant impossible de distinguer un effet **causé par cette
    story** d'un effet causé par le script lui-même. Déploiement standard
    uniquement.

- [x] Task 1 — Relais PHP : lecture des valeurs au clic et écouteurs (AC6, AC7, AC11)
  - [x] Fonction pure (chargeable sous `JEEDOM2HA_AJAX_FUNCTIONS_ONLY`) qui prend
    des équipements et rend `{cmd_id: valeur}` pour leurs commandes info, via
    `getCache('value', null)` (motif de `getFullTopology`,
    `core/class/jeedom2ha.class.php:729`), en omettant les `null`.
  - [x] Dans `executeHaAction`, pour `intention = publier` seulement : développer
    la portée en équipements **avant** la lecture (équipement : les ids reçus ;
    pièce : `eqLogic::byObjectId(pieceId)` ; global : tous les
    équipements), puis ajouter `current_values` au payload. Aucune décision :
    le démon ignore ce qui ne le concerne pas.
  - [x] Après la réponse du démon, pour `publier` seulement : appeler
    `jeedom2ha::syncStateListeners()` dans un `try/catch` (WARNING), comme
    `scanTopology` (ajax l.437-442).
  - [x] `syncStateListeners()` : ordre inversé récupérer → valider → purger →
    créer ; sur échec, rien n'est supprimé (AC11). Fetcher injectable
    (`$_targetsFetcher`) pour le test. **Écart** : la purge/création reste liée
    directement à la classe `listener` (pas d'injection séparée liste/supprime/
    crée) — non testable unitairement en PHP pur ; seule la logique
    récupérer→valider→décision-de-purge (fetcher injecté) est couverte côté
    daemon/PHP pur. Voir Completion Notes.
  - [x] Test PHP en CI (objets factices), un cas par portée (`equipement`,
    `piece`, `global`), plus le résiduel AC6 ; découvert par le motif existant
    (`find tests -name '*.php'`).

- [x] Task 2 — Démon (AC1-AC5, AC7-AC10)
  - [x] Extraire la boucle de `publish_initial_states` dans une méthode privée
    paramétrée par la source de valeur, qui compte publiés **et** échecs.
    `publish_initial_states(decision)` garde sa signature et son retour (nombre
    publié, AC9). Nouvelle méthode pour le clic,
    `publish_click_states(decision, fresh_values, fresh_since)` qui rend
    `(publiés, échecs)` : pour chaque candidat, valeur d'un évènement reçu après
    `fresh_since` (AC8), sinon `fresh_values[cmd_id]`, sinon **aucun état** (AC2).
    `app["topology"]` jamais muté.
  - [x] Échec de publication d'état : journal WARNING
    `initial_state_publish_failed` (eq, cmd, topic) et comptage (AC10).
  - [x] `handle_state_message` (`sync/state.py:90`) retient, pour chaque
    (eq, cmd) reçu, la valeur et l'instant monotone, **avant** la résolution de
    la cible (les évènements rejetés comptent, AC8).
  - [x] `_handle_action_execute` : relève `fresh_since = time.monotonic()` à
    l'entrée ; normalise `current_values` (dict, clés coercées en int ; `[]`,
    absent ou invalide ⇒ `None`, AC7).
  - [x] Branche « Publier » : appelle la méthode du clic juste après la
    décision et **avant** le `sleep`, avec le garde du sync (`state_sync is not
    None and mqtt_bridge.is_connected`), seulement si `fresh_values is not
    None`. Un échec d'état fait compter l'équipement dans `secondary_failed`
    (AC10).

- [x] Task 3 — Tests (AC1-AC11)
  - [x] `resources/daemon/tests/unit/test_story_19_5_etat_initial_publier.py` :
    20 tests, AC1 (principal, secondaire, secondaire sous principal refusé), AC2,
    AC3 (parité), AC4, AC5, AC7 (absent et `[]`), AC8 (évènement publié,
    évènement rejeté), AC9, AC10 (publication d'état en échec, WARNING), et le
    résiduel d'AC6.
  - [x] Test PHP (`tests/unit/test_story_19_5_php_relay.php`) de la fonction de
    lecture et de l'expansion des 3 portées (AC6) et du résiduel AC6. **Non
    fait** : test PHP dédié à l'ordre récupérer→valider→purger et à la
    conservation sur échec d'AC11 (nécessiterait un core Jeedom réel ou une
    extraction supplémentaire non réalisée dans ce tour — voir écart Task 1).
  - [x] Suite complète `python3 -m pytest -q` (1385 passed) et
    `node --test tests/unit/*.node.test.js` (305 passed) : 0 régression.

- [x] Task 4 — Preuve terrain et gate d'inventaire
  - [x] Dérouler la section « Preuve terrain » ; documenter la preuve par clic
    réel avant `ready-for-UX-validation` → `done` :
    `19-5-field-proof-2026-09-30.md`.

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
  avec délai 15 s l.617 ; `scanTopology` puis `syncStateListeners` l.430-444.
- `core/class/jeedom2ha.class.php` : `syncStateListeners` l.407-451 (cibles
  `GET /system/state_listeners`, `http_server.py:3472` →
  `StateSynchronizer.list_state_targets`, `sync/state.py:137`).
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

- `clawcode` — Claude (session détachée, worktree `feat-19-5`, base `b8a8863`).

### Debug Log References

- `/tmp/jeedom2ha-19-5-dev-report.md` (rapport de session détaché).

### Completion Notes List

- **Dev (30/09)** — Task 1-3 implémentées. Suite complète : `python3 -m pytest -q`
  1385 passed ; `node --test` 305 passed ; PHP (4 fichiers CI non skip-listés)
  0 échec. `git diff --stat` limité aux 4 fichiers de production attendus +
  2 nouveaux fichiers de test.
- **Écart documenté** : `syncStateListeners()` réordonné fetch→validate→purge→
  create (AC11) mais la purge/création reste directement liée à la classe
  `listener` du cœur Jeedom (pas d'injection séparée liste/supprime/crée comme
  suggéré par Task 1). Conséquence : le test PHP couvre la lecture pure et
  l'expansion de portée, pas l'ordre fetch→purge lui-même (non testable hors
  core Jeedom dans ce tour). Comportement conservé sur échec (fetch/validation
  KO ⇒ listeners existants gardés) est implémenté mais non couvert par un test
  automatisé faute d'extraction complète.
- **Écart de process (Step 2)** : la suite complète n'a pas été capturée avant
  tout changement de code (les 126 tests ciblés ont servi de garde-fou pendant
  le développement) ; la suite complète a été relancée après coup et montre
  0 régression (voir rapport de session).
- Task 0 et Task 4 (terrain) explicitement hors périmètre de ce tour.
- **Relecture de code ClaudeBox (30/09, sur `549d0e7`)** — corrections écrites par
  ClaudeBox :
  - AC11 : l'écart ci-dessus est levé. La logique est extraite dans
    `core/php/jeedom2ha_state_listeners.php` (fonctions pures, sans cœur Jeedom) :
    récupérer → valider **toutes** les cibles (tout-ou-rien, Codex P2 PR #184) →
    créer → purger (Codex P2 PR #185 : les nouveaux listeners sont créés avant de
    supprimer les anciens, donc une exception en cours de route ne laisse aucune
    commande sans écouteur ; écart assumé à l'ordre littéral de la Task 1), rien
    n'est touché sur échec de récupération ou de validation. `syncStateListeners()` garde son
    budget par défaut (15 s) pour le sync et le démarrage ; seul « Publier » passe
    3 s et une tentative (`jeedom2ha_realign_after_action`). 27 cas PHP ajoutés
    (ordre, conservation sur exception, réponse invalide ou cible mal formée, liste
    vide, création ou purge en échec, budget, `supprimer`, démon muet,
    indisponibilité sans exception).
  - AC8 : `fresh_since` relevé avant le premier `await` du handler (Codex P2, PR #184).
  - Résiduel AC6 : journal DEBUG `initial_state_no_click_value` ajouté et testé.
  - AC10 : test de câblage jusqu'au résultat du clic (échec d'état ⇒ `echec`, témoin
    ⇒ `succes`), vérifié par mutation.
  - Décompte : la suite Python complète se lance depuis la racine du dépôt (comme la
    CI), pas depuis `resources/daemon` ; les « 1385 passed » ci-dessus ne couvrent
    qu'une partie de la suite.
- **Code-review ClaudeBox (30/09, sur `bad53c2`, Codex « no major issues »)** — un
  point corrigé : la lecture des valeurs au clic pouvait faire échouer « Publier »
  entier (exception du cœur ou du cache), alors qu'elle n'est qu'un complément. Elle
  passe par `_jeedom2ha_collect_click_values` (best-effort, testée) : en cas
  d'échec, avertissement et publication **sans** `current_values`, donc comportement
  19-4 (AC7). +6 cas PHP (39/39).

- **correct-course + create-story** — 2026-09-29 (23:51) — statut résultant :
  `ready-for-dev`. Créée par `clawcode` en session détachée, documentation
  seulement.
- **Relecture ClaudeBox** — 2026-09-30 : preuve terrain rendue discriminante
  (états retenus, formes (a) et (b)) ; conception « injecter dans la
  topologie » remplacée par `fresh_values` (AC2) ; course avec les évènements
  (AC8) ; sync inchangé (AC9) ; portée limitée aux types streamés ; test PHP
  (AC6) ; pointeurs corrigés (`deploy-to-box.sh:97,99`).
- **Revue Codex** — 29/09 (`92c6888`) : P1 expansion de la portée avant la
  lecture PHP (intégrée à AC6 et Task 1) ; P1 valeurs de l'ancienne topologie
  (déjà traité par `fresh_values`, AC2/AC7). 30/09 (`415d609`) : P2 échec de
  l'état initial non propagé ⇒ AC10. 30/09 (`4feceb2`) : P1 écouteurs non
  réalignés après une première publication ⇒ AC11, et garantie d'AC8 restreinte
  aux commandes déjà écoutées. 30/09 (`a3c1e4b`) : P1 purge des listeners avant
  la récupération des cibles ⇒ ordre inversé et conservation sur échec (AC11) ;
  P2 expansion `piece` depuis l'état courant contre la topologie du démon ⇒
  résiduel déclaré et testé (AC6). 30/09 (`a733d09`) : P2 réalignement
  bloquant jusqu'à ~31 s contre 20 s côté client ⇒ budget de 3 s, une tentative
  (AC11).

- **Preuve terrain (30/09, ClaudeBox et `clawcode`, règle 2)** — `ed9cc30`
  déployé à 06:40:40Z (déploiement standard, `clawcode`). Parité identique, à un
  écart près, expliqué et sans lien avec 19-5 : le bouton du scénario 2 est
  republié, car le scénario est actif ce matin. Écouteurs : 227 avant et après.
  0 ERROR. Preuve par clic sur « escalier » (ClaudeBox, dans Chrome) :
  « Suppr. », changement de la valeur Jeedom (évènement rejeté par le démon),
  puis « Republier ». Le démon émet `initial_state_published` pour les 3 capteurs
  au clic. HA affiche la valeur Jeedom lue au clic, et non l'état retenu d'avant
  « Suppr. ». Mêmes `entity_id`. Artefact : `19-5-field-proof-2026-09-30.md`.

### File List

- `resources/daemon/sync/state.py` [MODIFIÉ]
- `resources/daemon/transport/http_server.py` [MODIFIÉ]
- `core/ajax/jeedom2ha.ajax.php` [MODIFIÉ]
- `core/class/jeedom2ha.class.php` [MODIFIÉ]
- `resources/daemon/tests/unit/test_story_19_5_etat_initial_publier.py` [NOUVEAU]
- `tests/unit/test_story_19_5_php_relay.php` [NOUVEAU]
- `core/php/jeedom2ha_state_listeners.php` [NOUVEAU — relecture ClaudeBox]

### Change Log

- 2026-09-29 — `correct-course` (CC-29) + `create-story` — statut `ready-for-dev`.
- 2026-09-30 — relecture ClaudeBox (AC2 renforcé, AC8 et AC9 ajoutés, preuve terrain discriminante).
- 2026-09-30 — revue Codex intégrée (AC6 : expansion de la portée testée ; AC10 : échec d'état compté).
- 2026-09-30 — revue Codex (`4feceb2`) intégrée (AC11 : écouteurs réalignés après « Publier »).
- 2026-09-30 — revue Codex (`a3c1e4b`) intégrée (AC11 : cibles récupérées avant la purge ; AC6 : résiduel pièce déclaré).
- 2026-09-30 — revue Codex (`a733d09`) intégrée (AC11 : budget de 3 s pour le réalignement).
- 2026-09-30 — dev-story (`clawcode`, `549d0e7`), statut `review`.
- 2026-09-30 — relecture de code ClaudeBox : AC11 extrait et testé, `fresh_since` avant le premier `await`, DEBUG du résiduel AC6, câblage AC10 testé.
- 2026-09-30 — revue Codex PR #185 : listeners créés avant la purge (aucune commande sans écouteur en cas d'exception).
- 2026-09-30 — code-review ClaudeBox : lecture des valeurs au clic en best-effort (AC7 sur échec).
- 2026-09-30 — PR #185 fusionnée (`ed9cc30`), déployée et prouvée sur le terrain ; statut `ready-for-UX-validation`.
