// ARTEFACT — Story 19.6 (AC2) : délai fixe du client, croisé avec la table commune.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const Budget = require('../../desktop/js/jeedom2ha_action_budget.js');
const fixture = JSON.parse(fs.readFileSync(
  path.join(__dirname, '../fixtures/action_budget_constants.json'), 'utf8'
));
const clientSource = fs.readFileSync(
  path.join(__dirname, '../../desktop/js/jeedom2ha.js'), 'utf8'
);

describe('19.6 / AC1-AC2 — constantes du budget croisées avec la table commune', () => {
  it('le module JS expose les mêmes constantes que la table', () => {
    assert.strictEqual(Budget.R, fixture.R);
    assert.strictEqual(Budget.RESERVE_S, fixture.reserve_s);
    assert.strictEqual(Budget.STATUS_TIMEOUT_S, fixture.status_timeout_s);
    assert.strictEqual(Budget.CLICK_READ_DEADLINE_S, fixture.click_read_deadline_s);
    assert.strictEqual(Budget.REALIGN_TIMEOUT_S, fixture.realign_timeout_s);
    assert.strictEqual(Budget.CLIENT_TIMEOUT_MS, fixture.client_timeout_ms);
  });
});

describe('19.6 / AC2 — délai fixe du client strictement supérieur au pire chemin', () => {
  it('worstPathMs() correspond au pire des deux chemins de la requête PHP', () => {
    // Chemin qui aboutit : statut(3) + lecture(10) + R(60) + réalignement(3) = 76 s
    // Chemin en échec    : statut(3) + lecture(10) + R(60) + second statut(3)  = 76 s
    assert.strictEqual(Budget.worstPathMs(), 76000);
  });

  it('CLIENT_TIMEOUT_MS dépasse strictement le pire chemin', () => {
    assert.ok(Budget.CLIENT_TIMEOUT_MS > Budget.worstPathMs());
  });

  it('reste sous le Timeout 300 d\'Apache (300000 ms)', () => {
    assert.ok(Budget.CLIENT_TIMEOUT_MS < 300000);
  });

  it('executeHaAction() déclare le même délai fixe que le module de budget (AJAX timeout)', () => {
    const fnStart = clientSource.indexOf('function executeHaAction(');
    assert.ok(fnStart >= 0, 'executeHaAction introuvable dans desktop/js/jeedom2ha.js');
    const fnEnd = clientSource.indexOf('\nfunction ', fnStart + 1);
    const fnBody = clientSource.slice(fnStart, fnEnd > 0 ? fnEnd : undefined);
    const match = fnBody.match(/timeout:\s*(\d+)\s*,/);
    assert.ok(match, 'aucun "timeout: N," trouvé dans executeHaAction()');
    const declaredTimeoutMs = Number(match[1]);
    assert.strictEqual(declaredTimeoutMs, Budget.CLIENT_TIMEOUT_MS);
    assert.ok(declaredTimeoutMs > Budget.worstPathMs());
  });
});
