// ARTEFACT — Story 25.2 (AC4) : `resolveEquipmentState` et `summarizeEquipmentCounters`, sans modification, donnent
// le même résultat sur l'arbre complet (GET /system/mapping_overrides/{eq_id}) et sur l'entrée agrégée correspondante
// (GET /system/equipment_states). Fixtures fictives générées par le démon (tests/fixtures/story_25_2_etat_parite.json,
// régénérées par `J2HA_UPDATE_SNAPSHOT=1 pytest resources/daemon/tests/unit/test_story_25_2_route_agregee.py -k parity`).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

const FIXTURE = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'fixtures', 'story_25_2_etat_parite.json'), 'utf8'));
const ENABLED = [true, false, undefined];

describe('25.2 — parité d\'état arbre complet / entrée agrégée', () => {
  const ids = Object.keys(FIXTURE);

  it('le corpus couvre plusieurs états distincts', () => {
    const states = new Set(ids.map((id) => M.resolveEquipmentState(FIXTURE[id].tree, true).state));
    assert.ok(states.size >= 4, 'états couverts : ' + Array.from(states).join(','));
  });

  for (const id of ids) {
    for (const enabled of ENABLED) {
      it('eq ' + id + ' enabled=' + enabled, () => {
        const { tree, aggregate } = FIXTURE[id];
        assert.deepEqual(M.resolveEquipmentState(aggregate, enabled), M.resolveEquipmentState(tree, enabled));
        assert.deepEqual(M.summarizeEquipmentCounters(aggregate, enabled), M.summarizeEquipmentCounters(tree, enabled));
      });
    }
  }
});
