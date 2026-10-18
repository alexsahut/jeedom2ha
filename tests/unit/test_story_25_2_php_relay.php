<?php
// ARTEFACT — Story 25.2 (Q9 A) : relais minimal et en lecture seule `getEquipmentStates` vers
// GET /system/equipment_states. Contrôle le câblage du fichier réel (aucun appel au démon).
// Exécution : php tests/unit/test_story_25_2_php_relay.php

define('JEEDOM2HA_AJAX_FUNCTIONS_ONLY', true);
require_once __DIR__ . '/../../core/ajax/jeedom2ha.ajax.php';

$passed = 0; $failed = 0;

function ok($label, $cond, $detail = '') {
    global $passed, $failed;
    if ($cond) { $passed++; echo "  ✔ {$label}\n"; }
    else { $failed++; echo "  ✖ {$label} {$detail}\n"; }
}

$src = file_get_contents(__DIR__ . '/../../core/ajax/jeedom2ha.ajax.php');
$start = strpos($src, "\$action == 'getEquipmentStates'");
$end = strpos($src, "else if (\$action ==", $start + 1);
ok('action getEquipmentStates présente', $start !== false);
$block = substr($src, $start, $end - $start);

echo "\n25.2 / câblage du relais\n";
ok('relaie GET /system/equipment_states', strpos($block, "'/system/equipment_states'") !== false && strpos($block, "'GET'") !== false);
ok('transmet refresh=1 seulement sur demande', strpos($block, "init('refresh', '') === '1'") !== false && strpos($block, "'?refresh=1'") !== false);
ok('budget court nommé', strpos($block, 'JEEDOM2HA_RELAY_BUDGET_SHORT_S') !== false);
ok('pas de deadline_s ni de timeout littéral', strpos($block, 'deadline_s') === false && !preg_match('/callDaemon\([^;]*,\s*\d+\s*\)/', $block));
ok('aucune écriture : pas de POST ni de config::save', strpos($block, "'POST'") === false && strpos($block, 'config::save') === false);
ok('erreur explicite si le démon ne répond pas', strpos($block, 'Le démon ne répond pas') !== false);

echo "\n{$passed} réussis, {$failed} échoués\n";
exit($failed > 0 ? 1 : 0);
