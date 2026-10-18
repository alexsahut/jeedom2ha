'use strict';

/* Harnais node:vm qui charge le VRAI code de l'interface — gabarit de la page (jeedom2ha.js : de
 * refreshBridgeStatus à la fin du bloc `$(function () {...})`) et contrôleur de surface
 * (jeedom2ha_mapping_surface.js en entier) — sur un faux DOM (voir fake_dom.js). Seuls le DOM, le
 * réseau (`$.ajax`) et `bootbox` sont factices ; aucune fonction du code testé n'est remplacée. */

const fs = require('node:fs');
const vm = require('node:vm');
const { createDom } = require('./fake_dom');

const M = require('../../../desktop/js/jeedom2ha_mapping_override.js');
const home = fs.readFileSync('desktop/js/jeedom2ha.js', 'utf8');
const surface = fs.readFileSync('desktop/js/jeedom2ha_mapping_surface.js', 'utf8');
const homeSlice = home.slice(home.indexOf('function refreshBridgeStatus'), home.indexOf('/* Permet la réorganisation'));

const BRIDGE_UP = { daemon: true, broker: { state: 'connected' }, derniere_operation_resultat: 'aucun' };

function makeAjax(calls) {
  return function ajax(options) {
    const call = {
      options, data: options.data || {}, action: (options.data || {}).action,
      doneCbs: [], failCbs: [], alwaysCbs: [], settled: false,
    };
    function settle(kind, body) {
      if (call.settled) return;
      call.settled = true;
      if (kind === 'ok') {
        if (options.success) options.success(body);
        call.doneCbs.forEach((fn) => fn(body));
      } else {
        if (options.error) options.error({}, 'error', '');
        call.failCbs.forEach((fn) => fn());
      }
      if (options.complete) options.complete();
      call.alwaysCbs.forEach((fn) => fn());
    }
    call.respond = (body) => settle('ok', body);
    call.fail = () => settle('fail');
    calls.push(call);
    const chain = {
      done(fn) { call.doneCbs.push(fn); return chain; },
      fail(fn) { call.failCbs.push(fn); return chain; },
      always(fn) { call.alwaysCbs.push(fn); return chain; },
    };
    return chain;
  };
}

/** Construit un arbre de démon (forme `GET /system/mapping_overrides/{eq}`) pour un équipement générique. */
function view(reason, valid, publish) {
  return {
    ha_entity_type: valid ? 'light' : null,
    projection_validity: { is_valid: valid, reason_code: valid ? null : reason, missing_capabilities: [], missing_fields: [] },
    should_publish: publish,
    publication_reason: reason,
  };
}
const READY = view('sure', true, true);
const EXCLUDED = view('publication_excluded_eqlogic', false, false);
const DISABLED = view('disabled_eqlogic', false, false);

const isReady = (d) => !!d && d.should_publish === true && !!d.projection_validity && d.projection_validity.is_valid === true;

function tree(id, diagnostics, extra) {
  const options = extra || {};
  // Story 22.2 : présence dans HA (`sync_status.published_in_ha`, `commands[].published_in_ha`).
  // Story 25.1 : par défaut un équipement est présent dès qu'une commande est prête (un équipement
  // exclu, désactivé ou bloqué n'est pas dans HA) ; un `sync` explicite sans le champ simule un démon
  // plus ancien (présence inconnue).
  const anyReady = diagnostics.some(isReady);
  let present = anyReady;
  if (options.present !== undefined) present = options.present;
  else if (options.sync) present = typeof options.sync.published_in_ha === 'boolean' ? options.sync.published_in_ha : null;
  return {
    jeedom_eq_id: id,
    eq_name: options.name || ('Équipement ' + id),
    mapped: true,
    eligible: true,
    equipment_decision: options.decision || null,
    entities: options.entities || [],
    sync_status: options.sync || { synced_should_publish: anyReady, current_should_publish: anyReady, override_pending: false, published_in_ha: present },
    commands: diagnostics.map((d, i) => ({
      jeedom_cmd_id: id * 100 + i, cmd_name: 'Commande ' + i, diagnostic: d,
      published_in_ha: present === null ? null : (present && isReady(d)),
    })),
  };
}
const ok = (payload) => ({ state: 'ok', result: { payload } });

function createUi(rooms) {
  const dom = createDom();
  const calls = [];
  dom.$.ajax = makeAjax(calls);
  const sandbox = {
    $: dom.$,
    bootbox: dom.bootbox,
    document: dom.document,
    Jeedom2haMappingOverride: M,
    console,
  };
  sandbox.window = sandbox;
  sandbox.window.j2haRoomsTree = rooms || [];
  sandbox.window.confirm = () => false;
  vm.createContext(sandbox);

  // Éléments de la page principale (extrait minimal du squelette PHP) pour les gestionnaires globaux.
  dom.add('<div id="div_alert"></div>');
  dom.add('<div id="div_haGatingReason"></div>');
  dom.add('<button class="j2ha-ha-action" data-ha-action="republier"></button>');
  dom.add('<button class="j2ha-ha-action" id="bt_rescanTopology" data-ha-action="rescan"></button>');
  dom.add('<button class="j2ha-ha-action" data-ha-action="supprimer-recreer"></button>');

  vm.runInContext(homeSlice, sandbox);
  vm.runInContext(surface, sandbox);

  const ui = {
    dom, calls, sandbox,
    $: dom.$,
    pending: (action) => calls.filter((c) => c.action === action && !c.settled),
    /** Répond à l'appel en attente le plus ancien pour cette action. */
    respond(action, body) {
      const call = ui.pending(action)[0];
      if (!call) throw new Error('aucun appel en attente : ' + action);
      call.respond(body);
      return call;
    },
    fail(action) {
      const call = ui.pending(action)[0];
      if (!call) throw new Error('aucun appel en attente : ' + action);
      call.fail();
      return call;
    },
    /** Pont disponible : ce que fait la page après un getBridgeStatus réussi. */
    bridgeUp() {
      sandbox.window.jeedom2haLastBridgeStatus = BRIDGE_UP;
      sandbox.applyHAGating(BRIDGE_UP);
    },
    openRoom(objectId) { sandbox.window.j2haOpenRoom(objectId); },
    modal: () => dom.$('.modal-j2ha-room'),
    click: (selector) => {
      const target = dom.$(selector).first();
      if (!target.length) throw new Error('élément introuvable : ' + selector);
      target.list[0].handlers.click.call(target.list[0], { preventDefault() {} });
    },
    /** Touche au clavier sur le premier élément trouvé (gestionnaire `keydown` du vrai code). */
    key: (selector, key) => {
      const target = dom.$(selector).first();
      if (!target.length) throw new Error('élément introuvable : ' + selector);
      const el = target.list[0];
      if (!el.handlers.keydown) throw new Error('aucun gestionnaire keydown : ' + selector);
      el.handlers.keydown.call(el, { key, target: el, preventDefault() {}, stopPropagation() {} });
    },
    /** Clic en dehors de tout menu (gestionnaire posé sur le document par le vrai code). */
    clickOutside: () => {
      const handler = dom.documentEl.handlers.click;
      if (!handler) throw new Error('aucun gestionnaire de clic sur le document');
      handler.call(dom.documentEl, { target: dom.body });
    },
    button: (selector) => dom.$(selector).first(),
    isDisabled: (selector) => dom.$(selector).first().prop('disabled') === true,
    /** Dernier dialogue de confirmation ouvert (bootbox) hors modale de pièce. */
    lastConfirmation: () => dom.dialogs.filter((d) => d.options.buttons).slice(-1)[0],
  };
  return ui;
}

module.exports = { createUi, tree, ok, READY, EXCLUDED, DISABLED, BRIDGE_UP, view, isReady };
