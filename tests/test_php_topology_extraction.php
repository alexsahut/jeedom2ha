<?php

function requireFirstExisting(array $candidates, $label) {
    foreach ($candidates as $candidate) {
        if (file_exists($candidate)) {
            require_once $candidate;
            return;
        }
    }
    fwrite(STDERR, "Unable to locate " . $label . " in candidates:\n- " . implode("\n- ", $candidates) . "\n");
    exit(1);
}

requireFirstExisting(
    array(
        __DIR__ . '/../../../core/php/core.inc.php',
        __DIR__ . '/../../core/php/core.inc.php',
    ),
    'Jeedom core bootstrap'
);

requireFirstExisting(
    array(
        __DIR__ . '/../core/class/jeedom2ha.class.php',
        __DIR__ . '/../../plugins/jeedom2ha/core/class/jeedom2ha.class.php',
    ),
    'jeedom2ha class file'
);

$failures = array();

function assertTrueTopology($condition, $message) {
    global $failures;
    if ($condition) {
        echo "PASS: " . $message . PHP_EOL;
        return;
    }
    $failures[] = $message;
    echo "FAIL: " . $message . PHP_EOL;
}

function assertSameTopology($expected, $actual, $message) {
    $details = sprintf('%s (expected=%s actual=%s)', $message, var_export($expected, true), var_export($actual, true));
    assertTrueTopology($expected === $actual, $details);
}

function findCandidateEqForExcludedObjectsProducer(array $topology) {
    $scope = isset($topology['published_scope']) && is_array($topology['published_scope']) ? $topology['published_scope'] : array();
    $piecesScope = isset($scope['pieces']) && is_array($scope['pieces']) ? $scope['pieces'] : array();
    $eqScope = isset($scope['equipements']) && is_array($scope['equipements']) ? $scope['equipements'] : array();
    $eqLogics = isset($topology['eq_logics']) && is_array($topology['eq_logics']) ? $topology['eq_logics'] : array();

    foreach ($eqLogics as $eq) {
        if (!is_array($eq)) {
            continue;
        }

        if (!isset($eq['id']) || !isset($eq['object_id']) || $eq['object_id'] === null) {
            continue;
        }

        if (!empty($eq['is_excluded'])) {
            continue;
        }

        $eqId = intval($eq['id']);
        $objectId = intval($eq['object_id']);
        $pieceKey = strval($objectId);
        $eqKey = strval($eqId);

        $pieceEntry = isset($piecesScope[$pieceKey]) && is_array($piecesScope[$pieceKey]) ? $piecesScope[$pieceKey] : null;
        $eqEntry = isset($eqScope[$eqKey]) && is_array($eqScope[$eqKey]) ? $eqScope[$eqKey] : null;
        if ($pieceEntry === null || $eqEntry === null) {
            continue;
        }

        if (($pieceEntry['raw_state'] ?? null) !== 'inherit' || ($pieceEntry['source'] ?? null) !== 'default_inherit') {
            continue;
        }
        if (($eqEntry['raw_state'] ?? null) !== 'inherit' || ($eqEntry['source'] ?? null) !== 'default_inherit') {
            continue;
        }

        return array('eq_id' => $eqId, 'object_id' => $objectId);
    }

    return null;
}

function mapEqById(array $eqLogics) {
    $byId = array();
    foreach ($eqLogics as $eq) {
        if (is_array($eq) && isset($eq['id'])) {
            $byId[intval($eq['id'])] = $eq;
        }
    }
    return $byId;
}

function restoreTopologyProducerConfig(array $snapshot) {
    foreach ($snapshot as $key => $value) {
        config::save($key, $value, 'jeedom2ha');
    }
}

echo "Testing scenarios_complete producer flag (Story 21.1)..." . PHP_EOL;

function makeScenarioStub($id, $name, $active, $throws = false) {
    return new class($id, $name, $active, $throws) {
        private $id;
        private $name;
        private $active;
        private $throws;
        public function __construct($id, $name, $active, $throws) {
            $this->id = $id;
            $this->name = $name;
            $this->active = $active;
            $this->throws = $throws;
        }
        public function getId() {
            if ($this->throws) {
                throw new Exception('unreadable scenario');
            }
            return $this->id;
        }
        public function getName() { return $this->name; }
        public function getIsActive() { return $this->active; }
    };
}

$fullRead = jeedom2ha::buildScenariosPayload(array(
    makeScenarioStub(20, 'S20', 1),
    makeScenarioStub(72, 'S72', 0),
));
assertSameTopology(true, $fullRead['complete'], 'scenarios_complete is true when the whole list is read');
assertSameTopology(2, count($fullRead['scenarios']), 'all scenarios are listed when the whole list is read');
assertSameTopology(false, $fullRead['scenarios'][1]['is_active'], 'is_active is cast to bool');

$partialRead = jeedom2ha::buildScenariosPayload(array(
    makeScenarioStub(20, 'S20', 1),
    makeScenarioStub(21, 'S21', 1, true),
));
assertSameTopology(false, $partialRead['complete'], 'scenarios_complete is false when one scenario throws');
assertSameTopology(1, count($partialRead['scenarios']), 'readable scenarios are still listed when one throws');

$noClass = jeedom2ha::buildScenariosPayload(null);
assertSameTopology(false, $noClass['complete'], 'scenarios_complete is false when the scenario class is absent');
assertSameTopology(array(), $noClass['scenarios'], 'no scenarios when the scenario class is absent');

$emptyRead = jeedom2ha::buildScenariosPayload(array());
assertSameTopology(true, $emptyRead['complete'], 'scenarios_complete is true for a fully read empty list');

echo "Testing getFullTopology() producer chain..." . PHP_EOL;

$configSnapshot = array(
    'excludedObjects' => config::byKey('excludedObjects', 'jeedom2ha', ''),
    'excludedPlugins' => config::byKey('excludedPlugins', 'jeedom2ha', ''),
    'publishedScopeGlobalState' => config::byKey('publishedScopeGlobalState', 'jeedom2ha', 'inherit'),
    'publishedScopeObjectsStates' => config::byKey('publishedScopeObjectsStates', 'jeedom2ha', '{}'),
    'publishedScopeEqLogicsStates' => config::byKey('publishedScopeEqLogicsStates', 'jeedom2ha', '{}'),
);

try {
    // Keep producer payload deterministic for the proof.
    config::save('excludedObjects', '', 'jeedom2ha');
    config::save('excludedPlugins', '', 'jeedom2ha');
    config::save('publishedScopeGlobalState', 'inherit', 'jeedom2ha');
    config::save('publishedScopeObjectsStates', '{}', 'jeedom2ha');
    config::save('publishedScopeEqLogicsStates', '{}', 'jeedom2ha');

    $topologyBefore = jeedom2ha::getFullTopology();
    assertTrueTopology(is_array($topologyBefore), 'getFullTopology returns an array');
    assertTrueTopology(array_key_exists('scenarios_complete', $topologyBefore) && is_bool($topologyBefore['scenarios_complete']), 'scenarios_complete is a boolean in the topology payload');
    assertTrueTopology(isset($topologyBefore['published_scope']) && is_array($topologyBefore['published_scope']), 'published_scope exists in topology payload');

    $scopeBefore = $topologyBefore['published_scope'] ?? array();
    foreach (array('global', 'pieces', 'equipements') as $requiredKey) {
        assertTrueTopology(array_key_exists($requiredKey, $scopeBefore), 'published_scope.' . $requiredKey . ' is present');
    }

    $candidate = findCandidateEqForExcludedObjectsProducer($topologyBefore);
    assertTrueTopology($candidate !== null, 'Found a non-excluded equipment with default_inherit scope markers for excludedObjects producer proof');

    if ($candidate !== null) {
        $targetEqId = intval($candidate['eq_id']);
        $targetObjectId = intval($candidate['object_id']);
        config::save('excludedObjects', strval($targetObjectId), 'jeedom2ha');

        $topologyAfter = jeedom2ha::getFullTopology();
        $scopeAfter = $topologyAfter['published_scope'] ?? array();
        $pieceKey = strval($targetObjectId);
        $eqKey = strval($targetEqId);

        $pieceEntry = $scopeAfter['pieces'][$pieceKey] ?? null;
        assertTrueTopology(is_array($pieceEntry), 'Target object still has a published_scope piece entry after excludedObjects change');
        assertSameTopology('inherit', $pieceEntry['raw_state'] ?? null, 'Piece raw_state remains inherit in producer payload (default marker case)');
        assertSameTopology('default_inherit', $pieceEntry['source'] ?? null, 'Piece source remains default_inherit in producer payload');

        $eqByIdAfter = mapEqById($topologyAfter['eq_logics'] ?? array());
        $targetEqAfter = $eqByIdAfter[$targetEqId] ?? null;
        assertTrueTopology(is_array($targetEqAfter), 'Target equipment remains present in eq_logics after excludedObjects change');
        assertSameTopology(true, (bool)($targetEqAfter['is_excluded'] ?? false), 'excludedObjects marks target equipment as excluded in getFullTopology output');
        assertSameTopology('object', $targetEqAfter['exclusion_source'] ?? null, 'excludedObjects maps target equipment to exclusion_source=object');

        $eqScopeEntry = $scopeAfter['equipements'][$eqKey] ?? null;
        assertTrueTopology(is_array($eqScopeEntry), 'Target equipment still has a published_scope entry after excludedObjects change');
        assertSameTopology('inherit', $eqScopeEntry['raw_state'] ?? null, 'Equipment raw_state remains inherit in producer payload');
        assertSameTopology('default_inherit', $eqScopeEntry['source'] ?? null, 'Equipment source remains default_inherit in producer payload');
    }
} catch (Throwable $e) {
    $failures[] = 'Unhandled exception: ' . $e->getMessage();
    echo "FATAL ERROR: " . $e->getMessage() . PHP_EOL;
    echo $e->getTraceAsString() . PHP_EOL;
} finally {
    restoreTopologyProducerConfig($configSnapshot);
}

if (!empty($failures)) {
    echo PHP_EOL . count($failures) . " assertion(s) failed." . PHP_EOL;
    exit(1);
}

echo PHP_EOL . "All getFullTopology producer assertions passed." . PHP_EOL;
exit(0);
