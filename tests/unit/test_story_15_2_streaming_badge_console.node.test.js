/**
 * Story 15.2 — Tests JS : badge Streaming actif (per-commande + résumé global).
 *
 * Invariants vérifiés :
 * - AC1 : le badge Streaming actif est construit à partir de eq.matched_commands (lecture backend stricte)
 * - AC2 : aucun badge par défaut/inventé quand streaming est absent
 * - AC3 : le résumé global expose streaming_actif/streaming_cibles_count
 * - AC4 : additif — la Section 2 (Typage Jeedom) et le badge Energy (15.1) gardent leur rendu existant
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const scopeSummary = require('../../desktop/js/jeedom2ha_scope_summary.js');

test('15.2 — jeedom2ha.js construit un index streamingByCmdId depuis eq.matched_commands', () => {
  const jsPath = path.resolve(__dirname, '../../desktop/js/jeedom2ha.js');
  const source = fs.readFileSync(jsPath, 'utf8');

  assert.ok(
    source.includes('streamingByCmdId'),
    'un index cmd_id -> streaming doit être construit pour le rendu'
  );
  assert.ok(
    source.includes('mcEntry.streaming === true'),
    "l'index streaming ne doit retenir que les commandes avec streaming === true (pas de valeur par défaut)"
  );
});

test('15.2 — le badge Streaming actif ne rend rien quand streaming est absent', () => {
  const jsPath = path.resolve(__dirname, '../../desktop/js/jeedom2ha.js');
  const source = fs.readFileSync(jsPath, 'utf8');

  assert.match(
    source,
    /if \(streamingByCmdId\[tt\.command_id\]\) \{/,
    'le badge Streaming actif doit être conditionné à la présence dans streamingByCmdId, sans placeholder par défaut'
  );
});

test('15.2 — non-régression : badge Energy (15.1) et Section 2 Typage Jeedom gardent leur rendu', () => {
  const jsPath = path.resolve(__dirname, '../../desktop/js/jeedom2ha.js');
  const source = fs.readFileSync(jsPath, 'utf8');

  assert.ok(source.includes('{{Typage Jeedom}}'));
  assert.ok(source.includes('energyByCmdId'));
  assert.ok(source.includes('mcEntry.state_class'));
});

test('15.2 — render(): badge global "Streaming actif" affiché uniquement quand streaming_actif est vrai', () => {
  const model = {
    has_contract: true,
    global: {
      name: 'Parc global',
      status_room: '',
      counts: { total: 4, exclus: 1, inclus: 3, publies: 2, ecarts: 0 },
      streaming_actif: true,
      streaming_cibles_count: 7,
    },
    pieces: [],
  };

  const html = scopeSummary.render(model);

  assert.match(html, /Streaming actif/);
  assert.match(html, /7/);
});

test('15.2 — render(): aucun badge global Streaming actif quand streaming_actif est faux', () => {
  const model = {
    has_contract: true,
    global: {
      name: 'Parc global',
      status_room: '',
      counts: { total: 4, exclus: 1, inclus: 3, publies: 2, ecarts: 0 },
      streaming_actif: false,
      streaming_cibles_count: 0,
    },
    pieces: [],
  };

  const html = scopeSummary.render(model);

  assert.doesNotMatch(html, /Streaming actif/);
});
