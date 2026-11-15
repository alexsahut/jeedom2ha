// ARTEFACT — story/select-mode, en VRAI Chromium (helpers/workview_browser.js) : sur une commande que rien ne couvre, le
// démon propose le rôle « Mode » ; « Corriger le type » montre « Mode (état) » (info) ou « Mode (commande) » (action), sans
// « Liste de choix » grisée ailleurs, un choix ne fait qu'un aperçu, et l'enregistrement envoie `haEntityType=select`.
// Ignoré sans Playwright / jQuery / PHP. Données fictives (CC-48).
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView, read } = require('./helpers/workview_browser');
const { DEMO, diag } = require('./helpers/front_v2_demo_trees');
const { ACTION_OK } = require('./helpers/write_scenarios');

const EQ = 102;
const UNCOVERED = () => diag('command_not_covered', {});

function tree() {
  const t = DEMO.lampePrise(true);
  t.jeedom_eq_id = EQ;
  t.commands.forEach((c) => { c.override_types_allowed = ['light', 'switch']; });
  t.commands.push(
    { jeedom_cmd_id: 2391, cmd_name: 'Programme', generic_type: null, coverable: false, covered: false, attendu_ha: null,
      effective_ha: null, override_applied: false, diagnostic: UNCOVERED(), published_in_ha: false,
      override_types_allowed: ['select'], mode_role: 'state', cmd_type: 'info', linked_state_cmd_id: null },
    { jeedom_cmd_id: 2392, cmd_name: 'Jour', generic_type: null, coverable: false, covered: false, attendu_ha: null,
      effective_ha: null, override_applied: false, diagnostic: UNCOVERED(), published_in_ha: false,
      override_types_allowed: ['select'], mode_role: 'command', cmd_type: 'action', linked_state_cmd_id: null },
  );
  return t;
}

function gate(seen) {
  return {
    isWrite: (action) => ['previewMappingOverride', 'saveMappingOverride', 'revertMappingOverride', 'executeHaAction'].includes(action),
    handleWrite: (action, request) => {
      seen.push({ action, body: request.postData });
      if (action === 'previewMappingOverride') {
        return { verdict: 'simulee', body: { state: 'ok', result: { status: 'ok', payload: {
          jeedom_eq_id: EQ, mapped: true, covered: true, auto: UNCOVERED(),
          overridden: diag('sure', { valid: true, publish: true, type: 'select', code: 'sure_mapping' }),
          entities_before: [], entities_after: [{ ha_entity_type: 'select', ha_unique_id: `jeedom2ha_eq_${EQ}_cmd_2391`,
            ha_name: 'Programme', ha_default_entity_id: `select.jeedom2ha_${EQ}_2391`, ha_controllable: true,
            ha_capabilities: ['mode', 'read'], will_publish: true, reason: 'sure' }],
          entity_id_changes: [{ from: null, to: `select.jeedom2ha_${EQ}_2391` }],
        } } } };
      }
      if (action === 'executeHaAction') return { verdict: 'simulee', body: ACTION_OK };
      return { verdict: 'simulee', body: { state: 'ok', result: { status: 'ok', payload: {} } } };
    },
  };
}

for (const theme of ['Light', 'Dark']) {
  test(`story/select-mode — « Mode (état) » sur une info non couverte, aperçu puis enregistrement (${theme})`, async (t) => {
    const seen = [];
    const options = { hash: `#j2ha-vue=piece:3;eq:${EQ}`, width: 1280, height: 1400, gate: gate(seen),
      treeFor: () => ({ state: 'ok', result: { status: 'ok', payload: tree() } }),
      extraCss: read('desktop/css/jeedom2ha_v2.css') };
    await withRealView(t, options, async (page, ctx) => {
      if (theme === 'Dark') await page.evaluate(() => document.body.setAttribute('data-theme', 'core2019_Dark'));
      const P = `.j2ha-eq-panel[data-eq-id="${EQ}"]`;
      await page.locator(`${P} .j2ha-cmd-table`).waitFor({ state: 'visible' });
      await page.locator(`${P} .j2ha-ignored-toggle`).click();
      await page.locator(`${P} .j2ha-mode-link[data-cmd-id="2391"]`).click();
      const box = page.locator('body > .j2ha-v3-type-modal[data-type-panel-for="2391"] .j2ha-v2-type-panel');
      await box.waitFor({ state: 'visible' });
      const labels = await box.locator('label').allInnerTexts();
      assert.ok(labels.some((l) => /Mode \(état\)/.test(l)), labels.join(' | '));
      assert.ok(!labels.some((l) => /Liste de choix/.test(l)), 'jamais « Liste de choix (select) »');
      await box.locator('input[data-type="select"]').check();
      await box.locator('.j2ha-v2-diff').waitFor({ state: 'visible' });
      await page.waitForFunction(() => !document.querySelector('.j2ha-v2-type-save').disabled);
      assert.deepEqual(seen.map((w) => w.action), ['previewMappingOverride'], 'aperçu seul, rien d’écrit');
      await box.locator('.j2ha-v2-type-save').click();
      await page.waitForFunction(() => true);
      await page.locator(`${P} .j2ha-v2-type-toast`).waitFor({ state: 'visible' });
      assert.equal(seen[1].action, 'saveMappingOverride');
      assert.equal(seen[1].body, `action=saveMappingOverride&eqId=${EQ}&cmdId=2391&haEntityType=select`);
      assert.deepEqual(ctx.errors, []);
    });
  });
}

test('story/select-mode — « Mode (commande) » sur une action non couverte', async (t) => {
  const options = { hash: `#j2ha-vue=piece:3;eq:${EQ}`, width: 1280, height: 1400, gate: gate([]),
    treeFor: () => ({ state: 'ok', result: { status: 'ok', payload: tree() } }), extraCss: read('desktop/css/jeedom2ha_v2.css') };
  await withRealView(t, options, async (page, ctx) => {
    const P = `.j2ha-eq-panel[data-eq-id="${EQ}"]`;
    await page.locator(`${P} .j2ha-cmd-table`).waitFor({ state: 'visible' });
    await page.locator(`${P} .j2ha-ignored-toggle`).click();
    assert.equal((await page.locator(`${P} .j2ha-mode-link[data-cmd-id="2392"]`).innerText()).trim(), 'Mode (commande)…');
    await page.locator(`${P} .j2ha-mode-link[data-cmd-id="2392"]`).click();
    const box = page.locator('body > .j2ha-v3-type-modal[data-type-panel-for="2392"] .j2ha-v2-type-panel');
    await box.waitFor({ state: 'visible' });
    const labels = await box.locator('label').allInnerTexts();
    assert.ok(labels.some((l) => /Mode \(commande\)/.test(l)), labels.join(' | '));
    assert.deepEqual(ctx.errors, []);
  });
});
