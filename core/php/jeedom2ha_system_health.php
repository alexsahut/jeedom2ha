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
 * story/system-health — appareil Home Assistant « Santé de Jeedom », en LECTURE SEULE.
 *
 * Désactivé par défaut (case `publishSystemHealth` de la configuration du plugin). Activé, le cron du plugin
 * (`jeedom2ha::cron5()`) relève :
 * - l'état du démon de chaque plugin actif qui a son propre démon (`hasOwnDeamon`), sauf jeedom2ha lui-même (son état
 *   est déjà l'entité « État du pont ») : `deamon_info()['state'] === 'ok'` -> en marche ;
 * - le nombre de mises à jour disponibles (`update::nbNeedUpdate()`) ;
 * - le nombre de messages du centre de messages (`message::nbMessage()`), JAMAIS leur texte ;
 * - la version du cœur (`jeedom::version()`).
 * Le relevé n'est envoyé au démon (POST /action/system_health) que si son EMPREINTE change. Décocher la case envoie une
 * seule demande de purge (configurations retenues vidées dans Home Assistant), puis plus rien.
 *
 * Fonctions PURES : aucune dépendance au cœur Jeedom (pas de classe `plugin`, `update`, `message`, `config` ni `log`
 * ici) ; les lectures, l'appel au démon et le journal sont injectés par l'appelant (core/class/jeedom2ha.class.php).
 * Chaque lecture est protégée : un plugin absent, sans méthode attendue ou qui lève une exception ne bloque ni le
 * relevé ni le cron (Jeedom 4.4, 4.5 et 4.6). Chargé directement par les tests CI
 * (tests/test_php_story_system_health.php).
 */

if (!defined('JEEDOM2HA_SYSTEM_HEALTH_ENABLED_KEY')) {
  /** Case de la configuration du plugin (désactivée par défaut). */
  define('JEEDOM2HA_SYSTEM_HEALTH_ENABLED_KEY', 'publishSystemHealth');
  /** Empreinte du dernier relevé envoyé avec succès ('' = à renvoyer). */
  define('JEEDOM2HA_SYSTEM_HEALTH_FINGERPRINT_KEY', 'systemHealthFingerprint');
  /** '1' dès qu'un relevé a pu être publié : la case décochée demande alors une purge, une seule fois. */
  define('JEEDOM2HA_SYSTEM_HEALTH_PUBLISHED_KEY', 'systemHealthPublished');
  /** Route du démon. */
  define('JEEDOM2HA_SYSTEM_HEALTH_ROUTE', '/action/system_health');
  /** Délai de l'appel au démon (une purge relit les configurations retenues : fenêtre bornée). */
  define('JEEDOM2HA_SYSTEM_HEALTH_TIMEOUT_S', 15);
}

/** La case est-elle cochée ? (valeur de configuration brute : '1', 1, true, 'on'). */
function jeedom2ha_system_health_enabled($raw): bool {
  if (is_bool($raw)) {
    return $raw;
  }
  return in_array(strtolower(trim((string) $raw)), array('1', 'true', 'on', 'yes'), true);
}

/**
 * Texte du relevé en UTF-8 valide : les octets invalides sont remplacés, pour que json_encode ne rende jamais false
 * (sinon callDaemon n'enverrait aucun corps et le relevé serait retenté sans fin). Sans dépendance au cœur.
 */
function jeedom2ha_system_health_utf8(string $value): string {
  if ($value === '' || preg_match('//u', $value) === 1) {
    return $value;
  }
  if (function_exists('mb_convert_encoding')) {
    $clean = @mb_convert_encoding($value, 'UTF-8', 'UTF-8');
    if (is_string($clean) && preg_match('//u', $clean) === 1) {
      return $clean;
    }
  }
  if (function_exists('iconv')) {
    $clean = @iconv('UTF-8', 'UTF-8//IGNORE', $value);
    if (is_string($clean) && preg_match('//u', $clean) === 1) {
      return $clean;
    }
  }
  return (string) preg_replace('/[\x80-\xFF]/', '?', $value);
}

/**
 * Un plugin (objet `plugin` du cœur) -> ligne du relevé, ou null s'il ne produit rien (pas un objet, sans identifiant,
 * jeedom2ha lui-même, inactif, sans démon propre). L'état du démon illisible (méthode absente, exception, réponse
 * inattendue) donne « arrêté » : le démon n'est pas vérifié en marche. Ne lève jamais.
 *
 * @return array{id:string,name:string,running:bool}|null
 */
function jeedom2ha_system_health_plugin_row($plugin, string $selfId = 'jeedom2ha'): ?array {
  try {
    if (!is_object($plugin) || !method_exists($plugin, 'getId')) {
      return null;
    }
    $id = trim(jeedom2ha_system_health_utf8((string) $plugin->getId()));
    if ($id === '' || $id === $selfId) {
      return null;
    }
    if (method_exists($plugin, 'isActive') && intval($plugin->isActive()) !== 1) {
      return null;
    }
    if (!method_exists($plugin, 'getHasOwnDeamon') || intval($plugin->getHasOwnDeamon()) !== 1) {
      return null;
    }
    $name = method_exists($plugin, 'getName') ? trim(jeedom2ha_system_health_utf8((string) $plugin->getName())) : '';
  } catch (\Throwable $e) {
    return null;
  }
  $running = false;
  try {
    if (method_exists($plugin, 'deamon_info')) {
      $info = $plugin->deamon_info();
      $running = is_array($info) && (($info['state'] ?? null) === 'ok');
    }
  } catch (\Throwable $e) {
    $running = false;
  }
  return array('id' => $id, 'name' => $name !== '' ? $name : $id, 'running' => $running);
}

/** Lecture protégée d'un compteur : entier >= 0, ou null si illisible. */
function jeedom2ha_system_health_count(callable $reader): ?int {
  try {
    $value = $reader();
  } catch (\Throwable $e) {
    return null;
  }
  if (is_int($value) && $value >= 0) {
    return $value;
  }
  if (is_string($value) && preg_match('/^[0-9]{1,9}$/', trim($value))) {
    return (int) trim($value);
  }
  if (is_array($value)) {
    return count($value);
  }
  return null;
}

/** Lecture protégée de la version du cœur : texte court, ou null. */
function jeedom2ha_system_health_version(callable $reader): ?string {
  try {
    $value = $reader();
  } catch (\Throwable $e) {
    return null;
  }
  $value = is_scalar($value) ? trim(jeedom2ha_system_health_utf8((string) $value)) : '';
  return ($value === '' || strlen($value) > 64) ? null : $value;
}

/**
 * Relevé complet. Lecteurs injectés (tous facultatifs ; absents = rien de lu) :
 * - `plugins`     () => array   objets `plugin` actifs (plugin::listPlugin(true)) ;
 * - `updates`     () => int     update::nbNeedUpdate() ;
 * - `messages`    () => int     message::nbMessage() ;
 * - `core_version`() => string  jeedom::version().
 * Les démons sont triés par identifiant (empreinte indépendante de l'ordre de lecture) ; un identifiant en double
 * n'est gardé qu'une fois.
 *
 * @return array{daemons:array,updates:?int,messages:?int,core_version:?string}
 */
function jeedom2ha_system_health_snapshot(array $readers, string $selfId = 'jeedom2ha'): array {
  $plugins = array();
  if (isset($readers['plugins']) && is_callable($readers['plugins'])) {
    try {
      $listed = $readers['plugins']();
      $plugins = is_array($listed) ? $listed : array();
    } catch (\Throwable $e) {
      $plugins = array();
    }
  }
  $daemons = array();
  foreach ($plugins as $plugin) {
    $row = jeedom2ha_system_health_plugin_row($plugin, $selfId);
    if ($row !== null && !isset($daemons[$row['id']])) {
      $daemons[$row['id']] = $row;
    }
  }
  ksort($daemons, SORT_STRING);
  $none = function () {
    return null;
  };
  return array(
    'daemons' => array_values($daemons),
    'updates' => jeedom2ha_system_health_count($readers['updates'] ?? $none),
    'messages' => jeedom2ha_system_health_count($readers['messages'] ?? $none),
    'core_version' => jeedom2ha_system_health_version($readers['core_version'] ?? $none),
  );
}

/** Empreinte du relevé (SHA-256 hexadécimal) : change dès qu'une valeur publiée change, indépendante de l'ordre. */
function jeedom2ha_system_health_fingerprint(array $snapshot): string {
  $daemons = array();
  foreach (($snapshot['daemons'] ?? array()) as $row) {
    if (is_array($row) && isset($row['id'])) {
      $daemons[(string) $row['id']] = array((string) $row['id'], (string) ($row['name'] ?? ''), (bool) ($row['running'] ?? false));
    }
  }
  ksort($daemons, SORT_STRING);
  return hash('sha256', (string) json_encode(array(
    'v' => 1,
    'daemons' => array_values($daemons),
    'updates' => $snapshot['updates'] ?? null,
    'messages' => $snapshot['messages'] ?? null,
    'core_version' => $snapshot['core_version'] ?? null,
  )));
}

/** Réponse du démon acceptée ? `status` ok, et purge complète quand elle est demandée. */
function jeedom2ha_system_health_response_ok($result, bool $purge = false): bool {
  if (!is_array($result) || ($result['status'] ?? null) !== 'ok') {
    return false;
  }
  return !$purge || (($result['purge_complete'] ?? false) === true);
}

/**
 * Un pas du cron. Dépendances injectées (toutes obligatoires) :
 * - `enabled`       () => bool          case cochée ;
 * - `published`     () => bool          un relevé a déjà été publié (purge à faire si la case est décochée) ;
 * - `set_published` (bool) => void
 * - `stored`        () => string        empreinte du dernier relevé envoyé avec succès ;
 * - `store`         (string) => void
 * - `snapshot`      () => array         relevé (jeedom2ha_system_health_snapshot) ;
 * - `send`          (array) => ?array   POST /action/system_health ;
 * - `log`           (string $level, string $message) => void
 *
 * Case décochée et rien de publié (le défaut) : AUCUNE lecture, AUCUN appel au démon.
 * Retour : `['status' => disabled|purged|unchanged|published|failed, 'reason' => string]`.
 */
function jeedom2ha_system_health_tick(array $deps): array {
  $log = $deps['log'];
  if (!$deps['enabled']()) {
    if (!$deps['published']()) {
      return array('status' => 'disabled', 'reason' => 'disabled');
    }
    $result = null;
    try {
      $result = $deps['send'](array('enabled' => false));
    } catch (\Throwable $e) {
      $result = null;
    }
    if (!jeedom2ha_system_health_response_ok($result, true)) {
      $log('warning', '[SYSTEM_HEALTH] Purge de « Santé de Jeedom » incomplète, nouvel essai au prochain passage');
      return array('status' => 'failed', 'reason' => 'purge_failed');
    }
    $deps['set_published'](false);
    $deps['store']('');
    $log('info', '[SYSTEM_HEALTH] « Santé de Jeedom » retirée de Home Assistant');
    return array('status' => 'purged', 'reason' => 'disabled');
  }
  $snapshot = $deps['snapshot']();
  $fingerprint = jeedom2ha_system_health_fingerprint($snapshot);
  if (hash_equals((string) $deps['stored'](), $fingerprint)) {
    return array('status' => 'unchanged', 'reason' => 'fingerprint_unchanged');
  }
  // Marqué publié AVANT l'envoi : un envoi partiel suivi d'une case décochée déclenche bien la purge.
  $deps['set_published'](true);
  $result = null;
  try {
    $result = $deps['send'](array('enabled' => true, 'snapshot' => $snapshot));
  } catch (\Throwable $e) {
    $result = null;
  }
  if (!jeedom2ha_system_health_response_ok($result)) {
    // Envoi échoué ou partiel : Home Assistant peut garder une partie de ce relevé. L'empreinte mémorisée est
    // effacée pour que le relevé suivant soit TOUJOURS republié, même s'il revient aux valeurs d'avant.
    $deps['store']('');
    $log('warning', '[SYSTEM_HEALTH] Relevé non publié, nouvel essai au prochain passage');
    return array('status' => 'failed', 'reason' => 'send_failed');
  }
  $deps['store']($fingerprint);
  return array('status' => 'published', 'reason' => 'fingerprint_changed');
}

/** Démarrage du démon : l'empreinte est oubliée, le relevé suivant est renvoyé (le démon repart sans état). */
function jeedom2ha_system_health_invalidate(callable $store): void {
  $store('');
}
