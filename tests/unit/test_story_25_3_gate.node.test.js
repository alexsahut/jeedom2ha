// ARTEFACT — Story 25.3 (AC17) : le gate 20-0 est ÉTENDU sans affaiblissement. Parcours `page-principale-b`
// accepté par le garde-fou du lanceur ; la politique d'interception ne change pas d'action autorisée ;
// les cinq parcours existants et le relevé de chargement ne perdent aucune assertion. Aucune box (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const test = require('node:test');
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');

const gateDir = path.join(__dirname, '..', 'e2e', 'gate');
const gate = (...parts) => pathToFileURL(path.join(gateDir, ...parts)).href;

function diffAgainstMain(file) {
  for (const base of ['main', 'origin/main']) {
    try {
      return execFileSync('git', ['diff', '-U0', base, '--', file], { encoding: 'utf8' });
    } catch { /* base suivante */ }
  }
  return null;
}
const removedLines = (diff) => diff.split('\n').filter((l) => l.startsWith('-') && !l.startsWith('---'));

test('25.3 gate — le parcours page-principale-b passe le garde-fou du lanceur et est valide', async () => {
  const { loadParcours, isValidParcours } = await import(gate('run-gate.mjs'));
  const parcours = await loadParcours(path.join(gateDir, 'parcours', 'page-principale-b.mjs'));
  assert.equal(isValidParcours(parcours), true);
  assert.equal(parcours.name, 'page-principale-b');
  assert.deepEqual(parcours.declaredEquipments, {});
  assert.deepEqual(parcours.declaredBascules, []);
  assert.equal(parcours.declaredRescan, false, 'lecture seule : aucune relecture de Jeedom déclarée');
});

test('25.3 gate — le parcours est en lecture seule : aucune confirmation d’action destructrice', () => {
  const source = fs.readFileSync(path.join(gateDir, 'parcours', 'page-principale-b.mjs'), 'utf8');
  assert.match(source, /Annuler/, 'la confirmation de suppression est annulée');
  assert.doesNotMatch(source, /hasText: \/\^Supprimer\$\/|btn-primary/);
  assert.match(source, /WRITE_ACTIONS/);
  assert.match(source, /ecriture-emise/);
});

test('25.3 gate — la politique ne change pas d’action autorisée : getEquipmentStates y est déjà, refresh=1 n’est pas distingué', async () => {
  const policy = await import(gate('lib', 'policy.mjs'));
  const plugin = policy.ALLOWED_READS.find((entry) => entry.pathname === '/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php');
  assert.deepEqual(plugin.actions, ['getMqttConfig', 'getBridgeStatus', 'getMappingOverrides', 'getEquipmentStates', 'previewMappingOverride']);
  const diff = diffAgainstMain('tests/e2e/gate/lib/policy.mjs');
  if (diff !== null) assert.equal(diff, '', 'policy.mjs inchangé');
  const base = { method: 'POST', resourceType: 'xhr', headers: { 'content-type': 'application/x-www-form-urlencoded' } };
  const url = 'https://domobox.famille-sahut.fr/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php';
  for (const postData of ['action=getEquipmentStates', 'action=getEquipmentStates&refresh=1']) {
    assert.equal(policy.classifyRequest({ ...base, url, postData }, {}).verdict, 'read', postData);
  }
});

test('25.3 gate — les parcours existants et la politique n’ont perdu aucune assertion', () => {
  const existing = ['controle-ecriture-non-declaree', 'decouverte-piece-25-eq-579', 'exclusion-publication-non-publiee', 'reference-bascule-eq-380', 'rescan-page-principale'];
  for (const name of existing) {
    const diff = diffAgainstMain(`tests/e2e/gate/parcours/${name}.mjs`);
    if (diff === null) continue;
    assert.deepEqual(removedLines(diff), [], `${name} : aucune ligne retirée ou modifiée`);
  }
  for (const file of ['tests/e2e/gate/run-gate.mjs', 'tests/e2e/gate/lib/policy.mjs', 'tests/e2e/gate/lib/interceptor.mjs', 'tests/e2e/gate/lib/simulate.mjs']) {
    const diff = diffAgainstMain(file);
    if (diff !== null) assert.equal(diff, '', file + ' inchangé');
  }
});

test('25.3 gate — le relevé de chargement attend une lecture d’état et aucune lecture par équipement', () => {
  const file = 'tests/e2e/gate/page-load-request-inventory.mjs';
  const source = fs.readFileSync(file, 'utf8');
  assert.match(source, /'getEquipmentStates',\s*\n\s*'previewMappingOverride'/);
  assert.match(source, /stateReads !== 1 \|\| perEquipmentReads !== 0/);
  const diff = diffAgainstMain(file);
  if (diff !== null) assert.deepEqual(removedLines(diff), [], 'le relevé n’est qu’étendu');
  // Les lectures autorisées restent exactement celles de la politique du gate.
  const reads = source.match(/actions: \[([\s\S]*?)\]/)[1].match(/'[A-Za-z]+'/g).map((s) => s.slice(1, -1));
  assert.deepEqual(reads, ['getMqttConfig', 'getBridgeStatus', 'getMappingOverrides', 'getEquipmentStates', 'previewMappingOverride']);
});

test('25.3 gate — l’inventaire des identifiants conservés par la page (sélecteurs des cinq parcours)', () => {
  const page = fs.readFileSync('desktop/php/jeedom2ha.php', 'utf8');
  for (const id of ['bt_rescanTopology', 'bt_exportDiagnostic', 'div_bridgeHealthBanner', 'span_healthBridge', 'span_healthMqtt', 'span_healthMqttBroker', 'span_healthSync', 'span_healthOp', 'span_healthOpMsg', 'j2ha_roomCards']) {
    assert.ok(page.includes(id) || fs.readFileSync('desktop/php/jeedom2ha_overview_helpers.php', 'utf8').includes(id), id);
  }
  for (const attr of ['data-ha-action="republier"', 'data-ha-action="rescan"', 'data-ha-action="supprimer-recreer"', 'data-action="gotoPluginConf"']) {
    assert.ok(page.includes(attr), attr);
  }
  const helpers = fs.readFileSync('desktop/php/jeedom2ha_overview_helpers.php', 'utf8');
  for (const needle of ['j2ha-room-card', 'data-object_id', 'objectDisplayCard']) assert.ok(helpers.includes(needle), needle);
});
