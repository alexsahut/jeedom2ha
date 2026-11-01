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

// Story 25.4 : la page simulée reproduit le DOM de la vue de travail C livrée — page principale (#j2ha_mainView), vue
// (#j2ha_workView) avec arbre (lignes de pièce et d'équipement, état dit par `.j2ha-state-word`) et détail (détail de
// pièce : KPI et actions ; détail d'équipement : panneau). Un clic sur une carte ouvre la vue, un clic sur une ligne
// affiche son détail, « Toutes les pièces » revient à la page.
function panel(id, name, state, badgeState, badgeText, options) {
  const badge = `<span class="j2ha-eq-publish-badge j2ha-badge j2ha-state-${badgeState}">${badgeText}</span>`;
  const menu = '<span class="j2ha-menu-wrap"><ul class="j2ha-menu"><li><button class="j2ha-eq-recreate">Supprimer de Home Assistant…</button></li></ul></span>';
  if (id === 579) {
    return `<div class="j2ha-eq-panel j2ha-eq-open" data-eq-id="${id}"><div class="j2ha-eq-head"><span class="j2ha-eq-name">${name}</span>${badge}</div>
    <div class="j2ha-eq-body">${multiEntityBody(id, options).replace('<div class="j2ha-eq-controls">' + SEG + '</div>', '<div class="j2ha-eq-controls">' + SEG + menu + '</div>')}</div></div>`;
  }
  return `<div class="j2ha-eq-panel j2ha-eq-open" data-eq-id="${id}"><div class="j2ha-eq-head"><span class="j2ha-eq-name">${name}</span>${badge}</div>
    <div class="j2ha-eq-body"><div class="j2ha-eq-controls">${SEG}${menu}</div>
      <table class="j2ha-cmd-table"><tbody><tr class="mapping-override-cmd" data-cmd-id="${id}1"><td class="mo-diag-cell ${state}">x</td></tr></tbody></table></div></div>`;
}

const stateWord = (state, text) => `<span class="j2ha-wv-state"><span class="j2ha-state-word j2ha-state-${state}">${text}</span></span>`;
const treeEq = (id, name, state, text) => `<li class="j2ha-wv-eq" data-eq-id="${id}"><div class="j2ha-wv-row">${stateWord(state, text)}<span class="j2ha-wv-name j2ha-free-name">${name}</span></div></li>`;

function html(withDiagnosticAction, titlePrefix = '', options = {}) {
  const room25 = `<div class="j2ha-wv-roomhead"><h2 class="j2ha-wv-title" tabindex="-1">${titlePrefix}<span class="j2ha-free-name">Pièce 25</span></h2>
    <div class="j2ha-room-actions"><button class="j2ha-room-republish">Republier</button><span class="j2ha-menu-wrap"><ul class="j2ha-menu"><li><button class="j2ha-room-recreate">Supprimer de Home Assistant…</button></li></ul></span></div></div>
    <div class="j2ha-wv-kpis">${counters([['published', '1 publié'], ['disabled', '1 désactivé']])}</div>`;
  const unassigned = `<div class="j2ha-wv-roomhead"><h2 class="j2ha-wv-title" tabindex="-1">Sans pièce</h2><div class="j2ha-room-actions"><span>Indisponible</span></div></div>
    <div class="j2ha-wv-kpis">${counters([['published', '1 publié']])}</div>`;
  const panels = { 579: panel(579, 'Eq-579', 'j2ha-diag-ready', 'published', 'Publié', options), 514: panel(514, 'Eq', 'j2ha-diag-disabled', 'disabled', 'Désactivé'), 7: panel(7, 'Sans', 'j2ha-diag-ready', 'published', 'Publié') };
  return `<body><div class="row"><div class="eqLogicThumbnailDisplay">
    <div class="eqLogicThumbnailContainer"><div class="eqLogicAction" data-action="gotoPluginConf">Configuration</div>
    ${withDiagnosticAction ? '<div class="eqLogicAction" data-action="diagnostic">Diagnostic</div>' : ''}</div>
    <div id="div_bridgeHealthBanner">Démon</div><button id="bt_exportDiagnostic">Télécharger le diagnostic support</button>
    <div id="j2ha_mainView"><div id="j2ha_roomCards"><div class="j2ha-room-card" data-object_id="0"><span class="name">Sans pièce</span><span class="text-muted"> (1)</span></div>
    <div class="j2ha-room-card" data-object_id="25" id="piece-25"><span class="name j2ha-free-name">Pièce 25</span><span class="text-muted"> (2)</span></div></div></div>
    <div id="j2ha_workView" class="j2ha-wv" style="display:none"><div class="j2ha-wv-bar"><button class="j2ha-wv-back">Toutes les pièces</button></div>
      <ul class="j2ha-wv-tree">
        <li class="j2ha-wv-room" data-object_id="25"><div class="j2ha-wv-row"><span class="j2ha-wv-name j2ha-free-name">Pièce 25</span></div><ul>${treeEq(579, 'Eq-579', 'published', 'Publié')}${treeEq(514, 'Eq', 'disabled', 'Désactivé')}</ul></li>
        <li class="j2ha-wv-room" data-object_id="0"><div class="j2ha-wv-row"><span class="j2ha-wv-name">Sans pièce</span></div><ul>${treeEq(7, 'Sans', 'published', 'Publié')}</ul></li>
      </ul>
      <div class="j2ha-wv-detail"><div class="j2ha-wv-pane"></div></div></div>
    <div class="eqLogic" style="display:none">Équipement</div></div></div>
    <script>
      var panes = { room25: ${JSON.stringify(room25)}, room0: ${JSON.stringify(unassigned)}, eq: ${JSON.stringify(panels)} };
      var view = document.getElementById('j2ha_workView');
      var pane = view.querySelector('.j2ha-wv-pane');
      function openView() { document.getElementById('j2ha_mainView').style.display = 'none'; view.style.display = 'block'; }
      document.querySelector('[data-object_id="25"].j2ha-room-card').onclick = function () { openView(); pane.innerHTML = panes.room25; };
      document.querySelector('[data-object_id="0"].j2ha-room-card').onclick = function () { openView(); pane.innerHTML = panes.room0; };
      view.querySelector('.j2ha-wv-back').onclick = function () { view.style.display = 'none'; document.getElementById('j2ha_mainView').style.display = 'block'; };
      view.querySelectorAll('.j2ha-wv-room > .j2ha-wv-row').forEach(function (row) {
        row.onclick = function () { pane.innerHTML = row.parentNode.getAttribute('data-object_id') === '25' ? panes.room25 : panes.room0; };
      });
      view.querySelectorAll('.j2ha-wv-eq > .j2ha-wv-row').forEach(function (row) {
        row.onclick = function () { pane.innerHTML = panes.eq[row.parentNode.getAttribute('data-eq-id')]; };
      });
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

test('20.3 gate simulé (R1-H) — un libellé statique interdit dans le détail de pièce (vue C) fait toujours échouer le parcours', async (t) => {
  const parcours = await import(gate('parcours', 'decouverte-piece-25-eq-579.mjs'));
  const content = html(false).replace('Republier</button>', 'Confiance mapping</button>');
  await withPage(t, content, [], async (page, helpers) => {
    await assert.rejects(() => parcours.run(page, { helpers }), /chaine-interdite-piece/);
  });
});

test('20.3 gate simulé (R2-6) — un libellé interdit dans le titre statique du détail de pièce (hors nom de pièce) fait échouer le parcours', async (t) => {
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
  // Story 25.4 : la fenêtre de pièce n'existe plus ; l'équipement est sélectionné dans l'arbre de la vue de travail.
  ui.openRoomWith(7, [ok(tree(287, [READY], { entities: [{
    ha_entity_type: 'light', command_ids: [28700], decision: READY, publication_override: null,
    override_command_id: 28700, override_pending: false, present_in_ha: true }] }))]);
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
  // Story 25.4 : vue de travail C — l'équipement 380 est une ligne de l'arbre ; son détail s'affiche à la sélection.
  const detail = `<div class="j2ha-eq-panel j2ha-eq-open" data-eq-id="380"><div class="j2ha-eq-head"><span class="j2ha-eq-name">Eq</span>
      <span class="j2ha-eq-publish-badge j2ha-badge">${INITIAL_BADGE}</span></div>
    <div class="j2ha-eq-body">
      <div class="j2ha-eq-counters"><div class="j2ha-eq-counter-line" id="counters380">
        <span class="j2ha-eq-counter">1 bloquée</span>
        <span class="j2ha-eq-counter">1 ignorée</span></div></div>
      <div class="j2ha-notice"><span class="j2ha-notice-text">${LONG_CAUSE}</span>
        <a class="j2ha-goto-blocking" href="#" onclick="document.querySelector('tr[data-cmd-id=&quot;2971&quot;]').classList.add('j2ha-diag-target-highlight');return false;">Voir la première commande bloquée</a></div>
      <table class="j2ha-cmd-table"><tbody>
        <tr class="mapping-override-cmd" data-cmd-id="2971"><td class="mo-td-diag mo-diag-cell j2ha-diag-blocking" id="diag2971">Bloquée</td>
          <td class="mo-td-override" id="type2971"><a class="j2ha-type-link" id="link2971" href="#">auto</a><span id="rev2971"></span></td></tr>
      </tbody></table></div></div>`;
  return `<body><div id="j2ha_mainView"><div id="j2ha_roomCards"><div class="j2ha-room-card" data-object_id="4" id="piece-4">Pièce</div></div></div>
    <div id="j2ha_workView" class="j2ha-wv" style="display:none"><div class="j2ha-wv-bar"><button class="j2ha-wv-back">Toutes les pièces</button></div>
      <ul class="j2ha-wv-tree"><li class="j2ha-wv-room" data-object_id="4"><div class="j2ha-wv-row">Pièce</div>
        <ul><li class="j2ha-wv-eq" data-eq-id="380"><div class="j2ha-wv-row"><span class="j2ha-wv-name j2ha-free-name">Eq</span></div></li></ul></li></ul>
      <div class="j2ha-wv-detail"><div class="j2ha-wv-pane"></div></div></div>
    <script>
      window.__push = function (action, verdict) { window.__pushNode(action, verdict); };
      var pane380 = document.querySelector('#j2ha_workView .j2ha-wv-pane');
      document.getElementById('piece-4').onclick = function () { document.getElementById('j2ha_mainView').style.display = 'none'; document.getElementById('j2ha_workView').style.display = 'block'; };
      document.querySelector('.j2ha-wv-eq[data-eq-id="380"] .j2ha-wv-row').onclick = function () { pane380.innerHTML = ${JSON.stringify(detail)}; wire(); };
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

// --- Story 24.11 (AC3) : parcours exclusion-publication-non-publiee à cible choisie à l'exécution ---
// Page simulée de la vue de travail C : cartes de pièce, arbre de la pièce ouverte (mot d'état par ligne), détail
// d'équipement rendu à la sélection (contrôle segmenté, en-têtes de groupe, commandes). Le journal de l'intercepteur
// est simulé par les gestionnaires de la page. `declareTarget` est un double qui consigne ses appels.

function htmlDynamic(rooms) {
  const cards = rooms.map((room) => `<div class="j2ha-room-card" data-object_id="${room.objectId}">Pièce</div>`).join('');
  return `<body><div id="j2ha_mainView"><div id="j2ha_roomCards">${cards}</div></div>
    <div id="j2ha_workView" class="j2ha-wv" style="display:none"><div class="j2ha-wv-bar"><button class="j2ha-wv-back">Toutes les pièces</button></div>
      <ul class="j2ha-wv-tree"></ul><div class="j2ha-wv-detail"><div class="j2ha-wv-pane"></div></div></div>
    <script>
      var rooms = ${JSON.stringify(rooms)};
      var policy = {};
      var view = document.getElementById('j2ha_workView');
      var tree = view.querySelector('.j2ha-wv-tree');
      var pane = view.querySelector('.j2ha-wv-pane');
      function push(action, verdict) { window.__pushNode(action, verdict); }
      function seg(eq) {
        return '<span class="j2ha-seg" role="radiogroup">' + ['Automatique', 'Toujours', 'Jamais'].map(function (label) {
          return '<button class="j2ha-seg-btn" role="radio" aria-checked="' + (policy[eq.id] === label) + '">' + label + '</button>';
        }).join('') + '</span>';
      }
      function renderPanel(eq) {
        var cmds = '';
        if (eq.groupHead) cmds += '<tr class="j2ha-group-head"><td>Groupe</td></tr>';
        for (var i = 0; i < eq.cmds; i += 1) cmds += '<tr class="mapping-override-cmd" data-cmd-id="' + eq.id + i + '"><td>x</td></tr>';
        pane.innerHTML = '<div class="j2ha-eq-panel j2ha-eq-open" data-eq-id="' + eq.id + '"><div class="j2ha-eq-body">'
          + '<div class="j2ha-eq-counters"><span class="j2ha-eq-counter">1 bloquée</span></div>'
          + '<div class="j2ha-eq-controls">' + seg(eq) + '</div>'
          + '<table class="j2ha-cmd-table"><tbody>' + cmds + '</tbody></table></div></div>';
        pane.querySelectorAll('.j2ha-eq-controls .j2ha-seg-btn').forEach(function (button) {
          button.onclick = function () {
            var label = button.textContent;
            if (label === 'Jamais') { push('savePublicationOverride', 'simulee'); push('getMappingOverrides', 'lecture-derivee'); }
            if (label === 'Automatique') { push('revertPublicationOverride', 'simulee'); push('getMappingOverrides', 'read'); }
            policy[eq.id] = label;
            renderPanel(eq);
          };
        });
      }
      function openRoom(room) {
        document.getElementById('j2ha_mainView').style.display = 'none';
        view.style.display = 'block';
        pane.innerHTML = '';
        tree.innerHTML = '<li class="j2ha-wv-room" data-object_id="' + room.objectId + '"><div class="j2ha-wv-row">Pièce</div><ul>'
          + room.eqs.map(function (eq) {
            return '<li class="j2ha-wv-eq' + (eq.disabled ? ' j2ha-wv-eq-disabled' : '') + '" data-eq-id="' + eq.id + '"><div class="j2ha-wv-row">'
              + '<span class="j2ha-wv-state"><span class="j2ha-state-word j2ha-state-' + eq.state + '">x</span></span></div></li>';
          }).join('') + '</ul></li>';
        tree.querySelectorAll('.j2ha-wv-eq > .j2ha-wv-row').forEach(function (row) {
          row.onclick = function () {
            push('getMappingOverrides', 'read');
            var id = Number(row.parentNode.getAttribute('data-eq-id'));
            renderPanel(room.eqs.find(function (eq) { return eq.id === id; }));
          };
        });
      }
      rooms.forEach(function (room) { room.eqs.forEach(function (eq) { policy[eq.id] = eq.seg || 'Automatique'; }); });
      document.querySelectorAll('.j2ha-room-card').forEach(function (card) {
        card.onclick = function () { openRoom(rooms.find(function (room) { return String(room.objectId) === card.getAttribute('data-object_id'); })); };
      });
      view.querySelector('.j2ha-wv-back').onclick = function () { view.style.display = 'none'; document.getElementById('j2ha_mainView').style.display = 'block'; };
    </script></body>`;
}

const eligible = (id, extra = {}) => ({ id, state: 'blocked', cmds: 1, ...extra });

async function withDynamicPage(t, rooms, fn) {
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
    const journal = [];
    const page = await browser.newPage();
    await page.exposeFunction('__pushNode', (action, verdict) => { journal.push({ action, verdict }); });
    await page.setContent(htmlDynamic(rooms));
    const recorded = {};
    const declared = [];
    const { normalizeParcoursRecord } = await import(gate('lib', 'report.mjs'));
    const record = (key, value) => {
      const [safeKey, safeValue] = normalizeParcoursRecord(key, value);
      assert.equal(Object.hasOwn(recorded, safeKey), false, `clé dupliquée ${safeKey}`);
      recorded[safeKey] = safeValue;
    };
    const helpers = {
      record,
      journalEntries: () => journal,
      // Double de `helpers.declareTarget` : consigne l'id et l'état du journal au moment de l'appel.
      declareTarget: (eqId) => {
        declared.push({ eqId, writesBefore: journal.filter((entry) => entry.verdict === 'simulee').length });
        record('cible', eqId);
      },
    };
    await fn(page, helpers, { recorded, declared, journal });
  } finally {
    await browser.close();
  }
}

test('24.11 gate simulé — le parcours retient la PREMIÈRE cible éligible, jamais 287, et la déclare avant toute écriture', async (t) => {
  const parcours = await import(gate('parcours', 'exclusion-publication-non-publiee.mjs'));
  const rooms = [
    { objectId: 25, eqs: [
      eligible(287), // sans réglage et éligible par ailleurs : exclu en permanence
      eligible(101, { state: 'published' }), // ligne publiée
      eligible(102, { seg: 'Toujours' }), // réglage enregistré
      eligible(103, { groupHead: true }), // plusieurs entités
      eligible(104, { state: 'nothing_to_publish', cmds: 0 }), // aucune commande
      eligible(105, { state: 'to_apply' }), // à appliquer : écarté
      eligible(106, { disabled: true }), // désactivé dans Jeedom
    ] },
    { objectId: 4, eqs: [eligible(201, { state: 'nothing_to_publish' }), eligible(202)] },
  ];
  await withDynamicPage(t, rooms, async (page, helpers, { recorded, declared, journal }) => {
    await parcours.run(page, { helpers });
    assert.deepEqual(declared, [{ eqId: '201', writesBefore: 0 }]);
    assert.equal(recorded.cible, '201');
    assert.equal(recorded.eq_cible_compteur_1, '1 bloquée');
    assert.equal(recorded.actions_entite_masquees, true);
    assert.equal(recorded.etape_12, 'etat-bouton-final');
    // Aucune écriture simulée ne vise un autre équipement que la cible (une seule exclusion, un seul retrait).
    assert.deepEqual(journal.filter((entry) => entry.verdict === 'simulee').map((entry) => entry.action),
      ['savePublicationOverride', 'revertPublicationOverride']);
  });
});

test('24.11 gate simulé — dans la pièce connue, la première ligne éligible de l’arbre est retenue', async (t) => {
  const parcours = await import(gate('parcours', 'exclusion-publication-non-publiee.mjs'));
  const rooms = [
    { objectId: 4, eqs: [eligible(401)] },
    { objectId: 25, eqs: [eligible(251, { state: 'excluded' }), eligible(252), eligible(253)] },
  ];
  await withDynamicPage(t, rooms, async (page, helpers, { recorded, declared }) => {
    await parcours.run(page, { helpers });
    assert.deepEqual(declared.map((entry) => entry.eqId), ['252']);
    assert.equal(recorded.etape_1, 'ouverture-piece-connue');
    assert.equal(Object.hasOwn(recorded, 'etape_2'), false);
  });
});

test('24.11 gate simulé — l’eq 287 n’est jamais retenu, même seul éligible : échec aucune-cible-eligible', async (t) => {
  const parcours = await import(gate('parcours', 'exclusion-publication-non-publiee.mjs'));
  assert.deepEqual(parcours.EXCLUDED_TARGETS, ['287']);
  await withDynamicPage(t, [{ objectId: 25, eqs: [eligible(287)] }, { objectId: 7, eqs: [eligible(287)] }], async (page, helpers, { declared, journal }) => {
    await assert.rejects(() => parcours.run(page, { helpers }), /aucune-cible-eligible/);
    assert.deepEqual(declared, []);
    assert.deepEqual(journal.filter((entry) => entry.verdict === 'simulee'), []);
  });
});

test('24.11 gate simulé — aucune ligne éligible : échec explicite aucune-cible-eligible, sans déclaration ni écriture', async (t) => {
  const parcours = await import(gate('parcours', 'exclusion-publication-non-publiee.mjs'));
  const rooms = [
    { objectId: 3, eqs: [eligible(31, { state: 'published' }), eligible(32, { seg: 'Jamais' }), eligible(33, { groupHead: true })] },
    { objectId: 5, eqs: [eligible(51, { cmds: 0 }), eligible(52, { state: 'disabled' })] },
  ];
  await withDynamicPage(t, rooms, async (page, helpers, { declared, journal }) => {
    await assert.rejects(() => parcours.run(page, { helpers }), /aucune-cible-eligible/);
    assert.deepEqual(declared, []);
    assert.deepEqual(journal.filter((entry) => entry.verdict === 'simulee'), []);
  });
});
