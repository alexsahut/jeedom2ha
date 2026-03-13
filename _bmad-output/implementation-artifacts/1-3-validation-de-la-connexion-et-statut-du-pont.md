# Story 1.3: Validation de la Connexion et Statut du Pont

Status: review

## Story

As a utilisateur Jeedom,
I want voir un statut "Connecté" clair dès que le pont communique avec MQTT,
so that je sois sûr que la publication vers Home Assistant est possible.

## Acceptance Criteria

1. **Given** la configuration MQTT est saisie **When** le démon tente de se connecter **Then** l'interface affiche distinctement l'état du démon et l'état MQTT (badges séparés)
2. **And** le démon configure un LWT (Last Will and Testament) MQTT
3. **And** les logs montrent clairement les succès/échecs de connexion broker
4. **And** une reconnexion automatique est tentée après une coupure temporaire
5. **And** en cas d'échec broker, le plugin reste pilotable côté Jeedom et remonte un état dégradé explicite (ex: "MQTT Déconnecté")

## Tasks / Subtasks

- [x] **Task 1 — Client MQTT persistant (`transport/mqtt_client.py`)** (AC: #2, #3, #4)
  - [x] 1.1 Créer la classe `MqttBridge` encapsulant paho-mqtt pour une connexion persistante au broker
  - [x] 1.2 Configurer le LWT au moment du `connect()` : topic `jeedom2ha/bridge/status`, payload `offline`, QoS 1, retain=true
  - [x] 1.3 Publier le birth message `online` sur le même topic dans le callback `on_connect` (QoS 1, retain=true)
  - [x] 1.4 Implémenter la reconnexion automatique via `reconnect_delay_set(min_delay=1, max_delay=30)` (NFR6 : reconnexion < 30s)
  - [x] 1.5 Tracker l'état de connexion via un enum ou constantes : `DISCONNECTED`, `CONNECTING`, `CONNECTED`, `RECONNECTING`
  - [x] 1.6 Exposer `async start(config: dict)` et `async stop()` pour intégration dans le lifecycle daemon
  - [x] 1.7 Support TLS réutilisant le pattern V1 de Story 1.2 (CA système uniquement, option `tls_verify`)
  - [x] 1.8 Bridge paho-mqtt thread → asyncio via `loop.call_soon_threadsafe()` pour les callbacks d'état

- [x] **Task 2 — Intégration dans le daemon et l'API HTTP** (AC: #2, #3, #4, #5)
  - [x] 2.1 Ajouter endpoint POST `/action/mqtt_connect` dans `http_server.py` : reçoit la config MQTT (host, port, user, password, tls, tls_verify), démarre `MqttBridge`
  - [x] 2.2 Si un `MqttBridge` est déjà connecté, le déconnecter proprement avant de reconnecter avec la nouvelle config (permet le changement de config sans redémarrage)
  - [x] 2.3 Stocker la référence `MqttBridge` dans le state de l'app aiohttp (`app["mqtt_bridge"]`)
  - [x] 2.4 Enrichir le payload de `/system/status` avec une section `mqtt` : `{"connected": bool, "state": "connected"|"disconnected"|"connecting"|"reconnecting", "broker": "host:port"}`
  - [x] 2.5 Dans `on_stop()` du daemon (`main.py`), récupérer la référence `MqttBridge` depuis l'app et appeler `stop()` (publish offline, disconnect) **avant** de stopper le HTTP server

- [x] **Task 3 — PHP : envoi config MQTT après démarrage daemon** (AC: #1, #3)
  - [x] 3.1 Dans `deamon_start()` de `jeedom2ha.class.php`, après le healthcheck réussi, lire la config MQTT via `config::byKey` (mqttHost, mqttPort, mqttUser, mqttPassword avec `utils::decrypt`, mqttTls, mqttTlsVerify) et appeler `callDaemon('/action/mqtt_connect', $mqttConfig, 'POST')`
  - [x] 3.2 Si aucune config MQTT n'est définie (`mqttHost` vide), ne pas appeler `/action/mqtt_connect` — le daemon reste actif sans connexion MQTT, log info `[DAEMON] Pas de configuration MQTT, connexion différée`
  - [x] 3.3 Logger le résultat : `[MQTT] Connexion MQTT initiée vers host:port` ou `[MQTT] Échec initiation MQTT : <message>`
  - [x] 3.4 Ne jamais logger le mot de passe — masquer avec `***`

- [x] **Task 4 — UI : badge de statut MQTT sur la page équipements** (AC: #1, #5)
  - [x] 4.1 Ajouter un endpoint AJAX `getBridgeStatus` dans `jeedom2ha.ajax.php` qui lit le statut via `callDaemon('/system/status')` et retourne la section MQTT
  - [x] 4.2 Dans `desktop/php/jeedom2ha.php`, ajouter une zone de statut du pont au-dessus de la liste des équipements : un encadré avec le badge MQTT
  - [x] 4.3 Dans `desktop/js/jeedom2ha.js`, au chargement de la page, appeler `getBridgeStatus` et afficher le badge MQTT
  - [x] 4.4 Badges : `label-success` "MQTT Connecté", `label-warning` "MQTT Déconnecté" (orange — pas rouge, c'est un état dégradé, pas une panne), `label-danger` "MQTT Erreur" (rouge uniquement si erreur d'infrastructure), `label-default` "MQTT Non configuré" (gris si aucune config)
  - [x] 4.5 Si le daemon est stoppé, afficher "Démon arrêté" au lieu d'un état MQTT (pas de confusion entre les deux états)

- [x] **Task 5 — Logging structuré MQTT** (AC: #3)
  - [x] 5.1 Logger avec préfixe `[MQTT]` : connexion réussie (`INFO`), échec catégorisé (`WARNING`), reconnexion en cours (`INFO`), reconnexion réussie (`INFO`)
  - [x] 5.2 Logger la configuration LWT au démarrage : topic et retain (`DEBUG`)
  - [x] 5.3 Logger chaque tentative de reconnexion avec le délai courant (`DEBUG`)
  - [x] 5.4 Ne jamais logger de mot de passe — masquer avec `***` si les paramètres doivent être loggués

- [x] **Task 6 — Tests unitaires** (AC: tous)
  - [x] 6.1 Créer `tests/unit/test_mqtt_bridge.py` : tester `MqttBridge` — connexion réussie, LWT configuré, birth message publié
  - [x] 6.2 Tester la reconnexion automatique après disconnect (callback `on_disconnect` avec rc != 0 → état `RECONNECTING`)
  - [x] 6.3 Tester la gestion d'erreur : broker injoignable → état cohérent, pas de crash
  - [x] 6.4 Tester endpoint `/action/mqtt_connect` : succès, paramètres manquants, reconnexion
  - [x] 6.5 Tester `/system/status` avec section MQTT (connected et disconnected)
  - [x] 6.6 Tester shutdown propre : `stop()` publie `offline` et déconnecte

## Dev Notes

### Architecture & Patterns obligatoires

**Connexion MQTT persistante — architecture paho-mqtt + asyncio :**

Le daemon est un processus asyncio (via `jeedomdaemon`). paho-mqtt utilise son propre thread réseau via `loop_start()`. Les callbacks (`on_connect`, `on_disconnect`, `on_message`) sont appelés dans le thread paho, pas dans l'event loop asyncio. Le bridge entre les deux mondes doit utiliser `loop.call_soon_threadsafe()`.

```python
# Pattern critique : bridge paho-thread → asyncio
import asyncio
import paho.mqtt.client as mqtt

BRIDGE_STATUS_TOPIC = "jeedom2ha/bridge/status"

class MqttBridge:
    def __init__(self):
        self._client = None
        self._state = "disconnected"  # disconnected | connecting | connected | reconnecting
        self._loop = None  # asyncio event loop reference
        self._broker_host = ""
        self._broker_port = 0

    async def start(self, config: dict):
        """Start persistent MQTT connection. Non-blocking — returns after initiating connect."""
        self._loop = asyncio.get_running_loop()
        self._broker_host = config["host"]
        self._broker_port = int(config.get("port", 1883))

        self._client = mqtt.Client(client_id="jeedom2ha_bridge", clean_session=True)

        # LWT — publié automatiquement par le broker si le client disparaît
        self._client.will_set(BRIDGE_STATUS_TOPIC, "offline", qos=1, retain=True)

        # Callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        # Reconnexion automatique (paho built-in)
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        # TLS (V1 — CA système uniquement)
        if config.get("tls", False):
            import ssl
            ctx = ssl.create_default_context()
            if not config.get("tls_verify", True):
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            self._client.tls_set_context(ctx)

        # Auth
        user = config.get("user", "")
        if user:
            self._client.username_pw_set(user, config.get("password", ""))

        self._state = "connecting"
        self._client.connect_async(self._broker_host, self._broker_port, keepalive=60)
        self._client.loop_start()

    async def stop(self):
        """Graceful shutdown: publish offline, disconnect, stop network thread."""
        if self._client is not None:
            try:
                self._client.publish(BRIDGE_STATUS_TOPIC, "offline", qos=1, retain=True)
                self._client.disconnect()
            except Exception:
                pass
            self._client.loop_stop()
            self._client = None
        self._state = "disconnected"

    def _on_connect(self, client, userdata, flags, rc):
        """Called in paho thread on successful connection."""
        if rc == 0:
            # Birth message
            client.publish(BRIDGE_STATUS_TOPIC, "online", qos=1, retain=True)
            self._loop.call_soon_threadsafe(self._set_state, "connected")
        else:
            self._loop.call_soon_threadsafe(self._set_state, "disconnected")

    def _on_disconnect(self, client, userdata, rc):
        """Called in paho thread on disconnect."""
        if rc != 0:
            # Unexpected disconnect → paho will auto-reconnect
            self._loop.call_soon_threadsafe(self._set_state, "reconnecting")
        else:
            # Clean disconnect (we called disconnect())
            self._loop.call_soon_threadsafe(self._set_state, "disconnected")

    def _set_state(self, new_state):
        self._state = new_state

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == "connected"

    @property
    def broker_info(self) -> str:
        return f"{self._broker_host}:{self._broker_port}" if self._broker_host else ""
```

> **IMPORTANT paho-mqtt API** : le code utilise l'API paho-mqtt v1 (`mqtt.Client(client_id=..., clean_session=True)`) qui est supportée par paho-mqtt 2.x avec un shim de compatibilité. Les tests Story 1.2 utilisent déjà ce pattern. Ne pas migrer vers l'API v2 dans cette story pour éviter une régression des tests existants.

**Topic MQTT du pont :**
- `jeedom2ha/bridge/status` — valeurs `online` / `offline`, retain=true, QoS 1
- Ce topic sera utilisé comme `availability_topic` dans les payloads MQTT Discovery des stories ultérieures (Epic 2)
- Le namespace `jeedom2ha/` est isolé conformément au NFR16

**LWT (Last Will and Testament) — rappel MQTT :**
Le LWT est un message pré-enregistré par le client MQTT auprès du broker au moment de la connexion. Si le broker détecte une déconnexion non propre (timeout keepalive, connexion TCP coupée), il publie automatiquement le message LWT. C'est le mécanisme standard pour signaler l'indisponibilité du pont à Home Assistant.

**Reconnexion automatique — paho-mqtt built-in :**
`reconnect_delay_set(min_delay=1, max_delay=30)` configure un backoff exponentiel automatique. paho-mqtt gère la reconnexion dans son thread réseau — aucune boucle de retry manuelle n'est nécessaire. Le callback `on_connect` est rappelé après chaque reconnexion réussie → le birth message est re-publié automatiquement.

**Endpoint `/action/mqtt_connect` — design :**
```python
async def _handle_mqtt_connect(request: web.Request) -> web.Response:
    """Handle POST /action/mqtt_connect — initiate persistent MQTT connection."""
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)

    data = await request.json()
    host = data.get("host", "")
    if not host:
        return web.json_response({
            "action": "mqtt.connect", "status": "error",
            "message": "Paramètre 'host' requis",
        })

    # Stop existing bridge if any
    existing = request.app.get("mqtt_bridge")
    if existing is not None:
        await existing.stop()

    bridge = MqttBridge()
    await bridge.start(data)
    request.app["mqtt_bridge"] = bridge

    payload = {
        "action": "mqtt.connect",
        "status": "ok",
        "payload": {"state": bridge.state, "broker": bridge.broker_info},
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return web.json_response(payload)
```

> Note : la réponse de `/action/mqtt_connect` retourne l'état `connecting` car `connect_async()` est non bloquant. Le passage à `connected` se fait via le callback `on_connect`. Le PHP vérifie l'état MQTT réel via `/system/status` ultérieurement.

**Enrichissement de `/system/status` :**
```python
# Dans _handle_system_status, ajouter :
mqtt_bridge = request.app.get("mqtt_bridge")
mqtt_section = {
    "connected": mqtt_bridge.is_connected if mqtt_bridge else False,
    "state": mqtt_bridge.state if mqtt_bridge else "disconnected",
    "broker": mqtt_bridge.broker_info if mqtt_bridge else "",
}
# Ajouter dans payload["payload"]["mqtt"] = mqtt_section
```

**PHP `deamon_start()` — ajout de l'envoi MQTT :**
```php
// Après la boucle de healthcheck réussie
$mqttHost = config::byKey('mqttHost', __CLASS__, '');
if ($mqttHost !== '') {
    $mqttConfig = array(
        'host'       => $mqttHost,
        'port'       => intval(config::byKey('mqttPort', __CLASS__, 1883)),
        'user'       => config::byKey('mqttUser', __CLASS__, ''),
        'password'   => utils::decrypt(config::byKey('mqttPassword', __CLASS__, '')),
        'tls'        => config::byKey('mqttTls', __CLASS__, '0') === '1',
        'tls_verify' => config::byKey('mqttTlsVerify', __CLASS__, '1') === '1',
    );
    log::add(__CLASS__, 'info', '[MQTT] Connexion MQTT initiée vers ' . $mqttHost . ':' . $mqttConfig['port']);
    $result = self::callDaemon('/action/mqtt_connect', $mqttConfig, 'POST');
    if ($result === null || !isset($result['status']) || $result['status'] !== 'ok') {
        log::add(__CLASS__, 'warning', '[MQTT] Échec initiation MQTT — le démon reste actif sans broker');
    }
} else {
    log::add(__CLASS__, 'info', '[DAEMON] Pas de configuration MQTT, connexion différée');
}
```

> **Sécurité** : le mot de passe est déchiffré via `utils::decrypt()` juste avant l'envoi au daemon et transmis uniquement via HTTP local 127.0.0.1. Ne jamais logger `$mqttConfig['password']`.

**AJAX `getBridgeStatus` :**
```php
if (init('action') == 'getBridgeStatus') {
    $status = jeedom2ha::callDaemon('/system/status');
    if ($status === null) {
        ajax::success(array('daemon' => false, 'mqtt' => array('state' => 'unknown')));
    }
    ajax::success(array(
        'daemon' => true,
        'mqtt' => isset($status['payload']['mqtt']) ? $status['payload']['mqtt'] : array('state' => 'disconnected'),
    ));
}
```

**UI Badge MQTT dans `desktop/php/jeedom2ha.php` :**

Ajouter un encadré de statut du pont entre la légende "Gestion" et la légende "Mes templates", au-dessus de la liste des équipements. Le badge MQTT est **distinct** du badge daemon natif de Jeedom (qui est géré dans la page Admin → Plugins).

```html
<!-- Zone statut pont — MQTT -->
<div id="div_bridgeStatus" class="well well-sm" style="margin:10px 5px;">
  <i class="fas fa-network-wired"></i> <strong>{{Pont MQTT}}</strong> :
  <span id="span_mqttStatus" class="label label-default">{{Chargement...}}</span>
  <span id="span_mqttBroker" style="margin-left:10px;color:#666;"></span>
</div>
```

```javascript
// Dans desktop/js/jeedom2ha.js — chargement initial du statut MQTT
function refreshBridgeStatus() {
  $.ajax({
    type: 'POST', url: 'core/ajax/jeedom2ha.ajax.php',
    data: {action: 'getBridgeStatus'},
    dataType: 'json',
    success: function(data) {
      if (data.state !== 'ok') return;
      var r = data.result;
      var $badge = $('#span_mqttStatus');
      var $broker = $('#span_mqttBroker');
      if (!r.daemon) {
        $badge.removeClass().addClass('label label-default').text('Démon arrêté');
        $broker.text('');
        return;
      }
      var mqtt = r.mqtt || {};
      switch (mqtt.state) {
        case 'connected':
          $badge.removeClass().addClass('label label-success').text('MQTT Connecté');
          break;
        case 'reconnecting':
          $badge.removeClass().addClass('label label-warning').text('MQTT Reconnexion...');
          break;
        case 'connecting':
          $badge.removeClass().addClass('label label-warning').text('MQTT Connexion...');
          break;
        case 'disconnected':
          $badge.removeClass().addClass('label label-warning').text('MQTT Déconnecté');
          break;
        default:
          $badge.removeClass().addClass('label label-default').text('MQTT Non configuré');
      }
      $broker.text(mqtt.broker || '');
    }
  });
}
// Appel au chargement et toutes les 30s quand la page est visible
refreshBridgeStatus();
setInterval(refreshBridgeStatus, 30000);
```

> **Règle UI (project-context)** : rouge réservé aux pannes d'infrastructure (broker totalement injoignable après config). L'état "MQTT Déconnecté" post-coupure temporaire est orange (`label-warning`), pas rouge.

**Shutdown propre du daemon (`main.py`) :**

L'ordre de shutdown est critique : MQTT d'abord (publish offline + disconnect), HTTP ensuite.

```python
async def on_stop(self):
    _LOGGER.info("[DAEMON] jeedom2ha daemon stopping")
    # 1. Stop MQTT bridge (publish offline, disconnect)
    if self._http_runner is not None:
        app = self._http_runner._server._app  # ou stocker app en attribut d'instance
        mqtt_bridge = app.get("mqtt_bridge")
        if mqtt_bridge is not None:
            await mqtt_bridge.stop()
    # 2. Stop HTTP server
    await stop_server(self._http_runner)
    self._http_runner = None
```

> **Alternative plus propre** : stocker l'app en attribut d'instance (`self._app`) dans `on_start()` plutôt que de naviguer `_http_runner._server._app`. L'app est créée dans `on_start()` via `create_app()` — il suffit de la garder.

**Format des échanges — enveloppe standard (rappel Story 1.1) :**

```json
// Réponse de /action/mqtt_connect
{
  "action": "mqtt.connect",
  "status": "ok",
  "payload": {"state": "connecting", "broker": "192.168.1.10:1883"},
  "request_id": "uuid",
  "timestamp": "2026-03-13T10:00:00Z"
}

// /system/status enrichi
{
  "action": "system.status",
  "status": "ok",
  "payload": {
    "version": "0.1.0",
    "uptime": 123.45,
    "mqtt": {
      "connected": true,
      "state": "connected",
      "broker": "192.168.1.10:1883"
    }
  },
  "request_id": "uuid",
  "timestamp": "2026-03-13T10:00:00Z"
}
```

### Project Structure Notes

**Fichiers à créer ou modifier dans cette story :**

```
jeedom2ha/
├── core/
│   ├── class/jeedom2ha.class.php       # MODIFIER: deamon_start() envoie config MQTT
│   └── ajax/jeedom2ha.ajax.php         # MODIFIER: ajouter action getBridgeStatus
├── desktop/
│   ├── php/jeedom2ha.php               # MODIFIER: ajouter zone badge MQTT
│   └── js/jeedom2ha.js                 # MODIFIER: ajouter refreshBridgeStatus()
└── resources/daemon/
    ├── main.py                         # MODIFIER: on_stop() arrête MQTT, stocker ref app
    └── transport/
        ├── mqtt_client.py              # CRÉER: classe MqttBridge
        └── http_server.py              # MODIFIER: ajouter /action/mqtt_connect, enrichir /system/status
tests/
└── unit/
    └── test_mqtt_bridge.py             # CRÉER: tests MqttBridge + endpoint mqtt_connect
```

**Fichiers à NE PAS toucher dans cette story :**
- `plugin_info/configuration.php` — formulaire MQTT déjà complet (Story 1.2)
- `plugin_info/packages.json` — paho-mqtt déjà ajouté (Story 1.2)
- `core/php/jeedom2ha.php` — stub callback inchangé (logique callback sera implémentée en Epic 3)

### Pièges à éviter

- **NE PAS** implémenter de logique de publication Discovery dans cette story — uniquement le birth/status du pont. Les payloads Discovery sont scope Epic 2.
- **NE PAS** souscrire à des topics MQTT dans cette story (pas de `subscribe`, pas de `on_message` MQTT). L'écoute des commandes HA → Jeedom est scope Epic 3.
- **NE PAS** passer les credentials MQTT en arguments CLI du daemon — les transmettre via POST `/action/mqtt_connect` après démarrage (cohérence Story 1.2).
- **NE PAS** écrire de boucle de retry manuelle pour la reconnexion — paho-mqtt gère ça nativement via `reconnect_delay_set()`.
- **NE PAS** utiliser `connect()` bloquant — utiliser `connect_async()` + `loop_start()` pour ne pas bloquer l'event loop asyncio.
- **NE PAS** confondre le shutdown propre (`disconnect()` appelé par le code → `on_disconnect(rc=0)`) avec la déconnexion subie (`rc != 0`). Le birth message ne doit être re-publié que dans `on_connect`, pas dans `on_disconnect`.
- **NE PAS** afficher rouge pour "MQTT Déconnecté" temporaire — utiliser `label-warning` (orange). Rouge est réservé aux pannes d'infrastructure (projet-context: "Rouge réservé aux pannes d'infrastructure").
- **NE PAS** logger le mot de passe MQTT en clair — masquer avec `***` (feedback Story 1.1).
- **NE PAS** bloquer `deamon_start()` en attendant que MQTT soit connecté — l'appel `/action/mqtt_connect` est non-bloquant (`connect_async`). Le daemon est "ok" dès que le HTTP API répond, même si MQTT est encore en cours de connexion.
- **NE PAS** accéder à `_http_runner._server._app` — stocker l'app en attribut propre du daemon pour un accès clean dans `on_stop()`.

### Intelligences des Stories précédentes à réutiliser

**Story 1.1 :**
- Pattern `callDaemon($endpoint, $payload, $method)` — déjà implémenté, `maxAttempts=1` pour POST
- `_check_secret(request, local_secret)` dans `http_server.py` — réutiliser directement
- Import path fix : `_DAEMON_DIR` dans `main.py` — ne pas casser, utiliser le même pattern pour `transport/mqtt_client.py`
- `app["start_time"]`, `app["local_secret"]` — pattern de state dans l'app aiohttp, ajouter `app["mqtt_bridge"]`
- `Jeedom2haDaemon._http_runner` — besoin de stocker aussi `self._app` pour un accès clean depuis `on_stop()`

**Story 1.2 :**
- `_sync_mqtt_connect()` dans `http_server.py` — logique de connexion synchrone de test. Le `MqttBridge` réutilise le même pattern TLS (`ssl.create_default_context()`, `ctx.check_hostname`, `ctx.verify_mode`) et auth (`username_pw_set`), mais avec `connect_async` au lieu de `connect` bloquant.
- Catégorisation des erreurs MQTT : les mêmes `error_code` doivent être loggués si la connexion persistante échoue (pas seulement pour le test).
- `config::byKey('mqttHost/Port/User/Password', 'jeedom2ha')` — réutiliser exactement les mêmes clés de config.
- `utils::decrypt(config::byKey('mqttPassword', ...))` — pattern de déchiffrement du mot de passe avant envoi au daemon.
- Le endpoint `/action/mqtt_test` (Story 1.2) et `/action/mqtt_connect` (cette story) coexistent — le test est un one-shot, le connect est persistant.

### Déviation architecture documentée (héritée Story 1.1 — M2)

Les tests sont dans `tests/unit/` (racine du repo) et non dans `resources/daemon/tests/` comme le spécifie l'architecture. Ce choix préserve l'infrastructure CI existante. À arbitrer en début d'Epic 2.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Internal Communication Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/project-context.md#MQTT Discovery Home Assistant — availability_topic, LWT, birth message]
- [Source: _bmad-output/project-context.md#Règles Python (Daemon)]
- [Source: _bmad-output/project-context.md#Règles JavaScript (Frontend)]
- [Source: _bmad-output/implementation-artifacts/1-1-initialisation-et-communication-php-python.md#Dev Notes]
- [Source: _bmad-output/implementation-artifacts/1-2-configuration-et-onboarding-mqtt-auto-manuel.md#Dev Notes]
- [Source: PyPI paho-mqtt — Client.will_set, reconnect_delay_set, connect_async, loop_start]
- [Source: HA MQTT Discovery — availability, birth_message concept]

## Validation manuelle (instance Jeedom de dev)

**Connexion MQTT :**
- [ ] Démarrer le daemon avec une config MQTT valide → logs `[MQTT] Connexion MQTT initiée vers host:port` puis `[MQTT] Connected to broker`
- [ ] Vérifier sur le broker (via `mosquitto_sub -t 'jeedom2ha/#' -v`) que `jeedom2ha/bridge/status` = `online` (retained)
- [ ] Arrêter le daemon proprement → `jeedom2ha/bridge/status` = `offline` (retained)
- [ ] Couper le broker MQTT temporairement → logs `[MQTT] Disconnected (rc=...)`, puis reconnexion auto, puis `[MQTT] Reconnected`
- [ ] Vérifier que le birth message `online` est re-publié après chaque reconnexion

**LWT :**
- [ ] Tuer le daemon brutalement (`kill -9`) → le broker publie automatiquement `offline` sur `jeedom2ha/bridge/status`
- [ ] Vérifier que le message LWT est retained (il persiste même si personne n'écoute au moment du kill)

**UI — Badges séparés :**
- [ ] Page équipements : badge "MQTT Connecté" (vert) quand tout est ok
- [ ] Couper le broker → badge passe à "MQTT Reconnexion..." (orange) puis "MQTT Déconnecté" (orange)
- [ ] Reconnecter le broker → badge revient à "MQTT Connecté" (vert)
- [ ] Daemon stoppé → badge "Démon arrêté" (gris) — pas de confusion avec l'état MQTT
- [ ] Aucune config MQTT → badge "MQTT Non configuré" (gris)

**Pas de config MQTT :**
- [ ] Démarrer le daemon sans config MQTT → le daemon est ok, pas de connexion MQTT tentée, log `[DAEMON] Pas de configuration MQTT, connexion différée`
- [ ] Le plugin reste pilotable (page UI accessible, config modifiable)

**Sécurité :**
- [ ] Vérifier les logs : aucun mot de passe en clair
- [ ] Vérifier que `/action/mqtt_connect` rejette les requêtes sans `X-Local-Secret` (401)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

- Import relatif `from .mqtt_client import MqttBridge` utilisé dans `http_server.py` (au lieu de `from transport.mqtt_client`) pour compatibilité avec l'import des tests (`resources.daemon.transport.http_server`) et le script `main.py` (via sys.path).
- `_handle_mqtt_connect` accepte le payload en direct ou enveloppé (`data.get("payload", data)`) pour compatibilité avec `callDaemon()` qui wrape les POST.
- Tests `TestMqttConnectEndpointBehavior` et `TestSystemStatusWithMqtt` utilisent `AsyncMock` pour les méthodes async du bridge mocké.

### Completion Notes List

- **Task 1** : `MqttBridge` implémentée dans `transport/mqtt_client.py`. LWT `jeedom2ha/bridge/status offline` configuré à la connexion. Birth message `online` publié dans `on_connect` rc=0. `reconnect_delay_set(1, 30)`. Bridge paho→asyncio via `call_soon_threadsafe`. TLS pattern identique à Story 1.2 (`ssl.create_default_context()`, `tls_verify`). paho-mqtt 2.0+ compat (try/except AttributeError).
- **Task 2** : Endpoint `/action/mqtt_connect` ajouté dans `http_server.py` avec arrêt du bridge existant, import `MqttBridge` relatif. `/system/status` enrichi avec section `mqtt: {connected, state, broker}`. `main.py` modifié pour stocker `self._app` et appeler `mqtt_bridge.stop()` avant `stop_server()` dans `on_stop()`.
- **Task 3** : `deamon_start()` dans `jeedom2ha.class.php` lit la config MQTT après healthcheck réussi, appelle `callDaemon('/action/mqtt_connect', $mqttConfig, 'POST')`. Aucun log du mot de passe. Log `[DAEMON] Pas de configuration MQTT, connexion différée` si pas de config.
- **Task 4** : Endpoint AJAX `getBridgeStatus` dans `jeedom2ha.ajax.php`. Zone `#div_bridgeStatus` dans `desktop/php/jeedom2ha.php`. Fonction `refreshBridgeStatus()` dans `desktop/js/jeedom2ha.js` avec refresh toutes les 30s. Badges : vert=connecté, orange=déconnecté/reconnexion/connexion, gris=non configuré/daemon arrêté.
- **Task 5** : Logging `[MQTT]` avec niveaux corrects dans `mqtt_client.py` et `http_server.py`. Aucun mot de passe loggué.
- **Task 6** : 36 nouveaux tests dans `tests/unit/test_mqtt_bridge.py`. Suite totale : 90/90 verts.

### File List

- `resources/daemon/transport/mqtt_client.py` (nouveau) — Classe `MqttBridge` : connexion persistante, LWT, birth message, reconnexion auto, TLS, bridge paho→asyncio
- `resources/daemon/transport/http_server.py` (modifié) — Ajout endpoint `/action/mqtt_connect`, enrichissement `/system/status` avec section MQTT, import `MqttBridge`
- `resources/daemon/main.py` (modifié) — Stockage `self._app`, shutdown MQTT avant HTTP dans `on_stop()`
- `core/class/jeedom2ha.class.php` (modifié) — `deamon_start()` envoie config MQTT après healthcheck réussi
- `core/ajax/jeedom2ha.ajax.php` (modifié) — Ajout action `getBridgeStatus`
- `desktop/php/jeedom2ha.php` (modifié) — Zone badge MQTT `#div_bridgeStatus`
- `desktop/js/jeedom2ha.js` (modifié) — Fonction `refreshBridgeStatus()` avec polling 30s
- `tests/unit/test_mqtt_bridge.py` (nouveau) — 36 tests : MqttBridge unit, callbacks, TLS, endpoint mqtt_connect, /system/status MQTT
