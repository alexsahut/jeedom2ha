<?php

define('JEEDOM2HA_AJAX_FUNCTIONS_ONLY', true);
require_once __DIR__ . '/../core/ajax/jeedom2ha.ajax.php';

$failures = array();

function assertTrueHomeSignals($condition, $message) {
    global $failures;
    if ($condition) {
        echo 'PASS: ' . $message . PHP_EOL;
        return;
    }
    $failures[] = $message;
    echo 'FAIL: ' . $message . PHP_EOL;
}

function assertSameHomeSignals($expected, $actual, $message) {
    $details = sprintf('%s (expected=%s actual=%s)', $message, var_export($expected, true), var_export($actual, true));
    assertTrueHomeSignals($expected === $actual, $details);
}

echo 'Testing Story 4.5 relay home signals (Perimetre + Publies + Statut piece)...' . PHP_EOL;

assertTrueHomeSignals(function_exists('_jeedom2ha_build_home_room_status'), '_jeedom2ha_build_home_room_status exists');
assertTrueHomeSignals(function_exists('_jeedom2ha_build_home_signals'), '_jeedom2ha_build_home_signals exists');

$publishedScope = array(
    'global' => array(
        'counts' => array('total' => 4, 'include' => 3, 'exclude' => 1),
    ),
    'pieces' => array(
        array(
            'object_id' => 1,
            'counts' => array('total' => 2, 'include' => 0, 'exclude' => 2),
            'home_perimetre' => 'Incluse',
        ),
        array(
            'object_id' => 2,
            'counts' => array('total' => 2, 'include' => 0, 'exclude' => 2),
            'home_perimetre' => 'Exclue',
        ),
    ),
    'equipements' => array(
        array('eq_id' => 101, 'object_id' => 1),
        array('eq_id' => 102, 'object_id' => 1),
        array('eq_id' => 201, 'object_id' => 2),
        array('eq_id' => 202, 'object_id' => 2),
    ),
);

$diagnosticPayload = array(
    'summary' => array(
        // Signal contractuel dédié lu en passthrough relay/home
        'home_statut' => 'Partiellement publiee',
    ),
    'rooms' => array(
        array('object_id' => 1, 'home_statut' => 'Non publiee'),
        array('object_id' => 2, 'home_statut' => 'Publiee'),
    ),
    'equipments' => array(
        array('eq_id' => 101, 'statut' => 'publie'),
        array('eq_id' => 102, 'statut' => 'publie'),
        array('eq_id' => 201, 'statut' => 'publie'),
        array('eq_id' => 202, 'statut' => 'non_publie'),
    ),
);

$signals = _jeedom2ha_build_home_signals($publishedScope, $diagnosticPayload);

assertSameHomeSignals(3, $signals['global']['publies'] ?? null, 'Global publies is computed from backend diagnostic statut');
assertSameHomeSignals('Partiellement publiee', $signals['global']['statut'] ?? null, 'Global statut uses dedicated passthrough signal');

$pieceSignalsById = array();
foreach ($signals['pieces'] ?? array() as $pieceSignal) {
    $pieceSignalsById[(int)$pieceSignal['object_id']] = $pieceSignal;
}

assertSameHomeSignals('Incluse', $pieceSignalsById[1]['perimetre'] ?? null, 'Piece 1 perimetre uses explicit home_perimetre (even if counts show 0 inclus)');
assertSameHomeSignals(2, $pieceSignalsById[1]['publies'] ?? null, 'Piece 1 publies is relayed');
assertSameHomeSignals('Non publiee', $pieceSignalsById[1]['statut'] ?? null, 'Piece 1 statut follows dedicated signal, no recomposition');
assertSameHomeSignals('Exclue', $pieceSignalsById[2]['perimetre'] ?? null, 'Piece 2 perimetre uses explicit home_perimetre');
assertSameHomeSignals(1, $pieceSignalsById[2]['publies'] ?? null, 'Piece 2 publies is relayed');
assertSameHomeSignals('Publiee', $pieceSignalsById[2]['statut'] ?? null, 'Piece 2 statut follows dedicated signal');

$noDedicatedStatusPayload = array(
    'equipments' => array(
        array('eq_id' => 101, 'statut' => 'publie'),
        array('eq_id' => 102, 'statut' => 'publie'),
        array('eq_id' => 201, 'statut' => 'publie'),
        array('eq_id' => 202, 'statut' => 'publie'),
    ),
);
$noDedicatedSignals = _jeedom2ha_build_home_signals($publishedScope, $noDedicatedStatusPayload);
$noDedicatedById = array();
foreach ($noDedicatedSignals['pieces'] ?? array() as $pieceSignal) {
    $noDedicatedById[(int)$pieceSignal['object_id']] = $pieceSignal;
}
assertSameHomeSignals('', $noDedicatedSignals['global']['statut'] ?? null, 'Missing dedicated global statut keeps neutral state');
assertSameHomeSignals('', $noDedicatedById[1]['statut'] ?? null, 'Missing dedicated room statut does not fallback to synthesized value');
assertSameHomeSignals('', $noDedicatedById[2]['statut'] ?? null, 'No diagnostic_equipments synthesis for room statut when dedicated field is absent');

$missingSignals = _jeedom2ha_build_home_signals($publishedScope, array());
assertSameHomeSignals(null, $missingSignals['global']['publies'] ?? null, 'Missing diagnostic payload keeps neutral Publies');
assertSameHomeSignals('', $missingSignals['global']['statut'] ?? null, 'Missing diagnostic payload keeps neutral Statut');

if (!empty($failures)) {
    echo PHP_EOL . count($failures) . ' assertion(s) failed.' . PHP_EOL;
    exit(1);
}

echo PHP_EOL . 'All Story 4.5 relay home signals assertions passed.' . PHP_EOL;
exit(0);
