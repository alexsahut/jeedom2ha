// ARTEFACT — Story 25.7 (D2, AC5, Q5, Q6) : ventilation des exclus d'une pièce (par plugin, pièce, individuelle, autre), repère
// « N exclus » de la carte, ligne « Exclus : » du détail de pièce, mention sur la ligne d'arbre. Invariant : somme de la
// ventilation ≤ effectif « exclu » ; aucune requête. Vrai code sur faux DOM ; plugins fictifs (CC-48).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const O = require('../../desktop/js/jeedom2ha_overview.js');
const { startBig, openCard, phpAvailable } = require('./helpers/workview_harness');
const { plain } = require('./helpers/page_b_harness');

const maybe = phpAvailable ? it : it.skip;
const NAMES = { plugin_alpha: 'Alpha', plugin_beta: 'Beta' };

function diag(reason) {
  return { confidence: null, ha_entity_type: null, publication_reason: reason, reason_code: null, should_publish: false,
    projection_validity: { is_valid: false, missing_capabilities: [], missing_fields: [], reason_code: reason } };
}
function excluded(id, reason) {
  return { jeedom_eq_id: id, commands: [{ jeedom_cmd_id: id * 10, covered: false, diagnostic: diag(reason), published_in_ha: false }], entities: [],
    equipment_decision: diag(reason), sync_status: { published_in_ha: false, synced_should_publish: false, current_should_publish: false } };
}

describe('25.7 / D2 — M.exclusionBreakdown et son texte', () => {
  const items = [
    { cause: { kind: 'plugin', code: 'excluded_plugin' }, eq_type: 'plugin_alpha' },
    { cause: { kind: 'plugin', code: 'excluded_plugin' }, eq_type: 'plugin_alpha' },
    { cause: { kind: 'plugin', code: 'excluded_plugin' }, eq_type: 'plugin_beta' },
    { cause: { kind: 'piece', code: 'excluded_object' }, eq_type: 'plugin_alpha' },
    { cause: { kind: 'individuelle', code: 'excluded_eqlogic' }, eq_type: 'plugin_alpha' },
    { cause: null, eq_type: 'plugin_alpha' },
  ];

  it('décompte par genre et, pour le plugin, par plugin ; l\'écart est « autre »', () => {
    const b = M.exclusionBreakdown(items);
    assert.equal(b.excluded, 6);
    assert.deepEqual(b.plugin, [{ eq_type: 'plugin_alpha', count: 2 }, { eq_type: 'plugin_beta', count: 1 }]);
    assert.equal(b.piece, 1);
    assert.equal(b.individuelle, 1);
    assert.equal(b.autre, 1);
  });

  it('texte : plugin(s), pièce, individuelle, autre ; zéros omis ; pluriels accordés', () => {
    const b = M.exclusionBreakdown(items);
    assert.equal(plain(M.exclusionBreakdownText(b, NAMES)), '2 par le plugin Alpha, 1 par le plugin Beta, 1 par la pièce, 1 individuelle, 1 autre');
    const only = M.exclusionBreakdown([{ cause: { kind: 'individuelle', code: 'excluded_eqlogic' }, eq_type: 'a' }, { cause: { kind: 'individuelle', code: 'excluded_eqlogic' }, eq_type: 'a' }]);
    assert.equal(plain(M.exclusionBreakdownText(only, NAMES)), '2 individuelles');
    assert.equal(M.exclusionBreakdownText(M.exclusionBreakdown([]), NAMES), '');
  });

  it('plugin sans nom ni identifiant : « par son plugin » ; identifiant sans nom : l\'identifiant', () => {
    const b = M.exclusionBreakdown([{ cause: { kind: 'plugin', code: 'excluded_plugin' }, eq_type: '' }, { cause: { kind: 'plugin', code: 'excluded_plugin' }, eq_type: 'plugin_gone' }]);
    assert.equal(plain(M.exclusionBreakdownText(b, NAMES)), '1 par son plugin, 1 par le plugin plugin_gone');
  });
});

describe('25.7 / AC5 — computeOverview porte la cause et la ventilation sans second calcul', () => {
  it('chaque ligne exclue porte sa cause ; la ventilation de la pièce somme au plus à l\'effectif « exclu »', () => {
    const rooms = [{ object_id: 2, object_name: 'P', equipments: [
      { eq_id: 1, eq_name: 'a', enabled: true, eq_type: 'plugin_alpha' }, { eq_id: 2, eq_name: 'b', enabled: true, eq_type: 'plugin_beta' },
      { eq_id: 3, eq_name: 'c', enabled: true, eq_type: 'plugin_alpha' }, { eq_id: 4, eq_name: 'd', enabled: false, eq_type: 'plugin_alpha' },
    ] }];
    const states = { 1: excluded(1, 'excluded_plugin'), 2: excluded(2, 'excluded_object'), 3: excluded(3, 'publication_excluded_eqlogic'), 4: excluded(4, 'excluded_plugin') };
    const overview = O.computeOverview(rooms, states);
    const room = overview.rooms[0];
    assert.deepEqual(room.equipments.map((row) => row.state), ['excluded', 'excluded', 'excluded', 'disabled']);
    assert.deepEqual(room.equipments.map((row) => row.cause && row.cause.kind), ['plugin', 'piece', 'individuelle', null], 'le désactivé n\'a aucune cause');
    assert.equal(room.exclusion.excluded, room.summary.by_state.excluded);
    assert.equal(room.exclusion.excluded, 3);
    assert.deepEqual(room.exclusion.plugin, [{ eq_type: 'plugin_alpha', count: 1 }]);
  });
});

describe('25.7 / AC5 — invariant de la ventilation sur 20 scènes seedées', () => {
  maybe('somme de la ventilation ≤ effectif « exclu » ; repère de carte = KPI ; aucune requête', () => {
    let withExclusion = 0;
    for (let seed = 1; seed <= 20; seed += 1) {
      const ui = startBig({ rooms: 4, equipments: 40, seed, unread: seed % 3, unassigned: seed % 2 });
      const before = ui.calls.length;
      const overview = ui.page.snapshot().view.overview;
      overview.rooms.forEach((room) => {
        const b = room.exclusion;
        const sum = b.plugin.reduce((n, p) => n + p.count, 0) + b.piece + b.individuelle;
        assert.ok(sum <= room.summary.by_state.excluded, `seed ${seed} pièce ${room.object_id}`);
        assert.equal(sum + b.autre, room.summary.by_state.excluded, 'la somme avec « autre » égale l\'effectif exclu');
        const card = ui.$(`#j2ha_roomCards .j2ha-room-card[data-object_id="${room.object_id}"] .j2ha-mark-excluded`);
        assert.equal(card.length, room.summary.by_state.excluded > 0 ? 1 : 0, `repère de carte ${seed}/${room.object_id}`);
        if (card.length) {
          withExclusion += 1;
          assert.equal(Number(plain(card.text()).trim().split(' ')[0]), room.summary.by_state.excluded);
        }
      });
      assert.equal(ui.calls.length, before, 'aucune requête');
    }
    assert.ok(withExclusion > 0, 'des cartes avec exclusions ont été contrôlées');
  });
});

describe('25.7 / AC3, AC5 — rendu : carte, ligne d\'arbre, détail de pièce', () => {
  maybe('carte : repère « N exclus » après les repères existants, infobulle et nom accessible = ventilation ; ratio inchangé', () => {
    const ui = startBig({ rooms: 3, equipments: 45, seed: 9 });
    const overview = ui.page.snapshot().view.overview;
    const room = overview.rooms.find((r) => r.summary.by_state.excluded > 0);
    assert.ok(room, 'une pièce avec des exclus');
    const sel = `#j2ha_roomCards .j2ha-room-card[data-object_id="${room.object_id}"]`;
    const mark = ui.$(`${sel} .j2ha-mark-excluded`);
    assert.match(plain(mark.text()).trim(), /^\d+ exclus?$/);
    const breakdown = plain(M.exclusionBreakdownText(room.exclusion, {}));
    assert.equal(plain(mark.attr('title')), 'Exclus : ' + breakdown);
    assert.equal(plain(mark.attr('aria-label')), plain(mark.attr('title')));
    const marks = ui.$(`${sel} .j2ha-room-marks .j2ha-mark`).list.map((n) => [...n.classes].join(' '));
    assert.match(marks[marks.length - 1], /j2ha-mark-excluded/, 'dernier repère : l\'ordre des repères existants est conservé');
    assert.equal(plain(ui.$(`${sel} .j2ha-room-ratio`).text()).trim().split(' ')[0], String(room.counts.published));
    assert.match(plain(ui.$(sel).attr('aria-label')), /exclus?/, 'le nom accessible de la carte mentionne les exclus');
  });

  maybe('ligne d\'arbre : mention grise après le nom pour un exclu avec cause ; rien pour les autres états ni pour un désactivé', () => {
    const ui = startBig({ rooms: 3, equipments: 45, seed: 9 });
    const overview = ui.page.snapshot().view.overview;
    ui.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="other"]');
    const rows = overview.rooms.flatMap((r) => r.equipments);
    const withCause = rows.filter((row) => row.cause);
    assert.ok(withCause.length > 0, 'des exclus avec cause');
    for (const row of rows) {
      const node = ui.$(`.j2ha-wv-eq[data-eq-id="${row.eq_id}"]`);
      if (!node.length) continue;
      const mention = node.find('.j2ha-wv-cause');
      if (row.cause) {
        assert.equal(mention.length, 1, 'eq ' + row.eq_id);
        assert.match(plain(mention.text()).trim(), /^(par le plugin .+|par son plugin|par la pièce|individuelle)$/);
      } else {
        assert.equal(mention.length, 0, `eq ${row.eq_id} (${row.state})`);
      }
    }
  });

  maybe('détail de pièce : « Exclus : » + ventilation sous les KPI ; absent sans exclu', () => {
    const ui = startBig({ rooms: 3, equipments: 45, seed: 9 });
    const overview = ui.page.snapshot().view.overview;
    const withExclusion = overview.rooms.find((r) => r.summary.by_state.excluded > 0);
    const without = overview.rooms.find((r) => r.summary.by_state.excluded === 0);
    openCard(ui, withExclusion.object_id);
    const line = ui.$('.j2ha-wv-exclusion');
    assert.equal(line.length, 1);
    assert.match(plain(line.text()).trim(), /^Exclus : /);
    assert.equal(plain(line.text()).trim(), 'Exclus : ' + plain(M.exclusionBreakdownText(withExclusion.exclusion, {})));
    if (without) {
      ui.click('.j2ha-wv-back');
      openCard(ui, without.object_id);
      assert.equal(ui.$('.j2ha-wv-exclusion').length, 0);
    }
  });
});
