// ARTEFACT — Story 25.7 (AC9) : l'étape 10 `cause-exclusion` du parcours vue-maitre-detail-c (lecture seule) passe en vrai
// Chromium sur la page livrée et enregistre la ventilation ; une mention hors glossaire, une mention sur un « Désactivé » ou
// des repères de carte qui ne somment pas aux lignes « Exclu » la font échouer (contrôles négatifs). `lib/policy.mjs` intact.
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView, gate } = require('./helpers/workview_browser');

const root = path.join(__dirname, '..', '..');
const source = fs.readFileSync(path.join(root, 'tests/e2e/gate/parcours/vue-maitre-detail-c.mjs'), 'utf8');

async function runParcours(page, ctx) {
  const parcours = await import(gate('parcours', 'vue-maitre-detail-c.mjs'));
  const { normalizeParcoursRecord } = await import(gate('lib', 'report.mjs'));
  const recorded = {};
  const helpers = {
    record: (key, value) => { const [k, v] = normalizeParcoursRecord(key, value); recorded[k] = v; },
    journalEntries: () => ctx.journal,
  };
  await parcours.run(page, { helpers });
  return recorded;
}

test('25.7 gate — étiquettes et clés record de l\'étape 10, étapes 1 à 9 gardées, aucune écriture déclarée', () => {
  for (const label of ['cause-exclusion-hors-glossaire', 'cause-sur-desactive', 'exclus-carte-differents-de-l-arbre', 'requete-pendant-cause-exclusion']) {
    assert.ok(source.includes(`'${label}'`), label);
  }
  for (const key of ['exclus_par_plugin', 'exclus_par_piece', 'exclus_individuels', 'exclus_sans_cause']) assert.ok(source.includes(`'${key}'`), key);
  assert.match(source, /atStep\(helpers, 10, 'cause-exclusion'/);
  for (const step of [1, 2, 3, 4, 6, 7, 8, 9]) assert.match(source, new RegExp(`atStep\\(helpers, ${step},`), 'étape ' + step);
  assert.match(source, /export const declaredEquipments = \{\};/);
});

test('25.7 gate réel — le parcours passe, la ventilation est enregistrée, aucune écriture ni requête de plus', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    const recorded = await runParcours(page, ctx);
    const total = recorded.exclus_par_plugin + recorded.exclus_par_piece + recorded.exclus_individuels + recorded.exclus_sans_cause;
    assert.ok(total >= 1, 'la fixture comporte des équipements exclus : ' + total);
    assert.equal(recorded.exclus_par_plugin, 0);
    assert.deepEqual(ctx.errors, []);
    const writes = ctx.journal.filter((e) => ['executeHaAction', 'exportDiagnostic', 'scanTopology', 'saveMappingOverride', 'savePublicationOverride'].includes(e.action)).length;
    assert.equal(writes, 0);
  });
});

/** Le parcours recharge la page (étape 6) : le patch est donc posé AVANT chaque chargement, à l'affectation de la bibliothèque. */
async function patchedPage(page, patchSource) {
  await page.addInitScript(`(function () {
    var value;
    Object.defineProperty(window, 'Jeedom2haMappingOverride', {
      configurable: true,
      get: function () { return value; },
      set: function (v) { value = v; (${patchSource})(v); },
    });
  }());`);
  await page.reload();
  await page.waitForFunction(() => (document.querySelector('#j2ha_houseNumber')?.textContent ?? '').trim() !== '');
}

test('25.7 gate réel — contrôle négatif : une mention hors glossaire fait échouer l\'étape', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    await patchedPage(page, `function (M) {
      var original = M.exclusionCauseText;
      M.exclusionCauseText = function (cause, name, form) { return form === 'short' ? 'cause inventée' : original(cause, name, form); };
    }`);
    await assert.rejects(() => runParcours(page, ctx), /cause-exclusion-hors-glossaire/);
  });
});

test('25.7 gate réel — contrôle négatif : des repères de carte qui ne somment pas aux lignes « Exclu » font échouer l\'étape', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    // Retire les repères « N exclus » de la page à chaque rendu de cartes : leur somme (0) ≠ lignes « Exclu » de l'arbre.
    await patchedPage(page, `function (M) {
      var original = M.exclusionBreakdown;
      M.exclusionBreakdown = function (items) { var b = original(items); b.excluded = 0; return b; };
    }`);
    await assert.rejects(() => runParcours(page, ctx), /exclus-carte-differents-de-l-arbre/);
  });
});
