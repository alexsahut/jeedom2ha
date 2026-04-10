<?php

define('JEEDOM2HA_AJAX_FUNCTIONS_ONLY', true);
require_once __DIR__ . '/../core/ajax/jeedom2ha.ajax.php';

$failures = array();

function assertTrueExport($condition, $message) {
    global $failures;
    if ($condition) {
        echo 'PASS: ' . $message . PHP_EOL;
        return;
    }
    $failures[] = $message;
    echo 'FAIL: ' . $message . PHP_EOL;
}

function assertSameExport($expected, $actual, $message) {
    $details = sprintf('%s (expected=%s actual=%s)', $message, var_export($expected, true), var_export($actual, true));
    assertTrueExport($expected === $actual, $details);
}

echo 'Testing export diagnostic coherence (Story 4.4)...' . PHP_EOL;

assertTrueExport(function_exists('_jeedom2ha_build_export_equipment'), '_jeedom2ha_build_export_equipment exists');
assertTrueExport(function_exists('_jeedom2ha_build_export_summary'), '_jeedom2ha_build_export_summary exists');

$rawEquipments = array(
    array(
        'eq_id' => 10,
        'name' => 'Lampe salon',
        'object_name' => 'Salon',
        'perimetre' => 'inclus',
        'statut' => 'publie',
        'ecart' => false,
        'cause_code' => null,
        'cause_label' => null,
        'cause_action' => null,
        'status_code' => 'partially_published',
        'reason_code' => 'sure',
        'matched_commands' => array(array('cmd_id' => 1, 'cmd_name' => 'OnOff', 'generic_type' => 'LIGHT_STATE', 'ignored' => 'x')),
        'unmatched_commands' => array(),
    ),
    array(
        'eq_id' => 11,
        'name' => 'Volet chambre',
        'object_name' => 'Chambre',
        'perimetre' => 'inclus',
        'statut' => 'non_publie',
        'ecart' => true,
        'cause_code' => 'no_mapping',
        'cause_label' => 'Aucun mapping compatible',
        'cause_action' => 'Vérifiez les types génériques',
        'status_code' => 'not_supported',
        'reason_code' => 'no_supported_generic_type',
        'matched_commands' => array(),
        'unmatched_commands' => array(array('cmd_id' => 2, 'cmd_name' => 'Level', 'generic_type' => 'BRIGHTNESS', 'extra' => 'y')),
    ),
    array(
        'eq_id' => 12,
        'name' => 'Capteur garage',
        'object_name' => 'Garage',
        'perimetre' => 'exclu_par_plugin',
        'statut' => 'non_publie',
        'ecart' => false,
        'cause_code' => 'excluded_plugin',
        'cause_label' => 'Exclu par le plugin',
        'cause_action' => null,
        'status_code' => 'excluded',
        'reason_code' => 'excluded_plugin',
        'matched_commands' => array(),
        'unmatched_commands' => array(),
    ),
);

$equipments = array();
foreach ($rawEquipments as $rawEq) {
    $equipments[] = _jeedom2ha_build_export_equipment($rawEq);
}

$summary = _jeedom2ha_build_export_summary($equipments);

// Cohérence 4D summary
assertSameExport(3, $summary['total'] ?? null, 'summary.total compte tous les équipements');
assertSameExport(2, $summary['inclus'] ?? null, 'summary.inclus compte les équipements in-scope');
assertSameExport(1, $summary['exclus'] ?? null, 'summary.exclus compte les équipements exclus');
assertSameExport(1, $summary['ecarts'] ?? null, 'summary.ecarts compte uniquement ecart=true');
assertSameExport(1, $summary['publies'] ?? null, 'summary.publies suit statut=publie');
assertSameExport(2, $summary['non_publies'] ?? null, 'summary.non_publies suit statut=non_publie');

// Aucune clé legacy de statut principal dans le résumé
assertTrueExport(!array_key_exists('partially_published', $summary), 'summary n\'expose pas partially_published');
assertTrueExport(!array_key_exists('ambiguous', $summary), 'summary n\'expose pas ambiguous');
assertTrueExport(!array_key_exists('not_supported', $summary), 'summary n\'expose pas not_supported');

// Champs 4D passthrough inchangés
assertSameExport('no_mapping', $equipments[1]['cause_code'] ?? null, 'cause_code est transmis tel quel');
assertSameExport('Aucun mapping compatible', $equipments[1]['cause_label'] ?? null, 'cause_label est transmis tel quel');
assertSameExport('Vérifiez les types génériques', $equipments[1]['cause_action'] ?? null, 'cause_action est transmis tel quel');
assertSameExport('partially_published', $equipments[0]['status_code'] ?? null, 'status_code technique reste disponible');

// Allowlist commandes stricte
assertSameExport(array('cmd_id', 'cmd_name', 'generic_type'), array_keys($equipments[0]['matched_commands'][0]), 'matched_commands respecte l\'allowlist');
assertSameExport(array('cmd_id', 'cmd_name', 'generic_type'), array_keys($equipments[1]['unmatched_commands'][0]), 'unmatched_commands respecte l\'allowlist');

if (!empty($failures)) {
    echo PHP_EOL . count($failures) . ' assertion(s) failed.' . PHP_EOL;
    exit(1);
}

echo PHP_EOL . 'All export diagnostic coherence assertions passed.' . PHP_EOL;
exit(0);
