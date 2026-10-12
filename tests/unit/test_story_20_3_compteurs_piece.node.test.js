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
// `commands[].published_in_ha`), plus « en attente d'application » et « non pris en charge » ;
// « exclu » et « désactivé » restent à part. L'ancien « publié » déduit des diagnostics a disparu.
function tree(id, diags, opts) {
  const o = opts || {};
  const present = o.present === undefined ? null : o.present;
  return {
    jeedom_eq_id: id,
    mapped: true,
    equipment_decision: o.decision || null,
    entities: o.entities || [],
    sync_status: { published_in_ha: present, override_pending: o.pending === true },
    commands: diags.map((d, i) => ({
      jeedom_cmd_id: id * 100 + i, cmd_name: 'C' + i, diagnostic: d,
      published_in_ha: o.cmdPresent === undefined ? present : o.cmdPresent[i],
    })),
  };
}

describe('22.2 / AC1 — summarizeRoom : publiés / en attente / non pris en charge', () => {
  it('compte les équipements d’après la présence dans HA, pas d’après les diagnostics', () => {
    const s = M.summarizeRoom([
      tree(1, [READY, READY], { present: true }),                      // publié
      tree(2, [READY, BLOCKING, UNCOVERED], { present: true }),        // publié (partiellement)
      tree(3, [BLOCKING], { present: false }),                         // non pris en charge
      tree(4, [EXCLUDED_BY_USER], { present: false }),                 // exclu
      tree(5, [DISABLED], { present: false }),                         // désactivé
      tree(6, [READY], { present: false }),                            // diagnostic prêt MAIS absent de HA
    ], 6);
    assert.equal(s.equipments_published, 2);
    assert.equal(s.equipments_unsupported, 2, 'bloquant et prêt-mais-absent : rien dans HA, rien en attente');
    assert.equal(s.equipments_excluded, 1);
    assert.equal(s.equipments_disabled, 1);
    assert.equal(s.equipments_pending, 0);
    assert.equal(s.equipments_read, 6);
  });

  it('un équipement dont un override attend d’être appliqué est « en attente », jamais « non pris en charge »', () => {
    const pendingEntity = { ha_entity_type: 'light', command_ids: [301], override_pending: true };
    const s = M.summarizeRoom([
      tree(3, [READY], { present: false, pending: true }),
      tree(3, [READY], { present: false, entities: [pendingEntity] }),
    ], 2);
    assert.equal(s.equipments_pending, 2);
    assert.equal(s.equipments_unsupported, 0);
  });

  it('un équipement publié peut aussi avoir une modification en attente (notions indépendantes)', () => {
    const s = M.summarizeRoom([tree(1, [READY], { present: true, pending: true })], 1);
    assert.equal(s.equipments_published, 1);
    assert.equal(s.equipments_pending, 1);
  });

  it('présence inconnue (démon plus ancien) : jamais comptée publiée ni non prise en charge', () => {
    const s = M.summarizeRoom([tree(1, [READY, BLOCKING], { present: null })], 1);
    assert.equal(s.equipments_published, 0);
    assert.equal(s.equipments_unsupported, 0);
    assert.equal(s.equipments_presence_unknown, 1);
    assert.equal(s.commands_published, 0);
    assert.match(M.buildRoomCounterLabels(s).presence_unknown, /^1 équipement dont la présence/);
  });

  it('une commande est publiée si au moins une entité présente la porte (forme 579) ; non prise en charge sinon', () => {
    // Commande 0 : principal refusé (diagnostic bloquant) mais portée par un secondaire présent.
    const s = M.summarizeRoom([
      tree(1, [READY, BLOCKING, UNCOVERED, BLOCKING], { present: true, cmdPresent: [true, false, false, false] }),
    ], 1);
    assert.equal(s.commands_published, 1);
    assert.equal(s.commands_unsupported, 3, 'bloquantes et non couvertes absentes de HA');
  });

  it('une commande bloquante mais présente via un autre porteur n’est jamais « non prise en charge »', () => {
    const s = M.summarizeRoom([tree(1, [BLOCKING], { present: true, cmdPresent: [true] })], 1);
    assert.equal(s.commands_published, 1);
    assert.equal(s.commands_unsupported, 0);
  });

  it('commandes en attente : portées par une entité dont l’override n’est pas appliqué', () => {
    const entities = [{ ha_entity_type: 'light', command_ids: [100, 101], override_pending: true },
      { ha_entity_type: 'sensor', command_ids: [102], override_pending: false }];
    const s = M.summarizeRoom([tree(1, [READY, READY, READY], { present: true, entities })], 1);
    assert.equal(s.commands_pending, 2);
    assert.equal(s.commands_published, 3);
  });

  it('une exclusion posée par l’utilisateur est comptée « exclue », jamais « non prise en charge »', () => {
    const s = M.summarizeRoom([tree(1, [EXCLUDED_BY_USER, EXCLUDED_BY_USER], { present: false })], 1);
    assert.equal(s.equipments_excluded, 1);
    assert.equal(s.equipments_unsupported, 0);
    assert.equal(s.commands_unsupported, 0);
  });

  it('un équipement désactivé n’est jamais compté non pris en charge', () => {
    const s = M.summarizeRoom([tree(1, [DISABLED, DISABLED], { present: false })], 1);
    assert.equal(s.equipments_disabled, 1);
    assert.equal(s.equipments_unsupported, 0);
    assert.equal(s.commands_unsupported, 0);
  });

  it('équipement exclu sans commande : lu dans equipment_decision (20.2 AC8)', () => {
    const s = M.summarizeRoom([
      tree(1, [], { decision: EXCLUDED_BY_USER, present: false }),
      tree(2, [], { decision: DISABLED, present: false }),
    ], 2);
    assert.equal(s.equipments_excluded, 1);
    assert.equal(s.equipments_disabled, 1);
  });

  it('arbres non lus : signalés, non comptés', () => {
    const s = M.summarizeRoom([tree(1, [READY], { present: true })], 3);
    assert.equal(s.equipments_read, 1);
    assert.equal(M.buildRoomCounterLabels(s).unread, '2 équipements non lus');
  });

  it('entrée invalide : zéro partout, sans exception', () => {
    const s = M.summarizeRoom(null, 0);
    assert.equal(s.equipments_published + s.commands_published + s.equipments_unsupported, 0);
    assert.equal(M.buildRoomCounterLabels(s).unread, '');
    assert.equal(M.buildRoomCounterLabels(s).presence_unknown, '');
  });
});

describe('22.2 / AC1 — libellés d’unité', () => {
  it('chaque compteur dit son unité (équipement ou commande) avec accord singulier / pluriel', () => {
    const labels = M.buildRoomCounterLabels({
      equipments_total: 4, equipments_read: 4,
      equipments_published: 1, equipments_pending: 2, equipments_unsupported: 3,
      equipments_excluded: 2, equipments_disabled: 0,
      commands_published: 1, commands_pending: 0, commands_unsupported: 2,
    });
    assert.deepEqual(labels.equipments, [
      '1 équipement publié dans Home Assistant', '2 équipements en attente d’application',
      '3 équipements non pris en charge', '2 équipements exclus',
      '0 équipement désactivé dans Jeedom',
    ]);
    assert.deepEqual(labels.commands, [
      '1 commande publiée dans Home Assistant', '0 commande en attente d’application',
      '2 commandes non prises en charge',
    ]);
  });
});

describe('20.3 / AC7 — le dénombrement ne lit que l’arbre de la pièce ouverte', () => {
  const surface = fs.readFileSync('desktop/js/jeedom2ha_mapping_surface.js', 'utf8');
  const override = fs.readFileSync('desktop/js/jeedom2ha_mapping_override.js', 'utf8');

  it('les compteurs sont alimentés depuis ctx.trees (arbres de la pièce) par M.summarizeRoom', () => {
    assert.match(surface, /M\.summarizeRoom\(trees, ctx\.room\.equipments\.length\)/);
    assert.match(surface, /ctx\.trees\[eqId\] = normalized;/);
  });

  it('aucune lecture globale du parc depuis la surface', () => {
    assert.doesNotMatch(surface, /getDiagnostics|getPublishedScopeForConsole|published_scope|diagnostic_equipments|home_signals/);
    assert.doesNotMatch(override, /published_scope|diagnostic_equipments|home_signals/);
  });
});
