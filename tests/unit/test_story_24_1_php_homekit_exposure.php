<?php
// Story 24.1 — signal d'exposition HomeKit : règle pure (lecture seule), sans cœur Jeedom.
// Reproduit à l'identique les tests de Homebridge (isset sur le tableau brut, intval, comparaisons souples).
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

// Contexte nominal : Homebridge présent ; pièces : 10 = 1, 11 = 0, 12 = "" (ou sans clé : lue 0), 13 = "1", 14 illisible.
function ctx(array $over = array()) {
    return array_merge(array(
        'homebridge'     => 'present',
        'default'        => 1,
        'active_plugins' => array('virtual' => true, 'zwave' => true, 'mobile' => true, 'homebridge' => true),
        'rooms'          => array(10 => 1, 11 => 0, 12 => '', 13 => '1', 14 => JEEDOM2HA_HOMEKIT_UNREADABLE, 15 => '0'),
    ), $over);
}

function expo($type, $obj, $eqConf, $ctx) {
    $r = jeedom2ha_homekit_eq_exposure($type, $obj, $eqConf, $ctx);
    return array($r['exposed'], $r['source']);
}

function conf($v) { return array('sendToHomebridge' => $v); }

echo "Équipement : règle à trois niveaux\n";
check('équipement à 1 → exposé', array(true, 'equipement'), expo('virtual', 10, conf(1), ctx()));
check('équipement à "1" → exposé', array(true, 'equipement'), expo('virtual', 10, conf('1'), ctx()));
check('équipement à 0 → false, equipement', array(false, 'equipement'), expo('virtual', 10, conf(0), ctx()));
check('équipement à "0" → false, equipement', array(false, 'equipement'), expo('virtual', 10, conf('0'), ctx()));
check('équipement à "" (isset vrai, intval 0) → false, equipement', array(false, 'equipement'), expo('virtual', 10, conf(''), ctx()));
check('équipement à "2" → exposé (différent de 0)', array(true, 'equipement'), expo('virtual', 10, conf('2'), ctx()));
check('équipement valeur texte (intval 0) → false', array(false, 'equipement'), expo('virtual', 10, conf('abc'), ctx()));
check('clé absente, défaut 1 → exposé, defaut_homebridge', array(true, 'defaut_homebridge'), expo('virtual', 10, array(), ctx()));
check('clé absente, défaut "1" → exposé', array(true, 'defaut_homebridge'), expo('virtual', 10, array('autre' => 1), ctx(array('default' => '1'))));
check('clé absente, défaut "0" → false, defaut_homebridge', array(false, 'defaut_homebridge'), expo('virtual', 10, array(), ctx(array('default' => '0'))));
check('clé absente, défaut 0 → false', array(false, 'defaut_homebridge'), expo('virtual', 10, array(), ctx(array('default' => 0))));
check('clé null (isset faux) → défaut', array(true, 'defaut_homebridge'), expo('virtual', 10, conf(null), ctx()));
check('configuration non tableau → défaut', array(true, 'defaut_homebridge'), expo('virtual', 10, '', ctx()));
check('défaut illisible (exception) → null', array(null, 'illisible'), expo('virtual', 10, array(), ctx(array('default' => JEEDOM2HA_HOMEKIT_UNREADABLE))));
check('configuration d\'équipement illisible (exception) → null', array(null, 'illisible'), expo('virtual', 10, JEEDOM2HA_HOMEKIT_UNREADABLE, ctx()));

echo "Pièce (Task 0 bis)\n";
check('pièce à 1 → exposée', array(true, 'equipement'), expo('virtual', 10, conf(1), ctx()));
check('pièce à "1" → exposée', array(true, 'equipement'), expo('virtual', 13, conf(1), ctx()));
check('pièce à 0 → false, piece', array(false, 'piece'), expo('virtual', 11, conf(1), ctx()));
check('pièce à "0" → false, piece', array(false, 'piece'), expo('virtual', 15, conf(1), ctx()));
check('pièce à "" → false, piece', array(false, 'piece'), expo('virtual', 12, conf(1), ctx()));
check('pièce sans clé (lue 0) → false, piece', array(false, 'piece'), expo('virtual', 11, conf(1), ctx(array('rooms' => array(11 => 0)))));
check('équipement sans pièce (null) → false, piece', array(false, 'piece'), expo('virtual', null, conf(1), ctx()));
check('équipement sans pièce (-1) → false, piece', array(false, 'piece'), expo('virtual', -1, conf(1), ctx()));
check('pièce inexistante → false, piece', array(false, 'piece'), expo('virtual', 99, conf(1), ctx()));
check('pièce illisible (exception) → null', array(null, 'illisible'), expo('virtual', 14, conf(1), ctx()));

echo "Plugins : la liste des plugins actifs fait foi\n";
check('plugin mobile → false, plugin_excluded', array(false, 'plugin_excluded'), expo('mobile', 10, conf(1), ctx()));
check('plugin homebridge → false, plugin_excluded', array(false, 'plugin_excluded'), expo('homebridge', 10, conf(1), ctx()));
check('plugin hors liste (inactif ou désinstallé) → false, plugin_excluded', array(false, 'plugin_excluded'), expo('zigbee', 10, conf(1), ctx()));
check('plugin hors liste, pièce à 0 : le plugin décide d\'abord', array(false, 'plugin_excluded'), expo('zigbee', 11, conf(1), ctx()));
check('liste des plugins illisible (null) → null', array(null, 'illisible'), expo('virtual', 10, conf(1), ctx(array('active_plugins' => null))));

echo "Homebridge absent / illisible\n";
check('Homebridge absent ou inactif → null, homebridge_absent', array(null, 'homebridge_absent'), expo('virtual', 10, conf(1), ctx(array('homebridge' => 'absent'))));
check('état de Homebridge illisible → null, illisible', array(null, 'illisible'), expo('virtual', 10, conf(1), ctx(array('homebridge' => 'unreadable'))));

echo "Scénarios (clé absente = NON exposé)\n";
$sc = function ($conf) { $r = jeedom2ha_homekit_scenario_exposure(function () use ($conf) { return $conf; }); return array($r['exposed'], $r['source']); };
check('scénario sans clé → false', array(false, 'scenario_configuration'), $sc(array()));
check('scénario clé null → false', array(false, 'scenario_configuration'), $sc(conf(null)));
check('scénario "0" → false', array(false, 'scenario_configuration'), $sc(conf('0')));
check('scénario 0 → false', array(false, 'scenario_configuration'), $sc(conf(0)));
check('scénario "1" → true', array(true, 'scenario_configuration'), $sc(conf('1')));
check('scénario 1 → true', array(true, 'scenario_configuration'), $sc(conf(1)));
check('scénario "" (tableau brut) → true', array(true, 'scenario_configuration'), $sc(conf('')));
check('configuration non tableau → false', array(false, 'scenario_configuration'), $sc(''));
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
check('liste vide → tableau vide (aucun plugin actif)', array(), jeedom2ha_homekit_normalize_active_plugins(array()));
check('non exploitable → null', null, jeedom2ha_homekit_normalize_active_plugins('x'));

echo "\n{$passed} passed, {$failed} failed\n";
exit($failed === 0 ? 0 : 1);
