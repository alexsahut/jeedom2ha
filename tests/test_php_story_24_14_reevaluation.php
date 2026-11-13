<?php
// ARTEFACT — Story 24.14 (décision D2 A, AC10) : réévaluation des décisions sans redémarrage. Empreinte pure (isEnable,
// isActive, exclusions ; aucun nom ; indépendante de l'ordre), pas de la tâche périodique (synchro de service seulement
// sur changement, jamais si le démon n'est pas prêt, refus 409 non mémorisé), câblage du cron dans la classe et
// non-régression de buildScenariosPayload. Identifiants et noms fictifs uniquement (CC-48).
// Exécution : php tests/test_php_story_24_14_reevaluation.php

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

require_once $root . '/core/php/jeedom2ha_reevaluation.php';

// ---------------------------------------------------------------------------
// Empreinte
// ---------------------------------------------------------------------------
echo "Empreinte des décisions\n";

function eq_row($id, $enable = 1, $type = 'virtual', $object = 3, $conf = '{}', $name = null) {
    $row = array('id' => (string) $id, 'isEnable' => (string) $enable, 'eqType_name' => $type,
                 'object_id' => $object === null ? null : (string) $object, 'configuration' => $conf);
    if ($name !== null) { $row['name'] = $name; }
    return $row;
}
$eqs = array(eq_row(1), eq_row(2, 0), eq_row(3, 1, 'zwave', 4), eq_row(4, 1, 'virtual', null, '{"jeedom2ha_excluded":"1"}'));
$scs = array(array('id' => '10', 'isActive' => '1'), array('id' => '11', 'isActive' => '0'));
$settings = array('excludedPlugins' => 'zwave', 'excludedObjects' => '7');
$base = jeedom2ha_decision_fingerprint($eqs, $scs, $settings);

check('empreinte = SHA-256 hexadécimal', (bool) preg_match('/^[0-9a-f]{64}$/', $base));
check('inchangée si rien ne change', jeedom2ha_decision_fingerprint($eqs, $scs, $settings) === $base);
check('indépendante de l\'ordre de lecture',
    jeedom2ha_decision_fingerprint(array_reverse($eqs), array_reverse($scs), $settings) === $base);
check('indépendante de l\'ordre des réglages CSV',
    jeedom2ha_decision_fingerprint($eqs, $scs, array('excludedPlugins' => ' zwave ,', 'excludedObjects' => '7,7')) === $base);

$e = $eqs; $e[0]['configuration'] = null; $e[1]['configuration'] = null; $e[2]['configuration'] = null;
check('configuration non rapatriée (NULL, sans clé d\'exclusion) = configuration sans exclusion',
    jeedom2ha_decision_fingerprint($e, $scs, $settings) === $base);
$e = $eqs; $e[0]['isEnable'] = '0';
check('change si un isEnable change', jeedom2ha_decision_fingerprint($e, $scs, $settings) !== $base);
$s = $scs; $s[1]['isActive'] = '1';
check('change si un isActive change', jeedom2ha_decision_fingerprint($eqs, $s, $settings) !== $base);
$e = $eqs; $e[0]['configuration'] = '{"jeedom2ha_excluded":1}';
check('change si l\'exclusion d\'un équipement change', jeedom2ha_decision_fingerprint($e, $scs, $settings) !== $base);
check('change si les plugins exclus changent',
    jeedom2ha_decision_fingerprint($eqs, $scs, array('excludedPlugins' => '', 'excludedObjects' => '7')) !== $base);
check('change si les pièces exclues changent (équipement de la pièce)',
    jeedom2ha_decision_fingerprint($eqs, $scs, array('excludedPlugins' => 'zwave', 'excludedObjects' => '3')) !== $base);
$e = $eqs; $e[] = eq_row(5);
check('change si un équipement apparaît', jeedom2ha_decision_fingerprint($e, $scs, $settings) !== $base);
$s = $scs; array_pop($s);
check('change si un scénario disparaît', jeedom2ha_decision_fingerprint($eqs, $s, $settings) !== $base);

// Champs sans effet sur les décisions : nom, autre configuration, équipements du plugin lui-même.
$named = array();
foreach ($eqs as $row) { $row['name'] = 'Nom fictif ' . $row['id']; $named[] = $row; }
$namedSc = array();
foreach ($scs as $row) { $row['name'] = 'Scénario fictif ' . $row['id']; $namedSc[] = $row; }
check('aucun nom n\'entre dans l\'empreinte', jeedom2ha_decision_fingerprint($named, $namedSc, $settings) === $base);
$e = $eqs; $e[0]['configuration'] = '{"autre_cle":"valeur"}';
check('une autre clé de configuration est sans effet', jeedom2ha_decision_fingerprint($e, $scs, $settings) === $base);
$e = $eqs; $e[] = eq_row(99, 0, 'jeedom2ha');
check('les équipements du plugin lui-même sont ignorés', jeedom2ha_decision_fingerprint($e, $scs, $settings) === $base);
$e = $eqs; $e[] = array('id' => 'x'); $e[] = 'garbage';
check('une ligne illisible est ignorée', jeedom2ha_decision_fingerprint($e, $scs, $settings) === $base);
$e = $eqs; $e[2]['object_id'] = '7';
check('un équipement exclu par plugin qui change de pièce exclue : même exclusion effective (plugin prime)',
    jeedom2ha_decision_fingerprint($e, $scs, $settings) === $base);

$source = file_get_contents($root . '/core/php/jeedom2ha_reevaluation.php');
check('fichier de fonctions pures : aucune dépendance au cœur Jeedom',
    strpos($source, 'core.inc.php') === false && !preg_match('/\b(config|DB|log)::/', $source));
check('la fonction d\'empreinte ne lit aucune colonne de nom',
    strpos($source, "['name']") === false && strpos($source, '"name"') === false);

// ---------------------------------------------------------------------------
// Pas de la tâche périodique
// ---------------------------------------------------------------------------
echo "Pas de la tâche périodique\n";

function make_deps(array $over = array()) {
    $state = (object) array('stored' => 'old', 'calls' => array(), 'logs' => array());
    $deps = array(
        'fingerprint' => function () { return 'new'; },
        'stored' => function () use ($state) { return $state->stored; },
        'store' => function ($f) use ($state) { $state->stored = $f; $state->calls[] = 'store'; },
        'ready' => function () use ($state) { $state->calls[] = 'ready'; return true; },
        'topology' => function () use ($state) { $state->calls[] = 'topology'; return array('eq_logics' => array()); },
        'sync' => function ($t) use ($state) { $state->calls[] = 'sync'; return array('status' => 'ok'); },
        'listeners' => function () use ($state) { $state->calls[] = 'listeners'; },
        'log' => function ($level, $message) use ($state) { $state->logs[] = array($level, $message); },
    );
    foreach ($over as $k => $v) { $deps[$k] = $v; }
    return array($deps, $state);
}
function levels($state, $level) {
    return count(array_filter($state->logs, function ($l) use ($level) { return $l[0] === $level; }));
}

list($deps, $st) = make_deps(array('fingerprint' => function () { return 'old'; }));
$r = jeedom2ha_reevaluation_tick($deps);
check('empreinte inchangée : aucun appel au démon ni synchro', $r['status'] === 'unchanged' && $st->calls === array());

list($deps, $st) = make_deps();
$r = jeedom2ha_reevaluation_tick($deps);
check('empreinte changée : synchro de service puis mémorisation et listeners',
    $r['status'] === 'synced' && $st->calls === array('ready', 'topology', 'sync', 'store', 'listeners') && $st->stored === 'new');

list($deps, $st) = make_deps(array('stored' => function () { return ''; }));
check('aucune empreinte mémorisée : une synchro a lieu', jeedom2ha_reevaluation_tick($deps)['status'] === 'synced');

list($deps, $st) = make_deps(array('ready' => function () { return false; }));
$r = jeedom2ha_reevaluation_tick($deps);
check('démon non prêt : jamais de synchro, rien de mémorisé',
    $r['reason'] === 'daemon_not_ready' && !in_array('sync', $st->calls, true) && $st->stored === 'old');
list($deps, $st) = make_deps(array('ready' => function () { throw new Exception('down'); }));
check('démon injoignable (exception) : jamais de synchro',
    jeedom2ha_reevaluation_tick($deps)['reason'] === 'daemon_not_ready' && $st->stored === 'old');

$conflict = array('status' => 'error', 'code' => 'action_in_progress', 'message' => 'opération en cours');
list($deps, $st) = make_deps(array('sync' => function ($t) use ($conflict) { return $conflict; }));
$r = jeedom2ha_reevaluation_tick($deps);
check('refus 409 : reporté, pas une erreur, empreinte non mémorisée',
    $r['status'] === 'deferred' && $st->stored === 'old' && levels($st, 'warning') === 0 && levels($st, 'error') === 0);
list($deps2, $st2) = make_deps(array('stored' => function () use ($st) { return $st->stored; }));
check('nouvel essai à l\'échéance suivante après un 409', jeedom2ha_reevaluation_tick($deps2)['status'] === 'synced');

list($deps, $st) = make_deps(array('sync' => function ($t) { return null; }));
$r = jeedom2ha_reevaluation_tick($deps);
check('démon muet pendant la synchro : échec journalisé, empreinte non mémorisée',
    $r['status'] === 'failed' && $st->stored === 'old' && levels($st, 'warning') === 1);
list($deps, $st) = make_deps(array('sync' => function ($t) { return array('status' => 'error', 'message' => 'x'); }));
check('synchro en échec (500) : empreinte non mémorisée', jeedom2ha_reevaluation_tick($deps)['status'] === 'failed' && $st->stored === 'old');
list($deps, $st) = make_deps(array('sync' => function ($t) { throw new Exception('boom'); }));
check('exception pendant la synchro : rattrapée, non mémorisée', jeedom2ha_reevaluation_tick($deps)['status'] === 'failed' && $st->stored === 'old');

// Revue P2 (1) — bouton ou disponibilité de scénario non publié : synchro incomplète, empreinte non mémorisée.
list($deps, $st) = make_deps(array('sync' => function ($t) {
    return array('status' => 'ok', 'operation_result' => 'partiel', 'scenario_availability_complete' => false);
}));
$r = jeedom2ha_reevaluation_tick($deps);
check('disponibilité de scénario non publiée : statut partial, empreinte non mémorisée',
    $r['status'] === 'partial' && $r['reason'] === 'sync_incomplete' && $st->stored === 'old'
    && !in_array('store', $st->calls, true) && levels($st, 'warning') === 1 && levels($st, 'error') === 0);
check('synchro incomplète : les listeners sont quand même réalignés', in_array('listeners', $st->calls, true));
list($deps2, $st2) = make_deps(array('stored' => function () use ($st) { return $st->stored; }));
check('nouvel essai à l\'échéance suivante après une synchro incomplète', jeedom2ha_reevaluation_tick($deps2)['status'] === 'synced');
foreach (array('partiel', 'echec') as $res) {
    list($deps, $st) = make_deps(array('sync' => function ($t) use ($res) {
        return array('status' => 'ok', 'operation_result' => $res, 'scenario_availability_complete' => true);
    }));
    $r = jeedom2ha_reevaluation_tick($deps);
    check("publication d'équipement en échec (operation_result $res) : partial, empreinte non mémorisée",
        $r['status'] === 'partial' && $st->stored === 'old');
}
list($deps, $st) = make_deps(array('sync' => function ($t) { return array('status' => 'ok', 'operation_result' => 'succes', 'scenario_availability_complete' => true); }));
check('synchro complète (champ vrai) : empreinte mémorisée', jeedom2ha_reevaluation_tick($deps)['status'] === 'synced' && $st->stored === 'new');

echo "Mémorisation après démarrage ou « Relire Jeedom »\n";
$saved = array();
$store = function ($f) use (&$saved) { $saved[] = $f; };
check('synchro réussie : empreinte mémorisée',
    jeedom2ha_reevaluation_remember_after_sync('fp', array('status' => 'ok'), $store) === true && $saved === array('fp'));
$saved = array();
check('synchro réussie, scénarios complets : empreinte mémorisée',
    jeedom2ha_reevaluation_remember_after_sync('fp', array('status' => 'ok', 'scenario_availability_complete' => true), $store) && $saved === array('fp'));
$saved = array();
check('synchro partielle ou en échec (équipement) : rien de mémorisé',
    !jeedom2ha_reevaluation_remember_after_sync('fp', array('status' => 'ok', 'operation_result' => 'partiel'), $store)
    && !jeedom2ha_reevaluation_remember_after_sync('fp', array('status' => 'ok', 'operation_result' => 'echec'), $store)
    && $saved === array());
check('synchro réussie (operation_result succes) : empreinte mémorisée',
    jeedom2ha_reevaluation_remember_after_sync('fp', array('status' => 'ok', 'operation_result' => 'succes'), $store) && $saved === array('fp'));
$saved = array();
check('synchro incomplète (disponibilité de scénario) : rien de mémorisé',
    !jeedom2ha_reevaluation_remember_after_sync('fp', array('status' => 'ok', 'scenario_availability_complete' => false), $store) && $saved === array());
check('synchro en échec, refusée (409) ou sans réponse : rien de mémorisé',
    !jeedom2ha_reevaluation_remember_after_sync('fp', array('status' => 'error'), $store)
    && !jeedom2ha_reevaluation_remember_after_sync('fp', array('status' => 'error', 'code' => 'action_in_progress'), $store)
    && !jeedom2ha_reevaluation_remember_after_sync('fp', null, $store) && $saved === array());
check('empreinte illisible (null) : rien de mémorisé',
    !jeedom2ha_reevaluation_remember_after_sync(null, array('status' => 'ok'), $store) && $saved === array());

list($deps, $st) = make_deps(array('fingerprint' => function () { throw new Exception('db'); }));
$r = jeedom2ha_reevaluation_tick($deps);
check('empreinte illisible : rien n\'est lancé', $r['reason'] === 'fingerprint_unreadable' && $st->calls === array());
list($deps, $st) = make_deps(array('topology' => function () { return null; }));
check('topologie illisible : pas de synchro', jeedom2ha_reevaluation_tick($deps)['reason'] === 'topology_unavailable' && !in_array('sync', $st->calls, true));
list($deps, $st) = make_deps(array('listeners' => function () { throw new Exception('l'); }));
check('échec des listeners : la synchro reste réussie', jeedom2ha_reevaluation_tick($deps)['status'] === 'synced' && $st->stored === 'new');

$order = array();
list($deps, $st) = make_deps(array(
    'fingerprint' => function () use (&$order) { $order[] = 'fingerprint'; return 'new'; },
    'topology' => function () use (&$order) { $order[] = 'topology'; return array(); },
));
jeedom2ha_reevaluation_tick($deps);
check('empreinte lue avant la topologie', $order === array('fingerprint', 'topology'));

list($deps, $st) = make_deps();
jeedom2ha_reevaluation_tick($deps);
$logText = implode("\n", array_map(function ($l) { return $l[1]; }, $st->logs));
check('journal sans nom ni identifiant de scénario/équipement', strpos($logText, 'fictif') === false && !preg_match('/\d{2,}/', $logText));

// ---------------------------------------------------------------------------
// Câblage dans la classe (lecture du source : la classe exige le cœur Jeedom)
// ---------------------------------------------------------------------------
echo "Câblage du cron\n";
$class = file_get_contents($root . '/core/class/jeedom2ha.class.php');
check('la classe charge le fichier de fonctions pures', strpos($class, "require_once __DIR__  . '/../php/jeedom2ha_reevaluation.php';") !== false);
check('cron5() est déclaré dans la classe du plugin', (bool) preg_match('/public static function cron5\(\)/', $class));
check('aucune autre méthode cron* déclarée', preg_match_all('/public static function cron[0-9A-Za-z]*\(/', $class) === 1);
check('synchro de service : en-tête X-Jeedom2ha-Sync-Mode = service',
    strpos($class, "array('X-Jeedom2ha-Sync-Mode' => 'service')") !== false);
check('synchro de démarrage : en-tête X-Jeedom2ha-Sync-Mode = boot',
    strpos($class, "array('X-Jeedom2ha-Sync-Mode' => 'boot')") !== false);
check('empreinte gardée en configuration du plugin (pas de table)',
    strpos($class, 'config::save(JEEDOM2HA_REEVALUATION_FINGERPRINT_KEY') !== false
    && !preg_match('/CREATE\s+TABLE|INSERT\s+INTO|UPDATE\s+`/i', $class));
check('requêtes minimales : aucune colonne de nom lue',
    (bool) preg_match("/SELECT `id`, `isEnable`, `eqType_name`, `object_id`, IF\\(`configuration` LIKE '%jeedom2ha_excluded%', `configuration`, NULL\\) AS `configuration` FROM `eqLogic`/", $class)
    && (bool) preg_match('/SELECT `id`, `isActive` FROM `scenario`/', $class));
check('démon prêt = broker MQTT connecté (isDaemonMqttReady)',
    strpos($class, "self::isDaemonMqttReady(self::callDaemon('/system/status', null, 'GET', 3, 1))") !== false);
check('démarrage : empreinte mémorisée par la règle commune (synchro aboutie et scénarios complets)',
    strpos($class, 'self::rememberDecisionFingerprintAfterSync($bootFingerprint, $syncResult);') !== false);
$ajax = file_get_contents($root . '/core/ajax/jeedom2ha.ajax.php');
$scanStart = strpos($ajax, "\$action == 'scanTopology'");
$scan = $scanStart === false ? '' : substr($ajax, $scanStart, strpos($ajax, "\$action == 'getDiagnostics'") - $scanStart);
$posFp = strpos($scan, '$fingerprint = jeedom2ha::safeDecisionFingerprint();');
$posTopo = strpos($scan, '$topology = jeedom2ha::getFullTopology();');
$posRemember = strpos($scan, 'jeedom2ha::rememberDecisionFingerprintAfterSync($fingerprint, $result);');
$posSync = strpos($scan, "'X-Jeedom2ha-Sync-Mode' => 'rescan'");
check('« Relire Jeedom » : empreinte lue avant la topologie, mémorisée après la synchro',
    $posFp !== false && $posTopo !== false && $posRemember !== false && $posSync !== false
    && $posFp < $posTopo && $posSync < $posRemember);
$info = json_decode(file_get_contents($root . '/plugin_info/info.json'), true);
check('plugin_info/info.json reste un JSON valide', is_array($info) && ($info['id'] ?? null) === 'jeedom2ha');

// Non-régression 21-1 / 24-1 : buildScenariosPayload inchangé (comparé à origin/main quand une base existe).
echo "Non-régression buildScenariosPayload\n";
function slice_function($text, $name) {
    $start = strpos($text, 'public static function ' . $name . '(');
    if ($start === false) { return null; }
    $end = strpos($text, "\n  }\n", $start);
    return $end === false ? null : substr($text, $start, $end - $start);
}
$current = slice_function($class, 'buildScenariosPayload');
check('buildScenariosPayload présent', $current !== null);
$baseText = null;
foreach (array('origin/main', 'main') as $ref) {
    $out = @shell_exec('git -C ' . escapeshellarg($root) . ' show ' . escapeshellarg($ref . ':core/class/jeedom2ha.class.php') . ' 2>/dev/null');
    if (is_string($out) && $out !== '') { $baseText = $out; break; }
}
if ($baseText !== null) {
    check('buildScenariosPayload identique à la base', slice_function($baseText, 'buildScenariosPayload') === $current);
} else {
    echo "  (aucune base git : comparaison ignorée)\n";
}

echo "\n{$passed} réussis, {$failed} échoués\n";
exit($failed === 0 ? 0 : 1);
