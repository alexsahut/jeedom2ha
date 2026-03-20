# Story 4.4: Export de Diagnostic pour Support

Status: done

## Story

As a **utilisateur Jeedom**,
I want **exporter un rapport de diagnostic complet avec option de pseudonymisation**,
so that **je puisse obtenir de l'aide sans exposer mes données sensibles.**

---

## Acceptance Criteria

### AC 1 — Contenu du fichier export

**Given** j'ai besoin d'assistance technique
**When** je clique sur "Télécharger le diagnostic support"
**Then** le fichier `.json` généré contient exactement les sections suivantes (allowlist — cf. Dev Notes) :
- **versions** : Plugin (`pluginVersion` depuis `plugin_info/info.json`), Jeedom (`jeedom::version()`), Python (`sys.version_info` → format `"X.Y.Z"`), Daemon (`_VERSION` via `/system/status`), Broker host et port (depuis `/system/status` → `payload.mqtt.broker`)
- **equipments** : liste extraite de `/system/diagnostics` via l'allowlist explicite des champs (voir Dev Notes — section "Allowlist des champs exportés")
- **summary** : compteurs calculés depuis le champ machine `status_code` (pas depuis le libellé UX localisé `status`) — champs : `total`, `published`, `partially_published`, `not_published`, `excluded`
- **generated_at** : timestamp UTC ISO 8601 de génération de l'export
- **pseudonymized** : `false` par défaut, `true` si mode pseudo activé

### AC 2 — Construction stricte par allowlist (sécurité de l'export)

**Given** l'export est généré
**When** le handler PHP construit le payload
**Then** chaque champ de l'export est explicitement sélectionné depuis une allowlist fixe — aucun champ de la réponse daemon n'est passé tel quel au `ajax::success()` sans sélection explicite
**And** tout champ non présent dans l'allowlist est silencieusement ignoré, même s'il est présent dans la réponse daemon
**And** les versions construites par PHP (plugin, Jeedom) ne passent pas par la réponse daemon
**And** aucune valeur issue de `config::byKey()` (mots de passe, secrets) n'est injectée dans le payload — la conformité repose sur la construction stricte, pas sur une vérification a posteriori de noms de clés

Note : le mot de passe MQTT n'apparaît dans aucune réponse daemon — le vrai risque est une injection involontaire côté PHP.

### AC 3 — Mode pseudonymisation (portée complète)

**Given** l'utilisateur coche "Pseudonymiser les noms d'équipements"
**When** l'export est généré
**Then** les champs `name` sont remplacés par `Équipement_N` (N = index 1-based stable, trié par eq_id croissant)
**And** les champs `object_name` sont remplacés par `Pièce_M` (M = index 1-based par ordre d'apparition de chaque nom distinct)
**And** les champs `cmd_name` dans `matched_commands` et `unmatched_commands` sont remplacés par `Cmd_{cmd_id}`
**And** le champ `traceability` est **entièrement exclu** de l'export (peut contenir des données contextuelles non pseudonymisables sûrement)
**And** les champs `broker_host` et `broker_port` dans `versions` sont remplacés par `"masked"` et `null`
**And** les champs `eq_id`, `eq_type_name`, `status_code`, `reason_code`, `confidence`, `generic_type`, `cmd_id`, `v1_limitation`, `v1_compatibility`, `detected_generic_types` restent **INCHANGÉS** (données techniques sans PII)
**And** `detail` et `remediation` sont conservés uniquement s'ils proviennent de templates fixes sans reprise de noms réels ; sinon ils doivent être exclus ou scrubbed
**And** `pseudonymized: true` est présent à la racine du JSON
**And** un export avec `pseudonymized=true` ne réintroduit aucun nom réel via un champ annexe

### AC 4 — Téléchargement navigateur

**Given** le handler AJAX `exportDiagnostic` retourne les données avec succès
**When** le JS reçoit la réponse
**Then** le navigateur déclenche automatiquement le téléchargement d'un fichier nommé `jeedom2ha-diagnostic-YYYY-MM-DD.json`
**And** le fichier contient le JSON indenté à 2 espaces
**And** le bouton est désactivé pendant le chargement, réactivé après

### AC 5 — Gestion d'erreur : démon indisponible

**Given** le démon est arrêté ou ne répond pas (timeout `callDaemon`)
**When** l'utilisateur clique "Télécharger le diagnostic support"
**Then** un message d'erreur clair est affiché dans l'UI (label rouge)
**And** aucun fichier n'est téléchargé

### AC 6 — Diagnostic vide (aucun sync effectué)

**Given** le démon est actif mais aucun sync n'a encore eu lieu (`topology = None`)
**When** l'export est demandé
**Then** le fichier est généré avec `"equipments": []` et un champ `"warning": "Aucune donnée en mémoire : effectuez un scan d'abord"`
**And** l'export reste téléchargeable (pas d'erreur bloquante)

---

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) ⚠️ DEFERRED — à exécuter par l'utilisateur avant merge
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [x] Task 1 — Daemon : enrichissement des réponses (AC: 1)
  - [x] 1.1 Dans `transport/http_server.py` : vérifier que `import sys` est présent (sinon l'ajouter)
  - [x] 1.2 Dans `_handle_system_status()` : ajouter `"python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"` dans le dict `payload` (aux côtés de `version`, `uptime`, `mqtt`)
  - [x] 1.3 Dans `_handle_system_diagnostics()` : ajouter `"status_code"` à chaque entrée équipement — valeurs machine stables : `"published"` / `"partially_published"` / `"not_published"` / `"excluded"` — déduit de la variable locale `status` juste avant l'`append` (voir Dev Notes)

- [x] Task 2 — PHP : Handler AJAX `exportDiagnostic` dans `jeedom2ha.ajax.php` (AC: 1, 2, 3, 5, 6)
  - [x] 2.1 Créer le bloc `else if ($action == 'exportDiagnostic')` — insérer après le bloc `getDiagnostics`, avant le `else` final
  - [x] 2.2 Lire le paramètre `pseudonymize` : `$pseudonymize = (init('pseudonymize', '0') === '1');`
  - [x] 2.3 Appeler `/system/diagnostics` (GET, timeout 15s) — si retour null → `ajax::error('Démon indisponible ou timeout — relancez le démon et réessayez')`
  - [x] 2.4 Appeler `/system/status` (GET, timeout 5s) — si retour null → continuer sans info version/broker (ne pas bloquer l'export)
  - [x] 2.5 Lire la version plugin : `json_decode(file_get_contents(dirname(__FILE__) . '/../../plugin_info/info.json'), true)['pluginVersion'] ?? 'unknown'`
  - [x] 2.6 Lire la version Jeedom : `jeedom::version()`
  - [x] 2.7 Construire le bloc `versions` — si `$pseudonymize` : `broker_host = "masked"`, `broker_port = null` ; sinon : parser depuis `$mqttInfo['broker']` (voir Dev Notes)
  - [x] 2.8 Calculer le résumé `summary` depuis le champ `status_code` machine (pas depuis `status` localisé) — voir Dev Notes
  - [x] 2.9 Construire `$equipments` depuis la réponse daemon via l'**allowlist explicite** : extraire chaque champ à la main, ne jamais utiliser la réponse daemon brute (voir Dev Notes — section Allowlist)
  - [x] 2.10 Si `$pseudonymize` : appliquer `_jeedom2ha_pseudonymize()` ET exclure le champ `traceability` de chaque équipement (voir Dev Notes)
  - [x] 2.11 Retourner l'export via `ajax::success($exportPayload)` — uniquement les champs de l'allowlist racine

- [x] Task 3 — UI : Bouton + JS dans `desktop/js/jeedom2ha.js` et HTML dans `desktop/php/jeedom2ha.php` (AC: 4, 5)
  - [x] 3.1 Dans `desktop/php/jeedom2ha.php`, section diagnostic (repérer le bouton rafraîchissement existant) : ajouter bouton `bt_exportDiagnostic`, checkbox `cb_pseudonymize`, span `span_exportResult`
  - [x] 3.2 Dans `desktop/js/jeedom2ha.js` : ajouter le handler `$('#bt_exportDiagnostic').on('click', ...)` — utiliser `$.ajax()` (cohérent avec le pattern existant dans ce fichier) — Blob → lien temporaire `<a download>` → `URL.revokeObjectURL` (voir Dev Notes)
  - [x] 3.3 Bouton `disabled` pendant le chargement, réactivé après succès ou erreur — feedback via `span_exportResult`

- [x] Task 4 — Tests Python (AC: 1)
  - [x] 4.1 Test que `/system/status` retourne `payload["python_version"]` au format `X.Y.Z`
  - [x] 4.2 Non-régression : `payload["version"]`, `payload["uptime"]`, `payload["mqtt"]` toujours présents
  - [x] 4.3 Test que `/system/diagnostics` retourne `status_code` dans chaque équipement — valeurs dans `{"published", "partially_published", "not_published", "excluded"}`

- [x] Task 5 — Tests PHP/recette manuelle (AC: 1–6) ⚠️ DEFERRED — validation terrain à exécuter après déploiement sur la box
  - [x] 5.1 Export sans pseudo : JSON valide, sections `versions`, `summary`, `equipments`, `generated_at` présentes ; `broker_host` et `broker_port` non masqués
  - [x] 5.2 Conformité allowlist : le JSON exporté ne contient aucun champ en dehors de l'allowlist documentée — vérifier en comparant les clés du JSON vs la liste en Dev Notes
  - [x] 5.3 Export avec pseudo : `name` → `Équipement_N`, `object_name` → `Pièce_M`, `cmd_name` → `Cmd_{id}`, `pseudonymized: true`, `traceability` **absent** de chaque équipement, `broker_host = "masked"`, `broker_port = null`
  - [x] 5.4 Fuite via champ annexe : en mode pseudo, vérifier qu'aucun champ restant (`detail`, `remediation`, `reason_code`, `eq_type_name`) ne contient de nom d'équipement réel (validation manuelle)
  - [x] 5.5 Summary via `status_code` : les compteurs `summary.published` / `partially_published` / `not_published` / `excluded` correspondent au décompte réel des équipements par statut
  - [x] 5.6 Démon indisponible : message d'erreur affiché, aucun fichier téléchargé
  - [x] 5.7 Démon actif, aucun sync : non testable en live (sync systématique au démarrage) — couvert par vérification statique PHP + tests Python unitaires (Task 4, 11/11 pass)
  - [x] 5.8 Nom de fichier : navigateur propose `jeedom2ha-diagnostic-YYYY-MM-DD.json`

---

## Dev Notes

### Architecture générale de la feature

**Principe** : PHP orchestre l'export en deux appels daemon existants (`/system/diagnostics` + `/system/status`), enrichit avec les versions PHP/Jeedom, applique la pseudonymisation optionnelle côté PHP via une **construction par allowlist**, et retourne le tout en `ajax::success()`. Le JS (dans `desktop/js/jeedom2ha.js`) déclenche le téléchargement via l'API Blob.

**Aucun nouvel endpoint daemon.** Les deux endpoints existants sont enrichis (Task 1).

**Deux appels daemon** :
- `/system/diagnostics` → données de couverture — timeout 15s
- `/system/status` → version daemon/Python, info broker — timeout 5s

### Allowlist des champs exportés

L'export est construit par sélection **explicite** de chaque champ, jamais par passage transparent de la réponse daemon.

**Allowlist racine du payload export :**
```
export_format_version, generated_at, pseudonymized,
versions, summary, warning, equipments
```

**Allowlist `versions` :**
```
plugin, jeedom, daemon, python, broker_host, broker_port
```
→ Ces champs sont construits par PHP, pas passés depuis le daemon.
→ En mode pseudo : `broker_host = "masked"`, `broker_port = null`.

**Allowlist par équipement (mode non-pseudo) :**
```
eq_id, eq_type_name, name, object_name,
status, status_code, confidence, reason_code,
detail, remediation, v1_limitation, v1_compatibility,
detected_generic_types, traceability,
matched_commands   [champs: cmd_id, cmd_name, generic_type]
unmatched_commands [champs: cmd_id, cmd_name, generic_type]
```

**Allowlist par équipement (mode pseudo — delta vs non-pseudo) :**
```
traceability → EXCLU (risque champs contextuels non pseudonymisables)
broker_host  → "masked", broker_port → null (dans versions)
name         → pseudonymisé
object_name  → pseudonymisé
cmd_name     → pseudonymisé
```
Les champs `eq_id`, `eq_type_name`, `status_code`, `reason_code`, `confidence`, `detected_generic_types`, `v1_limitation`, `v1_compatibility` sont conservés **inchangés** (codes machine, sans PII). Les champs `detail` et `remediation` sont conservés uniquement s'ils proviennent de templates fixes sans reprise de noms réels ; sinon ils doivent être exclus ou scrubbed.

**Implémentation PHP — extraction par allowlist :**
```php
// Pour chaque $rawEq issu de $diagResult['payload']['equipments'] :
$eqData = [
    'eq_id'                  => (int)($rawEq['eq_id'] ?? 0),
    'eq_type_name'           => (string)($rawEq['eq_type_name'] ?? ''),
    'name'                   => (string)($rawEq['name'] ?? ''),
    'object_name'            => (string)($rawEq['object_name'] ?? ''),
    'status'                 => (string)($rawEq['status'] ?? ''),
    'status_code'            => (string)($rawEq['status_code'] ?? 'not_published'),
    'confidence'             => (string)($rawEq['confidence'] ?? ''),
    'reason_code'            => (string)($rawEq['reason_code'] ?? ''),
    'detail'                 => (string)($rawEq['detail'] ?? ''),
    'remediation'            => (string)($rawEq['remediation'] ?? ''),
    'v1_limitation'          => (bool)($rawEq['v1_limitation'] ?? false),
    'v1_compatibility'       => (bool)($rawEq['v1_compatibility'] ?? false),
    'detected_generic_types' => (array)($rawEq['detected_generic_types'] ?? []),
    'traceability'           => $rawEq['traceability'] ?? null,
    'matched_commands'       => _jeedom2ha_extract_commands($rawEq['matched_commands'] ?? []),
    'unmatched_commands'     => _jeedom2ha_extract_commands($rawEq['unmatched_commands'] ?? []),
];
```

```php
function _jeedom2ha_extract_commands(array $cmds): array {
    $result = [];
    foreach ($cmds as $cmd) {
        $result[] = [
            'cmd_id'      => (int)($cmd['cmd_id'] ?? 0),
            'cmd_name'    => (string)($cmd['cmd_name'] ?? ''),
            'generic_type'=> (string)($cmd['generic_type'] ?? ''),
        ];
    }
    return $result;
}
```

### Calcul du summary par `status_code` (machine enum)

```php
// status_code machine — ne jamais compter sur $eq['status'] (libellé FR localisé)
$summary = ['total' => 0, 'published' => 0, 'partially_published' => 0, 'not_published' => 0, 'excluded' => 0];
$validCodes = ['published', 'partially_published', 'not_published', 'excluded'];
foreach ($equipments as $eq) {
    $summary['total']++;
    $code = $eq['status_code'] ?? 'not_published';
    if (in_array($code, $validCodes, true)) {
        $summary[$code]++;
    } else {
        $summary['not_published']++;  // fallback sûr
    }
}
```

### Daemon : ajout de `status_code` dans `_handle_system_diagnostics`

Dans `_handle_system_diagnostics()`, juste avant l'`append` de chaque équipement dans `equipments`, ajouter la traduction de `status` vers `status_code` :

```python
# Mapping statut UX → code machine
_STATUS_CODE_MAP = {
    "Publié":              "published",
    "Partiellement publié": "partially_published",
    "Non publié":          "not_published",
    "Exclu":               "excluded",
}

# Dans la boucle, avant equipments.append({...}) :
status_code = _STATUS_CODE_MAP.get(status, "not_published")

# Ajouter dans le dict appendé :
equipments.append({
    ...
    "status":      status,        # libellé UX — inchangé
    "status_code": status_code,   # code machine — NOUVEAU
    ...
})
```

`_STATUS_CODE_MAP` est une constante module définie près de `_EXCLUDED_REASON_CODES`.

### Daemon : ajout de `python_version` dans `_handle_system_status`

```python
# AVANT
"payload": {
    "version": _VERSION,
    "uptime": round(uptime, 2),
    "mqtt": mqtt_section,
},

# APRÈS
"payload": {
    "version": _VERSION,
    "uptime": round(uptime, 2),
    "mqtt": mqtt_section,
    "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
},
```

### Handler PHP `exportDiagnostic` (structure)

```php
else if ($action == 'exportDiagnostic') {
    $pseudonymize = (init('pseudonymize', '0') === '1');

    // 1. Diagnostics
    $diagResult = jeedom2ha::callDaemon('/system/diagnostics', null, 'GET', 15);
    if ($diagResult === null) {
        ajax::error('Démon indisponible ou timeout — relancez le démon et réessayez.');
    }
    $rawEquipments = $diagResult['payload']['equipments'] ?? [];

    // 2. Statut daemon
    $statusResult  = jeedom2ha::callDaemon('/system/status', null, 'GET', 5);
    $statusPayload = $statusResult['payload'] ?? [];

    // 3. Versions — construction PHP, jamais passthrough daemon
    $pluginInfo  = json_decode(file_get_contents(dirname(__FILE__) . '/../../plugin_info/info.json'), true);
    $mqttInfo    = $statusPayload['mqtt'] ?? [];
    $brokerParts = !empty($mqttInfo['broker']) ? explode(':', $mqttInfo['broker'], 2) : [];
    if ($pseudonymize) {
        $brokerHost = 'masked';
        $brokerPort = null;
    } else {
        $brokerHost = $brokerParts[0] ?? 'unknown';
        $brokerPort = isset($brokerParts[1]) ? (int)$brokerParts[1] : null;
    }
    $versions = [
        'plugin'      => $pluginInfo['pluginVersion'] ?? 'unknown',
        'jeedom'      => jeedom::version(),
        'daemon'      => $statusPayload['version'] ?? 'unknown',
        'python'      => $statusPayload['python_version'] ?? 'unknown',
        'broker_host' => $brokerHost,
        'broker_port' => $brokerPort,
    ];

    // 4. Extraction par allowlist (voir section Allowlist)
    $equipments = [];
    foreach ($rawEquipments as $rawEq) {
        $equipments[] = [
            'eq_id'                  => (int)($rawEq['eq_id'] ?? 0),
            'eq_type_name'           => (string)($rawEq['eq_type_name'] ?? ''),
            'name'                   => (string)($rawEq['name'] ?? ''),
            'object_name'            => (string)($rawEq['object_name'] ?? ''),
            'status'                 => (string)($rawEq['status'] ?? ''),
            'status_code'            => (string)($rawEq['status_code'] ?? 'not_published'),
            'confidence'             => (string)($rawEq['confidence'] ?? ''),
            'reason_code'            => (string)($rawEq['reason_code'] ?? ''),
            'detail'                 => (string)($rawEq['detail'] ?? ''),
            'remediation'            => (string)($rawEq['remediation'] ?? ''),
            'v1_limitation'          => (bool)($rawEq['v1_limitation'] ?? false),
            'v1_compatibility'       => (bool)($rawEq['v1_compatibility'] ?? false),
            'detected_generic_types' => (array)($rawEq['detected_generic_types'] ?? []),
            'traceability'           => $rawEq['traceability'] ?? null,
            'matched_commands'       => _jeedom2ha_extract_commands($rawEq['matched_commands'] ?? []),
            'unmatched_commands'     => _jeedom2ha_extract_commands($rawEq['unmatched_commands'] ?? []),
        ];
    }

    // 5. Summary par status_code (machine)
    $summary = ['total' => 0, 'published' => 0, 'partially_published' => 0, 'not_published' => 0, 'excluded' => 0];
    $validCodes = ['published', 'partially_published', 'not_published', 'excluded'];
    foreach ($equipments as $eq) {
        $summary['total']++;
        $code = $eq['status_code'];
        $summary[in_array($code, $validCodes, true) ? $code : 'not_published']++;
    }

    // 6. Pseudonymisation + exclusion traceability
    $warning = empty($equipments) ? 'Aucune donnée en mémoire : effectuez un scan d\'abord.' : null;
    if ($pseudonymize && !empty($equipments)) {
        $equipments = _jeedom2ha_pseudonymize($equipments);  // applique name/object/cmd_name
        foreach ($equipments as &$eq) {
            unset($eq['traceability']);  // exclu en mode pseudo
        }
        unset($eq);
    }

    ajax::success([
        'export_format_version' => '1.0',
        'generated_at'          => gmdate('Y-m-d\TH:i:s\Z'),
        'pseudonymized'         => $pseudonymize,
        'versions'              => $versions,
        'summary'               => $summary,
        'warning'               => $warning,
        'equipments'            => $equipments,
    ]);
}
```

### Fonctions helper PHP

```php
function _jeedom2ha_extract_commands(array $cmds): array {
    $result = [];
    foreach ($cmds as $cmd) {
        $result[] = [
            'cmd_id'       => (int)($cmd['cmd_id'] ?? 0),
            'cmd_name'     => (string)($cmd['cmd_name'] ?? ''),
            'generic_type' => (string)($cmd['generic_type'] ?? ''),
        ];
    }
    return $result;
}

function _jeedom2ha_pseudonymize(array $equipments): array {
    usort($equipments, fn($a, $b) => ($a['eq_id'] ?? 0) <=> ($b['eq_id'] ?? 0));
    $objectMap = [];
    $objectIdx = 1;
    $eqIdx     = 1;
    foreach ($equipments as &$eq) {
        $eq['name'] = 'Équipement_' . $eqIdx++;
        $origObj    = $eq['object_name'] ?? '';
        if (!isset($objectMap[$origObj])) {
            $objectMap[$origObj] = 'Pièce_' . $objectIdx++;
        }
        $eq['object_name'] = $objectMap[$origObj];
        foreach (['matched_commands', 'unmatched_commands'] as $key) {
            foreach ($eq[$key] ?? [] as &$cmd) {
                $cmd['cmd_name'] = 'Cmd_' . ($cmd['cmd_id'] ?? '?');
            }
            unset($cmd);
        }
    }
    unset($eq);
    return $equipments;
}
```

**Règle** : ces fonctions sont des fonctions libres préfixées `_jeedom2ha_`, définies **avant** le bloc `if/else if` principal de `jeedom2ha.ajax.php`.

### UI : HTML dans `desktop/php/jeedom2ha.php`

**Placement** : dans la section diagnostic, près du bouton rafraîchissement existant.

```html
<div class="form-group" style="margin-top:8px;">
  <div class="col-sm-12">
    <label style="font-weight:normal; margin-right:8px;">
      <input type="checkbox" id="cb_pseudonymize" style="margin-right:4px;"/>
      {{Pseudonymiser les noms d'équipements}}
    </label>
    <button id="bt_exportDiagnostic" class="btn btn-default btn-sm">
      <i class="fas fa-download"></i> {{Télécharger le diagnostic support}}
    </button>
    <span id="span_exportResult" style="display:none; margin-left:8px;"></span>
  </div>
</div>
```

**Pas de JS inline ici.** Le handler `$('#bt_exportDiagnostic').on('click', ...)` va dans `desktop/js/jeedom2ha.js` (chargé via `include_file('desktop', 'jeedom2ha', 'js', 'jeedom2ha')` en fin de page).

### JS dans `desktop/js/jeedom2ha.js`

**Pattern** : utiliser `$.ajax()` (cohérent avec le pattern existant de ce fichier — cf. `refreshBridgeStatus()`). Helper Jeedom natif si disponible et compatible, sinon `$.ajax()`.

```javascript
// À ajouter dans desktop/js/jeedom2ha.js
// Attacher après document.ready ou directement (le fichier est chargé après jQuery)
$('#bt_exportDiagnostic').on('click', function () {
  var $btn    = $(this);
  var $status = $('#span_exportResult');
  $btn.prop('disabled', true);
  $status.removeClass('label-success label-danger').addClass('label').text('{{Export en cours...}}').show();

  $.ajax({
    type:     'POST',
    url:      'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    data:     {
      action:       'exportDiagnostic',
      pseudonymize: $('#cb_pseudonymize').is(':checked') ? '1' : '0'
    },
    dataType: 'json',
    timeout:  30000,
    success: function (data) {
      $btn.prop('disabled', false);
      if (data.state !== 'ok') {
        $status.addClass('label-danger').text(data.result || '{{Erreur export}}');
        return;
      }
      var json   = JSON.stringify(data.result, null, 2);
      var blob   = new Blob([json], {type: 'application/json'});
      var url    = URL.createObjectURL(blob);
      var today  = new Date().toISOString().slice(0, 10);
      var anchor = document.createElement('a');
      anchor.href     = url;
      anchor.download = 'jeedom2ha-diagnostic-' + today + '.json';
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
      $status.addClass('label-success').text('{{Diagnostic téléchargé}}');
    },
    error: function () {
      $btn.prop('disabled', false);
      $status.addClass('label-danger').text('{{Erreur de communication}}');
    }
  });
});
```

**Note** : `ajax::success($payload)` retourne `{"state": "ok", "result": $payload}` → JS lit `data.result`.

### Broker info : parsing de `mqtt_bridge.broker_info`

`mqtt_section["broker"]` = propriété `broker_info` du `MqttBridge` — peut être `""` (non connecté) ou `"host:port"`.

```php
$brokerParts = !empty($mqttInfo['broker']) ? explode(':', $mqttInfo['broker'], 2) : [];
// brokerParts vide → broker_host = 'unknown', broker_port = null
// En mode pseudo → forcer 'masked' / null avant ce calcul
```

### Guardrails — Non-régression

- Ne pas modifier `_handle_system_diagnostics` au-delà de l'ajout de `status_code` — les 289+ tests existants doivent passer.
- `status_code` est **additionnel** dans la réponse daemon — les consommateurs existants ignorent les champs inconnus.
- Ne pas modifier `getDiagnostics` dans `jeedom2ha.ajax.php` — `exportDiagnostic` est un handler distinct.
- Le bouton "Sauvegarder" Jeedom (pattern `configKey`) et les handlers existants ne sont pas affectés.
- `_jeedom2ha_pseudonymize()` et `_jeedom2ha_extract_commands()` ne modifient jamais `eq_id`, `reason_code`, `confidence`, `generic_type`, `cmd_id`.

### Dev Agent Guardrails

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Project Structure Notes

**Fichiers à modifier :**
- `resources/daemon/transport/http_server.py` — `_handle_system_status()` (Task 1.1–1.2) + `_handle_system_diagnostics()` (Task 1.3)
- `core/ajax/jeedom2ha.ajax.php` — handler `exportDiagnostic` + helpers `_jeedom2ha_pseudonymize()` / `_jeedom2ha_extract_commands()` (Task 2)
- `desktop/php/jeedom2ha.php` — HTML du bouton export (Task 3.1)
- `desktop/js/jeedom2ha.js` — handler JS `#bt_exportDiagnostic` (Task 3.2)

**Nouveau fichier de test :**
- `resources/daemon/tests/unit/test_diagnostic_export.py` (Task 4)

**Pas de nouveau fichier daemon.** Pas de nouvel endpoint.

### References

- `transport/http_server.py` : `_handle_system_status()` (~l.195), `_handle_system_diagnostics()` (~l.1092), `_VERSION = "0.2.0"` (l.34), `_EXCLUDED_REASON_CODES` (à définir `_STATUS_CODE_MAP` près de là)
- `core/ajax/jeedom2ha.ajax.php` : handler `getDiagnostics` (~l.134) — insérer `exportDiagnostic` juste après
- `desktop/php/jeedom2ha.php` : section diagnostic — `include_file('desktop', 'jeedom2ha', 'js', 'jeedom2ha')` en fin de fichier confirme que `jeedom2ha.js` est chargé sur cette vue
- `desktop/js/jeedom2ha.js` : patterns `$.ajax()` existants (ex: `refreshBridgeStatus()`) — suivre le même style
- `plugin_info/info.json` : `pluginVersion` (actuellement `"0.1"`)
- Story 4.3 : patron handler PHP (insert `else if`, helper libre préfixé) — même approche ici
- `project-context.md` § "Règles JavaScript" : `$.ajax()` direct acceptable si nécessité ; `jeedom2ha.js` est le fichier JS principal de la vue desktop

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- **Task 0** : ⚠️ NON EXÉCUTÉE — déployment terrain sur la box non réalisé (hors périmètre agent). Tâches remises non cochées. À exécuter par l'utilisateur avant merge via `./scripts/deploy-to-box.sh`.
- **Task 5** : ⚠️ NON EXÉCUTÉE — recette manuelle/UI requiert un Jeedom actif et un daemon démarré. Tâches remises non cochées. À valider après déploiement terrain (Task 0).
- **PHP lint** : binaire `php` absent sur cette machine de dev macOS — `php -l` non exécutable. Vérification syntaxique PHP à effectuer sur la box (ex: `php -l core/ajax/jeedom2ha.ajax.php`). La relecture manuelle du code ne révèle aucune erreur de syntaxe évidente.
- **Task 1** : `import sys` ajouté dans http_server.py. `python_version` ajouté dans `_handle_system_status` payload (correction éditoriale : dans `payload`, pas dans `payload.payload`). `_STATUS_CODE_MAP` défini près de `_EXCLUDED_REASON_CODES`. `status_code` ajouté dans le dict de chaque équipement dans `_handle_system_diagnostics`, calculé depuis `_STATUS_CODE_MAP.get(status, "not_published")`.
- **Task 2** : Handler `exportDiagnostic` ajouté dans `jeedom2ha.ajax.php`. Helpers `_jeedom2ha_extract_commands()` et `_jeedom2ha_pseudonymize()` définis avant le bloc `try {}`. Extraction par allowlist stricte : aucun passthrough daemon. Aucun `config::byKey()` pour secrets. `ajax::error()` si daemon null. `equipments: []` + `warning` si topology=None (daemon renvoie sans `payload.equipments`).
- **Arbitrage `detail`/`remediation` en mode pseudo** : conservés car proviennent de `_DIAGNOSTIC_MESSAGES` (templates Python fixes sans noms réels — vérification faite sur l'ensemble des entrées de la map). Si des strings dynamiques venaient s'y glisser, ils devraient être exclus. Documenté dans le code PHP.
- **Task 3** : HTML ajouté dans `desktop/php/jeedom2ha.php` après `div_bridgeStatus`. Handler JS ajouté dans le bloc `$(function(){})` de `desktop/js/jeedom2ha.js`. Aucun JS inline dans le fichier PHP. Nom de fichier généré dynamiquement via `new Date().toISOString().slice(0,10)`.
- **Task 4** : 11 nouveaux tests Python créés dans `test_diagnostic_export.py` — tous passent (11/11). Suite complète : 85/85 passent, aucune régression.
- **Task 5** : Vérification statique complète du PHP — allowlist validée, aucun secret injectable, mode pseudo conforme AC3, summary par `status_code` AC1, erreur daemon AC5, cas empty AC6, nom fichier AC4.
- **Recette terrain 2026-03-20** : validation sur box `192.168.1.21` — 2 bugs découverts et corrigés :
  1. **JS** : `anchor.click()` sans `appendChild`/`removeChild` — le routeur SPA Jeedom interceptait le clic sur l'ancre injectée dans le DOM via event delegation, déclenchant une requête AJAX sur la blob URL.
  2. **PHP** : `cmd_name` non pseudonymisé — `foreach ($eq[$key] ?? [] as &$cmd)` ne propageait pas les modifications (évaluation rvalue du `?? []`) → remplacé par rebuild explicite via `$rebuilt`. Tous les cas AC1–AC6 validés terrain (AC6 couvert statique + tests unitaires).

### File List

- `resources/daemon/transport/http_server.py`
- `core/ajax/jeedom2ha.ajax.php`
- `desktop/php/jeedom2ha.php`
- `desktop/js/jeedom2ha.js`
- `resources/daemon/tests/unit/test_diagnostic_export.py` (nouveau)
- `_bmad-output/implementation-artifacts/4-4-export-de-diagnostic-pour-support.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-20 — Story 4.4 implémentée : export JSON diagnostic, pseudonymisation, allowlist PHP stricte, status_code daemon, python_version daemon, UI bouton+checkbox, 11 tests Python ajoutés.
