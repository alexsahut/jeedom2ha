'use strict';

// Front v2 — Lot 0 (socle) : ordre des scripts, points de montage invisibles tant qu'ils sont vides,
// modules chargeables sous node, aucune couleur en dur dans jeedom2ha_v2.css.

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..', '..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8');
const php = read('desktop/php/jeedom2ha.php');
const css = read('desktop/css/jeedom2ha_v2.css');

const MODULES = [
  ['jeedom2ha_lexique', 'Jeedom2haLexique'],
  ['jeedom2ha_ha_side', 'Jeedom2haHaSide'],
  ['jeedom2ha_guide', 'Jeedom2haGuide'],
  ['jeedom2ha_exclusions', 'Jeedom2haExclusions'],
  ['jeedom2ha_type_panel', 'Jeedom2haTypePanel'],
];

function includes(kind) {
  const re = new RegExp("include_file\\('desktop', '([a-z0-9_]+)', '" + kind + "', 'jeedom2ha'\\)", 'g');
  return [...php.matchAll(re)].map((m) => m[1]);
}

describe('Front v2 — Lot 0 : include_file de la page', () => {
  it('feuilles de style : jeedom2ha puis jeedom2ha_v2', () => {
    assert.deepEqual(includes('css'), ['jeedom2ha', 'jeedom2ha_v2']);
  });

  it('scripts dans l\'ordre prescrit', () => {
    assert.deepEqual(includes('js'), [
      'jeedom2ha_mapping_override',
      'jeedom2ha_lexique',
      'jeedom2ha_ha_side',
      'jeedom2ha_mapping_surface',
      'jeedom2ha_type_panel',
      'jeedom2ha_action_budget',
      'jeedom2ha_overview',
      'jeedom2ha_workview',
      'jeedom2ha_guide',
      'jeedom2ha_exclusions',
      'jeedom2ha',
    ]);
    assert.ok(php.indexOf("include_file('desktop', 'jeedom2ha', 'js'") < php.indexOf("include_file('core', 'plugin.template', 'js')"));
  });

  it('chaque script inclus existe', () => {
    for (const name of includes('js')) assert.ok(fs.existsSync(path.join(ROOT, 'desktop/js', name + '.js')), name);
    assert.ok(fs.existsSync(path.join(ROOT, 'desktop/css/jeedom2ha_v2.css')));
  });

  it('réglages courants transmis au JS', () => {
    assert.match(php, /sendVarToJS\('j2haExcludedPlugins', \(string\) config::byKey\('excludedPlugins', 'jeedom2ha', ''\)\)/);
    assert.match(php, /sendVarToJS\('j2haConfidencePolicy', \(string\) config::byKey\('confidencePolicy', 'jeedom2ha', 'sure_probable'\)\)/);
  });
});

describe('Front v2 — Lot 0 : points de montage', () => {
  const emptyDiv = (id) => new RegExp('<div id="' + id + '" class="[^"]+"[^>]*></div>');

  it('conteneurs vides présents', () => {
    for (const id of ['j2ha_v2_guide', 'j2ha_v2_helpline', 'j2ha_v2_todo', 'j2ha_v2_legend', 'j2ha_v2_toast']) {
      assert.match(php, emptyDiv(id), id);
      assert.equal(php.split('id="' + id + '"').length, 2, id + ' unique');
    }
    assert.match(php, /id="j2ha_v2_toast"[^>]*aria-live="polite"/);
  });

  it('positions : guide avant la vue principale, à faire et légende après le bloc maison, aide sous les actions', () => {
    const at = (s) => { const i = php.indexOf(s); assert.ok(i >= 0, s); return i; };
    assert.ok(at('id="j2ha_v2_guide"') < at('<div id="j2ha_mainView">'));
    assert.ok(at('id="div_haActions"') < at('id="j2ha_v2_helpline"'));
    assert.ok(at('id="j2ha_houseBlock"') < at('id="j2ha_v2_todo"'));
    assert.ok(at('id="j2ha_v2_todo"') < at('id="j2ha_v2_legend"'));
    assert.ok(at('id="j2ha_v2_legend"') < at('/#j2ha_mainView'));
  });

  // Garde levée au Lot 1 : les entrées réservées sont branchées dans le menu « Autres actions » (actives) et l'item
  // « Home Assistant » porte son libellé ; le conteneur réservé n'existe plus.
  it('bouton réservé masqué ; entrées du Lot 1 branchées dans le menu ; item Home Assistant libellé et masqué par défaut', () => {
    assert.match(php, /<button type="button" id="bt_j2haChoosePublished"[^>]* hidden>/);
    assert.ok(!php.includes('j2ha_v2_menuReserved'), 'plus de conteneur réservé');
    const menu = php.slice(php.indexOf('id="j2ha_moreMenu"'), php.indexOf('j2ha-menu-sep'));
    assert.match(menu, /id="bt_j2haCheckInstall" class="j2ha-menu-item" role="menuitem">/);
    assert.match(menu, /id="bt_j2haOpenGuide" class="j2ha-menu-item" role="menuitem">/);
    assert.match(php, /<div id="div_healthHa" class="j2ha-health-item" style="display:none;">\s*<strong>\{\{Home Assistant\}\}<\/strong>\s*<span id="span_healthHa"/);
  });

  it('CSS : les conteneurs vides ne s\'affichent pas', () => {
    for (const cls of ['guide', 'helpline', 'todo', 'legend', 'toast']) {
      assert.match(css, new RegExp('\\.j2ha-v2-' + cls + ':empty[,\\s{]'), cls);
    }
    assert.match(css, /\.j2ha-v2-guide:empty,[\s\S]*?\{\s*display: none;/);
  });
});

describe('Front v2 — Lot 0 : modules', () => {
  for (const [file, globalName] of MODULES) {
    it(file + ' : chargeable sous node et expose ' + globalName + ' dans la page', () => {
      const full = path.join(ROOT, 'desktop/js', file + '.js');
      delete require.cache[full];
      const mod = require(full);
      assert.equal(typeof mod, 'object');
      assert.ok(mod !== null);

      const src = fs.readFileSync(full, 'utf8');
      const root = {};
      // Hors node : la globale est posée sur la racine (window dans la page).
      new Function('globalThis', 'module', src)(root, undefined);
      assert.equal(typeof root[globalName], 'object', globalName);
      assert.doesNotMatch(src, /COMMAND_CAUSE_CATEGORIES|categoryOfCause|JSON\.stringify/);
    });
  }
});

describe('Front v2 — Lot 0 : jeedom2ha_v2.css', () => {
  const code = css.replace(/\/\*[\s\S]*?\*\//g, '');

  it('aucune couleur en dur (hexadécimal, rgb/hsl, nom de couleur)', () => {
    assert.doesNotMatch(code, /#[0-9a-fA-F]{3,8}\b/);
    assert.doesNotMatch(code, /\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(/);
    const named = /(?:^|[\s:,(])(white|black|red|green|blue|orange|gray|grey|yellow|purple|silver|navy)(?=[\s;,)!]|$)/im;
    assert.doesNotMatch(code, named);
  });

  it('les couleurs viennent des variables de thème', () => {
    const decls = [...code.matchAll(/(?:^|[;{\s])((?:background|color|border(?:-[a-z]+)*|box-shadow|outline)\s*:[^;}]+)/g)].map((m) => m[1]);
    assert.ok(decls.length > 20);
    assert.match(code, /var\(--j2ha-ok\)/);
    assert.match(code, /var\(--j2ha-warn\)/);
    assert.match(code, /var\(--j2ha-todo\)/);
  });

  it('composants de la maquette présents', () => {
    for (const cls of ['two', 'side', 'cause', 'steps', 'step', 'foot', 'toast', 'panel', 'diff']) {
      assert.match(code, new RegExp('\\.j2ha-v2-' + cls + '\\b'), cls);
    }
  });

  it('ne redéfinit aucune classe existante de jeedom2ha.css', () => {
    const selectors = [...code.matchAll(/\.(j2ha-[a-z0-9-]+)/g)].map((m) => m[1]);
    for (const s of selectors) assert.ok(s === 'j2ha-v2' || s.startsWith('j2ha-v2-'), s);
  });
});
