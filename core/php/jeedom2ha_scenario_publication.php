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
 * Front v3 (Lot 4a, option B d'Alexandre) — publication des scénarios au choix de l'utilisateur.
 *
 * Deux clés de configuration du plugin, listes JSON d'identifiants de scénarios :
 *  - `publishedScenarios` : scénarios que l'utilisateur a choisi de publier ;
 *  - `knownScenarioIds`   : scénarios déjà vus (un scénario absent de cette liste est « nouveau », marqué ✱).
 * Une clé ABSENTE (jamais écrite) garde le comportement d'avant le Lot 4a : le PHP n'envoie pas `published`
 * et le démon publie tous les scénarios lisibles.
 *
 * Migration (une seule fois, marqueur `scenarioPublicationSchema`) :
 *  - mise à jour (`jeedom2ha_update`) : tous les scénarios lisibles sont inscrits dans les deux listes, la
 *    projection vers Home Assistant reste identique ;
 *  - installation neuve (`jeedom2ha_install` sur une configuration vierge) : les deux listes sont vides, aucun
 *    scénario n'est publié tant que l'utilisateur ne l'a pas choisi ;
 *  - `jeedom2ha_install` sur une installation qui a déjà servi (réactivation du plugin, mise à jour faite plugin
 *    désactivé) : traitée comme une mise à jour, rien ne disparaît de HA.
 *
 * Fonctions PURES : aucune dépendance au cœur Jeedom ; la configuration, la lecture des scénarios et le journal
 * sont injectés par l'appelant (plugin_info/install.php, core/ajax/jeedom2ha.ajax.php, core/class/jeedom2ha.class.php)
 * et par les tests CI (tests/test_php_front_v3_lot4a_scenarios.php).
 */

const JEEDOM2HA_PUBLISHED_SCENARIOS_KEY = 'publishedScenarios';
const JEEDOM2HA_KNOWN_SCENARIOS_KEY = 'knownScenarioIds';
const JEEDOM2HA_SCENARIO_PUBLICATION_SCHEMA_KEY = 'scenarioPublicationSchema';
const JEEDOM2HA_SCENARIO_PUBLICATION_SCHEMA = '1';
const JEEDOM2HA_SCENARIO_PUBLICATION_MAX_IDS = 5000;

/* Clés que le cœur Jeedom écrit lui-même pour tout plugin avant l'appel de `<plugin>_install` (activation, démon,
 * dépendances) : leur présence ne prouve pas qu'une installation a déjà servi. */
const JEEDOM2HA_CORE_MANAGED_CONFIG_KEYS = array(
  'active', 'deamonAutoMode', 'dependancyAutoMode', 'deamonRestartNumber', 'lastDeamonLaunchTime',
  'lastDependancyInstallTime',
);

/**
 * Liste d'identifiants lue dans une valeur de configuration. `null` si la clé est absente ou illisible
 * (config::byKey rend '' pour une clé jamais écrite, un tableau pour une liste JSON).
 *
 * @return int[]|null identifiants entiers strictement positifs, uniques, triés
 */
function jeedom2ha_scenario_id_list($raw) {
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
 * Valeur à écrire dans la configuration : liste JSON (jamais vide en chaîne : '[]' reste une clé présente).
 */
function jeedom2ha_scenario_id_list_value(array $ids) {
  $ids = jeedom2ha_scenario_id_list($ids);
  return json_encode($ids === null ? array() : $ids);
}

/**
 * Paramètre strict de la route `saveScenarioPublication` : liste JSON d'entiers positifs, ex. `[12,15]` ou `[]`.
 * `null` si mal formé, en double ou trop long.
 *
 * @return int[]|null
 */
function jeedom2ha_parse_scenario_id_param($raw) {
  if (!is_string($raw) || !preg_match('/^\[(?:[1-9][0-9]{0,9}(?:,[1-9][0-9]{0,9})*)?\]$/', $raw)) {
    return null;
  }
  $values = json_decode($raw, true);
  if (!is_array($values) || count($values) > JEEDOM2HA_SCENARIO_PUBLICATION_MAX_IDS) {
    return null;
  }
  $ids = array_map('intval', $values);
  if (count(array_unique($ids)) !== count($ids)) {
    return null;
  }
  sort($ids);
  return $ids;
}

/**
 * Comment le scénario se lance, d'après `getMode()`, `getTrigger()` et `getSchedule()` (lecture seule).
 * Un déclencheur ne compte qu'en mode `provoke` ou `all`, une programmation qu'en mode `schedule` ou `all`.
 * `manual` : ni déclencheur ni programmation effectifs (lancé à la main). Valeurs `null` si illisibles.
 *
 * @return array{mode: ?string, has_trigger: ?bool, has_schedule: ?bool, manual: ?bool}
 */
function jeedom2ha_scenario_launch_info($mode, $triggers, $schedule) {
  $mode = in_array($mode, array('provoke', 'schedule', 'all'), true) ? $mode : null;
  if ($mode === null) {
    return array('mode' => null, 'has_trigger' => null, 'has_schedule' => null, 'manual' => null);
  }
  $hasTrigger = in_array($mode, array('provoke', 'all'), true) && jeedom2ha_scenario_has_entry($triggers);
  $hasSchedule = in_array($mode, array('schedule', 'all'), true) && jeedom2ha_scenario_has_entry($schedule);
  return array(
    'mode' => $mode,
    'has_trigger' => $hasTrigger,
    'has_schedule' => $hasSchedule,
    'manual' => !$hasTrigger && !$hasSchedule,
  );
}

/** Vrai si la valeur (chaîne ou liste de chaînes) contient au moins une entrée non vide. */
function jeedom2ha_scenario_has_entry($value) {
  if (is_array($value)) {
    foreach ($value as $entry) {
      if (jeedom2ha_scenario_has_entry($entry)) {
        return true;
      }
    }
    return false;
  }
  return is_scalar($value) && trim((string) $value) !== '';
}

/**
 * Champs `published` et `is_new` d'un scénario pour la topologie. Tableau vide si la publication n'est pas configurée
 * (clé `publishedScenarios` absente) : le démon publie alors comme avant.
 */
function jeedom2ha_scenario_publication_fields($scenarioId, $published, $known) {
  if (!is_array($published)) {
    return array();
  }
  return array(
    'published' => in_array((int) $scenarioId, $published, true),
    'is_new' => !in_array((int) $scenarioId, is_array($known) ? $known : $published, true),
  );
}

/**
 * Ajoute `published` et `is_new` aux lignes de scénarios de la topologie (buildScenariosPayload). Lignes inchangées
 * si la publication n'est pas configurée.
 */
function jeedom2ha_scenario_publication_rows(array $rows, $published, $known) {
  foreach ($rows as $index => $row) {
    if (is_array($row) && isset($row['id'])) {
      $rows[$index] = array_merge($row, jeedom2ha_scenario_publication_fields($row['id'], $published, $known));
    }
  }
  return $rows;
}

/**
 * Installation neuve : aucune clé de configuration du plugin hors celles que le cœur écrit lui-même, et aucun fichier
 * dans le dossier data/ du plugin (cache de publication, export de décision : ils survivent aux mises à jour).
 * Dans le doute, l'installation est réputée avoir servi (tous les scénarios restent publiés).
 */
function jeedom2ha_scenario_publication_is_fresh_install($configKeys, $dataFiles) {
  if (!is_array($configKeys) || !is_array($dataFiles)) {
    return false;
  }
  foreach ($configKeys as $key) {
    if (!in_array((string) $key, JEEDOM2HA_CORE_MANAGED_CONFIG_KEYS, true)) {
      return false;
    }
  }
  foreach ($dataFiles as $file) {
    if ($file !== '.' && $file !== '..') {
      return false;
    }
  }
  return true;
}

/**
 * Migration idempotente des deux clés (voir l'en-tête). `$context` : 'install' ou 'update'.
 *
 * $deps : read(key) → valeur brute de config::byKey ; save(key, string) ; readableIds() → int[] ou null si la lecture
 * des scénarios est incomplète ; isFresh() → bool (appelé seulement pour 'install') ; log(level, message).
 * Une lecture incomplète n'écrit rien (statut `deferred`) : le comportement d'avant reste en place et la migration
 * sera retentée (mise à jour suivante ou premier enregistrement d'un choix).
 *
 * @return array{status: string, published: ?int[], known: ?int[]}
 */
function jeedom2ha_scenario_publication_migrate($context, array $deps) {
  $log = isset($deps['log']) ? $deps['log'] : function ($level, $message) {};
  $published = jeedom2ha_scenario_id_list($deps['read'](JEEDOM2HA_PUBLISHED_SCENARIOS_KEY));
  $known = jeedom2ha_scenario_id_list($deps['read'](JEEDOM2HA_KNOWN_SCENARIOS_KEY));
  $marker = (string) $deps['read'](JEEDOM2HA_SCENARIO_PUBLICATION_SCHEMA_KEY);
  if ($marker === JEEDOM2HA_SCENARIO_PUBLICATION_SCHEMA && $published !== null) {
    return array('status' => 'done', 'published' => $published, 'known' => $known === null ? $published : $known);
  }
  if ($published !== null) {
    $status = 'kept';
    if ($known === null) {
      $known = $published;
      $deps['save'](JEEDOM2HA_KNOWN_SCENARIOS_KEY, jeedom2ha_scenario_id_list_value($known));
    }
  } elseif ($context === 'install' && $deps['isFresh']()) {
    $status = 'fresh';
    $published = array();
    $known = array();
    $deps['save'](JEEDOM2HA_PUBLISHED_SCENARIOS_KEY, jeedom2ha_scenario_id_list_value($published));
    $deps['save'](JEEDOM2HA_KNOWN_SCENARIOS_KEY, jeedom2ha_scenario_id_list_value($known));
  } else {
    $ids = $deps['readableIds']();
    if (!is_array($ids)) {
      $log('warning', '[SCENARIO] Migration de la publication des scénarios reportée : lecture des scénarios incomplète');
      return array('status' => 'deferred', 'published' => null, 'known' => null);
    }
    $status = 'migrated';
    $published = jeedom2ha_scenario_id_list($ids);
    $known = $published;
    $deps['save'](JEEDOM2HA_PUBLISHED_SCENARIOS_KEY, jeedom2ha_scenario_id_list_value($published));
    $deps['save'](JEEDOM2HA_KNOWN_SCENARIOS_KEY, jeedom2ha_scenario_id_list_value($known));
  }
  $deps['save'](JEEDOM2HA_SCENARIO_PUBLICATION_SCHEMA_KEY, JEEDOM2HA_SCENARIO_PUBLICATION_SCHEMA);
  $log('info', '[SCENARIO] Publication des scénarios (' . $context . ') : ' . $status . ', '
    . count($published) . ' publié(s), ' . count($known) . ' connu(s)');
  return array('status' => $status, 'published' => $published, 'known' => $known);
}

/**
 * Applique un choix : publier `$toPublish`, ne plus publier `$toUnpublish` ; les deux deviennent « connus ».
 *
 * @return array{published: int[], known: int[]}
 */
function jeedom2ha_scenario_publication_apply(array $published, array $known, array $toPublish, array $toUnpublish) {
  $published = array_diff(array_merge($published, $toPublish), $toUnpublish);
  $known = array_merge($known, $toPublish, $toUnpublish);
  return array(
    'published' => jeedom2ha_scenario_id_list(array_values($published)),
    'known' => jeedom2ha_scenario_id_list(array_values($known)),
  );
}

/**
 * Route `saveScenarioPublication` sans le cœur : valide, migre si besoin, écrit les deux clés.
 * Une erreur de validation lève une exception (message court, en français) et n'écrit rien.
 *
 * $deps : celles de jeedom2ha_scenario_publication_migrate (contexte 'update' : jamais « installation neuve ») ;
 * readableIds() sert aussi à refuser la publication d'un scénario qui n'existe pas.
 *
 * @return array{ids_to_publish: int[], ids_to_unpublish: int[], published: int[], known: int[]}
 */
function jeedom2ha_save_scenario_publication($rawToPublish, $rawToUnpublish, array $deps) {
  $toPublish = jeedom2ha_parse_scenario_id_param($rawToPublish);
  $toUnpublish = jeedom2ha_parse_scenario_id_param($rawToUnpublish);
  if ($toPublish === null || $toUnpublish === null) {
    throw new Exception('Liste de scénarios invalide');
  }
  if (count($toPublish) + count($toUnpublish) === 0) {
    throw new Exception('Aucun scénario à modifier');
  }
  if (count(array_intersect($toPublish, $toUnpublish)) > 0) {
    throw new Exception('Un scénario ne peut pas être publié et retiré à la fois');
  }
  if (count($toPublish) > 0) {
    $readable = $deps['readableIds']();
    if (!is_array($readable) || count(array_diff($toPublish, $readable)) > 0) {
      throw new Exception('Scénario introuvable');
    }
  }
  $migration = jeedom2ha_scenario_publication_migrate('update', $deps);
  if ($migration['published'] === null) {
    throw new Exception('Lecture des scénarios incomplète, réessayez');
  }
  $known = $migration['known'] === null ? $migration['published'] : $migration['known'];
  $next = jeedom2ha_scenario_publication_apply($migration['published'], $known, $toPublish, $toUnpublish);
  $deps['save'](JEEDOM2HA_PUBLISHED_SCENARIOS_KEY, jeedom2ha_scenario_id_list_value($next['published']));
  $deps['save'](JEEDOM2HA_KNOWN_SCENARIOS_KEY, jeedom2ha_scenario_id_list_value($next['known']));
  if (isset($deps['log'])) {
    $deps['log']('info', '[SCENARIO] Publication des scénarios modifiée : publier ' . json_encode($toPublish)
      . ', retirer ' . json_encode($toUnpublish));
  }
  return array(
    'ids_to_publish' => $toPublish,
    'ids_to_unpublish' => $toUnpublish,
    'published' => $next['published'],
    'known' => $next['known'],
  );
}
