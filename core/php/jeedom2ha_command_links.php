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
 * fix/switch-appariement-etat — info reliée à une commande action (lecture seule).
 *
 * Champs réellement présents dans Jeedom (vérifiés dans le code du cœur et du plugin virtual) :
 * - cœur, `cmd::execCmd()`, toute commande action : configuration `updateCmdId` (id de l'info mise
 *   à jour après l'exécution ; écran du virtuel : « Commande information à mettre à jour ») ;
 * - plugin virtual, `virtualCmd::execute()` : configuration `infoId` (id de l'info virtuelle écrite).
 *   Lue pour le seul plugin virtual.
 * story/select-mode — la valeur écrite (`updateCmdToValue` du cœur, `value` du virtual, seulement si le
 * lien correspondant est renseigné) et la liste d'une action « select » (`listValue` du cœur,
 * `valeur|libellé;…`) sont aussi exportées : options d'un select Home Assistant.
 *
 * Rend uniquement les clés renseignées (aucune clé vide sur chaque commande : la topologie est
 * envoyée en entier à chaque synchro). Une info commande n'a jamais ces clés.
 * Fonction pure, sans dépendance au cœur Jeedom : `$_config` lit une clé de configuration.
 */
function jeedom2ha_action_links(string $_type, string $_eqType, callable $_config): array {
  if ($_type !== 'action') {
    return array();
  }
  $keys = array('update_cmd_id' => 'updateCmdId');
  if ($_eqType === 'virtual') {
    $keys['virtual_info_id'] = 'infoId';
  }
  $out = array();
  foreach ($keys as $field => $configKey) {
    $raw = $_config($configKey);
    if ($raw === null || !is_scalar($raw) || is_bool($raw) || trim(strval($raw)) === '') {
      continue;
    }
    $out[$field] = strval($raw);
  }
  // story/select-mode — valeurs écrites (avec leur lien seulement) et liste d'une action « select ».
  $values = array('list_value' => 'listValue');
  if (isset($out['update_cmd_id'])) {
    $values['update_cmd_to_value'] = 'updateCmdToValue';
  }
  if (isset($out['virtual_info_id'])) {
    $values['virtual_value'] = 'value';
  }
  foreach ($values as $field => $configKey) {
    $raw = $_config($configKey);
    if ($raw === null || !is_scalar($raw) || is_bool($raw) || strval($raw) === '') {
      continue;
    }
    $out[$field] = strval($raw);
  }
  return $out;
}
