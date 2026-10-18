'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

function decisionView(publicationReason, options = {}) {
  const ready = options.ready === true;
  return {
    ha_entity_type: ready ? 'sensor' : null,
    reason_code: options.reasonCode || null,
    projection_validity: {
      is_valid: ready,
      reason_code: ready ? null : publicationReason,
      missing_capabilities: [],
      missing_fields: [],
    },
    should_publish: ready,
    publication_reason: publicationReason,
  };
}

function readyView() {
  return decisionView('sure', { ready: true });
}

function command(id, diagnostic) {
  return { jeedom_cmd_id: id, diagnostic };
}

// Story 25.1 : l'état d'un équipement vient de resolveEquipmentState (plus d'état de synthèse).
function tree(commands, published) {
  return {
    commands,
    sync_status: { synced_should_publish: true, current_should_publish: published, override_pending: false, published_in_ha: published },
  };
}

describe('CC-38 — exclusions volontaires', () => {
  const excludedReasons = [
    'excluded_eqlogic',
    'excluded_plugin',
    'excluded_object',
    'publication_excluded_eqlogic',
    'publication_excluded_command',
  ];

  for (const reason of excludedReasons) {
    it(`${reason} est une exclusion`, () => {
      const view = decisionView(reason);
      assert.strictEqual(M.isExcludedDiagnostic(view), true);
      assert.strictEqual(M.buildExcludedLabel(view).startsWith('Exclue → '), true);
    });
  }

  for (const [label, view] of [
    ['command_not_covered', decisionView('command_not_covered')],
    ['ambiguous_skipped', decisionView('ambiguous_skipped')],
    ['disabled_eqlogic', decisionView('disabled_eqlogic')],
    ['vue prête', readyView()],
    ['null', null],
  ]) {
    it(`${label} n'est pas une exclusion`, () => {
      assert.strictEqual(M.isExcludedDiagnostic(view), false);
    });
  }

  it('trois commandes excluded_plugin : synthèse exclue sans ancre', () => {
    const summary = M.summarizePublication({ commands: [
      command(1, decisionView('excluded_plugin')),
      command(2, decisionView('excluded_plugin')),
      command(3, decisionView('excluded_plugin')),
    ] });
    assert.deepStrictEqual({
      ready_count: summary.ready_count,
      blocking_count: summary.blocking_count,
      excluded_count: summary.excluded_count,
      first_blocking_cmd_id: summary.first_blocking_cmd_id,
    }, { ready_count: 0, blocking_count: 0, excluded_count: 3, first_blocking_cmd_id: null });
    assert.deepStrictEqual(M.resolveEquipmentState(tree([
      command(1, decisionView('excluded_plugin')),
      command(2, decisionView('excluded_plugin')),
      command(3, decisionView('excluded_plugin')),
    ], false)), { state: 'excluded', blocked_mention: 0 });
  });

  it('deux prêtes et une exclusion manuelle de commande restent publiées', () => {
    const summary = M.summarizePublication({ commands: [
      command(1, readyView()), command(2, readyView()),
      command(3, decisionView('publication_excluded_command')),
    ] });
    assert.deepStrictEqual(M.resolveEquipmentState(tree([
      command(1, readyView()), command(2, readyView()),
      command(3, decisionView('publication_excluded_command')),
    ], true)), { state: 'published', blocked_mention: 0 });
    assert.strictEqual(summary.first_blocking_cmd_id, null);
  });

  it('une ambiguë et deux exclusions : seule l’ambiguë bloque et reçoit l’ancre', () => {
    const summary = M.summarizePublication({ commands: [
      command(10, decisionView('ambiguous_skipped')),
      command(11, decisionView('excluded_object')),
      command(12, decisionView('excluded_object')),
    ] });
    assert.strictEqual(summary.blocking_count, 1);
    assert.strictEqual(summary.first_blocking_cmd_id, 10);
    assert.deepStrictEqual(M.resolveEquipmentState(tree([
      command(10, decisionView('ambiguous_skipped')),
      command(11, decisionView('excluded_object')),
      command(12, decisionView('excluded_object')),
    ], false)), { state: 'blocked', blocked_mention: 0 });
  });

  it('eq 579 : les vrais blocages gardent leur synthèse et leur ancre', () => {
    const summary = M.summarizePublication({ commands: [
      command(1, readyView()), command(2, readyView()), command(3, readyView()), command(4, readyView()),
      command(5, decisionView('command_not_covered')),
      command(6, decisionView('ambiguous_skipped')),
    ] });
    // « Partiellement publié » n'existe plus : équipement dans HA, avec la mention d'une commande bloquée.
    assert.deepStrictEqual(M.resolveEquipmentState(tree([
      command(1, readyView()), command(2, readyView()), command(3, readyView()), command(4, readyView()),
      command(5, decisionView('command_not_covered')),
      command(6, decisionView('ambiguous_skipped')),
    ], true)), { state: 'published', blocked_mention: 1 });
    assert.strictEqual(summary.first_blocking_cmd_id, 6);
  });

  it('diagnosticState d’une exclusion reste blocking : édition inchangée', () => {
    assert.strictEqual(M.diagnosticState(decisionView('excluded_eqlogic')), 'blocking');
  });

  it('eq 559 : excluded_plugin + covered:false ne reçoit pas le libellé non couverte', () => {
    assert.strictEqual(M.shouldShowUncoveredLabel(decisionView('excluded_plugin')), false);
  });

  it('collectBlockingCommandIds ignore les commandes non couvertes et exclues', () => {
    const ids = M.collectBlockingCommandIds({ commands: [
      command(1, decisionView('command_not_covered')),
      command(2, decisionView('excluded_plugin')),
      command(3, decisionView('ambiguous_skipped')),
    ] });
    assert.deepStrictEqual(ids, [3]);
  });
});

describe('25.1 / AC9 — mots d’état des exclusions (assertions rétablies)', () => {
  it('un équipement exclu se dit « Exclu », une commande exclue « Exclue », jamais « partiel » ni « prête »', () => {
    assert.strictEqual(M.EQUIPMENT_STATE_LABELS.excluded, 'Exclu');
    assert.strictEqual(M.resolveEquipmentState(tree([command(1, decisionView('excluded_object'))], false)).state, 'excluded');
    assert.strictEqual(M.classifyCommandCategory(command(1, decisionView('publication_excluded_command'))), 'excluded');
    assert.strictEqual(M.buildExcludedLabel(decisionView('excluded_plugin')).startsWith('Exclue → '), true);
    assert.ok(!Object.values(M.EQUIPMENT_STATE_LABELS).some((label) => /partiel|prêt/i.test(label)));
  });
});
