// ARTEFACT — Story 25.4 (AC26, AC30) : `index.md`, `compteurs.md` et `changelog_beta.md` décrivent la vue de travail
// (successeur de test_story_25_3_documentation). Plus de fenêtre ni de modale dans la documentation utilisateur (hors
// historique du changelog), libellés cités = libellés du code, emplacements de capture conservés, bloc des compteurs
// isolé. Aucun nom réel (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const W = require('../../desktop/js/jeedom2ha_workview.js');

const root = path.join(__dirname, '..', '..');
const read = (file) => fs.readFileSync(path.join(root, 'docs/fr_FR', file), 'utf8');
const index = read('index.md');
const compteurs = read('compteurs.md');
const changelogBeta = read('changelog_beta.md');

const word = (w) => new RegExp('(?<![\\p{L}\\p{N}_])' + w + '(?![\\p{L}\\p{N}_])', 'iu');
const FORBIDDEN = ['override', 'bridge', 'prête', 'prêtes', 'prêt', 'prêts', 'bloquante', 'bloquantes', 'rescanner', 'Override HA'];

describe('25.4 / AC30 — vocabulaire', () => {
  for (const [name, text] of [['index.md', index], ['compteurs.md', compteurs]]) {
    it(`${name} : aucun terme interdit, plus de « modale » ni de fenêtre de pièce`, () => {
      for (const forbidden of FORBIDDEN) assert.doesNotMatch(text, word(forbidden.replace(' ', '\\s')), `${name} : « ${forbidden} »`);
      assert.doesNotMatch(text, /Sera publié/);
      assert.doesNotMatch(text, /modale/i);
      assert.doesNotMatch(text, /fenêtre (de|d'une|de la|d’une) pièce|fenêtre de la pièce/i);
      assert.doesNotMatch(text, /fenêtre/i, name + ' : plus aucune fenêtre (les confirmations sont des « confirmations »)');
    });
  }
});

describe('25.4 / AC30 — index.md décrit la vue de travail', () => {
  it('section dédiée : ouverture, retour, adresse, arbre, recherche, filtres, détail de pièce, détail d’équipement, tablette', () => {
    assert.ok(index.includes('\n### La vue de travail\n'));
    for (const needle of ['**La vue de travail**'.replace(/\*\*/g, '**'), '« Toutes les pièces »', '« Précédent »', '#j2ha-vue=', 'Rechercher une pièce ou un équipement', 'Aucun résultat',
      'À traiter dans cette pièce', 'Rien à traiter dans cette pièce', 'Republier la pièce', 'Ouvrir les types génériques', '« Pièces »', 'Échap']) {
      assert.ok(index.includes(needle.replace('**La vue de travail**', 'vue de travail')), needle);
    }
    assert.match(index, /carte de pièce, sur une puce ou un segment de la jauge/);
    assert.match(index, /La lecture de la configuration|ne lit la configuration \*\*que de cet équipement\*\*/);
    assert.match(index, /partagé\*\* avec la page principale/);
    assert.match(index, new RegExp(`en dessous de ${W.LAYOUT_SPLIT_MIN_WIDTH} pixels`));
  });

  it('la liste filtrée et les cartes décrivent l’ouverture de la vue', () => {
    assert.match(index, /ouvre la \[vue de travail\]\(#la-vue-de-travail\)/);
    assert.match(index, /ouvre la vue de travail sur la pièce/);
  });

  it('le détail d’équipement est décrit sous son nouveau titre ; les anciennes sections sont conservées', () => {
    for (const heading of ['### Le détail d\'un équipement', '### Le tableau des commandes', '### Les causes de blocage', '### Réglages en attente et Appliquer', '### Les actions de publication']) {
      assert.ok(index.includes('\n' + heading + '\n'), heading);
    }
  });

  it('les emplacements de capture sont conservés, sans image', () => {
    for (const slot of ['page principale du plugin', 'cartes de pièce', 'vue de travail', 'détail d\'un équipement', 'tableau des commandes']) {
      assert.ok(index.includes(`<!-- CAPTURE-A-PRENDRE: ${slot} -->`), slot);
    }
    assert.ok(compteurs.includes('<!-- CAPTURE-A-PRENDRE: compteurs du détail de pièce -->'));
    assert.doesNotMatch(index + compteurs, /!\[[^\]]*\]\([^)]*\.(png|jpg|gif)\)/);
  });

  it('les liens internes pointent vers des titres existants', () => {
    const slug = (title) => title.toLowerCase().replace(/[^\p{L}\p{N}\s-]/gu, '').replace(/\s/g, '-');
    const headings = (text) => text.split('\n').filter((l) => /^#{1,6} /.test(l)).map((l) => slug(l.replace(/^#+ /, '')));
    const anchors = { 'index.md': headings(index), 'compteurs.md': headings(compteurs) };
    for (const [file, text] of [['index.md', index], ['compteurs.md', compteurs]]) {
      for (const m of text.matchAll(/\]\((index\.md|compteurs\.md)?#([^)]+)\)/g)) {
        assert.ok(anchors[m[1] || file].includes(m[2]), `${file} → ${m[1] || file}#${m[2]}`);
      }
    }
  });
});

describe('25.4 / AC30 — libellés cités = libellés du code', () => {
  const code = ['desktop/js', 'desktop/php', 'core'].flatMap((entry) => fs.readdirSync(path.join(root, entry), { recursive: true })
    .filter((f) => /\.(php|js)$/.test(f)).map((f) => path.join(root, entry, f)))
    .map((file) => fs.readFileSync(file, 'utf8').replace(/\{\{|\}\}/g, '').replace(/\\'/g, "'")).join('\n');

  it('chaque libellé de la vue cité entre « » dans index.md existe tel quel dans desktop/ ou core/', () => {
    for (const label of ['Toutes les pièces', 'Rechercher une pièce ou un équipement', 'À traiter dans cette pièce', 'Rien à traiter dans cette pièce',
      'Pièces', 'Aucun résultat', 'Republier la pièce', 'Supprimer de Home Assistant…', 'Ouvrir les types génériques', 'Appliquer',
      '(désactivé dans Jeedom)', 'non lu', 'Chargement…', 'Impossible de lire la configuration de cet équipement.',
      'Impossible de charger la configuration HA (démon indisponible).',
      'Republication et suppression de pièce indisponibles pour les équipements sans pièce : utilisez les actions de chaque équipement.']) {
      assert.ok(index.includes(label), `« ${label} » cité dans index.md`);
      assert.ok(code.includes(label), `« ${label} » absent du code`);
    }
  });

  it('compteurs.md cite les mentions de lecture de la page principale telles que le code les rend', () => {
    for (const label of ["Aucune synchronisation n'a encore eu lieu", 'Mise à jour en cours…', 'Chiffres indisponibles']) {
      assert.ok(compteurs.includes(label), label);
      assert.ok(code.includes(label), label + ' (code)');
    }
  });
});

describe('25.4 / AC30 — compteurs.md : bloc isolé, mêmes définitions que la page principale', () => {
  it('bloc COMPTEURS:DEBUT/FIN conservé ; les repères d’arbre et les KPI de pièce se rattachent aux définitions de la page principale', () => {
    assert.match(compteurs, /COMPTEURS:DEBUT/);
    assert.match(compteurs, /<!-- COMPTEURS:FIN -->\s*$/);
    assert.match(compteurs, /^## La ligne des états \(sous le titre de la pièce\)$/m);
    assert.match(compteurs, /^## La liste « À traiter dans cette pièce »$/m);
    assert.match(compteurs, /repères d'une pièce\) et des compteurs du détail de pièce/);
    assert.match(compteurs, /calculés à partir de la même lecture, sans rien relire/);
  });

  it('cloisonnement : aucun libellé de compteur hors de compteurs.md (index.md et changelog)', () => {
    const counters = /\d (publiés?|publiées?|à appliquer|exclus?|exclues?|désactivés?|rien à publier|ignorées?)\b|Chargement des compteurs|Compteurs indisponibles|équipements? non lus?/;
    assert.doesNotMatch(index, counters);
    assert.doesNotMatch(changelogBeta, counters);
  });
});

describe('25.4 / AC30 — changelog_beta.md', () => {
  it('une entrée annonce la vue de travail ; aucun nom réel (CC-48)', () => {
    assert.match(changelogBeta, /# 2026-10-19 — Vue de travail : l'arbre des pièces et le détail, sans fenêtre/);
    // Stories postérieures (25.8, 25.9) : l'entrée est cherchée par son titre, plus par sa position en tête du fichier.
    const entry = changelogBeta.split('\n---\n').find((part) => part.includes("Vue de travail : l'arbre des pièces et le détail, sans fenêtre"));
    assert.match(entry, /vue de travail/);
    assert.match(entry, /Aucune modification du démon/);
    assert.doesNotMatch(entry, /\b(salon|cuisine|chambre|garage|Alexandre|Dupont)\b/i);
  });
});
