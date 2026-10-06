'use strict';

/* Story 20-2 (P3, relecture indépendante PR #210, reprise X5d) : le lien ↺ d'une
 * ligne (`renderCommandRow` → `revertCommand`) devenait inerte après un échec
 * (`.off('click')` sans jamais être réattaché, et aucun gestionnaire d'erreur sur
 * la requête). Harnais node:vm : charge l'extrait réel de jeedom2ha_mapping_surface.js
 * (de `buildOptions` à `clearRequestError`, donc `renderCommandRow`/`revertCommand`
 * tels quels) avec un faux `$`/`$.ajax`/`M` réel — aucune logique métier réinventée.
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

const source = fs.readFileSync('desktop/js/jeedom2ha_mapping_surface.js', 'utf8');

// Shim DOM minimal : assez pour construire la ligne réelle (append/attr/prop/
// addClass/removeClass/html/text) et simuler un clic réel sur le lien ↺ trouvé
// par `.find()`, avec un `on`/`one`/`off` qui retire vraiment le gestionnaire.
function fakeEl(tagString) {
  const open = /^<(\w+)([^>]*)>/.exec(tagString || '') || [];
  const classMatch = /class="([^"]*)"/.exec(open[2] || '');
  const el = {
    tag: open[1] || '',
    classes: classMatch ? classMatch[1].split(/\s+/) : [],
    attrs: {},
    props: {},
    _text: null,
    children: [],
    handlers: {},
    hasClass(c) { return this.classes.indexOf(c) !== -1; },
    addClass(c) { c.split(/\s+/).forEach((x) => { if (!this.hasClass(x)) this.classes.push(x); }); return this; },
    removeClass(c) { const rm = c.split(/\s+/); this.classes = this.classes.filter((x) => rm.indexOf(x) === -1); return this; },
    attr(name, value) { if (value === undefined) return this.attrs[name]; this.attrs[name] = value; return this; },
    prop(name, value) { if (value === undefined) return this.props[name]; this.props[name] = value; return this; },
    text(value) { if (value === undefined) return this._text; this._text = value; this.children = []; return this; },
    html() { this.children = []; return this; },
    empty() { this.children = []; return this; },
    append(child) { this.children.push(child); return this; },
    show() { this._display = ''; return this; },
    hide() { this._display = 'none'; return this; },
    find(selector) {
      const cls = selector.replace('.', '');
      let found = null;
      (function walk(node) {
        for (const child of node.children) {
          if (found) return;
          if (child && child.hasClass && child.hasClass(cls)) { found = child; return; }
          if (child && child.children) walk(child);
        }
      })(this);
      return found || fakeEl('');
    },
    on(event, handler) { (this.handlers[event] = this.handlers[event] || []).push(handler); return this; },
    one(event, handler) {
      const self = this;
      function wrapped() { self.off(event, wrapped); handler.apply(self, arguments); }
      return this.on(event, wrapped);
    },
    off(event, handler) {
      if (!this.handlers[event]) return this;
      this.handlers[event] = handler ? this.handlers[event].filter((h) => h !== handler) : [];
      return this;
    },
    trigger(event) { (this.handlers[event] || []).slice().forEach((h) => h.call(this)); return this; },
  };
  return el;
}

// `$.ajax` factice : consigne chaque requête et répond selon une file programmée
// par le test (`{kind:'done', body}` ou `{kind:'fail'}`) — mêmes conventions que
// test_story_20_2_p1_p2_comportement_surface.node.test.js.
function fakeAjax(responses) {
  const calls = [];
  function ajax(options) {
    calls.push(Object.assign({}, options.data));
    const mode = responses.length ? responses.shift() : { kind: 'done', body: { state: 'ok', result: null } };
    if (mode.kind === 'done' && options.success) options.success(mode.body);
    if (mode.kind === 'fail' && options.error) options.error();
  }
  ajax.calls = calls;
  return ajax;
}

// Charge l'extrait réel (buildOptions..clearRequestError), donc `renderCommandRow`
// et `revertCommand` tels quels, avec `ctx` réinitialisé comme en tête de fichier.
function loadHarness(ajax) {
  const start = source.indexOf('function buildOptions');
  const end = source.indexOf('function disableButtons');
  const sandbox = {
    $: Object.assign((arg) => (typeof arg === 'string' ? fakeEl(arg) : arg), { ajax: ajax }),
    M: M,
    AJAX_URL: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    ctx: { reassurance: M.initReassuranceState(), timers: {}, xhr: {} },
    reloadCalls: [],
  };
  sandbox.reloadEquipment = (eqId) => { sandbox.reloadCalls.push(eqId); };
  vm.runInNewContext(source.slice(start, end), sandbox);
  return sandbox;
}

function normalizedRow() {
  return M.normalizeCommandRow({
    jeedom_cmd_id: 5368, cmd_name: 'Ouvrir', generic_type: 'VOLET', coverable: true,
    covered: true, effective_ha: 'cover', override_applied: true, override_source: 'command',
    diagnostic: null,
  });
}

// Point 4 (reprise X5d) : le gestionnaire RÉEL attaché au lien ↺ par renderCommandRow
// (jamais revertCommand appelé directement) poste bien revertMappingOverride/cmdId —
// jamais revertPublicationOverride (qui purgerait exclusion/forçage de toute l'entité).
test('P3 — le clic réel sur ↺ poste revertMappingOverride avec cmdId, jamais revertPublicationOverride', () => {
  const ajax = fakeAjax([{ kind: 'done', body: { state: 'ok', result: null } }]);
  const h = loadHarness(ajax);
  const $tr = h.renderCommandRow(287, normalizedRow());
  const link = $tr.find('.mo-revert-cmd');
  assert.equal(link.tag, 'a', 'le lien ↺ doit exister sur une commande avec override_applied');
  link.trigger('click');
  assert.deepEqual(ajax.calls[0], { action: 'revertMappingOverride', eqId: 287, cmdId: 5368 });
  assert.notEqual(ajax.calls[0].action, 'revertPublicationOverride');
  assert.deepEqual(h.reloadCalls, [287]);
});

test('P3 — une erreur démon réaffiche une cause lisible et réactive le lien pour un nouvel essai', () => {
  const ajax = fakeAjax([
    { kind: 'done', body: { state: 'ok', result: { status: 'error', message: 'Commande partagée sans entité propre' } } },
    { kind: 'done', body: { state: 'ok', result: null } },
  ]);
  const h = loadHarness(ajax);
  const $tr = h.renderCommandRow(287, normalizedRow());
  const link = $tr.find('.mo-revert-cmd');
  link.trigger('click');
  assert.equal(link.prop('disabled'), false, 'le lien doit redevenir cliquable après un échec');
  const errorSlot = $tr.find('.mo-revert-error');
  assert.equal(errorSlot._text, 'Commande partagée sans entité propre');
  assert.deepEqual(h.reloadCalls, [], 'une erreur démon ne doit jamais recharger l\'équipement');

  // Réessai : le gestionnaire a bien été réattaché (pas un lien inerte).
  link.trigger('click');
  assert.equal(ajax.calls.length, 2);
  assert.deepEqual(h.reloadCalls, [287]);
});

test('P3 — une erreur réseau (démon ne répond pas) affiche un message et réactive le lien', () => {
  const ajax = fakeAjax([{ kind: 'fail' }]);
  const h = loadHarness(ajax);
  const $tr = h.renderCommandRow(287, normalizedRow());
  const link = $tr.find('.mo-revert-cmd');
  link.trigger('click');
  assert.equal(link.prop('disabled'), false);
  const errorSlot = $tr.find('.mo-revert-error');
  assert.match(errorSlot._text, /ne répond pas/);
  assert.deepEqual(h.reloadCalls, []);
});
