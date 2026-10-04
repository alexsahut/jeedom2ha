'use strict';

const assert = require('node:assert/strict');
const { mkdtemp, readFile, rm, writeFile } = require('node:fs/promises');
const os = require('node:os');
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

const runner = () => import(pathToFileURL(path.join(
  __dirname,
  '..',
  'e2e',
  'gate',
  'run-gate.mjs',
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

test('story 20-0 — AC4 ignore une valeur de configuration présente dans un chemin', async () => {
  const { ac4Values, artifactsContain } = await mod();
  const values = ac4Values(['identifiant-prive', 'mot-de-passe-prive'], {
    mqttUser: 'jeedom',
  });
  assert.deepEqual(artifactsContain(values, ['/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php']), []);
});

test('story 20-0 — AC4 étiquette mqttPassword et les deux identifiants', async () => {
  const { ac4Values, artifactsContain } = await mod();
  const values = ac4Values(['identifiant-prive', 'mot-de-passe-prive'], {
    mqttPassword: 'mot-de-passe-mqtt-prive',
  });
  assert.deepEqual(artifactsContain(values, ['identifiant-prive mot-de-passe-prive mot-de-passe-mqtt-prive']), [
    'identifiant', 'mot-de-passe', 'config-mqttPassword',
  ]);
});

test('story 20-0 — AC4 trouve les formes JSON et URL encodées', async () => {
  const { artifactsContain } = await mod();
  const value = 'mot de passe/é';
  assert.deepEqual(artifactsContain([{ categorie: 'secret', valeur: value }], [JSON.stringify(value), encodeURIComponent(value)]), ['secret']);
});

test('story 20-0 — le témoin AC4 ne contient aucune valeur', async () => {
  const { enforceAc4 } = await runner();
  const directory = await mkdtemp(path.join(os.tmpdir(), 'jeedom2ha-ac4-'));
  const values = [
    { categorie: 'identifiant', valeur: 'identifiant-prive' },
    { categorie: 'mot-de-passe', valeur: 'mot-de-passe-prive' },
  ];
  try {
    await writeFile(path.join(directory, 'gate-report.md'), 'identifiant-prive');
    await writeFile(path.join(directory, 'gate-report.json'), 'mot-de-passe-prive');
    await writeFile(path.join(directory, 'gate-report-ac4.txt'), 'ancienne-preuve');
    await assert.rejects(() => enforceAc4(directory, values), /ac4-fuite-rapport:identifiant,mot-de-passe/);
    const witness = await readFile(path.join(directory, 'gate-report-ac4.txt'), 'utf8');
    assert.equal(witness, 'FAIL ac4\nidentifiant\nmot-de-passe\n');
    assert.equal(witness.includes('identifiant-prive'), false);
    assert.equal(witness.includes('mot-de-passe-prive'), false);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('story 20-0 — garde-fou de parcours : journal gelé et API Playwright/imports interdits', async () => {
  const { journalEntriesSnapshot, loadParcours } = await runner();
  const snapshot = journalEntriesSnapshot({ entries: [{ action: 'read', verdict: 'read' }] });
  assert.equal(Object.isFrozen(snapshot), true);
  assert.equal(Object.isFrozen(snapshot[0]), true);
  assert.throws(() => { snapshot[0].action = 'write'; }, /Cannot assign/);

  const directory = await mkdtemp(path.join(os.tmpdir(), 'jeedom2ha-parcours-'));
  const modulePath = path.join(directory, 'refused.mjs');
  try {
    for (const source of [
      'export const run = () => page.context();\n',
      'import x from "./x.mjs"; export const run = () => x;\n',
      'const x = require("x"); export const run = () => x;\n',
      'export const run = () => import("./x.mjs");\n',
    ]) {
      await writeFile(modulePath, source);
      await assert.rejects(() => loadParcours(modulePath), /parcours-refuse/);
    }
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('story 20-0 — navigation : seul document exact ou about:blank est recevable', async () => {
  const { documentAllowed, assertOpenPagesAllowed } = await runner();
  const ctx = { origin: 'https://domobox.famille-sahut.fr' };
  assert.equal(documentAllowed('https://domobox.famille-sahut.fr/index.php?v=d&m=jeedom2ha&p=jeedom2ha', ctx), true);
  assert.equal(documentAllowed('https://domobox.famille-sahut.fr/plugins/x/y.php', ctx), false);
  const journal = { entries: [], failures: [], failed: false };
  const context = { pages: () => [{ url: () => 'https://domobox.famille-sahut.fr/plugins/x/y.php' }] };
  assert.throws(() => assertOpenPagesAllowed(context, ctx, journal), /navigation-non-autorisee/);
  assert.equal(journal.failed, true);
  assert.equal(journal.failures[0].verdict, 'navigation-non-autorisee');
});

test('story 20-0 — statuts de redirection et en-tête Location sont refusés', async () => {
  const interceptor = await import(pathToFileURL(path.join(__dirname, '..', 'e2e', 'gate', 'lib', 'interceptor.mjs')).href);
  for (const status of [301, 302, 303, 307, 308]) assert.equal(interceptor.isRedirectResponse(status, {}), true);
  assert.equal(interceptor.isRedirectResponse(200, { location: '/suite' }), true);
  assert.equal(interceptor.isRedirectResponse(200, { Location: '/suite' }), true);
  assert.equal(interceptor.isRedirectResponse(200, {}), false);
  assert.equal(interceptor.isRedirectResponse(304, {}), false);
});

test('story 20-0 — le garde refuse seulement les requêtes redirigées hors navigation', async () => {
  const { isRedirectedNonNavigationRequest, redirectedRequestFailure } = await runner();
  const request = ({ redirected, navigation }) => ({
    redirectedFrom: () => redirected ? {} : null,
    isNavigationRequest: () => navigation,
    url: () => 'https://box.test/static.js?cache=private',
    method: () => 'GET',
    resourceType: () => 'script',
  });
  assert.equal(isRedirectedNonNavigationRequest(request({ redirected: true, navigation: false })), true);
  assert.equal(isRedirectedNonNavigationRequest(request({ redirected: true, navigation: true })), false);
  assert.equal(isRedirectedNonNavigationRequest(request({ redirected: false, navigation: false })), false);
  assert.equal(isRedirectedNonNavigationRequest({ redirectedFrom: () => { throw new Error('lecture-impossible'); } }), true);

  const journal = { entries: [], failures: [], failed: false };
  redirectedRequestFailure(journal, request({ redirected: true, navigation: false }));
  assert.equal(journal.failed, true);
  assert.deepEqual(journal.failures[0], {
    timestamp: journal.failures[0].timestamp,
    method: 'GET', resourceType: 'script', path: '/static.js', action: null,
    verdict: 'redirection-non-autorisee', reason: 'redirection-non-autorisee',
  });
});

test('story 20-0 — une connexion est journalisée sans clé, et seul le refus échoue', async () => {
  const { recordLoginAttempt } = await runner();
  const success = { entries: [], failures: [], failed: false };
  const accepted = recordLoginAttempt(success, true);
  assert.equal(success.failed, false);
  assert.deepEqual({ ...accepted, timestamp: '<horodatage>' }, {
    timestamp: '<horodatage>', method: 'POST', resourceType: 'request', path: '/core/ajax/user.ajax.php',
    action: 'login', verdict: 'auth', reason: 'connexion-ok',
  });
  assert.equal(Object.hasOwn(accepted, 'keys'), false);

  const refused = { entries: [], failures: [], failed: false };
  const denied = recordLoginAttempt(refused, false);
  assert.equal(refused.failed, true);
  assert.deepEqual(refused.failures, [denied]);
  assert.equal(denied.reason, 'connexion-refusee');
  assert.equal(Object.hasOwn(denied, 'keys'), false);
});

test('story 20-0 — les sondes JSON exigent strictement HTTP 200', async () => {
  const { isExpectedJsonResponse } = await runner();
  assert.equal(isExpectedJsonResponse({ status: () => 200 }), true);
  assert.equal(isExpectedJsonResponse({ status: () => 201 }), false);
  assert.equal(isExpectedJsonResponse({ status: () => 302 }), false);
});

test('story 20-0 — journal de refus : clés triées sans valeur', async () => {
  const interceptor = await import(pathToFileURL(path.join(__dirname, '..', 'e2e', 'gate', 'lib', 'interceptor.mjs')).href);
  const journal = { entries: [] };
  const entry = interceptor.appendEntry(journal, {
    method: 'POST', resourceType: 'xhr', url: 'https://box.test/x?action=read&z=visible',
    postData: 'body=valeur-privee&action=write', action: 'write', verdict: 'block-fail', reason: 'test',
  });
  assert.deepEqual(entry.keys, ['action', 'body', 'z']);
  assert.equal(JSON.stringify(entry).includes('valeur-privee'), false);
  assert.equal(JSON.stringify(entry).includes('visible'), false);
});
