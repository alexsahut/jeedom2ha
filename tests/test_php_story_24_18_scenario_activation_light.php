<?php
// ARTEFACT — Story 24.18 : synchro légère quand seule l'activation d'un scénario publié change. Empreinte en deux parties
// (structurelle / activation des scénarios publiés), choix entre chemin léger et synchro complète dans le pas de la tâche
// périodique, échec puis retour à la synchro complète, deux pas stables, câblage dans la classe. Sans cœur Jeedom.
// Identifiants fictifs uniquement (CC-48).
// Exécution : php tests/test_php_story_24_18_scenario_activation_light.php

$root = dirname(__DIR__);
$passed = 0;
$failed = 0;

function check($label, $condition) {
    global $passed, $failed;
    if ($condition) {
        $passed++;
        echo "  ✔ {$label}\n";
        return;
    }
    $failed++;
    echo "  ✖ {$label}\n";
}

require_once $root . '/core/php/jeedom2ha_reevaluation.php';

function eq_row($id, $enable = 1, $type = 'virtual', $object = 3, $conf = '{}') {
    return array('id' => (string) $id, 'isEnable' => (string) $enable, 'eqType_name' => $type,
                 'object_id' => $object === null ? null : (string) $object, 'configuration' => $conf);
}
function sc_row($id, $active) {
    return array('id' => (string) $id, 'isActive' => $active ? '1' : '0');
}

// ---------------------------------------------------------------------------
// AC1 — découpage de l'empreinte
// ---------------------------------------------------------------------------
echo "Empreinte en deux parties\n";
check('la fonction de découpage existe', function_exists('jeedom2ha_decision_fingerprint_parts'));
if (!function_exists('jeedom2ha_decision_fingerprint_parts')) {
    echo "\n{$passed} réussis, {$failed} échoués\n";
    exit(1);
}

$eqs = array(eq_row(1), eq_row(2, 0), eq_row(3, 1, 'zwave', 4));
$scs = array(sc_row(10, true), sc_row(11, false), sc_row(12, true));
// Scénarios 10 et 11 publiés, 12 non publié.
$settings = array('excludedPlugins' => 'zwave', 'excludedObjects' => '', 'publishedScenarios' => array(10, 11),
                  'knownScenarioIds' => array(10, 11, 12));
$p = jeedom2ha_decision_fingerprint_parts($eqs, $scs, $settings);
check('rend structural, activation, states, fingerprint',
    isset($p['structural'], $p['activation'], $p['states'], $p['fingerprint']));
check('composite au format v2:<structurelle>:<activation>',
    $p['fingerprint'] === 'v2:' . $p['structural'] . ':' . $p['activation']);
check('states : tous les scénarios, publiés ou non, triés (revue I1, option A)',
    $p['states'] === array(array('id' => 10, 'is_active' => true), array('id' => 11, 'is_active' => false),
                           array('id' => 12, 'is_active' => true)));

$toggled = jeedom2ha_decision_fingerprint_parts($eqs, array(sc_row(10, false), sc_row(11, false), sc_row(12, true)), $settings);
check('activation d\'un publié : structurelle inchangée', $toggled['structural'] === $p['structural']);
check('activation d\'un publié : activation changée', $toggled['activation'] !== $p['activation']);

$unpub = jeedom2ha_decision_fingerprint_parts($eqs, array(sc_row(10, true), sc_row(11, false), sc_row(12, false)), $settings);
check('activation d\'un non publié : structurelle inchangée, activation changée (revue I1, option A)',
    $unpub['structural'] === $p['structural'] && $unpub['activation'] !== $p['activation']);

$e = $eqs; $e[0]['isEnable'] = '0';
$x = jeedom2ha_decision_fingerprint_parts($e, $scs, $settings);
check('isEnable : structurelle changée, activation inchangée', $x['structural'] !== $p['structural'] && $x['activation'] === $p['activation']);
$x = jeedom2ha_decision_fingerprint_parts($eqs, array_merge($scs, array(sc_row(13, true))), $settings);
check('scénario ajouté : structurelle changée', $x['structural'] !== $p['structural']);
$x = jeedom2ha_decision_fingerprint_parts($eqs, array(sc_row(10, true), sc_row(11, false)), $settings);
check('scénario supprimé (non publié) : structurelle changée', $x['structural'] !== $p['structural']);
$s2 = $settings; $s2['publishedScenarios'] = array(10);
$x = jeedom2ha_decision_fingerprint_parts($eqs, $scs, $s2);
check('choix de publication : structurelle changée', $x['structural'] !== $p['structural']);
$s2 = $settings; $s2['excludedObjects'] = '3';
check('exclusion de pièce : structurelle changée', jeedom2ha_decision_fingerprint_parts($eqs, $scs, $s2)['structural'] !== $p['structural']);
check('ordre de lecture sans effet',
    jeedom2ha_decision_fingerprint_parts(array_reverse($eqs), array_reverse($scs), $settings)['fingerprint'] === $p['fingerprint']);
$named = $eqs; $named[0]['name'] = 'Nom fictif';
$namedSc = $scs; $namedSc[0]['name'] = 'Autre nom';
check('aucun nom n\'entre dans l\'empreinte', jeedom2ha_decision_fingerprint_parts($named, $namedSc, $settings)['fingerprint'] === $p['fingerprint']);

// Choix de publication absent (avant le Lot 4a) : tous les scénarios sont publiés.
$all = jeedom2ha_decision_fingerprint_parts($eqs, $scs, array('excludedPlugins' => 'zwave', 'excludedObjects' => ''));
check('sans choix de publication : tous publiés', count($all['states']) === 3);
$allToggled = jeedom2ha_decision_fingerprint_parts($eqs, array(sc_row(10, true), sc_row(11, false), sc_row(12, false)),
    array('excludedPlugins' => 'zwave', 'excludedObjects' => ''));
check('sans choix de publication : la bascule du 12 change l\'activation seule',
    $allToggled['structural'] === $all['structural'] && $allToggled['activation'] !== $all['activation']);

// Revue 24.18 (M2) — équivalence avec l'empreinte 24.14 : toute variation qui change l'ancienne change la composite.
$cases = array(
    'isEnable' => array($e, $scs, $settings),
    'isActive (publié)' => array($eqs, array(sc_row(10, false), sc_row(11, false), sc_row(12, true)), $settings),
    'isActive (non publié)' => array($eqs, array(sc_row(10, true), sc_row(11, false), sc_row(12, false)), $settings),
    'exclusion individuelle' => array(array(eq_row(1, 1, 'virtual', 3, '{"jeedom2ha_excluded":"1"}'), eq_row(2, 0), eq_row(3, 1, 'zwave', 4)), $scs, $settings),
    'excludedPlugins' => array($eqs, $scs, array_merge($settings, array('excludedPlugins' => ''))),
    'excludedPlugins (ajout)' => array($eqs, $scs, array_merge($settings, array('excludedPlugins' => 'zwave,virtual'))),
    'excludedObjects' => array($eqs, $scs, array_merge($settings, array('excludedObjects' => '3'))),
    'équipement ajouté' => array(array_merge($eqs, array(eq_row(9))), $scs, $settings),
    'équipement changé de pièce' => array(array(eq_row(1, 1, 'virtual', 7), eq_row(2, 0), eq_row(3, 1, 'zwave', 4)), $scs,
        array_merge($settings, array('excludedObjects' => '7'))),
    'scénario ajouté' => array($eqs, array_merge($scs, array(sc_row(13, false))), $settings),
    'scénario supprimé' => array($eqs, array(sc_row(10, true), sc_row(11, false)), $settings),
    'publishedScenarios' => array($eqs, $scs, array_merge($settings, array('publishedScenarios' => array(10)))),
    'knownScenarioIds' => array($eqs, $scs, array_merge($settings, array('knownScenarioIds' => array(10, 11)))),
);
$oldBase = jeedom2ha_decision_fingerprint($eqs, $scs, $settings);
foreach ($cases as $label => $args) {
    $oldChanged = jeedom2ha_decision_fingerprint($args[0], $args[1], $args[2]) !== $oldBase;
    $newChanged = jeedom2ha_decision_fingerprint_parts($args[0], $args[1], $args[2])['fingerprint'] !== $p['fingerprint'];
    check("M2 ({$label}) : l'ancienne empreinte change et la composite aussi", $oldChanged && $newChanged);
}
// Et inversement : ce qui ne change pas l'ancienne ne change pas la composite.
check('M2 : ordre, noms et ligne illisible sans effet sur les deux',
    jeedom2ha_decision_fingerprint(array_reverse($named), array_reverse($namedSc), $settings) === $oldBase
    && jeedom2ha_decision_fingerprint_parts(array_reverse($named), array_merge(array_reverse($namedSc), array(array('id' => 'x'))), $settings)['fingerprint'] === $p['fingerprint']);

// Lecture de la composite et choix du chemin.
check('composite lisible', jeedom2ha_reevaluation_parse_fingerprint($p['fingerprint']) === array('structural' => $p['structural'], 'activation' => $p['activation']));
check('ancien format (24.14) illisible en deux parties', jeedom2ha_reevaluation_parse_fingerprint(hash('sha256', 'x')) === null
    && jeedom2ha_reevaluation_parse_fingerprint('') === null && jeedom2ha_reevaluation_parse_fingerprint('v2:abc') === null);
check('chemin léger : structure égale, activation différente', jeedom2ha_reevaluation_light_candidate($p['fingerprint'], $toggled['fingerprint']));
check('pas de chemin léger : structure différente', !jeedom2ha_reevaluation_light_candidate($p['fingerprint'],
    jeedom2ha_decision_fingerprint_parts($e, array(sc_row(10, false), sc_row(11, false), sc_row(12, true)), $settings)['fingerprint']));
check('pas de chemin léger : ancien format stocké', !jeedom2ha_reevaluation_light_candidate(hash('sha256', 'x'), $toggled['fingerprint']));
check('pas de chemin léger : rien de stocké', !jeedom2ha_reevaluation_light_candidate('', $toggled['fingerprint']));
check('pas de chemin léger : identiques', !jeedom2ha_reevaluation_light_candidate($p['fingerprint'], $p['fingerprint']));

// ---------------------------------------------------------------------------
// AC2 à AC6 — pas de la tâche périodique
// ---------------------------------------------------------------------------
echo "Pas de la tâche périodique\n";
$OLD = $p['fingerprint'];
$NEW_LIGHT = $toggled['fingerprint'];
$NEW_STRUCT = jeedom2ha_decision_fingerprint_parts($e, array(sc_row(10, false), sc_row(11, false), sc_row(12, true)), $settings)['fingerprint'];

function make_deps($stored, $current, array $over = array()) {
    $state = (object) array('stored' => $stored, 'current' => $current, 'calls' => array(), 'logs' => array(), 'sent' => null);
    $deps = array(
        'fingerprint' => function () use ($state) {
            return array('fingerprint' => $state->current, 'states' => array(array('id' => 10, 'is_active' => false)));
        },
        'stored' => function () use ($state) { return $state->stored; },
        'store' => function ($f) use ($state) { $state->stored = $f; $state->calls[] = 'store'; },
        'ready' => function () use ($state) { $state->calls[] = 'ready'; return true; },
        'topology' => function () use ($state) { $state->calls[] = 'topology'; return array('eq_logics' => array()); },
        'sync' => function ($t) use ($state) { $state->calls[] = 'sync'; return array('status' => 'ok'); },
        'light' => function ($states) use ($state) {
            $state->calls[] = 'light'; $state->sent = $states;
            return array('status' => 'ok', 'result' => 'applied', 'scenario_ids' => array(10));
        },
        'listeners' => function () use ($state) { $state->calls[] = 'listeners'; },
        'log' => function ($level, $message) use ($state) { $state->logs[] = array($level, $message); },
    );
    foreach ($over as $k => $v) { $deps[$k] = $v; }
    return array($deps, $state);
}

// AC2 — seule l'activation change.
list($deps, $st) = make_deps($OLD, $NEW_LIGHT);
$r = jeedom2ha_reevaluation_tick($deps);
check('AC2 : chemin léger, statut light', $r['status'] === 'light');
check('AC2 : un seul appel léger, ni topologie, ni synchro complète, ni listeners',
    $st->calls === array('ready', 'store', 'light', 'store'));
check('AC2 : états des scénarios publiés envoyés', $st->sent === array(array('id' => 10, 'is_active' => false)));
check('AC2 : composite mémorisée (les deux parties)', $st->stored === $NEW_LIGHT);

// AC6 — deux pas stables.
list($deps2, $st2) = make_deps($st->stored, $NEW_LIGHT);
$r = jeedom2ha_reevaluation_tick($deps2);
check('AC6 : pas suivant sans changement : unchanged, aucun appel', $r['status'] === 'unchanged' && $st2->calls === array());

// « unchanged » du démon (déjà à jour) : composite mémorisée aussi.
list($deps, $st) = make_deps($OLD, $NEW_LIGHT, array('light' => function ($s) { return array('status' => 'ok', 'result' => 'unchanged'); }));
$r = jeedom2ha_reevaluation_tick($deps);
check('démon déjà à jour : light, composite mémorisée', $r['status'] === 'light' && $st->stored === $NEW_LIGHT);

// AC3 — activation et autre chose ensemble.
list($deps, $st) = make_deps($OLD, $NEW_STRUCT);
$r = jeedom2ha_reevaluation_tick($deps);
check('AC3 : structure changée : synchro complète, listeners, pas d\'appel léger',
    $r['status'] === 'synced' && in_array('sync', $st->calls, true) && in_array('listeners', $st->calls, true)
    && !in_array('light', $st->calls, true));
list($deps, $st) = make_deps(hash('sha256', 'ancien'), $NEW_LIGHT);
$r = jeedom2ha_reevaluation_tick($deps);
check('AC3 : ancien format stocké : synchro complète', $r['status'] === 'synced' && !in_array('light', $st->calls, true) && $st->stored === $NEW_LIGHT);
list($deps, $st) = make_deps('', $NEW_LIGHT);
check('AC3 : rien de stocké : synchro complète', jeedom2ha_reevaluation_tick($deps)['status'] === 'synced' && !in_array('light', $st->calls, true));
list($deps, $st) = make_deps($OLD, $NEW_LIGHT);
unset($deps['light']);
check('sans dépendance light : comportement 24.14 (synchro complète)', jeedom2ha_reevaluation_tick($deps)['status'] === 'synced');

// Démon non prêt : rien, même sur le chemin léger.
list($deps, $st) = make_deps($OLD, $NEW_LIGHT, array('ready' => function () { return false; }));
$r = jeedom2ha_reevaluation_tick($deps);
check('démon non prêt : skipped, rien envoyé, empreinte intacte', $r['reason'] === 'daemon_not_ready' && $st->stored === $OLD && $st->sent === null);

// AC4 — le démon doute : synchro complète dans le même pas.
list($deps, $st) = make_deps($OLD, $NEW_LIGHT, array('light' => function ($s) {
    return array('status' => 'error', 'code' => 'full_sync_required', 'reason' => 'pending_overrides');
}));
$r = jeedom2ha_reevaluation_tick($deps);
check('AC4 : full_sync_required : synchro complète dans le même pas',
    $r['status'] === 'synced' && in_array('sync', $st->calls, true) && in_array('listeners', $st->calls, true) && $st->stored === $NEW_LIGHT);

// AC5 — échecs du chemin léger puis retour à la synchro complète au pas suivant.
$failures = array(
    'exception' => function ($s) { throw new RuntimeException('boom'); },
    'aucune réponse' => function ($s) { return null; },
    'publication en échec' => function ($s) { return array('status' => 'error', 'code' => 'publish_failed', 'scenario_ids' => array(10)); },
    'broker injoignable' => function ($s) { return array('status' => 'error', 'code' => 'broker_unavailable'); },
);
foreach ($failures as $label => $fn) {
    list($deps, $st) = make_deps($OLD, $NEW_LIGHT, array('light' => $fn));
    $r = jeedom2ha_reevaluation_tick($deps);
    check("AC5 ({$label}) : failed, empreinte vide, pas de synchro complète dans ce pas",
        $r['status'] === 'failed' && $st->stored === '' && !in_array('sync', $st->calls, true));
    list($deps2, $st2) = make_deps($st->stored, $NEW_LIGHT);
    $r2 = jeedom2ha_reevaluation_tick($deps2);
    check("AC5 ({$label}) : pas suivant : synchro complète",
        $r2['status'] === 'synced' && in_array('sync', $st2->calls, true) && !in_array('light', $st2->calls, true));
}
// 409 : rien n'est remis (l'opération en cours peut être une relecture qui a invalidé l'empreinte, revue 24.18) :
// empreinte vide, synchro complète au pas suivant, comme le 409 de la synchro complète en 24.14.
list($deps, $st) = make_deps($OLD, $NEW_LIGHT, array('light' => function ($s) {
    return array('status' => 'error', 'code' => 'action_in_progress');
}));
$r = jeedom2ha_reevaluation_tick($deps);
check('409 : deferred, empreinte vide, pas de synchro complète dans ce pas',
    $r['status'] === 'deferred' && $st->stored === '' && !in_array('sync', $st->calls, true));
list($deps2, $st2) = make_deps($st->stored, $NEW_LIGHT);
check('409 : pas suivant : synchro complète', jeedom2ha_reevaluation_tick($deps2)['status'] === 'synced');

// Une dépendance `fingerprint` qui rend une chaîne (24.14) : pas de chemin léger possible (pas d'états).
list($deps, $st) = make_deps($OLD, $NEW_LIGHT, array('fingerprint' => function () use ($NEW_LIGHT) { return $NEW_LIGHT; }));
$r = jeedom2ha_reevaluation_tick($deps);
check('empreinte en chaîne seule : synchro complète', $r['status'] === 'synced' && !in_array('light', $st->calls, true));

// Revue 24.18 (M4) — au-delà du plafond, pas de chemin léger (le démon répondrait 400) : synchro complète.
$many = array();
for ($i = 1; $i <= JEEDOM2HA_REEVALUATION_LIGHT_MAX_SCENARIOS + 1; $i++) { $many[] = array('id' => $i, 'is_active' => true); }
list($deps, $st) = make_deps($OLD, $NEW_LIGHT, array('fingerprint' => function () use ($NEW_LIGHT, $many) {
    return array('fingerprint' => $NEW_LIGHT, 'states' => $many);
}));
$r = jeedom2ha_reevaluation_tick($deps);
check('M4 : liste au-delà du plafond : synchro complète, pas d\'appel léger', $r['status'] === 'synced' && !in_array('light', $st->calls, true));

// ---------------------------------------------------------------------------
// Câblage dans la classe
// ---------------------------------------------------------------------------
echo "Câblage\n";
$class = file_get_contents($root . '/core/class/jeedom2ha.class.php');
check('readDecisionFingerprintParts existe', strpos($class, 'public static function readDecisionFingerprintParts(): array') !== false);
check('readDecisionFingerprint rend la composite', strpos($class, "return self::readDecisionFingerprintParts()['fingerprint'];") !== false);
check('la tâche périodique lit les deux parties', strpos($class, 'return self::readDecisionFingerprintParts();') !== false);
check('la tâche périodique branche la route légère', strpos($class, "self::callDaemon('/action/scenario_activation', array('scenarios' => \$states), 'POST'") !== false);
check('la requête des scénarios ne lit aucun nom', strpos($class, "SELECT `id`, `isActive` FROM `scenario`") !== false);

echo "\n{$passed} réussis, {$failed} échoués\n";
exit($failed === 0 ? 0 : 1);
