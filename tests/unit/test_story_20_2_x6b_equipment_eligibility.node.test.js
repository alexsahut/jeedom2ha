'use strict';

// Story 20-2 — reprise X6b (P2, relecture indépendante PR #215). Un équipement
// INÉLIGIBLE (ex. eq 588-591, `excluded_plugin`) n'a ni entité ni commande dans
// l'arbre : sans les deux champs additifs du démon (`eligible`,
// `equipment_publication_override`), « Exclure » restait actif (sans effet,
// `evaluate_equipment` refuse l'inéligible avant toute exclusion) et « Revenir au
// mode automatique » restait grisé même avec un override d'équipement déjà posé
// (AC1/AC6). Même trou pour un équipement éligible sans entité.

const test = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

test('normalizeTree — eligible par défaut true (démon plus ancien, comportement inchangé)', () => {
  const tree = M.normalizeTree({ jeedom_eq_id: 588, mapped: false, entities: [], commands: [] });
  assert.equal(tree.eligible, true);
  assert.equal(tree.equipment_publication_override, null);
});

test('normalizeTree — eligible et equipment_publication_override lus tels quels', () => {
  const treeFalse = M.normalizeTree({ eligible: false, equipment_publication_override: 'exclude', entities: [], commands: [] });
  assert.equal(treeFalse.eligible, false);
  assert.equal(treeFalse.equipment_publication_override, 'exclude');

  const treeForce = M.normalizeTree({ eligible: true, equipment_publication_override: 'force_publish', entities: [], commands: [] });
  assert.equal(treeForce.eligible, true);
  assert.equal(treeForce.equipment_publication_override, 'force_publish');
});

test('normalizeTree — valeur hors énumération d\'equipment_publication_override repliée à null', () => {
  const tree = M.normalizeTree({ equipment_publication_override: 'autre_chose', entities: [], commands: [] });
  assert.equal(tree.equipment_publication_override, null);
});

test('publicationActionState — équipement inéligible : Exclure/Forcer inactifs, info-bulle dédiée', () => {
  const state = M.publicationActionState({ eligible: false, publication_override: null, has_publication_override: false }, true);
  assert.equal(state.can_exclude, false);
  assert.equal(state.can_force, false);
  assert.match(state.exclude_reason, /pas éligible|non éligible/i);
  assert.match(state.exclude_reason, /sans effet/i);
  assert.match(state.force_reason, /pas éligible|non éligible/i);
});

test('publicationActionState — équipement inéligible AVEC override posé : Revenir reste actif', () => {
  const state = M.publicationActionState({ eligible: false, publication_override: 'exclude', has_publication_override: true }, true);
  assert.equal(state.can_exclude, false);
  assert.equal(state.can_force, false);
  assert.equal(state.can_revert, true);
});

test('publicationActionState — équipement inéligible SANS aucun override : Revenir reste grisé', () => {
  const state = M.publicationActionState({ eligible: false, publication_override: null, has_publication_override: false }, true);
  assert.equal(state.can_revert, false);
  assert.match(state.revert_reason, /[Aa]ucun override/);
});

test('publicationActionState — eligible absent (démon plus ancien) : comportement équipement inchangé', () => {
  const state = M.publicationActionState({ publication_override: null, has_publication_override: true }, true);
  assert.equal(state.can_revert, true);
  assert.equal(state.can_exclude, true);
});

test('publicationActionState — eligible=false ignoré à la portée ENTITÉ (ne concerne que l\'équipement)', () => {
  const ready = { ha_entity_type: 'light', projection_validity: { is_valid: true }, should_publish: false };
  const state = M.publicationActionState({ eligible: false, decision: ready, override_command_id: 8, publication_override: null }, false);
  assert.equal(state.can_force, true);
});

test('equipmentPublicationTarget — équipement inéligible avec override persisté (eq 590) : exclude_eqlogic lisible sans entité', () => {
  const tree = M.normalizeTree({
    eligible: false, equipment_publication_override: 'exclude', mapped: false, entities: [], commands: [],
  });
  const target = M.equipmentPublicationTarget(tree);
  assert.equal(target.eligible, false);
  assert.equal(target.publication_override, 'exclude_eqlogic');
  assert.equal(target.has_publication_override, true);
  const state = M.publicationActionState(target, true);
  assert.equal(state.can_exclude, false);
  assert.equal(state.can_force, false);
  assert.equal(state.can_revert, true);
});

test('equipmentPublicationTarget — équipement éligible sans entité, forçage posé : Revenir actif', () => {
  const tree = M.normalizeTree({
    eligible: true, equipment_publication_override: 'force_publish', mapped: false, entities: [], commands: [],
  });
  const target = M.equipmentPublicationTarget(tree);
  assert.equal(target.publication_override, 'force_publish');
  assert.equal(target.has_publication_override, true);
  const state = M.publicationActionState(target, true);
  assert.equal(state.can_revert, true);
});

test('equipmentPublicationTarget — non-régression : veto lu via une entité exclude_eqlogic (sans champ équipement)', () => {
  const blocked = { ha_entity_type: 'cover', projection_validity: { is_valid: true }, should_publish: false };
  const tree = M.normalizeTree({
    entities: [{ ha_entity_type: 'cover', command_ids: [1], decision: blocked, publication_override: 'exclude_eqlogic', override_command_id: 1, override_pending: false }],
    commands: [],
  });
  const target = M.equipmentPublicationTarget(tree);
  assert.equal(target.publication_override, 'exclude_eqlogic');
  assert.equal(target.has_publication_override, true);
  assert.equal(target.eligible, true);
});

test('equipmentPublicationTarget — non-régression : override de type sur une commande active Revenir', () => {
  const tree = M.normalizeTree({
    entities: [],
    commands: [{ jeedom_cmd_id: 1, cmd_name: 'x', override_applied: true }],
  });
  const target = M.equipmentPublicationTarget(tree);
  assert.equal(target.has_publication_override, true);
  assert.equal(target.publication_override, null);
});
