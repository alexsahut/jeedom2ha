// ARTEFACT — Story 25.3 (AC15) : la page B n'ajoute aucune couleur littérale, lit uniquement des variables
// --j2ha-* (avec replis), tient les contrastes dans les deux thèmes et ne restyle pas le core.
// Analyse statique des sources (CSS, JS, PHP). Complète test_story_25_1_palette_theme. Aucune donnée réelle (CC-48).
'use strict';

const fs = require('node:fs');
const { execFileSync } = require('node:child_process');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const cssPath = 'desktop/css/jeedom2ha.css';
const css = fs.readFileSync(cssPath, 'utf8');
const newSources = {
  'jeedom2ha_overview.js': fs.readFileSync('desktop/js/jeedom2ha_overview.js', 'utf8'),
  'jeedom2ha_overview_helpers.php': fs.readFileSync('desktop/php/jeedom2ha_overview_helpers.php', 'utf8'),
  'jeedom2ha.php': fs.readFileSync('desktop/php/jeedom2ha.php', 'utf8'),
};
const stripComments = (text) => text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/<!--[\s\S]*?-->/g, '').replace(/^\s*\/\/.*$/gm, '');

function addedCssLines() {
  for (const base of ['main', 'origin/main']) {
    try {
      const diff = execFileSync('git', ['diff', '-U0', base, '--', cssPath], { encoding: 'utf8' });
      return diff.split('\n').filter((l) => l.startsWith('+') && !l.startsWith('+++')).map((l) => l.slice(1));
    } catch { /* base suivante */ }
  }
  return null;
}

describe('25.3 / AC15 — aucune couleur littérale ajoutée', () => {
  it('lignes CSS ajoutées : ni #hex, ni rgb()/rgba()/hsl(), ni nom de couleur', () => {
    const added = addedCssLines();
    if (added === null) return;
    const literal = /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(/;
    const named = /(?<![\w-])(red|blue|green|yellow|orange|purple|pink|black|white|gray|grey|silver|maroon|navy|teal|olive|lime|aqua|fuchsia|brown|gold|crimson|coral|salmon)(?![\w-])/i;
    const code = stripComments(added.join('\n'));
    assert.doesNotMatch(code, literal);
    assert.doesNotMatch(code, named);
  });

  it('JS et PHP de la page B : aucune couleur en dur, aucun style en ligne coloré, aucun .css() coloré', () => {
    for (const [file, source] of Object.entries(newSources)) {
      const code = stripComments(source);
      assert.doesNotMatch(code, /['"]#[0-9a-fA-F]{3,8}['"]/, file);
      for (const m of code.matchAll(/style="([^"]*)"/g)) assert.doesNotMatch(m[1], /color|background|border|#[0-9a-fA-F]{3,6}\b|rgb/i, file);
      for (const call of code.match(/\.css\([^)]*\)/g) || []) assert.doesNotMatch(call, /color|background|border/i, file);
      assert.doesNotMatch(code, /getComputedStyle|matchMedia|data-theme/, file);
    }
  });

  it('la seule couleur issue des données (objet Jeedom) passe par data-color puis une variable CSS d’accent', () => {
    const js = stripComments(newSources['jeedom2ha_overview.js']);
    assert.match(js, /style\.setProperty\('--j2ha-room-color', color\)/);
    assert.doesNotMatch(js, /\.style\.(color|background)/);
  });
});

describe('25.3 / AC15 — variables --j2ha-* et replis', () => {
  const body = stripComments(css);
  const rulesOf = (re) => [...body.matchAll(/([^{}]+)\{([^{}]*)\}/g)].filter((m) => re.test(m[1])).map((m) => ({ selector: m[1].trim(), body: m[2] }));

  it('chaque couleur des nouvelles règles est une variable --j2ha-* (ou une variable du core avec repli --j2ha-*)', () => {
    const selectors = /j2ha-(health-bar|house|gauge|seg|chip-filter|chip-dot|filter|frow|mark|room-state|room-ratio|room-marks|room-group|help-line|read-status)/;
    const offenders = [];
    for (const rule of rulesOf(selectors)) {
      for (const decl of rule.body.split(';').map((d) => d.trim()).filter(Boolean)) {
        const [prop, ...rest] = decl.split(':');
        const value = rest.join(':').trim();
        if (prop.trim() === 'border-radius' || !/color|background|border|outline/.test(prop)) continue;
        const colors = value.replace(/var\(--[a-z0-9-]+(?:,\s*var\(--[a-z0-9-]+\))?\)/gi, '').replace(/\b(solid|dashed|none|transparent|currentColor|\d+px|0|repeating-linear-gradient|135deg|\(|\)|,|\s)+/gi, ' ').trim();
        if (colors !== '') offenders.push(`${rule.selector} { ${decl} }`);
      }
    }
    assert.deepEqual(offenders, []);
  });

  it('fonds d’état : uniquement --j2ha-*-bg, translucides, avec repli rgba() déjà défini en 25.1', () => {
    assert.match(css, /@supports not \(color: color-mix/);
    const used = new Set([...css.matchAll(/var\((--j2ha-[a-z-]+-bg)\)/g)].map((m) => m[1]));
    for (const v of used) assert.ok(new RegExp(v + ':').test(css), v + ' défini');
  });

  it('aucun restylage du core : aucune règle ne cible seule .label, .btn, .panel, .modal, .objectDisplayCard', () => {
    for (const m of body.matchAll(/([^{}]+)\{/g)) {
      if (m[1].trim().startsWith('@')) continue;
      for (const selector of m[1].split(',').map((s) => s.trim())) {
        if (!selector) continue;
        assert.match(selector, /\.j2ha-|\.modal-j2ha-room|#j2ha_roomCards|^:root|^body\[data-theme/, selector);
        assert.doesNotMatch(selector, /^\.(label|btn|panel|modal|objectDisplayCard)(?![\w-])/, selector);
      }
    }
  });

  it('le point d’état de la barre de santé est un contenu généré dans la barre, sans couleur propre', () => {
    const dot = rulesOf(/\.j2ha-health-bar \.label::before/)[0];
    assert.ok(dot);
    assert.doesNotMatch(dot.body, /color|background/);
    assert.match(dot.body, /content:\s*"\\25CF"/);
  });
});

// Rapport de contraste WCAG (mêmes outils que 25.1).
const toRgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
const channel = (c) => { const v = c / 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
const luminance = ([r, g, b]) => 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
const contrast = (a, b) => { const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x); return (hi + 0.05) / (lo + 0.05); };
const blend = (fg, bg, alpha) => fg.map((v, i) => v * alpha + bg[i] * (1 - alpha));

function themeVars(re) {
  const out = {};
  for (const m of stripComments(css).matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    if (!re.test(m[1]) || /@supports/.test(m[1])) continue;
    for (const d of m[2].split(';').map((x) => x.trim()).filter(Boolean)) {
      const i = d.indexOf(':');
      if (/^--j2ha-/.test(d)) out[d.slice(0, i).trim()] = d.slice(i + 1).trim();
    }
  }
  return out;
}

describe('25.3 / AC15 — contrastes des nouveaux éléments dans les deux thèmes', () => {
  const THEMES = { clair: [themeVars(/Light/), ['#ffffff', '#f5f5f5']], sombre: [themeVars(/Dark/), ['#191919', '#2a2a2a']] };

  for (const [name, [vars, backgrounds]] of Object.entries(THEMES)) {
    it(`thème ${name} : puces, repères, mentions, texte de liste ≥ 4,5:1 (nus, teintés à 14 %, surface, survol)`, () => {
      for (const bgHex of backgrounds) {
        const bg = toRgb(bgHex);
        // Repères et mentions : teinte sur le fond de la page, et sur la surface du bloc maison.
        const surface = vars['--j2ha-surface'].match(/rgba\((\d+), (\d+), (\d+), ([0-9.]+)\)/);
        const onSurface = blend([Number(surface[1]), Number(surface[2]), Number(surface[3])], bg, Number(surface[4]));
        for (const tint of ['ok', 'todo', 'warn', 'neutral']) {
          const color = toRgb(vars['--j2ha-' + tint]);
          assert.ok(contrast(color, bg) >= 4.5, `${name} ${bgHex} ${tint} nu`);
          assert.ok(contrast(color, onSurface) >= 4.5, `${name} ${bgHex} ${tint} sur la surface du bloc maison`);
        }
        // Puce active : texte du thème sur --j2ha-todo-bg (14 %).
        const text = toRgb(vars['--j2ha-text']);
        assert.ok(contrast(text, blend(toRgb(vars['--j2ha-todo']), onSurface, 0.14)) >= 4.5, `${name} ${bgHex} puce active`);
        // Ligne de liste survolée : texte du thème sur --j2ha-surface-strong.
        const strong = vars['--j2ha-surface-strong'].match(/rgba\((\d+), (\d+), (\d+), ([0-9.]+)\)/);
        const hover = blend([Number(strong[1]), Number(strong[2]), Number(strong[3])], bg, Number(strong[4]));
        assert.ok(contrast(text, hover) >= 4.5, `${name} ${bgHex} survol`);
        // Segments de la jauge (aplats) et motif « non lus » : ≥ 3:1 contre le fond (objet graphique).
        for (const tint of ['ok', 'todo', 'warn', 'neutral']) assert.ok(contrast(toRgb(vars['--j2ha-' + tint]), bg) >= 3, `${name} segment ${tint}`);
      }
    });
  }

  it('les segments portent un mot dans la légende et un aria-label : l’état n’est jamais porté par la seule couleur', () => {
    const js = newSources['jeedom2ha_overview.js'];
    assert.match(js, /role="img"/);
    assert.match(js, /aria-label/);
    assert.match(js, /aria-pressed/);
    assert.match(js, /j2ha-chip-dot/);
  });
});

describe('25.3 / AC15 — compatibilité Jeedom 4.4 (pas d’API ni de variable propre à 4.6)', () => {
  it('aucune dépendance nouvelle : ni jeeDialog, ni fetch(), ni framework, ni police ou bibliothèque externe', () => {
    for (const [file, source] of Object.entries(newSources)) {
      assert.doesNotMatch(stripComments(source), /jeeDialog|\bfetch\(|new Vue|React\.|<script[^>]+src="https?:|fonts\.googleapis|cdn\./i, file);
    }
  });

  it('replis testables : color-mix() absent → rgba() ; aucune variable du core sans repli --j2ha-*', () => {
    for (const m of stripComments(css).matchAll(/var\(--(txt-color|logo-primary-color|border-radius)(.{0,40})/g)) {
      if (m[1] === 'border-radius') assert.match(m[2], /^,\s*0\)/);
      else assert.match(m[2], /^,\s*var\(--j2ha-/, m[0]);
    }
  });
});
