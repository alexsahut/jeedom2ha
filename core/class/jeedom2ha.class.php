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
   * Retourne un tableau [host, port, user, password, source] ou null si indisponible.
   * Ne lève jamais d'exception — log un warning et retourne null en cas d'échec.
   */
  public static function getMqttManagerConfig(): ?array {
    try {
      if (!class_exists('plugin')) {
        log::add(__CLASS__, 'debug', '[MQTT] Classe plugin indisponible — configuration manuelle requise');
        return null;
      }
      $mqtt2Plugin = plugin::byId('mqtt2');
      if (!is_object($mqtt2Plugin) || !$mqtt2Plugin->isActive()) {
        log::add(__CLASS__, 'debug', '[MQTT] mqtt2 absent ou inactif — configuration manuelle requise');
        return null;
      }
      // Clés de config mqtt2 — à vérifier sur instance réelle.
      // Si une clé retourne '' ou null, l'auto-détection est incomplète → fallback manuel.
      $host = config::byKey('mqtt::ip', 'mqtt2', '');
      $port = config::byKey('mqtt::port', 'mqtt2', 1883);
      $user = config::byKey('mqtt::username', 'mqtt2', '');
      $pass = config::byKey('mqtt::password', 'mqtt2', '');
      if ($host === '' || $host === null) {
        log::add(__CLASS__, 'warning', '[MQTT] Auto-détection mqtt2 : clé host vide ou inconnue, fallback manuel');
        return null;
      }
      log::add(__CLASS__, 'info', '[MQTT] Auto-détection mqtt2 : host détecté → configuration pré-remplie');
      return array(
        'host' => $host,
        'port' => intval($port),
        'user' => $user,
        'password' => $pass,
        'source' => 'mqtt2',
      );
    } catch (\Throwable $e) {
      log::add(__CLASS__, 'warning', '[MQTT] Auto-détection mqtt2 : exception → ' . $e->getMessage() . ' — fallback manuel');
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
    $socketPort = config::byKey('socketport', __CLASS__, '55081');
    $logLevel = log::convertLogLevel(log::getLogLevel(__CLASS__));

    $cmd = $pythonPath . ' ' . $daemonDir . '/main.py';
    $cmd .= ' --loglevel ' . $logLevel;
    $cmd .= ' --sockethost 127.0.0.1';
    $cmd .= ' --socketport ' . $socketPort;
    $cmd .= ' --callback ' . $callbackUrl;
    $cmd .= ' --apikey ' . $apiKey;
    $cmd .= ' --pid ' . $pidFile;
    $cmd .= ' --apiport ' . $apiPort;
    $cmd .= ' --localsecret ' . $localSecret;

    $cmdLog = preg_replace('/--localsecret\s+\S+/', '--localsecret ***', $cmd);
    $cmdLog = preg_replace('/--apikey\s+\S+/', '--apikey ***', $cmdLog);
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

  public static function callDaemon($_endpoint, $_payload = array(), $_method = 'GET') {
    $apiPort = config::byKey('daemonApiPort', __CLASS__, '55080');
    $localSecret = config::byKey('localSecret', __CLASS__);
    $url = 'http://127.0.0.1:' . $apiPort . $_endpoint;

    $opts = array(
      'http' => array(
        'method' => $_method,
        'header' => "X-Local-Secret: " . $localSecret . "\r\n" .
                    "Content-Type: application/json\r\n",
        'timeout' => 3,
        'ignore_errors' => true,
      ),
    );

    if ($_method === 'POST' && !empty($_payload)) {
      $opts['http']['content'] = json_encode($_payload);
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
