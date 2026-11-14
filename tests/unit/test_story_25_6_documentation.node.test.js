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
// Garde levée (front v3, Lot 5) : la section « La vue de travail » devient « La pièce et la fiche » (doc réécrite par écran).
const section = index.slice(index.indexOf('### La pièce et la fiche'), index.indexOf('**La fiche d\'un équipement**'));

// Garde levée (front v3, Lot 2) : la portée « pièce seule », la bascule « Cette pièce | Toute la maison » et « Page principale »
// sont supprimées. index.md décrit l'arbre unique, le fil d'Ariane et le sort des anciens liens `seule:1` ; chaque libellé cité
// existe dans desktop/. L'entrée historique de 25.6 reste dans changelog_beta.md, suivie de celle du front v3.
describe('25.6 / AC14 — documentation de la portée (front v3 : un seul arbre)', () => {
  it('index.md décrit : un seul arbre, la carte qui ouvre sa pièce, le fil d’Ariane « Maison », les anciens liens seule:1, « Précédent »', () => {
    assert.match(section, /\*\*Un seul arbre\.\*\*/);
    assert.match(section, /L'arbre contient toujours \*\*toute la maison\*\*/);
    assert.match(section, /`Maison › Niveau › Pièce`/);
    assert.match(section, /\*\*« Maison »\*\*/);
    assert.match(section, /`seule:1`/);
    assert.match(section, /« Précédent »/);
    assert.doesNotMatch(section, /Cette pièce \| Toute la maison|« Page principale »|Dans les autres pièces/, 'plus de bascule ni d’ancien retour');
    assert.doesNotMatch(index, /fenêtre/i);
  });

  it('chaque libellé cité existe verbatim dans desktop/', () => {
    for (const label of ['Maison', 'Rechercher', 'Aucun résultat']) {
      assert.ok(section.includes(`« ${label} »`), `« ${label} » cité dans index.md`);
      assert.ok(desktop.includes(`{{${label}}}`.replace(/\{\{|\}\}/g, '')), `« ${label} » absent de desktop/`);
    }
  });

  it('changelog_beta.md : l’entrée du front v3 annonce l’arbre unique et le fil d’Ariane, sans nom réel', () => {
    const entry = changelog.split('---').find((part) => /Vue de travail : un seul arbre/.test(part));
    assert.ok(entry, 'entrée présente');
    assert.match(entry, /« Cette pièce \| Toute la maison » disparaît/);
    assert.match(entry, /`Maison › Niveau › Pièce`/);
    assert.match(entry, /Aucune requête de plus/);
    assert.doesNotMatch(entry, /\b(salon|cuisine|chambre|garage|Alexandre|Dupont)\b/i);
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
