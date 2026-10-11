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
  return ['2 équipements publiés', '1 équipement exclu', '1 équipement désactivé dans Jeedom', '0 équipement à corriger',
    '5 commandes prêtes', '0 commande bloquante', '3 commandes non couvertes']
    .map((t) => `<span class="label label-default j2ha-room-counter">${t}</span>`).join('');
}

function panel(id, name, state, publish) {
  return `<div class="panel j2ha-eq-panel" data-eq-id="${id}">
    <a class="j2ha-eq-toggle" href="#" onclick="this.parentNode.querySelector('.panel-collapse').style.display='block';return false;"><span class="j2ha-eq-name">${name}</span>
      <span class="j2ha-eq-publish-badge label ${publish}">Badge</span></a>
    <div class="panel-collapse" style="display:none"><div class="j2ha-eq-actions"><button class="j2ha-eq-recreate">Supprimer puis recréer</button></div>
      <table class="j2ha-cmd-table"><tbody><tr class="mapping-override-cmd" data-cmd-id="${id}1"><td class="mo-diag-cell ${state}">x</td></tr></tbody></table></div></div>`;
}

function html(withDiagnosticAction) {
  const garage = `<div class="modal-j2ha-room"><div class="j2ha-room-counters">${counters()}</div>
    <div class="j2ha-room-actions"><button class="j2ha-room-republish">Republier la pièce</button><button class="j2ha-room-recreate">Supprimer</button></div>
    ${panel(100, 'Enphase', 'j2ha-diag-ready', 'j2ha-publish-ok')}${panel(514, 'Eq', 'j2ha-diag-disabled', 'j2ha-publish-disabled')}</div>`;
  const unassigned = `<div class="modal-j2ha-room"><div class="j2ha-room-counters">${counters()}</div>
    <div class="j2ha-room-actions"><span>Indisponible</span></div>${panel(7, 'Sans', 'j2ha-diag-ready', 'j2ha-publish-ok')}</div>`;
  return `<body><div class="row"><div class="eqLogicThumbnailDisplay">
    <div class="eqLogicThumbnailContainer"><div class="eqLogicAction" data-action="add">Ajouter</div><div class="eqLogicAction" data-action="gotoPluginConf">Configuration</div>
    ${withDiagnosticAction ? '<div class="eqLogicAction" data-action="diagnostic">Diagnostic</div>' : ''}</div>
    <div id="div_bridgeHealthBanner">Bridge</div><button id="bt_exportDiagnostic">Télécharger le diagnostic support</button>
    <div id="j2ha_roomCards"><div class="j2ha-room-card" data-object_id="0"><span class="name">Sans pièce</span><span class="text-muted"> (1)</span></div>
    <div class="j2ha-room-card" data-object_id="3" id="garage"><span class="name">Garage</span><span class="text-muted"> (2)</span></div></div></div>
    <div class="eqLogic" style="display:none">Équipement</div></div>
    <script>
      document.querySelector('[data-object_id="3"]').onclick = function () { document.body.insertAdjacentHTML('beforeend', ${JSON.stringify(garage)}); };
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
  const parcours = await import(gate('parcours', 'decouverte-garage-enphase.mjs'));
  await withPage(t, html(false), [], async (page, helpers, recorded) => {
    await parcours.run(page, { helpers });
    assert.equal(recorded.absence_synthese, true);
    assert.equal(recorded.absence_action_diagnostic, true);
    assert.equal(recorded.export_support_present, true);
    assert.equal(recorded.lectures_synthese_diagnostic, 0);
    assert.equal(recorded.chaines_interdites_page, 0);
    assert.equal(recorded.garage_compteur_1, '2 équipements publiés');
    assert.equal(recorded.garage_compteur_7, '3 commandes non couvertes');
    assert.equal(recorded.actions_piece_presentes, true);
    assert.equal(recorded.sans_piece_sans_action_piece, true);
    assert.equal(recorded.sans_piece_compteur_5, '5 commandes prêtes');
  });
});

test('20.3 gate simulé — l’action Diagnostic encore présente fait échouer le parcours', async (t) => {
  const parcours = await import(gate('parcours', 'decouverte-garage-enphase.mjs'));
  await withPage(t, html(true), [], async (page, helpers) => {
    await assert.rejects(() => parcours.run(page, { helpers }), /action-diagnostic-presente/);
  });
});

test('20.3 gate simulé — une lecture de synthèse ou de diagnostic au chargement fait échouer le parcours', async (t) => {
  const parcours = await import(gate('parcours', 'decouverte-garage-enphase.mjs'));
  await withPage(t, html(false), [{ action: 'getPublishedScopeForConsole' }], async (page, helpers) => {
    await assert.rejects(() => parcours.run(page, { helpers }), /lecture-synthese-ou-diagnostic/);
  });
});

test('20.3 gate simulé — une chaîne interdite dans la page fait échouer le parcours', async (t) => {
  const parcours = await import(gate('parcours', 'decouverte-garage-enphase.mjs'));
  await withPage(t, html(false).replace('Configuration</div>', 'Mes templates</div>'), [], async (page, helpers) => {
    await assert.rejects(() => parcours.run(page, { helpers }), /chaine-interdite-page/);
  });
});
