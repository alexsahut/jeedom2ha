# Story 12.2: Restitution d'état runtime — streaming des valeurs switch / button (vague 2)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur familial de Home Assistant,
je veux que mes entités actionnables publiées (`switch`, notamment `switch.jeedom2ha_554` du chauffe-eau eq554 et les sorties On/Off de l'IQ EV eq583) affichent leur état réel de marche au lieu de « inconnu »,
afin de connaître l'état réel de mes équipements pilotables et de construire des automatisations fiables, sans dépendre uniquement de l'optimisme de la commande sortante.

## Acceptance Criteria

1. **Streaming d'état switch.** Lorsqu'une commande info d'état (readback) d'un `switch` publié change de valeur côté Jeedom, cette valeur est publiée sur le `state_topic` MQTT déclaré à la discovery (`jeedom2ha/{eq}/state`). Un `switch` publié dont la commande de readback est alimentée n'est plus en `unknown`.
2. **État initial switch à la publication.** À la (re)publication discovery d'un `switch` de la vague 2, le système publie l'état courant connu de Jeedom (snapshot initial), sans attendre le prochain changement, lorsque la valeur est disponible (réutilise `publish_initial_states`).
3. **Mises à jour event-driven.** Les changements ultérieurs d'état sont propagés au `state_topic` sans dépendre d'un resync complet (`/action/sync`), via le canal inbound HTTP `POST /action/state_update` établi en 12.1.
4. **Traduction ON/OFF honnête.** La valeur Jeedom de readback du `switch` est traduite en `ON`/`OFF` cohérents avec le payload discovery du switch (`payload_on=ON` / `payload_off=OFF`, `discovery/publisher.py:_build_switch_payload`) — pas d'inversion, pas de valeur inventée.
5. **`button` = sans état (stateless), documenté.** Le type `button` est command-only : son payload discovery ne déclare **aucun** `state_topic` (`discovery/publisher.py:616`, `_TYPES_WITHOUT_STATE_TOPIC = {"button"}` dans `http_server.py:73`). HA ne présente jamais un `button` en `unknown` (entité de déclenchement, pas d'état persistant). La vague 2 ne publie donc **aucun** état pour `button` ; aucun `state_topic` orphelin n'est créé. Ce comportement est explicite et testé (honnêteté NFR — pas de faux readback).
6. **Activation scope-aware de `is_active` (décision architecte — §Décision Task 1).** Une fois la vague 2 en place, `StateSynchronizer` fournit un état réel fiable pour `switch`. Le contrat consulté par `CommandSynchronizer._is_state_sync_active()` / `_has_reliable_state()` devient **borné au périmètre réellement streamé** : `switch` bascule vers la confirmation réelle (`real_state_confirmation`) ; `light` et `cover` ne sont **pas** considérés comme fiables (ils ne sont pas streamés en vague 2) et conservent leur comportement optimiste actuel — pas de régression de gel.
7. **Cohérence state ⊆ discovery.** Aucune valeur publiée sur un `state_topic` dont l'entité `switch` n'a pas été publiée en discovery. Le `state_topic` est lu depuis `app["publications"]`, jamais reconstruit (AC repris de 12.1). `list_state_targets()` n'expose que des `switch` dont la discovery a réussi → les listeners PHP s'enregistrent automatiquement sur exactement ce périmètre (aucune modif PHP nécessaire).
8. **Vague 2 strictement bornée.** Seuls `switch` (état réel) et `button` (no-op documenté) sont concernés. `light`, `cover`, `climate`, `alarm_control_panel` ne sont **pas** ouverts ici.
9. **Pas de source de vérité concurrente (NFR6/NFR13).** Toute valeur publiée provient d'une commande info Jeedom ; le daemon ne calcule ni ne mémorise d'état métier autoritatif. Event-driven uniquement.
10. **Non-régression.** Le streaming sensor/binary_sensor (12.1), la discovery, le chemin HA → Jeedom (`CommandSynchronizer`) pour light/cover/climate, les compteurs de sync et le diagnostic restent inchangés hors `switch`. Suite pytest complète verte.
11. **Gate terrain.** Sur box réelle DEV/TEST `192.168.1.21`, après deploy/restart/sync : un `switch` publié alimenté par une commande info de readback (cible : `switch.jeedom2ha_554` eq554 si disponible, sinon un switch de l'install ayant `ENERGY_STATE`) affiche `on`/`off` réel dans HA (ou sur le broker via `mosquitto_sub`), et n'est plus en `unknown`. Aucune régression observée sur les capteurs eq553 (vague 1) ni sur le pilotage light/cover.

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) — **EXÉCUTÉ le 2026-06-18 sur box réelle `192.168.1.21` (`domobox`).**
  - [x] Dry-run : `./scripts/deploy-to-box.sh --dry-run` → `Simulation complete`, seuls `resources/daemon/sync/command.py` et `state.py` transférés (delta vague 2).
  - [x] Mode retenu : cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`.
  - [x] Script terminé avec `Deploy complete.` ; SSH OK, sudo OK, daemon redémarré.

- [x] Task 1 — Décision d'architecture du contrat `is_active` scope-aware + traitement `button` (AC: 5, 6) — **voir §Décision Task 1 (tranchée par l'agent architecte)**
  - [x] Trancher : `is_active` reste un booléen « streaming actionnable live » MAIS le caractère « fiable » est borné au périmètre réellement streamé (`switch`), pour ne pas geler `light`/`cover` en faux readback.
  - [x] Trancher : `button` est un no-op documenté (pas de `state_topic` → rien à streamer, jamais `unknown`).
  - [x] Documenter périmètre minimal et invariants dans la story.

- [x] Task 2 — Étendre `StateSynchronizer` (`resources/daemon/sync/state.py`) au `switch` (AC: 1, 2, 4, 7, 8)
  - [x] Ajouter le périmètre actionnable vague 2 : `_VAGUE2_ACTIONABLE = ("switch",)` ; ensemble streamé = `sensor`, `binary_sensor`, `switch`. `button` exclu (sans état).
  - [x] Généraliser `_iter_vague1_candidates` → `_iter_streamed_candidates` (types ∈ `_STREAMED_TYPES`), comportement vague 1 préservé à l'identique.
  - [x] `_translate_value` : `switch` → `ON`/`OFF` (table binaire `_BINARY_TRUE`, cohérent payload discovery). `sensor` inchangé (valeur brute). `button` jamais traduit (non streamé).
  - [x] `_candidate_cmd_id` : pour un `switch`, cible la commande **info de readback** (`ENERGY_STATE` via `_READBACK_KEYS`) et non les actions. Conserve : `reason_details["cmd_id"]` prioritaire ; sinon `info` ; sinon première commande. `_candidate_current_value` corrigé pour lire la même commande de readback (sinon snapshot switch vide car 1ʳᵉ cmd = action).
  - [x] `handle_state_message`, `list_state_targets`, `publish_initial_states` reposent sur l'itérateur généralisé → switch automatique. `state ⊆ discovery` vérifié (topic lu depuis `app["publications"]`).

- [x] Task 3 — Rendre `is_active` scope-aware + ajuster `CommandSynchronizer` (AC: 6, 10)
  - [x] `StateSynchronizer.is_active` → `True`.
  - [x] Exposer `streams_actionable_type(ha_type) -> bool` (True pour `switch`, False sinon).
  - [x] `sync/command.py:_has_reliable_state` : garde `_state_sync_streams_type` après `_is_state_sync_active`. Compat ascendante : méthode absente → comportement antérieur conservé.
  - [x] Tests 12.1 mis à jour : `test_real_state_sync_is_active_from_vague2`, `test_command_sync_sees_real_state_sync_as_active`.

- [x] Task 4 — Tests et non-régression (AC: 1, 2, 4, 5, 6, 8, 9, 10)
  - [x] Nouveau `tests/unit/test_story_12_2_switch_state_streaming.py` (17 cas) : switch → `ON`/`OFF` retain=True ; traductions ; snapshot initial ; `list_state_targets` inclut switch / exclut button ; `state ⊆ discovery`.
  - [x] Contrat `is_active` : True ; `streams_actionable_type` paramétré switch/light/cover/button/sensor/binary_sensor.
  - [x] `CommandSynchronizer` : switch + `ENERGY_STATE` → reliable True ; light + `LIGHT_STATE` → False ; cover + `FLAP_STATE` → False.
  - [x] `button` : `handle_state_message` → False, aucun publish.
  - [x] Non-régression : suite pytest complète verte — **891 passed** (unit + integration).

- [x] Task 5 — Gate terrain (AC: 11) — **PASS le 2026-06-18 sur box réelle `192.168.1.21`. Voir Completion Notes › Gate terrain 12.2.**
  - [x] `--cleanup-discovery --restart-daemon` → `Deploy complete.` ; daemon `0.2.0` up, `/system/status` = `ok`, MQTT `connected` (`127.0.0.1:1883`), `derniere_operation_resultat=succes`.
  - [x] `/system/state_listeners` inclut désormais les `switch` ayant `ENERGY_STATE` : eq554/187/188/447/448/443/103/597 (`ha_type=switch`), enregistrés sans modif PHP.
  - [x] Switch `on`/`off` réel prouvé via `mosquitto_sub` (retained) : `jeedom2ha/554/state=OFF` (cible AC#11, plus `unknown`) ; eq187=ON, eq188=OFF, eq447=ON, eq448=ON, eq443=ON, eq103=OFF, eq597=ON. Config discovery `switch/jeedom2ha_554` correcte (`state_on=ON`/`state_off=OFF`, `state_topic=jeedom2ha/554/state`).
  - [x] Non-régression : eq553 vague 1 OK (65 listeners multi-sensor `jeedom2ha/553/<cmd>/state` ; 95 configs sensor) ; light (18) / cover (8) / binary_sensor (7) discovery présents. Observation non-bloquante documentée (cf Completion Notes).

## Décision architecte (Task 1) — tranchée par Winston, 2026-06-18

Deux questions d'architecture conditionnent la vague 2. Décisions prises au niveau story (granularité identique à la sous-décision R1/R2 de Story 12.1), pas de document `create-architecture` dédié : le périmètre est borné et n'introduit ni nouveau composant ni nouveau contrat externe.

**Décision 1 — Contrat `is_active` scope-aware (pas de gel light/cover).**

Problème : `CommandSynchronizer._has_reliable_state()` consulte un booléen global `is_active`. Si la vague 2 le bascule à `True` sans borne, les types `light`/`cover` (qui possèdent des commandes info `LIGHT_STATE`/`FLAP_STATE`) seraient déclarés « fiables » alors qu'ils ne sont **pas** streamés → `CommandSynchronizer` cesserait de publier l'état optimiste en attendant une confirmation réelle qui n'arrive jamais ⇒ régression (entité figée/`unknown` après commande).

Verdict : le caractère « fiable » doit être **borné au périmètre réellement streamé**, pas un global. Solution minimale, sans nouveau composant :
- `StateSynchronizer.is_active` → `True` (au moins un domaine actionnable, `switch`, est streamé de façon fiable) ;
- `StateSynchronizer.streams_actionable_type(ha_type) -> bool` (source de vérité du périmètre actionnable : `True` pour `switch` seulement en vague 2) ;
- `command.py:_has_reliable_state` ajoute, après `_is_state_sync_active`, un garde : si `state_sync` expose `streams_actionable_type`, exiger qu'il renvoie `True` pour le type courant ; sinon (anciens fakes) conserver le comportement antérieur (compat ascendante).

Justification : « embrace boring technology » — on réutilise le contrat existant `is_active`/`_is_state_sync_active`, on ajoute un seul prédicat de périmètre. Le séquencement des vagues (FR49) reste piloté par un seul ensemble (`_VAGUE2_ACTIONABLE`), source unique côté daemon. Les vagues futures (`cover`, `climate`) n'auront qu'à étendre cet ensemble.

**Décision 2 — `button` est un no-op d'état documenté (honnêteté NFR).**

Constat de code : `button` est command-only — `discovery/publisher.py:_build_button_payload` ne déclare aucun `state_topic` et `http_server.py:73` le range dans `_TYPES_WITHOUT_STATE_TOPIC`. Une entité HA `button` est un déclencheur sans état persistant : elle n'apparaît jamais en `unknown`.

Verdict : la vague 2 ne publie **aucun** état pour `button`. L'epic groupe `switch`+`button` comme « la vague actionnable », mais l'état réel readback ne concerne structurellement que `switch`. Publier un `state_topic` pour `button` violerait state ⊆ discovery (aucun topic déclaré) et fabriquerait un faux état (anti-pattern « no faux readback »). Donc : `button` ∉ `_VAGUE2_ACTIONABLE` ; comportement testé explicitement (un `button` ne produit aucun publish). Aucune dette : il n'y a rien à streamer côté HA.

Conséquence d'implémentation : la registration PHP des listeners étant pilotée par `list_state_targets()` (qui ne renvoie que des entités avec `state_topic` valide commençant par `jeedom2ha/`), `button` est naturellement exclu sans code spécifique. Aucune modification PHP n'est requise par cette story.

## Dev Notes

### Source produit et scope

- Foyer produit : `pe-epic-12` (Restitution d'état runtime), vague 2. Définition : `_bmad-output/planning-artifacts/epics-projection-engine.md` (## Epic 12 → Story 12.2 réservée).
- Exigences : PRD `Feature 9` / `FR46-FR50` + `NFR13` (`_bmad-output/planning-artifacts/prd.md`).
- Débloque : `switch.jeedom2ha_554` de Story 11.2 (chauffe-eau eq554, `backlog-icebox §3.2`) et les parties actionnables de Story 11.3 (IQ EV On/Off eq583, pilotage priorisation eq628).
- Borne vague 2 : `switch` (état réel) + `button` (no-op documenté, sans état) UNIQUEMENT. `climate`/`alarm_control_panel`/autres = vagues ultérieures gouvernées (FR49).

### Fondations posées par Story 12.1 (à étendre, ne pas réinventer)

- `resources/daemon/sync/state.py` — `StateSynchronizer` : `handle_state_message(eq_id, cmd_id, value)`, `list_state_targets()`, `publish_initial_states(decision)`, `_resolve_state_target`, `_iter_vague1_candidates`, `_candidate_cmd_id`, `_candidate_state_topic`, `_translate_value`. Vague 1 limite à `_VAGUE1_TYPES = ("sensor", "binary_sensor")` et `is_active` retourne **False**.
- Canal inbound (12.1, déjà câblé et testé terrain) : `POST /action/state_update` (`transport/http_server.py`) → `StateSynchronizer.handle_state_message`. PHP `syncStateListeners()` lit `GET /system/state_listeners` (issu de `list_state_targets()`) et enregistre un listener Jeedom par cmd publiée → `callDaemon('/action/state_update')`. **Comme la registration PHP est pilotée par `list_state_targets()`, ouvrir le scope `switch` côté daemon enregistre automatiquement les listeners switch — aucune modif PHP.**

### Chemin de valeur switch (vague 2 cible)

- Mapper switch : `resources/daemon/mapping/switch.py`. `commands = energy_cmds` indexées par clés génériques `ENERGY_STATE` (info readback), `ENERGY_ON`/`ENERGY_OFF` (actions). La commande **readback** = `ENERGY_STATE` (`type=info`).
- Discovery payload : `discovery/publisher.py:_build_switch_payload` (~L450) → `state_topic=jeedom2ha/{eq}/state`, `command_topic=jeedom2ha/{eq}/set`, `payload_on=ON`, `payload_off=OFF`. → traduire la valeur readback en `ON`/`OFF` (table binaire identique à `binary_sensor`).
- `decision.state_topic` du switch = `jeedom2ha/{eq}/state`, assigné par `http_server.py:_resolve_state_topic` (L76-82, switch ∈ `PublisherRegistry.known_types()` et ∉ `_TYPES_WITHOUT_STATE_TOPIC`). À lire depuis `app["publications"]` (state ⊆ discovery), jamais reconstruit.

### Pourquoi `button` est un no-op (point clé honnêteté)

- `discovery/publisher.py:_build_button_payload` (L613-640) ne pose **aucun** `state_topic` ; commentaire explicite : « No state_topic: button is command-only (no persistent state in HA) ». `command_topic` = `jeedom2ha/{eq}/cmd`.
- `http_server.py:73` : `_TYPES_WITHOUT_STATE_TOPIC = {"button"}` → `_resolve_state_topic(button)` renvoie `""`.
- Conséquence : une entité HA `button` est un déclencheur sans état ; elle n'apparaît jamais en `unknown`. La vague 2 ne crée donc aucun `state_topic` pour `button` (interdit par state ⊆ discovery) et ne stream rien. L'epic regroupe `switch`+`button` comme « la vague actionnable » ; côté implémentation honnête, l'état réel ne concerne que `switch`.

### Interaction critique avec `CommandSynchronizer` (ne pas geler light/cover)

- `sync/command.py:_has_reliable_state` (L349-372) consulte `app["state_synchronizer"]` via `_is_state_sync_active` (L374-400). Aujourd'hui `is_active=False` → toujours optimiste. Si l'on bascule `is_active=True` **sans borne de type**, un `light` (avec `LIGHT_STATE` info) ou un `cover` (avec `FLAP_STATE`) serait considéré « fiable » → `CommandSynchronizer` attendrait une confirmation réelle **jamais publiée** (non streamés en vague 2) ⇒ régression (entité figée/`unknown` après commande). D'où le contrat **scope-aware** : seul le type réellement streamé (`switch`) est « fiable ».

### MQTT plumbing

- `MqttBridge.publish_message(topic, payload, qos=1, retain=True)` pour l'état (HA retrouve la dernière valeur au redémarrage). Réutiliser tel quel.

### Dev Agent Guardrails

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle.
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.
- Référence complète modes + cycle validé terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`.

#### Garde-fous implémentation

- Borne vague 2 stricte : ne PAS alimenter `light`/`cover`/`climate`/`alarm_control_panel`. `button` = no-op (jamais de `state_topic`).
- Ne JAMAIS reconstruire un `state_topic` à la main : le lire depuis `app["publications"]` (state ⊆ discovery, AC#7).
- Event-driven uniquement : pas de cache d'état métier autoritatif (NFR6/NFR13).
- `retain=True` pour l'état ; discovery publiée AVANT le premier état.
- `switch` : `ON`/`OFF` doivent matcher le payload discovery (pas d'inversion).
- `is_active` scope-aware : ne jamais déclarer fiable un type non streamé (sinon gel light/cover).
- Périmètre PHP : aucune modif attendue (registration pilotée par `list_state_targets()`).

### Project Structure Notes

- Worktree dédié : `projects/jeedom2ha-pe-12.1` (réutilisé pour la suite de l'epic 12).
- Module modifié : `resources/daemon/sync/state.py` (extension switch + `is_active` scope-aware) ; `resources/daemon/sync/command.py` (gate `_has_reliable_state` borné au type streamé).
- Tests : nouveau `tests/unit/test_story_12_2_switch_state_streaming.py` ; mise à jour des assertions `is_active` dans `test_story_12_1_state_streaming.py`.
- Les `_bmad-output/planning-artifacts/*` ne sont pas à modifier par cette story (sauf correction documentaire explicite).

### References

- `_bmad-output/planning-artifacts/epics-projection-engine.md` — ## Epic 12, Story 12.2 (réservée), Gates epic-level pe-epic-12.
- `_bmad-output/planning-artifacts/prd.md` — Feature 9, FR46-FR50, NFR13.
- `_bmad-output/implementation-artifacts/12-1-streaming-valeur-sensor-binary-sensor-vague-1.md` — fondations StateSynchronizer + canal inbound + R1 listeners.
- `resources/daemon/sync/state.py` — `StateSynchronizer` (à étendre).
- `resources/daemon/sync/command.py:349` — `_has_reliable_state` ; `:374` — `_is_state_sync_active`.
- `resources/daemon/mapping/switch.py` — `energy_cmds` (`ENERGY_STATE` readback).
- `resources/daemon/discovery/publisher.py:450` — `_build_switch_payload` ; `:613` — `_build_button_payload` (no state_topic).
- `resources/daemon/transport/http_server.py:73` — `_TYPES_WITHOUT_STATE_TOPIC` ; `:76` — `_resolve_state_topic`.
- `resources/daemon/tests/unit/test_story_12_1_state_streaming.py:326,335` — assertions `is_active` à mettre à jour.

## Senior Developer Review (AI) — code-review adversarial, 2026-06-18

**Reviewer :** Claude Opus 4.8 (rôle : relecteur adversarial). **Communication :** français, niveau intermediate.

**Cohérence git ↔ File List :** aucune divergence. Les 5 fichiers déclarés correspondent exactement aux changements git (`state.py`, `command.py`, `sprint-status.yaml`, `test_story_12_1_*` modifiés ; `12-2-*.md`, `test_story_12_2_*` ajoutés). `__pycache__` exclus.

**Audit AC :** AC#1-2-4-5-6-7-8-9-10 implémentés et couverts par tests. AC#3 vérifié : route inbound `POST /action/state_update` (`http_server.py:2746 _handle_action_state_update`) appelle `handle_state_message` sans filtre de type → le `switch` est pris en charge automatiquement, aucune modif route nécessaire. AC#11 (gate terrain) : NON exécutable hors box → reste à valider par Alexandre.

**Audit tâches :** Tasks 1-4 marquées [x] vérifiées dans le code. Tasks 0/5 marquées [~] (terrain, non exécutables) — honnêtement signalées, pas de faux [x].

### Findings

- 🔴 **HIGH — corrigé.** `switch` *sans* readback (`switch_on_off_only` : `ENERGY_ON`+`ENERGY_OFF`, pas d'`ENERGY_STATE`) : `_candidate_cmd_id`/`_candidate_current_value` retombaient sur la **première commande** (une action) → le switch devenait une cible d'état parasite sur une commande d'action (`list_state_targets` l'exposait, `handle_state_message` aurait publié). Viole AC#1 (« seul le readback alimente l'état du switch ») et le principe « no faux readback ». **Fix :** pour les types actionnables (présents dans `_READBACK_KEYS`), résolution **exclusivement** via les clés de readback ; sinon `None` (jamais de fallback sur une action). Régression couverte : `test_switch_without_readback_is_not_a_state_target`, `test_switch_without_readback_streams_nothing`.
- 🟢 Aucun problème de sécurité / injection (pas d'entrée externe non bornée ; topic lu depuis `app["publications"]`, jamais reconstruit).
- 🟢 Tests = vraies assertions (topics/payloads/retain exacts, paramétrage ON/OFF), pas de placeholder.

**Verdict :** après correction du HIGH, ACs code (1-10) implémentés et verts (**893 tests**). Seul AC#11 (terrain) reste à exécuter sur box.

### Review Follow-ups

- [x] [AI-Review][AC#11] Gate terrain exécuté sur box DEV/TEST `192.168.1.21` le 2026-06-18 — **PASS**. `state_listeners` inclut les switch `ENERGY_STATE` ; `on`/`off` réel prouvé via `mosquitto_sub` (eq554=OFF cible AC#11) ; non-régression eq553 + light/cover OK. Détails : Completion Notes › Gate terrain 12.2.
- [x] [AI-Review][P2][PR#125] `_READBACK_KEYS["switch"]` ne listait que `ENERGY_STATE` alors que `command.py:_has_reliable_state` traite aussi `PRESENCE` comme readback fiable → un presence switch (Story 10.7) avait son publish optimiste supprimé sans jamais streamer d'état réel. Corrigé : `PRESENCE` ajouté aux readback keys switch + 4 tests de régression. 897 tests verts.
- [ ] [AI-Review][LOW][suivi] 52 erreurs transitoires `[DISCOVERY] … bridge indisponible` sur la passe de discovery finale (15:35:13-16) du restart terrain, absentes du baseline 12.1 (0 erreur). Chaque entité concernée (eq627/128/385/113/67/244/506/193/389/594/595 — sensor/binary_sensor/climate/button) a été publiée avec succès 3-6× plus tôt dans le même restart (config + availability `online` + snapshot d'état) → aucune entité manquante sur le broker. Course bénigne entre une passe discovery tardive et la disponibilité du bridge ; à investiguer pour réduire le bruit (non bloquant AC#11).

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (create-story + dev-story + code-review)

### Debug Log References

- `pytest tests/unit/test_story_12_2_switch_state_streaming.py tests/unit/test_story_12_1_state_streaming.py tests/unit/test_command_sync.py -q` → 65 passed.
- `pytest tests/unit tests/integration -q` → **891 passed** (637 DeprecationWarnings pré-existants, hors scope).

### Completion Notes List

- Périmètre streamé étendu : `_STREAMED_TYPES = _VAGUE1_TYPES + _VAGUE2_ACTIONABLE` avec `_VAGUE2_ACTIONABLE = ("switch",)`. Les vagues futures n'ont qu'à étendre cet unique tuple.
- `is_active` scope-aware : `is_active=True` (un actionnable streamé) MAIS `streams_actionable_type()` borne la fiabilité au seul `switch`. `command.py:_has_reliable_state` ajoute le garde `_state_sync_streams_type` → `light`/`cover` conservent leur publish optimiste (pas de gel). Compat ascendante : un state_sync sans la méthode garde le comportement antérieur (anciens fakes verts).
- Readback switch = `ENERGY_STATE` (info), jamais `ENERGY_ON`/`ENERGY_OFF` (actions), via `_READBACK_KEYS`. Bug corrigé sur `_candidate_current_value` : il lisait la 1ʳᵉ commande (action pour un switch) → snapshot vide ; il résout désormais la commande de readback.
- `button` = no-op structurel : absent de `_VAGUE2_ACTIONABLE`, pas de `state_topic` (discovery), donc exclu automatiquement de `list_state_targets()` et de `handle_state_message`. Aucune modif PHP.
- Traduction `switch` → `ON`/`OFF` via `_ONOFF_TYPES` (partagé avec `binary_sensor`), cohérent avec le payload discovery (`payload_on=ON`/`payload_off=OFF`).
- **Gate terrain 12.2 — PASS le 2026-06-18** sur box réelle `192.168.1.21` (`domobox`), via `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon` → `Deploy complete.`
  - Runtime sain : `/system/status=ok`, daemon `0.2.0`, MQTT `connected` (`127.0.0.1:1883`), `derniere_operation_resultat=succes` (sync).
  - `/system/state_listeners` : les `switch` à readback `ENERGY_STATE` sont désormais enregistrés — eq554/187/188/447/448/443/103/597 (`ha_type=switch`), aux côtés des sensor/binary_sensor vague 1. Aucune modif PHP (registration pilotée par `list_state_targets()`).
  - **AC#11 prouvé** (mosquitto_sub retained sur `jeedom2ha/<eq>/state`) : `554=OFF` (cible, Chauffe-eau — plus `unknown`), `187=ON`, `188=OFF`, `447=ON`, `448=ON`, `443=ON`, `103=OFF`, `597=ON`. Mélange `ON`/`OFF` réels (pas un défaut uniforme). Config discovery `homeassistant/switch/jeedom2ha_554/config` correcte : `state_on=ON`/`state_off=OFF`, `state_topic=jeedom2ha/554/state`, `command_topic=jeedom2ha/554/set`, device `Chauffe-eau`. 9 configs `switch` publiées.
  - **Non-régression** : eq553 vague 1 intacte (65 listeners multi-sensor `jeedom2ha/553/<cmd>/state`) ; 95 configs `sensor`, 7 `binary_sensor`, 18 `light`, 8 `cover` présentes sur le broker ; pilotage light/cover non gelé (publish optimiste conservé).
  - **Observation non-bloquante** : 52 erreurs `[DISCOVERY] … bridge indisponible` sur la passe discovery finale (15:35:13-16), absentes du baseline 12.1. Bénignes : chaque entité concernée a 3-6 publications réussies antérieures dans le même restart (config + availability `online` + snapshot) ; toutes présentes sur le broker. Follow-up LOW ouvert (réduire le bruit / confirmer la cause de la course passe-tardive ↔ bridge).

### File List

- `resources/daemon/sync/state.py` (modifié) — périmètre vague 2 switch, `is_active`/`streams_actionable_type` scope-aware, `_READBACK_KEYS`, `_iter_streamed_candidates`, `_candidate_cmd_id`/`_candidate_current_value` readback-aware, `_translate_value` ON/OFF switch.
- `resources/daemon/sync/command.py` (modifié) — garde `_state_sync_streams_type` dans `_has_reliable_state` (compat ascendante).
- `resources/daemon/tests/unit/test_story_12_2_switch_state_streaming.py` (créé) — 17 cas de test vague 2.
- `resources/daemon/tests/unit/test_story_12_1_state_streaming.py` (modifié) — assertions `is_active` mises à jour pour le contrat vague 2.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modifié) — statut 12.2.

### Change Log

- 2026-06-18 — Story 12.2 créée via workflow create-story (vague 2 pe-epic-12 : streaming switch + button no-op).
- 2026-06-18 — Décision architecte (Winston) : contrat `is_active` scope-aware + `button` no-op documenté (§Décision Task 1).
- 2026-06-18 — dev-story : implémentation switch + scope-aware gate, 891 tests verts. Tasks 1-4 done ; Tasks 0/5 (terrain) à exécuter sur box. Statut → review.
- 2026-06-18 — code-review (adversarial) : 1 finding HIGH corrigé (switch sans readback → cible d'état parasite sur commande d'action ; résolution bornée aux clés de readback + 2 tests de régression). 893 tests verts. Statut → done (AC code 1-10 ; AC#11 terrain reste à valider par Alexandre).
- 2026-06-18 — gate terrain exécuté sur box réelle `192.168.1.21` (`--cleanup-discovery --restart-daemon`) : **AC#11 PASS** (switch `on`/`off` réel, eq554=OFF, state_listeners switch enregistrés, non-régression eq553 + light/cover). 1 follow-up LOW ouvert (52 erreurs transitoires `bridge indisponible` sur passe discovery finale, sans entité manquante). Story 12.2 entièrement validée (AC 1-11).
- 2026-06-18 — review PR #125 (bot, P2 résolu) : `_READBACK_KEYS["switch"]` n'incluait que `ENERGY_STATE`, alors que `command.py:_has_reliable_state` traite aussi `PRESENCE` comme readback fiable du switch. Asymétrie → un presence switch (Story 10.7) avait sa publication optimiste supprimée sans jamais streamer d'état réel (reste `unknown`). Corrigé : `PRESENCE` ajouté aux readback keys switch (les deux tables sont désormais alignées) + 4 tests de régression (presence switch streame ON/OFF, devient state target, snapshot initial, cohérence command↔state). 897 tests verts. Nettoyage : suppression de 2 lignes parasites (`</content>`/`</invoke>`) en fin de fichier.
