// ARTEFACT — Story 25.1 (AC17 à AC21, AC25) : palette sémantique à quatre teintes sur variables du
// thème Jeedom, clair ET sombre, sans couleur en dur, contrastes mesurés, jamais de restylage du core.
// Analyse statique des sources (CSS, JS, PHP) ; aucune donnée d'équipement (CC-48).
'use strict';

const fs = require('node:fs');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const css = fs.readFileSync('desktop/css/jeedom2ha.css', 'utf8');
const php = fs.readFileSync('desktop/php/jeedom2ha.php', 'utf8');
const jsFiles = fs.readdirSync('desktop/js').filter((f) => f.endsWith('.js'));
const jsSources = Object.fromEntries(jsFiles.map((f) => [f, fs.readFileSync('desktop/js/' + f, 'utf8')]));

const stripCssComments = (text) => text.replace(/\/\*[\s\S]*?\*\//g, '');
const stripJsComments = (text) => text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

/** Règles CSS à plat : { selector, body, atRule } (les @supports sont aplatis avec leur condition). */
function parseRules(source) {
  const text = stripCssComments(source);
  const rules = [];
  function walk(chunk, atRule) {
    let i = 0;
    while (i < chunk.length) {
      const open = chunk.indexOf('{', i);
      if (open === -1) break;
      const selector = chunk.slice(i, open).trim();
      let depth = 1;
      let j = open + 1;
      while (j < chunk.length && depth > 0) {
        if (chunk[j] === '{') depth += 1;
        else if (chunk[j] === '}') depth -= 1;
        j += 1;
      }
      const body = chunk.slice(open + 1, j - 1);
      if (selector.startsWith('@supports') || selector.startsWith('@media')) walk(body, selector);
      else rules.push({ selector, body, atRule: atRule || null });
      i = j;
    }
  }
  walk(text, null);
  return rules;
}

const declarations = (body) => body.split(';').map((d) => d.trim()).filter(Boolean).map((d) => {
  const at = d.indexOf(':');
  return { property: d.slice(0, at).trim(), value: d.slice(at + 1).trim() };
});

const rules = parseRules(css);
const isVariableBlock = (rule) => declarations(rule.body).every((d) => /^--j2ha-/.test(d.property));
const NAMED_COLORS = ['red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'black', 'white', 'gray', 'grey', 'silver',
  'maroon', 'navy', 'teal', 'olive', 'lime', 'aqua', 'fuchsia', 'brown', 'gold', 'crimson', 'coral', 'salmon'];

describe('25.1 / AC17 — aucune couleur en dur hors des blocs de variables --j2ha-*', () => {
  it('CSS : aucun littéral (#hex, rgb(), rgba(), hsl(), nom de couleur) hors blocs de variables', () => {
    const literal = /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(/;
    const named = new RegExp('(?<![\\w-])(' + NAMED_COLORS.join('|') + ')(?![\\w-])', 'i');
    const offenders = [];
    for (const rule of rules) {
      if (isVariableBlock(rule)) continue;
      for (const d of declarations(rule.body)) {
        if (d.property === 'content') continue;
        if (literal.test(d.value) || named.test(d.value)) offenders.push(`${rule.selector} { ${d.property}: ${d.value} }`);
      }
    }
    assert.deepEqual(offenders, []);
  });

  it('les blocs de définition sont de la forme body[data-theme*="Dark"] / body[data-theme*="Light"] (et leur repli)', () => {
    const blocks = rules.filter(isVariableBlock).map((r) => r.selector.replace(/\s+/g, ' '));
    assert.ok(blocks.some((s) => /body\[data-theme\*="Dark"\]/.test(s)));
    assert.ok(blocks.some((s) => /body\[data-theme\*="Light"\]/.test(s)));
    for (const selector of blocks) assert.match(selector, /^(:root,\s*)?body\[data-theme\*="(Dark|Light)"\]$|^:root$|^:root, body\[data-theme\*="Light"\]$/);
  });

  it('JS et PHP : aucun style en ligne ni .css() portant une couleur, un fond ou une bordure colorée', () => {
    const inlineStyle = /style="([^"]*)"/g;
    const colored = /color|background|border|#[0-9a-fA-F]{3,6}\b|rgb/i;
    const sources = { 'jeedom2ha.php': php, ...jsSources };
    for (const [file, source] of Object.entries(sources)) {
      const code = file.endsWith('.js') ? stripJsComments(source) : source.replace(/<!--[\s\S]*?-->/g, '');
      let m;
      while ((m = inlineStyle.exec(code)) !== null) assert.doesNotMatch(m[1], colored, `${file} : style="${m[1]}"`);
      for (const call of code.match(/\.css\([^)]*\)/g) || []) assert.doesNotMatch(call, colored, `${file} : ${call}`);
      assert.doesNotMatch(code.replace(/'#[A-Za-z_][\w-]*'/g, ''), /['"]#[0-9a-fA-F]{6}['"]|['"]#[0-9a-fA-F]{3}['"]/, file + ' : couleur hexadécimale en dur');
    }
  });

  it('la largeur se règle par des classes CSS ; plus d’appel .css(\'width\') en ligne (Story 25.4 : vue C, plus de fenêtre)', () => {
    assert.doesNotMatch(stripJsComments(jsSources['jeedom2ha_mapping_surface.js']), /\.css\(\s*'width'/);
    assert.doesNotMatch(stripJsComments(jsSources['jeedom2ha_workview.js']), /\.css\(\s*'(width|height)'/);
    // Remplace la largeur de 90 % de la fenêtre : la largeur de l'arbre de la vue C est portée par une règle CSS.
    const nav = rules.find((r) => r.selector === '.j2ha-wv-nav' && r.atRule);
    assert.ok(nav && /flex:\s*0 0 320px/.test(nav.body), 'largeur de l’arbre en disposition large');
  });

  it('toute variable de couleur du core est suivie d’un repli --j2ha-*', () => {
    const core = ['al-success-color', 'al-warning-color', 'al-danger-color', 'al-info-color', 'txt-color', 'bg-modal-color', 'bg-color', 'link-color', 'logo-primary-color'];
    const text = stripCssComments(css);
    for (const name of core) {
      for (const m of text.matchAll(new RegExp('var\\(--' + name + '(.{0,40})', 'g'))) {
        assert.match(m[1], /^,\s*var\(--j2ha-/, `--${name} sans repli --j2ha-* : ${m[0]}`);
      }
    }
    assert.ok(/var\(--link-color, var\(--j2ha-/.test(text), 'au moins une variable du core est effectivement lue');
  });
});

/** Valeurs des variables --j2ha-* d'un thème, lues dans le CSS (blocs « Light » incluant le repli « :root »). */
function themeVariables(themeRe) {
  const out = {};
  for (const rule of rules) {
    if (!isVariableBlock(rule) || rule.atRule || !themeRe.test(rule.selector)) continue;
    for (const d of declarations(rule.body)) out[d.property] = d.value;
  }
  return out;
}
const light = themeVariables(/Light/);
const dark = themeVariables(/Dark/);

describe('25.1 / AC18 — quatre teintes sémantiques, fonds translucides, repli', () => {
  const TINTS = ['ok', 'todo', 'warn', 'neutral'];

  it('exactement les quatre teintes --j2ha-ok / -todo / -warn / -neutral, définies pour les deux thèmes', () => {
    for (const [name, theme] of [['clair', light], ['sombre', dark]]) {
      for (const tint of TINTS) assert.match(theme['--j2ha-' + tint] || '', /^#[0-9a-f]{6}$/i, `${name} : --j2ha-${tint}`);
      assert.match(theme['--j2ha-danger'] || '', /^#[0-9a-f]{6}$/i, name + ' : rouge réservé à la zone destructive');
    }
    const defined = new Set(rules.filter((r) => isVariableBlock(r)).flatMap((r) => declarations(r.body).map((d) => d.property)));
    const colorTints = [...defined].filter((p) => /^--j2ha-[a-z]+$/.test(p));
    assert.deepEqual(colorTints.sort(), ['--j2ha-danger', '--j2ha-highlight', '--j2ha-line', '--j2ha-neutral', '--j2ha-ok', '--j2ha-surface', '--j2ha-text', '--j2ha-todo', '--j2ha-warn'].sort());
  });

  it('le rouge n’est utilisé que par la zone destructive (menu « ⋯ »)', () => {
    const users = rules.filter((r) => !isVariableBlock(r) && /var\(--j2ha-danger\)/.test(r.body)).map((r) => r.selector);
    assert.deepEqual(users, ['.j2ha-menu-item.j2ha-menu-danger']);
  });

  it('fonds d’état translucides par color-mix(in srgb, … 14%, transparent), repli rgba() sous @supports not', () => {
    for (const theme of [light, dark]) {
      for (const tint of TINTS) {
        assert.equal(theme[`--j2ha-${tint}-bg`], `color-mix(in srgb, var(--j2ha-${tint}) 14%, transparent)`);
      }
    }
    const fallbacks = rules.filter((r) => /@supports not/.test(r.atRule || '') && isVariableBlock(r));
    assert.equal(fallbacks.length, 2, 'un repli par thème');
    for (const fallback of fallbacks) {
      for (const tint of TINTS) {
        const value = declarations(fallback.body).find((d) => d.property === `--j2ha-${tint}-bg`).value;
        assert.match(value, /^rgba\(\d+, \d+, \d+, 0\.14\)$/);
      }
    }
  });

  it('les rgba() de repli reproduisent les teintes de chaque thème (même couleur, même opacité)', () => {
    const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)).join(', ');
    for (const fallback of rules.filter((r) => /@supports not/.test(r.atRule || ''))) {
      const theme = /Dark/.test(fallback.selector) ? dark : light;
      for (const tint of TINTS) {
        const value = declarations(fallback.body).find((d) => d.property === `--j2ha-${tint}-bg`).value;
        assert.equal(value, `rgba(${rgb(theme['--j2ha-' + tint])}, 0.14)`, fallback.selector + ' ' + tint);
      }
    }
  });

  it('aucun fond opaque pastel : tout fond d’état lit un --j2ha-*-bg, transparent ou une surface translucide', () => {
    for (const rule of rules) {
      if (isVariableBlock(rule)) continue;
      for (const d of declarations(rule.body)) {
        if (!/^background(-color)?$/.test(d.property)) continue;
        assert.match(d.value, /^(transparent|var\(--j2ha-(ok|todo|warn|neutral)-bg\)|var\(--j2ha-surface(-strong)?\)|var\(--j2ha-menu-bg\)|var\(--j2ha-line\)|var\(--j2ha-highlight\)( !important)?|var\(--(bg-modal-color|bg-color), var\(--j2ha-menu-bg\)\)|var\(--j2ha-(ok|todo|warn|neutral|danger)\))$/, `${rule.selector} { ${d.property}: ${d.value} }`);
      }
    }
  });

  it('« Bloqué » est l’état le plus visible : gras et bordure pleine ; « Publié » est discret (sans bordure)', () => {
    const blocked = rules.find((r) => r.selector === '.j2ha-badge.j2ha-state-blocked');
    const published = rules.find((r) => r.selector === '.j2ha-badge.j2ha-state-published');
    assert.match(blocked.body, /border:\s*1px solid var\(--j2ha-warn\)/);
    assert.match(blocked.body, /font-weight:\s*700/);
    assert.doesNotMatch(published.body, /border|font-weight/);
    assert.match(published.body, /background-color:\s*transparent/);
  });

  it('« Désactivé » est en italique', () => {
    assert.ok(rules.some((r) => /\.j2ha-badge\.j2ha-state-disabled/.test(r.selector) && /font-style:\s*italic/.test(r.body)));
  });
});

// Rapport de contraste WCAG.
const toRgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
const channel = (c) => { const v = c / 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
const luminance = ([r, g, b]) => 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
const contrast = (a, b) => { const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x); return (hi + 0.05) / (lo + 0.05); };
const blend = (fg, bg, alpha) => fg.map((v, i) => v * alpha + bg[i] * (1 - alpha));

describe('25.1 / AC19 — contrastes mesurés dans les deux thèmes', () => {
  // Fonds de référence. Sombre : --bg-color 25,25,25 relevé sur Jeedom 4.6.1 (story 25.1, AC19) ; plus un
  // fond de panneau un cran plus clair. Clair : la valeur de --bg-color du thème clair devait être relevée
  // à la Task 0 (hors de portée d'une session cloud, CC-48) : on contrôle donc le blanc ET un gris de
  // panneau Bootstrap, plus défavorable. À reconfirmer par ClaudeBox lors de la preuve terrain.
  const BACKGROUNDS = {
    clair: ['#ffffff', '#f5f5f5'],
    sombre: ['#191919', '#2a2a2a'],
  };
  const THEMES = { clair: light, sombre: dark };

  for (const [name, backgrounds] of Object.entries(BACKGROUNDS)) {
    it(`thème ${name} : texte d’état ≥ 4,5:1 sur son fond (nu et teinté à 14 %), bordures et icônes ≥ 3:1`, () => {
      for (const bgHex of backgrounds) {
        const bg = toRgb(bgHex);
        for (const tint of ['ok', 'todo', 'warn', 'neutral', 'danger']) {
          const color = toRgb(THEMES[name]['--j2ha-' + tint]);
          assert.ok(contrast(color, bg) >= 4.5, `${name} ${bgHex} ${tint} sur fond nu : ${contrast(color, bg).toFixed(2)}`);
          const tinted = blend(color, bg, 0.14);
          const need = tint === 'danger' ? 3 : 4.5; // le rouge n'est jamais sur fond teinté (menu opaque)
          assert.ok(contrast(color, tinted) >= need, `${name} ${bgHex} ${tint} sur fond teinté : ${contrast(color, tinted).toFixed(2)}`);
          assert.ok(contrast(color, bg) >= 3, `${name} ${tint} bordure/icône`);
        }
      }
    });
  }

  it('le rouge destructif reste lisible sur le fond du menu de chaque thème', () => {
    for (const [name, theme] of Object.entries(THEMES)) {
      assert.ok(contrast(toRgb(theme['--j2ha-danger']), toRgb(theme['--j2ha-menu-bg'])) >= 4.5, name);
    }
  });

  it('la surbrillance de la ligne ciblée est une variable translucide lisible en sombre comme en clair', () => {
    const text = { clair: '#222222', sombre: '#e0e0e0' };
    for (const [name, theme] of Object.entries(THEMES)) {
      const m = theme['--j2ha-highlight'].match(/^rgba\((\d+), (\d+), (\d+), ([0-9.]+)\)$/);
      assert.ok(m, name + ' : rgba attendu');
      const alpha = Number(m[4]);
      assert.ok(alpha > 0 && alpha < 1);
      for (const bgHex of BACKGROUNDS[name]) {
        const over = blend([Number(m[1]), Number(m[2]), Number(m[3])], toRgb(bgHex), alpha);
        assert.ok(contrast(toRgb(text[name]), over) >= 4.5, `${name} ${bgHex} : ${contrast(toRgb(text[name]), over).toFixed(2)}`);
      }
    }
    const rule = rules.find((r) => r.selector === '.j2ha-diag-target-highlight > td');
    assert.match(rule.body, /var\(--j2ha-highlight\)/);
  });

  it('les gris #555 #666 #888 #999 (< 3:1 sur fond sombre) n’existent plus', () => {
    assert.doesNotMatch(css, /#(555|666|888|999)\b/);
  });
});

describe('25.1 / AC19 (R2-1) — texte du contrôle segmenté lisible dans les trois états et les deux thèmes', () => {
  const ruleBody = (selector) => (rules.find((r) => r.selector === selector) || { body: '' }).body;
  const prop = (body, name) => (declarations(body).find((d) => d.property === name) || {}).value;
  const BACKGROUNDS = { clair: ['#ffffff', '#f5f5f5'], sombre: ['#191919', '#2a2a2a'] };
  const THEMES = { clair: light, sombre: dark };
  // Teinte portée par le segment actif de chaque catégorie.
  const ACTIVE_TINT = { auto: 'ok', always: 'todo', never: 'neutral' };

  it('le texte d’un segment vient d’une variable de thème, pas de l’héritage Bootstrap', () => {
    const base = ruleBody('.j2ha-seg-btn');
    assert.match(prop(base, 'color'), /^var\(--txt-color, var\(--j2ha-[a-z-]+\)\)$/);
    assert.doesNotMatch(prop(base, 'color'), /inherit/);
  });

  it('le segment désactivé est atténué par opacité, sans couleur de texte propre', () => {
    const body = ruleBody('.j2ha-seg-btn.j2ha-seg-disabled');
    const opacity = Number(prop(body, 'opacity'));
    assert.ok(opacity > 0 && opacity < 1, 'opacity attendue : ' + opacity);
    assert.equal(prop(body, 'color'), undefined);
  });

  it('le segment actif prend la teinte de sa catégorie (Automatique / Toujours / Jamais)', () => {
    for (const [key, tint] of Object.entries(ACTIVE_TINT)) {
      const selector = key === 'always' ? '.j2ha-seg-btn.j2ha-seg-active' : `.j2ha-seg-btn.j2ha-seg-active.j2ha-seg-${key}`;
      const body = ruleBody(selector);
      assert.equal(prop(body, 'color'), `var(--j2ha-${tint})`, key);
      assert.equal(prop(body, 'background-color'), `var(--j2ha-${tint}-bg)`, key);
    }
  });

  for (const [name, backgrounds] of Object.entries(BACKGROUNDS)) {
    it(`thème ${name} : texte des segments actif / disponible ≥ 4,5:1, désactivé atténué ≥ 3:1`, () => {
      const theme = THEMES[name];
      const opacity = Number(prop(ruleBody('.j2ha-seg-btn.j2ha-seg-disabled'), 'opacity'));
      const base = prop(ruleBody('.j2ha-seg-btn'), 'color');
      assert.match(base, /var\(--j2ha-([a-z-]+)\)\)$/);
      const fallbackVar = '--j2ha-' + base.match(/var\(--j2ha-([a-z-]+)\)\)$/)[1];
      for (const bgHex of backgrounds) {
        const bg = toRgb(bgHex);
        // Disponible : texte du thème (repli) sur le fond nu.
        const text = toRgb(theme[fallbackVar]);
        assert.ok(contrast(text, bg) >= 4.5, `${name} ${bgHex} disponible : ${contrast(text, bg).toFixed(2)}`);
        // Désactivé : même texte, atténué par l'opacité.
        const faded = blend(text, bg, opacity);
        assert.ok(contrast(faded, bg) >= 3, `${name} ${bgHex} désactivé : ${contrast(faded, bg).toFixed(2)}`);
        // Actif : teinte de la catégorie sur son fond teinté à 14 %.
        for (const [key, tint] of Object.entries(ACTIVE_TINT)) {
          const color = toRgb(theme['--j2ha-' + tint]);
          const tinted = blend(color, bg, 0.14);
          assert.ok(contrast(color, tinted) >= 4.5, `${name} ${bgHex} actif ${key} : ${contrast(color, tinted).toFixed(2)}`);
        }
      }
    });
  }
});

describe('25.1 / AC20 — ne jamais restyler le core ; arrondi du thème', () => {
  it('tous les sélecteurs sont préfixés .j2ha- ou limités à .modal-j2ha-room / #j2ha_roomCards', () => {
    const offenders = [];
    for (const rule of rules) {
      if (isVariableBlock(rule)) continue;
      for (const selector of rule.selector.split(',').map((s) => s.trim())) {
        if (!/\.j2ha-|\.modal-j2ha-room|#j2ha_roomCards/.test(selector)) offenders.push(selector);
        // Aucune règle ne cible seule .label, .btn, .panel, .modal, .objectDisplayCard.
        assert.doesNotMatch(selector, /^\.(label|btn|panel|modal|objectDisplayCard)(?![\w-])/, selector);
      }
    }
    assert.deepEqual(offenders, []);
  });

  it('les rayons de bordure utilisent var(--border-radius, 0) (le thème sombre est à angles droits)', () => {
    let seen = 0;
    for (const rule of rules) {
      for (const d of declarations(rule.body)) {
        if (d.property === 'border-radius') {
          seen += 1;
          assert.equal(d.value, 'var(--border-radius, 0)', rule.selector);
        }
      }
    }
    assert.ok(seen > 3);
  });

  it('aucune police ni bibliothèque externe ; chiffres en tabular-nums ; icônes Font Awesome 5 locales', () => {
    assert.doesNotMatch(css, /@import|@font-face|url\(\s*['"]?https?:/);
    assert.match(css, /font-variant-numeric:\s*tabular-nums/);
    for (const [file, source] of Object.entries({ php, ...jsSources })) {
      assert.doesNotMatch(source, /<script[^>]+src="https?:|<link[^>]+href="https?:|fonts\.googleapis|cdn\./i, file);
    }
    const icons = (Object.values(jsSources).join('\n') + php).match(/fa-[a-z-]+/g) || [];
    assert.ok(icons.length > 0);
  });
});

describe('25.1 / AC21 — thème : bascule et état initial', () => {
  it('aucune couleur n’est calculée ni figée en JS : uniquement des variables CSS', () => {
    for (const [file, source] of Object.entries(jsSources)) {
      const code = stripJsComments(source);
      assert.doesNotMatch(code, /getComputedStyle|prefers-color-scheme|data-theme|\.css\(\s*['"](color|background)/, file);
      // Story 25.4 : seule la vue de travail interroge matchMedia, pour la DISPOSITION (largeur), jamais pour un thème.
      if (file !== 'jeedom2ha_workview.js') assert.doesNotMatch(code, /matchMedia/, file);
      else assert.deepEqual([...code.matchAll(/matchMedia\(([^)]*)\)/g)].map((m) => /min-width/.test(m[1])), [true]);
    }
  });

  it('attribut data-theme absent ou inconnu : le jeu clair s’applique (jeu de repli sans sélecteur de thème)', () => {
    const fallback = rules.find((r) => isVariableBlock(r) && !r.atRule && /^:root/.test(r.selector));
    assert.ok(fallback, 'un bloc :root existe');
    const vars = Object.fromEntries(declarations(fallback.body).map((d) => [d.property, d.value]));
    for (const tint of ['ok', 'todo', 'warn', 'neutral', 'danger']) {
      assert.equal(vars['--j2ha-' + tint], light['--j2ha-' + tint], tint + ' : le repli est le jeu clair');
    }
    // Le sombre ne s'applique que sur body[data-theme*="Dark"], donc jamais par défaut.
    const darkRule = rules.find((r) => isVariableBlock(r) && !r.atRule && /Dark/.test(r.selector));
    assert.doesNotMatch(darkRule.selector, /:root/);
  });
});

describe('25.1 / AC25 — compatibilité Jeedom 4.4', () => {
  it('plugin_info/info.json exige toujours 4.4', () => {
    assert.equal(JSON.parse(fs.readFileSync('plugin_info/info.json', 'utf8')).require, '4.4');
  });

  it('seulement jQuery, Bootstrap 3, bootbox, jeedomUtils et Font Awesome 5 ; jeeDialog n’est pas introduit', () => {
    for (const [file, source] of Object.entries(jsSources)) {
      assert.doesNotMatch(stripJsComments(source), /jeeDialog|\bfetch\(|new Vue|React\./, file);
      assert.doesNotMatch(source, /\bfab fa-|fa-solid|fa-regular/, file + ' : Font Awesome 6');
    }
  });

  it('color-mix() absent : le repli rgba() existe pour chaque thème (@supports not)', () => {
    const fallbacks = rules.filter((r) => /@supports not \(color: color-mix\(/.test(r.atRule || '') && isVariableBlock(r));
    assert.equal(fallbacks.length, 2);
  });
});
