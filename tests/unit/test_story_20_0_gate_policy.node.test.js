/**
 * Story 20.0 (Tasks 2-3, incrément A) — Tests JS : politique d'interception (classifyRequest).
 *
 * Module testé : tests/e2e/gate/lib/policy.mjs (ESM pur, sans Playwright ni réseau).
 * Chargé via import() dynamique avec un chemin absolu construit depuis __dirname,
 * car ce fichier de test reste CommonJS (convention du runner `node --test`, Node 20).
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const POLICY_PATH = path.join(__dirname, '..', 'e2e', 'gate', 'lib', 'policy.mjs');

async function loadPolicy() {
  return import(pathToFileURL(POLICY_PATH).href);
}

const ORIGIN = 'https://domobox.famille-sahut.fr';
const PLUGIN_AJAX = '/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php';

function req(overrides) {
  return {
    method: 'GET',
    url: ORIGIN + '/index.php',
    resourceType: 'document',
    postData: null,
    ...overrides,
  };
}

function baseCtx(overrides) {
  return {
    loginAttempts: 0,
    declaredEquipments: {},
    lastPreviewType: {},
    ...overrides,
  };
}

test('story 20-0 — politique du gate (classifyRequest)', async (t) => {
  const { classifyRequest, ALLOWED_READS } = await loadPolicy();

  await t.test('5 effets de bord -> block-fail', () => {
    for (const action of ['scanTopology', 'executeHaAction', 'saveFilteringConfig', 'forceMqttManagerImport', 'testMqttConnection']) {
      const result = classifyRequest(
        req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr', postData: `action=${action}` }),
        baseCtx()
      );
      assert.equal(result.verdict, 'block-fail', `action=${action}`);
    }
  });

  await t.test("écriture d'override non déclarée -> block-fail", () => {
    const result = classifyRequest(
      req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr', postData: 'action=saveMappingOverride&eqId=1&cmdId=2&haEntityType=switch' }),
      baseCtx()
    );
    assert.equal(result.verdict, 'block-fail');
  });

  await t.test('écriture déclarée et conforme -> simulate', () => {
    const ctx = baseCtx({
      declaredEquipments: { '1': { commands: ['2'] } },
      lastPreviewType: { '1:2': 'switch' },
    });
    const result = classifyRequest(
      req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr', postData: 'action=saveMappingOverride&eqId=1&cmdId=2&haEntityType=switch' }),
      ctx
    );
    assert.equal(result.verdict, 'simulate');
  });

  await t.test('écriture déclarée, mauvais haEntityType -> block-fail', () => {
    const ctx = baseCtx({
      declaredEquipments: { '1': { commands: ['2'] } },
      lastPreviewType: { '1:2': 'switch' },
    });
    const result = classifyRequest(
      req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr', postData: 'action=saveMappingOverride&eqId=1&cmdId=2&haEntityType=light' }),
      ctx
    );
    assert.equal(result.verdict, 'block-fail');
  });

  await t.test('écriture, cmdId étranger -> block-fail', () => {
    const ctx = baseCtx({
      declaredEquipments: { '1': { commands: ['2'] } },
      lastPreviewType: { '1:2': 'switch' },
    });
    const result = classifyRequest(
      req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr', postData: 'action=saveMappingOverride&eqId=1&cmdId=99&haEntityType=switch' }),
      ctx
    );
    assert.equal(result.verdict, 'block-fail');
  });

  await t.test('écriture, eqId hors liste -> block-fail', () => {
    const ctx = baseCtx({
      declaredEquipments: { '1': { commands: ['2'] } },
      lastPreviewType: { '1:2': 'switch' },
    });
    const result = classifyRequest(
      req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr', postData: 'action=saveMappingOverride&eqId=9&cmdId=2&haEntityType=switch' }),
      ctx
    );
    assert.equal(result.verdict, 'block-fail');
  });

  await t.test('second login -> block-fail', () => {
    const result = classifyRequest(
      req({ method: 'POST', url: `${ORIGIN}/core/ajax/user.ajax.php`, resourceType: 'xhr', postData: 'action=login' }),
      baseCtx({ loginAttempts: 1 })
    );
    assert.equal(result.verdict, 'block-fail');
  });

  await t.test('premier login -> auth', () => {
    const result = classifyRequest(
      req({ method: 'POST', url: `${ORIGIN}/core/ajax/user.ajax.php`, resourceType: 'xhr', postData: 'action=login' }),
      baseCtx()
    );
    assert.equal(result.verdict, 'auth');
  });

  await t.test("action en double (corps) -> block-fail", () => {
    const result = classifyRequest(
      req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr', postData: 'action=getBridgeStatus&action=getDiagnostics' }),
      baseCtx()
    );
    assert.equal(result.verdict, 'block-fail');
  });

  await t.test("action dans l'URL et le corps -> block-fail", () => {
    const result = classifyRequest(
      req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}?action=getBridgeStatus`, resourceType: 'xhr', postData: 'action=getDiagnostics' }),
      baseCtx()
    );
    assert.equal(result.verdict, 'block-fail');
  });

  await t.test('GET statique avec action -> block', () => {
    const result = classifyRequest(
      req({ method: 'GET', url: `${ORIGIN}/core/php/getResource.php?action=x`, resourceType: 'script' }),
      baseCtx()
    );
    assert.equal(result.verdict, 'block');
  });

  await t.test('GET statique sous /ajax/ -> block', () => {
    const result = classifyRequest(
      req({ method: 'GET', url: `${ORIGIN}/core/ajax/some.ajax.php`, resourceType: 'script' }),
      baseCtx()
    );
    assert.equal(result.verdict, 'block');
  });

  await t.test('GET statique légitime -> static', () => {
    const result = classifyRequest(
      req({ method: 'GET', url: `${ORIGIN}/3rdparty/jquery/jquery.min.js`, resourceType: 'script' }),
      baseCtx()
    );
    assert.equal(result.verdict, 'static');
  });

  await t.test('autre origine -> block', () => {
    const result = classifyRequest(
      req({ method: 'GET', url: 'https://evil.example/3rdparty/jquery/jquery.min.js', resourceType: 'script' }),
      baseCtx()
    );
    assert.equal(result.verdict, 'block');
  });

  await t.test('8 lectures inscrites -> read', () => {
    for (const entry of ALLOWED_READS) {
      for (const action of entry.actions) {
        const result = classifyRequest(
          req({ method: 'POST', url: `${ORIGIN}${entry.pathname}`, resourceType: 'xhr', postData: `action=${action}` }),
          baseCtx()
        );
        assert.equal(result.verdict, 'read', `${entry.pathname} action=${action}`);
      }
    }
  });

  await t.test('exportDiagnostic -> block', () => {
    const result = classifyRequest(
      req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr', postData: 'action=exportDiagnostic' }),
      baseCtx()
    );
    assert.equal(result.verdict, 'block');
  });
});
