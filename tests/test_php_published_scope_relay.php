<?php
require_once __DIR__ . '/../../../core/php/core.inc.php';
require_once __DIR__ . '/../core/class/jeedom2ha.class.php';

$failures = array();

function assertTrueRelay($condition, $message) {
  global $failures;
  if ($condition) {
    echo "PASS: " . $message . PHP_EOL;
    return;
  }
  $failures[] = $message;
  echo "FAIL: " . $message . PHP_EOL;
}

function assertSameRelay($expected, $actual, $message) {
  $details = sprintf('%s (expected=%s actual=%s)', $message, var_export($expected, true), var_export($actual, true));
  assertTrueRelay($expected === $actual, $details);
}

echo "Testing published_scope relay helper..." . PHP_EOL;

assertTrueRelay(
  method_exists('jeedom2ha', 'getPublishedScopeForConsole'),
  'jeedom2ha::getPublishedScopeForConsole exists'
);

$backendContract = array(
  'global' => array(
    'counts' => array('total' => 3, 'include' => 1, 'exclude' => 2, 'exceptions' => 1),
    'has_pending_home_assistant_changes' => false,
  ),
  'pieces' => array(
    array(
      'object_id' => 1,
      'object_name' => 'Salon',
      'counts' => array('total' => 3, 'include' => 1, 'exclude' => 2, 'exceptions' => 1),
      'has_pending_home_assistant_changes' => false,
    ),
  ),
  'equipements' => array(
    array(
      'eq_id' => 10,
      'name' => 'Lampe exclue',
      'object_id' => 1,
      'effective_state' => 'exclude',
      'decision_source' => 'piece',
      'is_exception' => false,
      'has_pending_home_assistant_changes' => false,
    ),
    array(
      'eq_id' => 11,
      'name' => 'Lampe incluse locale',
      'object_id' => 1,
      'effective_state' => 'include',
      'decision_source' => 'exception_equipement',
      'is_exception' => true,
      'has_pending_home_assistant_changes' => false,
    ),
  ),
);

$relayOk = jeedom2ha::getPublishedScopeForConsole(function () use ($backendContract) {
  return array(
    'status' => 'ok',
    'payload' => $backendContract,
  );
});

assertSameRelay('ok', $relayOk['status'] ?? null, 'Relay returns status ok when daemon contract is available');
assertSameRelay($backendContract, $relayOk['published_scope'] ?? null, 'Relay forwards backend contract without recompute or regroup');
assertSameRelay(2, count($relayOk['published_scope']['equipements'] ?? array()), 'Relay keeps excluded and exception equipment entries visible for UI');

$relayUnavailable = jeedom2ha::getPublishedScopeForConsole(function () {
  return array(
    'status' => 'error',
    'message' => 'Contrat indisponible',
  );
});

assertSameRelay('unavailable', $relayUnavailable['status'] ?? null, 'Relay returns unavailable status when backend contract is missing');
assertTrueRelay(
  is_string($relayUnavailable['message'] ?? null) && $relayUnavailable['message'] !== '',
  'Relay unavailable response includes explicit user-facing message'
);

if (!empty($failures)) {
  echo PHP_EOL . count($failures) . " assertion(s) failed." . PHP_EOL;
  exit(1);
}

echo PHP_EOL . "All published_scope relay assertions passed." . PHP_EOL;
exit(0);
