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
