// ARTEFACT — Story 25.3 (AC6, Q7) : chaque fin d'action de la page (succès OU échec) signale à la page B qu'une
// relecture (sans refresh, coalescée) est due. Exécute le VRAI code de jeedom2ha.js et de la surface sur le faux DOM
// (harnais 25.1) ; seul `window.j2haNotifyStatesChanged` est espionné. Données fictives (CC-48).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { createUi, tree, ok, READY, BRIDGE_UP } = require('./helpers/ui_harness');

const ROOM = { object_id: 7, object_name: 'Pièce fictive', equipments: [{ eq_id: 1, eq_name: 'Eq 1', enabled: true }, { eq_id: 2, eq_name: 'Eq 2', enabled: true }] };
const ACTION_OK = { state: 'ok', result: { payload: { resultat: 'succes', message: 'Fait.', perimetre_impacte: { nom: 'Périmètre X' } } } };

function ui25() {
  const ui = createUi([ROOM]);
  let notified = 0;
  ui.sandbox.window.j2haNotifyStatesChanged = () => { notified += 1; };
  ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
  ui.bridgeUp();
  return { ui, count: () => notified };
}

describe('25.3 / AC6 — fins d’action → relecture des chiffres', () => {
  it('« Republier tout » : succès → un signal', () => {
    const { ui, count } = ui25();
    ui.click('.j2ha-ha-action[data-ha-action="republier"]');
    ui.lastConfirmation().options.buttons.confirm.callback();
    assert.equal(count(), 0, 'rien avant la fin de l’action');
    ui.respond('executeHaAction', ACTION_OK);
    assert.equal(count(), 1);
  });

  it('« Republier tout » : un échec réseau signale aussi (un échec peut avoir changé l’état)', () => {
    const { ui, count } = ui25();
    ui.click('.j2ha-ha-action[data-ha-action="republier"]');
    ui.lastConfirmation().options.buttons.confirm.callback();
    ui.fail('executeHaAction');
    assert.equal(count(), 1);
  });

  it('« Supprimer tout de Home Assistant » : fin d’action → un signal', () => {
    const { ui, count } = ui25();
    ui.click('.j2ha-ha-action[data-ha-action="supprimer-recreer"]');
    ui.lastConfirmation().options.buttons.confirm.callback();
    ui.respond('executeHaAction', ACTION_OK);
    assert.equal(count(), 1);
  });

  it('annuler la confirmation ne signale rien', () => {
    const { ui, count } = ui25();
    ui.click('.j2ha-ha-action[data-ha-action="supprimer-recreer"]');
    ui.lastConfirmation().options.buttons.cancel.callback();
    assert.equal(count(), 0);
  });

  it('« Relire Jeedom » : fin de synchro (succès) → un signal ; échec réseau → un signal', () => {
    for (const settle of [() => 'ok', () => 'fail']) {
      const { ui, count } = ui25();
      ui.click('#bt_rescanTopology');
      ui.lastConfirmation().options.buttons.confirm.callback();
      assert.equal(count(), 0);
      if (settle() === 'ok') ui.respond('scanTopology', { state: 'ok', result: { status: 'ok', operation_result: 'succes' } });
      else ui.fail('scanTopology');
      assert.equal(count(), 1);
    }
  });

  it('vue de travail : « Republier » d’un équipement (succès, puis échec) signale à chaque action, pas au retour à la page', () => {
    const { ui, count } = ui25();
    ui.openRoomWith(7, [ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    const before = count();
    ui.click('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-republish');
    ui.respond('executeHaAction', ACTION_OK);
    assert.ok(count() > before, 'succès signalé');
    const afterSuccess = count();
    ui.respond('getMappingOverrides', ui.trees[1]); // relecture de l'arbre de l'équipement 1 après l'action
    ui.show(2);
    ui.click('.j2ha-eq-panel[data-eq-id="2"] .j2ha-eq-republish');
    ui.fail('executeHaAction');
    assert.ok(count() > afterSuccess, 'échec signalé');
    const beforeClose = count();
    ui.click('.j2ha-wv-back');
    assert.equal(count(), beforeClose, 'revenir à la page principale ne signale rien');
  });

  it('sans la page B (hook absent), les actions fonctionnent sans erreur', () => {
    const ui = createUi([ROOM]);
    ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
    ui.bridgeUp();
    ui.click('.j2ha-ha-action[data-ha-action="republier"]');
    ui.lastConfirmation().options.buttons.confirm.callback();
    assert.doesNotThrow(() => ui.respond('executeHaAction', ACTION_OK));
  });
});
