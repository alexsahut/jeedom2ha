# Story 12.1: Restitution d'état runtime — streaming des valeurs sensor / binary_sensor (vague 1)

Status: done (daemon + listener PHP implémentés et testés ; gate terrain PASSÉ sur domobox le 2026-06-18 — eq553 « Tension réseau » = 238.4 V live, plus unknown ; 860 tests verts ; mergée main via PR #123. Réaligné done par correct-course 2026-06-19.)

## Story

En tant qu'utilisateur familial de Home Assistant,
je veux que mes entités publiées (capteurs MSunPV eq553 « tension réseau » et autres `sensor`/`binary_sensor`) affichent leurs valeurs réelles au lieu de « inconnu »,
afin de pouvoir construire un dashboard énergie/maison exploitable, alimenté en temps réel par Jeedom.

## Acceptance Criteria

1. **Chemin de valeur Jeedom → HA établi.** Lorsqu'une commande info Jeedom d'une entité publiée change de valeur, cette valeur est publiée sur le `state_topic` MQTT déclaré lors de la discovery. Une entité `sensor`/`binary_sensor` publiée n'est plus en état `unknown` une fois sa commande info alimentée.
2. **État initial à la publication.** À la (re)publication discovery d'une entité de la vague 1, le système publie l'état courant connu de Jeedom (snapshot initial), sans attendre le prochain changement, lorsque la valeur est disponible.
3. **Mises à jour event-driven.** Les changements ultérieurs de valeur côté Jeedom sont propagés au `state_topic` sans dépendre d'un resync complet (`/action/sync`).
4. **Vague 1 strictement bornée.** Seuls les types `sensor` et `binary_sensor` sont alimentés par cette story. Les domaines actionnables (`switch`, `light`, `cover`, `climate`, `alarm_control_panel`) ne sont PAS ouverts ici (le comportement optimiste existant de `CommandSynchronizer` reste inchangé).
5. **Cohérence state ⊆ discovery.** Aucune valeur n'est publiée sur un `state_topic` dont l'entité n'a pas été publiée en discovery. Aucun topic d'état orphelin créé. Le topic d'état utilisé est exactement celui du payload discovery (mono : `jeedom2ha/{eq}/state` ; multi-sensor eq553 : `jeedom2ha/{eq}/{cmd}/state`).
6. **`binary_sensor` : payload on/off honnête.** La valeur Jeedom binaire est traduite en `payload_on`/`payload_off` cohérents avec le payload discovery du binary_sensor (pas d'inversion, pas de valeur inventée).
7. **Pas de source de vérité concurrente (NFR6/NFR13).** Toute valeur publiée provient d'une commande info Jeedom ; le daemon ne calcule ni ne mémorise d'état métier autoritatif. Event-driven uniquement.
8. **Activation de `state_synchronizer` cohérente avec `CommandSynchronizer`.** Le `CommandSynchronizer` consulte `app["state_synchronizer"]` (`is_active`) pour décider confirmation réelle vs optimiste : une fois le `StateSynchronizer` réel en place, `_is_state_sync_active()` reflète l'état réel (et non plus un fake de test).
9. **Non-régression.** La discovery existante, le chemin HA → Jeedom (`CommandSynchronizer`), les compteurs de sync et le diagnostic restent inchangés sur les cas hors vague 1. Suite pytest complète verte.
10. **Gate terrain.** Sur box réelle DEV/TEST `192.168.1.21`, après deploy/restart/sync, les capteurs eq553 (« tension réseau ») affichent une valeur réelle dans HA (ou sur le broker via `mosquitto_sub`), et ne sont plus en `unknown` pour les commandes info alimentées.

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run OK (`./scripts/deploy-to-box.sh --dry-run`) : rsync simulé, `state.py` + `http_server.py` inclus, aucun transfert.
  - [x] Cycle complet `--cleanup-discovery --restart-daemon` → `Deploy complete.` (2026-06-18, box domobox 192.168.1.21).

- [x] Task 1 — Décision d'architecture du canal Jeedom → daemon (AC: 1, 3, 7) — **TRANCHÉE** (voir §Décision Task 1 ci-dessous)
  - [x] Mécanisme retenu : **Option A raffinée** — listener Jeedom `#listener#` event-driven, MAIS transport via le canal HTTP éprouvé `callDaemon()` → nouvelle route daemon `POST /action/state_update`, et NON via le socket `jeedomdaemon`/`on_message` (qui est un stub non câblé côté plugin : aucun `sendToDaemon` dans `core/`).
  - [x] Décision et périmètre minimal documentés dans la story (§Décision Task 1).
  - [x] Périmètre PHP gardé minimal et borné ; pipeline de projection non touché.

- [x] Task 2 — Implémenter `StateSynchronizer` (daemon) (AC: 1, 2, 3, 5, 6, 7, 8)
  - [x] Créé `resources/daemon/sync/state.py` (`StateSynchronizer`), miroir structurel de `CommandSynchronizer`.
  - [x] Expose `is_active` (property) — retourne **False** en vague 1 : on ne stream PAS l'état actionnable, donc `CommandSynchronizer` garde son chemin optimiste (AC#4/#9).
  - [x] Résout `(eq_id, cmd_id)` → `state_topic` **depuis `app["publications"]`** (jamais reconstruit) : mono → `decision.state_topic` ; multi-sensor → `reason_details["state_topic"]` via `reason_details["cmd_id"]` (`mapping/sensor.py:164-167`).
  - [x] Publie via `MqttBridge.publish_message(topic, payload, qos=1, retain=True)`.
  - [x] Traduction binaire : `1/true/on/open` → `ON`, sinon `OFF` (défauts HA, payload discovery non surchargé).
  - [x] Borne stricte vague 1 : `ha_entity_type ∈ {sensor, binary_sensor}` uniquement.

- [x] Task 3 — Câbler le canal inbound et l'instanciation (AC: 1, 3, 8) — **complète (daemon + PHP, R1 ciblé)**
  - [x] `StateSynchronizer` instancié dans `main.py` (`on_start`) et exposé dans `app["state_synchronizer"]`.
  - [x] Routage inbound : nouvelle route `POST /action/state_update` (`transport/http_server.py`) → `StateSynchronizer.handle_state_message(...)`. (Décision Task 1 : HTTP, pas `on_message`.)
  - [x] **R1 (ciblé) — source autoritative daemon** : `StateSynchronizer.list_state_targets()` + route `GET /system/state_listeners` exposent l'ensemble exact des `(eq_id, cmd_id)` vague-1 publiés (mapping single-sourcé dans le daemon ; `published_scope` est eq-level, ne porte pas les cmd_id).
  - [x] **Listener PHP** : `jeedom2ha::syncStateListeners()` purge puis (ré)enregistre un `listener` Jeedom par cmd publiée (lu depuis `/system/state_listeners`), callback `jeedom2ha::stateListener($options)` → `callDaemon('/action/state_update', {eq_id, cmd_id, value}, 'POST')`. Branché après chaque sync OK (`bootstrapRuntimeAfterDaemonStart` + scan manuel `ajax scanTopology`).
  - [x] Sous-décision « registration » R1 vs R2 : **R1 tranchée par l'agent architecte (Winston) le 2026-06-18** — écouter exactement le périmètre publié (cf. §Décision Task 1).

- [x] Task 4 — État initial (snapshot) à la publication discovery (AC: 2)
  - [x] `StateSynchronizer.publish_initial_states(decision)` publie `JeedomCmd.current_value` sur le `state_topic` des entités vague 1, gated sur `publication_decision_ref.discovery_published` (AC#5).
  - [x] Appelé dans `_handle_action_sync` APRÈS la publication discovery (primaire + secondaires), donc ordre discovery→état respecté.

- [x] Task 5 — Tests et non-régression (AC: 4, 6, 7, 9)
  - [x] Tests du vrai `StateSynchronizer` ajoutés (`tests/unit/test_story_12_1_state_streaming.py`, 19 tests) : interface `is_active`, résolution topic mono/multi, publication, borne vague 1, snapshot, state⊆discovery. Fakes `_FakeStateSynchronizer` conservés (couverture des branches `CommandSynchronizer` en isolation) + test du contrat sur l'objet réel.
  - [x] Traduction binary_sensor (on/off) et multi-sensor eq553 (`jeedom2ha/553/<cmd>/state`) testés.
  - [x] Test que les actionnables ne sont pas alimentés (AC#4) + `CommandSynchronizer._is_state_sync_active(real)` == False (optimiste préservé).
  - [x] Route HTTP testée (`tests/unit/test_story_12_1_state_update_route.py`, 7 tests : publish, wrapper/direct, auth 401, champs requis 400, entité inconnue, + `/system/state_listeners` liste & auth).
  - [x] `list_state_targets()` testé (mono/multi/binary inclus, light exclu, non-publié exclu).
  - [x] Suite pytest complète : **860 passed** (était 831 ; +29).

- [x] Task 6 — Gate terrain (AC: 10) — **PASSÉ le 2026-06-18 (box domobox 192.168.1.21)**
  - [x] `--cleanup-discovery --restart-daemon` → `Deploy complete.` ; daemon up, MQTT `connected`.
  - [x] `/system/state_listeners` renvoie 88 cibles vague-1 (dont eq553 multi-sensor par-cmd) ; **88 listeners PHP `stateListener` enregistrés** en base.
  - [x] Streaming live prouvé end-to-end : daemon log `POST /action/state_update` 200 (100 %) → `[SYNC-STATE] eq_id=553 cmd_id=5141 state_published jeedom2ha/553/5141/state` ; **37 `state_published`** post-deploy.
  - [x] **eq553 « Tension réseau » (cmd 5141) = 238.4 V** en retained MQTT (`jeedom2ha/553/5141/state`) — n'est plus `unknown`. Autres eq streamant : 244, 627, 385, 553(×N).
  - [x] Aucune régression observée : erreurs `listener_execution` (« Too many connections ») **antérieures au deploy** (mtime 03:36 vs deploy 12:02), 1 seul `jeeListener.php` actif (pas de tempête).
  - Note hardening (suivi possible, hors scope vague 1) : les listeners tournent en **background** (défaut Jeedom = un process `jeeListener.php` par changement de cmd, re-bootstrap core). Sous burst MSunPV × 88 capteurs c'est de la charge récurrente ; option `setOption('background', false)` (foreground) à évaluer si la charge devient un problème (trade-off : latence inline sur l'event vs coût process). Non appliqué : l'impl background fonctionne et la box est saine.

## Décision Task 1 (tranchée 2026-06-18)

**Mécanisme retenu : Option A raffinée — listener event-driven, transport HTTP `callDaemon` (PAS le socket `on_message`).**

Constat de code qui motive le raffinement :
- Le socket `jeedomdaemon` (`on_message`, `main.py:169`) est un **stub** et n'est **câblé nulle part** côté plugin : aucune occurrence de `sendToDaemon`/`send_to_daemon` dans `core/`. L'utiliser imposerait d'introduire un mécanisme socket PHP→daemon inexistant.
- Le canal PHP→daemon **réellement utilisé, authentifié et testé** est HTTP : `jeedom2ha::callDaemon()` (`core/class/jeedom2ha.class.php:403`, header `X-Local-Secret`) → routes `/action/*` du serveur aiohttp (`transport/http_server.py`).

Donc, à intention identique (event-driven, périmètre PHP minimal, pas de polling), le seam concret le plus sûr et cohérent est HTTP :

```
Jeedom #listener# (info cmd d'un eqLogic publié)
  → callDaemon('/action/state_update', {eq_id, cmd_id, value}, 'POST')
    → _handle_action_state_update (auth X-Local-Secret, unwrap {payload})
      → StateSynchronizer.handle_state_message(eq_id, cmd_id, value)
        → résolution state_topic depuis app["publications"]  (state ⊆ discovery)
          → MqttBridge.publish_message(state_topic, payload, qos=1, retain=True)
```

Périmètre vague 1 : `sensor`/`binary_sensor` info uniquement. Le daemon est **autoritatif** sur le filtrage (une cmd non publiée → `handle_state_message` renvoie False, rien publié), ce qui permet de garder le PHP « bête ».

**Sous-décision PHP « registration » — TRANCHÉE R1 (ciblé) par l'agent architecte (Winston), 2026-06-18.**

Options évaluées :
- **(R1, retenue)** Listener **ciblé** piloté par le périmètre publié : un `listener` Jeedom par cmd info effectivement publiée.
- **(R2, rejetée)** Listener **large** + filtrage 100% côté daemon : flood le daemon d'un POST par changement de cmd de *toute* l'install (anti-pattern, surtout MSunPV haute fréquence) ; le filtrage arrive après le saut réseau.

Verdict : R1 réutilise un contrat existant et garde le mapping single-sourcé dans le daemon. Comme `published_scope` est **eq-level** (pas de cmd_id), R1 s'appuie sur un nouvel endpoint dédié `GET /system/state_listeners` (issu de `StateSynchronizer.list_state_targets()`) qui renvoie l'ensemble exact des `(eq_id, cmd_id, ha_type, state_topic)` vague-1 publiés. PHP `syncStateListeners()` purge puis recrée les listeners depuis cette liste après chaque sync OK ; `state ⊆ discovery` est ainsi garanti **à la source**.

Le code daemon (route `/action/state_update`, auth, unwrap wrapper `callDaemon`, contrat `{status, published}`, filtrage autoritatif) reste en place et testé.

## Dev Notes

### Source produit et scope

- Foyer produit : `pe-epic-12` (Restitution d'état runtime). Définition : `_bmad-output/planning-artifacts/epics-projection-engine.md` (## Epic 12).
- Exigences : PRD `Feature 9` / `FR46-FR50` + `NFR13` (`_bmad-output/planning-artifacts/prd.md`).
- Origine : `sprint-change-proposal-2026-06-18.md` (régression systémique « entités publiées mais en état unknown »).
- Reprise de l'intention legacy `FR16 Retour d'état` / `FR17 Synchro temps réel` (`epics.md`), jamais re-planifiée depuis.
- Borne vague 1 : `sensor` + `binary_sensor` UNIQUEMENT. Domaines actionnables = vagues ultérieures gouvernées.

### Analyse architecture (chemin de valeur — N'EXISTE PAS aujourd'hui)

Le streaming runtime est une capacité **parallèle** au pipeline de projection à 5 étapes : il consomme les `state_topic` déjà déclarés en étape 5 (discovery), il ne réordonne ni ne revalide les étapes. Aujourd'hui : discovery publiée, mais **0 message sur les `state_topic`** → HA affiche `unknown`.

**Mécanisme miroir existant (qui fonctionne)** : `CommandSynchronizer` (HA → Jeedom). À calquer pour le sens inverse (Jeedom → HA).

- `resources/daemon/sync/command.py` — `CommandSynchronizer` (classe ligne 42). Construit avec `(app, mqtt_bridge, jeedom_api_endpoint, jeedom_core_apikey, request_timeout)`. Entrée MQTT : `handle_command_message(topic, payload)` (ligne 67). Résolution cible via `app["publications"]` (`_resolve_runtime_target`, ligne 170). Publication optimiste sur `state_topic` : `_publish_optimistic_state` (ligne 402). **Consulte déjà `app["state_synchronizer"]`** : `_has_reliable_state` (ligne 349), `_is_state_sync_active` (lignes 374-399) — c'est le contrat d'interface que le vrai `StateSynchronizer` doit honorer (`is_active`).

### Résolution du `state_topic` — DEUX schémas à supporter

- Actuateurs / mono-entité : `_resolve_state_topic(mapping)` → `jeedom2ha/{eq_id}/state` (`transport/http_server.py:76-82`). Assigné à `decision.state_topic` (`http_server.py:319`).
- **Multi-sensor (eq553, vague 1 cible)** : `state_topic = jeedom2ha/{eq}/{cmd}/state` (per-commande), voir Story 11.1 (`unique_id=jeedom2ha_eq_553_cmd_<cmd>`, `object_id=jeedom2ha_553_<cmd>`). **Ne PAS reconstruire le topic à la main** : le lire depuis le registre `app["publications"]` (mapping/publication par `eq_id`, secondaires inclus). C'est la garantie AC#5 (state ⊆ discovery).
- Payloads discovery et leurs `state_topic` : `discovery/publisher.py` (sensor ~L504, binary_sensor ~L532).

### MQTT plumbing

- `resources/daemon/transport/mqtt_client.py` — `MqttBridge` (ligne 37), paho-mqtt. Publication : `publish_message(topic, payload, qos=1, retain=False)` (ligne 315) — **utiliser `retain=True`** pour l'état (HA doit retrouver la dernière valeur au redémarrage). Souscriptions actuelles = topics commande (`jeedom2ha/+/set`, `.../brightness/set`, `.../position/set`, `.../cmd`) à L27-34. Handler commande enregistré via `set_command_handler` (L331). Le sens Jeedom → HA est un **publish** sortant du daemon, pas une nouvelle souscription MQTT.

### Canal inbound Jeedom → daemon (DÉCISION CENTRALE — Task 1)

C'est le point dur : aujourd'hui aucun canal ne porte les changements de valeur Jeedom jusqu'au daemon.

- `core/php/jeedom2ha.php` (L1-37) = stub HTTP 200. Son commentaire annonce explicitement que la logique daemon→Jeedom / state updates est « out of scope for Story 1.1, later story » — **c'est cette story**.
- `core/class/jeedom2ha.class.php` : `callDaemon()` (L403-456) pousse déjà des actions vers le daemon par HTTP POST avec header `X-Local-Secret`. Pas de listener `cmd::event` ni de cron de valeur aujourd'hui.
- Daemon : `Jeedom2haDaemon.on_message(message: list)` (`main.py:169-174`) est un **stub** prévu pour recevoir les messages de Jeedom via `jeedomdaemon` (`BaseDaemon`, `main.py:87-101`). C'est le seam naturel pour le sens Jeedom → daemon.
- **Recommandation (Option A)** : côté Jeedom, un listener sur les commandes info des eqLogics publiés émet la valeur vers le daemon (canal `jeedomdaemon` → `on_message`), le daemon route vers `StateSynchronizer` qui publie sur le `state_topic`. Minimal, event-driven, pas de polling. Trancher en Task 1 et documenter.

### Fakes de test à remplacer

- `tests/unit/test_command_sync.py:19` et `tests/integration/test_command_sync_coexistence.py:14` : `_FakeStateSynchronizer(active: bool)` avec attribut `.is_active`. Le vrai `StateSynchronizer` doit exposer `is_active` (property ou callable) compatible avec `CommandSynchronizer._is_state_sync_active()`.

### Dev Agent Guardrails

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.
- Référence complète modes + cycle validé terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`.

#### Garde-fous implémentation

- Borne vague 1 stricte : ne PAS alimenter `switch`/`light`/`cover`/`climate`/`alarm_control_panel`. Ne pas modifier le comportement optimiste de `CommandSynchronizer` hors activation `is_active`.
- Ne JAMAIS reconstruire un `state_topic` à la main : le lire depuis `app["publications"]` (cohérence state ⊆ discovery, AC#5).
- Event-driven uniquement : pas de cache d'état métier autoritatif dans le daemon (NFR6/NFR13). La valeur vient toujours d'une commande info Jeedom.
- `retain=True` pour l'état ; publier la discovery AVANT le premier état.
- binary_sensor : `payload_on`/`payload_off` doivent matcher le payload discovery (pas d'inversion).
- Périmètre PHP minimal et borné : ne pas réécrire le plugin ni toucher le pipeline de projection.

### Project Structure Notes

- Story branch/worktree dédié : `story/pe-12.1-state-streaming`.
- Nouveau module attendu : `resources/daemon/sync/state.py` (`StateSynchronizer`), miroir de `sync/command.py`.
- `sprint-status.yaml` : `pe-epic-12: in-progress` (1ère story de l'epic) et `12-1-...: ready-for-dev` à la création.
- Les `_bmad-output/planning-artifacts/*` ne sont pas à modifier par cette story (sauf correction documentaire explicite).

### References

- `_bmad-output/planning-artifacts/prd.md` — Feature 9, FR46-FR50, NFR13.
- `_bmad-output/planning-artifacts/epics-projection-engine.md` — ## Epic 12 + Gates epic-level pe-epic-12.
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-18.md` — origine et périmètre.
- `_bmad-output/planning-artifacts/backlog-icebox.md` §3.1 — inventaire eq553.
- `resources/daemon/sync/command.py` — `CommandSynchronizer` (template structurel + contrat `is_active`).
- `resources/daemon/transport/mqtt_client.py:315` — `MqttBridge.publish_message`.
- `resources/daemon/transport/http_server.py:76` — `_resolve_state_topic` (schéma mono-entité).
- `resources/daemon/discovery/publisher.py` — payloads sensor / binary_sensor et leurs `state_topic`.
- `resources/daemon/main.py:169` — `on_message` (seam canal Jeedom → daemon).
- `core/php/jeedom2ha.php`, `core/class/jeedom2ha.class.php:403` — `callDaemon` / canal PHP.
- `resources/daemon/tests/unit/test_command_sync.py:19` — fake `StateSynchronizer` à remplacer.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (create-story + dev-story daemon-side)

### Debug Log References

- `pytest resources/daemon/tests/unit -q` → **860 passed** (831 baseline + 29 nouveaux : 22 `test_story_12_1_state_streaming.py` + 7 `test_story_12_1_state_update_route.py`).

### Completion Notes List

- Create-story completed : story 12.1 matérialisée avec le map complet du chemin de valeur (StateSynchronizer miroir de CommandSynchronizer), la double résolution de state_topic (mono + multi-sensor eq553), et la décision d'architecture du canal inbound Jeedom → daemon laissée en Task 1 (Option A recommandée).
- Task 1 TRANCHÉE : canal inbound = route HTTP `POST /action/state_update` via `callDaemon` (canal éprouvé), pas le socket `on_message` (jamais alimenté côté PHP — aucun `sendToDaemon`/listener existant). Voir section « Décision Task 1 ».
- Tasks 2/4/5 livrées : `StateSynchronizer` (`sync/state.py`) + snapshot initial (`publish_initial_states`, AC#2) + suite de tests.
- `is_active` reste **False** en vague 1 → préserve le chemin optimiste de `CommandSynchronizer` (AC#4/#9) ; aucun domaine actionnable streamé.
- Task 3 COMPLÈTE (daemon + PHP). Sous-décision listener R1 vs R2 **tranchée R1 (ciblé) par l'agent architecte (Winston)** : `published_scope` est eq-level → ajout de `StateSynchronizer.list_state_targets()` + route `GET /system/state_listeners` pour exposer l'ensemble exact des `(eq_id, cmd_id)` vague-1 publiés (mapping autoritatif single-sourcé daemon). PHP : `syncStateListeners()` (re)enregistre un listener Jeedom par cmd publiée + callback `stateListener()` → `callDaemon('/action/state_update')`, branché après chaque sync OK.
- State ⊆ discovery (AC#5) : topics lus depuis `app["publications"]`, jamais reconstruits ; listeners PHP enregistrés sur exactement le périmètre publié.
- Gate terrain PASSÉ (domobox, 2026-06-18) : 88 listeners enregistrés, `POST /action/state_update` 200 à 100 %, eq553 « Tension réseau » (cmd 5141) = 238.4 V en MQTT (plus `unknown`). Erreurs `Too many connections` du log listener antérieures au deploy (sans lien). Suivi possible : listeners en foreground si la charge background devient un souci (hors scope vague 1).

### File List

- `_bmad-output/implementation-artifacts/12-1-streaming-valeur-sensor-binary-sensor-vague-1.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/sync/state.py` (nouveau — `StateSynchronizer` + `list_state_targets`)
- `resources/daemon/tests/unit/test_story_12_1_state_streaming.py` (nouveau — 22 tests)
- `resources/daemon/tests/unit/test_story_12_1_state_update_route.py` (nouveau — 7 tests)
- `resources/daemon/transport/http_server.py` (modifié — routes `/action/state_update` + `/system/state_listeners`, normalisation wrapper, hook snapshot)
- `resources/daemon/main.py` (modifié — instanciation/enregistrement `StateSynchronizer`)
- `core/class/jeedom2ha.class.php` (modifié — `syncStateListeners()` + `stateListener()` + hook post-bootstrap)
- `core/ajax/jeedom2ha.ajax.php` (modifié — réenregistrement des listeners après scan manuel)

### Change Log

- 2026-06-18 — Story 12.1 créée via workflow create-story (suite au Sprint Change Proposal 2026-06-18, ouverture de pe-epic-12).
- 2026-06-18 — Implémentation daemon-side : `StateSynchronizer` + route HTTP `/action/state_update` + snapshot initial + tests. Task 1 tranchée (canal HTTP).
- 2026-06-18 — Listener PHP (R1 ciblé, verdict architecte) : `list_state_targets()` + route `/system/state_listeners` + `syncStateListeners()`/`stateListener()` PHP + hooks post-sync. Suite 860 passed.
- 2026-06-18 — Gate terrain PASSÉ sur domobox : eq553 « Tension réseau » = 238.4 V dans HA (streaming live prouvé). Story → ready-for-review.
