'use strict';

/* Aide de test (Story 25.4) : page principale B (squelette PHP réel, faux cœur Jeedom) + vue de travail C, toutes
 * deux animées par le VRAI code sur le faux DOM, avec la surface d'équipement (jeedom2ha_mapping_surface.js) et le
 * gabarit de page (jeedom2ha.js) réels. Seuls le DOM, le navigateur (fake_browser.js), le réseau, les minuteries
 * et bootbox sont factices. Données fictives (CC-48). */

const assert = require('node:assert/strict');
const { createUi } = require('./ui_harness');
const { SCENE, phpAvailable, renderPhp, mainPart, equipmentsFor, okBody, plain } = require('./page_b_harness');
const { makeScene } = require('./big_scene');

/**
 * @param {object} options { scene, equipments (map eq_id -> entrée), window ({hash,width,height,noMatchMedia}), states (false = ne pas lire) }
 * @returns {object} ui de createUi + helpers de la vue
 */
function startWorkview(options) {
  const opts = options || {};
  const scene = opts.scene || SCENE;
  const rendered = renderPhp(scene);
  const rooms = rendered.vars.j2haRoomsTree;
  const ui = createUi(rooms, { skeleton: mainPart(rendered.html), ancestors: rendered.vars.j2haAncestors, window: opts.window, offsetTop: opts.offsetTop });
  ui.rendered = rendered;
  ui.rooms = rooms;
  ui.equipments = opts.equipments || equipmentsFor(rooms);
  ui.page.init();
  if (opts.states !== false) ui.respond('getEquipmentStates', okBody(ui.equipments));
  ui.text = (selector) => plain(ui.$(selector).text());
  ui.reads = () => ({ states: ui.count('getEquipmentStates'), trees: ui.count('getMappingOverrides') });
  ui.visible = (selector) => ui.$(selector).list.length > 0 && ui.$(selector).list[0].visible !== false;
  ui.rows = (selector) => ui.$(selector).list;
  return ui;
}

function startBig(options) {
  const big = makeScene(options);
  return startWorkview(Object.assign({}, options, { scene: big.scene, equipments: big.equipments }));
}

/** Clic sur une carte de pièce : le balisage PHP porte `onclick="j2haOpenRoom(id)"` (non exécuté par le faux DOM). */
function openCard(ui, objectId) {
  const card = ui.$(`#j2ha_roomCards .j2ha-room-card[data-object_id="${objectId}"]`);
  assert.equal(card.length, 1, 'carte de la pièce ' + objectId);
  assert.equal(card.attr('onclick'), `j2haOpenRoom(${objectId})`);
  ui.sandbox.window.j2haOpenRoom(objectId);
}

module.exports = { startWorkview, startBig, openCard, phpAvailable, assert, SCENE };
