// Front v3 — Lot 7 (revue Codex #406) : « Annuler » après « Enregistrer et publier quand même » (ou « Publier en <type> »)
// rétablit EXACTEMENT l'état d'avant. Entité à plusieurs commandes dont une commande sœur porte déjà une correction de type :
// l'annulation ne touche QUE la commande du panneau (réglage de publication retiré seul, `scope: 'command'`, ou réécrit tel
// qu'il était), jamais le retour canonique qui purgeait toute l'entité. VRAI code de la surface sur le faux DOM. Données
// fictives (CC-48). Le pendant côté démon (état des fichiers identique) : test_front_v3_lot7_annuler_preserve.py.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { createUi, BRIDGE_UP } = require('./helpers/ui_harness');
const { ACTION_OK } = require('./helpers/write_scenarios');
const { DEMO, demoRoom, diag } = require('./helpers/front_v2_demo_trees');

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const plain = (text) => String(text).replace(/\{\{|\}\}/g, '').replace(/\s+/g, ' ').trim();
const WRITES = ['saveMappingOverride', 'revertMappingOverride', 'savePublicationOverride', 'revertPublicationOverride'];

/** Lampe typée « prise » (entité unique 2311/2312/2313) ; la commande sœur 2312 porte déjà une correction de type. */
function lampeAvecSoeur(ownPublication) {
  const t = DEMO.lampePrise(true);
  const d = () => diag('ambiguous_skipped', { code: 'name_heuristic_rejection', type: 'switch', valid: true });
  t.commands.forEach((c) => { c.diagnostic = d(); c.override_types_allowed = ['light', 'switch']; });
  t.entities[0].decision = d();
  t.equipment_decision = d();
  const sister = t.commands.find((c) => c.jeedom_cmd_id === 2312);
  sister.override_applied = true;
  sister.override_source = 'user';
  sister.effective_ha = 'switch';
  if (ownPublication) t.commands.find((c) => c.jeedom_cmd_id === 2311).publication_override_own = ownPublication;
  return t;
}

/** « Publier quand même » depuis le panneau (type « lumière » + « Toujours »), enregistrement, puis clic sur « Annuler ». */
async function publishAnywayThenUndo(tree) {
  const ui = createUi([demoRoom()], { pluginNames: { virtual: 'Virtuel' } });
  ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
  ui.openRoomWith(9, [{ state: 'ok', result: { payload: tree } }]);
  const P = '.j2ha-eq-panel[data-eq-id="231"] ';
  const panel = '.j2ha-v3-type-modal[data-eq-id="231"][data-type-panel-for="2311"] ';
  ui.click(P + 'tr[data-cmd-id="2311"] .j2ha-type-link');
  ui.$(`${panel}input[data-type="light"]`).prop('checked', true).trigger('change');
  await sleep(450);
  ui.pending('previewMappingOverride')[0].respond({ state: 'ok', result: { status: 'ok', payload: {
    jeedom_eq_id: 231, mapped: true, covered: true, auto: tree.equipment_decision,
    overridden: diag('ambiguous_skipped', { code: 'name_heuristic_rejection', type: 'light', valid: true }) } } });
  ui.click(panel + '.j2ha-v2-type-anyway');
  ui.pending('previewMappingOverride').slice(-1)[0].respond({ state: 'ok', result: { status: 'ok', payload: {
    jeedom_eq_id: 231, mapped: true, covered: true, auto: tree.equipment_decision,
    overridden: diag('publication_forced', { type: 'light', valid: true, publish: true, code: 'name_heuristic_rejection' }),
    entities_before: [{ ha_entity_type: 'switch', ha_default_entity_id: 'switch.jeedom2ha_eq_231', will_publish: false }],
    entities_after: [{ ha_entity_type: 'light', ha_default_entity_id: 'light.jeedom2ha_eq_231', will_publish: true }] } } });
  assert.equal(plain(ui.$(panel + '.j2ha-v2-type-save').text()), 'Enregistrer et publier quand même');
  ui.click(panel + '.j2ha-v2-type-save');
  const saved = [ui.respond('saveMappingOverride', { state: 'ok', result: { status: 'ok' } }).data,
    ui.respond('savePublicationOverride', { state: 'ok', result: { status: 'ok' } }).data];
  ui.respond('executeHaAction', ACTION_OK);
  const before = ui.calls.filter((c) => WRITES.includes(c.action)).length;
  ui.click(P + '.j2ha-v2-type-undo');
  return { ui, P, saved, before };
}

describe('Lot 7 — « Annuler » après « Publier quand même » préserve la correction de type sœur', () => {
  it('sans réglage de publication avant : retrait limité à la commande (scope command), puis type précédent ; sœur intacte', async () => {
    const { ui, P, saved, before } = await publishAnywayThenUndo(lampeAvecSoeur(null));
    assert.deepEqual(saved.map((d) => ({ ...d })), [
      { action: 'saveMappingOverride', eqId: 231, cmdId: 2311, haEntityType: 'light' },
      { action: 'savePublicationOverride', eqId: 231, publicationPolicy: 'force_publish', cmdId: 2311 },
    ], 'corps de l’enregistrement inchangés');
    const r1 = ui.respond('revertPublicationOverride', { state: 'ok', result: { status: 'ok' } });
    assert.deepEqual({ ...r1.data }, { action: 'revertPublicationOverride', eqId: 231, cmdId: 2311, scope: 'command' },
      'jamais le retour canonique (sans scope) qui purge toutes les commandes de l’entité');
    const r2 = ui.respond('revertMappingOverride', { state: 'ok', result: { status: 'ok' } });
    assert.deepEqual({ ...r2.data }, { action: 'revertMappingOverride', eqId: 231, cmdId: 2311 });
    ui.respond('executeHaAction', ACTION_OK);
    const undoWrites = ui.calls.filter((c) => WRITES.includes(c.action)).slice(before);
    assert.equal(undoWrites.length, 2, 'deux écritures seulement');
    assert.ok(undoWrites.every((c) => c.data.cmdId === 2311), 'aucune écriture sur la commande sœur 2312 ni sur l’équipement');
    assert.ok(!undoWrites.some((c) => c.action === 'revertPublicationOverride' && c.data.scope !== 'command'));
    assert.match(plain(ui.$(P + '.j2ha-v2-type-toast').text()), /Réglage précédent rétabli\./);
    ui.win.Jeedom2haSurface.clearEquipment();
  });

  it('« Jamais » déjà posé sur la commande : réécrit tel quel (pas retiré), puis type précédent', async () => {
    const { ui, before } = await publishAnywayThenUndo(lampeAvecSoeur('exclude'));
    const r1 = ui.respond('savePublicationOverride', { state: 'ok', result: { status: 'ok' } });
    assert.deepEqual({ ...r1.data }, { action: 'savePublicationOverride', eqId: 231, publicationPolicy: 'exclude', cmdId: 2311 });
    ui.respond('revertMappingOverride', { state: 'ok', result: { status: 'ok' } });
    ui.respond('executeHaAction', ACTION_OK);
    const undoWrites = ui.calls.filter((c) => WRITES.includes(c.action)).slice(before);
    assert.deepEqual(undoWrites.map((c) => c.action), ['savePublicationOverride', 'revertMappingOverride']);
    ui.win.Jeedom2haSurface.clearEquipment();
  });

  it('« Toujours » déjà posé sur la commande : il reste, seul le type est rétabli', async () => {
    const { ui, before } = await publishAnywayThenUndo(lampeAvecSoeur('force_publish'));
    const r1 = ui.respond('revertMappingOverride', { state: 'ok', result: { status: 'ok' } });
    assert.deepEqual({ ...r1.data }, { action: 'revertMappingOverride', eqId: 231, cmdId: 2311 });
    ui.respond('executeHaAction', ACTION_OK);
    const undoWrites = ui.calls.filter((c) => WRITES.includes(c.action)).slice(before);
    assert.deepEqual(undoWrites.map((c) => c.action), ['revertMappingOverride'], 'aucune écriture de publication');
    ui.win.Jeedom2haSurface.clearEquipment();
  });

  it('échec du retrait : message d’une ligne, le type n’est pas touché', async () => {
    const { ui, P, before } = await publishAnywayThenUndo(lampeAvecSoeur(null));
    ui.respond('revertPublicationOverride', { state: 'ok', result: { status: 'error', message: 'Commande introuvable' } });
    assert.match(plain(ui.$(P + '.j2ha-v2-type-toast').text()), /Le réglage précédent n’a pas pu être rétabli/);
    assert.equal(ui.calls.filter((c) => WRITES.includes(c.action)).slice(before).length, 1);
    ui.win.Jeedom2haSurface.clearEquipment();
  });
});
