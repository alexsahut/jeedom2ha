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
  assert.match(noMapping.force_reason, /type Home Assistant identifié/);

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
  // Revue X4 (point 4) : exclude_eqlogic lu sur une cible ENTITÉ désigne le veto hérité de
  // l'équipement — cette entité ne porte pas elle-même l'override, Revenir n'a donc aucun
  // effet à sa propre portée (il faut le faire depuis l'équipement).
  assert.equal(stateEqlogic.can_revert, false);

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

test('20-2 — P2 revue (AC7) : badge entité en attente, lu tel quel', () => {
  assert.equal(M.shouldShowEntityPendingBadge({ override_pending: true }), true);
  assert.equal(M.shouldShowEntityPendingBadge({ override_pending: false }), false);
  assert.equal(M.shouldShowEntityPendingBadge(null), false);
});

test('20-2 — P2 revue : erreur de requête de publication lisible (y compris 409 relayé)', () => {
  assert.equal(M.readPublicationRequestError({ state: 'ok', result: { status: 'ok', payload: {} } }), null);
  assert.equal(
    M.readPublicationRequestError({ state: 'ok', result: { status: 'error', message: 'Commande sans entité propre' } }),
    'Commande sans entité propre',
  );
  assert.ok(M.readPublicationRequestError({ state: 'ok', result: { status: 'error' } }));
  assert.ok(M.readPublicationRequestError({ state: 'error', result: '{{Erreur}}' }));
  assert.ok(M.readPublicationRequestError(null));
});

test('20-2 — P2 revue (point 9) : le sélecteur de type (route TYPE) reste actif quelle que soit la publication', () => {
  // getOverrideSelectorState ne lit jamais publication_override : exclure/forcer une entité
  // (route PUBLICATION, story 20-2) ne doit jamais désactiver le sélecteur de type d'une
  // commande couverte (route TYPE, story 16-8) — deux mécanismes indépendants.
  const coveredRow = { diagnostic: { covered: true }, covered: true };
  assert.equal(M.getOverrideSelectorState(coveredRow).active, true);
  assert.equal(M.getOverrideSelectorState({ ...coveredRow, publication_override: 'exclude_eqlogic' }).active, true);
  assert.equal(M.getOverrideSelectorState({ ...coveredRow, publication_override: 'exclude_command' }).active, true);
  assert.equal(M.getOverrideSelectorState({ ...coveredRow, publication_override: 'force_publish' }).active, true);
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

test('20-2 — revue X4 (point 3) : exclusion posée sur l\'équipement vue au niveau équipement', () => {
  // renderEquipmentTree calcule désormais `publication_override: 'exclude_eqlogic'` pour la
  // cible équipement dès qu'une entité porte ce veto — même lecture que publicationActionState
  // ferait pour une entité déjà exclue : « Exclure » devient sans effet.
  const state = M.publicationActionState({ publication_override: 'exclude_eqlogic', has_publication_override: true }, true);
  assert.equal(state.can_exclude, false);
  assert.match(state.exclude_reason, /déjà exclue/);
});

test('20-2 — revue X4 (point 3) : bouton équipement « Revenir au mode automatique » fusionné', () => {
  // Le bouton unique doit s'activer que l'override en attente d'un retrait soit de type
  // (has_publication_override vrai sans policy de publication) ou de publication (policy posée).
  const fromTypeOverrideOnly = M.publicationActionState({ publication_override: null, has_publication_override: true }, true);
  assert.equal(fromTypeOverrideOnly.can_revert, true);

  const fromPublicationOverride = M.publicationActionState({ publication_override: 'force_publish', has_publication_override: true }, true);
  assert.equal(fromPublicationOverride.can_revert, true);

  const withoutAnyOverride = M.publicationActionState({ publication_override: null, has_publication_override: false }, true);
  assert.equal(withoutAnyOverride.can_revert, false);
  assert.match(withoutAnyOverride.revert_reason, /[Aa]ucun override/);
});

test('20-2 — revue X4 (point 4) : entité héritant du veto d\'équipement — Forcer/Revenir grisés', () => {
  // L'entité elle-même ne porte pas l'override (il vit sur l'équipement) : Forcer et
  // Revenir n'ont aucun effet à sa portée et doivent pointer vers l'équipement.
  const inherited = M.publicationActionState(
    { publication_override: 'exclude_eqlogic', has_publication_override: true, override_command_id: 42, decision: { should_publish: false, ha_entity_type: 'light' } },
    false,
  );
  assert.equal(inherited.can_exclude, false);
  assert.equal(inherited.can_force, false);
  assert.equal(inherited.can_revert, false);
  assert.match(inherited.force_reason, /l’équipement|l'équipement/);
  assert.match(inherited.revert_reason, /l’équipement|l'équipement/);

  // Une entité exclue par SA PROPRE commande (exclude_command, pas le veto d'équipement)
  // garde, elle, son bouton Revenir actif à sa propre portée — comportement inchangé.
  const ownExclusion = M.publicationActionState(
    { publication_override: 'exclude_command', has_publication_override: true, override_command_id: 42, decision: { should_publish: false, ha_entity_type: 'light' } },
    false,
  );
  assert.equal(ownExclusion.can_revert, true);
});

// Story 20-2 (P3, relecture indépendante PR #210, reprise X5d) : à la portée équipement,
// « Confirmer » doit lire l'arbre déjà reçu (currentEntities) pour distinguer une entité
// déjà publiée (aucun changement dû à CE forçage) d'une entité qui deviendrait réellement
// publiée — jamais recalculé, juste comparé par command_ids partagés.
test('20-2 — P3 (reprise X5d) : entité déjà publiée, aucun changement, Confirmer refusé', () => {
  const commands = [{ jeedom_cmd_id: 5, cmd_name: 'Ouvrir' }];
  const view = { entities: [{ command_ids: [5], decision: ready }] };
  const currentEntities = [{ command_ids: [5], decision: ready }];
  const state = M.equipmentForcePreviewState(view, commands, currentEntities);
  assert.equal(state.items[0].already_published, true);
  assert.equal(state.items[0].changes, false);
  assert.match(state.items[0].status_label, /Déjà publiée/);
  assert.equal(state.can_confirm, false);
  assert.match(state.refusal_reason, /ne changerait d.état/);
});

test('20-2 — P3 (reprise X5d) : entité non publiée qui le deviendrait, Confirmer actif', () => {
  const commands = [{ jeedom_cmd_id: 6, cmd_name: 'Fermer' }];
  const view = { entities: [{ command_ids: [6], decision: ready }] };
  const currentEntities = [{ command_ids: [6], decision: blocked }];
  const state = M.equipmentForcePreviewState(view, commands, currentEntities);
  assert.equal(state.items[0].already_published, false);
  assert.equal(state.items[0].changes, true);
  assert.match(state.items[0].status_label, /Sera publiée/);
  assert.equal(state.can_confirm, true);
  assert.equal(state.refusal_reason, null);
});

test('20-2 — P3 (reprise X5d) : mix d\'entités déjà publiées et bloquées, aucune transition, Confirmer refusé', () => {
  const commands = [{ jeedom_cmd_id: 5, cmd_name: 'Ouvrir' }, { jeedom_cmd_id: 7, cmd_name: 'Stop' }];
  const view = { entities: [
    { command_ids: [5], decision: ready },
    { command_ids: [7], decision: blocked },
  ] };
  const currentEntities = [
    { command_ids: [5], decision: ready },
    { command_ids: [7], decision: blocked },
  ];
  const state = M.equipmentForcePreviewState(view, commands, currentEntities);
  assert.equal(state.items[0].already_published, true);
  assert.equal(state.items[0].changes, false);
  assert.equal(state.items[1].already_published, false);
  assert.equal(state.items[1].changes, false);
  assert.match(state.items[1].status_label, /Ne sera pas publié/);
  assert.equal(state.can_confirm, false);
});

test('20-2 — P3 (reprise X5d) : entité absente de l\'arbre courant (jamais vue) traitée comme non publiée', () => {
  const commands = [{ jeedom_cmd_id: 9, cmd_name: 'Ouvrir' }];
  const view = { entities: [{ command_ids: [9], decision: ready }] };
  const state = M.equipmentForcePreviewState(view, commands, []);
  assert.equal(state.items[0].already_published, false);
  assert.equal(state.items[0].changes, true);
  assert.equal(state.can_confirm, true);
});

// Story 20-2 (P3, reprise X5e) : une entité secondaire qui partage UNE commande d'action
// avec l'entité principale (ex. commande 2) ne doit pas être associée à l'entité principale
// — sinon son aperçu est lu sur l'état de l'autre entité (ici : secondaire lue à tort comme
// déjà publiée, alors qu'elle ne l'est pas). L'association se fait par ensemble complet de
// command_ids, puis par position + ha_entity_type, jamais par simple recoupement partiel.
test('20-2 — P3 (reprise X5e) : entités avec commande d\'action partagée, pas de confusion principale/secondaire', () => {
  const commands = [
    { jeedom_cmd_id: 1, cmd_name: 'Monter' },
    { jeedom_cmd_id: 2, cmd_name: 'Stop' },
    { jeedom_cmd_id: 3, cmd_name: 'Descendre' },
  ];
  const currentEntities = [
    { ha_entity_type: 'cover', command_ids: [1, 2], decision: ready },
    { ha_entity_type: 'binary_sensor', command_ids: [2, 3], decision: blocked },
  ];
  const view = { entities: [
    { ha_entity_type: 'cover', command_ids: [1, 2], decision: ready },
    { ha_entity_type: 'binary_sensor', command_ids: [2, 3], decision: ready },
  ] };
  const state = M.equipmentForcePreviewState(view, commands, currentEntities);
  assert.equal(state.items[0].already_published, true);
  assert.equal(state.items[0].changes, false);
  assert.equal(state.items[1].already_published, false);
  assert.equal(state.items[1].changes, true);
  assert.match(state.items[1].status_label, /Sera publiée/);
  assert.equal(state.can_confirm, true);
});
