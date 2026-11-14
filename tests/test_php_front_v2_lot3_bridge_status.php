<?php
// ARTEFACT — Front v2, Lot 3 : relais `getBridgeStatus` — deux clés additives `ha` et `publication`, relayées telles quelles
// depuis `/system/status`, `null` si le démon ne les fournit pas ou ne répond pas. Les clés historiques sont inchangées.
// Exécute la VRAIE branche de l'ajax (extraite du fichier) avec un faux cœur Jeedom. Données fictives uniquement.
// Exécution : php tests/test_php_front_v2_lot3_bridge_status.php

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

class J2haAjaxDone extends Exception {
    public $result;
    public function __construct($result) { parent::__construct('done'); $this->result = $result; }
}

// Faux cœur : `ajax::success` termine la requête (comme le vrai, qui fait `die`).
class ajax {
    public static function success($result = '') { throw new J2haAjaxDone($result); }
}

class jeedom2ha {
    public static $status = null;
    public static function callDaemon($path) {
        if ($path !== '/system/status') { throw new Exception('route inattendue ' . $path); }
        return self::$status;
    }
}

$ajax = file_get_contents($root . '/core/ajax/jeedom2ha.ajax.php');
$start = strpos($ajax, "if (\$action == 'getBridgeStatus') {");
check('branche getBridgeStatus présente', $start !== false);
$end = $start === false ? false : strpos($ajax, "\n    else if (\$action ==", $start + 10);
check('fin de branche trouvée', $end !== false);
if ($start === false || $end === false) {
    echo "\n{$passed} réussis, {$failed} échoués\n";
    exit(1);
}
$branch = substr($ajax, $start, $end - $start);

function run_branch($branch, $status) {
    jeedom2ha::$status = $status;
    $action = 'getBridgeStatus';
    try {
        eval($branch);
    } catch (J2haAjaxDone $done) {
        return $done->result;
    }
    return 'NO_RESPONSE';
}

$historical = array('daemon', 'mqtt', 'demon', 'broker', 'derniere_synchro_terminee', 'derniere_operation_resultat');

echo "Démon qui fournit ha et publication\n";
$ha = array('birth_seen_at' => '2026-11-13T06:00:00+00:00', 'discovery_prefix' => 'homeassistant');
$publication = array('equipments_published' => 29, 'entities_published' => 41, 'scenarios_published' => 2);
$out = run_branch($branch, array('status' => 'ok', 'payload' => array(
    'mqtt' => array('state' => 'connected', 'connected' => true, 'broker' => 'broker.example.test:1883'),
    'demon' => array('version' => '0.0.0-test'),
    'broker' => array('state' => 'connected', 'connected' => true, 'broker' => 'broker.example.test:1883'),
    'derniere_synchro_terminee' => '2026-11-13T05:00:00+00:00',
    'derniere_operation_resultat' => 'aucun',
    'ha' => $ha,
    'publication' => $publication,
)));
check('ha relayé tel quel', is_array($out) && $out['ha'] === $ha);
check('publication relayée telle quelle', is_array($out) && $out['publication'] === $publication);
check('daemon vrai', is_array($out) && $out['daemon'] === true);
foreach ($historical as $key) {
    check("clé historique « {$key} » conservée", is_array($out) && array_key_exists($key, $out));
}
check('aucune autre clé ajoutée', is_array($out) && array_keys($out) === array('daemon', 'mqtt', 'demon', 'broker', 'derniere_synchro_terminee', 'ha', 'publication', 'derniere_operation_resultat'));

echo "Démon ancien (sans ha ni publication)\n";
$out = run_branch($branch, array('status' => 'ok', 'payload' => array(
    'mqtt' => array('state' => 'connected', 'connected' => true, 'broker' => ''),
)));
check('ha présent et null', is_array($out) && array_key_exists('ha', $out) && $out['ha'] === null);
check('publication présente et null', is_array($out) && array_key_exists('publication', $out) && $out['publication'] === null);
check('derniere_operation_resultat par défaut', is_array($out) && $out['derniere_operation_resultat'] === 'aucun');

echo "Valeurs mal formées\n";
$out = run_branch($branch, array('status' => 'ok', 'payload' => array('ha' => 'oui', 'publication' => 3)));
check('ha non tableau -> null', is_array($out) && $out['ha'] === null);
check('publication non tableau -> null', is_array($out) && $out['publication'] === null);

echo "Démon injoignable\n";
$out = run_branch($branch, null);
check('daemon faux', is_array($out) && $out['daemon'] === false);
check('ha null', is_array($out) && array_key_exists('ha', $out) && $out['ha'] === null);
check('publication null', is_array($out) && array_key_exists('publication', $out) && $out['publication'] === null);
foreach ($historical as $key) {
    check("clé historique « {$key} » conservée", is_array($out) && array_key_exists($key, $out));
}

echo "\n{$passed} réussis, {$failed} échoués\n";
exit($failed === 0 ? 0 : 1);
