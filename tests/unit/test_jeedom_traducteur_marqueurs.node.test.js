'use strict';
// Le cœur Jeedom traduit les fichiers JS du plugin à la volée : chaque `{{…}}` (expression non gourmande, multiligne,
// comme `translate::exec`) est remplacé par sa traduction, ou par son contenu sans accolades. Un `{{` hors libellé (JSDoc
// `@returns {{…}}`, objet littéral) s'apparie alors avec le `}}` d'un libellé plus bas et en retire les accolades : la
// box a affiché « {{par le plugin Deconz » (gate 25.6, 2026-10-19). Les tests servent les JS bruts et ne le voyaient pas.
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const DIR = path.join(__dirname, '..', '..', 'desktop', 'js');
const files = fs.readdirSync(DIR).filter((f) => f.endsWith('.js'));

// Équivalent de la traduction du cœur sans dictionnaire : `{{X}}` → `X`.
function translate(src) { return src.replace(/\{\{([\s\S]*?)\}\}/g, '$1'); }

describe('marqueurs de traduction Jeedom dans desktop/js', () => {
  for (const file of files) {
    it(`${file} : aucun marqueur {{…}} ne traverse une fin de ligne`, () => {
      const src = fs.readFileSync(path.join(DIR, file), 'utf8');
      const crossing = [];
      for (const m of src.matchAll(/\{\{([\s\S]*?)\}\}/g)) {
        if (m[1].includes('\n')) crossing.push(src.slice(0, m.index).split('\n').length);
      }
      assert.deepEqual(crossing, [], `marqueur ouvert ligne(s) ${crossing.join(', ')}`);
    });
  }

  it('après traduction, la mention courte de cause par plugin ne garde aucune accolade', () => {
    const src = translate(fs.readFileSync(path.join(DIR, 'jeedom2ha_mapping_override.js'), 'utf8'));
    const sandbox = { module: { exports: {} }, window: {} };
    sandbox.exports = sandbox.module.exports;
    new Function('module', 'exports', 'window', src)(sandbox.module, sandbox.exports, sandbox.window);
    const M = Object.keys(sandbox.module.exports).length ? sandbox.module.exports : (sandbox.window.jeedom2haMappingOverride || sandbox.window.J2haMapping || {});
    assert.equal(typeof M.exclusionCauseText, 'function', 'exclusionCauseText exportée');
    assert.equal(M.exclusionCauseText({ kind: 'plugin', code: 'excluded_plugin' }, 'Alpha', 'short'), 'par le plugin Alpha');
    assert.equal(M.exclusionCauseText({ kind: 'plugin', code: 'excluded_plugin' }, '', 'short'), 'par son plugin');
  });
});
