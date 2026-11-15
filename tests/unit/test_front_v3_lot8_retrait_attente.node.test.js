// ARTEFACT — Front v3, Lot 8 (revue P2 #406) : un retrait (ou une publication) de bouton de scénario non confirmé par le démon
// (`withdraw_pending`, `ha_pending`, `in_ha` inconnu) reste « ◷ En attente de Home Assistant », et la ligne ambre
// « n boutons pas encore à jour · Réessayer » survit aux relectures de l'état jusqu'à la confirmation. Vrai Chromium,
// vraie politique du gate (simulation déclarée). Données fictives (CC-48).
'use strict';

const test = require('node:test');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const S = require('../../desktop/js/jeedom2ha_scenarios.js');
const { withRealView, gate } = require('./helpers/workview_browser');

const txt = (page, sel) => page.$eval(sel, (n) => n.textContent.replace(/\s+/g, ' ').trim());
function sc(id, name, extra) {
  return Object.assign({
    id, name, group: '', mode: 'provoke', has_trigger: false, has_schedule: false, manual: true, is_active: true,
    published: false, is_new: false, in_ha: false, ha_entity_id: null, withdraw_pending: false, ha_pending: false,
  }, extra);
}
const pub = (id) => ({ published: true, in_ha: true, ha_entity_id: `button.jeedom2ha_scenario_${id}` });
const base = () => [sc(12, 'Tout éteindre', pub(12)), sc(31, 'Réveil semaine', pub(31)), sc(62, 'Cinéma')];
const UP = (scenarios) => ({ daemon: true, broker: { state: 'connected' }, derniere_operation_resultat: 'aucun', ha: { birth_seen_at: '2026-11-14T08:00:00Z' }, scenarios });

describe('Lot 8 — attente côté Home Assistant (pur)', () => {
  it('withdraw_pending, ha_pending et in_ha inconnu comptent comme « pas à jour », même sans désaccord apparent', () => {
    assert.equal(S.haWaiting(sc(1, 'a', { published: false, in_ha: null, withdraw_pending: true, ha_pending: true })), true);
    assert.equal(S.haWaiting(sc(1, 'a', { published: false, in_ha: false, withdraw_pending: true })), true, 'retrait non confirmé, in_ha faux');
    assert.equal(S.haWaiting(sc(1, 'a', Object.assign(pub(1), { ha_pending: true }))), true, 'disponibilité non confirmée');
    assert.equal(S.haWaiting(sc(1, 'a', { published: false, in_ha: null })), true, 'inconnu n’est jamais « absent »');
    assert.equal(S.haWaiting(sc(1, 'a', pub(1))), false);
    assert.equal(S.haWaiting(sc(1, 'a')), false);
    const legacy = { id: 2, published: true, in_ha: true }; // démon du Lot 4a sans les champs du Lot 8
    assert.equal(S.haWaiting(legacy), false);
    assert.deepEqual(S.haMismatchIds([sc(1, 'a', { in_ha: null, withdraw_pending: true }), sc(2, 'b', pub(2))]), [1]);
  });
});

test('Lot 8 réel — retrait partiel : l’avertissement ambre survit aux relectures, puis Réessayer, puis succès', async (t) => {
  const { classifyRequest } = await import(gate('lib', 'policy.mjs'));
  const simulate = await import(gate('lib', 'simulate.mjs'));
  const ctx = { origin: 'http://gate.test', loginAttempts: 0, declaredEquipments: {}, lastPreviewType: {}, declaredScenarioPublications: { 12: true } };
  const answers = [
    { status: 'ok', operation_result: 'partiel', operation_message: 'Synchronisation partielle.', scenario_availability_complete: false },
    { status: 'ok', operation_result: 'succes', operation_message: 'Synchronisation terminée.', scenario_availability_complete: true },
  ];
  const g = {
    isWrite: (action) => action !== 'getBridgeStatus' && action !== 'getEquipmentStates' && action !== 'getMappingOverrides',
    handleWrite(action, request) {
      const decision = classifyRequest(request, ctx);
      if (decision.verdict !== 'simulate' || decision.action !== 'saveScenarioPublication') return { verdict: decision.verdict };
      const body = simulate.buildScenarioPublicationResponse({ idsToPublish: decision.params.ids_to_publish, idsToUnpublish: decision.params.ids_to_unpublish });
      body.result.rescan = answers.shift();
      return { verdict: 'simulee', body };
    },
  };
  let scenarios = base();
  await withRealView(t, { gate: g, bridgeStatus: () => UP(scenarios) }, async (page, c) => {
    await page.click('#j2ha_tabBtnScenarios');
    await page.click('tr[data-id="12"] .j2ha-v3-sc-switch');
    // Le démon n'a pas pu retirer le bouton : choix enregistré, présence inconnue, retrait en attente.
    scenarios = base().map((s) => (s.id === 12 ? Object.assign(s, { published: false, ha_entity_id: null, in_ha: null, withdraw_pending: true, ha_pending: true }) : s));
    await page.click('.j2ha-v3-sc-apply');
    await page.click('.bootbox [data-bb-handler="confirm"]');
    await page.waitForFunction(() => /pas encore à jour/.test(document.querySelector('.j2ha-v3-sc-result').textContent)
      && window.jeedom2haLastBridgeStatus.scenarios[0].withdraw_pending === true);
    const expected = 'Choix enregistré · 1 bouton pas encore à jour dans Home Assistant · Réessayer';
    assert.equal(await txt(page, '.j2ha-v3-sc-result'), expected);
    assert.equal(await txt(page, 'tr[data-id="12"] .j2ha-v3-sc-hacell'), '◷ En attente de Home Assistant');

    // Deux relectures de l'état : rien ne change tant que le démon n'a pas confirmé.
    for (let i = 0; i < 2; i += 1) {
      const before = c.journal.filter((e) => e.action === 'getBridgeStatus').length;
      await page.evaluate(() => window.refreshBridgeStatus());
      await page.waitForFunction((n) => window.jeedom2haBridgeRefreshes && document.querySelector('.j2ha-v3-sc-result') && n >= 0, before);
      await page.waitForTimeout(150);
      assert.ok(c.journal.filter((e) => e.action === 'getBridgeStatus').length > before);
      assert.equal(await page.getAttribute('.j2ha-v3-sc-result', 'data-kind'), 'warn', 'jamais « Choix appliqué » sur un retrait non confirmé');
      assert.equal(await txt(page, '.j2ha-v3-sc-result'), expected);
      assert.equal(await txt(page, 'tr[data-id="12"] .j2ha-v3-sc-hacell'), '◷ En attente de Home Assistant');
    }

    // Réessayer : même corps ; le démon confirme le retrait.
    scenarios = base().map((s) => (s.id === 12 ? Object.assign(s, { published: false, ha_entity_id: null, in_ha: false }) : s));
    await page.click('.j2ha-v3-sc-retry');
    await page.waitForFunction(() => document.querySelector('.j2ha-v3-sc-result').getAttribute('data-kind') === 'ok');
    assert.equal(await txt(page, '.j2ha-v3-sc-result'), 'Choix appliqué : 1 retiré');
    assert.equal(await txt(page, 'tr[data-id="12"] .j2ha-v3-sc-hacell'), '—');
    const writes = c.journal.filter((e) => e.action === 'saveScenarioPublication');
    assert.deepEqual(writes.map((w) => c.bodies[c.journal.indexOf(w)]),
      Array(2).fill('action=saveScenarioPublication&ids_to_publish=%5B%5D&ids_to_unpublish=%5B12%5D'));
    assert.deepEqual(writes.map((w) => w.verdict), ['simulee', 'simulee']);
    assert.deepEqual(c.errors, []);
  });
});
