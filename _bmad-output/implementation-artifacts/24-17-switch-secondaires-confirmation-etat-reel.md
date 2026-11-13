# Story 24.17 : Interrupteurs secondaires confirmés par l'état réel

Status: review

> Suite de 24-16 (point ouvert « défaut plus large, hors périmètre »). Rédaction validée par Alexandre le 13/11/2026. Story rédigée par une session cloud déléguée (2026-11-13), documentaire, en lecture seule du code (`origin/main` `180b3ab`), sans accès à la box ni à Home Assistant. Aucun nom réel, aucune IP, aucune marque (CC-48) : identifiants seulement, ceux du corpus doré. **Draft** : la décision D1 (et le sous-point D2) revient à Alexandre avant `ready-for-dev`.

## Story

En tant qu'utilisateur qui pilote depuis Home Assistant une entité secondaire d'un équipement (une sortie d'une prise multiple, par exemple),
je veux que le démon confirme l'ordre par l'état réel streamé de cette entité, comme pour l'entité principale,
afin que le journal et la politique de confirmation disent la vérité et qu'aucun état supposé ne puisse être publié sur une entité dont l'état réel est connu.

**Parcours : démon.** Comportement standard attendu chez tout utilisateur du plugin (aucun cas propre à une installation).

## Constat hérité de 24-16

- Dans une synchro, la décision d'un mapping secondaire (`additional_mappings`, `publication_decision_ref`) ne reçoit **jamais** de `state_topic`. Seul le principal le reçoit, dans `_prepare_publication_bookkeeping`.
- `CommandSynchronizer._has_reliable_state` lit le `state_topic` **de la décision** : il est vide, donc faux. Tout `switch` secondaire tombe en `optimistic_controlled`, même quand son état est streamé sur son topic propre (`reason_details["state_topic"]`).
- 24-16 a corrigé ce cas pour le seul interrupteur « Verrouillage » du thermostat, par une branche dédiée dans `_select_confirmation_policy` qui relit le topic propre.

## Faits établis dans le code (`origin/main` `180b3ab`, lecture seule)

| # | Fait | Pointeur |
|---|---|---|
| F1 | La décision d'un secondaire vient de `evaluate_equipment()` (`decide_publication`) sans `state_topic`. `_publish_additional_sensors` ne règle que `active_or_alive`, `discovery_published` et le résultat de publication. Seul le principal reçoit `state_topic`, dans `_prepare_publication_bookkeeping`. | `transport/http_server.py:224-298`, `:362-375` |
| F2 | Les chemins d'action posent un `state_topic` sur un secondaire seulement quand aucune décision de synchro n'existe (`_reset_secondary_runtime_state`, branche « jamais synchronisé »). Sinon ils recopient la décision précédente (`dataclasses.replace`), donc sans `state_topic`. | `transport/http_server.py:605-630` |
| F3 | `_resolve_state_topic` rend le topic propre (`reason_details["state_topic"]`) pour `switch`, `valve` et `lock`. Pour tout autre type, il rend `jeedom2ha/<eq>/state`, qui est le topic **du principal** quand il est appelé sur un secondaire. | `transport/http_server.py:126-142` |
| F4 | `_has_reliable_state` exige, dans l'ordre : un `state_topic` dans la décision, un synchroniseur d'état actif, un type streamé, et un canal `state` alimenté par une info (`has_reliable_channel`). | `sync/command.py:1144-1162` |
| F5 | Politique par famille : `on_off` (switch, light) → `real_state_confirmation` si l'état est fiable, **sinon `optimistic_controlled`**. `valve_open_close`, `lock_lock_unlock`, `barrier_toggle` et `cover_motion` → `real_state_confirmation`, sinon `stateless`. La branche 24-16 (`thermostat_lock`) passe avant `on_off` et relit le topic propre par `replace(decision, state_topic=own_topic)`. | `sync/command.py:1088-1142` |
| F6 | En `optimistic_controlled`, `_publish_optimistic_state` publie sur le `state_topic` **de la décision**. Pour un secondaire, il est vide : rien n'est publié, et le démon journalise en WARNING `reason_code=missing_state_topic_runtime action=skip_optimistic_state`. | `sync/command.py:1222-1235` |
| F7 | `StateSynchronizer` lit d'abord le topic propre du candidat (`_candidate_state_topic` : `reason_details["state_topic"]`, puis la décision, puis `jeedom2ha/<eq>/state`). Il parcourt le principal et les secondaires des types streamés (`_iter_streamed_candidates`). L'état d'un secondaire est donc déjà streamé sur son topic propre. | `sync/state.py:716-725`, `:780-792` |
| F8 | La discovery d'un `switch` déclare `state_topic` (topic propre pour un secondaire) et aucune clé `optimistic`. HA est donc non optimiste : il affiche l'état reçu sur ce topic. | `discovery/publisher.py:763-806` |
| F9 | Le routage d'un ordre retrouve le secondaire visé par son topic d'ordre et rend **sa propre** décision (`publication_decision_ref`), jamais celle du principal (I11). | `sync/command.py:346-426` |
| F10 | Canal fiable d'un `switch` : `STATE_KEYS["switch"]` = `ENERGY_STATE`, `SWITCH_STATE`, `PRESENCE`, `THERMOSTAT_LOCK`. **`FAN_STATE` n'y est pas**, alors que `SwitchMapper` groupe les trios `FAN_STATE` / `FAN_ON` / `FAN_OFF` en `switch` (14.1). Un trio `FAN_*`, principal ou secondaire, n'a donc jamais d'état fiable pour la politique de confirmation, alors que son état est streamé (le topic propre et `reason_details["cmd_id"]` l'alimentent). | `sync/readback.py:45-57`, `:89-127` ; `mapping/switch.py:66`, `:287-319` ; `sync/state.py:679-713` |

### Types secondaires actionnables produits par le code

| Type | Origine du secondaire | Topic propre | Famille d'ordre | Politique aujourd'hui |
|---|---|---|---|---|
| `switch` (trio `SWITCH_*`) | Plusieurs trios sur un équipement : le premier est principal, les autres secondaires (`SwitchMapper.map_all` → `_map_structural_multi_entity`) | oui | `on_off` | `optimistic_controlled` + WARNING `missing_state_topic_runtime` |
| `switch` (trio `FAN_*`) | Idem, famille `FAN` (14.1) | oui | `on_off` | `optimistic_controlled` + WARNING (et resterait `optimistic_controlled` même avec un topic, F10) |
| `switch` « Verrouillage » | `ClimateMapper.map_all` (24-15 D4 A) | oui | `on_off` (traduction dédiée) | `real_state_confirmation` (24-16) |
| `valve` | Plusieurs vannes, ou vanne ajoutée à une entité gardée (`_with_valves`, 24-8) | oui | `valve_open_close` | `stateless` (jamais `real_state_confirmation`) |
| `lock` | Serrure ajoutée à une entité gardée ou à une vanne (`_with_locks`, 24-9) | oui | `lock_lock_unlock` | `stateless` (jamais `real_state_confirmation`) |
| `light`, `cover` | **Aucun mapper ne les produit en secondaire** (`LightMapper` et `CoverMapper` rendent une seule entité ; un `light` agrégé est principal, 11.4). Possible seulement par une surcharge de type (D11) appliquée à un secondaire. | non (pas de `reason_details["state_topic"]` propre au type, F3) | `on_off` / `cover_motion` / `barrier_toggle` | `optimistic_controlled` (light) ou `stateless` (cover) |
| `sensor`, `binary_sensor` | Multi-capteurs (11.1) | oui | aucun ordre | sans objet |

### Mesure sur le corpus doré (`tests/fixtures/golden_corpus/sync_payload.json`, vraie synchro `/action/sync`, synchroniseur d'état actif)

Relevé fait par cette session dans un test jetable, hors dépôt. 33 secondaires au total : 24 `sensor`, 3 `binary_sensor`, 6 `switch`, aucun `valve`, `lock`, `light` ni `cover`.

| Équipement | Principal | Secondaires actionnables | Politique aujourd'hui | Politique avec le topic propre |
|---|---|---|---|---|
| 583 | `switch` (topic `…/583/5987/state` dans sa décision : `real_state_confirmation`) | 2 `switch` `SWITCH_*` (`…/583/6009/…`, `…/583/6010/…`) | `optimistic_controlled` | `real_state_confirmation` |
| 628 | `switch` (topic `…/628/5977/state` : `real_state_confirmation`) | 3 `switch` `SWITCH_*` (`…/628/5980/…`, `…/628/5983/…`, `…/628/6004/…`) | `optimistic_controlled` | `real_state_confirmation` |
| 11000 | `climate` | 1 `switch` « Verrouillage » | `real_state_confirmation` (24-16) | inchangé |

**5 cas concernés dans le corpus doré** : 5 `switch` secondaires `SWITCH_*`, sur 2 équipements. Un ordre `ON` sur `jeedom2ha/583/6009/set` journalise aujourd'hui :

```
[SYNC-CMD] eq_id=583 topic=jeedom2ha/583/6009/set reason_code=command_executed action=execute_command cmd_id=5999
[SYNC-CMD] eq_id=583 topic=jeedom2ha/583/6009/set reason_code=optimistic_controlled action=select_confirmation_policy
[SYNC-CMD] eq_id=583 topic=jeedom2ha/583/6009/set reason_code=missing_state_topic_runtime action=skip_optimistic_state
```

Aucun message n'est publié sur MQTT par le synchroniseur d'ordres. Le corpus doré n'a aucun trio `FAN_*` : F10 n'y est pas mesurable.

### Effet réel sur Home Assistant (à lire avant D1)

- **Pour un secondaire dont l'état est streamé (les 5 cas du corpus)**, HA affiche **déjà** l'état réel : la discovery déclare le topic propre, sans `optimistic` (F8), le synchroniseur d'état y publie l'état Jeedom (F7), et aucun état supposé n'est publié faute de topic dans la décision (F6). Ce qui est faux aujourd'hui, c'est la **politique annoncée** (`optimistic_controlled`) et le WARNING `missing_state_topic_runtime` à chaque ordre. Après correction, le journal dit `real_state_confirmation` et le WARNING disparaît. L'état affiché dans HA ne change pas ; seul le comportement du démon est rendu cohérent avec le principal.
- **Pour un secondaire sans état fiable** (trio `FAN_*`, F10 ; `light` obtenu par surcharge), l'effet dépend de l'option : voir les risques de D1 et le sous-point D2.
- **Pour `valve` et `lock` secondaires**, la politique passe de `stateless` à `real_state_confirmation`. Aucun effet dans HA : `stateless` ne publie rien, et `real_state_confirmation` non plus.

## Décisions d'Alexandre (13/11/2026, 12:01)

- **D1 : A** — correction à la source (topic d'état propre posé sur les décisions secondaires, tous les chemins).
- **D2 : oui (D2-a)** — `FAN_STATE` ajouté aux canaux d'état fiables du `switch` dans cette story.
- Les AC rédigés pour A et D2-a s'appliquent tels quels. Task 0 (lecture seule) à ClaudeBox avant la preuve terrain.

## Décision D1 (Alexandre) — où corriger

### Option A — Poser le `state_topic` propre sur les décisions secondaires, à la source

- **Quoi** : dans la synchro, `_publish_additional_sensors` (ou une fonction de tenue des secondaires appelée au même endroit) pose sur chaque décision secondaire `sec_decision.state_topic = reason_details["state_topic"]`. On ne le fait **que** pour les types qui ont un topic propre (`switch`, `valve`, `lock`), **jamais** avec le repli `jeedom2ha/<eq>/state` de `_resolve_state_topic` (F3). Même règle dans les chemins d'action qui fabriquent une décision secondaire (`_reset_secondary_runtime_state`, décision d'exclusion par le scope, F2) : une décision recopiée garde le topic, une décision neuve le reçoit.
- **Effet** : `_has_reliable_state`, `_publish_optimistic_state` et toute lecture future du `state_topic` d'une décision voient la même chose pour un principal et pour un secondaire. Les 5 `switch` du corpus passent en `real_state_confirmation` ; `valve` et `lock` secondaires aussi. La branche 24-16 devient redondante mais reste juste : on la garde (la retirer obligerait à déclarer des lignes remplacées à la garde 25.4, sans gain).
- **Risques** :
  - **Changement réel pour un secondaire sans état fiable.** Un trio `FAN_*` secondaire (F10) reste en `optimistic_controlled`. Mais `_publish_optimistic_state` trouve désormais un topic et **publie un état supposé** (`ON` / `OFF`, non retenu) sur le topic propre, alors qu'aujourd'hui il ne publie rien. HA montre alors brièvement un état supposé avant l'état streamé. C'est exactement le comportement actuel d'un trio `FAN_*` **principal**. D2 traite ce point.
  - **Topic du principal.** Si le repli `jeedom2ha/<eq>/state` était utilisé pour un secondaire `light` obtenu par surcharge, un état supposé serait publié sur le topic **du principal**. La règle « topic propre seulement » l'interdit : à couvrir par un test.
  - **Surface touchée.** La tenue des décisions est dans `transport/http_server.py`, sur plusieurs chemins : synchro, « Publier », exclusion par le scope, remise à zéro des secondaires, décision stable entre deux synchros (24-14). Il faut un test par chemin.
  - **Golden.** `expected_sync_snapshot.json` ne sérialise que les décisions des principaux (`runtime/mappings/<eq>/publication_decision_ref`, `runtime/publications/<eq>`) : il ne devrait pas changer. À vérifier ; s'il change, régénérer et justifier ligne à ligne.
- **Effet sur HA** : aucun changement d'affichage pour les secondaires à état streamé. Changement possible (état supposé publié) pour un secondaire sans état fiable, sauf si D2 est retenu.

### Option B — Généraliser la branche 24-16 dans `_select_confirmation_policy`

- **Quoi** : avant les branches par famille, `_select_confirmation_policy` calcule une décision effective. Si la décision n'a pas de `state_topic` et que le candidat a un `reason_details["state_topic"]` (types `switch`, `valve`, `lock`), on utilise `replace(decision, state_topic=own_topic)`, sans muter la décision. Les branches existantes s'appliquent ensuite à cette décision effective. La branche 24-16 devient un cas particulier ; on la garde pour le « jamais `optimistic_controlled` » du verrou.
- **Effet** : les 5 `switch` du corpus passent en `real_state_confirmation` ; `valve` et `lock` secondaires aussi. Rien d'autre ne bouge : la décision stockée reste sans `state_topic`.
- **Risques** :
  - **Correctif local, défaut latent.** Toute autre lecture du `state_topic` d'une décision secondaire (aujourd'hui `_publish_optimistic_state`, demain un autre consommateur) reste fausse. Pour un secondaire sans état fiable (trio `FAN_*`), la politique reste `optimistic_controlled`, le WARNING `missing_state_topic_runtime` reste et rien n'est publié : le journal continue d'annoncer une politique qui n'est pas appliquée. On peut passer la décision effective à `_publish_optimistic_state`, mais on retombe alors sur le risque principal de A.
  - **Deux sources de vérité** pour le topic d'un secondaire : la décision (vide) et la politique (topic propre).
  - **Surface touchée** : `sync/command.py` seul, en ajouts. Faible risque de régression.
- **Effet sur HA** : aucun changement d'affichage pour les secondaires à état streamé ; aucun changement pour les autres (rien n'est publié, comme aujourd'hui).

### Recommandation : option A

- C'est la cause qu'a trouvée 24-16 (F1) : la décision d'un secondaire est incomplète. B la contourne une seconde fois, A la corrige. Après A, un secondaire se comporte comme un principal du même type, ce qui est la règle attendue depuis 11.1 (« chaque entité a ses propres identifiants et topics »).
- Le seul effet visible de A (état supposé publié pour un secondaire sans état fiable) est déjà le comportement d'un principal du même type. D2 le supprime à la racine pour `FAN_*`.
- Le surcoût de A (plusieurs chemins de `http_server.py`) se couvre par des tests par chemin. La Task 0 dit combien de secondaires de production sont exposés.

### Sous-point D2 (Alexandre) — `FAN_STATE` comme canal d'état fiable d'un `switch`

- **Constat (F10)** : un trio `FAN_*` publié en `switch` est streamé mais jamais jugé fiable. Principal : `optimistic_controlled` avec un état supposé publié à chaque ordre, puis l'état réel streamé. Secondaire : même chose après A.
- **Option D2-a (recommandée)** : ajouter `FAN_STATE` à `STATE_KEYS["switch"]` dans cette story. Un trio `FAN_*` avec une info `FAN_STATE` passe en `real_state_confirmation`, principal comme secondaire, et plus aucun état supposé n'est publié pour lui. Même défaut que celui de la story (état streamé mais jugé non fiable), même correctif. Tous les consommateurs de `STATE_KEYS` sont à vérifier : discovery (`has_reliable_channel`), `reconcile_fresh_read`, liaisons d'état.
- **Option D2-b** : hors périmètre ; un trio `FAN_*` garde `optimistic_controlled`. Avec A, ses secondaires publient alors un état supposé, comme son principal.

## Critères d'acceptation (rédigés pour l'option A et D2-a ; à ajuster si Alexandre retient B ou D2-b)

1. **AC1 — Secondaire `switch` à état streamé.** Après une vraie synchro, un ordre `ON` / `OFF` sur le topic propre d'un `switch` secondaire `SWITCH_*` dont l'info d'état est streamée journalise `reason_code=real_state_confirmation`. Aucun `missing_state_topic_runtime`, aucune publication MQTT par le synchroniseur d'ordres. Forme du corpus doré : 583 (2 secondaires) et 628 (3 secondaires).
2. **AC2 — Topic propre seulement.** La décision d'un secondaire porte son `reason_details["state_topic"]` ou rien. Jamais `jeedom2ha/<eq>/state`, jamais le topic d'une autre entité, même pour un type dont `_resolve_state_topic` rend le repli (F3).
3. **AC3 — Tous les chemins.** AC1 et AC2 tiennent après : la synchro complète, « Publier » d'un équipement, « Relire Jeedom », l'exclusion par le scope puis la réinclusion, et une seconde synchro sans changement (décision stable, 24-14).
4. **AC4 — `valve` et `lock` secondaires.** Une vanne ou une serrure secondaire à état streamé donne `real_state_confirmation` ; sans état fiable, `stateless`. Jamais `optimistic_controlled`.
5. **AC5 — `FAN_*` (si D2-a).** Un trio `FAN_*`, principal ou secondaire, avec une info `FAN_STATE` donne `real_state_confirmation` ; aucun état supposé publié après un ordre.
6. **AC6 — Secondaire sans état fiable.** Un `switch` secondaire sans info d'état fiable (cas synthétique) garde `optimistic_controlled`. L'état supposé n'est publié que sur **son** topic propre, jamais sur celui du principal. Un secondaire sans topic propre ne publie rien.
7. **AC7 — Rien d'autre ne change.** Discovery, `unique_id`, topics, routage des ordres (I11), streaming d'état, verrou de thermostat (24-16), principaux et `climate` inchangés. Le golden 8.4 est inchangé, ou chaque écart est justifié.
8. **AC8 — Non-régression.** Suites Python et Node, `flake8` vertes. Garde 25.4 tenue (lignes remplacées déclarées). `desktop/js/jeedom2ha_mapping_override.js` intact (garde 24.2).
9. **AC9 — Preuve terrain (ClaudeBox, avec l'accord d'Alexandre).** Sur une prise multiple réelle choisie à la Task 0 : un ordre on puis off depuis HA sur une sortie secondaire. Le journal porte `reason_code=real_state_confirmation`, sans `missing_state_topic_runtime` ; la sortie suit l'état réel ; l'état initial est restauré.

## Tâches

- [ ] **Task 0 (ClaudeBox, lecture seule, avant `ready-for-dev`)** — relevé en production des secondaires publiés, sans aucun ordre :
  - depuis l'export de décision (24-2) : le nombre de secondaires publiés par type (`switch`, `valve`, `lock`, `light`, `cover`), avec pour chacun l'équipement, le topic propre et la clé d'état (`SWITCH_STATE`, `FAN_STATE`, `THERMOSTAT_LOCK`, `VALVE_*`, `LOCK_STATE`…) ;
  - les secondaires dont le type vient d'une surcharge (`override_applied`) ;
  - les trios `FAN_*` publiés en `switch`, principaux et secondaires (pour D2) ;
  - dans le journal du démon : le nombre de lignes `reason_code=missing_state_topic_runtime` et `reason_code=optimistic_controlled` sur des topics d'ordre `jeedom2ha/<eq>/<cmd>/set`, sur une fenêtre récente ;
  - la prise multiple à utiliser pour AC9.
- [x] **T1** — Test rouge en forme de production : vraie synchro du corpus doré, ordre sur `jeedom2ha/583/6009/set` → aujourd'hui `optimistic_controlled` et `missing_state_topic_runtime`.
- [x] **T2** — Correctif selon D1 : A (tenue de la décision secondaire dans `transport/http_server.py`, topic propre seulement, tous les chemins de F2) ou B (décision effective dans `_select_confirmation_policy`).
- [x] **T3** — Selon D2 : `FAN_STATE` dans `STATE_KEYS["switch"]`, et vérification de chaque consommateur de `STATE_KEYS`.
- [x] **T4** — Tests (ci-dessous), golden 8.4 et garde 25.4.
- [ ] **T5** — Preuve terrain AC9 (ClaudeBox, hors session cloud).

## Tests attendus (`resources/daemon/tests/unit/test_story_24_17_switch_secondaires_confirmation.py`, identifiants synthétiques)

- **Politique, forme de production** (vraie synchro `/action/sync` sur le corpus doré, synchroniseur d'état actif) : `ON` puis `OFF` sur chacun des 5 secondaires (583 : 6009, 6010 ; 628 : 5980, 5983, 6004) → `real_state_confirmation` ; aucune publication MQTT par le synchroniseur d'ordres ; aucun `missing_state_topic_runtime`.
- **Décision secondaire (A)** : après la synchro, `publication_decision_ref.state_topic` de chaque `switch` secondaire = son topic propre ; capteurs secondaires sans topic de repli `jeedom2ha/<eq>/state`.
- **Chemins** : « Publier » d'un équipement, exclusion par le scope puis réinclusion, seconde synchro sans changement → même décision, même politique.
- **Sans état fiable** : secondaire synthétique sans info d'état → `optimistic_controlled`, publication éventuelle sur son seul topic propre (jamais `jeedom2ha/<eq>/state`) ; sans synchroniseur d'état → aucune `real_state_confirmation`.
- **`valve` / `lock` secondaires** (équipements synthétiques : deux vannes ; entité gardée + serrure) → `real_state_confirmation` avec état streamé, `stateless` sans état.
- **`FAN_*` (si D2-a)** : principal et secondaire `FAN_*` → `real_state_confirmation`, aucun état supposé publié.
- **Non-régression** : principaux 583 et 628 inchangés (`real_state_confirmation`) ; `switch` mono-entité sans état fiable → `optimistic_controlled` avec publication sur `jeedom2ha/<eq>/state` (inchangé) ; tests 24-15 et 24-16 verts ; routage I11 (un secondaire refusé sous un principal publié n'est pas routé).

## Parité Homebridge

Peu pertinente pour cette story. Homebridge n'a pas de notion de « politique de confirmation » visible ; il expose chaque sortie d'une prise multiple comme un service séparé, alimenté par son info d'état. Après la correction, HA garde le même comportement que dans les cas déjà alignés : l'état affiché vient de l'info Jeedom. Cette session n'a pas pu lire la source publique de `homebridge-jeedom` (accès refusé). Si Alexandre veut la parité exacte, ClaudeBox relève dans la version installée (1.9.0, Task 0 bis de 24-15) si Homebridge met à jour la sortie dès l'ordre ou seulement à l'événement Jeedom. Ce point est facultatif et ne bloque pas D1.

## Garde-fous

- Ne changer ni la discovery, ni les `unique_id`, ni les topics, ni le routage des ordres.
- Jamais de topic de repli `jeedom2ha/<eq>/state` sur une décision secondaire.
- Aucun état supposé sur une entité dont l'état réel est streamé.
- Garder la branche 24-16 du verrou de thermostat.
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud ; aucun accès à la box ni à HA.
- Garde 25.4 : déclarer toute ligne remplacée dans `resources/daemon/`.

## Dev Notes

- Pointeurs : `transport/http_server.py` (`_resolve_state_topic` `:126-142`, `_publish_additional_sensors` `:224-298`, `_prepare_publication_bookkeeping` `:362-375`, décision d'exclusion par le scope `~:455-475`, `_reset_secondary_runtime_state` `~:605-630`, décisions recopiées `~:4894-4908`, `~:5230-5245`) ; `sync/command.py` (`_resolve_runtime_target` `:346-426`, `_select_confirmation_policy` `:1088-1142`, `_has_reliable_state` `:1144-1162`, `_publish_optimistic_state` `:1222-1260`) ; `sync/state.py` (`_iter_streamed_candidates` `:716`, `_candidate_state_topic` `:780`) ; `sync/readback.py` (`STATE_KEYS` `:45-57`) ; `mapping/switch.py` (`_SWITCH_CMD_FAMILIES` `:66`, `_map_cmd_group` `:287-319`) ; `mapping/registry.py` (`_with_valves`, `_with_locks`, `_map_structural_multi_entity`).
- Le test de 24-16 (`test_story_24_16_verrou_thermostat_confirmation.py`) montre comment monter une vraie synchro du corpus doré et un `CommandSynchronizer` avec `_execute_exec_cmd` simulé : à réutiliser.
- 24-16 est en `review` (preuve terrain AC7 restante) ; cette story ne la touche pas.

## Dev Agent Record (2026-11-13, session cloud déléguée)

Branche `story/24-17-switch-secondaires-confirmation` (depuis `origin/main` `345eb92`). Décisions appliquées : **D1 A**, **D2-a**. Task 0 et T5 laissées à ClaudeBox.

### T1 — test rouge en forme de production

Vraie synchro `/action/sync` du corpus doré, synchroniseur d'état actif, ordre `ON` sur `jeedom2ha/583/6009/set`. Avant correctif, le journal est exactement celui du constat : `command_executed` (cmd 5999), `reason_code=optimistic_controlled action=select_confirmation_policy`, puis WARNING `reason_code=missing_state_topic_runtime action=skip_optimistic_state`. Sans le correctif, 21 des 33 tests de la story échouent (vérifié en retirant le correctif puis en le réappliquant).

### T2 — correctif à la source (D1 A), `transport/http_server.py`

- Nouvelle fonction `_secondary_own_state_topic(secondary)` : rend `reason_details["state_topic"]` pour `switch`, `valve`, `lock` seulement, et seulement s'il est sous `jeedom2ha/<eq>/` ; sinon `""`. **Jamais** le repli `jeedom2ha/<eq>/state` de `_resolve_state_topic` (inchangée).
- `_publish_additional_sensors` (chemin commun de la synchro et de « Publier », via `apply_publication_decision`) pose `sec_decision.state_topic` avec ce topic propre, à côté de `active_or_alive = False`. La décision stable entre deux synchros (24-14) et « Relire Jeedom » passent par ce même chemin.
- `_reset_secondary_runtime_state` (appelé par `_sync_publication_decision_refs` : exclusion par le scope dans la synchro et dans « Publier », « Supprimer », dépublication) : la décision recopiée par `dataclasses.replace` reçoit le topic propre ; la décision neuve « jamais synchronisé » aussi, à la place du repli `_resolve_state_topic(secondary)` (seule ligne remplacée de la story).
- `sync/command.py` n'est pas modifié : la branche 24-16 (`thermostat_lock`) est gardée telle quelle. `_has_reliable_state` et `_publish_optimistic_state` lisent désormais le topic propre de la décision secondaire.

### T3 — `FAN_STATE` canal fiable du `switch` (D2-a), `sync/readback.py`

`STATE_KEYS["switch"]` gagne `FAN_STATE` en dernière position (ajout, ordre des clés antérieures inchangé). Consommateurs vérifiés :

- `has_reliable_channel` / `CommandSynchronizer._has_reliable_state` : un trio `FAN_*` (principal ou secondaire) passe en `real_state_confirmation` ; plus d'état supposé publié.
- Discovery : le payload `switch` ne lit pas `has_reliable_channel` (pas de clé `optimistic`) : inchangé. `light`, `cover`, `valve` lisent leurs propres clés : inchangés.
- `sync/state.py` `_READBACK_KEYS["switch"]` (dérivé de `STATE_KEYS`) : un trio porte `reason_details["cmd_id"]`, donc sa liaison de streaming reste l'unique liaison `cmd_id → topic propre` (inchangée). **Seul effet** : `_candidate_current_value` trouve désormais la valeur courante de `FAN_STATE`, donc l'**état initial** d'un trio `FAN_*` est publié à la synchro / au « Publier » (il ne l'était pas : la valeur restait inconnue jusqu'au premier événement Jeedom). Même comportement qu'un trio `SWITCH_*`. Aucun trio `FAN_*` dans le corpus doré.
- `_PURGEABLE_CHANNELS` ne contient pas `switch` : aucune purge nouvelle. `reconcile_fresh_read` ne lit pas `STATE_KEYS` : inchangé.

### T4 — tests, golden, gardes

`resources/daemon/tests/unit/test_story_24_17_switch_secondaires_confirmation.py` — 33 tests, identifiants synthétiques (corpus doré + équipements 17000 deux vannes, 17100 prise + serrure, 17200 trio `FAN_*` seul, 17300 trio `SWITCH_*` + trio `FAN_*`) :

- AC1 : `ON` puis `OFF` sur les 5 secondaires (583 : 6009, 6010 ; 628 : 5980, 5983, 6004) → `real_state_confirmation`, bonne commande exécutée, aucune publication MQTT par le synchroniseur d'ordres, aucun `missing_state_topic_runtime` ; état streamé sur le topic propre.
- AC2 : après synchro, toute décision secondaire `switch` / `valve` / `lock` porte son topic propre, toute autre (capteurs) n'en porte aucun, jamais `jeedom2ha/<eq>/state` ; un `light` secondaire (cas de surcharge) n'obtient jamais le repli.
- AC3 : « Publier », seconde synchro sans changement, exclusion par le scope puis réinclusion (aucun ordre routé pendant l'exclusion), « Supprimer » puis « Publier », décision recopiée → même topic, même politique.
- AC4 : vanne et serrure secondaires → `real_state_confirmation` avec synchroniseur d'état, `stateless` sans ; vanne sans info d'état → `stateless` ; jamais `optimistic_controlled`.
- AC5 : `FAN_STATE` dans `STATE_KEYS["switch"]` ; trio `FAN_*` principal et secondaire → `real_state_confirmation`, rien publié ; état initial et streaming sur le topic propre.
- AC6 : secondaire sans info d'état → `optimistic_controlled`, état supposé publié sur **son seul** topic propre ; secondaire sans topic propre → rien publié (`missing_state_topic_runtime`) ; sans synchroniseur d'état → aucune `real_state_confirmation`.
- AC7 : principaux 583 et 628 inchangés (`real_state_confirmation`), verrou de thermostat 24-16 inchangé, I11 (secondaire refusé sous un principal publié → non routé), topics et `unique_id` de discovery inchangés.

**Golden 8.4** (`expected_sync_snapshot.json`) : **inchangé** (aucun fichier de fixture modifié ; `test_story_8_4` et gardes 19-4 verts).

**Garde 25.4** : une seule ligne retirée sous `resources/daemon/` — `state_topic=_resolve_state_topic(secondary),` dans `_reset_secondary_runtime_state` — déclarée dans `REPLACED_BY_24_17` (`tests/unit/test_story_25_4_non_regression.node.test.js`, « fichier::ligne »). **Garde 24.2** : `desktop/js/jeedom2ha_mapping_override.js` non touché.

### Fichiers modifiés

- `resources/daemon/transport/http_server.py` (ajouts + 1 ligne remplacée)
- `resources/daemon/sync/readback.py` (ajout)
- `resources/daemon/tests/unit/test_story_24_17_switch_secondaires_confirmation.py` (nouveau)
- `tests/unit/test_story_25_4_non_regression.node.test.js` (déclaration 25.4)
- cette story, `sprint-status.yaml`

### Résultats

- `python3 -m pytest` : 3279 passés, 1 ignoré, 9 désélectionnés (charge).
- `flake8 resources/daemon tests` : vert.
- `node --test tests/unit/*.node.test.js` : 1211 passés, 3 ignorés, 0 échec.

### Points d'attention pour la preuve terrain (T5)

- Pour un `switch` secondaire **sans** synchroniseur d'état actif (démon sans clé API cœur), la politique reste `optimistic_controlled` et un état supposé est désormais publié sur le topic propre du secondaire, comme pour un principal (attendu par D1 A).
- Trio `FAN_*` en production (Task 0) : son état initial est désormais publié à la synchro.

## Journal

- 2026-11-13 — Story rédigée (session cloud déléguée, documentaire, `180b3ab`) : 5 `switch` secondaires concernés dans le corpus doré (583 : 2, 628 : 3) ; types secondaires actionnables relevés dans le code (`switch` `SWITCH_*` / `FAN_*`, verrou de thermostat, `valve`, `lock` ; `light` / `cover` seulement par surcharge) ; effet HA : aucun changement d'affichage pour un état streamé, la politique et le WARNING `missing_state_topic_runtime` étaient faux ; D1 (A à la source, recommandée / B dans la politique) et D2 (`FAN_STATE` fiable) à Alexandre ; Task 0 ClaudeBox en lecture seule.
- 2026-11-13 — Décisions d'Alexandre 12:01 : D1 A, D2 oui (D2-a) ; story passée en ready-for-dev.
- 2026-11-13 — Dev-story (session cloud déléguée, TDD, depuis `345eb92`) : D1 A (topic propre posé sur les décisions secondaires dans `_publish_additional_sensors` et `_reset_secondary_runtime_state`, jamais le repli `jeedom2ha/<eq>/state`), D2-a (`FAN_STATE` dans `STATE_KEYS["switch"]`) ; 33 tests ; golden 8.4 inchangé ; garde 25.4 : 1 ligne remplacée déclarée ; statut review, Task 0 et T5 à ClaudeBox.
