// ARTEFACT — Story 25.6 (D2, AC5, Q3, Q4) : la portée dans le fragment d'URL (`seule:1`), successeur de test_story_25_4_etat_url.
// Encodage déterministe (piece, eq, f, seule), entrées hostiles, historique à état `null` (cohabitation avec le popstate du
// cœur, #302), « Précédent » / « Suivant » dans la portée de l'entrée restaurée, lien profond. Données fictives (CC-48).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const W = require('../../desktop/js/jeedom2ha_workview.js');
const { startBig, openCard, phpAvailable } = require('./helpers/workview_harness');
const { tree, ok, READY } = require('./helpers/ui_harness');

const maybe = phpAvailable ? it : it.skip;
const scope = (ui) => ui.$('#j2ha_workView').attr('data-j2ha-scope');
const roomIds = (ui) => ui.$('.j2ha-wv-tree .j2ha-wv-room').list.map((n) => n.attrs['data-object_id']);

describe('25.6 / D2 — encodage du fragment', () => {
  it('ordre déterministe piece, eq, f, seule ; aller-retour ; les fragments de 25.4 restent valides (toutes)', () => {
    assert.equal(W.formatFragment({ piece: 4, eq: null, filter: null, seule: true }), '#j2ha-vue=piece:4;seule:1');
    assert.equal(W.formatFragment({ piece: 4, eq: 12, filter: null, seule: true }), '#j2ha-vue=piece:4;eq:12;seule:1');
    assert.equal(W.formatFragment({ piece: 4, eq: 12, filter: 'blocked', seule: true }), '#j2ha-vue=piece:4;eq:12;f:blocked;seule:1');
    assert.equal(W.formatFragment({ piece: 0, eq: null, filter: null, seule: true }), '#j2ha-vue=piece:0;seule:1');
    assert.equal(W.formatFragment({ piece: 4, eq: 12, filter: 'blocked' }), '#j2ha-vue=piece:4;eq:12;f:blocked');
    assert.equal(W.formatFragment({ piece: null, eq: null, filter: null, seule: true }), '', 'seule sans piece n’est jamais écrit');
    assert.equal(W.parseFragment('#j2ha-vue=piece:4;seule:1').seule, true);
    assert.equal(W.parseFragment('#j2ha-vue=seule:1;piece:4;f:blocked').seule, true, 'l’ordre de lecture est libre');
    assert.deepEqual(W.parseFragment('#j2ha-vue=piece:4;eq:12;f:blocked'), { piece: 4, eq: 12, filter: 'blocked' });
    const hash = '#j2ha-vue=piece:4;eq:12;f:blocked;seule:1';
    assert.equal(W.formatFragment(W.parseFragment(hash)), hash);
  });

  it('entrées hostiles : seule:0, seule:oui, seule:1 sans piece, seule en double → ignorées sans erreur', () => {
    for (const input of ['#j2ha-vue=piece:4;seule:0', '#j2ha-vue=piece:4;seule:oui', '#j2ha-vue=piece:4;seule:2', '#j2ha-vue=piece:4;seule:',
      '#j2ha-vue=seule:1', '#j2ha-vue=f:blocked;seule:1', '#j2ha-vue=piece:4;seule:1;seule:1', '#j2ha-vue=piece:4;seule:1;x:1', '#j2ha-vue=piece:4;seule:true']) {
      let parsed;
      assert.doesNotThrow(() => { parsed = W.parseFragment(input); }, input);
      assert.equal(parsed, null, input);
    }
  });

  it('resolveFragment : seule:1 avec une pièce inconnue → null ; avec une pièce connue, la portée est conservée', () => {
    const rooms = [{ object_id: 4, object_name: 'A', equipments: [{ eq_id: 12, eq_name: 'x', enabled: true }] }];
    assert.equal(W.resolveFragment({ piece: 9, eq: null, filter: null, seule: true }, rooms), null);
    assert.deepEqual(W.resolveFragment({ piece: 4, eq: 12, filter: null, seule: true }, rooms), { piece: 4, eq: 12, filter: null, seule: true });
    assert.deepEqual(W.resolveFragment({ piece: 4, eq: null, filter: null }, rooms), { piece: 4, eq: null, filter: null });
  });
});

describe('25.6 / AC5 — historique, « Précédent » / « Suivant », état `null`', () => {
  maybe('carte → équipement → élargir : fragments, remplacement, état d’historique null', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6 });
    openCard(ui, 10);
    assert.equal(ui.win.location.hash, '#j2ha-vue=piece:10;seule:1');
    assert.equal(ui.win.history.state, null);
    const eq = Number(ui.$('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.selectEquipment(eq, ok(tree(eq, [READY])));
    assert.equal(ui.win.location.hash, `#j2ha-vue=piece:10;eq:${eq};seule:1`);
    assert.equal(ui.win.history.state, null);
    const pushes = ui.win.historyWrites.push;
    const depth = ui.win.historyIndex();
    ui.click('.j2ha-wv-widen');
    assert.equal(ui.win.location.hash, `#j2ha-vue=piece:10;eq:${eq}`, 'même fragment sans seule');
    assert.equal(ui.win.historyWrites.push, pushes, 'remplacement, pas de nouvelle entrée');
    assert.equal(ui.win.historyIndex(), depth);
    assert.equal(ui.win.history.state, null);
  });

  maybe('« Précédent » depuis l’équipement revient à la pièce dans la portée de l’entrée restaurée, puis à la page principale ; « Suivant » rejoue', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6 });
    let loads = 0;
    ui.win.addEventListener('popstate', (event) => { if (event.state !== null) loads += 1; });
    openCard(ui, 10);
    const eq = Number(ui.$('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.selectEquipment(eq, ok(tree(eq, [READY])));
    ui.click('.j2ha-wv-widen');
    assert.equal(scope(ui), 'toutes');
    ui.win.history.back();
    assert.equal(ui.isOpen(), true);
    assert.equal(ui.$('.j2ha-eq-panel').length, 0, 'retour à la pièce');
    assert.equal(scope(ui), 'piece', 'portée de l’entrée restaurée');
    assert.deepEqual(roomIds(ui), ['10']);
    ui.win.history.forward();
    assert.equal(ui.$('.j2ha-eq-panel').length, 1, 'Suivant rejoue l’équipement');
    assert.equal(scope(ui), 'toutes', 'avec la portée de l’entrée remplacée');
    ui.win.history.back();
    ui.win.history.back();
    assert.equal(ui.isOpen(), false);
    assert.equal(ui.win.location.hash, '');
    assert.equal(loads, 0, 'le cœur ne recharge jamais la page (aucun jeedomUtils.loadPage)');
  });

  maybe('élargir sans équipement : « Précédent » ramène à la page principale (profondeur de 25.4 conservée)', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6 });
    openCard(ui, 10);
    ui.click('.j2ha-wv-widen');
    assert.equal(ui.win.location.hash, '#j2ha-vue=piece:10');
    ui.win.history.back();
    assert.equal(ui.isOpen(), false);
  });

  maybe('filtre en portée pièce : remplace l’entrée et garde seule:1', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6 });
    openCard(ui, 10);
    const pushes = ui.win.historyWrites.push;
    ui.click('.j2ha-wv-chips .j2ha-chip-filter[data-filter="published"]');
    assert.equal(ui.win.location.hash, '#j2ha-vue=piece:10;f:published;seule:1');
    assert.equal(ui.win.historyWrites.push, pushes);
    assert.equal(ui.win.history.state, null);
  });
});

describe('25.6 / AC5 — lien profond', () => {
  maybe('piece:P;seule:1 rouvre en portée pièce : un getEquipmentStates, zéro arbre ; avec un équipement : un arbre', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6, window: { hash: '#j2ha-vue=piece:10;seule:1' } });
    assert.equal(ui.isOpen(), true);
    assert.equal(scope(ui), 'piece');
    assert.deepEqual(roomIds(ui), ['10']);
    assert.deepEqual(ui.reads(), { states: 1, trees: 0 });
    const eq = 1000;
    const deep = startBig({ rooms: 3, equipments: 30, seed: 6, window: { hash: `#j2ha-vue=piece:10;eq:${eq};seule:1` } });
    assert.equal(scope(deep), 'piece');
    assert.deepEqual(deep.reads(), { states: 1, trees: 1 });
    assert.equal(deep.$(`.j2ha-wv-eq[data-eq-id="${eq}"]`).attr('aria-selected'), 'true');
  });

  maybe('un fragment de 25.4 (sans seule) rouvre en portée toutes', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6, window: { hash: '#j2ha-vue=piece:10' } });
    assert.equal(scope(ui), 'toutes');
    assert.equal(roomIds(ui).length, 3);
  });

  maybe('entrées hostiles et pièce inconnue : fragment ignoré, page principale, aucune erreur', () => {
    for (const hash of ['#j2ha-vue=piece:10;seule:0', '#j2ha-vue=piece:10;seule:oui', '#j2ha-vue=seule:1', '#j2ha-vue=piece:10;seule:1;seule:1', '#j2ha-vue=piece:9999;seule:1']) {
      let ui;
      assert.doesNotThrow(() => { ui = startBig({ rooms: 3, equipments: 30, seed: 6, window: { hash } }); }, hash);
      assert.equal(ui.isOpen(), false, hash);
      assert.deepEqual(ui.reads(), { states: 1, trees: 0 }, hash);
    }
  });
});

describe('25.6 / AC5 — cohabitation avec le popstate du cœur (#302), nouvelles entrées', () => {
  maybe('aucune entrée poussée ou remplacée (ouvrir, sélectionner, filtrer, élargir) n’a d’état non null', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6 });
    const states = [];
    for (const method of ['pushState', 'replaceState']) {
      const original = ui.win.history[method];
      ui.win.history[method] = (state, ...rest) => { states.push(state); return original.call(ui.win.history, state, ...rest); };
    }
    openCard(ui, 10);
    const eq = Number(ui.$('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.selectEquipment(eq, ok(tree(eq, [READY])));
    ui.click('.j2ha-wv-chips .j2ha-chip-filter[data-filter="published"]');
    ui.click('.j2ha-wv-widen');
    assert.ok(states.length >= 4);
    assert.ok(states.every((state) => state === null), 'tous les états valent null');
  });
});
