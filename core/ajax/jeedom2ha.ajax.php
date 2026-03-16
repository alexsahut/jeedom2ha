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
    else {
      throw new Exception(__('Aucune méthode correspondante à', __FILE__) . ' : ' . $action);
    }
}
catch (Exception $e) {
    ajax::error(displayException($e), $e->getCode());
}
