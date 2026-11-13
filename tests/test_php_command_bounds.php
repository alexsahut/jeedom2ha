<?php
// ARTEFACT — correctif fix/daemon-sync-body-limit : les bornes vides d'une commande ne sont pas exportées
// (aucune clé min_value / max_value nulle sur chaque commande), une borne renseignée l'est telle quelle, et
// l'export de la classe passe bien par ce filtre. Données fictives uniquement (CC-48).
// Exécution : php tests/test_php_command_bounds.php

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

require_once $root . '/core/php/jeedom2ha_command_bounds.php';

$row = array('id' => 11, 'type' => 'info', 'min_value' => null, 'max_value' => null);
$out = jeedom2ha_drop_empty_bounds($row);
check('bornes nulles : clés retirées', !array_key_exists('min_value', $out) && !array_key_exists('max_value', $out));
check('autres clés conservées', $out['id'] === 11 && $out['type'] === 'info');

$out = jeedom2ha_drop_empty_bounds(array('id' => 12, 'min_value' => '', 'max_value' => '  '));
check('bornes vides ou blanches : clés retirées', !array_key_exists('min_value', $out) && !array_key_exists('max_value', $out));

$out = jeedom2ha_drop_empty_bounds(array('id' => 13, 'min_value' => array(1), 'max_value' => false));
check('bornes non scalaires ou booléennes : clés retirées', !array_key_exists('min_value', $out) && !array_key_exists('max_value', $out));

$out = jeedom2ha_drop_empty_bounds(array('id' => 14, 'min_value' => '7', 'max_value' => 30));
check('bornes renseignées : conservées telles quelles', $out['min_value'] === '7' && $out['max_value'] === 30);

$out = jeedom2ha_drop_empty_bounds(array('id' => 15, 'min_value' => '0', 'max_value' => null));
check('borne « 0 » conservée, borne nulle retirée', $out['min_value'] === '0' && !array_key_exists('max_value', $out));

$out = jeedom2ha_drop_empty_bounds(array('id' => 16));
check('sans clé de borne : ligne inchangée', $out === array('id' => 16));

$class = file_get_contents($root . '/core/class/jeedom2ha.class.php');
check('la classe charge le filtre', strpos($class, "/../php/jeedom2ha_command_bounds.php'") !== false);
check('l\'export des commandes applique le filtre', strpos($class, '$cmds[count($cmds) - 1] = jeedom2ha_drop_empty_bounds($cmds[count($cmds) - 1]);') !== false);

echo "\n{$passed} réussis, {$failed} échoués\n";
exit($failed === 0 ? 0 : 1);
