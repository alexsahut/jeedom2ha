<?php
// ARTEFACT — Story 25.8 (AC1 à AC5, AC16) : exclusion de pièce depuis la surface, côté PHP.
//  - D1 : fonction pure de lecture / modification de `excludedObjects` (ids identiques à ceux de l'extraction) ;
//  - D2 : route `saveRoomExclusion` (seule la clé `excludedObjects`, validation stricte, aucune relecture implicite) ;
//  - `excluded` ajouté à `j2haRoomsTree` (rendu de la page avec un faux cœur Jeedom).
// Identifiants fictifs uniquement (CC-48). Exécution : php tests/test_php_story_25_8_exclusion_piece.php

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

$functionFile = $root . '/core/php/jeedom2ha_room_exclusion.php';
check('le fichier de fonctions pures existe sous core/php', is_file($functionFile));
if (!is_file($functionFile)) {
    echo "\n{$passed} réussis, {$failed} échoués\n";
    exit(1);
}
require_once $functionFile;

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

/** Règle de l'extraction, copie littérale de core/class/jeedom2ha.class.php:765-766 (appliquée à une chaîne). */
function reference_ids($csv) {
    $raw = array_filter(array_unique(array_map('trim', explode(',', $csv))), 'is_numeric');
    return array_map('intval', $raw);
}

echo "Équivalence : la règle de l'extraction est toujours celle du plugin\n";
$class = file_get_contents($root . '/core/class/jeedom2ha.class.php');
check(
    'core/class lit excludedObjects avec array_filter(array_unique(array_map(trim…))), is_numeric puis intval',
    strpos($class, "\$excludedObjectsRaw = array_filter(array_unique(array_map('trim', explode(',', config::byKey('excludedObjects', __CLASS__, '')))), 'is_numeric');") !== false
        && strpos($class, "\$excludedObjects = array_map('intval', \$excludedObjectsRaw);") !== false
);

echo "D1 — lecture : ids identiques à l'extraction pour toute la table\n";
$table = array('', '5', '5,12', ' 5 , 12 ', '5,,12', '12,5,5', 'abc,5', '7,5,999999', '-3,5', '5.0,5', '1e3,5', ',', 'abc', '05,5');
foreach ($table as $csv) {
    check('ids égaux pour ' . json_encode($csv), array_values(jeedom2ha_excluded_object_ids($csv)) === array_values(reference_ids($csv)));
}

echo "D1 — exclure / ne plus exclure (table de fixtures fictives)\n";
$cases = array(
    // [csv, id, excluded, csv attendu, changed attendu]
    array('', 5, true, '5', true),
    array('', 5, false, '', false),
    array('5', 5, true, '5', false),
    array('5', 5, false, '', true),
    array('5,12', 7, true, '5,12,7', true),
    array('5,12', 12, false, '5', true),
    array(' 5 , 12 ', 7, true, '5,12,7', true),
    array(' 5 , 12 ', 12, true, ' 5 , 12 ', false),
    array('5,,12', 7, true, '5,12,7', true),
    array('12,5,5', 5, false, '12', true),
    array('12,5,5', 5, true, '12,5,5', false),
    array('abc,5', 7, true, 'abc,5,7', true),
    array('abc,5', 5, false, 'abc', true),
    array('7,5,999999', 5, false, '7,999999', true),
    array('7,5,999999', 999999, false, '7,5', true),
    array('-3,5', 3, true, '-3,5,3', true),
    array('-3,5', 5, false, '-3', true),
    array('5.0,5', 5, true, '5.0,5', false),
    array('5.0,5', 5, false, '', true),
    array('5.0,5', 6, false, '5.0,5', false),
);
foreach ($cases as $c) {
    list($csv, $id, $excluded, $expectedCsv, $expectedChanged) = $c;
    $r = jeedom2ha_toggle_excluded_object($csv, $id, $excluded);
    $label = json_encode($csv) . ($excluded ? ' + ' : ' − ') . $id;
    check($label . ' → ' . json_encode($expectedCsv) . ' changed=' . ($expectedChanged ? '1' : '0'), $r['csv'] === $expectedCsv && $r['changed'] === $expectedChanged);
    check($label . ' : ids = règle de l\'extraction sur la nouvelle chaîne', array_values($r['ids']) === array_values(reference_ids($r['csv'])));
    $again = jeedom2ha_toggle_excluded_object($r['csv'], $id, $excluded);
    check($label . ' : rejouer ne change plus rien', $again['changed'] === false && $again['csv'] === $r['csv']);
}
$one = jeedom2ha_toggle_excluded_object('5,12', 7, true);
check('forme de la sortie : csv, changed, ids', array_keys($one) === array('csv', 'changed', 'ids') && is_string($one['csv']) && is_bool($one['changed']) && is_array($one['ids']));
check('ids : entiers', $one['ids'] === array(5, 12, 7));

// Le CSV rendu est celui lu par le plugin : mêmes jetons numériques retenus.
$rt = jeedom2ha_toggle_excluded_object('abc,5,-3', 9, true);
check('autres jetons conservés dans leur ordre, jeton visé en fin', $rt['csv'] === 'abc,5,-3,9');

echo "D2 — route : seule la clé excludedObjects, jamais d'écriture sans changement\n";
function make_io($csv, $known) {
    $io = new stdClass();
    $io->csv = $csv;
    $io->saves = array();
    $io->logs = array();
    $io->daemon = 0;
    $io->objectExists = function ($id) use ($known) { return in_array($id, $known, true); };
    $io->read = function () use ($io) { return $io->csv; };
    $io->save = function ($value) use ($io) { $io->saves[] = array('excludedObjects', $value); $io->csv = $value; };
    $io->log = function ($level, $message) use ($io) { $io->logs[] = array($level, $message); };
    return $io;
}
function call_route($objectId, $excluded, $io) {
    return jeedom2ha_save_room_exclusion($objectId, $excluded, $io->objectExists, $io->read, $io->save, $io->log);
}

$io = make_io('5,12,999999,abc', array(5, 7, 12));
$r = call_route('7', '1', $io);
check('exclure : réponse { object_id, excluded, changed, excluded_objects }', $r === array('object_id' => 7, 'excluded' => true, 'changed' => true, 'excluded_objects' => array(5, 12, 999999, 7)));
check('exclure : une seule écriture, sur la seule clé excludedObjects', $io->saves === array(array('excludedObjects', '5,12,999999,abc,7')));
$r = call_route('7', '1', $io);
check('rejouer : changed=false, aucune écriture de plus', $r['changed'] === false && count($io->saves) === 1);
$r = call_route('7', '0', $io);
check('ne plus exclure : chaîne finale identique à la chaîne de départ (reprise sans perte)', $io->csv === '5,12,999999,abc' && $r['changed'] === true && $r['excluded'] === false && count($io->saves) === 2);
check('ne plus exclure : les deux pièces initiales restent exclues', in_array(5, $r['excluded_objects'], true) && in_array(12, $r['excluded_objects'], true) && !in_array(7, $r['excluded_objects'], true));
$r = call_route('7', '0', $io);
check('rejouer « ne plus exclure » : changed=false, aucune écriture', $r['changed'] === false && count($io->saves) === 2);

echo "Journal : une ligne info, sans la chaîne complète\n";
check('quatre lignes de journal (une par appel)', count($io->logs) === 4);
check('niveau info', $io->logs[0][0] === 'info');
check('format [CONFIG] saveRoomExclusion: objectId=<id> excluded=<0|1> changed=<0|1>', $io->logs[0][1] === '[CONFIG] saveRoomExclusion: objectId=7 excluded=1 changed=1' && $io->logs[1][1] === '[CONFIG] saveRoomExclusion: objectId=7 excluded=1 changed=0');
$allLogs = json_encode($io->logs);
check('jamais la chaîne complète dans le journal', strpos($allLogs, '999999') === false && strpos($allLogs, 'abc') === false);

echo "D2 — entrées hostiles : erreur, aucune écriture, aucune ligne de journal, aucun appel au démon\n";
$hostileIds = array(0, '0', -1, '-1', '', 'abc', '1e3', '12;5', '07', ' 7', '7 ', 7.5, null, array(7), '99999999999', '999');
foreach ($hostileIds as $bad) {
    $io = make_io('5', array(5, 7));
    $threw = false;
    try { call_route($bad, '1', $io); } catch (Exception $e) { $threw = true; }
    check('objectId refusé : ' . json_encode($bad), $threw && $io->saves === array() && $io->logs === array() && $io->csv === '5');
}
foreach (array('', '2', 'true', 'oui', ' 1', '1 ', '01', null, 1, true, array('1')) as $bad) {
    $io = make_io('5', array(5, 7));
    $threw = false;
    try { call_route('7', $bad, $io); } catch (Exception $e) { $threw = true; }
    check('excluded refusé : ' . json_encode($bad), $threw && $io->saves === array() && $io->logs === array());
}
$io = make_io('5', array(5));
$threw = false;
try { call_route('8', '1', $io); } catch (Exception $e) { $threw = true; }
check('objet Jeedom inconnu : erreur sans écriture ni journal', $threw && $io->saves === array() && $io->logs === array());

echo "Journal de refus : l'entrée brute n'y figure jamais\n";
$io = make_io('5', array(5));
try { call_route("12;5<script>", '1', $io); } catch (Exception $e) { $message = $e->getMessage(); }
check('le message d\'erreur ne cite pas l\'entrée brute', isset($message) && strpos($message, 'script') === false && strpos($message, '12;5') === false);

echo "AC2 / AC4 — le code de la route : pas de démon, pas de relecture, une seule clé écrite\n";
$ajax = file_get_contents($root . '/core/ajax/jeedom2ha.ajax.php');
$start = strpos($ajax, "else if (\$action == 'saveRoomExclusion')");
check('branche saveRoomExclusion présente dans l\'ajax', $start !== false);
$end = $start === false ? false : strpos($ajax, "\n    else if (\$action ==", $start + 10);
if ($end === false && $start !== false) { $end = strpos($ajax, "\n    else {", $start + 10); }
$branch = $start === false ? '' : code_only('<?php ' . substr($ajax, $start, $end - $start));
check('la branche appelle la fonction pure', strpos($branch, 'jeedom2ha_save_room_exclusion(') !== false);
foreach (array('callDaemon', 'scanTopology', 'getFullTopology', 'syncStateListeners', 'excludedPlugins', 'confidencePolicy', 'publishedScope') as $forbidden) {
    check('la branche ne contient pas « ' . $forbidden . ' »', strpos($branch, $forbidden) === false);
}
check('la branche écrit au cœur une seule fois, sur la seule clé excludedObjects', substr_count($branch, 'config::save(') === 1 && strpos($branch, "config::save('excludedObjects', ") !== false);
check('la branche ne cite aucune autre clé de configuration', preg_match_all("/config::(?:save|byKey)\\('([A-Za-z]+)'/", $branch, $m) === 2 && count(array_unique($m[1])) === 1 && $m[1][0] === 'excludedObjects');
$functions = code_only(file_get_contents($functionFile));
foreach (array('callDaemon', 'scanTopology', 'getFullTopology', 'syncStateListeners', 'excludedPlugins', 'confidencePolicy', 'core.inc.php', 'config::', 'jeeObject', 'log::') as $forbidden) {
    check('le fichier de fonctions ne contient pas « ' . $forbidden . ' » (hors commentaires)', strpos($functions, $forbidden) === false);
}
check('les autres actions de l\'ajax sont conservées (saveFilteringConfig, scanTopology)', strpos($ajax, "\$action == 'saveFilteringConfig'") !== false && strpos($ajax, "\$action == 'scanTopology'") !== false);
check('require_once du fichier de fonctions dans l\'ajax', strpos($ajax, "jeedom2ha_room_exclusion.php'") !== false);

echo "AC5 — `excluded` dans j2haRoomsTree (rendu de la page, faux cœur Jeedom)\n";
$fixture = array(
    'objects' => array(
        array('id' => 5, 'name' => 'Pièce fictive A', 'father_id' => null, 'display' => array()),
        array('id' => 7, 'name' => 'Pièce fictive B', 'father_id' => null, 'display' => array()),
        array('id' => 12, 'name' => 'Pièce fictive C', 'father_id' => null, 'display' => array()),
        array('id' => 20, 'name' => 'Pièce fictive D', 'father_id' => null, 'display' => array()),
    ),
    'eqlogics' => array(
        '5' => array(array('id' => 501, 'name' => 'Eq 501')),
        '7' => array(array('id' => 701, 'name' => 'Eq 701')),
        '12' => array(array('id' => 1201, 'name' => 'Eq 1201')),
        '20' => array(array('id' => 2001, 'name' => 'Eq 2001')),
        'null' => array(array('id' => 9001, 'name' => 'Eq sans objet')),
    ),
    'config' => array('excludedObjects' => ' 5 , 12 ,abc,0'),
    'doc' => 'https://doc.example.test/plugin',
);
$file = tempnam(sys_get_temp_dir(), 'j2ha');
file_put_contents($file, json_encode($fixture));
$out = json_decode(shell_exec('php ' . escapeshellarg($root . '/tests/unit/helpers/render_page.php') . ' ' . escapeshellarg($file)), true);
unlink($file);
check('le rendu de la page réussit', is_array($out) && isset($out['vars']['j2haRoomsTree']));
$rooms = $out['vars']['j2haRoomsTree'];
$byId = array();
foreach ($rooms as $room) { $byId[$room['object_id']] = $room; }
check('pièce 5 : excluded=true', $byId[5]['excluded'] === true);
check('pièce 12 : excluded=true', $byId[12]['excluded'] === true);
check('pièce 7 : excluded=false', $byId[7]['excluded'] === false);
check('pièce 20 : excluded=false', $byId[20]['excluded'] === false);
check('« Sans pièce » : excluded=false même si « 0 » figure dans la chaîne', $byId[0]['excluded'] === false);
check('champs existants inchangés (noms et types), excluded ajouté en fin', array_keys($byId[5]) === array('object_id', 'object_name', 'parent_number', 'father_id', 'icon_classes', 'color', 'equipments', 'excluded') && is_int($byId[5]['object_id']) && is_string($byId[5]['object_name']));
check('équipements inchangés', array_keys($byId[5]['equipments'][0]) === array('eq_id', 'eq_name', 'enabled', 'eq_type'));

echo "\n{$passed} réussis, {$failed} échoués\n";
exit($failed > 0 ? 1 : 0);
