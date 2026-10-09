// ARTEFACT — Story 20.3 (AC3, AC7, Q1=A) : compteurs de la pièce ouverte, dénombrés
// uniquement à partir des arbres du démon (evaluate_equipment()) ; aucune décision recalculée.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

function view(reason, valid, publish) {
  return {
    ha_entity_type: valid ? 'light' : null,
    projection_validity: { is_valid: valid, reason_code: valid ? null : reason, missing_capabilities: [], missing_fields: [] },
    should_publish: publish,
    publication_reason: reason,
  };
}
const READY = view('sure', true, true);
const BLOCKING = view('projection_invalid', false, false);
const UNCOVERED = view('command_not_covered', false, false);
const EXCLUDED_BY_USER = view('publication_excluded_eqlogic', false, false);
const DISABLED = view('disabled_eqlogic', false, false);

function tree(id, diags, equipmentDecision) {
  return {
    jeedom_eq_id: id,
    mapped: true,
    equipment_decision: equipmentDecision || null,
    commands: diags.map((d, i) => ({ jeedom_cmd_id: id * 100 + i, cmd_name: 'C' + i, diagnostic: d })),
  };
}

describe('20.3 / AC3 — summarizeRoom', () => {
  it('compte équipements publiés / exclus / désactivés / à corriger et commandes prêtes / bloquantes / non couvertes', () => {
    const s = M.summarizeRoom([
      tree(1, [READY, READY]),                 // publié
      tree(2, [READY, BLOCKING, UNCOVERED]),   // publié partiellement + à corriger
      tree(3, [BLOCKING]),                     // à corriger
      tree(4, [EXCLUDED_BY_USER]),             // exclu
      tree(5, [DISABLED]),                     // désactivé
    ], 5);
    assert.deepEqual(
      [s.equipments_published, s.equipments_excluded, s.equipments_disabled, s.equipments_to_fix],
      [2, 1, 1, 2]
    );
    assert.deepEqual([s.commands_ready, s.commands_blocking, s.commands_uncovered], [3, 2, 1]);
    assert.equal(s.equipments_read, 5);
  });

  it('une exclusion posée par l’utilisateur est comptée « exclue », jamais « à corriger »', () => {
    const s = M.summarizeRoom([tree(1, [EXCLUDED_BY_USER, EXCLUDED_BY_USER])], 1);
    assert.equal(s.equipments_excluded, 1);
    assert.equal(s.equipments_to_fix, 0);
    assert.equal(s.commands_blocking, 0);
  });

  it('une commande non couverte n’est jamais comptée bloquante', () => {
    const s = M.summarizeRoom([tree(1, [READY, UNCOVERED])], 1);
    assert.equal(s.commands_blocking, 0);
    assert.equal(s.commands_uncovered, 1);
    assert.equal(s.equipments_to_fix, 0);
  });

  it('un équipement désactivé n’est jamais compté bloquant ni à corriger', () => {
    const s = M.summarizeRoom([tree(1, [DISABLED, DISABLED])], 1);
    assert.equal(s.equipments_disabled, 1);
    assert.equal(s.equipments_to_fix, 0);
    assert.equal(s.commands_blocking, 0);
  });

  it('équipement exclu sans commande : lu dans equipment_decision (20.2 AC8)', () => {
    const s = M.summarizeRoom([tree(1, [], EXCLUDED_BY_USER), tree(2, [], DISABLED)], 2);
    assert.equal(s.equipments_excluded, 1);
    assert.equal(s.equipments_disabled, 1);
  });

  it('arbres non lus : signalés, non comptés', () => {
    const s = M.summarizeRoom([tree(1, [READY])], 3);
    assert.equal(s.equipments_read, 1);
    assert.equal(M.buildRoomCounterLabels(s).unread, '2 équipements non lus');
  });

  it('entrée invalide : zéro partout, sans exception', () => {
    const s = M.summarizeRoom(null, 0);
    assert.equal(s.equipments_published + s.commands_ready, 0);
    assert.equal(M.buildRoomCounterLabels(s).unread, '');
  });
});

describe('20.3 / AC3 — libellés d’unité', () => {
  it('chaque compteur dit son unité (équipement ou commande) avec accord singulier / pluriel', () => {
    const labels = M.buildRoomCounterLabels({
      equipments_total: 4, equipments_read: 4,
      equipments_published: 1, equipments_excluded: 2, equipments_disabled: 0, equipments_to_fix: 3,
      commands_ready: 1, commands_blocking: 2, commands_uncovered: 0,
    });
    assert.deepEqual(labels.equipments, [
      '1 équipement publié', '2 équipements exclus',
      '0 équipement désactivé dans Jeedom', '3 équipements à corriger',
    ]);
    assert.deepEqual(labels.commands, ['1 commande prête', '2 commandes bloquantes', '0 commande non couverte']);
  });
});

describe('20.3 / AC7 — le dénombrement ne lit que l’arbre de la pièce ouverte', () => {
  const surface = fs.readFileSync('desktop/js/jeedom2ha_mapping_surface.js', 'utf8');
  const override = fs.readFileSync('desktop/js/jeedom2ha_mapping_override.js', 'utf8');

  it('les compteurs sont alimentés depuis ctx.trees (arbres de la pièce) par M.summarizeRoom', () => {
    assert.match(surface, /M\.summarizeRoom\(trees, ctx\.room\.equipments\.length\)/);
    assert.match(surface, /ctx\.trees\[eqId\] = normalized;/);
  });

  it('aucune lecture globale du parc depuis la surface', () => {
    assert.doesNotMatch(surface, /getDiagnostics|getPublishedScopeForConsole|published_scope|diagnostic_equipments|home_signals/);
    assert.doesNotMatch(override, /published_scope|diagnostic_equipments|home_signals/);
  });
});
