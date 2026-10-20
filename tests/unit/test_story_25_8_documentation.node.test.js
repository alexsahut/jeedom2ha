// ARTEFACT — Story 25.8 (AC18) : `index.md`, `compteurs.md` et `changelog_beta.md` décrivent l'exclusion de pièce depuis la surface ;
// chaque libellé cité existe verbatim dans desktop/ ou plugin_info/. Aucun nom réel de pièce, d'équipement ou de personne (CC-48).
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
const code = ['desktop/js', 'desktop/php'].flatMap((dir) => fs.readdirSync(path.join(root, dir)).filter((f) => /\.(js|php)$/.test(f)).map((f) => read(path.join(dir, f))))
  .join('\n').replace(/\{\{|\}\}/g, '').replace(/\\'/g, "'");
const section = index.slice(index.indexOf('### Exclure une pièce'), index.indexOf('### Télécharger le diagnostic support'));

describe('25.8 / AC18 — documentation de l\'exclusion de pièce', () => {
  it('index.md : la section « Exclure une pièce » existe, dans la table des matières par ancre, avec toutes les règles décidées', () => {
    assert.ok(section.length > 500, 'section présente');
    for (const needle of ['menu « ⋯ »', '« Exclure la pièce… »', '« Ne plus exclure la pièce… »', 'Ouvrir ce menu n\'ouvre pas la pièce', 'Sans pièce',
      'La confirmation est chiffrée', 'L\'effet est immédiat', 'relecture complète de Jeedom', 'sans seconde confirmation',
      'applique', 'réglages en attente', 'Pièce exclue', 'N pas encore retirés', 'La pièce prime sur « Toujours »', 'Pas de cascade', 'sous-pièces',
      'Relancez « Relire Jeedom » pour retirer les entités.', 'Exclure une pièce déjà exclue ne change rien mais relance quand même la relecture']) {
      assert.ok(section.includes(needle) || index.includes(needle), needle);
    }
    assert.match(index, /\(#exclure-une-pièce\)/);
  });

  it('index.md : les cartes et le détail de pièce mentionnent le menu, l\'encart et la mention « Pièce exclue »', () => {
    assert.match(index, /Chaque carte \(sauf « Sans pièce »\) a un menu « ⋯ »/);
    assert.match(index, /« Pièce exclue : ses équipements ne sont pas publiés dans Home Assistant\. »/);
    assert.match(index, /« Supprimer de Home Assistant… »\*\*, en rouge, dans le menu seulement/);
  });

  it('index.md : § Filtrage et publication indique que le champ de la configuration est retiré ; famille 7 mise à jour', () => {
    const filtering = index.slice(index.indexOf('### Filtrage et publication'), index.indexOf('## Première synchronisation'));
    assert.doesNotMatch(filtering, /\| \*\*Pièces exclues\*\* \|/);
    assert.match(filtering, /Il n'y a plus de champ de saisie des pièces/);
    assert.match(index, /exclu de Jeedom2HA \(pièce dans la liste d’exclusions\) \| Exclusion de la pièce, posée depuis sa carte ou son détail/);
    assert.match(index, /« par la pièce » correspond à l'exclusion de la pièce/);
  });

  it('compteurs.md : une pièce exclue n\'est pas un état de plus', () => {
    assert.match(compteurs, /Une pièce exclue n'est pas un état de plus/);
    assert.match(compteurs, /« Désactivé » dans une pièce exclue/);
  });

  it('chaque libellé cité entre « » existe verbatim dans desktop/', () => {
    for (const label of ['Exclure la pièce…', 'Ne plus exclure la pièce…', 'Pièce exclue', 'Exclure la pièce', 'Ne plus exclure',
      'Pièce exclue : ses équipements ne sont pas publiés dans Home Assistant.', 'Pièce exclue : elle prime sur ce réglage.',
      "Nombre d'entités inconnu : la lecture des états n'est pas disponible.", "Aucune entité n'est publiée dans cette pièce.",
      "Ses équipements seront relus et publiés s'ils sont publiables.", 'Relancez « Relire Jeedom » pour retirer les entités.',
      'Une opération est déjà en cours.', 'pas encore retirés', 'La relecture appliquera aussi', 'réglages en attente',
      'entités seront retirées', 'entité sera retirée', 'Toutes les pièces']) {
      const present = code.includes(label) || read('desktop/js/jeedom2ha.js').replace(/\{\{|\}\}/g, '').replace(/\\'/g, "'").includes(label);
      assert.ok(present, `« ${label} » absent de desktop/`);
    }
    for (const cited of ["Nombre d'entités inconnu : la lecture des états n'est pas disponible.", "Aucune entité n'est publiée dans cette pièce.",
      "Ses équipements seront relus et publiés s'ils sont publiables.", 'Pièce exclue : elle prime sur ce réglage.', 'Relancez « Relire Jeedom » pour retirer les entités.']) {
      assert.ok(index.includes(cited), `« ${cited} » cité dans index.md`);
    }
  });

  it('changelog_beta.md : l\'entrée de la story existe, sans nom réel, et annonce l\'unique ajout de champ du démon', () => {
    const entry = changelog.split('\n---\n').find((part) => part.includes('Exclure une pièce depuis la surface'));
    assert.ok(entry, 'entrée présente');
    assert.match(entry, /présent|present_in_ha/);
    assert.match(entry, /Aucune autre modification du démon/);
    assert.match(entry, /liste à cocher/);
    assert.doesNotMatch(entry, /\b(salon|cuisine|chambre|garage|Alexandre|Dupont)\b/i);
  });
});
