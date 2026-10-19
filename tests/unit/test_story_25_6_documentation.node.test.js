// ARTEFACT — Story 25.6 (AC14, AC10) : `index.md` et `changelog_beta.md` décrivent la portée de la vue de travail ; chaque
// libellé cité existe verbatim dans desktop/ ; le libellé « Toutes les pièces » n'est plus celui du retour. Aucun nom réel (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const root = path.join(__dirname, '..', '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const index = read('docs/fr_FR/index.md');
const changelog = read('docs/fr_FR/changelog_beta.md');
const desktop = ['desktop/js', 'desktop/php'].flatMap((dir) => fs.readdirSync(path.join(root, dir)).filter((f) => /\.(js|php)$/.test(f)).map((f) => read(path.join(dir, f))))
  .join('\n').replace(/\{\{|\}\}/g, '');
const section = index.slice(index.indexOf('### La vue de travail'), index.indexOf('**Le détail d\'une pièce**'));

describe('25.6 / AC14 — documentation de la portée', () => {
  it('index.md décrit : pièce seule depuis une carte, « Toutes les pièces », « Page principale », ouverture en portée toutes, seule:1, « Précédent »', () => {
    assert.match(section, /\*\*La portée\.\*\*/);
    assert.match(section, /Depuis \*\*une carte de pièce\*\*, l'arbre n'affiche que \*\*cette pièce\*\*/);
    assert.match(section, /\*\*« Toutes les pièces »\*\*/);
    assert.match(section, /« Page principale »/);
    assert.match(section, /Depuis une puce, un segment de la jauge ou une ligne de la liste filtrée, la vue s'ouvre directement sur \*\*toutes les pièces\*\*/);
    assert.match(section, /`seule:1`/);
    assert.match(section, /« Précédent »/);
    assert.doesNotMatch(section, /« Toutes les pièces » \(ou le bouton « Précédent »/, 'plus le libellé du retour');
    assert.doesNotMatch(index, /fenêtre/i);
  });

  it('chaque libellé cité existe verbatim dans desktop/', () => {
    for (const label of ['Toutes les pièces', 'Page principale', 'Pièces']) {
      assert.ok(section.includes(`« ${label} »`), `« ${label} » cité dans index.md`);
      assert.ok(desktop.includes(label), `« ${label} » absent de desktop/`);
    }
  });

  it('changelog_beta.md : une entrée annonce la pièce seule, sans nom réel', () => {
    const entry = changelog.split('---').find((part) => /Vue de travail : une carte ouvre la pièce seule/.test(part));
    assert.ok(entry, 'entrée présente');
    assert.match(entry, /Vue de travail : une carte ouvre la pièce seule/);
    assert.match(entry, /« Toutes les pièces »/);
    assert.match(entry, /« Page principale »/);
    assert.match(entry, /Aucune requête de plus/);
    assert.doesNotMatch(entry, /\b(salon|cuisine|chambre|garage|Alexandre|Dupont)\b/i);
  });
});
