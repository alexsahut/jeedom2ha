<?php
/* SPDX-License-Identifier: AGPL-3.0-or-later
 * This file is part of Jeedom2HA.
 *
 * FR49 (CC-64) — alarme : fonctions pures, sans dépendance au cœur Jeedom (testées par
 * tests/test_php_alarm.php).
 * - export en LECTURE SEULE des clés de mode posées par Homebridge sur l'eqLogic d'une alarme
 *   (`SetModePresent`, `SetModeAbsent`, `SetModeNuit`, format « id|libellé ») : aucune écriture
 *   côté Jeedom ;
 * - code de désarmement saisi dans la configuration du plugin : stocké chiffré, transmis au
 *   démon dans le corps HTTP local de /action/mqtt_connect (jamais en ligne de commande, jamais
 *   dans un journal).
 */

if (!defined('JEEDOM2HA_ALARM_MODE_KEYS')) {
  define('JEEDOM2HA_ALARM_MODE_KEYS', array('SetModePresent', 'SetModeAbsent', 'SetModeNuit'));
}
if (!defined('JEEDOM2HA_ALARM_CODE_KEY')) {
  define('JEEDOM2HA_ALARM_CODE_KEY', 'alarmDisarmCode');
}
if (!defined('JEEDOM2HA_ALARM_CODE_CLEAR_KEY')) {
  define('JEEDOM2HA_ALARM_CODE_CLEAR_KEY', 'alarmDisarmCodeClear');
}

/**
 * Clés de mode d'un équipement alarme (au moins une commande de generic type ALARM_*), lues par
 * `$_config($key)` (getConfiguration de l'eqLogic). Seules les clés présentes, scalaires et non
 * vides sont rendues, telles quelles ; aucun équipement sans commande ALARM_* n'en porte.
 */
function jeedom2ha_alarm_mode_config(array $_cmdGenericTypes, callable $_config): array {
  $isAlarm = false;
  foreach ($_cmdGenericTypes as $genericType) {
    if (is_string($genericType) && strpos($genericType, 'ALARM_') === 0) {
      $isAlarm = true;
      break;
    }
  }
  if (!$isAlarm) {
    return array();
  }
  $out = array();
  foreach (JEEDOM2HA_ALARM_MODE_KEYS as $key) {
    try {
      $value = $_config($key);
    } catch (Throwable $e) {
      continue;
    }
    if ((is_string($value) || is_int($value)) && trim((string) $value) !== '') {
      $out[$key] = (string) $value;
    }
  }
  return $out;
}

/** Code à transmettre au démon : le code déchiffré, ou '' s'il n'y en a pas (jamais journalisé). */
function jeedom2ha_alarm_code_for_daemon($_stored, callable $_decrypt): string {
  if (!is_string($_stored) || $_stored === '') {
    return '';
  }
  try {
    $code = $_decrypt($_stored);
  } catch (Throwable $e) {
    return '';
  }
  return (is_string($code) && trim($code) !== '') ? $code : '';
}

/**
 * Valeur à enregistrer quand l'utilisateur saisit un code : le code chiffré ; une saisie vide ou
 * blanche garde le code déjà enregistré (`$_current`), comme le mot de passe MQTT.
 */
function jeedom2ha_alarm_code_to_store($_value, $_current, callable $_encrypt): string {
  if (!is_string($_value) || trim($_value) === '') {
    return is_string($_current) ? $_current : '';
  }
  return (string) $_encrypt($_value);
}

/** La case « Retirer le code » est cochée. */
function jeedom2ha_alarm_code_clear_requested($_value): bool {
  return $_value === true || $_value === 1 || $_value === '1';
}
