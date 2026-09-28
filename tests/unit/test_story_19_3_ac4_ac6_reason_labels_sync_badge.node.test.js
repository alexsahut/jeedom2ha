// Story 19.3 — AC4 : les 12 nouveaux codes exposés par le branchement sur
// evaluate_equipment() (Story 19.0/19.1) ont un libellé français concret dans
// REASON_LABELS, jamais le code brut ni une chaîne vide — via buildBlockingReason,
// l'API réellement consommée par la surface (REASON_LABELS n'est pas exporté).
// AC6 : shouldShowOverridePendingBadge lit sync_status.override_pending, avec
// normalisation stricte (jamais un badge sur une valeur absente/malformée).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

function blockingView(reason, extra) {
  return Object.assign(
    {
      ha_entity_type: null,
      projection_validity: { is_valid: false, reason_code: null, missing_capabilities: [], missing_fields: [] },
      should_publish: false,
      publication_reason: reason,
    },
    extra || {}
  );
}

// Story 19.3 (AC4) — codes ajoutés par le branchement evaluate_equipment() (AC1/AC2/AC3).
const NEW_BLOCKING_REASON_CODES = [
  'no_mapping',
  'skipped_no_mapping_candidate',
  'ha_component_not_in_product_scope',
  'publication_excluded_eqlogic',
  'publication_excluded_command',
  'command_not_covered',
  'excluded_eqlogic',
  'excluded_plugin',
  'excluded_object',
  'no_commands',
];

describe('19.3 / AC4 — REASON_LABELS français pour les nouveaux codes de blocage', () => {
  for (const code of NEW_BLOCKING_REASON_CODES) {
    it(`traduit "${code}" en libellé français concret (pas le code brut)`, () => {
      const label = M.buildBlockingReason(blockingView(code));
      assert.notStrictEqual(label, '');
      assert.notStrictEqual(label, code);
      assert.strictEqual(typeof label, 'string');
    });
  }

  it('publication_forced (should_publish=true) a aussi un libellé français concret', () => {
    const view = blockingView('publication_forced', { should_publish: true });
    const label = M.buildBlockingReason(view);
    assert.notStrictEqual(label, '');
    assert.notStrictEqual(label, 'publication_forced');
  });
});

// ---------------------------------------------------------------------------
// AC6 — badge « pas encore appliqué » (shouldShowOverridePendingBadge)
// ---------------------------------------------------------------------------

function treeWithSyncStatus(syncStatus) {
  return { jeedom_eq_id: 1, eq_name: 'Test', mapped: true, commands: [], sync_status: syncStatus };
}

describe('19.3 / AC6 — shouldShowOverridePendingBadge', () => {
  it('affiche le badge quand override_pending=true (override sauvegardé, pas encore syncé)', () => {
    const tree = treeWithSyncStatus({
      synced_should_publish: true,
      current_should_publish: false,
      override_pending: true,
    });
    assert.strictEqual(M.shouldShowOverridePendingBadge(tree), true);
  });

  it("n'affiche pas le badge quand la décision syncée == la décision courante", () => {
    const tree = treeWithSyncStatus({
      synced_should_publish: true,
      current_should_publish: true,
      override_pending: false,
    });
    assert.strictEqual(M.shouldShowOverridePendingBadge(tree), false);
  });

  it("n'affiche jamais le badge sur un équipement jamais synchronisé (synced_should_publish=null)", () => {
    const tree = treeWithSyncStatus({
      synced_should_publish: null,
      current_should_publish: true,
      override_pending: false,
    });
    assert.strictEqual(M.shouldShowOverridePendingBadge(tree), false);
  });

  it('normalise un sync_status malformé/absent en override_pending=false (jamais un badge sur du bruit)', () => {
    assert.strictEqual(M.shouldShowOverridePendingBadge(treeWithSyncStatus(undefined)), false);
    assert.strictEqual(M.shouldShowOverridePendingBadge(treeWithSyncStatus({})), false);
    assert.strictEqual(
      M.shouldShowOverridePendingBadge(treeWithSyncStatus({ override_pending: 'true' })),
      false
    );
    assert.strictEqual(M.shouldShowOverridePendingBadge({}), false);
  });
});
