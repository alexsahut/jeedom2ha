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
 * Story 25.8 — exclusion d'une pièce depuis la surface : lecture-modification-écriture de la clé `excludedObjects`.
 *
 * Fonctions PURES : aucune dépendance au cœur Jeedom (pas de core.inc.php, pas de classe `config`) ; l'accès à la
 * configuration, au journal et à l'existence de l'objet est injecté par l'appelant. Chargé par
 * core/ajax/jeedom2ha.ajax.php, par la page (desktop/php/jeedom2ha.php) et directement par les tests CI
 * (tests/test_php_story_25_8_exclusion_piece.php).
 *
 * La clé est une chaîne CSV d'identifiants d'objets Jeedom. La règle de lecture est celle de l'extraction de la
 * topologie (core/class/jeedom2ha.class.php, `trim`, `array_unique`, `is_numeric`, `intval`) : ce que la surface
 * affiche exclu est exactement ce que le plugin exclut. Cette route n'appelle jamais le démon et ne lance jamais de
 * relecture : l'effet sur Home Assistant ne vient que de la relecture explicite enchaînée par l'interface.
 */

/**
 * Identifiants d'objets exclus lus dans la chaîne CSV, par la règle de l'extraction (core/class/jeedom2ha.class.php).
 *
 * @return int[]
 */
function jeedom2ha_excluded_object_ids($csv) {
  $raw = array_filter(array_unique(array_map('trim', explode(',', (string) $csv))), 'is_numeric');
  return array_values(array_map('intval', $raw));
}

/**
 * Exclut ou ne plus exclut un objet dans la chaîne CSV.
 *
 * Tous les autres jetons sont conservés, dans leur ordre (identifiants d'objets disparus et jetons non numériques
 * compris) ; les jetons vides sont ignorés. Exclure ajoute l'identifiant EN FIN s'il n'y figure pas déjà ; ne plus
 * exclure retire TOUTES les occurrences numériques égales. Sans changement, la chaîne d'origine est rendue telle quelle.
 *
 * @return array {csv: string, changed: bool, ids: int[]}
 */
function jeedom2ha_toggle_excluded_object($csv, $objectId, $excluded) {
  $csv = (string) $csv;
  $objectId = (int) $objectId;
  $tokens = array();
  foreach (explode(',', $csv) as $token) {
    $token = trim($token);
    if ($token !== '') {
      $tokens[] = $token;
    }
  }
  $matches = function ($token) use ($objectId) {
    return is_numeric($token) && intval($token) === $objectId;
  };
  $present = false;
  foreach ($tokens as $token) {
    if ($matches($token)) {
      $present = true;
      break;
    }
  }
  if ($excluded) {
    if ($present) {
      return array('csv' => $csv, 'changed' => false, 'ids' => jeedom2ha_excluded_object_ids($csv));
    }
    $tokens[] = (string) $objectId;
  } else {
    if (!$present) {
      return array('csv' => $csv, 'changed' => false, 'ids' => jeedom2ha_excluded_object_ids($csv));
    }
    $tokens = array_values(array_filter($tokens, function ($token) use ($matches) {
      return !$matches($token);
    }));
  }
  $next = implode(',', $tokens);
  return array('csv' => $next, 'changed' => true, 'ids' => jeedom2ha_excluded_object_ids($next));
}

/**
 * Route `saveRoomExclusion` (logique pure) : valide, lit, modifie, n'écrit QUE si la chaîne change.
 *
 * @param mixed    $objectId     identifiant brut reçu (entier strictement positif, 9 chiffres au plus)
 * @param mixed    $excluded     exactement '1' (exclure) ou '0' (ne plus exclure)
 * @param callable $objectExists function (int $id): bool — l'objet Jeedom existe
 * @param callable $readCsv      function (): string — valeur de `excludedObjects`
 * @param callable $saveCsv      function (string $value): void — écrit `excludedObjects` (seule clé écrite)
 * @param callable $log          function (string $level, string $message): void
 * @return array {object_id, excluded, changed, excluded_objects}
 * @throws Exception entrée refusée (aucune écriture, aucune ligne de journal, l'entrée brute n'est jamais citée)
 */
function jeedom2ha_save_room_exclusion($objectId, $excluded, callable $objectExists, callable $readCsv, callable $saveCsv, callable $log) {
  if (is_int($objectId)) {
    $objectId = (string) $objectId;
  }
  if (!is_string($objectId) || preg_match('/^[1-9][0-9]{0,8}$/', $objectId) !== 1) {
    throw new Exception('Identifiant de pièce invalide');
  }
  if (!is_string($excluded) || ($excluded !== '1' && $excluded !== '0')) {
    throw new Exception('Valeur d\'exclusion invalide');
  }
  $id = (int) $objectId;
  if ($objectExists($id) !== true) {
    throw new Exception('Pièce introuvable');
  }
  $result = jeedom2ha_toggle_excluded_object((string) $readCsv(), $id, $excluded === '1');
  if ($result['changed']) {
    $saveCsv($result['csv']);
  }
  $log('info', '[CONFIG] saveRoomExclusion: objectId=' . $id . ' excluded=' . $excluded . ' changed=' . ($result['changed'] ? '1' : '0'));
  return array(
    'object_id' => $id,
    'excluded' => $excluded === '1',
    'changed' => $result['changed'],
    'excluded_objects' => $result['ids'],
  );
}
