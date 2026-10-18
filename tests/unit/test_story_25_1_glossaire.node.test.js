// ARTEFACT — Story 25.1 (AC7, AC8, AC9) : un mot = une notion. Plus aucun terme interdit dans les
// libellés de l'interface (chaînes `{{…}}`, `__()` et libellés construits en JS, infobulles comprises) ;
// libellés exacts du glossaire (D4) présents dans le rendu. Identifiants fictifs (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const { createUi, tree, ok, READY, EXCLUDED, DISABLED, BRIDGE_UP, view } = require('./helpers/ui_harness');

// Termes interdits dans un libellé (AC7), en mot entier et insensible à la casse. `Homebridge` n'est pas
// concerné (mot entier) ; `override_pending`, `getBridgeStatus`… non plus (un identifiant n'est pas un mot).
const word = (w) => new RegExp('(?<![\\p{L}\\p{N}_])' + w + '(?![\\p{L}\\p{N}_])', 'iu');
const FORBIDDEN = [
  ['override', word('override')], ['bridge', word('bridge')],
  ['prête', word('prête')], ['prêtes', word('prêtes')], ['prêt', word('prêt')], ['prêts', word('prêts')],
  ['bloquante', word('bloquante')], ['bloquantes', word('bloquantes')], ['rescanner', word('rescanner')],
  ['commande(s)', /commande\(s\)/i], ['(s) en suffixe', /\p{L}\(s\)/iu],
];

/* Exceptions autorisées par D4, codées en dur : identifiants de code (`override_pending`, `mapping_overrides`,
 * `getBridgeStatus`, classes CSS, champs JSON du démon, noms de fichiers de tests), historique des versions
 * (`changelog*.md`, non scanné ici), le mot « Homebridge » (mot entier, jamais détecté) et les noms de types HA
 * dans les listes techniques (`switch`, `sensor`…). Un texte en minuscules ASCII sans espace ni accent est un
 * identifiant ou un sélecteur, pas un libellé : il n'est pas contrôlé. */
const isIdentifierOnly = (text) => /^[a-z0-9_.#:\[\]="'>,~+*()\s-]*$/.test(text) && !/\{\{/.test(text);

/** Chaînes littérales d'un source JS (hors commentaires), décodées. */
function jsStrings(source) {
  const code = source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
  const out = [];
  const re = /'((?:[^'\\\n]|\\.)*)'|"((?:[^"\\\n]|\\.)*)"|`((?:[^`\\]|\\.)*)`/g;
  let m;
  while ((m = re.exec(code)) !== null) {
    out.push((m[1] !== undefined ? m[1] : m[2] !== undefined ? m[2] : m[3]).replace(/\\'/g, "'").replace(/\\"/g, '"'));
  }
  return out;
}

/** Textes rendus : balises retirées, mais les valeurs de title / aria-label / placeholder sont conservées. */
function visibleTexts(raw) {
  const texts = [];
  const attrRe = /\b(?:title|aria-label|placeholder)="([^"]*)"/g;
  let a;
  while ((a = attrRe.exec(raw)) !== null) texts.push(a[1]);
  const text = raw.replace(/<[^>]*>/g, ' ').trim();
  if (text) texts.push(text);
  return texts;
}

function phpStrings(source) {
  const code = source.replace(/<!--[\s\S]*?-->/g, '').replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
  const out = [];
  code.replace(/\{\{([\s\S]*?)\}\}/g, (_m, t) => { out.push('{{' + t + '}}'); return ''; });
  code.replace(/__\(\s*'((?:[^'\\]|\\.)*)'/g, (_m, t) => { out.push(t); return ''; });
  return out;
}

function violations(texts, label) {
  const found = [];
  for (const raw of texts) {
    for (const text of visibleTexts(raw)) {
      if (isIdentifierOnly(text)) continue;
      for (const [name, re] of FORBIDDEN) {
        if (re.test(text)) found.push(`${label} : « ${text} » contient « ${name} »`);
      }
    }
  }
  return found;
}

const jsFiles = fs.readdirSync('desktop/js').filter((f) => f.endsWith('.js'));

describe('25.1 / AC7 — aucun terme interdit dans les libellés', () => {
  it('desktop/js : chaînes {{…}}, libellés construits, REASON_LABELS, infobulles', () => {
    const found = jsFiles.flatMap((file) => violations(jsStrings(fs.readFileSync(path.join('desktop/js', file), 'utf8')), file));
    assert.deepEqual(found, []);
  });

  it('desktop/php : chaînes {{…}} et __()', () => {
    const found = violations(phpStrings(fs.readFileSync('desktop/php/jeedom2ha.php', 'utf8')), 'jeedom2ha.php');
    assert.deepEqual(found, []);
  });

  it('desktop/css : aucun terme interdit dans les commentaires et contenus générés', () => {
    const css = fs.readFileSync('desktop/css/jeedom2ha.css', 'utf8');
    const contents = [...css.matchAll(/content:\s*"([^"]*)"/g)].map((m) => m[1]);
    assert.deepEqual(violations(contents, 'jeedom2ha.css'), []);
  });

  it('le détecteur détecte : chaque terme interdit injecté dans une chaîne est signalé', () => {
    for (const bad of ['Override HA', 'Bridge indisponible', 'Rescanner la topologie', 'commande(s) prête(s)', 'une prête', 'bloquante', 'Prêt : ok', 'des bloquantes']) {
      assert.ok(violations(['{{' + bad + '}}'], 'x').length > 0, bad);
    }
    assert.deepEqual(violations(['{{Aucun impact Homebridge : rien ne change}}', 'override_pending', '<span class="mapping-override-cmd"></span>'], 'x'), []);
    assert.ok(violations(['<a title="Override HA"></a>'], 'x').length > 0, 'les infobulles sont contrôlées');
  });

  it('l’extracteur couvre bien les sources (libellés connus retrouvés)', () => {
    assert.ok(jsStrings(fs.readFileSync('desktop/js/jeedom2ha_mapping_surface.js', 'utf8')).includes('{{Automatique}}'));
    assert.ok(jsStrings(fs.readFileSync('desktop/js/jeedom2ha_mapping_override.js', 'utf8')).includes('Rien à publier'));
    assert.ok(phpStrings(fs.readFileSync('desktop/php/jeedom2ha.php', 'utf8')).includes('{{Démon}}'));
  });

  it('les exceptions du test sont exactement celles de D4 (liste fermée)', () => {
    const source = fs.readFileSync(__filename, 'utf8');
    const block = source.match(/\/\* Exceptions autorisées par D4[\s\S]*?\*\//)[0];
    for (const expected of ['identifiants de code', 'changelog*.md', 'Homebridge', 'noms de types HA']) {
      assert.ok(block.includes(expected), expected);
    }
  });
});

describe('25.1 / AC9 — toutes les causes passent par le glossaire', () => {
  it('REASON_LABELS ne cite plus « Override HA » ni « Forcer » ; switch_state_orphan dit « Type HA » et « Toujours »', () => {
    for (const [code, label] of Object.entries(M.REASON_LABELS)) {
      assert.doesNotMatch(label, /Override HA|Forcer|Exclure/, code);
    }
    assert.match(M.REASON_LABELS.switch_state_orphan, /« Type HA »/);
    assert.match(M.REASON_LABELS.switch_state_orphan, /« Toujours »/);
    assert.match(M.REASON_LABELS.switch_state_orphan, /binary_sensor/);
  });
});

function fullRoom() {
  const decisions = [
    tree(1, [READY]),
    tree(2, [READY], { entities: [{ ha_entity_type: 'light', command_ids: [200], decision: READY, override_pending: true, override_command_id: 200 }] }),
    tree(3, [view('no_generic_type_configured', false, false), READY, view('command_not_covered', false, false)], { present: true }),
    tree(4, [EXCLUDED], { decision: EXCLUDED, present: false }),
    tree(5, [DISABLED], { decision: DISABLED, present: false }),
    tree(6, [view('command_not_covered', false, false)], { present: false }),
  ];
  decisions[2].commands[0].published_in_ha = false;
  const ui = createUi([{ object_id: 7, object_name: 'Zone', equipments: decisions.map((t, i) => ({ eq_id: i + 1, eq_name: 'Eq ' + (i + 1), enabled: true })) }]);
  ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
  ui.openRoom(7);
  decisions.forEach((t) => ui.respond('getMappingOverrides', ok(t)));
  return ui;
}

describe('25.1 / AC8 — libellés exacts du glossaire', () => {
  it('états d’équipement, états de commande, réglage de publication et actions présents tels quels', () => {
    const ui = fullRoom();
    const text = ui.$('.modal-j2ha-room').text().replace(/\{\{|\}\}/g, '');
    for (const label of ['Publié', 'À appliquer', 'Bloqué', 'Exclu', 'Désactivé', 'Rien à publier',
      'Publiée', 'Bloquée', 'Exclue', 'Automatique', 'Toujours', 'Jamais', 'Appliquer', 'Republier',
      'Supprimer de Home Assistant…']) {
      assert.ok(text.includes(label), label);
    }
    assert.match(M.buildUncoveredLabel(), /^Ignorée/);
    assert.ok(/1 commande ignorée,/.test(text), 'et les commandes ignorées sont comptées « ignorées »');
  });

  it('page principale : « Démon » (plus « Bridge »), « Relire Jeedom » (plus « Rescanner la topologie Jeedom »)', () => {
    const page = fs.readFileSync('desktop/php/jeedom2ha.php', 'utf8');
    assert.match(page, /<strong>\{\{Démon\}\}<\/strong>/);
    assert.match(page, /\{\{Relire Jeedom\}\}/);
    assert.match(page, /\{\{Supprimer de Home Assistant…\}\}/);
    const home = fs.readFileSync('desktop/js/jeedom2ha.js', 'utf8');
    assert.match(home, /\{\{Relire Jeedom\}\}/);
    assert.match(home, /\{\{Relire\}\}/);
  });

  it('aucune étiquette de badge, bouton, en-tête ou segment ne se termine par un point', () => {
    const ui = fullRoom();
    const selectors = ['.j2ha-eq-publish-badge', '.j2ha-seg-btn', '.j2ha-menu-item', '.j2ha-eq-apply', 'th', '.j2ha-group-head', '.j2ha-chip', '.j2ha-open-generic-types'];
    for (const selector of selectors) {
      ui.$('.modal-j2ha-room ' + selector).list.forEach((el) => {
        const text = ui.$(el).text().replace(/\{\{|\}\}/g, '').trim();
        assert.doesNotMatch(text, /\.$/, selector + ' : ' + text);
      });
    }
    const page = fs.readFileSync('desktop/php/jeedom2ha.php', 'utf8');
    for (const label of page.match(/<button[\s\S]*?<\/button>/g)) {
      const text = label.replace(/<[^>]*>/g, ' ').replace(/\{\{|\}\}/g, '').trim();
      assert.doesNotMatch(text, /\.$/, text);
    }
  });

  it('domaine HA : traduit avec le terme technique en petit dans les en-têtes de groupe', () => {
    const t = tree(1, [READY, READY], { entities: [
      { ha_entity_type: 'light', command_ids: [100], decision: READY, override_command_id: 100 },
      { ha_entity_type: 'alarm_control_panel', command_ids: [101], decision: READY, override_command_id: 101 },
    ] });
    const ui = createUi([{ object_id: 7, object_name: 'Zone', equipments: [{ eq_id: 1, eq_name: 'Eq', enabled: true }] }]);
    ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
    ui.openRoom(7);
    ui.respond('getMappingOverrides', ok(t));
    assert.deepEqual(ui.$('.j2ha-group-name strong').list.map((el) => ui.$(el).text()), ['Lumière', 'Alarme']);
    assert.deepEqual(ui.$('.j2ha-group-name .j2ha-tech').list.map((el) => ui.$(el).text()), ['light', 'alarm_control_panel']);
  });
});
