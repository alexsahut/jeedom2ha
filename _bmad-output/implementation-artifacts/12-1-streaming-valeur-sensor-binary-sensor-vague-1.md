# Story 12.1: Restitution d'état runtime — streaming des valeurs sensor / binary_sensor (vague 1)

Status: ready-for-dev

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

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.`

- [ ] Task 1 — Décision d'architecture du canal Jeedom → daemon (AC: 1, 3, 7)
  - [ ] Trancher le mécanisme par lequel un changement de valeur Jeedom atteint le daemon. Trois options identifiées (voir Dev Notes §Canal inbound) :
    - **Option A (recommandée)** : listener Jeedom `cmd::event` / `#listener#` côté plugin → envoi au daemon (via `jeedomdaemon` `send_to_daemon` → `on_message()` du daemon `main.py:169`), puis publication MQTT.
    - **Option B** : cron Jeedom (`jeedom2ha.class.php`) qui pousse les deltas de valeur vers le daemon par HTTP.
    - **Option C** : polling daemon-initié.
  - [ ] Documenter la décision et son périmètre minimal pour la vague 1 (sensor/binary_sensor info) directement dans la story.
  - [ ] Garder le périmètre PHP minimal et borné ; ne pas réécrire le plugin.

- [ ] Task 2 — Implémenter `StateSynchronizer` (daemon) (AC: 1, 2, 3, 5, 6, 7, 8)
  - [ ] Créer `resources/daemon/sync/state.py` avec une classe `StateSynchronizer` calquée structurellement sur `CommandSynchronizer` (`sync/command.py`).
  - [ ] Interface attendue par le code existant : `is_active` (property ou callable), cohérente avec `CommandSynchronizer._is_state_sync_active()` (`sync/command.py:374-399`).
  - [ ] Résoudre, pour un `(eq_id, cmd_id, valeur)` entrant, le `state_topic` cible **depuis le registre de publications** `app["publications"]` (ne jamais reconstruire un topic à la main) : mono-entité → `jeedom2ha/{eq}/state` ; multi-sensor → `jeedom2ha/{eq}/{cmd}/state`.
  - [ ] Publier via `MqttBridge.publish_message(state_topic, payload, qos=1, retain=True)` (`transport/mqtt_client.py:315`).
  - [ ] Traduire la valeur binaire en `payload_on`/`payload_off` cohérents avec le payload binary_sensor (`discovery/publisher.py` ~ligne 532).
  - [ ] Borne stricte vague 1 : ne traiter que les entités dont le `ha_entity_type ∈ {sensor, binary_sensor}` dans `app["publications"]`. Ignorer le reste.

- [ ] Task 3 — Câbler le canal inbound et l'instanciation (AC: 1, 3, 8)
  - [ ] Instancier `StateSynchronizer` dans `main.py` (`on_start`) et l'exposer dans `self._app["state_synchronizer"]` (cf. `CommandSynchronizer` à `main.py:139-145`).
  - [ ] Implémenter le routage des messages de valeur entrants : selon l'option Task 1, soit via `Jeedom2haDaemon.on_message()` (`main.py:169`), soit via un handler dédié, vers `StateSynchronizer.handle_state_message(...)`.
  - [ ] Côté PHP (option retenue), brancher l'émission de valeur minimale (listener ou cron) — périmètre borné, sans toucher au pipeline de projection.

- [ ] Task 4 — État initial (snapshot) à la publication discovery (AC: 2)
  - [ ] Après publication discovery d'une entité vague 1, publier l'état courant connu de Jeedom sur son `state_topic` lorsqu'il est disponible (sinon laisser `unknown`, sans inventer de valeur).
  - [ ] Vérifier l'ordre : discovery publié AVANT le premier message d'état (sinon HA ignore l'état).

- [ ] Task 5 — Tests et non-régression (AC: 4, 6, 7, 9)
  - [ ] Remplacer/compléter les fakes `_FakeStateSynchronizer` (`tests/unit/test_command_sync.py:19`, `tests/integration/test_command_sync_coexistence.py:14`) par des tests du vrai `StateSynchronizer` (interface `is_active`, résolution de topic, publication, borne vague 1).
  - [ ] Tester la traduction binary_sensor (on/off) et le cas multi-sensor eq553 (`jeedom2ha/553/<cmd>/state`).
  - [ ] Tester que les types actionnables ne sont pas alimentés par cette story (AC#4) et que `CommandSynchronizer` reste inchangé sur l'optimiste hors vague 1.
  - [ ] Lancer la suite pytest complète (`python3 -m pytest resources/daemon/tests -q`).

- [ ] Task 6 — Gate terrain (AC: 10)
  - [ ] `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon` → `Deploy complete.`
  - [ ] Provoquer/attendre un changement de valeur eq553 et vérifier sur le broker (`mosquitto_sub -h 127.0.0.1 -p 1883 ... -t 'jeedom2ha/553/#'`) que les `state_topic` reçoivent des valeurs ; confirmer dans HA que les capteurs ne sont plus `unknown`.
  - [ ] Documenter les preuves dans la story (topics, valeurs, capture HA).

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

Claude Opus 4.8 (create-story)

### Debug Log References

### Completion Notes List

- Create-story completed : story 12.1 matérialisée avec le map complet du chemin de valeur (StateSynchronizer miroir de CommandSynchronizer), la double résolution de state_topic (mono + multi-sensor eq553), et la décision d'architecture du canal inbound Jeedom → daemon laissée en Task 1 (Option A recommandée).

### File List

- `_bmad-output/implementation-artifacts/12-1-streaming-valeur-sensor-binary-sensor-vague-1.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-06-18 — Story 12.1 créée via workflow create-story (suite au Sprint Change Proposal 2026-06-18, ouverture de pe-epic-12).
