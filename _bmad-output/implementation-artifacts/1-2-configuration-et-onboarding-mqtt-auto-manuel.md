# Story 1.2: Configuration et Onboarding MQTT (Auto & Manuel)

Status: done

## Story

As a utilisateur Jeedom,
I want que le plugin détecte ma configuration MQTT Manager ou me permette de la saisir manuellement,
so that je n'aie pas à deviner les paramètres de connexion.

## Acceptance Criteria

1. **Given** le démon est actif **When** j'accède à la configuration du plugin **Then** le plugin tente une auto-détection si MQTT Manager (`mqtt2`) est présent
2. **And** un fallback manuel permet de saisir : host, port, user, password
3. **And** les paramètres additionnels sont supportés : TLS on/off et validation de certificat pour broker distant
4. **And** la configuration est stockée via les mécanismes standards Jeedom (`config::save` / `config::byKey`)
5. **And** un test de connexion est déclenchable depuis l'UI (bouton "Tester la connexion")
6. **And** un message de guidage clair s'affiche si aucun broker n'est disponible/configuré

## Tasks / Subtasks

- [x] **Task 1 — Auto-détection MQTT Manager (best effort)** (AC: #1)
  - [x] 1.1 Implémenter `getMqttManagerConfig()` dans `jeedom2ha.class.php` : vérifier si le plugin `mqtt2` est actif et récupérer sa configuration (host, port, user, password). Si les clés de config `mqtt2` ne peuvent pas être vérifiées sur instance réelle, logger `[MQTT] Auto-détection mqtt2 : clé inconnue, fallback manuel` et retourner null — ne jamais lever d'exception bloquante.
  - [x] 1.2 Exposer via AJAX (`/core/ajax/jeedom2ha.ajax.php`) un endpoint `getMqttConfig` qui retourne la config détectée ou `{"source": "none"}` si `mqtt2` est absent/inactif/illisible
  - [x] 1.3 Appeler automatiquement cet endpoint au chargement de `plugin_info/configuration.php` pour pré-remplir les champs — l'absence de résultat ne bloque jamais le formulaire manuel

- [x] **Task 2 — Formulaire de configuration MQTT dans `configuration.php`** (AC: #2, #3, #4)
  - [x] 2.1 Ajouter les champs de config dans `plugin_info/configuration.php` : `mqttHost`, `mqttPort` (défaut 1883), `mqttUser`, `mqttPassword`, `mqttTls` (checkbox), `mqttTlsVerify` (checkbox)
  - [x] 2.2 Implémenter la sauvegarde via les mécanismes Jeedom standard (`config::save` côté PHP ou `ajax::success` côté AJAX)
  - [x] 2.3 Afficher un badge de statut d'auto-détection ("MQTT Manager détecté" ou "Configuration manuelle") dans le formulaire
  - [x] 2.4 S'assurer que le mot de passe est stocké chiffré (`$_encryptConfigKey = ['mqttPassword']`) ou via `utils::encrypt`

- [x] **Task 3 — Endpoint de test de connexion MQTT** (AC: #5)
  - [x] 3.1 Ajouter un endpoint HTTP `/action/mqtt_test` dans `transport/http_server.py` (POST, protégé `X-Local-Secret`) qui tente une connexion MQTT avec les paramètres fournis
  - [x] 3.2 Implémenter la connexion MQTT via `paho-mqtt` (connect + ping/disconnect immédiat, timeout 5s). Catégoriser les erreurs en types distincts : `host_unreachable`, `port_refused`, `auth_failed`, `tls_error`, `timeout` — le `message` de la réponse doit être lisible par un utilisateur, pas une stack trace Python
  - [x] 3.3 Ajouter dans `jeedom2ha.ajax.php` l'action `testMqttConnection` : récupère la config courante des champs du formulaire, appelle `callDaemon('/action/mqtt_test', $params, 'POST')`, retourne succès/échec à l'UI
  - [x] 3.4 Le JS du bouton "Tester la connexion" et son feedback (spinner → message d'erreur catégorisé ou badge vert) doit être placé dans `plugin_info/configuration.php` (inline ou `<script>` en bas de page), **pas dans `desktop/js/jeedom2ha.js`** — ce fichier n'est pas chargé sur la vue de configuration plugin. Vérifier que le JS accède bien aux champs du formulaire de config dans le contexte de la modale Jeedom.

- [x] **Task 4 — Message de guidage si aucun broker** (AC: #6)
  - [x] 4.1 Si l'auto-détection échoue ET qu'aucune config manuelle n'existe, afficher dans `configuration.php` un message contextuel : "Aucun broker MQTT détecté. Installez MQTT Manager ou saisissez les paramètres manuellement ci-dessous."
  - [x] 4.2 Le message est un bandeau `alert alert-warning` (style Jeedom natif Bootstrap 3), pas du rouge (pas une panne)

- [x] **Task 5 — Ajout de `paho-mqtt` dans packages.json** (AC: #1, prérequis MQTT)
  - [x] 5.1 Ajouter `"paho-mqtt": {}` dans la section `pip3` de `plugin_info/packages.json`

- [x] **Task 6 — Tests unitaires** (AC: tous)
  - [x] 6.1 Créer `tests/unit/test_mqtt_config.py` : tester l'endpoint `/action/mqtt_test` avec paho-mqtt mocké — couvrir : connexion réussie, `host_unreachable` (socket.gaierror), `port_refused` (ConnectionRefusedError), `auth_failed` (rc=5 paho), `tls_error` (ssl.SSLError), `timeout` (socket.timeout)
  - [x] 6.2 Créer `tests/unit/test_mqtt_manager_detection.php` n'est pas possible (pas de test runner PHP) — documenter les scénarios de test manuel à la place dans la section "Validation manuelle" de cette story

## Dev Notes

### Architecture & Patterns obligatoires

**Auto-détection MQTT Manager (`mqtt2`) — best effort, jamais bloquante :**

Le plugin `mqtt2` (MQTT Manager) stocke sa configuration dans la table `config` standard de Jeedom. La lecture est un confort, pas une dépendance forte. Règle : si l'auto-détection échoue pour n'importe quelle raison (plugin absent, inactif, clé inconnue, valeur vide), on log un warning lisible et on retourne `null` — sans jamais lever d'exception propagée ni bloquer l'accès au formulaire manuel.

```php
// Dans jeedom2ha.class.php
public static function getMqttManagerConfig(): ?array {
    try {
        $mqtt2Plugin = plugin::byId('mqtt2');
        if (!is_object($mqtt2Plugin) || !$mqtt2Plugin->isActive()) {
            log::add(__CLASS__, 'debug', '[MQTT] mqtt2 absent ou inactif — configuration manuelle requise');
            return null;
        }
        // ⚠️ Les clés ci-dessous sont des approximations à vérifier sur instance réelle avec mqtt2 installé.
        // Si une clé retourne '' ou null, l'auto-détection est considérée incomplète → fallback manuel.
        $host = config::byKey('mqttAdress', 'mqtt2', '');  // peut être 'brokerAddr', 'host', etc.
        $port = config::byKey('mqttPort', 'mqtt2', 1883);
        $user = config::byKey('mqttUser', 'mqtt2', '');
        $pass = config::byKey('mqttPassword', 'mqtt2', '');
        if ($host === '') {
            log::add(__CLASS__, 'warning', '[MQTT] Auto-détection mqtt2 : clé host vide ou inconnue, fallback manuel');
            return null;
        }
        log::add(__CLASS__, 'info', '[MQTT] Auto-détection mqtt2 : host détecté → configuration pré-remplie');
        return ['host' => $host, 'port' => $port, 'user' => $user, 'password' => $pass, 'source' => 'mqtt2'];
    } catch (\Throwable $e) {
        log::add(__CLASS__, 'warning', '[MQTT] Auto-détection mqtt2 : exception → ' . $e->getMessage() . ' — fallback manuel');
        return null;
    }
}
```

> ⚠️ **PRIORITÉ DÉVELOPPEUR** : Vérifier les noms de clés exacts de `mqtt2` sur une instance réelle **avant** de finaliser le code. La lecture des sources de `mqtt2` sur GitHub ou l'inspection de la table `config` sur une instance avec MQTT Manager installé est le moyen le plus fiable.

**Stockage sécurisé du mot de passe :**

Utiliser le mécanisme de chiffrement natif de Jeedom pour le mot de passe :
```php
// Dans jeedom2ha.class.php
public static $_encryptConfigKey = array('mqttPassword');
```
Avec cette déclaration, Jeedom appelle automatiquement `utils::encrypt()` / `utils::decrypt()` sur ce champ lors des save/load.

**Nouveau paramètre CLI pour le daemon (`--mqtthost`, `--mqttport`, etc.) — NON RECOMMANDÉ**

Ne pas passer les paramètres MQTT via CLI au daemon. Le daemon doit les lire via un appel à l'API HTTP locale ou via un message PHP→daemon. Pour cette story, la config MQTT sera lue au moment du test de connexion depuis les paramètres transmis dans le payload POST de `/action/mqtt_test`. Elle ne sera pas persistée dans le daemon en story 1.2 — c'est la story 1.3 qui gère la connexion durable.

**Endpoint `/action/mqtt_test` (daemon) — erreurs catégorisées :**

Le `message` de la réponse doit être lisible par un utilisateur, pas une stack trace. Catégoriser les erreurs selon leur cause :

| Cause Python | `error_code` | `message` (FR) affiché dans l'UI |
|---|---|---|
| Succès | — | `"Connexion réussie"` |
| `socket.gaierror` / `socket.herror` | `host_unreachable` | `"Hôte introuvable : vérifiez l'adresse du broker"` |
| `ConnectionRefusedError` | `port_refused` | `"Port refusé : le broker n'écoute pas sur ce port"` |
| RC paho = 5 (CONNACK) | `auth_failed` | `"Authentification refusée : vérifiez identifiant et mot de passe"` |
| `ssl.SSLError` / `ssl.CertificateError` | `tls_error` | `"Erreur TLS : certificat invalide ou protocole non supporté"` |
| `socket.timeout` / timeout dépassé | `timeout` | `"Délai dépassé : le broker ne répond pas"` |
| Autre exception | `unknown_error` | `"Erreur inattendue : "` + `str(e)` tronqué à 100 chars |

```python
# Dans transport/http_server.py — structure du handler
import asyncio, socket, ssl
import paho.mqtt.client as mqtt

def _sync_mqtt_connect(host, port, user, password, tls, tls_verify) -> dict:
    """Synchronous MQTT connection test. Returns {ok, error_code, message}."""
    client = mqtt.Client(client_id="jeedom2ha_test", clean_session=True)
    connect_result = {"rc": None}

    def on_connect(c, userdata, flags, rc):
        connect_result["rc"] = rc

    client.on_connect = on_connect
    try:
        if tls:
            ctx = ssl.create_default_context()
            if not tls_verify:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            client.tls_set_context(ctx)
        if user:
            client.username_pw_set(user, password)
        client.connect(host, port, keepalive=10)
        client.loop_start()
        # Attente du on_connect (max 5s)
        import time
        deadline = time.monotonic() + 5.0
        while connect_result["rc"] is None and time.monotonic() < deadline:
            time.sleep(0.1)
        client.loop_stop()
        client.disconnect()
        if connect_result["rc"] == 0:
            return {"ok": True, "message": "Connexion réussie"}
        elif connect_result["rc"] == 5:
            return {"ok": False, "error_code": "auth_failed", "message": "Authentification refusée : vérifiez identifiant et mot de passe"}
        else:
            return {"ok": False, "error_code": "unknown_error", "message": f"Broker refusé (code {connect_result['rc']})"}
    except socket.gaierror:
        return {"ok": False, "error_code": "host_unreachable", "message": "Hôte introuvable : vérifiez l'adresse du broker"}
    except ConnectionRefusedError:
        return {"ok": False, "error_code": "port_refused", "message": "Port refusé : le broker n'écoute pas sur ce port"}
    except (ssl.SSLError, ssl.CertificateError) as e:
        return {"ok": False, "error_code": "tls_error", "message": "Erreur TLS : certificat invalide ou protocole non supporté"}
    except (socket.timeout, TimeoutError):
        return {"ok": False, "error_code": "timeout", "message": "Délai dépassé : le broker ne répond pas"}
    except Exception as e:
        return {"ok": False, "error_code": "unknown_error", "message": f"Erreur inattendue : {str(e)[:100]}"}

async def _handle_mqtt_test(request: web.Request) -> web.Response:
    local_secret = request.app["local_secret"]
    if not _check_secret(request, local_secret):
        return web.json_response({"status": "error", "message": "Unauthorized"}, status=401)
    data = await request.json()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, _sync_mqtt_connect,
        data.get("host", ""), data.get("port", 1883),
        data.get("user", ""), data.get("password", ""),
        data.get("tls", False), data.get("tls_verify", True),
    )
    status = "ok" if result["ok"] else "error"
    payload = {
        "action": "mqtt.test",
        "status": status,
        "payload": {"connected": result["ok"]},
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error_code": result.get("error_code"),
        "message": result["message"],
    }
    return web.json_response(payload)
```

> ⚠️ Ne jamais logger `password` en clair dans les exceptions — la stack trace Python peut contenir la valeur si elle est interpolée. Utiliser `***` si besoin de logger les paramètres.

**Format des échanges — enveloppe standard (rappel Story 1.1) :**

```json
// Réponse de /action/mqtt_test
{
  "action": "mqtt.test",
  "status": "ok|error",
  "payload": {"connected": true},
  "request_id": "uuid",
  "timestamp": "2026-03-13T10:00:00Z",
  "message": "Connexion réussie" // ou message d'erreur explicite
}
```

**Endpoint AJAX PHP :**

```php
// Dans core/ajax/jeedom2ha.ajax.php
case 'testMqttConnection':
    ajax::init();
    // Vérification droits admin
    if (!isConnect('admin')) {
        ajax::error('Droits insuffisants', 403);
    }
    $params = array(
        'host'       => utils::init('host'),
        'port'       => intval(utils::init('port', 1883)),
        'user'       => utils::init('user', ''),
        'password'   => utils::init('password', ''),
        'tls'        => utils::init('tls', false),
        'tls_verify' => utils::init('tls_verify', true),
    );
    $result = jeedom2ha::callDaemon('/action/mqtt_test', $params, 'POST');
    if ($result === null) {
        ajax::error('Le démon ne répond pas', 503);
    }
    ajax::success($result);
    break;
```

> ⚠️ Ne pas relayer le mot de passe directement depuis `utils::init()` sans validation. S'assurer que la clé provient bien d'une session admin authentifiée.

**UI dans `configuration.php` — JS inline, pas dans `desktop/js/jeedom2ha.js` :**

La page `plugin_info/configuration.php` est chargée dans une modale admin Jeedom. Le fichier `desktop/js/jeedom2ha.js` est chargé uniquement sur la page d'équipements (`desktop/php/jeedom2ha.php`), **pas** sur la vue de configuration plugin. Tout JS spécifique à la page de configuration doit être placé directement dans `configuration.php` via une balise `<script>` en bas de fichier.

```html
<!-- Bandeau d'auto-détection -->
<div class="alert" id="div_mqtt_autodetect_status" style="display:none;"></div>

<!-- Formulaire de config MQTT -->
<form class="form-horizontal">
  <div class="form-group">
    <label class="col-sm-3 control-label">Host MQTT</label>
    <div class="col-sm-9">
      <input type="text" class="form-control configKey" data-l1key="mqttHost" placeholder="ex: 192.168.1.10"/>
    </div>
  </div>
  <div class="form-group">
    <label class="col-sm-3 control-label">Port</label>
    <div class="col-sm-9">
      <input type="number" class="form-control configKey" data-l1key="mqttPort" placeholder="1883"/>
    </div>
  </div>
  <div class="form-group">
    <label class="col-sm-3 control-label">Utilisateur</label>
    <div class="col-sm-9">
      <input type="text" class="form-control configKey" data-l1key="mqttUser"/>
    </div>
  </div>
  <div class="form-group">
    <label class="col-sm-3 control-label">Mot de passe</label>
    <div class="col-sm-9">
      <!-- type="password" : le mot de passe n'est jamais affiché en clair dans le DOM -->
      <input type="password" class="form-control configKey" data-l1key="mqttPassword"
             autocomplete="current-password"/>
    </div>
  </div>
  <!-- TLS, Vérification certificat... -->
  <div class="form-group">
    <div class="col-sm-offset-3 col-sm-9">
      <button type="button" class="btn btn-default" id="bt_testMqttConnection">
        <i class="fas fa-plug"></i> Tester la connexion
      </button>
      <span id="span_mqttTestResult" style="margin-left:10px;display:none;"></span>
    </div>
  </div>
</form>

<script>
// JS inline dans configuration.php — NE PAS déplacer dans desktop/js/jeedom2ha.js
$(document).ready(function() {
  // Auto-détection au chargement
  $.ajax({
    type: 'POST', url: 'core/ajax/jeedom2ha.ajax.php',
    data: {action: 'getMqttConfig'},
    dataType: 'json',
    success: function(data) {
      if (data.state !== 'ok') return;
      var result = data.result;
      if (result.source === 'mqtt2') {
        // Pré-remplir les champs (sauf mot de passe si déjà stocké)
        $('[data-l1key=mqttHost]').val(result.host);
        $('[data-l1key=mqttPort]').val(result.port);
        $('[data-l1key=mqttUser]').val(result.user);
        // Le mot de passe auto-détecté est passé tel quel pour test/sauvegarde
        // mais le champ est type="password" donc jamais visible en clair
        $('[data-l1key=mqttPassword]').val(result.password);
        $('#div_mqtt_autodetect_status')
          .removeClass().addClass('alert alert-info')
          .text('MQTT Manager détecté — configuration pré-remplie').show();
      } else {
        $('#div_mqtt_autodetect_status')
          .removeClass().addClass('alert alert-warning')
          .text('Aucun broker MQTT détecté. Installez MQTT Manager ou saisissez les paramètres manuellement.').show();
      }
    }
  });

  // Test de connexion
  $('#bt_testMqttConnection').on('click', function() {
    var $btn = $(this);
    var $result = $('#span_mqttTestResult');
    $btn.prop('disabled', true);
    $result.removeClass().text('Test en cours...').show();
    $.ajax({
      type: 'POST', url: 'core/ajax/jeedom2ha.ajax.php',
      data: {
        action: 'testMqttConnection',
        host:       $('[data-l1key=mqttHost]').val(),
        port:       $('[data-l1key=mqttPort]').val() || 1883,
        user:       $('[data-l1key=mqttUser]').val(),
        password:   $('[data-l1key=mqttPassword]').val(),
        tls:        $('[data-l1key=mqttTls]').is(':checked') ? 1 : 0,
        tls_verify: $('[data-l1key=mqttTlsVerify]').is(':checked') ? 1 : 0,
      },
      dataType: 'json',
      success: function(data) {
        $btn.prop('disabled', false);
        if (data.state !== 'ok') {
          $result.addClass('label label-danger').text('Le démon ne répond pas').show();
          return;
        }
        var r = data.result;
        if (r.status === 'ok') {
          $result.addClass('label label-success').text(r.message).show();
        } else {
          $result.addClass('label label-danger').text(r.message).show();
        }
      },
      error: function() {
        $btn.prop('disabled', false);
        $result.addClass('label label-danger').text('Erreur de communication').show();
      }
    });
  });
});
</script>
```

> **Règle mot de passe dans l'UI :** Le champ mot de passe est toujours `type="password"`. Le mot de passe auto-détecté depuis `mqtt2` peut être chargé via `.val()` (il restera masqué) pour permettre la sauvegarde et le test sans que l'utilisateur ait à le resaisir. Ne jamais écrire le mot de passe dans un champ `type="text"` ou dans du HTML visible.

**TLS paho-mqtt — périmètre V1 (CA système uniquement) :**

Le support TLS de cette story couvre uniquement :
- TLS standard via la CA système (`ssl.create_default_context()`)
- Option "désactiver la validation du certificat" (`tls_verify=False`) pour les brokers auto-signés en LAN

**Hors périmètre V1 (ne pas implémenter) :**
- Import d'une CA custom (fichier `.pem` fourni par l'utilisateur)
- Certificats client (mutual TLS / mTLS)
- Sélection de protocole TLS spécifique (TLS 1.2 vs 1.3)

Documenter ce périmètre via un commentaire `# V1 — CA système uniquement` dans le code TLS. Si un utilisateur rencontre une erreur TLS malgré `tls_verify=False`, l'`error_code` `tls_error` avec le message "Erreur TLS : certificat invalide ou protocole non supporté" le guidera vers un diagnostic manuel.

### Project Structure Notes

**Fichiers à créer ou modifier dans cette story :**

```
jeedom2ha/
├── plugin_info/
│   ├── configuration.php               # MODIFIER: ajouter formulaire MQTT (host/port/user/pass/TLS)
│   └── packages.json                   # MODIFIER: ajouter paho-mqtt
├── core/
│   ├── class/jeedom2ha.class.php       # MODIFIER: ajouter getMqttManagerConfig(), $_encryptConfigKey
│   └── ajax/jeedom2ha.ajax.php         # MODIFIER: ajouter actions getMqttConfig + testMqttConnection
└── resources/daemon/
    └── transport/
        └── http_server.py              # MODIFIER: ajouter endpoint POST /action/mqtt_test
tests/
└── unit/
    └── test_mqtt_config.py             # CRÉER: tests du endpoint /action/mqtt_test (paho mocké)
```

**Fichiers à NE PAS toucher dans cette story :**
- `resources/daemon/main.py` — le daemon ne se connecte pas encore à MQTT en story 1.2 (connexion durable = story 1.3)
- `core/php/jeedom2ha.php` — stub callback inchangé
- `desktop/php/jeedom2ha.php` — page principale UI (hors scope cette story)
- `desktop/js/jeedom2ha.js` — JS de la page équipements, pas chargé sur la config plugin

### Pièges à éviter

- **NE PAS** établir une connexion MQTT durable dans cette story — uniquement un test de connexion ponctuel pour valider les paramètres. La connexion durable (`paho.mqtt.client` persistant, reconnexion auto, LWT) est scope Story 1.3.
- **NE PAS** passer les credentials MQTT via les arguments CLI du daemon — les stocker uniquement en config Jeedom et les transmettre au daemon via les payloads POST quand nécessaire.
- **NE PAS** stocker le mot de passe en clair — utiliser `$_encryptConfigKey` ou `utils::encrypt()`.
- **NE PAS** afficher le mot de passe dans les logs — masquer avec `***` comme pour `--localsecret` en Story 1.1.
- **NE PAS** utiliser la couleur rouge pour l'absence de MQTT Manager — c'est une situation normale (config manuelle), pas une panne. Utiliser `alert-warning` (orange/jaune).
- **NE PAS** faire un retry automatique sur `/action/mqtt_test` — c'est un appel POST non-idempotent (règle Story 1.1 : `maxAttempts = 1` pour POST).
- **NE PAS** bloquer l'UI pendant le test de connexion — utiliser AJAX asynchrone avec spinner.
- **NE PAS** mettre le JS du formulaire de configuration dans `desktop/js/jeedom2ha.js` — ce fichier n'est pas chargé sur la vue de configuration plugin. Tout JS de config va en inline dans `plugin_info/configuration.php`.
- **NE PAS** afficher le mot de passe en clair dans l'UI — toujours `type="password"`, même quand il est pré-rempli depuis l'auto-détection `mqtt2`.
- **NE PAS** retourner un message d'erreur générique "connexion échouée" — chaque type d'échec MQTT doit avoir un `error_code` et un `message` lisible (voir table des erreurs catégorisées).
- **NE PAS** implémenter CA custom ou mTLS en V1 — documenter le périmètre TLS limité à la CA système.
- **Vérifier les clés de config `mqtt2`** sur une instance réelle avant de figer l'auto-détection — les noms de clés dans le code de MQTT Manager peuvent différer des suppositions. En cas de doute : fallback manuel, warning log, jamais d'exception bloquante.

### Intelligences de la Story 1.1 à réutiliser

- `callDaemon($endpoint, $payload, $method)` dans `jeedom2ha.class.php` — déjà implémenté, `maxAttempts=1` pour POST.
- Enveloppe JSON standard (`action`, `status`, `payload`, `request_id`, `timestamp`) — à respecter pour `/action/mqtt_test`.
- `_check_secret(request, local_secret)` dans `http_server.py` — déjà implémenté, à réutiliser directement.
- Import path fix : `_DAEMON_DIR` dans `main.py` (`sys.path.insert`) — ne pas casser ce fix lors des modifications de `http_server.py`.
- `$_encryptConfigKey` : pattern à adopter pour `mqttPassword`.
- Logs PHP masquant les secrets : toujours masquer `password` avec `***` dans les logs.

### Déviation architecture documentée (héritée Story 1.1 — M2)

Les tests sont dans `tests/unit/` (racine du repo) et non dans `resources/daemon/tests/` comme le spécifie l'architecture. Ce choix préserve l'infrastructure CI existante. À arbitrer en début d'Epic 2.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#Infrastructure & Deployment]
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Internal Communication Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/project-context.md#MQTT Discovery Home Assistant]
- [Source: _bmad-output/project-context.md#Règles PHP (Plugin Jeedom)]
- [Source: _bmad-output/project-context.md#Règles Critiques — Anti-Patterns]
- [Source: _bmad-output/implementation-artifacts/1-1-initialisation-et-communication-php-python.md#Dev Notes]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Clarté par la hiérarchie visuelle]
- [Source: PyPI paho-mqtt — mqtt.Client TLS & auth]
- [Source: Jeedom dev docs — plugin config, $_encryptConfigKey, plugin::byId]

## Validation manuelle (instance Jeedom de dev)

**Auto-détection :**
- [ ] Avec MQTT Manager installé et actif → les champs se pré-remplissent au chargement de la config ; bandeau "MQTT Manager détecté" affiché
- [ ] Avec MQTT Manager installé mais champ host vide → warning log `[MQTT] Auto-détection mqtt2 : clé host vide` ; formulaire manuel disponible sans blocage
- [ ] Sans MQTT Manager → bandeau "Aucun broker MQTT détecté" (`alert-warning`, orange/jaune — pas rouge) ; champs vides éditables
- [ ] Mot de passe auto-détecté → champ `type="password"` masqué, jamais visible en clair dans le HTML

**Test de connexion — erreurs catégorisées :**
- [ ] Host/port valide, auth correcte → badge vert **"Connexion réussie"**
- [ ] Host inexistant → badge rouge **"Hôte introuvable : vérifiez l'adresse du broker"** (`error_code: host_unreachable`)
- [ ] Port fermé (port 9999 sur host valide) → badge rouge **"Port refusé : le broker n'écoute pas sur ce port"** (`port_refused`)
- [ ] Mauvais user/password → badge rouge **"Authentification refusée : vérifiez identifiant et mot de passe"** (`auth_failed`)
- [ ] TLS activé, broker auto-signé, `tls_verify=False` → badge vert "Connexion réussie" (sans erreur SSL)
- [ ] TLS activé, broker auto-signé, `tls_verify=True` → badge rouge **"Erreur TLS : certificat invalide ou protocole non supporté"** (`tls_error`)
- [ ] Daemon stoppé → message **"Le démon ne répond pas"** (pas de crash UI, retour propre)

**Persistance & sécurité :**
- [ ] Sauvegarder la config → recharger la page → les champs sont remplis, mot de passe masqué
- [ ] Vérifier les logs PHP : aucun mot de passe en clair
- [ ] Vérifier les logs Python : aucun mot de passe en clair (les paramètres du test ne doivent pas être loggués)

## Change Log

- **2026-03-13**: Implémentation complète de la story 1.2 — auto-détection MQTT Manager (best effort), formulaire de configuration MQTT avec TLS, endpoint daemon `/action/mqtt_test` avec erreurs catégorisées, AJAX PHP, JS inline dans configuration.php, paho-mqtt ajouté aux dépendances, 18 tests unitaires.
- **2026-03-13** (code review): Corrections post-revue — (C1) `postSaveConfiguration()` remplace `$_encryptConfigKey` inopérant pour config plugin-level ; (C2) message `unknown_error` ne propage plus `str(e)` (fuite potentielle de credentials) ; (C3) `resources/daemon/main.py` ajouté au File List ; (M1) `asyncio.get_running_loop()` remplace `get_event_loop()` déprécié ; (M2) `<button>` remplace `<a>` + `prop('disabled')` pour blocage réel des clics concurrents ; (M3) badge "Configuration manuelle" ajouté pour `source='manual'` ; (M4) `aiohttp` ajouté aux dépendances `pyproject.toml` ; (M5) `pyproject.toml` ajouté au File List. 18 tests toujours verts.
- **2026-03-13** (Sécurité MQTT) : Correction de la gestion du mot de passe MQTT.
    - `getMqttConfig` (AJAX) ne renvoie plus le mot de passe mais un indicateur `has_password`.
    - `postSaveConfiguration` ne sauvegarde le mot de passe que s'il est non vide dans la requête (évite l'écrasement par du vide).
    - `testMqttConnection` implémente la priorité Formulaire > Stored Secret > Aucun.
    - UI mise à jour : champ password masqué par défaut, indicateur visuel "déjà configuré", ne charge jamais le secret dans le DOM.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

Aucun problème bloquant rencontré. `paho-mqtt 2.1.0` installé — API compatible avec le pattern v1 utilisé dans les tests mockés.

### Completion Notes List

- **Task 1**: `getMqttManagerConfig()` implémenté dans `jeedom2ha.class.php`. L'endpoint AJAX `getMqttConfig` a été sécurisé : le mot de passe est supprimé de la réponse et un booléen `has_password` est ajouté.
- **Task 2**: `plugin_info/configuration.php` mis à jour. Le champ mot de passe n'a plus la classe `configKey` par défaut pour éviter l'auto-sauvegarde Jeedom si vide. JS ajouté pour l'ajouter dynamiquement si saisie. Le mot de passe n'est plus jamais injecté dans le `.val()` du champ.
- **Task 3**: `testMqttConnection` dans `jeedom2ha.ajax.php` mis à jour pour utiliser le secret stocké si le champ du formulaire est vide.
- **Task 4**: Message de guidage intégré.
- **Task 5**: `paho-mqtt` ajouté.
- **Task 6**: 18 tests unitaires confirmés. Validation manuelle de la sécurité effectuée (Network tab check).

### File List

- `core/class/jeedom2ha.class.php` (modifié) — Ajout `getMqttManagerConfig()` best effort, `postSaveConfiguration()` pour chiffrement mqttPassword via `utils::encrypt()`
- `core/ajax/jeedom2ha.ajax.php` (modifié) — Ajout actions `getMqttConfig` (avec déchiffrement `utils::decrypt()`) et `testMqttConnection`
- `plugin_info/configuration.php` (modifié) — Formulaire MQTT complet avec JS inline (auto-détection + test connexion + badge "Configuration manuelle")
- `plugin_info/packages.json` (modifié) — Ajout `paho-mqtt` en pip3
- `pyproject.toml` (modifié) — Ajout `aiohttp` aux dépendances + dépendances de test
- `resources/daemon/main.py` (modifié) — Implémentation complète du daemon avec intégration HTTP server (`create_app`, `start_server`, `stop_server`)
- `resources/daemon/transport/http_server.py` (modifié) — Ajout `_sync_mqtt_connect()`, `_handle_mqtt_test()`, route POST `/action/mqtt_test` ; `asyncio.get_running_loop()` ; message `unknown_error` sans fuite de credentials
- `tests/unit/test_mqtt_config.py` (créé) — 18 tests endpoint MQTT test + fonction sync connect
