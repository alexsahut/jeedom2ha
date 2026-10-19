// ARTEFACT — Story 25.4 (AC27 à AC29) : le gate 20-0 est ADAPTÉ à la vue C, jamais affaibli. Registre d'assertions capturé
// sur main avant la story (`story_25_4_gate_assertions.json`) : une étiquette d'erreur, une clé `record`, une étape ou
// une écriture déclarée qui DISPARAÎT d'un parcours adapté fait échouer ce test (ajouter est permis, retirer non).
// `lib/policy.mjs` inchangé ; le nouveau parcours `vue-maitre-detail-c` est valide et en lecture seule. Aucune box (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const test = require('node:test');
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const { registryOf, PARCOURS } = require('./helpers/capture_story_25_4_references');

const root = path.join(__dirname, '..', '..');
const gateDir = path.join(root, 'tests', 'e2e', 'gate');
const gate = (...parts) => pathToFileURL(path.join(gateDir, ...parts)).href;
const registry = JSON.parse(fs.readFileSync(path.join(root, 'tests/fixtures/story_25_4_gate_assertions.json'), 'utf8'));

function diffAgainstMain(file) {
  for (const base of ['main', 'origin/main']) {
    try {
      return execFileSync('git', ['diff', '-U0', base, '--', file], { encoding: 'utf8', cwd: root });
    } catch { /* base suivante */ }
  }
  return null;
}

test('25.4 gate — le registre couvre les cinq parcours qui touchent la fenêtre de pièce', () => {
  assert.deepEqual(Object.keys(registry.parcours), PARCOURS);
  for (const name of PARCOURS) {
    const entry = registry.parcours[name];
    assert.ok(entry.errors.length > 0 && entry.steps.length > 0, name);
  }
});

for (const name of PARCOURS) {
  test(`25.4 gate — ${name} : aucune étiquette d’erreur, clé record, étape ni écriture déclarée n’a disparu`, () => {
    const source = fs.readFileSync(path.join(gateDir, 'parcours', name + '.mjs'), 'utf8');
    const now = registryOf(source);
    const ref = registry.parcours[name];
    assert.deepEqual(ref.errors.filter((label) => !now.errors.includes(label)), [], 'étiquettes d’erreur retirées');
    assert.deepEqual(ref.records.filter((key) => !now.records.includes(key)), [], 'clés record retirées');
    assert.deepEqual(ref.steps.filter((step) => !now.steps.includes(step)), [], 'étapes retirées');
    for (const [key, value] of Object.entries(ref.declared)) {
      assert.equal(now.declared[key], value, 'déclaration modifiée : ' + key);
    }
  });
}

test('25.4 gate — vrais clics Playwright : plus aucun dispatchEvent(click) dans les parcours adaptés ni dans le nouveau', () => {
  for (const name of [...PARCOURS, 'vue-maitre-detail-c']) {
    const source = fs.readFileSync(path.join(gateDir, 'parcours', name + '.mjs'), 'utf8');
    assert.doesNotMatch(source, /dispatchEvent\(\s*['"]click['"]/, name);
    assert.doesNotMatch(source, /modal-j2ha-room|j2ha-eq-toggle|panel-collapse|bootbox-close-button/, name + ' : plus de fenêtre de pièce');
  }
});

test('25.4 gate — la politique et le lanceur ne changent pas (diff vide) ; aucune action n’est ajoutée', async () => {
  for (const file of ['tests/e2e/gate/lib/policy.mjs', 'tests/e2e/gate/run-gate.mjs', 'tests/e2e/gate/lib/interceptor.mjs', 'tests/e2e/gate/lib/simulate.mjs']) {
    const diff = diffAgainstMain(file);
    if (diff !== null) assert.equal(diff, '', file + ' inchangé');
  }
  const policy = await import(gate('lib', 'policy.mjs'));
  const plugin = policy.ALLOWED_READS.find((entry) => entry.pathname === '/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php');
  assert.deepEqual(plugin.actions, ['getMqttConfig', 'getBridgeStatus', 'getMappingOverrides', 'getEquipmentStates', 'previewMappingOverride']);
});

test('25.4 gate — le parcours vue-maitre-detail-c est valide, en lecture seule, et porte les assertions (1) à (4) et (6) à (9)', async () => {
  const { loadParcours, isValidParcours } = await import(gate('run-gate.mjs'));
  const parcours = await loadParcours(path.join(gateDir, 'parcours', 'vue-maitre-detail-c.mjs'));
  assert.equal(isValidParcours(parcours), true);
  assert.equal(parcours.name, 'vue-maitre-detail-c');
  assert.deepEqual(parcours.declaredEquipments, {});
  assert.deepEqual(parcours.declaredBascules, []);
  assert.equal(parcours.declaredRescan, false);
  const source = fs.readFileSync(path.join(gateDir, 'parcours', 'vue-maitre-detail-c.mjs'), 'utf8');
  for (const label of [
    'lecture-a-l-ouverture', 'arbre-pieces-differentes-de-la-page', 'reperes-arbre-differents-de-la-page',
    'requete-pendant-filtre', 'lignes-filtre-differentes-du-nombre', 'selection-lecture-arbre-inattendue', 'pastille-arbre-differente-du-badge',
    'lien-profond-selection-perdue', 'lien-profond-lectures', 'disposition-inattendue', 'defilement-horizontal-detail',
    'tiroir-pieces-inoperant', 'requete-pendant-changement-de-disposition', 'precedent-ne-remonte-pas', 'ecriture-emise-par-le-menu-de-piece',
  ]) {
    assert.ok(source.includes(`'${label}'`), label);
  }
  assert.match(source, /window\.innerWidth|innerWidth/, 'la largeur de fenêtre est enregistrée');
  assert.match(source, /WRITE_ACTIONS/);
  assert.doesNotMatch(source, /hasText: \/\^Supprimer\$\/|btn-primary/);
  assert.match(source, /Annuler/);
});

test('25.4 gate — le relevé de chargement garde le chargement par défaut inchangé et ajoute une variante « lien profond » en lecture seule', () => {
  const file = path.join(gateDir, 'page-load-request-inventory.mjs');
  const source = fs.readFileSync(file, 'utf8');
  assert.match(source, /stateReads !== 1 \|\| perEquipmentReads !== 0/);
  assert.match(source, /lien-profond|j2ha-vue=/);
  const diff = diffAgainstMain('tests/e2e/gate/page-load-request-inventory.mjs');
  if (diff !== null) {
    const removed = diff.split('\n').filter((l) => l.startsWith('-') && !l.startsWith('---'));
    assert.deepEqual(removed, [], 'le relevé n’est qu’étendu');
  }
  const reads = source.match(/actions: \[([\s\S]*?)\]/)[1].match(/'[A-Za-z]+'/g).map((s) => s.slice(1, -1));
  assert.deepEqual(reads, ['getMqttConfig', 'getBridgeStatus', 'getMappingOverrides', 'getEquipmentStates', 'previewMappingOverride']);
});
