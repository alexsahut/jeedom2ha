// ARTEFACT — Front v3, Lot 1 : page maison sans phrase. Barre d'état (« Appliquer (n) », verdict « Rien à faire » FAIL-CLOSED),
// onglets, puces-boutons qui filtrent la grille, liste « À faire », tuiles 220 × 72. Vrai code sur faux DOM (squelette PHP
// réel) puis en vrai Chromium. Données fictives (CC-48).
'use strict';

const { describe, it } = require('node:test');
const test = require('node:test');
const assert = require('node:assert/strict');
const O = require('../../desktop/js/jeedom2ha_overview.js');
const { plain, phpAvailable, renderPhp, mainPart, SCENE, startPage } = require('./helpers/page_b_harness');
const { withRealView } = require('./helpers/workview_browser');

const maybe = phpAvailable ? it : it.skip;
const NOW = Date.parse('2026-11-14T12:00:00Z');
const UP = (op, at) => ({ daemon: true, broker: { state: 'connected' }, derniere_operation_resultat: op, derniere_synchro_terminee: at });
const SYNC_OK = { intention: 'sync', resultat: 'succes', message: 'Synchronisation terminée.' };
const CLEAN = { counts: { published: 3, to_apply: 0, blocked: 0, other: 1, unread: 0 } };

describe('Lot 1 — verdict de la barre d’état, fail-closed', () => {
  it('« Rien à faire » seulement si la dernière opération est une relecture RÉUSSIE de moins de 24 h et rien n’est ouvert', () => {
    const v = O.statusVerdict(UP(SYNC_OK, new Date(NOW - 3600e3).toISOString()), CLEAN, NOW);
    assert.equal(v.kind, 'ok');
    assert.equal(plain(v.text), 'Rien à faire');
    assert.match(plain(v.title), /^Relu à \d\d:\d\d$/);
  });

  it('sinon « Non vérifié » : relecture de plus de 24 h, partielle, échouée, autre opération, jamais relu, états non lus ou illisibles', () => {
    const old = new Date(NOW - 25 * 3600e3).toISOString();
    const recent = new Date(NOW - 60e3).toISOString();
    for (const [status, overview] of [
      [UP(SYNC_OK, old), CLEAN],
      [UP({ intention: 'sync', resultat: 'partiel' }, recent), CLEAN],
      [UP({ intention: 'sync', resultat: 'echec' }, recent), CLEAN],
      [UP({ intention: 'publier', resultat: 'succes' }, recent), CLEAN], // relecture précédente jamais observée
      [UP({ intention: 'publier', resultat: 'partiel' }, recent), CLEAN],
      [UP('aucun', null), CLEAN],
      [UP(SYNC_OK, 'pas une date'), CLEAN],
      [UP(SYNC_OK, recent), null],
      [UP(SYNC_OK, recent), { counts: Object.assign({}, CLEAN.counts, { unread: 1 }) }],
    ]) {
      assert.equal(O.statusVerdict(status, overview, NOW).kind, 'unverified', JSON.stringify([status, overview]));
    }
  });

  it('après un « Appliquer » ou un « Republier » RÉUSSI : ✓ si la relecture réussie observée avant (même date de fin) a moins de 24 h', () => {
    const at = new Date(NOW - 3600e3).toISOString();
    let memory = O.rememberSync(null, UP(SYNC_OK, at));
    assert.deepEqual(memory, { at, ok: true });
    const applied = UP({ intention: 'publier', resultat: 'succes' }, at);
    memory = O.rememberSync(memory, applied);
    assert.deepEqual(memory, { at, ok: true }, 'la mémoire survit à l’opération suivante');
    assert.equal(O.statusVerdict(applied, CLEAN, NOW, memory).kind, 'ok');
    assert.equal(O.statusVerdict(UP({ intention: 'publier', resultat: 'succes' }, at), CLEAN, NOW, null).kind, 'unverified', 'sans relecture observée');
    assert.equal(O.statusVerdict(UP({ intention: 'publier', resultat: 'echec' }, at), CLEAN, NOW, memory).kind, 'unverified', 'dernière opération en échec');
    assert.equal(O.statusVerdict(UP({ intention: 'supprimer', resultat: 'partiel' }, at), CLEAN, NOW, memory).kind, 'unverified', 'dernière opération partielle');
    const failed = O.rememberSync(null, UP({ intention: 'sync', resultat: 'partiel' }, at));
    assert.equal(O.statusVerdict(applied, CLEAN, NOW, failed).kind, 'unverified', 'la relecture retenue n’a pas réussi');
    const later = new Date(NOW - 60e3).toISOString();
    assert.equal(O.rememberSync(memory, UP({ intention: 'publier', resultat: 'succes' }, later)), null, 'autre date de fin : la mémoire ne vaut plus');
    const old = new Date(NOW - 25 * 3600e3).toISOString();
    assert.equal(O.statusVerdict(UP({ intention: 'publier', resultat: 'succes' }, old), CLEAN, NOW, { at: old, ok: true }).kind, 'unverified', 'plus de 24 h');
  });

  it('rien quand il y a quelque chose à faire (Appliquer / À faire le disent) ou quand le pont est en panne (les pastilles le disent)', () => {
    const recent = new Date(NOW - 60e3).toISOString();
    assert.equal(O.statusVerdict(UP(SYNC_OK, recent), { counts: Object.assign({}, CLEAN.counts, { to_apply: 2 }) }, NOW), null);
    assert.equal(O.statusVerdict(UP(SYNC_OK, recent), { counts: Object.assign({}, CLEAN.counts, { blocked: 1 }) }, NOW), null);
    assert.equal(O.statusVerdict({ daemon: false }, CLEAN, NOW), null);
    assert.equal(O.statusVerdict({ daemon: true, broker: { state: 'disconnected' } }, CLEAN, NOW), null);
    assert.equal(O.statusVerdict(null, CLEAN, NOW), null);
  });
});

describe('Lot 1 — puces, marques, confirmation', () => {
  it('houseChips : ordre du liseré, nombres non nuls seulement (sauf la puce active), icône et définition', () => {
    const counts = { published: 8, to_apply: 6, blocked: 4, other: 4, unread: 0 };
    const chips = O.houseChips(counts, null, null);
    assert.deepEqual(chips.map((c) => c.key), ['published', 'to_apply', 'blocked', 'other']);
    assert.deepEqual(chips.map((c) => c.scope), ['grid', 'grid', 'todo', 'grid']);
    chips.forEach((c) => { assert.match(c.icon, /^fa-/); assert.ok(plain(c.title).length > 0); });
    assert.deepEqual(O.houseChips(counts, null, 'unread').map((c) => c.key).pop(), 'unread', 'puce active à zéro gardée');
  });

  it('tileMarks : seulement les nombres non nuls ; « exclus » en dernier, d’après la ventilation ; filtrées par groupe', () => {
    const room = {
      counts: { published: 1, to_apply: 1, blocked: 2, other: 2, unread: 0 },
      equipments: [{ state: 'disabled' }, { state: 'excluded' }],
      exclusion: { excluded: 1 },
    };
    assert.deepEqual(O.tileMarks(room).map((m) => [m.key, m.count]), [['blocked', 2], ['to_apply', 1], ['disabled', 1], ['excluded', 1]]);
    assert.deepEqual(O.tileMarks(room, 'other').map((m) => m.key), ['disabled', 'excluded']);
    assert.deepEqual(O.tileMarks({ counts: { published: 2, to_apply: 0, blocked: 0, other: 0, unread: 0 }, equipments: [] }), []);
  });

  it('applyDialog : titre et bouton chiffrés, une ligne', () => {
    const d = O.applyDialog(6);
    assert.equal(plain(d.title), 'Appliquer 6 réglages en attente ?');
    assert.equal(plain(d.confirmLabel), 'Appliquer (6)');
    assert.equal(d.lines.length, 1);
    assert.equal(plain(O.applyDialog(1).title), 'Appliquer 1 réglage en attente ?');
  });
});

describe('Lot 1 — page rendue (squelette PHP réel)', () => {
  maybe('aucune phrase permanente : ni titre, ni légende, ni ligne d’aide, ni tuile « Gestion » ; liste filtrée retirée', () => {
    const main = mainPart(renderPhp(SCENE).html);
    assert.doesNotMatch(main, /<legend|j2ha-help-line|j2ha_v2_helpline|j2ha_v2_legend|j2ha_filterPanel|j2ha_houseMeta|logoSecondary|\{\{Gestion\}\}/);
    assert.match(main, /id="j2ha_tab_scenarios"/);
    assert.doesNotMatch(main, /DisplayCard|ListContainer/);
  });

  maybe('« Appliquer (n) » visible seulement si n > 0, avec le nombre de la puce « à appliquer »', () => {
    const ui = startPage({ bridgeStatus: UP('aucun', null) });
    const n = ui.page.view().overview.counts.to_apply;
    assert.ok(n > 0);
    assert.equal(ui.$('#bt_j2haApply').prop('hidden'), false);
    assert.equal(ui.text('#bt_j2haApply .j2ha-v3-apply-count'), `(${n})`);
    assert.equal(ui.page.toApplyIds().length, n);
  });

  maybe('verdict rendu : « Non vérifié » + [Relire] quand rien n’est ouvert mais la relecture n’est pas prouvée', () => {
    let status = UP('aucun', null);
    const ui = startPage({ bridgeStatus: () => status });
    // La scène a des bloqués : aucun verdict.
    assert.equal(ui.$('#j2ha_v3_verdict').children().length, 0);
    assert.equal(ui.$('#j2ha_v3_verdict').attr('data-kind'), undefined);
    status = { daemon: false };
    ui.page.statusChanged();
    assert.equal(ui.$('#j2ha_v3_verdict').children().length, 0);
  });

  maybe('onglets : Équipements sélectionné, Scénarios masqué ; clic et flèches basculent', () => {
    const ui = startPage();
    assert.equal(ui.$('#j2ha_tabBtnEquipments').attr('aria-selected'), 'true');
    assert.equal(ui.$('#j2ha_tab_scenarios').prop('hidden'), true);
    ui.click('#j2ha_tabBtnScenarios');
    assert.equal(ui.$('#j2ha_tabBtnScenarios').attr('aria-selected'), 'true');
    assert.equal(ui.$('#j2ha_tab_equipments').prop('hidden'), true);
    assert.equal(ui.$('#j2ha_tab_scenarios').prop('hidden'), false);
    ui.key('#j2ha_tabBtnScenarios', 'ArrowLeft');
    assert.equal(ui.$('#j2ha_tab_equipments').prop('hidden'), false);
  });
});

test('Lot 1 réel — « Appliquer (n) » : confirmation chiffrée puis executeHaAction publier / equipement sur les n équipements', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    await page.waitForFunction(() => !document.querySelector('#bt_j2haApply').hidden && !document.querySelector('#bt_j2haApply').disabled);
    const ids = await page.evaluate(() => window.Jeedom2haOverviewPage.toApplyIds());
    assert.ok(ids.length > 0);
    assert.equal((await page.locator('#bt_j2haApply').innerText()).trim(), `Appliquer (${ids.length})`);
    await page.locator('#bt_j2haApply').click();
    const dialog = page.locator('.bootbox').first();
    await dialog.waitFor({ state: 'visible' });
    assert.match((await dialog.innerText()).replace(/\s+/g, ' '), new RegExp(`^Appliquer ${ids.length} réglages en attente \\?`));
    assert.equal(ctx.journal.filter((e) => e.action === 'executeHaAction').length, 0, 'rien avant la confirmation');
    await dialog.locator('[data-bb-handler="confirm"]').click();
    await new Promise((r) => setTimeout(r, 300));
    const idx = ctx.journal.findIndex((e) => e.action === 'executeHaAction');
    assert.ok(idx >= 0, 'executeHaAction émis');
    const body = new URLSearchParams(ctx.bodies[idx]);
    assert.equal(body.get('intention'), 'publier');
    assert.equal(body.get('portee'), 'equipement');
    assert.deepEqual(JSON.parse(body.get('selection')), ids);
    assert.deepEqual(ctx.errors, []);
  });
});

test('Lot 1 réel — barre d’état : pastilles, ⚙ (gotoPluginConf), tuiles 220 × 72 sans règle *DisplayCard du cœur', async (t) => {
  await withRealView(t, {}, async (page) => {
    await page.waitForFunction(() => document.querySelector('#span_healthBridge').getAttribute('data-level') === 'ok');
    const r = await page.evaluate(() => ({
      bridge: document.querySelector('#span_healthBridge').getAttribute('aria-label'),
      conf: !!document.querySelector('#div_bridgeHealthBanner .eqLogicAction[data-action="gotoPluginConf"]'),
      tile: (() => { const b = document.querySelector('#j2ha_roomCards .j2ha-room-card').getBoundingClientRect(); return [b.width, b.height]; })(),
      sync: document.querySelector('#span_healthSync').textContent.trim(),
    }));
    assert.equal(r.bridge, 'Démon : Actif');
    assert.ok(r.conf);
    assert.deepEqual(r.tile, [220, 72]);
    assert.equal(r.sync, 'Jamais relu');
  });
});

test('Lot 1 réel — parcours page-principale-b avec une pièce exclue visible sous un filtre : compteur lu dans data-count', async (t) => {
  const { gate } = require('./helpers/workview_browser');
  const scene = Object.assign({}, SCENE, { config: { excludedObjects: '4' } });
  await withRealView(t, { scene }, async (page, ctx) => {
    const visibleExcluded = [];
    for (const key of ['published', 'to_apply', 'other', 'unread']) {
      await page.evaluate((k) => window.Jeedom2haOverviewPage.setFilter(k), key);
      const r = await page.evaluate(() => {
        const card = document.querySelector('#j2ha_roomCards .j2ha-room-card[data-object_id="4"]');
        return { hidden: card.hidden, text: card.querySelector('.j2ha-room-ratio').textContent, count: card.getAttribute('data-count') };
      });
      if (!r.hidden) visibleExcluded.push(r);
      await page.evaluate(() => window.Jeedom2haOverviewPage.setFilter(null));
    }
    assert.ok(visibleExcluded.length > 0, 'la pièce exclue reste visible sous au moins un filtre');
    visibleExcluded.forEach((r) => { assert.equal(r.text, 'Pièce exclue'); assert.match(r.count, /^\d+$/); });
    const parcours = await import(gate('parcours', 'page-principale-b.mjs'));
    const recorded = {};
    await parcours.run(page, { helpers: { record: (k, v) => { recorded[k] = v; }, journalEntries: () => ctx.journal } });
    assert.ok(recorded.puces_controlees >= 3);
    assert.deepEqual(ctx.errors, []);
  });
});

test('Lot 1 réel — pastille Home Assistant toujours visible : grise avec « ? » et raison en info-bulle quand l’état est inconnu', async (t) => {
  await withRealView(t, {}, async (page) => {
    // Le banc répond à getBridgeStatus sans champ `ha` : état inconnu.
    await page.waitForFunction(() => document.querySelector('#span_healthBridge').getAttribute('data-level') === 'ok');
    const r = await page.evaluate(() => {
      const ha = document.querySelector('#span_healthHa');
      return { visible: ha.getBoundingClientRect().width > 0 && getComputedStyle(document.querySelector('#div_healthHa')).display !== 'none',
        level: ha.getAttribute('data-level'), title: ha.getAttribute('data-j2ha-tip'), q: getComputedStyle(ha.querySelector('.j2ha-v3-pill-q')).display };
    });
    assert.equal(r.visible, true);
    assert.equal(r.level, 'unknown');
    assert.notEqual(r.q, 'none', '« ? » affiché');
    assert.equal(r.title, 'Home Assistant : état inconnu (le démon ne fournit pas cette information)');
  });
});
