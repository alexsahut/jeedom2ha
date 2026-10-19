// ARTEFACT — Story 25.4 (AC1, AC2, AC3 partiel) : la fenêtre de pièce est RETIRÉE, sans reste mort. Aucune occurrence
// fonctionnelle de la modale (classes, fonctions de rendu, accordéon) dans `desktop/`, `tests/` ni `docs/` ; les règles
// CSS qui lui étaient propres sont supprimées (la liste de retrait est dans la référence capturée avant la story) ;
// `window.j2haOpenRoom` reste défini et ne crée aucune modale ; les fonctions de rendu de l'ÉQUIPEMENT sont conservées.
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { startBig, openCard, phpAvailable } = require('./helpers/workview_harness');
const { selectorTable } = require('./helpers/capture_story_25_4_references');

const root = path.join(__dirname, '..', '..');
const maybe = phpAvailable ? it : it.skip;
const baseline = JSON.parse(fs.readFileSync(path.join(root, 'tests/fixtures/story_25_4_css_baseline.json'), 'utf8'));

// Liste de retrait (AC2) : tout ce qui n'existe plus. Reconstruite par assemblage pour que ce fichier, seul avec la référence
// capturée, porte ces noms.
const RETIRED_CLASS = ['modal', 'j2ha', 'room'].join('-');
const RETIRED_RENDER = ['buildRoom', 'ModalHtml'].join('');
const ALLOWED_FILES = new Set([
  'tests/fixtures/story_25_4_css_baseline.json',
  'tests/fixtures/story_25_4_gate_assertions.json',
  'tests/unit/helpers/capture_story_25_4_references.js',
  'tests/unit/test_story_25_4_retrait_modale.node.test.js',
]);

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? (entry.name === 'node_modules' ? [] : walk(full)) : [full];
  });
}

describe('25.4 / AC2 — aucun reste fonctionnel de la fenêtre de pièce', () => {
  it('desktop/, tests/ et docs/ ne contiennent ni la classe de la modale ni sa fonction de rendu (hors référence de retrait)', () => {
    const found = [];
    for (const dir of ['desktop', 'tests', 'docs']) {
      for (const file of walk(path.join(root, dir))) {
        const rel = path.relative(root, file).split(path.sep).join('/');
        if (ALLOWED_FILES.has(rel) || !/\.(js|mjs|php|css|md|json)$/.test(rel)) continue;
        const text = fs.readFileSync(file, 'utf8');
        if (text.includes(RETIRED_CLASS) || text.includes(RETIRED_RENDER)) found.push(rel);
      }
    }
    assert.deepEqual(found, []);
  });

  it('la surface ne définit plus ni openRoom, ni l’accordéon ; elle expose le détail d’équipement', () => {
    const surface = fs.readFileSync(path.join(root, 'desktop/js/jeedom2ha_mapping_surface.js'), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
    for (const retired of ['function openRoom', 'function togglePanel', 'function setPanelOpen', 'j2ha-eq-accordion', 'panel-group', 'panel-collapse', 'bootbox.dialog({\n      // « Sans pièce »', "window.j2haOpenRoom"]) {
      assert.ok(!surface.includes(retired), retired);
    }
    assert.doesNotMatch(surface, /\.each\(function \(\) \{\s*var \$panel = \$\(this\);\s*\$panel\.data\('loaded'/);
    // Les fonctions de rendu et d'écriture de l'équipement sont conservées (déplacées dans le détail, pas retirées).
    for (const kept of ['function renderCommandTable', 'function renderNotices', 'function renderIgnored', 'function buildSegmented', 'function renderControls', 'function applyEquipment', 'function saveOverride', 'function revertCommand', 'function publicationRequest', 'function requestPublication', 'function runHaAction']) {
      assert.ok(surface.includes(kept), kept);
    }
  });

  it('les sélecteurs de la fenêtre listés dans la référence ne sont plus dans le CSS', () => {
    const css = fs.readFileSync(path.join(root, 'desktop/css/jeedom2ha.css'), 'utf8');
    assert.ok(baseline.modal_selectors.length >= 10);
    const present = Object.keys(selectorTable(css)).map((key) => key.replace(/^.*\| /, ''));
    for (const selector of baseline.modal_selectors) assert.ok(!present.includes(selector), selector);
    assert.doesNotMatch(css, /j2ha-eq-accordion|panel-group|panel-collapse|j2ha-eq-toggle/);
  });
});

describe('25.4 / AC1, AC2 — le point d’entrée des cartes ne crée aucune modale', () => {
  maybe('window.j2haOpenRoom est défini, ouvre la vue et n’appelle jamais bootbox.dialog avec une classe de pièce', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    assert.equal(typeof ui.win.j2haOpenRoom, 'function');
    const before = ui.dom.dialogs.length;
    ui.win.j2haOpenRoom(10);
    ui.win.j2haOpenRoom('11');
    ui.win.j2haOpenRoom('x'); // identifiant invalide : ignoré
    assert.equal(ui.dom.dialogs.length, before);
    assert.ok(ui.dom.dialogs.every((d) => !String(d.options.className || '').includes(RETIRED_CLASS)));
    assert.equal(ui.isOpen(), true);
  });

  maybe('les cartes conservent objectDisplayCard, j2ha-room-card, data-object_id et j2haOpenRoom(id) ; jamais eqLogicDisplayCard', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    const cards = ui.$('#j2ha_roomCards .j2ha-room-card');
    assert.ok(cards.length >= 3);
    cards.list.forEach((card) => {
      assert.ok(card.classes.has('objectDisplayCard'));
      assert.ok(!card.classes.has('eqLogicDisplayCard'));
      assert.match(card.attrs['data-object_id'], /^\d+$/);
      assert.equal(card.attrs.onclick, `j2haOpenRoom(${card.attrs['data-object_id']})`);
    });
    openCard(ui, 10);
  });
});
