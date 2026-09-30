<?php
// ARTEFACT — Story 19.6 (CC-32) : tests relay PHP — budget fixe, échéance, second statut.
// Exécution : php tests/unit/test_story_19_6_php_relay.php

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

function assert_throws_message($label, callable $fn, string $expectedMessage) {
    global $passed, $failed, $total;
    $total++;
    try {
        $fn();
        $failed++;
        echo "  ✖ {$label}\n    expected exception, none thrown\n";
        return;
    } catch (\Throwable $e) {
        if ($e->getMessage() === $expectedMessage) {
            $passed++;
            echo "  ✔ {$label}\n";
        } else {
            $failed++;
            echo "  ✖ {$label}\n    expected: {$expectedMessage}\n    actual:   {$e->getMessage()}\n";
        }
    }
}

$fixture = json_decode(file_get_contents(__DIR__ . '/../fixtures/action_budget_constants.json'), true);

// ---------------------------------------------------------------------------
// AC1 — constantes fixes, table commune avec le test node
// ---------------------------------------------------------------------------

echo "\nStory 19.6 / AC1 — constantes du budget fixe\n";

assert_eq('R == table', $fixture['R'], JEEDOM2HA_ACTION_BUDGET_R);
assert_eq('reserve_s == table', $fixture['reserve_s'], JEEDOM2HA_ACTION_BUDGET_RESERVE_S);
assert_eq('status_timeout_s == table', $fixture['status_timeout_s'], JEEDOM2HA_ACTION_BUDGET_STATUS_TIMEOUT_S);
assert_eq('click_read_deadline_s == table', $fixture['click_read_deadline_s'], JEEDOM2HA_ACTION_BUDGET_CLICK_READ_DEADLINE_S);
assert_eq('realign_timeout_s == table', $fixture['realign_timeout_s'], JEEDOM2HA_ACTION_BUDGET_REALIGN_TIMEOUT_S);
assert_eq('deadline_s == R - reserve_s == table', $fixture['deadline_s'], jeedom2ha_action_deadline_s());

// ---------------------------------------------------------------------------
// AC1 — contenu de la ligne de journal
// ---------------------------------------------------------------------------

echo "\nStory 19.6 / AC1 — ligne de journal figée\n";

assert_eq(
    'ligne de journal exacte',
    '[ACTION-BUDGET] intention=publier portee=global R=60 reserve_s=5 deadline_s=55 duration_s=1.250',
    jeedom2ha_build_action_budget_log_line('publier', 'global', 60, 5, 55, 1.25)
);

// ---------------------------------------------------------------------------
// Harnais commun pour jeedom2ha_dispatch_action_relay
// ---------------------------------------------------------------------------

function make_clock(array $ticks) {
    $i = 0;
    return function () use (&$i, $ticks) {
        $t = $ticks[$i] ?? end($ticks);
        $i++;
        return $t;
    };
}

// ---------------------------------------------------------------------------
// AC3 — ordre imposé : statut, puis lecture au clic, puis action
// ---------------------------------------------------------------------------

echo "\nStory 19.6 / AC3 — ordre statut -> lecture -> action\n";

$calls = [];
$probeStatus = function (int $t, int $a) use (&$calls) {
    $calls[] = 'status';
    return ['status' => 'ok'];
};
$collectClickValues = function () use (&$calls) {
    $calls[] = 'click';
    return ['30001' => '21.5'];
};
$callAction = function (array $params, int $timeout) use (&$calls) {
    $calls[] = 'action';
    return ['status' => 'ok', 'result' => []];
};
$realign = function (array $result) use (&$calls) {
    $calls[] = 'realign';
};
$logInfo = function (string $level, string $m) use (&$calls) {
    $calls[] = 'log:' . $level . ':' . $m;
};
$now = make_clock([0.0, 1.0]);

$result = jeedom2ha_dispatch_action_relay('publier', ['intention' => 'publier', 'portee' => 'global'], $probeStatus, $collectClickValues, $callAction, $realign, $logInfo, $now);

assert_eq('ordre : status puis click puis action puis realign', ['status', 'click', 'action', 'realign'], array_values(array_filter($calls, function ($c) { return strpos($c, 'log:') !== 0; })));
assert_eq('résultat renvoyé au relais', ['status' => 'ok', 'result' => []], $result);

// ---------------------------------------------------------------------------
// AC3 — démon injoignable au statut préalable : message actuel, pas d'action
// ---------------------------------------------------------------------------

echo "\nStory 19.6 / AC3 — démon injoignable au statut préalable\n";

$calls2 = [];
$probeStatusDown = function (int $t, int $a) use (&$calls2) {
    $calls2[] = 'status';
    return null;
};
$callActionNeverCalled = function (array $params, int $timeout) use (&$calls2) {
    $calls2[] = 'action';
    return ['status' => 'ok'];
};

assert_throws_message(
    'statut préalable en échec : message démon injoignable',
    function () use ($probeStatusDown, $callActionNeverCalled) {
        jeedom2ha_dispatch_action_relay('publier', ['intention' => 'publier', 'portee' => 'global'], $probeStatusDown, null, $callActionNeverCalled, function () {}, function () {}, make_clock([0.0]));
    },
    jeedom2ha_action_daemon_unreachable_message()
);
assert_eq('aucun appel action après statut en échec', ['status'], $calls2);

// ---------------------------------------------------------------------------
// AC1 — deadline_s transmis au démon = R - reserve_s
// ---------------------------------------------------------------------------

echo "\nStory 19.6 / AC1 — deadline_s transmis\n";

$capturedParams = null;
$callActionCapture = function (array $params, int $timeout) use (&$capturedParams) {
    $capturedParams = $params;
    return ['status' => 'ok'];
};
jeedom2ha_dispatch_action_relay(
    'supprimer',
    ['intention' => 'supprimer', 'portee' => 'equipement'],
    function () { return ['status' => 'ok']; },
    null,
    $callActionCapture,
    function () {},
    function () {},
    make_clock([0.0, 1.0])
);
assert_eq('deadline_s == 55', 55, $capturedParams['deadline_s']);

// ---------------------------------------------------------------------------
// AC2 — échéance de lecture des valeurs au clic atteinte
// ---------------------------------------------------------------------------

echo "\nStory 19.6 / AC2 — échéance de lecture au clic\n";

$cmds = [
    ['cmd_id' => 1, 'type' => 'info'],
    ['cmd_id' => 2, 'type' => 'info'],
    ['cmd_id' => 3, 'type' => 'info'],
];
$warns = [];
$warn = function (string $m) use (&$warns) { $warns[] = $m; };
// Horloge : start=0, puis 1, 2 (sous l'échéance de 10) pour les 2 premières commandes,
// puis 11 (>= 10) pour la 3e : arrêt avant lecture.
$clock = make_clock([0.0, 1.0, 2.0, 11.0]);
$valuesGetter = function ($c) { return 'v' . $c['cmd_id']; };

$boundedValues = _jeedom2ha_read_current_values_bounded($cmds, $valuesGetter, $clock, 10.0, $warn);

assert_eq('valeurs partielles transmises (2 lues)', [1 => 'v1', 2 => 'v2'], $boundedValues);
assert_eq('un WARNING journalisé', 1, count($warns));
assert_eq('le WARNING mentionne le nombre de commandes lues (2)', true, strpos($warns[0], '2 commande') !== false);

// Correction de revue (bloc C) — l'échéance couvre aussi la liste des commandes
// (_cmdsFetcher), pas seulement la lecture des valeurs : l'horloge démarre avant
// l'expansion de la portée.
echo "\nStory 19.6 / AC2 — échéance atteinte pendant la liste des commandes\n";

$listWarns = [];
$listWarn = function (string $m) use (&$listWarns) { $listWarns[] = $m; };
// 2 équipements dans la portée piece ; le fetcher de commandes consomme du temps.
$pieceFetcherList = function (int $p) { return [10, 20]; };
$allFetcherList = function () { return []; };
$cmdsFetcherCalls = 0;
$cmdsFetcherList = function ($eqId) use (&$cmdsFetcherCalls) {
    $cmdsFetcherCalls++;
    return [['cmd_id' => $eqId, 'type' => 'info']];
};
$valuesGetterList = function ($c) { return 'v' . $c['cmd_id']; };
// Horloge : start=0.0 ; le 1er eqId est listé sous l'échéance (1.0 < 4.0) ; avant le
// 2e eqId, le temps écoulé dépasse déjà l'échéance (5.0 >= 4.0).
$clockList = make_clock([0.0, 1.0, 5.0]);

$listResult = _jeedom2ha_collect_click_values(
    'piece',
    [9],
    $pieceFetcherList,
    $allFetcherList,
    $cmdsFetcherList,
    $valuesGetterList,
    $listWarn,
    $clockList,
    4.0
);

assert_eq('résultat vide : arrêt avant toute lecture de valeur', [], $listResult);
assert_eq('un seul eqId a eu le temps d\'être listé', 1, $cmdsFetcherCalls);
assert_eq('un WARNING journalisé, mentionnant la liste des commandes', 1, count($listWarns));
assert_eq('le WARNING mentionne "liste des commandes"', true, strpos($listWarns[0], 'liste des commandes') !== false);

// ---------------------------------------------------------------------------
// AC5 — les deux messages distincts en cas de vrai dépassement
// ---------------------------------------------------------------------------

echo "\nStory 19.6 / AC5 — messages distincts au dépassement\n";

// Cas a : démon injoignable au second statut (comme au premier)
$callActionTimeout = function (array $params, int $timeout) { return null; };
$statusSeq = [['status' => 'ok'], null]; // 1er OK (avant action), 2e null (après échec)
$statusIdx = 0;
$probeStatusSeqA = function (int $t, int $a) use (&$statusIdx, $statusSeq) {
    $v = $statusSeq[$statusIdx];
    $statusIdx++;
    return $v;
};
$logsA = [];
$logA = function (string $level, string $m) use (&$logsA) { $logsA[] = [$level, $m]; };
assert_throws_message(
    'second statut injoignable : message démon injoignable',
    function () use ($probeStatusSeqA, $callActionTimeout, $logA) {
        jeedom2ha_dispatch_action_relay('publier', ['intention' => 'publier', 'portee' => 'global'], $probeStatusSeqA, function () { return null; }, $callActionTimeout, function () {}, $logA, make_clock([0.0, 1.0]));
    },
    jeedom2ha_action_daemon_unreachable_message()
);
assert_eq('journal : ligne info puis error (démon injoignable)', ['info', 'error'], array_column($logsA, 0));

// Cas b : démon joignable au second statut -> message de dépassement, pas de réalignement
$statusSeq2 = [['status' => 'ok'], ['status' => 'ok']];
$statusIdx2 = 0;
$probeStatusSeqB = function (int $t, int $a) use (&$statusIdx2, $statusSeq2) {
    $v = $statusSeq2[$statusIdx2];
    $statusIdx2++;
    return $v;
};
$realignCalledB = false;
$logsB = [];
$logB = function (string $level, string $m) use (&$logsB) { $logsB[] = [$level, $m]; };
assert_throws_message(
    'second statut joignable : message de vrai dépassement',
    function () use ($probeStatusSeqB, $callActionTimeout, &$realignCalledB, $logB) {
        jeedom2ha_dispatch_action_relay('publier', ['intention' => 'publier', 'portee' => 'global'], $probeStatusSeqB, function () { return null; }, $callActionTimeout, function () use (&$realignCalledB) { $realignCalledB = true; }, $logB, make_clock([0.0, 1.0]));
    },
    jeedom2ha_action_timeout_message()
);
assert_eq('aucun réalignement en cas de vrai dépassement', false, $realignCalledB);
assert_eq('journal : ligne info puis warning (dépassement AC5)', ['info', 'warning'], array_column($logsB, 0));

// ---------------------------------------------------------------------------
// AC8 — 409 (action_in_progress) transmis tel quel, sans second statut ni réalignement
// ---------------------------------------------------------------------------

echo "\nStory 19.6 / AC8 — action_in_progress transmis tel quel\n";

$statusCallCount = 0;
$probeStatusOnce = function (int $t, int $a) use (&$statusCallCount) {
    $statusCallCount++;
    return ['status' => 'ok'];
};
$callActionConflict = function (array $params, int $timeout) {
    return ['status' => 'error', 'code' => 'action_in_progress', 'message' => 'Une action Home Assistant est déjà en cours.'];
};
$realignCalledConflict = false;
$logsConflict = [];
$logConflict = function (string $level, string $m) use (&$logsConflict) { $logsConflict[] = [$level, $m]; };
assert_throws_message(
    '409 : message transmis tel quel',
    function () use ($probeStatusOnce, $callActionConflict, &$realignCalledConflict, $logConflict) {
        jeedom2ha_dispatch_action_relay('supprimer', ['intention' => 'supprimer', 'portee' => 'global'], $probeStatusOnce, null, $callActionConflict, function () use (&$realignCalledConflict) { $realignCalledConflict = true; }, $logConflict, make_clock([0.0, 1.0]));
    },
    'Une action Home Assistant est déjà en cours.'
);
assert_eq('statut appelé une seule fois (préalable seulement)', 1, $statusCallCount);
assert_eq('aucun réalignement après un refus 409', false, $realignCalledConflict);
assert_eq('journal : ligne info puis warning (refus 409)', ['info', 'warning'], array_column($logsConflict, 0));

// ---------------------------------------------------------------------------
// AC4 — réalignement après succès seulement
// ---------------------------------------------------------------------------

echo "\nStory 19.6 / AC4 — réalignement après succès seulement\n";

$realignCalledSuccess = false;
jeedom2ha_dispatch_action_relay(
    'publier',
    ['intention' => 'publier', 'portee' => 'global'],
    function () { return ['status' => 'ok']; },
    function () { return null; },
    function (array $p, int $t) { return ['status' => 'ok']; },
    function (array $r) use (&$realignCalledSuccess) { $realignCalledSuccess = true; },
    function () {},
    make_clock([0.0, 1.0])
);
assert_eq('réalignement appelé après un succès', true, $realignCalledSuccess);

// ---------------------------------------------------------------------------
// AC3 — petite portée : flux inchangé (supprimer, pas de lecture au clic)
// ---------------------------------------------------------------------------

echo "\nStory 19.6 / AC3 — petit parc : flux inchangé\n";

$smallResult = jeedom2ha_dispatch_action_relay(
    'supprimer',
    ['intention' => 'supprimer', 'portee' => 'equipement', 'selection' => [12]],
    function () { return ['status' => 'ok']; },
    null,
    function (array $p, int $t) { return ['status' => 'ok', 'result' => ['published' => 1]]; },
    function () {},
    function () {},
    make_clock([0.0, 0.2])
);
assert_eq('résultat du démon renvoyé sans altération', ['status' => 'ok', 'result' => ['published' => 1]], $smallResult);

// ---------------------------------------------------------------------------
// Résultat
// ---------------------------------------------------------------------------

echo "\n" . str_repeat('-', 60) . "\n";
echo "Story 19.6 PHP relay tests: {$passed}/{$total} passed";
if ($failed > 0) {
    echo " ({$failed} FAILED)";
}
echo "\n";
exit($failed > 0 ? 1 : 0);
