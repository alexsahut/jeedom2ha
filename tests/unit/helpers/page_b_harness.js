'use strict';

/* Aide de test (Story 25.3) : rend le VRAI squelette PHP de la page principale (faux cœur Jeedom, voir render_page.php),
 * le charge dans le faux DOM et démarre le VRAI jeedom2ha_overview.js. Données fictives (CC-48). */

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const assert = require('node:assert/strict');
const { createDom } = require('./fake_dom');
const O = require('../../../desktop/js/jeedom2ha_overview.js');

const FIXTURE = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'fixtures', 'story_25_2_parite_etat.json'), 'utf8'));
const plain = (text) => String(text).replace(/\{\{|\}\}/g, '');
const clone = (value) => JSON.parse(JSON.stringify(value));

let phpAvailable = true;
try { execFileSync('php', ['-v'], { stdio: 'ignore' }); } catch { phpAvailable = false; }

/** Pièces fictives : maison > étage > deux salles ; une salle isolée ; des équipements sans objet. */
const SCENE = {
  objects: [
    { id: 1, name: 'Maison fictive', father_id: null, display: {} },
    { id: 2, name: 'Étage fictif', father_id: 1, display: { icon: '<i class="fas fa-bed"></i>', tagColor: '#ff8800' } },
    { id: 3, name: 'Salle A', father_id: 2, display: { icon: '<i class="icon jeedom-maison"></i>' } },
    { id: 4, name: 'Salle B <i>fictive</i>', father_id: 2, display: { icon: '<i class="fas fa-couch"></i>', tagColor: '#123' } },
    { id: 5, name: 'Isolée', father_id: null, display: {} },
  ],
  eqlogics: {
    2: [{ id: 101, name: 'Eq 101' }],
    3: [{ id: 102, name: 'Eq 102' }, { id: 103, name: 'Eq 103' }, { id: 104, name: 'Eq 104', enabled: false }],
    4: [{ id: 105, name: 'Eq 105' }, { id: 106, name: 'Eq <b>106</b>' }, { id: 998, name: 'Eq 998' }],
    5: [{ id: 107, name: 'Eq 107' }, { id: 108, name: 'Eq 108' }, { id: 109, name: 'Eq 109' }, { id: 110, name: 'Eq 110' }],
    null: [{ id: 111, name: 'Eq sans objet' }],
  },
  doc: 'https://doc.example.test/plugin',
};

function renderPhp(scene) {
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'j2ha-')), 'scene.json');
  fs.writeFileSync(file, JSON.stringify(scene));
  const out = execFileSync('php', [path.join(__dirname, 'render_page.php'), file], { encoding: 'utf8', maxBuffer: 1 << 24 });
  return JSON.parse(out);
}

/** Partie `eqLogicThumbnailDisplay` du rendu, sans commentaires : ce que voit l'utilisateur sur la page B. */
function mainPart(html) {
  const start = html.indexOf('<div class="col-xs-12 eqLogicThumbnailDisplay">');
  const end = html.indexOf('<!-- /.eqLogicThumbnailDisplay -->');
  return html.slice(start, end).replace(/<!--[\s\S]*?-->/g, '').replace(/<\?php[\s\S]*?\?>/g, '');
}

function equipmentsFor(rooms) {
  const out = {};
  const ids = Object.keys(FIXTURE);
  let i = 0;
  rooms.forEach((room) => room.equipments.forEach((e) => {
    if (e.eq_id === 998) return; // « non lu »
    const entry = clone(FIXTURE[ids[i % ids.length]].aggregated);
    entry.jeedom_eq_id = e.eq_id;
    out[String(e.eq_id)] = entry;
    i += 1;
  }));
  return out;
}

const okBody = (equipments, meta) => ({
  state: 'ok',
  result: { status: 'ok', payload: { schema_version: 1, available: true, meta: Object.assign({ action_in_progress: false }, meta || {}), equipments, unread: [] } },
});

function startPage(options) {
  const opts = options || {};
  const rendered = renderPhp(opts.scene || SCENE);
  const rooms = rendered.vars.j2haRoomsTree;
  const dom = createDom();
  const calls = [];
  dom.$.ajax = (o) => { calls.push({ options: o, data: o.data || {}, action: (o.data || {}).action, settled: false }); };
  dom.add(mainPart(rendered.html));
  let now = 5_000_000;
  const timers = [];
  const opened = [];
  const page = O.createPage({
    $: dom.$, document: dom.document, bootbox: dom.bootbox, rooms,
    readStates: O.ajaxFetch(dom.$),
    now: () => now,
    setTimeout: (fn, ms) => { timers.push({ fn, ms }); return timers.length; },
    clearTimeout: () => {},
    openRoom: (id) => opened.push(id),
  });
  page.init();
  const ui = {
    dom, calls, rooms, rendered, page, opened, timers,
    $: dom.$,
    answer(body) {
      const call = calls.find((c) => !c.settled);
      assert.ok(call, 'aucun appel en attente');
      call.settled = true;
      if (body === null) call.options.error(); else call.options.success(body);
      return call;
    },
    text: (selector) => plain(dom.$(selector).text()),
    click: (selector) => { const el = dom.$(selector).first(); assert.ok(el.length, selector); el.list[0].handlers.click.call(el.list[0], { preventDefault() {}, stopPropagation() {} }); },
    key: (selector, key) => { const el = dom.$(selector).first(); assert.ok(el.length, selector); el.list[0].handlers.keydown.call(el.list[0], { key, target: el.list[0], preventDefault() {}, stopPropagation() {} }); },
  };
  if (opts.answer !== false) ui.answer(okBody(equipmentsFor(rooms)));
  return ui;
}


module.exports = { SCENE, FIXTURE, plain, clone, phpAvailable, renderPhp, mainPart, equipmentsFor, okBody, startPage };
