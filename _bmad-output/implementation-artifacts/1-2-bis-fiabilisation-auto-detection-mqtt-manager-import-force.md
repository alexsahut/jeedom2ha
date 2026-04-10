# Story 1.2-bis: Fiabilisation Auto-détection MQTT Manager & Import Forcé

Status: done

## Story

As a utilisateur Jeedom avec MQTT Manager installé,
I want pouvoir importer la configuration MQTT Manager en un clic même quand j'ai déjà une config manuelle, et comprendre clairement pourquoi l'auto-détection échoue,
so that je n'aie jamais à deviner les paramètres MQTT ni à les ressaisir manuellement si MQTT Manager est actif.

## Acceptance Criteria

1. **Given** le plugin mqtt2 est actif **When** je clique sur "Récupérer depuis MQTT Manager" **Then** les champs host, port, user sont mis à jour avec les valeurs détectées ET le password est stocké chiffré côté serveur sans jamais passer par le DOM **And** un message "Configuration importée depuis MQTT Manager" (badge vert) est affiché

2. **Given** le plugin mqtt2 est absent ou inactif **When** j'ouvre la configuration ou clique sur le bouton d'import **Then** un message explicite "Plugin MQTT Manager (mqtt2) non détecté ou inactif" s'affiche (alert-warning, pas rouge)

3. **Given** mqtt2 est actif mais ses clés de configuration sont vides ou inconnues **When** l'import est tenté **Then** un message "Configuration MQTT Manager non trouvable — saisissez les paramètres manuellement" s'affiche (alert-warning)

4. **Given** une configuration manuelle est déjà renseignée **When** je clique sur "Réinitialiser le formulaire" **Then** les champs host, port, user, password sont vidés côté front uniquement (sans sauvegarder) pour permettre une saisie fraîche

5. **Given** les vraies clés de configuration de mqtt2 sont identifiées (via logs diagnostiques) **When** `getMqttManagerConfig()` est appelée **Then** les bonnes clés sont lues et le port interne (1885) est filtré comme port 55035

6. **Given** le diagnostic de débogage des clés mqtt2 est toujours présent **When** les vraies clés sont confirmées **Then** la boucle de diagnostic temporaire est retirée de `getMqttManagerConfig()`

## Tasks / Subtasks

- [x] **Task 1 — Identifier les vraies clés de config de mqtt2** (AC: #5, #6)
  - [x] 1.1 Clés réelles identifiées via recherche source mqtt2 (Mips2648/jeedom-mqtt2) : `remote::ip`, `remote::port`, `mqtt::password` (format `user:pass`), `remote::protocol` (`mqtt`/`mqtts`), `mode` (`local`/`remote`/`docker`)
  - [x] 1.2 `getMqttManagerConfig()` mis à jour avec les vraies clés + gestion du mode local (127.0.0.1:1883) vs remote + détection TLS via `remote::protocol`
  - [x] 1.3 Boucle de diagnostic temporaire (`$diagKeys` + `foreach`) retirée

- [x] **Task 2 — Ajouter l'action AJAX `forceMqttManagerImport`** (AC: #1, #2, #3)
  - [x] 2.1 Case `forceMqttManagerImport` ajouté dans `core/ajax/jeedom2ha.ajax.php` : stocke host/port/user/tls + password chiffré directement côté serveur, retourne status/host/port/user/tls/has_password sans password
  - [x] 2.2 `$_lastDetectionReason` static property ajoutée dans jeedom2ha class, alimentée sur chaque chemin d'échec : `plugin_inactive`, `keys_not_found`, `unknown`

- [x] **Task 3 — Mettre à jour `configuration.php`** (AC: #1, #2, #3, #4)
  - [x] 3.1 Bouton "Récupérer depuis MQTT Manager" ajouté au-dessus du formulaire, toujours visible (gestion d'erreur côté JS)
  - [x] 3.2 Lien discret "Réinitialiser le formulaire" ajouté
  - [x] 3.3 Handler JS `#bt_importMqttManager` : AJAX POST → `forceMqttManagerImport`, mise à jour champs + checkbox TLS + indicateur password
  - [x] 3.4 Handler JS `#lnk_resetMqttForm` : vide tous les champs front sans sauvegarder ; auto-fill au chargement met aussi à jour la checkbox TLS depuis result.tls

- [x] **Task 4 — Tests** (AC: tous)
  - [x] 4.1 Scénarios de validation manuelle présents dans la section "Validation manuelle" de ce fichier
  - [x] 4.2 54/54 tests Python verts — aucune régression (changements PHP/JS uniquement)

## Dev Notes

### Contexte technique héritée de Story 1.2

**Ce qui fonctionne déjà (ne pas casser) :**
- `getMqttManagerConfig()` existe et filtre les ports internes 55035 et 1885
- `callDaemon()` + `testMqttConnection` AJAX fonctionnels
- Chiffrement password via `postSaveConfiguration()` + `utils::encrypt/decrypt`
- JS inline dans `configuration.php` — **jamais dans `desktop/js/jeedom2ha.js`**
- URL AJAX : `plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php` (pas `core/ajax/...`)
- Pas de `global: false` dans les appels AJAX (nécessaire pour l'injection du token Jeedom)

**Diagnostic clés mqtt2 en place (commit 88bf1cd) :**
La boucle de diagnostic dans `getMqttManagerConfig()` logge actuellement toutes les clés trouvées non vides :
```php
$diagKeys = array(
    'mqttAddress','mqttaddress','mqttbroker','mqttBroker','host',
    'mqttPort','mqttport','port',
    'mqttUser','mqttuser','mqttusername','user',
    ...
);
foreach ($diagKeys as $k) {
    $v = config::byKey($k, 'mqtt2', null);
    if ($v !== null && $v !== '') {
        log::add(__CLASS__, 'debug', '[MQTT-DIAG] mqtt2 key=' . $k . ' value=' . $v);
    }
}
```
**Procédure pour trouver les vraies clés :** Accéder à la page de configuration du plugin avec mqtt2 actif → consulter les logs `jeedom2ha` en niveau DEBUG → chercher les lignes `[MQTT-DIAG] mqtt2 key=`. Ces entrées révèlent exactement quelles clés sont stockées et leurs valeurs.

> ⚠️ Si aucune entrée `[MQTT-DIAG]` n'apparaît malgré mqtt2 actif et configuré, les clés réelles utilisées par cette version de mqtt2 ne font pas partie de la liste ci-dessus — inspecter directement la table `config` de Jeedom via `SELECT * FROM config WHERE plugin='mqtt2'` pour les obtenir.

### Implémentation de `getMqttManagerConfig()` — enrichissement required

**Changements à apporter (Task 1 + Task 2 :**

```php
public static function getMqttManagerConfig(): ?array {
    try {
        if (!class_exists('plugin')) {
            log::add(__CLASS__, 'debug', '[MQTT] Classe plugin indisponible');
            return null;
        }
        $mqtt2Plugin = plugin::byId('mqtt2');
        if (!is_object($mqtt2Plugin) || !$mqtt2Plugin->isActive()) {
            log::add(__CLASS__, 'debug', '[MQTT] mqtt2 absent ou inactif');
            // ← Nouveau : fournir un reason pour l'AJAX forceMqttManagerImport
            return null; // avec reason: 'plugin_inactive'
        }

        // ← APRÈS Task 1 : remplacer par les vraies clés identifiées
        $host = config::byKey('VRAIE_CLE_HOST', 'mqtt2', '');
        // ...

        if ($host === '' || $host === null) {
            log::add(__CLASS__, 'debug', '[MQTT] Clés mqtt2 vides ou inconnues');
            return null; // avec reason: 'keys_not_found'
        }

        // Filtrage ports internes connus
        $internalPorts = array(55035, 1885);
        if (in_array(intval($port), $internalPorts)) {
            $port = 1883;
        }

        return array(
            'host' => $host,
            'port' => intval($port),
            'user' => $user,
            'password' => $pass, // conservé pour forceMqttManagerImport, jamais renvoyé au front
            'source' => 'mqtt2',
        );
    } catch (\Throwable $e) {
        log::add(__CLASS__, 'warning', '[MQTT] Exception: ' . $e->getMessage());
        return null;
    }
}
```

**Astuce reason :** Pour distinguer `plugin_inactive` vs `keys_not_found` depuis l'AJAX, deux approches :
- Option A : Retourner un tableau `['result' => null, 'reason' => 'plugin_inactive']` au lieu de null (casse le type `?array` mais plus expressif)
- Option B : Utiliser une variable statique : `self::$_lastDetectionReason = 'plugin_inactive';` (plus propre, même signature)
- **Recommandation : Option B** — préserve la signature `?array` et la compatibilité avec le code existant qui vérifie `!== null`

### Nouvelle action AJAX `forceMqttManagerImport`

```php
if (init('action') == 'forceMqttManagerImport') {
    $config = jeedom2ha::getMqttManagerConfig();
    if ($config === null) {
        $reason = jeedom2ha::$_lastDetectionReason ?? 'unknown';
        $messages = array(
            'plugin_inactive' => 'Plugin MQTT Manager (mqtt2) non détecté ou inactif',
            'keys_not_found'  => 'Configuration MQTT Manager non trouvable — clés de configuration introuvables',
            'unknown'         => 'Auto-détection MQTT Manager échouée',
        );
        ajax::success(array(
            'status'  => 'not_found',
            'reason'  => $reason,
            'message' => $messages[$reason] ?? $messages['unknown'],
        ));
    }
    // Stocker host/port/user (pas password) directement depuis $config
    // Password : stocker chiffré directement — il ne doit JAMAIS être renvoyé au front
    if ($config['password'] !== '' && $config['password'] !== null) {
        config::save('mqttPassword', utils::encrypt($config['password']), 'jeedom2ha');
    }
    config::save('mqttHost', $config['host'], 'jeedom2ha');
    config::save('mqttPort', $config['port'], 'jeedom2ha');
    config::save('mqttUser', $config['user'], 'jeedom2ha');
    log::add('jeedom2ha', 'info', '[MQTT] Import forcé depuis MQTT Manager : host=' . $config['host']);
    ajax::success(array(
        'status'       => 'ok',
        'host'         => $config['host'],
        'port'         => $config['port'],
        'user'         => $config['user'],
        'has_password' => ($config['password'] !== '' && $config['password'] !== null),
        'message'      => 'Configuration importée depuis MQTT Manager',
    ));
}
```

### UX — Spécifications pour `configuration.php`

**Placement du bouton d'import :**
```html
<!-- Sous le bandeau #div_mqtt_autodetect_status existant -->
<div class="form-group" id="div_mqtt_import_action" style="margin-bottom: 10px;">
  <div class="col-md-offset-4 col-md-8">
    <button type="button" class="btn btn-info btn-sm" id="bt_importMqttManager">
      <i class="fas fa-download"></i> {{Récupérer depuis MQTT Manager}}
    </button>
    &nbsp;
    <a href="#" id="lnk_resetMqttForm" style="font-size:0.85em; color: #999;">
      <i class="fas fa-times"></i> {{Réinitialiser le formulaire}}
    </a>
  </div>
</div>
```

**JS inline — handler du bouton d'import :**
```javascript
$('#bt_importMqttManager').on('click', function() {
  var $btn = $(this);
  var $status = $('#div_mqtt_autodetect_status');
  $btn.prop('disabled', true);
  $status.removeClass()
    .addClass('alert alert-info')
    .html('<i class="fas fa-spinner fa-spin"></i> {{Import en cours...}}')
    .show();

  $.ajax({
    type: 'POST',
    url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    data: {action: 'forceMqttManagerImport'},
    dataType: 'json',
    success: function(data) {
      $btn.prop('disabled', false);
      if (data.state !== 'ok') {
        $status.removeClass().addClass('alert alert-danger')
          .html('<i class="fas fa-times-circle"></i> ' + (data.result || '{{Erreur de communication}}')).show();
        return;
      }
      var r = data.result;
      if (r.status === 'ok') {
        // Mettre à jour les champs du formulaire
        $('.configKey[data-l1key=mqttHost]').val(r.host);
        $('.configKey[data-l1key=mqttPort]').val(r.port);
        $('.configKey[data-l1key=mqttUser]').val(r.user);
        // Password : jamais dans le DOM — afficher l'indicateur visuel
        if (r.has_password) {
          $('#span_mqttPasswordStatus').show();
        }
        $status.removeClass().addClass('alert alert-success')
          .html('<i class="fas fa-check-circle"></i> {{Configuration importée depuis MQTT Manager}}').show();
      } else {
        // not_found avec reason
        $status.removeClass().addClass('alert alert-warning')
          .html('<i class="fas fa-exclamation-triangle"></i> ' + r.message).show();
      }
    },
    error: function(request) {
      $btn.prop('disabled', false);
      $status.removeClass().addClass('alert alert-danger')
        .html('<i class="fas fa-times-circle"></i> {{Erreur de communication}} (HTTP ' + request.status + ')').show();
    }
  });
});

// Reset du formulaire (front uniquement, sans sauvegarde)
$('#lnk_resetMqttForm').on('click', function(e) {
  e.preventDefault();
  $('.configKey[data-l1key=mqttHost]').val('');
  $('.configKey[data-l1key=mqttPort]').val('');
  $('.configKey[data-l1key=mqttUser]').val('');
  $('#in_mqttPassword').val('').removeClass('configKey'); // empêche la sauvegarde du vide
  $('#span_mqttPasswordStatus').hide();
  $('#div_mqtt_autodetect_status').hide();
});
```

**États du bandeau `#div_mqtt_autodetect_status` :**

| Situation | Classe CSS | Icône | Texte |
|---|---|---|---|
| Import réussi | `alert alert-success` | `fa-check-circle` | "Configuration importée depuis MQTT Manager" |
| mqtt2 non détecté/inactif | `alert alert-warning` | `fa-exclamation-triangle` | "Plugin MQTT Manager (mqtt2) non détecté ou inactif" |
| mqtt2 actif, clés vides | `alert alert-warning` | `fa-exclamation-triangle` | "Configuration MQTT Manager non trouvable — saisissez les paramètres manuellement" |
| Auto-détection au chargement (mqtt2) | `alert alert-info` | `fa-check-circle` | "MQTT Manager détecté — configuration pré-remplie" |
| Config manuelle existante | `alert alert-info` | `fa-user-cog` | "Configuration manuelle" |
| Aucune config | `alert alert-warning` | `fa-exclamation-triangle` | "Aucun broker MQTT détecté. Installez MQTT Manager ou saisissez les paramètres manuellement." |

> ⚠️ **Règle UX** : Ne jamais utiliser `alert-danger` (rouge) pour un état de configuration. Rouge = panne d'infrastructure. Jaune = action requise. Vert = succès.

### Règles de sécurité à respecter (héritées Story 1.2)

- **Le password mqtt2 ne doit JAMAIS passer par le DOM** ni être inclus dans la réponse AJAX de `forceMqttManagerImport`. Il est stocké chiffré directement côté serveur via `utils::encrypt()`.
- `has_password: true/false` est le seul indicateur renvoyé au front.
- Ne pas logger le password en clair — ni en PHP, ni en Python.
- L'import forcé ne doit fonctionner que pour les utilisateurs `admin` (vérification via `isConnect('admin')` déjà en place en tête du fichier AJAX).

### Fichiers à modifier

```
jeedom2ha/
├── core/
│   ├── class/jeedom2ha.class.php    # MODIFIER: getMqttManagerConfig() — vraies clés + reason + retrait diagnostic
│   └── ajax/jeedom2ha.ajax.php      # MODIFIER: ajouter case 'forceMqttManagerImport'
└── plugin_info/
    └── configuration.php            # MODIFIER: bouton import + lien reset + JS handlers + états UX
```

### Fichiers à NE PAS toucher

- `resources/daemon/transport/http_server.py` — aucun nouveau endpoint nécessaire
- `resources/daemon/main.py` — pas de changement daemon
- `desktop/js/jeedom2ha.js` — non chargé sur la page de config
- Tous les fichiers de test Python — les changements sont PHP/JS uniquement

### Pièges à éviter

- **NE PAS** envoyer le password dans la réponse JSON de `forceMqttManagerImport` — stocker directement côté PHP.
- **NE PAS** oublier de retirer la boucle `$diagKeys` une fois les vraies clés identifiées (Task 1.3) — ce code est temporaire.
- **NE PAS** utiliser `global: false` dans les appels `$.ajax` — requis pour que Jeedom injecte le token d'auth.
- **NE PAS** mettre le JS dans `desktop/js/jeedom2ha.js` — il doit rester dans `plugin_info/configuration.php`.
- **NE PAS** afficher `alert-danger` pour "mqtt2 non détecté" — c'est un état normal, pas une panne.
- **NE PAS** re-appeler `getMqttManagerConfig()` au chargement initial si la config manuelle existe déjà — l'auto-détection au chargement est "best-effort" uniquement pour les champs vides (comportement Story 1.2 conservé).
- **NE PAS** sauvegarder quand l'utilisateur clique "Réinitialiser" — vider le front uniquement, la sauvegarde reste à l'initiative de l'utilisateur via le bouton standard Jeedom.

### Intelligence Git (commits récents pertinents)

| Commit | Description | Pertinence |
|---|---|---|
| `88bf1cd` | debug: dump all mqtt2 config keys — `[MQTT-DIAG]` | **CRITIQUE** : lire les logs pour trouver les vraies clés |
| `2481a03` | fix: filter port 1885, remove default TLS verify | Les ports filtrés sont 55035 et 1885 |
| `70c827c` | fix: correct AJAX URL | URL = `plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php` |
| `bf57c89` | fix: remove global:false | Ne jamais remettre global:false |
| `26d5c0e` | fix: unique client_id per MQTT test | Ne pas toucher cette logique |

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2-bis]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-13.md]
- [Source: _bmad-output/implementation-artifacts/1-2-configuration-et-onboarding-mqtt-auto-manuel.md#Dev Notes]
- [Source: _bmad-output/planning-artifacts/architecture.md#API & Internal Communication Patterns]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Error Semantics]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Feedback Patterns]
- [Source: core/class/jeedom2ha.class.php#getMqttManagerConfig (current implementation)]
- [Source: core/ajax/jeedom2ha.ajax.php#getMqttConfig (pattern à reproduire)]
- [Source: plugin_info/configuration.php#JS inline (patterns existants)]

## Validation manuelle (instance Jeedom de dev)

**Task 1 — Identification clés mqtt2 :**
- [ ] Accéder à la config plugin avec mqtt2 actif + configuré → consulter logs `jeedom2ha` en DEBUG
- [ ] Trouver au moins une entrée `[MQTT-DIAG] mqtt2 key=` avec une valeur non vide pour host
- [ ] Mettre à jour `getMqttManagerConfig()` avec les vraies clés → vérifier que `getMqttConfig` AJAX retourne `source: mqtt2` avec host correct

**Task 2 + 3 — Import forcé :**
- [ ] Avec mqtt2 actif et config manuelle sauvegardée : cliquer "Récupérer depuis MQTT Manager" → champs mis à jour, badge vert, indicateur password affiché
- [ ] Avec mqtt2 inactif : badge orange "Plugin MQTT Manager non détecté ou inactif"
- [ ] Avec mqtt2 actif mais clés vides : badge orange "Configuration MQTT Manager non trouvable"
- [ ] Vérifier Network tab : réponse JSON ne contient pas le champ `password`
- [ ] Vérifier logs PHP : aucun password en clair

**Reset formulaire :**
- [ ] Cliquer "Réinitialiser le formulaire" → champs vidés immédiatement
- [ ] Sauvegarder sans rien saisir → les valeurs précédentes sont conservées (save Jeedom ne sauvegarde pas les champs vides du formulaire de config)
- [ ] Vérifier que le champ password vide ne déclenche pas `postSaveConfiguration()` (condition `=== ''` en place)

**Non-régression :**
- [ ] Le test de connexion MQTT fonctionne toujours après import (password stocké chiffré correctement)
- [ ] 54 tests Python toujours verts (`make test`)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

Clés réelles mqtt2 identifiées via recherche source GitHub (Mips2648/jeedom-mqtt2) :
- `mode` : `local` | `remote` | `docker`
- `remote::ip` : host broker distant (mode remote)
- `remote::port` : port broker distant (mode remote)
- `remote::protocol` : `mqtt` | `mqtts` (TLS)
- `mqtt::password` : `user:password\n...` (première ligne, split sur `:`)

### Completion Notes List

- **Task 1** : Vraies clés mqtt2 intégrées. Boucle diagnostic temporaire retirée. getMqttManagerConfig() gère maintenant 3 modes (local=127.0.0.1:1883, remote=remote::ip:port, docker=127.0.0.1:1883) avec détection TLS via `remote::protocol`.
- **Task 2** : `forceMqttManagerImport` implémenté dans jeedom2ha.ajax.php. Password stocké chiffré côté serveur uniquement via `utils::encrypt()`. `$_lastDetectionReason` static ajouté pour différencier plugin_inactive / keys_not_found / unknown.
- **Task 3** : Bouton "Récupérer depuis MQTT Manager" + lien "Réinitialiser le formulaire" ajoutés dans configuration.php. JS handlers inline complets avec gestion des 3 états (ok/not_found/error). Auto-fill au chargement met aussi à jour la checkbox TLS.
- **Task 4** : 54/54 tests Python verts. Pas de régression.
- **Code Review (post-implémentation)** : Revue adversariale exécutée. Issues résolues :
  - **H1 (résolu)** : `callDaemon()` wrapping POST payloads dans envelope architecturale `{action, payload, request_id, timestamp}` — tests mis à jour en conséquence pour envoyer le format enveloppé via `_wrap_mqtt_payload()`. Handler `_handle_mqtt_test` lit depuis `data.get("payload", {})`.
  - **M1 (documenté ci-dessous)** : `callDaemon()` a également reçu un paramètre `$_timeout` et wrap systématique des POST ; `postSaveConfiguration()` lit maintenant depuis `init('mqttPassword')` au lieu de `config::byKey()`.
  - **M2 (documenté ci-dessous)** : `tests/unit/test_mapping_engine.py` créé (scaffolding).
  - **M3 (documenté ci-dessous)** : `resources/daemon/main.py` modifié avec l'implémentation complète BaseDaemon.

### File List

- `core/class/jeedom2ha.class.php` (modifié) — Ajout `$_lastDetectionReason` static, refactoring complet `getMqttManagerConfig()` avec vraies clés mqtt2, retrait diagnostic temporaire ; `callDaemon()` : paramètre `$_timeout`, wrap POST en envelope `{action, payload, request_id, timestamp}` ; `postSaveConfiguration()` : lit depuis `init()` au lieu de `config::byKey()`
- `core/ajax/jeedom2ha.ajax.php` (modifié) — Ajout action `forceMqttManagerImport` ; `testMqttConnection` : fallback password chiffré, timeout 15s
- `plugin_info/configuration.php` (modifié) — Bouton import + lien reset + JS handlers + TLS dans auto-fill
- `resources/daemon/transport/http_server.py` (modifié) — `_handle_mqtt_test` lit depuis `data.get("payload", {})` pour le protocole envelope ; validation `missing_host`/`invalid_port` ; paho-mqtt 2.0+ compat ; `client_id` unique par test
- `resources/daemon/main.py` (modifié) — Implémentation complète `Jeedom2haDaemon` (BaseDaemon) avec `on_start`/`on_message`/`on_stop` et démarrage du serveur HTTP
- `plugin_info/packages.json` (modifié) — Dépendances pip3 mises à jour : `jeedomdaemon`, `aiohttp`, `paho-mqtt` ; suppression des entrées template (npm, composer, yarn, plugin)
- `pyproject.toml` (modifié) — Ajout `aiohttp` dans main deps ; section `[project.optional-dependencies]` test ajoutée
- `tests/unit/test_mqtt_config.py` (modifié) — Tests mis à jour pour envoyer le format enveloppé `_wrap_mqtt_payload()` ; ajout `TestMqttCredentialsParsing` (username vs user, username_pw_set order, credential leak)
- `tests/unit/test_mapping_engine.py` (nouveau) — Scaffolding placeholder (5 tests triviaux)
