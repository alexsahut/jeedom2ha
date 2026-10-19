'use strict';

/* Aide de test (Story 25.4) : la page du plugin dans un VRAI Chromium (Playwright), avec le VRAI jQuery, le VRAI squelette
 * PHP (faux cœur Jeedom), le VRAI CSS et les VRAIS scripts du plugin, y compris la vue C. Seuls le réseau (servi par
 * Playwright, retardable par action / équipement) et `bootbox` sont factices. Ignoré si Playwright, jQuery ou PHP sont
 * introuvables. Aucune box, aucun réseau réel, données fictives (CC-48). */

const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { SCENE, phpAvailable, renderPhp, mainPart, equipmentsFor, FIXTURE, clone } = require('./page_b_harness');

const ROOT = path.join(__dirname, '..', '..', '..');
const gate = (...parts) => pathToFileURL(path.join(ROOT, 'tests', 'e2e', 'gate', ...parts)).href;
const JQUERY = [process.env.JEEDOM2HA_JQUERY, '/usr/share/javascript/jquery/jquery.min.js', '/usr/share/javascript/jquery/jquery.js']
  .filter(Boolean).find((file) => fs.existsSync(file));
const read = (file) => fs.readFileSync(path.join(ROOT, file), 'utf8');

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

const SCRIPTS = ['jeedom2ha_mapping_override', 'jeedom2ha_mapping_surface', 'jeedom2ha_action_budget', 'jeedom2ha_overview', 'jeedom2ha_workview', 'jeedom2ha'];

/** Corps d'un arbre unitaire pour `eqId` (le contrôleur exige que l'identifiant corresponde). */
function treeBody(eqId, source) {
  const tree = clone(FIXTURE[source || '101'].tree);
  tree.jeedom_eq_id = eqId;
  return { state: 'ok', result: { status: 'ok', payload: tree } };
}

/**
 * Arbre unitaire COHÉRENT avec l'entrée agrégée de l'équipement (même fixture de 25.2) : la parité d'état entre l'arbre
 * de la vue et le détail est alors observable (un arbre au hasard la fausserait).
 */
function unitTreeFor(equipments, eqId) {
  const entry = equipments[String(eqId)];
  if (!entry) return treeBody(eqId);
  const wanted = JSON.stringify(Object.assign({}, entry, { jeedom_eq_id: 0 }));
  const source = Object.keys(FIXTURE).find((id) => JSON.stringify(Object.assign({}, FIXTURE[id].aggregated, { jeedom_eq_id: 0 })) === wanted);
  return treeBody(eqId, source || '101');
}

/**
 * @param {object} t contexte node:test (pour `t.skip`)
 * @param {object} options { css (texte CSS de remplacement), width, height, hash, scene, equipments, delay (action, eqId) -> ms,
 *                           treeFor (eqId) -> corps, extraCss }
 * @param {Function} fn (page, ctx) => Promise
 */
async function withRealView(t, options, fn) {
  const opts = options || {};
  if (!phpAvailable || !JQUERY) { t.skip('PHP ou jQuery indisponible'); return; }
  let playwright;
  try {
    const { loadPlaywright } = await import(gate('lib', 'playwright.mjs'));
    playwright = loadPlaywright();
  } catch { t.skip('Playwright indisponible'); return; }
  const rendered = renderPhp(opts.scene || SCENE);
  const rooms = rendered.vars.j2haRoomsTree;
  const equipments = opts.equipments || equipmentsFor(rooms);
  const states = { state: 'ok', result: { status: 'ok', payload: { schema_version: 1, available: true, meta: { action_in_progress: false }, equipments, unread: [] } } };
  const browser = await playwright.chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: opts.width || 1280, height: opts.height || 800 } });
    const page = await context.newPage();
    const journal = [];
    const bodies = [];
    const errors = [];
    const css = (opts.css !== undefined ? opts.css : read('desktop/css/jeedom2ha.css')) + (opts.extraCss || '');
    // Les scripts sont SERVIS (balises <script src>) pour que `page.reload()` rejoue la page entière, lien profond compris.
    const scriptTags = ['/assets/jquery.js', '/assets/bootbox-stub.js', ...SCRIPTS.map((file) => `/assets/${file}.js`)]
      .map((src) => `<script src="${src}"></script>`).join('');
    const html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>'
      + css + '</style></head><body>' + mainPart(rendered.html).replace(/\{\{([^}]*)\}\}/g, '$1') + '<div id="div_alert"></div>'
      + `<script>window.j2haRoomsTree = ${JSON.stringify(rooms)}; window.j2haAncestors = ${JSON.stringify(rendered.vars.j2haAncestors)}; window.j2haPluginNames = ${JSON.stringify(rendered.vars.j2haPluginNames || {})};</script>`
      + scriptTags + '</body></html>';
    await page.route('http://gate.test/**', async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      if (url.pathname === '/') { await route.fulfill({ contentType: 'text/html', body: html }); return; }
      if (url.pathname === '/assets/jquery.js') { await route.fulfill({ contentType: 'application/javascript', body: read0(JQUERY) }); return; }
      if (url.pathname === '/assets/bootbox-stub.js') { await route.fulfill({ contentType: 'application/javascript', body: BOOTBOX_STUB }); return; }
      const script = /^\/assets\/([a-z0-9_]+)\.js$/.exec(url.pathname);
      if (script && SCRIPTS.includes(script[1])) {
        await route.fulfill({ contentType: 'application/javascript', body: read(`desktop/js/${script[1]}.js`).replace(/\{\{([^}]*)\}\}/g, '$1') });
        return;
      }
      if (url.pathname.endsWith('/jeedom2ha.ajax.php')) {
        const raw = request.postData() || '';
        const params = new URLSearchParams(raw);
        const action = params.get('action');
        const eqId = Number(params.get('eqId'));
        journal.push({ action, eqId: Number.isFinite(eqId) ? eqId : null, verdict: 'lecture', method: 'POST', resourceType: request.resourceType(), path: url.pathname, at: Date.now() });
        bodies.push(raw);
        let body = { state: 'error', result: 'écriture interdite en test' };
        if (action === 'getBridgeStatus') body = { state: 'ok', result: { daemon: true, broker: { state: 'connected' }, derniere_operation_resultat: 'aucun' } };
        else if (action === 'getEquipmentStates') body = states;
        else if (action === 'getMappingOverrides') body = opts.treeFor ? opts.treeFor(eqId) : unitTreeFor(equipments, eqId);
        const wait = opts.delay ? opts.delay(action, eqId) : 0;
        if (wait > 0) await new Promise((resolve) => setTimeout(resolve, wait));
        await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
        return;
      }
      await route.fulfill({ status: 404, body: '' });
    });
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto('http://gate.test/' + (opts.hash || ''));
    await page.waitForFunction(() => (document.querySelector('#j2ha_houseNumber')?.textContent ?? '').trim() !== '');
    await fn(page, { rendered, rooms, errors, journal, bodies, equipments, states, browser, context });
  } finally {
    await browser.close();
  }
}

function read0(file) { return fs.readFileSync(file, 'utf8'); }

module.exports = { withRealView, treeBody, phpAvailable, JQUERY, gate, read, SCRIPTS };
