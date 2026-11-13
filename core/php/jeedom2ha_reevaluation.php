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
 * Story 24.14 (décision D2 A) — réévaluation des décisions de publication sans redémarrage.
 *
 * Dans Jeedom, `isActive` d'un scénario et `isEnable` d'un équipement servent souvent de planning (agenda, modes,
 * autre scénario) : ils basculent plusieurs fois par jour. Le démon ne les relit qu'à une synchro complète. Le cron
 * du plugin (`jeedom2ha::cron5()`) calcule ici une EMPREINTE légère de l'état qui pilote les décisions et ne lance une
 * synchro de service que si elle a changé depuis la dernière synchro réussie.
 *
 * Fonctions PURES : aucune dépendance au cœur Jeedom (pas de chargement du cœur, pas de classe `config`, `DB` ni `log`) ;
 * la lecture de la base, du démon, de la configuration et le journal sont injectés par l'appelant
 * (core/class/jeedom2ha.class.php). Chargé directement par les tests CI (tests/test_php_story_24_14_reevaluation.php).
 *
 * L'empreinte ne contient AUCUN nom (équipement, scénario, pièce) : seulement des identifiants numériques, des
 * drapeaux et la source d'exclusion effective, puis un condensé SHA-256.
 */

if (!defined('JEEDOM2HA_REEVALUATION_FINGERPRINT_KEY')) {
  /** Clé de configuration du plugin qui garde l'empreinte de la dernière synchro réussie (pas de table DB). */
  define('JEEDOM2HA_REEVALUATION_FINGERPRINT_KEY', 'decisionFingerprint');
  /** Délai du POST /action/sync de service (le démon attend au plus 7 s le verrou, puis répond 409). */
  define('JEEDOM2HA_REEVALUATION_SYNC_TIMEOUT_S', 60);
}

/** Identifiants numériques d'une chaîne CSV, règle de l'extraction de la topologie (trim, unique, is_numeric). */
function jeedom2ha_reevaluation_csv_ids($csv): array {
  $ids = array_map('intval', array_filter(array_unique(array_map('trim', explode(',', (string) $csv))), 'is_numeric'));
  sort($ids);
  return array_values(array_unique($ids));
}

/** Identifiants de plugins d'une chaîne CSV (trim, unique, non vides), triés. */
function jeedom2ha_reevaluation_csv_plugins($csv): array {
  $plugins = array_values(array_filter(array_unique(array_map('trim', explode(',', (string) $csv))), 'strlen'));
  sort($plugins, SORT_STRING);
  return $plugins;
}

/**
 * Ligne `eqLogic` brute (base de données) -> état qui pilote la décision, sans nom.
 * Colonnes lues : `id`, `isEnable`, `eqType_name`, `object_id`, `configuration` (JSON).
 *
 * @return array{id:int,is_enable:bool,eq_type:string,object_id:?int,excluded:bool}|null  null pour une ligne illisible
 */
function jeedom2ha_reevaluation_eq_row(array $row): ?array {
  if (!isset($row['id']) || !is_numeric($row['id'])) {
    return null;
  }
  $configuration = $row['configuration'] ?? null;
  if (is_string($configuration)) {
    $decoded = json_decode($configuration, true);
    $configuration = is_array($decoded) ? $decoded : array();
  }
  if (!is_array($configuration)) {
    $configuration = array();
  }
  $objectId = $row['object_id'] ?? null;
  return array(
    'id' => (int) $row['id'],
    'is_enable' => (bool) ($row['isEnable'] ?? true),
    'eq_type' => (string) ($row['eqType_name'] ?? ''),
    'object_id' => ($objectId === null || $objectId === '') ? null : (int) $objectId,
    // Même lecture que l'extraction : (bool) getConfiguration('jeedom2ha_excluded', false)
    'excluded' => (bool) ($configuration['jeedom2ha_excluded'] ?? false),
  );
}

/**
 * Empreinte des décisions de publication (SHA-256 hexadécimal).
 *
 * Entrées :
 * - `$eqRows` : lignes `eqLogic` brutes (voir jeedom2ha_reevaluation_eq_row) ; les équipements du plugin lui-même
 *   (`$selfEqType`) sont ignorés, comme dans l'extraction.
 * - `$scenarioRows` : lignes `scenario` brutes (`id`, `isActive`).
 * - `$settings` : `excludedPlugins` et `excludedObjects` (chaînes CSV de la configuration du plugin).
 *
 * L'empreinte change si un `isEnable`, un `isActive`, une exclusion d'équipement, la liste des plugins ou des pièces
 * exclus (ou l'exclusion effective d'un équipement qui change de pièce) change ; elle ne dépend pas de l'ordre de
 * lecture. Une ligne illisible est ignorée.
 */
function jeedom2ha_decision_fingerprint(array $eqRows, array $scenarioRows, array $settings, string $selfEqType = 'jeedom2ha'): string {
  $excludedPlugins = jeedom2ha_reevaluation_csv_plugins($settings['excludedPlugins'] ?? '');
  $excludedObjects = jeedom2ha_reevaluation_csv_ids($settings['excludedObjects'] ?? '');

  $equipments = array();
  foreach ($eqRows as $raw) {
    $row = is_array($raw) ? jeedom2ha_reevaluation_eq_row($raw) : null;
    if ($row === null || $row['eq_type'] === $selfEqType) {
      continue;
    }
    // Source d'exclusion effective, priorité de l'extraction : équipement > plugin > pièce.
    $exclusion = '-';
    if ($row['excluded']) {
      $exclusion = 'e';
    } elseif (in_array($row['eq_type'], $excludedPlugins, true)) {
      $exclusion = 'p';
    } elseif ($row['object_id'] !== null && in_array($row['object_id'], $excludedObjects, true)) {
      $exclusion = 'o';
    }
    $equipments[$row['id']] = $row['id'] . ':' . ($row['is_enable'] ? '1' : '0') . ':' . $exclusion;
  }
  ksort($equipments);

  $scenarios = array();
  foreach ($scenarioRows as $raw) {
    if (!is_array($raw) || !isset($raw['id']) || !is_numeric($raw['id'])) {
      continue;
    }
    $id = (int) $raw['id'];
    $scenarios[$id] = $id . ':' . ((bool) ($raw['isActive'] ?? false) ? '1' : '0');
  }
  ksort($scenarios);

  $canonical = json_encode(array(
    'v' => 1,
    'eq' => array_values($equipments),
    'sc' => array_values($scenarios),
    'excluded_plugins' => $excludedPlugins,
    'excluded_objects' => $excludedObjects,
  ));
  return hash('sha256', (string) $canonical);
}

/**
 * Story 24.14 (revue P2) — une réponse de POST /action/sync permet-elle de mémoriser l'empreinte ?
 * Oui seulement si la synchro a complètement réussi (`status` ok, `operation_result` `succes`) et si tous les boutons de scénario et leurs disponibilités
 * ont été publiés (`scenario_availability_complete` différent de false ; absent chez un démon plus ancien = oui).
 * Sinon l'empreinte n'est pas mémorisée : la tâche périodique réessaie à l'échéance suivante.
 */
function jeedom2ha_reevaluation_sync_can_remember($result): bool {
  return is_array($result)
    && ($result['status'] ?? null) === 'ok'
    // Revue P2 : synchro complètement réussie seulement (aucun échec de publication d'équipement, de secondaire,
    // de disponibilité, ni de dépublication différée) ; champ absent chez un démon plus ancien = réussite.
    && ($result['operation_result'] ?? 'succes') === 'succes'
    && ($result['scenario_availability_complete'] ?? true) !== false;
}

/**
 * Story 24.14 (revue P2, 3e passe) — invalide l'empreinte mémorisée AVANT d'envoyer une synchro (tâche périodique,
 * démarrage, « Relire Jeedom »). Une synchro partielle, en échec, refusée, sans réponse ou interrompue laisse ainsi
 * une empreinte vide : le pas suivant resynchronise quoi qu'il arrive, même si l'état Jeedom est revenu entre-temps à
 * celui de l'ancienne empreinte (actif -> désactivé -> synchro partielle -> réactivé). Seule une synchro complète
 * mémorise ensuite la nouvelle empreinte.
 *
 * @param callable $store (string) => void
 */
function jeedom2ha_reevaluation_invalidate_before_sync(callable $store): void {
  $store('');
}

/**
 * Story 24.14 (revue P2) — après une synchro complète hors tâche périodique (démarrage du démon, « Relire Jeedom »),
 * mémorise l'empreinte lue AVANT la topologie, si la réponse le permet. `$fingerprint` null (illisible) : rien.
 *
 * @return bool true si l'empreinte a été mémorisée
 */
function jeedom2ha_reevaluation_remember_after_sync(?string $fingerprint, $result, callable $store): bool {
  if ($fingerprint === null || $fingerprint === '' || !jeedom2ha_reevaluation_sync_can_remember($result)) {
    return false;
  }
  $store($fingerprint);
  return true;
}

/**
 * Un pas de la tâche périodique : synchro de service seulement si l'empreinte a changé et si le démon est prêt.
 *
 * Dépendances injectées (toutes obligatoires) :
 * - `fingerprint` () => string        empreinte courante (peut lever)
 * - `stored`      () => string        empreinte de la dernière synchro réussie ('' si aucune)
 * - `store`       (string) => void    mémorise l'empreinte
 * - `ready`       () => bool          démon joignable et broker connecté
 * - `topology`    () => array         topologie complète (getFullTopology)
 * - `sync`        (array) => ?array   POST /action/sync en mode service
 * - `listeners`   () => void          réaligne les listeners d'état après une synchro réussie
 * - `log`         (string $level, string $message) => void
 *
 * Retour : `['status' => unchanged|synced|partial|deferred|skipped|failed, 'reason' => string]`.
 * `partial` : synchro aboutie mais partielle (publication d'équipement ou de scénario en échec) ; empreinte non
 * mémorisée, nouvel essai à l'échéance suivante.
 * Un refus 409 (`action_in_progress`) n'est pas une erreur : rien n'est mémorisé, nouvel essai à l'échéance suivante.
 * L'empreinte est lue AVANT la topologie : un changement survenu pendant la synchro sera vu au pas suivant.
 */
function jeedom2ha_reevaluation_tick(array $deps): array {
  $log = $deps['log'];
  try {
    $current = (string) $deps['fingerprint']();
  } catch (\Throwable $e) {
    $log('warning', '[REEVAL] Empreinte illisible, réévaluation reportée : ' . $e->getMessage());
    return array('status' => 'skipped', 'reason' => 'fingerprint_unreadable');
  }
  if ($current !== '' && hash_equals((string) $deps['stored'](), $current)) {
    return array('status' => 'unchanged', 'reason' => 'fingerprint_unchanged');
  }
  try {
    $ready = (bool) $deps['ready']();
  } catch (\Throwable $e) {
    $ready = false;
  }
  if (!$ready) {
    $log('debug', '[REEVAL] État Jeedom changé, démon non prêt : réévaluation reportée');
    return array('status' => 'skipped', 'reason' => 'daemon_not_ready');
  }
  try {
    $topology = $deps['topology']();
  } catch (\Throwable $e) {
    $log('warning', '[REEVAL] Topologie illisible, réévaluation reportée : ' . $e->getMessage());
    return array('status' => 'skipped', 'reason' => 'topology_unavailable');
  }
  if (!is_array($topology)) {
    $log('warning', '[REEVAL] Topologie illisible, réévaluation reportée');
    return array('status' => 'skipped', 'reason' => 'topology_unavailable');
  }
  $log('info', '[REEVAL] État Jeedom changé (actif / désactivé / exclusion) : synchro de service');
  jeedom2ha_reevaluation_invalidate_before_sync($deps['store']);
  try {
    $result = $deps['sync']($topology);
  } catch (\Throwable $e) {
    $log('warning', '[REEVAL] Synchro de service échouée : ' . $e->getMessage());
    return array('status' => 'failed', 'reason' => 'sync_failed');
  }
  if (is_array($result) && ($result['code'] ?? null) === 'action_in_progress') {
    $log('info', '[REEVAL] Opération en cours dans le démon : synchro de service reportée à la prochaine échéance');
    return array('status' => 'deferred', 'reason' => 'action_in_progress');
  }
  if (!is_array($result) || ($result['status'] ?? null) !== 'ok') {
    $message = is_array($result) ? (string) ($result['message'] ?? 'réponse inattendue') : 'aucune réponse du démon';
    $log('warning', '[REEVAL] Synchro de service échouée : ' . $message);
    return array('status' => 'failed', 'reason' => 'sync_failed');
  }
  $partial = !jeedom2ha_reevaluation_sync_can_remember($result);
  if ($partial) {
    $log('warning', '[REEVAL] Synchro de service incomplète (publication partielle) : nouvel essai à la prochaine échéance');
  } else {
    $deps['store']($current);
  }
  try {
    $deps['listeners']();
  } catch (\Throwable $e) {
    $log('warning', '[REEVAL] Réenregistrement des listeners échoué : ' . $e->getMessage());
  }
  if ($partial) {
    return array('status' => 'partial', 'reason' => 'sync_incomplete');
  }
  $log('info', '[REEVAL] Synchro de service terminée');
  return array('status' => 'synced', 'reason' => 'fingerprint_changed');
}
