'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

const ready = { ha_entity_type: 'light', projection_validity: { is_valid: true }, should_publish: true, publication_reason: 'sure' };
const blocked = { ha_entity_type: 'cover', projection_validity: { is_valid: true }, should_publish: false, publication_reason: 'ambiguous_skipped' };

test('20-2 — entités : contrat démon lu sans recalcul', () => {
  const tree = M.normalizeTree({ equipment_decision: ready, entities: [{
    ha_entity_type: 'light', command_ids: [21, 22], decision: ready,
    publication_override: null, reason_details: {}, override_command_id: 21, override_pending: true,
  }] });
  assert.deepEqual(tree.entities[0].command_ids, [21, 22]);
  assert.equal(M.entityCommandsLabel(tree.entities[0]), 'Commandes : #21, #22');
  assert.equal(M.publicationActionState(tree.entities[0]).can_exclude, true);
  assert.equal(M.publicationActionState(tree.entities[0]).can_force, false);
});

test('20-2 — actions : clé absente grisée, automatique retire publication et type', () => {
  const noKey = M.publicationActionState({ decision: blocked, override_command_id: null });
  assert.equal(noKey.can_exclude, false);
  assert.match(noKey.reason, /commande clé/);
  const active = M.publicationActionState({ decision: ready, override_command_id: 8, publication_override: 'exclude' });
  assert.equal(active.can_revert, true);
  assert.equal(M.shouldConfirmPublication('exclude', ready), true);
  assert.equal(M.shouldConfirmPublication('force_publish', ready), false);
});

test('20-2 — causes ambiguës : libellés spécifiques issus de reason_code', () => {
  for (const [code, phrase] of [
    ['name_heuristic_rejection', 'mot du nom'],
    ['duplicate_generic_types', 'types génériques en double'],
    ['switch_state_orphan', 'état sans ordre On/Off'],
  ]) {
    assert.match(M.buildPublishCellLabel({ ...blocked, reason_code: code }), new RegExp(phrase));
  }
});
