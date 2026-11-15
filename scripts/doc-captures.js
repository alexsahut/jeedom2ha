#!/usr/bin/env node
'use strict';
/*
 * Captures de la documentation (docs/fr_FR/images/) rendues dans le banc réel, sans box : vrai Chromium (Playwright), vrai
 * jQuery, vrai squelette PHP, vrais CSS et JS du plugin (tests/unit/helpers/workview_browser.js). Seul le réseau est simulé.
 *
 * Données FICTIVES (CC-48) : maison, pièces, équipements, scénarios et plugins inventés ; aucune adresse, aucun nom réel,
 * aucune marque. Thème clair, 1280 px de large, comme le storyboard de la story 23.2.
 *
 * Usage : node scripts/doc-captures.js [--out <dossier>] [--only nom1,nom2]
 *   --out   dossier de sortie (défaut : docs/fr_FR/images)
 *   --only  noms de captures à régénérer (sans .png)
 * Prérequis : ceux des tests de rendu réel (PHP, jQuery, Playwright ; voir workview_browser.js). Font Awesome est cherché dans
 * JEEDOM2HA_FONTAWESOME, puis dans node_modules ; sans lui, les icônes sont absentes (la box les fournit par le cœur).
 *
 * La capture « home-assistant-appareils.png » vient de Home Assistant : elle n'est pas produite ici
 * (tests/e2e/captures/run-captures.mjs, sur la VM de démo).
 */

const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const ROOT = path.join(__dirname, '..');
const H = (p) => require(path.join(ROOT, 'tests/unit/helpers', p));
const { withRealView, JQUERY } = H('workview_browser.js');
const { FIXTURE, clone } = H('page_b_harness.js');
const { DEMO } = H('front_v2_demo_trees.js');
const C = H('core_css_reel.js');

const args = process.argv.slice(2);
const argOf = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : null; };
const OUT = path.resolve(argOf('--out') || path.join(ROOT, 'docs/fr_FR/images'));
const ONLY = argOf('--only') ? argOf('--only').split(',') : null;
const WIDTH = 1280;
fs.mkdirSync(OUT, { recursive: true });

// --- Font Awesome local (aucun CDN) : polices embarquées en data URI.
function fontAwesomeCss() {
  const dirs = [process.env.JEEDOM2HA_FONTAWESOME, '/opt/npm-tools/node_modules/@fortawesome/fontawesome-free'];
  try { dirs.push(path.dirname(path.dirname(require.resolve('@fortawesome/fontawesome-free/css/all.min.css')))); } catch (e) { /* absent */ }
  const dir = dirs.filter(Boolean).find((d) => fs.existsSync(path.join(d, 'css/all.min.css')));
  if (!dir) { console.warn('Font Awesome introuvable : icônes absentes des captures.'); return ''; }
  return fs.readFileSync(path.join(dir, 'css/all.min.css'), 'utf8').replace(/url\(\.\.\/webfonts\/([a-z0-9-]+\.woff2)\)/g,
    (m, f) => 'url(data:font/woff2;base64,' + fs.readFileSync(path.join(dir, 'webfonts', f)).toString('base64') + ')');
}
const FA = fontAwesomeCss();

// --- Base Bootstrap minimale (le banc ne charge qu'un extrait du cœur) et thème clair du cœur.
const BASE = `
body { font-family: Roboto, "Segoe UI", Arial, sans-serif; font-size: 13px; margin: 0; padding: 12px 16px; line-height: 1.42857; }
legend { font-size: 17px; border-bottom: 1px solid var(--j2ha-line); padding-bottom: 4px; margin: 14px 0 10px; width: 100%; }
.label { display: inline; padding: .2em .6em .3em; font-size: 75%; font-weight: 700; color: #fff; border-radius: .25em; }
.btn { display: inline-block; cursor: pointer; } .btn-xs { height: auto; padding: 1px 5px; font-size: 12px; }
.text-muted { opacity: .75; } .table { width: 100%; border-collapse: collapse; } .table td, .table th { padding: 5px; border-top: 1px solid var(--j2ha-line); text-align: left; }
.bootbox.modal { position: fixed; left: 50%; top: 40px; transform: translateX(-50%); width: 760px; max-height: calc(100% - 80px); overflow: auto; background: rgb(245,245,245); border: 1px solid var(--j2ha-line); box-shadow: 0 10px 40px rgba(0,0,0,.4); z-index: 1000; padding: 0; }
.bootbox .modal-title { font-size: 16px; font-weight: 700; padding: 12px 16px; border-bottom: 1px solid var(--j2ha-line); }
.bootbox .bootbox-body { padding: 12px 16px; } .bootbox .modal-footer { padding: 10px 16px; border-top: 1px solid var(--j2ha-line); text-align: right; }
.cursor { cursor: pointer; } .logoSecondary { text-align: center; width: 110px; padding: 10px; }
:root { --txt-color: #333; --btn-default-color: #e8e8e8; --linkHoverLight-color: #333; --link-color: #2a7fb8; --bg-color: 245,245,245; --form-bg-color: #fff; }
body { background: #f5f5f5; color: #333; }
`;

// --- Maison fictive : deux niveaux, sept pièces.
const SCENE = {
  objects: [
    { id: 1, name: 'Maison', father_id: null, display: {} },
    { id: 2, name: 'Rez-de-chaussée', father_id: 1, display: {} },
    { id: 3, name: 'Séjour', father_id: 2, display: { icon: '<i class="fas fa-couch"></i>' } },
    { id: 4, name: 'Cuisine', father_id: 2, display: { icon: '<i class="fas fa-utensils"></i>' } },
    { id: 9, name: 'Bureau', father_id: 2, display: { icon: '<i class="fas fa-desktop"></i>' } },
    { id: 6, name: 'Étage', father_id: 1, display: {} },
    { id: 7, name: 'Chambre', father_id: 6, display: { icon: '<i class="fas fa-bed"></i>' } },
    { id: 8, name: 'Salle de bain', father_id: 6, display: { icon: '<i class="fas fa-bath"></i>' } },
    { id: 10, name: 'Jardin', father_id: 1, display: { icon: '<i class="fas fa-tree"></i>' } },
  ],
  eqlogics: {
    3: [{ id: 301, name: 'Plafonnier' }, { id: 302, name: 'Lampadaire' }, { id: 303, name: 'Volet baie' }, { id: 304, name: 'Thermomètre' }],
    4: [{ id: 401, name: 'Spots' }, { id: 402, name: 'Prise four' }, { id: 403, name: 'Détecteur fumée', enabled: false }],
    9: [{ id: 142, name: 'Multiprise Bureau' }, { id: 150, name: 'Portail' }, { id: 160, name: 'Ventilateur Chambre' },
      { id: 231, name: 'Lampe Chevet' }, { id: 300, name: 'Capteur Atelier' }, { id: 200, name: 'Plafonnier Séjour' }],
    7: [{ id: 701, name: 'Lampe lecture' }, { id: 702, name: 'Volet' }, { id: 703, name: 'Présence' }],
    8: [{ id: 801, name: 'Sèche-serviettes' }, { id: 802, name: 'Hygrométrie' }],
    10: [{ id: 1001, name: 'Arrosage', type: 'plugin_alpha' }, { id: 1002, name: 'Éclairage allée' }, { id: 1003, name: 'Station météo', type: 'plugin_alpha' }],
  },
  plugin_names: { plugin_alpha: 'Passerelle Alpha', virtual: 'Virtuel' },
  doc: 'https://doc.example.test/jeedom2ha/index.md',
};

// Plugin fictif ou virtuel pour chaque équipement (le faux cœur donne sinon un plugin réel par défaut).
Object.values(SCENE.eqlogics).flat().forEach((eq) => { if (!eq.type) eq.type = 'virtual'; });

// États : la démo du front v2 pour le Bureau, des fixtures 25.2 pour le reste (publiés en majorité, quelques cas à traiter).
const FIX = { 301: '101', 302: '101', 303: '101', 304: '101', 401: '101', 402: '102', 403: '101', 701: '101', 702: '105',
  703: '101', 801: '101', 802: '101', 1001: '110', 1002: '101', 1003: '110' };
const DEMO_BY_ID = {};
Object.values(DEMO).forEach((make) => { const t = make(true); DEMO_BY_ID[t.jeedom_eq_id] = t; });
const equipments = {};
const trees = {};
Object.values(SCENE.eqlogics).flat().forEach((eq) => {
  if (DEMO_BY_ID[eq.id]) { const t = clone(DEMO_BY_ID[eq.id]); equipments[String(eq.id)] = t; trees[eq.id] = t; return; }
  const k = FIX[eq.id] || '101';
  const agg = clone(FIXTURE[k].aggregated); agg.jeedom_eq_id = eq.id;
  const tree = clone(FIXTURE[k].tree); tree.jeedom_eq_id = eq.id; tree.eq_name = eq.name;
  equipments[String(eq.id)] = agg; trees[eq.id] = tree;
});
// « Lampe Chevet » : une lampe branchée sur une prise ; le type « Lumière » est permis pour « Corriger le type ».
trees[231].commands.forEach((c) => { c.override_types_allowed = ['light', 'switch']; });
const treeFor = (id) => ({ state: 'ok', result: { status: 'ok', payload: trees[id] || clone(FIXTURE['101'].tree) } });

// --- Scénarios fictifs (onglet « Scénarios »).
const sc = (id, name, extra) => Object.assign({ id, name, group: '', mode: 'provoke', has_trigger: false, has_schedule: false, manual: true,
  is_active: true, published: false, is_new: false, in_ha: false, ha_entity_id: null }, extra);
const pub = (id) => ({ published: true, in_ha: true, ha_entity_id: `button.jeedom2ha_scenario_${id}` });
const SCHEDULED = { mode: 'schedule', has_schedule: true, manual: false };
const SCENARIOS = [
  sc(12, 'Tout éteindre', Object.assign({ group: 'Ambiances' }, pub(12))),
  sc(31, 'Réveil semaine', Object.assign({ group: 'Matin' }, SCHEDULED, pub(31))),
  sc(40, 'Mode vacances', Object.assign({ group: 'Absence', is_active: false }, pub(40))),
  sc(51, 'Arrosage nuit', Object.assign({ group: 'Jardin', is_new: true }, SCHEDULED)),
  sc(52, 'Bonne nuit', { group: 'Ambiances', is_new: true }),
  sc(60, 'Purge journaux', Object.assign({ group: 'Technique' }, SCHEDULED)),
  sc(61, 'Alerte fumée', { group: 'Sécurité', is_new: true, has_trigger: true, manual: false, mode: 'provoke' }),
  sc(62, 'Cinéma', { group: 'Ambiances' }),
];

// --- État du démon : tout tourne, Home Assistant vu, relecture réussie il y a 20 minutes.
function bridgeStatus() {
  const relu = new Date(Date.now() - 20 * 60 * 1000).toISOString();
  return {
    daemon: true, broker: { state: 'connected', broker: '' },
    derniere_synchro_terminee: relu,
    derniere_operation_resultat: { resultat: 'succes', intention: 'sync', portee: 'global', message: 'Synchronisation terminée.', timestamp: relu },
    ha: { birth_seen_at: relu },
    publication: { scenarios_published: SCENARIOS.filter((s) => s.published).length },
    scenarios: SCENARIOS,
  };
}

// Aperçu de « Corriger le type » : prise → lumière, identifiant modifié.
const PREVIEW = { state: 'ok', result: { status: 'ok', payload: { jeedom_eq_id: 231, mapped: true, covered: true,
  overridden: { ha_entity_type: 'light', projection_validity: { is_valid: true, reason_code: null, missing_capabilities: [], missing_fields: [] }, should_publish: true, publication_reason: 'sure', confidence: 'sure' },
  entities_before: [{ ha_entity_type: 'switch', ha_default_entity_id: 'switch.jeedom2ha_eq_231', ha_controllable: true, ha_capabilities: ['on_off'], will_publish: true }],
  entities_after: [{ ha_entity_type: 'light', ha_default_entity_id: 'light.jeedom2ha_eq_231', ha_controllable: true, ha_capabilities: ['on_off'], will_publish: true }],
  entity_id_changes: [{ from: 'switch.jeedom2ha_eq_231', to: 'light.jeedom2ha_eq_231' }] } } };

const t = { skip: (m) => { throw new Error('banc indisponible : ' + m); } };
const opts = (extra) => Object.assign({ scene: SCENE, equipments, treeFor, width: WIDTH, height: 760, bridgeStatus,
  extraCss: FA + BASE,
  respond: (action) => (action === 'previewMappingOverride' ? PREVIEW : undefined) }, extra || {});

async function settle(page, ms) {
  await page.evaluate(() => document.body.setAttribute('data-theme', 'core2019_Light'));
  await page.waitForTimeout(ms || 600);
  // Le guide s'ouvre seul tant que rien n'est publié : on le ferme pour les captures qui ne le montrent pas.
  await page.evaluate(() => { const g = document.querySelector('#j2ha_v2_guide'); if (g) g.style.display = 'none'; });
}
async function noOverflow(page, name) {
  const ovf = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  if (ovf) throw new Error(`${name} : débordement horizontal`);
}
const file = (name) => path.join(OUT, name + '.png');
// Pleine page bornée à 2000 px, comme le storyboard 23.2.
async function fullPage(page, name) {
  const h = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewportSize({ width: WIDTH, height: Math.min(Math.max(h, 720), 2000) });
  await page.screenshot({ path: file(name) });
}
// Un élément, ou la zone qui couvre plusieurs éléments, avec une marge.
async function region(page, name, selectors, pad) {
  const p = pad === undefined ? 8 : pad;
  const boxes = [];
  for (const s of selectors) { const b = await page.locator(s).first().boundingBox(); if (b) boxes.push(b); }
  if (!boxes.length) throw new Error(`${name} : rien à capturer (${selectors.join(', ')})`);
  const x = Math.max(0, Math.min(...boxes.map((b) => b.x)) - p);
  const y = Math.max(0, Math.min(...boxes.map((b) => b.y)) - p);
  const right = Math.min(WIDTH, Math.max(...boxes.map((b) => b.x + b.width)) + p);
  const bottom = Math.max(...boxes.map((b) => b.y + b.height)) + p;
  const vh = page.viewportSize().height;
  if (bottom > vh) await page.setViewportSize({ width: WIDTH, height: Math.ceil(bottom) + 10 });
  await page.screenshot({ path: file(name), clip: { x, y, width: right - x, height: bottom - y } });
}
// Une boîte (bootbox) rendue en place, capturée seule.
async function dialog(page, name) {
  await page.evaluate(() => { const b = document.querySelector('.bootbox:last-of-type'); b.style.cssText += ';position:static;transform:none;margin:0 auto;max-height:none;'; window.scrollTo(0, 0); });
  const h = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewportSize({ width: WIDTH, height: Math.min(h + 20, 2000) });
  await page.locator('.bootbox').last().screenshot({ path: file(name) });
}

// --- Les captures : nom de fichier (sans .png) → parcours.
const SHOTS = {
  // Page maison entière : barre d'état, onglets, chiffre de la maison, puces, « À faire », tuiles de pièce.
  'page-principale': { hash: '', run: async (page) => { await settle(page, 900); await fullPage(page, 'page-principale'); } },
  // Barre d'état, menu ⋯ ouvert.
  'barre-etat': { hash: '', run: async (page) => {
    await settle(page, 900);
    await page.locator('#j2ha_moreMenu .j2ha-menu-toggle').first().click();
    await page.waitForTimeout(200);
    await region(page, 'barre-etat', ['#div_bridgeHealthBanner', '#j2ha_moreMenu .j2ha-menu']);
  } },
  // Puce « Bloqués » : la liste « À faire » et la grille filtrée.
  'a-faire': { hash: '', run: async (page) => {
    await settle(page, 900);
    await page.locator('.j2ha-chip-filter[data-filter="blocked"]').first().click();
    await page.waitForTimeout(300);
    await region(page, 'a-faire', ['#j2ha_houseBlock', '#j2ha_v2_todo']);
  } },
  // Tuiles de pièce.
  'cartes-de-piece': { hash: '', run: async (page) => { await settle(page, 900); await region(page, 'cartes-de-piece', ['#j2ha_roomCards']); } },
  // Vue d'une pièce : fil d'Ariane, arbre de la maison, fiche d'un équipement publié.
  'vue-de-travail': { hash: '#j2ha-vue=piece:9;eq:200', run: async (page) => {
    await settle(page, 1200);
    await page.screenshot({ path: file('vue-de-travail') });
  } },
  // Fiche d'un équipement bloqué : en-tête, bande de cause.
  'detail-equipement': { hash: '#j2ha-vue=piece:9;eq:231', run: async (page) => {
    await settle(page, 1200);
    await region(page, 'detail-equipement', ['.j2ha-eq-panel[data-eq-id="231"]']);
  } },
  // Fiche d'une multiprise : bloc « Dans Home Assistant » et tableau des commandes.
  'tableau-des-commandes': { hash: '#j2ha-vue=piece:9;eq:142', run: async (page) => {
    await settle(page, 1200);
    await region(page, 'tableau-des-commandes', ['.j2ha-eq-panel[data-eq-id="142"]']);
  } },
  // « Corriger le type » : aperçu avant / après.
  'corriger-le-type': { hash: '#j2ha-vue=piece:9;eq:231', run: async (page) => {
    await settle(page, 1200);
    const P = '.j2ha-eq-panel[data-eq-id="231"]';
    await page.locator(`${P} .j2ha-cmd-table .j2ha-type-link`).first().click();
    await page.locator('.j2ha-v2-type-panel').first().waitFor();
    await page.locator('.j2ha-v2-type-panel input[data-type="light"]').first().check();
    await page.waitForTimeout(900);
    await page.screenshot({ path: file('corriger-le-type') });
  } },
  // « Choisir ce qui est publié » : une pièce dépliée, un équipement décoché.
  'choisir-ce-qui-est-publie': { hash: '', run: async (page) => {
    await settle(page, 900);
    await page.evaluate(() => window.jQuery('#bt_j2haChoosePublished').trigger('click'));
    const panel = page.locator('.bootbox').last();
    await panel.locator('.j2ha-v2-excl').waitFor();
    const tw = panel.locator('.j2ha-v2-excl-group[data-kind="room"][data-id="9"] .j2ha-v2-excl-twisty');
    if (await tw.count()) await tw.click();
    const eq = panel.locator('.j2ha-v2-excl-eq[data-eq-id="160"] .j2ha-v2-excl-cb');
    if (await eq.count()) await eq.uncheck();
    await page.waitForTimeout(300);
    await dialog(page, 'choisir-ce-qui-est-publie');
  } },
  // Onglet « Scénarios ».
  scenarios: { hash: '', run: async (page) => {
    await settle(page, 900);
    await page.click('#j2ha_tabBtnScenarios');
    await page.waitForTimeout(300);
    await fullPage(page, 'scenarios');
  } },
  // « Vérifier l'installation », « Avancé » déplié.
  'verifier-installation': { hash: '', run: async (page) => {
    await settle(page, 900);
    await page.evaluate(() => window.jQuery('#bt_j2haCheckInstall').trigger('click'));
    const check = page.locator('.bootbox').last();
    await check.locator('.j2ha-v2-checkbox').waitFor();
    await page.waitForTimeout(400);
    await check.locator('.j2ha-v2-check-advanced').click();
    await page.waitForTimeout(200);
    await dialog(page, 'verifier-installation');
  } },
  // Guide de démarrage (installation neuve : rien n'est encore relu).
  'guide-demarrage': { hash: '', status: () => ({ daemon: true, broker: { state: 'connected', broker: '' }, derniere_operation_resultat: 'aucun', scenarios: SCENARIOS.map((s) => Object.assign({}, s, { published: false, in_ha: false, ha_entity_id: null, is_new: true })) }),
    run: async (page) => {
      await page.evaluate(() => { window.localStorage.clear(); window.jQuery('#bt_j2haOpenGuide').trigger('click'); });
      await page.locator('#j2ha_v2_guide .j2ha-v2-step').first().waitFor();
      await page.waitForTimeout(500);
      await region(page, 'guide-demarrage', ['#j2ha_v2_guide'], 12);
    } },
  // compteurs.md : la vue d'une pièce avec ses compteurs, et la ligne d'un équipement bloqué.
  'compteurs-detail-piece': { hash: '#j2ha-vue=piece:9', run: async (page) => {
    await settle(page, 1200);
    await page.screenshot({ path: file('compteurs-detail-piece') });
  } },
  'compteurs-equipement-deplie': { hash: '#j2ha-vue=piece:9;eq:300', run: async (page) => {
    await settle(page, 1200);
    await region(page, 'compteurs-equipement-deplie', ['.j2ha-eq-panel[data-eq-id="300"]']);
  } },
};

// Configuration du plugin : page à part (plugin_info/configuration.php rendue par le banc, comme les tests de la configuration).
async function configuration() {
  const { loadPlaywright } = await import(pathToFileURL(path.join(ROOT, 'tests/e2e/gate/lib/playwright.mjs')).href);
  const { chromium } = loadPlaywright();
  const fixture = C.configFixture();
  const html = C.renderConfiguration(fixture).replace(/\{\{([^}]*)\}\}/g, '$1');
  const CFG = `.form-group { margin-bottom: 12px; overflow: hidden; } .control-label { font-weight: 700; text-align: right; padding-top: 7px; }
.col-md-4 { width: 33%; float: left; padding: 0 12px; box-sizing: border-box; } .col-md-6 { width: 50%; float: left; padding: 0 12px; box-sizing: border-box; } .col-md-offset-4 { margin-left: 33%; }
.form-control { display: block; width: 100%; padding: 6px 10px; box-sizing: border-box; border: 1px solid rgba(128,128,128,.5); background: var(--form-bg-color); color: inherit; }
.help-block { opacity: .75; } .btn-primary { background: #3c8dbc; border-color: #367fa9; color: #fff; } .text-warning { color: #8a6d3b; } fieldset { border: 0; } .alert { padding: 10px 14px; border: 1px solid rgba(128,128,128,.4); margin: 8px 0; }`;
  const browser = await chromium.launch();
  try {
    const page = await (await browser.newContext({ viewport: { width: WIDTH, height: 720 } })).newPage();
    await page.route('http://cfg.test/**', async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname === '/') {
        await route.fulfill({ contentType: 'text/html', body: `<!doctype html><html><head><meta charset="utf-8"><style>${C.CORE_CSS}${FA}${BASE}${CFG}</style>`
          + `<script src="/jq.js"></script></head><body data-theme="core2019_Light"><div id="div_plugin_configuration">${html}</div></body></html>` });
        return;
      }
      if (url.pathname === '/jq.js') { await route.fulfill({ contentType: 'application/javascript', body: fs.readFileSync(JQUERY, 'utf8') }); return; }
      await route.fulfill({ contentType: 'application/json', body: '{"state":"ok","result":{"source":"manual","has_password":true}}' });
    });
    await page.goto('http://cfg.test/');
    await page.waitForTimeout(400);
    // CC-48 : aucun hôte ni identifiant, même fictif, dans la capture.
    await page.evaluate(() => {
      document.querySelectorAll('input[type="text"], input[type="password"], input:not([type])').forEach((i) => { i.value = ''; i.removeAttribute('placeholder'); });
      document.querySelectorAll('details').forEach((d) => { d.open = true; });
    });
    await page.screenshot({ path: file('configuration'), fullPage: true });
  } finally { await browser.close(); }
}

(async () => {
  const log = [];
  for (const [name, shot] of Object.entries(SHOTS)) {
    if (ONLY && !ONLY.includes(name)) continue;
    try {
      await withRealView(t, opts({ hash: shot.hash, bridgeStatus: shot.status || bridgeStatus }), async (page, ctx) => {
        await shot.run(page);
        await noOverflow(page, name);
        if (ctx.errors.length) throw new Error('erreurs JS : ' + ctx.errors.join(' | '));
      });
      log.push(`${name}.png : ok`);
    } catch (e) { log.push(`${name}.png : ÉCHEC ${e.message.split('\n')[0]}`); process.exitCode = 1; }
  }
  if (!ONLY || ONLY.includes('configuration')) {
    try { await configuration(); log.push('configuration.png : ok'); } catch (e) { log.push('configuration.png : ÉCHEC ' + e.message.split('\n')[0]); process.exitCode = 1; }
  }
  if (OUT === path.join(ROOT, 'docs/fr_FR/images') && !process.exitCode) await updateManifest(log);
  console.log(log.join('\n'));
})();

// Manifeste des captures (story 23.2) : empreinte et taille de chaque capture régénérée ici ; les autres entrées (capture Home
// Assistant, vidéo) restent celles de leur outil. Aucune URL, aucun identifiant (assertManifestClean).
async function updateManifest(log) {
  const { sha256, assertManifestClean } = await import(pathToFileURL(path.join(ROOT, 'tests/e2e/captures/lib/safety.mjs')).href);
  const file = path.join(OUT, 'captures-manifest.json');
  const manifest = JSON.parse(fs.readFileSync(file, 'utf8'));
  const done = log.filter((l) => / : ok$/.test(l)).map((l) => l.split(' : ')[0]);
  const { execSync } = require('node:child_process');
  let commit = null;
  try { commit = execSync('git rev-parse --short HEAD', { cwd: ROOT }).toString().trim(); } catch (e) { commit = null; }
  const generated = { tool: 'scripts/doc-captures.js', data: 'banc réel, données fictives (CC-48)', source_commit: commit,
    generated_on: new Date().toISOString().slice(0, 10), width: WIDTH };
  for (const name of done) {
    const buf = fs.readFileSync(path.join(OUT, name));
    const entry = manifest.files.find((f) => f.file === name);
    const data = { sha256: sha256(buf), bytes: buf.length, generated };
    if (entry) Object.assign(entry, data);
    else manifest.files.push(Object.assign({ id: name.replace(/\.png$/, ''), file: name }, data));
  }
  manifest.files = manifest.files.filter((f) => fs.existsSync(path.join(OUT, f.file)));
  manifest.regenerate_doc = 'node scripts/doc-captures.js';
  assertManifestClean(manifest, []);
  fs.writeFileSync(file, JSON.stringify(manifest, null, 2) + '\n');
}
