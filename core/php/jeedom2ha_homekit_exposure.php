<?php
/* SPDX-License-Identifier: AGPL-3.0-or-later
 * This file is part of Jeedom2HA.
*
* Jeedom2HA is free software: you can redistribute it and/or modify
* it under the terms of the GNU Affero General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* Jeedom2HA is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU Affero General Public License for more details.
*
* You should have received a copy of the GNU Affero General Public License
* along with Jeedom2HA. If not, see <https://www.gnu.org/licenses/>.
*/

/*
 * Story 24.1 — signal d'exposition HomeKit (LECTURE SEULE) et identifiants physiques.
 *
 * Fonctions PURES : aucune dépendance au cœur Jeedom (pas de core.inc.php). Ce fichier est
 * chargé par core/class/jeedom2ha.class.php et directement par les tests CI
 * (tests/unit/test_story_24_1_php_homekit_exposure.php).
 *
 * Reproduit, sans jamais appeler le plugin Homebridge, la règle d'exposition de ce plugin
 * (lue sur la box par ClaudeBox, plugins/homebridge/core/class/homebridge.class.php:2680-2710
 * et :3119, core/api/homebridge.api.php:44, core/class/plugin.class.php:208-221 ; ce code n'est
 * pas dans ce dépôt). Les tests de Homebridge sont reproduits À L'IDENTIQUE (isset sur le
 * tableau brut de configuration, intval, comparaisons souples) : c'est Homebridge qui tranche,
 * jamais ce plugin. Un écart futur de Homebridge se corrige ICI. Équipement, dans l'ordre :
 *   1. plugin Homebridge installé et actif (sinon : signal inconnu) ;
 *   2. plugin de l'équipement dans la liste des plugins actifs (plugin::listPlugin(true, false,
 *      true, true), liste d'identifiants lue en base) et ni `mobile` ni `homebridge` ;
 *   3. pièce : identifiant non nul, différent de -1, pièce existante, et
 *      getConfiguration('sendToHomebridge', 0) == 1 (comparaison souple) ; sinon false/piece ;
 *   4. si isset(configuration['sendToHomebridge']) : intval de cette valeur (provenance
 *      `equipement`), sinon intval(config::byKey('sendToHomebridgeDefault', 'homebridge', 1, true))
 *      (provenance `defaut_homebridge`) ; exposé si la valeur est différente de 0.
 * Aucun drapeau par commande. Scénario : exposé si isset(configuration['sendToHomebridge'])
 * et valeur != "0" ; clé absente = NON exposé (corrigé par ClaudeBox le 12/10, R1 de #261).
 *
 * `null` (provenance `illisible`) seulement pour une exception de lecture : jamais pour une
 * valeur inattendue, dont Homebridge décide. Aucune écriture dans la configuration de Jeedom
 * ou de Homebridge.
 */

/** Plugins que Homebridge n'expose jamais. */
const JEEDOM2HA_HOMEKIT_EXCLUDED_PLUGINS = array('mobile', 'homebridge');

/** Marqueur : lecture d'une valeur de configuration en échec (exception). */
const JEEDOM2HA_HOMEKIT_UNREADABLE = '__jeedom2ha_unreadable__';

/**
 * Identifiant physique : chaîne non vide, sinon null (jamais une chaîne vide).
 * Ne doit être écrit dans aucun journal de niveau info ou supérieur (adresses d'appareil possibles).
 */
function jeedom2ha_normalize_logical_id($raw): ?string {
  if ($raw === null || is_array($raw) || is_object($raw) || is_bool($raw)) {
    return null;
  }
  $value = trim(strval($raw));
  return $value === '' ? null : $value;
}

/**
 * Normalise la liste des plugins actifs rendue par plugin::listPlugin(true, false, true, true) :
 * liste simple d'identifiants. Rend null si la liste n'est pas exploitable.
 */
function jeedom2ha_homekit_normalize_active_plugins($list): ?array {
  if (!is_array($list)) {
    return null;
  }
  $ids = array();
  foreach ($list as $item) {
    if (is_string($item) && $item !== '') {
      $ids[$item] = true;
    }
  }
  return $ids;
}

/**
 * Résultat du signal : exposed true|false|null et provenance.
 */
function jeedom2ha_homekit_result(?bool $exposed, string $source): array {
  return array('exposed' => $exposed, 'source' => $source);
}

/**
 * Signal d'exposition d'un équipement.
 *
 * @param string $eqType   nom du plugin de l'équipement (getEqType_name)
 * @param mixed  $objectId identifiant de pièce brut (null, -1 ou entier)
 * @param mixed  $eqConf   tableau brut de configuration de l'équipement (getConfiguration()
 *                         sans argument) ; JEEDOM2HA_HOMEKIT_UNREADABLE si la lecture a échoué
 * @param array  $ctx      contexte de lecture :
 *   'homebridge'     => 'present' | 'absent' | 'unreadable'
 *   'default'        => valeur brute de config::byKey('sendToHomebridgeDefault', 'homebridge', 1, true)
 *                       ou JEEDOM2HA_HOMEKIT_UNREADABLE
 *   'active_plugins' => ids actifs (jeedom2ha_homekit_normalize_active_plugins) ou null
 *   'rooms'          => [id => getConfiguration('sendToHomebridge', 0) de la pièce | UNREADABLE]
 * @return array{exposed: ?bool, source: string}
 */
function jeedom2ha_homekit_eq_exposure(string $eqType, $objectId, $eqConf, array $ctx): array {
  $homebridge = $ctx['homebridge'] ?? 'unreadable';
  if ($homebridge === 'absent') {
    return jeedom2ha_homekit_result(null, 'homebridge_absent');
  }
  if ($homebridge !== 'present') {
    return jeedom2ha_homekit_result(null, 'illisible');
  }

  // 2. Plugin de l'équipement : la liste des plugins actifs fait foi.
  if (in_array($eqType, JEEDOM2HA_HOMEKIT_EXCLUDED_PLUGINS, true)) {
    return jeedom2ha_homekit_result(false, 'plugin_excluded');
  }
  $active = $ctx['active_plugins'] ?? null;
  if (!is_array($active)) {
    return jeedom2ha_homekit_result(null, 'illisible');
  }
  if (!isset($active[$eqType])) {
    return jeedom2ha_homekit_result(false, 'plugin_excluded');
  }

  // 3. Pièce : identifiant non nul, différent de -1, pièce existante, configuration == 1 (défaut 0).
  $rooms = $ctx['rooms'] ?? array();
  if ($objectId === null || !is_numeric($objectId) || intval($objectId) === -1
      || !array_key_exists(intval($objectId), $rooms)) {
    return jeedom2ha_homekit_result(false, 'piece');
  }
  $roomRaw = $rooms[intval($objectId)];
  if ($roomRaw === JEEDOM2HA_HOMEKIT_UNREADABLE) {
    return jeedom2ha_homekit_result(null, 'illisible');
  }
  if (!($roomRaw == 1)) { // comparaison souple, comme Homebridge
    return jeedom2ha_homekit_result(false, 'piece');
  }

  // 4. Équipement (isset sur le tableau brut), sinon valeur par défaut de Homebridge.
  if ($eqConf === JEEDOM2HA_HOMEKIT_UNREADABLE) {
    return jeedom2ha_homekit_result(null, 'illisible');
  }
  if (is_array($eqConf) && isset($eqConf['sendToHomebridge'])) {
    return jeedom2ha_homekit_result(intval($eqConf['sendToHomebridge']) !== 0, 'equipement');
  }
  $default = array_key_exists('default', $ctx) ? $ctx['default'] : 1;
  if ($default === JEEDOM2HA_HOMEKIT_UNREADABLE) {
    return jeedom2ha_homekit_result(null, 'illisible');
  }
  return jeedom2ha_homekit_result(intval($default) !== 0, 'defaut_homebridge');
}

/**
 * Signal d'exposition d'un scénario : exposé si isset(configuration['sendToHomebridge']) et
 * valeur != "0" (clé absente = NON exposé). $readConfig rend le tableau brut de configuration
 * (lecture seule) ; une exception de lecture rend null (illisible).
 */
function jeedom2ha_homekit_scenario_exposure(callable $readConfig): array {
  try {
    $conf = call_user_func($readConfig);
  } catch (Throwable $e) {
    return jeedom2ha_homekit_result(null, 'illisible');
  }
  $exposed = is_array($conf) && isset($conf['sendToHomebridge']) && $conf['sendToHomebridge'] != '0';
  return jeedom2ha_homekit_result($exposed, 'scenario_configuration');
}
