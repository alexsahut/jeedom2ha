// GARDE du harnais Chromium (workview_browser.withRealView) : l'extrait du CSS du cœur Jeedom 4.6.1
// (helpers/core_css_reel.js) est chargé PAR DÉFAUT, AVANT le CSS du plugin, comme sur la box. Sans lui, quatre défauts
// visibles seulement sur la box sont passés à travers les tests (icône de carte à 38 px, carte figée 130 px en
// overflow:hidden, fond de bouton sur `.btn-link`, bouton `confirm` de bootbox forcé en vert).
// Données fictives (CC-48). Ignoré sans Playwright / jQuery / PHP.
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView, CORE_CSS } = require('./helpers/workview_browser');

// Garde levée (front v3, Lot 1) : la carte de pièce ne porte plus `objectDisplayCard` (cible §1 : le cœur la figerait à
// 130 px, overflow:hidden, icône à 38 px). La règle témoin du cœur devient `.btn { height: 32px }` (bouton « Relire Jeedom »).
const RESCAN = '#bt_rescanTopology';
const rescanPx = (page) => page.evaluate((sel) => parseFloat(getComputedStyle(document.querySelector(sel)).height), RESCAN);

test('harnais — par défaut, le CSS du cœur est chargé AVANT celui du plugin', async (t) => {
  await withRealView(t, {}, async (page) => {
    const css = await page.evaluate(() => document.querySelector('head style').textContent);
    const core = css.indexOf(CORE_CSS);
    assert.equal(core, 0, 'l\'extrait du cœur ouvre la feuille');
    assert.ok(css.indexOf('.j2ha-', CORE_CSS.length) > 0, 'le CSS du plugin suit');
    // Front v3 (Lot 1) : les deux feuilles du plugin, dans l'ordre de la page.
    assert.ok(css.indexOf('.j2ha-v2-') > css.indexOf('.j2ha-health-bar'), 'jeedom2ha.css puis jeedom2ha_v2.css');
    assert.equal(await rescanPx(page), 32, 'règle `.btn` du cœur');
  });
});

test('harnais — la tuile de pièce échappe aux règles *DisplayCard du cœur (seul le CSS du cœur chargé)', async (t) => {
  await withRealView(t, { css: '', coreCss: true }, async (page) => {
    assert.equal(await rescanPx(page), 32);
    const r = await page.evaluate(() => {
      const card = document.querySelector('#j2ha_roomCards .j2ha-room-card');
      return { cls: card.className, h: getComputedStyle(card).height, icon: getComputedStyle(card.querySelector('.j2ha-room-icon')).fontSize };
    });
    assert.doesNotMatch(r.cls, /DisplayCard/);
    assert.notEqual(r.h, '130px', 'pas figée à 130 px par le cœur');
    assert.notEqual(r.icon, '38px', 'icône non agrandie par le cœur');
  });
});

test('harnais — `coreCss: false` retire le cœur ; un `css` fourni sans `coreCss` ne le charge pas', async (t) => {
  await withRealView(t, { coreCss: false }, async (page) => {
    assert.notEqual(await rescanPx(page), 32, 'sans la règle du cœur');
  });
  await withRealView(t, { css: '' }, async (page) => {
    assert.notEqual(await rescanPx(page), 32);
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

// Front v3 (Lot 1, garde levée) : la tuile 220 × 72 remplace la carte du cœur. Avec le CSS du cœur chargé, elle garde sa taille,
// son icône de 20 px et son liseré de 4 px collé au bas ; une pièce bloquée le dit par sa marque ⚠ (plus de liseré gauche).
test('tuile de pièce 220 × 72 avec le CSS du cœur : icône 20 px, liseré de 4 px au bas, marque ⚠ si bloquée', async (t) => {
  await withRealView(t, {}, async (page) => {
    const r = await page.evaluate(() => {
      const card = document.querySelector('.j2ha-room-groups .j2ha-room-card');
      const blocked = document.querySelector('.j2ha-room-groups .j2ha-room-card.j2ha-room-blocked');
      const box = card.getBoundingClientRect();
      const stripe = card.querySelector('.j2ha-gauge-card').getBoundingClientRect();
      return {
        w: box.width, h: box.height, icon: getComputedStyle(card.querySelector('.j2ha-room-icon')).fontSize,
        stripeH: stripe.height, stripeBottom: Math.round(box.bottom - stripe.bottom),
        warn: blocked ? blocked.querySelectorAll('.j2ha-mark-blocked .fa-exclamation-triangle').length : null,
      };
    });
    assert.equal(r.w, 220);
    assert.equal(r.h, 72);
    assert.equal(r.icon, '20px');
    assert.equal(r.stripeH, 4);
    assert.ok(r.stripeBottom <= 1, 'liseré collé au bas de la tuile');
    assert.equal(r.warn, 1, 'marque ⚠ de la pièce bloquée');
  });
});
