// ARTEFACT — Story 25.3 (AC1, AC5, AC6, Q6, Q7, Q10) : un seul appel au chargement, jamais de boucle ;
// refresh=1 réservé à « Actualiser » ; relectures coalescées sur 500 ms ; 3 relectures bornées pendant une
// opération ; relecture au retour d'onglet (> 60 s). Planificateur factice, aucun réseau. Données fictives (CC-48).
'use strict';

const fs = require('node:fs');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const O = require('../../desktop/js/jeedom2ha_overview.js');

const okPayload = (extra) => ({ state: 'ok', result: { status: 'ok', payload: Object.assign({ schema_version: 1, available: true, meta: { action_in_progress: false }, equipments: {}, unread: [] }, extra || {}) } });
const busyPayload = () => okPayload({ meta: { action_in_progress: true } });
const neverSynced = () => ({ state: 'ok', result: { status: 'ok', payload: { schema_version: 1, available: false, equipments: {}, unread: [] } } });

function harness(options) {
  const opts = options || {};
  let time = 1_000_000;
  let nextId = 1;
  const timers = new Map();
  const calls = [];
  const updates = [];
  const reader = O.createReader({
    readStates(refresh, done) { calls.push({ refresh, done, settled: false }); },
    now: () => time,
    setTimeout(fn, ms) { const id = nextId++; timers.set(id, { fn, at: time + ms }); return id; },
    clearTimeout(id) { timers.delete(id); },
    onUpdate(state) { updates.push(state); },
  });
  const h = {
    reader, calls, updates, timers,
    advance(ms) {
      const until = time + ms;
      for (;;) {
        const due = [...timers.entries()].filter(([, t]) => t.at <= until).sort((a, b) => a[1].at - b[1].at)[0];
        if (!due) break;
        timers.delete(due[0]);
        time = Math.max(time, due[1].at);
        due[1].fn();
      }
      time = until;
    },
    answer(data) {
      const call = calls.find((c) => !c.settled);
      assert.ok(call, 'aucun appel en attente');
      call.settled = true;
      call.done(data);
      return call;
    },
    pending: () => calls.filter((c) => !c.settled).length,
  };
  if (opts.start !== false) { reader.load(); }
  return h;
}

describe('25.3 / AC1 — un seul appel au chargement', () => {
  it('l’initialisation émet exactement un appel, sans refresh', () => {
    const h = harness();
    assert.equal(h.calls.length, 1);
    assert.equal(h.calls[0].refresh, false);
    h.answer(okPayload());
    h.advance(60_000);
    assert.equal(h.calls.length, 1, 'aucun appel supplémentaire sans événement');
  });

  it('100 équipements, 3 pièces : toujours un appel (la lecture ne dépend pas de la taille)', () => {
    const rooms = [1, 2, 3].map((r) => ({ object_id: r, object_name: 'P' + r, equipments: Array.from({ length: 34 }, (_v, i) => ({ eq_id: r * 100 + i, eq_name: 'E', enabled: true })) }));
    const equipments = {};
    rooms.forEach((room) => room.equipments.forEach((e) => { equipments[String(e.eq_id)] = null; }));
    const h = harness();
    h.answer(okPayload({ equipments: {} }));
    O.computeOverview(rooms, {});
    assert.equal(h.calls.length, 1);
  });

  it('la source n’appelle getEquipmentStates qu’à un seul endroit, hors de toute boucle', () => {
    const files = fs.readdirSync('desktop/js').filter((f) => f.endsWith('.js'));
    const hits = [];
    for (const file of files) {
      fs.readFileSync('desktop/js/' + file, 'utf8').split('\n').forEach((line, i) => {
        if (/getEquipmentStates/.test(line) && !/^\s*(\/\/|\*|\/\*)/.test(line)) hits.push(`${file}:${i + 1}`);
      });
    }
    assert.equal(hits.length, 1, hits.join(', '));
    const php = fs.readFileSync('desktop/php/jeedom2ha.php', 'utf8');
    assert.ok(!/getEquipmentStates/.test(php.replace(/\/\/.*$/gm, '').replace(/\/\*[\s\S]*?\*\//g, '').replace(/<!--[\s\S]*?-->/g, '')));
    const source = fs.readFileSync('desktop/js/jeedom2ha_overview.js', 'utf8');
    const fetchFn = source.match(/function ajaxFetch[\s\S]*?\n  \}\n/)[0];
    assert.doesNotMatch(fetchFn, /\b(for|while|forEach|map)\b/);
  });

  it('aucun getMappingOverrides dans le module de la page principale', () => {
    assert.ok(!/getMappingOverrides/.test(fs.readFileSync('desktop/js/jeedom2ha_overview.js', 'utf8')));
  });
});

describe('25.3 / AC5 — refresh=1 réservé à « Actualiser »', () => {
  it('seul refresh() émet refresh=1 ; load, trigger, relectures planifiées et retour d’onglet n’en émettent pas', () => {
    const h = harness();
    h.answer(busyPayload());
    h.advance(2_000); h.answer(busyPayload());
    h.advance(5_000); h.answer(okPayload());
    h.reader.trigger(); h.advance(500); h.answer(okPayload());
    h.advance(61_000); h.reader.onVisible(); h.advance(500); h.answer(okPayload());
    assert.ok(h.calls.length >= 5);
    h.calls.forEach((c) => assert.equal(c.refresh, false));
    h.reader.refresh();
    assert.equal(h.calls[h.calls.length - 1].refresh, true);
    assert.equal(h.calls.filter((c) => c.refresh).length, 1);
  });

  it('pendant l’attente, « Actualiser » est désactivé : pas de double appel', () => {
    const h = harness();
    h.answer(okPayload());
    h.reader.refresh();
    assert.equal(h.reader.state().refreshing, true);
    h.reader.refresh();
    assert.equal(h.calls.filter((c) => c.refresh).length, 1);
    h.answer(okPayload());
    assert.equal(h.reader.state().refreshing, false);
    h.reader.refresh();
    assert.equal(h.calls.filter((c) => c.refresh).length, 2);
  });

  it('refresh=1 n’apparaît dans les sources qu’une fois, dans la fonction de lecture', () => {
    const hits = [];
    for (const file of fs.readdirSync('desktop/js').filter((f) => f.endsWith('.js'))) {
      fs.readFileSync('desktop/js/' + file, 'utf8').split('\n').forEach((line, i) => {
        if (/\brefresh\b['"]?\s*[:=]\s*'1'|refresh=1/.test(line) && !/^\s*(\/\/|\*|\/\*)/.test(line)) hits.push(`${file}:${i + 1}`);
      });
    }
    assert.equal(hits.length, 1, hits.join(', '));
  });
});

describe('25.3 / AC6, Q7 — événements, coalescence 500 ms', () => {
  it('un événement terminé → un appel, après 500 ms', () => {
    const h = harness();
    h.answer(okPayload());
    h.reader.trigger();
    assert.equal(h.calls.length, 1);
    h.advance(499);
    assert.equal(h.calls.length, 1);
    h.advance(1);
    assert.equal(h.calls.length, 2);
  });

  it('deux événements rapprochés se coalescent en un seul appel', () => {
    const h = harness();
    h.answer(okPayload());
    h.reader.trigger(); h.advance(200); h.reader.trigger(); h.advance(300);
    assert.equal(h.calls.length, 2);
    h.advance(1000);
    assert.equal(h.calls.length, 2);
  });

  it('un événement pendant une lecture en vol déclenche une seule relecture ensuite', () => {
    const h = harness();
    h.reader.trigger(); h.advance(500);
    assert.equal(h.calls.length, 1, 'la lecture initiale est encore en vol');
    h.answer(okPayload());
    h.advance(500);
    assert.equal(h.calls.length, 2);
    h.reader.trigger(); h.reader.trigger(); h.advance(500);
    assert.equal(h.pending(), 1);
  });

  it('aucune minuterie périodique (setInterval) dans les sources', () => {
    for (const file of fs.readdirSync('desktop/js').filter((f) => f.endsWith('.js'))) {
      assert.doesNotMatch(fs.readFileSync('desktop/js/' + file, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, ''), /setInterval/, file);
    }
  });
});

describe('25.3 / Q6 — relectures bornées pendant une opération', () => {
  it('au plus 3 relectures automatiques (2 s, 5 s, 10 s), puis le message reste', () => {
    const h = harness();
    h.answer(busyPayload());
    h.advance(1_999); assert.equal(h.calls.length, 1);
    h.advance(1); assert.equal(h.calls.length, 2); h.answer(busyPayload());
    h.advance(4_999); assert.equal(h.calls.length, 2);
    h.advance(1); assert.equal(h.calls.length, 3); h.answer(busyPayload());
    h.advance(9_999); assert.equal(h.calls.length, 3);
    h.advance(1); assert.equal(h.calls.length, 4); h.answer(busyPayload());
    h.advance(120_000);
    assert.equal(h.calls.length, 4, 'pas de quatrième relecture automatique');
    assert.equal(h.reader.state().kind, 'ok');
  });

  it('available:false + reason:action_in_progress est relu de la même façon', () => {
    const h = harness();
    h.answer({ state: 'ok', result: { status: 'ok', payload: { available: false, reason: 'action_in_progress', equipments: {}, unread: [] } } });
    h.advance(2_000);
    assert.equal(h.calls.length, 2);
  });

  it('une lecture normale annule la relecture planifiée', () => {
    const h = harness();
    h.answer(busyPayload());
    h.reader.trigger(); h.advance(500); h.answer(okPayload());
    h.advance(60_000);
    assert.equal(h.calls.length, 2);
  });

  it('une erreur ajax n’est pas relue automatiquement ; « Actualiser » reprend la main', () => {
    const h = harness();
    h.answer(null);
    h.advance(120_000);
    assert.equal(h.calls.length, 1);
    assert.equal(h.reader.state().kind, 'unavailable');
    h.reader.refresh();
    assert.equal(h.calls.length, 2);
  });

  it('avant la première synchro : aucune relecture automatique', () => {
    const h = harness();
    h.answer(neverSynced());
    h.advance(120_000);
    assert.equal(h.calls.length, 1);
    assert.equal(h.reader.state().kind, 'never_synced');
  });

  it('les derniers chiffres valides sont conservés quand une lecture suivante échoue', () => {
    const h = harness();
    h.answer(okPayload({ equipments: { 1: { x: 1 } } }));
    assert.ok(h.reader.state().valid);
    h.reader.trigger(); h.advance(500); h.answer(null);
    assert.equal(h.reader.state().kind, 'unavailable');
    assert.ok(h.reader.state().valid, 'copie unique de la dernière réponse valide');
  });
});

describe('25.3 / Q10 — relecture au retour sur l’onglet', () => {
  it('relit seulement si la dernière lecture date de plus de 60 s, sans refresh, coalescée', () => {
    const h = harness();
    h.answer(okPayload());
    h.advance(30_000); h.reader.onVisible(); h.advance(500);
    assert.equal(h.calls.length, 1, '30 s : pas de relecture');
    h.advance(31_000); h.reader.onVisible(); h.reader.onVisible();
    assert.equal(h.calls.length, 1, 'coalescence : rien avant 500 ms');
    h.advance(500);
    assert.equal(h.calls.length, 2);
    assert.equal(h.calls[1].refresh, false);
  });

  it('se coalesce avec un autre déclencheur de l’AC6', () => {
    const h = harness();
    h.answer(okPayload());
    h.advance(61_000);
    h.reader.trigger(); h.reader.onVisible(); h.advance(500);
    assert.equal(h.calls.length, 2);
  });

  it('la source écoute visibilitychange (pas de focus) et ne déclenche que sur « visible »', () => {
    const source = fs.readFileSync('desktop/js/jeedom2ha_overview.js', 'utf8');
    assert.match(source, /visibilitychange/);
    assert.match(source, /visibilityState === 'visible'/);
    assert.doesNotMatch(source, /addEventListener\('focus'|\.on\('focus'/);
  });

  it('retour d’onglet sans lecture réussie : relit (dernière lecture inconnue)', () => {
    const h = harness();
    h.answer(null);
    h.advance(5_000); h.reader.onVisible(); h.advance(500);
    assert.equal(h.calls.length, 2);
  });
});
