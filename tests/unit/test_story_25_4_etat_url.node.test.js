// ARTEFACT — Story 25.4 (AC7, AC17, AC18, Q1) : l'état « vue C, pièce, équipement, filtre » dans le fragment d'URL
// (`#j2ha-vue=piece:P;eq:E;f:F`) — encodage, validation hostile, historique (« Précédent » remonte d'un niveau),
// lien profond (un getEquipmentStates et au plus un getMappingOverrides), repli sessionStorage si le fragment est
// inutilisable. Vrai code sur faux DOM et faux navigateur ; identifiants fictifs (CC-48).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const W = require('../../desktop/js/jeedom2ha_workview.js');
const { startWorkview, startBig, openCard, phpAvailable } = require('./helpers/workview_harness');
const { tree, ok, READY } = require('./helpers/ui_harness');

const maybe = phpAvailable ? it : it.skip;

describe('25.4 / AC18 — encodage et lecture du fragment', () => {
  it('formatFragment / parseFragment : aller-retour, préfixe obligatoire', () => {
    assert.equal(W.formatFragment({ piece: 4, eq: 12, filter: 'blocked' }), '#j2ha-vue=piece:4;eq:12;f:blocked');
    assert.equal(W.formatFragment({ piece: 0, eq: null, filter: null }), '#j2ha-vue=piece:0');
    assert.equal(W.formatFragment({ piece: null, eq: null, filter: 'blocked' }), '#j2ha-vue=f:blocked');
    assert.deepEqual(W.parseFragment('#j2ha-vue=piece:4;eq:12;f:blocked'), { piece: 4, eq: 12, filter: 'blocked' });
    assert.deepEqual(W.parseFragment('#j2ha-vue=piece:0'), { piece: 0, eq: null, filter: null });
    assert.deepEqual(W.parseFragment('#j2ha-vue=f:to_apply'), { piece: null, eq: null, filter: 'to_apply' });
    assert.equal(W.parseFragment('#autre=piece:4'), null, 'jamais un fragment qui ne serait pas au plugin');
    assert.equal(W.parseFragment(''), null);
  });

  it('entrées hostiles : ignorées sans erreur (null)', () => {
    const hostile = [
      '#j2ha-vue=piece:abc', '#j2ha-vue=piece:-1', '#j2ha-vue=piece:1.5', '#j2ha-vue=piece:1e3', '#j2ha-vue=piece:99999999999999999999',
      '#j2ha-vue=piece:4;eq:abc', '#j2ha-vue=piece:4;eq:0', '#j2ha-vue=eq:12', '#j2ha-vue=piece:4;f:inconnu', '#j2ha-vue=piece:4;f:',
      '#j2ha-vue=piece:4;eq:12;eq:13', '#j2ha-vue=piece:4;x:1', '#j2ha-vue=<script>alert(1)</script>', '#j2ha-vue=piece:4;;;', '#j2ha-vue=',
      '#j2ha-vue=piece:4%3Beq:12', '#j2ha-vue=piece:4;eq:12;f:blocked;f:blocked', null, undefined, 42, {},
    ];
    for (const input of hostile) {
      let parsed;
      assert.doesNotThrow(() => { parsed = W.parseFragment(input); }, String(input));
      assert.equal(parsed, null, String(input));
    }
  });

  it('resolveFragment : pièce inconnue ou équipement d’une autre pièce → null (page principale)', () => {
    const rooms = [
      { object_id: 4, object_name: 'A', equipments: [{ eq_id: 12, eq_name: 'x', enabled: true }] },
      { object_id: 5, object_name: 'B', equipments: [{ eq_id: 13, eq_name: 'y', enabled: true }] },
    ];
    assert.deepEqual(W.resolveFragment({ piece: 4, eq: 12, filter: 'blocked' }, rooms), { piece: 4, eq: 12, filter: 'blocked' });
    assert.deepEqual(W.resolveFragment({ piece: null, eq: null, filter: 'blocked' }, rooms), { piece: null, eq: null, filter: 'blocked' });
    assert.equal(W.resolveFragment({ piece: 9, eq: null, filter: null }, rooms), null);
    assert.equal(W.resolveFragment({ piece: 4, eq: 13, filter: null }, rooms), null, 'équipement d’une autre pièce');
    assert.equal(W.resolveFragment({ piece: 4, eq: 99, filter: null }, rooms), null);
    assert.equal(W.resolveFragment(null, rooms), null);
  });
});

describe('25.4 / AC18, AC17 — historique et « Précédent »', () => {
  maybe('carte → équipement : l’URL suit ; « Précédent » remonte équipement → pièce → page principale', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6 });
    const before = ui.calls.length;
    openCard(ui, 10);
    assert.equal(ui.win.location.hash, '#j2ha-vue=piece:10');
    const eq = Number(ui.$('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.selectEquipment(eq, ok(tree(eq, [READY])));
    assert.equal(ui.win.location.hash, `#j2ha-vue=piece:10;eq:${eq}`);
    ui.win.history.back();
    assert.equal(ui.isOpen(), true);
    assert.equal(ui.$('.j2ha-eq-panel').length, 0, 'retour à la sélection de la pièce');
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="10"]').attr('aria-selected'), 'true');
    ui.win.history.back();
    assert.equal(ui.isOpen(), false, 'retour à la page principale');
    assert.equal(ui.win.location.hash, '');
    assert.equal(ui.calls.length - before, 1, 'aucune requête de navigation (seulement la lecture de l’arbre sélectionné)');
  });

  maybe('« Toutes les pièces » revient sur l’entrée précédant l’ouverture ; sans historique (lien profond) : fragment retiré sur place', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6 });
    openCard(ui, 10);
    ui.click('.j2ha-wv-room[data-object_id="11"] .j2ha-wv-row');
    ui.click('.j2ha-wv-back');
    assert.equal(ui.isOpen(), false);
    assert.equal(ui.win.location.hash, '');
    assert.equal(ui.win.historyIndex(), 0, 'on est revenu à l’entrée initiale, sans quitter la page');

    const deep = startBig({ rooms: 3, equipments: 30, seed: 6, window: { hash: '#j2ha-vue=piece:10' } });
    assert.equal(deep.isOpen(), true);
    deep.click('.j2ha-wv-back');
    assert.equal(deep.isOpen(), false);
    assert.equal(deep.win.location.hash, '');
    assert.equal(deep.win.historyIndex(), 0, 'jamais de history.back() hors du plugin');
  });

  maybe('filtre : remplace l’entrée courante (pas de niveau de plus) ; la recherche n’est pas mémorisée', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6 });
    openCard(ui, 10);
    const pushes = ui.win.historyWrites.push;
    ui.click('.j2ha-wv-chips .j2ha-chip-filter[data-filter="published"]');
    assert.equal(ui.win.location.hash, '#j2ha-vue=piece:10;f:published');
    assert.equal(ui.win.historyWrites.push, pushes);
    const input = ui.$('.j2ha-wv-search').list[0];
    input.props.value = 'eq';
    input.handlers.input.call(input, { target: input });
    ui.advance(400);
    assert.ok(!/eq|search|q:/.test(ui.win.location.hash.replace('#j2ha-vue=', '')));
  });

  maybe('la mise à jour de l’URL ne déclenche ni rechargement ni requête', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6 });
    const before = ui.calls.length;
    openCard(ui, 10);
    ui.click('.j2ha-wv-room[data-object_id="11"] .j2ha-wv-row');
    ui.click('.j2ha-wv-chips .j2ha-chip-filter[data-filter="published"]');
    assert.equal(ui.calls.length, before);
  });
});

describe('25.4 / AC7 — lien profond', () => {
  maybe('pièce + équipement : un getEquipmentStates et un getMappingOverrides', () => {
    const eq = 1000; // premier équipement de la pièce 10 dans les scènes générées
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6, window: { hash: `#j2ha-vue=piece:10;eq:${eq}` } });
    assert.deepEqual(ui.reads(), { states: 1, trees: 1 });
    assert.equal(ui.pending('getMappingOverrides')[0].data.eqId, eq);
    assert.equal(ui.pending('getEquipmentStates').length, 0);
    assert.equal(ui.$(`.j2ha-wv-eq[data-eq-id="${eq}"]`).attr('aria-selected'), 'true');
  });

  maybe('pièce seule ou aucun état d’URL : zéro lecture d’arbre ; le chargement par défaut est inchangé', () => {
    assert.deepEqual(startBig({ rooms: 3, equipments: 30, seed: 6, window: { hash: '#j2ha-vue=piece:10' } }).reads(), { states: 1, trees: 0 });
    assert.deepEqual(startBig({ rooms: 3, equipments: 30, seed: 6 }).reads(), { states: 1, trees: 0 });
    const filtered = startBig({ rooms: 3, equipments: 30, seed: 6, window: { hash: '#j2ha-vue=f:blocked' } });
    assert.equal(filtered.isOpen(), true);
    assert.equal(filtered.page.filter(), 'blocked');
    assert.deepEqual(filtered.reads(), { states: 1, trees: 0 });
  });

  maybe('état d’URL invalide : ignoré sans erreur, page principale ouverte', () => {
    for (const hash of ['#j2ha-vue=piece:9999', '#j2ha-vue=piece:10;eq:1', '#j2ha-vue=piece:x', '#j2ha-vue=<img onerror=1>', '#autre']) {
      const ui = startBig({ rooms: 3, equipments: 30, seed: 6, window: { hash } });
      assert.equal(ui.isOpen(), false, hash);
      assert.deepEqual(ui.reads(), { states: 1, trees: 0 }, hash);
    }
  });
});

describe('25.4 / Q1 — repli sessionStorage si le fragment est inutilisable', () => {
  maybe('pushState qui lève : la sélection est conservée dans sessionStorage et « Précédent » reste géré par history.state', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6 });
    // Un cœur qui intercepte / interdit le fragment : toute écriture d'historique échoue.
    ui.win.history.pushState = () => { throw new Error('interdit'); };
    ui.win.history.replaceState = () => { throw new Error('interdit'); };
    assert.doesNotThrow(() => openCard(ui, 10));
    assert.equal(ui.isOpen(), true);
    assert.match(ui.win.sessionStorage.getItem('j2ha-vue') || '', /"piece":10/);
    ui.click('.j2ha-wv-back');
    assert.equal(ui.isOpen(), false);
  });
});

// Correctif du 2026-10-19 (gate 20-0 sur la box, parcours vue-maitre-detail-c, étape 8 « precedent-ne-remonte-pas ») :
// le cœur Jeedom (desktop/common/js/utils.js, 4.4 à 4.6) écoute `popstate` et recharge la page par
// `jeedomUtils.loadPage(index.php?…)` dès que `event.state !== null`. Les entrées de la vue portent donc un état `null`,
// et la profondeur est tenue par la vue elle-même.
describe('25.4 / AC18 — cohabitation avec le popstate du cœur Jeedom', () => {
  function coreListener(win) {
    const loads = [];
    win.addEventListener('popstate', (event) => { if (event.state !== null) loads.push(win.location.hash); });
    return loads;
  }

  maybe('aucune entrée d’historique de la vue ne déclenche le rechargement du cœur ; « Précédent » remonte toujours', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6 });
    const loads = coreListener(ui.win);
    openCard(ui, 10);
    assert.equal(ui.win.history.state, null);
    const eq = Number(ui.$('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.selectEquipment(eq, ok(tree(eq, [READY])));
    assert.equal(ui.win.history.state, null);
    ui.click('.j2ha-wv-chips .j2ha-chip-filter[data-filter="published"]');
    assert.equal(ui.win.history.state, null, 'replaceState aussi');
    ui.win.history.back();
    assert.equal(ui.isOpen(), true);
    assert.equal(ui.$('.j2ha-eq-panel').length, 0, 'retour à la pièce');
    ui.win.history.forward();
    assert.equal(ui.$('.j2ha-eq-panel').length, 1, 'en avant : de nouveau l’équipement');
    ui.win.history.back();
    ui.win.history.back();
    assert.equal(ui.isOpen(), false, 'retour à la page principale');
    assert.deepEqual(loads, [], 'le cœur ne recharge jamais la page');
  });
});
