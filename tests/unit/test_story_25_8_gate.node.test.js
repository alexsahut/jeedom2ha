// ARTEFACT — Story 25.8 (AC14, AC15) : le parcours `exclusion-piece-simulee` passe en vrai Chromium sur la page livrée, avec la VRAIE
// politique du gate (policy.mjs) et la VRAIE simulation (simulate.mjs) appliquées à `saveRoomExclusion` et `scanTopology` déclarées ;
// il enregistre un nombre entier d'entités annoncées ; chaque étiquette d'erreur est portée par un contrôle négatif ; le contrôle
// `controle-exclusion-piece-non-declaree` provoque une écriture sur une autre pièce, que la politique bloque. Aucune box (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView, gate } = require('./helpers/workview_browser');

const root = path.join(__dirname, '..', '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const source = read('tests/e2e/gate/parcours/exclusion-piece-simulee.mjs');
const WRITES = ['saveRoomExclusion', 'scanTopology', 'executeHaAction', 'savePublicationOverride', 'saveMappingOverride', 'revertMappingOverride', 'revertPublicationOverride', 'saveFilteringConfig', 'exportDiagnostic'];

test('25.8 gate — étiquettes d\'erreur distinctes et clés record présentes, pièce et relecture déclarées', () => {
  for (const label of ['menu-carte-ouvre-la-piece', 'confirmation-sans-nombre', 'ecriture-apres-annulation', 'sequence-exclusion-inattendue',
    'carte-non-marquee-exclue', 'detail-piece-exclusion-absente', 'sans-piece-excluable', 'exclusion-non-declaree-transmise']) {
    assert.ok(source.includes(`'${label}'`), label);
  }
  assert.ok(source.includes("'entites_annoncees'"));
  assert.match(source, /export const declaredRescan = true;/);
  assert.match(source, /export const declaredRoomExclusions = \{ '\d+': \{ excluded: '1' \} \};/);
  assert.match(source, /export const declaredEquipments = \{\};/);
  for (const step of [1, 2, 3, 4, 5, 6, 7, 8]) assert.match(source, new RegExp(`atStep\\(helpers, ${step},`), 'étape ' + step);
});

test('25.8 gate — les deux parcours sont acceptés par le lanceur (aucun motif interdit) et valides', async () => {
  const { loadParcours, isValidParcours } = await import(gate('run-gate.mjs'));
  for (const file of ['exclusion-piece-simulee.mjs', 'controle-exclusion-piece-non-declaree.mjs']) {
    const parcours = await loadParcours(path.join(root, 'tests/e2e/gate/parcours', file));
    assert.equal(isValidParcours(parcours), true, file);
    assert.deepEqual(Object.keys(parcours.declaredRoomExclusions), ['4'], file);
  }
});

test('25.8 gate — le lanceur transmet declaredRoomExclusions (défaut {}) et amorce la liste simulée depuis la configuration lue', () => {
  const runner = read('tests/e2e/gate/run-gate.mjs');
  assert.match(runner, /declaredRoomExclusions: parcours\.declaredRoomExclusions \|\| \{\},/);
  assert.match(runner, /setRoomExclusionBase\(simState, probeBefore\.configValues\.excludedObjects\);/);
});

test('25.8 gate — l\'intercepteur traite saveRoomExclusion par une branche EXPLICITE, jamais par la branche else des retours de réglage', () => {
  const interceptor = read('tests/e2e/gate/lib/interceptor.mjs');
  const explicit = interceptor.indexOf("decision.action === 'saveRoomExclusion'");
  const fallback = interceptor.indexOf('} else {\n          const revert = recordRevert(simState');
  assert.ok(explicit > 0 && fallback > explicit, 'branche explicite avant le repli');
  assert.match(interceptor, /buildRoomExclusionResponse\(simState, \{ objectId: params\.objectId, excluded: params\.excluded \}\)/);
});

test('25.8 gate — l\'auto-test de l\'intercepteur couvre la nouvelle branche (déclarée simulée, non déclarée bloquée)', () => {
  const selftest = read('tests/e2e/gate/interceptor-selftest.mjs');
  assert.match(selftest, /'saveRoomExclusion'/);
  assert.match(selftest, /exclusion de pièce déclarée : réponse simulée/);
  assert.match(selftest, /exclusion de pièce non déclarée/);
});

async function makeGate(parcoursFile, baseExcluded) {
  const { classifyRequest } = await import(gate('lib', 'policy.mjs'));
  const simulate = await import(gate('lib', 'simulate.mjs'));
  const parcours = await import(gate('parcours', parcoursFile));
  const state = simulate.createState();
  simulate.setRoomExclusionBase(state, baseExcluded === undefined ? '' : baseExcluded);
  const ctx = {
    origin: 'http://gate.test', loginAttempts: 0, declaredEquipments: parcours.declaredEquipments, declaredPublicationOverrides: {},
    declaredRoomExclusions: parcours.declaredRoomExclusions || {}, declaredRescan: parcours.declaredRescan === true, lastPreviewType: state.lastPreviewType,
  };
  return {
    parcours,
    isWrite: (action) => WRITES.includes(action),
    handleWrite(action, request) {
      const decision = classifyRequest(request, ctx);
      if (decision.verdict !== 'simulate') return { verdict: decision.verdict };
      if (decision.action === 'scanTopology') {
        return { verdict: 'simulee', body: { state: 'ok', result: { status: 'ok', operation_result: 'succes', operation_message: 'Synchronisation terminée.', payload: { mapping_summary: { equipments_published: 0 } } } } };
      }
      return { verdict: 'simulee', body: simulate.buildRoomExclusionResponse(state, decision.params) };
    },
  };
}

async function runParcours(page, ctx, parcours) {
  const { normalizeParcoursRecord } = await import(gate('lib', 'report.mjs'));
  const recorded = {};
  const helpers = {
    record: (key, value) => { const [k, v] = normalizeParcoursRecord(key, value); recorded[k] = v; },
    journalEntries: () => ctx.journal,
  };
  await parcours.run(page, { helpers });
  return recorded;
}

test('25.8 gate réel — le parcours passe : nombre entier annoncé, séquence exacte, carte « Pièce exclue », aucune écriture non simulée', async (t) => {
  const g = await makeGate('exclusion-piece-simulee.mjs');
  await withRealView(t, { gate: g }, async (page, ctx) => {
    const recorded = await runParcours(page, ctx, g.parcours);
    assert.ok(Number.isInteger(recorded.entites_annoncees) && recorded.entites_annoncees >= 0, 'entités annoncées : ' + recorded.entites_annoncees);
    assert.equal(recorded.etape_8, 'exclusion-non-declaree-transmise');
    const writes = ctx.journal.filter((entry) => WRITES.includes(entry.action)).map((entry) => `${entry.action}:${entry.verdict}`);
    assert.deepEqual(writes, ['saveRoomExclusion:simulee', 'scanTopology:simulee'], 'une seule exclusion, une seule relecture, toutes deux simulées');
    assert.deepEqual(ctx.errors, []);
    // Séquence demandée : écriture, relecture, puis une lecture des états sans refresh.
    const actions = ctx.journal.map((entry) => entry.action);
    const save = actions.indexOf('saveRoomExclusion');
    const scan = actions.indexOf('scanTopology');
    const after = actions.slice(scan).filter((action) => action === 'getEquipmentStates');
    assert.ok(save >= 0 && scan > save);
    assert.equal(after.length, 1);
    assert.ok(ctx.bodies.every((body) => !/refresh=1/.test(body)), 'jamais refresh=1');
  });
});

test('25.8 gate réel — le nombre annoncé est celui de la fixture : somme des entités présentes des équipements de la pièce', async (t) => {
  const g = await makeGate('exclusion-piece-simulee.mjs');
  await withRealView(t, { gate: g }, async (page, ctx) => {
    const expected = Object.values(ctx.equipments).filter((entry) => ctx.rooms.find((r) => r.object_id === 4).equipments.some((eq) => eq.eq_id === entry.jeedom_eq_id))
      .reduce((sum, entry) => sum + entry.entities.filter((e) => e.present_in_ha === true).length, 0);
    const recorded = await runParcours(page, ctx, g.parcours);
    assert.equal(recorded.entites_annoncees, expected);
  });
});

/** Un défaut introduit dans la page livrée doit faire échouer l'étape qui le porte, avec SON étiquette. */
async function negative(t, label, patch, failing) {
  const g = await makeGate('exclusion-piece-simulee.mjs');
  await withRealView(t, { gate: g }, async (page, ctx) => {
    await page.evaluate(patch);
    await assert.rejects(() => runParcours(page, ctx, g.parcours), failing || new RegExp(label), label);
  });
}

test('25.8 gate réel — contrôle négatif : un menu de carte qui ouvre la pièce échoue (menu-carte-ouvre-la-piece)', async (t) => {
  await negative(t, 'menu-carte-ouvre-la-piece', () => {
    document.querySelector('#j2ha_roomCards .j2ha-room-card[data-object_id="4"] .j2ha-menu-toggle').addEventListener('click', () => window.j2haOpenRoom(4), true);
  });
});

test('25.8 gate réel — contrôle négatif : une confirmation sans nombre échoue (confirmation-sans-nombre)', async (t) => {
  await negative(t, 'confirmation-sans-nombre', () => {
    window.Jeedom2haOverviewPage.exclusionDialog = () => ({ title: 'Exclure ?', lines: ['Des entités seront retirées.'], confirmLabel: 'Exclure la pièce', danger: true });
  });
});

test('25.8 gate réel — contrôle négatif : une écriture à l\'annulation échoue (ecriture-apres-annulation)', async (t) => {
  await negative(t, 'ecriture-apres-annulation', () => {
    const real = window.bootbox.dialog;
    window.bootbox.dialog = (options) => {
      const cancel = options.buttons.cancel.callback;
      options.buttons.cancel.callback = () => { options.buttons.confirm.callback(); if (cancel) cancel(); };
      return real(options);
    };
  });
});

test('25.8 gate réel — contrôle négatif : une exclusion sans relecture échoue (sequence-exclusion-inattendue)', async (t) => {
  await negative(t, 'sequence-exclusion-inattendue', () => {
    window.triggerTopologyRescan = ($button, snapshot, owner) => { window.releaseTopologyRescanReservation($button, snapshot, owner); };
  });
});

test('25.8 gate réel — contrôle négatif : une carte jamais marquée échoue (carte-non-marquee-exclue)', async (t) => {
  // Le drapeau en mémoire n'est jamais remplacé par la réponse de la route : la carte garde son ratio.
  await negative(t, 'carte-non-marquee-exclue', () => {
    window.Jeedom2haOverviewPage.setExcludedObjects = () => {};
  });
});

test('25.8 gate réel — contrôle négatif : le détail sans encart « Pièce exclue » échoue (detail-piece-exclusion-absente)', async (t) => {
  await negative(t, 'detail-piece-exclusion-absente', () => {
    const surface = window.Jeedom2haSurface;
    surface.buildRoomExcludedNotice = () => null;
  });
});

test('25.8 gate réel — le contrôle négatif d\'une écriture sur une autre pièce est BLOQUÉ par la politique et consigné en échec', async (t) => {
  const g = await makeGate('controle-exclusion-piece-non-declaree.mjs');
  await withRealView(t, { gate: g }, async (page, ctx) => {
    const recorded = await runParcours(page, ctx, g.parcours);
    assert.equal(recorded.ecriture_non_declaree_provoquee, true);
    await page.waitForTimeout(300);
    const attempts = ctx.journal.filter((entry) => entry.action === 'saveRoomExclusion');
    assert.equal(attempts.length, 1);
    assert.equal(attempts[0].verdict, 'block-fail', 'bloquée par la politique, jamais servie');
  });
});
