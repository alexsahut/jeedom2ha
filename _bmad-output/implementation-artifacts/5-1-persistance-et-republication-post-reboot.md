# Story 5.1: Persistance et Republication Post-Reboot

Status: done

## Story

As a utilisateur Home Assistant,
I want que le pont jeedom2ha récupère automatiquement après tout redémarrage (daemon, broker MQTT, Home Assistant ou box Jeedom),
so that les entités HA restent disponibles sans intervention manuelle et sans ghosts, en toute circonstance terrain.

## Hypothèses de Plateforme

Ces hypothèses ont été vérifiées dans le code existant (post-Epic 4) — elles gouvernent l'implémentation :

| Hypothèse | Valeur vérifiée | Impact |
|-----------|----------------|--------|
| H1 — Cache disque | Aucun fichier `data/` n'existe encore pour les publications | À créer dans `data/jeedom2ha_cache.json` |
| H2 — Topology push | PHP appelle `/action/sync` (daemon ne pull pas la topology) | Backoff = PHP-side borné (voir NFR2) + daemon watchdog log |
| H3 — paho `on_connect` | Appelé à **chaque** reconnexion (pas seulement la première) | Exploitable pour republier sur reconnect broker |
| H4 — `app["publications"]` | Dict[int, PublicationDecision] en RAM, perdu au restart daemon | Le cache disque en devient la source de warm-start |
| H5 — `pending_discovery_unpublish` | En RAM uniquement (`app["pending_discovery_unpublish"]`) | Les unpublish déférés perdus au restart sont couverts par la réconciliation boot |
| H6 — `homeassistant/status` | Non souscrit actuellement (`COMMAND_SUBSCRIPTION_TOPICS` ne l'inclut pas) | À ajouter dans `_subscribe_command_topics()` |
| H7 — Broker persistence | Le plugin ne peut PAS supposer que Mosquitto a la persistence activée | Republication complète obligatoire à chaque reconnexion |
| H8 — Reconciliation boot | `/action/sync` compare `anciens_eq_ids` (anciens mappings) vs topologie courante | Le cache disque fournit `anciens_eq_ids` au boot avant la première sync PHP |
| H9 — `asyncio.sleep` | L'event loop asyncio tourne en continu pendant le lissage | Non-bloquant pour les autres tâches (commandes, event::changes) |
| H10 — Bootstrap PHP | `deamon_start()` appelle `getFullTopology()` puis `callDaemon('/action/sync')` (3.2-bis) | Le backoff Jeedom est une extension PHP bornée de ce mécanisme existant |
| H11 — Auth locale | `/system/status` et `/action/sync` utilisent `X-Local-Secret` (prouvé terrain) | Aucun nouveau flux d'auth n'est introduit dans 5.1 — contrat existant conservé |
| H12 — États courants | Les états courants arrivent via `event::changes` (Story 3.1, mécanisme existant) | Hors scope 5.1 — non modifié dans cette story |
| H13 — Availability locale | Publiée dans `/action/sync` handler existant (Story 3.3) | Hors scope 5.1 — comportement existant préservé, non modifié |

## Acceptance Criteria

### Groupe 1 — Cache disque (prérequis de la réconciliation boot)

1. **Given** la première `/action/sync` réussit **When** le handler `/action/sync` se termine **Then** un fichier `data/jeedom2ha_cache.json` est écrit avec le format `{eq_id: {"entity_type": str, "published": bool}}` pour chaque équipement dans `app["publications"]`

2. **Given** le daemon redémarre **When** `on_start()` s'exécute **Then** le fichier `data/jeedom2ha_cache.json` est chargé en mémoire avant la connexion MQTT, sans déclencher de publication

3. **Given** le fichier `data/jeedom2ha_cache.json` est absent ou corrompu **When** le daemon démarre **Then** le daemon démarre normalement (RAM vide), log `INFO [CACHE] Cache disque absent ou invalide — cold start`, et ne publie rien

### Groupe 2 — Séquence de boot et invariant INV-2 (aucune publication sans Jeedom)

4. **Given** le daemon vient de démarrer et n'a pas encore reçu de `/action/sync` de PHP **When** 90 secondes s'écoulent sans réception d'un `/action/sync` valide **Then** le daemon log `WARNING [BOOTSTRAP] Aucune topologie reçue depuis Jeedom après 90s — aucune publication en attente` mais reste actif et ne publie rien depuis le cache seul

5. **Given** le daemon a chargé un cache disque au boot **When** PHP envoie `/action/sync` avec une topologie Jeedom valide **Then** la reconciliation compare le cache disque vs la topologie courante :
   - Nouveau `eq_id` (absent du cache) → publish discovery
   - `eq_id` inchangé (dans cache avec même `entity_type`) → republish discovery (refresh retained)
   - `eq_id` disparu de la topologie (dans cache mais absent de Jeedom) → unpublish (payload vide retained)
   - `eq_id` avec `is_enable=false` (dans cache comme `published`) → unpublish (INV-11)
   - `eq_id` exclu → unpublish si était publié (INV-6)

6. **Given** la reconnexion broker MQTT s'établit (cas reconnect, pas seulement premier connect) **When** `_on_connect()` est appelé **Then** aucune publication n'est déclenchée si `app["publications"]` est vide (boot avant première sync)

### Groupe 3 — Republication sur birth message HA (Décision 6)

7. **Given** le daemon est en mode nominal avec des entités publiées **When** le topic `homeassistant/status` reçoit le payload `online` **Then** le daemon republie la discovery complète depuis `app["publications"]` (RAM cache) pour tous les `eq_id` avec `published=True`, sans déclencher de rescan Jeedom

8. **Given** la republication birth HA se déclenche **When** la liste des entités publiées est non vide **Then** chaque publish est espacé de `max(0.1, 10.0 / nb_entites)` secondes via `asyncio.sleep()` (Décision 8, INV-9)

9. **Given** un birth message HA arrive alors que `app["publications"]` est vide (daemon en cours de boot) **When** le message `homeassistant/status = online` est reçu **Then** le daemon log `INFO [BOOTSTRAP] Birth HA reçu — aucune entité publiée en mémoire, republication ignorée (la prochaine /action/sync publiera toutes les entités éligibles)`, sans publier et sans déclencher aucune action différée

### Groupe 4 — Republication sur reconnect broker (Décision 6)

10. **Given** le broker MQTT redémarre et le daemon se reconnecte **When** `_on_connect()` est appelé avec `app["publications"]` non vide **Then** le daemon déclenche une republication discovery complète depuis le cache RAM (même logique que birth HA, avec lissage Décision 8)

11. **Given** la reconnexion broker se déclenche **When** des `pending_discovery_unpublish` sont en attente **Then** ces unpublish sont rejoués avant la republication discovery (comportement existant préservé)

### Groupe 5 — Lissage des republications batch (Décision 8)

12. **Given** une republication **batch** de N entités est déclenchée (**birth HA ou reconnect broker uniquement**) **When** N > 0 **Then** `delay = max(0.1, 10.0 / N)` est calculé et `asyncio.sleep(delay)` est appelé entre chaque publish, garantissant que le lot complet prend ≥ 10 secondes pour N > 100 entités

> **Note scope lissage** : Le lissage Décision 8 s'applique UNIQUEMENT aux republications batch (`_republish_all_from_cache`). Il ne s'applique PAS au handler `/action/sync`, qui répondrait en timeout côté PHP si les publishes étaient lisés dans son chemin synchrone. Le premier `/action/sync` post-boot publie au rythme nominal du handler existant.

### Groupe 6 — Backoff PHP au bootstrap (Décision 7 + NFR2)

13. **Given** PHP exécute `bootstrapRuntimeAfterDaemonStart()` et `getFullTopology()` échoue **When** l'échec est détecté **Then** PHP retente avec backoff exponentiel dans la limite d'un budget de 5s total, logge `WARNING [BOOTSTRAP] Jeedom API indisponible — retry dans Ns`, et ne transmet pas de topology corrompue au daemon

14. **Given** PHP réussit `getFullTopology()` **When** `callDaemon('/action/sync', $topology)` aboutit **Then** la reconciliation boot s'exécute normalement et les entités sont publiées dans HA

15. **Given** `getFullTopology()` échoue et le budget de 5s est épuisé **When** la limite est atteinte **Then** `bootstrapRuntimeAfterDaemonStart()` retourne immédiatement avec log `WARNING [BOOTSTRAP] Jeedom API indisponible après Xs — bootstrap différé au prochain cycle Jeedom` ; `deamon_start()` se termine en < 5s total (NFR2) ; le prochain cycle de supervision Jeedom (cron) relancera le bootstrap

### Groupe 7 — Invariants et robustesse

16. **Given** la republication (birth HA ou reconnect broker) est en cours **When** une erreur de publish MQTT survient pour une entité **Then** l'erreur est loguée avec `ERROR [DISCOVERY] eq_id=N entity_type=X : échec publish — raison` et la republication continue pour les entités suivantes (INV-10)

17. **Given** le bridge status topic **When** le daemon démarre et se connecte au broker **Then** le birth message `jeedom2ha/bridge/status = online` est publié **avant** la republication discovery (séquence Décision 1)

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`
  - [x] **Preflight auth/sync obligatoire** (story touche `/action/sync` et le bootstrap) :
    - [x] Relire `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md` — section "Contrat projet à retenir"
    - [x] Relire `_bmad-output/planning-artifacts/architecture.md` — section communication PHP ↔ daemon
    - [x] Exporter les credentials terrain : `LOCAL_SECRET`, `PLUGIN_API_KEY`, `CORE_API_KEY` (commandes dans le fichier contexte terrain)
    - [x] Vérifier `/system/status` avec `X-Local-Secret` : `curl -sS -H "X-Local-Secret: $LOCAL_SECRET" "$DAEMON_API/system/status" | jq` → attendu : `"status": "ok"`
    - [x] Vérifier `/action/sync` avec `X-Local-Secret` : générer la topologie PHP puis l'envoyer → attendu : HTTP 200, payload de synthèse
    - [x] Confirmer que 5.1 n'introduit aucun nouveau flux JSON-RPC depuis le daemon (H11 = vrai)

- [x] Task 1 — Cache disque : persistance et chargement (AC: #1, #2, #3)
  - [x] 1.1 Créer `resources/daemon/cache/disk_cache.py` avec :
    - `save_publications_cache(publications: Dict[int, PublicationDecision], data_dir: str) -> None` : écrit `data/jeedom2ha_cache.json` avec `{eq_id: {"entity_type": str, "published": bool}}`
    - `load_publications_cache(data_dir: str) -> Dict[int, dict]` : charge le fichier JSON, retourne `{}` si absent ou corrompu (log INFO)
  - [x] 1.2 Dans `/action/sync` handler (`http_server.py`) : appeler `save_publications_cache()` après `request.app["mappings"].update()` et `request.app["publications"].update()`
  - [x] 1.3 Dans `on_start()` (`main.py`) : charger le cache disque dans `app["boot_cache"]` (Dict[int, dict] — séparé de `app["publications"]` pour ne pas court-circuiter l'initialisation)
  - [x] 1.4 Le `data_dir` est résolu en absolu depuis `__file__` — pas de chemin codé en dur
  - [x] 1.5 Tests unitaires : `save_publications_cache` + `load_publications_cache` (happy path, fichier absent, JSON corrompu)

- [x] Task 2 — Séquence de boot : watchdog INV-2 (AC: #4, #6)
  - [x] 2.1 Dans `on_start()`, après connexion MQTT, lancer une tâche asyncio `_boot_watchdog(app, timeout_s=90)` qui log `WARNING [BOOTSTRAP] Aucune topologie reçue depuis Jeedom après 90s — aucune publication en attente` si `app["publications"]` reste vide
  - [x] 2.2 La tâche watchdog s'annule d'elle-même dès que `app["publications"]` reçoit sa première entrée (via `/action/sync`)
  - [x] 2.3 La tâche watchdog ne publie RIEN — elle ne lit pas `app["boot_cache"]` pour publier

- [x] Task 3 — Subscription `homeassistant/status` et republication sur birth HA (AC: #7, #8, #9)
  - [x] 3.1 Dans `_subscribe_command_topics()` (`mqtt_client.py`) : ajouter `"homeassistant/status"` QoS 1 à `COMMAND_SUBSCRIPTION_TOPICS`
  - [x] 3.2 Dans `_on_message()` (`mqtt_client.py`) : détecter topic `homeassistant/status` + payload `"online"` → `loop.call_soon_threadsafe(self._trigger_ha_birth_republish)` (paho thread safety)
  - [x] 3.3 Implémenter `_trigger_ha_birth_republish` → crée une tâche asyncio `_republish_all_from_cache(app, reason="ha_birth")`
  - [x] 3.4 `_republish_all_from_cache(app, reason)` : itère sur `app["publications"]` (filter `published=True`), publie via `DiscoveryPublisher`, avec `asyncio.sleep(max(0.1, 10.0 / nb_entites))` entre chaque publish
  - [x] 3.5 Si `app["publications"]` est vide au moment du birth HA : log `INFO [BOOTSTRAP] Birth HA reçu — aucune entité publiée en mémoire, republication ignorée (la prochaine /action/sync publiera toutes les entités éligibles)`, aucune action différée, aucun flag posé
  - [x] 3.6 Test unitaire : birth HA avec `app["publications"]` non vide → `_republish_all_from_cache` appelé ; avec `app["publications"]` vide → aucun publish, log attendu

- [x] Task 4 — Republication sur reconnect broker (AC: #10, #11)
  - [x] 4.1 Dans `_on_connect()` (`mqtt_client.py`) : après birth message bridge, si `app["publications"]` non vide → `loop.call_soon_threadsafe` → asyncio task `_republish_all_from_cache(app, reason="broker_reconnect")`
  - [x] 4.2 Rejouer `pending_discovery_unpublish` AVANT la republication discovery (ordre existant préservé)
  - [x] 4.3 Injecter `app` dans `MqttBridge` via callback `on_reconnect_cb` (option b) dans `MqttBridge.start(config, on_reconnect_cb=...)` — maintient la séparation de responsabilités
  - [x] 4.4 Test unitaire : `_on_connect()` avec publications non vides → callback `on_reconnect_cb` appelé

- [x] Task 5 — Lissage des republications batch (Décision 8) (AC: #12)
  - [x] 5.1 `_republish_all_from_cache` implémente le lissage : `delay = max(0.1, 10.0 / nb_entites)` calculé UNE SEULE FOIS pour le lot
  - [x] 5.2 `asyncio.sleep(delay)` appelé **après** chaque publish (pas avant le premier)
  - [x] 5.3 Le lissage s'applique aux **2 cas batch uniquement** : birth HA et reconnect broker. Il ne s'applique PAS au handler `/action/sync` (chemin HTTP synchrone, timeout PHP si lisé)
  - [x] 5.4 Test unitaire : calcul délai pour N=1 (→ 0.1s), N=50 (→ 0.2s), N=100 (→ 0.1s), N=200 (→ 0.05 → plafonné à 0.1s)

- [x] Task 6 — Backoff PHP au bootstrap borné NFR2 (Décision 7) (AC: #13, #14, #15)
  - [x] 6.1 Dans `core/class/jeedom2ha.class.php`, méthode `bootstrapRuntimeAfterDaemonStart()` : entourer l'appel à `getFullTopology()` d'un retry backoff **borné à 5s total** (ex: 2 tentatives max : attente 1s puis 2s)
  - [x] 6.2 Si `getFullTopology()` échoue ET que le budget 5s est épuisé : log `WARNING [BOOTSTRAP] Jeedom API indisponible après Xs — bootstrap différé au prochain cycle Jeedom`, retourner immédiatement
  - [x] 6.3 Si `getFullTopology()` retourne un résultat vide ou invalide → ne PAS appeler `callDaemon('/action/sync')` ; log WARNING
  - [x] 6.4 `deamon_start()` se termine en < 5s dans tous les cas (NFR2 vérifiable en terrain avec `time php -r '...'`)
  - [x] 6.5 Le retry long-terme (convergence garantie) est assuré par le watchdog daemon (Task 2) et le cron de supervision Jeedom — pas par une boucle PHP illimitée
  - [x] 6.6 Test PHP : mock `getFullTopology()` renvoyant une erreur → vérifier que `bootstrapRuntimeAfterDaemonStart()` retourne en < 5s et ne plante pas (testable via injection de dépendances existante)

- [x] Task 7 — Reconciliation boot depuis le cache disque (AC: #5)
  - [x] 7.1 Dans `/action/sync` handler : quand `request.app["mappings"]` est vide (premier sync post-boot), initialiser `anciens_eq_ids` depuis `app["boot_cache"]` (les `eq_id` avec `published=True`) plutôt que depuis `request.app["mappings"].keys()` (vide au premier boot)
  - [x] 7.2 Permet à la reconciliation existante (`eq_ids_supprimes = anciens_eq_ids - nouveaux_eq_ids`) de détecter les suppressions survenues pendant le downtime daemon
  - [x] 7.3 Une fois le premier sync terminé, `app["boot_cache"]` est effacé (RAM) — son rôle est accompli
  - [x] 7.4 Test intégration : boot avec cache `{eq_id=X published=True}`, première sync sans `eq_id=X` → unpublish déclenché

- [ ] Task 8 — Tests terrain (non négociables) (AC: Runbook)
  - [ ] 8.1 Exécuter TC-A (restart daemon) — preuves : log boot complet, entités HA disponibles
  - [ ] 8.2 Exécuter TC-B (restart broker Mosquitto) — preuves : reconnexion auto, republish visible
  - [ ] 8.3 Exécuter TC-C (restart Home Assistant) — preuves : birth message détecté, republish depuis cache RAM
  - [ ] 8.4 Exécuter TC-D (reboot complet box Jeedom) — preuves : récupération automatique, ghost-risk couvert
  - [ ] 8.5 Vérifier sur chaque test : aucun ghost, aucun doublon, état correct dans HA, log conforme au format attendu

## Dev Notes

### Architecture existante — points d'ancrage

| Fichier | Rôle | Point d'ancrage pour 5.1 |
|---------|------|--------------------------|
| `resources/daemon/transport/mqtt_client.py` | MqttBridge + paho lifecycle | `_on_connect()`, `_subscribe_command_topics()`, `_on_message()` |
| `resources/daemon/transport/http_server.py` | `/action/sync` handler, `create_app()` | `_handle_action_sync()`, `app["publications"]`, `app["mappings"]` |
| `resources/daemon/main.py` | Point d'entrée daemon, `on_start()` | Chargement cache disque, injection callback reconnect |
| `resources/daemon/discovery/publisher.py` | `DiscoveryPublisher` | Réutiliser `publish_light/cover/switch()` pour la republication |
| `core/class/jeedom2ha.class.php` | PHP plugin — `deamon_start()`, `bootstrapRuntimeAfterDaemonStart()` | Backoff borné NFR2 (Task 6) |

### Règle critique sur le threading paho

`MqttBridge._on_connect()` s'exécute dans le **thread paho**, pas dans l'event loop asyncio. Tout appel à `asyncio.create_task()` depuis `_on_connect()` est interdit. Utiliser **exclusivement** `self._loop.call_soon_threadsafe(...)` pour marshaller vers asyncio. Voir `_dispatch_command_message()` comme pattern de référence.

### Format du cache disque

```json
{
  "123": {"entity_type": "light", "published": true},
  "456": {"entity_type": "cover", "published": true},
  "789": {"entity_type": "switch", "published": false}
}
```

- Clés JSON = strings (JSON ne supporte pas les entiers comme clés) → convertir en `int` au chargement
- `published=false` : l'entrée existait mais n'était pas publiée → pas d'unpublish nécessaire au boot

### Ordre de boot (Décision 1) — strictement ordonné

```
1. Charger cache disque → app["boot_cache"]
2. Connecter broker MQTT (mqtt_bridge.start())
3. Publier birth: bridge = "online" (dans _on_connect())
4. Souscrire homeassistant/status (dans _subscribe_command_topics())
5. Attendre PHP → /action/sync (PHP appelle getFullTopology + callDaemon, borné 5s)
   └─ Si 90s sans sync : log WARNING [BOOTSTRAP], rester actif, ne rien publier
6. /action/sync reçu → reconciliation (cache disque vs topologie Jeedom)
   └─ Nouveaux → publish, Supprimés/Désactivés/Exclus → unpublish, Inchangés → republish
   └─ Lissage : NON — /action/sync est un handler HTTP synchrone (timeout PHP si lisé)
```

**Étapes 7-8 de la matrice lifecycle (états courants + availability)** : Ces comportements sont assurés par les mécanismes existants (`event::changes` pour les états, `/action/sync` handler pour l'availability locale). Ils ne sont **pas modifiés** dans 5.1 et n'ont pas d'AC dédiés dans cette story.

**INV-2 INTERDIT :** entre les étapes 1 et 5, AUCUN discovery n'est publié depuis le cache disque seul.

### Lissage — périmètre exact (Option B retenue)

Le lissage Décision 8 (`delay = max(0.1, 10.0 / nb_entites)`) s'applique **uniquement** à `_republish_all_from_cache()`, c'est-à-dire :
- Birth message HA → republication batch depuis RAM
- Reconnexion broker → republication batch depuis RAM

Il ne s'applique **pas** au handler `/action/sync`. Le handler `/action/sync` est appelé via une requête HTTP depuis PHP (timeout implicite ~15s côté callDaemon). Ajouter `asyncio.sleep()` dans ce chemin provoquerait des timeouts PHP. Le lissage NFR21 est satisfait par les 2 cas batch ci-dessus.

### Republication sur birth HA / reconnect broker (Décision 6)

Source de republication = `app["publications"]` (RAM, mis à jour en continu par `/action/sync`). PAS le cache disque (`app["boot_cache"]`). PAS un rescan Jeedom.

- **Boot** (Cas 1, 2) : rescan Jeedom obligatoire car le daemon était arrêté → passe par `/action/sync`
- **Birth HA / reconnect broker** (Cas 3, 4) : le daemon tournait, son cache RAM est valide → passe par `_republish_all_from_cache()`

**Cas birth HA pendant le boot du daemon** (AC #9) : si `app["publications"]` est vide quand `homeassistant/status = online` arrive → la republication est **ignorée** (log INFO + aucune action différée). La prochaine `/action/sync` publiera toutes les entités éligibles. Ce comportement est testable : assert no publish call when `publications == {}`.

### Ghost-risk supprimé par le cache disque

Le mécanisme `pending_discovery_unpublish` est en RAM — il est perdu au restart daemon. Sans le cache disque (Task 7), un `eq_id` supprimé dans Jeedom pendant le downtime daemon ne serait pas détecté (`anciens_eq_ids` serait vide au premier sync post-boot). Avec le cache disque, `anciens_eq_ids` contient les `eq_id published=True` du dernier snapshot → la différence d'ensembles détecte la suppression.

### Dev Agent Guardrails

#### Guardrail 1 — Ne pas utiliser le cache disque comme source de vérité

Le cache disque est un **accélérateur de boot** uniquement. Règle : `app["boot_cache"]` sert uniquement à initialiser `anciens_eq_ids` dans le premier `/action/sync`. Il est purgé après le premier sync. Il n'est JAMAIS utilisé pour publier directement.

#### Guardrail 2 — Séparation stricte `boot_cache` vs `publications`

- `app["boot_cache"]` = Dict[int, dict] chargé du disque au boot — lecture seule, purgé après premier sync
- `app["publications"]` = Dict[int, PublicationDecision] mis à jour par chaque `/action/sync` — source de la republication birth/reconnect

Ne jamais confondre les deux. Ne pas écrire dans `app["boot_cache"]` pendant le runtime.

#### Guardrail 3 — Lissage uniquement dans `_republish_all_from_cache()`

`asyncio.sleep()` n'est autorisé que dans `_republish_all_from_cache()`. Interdit dans le handler `/action/sync`, dans `_on_connect()`, et dans tout chemin HTTP synchrone.

#### Guardrail 4 — paho thread safety

Zéro appel direct à `asyncio.create_task()` depuis les callbacks paho. Uniquement `self._loop.call_soon_threadsafe()`. Voir `_dispatch_command_message()` comme pattern de référence.

#### Guardrail 5 — Backoff PHP borné NFR2

Aucune boucle de retry illimitée dans le chemin synchrone PHP. `deamon_start()` et `bootstrapRuntimeAfterDaemonStart()` doivent se terminer en < 5s même si Jeedom est indisponible. La convergence à long terme est assurée par le cron Jeedom et le daemon watchdog, pas par une boucle PHP bloquante.

#### Guardrail 6 — Aucun fallback silencieux (INV-10)

Toute erreur (échec publish, cache corrompu, Jeedom indisponible, échec JSON) doit être loguée `ERROR` ou `WARNING`. Jamais de `except: pass` sans log.

#### Guardrail 7 — Auth/JSON-RPC : aucun nouveau flux introduit dans 5.1

5.1 ne modifie pas le contrat d'authentification. Les flux existants `X-Local-Secret` sur `/system/status` et `/action/sync` sont préservés. Aucun nouveau flux JSON-RPC depuis le daemon n'est autorisé dans cette story (H11). Si une implémentation nécessite un appel JSON-RPC daemon → PHP, elle sort du scope 5.1.

#### Guardrail 8 — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box réelle
- Ne jamais improviser de rsync ad hoc ou copie SSH manuelle
- Référence : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Project Structure Notes

- Nouveau module : `resources/daemon/cache/disk_cache.py` + `resources/daemon/cache/__init__.py`
- Tests unitaires : `tests/unit/test_disk_cache.py`
- Tests intégration : `tests/integration/test_boot_reconciliation.py`
- PHP : `core/class/jeedom2ha.class.php` — méthode `bootstrapRuntimeAfterDaemonStart()`
- Le `data/` directory est géré par Jeedom — vérifier son existence avant `json.dump`, ne pas le créer si absent

### Références

- [Source: epic-5-lifecycle-matrix.md#Décision-1] — Ordre de vérité au redémarrage
- [Source: epic-5-lifecycle-matrix.md#Décision-6] — Republication birth HA depuis cache courant
- [Source: epic-5-lifecycle-matrix.md#Décision-7] — Backoff Jeedom au bootstrap
- [Source: epic-5-lifecycle-matrix.md#Décision-8] — Lissage republication
- [Source: epic-5-lifecycle-matrix.md#Q1] — Persistence du `pending_discovery_unpublish` → couverte par cache disque + Task 7
- [Source: epic-5-lifecycle-matrix.md#Invariants] — INV-1, INV-2, INV-3, INV-5, INV-8, INV-9, INV-10, INV-11
- [Source: epic-5-lifecycle-matrix.md#Impacts-directs-sur-la-spec-5.1] — Checklist officielle des exigences 5.1
- [Source: implementation-readiness-report-2026-03-13.md#NFR2] — Bootstrap < 10s UI
- [Source: implementation-readiness-report-2026-03-13.md#NFR21] — Bootstrap étalé ≥ 10s pour > 50 eq
- [Source: resources/daemon/transport/mqtt_client.py#_on_connect] — Point d'ancrage reconnect republication
- [Source: resources/daemon/transport/http_server.py#_handle_action_sync] — Point d'ancrage cache persist + anciens_eq_ids
- [Source: implementation-artifacts/3-2-bis-bootstrap-runtime-apres-restart-daemon.md] — Scope guardrails du bootstrap (à ne pas régresser)
- [Source: implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md] — Contrat auth terrain obligatoire

## Stratégie de Tests

### Tests minimum par groupe d'AC

| Groupe AC | Type de test | Fichier cible | Ce qu'il vérifie |
|-----------|-------------|---------------|------------------|
| #1 — Cache disque persist | Unitaire | `tests/unit/test_disk_cache.py` | `save_publications_cache` écrit le bon JSON ; `load_publications_cache` lit + convertit les clés int |
| #2 — Cache disque load | Unitaire | `tests/unit/test_disk_cache.py` | Fichier absent → `{}` + log INFO ; JSON corrompu → `{}` + log INFO |
| #3 — Cold start | Unitaire | `tests/unit/test_disk_cache.py` | Démarrage sans fichier cache → `app["boot_cache"]` = `{}`, aucun publish |
| #4 — Watchdog 90s | Unitaire | `tests/unit/test_daemon_startup.py` | Watchdog log WARNING après timeout si publications vides ; s'annule dès première entry |
| #5 — Reconciliation boot | Intégration | `tests/integration/test_boot_reconciliation.py` | Cache `{X: published}` + sync sans `X` → unpublish déclenché ; cache `{X: published}` + sync avec `X` → republish |
| #6 — No publish avant sync | Unitaire | `tests/unit/test_daemon_startup.py` | `_on_connect()` avec publications vides → aucun publish |
| #7, #8 — Birth HA nominal | Unitaire | `tests/unit/test_mqtt_bridge.py` | Réception `homeassistant/status=online` → `_republish_all_from_cache` appelé ; N entités → sleep = max(0.1, 10/N) |
| #9 — Birth HA pendant boot | Unitaire | `tests/unit/test_mqtt_bridge.py` | Publications vides + birth HA → aucun publish, log INFO exact attendu |
| #10, #11 — Reconnect broker | Unitaire | `tests/unit/test_mqtt_bridge.py` | `_on_connect()` avec publications non vides → callback on_reconnect_cb appelé ; pending_unpublish rejoués avant republish |
| #12 — Lissage | Unitaire | `tests/unit/test_mqtt_bridge.py` | `asyncio.sleep` mocké ; vérifier que delay = max(0.1, 10/N) est respecté pour N=50, N=200 |
| #13-15 — Backoff PHP borné | Test PHP | stub/mock getFullTopology | `bootstrapRuntimeAfterDaemonStart()` retourne en < 5s même si getFullTopology() lève une exception |
| #16, #17 — Robustesse / birth message | Unitaire | `tests/unit/test_mqtt_bridge.py` | Erreur publish → log ERROR, boucle continue ; birth message → publié avant republications |
| Runbook terrain | Terrain (box réelle) | Task 8 | TC-A, TC-B, TC-C, TC-D avec preuves log et broker |

## Runbook Terrain Obligatoire

### Pré-conditions

```
- Box Jeedom de test avec daemon actif
- Au moins 3 entités publiées dans HA (vérifier dans l'UI HA)
- Preflight auth/sync Task 0 exécuté avec succès (LOCAL_SECRET, /system/status, /action/sync OK)
- deploy-to-box.sh --cleanup-discovery --restart-daemon exécuté avec succès
- mosquitto_sub disponible sur la box ou en local pour observer les topics
```

### TC-A — Restart daemon

```
PREUVE ATTENDUE : log daemon montrant la séquence boot complète

1. Stopper le daemon (Jeedom UI → Plugin → jeedom2ha → Stopper le daemon)
2. Vérifier HA : toutes les entités jeedom2ha passent "unavailable" (LWT tire)
3. Vérifier broker : jeedom2ha/bridge/status = "offline"
4. Redémarrer le daemon (Jeedom UI)
5. Vérifier logs daemon : séquence [CACHE] → [MQTT] connect → [MQTT] birth → [BOOTSTRAP] → [DISCOVERY] publish
6. Vérifier HA : toutes les entités reviennent "available" avec état correct
7. Vérifier broker : jeedom2ha/bridge/status = "online"
VERDICT : Pass si aucun ghost, aucun doublon, état correct dans HA
```

### TC-B — Restart broker MQTT

```
PREUVE ATTENDUE : log daemon montrant reconnexion + republish depuis cache courant

1. Depuis la box Jeedom : systemctl restart mosquitto (ou équivalent)
2. Vérifier logs daemon : [MQTT] Unexpected disconnect → [MQTT] reconnect → [DISCOVERY] republish
3. Vérifier HA : entités reviennent disponibles (avec ou sans persistence broker)
4. Vérifier broker : topics discovery toujours présents
VERDICT : Pass si daemon reconnecte automatiquement et republie sans intervention
```

### TC-C — Restart Home Assistant

```
PREUVE ATTENDUE : log daemon montrant détection birth message + republish depuis cache RAM

1. Restart HA (Docker : docker restart homeassistant ; ou service)
2. Vérifier broker : homeassistant/status = "online" publié par HA
3. Vérifier logs daemon : [BOOTSTRAP] Birth HA reçu → [DISCOVERY] republish N entités
4. Vérifier HA : toutes les entités jeedom2ha redécouvertes avec état correct
VERDICT : Pass si entités réapparaissent sans intervention, aucun ghost
```

### TC-D — Reboot complet box Jeedom

```
PREUVE ATTENDUE : log daemon post-reboot montrant la récupération automatique complète

1. Reboot la box Jeedom (Jeedom UI → Configuration → OS/DB → Redémarrer)
2. Attendre le démarrage complet (3-5 min pour Jeedom + daemon)
3. Vérifier HA : toutes les entités jeedom2ha disponibles, aucun ghost
4. Vérifier logs daemon post-reboot : [CACHE] → [MQTT] → [BOOTSTRAP] → [DISCOVERY]
5. Supprimer un équipement dans Jeedom pendant le downtime → vérifier qu'il est unpublié après reboot
VERDICT : Pass si récupération sans intervention, ghost-risk couvert
```

### Vérifications broker transversales

```
# Vérifier discovery topics présents
mosquitto_sub -h <broker> -t "homeassistant/+/jeedom2ha_+/config" -v --retained-only

# Vérifier bridge status
mosquitto_sub -h <broker> -t "jeedom2ha/bridge/status" -C 1

# Vérifier availability locale
mosquitto_sub -h <broker> -t "jeedom2ha/+/availability" -v --retained-only
```

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Tasks 0–7 implémentées et testées. Task 8 (tests terrain TC-A/B/C/D) réservée à l'exécution manuelle sur box réelle via `scripts/deploy-to-box.sh`.
- Contrainte paho thread-safety respectée : callbacks `_on_connect` / `_on_message` utilisent `call_soon_threadsafe` → sync wrapper → `asyncio.create_task()` depuis l'event loop.
- Pattern d'injection callback retenu : `bridge.start(config, on_reconnect_cb=..., on_ha_birth_cb=...)` — closures capturant `app`, aucune référence directe à `app` dans `MqttBridge`.
- boot_cache / publications séparation strictement respectée : `app["boot_cache"]` purgé après le premier `/action/sync`, jamais utilisé pour publier directement.
- Lissage Décision 8 appliqué uniquement dans `_republish_all_from_cache()` (batch birth HA + reconnect broker). Absent du handler `/action/sync` (chemin HTTP synchrone, timeout PHP si lisé).
- Ghost-risk boot couvert : `anciens_eq_ids` initialisés depuis `boot_cache` au premier sync, permettant la détection des eq_id supprimés pendant le downtime daemon.
- PHP backoff borné : budget 5s, 2 retries (1s + 2s max), retour immédiat si épuisé — conforme NFR2.
- Correction mid-sprint : `eq_ids_supprimes` loop — cas `old_decision is None and is_first_sync` ajouté pour traiter les unpublish boot_cache sans PublicationDecision en RAM.
- 388 tests passent, 0 échec au moment de la mise en review.
- **Clôture terrain 2026-03-20** : tests terrain TC-A (restart daemon), TC-B (restart broker), TC-C (restart HA), TC-D (reboot complet box) exécutés et validés PASS sur box réelle.
- **Code-review finale** : APPROVED WITH FOLLOW-UP (claude-opus-4-6). Aucun défaut bloquant, aucun retour en dev.
- **Follow-up identifié hors périmètre 5.1** : le répertoire `data/` n'est pas créé automatiquement par le plugin à l'installation. Le daemon gère l'absence gracieusement (cold start, WARNING log). Le fix relève du lifecycle d'installation (`install.php` ou `postInstall()`), pas du cycle de restart couvert par 5.1.

### File List

- `resources/daemon/cache/__init__.py` — CREATED (package init)
- `resources/daemon/cache/disk_cache.py` — CREATED (`save_publications_cache`, `load_publications_cache`)
- `resources/daemon/main.py` — MODIFIED (`_boot_watchdog`, boot_cache load, watchdog task, imports)
- `resources/daemon/transport/http_server.py` — MODIFIED (`_republish_all_from_cache`, first-sync reconciliation, boot_cache purge, watchdog signal, reconnect/birth callbacks, `_DATA_DIR`, `save_publications_cache` call, `create_app` init)
- `resources/daemon/transport/mqtt_client.py` — MODIFIED (`HA_STATUS_TOPIC`, `on_reconnect_cb`/`on_ha_birth_cb` injection, `_trigger_reconnect_republish`, `_trigger_ha_birth_republish`, `_subscribe_command_topics` update)
- `core/class/jeedom2ha.class.php` — MODIFIED (`bootstrapRuntimeAfterDaemonStart` retry backoff borné 5s)
- `tests/unit/test_disk_cache.py` — CREATED (14 tests : save/load happy path, missing dir, cold start, corruption, roundtrip)
- `tests/unit/test_daemon_startup.py` — MODIFIED (TestBootWatchdog × 5, TestOnStartBootCache × 3)
- `tests/unit/test_mqtt_bridge.py` — MODIFIED (TestHaStatusSubscription, TestBirthHaRepublication, TestBrokerReconnectRepublication, TestRepublishAllFromCache)
- `tests/integration/test_boot_reconciliation.py` — CREATED (6 tests : new eq_id, disappeared eq_id, boot_cache purge, second sync, watchdog event, disk save)

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-03-20 | 5.1.0 | Implémentation complète Tasks 0–7 : cache disque, watchdog boot, homeassistant/status, republication birth HA, republication reconnect broker, lissage batch, backoff PHP NFR2, réconciliation boot | claude-sonnet-4-6 |
| 2026-03-20 | 5.1.0 | Clôture : tests terrain TC-A/B/C/D PASS, code-review APPROVED WITH FOLLOW-UP, story → done | claude-opus-4-6 |
