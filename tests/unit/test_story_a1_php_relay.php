<?php
// ARTEFACT — Story A1 : relais de parc (scanTopology, exportDiagnostic, getDiagnostics) bornés
// par le budget fixe R, et relais indépendants du parc (testMqttConnection, getMappingOverrides)
// restés sur le budget court. Exécute le vrai jeedom2ha_dispatch_parc_relay appelé par le relais.
// Exécution : php tests/unit/test_story_a1_php_relay.php

define('JEEDOM2HA_AJAX_FUNCTIONS_ONLY', true);
require_once __DIR__ . '/../../core/ajax/jeedom2ha.ajax.php';

$passed = 0; $failed = 0;

function ok($label, $cond, $detail = '') {
    global $passed, $failed;
    if ($cond) { $passed++; echo "  ✔ {$label}\n"; }
    else { $failed++; echo "  ✖ {$label} {$detail}\n"; }
}
function eq($label, $expected, $actual) {
    ok($label, $expected === $actual, 'expected=' . json_encode($expected) . ' actual=' . json_encode($actual));
}
function throws_msg($label, callable $fn, $expected) {
    try { $fn(); ok($label, false, 'aucune exception'); }
    catch (\Throwable $e) { eq($label, $expected, $e->getMessage()); }
}
function clock(array $ticks) {
    $i = 0;
    return function () use (&$i, $ticks) { $t = $ticks[$i] ?? end($ticks); $i++; return $t; };
}

echo "\nA1 / constantes\n";
eq('R == 60', 60, JEEDOM2HA_ACTION_BUDGET_R);
eq('budget court == 15', 15, JEEDOM2HA_RELAY_BUDGET_SHORT_S);

echo "\nA1 / AC3 — démon lent (> 15 s, < R) : succès, jamais « ne répond pas »\n";
$budgetsRecus = [];
$logs = [];
$res = jeedom2ha_dispatch_parc_relay(
    'TOPOLOGY',
    function (int $t) use (&$budgetsRecus) { $budgetsRecus[] = $t; return ['status' => 'ok', 'operation_result' => 'succes']; },
    function () { throw new Exception('sonde inattendue'); },
    function ($l, $m) use (&$logs) { $logs[] = $l . ':' . $m; },
    clock([0.0, 40.0])   // 300 équipements : 40 s de travail, ancien timeout 15 s dépassé
);
eq('résultat renvoyé tel quel', ['status' => 'ok', 'operation_result' => 'succes'], $res);
eq('appel borné à R (60 s), plus 15 s', [60], $budgetsRecus);
eq('ligne de budget journalisée', ['info:[RELAY-BUDGET] relais=TOPOLOGY R=60 duration_s=40.000'], $logs);

echo "\nA1 / AC3 — dépassement réel de R, démon joignable : message distinct\n";
$probes = 0;
throws_msg(
    'null après ~R + statut ok => message de dépassement',
    function () use (&$probes) {
        jeedom2ha_dispatch_parc_relay('EXPORT', function () { return null; },
            function () use (&$probes) { $probes++; return ['status' => 'ok']; },
            function () {}, clock([0.0, 60.2]));
    },
    jeedom2ha_relay_timeout_message()
);
eq('une sonde de statut', 1, $probes);
ok('message de dépassement distinct de « ne répond pas »', jeedom2ha_relay_timeout_message() !== jeedom2ha_action_daemon_unreachable_message());

echo "\nA1 / AC3 — message déclenché seulement au dépassement réel (pas un timeout arbitraire)\n";
throws_msg(
    'échec immédiat (HTTP 500) + statut ok => erreur démon, pas dépassement',
    function () {
        jeedom2ha_dispatch_parc_relay('DIAGNOSTICS', function () { return null; },
            function () { return ['status' => 'ok']; }, function () {}, clock([0.0, 0.2]));
    },
    jeedom2ha_action_daemon_error_message()
);
throws_msg(
    'démon réellement injoignable (statut null) => message injoignable',
    function () {
        jeedom2ha_dispatch_parc_relay('TOPOLOGY', function () { return null; },
            function () { return null; }, function () {}, clock([0.0, 0.1]));
    },
    jeedom2ha_action_daemon_unreachable_message()
);
throws_msg(
    'injoignable même après R plein => injoignable (pas dépassement)',
    function () {
        jeedom2ha_dispatch_parc_relay('TOPOLOGY', function () { return null; },
            function () { return null; }, function () {}, clock([0.0, 60.0]));
    },
    jeedom2ha_action_daemon_unreachable_message()
);

echo "\nA1 / AC1-AC2 — câblage réel dans core/ajax/jeedom2ha.ajax.php\n";
$src = file_get_contents(__DIR__ . '/../../core/ajax/jeedom2ha.ajax.php');
function action_block($src, $action) {
    $start = strpos($src, "\$action == '{$action}'");
    $end = strpos($src, "else if (\$action ==", $start + 1);
    return substr($src, $start, $end - $start);
}
foreach (['scanTopology' => 'TOPOLOGY', 'getDiagnostics' => 'DIAGNOSTICS', 'exportDiagnostic' => 'EXPORT'] as $a => $label) {
    $b = action_block($src, $a);
    ok("{$a} passe par le relais borné ({$label})", strpos($b, "_jeedom2ha_run_parc_relay('{$label}'") !== false);
    ok("{$a} n'a plus de timeout 15 littéral", !preg_match('/callDaemon\([^;]*,\s*15\b/', $b));
}
foreach (['testMqttConnection', 'getMappingOverrides'] as $a) {
    $b = action_block($src, $a);
    ok("{$a} garde le budget court nommé", strpos($b, 'JEEDOM2HA_RELAY_BUDGET_SHORT_S') !== false);
    ok("{$a} n'utilise pas deadline_s", strpos($b, "['deadline_s']") === false && strpos($b, "'deadline_s' =>") === false);
    ok("{$a} documente sa décision inline", strpos($b, 'Story A1 (audit)') !== false);
}

echo "\n{$passed} réussis, {$failed} échoués\n";
exit($failed > 0 ? 1 : 0);
