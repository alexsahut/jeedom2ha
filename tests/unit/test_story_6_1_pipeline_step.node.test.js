/**
 * Story 6.1 — Tests JS : pipeline_step_visible, isStep5Failed, cause canonique.
 *
 * Invariants vérifiés :
 * - AC1 : l'étape visible provient du backend (pas de calcul local depuis reason_code)
 * - AC2 / I7 : cause canonique = traceability.decision_trace.reason_code uniquement
 * - AC4 : isStep5Failed détecte correctement le cas deux blocs séparés
 * - AC5 : contrat additif — les helpers existants restent inchangés
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const helpers = require('../../desktop/js/jeedom2ha_diagnostic_helpers.js');

// ---------------------------------------------------------------------------
// AC1 — Étape visible provient du backend : vérification structurelle du JS
// ---------------------------------------------------------------------------

test('6.1 / AC1 — jeedom2ha.js lit pipeline_step_visible depuis le backend sans recalcul', () => {
  const jsPath = path.resolve(__dirname, '../../desktop/js/jeedom2ha.js');
  const source = fs.readFileSync(jsPath, 'utf8');

  // Le JS doit lire eq.pipeline_step_visible directement
  assert.ok(
    source.includes('eq.pipeline_step_visible'),
    'buildDetailRow doit lire eq.pipeline_step_visible (fourni par le backend)'
  );

  // Le JS ne doit pas déduire l'étape depuis reason_code ou status_code (anti-pattern I17)
  // On vérifie l'absence d'un mapping local reason_code → step
  assert.ok(
    !source.match(/reason_code.*step_visible|status_code.*step_visible|step_visible.*reason_code/),
    'pipeline_step_visible ne doit jamais être calculé localement depuis reason_code'
  );
});

test('6.1 / AC1 — PIPELINE_STEP_LABELS défini dans jeedom2ha.js avec 5 entrées exactes', () => {
  const jsPath = path.resolve(__dirname, '../../desktop/js/jeedom2ha.js');
  const source = fs.readFileSync(jsPath, 'utf8');

  assert.ok(
    source.includes('PIPELINE_STEP_LABELS'),
    'PIPELINE_STEP_LABELS doit être défini dans jeedom2ha.js'
  );

  // Vérifier que les 5 clés d'étapes sont présentes
  for (var step = 1; step <= 5; step++) {
    assert.ok(
      source.includes('\n        ' + step + ':') || source.includes('\n        ' + step + ' :')
        || new RegExp('PIPELINE_STEP_LABELS[\\s\\S]{0,500}' + step + '\\s*:').test(source),
      'PIPELINE_STEP_LABELS doit contenir l\'étape ' + step
    );
  }
});

// ---------------------------------------------------------------------------
// AC2 / I7 — Cause canonique = traceability.decision_trace.reason_code
// ---------------------------------------------------------------------------

test('6.1 / AC2 — getCanonicalDiagnosticCause retourne decision_trace.reason_code', () => {
  const eq = {
    reason_code: 'discovery_publish_failed',  // top-level (ne doit PAS être la cause principale)
    traceability: {
      decision_trace: { reason_code: 'published' },
      publication_trace: {
        last_discovery_publish_result: 'failed',
        technical_reason_code: 'discovery_publish_failed',
      },
    },
  };

  const cause = helpers.getCanonicalDiagnosticCause(eq);
  assert.equal(cause, 'published', 'La cause canonique doit être decision_trace.reason_code');
});

test('6.1 / I7 — getCanonicalDiagnosticCause ne retourne jamais technical_reason_code', () => {
  const eq = {
    reason_code: 'discovery_publish_failed',
    traceability: {
      decision_trace: { reason_code: 'sure' },
      publication_trace: {
        last_discovery_publish_result: 'failed',
        technical_reason_code: 'discovery_publish_failed',
      },
    },
  };

  const cause = helpers.getCanonicalDiagnosticCause(eq);
  assert.notEqual(cause, 'discovery_publish_failed', 'I7 : technical_reason_code ne peut pas être la cause canonique');
  assert.notEqual(cause, 'local_availability_publish_failed', 'I7 : technical_reason_code ne peut pas être la cause canonique');
});

test('6.1 / AC2 — getCanonicalDiagnosticCause retourne chaîne vide si traceability absent', () => {
  assert.equal(helpers.getCanonicalDiagnosticCause({}), '');
  assert.equal(helpers.getCanonicalDiagnosticCause(null), '');
  assert.equal(helpers.getCanonicalDiagnosticCause({ traceability: {} }), '');
});

// ---------------------------------------------------------------------------
// AC4 — isStep5Failed : détection correcte du cas deux blocs
// ---------------------------------------------------------------------------

test('6.1 / AC4 — isStep5Failed retourne true pour step 5 + failed', () => {
  assert.equal(helpers.isStep5Failed(5, 'failed'), true);
});

test('6.1 / AC4 — isStep5Failed retourne false pour step 5 + success', () => {
  assert.equal(helpers.isStep5Failed(5, 'success'), false);
});

test('6.1 / AC4 — isStep5Failed retourne false pour step 5 + not_attempted', () => {
  assert.equal(helpers.isStep5Failed(5, 'not_attempted'), false);
});

test('6.1 / AC4 — isStep5Failed retourne false pour step < 5 même si pubResult failed', () => {
  // Seul step 5 peut avoir un résultat technique — les autres étapes ne publient pas
  assert.equal(helpers.isStep5Failed(4, 'failed'), false);
  assert.equal(helpers.isStep5Failed(3, 'failed'), false);
  assert.equal(helpers.isStep5Failed(1, 'failed'), false);
});

test('6.1 / AC4 — isStep5Failed retourne false pour step null ou undefined', () => {
  assert.equal(helpers.isStep5Failed(null, 'failed'), false);
  assert.equal(helpers.isStep5Failed(undefined, 'failed'), false);
});

// ---------------------------------------------------------------------------
// AC4 — Rendu deux blocs vérifié au niveau structurel dans jeedom2ha.js
// ---------------------------------------------------------------------------

test('6.1 / AC4 — jeedom2ha.js rend deux blocs séparés pour step 5 failed', () => {
  const jsPath = path.resolve(__dirname, '../../desktop/js/jeedom2ha.js');
  const source = fs.readFileSync(jsPath, 'utf8');

  // Vérifier la présence des deux blocs
  assert.ok(
    source.includes('Décision pipeline'),
    'Le bloc Décision pipeline doit être présent dans buildDetailRow'
  );
  assert.ok(
    source.includes('Résultat technique'),
    'Le bloc Résultat technique doit être présent dans buildDetailRow'
  );

  // Les deux blocs sont rendus dans le même contexte isStep5Failed
  const step5Block = source.match(/isStep5Failed[\s\S]{0,2000}Décision pipeline[\s\S]{0,2000}Résultat technique/);
  assert.ok(step5Block, 'Les deux blocs doivent être dans le même bloc conditionnel isStep5Failed');
});

// ---------------------------------------------------------------------------
// AC5 — Non-régression helpers existants
// ---------------------------------------------------------------------------

test('6.1 / AC5 — helpers existants non modifiés : filterInScopeEquipments', () => {
  const eqs = [
    { eq_id: 1, perimetre: 'inclus' },
    { eq_id: 2, perimetre: 'exclu_par_piece' },
  ];
  const result = helpers.filterInScopeEquipments(eqs);
  assert.equal(result.length, 1);
  assert.equal(result[0].eq_id, 1);
});

test('6.1 / AC5 — helpers existants non modifiés : getDiagnosticColumns', () => {
  const cols = helpers.getDiagnosticColumns();
  assert.deepEqual(cols, ['Piece', 'Nom', 'Ecart', 'Statut', 'Confiance', 'Raison']);
});

test('6.1 / AC5 — helpers existants non modifiés : getEcartBadgeHtml', () => {
  assert.ok(helpers.getEcartBadgeHtml(true).includes('warning'));
  assert.ok(helpers.getEcartBadgeHtml(false).includes('success'));
});
