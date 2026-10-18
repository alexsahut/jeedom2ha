// ARTEFACT — Story 25.1 (AC1, AC2) : une seule fonction d'état d'équipement, pure et déterministe.
// Table de vérité D1 (R1 à R8) avec les états attendus écrits en dur. Identifiants génériques
// uniquement (CC-48).
'use strict';

const fs = require('node:fs');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const { view, READY, EXCLUDED, DISABLED } = require('./helpers/ui_harness');

const STATES = ['published', 'to_apply', 'blocked', 'excluded', 'disabled', 'nothing_to_publish'];
const BLOCKED = view('no_generic_type_configured', false, false);
const IGNORED = view('command_not_covered', false, false);
const EXCLUDED_OBJECT = view('excluded_object', false, false);

/** Commande d'un arbre de démon ; `published` = présence dans HA de la commande. */
function cmd(id, diagnostic, published) {
  return { jeedom_cmd_id: id, cmd_name: 'Commande ' + id, diagnostic, covered: true, published_in_ha: published === undefined ? false : published };
}

/** Arbre minimal ; `sync` complète/écrase le bloc `sync_status`. */
function eq(options) {
  const o = options || {};
  const sync = Object.assign({ synced_should_publish: true, current_should_publish: true, override_pending: false, published_in_ha: false }, o.sync || {});
  return {
    jeedom_eq_id: 1,
    eq_name: 'Équipement 1',
    mapped: true,
    eligible: true,
    equipment_decision: o.decision || null,
    entities: o.entities || [],
    sync_status: sync,
    commands: o.commands || [],
  };
}

const pendingEntity = { ha_entity_type: 'light', command_ids: [1], decision: READY, override_pending: true };

function stateOf(tree) { return M.resolveEquipmentState(tree).state; }

describe('25.1 / AC1 — une seule fonction d’état', () => {
  it('resolveEquipmentState est exportée ; publicationSummaryState et buildPublicationSummaryLabel n’existent plus', () => {
    assert.equal(typeof M.resolveEquipmentState, 'function');
    assert.equal(M.publicationSummaryState, undefined);
    assert.equal(M.buildPublicationSummaryLabel, undefined);
    for (const file of fs.readdirSync('desktop/js')) {
      const text = fs.readFileSync('desktop/js/' + file, 'utf8');
      assert.doesNotMatch(text, /publicationSummaryState|buildPublicationSummaryLabel/, file);
    }
  });

  it('les compteurs obtiennent l’état uniquement via resolveEquipmentState (pas de ready_count/blocking_count)', () => {
    const source = fs.readFileSync('desktop/js/jeedom2ha_mapping_override.js', 'utf8');
    // summarizeRoom délègue à summarizeEquipmentCounters, qui appelle resolveEquipmentState.
    const delegate = { summarizeEquipmentCounters: /resolveEquipmentState/, summarizeRoom: /summarizeEquipmentCounters/ };
    for (const fn of Object.keys(delegate)) {
      const body = source.match(new RegExp('function ' + fn + '\\([\\s\\S]*?\\n  \\}\\n'))[0];
      assert.match(body, delegate[fn], fn);
      assert.doesNotMatch(body, /ready_count|blocking_count/, fn);
    }
  });
});

describe('25.1 / AC2 — table de vérité D1', () => {
  it('R1 : réglage en attente → to_apply, même si l’équipement est dans HA', () => {
    assert.equal(stateOf(eq({ commands: [cmd(1, READY, true)], sync: { published_in_ha: true }, entities: [pendingEntity] })), 'to_apply');
    assert.equal(stateOf(eq({ commands: [cmd(1, READY, true)], sync: { published_in_ha: true, override_pending: true } })), 'to_apply');
  });

  it('R2 : présent dans HA → published', () => {
    assert.equal(stateOf(eq({ commands: [cmd(1, READY, true)], sync: { published_in_ha: true } })), 'published');
  });

  it('R3 : désactivé dans Jeedom → disabled', () => {
    assert.equal(stateOf(eq({ decision: DISABLED, commands: [cmd(1, DISABLED)] })), 'disabled');
  });

  it('R4 : exclu (décision d’équipement, ou toutes les commandes exclues) → excluded', () => {
    assert.equal(stateOf(eq({ decision: EXCLUDED, commands: [cmd(1, EXCLUDED)] })), 'excluded');
    assert.equal(stateOf(eq({ commands: [cmd(1, EXCLUDED), cmd(2, EXCLUDED)] })), 'excluded');
  });

  it('R5 : publication due mais pas faite (P false, r > 0, plan courant true) → to_apply', () => {
    assert.equal(stateOf(eq({ commands: [cmd(1, READY)], sync: { published_in_ha: false, current_should_publish: true } })), 'to_apply');
  });

  it('R6 : présence inconnue (démon plus ancien), r > 0 → to_apply, jamais published', () => {
    const tree = eq({ commands: [cmd(1, READY, null)], sync: { published_in_ha: null, current_should_publish: null } });
    assert.equal(stateOf(tree), 'to_apply');
    assert.notEqual(stateOf(eq({ commands: [cmd(1, READY, null)], sync: { published_in_ha: null, current_should_publish: true } })), 'published');
  });

  it('R7 : commande bloquée, rien dans HA → blocked', () => {
    assert.equal(stateOf(eq({ commands: [cmd(1, BLOCKED)], sync: { current_should_publish: false } })), 'blocked');
  });

  it('R8 : rien de publiable ni de bloqué → nothing_to_publish', () => {
    assert.equal(stateOf(eq({ commands: [cmd(1, IGNORED), cmd(2, IGNORED)], sync: { current_should_publish: false } })), 'nothing_to_publish');
    assert.equal(stateOf(eq({ decision: view('no_commands', false, false), commands: [] })), 'nothing_to_publish');
  });

  it('croisements : « Désactivé » l’emporte sur « Exclu »', () => {
    assert.equal(stateOf(eq({ decision: DISABLED, commands: [cmd(1, EXCLUDED)] })), 'disabled');
    assert.equal(stateOf(eq({ decision: DISABLED, commands: [cmd(1, EXCLUDED)], sync: { published_in_ha: false } })), 'disabled');
    assert.equal(stateOf(eq({ commands: [cmd(1, DISABLED), cmd(2, EXCLUDED)] })), 'disabled');
  });

  it('croisements : P true + commandes bloquées → published avec la mention du nombre de bloquées', () => {
    const result = M.resolveEquipmentState(eq({
      commands: [cmd(1, READY, true), cmd(2, BLOCKED), cmd(3, BLOCKED), cmd(4, IGNORED)], sync: { published_in_ha: true },
    }));
    assert.deepEqual(result, { state: 'published', blocked_mention: 2 });
  });

  it('croisements : P true + réglage en attente → to_apply (la mention suit)', () => {
    const result = M.resolveEquipmentState(eq({
      commands: [cmd(1, READY, true), cmd(2, BLOCKED)], sync: { published_in_ha: true }, entities: [pendingEntity],
    }));
    assert.deepEqual(result, { state: 'to_apply', blocked_mention: 1 });
  });

  it('croisements : P false, r > 0, sans attente → to_apply', () => {
    assert.equal(stateOf(eq({ commands: [cmd(1, READY), cmd(2, BLOCKED)], sync: { published_in_ha: false } })), 'to_apply');
  });

  it('croisements : jamais synchronisé + override_pending du démon → pas de to_apply par R1', () => {
    // Plan courant sans publication : R5 ne s'applique pas non plus, donc rien ne justifie « À appliquer ».
    const never = { synced_should_publish: null, current_should_publish: false, published_in_ha: false, override_pending: true };
    assert.notEqual(stateOf(eq({ commands: [cmd(1, READY)], sync: never, entities: [pendingEntity] })), 'to_apply');
    assert.equal(stateOf(eq({ commands: [cmd(1, BLOCKED)], sync: never, entities: [pendingEntity] })), 'blocked');
  });

  it('croisements : P false, r > 0, plan courant false → jamais to_apply (R7 ou R8)', () => {
    const hors = { published_in_ha: false, current_should_publish: false };
    assert.equal(stateOf(eq({ commands: [cmd(1, READY), cmd(2, BLOCKED)], sync: hors })), 'blocked');
    assert.equal(stateOf(eq({ commands: [cmd(1, READY)], sync: hors })), 'nothing_to_publish');
  });

  it('croisements : pièce exclue (excluded_object) → catégorie Exclue, équipement « excluded »', () => {
    assert.equal(M.classifyCommandCategory(cmd(1, EXCLUDED_OBJECT)), 'excluded');
    assert.equal(stateOf(eq({ decision: EXCLUDED_OBJECT, commands: [cmd(1, EXCLUDED_OBJECT)] })), 'excluded');
  });

  it('croisements : seul un capteur secondaire est publié (principal refusé, P true) → published', () => {
    const result = M.resolveEquipmentState(eq({
      commands: [cmd(1, BLOCKED), cmd(2, READY, true)], sync: { synced_should_publish: false, current_should_publish: false, published_in_ha: true },
    }));
    assert.equal(result.state, 'published');
  });

  it('croisements : équipement sans commande — exclu → excluded, désactivé → disabled', () => {
    assert.equal(stateOf(eq({ decision: EXCLUDED, commands: [] })), 'excluded');
    assert.equal(stateOf(eq({ decision: DISABLED, commands: [] })), 'disabled');
  });

  it('croisements : commandes toutes ignorées → nothing_to_publish', () => {
    assert.equal(stateOf(eq({ commands: [cmd(1, IGNORED)], sync: { current_should_publish: null } })), 'nothing_to_publish');
  });
});

function deepFreeze(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.freeze(value);
    Object.values(value).forEach(deepFreeze);
  }
  return value;
}

describe('25.1 / AC2 — pureté et domaine de sortie', () => {
  it('ne mute pas l’arbre (gel profond) et rend des résultats identiques à chaque appel', () => {
    const tree = deepFreeze(eq({ commands: [cmd(1, READY), cmd(2, BLOCKED)], entities: [pendingEntity], decision: READY }));
    const first = M.resolveEquipmentState(tree);
    const second = M.resolveEquipmentState(tree);
    assert.deepEqual(first, second);
    assert.deepEqual(first, { state: 'to_apply', blocked_mention: 1 });
  });

  it('aucun état hors des six sur le produit cartésien des booléens et de P ∈ {true, false, null}', () => {
    const triState = [true, false, null];
    const commandSets = [[], [cmd(1, READY)], [cmd(1, BLOCKED)], [cmd(1, IGNORED)], [cmd(1, EXCLUDED)],
      [cmd(1, DISABLED)], [cmd(1, READY, true), cmd(2, BLOCKED)], [cmd(1, null)]];
    const decisions = [null, EXCLUDED, DISABLED, READY];
    let count = 0;
    for (const P of triState) for (const current of triState) for (const synced of triState)
      for (const pending of [true, false]) for (const entityPending of [true, false])
        for (const commands of commandSets) for (const decision of decisions) {
          const result = M.resolveEquipmentState(eq({
            commands, decision,
            sync: { published_in_ha: P, current_should_publish: current, synced_should_publish: synced, override_pending: pending },
            entities: entityPending ? [pendingEntity] : [],
          }));
          assert.ok(STATES.includes(result.state), JSON.stringify(result));
          assert.ok(Number.isInteger(result.blocked_mention) && result.blocked_mention >= 0);
          if (!['published', 'to_apply'].includes(result.state)) assert.equal(result.blocked_mention, 0);
          count += 1;
        }
    assert.equal(count, 3 * 3 * 3 * 2 * 2 * 8 * 4);
  });

  it('un arbre vide ou illisible reste dans le domaine', () => {
    for (const input of [null, undefined, {}, { commands: 'x' }]) {
      assert.ok(STATES.includes(M.resolveEquipmentState(input).state));
    }
  });
});
