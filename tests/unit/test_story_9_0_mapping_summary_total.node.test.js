'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

function sumPublishedCounters(summary) {
  if (!summary || typeof summary !== 'object') {
    return 0;
  }

  return Object.keys(summary).reduce((acc, key) => {
    if (!key.endsWith('_published')) {
      return acc;
    }
    const numericValue = Number(summary[key]);
    return Number.isFinite(numericValue) ? acc + numericValue : acc;
  }, 0);
}

test('9.0 / AC1+AC5 — configuration.php utilise un calcul dynamique *_published', () => {
  const phpPath = path.resolve(__dirname, '../../plugin_info/configuration.php');
  const source = fs.readFileSync(phpPath, 'utf8');

  assert.match(source, /endsWith\('_published'\)|endsWith\("_published"\)/);
  assert.doesNotMatch(source, /summary\.lights_published/);
  assert.doesNotMatch(source, /summary\.covers_published/);
  assert.doesNotMatch(source, /summary\.switches_published/);
});

test('9.0 / AC2+AC5 — deploy-to-box.sh utilise un calcul jq dynamique *_published', () => {
  const scriptPath = path.resolve(__dirname, '../../scripts/deploy-to-box.sh');
  const source = fs.readFileSync(scriptPath, 'utf8');

  assert.match(source, /to_entries\[\]\s*\|\s*select\(\.key \| endswith\("_published"\)\)/);
  assert.doesNotMatch(source, /\.mapping_summary\.lights_published/);
  assert.doesNotMatch(source, /\.mapping_summary\.covers_published/);
  assert.doesNotMatch(source, /\.mapping_summary\.switches_published/);
});

test('9.0 / AC3 — payload legacy only conserve le total historique', () => {
  const summary = {
    lights_published: 10,
    covers_published: 8,
    switches_published: 5,
    lights_sure: 3,
  };
  assert.equal(sumPublishedCounters(summary), 23);
});

test('9.0 / AC4 — payload forward inclut automatiquement sensors/binary_sensors/buttons', () => {
  const summary = {
    lights_published: 10,
    covers_published: 8,
    switches_published: 5,
    sensors_published: 4,
    binary_sensors_published: 2,
    buttons_published: 1,
    sensors_sure: 99,
  };
  assert.equal(sumPublishedCounters(summary), 30);
});

test('9.0 / AC1+AC2 — valeurs absentes/non numériques ignorées, sans NaN', () => {
  const summary = {
    lights_published: 2,
    covers_published: '3',
    switches_published: null,
    sensors_published: 'abc',
    binary_sensors_published: undefined,
    buttons_published: Number.POSITIVE_INFINITY,
    unrelated_key: 77,
  };
  const total = sumPublishedCounters(summary);

  assert.equal(total, 5);
  assert.equal(Number.isFinite(total), true);
});

test('9.0 / AC1+AC2 — mapping_summary absent retourne 0', () => {
  assert.equal(sumPublishedCounters(undefined), 0);
  assert.equal(sumPublishedCounters(null), 0);
});
