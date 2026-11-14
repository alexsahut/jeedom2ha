// ARTEFACT — Front v2, Lot 7 (spec E2, E3) : la maison et la pièce. Puces à zéro masquées, « exclus ou inactifs », clic de
// puce = filtre SUR PLACE, phrase « Cliquez sur un chiffre… », légende repliable, bloc « À faire » (cinq lignes, cause en
// clair et action de la fiche Jeedom2haLexique), mention des scénarios depuis `status.publication`, conseils seulement si
// le nombre est connu sans requête de plus ; vue de travail : recherche globale groupée, bascule de portée, une seule mention
// par ligne « À traiter ». Vrai code sur faux DOM (squelette PHP réel) ; données fictives (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const O = require('../../desktop/js/jeedom2ha_overview.js');
const W = require('../../desktop/js/jeedom2ha_workview.js');
const L = require('../../desktop/js/jeedom2ha_lexique.js');
const { createDom } = require('./helpers/fake_dom');
const { SCENE, FIXTURE, plain, clone, phpAvailable, renderPhp, mainPart, equipmentsFor, okBody } = require('./helpers/page_b_harness');
const { startBig, openCard } = require('./helpers/workview_harness');

const maybe = phpAvailable ? it : it.skip;
const root = path.join(__dirname, '..', '..');

// Équipement bloqué « le plugin hésite sur le type » (lampe typée prise) et équipement sans type générique.
const AMBIGUOUS = JSON.parse(JSON.stringify(FIXTURE['106'].aggregated).replace(/no_generic_type_configured/g, 'ambiguous_skipped'));
const NO_TYPE = clone(FIXTURE['106'].aggregated);

function start(options) {
  const opts = options || {};
  const rendered = renderPhp(SCENE);
  const rooms = rendered.vars.j2haRoomsTree;
  const dom = createDom();
  const calls = [];
  dom.$.ajax = (o) => { calls.push({ options: o, action: (o.data || {}).action }); };
  dom.add(mainPart(rendered.html));
  const views = [];
  let status = opts.status === undefined ? null : opts.status;
  const page = O.createPage({
    $: dom.$, document: dom.document, bootbox: dom.bootbox, rooms,
    readStates: O.ajaxFetch(dom.$), now: () => 5_000_000,
    setTimeout: () => 0, clearTimeout: () => {},
    openRoom: () => {}, excludeRoom: () => {},
    openView: (target) => { views.push(target); return true; },
    bridgeStatus: () => status,
  });
  page.init();
  const equipments = equipmentsFor(rooms);
  equipments['102'] = clone(AMBIGUOUS);
  equipments['106'] = clone(NO_TYPE);
  if (typeof opts.mutate === 'function') opts.mutate(equipments, rooms);
  calls[0].options.success(okBody(equipments));
  const $ = dom.$;
  return {
    dom, $, page, views, calls, rooms, equipments,
    setStatus: (next) => { status = next; },
    text: (selector) => plain($(selector).text()).replace(/\s+/g, ' ').trim(),
    click: (selector) => { const el = $(selector).first(); assert.ok(el.length, selector); el.list[0].handlers.click.call(el.list[0], { preventDefault() {}, stopPropagation() {} }); },
  };
}

describe('Lot 7 / E2 — puces : zéro masquées, « exclus ou inactifs », filtre sur place', () => {
  maybe('aucune puce à zéro ; libellé « exclus ou inactifs » ; un clic filtre sur place sans ouvrir la vue ni lire le réseau', () => {
    const ui = start();
    const counts = ui.page.view().overview.counts;
    const chips = ui.$('#j2ha_houseChips .j2ha-chip-filter').list;
    assert.ok(chips.length > 0);
    chips.forEach((chip) => assert.ok(counts[chip.attrs['data-filter']] > 0, chip.attrs['data-filter']));
    assert.equal(ui.text('#j2ha_houseChips .j2ha-chip-filter[data-filter="other"]'), `${counts.other} exclus ou inactifs`);
    const before = ui.calls.length;
    ui.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="blocked"]');
    assert.deepEqual(ui.views, [], 'la vue de travail ne s’ouvre pas');
    assert.equal(ui.page.filter(), 'blocked');
    assert.equal(ui.$('#j2ha_filterList .j2ha-frow').length, counts.blocked);
    assert.equal(ui.$('#j2ha_houseChips .j2ha-chip-filter[data-filter="blocked"]').attr('aria-controls'), 'j2ha_filterPanel');
    ui.click('#j2ha_houseGauge .j2ha-seg[data-filter="published"]');
    assert.equal(ui.page.filter(), 'published', 'le segment filtre de la même façon');
    assert.deepEqual(ui.views, []);
    assert.equal(ui.calls.length, before, 'aucune requête');
    ui.click('#j2ha_filterList .j2ha-frow-btn');
    assert.equal(ui.views.length, 1, 'une ligne de la liste ouvre la vue sur l’équipement');
    assert.ok(ui.views[0].room !== undefined && ui.views[0].eq !== undefined);
  });

  maybe('« Cliquez sur un chiffre pour voir la liste. » est affiché avec les puces', () => {
    const ui = start();
    assert.equal(ui.text('#j2ha_houseBlock .j2ha-v2-chips-hint'), 'Cliquez sur un chiffre pour voir la liste.');
    assert.equal(ui.$('#j2ha_houseBlock .j2ha-v2-chips-hint').list[0].visible, true);
  });

  maybe('filtre devenu vide après une relecture : « Aucun équipement dans cet état. », aucune ligne', () => {
    const ui = start();
    ui.page.setFilter('blocked');
    const equipments = clone(ui.equipments);
    equipments['102'] = clone(FIXTURE['101'].aggregated);
    equipments['106'] = clone(FIXTURE['101'].aggregated);
    ui.page.reader.load();
    ui.calls[ui.calls.length - 1].options.success(okBody(equipments));
    assert.equal(ui.page.view().overview.counts.blocked, 0);
    assert.equal(ui.$('#j2ha_filterList .j2ha-frow').length, 0);
    assert.equal(ui.text('#j2ha_filterList .j2ha-v2-filter-empty'), 'Aucun équipement dans cet état.');
    assert.equal(ui.$('#j2ha_houseChips .j2ha-chip-filter[data-filter="blocked"]').length, 1, 'la puce active à zéro reste pour retirer le filtre');
  });
});

describe('Lot 7 / E2 — bloc « À faire »', () => {
  maybe('cite la lampe hésitante et l’équipement sans type avec leur action ; « Voir les N bloqués » filtre sur place', () => {
    const ui = start();
    const rows = ui.$('#j2ha_v2_todo .j2ha-v2-todo-row').list;
    assert.equal(ui.text('#j2ha_v2_todo .j2ha-v2-todo-title'), 'À faire');
    const byId = Object.fromEntries(rows.map((row) => [row.attrs['data-eq-id'], row]));
    assert.ok(byId['102'] && byId['106'], 'les deux équipements bloqués');
    assert.match(plain(ui.$(byId['102']).text()), /Bloqué/);
    assert.match(plain(ui.$(byId['102']).text()), /Le plugin hésite sur le type de cet équipement\./);
    assert.match(plain(ui.$(byId['106']).text()), /Jeedom ne sait pas à quoi servent ces commandes\./);
    // Garde levée (front v2, Lot 9a, point 9) : l'équipement hésitant propose « Publier quand même » (le type corrigé ne
    // le débloquerait pas) ; le bouton ouvre la fiche, où l'action du même nom règle « Toujours ».
    const fix = ui.$(byId['102']).find('.j2ha-v2-todo-action');
    assert.equal(plain(fix.text()), L.ACTIONS.publish_anyway);
    assert.equal(fix.list[0].tag, 'button');
    assert.ok(fix.hasClass('btn-primary'));
    fix.list[0].handlers.click.call(fix.list[0], {});
    assert.deepEqual(ui.views, [{ room: 3, eq: 102 }], '« Publier quand même » ouvre la fiche de l’équipement');
    const link = ui.$(byId['106']).find('.j2ha-v2-todo-action');
    assert.equal(link.list[0].tag, 'a');
    assert.equal(link.attr('href'), 'index.php?v=d&p=types');
    assert.equal(link.attr('target'), '_blank');
    assert.equal(plain(link.text()), L.ACTIONS.generic_types);
    const blocked = ui.page.view().overview.counts.blocked;
    assert.equal(ui.text('#j2ha_v2_todo .j2ha-v2-todo-all'), `Voir les ${blocked} bloqués`);
    ui.click('#j2ha_v2_todo .j2ha-v2-todo-all');
    assert.equal(ui.page.filter(), 'blocked');
    assert.equal(ui.views.length, 1, 'la vue ne s’ouvre pas');
    ui.click('#j2ha_v2_todo .j2ha-v2-todo-all');
    assert.equal(ui.page.filter(), 'blocked', 'jamais de bascule : le filtre reste posé');
  });

  maybe('cinq lignes au plus, dans l’ordre de la grille ; absent quand rien n’est bloqué', () => {
    const many = start({ mutate: (equipments) => { ['101', '103', '105', '107', '108', '109', '110'].forEach((id) => { equipments[id] = clone(NO_TYPE); }); } });
    assert.ok(many.page.view().overview.counts.blocked > 5);
    assert.equal(many.$('#j2ha_v2_todo .j2ha-v2-todo-row').length, 5);
    const grid = many.$('#j2ha_roomCards .j2ha-room-card').list.map((el) => Number(el.attrs['data-object_id']));
    const rooms = many.$('#j2ha_v2_todo .j2ha-v2-todo-row').list.map((row) => {
      const id = Number(row.attrs['data-eq-id']);
      return many.rooms.find((r) => r.equipments.some((e) => e.eq_id === id)).object_id;
    });
    const ranks = rooms.map((id) => grid.indexOf(id));
    assert.deepEqual(ranks, [...ranks].sort((a, b) => a - b));
    const none = start({ mutate: (equipments) => { equipments['102'] = clone(FIXTURE['101'].aggregated); equipments['106'] = clone(FIXTURE['101'].aggregated); } });
    assert.equal(none.page.view().overview.counts.blocked, 0);
    assert.equal(none.$('#j2ha_v2_todo').children().length, 0, 'vide = invisible (point de montage :empty)');
  });

  it('todoItems : cause lue dans l’entrée agrégée (groupBlockedCauses), fiche du lexique, aucune lecture d’arbre', () => {
    const rooms = [{ object_id: 3, object_name: 'Bureau', equipments: [
      { eq_id: 1, eq_name: 'Lampe Chevet', enabled: true, eq_type: 'demo' },
      { eq_id: 2, eq_name: 'Équipement libre', enabled: true, eq_type: 'demo' },
    ] }];
    const equipments = { 1: clone(AMBIGUOUS), 2: clone(NO_TYPE) };
    const items = O.todoItems(O.computeOverview(rooms, equipments), equipments);
    assert.deepEqual(items.map((i) => [i.eq_id, i.kind, i.action && i.action.key]), [[1, 'blocked', 'publish_anyway'], [2, 'blocked', 'generic_types']]);
    assert.equal(items[0].text, O.causeSentence(L.causeSheet('ambiguous_skipped').quoi));
    assert.equal(O.causeSentence('Non publié : le nom dit « lampe ».'), 'Le nom dit « lampe ».');
  });
});

describe('Lot 7 / E2 — légende, titre, phrase d’accueil', () => {
  maybe('« Que veulent dire ces mots ? » : repliée, aria-expanded, six états (mots de 25.1) puis Pilotable / Lecture seule / Conseil', () => {
    const ui = start();
    const toggle = ui.$('#j2ha_v2_legend .j2ha-v2-legend-toggle');
    assert.equal(plain(toggle.text()), 'Que veulent dire ces mots ?');
    assert.equal(toggle.attr('aria-expanded'), 'false');
    assert.equal(ui.$('#j2ha_v2_legendList').list[0].visible, false);
    ui.click('#j2ha_v2_legend .j2ha-v2-legend-toggle');
    assert.equal(toggle.attr('aria-expanded'), 'true');
    assert.equal(ui.$('#j2ha_v2_legendList').list[0].visible, true);
    const terms = ui.$('#j2ha_v2_legendList dt').list.map((dt) => plain(ui.$(dt).text()).trim());
    assert.deepEqual(terms, [...['published', 'to_apply', 'blocked', 'excluded', 'disabled', 'nothing_to_publish'].map((s) => M.EQUIPMENT_STATE_LABELS[s]), 'Pilotable', 'Lecture seule', 'Conseil']);
    ui.click('#j2ha_v2_legend .j2ha-v2-legend-toggle');
    assert.equal(toggle.attr('aria-expanded'), 'false');
  });

  maybe('titre « Ce que Jeedom publie dans Home Assistant » et phrase d’accueil, sans perdre le lien « Aide »', () => {
    const ui = start();
    assert.equal(ui.text('#j2ha_mainView legend'), 'Ce que Jeedom publie dans Home Assistant');
    assert.equal(ui.text('#j2ha_mainView .j2ha-v2-welcome'), 'jeedom2ha publie vos équipements Jeedom dans Home Assistant. Jeedom reste la source : rien n\'y est modifié.');
    assert.equal(ui.$('#j2ha_mainView .j2ha-help-line a').length, 1, 'le lien « Aide » reste');
    ui.page.render();
    assert.equal(ui.$('#j2ha_mainView .j2ha-v2-welcome').length, 1, 'posée une seule fois');
  });
});

describe('Lot 7 / E2 — scénarios (status.publication, Lot 3)', () => {
  maybe('mention « + N scénarios publiés comme boutons » si le démon fournit le nombre ; rien sinon ; suit la relecture de l’état', () => {
    const without = start();
    assert.doesNotMatch(without.text('#j2ha_houseMeta'), /scénario/);
    const ui = start({ status: { publication: { equipments_published: 9, entities_published: 20, scenarios_published: 12 } } });
    assert.match(ui.text('#j2ha_houseMeta'), / · \+ 12 scénarios publiés comme boutons$/);
    ui.setStatus({ publication: { scenarios_published: 1 } });
    ui.page.statusChanged();
    assert.match(ui.text('#j2ha_houseMeta'), / · \+ 1 scénario publié comme bouton$/);
    ui.setStatus({ publication: null });
    ui.page.statusChanged();
    assert.doesNotMatch(ui.text('#j2ha_houseMeta'), /scénario/);
  });

  it('scenarioMention : nombre absent, nul, non numérique → aucune mention', () => {
    for (const status of [null, {}, { publication: null }, { publication: {} }, { publication: { scenarios_published: 0 } }, { publication: { scenarios_published: '3' } }]) {
      assert.equal(O.scenarioMention(status), '', JSON.stringify(status));
    }
    assert.equal(plain(O.scenarioMention({ publication: { scenarios_published: 2 } })), '+ 2 scénarios publiés comme boutons');
  });
});

describe('Lot 7 — conseils : seulement si le nombre est connu sans requête de plus', () => {
  maybe('la route agrégée ne porte pas les conseils : aucune puce, aucune ligne, nombre inconnu (null), aucune fiche lue', () => {
    const ui = start();
    assert.equal(ui.page.view().overview.advice, null);
    assert.equal(ui.$('#j2ha_houseChips .j2ha-chip-filter[data-filter="advice"]').length, 0);
    assert.equal(ui.$('#j2ha_v2_todo [data-kind="advice"]').length, 0);
    assert.equal(ui.calls.filter((c) => c.action === 'getMappingOverrides').length, 0);
  });

  maybe('si chaque entrée portait `hints` : puce « N conseils », filtre sur place, ligne « Conseil » après les bloqués', () => {
    const ui = start({ mutate: (equipments) => {
      Object.values(equipments).forEach((entry) => { entry.hints = []; });
      equipments['101'].hints = [{ code: 'actions_not_linked_to_state', cmd_ids: [], details: { count: 3 } }];
    } });
    const overview = ui.page.view().overview;
    const published = overview.rooms.flatMap((r) => r.equipments).find((r) => r.eq_id === 101);
    assert.equal(published.state, 'published');
    assert.equal(overview.advice, 1);
    assert.equal(ui.text('#j2ha_houseChips .j2ha-chip-filter[data-filter="advice"]'), '1 conseil');
    ui.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="advice"]');
    assert.deepEqual(ui.$('#j2ha_filterList .j2ha-frow-btn').list.map((b) => plain(ui.$(b).find('.j2ha-frow-name').text())), ['Eq 101']);
    const kinds = ui.$('#j2ha_v2_todo .j2ha-v2-todo-row').list.map((row) => row.attrs['data-kind']);
    assert.equal(kinds[kinds.length - 1], 'advice');
    assert.ok(kinds.indexOf('advice') > kinds.lastIndexOf('blocked'));
  });

  it('adviceCount : une seule entrée sans `hints` rend le nombre inconnu', () => {
    assert.equal(O.adviceCount([{ state: 'published', advice: true }, { state: 'published', advice: null }]), null);
    assert.equal(O.adviceCount([{ state: 'published', advice: true }, { state: 'blocked', advice: false }, { state: null, advice: null }]), 1);
    assert.equal(O.adviceCount([]), null);
  });
});

describe('Lot 7 / E3 — vue de travail', () => {
  it('buildTreeModel : en portée pièce, la recherche ajoute « Dans les autres pièces » (ordre de la grille), le filtre s’applique aussi', () => {
    const rooms = [1, 2, 3].map((id) => ({ object_id: id, object_name: 'Salle ' + id, icon_classes: '', color: '',
      equipments: [{ eq_id: id * 10, eq_name: 'Lampe ' + id, enabled: true }, { eq_id: id * 10 + 1, eq_name: 'Prise ' + id, enabled: true }] }));
    const groups = [{ title: 'Étage', room_ids: [3, 1] }, { title: null, room_ids: [2] }];
    const base = { rooms, groups, overview: null, filter: null, expanded: {}, selectedRoom: 1, selectedEq: null, scope: 'piece' };
    const lamps = W.buildTreeModel(Object.assign({ search: 'lampe' }, base));
    assert.deepEqual(lamps.groups.map((g) => [g.title, g.others, g.rooms.map((r) => r.object_id)]), [[null, false, [1]], ['{{Dans les autres pièces}}', true, [3, 2]]]);
    assert.equal(lamps.otherCount, 2);
    const other = W.buildTreeModel(Object.assign({ search: 'Salle 2' }, base));
    assert.deepEqual(other.groups.map((g) => g.rooms.map((r) => r.object_id)), [[2]], 'la pièce ouverte ne correspond pas : seul le groupe des autres');
    assert.equal(other.groups[0].others, true);
    assert.equal(W.buildTreeModel(Object.assign({ search: '' }, base)).groups.length, 1, 'sans recherche : la pièce seule');
    const states = { rooms: rooms.map((r) => ({ object_id: r.object_id, counts: {}, equipments: r.equipments.map((e) => ({ eq_id: e.eq_id, state: 'published', group: e.eq_id % 10 ? 'blocked' : 'published', blocked_mention: 0 })) })) };
    const filtered = W.buildTreeModel(Object.assign({}, base, { overview: states, filter: 'blocked', search: 'lampe' }));
    assert.deepEqual(filtered.groups.map((g) => g.rooms.map((r) => r.rows.map((row) => row.eq_id))), [[[30], [20]]],
      'la pièce ouverte filtrée n’a aucune lampe bloquée ; les autres pièces montrent leurs lampes sans le filtre de la pièce');
  });

  // Relecture Codex (PR #392, P2) : une pièce choisie dans « Dans les autres pièces » devient la pièce de la portée ; les
  // puces doivent prendre ses effectifs.
  maybe('portée pièce : choisir une autre pièce (ou un de ses équipements) depuis la recherche met les puces à ses effectifs', () => {
    const O2 = require('../../desktop/js/jeedom2ha_overview.js');
    const chipText = (ui) => ui.$('.j2ha-wv-chips .j2ha-chip-filter').list.map((n) => plain(ui.$(n).text()).trim());
    for (const target of ['room', 'eq']) {
      const ui = startBig({ rooms: 3, equipments: 30, seed: 6 });
      openCard(ui, 11);
      const rooms = ui.page.snapshot().view.overview.rooms;
      const other = rooms.find((r) => r.object_id === 10);
      assert.notDeepEqual(O2.chipsFor(other.counts).map((c) => plain(c.label)), O2.chipsFor(rooms.find((r) => r.object_id === 11).counts).map((c) => plain(c.label)), 'scène discriminante');
      const search = ui.$('.j2ha-wv-search').list[0];
      search.props.value = ui.rooms.find((r) => r.object_id === 10).object_name;
      search.handlers.input.call(search, { target: search });
      ui.advance(400);
      if (target === 'room') ui.click('.j2ha-wv-room[data-object_id="10"] > .j2ha-wv-row');
      else ui.click('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq .j2ha-wv-row');
      assert.equal(ui.wv.state().room, 10);
      assert.equal(ui.wv.state().scope, 'piece');
      assert.deepEqual(chipText(ui), O2.chipsFor(other.counts).map((c) => plain(c.label)), target);
    }
  });

  maybe('« À traiter dans cette pièce » : une seule mention par ligne (pas de « N bloquées » à côté de « N commandes bloquées : … »)', () => {
    let checked = 0;
    for (let seed = 1; seed <= 6; seed += 1) {
      const ui = startBig({ rooms: 3, equipments: 30, seed });
      for (const id of [10, 11, 12]) {
        openCard(ui, id);
        for (const row of ui.$('.j2ha-wv-todo-row').list) {
          if (ui.$(row).find('.j2ha-wv-todo-cause').length === 0) continue;
          assert.doesNotMatch(plain(ui.$(row).find('.j2ha-wv-todo-counters').text()), /bloquées?/, `seed ${seed}`);
          checked += 1;
        }
        ui.click('.j2ha-wv-back');
      }
    }
    assert.ok(checked > 0, 'des lignes avec cause ont été contrôlées');
  });
});

describe('Lot 7 — gardes', () => {
  it('aucune recopie des sources uniques ; pas de JSON.stringify ni de copie profonde des états dans la page', () => {
    const overview = fs.readFileSync(path.join(root, 'desktop/js/jeedom2ha_overview.js'), 'utf8');
    const workview = fs.readFileSync(path.join(root, 'desktop/js/jeedom2ha_workview.js'), 'utf8');
    for (const source of [overview, workview]) {
      assert.doesNotMatch(source, /COMMAND_CAUSE_CATEGORIES|categoryOfCause|function resolveEquipmentState/);
    }
    assert.doesNotMatch(overview, /JSON\.stringify|JSON\.parse|structuredClone/);
    assert.equal((overview.match(/action: 'getEquipmentStates'/g) || []).length, 1, 'un seul site d’appel de la route agrégée');
  });
});
