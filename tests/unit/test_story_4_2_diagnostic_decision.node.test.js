/**
 * Story 4.2 — Diagnostic de la décision : surface visible non ambiguë.
 *
 * On teste un helper pur dérivé de la vraie modal pour verrouiller le cas
 * "backend correct mais libellé visible ambigu".
 */

const test = require('node:test');
const assert = require('node:assert/strict');

const helpers = require('../../desktop/js/jeedom2ha_diagnostic_helpers.js');

test('4.2 / AC4 — la raison visible privilégie cause_label pour low_confidence', () => {
  const eq = {
    reason_code: 'low_confidence',
    cause_label: 'Confiance insuffisante pour la politique active',
  };

  const reason = helpers.getDiagnosticReasonLabel(eq);
  assert.equal(reason, 'Confiance insuffisante pour la politique active');
  assert.doesNotMatch(reason, /low_confidence/);
});

test('4.2 / AC2 — la raison visible distingue le hors-scope produit du mapping', () => {
  const eq = {
    reason_code: 'ha_component_not_in_product_scope',
    cause_label: 'Composant Home Assistant non ouvert dans ce cycle',
  };

  const reason = helpers.getDiagnosticReasonLabel(eq);
  assert.equal(reason, 'Composant Home Assistant non ouvert dans ce cycle');
  assert.notEqual(reason, 'Aucun mapping compatible trouvé');
  assert.notEqual(reason, 'Cause inconnue');
});

test('4.2 / AC3 — l action recommandée privilégie cause_action et désactive le CTA de configuration', () => {
  const eq = {
    cause_action: "Aucune action côté Jeedom : ce composant n'est pas encore pris en charge dans le cycle courant.",
    remediation: 'Configurer les types génériques dans Jeedom',
    eq_type_name: 'virtual',
  };

  const action = helpers.resolveDiagnosticAction(eq);
  assert.equal(
    action.text,
    "Aucune action côté Jeedom : ce composant n'est pas encore pris en charge dans le cycle courant."
  );
  assert.equal(action.showConfigLink, false);
});

test('4.2 / AC6 — sans cause_action, aucune action locale n est recalculée', () => {
  const eq = {
    cause_action: '',
    remediation: 'Configurer les types génériques dans Jeedom',
    eq_type_name: 'virtual',
  };

  const action = helpers.resolveDiagnosticAction(eq);
  assert.equal(action.text, '');
  assert.equal(action.showConfigLink, false);
});

test('4.2 / AC6 — le cas backend correct mais surface ambiguë est explicitement empêché', () => {
  const eq = {
    reason_code: 'low_confidence',
    cause_label: 'Confiance insuffisante pour la politique active',
  };

  const reason = helpers.getDiagnosticReasonLabel(eq);
  assert.equal(reason, 'Confiance insuffisante pour la politique active');
});
