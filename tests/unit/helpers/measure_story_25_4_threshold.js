'use strict';

/* Story 25.4 (Task 7, AC20, Q3) — PROTOCOLE DE MESURE du seuil de repli, dans le Chromium de la session, avec le VRAI CSS
 * (la media query de la vue est forcée à « toujours large » pour mesurer la disposition large à chaque largeur) et la fixture
 * la plus lourde : 292 équipements fictifs (noms longs) et un équipement de 5 entités aux noms de commande longs.
 *
 *   node tests/unit/helpers/measure_story_25_4_threshold.js
 *
 * Largeurs candidates : 768, 834, 900, 980, 1024, 1112, 1180, 1280 (px de viewport CSS). Critères (décision ClaudeBox Q3 = A) :
 *   (a) aucun défilement horizontal dans le détail (`scrollWidth <= clientWidth`) pour le tableau des commandes à quatre colonnes ;
 *   (b) panneau de gauche (arbre) >= 280 px ;
 *   (c) détail utile >= 560 px.
 * Seuil retenu = la plus petite largeur candidate qui satisfait (a), (b) et (c) ; 1024 px si la mesure n'aboutit pas.
 * Le contexte de la page imite le cœur Jeedom : marges latérales de 15 px (colonne Bootstrap) et barre de défilement verticale
 * de la page réservée. Écrit tests/fixtures/story_25_4_mesure_seuil.json (identifiants et données fictifs, CC-48). La preuve sur
 * l'iPad mural en mode bureau reste une réserve de la preuve terrain (Task 11), jamais une assertion de cette mesure. */

const fs = require('node:fs');
const path = require('node:path');
const { withRealView, read } = require('./workview_browser');
const { makeScene } = require('./big_scene');
const { FIXTURE, clone } = require('./page_b_harness');

const WIDTHS = [768, 834, 900, 980, 1024, 1112, 1180, 1280];
const MIN_NAV = 280;
const MIN_DETAIL = 560;
const OUT = path.join(__dirname, '..', '..', 'fixtures', 'story_25_4_mesure_seuil.json');

/** Arbre unitaire le plus lourd : 5 entités, 3 commandes chacune, noms de commande et types génériques longs, un type imposé. */
function heavyTree(eqId) {
  const tree = clone(FIXTURE['101'].tree);
  const types = ['light', 'switch', 'sensor', 'binary_sensor', 'cover'];
  const diag = clone(FIXTURE['101'].tree.commands[0].diagnostic);
  tree.jeedom_eq_id = eqId;
  tree.eq_name = 'Équipement fictif à cinq entités et noms de commande longs';
  tree.mapped = true;
  tree.entities = types.map((type, e) => ({
    ha_entity_type: type, command_ids: [0, 1, 2].map((c) => eqId * 100 + e * 10 + c), decision: diag,
    publication_override: null, override_command_id: eqId * 100 + e * 10, override_pending: false, present_in_ha: true,
  }));
  tree.commands = [];
  types.forEach((type, e) => [0, 1, 2].forEach((c) => {
    tree.commands.push({
      jeedom_cmd_id: eqId * 100 + e * 10 + c,
      cmd_name: `Commande numéro ${e}${c} avec un nom particulièrement long pour mesurer le tableau`,
      generic_type: 'LIGHT_SET_COLOR_TEMPERATURE_EXTENDED', covered: true, coverable: true, attendu_ha: type,
      effective_ha: type, override_applied: e === 3 && c === 1, diagnostic: clone(diag), published_in_ha: true,
    });
  }));
  return { state: 'ok', result: { status: 'ok', payload: tree } };
}

async function measure() {
  const big = makeScene({ rooms: 12, equipments: 292, seed: 25, longNames: true, grouped: true });
  const forced = read('desktop/css/jeedom2ha.css').replace(/@media \(min-width: \d+px\)/g, '@media (min-width: 0px)');
  const extra = '\nhtml { overflow-y: scroll; }\nbody { margin: 0; }\n.eqLogicThumbnailDisplay { padding: 0 15px; }\n';
  const rows = [];
  for (const width of WIDTHS) {
    await withRealView({ skip() { throw new Error('mesure indisponible'); } }, {
      width, height: 900, scene: big.scene, equipments: big.equipments, css: forced, extraCss: extra,
      treeFor: (eqId) => heavyTree(eqId),
    }, async (page) => {
      await page.locator('#j2ha_roomCards .j2ha-room-card').first().click();
      await page.locator('.j2ha-wv-eq .j2ha-wv-row').first().click();
      await page.locator('.j2ha-eq-panel .j2ha-cmd-table').waitFor({ state: 'visible' });
      const m = await page.evaluate(() => {
        const detail = document.querySelector('.j2ha-wv-detail');
        const nav = document.querySelector('.j2ha-wv-nav');
        const table = document.querySelector('.j2ha-cmd-table');
        return {
          viewport: window.innerWidth,
          layout: document.querySelector('#j2ha_workView').getAttribute('data-j2ha-layout'),
          detail_client: detail.clientWidth, detail_scroll: detail.scrollWidth,
          nav_width: Math.round(nav.getBoundingClientRect().width),
          table_width: Math.round(table.getBoundingClientRect().width),
          height: Math.round(document.querySelector('#j2ha_workView').getBoundingClientRect().height),
        };
      });
      const a = m.detail_scroll <= m.detail_client;
      const b = m.nav_width >= MIN_NAV;
      const c = m.detail_client >= MIN_DETAIL;
      rows.push({ width, detail_width: m.detail_client, nav_width: m.nav_width, table_width: m.table_width, height: m.height, a_no_hscroll: a, b_nav_280: b, c_detail_560: c, ok: a && b && c });
    });
  }
  const chosen = rows.find((row) => row.ok);
  return { rows, chosen: chosen ? chosen.width : null };
}

if (require.main === module) {
  measure().then((result) => {
    const decided = result.chosen === null ? 1024 : result.chosen;
    const out = {
      description: 'Story 25.4 (AC20, Q3) : mesure du seuil de repli, Chromium de la session (voir measure_story_25_4_threshold.js). Données fictives.',
      method: 'disposition large forcée à chaque largeur candidate ; fixture : 292 équipements, équipement de 5 entités aux noms longs ; contexte Jeedom imité (marges de 15 px, barre de défilement réservée)',
      criteria: { a: 'aucun défilement horizontal dans le détail', b: 'panneau de gauche >= 280 px', c: 'détail utile >= 560 px' },
      rows: result.rows,
      measured_threshold: result.chosen,
      retained_threshold: decided,
      fallback_used: result.chosen === null,
      reserve: 'La largeur CSS réelle de l\'iPad mural en mode bureau est relevée en preuve terrain (Task 11, CC-48) : elle peut réviser ce seuil par une PR de suite.',
    };
    fs.writeFileSync(OUT, JSON.stringify(out, null, 2) + '\n');
    console.log(JSON.stringify(out.rows, null, 1));
    console.log('seuil mesuré :', result.chosen, '— retenu :', decided);
  }).catch((error) => { console.error(error); process.exit(1); });
}

module.exports = { measure, heavyTree, WIDTHS };
