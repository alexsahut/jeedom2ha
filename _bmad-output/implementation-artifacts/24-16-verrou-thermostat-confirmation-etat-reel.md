# Story 24.16 : Verrou de thermostat confirmé par l'état réel

Status: review

> Correctif court, suite de la recette de 24-15 (13/11/2026). Story rédigée par une session cloud déléguée (2026-11-13), en lecture seule du code (`origin/main` `575dc58`), sans accès à la box ni à Home Assistant. Aucun nom réel, aucune IP, aucune marque (CC-48) : identifiants seulement.

## Story

En tant qu'utilisateur qui verrouille un thermostat depuis Home Assistant,
je veux que l'interrupteur « Verrouillage » ne change d'état que lorsque Jeedom confirme le verrou,
afin que HA ne montre jamais un verrou supposé.

**Parcours : démon.** Comportement standard attendu chez tout utilisateur du plugin Jeedom « thermostat » (aucun cas propre à une installation).

## Contexte : constat de recette (24-15, AC12, 13/11/2026, heures UTC)

- Sur l'eq 219, verrou on / off envoyés depuis HA entre 07:41 et 07:43 : les ordres partent bien (cmds 1784 / 1785).
- Le journal du démon donne pour l'interrupteur de verrouillage :
  `[SYNC-CMD] ... topic=jeedom2ha/219/1783/set reason_code=optimistic_controlled action=select_confirmation_policy`
- Les autres ordres du thermostat (consigne, mode, preset) sont confirmés par l'état réel (`real_state_confirmation`).
- 24-15 (D4 A) veut un interrupteur « Verrouillage » alimenté par `THERMOSTAT_LOCK` et dit « jamais d'état supposé » : la politique `optimistic_controlled` est contraire à cette règle.
- Cas observé en production : sur un équipement, l'info `THERMOSTAT_LOCK` vaut `''` (valeur vide).

## Faits établis dans le code (`origin/main` `575dc58`, lecture seule)

| # | Fait | Pointeur |
|---|---|---|
| F1 | L'ordre du verrou est traduit avec `command_family="on_off"`, sans `optimistic_state_payload`. | `sync/command.py`, `_translate_thermostat_lock_command` (~`:608-620`) |
| F2 | Pour `on_off` sur un `switch`, la politique est `real_state_confirmation` si `_has_reliable_state` est vrai, **sinon `optimistic_controlled`**. Le verrou n'a pas de branche propre (les familles `valve`, `lock`, `climate` tombent sur `stateless`, jamais sur `optimistic_controlled`). | `sync/command.py`, `_select_confirmation_policy` (~`:1087-1131`) |
| F3 | `_has_reliable_state` exige : un `state_topic` dans la décision, un synchroniseur d'état actif, un type streamé, et un canal `state` alimenté par une info (`has_reliable_channel`). | `sync/command.py` (~`:1133-1150`) ; `sync/readback.py`, `has_reliable_channel`, `readback_commands` |
| F4 | `THERMOSTAT_LOCK` est ajouté aux clés d'état du `switch` ; la traduction de l'état du verrou rend `ON` pour `1` / `true` / `on`, `OFF` pour `0` / `false` / `off`, et **rien** pour toute autre valeur. | `sync/readback.py:55-57` ; `sync/state.py` (~`:876-883`, `_LOCK_SWITCH_ON` / `_LOCK_SWITCH_OFF`) |
| F5 | La décision d'un secondaire porte `state_topic=_resolve_state_topic(...)`, qui rend le `state_topic` du `switch` (`jeedom2ha/<eq>/<lock_info>/state`). | `transport/http_server.py:126-140`, `:470`, `:625` |
| F6 | Aucun test de 24-15 ne vérifie la politique de confirmation du verrou. | `resources/daemon/tests/unit/test_story_24_15_thermostat_climate_complet.py` |

La lecture statique ne dit pas laquelle des conditions de F3 est fausse en production : le premier travail est de reproduire le constat par un test (forme de production : climate principal + secondaire de verrou, décision du secondaire issue d'une vraie synchro).

## Critères d'acceptation

1. **AC1 — Confirmation par l'état réel.** Un ordre `ON` / `OFF` sur l'interrupteur « Verrouillage » d'un thermostat dont l'info `THERMOSTAT_LOCK` est streamée journalise `reason_code=real_state_confirmation` ; l'état de l'interrupteur ne change que par l'état streamé de `THERMOSTAT_LOCK`.
2. **AC2 — Jamais d'état supposé.** Pour cet interrupteur, la politique n'est **jamais** `optimistic_controlled` : sans état fiable, elle est `stateless`. Aucun message n'est publié sur le topic d'état après un ordre.
3. **AC3 — Valeur vide.** Une valeur de `THERMOSTAT_LOCK` vide (`''`, ou espaces seuls) ne publie rien : ni à l'état initial (démarrage, « Relire Jeedom », synchro de service), ni au streaming. Même règle pour toute valeur non reconnue.
4. **AC4 — Ordres inchangés.** `ON` → `THERMOSTAT_SET_LOCK`, `OFF` → `THERMOSTAT_SET_UNLOCK` ; tout autre payload refusé (`invalid_command_payload`) ; commande absente refusée (`missing_action_command`).
5. **AC5 — Rien d'autre ne change.** Discovery, `unique_id`, topics, `entity_category: config` de l'interrupteur inchangés ; les autres `switch` (prises, interrupteurs) gardent leur politique actuelle, `optimistic_controlled` compris quand ils n'ont pas d'état fiable ; le `climate` est inchangé.
6. **AC6 — Non-régression.** Suites Python et Node, `flake8` vertes ; garde 25.4 tenue (lignes remplacées déclarées) ; `desktop/js/jeedom2ha_mapping_override.js` intact (garde 24.2).
7. **AC7 — Preuve terrain (ClaudeBox, avec l'accord d'Alexandre).** Sur un thermostat réel : verrou on puis off depuis HA ; le journal porte `reason_code=real_state_confirmation` ; l'interrupteur suit l'état réel ; état initial restauré.

## Tâches

- [x] T1 — Test rouge qui reproduit le constat : forme de production (climate + secondaire de verrou, synchroniseur d'état actif), ordre `ON` sur `jeedom2ha/<eq>/<lock_info>/set` → aujourd'hui `optimistic_controlled`. Identifier la condition de F3 qui échoue et la consigner dans le Dev Agent Record.
- [x] T2 — Corriger dans `sync/command.py` : famille de commande propre au verrou (par exemple `thermostat_lock`) ou branche dédiée dans `_select_confirmation_policy`, avec `real_state_confirmation` si l'état est fiable, sinon `stateless` ; corriger aussi la cause trouvée en T1 si elle empêche l'état fiable.
- [x] T3 — Valeur vide : vérifier (et corriger si besoin) que `''` ne publie rien à l'état initial ni au streaming.
- [x] T4 — Tests (voir ci-dessous) et garde 25.4.
- [ ] T5 — Preuve terrain AC7 (ClaudeBox, hors session cloud).

## Tests attendus (`resources/daemon/tests/unit/test_story_24_16_verrou_thermostat_confirmation.py`, identifiants synthétiques)

- Politique : verrou avec info streamée → `real_state_confirmation` (forme de production, décision du secondaire issue de la synchro) ; sans synchroniseur actif ou sans info → `stateless` ; jamais `optimistic_controlled`.
- Aucun message publié sur le topic d'état après un ordre `ON` ou `OFF`.
- État : `1` → `ON`, `0` → `OFF`, `''` → rien, `'  '` → rien, valeur inconnue → rien ; à l'état initial et au streaming.
- Ordres : `ON` / `OFF` vers les bonnes commandes ; payload invalide et commande absente refusés.
- Non-régression : un `switch` ordinaire sans état fiable reste `optimistic_controlled` ; un `switch` ordinaire avec état fiable reste `real_state_confirmation` ; climate inchangé (tests 24-15 verts).

## Garde-fous

- Ne pas toucher la politique des autres `switch` ni des autres types.
- Aucun état optimiste ni inventé.
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud ; aucun accès box ni HA.
- Garde 25.4 : déclarer toute ligne remplacée dans `resources/daemon/`.

## Dev Agent Record (2026-11-13, session cloud déléguée)

Branche `story/24-16-verrou-thermostat-confirmation-etat-reel` depuis `origin/main` `be23478`. TDD : `resources/daemon/tests/unit/test_story_24_16_verrou_thermostat_confirmation.py` écrit d'abord, rouge sur le constat exact de production (`[SYNC-CMD] eq_id=11000 topic=jeedom2ha/11000/110009/set reason_code=optimistic_controlled action=select_confirmation_policy`), puis le code.

### Cause (T1)

Forme de production reproduite par une **vraie synchro** (`/action/sync` sur le corpus doré, thermostat synthétique 11000 avec verrou), synchroniseur d'état actif. La condition de F3 qui échoue est la **première** : `decision.state_topic` est vide.

- L'interrupteur « Verrouillage » est un **secondaire** du climate (`additional_mappings`). Sa décision (`publication_decision_ref`) est produite par `evaluate_equipment()` (`decide_publication`) et ne reçoit **jamais** de `state_topic` : seul le principal le reçoit, dans `_prepare_publication_bookkeeping` (`http_server.py`). F5 ne vaut que pour les chemins d'action (`_scope_excluded_decision`, `_reset_secondary_runtime_state`), pas pour la synchro.
- Relevé du test : décision du secondaire `state_topic=None` ; principal `jeedom2ha/11000/state` ; topic propre de l'interrupteur (`reason_details`) `jeedom2ha/11000/110009/state`.
- `StateSynchronizer` lit d'abord le topic propre du candidat (`_candidate_state_topic`) : l'état du verrou est donc bien streamé (constat `initial_state_published` en production), alors que `CommandSynchronizer._has_reliable_state` ne lit que la décision → faux → `optimistic_controlled`.

### Correctif (T2)

`sync/command.py`, `_select_confirmation_policy` : branche dédiée à l'interrupteur `thermostat_lock`, placée avant la branche `on_off`. Elle évalue `_has_reliable_state` avec le topic propre de l'interrupteur (copie `dataclasses.replace` de la décision, jamais mutée) : `real_state_confirmation` si l'état est fiable, sinon `stateless` ; jamais `optimistic_controlled`. L'ordre n'ayant pas de `optimistic_state_payload`, rien n'est publié sur le topic d'état après l'ordre. **Ajouts seuls** (11 lignes, aucune ligne retirée sous `resources/daemon/`) : garde 25.4 inchangée. Traduction des ordres, discovery, `unique_id`, topics et autres `switch` non touchés.

### Valeur vide (T3)

Déjà conforme, aucun code : `_translate_value` rend `None` pour une valeur vide ou d'espaces, et la table du verrou rend `None` pour toute valeur non reconnue. Prouvé par test à l'état initial (synchro) et au streaming : `''`, `'   '`, `'abc'`, `'2'` → rien publié.

### Tests (T4)

21 tests : politique en forme de production (`ON` / `OFF` → `real_state_confirmation`, aucune publication MQTT par le synchroniseur d'ordres) ; sans synchroniseur d'état ou sans info de verrou → `stateless` ; états `1` / `0` / `true` / `off` streamés, valeurs vides ou inconnues → rien ; ordres `ON` / `OFF` vers les bonnes commandes, payload invalide (`invalid_command_payload`) et ordre absent (`missing_action_command`) refusés ; non-régression : `switch` ordinaire sans état fiable → `optimistic_controlled`, avec état fiable → `real_state_confirmation`, secondaire ordinaire sans `state_topic` de décision → `optimistic_controlled` (inchangé).

Suites : pytest 3246 passés, 1 ignoré ; `flake8 resources/daemon tests` vert ; `node --test --test-concurrency=2` 1211 passés, 3 ignorés, 0 échec ; `php -l` 38/38 ; tests PHP 17 passés, 3 ignorés (cœur Jeedom requis).

### Points ouverts

- **Défaut plus large, hors périmètre (AC5)** : tout `switch` **secondaire** (prises multiples de `mapping/switch.py`, etc.) a la même décision sans `state_topic` après une synchro, donc `optimistic_controlled` même quand son état est streamé. Le corriger à la source (poser `state_topic` sur les décisions secondaires dans la synchro) changerait la politique de ces switch : à décider dans une story dédiée.
- **T5 / AC7** : preuve terrain à ClaudeBox (verrou on puis off depuis HA, journal `reason_code=real_state_confirmation`, état initial restauré).

## Journal

- 2026-11-13 — Constat à la recette de 24-15 (ClaudeBox) ; story rédigée par une session cloud déléguée, `ready-for-dev`.
- 2026-11-13 — Dev-story (session cloud déléguée, TDD) : cause trouvée (décision du secondaire sans `state_topic`), correctif en ajouts seuls, `review` ; reste la preuve terrain AC7.
