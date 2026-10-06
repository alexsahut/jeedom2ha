'use strict';

/* Story 20-2 — tests de comportement de la surface (point 7 de X4, point 6 de la
 * relecture indépendante PR #210). Harnais node:vm : charge l'extrait réel de
 * jeedom2ha_mapping_surface.js (de `revertCommand` à `applyEquipment`) avec un faux
 * `$.ajax` qui consigne les requêtes et un faux `bootbox.dialog` qui capture les
 * boutons de la modale — aucune logique métier réinventée, on exécute le code du
 * contrôleur tel quel. */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

const source = fs.readFileSync('desktop/js/jeedom2ha_mapping_surface.js', 'utf8');

function fakeButtons(n) {
  var list = [];
  for (var i = 0; i < n; i++) {
    list.push({
      _props: {},
      prop(name, value) {
        if (value === undefined) return this._props[name];
        this._props[name] = value;
        return this;
      },
      data(key, value) {
        if (value === undefined) return this._props['data:' + key];
        this._props['data:' + key] = value;
        return this;
      },
      removeData(key) {
        delete this._props['data:' + key];
        return this;
      },
    });
  }
  list.each = function (fn) {
    list.forEach(function (button, i) { fn.call(button, i, button); });
    return list;
  };
  return list;
}

function fakeErrorSlot() {
  return {
    length: 1,
    _text: null,
    _visible: false,
    text(t) { this._text = t; return this; },
    show() { this._visible = true; return this; },
    hide() { this._visible = false; return this; },
    empty() { this._text = null; return this; },
  };
}

function fakeEl(tag) {
  return {
    tag: tag,
    _text: null,
    _props: {},
    children: [],
    text(t) { if (t === undefined) return this._text; this._text = t; return this; },
    append(child) { this.children.push(child); return this; },
    prop(name, value) { if (value === undefined) return this._props[name]; this._props[name] = value; return this; },
    attr(name, value) { if (value === undefined) return this._props[name]; this._props[name] = value; return this; },
  };
}

// `$.ajax` factice : consigne chaque requête (`data`) et répond selon une file de
// réponses programmées par le test (`{kind:'done', body}` ou `{kind:'fail'}`).
function fakeAjax(responses) {
  var calls = [];
  function ajax(options) {
    // Copie dans le royaume principal : `options.data` est un littéral créé dans
    // le contexte `vm` du contrôleur, dont le prototype diffère de celui du
    // royaume de test — `assert.deepEqual` (strict) échoue sur « même structure
    // mais pas la même référence » sinon, bien que les clés/valeurs soient identiques.
    calls.push(Object.assign({}, options.data));
    var mode = responses.length ? responses.shift() : { kind: 'done', body: { state: 'ok', result: null } };
    if (options.success && mode.kind === 'done') {
      options.success(mode.body);
    }
    return {
      done(fn) { if (mode.kind === 'done') fn(mode.body); return this; },
      fail(fn) { if (mode.kind === 'fail') fn(); return this; },
      always(fn) { fn(); return this; },
    };
  }
  ajax.calls = calls;
  return ajax;
}

// Charge l'extrait réel du contrôleur (revertCommand..applyEquipment) dans un
// bac à sable minimal : jQuery/bootbox factices, module pur réel, `reloadEquipment`
// espionné (la vraie fonction vit plus loin dans le fichier, hors de cet extrait).
function loadHarness(ajax) {
  var start = source.indexOf('function revertCommand');
  var end = source.indexOf('function renderSummary');
  var dialogs = [];
  var sandbox = {
    // `$(this)` sur un bouton du faux `.each` reçoit déjà un objet jQuery-like
    // (prop/data/removeData) : ne le ré-envelopper pas dans un `fakeEl`, qui n'a
    // pas ces méthodes — seul `$('<tag>')` (une chaîne) doit créer un élément.
    $: Object.assign(function (arg) { return typeof arg === 'string' ? fakeEl(arg) : arg; }, { ajax: ajax }),
    bootbox: {
      dialog(options) {
        var record = { options: options, handlers: {} };
        dialogs.push(record);
        return {
          on(event, cb) { record.handlers[event] = cb; },
          find() { return fakeEl(''); },
        };
      },
    },
    window: { confirm: function () { return false; } },
    M: M,
    AJAX_URL: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    reloadCalls: [],
  };
  sandbox.reloadEquipment = function (eqId) { sandbox.reloadCalls.push(eqId); };
  vm.runInNewContext(source.slice(start, end), sandbox);
  return { sandbox: sandbox, dialogs: dialogs };
}

test('P1 — le lien ↺ de ligne (revertCommand) retire uniquement le type de la commande', () => {
  var ajax = fakeAjax([{ kind: 'done', body: { state: 'ok', result: null } }]);
  var h = loadHarness(ajax);
  h.sandbox.revertCommand(287, 5368);
  assert.equal(ajax.calls.length, 1);
  assert.deepEqual(ajax.calls[0], { action: 'revertMappingOverride', eqId: 287, cmdId: 5368 });
  assert.notEqual(ajax.calls[0].action, 'revertPublicationOverride');
  assert.deepEqual(h.sandbox.reloadCalls, [287]);
});

test('Revenir au mode automatique : portée entité (cmdId) et équipement (sans cmdId)', () => {
  var ajax = fakeAjax([
    { kind: 'done', body: { state: 'ok', result: null } },
    { kind: 'done', body: { state: 'ok', result: null } },
  ]);
  var h = loadHarness(ajax);
  h.sandbox.revertPublication(287, 5368, fakeButtons(2), fakeErrorSlot());
  h.sandbox.revertPublication(287, null, fakeButtons(2), fakeErrorSlot());
  assert.deepEqual(ajax.calls[0], { action: 'revertPublicationOverride', eqId: 287, cmdId: 5368 });
  assert.deepEqual(ajax.calls[1], { action: 'revertPublicationOverride', eqId: 287 });
  assert.deepEqual(h.sandbox.reloadCalls, [287, 287]);
});

var notPublished = { should_publish: false };
var published = { should_publish: true };

test('Exclure, portée entité : aucune modale si non publiée, confirmation si publiée', () => {
  var ajax = fakeAjax([{ kind: 'done', body: { state: 'ok', result: null } }]);
  var h = loadHarness(ajax);
  h.sandbox.requestPublication(20200, { decision: notPublished, override_command_id: 5368 },
    false, 'exclude', fakeButtons(2), [], fakeErrorSlot());
  assert.equal(ajax.calls.length, 1, 'aucune confirmation requise : envoi direct');
  assert.equal(h.dialogs.length, 0);

  var h2 = loadHarness(fakeAjax([]));
  h2.sandbox.requestPublication(20200, { decision: published, override_command_id: 5368 },
    false, 'exclude', fakeButtons(2), [], fakeErrorSlot());
  assert.equal(h2.dialogs.length, 1, 'entité déjà publiée : confirmation requise');
});

test('Exclure, portée équipement : confirmation dès qu’une entité secondaire est publiée', () => {
  var entities = [
    { ha_entity_type: 'switch', command_ids: [5368], decision: notPublished },
    { ha_entity_type: 'sensor', command_ids: [5369], decision: published },
  ];
  var h = loadHarness(fakeAjax([]));
  h.sandbox.requestPublication(20200, { decision: notPublished, override_command_id: null },
    true, 'exclude', fakeButtons(2), [{ jeedom_cmd_id: 5369, cmd_name: 'Conso W' }], fakeErrorSlot(), entities);
  assert.equal(h.dialogs.length, 1, 'une entité secondaire publiée doit confirmer (AC5)');
  var content = h.dialogs[0].options.message;
  var listed = content.children.some((p) => (p.children || []).some((li) => (li.text() || '').indexOf('Conso W') !== -1));
  assert.equal(listed, true, 'la modale liste l’entité secondaire qui quittera Home Assistant');
});

test('Exclure, portée équipement : aucune modale si équipement et entités non publiés', () => {
  var entities = [{ ha_entity_type: 'switch', command_ids: [5368], decision: notPublished }];
  var ajax = fakeAjax([{ kind: 'done', body: { state: 'ok', result: null } }]);
  var h = loadHarness(ajax);
  h.sandbox.requestPublication(20200, { decision: notPublished, override_command_id: null },
    true, 'exclude', fakeButtons(2), [], fakeErrorSlot(), entities);
  assert.equal(h.dialogs.length, 0);
  assert.equal(ajax.calls.length, 1);
});

// Relecture indépendante PR #210 (point 6) : aperçu de forçage à la portée ENTITÉ —
// previewMappingOverride envoie cmdId, la modale liste type/validité/commandes, et le
// bouton Confirmer envoie l'écriture réelle (savePublicationOverride) une fois cliqué.
test('Forcer, portée entité : aperçu accepté envoie cmdId et confirme la pose', () => {
  const previewBody = {
    state: 'ok',
    result: { payload: { overridden: {
      ha_entity_type: 'cover', projection_validity: { is_valid: true }, should_publish: true,
      publication_reason: 'sure', command_ids: [5368],
    } } },
  };
  var ajax = fakeAjax([{ kind: 'done', body: previewBody }, { kind: 'done', body: { state: 'ok', result: null } }]);
  var h = loadHarness(ajax);
  h.sandbox.requestPublication(20200, { decision: notPublished, override_command_id: 5368 },
    false, 'force', fakeButtons(2), [{ jeedom_cmd_id: 5368, cmd_name: 'Ouvrir' }], fakeErrorSlot());
  assert.deepEqual(ajax.calls[0], { action: 'previewMappingOverride', eqId: 20200, publicationPolicy: 'force_publish', cmdId: 5368 });
  assert.equal(h.dialogs.length, 1);
  h.dialogs[0].options.buttons.confirm.callback();
  assert.equal(ajax.calls.length, 2, 'le clic sur Confirmer envoie la pose réelle (savePublicationOverride)');
});

test('Forcer, portée équipement : aucun cmdId envoyé, la modale liste chaque entité (entities[])', () => {
  const entities = [
    { ha_entity_type: 'switch', command_ids: [5368], decision: { should_publish: true } },
    { ha_entity_type: 'sensor', command_ids: [5369], decision: { should_publish: false } },
  ];
  const previewBody = {
    state: 'ok',
    result: { payload: { overridden: {
      ha_entity_type: 'switch', projection_validity: { is_valid: true }, should_publish: true,
      command_ids: [5368], entities: entities,
    } } },
  };
  var ajax = fakeAjax([{ kind: 'done', body: previewBody }]);
  var h = loadHarness(ajax);
  h.sandbox.requestPublication(20200, { decision: notPublished, override_command_id: null },
    true, 'force', fakeButtons(2), [], fakeErrorSlot(), entities);
  assert.deepEqual(ajax.calls[0], { action: 'previewMappingOverride', eqId: 20200, publicationPolicy: 'force_publish' });
  assert.equal(h.dialogs.length, 1, 'un aperçu réussi ouvre la modale de confirmation');
  var content = h.dialogs[0].options.message;
  var text = content.children.map((p) => (p.children || []).map((li) => li.text()).concat(p.text() || []).join('|')).join('||');
  assert.match(text, /switch/, 'la modale liste l’entité switch (AC3 — toutes les entités, pas seulement la principale)');
  assert.match(text, /sensor/, 'la modale liste aussi l’entité sensor non publiée');
});

test('Forcer : un aperçu refusé grise Confirmer avec la cause réelle, sans jamais poser', () => {
  const previewBody = {
    state: 'ok',
    result: { payload: { overridden: {
      ha_entity_type: 'cover', projection_validity: { is_valid: false, reason_code: 'ha_missing_command_topic' },
      should_publish: false, publication_reason: 'ambiguous_skipped', command_ids: [5368],
    } } },
  };
  var ajax = fakeAjax([{ kind: 'done', body: previewBody }]);
  var h = loadHarness(ajax);
  h.sandbox.requestPublication(20200, { decision: notPublished, override_command_id: 5368 },
    false, 'force', fakeButtons(2), [], fakeErrorSlot());
  assert.equal(h.dialogs.length, 1);
  h.dialogs[0].options.buttons.confirm.callback();
  assert.equal(ajax.calls.length, 1, 'Confirmer grisé par disableConfirm : aucune écriture déclenchée');
});

test('Forcer : une erreur démon relayée par le PHP (409 inclus) n\'ouvre jamais de modale', () => {
  var errorSlot = fakeErrorSlot();
  var ajax = fakeAjax([{ kind: 'done', body: { state: 'ok', result: { status: 'error', message: 'Commande partagée sans entité propre' } } }]);
  var h = loadHarness(ajax);
  h.sandbox.requestPublication(20200, { decision: notPublished, override_command_id: 5368 },
    false, 'force', fakeButtons(2), [], errorSlot);
  assert.equal(h.dialogs.length, 0, 'erreur démon relayée : pas de modale, le message réel est affiché');
  assert.equal(errorSlot._text, 'Commande partagée sans entité propre');
});

test('Forcer : le démon ne répond pas (.fail) affiche un message et libère les boutons', () => {
  var errorSlot = fakeErrorSlot();
  var buttons = fakeButtons(2);
  var ajax = fakeAjax([{ kind: 'fail' }]);
  var h = loadHarness(ajax);
  h.sandbox.requestPublication(20200, { decision: notPublished, override_command_id: 5368 },
    false, 'force', buttons, [], errorSlot);
  assert.equal(h.dialogs.length, 0);
  assert.match(errorSlot._text, /ne répond pas/);
});

// Point 6 : applyEquipment (bouton « Appliquer ») — succès (recharge l'équipement) et
// erreur démon relayée (message affiché, aucun rechargement).
test('Appliquer : succès recharge l\'équipement, erreur démon affiche le message sans recharger', () => {
  var okButton = { _disabled: false, prop(name, value) { if (value === undefined) return this._disabled; this._disabled = value; return this; } };
  var okAjax = fakeAjax([{ kind: 'done', body: { state: 'ok', result: null } }]);
  var h1 = loadHarness(okAjax);
  h1.sandbox.applyEquipment(20200, okButton, fakeErrorSlot());
  assert.deepEqual(okAjax.calls[0], { action: 'executeHaAction', intention: 'publier', portee: 'equipement', selection: JSON.stringify([20200]) });
  assert.deepEqual(h1.sandbox.reloadCalls, [20200]);
  assert.equal(okButton.prop('disabled'), false, 'le bouton est réactivé après la requête');

  var errSlot = fakeErrorSlot();
  var errButton = { _disabled: false, prop(name, value) { if (value === undefined) return this._disabled; this._disabled = value; return this; } };
  var errAjax = fakeAjax([{ kind: 'done', body: { state: 'ok', result: { status: 'error', message: 'Publication refusée' } } }]);
  var h2 = loadHarness(errAjax);
  h2.sandbox.applyEquipment(20200, errButton, errSlot);
  assert.deepEqual(h2.sandbox.reloadCalls, [], 'une erreur démon ne doit jamais recharger l\'équipement');
  assert.equal(errSlot._text, 'Publication refusée');
});
