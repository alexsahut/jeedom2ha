// ARTEFACT — Story 25.4, relecture R1 (PR #301) : P2-1 historique d'une vue ouverte depuis une puce ou un segment (AC17, AC18),
// P2-2 focus rendu au déclencheur (AC19), P3-1 « Appliquer » d'une ligne « À traiter » qui survit aux rendus, P3-2 corps
// d'écriture de ce clic = référence de main, P3-3 `window.j2haOpenRoom` défini dès le chargement du script.
// Vrai code sur faux DOM / faux navigateur ; identifiants fictifs (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { startWorkview, startBig, openCard, phpAvailable } = require('./helpers/workview_harness');
const { createUi, tree, ok, READY, BRIDGE_UP } = require('./helpers/ui_harness');
const { okBody } = require('./helpers/page_b_harness');
const { makeScene } = require('./helpers/big_scene');
const { ROOMS, WRITE_ACTIONS, serialize } = require('./helpers/write_scenarios');

const maybe = phpAvailable ? it : it.skip;
const root = path.join(__dirname, '..', '..');
const reference = JSON.parse(fs.readFileSync(path.join(root, 'tests/fixtures/story_25_4_corps_ecriture.json'), 'utf8'));
const CHIP = '#j2ha_houseChips .j2ha-chip-filter[data-filter="published"]';
const SEGMENT = '#j2ha_houseGauge .j2ha-seg-published';

describe('25.4 / R1 P2-1 — une vue ouverte depuis une puce ou un segment crée une entrée d’historique', () => {
  for (const [name, selector] of [['puce', CHIP], ['segment de jauge', SEGMENT]]) {
    maybe(`${name} → « Précédent » revient à la page principale, entrée de base sans fragment`, () => {
      const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
      assert.equal(ui.win.location.hash, '');
      ui.click(selector);
      assert.equal(ui.isOpen(), true);
      assert.equal(ui.win.location.hash, '#j2ha-vue=f:published');
      ui.win.history.back();
      assert.equal(ui.isOpen(), false, 'la page du plugin n’est pas quittée : on revient à la page principale');
      assert.equal(ui.win.location.hash, '', 'l’entrée de base n’a pas été réécrite');
    });
  }
});

describe('25.4 / R1 P2-2 — le focus revient au déclencheur', () => {
  maybe('le déclencheur est refocalisé au retour s’il est encore dans le document', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    const card = ui.$('#j2ha_roomCards .j2ha-room-card[data-object_id="10"]');
    card.focus();
    const before = card.list[0].focusCount;
    openCard(ui, 10);
    ui.click('.j2ha-wv-back');
    assert.equal(ui.dom.focused, card.list[0]);
    assert.equal(card.list[0].focusCount, before + 1, 'refocalisé au retour');
  });

  maybe('déclencheur disparu : le focus va à la carte de la pièce qui était ouverte', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    const ghost = ui.dom.add('<button class="ghost">x</button>');
    ghost.focus();
    openCard(ui, 10);
    ghost.remove();
    ui.click('.j2ha-wv-back');
    const card = ui.$('#j2ha_roomCards .j2ha-room-card[data-object_id="10"]').list[0];
    assert.equal(ui.dom.focused, card);
  });
});

describe('25.4 / R1 P3-1 — « Appliquer » d’une ligne « À traiter » survit aux rendus', () => {
  function openWithPending() {
    const big = makeScene({ rooms: 3, equipments: 30, seed: 8 });
    const ui = startWorkview({ scene: big.scene, equipments: big.equipments });
    const overview = ui.page.snapshot().view.overview;
    const room = overview.rooms.find((r) => r.equipments.some((e) => e.state === 'to_apply'));
    openCard(ui, room.object_id);
    const target = room.equipments.find((e) => e.state === 'to_apply').eq_id;
    const apply = `.j2ha-wv-todo-row[data-eq-id="${target}"] .j2ha-wv-todo-apply`;
    return { ui, target, apply, equipments: big.equipments };
  }

  maybe('relecture des états pendant l’appel : bouton toujours réservé, un seul envoi', () => {
    const { ui, apply } = openWithPending();
    ui.click(apply);
    assert.equal(ui.pending('executeHaAction').length, 1);
    ui.page.render();
    ui.page.render();
    assert.equal(ui.$(apply).length, 1);
    assert.equal(ui.$(apply).prop('disabled'), true, 'bouton réservé après le rendu suivant');
    assert.equal(ui.calls.filter((c) => c.action === 'executeHaAction').length, 1, 'un seul envoi');
  });

  maybe('resélection de la pièce pendant l’appel : toujours un seul envoi', () => {
    const { ui, apply } = openWithPending();
    ui.click(apply);
    ui.showRoom();
    assert.equal(ui.$(apply).prop('disabled'), true);
    assert.equal(ui.calls.filter((c) => c.action === 'executeHaAction').length, 1);
  });

  maybe('l’erreur d’un appel échoué reste lisible après la relecture des états qui suit l’échec', () => {
    const { ui, target, apply, equipments } = openWithPending();
    ui.click(apply);
    ui.fail('executeHaAction');
    ui.advance(500);
    ui.respond('getEquipmentStates', okBody(equipments));
    const error = ui.$(`.j2ha-wv-todo-row[data-eq-id="${target}"] .j2ha-publication-error`);
    assert.match(ui.$(error).text(), /Le démon ne répond pas/);
    assert.equal(ui.$(apply).prop('disabled') === true, false, 'bouton de nouveau actif après l’échec');
  });
});

describe('25.4 / R1 P3-2 — le clic « Appliquer » d’une ligne « À traiter » a le corps d’écriture de main', () => {
  it('même requête que le scénario `appliquer-equipement` de la référence', () => {
    const entity = { ha_entity_type: 'light', command_ids: [100], decision: READY, publication_override: null, override_command_id: 100, override_pending: true, present_in_ha: true };
    const ui = createUi(ROOMS);
    ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
    ui.openRoomWith(7, [ok(tree(1, [READY], { entities: [entity] }))], { select: null });
    const apply = ui.$('.j2ha-wv-todo-apply');
    assert.equal(apply.length, 1, 'une ligne « À appliquer »');
    ui.click('.j2ha-wv-todo-apply');
    const writes = ui.calls.filter((c) => WRITE_ACTIONS.includes(c.action)).map((c) => ({ action: c.action, body: serialize(c.data) }));
    assert.deepEqual(writes, reference.scenarios['appliquer-equipement']);
  });
});

describe('25.4 / R1 P3-3 — window.j2haOpenRoom dès le chargement du script', () => {
  it('défini avant le DOM prêt, sans effet (et sans erreur) tant qu’il n’y a pas d’instance', () => {
    const context = { console, setTimeout, clearTimeout, document: {} };
    context.window = context;
    context.$ = function () { /* le DOM n’est jamais « prêt » : aucune instance */ };
    vm.createContext(context);
    for (const file of ['jeedom2ha_mapping_override.js', 'jeedom2ha_overview.js', 'jeedom2ha_workview.js']) {
      vm.runInContext(fs.readFileSync(path.join(root, 'desktop/js', file), 'utf8'), context, { filename: file });
    }
    assert.equal(typeof context.window.j2haOpenRoom, 'function');
    assert.doesNotThrow(() => context.window.j2haOpenRoom(4));
  });
});
