// ARTEFACT — Front v3, Lot 5 : documentation réécrite par écran, captures du banc réel, glossaire des états, « En savoir plus ».
// - index.md : une section par écran (barre d'état, page maison et puces, À faire, pièce et fiche, Corriger le type, Choisir ce qui
//   est publié, Scénarios, Configuration, Vérifier l'installation, Guide), chacune illustrée par sa capture ;
// - glossaire des états : couleur, icône, mot, pour les six états du code (mêmes mots, mêmes icônes que l'écran) ;
// - chaque image citée existe, chaque image de docs/fr_FR/images est citée (hors dossier « to-delete »), le manifeste les connaît ;
// - « En savoir plus » des bandes de cause : rendu dans le vrai Chromium, il vise l'aide de la page et une ancre qui existe ;
// - changelog_beta : entrée « Refonte de l'interface (front v3) » avec la publication des scénarios au choix.
// Données fictives (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView } = require('./helpers/workview_browser');
const { DEMO } = require('./helpers/front_v2_demo_trees');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

const root = path.join(__dirname, '..', '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const index = read('docs/fr_FR/index.md');
const premiers = read('docs/fr_FR/premiers-pas.md');
const compteurs = read('docs/fr_FR/compteurs.md');
const changelog = read('docs/fr_FR/changelog_beta.md');
const IMAGES = path.join(root, 'docs/fr_FR/images');
const slug = (title) => title.toLowerCase().replace(/[^\p{L}\p{N}\s-]/gu, '').replace(/\s/g, '-');
const anchors = index.split('\n').filter((l) => /^#{1,6} /.test(l)).map((l) => slug(l.replace(/^#+ /, '')));

// Section de index.md : du titre exact au titre suivant de même niveau ou plus haut.
function section(heading) {
  const start = index.indexOf('\n' + heading + '\n');
  assert.ok(start >= 0, heading);
  const level = heading.match(/^#+/)[0].length;
  const rest = index.slice(start + heading.length + 2);
  const next = rest.search(new RegExp('\\n#{1,' + level + '} '));
  return next < 0 ? rest : rest.slice(0, next);
}

const SCREENS = [
  ['### La barre d\'état', 'barre-etat.png'],
  ['### La page maison et les puces', 'page-principale.png'],
  ['### À faire', 'a-faire.png'],
  ['### La pièce et la fiche', 'vue-de-travail.png'],
  ['### Corriger le type', 'corriger-le-type.png'],
  ['### Choisir ce qui est publié', 'choisir-ce-qui-est-publie.png'],
  ['### Les scénarios', 'scenarios.png'],
  ['### Configuration', 'configuration.png'],
  ['### Vérifier l\'installation', 'verifier-installation.png'],
  ['### Le guide de démarrage', 'guide-demarrage.png'],
];

test('Lot 5 — une section par écran sous « Les écrans », chacune avec sa capture, listée dans le sommaire', () => {
  const screens = index.slice(index.indexOf('\n## Les écrans\n'), index.indexOf('\n## Ce que le plugin publie'));
  let from = 0;
  for (const [heading, image] of SCREENS) {
    const at = screens.indexOf('\n' + heading + '\n');
    assert.ok(at > from, `${heading} : présent, dans l'ordre`);
    from = at;
    assert.ok(section(heading).includes(`](images/${image})`), `${heading} : capture ${image}`);
    const head = index.slice(0, index.indexOf('\n## Présentation'));
    assert.ok(head.includes(`(#${slug(heading.replace(/^#+ /, ''))})`), `${heading} : dans le sommaire`);
  }
});

test('Lot 5 — chaque section d’écran reste courte (version « En savoir plus »)', () => {
  for (const [heading] of SCREENS) {
    // Corps de la section, sans ses sous-sections de référence (####, par exemple « Quand un bouton est grisé »).
    const body = section(heading).split(/\n#### /)[0];
    const words = body.replace(/<!--[\s\S]*?-->|!\[[^\]]*\]\([^)]*\)/g, '').split(/\s+/).filter(Boolean).length;
    assert.ok(words < 1200, `${heading} : ${words} mots`);
  }
  assert.ok(premiers.split('\n').length < 120);
});

test('Lot 5 — glossaire des états : les six mots du code, avec couleur et icône, dans l’ordre de l’écran', () => {
  const glossary = section('## Glossaire des états');
  // Icône dite en mots, par icône Font Awesome de l'écran (STATE_ICONS de jeedom2ha_mapping_surface.js et jeedom2ha_overview.js).
  const ICON_WORDS = { 'fa-check-circle': '✓ dans un rond', 'fa-clock': 'horloge', 'fa-exclamation-triangle': 'triangle ⚠',
    'fa-eye-slash': 'œil barré', 'fa-pause-circle': 'pause', 'fa-minus-circle': 'rond barré d\'un trait' };
  const COLORS = { published: 'vert', to_apply: 'bleu', blocked: 'orange', excluded: 'gris', disabled: 'gris, italique', nothing_to_publish: 'gris' };
  const surface = read('desktop/js/jeedom2ha_mapping_surface.js');
  const icons = {};
  for (const m of surface.slice(surface.indexOf('var STATE_ICONS = {'), surface.indexOf('};', surface.indexOf('var STATE_ICONS = {'))).matchAll(/(\w+): '(fa-[a-z-]+)'/g)) icons[m[1]] = m[2];
  let from = 0;
  for (const state of M.EQUIPMENT_STATES) {
    const word = M.EQUIPMENT_STATE_LABELS[state];
    const row = `| **${word}** | ${COLORS[state]} | ${ICON_WORDS[icons[state]]} |`;
    const at = glossary.indexOf(row);
    assert.ok(at > from, `${state} : ${row}`);
    from = at;
  }
  for (const word of ['Conseil', 'Non vérifié', 'Rien à faire', 'Nouveau', 'Inactif', 'Non confirmé']) assert.ok(glossary.includes(`**${word}**`), word);
  assert.match(glossary, /la couleur ne porte jamais le sens seule/i);
  assert.match(premiers, /\]\(index\.md#glossaire-des-états\)/);
});

test('Lot 5 — images : chacune citée existe, chacune présente est citée, le manifeste les connaît', () => {
  const docs = ['index.md', 'premiers-pas.md', 'compteurs.md'].map((f) => read('docs/fr_FR/' + f)).join('\n');
  const cited = new Set([...docs.matchAll(/\]\(images\/([a-z0-9-]+\.png)\)/g)].map((m) => m[1]));
  for (const file of cited) assert.ok(fs.existsSync(path.join(IMAGES, file)), `citée mais absente : ${file}`);
  const present = fs.readdirSync(IMAGES).filter((f) => f.endsWith('.png'));
  for (const file of present) assert.ok(cited.has(file), `présente mais jamais citée (à déplacer dans images/to-delete) : ${file}`);
  const manifest = JSON.parse(fs.readFileSync(path.join(IMAGES, 'captures-manifest.json'), 'utf8'));
  const known = new Set(manifest.files.map((f) => f.file));
  for (const file of present) assert.ok(known.has(file), `absente du manifeste : ${file}`);
  for (const f of manifest.files) assert.ok(fs.existsSync(path.join(IMAGES, f.file)), `manifeste : ${f.file} absent`);
});

test('Lot 5 — script de captures : banc réel, 1280 px, thème clair, aucune donnée réelle', () => {
  const src = read('scripts/doc-captures.js');
  assert.match(src, /withRealView/);
  assert.match(src, /const WIDTH = 1280;/);
  assert.match(src, /core2019_Light/);
  assert.doesNotMatch(src, /\b(?:\d{1,3}\.){3}\d{1,3}\b/, 'aucune adresse IP');
  assert.doesNotMatch(src, /zwave|Z-Wave/i, 'aucun plugin réel nommé');
  for (const [, image] of SCREENS) assert.ok(src.includes(`'${image.replace(/\.png$/, '')}'`) || src.includes(`${image.replace(/\.png$/, '')}:`), image);
});

test('Lot 5 — ancres : « En savoir plus » et les renvois de la doc visent des titres existants', () => {
  const surface = read('desktop/js/jeedom2ha_mapping_surface.js');
  const anchor = surface.match(/var HELP_ANCHOR = '#([^']+)';/)[1];
  assert.ok(anchors.includes(anchor), `« En savoir plus » → index.md#${anchor}`);
  // « Aide » (icône ? de la barre d'état) : la documentation du plugin, index.md (repli de la page).
  assert.match(read('desktop/php/jeedom2ha.php'), /docs\/fr_FR\/index\.md';/);
  for (const [name, text] of [['index.md', index], ['premiers-pas.md', premiers], ['compteurs.md', compteurs]]) {
    for (const m of text.matchAll(/\]\((index\.md)?#([^)]+)\)/g)) {
      if (name === 'compteurs.md' && !m[1]) continue;
      assert.ok(anchors.includes(m[2]), `${name} → index.md#${m[2]}`);
    }
  }
});

test('Lot 5 — changelog_beta : « Refonte de l’interface (front v3) », scénarios au choix', () => {
  const entry = changelog.split('\n---\n').find((part) => part.includes('Refonte de l\'interface (front v3)'));
  assert.ok(entry, 'entrée présente');
  assert.ok(changelog.indexOf('Refonte de l\'interface (front v3)') < changelog.indexOf('# 2026-11-14 — Vue de travail'), 'en tête');
  assert.match(entry, /déjà publiés le restent/);
  assert.match(entry, /arrive \*\*non publié\*\*, marqué ✱/);
  assert.ok(entry.split('\n').filter((l) => l.startsWith('- ')).length <= 10, 'liste courte');
  assert.doesNotMatch(entry, /\b(salon|Alexandre|Dupont)\b/i);
});

test('Lot 5 — « En savoir plus » : rendu dans la bande de cause, vers l’aide de la page et la section des causes (vrai Chromium)', async (t) => {
  const SCENE = {
    objects: [{ id: 1, name: 'Maison', father_id: null, display: {} }, { id: 9, name: 'Bureau', father_id: 1, display: {} }],
    eqlogics: { 9: [{ id: 231, name: 'Lampe Chevet', type: 'virtual' }] },
    plugin_names: { virtual: 'Virtuel' },
    doc: 'https://doc.example.test/plugin/index.md',
  };
  const tree = DEMO.lampePrise(true);
  await withRealView(t, { scene: SCENE, equipments: { 231: tree }, treeFor: () => ({ state: 'ok', result: { status: 'ok', payload: tree } }),
    hash: '#j2ha-vue=piece:9;eq:231', width: 1280, height: 800 }, async (page, ctx) => {
    const link = page.locator('.j2ha-eq-panel[data-eq-id="231"] .j2ha-eq-band .j2ha-v2-help').first();
    await link.waitFor();
    assert.equal((await link.textContent()).trim(), 'En savoir plus');
    assert.equal(await link.getAttribute('href'), 'https://doc.example.test/plugin/index.md#les-causes-de-blocage');
    assert.equal(await link.getAttribute('target'), '_blank');
    assert.ok(await link.isVisible());
    assert.deepEqual(ctx.errors, []);
  });
});
