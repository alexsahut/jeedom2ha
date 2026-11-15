<?php
// ARTEFACT — fix/switch-appariement-etat : l'info mise à jour par une action est exportée en ajout seulement
// (updateCmdId du cœur, infoId du plugin virtual), sans clé vide, jamais pour une info, jamais la valeur écrite,
// et `infoId` n'est lu que pour le plugin virtual. Données fictives uniquement (CC-48).
// Exécution : php tests/test_php_command_links.php

$root = dirname(__DIR__);
$passed = 0;
$failed = 0;

function check($label, $condition) {
    global $passed, $failed;
    if ($condition) {
        $passed++;
        echo "  ✔ {$label}\n";
        return;
    }
    $failed++;
    echo "  ✖ {$label}\n";
}

require_once $root . '/core/php/jeedom2ha_command_links.php';

function config_of(array $values) {
    return function (string $key) use ($values) {
        return array_key_exists($key, $values) ? $values[$key] : null;
    };
}

// Action du cœur qui met une info à jour après exécution (« On » d'un relais suivi d'un état virtuel).
$out = jeedom2ha_action_links('action', 'virtual', config_of(array('updateCmdId' => '108', 'updateCmdToValue' => '1')));
check('cœur : updateCmdId et, avec lui, updateCmdToValue (story/select-mode)', $out === array('update_cmd_id' => '108', 'update_cmd_to_value' => '1'));

$out = jeedom2ha_action_links('action', 'zwavejs', config_of(array('updateCmdId' => '#108#', 'updateCmdToValue' => '0')));
check('cœur : tout plugin, lien tel quel, valeur « 0 » gardée', $out === array('update_cmd_id' => '#108#', 'update_cmd_to_value' => '0'));

// Action virtuelle qui écrit une constante dans une info virtuelle.
$out = jeedom2ha_action_links('action', 'virtual', config_of(array('infoId' => '207', 'value' => 'Absence')));
check('virtual : infoId et value exportés, casse gardée', $out === array('virtual_info_id' => '207', 'virtual_value' => 'Absence'));

$out = jeedom2ha_action_links('action', 'zwavejs', config_of(array('infoId' => '207', 'value' => 'x')));
check('hors virtual : infoId / value jamais lus', $out === array());

$out = jeedom2ha_action_links('action', 'virtual', config_of(array('updateCmdId' => '', 'infoId' => '  ', 'value' => 'manu', 'updateCmdToValue' => '1')));
check('lien vide : aucune clé, valeur orpheline non exportée', $out === array());

$out = jeedom2ha_action_links('action', 'virtual', config_of(array('updateCmdId' => array(1), 'infoId' => true)));
check('lien non scalaire ou booléen : aucune clé', $out === array());

$out = jeedom2ha_action_links('info', 'virtual', config_of(array('updateCmdId' => '108', 'infoId' => '207', 'value' => 'a')));
check('commande info : aucune clé', $out === array());

// story/select-mode — liste d'une action « select », tout plugin.
$out = jeedom2ha_action_links('action', 'zwavejs', config_of(array('listValue' => 'eco|Éco;confort|Confort')));
check('listValue exporté tel quel', $out === array('list_value' => 'eco|Éco;confort|Confort'));

$out = jeedom2ha_action_links('info', 'zwavejs', config_of(array('listValue' => 'a|A;b|B')));
check('listValue jamais pour une info', $out === array());

$class = file_get_contents($root . '/core/class/jeedom2ha.class.php');
check('la classe charge le module', strpos($class, "/../php/jeedom2ha_command_links.php'") !== false);
check('l\'export des commandes ajoute les liens', strpos($class, '$cmds[count($cmds) - 1] += jeedom2ha_action_links(') !== false);

echo "\n{$passed} réussis, {$failed} échoués\n";
exit($failed === 0 ? 0 : 1);
