// Front v2 (Lot 6) — exclusion unifiée (E6) et confirmations chiffrées (E9). Modèle pur (priorités plugin / pièce / équipement,
// exception HomeKit, sous-pièces non entraînées, « Sans pièce » non excluable, comptage d'entités), écritures comparées aux corps
// de référence, textes des confirmations, puis le parcours `exclusion-unifiee-simulee` en VRAI Chromium avec la VRAIE politique
// du gate. Données fictives (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it, test } = require('node:test');
const assert = require('node:assert/strict');
const X = require('../../desktop/js/jeedom2ha_exclusions.js');
const { serialize } = require('./helpers/write_scenarios');
const { withRealView, gate } = require('./helpers/workview_browser');
const { SCENE } = require('./helpers/page_b_harness');

const root = path.join(__dirname, '..', '..');
const plain = (text) => String(text).replace(/\{\{|\}\}/g, '');
const reference = JSON.parse(fs.readFileSync(path.join(root, 'tests/fixtures/story_25_4_corps_ecriture.json'), 'utf8'));

const diag = (reason, publish) => ({ ha_entity_type: null, publication_reason: reason, reason_code: null, should_publish: publish,
  projection_validity: { is_valid: true, missing_capabilities: [], missing_fields: [], reason_code: null } });
function entry(id, opts) {
  const o = opts || {};
  const n = o.entities === undefined ? 1 : o.entities;
  const published = o.reason === undefined || o.reason === 'sure_mapping' || o.reason === 'publication_forced';
  return Object.assign({
    jeedom_eq_id: id, equipment_decision: diag(o.reason || 'sure_mapping', published),
    entities: Array.from({ length: n }, () => ({ override_pending: false, present_in_ha: o.present === undefined ? published : o.present })),
    commands: [{ jeedom_cmd_id: id * 10, covered: true, diagnostic: diag(o.reason || 'sure_mapping', published), published_in_ha: published }],
    sync_status: { published_in_ha: published, synced_should_publish: published, current_should_publish: published, override_pending: false },
  }, o.extra || {});
}

// Maison fictive : Salon (1) > Coin lecture (2, sous-pièce) ; Garage (3, exclu) ; Sans pièce (0).
const ROOMS = [
  { object_id: 1, object_name: 'Salon', father_id: 0, excluded: false, equipments: [
    { eq_id: 11, eq_name: 'Lampe', enabled: true, eq_type: 'zwave' },
    { eq_id: 12, eq_name: 'Volet', enabled: true, eq_type: 'virtual' },
    { eq_id: 13, eq_name: 'Prise', enabled: true, eq_type: 'zwave' },
  ] },
  { object_id: 2, object_name: 'Coin lecture', father_id: 1, excluded: false, equipments: [
    { eq_id: 21, eq_name: 'Liseuse', enabled: true, eq_type: 'zwave' },
  ] },
  { object_id: 3, object_name: 'Garage', father_id: 0, excluded: true, equipments: [
    { eq_id: 31, eq_name: 'Portail', enabled: true, eq_type: 'zwave' },
    { eq_id: 32, eq_name: 'Détecteur', enabled: true, eq_type: 'zwave' },
  ] },
  { object_id: 0, object_name: 'Sans pièce', father_id: 0, excluded: false, equipments: [
    { eq_id: 41, eq_name: 'Thermomètre', enabled: true, eq_type: 'virtual' },
  ] },
];
const EQUIPMENTS = {
  11: entry(11, { entities: 2 }),
  12: entry(12, { entities: 3 }),
  13: entry(13, { reason: 'publication_excluded_eqlogic', entities: 1 }),
  21: entry(21, { entities: 1 }),
  31: entry(31, { reason: 'excluded_object', entities: 1 }),
  32: entry(32, { entities: 1, extra: { homekit_kept_in_excluded_room: true, homekit_exposed_effective: true, scope_inherit: true } }),
  41: entry(41, { entities: 4 }),
};
const SNAP = { kind: 'ok', view: { stale: false, equipments: EQUIPMENTS, overview: { counts: { published: 5, to_apply: 2 } } } };
const NAMES = { zwave: 'Z-Wave', virtual: 'Virtuel' };
const model = (snap, csv) => X.buildModel(ROOMS, snap === undefined ? SNAP : snap, csv === undefined ? '' : csv, NAMES);
const changes = (patch) => Object.assign(X.emptyChanges(), patch);

describe('Lot 6 — priorités et raison effective', () => {
  it('lecture des réglages propres : « Jamais », masqué par la pièce, ancien réglage, « Toujours »', () => {
    assert.deepEqual(X.ownPolicyOf(EQUIPMENTS[13]), { own: 'never', known: true });
    assert.deepEqual(X.ownPolicyOf(EQUIPMENTS[31]), { own: 'auto', known: false });
    assert.deepEqual(X.ownPolicyOf(entry(9, { reason: 'excluded_eqlogic' })), { own: 'legacy', known: true });
    assert.deepEqual(X.ownPolicyOf(entry(9, { reason: 'publication_forced' })), { own: 'always', known: true });
    assert.deepEqual(X.ownPolicyOf(null), { own: 'auto', known: false });
  });

  it('plugin > pièce > équipement : le plugin exclu l\'emporte sur un « Jamais » et sur la pièce', () => {
    const m = model(undefined, 'zwave');
    assert.deepEqual(X.effectOf(m, 13, null), { excluded: true, reason: 'plugin', homekit: false });
    assert.equal(X.effectOf(m, 31, null).reason, 'plugin');
    assert.equal(plain(X.reasonText(m, 31, null)), 'Exclu : plugin Z-Wave exclu');
  });

  it('pièce exclue : « Exclu : pièce Garage exclue » ; l\'équipement exposé à HomeKit reste publié', () => {
    const m = model();
    assert.equal(plain(X.reasonText(m, 31, null)), 'Exclu : pièce Garage exclue');
    assert.deepEqual(X.effectOf(m, 32, null), { excluded: false, reason: null, homekit: true });
    assert.equal(plain(X.reasonText(m, 32, null)), 'Reste publié : exposé à HomeKit');
    // Un équipement désactivé n'est pas exposé : l'exception ne joue pas.
    const disabled = X.buildModel([{ object_id: 3, object_name: 'Garage', excluded: true, equipments: [{ eq_id: 32, eq_name: 'D', enabled: false, eq_type: 'zwave' }] }], SNAP, '', NAMES);
    assert.equal(X.effectOf(disabled, 32, null).reason, 'room');
  });

  it('exclure une pièce n\'entraîne pas ses sous-pièces ; la pièce parente le signale', () => {
    const m = model();
    const c = changes({ rooms: { 1: true } });
    assert.equal(X.effectOf(m, 11, c).reason, 'room');
    assert.equal(X.effectOf(m, 21, c).excluded, false, 'Coin lecture (sous-pièce) reste publiée');
    assert.equal(m.rooms.find((r) => r.id === 1).hasChildren, true);
  });

  it('« Sans pièce » n\'est jamais excluable : aucune écriture même si on le demande', () => {
    const m = model();
    assert.equal(m.rooms.find((r) => r.id === 0).excludable, false);
    assert.equal(X.effectOf(m, 41, changes({ rooms: { 0: true } })).excluded, false);
    assert.deepEqual(X.writesFor(m, changes({ rooms: { 0: true } }), 'sure_probable').filter((w) => w.kind === 'room' && w.id === 0), []);
  });

  it('« Jamais » d\'un équipement : « Exclu : réglage « Jamais » de l\'équipement »', () => {
    assert.equal(plain(X.reasonText(model(), 13, null)), 'Exclu : réglage « Jamais » de l\'équipement');
  });
});

describe('Lot 6 — différence chiffrée (pied en direct)', () => {
  it('décocher le plugin Virtuel : 2 équipements, 7 entités retirées ; le bouton rouge porte le chiffre', () => {
    const m = model();
    const d = X.diff(m, changes({ plugins: { virtual: true } }));
    assert.deepEqual([d.changes, d.removedEquipments, d.removedEntities, d.excluded.sort()], [1, 2, 7, [12, 41]]);
    assert.equal(plain(X.footText(d)), '1 changement · 2 équipements seront retirés de Home Assistant (7 entités)');
    assert.deepEqual(X.applyButton(d), { label: '{{Appliquer — retirer}} 7 {{entités}}', danger: true, disabled: false });
  });

  it('une pièce et un équipement d\'une autre pièce : deux changements, les deux portées comptées ensemble', () => {
    const d = X.diff(model(), changes({ rooms: { 1: true }, eqs: { 21: 'exclude' } }));
    // Salon : Lampe (2) + Volet (3) ; Prise était déjà exclue (« Jamais ») ; Liseuse (1).
    assert.deepEqual([d.changes, d.removedEquipments, d.removedEntities], [2, 3, 6]);
  });

  it('ne plus exclure le Garage : Portail revient ; bouton vert « Appliquer — publier 1 équipement »', () => {
    const d = X.diff(model(), changes({ rooms: { 3: false } }));
    assert.deepEqual([d.excluded, d.returned], [[], [31]]);
    const b = X.applyButton(d);
    assert.equal(plain(b.label), 'Appliquer — publier 1 équipement');
    assert.equal(b.danger, false);
  });

  it('recocher annule le changement : aucun changement, bouton inactif', () => {
    const m = model();
    const d = X.diff(m, changes({ plugins: { zwave: false }, rooms: { 3: true }, eqs: { 13: 'exclude', 11: 'include' } }));
    assert.equal(d.changes, 0);
    assert.equal(X.applyButton(d).disabled, true);
    assert.deepEqual(X.writesFor(m, changes({ rooms: { 3: true } }), 'sure_probable'), []);
  });

  it('lecture indisponible : le nombre d\'entités est dit inconnu, le bouton reste rouge', () => {
    const m = model(null);
    const d = X.diff(m, changes({ plugins: { virtual: true } }));
    assert.equal(d.entitiesKnown, false);
    assert.match(plain(X.footText(d)), /nombre d'entités inconnu pour l'instant/);
    assert.equal(X.applyButton(d).danger, true);
  });
});

describe('Lot 6 — écritures : routes et corps existants, inverses pour « Annuler »', () => {
  const byAction = (name) => Object.values(reference.scenarios).flat().filter((w) => w.action === name).map((w) => w.body);

  it('« Jamais » et retour en automatique : corps IDENTIQUES à la référence de 25.4', () => {
    const m = X.buildModel([{ object_id: 7, object_name: 'P', equipments: [{ eq_id: 1, eq_name: 'E', enabled: true, eq_type: 'zwave' }] }],
      { kind: 'ok', view: { stale: false, equipments: { 1: entry(1) }, overview: null } }, '', {});
    const exclude = X.writesFor(m, changes({ eqs: { 1: 'exclude' } }), 'sure_probable');
    assert.deepEqual(exclude.map((w) => serialize(w.data)), ['action=savePublicationOverride&eqId=1&publicationPolicy=exclude']);
    assert.ok(byAction('savePublicationOverride').includes(serialize(exclude[0].data)));
    const undo = X.inverseWrites(m, changes({ eqs: { 1: 'exclude' } }), 'sure_probable');
    assert.deepEqual(undo.map((w) => serialize(w.data)), ['action=revertPublicationOverride&eqId=1']);
    assert.ok(byAction('revertPublicationOverride').includes(serialize(undo[0].data)));
  });

  it('pièce : mêmes paramètres que le menu de carte (action, objectId, excluded) ; plugins : ceux de la configuration', () => {
    const m = model(undefined, 'enocean, zwave');
    const writes = X.writesFor(m, changes({ plugins: { virtual: true, zwave: false }, rooms: { 1: true } }), 'sure_only');
    assert.deepEqual(writes.map((w) => serialize(w.data)), [
      'action=saveFilteringConfig&confidencePolicy=sure_only&excludedPlugins=enocean,virtual',
      'action=saveRoomExclusion&excluded=1&objectId=1',
    ]);
    const home = fs.readFileSync(path.join(root, 'desktop/js/jeedom2ha.js'), 'utf8');
    assert.match(home, /data: \{action: 'saveRoomExclusion', objectId: String\(roomId\), excluded: excluded \? '1' : '0'\}/);
    const conf = fs.readFileSync(path.join(root, 'plugin_info/configuration.php'), 'utf8');
    assert.match(conf, /action:\s+'saveFilteringConfig',\s+excludedPlugins:[^\n]+\n\s+confidencePolicy:/);
    // Politique inconnue : jamais transmise telle quelle (la route la ramènerait à sure_probable).
    assert.equal(X.writesFor(m, changes({ plugins: { virtual: true } }), 'x').at(0).data.confidencePolicy, 'sure_probable');
  });

  it('annuler rend exactement la valeur d\'origine de excludedPlugins et le réglage « Toujours »', () => {
    const m = X.buildModel([{ object_id: 7, object_name: 'P', equipments: [{ eq_id: 5, eq_name: 'E', enabled: true, eq_type: 'zwave' }] }],
      { kind: 'ok', view: { stale: false, equipments: { 5: entry(5, { reason: 'publication_forced' }) }, overview: null } }, ' zwave ,, enocean', {});
    const c = changes({ plugins: { zwave: false }, rooms: { 7: true }, eqs: { 5: 'exclude' } });
    assert.deepEqual(X.inverseWrites(m, c, 'sure_probable').map((w) => serialize(w.data)), [
      'action=saveFilteringConfig&confidencePolicy=sure_probable&excludedPlugins= zwave ,, enocean',
      'action=saveRoomExclusion&excluded=0&objectId=7',
      'action=savePublicationOverride&eqId=5&publicationPolicy=force_publish',
    ]);
  });

  it('CSV des plugins : ordre gardé, plugins absents de la page gardés, doublons et vides retirés', () => {
    assert.deepEqual(X.parsePluginList(' a, b ,,a '), ['a', 'b']);
    assert.equal(X.serializePluginList('x,a', { b: true, a: false }), 'x,b');
  });
});

describe('Lot 6 — confirmations chiffrées (E9)', () => {
  it('« Supprimer tout » : équipements et entités présents dans le texte et sur le bouton', () => {
    const d = X.deleteAllDialog(SNAP);
    assert.equal(plain(d.title), 'Supprimer tout de Home Assistant');
    // Présents : 11 (2), 12 (3), 21 (1), 32 (1), 41 (4) ; 13 et 31 ne le sont pas.
    assert.equal(plain(d.lines[0]), '5 équipements (11 entités) seront retirés de Home Assistant.');
    assert.equal(plain(d.confirmLabel), 'Supprimer 11 entités');
    assert.match(plain(d.lines.join(' ')), /Republier tout/);
    assert.match(plain(d.lines.join(' ')), /ne s'annule pas/);
  });

  it('lecture indisponible : la confirmation le dit au lieu de se taire', () => {
    const d = X.deleteAllDialog(null);
    assert.match(plain(d.lines[0]), /Nombre d'entités inconnu pour l'instant/);
    assert.equal(plain(d.confirmLabel), 'Supprimer tout');
    assert.equal(plain(X.republishAllDialog({ kind: 'ok', view: { stale: true, equipments: {}, overview: null } }).confirmLabel), 'Republier tout');
  });

  it('« Republier tout », « Republier la pièce », « Relire Jeedom » : chiffres lus dans la copie des états', () => {
    const all = X.republishAllDialog(SNAP);
    assert.equal(plain(all.confirmLabel), 'Republier 5 équipements');
    assert.ok(all.lines.some((l) => plain(l) === '2 réglages en attente seront aussi appliqués.'));
    const room = X.republishRoomDialog(SNAP, ROOMS, 1, 'Salon');
    assert.equal(plain(room.title), 'Republier la pièce « Salon »');
    assert.equal(plain(room.confirmLabel), 'Republier 2 équipements');
    assert.match(plain(X.rescanDialog(SNAP).lines.join(' ')), /D'après la dernière lecture : 2 réglages en attente seront appliqués\./);
  });

  it('jeedom2ha.js : les boutons globaux lisent ces textes ; la suppression reste rouge et garde data-ha-action="supprimer-recreer"', () => {
    const home = fs.readFileSync(path.join(root, 'desktop/js/jeedom2ha.js'), 'utf8');
    const del = home.match(/\$\('\.j2ha-ha-action\[data-ha-action="supprimer-recreer"\]'\)[\s\S]*?\n  \}\);/)[0];
    assert.match(del, /deleteAllDialog\(j2haPageSnapshot\(\)\)/);
    assert.match(del, /confirmHaSupprimerAction\(/);
    assert.match(home, /republishAllDialog\(j2haPageSnapshot\(\)\)/);
    assert.doesNotMatch(home, /JSON\.stringify\([^)]*snapshot/i);
  });
});

describe('Lot 6 — menu de carte et bouton de la page', () => {
  it('le menu de carte porte « Choisir ce qui est publié… », « Republier la pièce » puis l\'exclusion', () => {
    const php = fs.readFileSync(path.join(root, 'desktop/php/jeedom2ha_overview_helpers.php'), 'utf8');
    const fn = php.slice(php.indexOf('function j2ha_render_room_menu'), php.indexOf('function j2ha_render_room_card'));
    const order = ['j2ha-room-choose', 'j2ha-card-republish', 'j2ha-menu-sep', 'j2ha-room-exclude'].map((c) => fn.indexOf(c));
    assert.ok(order.every((at, i) => at > 0 && (i === 0 || at > order[i - 1])), order.join(','));
    assert.match(fn, /data-ha-action="republier-piece" disabled/);
    assert.match(fn, /\{\{Autres actions\}\}/);
  });
});

// --- Parcours du gate en vrai Chromium ---

const WRITES = ['saveRoomExclusion', 'scanTopology', 'executeHaAction', 'savePublicationOverride', 'saveMappingOverride', 'revertMappingOverride', 'revertPublicationOverride', 'saveFilteringConfig', 'exportDiagnostic'];
// Scène fictive : des équipements du plugin « virtual » dans deux pièces.
const SCENE_VIRTUAL = Object.assign({}, SCENE, {
  eqlogics: Object.assign({}, SCENE.eqlogics, {
    3: [{ id: 102, name: 'Eq 102', type: 'virtual' }, { id: 103, name: 'Eq 103' }, { id: 104, name: 'Eq 104', enabled: false }],
    5: [{ id: 107, name: 'Eq 107', type: 'virtual' }, { id: 108, name: 'Eq 108' }, { id: 109, name: 'Eq 109' }, { id: 110, name: 'Eq 110' }],
  }),
  plugin_names: { zwave: 'Z-Wave', virtual: 'Virtuel' },
});

async function makeGate(overrides) {
  const { classifyRequest } = await import(gate('lib', 'policy.mjs'));
  const simulate = await import(gate('lib', 'simulate.mjs'));
  const parcours = await import(gate('parcours', 'exclusion-unifiee-simulee.mjs'));
  const ctx = Object.assign({
    origin: 'http://gate.test', loginAttempts: 0, declaredEquipments: {}, declaredPublicationOverrides: {}, declaredRoomExclusions: {},
    declaredRescan: parcours.declaredRescan === true, declaredFilteringConfig: parcours.declaredFilteringConfig, lastPreviewType: {},
  }, overrides || {});
  return {
    parcours,
    isWrite: (action) => WRITES.includes(action),
    handleWrite(action, request) {
      const decision = classifyRequest(request, ctx);
      if (decision.verdict !== 'simulate') return { verdict: decision.verdict };
      if (decision.action === 'scanTopology') {
        return { verdict: 'simulee', body: { state: 'ok', result: { status: 'ok', operation_result: 'succes', operation_message: 'Relecture terminée.', payload: { mapping_summary: {} } } } };
      }
      return { verdict: 'simulee', body: simulate.buildFilteringConfigResponse(decision.params) };
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

test('Lot 6 gate — le parcours est accepté par le lanceur et déclare ses écritures', async () => {
  const { loadParcours, isValidParcours } = await import(gate('run-gate.mjs'));
  const parcours = await loadParcours(path.join(root, 'tests/e2e/gate/parcours/exclusion-unifiee-simulee.mjs'));
  assert.equal(isValidParcours(parcours), true);
  assert.deepEqual(parcours.declaredFilteringConfig, { excludedPlugins: ['virtual', ''], confidencePolicy: 'sure_probable' });
  assert.equal(parcours.declaredRescan, true);
  const runner = fs.readFileSync(path.join(root, 'tests/e2e/gate/run-gate.mjs'), 'utf8');
  assert.match(runner, /declaredFilteringConfig: parcours\.declaredFilteringConfig \|\| null,/);
  const interceptor = fs.readFileSync(path.join(root, 'tests/e2e/gate/lib/interceptor.mjs'), 'utf8');
  assert.ok(interceptor.indexOf("decision.action === 'saveFilteringConfig'") > 0
    && interceptor.indexOf("decision.action === 'saveFilteringConfig'") < interceptor.indexOf('} else {\n          const revert = recordRevert(simState'));
});

test('Lot 6 gate réel — le parcours passe : pied chiffré, une écriture et une relecture, puis l\'annulation', async (t) => {
  const g = await makeGate();
  await withRealView(t, { gate: g, scene: SCENE_VIRTUAL }, async (page, ctx) => {
    const recorded = await runParcours(page, ctx, g.parcours);
    const virtualIds = ctx.rooms.flatMap((r) => r.equipments).filter((eq) => eq.eq_type === 'virtual').map((eq) => String(eq.eq_id));
    const expected = virtualIds.reduce((sum, id) => sum + (ctx.equipments[id] ? ctx.equipments[id].entities.filter((e) => e.present_in_ha === true).length : 0), 0);
    assert.equal(recorded.entites_annoncees, expected);
    assert.equal(recorded.etape_7, 'ecriture-non-declaree-transmise');
    const writes = ctx.journal.filter((entry) => WRITES.includes(entry.action)).map((entry) => `${entry.action}:${entry.verdict}`);
    assert.deepEqual(writes, ['saveFilteringConfig:simulee', 'scanTopology:simulee', 'saveFilteringConfig:simulee', 'scanTopology:simulee']);
    const bodies = ctx.bodies.filter((body) => body.startsWith('action=saveFilteringConfig'));
    assert.deepEqual(bodies.map((b) => Object.fromEntries(new URLSearchParams(b))), [
      { action: 'saveFilteringConfig', excludedPlugins: 'virtual', confidencePolicy: 'sure_probable' },
      { action: 'saveFilteringConfig', excludedPlugins: '', confidencePolicy: 'sure_probable' },
    ]);
    assert.deepEqual(ctx.errors, []);
  });
});

test('Lot 6 gate réel — sans déclaration, saveFilteringConfig est BLOQUÉE et rien n\'est relu', async (t) => {
  const g = await makeGate({ declaredFilteringConfig: null });
  await withRealView(t, { gate: g, scene: SCENE_VIRTUAL }, async (page, ctx) => {
    await assert.rejects(() => runParcours(page, ctx, g.parcours), /sequence-exclusion-inattendue/);
    const writes = ctx.journal.filter((entry) => WRITES.includes(entry.action)).map((entry) => `${entry.action}:${entry.verdict}`);
    assert.deepEqual(writes, ['saveFilteringConfig:block-fail']);
  });
});

test('Lot 6 réel — carte : « Choisir ce qui est publié… » ouvre le panneau sur la pièce, sans ouvrir la pièce ni écrire', async (t) => {
  const g = await makeGate();
  await withRealView(t, { gate: g, scene: SCENE_VIRTUAL }, async (page, ctx) => {
    const card = '#j2ha_roomCards .j2ha-room-card[data-object_id="3"]';
    await page.locator(`${card} .j2ha-menu-toggle`).click();
    await page.locator(`${card} .j2ha-room-choose`).click();
    await page.locator('.bootbox .j2ha-v2-excl').waitFor({ state: 'visible' });
    const opened = await page.evaluate(() => getComputedStyle(document.querySelector('#j2ha_workView')).display !== 'none');
    assert.equal(opened, false, 'la pièce ne s\'ouvre pas');
    const group = page.locator('.bootbox .j2ha-v2-excl-group[data-kind="room"][data-id="3"]');
    assert.equal(await group.getAttribute('aria-expanded'), 'true', 'positionné sur la pièce');
    assert.equal(await page.locator('.bootbox .j2ha-v2-excl-group[data-kind="room"][data-id="0"] .j2ha-v2-excl-cb').isDisabled(), true, '« Sans pièce » non excluable');
    assert.deepEqual(ctx.journal.filter((entry) => WRITES.includes(entry.action)), []);
    assert.deepEqual(ctx.errors, []);
  });
});
