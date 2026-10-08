// ARTEFACT — Story 20.3 (AC1, AC2, AC5, AC6, AC7, AC9) : la synthèse « Parc global » et la modale
// Diagnostic sont retirées de l'interface ; les relais et l'export support sont conservés ;
// le texte rendu ne contient plus de jargon de gabarit ni d'infrastructure.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const read = (p) => fs.readFileSync(p, 'utf8');
const php = read('desktop/php/jeedom2ha.php');
const jsDir = 'desktop/js';
const jsFiles = fs.readdirSync(jsDir).filter((f) => f.endsWith('.js'));
const jsSources = Object.fromEntries(jsFiles.map((f) => [f, read(path.join(jsDir, f))]));
const allJs = Object.values(jsSources).join('\n');

function stripPhpComments(source) {
  return source
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '');
}

function stripJsComments(source) {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

describe('20.3 / AC1 — « Parc global » supprimé', () => {
  const page = stripPhpComments(php);

  it('le DOM de la page ne contient ni #div_scopeSummary, ni #bt_refreshScopeSummary, ni les libellés de la synthèse', () => {
    assert.doesNotMatch(page, /div_scopeSummary|bt_refreshScopeSummary|Parc global|Synthèse du périmètre publié/);
  });

  it('les modules de synthèse et de diagnostic ne sont plus inclus et n’existent plus', () => {
    assert.doesNotMatch(page, /jeedom2ha_scope_summary|jeedom2ha_diagnostic_helpers/);
    assert.equal(fs.existsSync('desktop/js/jeedom2ha_scope_summary.js'), false);
    assert.equal(fs.existsSync('desktop/js/jeedom2ha_diagnostic_helpers.js'), false);
  });

  it('plus aucun gestionnaire de synthèse dans le JS livré', () => {
    const code = stripJsComments(allJs);
    assert.doesNotMatch(code, /div_scopeSummary|j2ha-row-toggle|j2ha-ecart-clickable|refreshPublishedScopeSummary|renderPublishedScopeSummary|Jeedom2haScopeSummary|table_scopeSummaryHierarchy/);
  });

  it('aucune requête getPublishedScopeForConsole ni getDiagnostics émise par l’interface', () => {
    const code = stripJsComments(allJs);
    assert.doesNotMatch(code, /getPublishedScopeForConsole/);
    assert.doesNotMatch(code, /getDiagnostics/);
  });

  it('plus aucune règle CSS de la synthèse', () => {
    assert.doesNotMatch(read('desktop/css/jeedom2ha.css'), /scopeSummary|ecart-affordance|div_diagnosticTable/);
  });
});

describe('20.3 / AC2 — modale Diagnostic supprimée, export support conservé', () => {
  const page = stripPhpComments(php);

  it('l’action « Diagnostic » et la modale n’existent plus', () => {
    assert.doesNotMatch(page, /data-action="diagnostic"/);
    const code = stripJsComments(allJs);
    assert.doesNotMatch(code, /data-action=diagnostic|Diagnostic de Couverture|modal-diagnostic|Jeedom2haDiagnosticHelpers/);
  });

  it('« Ajouter » et « Configuration » gardent eqLogicThumbnailContainer / eqLogicAction / data-action', () => {
    assert.match(page, /<div class="eqLogicThumbnailContainer">\s*<div class="cursor eqLogicAction logoPrimary" data-action="add">/);
    assert.match(page, /eqLogicAction logoSecondary" data-action="gotoPluginConf"/);
  });

  it('« Télécharger le diagnostic support » est conservé, avec son action exportDiagnostic', () => {
    assert.match(page, /id="bt_exportDiagnostic"/);
    assert.match(page, /\{\{Télécharger le diagnostic support\}\}/);
    assert.match(jsSources['jeedom2ha.js'], /action:\s+'exportDiagnostic'/);
  });
});

describe('20.3 / AC7 + AC9 — routes et relais backend conservés', () => {
  const ajax = read('core/ajax/jeedom2ha.ajax.php');
  const klass = read('core/class/jeedom2ha.class.php');

  it('les relais PHP getDiagnostics, getPublishedScopeForConsole et exportDiagnostic sont intacts', () => {
    assert.match(ajax, /case 'getDiagnostics'|'getDiagnostics'/);
    assert.match(ajax, /getPublishedScopeForConsole/);
    assert.match(ajax, /exportDiagnostic/);
    assert.match(klass, /public static function getPublishedScopeForConsole/);
  });

  it('le démon expose toujours /system/diagnostics et /system/published_scope', () => {
    const daemon = read('resources/daemon/transport/http_server.py');
    assert.match(daemon, /\/system\/diagnostics/);
    assert.match(daemon, /\/system\/published_scope/);
  });

  it('la surface ne lit ni published_scope, ni diagnostic_equipments, ni home_signals', () => {
    for (const file of ['jeedom2ha.js', 'jeedom2ha_mapping_surface.js', 'jeedom2ha_mapping_override.js']) {
      assert.doesNotMatch(stripJsComments(jsSources[file]), /published_scope|diagnostic_equipments|home_signals/, file);
    }
  });
});

describe('20.3 / AC5 — helpers de diagnostic sans consommateur retirés', () => {
  it('aucune référence résiduelle aux helpers de la modale', () => {
    assert.doesNotMatch(stripJsComments(allJs), /getCanonicalDiagnosticCause|isStep5Failed|getEcartBadgeHtml|findTargetEquipmentIndex|filterInScopeEquipments|PIPELINE_STEP_LABELS/);
  });
});

describe('20.3 / AC6 — libellés français d’usage', () => {
  const FORBIDDEN = [
    /mapping/i, /\bTemplate/i, /\bMes templates/i, /Paramètre n°1/, /Paramètres spécifiques/,
    /\bÉcart/, /\bEcart/, /\bConfiance/, /\beq_id\b/, /\breason_code\b/, /Parc global/,
    /Synthèse du périmètre/, /Diagnostic de Couverture/, /Parité FAN/, /Mot de passe/, /Auto-actualisation/,
  ];

  // Textes visibles du PHP : tout ce qui passe par {{ }} (la traduction Jeedom).
  function phpVisibleTexts() {
    const texts = [];
    stripPhpComments(php).replace(/\{\{([\s\S]*?)\}\}/g, (_m, t) => { texts.push(t); return ''; });
    return texts;
  }

  // Littéraux de chaîne JS à contenu rédigé (espace ou {{ }}) ; les identifiants techniques
  // (noms d’actions, classes, routes) n’ont pas d’espace et ne sont pas rendus.
  function jsVisibleTexts(source) {
    const texts = [];
    const re = /'((?:[^'\\\n]|\\.)*)'|"((?:[^"\\\n]|\\.)*)"/g;
    let m;
    const code = stripJsComments(source);
    while ((m = re.exec(code)) !== null) {
      const t = m[1] !== undefined ? m[1] : m[2];
      // Les balises HTML (classes, attributs) ne sont pas du texte rendu.
      const visible = t.replace(/<[^>]*>/g, ' ');
      if (/\s/.test(visible.trim()) || visible.includes('{{')) texts.push(visible);
    }
    return texts;
  }

  it('la page principale et la page d’équipement ne contiennent aucune chaîne interdite', () => {
    for (const text of phpVisibleTexts()) {
      for (const re of FORBIDDEN) assert.doesNotMatch(text, re, `« ${text} »`);
    }
  });

  it('les modules JS de la surface (modale de pièce) ne contiennent aucune chaîne interdite', () => {
    for (const file of ['jeedom2ha.js', 'jeedom2ha_mapping_surface.js', 'jeedom2ha_mapping_override.js']) {
      for (const text of jsVisibleTexts(jsSources[file])) {
        for (const re of FORBIDDEN) assert.doesNotMatch(text, re, `${file} : « ${text} »`);
      }
    }
  });

  it('table validée : libellés de remplacement présents', () => {
    const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
    assert.match(php, /\{\{Configuration Home Assistant par pièce\}\}/);
    assert.equal(M.buildUncoveredLabel(), 'Ne sera pas publié — commande sans type Home Assistant applicable');
    const reason = (code) => M.buildBlockingReason({
      publication_reason: code, should_publish: false, projection_validity: { is_valid: false },
    });
    assert.match(reason('ambiguous_skipped'), /^type Home Assistant ambigu/);
    assert.match(reason('sure_mapping'), /^type Home Assistant identifié/);
    assert.match(reason('no_mapping'), /^aucun type Home Assistant identifié/);
    assert.match(reason('command_not_covered'), /^commande sans type Home Assistant applicable/);
  });

  it('la section « Mes templates » et les champs sans usage sont retirés sans eqLogicAttr orphelin', () => {
    const page = stripPhpComments(php);
    assert.doesNotMatch(page, /data-l2key="(param1|password|autorefresh)"/);
    assert.doesNotMatch(page, /in_searchEqlogic|eqLogicDisplayCard|jeeHelper/);
    // Le squelette exigé par le cœur Jeedom est conservé.
    assert.match(page, /class="col-xs-12 eqLogic"/);
    assert.match(page, /eqLogicAction[^>]*data-action="save"/);
    assert.match(page, /id="table_cmd"/);
    assert.match(page, /include_file\('core', 'plugin\.template', 'js'\)/);
  });
});
