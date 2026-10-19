<?php
// ARTEFACT — Story 25.9 (AC1, AC3, AC5, AC6, AC10) : page de configuration — « Plugins exclus » en liste à cocher des plugins présents
// (même clé `excludedPlugins`, même format), retrait du champ « Pièces exclues » au profit d'un renvoi vers la surface, et
// `saveFilteringConfig` qui n'écrit plus (ni n'efface) `excludedObjects`. Fonctions pures + rendu de la page avec un faux cœur
// Jeedom. Plugins et identifiants fictifs uniquement (CC-48). Exécution : php tests/test_php_story_25_9_configuration.php

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

/** Code PHP sans commentaires (les commentaires citent légitimement les clés interdites). */
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

$functionFile = $root . '/core/php/jeedom2ha_excluded_plugins.php';
check('le fichier de fonctions pures existe sous core/php', is_file($functionFile));
if (!is_file($functionFile)) {
    echo "\n{$passed} réussis, {$failed} échoués\n";
    exit(1);
}
require_once $functionFile;

echo "AC1 — liste D1 : plugins présents (hors jeedom2ha), cochés selon excludedPlugins, absents encore exclus conservés\n";
$names = array('plugin_gamma' => 'Gamma', 'plugin_alpha' => 'Alpha', 'plugin_beta' => 'Beta');
$list = jeedom2ha_build_excluded_plugins_list($names, 'plugin_beta,plugin_gone');
$summary = array_map(function ($item) { return $item['id'] . ':' . ($item['checked'] ? '1' : '0') . ':' . ($item['absent'] ? 'absent' : 'present'); }, $list);
check('ordre : par nom affiché, puis les absents exclus', $summary === array('plugin_alpha:0:present', 'plugin_beta:1:present', 'plugin_gamma:0:present', 'plugin_gone:1:absent'));
check('chaque entrée porte id, name, checked, absent', array_keys($list[0]) === array('id', 'name', 'checked', 'absent') && $list[0]['name'] === 'Alpha');
check('un plugin absent est nommé par son identifiant', $list[3]['name'] === 'plugin_gone');
check('jeedom2ha n\'apparaît pas (présent dans la table ou dans excludedPlugins)', count(array_filter(jeedom2ha_build_excluded_plugins_list(array('jeedom2ha' => 'Jeedom2HA', 'plugin_alpha' => 'Alpha'), 'jeedom2ha'), function ($i) { return $i['id'] === 'jeedom2ha'; })) === 0);
$sorted = jeedom2ha_build_excluded_plugins_list(array('p1' => 'Zèbre', 'p2' => 'alpha', 'p3' => 'Éclair', 'p4' => 'Beta', 'p5' => 'eclat'), '');
check('tri sans tenir compte de la casse ni des accents', array_map(function ($i) { return $i['id']; }, $sorted) === array('p2', 'p4', 'p3', 'p5', 'p1'));
check('une table vide et aucun plugin exclu : liste vide', jeedom2ha_build_excluded_plugins_list(array(), '') === array());
check('doublons et espaces : un seul élément par plugin exclu absent', count(jeedom2ha_build_excluded_plugins_list(array(), ' plugin_gone , plugin_gone,,plugin_other ')) === 2);

echo "AC1 — rendu : échappé, libellé = nom puis identifiant, état « absent de Jeedom », groupe nommé\n";
$hostile = jeedom2ha_build_excluded_plugins_list(array('plugin_html' => '<img src=x onerror=alert(1)>', 'plugin_alpha' => 'Alpha'), 'plugin_alpha,"><script>x</script>');
$html = jeedom2ha_render_excluded_plugins_checklist($hostile);
check('aucune injection HTML possible par un nom de plugin ni par un identifiant exclu', strpos($html, '<img') === false && strpos($html, '<script') === false && strpos($html, '&lt;img src=x onerror=alert(1)&gt;') !== false);
check('une vraie case à cocher et un label associé par plugin', substr_count($html, 'type="checkbox"') === 3 && substr_count($html, '<label for="') === 3);
check('aucune case ne porte configKey (le cœur ne les enregistre pas)', strpos($html, 'configKey') === false);
$ok = jeedom2ha_render_excluded_plugins_checklist($list);
check('plugin_beta est coché, plugin_alpha ne l\'est pas', preg_match('/value="plugin_beta"[^>]*checked/', $ok) === 1 && preg_match('/value="plugin_alpha"[^>]*checked/', $ok) === 0);
check('libellé : nom affiché suivi de l\'identifiant en texte secondaire', preg_match('/Alpha<\/span> <small class="text-muted">\(plugin_alpha\)<\/small>/', $ok) === 1);
check('plugin absent : coché, mention « (absent de Jeedom) »', preg_match('/value="plugin_gone"[^>]*checked/', $ok) === 1 && strpos($ok, '{{(absent de Jeedom)}}') !== false);
check('l\'état initial de chaque case est consigné (data-initial)', preg_match_all('/data-initial="1"/', $ok) === 2 && preg_match_all('/data-initial="0"/', $ok) === 2);
check('groupe accessible : role="group" nommé par le libellé « Plugins exclus »', strpos($ok, 'role="group"') !== false && strpos($ok, 'aria-labelledby="lbl_excludedPlugins"') !== false);
check('liste bornée en hauteur, défilement vertical seulement', strpos($ok, 'overflow-y:auto') !== false && strpos($ok, 'overflow-x:hidden') !== false);
check('aide : « Les équipements des plugins cochés ne sont pas publiés dans Home Assistant. »', strpos($ok, '{{Les équipements des plugins cochés ne sont pas publiés dans Home Assistant.}}') !== false);
check('sans plugin : « Aucun plugin avec des équipements. »', strpos(jeedom2ha_render_excluded_plugins_checklist(array()), '{{Aucun plugin avec des équipements.}}') !== false);
check('aucun terme technique « eq_type_name » dans un libellé visible', stripos($ok, 'eq_type_name') === false);

echo "AC3 — équivalence avec l'extraction : ce que la page montre coché est ce que le plugin exclut\n";
$class = file_get_contents($root . '/core/class/jeedom2ha.class.php');
check('core/class lit excludedPlugins avec array_filter(array_unique(array_map(trim…)))', strpos($class, "\$excludedPlugins = array_filter(array_unique(array_map('trim', explode(',', config::byKey('excludedPlugins', __CLASS__, '')))));") !== false);
function reference_plugin_ids($csv) {
    return array_filter(array_unique(array_map('trim', explode(',', $csv))));
}
$table = array('', 'plugin_a', 'plugin_a,plugin_b', ' plugin_a , plugin_b ', 'plugin_a,plugin_a', ',,plugin_a,,', '0', 'plugin_a,0,plugin_b', 'Plugin_A,plugin_a');
foreach ($table as $csv) {
    $expected = array_values(reference_plugin_ids($csv));
    check('ids = règle de l\'extraction pour ' . json_encode($csv), array_values(jeedom2ha_excluded_plugin_ids($csv)) === $expected);
    $checked = array();
    foreach (jeedom2ha_build_excluded_plugins_list(array('plugin_a' => 'A', 'plugin_b' => 'B'), $csv) as $item) {
        if ($item['checked']) { $checked[] = $item['id']; }
    }
    sort($checked);
    $wanted = $expected;
    sort($wanted);
    check('ensemble coché = ensemble exclu pour ' . json_encode($csv), $checked === $wanted);
}

echo "AC6 — saveFilteringConfig : excludedPlugins et confidencePolicy seulement, excludedObjects ni écrit ni effacé\n";
$saves = array();
$logs = array();
$save = function ($key, $value) use (&$saves) { $saves[] = array($key, $value); };
$log = function ($level, $message) use (&$logs) { $logs[] = array($level, $message); };
jeedom2ha_save_filtering_config(array('excludedPlugins' => 'plugin_a,plugin_b', 'excludedObjects' => '7', 'confidencePolicy' => 'sure_only'), $save, $log);
check('avec un paramètre excludedObjects (ancienne page ouverte) : jamais écrit', $saves === array(array('excludedPlugins', 'plugin_a,plugin_b'), array('confidencePolicy', 'sure_only')));
$saves = array();
jeedom2ha_save_filtering_config(array('excludedPlugins' => '', 'excludedObjects' => '', 'confidencePolicy' => 'sure_probable'), $save, $log);
check('avec excludedObjects vide : jamais effacé', array_map(function ($s) { return $s[0]; }, $saves) === array('excludedPlugins', 'confidencePolicy'));
$saves = array();
jeedom2ha_save_filtering_config(array('excludedPlugins' => 'plugin_a'), $save, $log);
check('sans paramètre excludedObjects : jamais effacé, politique par défaut', $saves === array(array('excludedPlugins', 'plugin_a'), array('confidencePolicy', 'sure_probable')));
$saves = array();
jeedom2ha_save_filtering_config(array('excludedPlugins' => 'plugin_a', 'confidencePolicy' => 'valeur-inconnue'), $save, $log);
check('politique inconnue : repli sur sure_probable (comportement conservé)', $saves[1] === array('confidencePolicy', 'sure_probable'));
$saves = array();
jeedom2ha_save_filtering_config(array(), $save, $log);
check('requête vide : excludedPlugins vidé comme avant, rien d\'autre', $saves === array(array('excludedPlugins', ''), array('confidencePolicy', 'sure_probable')));
check('aucune ligne de journal ne mentionne excludedObjects', strpos(json_encode($logs), 'excludedObjects') === false && count($logs) === 5);
check('journal : [CONFIG] saveFilteringConfig: excludedPlugins="…" confidencePolicy="…"', $logs[0] === array('info', '[CONFIG] saveFilteringConfig: excludedPlugins="plugin_a,plugin_b" confidencePolicy="sure_only"'));
$ajax = file_get_contents($root . '/core/ajax/jeedom2ha.ajax.php');
$start = strpos($ajax, "else if (\$action == 'saveFilteringConfig')");
$end = $start === false ? false : strpos($ajax, "\n    else if (\$action ==", $start + 10);
$branch = ($start === false || $end === false) ? '' : code_only('<?php ' . substr($ajax, $start, $end - $start));
check('branche saveFilteringConfig trouvée et réduite à l\'appel de la fonction pure', $branch !== '' && strpos($branch, 'jeedom2ha_save_filtering_config(') !== false);
check('la branche ne lit ni ne cite excludedObjects', strpos($branch, 'excludedObjects') === false);
check('la branche ne transmet que excludedPlugins et confidencePolicy', preg_match_all("/'(excluded[A-Za-z]*|confidencePolicy)'/", $branch, $m) && array_values(array_unique($m[1])) === array('excludedPlugins', 'confidencePolicy'));
check('require_once du fichier de fonctions dans l\'ajax', strpos($ajax, "jeedom2ha_excluded_plugins.php'") !== false);

echo "AC10 — la route de 25.8 reste le seul écrivain d'excludedObjects\n";
$writers = 0;
$rii = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root . '/core', FilesystemIterator::SKIP_DOTS));
foreach ($rii as $file) {
    if (substr($file->getFilename(), -4) !== '.php') { continue; }
    $writers += substr_count(code_only(file_get_contents($file->getPathname())), "config::save('excludedObjects'");
}
check('une seule occurrence de config::save(\'excludedObjects\' dans core/ (la route saveRoomExclusion)', $writers === 1);
check('elle est dans la branche saveRoomExclusion', strpos($ajax, "config::save('excludedObjects'") > strpos($ajax, "\$action == 'saveRoomExclusion'"));

echo "AC5 — page de configuration rendue (faux cœur Jeedom) : plus de champ « Pièces exclues », renvoi vers la surface\n";
$config = file_get_contents($root . '/plugin_info/configuration.php');
check('grep excludedObjects plugin_info/configuration.php ne renvoie rien', strpos($config, 'excludedObjects') === false);

function render_configuration($root, $fixture) {
    $tmp = sys_get_temp_dir() . '/j2ha-cfg-' . getmypid() . '-' . mt_rand();
    $plugin = $tmp . '/plugins/jeedom2ha';
    foreach (array('plugin_info', 'core/php', 'desktop/php') as $dir) { mkdir($plugin . '/' . $dir, 0777, true); }
    mkdir($tmp . '/core/php', 0777, true);
    copy($root . '/plugin_info/configuration.php', $plugin . '/plugin_info/configuration.php');
    foreach (glob($root . '/core/php/*.php') as $file) { copy($file, $plugin . '/core/php/' . basename($file)); }
    copy($root . '/desktop/php/jeedom2ha_overview_helpers.php', $plugin . '/desktop/php/jeedom2ha_overview_helpers.php');
    file_put_contents($tmp . '/fixture.json', json_encode($fixture));
    file_put_contents($tmp . '/core/php/core.inc.php', '<?php
$GLOBALS["j2ha_fixture"] = json_decode(file_get_contents(' . var_export($tmp . '/fixture.json', true) . '), true);
class J2haFakeEq { private $t; public function __construct($t) { $this->t = $t; } public function getEqType_name() { return $this->t; } }
class eqLogic { public static function all() { return array_map(function ($t) { return new J2haFakeEq($t); }, $GLOBALS["j2ha_fixture"]["eq_types"]); } }
class J2haFakePlugin { private $id; public function __construct($id) { $this->id = $id; } public function getName() { $n = $GLOBALS["j2ha_fixture"]["plugin_names"]; if (!isset($n[$this->id])) { throw new Exception("introuvable"); } return $n[$this->id]; } }
class plugin { public static function byId($id) { return new J2haFakePlugin($id); } }
class config { public static function byKey($key, $plugin = "core", $default = "") { $c = $GLOBALS["j2ha_fixture"]["config"]; return array_key_exists($key, $c) ? $c[$key] : $default; } }
function isConnect($right = "") { return true; }
function include_file() {}
');
    $html = shell_exec('php ' . escapeshellarg($plugin . '/plugin_info/configuration.php') . ' 2>&1');
    shell_exec('rm -rf ' . escapeshellarg($tmp));
    return (string) $html;
}
$fixture = array(
    'eq_types' => array('plugin_alpha', 'plugin_beta', 'plugin_beta', 'plugin_gamma', 'jeedom2ha', 'plugin_html'),
    'plugin_names' => array('plugin_alpha' => 'Alpha', 'plugin_beta' => 'Beta', 'plugin_gamma' => 'Gamma', 'plugin_html' => '<img src=x onerror=alert(1)>'),
    'config' => array('excludedPlugins' => 'plugin_beta,plugin_gone', 'excludedObjects' => '5,12,abc,999999'),
);
$page = render_configuration($root, $fixture);
check('la page se rend (faux cœur)', strpos($page, 'Filtrage &amp; Publication') !== false || strpos($page, 'Filtrage') !== false);
check('aucun élément .configKey[data-l1key=excludedObjects] ni champ de saisie des pièces', strpos($page, 'excludedObjects') === false && strpos($page, '{{Pièces exclues}}') === false);
check('« Sauvegarder » du cœur n\'écrit plus excludedObjects : plus aucun configKey ne porte la clé', preg_match('/data-l1key="excludedObjects"/', $page) === 0);
check('renvoi : texte, lien vers la page du plugin', strpos($page, '{{Pièces exclues : elles se règlent depuis la page du plugin (menu « ⋯ » d\'une carte de pièce, ou détail de la pièce).}}') !== false && strpos($page, 'index.php?v=d&amp;m=jeedom2ha&amp;p=jeedom2ha') !== false);
check('le nombre de pièces exclues est calculé depuis la clé (« 3 pièces exclues », sans noms)', strpos($page, '3 {{pièces exclues}}') !== false && strpos($page, 'Pièce fictive') === false);
$one = render_configuration($root, array_merge($fixture, array('config' => array('excludedPlugins' => '', 'excludedObjects' => '5'))));
check('« 1 pièce exclue » au singulier', strpos($one, '1 {{pièce exclue}}') !== false);
$none = render_configuration($root, array_merge($fixture, array('config' => array('excludedPlugins' => '', 'excludedObjects' => ''))));
check('aucune pièce exclue : pas de nombre, mais le renvoi reste', strpos($none, '{{Pièces exclues : elles se règlent depuis la page du plugin') !== false && strpos($none, '{{pièce exclue}}') === false && strpos($none, '{{pièces exclues}}') === false);
check('liste : alpha, beta (cochée), gamma, plugin_html échappé, plugin_gone coché « absent de Jeedom »', preg_match('/value="plugin_beta"[^>]*checked/', $page) === 1 && preg_match('/value="plugin_gone"[^>]*checked/', $page) === 1 && strpos($page, '<img src=x') === false && strpos($page, 'jeedom2ha</small>') === false);
check('champ porteur masqué configKey excludedPlugins, valeur chargée conservée verbatim', preg_match('/<input type="hidden" class="configKey" data-l1key="excludedPlugins" value="plugin_beta,plugin_gone"/', $page) === 1);
check('« Politique de publication » et « Appliquer… » sont conservés', strpos($page, 'data-l1key="confidencePolicy"') !== false && strpos($page, 'id="bt_applyAndRescan"') !== false);
check('plus d\'exemple « virtual,zwave,rfxcom » ni de texte libre pour les plugins', strpos($page, 'virtual,zwave,rfxcom') === false && strpos($page, '(eq_type_name)') === false);

echo "\n{$passed} réussis, {$failed} échoués\n";
exit($failed > 0 ? 1 : 0);
