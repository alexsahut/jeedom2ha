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
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
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

  await t.test('publication déclarée : exclusion puis retrait simulables, Appliquer reste bloqué', () => {
    const ctx = baseCtx({ declaredPublicationOverrides: { '287': { commands: [] } } });
    const save = classifyRequest(req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr',
      postData: 'action=savePublicationOverride&eqId=287&publicationPolicy=exclude' }), ctx);
    const revert = classifyRequest(req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr',
      postData: 'action=revertPublicationOverride&eqId=287' }), ctx);
    const apply = classifyRequest(req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr',
      postData: 'action=executeHaAction&intention=publier' }), ctx);
    assert.equal(save.verdict, 'simulate');
    assert.equal(revert.verdict, 'simulate');
    assert.equal(apply.verdict, 'block-fail');
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

  await t.test('lectures inscrites (4 du plugin, 2 du cœur) -> read', () => {
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

  await t.test('20.3 — getDiagnostics et getPublishedScopeForConsole ne sont plus des lectures autorisées -> block', () => {
    for (const action of ['getDiagnostics', 'getPublishedScopeForConsole']) {
      const result = classifyRequest(
        req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr', postData: `action=${action}` }),
        baseCtx()
      );
      assert.equal(result.verdict, 'block', `action=${action}`);
      assert.equal(ALLOWED_READS.some((entry) => entry.actions.includes(action)), false, action);
    }
  });

  await t.test('exportDiagnostic -> block', () => {
    const result = classifyRequest(
      req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr', postData: 'action=exportDiagnostic' }),
      baseCtx()
    );
    assert.equal(result.verdict, 'block');
  });

  await t.test('GET scanTopology -> block-fail', () => {
    const result = classifyRequest(
      req({ method: 'GET', url: `${ORIGIN}${PLUGIN_AJAX}?action=scanTopology`, resourceType: 'xhr' }),
      baseCtx()
    );
    assert.equal(result.verdict, 'block-fail');
  });

  await t.test('POST scanTopology déclaré -> simulate', () => {
    const result = classifyRequest(
      req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr', postData: 'action=scanTopology' }),
      baseCtx({ declaredRescan: true })
    );
    assert.equal(result.verdict, 'simulate');
    assert.equal(result.reason, 'rescan-declare');
  });

  await t.test('POST scanTopology non déclaré -> block-fail', () => {
    const result = classifyRequest(
      req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr', postData: 'action=scanTopology' }), baseCtx()
    );
    assert.equal(result.verdict, 'block-fail');
  });

  await t.test('GET saveMappingOverride -> block-fail', () => {
    const ctx = baseCtx({
      declaredEquipments: { '1': { commands: ['2'] } },
      lastPreviewType: { '1:2': 'switch' },
    });
    const result = classifyRequest(
      req({ method: 'GET', url: `${ORIGIN}${PLUGIN_AJAX}?action=saveMappingOverride&eqId=1&cmdId=2&haEntityType=switch`, resourceType: 'xhr' }),
      ctx
    );
    assert.equal(result.verdict, 'block-fail');
  });

  await t.test("eqId dans l'URL d'une écriture -> block-fail", () => {
    const ctx = baseCtx({
      declaredEquipments: { '1': { commands: ['2'] } },
      lastPreviewType: { '1:2': 'switch' },
    });
    const result = classifyRequest(
      req({
        method: 'POST',
        url: `${ORIGIN}${PLUGIN_AJAX}?eqId=1`,
        resourceType: 'xhr',
        postData: 'action=saveMappingOverride&eqId=1&cmdId=2&haEntityType=switch',
      }),
      ctx
    );
    assert.equal(result.verdict, 'block-fail');
  });

  await t.test('cmdId en double dans le corps -> block-fail', () => {
    const ctx = baseCtx({
      declaredEquipments: { '1': { commands: ['2'] } },
      lastPreviewType: { '1:2': 'switch' },
    });
    const result = classifyRequest(
      req({
        method: 'POST',
        url: `${ORIGIN}${PLUGIN_AJAX}`,
        resourceType: 'xhr',
        postData: 'action=saveMappingOverride&eqId=1&cmdId=2&cmdId=2&haEntityType=switch',
      }),
      ctx
    );
    assert.equal(result.verdict, 'block-fail');
  });

  await t.test('revertMappingOverride avec cmdId=abc -> block-fail', () => {
    const ctx = baseCtx({
      declaredEquipments: { '1': { commands: ['2'] } },
    });
    const result = classifyRequest(
      req({
        method: 'POST',
        url: `${ORIGIN}${PLUGIN_AJAX}`,
        resourceType: 'xhr',
        postData: 'action=revertMappingOverride&eqId=1&cmdId=abc',
      }),
      ctx
    );
    assert.equal(result.verdict, 'block-fail');
  });

  await t.test('eqId = constructor puis __proto__ -> block-fail, sans exception', () => {
    const ctx = baseCtx();
    for (const eqId of ['constructor', '__proto__']) {
      assert.doesNotThrow(() => {
        const result = classifyRequest(
          req({
            method: 'POST',
            url: `${ORIGIN}${PLUGIN_AJAX}`,
            resourceType: 'xhr',
            postData: `action=revertMappingOverride&eqId=${eqId}`,
          }),
          ctx
        );
        assert.equal(result.verdict, 'block-fail', `eqId=${eqId}`);
      });
    }
  });

  await t.test('ctx absent -> block-fail pour une écriture, sans exception', () => {
    assert.doesNotThrow(() => {
      const result = classifyRequest(
        req({
          method: 'POST',
          url: `${ORIGIN}${PLUGIN_AJAX}`,
          resourceType: 'xhr',
          postData: 'action=saveMappingOverride&eqId=1&cmdId=2&haEntityType=switch',
        }),
        undefined
      );
      assert.equal(result.verdict, 'block-fail');
    });
  });

  await t.test('connexion avec ctx absent -> block-fail, sans exception', () => {
    assert.doesNotThrow(() => {
      const result = classifyRequest(
        req({ method: 'POST', url: `${ORIGIN}/core/ajax/user.ajax.php`, resourceType: 'xhr', postData: 'action=login' }),
        undefined
      );
      assert.equal(result.verdict, 'block-fail');
    });
  });

  await t.test('URL illisible -> block-fail', () => {
    assert.doesNotThrow(() => {
      const result = classifyRequest(
        req({ method: 'GET', url: 'not a valid url', resourceType: 'document' }),
        baseCtx()
      );
      assert.equal(result.verdict, 'block-fail');
    });
  });

  await t.test('ctx.origin injectable : lecture sur cette origine -> read, sur la box -> block', () => {
    const ctx = baseCtx({ origin: 'http://127.0.0.1:8123' });

    const onInjectedOrigin = classifyRequest(
      req({ method: 'POST', url: `http://127.0.0.1:8123${PLUGIN_AJAX}`, resourceType: 'xhr', postData: 'action=getBridgeStatus' }),
      ctx
    );
    assert.equal(onInjectedOrigin.verdict, 'read');

    const onBoxOrigin = classifyRequest(
      req({ method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr', postData: 'action=getBridgeStatus' }),
      ctx
    );
    assert.equal(onBoxOrigin.verdict, 'block');
  });

  await t.test('noms de paramètres PHP ambigus ou invalides -> block-fail', () => {
    const variants = [
      `action=listByType&type=jeedom2ha&+action=remove&id=579`,
      `action=listByType&type=jeedom2ha&%20action=remove&id=579`,
      'action=getBridgeStatus&action%00=scanTopology',
      'action=getBridgeStatus&action%5B%5D=scanTopology',
    ];
    for (const postData of variants) {
      const result = classifyRequest(
        req({ method: 'POST', url: `${ORIGIN}/core/ajax/eqLogic.ajax.php`, resourceType: 'xhr', postData }),
        baseCtx(),
      );
      assert.equal(result.verdict, 'block-fail', postData);
    }
  });

  await t.test('corps non form, duplicat URL/corps et doublon de lecture -> block-fail', () => {
    const cases = [
      req({
        method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr',
        postData: 'field=abc%26action%3DscanTopology',
        headers: { 'content-type': 'multipart/form-data; boundary=gate' },
      }),
      req({
        method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr',
        postData: '{"action":"getBridgeStatus"}', headers: { 'content-type': 'application/json' },
      }),
      req({
        method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}?action=getBridgeStatus`, resourceType: 'xhr',
        postData: 'action=getBridgeStatus',
      }),
      req({
        method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}?eqId=1`, resourceType: 'xhr',
        postData: 'action=previewMappingOverride&eqId=1&cmdId=2&haEntityType=switch',
      }),
    ];
    for (const input of cases) assert.equal(classifyRequest(input, baseCtx()).verdict, 'block-fail');
  });

  await t.test('écritures camouflées par des clés PHP ambiguës -> block-fail', () => {
    const result = classifyRequest(
      req({
        method: 'POST', url: `${ORIGIN}${PLUGIN_AJAX}`, resourceType: 'xhr',
        postData: 'action=previewMappingOverride&eqId=1&cmdId=2&haEntityType=switch&+action=saveMappingOverride',
      }),
      baseCtx(),
    );
    assert.equal(result.verdict, 'block-fail');
  });

  await t.test('chemins non canoniques et PHP chargé comme ressource -> block-fail ou block', () => {
    assert.equal(classifyRequest(req({
      method: 'GET', url: `${ORIGIN}/core//api/jeeApi.php`, resourceType: 'image',
    }), baseCtx()).verdict, 'block-fail');
    assert.equal(classifyRequest(req({
      method: 'GET', url: `${ORIGIN}/core%2Fapi/jeeApi.php`, resourceType: 'image',
    }), baseCtx()).verdict, 'block-fail');
    assert.equal(classifyRequest(req({
      method: 'GET', url: `${ORIGIN}/plugins/x/y.php`, resourceType: 'script',
    }), baseCtx()).verdict, 'block');
  });

  await t.test('getResource n’autorise que file, md5 et lang strictement valides', () => {
    const allowed = classifyRequest(req({
      method: 'GET', url: `${ORIGIN}/core/php/getResource.php?file=core%2Fjs%2Fapp.js&md5=0123456789abcdef0123456789abcdef&lang=fr_FR`, resourceType: 'script',
    }), baseCtx());
    assert.equal(allowed.verdict, 'static');
    for (const suffix of ['&extra=x', '&file=..%2Fsecret.js', '&lang=..%2Fx', '&md5=pas-un-md5']) {
      const result = classifyRequest(req({
        method: 'GET', url: `${ORIGIN}/core/php/getResource.php?file=core%2Fjs%2Fapp.js&md5=0123456789abcdef0123456789abcdef${suffix}`, resourceType: 'script',
      }), baseCtx());
      assert.ok(['block', 'block-fail'].includes(result.verdict));
    }
  });

  await t.test('page plugin : triplet strict, aucun paramètre supplémentaire', () => {
    for (const query of ['v=d&m=jeedom2ha&p=administration', 'v=d&m=jeedom2ha&p=jeedom2ha&modal=x', 'v=d&m=jeedom2ha&p=jeedom2ha&configure=1']) {
      const result = classifyRequest(req({ method: 'GET', url: `${ORIGIN}/index.php?${query}`, resourceType: 'document' }), baseCtx());
      assert.equal(result.verdict, 'block');
    }
  });
});
