# Story 12.6 : Recaler les listeners d'état par différence (correctif « Listener non trouvé », CC-45)

Status: review

> Story de correction créée le 2026-11-23 par une session cloud déléguée (workflow `bmad-create-story`, non interactif), à partir d'un diagnostic de production fait en lecture seule par une autre session le 23/11. Base : `origin/main` `85bab95` (PR #420). Dépôt en gel : on ne corrige que ce défaut. Aucun accès à la box ni à Home Assistant ; identifiants d'exemple seulement, aucun nom réel, aucune IP.

## Story

En tant que porteur du projet qui lit le centre de messages Jeedom,
je veux qu'une resynchronisation de jeedom2ha ne supprime et ne recrée plus tous les listeners d'état,
afin de ne plus voir des dizaines de « Listener non trouvé » par jour et de ne plus perdre de mise à jour d'état vers HA pendant une resynchronisation.

**Parcours : PHP seul.** Aucun changement du démon, de la discovery, du JS ou de la configuration.

## Contexte

Rattachement : **pe-epic-12** (restitution d'état runtime), suite de la story 12.1 (`12-1-streaming-valeur-sensor-binary-sensor-vague-1.md`), qui a créé les listeners `stateListener`, et de la story 19.5 (AC11), qui a fixé l'ordre « récupérer → valider → créer → purger ». Défaut déjà relevé sous le nom **CC-45** dans `20-2-preuve-complement-2026-10-06.md` (cinq « Listener non trouvé » dans la seconde d'un réalignement).

### Diagnostic de production (lecture seule, 23/11, 21:10)

- Le centre de messages reçoit des dizaines d'entrées par jour, type « plugin », texte `Listener non trouvé : <id>` ; `log/listener_execution` en contient depuis l'identifiant 42085 (dès 12.1, pas une régression récente).
- L'erreur vient du cœur (`core/php/jeeListener.php`) : un listener lancé en tâche de fond est relu par son identifiant ; s'il a été supprimé entre-temps, une exception est journalisée sous le plugin.
- `jeedom2ha::syncStateListeners()` supprime **tous** les listeners `stateListener` et recrée les 291 à chaque resynchronisation ; une commande qui change pendant ce moment lance `jeeListener.php` sur un identifiant déjà supprimé.
- Preuves : erreurs aux tics du cron des 5 minutes (xx:x0:10, xx:x5:10), là où le log écrivait `[STATE-LISTENER] 291 listener(s) état (re)enregistré(s)` ; environ 7 500 recréations le 23/11 (≈ 26 resynchronisations) ; identifiants d'un même tic proches. Autres plugins écartés.
- Impact : pollution du centre de messages ; perte possible d'une mise à jour d'état vers HA pour une commande qui change pendant la resynchronisation.

### Faits établis dans le code (`85bab95`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | `syncStateListeners()` délègue à la fonction pure `jeedom2ha_realign_state_listeners()` : relevé des existants, création de **toutes** les cibles, puis suppression de **tous** les existants. | `core/class/jeedom2ha.class.php` (`syncStateListeners`), `core/php/jeedom2ha_state_listeners.php` |
| F2 | Un listener d'état porte `class = jeedom2ha`, `function = stateListener`, options `eq_id` et `cmd_id`, un seul événement `#<cmd_id>#` (`addEvent($cmdId)`). | `syncStateListeners`, création |
| F3 | Cibles : `GET /system/state_listeners` → `{status: ok, listeners: [{eq_id, cmd_id, …}]}`, validées tout-ou-rien par `jeedom2ha_normalize_state_listener_targets()` ; échec ou réponse invalide → rien n'est touché. | `core/php/jeedom2ha_state_listeners.php` |
| F4 | Appelants : post-bootstrap du démon, `cron5()` via `reevaluateDecisionsIfChanged()` (chemin `listeners`), « Relire Jeedom » (`scanTopology`), choix des scénarios, après « Publier ». | voir l'enquête ci-dessous |
| F5 | Les tests de 19.5 appellent `jeedom2ha_realign_state_listeners` avec cinq arguments et des listeners opaques (`'L1'`, `'L2'`) : ils fixent le comportement « tout remplacer ». | `tests/unit/test_story_19_5_php_relay.php` |

## Critères d'acceptation

1. **AC1 — Différence pure** : une fonction pure `jeedom2ha_state_listener_plan($targets, $existing)` (sans cœur Jeedom) rend `keep`, `create` et `remove` à partir des cibles normalisées et de la description des listeners existants (`eq_id`, `cmd_id`, événements).
2. **AC2 — Conserver** : un listener existant dont le couple (eq_id, cmd_id) est toujours voulu **et** qui surveille exactement l'événement `#<cmd_id>#` est conservé tel quel (même identifiant, aucune écriture).
3. **AC3 — Créer** : une cible sans listener conservé est créée (une seule fois, même si le démon la renvoie deux fois).
4. **AC4 — Supprimer** : sont supprimés seulement les listeners qui ne sont plus voulus, les doublons (on garde le premier relevé, le plus ancien) et les listeners mal formés (options absentes ou non numériques, événements illisibles, absents, multiples ou différents de `#<cmd_id>#`, description qui lève une exception). Un listener mal formé d'une cible voulue est remplacé : création d'abord, suppression ensuite.
5. **AC5 — Parc inchangé** : si le parc n'a pas changé, une resynchronisation ne crée ni ne supprime rien.
6. **AC6 — Échec du démon** : échec de récupération, réponse invalide ou cible mal formée → rien n'est touché (comportement inchangé). Une liste valide vide supprime tous les listeners (comportement inchangé : plus rien de publié).
7. **AC7 — Ordre et robustesse** : récupérer → valider → relever → créer les manquants → supprimer les indésirables. Création interrompue → aucune suppression ; suppression interrompue → avertissement, résorbé au réalignement suivant (inchangé, 19.5).
8. **AC8 — Compatibilité** : sans fonction de description (appel historique à cinq arguments), le comportement reste « tout remplacer » : les tests de 19.5 passent sans modification.
9. **AC9 — Journal** : une ligne `[STATE-LISTENER]` donne le nombre en place, conservés, créés et supprimés ; niveau `info` seulement s'il y a eu une création ou une suppression, `debug` sinon.
10. **AC10 — Tests CI** (`tests/test_php_story_12_6_state_listeners_diff.php`, format des tests PHP autonomes) : cible identique → 0 création, 0 suppression ; ajout d'une commande → 1 création ; retrait → 1 suppression ; doublons nettoyés ; cible vide ou démon en échec → aucune suppression en échec, tout supprimé pour une liste valide vide ; listener mal formé ; événement différent ; eq_id différent ; ordre des opérations ; câblage de `syncStateListeners`. Écrits rouges d'abord.
11. **AC11 — Enquête (lecture du code)** : tous les chemins qui réalignent les listeners sont listés, avec celui qui tourne aux tics de 5 minutes et sa condition ; conclusion et relevés de production à faire (section « Enquête »). Un éventuel second défaut n'est **pas** corrigé ici.
12. **AC12 — Preuve terrain (hors session cloud)** : voir Task 5. La preuve se fait par l'état (table `listener`, `log/listener_execution`, entité HA), pas par le journal du plugin : le niveau de log par défaut de la prod n'écrit rien.

## UI Impact

- **UI Impact:** Non — aucun changement d'interface ; côté Jeedom, le centre de messages n'est plus pollué.

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) — **hors session cloud** (CLAUDE.md : jamais `deploy-to-box.sh` ni accès box/HA) ; à ClaudeBox / porteur du projet
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`
- [x] Task 1 — Tests rouges (AC10)
- [x] Task 2 — Fonction pure de différence et réalignement (AC1 à AC8)
  - [x] 2.1 `jeedom2ha_state_listener_describe_normalize()` : description → `['eq_id', 'cmd_id']` ou null (mal formé)
  - [x] 2.2 `jeedom2ha_state_listener_plan()` : keep / create / remove
  - [x] 2.3 `jeedom2ha_realign_state_listeners()` : sixième argument facultatif `describeListener`, septième `&$stats`
- [x] Task 3 — Câblage dans `syncStateListeners()` (description : id, options, événements) et journal (AC9)
- [x] Task 4 — Suites vertes : pytest, flake8, `php -l`, tests PHP autonomes, Node (garde 25.4 AC31, lignes remplacées déclarées si besoin) ; sprint-status
- [x] Task 6 — Revue de code (`bmad-code-review`, auto-revue) : voir « Review Findings »
- [ ] Task 5 — Preuve terrain (hors session cloud, ClaudeBox / agent prod, lecture seule sauf déploiement)
  - [ ] Avant déploiement : nombre de listeners `class = jeedom2ha`, `function = stateListener` et liste de leurs identifiants (``SELECT `id`, `event`, `option` FROM `listener` WHERE `class`='jeedom2ha' AND `function`='stateListener' ORDER BY `id` ``)
  - [ ] Après déploiement et un premier réalignement : même relevé (le premier passage peut créer ou supprimer : doublons, listeners mal formés)
  - [ ] Après **deux tics de resynchronisation** (constatés par l'état : deux valeurs successives de `sync_at` dans l'export de décision, ou deux changements de la clé `decisionFingerprint`) : identifiants **inchangés**, même nombre
  - [ ] Sur 24 h : nouvelles lignes `Listener non trouvé` dans `log/listener_execution` et dans le centre de messages, objectif **0 venant de jeedom2ha** (identifiants comparés à la table `listener` de jeedom2ha)
  - [ ] Une commande info publiée qui change (capteur vivant) → l'entité HA suit (valeur et horodatage)

## Enquête — pourquoi environ 26 resynchronisations par jour (AC11, lecture du code seulement)

### Chemins qui réalignent les listeners

| # | Chemin | Déclencheur | Condition | Pointeur |
|---|---|---|---|---|
| C1 | `bootstrapRuntimeAfterDaemonStart()` | démarrage du démon (`deamon_start`) | synchro de démarrage `status: ok` | `core/class/jeedom2ha.class.php` (appel `self::syncStateListeners()` après `[SYNC] Runtime bootstrap startup sync succeeded`) |
| C2 | `cron5()` → `reevaluateDecisionsIfChanged()` → `jeedom2ha_reevaluation_tick()` → dépendance `listeners` | **cron du plugin, toutes les 5 minutes** | empreinte courante ≠ empreinte mémorisée (ou mémorisée vide), démon prêt, topologie lue, synchro de service `status: ok` (complète **ou partielle**) | `core/class/jeedom2ha.class.php` (`cron5`, `reevaluateDecisionsIfChanged`), `core/php/jeedom2ha_reevaluation.php` (`jeedom2ha_reevaluation_tick`) |
| C3 | ajax `scanTopology` (« Relire Jeedom ») | clic | synchro `status: ok` | `core/ajax/jeedom2ha.ajax.php` |
| C4 | ajax `saveScenarioPublication` → `_jeedom2ha_scenario_publication_rescan()` | clic | synchro `status: ok` | `core/ajax/jeedom2ha.ajax.php` |
| C5 | ajax `executeHaAction` (intention `publier`) → `jeedom2ha_realign_after_action()` | clic | réponse du démon non nulle | `core/ajax/jeedom2ha.ajax.php`, `core/php/jeedom2ha_state_listeners.php` |

Aucun réalignement inconditionnel : `systemHealthTick()` (l'autre pas de `cron5`) n'y touche pas, `deamon_info()` non plus.

### Celui des tics de 5 minutes

C2. Le pas n'appelle le démon que si l'empreinte `jeedom2ha_decision_fingerprint()` change. Elle est calculée sur : chaque `eqLogic` (id, `isEnable`, source d'exclusion), chaque **scénario** (id, `isActive`), les plugins et pièces exclus, les choix de publication des scénarios. Elle est stable par construction (triée, condensé SHA-256, aucun horodatage, aucun nom) : pas de comparaison instable.

Trois conditions mènent à une synchro de service à un tic :

1. **H1 — changement réel de l'état qui pilote les décisions** (comportement voulu par la story 24.14, décision D2 A) : un scénario activé ou désactivé par un autre scénario, un agenda ou un mode (`isActive`), un équipement activé ou désactivé (`isEnable`), un équipement ou un scénario créé ou supprimé par un plugin. La docstring de `jeedom2ha_reevaluation.php` le prévoit : ces drapeaux « basculent plusieurs fois par jour ».
2. **H2 — synchro partielle qui se répète** : si la réponse de `/action/sync` n'est pas complète (`operation_result` ≠ `succes`, ou `scenario_availability_complete` faux), l'empreinte n'est pas mémorisée (elle a été vidée avant l'envoi) ; le tic suivant resynchronise, **et réaligne quand même les listeners** (`jeedom2ha_reevaluation_tick`, dépendance `listeners` appelée aussi en `partial`). Côté démon (`transport/http_server.py`, fin de `_handle_action_sync`), `partiel` vient d'un échec technique de publication encore mémorisé dans `publications`, d'un bouton ou d'une disponibilité de scénario non publié, ou d'une dépublication différée en attente (`pending_discovery_unpublish`, `pending_local_availability_cleanup`). Une synchro partielle persistante donne une synchro à **chaque** tic (288 par jour) ; des épisodes de deux heures donnent environ 24 synchros.
3. **H3 — état modifié pendant la lecture** : l'empreinte relue après l'extraction diffère, rien n'est mémorisé, une synchro de plus au tic suivant (rare, une par changement).

### Conclusion

- **Pas de réalignement inconditionnel, pas d'empreinte instable** dans le code : les ≈ 26 resynchronisations viennent de C2 sur changement d'empreinte. Avec le volume observé (≈ 26 par jour, pas 288), **H1 est l'hypothèse la plus probable** : des scénarios ou équipements qui basculent `isActive` / `isEnable` dans la journée, ce que 24.14 traite volontairement par une synchro de service. La configuration du plugin ne bouge pas, mais l'empreinte ne dépend pas seulement d'elle.
- **Ce n'est donc pas, en l'état, un second défaut prouvé** : la synchro de service sur bascule est le comportement voulu ; le défaut était qu'elle recrée les 291 listeners, ce que corrige cette story (une synchro sans changement de parc publié ne touche plus aucun listener).
- **Second défaut possible, à confirmer par les relevés (H2)** : si les relevés montrent des tics **consécutifs** avec l'empreinte mémorisée vide, une synchro partielle persistante relance une synchro complète toutes les 5 minutes. Cause probable : un échec de publication ou une dépublication différée qui ne se résorbe pas ; pointeurs : `core/php/jeedom2ha_reevaluation.php` (`jeedom2ha_reevaluation_tick`, branche `$partial`), `resources/daemon/transport/http_server.py` (calcul de `_has_failures` / `_has_deferred` et de `scenario_availability_complete`). Correction proposée (PR séparée) : borner les relances d'une synchro partielle (par exemple mémoriser l'empreinte avec un marqueur « partiel » et ne relancer qu'après N tics ou sur changement réel), et journaliser en `warning` la cause exacte (identifiants en échec) pour qu'elle soit visible au niveau de log par défaut.
- **Amélioration possible, non retenue ici** : l'empreinte inclut le `isActive` de tous les scénarios, y compris ceux que l'utilisateur ne publie pas, et le `isEnable` d'équipements exclus. Les retirer réduirait les synchros, mais le statut du démon expose `is_active` pour tous les scénarios (liste de la page) : à trancher par le porteur du projet, pas un défaut.

### Relevés à faire en production (lecture seule)

1. **Empreinte mémorisée** : valeur de la clé `decisionFingerprint` du plugin (`config` : `plugin = 'jeedom2ha'`, `key = 'decisionFingerprint'`) relevée juste avant et juste après plusieurs tics xx:x0 / xx:x5 (par exemple à :04:50 et :05:30 sur une heure). Valeur qui change d'un tic à l'autre → H1 ; valeur vide qui le reste plusieurs tics de suite → H2.
2. **État qui pilote l'empreinte** : `SELECT id, isActive FROM scenario ORDER BY id` et `SELECT id, isEnable, eqType_name, object_id FROM eqLogic ORDER BY id`, pris à deux instants encadrant une resynchronisation ; la différence nomme le scénario ou l'équipement qui bascule (H1), sans rien modifier.
3. **Horodatage des synchros** : export de décision du démon (`GET /system/decision_export` en local avec le secret, ou le fichier `jeedom2ha_decision_export.json` du dossier de données du démon), champs `sync_at` et `sync_origin`, relevé plusieurs fois ; `sync_origin` doit désigner la synchro de service du cron.
4. **Résultat de la dernière synchro** : `GET /system/status` du démon (en local, avec le secret), champ `derniere_operation_resultat` (`succes` / `partiel` / `echec`) après chaque tic qui a resynchronisé : `partiel` répété → H2.
5. **Rythme** : horodatages des groupes `Listener non trouvé` du 23/11 (déjà relevés) : tics consécutifs pendant des heures → H2 ; tics isolés irréguliers → H1. Croiser avec l'historique des scénarios (`log/scenarioLog/`, dates des activations / désactivations) si H1.
6. **Facultatif** : passer un temps court le log du plugin en `info` pour voir `[REEVAL] État Jeedom changé …` et `[REEVAL] Synchro de service incomplète …` (à décider par le porteur du projet : c'est une modification de configuration).

## Dev Notes

- **Description d'un listener** (adaptateur du cœur, dans la classe) : `getId()`, `getOption('eq_id')`, `getOption('cmd_id')`, `getEvent()` (tableau ou chaîne JSON selon la version du cœur, éléments `#<id>#`). La fonction pure normalise et refuse tout ce qu'elle ne comprend pas : un listener douteux est remplacé, jamais conservé.
- **eq_id différent** pour un même cmd_id : remplacé (l'option `eq_id` sert au callback `stateListener`).
- **Ordre de conservation des doublons** : le premier relevé (ordre de `listener::byClass`, identifiants croissants) ; les suivants sont supprimés.
- **Aucune écriture** sur un listener conservé (pas de `save()`), pour ne pas toucher à son identifiant ni à sa ligne.
- **Retour de `syncStateListeners()`** : nombre de listeners en place pour le parc publié (conservés + créés), comme avant pour un premier enregistrement.
- **Hors périmètre** : le cœur Jeedom, les autres plugins, le démon, l'empreinte de 24.14.

### Dev Agent Guardrails

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`
- Session cloud : aucun déploiement, aucun accès box / HA (CLAUDE.md).

### Project Structure Notes

- `core/php/jeedom2ha_state_listeners.php` (fonctions pures), `core/class/jeedom2ha.class.php` (`syncStateListeners`).
- Tests : `tests/test_php_story_12_6_state_listeners_diff.php` (nouveau, exécuté par le job PHP de la CI).

### References

- [Source: _bmad-output/implementation-artifacts/12-1-streaming-valeur-sensor-binary-sensor-vague-1.md] (listeners `stateListener`, R1)
- [Source: tests/unit/test_story_19_5_php_relay.php] (AC11 de 19.5 : ordre récupérer → valider → créer → purger)
- [Source: _bmad-output/implementation-artifacts/20-2-preuve-complement-2026-10-06.md] (CC-45)
- [Source: core/php/jeedom2ha_reevaluation.php] (story 24.14, empreinte et pas du cron)

## Review Findings

Auto-revue adversariale (`bmad-code-review`, 2026-11-23, même session) sur le diff `85bab95..fix/state-listeners-diff`.

- [x] [Review][Medium] Une cible à `eq_id` 0, admise par `jeedom2ha_normalize_state_listener_targets` (eq_id ≥ 0), aurait été jugée mal formée par la description (eq_id > 0 exigé) : son listener aurait été recréé à chaque réalignement, ce qui reproduisait le défaut pour cette cible. Corrigé : `eq_id` 0 accepté (négatif toujours refusé) ; deux tests ajoutés. [`core/php/jeedom2ha_state_listeners.php`, `jeedom2ha_state_listener_describe_normalize`]
- [x] [Review][Low] Résiduel assumé : la suppression d'un listener qui n'est plus voulu (parc qui change vraiment) peut encore croiser un événement en cours et donner un « Listener non trouvé » isolé. Inévitable sans toucher au cœur ; rare (seulement quand le parc publié change) et sans perte d'état (la commande n'est plus publiée).
- [x] [Review][Low] Format de `listener::getEvent()` selon la version du cœur (tableau ou chaîne JSON) : les deux sont acceptés ; tout autre format rend le listener « mal formé », donc remplacé une fois puis stable (les listeners créés par `addEvent` ont toujours la forme attendue). À vérifier sur la prod pendant la preuve terrain (Task 5 : identifiants inchangés après deux tics).
- Pas d'autre constat : ordre créer → supprimer conservé, échec du démon sans effet, compatibilité 19.5 (39/39 inchangés), PHP 7.4 (aucune syntaxe 8.x), aucun nom réel ni IP.

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (session Claude Code cloud déléguée, 2026-11-23).

### Debug Log References

- Branche `fix/state-listeners-diff` depuis `origin/main` `85bab95`.
- Cycle rouge vérifié : `tests/test_php_story_12_6_state_listeners_diff.php` en échec (`jeedom2ha_state_listener_plan()` absente), puis 3 échecs de câblage tant que `syncStateListeners()` n'était pas modifiée ; 48/48 verts ensuite (dont 2 tests de la revue, rouges avant le correctif eq_id 0).

### Implementation Plan

- `jeedom2ha_state_listener_describe_normalize()` : description (`eq_id`, `cmd_id`, `events`) → couple normalisé, ou null si mal formé (un seul événement `#<cmd_id>#`, options numériques).
- `jeedom2ha_state_listener_plan()` : différence pure keep / create / remove (premier relevé conservé, doublons et indésirables supprimés, cibles dédoublonnées).
- `jeedom2ha_realign_state_listeners()` : 6e argument facultatif `describeListener` (sans lui : « tout remplacer », comportement 19.5), 7e `&$stats` ; ordre récupérer → valider → relever → créer → supprimer inchangé ; retour = conservés + créés.
- `syncStateListeners()` : description lue sans écriture (`getId`, `getOption`, `getEvent`), journal `en place (conservés, créés, supprimés)` en `info` seulement s'il y a eu un changement.

### Completion Notes List

- AC1 à AC11 faits ; AC12 / Task 5 (preuve terrain) et Task 0 restent à ClaudeBox / agent prod.
- Enquête (AC11) : pas de réalignement inconditionnel ni d'empreinte instable ; les tics de 5 minutes viennent de `cron5` → `reevaluateDecisionsIfChanged` sur changement d'empreinte. Hypothèse principale H1 (bascules `isActive` / `isEnable`, comportement voulu de 24.14) ; second défaut possible H2 (synchro partielle répétée) à confirmer par les relevés, non corrigé ici.
- Garde 25.4 AC31 : cinq lignes remplacées de `core/class/jeedom2ha.class.php` déclarées (`REPLACED_BY_12_6`).
- Suites : pytest 3809 passés, 37 ignorés ; flake8 vert ; `php -l` vert sur tous les fichiers ; tests PHP autonomes 24 verts (3 exigent un vrai cœur Jeedom, ignorés comme en CI), dont 19.5 39/39 sans modification ; Node 1649 / 1652, les 3 échecs `25.4 AC8` préexistants (garde-fou périmé connu, hors périmètre).

### File List

- `core/php/jeedom2ha_state_listeners.php` (modifié)
- `core/class/jeedom2ha.class.php` (modifié)
- `tests/test_php_story_12_6_state_listeners_diff.php` (nouveau)
- `tests/unit/test_story_25_4_non_regression.node.test.js` (modifié : `REPLACED_BY_12_6`)
- `_bmad-output/implementation-artifacts/12-6-state-listeners-recalage-par-difference.md` (nouveau)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modifié)
