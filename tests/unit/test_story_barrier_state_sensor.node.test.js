// ARTEFACT — story/barrier-state-sensor : la commande d'état d'un portail / d'une porte motorisée est lue par la cover
// ET par son capteur compagnon « État » (`reason_details.barrier_companion_of`). Le compagnon suit la cover et ne
// compte pas comme une seconde entité : « Corriger le type » reste ouvrable sur la ligne d'état, comme avant la story
// (l'override vise la cover). Une vraie commande partagée par deux entités garde le réglage grisé. Exécute le VRAI code
// de l'interface ; identifiants génériques uniquement (CC-48).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const { createUi, tree, ok, READY, BRIDGE_UP } = require('./helpers/ui_harness');

const ROOM = { object_id: 7, object_name: 'Zone', equipments: [
  { eq_id: 1, eq_name: 'Eq 1', enabled: true },
  { eq_id: 2, eq_name: 'Eq 2', enabled: true },
] };

function openRoomWith(trees) {
  const ui = createUi([ROOM]);
  ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
  const bodies = {};
  const entries = {};
  trees.forEach((body) => { const p = body.result.payload; bodies[p.jeedom_eq_id] = body; entries[String(p.jeedom_eq_id)] = p; });
  ui.loadStates(entries);
  ui.openRoom(7);
  if (!ui.$('.j2ha-wv-eq[data-eq-id="1"] .j2ha-wv-row').length) ui.click('.j2ha-wv-room[data-object_id="7"] .j2ha-wv-row');
  ui.selectEquipment(1, bodies[1]);
  return ui;
}

const entity = (type, ids, extra) => Object.assign({
  ha_entity_type: type, command_ids: ids, decision: READY, publication_override: null,
  override_command_id: ids[0], override_pending: false, present_in_ha: true,
}, extra || {});

// Forme d'une porte motorisée : bascule 101, état numérique 102 ; le compagnon « État » lit 102.
const COVER = entity('cover', [101, 102], { reason_details: { barrier_mode: 'toggle_on_state', barrier_state: 'GARAGE_STATE' } });
const COMPANION = entity('sensor', [102], {
  override_command_id: null,
  reason_details: { cmd_id: 102, device_class: 'enum', barrier_companion_of: 'jeedom2ha_eq_1' },
});
const STATE_ROW = { jeedom_cmd_id: 102, cmd_name: 'Etat', covered: true, diagnostic: READY, published_in_ha: true };
const TOGGLE_ROW = { jeedom_cmd_id: 101, cmd_name: 'Bascule', covered: true, diagnostic: READY, published_in_ha: true };

function barrierTree(entities) {
  const t = tree(1, [READY, READY], { entities });
  t.commands = [TOGGLE_ROW, STATE_ROW];
  return t;
}

const typeLink = (ui, cmdId) => ui.$(`.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="${cmdId}"] .j2ha-type-link`);

describe('story/barrier-state-sensor — « Corriger le type » sur l’état d’un portail / d’une porte motorisée', () => {
  it('pur : le compagnon « État » ne compte pas ; la ligne d’état reste réglable, comme avant la story', () => {
    assert.equal(M.countEntitiesCarryingCommand([COVER, COMPANION], 102), 1);
    assert.deepEqual(M.getOverrideSelectorState(STATE_ROW, [COVER, COMPANION]), M.getOverrideSelectorState(STATE_ROW, [COVER]));
    assert.deepEqual(M.getOverrideSelectorState(STATE_ROW, [COVER, COMPANION]), { active: true, reason: null });
  });

  it('pur : une vraie commande partagée par deux entités principales reste grisée', () => {
    const shared = [entity('switch', [102]), entity('binary_sensor', [102])];
    assert.equal(M.countEntitiesCarryingCommand(shared, 102), 2);
    const state = M.getOverrideSelectorState(STATE_ROW, shared);
    assert.equal(state.active, false);
    assert.match(state.reason, /portée par plusieurs entités/);
    // Un compagnon de plus ne lève pas le grisage d'une commande réellement partagée.
    assert.equal(M.getOverrideSelectorState(STATE_ROW, [...shared, COMPANION]).active, false);
  });

  it('interface : lien « Corriger le type » actif sur la ligne d’état, panneau ouvrable', () => {
    const ui = openRoomWith([ok(barrierTree([COVER, COMPANION])), ok(tree(2, [READY]))]);
    const link = typeLink(ui, 102);
    assert.equal(link.length, 1);
    assert.ok(!link.hasClass('j2ha-type-unavailable'));
    assert.notEqual(link.attr('aria-disabled'), 'true');
    assert.doesNotMatch(String(link.attr('title') || ''), /plusieurs entités/);
    ui.click('.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="102"] .j2ha-type-link');
    assert.equal(ui.$('.j2ha-v3-type-modal[data-eq-id="1"][data-type-panel-for="102"] .j2ha-v2-type-panel').length, 1);
  });

  it('interface : même rendu de la ligne d’état qu’avec la cover seule (comportement de main)', () => {
    const withCompanion = openRoomWith([ok(barrierTree([COVER, COMPANION])), ok(tree(2, [READY]))]);
    const coverOnly = openRoomWith([ok(barrierTree([COVER])), ok(tree(2, [READY]))]);
    for (const attr of ['class', 'aria-disabled', 'title']) {
      assert.equal(typeLink(withCompanion, 102).attr(attr), typeLink(coverOnly, 102).attr(attr), attr);
    }
  });

  it('interface : une vraie commande partagée par deux entités garde le lien grisé', () => {
    const t = barrierTree([entity('switch', [102]), entity('binary_sensor', [102])]);
    const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
    const link = typeLink(ui, 102);
    assert.ok(link.hasClass('j2ha-type-unavailable'));
    assert.equal(link.attr('aria-disabled'), 'true');
  });
});
