<?php
// ARTEFACT — FR49 (12.4, revue Codex de 2626aee) : au clic « Publier », une info d'alarme LUE à null
// part dans `current_values_null` ; une info non lue (échéance dépassée) n'y est pas ; le payload
// `current_values` des autres types ne change pas. Fonctions pures + vrai relais
// (_jeedom2ha_collect_click_values + jeedom2ha_dispatch_action_relay) + câblage de l'ajax.
// Identifiants fictifs (CC-48). Exécution : php tests/test_php_alarm_click_null.php

define('JEEDOM2HA_AJAX_FUNCTIONS_ONLY', true);
require_once __DIR__ . '/../core/ajax/jeedom2ha.ajax.php';

$passed = 0;
$failed = 0;
function check($label, $condition) {
    global $passed, $failed;
    if ($condition) { $passed++; echo "  ✔ {$label}\n"; return; }
    $failed++;
    echo "  ✖ {$label}\n";
}

echo "Fonctions pures\n";
check('Actif / Statut / Mode : infos d\'alarme', jeedom2ha_alarm_is_info_cmd('ALARM_ENABLE_STATE', '', 'virtual')
    && jeedom2ha_alarm_is_info_cmd('ALARM_STATE', 'state', 'alarm') && jeedom2ha_alarm_is_info_cmd('ALARM_MODE', 'mode', 'alarm'));
check('Immédiat : logicalId immediatState du plugin alarm seulement', jeedom2ha_alarm_is_info_cmd(null, 'immediatState', 'alarm')
    && !jeedom2ha_alarm_is_info_cmd(null, 'immediatState', 'virtual'));
check('autres commandes : non', !jeedom2ha_alarm_is_info_cmd('LIGHT_STATE', '', 'virtual') && !jeedom2ha_alarm_is_info_cmd('', '', 'alarm')
    && !jeedom2ha_alarm_is_info_cmd(null, null, null));

$sink = new ArrayObject();
check('lecture : la valeur est rendue telle quelle', jeedom2ha_alarm_click_read(array('cmd_id' => 1, 'alarm_info' => true), '1', $sink) === '1'
    && jeedom2ha_alarm_click_read(array('cmd_id' => 2, 'alarm_info' => true), null, $sink) === null
    && jeedom2ha_alarm_click_read(array('cmd_id' => 3, 'alarm_info' => false), null, $sink) === null
    && jeedom2ha_alarm_click_read(array('cmd_id' => 4), null, $sink) === null);
check('seule l\'info d\'alarme lue à null est notée', $sink->getArrayCopy() === array(2));
check('payload sans lecture au clic : inchangé', jeedom2ha_alarm_add_click_null_reads(array('intention' => 'publier'), $sink) === array('intention' => 'publier'));
check('payload sans info d\'alarme à null : inchangé', jeedom2ha_alarm_add_click_null_reads(array('current_values' => array(5 => '1')), new ArrayObject()) === array('current_values' => array(5 => '1')));
check('payload : current_values_null ajouté, current_values intact', jeedom2ha_alarm_add_click_null_reads(array('current_values' => array(5 => '1')), new ArrayObject(array(2, '2', 7)))
    === array('current_values' => array(5 => '1'), 'current_values_null' => array(2, 7)));
check('current_values vide (tout lu à null) : la liste part quand même', jeedom2ha_alarm_add_click_null_reads(array('current_values' => array()), new ArrayObject(array(2)))
    === array('current_values' => array(), 'current_values_null' => array(2)));

echo "Vrai relais : lecture bornée au clic puis appel de /action/execute\n";
// Équipement d'alarme 7100 : Actif lu à null, Mode lu, Statut non lu (échéance), lampe 7300 lue à null.
$cmdsByEq = array(
    7100 => array(
        array('cmd_id' => 71001, 'type' => 'info', 'alarm_info' => true, 'value' => null),       // Actif lu à null
        array('cmd_id' => 71004, 'type' => 'info', 'alarm_info' => true, 'value' => 'mode nuit'),
        array('cmd_id' => 71005, 'type' => 'action', 'alarm_info' => false, 'value' => null),
    ),
    7300 => array(
        array('cmd_id' => 73003, 'type' => 'info', 'alarm_info' => false, 'value' => null),     // lampe lue à null
        array('cmd_id' => 71002, 'type' => 'info', 'alarm_info' => true, 'value' => null),      // atteinte après l'échéance
    ),
);
$clock = 0.0;
$readNull = new ArrayObject();
$warnings = array();
$values = _jeedom2ha_collect_click_values(
    'equipement', array('7100', '7300'),
    function ($p) { return array(); }, function () { return array(); },
    function ($eqId) use ($cmdsByEq) { return $cmdsByEq[$eqId]; },
    function ($c) use ($readNull, &$clock) {
        $clock += 1.0;   // chaque lecture coûte 1 s ; échéance à 2,5 s
        return jeedom2ha_alarm_click_read($c, $c['value'], $readNull);
    },
    function ($m) use (&$warnings) { $warnings[] = $m; },
    function () use (&$clock) { return $clock; },
    2.5
);
check('current_values : les valeurs non nulles seulement (comportement inchangé)', $values === array(71004 => 'mode nuit'));
check('Actif lu à null : noté ; lampe à null : non ; Statut non lu : non', $readNull->getArrayCopy() === array(71001));
check('l\'échéance a bien coupé la lecture', count($warnings) === 1);

$sent = null;
$result = jeedom2ha_dispatch_action_relay(
    'publier',
    array('intention' => 'publier', 'portee' => 'equipement', 'selection' => array('7100')),
    function ($t, $a) { return array('status' => 'ok'); },
    function () use ($values) { return $values; },
    function (array $callParams, $timeoutS) use ($readNull, &$sent) {
        // Même câblage que l'ajax : ajout de current_values_null juste avant l'appel.
        $sent = jeedom2ha_alarm_add_click_null_reads($callParams, $readNull);
        return array('status' => 'ok');
    },
    function ($r) {}, function ($l, $m) {}, function () { return 0.0; }
);
check('payload envoyé : current_values inchangé', $sent['current_values'] === array(71004 => 'mode nuit'));
check('payload envoyé : current_values_null = [Actif]', $sent['current_values_null'] === array(71001));
check('JSON : current_values_null est une liste d\'entiers', strpos(json_encode($sent), '"current_values_null":[71001]') !== false);

echo "Câblage de l'ajax (source)\n";
$ajax = file_get_contents(__DIR__ . '/../core/ajax/jeedom2ha.ajax.php');
check('les commandes du clic portent alarm_info', strpos($ajax, "\$cmds[count(\$cmds) - 1]['alarm_info'] = jeedom2ha_alarm_is_info_cmd(\$cmd->getGeneric_type(), \$cmd->getLogicalId(), \$cmd->getEqType_name());") !== false);
check('la lecture passe par jeedom2ha_alarm_click_read', strpos($ajax, "return jeedom2ha_alarm_click_read(\$c, \$c['_cmd']->getCache('value', null), \$alarmReadNull);") !== false);
check('l\'appel de /action/execute ajoute current_values_null', strpos($ajax, '$callParams = jeedom2ha_alarm_add_click_null_reads($callParams, $alarmReadNull);') !== false);

echo "\n{$passed} réussis, {$failed} échoués\n";
exit($failed === 0 ? 0 : 1);
