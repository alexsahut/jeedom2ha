'use strict';

/* Harnais node:vm qui charge le VRAI code de l'interface — gabarit de la page (jeedom2ha.js : de
 * refreshBridgeStatus à la fin du bloc `$(function () {...})`), contrôleur de surface
 * (jeedom2ha_mapping_surface.js en entier), page principale B (jeedom2ha_overview.js) et vue de travail C
 * (jeedom2ha_workview.js) — sur un faux DOM (voir fake_dom.js) et un faux navigateur (fake_browser.js).
 * Seuls le DOM, le navigateur, le réseau (`$.ajax`), les minuteries de B / C et `bootbox` sont factices ;
 * aucune fonction du code testé n'est remplacée.
 *
 * Story 25.4 : la fenêtre de pièce n'existe plus. `ui.openRoom(id)` ouvre la vue C sur la pièce (aucune
 * lecture) ; `ui.selectEquipment(eqId, tree)` sélectionne un équipement de l'arbre (une lecture d'arbre
 * unitaire) et, si `tree` est fourni, y répond. */

const fs = require('node:fs');
const vm = require('node:vm');
const { createDom } = require('./fake_dom');
const { createFakeWindow } = require('./fake_browser');

const M = require('../../../desktop/js/jeedom2ha_mapping_override.js');
const O = require('../../../desktop/js/jeedom2ha_overview.js');
const W = require('../../../desktop/js/jeedom2ha_workview.js');
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

/** Squelette minimal de la page (ids et classes lus par B et C) : cartes regroupées dans l'ordre des pièces. */
function skeletonFor(rooms) {
  const cards = (rooms || []).map((room) => `<div class="objectDisplayCard cursor j2ha-room-card" data-object_id="${room.object_id}"><span class="name">${room.object_name}</span><span class="text-muted j2ha-room-count"> (${room.equipments.length})</span><div class="j2ha-room-state"></div></div>`).join('');
  return '<div id="j2ha_mainView"><div id="j2ha_houseBlock"><span id="j2ha_houseNumber"></span><span id="j2ha_houseSub"></span>'
    + '<div id="j2ha_houseMeta"></div><div id="j2ha_houseGauge"></div><div id="j2ha_houseChips"></div><span id="j2ha_freshness"></span>'
    + '<button id="bt_refreshStates"></button><div id="j2ha_readStatus"></div></div>'
    + '<div id="j2ha_filterPanel"><strong id="j2ha_filterTitle"></strong><button id="bt_clearFilter"></button><ul id="j2ha_filterList"></ul></div>'
    + `<div id="j2ha_roomCards" class="j2ha-room-groups"><div class="j2ha-room-group"><div class="objectListContainer">${cards}</div></div></div></div>`
    + '<div id="j2ha_workView" class="j2ha-wv"></div>';
}

function createUi(rooms, options) {
  const opts = options || {};
  const dom = createDom();
  const calls = [];
  dom.$.ajax = makeAjax(calls);
  const win = createFakeWindow(opts.window);
  const sandbox = {
    $: dom.$,
    bootbox: dom.bootbox,
    document: dom.document,
    Jeedom2haMappingOverride: M,
    setTimeout,
    clearTimeout,
    console,
  };
  // `window` est le faux navigateur (location / history / matchMedia / tailles) ; le code testé y pose ses globales.
  Object.assign(win, {
    Jeedom2haMappingOverride: M,
    j2haRoomsTree: rooms || [],
    j2haAncestors: opts.ancestors || [],
    confirm: () => false,
  });
  sandbox.window = win;
  vm.createContext(sandbox);

  // Éléments de la page principale (extrait minimal du squelette PHP) pour les gestionnaires globaux.
  dom.add('<div id="div_alert"></div>');
  dom.add('<div id="div_haGatingReason"></div>');
  dom.add('<button class="j2ha-ha-action" data-ha-action="republier"></button>');
  dom.add('<button class="j2ha-ha-action" id="bt_rescanTopology" data-ha-action="rescan"></button>');
  dom.add('<button class="j2ha-ha-action" data-ha-action="supprimer-recreer"></button>');
  dom.add(opts.skeleton || skeletonFor(rooms));

  vm.runInContext(homeSlice, sandbox);
  vm.runInContext(surface, sandbox);

  // Minuteries de B et de C : déterministes (`ui.advance(ms)`), jamais de vraie attente.
  const timers = [];
  let clock = 5_000_000;
  const env = {
    setTimeout: (fn, ms) => { timers.push({ fn, at: clock + ms, id: timers.length + 1, cancelled: false }); return timers.length; },
    clearTimeout: (id) => { const t = timers[id - 1]; if (t) t.cancelled = true; },
    now: () => clock,
  };
  const holder = {};
  const page = O.createPage({
    $: dom.$, document: dom.document, bootbox: dom.bootbox, rooms: sandbox.window.j2haRoomsTree,
    readStates: O.ajaxFetch(dom.$),
    now: env.now, setTimeout: env.setTimeout, clearTimeout: env.clearTimeout,
    openRoom: (id) => holder.wv.open({ room: id }),
    openView: (target) => holder.wv.open(target),
  });
  const wv = W.createWorkview({
    $: dom.$, document: dom.document, window: win, surface: win.Jeedom2haSurface,
    page, rooms: win.j2haRoomsTree, now: env.now, setTimeout: env.setTimeout, clearTimeout: env.clearTimeout,
    offsetTop: () => opts.offsetTop || 120,
  });
  holder.wv = wv;
  // Fins d'action : une relecture des états par B, sans refresh, coalescée (ce que fait le démarrage navigateur de B).
  win.j2haNotifyStatesChanged = () => page.reader.trigger();

  wv.start();

  const ui = {
    dom, calls, sandbox, page, wv, win,
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
    count: (action) => calls.filter((c) => c.action === action).length,
    /** Avance l'horloge de B et de C et exécute les minuteries échues. */
    advance(ms) {
      clock += ms;
      timers.filter((t) => !t.cancelled && !t.done && t.at <= clock).forEach((t) => { t.done = true; t.fn(); });
    },
    /** Lecture des états de la maison par B (un appel), avec la réponse fournie ({ eq_id: entrée }). */
    loadStates(equipments, meta) {
      page.reader.load();
      return ui.respond('getEquipmentStates', {
        state: 'ok',
        result: { status: 'ok', payload: { schema_version: 1, available: true, meta: Object.assign({ action_in_progress: false }, meta || {}), equipments: equipments || {}, unread: [] } },
      });
    },
    /** Pont disponible : ce que fait la page après un getBridgeStatus réussi. */
    bridgeUp() {
      sandbox.window.jeedom2haLastBridgeStatus = BRIDGE_UP;
      sandbox.applyHAGating(BRIDGE_UP);
    },
    openRoom(objectId) { win.j2haOpenRoom(objectId); },
    /** Sélectionne un équipement dans l'arbre de la vue (clic réel sur la ligne) puis, si `tree` est fourni, répond à la lecture. */
    selectEquipment(eqId, tree) {
      ui.click(`.j2ha-wv-eq[data-eq-id="${eqId}"] .j2ha-wv-row`);
      if (tree !== undefined && tree !== null) ui.respond('getMappingOverrides', tree);
    },
    isOpen: () => wv.isOpen(),
    /** Revient au détail de la pièce affichée (clic sur la ligne de la pièce dans l'arbre). */
    showRoom() {
      const state = wv.state();
      ui.click(`.j2ha-wv-room[data-object_id="${state.room}"] .j2ha-wv-row`);
    },
    click: (selector) => {
      const target = dom.$(selector).first();
      if (!target.length) throw new Error('élément introuvable : ' + selector);
      target.list[0].handlers.click.call(target.list[0], { preventDefault() {}, stopPropagation() {}, target: target.list[0] });
    },
    /** Touche au clavier sur le premier élément trouvé (gestionnaire `keydown` du vrai code). */
    key: (selector, key, extra) => {
      const target = dom.$(selector).first();
      if (!target.length) throw new Error('élément introuvable : ' + selector);
      const el = target.list[0];
      if (!el.handlers.keydown) throw new Error('aucun gestionnaire keydown : ' + selector);
      el.handlers.keydown.call(el, Object.assign({ key, target: el, preventDefault() {}, stopPropagation() {} }, extra || {}));
    },
    /** Clic en dehors de tout menu (gestionnaire posé sur le document par le vrai code). */
    clickOutside: () => {
      const handler = dom.documentEl.handlers.click;
      if (!handler) throw new Error('aucun gestionnaire de clic sur le document');
      handler.call(dom.documentEl, { target: dom.body });
    },
    button: (selector) => dom.$(selector).first(),
    isDisabled: (selector) => dom.$(selector).first().prop('disabled') === true,
    /** Dernier dialogue de confirmation ouvert (bootbox) hors fenêtre de pièce. */
    lastConfirmation: () => dom.dialogs.filter((d) => d.options.buttons).slice(-1)[0],
  };
  return ui;
}

module.exports = { createUi, skeletonFor, tree, ok, READY, EXCLUDED, DISABLED, BRIDGE_UP, view, isReady };
