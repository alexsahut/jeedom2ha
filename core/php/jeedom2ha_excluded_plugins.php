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
 * Story 25.9 — page de configuration : « Plugins exclus » en liste à cocher des plugins présents.
 *
 * Fonctions PURES (aucune dépendance au cœur Jeedom, compatibles PHP 7.4), chargées par plugin_info/configuration.php, par
 * core/ajax/jeedom2ha.ajax.php et directement par les tests CI (tests/test_php_story_25_9_configuration.php). La clé reste
 * `excludedPlugins`, au même format (CSV d'identifiants techniques `eq_type_name`) ; la règle de lecture est celle de l'extraction de
 * la topologie (core/class/jeedom2ha.class.php) : ce que la page montre coché est exactement ce que le plugin exclut.
 */

require_once __DIR__ . '/jeedom2ha_room_exclusion.php';

/**
 * Identifiants de plugins exclus lus dans la chaîne CSV, par la règle de l'extraction (`trim`, `array_unique`, `array_filter`).
 *
 * @return string[]
 */
function jeedom2ha_excluded_plugin_ids($csv) {
  return array_values(array_filter(array_unique(array_map('trim', explode(',', (string) $csv)))));
}

/** Texte replié pour le tri : minuscules, sans accents (table explicite, aucune dépendance à l'extension intl). */
function jeedom2ha_fold_text($text) {
  $text = (string) $text;
  $lower = function_exists('mb_strtolower') ? mb_strtolower($text, 'UTF-8') : strtolower($text);
  static $map = array(
    'à' => 'a', 'á' => 'a', 'â' => 'a', 'ã' => 'a', 'ä' => 'a', 'å' => 'a', 'æ' => 'ae', 'ç' => 'c',
    'è' => 'e', 'é' => 'e', 'ê' => 'e', 'ë' => 'e', 'ì' => 'i', 'í' => 'i', 'î' => 'i', 'ï' => 'i',
    'ñ' => 'n', 'ò' => 'o', 'ó' => 'o', 'ô' => 'o', 'õ' => 'o', 'ö' => 'o', 'ø' => 'o', 'œ' => 'oe',
    'ù' => 'u', 'ú' => 'u', 'û' => 'u', 'ü' => 'u', 'ý' => 'y', 'ÿ' => 'y', 'ß' => 'ss',
  );
  return strtr($lower, $map);
}

/**
 * Liste D1 de la page de configuration : les plugins PRÉSENTS (`$names` : { identifiant: nom affiché }, déjà débarrassée de
 * `jeedom2ha`), triés par nom affiché sans tenir compte de la casse ni des accents, cochés s'ils figurent dans `excludedPlugins` ;
 * puis, cochés, les identifiants exclus mais ABSENTS de Jeedom (rien n'est perdu à l'enregistrement). `jeedom2ha` n'apparaît jamais.
 *
 * @return array[] liste de { id: string, name: string, checked: bool, absent: bool }
 */
function jeedom2ha_build_excluded_plugins_list(array $names, $excludedCsv) {
  $excluded = jeedom2ha_excluded_plugin_ids($excludedCsv);
  $items = array();
  foreach ($names as $id => $name) {
    $id = (string) $id;
    if ($id === '' || $id === 'jeedom2ha') {
      continue;
    }
    $items[] = array(
      'id' => $id,
      'name' => trim((string) $name) !== '' ? trim((string) $name) : $id,
      'checked' => in_array($id, $excluded, true),
      'absent' => false,
    );
  }
  usort($items, function ($a, $b) {
    $cmp = strcmp(jeedom2ha_fold_text($a['name']), jeedom2ha_fold_text($b['name']));
    return $cmp !== 0 ? $cmp : strcmp($a['id'], $b['id']);
  });
  $known = array();
  foreach ($items as $item) {
    $known[$item['id']] = true;
  }
  foreach ($excluded as $id) {
    if ($id === 'jeedom2ha' || isset($known[$id])) {
      continue;
    }
    $known[$id] = true;
    $items[] = array('id' => $id, 'name' => $id, 'checked' => true, 'absent' => true);
  }
  return $items;
}

function jeedom2ha_html_attr($text) {
  return htmlspecialchars((string) $text, ENT_QUOTES, 'UTF-8');
}

/**
 * Rendu du groupe de cases à cocher (D1, AC1, AC4) : vraie `input type="checkbox"` avec `label` associé par plugin, groupe nommé
 * par le libellé « Plugins exclus », hauteur bornée avec défilement vertical seulement (Q5). Les noms viennent de Jeedom et sont
 * échappés. Les cases ne portent PAS `configKey` : seul le champ masqué porteur est lu par « Sauvegarder » du cœur.
 */
function jeedom2ha_render_excluded_plugins_checklist(array $list) {
  $html = '<div id="div_excludedPluginsList" class="j2ha-plugin-checklist" role="group" aria-labelledby="lbl_excludedPlugins"'
    . ' style="max-height:18em;overflow-y:auto;overflow-x:hidden;">';
  if (count($list) === 0) {
    $html .= '<p class="text-muted j2ha-plugin-empty">{{Aucun plugin avec des équipements.}}</p>';
  }
  $index = 0;
  foreach ($list as $item) {
    $index++;
    $inputId = 'cb_excludedPlugin_' . $index;
    $html .= '<div class="checkbox"><label for="' . $inputId . '">'
      . '<input type="checkbox" id="' . $inputId . '" class="j2ha-excluded-plugin" value="' . jeedom2ha_html_attr($item['id']) . '"'
      . ' data-initial="' . ($item['checked'] ? '1' : '0') . '"' . ($item['checked'] ? ' checked' : '') . '> '
      . '<span>' . jeedom2ha_html_attr($item['name']) . '</span> '
      . '<small class="text-muted">(' . jeedom2ha_html_attr($item['id']) . ')</small>'
      . ($item['absent'] ? ' <em class="text-muted">{{(absent de Jeedom)}}</em>' : '')
      . '</label></div>';
  }
  $html .= '</div>';
  $html .= '<span class="help-block">{{Les équipements des plugins cochés ne sont pas publiés dans Home Assistant.}}</span>';
  return $html;
}

/**
 * Nombre de pièces exclues (renvoi de la page de configuration vers la surface) : lu dans la clé des pièces exclues par la règle de
 * l'extraction. Aucune écriture : la surface (route `saveRoomExclusion`) est la seule à écrire cette clé.
 */
function jeedom2ha_excluded_rooms_count() {
  return count(jeedom2ha_excluded_object_ids(config::byKey('excludedObjects', 'jeedom2ha', '')));
}

/**
 * Logique de la route `saveFilteringConfig` : écrit `excludedPlugins` et `confidencePolicy`, JAMAIS la clé des pièces exclues (ni
 * écrite ni effacée, même si une ancienne page restée ouverte l'envoie : la valeur existante est conservée telle quelle).
 *
 * @param array    $request params reçus (seules les clés excludedPlugins et confidencePolicy sont lues)
 * @param callable $save    function (string $key, string $value): void
 * @param callable $log     function (string $level, string $message): void
 */
function jeedom2ha_save_filtering_config(array $request, callable $save, callable $log) {
  $excludedPlugins = isset($request['excludedPlugins']) ? (string) $request['excludedPlugins'] : '';
  $confidencePolicy = isset($request['confidencePolicy']) ? (string) $request['confidencePolicy'] : 'sure_probable';
  // Validation : valeurs autorisées uniquement
  if (!in_array($confidencePolicy, array('sure_only', 'sure_probable'), true)) {
    $confidencePolicy = 'sure_probable';
  }
  $save('excludedPlugins', $excludedPlugins);
  $save('confidencePolicy', $confidencePolicy);
  $log('info', '[CONFIG] saveFilteringConfig: excludedPlugins="' . $excludedPlugins . '" confidencePolicy="' . $confidencePolicy . '"');
}
