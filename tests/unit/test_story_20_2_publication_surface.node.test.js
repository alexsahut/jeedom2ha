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

test('20-2 — P2 revue : chaque bouton porte sa propre cause de blocage', () => {
  const alreadyPublished = M.publicationActionState({ decision: ready, override_command_id: 8, publication_override: null });
  assert.equal(alreadyPublished.can_force, false);
  assert.match(alreadyPublished.force_reason, /Déjà publiée/);

  const alreadyForced = M.publicationActionState({ decision: blocked, override_command_id: 8, publication_override: 'force_publish' });
  assert.equal(alreadyForced.can_force, false);
  assert.match(alreadyForced.force_reason, /déjà forcée|Publication déjà forcée/i);

  const noMapping = M.publicationActionState({ decision: { ha_entity_type: null, should_publish: false }, override_command_id: 8, publication_override: null });
  assert.equal(noMapping.can_force, false);
  assert.match(noMapping.force_reason, /mapping/);

  const outOfScope = M.publicationActionState({ decision: { ha_entity_type: 'vacuum', should_publish: false }, override_command_id: 8, publication_override: null });
  assert.equal(outOfScope.can_force, false);
  assert.match(outOfScope.force_reason, /hors périmètre/);

  const invalidProjection = M.publicationActionState({
    decision: { ha_entity_type: 'light', should_publish: false, projection_validity: { is_valid: false } },
    override_command_id: 8, publication_override: null,
  });
  assert.equal(invalidProjection.can_force, false);
  assert.match(invalidProjection.force_reason, /invalide/);

  const forceable = M.publicationActionState({
    decision: { ha_entity_type: 'light', should_publish: false, projection_validity: { is_valid: true } },
    override_command_id: 8, publication_override: null,
  });
  assert.equal(forceable.can_force, true);
  assert.equal(forceable.force_reason, null);

  const alreadyExcluded = M.publicationActionState({ decision: blocked, override_command_id: 8, publication_override: 'exclude_command' });
  assert.equal(alreadyExcluded.can_exclude, false);
  assert.match(alreadyExcluded.exclude_reason, /déjà exclue/i);

  const nothingToRevert = M.publicationActionState({ decision: blocked, override_command_id: 8, publication_override: null });
  assert.equal(nothingToRevert.can_revert, false);
  assert.match(nothingToRevert.revert_reason, /Aucun override/);
});

test('20-2 — P1 revue : exclude_eqlogic/exclude_command du démon restent lisibles après normalizeTree', () => {
  const treeEqlogic = M.normalizeTree({ entities: [{
    ha_entity_type: 'light', command_ids: [9], decision: blocked,
    publication_override: 'exclude_eqlogic', override_command_id: 9, override_pending: false,
  }] });
  assert.equal(treeEqlogic.entities[0].publication_override, 'exclude_eqlogic');
  const stateEqlogic = M.publicationActionState(treeEqlogic.entities[0]);
  assert.equal(stateEqlogic.can_exclude, false);
  assert.equal(stateEqlogic.can_revert, true);

  const treeCommand = M.normalizeTree({ entities: [{
    ha_entity_type: 'switch', command_ids: [11], decision: blocked,
    publication_override: 'exclude_command', override_command_id: 11, override_pending: false,
  }] });
  assert.equal(treeCommand.entities[0].publication_override, 'exclude_command');
  const stateCommand = M.publicationActionState(treeCommand.entities[0]);
  assert.equal(stateCommand.can_exclude, false);
  assert.equal(stateCommand.can_revert, true);
});

test('20-2 — P2 revue : libellé entité avec noms de commande réels (commands[])', () => {
  const commands = [
    { jeedom_cmd_id: 21, cmd_name: 'Allumer' },
    { jeedom_cmd_id: 22, cmd_name: 'Variateur' },
  ];
  const entity = { command_ids: [21, 22] };
  assert.deepEqual(M.resolveCommandNames(commands, [21, 22]), ['Allumer', 'Variateur']);
  assert.equal(M.entityCommandsLabel(entity, commands), 'Commandes : Allumer, Variateur');
  // Commande absente de l'arbre courant : fallback #id, jamais vide.
  assert.equal(M.entityCommandsLabel({ command_ids: [99] }, commands), 'Commandes : #99');
});

test('20-2 — P2 revue (AC3) : aperçu du forçage lit type, validité et commandes', () => {
  const commands = [{ jeedom_cmd_id: 5, cmd_name: 'Ouvrir' }, { jeedom_cmd_id: 6, cmd_name: 'Fermer' }];
  const acceptedView = {
    ha_entity_type: 'cover', projection_validity: { is_valid: true }, should_publish: true,
    publication_reason: 'sure', command_ids: [5, 6],
  };
  const accepted = M.forcePreviewState(acceptedView, commands);
  assert.equal(accepted.ha_entity_type, 'cover');
  assert.equal(accepted.is_valid, true);
  assert.equal(accepted.can_confirm, true);
  assert.equal(accepted.refusal_reason, null);
  assert.deepEqual(accepted.command_names, ['Ouvrir', 'Fermer']);

  const refusedView = {
    ha_entity_type: 'cover', projection_validity: { is_valid: false, reason_code: 'ha_missing_command_topic' },
    should_publish: false, publication_reason: 'ambiguous_skipped', command_ids: [5],
  };
  const refused = M.forcePreviewState(refusedView, commands);
  assert.equal(refused.can_confirm, false);
  assert.ok(refused.refusal_reason);

  const emptyView = M.forcePreviewState(null, commands);
  assert.equal(emptyView.can_confirm, false);
  assert.ok(emptyView.refusal_reason);
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
