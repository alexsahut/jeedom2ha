// ARTEFACT — Story 16.8, CC-37 : `normalizeCommandRow` ne recopiait pas `covered` depuis
// l'arbre GET, donc `renderDiagnosticCell` (jeedom2ha_mapping_surface.js) recevait
// `row.covered === undefined`, jamais `=== false`, et retombait sur `diagnosticState()`
// (= 'blocking' pour une commande non couverte) au lieu du libellé « non couverte ».
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

// Vue diagnostic d'une commande non couverte par le mapping (`_decision_view(decision, None)`
// côté démon), identique à `uncoveredView()` des tests 16.8/19.3 existants.
function uncoveredView() {
  return {
    ha_entity_type: null,
    confidence: null,
    reason_code: null,
    projection_validity: { is_valid: false, reason_code: 'command_not_covered', missing_capabilities: [], missing_fields: [] },
    should_publish: false,
    publication_reason: 'command_not_covered',
  };
}

function readyView() {
  return {
    ha_entity_type: 'light',
    projection_validity: { is_valid: true, reason_code: null, missing_capabilities: [], missing_fields: [] },
    should_publish: true,
    publication_reason: 'sure',
  };
}

describe('CC-37 — normalizeCommandRow recopie covered', () => {
  it('covered: false est préservé', () => {
    const row = M.normalizeCommandRow({ jeedom_cmd_id: 1, covered: false });
    assert.strictEqual(row.covered, false);
  });

  it('covered: true est préservé', () => {
    const row = M.normalizeCommandRow({ jeedom_cmd_id: 2, covered: true });
    assert.strictEqual(row.covered, true);
  });

  it('covered absent (démon plus ancien) → null, jamais undefined', () => {
    const row = M.normalizeCommandRow({ jeedom_cmd_id: 3 });
    assert.strictEqual(row.covered, null);
  });
});

describe('CC-37 — une commande non couverte mène au libellé « non couverte », jamais à l’état bloquant', () => {
  it('covered=false + command_not_covered → shouldShowUncoveredLabel vrai (branche uncovered du renderer)', () => {
    const row = M.normalizeCommandRow({ jeedom_cmd_id: 4, covered: false, diagnostic: uncoveredView() });
    // Reproduit la condition exacte de renderDiagnosticCell (jeedom2ha_mapping_surface.js) :
    // avant le correctif, `row.covered` était `undefined`, donc cette condition était fausse
    // et le rendu retombait sur `diagnosticState()` = 'blocking'.
    assert.strictEqual(row.covered, false);
    assert.strictEqual(M.shouldShowUncoveredLabel(row.diagnostic), true);
  });

  it('sans le correctif (covered undefined), la même vue bascule à tort en « blocking »', () => {
    // Démontre la cause du bug : diagnosticState() seul, sans le garde `covered === false`,
    // classe une commande non couverte comme bloquante.
    assert.strictEqual(M.diagnosticState(uncoveredView()), 'blocking');
  });
});

describe('CC-37 — cohérence avec summarizePublication', () => {
  it('une commande non couverte n’est comptée ni prête ni bloquante dans la synthèse', () => {
    const tree = {
      commands: [
        M.normalizeCommandRow({ jeedom_cmd_id: 1, covered: true, diagnostic: readyView() }),
        M.normalizeCommandRow({ jeedom_cmd_id: 2, covered: false, diagnostic: uncoveredView() }),
      ],
    };
    const summary = M.summarizePublication(tree);
    assert.strictEqual(summary.ready_count, 1);
    assert.strictEqual(summary.blocking_count, 0);
    assert.strictEqual(summary.uncovered_count, 1);
  });
});
