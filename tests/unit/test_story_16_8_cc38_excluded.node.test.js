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
      assert.strictEqual(M.buildExcludedLabel(view).startsWith('Ne sera pas publié — '), true);
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
    assert.strictEqual(M.buildPublicationSummaryLabel(summary), 'Exclu de Jeedom2HA : ne sera pas publié dans Home Assistant.');
    assert.strictEqual(M.publicationSummaryState(summary), 'excluded');
  });

  it('deux prêtes et une exclusion manuelle de commande restent publiées', () => {
    const summary = M.summarizePublication({ commands: [
      command(1, readyView()), command(2, readyView()),
      command(3, decisionView('publication_excluded_command')),
    ] });
    assert.strictEqual(M.publicationSummaryState(summary), 'publish');
    assert.strictEqual(M.buildPublicationSummaryLabel(summary), 'Sera publié dans Home Assistant : 2 commande(s) prête(s).');
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
    assert.strictEqual(M.buildPublicationSummaryLabel(summary), 'Ne sera pas publié dans Home Assistant : 1 commande(s) bloquante(s).');
  });

  it('eq 579 Enphase : les vrais blocages gardent leur synthèse et leur ancre', () => {
    const summary = M.summarizePublication({ commands: [
      command(1, readyView()), command(2, readyView()), command(3, readyView()), command(4, readyView()),
      command(5, decisionView('command_not_covered')),
      command(6, decisionView('ambiguous_skipped')),
    ] });
    assert.strictEqual(M.buildPublicationSummaryLabel(summary), 'Partiellement publié : 4 prête(s), 1 bloquante(s).');
    assert.strictEqual(summary.first_blocking_cmd_id, 6);
  });

  it('diagnosticState d’une exclusion reste blocking : édition inchangée', () => {
    assert.strictEqual(M.diagnosticState(decisionView('excluded_eqlogic')), 'blocking');
  });
});
