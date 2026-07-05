/**
 * Story 15.1 — Tests JS : badge Energy (state_class/unit_of_measurement) dans buildDetailRow.
 *
 * Invariants vérifiés :
 * - AC1 : le badge Energy est construit à partir de eq.matched_commands (lecture backend stricte)
 * - AC2 : aucun badge par défaut/inventé quand state_class est absent
 * - AC3 : additif — la Section 2 (Typage Jeedom) conserve son rendu existant
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

test('15.1 — jeedom2ha.js construit un index energyByCmdId depuis eq.matched_commands', () => {
  const jsPath = path.resolve(__dirname, '../../desktop/js/jeedom2ha.js');
  const source = fs.readFileSync(jsPath, 'utf8');

  assert.ok(
    source.includes('eq.matched_commands'),
    'buildDetailRow doit lire eq.matched_commands (fourni par le backend)'
  );
  assert.ok(
    source.includes('energyByCmdId'),
    'un index cmd_id -> reason_details Energy doit être construit pour le rendu'
  );
  assert.ok(
    source.includes('mcEntry.state_class'),
    "l'index Energy ne doit retenir que les commandes avec state_class présent (pas de valeur par défaut)"
  );
});

test('15.1 — le badge Energy ne rend rien quand state_class est absent', () => {
  const jsPath = path.resolve(__dirname, '../../desktop/js/jeedom2ha.js');
  const source = fs.readFileSync(jsPath, 'utf8');

  // Le badge n'est ajouté que dans un bloc conditionnel sur energyInfo truthy.
  assert.match(
    source,
    /var energyInfo = energyByCmdId\[tt\.command_id\];\s*\n\s*if \(energyInfo\) \{/,
    'le badge Energy doit être conditionné à la présence de energyInfo, sans placeholder par défaut'
  );
});

test('15.1 — non-régression : la Section 2 Typage Jeedom garde son marqueur de titre', () => {
  const jsPath = path.resolve(__dirname, '../../desktop/js/jeedom2ha.js');
  const source = fs.readFileSync(jsPath, 'utf8');

  assert.ok(source.includes('{{Typage Jeedom}}'));
  assert.ok(source.includes('tt.logical_role'));
  assert.ok(source.includes('tt.command_id'));
});
