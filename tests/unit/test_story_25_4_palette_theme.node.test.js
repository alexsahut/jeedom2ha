// ARTEFACT — Story 25.4 (AC23) : la vue C n'ajoute aucune couleur littérale, lit uniquement des variables --j2ha-* (avec
// replis), tient les contrastes dans les deux thèmes, respecte var(--border-radius) et ses replis (color-mix, dvh, sticky)
// et ne restyle pas le core. Successeur de test_story_25_3_palette_theme. Analyse statique des sources. Aucune donnée réelle.
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { selectorTable } = require('./helpers/capture_story_25_4_references');

const root = path.join(__dirname, '..', '..');
const css = fs.readFileSync(path.join(root, 'desktop/css/jeedom2ha.css'), 'utf8');
const baseline = JSON.parse(fs.readFileSync(path.join(root, 'tests/fixtures/story_25_4_css_baseline.json'), 'utf8'));
const table = selectorTable(css);
const stripComments = (text) => text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/<!--[\s\S]*?-->/g, '').replace(/^\s*\/\/.*$/gm, '');
const added = Object.entries(table).filter(([key]) => !(key in baseline.selectors));
const js = stripComments(fs.readFileSync(path.join(root, 'desktop/js/jeedom2ha_workview.js'), 'utf8'));

describe('25.4 / AC23 — aucune couleur littérale ajoutée', () => {
  it('règles CSS ajoutées : ni #hex, ni rgb()/rgba()/hsl(), ni nom de couleur', () => {
    assert.ok(added.length > 20);
    const literal = /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(/;
    const named = /(?<![\w-])(red|blue|green|yellow|orange|purple|pink|black|white|gray|grey|silver|maroon|navy|teal|olive|lime|aqua|fuchsia|brown|gold|crimson|coral|salmon)(?![\w-])/i;
    for (const [key, declarations] of added) {
      assert.doesNotMatch(declarations, literal, key);
      assert.doesNotMatch(declarations, named, key);
    }
  });

  it('les variables --j2ha-* ne sont ni ajoutées ni modifiées : la vue lit celles de 25.1 / 25.3', () => {
    for (const key of Object.keys(baseline.selectors).filter((k) => /^(:root|body\[data-theme)/.test(k.replace(/^.*\| /, '')))) {
      assert.equal(table[key], baseline.selectors[key], key);
    }
    for (const [, declarations] of added) assert.doesNotMatch(declarations, /(^|;)--j2ha-[a-z-]+:(?!.*var\()/);
  });

  it('chaque couleur ajoutée est une variable --j2ha-* (ou une variable du core suivie d’un repli --j2ha-*)', () => {
    for (const [key, declarations] of added) {
      for (const decl of declarations.split(';').filter(Boolean)) {
        const [property, ...rest] = decl.split(':');
        const value = rest.join(':').trim();
        if (!/^(color|background(-color)?|border(-(top|right|bottom|left))?(-color)?|outline|box-shadow|fill|stroke)$/.test(property.trim())) continue;
        let flat = value;
        for (let i = 0; i < 6; i += 1) flat = flat.replace(/var\(--[a-z0-9-]+(?:,\s*[^()]*)?\)/gi, '');
        const leftover = flat
          .replace(/\b(solid|dashed|none|transparent|inherit|currentColor|\d+px|0|\(|\)|,|\s|!important)+/gi, ' ').trim();
        assert.equal(leftover, '', `${key} { ${decl} }`);
      }
    }
  });

  it('JS de la vue : aucune couleur en dur, aucun style en ligne coloré, aucun .css() coloré ; la couleur d’objet passe par une variable d’accent', () => {
    assert.doesNotMatch(js, /['"]#[0-9a-fA-F]{3,8}['"]/);
    for (const m of js.matchAll(/style="([^"]*)"/g)) assert.doesNotMatch(m[1], /color|background|border|#[0-9a-fA-F]{3,6}\b|rgb/i);
    for (const call of js.match(/\.css\([^)]*\)/g) || []) assert.doesNotMatch(call, /color|background|border/i);
    assert.match(js, /style\.setProperty\('--j2ha-room-color', room\.color\)/);
    assert.doesNotMatch(js, /\.style\.(color|background)/);
    assert.doesNotMatch(js, /getComputedStyle|prefers-color-scheme|data-theme/);
  });
});

describe('25.4 / AC23 — accent d’objet, rayon, replis', () => {
  it('la couleur Jeedom d’un objet est un accent d’icône ou de filet : jamais le fond ni le texte', () => {
    for (const [key, declarations] of added) {
      if (!/--j2ha-room-color/.test(declarations)) continue;
      assert.doesNotMatch(declarations, /background(-color)?:[^;]*--j2ha-room-color/, key);
      if (/(^|;)color:[^;]*--j2ha-room-color/.test(declarations)) assert.match(key, /\.j2ha-wv-(icon|roomicon)$/, key);
      assert.match(declarations, /var\(--j2ha-room-color, var\(--(?:j2ha-|logo-primary-color)/);
    }
  });

  it('var(--border-radius) est respecté (angles droits du thème sombre) : jamais de rayon en dur', () => {
    for (const [key, declarations] of added) {
      for (const m of declarations.matchAll(/border-radius:([^;]*)/g)) assert.match(m[1], /var\(--border-radius, 0\)/, key);
    }
  });

  it('replis : color-mix() absent (rgba déjà défini), dvh → vh, sticky → -webkit-sticky', () => {
    assert.match(css, /@supports not \(color: color-mix/);
    assert.match(css, /@supports \(height: 100dvh\)/);
    assert.match(css, /height: var\(--j2ha-wv-height, calc\(100vh - 160px\)\)/);
    assert.match(css, /position: -webkit-sticky;[^}]*position: sticky;/);
    assert.doesNotMatch(css, /color-mix\([^)]*\)[^;]*;\s*\n\s*\.j2ha-wv/); // aucun nouveau color-mix : les fonds d'état lisent --j2ha-*-bg
  });

  it('aucun restylage du core : aucune règle nouvelle ne cible .label, .btn, .panel, .modal, .objectDisplayCard, ni un sélecteur nu partagé', () => {
    for (const [key] of added) {
      const selector = key.replace(/^.*\| /, '');
      assert.doesNotMatch(selector, /^\.(label|btn|panel|modal|objectDisplayCard)(?![\w-])/, selector);
      // Story 25.7 (AC8) : l'unique exception est le repère de carte, sur sa classe nouvelle, sous .j2ha-room-groups.
      if (selector === '.j2ha-room-groups .j2ha-mark.j2ha-mark-excluded') continue;
      // Story 25.8 : menu « ⋯ » de la carte et ligne « Pièce exclue » (classes nouvelles, sous .j2ha-room-groups).
      if (/^\.j2ha-room-groups \.j2ha-room-(card\.j2ha-room-has-menu|card \.j2ha-room-menu(-toggle|-list)?|excluded-line)/.test(selector)) continue;
      assert.match(selector, /^\.j2ha-wv/, selector);
    }
  });
});

// Rapport de contraste WCAG (mêmes outils que 25.1) : les variables sont lues dans le CSS.
const toRgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
const channel = (c) => { const v = c / 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
const luminance = ([r, g, b]) => 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
const contrast = (a, b) => { const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x); return (hi + 0.05) / (lo + 0.05); };
const blend = (fg, bg, alpha) => fg.map((v, i) => v * alpha + bg[i] * (1 - alpha));

function themeVars(selectorStart) {
  const out = {};
  for (const [key, declarations] of Object.entries(table)) {
    if (key.includes('@supports') || !key.replace(/^.*\| /, '').startsWith(selectorStart)) continue;
    for (const d of declarations.split(';').filter(Boolean)) {
      const i = d.indexOf(':');
      if (/^--j2ha-/.test(d)) out[d.slice(0, i).trim()] = d.slice(i + 1).trim();
    }
  }
  return out;
}

describe('25.4 / AC23 — contrastes des nouveaux éléments dans les deux thèmes (texte ≥ 4,5:1)', () => {
  const themes = [
    ['clair', themeVars(':root'), [255, 255, 255]],
    ['sombre', Object.assign({}, themeVars(':root'), themeVars('body[data-theme*="Dark"]')), [25, 25, 25]],
  ];
  for (const [name, vars, page] of themes) {
    it(`thème ${name} : mot d’état, cause (orange), sélection, KPI, repères`, () => {
      const rgb = (v) => toRgb(vars[v]);
      // Lignes d'arbre et liste « À traiter » : mots d'état et causes sur le fond de la page.
      for (const tint of ['ok', 'todo', 'warn', 'neutral']) {
        assert.ok(contrast(rgb('--j2ha-' + tint), page) >= 4.5, `${tint} sur la page (${name})`);
        // Fond translucide d'état (14 %) : KPI et sélection.
        assert.ok(contrast(rgb('--j2ha-' + tint), blend(rgb('--j2ha-' + tint), page, 0.14)) >= 4.5, `${tint} sur son fond (${name})`);
      }
      assert.ok(contrast(rgb('--j2ha-text'), page) >= 4.5);
      // Ligne sélectionnée : texte courant sur fond translucide bleu.
      assert.ok(contrast(rgb('--j2ha-text'), blend(rgb('--j2ha-todo'), page, 0.14)) >= 4.5, `texte sur sélection (${name})`);
      // Anneau de focus et filet de sélection (icônes / bordures ≥ 3:1).
      assert.ok(contrast(rgb('--j2ha-todo'), page) >= 3);
    });
  }
});
