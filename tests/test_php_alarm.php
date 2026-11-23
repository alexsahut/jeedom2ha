<?php
// ARTEFACT — FR49 (CC-64) : alarme. (1) fonctions pures de core/php/jeedom2ha_alarm.php ; (2) VRAI
// jeedom2ha::getFullTopology() sur un faux cœur Jeedom : les clés de mode Homebridge d'une alarme sont
// exportées en lecture seule, sans aucune écriture côté Jeedom ; (3) code de désarmement : stocké chiffré,
// retiré par la case dédiée, transmis au démon dans le corps HTTP local, jamais en ligne de commande ni
// dans un journal. Identifiants et libellés fictifs uniquement (CC-48).
// Exécution : php tests/test_php_alarm.php

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

/** Code PHP sans commentaires. */
function code_only($source) {
    $out = '';
    foreach (token_get_all($source) as $token) {
        if (is_array($token)) {
            if ($token[0] === T_COMMENT || $token[0] === T_DOC_COMMENT) { continue; }
            $out .= $token[1];
        } else {
            $out .= $token;
        }
    }
    return $out;
}

// ---------------------------------------------------------------------------------------------------
// Faux cœur Jeedom, chargé AVANT la classe du plugin (son require_once du cœur est intercepté plus bas).
// ---------------------------------------------------------------------------------------------------
$GLOBALS['j2ha_writes'] = array();
$GLOBALS['j2ha_config'] = array();
$GLOBALS['j2ha_logs'] = array();

class FakeCmdObj {
    private $d;
    public function __construct(array $d) { $this->d = $d; }
    public function getId() { return $this->d['id']; }
    public function getName() { return $this->d['name']; }
    public function getGeneric_type() { return $this->d['generic_type'] ?? ''; }
    public function getType() { return $this->d['type']; }
    public function getSubType() { return $this->d['sub_type']; }
    public function getCache($k, $def = null) { return $this->d['value'] ?? $def; }
    public function getUnite() { return ''; }
    public function getIsVisible() { return 1; }
    public function getIsHistorized() { return 0; }
    public function getLogicalId() { return $this->d['logical_id'] ?? ''; }
    public function getDisplay($k, $def = null) { return $def; }
    public function getValue() { return ''; }
    public function getConfiguration($k = '', $def = null) { return $def; }
    public function setConfiguration($k, $v) { $GLOBALS['j2ha_writes'][] = 'cmd::setConfiguration ' . $k; }
    public function save() { $GLOBALS['j2ha_writes'][] = 'cmd::save'; }
}

class eqLogic {
    public $d;
    public function __construct(array $d = array()) { $this->d = $d; }
    public static function all() { return array_map(function ($d) { return new eqLogic($d); }, $GLOBALS['j2ha_eqs']); }
    public function getId() { return $this->d['id']; }
    public function getName() { return $this->d['name']; }
    public function getObject_id() { return null; }
    public function getIsEnable() { return 1; }
    public function getIsVisible() { return 1; }
    public function getEqType_name() { return $this->d['eq_type']; }
    public function getGeneric_type() { return ''; }
    public function getLogicalId() { return ''; }
    public function getStatus($k, $def = null) { return $def; }
    public function getConfiguration($k = '', $def = null) {
        $conf = $this->d['conf'] ?? array();
        if ($k === '') { return $conf; }
        return array_key_exists($k, $conf) ? $conf[$k] : $def;
    }
    public function setConfiguration($k, $v) { $GLOBALS['j2ha_writes'][] = 'eqLogic::setConfiguration ' . $k; }
    public function save() { $GLOBALS['j2ha_writes'][] = 'eqLogic::save'; }
}
class cmd {
    public static function byEqLogicId($id) {
        foreach ($GLOBALS['j2ha_eqs'] as $eq) {
            if ($eq['id'] === $id) { return array_map(function ($c) { return new FakeCmdObj($c); }, $eq['cmds']); }
        }
        return array();
    }
}
class jeeObject { public static function all() { return array(); } }
class config {
    public static function byKey($k, $plugin = 'core', $def = '', $forceFresh = false) {
        $key = $plugin . '::' . $k;
        return array_key_exists($key, $GLOBALS['j2ha_config']) ? $GLOBALS['j2ha_config'][$key] : $def;
    }
    public static function save($k, $v, $plugin = 'core') { $GLOBALS['j2ha_config'][$plugin . '::' . $k] = $v; $GLOBALS['j2ha_writes'][] = 'config::save ' . $k; }
    public static function remove($k, $plugin = 'core') { unset($GLOBALS['j2ha_config'][$plugin . '::' . $k]); $GLOBALS['j2ha_writes'][] = 'config::remove ' . $k; }
}
class log {
    public static function add($plugin, $level, $message) { $GLOBALS['j2ha_logs'][] = $level . ' ' . $message; }
    public static function convertLogLevel($l) { return 'info'; }
    public static function getLogLevel($p) { return 200; }
}
class utils {
    public static function encrypt($v) { return 'ENC(' . strrev($v) . ')'; }
    public static function decrypt($v) { return (strpos($v, 'ENC(') === 0) ? strrev(substr($v, 4, -1)) : $v; }
}

// Le fichier de classe charge le cœur par un chemin relatif : on le lit et on retire ce require.
$classFile = $root . '/core/class/jeedom2ha.class.php';
$classSource = file_get_contents($classFile);
$patched = str_replace("require_once __DIR__  . '/../../../../core/php/core.inc.php';", '', $classSource);
$patched = str_replace('__DIR__', var_export($root . '/core/class', true), $patched);
check('le require du cœur Jeedom a été intercepté', $patched !== $classSource);
eval('?>' . $patched);

// ---------------------------------------------------------------------------------------------------
echo "Fonctions pures — clés de mode\n";
$conf = array('SetModePresent' => '9002|mode jour', 'SetModeAbsent' => '9001|Mode Total', 'SetModeNuit' => '', 'Autre' => 'x');
$read = function ($k) use ($conf) { return $conf[$k] ?? null; };
check('alarme : les clés présentes et non vides, telles quelles', jeedom2ha_alarm_mode_config(array('ALARM_STATE', null), $read) === array('SetModePresent' => '9002|mode jour', 'SetModeAbsent' => '9001|Mode Total'));
check('équipement sans commande ALARM_* : rien', jeedom2ha_alarm_mode_config(array('LIGHT_STATE', null), $read) === array());
check('aucune clé : tableau vide', jeedom2ha_alarm_mode_config(array('ALARM_ENABLE_STATE'), function ($k) { return null; }) === array());
check('valeur non scalaire ou blanche ignorée', jeedom2ha_alarm_mode_config(array('ALARM_MODE'), function ($k) { return $k === 'SetModeNuit' ? array('x') : '  '; }) === array());
check('lecture en erreur ignorée', jeedom2ha_alarm_mode_config(array('ALARM_MODE'), function ($k) { throw new Exception('illisible'); }) === array());

echo "Fonctions pures — code\n";
$enc = function ($v) { return 'ENC(' . strrev($v) . ')'; };
$dec = function ($v) { return strrev(substr($v, 4, -1)); };
check('saisie : stockée chiffrée', jeedom2ha_alarm_code_to_store('4321', 'OLD', $enc) === 'ENC(1234)');
check('saisie vide : le code actuel est gardé', jeedom2ha_alarm_code_to_store('', 'OLD', $enc) === 'OLD');
check('saisie blanche : le code actuel est gardé', jeedom2ha_alarm_code_to_store('   ', 'OLD', $enc) === 'OLD');
check('démon : code déchiffré', jeedom2ha_alarm_code_for_daemon('ENC(1234)', $dec) === '4321');
check('démon : rien de stocké -> chaîne vide', jeedom2ha_alarm_code_for_daemon('', $dec) === '');
check('démon : déchiffrement en erreur -> chaîne vide', jeedom2ha_alarm_code_for_daemon('x', function ($v) { throw new Exception('x'); }) === '');
check('case « Retirer » : seulement 1 / « 1 » / true', jeedom2ha_alarm_code_clear_requested('1') && jeedom2ha_alarm_code_clear_requested(1) && !jeedom2ha_alarm_code_clear_requested('0') && !jeedom2ha_alarm_code_clear_requested(''));
$functions = code_only(file_get_contents($root . '/core/php/jeedom2ha_alarm.php'));
foreach (array('config::', 'log::', 'core.inc.php', 'setConfiguration', '->save(') as $forbidden) {
    check('fonctions pures sans « ' . $forbidden . ' »', strpos($functions, $forbidden) === false);
}

// ---------------------------------------------------------------------------------------------------
echo "Export de topologie — VRAI getFullTopology sur un faux cœur\n";
$GLOBALS['j2ha_eqs'] = array(
    array('id' => 900, 'name' => 'Alarme essai', 'eq_type' => 'alarm',
          'conf' => array('SetModePresent' => '9105|mode jour', 'SetModeAbsent' => '9104|mode total', 'SetModeNuit' => '9106|mode nuit', 'sendToHomebridge' => 1),
          'cmds' => array(
              array('id' => 9101, 'name' => 'Actif', 'generic_type' => 'ALARM_ENABLE_STATE', 'type' => 'info', 'sub_type' => 'binary', 'value' => 1),
              array('id' => 9102, 'name' => 'Statut', 'generic_type' => 'ALARM_STATE', 'type' => 'info', 'sub_type' => 'binary', 'value' => 0),
              array('id' => 9103, 'name' => 'Immédiat', 'generic_type' => '', 'type' => 'info', 'sub_type' => 'binary', 'logical_id' => 'immediatState', 'value' => 0),
              array('id' => 9104, 'name' => 'mode total', 'generic_type' => 'ALARM_SET_MODE', 'type' => 'action', 'sub_type' => 'other'),
          )),
    array('id' => 901, 'name' => 'Lampe essai', 'eq_type' => 'virtual',
          'conf' => array('SetModePresent' => '1|ne doit pas sortir'),
          'cmds' => array(array('id' => 9111, 'name' => 'Etat', 'generic_type' => 'LIGHT_STATE', 'type' => 'info', 'sub_type' => 'binary'))),
    array('id' => 902, 'name' => 'Alarme sans modes', 'eq_type' => 'virtual', 'conf' => array(),
          'cmds' => array(array('id' => 9121, 'name' => 'Etat', 'generic_type' => 'ALARM_STATE', 'type' => 'info', 'sub_type' => 'binary'))),
);
$GLOBALS['j2ha_writes'] = array();
$topology = jeedom2ha::getFullTopology();
$byId = array();
foreach ($topology['eq_logics'] as $eq) { $byId[$eq['id']] = $eq; }
check('alarme : alarm_mode_config exporté tel quel', ($byId[900]['alarm_mode_config'] ?? null) === array('SetModePresent' => '9105|mode jour', 'SetModeAbsent' => '9104|mode total', 'SetModeNuit' => '9106|mode nuit'));
check('alarme : l\'info « Immédiat » sort avec son logicalId', in_array('immediatState', array_map(function ($c) { return $c['logical_id']; }, $byId[900]['cmds']), true));
check('équipement non alarme : pas de clé alarm_mode_config', !array_key_exists('alarm_mode_config', $byId[901]));
check('alarme sans clés de mode : pas de clé alarm_mode_config (charge inchangée)', !array_key_exists('alarm_mode_config', $byId[902]));
check('aucune écriture côté Jeedom pendant l\'export', $GLOBALS['j2ha_writes'] === array());

// ---------------------------------------------------------------------------------------------------
echo "Code de désarmement — hooks de configuration du cœur (preConfig_)\n";
$GLOBALS['j2ha_config'] = array();
$GLOBALS['j2ha_logs'] = array();
check('saisie : la valeur enregistrée est chiffrée', jeedom2ha::preConfig_alarmDisarmCode('2468') === 'ENC(8642)');
$GLOBALS['j2ha_config']['jeedom2ha::alarmDisarmCode'] = 'ENC(8642)';
check('saisie vide : le code enregistré reste', jeedom2ha::preConfig_alarmDisarmCode('') === 'ENC(8642)');
check('case non cochée : rien n\'est retiré', jeedom2ha::preConfig_alarmDisarmCodeClear('0') === '0' && isset($GLOBALS['j2ha_config']['jeedom2ha::alarmDisarmCode']));
check('case cochée : le code est retiré et la case se décoche', jeedom2ha::preConfig_alarmDisarmCodeClear('1') === '0' && !isset($GLOBALS['j2ha_config']['jeedom2ha::alarmDisarmCode']));
check('aucun journal ne contient le code', count(array_filter($GLOBALS['j2ha_logs'], function ($l) { return strpos($l, '2468') !== false || strpos($l, '8642') !== false; })) === 0);

echo "Code de désarmement — transmis au démon dans le corps HTTP local, jamais en ligne de commande\n";
$start = strpos($classSource, 'public static function deamon_start()');
$end = strpos($classSource, 'public static function isDaemonMqttReady');
$daemonStart = code_only('<?php ' . substr($classSource, $start, $end - $start));
check('le code part dans $mqttConfig (corps de /action/mqtt_connect)', strpos($daemonStart, "\$mqttConfig['alarm_disarm_code'] = \$alarmCode;") !== false);
check('… seulement s\'il est configuré', strpos($daemonStart, "if (\$alarmCode !== '') {") !== false);
check('… et après la construction de la ligne de commande du démon', strpos($daemonStart, '$alarmCode') > strrpos($daemonStart, '$cmd .='));
preg_match_all('/\$cmd \.= [^;]*;/', $daemonStart, $cmdLines);
check('la ligne de commande ne cite jamais le code', count($cmdLines[0]) > 0 && count(array_filter($cmdLines[0], function ($l) { return stripos($l, 'alarm') !== false; })) === 0);
check('le fichier de secrets du démon ne contient pas le code', strpos(substr($daemonStart, 0, strpos($daemonStart, '$cmd = ')), 'alarm') === false);
preg_match_all('/log::add\([^;]*;/', $daemonStart, $logLines);
check('aucun log::add ne cite le code', count(array_filter($logLines[0], function ($l) { return stripos($l, 'alarmCode') !== false || stripos($l, 'alarm_disarm_code') !== false; })) === 0);

echo "\n{$passed} réussis, {$failed} échoués\n";
exit($failed === 0 ? 0 : 1);
