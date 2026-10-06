// ARTEFACT — Story 20-2 (revue ClaudeBox X4, point 7) : comportements DOM de la surface de
// publication, extraits par node:vm (modèle : loadConfirmationHarness,
// test_story_20_4_rescan_ui.node.test.js, PR #209). Les fonctions pures (jeedom2ha_mapping_override.js)
// restent couvertes par test_story_20_2_publication_surface.node.test.js ; ce fichier couvre
// uniquement l'orchestration jQuery/Bootbox de jeedom2ha_mapping_surface.js.
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('desktop/js/jeedom2ha_mapping_surface.js', 'utf8');

function loadPublicationDialogHarness() {
  const start = source.indexOf('function confirmPublicationDialog');
  const end = source.indexOf('function buildForcePreviewContent', start);
  const handlers = {};
  let dialogOptions;
  let confirmDisabled = false;
  let confirmTitle = null;
  const sandbox = {
    bootbox: {
      dialog(opts) {
        dialogOptions = opts;
        return {
          on(event, cb) { handlers[event] = cb; },
          find() {
            return {
              prop(name, value) { if (name === 'disabled') confirmDisabled = value; return this; },
              attr(name, value) { if (name === 'title') confirmTitle = value; return this; },
            };
          },
        };
      },
    },
  };
  vm.runInNewContext(source.slice(start, end), sandbox);
  return {
    confirmPublicationDialog: sandbox.confirmPublicationDialog,
    handlers,
    get dialogOptions() { return dialogOptions; },
    get confirmDisabled() { return confirmDisabled; },
    get confirmTitle() { return confirmTitle; },
  };
}

function loadButtonStateHarness() {
  const start = source.indexOf('function disableButtons');
  const end = source.indexOf('function publicationRequest', start);
  function wrap(el) {
    return {
      prop(name, value) {
        if (value === undefined) return el[name];
        el[name] = value;
        return this;
      },
      data(key, value) {
        if (value === undefined) return el.__data[key];
        el.__data[key] = value;
        return this;
      },
      removeData(key) { delete el.__data[key]; return this; },
    };
  }
  function makeGroup(initialStates) {
    const els = initialStates.map((disabled) => ({ disabled, __data: {} }));
    return { els, each(fn) { this.els.forEach((el, i) => fn.call(el, i, el)); return this; } };
  }
  const sandbox = { $: wrap };
  vm.runInNewContext(source.slice(start, end), sandbox);
  return { disableButtons: sandbox.disableButtons, restoreButtons: sandbox.restoreButtons, makeGroup };
}

test('20-2 — revue X4 (point 5) : Annuler, Échap et la croix (hidden.bs.modal) libèrent sans confirmer', () => {
  for (const close of ['cancel', 'onEscape', 'hidden.bs.modal']) {
    const harness = loadPublicationDialogHarness();
    const state = { confirmed: 0, cancelled: 0 };
    harness.confirmPublicationDialog('contenu', () => { state.confirmed += 1; }, () => { state.cancelled += 1; });
    if (close === 'cancel') harness.dialogOptions.buttons.cancel.callback();
    else if (close === 'onEscape') harness.dialogOptions.onEscape();
    else harness.handlers['hidden.bs.modal']();
    assert.equal(state.confirmed, 0, close);
    assert.equal(state.cancelled, 1, close);
  }
});

test('20-2 — revue X4 (point 5) : après Confirmer, la fermeture de la modale ne rappelle pas onCancel', () => {
  const harness = loadPublicationDialogHarness();
  const state = { confirmed: 0, cancelled: 0 };
  harness.confirmPublicationDialog('contenu', () => { state.confirmed += 1; }, () => { state.cancelled += 1; });
  harness.dialogOptions.buttons.confirm.callback();
  harness.handlers['hidden.bs.modal']();
  harness.dialogOptions.onEscape();
  assert.equal(state.confirmed, 1);
  assert.equal(state.cancelled, 0);
});

test('20-2 — revue X4 (point 3/6) : un aperçu refusé (disableConfirm) grise Confirmer avec la cause réelle et bloque le clic', () => {
  const harness = loadPublicationDialogHarness();
  const state = { confirmed: 0 };
  harness.confirmPublicationDialog(
    'contenu', () => { state.confirmed += 1; }, () => {},
    { disableConfirm: 'ha_missing_temperature_command_topic' },
  );
  assert.equal(harness.confirmDisabled, true);
  assert.equal(harness.confirmTitle, 'ha_missing_temperature_command_topic');
  harness.dialogOptions.buttons.confirm.callback();
  assert.equal(state.confirmed, 0);
});

test('20-2 — revue X4 (point 5) : disableButtons capture l\'état initial, restoreButtons le restaure exactement', () => {
  const harness = loadButtonStateHarness();
  // Exclure actif, Forcer déjà grisé pour sa propre cause (ex. déjà publiée), Revenir actif.
  const group = harness.makeGroup([false, true, false]);
  harness.disableButtons(group);
  assert.deepEqual(group.els.map((el) => el.disabled), [true, true, true]);
  harness.restoreButtons(group);
  assert.deepEqual(group.els.map((el) => el.disabled), [false, true, false]);
  assert.deepEqual(group.els.map((el) => el.__data), [{}, {}, {}]);
});

test('20-2 — revue X4 (point 5) : un second disableButtons imbriqué ne doit pas écraser l\'état capturé', () => {
  // Reproduit requestPublication -> save() -> publicationRequest : disableButtons est appelé
  // une première fois avant la modale, une seconde fois (sans effet sur la capture) après
  // confirmation, avant que la seule restoreButtons finale restaure l'état d'origine.
  const harness = loadButtonStateHarness();
  const group = harness.makeGroup([false, true]);
  harness.disableButtons(group);
  harness.disableButtons(group);
  assert.deepEqual(group.els.map((el) => el.disabled), [true, true]);
  harness.restoreButtons(group);
  assert.deepEqual(group.els.map((el) => el.disabled), [false, true]);
});
