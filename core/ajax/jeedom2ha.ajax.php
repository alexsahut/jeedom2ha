<?php
/* This file is part of Jeedom.
 *
 * Jeedom is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Jeedom is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Jeedom. If not, see <http://www.gnu.org/licenses/>.
 */

/**
 * Helper — Extrait les commandes par allowlist (cmd_id, cmd_name, generic_type).
 * Story 4.4 — aucun champ hors allowlist ne passe.
 */
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

/**
 * Helper — Pseudonymise les champs PII d'un tableau d'équipements.
 *   name       → Équipement_N  (trié par eq_id croissant, index 1-based)
 *   object_name → Pièce_M      (index 1-based par ordre d'apparition)
 *   cmd_name   → Cmd_{cmd_id}  (dans matched_commands et unmatched_commands)
 * Les champs techniques (eq_id, reason_code, confidence, etc.) restent inchangés.
 * Story 4.4 — appliqué uniquement si mode pseudo activé.
 */
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
            $rebuilt = [];
            foreach ($eq[$key] ?? [] as $cmd) {
                $cmd['cmd_name'] = 'Cmd_' . ($cmd['cmd_id'] ?? '?');
                $rebuilt[] = $cmd;
            }
            $eq[$key] = $rebuilt;
        }
    }
    unset($eq);
    return $equipments;
}

try {
    require_once dirname(__FILE__) . '/../../../../core/php/core.inc.php';
    include_file('core', 'authentification', 'php');

    if (!isConnect('admin')) {
        throw new Exception(__('401 - Accès non autorisé', __FILE__));
    }

  /* Fonction permettant l'envoi de l'entête 'Content-Type: application/json'
    En V3 : indiquer l'argument 'true' pour contrôler le token d'accès Jeedom
    En V4 : autoriser l'exécution d'une méthode 'action' en GET en indiquant le(s) nom(s) de(s) action(s) dans un tableau en argument
  */
    ajax::init();

    $action = init('action');

    if ($action == 'getMqttConfig') {
      $hasPassword = (config::byKey('mqttPassword', 'jeedom2ha', '') !== '');
      // Tente l'auto-détection mqtt2, sinon retourne la config manuelle stockée
      $mqtt2Config = jeedom2ha::getMqttManagerConfig();
      if ($mqtt2Config !== null) {
        unset($mqtt2Config['password']); // Sécurité : ne jamais renvoyer le password
        $mqtt2Config['has_password'] = $hasPassword;
        ajax::success($mqtt2Config);
      }
      // Fallback : retourner la config manuelle si elle existe
      $host = config::byKey('mqttHost', 'jeedom2ha', '');
      if ($host !== '') {
        ajax::success(array(
          'host' => $host,
          'port' => intval(config::byKey('mqttPort', 'jeedom2ha', 1883)),
          'user' => config::byKey('mqttUser', 'jeedom2ha', ''),
          'has_password' => $hasPassword,
          'source' => 'manual',
        ));
      }
      ajax::success(array('source' => 'none', 'has_password' => $hasPassword));
    }
    else if ($action == 'forceMqttManagerImport') {
      $config = jeedom2ha::getMqttManagerConfig();
      if ($config === null) {
        $reason = jeedom2ha::$_lastDetectionReason;
        $messages = array(
          'plugin_inactive' => __('Plugin MQTT Manager (mqtt2) non détecté ou inactif', __FILE__),
          'keys_not_found'  => __('Configuration MQTT Manager non trouvable — saisissez les paramètres manuellement', __FILE__),
          'unknown'         => __('Auto-détection MQTT Manager échouée', __FILE__),
        );
        ajax::success(array(
          'status'  => 'not_found',
          'reason'  => $reason,
          'message' => isset($messages[$reason]) ? $messages[$reason] : $messages['unknown'],
        ));
      }
      // Stocker la config détectée directement côté serveur
      // Le password ne quitte JAMAIS le serveur — stocké chiffré uniquement
      config::save('mqttHost', $config['host'], 'jeedom2ha');
      config::save('mqttPort', $config['port'], 'jeedom2ha');
      config::save('mqttUser', $config['user'], 'jeedom2ha');
      config::save('mqttTls', $config['tls'] ? '1' : '0', 'jeedom2ha');
      if ($config['password'] !== '' && $config['password'] !== null) {
        config::save('mqttPassword', utils::encrypt($config['password']), 'jeedom2ha');
      }
      log::add('jeedom2ha', 'info', '[MQTT] Import forcé depuis MQTT Manager : host=' . $config['host'] . ' port=' . $config['port']);
      ajax::success(array(
        'status'       => 'ok',
        'host'         => $config['host'],
        'port'         => $config['port'],
        'user'         => $config['user'],
        'tls'          => $config['tls'],
        'has_password' => ($config['password'] !== '' && $config['password'] !== null),
        'message'      => __('Configuration importée depuis MQTT Manager', __FILE__),
      ));
    }
    else if ($action == 'testMqttConnection') {
      $password = init('password', '');
      // Priorité : Formulaire > Secret Stocké > Aucun
      if ($password === '') {
        $storedPassword = config::byKey('mqttPassword', 'jeedom2ha', '');
        if ($storedPassword !== '') {
          $password = utils::decrypt($storedPassword);
        }
      }

      $params = array(
        'host'       => init('host', ''),
        'port'       => intval(init('port', 1883)),
        'user'       => init('user', ''),
        'password'   => $password,
        'tls'        => (init('tls', '0') === '1'),
        'tls_verify' => (init('tls_verify', '1') === '1'),
      );
      $result = jeedom2ha::callDaemon('/action/mqtt_test', $params, 'POST', 15);
      if ($result === null) {
        log::add('jeedom2ha', 'error', '[MQTT] Le démon n\'a pas répondu au test de connexion (timeout 15s)');
        throw new Exception(__('Le démon ne répond pas (timeout API) — vérifiez qu\'il est bien démarré dans l\'onglet Santé', __FILE__));
      }
      log::add('jeedom2ha', 'debug', '[MQTT] Résultat du test de connexion : ' . json_encode($result));
      ajax::success($result);
    }
    else if ($action == 'getBridgeStatus') {
      $status = jeedom2ha::callDaemon('/system/status');
      if ($status === null) {
        ajax::success(array('daemon' => false, 'mqtt' => array('state' => 'unknown', 'connected' => false, 'broker' => '')));
      }
      $mqtt = (isset($status['payload']['mqtt'])) ? $status['payload']['mqtt'] : array('state' => 'disconnected', 'connected' => false, 'broker' => '');
      ajax::success(array('daemon' => true, 'mqtt' => $mqtt));
    }
    else if ($action == 'scanTopology') {
      $topology = jeedom2ha::getFullTopology();
      $result = jeedom2ha::callDaemon('/action/sync', $topology, 'POST', 15);
      if ($result === null) {
        log::add('jeedom2ha', 'error', '[TOPOLOGY] Le démon n\'a pas répondu au scan de topologie (timeout 15s)');
        throw new Exception(__('Le démon ne répond pas (timeout API) — vérifiez qu\'il est bien démarré', __FILE__));
      }
      ajax::success($result);
    }
    else if ($action == 'getDiagnostics') {
      $result = jeedom2ha::callDaemon('/system/diagnostics', null, 'GET', 15);
      if ($result === null) {
        log::add('jeedom2ha', 'error', '[DIAGNOSTICS] Le démon n\'a pas répondu (timeout 15s)');
        throw new Exception(__('Le démon ne répond pas (timeout API) — vérifiez qu\'il est bien démarré', __FILE__));
      }
      ajax::success($result);
    }
    else if ($action == 'exportDiagnostic') {
      $pseudonymize = (init('pseudonymize', '0') === '1');

      // 1. Diagnostics (timeout 15s — source principale de l'export)
      $diagResult = jeedom2ha::callDaemon('/system/diagnostics', null, 'GET', 15);
      if ($diagResult === null) {
        log::add('jeedom2ha', 'error', '[EXPORT] Le démon n\'a pas répondu (timeout 15s)');
        ajax::error(__('Démon indisponible ou timeout — relancez le démon et réessayez.', __FILE__));
      }
      $rawEquipments = $diagResult['payload']['equipments'] ?? [];

      // 2. Statut daemon (timeout 5s — info version/broker, non bloquant)
      $statusResult  = jeedom2ha::callDaemon('/system/status', null, 'GET', 5);
      $statusPayload = $statusResult['payload'] ?? [];

      // 3. Versions — construction PHP stricte, jamais passthrough daemon
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

      // 4. Extraction par allowlist explicite — aucun passthrough brut
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

      // 5. Summary calculé depuis status_code machine (jamais depuis le libellé localisé status)
      $summary    = ['total' => 0, 'published' => 0, 'partially_published' => 0, 'not_published' => 0, 'excluded' => 0];
      $validCodes = ['published', 'partially_published', 'not_published', 'excluded'];
      foreach ($equipments as $eq) {
        $summary['total']++;
        $code = $eq['status_code'];
        $summary[in_array($code, $validCodes, true) ? $code : 'not_published']++;
      }

      // 6. Warning si aucun équipement en mémoire
      $warning = empty($equipments) ? 'Aucune donnée en mémoire : effectuez un scan d\'abord.' : null;

      // 7. Pseudonymisation + exclusion traceability si mode pseudo activé
      // Note : detail et remediation proviennent de templates fixes sans noms réels
      // (_DIAGNOSTIC_MESSAGES côté daemon) — ils sont conservés en mode pseudo.
      if ($pseudonymize && !empty($equipments)) {
        $equipments = _jeedom2ha_pseudonymize($equipments);
        foreach ($equipments as &$eq) {
          unset($eq['traceability']);  // traceability exclu en mode pseudo (risque champs contextuels)
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
    else if ($action == 'saveFilteringConfig') {
      $excludedPlugins  = init('excludedPlugins', '');
      $excludedObjects  = init('excludedObjects', '');
      $confidencePolicy = init('confidencePolicy', 'sure_probable');
      // Validation : valeurs autorisées uniquement
      if (!in_array($confidencePolicy, ['sure_only', 'sure_probable'])) {
        $confidencePolicy = 'sure_probable';
      }
      config::save('excludedPlugins',  $excludedPlugins,  'jeedom2ha');
      config::save('excludedObjects',  $excludedObjects,  'jeedom2ha');
      config::save('confidencePolicy', $confidencePolicy, 'jeedom2ha');
      log::add('jeedom2ha', 'info', '[CONFIG] saveFilteringConfig: excludedPlugins="'
        . $excludedPlugins . '" excludedObjects="' . $excludedObjects
        . '" confidencePolicy="' . $confidencePolicy . '"');
      ajax::success(['saved' => true]);
    }
    else {
      throw new Exception(__('Aucune méthode correspondante à', __FILE__) . ' : ' . $action);
    }
}
catch (Exception $e) {
    ajax::error(displayException($e), $e->getCode());
}
