'use strict';

/* Aide de test (front v2, Lot 1) : branche le VRAI jeedom2ha_guide.js sur une page B rendue par page_b_harness
 * (squelette PHP réel + VRAI jeedom2ha_overview.js, faux DOM). Les actions de la page (configuration, relecture,
 * filtres) sont enregistrées au lieu d'être exécutées ; le stockage local est un objet en mémoire. Données fictives. */

const G = require('../../../desktop/js/jeedom2ha_guide.js');
const { startPage } = require('./page_b_harness');

function memoryStorage(initial, options) {
  const data = Object.assign({}, initial || {});
  const opts = options || {};
  return {
    data,
    getItem(key) { if (opts.broken) throw new Error('stockage refusé'); return Object.prototype.hasOwnProperty.call(data, key) ? data[key] : null; },
    setItem(key, value) { if (opts.broken) throw new Error('stockage refusé'); data[key] = String(value); },
    removeItem(key) { if (opts.broken) throw new Error('stockage refusé'); delete data[key]; },
  };
}

/** Démarre la page B puis le guide. `options.page` est transmis à startPage ; `options.storage` = valeurs initiales. */
function startGuide(options) {
  const opts = options || {};
  const ui = startPage(opts.page);
  const storage = memoryStorage(opts.storage, { broken: opts.brokenStorage });
  const done = [];
  const haConfirmedCalls = [];
  const actions = {
    calls: [],
    openConfig() { actions.calls.push('config'); },
    openChoose() { actions.calls.push('choose'); },
    openFilter(key) { actions.calls.push('filter:' + key); },
    rescan() { actions.calls.push('rescan'); },
    publish(onDone) {
      actions.calls.push('publish');
      if (opts.publishBusy) return false;
      done.push(onDone);
      return true;
    },
  };
  const guide = G.createGuide({
    $: ui.$, bootbox: ui.dom.bootbox, storage, rooms: ui.rooms, actions,
    canAutoShow: () => opts.canAutoShow !== false,
    onHaConfirmed: () => { haConfirmedCalls.push(true); },
  });
  ui.page.subscribe(() => guide.onSnapshot(ui.page.snapshot()));
  guide.onSnapshot(ui.page.snapshot());
  return Object.assign(ui, { guide, storage, actions, haConfirmedCalls, finishPublish: (failed) => done.shift()(failed) });
}

module.exports = { G, memoryStorage, startGuide };
