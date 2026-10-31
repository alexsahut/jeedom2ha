'use strict';

/* Scènes fictives de taille variable pour la vue C (Story 25.4) : N pièces, M équipements, états variés tirés du
 * corpus de 25.2 (`story_25_2_parite_etat.json`), générateur pseudo-aléatoire SEEDÉ (reproductible). Identifiants,
 * noms et couleurs fictifs (CC-48). Rend une scène au format de `render_page.php` ({objects, eqlogics}) et la copie
 * des états (`payload.equipments`, clés = String(eq_id)). */

const { FIXTURE, clone } = require('./page_b_harness');

/** Mulberry32 : petit générateur seedé. */
function prng(seed) {
  let a = seed >>> 0;
  return function next() {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const FIXTURE_IDS = Object.keys(FIXTURE);

/**
 * @param {object} options { rooms, equipments, seed, unread (nombre d'équipements absents de la copie), unassigned,
 *                           longNames (noms de pièce / d'équipement longs), grouped (pièces sous un parent) }
 */
function makeScene(options) {
  const opts = Object.assign({ rooms: 3, equipments: 40, seed: 1, unread: 0, unassigned: 0, longNames: false, grouped: false }, options || {});
  const random = prng(opts.seed);
  const objects = [];
  const eqlogics = {};
  const equipments = {};
  const enabledById = {};
  let nextEq = 1000;
  let remaining = opts.equipments - opts.unassigned;
  if (opts.grouped) objects.push({ id: 1, name: 'Parent fictif', father_id: null, display: {} });
  for (let r = 0; r < opts.rooms; r += 1) {
    const id = 10 + r;
    const roomsLeft = opts.rooms - r;
    const count = r === opts.rooms - 1 ? remaining : Math.max(1, Math.min(remaining - (roomsLeft - 1), Math.round(remaining / roomsLeft + (random() - 0.5) * 4)));
    remaining -= count;
    objects.push({
      id, name: opts.longNames ? `Pièce fictive numéro ${r} à nom particulièrement long` : `Pièce ${r}`,
      father_id: opts.grouped ? 1 : null, display: {},
    });
    eqlogics[String(id)] = [];
    for (let e = 0; e < count; e += 1) {
      const source = FIXTURE_IDS[Math.floor(random() * FIXTURE_IDS.length)];
      const eqId = nextEq;
      nextEq += 1;
      const enabled = FIXTURE[source].enabled !== false;
      eqlogics[String(id)].push({ id: eqId, name: opts.longNames ? `Équipement ${eqId} avec un nom de commande très long` : `Eq ${eqId}`, enabled });
      enabledById[eqId] = enabled;
      const entry = clone(FIXTURE[source].aggregated);
      entry.jeedom_eq_id = eqId;
      equipments[String(eqId)] = entry;
    }
  }
  if (opts.unassigned > 0) {
    eqlogics.null = [];
    for (let e = 0; e < opts.unassigned; e += 1) {
      const source = FIXTURE_IDS[Math.floor(random() * FIXTURE_IDS.length)];
      const eqId = nextEq;
      nextEq += 1;
      eqlogics.null.push({ id: eqId, name: `Eq ${eqId}`, enabled: true });
      const entry = clone(FIXTURE[source].aggregated);
      entry.jeedom_eq_id = eqId;
      equipments[String(eqId)] = entry;
    }
  }
  // « Non lus » : équipements de la liste Jeedom absents de la copie des états.
  const ids = Object.keys(equipments);
  for (let u = 0; u < opts.unread && ids.length > 0; u += 1) {
    const pick = ids.splice(Math.floor(random() * ids.length), 1)[0];
    delete equipments[pick];
  }
  return { scene: { objects, eqlogics, doc: 'https://doc.example.test/plugin' }, equipments };
}

module.exports = { makeScene, prng };
