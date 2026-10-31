// ARTEFACT — Story 25.8 (AC6, AC8, AC11) en VRAI Chromium : sur la page livrée (vrai CSS, vrai jQuery, vrais scripts), le menu « ⋯ »
// d'une carte de pièce ne l'ouvre JAMAIS — clic, Entrée, Espace, flèches, Échap — ; la cible du bouton fait au moins 44 × 44 px ;
// l'entrée ouvre la confirmation chiffrée (bouton rouge) sans aucune requête d'écriture avant le clic de confirmation ; la carte de
// « Sans pièce » n'a pas de menu. Réseau et bootbox factices, données fictives (CC-48). Ignoré sans Playwright / jQuery / PHP.
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView } = require('./helpers/workview_browser');

const CARD = (id) => `#j2ha_roomCards .j2ha-room-card[data-object_id="${id}"]`;
const viewVisible = (page) => page.evaluate(() => { const v = document.querySelector('#j2ha_workView'); return !!v && getComputedStyle(v).display !== 'none'; });
const writes = (ctx) => ctx.journal.filter((e) => ['saveRoomExclusion', 'scanTopology', 'executeHaAction'].includes(e.action));

test('25.8 réel — le menu de la carte n\'ouvre jamais la pièce (souris, Entrée, Espace, flèches, Échap)', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    const toggle = page.locator(`${CARD(4)} .j2ha-menu-toggle`);
    const hash = await page.evaluate(() => window.location.hash);
    await toggle.click();
    assert.equal(await viewVisible(page), false, 'clic souris');
    assert.equal(await page.locator(`${CARD(4)} .j2ha-room-menu`).evaluate((el) => el.classList.contains('j2ha-menu-open')), true, 'menu ouvert');
    for (const key of ['Escape', 'Enter', 'ArrowDown', 'ArrowUp', 'Escape', 'Space', 'Escape']) {
      await page.keyboard.press(key);
      assert.equal(await viewVisible(page), false, 'touche ' + key);
    }
    assert.equal(await page.evaluate(() => window.location.hash), hash, 'fragment d\'URL inchangé');
    assert.equal(ctx.journal.filter((e) => e.action === 'getMappingOverrides').length, 0, 'aucune lecture d\'arbre');
    assert.deepEqual(writes(ctx), []);
    assert.deepEqual(ctx.errors, []);
  });
});

test('25.8 réel — la carte, elle, s\'ouvre toujours au clic et au clavier (contrôle : le menu ne la neutralise pas)', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    await page.locator(CARD(4)).click({ position: { x: 20, y: 60 } });
    assert.equal(await viewVisible(page), true);
    assert.deepEqual(ctx.errors, []);
  });
  await withRealView(t, {}, async (page) => {
    await page.locator(CARD(4)).focus();
    await page.keyboard.press('Enter');
    assert.equal(await viewVisible(page), true);
  });
});

test('25.8 réel — cible du bouton « ⋯ » ≥ 44 × 44 px, menu visible dans la page, « Sans pièce » sans menu', async (t) => {
  await withRealView(t, {}, async (page) => {
    const box = await page.locator(`${CARD(4)} .j2ha-menu-toggle`).boundingBox();
    assert.ok(box.width >= 44 && box.height >= 44, `${box.width} × ${box.height}`);
    await page.locator(`${CARD(4)} .j2ha-menu-toggle`).click();
    const menu = await page.locator(`${CARD(4)} .j2ha-menu`).boundingBox();
    assert.ok(menu && menu.width >= 150, 'menu rendu');
    assert.equal(await page.locator(`${CARD(0)} .j2ha-room-menu`).count(), 0);
    assert.equal(await page.locator(`${CARD(0)} .j2ha-room-exclude`).count(), 0);
    // Les cartes de pièce portent chacune leur menu, et un seul menu est ouvert à la fois.
    await page.locator(`${CARD(3)} .j2ha-menu-toggle`).click();
    assert.equal(await page.locator('#j2ha_roomCards .j2ha-menu-open').count(), 1);
  });
});

test('25.8 réel — l\'entrée ouvre la confirmation chiffrée (bouton rouge) sans écriture avant le clic de confirmation', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    await page.waitForFunction(() => !document.querySelector('#j2ha_roomCards .j2ha-room-card[data-object_id="4"] .j2ha-room-exclude').disabled);
    await page.locator(`${CARD(4)} .j2ha-menu-toggle`).click();
    await page.locator(`${CARD(4)} .j2ha-room-exclude`).click();
    assert.equal(await viewVisible(page), false, 'la pièce reste fermée');
    const dialog = page.locator('.bootbox').first();
    await dialog.waitFor({ state: 'visible' });
    const body = (await dialog.innerText()).replace(/\s+/g, ' ');
    assert.match(body, /^Exclure la pièce « .* » de Home Assistant \?/);
    assert.match(body, /(\d+ entités? (seront|sera) retirées?|Aucune entité n'est publiée dans cette pièce)/);
    assert.equal(await dialog.locator('.btn-danger').count(), 1, 'bouton de confirmation rouge');
    assert.deepEqual(writes(ctx), []);
    // Les entrées des autres pièces sont réservées pendant la confirmation (une seule opération à la fois).
    assert.equal(await page.locator(`${CARD(3)} .j2ha-room-exclude`).isDisabled(), true);
    await dialog.locator('.btn-default').filter({ hasText: 'Annuler' }).click();
    assert.deepEqual(writes(ctx), []);
    await page.waitForFunction(() => !document.querySelector('#j2ha_roomCards .j2ha-room-card[data-object_id="3"] .j2ha-room-exclude').disabled);
    assert.deepEqual(ctx.errors, []);
  });
});
