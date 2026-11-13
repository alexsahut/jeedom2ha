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

/**
 * Correctif fix/daemon-sync-body-limit — bornes d'une commande exportée (Story 24.15, D3).
 *
 * Retire `min_value` / `max_value` d'une ligne de commande de la topologie quand la borne est
 * absente : null, chaîne vide ou valeur non scalaire. La topologie est envoyée en entier à
 * chaque synchro : deux clés nulles sur chaque commande l'alourdissent sans rien apporter.
 * Le démon lit une clé absente comme « pas de borne » (models/topology.py).
 * Fonction pure, sans dépendance au cœur Jeedom.
 */
function jeedom2ha_drop_empty_bounds(array $row): array {
  foreach (array('min_value', 'max_value') as $key) {
    if (!array_key_exists($key, $row)) {
      continue;
    }
    $value = $row[$key];
    if ($value === null || !is_scalar($value) || is_bool($value) || trim(strval($value)) === '') {
      unset($row[$key]);
    }
  }
  return $row;
}
