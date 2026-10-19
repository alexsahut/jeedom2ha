// ARTEFACT — Story 25.4 (AC4, AC11, AC12, AC13, AC14) : l'arbre pièces → équipements (ordre, repères, états, rendu
// différé), la recherche (noms seulement, accents, texte jamais interprété), les filtres partagés avec la page B,
// la source de vérité unique de l'état et l'invariant « somme des KPI = repères des cartes ». Vrai code sur faux DOM ;
// données fictives, scènes générées avec un générateur seedé (CC-48).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const O = require('../../desktop/js/jeedom2ha_overview.js');
const W = require('../../desktop/js/jeedom2ha_workview.js');
const { startWorkview, startBig, openCard, phpAvailable } = require('./helpers/workview_harness');
const { makeScene } = require('./helpers/big_scene');

const maybe = phpAvailable ? it : it.skip;
const plain = (text) => String(text).replace(/\{\{|\}\}/g, '');

function search(ui, text) {
  const input = ui.$('.j2ha-wv-search').list[0];
  input.props.value = text;
  input.handlers.input.call(input, { target: input });
  ui.advance(400);
}

const roomIds = (ui) => ui.$('.j2ha-wv-room').list.map((el) => Number(el.attrs['data-object_id']));
const eqRows = (ui) => ui.$('.j2ha-wv-eq').list;

describe('25.4 / AC11 — l’arbre reprend l’ordre, les sous-titres de groupe et les repères de la page B', () => {
  maybe('pièces dans l’ordre de la grille, sous-titres de groupe, « Sans pièce » présente, une seule pièce dépliée', () => {
    const ui = startWorkview();
    openCard(ui, 4);
    const grid = ui.$('#j2ha_roomCards .j2ha-room-card').list.map((el) => Number(el.attrs['data-object_id']));
    assert.deepEqual(roomIds(ui), grid);
    assert.ok(roomIds(ui).includes(0), 'Sans pièce');
    const titlesInGrid = ui.$('#j2ha_roomCards .j2ha-room-group-title').list.map((el) => ui.$(el).text());
    const titlesInTree = ui.$('.j2ha-wv-group-title').list.map((el) => ui.$(el).text());
    assert.deepEqual(titlesInTree, titlesInGrid);
    assert.equal(ui.$('.j2ha-wv-room[aria-expanded="true"]').length, 1);
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="4"]').attr('aria-expanded'), 'true');
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="4"]').attr('aria-selected'), 'true');
  });

  maybe('rendu différé : les lignes d’une pièce repliée ne sont pas dans le DOM ; elles apparaissent au dépliage', () => {
    const ui = startBig({ rooms: 4, equipments: 44, seed: 9 });
    openCard(ui, 10);
    const rendered = ui.$('.j2ha-wv-eq').length;
    const dom10 = ui.$('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq').length;
    assert.equal(rendered, dom10, 'seules les lignes de la pièce sélectionnée existent');
    ui.click('.j2ha-wv-room[data-object_id="12"] .j2ha-wv-toggle');
    assert.ok(ui.$('.j2ha-wv-room[data-object_id="12"] .j2ha-wv-eq').length > 0);
    ui.click('.j2ha-wv-room[data-object_id="12"] .j2ha-wv-toggle');
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="12"] .j2ha-wv-eq').length, 0);
  });

  maybe('chaque pièce : « n / t », repères « N bloqués » et « N à appliquer » seulement s’ils sont non nuls, comme sur la carte', () => {
    const ui = startWorkview();
    openCard(ui, 4);
    for (const room of ui.page.snapshot().view.overview.rooms) {
      const item = ui.$(`.j2ha-wv-room[data-object_id="${room.object_id}"]`);
      const card = ui.$(`#j2ha_roomCards .j2ha-room-card[data-object_id="${room.object_id}"]`);
      const ratio = plain(item.find('.j2ha-wv-ratio').first().text());
      assert.equal(ratio, plain(card.find('.j2ha-room-ratio').text()).replace(/ publiés?$/, ''), 'ratio ' + room.object_id);
      const treeMarks = item.find('.j2ha-wv-room-marks .j2ha-mark').list.map((el) => plain(ui.$(el).text()));
      const cardMarks = card.find('.j2ha-room-marks .j2ha-mark').list.map((el) => plain(ui.$(el).text())).filter((t) => !/non lu/.test(t));
      assert.deepEqual(treeMarks, cardMarks, 'repères ' + room.object_id);
      if (room.counts.blocked === 0) assert.ok(!treeMarks.some((t) => /bloqué/.test(t)));
    }
  });

  maybe('lignes d’équipement : état avant le nom (mot + icône), désactivé atténué, non lu sans état, mention « N bloquées »', () => {
    const ui = startBig({ rooms: 3, equipments: 40, seed: 21, unread: 3 });
    openCard(ui, 10);
    for (const id of [11, 12]) ui.click('.j2ha-wv-room[data-object_id="' + id + '"] .j2ha-wv-toggle');
    const rows = eqRows(ui);
    assert.ok(rows.length >= 40);
    const view = ui.page.snapshot().view.overview;
    for (const el of rows) {
      const eqId = Number(el.attrs['data-eq-id']);
      const model = view.rooms.flatMap((r) => r.equipments).find((r) => r.eq_id === eqId);
      const node = ui.$(el);
      const children = node.find('.j2ha-wv-row').children().list;
      const word = node.find('.j2ha-wv-state').first();
      assert.ok(children.length > 0);
      if (model.state) {
        assert.equal(plain(word.text()).trim(), M.EQUIPMENT_STATE_LABELS[model.state], 'mot d’état ' + eqId);
        assert.ok(word.find('.j2ha-state-word').hasClass('j2ha-state-' + model.state));
        if (model.blocked_mention > 0) assert.match(plain(node.find('.j2ha-mark-blocked').text()), /^\d+ bloquées?$/);
      } else {
        assert.equal(word.find('.j2ha-state-word').length, 0, 'non lu : sans état');
        assert.match(plain(node.find('.j2ha-wv-unread').text()), /non lu/);
      }
    }
    const disabled = ui.$('.j2ha-wv-eq-disabled');
    assert.ok(disabled.length > 0, 'au moins un équipement désactivé dans la scène');
    assert.match(plain(disabled.first().text()), /\(désactivé dans Jeedom\)/);
  });
});

describe('25.4 / AC12 — recherche', () => {
  maybe('sans casse ni accents, noms de pièce et d’équipement seulement ; pièce dont le nom correspond = tous ses équipements', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 5, longNames: true });
    openCard(ui, 10);
    search(ui, 'PIECE FICTIVE NUMERO 1');
    assert.deepEqual(roomIds(ui), [11], 'une seule pièce, sa recherche ne porte pas sur les autres');
    const all = ui.page.snapshot().view.overview.rooms.find((r) => r.object_id === 11).equipments.length;
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="11"] .j2ha-wv-eq').length, all, 'tous les équipements de la pièce');
    search(ui, 'équipement 1001 ');
    assert.ok(ui.$('.j2ha-wv-eq[data-eq-id="1001"]').length === 1);
    assert.ok(roomIds(ui).length >= 1);
    search(ui, 'zzz absent');
    assert.equal(roomIds(ui).length, 0);
    assert.equal(ui.text('.j2ha-wv-search-status'), 'Aucun résultat');
    assert.equal(ui.$('.j2ha-wv-search-status').attr('role'), 'status');
  });

  maybe('aucune requête réseau ; vider le champ restaure dépliages et sélection', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 5 });
    openCard(ui, 11);
    ui.click('.j2ha-wv-room[data-object_id="12"] .j2ha-wv-toggle');
    const before = ui.calls.length;
    search(ui, 'eq 10');
    search(ui, '');
    assert.equal(ui.calls.length, before, 'aucune requête');
    assert.equal(ui.$('.j2ha-wv-room[aria-expanded="true"]').length, 2);
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="11"]').attr('aria-selected'), 'true');
  });

  maybe('le texte saisi n’est ni du HTML ni une expression régulière ; la sélection en cours n’est pas perdue', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 5 });
    openCard(ui, 10);
    for (const hostile of ['<img src=x onerror=alert(1)>', '(.*', '[a-', '\\', '.*', '"><script>x</script>']) {
      assert.doesNotThrow(() => search(ui, hostile), hostile);
      assert.equal(ui.$('.j2ha-wv-tree img, .j2ha-wv-tree script').length, 0);
      assert.equal(roomIds(ui).length, 0, 'aucun nom ne correspond : ' + hostile);
      assert.match(ui.text('.j2ha-wv-detail'), /./, 'le détail de la pièce reste affiché');
      assert.equal(ui.$('.j2ha-wv-title').length > 0, true);
    }
  });

  it('foldText : insensible à la casse et aux accents, texte littéral', () => {
    assert.equal(W.foldText('Éclairage SALLE à Manger'), 'eclairage salle a manger');
    assert.equal(W.foldText('(.*'), '(.*');
  });
});

describe('25.4 / AC13 — filtres d’état partagés avec la page B', () => {
  maybe('mêmes puces, mêmes libellés et effectifs que la page B ; une puce à zéro est désactivée', () => {
    const ui = startBig({ rooms: 3, equipments: 40, seed: 17, unread: 2 });
    openCard(ui, 10);
    const b = ui.$('#j2ha_houseChips .j2ha-chip-filter').list.map((el) => [el.attrs['data-filter'], plain(ui.$(el).text()), !!el.props.disabled]);
    const c = ui.$('.j2ha-wv-chips .j2ha-chip-filter').list.map((el) => [el.attrs['data-filter'], plain(ui.$(el).text()), !!el.props.disabled]);
    assert.deepEqual(c, b);
    assert.ok(c.some((entry) => entry[0] === 'unread'), 'non lus > 0');
  });

  maybe('le filtre de B est l’état initial de C ; un changement dans C est visible au retour en B ; une seule vérité', () => {
    const ui = startBig({ rooms: 3, equipments: 40, seed: 17 });
    ui.page.setFilter('blocked');
    openCard(ui, 10);
    assert.equal(ui.$('.j2ha-wv-chips .j2ha-chip-filter[data-filter="blocked"]').attr('aria-pressed'), 'true');
    ui.click('.j2ha-wv-chips .j2ha-chip-filter[data-filter="to_apply"]');
    assert.equal(ui.page.filter(), 'to_apply');
    ui.click('.j2ha-wv-back');
    assert.equal(ui.$('#j2ha_houseChips .j2ha-chip-filter[data-filter="to_apply"]').attr('aria-pressed'), 'true');
    assert.equal(ui.visible('#j2ha_filterPanel'), true);
  });

  maybe('le nombre de lignes de l’arbre pour un filtre égale l’effectif de la puce ; ET logique avec la recherche ; aucune requête', () => {
    const ui = startBig({ rooms: 4, equipments: 60, seed: 23, unread: 3 });
    openCard(ui, 10);
    const before = ui.calls.length;
    for (const chip of ui.$('.j2ha-wv-chips .j2ha-chip-filter').list) {
      if (chip.props.disabled) continue;
      const key = chip.attrs['data-filter'];
      const announced = Number(plain(ui.$(chip).text()).replace(/[^0-9].*$/, ''));
      ui.click(`.j2ha-wv-chips .j2ha-chip-filter[data-filter="${key}"]`);
      assert.equal(eqRows(ui).length, announced, 'filtre ' + key);
      ui.click(`.j2ha-wv-chips .j2ha-chip-filter[data-filter="${key}"]`);
    }
    ui.click('.j2ha-wv-chips .j2ha-chip-filter[data-filter="published"]');
    const published = eqRows(ui).length;
    search(ui, 'eq 1');
    assert.ok(eqRows(ui).length <= published);
    assert.equal(ui.calls.length, before, 'aucune requête (filtres et recherche)');
  });

  maybe('un équipement sélectionné qui sort du filtre reste affiché dans le détail', () => {
    const ui = startBig({ rooms: 3, equipments: 40, seed: 17 });
    openCard(ui, 10);
    const first = Number(ui.$('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.selectEquipment(first);
    const state = ui.page.snapshot().view.overview.rooms.flatMap((r) => r.equipments).find((r) => r.eq_id === first).group;
    const other = ['published', 'blocked', 'to_apply', 'other'].find((k) => k !== state && !ui.$(`.j2ha-wv-chips .j2ha-chip-filter[data-filter="${k}"]`).list[0].props.disabled);
    ui.click(`.j2ha-wv-chips .j2ha-chip-filter[data-filter="${other}"]`);
    assert.equal(ui.$(`.j2ha-eq-panel[data-eq-id="${first}"]`).length, 1);
  });
});

describe('25.4 / AC4, AC14 — source de vérité unique et invariants', () => {
  it('l’état de chaque équipement est resolveEquipmentState(entrée, enabled) ; « Désactivé » prime sur « Exclu » (enabled ∈ {true,false})', () => {
    const { FIXTURE } = require('./helpers/page_b_harness');
    const exclu = FIXTURE['110'].aggregated;
    for (const enabled of [true, false]) {
      const rooms = [{ object_id: 7, object_name: 'Zone', equipments: [{ eq_id: 110, eq_name: 'Eq', enabled }] }];
      const overview = O.computeOverview(rooms, { 110: exclu });
      const expected = M.resolveEquipmentState(exclu, enabled).state;
      assert.equal(overview.rooms[0].equipments[0].state, expected);
      assert.equal(expected, enabled ? 'excluded' : 'disabled');
    }
  });

  it('aucun module de la vue ne duplique la partition des causes ni ne recalcule un état', () => {
    const fs = require('node:fs');
    const path = require('node:path');
    const dir = path.join(__dirname, '..', '..', 'desktop', 'js');
    for (const file of fs.readdirSync(dir).filter((f) => f.endsWith('.js') && f !== 'jeedom2ha_mapping_override.js')) {
      assert.doesNotMatch(fs.readFileSync(path.join(dir, file), 'utf8'), /COMMAND_CAUSE_CATEGORIES|categoryOfCause/, file);
    }
  });

  maybe('20 scènes seedées : somme des KPI d’une pièce = repères de la carte, état par état ; somme des pièces = bloc maison', () => {
    for (let seed = 1; seed <= 20; seed += 1) {
      const ui = startBig({ rooms: 3 + (seed % 3), equipments: 25 + seed, seed, unread: seed % 4 });
      const overview = ui.page.snapshot().view.overview;
      const houseByState = {};
      for (const room of overview.rooms) {
        openCard(ui, room.object_id);
        const kpis = ui.$('.j2ha-wv-kpis .j2ha-room-counter').list.map((el) => [el.attrs['data-state'], Number(plain(ui.$(el).text()).trim().split(' ')[0])]);
        const byState = {};
        kpis.forEach(([state, n]) => { byState[state] = n; houseByState[state] = (houseByState[state] || 0) + n; });
        M.EQUIPMENT_STATES.forEach((state) => {
          assert.equal(byState[state] || 0, room.summary.by_state[state], `seed ${seed} pièce ${room.object_id} ${state}`);
        });
        // Les repères de la carte (page B) sont les mêmes que ceux de l'arbre de la vue.
        const card = ui.$(`#j2ha_roomCards .j2ha-room-card[data-object_id="${room.object_id}"]`);
        const blocked = Number((plain(card.find('.j2ha-mark-blocked').text()).match(/^\d+/) || ['0'])[0]);
        const toApply = Number((plain(card.find('.j2ha-mark-to_apply').text()).match(/^\d+/) || ['0'])[0]);
        assert.equal(byState.blocked || 0, blocked, `seed ${seed} bloqués`);
        assert.equal(byState.to_apply || 0, toApply, `seed ${seed} à appliquer`);
        ui.click('.j2ha-wv-back');
      }
      M.EQUIPMENT_STATES.forEach((state) => {
        assert.equal(houseByState[state] || 0, overview.house.by_state[state], `seed ${seed} maison ${state}`);
      });
    }
  });

  maybe('« À traiter dans cette pièce » : bloqués et à appliquer seulement, cause dite une fois, sans lire d’arbre (Q8)', () => {
    const big = makeScene({ rooms: 3, equipments: 30, seed: 8 });
    const ui = startWorkview({ scene: big.scene, equipments: big.equipments });
    const overview = ui.page.snapshot().view.overview;
    for (const room of overview.rooms) {
      openCard(ui, room.object_id);
      const expected = room.equipments.filter((r) => r.state === 'blocked' || r.state === 'to_apply').map((r) => r.eq_id);
      const listed = ui.$('.j2ha-wv-todo-row').list.map((el) => Number(el.attrs['data-eq-id']));
      assert.deepEqual(listed, expected, 'pièce ' + room.object_id);
      if (expected.length === 0) {
        assert.match(plain(ui.text('.j2ha-wv-todo-empty')), /Rien à traiter dans cette pièce/);
        assert.match(plain(ui.text('.j2ha-wv-todo-empty')), /n'appelle(nt)? aucune action/);
      }
      for (const row of ui.$('.j2ha-wv-todo-row').list) {
        const id = Number(row.attrs['data-eq-id']);
        const entry = ui.equipments[String(id)];
        if (room.equipments.find((r) => r.eq_id === id).state === 'blocked') {
          const groups = M.groupBlockedCauses(entry);
          assert.equal(ui.$(row).find('.j2ha-wv-todo-cause').length, groups.length, 'une mention par cause distincte');
          assert.match(plain(ui.$(row).text()), new RegExp(M.buildCauseNoticeText(groups[0]).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
        } else {
          assert.equal(ui.$(row).find('.j2ha-wv-todo-apply').length, 1, '« Appliquer » seulement sur « À appliquer »');
        }
      }
    }
    assert.equal(ui.count('getMappingOverrides'), 0, 'aucune lecture d’arbre pour produire la liste');
  });

  maybe('« Appliquer » d’une ligne : même écriture directe (publier / équipement) sans lire d’arbre, bouton réservé', () => {
    const big = makeScene({ rooms: 3, equipments: 30, seed: 8 });
    const ui = startWorkview({ scene: big.scene, equipments: big.equipments });
    const overview = ui.page.snapshot().view.overview;
    const room = overview.rooms.find((r) => r.equipments.some((e) => e.state === 'to_apply'));
    openCard(ui, room.object_id);
    const target = room.equipments.find((e) => e.state === 'to_apply').eq_id;
    ui.click(`.j2ha-wv-todo-row[data-eq-id="${target}"] .j2ha-wv-todo-apply`);
    const call = ui.pending('executeHaAction')[0];
    assert.deepEqual([call.data.intention, call.data.portee, call.data.selection], ['publier', 'equipement', `[${target}]`]);
    assert.equal(ui.$(`.j2ha-wv-todo-row[data-eq-id="${target}"] .j2ha-wv-todo-apply`).prop('disabled'), true);
    assert.equal(ui.count('getMappingOverrides'), 0);
  });
});
