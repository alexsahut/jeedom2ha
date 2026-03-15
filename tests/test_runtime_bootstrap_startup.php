<?php
require_once __DIR__ . '/../../../core/php/core.inc.php';
require_once __DIR__ . '/../core/class/jeedom2ha.class.php';

$failures = array();

function assertTrue($condition, $message) {
  global $failures;
  if ($condition) {
    echo "PASS: " . $message . PHP_EOL;
    return;
  }

  $failures[] = $message;
  echo "FAIL: " . $message . PHP_EOL;
}

function assertSameValue($expected, $actual, $message) {
  $details = sprintf('%s (expected=%s actual=%s)', $message, var_export($expected, true), var_export($actual, true));
  assertTrue($expected === $actual, $details);
}

function assertArrayHasKeyValue($array, $key, $expected, $message) {
  $actual = is_array($array) && array_key_exists($key, $array) ? $array[$key] : null;
  assertSameValue($expected, $actual, $message);
}

echo "Testing daemon startup runtime bootstrap..." . PHP_EOL;

assertTrue(method_exists('jeedom2ha', 'isDaemonMqttReady'), 'jeedom2ha::isDaemonMqttReady exists');
assertTrue(method_exists('jeedom2ha', 'bootstrapRuntimeAfterDaemonStart'), 'jeedom2ha::bootstrapRuntimeAfterDaemonStart exists');

$readyStatus = array(
  'status' => 'ok',
  'payload' => array(
    'mqtt' => array(
      'connected' => true,
      'state' => 'connected',
    ),
  ),
);

assertSameValue(true, jeedom2ha::isDaemonMqttReady($readyStatus), 'Strict MQTT readiness accepts only the exact connected status');
assertSameValue(
  false,
  jeedom2ha::isDaemonMqttReady(array('status' => 'ok', 'payload' => array('mqtt' => array('connected' => false, 'state' => 'connected')))),
  'Strict MQTT readiness rejects disconnected payloads'
);
assertSameValue(
  false,
  jeedom2ha::isDaemonMqttReady(array('status' => 'ok', 'payload' => array('mqtt' => array('connected' => true, 'state' => 'reconnecting')))),
  'Strict MQTT readiness rejects non-connected MQTT states'
);
assertSameValue(
  false,
  jeedom2ha::isDaemonMqttReady(array('status' => 'error', 'payload' => array('mqtt' => array('connected' => true, 'state' => 'connected')))),
  'Strict MQTT readiness requires global status ok'
);

$statusCalls = 0;
$topologyCalls = 0;
$syncCalls = 0;
$topology = array('objects' => array(array('id' => 1)), 'eq_logics' => array(array('id' => 391)));
$statusSequence = array(
  array('status' => 'ok', 'payload' => array('mqtt' => array('connected' => false, 'state' => 'connecting'))),
  $readyStatus,
);
$syncPayload = null;

$success = jeedom2ha::bootstrapRuntimeAfterDaemonStart(
  0.05,
  1,
  function () use (&$statusSequence, &$statusCalls) {
    $statusCalls++;
    if (count($statusSequence) === 0) {
      return null;
    }
    return array_shift($statusSequence);
  },
  function () use (&$topologyCalls, $topology) {
    $topologyCalls++;
    return $topology;
  },
  function ($payload) use (&$syncCalls, &$syncPayload) {
    $syncCalls++;
    $syncPayload = $payload;
    return array('status' => 'ok');
  }
);

assertArrayHasKeyValue($success, 'status', 'success', 'Bootstrap succeeds when MQTT becomes ready');
assertArrayHasKeyValue($success, 'reason', 'sync_completed', 'Bootstrap success reason is explicit');
assertSameValue(2, $statusCalls, 'Bootstrap polls /system/status until readiness is observed');
assertSameValue(1, $topologyCalls, 'Bootstrap fetches topology exactly once on success');
assertSameValue(1, $syncCalls, 'Bootstrap triggers one sync exactly once per startup path');
assertSameValue($topology, $syncPayload, 'Bootstrap reuses the existing topology payload for /action/sync');

$timeoutTopologyCalls = 0;
$timeoutSyncCalls = 0;
$timeoutResult = jeedom2ha::bootstrapRuntimeAfterDaemonStart(
  0.01,
  1,
  function () {
    return array('status' => 'ok', 'payload' => array('mqtt' => array('connected' => false, 'state' => 'connecting')));
  },
  function () use (&$timeoutTopologyCalls) {
    $timeoutTopologyCalls++;
    return array();
  },
  function () use (&$timeoutSyncCalls) {
    $timeoutSyncCalls++;
    return array('status' => 'ok');
  }
);

assertArrayHasKeyValue($timeoutResult, 'status', 'skipped', 'Bootstrap skips cleanly when MQTT readiness times out');
assertArrayHasKeyValue($timeoutResult, 'reason', 'mqtt_not_ready_timeout', 'Bootstrap timeout reason is explicit');
assertSameValue(0, $timeoutTopologyCalls, 'No topology extraction happens before MQTT readiness');
assertSameValue(0, $timeoutSyncCalls, 'No sync call happens before MQTT readiness');

$statusFailureTopologyCalls = 0;
$statusFailureSyncCalls = 0;
$statusFailure = jeedom2ha::bootstrapRuntimeAfterDaemonStart(
  0.05,
  1,
  function () {
    return null;
  },
  function () use (&$statusFailureTopologyCalls) {
    $statusFailureTopologyCalls++;
    return array();
  },
  function () use (&$statusFailureSyncCalls) {
    $statusFailureSyncCalls++;
    return array('status' => 'ok');
  }
);

assertArrayHasKeyValue($statusFailure, 'status', 'failed', 'Bootstrap fails explicitly when /system/status is unavailable');
assertArrayHasKeyValue($statusFailure, 'reason', 'status_request_failed', 'Bootstrap surfaces /system/status failure reason');
assertSameValue(0, $statusFailureTopologyCalls, 'No topology extraction happens when status fetch fails');
assertSameValue(0, $statusFailureSyncCalls, 'No sync call happens when status fetch fails');

$syncFailure = jeedom2ha::bootstrapRuntimeAfterDaemonStart(
  0.05,
  1,
  function () use ($readyStatus) {
    return $readyStatus;
  },
  function () use ($topology) {
    return $topology;
  },
  function () {
    return array('status' => 'error', 'message' => 'sync refused');
  }
);

assertArrayHasKeyValue($syncFailure, 'status', 'failed', 'Bootstrap fails explicitly when /action/sync fails');
assertArrayHasKeyValue($syncFailure, 'reason', 'sync_failed', 'Bootstrap surfaces /action/sync failure reason');

if (!empty($failures)) {
  echo PHP_EOL . count($failures) . " assertion(s) failed." . PHP_EOL;
  exit(1);
}

echo PHP_EOL . "All runtime bootstrap assertions passed." . PHP_EOL;
exit(0);
