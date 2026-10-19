// ARTEFACT — Story 25.7 (AC10, AC7) : `index.md`, `compteurs.md` et `changelog_beta.md` décrivent la cause d'exclusion ; chaque
// libellé cité existe verbatim dans desktop/. Aucun nom réel de plugin ni d'équipement (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const root = path.join(__dirname, '..', '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const index = read('docs/fr_FR/index.md');
const compteurs = read('docs/fr_FR/compteurs.md');
const changelog = read('docs/fr_FR/changelog_beta.md');
const desktop = ['desktop/js', 'desktop/php'].flatMap((dir) => fs.readdirSync(path.join(root, dir)).filter((f) => /\.(js|php)$/.test(f)).map((f) => read(path.join(dir, f))))
  .join('\n').replace(/\{\{|\}\}/g, '').replace(/\\'/g, "'");

describe('25.7 / AC10 — documentation de la cause d\'exclusion', () => {
  it('index.md : les trois mentions, où agir, badges, détail d\'équipement, détail de pièce, carte, famille « Exclusions volontaires »', () => {
    for (const needle of ['« par le plugin X »', '« par la pièce »', '« individuelle »', 'Exclusions volontaires', '« Exclus : »', '« N exclus »',
      '**La cause d\'exclusion**', 'Ouvrir la configuration du plugin', '« Plugins exclus »', '« Pièces exclues »', '« par son plugin »', '« autre »']) {
      assert.ok(index.includes(needle), needle);
    }
    assert.match(index, /Ce n'est pas un état de plus/);
    assert.match(index, /jamais pour un équipement « Désactivé »/);
    assert.doesNotMatch(index, /fenêtre/i);
  });

  it('compteurs.md : la cause n\'ajoute pas d\'état et la somme de la ventilation peut être inférieure au compte « exclu »', () => {
    assert.match(compteurs, /La cause d'exclusion n'est pas un état de plus/);
    assert.match(compteurs, /sa somme peut être inférieure au compte « exclu »/);
    assert.match(compteurs, /« Désactivé » n'a jamais de cause d'exclusion/);
  });

  it('chaque libellé cité entre « » dans la documentation existe verbatim dans desktop/', () => {
    for (const label of ['Exclus', 'Plugins exclus', 'Ouvrir la configuration du plugin', 'par le plugin', 'par la pièce', 'individuelle', 'par son plugin', 'autre',
      'Exclu par la pièce : toute la pièce est exclue', 'Exclusion individuelle : réglage « Jamais »', 'Exclusion individuelle : « Jamais » sur ses entités',
      "Exclusion individuelle : réglage de l'équipement dans Jeedom"]) {
      assert.ok(desktop.includes(label), `« ${label} » absent de desktop/`);
    }
    for (const cited of ['Exclu par la pièce : toute la pièce est exclue', 'Exclusion individuelle : réglage « Jamais »', 'Exclusion individuelle : « Jamais » sur ses entités',
      "Exclusion individuelle : réglage de l'équipement dans Jeedom"]) {
      assert.ok(index.includes(cited), `« ${cited} » cité dans index.md`);
    }
  });

  it('changelog_beta.md : l\'entrée de la cause d\'exclusion existe ; aucun nom réel', () => {
    // Stories postérieures (25.8, 25.9) : l'entrée est cherchée par son titre, plus par sa position en tête du fichier.
    const entry = changelog.split('---').find((part) => part.includes("Cause d'exclusion affichée"));
    assert.match(entry, /Cause d'exclusion affichée/);
    assert.match(entry, /« par le plugin X »/);
    assert.match(entry, /Aucune modification du démon/);
    assert.match(entry, /Aucune requête de plus/);
    assert.doesNotMatch(entry, /\b(salon|cuisine|chambre|garage|Alexandre|Dupont)\b/i);
  });
});
