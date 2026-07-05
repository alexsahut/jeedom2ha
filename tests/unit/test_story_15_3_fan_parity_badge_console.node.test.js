/**
 * Story 15.3 — Tests JS : badge "Parité FAN → switch" (console détaillée + vue Parc global).
 *
 * Invariants vérifiés :
 * - AC1 : le badge est affiché au niveau équipement quand fan_switch_parity === true
 * - AC2 : aucun badge par défaut/inventé quand fan_switch_parity est absent ou faux
 * - AC4 : additif — Section 2 (Typage Jeedom), badges Energy (15.1) et Streaming (15.2) gardent leur rendu
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const scopeSummary = require('../../desktop/js/jeedom2ha_scope_summary.js');

test('15.3 — jeedom2ha.js affiche le badge Parité FAN → switch uniquement quand fan_switch_parity === true', () => {
  const jsPath = path.resolve(__dirname, '../../desktop/js/jeedom2ha.js');
  const source = fs.readFileSync(jsPath, 'utf8');

  assert.ok(
    source.includes('fanParityBadgeHtml'),
    'un badge Parité FAN → switch additif doit être construit pour le rendu équipement'
  );
  assert.match(
    source,
    /if \(eq\.fan_switch_parity === true\) \{/,
    'le badge doit être conditionné strictement à fan_switch_parity === true, sans placeholder par défaut'
  );
});

test('15.3 — non-régression : badges Energy (15.1) et Streaming (15.2) gardent leur rendu', () => {
  const jsPath = path.resolve(__dirname, '../../desktop/js/jeedom2ha.js');
  const source = fs.readFileSync(jsPath, 'utf8');

  assert.ok(source.includes('{{Typage Jeedom}}'));
  assert.ok(source.includes('energyByCmdId'));
  assert.ok(source.includes('streamingByCmdId'));
});

test('15.3 — render(): badge "Parité FAN → switch" affiché sur la ligne équipement quand fan_switch_parity est vrai', () => {
  const model = {
    has_contract: true,
    global: {
      name: 'Parc global',
      status_room: '',
      counts: { total: 1, exclus: 0, inclus: 1, publies: 1, ecarts: 0 },
      streaming_actif: false,
      streaming_cibles_count: 0,
    },
    pieces: [
      {
        object_id: 1,
        object_name: 'Local technique',
        status_room: '',
        counts: { total: 1, exclus: 0, inclus: 1, publies: 1, ecarts: 0 },
        equipements: [
          {
            eq_id: 67,
            name: 'Pompe filtration',
            perimetre: 'inclus',
            statut: 'publie',
            ecart: false,
            fan_switch_parity: true,
            actions_ha: null,
            counts: { total: 1, exclus: 0, inclus: 1, publies: 1, ecarts: 0 },
          },
        ],
      },
    ],
  };

  const html = scopeSummary.render(model);

  assert.match(html, /Parité FAN/);
});

test('15.3 — render(): aucun badge "Parité FAN → switch" quand fan_switch_parity est faux ou absent', () => {
  const model = {
    has_contract: true,
    global: {
      name: 'Parc global',
      status_room: '',
      counts: { total: 1, exclus: 0, inclus: 1, publies: 1, ecarts: 0 },
      streaming_actif: false,
      streaming_cibles_count: 0,
    },
    pieces: [
      {
        object_id: 1,
        object_name: 'Salon',
        status_room: '',
        counts: { total: 1, exclus: 0, inclus: 1, publies: 1, ecarts: 0 },
        equipements: [
          {
            eq_id: 583,
            name: 'Prise standard',
            perimetre: 'inclus',
            statut: 'publie',
            ecart: false,
            fan_switch_parity: false,
            actions_ha: null,
            counts: { total: 1, exclus: 0, inclus: 1, publies: 1, ecarts: 0 },
          },
        ],
      },
    ],
  };

  const html = scopeSummary.render(model);

  assert.doesNotMatch(html, /Parité FAN/);
});
