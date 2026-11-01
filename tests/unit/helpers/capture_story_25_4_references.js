'use strict';

/* Story 25.4 (Task 1) — capture de l'ÉTAT DE RÉFÉRENCE avant tout changement de code. À exécuter sur `main`
 * (fenêtre de pièce encore présente) :
 *
 *   node tests/unit/helpers/capture_story_25_4_references.js [corps|css|gate|tout]
 *
 * Écrit sous tests/fixtures/ :
 *   story_25_4_corps_ecriture.json   corps sérialisés (clés triées) de chaque écriture, relevés en rejouant les
 *                                    scénarios d'écriture (write_scenarios.js) sur la modale de pièce ;
 *   story_25_4_css_baseline.json     sélecteurs et déclarations de desktop/css/jeedom2ha.css + liste des
 *                                    sélecteurs propres à la modale (retrait attendu, AC2) ;
 *   story_25_4_gate_assertions.json  registre d'assertions des parcours du gate qui touchent la fenêtre de pièce.
 *
 * Les fichiers capturés sont versionnés : ce script n'est PAS relancé sur la branche de la story (ses sorties
 * seraient alors celles de la vue C). Il documente comment la référence a été produite. Aucune donnée réelle. */

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..', '..', '..');
const FIXTURES = path.join(ROOT, 'tests', 'fixtures');

// --- CSS : sélecteur individuel -> déclarations concaténées, par contexte d'at-rule ---

function stripComments(css) {
  return css.replace(/\/\*[\s\S]*?\*\//g, '');
}

const squash = (text) => text.replace(/\s+/g, ' ').trim();

/** Analyse plate d'une feuille : rend [{ at, selectors: [...], declarations: 'a:b;c:d' }] (at-rules d'un niveau). */
function parseCss(css) {
  const text = stripComments(css);
  const rules = [];
  function walk(start, end, at) {
    let i = start;
    while (i < end) {
      const open = text.indexOf('{', i);
      if (open === -1 || open >= end) break;
      const head = squash(text.slice(i, open));
      let depth = 1;
      let j = open + 1;
      while (j < end && depth > 0) {
        if (text[j] === '{') depth += 1;
        else if (text[j] === '}') depth -= 1;
        j += 1;
      }
      const body = text.slice(open + 1, j - 1);
      if (head.startsWith('@media') || head.startsWith('@supports')) {
        walk(open + 1, j - 1, head);
      } else if (!head.startsWith('@')) {
        const declarations = body.split(';').map(squash).filter(Boolean).map((d) => d.replace(/\s*:\s*/, ':')).join(';');
        rules.push({ at, selectors: head.split(',').map(squash).filter(Boolean), declarations });
      }
      i = j;
    }
  }
  walk(0, text.length, '');
  return rules;
}

/** Table `contexte|sélecteur` -> déclarations (concaténées dans l'ordre de la feuille). */
function selectorTable(css) {
  const table = {};
  parseCss(css).forEach((rule) => {
    rule.selectors.forEach((selector) => {
      const key = (rule.at ? rule.at + ' | ' : '') + selector;
      table[key] = table[key] ? table[key] + ';' + rule.declarations : rule.declarations;
    });
  });
  return table;
}

// Sélecteurs propres à la fenêtre de pièce (modale, accordéon, en-tête de pièce à compteurs) : retirés par la story.
const MODAL_SELECTORS = [
  '.modal-j2ha-room .modal-dialog',
  '.modal-j2ha-room .j2ha-eq-accordion .j2ha-eq-panel',
  '.modal-j2ha-room .j2ha-eq-head',
  '.modal-j2ha-room .j2ha-eq-panel.j2ha-eq-open > .j2ha-eq-head',
  '.modal-j2ha-room tr.mapping-override-cmd',
  '.modal-j2ha-room .j2ha-eq-panel.j2ha-eq-open .j2ha-eq-controls',
  '.modal-j2ha-room .j2ha-eq-panel.j2ha-eq-open > .panel-collapse > .panel-body',
  '.j2ha-eq-toggle',
  '.j2ha-eq-toggle:focus',
  // Accordéon : les commandes n'étaient visibles que dans un panneau déplié (`display: none` par défaut).
  '.j2ha-eq-controls',
  // En-tête de la fenêtre (compteurs de pièce lus dans les arbres chargés) : remplacé par les KPI de la vue C.
  // `.j2ha-room-counter-unread` RESTE : le détail d'équipement l'emploie pour la présence inconnue (démon plus ancien).
  '.j2ha-room-head',
  '.j2ha-room-counters',
  '.j2ha-room-counter-line',
];

function captureCss() {
  const css = fs.readFileSync(path.join(ROOT, 'desktop', 'css', 'jeedom2ha.css'), 'utf8');
  const table = selectorTable(css);
  const out = {
    description: 'Story 25.4 (AC2, AC24, AC25) : sélecteurs et déclarations de desktop/css/jeedom2ha.css sur main, avant la story.',
    modal_selectors: MODAL_SELECTORS,
    selectors: table,
  };
  const missing = MODAL_SELECTORS.filter((s) => !(s in table));
  if (missing.length) throw new Error('sélecteurs de modale introuvables : ' + missing.join(' ; '));
  fs.writeFileSync(path.join(FIXTURES, 'story_25_4_css_baseline.json'), JSON.stringify(out, null, 2) + '\n');
  return Object.keys(table).length;
}

// --- Gate : registre d'assertions des parcours ---

const PARCOURS = [
  'decouverte-piece-25-eq-579', 'exclusion-publication-non-publiee', 'reference-bascule-eq-380',
  'controle-ecriture-non-declaree', 'page-principale-b',
];

function uniq(list) {
  return Array.from(new Set(list));
}

/** Étiquettes d'erreur, clés `record`, étapes et déclarations d'écriture d'un parcours (lecture du source). */
function registryOf(source) {
  const errors = [];
  const errorRe = /new Error\((['"`])((?:\\.|(?!\1)[\s\S])*?)\1\)/g;
  let m;
  while ((m = errorRe.exec(source))) errors.push(m[2]);
  const records = [];
  const recordRe = /helpers\.record\(\s*(['"`])((?:\\.|(?!\1)[\s\S])*?)\1/g;
  while ((m = recordRe.exec(source))) records.push(m[2]);
  const steps = [];
  const stepRe = /\b(?:atStep|waitAtStep)\(\s*helpers\s*,\s*(['"`]?)([A-Za-z0-9_${}]+)\1\s*,\s*(['"`])((?:\\.|(?!\3)[\s\S])*?)\3/g;
  while ((m = stepRe.exec(source))) steps.push(`${m[2]}:${m[4]}`);
  const declared = {};
  // Story 24.11 : `dynamicTarget` est relevé comme une déclaration (une cible choisie à l'exécution ne peut pas
  // redevenir silencieusement statique, ni l'inverse).
  ['declaredEquipments', 'declaredBascules', 'declaredPublicationOverrides', 'declaredRescan', 'dynamicTarget'].forEach((name) => {
    const re = new RegExp('export const ' + name + ' = ([\\s\\S]*?);\\n');
    const found = re.exec(source);
    if (found) declared[name] = found[1].replace(/\s+/g, ' ').trim();
  });
  return { errors: uniq(errors), records: uniq(records), steps: uniq(steps), declared };
}

function captureGate() {
  const out = {
    description: 'Story 25.4 (AC27) : registre d\'assertions des parcours du gate 20-0 qui touchent la fenêtre de pièce, capturé sur main. '
      + 'Sur-ensemble minimal : ajouter est permis, retirer non.',
    parcours: {},
  };
  PARCOURS.forEach((name) => {
    const source = fs.readFileSync(path.join(ROOT, 'tests', 'e2e', 'gate', 'parcours', name + '.mjs'), 'utf8');
    out.parcours[name] = registryOf(source);
  });
  fs.writeFileSync(path.join(FIXTURES, 'story_25_4_gate_assertions.json'), JSON.stringify(out, null, 2) + '\n');
  return PARCOURS.map((name) => `${name}: ${out.parcours[name].errors.length} erreurs, ${out.parcours[name].records.length} clés, ${out.parcours[name].steps.length} étapes`);
}

// --- Écritures : scénarios rejoués sur la fenêtre de pièce ---

async function captureWrites() {
  const { createUi, BRIDGE_UP } = require('./ui_harness');
  const { runAll } = require('./write_scenarios');
  function openModal(rooms, objectId, trees) {
    const ui = createUi(rooms);
    ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
    ui.openRoom(objectId);
    trees.forEach((t) => ui.respond('getMappingOverrides', t));
    return ui;
  }
  const scenarios = await runAll(openModal);
  const out = {
    description: 'Story 25.4 (AC8) : corps sérialisés (clés triées) des écritures de l\'écran d\'équipement et de pièce, relevés sur la fenêtre de pièce de main.',
    scenarios,
  };
  fs.writeFileSync(path.join(FIXTURES, 'story_25_4_corps_ecriture.json'), JSON.stringify(out, null, 2) + '\n');
  return Object.entries(scenarios).map(([name, writes]) => `${name}: ${writes.length}`);
}

module.exports = { parseCss, selectorTable, registryOf, MODAL_SELECTORS, PARCOURS };

if (require.main === module) {
  (async () => {
    const what = process.argv[2] || 'tout';
    if (what === 'css' || what === 'tout') console.log('css:', captureCss(), 'sélecteurs');
    if (what === 'gate' || what === 'tout') console.log('gate:', captureGate().join('\n      '));
    if (what === 'corps' || what === 'tout') console.log('corps:', (await captureWrites()).join('\n      '));
  })().catch((error) => { console.error(error); process.exit(1); });
}
