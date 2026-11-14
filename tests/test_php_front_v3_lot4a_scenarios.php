<?php
// ARTEFACT — Front v3, Lot 4a (option B d'Alexandre) : publication des scénarios au choix de l'utilisateur, côté PHP.
//  - fonctions pures de core/php/jeedom2ha_scenario_publication.php (listes, mode de lancement, migration, choix) ;
//  - méthodes de la classe qui enrichissent la topologie (extraites du VRAI fichier, faux cœur Jeedom) ;
//  - VRAIE branche ajax `saveScenarioPublication` (extraite du fichier) avec un faux cœur ;
//  - plugin_info/install.php : migration appelée par install ET update, sans la classe du plugin.
// Identifiants et noms fictifs uniquement. Exécution : php tests/test_php_front_v3_lot4a_scenarios.php

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

function done_and_exit() {
    global $passed, $failed;
    echo "\n{$passed} réussis, {$failed} échoués\n";
    exit($failed === 0 ? 0 : 1);
}

$functionFile = $root . '/core/php/jeedom2ha_scenario_publication.php';
check('le fichier de fonctions pures existe sous core/php', is_file($functionFile));
if (!is_file($functionFile)) {
    done_and_exit();
}
require_once $functionFile;

/** Configuration en mémoire : read/save comme config::byKey/config::save (liste JSON décodée à la lecture). */
function memory_deps(array &$store, $readable = array(20, 21, 22), $fresh = false, array &$writes = null) {
    return array(
        'read' => function ($key) use (&$store) {
            if (!array_key_exists($key, $store) || $store[$key] === '') {
                return '';
            }
            $decoded = json_decode($store[$key], true);
            return is_array($decoded) ? $decoded : $store[$key];
        },
        'save' => function ($key, $value) use (&$store, &$writes) {
            $store[$key] = $value;
            if (is_array($writes)) {
                $writes[] = $key;
            }
        },
        'readableIds' => function () use ($readable) {
            return $readable;
        },
        'isFresh' => function () use ($fresh) {
            return $fresh;
        },
        'log' => function ($level, $message) {
        },
    );
}

echo "Listes d'identifiants\n";
check('clé absente -> null', jeedom2ha_scenario_id_list('') === null);
check('liste JSON vide -> []', jeedom2ha_scenario_id_list(array()) === array() && jeedom2ha_scenario_id_list('[]') === array());
check('tri, doublons, chaînes numériques', jeedom2ha_scenario_id_list(array(22, '20', 22, 0, -1, 'x', 1.5)) === array(20, 22));
check('valeur écrite = liste JSON', jeedom2ha_scenario_id_list_value(array(22, 20)) === '[20,22]' && jeedom2ha_scenario_id_list_value(array()) === '[]');
check('paramètre strict accepté', jeedom2ha_parse_scenario_id_param('[15,12]') === array(12, 15) && jeedom2ha_parse_scenario_id_param('[]') === array());
foreach (array('', '12', '[12,]', '[ 12]', '[012]', '[0]', '[-1]', '["12"]', '[12,12]', '{"a":1}', null) as $bad) {
    check('paramètre refusé : ' . var_export($bad, true), jeedom2ha_parse_scenario_id_param($bad) === null);
}

echo "Mode de lancement\n";
check('provoqué sans déclencheur -> lancé à la main',
    jeedom2ha_scenario_launch_info('provoke', array(''), '') === array('mode' => 'provoke', 'has_trigger' => false, 'has_schedule' => false, 'manual' => true));
check('provoqué avec déclencheur', jeedom2ha_scenario_launch_info('provoke', array('#123#'), '')['has_trigger'] === true
    && jeedom2ha_scenario_launch_info('provoke', array('#123#'), '')['manual'] === false);
check('programmé', jeedom2ha_scenario_launch_info('schedule', array('#1#'), array('0 7 * * *')) === array('mode' => 'schedule', 'has_trigger' => false, 'has_schedule' => true, 'manual' => false));
check('les deux', jeedom2ha_scenario_launch_info('all', array('#1#'), '*/5 * * * *') === array('mode' => 'all', 'has_trigger' => true, 'has_schedule' => true, 'manual' => false));
check('programmé sans programmation -> lancé à la main', jeedom2ha_scenario_launch_info('schedule', array(), array(''))['manual'] === true);
check('mode illisible -> tout null', jeedom2ha_scenario_launch_info('autre', array(), '') === array('mode' => null, 'has_trigger' => null, 'has_schedule' => null, 'manual' => null));

echo "Champs published / is_new\n";
check('publication non configurée : aucun champ', jeedom2ha_scenario_publication_fields(20, null, null) === array());
check('publié et connu', jeedom2ha_scenario_publication_fields(20, array(20), array(20, 21)) === array('published' => true, 'is_new' => false));
check('non publié et nouveau', jeedom2ha_scenario_publication_fields(22, array(20), array(20, 21)) === array('published' => false, 'is_new' => true));
$rows = array(array('id' => 20, 'name' => 'A'), array('id' => 21, 'name' => 'B'));
check('lignes inchangées si non configuré', jeedom2ha_scenario_publication_rows($rows, null, null) === $rows);
check('lignes enrichies', jeedom2ha_scenario_publication_rows($rows, array(21), array(21))[1] === array('id' => 21, 'name' => 'B', 'published' => true, 'is_new' => false));

echo "Installation neuve ?\n";
check('configuration vierge et data/ vide -> neuve', jeedom2ha_scenario_publication_is_fresh_install(array('active', 'deamonAutoMode'), array('.', '..')) === true);
check('une clé du plugin -> a servi', jeedom2ha_scenario_publication_is_fresh_install(array('active', 'mqttHost'), array()) === false);
check('un fichier dans data/ -> a servi', jeedom2ha_scenario_publication_is_fresh_install(array('active'), array('.', '..', 'jeedom2ha_cache.json')) === false);
check('data/ illisible -> a servi', jeedom2ha_scenario_publication_is_fresh_install(array(), null) === false);

echo "Migration\n";
$store = array();
$writes = array();
$r = jeedom2ha_scenario_publication_migrate('update', memory_deps($store, array(22, 20, 21), false, $writes));
check('mise à jour, clé absente -> tous les lisibles publiés', $r['status'] === 'migrated' && $store['publishedScenarios'] === '[20,21,22]');
check('mise à jour -> tous connus', $store['knownScenarioIds'] === '[20,21,22]');
check('marqueur posé en dernier', $store['scenarioPublicationSchema'] === '1' && end($writes) === 'scenarioPublicationSchema');
$writes = array();
$r = jeedom2ha_scenario_publication_migrate('update', memory_deps($store, array(20, 21, 22, 23), false, $writes));
check('idempotente : seconde exécution sans écriture ni nouveau scénario publié', $r['status'] === 'done' && $writes === array()
    && $store['publishedScenarios'] === '[20,21,22]');
$r = jeedom2ha_scenario_publication_migrate('install', memory_deps($store, array(20, 21, 22, 23), true, $writes));
check('réactivation (install) après migration : rien ne change', $r['status'] === 'done' && $writes === array());

$store = array('publishedScenarios' => '[21]', 'knownScenarioIds' => '[21,22]');
$writes = array();
$r = jeedom2ha_scenario_publication_migrate('update', memory_deps($store, array(20, 21, 22), false, $writes));
check('clé présente -> inchangée', $r['status'] === 'kept' && $store['publishedScenarios'] === '[21]' && $store['knownScenarioIds'] === '[21,22]'
    && $writes === array('scenarioPublicationSchema'));

$store = array();
$r = jeedom2ha_scenario_publication_migrate('install', memory_deps($store, array(20, 21), true));
check('installation neuve -> listes vides, aucun scénario publié', $r['status'] === 'fresh' && $store['publishedScenarios'] === '[]'
    && $store['knownScenarioIds'] === '[]' && $store['scenarioPublicationSchema'] === '1');
check('installation neuve : clé présente (\'[]\' n\'est pas une clé absente)', jeedom2ha_scenario_id_list(json_decode($store['publishedScenarios'], true)) === array());

$store = array();
$r = jeedom2ha_scenario_publication_migrate('install', memory_deps($store, array(20, 21), false));
check('install sur une installation qui a servi -> traitée en mise à jour', $r['status'] === 'migrated' && $store['publishedScenarios'] === '[20,21]');

$store = array();
$writes = array();
$r = jeedom2ha_scenario_publication_migrate('update', memory_deps($store, null, false, $writes));
check('lecture incomplète -> reportée, rien écrit', $r['status'] === 'deferred' && $writes === array() && $store === array());

$store = array('scenarioPublicationSchema' => '1');
$r = jeedom2ha_scenario_publication_migrate('update', memory_deps($store, array(20)));
check('marqueur sans liste (clé effacée) -> migrée de nouveau, rien ne disparaît', $r['status'] === 'migrated' && $store['publishedScenarios'] === '[20]');

echo "Choix de l'utilisateur\n";
$apply = jeedom2ha_scenario_publication_apply(array(20, 21), array(20, 21), array(22), array(21));
check('publier / retirer, les deux deviennent connus', $apply === array('published' => array(20, 22), 'known' => array(20, 21, 22)));

$store = array('publishedScenarios' => '[20,21]', 'knownScenarioIds' => '[20,21]', 'scenarioPublicationSchema' => '1');
$saved = jeedom2ha_save_scenario_publication('[22]', '[21]', memory_deps($store, array(20, 21, 22)));
check('enregistré', $store['publishedScenarios'] === '[20,22]' && $store['knownScenarioIds'] === '[20,21,22]'
    && $saved['ids_to_publish'] === array(22) && $saved['ids_to_unpublish'] === array(21));

$store = array();
jeedom2ha_save_scenario_publication('[]', '[21]', memory_deps($store, array(20, 21, 22)));
check('clé absente : migration d\'abord (rien d\'autre ne disparaît)', $store['publishedScenarios'] === '[20,22]' && $store['scenarioPublicationSchema'] === '1');

$errors = array(
    'liste mal formée' => array('12', '[]'),
    'rien à modifier' => array('[]', '[]'),
    'publié et retiré à la fois' => array('[20]', '[20]'),
    'scénario introuvable' => array('[99]', '[]'),
);
foreach ($errors as $label => $params) {
    $store = array('publishedScenarios' => '[20]', 'knownScenarioIds' => '[20]', 'scenarioPublicationSchema' => '1');
    $before = $store;
    $thrown = false;
    try {
        jeedom2ha_save_scenario_publication($params[0], $params[1], memory_deps($store, array(20, 21)));
    } catch (Exception $e) {
        $thrown = true;
    }
    check("refusé sans écriture : {$label}", $thrown && $store === $before);
}
$store = array();
$thrown = false;
try {
    jeedom2ha_save_scenario_publication('[20]', '[]', memory_deps($store, null));
} catch (Exception $e) {
    $thrown = true;
}
check('lecture incomplète : refusé sans écriture', $thrown && $store === array());

// ---------------------------------------------------------------------------------------------------------------
// Méthodes de la classe (extraites du VRAI fichier, dans une fausse classe, avec un faux `config`).
// ---------------------------------------------------------------------------------------------------------------
echo "Classe : enrichissement de la topologie\n";
$class = file_get_contents($root . '/core/class/jeedom2ha.class.php');
function extract_method($text, $name) {
    $start = strpos($text, 'public static function ' . $name . '(');
    if ($start === false) { return null; }
    $doc = strrpos(substr($text, 0, $start), '/**');
    $end = strpos($text, "\n  }\n", $start);
    return $end === false ? null : substr($text, $start, $end - $start) . "\n  }\n";
}
$methods = '';
foreach (array('readScenarioLaunchInfo', 'applyScenarioLaunchInfo', 'applyScenarioPublication') as $name) {
    $code = extract_method($class, $name);
    check("méthode {$name} présente", $code !== null);
    $methods .= (string) $code;
}
check('la classe charge les fonctions pures', strpos($class, "require_once __DIR__  . '/../php/jeedom2ha_scenario_publication.php';") !== false);
check('getFullTopology : groupe et mode puis publication ajoutés après buildScenariosPayload',
    preg_match('/buildScenariosPayload\(class_exists\(\'scenario\'\) \? scenario::all\(\) : null\);\s*\n(?:\s*\/\/[^\n]*\n)*\s*\$scenariosPayload\[\'scenarios\'\] = self::applyScenarioLaunchInfo\([^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*\$scenariosPayload\[\'scenarios\'\] = self::applyScenarioPublication\(\$scenariosPayload\[\'scenarios\'\]\);\s*\n\s*\$result\[\'scenarios\'\] = \$scenariosPayload\[\'scenarios\'\];/', $class) === 1);

class config {
    public static $values = array();
    public static function byKey($key, $plugin = 'core', $default = '', $fresh = false) {
        return array_key_exists($key, self::$values) ? self::$values[$key] : $default;
    }
}
eval('class jeedom2ha {' . "\n" . $methods . '}');

class FakeScenario {
    private $d;
    public function __construct(array $d) { $this->d = $d; }
    public function getId() { return $this->d['id']; }
    public function getGroup() { return $this->d['group']; }
    public function getMode() { return $this->d['mode']; }
    public function getTrigger() { return $this->d['trigger']; }
    public function getSchedule() { return $this->d['schedule']; }
}
class BrokenScenario {
    public function getId() { return 23; }
    public function getMode() { throw new RuntimeException('illisible'); }
}
$scenarios = array(
    new FakeScenario(array('id' => 20, 'group' => 'Ambiances', 'mode' => 'provoke', 'trigger' => array(''), 'schedule' => '')),
    new FakeScenario(array('id' => 21, 'group' => '', 'mode' => 'schedule', 'trigger' => array(), 'schedule' => '0 7 * * *')),
    new BrokenScenario(),
);
$rows = array(array('id' => 20, 'name' => 'A', 'is_active' => true), array('id' => 21, 'name' => 'B', 'is_active' => false),
    array('id' => 23, 'name' => 'C', 'is_active' => true), array('id' => 24, 'name' => 'D', 'is_active' => true));
$out = jeedom2ha::applyScenarioLaunchInfo($rows, $scenarios);
check('groupe et mode ajoutés', $out[0] === array('id' => 20, 'name' => 'A', 'is_active' => true, 'group' => 'Ambiances', 'mode' => 'provoke',
    'has_trigger' => false, 'has_schedule' => false, 'manual' => true));
check('programmé', $out[1]['mode'] === 'schedule' && $out[1]['manual'] === false && $out[1]['group'] === '');
check('lecture en échec -> null, ligne conservée', $out[2]['mode'] === null && $out[2]['manual'] === null && $out[2]['name'] === 'C');
check('scénario absent de la seconde lecture -> null', $out[3]['mode'] === null && count($out) === 4);
check('source absente -> null partout', jeedom2ha::applyScenarioLaunchInfo($rows, null)[0]['mode'] === null);

config::$values = array();
check('publication non migrée : lignes inchangées (le démon publie comme avant)', jeedom2ha::applyScenarioPublication($rows) === $rows);
config::$values = array('publishedScenarios' => array(20), 'knownScenarioIds' => array(20, 21));
$pub = jeedom2ha::applyScenarioPublication($rows);
check('publication configurée : published / is_new', $pub[0]['published'] === true && $pub[0]['is_new'] === false
    && $pub[1]['published'] === false && $pub[1]['is_new'] === false && $pub[2]['is_new'] === true);
config::$values = array('publishedScenarios' => array(), 'knownScenarioIds' => array());
check('installation neuve : rien de publié, tout nouveau', jeedom2ha::applyScenarioPublication($rows)[0] === array('id' => 20, 'name' => 'A', 'is_active' => true, 'published' => false, 'is_new' => true));

// ---------------------------------------------------------------------------------------------------------------
// VRAIE branche ajax `saveScenarioPublication`.
// ---------------------------------------------------------------------------------------------------------------
echo "Ajax : saveScenarioPublication\n";
$ajax = file_get_contents($root . '/core/ajax/jeedom2ha.ajax.php');
$start = strpos($ajax, "if (\$action == 'saveScenarioPublication') {");
$end = $start === false ? false : strpos($ajax, "\n    else if (\$action ==", $start + 10);
check('branche saveScenarioPublication présente', $start !== false && $end !== false);
check('l\'ajax charge les fonctions pures', strpos($ajax, "require_once __DIR__ . '/../php/jeedom2ha_scenario_publication.php';") !== false);
check('relecture : même enchaînement que scanTopology (empreinte, topologie, synchro « rescan »)',
    strpos($ajax, "function _jeedom2ha_scenario_publication_rescan(): array {") !== false
    && preg_match("/function _jeedom2ha_scenario_publication_rescan\(\): array \{.*?safeDecisionFingerprint.*?getFullTopology.*?invalidateDecisionFingerprintBeforeSync.*?'\/action\/sync'.*?'X-Jeedom2ha-Sync-Mode' => 'rescan'.*?rememberDecisionFingerprintAfterSync/s", $ajax) === 1);
if ($start === false || $end === false) {
    done_and_exit();
}
$branch = substr($ajax, $start, $end - $start);

class J2haAjaxDone extends Exception {
    public $result;
    public function __construct($result) { parent::__construct('done'); $this->result = $result; }
}
class ajax {
    public static function success($result = '') { throw new J2haAjaxDone($result); }
}
$GLOBALS['j2ha_params'] = array();
$GLOBALS['j2ha_store'] = array();
$GLOBALS['j2ha_rescans'] = 0;
function init($key, $default = '') {
    return array_key_exists($key, $GLOBALS['j2ha_params']) ? $GLOBALS['j2ha_params'][$key] : $default;
}
function _jeedom2ha_scenario_publication_rescan() {
    $GLOBALS['j2ha_rescans']++;
    return array('status' => 'ok', 'scenario_availability_complete' => true);
}
// La branche appelle jeedom2ha::scenarioPublicationDeps() : méthode ajoutée à la fausse classe par une sous-classe nommée.
eval(str_replace('jeedom2ha::scenarioPublicationDeps()', 'memory_deps($GLOBALS[\'j2ha_store\'], array(20, 21, 22))', 'function run_save() { $action = "saveScenarioPublication"; try { ' . $branch . ' } catch (J2haAjaxDone $done) { return $done->result; } return "NO_RESPONSE"; }'));
check('la branche passe bien par scenarioPublicationDeps', strpos($branch, 'jeedom2ha::scenarioPublicationDeps()') !== false);

$GLOBALS['j2ha_store'] = array('publishedScenarios' => '[20,21]', 'knownScenarioIds' => '[20,21]', 'scenarioPublicationSchema' => '1');
$GLOBALS['j2ha_params'] = array('ids_to_publish' => '[22]', 'ids_to_unpublish' => '[21]');
$out = run_save();
check('réponse', is_array($out) && $out['saved'] === true && $out['ids_to_publish'] === array(22) && $out['ids_to_unpublish'] === array(21)
    && $out['rescan'] === array('status' => 'ok', 'scenario_availability_complete' => true));
check('les deux clés écrites', $GLOBALS['j2ha_store']['publishedScenarios'] === '[20,22]' && $GLOBALS['j2ha_store']['knownScenarioIds'] === '[20,21,22]');
check('relecture déclenchée une fois', $GLOBALS['j2ha_rescans'] === 1);

$GLOBALS['j2ha_params'] = array('ids_to_publish' => '[99]', 'ids_to_unpublish' => '[]');
$before = $GLOBALS['j2ha_store'];
$thrown = false;
try {
    run_save();
} catch (Exception $e) {
    $thrown = !($e instanceof J2haAjaxDone);
}
check('demande invalide : erreur, rien écrit, aucune relecture', $thrown && $GLOBALS['j2ha_store'] === $before && $GLOBALS['j2ha_rescans'] === 1);

// ---------------------------------------------------------------------------------------------------------------
// plugin_info/install.php
// ---------------------------------------------------------------------------------------------------------------
echo "install.php\n";
$install = file_get_contents($root . '/plugin_info/install.php');
check('fonctions pures chargées', strpos($install, "require_once dirname(__FILE__) . '/../core/php/jeedom2ha_scenario_publication.php';") !== false);
check('install : migration en contexte install', preg_match("/function jeedom2ha_install\(\) \{.*?jeedom2ha_migrate_scenario_publication\('install', \\\$dataDirFilesBefore\);\r?\n\}/s", $install) === 1);
check('update : migration en contexte update', preg_match("/function jeedom2ha_update\(\) \{.*?jeedom2ha_migrate_scenario_publication\('update', \\\$dataDirFilesBefore\);\r?\n\}/s", $install) === 1);
check('data/ lu AVANT sa création', preg_match("/\\\$dataDirFilesBefore = jeedom2ha_data_dir_files\(\\\$dataDir\);.*?mkdir/s", $install) === 1);
check('migration indépendante de la classe du plugin', strpos($install, 'jeedom2ha::') === false);
check('migration qui ne lève jamais', preg_match('/function jeedom2ha_migrate_scenario_publication.*?catch \(\\\\Throwable \$e\)/s', $install) === 1);

done_and_exit();
