'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');
const { pathToFileURL } = require('node:url');

const mod = () => import(pathToFileURL(path.join(
  __dirname,
  '..',
  'e2e',
  'gate',
  'lib',
  'report.mjs',
)).href);

test('story 20-0 — identifiants incomplets refusés', async () => {
  const { parseCredentials } = await mod();
  assert.throws(() => parseCredentials('JEEDOM_USER=clawcode\n'), /identifiants-incomplets/);
});

test('story 20-0 — getBridgeStatus extrait sa forme réelle', async () => {
  const { extractBridgeStatus } = await mod();
  const witness = extractBridgeStatus({
    state: 'ok',
    result: {
      daemon: true,
      derniere_synchro_terminee: '2026-10-02T12:00:00+00:00',
      derniere_operation_resultat: { timestamp: '2026-10-02T12:00:01+00:00' },
    },
  });
  assert.equal(witness.daemon, true);
  assert.equal(witness.derniere_operation_timestamp, '2026-10-02T12:00:01+00:00');
  assert.throws(() => extractBridgeStatus({ state: 'ok', result: { daemon: false } }));
  assert.throws(() => extractBridgeStatus({ state: 'ok', result: { daemon: true } }));
});

test('story 20-0 — getKey en erreur rend la sonde illisible', async () => {
  const { CONFIG_KEYS, extractConfigValues } = await mod();
  const responses = Object.fromEntries(CONFIG_KEYS.map((key) => [key, { state: 'ok', result: '' }]));
  responses.mqttPassword = { state: 'error', result: 'message-d-erreur' };
  assert.throws(() => extractConfigValues(responses), /sonde-config-illisible:mqttPassword/);
});

test('story 20-0 — les cinq vérifications et la ligne activité sont calculées séparément', async () => {
  const { calculateChecks } = await mod();
  const result = calculateChecks({
    journal: { failed: false },
    witnessDifferences: ['daemon-pid'],
    probeDifferences: [],
    window: { daemon: { '[DISCOVERY]': 0 }, daemonErrors: 0, pluginErrors: 1 },
    consoleErrors: [],
    failure: null,
  });
  assert.deepEqual(result.checks, {
    ac3_1_interception: true,
    ac3_2_box: false,
    ac3_3_console: true,
    ac3_4_logs: false,
    ac3_5_report: true,
  });
  assert.equal(result.activity, true);
});

test('story 20-0 — les URLs de console perdent toute query string', async () => {
  const { sanitizeUrl } = await mod();
  const value = 'Erreur https://box.test/path?apikey=secret&x=1 suite';
  assert.equal(sanitizeUrl(value), 'Erreur https://box.test/path?… suite');
});

test('story 20-0 — la raison conserve une ligne, assainie et bornée', async () => {
  const { sanitizeReason } = await mod();
  const detail = `https://box.test/path?apikey=secret ${'x'.repeat(400)}\ntrace Playwright`;
  const result = sanitizeReason(new Error(detail));
  assert.equal(result.includes('apikey=secret'), false);
  assert.equal(result.includes('\n'), false);
  assert.equal(result.length, 300);
});

test('story 20-0 — les constats de parcours sont strictement bornés', async () => {
  const { normalizeParcoursRecord } = await mod();
  assert.deepEqual(normalizeParcoursRecord('cmd_42_etat', 'prete'), ['cmd_42_etat', 'prete']);
  assert.throws(() => normalizeParcoursRecord('cmd?42', 'prete'));
  assert.throws(() => normalizeParcoursRecord('etat', 'a=b'));
  assert.throws(() => normalizeParcoursRecord('etat', 'x'.repeat(81)));
});

test('story 20-0 — AC4 détecte la valeur longue et ignore une config courte', async () => {
  const { ac4Values, artifactsContain } = await mod();
  const values = ac4Values(['user', 'password-long'], {
    mqttHost: 'court',
    mqttPassword: 'secret-config',
  });
  assert.equal(artifactsContain(values, ['rapport secret-config']), true);
  assert.equal(artifactsContain(values, ['rapport court']), false);
});
