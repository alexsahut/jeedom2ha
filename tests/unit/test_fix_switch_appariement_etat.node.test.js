// ARTEFACT — fix/switch-appariement-etat : la cause « plusieurs ordres On/Off » a un libellé, une catégorie
// (Bloquée), une fiche du lexique et un libellé court, et passe avant « type ambigu » dans le diagnostic.
// Identifiants fictifs (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const L = require('../../desktop/js/jeedom2ha_lexique.js');

const CODE = 'switch_pairing_ambiguous';
const LABEL = 'plusieurs ordres On/Off — reliez à l’état, dans Jeedom, ceux qui pilotent l’appareil';

function ambiguousView() {
  return {
    publication_reason: 'ambiguous_skipped', reason_code: CODE, is_valid: false,
    validity_reason_code: 'ha_missing_command_topic', missing_fields: ['command_topic'], missing_capabilities: ['has_command'],
  };
}

describe('fix/switch-appariement-etat — cause « plusieurs ordres On/Off »', () => {
  it('libellé et catégorie Bloquée', () => {
    assert.equal(M.REASON_LABELS[CODE], LABEL);
    assert.equal(M.categoryOfCause(CODE), 'blocked');
  });

  it('la cause précise passe avant « type ambigu » et avant le symptôme', () => {
    assert.equal(M.buildBlockingReason(ambiguousView()), LABEL);
  });

  it('fiche du lexique : quoi, pourquoi, action « équipement »', () => {
    const sheet = L.causeSheet(CODE);
    assert.match(sheet.quoi, /plusieurs ordres On et Off/);
    assert.deepEqual(sheet.actions.map((a) => a.key), ['equipment']);
    assert.match(sheet.aide, /« Commande information à mettre à jour »/);
    assert.match(sheet.aide, /commande d’état liée/);
    assert.match(sheet.aide, /Ne changez ni la valeur/);
    assert.doesNotMatch(sheet.aide, /champ « Valeur »/);
    assert.doesNotMatch(sheet.aide, /type générique[^s]/);
  });

  it('libellés courts de la bande et de la liste « À faire » (quatre mots au plus)', () => {
    const root = path.resolve(__dirname, '../..');
    const surface = fs.readFileSync(path.join(root, 'desktop/js/jeedom2ha_mapping_surface.js'), 'utf8');
    const overview = fs.readFileSync(path.join(root, 'desktop/js/jeedom2ha_overview.js'), 'utf8');
    assert.ok(surface.includes("switch_pairing_ambiguous: '{{Ordres On/Off en double}}'"));
    assert.ok(overview.includes("switch_pairing_ambiguous: '{{Ordres On / Off en double}}'"));
  });

  it('libellé, fiche, cause du démon, doc et changelog disent le même remède (champs réels de Jeedom)', () => {
    const root = path.resolve(__dirname, '../..');
    const read = (f) => fs.readFileSync(path.join(root, f), 'utf8').replace(/[’]/g, "'");
    const texts = {
      lexique: L.causeSheet(CODE).aide.replace(/[’]/g, "'"),
      cause: read('resources/daemon/models/cause_mapping.py').replace(/"\s*\n\s*"/g, ''),
      doc: read('docs/fr_FR/index.md'),
    };
    for (const [name, text] of Object.entries(texts)) {
      assert.match(text, /« Commande information à mettre à jour »/, name);
      assert.match(text, /commande d'état liée de l'action/, name);
    }
    const changelog = read('docs/fr_FR/changelog_beta.md');
    assert.ok(changelog.includes(LABEL.replace(/[’]/g, "'")) || fs.readFileSync(path.join(root, 'docs/fr_FR/changelog_beta.md'), 'utf8').includes(LABEL));
    assert.match(changelog, /« Commande information à mettre à jour »/);
    assert.doesNotMatch(changelog, /configuration avancée du cœur/);
    assert.doesNotMatch(texts.doc.split('\n').find((l) => l.includes(LABEL.replace(/[’]/g, "'"))) || '', /champ « Valeur » de chaque action/);
  });

  it('la documentation reprend le libellé mot pour mot', () => {
    const doc = fs.readFileSync(path.resolve(__dirname, '../../docs/fr_FR/index.md'), 'utf8');
    assert.ok(doc.includes('| ' + LABEL + ' |'));
    assert.ok(doc.includes('« Ordres On/Off en double »'));
  });
});
