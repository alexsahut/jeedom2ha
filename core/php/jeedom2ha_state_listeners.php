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
 * Story 19.5 (AC11) — fonctions PURES du réalignement des listeners d'état.
 * Story 12.6 (CC-45) — recalage par différence (jeedom2ha_state_listener_plan), testé par
 * tests/test_php_story_12_6_state_listeners_diff.php.
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
 * Story 12.6 (CC-45) — identifiant numérique strictement positif, ou null.
 * Accepte un entier ou une chaîne de chiffres (options relues depuis le JSON du cœur).
 */
function jeedom2ha_state_listener_positive_int($value): ?int {
  if (is_int($value)) {
    return $value > 0 ? $value : null;
  }
  if (is_string($value) && preg_match('/^[1-9][0-9]{0,18}$/', trim($value))) {
    return intval(trim($value));
  }
  return null;
}

/**
 * Story 12.6 (CC-45) — description d'un listener existant -> ['eq_id' => int, 'cmd_id' => int], ou null s'il est mal
 * formé. Bien formé = option `cmd_id` entière positive, `eq_id` entière positive ou nulle (contrat des cibles) ET un seul
 * événement, exactement `#<cmd_id>#`. `getEvent()` rend un tableau (cœur 4.4 à 4.6) ; chaîne JSON acceptée par défense.
 * Tout ce qui n'est pas compris est mal formé : un listener douteux est remplacé, jamais conservé.
 */
function jeedom2ha_state_listener_describe_normalize($description): ?array {
  if (!is_array($description)) {
    return null;
  }
  // eq_id 0 est une cible valide du contrat (jeedom2ha_normalize_state_listener_targets) : accepté ici aussi, sinon
  // un tel listener serait remplacé à chaque réalignement (revue 12.6).
  $rawEqId = $description['eq_id'] ?? null;
  $eqId = ($rawEqId === 0 || $rawEqId === '0') ? 0 : jeedom2ha_state_listener_positive_int($rawEqId);
  $cmdId = jeedom2ha_state_listener_positive_int($description['cmd_id'] ?? null);
  if ($eqId === null || $cmdId === null) {
    return null;
  }
  $events = $description['events'] ?? null;
  if (is_string($events)) {
    $events = json_decode($events, true);
  }
  if (!is_array($events) || count($events) !== 1) {
    return null;
  }
  // Revue Codex P2 (PR #421) : le cœur (listener::searchEvent) cherche le motif COMPLET `#<cmd_id>#`. Toute autre forme
  // (`101`, `"101"`, `"#101"`, `"101#"`, espaces…) ne se déclenche jamais : mal formé, donc remplacé.
  $event = reset($events);
  if (!is_string($event) || $event !== '#' . $cmdId . '#') {
    return null;
  }
  return array('eq_id' => $eqId, 'cmd_id' => $cmdId);
}

/**
 * Story 12.6 (CC-45) — différence PURE entre les cibles voulues et les listeners existants.
 *
 * @param array $targets  cibles normalisées [['eq_id' => int, 'cmd_id' => int], ...]
 *                        (jeedom2ha_normalize_state_listener_targets)
 * @param array $existing descriptions des listeners existants, dans l'ordre de relevé :
 *                        [['eq_id' => mixed, 'cmd_id' => mixed, 'events' => mixed, ...autres clés libres], ...]
 * @return array ['keep' => entrées conservées, 'create' => cibles à créer, 'remove' => entrées à supprimer,
 *               'replaced_malformed' => nombre de listeners mal formés d'une commande encore voulue (remplacés)]
 *
 * Règles : un listener bien formé d'une cible voulue est conservé (le premier relevé, le plus ancien) ; ses doublons,
 * les listeners qui ne sont plus voulus et les listeners mal formés sont supprimés ; une cible sans listener conservé
 * est créée une seule fois. Les entrées qui ne sont pas des tableaux sont ignorées (rien à désigner). Parc inchangé :
 * rien à créer ni à supprimer.
 */
function jeedom2ha_state_listener_plan(array $targets, array $existing): array {
  $wanted = array();
  foreach ($targets as $target) {
    $key = intval($target['eq_id']) . ':' . intval($target['cmd_id']);
    if (!isset($wanted[$key])) {
      $wanted[$key] = array('eq_id' => intval($target['eq_id']), 'cmd_id' => intval($target['cmd_id']));
    }
  }

  $wantedCmds = array();
  foreach ($wanted as $target) {
    $wantedCmds[$target['cmd_id']] = true;
  }

  $keep = array();
  $remove = array();
  $covered = array();
  $replacedMalformed = 0;
  foreach ($existing as $entry) {
    if (!is_array($entry)) {
      continue;
    }
    $normalized = jeedom2ha_state_listener_describe_normalize($entry);
    if ($normalized === null) {
      $remove[] = $entry;
      // Revue 6 : un listener mal formé d'une commande encore voulue est remplacé ; compté pour le signaler.
      $rawCmd = jeedom2ha_state_listener_positive_int($entry['cmd_id'] ?? null);
      if ($rawCmd !== null && isset($wantedCmds[$rawCmd])) {
        $replacedMalformed++;
      }
      continue;
    }
    $key = $normalized['eq_id'] . ':' . $normalized['cmd_id'];
    if (!isset($wanted[$key]) || isset($covered[$key])) {
      $remove[] = $entry; // plus voulu, ou doublon d'un listener déjà conservé
      continue;
    }
    $covered[$key] = true;
    $keep[] = $entry;
  }

  $create = array();
  foreach ($wanted as $key => $target) {
    if (!isset($covered[$key])) {
      $create[] = $target;
    }
  }
  return array('keep' => $keep, 'create' => $create, 'remove' => $remove, 'replaced_malformed' => $replacedMalformed);
}

/**
 * Réaligne les listeners d'état dans l'ordre récupérer -> valider -> relever -> créer -> purger.
 * Sur échec de la récupération (exception) ou réponse invalide, RIEN n'est touché : les
 * listeners existants sont conservés et un avertissement est journalisé.
 * Les nouveaux listeners sont créés AVANT de supprimer les anciens (revue Codex P2,
 * PR #185) : une exception pendant la création laisse les anciens intacts ; une exception
 * pendant la purge laisse des doublons temporaires (un évènement relayé deux fois, sans
 * effet : même valeur publiée), résorbés au réalignement suivant. Aucune commande ne se
 * retrouve sans écouteur.
 *
 * Story 12.6 (CC-45) — avec `$describeListener`, le réalignement se fait PAR DIFFÉRENCE
 * (jeedom2ha_state_listener_plan) : les listeners encore voulus et bien formés sont conservés
 * tels quels (même identifiant, aucune écriture), seuls les manquants sont créés et seuls les
 * indésirables (plus voulus, doublons, mal formés) supprimés. Parc inchangé : rien n'est touché,
 * donc plus de « Listener non trouvé » pour un évènement arrivé pendant une resynchronisation.
 * Sans `$describeListener` (appel historique), tous les existants sont remplacés.
 *
 * @param callable      $fetchTargets     function(): mixed — réponse brute du démon
 * @param callable      $listExisting     function(): iterable — listeners d'état existants
 * @param callable      $removeListener   function($listener): void
 * @param callable      $createListener   function(int $eqId, int $cmdId): void
 * @param callable      $warn             function(string $message): void
 * @param callable|null $describeListener function($listener): array ['eq_id', 'cmd_id', 'events'] (peut lever)
 * @param array|null    $stats            rempli avec ['kept', 'created', 'removed', 'replaced_malformed'] (entiers)
 * @return int|null nombre de listeners en place pour le parc (conservés + créés), ou null si rien n'a été appliqué
 */
function jeedom2ha_realign_state_listeners(
  callable $fetchTargets,
  callable $listExisting,
  callable $removeListener,
  callable $createListener,
  callable $warn,
  ?callable $describeListener = null,
  ?array &$stats = null
): ?int {
  $stats = array('kept' => 0, 'created' => 0, 'removed' => 0, 'replaced_malformed' => 0);
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

  try {
    // Relevé AVANT la création, pour ne jamais supprimer les listeners qu'on vient de créer.
    $listeners = array();
    foreach ($listExisting() as $listener) {
      $listeners[] = $listener;
    }
  } catch (\Throwable $e) {
    $warn('[STATE-LISTENER] Listeners existants illisibles, rien modifié : ' . $e->getMessage());
    return null;
  }

  $entries = array();
  foreach ($listeners as $index => $listener) {
    $description = array();
    if ($describeListener !== null) {
      try {
        $described = $describeListener($listener);
        $description = is_array($described) ? $described : array();
      } catch (\Throwable $e) {
        $description = array(); // illisible = mal formé : remplacé
      }
    }
    $description['_jeedom2ha_index'] = $index;
    $entries[] = $description;
  }
  $plan = jeedom2ha_state_listener_plan($targets, $entries);

  $created = 0;
  try {
    foreach ($plan['create'] as $target) {
      $createListener($target['eq_id'], $target['cmd_id']);
      $created++;
    }
  } catch (\Throwable $e) {
    $warn('[STATE-LISTENER] Création interrompue après ' . $created . ' listener(s), anciens listeners conservés : ' . $e->getMessage());
    $stats['kept'] = count($plan['keep']);
    $stats['created'] = $created;
    return null;
  }
  if ($describeListener !== null && $plan['replaced_malformed'] > 0) {
    // Revue 6 : visible au niveau de log par défaut, pour qu'une régression de format ne passe pas inaperçue.
    $warn('[STATE-LISTENER] ' . $plan['replaced_malformed'] . ' listener(s) mal formé(s) d\'une commande publiée remplacé(s)');
  }

  $removed = 0;
  try {
    foreach ($plan['remove'] as $entry) {
      $removeListener($listeners[$entry['_jeedom2ha_index']]);
      $removed++;
    }
  } catch (\Throwable $e) {
    $warn('[STATE-LISTENER] Purge interrompue, doublons temporaires jusqu\'au prochain réalignement : ' . $e->getMessage());
  }
  $stats = array('kept' => count($plan['keep']), 'created' => $created, 'removed' => $removed,
    'replaced_malformed' => $plan['replaced_malformed']);
  return count($plan['keep']) + $created;
}

/**
 * Story 12.6 (revue 7) — prend le verrou exclusif du réalignement, pour que deux réalignements concurrents (cron5 et un
 * clic, par exemple) ne se chevauchent pas. Fonction PURE : la prise non bloquante est injectée (dans la classe : `flock`
 * sur un fichier du dossier temporaire du plugin ; le système le rend quand la poignée est fermée ou que le processus
 * meurt, et PHP ferme la poignée locale même si une exception remonte : jamais de blocage permanent).
 *
 * Attente bornée à `$waitS` secondes (nouvel essai toutes les 0,2 s). Verrou toujours occupé à l'échéance, ou prise du
 * verrou en échec : false et un avertissement ; l'appelant ne touche alors à rien et le réalignement suivant recale.
 *
 * @param callable $tryLock function(): bool — prise non bloquante (peut lever)
 * @param callable $sleep   function(float $seconds): void
 * @param callable $now     function(): float — secondes
 * @param float    $waitS   attente maximale
 * @param callable $warn    function(string $message): void
 * @return bool true si le verrou est pris
 */
function jeedom2ha_state_listener_acquire_lock(callable $tryLock, callable $sleep, callable $now, float $waitS, callable $warn): bool {
  $deadline = $now() + max(0.0, $waitS);
  while (true) {
    try {
      if ((bool) $tryLock()) {
        return true;
      }
    } catch (\Throwable $e) {
      $warn('[STATE-LISTENER] Verrou du réalignement indisponible, listeners inchangés : ' . $e->getMessage());
      return false;
    }
    if ($now() >= $deadline) {
      $warn('[STATE-LISTENER] Réalignement déjà en cours, celui-ci est abandonné (listeners inchangés, recalés au suivant)');
      return false;
    }
    $sleep(0.2);
  }
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
