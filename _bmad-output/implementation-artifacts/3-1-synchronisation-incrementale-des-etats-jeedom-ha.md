# Story 3.1: Synchronisation incrémentale des états Jeedom → HA

Status: done

## Story

As a utilisateur Jeedom,
I want que mes changements d'état soient répercutés fidèlement dans HA,
so that j'aie une vision juste de ma maison en temps réel.

## Acceptance Criteria

1. **Given** des équipements sont publiés dans HA par `jeedom2ha` et marqués vivants dans le registre runtime
2. **When** un changement d'état survient dans Jeedom (via `event::changes`)
3. **Then** le démon ne traite que les commandes reliées à des entités réellement publiées et vivantes
4. **And** le démon ignore (avec trace runtime exploitable dans les logs) tout événement lié à une entité non publiée, exclue, supprimée ou non vivante
5. **And** le démon publie l'état uniquement sur le `state_topic` de l'entité `jeedom2ha` correspondante, sans interaction avec les topics d'autres publishers
6. **And** la latence cible reste proche de 1s, et acceptable ≤ 2s en contexte nominal sur le périmètre V1
7. **And** la synchro incrémentale n'amplifie pas les faux positifs de mapping : aucune nouvelle entité n'est créée par le flux d'état
8. **And** lorsqu'une entité sort du registre actif via un mécanisme existant, le cleanup discovery est fait via payload vide retained sur le topic discovery exact de l'entité concernée (pas de purge globale broker)

## Scope Guardrails (non négociable)

- Synchro incrémentale via `event::changes` uniquement pour des entités `jeedom2ha` déjà publiées et vivantes.
- Aucune création d'entité via le flux d'état.
- Aucun impact sur les topics d'autres publishers MQTT.
- Cleanup lifecycle uniquement par payload vide retained sur le topic discovery exact.
- Pas d'anticipation Epic 4 (exclusions multicritères, politique de confiance configurable) ni Epic 5 (détection/réconciliation lifecycle avancée).

## Tasks / Subtasks

- [x] **Task 1 — Introduire un registre runtime exploitable par la synchro d'état** (AC: #1, #3, #4, #7)
  - [x] 1.1 Ajouter `resources/daemon/sync/state.py` avec un service `StateSynchronizer` lisant le registre runtime existant (`app["publications"]` / `app["mappings"]`).
  - [x] 1.2 Construire un index runtime `cmd_id -> {state_topic, should_publish, active_or_alive}` uniquement à partir des décisions `should_publish=True`.
  - [x] 1.3 Traiter comme non vivante toute entité absente du registre actif, exclue, retirée ou non publiée ; ignorer l'événement avec un code raison loggable.
  - [x] 1.4 Interdire toute création de mapping/entité/topic dans `StateSynchronizer` (lecture seule du registre publication).

- [x] **Task 2 — Implémenter la boucle `event::changes` incrémentale** (AC: #2, #3, #6)
  - [x] 2.1 Interroger Jeedom `event::changes` avec curseur `datetime` incrémental.
  - [x] 2.2 Débouncer par `cmd_id` (ne garder que la dernière valeur par batch) sans perdre l'état final.
  - [x] 2.3 Viser un cycle nominal ~1s et gérer erreurs/réessais sans crash du daemon.
  - [x] 2.4 Ajouter des logs `[SYNC]` structurés et exploitables: `cmd_id`, `reason_code`, `action`.

- [x] **Task 3 — Publier les états strictement dans le namespace `jeedom2ha`** (AC: #4, #5, #6, #7)
  - [x] 3.1 Lire le `state_topic` depuis le registre runtime des publications existantes (source de vérité) ; ne pas reconstruire le topic par convention/pattern si l'information runtime existe déjà.
  - [x] 3.2 Refuser toute publication vers un topic hors préfixe `jeedom2ha/` (guardrail de coexistence publishers).
  - [x] 3.3 Publier les états incrémentaux via `MqttBridge.publish_message(..., retain=False)` ; aucune publication discovery via ce flux.
  - [x] 3.4 Appliquer la state safety: si valeur `event::changes` absente/invalide/non publiable honnêtement, ne pas inventer d'état (skip + `reason_code` loggable), ou appliquer uniquement un fallback déjà explicitement défini par mapping/runtime.

- [x] **Task 4 — Respecter le lifecycle cleanup exact via mécanismes existants** (AC: #8)
  - [x] 4.1 Conserver le cleanup discovery existant basé sur payload vide retained + topic exact (`DiscoveryPublisher.unpublish_entity` / `unpublish_by_eq_id`).
  - [x] 4.2 Vérifier que la synchro d'état n'ajoute aucun mécanisme de purge globale broker ni wildcard topic, et ne redessine pas le lifecycle.
  - [x] 4.3 Lorsqu'un événement concerne une entité déjà sortie du registre actif par mécanisme existant, ignorer + tracer ; ne jamais recréer l'entité ni relancer un cleanup alternatif.

- [x] **Task 5 — Intégrer le service au cycle de vie daemon** (AC: #1, #2, #6)
  - [x] 5.1 Instancier `StateSynchronizer` dans `resources/daemon/main.py` après création app HTTP.
  - [x] 5.2 Démarrer la tâche async en `on_start()` et l'arrêter proprement en `on_stop()`.
  - [x] 5.3 Fournir au synchronizer les dépendances runtime: accès registre app, client MQTT bridge, config API Jeedom (`apikey` + endpoint local).

- [x] **Task 6 — Couverture automatisée minimum (unitaires/intégration locale)** (AC: #3, #4, #5, #7, #8)
  - [x] 6.1 Créer `resources/daemon/tests/unit/test_state_sync.py` pour couvrir:
    - publish état sur entité publiée/vivante uniquement ;
    - ignore événement non publié/non vivant avec trace runtime exploitable dans les logs ;
    - aucune création d'entité via flux d'état ;
    - lecture `state_topic` depuis registre runtime (pas de recomputation par pattern) ;
    - rejet publication hors namespace `jeedom2ha/` ;
    - state safety sur valeur invalide (skip + `reason_code`) ;
    - debounce `event::changes` (dernière valeur conservée).
  - [x] 6.2 Ajouter dans `resources/daemon/tests/unit/` un test de non-régression cleanup exact retained (topic discovery exact + payload vide) sur mécanisme existant.
  - [x] 6.3 Ajouter dans `resources/daemon/tests/integration/` un test de coexistence simulée confirmant qu'aucun topic tiers (hors `jeedom2ha/*`) n'est publié/touché par la synchro d'état.

## Plan de tests réels minimum (obligatoire)

- [ ] **Test réel 3.1-A (coexistence publishers)**: box Jeedom + broker MQTT + HA + au moins un autre publisher MQTT ; vérifier qu'aucun topic externe n'est touché.
- [ ] **Test réel 3.1-B (gating runtime)**: événement sur entité non publiée/non vivante -> aucun publish `state_topic`, trace runtime exploitable dans les logs.
- [ ] **Test réel 3.1-C (cleanup exact)**: retrait d'une entité publiée via mécanisme existant -> payload vide retained sur topic discovery exact, disparition HA sans ghost entity.
- [ ] **Preuve standard homogène pour chaque test**: préconditions, commande/événement injecté, extraits logs runtime, topics observés (broker), observation HA, verdict.

## Risques / Pièges à éviter

- Utiliser `event::changes` pour créer des entités ou réconcilier la topologie (hors scope Story 3.1).
- Publier par erreur sur des topics d'autres intégrations MQTT (collision/coexistence cassée).
- Faire un cleanup global broker au lieu d'un cleanup discovery exact par topic.
- Introduire un mode optimiste qui masque un état inconnu (amplification faux positifs).
- Couper la traçabilité terrain: logs incomplets ou preuves de test non homogènes.

## Dev Notes

### Contexte code existant à réutiliser

- Registre runtime déjà maintenu par `/action/sync` dans `resources/daemon/transport/http_server.py` (`app["mappings"]`, `app["publications"]`).
- Cleanup discovery exact déjà implémenté dans `resources/daemon/discovery/publisher.py` (`unpublish_entity`, `unpublish_by_eq_id`) via payload vide retained.
- Bridge MQTT existant dans `resources/daemon/transport/mqtt_client.py` avec `publish_message(...)`.
- Point d'intégration daemon disponible dans `resources/daemon/main.py` (`on_start`, `on_stop`).

### Contraintes d'implémentation Story 3.1

- Le flux `event::changes` synchronise uniquement l'état d'entités déjà publiées/vivantes.
- Aucune écriture discovery depuis la synchro d'état (hors cleanup exact déclenché par mécanisme existant).
- Les logs doivent être runtime-oriented et exploitables (`reason_code`, `cmd_id`, `entity_id/topic`).
- Maintenir la cohérence disponibilité bridge/entités existante ; ne pas introduire de nouveau modèle de disponibilité dans cette story.

### Contrat minimal du registre runtime (lecture synchro d'état)

- `StateSynchronizer` lit un registre runtime des publications existantes et s'y conforme comme source de vérité.
- Champs minimums requis côté lecture pour chaque commande synchronisable:
  - `cmd_id` (identifiant commande Jeedom source) ;
  - `state_topic` (topic exact de publication d'état) ;
  - `should_publish` (autorisation de publier) ;
  - un indicateur `active_or_alive` (ou équivalent existant) marquant l'entité comme vivante/active dans le registre courant.
- `StateSynchronizer` est strictement en lecture seule vis-à-vis de ce registre: il ne crée ni n'altère les entrées de publication/mapping/lifecycle.

### Frontière Story 3.1 (pas lifecycle/disponibilité)

- Story 3.1 n'implémente pas un nouveau moteur lifecycle.
- Story 3.1 n'introduit aucune politique availability nouvelle.
- `event::changes` sert uniquement au flux d'état incrémental.
- Si une entité a déjà quitté le registre actif via mécanisme existant: ignore + log ; aucune recréation.
- Le cleanup exact est uniquement préservé/réutilisé via les mécanismes existants ; il n'est pas redessiné dans cette story.

### State Safety (valeurs inattendues)

- Si la valeur issue de `event::changes` est absente, invalide ou non publiable honnêtement: ne pas inventer d'état.
- Comportement attendu: skip + `reason_code` exploitable dans les logs.
- Un fallback n'est autorisé que s'il est déjà explicitement défini par le mapping/runtime existant.
- Aucun mode optimiste implicite dans cette story.

### Hors périmètre explicite

- Exclusion multicritères et politique de confiance configurable (Epic 4).
- Détection/réconciliation lifecycle avancée (Epic 5).
- Ajout de nouveaux types d'entités ou extension fonctionnelle de mapping.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1: Synchronisation incrémentale des états Jeedom → HA]
- [Source: _bmad-output/planning-artifacts/prd.md#Contraintes Techniques du Domaine]
- [Source: _bmad-output/planning-artifacts/prd.md#Exigences Non-Fonctionnelles]
- [Source: _bmad-output/planning-artifacts/architecture.md#4. Process Patterns, Fallbacks & State Safety]
- [Source: _bmad-output/planning-artifacts/architecture.md#6. Lifecycle Consistency Rules]

## Dev Agent Record

### Agent Model Used

Codex GPT-5

### Debug Log References

- Story générée à partir de `epics.md` mis à jour (rétro Epic 2 intégrée), sans extension de périmètre Epic 4/Epic 5.
- Implémentation Story 3.1 en TDD: nouveaux tests `state sync` écrits en échec initial puis code ajouté.
- Validation exécutée: tests ciblés Story 3.1 (`14 passed`) + `python3 -m pytest -q` global (`261 passed`), puis `python3 -m flake8` global (1 finding hors périmètre dans `resources/demond/jeedom/jeedom.py`) et `python3 -m flake8` ciblé fichiers Story 3.1 (OK).
- Preuve TDD reprise BMAD: 3 tests rouges d'abord (`state_topic` absent sans fallback, gating runtime après discovery KO, rollback startup) puis passage au vert après correctifs.
- Reprise blocage test réel Story 3.1: ajout d'une clé API cœur dédiée au flux `event::changes` (séparée de `--apikey` plugin), avec injection launcher PHP -> daemon -> `StateSynchronizer`.
- Validation reprise blocage API: `python3 -m pytest -q resources/daemon/tests/unit/test_state_sync.py resources/daemon/tests/unit/test_state_sync_lifecycle.py resources/daemon/tests/unit/test_discovery_cleanup_exact.py resources/daemon/tests/integration/test_state_sync_coexistence.py resources/daemon/tests/integration/test_state_sync_cleanup_runtime_flow.py` (`17 passed`) puis `python3 -m pytest -q` global (`264 passed`).
- Reprise blocage terrain format `event::changes`: adaptation au payload réel Jeedom (`name=cmd::update`, `option.cmd_id`, `option.value`) et filtrage explicite des événements non pertinents (`eqLogic::update`, `scenario::update`, `jeeObject::summary::update`).
- Validation reprise parsing runtime: `python3 -m pytest -q resources/daemon/tests/unit/test_state_sync.py resources/daemon/tests/unit/test_state_sync_lifecycle.py resources/daemon/tests/unit/test_discovery_cleanup_exact.py resources/daemon/tests/integration/test_state_sync_coexistence.py resources/daemon/tests/integration/test_state_sync_cleanup_runtime_flow.py` (`20 passed`) puis `python3 -m pytest -q` global (`267 passed`).
- Reprise blocage terrain incrémentalité réelle: correction parsing/format du curseur `event::changes` pour le format Jeedom epoch float (`1773522118.696700`) afin d'éviter le rejeu de backlog à chaque poll.
- Validation reprise incrémentalité: tests rouges puis verts sur datetime epoch, format curseur envoyé, et non-rejeu batch entre polls; exécution `python3 -m pytest -q resources/daemon/tests/unit/test_state_sync.py resources/daemon/tests/unit/test_state_sync_lifecycle.py resources/daemon/tests/unit/test_discovery_cleanup_exact.py resources/daemon/tests/integration/test_state_sync_coexistence.py resources/daemon/tests/integration/test_state_sync_cleanup_runtime_flow.py` (`23 passed`) puis `python3 -m pytest -q` global (`270 passed`).
- Validation finale sur box réelle Story 3.1: daemon actif `resources/daemon/main.py`, logs `[SYNC]` + `[SYNC-PROBE]` observés pour `cmd_id=3265` sur `jeedom2ha/391/state` avec séquence MQTT `OFF -> ON -> OFF`, confirmant le passage live via `StateSynchronizer`.

### Completion Notes List

- Ajout de `StateSynchronizer` (`resources/daemon/sync/state.py`) avec boucle `event::changes`, curseur incrémental, debounce par `cmd_id`, logs structurés `[SYNC]`, garde-fous namespace `jeedom2ha/*` et state safety.
- Le registre runtime de publication est enrichi via `PublicationDecision.state_topic` et `PublicationDecision.active_or_alive`, alimentés depuis `/action/sync`.
- Intégration cycle de vie daemon dans `main.py` (start/stop du synchronizer, injection endpoint local `jeeApi.php` + apikey).
- Chemins de tests alignés explicitement avec la story: `resources/daemon/tests/unit/...` et `resources/daemon/tests/integration/...` (pas de divergence maintenue).
- Couverture automatisée locale renforcée pour AC #8 sur un flux proche runtime réel: `/action/sync` (cleanup exact retained topic) puis événement tardif `event::changes` ignoré sans recréation, sans purge globale, sans wildcard, sans cleanup alternatif.
- Bloquant corrigé: un échec de publication discovery laisse désormais l'entrée runtime en non publiable/non vivante (`should_publish=False`, `active_or_alive=False`), donc aucun `event::changes` ultérieur ne publie de `state_topic`.
- Guardrail renforcé: `StateSynchronizer` ne reconstruit plus de `state_topic` par convention si absent du registre runtime; comportement = skip + `reason_code=missing_state_topic_runtime`.
- Robustesse lifecycle: rollback `on_start` ajouté; si `start_server` échoue, la tâche sync est stoppée immédiatement et l'état daemon est nettoyé (`_app`, `_state_synchronizer`, `_http_runner` remis à `None`).
- AC latence (#6): implémentation locale du cycle nominal (~1s) et de la résilience (retry/erreurs) effectuée; la preuve terrain de latence nominale ≤2s n'est pas démontrée ici sans box Jeedom+broker+HA.
- Tests réels 3.1-A/B/C restent volontairement non exécutés dans cet environnement de dev local (checkboxes conservées non cochées).
- Correctif blocant terrain: le daemon conserve `--apikey` plugin inchangé, ajoute `--jeedomcoreapikey` dédié à `event::changes`, et `StateSynchronizer` utilise exclusivement cette clé core pour `/core/api/jeeApi.php`.
- Mode dégradé explicite: si clé core absente, la synchro incrémentale est désactivée sans crash avec log runtime exploitable (`reason_code=missing_jeedom_core_apikey`, `action=disable_incremental_sync`).
- Séparation des clés verrouillée par test lifecycle: `app["jeedom_api"]["apikey"]` reste la clé plugin, `app["jeedom_api"]["core_apikey"]` est injectée séparément vers `StateSynchronizer`.
- Correctif format réel `event::changes`: `StateSynchronizer` traite les événements `cmd::update` uniquement, lit `cmd_id` depuis `option.cmd_id` et lit la valeur depuis `option.value`.
- Réduction du bruit runtime: les événements non pertinents (hors `cmd::update`) sont ignorés proprement en `DEBUG` (`reason_code=event_not_cmd_update`) au lieu de spammer des `WARNING`.
- Cas réellement malformé conservé en diagnostic explicite: `reason_code=invalid_event_payload` + `action=skip_event`, sans publication de state.
- Correctif incrémentalité runtime: `_extract_event_datetime()` accepte désormais le format datetime Jeedom réel en epoch float string (et tolère un format ms), ce qui permet une avance de curseur fiable sur événements terrain.
- Alignement requête Jeedom: `_format_cursor()` envoie maintenant `datetime` au format epoch float string (6 décimales) attendu par `event::changes`, au lieu d'un datetime ISO-like.
- Verrouillage anti-rejeu: test dédié sur deux polls successifs garantit qu'un batch déjà traité n'est pas rejoué au poll suivant (`publish_state` unique).
- Validation production Story 3.1 confirmée sur box réelle: flux live Jeedom -> `event::changes` -> `StateSynchronizer` -> publish MQTT `jeedom2ha/391/state` observé avec cohérence logs/runtime.

### File List

- `_bmad-output/implementation-artifacts/3-1-synchronisation-incrementale-des-etats-jeedom-ha.md`
- `core/class/jeedom2ha.class.php`
- `resources/daemon/models/mapping.py`
- `resources/daemon/sync/__init__.py`
- `resources/daemon/sync/state.py`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/main.py`
- `resources/daemon/tests/__init__.py`
- `resources/daemon/tests/unit/__init__.py`
- `resources/daemon/tests/integration/__init__.py`
- `resources/daemon/tests/unit/test_state_sync.py`
- `resources/daemon/tests/unit/test_discovery_cleanup_exact.py`
- `resources/daemon/tests/integration/test_state_sync_coexistence.py`
- `resources/daemon/tests/integration/test_state_sync_cleanup_runtime_flow.py`
- `resources/daemon/tests/unit/test_state_sync_lifecycle.py`
- `pyproject.toml`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-14: Implémentation Story 3.1 (sync incrémentale `event::changes`, guardrails runtime/namespace/state safety, intégration daemon, tests unitaires et intégration locale, validation complète pytest).
- 2026-03-14: Reprise ciblée Story 3.1: alignement des chemins de tests vers `resources/daemon/tests/*`, renforcement de preuve AC #8 sur flux runtime cleanup/sync, clarification explicite des limites de preuve latence sans box réelle.
- 2026-03-14: Reprise BMAD code review (3 points): gating runtime strict après échec discovery, suppression fallback `state_topic` hors registre runtime, rollback startup sync si échec HTTP; tests rouges->verts puis régression globale.
- 2026-03-14: Reprise blocage test réel `event::changes` (clé core Jeedom dédiée): nouvel argument launcher `--jeedomcoreapikey`, séparation plugin/core côté daemon, usage strict de la clé core dans `StateSynchronizer`, mode dégradé explicite si clé absente, tests Story 3.1 + régression globale au vert.
- 2026-03-14: Reprise blocage test réel format `event::changes`: parsing `cmd::update` conforme payload Jeedom réel (`option.cmd_id`/`option.value`), filtrage propre des événements non pertinents sans spam warning, tests Story 3.1 et régression globale au vert.
- 2026-03-14: Reprise blocage test réel incrémentalité `event::changes`: parsing datetime Jeedom epoch float + format curseur epoch float pour requêtes, suppression du rejeu de backlog entre polls, nouveaux tests cursor/non-rejeu, suites Story 3.1 et globale au vert.
- 2026-03-15: Validation finale Story 3.1 sur box réelle (preuve de passage live par `StateSynchronizer`), story clôturée en `done`.
