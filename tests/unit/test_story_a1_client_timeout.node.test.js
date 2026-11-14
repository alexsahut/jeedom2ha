// ARTEFACT — Story A1 : délais clients des relais de parc, croisés avec le budget R.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const Budget = require('../../desktop/js/jeedom2ha_action_budget.js');
const root = path.join(__dirname, '../..');
const mainJs = fs.readFileSync(path.join(root, 'desktop/js/jeedom2ha.js'), 'utf8');
const configPhp = fs.readFileSync(path.join(root, 'plugin_info/configuration.php'), 'utf8');

function block(src, marker) {
  const i = src.indexOf(marker);
  assert.ok(i >= 0, marker + ' introuvable');
  return src.slice(i, i + 600);
}

describe('A1 — délais clients des relais de parc > budget R du relais PHP', () => {
  it('le délai client dépasse R + sonde de statut', () => {
    assert.ok(Budget.CLIENT_TIMEOUT_MS > (Budget.R + Budget.STATUS_TIMEOUT_S) * 1000);
  });

  it('scanTopology (console) lit Jeedom2haActionBudget.CLIENT_TIMEOUT_MS, plus de 20 s', () => {
    const b = block(mainJs, "data: {action: 'scanTopology'}");
    assert.match(b, /Jeedom2haActionBudget\.CLIENT_TIMEOUT_MS\) \|\| 90000/);
    assert.doesNotMatch(b, /timeout: 20000/);
  });

  it('exportDiagnostic lit Jeedom2haActionBudget.CLIENT_TIMEOUT_MS, plus de 30 s', () => {
    const b = block(mainJs, "action:       'exportDiagnostic'");
    assert.match(b, /Jeedom2haActionBudget\.CLIENT_TIMEOUT_MS\) \|\| 90000/);
    assert.doesNotMatch(b, /timeout:\s*30000/);
  });

  // Garde levée (front v3, Lot 3) : la configuration ne lance plus scanTopology (relecture du panneau « Choisir… » : budget
  // client de la page, vérifié ci-dessus).
  it('scanTopology : plus aucun appel depuis la configuration ; budget client de la page à 90 s', () => {
    assert.doesNotMatch(configPhp, /scanTopology/);
    assert.equal(Budget.CLIENT_TIMEOUT_MS, 90000);
  });
});
