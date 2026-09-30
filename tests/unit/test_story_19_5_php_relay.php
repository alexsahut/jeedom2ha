<?php
// ARTEFACT — Story 19.5 : tests relay PHP (CC-29) état initial au clic « Publier ».
// Exécution : php tests/unit/test_story_19_5_php_relay.php

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

// ---------------------------------------------------------------------------
// AC6 — _jeedom2ha_read_current_values : lecture pure, omission des null
// ---------------------------------------------------------------------------

echo "\nStory 19.5 / AC6 — lecture pure des valeurs courantes\n";

$cmds = [
    ['cmd_id' => 30003, 'type' => 'info', '_val' => '1'],
    ['cmd_id' => 30001, 'type' => 'action', '_val' => null],
    ['cmd_id' => 30099, 'type' => 'info', '_val' => null],
    ['cmd_id' => 0,     'type' => 'info', '_val' => 'x'],
];
$values = _jeedom2ha_read_current_values($cmds, function ($c) { return $c['_val']; });

assert_eq('seule la commande info avec valeur non-null est retenue', ['30003' => '1'], $values);

// ---------------------------------------------------------------------------
// AC6/AC11 — _jeedom2ha_expand_portee_to_eq_ids : les 3 portées
// ---------------------------------------------------------------------------

echo "\nStory 19.5 / AC6-AC11 — expansion de portée en eq_id\n";

$pieceFetcher = function ($pieceId) { return $pieceId === 7 ? [101, 102] : []; };
$allFetcher = function () { return [201, 202, 203]; };

assert_eq(
    'portee=equipement -> selection telle quelle (ids valides)',
    [55, 56],
    _jeedom2ha_expand_portee_to_eq_ids('equipement', ['55', '56', 'abc'], $pieceFetcher, $allFetcher)
);

assert_eq(
    'portee=piece -> resolue via le fetcher piece injecte',
    [101, 102],
    _jeedom2ha_expand_portee_to_eq_ids('piece', [7], $pieceFetcher, $allFetcher)
);

assert_eq(
    'portee=global -> resolue via le fetcher global injecte',
    [201, 202, 203],
    _jeedom2ha_expand_portee_to_eq_ids('global', [], $pieceFetcher, $allFetcher)
);

assert_eq(
    'portee inconnue -> tableau vide',
    [],
    _jeedom2ha_expand_portee_to_eq_ids('bogus', [1], $pieceFetcher, $allFetcher)
);

// ---------------------------------------------------------------------------
// Résiduel AC6 — équipement sans commande info exploitable -> aucune valeur
// ---------------------------------------------------------------------------

echo "\nStory 19.5 / residuel AC6 — aucune commande info exploitable\n";

$noneValues = _jeedom2ha_read_current_values(
    [['cmd_id' => 900, 'type' => 'info', '_val' => null]],
    function ($c) { return $c['_val']; }
);
assert_eq('aucune valeur => tableau vide (pas une erreur)', [], $noneValues);

// ---------------------------------------------------------------------------
// Résultat
// ---------------------------------------------------------------------------

echo "\n" . str_repeat('-', 60) . "\n";
echo "Story 19.5 PHP relay tests: {$passed}/{$total} passed";
if ($failed > 0) {
    echo " ({$failed} FAILED)";
}
echo "\n";
exit($failed > 0 ? 1 : 0);
