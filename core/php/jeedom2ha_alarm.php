<?php
/* SPDX-License-Identifier: AGPL-3.0-or-later
 * This file is part of Jeedom2HA.
 *
 * FR49 (CC-64) — alarme : fonctions pures, sans dépendance au cœur Jeedom (testées par
 * tests/test_php_alarm.php).
 * - export en LECTURE SEULE des clés de mode posées par Homebridge sur l'eqLogic d'une alarme
 *   (`SetModePresent`, `SetModeAbsent`, `SetModeNuit`, format « id|libellé ») : aucune écriture
 *   côté Jeedom ;
 * - code de désarmement saisi dans la configuration du plugin (4 à 8 chiffres) : stocké chiffré, transmis au
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
// Revue de 12.4 : code numérique de 4 à 8 chiffres (pavé numérique de HA, `code: REMOTE_CODE`).
if (!defined('JEEDOM2HA_ALARM_CODE_PATTERN')) {
  define('JEEDOM2HA_ALARM_CODE_PATTERN', '/^[0-9]{4,8}$/');
}
if (!defined('JEEDOM2HA_ALARM_CODE_INVALID_MESSAGE')) {
  define('JEEDOM2HA_ALARM_CODE_INVALID_MESSAGE', 'Code de désarmement refusé : il doit compter 4 à 8 chiffres (0 à 9), sans lettre ni symbole. Le code enregistré n\'a pas changé.');
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

/**
 * Champs à ajouter au corps de /action/mqtt_connect (jamais journalisés) :
 * - aucun code enregistré : tableau vide (comportement sans code) ;
 * - code lisible : `alarm_disarm_code` ;
 * - code enregistré mais illisible (déchiffrement en échec, en erreur ou vide) :
 *   `alarm_disarm_code_unreadable` = true, sans aucune valeur — le démon exige alors toujours
 *   le code dans la discovery et refuse tout désarmement venant de HA.
 */
function jeedom2ha_alarm_code_daemon_fields($_stored, callable $_decrypt): array {
  if (!is_string($_stored) || $_stored === '') {
    return array();
  }
  try {
    $code = $_decrypt($_stored);
  } catch (Throwable $e) {
    $code = null;
  }
  if (is_string($code) && trim($code) !== '') {
    return array('alarm_disarm_code' => $code);
  }
  return array('alarm_disarm_code_unreadable' => true);
}

/** Code saisi, espaces de début et de fin retirés ('' si ce n'est pas un texte ou un entier). */
function jeedom2ha_alarm_code_normalize($_value): string {
  if (is_int($_value)) {
    return (string) $_value;
  }
  return is_string($_value) ? trim($_value) : '';
}

/** Le code saisi (normalisé) compte 4 à 8 chiffres, et rien d'autre. */
function jeedom2ha_alarm_code_is_valid($_value): bool {
  return preg_match(JEEDOM2HA_ALARM_CODE_PATTERN, jeedom2ha_alarm_code_normalize($_value)) === 1;
}

/**
 * Valeur à enregistrer quand l'utilisateur saisit un code : le code (espaces de début et de fin
 * retirés) chiffré ; une saisie vide ou blanche garde le code déjà enregistré (`$_current`), comme
 * le mot de passe MQTT. Un code qui ne compte pas 4 à 8 chiffres est refusé : exception au message
 * clair (sans la valeur saisie), que le cœur affiche, et le code enregistré ne change pas.
 */
function jeedom2ha_alarm_code_to_store($_value, $_current, callable $_encrypt): string {
  $code = jeedom2ha_alarm_code_normalize($_value);
  if ($code === '') {
    return is_string($_current) ? $_current : '';
  }
  if (!jeedom2ha_alarm_code_is_valid($code)) {
    throw new InvalidArgumentException(JEEDOM2HA_ALARM_CODE_INVALID_MESSAGE);
  }
  return (string) $_encrypt($code);
}

/** La case « Retirer le code » est cochée. */
function jeedom2ha_alarm_code_clear_requested($_value): bool {
  return $_value === true || $_value === 1 || $_value === '1';
}

/**
 * Revue Codex de 12.4 (4e passe) — une commande est l'une des quatre infos de l'alarme lues
 * par le démon (Actif, Statut, Mode par generic type ; Immédiat par logicalId, plugin « alarm »),
 * même règle que `mapping/alarm_control_panel.py`.
 */
function jeedom2ha_alarm_is_info_cmd($_genericType, $_logicalId, $_eqTypeName): bool {
  if (in_array($_genericType, array('ALARM_ENABLE_STATE', 'ALARM_STATE', 'ALARM_MODE'), true)) {
    return true;
  }
  return $_logicalId === 'immediatState' && $_eqTypeName === 'alarm';
}

/**
 * Lecture au clic « Publier » d'une commande : rend la valeur telle quelle (le payload
 * `current_values` des autres types ne change pas) et note dans `$_readNull` une info d'alarme
 * effectivement LUE à null. Une commande non lue (échéance dépassée) n'appelle jamais cette
 * fonction : elle reste « non lue » pour le démon, qui garde sa lecture précédente.
 */
function jeedom2ha_alarm_click_read(array $_cmd, $_value, ArrayObject $_readNull) {
  if ($_value === null && !empty($_cmd['alarm_info'])) {
    $cmdId = (int) ($_cmd['cmd_id'] ?? 0);
    if ($cmdId > 0) {
      $_readNull[] = $cmdId;
    }
  }
  return $_value;
}

/**
 * Ajoute `current_values_null` (ids des infos d'alarme lues à null) au payload de
 * /action/execute, seulement si la lecture au clic a eu lieu (`current_values` présent) et
 * qu'au moins une info d'alarme a été lue à null. Sinon le payload est inchangé.
 */
function jeedom2ha_alarm_add_click_null_reads(array $_params, ArrayObject $_readNull): array {
  if (!array_key_exists('current_values', $_params) || count($_readNull) === 0) {
    return $_params;
  }
  $ids = array();
  foreach ($_readNull as $cmdId) {
    $cmdId = (int) $cmdId;
    if ($cmdId > 0 && !in_array($cmdId, $ids, true)) {
      $ids[] = $cmdId;
    }
  }
  if (!empty($ids)) {
    $_params['current_values_null'] = $ids;
  }
  return $_params;
}
