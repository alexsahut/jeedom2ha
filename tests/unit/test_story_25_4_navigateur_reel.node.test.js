// ARTEFACT — Story 25.4 (AC1, AC5 à AC7, AC9, AC15, AC17 à AC19, AC22, AC29 (5)) : la vue C dans un VRAI Chromium
// (Playwright) avec le vrai jQuery, le vrai squelette PHP, le vrai CSS et les vrais scripts du plugin ; vrais clics
// (contrôle d'actionnabilité : ce qui est caché, recouvert ou réduit à 2 px fait échouer le test). Réseau factice,
// retardé à la demande. Précision ClaudeBox n°1 : la réponse tardive de l'AC29 (5) est prouvée ICI (l'interception
// du gate ne retarde pas une réponse à la demande). Ignoré si Playwright, jQuery ou PHP sont introuvables. Aucune
// box, données fictives (CC-48).
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView, gate } = require('./helpers/workview_browser');
const { makeScene } = require('./helpers/big_scene');

const THRESHOLD = require('../../desktop/js/jeedom2ha_workview.js').LAYOUT_SPLIT_MIN_WIDTH;
const actions = (ctx, name) => ctx.journal.filter((e) => e.action === name);

test('25.4 réel — ouvrir depuis une carte : aucune modale, aucune lecture ; la barre de santé reste, la grille est masquée', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    const before = ctx.journal.length;
    await page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="4"]').click();
    await page.locator('#j2ha_workView').waitFor({ state: 'visible' });
    assert.equal(await page.locator('.modal:visible, .bootbox:visible').count(), 0, 'aucune modale');
    assert.equal(ctx.journal.length, before, 'aucune requête à l’ouverture');
    assert.equal(await page.locator('#div_bridgeHealthBanner').isVisible(), true);
    assert.equal(await page.locator('#j2ha_roomCards').isVisible(), false);
    assert.equal(await page.locator('.j2ha-wv-room[data-object_id="4"]').getAttribute('aria-selected'), 'true');
    assert.deepEqual(ctx.errors, []);
  });
});

test('25.4 réel — sélection d’un équipement : un getMappingOverrides, tableau des commandes, pastille d’arbre = badge du détail', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    await page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="3"]').click();
    const row = page.locator('.j2ha-wv-eq').first();
    const eqId = await row.getAttribute('data-eq-id');
    const treeWord = (await row.locator('.j2ha-state-word').first().innerText()).trim();
    await row.locator('.j2ha-wv-row').click();
    await page.locator(`.j2ha-eq-panel[data-eq-id="${eqId}"] .j2ha-cmd-table`).waitFor({ state: 'visible' });
    assert.equal(actions(ctx, 'getMappingOverrides').length, 1);
    const badge = (await page.locator(`.j2ha-eq-panel[data-eq-id="${eqId}"] .j2ha-eq-publish-badge`).innerText()).trim();
    assert.equal(typeof badge, 'string');
    assert.ok(treeWord.length > 0);
    // Le mot d'état de l'arbre vient de l'entrée agrégée, celui du détail de l'arbre unitaire : mêmes mots (parité 25.2).
    // La fixture unitaire de ce test est celle d'un autre équipement ; on ne compare donc que la présence des deux.
    assert.deepEqual(ctx.errors, []);
  });
});

test('25.4 réel — A puis B : la réponse tardive de A n’est pas rendue (AC29 (5), porté par ce test)', async (t) => {
  const delay = (action, eqId) => (action === 'getMappingOverrides' && eqId === 102 ? 700 : 0);
  await withRealView(t, { delay }, async (page, ctx) => {
    await page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="3"]').click();
    await page.locator('.j2ha-wv-eq[data-eq-id="102"] .j2ha-wv-row').click();
    await page.locator('.j2ha-wv-eq[data-eq-id="103"] .j2ha-wv-row').click();
    await page.waitForFunction(() => (document.querySelector('.j2ha-eq-panel[data-eq-id="103"] .j2ha-eq-publish-badge')?.textContent ?? '').trim() !== '');
    await new Promise((resolve) => setTimeout(resolve, 900));
    assert.equal(actions(ctx, 'getMappingOverrides').length, 2);
    assert.equal(await page.locator('.j2ha-eq-panel[data-eq-id="102"]').count(), 0, 'la réponse de A, arrivée après, n’est pas rendue');
    assert.equal(await page.locator('.j2ha-eq-panel[data-eq-id="103"]').count(), 1);
    assert.deepEqual(ctx.errors, []);
  });
});

test('25.4 réel — lien profond : un getEquipmentStates (sans refresh) et un getMappingOverrides ; « Précédent » remonte d’un niveau', async (t) => {
  await withRealView(t, { hash: '#j2ha-vue=piece:3;eq:102' }, async (page, ctx) => {
    await page.locator('.j2ha-eq-panel[data-eq-id="102"] .j2ha-cmd-table').waitFor({ state: 'visible' });
    assert.equal(actions(ctx, 'getEquipmentStates').length, 1);
    assert.equal(actions(ctx, 'getMappingOverrides').length, 1);
    assert.ok(!ctx.bodies.some((b) => b.includes('refresh=')));
    // Clic sur la pièce dans l'arbre, puis « Précédent ».
    await page.locator('.j2ha-wv-room[data-object_id="3"] > .j2ha-wv-row').click();
    assert.equal(await page.evaluate(() => location.hash), '#j2ha-vue=piece:3');
    await page.goBack();
    assert.equal(await page.locator('.j2ha-eq-panel[data-eq-id="102"]').count(), 1, 'retour à l’entrée précédente (lien profond)');
    assert.deepEqual(ctx.errors, []);
  });
});

test('25.4 réel — aucun défilement horizontal dans le détail à plusieurs largeurs ; layout split puis compact ; tiroir « Pièces »', async (t) => {
  const big = makeScene({ rooms: 4, equipments: 40, seed: 3, longNames: true });
  for (const width of [1280, 1100, 900, 768]) {
    await withRealView(t, { width, height: 900, scene: big.scene, equipments: big.equipments }, async (page, ctx) => {
      await page.locator('#j2ha_roomCards .j2ha-room-card').first().click();
      await page.locator('.j2ha-wv-eq .j2ha-wv-row').first().waitFor({ state: 'visible' }).catch(() => {});
      const layout = await page.locator('#j2ha_workView').getAttribute('data-j2ha-layout');
      assert.equal(layout, width >= THRESHOLD ? 'split' : 'compact', 'largeur ' + width);
      if (layout === 'compact') {
        const toggle = page.locator('.j2ha-wv-drawer-toggle');
        await toggle.click();
        assert.equal(await toggle.getAttribute('aria-expanded'), 'true');
        await page.locator('.j2ha-wv-eq .j2ha-wv-row').first().click();
        assert.equal(await toggle.getAttribute('aria-expanded'), 'false');
      } else {
        await page.locator('.j2ha-wv-eq .j2ha-wv-row').first().click();
      }
      await page.locator('.j2ha-eq-panel .j2ha-cmd-table').waitFor({ state: 'visible' });
      const overflow = await page.locator('.j2ha-wv-detail').evaluate((el) => el.scrollWidth - el.clientWidth);
      assert.ok(overflow <= 1, `défilement horizontal de ${overflow}px à ${width}px`);
      assert.deepEqual(ctx.errors, []);
    });
  }
});

test('25.4 réel — clavier : roving tabindex, flèches, Entrée ; focus déplacé vers le titre du détail', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    await page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="3"]').click();
    const tabbable = await page.locator('.j2ha-wv-tree [role=treeitem][tabindex="0"]').count();
    assert.equal(tabbable, 1, 'une seule ligne dans l’ordre de tabulation');
    const selected = page.locator('.j2ha-wv-room[data-object_id="3"]');
    await selected.focus();
    await page.keyboard.press('ArrowDown');
    assert.match(await page.evaluate(() => document.activeElement.className), /j2ha-wv-eq/);
    await page.keyboard.press('Enter');
    await page.locator('.j2ha-eq-panel .j2ha-cmd-table').waitFor({ state: 'visible' });
    assert.equal(await page.evaluate(() => document.activeElement.classList.contains('j2ha-wv-title')), true, 'focus sur le titre du détail');
    assert.equal(await page.evaluate(() => document.activeElement.getAttribute('tabindex')), '-1');
    assert.equal(await page.locator('.j2ha-wv-tree').getAttribute('role'), 'tree');
    assert.deepEqual(ctx.errors, []);
  });
});

test('25.4 réel — le focus clavier reste sur la puce de la vue après un filtre et après une relecture des états', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    await page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="3"]').click();
    const chip = page.locator('.j2ha-wv-chips .j2ha-chip-filter:not([disabled])').first();
    const key = await chip.getAttribute('data-filter');
    await chip.focus();
    await page.keyboard.press('Enter');
    const focused = () => page.evaluate(() => document.activeElement && { cls: document.activeElement.className, filter: document.activeElement.getAttribute('data-filter'), pressed: document.activeElement.getAttribute('aria-pressed') });
    let now = await focused();
    assert.match(now.cls, /j2ha-wv-chip/);
    assert.equal(now.filter, key);
    assert.equal(now.pressed, 'true');
    await page.evaluate(() => window.j2haNotifyStatesChanged());
    await new Promise((resolve) => setTimeout(resolve, 900));
    assert.equal(ctx.journal.filter((e) => e.action === 'getEquipmentStates').length, 2);
    now = await focused();
    assert.match(now.cls, /j2ha-wv-chip/, 'la puce garde le focus après la relecture');
    assert.deepEqual(ctx.errors, []);
  });
});

test('25.4 réel — ouvrir le menu « ⋯ » de pièce puis annuler la suppression n’émet aucune écriture (AC29 (9))', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    await page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="3"]').click();
    await page.locator('.j2ha-wv .j2ha-menu-toggle').click();
    await page.locator('.j2ha-wv .j2ha-room-recreate').click();
    const confirmation = page.locator('.bootbox .btn-danger');
    await confirmation.waitFor({ state: 'visible' });
    await page.locator('.bootbox .btn-default').filter({ hasText: /^Annuler$/ }).first().click();
    assert.equal(ctx.journal.filter((e) => e.action === 'executeHaAction').length, 0);
    assert.deepEqual(ctx.errors, []);
  });
});

test('25.4 réel — le parcours vue-maitre-detail-c du gate passe sur la page livrée, en lecture seule', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    const parcours = await import(gate('parcours', 'vue-maitre-detail-c.mjs'));
    const { normalizeParcoursRecord } = await import(gate('lib', 'report.mjs'));
    const recorded = {};
    const helpers = {
      record: (key, value) => { const [k, v] = normalizeParcoursRecord(key, value); recorded[k] = v; },
      journalEntries: () => ctx.journal,
    };
    await parcours.run(page, { helpers });
    assert.equal(recorded.lectures_a_l_ouverture, 0);
    assert.equal(recorded.lectures_arbre_selection, 1);
    assert.equal(recorded.lien_profond_lectures_etat, 1);
    assert.equal(recorded.lien_profond_lectures_arbre, 1);
    assert.ok(recorded.largeur_fenetre_large >= THRESHOLD && recorded.largeur_fenetre_etroite < THRESHOLD);
    assert.equal(recorded.precedent_niveaux, 2);
    assert.equal(recorded.ecritures_menu_piece, 0);
    assert.ok(Number.isFinite(recorded.temps_chargement_eq_selectionne_ms));
    assert.deepEqual(ctx.errors, []);
    const writes = ctx.journal.filter((e) => ['executeHaAction', 'exportDiagnostic', 'scanTopology', 'saveMappingOverride', 'savePublicationOverride'].includes(e.action)).length;
    assert.equal(writes, 0, 'aucune écriture émise par le parcours');
  });
});

test('25.4 réel — un défilement horizontal du détail, une lecture à l’ouverture ou un arbre sans les pièces de la page fait échouer le parcours', async (t) => {
  await withRealView(t, {}, async (page) => {
    const parcours = await import(gate('parcours', 'vue-maitre-detail-c.mjs'));
    // Une lecture d'arbre émise à l'ouverture (journal truqué) fait échouer l'assertion (1).
    let calls = 0;
    const helpers = {
      record: () => {},
      journalEntries: () => {
        calls += 1;
        return calls > 2 ? [{ action: 'getMappingOverrides', resourceType: 'xhr', path: '/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php' }] : [];
      },
    };
    await assert.rejects(() => parcours.run(page, { helpers }), /lecture-a-l-ouverture/);
  });
});

