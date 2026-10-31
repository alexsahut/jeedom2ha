// ARTEFACT — Story 16.8 : tests JS purs de la surface par pièce
// (normalisation arbre pièce -> équipement, synthèse de publication par équipement).
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

// Commande non couverte par le mapping : forme de `_decision_view(decision, None)` côté
// démon (branche `mapping=None` de l'arbre GET), `publication_reason=command_not_covered`.
function uncoveredView() {
  return {
    ha_entity_type: null,
    confidence: null,
    reason_code: null,
    projection_validity: { is_valid: false, reason_code: 'command_not_covered', missing_capabilities: [], missing_fields: [] },
    should_publish: false,
    publication_reason: 'command_not_covered',
  };
}

function disabledView() {
  return {
    ha_entity_type: null,
    projection_validity: { is_valid: false, reason_code: 'disabled_eqlogic', missing_capabilities: [], missing_fields: [] },
    should_publish: false,
    publication_reason: 'disabled_eqlogic',
  };
}

// ---------------------------------------------------------------------------
// AC2/AC3 — normalisation de l'arbre pièce -> équipement (ordre natif préservé)
// ---------------------------------------------------------------------------

describe('16.8 / AC2-AC3 — normalizeRoomsTree', () => {
  it('préserve l’ordre natif des pièces et des équipements sans tri', () => {
    const rooms = M.normalizeRoomsTree([
      { object_id: 5, object_name: 'Salon', parent_number: 0, equipments: [
        { eq_id: 30, eq_name: 'Lampe', enabled: true },
        { eq_id: 12, eq_name: 'Volet', enabled: true },
      ] },
      { object_id: 2, object_name: 'Cuisine', parent_number: 0, equipments: [
        { eq_id: 7, eq_name: 'Prise', enabled: false },
      ] },
    ]);
    assert.deepStrictEqual(rooms.map((r) => r.object_id), [5, 2]);
    assert.deepStrictEqual(rooms[0].equipments.map((e) => e.eq_id), [30, 12]);
    assert.strictEqual(rooms[1].equipments[0].enabled, false);
  });

  it('écarte les pièces sans équipement exploitable (rien de cliquable à vide)', () => {
    const rooms = M.normalizeRoomsTree([
      { object_id: 1, object_name: 'Vide', equipments: [] },
      { object_id: 2, object_name: 'Garage', equipments: [{ eq_id: 9, eq_name: 'Porte', enabled: true }] },
    ]);
    assert.deepStrictEqual(rooms.map((r) => r.object_id), [2]);
  });

  it('écarte les équipements sans id valide', () => {
    const rooms = M.normalizeRoomsTree([
      { object_id: 3, object_name: 'Bureau', equipments: [
        { eq_id: null, eq_name: 'Fantôme', enabled: true },
        { eq_id: 44, eq_name: 'PC', enabled: true },
      ] },
    ]);
    assert.deepStrictEqual(rooms[0].equipments.map((e) => e.eq_id), [44]);
  });

  it('payload absent / non tableau → tableau vide sûr', () => {
    assert.deepStrictEqual(M.normalizeRoomsTree(null), []);
    assert.deepStrictEqual(M.normalizeRoomsTree({}), []);
  });

  it('coerce les ids numériques en string vers int', () => {
    const rooms = M.normalizeRoomsTree([
      { object_id: '8', object_name: 'Chambre', equipments: [{ eq_id: '61', eq_name: 'Radiateur', enabled: true }] },
    ]);
    assert.strictEqual(rooms[0].object_id, 8);
    assert.strictEqual(rooms[0].equipments[0].eq_id, 61);
  });

  it('conserve « Sans pièce » (object_id 0) en dernière position et les désactivés en ordre natif', () => {
    const rooms = M.normalizeRoomsTree([
      { object_id: 7, object_name: 'Garage', equipments: [{ eq_id: 279, eq_name: 'Porte', enabled: false }] },
      { object_id: 0, object_name: 'Sans pièce', equipments: [
        { eq_id: 51, eq_name: 'Premier', enabled: false },
        { eq_id: 52, eq_name: 'Second', enabled: true },
      ] },
    ]);
    assert.deepStrictEqual(rooms.map((r) => r.object_id), [7, 0]);
    assert.deepStrictEqual(rooms[1].equipments.map((e) => e.eq_id), [51, 52]);
    assert.strictEqual(rooms[0].equipments[0].enabled, false);
    assert.strictEqual(rooms[1].equipments[0].enabled, false);
  });
});

// ---------------------------------------------------------------------------
// AC9/AC10 — synthèse de publication par équipement (Bloc C)
// ---------------------------------------------------------------------------

function treeWith(diags) {
  return {
    jeedom_eq_id: 100,
    mapped: true,
    commands: diags.map((d, i) => ({ jeedom_cmd_id: 10 + i, cmd_name: 'C' + i, diagnostic: d })),
  };
}

// Story 25.1 : l'état d'un équipement vient de resolveEquipmentState (successeur de
// publicationSummaryState) ; `published` simule la présence dans HA que porte le démon.
function stateTree(diags, published) {
  const t = treeWith(diags);
  t.sync_status = { synced_should_publish: published, current_should_publish: published, override_pending: false, published_in_ha: published };
  t.commands.forEach((c) => { c.published_in_ha = published && M.isReadyDiagnostic(c.diagnostic); });
  return t;
}
const stateOf = (diags, published) => M.resolveEquipmentState(stateTree(diags, published));

describe('16.8 / AC9 — summarizePublication', () => {
  it('désactivées : état neutre, ni prête ni bloquante et jamais ancrée', () => {
    const tree = treeWith([disabledView(), blockingView()]);
    const s = M.summarizePublication(tree);
    assert.strictEqual(M.isDisabledDiagnostic(disabledView()), true);
    assert.strictEqual(s.disabled_count, 1);
    assert.strictEqual(s.blocking_count, 1);
    assert.strictEqual(s.first_blocking_cmd_id, 11);
    assert.deepStrictEqual(M.collectBlockingCommandIds(tree), [11]);
  });

  it('seulement désactivées : état « Désactivé » dédié et libellé factuel', () => {
    assert.deepStrictEqual(stateOf([disabledView(), disabledView()], false), { state: 'disabled', blocked_mention: 0 });
    assert.strictEqual(M.EQUIPMENT_STATE_LABELS.disabled, 'Désactivé');
    assert.strictEqual(M.buildDisabledLabel(disabledView()), 'Équipement désactivé dans Jeedom');
  });

  it('désactivé l’emporte sur exclu quand aucune commande n’est prête ou bloquée (D1 : R3 avant R4)', () => {
    const excluded = Object.assign({}, disabledView(), { publication_reason: 'excluded_plugin' });
    const t = stateTree([disabledView(), excluded], false);
    t.equipment_decision = disabledView();
    assert.strictEqual(M.resolveEquipmentState(t).state, 'disabled');
    assert.strictEqual(stateOf([excluded, excluded], false).state, 'excluded');
  });

  it('toutes prêtes → dans HA : Publié, 0 bloquée', () => {
    const s = M.summarizePublication(treeWith([readyView(), readyView()]));
    assert.strictEqual(s.total, 2);
    assert.strictEqual(s.ready_count, 2);
    assert.strictEqual(s.blocking_count, 0);
    assert.strictEqual(s.will_publish, true);
    assert.strictEqual(s.first_blocking_cmd_id, null);
    assert.deepStrictEqual(stateOf([readyView(), readyView()], true), { state: 'published', blocked_mention: 0 });
  });

  it('aucune prête, que des bloquées → Bloqué', () => {
    const s = M.summarizePublication(treeWith([blockingView(), blockingView()]));
    assert.strictEqual(s.will_publish, false);
    assert.strictEqual(s.blocking_count, 2);
    assert.strictEqual(stateOf([blockingView(), blockingView()], false).state, 'blocked');
  });

  it('mixte → Publié avec la mention des bloquées (plus d’état partiel) + première commande bloquée en ordre natif', () => {
    const s = M.summarizePublication(treeWith([readyView(), blockingView(), blockingView()]));
    assert.strictEqual(s.ready_count, 1);
    assert.strictEqual(s.blocking_count, 2);
    assert.strictEqual(s.will_publish, true);
    assert.strictEqual(s.first_blocking_cmd_id, 11); // 10 = ready, 11 = premier blocking
    assert.deepStrictEqual(stateOf([readyView(), blockingView(), blockingView()], true), { state: 'published', blocked_mention: 2 });
  });

  it('diagnostic absent (unknown) ne compte ni prêt ni bloqué', () => {
    const s = M.summarizePublication(treeWith([null, readyView()]));
    assert.strictEqual(s.unknown_count, 1);
    assert.strictEqual(s.ready_count, 1);
    assert.strictEqual(s.blocking_count, 0);
    assert.strictEqual(s.will_publish, true);
  });

  it('équipement sans commande projetable → Rien à publier', () => {
    const s = M.summarizePublication(treeWith([null, null]));
    assert.strictEqual(s.will_publish, false);
    assert.strictEqual(stateOf([null, null], false).state, 'nothing_to_publish');
  });

  it('commande non couverte (command_not_covered) : ni prête ni bloquée, jamais l’ancre', () => {
    const s = M.summarizePublication(treeWith([readyView(), uncoveredView(), readyView()]));
    assert.strictEqual(s.total, 3);
    assert.strictEqual(s.ready_count, 2);
    assert.strictEqual(s.blocking_count, 0);
    assert.strictEqual(s.uncovered_count, 1);
    assert.strictEqual(s.unknown_count, 0);
    assert.strictEqual(s.first_blocking_cmd_id, null);
    assert.deepStrictEqual(stateOf([readyView(), uncoveredView(), readyView()], true), { state: 'published', blocked_mention: 0 });
  });

  it('non couverte avant une vraie bloquée : l’ancre va à la bloquée', () => {
    const s = M.summarizePublication(treeWith([uncoveredView(), readyView(), blockingView()]));
    assert.strictEqual(s.uncovered_count, 1);
    assert.strictEqual(s.blocking_count, 1);
    assert.strictEqual(s.first_blocking_cmd_id, 12); // 10 = non couverte, 11 = prête, 12 = bloquée
    assert.deepStrictEqual(stateOf([uncoveredView(), readyView(), blockingView()], true), { state: 'published', blocked_mention: 1 });
  });

  it('seulement des non couvertes → Rien à publier, jamais Bloqué', () => {
    const s = M.summarizePublication(treeWith([uncoveredView(), uncoveredView()]));
    assert.strictEqual(s.uncovered_count, 2);
    assert.strictEqual(s.blocking_count, 0);
    assert.strictEqual(s.will_publish, false);
    assert.strictEqual(stateOf([uncoveredView(), uncoveredView()], false).state, 'nothing_to_publish');
  });

  it('bascule par override : la commande devenue prête retire la mention des bloquées', () => {
    const before = M.summarizePublication(treeWith([readyView(), blockingView()]));
    const after = M.summarizePublication(treeWith([readyView(), readyView()]));
    assert.deepStrictEqual(stateOf([readyView(), blockingView()], true), { state: 'published', blocked_mention: 1 });
    assert.strictEqual(before.first_blocking_cmd_id, 11);
    assert.deepStrictEqual(stateOf([readyView(), readyView()], true), { state: 'published', blocked_mention: 0 });
    assert.strictEqual(after.first_blocking_cmd_id, null);
  });
});

describe('16.8 / AC9-AC10 — état et ligne de compteurs d’un équipement (successeurs de buildPublicationSummaryLabel)', () => {
  const items = (diags, published) => M.buildEquipmentCounterLabels(stateTree(diags, published)).items;

  it('vert : Publié + compte des publiées', () => {
    assert.strictEqual(stateOf([readyView(), readyView()], true).state, 'published');
    assert.deepStrictEqual(items([readyView(), readyView()], true), ['2 publiées']);
  });

  it('bloqué : Bloqué + compte des bloquées', () => {
    assert.strictEqual(stateOf([blockingView()], false).state, 'blocked');
    assert.strictEqual(M.EQUIPMENT_STATE_LABELS.blocked, 'Bloqué');
    assert.deepStrictEqual(items([blockingView()], false), ['1 bloquée']);
  });

  it('mixte : compte des publiées ET des bloquées, sans état partiel', () => {
    assert.strictEqual(stateOf([readyView(), blockingView()], true).state, 'published');
    assert.deepStrictEqual(items([readyView(), blockingView()], true), ['1 publiée', '1 bloquée']);
  });

  it('vide : « Rien à publier »', () => {
    assert.strictEqual(stateOf([], false).state, 'nothing_to_publish');
    assert.strictEqual(M.EQUIPMENT_STATE_LABELS.nothing_to_publish, 'Rien à publier');
  });

  it('cas de l’eq 391 : 3 prêtes + 1 non couverte → Publié, la non couverte est ignorée (jamais bloquée)', () => {
    const diags = [readyView(), readyView(), readyView(), uncoveredView()];
    assert.deepStrictEqual(stateOf(diags, true), { state: 'published', blocked_mention: 0 });
    assert.deepStrictEqual(items(diags, true), ['3 publiées', '1 ignorée']);
  });
});

// ---------------------------------------------------------------------------
// 16.8 refonte tableau — colonne diagnostic « ce qui sera publié »
// ---------------------------------------------------------------------------

describe('16.8 / tableau — buildPublishCellLabel', () => {
  it('prêt → « À appliquer → <type HA> »', () => {
    assert.strictEqual(M.buildPublishCellLabel(readyView()), 'À appliquer → Lumière (light)');
  });

  it('bloquant (capacité manquante) → « Bloquée → <raison> »', () => {
    assert.strictEqual(M.buildPublishCellLabel(blockingView()), 'Bloquée → position manquant');
  });

  it('bloquant (champ manquant) → mentionne le champ', () => {
    const view = {
      ha_entity_type: 'switch',
      projection_validity: { is_valid: false, reason_code: 'missing_field', missing_capabilities: [], missing_fields: ['command_topic'] },
      should_publish: false,
      publication_reason: 'projection_invalid',
    };
    assert.strictEqual(M.buildPublishCellLabel(view), 'Bloquée → command_topic manquant');
  });

  it('diagnostic absent (unknown) → tiret neutre', () => {
    assert.strictEqual(M.buildPublishCellLabel(null), '—');
  });
});

describe('20.1 / AC7 — sélecteur de type HA', () => {
  it('reste actif pour les diagnostics prêts ou bloquants', () => {
    assert.deepStrictEqual(M.getOverrideSelectorState({ covered: true, diagnostic: readyView() }), { active: true, reason: null });
    assert.deepStrictEqual(M.getOverrideSelectorState({ covered: true, diagnostic: blockingView() }), { active: true, reason: null });
  });

  it('est désactivé avec une raison factuelle pour non couverte, exclue et désactivée', () => {
    assert.match(M.getOverrideSelectorState({ covered: false, diagnostic: uncoveredView() }).reason, /Aucun type Home Assistant ne couvre/);
    assert.match(M.getOverrideSelectorState({ covered: false, diagnostic: Object.assign({}, disabledView(), { publication_reason: 'excluded_plugin' }) }).reason, /exclue/);
    assert.match(M.getOverrideSelectorState({ covered: false, diagnostic: disabledView() }).reason, /désactivé/);
    assert.strictEqual(M.getOverrideSelectorState({ covered: false, diagnostic: disabledView() }).active, false);
  });
});

describe('16.8 / tableau — buildBlockingReason', () => {
  it('priorise les champs manquants sur les codes', () => {
    const view = {
      projection_validity: { is_valid: false, reason_code: 'x', missing_capabilities: ['cap'], missing_fields: ['command_topic'] },
      should_publish: false,
      publication_reason: 'projection_invalid',
    };
    assert.strictEqual(M.buildBlockingReason(view), 'command_topic manquant');
  });

  it('vue prête → pas de raison', () => {
    assert.strictEqual(M.buildBlockingReason(readyView()), '');
  });

  // #809 — lumière actionnable réellement bloquée par ambiguïté de mapping :
  // publication_reason=ambiguous_skipped l'emporte sur le symptôme command_topic manquant.
  it('cause de décision (ambiguous_skipped) prime sur le symptôme command_topic', () => {
    const view = {
      ha_entity_type: 'light',
      reason_code: 'conflicting_generic_types',
      publication_reason: 'ambiguous_skipped',
      should_publish: false,
      projection_validity: {
        is_valid: false,
        reason_code: 'ha_missing_command_topic',
        missing_capabilities: ['has_command'],
        missing_fields: ['command_topic'],
      },
    };
    const reason = M.buildBlockingReason(view);
    assert.match(reason, /ambig/i);
    assert.doesNotMatch(reason, /command_topic/);
    assert.strictEqual(M.buildPublishCellLabel(view), 'Bloquée → ' + reason);
  });

  it('symptôme ha_missing_command_topic → libellé « non pilotable » quand c’est la seule cause', () => {
    const view = {
      ha_entity_type: 'switch',
      publication_reason: null,
      reason_code: null,
      should_publish: false,
      projection_validity: {
        is_valid: false,
        reason_code: 'ha_missing_command_topic',
        missing_capabilities: [],
        missing_fields: ['command_topic'],
      },
    };
    assert.match(M.buildBlockingReason(view), /non pilotable/i);
  });
});

describe('16.8 / AC12 « jamais vide » — commande non couverte', () => {
  it('readPreviewCovered → false quand le backend renvoie covered:false', () => {
    assert.strictEqual(M.readPreviewCovered({ payload: { covered: false, overridden: null } }), false);
  });

  it('readPreviewCovered → true quand covered:true', () => {
    assert.strictEqual(M.readPreviewCovered({ payload: { covered: true } }), true);
  });

  it('readPreviewCovered → true par défaut (rétro-compat backend sans le champ)', () => {
    assert.strictEqual(M.readPreviewCovered({ payload: { overridden: {} } }), true);
    assert.strictEqual(M.readPreviewCovered(null), true);
  });

  it('accepte aussi un payload déjà déballé', () => {
    assert.strictEqual(M.readPreviewCovered({ covered: false }), false);
  });

  it('buildUncoveredLabel → message factuel « Ignorée → sans équivalent dans Home Assistant »', () => {
    assert.match(M.buildUncoveredLabel(), /sans équivalent dans Home Assistant/i);
    assert.match(M.buildUncoveredLabel(), /^Ignorée/);
  });
});
