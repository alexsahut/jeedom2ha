// Story 19.3 (P1, relecture ClaudeBox PR #176 tour 2) — `covered:false` ne doit PAS toujours
// afficher le libellé générique « non couverte par un mapping » : une commande exclue ou
// inéligible en amont (I1/I4) porte aussi `covered:false`, mais avec une VRAIE cause à
// afficher (shouldShowUncoveredLabel). Le libellé générique ne sort que pour une commande
// réellement non couverte (aucune cause : `view=null`, ou `publication_reason:
// 'command_not_covered'`).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

function diagnosticView(reason, extra) {
  return Object.assign(
    {
      ha_entity_type: null,
      projection_validity: { is_valid: false, reason_code: null, missing_capabilities: [], missing_fields: [] },
      should_publish: false,
      publication_reason: reason,
    },
    extra || {}
  );
}

// Story 4.3 (topology.py `_EXCLUSION_SOURCE_TO_REASON`) + evaluate_equipment.py
// (`_ELIGIBILITY_REASON_ALIAS`) — les 6 raisons d'inéligibilité/exclusion amont qui peuvent
// accompagner `covered:false` avec une vraie cause à afficher.
const ELIGIBILITY_REASON_CODES = [
  'excluded_eqlogic',
  'excluded_plugin',
  'excluded_object',
  'disabled_eqlogic',
  'no_commands',
  'no_generic_type_configured',
];

describe('19.3 / P1 — shouldShowUncoveredLabel', () => {
  for (const code of ELIGIBILITY_REASON_CODES) {
    it(`covered:false + publication_reason="${code}" -> affiche le VRAI diagnostic (pas le libellé générique)`, () => {
      assert.strictEqual(M.shouldShowUncoveredLabel(diagnosticView(code)), false);
    });
  }

  it('covered:false + publication_reason="command_not_covered" -> libellé générique « non couverte »', () => {
    assert.strictEqual(M.shouldShowUncoveredLabel(diagnosticView('command_not_covered')), true);
  });

  it('covered:false + view=null (aucun diagnostic) -> libellé générique « non couverte »', () => {
    assert.strictEqual(M.shouldShowUncoveredLabel(null), true);
  });

  it('covered:false + view=undefined -> libellé générique « non couverte »', () => {
    assert.strictEqual(M.shouldShowUncoveredLabel(undefined), true);
  });
});

describe('19.3 / P1 — readPreviewAuto (miroir de readPreviewOverridden pour la branche !covered)', () => {
  it('extrait payload.payload.auto quand présent', () => {
    const auto = { ha_entity_type: 'switch', should_publish: false, publication_reason: 'excluded_eqlogic' };
    const result = { payload: { covered: false, auto: auto } };
    assert.deepStrictEqual(M.readPreviewAuto(result), auto);
  });

  it('extrait payload.auto quand le payload est déjà déplié (pas de double-emballage)', () => {
    const auto = { ha_entity_type: 'light' };
    assert.deepStrictEqual(M.readPreviewAuto({ covered: false, auto: auto }), auto);
  });

  it('retourne null quand auto est absent', () => {
    assert.strictEqual(M.readPreviewAuto({ payload: { covered: false } }), null);
  });

  it('retourne null quand auto est malformé (pas un objet)', () => {
    assert.strictEqual(M.readPreviewAuto({ payload: { auto: 'switch' } }), null);
  });

  it('retourne null sur une entrée vide/absente', () => {
    assert.strictEqual(M.readPreviewAuto(null), null);
    assert.strictEqual(M.readPreviewAuto(undefined), null);
    assert.strictEqual(M.readPreviewAuto({}), null);
  });
});
