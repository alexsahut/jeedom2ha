<?php
// ARTEFACT — Story 24.2 : action AJAX d'administrateur `getDecisionExport` (relais borné de la route
// interne du démon) et payload de sync. Fonctions pures et lecture du source, sans cœur Jeedom.
// Exécution : php tests/unit/test_story_24_2_php_export.php

define('JEEDOM2HA_AJAX_FUNCTIONS_ONLY', true);
require_once __DIR__ . '/../../core/ajax/jeedom2ha.ajax.php';

$passed = 0; $failed = 0;

function ok($label, $cond, $detail = '') {
    global $passed, $failed;
    if ($cond) { $passed++; echo "  ✔ {$label}\n"; }
    else { $failed++; echo "  ✖ {$label} {$detail}\n"; }
}
function throws_msg_contains($label, callable $fn, $fragment) {
    try { $fn(); ok($label, false, 'aucune exception'); }
    catch (\Throwable $e) { ok($label, strpos($e->getMessage(), $fragment) !== false, $e->getMessage()); }
}

$document = array(
    'schema_version' => 1,
    'totals' => array('equipments' => 1, 'commands' => 0, 'scenarios' => 0),
    'equipments' => array(
        array('eq_id' => 1, 'overrides' => array('publication' => null, 'types' => array()), 'commands' => array()),
        array('eq_id' => 2, 'overrides' => array('publication' => 'exclude', 'types' => array('70' => 'switch')), 'commands' => array()),
    ),
    'scenarios' => array(),
);

echo "\n24.2 / payload du démon rendu tel quel\n";
$payload = _jeedom2ha_decision_export_payload(array('status' => 'ok', 'payload' => $document));
ok('schema_version conservée', $payload['schema_version'] === 1);
ok('totaux et tableaux conservés', $payload['totals'] === $document['totals'] && count($payload['equipments']) === 2);
$json = json_encode($payload);
ok('overrides.types vide reste un objet {} (pas [])', strpos($json, '"types":{}') !== false, $json);
ok('overrides.types non vide inchangé', strpos($json, '"types":{"70":"switch"}') !== false, $json);
ok('listes vides restent des listes', strpos($json, '"commands":[]') !== false && strpos($json, '"scenarios":[]') !== false);

echo "\n24.2 / erreurs explicites pour l'UI\n";
throws_msg_contains('démon sans donnée en mémoire',
    function () { _jeedom2ha_decision_export_payload(array('status' => 'error', 'message' => 'Export de décision indisponible')); },
    'Relire Jeedom');
throws_msg_contains('réponse sans document',
    function () { _jeedom2ha_decision_export_payload(array('status' => 'ok', 'payload' => array())); },
    'Relire Jeedom');
throws_msg_contains('réponse vide',
    function () { _jeedom2ha_decision_export_payload(array()); },
    'Relire Jeedom');

echo "\n24.2 / câblage réel dans core/ajax/jeedom2ha.ajax.php\n";
$src = file_get_contents(__DIR__ . '/../../core/ajax/jeedom2ha.ajax.php');
function action_block($src, $action) {
    $start = strpos($src, "\$action == '{$action}'");
    $end = strpos($src, "else if (\$action ==", $start + 1);
    return substr($src, $start, $end - $start);
}
$b = action_block($src, 'getDecisionExport');
ok('l\'action existe', $b !== '' && strpos($src, "\$action == 'getDecisionExport'") !== false);
ok('relais borné de parc (budget fixe R, motif A1)', strpos($b, "_jeedom2ha_run_parc_relay('DECISION_EXPORT'") !== false);
ok('relaie la route interne en GET, une seule tentative', strpos($b, "callDaemon('/system/decision_export', null, 'GET', \$timeoutS, 1)") !== false);
ok('aucun timeout 15 littéral', !preg_match('/callDaemon\([^;]*,\s*15\b/', $b));
ok('aucune écriture (pas de POST)', strpos($b, "'POST'") === false);
ok('aucun nom ni secret ajouté côté PHP', strpos($b, 'localSecret') === false && strpos($b, 'getName') === false);
ok('l\'accès administrateur est vérifié avant toute action', strpos($src, "isConnect('admin')") !== false
    && strpos($src, "isConnect('admin')") < strpos($src, "\$action == 'getDecisionExport'"));

echo "\n24.2 / payload de sync : réglages de filtrage, identifiants seulement\n";
$cls = file_get_contents(__DIR__ . '/../../core/class/jeedom2ha.class.php');
ok('sync_config porte excluded_plugins', strpos($cls, "'excluded_plugins' => array_values(\$excludedPlugins)") !== false);
ok('sync_config porte excluded_piece_ids (identifiants de excludedObjects)', strpos($cls, "'excluded_piece_ids' => array_values(\$excludedObjects)") !== false);
ok('confidence_policy conservée', strpos($cls, "'confidence_policy' => \$confidencePolicy") !== false);

echo "\n{$passed} réussis, {$failed} échoués\n";
exit($failed > 0 ? 1 : 0);
