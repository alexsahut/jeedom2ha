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

    if (init('action') == 'getMqttConfig') {
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

    if (init('action') == 'testMqttConnection') {
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
      $result = jeedom2ha::callDaemon('/action/mqtt_test', $params, 'POST');
      if ($result === null) {
        throw new Exception(__('Le démon ne répond pas — vérifiez qu\'il est bien démarré', __FILE__));
      }
      ajax::success($result);
    }

    throw new Exception(__('Aucune méthode correspondante à', __FILE__) . ' : ' . init('action'));
    /*     * *********Catch exeption*************** */
}
catch (Exception $e) {
    ajax::error(displayException($e), $e->getCode());
}
