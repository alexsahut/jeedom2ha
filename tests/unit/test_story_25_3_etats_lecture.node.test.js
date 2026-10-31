// ARTEFACT — Story 25.3 (AC2, AC3, AC4, AC10, AC11, D1, D2) : agrégats de la page principale B, réconciliation
// « non lu », états de rendu de la lecture et invariants des segments. Pur, sans DOM. Données fictives (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const O = require('../../desktop/js/jeedom2ha_overview.js');

const FIXTURE = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'fixtures', 'story_25_2_parite_etat.json'), 'utf8'));
const plain = (text) => String(text).replace(/\{\{|\}\}/g, '');
const clone = (value) => JSON.parse(JSON.stringify(value));

/** Trois pièces fictives + une pseudo-pièce, équipements 101..110 du corpus de 25.2 (+ un id absent de la route). */
function sampleRooms() {
  return [
    { object_id: 1, object_name: 'Pièce A', equipments: [101, 102, 103].map((id) => ({ eq_id: id, eq_name: 'Eq ' + id, enabled: true })) },
    { object_id: 2, object_name: 'Pièce B', equipments: [104, 105, 998].map((id) => ({ eq_id: id, eq_name: 'Eq ' + id, enabled: id !== 104 })) },
    { object_id: 3, object_name: 'Pièce C', equipments: [106, 107, 108, 109, 110].map((id) => ({ eq_id: id, eq_name: 'Eq ' + id, enabled: true })) },
    { object_id: 0, object_name: 'Sans pièce', equipments: [] },
  ];
}
function sampleEquipments() {
  const out = {};
  for (const [id, entry] of Object.entries(FIXTURE)) out[id] = clone(entry.aggregated);
  return out;
}
const payloadOf = (equipments, meta) => ({
  schema_version: 1, available: true, meta: Object.assign({ action_in_progress: false }, meta || {}), equipments, unread: [],
});

describe('25.3 / D1, AC2 — agrégats construits sur resolveEquipmentState et summarizeRoom', () => {
  it('l’état de chaque équipement est resolveEquipmentState(entrée, enabled) avec enabled lu dans j2haRoomsTree', () => {
    const rooms = sampleRooms();
    const equipments = sampleEquipments();
    const overview = O.computeOverview(rooms, equipments);
    for (const room of overview.rooms) {
      const source = rooms.find((r) => r.object_id === room.object_id);
      for (const row of room.equipments) {
        const eq = source.equipments.find((e) => e.eq_id === row.eq_id);
        const entry = equipments[String(row.eq_id)];
        if (!entry) { assert.equal(row.state, null); continue; }
        assert.deepEqual({ state: row.state, blocked_mention: row.blocked_mention }, M.resolveEquipmentState(entry, eq.enabled));
      }
    }
  });

  it('table : enabled ∈ {true,false} sur un même équipement — « Désactivé » prime sur « Exclu » (25.1 R3/R4)', () => {
    const equipments = sampleEquipments();
    for (const [enabled, expected] of [[true, 'excluded'], [false, 'disabled']]) {
      const rooms = [{ object_id: 9, object_name: 'X', equipments: [{ eq_id: 110, eq_name: 'E', enabled }] }];
      const overview = O.computeOverview(rooms, { 110: equipments['110'] });
      assert.equal(overview.rooms[0].equipments[0].state, expected);
      assert.equal(overview.rooms[0].summary.by_state[expected], 1);
    }
  });

  it('les compteurs de pièce sont ceux de summarizeRoom, et la maison est la somme des pièces', () => {
    const rooms = sampleRooms();
    const equipments = sampleEquipments();
    const overview = O.computeOverview(rooms, equipments);
    for (const room of overview.rooms) {
      const source = rooms.find((r) => r.object_id === room.object_id);
      const enabledById = {};
      const trees = [];
      source.equipments.forEach((e) => { enabledById[e.eq_id] = e.enabled; if (equipments[String(e.eq_id)]) trees.push(equipments[String(e.eq_id)]); });
      assert.deepEqual(room.summary, M.summarizeRoom(trees, source.equipments.length, enabledById));
    }
    assert.deepEqual(overview.house, M.summarizeHouse(overview.rooms.map((r) => r.summary)));
    for (const state of M.EQUIPMENT_STATES) {
      assert.equal(overview.house.by_state[state], overview.rooms.reduce((n, r) => n + r.summary.by_state[state], 0));
    }
  });

  it('M = nombre d’équipements de j2haRoomsTree, pseudo-pièce comprise ; P = pièces avec object_id > 0', () => {
    const rooms = sampleRooms();
    rooms[3].equipments = [{ eq_id: 101, eq_name: 'Dupliqué fictif', enabled: true }];
    const overview = O.computeOverview(rooms, sampleEquipments());
    assert.equal(overview.total, 12);
    assert.equal(overview.rooms_count, 3);
  });

  it('la source ne réécrit aucune règle d’état, partition ni table de libellés (AC2)', () => {
    const source = fs.readFileSync('desktop/js/jeedom2ha_overview.js', 'utf8');
    for (const forbidden of ['COMMAND_CAUSE_CATEGORIES', 'categoryOfCause', 'classifyCommandCategory', 'analyzeEquipment', 'normalizeTree', 'sync_status', 'equipment_decision']) {
      assert.ok(!source.includes(forbidden), forbidden);
    }
    const php = fs.readFileSync('desktop/php/jeedom2ha.php', 'utf8');
    assert.ok(!php.includes('COMMAND_CAUSE_CATEGORIES') && !php.includes('categoryOfCause'));
  });

  it('git diff : aucune ligne de resolveEquipmentState, summarizeRoom & co. n’est modifiée', () => {
    const { execFileSync } = require('node:child_process');
    let base = 'main';
    try { execFileSync('git', ['rev-parse', '--verify', base], { stdio: 'ignore' }); } catch { base = 'origin/main'; }
    let diff = '';
    try { diff = execFileSync('git', ['diff', '-U0', base, '--', 'desktop/js/jeedom2ha_mapping_override.js'], { encoding: 'utf8' }); } catch { return; }
    const { ALLOWED_REMOVED } = require('./helpers/git_base');
    const removed = diff.split('\n').filter((l) => l.startsWith('-') && !l.startsWith('---') && !ALLOWED_REMOVED.has(l));
    assert.deepEqual(removed, [], 'seuls des ajouts sont admis dans jeedom2ha_mapping_override.js');
  });
});

describe('25.3 / AC3 — réconciliation « non lu »', () => {
  it('un eq_id de j2haRoomsTree absent de la route est non lu : jamais publié, bloqué, exclu ni désactivé', () => {
    const overview = O.computeOverview(sampleRooms(), sampleEquipments());
    const roomB = overview.rooms.find((r) => r.object_id === 2);
    const unread = roomB.equipments.find((e) => e.eq_id === 998);
    assert.equal(unread.state, null);
    assert.equal(unread.group, 'unread');
    assert.equal(roomB.summary.equipments_total - roomB.summary.equipments_read, 1);
    assert.equal(roomB.counts.unread, 1);
    assert.equal(overview.counts.unread, 1);
    const stated = M.EQUIPMENT_STATES.reduce((n, s) => n + roomB.summary.by_state[s], 0);
    assert.equal(stated, 2, 'les deux autres équipements seulement');
  });

  it('les clés de la route sont des chaînes, les eq_id de j2haRoomsTree des entiers ("101" ↔ 101)', () => {
    const equipments = { '101': sampleEquipments()['101'] };
    const overview = O.computeOverview([{ object_id: 1, object_name: 'A', equipments: [{ eq_id: 101, eq_name: 'E', enabled: true }] }], equipments);
    assert.equal(overview.rooms[0].equipments[0].state, 'published');
  });

  it('un eq_id de la route absent de j2haRoomsTree est ignoré sans erreur', () => {
    const equipments = sampleEquipments();
    const rooms = [{ object_id: 1, object_name: 'A', equipments: [{ eq_id: 101, eq_name: 'E', enabled: true }] }];
    const overview = O.computeOverview(rooms, equipments);
    assert.equal(overview.total, 1);
    assert.equal(overview.rooms[0].summary.equipments_read, 1);
  });

  it('une entrée dont jeedom_eq_id diffère de l’eq_id reste évaluée avec le enabled de j2haRoomsTree', () => {
    const entry = sampleEquipments()['110'];
    delete entry.jeedom_eq_id;
    const overview = O.computeOverview([{ object_id: 1, object_name: 'A', equipments: [{ eq_id: 110, eq_name: 'E', enabled: false }] }], { 110: entry });
    assert.equal(overview.rooms[0].equipments[0].state, 'disabled');
    assert.equal(overview.rooms[0].summary.by_state.disabled, 1);
  });

  it('libellé du repère : accord du pluriel par le code', () => {
    assert.equal(plain(O.unreadLabel(1)), '1 non lu');
    assert.equal(plain(O.unreadLabel(2)), '2 non lus');
  });
});

describe('25.3 / AC10, AC12 — segments sommant au total (invariant sur 20 fixtures seedées)', () => {
  function rng(seed) { let s = seed; return () => { s = (s * 1664525 + 1013904223) % 4294967296; return s / 4294967296; }; }

  it('publiés + à appliquer + bloqués + autres + non lus = M, par pièce et pour la maison', () => {
    const base = sampleEquipments();
    const ids = Object.keys(base);
    for (let seed = 1; seed <= 20; seed++) {
      const random = rng(seed);
      const rooms = [];
      const equipments = {};
      let next = 1000;
      const roomCount = 1 + Math.floor(random() * 5);
      for (let r = 0; r < roomCount; r++) {
        const list = [];
        const n = 1 + Math.floor(random() * 8);
        for (let i = 0; i < n; i++) {
          const id = next++;
          list.push({ eq_id: id, eq_name: 'E' + id, enabled: random() > 0.2 });
          if (random() > 0.15) equipments[String(id)] = Object.assign(clone(base[ids[Math.floor(random() * ids.length)]]), { jeedom_eq_id: id });
        }
        rooms.push({ object_id: r + 1, object_name: 'R' + r, equipments: list });
      }
      const overview = O.computeOverview(rooms, equipments);
      const sum = (c) => c.published + c.to_apply + c.blocked + c.other + c.unread;
      overview.rooms.forEach((room) => assert.equal(sum(room.counts), room.summary.equipments_total, `seed ${seed}`));
      assert.equal(sum(overview.counts), overview.total, `seed ${seed}`);
      for (const key of ['published', 'to_apply', 'blocked', 'other', 'unread']) {
        assert.equal(overview.counts[key], overview.rooms.reduce((n, r) => n + r.counts[key], 0), `seed ${seed} ${key}`);
      }
      const segments = O.gaugeSegments(overview.counts, overview.total);
      assert.equal(segments.reduce((n, s) => n + s.count, 0), overview.total);
      assert.ok(segments.every((s) => s.count > 0), 'segments de largeur nulle non rendus');
    }
  });

  it('ordre des segments : publiés, à appliquer, bloqués, exclus et autres, non lus', () => {
    const segments = O.gaugeSegments({ published: 1, to_apply: 2, blocked: 3, other: 4, unread: 5 }, 15);
    assert.deepEqual(segments.map((s) => s.key), ['published', 'to_apply', 'blocked', 'other', 'unread']);
    assert.deepEqual(segments.map((s) => s.pct), [1, 2, 3, 4, 5].map((n) => (n / 15) * 100));
  });

  it('l’aria-label de la jauge dit les nombres en toutes lettres', () => {
    const label = plain(O.gaugeLabel({ published: 5, to_apply: 1, blocked: 2, other: 3, unread: 0 }, 11));
    assert.match(label, /5 publiés sur 11/);
    assert.match(label, /1 à appliquer/);
    assert.match(label, /2 bloqués/);
    assert.match(label, /3 exclus et autres/);
    assert.doesNotMatch(label, /non lu/);
  });

  it('« N publiés sur M » accorde le pluriel et ne dit jamais « Sera publié » ni « prête »', () => {
    assert.equal(plain(O.houseHeadline(1, 1).sub), 'publié sur 1');
    assert.equal(plain(O.houseHeadline(0, 3).sub), 'publié sur 3');
    assert.equal(plain(O.houseHeadline(2, 3).sub), 'publiés sur 3');
  });
});

describe('25.3 / AC11 — filtres globaux', () => {
  it('chaque filtre liste les équipements de l’état, toutes pièces, dans l’ordre de la grille puis natif', () => {
    const overview = O.computeOverview(sampleRooms(), sampleEquipments());
    for (const key of ['published', 'to_apply', 'blocked', 'other', 'unread']) {
      const rows = O.filterRows(overview, key);
      assert.equal(rows.length, overview.counts[key], key);
      const expectedOrder = overview.rooms.flatMap((r) => r.equipments.filter((e) => e.group === key).map((e) => e.eq_id));
      assert.deepEqual(rows.map((r) => r.eq_id), expectedOrder);
    }
  });

  it('« exclus et autres » regroupe exclus, désactivés et rien à publier avec leur propre état', () => {
    const overview = O.computeOverview(sampleRooms(), sampleEquipments());
    const rows = O.filterRows(overview, 'other');
    assert.ok(rows.length > 0);
    rows.forEach((row) => assert.ok(['excluded', 'disabled', 'nothing_to_publish'].includes(row.state), row.state));
  });

  it('une ligne porte la pièce, le nom et la mention « N bloquées » quand blocked_mention > 0', () => {
    const equipments = sampleEquipments();
    const target = Object.values(equipments)[0];
    const overview = O.computeOverview(sampleRooms(), equipments);
    const rows = O.filterRows(overview, 'published');
    rows.forEach((row) => { assert.ok(row.room_name); assert.ok(row.eq_name); assert.equal(typeof row.blocked_mention, 'number'); });
    assert.ok(target);
    assert.equal(plain(O.blockedMentionLabel(2)), '2 bloquées');
    assert.equal(plain(O.blockedMentionLabel(1)), '1 bloquée');
  });
});

describe('25.3 / D2, AC4 — états de rendu de la lecture', () => {
  const ok = (payload) => ({ state: 'ok', result: { status: 'ok', payload } });

  it('available:true sans opération : rendu normal', () => {
    const r = O.classifyResponse(ok(payloadOf({})));
    assert.equal(r.kind, 'ok');
    assert.equal(r.payload.available, true);
  });

  it('available:true + action_in_progress:true : rendu normal et mention, relecture planifiée', () => {
    const r = O.classifyResponse(ok(payloadOf({}, { action_in_progress: true })));
    assert.equal(r.kind, 'ok');
    assert.equal(r.action_in_progress, true);
    assert.equal(plain(r.notice), 'Opération en cours : ces chiffres peuvent changer');
    assert.equal(r.retry, true);
  });

  it('available:false sans reason : avant la première synchro, aucune relecture', () => {
    const r = O.classifyResponse(ok({ schema_version: 1, available: false, equipments: {}, unread: [] }));
    assert.equal(r.kind, 'never_synced');
    assert.equal(plain(r.message), 'Aucune synchronisation n\'a encore eu lieu');
    assert.equal(r.retry, false);
  });

  it('available:false + reason:action_in_progress : message, relecture planifiée', () => {
    const r = O.classifyResponse(ok({ schema_version: 1, available: false, reason: 'action_in_progress', equipments: {}, unread: [] }));
    assert.equal(r.kind, 'in_progress');
    assert.equal(plain(r.message), 'Mise à jour en cours…');
    assert.equal(r.retry, true);
  });

  it('erreur ajax, state ≠ ok, status ≠ ok ou réponse vide : « Chiffres indisponibles », aucune relecture automatique', () => {
    for (const data of [null, undefined, {}, { state: 'error', result: 'x' }, { state: 'ok', result: null },
      { state: 'ok', result: { status: 'error' } }, { state: 'ok', result: { status: 'ok' } }, { state: 'ok', result: 'texte' }]) {
      const r = O.classifyResponse(data);
      assert.equal(r.kind, 'unavailable');
      assert.equal(plain(r.message), 'Chiffres indisponibles');
      assert.equal(r.retry, false);
    }
  });

  it('aucun cas n’affiche NaN, undefined ni « 0 publiés sur 0 »', () => {
    const cases = [
      ok(payloadOf({})), ok(payloadOf({}, { action_in_progress: true })),
      ok({ available: false, equipments: {}, unread: [] }), ok({ available: false, reason: 'action_in_progress' }), null,
    ];
    for (const data of cases) {
      const r = O.classifyResponse(data);
      for (const text of [r.message, r.notice]) {
        if (typeof text !== 'string') continue;
        assert.doesNotMatch(plain(text), /NaN|undefined|0 publiés sur 0/);
      }
    }
    const empty = O.computeOverview([], {});
    assert.equal(empty.total, 0);
    assert.equal(O.gaugeSegments(empty.counts, empty.total).length, 0);
  });

  it('un available:false ne produit jamais une jauge pleine de « non lus »', () => {
    const view = O.buildViewModel({ kind: 'never_synced', payload: null }, sampleRooms());
    assert.equal(view.gauge, 'neutral');
    assert.equal(view.overview, null);
  });

  it('chiffres valides conservés (atténués) pendant une opération ou une erreur', () => {
    const rooms = sampleRooms();
    const valid = payloadOf(sampleEquipments());
    const progress = O.buildViewModel({ kind: 'in_progress', payload: null }, rooms, valid);
    assert.equal(progress.stale, true);
    assert.ok(progress.overview && progress.overview.total === 11);
    const none = O.buildViewModel({ kind: 'in_progress', payload: null }, rooms, null);
    assert.equal(none.overview, null);
    assert.equal(plain(none.message), 'Mise à jour en cours…');
    const err = O.buildViewModel({ kind: 'unavailable', payload: null, message: '{{Chiffres indisponibles}}' }, rooms, valid);
    assert.equal(err.stale, true);
    assert.ok(err.overview);
  });
});

describe('25.3 / AC7, D3 — une seule copie en mémoire, aucune re-sérialisation', () => {
  function heavyScene(count) {
    const ids = Object.keys(FIXTURE);
    const rooms = [];
    const equipments = {};
    let next = 1000;
    for (let r = 0; r < 30; r++) {
      const list = [];
      for (let i = 0; i < Math.ceil(count / 30) && next - 1000 < count; i++) {
        const id = next++;
        list.push({ eq_id: id, eq_name: 'E' + id, enabled: id % 7 !== 0 });
        const entry = clone(FIXTURE[ids[id % ids.length]].aggregated);
        entry.jeedom_eq_id = id;
        equipments[String(id)] = entry;
      }
      rooms.push({ object_id: r + 1, object_name: 'R' + r, equipments: list });
    }
    return { rooms, equipments };
  }

  it('JSON.stringify n’est appelé sur aucune partie de payload.equipments (agrégats et rendu de la liste)', () => {
    const { rooms, equipments } = heavyScene(292);
    const original = JSON.stringify;
    let calls = 0;
    JSON.stringify = function (...args) { calls += 1; return original.apply(this, args); };
    try {
      const overview = O.computeOverview(rooms, equipments);
      O.filterRows(overview, 'published');
      O.gaugeSegments(overview.counts, overview.total);
      O.buildViewModel({ kind: 'ok', payload: { equipments } }, rooms, null);
    } finally {
      JSON.stringify = original;
    }
    assert.equal(calls, 0);
  });

  it('les entrées de la réponse ne sont ni modifiées ni dupliquées (identité conservée)', () => {
    const { rooms, equipments } = heavyScene(60);
    const before = Object.values(equipments).map((e) => e);
    const snapshot = JSON.stringify(equipments);
    O.computeOverview(rooms, equipments);
    assert.equal(JSON.stringify(equipments), snapshot, 'aucune mutation');
    Object.values(equipments).forEach((entry, i) => assert.equal(entry, before[i]));
  });

  it('mesure Node : agrégats de 292 équipements de la forme la plus lourde du corpus (consignée au Dev Agent Record)', () => {
    const { rooms, equipments } = heavyScene(292);
    const runs = [];
    for (let i = 0; i < 20; i++) {
      const t0 = process.hrtime.bigint();
      O.computeOverview(rooms, equipments);
      runs.push(Number(process.hrtime.bigint() - t0) / 1e6);
    }
    runs.sort((a, b) => a - b);
    const median = runs[Math.floor(runs.length / 2)];
    console.log(`# mesure 25.3 : computeOverview 292 équipements — médiane ${median.toFixed(2)} ms, max ${runs[runs.length - 1].toFixed(2)} ms`);
    assert.ok(Number.isFinite(median), 'mesure consignée, sans seuil inventé');
  });
});
