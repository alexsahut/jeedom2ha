// ARTEFACT — Story 20.3 (AC10, gate simulé) : le parcours de découverte étendu s'exécute contre un
// DOM local qui reproduit la page livrée (sans synthèse ni action Diagnostic) ; aucune box, aucun
// réseau. Ignoré quand Playwright n'est pas résoluble (CI sans outils du gate).
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const gate = (...parts) => pathToFileURL(path.join(__dirname, '..', 'e2e', 'gate', ...parts)).href;

// Story 25.1 : la page simulée reproduit le DOM livré — un chiffre et un mot par état d'équipement non nul
// (compteurs de la pièce), badge d'état unique, contrôle segmenté « Automatique | Toujours | Jamais »,
// tableau regroupé par entité, réglage « Type HA » en lien.
function counters(parts) {
  return parts.map(([state, text]) => `<span class="j2ha-chip j2ha-room-counter j2ha-chip-${state}" data-state="${state}">${text}</span>`).join('');
}

const SEG = '<span class="j2ha-seg" role="radiogroup"><button class="j2ha-seg-btn" role="radio">Automatique</button><button class="j2ha-seg-btn" role="radio">Toujours</button><button class="j2ha-seg-btn" role="radio">Jamais</button></span>';
const SHARED_TITLE = 'Cette commande est portée par plusieurs entités : le type Home Assistant choisi ne s’appliquerait qu’à l’entité principale de l’équipement. Réglage indisponible ici.';

// Story 22.2 / 25.1 : équipement multi-entités (579) — compteurs de commandes, deux groupes d'entité avec leur
// contrôle segmenté, contrôle d'équipement, commande 5369 portée par plusieurs entités (Type HA indisponible).
function multiEntityBody(id, { entitySeg = SEG, sharedAria = 'true' } = {}) {
  return `<div class="j2ha-eq-counters"><div class="j2ha-eq-counter-line">
    <span class="j2ha-eq-counter">5 publiées</span>
    <span class="j2ha-eq-counter">1 ignorée</span></div></div>
    <div class="j2ha-eq-controls">${SEG}</div>
    <table class="j2ha-cmd-table"><tbody>
      <tr class="j2ha-group-head"><td>Interrupteur switch ${entitySeg}</td></tr>
      <tr class="mapping-override-cmd" data-cmd-id="${id}1"><td class="mo-diag-cell j2ha-diag-ready">x</td></tr>
      <tr class="j2ha-group-head"><td>Capteur binaire binary_sensor ${SEG}</td></tr>
      <tr class="mapping-override-cmd" data-cmd-id="5369"><td class="mo-diag-cell j2ha-diag-ready">x</td><td class="mo-td-override"><span class="j2ha-type-link j2ha-type-unavailable" aria-disabled="${sharedAria}" title="${SHARED_TITLE}">auto</span></td></tr>
    </tbody></table>`;
}

function panel(id, name, state, badgeState, badgeText, options) {
  const badge = `<span class="j2ha-eq-publish-badge j2ha-badge j2ha-state-${badgeState}">${badgeText}</span>`;
  if (id === 579) {
    return `<div class="panel j2ha-eq-panel" data-eq-id="${id}">
    <a class="j2ha-eq-toggle" href="#" onclick="this.parentNode.querySelector('.panel-collapse').style.display='block';return false;"><span class="j2ha-eq-name">${name}</span>
      ${badge}</a>
    <div class="panel-collapse" style="display:none">${multiEntityBody(id, options)}</div></div>`;
  }
  return `<div class="panel j2ha-eq-panel" data-eq-id="${id}">
    <a class="j2ha-eq-toggle" href="#" onclick="this.parentNode.querySelector('.panel-collapse').style.display='block';return false;"><span class="j2ha-eq-name">${name}</span>
      ${badge}</a>
    <div class="panel-collapse" style="display:none"><div class="j2ha-eq-controls">${SEG}<span class="j2ha-menu-wrap"><ul class="j2ha-menu"><li><button class="j2ha-eq-recreate">Supprimer de Home Assistant…</button></li></ul></span></div>
      <table class="j2ha-cmd-table"><tbody><tr class="mapping-override-cmd" data-cmd-id="${id}1"><td class="mo-diag-cell ${state}">x</td></tr></tbody></table></div></div>`;
}

function html(withDiagnosticAction, titlePrefix = '', options = {}) {
  const room25 = `<div class="modal-j2ha-room"><div class="modal-title">${titlePrefix}<span class="j2ha-free-name">Pièce 25</span></div><div class="j2ha-room-counters">${counters([['published', '1 publié'], ['disabled', '1 désactivé']])}</div>
    <div class="j2ha-room-actions"><span class="j2ha-menu-wrap"><ul class="j2ha-menu"><li><button class="j2ha-room-republish">Republier</button></li><li><button class="j2ha-room-recreate">Supprimer de Home Assistant…</button></li></ul></span></div>
    ${panel(579, 'Eq-579', 'j2ha-diag-ready', 'published', 'Publié', options)}${panel(514, 'Eq', 'j2ha-diag-disabled', 'disabled', 'Désactivé')}</div>`;
  const unassigned = `<div class="modal-j2ha-room"><div class="j2ha-room-counters">${counters([['published', '1 publié']])}</div>
    <div class="j2ha-room-actions"><span>Indisponible</span></div>${panel(7, 'Sans', 'j2ha-diag-ready', 'published', 'Publié')}</div>`;
  return `<body><div class="row"><div class="eqLogicThumbnailDisplay">
    <div class="eqLogicThumbnailContainer"><div class="eqLogicAction" data-action="gotoPluginConf">Configuration</div>
    ${withDiagnosticAction ? '<div class="eqLogicAction" data-action="diagnostic">Diagnostic</div>' : ''}</div>
    <div id="div_bridgeHealthBanner">Démon</div><button id="bt_exportDiagnostic">Télécharger le diagnostic support</button>
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
    const { normalizeParcoursRecord } = await import(gate('lib', 'report.mjs'));
    const helpers = {
      // Story 22.2 : chaque observation passe par la validation du vrai rapport du gate (clé, type,
      // 80 caractères au plus), pour détecter sans la box une valeur que le rapport refuserait.
      record: (key, value) => {
        const [safeKey, safeValue] = normalizeParcoursRecord(key, value);
        assert.equal(Object.hasOwn(recorded, safeKey), false, `clé dupliquée ${safeKey}`);
        recorded[safeKey] = safeValue;
      },
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
    assert.equal(recorded.piece_25_compteur_1, '1 publié');
    assert.equal(recorded.piece_25_compteur_2, '1 désactivé');
    assert.equal(Object.hasOwn(recorded, 'piece_25_compteur_3'), false, 'les états à zéro ne sont pas affichés');
    // Story 22.2 : équipement multi-entités, actions nommées par portée, commande 5369 partagée.
    assert.equal(recorded.eq_579_compteur_1, '5 publiées');
    assert.equal(recorded.eq_579_entite_2_actions, 3);
    assert.equal(recorded.eq_579_actions_equipement, 3);
    assert.equal(recorded.selecteur_5369_desactive, true);
    assert.equal(recorded.actions_piece_presentes, true);
    assert.equal(recorded.sans_piece_sans_action_piece, true);
    assert.equal(recorded.sans_piece_compteur_1, '1 publié');
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
  const content = html(false).replace('Republier</button>', 'Confiance mapping</button>');
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

test('22.2 gate simulé — un équipement multi-entités dont un contrôle d’entité est incomplet fait échouer le parcours', async (t) => {
  const parcours = await import(gate('parcours', 'decouverte-piece-25-eq-579.mjs'));
  // Le contrôle d'un groupe d'entité perd sa position « Jamais » : le parcours doit le refuser.
  const content = html(false, '', { entitySeg: SEG.replace('<button class="j2ha-seg-btn" role="radio">Jamais</button>', '') });
  await withPage(t, content, [], async (page, helpers) => {
    await assert.rejects(() => parcours.run(page, { helpers }), /actions-entite-579-inattendues/);
  });
});

test('22.2 gate simulé — la commande 5369 dont le réglage « Type HA » reste actif fait échouer le parcours', async (t) => {
  const parcours = await import(gate('parcours', 'decouverte-piece-25-eq-579.mjs'));
  const content = html(false, '', { sharedAria: 'false' });
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
  // Story 25.1 : « Exclure l’équipement » / « Revenir au mode automatique » deviennent les positions « Jamais » / « Automatique ».
  const rendered = ui.$('.j2ha-eq-controls .j2ha-seg-btn').list.map((b) => ui.$(b).text().replace(/\{\{|\}\}/g, ''));
  assert.deepEqual(rendered, ['Automatique', 'Toujours', 'Jamais']);
  const source = fs.readFileSync(path.join(__dirname, '..', 'e2e', 'gate', 'parcours', 'exclusion-publication-non-publiee.mjs'), 'utf8');
  assert.ok(source.includes(`EXCLUDE_LABEL = '${rendered[2]}'`), rendered[2]);
  assert.ok(source.includes(`REVERT_LABEL = '${rendered[0]}'`), rendered[0]);
});

test('22.2 R2 — le parcours 380 bascule sur le seul type encore proposé pour 2971, jamais sur un type retiré', () => {
  const fs = require('node:fs');
  const source = fs.readFileSync(path.join(__dirname, '..', 'e2e', 'gate', 'parcours', 'reference-bascule-eq-380.mjs'), 'utf8');
  assert.match(source, /const BASCULE_TYPE = 'cover';/);
  assert.match(source, /haEntityType: BASCULE_TYPE/);
  assert.doesNotMatch(source, /selectOption\('(sensor|binary_sensor)'\)/);
  assert.match(source, /type-refuse-encore-propose/);
});


// --- Parcours de référence 380 sur une page simulée (22.2, fix du gate) ---
// La cause d'un type refusé fait environ 90 caractères, comme sur la box : le parcours ne doit en
// enregistrer que le constat. Le journal de l'intercepteur est simulé par les gestionnaires de la page.

// Story 25.1 : la cause (environ 80 caractères, comme sur la box) est dite une fois, dans l'encart de l'équipement ;
// le parcours ne doit en enregistrer que le constat. Le badge dit l'état (« Bloqué », « À appliquer »).
const CAUSE = 'type Home Assistant ambigu — précisez les types génériques dans Jeedom';
const LONG_CAUSE = `1 commande bloquée : ${CAUSE}`;
const INITIAL_BADGE = 'Bloqué';
const READY_BADGE = 'À appliquer';

function html380(journal, { sensorOffered = false } = {}) {
  const options = `<option value="">auto</option>${sensorOffered ? '<option value="sensor">sensor</option><option value="binary_sensor">binary_sensor</option>' : ''}<option value="cover">cover</option>`;
  const modal = `<div class="modal-j2ha-room"><div class="j2ha-eq-panel" data-eq-id="380">
    <a class="j2ha-eq-toggle" href="#" onclick="document.querySelector('.panel-collapse').style.display='block';return false;"><span class="j2ha-eq-name">Eq</span>
      <span class="j2ha-eq-publish-badge j2ha-badge">${INITIAL_BADGE}</span></a>
    <div class="panel-collapse" style="display:none">
      <div class="j2ha-eq-counters"><div class="j2ha-eq-counter-line" id="counters380">
        <span class="j2ha-eq-counter">1 bloquée</span>
        <span class="j2ha-eq-counter">1 ignorée</span></div></div>
      <div class="j2ha-notice"><span class="j2ha-notice-text">${LONG_CAUSE}</span>
        <a class="j2ha-goto-blocking" href="#" onclick="document.querySelector('tr[data-cmd-id=&quot;2971&quot;]').classList.add('j2ha-diag-target-highlight');return false;">Voir la première commande bloquée</a></div>
      <table class="j2ha-cmd-table"><tbody>
        <tr class="mapping-override-cmd" data-cmd-id="2971"><td class="mo-td-diag mo-diag-cell j2ha-diag-blocking" id="diag2971">Bloquée</td>
          <td class="mo-td-override" id="type2971"><a class="j2ha-type-link" id="link2971" href="#">auto</a><span id="rev2971"></span></td></tr>
      </tbody></table></div></div></div>`;
  return `<body><div id="j2ha_roomCards"><div class="j2ha-room-card" data-object_id="4" id="piece-4">Pièce</div></div>
    <script>
      window.__push = function (action, verdict) { window.__pushNode(action, verdict); };
      document.getElementById('piece-4').onclick = function () { document.body.insertAdjacentHTML('beforeend', ${JSON.stringify(modal)}); wire(); };
      function setReady(on) {
        var cell = document.getElementById('diag2971');
        cell.className = 'mo-td-diag mo-diag-cell ' + (on ? 'j2ha-diag-todo' : 'j2ha-diag-blocking');
        cell.textContent = on ? 'À appliquer → Interrupteur (switch)' : 'Bloquée';
        document.querySelector('.j2ha-eq-publish-badge').textContent = on ? ${JSON.stringify(READY_BADGE)} : ${JSON.stringify(INITIAL_BADGE)};
        document.getElementById('counters380').innerHTML = on
          ? '<span class="j2ha-eq-counter">1 à appliquer</span><span class="j2ha-eq-counter">1 ignorée</span>'
          : '<span class="j2ha-eq-counter">1 bloquée</span><span class="j2ha-eq-counter">1 ignorée</span>';
        document.getElementById('rev2971').innerHTML = on ? '<a class="mo-revert-cmd" href="#">↺</a>' : '';
        if (on) document.querySelector('.mo-revert-cmd').onclick = function () {
          window.__push('revertMappingOverride', 'simulee'); window.__push('getMappingOverrides', 'read'); setReady(false); return false;
        };
      }
      function wire() {
        // Le sélecteur n'existe qu'après un clic sur le lien « auto » de la colonne « Type HA ».
        document.getElementById('link2971').onclick = function () {
          var select = document.createElement('select');
          select.id = 'sel2971';
          select.innerHTML = ${JSON.stringify(options)};
          select.onchange = function () {
            window.__push('previewMappingOverride', 'apercu-simule'); window.__push('saveMappingOverride', 'simulee');
            window.__push('getMappingOverrides', 'lecture-derivee'); setReady(true);
          };
          document.getElementById('type2971').appendChild(select);
          return false;
        };
      }
    </script></body>`;
}

async function with380Page(t, fn, options) {
  const journal = [];
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
    await page.exposeFunction('__pushNode', (action, verdict) => { journal.push({ action, verdict }); });
    await page.setContent(html380(journal, options));
    const recorded = {};
    const { normalizeParcoursRecord } = await import(gate('lib', 'report.mjs'));
    const helpers = {
      record: (key, value) => {
        const [safeKey, safeValue] = normalizeParcoursRecord(key, value);
        assert.equal(Object.hasOwn(recorded, safeKey), false, `clé dupliquée ${safeKey}`);
        recorded[safeKey] = safeValue;
      },
      journalEntries: () => journal,
    };
    await fn(page, helpers, recorded);
  } finally {
    await browser.close();
  }
}

test('22.2 gate simulé — le parcours de référence 380 passe et n’enregistre aucune valeur que le rapport refuserait', async (t) => {
  assert.ok(LONG_CAUSE.length > 80, 'la cause simulée est aussi longue que la vraie');
  const parcours = await import(gate('parcours', 'reference-bascule-eq-380.mjs'));
  await with380Page(t, async (page, helpers, recorded) => {
    await parcours.run(page, { helpers });
    assert.equal(recorded.etape_a_cause_lisible, true);
    assert.equal(Object.hasOwn(recorded, 'etape_a_cause'), false);
    assert.equal(recorded.etape_a_types_proposes, 'cover');
    assert.equal(recorded.etape_b_cellule, 'a-appliquer');
    assert.equal(recorded.etape_c_cellule, 'bloquee');
    assert.equal(recorded.synthese_initiale, 'Bloqué');
    assert.equal(recorded.etape_b_synthese, 'À appliquer');
    assert.equal(recorded.compteurs_restitues, true);
  });
});

test('22.2 gate simulé — un type refusé encore proposé fait échouer le parcours 380', async (t) => {
  const parcours = await import(gate('parcours', 'reference-bascule-eq-380.mjs'));
  await with380Page(t, async (page, helpers) => {
    await assert.rejects(() => parcours.run(page, { helpers }), /type-refuse-encore-propose/);
  }, { sensorOffered: true });
});

test('22.2 gate simulé — le rapport refuse bien une observation de plus de 80 caractères (garde-fou du test)', async () => {
  const { normalizeParcoursRecord } = await import(gate('lib', 'report.mjs'));
  assert.throws(() => normalizeParcoursRecord('etape_a_cause', LONG_CAUSE), /parcours-record-valeur-invalide/);
  assert.deepEqual(normalizeParcoursRecord('etape_a_cause_lisible', true), ['etape_a_cause_lisible', true]);
});
