// GARDE du harnais Chromium (workview_browser.withRealView) : l'extrait du CSS du cœur Jeedom 4.6.1
// (helpers/core_css_reel.js) est chargé PAR DÉFAUT, AVANT le CSS du plugin, comme sur la box. Sans lui, quatre défauts
// visibles seulement sur la box sont passés à travers les tests (icône de carte à 38 px, carte figée 130 px en
// overflow:hidden, fond de bouton sur `.btn-link`, bouton `confirm` de bootbox forcé en vert).
// Données fictives (CC-48). Ignoré sans Playwright / jQuery / PHP.
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView, CORE_CSS } = require('./helpers/workview_browser');

const ICON = '#j2ha_roomCards .objectDisplayCard i.j2ha-room-icon';
const iconPx = (page) => page.evaluate((sel) => parseFloat(getComputedStyle(document.querySelector(sel)).fontSize), ICON);

test('harnais — par défaut, le CSS du cœur est chargé AVANT celui du plugin', async (t) => {
  await withRealView(t, {}, async (page) => {
    const css = await page.evaluate(() => document.querySelector('head style').textContent);
    const core = css.indexOf(CORE_CSS);
    assert.equal(core, 0, 'l\'extrait du cœur ouvre la feuille');
    assert.ok(css.indexOf('.j2ha-', CORE_CSS.length) > 0, 'le CSS du plugin suit');
    // Règle connue du cœur (`.objectDisplayCard i { font-size: 38px !important }`) : elle l'emporte sur les 22 px du plugin.
    assert.equal(await iconPx(page), 38);
  });
});

test('harnais — une icône de carte mesure 38 px avec le seul CSS du cœur (sans le CSS du plugin)', async (t) => {
  await withRealView(t, { css: '', coreCss: true }, async (page) => {
    assert.equal(await iconPx(page), 38);
    const h = await page.evaluate(() => getComputedStyle(document.querySelector('#j2ha_roomCards .objectDisplayCard')).height);
    assert.equal(h, '130px', 'carte figée à 130 px par le cœur');
  });
});

test('harnais — `coreCss: false` retire le cœur ; un `css` fourni sans `coreCss` ne le charge pas', async (t) => {
  await withRealView(t, { coreCss: false }, async (page) => {
    assert.equal(await iconPx(page), 22, 'taille du plugin seule');
  });
  await withRealView(t, { css: '' }, async (page) => {
    assert.notEqual(await iconPx(page), 38);
  });
});

test('harnais — bootbox factice fidèle : `.modal-footer`, `bootbox-accept` / `bootbox-cancel` ; la confirmation destructive n\'est pas verte', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    await page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="3"]').click();
    await page.locator('.j2ha-wv .j2ha-menu-toggle').click();
    await page.locator('.j2ha-wv .j2ha-room-recreate').click();
    await page.locator('.bootbox .modal-footer .btn-danger').waitFor({ state: 'visible' });
    const r = await page.evaluate(() => {
      const success = getComputedStyle(document.documentElement).getPropertyValue('--al-success-color').trim();
      const probe = document.createElement('span');
      probe.style.backgroundColor = success;
      document.body.appendChild(probe);
      const green = getComputedStyle(probe).backgroundColor;
      probe.remove();
      const btn = (k) => document.querySelector(`.bootbox .modal-footer [data-bb-handler="${k}"]`);
      return { green, confirmClass: btn('confirm').className, confirmBg: getComputedStyle(btn('confirm')).backgroundColor, cancelClass: btn('cancel').className };
    });
    assert.match(r.cancelClass, /\bbootbox-cancel\b/);
    assert.match(r.confirmClass, /\bbtn-danger\b/);
    assert.doesNotMatch(r.confirmClass, /\bbootbox-accept\b/, 'le produit retire bootbox-accept du bouton btn-danger');
    assert.notEqual(r.confirmBg, r.green, 'le vert `!important` du cœur ne s\'applique pas à la confirmation destructive');
    await page.locator('.bootbox .modal-footer [data-bb-handler="cancel"]').click();
    assert.equal(ctx.journal.filter((e) => e.action === 'executeHaAction').length, 0, 'annulation sans écriture');
    assert.deepEqual(ctx.errors, []);
  });
});

// Défaut révélé par le CSS du cœur, corrigé dans desktop/css/jeedom2ha.css : la règle du cœur
// `div[class*="ListContainer"]:not(.batteryListContainer):not(.alertListContainer) div { border: none !important; }` efface,
// dans desktop/css/jeedom2ha.css, le filet de couleur de pièce (`.j2ha-room-groups .j2ha-room-card { border-top: 3px … }`)
// et le liseré orange des pièces bloquées (`.j2ha-room-card.j2ha-room-blocked { border-left: 4px … }`).
test('filet de couleur et liseré « bloqué » des cartes de pièce visibles avec le CSS du cœur', async (t) => {
  await withRealView(t, {}, async (page) => {
    const r = await page.evaluate(() => {
      const card = document.querySelector('.j2ha-room-groups .j2ha-room-card');
      const blocked = document.querySelector('.j2ha-room-groups .j2ha-room-card.j2ha-room-blocked');
      return { top: getComputedStyle(card).borderTopWidth, left: blocked ? getComputedStyle(blocked).borderLeftWidth : null };
    });
    assert.equal(r.top, '3px', 'filet de couleur de pièce');
    assert.equal(r.left, '4px', 'liseré orange de la pièce bloquée');
  });
});
