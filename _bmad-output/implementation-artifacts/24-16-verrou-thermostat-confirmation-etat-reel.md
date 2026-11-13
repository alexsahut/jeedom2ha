# Story 24.16 : Verrou de thermostat confirmé par l'état réel

Status: ready-for-dev

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

- [ ] T1 — Test rouge qui reproduit le constat : forme de production (climate + secondaire de verrou, synchroniseur d'état actif), ordre `ON` sur `jeedom2ha/<eq>/<lock_info>/set` → aujourd'hui `optimistic_controlled`. Identifier la condition de F3 qui échoue et la consigner dans le Dev Agent Record.
- [ ] T2 — Corriger dans `sync/command.py` : famille de commande propre au verrou (par exemple `thermostat_lock`) ou branche dédiée dans `_select_confirmation_policy`, avec `real_state_confirmation` si l'état est fiable, sinon `stateless` ; corriger aussi la cause trouvée en T1 si elle empêche l'état fiable.
- [ ] T3 — Valeur vide : vérifier (et corriger si besoin) que `''` ne publie rien à l'état initial ni au streaming.
- [ ] T4 — Tests (voir ci-dessous) et garde 25.4.
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

## Journal

- 2026-11-13 — Constat à la recette de 24-15 (ClaudeBox) ; story rédigée par une session cloud déléguée, `ready-for-dev`.
