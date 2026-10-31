// ARTEFACT — Story 25.3 (AC14) : `index.md`, `compteurs.md` et `changelog_beta.md` décrivent la page principale B
// (successeur de test_story_25_1_documentation pour ce périmètre). Aucun nom réel (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const read = (file) => fs.readFileSync(path.join('docs/fr_FR', file), 'utf8');
const index = read('index.md');
const compteurs = read('compteurs.md');
const changelogBeta = read('changelog_beta.md');

const word = (w) => new RegExp('(?<![\\p{L}\\p{N}_])' + w + '(?![\\p{L}\\p{N}_])', 'iu');
const FORBIDDEN = ['override', 'bridge', 'prête', 'prêtes', 'prêt', 'prêts', 'bloquante', 'bloquantes', 'rescanner', 'Override HA', 'mode automatique'];

describe('25.3 / AC14 — vocabulaire', () => {
  for (const [name, text] of [['index.md', index], ['compteurs.md', compteurs]]) {
    it(`${name} : aucun terme interdit par 25.1 AC23`, () => {
      for (const forbidden of FORBIDDEN) assert.doesNotMatch(text, word(forbidden.replace(' ', '\\s')), `${name} : « ${forbidden} »`);
      assert.doesNotMatch(text, /Sera publié/);
    });
  }
});

describe('25.3 / AC14 — index.md décrit la nouvelle page principale', () => {
  it('barre de santé, actions, menu « ⋯ », bloc maison et filtres, cartes, « Actualiser », « non lu », regroupement par parent', () => {
    for (const heading of ['### La barre de santé', '### Les actions de la barre de santé', '### Le bloc de la maison', '### Les cartes de pièce']) {
      assert.ok(index.includes(heading), heading);
    }
    assert.match(index, /menu « ⋯ »/);
    assert.match(index, /Chaque puce \(et chaque segment de la jauge\) est un filtre/);
    assert.match(index, /« Actualiser »/);
    assert.match(index, /« non lu »/);
    assert.match(index, /regroupées par objet parent/);
    assert.match(index, /au retour sur l'onglet|quand vous revenez sur l'onglet/);
  });

  it('ne mentionne plus le bandeau de santé ni la zone « Actions Home Assistant » ; le bandeau bleu a disparu', () => {
    assert.doesNotMatch(index, /bandeau de santé/);
    assert.doesNotMatch(index, /zone « Actions Home Assistant »/);
    assert.doesNotMatch(index, /\*\*« Republier dans Home Assistant »\*\*/);
    assert.match(index, /Aucun bandeau bleu n'ouvre plus la page/);
    assert.match(index, /partagé avec Homebridge/, 'la note Homebridge est conservée, dans le texte');
  });

  it('les emplacements de capture sont conservés, sans image', () => {
    for (const slot of ['page principale du plugin', 'cartes de pièce']) assert.ok(index.includes(`<!-- CAPTURE-A-PRENDRE: ${slot} -->`), slot);
    assert.doesNotMatch(index + compteurs, /!\[[^\]]*\]\([^)]*\.(png|jpg|gif)\)/);
  });
});

describe('25.3 / AC14 — compteurs.md, bloc isolé', () => {
  it('décrit la jauge de la maison, les repères des cartes, « non lu » et ce qui n’est pas un état', () => {
    assert.match(compteurs, /^## La jauge de la maison$/m);
    assert.match(compteurs, /^## Les repères d'une carte de pièce$/m);
    assert.match(compteurs, /\*\*Non lu\*\* n'est pas un septième état|\*\*Non lu\*\* n'est pas un/);
    assert.match(compteurs, /Ce qui n'est pas un état/);
    assert.match(compteurs, /COMPTEURS:DEBUT/);
    assert.match(compteurs, /<!-- COMPTEURS:FIN -->\s*$/);
    const before = compteurs.slice(0, compteurs.indexOf('COMPTEURS:DEBUT'));
    assert.equal(before.replace(/<!--\s*$/, '').trim(), '', 'rien avant le bloc isolé');
  });
});

describe('25.3 / AC14 — changelog_beta.md', () => {
  it('reçoit une entrée sur la page principale', () => {
    assert.match(changelogBeta, /^# 2026-10-19 — Page principale/m);
    assert.ok(changelogBeta.indexOf('# 2026-10-19 — Page principale') < changelogBeta.indexOf('# 2026-10-18 — Un seul état'));
  });
});

describe('25.3 / AC14 — libellés cités = libellés du code', () => {
  const code = ['desktop/js', 'desktop/php', 'core'].flatMap((dir) => fs.readdirSync(dir, { recursive: true })
    .filter((f) => /\.(php|js)$/.test(f)).map((f) => path.join(dir, f)))
    .map((file) => fs.readFileSync(file, 'utf8').replace(/\{\{|\}\}/g, '').replace(/\\'/g, "'"))
    .join('\n');

  it('chaque libellé de la page B cité dans la documentation existe tel quel dans desktop/ ou core/', () => {
    const labels = ['Republier tout', 'Relire Jeedom', 'Télécharger le diagnostic…', 'Supprimer tout de Home Assistant…', 'Actualiser',
      'Tout afficher', 'Aide', 'Plus d\'actions', 'Télécharger le diagnostic support', 'Pseudonymiser les noms d\'équipements',
      'Aucune synchronisation n\'a encore eu lieu', 'Opération en cours : ces chiffres peuvent changer', 'Chiffres indisponibles',
      'Aucune pièce avec équipement trouvée.'];
    const text = index + compteurs + changelogBeta;
    let cited = 0;
    for (const label of labels) {
      if (text.includes(`« ${label} »`) || text.includes(`**« ${label} »**`) || text.includes(`**${label}**`) || text.includes(`« ${label}`)) {
        cited += 1;
        assert.ok(code.includes(label), `« ${label} » cité mais absent du code`);
      }
    }
    assert.ok(cited >= 11, 'les libellés de la page B sont bien cités (' + cited + ')');
  });
});
