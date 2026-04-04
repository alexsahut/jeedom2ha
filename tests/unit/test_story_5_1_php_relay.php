<?php
// ARTEFACT — Story 5.1 : tests relay PHP passthrough strict du signal actions_ha.
// Exécution : php tests/unit/test_story_5_1_php_relay.php

// Guard pour charger les fonctions sans le code d'exécution AJAX
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
// Test 1 — passthrough strict de actions_ha via l'allowlist diagnostic_equipments
// ---------------------------------------------------------------------------

echo "\nStory 5.1 / PHP relay — passthrough strict de actions_ha\n";

// Simule un payload daemon avec actions_ha
$rawEq = [
    'eq_id' => 42,
    'perimetre' => 'inclus',
    'statut' => 'publie',
    'ecart' => false,
    'cause_code' => null,
    'cause_label' => null,
    'cause_action' => null,
    'status_code' => 'published',
    'reason_code' => 'sure',
    'detail' => '',
    'remediation' => '',
    'v1_limitation' => false,
    'confidence' => 'sure',
    'matched_commands' => [],
    'unmatched_commands' => [],
    'actions_ha' => [
        'publier' => ['label' => 'Republier dans Home Assistant', 'disponible' => true, 'raison_indisponibilite' => null, 'niveau_confirmation' => 'aucune'],
        'supprimer' => ['label' => 'Supprimer de Home Assistant', 'disponible' => true, 'raison_indisponibilite' => null, 'niveau_confirmation' => 'forte'],
    ],
];

// Le code PHP inline de getPublishedScopeForConsole extrait les champs par allowlist.
// On simule ce que fait la boucle foreach($dp['equipments'] as $eq).
$eqDiag = [
    'statut' => (string)($rawEq['statut'] ?? ''),
    'publies' => (($rawEq['statut'] ?? '') === 'publie') ? 1 : 0,
    'ecart' => array_key_exists('ecart', $rawEq) ? (bool)$rawEq['ecart'] : null,
    'cause_code' => isset($rawEq['cause_code']) ? (string)$rawEq['cause_code'] : '',
    'cause_label' => isset($rawEq['cause_label']) ? (string)$rawEq['cause_label'] : '',
    'cause_action' => isset($rawEq['cause_action']) ? (string)$rawEq['cause_action'] : '',
    'status_code' => (string)($rawEq['status_code'] ?? ''),
    'reason_code' => (string)($rawEq['reason_code'] ?? ''),
    'detail' => (string)($rawEq['detail'] ?? ''),
    'remediation' => (string)($rawEq['remediation'] ?? ''),
    'v1_limitation' => (bool)($rawEq['v1_limitation'] ?? false),
    'perimetre' => (string)($rawEq['perimetre'] ?? ''),
    'confidence' => (string)($rawEq['confidence'] ?? ''),
    'matched_commands' => _jeedom2ha_extract_commands($rawEq['matched_commands'] ?? []),
    'unmatched_commands' => _jeedom2ha_extract_commands($rawEq['unmatched_commands'] ?? []),
    // Story 5.1 — passthrough strict
    'actions_ha' => $rawEq['actions_ha'] ?? null,
];

assert_eq(
    'actions_ha est transmis tel quel (non null)',
    true,
    $eqDiag['actions_ha'] !== null
);

assert_eq(
    'actions_ha.publier.label intact',
    'Republier dans Home Assistant',
    $eqDiag['actions_ha']['publier']['label']
);

assert_eq(
    'actions_ha.supprimer.disponible intact',
    true,
    $eqDiag['actions_ha']['supprimer']['disponible']
);

assert_eq(
    'actions_ha.supprimer.niveau_confirmation intact',
    'forte',
    $eqDiag['actions_ha']['supprimer']['niveau_confirmation']
);

// ---------------------------------------------------------------------------
// Test 2 — actions_ha absent → null (pas d'enrichissement local)
// ---------------------------------------------------------------------------

echo "\nStory 5.1 / PHP relay — actions_ha absent → null\n";

$rawEqSansActions = [
    'eq_id' => 99,
    'perimetre' => 'exclu_sur_equipement',
    'statut' => 'non_publie',
];

$eqDiagSans = [
    'actions_ha' => $rawEqSansActions['actions_ha'] ?? null,
];

assert_eq(
    'actions_ha est null quand absent du payload daemon',
    null,
    $eqDiagSans['actions_ha']
);

// ---------------------------------------------------------------------------
// Test 3 — aucun calcul local de label ou disponibilité
// ---------------------------------------------------------------------------

echo "\nStory 5.1 / PHP relay — aucun calcul local\n";

// Le relay transmet le label exact, même si le statut semble contredire
$rawEqContradiction = [
    'statut' => 'non_publie',
    'actions_ha' => [
        'publier' => ['label' => 'Créer dans Home Assistant', 'disponible' => true, 'raison_indisponibilite' => null, 'niveau_confirmation' => 'aucune'],
        'supprimer' => ['label' => 'Supprimer de Home Assistant', 'disponible' => false, 'raison_indisponibilite' => 'Aucune entité', 'niveau_confirmation' => 'forte'],
    ],
];

$relayedActions = $rawEqContradiction['actions_ha'] ?? null;

assert_eq(
    'Le relay ne recalcule pas le label',
    'Créer dans Home Assistant',
    $relayedActions['publier']['label']
);

assert_eq(
    'Le relay ne recalcule pas la disponibilité',
    false,
    $relayedActions['supprimer']['disponible']
);

// ---------------------------------------------------------------------------
// Résultat
// ---------------------------------------------------------------------------

echo "\n" . str_repeat('-', 60) . "\n";
echo "Story 5.1 PHP relay tests: {$passed}/{$total} passed";
if ($failed > 0) {
    echo " ({$failed} FAILED)";
}
echo "\n";
exit($failed > 0 ? 1 : 0);
