<?php
// Story 24.1 — signal d'exposition HomeKit : règle pure (lecture seule), sans cœur Jeedom.
// Exécution : php tests/unit/test_story_24_1_php_homekit_exposure.php
// Identifiants numériques/génériques uniquement (CC-48).

require_once __DIR__ . '/../../core/php/jeedom2ha_homekit_exposure.php';

$passed = 0;
$failed = 0;

function check($label, $expected, $actual) {
    global $passed, $failed;
    if ($expected === $actual) {
        $passed++;
        echo "  PASS: {$label}\n";
    } else {
        $failed++;
        echo "  FAIL: {$label}\n    expected: " . json_encode($expected) . "\n    actual:   " . json_encode($actual) . "\n";
    }
}

// Contexte nominal : Homebridge présent, plugins actifs, pièce 10 à 1, pièce 11 à 0, pièce 12 sans clé.
function ctx(array $over = array()) {
    return array_merge(array(
        'homebridge'     => 'present',
        'default'        => null,
        'active_plugins' => array('virtual' => true, 'zwave' => true, 'mobile' => true, 'homebridge' => true),
        'rooms'          => array(10 => 1, 11 => 0, 12 => null, 13 => '1', 14 => JEEDOM2HA_HOMEKIT_UNREADABLE, 15 => 'x'),
    ), $over);
}

function expo($type, $obj, $eq, $ctx) {
    $r = jeedom2ha_homekit_eq_exposure($type, $obj, $eq, $ctx);
    return array($r['exposed'], $r['source']);
}

echo "Équipement exposé / règle à trois niveaux\n";
check('équipement exposé (pièce 1, équipement 1)', array(true, 'equipement'), expo('virtual', 10, 1, ctx()));
check('valeurs en chaîne "1"', array(true, 'equipement'), expo('virtual', 13, '1', ctx()));
check('pièce à 0 → false, provenance piece', array(false, 'piece'), expo('virtual', 11, 1, ctx()));
check('équipement à 0 → false, provenance equipement', array(false, 'equipement'), expo('virtual', 10, 0, ctx()));
check('clé absente, défaut Homebridge absent (=1) → true', array(true, 'defaut_homebridge'), expo('virtual', 10, null, ctx()));
check('clé absente, défaut Homebridge 1 → true', array(true, 'defaut_homebridge'), expo('virtual', 10, null, ctx(array('default' => '1'))));
check('clé absente, défaut Homebridge 0 → false', array(false, 'defaut_homebridge'), expo('virtual', 10, null, ctx(array('default' => 0))));
check('clé vide (chaîne) = absente', array(true, 'defaut_homebridge'), expo('virtual', 10, '', ctx()));
check('défaut Homebridge illisible → null', array(null, 'illisible'), expo('virtual', 10, null, ctx(array('default' => JEEDOM2HA_HOMEKIT_UNREADABLE))));

echo "Task 0 bis — pièce absente et pièce sans clé\n";
check('équipement sans pièce (null) → false, provenance piece', array(false, 'piece'), expo('virtual', null, 1, ctx()));
check('équipement sans pièce (-1) → false, provenance piece', array(false, 'piece'), expo('virtual', -1, 1, ctx()));
check('pièce inexistante → false, provenance piece', array(false, 'piece'), expo('virtual', 99, 1, ctx()));
check('pièce sans clé sendToHomebridge (= 0) → false, provenance piece', array(false, 'piece'), expo('virtual', 12, 1, ctx()));

echo "Plugins\n";
check('plugin mobile → false, plugin_excluded', array(false, 'plugin_excluded'), expo('mobile', 10, 1, ctx()));
check('plugin homebridge → false, plugin_excluded', array(false, 'plugin_excluded'), expo('homebridge', 10, 1, ctx()));
check('plugin inactif (absent de la liste active) → false, plugin_excluded', array(false, 'plugin_excluded'), expo('zigbee', 10, 1, ctx()));
$probeActive = ctx(array('active_plugins' => array(), 'plugin_active_probe' => function ($id) { return $id === 'zigbee'; }));
check('repli de sonde : plugin actif hors liste', array(true, 'equipement'), expo('zigbee', 10, 1, $probeActive));
check('repli de sonde : plugin inactif', array(false, 'plugin_excluded'), expo('other', 10, 1, $probeActive));
$probeThrows = ctx(array('active_plugins' => array(), 'plugin_active_probe' => function ($id) { throw new Exception('x'); }));
check('sonde illisible → null', array(null, 'illisible'), expo('zigbee', 10, 1, $probeThrows));
check('liste des plugins actifs illisible (null) et sans sonde → null', array(null, 'illisible'), expo('virtual', 10, 1, ctx(array('active_plugins' => null))));

echo "Homebridge absent / valeurs illisibles — jamais false par défaut\n";
check('Homebridge absent ou inactif → null, homebridge_absent', array(null, 'homebridge_absent'), expo('virtual', 10, 1, ctx(array('homebridge' => 'absent'))));
check('état de Homebridge illisible → null, illisible', array(null, 'illisible'), expo('virtual', 10, 1, ctx(array('homebridge' => 'unreadable'))));
check('pièce illisible → null', array(null, 'illisible'), expo('virtual', 14, 1, ctx()));
check('valeur de pièce non numérique → null', array(null, 'illisible'), expo('virtual', 15, 1, ctx()));
check('valeur d\'équipement non numérique → null', array(null, 'illisible'), expo('virtual', 10, 'abc', ctx()));
check('valeur d\'équipement hors 0/1 → null', array(null, 'illisible'), expo('virtual', 10, 7, ctx()));

echo "Scénarios\n";
$sc = function ($raw) { $r = jeedom2ha_homekit_scenario_exposure(function () use ($raw) { return $raw; }); return array($r['exposed'], $r['source']); };
check('scénario clé absente → exposé', array(true, 'scenario_configuration'), $sc(null));
check('scénario "1" → exposé', array(true, 'scenario_configuration'), $sc('1'));
check('scénario "0" → non exposé', array(false, 'scenario_configuration'), $sc('0'));
check('scénario 0 (entier) → non exposé', array(false, 'scenario_configuration'), $sc(0));
check('scénario lecture en échec → null', array(null, 'illisible'), (function () {
    $r = jeedom2ha_homekit_scenario_exposure(function () { throw new Exception('x'); });
    return array($r['exposed'], $r['source']);
})());

echo "Identifiants physiques\n";
check('logical_id vide → null', null, jeedom2ha_normalize_logical_id(''));
check('logical_id espaces → null', null, jeedom2ha_normalize_logical_id('   '));
check('logical_id absent → null', null, jeedom2ha_normalize_logical_id(null));
check('logical_id non scalaire → null', null, jeedom2ha_normalize_logical_id(array('a')));
check('logical_id numérique → chaîne', '42', jeedom2ha_normalize_logical_id(42));
check('logical_id chaîne conservé', 'ab:01', jeedom2ha_normalize_logical_id('ab:01'));

echo "Liste des plugins actifs\n";
check('liste d\'identifiants', array('a' => true, 'b' => true), jeedom2ha_homekit_normalize_active_plugins(array('a', 'b')));
check('tableau indexé par identifiant', true, isset(jeedom2ha_homekit_normalize_active_plugins(array('a' => 'Nom A'))['a']));
check('non exploitable → null', null, jeedom2ha_homekit_normalize_active_plugins('x'));

echo "\n{$passed} passed, {$failed} failed\n";
exit($failed === 0 ? 0 : 1);
