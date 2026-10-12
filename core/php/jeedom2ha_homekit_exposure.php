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

/*
 * Story 24.1 — signal d'exposition HomeKit (LECTURE SEULE) et identifiants physiques.
 *
 * Fonctions PURES : aucune dépendance au cœur Jeedom (pas de core.inc.php). Ce fichier est
 * chargé par core/class/jeedom2ha.class.php et directement par les tests CI
 * (tests/unit/test_story_24_1_php_homekit_exposure.php).
 *
 * Reproduit, sans jamais appeler le plugin Homebridge, la règle d'exposition de ce plugin
 * (lue le 2026-10-12 par ClaudeBox, plugins/homebridge/core/class/homebridge.class.php:2680-2710,
 * core/api/homebridge.api.php:44, homebridge.class.php:3119-3122 ; ce code n'est pas dans ce dépôt).
 * Un écart futur de Homebridge se corrige ICI. Un équipement est exposé si, dans l'ordre :
 *   1. le plugin Homebridge est installé et actif (sinon : signal inconnu) ;
 *   2. son plugin est actif, et n'est ni `mobile` ni `homebridge` ;
 *   3. il a une pièce (identifiant non nul, différent de -1, pièce existante) dont la
 *      configuration `sendToHomebridge` vaut 1 (lue avec la valeur par défaut 0 : une pièce
 *      sans clé n'expose rien) ;
 *   4. sa propre configuration `sendToHomebridge` vaut 1 ; clé absente : valeur par défaut
 *      `sendToHomebridgeDefault` de la configuration du plugin Homebridge (défaut 1).
 * Aucun drapeau par commande : les commandes héritent de l'équipement.
 * Scénario : exposé si `configuration.sendToHomebridge` est différent de « 0 » (absent = exposé).
 *
 * Tri-état strict : true / false / null (inconnu). Jamais false par défaut pour une valeur
 * inconnue. Aucune écriture dans la configuration de Jeedom ou de Homebridge.
 */

/** Plugins que Homebridge n'expose jamais. */
const JEEDOM2HA_HOMEKIT_EXCLUDED_PLUGINS = array('mobile', 'homebridge');

/** Marqueur : valeur de configuration de pièce illisible. */
const JEEDOM2HA_HOMEKIT_UNREADABLE = '__jeedom2ha_unreadable__';

/**
 * Normalise un drapeau 0/1 (entier, chaîne, booléen) ; null si absent ou illisible.
 */
function jeedom2ha_homekit_flag($raw): ?int {
  if (is_bool($raw)) {
    return $raw ? 1 : 0;
  }
  if (is_int($raw)) {
    return ($raw === 0 || $raw === 1) ? $raw : null;
  }
  if (is_string($raw)) {
    $clean = trim($raw);
    if ($clean === '0') {
      return 0;
    }
    if ($clean === '1') {
      return 1;
    }
  }
  return null;
}

/**
 * Valeur de configuration absente (clé non définie) : null ou chaîne vide.
 */
function jeedom2ha_homekit_is_absent($raw): bool {
  return $raw === null || (is_string($raw) && trim($raw) === '');
}

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
 * tolère une liste d'identifiants, un tableau indexé par identifiant ou des objets plugin.
 * Rend null si la liste n'est pas exploitable.
 */
function jeedom2ha_homekit_normalize_active_plugins($list): ?array {
  if (!is_array($list)) {
    return null;
  }
  $ids = array();
  foreach ($list as $key => $item) {
    if (is_object($item) && method_exists($item, 'getId')) {
      $ids[strval($item->getId())] = true;
      continue;
    }
    if (is_string($item) && $item !== '') {
      $ids[$item] = true;
    }
    if (is_string($key) && $key !== '') {
      $ids[$key] = true;
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
 * @param string $eqType     nom du plugin de l'équipement (getEqType_name)
 * @param mixed  $objectId   identifiant de pièce brut (null, -1 ou entier)
 * @param mixed  $eqRaw      configuration.sendToHomebridge brute de l'équipement (null si absente)
 * @param array  $ctx        contexte de lecture :
 *   'homebridge'          => 'present' | 'absent' | 'unreadable'
 *   'default'             => valeur brute de sendToHomebridgeDefault (null = défaut 1)
 *   'active_plugins'      => ids actifs (jeedom2ha_homekit_normalize_active_plugins) ou null
 *   'plugin_active_probe' => ?callable(string): ?bool, repli de lecture de l'activation d'un plugin
 *   'rooms'               => [id => valeur brute de la pièce | JEEDOM2HA_HOMEKIT_UNREADABLE]
 * @return array{exposed: ?bool, source: string}
 */
function jeedom2ha_homekit_eq_exposure(string $eqType, $objectId, $eqRaw, array $ctx): array {
  $homebridge = $ctx['homebridge'] ?? 'unreadable';
  if ($homebridge === 'absent') {
    return jeedom2ha_homekit_result(null, 'homebridge_absent');
  }
  if ($homebridge !== 'present') {
    return jeedom2ha_homekit_result(null, 'illisible');
  }

  // 2. Plugin de l'équipement.
  if (in_array($eqType, JEEDOM2HA_HOMEKIT_EXCLUDED_PLUGINS, true)) {
    return jeedom2ha_homekit_result(false, 'plugin_excluded');
  }
  $active = $ctx['active_plugins'] ?? null;
  $pluginActive = null;
  if (is_array($active) && isset($active[$eqType])) {
    $pluginActive = true;
  } elseif (isset($ctx['plugin_active_probe']) && is_callable($ctx['plugin_active_probe'])) {
    try {
      $pluginActive = call_user_func($ctx['plugin_active_probe'], $eqType);
    } catch (Throwable $e) {
      $pluginActive = null;
    }
  } elseif (is_array($active)) {
    $pluginActive = false;
  }
  if ($pluginActive === null) {
    return jeedom2ha_homekit_result(null, 'illisible');
  }
  if ($pluginActive === false) {
    return jeedom2ha_homekit_result(false, 'plugin_excluded');
  }

  // 3. Pièce : identifiant non nul, différent de -1, pièce existante, sendToHomebridge = 1 (défaut 0).
  $rooms = $ctx['rooms'] ?? array();
  if ($objectId === null || $objectId === '' || !is_numeric($objectId) || intval($objectId) <= 0
      || !array_key_exists(intval($objectId), $rooms)) {
    return jeedom2ha_homekit_result(false, 'piece');
  }
  $roomRaw = $rooms[intval($objectId)];
  if ($roomRaw === JEEDOM2HA_HOMEKIT_UNREADABLE) {
    return jeedom2ha_homekit_result(null, 'illisible');
  }
  if (jeedom2ha_homekit_is_absent($roomRaw)) {
    return jeedom2ha_homekit_result(false, 'piece'); // pièce sans clé = 0
  }
  $roomFlag = jeedom2ha_homekit_flag($roomRaw);
  if ($roomFlag === null) {
    return jeedom2ha_homekit_result(null, 'illisible');
  }
  if ($roomFlag !== 1) {
    return jeedom2ha_homekit_result(false, 'piece');
  }

  // 4. Équipement, puis valeur par défaut de Homebridge.
  if (!jeedom2ha_homekit_is_absent($eqRaw)) {
    $eqFlag = jeedom2ha_homekit_flag($eqRaw);
    if ($eqFlag === null) {
      return jeedom2ha_homekit_result(null, 'illisible');
    }
    return jeedom2ha_homekit_result($eqFlag === 1, 'equipement');
  }
  $defaultRaw = $ctx['default'] ?? null;
  if (jeedom2ha_homekit_is_absent($defaultRaw)) {
    return jeedom2ha_homekit_result(true, 'defaut_homebridge'); // défaut de Homebridge : 1
  }
  $defaultFlag = jeedom2ha_homekit_flag($defaultRaw);
  if ($defaultFlag === null) {
    return jeedom2ha_homekit_result(null, 'illisible');
  }
  return jeedom2ha_homekit_result($defaultFlag === 1, 'defaut_homebridge');
}

/**
 * Signal d'exposition d'un scénario : exposé si configuration.sendToHomebridge est différent
 * de « 0 » (absent = exposé). $readConfig est un callable sans argument qui lit la valeur
 * (lecture seule) ; une exception la rend illisible (null).
 */
function jeedom2ha_homekit_scenario_exposure(callable $readConfig): array {
  try {
    $raw = call_user_func($readConfig);
  } catch (Throwable $e) {
    return jeedom2ha_homekit_result(null, 'illisible');
  }
  return jeedom2ha_homekit_result($raw != '0', 'scenario_configuration');
}
