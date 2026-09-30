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
 * Story 19.5 (AC11) — fonctions PURES du réalignement des listeners d'état.
 *
 * Aucune dépendance au cœur Jeedom (pas de core.inc.php) : ce fichier est chargé
 * par core/class/jeedom2ha.class.php et core/ajax/jeedom2ha.ajax.php, et directement
 * par les tests CI (tests/unit/test_story_19_5_php_relay.php).
 */

/**
 * Valide la réponse de GET /system/state_listeners et rend les cibles normalisées
 * [['eq_id' => int, 'cmd_id' => int], ...], ou null si la réponse est inexploitable.
 * Tout-ou-rien : une seule cible mal formée invalide toute la réponse (revue Codex P2,
 * PR #184), car les listeners existants ne doivent être purgés que pour un ensemble sûr.
 * Une liste valide mais vide est acceptée (plus rien de publié : tout purger).
 */
function jeedom2ha_normalize_state_listener_targets($response): ?array {
  if (!is_array($response) || ($response['status'] ?? null) !== 'ok'
      || !isset($response['listeners']) || !is_array($response['listeners'])) {
    return null;
  }
  $targets = [];
  foreach ($response['listeners'] as $target) {
    if (!is_array($target) || !isset($target['cmd_id']) || !is_numeric($target['cmd_id'])) {
      return null;
    }
    $cmdId = intval($target['cmd_id']);
    if ($cmdId <= 0) {
      return null;
    }
    $eqId = $target['eq_id'] ?? 0;
    if (!is_numeric($eqId) || intval($eqId) < 0) {
      return null;
    }
    $targets[] = ['eq_id' => intval($eqId), 'cmd_id' => $cmdId];
  }
  return $targets;
}

/**
 * Réaligne les listeners d'état dans l'ordre récupérer -> valider -> purger -> créer.
 * Sur échec de la récupération (exception) ou réponse invalide, RIEN n'est supprimé :
 * les listeners existants sont conservés et un avertissement est journalisé.
 *
 * @param callable $fetchTargets  function(): mixed — réponse brute du démon
 * @param callable $listExisting  function(): iterable — listeners d'état existants
 * @param callable $removeListener function($listener): void
 * @param callable $createListener function(int $eqId, int $cmdId): void
 * @param callable $warn          function(string $message): void
 * @return int|null nombre de listeners créés, ou null si rien n'a été touché
 */
function jeedom2ha_realign_state_listeners(
  callable $fetchTargets,
  callable $listExisting,
  callable $removeListener,
  callable $createListener,
  callable $warn
): ?int {
  try {
    $response = $fetchTargets();
  } catch (\Throwable $e) {
    $warn('[STATE-LISTENER] Cibles indisponibles, listeners existants conservés : ' . $e->getMessage());
    return null;
  }

  $targets = jeedom2ha_normalize_state_listener_targets($response);
  if ($targets === null) {
    $warn('[STATE-LISTENER] Contrat state_listeners invalide, listeners existants conservés');
    return null;
  }

  foreach ($listExisting() as $existing) {
    $removeListener($existing);
  }

  $count = 0;
  foreach ($targets as $target) {
    $createListener($target['eq_id'], $target['cmd_id']);
    $count++;
  }
  return $count;
}

/**
 * Après une action HA, réaligne les listeners pour « publier » seulement, avec un budget
 * court (3 s, une seule tentative) pour rester sous les 20 s du client
 * (desktop/js/jeedom2ha.js:343). Jamais d'exception vers l'appelant : la réponse de
 * l'action n'est pas modifiée.
 *
 * @param string   $intention
 * @param mixed    $daemonResult réponse de /action/execute (null : démon muet, rien à faire)
 * @param callable $realign      function(int $timeout, int $maxAttempts): int
 * @param callable $warn         function(string $message): void
 * @return bool true si le réalignement a été tenté
 */
function jeedom2ha_realign_after_action(string $intention, $daemonResult, callable $realign, callable $warn): bool {
  if ($intention !== 'publier' || $daemonResult === null) {
    return false;
  }
  try {
    $realign(3, 1);
  } catch (\Throwable $e) {
    $warn('[ACTION] Réalignement des listeners après publier : ' . $e->getMessage());
  }
  return true;
}
