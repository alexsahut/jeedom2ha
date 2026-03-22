<?php
require_once __DIR__  . '/../../core/php/core.inc.php';
require_once __DIR__  . '/../../plugins/jeedom2ha/core/class/jeedom2ha.class.php';

// Mockclass to simulate a broken third-party eqLogic (e.g., enphasesecur)
// which extends eqLogic but does not implement all expected methods correctly,
// or where methods disappear due to version conflicts.
class BrokenEqLogic extends eqLogic {
    // We intentionally override __call to simulate method missing errors
    // if a method is called that isn't explicitly defined here or in the parent
    // in a way that breaks. Actually, just not defining it is enough for `method_exists`
    // to fail if the parent eqLogic class in Jeedom's core changed, but in our mocked
    // test environment inside Jeedom, `eqLogic` has it.
    // To truly test `method_exists` defensive programming, we will use a dummy object
    // and cast it or just rely on the fact that `method_exists` will return false
    // if we unset the method or use a completely different class.
}

// Since we can't easily mock the static `eqLogic::all()` call without a full mocking framework
// inside the Jeedom runtime, we will do a targeted unit test of the array building logic if possible,
// OR we just execute the full topology and ensure it doesn't crash on the current DB.
// To inject a faulty object, we can temporarily mock the DB return or just rely on the PHP syntax check.

// Let's at least test that running the function doesn't crash on the actual Jeedom instance.
echo "Testing getFullTopology()...\n";
try {
    $topology = jeedom2ha::getFullTopology();
    echo "SUCCESS: Topology extracted safely.\n";
    echo "Objects: " . count($topology['objects']) . "\n";
    echo "EqLogics: " . count($topology['eq_logics']) . "\n";

    // Story 1.1 contract check: published_scope minimal root keys must be present.
    if (!isset($topology['published_scope']) || !is_array($topology['published_scope'])) {
        throw new Exception("published_scope missing in topology payload");
    }

    $scope = $topology['published_scope'];
    foreach (['global', 'pieces', 'equipements'] as $requiredKey) {
        if (!array_key_exists($requiredKey, $scope)) {
            throw new Exception("published_scope.$requiredKey missing in topology payload");
        }
    }
    echo "published_scope contract roots: OK (global/pieces/equipements)\n";
    exit(0);
} catch (Throwable $e) {
    echo "FATAL ERROR: " . $e->getMessage() . "\n";
    echo $e->getTraceAsString() . "\n";
    exit(1);
}
