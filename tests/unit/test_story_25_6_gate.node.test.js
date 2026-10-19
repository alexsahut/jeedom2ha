// ARTEFACT — Story 25.6 (AC11) : le gate 20-0 est adapté à la portée, jamais affaibli. Le registre de 25.4 reste le plancher
// (test_story_25_4_gate, inchangé) ; ce test ajoute : les étiquettes et clés `record` nouvelles de l'étape 2 existent, le
// parcours passe en vrai Chromium sur la page livrée et enregistre la portée, `lib/policy.mjs` est intact. Aucune box (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView, gate } = require('./helpers/workview_browser');

const root = path.join(__dirname, '..', '..');
const source = fs.readFileSync(path.join(root, 'tests/e2e/gate/parcours/vue-maitre-detail-c.mjs'), 'utf8');

test('25.6 gate — étape 2 : étiquettes d’erreur et clés record nouvelles présentes, étapes 1 à 9 gardées', () => {
  for (const label of ['portee-piece-seule', 'requete-pendant-elargissement', 'arbre-pieces-differentes-de-la-page', 'reperes-arbre-differents-de-la-page']) {
    assert.ok(source.includes(`'${label}'`), label);
  }
  for (const key of ['portee_ouverture', 'pieces_arbre_portee_piece', 'pieces_arbre', 'reperes_bloques']) {
    assert.ok(source.includes(`'${key}'`), key);
  }
  for (const step of [1, 2, 3, 4, 6, 7, 8, 9]) assert.match(source, new RegExp(`atStep\\(helpers, ${step},`), 'étape ' + step);
});

test('25.6 gate — lib/policy.mjs n’est pas modifié par la story (Story 25.8 : ajout seul de saveRoomExclusion, aucune ligne retirée)', () => {
  for (const base of ['main', 'origin/main']) {
    try {
      const diff = execFileSync('git', ['diff', '-U0', base, '--', 'tests/e2e/gate/lib/policy.mjs'], { encoding: 'utf8', cwd: root });
      assert.deepEqual(diff.split('\n').filter((l) => l.startsWith('-') && !l.startsWith('---')), [], 'policy.mjs : aucune ligne retirée');
      return;
    } catch (error) {
      if (error.code === 'ERR_ASSERTION') throw error;
    }
  }
});

test('25.6 gate réel — le parcours adapté passe sur la page livrée et enregistre la portée ; une portée « toutes » à l’ouverture le fait échouer', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    const parcours = await import(gate('parcours', 'vue-maitre-detail-c.mjs'));
    const { normalizeParcoursRecord } = await import(gate('lib', 'report.mjs'));
    const recorded = {};
    const helpers = {
      record: (key, value) => { const [k, v] = normalizeParcoursRecord(key, value); recorded[k] = v; },
      journalEntries: () => ctx.journal,
    };
    await parcours.run(page, { helpers });
    assert.equal(recorded.portee_ouverture, 'piece');
    assert.equal(recorded.pieces_arbre_portee_piece, 1);
    assert.equal(recorded.requetes_pendant_elargissement, 0);
    assert.ok(recorded.pieces_arbre > 1, 'après élargissement : toutes les pièces');
    assert.deepEqual(ctx.errors, []);
  });
  // Contrôle négatif : une vue qui ouvrirait toutes les pièces (portée non appliquée) est refusée par l'étape 2.
  await withRealView(t, {}, async (page) => {
    await page.evaluate(() => {
      const open = window.Jeedom2haWorkviewInstance.open;
      window.j2haOpenRoom = (id) => open({ room: id, scope: 'toutes' });
    });
    const parcours = await import(gate('parcours', 'vue-maitre-detail-c.mjs'));
    const helpers = { record: () => {}, journalEntries: () => [] };
    await assert.rejects(() => parcours.run(page, { helpers }), /portee-piece-seule/);
  });
});
