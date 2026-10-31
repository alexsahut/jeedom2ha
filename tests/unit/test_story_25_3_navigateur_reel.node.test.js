// ARTEFACT — Story 25.3 (AC1, AC5, AC9 à AC12, AC17) : la page B dans un VRAI navigateur (Chromium via Playwright)
// avec le VRAI jQuery, le VRAI squelette PHP (faux cœur Jeedom), le VRAI CSS et les VRAIS scripts du plugin ; seuls
// le réseau (`$.ajax`) et `bootbox` sont factices. Le parcours `page-principale-b.mjs` du gate 20-0 est exécuté sur
// cette page, avec un journal alimenté par le faux réseau. Ignoré si Playwright, jQuery ou PHP sont introuvables
// (CI sans outils du gate). Aucune box, aucun réseau réel, données fictives (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const { SCENE, FIXTURE, phpAvailable, renderPhp, mainPart, equipmentsFor } = require('./helpers/page_b_harness');

const gate = (...parts) => pathToFileURL(path.join(__dirname, '..', 'e2e', 'gate', ...parts)).href;
const JQUERY = [process.env.JEEDOM2HA_JQUERY, '/usr/share/javascript/jquery/jquery.min.js', '/usr/share/javascript/jquery/jquery.js']
  .filter(Boolean).find((file) => fs.existsSync(file));

const read = (file) => fs.readFileSync(file, 'utf8');

const BOOTBOX_STUB = `
window.bootbox = { dialog: function (o) {
  var $m = $('<div class="bootbox modal"></div>');
  $m.append($('<div class="modal-title"></div>').html(o.title || ''));
  $m.append($('<div class="bootbox-body"></div>').append(o.message));
  var handlers = {};
  function close() { $m.detach(); if (handlers['hidden.bs.modal']) handlers['hidden.bs.modal'](); }
  Object.keys(o.buttons || {}).forEach(function (k) {
    var b = o.buttons[k];
    $m.append($('<button type="button"></button>').addClass('btn ' + (b.className || '')).text(b.label).on('click', function () { if (b.callback) b.callback(); close(); }));
  });
  $m.addClass(o.className || '');
  $(document.body).append($m);
  if (o.onEscape) $(document).on('keydown.bb', function (e) { if (e.key === 'Escape') { $(document).off('keydown.bb'); if (typeof o.onEscape === 'function') o.onEscape(); close(); } });
  return { on: function (ev, cb) { handlers[ev] = cb; } };
} };
$.fn.sortable = function () { return this; };
$.fn.showAlert = function () { return this; };
`;

async function withRealPage(t, fn, options) {
  const withView = !options || options.workview !== false;
  if (!phpAvailable || !JQUERY) { t.skip('PHP ou jQuery indisponible'); return; }
  let playwright;
  try {
    const { loadPlaywright } = await import(gate('lib', 'playwright.mjs'));
    playwright = loadPlaywright();
  } catch { t.skip('Playwright indisponible'); return; }
  const rendered = renderPhp(SCENE);
  const rooms = rendered.vars.j2haRoomsTree;
  const states = { state: 'ok', result: { status: 'ok', payload: { schema_version: 1, available: true, meta: { action_in_progress: false }, equipments: equipmentsFor(rooms), unread: [] } } };
  const trees = { default: { state: 'ok', result: { status: 'ok', payload: FIXTURE['101'].tree } } };
  const fixtures = { bridge: { state: 'ok', result: { daemon: true, broker: { state: 'connected' }, derniere_operation_resultat: 'aucun' } }, states, trees };
  const browser = await playwright.chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    const journal = [];
    const bodies = [];
    const html = '<!doctype html><html><head><meta charset="utf-8"><style>' + read('desktop/css/jeedom2ha.css') + '</style></head><body>'
      + mainPart(rendered.html).replace(/\{\{([^}]*)\}\}/g, '$1') + '<div id="div_alert"></div></body></html>';
    // Vrai réseau du navigateur, servi par Playwright : le VRAI $.ajax de jQuery émet de vraies requêtes POST.
    await page.route('http://gate.test/**', async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      if (url.pathname === '/') { await route.fulfill({ contentType: 'text/html', body: html }); return; }
      if (url.pathname.endsWith('/jeedom2ha.ajax.php')) {
        const params = new URLSearchParams(request.postData() || '');
        const action = params.get('action');
        // Même forme que le journal du gate (appendEntry) : le parcours filtre sur resourceType et path.
        journal.push({ action, verdict: 'lecture', method: 'POST', resourceType: request.resourceType(), path: url.pathname });
        bodies.push(request.postData() || '');
        let body = { state: 'error', result: 'écriture interdite en test' };
        if (action === 'getBridgeStatus') body = fixtures.bridge;
        else if (action === 'getEquipmentStates') body = fixtures.states;
        else if (action === 'getMappingOverrides') body = fixtures.trees.default;
        await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
        return;
      }
      await route.fulfill({ status: 404, body: '' });
    });
    await page.goto('http://gate.test/');
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.addScriptTag({ content: read(JQUERY) });
    await page.evaluate((vars) => { window.j2haRoomsTree = vars.j2haRoomsTree; window.j2haAncestors = vars.j2haAncestors; }, rendered.vars);
    await page.addScriptTag({ content: BOOTBOX_STUB });
    for (const file of ['jeedom2ha_mapping_override', 'jeedom2ha_mapping_surface', 'jeedom2ha_action_budget', 'jeedom2ha_overview', ...(withView ? ['jeedom2ha_workview'] : []), 'jeedom2ha']) {
      await page.addScriptTag({ content: read(`desktop/js/${file}.js`).replace(/\{\{([^}]*)\}\}/g, '$1') });
    }
    await page.waitForFunction(() => (document.querySelector('#j2ha_houseNumber')?.textContent ?? '').trim() !== '');
    await fn(page, { rendered, errors, fixtures, journal, bodies });
  } finally {
    await browser.close();
  }
}

test('25.3 navigateur réel — un seul appel au chargement, jauges cohérentes, filtres sans réseau, aucune erreur JS', async (t) => {
  await withRealPage(t, async (page, ctx) => {
    const journal = async () => ctx.journal.map((e) => e.action);
    const actions = await journal();
    assert.equal(actions.filter((a) => a === 'getEquipmentStates').length, 1);
    assert.equal(actions.filter((a) => a === 'getMappingOverrides').length, 0);
    assert.equal(actions.filter((a) => a === 'getBridgeStatus').length, 1);
    const bodies = ctx.bodies;
    assert.ok(!bodies.some((b) => b.includes('refresh=')), 'aucun refresh au chargement');
    const text = (await page.locator('#j2ha_houseSub').textContent()).trim();
    assert.match(text, /^publiés? sur 12$/);
    assert.equal((await page.locator('#j2ha_houseMeta').textContent()).trim(), '12 équipements Jeedom, 4 pièces');
    assert.equal(await page.locator('#j2ha_roomCards .j2ha-room-card').count(), 5);
    assert.deepEqual(ctx.errors, []);
    // Filtre sans requête réseau.
    const before = (await journal()).length;
    await page.locator('#j2ha_houseChips .j2ha-chip-filter:not([disabled])').first().click();
    assert.ok((await page.locator('#j2ha_filterList .j2ha-frow').count()) > 0);
    assert.equal((await journal()).length, before);
    // Style : la jauge de la maison est visible et segmentée en flex.
    const display = await page.locator('#j2ha_houseGauge .j2ha-gauge').evaluate((el) => getComputedStyle(el).display);
    assert.equal(display, 'flex');
    // Couleur Jeedom : variable CSS d'accent posée sur la carte validée seulement.
    const accents = await page.locator('#j2ha_roomCards .j2ha-room-card').evaluateAll((cards) => cards.map((c) => c.style.getPropertyValue('--j2ha-room-color').trim()));
    assert.deepEqual(accents.filter(Boolean).sort(), ['#123', '#ff8800']);
    assert.deepEqual(ctx.errors, []);
  });
});

test('25.3 navigateur réel — le parcours du gate page-principale-b passe sur la page livrée', async (t) => {
  await withRealPage(t, async (page, ctx) => {
    const parcours = await import(gate('parcours', 'page-principale-b.mjs'));
    const { normalizeParcoursRecord } = await import(gate('lib', 'report.mjs'));
    const recorded = {};
    const helpers = {
      record: (key, value) => { const [k, v] = normalizeParcoursRecord(key, value); recorded[k] = v; },
      journalEntries: () => ctx.journal,
    };
    await parcours.run(page, { helpers });
    assert.equal(recorded.lectures_etat_chargement, 1);
    assert.equal(recorded.lectures_par_equipement_chargement, 0);
    assert.equal(recorded.refresh_emis, 1);
    assert.equal(recorded.ecritures_menu, 0);
    assert.ok(recorded.puces_controlees >= 3);
    assert.ok(recorded.equipements_fenetre_piece >= 1);
    assert.deepEqual(ctx.errors, []);
    const writes = ctx.journal.filter((e) => ['executeHaAction', 'exportDiagnostic', 'scanTopology'].includes(e.action)).length;
    assert.equal(writes, 0, 'aucune écriture émise par le parcours');
  });
});

test('25.3 navigateur réel — un bandeau bleu ou une lecture par équipement au chargement fait échouer le parcours', async (t) => {
  await withRealPage(t, async (page) => {
    const parcours = await import(gate('parcours', 'page-principale-b.mjs'));
    const helpers = { record: () => {}, journalEntries: () => [{ action: 'getEquipmentStates' }, { action: 'getMappingOverrides' }] };
    await assert.rejects(() => parcours.run(page, { helpers }), /lecture-par-equipement-au-chargement/);
    await page.evaluate(() => { document.body.insertAdjacentHTML('beforeend', '<div class="alert alert-info j2ha-surface-intro">x</div>'); });
    const helpers2 = { record: () => {}, journalEntries: () => [{ action: 'getEquipmentStates' }] };
    await assert.rejects(() => parcours.run(page, { helpers: helpers2 }), /bandeau-bleu-present/);
  });
});

// Story 25.4 : avec la vue de travail, une puce de la page B ouvre la vue ; le comportement de 25.3 (liste filtrée sur la page B)
// est celui du repli sans la vue, que ce test exerce (`workview: false`). Le focus des puces DE LA VUE est contrôlé par
// `test_story_25_4_navigateur_reel`.
test('25.3 navigateur réel — le focus clavier reste sur la puce après un filtre ou une relecture', async (t) => {
  await withRealPage(t, async (page, ctx) => {
    await page.locator('#j2ha_houseChips .j2ha-chip-filter:not([disabled])').first().focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('#j2ha_houseChips .j2ha-chip-filter[aria-pressed="true"]').count(), 1);
    const focused = () => page.evaluate(() => document.activeElement && document.activeElement.className);
    assert.match(await focused(), /j2ha-chip-filter/, 'la puce garde le focus après le rendu');
    assert.equal(await page.evaluate(() => document.activeElement.getAttribute('aria-pressed')), 'true');
    // Relecture complète des états : la puce focalisée reste focalisée.
    await page.evaluate(() => window.j2haNotifyStatesChanged());
    await new Promise((resolve) => setTimeout(resolve, 900));
    assert.equal(ctx.journal.filter((e) => e.action === 'getEquipmentStates').length, 2);
    assert.match(await focused(), /j2ha-chip-filter/);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#j2ha_filterList .j2ha-frow').count(), 0, 'Échap retire le filtre');
    assert.deepEqual(ctx.errors, []);
  }, { workview: false });
});
