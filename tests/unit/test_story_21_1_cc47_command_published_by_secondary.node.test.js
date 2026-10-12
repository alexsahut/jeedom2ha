// Story 21.1 (bloc B, CC-47) — une commande portée par un principal refusé ET par une entité
// secondaire publiée s'affiche « Sera publié : <type du secondaire> », et la synthèse de
// l'équipement comme les totaux de pièce la comptent « prête ». L'écran ne fait que consommer
// la décision par commande du démon (aucun recalcul propre à l'UI) ; arbre de la forme d'un
// équipement de terrain, identifiants synthétiques uniquement.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

function view(type, reason, valid, publish, extra) {
  return Object.assign({
    ha_entity_type: type,
    reason_code: null,
    projection_validity: { is_valid: valid, reason_code: valid ? null : reason, missing_capabilities: [], missing_fields: [] },
    should_publish: publish,
    publication_reason: reason,
  }, extra || {});
}

const PUBLISHED_BINARY = view('binary_sensor', 'sure', true, true);
const PUBLISHED_SENSOR = view('sensor', 'sure', true, true);
const REFUSED_PRIMARY = view('switch', 'ambiguous_skipped', false, false, { reason_code: 'switch_state_orphan' });
const UNCOVERED = view(null, 'command_not_covered', false, false);
const EXCLUDED = view('switch', 'publication_excluded_eqlogic', false, false);
const DISABLED = view(null, 'disabled_eqlogic', false, false);
const FORCED = view('switch', 'publication_forced', true, true);

const STATE_CMD = 5369;

// Forme de l'équipement de terrain : principal `switch` refusé (état sans ordre On/Off) + cinq
// entités secondaires publiées ; la commande d'état est portée par le principal ET par un
// `binary_sensor`. Le démon résout la commande vers l'entité qui la publie.
function tree579() {
  return {
    jeedom_eq_id: 579,
    mapped: true,
    equipment_decision: REFUSED_PRIMARY,
    entities: [
      { ha_entity_type: 'switch', command_ids: [STATE_CMD], decision: REFUSED_PRIMARY, override_pending: false },
      { ha_entity_type: 'binary_sensor', command_ids: [STATE_CMD], decision: PUBLISHED_BINARY, override_pending: false },
    ],
    commands: [
      { jeedom_cmd_id: 5368, cmd_name: 'C0', covered: false, diagnostic: UNCOVERED },
      { jeedom_cmd_id: STATE_CMD, cmd_name: 'Etat', covered: true, diagnostic: PUBLISHED_BINARY },
      { jeedom_cmd_id: 5493, cmd_name: 'C2', covered: true, diagnostic: PUBLISHED_SENSOR },
      { jeedom_cmd_id: 5494, cmd_name: 'C3', covered: true, diagnostic: PUBLISHED_SENSOR },
      { jeedom_cmd_id: 5689, cmd_name: 'C4', covered: true, diagnostic: PUBLISHED_SENSOR },
      { jeedom_cmd_id: 5695, cmd_name: 'C5', covered: true, diagnostic: PUBLISHED_SENSOR },
    ],
  };
}

describe('21.1 / AC8 — ligne d’une commande publiée par une entité secondaire', () => {
  it('la ligne affiche « Sera publié : binary_sensor », jamais « Ne sera pas publié »', () => {
    const row = tree579().commands.find((c) => c.jeedom_cmd_id === STATE_CMD);
    const label = M.buildPublishCellLabel(row.diagnostic);
    assert.equal(label, 'Sera publié : binary_sensor');
    assert.doesNotMatch(label, /Ne sera pas publié/);
    assert.equal(M.diagnosticState(row.diagnostic), 'ready');
    assert.equal(M.buildBlockingReason(row.diagnostic), '');
  });

  it('la synthèse de l’équipement compte 5 prêtes, 0 bloquante, 1 non couverte', () => {
    const s = M.summarizePublication(tree579());
    assert.equal(s.ready_count, 5);
    assert.equal(s.blocking_count, 0);
    assert.equal(s.uncovered_count, 1);
    assert.equal(s.will_publish, true);
    assert.equal(s.first_blocking_cmd_id, null);
    assert.equal(M.buildPublicationSummaryLabel(s), 'Sera publié dans Home Assistant : 5 commande(s) prête(s).');
    assert.doesNotMatch(M.buildPublicationSummaryLabel(s), /bloquante/);
  });

  it('les totaux de pièce comptent la commande prête et aucune bloquante', () => {
    const s = M.summarizeRoom([tree579()], 1);
    assert.equal(s.commands_ready, 5);
    assert.equal(s.commands_blocking, 0);
    assert.equal(s.commands_uncovered, 1);
    assert.equal(s.equipments_to_fix, 0);
    assert.equal(s.equipments_published, 1);
  });

  it('l’entité principale refusée garde son propre libellé d’entité, sans bloquer la commande', () => {
    const entities = tree579().entities;
    const primary = entities[0];
    assert.equal(M.isReadyDiagnostic(primary.decision), false);
    assert.match(M.buildPublishCellLabel(primary.decision), /^Ne sera pas publié — état sans ordre On\/Off/);
    // …mais ne se reporte pas sur la commande ni sur la synthèse (déjà vérifié ci-dessus).
    assert.equal(M.isReadyDiagnostic(entities[1].decision), true);
  });
});

describe('21.1 / AC12 — pas de régression de la surface', () => {
  it('équipement à une seule entité refusée : la commande reste bloquante', () => {
    const t = {
      jeedom_eq_id: 901, mapped: true, equipment_decision: REFUSED_PRIMARY,
      commands: [{ jeedom_cmd_id: 9101, cmd_name: 'Etat', covered: true, diagnostic: REFUSED_PRIMARY }],
    };
    const s = M.summarizePublication(t);
    assert.equal(s.ready_count, 0);
    assert.equal(s.blocking_count, 1);
    assert.match(M.buildPublishCellLabel(REFUSED_PRIMARY), /^Ne sera pas publié — /);
    assert.match(M.buildPublicationSummaryLabel(s), /^Ne sera pas publié dans Home Assistant : 1 commande\(s\) bloquante\(s\)\./);
  });

  it('commande non couverte, exclue, désactivée, forcée : comptées comme avant', () => {
    const t = {
      jeedom_eq_id: 1, mapped: true, equipment_decision: null,
      commands: [UNCOVERED, EXCLUDED, DISABLED, FORCED].map((d, i) => ({ jeedom_cmd_id: 10 + i, cmd_name: 'C', diagnostic: d })),
    };
    const s = M.summarizePublication(t);
    assert.equal(s.uncovered_count, 1);
    assert.equal(s.excluded_count, 1);
    assert.equal(s.disabled_count, 1);
    assert.equal(s.ready_count, 1);
    assert.equal(s.blocking_count, 0);
    assert.equal(M.buildPublishCellLabel(FORCED), 'Sera publié : switch');
  });
});

describe('21.1 / AC11 — libellé honnête de la cause « état sans ordre On/Off »', () => {
  it('dit état seul / rien à piloter, propose binary_sensor puis « Forcer », sans invitation aux types génériques', () => {
    const label = M.buildPublishCellLabel(REFUSED_PRIMARY);
    assert.match(label, /^Ne sera pas publié — état sans ordre On\/Off/);
    assert.match(label, /rien à piloter/);
    assert.match(label, /binary_sensor/);
    assert.match(label, /Forcer/);
    assert.doesNotMatch(label, /précisez/);
  });

  it('les autres causes d’ambiguïté gardent leur libellé (F10 reste au backlog)', () => {
    const ambiguous = view('switch', 'ambiguous_skipped', false, false);
    assert.match(M.buildPublishCellLabel(ambiguous), /précisez les types génériques dans Jeedom/);
  });
});
