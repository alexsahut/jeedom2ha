// ARTEFACT — Story 20.3 (AC3, AC7, Q1=A) : compteurs de la pièce ouverte, dénombrés
// uniquement à partir des arbres du démon (evaluate_equipment()) ; aucune décision recalculée.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

function view(reason, valid, publish) {
  return {
    ha_entity_type: valid ? 'light' : null,
    projection_validity: { is_valid: valid, reason_code: valid ? null : reason, missing_capabilities: [], missing_fields: [] },
    should_publish: publish,
    publication_reason: reason,
  };
}
const READY = view('sure', true, true);
const BLOCKING = view('projection_invalid', false, false);
const UNCOVERED = view('command_not_covered', false, false);
const EXCLUDED_BY_USER = view('publication_excluded_eqlogic', false, false);
const DISABLED = view('disabled_eqlogic', false, false);

// Story 22.2 (Q1 A, Q2 A) : « publié » = présence réelle dans HA (`sync_status.published_in_ha`,
// `commands[].published_in_ha`). Story 25.1 : un équipement n'a qu'UN état (resolveEquipmentState) ;
// la pièce les dénombre (`by_state`), les commandes se comptent par équipement (`commands`).
function tree(id, diags, opts) {
  const o = opts || {};
  const present = o.present === undefined ? null : o.present;
  return {
    jeedom_eq_id: id,
    mapped: true,
    equipment_decision: o.decision || null,
    entities: o.entities || [],
    sync_status: {
      synced_should_publish: o.neverSynced ? null : true,
      current_should_publish: o.current === undefined ? true : o.current,
      published_in_ha: present,
      override_pending: o.pending === true,
    },
    commands: diags.map((d, i) => ({
      jeedom_cmd_id: id * 100 + i, cmd_name: 'C' + i, diagnostic: d,
      published_in_ha: o.cmdPresent === undefined ? present : o.cmdPresent[i],
    })),
  };
}

describe('22.2 / AC1 (25.1) — summarizeRoom : un état par équipement', () => {
  it('compte les équipements d’après la présence dans HA, pas d’après les diagnostics', () => {
    const s = M.summarizeRoom([
      tree(1, [READY, READY], { present: true }),                      // Publié
      tree(2, [READY, BLOCKING, UNCOVERED], { present: true, cmdPresent: [true, false, false] }), // Publié (avec la mention d’une bloquée)
      tree(3, [BLOCKING], { present: false, current: false }),         // Bloqué
      tree(4, [EXCLUDED_BY_USER], { present: false }),                 // Exclu
      tree(5, [DISABLED], { present: false }),                         // Désactivé
      tree(6, [READY], { present: false }),                            // diagnostic prêt MAIS absent de HA : À appliquer
    ], 6);
    assert.deepEqual(s.by_state, { published: 2, to_apply: 1, blocked: 1, excluded: 1, disabled: 1, nothing_to_publish: 0 });
    assert.deepEqual(M.buildRoomCounterLabels(s).items.map((item) => item.text), ['2 publiés', '1 à appliquer', '1 bloqué', '1 exclu', '1 désactivé']);
    assert.equal(s.equipments_read, 6);
    assert.equal(s.defects, 2, 'la bloquée de l’équipement publié et celle de l’équipement bloqué');
  });

  it('un équipement dont un réglage attend d’être appliqué est « À appliquer », jamais « Bloqué »', () => {
    const pendingEntity = { ha_entity_type: 'light', command_ids: [301], override_pending: true };
    const s = M.summarizeRoom([
      tree(3, [READY], { present: false, pending: true }),
      tree(3, [READY], { present: false, entities: [pendingEntity] }),
    ], 2);
    assert.equal(s.by_state.to_apply, 2);
    assert.equal(s.by_state.blocked, 0);
  });

  it('jamais synchronisé : les entités marquées en attente faute de décision ne comptent pas comme réglage en attente', () => {
    const pendingEntity = { ha_entity_type: 'light', command_ids: [100], override_pending: true };
    const s = M.summarizeRoom([tree(1, [BLOCKING], { present: false, neverSynced: true, current: false, entities: [pendingEntity] })], 1);
    assert.equal(s.by_state.to_apply, 0);
    assert.equal(s.by_state.blocked, 1);
    assert.equal(s.defects, 1);
  });

  it('un équipement publié qui a aussi une modification en attente est « À appliquer » (un seul état, R1 avant R2)', () => {
    const s = M.summarizeRoom([tree(1, [READY], { present: true, pending: true })], 1);
    assert.equal(s.by_state.published, 0);
    assert.equal(s.by_state.to_apply, 1);
  });

  it('présence inconnue (démon plus ancien) : jamais comptée publiée, dite inconnue', () => {
    const s = M.summarizeRoom([tree(1, [READY, BLOCKING], { present: null })], 1);
    assert.equal(s.by_state.published, 0);
    assert.equal(s.by_state.to_apply, 1, 'R6 : à appliquer, jamais publié');
    assert.equal(s.equipments_presence_unknown, 1);
    assert.match(M.buildRoomCounterLabels(s).presence_unknown, /^1 équipement dont la présence/);
  });

  it('une commande est publiée si au moins une entité présente la porte (forme 579) ; bloquée ou ignorée sinon', () => {
    // Commande 0 : principal refusé (diagnostic bloquant) mais portée par un secondaire présent.
    const c = M.summarizeEquipmentCounters(
      tree(1, [READY, BLOCKING, UNCOVERED, BLOCKING], { present: true, cmdPresent: [true, false, false, false] }));
    assert.equal(c.commands.published, 1);
    assert.equal(c.commands.blocked, 2, 'bloquées absentes de HA');
    assert.equal(c.commands.ignored, 1, 'non couverte absente de HA');
    assert.equal(c.defects, 2);
  });

  it('une commande bloquante mais présente via un autre porteur n’est jamais « bloquée »', () => {
    const c = M.summarizeEquipmentCounters(tree(1, [BLOCKING], { present: true, cmdPresent: [true] }));
    assert.equal(c.commands.published, 1);
    assert.equal(c.commands.blocked, 0);
    assert.equal(c.defects, 0);
  });

  it('entités en attente : l’équipement est « À appliquer », ses commandes déjà dans HA restent publiées', () => {
    const entities = [{ ha_entity_type: 'light', command_ids: [100, 101], override_pending: true },
      { ha_entity_type: 'sensor', command_ids: [102], override_pending: false }];
    const c = M.summarizeEquipmentCounters(tree(1, [READY, READY, READY], { present: true, entities }));
    assert.equal(c.state, 'to_apply');
    assert.equal(c.commands.published, 3);
  });

  it('une exclusion posée par l’utilisateur est comptée « exclue », jamais « bloquée »', () => {
    const t = tree(1, [EXCLUDED_BY_USER, EXCLUDED_BY_USER], { present: false });
    const s = M.summarizeRoom([t], 1);
    assert.equal(s.by_state.excluded, 1);
    assert.equal(s.by_state.blocked, 0);
    assert.equal(s.defects, 0);
    assert.equal(M.summarizeEquipmentCounters(t).commands.excluded, 2);
  });

  it('un équipement désactivé n’est jamais compté bloqué', () => {
    const s = M.summarizeRoom([tree(1, [DISABLED, DISABLED], { present: false })], 1);
    assert.equal(s.by_state.disabled, 1);
    assert.equal(s.by_state.blocked, 0);
    assert.equal(s.defects, 0);
  });

  it('équipement exclu sans commande : lu dans equipment_decision (20.2 AC8)', () => {
    const s = M.summarizeRoom([
      tree(1, [], { decision: EXCLUDED_BY_USER, present: false }),
      tree(2, [], { decision: DISABLED, present: false }),
    ], 2);
    assert.equal(s.by_state.excluded, 1);
    assert.equal(s.by_state.disabled, 1);
  });

  it('arbres non lus : signalés, non comptés', () => {
    const s = M.summarizeRoom([tree(1, [READY], { present: true })], 3);
    assert.equal(s.equipments_read, 1);
    assert.equal(M.buildRoomCounterLabels(s).unread, '2 équipements non lus');
  });

  it('entrée invalide : zéro partout, sans exception', () => {
    const s = M.summarizeRoom(null, 0);
    assert.equal(Object.values(s.by_state).reduce((a, b) => a + b, 0) + s.defects, 0);
    assert.deepEqual(M.buildRoomCounterLabels(s).items, []);
    assert.equal(M.buildRoomCounterLabels(s).unread, '');
    assert.equal(M.buildRoomCounterLabels(s).presence_unknown, '');
  });
});

describe('22.2 / AC1 (25.1) — libellés d’unité', () => {
  it('chaque compteur dit son état en un mot court avec accord singulier / pluriel, zéros masqués', () => {
    const labels = M.buildRoomCounterLabels({
      equipments_total: 8, equipments_read: 8,
      by_state: { published: 1, to_apply: 2, blocked: 3, excluded: 2, disabled: 0, nothing_to_publish: 1 },
    });
    assert.deepEqual(labels.items.map((i) => i.text), [
      '1 publié', '2 à appliquer', '3 bloqués', '2 exclus', '1 rien à publier',
    ]);
  });
});

describe('20.3 / AC7 — le dénombrement ne lit que l’arbre de la pièce ouverte', () => {
  const surface = fs.readFileSync('desktop/js/jeedom2ha_mapping_surface.js', 'utf8');
  const override = fs.readFileSync('desktop/js/jeedom2ha_mapping_override.js', 'utf8');

  it('les compteurs sont alimentés depuis ctx.trees (arbres de la pièce) par M.summarizeRoom', () => {
    assert.match(surface, /M\.summarizeRoom\(trees, ctx\.room\.equipments\.length, roomEnabledById\(\)\)/);
    assert.match(surface, /ctx\.trees\[eqId\] = normalized;/);
  });

  it('aucune lecture globale du parc depuis la surface', () => {
    assert.doesNotMatch(surface, /getDiagnostics|getPublishedScopeForConsole|published_scope|diagnostic_equipments|home_signals/);
    assert.doesNotMatch(override, /published_scope|diagnostic_equipments|home_signals/);
  });
});

describe('25.1 / AC9 — mots courts de la ligne des états (assertions rétablies)', () => {
  it('un état non nul = un chiffre et son mot ; l’ordre est celui des états', () => {
    const s = M.summarizeRoom([tree(1, [READY], { present: true }), tree(2, [DISABLED], { present: false })], 2);
    const labels = M.buildRoomCounterLabels(s);
    assert.deepEqual(labels.items.map((item) => item.text), ['1 publié', '1 désactivé']);
    assert.deepEqual(labels.items.map((item) => item.state), ['published', 'disabled']);
    assert.equal(labels.unread, '');
  });
});
