// ARTEFACT — Story 20.3 (AC4, Q2=A, Q2b=A) : « Republier la pièce » et « Supprimer puis recréer »
// (pièce et équipement) vivent dans la modale de pièce, sur les routes existantes (executeHaAction)
// avec les confirmations fortes ; les boutons globaux n'affichent plus de nombre.
// Harnais node:vm : extrait réel du contrôleur de surface, jQuery/bootbox factices.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const surface = fs.readFileSync('desktop/js/jeedom2ha_mapping_surface.js', 'utf8');
const home = fs.readFileSync('desktop/js/jeedom2ha.js', 'utf8');

function escapeText(t) {
  return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function fakeEl(html) {
  return {
    html_: html || '',
    children: [],
    handlers: {},
    props: {},
    _text: null,
    append(child) { this.children.push(child); return this; },
    text(t) { if (t === undefined) return this._text; this._text = String(t); return this; },
    html() { return escapeText(this._text === null ? '' : this._text); },
    on(event, fn) { this.handlers[event] = fn; return this; },
    prop(name, value) { if (value === undefined) return this.props[name]; this.props[name] = value; return this; },
    addClass() { return this; },
    empty() { this.children = []; return this; },
    show() { return this; },
    length: 1,
    first() { return this; },
  };
}

function loadHarness() {
  const start = surface.indexOf('function renderRoomCounters');
  const end = surface.indexOf('// --- Synthèse de publication par équipement');
  const calls = { publish: [], delete: [], executed: [], reloaded: [], feedback: [] };
  const sandbox = {
    $: function (arg) { return fakeEl(typeof arg === 'string' ? arg : ''); },
    document: { createTextNode: (t) => ({ textNode: t }) },
    ctx: { room: { equipments: [{ eq_id: 1 }, { eq_id: 2 }] }, trees: {} },
    M: require('../../desktop/js/jeedom2ha_mapping_override.js'),
    reloadEquipment: (id) => calls.reloaded.push(id),
    refreshBridgeStatus: () => calls.reloaded.push('bridge'),
    confirmHaPublishAction: (title, message, label, onConfirm) => calls.publish.push({ title, message, label, onConfirm }),
    confirmHaSupprimerAction: (title, message, label, onConfirm) => calls.delete.push({ title, message, label, onConfirm }),
    setHaActionPendingState: () => ({}),
    restoreHaActionPendingState: () => {},
    buildHaActionUserMessage: (p) => p.message,
    getHaActionAlertLevel: (p) => (p.resultat === 'succes' ? 'success' : 'danger'),
    shouldRefreshPublishedScopeAfterHaAction: (p) => p.resultat === 'succes' || p.resultat === 'succes_partiel',
    executeHaAction: (intention, portee, selection, handlers) => {
      calls.executed.push({ intention, portee, selection: Array.from(selection), handlers });
    },
  };
  vm.runInNewContext(surface.slice(start, end), sandbox);
  return { sandbox, calls };
}

function findButtons(el, acc) {
  acc = acc || [];
  (el.children || []).forEach((c) => { if (c && c.handlers) { if (c.handlers.click) acc.push(c); findButtons(c, acc); } });
  return acc;
}

describe('20.3 / Q2=A — actions de pièce', () => {
  it('« Republier la pièce » : confirmation puis executeHaAction(publier, piece, [id]) ; nom échappé', () => {
    const { sandbox, calls } = loadHarness();
    const $wrap = sandbox.buildRoomActions({ object_id: 7, object_name: 'Salon <b>"x"</b>' });
    const [republish] = findButtons($wrap);
    republish.handlers.click();
    assert.equal(calls.publish.length, 1);
    assert.match(calls.publish[0].title, /Republier la pièce/);
    assert.match(calls.publish[0].message, /Salon &lt;b&gt;&quot;x&quot;&lt;\/b&gt;/);
    assert.doesNotMatch(calls.publish[0].message, /<b>/);
    assert.equal(calls.executed.length, 0, 'aucune écriture avant confirmation');
    calls.publish[0].onConfirm();
    assert.equal(calls.executed.length, 1);
    assert.deepEqual([calls.executed[0].intention, calls.executed[0].portee, calls.executed[0].selection], ['publier', 'piece', [7]]);
  });

  it('« Supprimer puis recréer la pièce » : confirmation forte puis executeHaAction(supprimer, piece, [id])', () => {
    const { sandbox, calls } = loadHarness();
    const $wrap = sandbox.buildRoomActions({ object_id: 7, object_name: 'Salon' });
    const buttons = findButtons($wrap);
    assert.equal(buttons.length, 2);
    buttons[1].handlers.click();
    assert.equal(calls.delete.length, 1);
    for (const word of ['Attention', 'historique', 'dashboards', 'automatisations', 'entity_id']) {
      assert.ok(calls.delete[0].message.includes(word), word);
    }
    assert.equal(calls.executed.length, 0);
    calls.delete[0].onConfirm();
    assert.deepEqual([calls.executed[0].intention, calls.executed[0].portee, calls.executed[0].selection], ['supprimer', 'piece', [7]]);
  });

  it('« Sans pièce » (object_id 0) : aucune action de pièce, le démon n’adresse pas cette pièce', () => {
    const { sandbox } = loadHarness();
    const $wrap = sandbox.buildRoomActions({ object_id: 0, object_name: 'Sans pièce' });
    assert.equal(findButtons($wrap).length, 0);
  });

  it('succès : l’arbre de la pièce est relu ; échec : aucun rechargement', () => {
    const { sandbox, calls } = loadHarness();
    const $wrap = sandbox.buildRoomActions({ object_id: 7, object_name: 'Salon' });
    findButtons($wrap)[0].handlers.click();
    calls.publish[0].onConfirm();
    const { handlers } = calls.executed[0];
    handlers.onSuccess({ resultat: 'echec', message: 'x' });
    assert.deepEqual(calls.reloaded.filter((x) => x !== 'bridge'), []);
    handlers.onSuccess({ resultat: 'succes', message: 'ok' });
    assert.deepEqual(calls.reloaded.filter((x) => x !== 'bridge'), [1, 2]);
  });
});

describe('20.3 / Q2=A — « Supprimer puis recréer » par équipement', () => {
  it('confirmation forte, nom échappé, route equipement', () => {
    const { sandbox, calls } = loadHarness();
    const $host = fakeEl();
    sandbox.appendEquipmentRecreateButton($host, 12, 'Lampe <i>');
    const [button] = findButtons($host);
    button.handlers.click();
    assert.equal(calls.delete.length, 1);
    assert.match(calls.delete[0].message, /Lampe &lt;i&gt;/);
    assert.ok(calls.delete[0].message.includes('Attention'));
    assert.match(calls.delete[0].label, /Supprimer 1 équipement/);
    calls.delete[0].onConfirm();
    assert.deepEqual([calls.executed[0].intention, calls.executed[0].portee, calls.executed[0].selection], ['supprimer', 'equipement', [12]]);
    calls.executed[0].handlers.onSuccess({ resultat: 'succes', message: 'ok' });
    assert.ok(calls.reloaded.includes(12));
  });

  it('un bouton désactivé (gating pont indisponible) ne déclenche aucune confirmation', () => {
    const { sandbox, calls } = loadHarness();
    const $host = fakeEl();
    sandbox.appendEquipmentRecreateButton($host, 12, 'Lampe');
    const [button] = findButtons($host);
    button.props.disabled = true;
    button.handlers.click();
    assert.equal(calls.delete.length, 0);
  });
});

describe('20.3 / Q2b=A — boutons globaux sans nombre', () => {
  it('les confirmations globales ne lisent plus data-scope-count / data-scope-publies', () => {
    assert.doesNotMatch(home, /data-scope-count|data-scope-publies|_readHaActionCount/);
  });

  it('textes décidés : « Republier tous les équipements inclus ? » et « Supprimer puis recréer tout le parc publié ? » avec la mise en garde forte', () => {
    assert.match(home, /\{\{Republier tous les équipements inclus \?\}\}/);
    const del = home.match(/\$\('\.j2ha-ha-action\[data-ha-action="supprimer-recreer"\]'\)[\s\S]*?\n  \}\);/);
    assert.ok(del, 'gestionnaire global supprimer absent');
    assert.match(del[0], /\{\{Supprimer puis recréer tout le parc publié \?\}\}/);
    for (const word of ['Attention', 'historique', 'dashboards', 'automatisations', 'entity_id']) {
      assert.ok(del[0].includes(word), word);
    }
    assert.match(del[0], /triggerSupprimerAction\(\$button, 'global', \['all'\]\)/);
    assert.match(home, /triggerPublierAction\(\$button, 'global', \['all'\]\)/);
  });
});

describe('20.3 / AC4 — gating indépendant d’un rendu de synthèse', () => {
  it('applyHAGating ne lit aucun élément de synthèse et les boutons de la surface suivent le gating', () => {
    const gating = home.match(/function applyHAGating[\s\S]*?\n\}/)[0];
    assert.doesNotMatch(gating, /scopeSummary/);
    assert.match(surface, /data-ha-action="republier"/);
    assert.match(surface, /data-ha-action="supprimer"/);
    assert.match(surface, /applyHAGating\(window\.jeedom2haLastBridgeStatus \|\| null\)/);
  });

  it('les triggers globaux ne rafraîchissent plus de synthèse', () => {
    const publier = home.match(/function triggerPublierAction[\s\S]*?\n\}/)[0];
    const supprimer = home.match(/function triggerSupprimerAction[\s\S]*?\n\}/)[0];
    assert.doesNotMatch(publier + supprimer, /refreshPublishedScopeSummary|preserveNavState/);
    assert.match(publier, /executeHaAction\('publier'/);
    assert.match(supprimer, /executeHaAction\('supprimer'/);
  });
});
