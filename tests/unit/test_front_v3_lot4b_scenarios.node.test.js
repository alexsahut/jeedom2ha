// ARTEFACT — Front v3, Lot 4b : onglet « Scénarios » (option B). Fonctions pures sous node, puis la page en VRAI Chromium
// (squelette PHP réel, vrais scripts, vrai CSS) : liste, filtres, sélection groupée, confirmation de retrait chiffrée, corps
// EXACT de `saveScenarioPublication` passé à la VRAIE politique du gate (simulation déclarée), suggestion « lancés à la main »
// qui ne présélectionne que `manual === true`, étape 3 du guide, démon ancien. Données fictives (CC-48).
'use strict';

const { describe, it } = require('node:test');
const test = require('node:test');
const assert = require('node:assert/strict');
const S = require('../../desktop/js/jeedom2ha_scenarios.js');
const O = require('../../desktop/js/jeedom2ha_overview.js');
const { withRealView, gate } = require('./helpers/workview_browser');

const plain = (text) => String(text).replace(/\{\{|\}\}/g, '');
const txt = (page, sel) => page.$eval(sel, (n) => n.textContent.replace(/\s+/g, ' ').trim());

function sc(id, name, extra) {
  return Object.assign({
    id, name, group: '', mode: 'provoke', has_trigger: false, has_schedule: false, manual: true, is_active: true,
    published: false, is_new: false, in_ha: false, ha_entity_id: null,
  }, extra);
}
const pub = (id) => ({ published: true, in_ha: true, ha_entity_id: `button.jeedom2ha_scenario_${id}` });
const SCHEDULE = { mode: 'schedule', has_schedule: true, manual: false };
const TRIGGER = { mode: 'provoke', has_trigger: true, manual: false };

function fixture() {
  return [
    sc(12, 'Tout éteindre', Object.assign({ group: 'Ambiances' }, pub(12))),
    sc(31, 'Réveil semaine', Object.assign({ group: 'Matin' }, SCHEDULE, pub(31))),
    sc(40, 'Mode vacances', Object.assign({ group: 'Absence', is_active: false }, pub(40))),
    sc(51, 'Arrosage nuit', Object.assign({ group: 'Jardin', is_new: true }, SCHEDULE)),
    sc(52, 'Bonne nuit', { is_new: true }),
    sc(60, 'Purge journaux', Object.assign({ group: 'Technique' }, SCHEDULE)),
    sc(61, 'Alerte fumée', Object.assign({ group: 'Sécurité', is_new: true }, TRIGGER)),
    sc(62, 'Cinéma', { group: 'Ambiances' }),
    sc(63, 'Ancien test', { group: 'Technique', is_new: true, is_active: false }),
  ];
}
const UP = (scenarios) => Object.assign({ daemon: true, broker: { state: 'connected' }, derniere_operation_resultat: 'aucun', ha: { birth_seen_at: '2026-11-14T08:00:00Z' } },
  scenarios === undefined ? {} : { scenarios });

describe('Lot 4b — lecture et compte de l’onglet', () => {
  it('readList : null sans le champ (démon ancien), lignes mal formées écartées', () => {
    assert.equal(S.readList({ daemon: true }), null);
    assert.equal(S.readList(null), null);
    assert.equal(S.readList({ scenarios: null }), null);
    assert.deepEqual(S.readList({ scenarios: [{ id: 3 }, null, { id: 'x' }, { id: 0 }] }).map((s) => s.id), [3]);
  });

  it('compte de l’onglet : « publiés/total » et ✱ s’il y a des nouveaux ; repli sur le nombre d’avant sans la liste', () => {
    assert.equal(S.tabCount(fixture()), '3/9 ✱');
    assert.equal(S.tabCount(fixture().map((s) => Object.assign(s, { is_new: false }))), '3/9');
    assert.equal(O.scenarioTabText(UP(fixture())), '3/9 ✱');
    assert.equal(O.scenarioTabText(UP([])), '0/0');
    assert.equal(O.scenarioTabText({ publication: { scenarios_published: 4 } }), '4', 'démon ancien : nombre publié');
    assert.equal(O.scenarioTabText({}), '');
  });
});

describe('Lot 4b — issue de l’enregistrement et état réel côté Home Assistant', () => {
  const ok = (rescan) => ({ state: 'ok', result: { saved: true, ids_to_publish: [52], ids_to_unpublish: [], rescan } });
  it('saveOutcome : succès, partiel (operation_result partiel ou scenario_availability_complete false), échec, rien d’enregistré', () => {
    assert.equal(S.saveOutcome(ok({ status: 'ok', operation_result: 'succes', scenario_availability_complete: true })), 'ok');
    assert.equal(S.saveOutcome(ok({ status: 'ok', operation_result: 'succes' })), 'ok', 'champ absent : succès');
    assert.equal(S.saveOutcome(ok({ status: 'ok', operation_result: 'partiel', scenario_availability_complete: false })), 'partial');
    assert.equal(S.saveOutcome(ok({ status: 'ok', operation_result: 'partiel' })), 'partial');
    assert.equal(S.saveOutcome(ok({ status: 'ok', operation_result: 'succes', scenario_availability_complete: false })), 'partial');
    assert.equal(S.saveOutcome(ok({ status: 'ok', operation_result: 'echec' })), 'failed');
    assert.equal(S.saveOutcome(ok({ status: 'error', message: 'x' })), 'failed');
    assert.equal(S.saveOutcome(ok(undefined)), 'failed');
    assert.equal(S.saveOutcome({ state: 'error', result: 'refus' }), 'error');
    assert.equal(S.saveOutcome({ state: 'ok', result: { saved: false } }), 'error');
  });
  it('haMismatchIds : choix enregistré et bouton réel (in_ha) en désaccord, dans les deux sens', () => {
    const list = [sc(1, 'a', { published: true, in_ha: true }), sc(2, 'b', { published: true, in_ha: false }), sc(3, 'c', { published: false, in_ha: true }), sc(4, 'd')];
    assert.deepEqual(S.haMismatchIds(list), [2, 3]);
    assert.deepEqual(S.haMismatchIds(null), []);
  });
});

describe('Lot 4b — filtres', () => {
  const list = fixture();
  const ids = (filter) => S.filterList(list, filter).map((s) => s.id).sort((a, b) => a - b);

  it('puces : Publiés, Non publiés, Inactifs, Nouveaux ; zéro masqué sauf la puce active', () => {
    assert.deepEqual(S.chipsFor(list, null).map((c) => [c.key, c.count]), [['published', 3], ['unpublished', 6], ['inactive', 2], ['new', 4]]);
    assert.deepEqual(ids({ chip: 'published' }), [12, 31, 40]);
    assert.deepEqual(ids({ chip: 'unpublished' }), [51, 52, 60, 61, 62, 63]);
    assert.deepEqual(ids({ chip: 'inactive' }), [40, 63]);
    assert.deepEqual(ids({ chip: 'new' }), [51, 52, 61, 63]);
    const none = list.map((s) => Object.assign({}, s, { is_new: false }));
    assert.deepEqual(S.chipsFor(none, null).map((c) => c.key), ['published', 'unpublished', 'inactive']);
    assert.deepEqual(S.chipsFor(none, 'new').map((c) => c.key).pop(), 'new');
  });

  it('mode : « Lancé à la main », « Programmé », « Déclenché » d’après manual, has_schedule, has_trigger', () => {
    assert.deepEqual(ids({ mode: 'manual' }), [12, 40, 52, 62, 63]);
    assert.deepEqual(ids({ mode: 'schedule' }), [31, 51, 60]);
    assert.deepEqual(ids({ mode: 'trigger' }), [61]);
    assert.deepEqual(S.modeKeys(sc(1, 'x', { manual: null })), [], 'illisible');
    assert.deepEqual(S.modeKeys(sc(1, 'x', { manual: false, has_schedule: true, has_trigger: true })), ['schedule', 'trigger']);
  });

  it('groupe (sans groupe en dernier, illisible jamais proposé), recherche sans accents, filtres cumulés', () => {
    assert.deepEqual(S.groupsOf(list.concat([sc(99, 'y', { group: null })])), ['Absence', 'Ambiances', 'Jardin', 'Matin', 'Sécurité', 'Technique', '']);
    assert.deepEqual(ids({ group: 'Ambiances' }), [12, 62]);
    assert.deepEqual(ids({ group: '' }), [52]);
    assert.deepEqual(ids({ query: 'FUMEE' }), [61]);
    assert.deepEqual(ids({ query: 'nuit' }), [51, 52]);
    assert.deepEqual(ids({ query: 'nuit', mode: 'manual' }), [52]);
    assert.deepEqual(ids({ chip: 'new', group: 'Technique' }), [63]);
  });
});

describe('Lot 4b — choix en attente, corps de la requête, confirmation', () => {
  const list = fixture();

  it('une attente égale au choix enregistré disparaît ; la relecture retire celles que le démon reflète', () => {
    let p = S.setPending(list, {}, [52, 12], true);
    assert.deepEqual(p, { 52: true }, 'publier un publié : rien en attente');
    p = S.setPending(list, p, [52], false);
    assert.deepEqual(p, {});
    p = S.setPending(list, {}, [12, 52, 999], false);
    assert.deepEqual(p, { 12: false }, 'identifiant inconnu ignoré');
    const after = list.map((s) => (s.id === 12 ? Object.assign({}, s, { published: false }) : s));
    assert.deepEqual(S.prunePending(after, p), {});
  });

  it('requestFor : listes JSON strictes et triées, une seule requête ; null sans changement', () => {
    const r = S.requestFor(list, { 62: true, 52: true, 40: false, 12: false });
    assert.equal(r.action, 'saveScenarioPublication');
    assert.equal(r.ids_to_publish, '[52,62]');
    assert.equal(r.ids_to_unpublish, '[12,40]');
    assert.equal(S.requestFor(list, {}), null);
    assert.equal(S.requestFor(list, { 12: true }), null);
  });

  it('confirmation chiffrée seulement s’il y a un retrait : « Retirer n boutons de Home Assistant ? »', () => {
    assert.equal(S.removalDialog(S.requestFor(list, { 52: true })), null);
    const d = S.removalDialog(S.requestFor(list, { 12: false, 40: false, 52: true }));
    assert.equal(plain(d.title), 'Retirer 2 boutons de Home Assistant ?');
    assert.equal(plain(d.confirmLabel), 'Retirer (2)');
    assert.equal(plain(S.removalDialog(S.requestFor(list, { 12: false })).title), 'Retirer 1 bouton de Home Assistant ?');
    d.lines.forEach((line) => assert.ok(plain(line).length < 90, 'une ligne'));
    assert.equal(plain(S.successLine(S.requestFor(list, { 12: false, 40: false, 52: true }))), 'Choix appliqué : 1 publié, 2 retirés');
  });

  it('suggestion : non publiés, actifs, lancés à la main, nouveaux (ou tous si rien n’est publié) ; jamais programmé ni déclenché', () => {
    assert.deepEqual(S.suggestionIds(list, {}), [52]);
    assert.deepEqual(S.suggestionIds(list, { 52: true }), [], 'déjà présélectionné');
    const fresh = list.map((s) => Object.assign({}, s, { published: false, is_new: false }));
    assert.deepEqual(S.suggestionIds(fresh, {}), [12, 52, 62], 'installation neuve : tous les lancés à la main actifs');
    S.suggestionIds(fresh, {}).forEach((id) => assert.equal(fresh.find((s) => s.id === id).manual, true));
    assert.deepEqual(S.suggestionIds(null, {}), []);
    assert.deepEqual(S.suggestionIds([sc(5, 'x', { manual: null, is_new: true })], {}), [], 'mode illisible : jamais suggéré');
    assert.equal(plain(S.suggestionText(3).line), '3 scénarios lancés à la main');
    assert.equal(plain(S.suggestionText(3).button), 'Publier ces 3');
    assert.equal(plain(S.suggestionText(1).button), 'Publier ce scénario');
  });
});

// --- Banc réel (vrai Chromium) ---

async function scenarioGate(declared) {
  const { classifyRequest } = await import(gate('lib', 'policy.mjs'));
  const simulate = await import(gate('lib', 'simulate.mjs'));
  const ctx = { origin: 'http://gate.test', loginAttempts: 0, declaredEquipments: {}, lastPreviewType: {}, declaredScenarioPublications: declared };
  return {
    isWrite: (action) => action !== 'getBridgeStatus' && action !== 'getEquipmentStates' && action !== 'getMappingOverrides',
    handleWrite(action, request) {
      const decision = classifyRequest(request, ctx);
      if (decision.verdict !== 'simulate' || decision.action !== 'saveScenarioPublication') return { verdict: decision.verdict };
      return { verdict: 'simulee', body: simulate.buildScenarioPublicationResponse({ idsToPublish: decision.params.ids_to_publish, idsToUnpublish: decision.params.ids_to_unpublish }) };
    },
  };
}

const rowIds = (page) => page.$$eval('#j2ha_tab_scenarios tbody tr', (rows) => rows.map((r) => Number(r.getAttribute('data-id'))).sort((a, b) => a - b));

test('Lot 4b réel — liste, filtres, sélection groupée, confirmation de retrait, corps exact, une seule écriture et aucune relecture enchaînée', async (t) => {
  let scenarios = fixture();
  const g = await scenarioGate({ 12: true, 40: true, 52: true });
  await withRealView(t, { gate: g, bridgeStatus: () => UP(scenarios) }, async (page, ctx) => {
    await page.waitForFunction(() => document.querySelector('#j2ha_tabScenariosCount').textContent === '3/9 ✱');
    await page.click('#j2ha_tabBtnScenarios');
    assert.deepEqual(await rowIds(page), [12, 31, 40, 51, 52, 60, 61, 62, 63]);

    // Colonnes : nom + groupe, mode, état Jeedom, Dans Home Assistant, interrupteur (jamais grisé pour un inactif).
    const cells = await page.$$eval('#j2ha_tab_scenarios tbody tr', (rows) => Object.fromEntries(rows.map((r) => [r.getAttribute('data-id'), {
      name: r.querySelector('.j2ha-v3-sc-name').textContent, group: (r.querySelector('.j2ha-v3-sc-group-tag') || {}).textContent || '',
      fresh: !!r.querySelector('.j2ha-v3-sc-new'), mode: r.querySelector('.j2ha-v3-sc-modecell').innerText.trim(), jeedom: r.querySelector('.j2ha-v3-sc-jeedom').innerText.trim(),
      ha: r.querySelector('.j2ha-v3-sc-hacell').innerText.trim(), code: !!r.querySelector('.j2ha-v3-sc-hacell code'), copy: !!r.querySelector('.j2ha-v3-sc-copy'),
      on: r.querySelector('.j2ha-v3-sc-switch').getAttribute('aria-checked'), disabled: r.querySelector('.j2ha-v3-sc-switch').disabled,
    }])));
    assert.deepEqual(cells['12'], { name: 'Tout éteindre', group: 'Ambiances', fresh: false, mode: 'À la main', jeedom: 'Actif', ha: 'button.jeedom2ha_scenario_12', code: true, copy: true, on: 'true', disabled: false });
    assert.equal(cells['40'].ha, 'Indisponible');
    assert.equal(cells['40'].jeedom, 'Inactif');
    assert.equal(cells['40'].disabled, false, 'un scénario inactif garde un interrupteur utilisable');
    assert.equal(cells['63'].disabled, false);
    assert.equal(cells['51'].ha, '—');
    assert.equal(cells['51'].mode, 'Programmé');
    assert.equal(cells['61'].mode, 'Déclenché');
    assert.equal(cells['51'].fresh, true);

    // Puces (aria-pressed), groupe, mode, recherche.
    await page.click('.j2ha-v3-sc-chip[data-filter="inactive"]');
    assert.equal(await page.getAttribute('.j2ha-v3-sc-chip[data-filter="inactive"]', 'aria-pressed'), 'true');
    assert.deepEqual(await rowIds(page), [40, 63]);
    await page.click('.j2ha-v3-sc-chip[data-filter="inactive"]');
    assert.deepEqual((await rowIds(page)).length, 9);
    await page.selectOption('.j2ha-v3-sc-group', { label: 'Ambiances' });
    assert.deepEqual(await rowIds(page), [12, 62]);
    await page.selectOption('.j2ha-v3-sc-group', { label: 'Tous les groupes' });
    await page.selectOption('.j2ha-v3-sc-mode', 'schedule');
    assert.deepEqual(await rowIds(page), [31, 51, 60]);
    await page.selectOption('.j2ha-v3-sc-mode', '');
    await page.fill('.j2ha-v3-sc-search', 'nuit');
    assert.deepEqual(await rowIds(page), [51, 52]);
    await page.fill('.j2ha-v3-sc-search', '');

    // Suggestion : une ligne, elle ne présélectionne que les lancés à la main (ici Bonne nuit), rien n'est envoyé.
    assert.equal(await txt(page, '.j2ha-v3-sc-suggest'), '1 scénario lancé à la main → Publier ce scénario');
    const writesBefore = ctx.journal.filter((e) => e.action === 'saveScenarioPublication').length;
    await page.click('.j2ha-v3-sc-suggest-btn');
    assert.deepEqual(await page.evaluate(() => window.Jeedom2haScenariosPage.pending()), { 52: true });
    assert.equal(await page.isHidden('.j2ha-v3-sc-suggest'), true);
    assert.equal(await page.$eval('tr[data-id="52"] .j2ha-v3-sc-wait', (n) => n.textContent.includes('◷')), true, 'ligne marquée ◷');
    assert.equal(ctx.journal.filter((e) => e.action === 'saveScenarioPublication').length, writesBefore, 'présélection seulement');

    // Sélection groupée : « Ne pas publier (2) » sur 12 et 40, puis « Appliquer (3) ».
    await page.check('tr[data-id="12"] .j2ha-v3-sc-check');
    await page.check('tr[data-id="40"] .j2ha-v3-sc-check');
    assert.equal(await txt(page, '.j2ha-v3-sc-selcount'), '2 sélectionnés');
    assert.equal(await txt(page, '.j2ha-v3-sc-selunpub'), 'Ne pas publier (2)');
    await page.click('.j2ha-v3-sc-selunpub');
    assert.equal(await page.isHidden('.j2ha-v3-sc-selbar'), true);
    assert.equal(await txt(page, '.j2ha-v3-sc-apply'), 'Appliquer (3)');

    // Confirmation chiffrée ; « Annuler » n'écrit rien.
    await page.click('.j2ha-v3-sc-apply');
    assert.equal(await txt(page, '.bootbox .modal-title'), 'Retirer 2 boutons de Home Assistant ?');
    assert.equal(await txt(page, '.bootbox [data-bb-handler="confirm"]'), 'Retirer (2)');
    await page.click('.bootbox [data-bb-handler="cancel"]');
    assert.equal(ctx.journal.filter((e) => e.action === 'saveScenarioPublication').length, 0);

    await page.click('.j2ha-v3-sc-apply');
    const statusReadsBefore = ctx.journal.filter((e) => e.action === 'getBridgeStatus').length;
    // Le démon reflète le choix à la relecture d'état suivante.
    scenarios = fixture().map((s) => (s.id === 52 ? Object.assign(s, pub(52), { is_new: false })
      : (s.id === 12 || s.id === 40 ? Object.assign(s, { published: false, in_ha: false, ha_entity_id: null }) : s)));
    await page.click('.bootbox [data-bb-handler="confirm"]');
    await page.waitForFunction(() => document.querySelector('.j2ha-v3-sc-result').getAttribute('data-kind') === 'ok');
    assert.equal(await txt(page, '.j2ha-v3-sc-result'), 'Choix appliqué : 1 publié, 2 retirés');
    const writes = ctx.journal.filter((e) => e.action === 'saveScenarioPublication');
    assert.equal(writes.length, 1, 'un seul appel');
    assert.equal(writes[0].verdict, 'simulee', 'accepté par la politique du gate (déclaré)');
    const raw = ctx.bodies[ctx.journal.indexOf(writes[0])];
    assert.equal(raw, 'action=saveScenarioPublication&ids_to_publish=%5B52%5D&ids_to_unpublish=%5B12%2C40%5D');
    await page.waitForFunction((n) => window.jeedom2haLastBridgeStatus && window.jeedom2haLastBridgeStatus.scenarios[0].published === false && n >= 0, statusReadsBefore);
    assert.ok(ctx.journal.filter((e) => e.action === 'getBridgeStatus').length > statusReadsBefore, 'état du démon relu');
    assert.equal(ctx.journal.filter((e) => e.action === 'scanTopology').length, 0, 'aucune relecture enchaînée');
    await page.waitForFunction(() => document.querySelector('#j2ha_tabScenariosCount').textContent === '2/9 ✱');
    assert.deepEqual(await page.evaluate(() => window.Jeedom2haScenariosPage.pending()), {});
    assert.equal(await page.isHidden('.j2ha-v3-sc-foot'), true);
    assert.equal(await page.evaluate(() => window.jeedom2haRescanInProgress), false, 'réservation rendue');
    assert.deepEqual(ctx.errors, []);
  });
});

test('Lot 4b réel — échec partiel : ligne ambre « Choix enregistré · n boutons pas encore à jour… · Réessayer », colonne HA d’après in_ha', async (t) => {
  let scenarios = fixture();
  const real = await scenarioGate({ 52: true, 62: true });
  const answers = [
    { status: 'ok', operation_result: 'partiel', operation_message: 'Synchronisation partielle.', scenario_availability_complete: false },
    { status: 'ok', operation_result: 'succes', operation_message: 'Synchronisation terminée.', scenario_availability_complete: true },
  ];
  const g = {
    isWrite: real.isWrite,
    handleWrite(action, request) {
      const out = real.handleWrite(action, request);
      if (out.verdict === 'simulee') out.body.result.rescan = answers.shift();
      return out;
    },
  };
  await withRealView(t, { gate: g, bridgeStatus: () => UP(scenarios) }, async (page, ctx) => {
    await page.click('#j2ha_tabBtnScenarios');
    await page.click('tr[data-id="52"] .j2ha-v3-sc-switch');
    await page.click('tr[data-id="62"] .j2ha-v3-sc-switch');
    // Choix enregistré, mais seul 62 a son bouton : 52 reste en retard.
    scenarios = fixture().map((s) => (s.id === 52 ? Object.assign(s, { published: true, in_ha: false, ha_entity_id: 'button.jeedom2ha_scenario_52' })
      : (s.id === 62 ? Object.assign(s, pub(62)) : s)));
    await page.click('.j2ha-v3-sc-apply');
    await page.waitForFunction(() => /1 bouton pas encore/.test(document.querySelector('.j2ha-v3-sc-result').textContent));
    assert.equal(await page.getAttribute('.j2ha-v3-sc-result', 'data-kind'), 'warn', 'ambre, jamais vert');
    assert.equal(await txt(page, '.j2ha-v3-sc-result'), 'Choix enregistré · 1 bouton pas encore à jour dans Home Assistant · Réessayer');
    assert.equal(await txt(page, 'tr[data-id="52"] .j2ha-v3-sc-hacell'), '◷ En attente de Home Assistant', 'publié mais pas dans HA : pas de button.…');
    assert.equal(await page.$('tr[data-id="52"] .j2ha-v3-sc-hacell code'), null);
    assert.equal(await txt(page, 'tr[data-id="62"] .j2ha-v3-sc-hacell'), 'button.jeedom2ha_scenario_62');
    assert.equal(await page.isHidden('.j2ha-v3-sc-foot'), true, 'le choix est enregistré : plus rien en attente côté écran');

    // Réessayer : le même corps, une seconde fois ; le démon rattrape le bouton.
    scenarios = scenarios.map((s) => (s.id === 52 ? Object.assign({}, s, { in_ha: true }) : s));
    await page.click('.j2ha-v3-sc-retry');
    await page.waitForFunction(() => document.querySelector('.j2ha-v3-sc-result').getAttribute('data-kind') === 'ok');
    assert.equal(await txt(page, '.j2ha-v3-sc-result'), 'Choix appliqué : 2 publiés');
    const writes = ctx.journal.filter((e) => e.action === 'saveScenarioPublication');
    assert.equal(writes.length, 2);
    const raws = writes.map((w) => ctx.bodies[ctx.journal.indexOf(w)]);
    assert.deepEqual(raws, Array(2).fill('action=saveScenarioPublication&ids_to_publish=%5B52%2C62%5D&ids_to_unpublish=%5B%5D'));
    assert.deepEqual(writes.map((w) => w.verdict), ['simulee', 'simulee']);
    assert.equal(await txt(page, 'tr[data-id="52"] .j2ha-v3-sc-hacell'), 'button.jeedom2ha_scenario_52');
    assert.equal(ctx.journal.filter((e) => e.action === 'scanTopology').length, 0);
  });
});

test('Lot 4b réel — retrait pas encore fait dans Home Assistant : « En attente de Home Assistant » au lieu de « — »', async (t) => {
  const scenarios = fixture().map((s) => (s.id === 31 ? Object.assign(s, { published: false, ha_entity_id: null, in_ha: true }) : s));
  await withRealView(t, { bridgeStatus: () => UP(scenarios) }, async (page) => {
    await page.click('#j2ha_tabBtnScenarios');
    assert.equal(await txt(page, 'tr[data-id="31"] .j2ha-v3-sc-hacell'), '◷ En attente de Home Assistant');
    assert.equal(await txt(page, 'tr[data-id="40"] .j2ha-v3-sc-hacell'), 'Indisponible', 'inactif publié et présent : inchangé');
  });
});

test('Lot 4b réel — écriture non déclarée : bloquée par la politique du gate, message d’erreur, attente conservée', async (t) => {
  const g = await scenarioGate({ 99: true });
  await withRealView(t, { gate: g, bridgeStatus: () => UP(fixture()) }, async (page, ctx) => {
    await page.click('#j2ha_tabBtnScenarios');
    await page.click('tr[data-id="62"] .j2ha-v3-sc-switch');
    await page.click('.j2ha-v3-sc-apply');
    await page.waitForFunction(() => document.querySelector('.j2ha-v3-sc-result').getAttribute('data-kind') === 'error');
    assert.equal(ctx.journal.find((e) => e.action === 'saveScenarioPublication').verdict, 'block-fail');
    assert.deepEqual(await page.evaluate(() => window.Jeedom2haScenariosPage.pending()), { 62: true });
    assert.equal(await page.evaluate(() => window.jeedom2haRescanInProgress), false);
  });
});

test('Lot 4b réel — étape 3 du guide : même suggestion ; « Publier ce scénario » ouvre l’onglet et présélectionne seulement', async (t) => {
  await withRealView(t, { bridgeStatus: () => UP(fixture()) }, async (page, ctx) => {
    await page.waitForFunction(() => window.Jeedom2haGuideInstance && window.jeedom2haLastBridgeStatus);
    await page.evaluate(() => window.Jeedom2haGuideInstance.open());
    const line = page.locator('#j2ha_v2_guide [data-step="choice"] .j2ha-v3-sc-guide-suggest');
    assert.equal((await line.textContent()).replace(/\s+/g, ' ').trim(), '1 scénario lancé à la main → Publier ce scénario');
    await line.locator('button').click();
    assert.equal(await page.evaluate(() => window.Jeedom2haGuideInstance.state().visible), false);
    assert.equal(await page.getAttribute('#j2ha_tabBtnScenarios', 'aria-selected'), 'true');
    assert.deepEqual(await page.evaluate(() => window.Jeedom2haScenariosPage.pending()), { 52: true });
    assert.equal(ctx.journal.filter((e) => e.action === 'saveScenarioPublication').length, 0);
  });
});

test('Lot 4b réel — installation neuve : la suggestion prend tous les lancés à la main actifs, jamais un programmé ni un déclenché', async (t) => {
  const fresh = fixture().map((s) => Object.assign(s, { published: false, in_ha: false, ha_entity_id: null, is_new: false }));
  await withRealView(t, { bridgeStatus: () => UP(fresh) }, async (page) => {
    await page.click('#j2ha_tabBtnScenarios');
    assert.equal(await txt(page, '.j2ha-v3-sc-suggest'), '3 scénarios lancés à la main → Publier ces 3');
    await page.click('.j2ha-v3-sc-suggest-btn');
    assert.deepEqual(await page.evaluate(() => window.Jeedom2haScenariosPage.pending()), { 12: true, 52: true, 62: true });
    assert.equal(await txt(page, '#j2ha_tabScenariosCount'), '0/9');
  });
});

test('Lot 4b réel — démon ancien : « Liste indisponible · Relire » (relit l’état) ; Jeedom sans scénario : « Aucun scénario dans Jeedom »', async (t) => {
  let status = UP(undefined);
  await withRealView(t, { bridgeStatus: () => status }, async (page, ctx) => {
    await page.click('#j2ha_tabBtnScenarios');
    await page.waitForSelector('.j2ha-v3-sc-state[data-kind="unavailable"]');
    assert.equal(await txt(page, '.j2ha-v3-sc-state'), 'Liste indisponible · Relire');
    assert.equal(await txt(page, '#j2ha_tabScenariosCount'), '');
    const reads = ctx.journal.filter((e) => e.action === 'getBridgeStatus').length;
    status = UP([]);
    await page.click('.j2ha-v3-sc-reread');
    await page.waitForSelector('.j2ha-v3-sc-state[data-kind="empty"]');
    assert.equal(ctx.journal.filter((e) => e.action === 'getBridgeStatus').length, reads + 1);
    assert.equal(await txt(page, '.j2ha-v3-sc-state'), 'Aucun scénario dans Jeedom');
    assert.equal(ctx.journal.filter((e) => e.action === 'scanTopology').length, 0);
  });
});

test('Lot 4b réel — rendu : aucun débordement horizontal à 1280 et 760 px, clair et sombre', async (t) => {
  for (const width of [1280, 760]) {
    await withRealView(t, { width, bridgeStatus: () => UP(fixture()) }, async (page) => {
      await page.click('#j2ha_tabBtnScenarios');
      for (const theme of ['light', 'dark']) {
        await page.evaluate((th) => document.body.setAttribute('data-theme', th === 'dark' ? 'core2019_Dark' : 'core2019_Light'), theme);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
        assert.ok(overflow <= 0, `${width} ${theme} : débordement ${overflow}`);
        // Interrupteur publié = couleur « publié » du thème (variable --j2ha-ok), différente du non publié.
        const on = await page.$eval('tr[data-id="12"] .j2ha-v3-sc-switch', (n) => getComputedStyle(n).backgroundColor);
        const off = await page.$eval('tr[data-id="51"] .j2ha-v3-sc-switch', (n) => getComputedStyle(n).backgroundColor);
        const ok = await page.evaluate(() => getComputedStyle(document.body).getPropertyValue('--j2ha-ok').trim());
        assert.ok(ok, 'variable --j2ha-ok définie');
        assert.notEqual(on, off);
      }
    });
  }
});

test('Lot 4b — doc : section « Les scénarios » avec les libellés de l’écran, mot pour mot', () => {
  const doc = require('node:fs').readFileSync('docs/fr_FR/index.md', 'utf8');
  // Front v3 (Lot 5) : la doc est réécrite par écran ; la section suivante est « Configuration ».
  const section = doc.slice(doc.indexOf('### Les scénarios'), doc.indexOf('### Configuration'));
  // Front v3 (Lot 5) : la puce s'affiche « ✱ 3 Nouveaux » (icône, nombre, mot) : la doc cite le mot, après l'icône.
  for (const label of ['Publiés', 'Non publiés', 'Inactifs', '✱ « Nouveaux »', 'Tous les groupes', 'Tous les modes', 'Lancé à la main', 'Programmé', 'Déclenché',
    'Rechercher', 'Dans Home Assistant', 'Indisponible', 'Publier (n)', 'Ne pas publier (n)', 'Appliquer (n)', 'Annuler', 'Retirer n boutons de Home Assistant ?',
    'lancés à la main → Publier ces n', 'Aucun scénario dans Jeedom', 'Liste indisponible · Relire', '◷', 'En attente de Home Assistant',
    'Choix enregistré · n boutons pas encore à jour dans Home Assistant · Réessayer']) {
    assert.ok(section.includes(label), label);
  }
  assert.doesNotMatch(doc, /Chaque scénario Jeedom est publié comme un bouton/);
});
