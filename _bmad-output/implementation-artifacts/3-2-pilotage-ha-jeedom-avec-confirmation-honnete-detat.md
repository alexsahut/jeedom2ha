# Story 3.2: Pilotage HA → Jeedom avec confirmation honnête d'état

Status: done

## Story

As a utilisateur Home Assistant,  
I want piloter mes équipements depuis HA avec une confirmation réelle de réussite,  
so that je sois sûr que mes ordres sont exécutés.

## Acceptance Criteria

1. **Given** un actionneur est publié par `jeedom2ha`, vivant, et **autorisé au pilotage** au sens runtime (publication active, `active_or_alive=true`, topic de commande exact connu, commandes action requises présentes dans `mapping.commands`)
2. **When** j'envoie une commande (ON/OFF, position, niveau, etc.) depuis HA
3. **Then** le démon traduit l'ordre et l'exécute via l'interface Jeedom standard retenue par l'architecture (API Jeedom)
4. **And** le démon rejette (avec trace runtime exploitable dans les logs) toute commande visant une entité non publiée, non vivante, inconnue ou retirée
5. **And** le plugin privilégie la confirmation par état réel quand elle existe, sans publier d'état mensonger
6. **And** pour les commandes sans retour fiable, il applique la politique prévue (optimiste contrôlé ou action stateless), de manière explicable et traçable
7. **And** le traitement des commandes reste strictement borné aux topics `jeedom2ha`, sans collision avec d'autres publishers/intégrations HA
8. **And** aucune commande ne réactive une ghost entity : une entité retirée reste non pilotable tant qu'elle n'est pas republiée proprement

## Scope Guardrails (non négociable)

- Gating commande obligatoire via le registre runtime (`app["publications"]` + `active_or_alive`) avant toute exécution Jeedom.
- Interdire tout effet de bord discovery dans le flux commande (pas de création d'entité, pas de republication config, pas de cleanup alternatif).
- Contrat de topics verrouillé sur ceux déjà publiés par `DiscoveryPublisher` uniquement:
  - `jeedom2ha/{eq_id}/set` (switch/light/cover)
  - `jeedom2ha/{eq_id}/brightness/set` (light)
  - `jeedom2ha/{eq_id}/position/set` (cover)
- Pas de commande si MQTT bridge indisponible ou mapping runtime introuvable/non vivant.
- Frontière commande/état stricte: le flux commande ne publie pas d'état immédiat, sauf cas explicitement autorisé par la matrice de politique ci-dessous.
- Confirmation d'état honnête: préférer l'état réel (flux `event::changes` existant Story 3.1), ne jamais forcer un état faux.
- Ne pas étendre le périmètre Epic 4 (diagnostic UX avancé) ni Epic 5 (réconciliation lifecycle avancée).

## Tasks / Subtasks

- [x] **Task 1 — Introduire un routeur de commandes MQTT borné au namespace `jeedom2ha`** (AC: #2, #7)
  - [x] 1.1 Ajouter un service dédié (ex: `resources/daemon/sync/command.py`) pour parser les topics de commande et normaliser les payloads.
  - [x] 1.2 Verrouiller le contrat exact (pas de schéma concurrent):
    - [x] `jeedom2ha/{eq_id}/set` (switch/light/cover open-close-stop)
    - [x] `jeedom2ha/{eq_id}/brightness/set` (light brightness 0..100)
    - [x] `jeedom2ha/{eq_id}/position/set` (cover position 0..100)
  - [x] 1.3 Ignorer/rejeter proprement tout topic hors pattern avec `reason_code` explicite.
  - [x] 1.4 Résoudre la commande par topic exact publié + `mapping.commands`, sans inventer de nouveau routage.
  - [x] 1.5 Garantir l'anti-boucle: séparation stricte des flux commande (`*/set`) vs états (`*/state`, `*/brightness`, `*/position`).

- [x] **Task 2 — Appliquer le gating runtime avant exécution Jeedom** (AC: #1, #4, #8)
  - [x] 2.1 Définir/implémenter "autorisé au pilotage" de façon testable:
    - [x] `should_publish=true`
    - [x] `active_or_alive=true`
    - [x] topic commande exact conforme au contrat ci-dessus
    - [x] commandes action requises présentes dans `mapping.commands` pour la famille traitée
  - [x] 2.2 Rejeter les commandes vers entités non publiées, retirées, non vivantes ou inconnues.
  - [x] 2.3 Produire des logs `[SYNC-CMD]` structurés: `eq_id`, `topic`, `reason_code`, `action`.
  - [x] 2.4 Verrouiller le cas ghost entity: aucun appel Jeedom tant que l'entité n'est pas republiée via `/action/sync`.

- [x] **Task 3 — Exécuter les commandes via API Jeedom standard (`cmd::execCmd`)** (AC: #3)
  - [x] 3.1 Implémenter un adaptateur d'exécution JSON-RPC vers `core/api/jeeApi.php` (sur endpoint local déjà dérivé dans le daemon).
  - [x] 3.2 Traduire payload HA -> commande Jeedom en s'appuyant uniquement sur `mapping.commands`:
    - [x] Light/Switch ON/OFF -> `LIGHT_ON`/`LIGHT_OFF` ou `ENERGY_ON`/`ENERGY_OFF`
    - [x] Cover OPEN/CLOSE/STOP -> `FLAP_UP`/`FLAP_DOWN`/`FLAP_STOP`
    - [x] Brightness/Position -> `LIGHT_SLIDER`/`FLAP_SLIDER` avec `options={"slider":"<0..100>"}` (entier normalisé puis string)
  - [x] 3.3 Contrat d'appel `cmd::execCmd`:
    - [x] Actions ON/OFF/OPEN/CLOSE/STOP: `params={id:<cmd_id>, options:{}}`
    - [x] Actions slider: `params={id:<cmd_id>, options:{"slider":"<0..100>"}}`
  - [x] 3.4 Comportement d'erreur déterministe:
    - [x] payload invalide -> rejet local, aucun appel RPC, `reason_code=invalid_command_payload`
    - [x] commande Jeedom absente -> rejet local, aucun appel RPC, `reason_code=missing_action_command`
    - [x] erreur RPC -> échec de commande, aucun état immédiat, `reason_code=jeedom_rpc_error`
    - [x] timeout RPC -> échec de commande, aucun retry implicite, aucun état immédiat, `reason_code=jeedom_rpc_timeout`

- [x] **Task 4 — Politique de confirmation honnête d'état** (AC: #5, #6)
  - [x] 4.1 Appliquer la matrice explicite de politique de confirmation (section Dev Notes) sans déviation.
  - [x] 4.2 Si retour d'état fiable disponible (cmd info + flux Story 3.1 actif), confirmation par état réel obligatoire.
  - [x] 4.3 Si retour d'état non fiable, n'autoriser l'optimiste contrôlé que pour les lignes explicitement marquées comme autorisées.
  - [x] 4.4 Interdire toute publication d'état immédiat hors cas explicitement autorisé par la matrice.
  - [x] 4.5 Journaliser la stratégie choisie (`real_state_confirmation`, `optimistic_controlled`, `stateless`) avec `reason_code`.
  - [x] 4.6 Maintenir une latence nominale de confirmation cible ~1s, acceptable <=2s quand retour réel disponible.

- [x] **Task 5 — Intégration daemon et MQTT bridge** (AC: #2, #3, #4, #7)
  - [x] 5.1 Étendre `MqttBridge` pour souscrire aux topics de commande au `on_connect`.
  - [x] 5.2 Relayer les messages entrants vers le service de pilotage sans couplage fort au thread paho.
  - [x] 5.3 Intégrer le service au cycle de vie du daemon (`main.py`) sans régression Story 3.1.
  - [x] 5.4 Préserver les garanties existantes: namespace strict, séparation des clés API plugin/core, rollback propre au démarrage.

- [x] **Task 6 — Couverture automatisée minimum (unitaires/intégration locale)** (AC: #3, #4, #5, #6, #7, #8)
  - [x] 6.1 Ajouter des tests unitaires dédiés au parsing topic/payload et au routage de commande.
  - [x] 6.2 Tester le gating runtime (entité active vs non active/ghost) avant appel API Jeedom.
  - [x] 6.3 Tester la traduction des commandes par type d'entité (light/switch/cover + brightness/position).
  - [x] 6.4 Tester la politique de confirmation honnête (réel prioritaire, optimiste/stateless explicite).
  - [x] 6.5 Ajouter test de coexistence publisher: aucun effet hors namespace `jeedom2ha`.

## Plan de tests réels minimum (obligatoire)

- [ ] **Test réel 3.2-A (happy path pilotage):** commande HA valide sur entité publiée/vivante -> exécution Jeedom + confirmation cohérente dans HA.
- [ ] **Test réel 3.2-B (gating anti-ghost):** commande vers entité retirée/non publiée -> rejet propre + aucun effet Jeedom + log runtime.
- [ ] **Test réel 3.2-C (coexistence namespace):** présence d'un autre publisher MQTT -> aucune consommation/aucun impact hors `jeedom2ha`.
- [ ] **Contexte de test réel (référence Story 3.1) à respecter pour les 3 tests:**
  - [ ] variables shell dédiées (URL/API key core/API key plugin/local secret/topic test) chargées avant exécution
  - [ ] broker MQTT local explicite pour la campagne de preuve
  - [ ] local secret relu dynamiquement depuis la config active (pas de secret figé)
  - [ ] mêmes critères de preuve homogène pour tous les cas
- [ ] **Preuve standard homogène pour chaque test:** préconditions, commande injectée, logs runtime, topics observés broker, observation Jeedom/HA, verdict.

## Risques / Pièges à éviter

- Écouter trop large (`#` / wildcard global) et capturer des commandes externes.
- Exécuter `cmd::execCmd` sans vérifier `active_or_alive`.
- Publier un état optimiste non explicité quand un état réel n'est pas disponible.
- Recréer/republier une entité depuis le flux commande (casse lifecycle).
- Couplage thread paho <-> asyncio non maîtrisé (race conditions).

## Dev Notes

### Contexte code existant à réutiliser

- `resources/daemon/sync/state.py` (Story 3.1): mécanisme runtime gating, logs structurés, flux `event::changes`, garde-fous namespace.
- `resources/daemon/transport/http_server.py`: source de vérité runtime `app["mappings"]` et `app["publications"]`.
- `resources/daemon/discovery/publisher.py`: contrats topics de commande déjà publiés (`command_topic`, `brightness_command_topic`, `set_position_topic`).
- `resources/daemon/transport/mqtt_client.py`: bridge MQTT déjà prêt pour LWT/reconnect; à étendre pour souscriptions commandes.

### Contrat de routage commande (exigé)

- Les commandes doivent être résolues à partir du couple `(topic publié par DiscoveryPublisher, mapping.commands)` et non par heuristique libre.
- Contrat exact des topics (et uniquement ceux-ci):
  - `jeedom2ha/{eq_id}/set` pour switch/light/cover
  - `jeedom2ha/{eq_id}/brightness/set` pour light
  - `jeedom2ha/{eq_id}/position/set` pour cover
- Aucune variante de schéma de topic ne doit être introduite dans Story 3.2.
- La résolution vers cmd Jeedom doit rester déterministe et explicable (`reason_code` en cas de rejet).
- Les payloads attendus par topic:
  - `jeedom2ha/{eq_id}/set`: `ON`/`OFF` (light/switch) ou `OPEN`/`CLOSE`/`STOP` (cover)
  - `jeedom2ha/{eq_id}/brightness/set`: entier 0..100
  - `jeedom2ha/{eq_id}/position/set`: entier 0..100

### Définition runtime: "autorisé au pilotage"

Une commande est autorisée au pilotage si et seulement si:

- `PublicationDecision.should_publish == true`
- `PublicationDecision.active_or_alive == true`
- le topic reçu correspond exactement à un topic de commande contractuel de l'entité
- `mapping.commands` contient la commande action requise pour la famille demandée
- l'entité n'est pas marquée retirée/inactive dans le registre runtime courant

### Politique de confirmation honnête (à implémenter explicitement)

- **Règle de frontière commande vs état (noir sur blanc):**
  - le flux commande ne publie pas d'état immédiat par défaut;
  - la confirmation passe par Story 3.1 (`event::changes`) dès qu'un retour d'état fiable existe;
  - seul un cas explicitement autorisé par la matrice ci-dessous peut publier un état immédiat.
- **Matrice de politique (obligatoire, sans invention côté dev):**

| Famille commande | Retour d'état fiable disponible | Politique | État immédiat autorisé |
|---|---|---|---|
| light/switch ON/OFF | Oui (`cmd info` mappé + flux Story 3.1 actif) | `real_state_confirmation` | Non |
| light/switch ON/OFF | Non | `optimistic_controlled` | Oui, `ON/OFF` non retained sur `state_topic` runtime |
| cover OPEN/CLOSE/STOP | Oui (`cmd info` cover mappé + flux Story 3.1 actif) | `real_state_confirmation` | Non |
| cover OPEN/CLOSE/STOP | Non | `stateless` | Non |
| brightness (0..100) | Oui/Non (scope actuel Story 3.2) | `stateless` | Non |
| position (0..100) | Oui/Non (scope actuel Story 3.2) | `stateless` | Non |

- Interdiction stricte: publier un état immédiat hors ligne explicitement marquée "Oui" dans la matrice.
- Anti-boucle renforcé: même en optimiste contrôlé, publication uniquement sur `state_topic` runtime; le routeur commande ne consomme que les topics `*/set`.

### Exigences architecture et conformité

- Respect strict des patterns d'architecture: séparation flux commandes / états / lifecycle.
- Respect du namespace MQTT `jeedom2ha/*` et de la politique retained (commandes non retained).
- Préserver le comportement de cleanup exact retained sur discovery (hérité Stories 2.x + 3.1).

### Exigences de tests

- Tests unitaires Python sous `resources/daemon/tests/unit/` priorisés pour la logique de routage/traduction.
- Tests intégration Python sous `resources/daemon/tests/integration/` pour validation de flux complet commande -> Jeedom -> confirmation.
- Non-régression obligatoire sur suites Story 3.1 (`test_state_sync*`, `test_discovery_cleanup_exact`).
- Pour les tests réels, réutiliser le contexte de preuve Story 3.1 (variables shell, broker local, secret relu dynamiquement, format de preuve homogène).

### Previous Story Intelligence (Story 3.1)

- Le registre runtime enrichi (`state_topic`, `active_or_alive`) est déjà la source de vérité: le réutiliser, ne pas le contourner.
- Le namespace strict `jeedom2ha/*` est déjà verrouillé côté sync d'état: appliquer la même discipline côté commandes.
- Les blocages terrain déjà résolus (format réel `event::changes`, clé API core dédiée) doivent rester intacts.
- Les entités ayant échoué en publication discovery sont forcées `should_publish=False`, `active_or_alive=False`: conserver ce garde-fou.

### Git Intelligence Summary (5 derniers commits)

- Les derniers commits fonctionnels du domaine produit (`Story 2.4`) montrent un pattern stable:
  - extension incrémentale `mapping` + `publisher` + `http_server`,
  - ajout de tests unitaires ciblés et assertions explicites sur topics/payloads,
  - snapshot d'artefacts BMAD en parallèle (`sprint-status`, story files).
- Conserver cette stratégie incrémentale pour Story 3.2: code + tests + mise à jour artifacts.

### Latest Technical Information (veille ciblée)

- `paho-mqtt` version stable la plus récente repérée: `2.1.0` (PyPI).  
  Conséquence: préserver la compatibilité API callbacks déjà gérée (`CallbackAPIVersion.VERSION1` + fallback).
- Documentation Home Assistant MQTT:
  - `light.mqtt`: topics de commande dédiés (`command_topic`, `brightness_command_topic`),
  - `cover.mqtt`: `command_topic` + `set_position_topic`,
  - `switch.mqtt`: `command_topic`.
- Conséquence Story 3.2: router strictement les topics effectivement publiés par `DiscoveryPublisher`, sans déviation.

### Project Structure Notes

- Zone principale d'implémentation attendue: `resources/daemon/`.
- Références de boundary:
  - transport MQTT: `resources/daemon/transport/mqtt_client.py`
  - runtime registry: `resources/daemon/transport/http_server.py`
  - sync état existant: `resources/daemon/sync/state.py`
- Éviter tout ajout de logique métier dans `core/php/jeedom2ha.php` (callback actuellement minimal).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3: Synchronisation & Pilotage]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2: Pilotage HA → Jeedom avec confirmation honnête d'état]
- [Source: _bmad-output/planning-artifacts/architecture.md#4. Process Patterns, Fallbacks & State Safety]
- [Source: _bmad-output/planning-artifacts/architecture.md#6. Lifecycle Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries]
- [Source: _bmad-output/planning-artifacts/prd.md#Contraintes Techniques du Domaine]
- [Source: _bmad-output/planning-artifacts/prd.md#Exigences Fonctionnelles]
- [Source: _bmad-output/planning-artifacts/prd.md#Exigences Non-Fonctionnelles]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Feedback Patterns]
- [Source: _bmad-output/project-context.md#Communication Daemon ↔ Plugin PHP]
- [Source: https://pypi.org/project/paho-mqtt/]
- [Source: https://www.home-assistant.io/integrations/light.mqtt/]
- [Source: https://www.home-assistant.io/integrations/cover.mqtt/]
- [Source: https://www.home-assistant.io/integrations/switch.mqtt/]

## Dev Agent Record

### Agent Model Used

Codex GPT-5 (dev-story workflow)

### Debug Log References

- Implémentation TDD Story 3.2: phase RED avec nouveaux tests `test_command_sync.py` et `test_command_sync_coexistence.py` (échec initial attendu), puis phase GREEN.
- Ajout du service `CommandSynchronizer` (`resources/daemon/sync/command.py`) avec routage topics strict `DiscoveryPublisher`, gating runtime `publications/active_or_alive`, traduction `mapping.commands`, exécution `cmd::execCmd`, et logs structurés `[SYNC-CMD]`.
- Intégration daemon/MQTT: souscriptions topics commande au `on_connect`, relay thread-safe vers asyncio, wiring `main.py` avec rollback propre startup/shutdown.
- Validation automatisée Story 3.2 + non-régression Story 3.1:
  - `python3 -m pytest -q resources/daemon/tests/unit/test_command_sync.py resources/daemon/tests/integration/test_command_sync_coexistence.py` -> `14 passed`
  - `python3 -m pytest -q resources/daemon/tests/unit/test_state_sync.py resources/daemon/tests/unit/test_state_sync_lifecycle.py resources/daemon/tests/unit/test_discovery_cleanup_exact.py resources/daemon/tests/integration/test_state_sync_coexistence.py resources/daemon/tests/integration/test_state_sync_cleanup_runtime_flow.py resources/daemon/tests/unit/test_command_sync.py resources/daemon/tests/integration/test_command_sync_coexistence.py` -> `37 passed`
  - `python3 -m pytest -q` -> `284 passed` (warnings de dépréciation aiohttp déjà existants hors périmètre Story 3.2)
- Reprise ciblée review (CHANGES REQUESTED) appliquée sans élargissement de scope:
  - verrouillage topics Discovery strict pour empêcher toute acceptation commande sur `sensor`/`binary_sensor` (`topic_not_published_by_discovery`) ;
  - correction de `_has_reliable_state` pour dépendre d’un state sync réellement actif/utilisable (pas seulement présent) ;
  - réalignement auth terrain par méthode: `cmd::execCmd` utilise la `core API key` prouvée sur box réelle (pas la clé plugin).
- Validation post-correctifs review:
  - `python3 -m pytest -q resources/daemon/tests/unit/test_command_sync.py resources/daemon/tests/integration/test_command_sync_coexistence.py` -> `17 passed`
  - `python3 -m pytest -q resources/daemon/tests/unit/test_state_sync.py resources/daemon/tests/unit/test_state_sync_lifecycle.py resources/daemon/tests/unit/test_discovery_cleanup_exact.py resources/daemon/tests/integration/test_state_sync_coexistence.py resources/daemon/tests/integration/test_state_sync_cleanup_runtime_flow.py resources/daemon/tests/unit/test_command_sync.py resources/daemon/tests/integration/test_command_sync_coexistence.py` -> `40 passed`
  - `python3 -m pytest -q` -> `287 passed`
- Correction terrain Story 3.2 (auth `cmd::execCmd`) exécutée sans élargissement de scope:
  - `CommandSynchronizer` et wiring daemon mis à jour pour utiliser explicitement la `core API key` sur le flux commande ;
  - tests Story 3.2 alignés sur le contrat réel documenté (`cmd::execCmd` -> core key) ;
  - validations rejouées:
    - `python3 -m pytest -q resources/daemon/tests/unit/test_command_sync.py resources/daemon/tests/integration/test_command_sync_coexistence.py` -> `17 passed`
    - `python3 -m pytest -q resources/daemon/tests/unit/test_state_sync.py resources/daemon/tests/unit/test_state_sync_lifecycle.py resources/daemon/tests/unit/test_discovery_cleanup_exact.py resources/daemon/tests/integration/test_state_sync_coexistence.py resources/daemon/tests/integration/test_state_sync_cleanup_runtime_flow.py` -> `23 passed` (`6 warnings` connues hors scope)
    - `python3 -m pytest -q` -> `287 passed` (`37 warnings` connues hors scope)

### Completion Notes List

- Routage commande borné au namespace `jeedom2ha` implémenté: uniquement `/{eq_id}/set`, `/{eq_id}/brightness/set`, `/{eq_id}/position/set`, avec rejet explicite des topics hors contrat.
- Gating runtime obligatoire avant tout RPC implémenté via `app["publications"]`, `should_publish`, `active_or_alive`, topic exact publié, et présence de la commande action dans `mapping.commands`.
- Exécution Jeedom standard via JSON-RPC `cmd::execCmd` implémentée avec contrat `options` strict (`{}` pour actions, `{"slider":"<0..100>"}` pour sliders) et erreurs déterministes (`invalid_command_payload`, `missing_action_command`, `jeedom_rpc_error`, `jeedom_rpc_timeout`).
- Contrat d’authentification flux commande réaligné sur la preuve terrain: `cmd::execCmd` envoie la `core API key` (et non la clé plugin), conformément à la règle projet "contrat par méthode/flux".
- Politique de confirmation honnête appliquée selon matrice Story 3.2: `real_state_confirmation` prioritaire si retour fiable, `optimistic_controlled` uniquement pour ON/OFF light/switch sans retour fiable, `stateless` sinon.
- Aucun effet de bord discovery/lifecycle introduit; non-régressions Story 3.1 validées par les suites ciblées et la suite globale.
- Les tests réels 3.2-A/B/C restent non exécutés dans cet environnement local (cases conservées non cochées).
- Correctif review #1: `CommandSynchronizer._expected_command_topics()` n’expose `/{eq_id}/set` que pour `light`/`switch`/`cover`; un `sensor`/`binary_sensor` sur `/{eq_id}/set` est rejeté avec `topic_not_published_by_discovery`.
- Correctif review #2: retour fiable conditionné à un state sync réellement actif (`StateSynchronizer.is_active`), évitant les faux positifs `real_state_confirmation` en mode Story 3.1 dégradé.
- Correctif review #3 (réaligné terrain): suppression d’ambiguïté plugin/core sur le flux commande; `cmd::execCmd` utilise explicitement la `core API key` prouvée sur box réelle.

### File List

- `_bmad-output/implementation-artifacts/3-2-pilotage-ha-jeedom-avec-confirmation-honnete-detat.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/sync/command.py`
- `resources/daemon/sync/state.py`
- `resources/daemon/transport/mqtt_client.py`
- `resources/daemon/main.py`
- `resources/daemon/tests/unit/test_command_sync.py`
- `resources/daemon/tests/integration/test_command_sync_coexistence.py`

### Change Log

- 2026-03-15: Story 3.2 créée en statut `ready-for-dev` avec contexte complet dev, garde-fous architecture, intelligence story précédente, synthèse git et veille technique.
- 2026-03-15: Implémentation Story 3.2 (routeur commande strict `jeedom2ha`, gating runtime avant RPC, exécution `cmd::execCmd` avec contrat `options`, politique de confirmation honnête, logs `[SYNC-CMD]`, intégration `MqttBridge`/`main.py`, tests unitaires + intégration 3.2).
- 2026-03-15: Validation non-régression Story 3.1 + suite globale pytest au vert (`284 passed`), story passée en `review`.
- 2026-03-15: Reprise ciblée review Story 3.2 (3 écarts bloquants corrigés: topics Discovery strict sensor/binary, fiabilité state sync réellement active, séparation plugin/core API keys) + validation complète (`17/40/287` tests passés).
- 2026-03-15: Réalignement Story 3.2 sur vérité terrain auth Jeedom: `cmd::execCmd` basculé sur `core API key`, tests Story 3.2 corrigés, non-régressions Story 3.1 ciblées rejouées (`23 passed`) et suite globale confirmée (`287 passed`).
- 2026-03-16: Clôture documentaire en `done` après correction des écarts de code review; les tests terrain 3.2-A/B/C restent différés et non exécutés dans cette clôture, avec risque accepté pour cette itération.

## Decision de cloture

### Decision de cloture

- Story `3.2` closee en `done` pour cette iteration.
- Les correctifs issus de la code review ont ete integres et les validations automatisees locales ont ete rejouees avec succes.
- Les tests terrain 3.2-A / 3.2-B / 3.2-C restent differes et non executes dans cette cloture; aucune preuve terrain supplementaire n'est revendiquee ici.

### Risques acceptes

- Un ecart reste possible entre la couverture automatisee locale et le comportement reel Jeedom / MQTT / Home Assistant sur le flux commande.
- Les scenarios terrain happy path, anti-ghost et coexistence namespace ne sont pas reproves dans cette cloture.
