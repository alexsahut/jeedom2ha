<?php
// ARTEFACT — Story 25.7 (AC6, Q1 A) : le nom du plugin vient de la PAGE. `eq_type` est un champ ADDITIF de `j2haRoomsTree`
// (aucun champ existant renommé ni retypé) et `j2haPluginNames` {identifiant: nom affiché} est construit une fois pour les
// seuls plugins présents, avec repli sur l'identifiant. Fonctions pures et rendu de la page avec un faux cœur Jeedom.
// Plugins fictifs (CC-48). Exécution : php tests/unit/test_story_25_7_php_plugin_names.php

require_once __DIR__ . '/../../desktop/php/jeedom2ha_overview_helpers.php';

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

echo "Identifiant de plugin : liste blanche de caractères, sinon vide\n";
check('identifiant simple conservé', j2ha_plugin_id('plugin_alpha') === 'plugin_alpha');
check('tiret conservé', j2ha_plugin_id('plugin-beta') === 'plugin-beta');
foreach (array('', null, 42, '<script>', 'a b', "x\ny", str_repeat('a', 65), '"quoted"') as $bad) {
    check('rejeté : ' . json_encode($bad), j2ha_plugin_id($bad) === '');
}

echo "Table des noms : plugins présents seulement, repli sur l'identifiant\n";
$names = array('plugin_alpha' => 'Alpha affiché', 'plugin_beta' => '');
$resolver = function ($id) use ($names) {
    if (!isset($names[$id])) {
        throw new Exception('plugin introuvable');
    }
    return $names[$id];
};
$table = j2ha_plugin_names(array('plugin_alpha', 'plugin_beta', 'plugin_gone', 'plugin_alpha', '', '<bad>'), $resolver);
check('nom affiché lu dans le cœur', $table['plugin_alpha'] === 'Alpha affiché');
check('nom vide : repli sur l\'identifiant', $table['plugin_beta'] === 'plugin_beta');
check('plugin désinstallé (exception) : repli sur l\'identifiant', $table['plugin_gone'] === 'plugin_gone');
check('une entrée par plugin présent, identifiants invalides écartés', array_keys($table) === array('plugin_alpha', 'plugin_beta', 'plugin_gone'));
check('table vide pour aucun type', j2ha_plugin_names(array(), $resolver) === array());
$weird = j2ha_plugin_names(array('plugin_alpha'), function ($id) { return array('pas', 'une chaîne'); });
check('résolveur non chaîne : repli', $weird['plugin_alpha'] === 'plugin_alpha');

echo "Rendu de la page : eq_type additif, table des noms, champs existants inchangés\n";
$fixture = array(
    'objects' => array(array('id' => 2, 'name' => 'Pièce fictive', 'father_id' => null, 'display' => array())),
    'eqlogics' => array(
        '2' => array(
            array('id' => 101, 'name' => 'Eq 101', 'type' => 'plugin_alpha'),
            array('id' => 102, 'name' => 'Eq 102', 'type' => 'plugin_gone', 'enabled' => false),
        ),
        'null' => array(array('id' => 111, 'name' => 'Eq sans objet', 'type' => 'plugin_alpha')),
    ),
    'plugin_names' => array('plugin_alpha' => 'Alpha <b>affiché</b>'),
    'doc' => 'https://doc.example.test/plugin',
);
$file = tempnam(sys_get_temp_dir(), 'j2ha');
file_put_contents($file, json_encode($fixture));
$out = json_decode(shell_exec('php ' . escapeshellarg(__DIR__ . '/helpers/render_page.php') . ' ' . escapeshellarg($file)), true);
unlink($file);
check('le rendu de la page réussit', is_array($out) && isset($out['vars']['j2haRoomsTree']));
$rooms = $out['vars']['j2haRoomsTree'];
$eq = $rooms[0]['equipments'][0];
check('eq_type ajouté à chaque équipement', $eq['eq_type'] === 'plugin_alpha' && $rooms[0]['equipments'][1]['eq_type'] === 'plugin_gone');
check('« Sans pièce » porte aussi eq_type', $rooms[1]['object_id'] === 0 && $rooms[1]['equipments'][0]['eq_type'] === 'plugin_alpha');
check('champs existants inchangés (noms et types)', array_keys($eq) === array('eq_id', 'eq_name', 'enabled', 'eq_type') && is_int($eq['eq_id']) && is_bool($eq['enabled']));
$expected = array('object_id', 'object_name', 'parent_number', 'father_id', 'icon_classes', 'color', 'equipments');
check('champs de pièce inchangés', array_keys($rooms[0]) === $expected);
$table = $out['vars']['j2haPluginNames'];
check('table des noms : seulement les plugins présents', array_keys($table) === array('plugin_alpha', 'plugin_gone'));
check('nom brut conservé (échappé côté JS par .text())', $table['plugin_alpha'] === 'Alpha <b>affiché</b>');
check('plugin absent du cœur : identifiant', $table['plugin_gone'] === 'plugin_gone');

echo "\n{$passed} réussis, {$failed} échoués\n";
exit($failed > 0 ? 1 : 0);
