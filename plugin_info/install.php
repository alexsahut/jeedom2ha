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

require_once dirname(__FILE__) . '/../../../core/php/core.inc.php';
require_once dirname(__FILE__) . '/../core/php/jeedom2ha_scenario_publication.php'; // front v3 (Lot 4a)

/**
 * Front v3 (Lot 4a, option B) — migration de la publication des scénarios, une seule fois (marqueur
 * `scenarioPublicationSchema`). Jeedom appelle `jeedom2ha_install` à la première activation du plugin (et à chaque
 * réactivation après une désactivation) et `jeedom2ha_update` à la mise à jour d'un plugin actif : seule une
 * configuration vierge (aucune clé du plugin hors celles du cœur, dossier data/ vide) est traitée en installation
 * neuve ; tout autre cas inscrit tous les scénarios lisibles, la projection vers HA reste identique.
 * Ne lève jamais : un échec laisse les clés absentes, donc le comportement d'avant (tous publiés).
 */
function jeedom2ha_migrate_scenario_publication($context, $dataDirFilesBefore) {
    try {
        // Dépendances construites ici, sans la classe du plugin : pendant une mise à jour, l'ancienne version de la
        // classe peut être déjà chargée dans le processus.
        jeedom2ha_scenario_publication_migrate($context, array(
            'read' => function ($key) {
                return config::byKey($key, 'jeedom2ha', '', true);
            },
            'save' => function ($key, $value) {
                config::save($key, $value, 'jeedom2ha');
            },
            'readableIds' => function () {
                if (!class_exists('scenario')) {
                    return null;
                }
                $ids = array();
                foreach (scenario::all() as $scenario) {
                    try {
                        $ids[] = intval($scenario->getId());
                    } catch (\Throwable $e) {
                        return null; // lecture incomplète : migration reportée, rien n'est retiré
                    }
                }
                return $ids;
            },
            'isFresh' => function () use ($dataDirFilesBefore) {
                $rows = DB::Prepare('SELECT `key` FROM `config` WHERE `plugin` = :plugin', array('plugin' => 'jeedom2ha'), DB::FETCH_TYPE_ALL);
                $keys = array();
                foreach (is_array($rows) ? $rows : array() as $row) {
                    $keys[] = isset($row['key']) ? $row['key'] : '';
                }
                return jeedom2ha_scenario_publication_is_fresh_install($keys, $dataDirFilesBefore);
            },
            'log' => function ($level, $message) {
                log::add('jeedom2ha', $level, $message);
            },
        ));
    } catch (\Throwable $e) {
        log::add('jeedom2ha', 'warning', '[SCENARIO] Migration de la publication des scénarios non faite : ' . $e->getMessage());
    }
}

/** Fichiers du dossier data/ avant toute création (null si illisible : l'installation est alors réputée avoir servi). */
function jeedom2ha_data_dir_files($dataDir) {
    if (!is_dir($dataDir)) {
        return array();
    }
    $files = scandir($dataDir);
    return is_array($files) ? $files : null;
}

// Fonction exécutée automatiquement après l'installation du plugin
function jeedom2ha_install() {
    $dataDir = __DIR__ . '/../data';
    $dataDirFilesBefore = jeedom2ha_data_dir_files($dataDir); // front v3 (Lot 4a) : lu avant la création de data/
    if (!is_dir($dataDir)) {
        if (!mkdir($dataDir, 0775, true)) {
            log::add('jeedom2ha', 'error', 'Impossible de créer le répertoire data/ : ' . $dataDir);
        } else {
            log::add('jeedom2ha', 'info', 'Répertoire data/ créé automatiquement : ' . $dataDir);
        }
    }
    jeedom2ha_migrate_scenario_publication('install', $dataDirFilesBefore);
}

// Fonction exécutée automatiquement après la mise à jour du plugin
function jeedom2ha_update() {
    $dataDir = __DIR__ . '/../data';
    $dataDirFilesBefore = jeedom2ha_data_dir_files($dataDir); // front v3 (Lot 4a)
    if (!is_dir($dataDir)) {
        if (!mkdir($dataDir, 0775, true)) {
            log::add('jeedom2ha', 'error', 'Impossible de créer le répertoire data/ : ' . $dataDir);
        } else {
            log::add('jeedom2ha', 'info', 'Répertoire data/ créé automatiquement : ' . $dataDir);
        }
    }
    jeedom2ha_migrate_scenario_publication('update', $dataDirFilesBefore);
}

// Fonction exécutée automatiquement après la suppression du plugin
function jeedom2ha_remove() {
}
