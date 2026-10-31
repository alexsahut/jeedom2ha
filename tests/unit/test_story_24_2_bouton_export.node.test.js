// ARTEFACT — Story 24.2 (AC3, AC9, AC11) : l'entrée « Télécharger l'export de décision » du menu « ⋯ » de la page principale
// (squelette PHP rendu avec un faux cœur Jeedom, animé par le VRAI jeedom2ha_overview.js), son gestionnaire de téléchargement,
// les règles de libellés `{{…}}` et la séparation avec la liste blanche de getEquipmentStates. Identifiants fictifs (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { plain, startPage, phpAvailable } = require('./helpers/page_b_harness');

const root = path.join(__dirname, '..', '..');
const maybe = phpAvailable ? it : it.skip;
const read = (rel) => fs.readFileSync(path.join(root, rel), 'utf8');
const FORBIDDEN = ['override', 'bridge', 'prête', 'prêt', 'bloquante', 'rescanner', 'modale', 'modal'];

function labels(code) {
  return [...code.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '').matchAll(/\{\{([^}]*)\}\}/g)].map((m) => m[1]);
}

describe('24.2 / AC3 — menu « ⋯ »', () => {
  maybe('l\'entrée vient juste après « Télécharger le diagnostic… », avant le séparateur', () => {
    const ui = startPage();
    const items = ui.$('#j2ha_moreMenu .j2ha-menu li').list.map((li) => plain(ui.$(li).text()).trim());
    assert.deepEqual(items.slice(0, 2), ['Télécharger le diagnostic…', 'Télécharger l\'export de décision…']);
    assert.equal(ui.$('#bt_openDecisionExport').length, 1);
    assert.equal(ui.$('.j2ha-menu-danger').length, 1, 'le rouge reste réservé à la suppression');
  });

  maybe('l\'entrée ouvre une boîte portant le bouton de téléchargement ; fermer n\'émet aucune requête', () => {
    const ui = startPage();
    const before = ui.calls.length;
    ui.click('#bt_openDecisionExport');
    assert.equal(ui.dom.dialogs.length, 1);
    const dialog = ui.dom.dialogs[0];
    assert.equal(plain(dialog.options.title), 'Télécharger l\'export de décision');
    const modal = ui.$(dialog.modal);
    assert.equal(modal.find('#bt_exportDecision').length, 1);
    assert.match(plain(modal.text()), /identifiants seulement/);
    dialog.close();
    assert.equal(ui.calls.length, before, 'fermer ne déclenche aucune requête');
    assert.equal(ui.$('#div_decisionExportDialog #bt_exportDecision').length, 1, 'le contenu retourne à sa place');
  });

  maybe('au chargement, aucune requête ne concerne l\'export (lecture à la demande seulement)', () => {
    const ui = startPage();
    assert.equal(ui.calls.filter((c) => c.action === 'getDecisionExport').length, 0);
  });

  it('le gestionnaire relaie l\'action d\'administrateur getDecisionExport puis télécharge un fichier JSON daté', () => {
    const src = read('desktop/js/jeedom2ha.js');
    const block = src.slice(src.indexOf("$('#bt_exportDecision').on('click'"));
    assert.match(block, /action:\s+'getDecisionExport'/);
    assert.match(block, /JSON\.stringify\(data\.result, null, 2\)/);
    assert.match(block, /jeedom2ha-decision-export-' \+ today \+ '\.json'/);
    assert.match(block, /Jeedom2haActionBudget\.CLIENT_TIMEOUT_MS/);
    assert.doesNotMatch(block.slice(0, block.indexOf('\n});')), /exportDiagnostic/);
  });
});

describe('24.2 / libellés', () => {
  it('libellés {{…}} sur une seule ligne, aucun « {{ » hors libellé, aucun point final, aucun terme interdit', () => {
    const php = read('desktop/php/jeedom2ha.php');
    const js = read('desktop/js/jeedom2ha.js');
    const overview = read('desktop/js/jeedom2ha_overview.js');
    const added = [
      php.slice(php.indexOf('id="bt_openDecisionExport"') - 120, php.indexOf('id="bt_openDecisionExport"') + 260),
      php.slice(php.indexOf('id="div_decisionExportDialog"'), php.indexOf('Story 16.8 / 25.3')),
      js.slice(js.indexOf("$('#bt_exportDecision')"), js.indexOf('/* Permet la réorganisation')),
      overview.slice(overview.indexOf('function openDecisionExportDialog'), overview.indexOf('function init()')),
    ].join('\n');
    const withoutLabels = added.replace(/\{\{[^}\n]*\}\}/g, '');
    assert.doesNotMatch(withoutLabels, /\{\{|\}\}/, 'marqueur mal formé ou sur plusieurs lignes');
    const found = labels(added);
    for (const label of ['Télécharger l\'export de décision…', 'Télécharger l\'export de décision', 'Export en cours…', 'Export de décision téléchargé']) {
      assert.ok(found.includes(label), label);
    }
    for (const label of found) {
      assert.doesNotMatch(label, /\.$/, label);
      assert.doesNotMatch(label, /présent dans HA|présent dans Home Assistant|Assist/i, label);
      for (const word of FORBIDDEN) assert.doesNotMatch(label, new RegExp('(?<![\\p{L}\\p{N}_])' + word + '(?![\\p{L}\\p{N}_])', 'iu'), label);
    }
    assert.ok(added.includes("w('Télécharger l\\'export de décision')"), 'titre via w(), jamais un {{ en dur dans le code');
  });

  it('aucune couleur littérale ni CSS ajouté : les classes du plugin existantes sont réutilisées', () => {
    const php = read('desktop/php/jeedom2ha.php');
    const block = php.slice(php.indexOf('id="div_decisionExportDialog"'), php.indexOf('Story 16.8 / 25.3'));
    assert.doesNotMatch(block, /#[0-9a-fA-F]{3,8}\b|rgb\(|hsl\(/);
    assert.match(block, /class="j2ha-diagnostic-dialog"/);
  });
});

describe('24.2 / AC9 — séparation avec getEquipmentStates et gardes « diff vide »', () => {
  it('la liste blanche de getEquipmentStates ne porte aucun champ de l\'export : route et fichier séparés', () => {
    const src = read('resources/daemon/transport/http_server.py');
    const projection = src.slice(src.indexOf('def _project_equipment_state'), src.indexOf('def _build_equipment_states'));
    // Story 24.4 (R1) : `homekit_exposed_effective` est un booléen additif voulu de la route agrégée (pas le champ d'export `homekit_exposed`).
    for (const field of ['decision_export', 'homekit_exposed(?!_effective)', 'logical_id', 'schema_version', 'pending_changes']) {
      assert.ok(!new RegExp(field).test(projection), field);
    }
    assert.match(src, /app\.router\.add_get\("\/system\/decision_export", _handle_system_decision_export\)/);
    const ajax = read('core/ajax/jeedom2ha.ajax.php');
    const states = ajax.slice(ajax.indexOf("$action == 'getEquipmentStates'"), ajax.indexOf("$action == 'getDecisionExport'"));
    assert.ok(!states.includes('decision_export'));
  });

  it('jeedom2ha_mapping_override.js n\'est pas modifié par la story (aucune ligne retirée)', () => {
    const { execFileSync } = require('node:child_process');
    let removed = null;
    try {
      const base = execFileSync('git', ['merge-base', 'HEAD', 'origin/main'], { cwd: root, encoding: 'utf8' }).trim();
      removed = execFileSync('git', ['diff', '--numstat', base, '--', 'desktop/js/jeedom2ha_mapping_override.js'], { cwd: root, encoding: 'utf8' });
    } catch { return; } // pas d'historique git (archive) : garde sans objet
    assert.equal(removed.trim(), '');
  });
});
