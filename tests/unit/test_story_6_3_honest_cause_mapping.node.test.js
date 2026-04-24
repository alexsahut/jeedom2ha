'use strict';

/**
 * Story 6.3 — Sémantique honnête cause_label / cause_action (frontend).
 *
 * Vérifie que :
 * - resolveDiagnosticAction retourne text='' quand cause_action est null (backend null)
 * - jeedom2ha.js affiche le message standardisé AC4 ("Aucune action utilisateur directe possible")
 *   pour tout cause_action null — sans logique locale de mapping reason_code → libellé
 * - le faux CTA "Choisir manuellement le type d'équipement" n'est plus présent dans le source JS
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const helpers = require('../../desktop/js/jeedom2ha_diagnostic_helpers.js');

function readDiagnosticJs() {
  const jsPath = path.resolve(__dirname, '../../desktop/js/jeedom2ha.js');
  return fs.readFileSync(jsPath, 'utf8');
}

// AC4 — cause_action null → text vide dans le helper (la couche d'affichage gère le fallback)
test('6.3 / AC4 — resolveDiagnosticAction retourne text vide quand cause_action est null', () => {
  const action = helpers.resolveDiagnosticAction({ cause_action: null });
  assert.equal(action.text, '');
  assert.equal(action.source, 'none');
  assert.equal(action.showConfigLink, false);
});

// AC4 — le message standardisé est bien dans la source JS de rendu (pas de silence)
test('6.3 / AC4 — jeedom2ha.js affiche "Aucune action utilisateur directe possible" pour cause_action null', () => {
  const source = readDiagnosticJs();
  assert.match(source, /Aucune action utilisateur directe possible/,
    'Le message standardisé AC4 doit apparaître dans jeedom2ha.js');
});

// AC4 — le faux CTA "Choisir manuellement" ne doit plus apparaître comme libellé hardcodé
test('6.3 / AC4 — le faux CTA "Choisir manuellement le type d\'équipement" est absent du source JS', () => {
  const source = readDiagnosticJs();
  assert.doesNotMatch(source, /Choisir manuellement le type d.équipement/,
    'Le faux CTA ne doit plus être présent dans jeedom2ha.js');
});

// AC4 — pas de mapping local reason_code → libellé côté frontend
test('6.3 / AC4 — jeedom2ha.js ne maintient pas de mapping local reason_code vers libellé d\'action', () => {
  const source = readDiagnosticJs();
  assert.doesNotMatch(source, /\bcauseLabels\b/);
  assert.doesNotMatch(source, /\bactionLabels\b/);
  assert.doesNotMatch(source, /ambiguous_skipped.*Choisir/);
});

// AC1 — getDiagnosticReasonLabel lit toujours cause_label backend
test('6.3 / AC1 — getDiagnosticReasonLabel lit cause_label backend (non vide)', () => {
  const label = helpers.getDiagnosticReasonLabel({
    reason_code: 'ha_missing_command_topic',
    cause_label: 'Projection HA incomplète — commande requise absente',
  });
  assert.equal(label, 'Projection HA incomplète — commande requise absente');
});
