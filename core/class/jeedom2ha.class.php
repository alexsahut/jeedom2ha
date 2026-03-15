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

/* * ***************************Includes********************************* */
require_once __DIR__  . '/../../../../core/php/core.inc.php';

class jeedom2ha extends eqLogic {
  /*     * *************************Attributs****************************** */

  /*
  * Permet de définir les possibilités de personnalisation du widget (en cas d'utilisation de la fonction 'toHtml' par exemple)
  * Tableau multidimensionnel - exemple: array('custom' => true, 'custom::layout' => false)
  public static $_widgetPossibility = array();
  */

  /**
   * Raison du dernier échec d'auto-détection MQTT Manager.
   * Valeurs possibles : 'plugin_inactive', 'keys_not_found', 'unknown'
   * Mis à jour par getMqttManagerConfig() avant chaque retour null.
   */
  public static $_lastDetectionReason = 'unknown';

  /*     * ***********************Methode static*************************** */

  /**
   * Appelé automatiquement par Jeedom après la sauvegarde de la configuration plugin.
   * Chiffre le mot de passe MQTT via utils::encrypt().
   * Ne remplace le secret existant que si une nouvelle valeur non vide est fournie.
   */
  public static function postSaveConfiguration() {
    $password = init('mqttPassword');
    if ($password === null || $password === '') {
      return;
    }
    config::save('mqttPassword', utils::encrypt($password), __CLASS__);
  }

  /**
   * Auto-détection best effort de la configuration MQTT Manager (mqtt2).
   * Retourne un tableau [host, port, user, password, tls, source] ou null si indisponible.
   * Ne lève jamais d'exception — log un warning et retourne null en cas d'échec.
   * En cas d'échec, $_lastDetectionReason indique la cause ('plugin_inactive', 'keys_not_found', 'unknown').
   *
   * Clés réelles utilisées par mqtt2 (Mips2648) :
   *   mode          : 'local' | 'remote' | 'docker'
   *   remote::ip    : adresse IP/hostname du broker distant (mode remote uniquement)
   *   remote::port  : port du broker distant (mode remote uniquement)
   *   remote::protocol : 'mqtt' | 'mqtts' (TLS en mode remote)
   *   mqtt::password : credentials au format "user:password\n..." (première ligne utilisée)
   */
  public static function getMqttManagerConfig(): ?array {
    try {
      if (!class_exists('plugin')) {
        log::add(__CLASS__, 'debug', '[MQTT] Classe plugin indisponible — configuration manuelle requise');
        self::$_lastDetectionReason = 'plugin_inactive';
        return null;
      }
      $mqtt2Plugin = plugin::byId('mqtt2');
      if (!is_object($mqtt2Plugin) || !$mqtt2Plugin->isActive()) {
        log::add(__CLASS__, 'debug', '[MQTT] mqtt2 absent ou inactif — configuration manuelle requise');
        self::$_lastDetectionReason = 'plugin_inactive';
        return null;
      }

      // Détecter le mode mqtt2 : 'local', 'remote' ou 'docker'
      $mode = config::byKey('mode', 'mqtt2', 'local');

      if ($mode === 'remote') {
        $host = config::byKey('remote::ip', 'mqtt2', '');
        $port = intval(config::byKey('remote::port', 'mqtt2', 1883));
        $protocol = config::byKey('remote::protocol', 'mqtt2', 'mqtt');
        $tls = ($protocol === 'mqtts');
      } else {
        // Mode local ou docker : broker Mosquitto interne sur 127.0.0.1:1883
        $host = '127.0.0.1';
        $port = 1883;
        $tls = false;
      }

      if ($host === '' || $host === null) {
        log::add(__CLASS__, 'debug', '[MQTT] Auto-détection mqtt2 : hôte non trouvé (mode=' . $mode . ')');
        self::$_lastDetectionReason = 'keys_not_found';
        return null;
      }

      // Filtrage de sécurité : ports internes connus de MQTT Manager
      // 55035 = socket interne jeedomdaemon, 1885 = port Mosquitto interne
      $internalPorts = array(55035, 1885);
      if (in_array($port, $internalPorts)) {
        log::add(__CLASS__, 'info', '[MQTT] Auto-détection mqtt2 : port interne détecté (' . $port . '), repli sur 1883');
        $port = 1883;
      }

      // Authentification : clé 'mqtt::password' au format "user:password" (première ligne)
      $user = '';
      $pass = '';
      $authRaw = config::byKey('mqtt::password', 'mqtt2', '');
      if ($authRaw !== '' && $authRaw !== null) {
        $firstLine = explode("\n", $authRaw)[0];
        if (strpos($firstLine, ':') !== false) {
          list($user, $pass) = explode(':', $firstLine, 2);
        } else {
          $user = $firstLine;
        }
      }

      log::add(__CLASS__, 'info', '[MQTT] Auto-détection mqtt2 : host=' . $host . ' port=' . $port . ' mode=' . $mode . ' tls=' . ($tls ? 'true' : 'false'));
      return array(
        'host'     => $host,
        'port'     => $port,
        'user'     => $user,
        'password' => $pass,
        'tls'      => $tls,
        'source'   => 'mqtt2',
      );
    } catch (\Throwable $e) {
      log::add(__CLASS__, 'warning', '[MQTT] Auto-détection mqtt2 : exception → ' . $e->getMessage());
      self::$_lastDetectionReason = 'unknown';
      return null;
    }
  }

  public static function deamon_info() {
    $return = array();
    $return['log'] = __CLASS__;
    $return['launchable'] = 'ok';
    $return['state'] = 'nok';

    // Check Python3 availability
    $pythonPath = system::getCmdPython3(__CLASS__);
    if ($pythonPath === '') {
      $return['launchable'] = 'nok';
      message::add(__CLASS__, __('Python3 introuvable pour le plugin', __FILE__));
      return $return;
    }

    // Check if daemon process is running via PID
    $pid_file = jeedom::getTmpFolder(__CLASS__) . '/deamon.pid';
    if (file_exists($pid_file)) {
      $pid = intval(trim(file_get_contents($pid_file)));
      if ($pid > 0 && posix_kill($pid, 0)) {
        $return['state'] = 'ok';
      }
    }

    // Healthcheck via HTTP if process is running
    if ($return['state'] === 'ok') {
      $status = self::callDaemon('/system/status');
      if ($status === null || !isset($status['status']) || $status['status'] !== 'ok') {
        $return['state'] = 'nok';
      }
    }

    return $return;
  }

  public static function deamon_start() {
    self::deamon_stop();
    log::add(__CLASS__, 'info', '[DAEMON] Starting daemon...');

    $daemonDir = __DIR__ . '/../../resources/daemon';
    $pythonPath = system::getCmdPython3(__CLASS__);

    // Generate local_secret if not yet stored
    $localSecret = config::byKey('localSecret', __CLASS__);
    if ($localSecret === '' || $localSecret === null) {
      $localSecret = bin2hex(random_bytes(16));
      config::save('localSecret', $localSecret, __CLASS__);
      log::add(__CLASS__, 'info', '[DAEMON] Generated new local_secret');
    }

    $apiPort = config::byKey('daemonApiPort', __CLASS__, '55080');

    $pidFile = jeedom::getTmpFolder(__CLASS__) . '/deamon.pid';
    $callbackUrl = network::getNetworkAccess('internal', 'proto:127.0.0.1:port:comp') . '/plugins/jeedom2ha/core/php/jeedom2ha.php';
    $apiKey = jeedom::getApiKey(__CLASS__);
    $jeedomCoreApiKey = config::byKey('api');
    $socketPort = config::byKey('socketport', __CLASS__, '55081');
    $logLevel = log::convertLogLevel(log::getLogLevel(__CLASS__));

    $cmd = $pythonPath . ' ' . $daemonDir . '/main.py';
    $cmd .= ' --loglevel ' . $logLevel;
    $cmd .= ' --sockethost 127.0.0.1';
    $cmd .= ' --socketport ' . $socketPort;
    $cmd .= ' --callback ' . $callbackUrl;
    $cmd .= ' --apikey ' . $apiKey;
    $cmd .= ' --jeedomcoreapikey ' . escapeshellarg((string) $jeedomCoreApiKey);
    $cmd .= ' --pid ' . $pidFile;
    $cmd .= ' --apiport ' . $apiPort;
    $cmd .= ' --localsecret ' . $localSecret;

    $cmdLog = preg_replace('/--localsecret\s+\S+/', '--localsecret ***', $cmd);
    $cmdLog = preg_replace('/--apikey\s+\S+/', '--apikey ***', $cmdLog);
    $cmdLog = preg_replace('/--jeedomcoreapikey\s+\S+/', '--jeedomcoreapikey ***', $cmdLog);
    log::add(__CLASS__, 'info', '[DAEMON] Launching: ' . $cmdLog);
    $result = exec($cmd . ' >> ' . log::getPathToLog(__CLASS__ . '_daemon') . ' 2>&1 &');
    // Use wall-clock deadline: callDaemon has a 3s timeout per attempt (2 attempts for GET),
    // so each deamon_info() call can take up to ~7s. The deadline enforces a real 20s limit.
    $deadline = time() + 20;
    $deamon_info = array('state' => 'nok');
    while (time() < $deadline) {
      $deamon_info = self::deamon_info();
      if ($deamon_info['state'] === 'ok') {
        break;
      }
      if (time() + 1 < $deadline) {
        sleep(1);
      }
    }
    if ($deamon_info['state'] !== 'ok') {
      log::add(__CLASS__, 'error', '[DAEMON] Failed to start daemon within 20s — check logs');
      return false;
    }
    log::add(__CLASS__, 'info', '[DAEMON] Daemon started successfully');

    // Send MQTT config to daemon (non-blocking — connect_async on daemon side)
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
      log::add(__CLASS__, 'info', '[MQTT] Connexion MQTT initiée vers ' . $mqttHost . ':' . $mqttConfig['port'] . ' (user=' . ($mqttConfig['user'] !== '' ? $mqttConfig['user'] : 'anonymous') . ' tls=' . ($mqttConfig['tls'] ? 'true' : 'false') . ')');
      $result = self::callDaemon('/action/mqtt_connect', $mqttConfig, 'POST');
      if ($result === null || !isset($result['status']) || $result['status'] !== 'ok') {
        log::add(__CLASS__, 'warning', '[MQTT] Échec initiation MQTT — le démon reste actif sans broker');
      }
    } else {
      log::add(__CLASS__, 'info', '[DAEMON] Pas de configuration MQTT, connexion différée');
    }

    return true;
  }

  public static function deamon_stop() {
    log::add(__CLASS__, 'info', '[DAEMON] Stopping daemon...');
    $pid_file = jeedom::getTmpFolder(__CLASS__) . '/deamon.pid';
    if (file_exists($pid_file)) {
      $pid = intval(trim(file_get_contents($pid_file)));
      if ($pid > 0) {
        posix_kill($pid, 15); // SIGTERM
        $i = 0;
        while ($i < 10) {
          if (!posix_kill($pid, 0)) {
            break;
          }
          sleep(1);
          $i++;
        }
        if ($i >= 10) {
          posix_kill($pid, 9); // SIGKILL as last resort
          log::add(__CLASS__, 'warning', '[DAEMON] Daemon did not stop gracefully, sent SIGKILL');
        }
      }
      if (file_exists($pid_file)) {
        unlink($pid_file);
      }
    }
    log::add(__CLASS__, 'info', '[DAEMON] Daemon stopped');
  }

  public static function callDaemon($_endpoint, $_payload = array(), $_method = 'GET', $_timeout = 3) {
    $apiPort = config::byKey('daemonApiPort', __CLASS__, '55080');
    $localSecret = config::byKey('localSecret', __CLASS__);
    $url = 'http://127.0.0.1:' . $apiPort . $_endpoint;

    $opts = array(
      'http' => array(
        'method' => $_method,
        'header' => "X-Local-Secret: " . $localSecret . "\r\n" .
                    "Content-Type: application/json\r\n",
        'timeout' => $_timeout,
        'ignore_errors' => true,
      ),
    );

    if ($_method === 'POST' && !empty($_payload)) {
      $action = ltrim($_endpoint, '/');
      $action = str_replace('action/', '', $action);
      $action = str_replace('/', '.', $action);
      
      $wrappedPayload = array(
        'action' => $action,
        'payload' => $_payload,
        'request_id' => bin2hex(random_bytes(8)),
        'timestamp' => date('c'),
      );
      $opts['http']['content'] = json_encode($wrappedPayload);
    }

    $context = stream_context_create($opts);

    // Retry only for idempotent GET requests
    $maxAttempts = ($_method === 'GET') ? 2 : 1;
    $lastError = null;

    for ($attempt = 1; $attempt <= $maxAttempts; $attempt++) {
      $result = @file_get_contents($url, false, $context);
      if ($result !== false) {
        $data = json_decode($result, true);
        if (is_array($data)) {
          return $data;
        }
        log::add(__CLASS__, 'warning', '[API] Invalid JSON response from daemon: ' . $result);
        return null;
      }
      $lastError = error_get_last();
      if ($attempt < $maxAttempts) {
        sleep(1); // 1s between retries per architecture spec
      }
    }

    log::add(__CLASS__, 'debug', '[API] Daemon unreachable at ' . $url . ': ' . ($lastError['message'] ?? 'unknown error'));
    return null;
  }

  /**
   * Extrait la topologie complète de Jeedom pour synchronisation daemon.
   * Strictement Read-Only : utilise le cache pour les valeurs, jamais execCmd.
   */
  public static function getFullTopology(): array {
    $result = array('objects' => array(), 'eq_logics' => array());

    // 1. Objects Jeedom (contexte spatial / suggested_area)
    foreach (jeeObject::all() as $obj) {
      $result['objects'][] = array(
        'id'        => intval($obj->getId()),
        'name'      => $obj->getName(),
        'father_id' => ($obj->getFather_id() !== null) ? intval($obj->getFather_id()) : null,
        'isVisible' => (bool)$obj->getIsVisible(),
      );
    }

    // 2. EqLogics (équipements)
    foreach (eqLogic::all() as $eq) {
      // Exclure les équipements de ce plugin
      if ($eq->getEqType_name() === __CLASS__) {
        continue;
      }

      $cmds = array();
      foreach (cmd::byEqLogicId($eq->getId()) as $cmd) {
        $cmds[] = array(
          'id'            => intval($cmd->getId()),
          'name'          => $cmd->getName(),
          'generic_type'  => $cmd->getGeneric_type() ?: null,
          'type'          => $cmd->getType(),
          'sub_type'      => $cmd->getSubType(),
          'current_value' => $cmd->getCache('value', null),
          'unit'          => $cmd->getUnite() ?: null,
          'is_visible'    => (bool)$cmd->getIsVisible(),
          'is_historized' => (bool)$cmd->getIsHistorized(),
        );
      }

      $result['eq_logics'][] = array(
        'id'           => intval($eq->getId()),
        'name'         => $eq->getName(),
        'object_id'    => (method_exists($eq, 'getObject_id') && $eq->getObject_id() !== null) ? intval($eq->getObject_id()) : null,
        'is_enable'    => method_exists($eq, 'getIsEnable') ? (bool)$eq->getIsEnable() : true, // Actif par défaut si on ne peut pas savoir
        'is_visible'   => method_exists($eq, 'getIsVisible') ? (bool)$eq->getIsVisible() : true,
        'eq_type'      => method_exists($eq, 'getEqType_name') ? $eq->getEqType_name() : 'unknown',
        'generic_type' => method_exists($eq, 'getGeneric_type') ? ($eq->getGeneric_type() ?: null) : null,
        'is_excluded'  => method_exists($eq, 'getConfiguration') ? (bool)$eq->getConfiguration('jeedom2ha_excluded', false) : false,
        'cmds'         => $cmds,
      );
    }

    log::add(__CLASS__, 'info', '[TOPOLOGY] Scan complet : ' . count($result['objects']) . ' objets, ' . count($result['eq_logics']) . ' eqLogics');
    return $result;
  }

  /*     * *********************Méthodes d'instance************************* */

  // Fonction exécutée automatiquement avant la création de l'équipement
  public function preInsert() {
  }

  // Fonction exécutée automatiquement après la création de l'équipement
  public function postInsert() {
  }

  // Fonction exécutée automatiquement avant la mise à jour de l'équipement
  public function preUpdate() {
  }

  // Fonction exécutée automatiquement après la mise à jour de l'équipement
  public function postUpdate() {
  }

  // Fonction exécutée automatiquement avant la sauvegarde (création ou mise à jour) de l'équipement
  public function preSave() {
  }

  // Fonction exécutée automatiquement après la sauvegarde (création ou mise à jour) de l'équipement
  public function postSave() {
  }

  // Fonction exécutée automatiquement avant la suppression de l'équipement
  public function preRemove() {
  }

  // Fonction exécutée automatiquement après la suppression de l'équipement
  public function postRemove() {
  }

  /*
  * Permet de crypter/décrypter automatiquement des champs de configuration des équipements
  * Exemple avec le champ "Mot de passe" (password)
  public function decrypt() {
    $this->setConfiguration('password', utils::decrypt($this->getConfiguration('password')));
  }
  public function encrypt() {
    $this->setConfiguration('password', utils::encrypt($this->getConfiguration('password')));
  }
  */

  /*
  * Permet de modifier l'affichage du widget (également utilisable par les commandes)
  public function toHtml($_version = 'dashboard') {}
  */

  /*     * **********************Getteur Setteur*************************** */
}

class jeedom2haCmd extends cmd {
  /*     * *************************Attributs****************************** */

  /*
  public static $_widgetPossibility = array();
  */

  /*     * ***********************Methode static*************************** */


  /*     * *********************Methode d'instance************************* */

  /*
  * Permet d'empêcher la suppression des commandes même si elles ne sont pas dans la nouvelle configuration de l'équipement envoyé en JS
  public function dontRemoveCmd() {
    return true;
  }
  */

  // Exécution d'une commande
  public function execute($_options = array()) {
  }

  /*     * **********************Getteur Setteur*************************** */
}
