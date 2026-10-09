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

  it('seulement désactivées : badge neutre dédié et libellé factuel', () => {
    const s = M.summarizePublication(treeWith([disabledView(), disabledView()]));
    assert.strictEqual(M.publicationSummaryState(s), 'disabled');
    assert.strictEqual(
      M.buildPublicationSummaryLabel(s),
      'Désactivé dans Jeedom : ne sera pas publié dans Home Assistant.');
    assert.strictEqual(
      M.buildDisabledLabel(disabledView()),
      'Ne sera pas publié — équipement désactivé dans Jeedom');
  });

  it('exclu l’emporte sur désactivée quand aucune commande n’est prête ou bloquante', () => {
    const excluded = Object.assign({}, disabledView(), { publication_reason: 'excluded_plugin' });
    const s = M.summarizePublication(treeWith([disabledView(), excluded]));
    assert.strictEqual(M.publicationSummaryState(s), 'excluded');
  });

  it('toutes prêtes → sera publié, 0 bloquante', () => {
    const s = M.summarizePublication(treeWith([readyView(), readyView()]));
    assert.strictEqual(s.total, 2);
    assert.strictEqual(s.ready_count, 2);
    assert.strictEqual(s.blocking_count, 0);
    assert.strictEqual(s.will_publish, true);
    assert.strictEqual(s.first_blocking_cmd_id, null);
    assert.strictEqual(M.publicationSummaryState(s), 'publish');
  });

  it('aucune prête, que des bloquantes → ne sera pas publié', () => {
    const s = M.summarizePublication(treeWith([blockingView(), blockingView()]));
    assert.strictEqual(s.will_publish, false);
    assert.strictEqual(s.blocking_count, 2);
    assert.strictEqual(M.publicationSummaryState(s), 'blocked');
  });

  it('mixte → partiellement publié + première commande bloquante en ordre natif', () => {
    const s = M.summarizePublication(treeWith([readyView(), blockingView(), blockingView()]));
    assert.strictEqual(s.ready_count, 1);
    assert.strictEqual(s.blocking_count, 2);
    assert.strictEqual(s.will_publish, true);
    assert.strictEqual(s.first_blocking_cmd_id, 11); // 10 = ready, 11 = premier blocking
    assert.strictEqual(M.publicationSummaryState(s), 'partial');
  });

  it('diagnostic absent (unknown) ne compte ni prêt ni bloquant', () => {
    const s = M.summarizePublication(treeWith([null, readyView()]));
    assert.strictEqual(s.unknown_count, 1);
    assert.strictEqual(s.ready_count, 1);
    assert.strictEqual(s.blocking_count, 0);
    assert.strictEqual(s.will_publish, true);
  });

  it('équipement sans commande projetable → état vide', () => {
    const s = M.summarizePublication(treeWith([null, null]));
    assert.strictEqual(s.will_publish, false);
    assert.strictEqual(M.publicationSummaryState(s), 'empty');
  });

  it('commande non couverte (command_not_covered) : ni prête ni bloquante, jamais l’ancre', () => {
    const s = M.summarizePublication(treeWith([readyView(), uncoveredView(), readyView()]));
    assert.strictEqual(s.total, 3);
    assert.strictEqual(s.ready_count, 2);
    assert.strictEqual(s.blocking_count, 0);
    assert.strictEqual(s.uncovered_count, 1);
    assert.strictEqual(s.unknown_count, 0);
    assert.strictEqual(s.first_blocking_cmd_id, null);
    assert.strictEqual(M.publicationSummaryState(s), 'publish');
  });

  it('non couverte avant une vraie bloquante : l’ancre va à la bloquante', () => {
    const s = M.summarizePublication(treeWith([uncoveredView(), readyView(), blockingView()]));
    assert.strictEqual(s.uncovered_count, 1);
    assert.strictEqual(s.blocking_count, 1);
    assert.strictEqual(s.first_blocking_cmd_id, 12); // 10 = non couverte, 11 = prête, 12 = bloquante
    assert.strictEqual(M.publicationSummaryState(s), 'partial');
  });

  it('seulement des non couvertes → état vide, jamais « ne sera pas publié »', () => {
    const s = M.summarizePublication(treeWith([uncoveredView(), uncoveredView()]));
    assert.strictEqual(s.uncovered_count, 2);
    assert.strictEqual(s.blocking_count, 0);
    assert.strictEqual(s.will_publish, false);
    assert.strictEqual(M.publicationSummaryState(s), 'empty');
  });

  it('bascule par override : la commande devenue prête fait passer la synthèse de partiel à publié', () => {
    const before = M.summarizePublication(treeWith([readyView(), blockingView()]));
    const after = M.summarizePublication(treeWith([readyView(), readyView()]));
    assert.strictEqual(M.publicationSummaryState(before), 'partial');
    assert.strictEqual(before.first_blocking_cmd_id, 11);
    assert.strictEqual(M.publicationSummaryState(after), 'publish');
    assert.strictEqual(after.first_blocking_cmd_id, null);
  });
});

describe('16.8 / AC9-AC10 — buildPublicationSummaryLabel', () => {
  it('vert : « Sera publié » + compte prêtes', () => {
    const label = M.buildPublicationSummaryLabel(M.summarizePublication(treeWith([readyView(), readyView()])));
    assert.match(label, /Sera publié/);
    assert.match(label, /2 commande/);
  });

  it('bloqué : « Ne sera pas publié » + compte bloquantes', () => {
    const label = M.buildPublicationSummaryLabel(M.summarizePublication(treeWith([blockingView()])));
    assert.match(label, /Ne sera pas publié/);
    assert.match(label, /1 commande/);
  });

  it('partiel : compte prêtes ET bloquantes', () => {
    const label = M.buildPublicationSummaryLabel(M.summarizePublication(treeWith([readyView(), blockingView()])));
    assert.match(label, /Partiellement/);
    assert.match(label, /1 prête/);
    assert.match(label, /1 bloquante/);
  });

  it('vide : message explicite « aucune commande projetable »', () => {
    const label = M.buildPublicationSummaryLabel(M.summarizePublication(treeWith([])));
    assert.match(label, /Aucune commande projetable/);
  });

  it('cas de l’eq 391 : 3 prêtes + 1 non couverte → « Sera publié », jamais « Partiellement »', () => {
    const label = M.buildPublicationSummaryLabel(
      M.summarizePublication(treeWith([readyView(), readyView(), readyView(), uncoveredView()])));
    assert.strictEqual(label, 'Sera publié dans Home Assistant : 3 commande(s) prête(s).');
  });
});

// ---------------------------------------------------------------------------
// 16.8 refonte tableau — colonne diagnostic « ce qui sera publié »
// ---------------------------------------------------------------------------

describe('16.8 / tableau — buildPublishCellLabel', () => {
  it('prêt → « Sera publié : <type HA> »', () => {
    assert.strictEqual(M.buildPublishCellLabel(readyView()), 'Sera publié : light');
  });

  it('bloquant (capacité manquante) → « Ne sera pas publié — <raison> »', () => {
    assert.strictEqual(M.buildPublishCellLabel(blockingView()), 'Ne sera pas publié — position manquant');
  });

  it('bloquant (champ manquant) → mentionne le champ', () => {
    const view = {
      ha_entity_type: 'switch',
      projection_validity: { is_valid: false, reason_code: 'missing_field', missing_capabilities: [], missing_fields: ['command_topic'] },
      should_publish: false,
      publication_reason: 'projection_invalid',
    };
    assert.strictEqual(M.buildPublishCellLabel(view), 'Ne sera pas publié — command_topic manquant');
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
    assert.strictEqual(M.buildPublishCellLabel(view), 'Ne sera pas publié — ' + reason);
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

  it('buildUncoveredLabel → message factuel « sans type Home Assistant applicable »', () => {
    assert.match(M.buildUncoveredLabel(), /sans type Home Assistant applicable/i);
    assert.match(M.buildUncoveredLabel(), /ne sera pas publié/i);
  });
});
