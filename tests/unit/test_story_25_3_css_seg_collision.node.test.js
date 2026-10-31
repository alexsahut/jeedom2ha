'use strict';
// Story 25.3 (correctif du 2026-10-19) : la classe `.j2ha-seg` désigne À LA FOIS le contrôle segmenté
// « Automatique | Toujours | Jamais » de 25.1 et les segments de jauge de la page B. Une règle de jauge
// non portée par `.j2ha-gauge` (flex-basis: 0) réduisait le contrôle segmenté à 2 px dans la fenêtre de
// pièce (gate 20-0 sur la box : clic « Exclure » impossible). Ce test interdit son retour.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const css = fs.readFileSync(path.join(__dirname, '..', '..', 'desktop', 'css', 'jeedom2ha.css'), 'utf8')
  .replace(/\/\*[\s\S]*?\*\//g, '');

function rules() {
  const out = [];
  const re = /([^{}]+)\{([^{}]*)\}/g;
  let m;
  while ((m = re.exec(css)) !== null) out.push({ selector: m[1].trim(), body: m[2] });
  return out;
}

test('25.3 — aucune règle de dimension de jauge ne vise le .j2ha-seg nu du contrôle segmenté', () => {
  const offending = rules().filter((r) => r.selector.split(',').some((sel) => {
    const s = sel.trim();
    return /(^|\s)\.j2ha-seg(?![-\w])/.test(s) && !/\.j2ha-gauge/.test(s) && /flex-basis|min-width|flex-grow/.test(r.body);
  }));
  assert.deepStrictEqual(offending.map((r) => r.selector), []);
});

test('25.3 — les segments de jauge sont portés par .j2ha-gauge', () => {
  const gauge = rules().filter((r) => /\.j2ha-gauge\s+\.j2ha-seg/.test(r.selector) && /flex-basis/.test(r.body));
  assert.ok(gauge.length >= 1, 'règle .j2ha-gauge .j2ha-seg avec flex-basis attendue');
});
