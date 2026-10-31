// ARTEFACT — Story 25.2 (AC4) : la source de vérité de l'état reste `resolveEquipmentState`. Alimentée
// par l'entrée agrégée de GET /system/equipment_states (liste blanche) ou par l'arbre unitaire complet
// de GET /system/mapping_overrides/{eq_id}, elle rend le même état et les mêmes compteurs.
// Fixtures fictives (CC-48) générées par resources/daemon/tests/unit/test_story_25_2_route_agregee.py
// (tests/fixtures/story_25_2_parite_etat.json). Aucune modification de desktop/.
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

const FIXTURE = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'fixtures', 'story_25_2_parite_etat.json'), 'utf8'));
const STATES = ['published', 'to_apply', 'blocked', 'excluded', 'disabled', 'nothing_to_publish'];
const ENABLED_CASES = [true, false, undefined];
const clone = (value) => JSON.parse(JSON.stringify(value));

function assertParity(fullTree, aggregated, enabled, label) {
  assert.deepEqual(M.resolveEquipmentState(aggregated, enabled), M.resolveEquipmentState(fullTree, enabled), label);
  assert.deepEqual(M.summarizeEquipmentCounters(aggregated, enabled), M.summarizeEquipmentCounters(fullTree, enabled), label);
}

describe('Story 25.2 — parité de l’état : arbre complet vs entrée agrégée', () => {
  it('chaque équipement du corpus, pour enabled ∈ {true, false, undefined}', () => {
    for (const [eqId, entry] of Object.entries(FIXTURE)) {
      for (const enabled of ENABLED_CASES) {
        assertParity(entry.tree, entry.aggregated, enabled, `eq ${eqId} enabled=${enabled}`);
      }
    }
  });

  it('le corpus couvre au moins 4 des 6 états de D1 (publié, à appliquer, exclu, désactivé…)', () => {
    const seen = new Set();
    for (const entry of Object.values(FIXTURE)) {
      for (const enabled of [true, false]) seen.add(M.resolveEquipmentState(entry.aggregated, enabled).state);
    }
    seen.forEach((state) => assert.ok(STATES.includes(state), state));
    for (const state of ['published', 'to_apply', 'excluded', 'disabled']) assert.ok(seen.has(state), state);
  });

  it('l’état de l’entrée agrégée suit l’activation Jeedom fournie par l’appelant, pas le démon', () => {
    const entry = FIXTURE['104'];
    assert.equal(entry.enabled, false);
    // Le démon porte l'inactivité par `disabled_eqlogic` (décision déjà portée, Q2) ; `enabled` vient de l'appelant.
    assert.equal(M.resolveEquipmentState(entry.aggregated, undefined).state, 'disabled');
    assert.equal(M.resolveEquipmentState(FIXTURE['110'].aggregated, true).state, 'excluded');
    assert.equal(M.resolveEquipmentState(FIXTURE['110'].aggregated, false).state, 'disabled');
  });

  it('croisements : présence inconnue, jamais synchronisé, désactivé + exclu, secondaire seul publié', () => {
    const mutations = {
      'présence null': (tree) => { tree.sync_status.published_in_ha = null; },
      'rien de publié': (tree) => {
        tree.sync_status.published_in_ha = false;
        tree.commands.forEach((c) => { c.published_in_ha = false; });
      },
      'override en attente': (tree) => { tree.sync_status.override_pending = true; },
      'entité en attente': (tree) => { tree.entities.forEach((e) => { e.override_pending = true; }); },
      'jamais synchronisé': (tree) => {
        tree.sync_status.synced_should_publish = null;
        tree.sync_status.published_in_ha = false;
      },
      'dernière commande seule publiée': (tree) => {
        tree.commands.forEach((c, i) => { c.published_in_ha = i === tree.commands.length - 1; });
      },
    };
    for (const [eqId, entry] of Object.entries(FIXTURE)) {
      for (const [name, mutate] of Object.entries(mutations)) {
        const tree = clone(entry.tree);
        const aggregated = clone(entry.aggregated);
        mutate(tree);
        mutate(aggregated);
        for (const enabled of ENABLED_CASES) assertParity(tree, aggregated, enabled, `eq ${eqId} ${name} enabled=${enabled}`);
      }
    }
    // Désactivé + exclu : « Désactivé » prime (R3), identique sur les deux entrées.
    const excluded = FIXTURE['110'];
    assert.equal(M.resolveEquipmentState(excluded.aggregated, true).state, 'excluded');
    assert.equal(M.resolveEquipmentState(excluded.aggregated, false).state, 'disabled');
    assertParity(excluded.tree, excluded.aggregated, false, 'désactivé + exclu');
  });

  it('l’entrée agrégée ne porte que la liste blanche (aucun état résolu, aucun enabled)', () => {
    const forbidden = new Set(['state', 'blocked_mention', 'by_state', 'defects', 'counts', 'enabled', 'category', 'to_apply', 'ignored']);
    const walk = (node) => {
      if (Array.isArray(node)) return node.forEach(walk);
      if (node && typeof node === 'object') {
        Object.keys(node).forEach((key) => { assert.ok(!forbidden.has(key), key); walk(node[key]); });
      }
    };
    Object.values(FIXTURE).forEach((entry) => walk(entry.aggregated));
  });
});
