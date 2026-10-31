// ARTEFACT — Story 25.4 (AC8) : contrat d'écriture. Les écritures déclenchées depuis la vue C (aperçu, enregistrement,
// retour au mode automatique, réglage de publication, Appliquer, Republier, Supprimer) ont EXACTEMENT les mêmes
// routes, paramètres, valeurs et ordre d'opérations qu'avant la story : comparaison, clés triées, à la référence
// `tests/fixtures/story_25_4_corps_ecriture.json` relevée sur main AVANT tout changement. Le test échoue si un
// paramètre est ajouté, retiré ou renommé. Vrai code sur faux DOM ; identifiants fictifs (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { createUi, BRIDGE_UP } = require('./helpers/ui_harness');
const { SCENARIOS, runAll, serialize, WRITE_ACTIONS } = require('./helpers/write_scenarios');

const reference = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'fixtures', 'story_25_4_corps_ecriture.json'), 'utf8'));

/** Atteint le détail de l'équipement 1 de la pièce 7 par la vue C : ouverture de la pièce, sélection, lecture de l'arbre. */
function openInView(rooms, objectId, trees) {
  const ui = createUi(rooms);
  ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
  ui.openRoom(objectId);
  ui.selectEquipment(1, trees[0]);
  return ui;
}

describe('25.4 / AC8 — corps d’écriture identiques à la référence de main', () => {
  it('la référence couvre tous les scénarios et toutes les actions d’écriture', () => {
    assert.deepEqual(Object.keys(reference.scenarios), SCENARIOS.map((s) => s.name));
    const seen = new Set(Object.values(reference.scenarios).flat().map((w) => w.action));
    for (const action of WRITE_ACTIONS) assert.ok(seen.has(action), action);
  });

  it('chaque scénario rejoué sur la vue C produit les mêmes requêtes, dans le même ordre', async () => {
    const got = await runAll(openInView);
    for (const name of Object.keys(reference.scenarios)) {
      assert.deepEqual(got[name], reference.scenarios[name], name);
    }
  });

  it('le sérialiseur trie les clés (un paramètre ajouté, retiré ou renommé change le corps)', () => {
    assert.equal(serialize({ b: 2, a: 1 }), 'a=1&b=2');
    assert.notEqual(serialize({ action: 'x', eqId: 1 }), serialize({ action: 'x', eqId: 1, extra: 1 }));
  });

  // Story 25.8 : `saveRoomExclusion` est ajoutée à la politique comme écriture SIMULÉE déclarée (jamais une lecture autorisée) ;
  // les actions autorisées (lectures) et les verdicts existants sont inchangés : aucune ligne existante n’est retirée.
  it('lib/policy.mjs n’ajoute ni ne retire aucune action autorisée (aucune ligne retirée)', () => {
    const { execFileSync } = require('node:child_process');
    for (const base of ['main', 'origin/main']) {
      try {
        const diff = execFileSync('git', ['diff', base, '--', 'tests/e2e/gate/lib/policy.mjs'], { encoding: 'utf8' });
        assert.deepEqual(diff.split('\n').filter((l) => l.startsWith('-') && !l.startsWith('---')), []);
        return;
      } catch (error) {
        if (error.code === 'ERR_ASSERTION') throw error;
      }
    }
  });
});
