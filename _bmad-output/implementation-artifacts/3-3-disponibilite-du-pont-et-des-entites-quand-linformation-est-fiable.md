# Story 3.3: Disponibilite du pont et des entites quand l'information est fiable

Status: review

## Story

As a utilisateur Home Assistant,  
I want visualiser l'etat de disponibilite de mes equipements,  
so that je sache si mon systeme est operationnel.

## Acceptance Criteria

1. **Given** le pont `jeedom2ha` est publie dans Home Assistant
2. **When** la connectivite MQTT du daemon change (connexion broker, perte broker, arret propre ou brutal du daemon)
3. **Then** le topic global `jeedom2ha/bridge/status` reste la source de verite de disponibilite du pont via LWT/birth retained
4. **And** toute entite `jeedom2ha` publiee devient indisponible dans HA quand le pont est hors ligne
5. **And** aucun unpublish discovery n'est emis pour un simple incident de connectivite globale

6. **Given** une entite HA publiee dispose d'un signal local d'indisponibilite fiable porte par l'equipement Jeedom (`eqLogic`) correspondant au meme `eq_id`
7. **When** le demon publie ou republie la discovery de cette entite HA
8. **Then** la discovery combine la disponibilite globale du pont et le topic local unique `jeedom2ha/{eq_id}/availability` porte par cet `eqLogic`
9. **And** Home Assistant considere l'entite disponible uniquement si les deux sources sont `online`
10. **And** cette combinaison reste conforme aux schemas MQTT officiels `light`, `cover` et `switch`

11. **Given** aucune information locale fiable n'existe pour l'equipement Jeedom (`eqLogic`) source d'une entite HA publiee
12. **When** sa discovery est publiee ou republiee
13. **Then** l'entite conserve une availability basee uniquement sur le pont
14. **And** le plugin n'invente jamais une indisponibilite locale

15. **Given** l'equipement Jeedom (`eqLogic`) source d'une entite HA publiee devient localement indisponible sans etre supprime de Jeedom
16. **When** le demon traite cette information fiable
17. **Then** il publie un etat `offline` retained sur le topic local unique `jeedom2ha/{eq_id}/availability`
18. **And** l'entite reste connue de HA
19. **And** ce cas reste distinct d'une suppression, exclusion ou ineligibilite qui continue d'utiliser l'unpublish discovery

20. **Given** un equipement est supprime, exclu ou rendu ineligible
21. **When** `/action/sync` reconcilie le perimetre publie
22. **Then** le plugin retire la discovery comme aujourd'hui
23. **And** il ne remplace jamais cette suppression par un simple `unavailable`

24. **Given** une commande HA vise une entite explicitement marquee indisponible localement
25. **When** un message MQTT de commande arrive
26. **Then** le demon la rejette proprement avec un `reason_code` explicite
27. **And** il ne contourne pas le signal d'indisponibilite publie a HA

## Scope Guardrails (non negociable)

- Conserver l'implementation actuelle du **LWT global** dans `resources/daemon/transport/mqtt_client.py` comme source de verite du pont. Story 3.3 etend la disponibilite des entites, elle ne remplace pas Story 1.3.
- **Ne pas** migrer la discovery vers le mode `device` Home Assistant dans cette story. Le code courant utilise le single-component discovery; Story 3.3 doit rester incremental et compatible avec l'existant.
- **Ne pas** surcharger `PublicationDecision.active_or_alive` pour representer l'indisponibilite locale. Ce flag sert deja au gating runtime "publie/vivant" introduit par Stories 3.2 et 3.2-bis.
- **Contrat de topic local fige pour toute la story:** `jeedom2ha/{eq_id}/availability`, ou `eq_id` designe toujours l'identifiant Jeedom de l'`eqLogic` porteur du signal local. Aucun autre schema de topic local n'est autorise dans cette story.
- **Ne pas** assimiler un equipement `disabled`, exclu, supprime ou non mappable a une simple indisponibilite temporaire. Ces cas doivent continuer a utiliser l'unpublish discovery.
- **Ne pas** inventer une heuristique plugin-specifique opaque de type "nom contient offline" ou "valeur vide = indisponible". Toute disponibilite locale doit provenir d'un signal Jeedom standard et explicite.
- **Ne pas** supposer l'existence d'un vrai service temps reel `resources/daemon/sync/state.py`. Ce fichier n'existe pas dans le workspace courant; Story 3.3 doit fonctionner avec les points d'entree reels disponibles aujourd'hui.
- Respecter la politique retained du projet: `discovery` et `availability` retained, `command` non retained.
- Aucune extension UX obligatoire cote Jeedom Desktop dans cette story. Le badge de pont existant peut rester tel quel; le coeur du sujet est le contrat MQTT et le runtime daemon.

## Tasks / Subtasks

- [x] **Task 1 - Introduire un modele de disponibilite runtime distinct du gating `active_or_alive`** (AC: #6, #8, #15, #24)
  - [x] 1.1 Etendre `PublicationDecision` ou ajouter une structure auxiliaire pour porter explicitement:
    - [x] `bridge_availability_topic`
    - [x] `eqlogic_availability_topic` (optionnel, toujours `jeedom2ha/{eq_id}/availability`)
    - [x] `local_availability_supported`
    - [x] `local_availability_state` (`online`, `offline`, `unknown`)
    - [x] `availability_reason`
  - [x] 1.2 Conserver `active_or_alive` avec son sens actuel: discovery publiee avec succes et runtime commandable au sens Stories 3.2 / 3.2-bis.
  - [x] 1.3 Centraliser les constantes MQTT de disponibilite (`online`, `offline`, topic global du pont) pour eviter les chaines dupliquees.

- [x] **Task 2 - Extraire un signal local fiable depuis la topologie Jeedom sans heuristique opaque** (AC: #6, #11, #15, #20)
  - [x] 2.1 Etendre `core/class/jeedom2ha.class.php::getFullTopology()` pour exposer un bloc de statut minimal d'equipement quand les getters standards Jeedom sont disponibles.
  - [x] 2.2 Prioriser des signaux standards issus du core Jeedom, en particulier les statuts `timeout` et `lastCommunication`, plutot que des conventions de plugins tiers.
  - [x] 2.3 Normaliser ce bloc dans `resources/daemon/models/topology.py` avec une semantique conservative:
    - [x] `timeout === 1` -> indisponibilite locale fiable
    - [x] `timeout === 0` -> disponibilite locale fiable
    - [x] valeur absente / non interpretable -> disponibilite locale non supportee
  - [x] 2.4 Garder `is_enable == false`, exclusion explicite et absence d'eligibilite dans le flux actuel d'unpublish, pas dans le flux availability.

- [x] **Task 3 - Adapter `DiscoveryPublisher` a la disponibilite bridge-only ou composee** (AC: #8, #11, #13)
  - [x] 3.1 Ajouter un helper commun pour construire les champs availability des payloads `light`, `cover` et `switch`.
  - [x] 3.2 Si `local_availability_supported == false`, conserver le schema actuel `availability_topic = jeedom2ha/bridge/status`.
  - [x] 3.3 Si `local_availability_supported == true`, publier un schema officiel Home Assistant avec:
    - [x] une liste `availability` contenant le topic global du pont et le topic local unique de l'`eqLogic` `jeedom2ha/{eq_id}/availability`
    - [x] `availability_mode = all`
    - [x] `payload_available = online`
    - [x] `payload_not_available = offline`
  - [x] 3.4 Preserver strictement les topics de commande/etat existants (`state_topic`, `command_topic`, `brightness_command_topic`, `set_position_topic`).

- [x] **Task 4 - Publier et nettoyer les topics de disponibilite locale au bon moment** (AC: #15, #17, #20, #22)
  - [x] 4.1 Lors de `/action/sync`, apres publication discovery reussie, publier un message retained sur `jeedom2ha/{eq_id}/availability` uniquement pour les entites HA dont l'`eqLogic` source supporte une disponibilite locale fiable.
  - [x] 4.2 Si une entite bascule de "support local availability" vers "bridge-only", nettoyer le topic local retained devenu obsolete.
  - [x] 4.3 Lors d'un unpublish d'entite (suppression, exclusion, ineligibilite), nettoyer aussi le topic local d'availability pour eviter des traces retained orphelines.
  - [x] 4.4 Ne pas republier artificiellement tous les topics locaux lors d'une simple deconnexion broker: le LWT global doit suffire a marquer les entites indisponibles via `availability_mode = all`.

- [x] **Task 5 - Aligner le flux commande avec l'indisponibilite locale explicite** (AC: #24, #26)
  - [x] 5.1 Etendre `resources/daemon/sync/command.py` pour rejeter une commande quand une entite est explicitement `offline` localement.
  - [x] 5.2 Journaliser ce rejet avec un `reason_code` dedie (ex: `entity_unavailable`) sans casser les garde-fous existants (`mqtt_unavailable`, `entity_not_alive`, `entity_not_published`).
  - [x] 5.3 Ne pas changer la politique de confirmation honnete d'etat de Story 3.2 au-dela de ce gating supplementaire.

- [x] **Task 6 - Couverture automatisee minimale obligatoire** (AC: #1, #8, #13, #17, #22, #26)
  - [x] 6.1 Etendre `tests/unit/test_discovery_publisher.py` pour couvrir les deux modes:
    - [x] bridge-only
    - [x] bridge + entite avec `availability_mode = all`
  - [x] 6.2 Ajouter des tests de normalisation topologie/statut dans `tests/unit/test_topology.py`.
  - [x] 6.3 Ajouter des tests `http_server` verifies:
    - [x] publication d'un topic local retained quand le signal est fiable
    - [x] absence de topic local quand le signal ne l'est pas
    - [x] nettoyage du topic local lors d'un unpublish
  - [x] 6.4 Ajouter des tests `resources/daemon/tests/unit/test_command_sync.py` pour le rejet `entity_unavailable`.
  - [x] 6.5 Preserver les tests existants Story 1.3, 3.2 et 3.2-bis sur LWT, commande et bootstrap runtime.

## Plan de tests reels minimum (obligatoire)

- [ ] **Test reel 3.3-A (pont offline global):**
  - [ ] partir d'au moins deux entites `jeedom2ha` publiees dans HA
  - [ ] arreter brutalement le daemon ou couper le broker
  - [ ] verifier que `jeedom2ha/bridge/status` passe a `offline` en retained
  - [ ] verifier que les entites deviennent `unavailable` dans HA sans disparition des entites

- [ ] **Test reel 3.3-B (indisponibilite locale d'une seule entite):**
  - [ ] choisir un equipement dont le plugin source remonte un statut standard Jeedom interpretable (`timeout` ou equivalent normalise)
  - [ ] provoquer l'indisponibilite locale de cet equipement sans supprimer l'equipement Jeedom
  - [ ] verifier qu'un seul topic `jeedom2ha/{eq_id}/availability` passe a `offline`
  - [ ] verifier que l'entite cible devient `unavailable` tandis qu'une autre entite du meme pont reste disponible
  - [ ] si aucun equipement de la box de validation ne remonte un `timeout` fiable exploitable, marquer ce test terrain comme **conditionnel non executable sur cette box**
  - [ ] dans ce cas, fournir obligatoirement la preuve automatisee locale du chemin `timeout=1 -> jeedom2ha/{eq_id}/availability=offline -> entite unavailable -> rejet commande`

- [ ] **Test reel 3.3-C (suppression vs indisponibilite):**
  - [ ] supprimer ou exclure un equipement Jeedom deja publie
  - [ ] verifier qu'un payload vide retained est publie sur son topic discovery
  - [ ] verifier que l'entite disparait proprement de HA
  - [ ] verifier qu'on n'observe pas un simple basculement persistant en `unavailable`

- [ ] **Contexte terrain obligatoire:**
  - [ ] relire les secrets actifs (`plugin API key`, `core API key`, `local secret`) depuis la box reelle
  - [ ] capturer les logs `[MQTT]`, `[DISCOVERY]`, `[SYNC]`, `[SYNC-CMD]`, et idealement un prefixe `[AVAIL]` si ajoute
  - [ ] observer les topics MQTT retenus avant/apres chaque test
  - [ ] conserver la box Jeedom et le broker reels comme source de verite si le comportement diverge du code local

## Risques / Pieges a eviter

- Confondre **publie/vivant** (`active_or_alive`) et **disponible localement**.
- Marquer `disabled_eqlogic` ou `excluded_eqlogic` comme simplement `offline` au lieu de conserver l'unpublish discovery.
- Publier un topic local d'availability pour toutes les entites alors qu'aucune source fiable n'existe.
- Introduire une migration non demandee vers le device discovery HA.
- Casser les tests actuels qui verifient `availability_topic = jeedom2ha/bridge/status` sans ajouter les nouveaux cas "compose".
- Laisser des topics local availability retained orphelins apres suppression ou downgrade bridge-only.
- Se baser sur un module `resources/daemon/sync/state.py` inexistant dans le workspace courant.

## Dev Notes

### Contexte code existant a reutiliser

- `resources/daemon/transport/mqtt_client.py`
  - definit deja `BRIDGE_STATUS_TOPIC = "jeedom2ha/bridge/status"`
  - configure le LWT `offline` retained
  - publie le birth `online` retained au `on_connect`
- `resources/daemon/discovery/publisher.py`
  - construit aujourd'hui tous les payloads `light`, `cover`, `switch`
  - injecte actuellement `availability_topic = "jeedom2ha/bridge/status"` en dur
- `resources/daemon/transport/http_server.py`
  - reconstruit `app["mappings"]` et `app["publications"]` dans `/action/sync`
  - gere deja l'unpublish discovery des equipements supprimes/ineligibles
- `resources/daemon/sync/command.py`
  - applique deja le gating runtime et la politique de confirmation honnete
  - doit rester coherent avec l'etat d'availability publie a HA
- `core/class/jeedom2ha.class.php::getFullTopology()`
  - exporte actuellement `is_enable`, `is_visible` et les commandes, mais aucun statut local de disponibilite

### Intelligence extraite des stories precedentes

- Story 1.3 a deja livre la disponibilite **globale** du pont via LWT/birth. Story 3.3 part de cette base, elle ne la reimplemente pas.
- Story 3.2 a introduit `active_or_alive` pour le gating commande, mais ce flag signifie "discovery publiee et runtime vivant", pas "equipement localement joignable".
- Story 3.2-bis a impose le pattern de rehydratation runtime via `getFullTopology()` puis `/action/sync`; Story 3.3 doit reutiliser ce chemin plutot que creer un pipeline parallele.
- Les artefacts precedents mentionnent `resources/daemon/sync/state.py`, mais ce fichier est absent du workspace courant. Les tests Story 3.2 utilisent seulement un `_FakeStateSynchronizer`.

### Decision technique recommandee

- **Disponibilite globale du pont:** continuer a utiliser `jeedom2ha/bridge/status` tel quel.
- **Contrat de topic local unique:** `jeedom2ha/{eq_id}/availability`, avec `eq_id` = identifiant Jeedom de l'`eqLogic` porteur du signal local. Ce topic est porte par l'equipement Jeedom et reutilise tel quel par l'entite HA publiee pour ce meme `eq_id`.
- **Disponibilite locale d'entite:** n'exister que quand la topologie normalisee contient un signal Jeedom standard, interpretable et fiable pour l'`eqLogic` source.
- **Composition dans HA:** utiliser `availability` + `availability_mode = all` pour les entites disposant d'une disponibilite locale; conserver `availability_topic` bridge-only pour les autres.
- **Signal local retenu en priorite:** statut `timeout` de `eqLogic`, avec `lastCommunication` comme contexte diagnostique utile mais non suffisant seul pour trancher un online/offline.
- **Aucune source fiable:** rester en bridge-only. Mieux vaut publier moins d'indisponibilite que mentir.

### Conformite architecture et regles metier

- Respecter la separation stricte des cas:
  - indisponibilite temporaire -> topic availability
  - suppression / exclusion / ineligibilite -> unpublish discovery
- Respecter la politique retained:
  - discovery retained
  - availability retained
  - commandes non retained
- Garder le namespace strict `jeedom2ha/*`.
- Ne pas polluer les payloads avec des champs HA non documentes ou avec des valeurs non supportees.

### Latest Technical Information (veille ciblee)

- Les documentations officielles Home Assistant `light.mqtt`, `cover.mqtt` et `switch.mqtt` supportent toutes:
  - `availability` sous forme de liste de topics
  - `availability_mode`
  - `payload_available` / `payload_not_available`
- Pour le cas Story 3.3, la combinaison recommandee est:
  - topic pont global
  - topic local entite
  - `availability_mode = all`
- La page officielle PyPI indique toujours `paho-mqtt 2.1.0` comme version stable visible. Le code actuel gere deja la compatibilite callbacks 2.x; aucune mise a jour de dependance n'est requise pour cette story.
- Le core Jeedom reference explicitement des statuts d'equipement `timeout` et `lastCommunication` dans `eqLogic.class.php`; ces statuts doivent etre privilegies face a des heuristiques plugin-specifiques.

### File Structure Requirements

- Changements principaux attendus:
  - `core/class/jeedom2ha.class.php`
  - `resources/daemon/models/topology.py`
  - `resources/daemon/models/mapping.py`
  - `resources/daemon/discovery/publisher.py`
  - `resources/daemon/transport/http_server.py`
  - `resources/daemon/sync/command.py`
- Tests probables a etendre:
  - `tests/unit/test_topology.py`
  - `tests/unit/test_discovery_publisher.py`
  - `tests/unit/test_http_server.py`
  - `tests/unit/test_mqtt_bridge.py`
  - `resources/daemon/tests/unit/test_command_sync.py`
- Nouveau module optionnel:
  - un petit helper `resources/daemon/sync/availability.py` est acceptable si et seulement s'il reduit la duplication entre discovery, `/action/sync` et le gating commande

### Git Intelligence Summary

- Les derniers commits fonctionnels du repo suivent un pattern stable:
  - petit changement cible dans `publisher`, `http_server`, `main.py` ou `command.py`
  - renforcement de tests unitaires/integration precis
  - mise a jour des artefacts BMAD en fin de story
- Story 3.3 doit suivre le meme style: changement chirurgical, pas de refonte globale discovery/lifecycle.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3: Synchronisation & Pilotage]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3: Disponibilité du pont et des entités quand l'information est fiable]
- [Source: _bmad-output/planning-artifacts/prd.md#Contraintes Techniques du Domaine]
- [Source: _bmad-output/planning-artifacts/prd.md#Cycle de Vie des Entités]
- [Source: _bmad-output/planning-artifacts/prd.md#Exigences Non-Fonctionnelles]
- [Source: _bmad-output/planning-artifacts/architecture.md#4. Process Patterns, Fallbacks & State Safety]
- [Source: _bmad-output/planning-artifacts/architecture.md#6. Lifecycle Consistency Rules]
- [Source: _bmad-output/project-context.md#MQTT Discovery Home Assistant]
- [Source: _bmad-output/project-context.md#Critical Don't-Miss Rules]
- [Source: _bmad-output/implementation-artifacts/3-2-pilotage-ha-jeedom-avec-confirmation-honnete-detat.md]
- [Source: _bmad-output/implementation-artifacts/3-2-bis-bootstrap-runtime-apres-restart-daemon.md]
- [Source: core/class/jeedom2ha.class.php]
- [Source: resources/daemon/models/topology.py]
- [Source: resources/daemon/models/mapping.py]
- [Source: resources/daemon/discovery/publisher.py]
- [Source: resources/daemon/transport/http_server.py]
- [Source: resources/daemon/transport/mqtt_client.py]
- [Source: resources/daemon/sync/command.py]
- [Source: tests/unit/test_discovery_publisher.py]
- [Source: tests/unit/test_mqtt_bridge.py]
- [Source: tests/unit/test_topology.py]
- [Source: resources/daemon/tests/unit/test_command_sync.py]
- [Source: https://www.home-assistant.io/integrations/light.mqtt/]
- [Source: https://www.home-assistant.io/integrations/cover.mqtt/]
- [Source: https://www.home-assistant.io/integrations/switch.mqtt/]
- [Source: https://www.home-assistant.io/docs/mqtt/]
- [Source: https://pypi.org/project/paho-mqtt/]
- [Source: https://raw.githubusercontent.com/jeedom/core/master/core/class/eqLogic.class.php]

## Dev Agent Record

### Agent Model Used

Codex GPT-5 (dev-story workflow)

### Debug Log References

- Preflight Git execute et valide sur la branche `codex/story-3-3-disponibilite-fiable` avant toute implementation.
- `sprint-status.yaml` passe de `ready-for-dev` a `in-progress` au demarrage de l'implementation.
- Story 3.3 implementee uniquement dans le worktree dedie, sans modification metier dans le clone principal.
- Couverture locale executee:
  - `python3 -m pytest tests/unit/test_discovery_publisher.py tests/unit/test_http_server.py resources/daemon/tests/unit/test_command_sync.py -q` -> `64 passed`
  - `python3 -m pytest -q` -> `253 passed`
- Reprise suite code review `changes requested`: corrections ciblees sur schema HA availability, gestion echec publish local retained, et regression downgrade `local -> bridge-only`.
- Reprise blocker review additionnel (cleanup local retained perdu hors connexion broker): ajout d'une file de cleanup differe en runtime et replay au sync reconnecte.
- Validation post-fix blocker:
  - `python3 -m pytest tests/unit/test_http_server.py -q` -> `16 passed`
  - `python3 -m pytest -q` -> `255 passed`

### Completion Notes List

- Ajout d'un contrat availability centralise (`resources/daemon/models/availability.py`) pour eliminer les chaines dupliquees (`online`, `offline`, topic pont, topic local).
- Extension de `PublicationDecision` avec metadata availability dediee, en conservant strictement le sens existant de `active_or_alive`.
- Extension de `getFullTopology()` PHP pour exposer un bloc `status` minimal (`timeout`, `lastCommunication`) sans heuristique plugin-specifique.
- Normalisation conservative dans `topology.py`: `timeout=1 -> offline`, `timeout=0 -> online`, sinon `unknown` et bridge-only.
- `DiscoveryPublisher` adapte en bridge-only ou compose (`availability` + `availability_mode=all`) sans toucher aux topics de commande/etat existants.
- `/action/sync` etendu pour publier le topic local retained uniquement quand le signal est fiable, nettoyer ce topic lors d'un downgrade bridge-only et lors d'un unpublish.
- `CommandSynchronizer` etendu pour rejeter une commande avec `reason_code=entity_unavailable` quand l'entite est explicitement `offline` localement.
- Separation unavailable vs unpublish conservee; aucun basculement vers device discovery; aucune dependance introduite sur `resources/daemon/sync/state.py`.

### File List

- _bmad-output/implementation-artifacts/3-3-disponibilite-du-pont-et-des-entites-quand-linformation-est-fiable.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- core/class/jeedom2ha.class.php
- resources/daemon/discovery/publisher.py
- resources/daemon/models/availability.py
- resources/daemon/models/mapping.py
- resources/daemon/models/topology.py
- resources/daemon/sync/command.py
- resources/daemon/transport/http_server.py
- resources/daemon/transport/mqtt_client.py
- resources/daemon/tests/unit/test_command_sync.py
- tests/unit/test_discovery_publisher.py
- tests/unit/test_http_server.py
- tests/unit/test_topology.py

### Change Log

- 2026-03-16: Story passee en `in-progress` et implementation chirurgicale du contrat availability local (`jeedom2ha/{eq_id}/availability`) sans changement de scope.
- 2026-03-16: Ajout du module `models/availability.py` + integration dans `mapping`, `publisher`, `http_server`, `command` et centralisation des constantes availability dans `mqtt_client`.
- 2026-03-16: Extension de la topologie PHP/Python pour transporter et normaliser les signaux standards Jeedom (`timeout`, `lastCommunication`) en bridge-only vs compose.
- 2026-03-16: Ajout/ajustement des tests unitaires Story 3.3 (publisher, topology, http_server, command sync) et validation complete locale (`251 passed`).
- 2026-03-16: Corrections post-review: `availability` conforme schema officiel HA (liste d'objets `topic`), retrait de l'ignorance d'echec publish local (decision runtime safe `local_availability_publish_failed`), ajout du test de regression downgrade `local -> bridge-only` avec nettoyage retained obligatoire.
- 2026-03-16: Story passee en `review` apres materialisation des changements en commits Git et revalidation complete (`253 passed`).
- 2026-03-16: Fix blocker review final: persistance + replay du cleanup differe `jeedom2ha/{eq_id}/availability` quand downgrade `local -> bridge-only` ou unpublish survient broker deconnecte; ajout de 2 tests de regression dedies; validation locale complete (`255 passed`).
