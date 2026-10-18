// ARTEFACT — Story 20-2 (AC8, X6) : un équipement exclu sans commande doit afficher
// « Exclu », pas « Aucune commande projetable » (constat validation UX ClaudeBox 06/10,
// eq 588-591). `summarizePublication` ne peut pas le trouver en bouclant sur `commands`
// (vide) ; il doit lire `equipment_decision.publication_reason`, seule source du démon.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

function readyView() {
  return {
    ha_entity_type: 'light',
    projection_validity: { is_valid: true, reason_code: null, missing_capabilities: [], missing_fields: [] },
    should_publish: true,
    publication_reason: 'sure',
  };
}
function blockingView() {
  return {
    ha_entity_type: 'cover',
    projection_validity: { is_valid: false, reason_code: 'missing_capability', missing_capabilities: ['position'], missing_fields: [] },
    should_publish: false,
    publication_reason: 'projection_invalid',
  };
}
function decisionView(reason) {
  return {
    ha_entity_type: null,
    projection_validity: { is_valid: false, reason_code: reason, missing_capabilities: [], missing_fields: [] },
    should_publish: false,
    publication_reason: reason,
  };
}
function treeNoCommands(decisionReason) {
  return {
    jeedom_eq_id: 588,
    mapped: true,
    equipment_decision: decisionReason ? decisionView(decisionReason) : null,
    commands: [],
  };
}
function treeWith(diags, published) {
  return {
    jeedom_eq_id: 100,
    mapped: true,
    sync_status: { synced_should_publish: published, current_should_publish: published, override_pending: false, published_in_ha: published },
    commands: diags.map((d, i) => ({ jeedom_cmd_id: 10 + i, cmd_name: 'C' + i, diagnostic: d, published_in_ha: published && d.should_publish === true })),
  };
}

describe('20-2 / AC8 — équipement exclu sans commande', () => {
  ['excluded_plugin', 'excluded_eqlogic', 'excluded_object', 'publication_excluded_eqlogic'].forEach((reason) => {
    it('raison « ' + reason + ' » -> « Exclu », état excluded', () => {
      const summary = M.summarizePublication(treeNoCommands(reason));
      assert.strictEqual(summary.excluded_count, 1);
      assert.strictEqual(M.resolveEquipmentState(treeNoCommands(reason)).state, 'excluded');
      assert.strictEqual(M.EQUIPMENT_STATE_LABELS.excluded, 'Exclu');
    });
  });

  it('raison « disabled_eqlogic » -> « Désactivé », état disabled (comportement existant)', () => {
    const summary = M.summarizePublication(treeNoCommands('disabled_eqlogic'));
    assert.strictEqual(summary.disabled_count, 1);
    assert.strictEqual(M.resolveEquipmentState(treeNoCommands('disabled_eqlogic')).state, 'disabled');
    assert.strictEqual(M.EQUIPMENT_STATE_LABELS.disabled, 'Désactivé');
  });

  it('equipment_decision absent -> « Rien à publier » (successeur de « Aucune commande projetable »)', () => {
    const summary = M.summarizePublication(treeNoCommands(null));
    assert.strictEqual(summary.excluded_count, 0);
    assert.strictEqual(summary.disabled_count, 0);
    assert.strictEqual(M.resolveEquipmentState(treeNoCommands(null)).state, 'nothing_to_publish');
    assert.strictEqual(M.EQUIPMENT_STATE_LABELS.nothing_to_publish, 'Rien à publier');
  });

  it('equipment_decision sans exclusion (« no_commands ») -> « Rien à publier »', () => {
    const summary = M.summarizePublication(treeNoCommands('no_commands'));
    assert.strictEqual(summary.excluded_count, 0);
    assert.strictEqual(summary.disabled_count, 0);
    assert.strictEqual(M.resolveEquipmentState(treeNoCommands('no_commands')).state, 'nothing_to_publish');
  });

  it('non-régression : arbre avec commandes prêtes inchangé', () => {
    const summary = M.summarizePublication(treeWith([readyView(), readyView()], true));
    assert.strictEqual(summary.ready_count, 2);
    assert.strictEqual(M.resolveEquipmentState(treeWith([readyView(), readyView()], true)).state, 'published');
    assert.strictEqual(M.EQUIPMENT_STATE_LABELS.published, 'Publié');
  });

  it('non-régression : arbre avec commande bloquante inchangé', () => {
    const summary = M.summarizePublication(treeWith([blockingView()], false));
    assert.strictEqual(summary.blocking_count, 1);
    assert.strictEqual(M.resolveEquipmentState(treeWith([blockingView()], false)).state, 'blocked');
    assert.strictEqual(M.EQUIPMENT_STATE_LABELS.blocked, 'Bloqué');
  });

  it('non-régression : exclusion par commande (arbre avec commandes) inchangée', () => {
    const summary = M.summarizePublication(treeWith([decisionView('excluded_eqlogic')], false));
    assert.strictEqual(summary.excluded_count, 1);
    assert.strictEqual(M.resolveEquipmentState(treeWith([decisionView('excluded_eqlogic')], false)).state, 'excluded');
    assert.strictEqual(M.EQUIPMENT_STATE_LABELS.excluded, 'Exclu');
  });
});

describe('25.1 / AC9 — mot d’état d’un équipement sans commande (assertions rétablies)', () => {
  it('exclu → « Exclu », désactivé → « Désactivé », rien → « Rien à publier »', () => {
    const word = (reason) => M.EQUIPMENT_STATE_LABELS[M.resolveEquipmentState(treeNoCommands(reason)).state];
    assert.strictEqual(word('excluded_eqlogic'), 'Exclu');
    assert.strictEqual(word('disabled_eqlogic'), 'Désactivé');
    assert.strictEqual(word(null), 'Rien à publier');
  });
});
