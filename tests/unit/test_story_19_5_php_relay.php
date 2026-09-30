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
// AC11 — réalignement des listeners : récupérer -> valider -> créer -> purger
// (revue ClaudeBox + Codex P2, PR #184 ; fonctions pures de
// core/php/jeedom2ha_state_listeners.php, chargé par l'ajax)
// ---------------------------------------------------------------------------

echo "\nStory 19.5 / AC11 — réalignement des listeners\n";

function _realign_harness($fetch, $failCreateAt = null, $failRemoveAt = null) {
    $trace = [];
    $warnings = [];
    $creates = 0;
    $removes = 0;
    $count = jeedom2ha_realign_state_listeners(
        function () use ($fetch, &$trace) { $trace[] = 'fetch'; return $fetch(); },
        function () use (&$trace) { $trace[] = 'list'; return ['L1', 'L2']; },
        function ($l) use (&$trace, &$removes, $failRemoveAt) {
            $removes++;
            if ($failRemoveAt !== null && $removes === $failRemoveAt) { throw new Exception('db remove'); }
            $trace[] = 'remove:' . $l;
        },
        function (int $eqId, int $cmdId) use (&$trace, &$creates, $failCreateAt) {
            $creates++;
            if ($failCreateAt !== null && $creates === $failCreateAt) { throw new Exception('db save'); }
            $trace[] = 'create:' . $eqId . '/' . $cmdId;
        },
        function (string $m) use (&$warnings) { $warnings[] = $m; }
    );
    return [$count, $trace, $warnings];
}

$twoTargets = function () {
    return ['status' => 'ok', 'listeners' => [['eq_id' => 10, 'cmd_id' => 101], ['eq_id' => 11, 'cmd_id' => 111]]];
};

list($c, $t, $w) = _realign_harness($twoTargets);
assert_eq('ordre : récupérer, relever, créer, puis purger', ['fetch', 'list', 'create:10/101', 'create:11/111', 'remove:L1', 'remove:L2'], $t);
assert_eq('nombre de listeners créés', 2, $c);
assert_eq('aucun avertissement sur une réponse valide', 0, count($w));

list($c, $t, $w) = _realign_harness($twoTargets, 2, null);
assert_eq('création en échec : anciens listeners jamais purgés (Codex P2 PR #185)', ['fetch', 'list', 'create:10/101'], $t);
assert_eq('création en échec : null', null, $c);
assert_eq('création en échec : un avertissement', 1, count($w));

list($c, $t, $w) = _realign_harness($twoTargets, null, 1);
assert_eq('purge en échec : nouveaux listeners en place, doublons temporaires', ['fetch', 'list', 'create:10/101', 'create:11/111'], $t);
assert_eq('purge en échec : les créations comptent', 2, $c);
assert_eq('purge en échec : un avertissement', 1, count($w));

list($c, $t, $w) = _realign_harness(function () { throw new Exception('timeout'); });
assert_eq('exception à la récupération : rien purgé, rien créé', ['fetch'], $t);
assert_eq('exception à la récupération : null (rien touché)', null, $c);
assert_eq('exception à la récupération : un avertissement', 1, count($w));

list($c, $t, $w) = _realign_harness(function () { return null; });
assert_eq('démon muet (null) : listeners conservés', ['fetch'], $t);
assert_eq('démon muet (null) : null', null, $c);

list($c, $t, $w) = _realign_harness(function () { return ['status' => 'error']; });
assert_eq('status != ok : listeners conservés', ['fetch'], $t);

list($c, $t, $w) = _realign_harness(function () { return ['status' => 'ok', 'listeners' => [[]]]; });
assert_eq('cible mal formée ({}) : listeners conservés (tout-ou-rien)', ['fetch'], $t);
assert_eq('cible mal formée : un avertissement', 1, count($w));

list($c, $t, $w) = _realign_harness(function () {
    return ['status' => 'ok', 'listeners' => [['eq_id' => 10, 'cmd_id' => 101], ['cmd_id' => 0]]];
});
assert_eq('une cible à cmd_id 0 parmi des valides : rien purgé', ['fetch'], $t);

list($c, $t, $w) = _realign_harness(function () { return ['status' => 'ok', 'listeners' => []]; });
assert_eq('liste valide vide : tout purgé, rien créé', ['fetch', 'list', 'remove:L1', 'remove:L2'], $t);
assert_eq('liste valide vide : 0', 0, $c);

echo "\nStory 19.5 / AC11 — réalignement après l'action (budget, portée)\n";

$calls = [];
$warns = [];
$realign = function (int $timeout, int $attempts) use (&$calls) { $calls[] = [$timeout, $attempts]; return 1; };
$warn = function (string $m) use (&$warns) { $warns[] = $m; };

assert_eq('publier + réponse démon : réalignement tenté', true, jeedom2ha_realign_after_action('publier', ['status' => 'ok'], $realign, $warn));
assert_eq('budget : 3 s, une seule tentative', [[3, 1]], $calls);

$calls = [];
assert_eq('supprimer : pas de réalignement', false, jeedom2ha_realign_after_action('supprimer', ['status' => 'ok'], $realign, $warn));
assert_eq('publier sans réponse du démon : pas de réalignement', false, jeedom2ha_realign_after_action('publier', null, $realign, $warn));
assert_eq('aucun appel dans ces deux cas', [], $calls);

$threw = false;
try {
    $res = jeedom2ha_realign_after_action('publier', ['status' => 'ok'], function (int $t, int $a) { throw new Exception('state_listeners indisponible'); }, $warn);
} catch (\Throwable $e) {
    $threw = true;
}
assert_eq('state_listeners indisponible après une action réussie : aucune exception vers l UI', false, $threw);
assert_eq('state_listeners indisponible : un avertissement journalisé', 1, count($warns));

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
