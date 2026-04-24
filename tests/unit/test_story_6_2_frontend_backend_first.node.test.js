'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const helpers = require('../../desktop/js/jeedom2ha_diagnostic_helpers.js');

function readDiagnosticJs() {
  const jsPath = path.resolve(__dirname, '../../desktop/js/jeedom2ha.js');
  return fs.readFileSync(jsPath, 'utf8');
}

test('6.2 / frontend — getDiagnosticReasonLabel lit uniquement cause_label backend', () => {
  const reason = helpers.getDiagnosticReasonLabel({
    reason_code: 'ambiguous_skipped',
    cause_label: 'Plusieurs types possibles — décision non automatique',
  });
  assert.equal(reason, 'Plusieurs types possibles — décision non automatique');

  const withoutBackendLabel = helpers.getDiagnosticReasonLabel({
    reason_code: 'ambiguous_skipped',
    cause_label: '',
  });
  assert.equal(withoutBackendLabel, '');
});

test('6.2 / frontend — resolveDiagnosticAction lit uniquement cause_action backend', () => {
  const action = helpers.resolveDiagnosticAction({
    cause_action: 'Choisir manuellement le type d’équipement',
    remediation: 'Ne doit pas être utilisée',
  });
  assert.equal(action.text, 'Choisir manuellement le type d’équipement');
  assert.equal(action.source, 'cause_action');
  assert.equal(action.showConfigLink, false);

  const noBackendAction = helpers.resolveDiagnosticAction({
    cause_action: '',
    remediation: 'Ne doit pas être utilisée',
  });
  assert.equal(noBackendAction.text, '');
  assert.equal(noBackendAction.source, 'none');
  assert.equal(noBackendAction.showConfigLink, false);
});

test('6.2 / frontend — jeedom2ha.js ne maintient plus de mapping local reason_code -> libellé', () => {
  const source = readDiagnosticJs();
  assert.doesNotMatch(source, /\breasonLabels\b/);
});

test('6.2 / frontend — jeedom2ha.js lit cause_label et cause_action fournis par le backend', () => {
  const source = readDiagnosticJs();
  assert.match(source, /eq\.cause_label/);
  assert.match(source, /eq\.cause_action/);
});
