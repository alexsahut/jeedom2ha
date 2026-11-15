// ARTEFACT — fix/switch-appariement-etat, en VRAI Chromium (helpers/workview_browser.js), thèmes clair et sombre : un
// équipement à plusieurs ordres On/Off non reliés à l'état affiche une bande d'une ligne « Ordres On/Off en double », la
// fiche du lexique en info-bulle, l'action « Ouvrir l’équipement dans Jeedom », et rien ne s'écrit. Ignoré sans
// Playwright / jQuery / PHP. Données fictives (CC-48).
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView, read } = require('./helpers/workview_browser');
const { DEMO } = require('./helpers/front_v2_demo_trees');

const EQ = 231;
const SCENE = {
  objects: [
    { id: 1, name: 'Maison', father_id: null, display: {} },
    { id: 9, name: 'Buanderie', father_id: 1, display: {} },
  ],
  eqlogics: { 9: [{ id: EQ, name: 'Ballon eau chaude', type: 'virtual' }] },
  plugin_names: { virtual: 'Virtuel' },
  doc: 'https://doc.example.test/plugin',
};

function pairingTree() {
  const text = JSON.stringify(DEMO.lampePrise(true)).split('name_heuristic_rejection').join('switch_pairing_ambiguous');
  const tree = JSON.parse(text);
  tree.eq_name = 'Ballon eau chaude';
  tree.hints = [];
  for (const entity of tree.entities) {
    entity.ha_name = 'Ballon eau chaude';
    entity.reason_details = { pairing_candidates: { ENERGY_ON: [2312, 2314], ENERGY_OFF: [2313, 2315] } };
  }
  return tree;
}

const TREE = pairingTree();
const CORE_LIGHT = ':root { --bg-color: 245, 245, 245; --txt-color: #333; }';

for (const theme of ['Light', 'Dark']) {
  test(`fix/switch-appariement-etat — bande « Ordres On/Off en double », sans écriture (${theme})`, async (t) => {
    const options = {
      scene: SCENE, equipments: { [EQ]: TREE },
      treeFor: () => ({ state: 'ok', result: { status: 'ok', payload: TREE } }),
      hash: `#j2ha-vue=piece:9;eq:${EQ}`, width: 1280, height: 900,
      extraCss: read('desktop/css/jeedom2ha_v2.css') + (theme === 'Light' ? CORE_LIGHT : ''),
    };
    await withRealView(t, options, async (page, ctx) => {
      await page.evaluate((th) => document.body.setAttribute('data-theme', 'core2019_' + th), theme);
      const panel = `.j2ha-eq-panel[data-eq-id="${EQ}"]`;
      await page.locator(`${panel} .j2ha-cmd-table`).waitFor();
      const band = page.locator(`${panel} .j2ha-eq-notices .j2ha-eq-band`);
      assert.equal(await band.count(), 1);
      assert.equal((await band.locator('.j2ha-eq-band-what').innerText()).trim(), 'Ordres On/Off en double');
      const tip = await band.locator('.j2ha-eq-band-info').getAttribute('data-j2ha-tip');
      assert.match(tip, /plusieurs ordres On et Off/);
      assert.match(tip, /ne devine pas/);
      const text = await band.innerText();
      assert.doesNotMatch(text, /Publier en interrupteur/, 'forcer ne lève pas ce blocage : pas de bouton « Publier quand même »');
      const h = await band.evaluate((el) => el.getBoundingClientRect().height);
      assert.ok(h <= 56, `bande sur une ligne (${h} px)`);
      assert.equal((await page.locator(`${panel} .j2ha-eq-ha-empty`).innerText()).trim(), 'Rien');
      assert.ok(!ctx.journal.some((e) => ['saveMappingOverride', 'savePublicationOverride', 'executeHaAction'].includes(e.action)), 'aucune écriture');
      assert.deepEqual(ctx.errors, []);
    });
  });
}
