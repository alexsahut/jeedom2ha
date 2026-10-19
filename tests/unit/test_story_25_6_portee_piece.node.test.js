// ARTEFACT — Story 25.6 (D1, AC1, AC2, AC4, AC7, AC8, AC9) : la vue C a une PORTÉE. Depuis une carte, l'arbre ne contient
// que la pièce d'entrée (`data-j2ha-scope="piece"`) ; depuis une puce, un segment ou une ligne de liste, toutes les pièces
// (`toutes`) ; le bouton « Toutes les pièces » élargit en gardant la sélection. Vrai code sur faux DOM ; données fictives (CC-48).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const W = require('../../desktop/js/jeedom2ha_workview.js');
const { startBig, openCard, phpAvailable } = require('./helpers/workview_harness');
const { plain } = require('./helpers/page_b_harness');
const { tree, ok, READY } = require('./helpers/ui_harness');

const maybe = phpAvailable ? it : it.skip;
const scope = (ui) => ui.$('#j2ha_workView').attr('data-j2ha-scope');
const roomIds = (ui) => ui.$('.j2ha-wv-tree .j2ha-wv-room').list.map((n) => n.attrs['data-object_id']);

describe('25.6 / AC1 — depuis une carte : cette pièce seule', () => {
  maybe('l’arbre ne contient qu’une ligne de pièce, dépliée et sélectionnée, sans sous-titre de groupe ; repères = carte', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11, grouped: true, unassigned: 3 });
    const card = (id) => plain(ui.$(`#j2ha_roomCards .j2ha-room-card[data-object_id="${id}"] .j2ha-room-ratio`).text()).replace(/ publiés?$/, '').trim();
    const ratio = card(12);
    openCard(ui, 12);
    assert.equal(scope(ui), 'piece');
    assert.deepEqual(roomIds(ui), ['12']);
    const room = ui.$('.j2ha-wv-room[data-object_id="12"]');
    assert.equal(room.attr('aria-expanded'), 'true');
    assert.equal(room.attr('aria-selected'), 'true');
    assert.equal(ui.$('.j2ha-wv-tree .j2ha-wv-group').length, 0, 'aucun sous-titre de groupe');
    assert.equal(plain(ui.$('.j2ha-wv-room[data-object_id="12"] > .j2ha-wv-row .j2ha-wv-ratio').text()).trim(), ratio);
    assert.equal(ui.$('.j2ha-wv-tree [role=treeitem][aria-level="1"]').length, 1, 'un seul treeitem de niveau 1');
  });

  maybe('« Sans pièce » (object_id 0) s’ouvre de la même façon', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11, unassigned: 3 });
    openCard(ui, 0);
    assert.equal(scope(ui), 'piece');
    assert.deepEqual(roomIds(ui), ['0']);
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="0"]').attr('aria-selected'), 'true');
  });
});

describe('25.6 / AC2, Q2 — depuis un filtre ou une ligne de liste : toutes les pièces', () => {
  maybe('puce, segment de la jauge, ligne de la liste filtrée : portée « toutes » et arbre complet', () => {
    const openers = [
      (ui) => ui.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="published"]'),
      (ui) => ui.click('#j2ha_houseGauge .j2ha-seg-published'),
      (ui) => { ui.page.setFilter('published'); ui.click('#j2ha_filterList .j2ha-frow-btn'); },
    ];
    for (const open of openers) {
      const ui = startBig({ rooms: 5, equipments: 40, seed: 4 });
      open(ui);
      assert.equal(ui.isOpen(), true);
      assert.equal(scope(ui), 'toutes');
      assert.equal(ui.$('.j2ha-wv-widen').length, 0);
      assert.ok(roomIds(ui).length > 1, 'plusieurs pièces dans l’arbre filtré');
    }
  });
});

describe('25.6 / AC4 — bouton « Toutes les pièces » (élargir)', () => {
  maybe('présent en portée pièce (avant la recherche), absent en portée toutes ; le retour s’appelle « Page principale »', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    openCard(ui, 11);
    assert.equal(ui.$('.j2ha-wv-widen').length, 1);
    assert.equal(plain(ui.$('.j2ha-wv-widen').text()).trim(), 'Toutes les pièces');
    assert.equal(ui.$('.j2ha-wv-tools .j2ha-wv-widen').length, 1, 'dans la zone d’outils de l’arbre');
    assert.equal(plain(ui.$('.j2ha-wv-back').text()).trim(), 'Page principale');
    ui.click('.j2ha-wv-widen');
    assert.equal(scope(ui), 'toutes');
    assert.equal(ui.$('.j2ha-wv-widen').length, 0, 'absent du DOM en portée toutes');
    const buttons = ui.$('#j2ha_workView button').list.map((n) => plain(ui.$(n).text()).trim());
    assert.equal(buttons.filter((text) => text === 'Toutes les pièces').length, 0, 'plus aucun bouton « Toutes les pièces » une fois élargi');
  });

  maybe('élargir : tout l’arbre, sélection (pièce ou équipement) conservée et dépliée, annonce, focus sur la ligne sélectionnée', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    openCard(ui, 11);
    ui.click('.j2ha-wv-widen');
    assert.equal(roomIds(ui).length, 5);
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="11"]').attr('aria-selected'), 'true');
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="11"]').attr('aria-expanded'), 'true');
    assert.equal(plain(ui.$('.j2ha-wv-live').text()).trim(), 'Toutes les pièces');
    assert.equal(ui.dom.document.activeElement, ui.$('.j2ha-wv-room[data-object_id="11"]').list[0], 'focus sur la ligne sélectionnée');

    const eq = startBig({ rooms: 5, equipments: 40, seed: 11 });
    openCard(eq, 11);
    const id = Number(eq.$('.j2ha-wv-room[data-object_id="11"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    eq.selectEquipment(id, ok(tree(id, [READY])));
    eq.click('.j2ha-wv-widen');
    assert.equal(eq.$(`.j2ha-wv-eq[data-eq-id="${id}"]`).attr('aria-selected'), 'true');
    assert.equal(eq.$('.j2ha-eq-panel').length, 1, 'le détail de l’équipement reste affiché');
    assert.equal(eq.dom.document.activeElement, eq.$(`.j2ha-wv-eq[data-eq-id="${id}"]`).list[0]);
  });

  maybe('activation au clavier : Entrée et Espace sur le bouton passent par le gestionnaire de clic (bouton natif)', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    openCard(ui, 11);
    assert.equal(ui.$('.j2ha-wv-widen').list[0].tag, 'button');
    assert.equal(ui.$('.j2ha-wv-widen').attr('type'), 'button');
    assert.ok(plain(ui.$('.j2ha-wv-widen').text()).trim().length > 0, 'nom accessible');
  });

  maybe('le retour reste « goBack » : il revient à la page principale, quelle que soit la portée', () => {
    for (const widen of [false, true]) {
      const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
      openCard(ui, 11);
      if (widen) ui.click('.j2ha-wv-widen');
      ui.click('.j2ha-wv-back');
      assert.equal(ui.isOpen(), false);
      assert.equal(ui.win.location.hash, '');
    }
  });
});

describe('25.6 / AC7, Q5 — recherche, puces et KPI dans la portée', () => {
  maybe('la recherche ne fait jamais apparaître une autre pièce ; « Aucun résultat » dans la pièce', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    openCard(ui, 11);
    const search = ui.$('.j2ha-wv-search').list[0];
    search.props.value = 'pièce 3';
    search.handlers.input.call(search, { target: search });
    ui.advance(400);
    assert.equal(roomIds(ui).length, 0);
    assert.equal(plain(ui.$('.j2ha-wv-search-status').text()).trim(), 'Aucun résultat');
    search.props.value = 'Eq';
    search.handlers.input.call(search, { target: search });
    ui.advance(400);
    assert.deepEqual(roomIds(ui), ['11']);
  });

  maybe('effectifs des puces : ceux de la pièce en portée pièce, ceux de la maison en portée toutes ; page B inchangée', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    const house = ui.page.snapshot().view.overview;
    const chipText = (selector) => ui.$(selector).list.map((n) => plain(ui.$(n).text()).trim());
    const before = chipText('#j2ha_houseChips .j2ha-chip-filter');
    openCard(ui, 11);
    const ov = house.rooms.find((r) => r.object_id === 11);
    const O = require('../../desktop/js/jeedom2ha_overview.js');
    assert.deepEqual(chipText('.j2ha-wv-chips .j2ha-chip-filter'), O.chipsFor(ov.counts).map((c) => c.label));
    assert.deepEqual(chipText('#j2ha_houseChips .j2ha-chip-filter'), before, 'les puces de la page B gardent les effectifs maison');
    ui.click('.j2ha-wv-widen');
    assert.deepEqual(chipText('.j2ha-wv-chips .j2ha-chip-filter'), O.chipsFor(house.counts).map((c) => c.label));
  });

  maybe('invariant AC13 de 25.4 : lignes de l’arbre pour une puce = effectif de la puce, dans les deux portées (20 scènes seedées)', () => {
    let checked = 0;
    for (let seed = 1; seed <= 20; seed += 1) {
      const ui = startBig({ rooms: 4, equipments: 36, seed, unread: seed % 3, unassigned: seed % 2 });
      const target = [10, 11, 12, 13][seed % 4];
      for (const widen of [false, true]) {
        openCard(ui, target);
        if (widen) ui.click('.j2ha-wv-widen');
        const chips = ui.$('.j2ha-wv-chips .j2ha-chip-filter').list.filter((n) => !n.props.disabled);
        for (const chip of chips) {
          const key = chip.attrs['data-filter'];
          const announced = Number(plain(ui.$(chip).text()).trim().replace(/[^0-9].*$/, ''));
          ui.click(`.j2ha-wv-chips .j2ha-chip-filter[data-filter="${key}"]`);
          assert.equal(ui.$('.j2ha-wv-tree .j2ha-wv-eq').length, announced, `seed ${seed} ${widen ? 'toutes' : 'piece'} ${key}`);
          if (!widen) assert.ok(roomIds(ui).every((id) => id === String(target)), 'jamais une autre pièce');
          ui.click(`.j2ha-wv-chips .j2ha-chip-filter[data-filter="${key}"]`);
          checked += 1;
        }
        ui.click('.j2ha-wv-back');
      }
    }
    assert.ok(checked > 20, 'des puces ont bien été contrôlées : ' + checked);
  });

  maybe('le filtre reste partagé avec la page B : une puce activée en portée pièce est le filtre actif au retour', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    openCard(ui, 11);
    const chip = ui.$('.j2ha-wv-chips .j2ha-chip-filter').list.find((n) => !n.props.disabled);
    ui.click(`.j2ha-wv-chips .j2ha-chip-filter[data-filter="${chip.attrs['data-filter']}"]`);
    assert.equal(ui.page.filter(), chip.attrs['data-filter']);
    ui.click('.j2ha-wv-back');
    assert.equal(ui.page.filter(), chip.attrs['data-filter']);
  });
});

describe('25.6 / AC8 — disposition étroite', () => {
  maybe('le tiroir contient la pièce seule et le bouton ; élargir ne referme pas le tiroir ouvert ; la portée survit au changement de disposition', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11, window: { width: 700 } });
    openCard(ui, 11);
    assert.equal(ui.wv.state().layout, 'compact');
    assert.equal(ui.$('.j2ha-wv-nav .j2ha-wv-widen').length, 1);
    assert.deepEqual(roomIds(ui), ['11']);
    ui.click('.j2ha-wv-drawer-toggle');
    assert.equal(ui.wv.state().drawerOpen, true);
    ui.click('.j2ha-wv-widen');
    assert.equal(ui.wv.state().drawerOpen, true, 'le tiroir ouvert reste ouvert');
    assert.equal(roomIds(ui).length, 5);
    const narrow = startBig({ rooms: 5, equipments: 40, seed: 11, window: { width: 700 } });
    openCard(narrow, 11);
    narrow.win.setSize(1400, 900);
    assert.equal(narrow.wv.state().layout, 'split');
    assert.equal(scope(narrow), 'piece', 'changer de disposition conserve la portée');
  });
});

describe('25.6 / AC9 — relectures et pièce disparue', () => {
  maybe('une relecture des états garde la portée et la sélection', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    openCard(ui, 11);
    ui.page.reader.trigger();
    ui.advance(500);
    ui.respond('getEquipmentStates', { state: 'ok', result: { status: 'ok', payload: { schema_version: 1, available: true, meta: { action_in_progress: false }, equipments: ui.equipments, unread: [] } } });
    assert.equal(scope(ui), 'piece');
    assert.deepEqual(roomIds(ui), ['11']);
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="11"]').attr('aria-selected'), 'true');
  });

  maybe('reconcile sans la pièce : portée « toutes », sans sélection, entrée remplacée (rien de poussé)', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    openCard(ui, 11);
    const pushes = ui.win.historyWrites.push;
    const next = ui.rooms.filter((r) => r.object_id !== 11);
    ui.wv.reconcile(next);
    assert.equal(scope(ui), 'toutes');
    assert.equal(ui.wv.state().room, null);
    assert.equal(ui.win.historyWrites.push, pushes, 'aucune entrée poussée');
    assert.equal(ui.win.location.hash, '');
    assert.equal(roomIds(ui).length, 4);
  });

  maybe('reconcile sans l’équipement sélectionné : retour à la sélection de la pièce, portée pièce conservée', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    openCard(ui, 11);
    const id = Number(ui.$('.j2ha-wv-room[data-object_id="11"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.selectEquipment(id, ok(tree(id, [READY])));
    const next = JSON.parse(JSON.stringify(ui.rooms));
    next.find((r) => r.object_id === 11).equipments = next.find((r) => r.object_id === 11).equipments.filter((e) => e.eq_id !== id);
    ui.wv.reconcile(next);
    assert.equal(scope(ui), 'piece');
    assert.equal(ui.wv.state().room, 11);
    assert.equal(ui.wv.state().eq, null);
  });
});

describe('25.6 / D1 — modèle d’arbre pur', () => {
  it('buildTreeModel : portée « piece » = une seule pièce, sans titre de groupe ; sans pièce sélectionnée, retombe sur « toutes »', () => {
    const rooms = [1, 2, 3].map((id) => ({ object_id: id, object_name: 'P' + id, icon_classes: '', color: '', equipments: [{ eq_id: id * 10, eq_name: 'e' + id, enabled: true }] }));
    const groups = [{ title: 'Parent', room_ids: [1, 2] }, { title: 'Autre', room_ids: [3] }];
    const base = { rooms, groups, overview: null, filter: null, search: '', expanded: {}, selectedRoom: 2, selectedEq: null };
    const one = W.buildTreeModel(Object.assign({ scope: 'piece' }, base));
    assert.equal(one.roomCount, 1);
    assert.deepEqual(one.groups.map((g) => g.title), [null]);
    assert.equal(one.groups[0].rooms[0].object_id, 2);
    assert.equal(W.buildTreeModel(Object.assign({ scope: 'toutes' }, base)).roomCount, 3);
    assert.equal(W.buildTreeModel(Object.assign({ scope: 'piece' }, base, { selectedRoom: null })).roomCount, 3);
    assert.equal(W.buildTreeModel(base).roomCount, 3, 'sans portée : comportement de 25.4');
  });
});
