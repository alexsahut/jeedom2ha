// ARTEFACT — Story 24.11 (AC2) : cadre du gate 20-0, cible déclarée à l'exécution. `helpers.declareTarget` est
// bornée (une fois, avant toute écriture interceptée, id numérique sans réglage dans le témoin « avant ») et la
// politique d'interception reste inchangée : elle n'admet en simulation que les écritures d'un équipement déclaré.
// Aucune box, aucun réseau (CC-48) : le témoin « avant » est un objet local.
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');

const gateDir = path.join(__dirname, '..', 'e2e', 'gate');
const gate = (...parts) => pathToFileURL(path.join(gateDir, ...parts)).href;
const ORIGIN = 'https://domobox.famille-sahut.fr';
const PLUGIN_AJAX = `${ORIGIN}/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php`;

function witness(json) {
  return { readable: true, overrides: json ? { present: true, json } : { present: false, json: null } };
}

const WITH_OVERRIDES = witness({
  schema_version: 2,
  overrides: { '12:34': { ha_entity_type: 'light' } },
  equipment_overrides: { '287': { publication_policy: 'exclude' } },
});

function setup({ before = WITH_OVERRIDES, entries = [], failed = false } = {}) {
  const ctx = {
    origin: ORIGIN,
    declaredEquipments: {},
    declaredPublicationOverrides: {},
    declaredRoomExclusions: {},
    declaredRescan: false,
  };
  const journal = { entries, failed, failures: [] };
  const records = [];
  const record = (key, value) => records.push([key, value]);
  return { ctx, journal, records, record, before };
}

function publicationWrite(eqId, policy = 'exclude') {
  const form = new URLSearchParams({ action: 'savePublicationOverride', eqId, publicationPolicy: policy }).toString();
  return { method: 'POST', url: PLUGIN_AJAX, resourceType: 'xhr', postData: form, headers: { 'content-type': 'application/x-www-form-urlencoded' } };
}

test('24.11 cadre — declareTarget accepte un id numérique sans réglage et ne déclare QUE lui, avec { commands: [] }', async () => {
  const { createDeclareTarget } = await import(gate('run-gate.mjs'));
  const s = setup();
  const declareTarget = createDeclareTarget(s);
  assert.equal(declareTarget('42'), '42');
  assert.deepEqual(s.ctx.declaredEquipments, { 42: { commands: [] } });
  assert.deepEqual(s.ctx.declaredPublicationOverrides, { 42: { commands: [] } });
  assert.deepEqual(s.ctx.declaredRoomExclusions, {});
  assert.equal(s.ctx.declaredRescan, false);
  assert.deepEqual(s.records, [['cible', '42']]);
});

test('24.11 cadre — declareTarget refuse un id portant un réglage (équipement ou commande) dans le témoin « avant »', async () => {
  const { createDeclareTarget } = await import(gate('run-gate.mjs'));
  for (const eqId of ['287', '12']) {
    const s = setup();
    assert.throws(() => createDeclareTarget(s)(eqId), /override-declare/);
    assert.deepEqual(s.ctx.declaredEquipments, {});
    assert.deepEqual(s.ctx.declaredPublicationOverrides, {});
    assert.deepEqual(s.records, []);
  }
});

test('24.11 cadre — declareTarget refuse un deuxième appel, y compris après un premier appel refusé', async () => {
  const { createDeclareTarget } = await import(gate('run-gate.mjs'));
  const s = setup();
  const declareTarget = createDeclareTarget(s);
  declareTarget('42');
  assert.throws(() => declareTarget('43'), /cible-deja-declaree/);
  assert.throws(() => declareTarget('42'), /cible-deja-declaree/);
  assert.deepEqual(Object.keys(s.ctx.declaredEquipments), ['42']);
  const refused = setup();
  const second = createDeclareTarget(refused);
  assert.throws(() => second('287'), /override-declare/);
  assert.throws(() => second('42'), /cible-deja-declaree/);
  assert.deepEqual(refused.ctx.declaredEquipments, {});
});

test('24.11 cadre — declareTarget refuse un appel après une écriture interceptée (simulée, refusée) ou un journal en échec', async () => {
  const { createDeclareTarget, hasInterceptedWrite } = await import(gate('run-gate.mjs'));
  const cases = [
    { entries: [{ action: 'savePublicationOverride', verdict: 'simulee' }] },
    { entries: [{ action: 'savePublicationOverride', verdict: 'block-fail' }] },
    { entries: [{ action: 'saveRoomExclusion', verdict: 'simulee' }] },
    { entries: [{ action: 'scanTopology', verdict: 'simulee' }] },
    { entries: [{ action: 'saveMappingOverride', verdict: 'block-fail' }] },
    { entries: [{ action: 'getMappingOverrides', verdict: 'read' }], failed: true },
  ];
  for (const options of cases) {
    const s = setup(options);
    assert.throws(() => createDeclareTarget(s)('42'), /cible-apres-ecriture/, JSON.stringify(options));
    assert.deepEqual(s.ctx.declaredEquipments, {});
    assert.deepEqual(s.ctx.declaredPublicationOverrides, {});
  }
  // Des lectures seules (arbre, états, long-polling) n'empêchent pas la déclaration.
  const reads = [
    { action: 'getMappingOverrides', verdict: 'read' }, { action: 'getEquipmentStates', verdict: 'read' },
    { action: 'changes', verdict: 'lecture-simulee' }, { action: null, verdict: 'document' },
  ];
  assert.equal(hasInterceptedWrite(reads), false);
  assert.equal(createDeclareTarget(setup({ entries: reads }))('42'), '42');
});

test('24.11 cadre — declareTarget refuse un id non numérique', async () => {
  const { createDeclareTarget } = await import(gate('run-gate.mjs'));
  for (const eqId of ['abc', '12a', '', ' 12', '0', '012', '-1', '1.5', '__proto__', 'constructor', null, undefined, 1.5, -3, {}, ['12']]) {
    const s = setup({ before: witness(null) });
    assert.throws(() => createDeclareTarget(s)(eqId), /cible-id-invalide/, String(eqId));
    assert.deepEqual(s.ctx.declaredEquipments, {});
    assert.deepEqual(s.records, []);
  }
  // Un entier sûr est accepté sous sa forme décimale.
  const s = setup({ before: witness(null) });
  assert.equal(createDeclareTarget(s)(42), '42');
});

test('24.11 cadre — la politique est inchangée : avant déclaration l’écriture est refusée, après seule la cible est simulée', async () => {
  const { createDeclareTarget } = await import(gate('run-gate.mjs'));
  const { classifyRequest } = await import(gate('lib', 'policy.mjs'));
  const s = setup();
  assert.equal(classifyRequest(publicationWrite('42'), s.ctx).verdict, 'block-fail');
  createDeclareTarget(s)('42');
  assert.equal(classifyRequest(publicationWrite('42'), s.ctx).verdict, 'simulate');
  assert.equal(classifyRequest(publicationWrite('43'), s.ctx).verdict, 'block-fail');
  assert.equal(classifyRequest(publicationWrite('287'), s.ctx).verdict, 'block-fail');
});

test('24.11 cadre — isValidParcours : `dynamicTarget` exige true ET des déclarations vides', async () => {
  const { isValidParcours } = await import(gate('run-gate.mjs'));
  const base = { name: 'x', declaredEquipments: {}, declaredPublicationOverrides: {}, declaredBascules: [], run: () => {} };
  assert.equal(isValidParcours({ ...base, dynamicTarget: true }), true);
  // `{}` déclaré pour une cible dynamique sans `dynamicTarget === true` : refusé.
  for (const dynamicTarget of [false, 'true', 1, null, {}]) {
    assert.equal(isValidParcours({ ...base, dynamicTarget }), false, String(dynamicTarget));
  }
  // Cible dynamique avec une déclaration statique : refusée (la seule cible possible est celle de declareTarget).
  assert.equal(isValidParcours({ ...base, dynamicTarget: true, declaredEquipments: { '1': { commands: [] } } }), false);
  assert.equal(isValidParcours({ ...base, dynamicTarget: true, declaredPublicationOverrides: { '1': { commands: [] } } }), false);
  assert.equal(isValidParcours({ ...base, dynamicTarget: true, declaredPublicationOverrides: undefined }), false);
  assert.equal(isValidParcours({ ...base, dynamicTarget: true, declaredEquipments: [] }), false);
  // Choix documenté dans la story : un parcours en lecture seule, sans `dynamicTarget`, garde `{}` (et ne reçoit
  // jamais `declareTarget`, donc ne peut rien écrire).
  const readOnly = { ...base };
  delete readOnly.declaredPublicationOverrides;
  assert.equal(isValidParcours(readOnly), true);
});

test('24.11 cadre — le parcours exclusion-publication-non-publiee se charge, est valide et à cible dynamique', async () => {
  const { loadParcours, isValidParcours } = await import(gate('run-gate.mjs'));
  const parcours = await loadParcours(path.join(gateDir, 'parcours', 'exclusion-publication-non-publiee.mjs'));
  assert.equal(isValidParcours(parcours), true);
  assert.equal(parcours.dynamicTarget, true);
  assert.deepEqual(parcours.declaredEquipments, {});
  assert.deepEqual(parcours.declaredPublicationOverrides, {});
  assert.deepEqual(parcours.declaredBascules, []);
  assert.deepEqual(parcours.EXCLUDED_TARGETS, ['287']);
  const source = fs.readFileSync(path.join(gateDir, 'parcours', 'exclusion-publication-non-publiee.mjs'), 'utf8');
  assert.match(source, /helpers\.declareTarget\(eqId\)/);
  assert.match(source, /'aucune-cible-eligible'/);
  // La déclaration précède le premier clic d'écriture (« Jamais »).
  assert.ok(source.indexOf('helpers.declareTarget(eqId)') < source.indexOf('excludeButton.click()'));
});

test('24.11 cadre — la cible apparaît dans le rapport : declareTarget reçoit le collecteur du rapport, et seul un parcours dynamique la reçoit', async () => {
  const { createDeclareTarget } = await import(gate('run-gate.mjs'));
  const { normalizeParcoursRecord } = await import(gate('lib', 'report.mjs'));
  // Le collecteur réel (createRecorder) passe par normalizeParcoursRecord puis écrit dans data.parcours, qui est
  // sérialisé tel quel dans gate-report.json (`parcours: data.parcours`).
  const report = {};
  const s = setup();
  s.record = (key, value) => { const [k, v] = normalizeParcoursRecord(key, value); report[k] = v; };
  createDeclareTarget(s)('42');
  assert.deepEqual(report, { cible: '42' });
  const source = fs.readFileSync(path.join(gateDir, 'run-gate.mjs'), 'utf8');
  assert.match(source, /const record = createRecorder\(data\.parcours\);/);
  assert.match(source, /declareTarget: createDeclareTarget\(\{ before, ctx, journal, record \}\)/);
  assert.match(source, /parcours: data\.parcours,/);
  assert.match(source, /if \(parcours\.dynamicTarget === true\) \{\n\s+ctx\.declaredEquipments = \{\};\n\s+ctx\.declaredPublicationOverrides = \{\};/);
  // La déclaration statique reste contrôlée contre le témoin « avant », comme avant la story.
  assert.match(source, /assertNoOverrideOn\(before, Object\.keys\(parcours\.declaredEquipments\)\);/);
});

test('24.11 revue Codex P2 — isDeclarableTarget dit, sans rien consommer, si declareTarget accepterait l’id', async () => {
  const { createDeclareTarget, isDeclarableTarget } = await import(gate('run-gate.mjs'));
  const s = setup();
  // Réglage de commande seul (type HA forcé, '12:34') et réglage d'équipement (287) : refusés.
  assert.equal(isDeclarableTarget(s.before, '12'), false);
  assert.equal(isDeclarableTarget(s.before, '287'), false);
  assert.equal(isDeclarableTarget(s.before, 'abc'), false);
  assert.equal(isDeclarableTarget(s.before, '42'), true);
  assert.equal(isDeclarableTarget(s.before, 42), true);
  // La vérification ne consomme pas la déclaration unique.
  assert.equal(createDeclareTarget(s)('42'), '42');
  assert.deepEqual(s.records, [['cible', '42']]);
});
