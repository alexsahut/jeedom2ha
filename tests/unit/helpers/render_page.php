<?php
// Aide de test (Story 25.3) : rend desktop/php/jeedom2ha.php avec un faux cœur Jeedom et rend sur stdout
// {"html": "...", "vars": {...}} (variables passées à sendVarToJS). Sans argument : ne fait rien (code 0),
// car la CI exécute tous les fichiers PHP de tests/. Fixture : JSON {objects: [...], eqlogics: {...}}.
if (!isset($argv[1])) {
    exit(0);
}
$fixture = json_decode(file_get_contents($argv[1]), true);
$GLOBALS['j2ha_fixture'] = $fixture;
$GLOBALS['j2ha_vars'] = array();

class J2haFakeObject {
    private $d;
    public function __construct($d) { $this->d = $d; }
    public function getId() { return $this->d['id']; }
    public function getName() { return $this->d['name']; }
    public function getFather_id() { return isset($this->d['father_id']) ? $this->d['father_id'] : null; }
    public function getConfiguration($k, $default = '') { return $k === 'parentNumber' ? (isset($this->d['depth']) ? $this->d['depth'] : 0) : $default; }
    public function getDisplay($k, $default = '') { return isset($this->d['display'][$k]) ? $this->d['display'][$k] : $default; }
}
class J2haFakeEq {
    private $d;
    public function __construct($d) { $this->d = $d; }
    public function getId() { return $this->d['id']; }
    public function getName() { return $this->d['name']; }
    public function getEqType_name() { return isset($this->d['type']) ? $this->d['type'] : 'zwave'; }
    public function getIsEnable() { return isset($this->d['enabled']) ? ($this->d['enabled'] ? 1 : 0) : 1; }
}
class jeeObject {
    public static function buildTree($a = null, $b = false) {
        return array_map(function ($d) { return new J2haFakeObject($d); }, $GLOBALS['j2ha_fixture']['objects']);
    }
}
class eqLogic {
    public static function byObjectId($id, $onlyEnable = false) {
        $key = $id === null ? 'null' : (string) $id;
        $list = isset($GLOBALS['j2ha_fixture']['eqlogics'][$key]) ? $GLOBALS['j2ha_fixture']['eqlogics'][$key] : array();
        return array_map(function ($d) { return new J2haFakeEq($d); }, $list);
    }
}
class J2haFakePlugin {
    public function getId() { return 'jeedom2ha'; }
    public function getDocumentation() { return isset($GLOBALS['j2ha_fixture']['doc']) ? $GLOBALS['j2ha_fixture']['doc'] : ''; }
}
class plugin { public static function byId($id) { return new J2haFakePlugin(); } }
class jeedom { public static function getConfiguration($k) { return array(); } }
function isConnect($right = '') { return true; }
function sendVarToJS($name, $value) { $GLOBALS['j2ha_vars'][$name] = $value; }
function __($text, $file = '') { return $text; }
function init($k, $d = '') { return $d; }
function include_file() { }

ob_start();
include __DIR__ . '/../../../desktop/php/jeedom2ha.php';
$html = ob_get_clean();
echo json_encode(array('html' => $html, 'vars' => $GLOBALS['j2ha_vars']));
