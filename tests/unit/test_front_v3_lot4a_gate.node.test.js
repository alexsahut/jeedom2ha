/**
 * Front v3 (Lot 4a) — politique du gate : `saveScenarioPublication` est une écriture SIMULÉE quand le parcours déclare les
 * scénarios concernés (`declaredScenarioPublications`), comme les simulations déclarées des Lots 5 et 6 de la v2 ; sans
 * déclaration, elle reste un effet de bord BLOQUÉ (elle écrit la configuration et relit Jeedom). Les lectures autorisées
 * ne changent pas. Identifiants fictifs uniquement.
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const GATE = path.join(__dirname, '..', 'e2e', 'gate');
const load = (file) => import(pathToFileURL(path.join(GATE, 'lib', file)).href);

const ORIGIN = 'https://box.example.test';
const PLUGIN_AJAX = '/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php';

const post = (body, extra) => ({
  method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr', postData: body,
  headers: { 'content-type': 'application/x-www-form-urlencoded' }, ...extra,
});
const ctx = (declared) => ({
  origin: ORIGIN, loginAttempts: 0, declaredEquipments: {}, lastPreviewType: {},
  ...(declared === undefined ? {} : { declaredScenarioPublications: declared }),
});
const body = (publish, unpublish) => `action=saveScenarioPublication&ids_to_publish=${encodeURIComponent(publish)}&ids_to_unpublish=${encodeURIComponent(unpublish)}`;

test('front v3 lot 4a — saveScenarioPublication : simulée si déclarée', async () => {
  const { classifyRequest } = await load('policy.mjs');
  const declared = { 12: true, 15: true };
  for (const [publish, unpublish] of [['[12]', '[]'], ['[]', '[15]'], ['[12]', '[15]'], ['[12,15]', '[]']]) {
    const result = classifyRequest(post(body(publish, unpublish)), ctx(declared));
    assert.equal(result.verdict, 'simulate', `${publish} / ${unpublish}`);
    assert.equal(result.reason, 'publication-scenarios-declaree');
    assert.equal(result.params.ids_to_publish, publish);
  }
});

test('front v3 lot 4a — saveScenarioPublication : bloquée sinon', async () => {
  const { classifyRequest, DEFAULT_ORIGIN } = await load('policy.mjs');
  const declared = { 12: true, 15: true };
  const cases = {
    'ctx sans déclaration': [post(body('[12]', '[]')), ctx()],
    'déclaration vide': [post(body('[12]', '[]')), ctx({})],
    'identifiant non déclaré': [post(body('[12,99]', '[]')), ctx(declared)],
    'identifiant retiré non déclaré': [post(body('[]', '[99]')), ctx(declared)],
    'déclaration non vraie': [post(body('[12]', '[]')), ctx({ 12: 'oui' })],
    'listes vides': [post(body('[]', '[]')), ctx(declared)],
    'publié et retiré à la fois': [post(body('[12]', '[12]')), ctx(declared)],
    'doublon': [post(body('[12,12]', '[]')), ctx(declared)],
    'format libre': [post(body('12', '[]')), ctx(declared)],
    'espaces': [post(body('[12, 15]', '[]')), ctx(declared)],
    'zéro initial': [post(body('[012]', '[]')), ctx(declared)],
    'paramètre absent': [post('action=saveScenarioPublication&ids_to_publish=%5B12%5D'), ctx(declared)],
    'paramètre en plus': [post(`${body('[12]', '[]')}&excludedPlugins=x`), ctx(declared)],
    'action seule': [post('action=saveScenarioPublication'), ctx(declared)],
    'prototype': [post(body('[12]', '[]')), ctx(Object.create({ 12: true }))],
    'ctx absent': [post(body('[12]', '[]'), { url: `${DEFAULT_ORIGIN}${PLUGIN_AJAX}` }), undefined],
  };
  for (const [label, [request, context]] of Object.entries(cases)) {
    assert.equal(classifyRequest(request, context).verdict, 'block-fail', label);
  }
  const get = classifyRequest({ ...post(null), method: 'GET', url: `${ORIGIN}${PLUGIN_AJAX}?${body('[12]', '[]')}` }, ctx(declared));
  assert.equal(get.verdict, 'block-fail');
  const json = classifyRequest(post(body('[12]', '[]'), { headers: { 'content-type': 'application/json' } }), ctx(declared));
  assert.equal(json.verdict, 'block-fail');
  const other = classifyRequest(post(body('[12]', '[]'), { url: `${ORIGIN}/core/ajax/other.ajax.php` }), ctx(declared));
  assert.notEqual(other.verdict, 'simulate');
});

test('front v3 lot 4a — déclarations indépendantes, lectures inchangées', async () => {
  const { classifyRequest, ALLOWED_READS } = await load('policy.mjs');
  const scenarios = ctx({ 12: true });
  for (const action of ['scanTopology', 'executeHaAction', 'saveFilteringConfig', 'saveRoomExclusion']) {
    assert.equal(classifyRequest(post(`action=${action}`), scenarios).verdict, 'block-fail', action);
  }
  const filtering = { ...ctx(), declaredFilteringConfig: { excludedPlugins: ['virtual'], confidencePolicy: 'sure_probable' } };
  assert.equal(classifyRequest(post(body('[12]', '[]')), filtering).verdict, 'block-fail');
  const plugin = ALLOWED_READS.find((entry) => entry.pathname === PLUGIN_AJAX).actions;
  assert.deepEqual(plugin, ['getMqttConfig', 'getBridgeStatus', 'getMappingOverrides', 'getEquipmentStates', 'previewMappingOverride']);
  assert.equal(ALLOWED_READS.length, 3);
});

test('front v3 lot 4a — réponse simulée, branche explicite de l\'intercepteur, déclaration du lanceur', async () => {
  const { buildScenarioPublicationResponse } = await load('simulate.mjs');
  assert.deepEqual(buildScenarioPublicationResponse({ idsToPublish: '[15,12]', idsToUnpublish: '[]' }), {
    state: 'ok',
    result: {
      saved: true, ids_to_publish: [12, 15], ids_to_unpublish: [],
      rescan: { status: 'ok', operation_result: 'succes', operation_message: 'Synchronisation terminée.', scenario_availability_complete: true },
    },
  });
  assert.throws(() => buildScenarioPublicationResponse({ idsToPublish: '12', idsToUnpublish: '[]' }));

  const interceptor = fs.readFileSync(path.join(GATE, 'lib', 'interceptor.mjs'), 'utf8');
  assert.match(interceptor, /else if \(decision\.action === 'saveScenarioPublication'\) \{[\s\S]*?buildScenarioPublicationResponse\(\{ idsToPublish: params\.ids_to_publish, idsToUnpublish: params\.ids_to_unpublish \}\)/);
  const runner = fs.readFileSync(path.join(GATE, 'run-gate.mjs'), 'utf8');
  assert.match(runner, /declaredScenarioPublications: parcours\.declaredScenarioPublications \|\| \{\},/);
  assert.match(runner, /'saveScenarioPublication', \/\/ front v3 \(Lot 4a\)/);
});
