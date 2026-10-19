// ARTEFACT — Story 25.6 (AC3, AC4, AC8) : la portée dans un VRAI Chromium (vrai CSS, vrais clics). Fixture de 40 pièces
// fictives, carte de la 35ᵉ : la pièce choisie est dans la zone visible de l'arbre ; élargir la garde visible ; le bouton
// d'élargissement est une cible tactile ≥ 44 × 44 px en disposition étroite. Ignoré si Playwright, jQuery ou PHP manquent.
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView } = require('./helpers/workview_browser');
const { makeScene } = require('./helpers/big_scene');

const THRESHOLD = require('../../desktop/js/jeedom2ha_workview.js').LAYOUT_SPLIT_MIN_WIDTH;
const inside = (page, selector) => page.evaluate((sel) => {
  const row = document.querySelector(sel).getBoundingClientRect();
  const box = document.querySelector('.j2ha-wv-tree').getBoundingClientRect();
  return row.top >= box.top - 1 && row.bottom <= box.bottom + 1 && row.height > 0;
}, selector);

test('25.6 réel — 40 pièces, carte de la 35ᵉ : l’arbre ne contient que cette pièce, dans la zone visible ; élargir la garde visible', async (t) => {
  const big = makeScene({ rooms: 40, equipments: 160, seed: 5 });
  await withRealView(t, { width: 1280, height: 800, scene: big.scene, equipments: big.equipments }, async (page, ctx) => {
    const id = 10 + 34;
    await page.locator(`#j2ha_roomCards .j2ha-room-card[data-object_id="${id}"]`).click();
    await page.locator('#j2ha_workView').waitFor({ state: 'visible' });
    assert.equal(await page.locator('#j2ha_workView').getAttribute('data-j2ha-scope'), 'piece');
    assert.equal(await page.locator('.j2ha-wv-tree .j2ha-wv-room').count(), 1);
    assert.equal(await inside(page, `.j2ha-wv-room[data-object_id="${id}"]`), true, 'la pièce est visible dans l’arbre');
    assert.equal(await page.evaluate(() => document.activeElement.classList.contains('j2ha-wv-title')), true, 'focus sur le titre du détail');
    assert.equal(await page.locator('.j2ha-wv-title').count(), 1, 'détail de pièce affiché');
    assert.equal(await page.evaluate(() => location.hash), `#j2ha-vue=piece:${id};seule:1`);

    await page.locator('.j2ha-wv-widen').click();
    assert.equal(await page.locator('.j2ha-wv-tree .j2ha-wv-room').count(), 40);
    assert.equal(await page.locator('.j2ha-wv-widen').count(), 0);
    assert.equal(await inside(page, `.j2ha-wv-room[data-object_id="${id}"]`), true, 'la sélection est ramenée dans la zone visible');
    assert.equal(await page.evaluate(() => document.activeElement.getAttribute('data-object_id')), String(id), 'focus sur la ligne sélectionnée');
    await page.goBack();
    assert.equal(await page.locator('#j2ha_workView').isVisible(), false, '« Précédent » après élargissement : page principale');
    assert.deepEqual(ctx.errors, []);
  });
});

test('25.6 réel — « Précédent » depuis la pièce seule, sans rechargement ; zéro requête de navigation', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    const before = ctx.journal.length;
    await page.evaluate(() => { window.__marker = 1; });
    await page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="4"]').click();
    await page.locator('.j2ha-wv-widen').click();
    await page.goBack();
    await page.goForward();
    assert.equal(await page.evaluate(() => window.__marker), 1, 'la page n’a pas été rechargée');
    assert.equal(ctx.journal.length, before, 'aucune requête');
    assert.deepEqual(ctx.errors, []);
  });
});

test('25.6 réel — disposition étroite : le bouton « Toutes les pièces » est une cible ≥ 44 × 44 px dans le tiroir ; il élargit sans le refermer', async (t) => {
  await withRealView(t, { width: THRESHOLD - 200, height: 900 }, async (page, ctx) => {
    await page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="4"]').click();
    await page.locator('.j2ha-wv-drawer-toggle').click();
    const box = await page.locator('.j2ha-wv-widen').boundingBox();
    assert.ok(box.width >= 44 && box.height >= 44, `cible ${box.width}×${box.height}`);
    await page.locator('.j2ha-wv-widen').click();
    assert.equal(await page.locator('.j2ha-wv-drawer-toggle').getAttribute('aria-expanded'), 'true');
    assert.ok((await page.locator('.j2ha-wv-tree .j2ha-wv-room').count()) > 1);
    assert.deepEqual(ctx.errors, []);
  });
});
