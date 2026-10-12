// ARTEFACT — Story 20.3 (AC10, gate simulé) : le parcours de découverte étendu s'exécute contre un
// DOM local qui reproduit la page livrée (sans synthèse ni action Diagnostic) ; aucune box, aucun
// réseau. Ignoré quand Playwright n'est pas résoluble (CI sans outils du gate).
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const gate = (...parts) => pathToFileURL(path.join(__dirname, '..', 'e2e', 'gate', ...parts)).href;

function counters() {
  return ['2 équipements publiés dans Home Assistant', '0 équipement en attente d’application',
    '0 équipement non pris en charge', '1 équipement exclu', '1 équipement désactivé dans Jeedom',
    '5 commandes publiées dans Home Assistant', '0 commande en attente d’application', '3 commandes non prises en charge']
    .map((t) => `<span class="label label-default j2ha-room-counter">${t}</span>`).join('');
}

// Story 22.2 : équipement multi-entités (579) — compteurs, deux lignes d'entité avec leurs trois
// actions « cette entité », trois actions d'équipement, commande 5369 portée par deux entités.
function multiEntityBody(id) {
  const entityActions = '<button>Exclure cette entité</button><button>Forcer cette entité</button><button>Revenir au mode automatique (cette entité)</button>';
  return `<div class="j2ha-eq-counters"><div class="j2ha-eq-counter-line">
    <span class="label j2ha-eq-counter">5 commandes publiées dans Home Assistant</span>
    <span class="label j2ha-eq-counter">0 commande en attente d’application</span>
    <span class="label j2ha-eq-counter">1 commande non prise en charge</span></div></div>
    <div class="j2ha-eq-actions"><span class="j2ha-publication-actions"><button>Exclure l’équipement</button><button>Forcer l’équipement</button><button>Revenir au mode automatique (équipement entier)</button></span></div>
    <div class="j2ha-eq-entities"><div class="j2ha-entity-row"><strong>switch</strong><span class="j2ha-publication-actions">${entityActions}</span></div>
    <div class="j2ha-entity-row"><strong>binary_sensor</strong><span class="j2ha-publication-actions">${entityActions}</span></div></div>
    <table class="j2ha-cmd-table"><tbody>
      <tr class="mapping-override-cmd" data-cmd-id="${id}1"><td class="mo-diag-cell j2ha-diag-ready">x</td></tr>
      <tr class="mapping-override-cmd" data-cmd-id="5369"><td class="mo-td-override"><select disabled title="Cette commande est portée par deux entités : réglage indisponible ici."></select></td><td class="mo-diag-cell j2ha-diag-ready">x</td></tr>
    </tbody></table>`;
}

function panel(id, name, state, publish) {
  if (id === 579) {
    return `<div class="panel j2ha-eq-panel" data-eq-id="${id}">
    <a class="j2ha-eq-toggle" href="#" onclick="this.parentNode.querySelector('.panel-collapse').style.display='block';return false;"><span class="j2ha-eq-name">${name}</span>
      <span class="j2ha-eq-publish-badge label ${publish}">Badge</span></a>
    <div class="panel-collapse" style="display:none">${multiEntityBody(id)}</div></div>`;
  }
  return `<div class="panel j2ha-eq-panel" data-eq-id="${id}">
    <a class="j2ha-eq-toggle" href="#" onclick="this.parentNode.querySelector('.panel-collapse').style.display='block';return false;"><span class="j2ha-eq-name">${name}</span>
      <span class="j2ha-eq-publish-badge label ${publish}">Badge</span></a>
    <div class="panel-collapse" style="display:none"><div class="j2ha-eq-actions"><button class="j2ha-eq-recreate">Supprimer de Home Assistant</button></div>
      <table class="j2ha-cmd-table"><tbody><tr class="mapping-override-cmd" data-cmd-id="${id}1"><td class="mo-diag-cell ${state}">x</td></tr></tbody></table></div></div>`;
}

function html(withDiagnosticAction, titlePrefix = '') {
  const room25 = `<div class="modal-j2ha-room"><div class="modal-title">${titlePrefix}<span class="j2ha-free-name">Pièce 25</span></div><div class="j2ha-room-counters">${counters()}</div>
    <div class="j2ha-room-actions"><button class="j2ha-room-republish">Republier la pièce</button><button class="j2ha-room-recreate">Supprimer la pièce de Home Assistant</button></div>
    ${panel(579, 'Eq-579', 'j2ha-diag-ready', 'j2ha-publish-ok')}${panel(514, 'Eq', 'j2ha-diag-disabled', 'j2ha-publish-disabled')}</div>`;
  const unassigned = `<div class="modal-j2ha-room"><div class="j2ha-room-counters">${counters()}</div>
    <div class="j2ha-room-actions"><span>Indisponible</span></div>${panel(7, 'Sans', 'j2ha-diag-ready', 'j2ha-publish-ok')}</div>`;
  return `<body><div class="row"><div class="eqLogicThumbnailDisplay">
    <div class="eqLogicThumbnailContainer"><div class="eqLogicAction" data-action="gotoPluginConf">Configuration</div>
    ${withDiagnosticAction ? '<div class="eqLogicAction" data-action="diagnostic">Diagnostic</div>' : ''}</div>
    <div id="div_bridgeHealthBanner">Bridge</div><button id="bt_exportDiagnostic">Télécharger le diagnostic support</button>
    <div id="j2ha_roomCards"><div class="j2ha-room-card" data-object_id="0"><span class="name">Sans pièce</span><span class="text-muted"> (1)</span></div>
    <div class="j2ha-room-card" data-object_id="25" id="piece-25"><span class="name j2ha-free-name">Pièce 25</span><span class="text-muted"> (2)</span></div></div></div>
    <div class="eqLogic" style="display:none">Équipement</div></div>
    <script>
      document.querySelector('[data-object_id="25"]').onclick = function () { document.body.insertAdjacentHTML('beforeend', ${JSON.stringify(room25)}); };
      document.querySelector('[data-object_id="0"]').onclick = function () { document.body.insertAdjacentHTML('beforeend', ${JSON.stringify(unassigned)}); };
      document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { var m = document.querySelector('.modal-j2ha-room'); if (m) m.remove(); } });
    </script></body>`;
}

async function withPage(t, content, journal, fn) {
  let playwright;
  try {
    const { loadPlaywright } = await import(gate('lib', 'playwright.mjs'));
    playwright = loadPlaywright();
  } catch {
    t.skip('Playwright indisponible : gate simulé ignoré');
    return;
  }
  const browser = await playwright.chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.setContent(content);
    const recorded = {};
    const helpers = {
      record: (key, value) => { assert.equal(Object.hasOwn(recorded, key), false, `clé dupliquée ${key}`); recorded[key] = value; },
      journalEntries: () => journal,
    };
    await fn(page, helpers, recorded);
  } finally {
    await browser.close();
  }
}

test('20.3 gate simulé — le parcours étendu passe sur la page livrée et relève les compteurs', async (t) => {
  const parcours = await import(gate('parcours', 'decouverte-piece-25-eq-579.mjs'));
  await withPage(t, html(false), [], async (page, helpers, recorded) => {
    await parcours.run(page, { helpers });
    assert.equal(recorded.absence_synthese, true);
    assert.equal(recorded.absence_action_diagnostic, true);
    assert.equal(recorded.export_support_present, true);
    assert.equal(recorded.lectures_synthese_diagnostic, 0);
    assert.equal(recorded.chaines_interdites_page, 0);
    assert.equal(recorded.piece_25_compteur_1, '2 équipements publiés dans Home Assistant');
    assert.equal(recorded.piece_25_compteur_8, '3 commandes non prises en charge');
    // Story 22.2 : équipement multi-entités, actions nommées par portée, commande 5369 partagée.
    assert.equal(recorded.eq_579_compteur_1, '5 commandes publiées dans Home Assistant');
    assert.equal(recorded.eq_579_entite_2_actions, 3);
    assert.equal(recorded.eq_579_actions_equipement, 3);
    assert.equal(recorded.selecteur_5369_desactive, true);
    assert.equal(recorded.actions_piece_presentes, true);
    assert.equal(recorded.sans_piece_sans_action_piece, true);
    assert.equal(recorded.sans_piece_compteur_6, '5 commandes publiées dans Home Assistant');
  });
});

test('20.3 gate simulé — l’action Diagnostic encore présente fait échouer le parcours', async (t) => {
  const parcours = await import(gate('parcours', 'decouverte-piece-25-eq-579.mjs'));
  await withPage(t, html(true), [], async (page, helpers) => {
    await assert.rejects(() => parcours.run(page, { helpers }), /action-diagnostic-presente/);
  });
});

test('20.3 gate simulé — une lecture de synthèse ou de diagnostic au chargement fait échouer le parcours', async (t) => {
  const parcours = await import(gate('parcours', 'decouverte-piece-25-eq-579.mjs'));
  await withPage(t, html(false), [{ action: 'getPublishedScopeForConsole' }], async (page, helpers) => {
    await assert.rejects(() => parcours.run(page, { helpers }), /lecture-synthese-ou-diagnostic/);
  });
});

test('20.3 gate simulé — une chaîne interdite dans la page fait échouer le parcours', async (t) => {
  const parcours = await import(gate('parcours', 'decouverte-piece-25-eq-579.mjs'));
  await withPage(t, html(false).replace('Configuration</div>', 'Mes templates</div>'), [], async (page, helpers) => {
    await assert.rejects(() => parcours.run(page, { helpers }), /chaine-interdite-page/);
  });
});

test('20.3 gate simulé (R1-H) — les noms libres ne sont pas soumis au gate de chaînes interdites', async (t) => {
  const parcours = await import(gate('parcours', 'decouverte-piece-25-eq-579.mjs'));
  const content = html(false)
    .replace('>Sans</span>', '>Mapping Template Écart</span>')
    .replace('>Eq</span>', '>Diagnostic de Couverture</span>');
  await withPage(t, content, [], async (page, helpers, recorded) => {
    await parcours.run(page, { helpers });
    assert.equal(recorded.chaines_interdites_page, 0);
    assert.equal(recorded.chaines_interdites_piece, 0);
  });
});

test('20.3 gate simulé (R1-H) — un libellé statique interdit dans la modale de pièce fait toujours échouer le parcours', async (t) => {
  const parcours = await import(gate('parcours', 'decouverte-piece-25-eq-579.mjs'));
  const content = html(false).replace('Republier la pièce</button>', 'Confiance mapping</button>');
  await withPage(t, content, [], async (page, helpers) => {
    await assert.rejects(() => parcours.run(page, { helpers }), /chaine-interdite-piece/);
  });
});

test('20.3 gate simulé (R2-6) — un libellé interdit dans le titre statique de la modale (hors nom de pièce) fait échouer le parcours', async (t) => {
  const parcours = await import(gate('parcours', 'decouverte-piece-25-eq-579.mjs'));
  const content = html(false, 'Confiance ');
  await withPage(t, content, [], async (page, helpers) => {
    await assert.rejects(() => parcours.run(page, { helpers }), /chaine-interdite-piece/);
  });
});

test('22.2 gate simulé — un équipement multi-entités aux actions d’entité sans portée fait échouer le parcours', async (t) => {
  const parcours = await import(gate('parcours', 'decouverte-piece-25-eq-579.mjs'));
  const content = html(false).replaceAll('Exclure cette entité', 'Exclure');
  await withPage(t, content, [], async (page, helpers) => {
    await assert.rejects(() => parcours.run(page, { helpers }), /actions-entite-579-inattendues/);
  });
});

test('22.2 gate simulé — la commande 5369 dont le sélecteur reste actif fait échouer le parcours', async (t) => {
  const parcours = await import(gate('parcours', 'decouverte-piece-25-eq-579.mjs'));
  const content = html(false).replaceAll('<select disabled title=', '<select title=');
  await withPage(t, content, [], async (page, helpers) => {
    await assert.rejects(() => parcours.run(page, { helpers }), /selecteur-5369-actif/);
  });
});

test('22.2 — les libellés attendus par les parcours 287 et 579 sont ceux que rend l’interface réelle', async () => {
  const fs = require('node:fs');
  const { createUi, tree, ok, READY, BRIDGE_UP } = require('./helpers/ui_harness');
  const ui = createUi([{ object_id: 7, object_name: 'Zone', equipments: [{ eq_id: 287, eq_name: 'Eq', enabled: true }] }]);
  ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
  ui.openRoom(7);
  ui.respond('getMappingOverrides', ok(tree(287, [READY], { entities: [{
    ha_entity_type: 'light', command_ids: [28700], decision: READY, publication_override: null,
    override_command_id: 28700, override_pending: false, present_in_ha: true }] })));
  const rendered = ui.$('.j2ha-eq-actions .j2ha-publication-actions button').list.map((b) => ui.$(b).text().replace(/\{\{|\}\}/g, ''));
  const source = fs.readFileSync(path.join(__dirname, '..', 'e2e', 'gate', 'parcours', 'exclusion-publication-non-publiee.mjs'), 'utf8');
  assert.ok(source.includes(`EXCLUDE_LABEL = '${rendered[0]}'`), rendered[0]);
  assert.ok(source.includes(`REVERT_LABEL = '${rendered[2]}'`), rendered[2]);
});
