// ARTEFACT — Story 25.7 (D1, AC1, AC2, AC7) : la cause d'exclusion d'un équipement. Table de vérité de D1, parité entre
// l'entrée agrégée et l'arbre unitaire (fixtures de 25.2 complétées de cas d'exclusion fictifs), libellés. La fonction est
// PURE et AJOUTÉE à jeedom2ha_mapping_override.js : aucune règle d'état n'est réécrite. Plugins fictifs (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

const FIXTURE = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'fixtures', 'story_25_2_parite_etat.json'), 'utf8'));
const plain = (text) => String(text).replace(/\{\{|\}\}/g, '');

function diag(reason) {
  return {
    confidence: null, ha_entity_type: null, publication_reason: reason, reason_code: null, should_publish: false,
    projection_validity: { is_valid: false, missing_capabilities: [], missing_fields: [], reason_code: reason },
  };
}
/** Entrée fictive : décision d'équipement (ou null) et raisons des commandes ; jamais publiée dans HA. */
function entry(decisionReason, commandReasons, extra) {
  return Object.assign({
    jeedom_eq_id: 7,
    commands: (commandReasons || []).map((reason, i) => ({ jeedom_cmd_id: 70 + i, covered: false, diagnostic: diag(reason), published_in_ha: false })),
    entities: [],
    equipment_decision: decisionReason ? diag(decisionReason) : null,
    sync_status: { published_in_ha: false, synced_should_publish: false, current_should_publish: false },
  }, extra || {});
}

describe('25.7 / AC1 — exclusionCauseOf : table de vérité de D1', () => {
  const rows = [
    ['excluded_plugin', entry('excluded_plugin', ['excluded_plugin']), true, { kind: 'plugin', code: 'excluded_plugin' }],
    ['excluded_object', entry('excluded_object', ['excluded_object']), true, { kind: 'piece', code: 'excluded_object' }],
    ['publication_excluded_eqlogic', entry('publication_excluded_eqlogic', ['publication_excluded_eqlogic']), true, { kind: 'individuelle', code: 'publication_excluded_eqlogic' }],
    ['excluded_eqlogic', entry('excluded_eqlogic', ['excluded_eqlogic']), true, { kind: 'individuelle', code: 'excluded_eqlogic' }],
    ['décision seule, sans commande', entry('excluded_object', []), true, { kind: 'piece', code: 'excluded_object' }],
    ['décision = raison de commande d\'exclusion', entry('publication_excluded_command', ['publication_excluded_command']), true, { kind: 'individuelle', code: 'publication_excluded_command' }],
    ['toutes les commandes « Jamais », pas de décision d\'exclusion', entry(null, ['publication_excluded_command', 'publication_excluded_command']), true, { kind: 'individuelle', code: 'publication_excluded_command' }],
    ['même raison de plugin sur toutes les commandes', entry(null, ['excluded_plugin', 'excluded_plugin']), true, { kind: 'plugin', code: 'excluded_plugin' }],
    ['commandes exclues pour des raisons différentes → aucune cause inventée', entry(null, ['excluded_plugin', 'publication_excluded_command']), true, null],
    ['désactivé dans Jeedom + exclu par la pièce → aucune cause (R3 avant R4)', entry('excluded_object', ['excluded_object']), false, null],
    ['désactivé (diagnostic) → aucune cause', entry('disabled_eqlogic', ['disabled_eqlogic']), true, null],
    ['raison inconnue → aucune cause', entry('zzz_inconnue', ['zzz_inconnue']), true, null],
    ['exclu pour une raison valide mais état non exclu (commande bloquée)', entry(null, ['excluded_plugin', 'ambiguous_skipped']), true, null],
    ['enabled inconnu (undefined) : l\'état ne dépend que de l\'arbre', entry('excluded_object', ['excluded_object']), undefined, { kind: 'piece', code: 'excluded_object' }],
    ['enabled inconnu (null)', entry('excluded_plugin', ['excluded_plugin']), null, { kind: 'plugin', code: 'excluded_plugin' }],
  ];
  for (const [name, input, enabled, expected] of rows) {
    it(name, () => {
      const cause = M.exclusionCauseOf(input, enabled);
      assert.deepEqual(cause, expected);
      if (cause) assert.equal(M.resolveEquipmentState(input, enabled).state, 'excluded', 'une cause n\'existe que pour l\'état Exclu');
    });
  }

  it('équipement publié, à appliquer, bloqué, rien à publier, non lu : aucune cause', () => {
    for (const id of Object.keys(FIXTURE)) {
      const fixture = FIXTURE[id];
      const state = M.resolveEquipmentState(fixture.aggregated, fixture.enabled).state;
      const cause = M.exclusionCauseOf(fixture.aggregated, fixture.enabled);
      if (state !== 'excluded') assert.equal(cause, null, `${id} (${state})`);
    }
    assert.equal(M.exclusionCauseOf(null, true), null, 'non lu (aucune entrée)');
    assert.equal(M.exclusionCauseOf(undefined, true), null);
    assert.equal(M.exclusionCauseOf({}, true), null);
  });

  it('pure : ne mute pas son argument', () => {
    const input = entry('excluded_plugin', ['excluded_plugin']);
    const before = JSON.stringify(input);
    M.exclusionCauseOf(input, true);
    assert.equal(JSON.stringify(input), before);
  });
});

describe('25.7 / AC2 — parité entrée agrégée / arbre unitaire', () => {
  it('fixtures de 25.2 : la cause est deepEqual sur les deux formes', () => {
    let excluded = 0;
    for (const id of Object.keys(FIXTURE)) {
      const { aggregated, tree, enabled } = FIXTURE[id];
      const fromAggregated = M.exclusionCauseOf(aggregated, enabled);
      const fromTree = M.exclusionCauseOf(tree, enabled);
      assert.deepEqual(fromAggregated, fromTree, 'équipement ' + id);
      if (fromAggregated) excluded += 1;
    }
    assert.ok(excluded >= 1, 'les fixtures de 25.2 couvrent des exclusions : ' + excluded);
  });

  it('cas d\'exclusion fictifs complémentaires : mêmes causes, mention courte = phrase au même genre', () => {
    const cases = [
      ['excluded_plugin', ['excluded_plugin']], ['excluded_object', ['excluded_object']], ['publication_excluded_eqlogic', ['publication_excluded_eqlogic']],
      ['excluded_eqlogic', ['excluded_eqlogic']], [null, ['publication_excluded_command']],
    ];
    for (const [decision, commands] of cases) {
      const aggregated = entry(decision, commands);
      const unit = Object.assign({}, aggregated, { eq_name: 'Eq', mapped: false, eligible: true });
      const a = M.exclusionCauseOf(aggregated, true);
      assert.deepEqual(a, M.exclusionCauseOf(unit, true));
      assert.ok(a, 'cause attendue');
      assert.ok(M.exclusionCauseText(a, 'Alpha', 'short').length > 0 && M.exclusionCauseText(a, 'Alpha', 'sentence').length > 0);
    }
  });
});

describe('25.7 / AC7, AC6 — libellés (mention courte, phrase du détail)', () => {
  const short = (cause, name) => plain(M.exclusionCauseText(cause, name, 'short'));
  const sentence = (cause, name) => plain(M.exclusionCauseText(cause, name, 'sentence'));

  it('mentions courtes de D1', () => {
    assert.equal(short({ kind: 'plugin', code: 'excluded_plugin' }, 'Alpha'), 'par le plugin Alpha');
    assert.equal(short({ kind: 'piece', code: 'excluded_object' }), 'par la pièce');
    assert.equal(short({ kind: 'individuelle', code: 'publication_excluded_eqlogic' }), 'individuelle');
    assert.equal(short({ kind: 'individuelle', code: 'excluded_eqlogic' }), 'individuelle', 'Q3 : excluded_eqlogic = individuelle');
  });

  it('phrases du détail de D1', () => {
    assert.equal(sentence({ kind: 'plugin', code: 'excluded_plugin' }, 'Alpha'), 'Exclu par le plugin Alpha (configuration du plugin, « Plugins exclus »)');
    assert.equal(sentence({ kind: 'piece', code: 'excluded_object' }), 'Exclu par la pièce : toute la pièce est exclue');
    assert.equal(sentence({ kind: 'individuelle', code: 'publication_excluded_eqlogic' }), 'Exclusion individuelle : réglage « Jamais »');
    assert.equal(sentence({ kind: 'individuelle', code: 'publication_excluded_command' }), 'Exclusion individuelle : « Jamais » sur ses entités');
    assert.equal(sentence({ kind: 'individuelle', code: 'excluded_eqlogic' }), 'Exclusion individuelle : réglage de l\'équipement dans Jeedom');
  });

  it('nom de plugin absent ou vide : « par son plugin », jamais « undefined » ni chaîne vide', () => {
    for (const name of [undefined, null, '', '   ']) {
      assert.equal(short({ kind: 'plugin', code: 'excluded_plugin' }, name), 'par son plugin');
      assert.equal(sentence({ kind: 'plugin', code: 'excluded_plugin' }, name), 'Exclu par son plugin (configuration du plugin, « Plugins exclus »)');
    }
  });

  it('cause nulle ou inconnue : chaîne vide ; libellés via {{…}}, aucun point final, aucun terme interdit', () => {
    assert.equal(M.exclusionCauseText(null, 'Alpha', 'short'), '');
    assert.equal(M.exclusionCauseText({ kind: 'inconnue', code: 'x' }, 'Alpha', 'short'), '');
    const raw = [
      M.exclusionCauseText({ kind: 'plugin', code: 'excluded_plugin' }, 'Alpha', 'short'), M.exclusionCauseText({ kind: 'piece', code: 'excluded_object' }, '', 'short'),
      M.exclusionCauseText({ kind: 'individuelle', code: 'excluded_eqlogic' }, '', 'sentence'),
    ];
    for (const text of raw) {
      assert.match(text, /\{\{/, 'passe par {{…}} : ' + text);
      assert.doesNotMatch(plain(text), /\.$/);
      assert.doesNotMatch(plain(text), /override|bridge|prête|\p{L}\(s\)/iu);
    }
    assert.deepEqual(Object.values(M.EQUIPMENT_STATE_LABELS), ['Publié', 'À appliquer', 'Bloqué', 'Exclu', 'Désactivé', 'Rien à publier'], 'les six libellés d\'état sont inchangés');
  });

  it('le nom du plugin est du texte : aucune interprétation HTML ici (échappé par .text() côté rendu)', () => {
    assert.equal(short({ kind: 'plugin', code: 'excluded_plugin' }, '<b>X</b>'), 'par le plugin <b>X</b>');
  });
});
