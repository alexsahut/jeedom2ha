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

if (!defined('JEEDOM2HA_REEVALUATION_LIGHT_MAX_SCENARIOS')) {
  /** Story 24.18 (revue M4) — plafond de la liste envoyée à /action/scenario_activation (même valeur côté démon). */
  define('JEEDOM2HA_REEVALUATION_LIGHT_MAX_SCENARIOS', 5000);
}

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
 * Front v3 (Lot 4a) — liste d'identifiants de scénarios d'une clé de configuration (tableau déjà décodé par la lecture de configuration
 * ou chaîne JSON), triée et dédoublonnée ; null si la clé est absente ou illisible. Même règle que
 * jeedom2ha_scenario_id_list (core/php/jeedom2ha_scenario_publication.php), dupliquée pour garder ce fichier autonome.
 */
function jeedom2ha_reevaluation_scenario_ids($raw): ?array {
  if (is_string($raw) && $raw !== '') {
    $decoded = json_decode($raw, true);
    $raw = is_array($decoded) ? $decoded : null;
  }
  if (!is_array($raw)) {
    return null;
  }
  $ids = array();
  foreach ($raw as $value) {
    if (is_int($value) && $value > 0) {
      $ids[$value] = true;
    } elseif (is_string($value) && preg_match('/^[1-9][0-9]{0,9}$/', $value)) {
      $ids[(int) $value] = true;
    }
  }
  $ids = array_keys($ids);
  sort($ids);
  return $ids;
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
  // Front v3 (Lot 4a) — choix de publication des scénarios (`publishedScenarios`, `knownScenarioIds`), ajouté
  // seulement si au moins une des deux clés existe : sans elles, l'empreinte reste exactement celle d'avant (aucune
  // resynchro à la mise à jour du code) ; avec elles, tout changement de choix relance la synchro de service.
  $scenarioPublication = array(
    'published' => jeedom2ha_reevaluation_scenario_ids($settings['publishedScenarios'] ?? null),
    'known' => jeedom2ha_reevaluation_scenario_ids($settings['knownScenarioIds'] ?? null),
  );
  if ($scenarioPublication['published'] !== null || $scenarioPublication['known'] !== null) {
    $canonical .= '|scenario_publication:' . json_encode($scenarioPublication);
  }
  return hash('sha256', (string) $canonical);
}

/**
 * Story 24.18 — empreinte en deux parties, pour la « synchro légère ».
 *
 * - `structural` : tout ce que contient l'empreinte 24.14 SAUF l'activation des scénarios (équipements, identifiants de
 *   tous les scénarios, exclusions, choix de publication des scénarios) ;
 * - `activation` : `id:isActive` de TOUS les scénarios (revue 24.18, I1) : un scénario non publié qui bascule ne publie
 *   rien dans HA, mais le démon met à jour son instantané (écran des scénarios du plugin, export), comme la synchro
 *   complète ;
 * - `states` : `[['id' => int, 'is_active' => bool], ...]` de tous les scénarios, triés (envoyés au démon) ;
 * - `fingerprint` : valeur composite `v2:<structural>:<activation>`, la seule mémorisée (clé `decisionFingerprint`).
 *   Deux composites égales <=> les deux parties égales.
 *
 * @return array{structural:string,activation:string,states:array,fingerprint:string}
 */
function jeedom2ha_decision_fingerprint_parts(array $eqRows, array $scenarioRows, array $settings, string $selfEqType = 'jeedom2ha'): array {
  $excludedPlugins = jeedom2ha_reevaluation_csv_plugins($settings['excludedPlugins'] ?? '');
  $excludedObjects = jeedom2ha_reevaluation_csv_ids($settings['excludedObjects'] ?? '');

  $equipments = array();
  foreach ($eqRows as $raw) {
    $row = is_array($raw) ? jeedom2ha_reevaluation_eq_row($raw) : null;
    if ($row === null || $row['eq_type'] === $selfEqType) {
      continue;
    }
    // Même source d'exclusion effective que l'empreinte 24.14 : équipement > plugin > pièce.
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

  $published = jeedom2ha_reevaluation_scenario_ids($settings['publishedScenarios'] ?? null);
  $known = jeedom2ha_reevaluation_scenario_ids($settings['knownScenarioIds'] ?? null);
  $scenarioIds = array();
  $states = array();
  foreach ($scenarioRows as $raw) {
    if (!is_array($raw) || !isset($raw['id']) || !is_numeric($raw['id'])) {
      continue;
    }
    $id = (int) $raw['id'];
    $scenarioIds[$id] = $id;
    // Revue 24.18 (I1, option A) : l'activation de TOUS les scénarios entre dans la partie activation, publiés ou non :
    // l'écran des scénarios du plugin (statut `is_active`) et l'export (`active`) doivent suivre sans synchro complète.
    $states[$id] = (bool) ($raw['isActive'] ?? false);
  }
  ksort($scenarioIds);
  ksort($states);

  $structural = hash('sha256', (string) json_encode(array(
    'v' => 2,
    'eq' => array_values($equipments),
    'sc_ids' => array_values($scenarioIds),
    'excluded_plugins' => $excludedPlugins,
    'excluded_objects' => $excludedObjects,
    'scenario_publication' => array('published' => $published, 'known' => $known),
  )));
  $activationRows = array();
  $stateList = array();
  foreach ($states as $id => $active) {
    $activationRows[] = $id . ':' . ($active ? '1' : '0');
    $stateList[] = array('id' => $id, 'is_active' => $active);
  }
  $activation = hash('sha256', (string) json_encode(array('v' => 2, 'sc' => $activationRows)));
  return array(
    'structural' => $structural,
    'activation' => $activation,
    'states' => $stateList,
    'fingerprint' => 'v2:' . $structural . ':' . $activation,
  );
}

/**
 * Story 24.18 — lit une empreinte composite `v2:<structurelle>:<activation>` ; null si elle n'est pas à ce format
 * (vide, ancienne empreinte 24.14, valeur abîmée) : le chemin léger est alors impossible, synchro complète.
 *
 * @return array{structural:string,activation:string}|null
 */
function jeedom2ha_reevaluation_parse_fingerprint($fingerprint): ?array {
  if (!is_string($fingerprint) || !preg_match('/^v2:([0-9a-f]{64}):([0-9a-f]{64})$/', $fingerprint, $m)) {
    return null;
  }
  return array('structural' => $m[1], 'activation' => $m[2]);
}

/**
 * Story 24.18 — le chemin léger s'applique-t-il ? Oui seulement si l'empreinte mémorisée et la courante sont toutes deux
 * au format composite, avec la même partie structurelle et une activation différente. Tout autre cas : synchro complète.
 */
function jeedom2ha_reevaluation_light_candidate($stored, $current): bool {
  $s = jeedom2ha_reevaluation_parse_fingerprint($stored);
  $c = jeedom2ha_reevaluation_parse_fingerprint($current);
  return $s !== null && $c !== null
    && hash_equals($s['structural'], $c['structural'])
    && !hash_equals($s['activation'], $c['activation']);
}

/**
 * Story 24.18 — chemin léger d'un pas de la tâche périodique (seule l'activation de scénarios a changé).
 *
 * Retour : un résultat du pas (`light`, `deferred`, `failed`), ou null si le démon demande une synchro complète
 * (`full_sync_required`) : l'appelant la lance alors dans le même pas.
 */
function jeedom2ha_reevaluation_light_step(array $deps, string $stored, string $current, array $states): ?array {
  $log = $deps['log'];
  $log('info', '[REEVAL] Seule l\'activation de scénarios a changé : mise à jour légère');
  // Invalidée avant l'envoi : une réponse perdue laisse une empreinte vide, donc une synchro complète au pas suivant.
  jeedom2ha_reevaluation_invalidate_before_sync($deps['store']);
  try {
    $result = $deps['light']($states);
  } catch (\Throwable $e) {
    $log('warning', '[REEVAL] Mise à jour légère échouée, synchro complète au prochain pas : ' . $e->getMessage());
    return array('status' => 'failed', 'reason' => 'light_failed');
  }
  $code = is_array($result) ? ($result['code'] ?? null) : null;
  if ($code === 'action_in_progress') {
    // Le démon n'a rien fait, mais l'opération en cours peut être une relecture qui a elle-même invalidé l'empreinte :
    // ne rien remettre (revue 24.18), l'empreinte reste vide et le pas suivant fait une synchro complète, comme en 24.14.
    $log('info', '[REEVAL] Opération en cours dans le démon : synchro complète à la prochaine échéance');
    return array('status' => 'deferred', 'reason' => 'action_in_progress');
  }
  if ($code === 'full_sync_required') {
    $log('info', '[REEVAL] Le démon demande une synchro complète (' . (string) ($result['reason'] ?? 'inconnu') . ')');
    return null;
  }
  if (is_array($result) && ($result['status'] ?? null) === 'ok'
      && in_array($result['result'] ?? null, array('applied', 'unchanged'), true)) {
    $deps['store']($current);
    $log('info', '[REEVAL] Mise à jour légère terminée (scénarios : '
      . implode(',', array_map('intval', (array) ($result['scenario_ids'] ?? array()))) . ')');
    return array('status' => 'light', 'reason' => 'scenario_activation');
  }
  $message = is_array($result) ? (string) ($result['code'] ?? ($result['message'] ?? 'réponse inattendue')) : 'aucune réponse du démon';
  $log('warning', '[REEVAL] Mise à jour légère échouée (' . $message . ') : synchro complète au prochain pas');
  return array('status' => 'failed', 'reason' => 'light_failed');
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
 * Story 24.14 (revue P2, 5e passe) — empreinte à mémoriser après une synchro : celle lue AVANT l'extraction de la
 * topologie, seulement si une relecture APRÈS l'extraction donne la même valeur. Sinon l'état a changé pendant la
 * lecture et la topologie envoyée peut ne pas correspondre à l'empreinte : on ne mémorise rien (l'empreinte, déjà
 * invalidée avant l'envoi, reste vide) et le pas suivant resynchronise.
 */
function jeedom2ha_reevaluation_stable_fingerprint(?string $before, ?string $after): ?string {
  if ($before === null || $before === '' || $after === null || !hash_equals($before, $after)) {
    return null;
  }
  return $before;
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
 * - `fingerprint` () => string|array  empreinte courante (peut lever) ; Story 24.18 : ou
 *                                     `['fingerprint' => composite, 'states' => états de tous les scénarios]`
 * - `light`       (array) => ?array   facultatif (Story 24.18) : POST /action/scenario_activation ; absent = 24.14 strict
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
 * L'empreinte est lue AVANT la topologie et relue APRÈS : elle n'est mémorisée que si les deux lectures concordent.
 */
function jeedom2ha_reevaluation_tick(array $deps): array {
  $log = $deps['log'];
  // Story 24.18 — `fingerprint` peut rendre les parties (`fingerprint` + `states`) ou, comme en 24.14, une chaîne.
  $states = null;
  try {
    $read = $deps['fingerprint']();
    if (is_array($read)) {
      $states = isset($read['states']) && is_array($read['states']) ? $read['states'] : null;
      $read = $read['fingerprint'] ?? '';
    }
    $current = (string) $read;
  } catch (\Throwable $e) {
    $log('warning', '[REEVAL] Empreinte illisible, réévaluation reportée : ' . $e->getMessage());
    return array('status' => 'skipped', 'reason' => 'fingerprint_unreadable');
  }
  $stored = (string) $deps['stored']();
  if ($current !== '' && hash_equals($stored, $current)) {
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
  // Story 24.18 — seule l'activation de scénarios a changé : synchro légère (aucune topologie, aucun listener).
  if (isset($deps['light']) && $states !== null && count($states) <= JEEDOM2HA_REEVALUATION_LIGHT_MAX_SCENARIOS
      && jeedom2ha_reevaluation_light_candidate($stored, $current)) {
    $light = jeedom2ha_reevaluation_light_step($deps, $stored, $current, $states);
    if ($light !== null) {
      return $light;
    }
    // Le démon doute : synchro complète dans le même pas, comme avant 24.18.
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
  // Revue P2 (5e passe) — relecture après l'extraction : l'empreinte mémorisée doit être celle de la topologie envoyée.
  try {
    $after = $deps['fingerprint']();
    $after = (string) (is_array($after) ? ($after['fingerprint'] ?? '') : $after);
  } catch (\Throwable $e) {
    $after = null;
  }
  $stable = jeedom2ha_reevaluation_stable_fingerprint($current, $after);
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
  } elseif ($stable !== null) {
    $deps['store']($stable);
  } else {
    $log('info', '[REEVAL] État Jeedom modifié pendant la lecture : empreinte non mémorisée, nouvelle synchro à la prochaine échéance');
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
