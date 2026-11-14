// ARTEFACT — Story 25.6, puis front v3 (Lot 2). Garde levée (front v3, Lot 2) : la PORTÉE de la vue C disparaît. Story 25.6
// ouvrait une carte sur la pièce SEULE (`data-j2ha-scope="piece"`) et la bascule « Cette pièce | Toute la maison » (front v2,
// Lot 7) changeait la portée. Décision du challenge UX du 14/11 (synthèse, point 6) : UN arbre de toute la maison, avec une
// recherche qui le filtre ; la bascule est supprimée, un ancien lien `seule:1` s'ouvre sur toute la maison ; le fil d'Ariane
// `Maison › Niveau › Pièce` remplace « Page principale » et « Pièces ». Ce fichier vérifie ce nouveau contrat. Vrai code sur
// faux DOM ; données fictives (CC-48).
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

function type(ui, value) {
  const search = ui.$('.j2ha-wv-search').list[0];
  search.props.value = value;
  search.handlers.input.call(search, { target: search });
  ui.advance(400);
}

describe('front v3 (Lot 2) — un seul arbre : la carte ouvre toute la maison sur sa pièce', () => {
  maybe('carte : toutes les pièces, la pièce dépliée et sélectionnée ; aucune bascule de portée', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11, grouped: true, unassigned: 3 });
    openCard(ui, 12);
    assert.equal(scope(ui), 'toutes');
    assert.equal(roomIds(ui).length, 6, 'cinq pièces et « Sans pièce »');
    const room = ui.$('.j2ha-wv-room[data-object_id="12"]');
    assert.equal(room.attr('aria-expanded'), 'true');
    assert.equal(room.attr('aria-selected'), 'true');
    for (const gone of ['.j2ha-wv-scope', '.j2ha-wv-narrow', '.j2ha-wv-widen']) assert.equal(ui.$(gone).length, 0, gone);
    assert.equal(ui.win.location.hash, '#j2ha-vue=piece:12', 'plus de seule:1');
  });

  maybe('« Sans pièce » (object_id 0) s’ouvre de la même façon', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11, unassigned: 3 });
    openCard(ui, 0);
    assert.equal(scope(ui), 'toutes');
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="0"]').attr('aria-selected'), 'true');
    assert.ok(roomIds(ui).length > 1);
  });

  maybe('ligne de la liste « À faire » : même arbre complet, filtre gardé', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 4 });
    // Garde levée (front v3, Lot 1, P8) : plus de liste filtrée ; la vue s'ouvre depuis une ligne « À faire » (puce « Bloqués »).
    ui.page.setFilter('blocked');
    ui.click('#j2ha_v2_todo .j2ha-v3-todo-open');
    assert.equal(ui.isOpen(), true);
    assert.equal(scope(ui), 'toutes');
    assert.equal(ui.page.filter(), 'published');
    assert.ok(roomIds(ui).length > 1);
  });

  maybe('effectifs des puces : ceux de la maison, comme sur la page principale', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    const house = ui.page.snapshot().view.overview;
    const O = require('../../desktop/js/jeedom2ha_overview.js');
    openCard(ui, 11);
    assert.deepEqual(ui.$('.j2ha-wv-chips .j2ha-chip-filter').list.map((n) => plain(ui.$(n).text()).trim()),
      O.chipsFor(house.counts).map((c) => plain(c.label)));
  });
});

describe('front v3 (Lot 2) — fil d’Ariane Maison › Niveau › Pièce', () => {
  maybe('pièce : « Maison » (retour, même historique), niveaux, pièce courante (aria-current) ; plus de « Page principale » ni de « Pièces »', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11, grouped: true });
    openCard(ui, 12);
    const crumb = ui.$('.j2ha-wv-bar .j2ha-wv-crumb');
    assert.equal(crumb.length, 1);
    assert.equal(plain(crumb.attr('aria-label')), "Fil d'Ariane");
    assert.equal(plain(ui.$('.j2ha-wv-back').text()).trim(), 'Maison');
    assert.equal(plain(ui.$('.j2ha-wv-crumb-current').text()).trim(), ui.rooms.find((r) => r.object_id === 12).object_name);
    assert.equal(ui.$('.j2ha-wv-crumb-current').attr('aria-current'), 'page');
    const texts = ui.$('#j2ha_workView button').list.map((n) => plain(ui.$(n).text()).trim());
    assert.ok(!texts.includes('Page principale') && !texts.includes('Pièces'), 'anciens boutons retirés');
    assert.equal(plain(ui.$('.j2ha-wv-drawer-toggle').attr('aria-label') || ui.$('.j2ha-wv-drawer-toggle').attr('title')).trim().length > 0, true, 'tiroir : icône nommée');
    ui.click('.j2ha-wv-back');
    assert.equal(ui.isOpen(), false);
    assert.equal(ui.win.location.hash, '');
  });

  maybe('équipement : la pièce du fil d’Ariane est un lien qui revient à la pièce', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    openCard(ui, 11);
    const id = Number(ui.$('.j2ha-wv-room[data-object_id="11"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.selectEquipment(id, ok(tree(id, [READY])));
    assert.equal(ui.$('.j2ha-wv-crumb-current').length, 0);
    ui.click('.j2ha-wv-crumb-room');
    assert.equal(ui.wv.state().room, 11);
    assert.equal(ui.wv.state().eq, null);
    assert.equal(ui.$('.j2ha-wv-crumb-current').length, 1);
  });

  maybe('un niveau du fil d’Ariane revient à la page principale', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11, grouped: true });
    openCard(ui, 12);
    const levels = ui.$('.j2ha-wv-crumb-level');
    if (levels.length === 0) return; // scène sans niveau intermédiaire
    ui.click('.j2ha-wv-crumb-level');
    assert.equal(ui.isOpen(), false);
  });
});

describe('front v3 (Lot 2) — la recherche filtre tout l’arbre ; le volet de droite dit « n résultats »', () => {
  maybe('recherche : toutes les pièces, « n résultats » à droite, la sélection reste dessous ; vider le champ la rend', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    openCard(ui, 11);
    const other = ui.rooms.find((r) => r.object_id !== 11 && r.object_id > 0);
    const before = ui.calls.length;
    type(ui, other.object_name);
    assert.ok(roomIds(ui).includes(String(other.object_id)), 'la pièce cherchée apparaît');
    assert.equal(ui.$('.j2ha-wv-tree .j2ha-wv-group-other').length, 0, 'plus de groupe « Dans les autres pièces »');
    const n = ui.$('.j2ha-wv-tree .j2ha-wv-eq').length;
    assert.ok(n > 0);
    assert.equal(ui.$('.j2ha-wv-results').list[0].visible, true);
    assert.equal(ui.$('.j2ha-wv-pane').list[0].visible, false);
    assert.equal(plain(ui.$('.j2ha-wv-results-title').text()).trim(), n + (n > 1 ? ' résultats' : ' résultat'));
    assert.equal(ui.$('.j2ha-wv-results .j2ha-wv-result').length, n);
    type(ui, 'zzz introuvable');
    assert.equal(plain(ui.$('.j2ha-wv-results-title').text()).trim(), 'Aucun résultat');
    assert.equal(plain(ui.$('.j2ha-wv-search-status').text()).trim(), 'Aucun résultat');
    type(ui, '');
    assert.equal(ui.$('.j2ha-wv-results').list[0].visible, false);
    assert.equal(ui.$('.j2ha-wv-pane').list[0].visible, true);
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="11"]').attr('aria-selected'), 'true', 'sélection inchangée');
    assert.equal(ui.calls.length, before, 'aucune requête');
  });

  maybe('un résultat choisi affiche l’équipement (une lecture) ; taper de nouveau rend les résultats', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    openCard(ui, 11);
    const other = ui.rooms.find((r) => r.object_id !== 11 && r.object_id > 0);
    type(ui, other.object_name);
    const first = ui.$('.j2ha-wv-results .j2ha-wv-result').list[0];
    const id = Number(first.attrs['data-eq-id']);
    ui.click(`.j2ha-wv-results .j2ha-wv-result[data-eq-id="${id}"]`);
    assert.equal(ui.wv.state().eq, id);
    assert.equal(ui.count('getMappingOverrides'), 1);
    assert.equal(ui.$('.j2ha-wv-results').list[0].visible, false);
    assert.equal(ui.$('.j2ha-wv-pane').list[0].visible, true);
    type(ui, other.object_name.slice(0, -1));
    assert.equal(ui.$('.j2ha-wv-results').list[0].visible, true);
  });
});

describe('front v3 (Lot 2) — anciens liens et relectures', () => {
  maybe('un ancien lien `seule:1` rouvre la pièce dans l’arbre complet', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11, window: { hash: '#j2ha-vue=piece:11;seule:1' } });
    assert.equal(ui.isOpen(), true);
    assert.equal(scope(ui), 'toutes');
    assert.equal(ui.wv.state().room, 11);
    assert.equal(roomIds(ui).length, 5);
  });

  maybe('une relecture des états garde la sélection', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    openCard(ui, 11);
    ui.page.reader.trigger();
    ui.advance(500);
    ui.respond('getEquipmentStates', { state: 'ok', result: { status: 'ok', payload: { schema_version: 1, available: true, meta: { action_in_progress: false }, equipments: ui.equipments, unread: [] } } });
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="11"]').attr('aria-selected'), 'true');
    assert.equal(roomIds(ui).length, 5);
  });

  maybe('reconcile sans la pièce : sans sélection, entrée remplacée (rien de poussé)', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    openCard(ui, 11);
    const pushes = ui.win.historyWrites.push;
    ui.wv.reconcile(ui.rooms.filter((r) => r.object_id !== 11));
    assert.equal(ui.wv.state().room, null);
    assert.equal(ui.win.historyWrites.push, pushes, 'aucune entrée poussée');
    assert.equal(ui.win.location.hash, '');
    assert.equal(roomIds(ui).length, 4);
  });

  maybe('reconcile sans l’équipement sélectionné : retour à la sélection de la pièce', () => {
    const ui = startBig({ rooms: 5, equipments: 40, seed: 11 });
    openCard(ui, 11);
    const id = Number(ui.$('.j2ha-wv-room[data-object_id="11"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.selectEquipment(id, ok(tree(id, [READY])));
    const next = JSON.parse(JSON.stringify(ui.rooms));
    next.find((r) => r.object_id === 11).equipments = next.find((r) => r.object_id === 11).equipments.filter((e) => e.eq_id !== id);
    ui.wv.reconcile(next);
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

// Relecture ClaudeBox de #307 (P2) : une carte « grisée » par le filtre de la page B reste cliquable et ouvre la pièce
// seule avec ce filtre ; la puce active ne doit jamais être désactivée, sinon le filtre ne peut plus être retiré.
describe('25.6 — puce active jamais désactivée (relecture #307)', () => {
  const O = require('../../desktop/js/jeedom2ha_overview.js');
  // Garde levée (front v2, Lot 7, spec E2/E3) : les puces à zéro ne sont plus affichées (au lieu d'être grisées), sauf la
  // puce active, qui reste cliquable pour retirer le filtre.
  it('chipsFor : la puce active à zéro reste affichée et cliquable ; les autres puces à zéro sont masquées', () => {
    const counts = { published: 0, to_apply: 0, blocked: 2, other: 0, unread: 0 };
    const chips = O.chipsFor(counts, 'published');
    assert.equal(chips.find((c) => c.key === 'published').disabled, false);
    assert.equal(chips.find((c) => c.key === 'to_apply'), undefined);
    assert.equal(chips.find((c) => c.key === 'blocked').disabled, false);
    assert.deepEqual(chips.map((c) => c.key), ['published', 'blocked']);
  });
  it('chipsFor : la puce « non lus » active à zéro reste affichée', () => {
    const chips = O.chipsFor({ published: 1, to_apply: 0, blocked: 0, other: 0, unread: 0 }, 'unread');
    const unread = chips.find((c) => c.key === 'unread');
    assert.ok(unread, 'puce non lus présente');
    assert.equal(unread.disabled, false);
    assert.equal(O.chipsFor({ published: 1, to_apply: 0, blocked: 0, other: 0, unread: 0 }).find((c) => c.key === 'unread'), undefined);
  });
});
