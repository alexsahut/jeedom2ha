<?php
// ARTEFACT — Story 20-2 (revue ClaudeBox X4, point 1) : relais PHP de previewMappingOverride.
// Exécution : php tests/unit/test_story_20_2_php_relay.php

define('JEEDOM2HA_AJAX_FUNCTIONS_ONLY', true);
require_once __DIR__ . '/../../core/ajax/jeedom2ha.ajax.php';

$passed = 0;
$failed = 0;
$total  = 0;

function assert_eq($label, $expected, $actual) {
    global $passed, $failed, $total;
    $total++;
    if ($expected === $actual) {
        $passed++;
        echo "  ✔ {$label}\n";
    } else {
        $failed++;
        echo "  ✖ {$label}\n";
        echo "    expected: " . json_encode($expected) . "\n";
        echo "    actual:   " . json_encode($actual) . "\n";
    }
}

function assert_throws($label, callable $fn) {
    global $passed, $failed, $total;
    $total++;
    try {
        $fn();
        $failed++;
        echo "  ✖ {$label}\n    expected exception, none thrown\n";
    } catch (\Throwable $e) {
        $passed++;
        echo "  ✔ {$label}\n";
    }
}

echo "\nStory 20-2 / point 1 — aperçu de type inchangé (rétro-compat)\n";

assert_eq(
    'type sur commande : eqId + cmdId + ha_entity_type, pas de publication_policy',
    array('jeedom_eq_id' => 12, 'jeedom_cmd_id' => 34, 'ha_entity_type' => 'light'),
    _jeedom2ha_build_override_preview_params('12', '34', 'light', '')
);

echo "\nStory 20-2 / point 1 — forçage d'entité (portée commande)\n";

assert_eq(
    'force_publish sur une commande : jeedom_cmd_id + publication_policy, pas ha_entity_type',
    array('jeedom_eq_id' => 12, 'jeedom_cmd_id' => 34, 'publication_policy' => 'force_publish'),
    _jeedom2ha_build_override_preview_params('12', '34', '', 'force_publish')
);

assert_eq(
    'exclude sur une commande',
    array('jeedom_eq_id' => 12, 'jeedom_cmd_id' => 34, 'publication_policy' => 'exclude'),
    _jeedom2ha_build_override_preview_params('12', '34', '', 'exclude')
);

echo "\nStory 20-2 / point 1 — forçage d'équipement (portée équipement, cmdId absent)\n";

assert_eq(
    'force_publish à la portée équipement : aucun jeedom_cmd_id (jamais 0 par défaut)',
    array('jeedom_eq_id' => 12, 'publication_policy' => 'force_publish'),
    _jeedom2ha_build_override_preview_params('12', '', '', 'force_publish')
);

assert_eq(
    'exclude à la portée équipement, cmdId non numérique traité comme absent',
    array('jeedom_eq_id' => 12, 'publication_policy' => 'exclude'),
    _jeedom2ha_build_override_preview_params('12', null, '', 'exclude')
);

echo "\nStory 20-2 / point 1 — valeurs invalides\n";

assert_throws(
    'eqId non numérique rejeté',
    function () { _jeedom2ha_build_override_preview_params('abc', '34', 'light', ''); }
);

assert_throws(
    'publicationPolicy hors énumération rejetée',
    function () { _jeedom2ha_build_override_preview_params('12', '34', '', 'autre'); }
);

assert_throws(
    'ni haEntityType ni publicationPolicy : requête vide rejetée',
    function () { _jeedom2ha_build_override_preview_params('12', '34', '', ''); }
);

echo "\n--- Bilan Story 20-2 / point 1 : {$passed}/{$total} passés, {$failed} échoués ---\n";
if ($failed > 0) {
    exit(1);
}
