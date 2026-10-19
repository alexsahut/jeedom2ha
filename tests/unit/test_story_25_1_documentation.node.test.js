// ARTEFACT — Story 25.1 (AC23) : `index.md` et `compteurs.md` réalignés sur le glossaire et sur la
// fenêtre d'une pièce réorganisée (successeur de test_story_22_2_documentation). Aucun nom réel (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

const read = (file) => fs.readFileSync(path.join('docs/fr_FR', file), 'utf8');
const index = read('index.md');
const compteurs = read('compteurs.md');
const changelogBeta = read('changelog_beta.md');

// Mots interdits (AC23), en mot entier et insensible à la casse, hors identifiants de code (`override_pending`,
// noms de fichiers) et hors historique des versions (`changelog*.md`, non analysé ici). « Homebridge » n'est
// pas concerné (mot entier). « mode automatique » désigne l'ancien réglage de publication.
const word = (w) => new RegExp('(?<![\\p{L}\\p{N}_])' + w + '(?![\\p{L}\\p{N}_])', 'iu');
const FORBIDDEN = ['override', 'bridge', 'prête', 'prêtes', 'prêt', 'prêts', 'bloquante', 'bloquantes', 'rescanner', 'Override HA', 'mode automatique'];

describe('25.1 / AC23 — vocabulaire des deux pages', () => {
  for (const [name, text] of [['index.md', index], ['compteurs.md', compteurs]]) {
    it(`${name} : aucun terme de l’ancien vocabulaire`, () => {
      for (const forbidden of FORBIDDEN) {
        assert.doesNotMatch(text, word(forbidden.replace(' ', '\\s')), `${name} contient « ${forbidden} »`);
      }
      assert.doesNotMatch(text, /Rescan\b|rescan\b/i);
    });
  }

  it('le glossaire de la présentation dit « Réglage » (plus « Override ») et définit les états et le démon', () => {
    assert.match(index, /\| \*\*Réglage\*\* \|/);
    assert.match(index, /\| \*\*État\*\* \|/);
    assert.match(index, /\| \*\*Démon\*\* \|/);
  });

  it('les emplacements de capture sont conservés (pas de captures, décision 20-5 Q3)', () => {
    assert.match(compteurs, /<!-- CAPTURE-A-PRENDRE: compteurs du détail de pièce -->/);
    assert.match(compteurs, /<!-- CAPTURE-A-PRENDRE: ligne de compteurs d'un équipement déplié -->/);
    for (const slot of ['page principale du plugin', 'cartes de pièce', 'vue de travail', 'tableau des commandes']) {
      assert.ok(index.includes(`<!-- CAPTURE-A-PRENDRE: ${slot} -->`), slot);
    }
    assert.doesNotMatch(index + compteurs, /!\[[^\]]*\]\([^)]*\.(png|jpg|gif)\)/);
  });

  it('les liens internes de index.md et de compteurs.md pointent vers des titres existants', () => {
    const slug = (title) => title.toLowerCase().replace(/[^\p{L}\p{N}\s-]/gu, '').replace(/\s/g, '-');
    const headings = (text) => text.split('\n').filter((l) => /^#{1,6} /.test(l)).map((l) => slug(l.replace(/^#+ /, '')));
    const anchors = { 'index.md': headings(index), 'compteurs.md': headings(compteurs) };
    for (const [file, text] of [['index.md', index], ['compteurs.md', compteurs]]) {
      for (const m of text.matchAll(/\]\((index\.md|compteurs\.md)?#([^)]+)\)/g)) {
        const target = m[1] || file;
        assert.ok(anchors[target].includes(m[2]), `${file} → ${target}#${m[2]}`);
      }
    }
  });
});

describe('25.1 / AC23 — libellés cités = libellés du code', () => {
  const code = ['desktop/js/jeedom2ha.js', 'desktop/js/jeedom2ha_mapping_surface.js', 'desktop/js/jeedom2ha_mapping_override.js', 'desktop/php/jeedom2ha.php', 'core']
    .flatMap((entry) => (fs.statSync(entry).isDirectory()
      ? fs.readdirSync(entry, { recursive: true }).filter((f) => /\.(php|js)$/.test(f)).map((f) => path.join(entry, f))
      : [entry]))
    .map((file) => fs.readFileSync(file, 'utf8').replace(/\{\{|\}\}/g, ''))
    .join('\n');

  const LABELS = ['Publié', 'À appliquer', 'Bloqué', 'Exclu', 'Désactivé', 'Rien à publier', 'Publiée', 'Bloquée', 'Exclue',
    'Automatique', 'Toujours', 'Jamais', 'Appliquer', 'Republier', 'Supprimer de Home Assistant…', 'Relire Jeedom', 'Démon',
    'Ouvrir les types génériques', 'Voir la première commande bloquée', 'Retirer le type imposé', 'Type HA', 'Dans Home Assistant',
    'Type Jeedom', 'Publication dans Home Assistant', 'Relire', 'Tout remettre en automatique…'];

  it('chaque libellé du glossaire cité entre « » dans la documentation existe tel quel dans desktop/ ou core/', () => {
    const text = index + compteurs;
    let cited = 0;
    for (const label of LABELS) {
      if (text.includes(`« ${label} »`) || text.includes(`**« ${label} »**`) || text.includes(`**${label}**`)) {
        cited += 1;
        assert.ok(code.includes(label), `« ${label} » cité mais absent du code`);
      }
    }
    assert.ok(cited >= 15, 'la documentation cite bien les libellés du glossaire (' + cited + ')');
  });

  it('les mots des six états cités dans compteurs.md sont ceux de l’interface', () => {
    for (const label of Object.values(M.EQUIPMENT_STATE_LABELS)) {
      assert.ok(compteurs.includes(`**${label}**`), label);
      assert.ok(index.includes(`**${label}**`), label + ' (badges)');
    }
  });
});

describe('25.1 / AC23 — compteurs.md', () => {
  it('bloc isolé conservé', () => {
    assert.match(compteurs, /COMPTEURS:DEBUT/);
    assert.match(compteurs, /<!-- COMPTEURS:FIN -->\s*$/);
  });

  it('décrit les six états et leurs priorités R1 à R8, dont « Désactivé » prime sur « Exclu »', () => {
    for (const rule of ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8']) assert.match(compteurs, new RegExp('\\| ' + rule + ' \\|'));
    assert.match(compteurs, /« Désactivé » l'emporte sur « Exclu »/);
    assert.match(compteurs, /jamais « Publié »/);
    assert.match(compteurs, /pas d'état « partiel »/);
    // L'ordre des lignes du tableau est celui des règles : R3 (Désactivé) avant R4 (Exclu).
    assert.ok(compteurs.indexOf('| R3 |') < compteurs.indexOf('| R4 |'));
  });

  it('décrit les quatre catégories de commande, « Ignorée » non comptée comme défaut', () => {
    for (const category of ['Publiée', 'Bloquée', 'Ignorée', 'Exclue']) assert.ok(compteurs.includes(`**${category}**`), category);
    assert.match(compteurs, /jamais comptées comme un défaut/);
    assert.match(compteurs, /\| \*\*Ignorée\*\* \(gris\)[^\n]*\| Non \|/);
    assert.match(compteurs, /\| \*\*Bloquée\*\* \(orange\)[^\n]*\| \*\*Oui\*\* \|/);
  });

  it('décrit la ligne des états de la pièce (zéros masqués, sans compteur de commandes) et la ligne des commandes', () => {
    assert.match(compteurs, /état \*\*non nul\*\*/);
    assert.match(compteurs, /Un état à zéro n'est pas affiché/);
    assert.match(compteurs, /pas de compteur de commandes au niveau de la pièce/);
    assert.match(compteurs, /3 publiées · 1 bloquée · 5 ignorées/);
    const order = ['publié', 'à appliquer', 'bloqué', 'exclu', 'désactivé', 'rien à publier'];
    const line = compteurs.match(/\*\*publié\*\*[^\n]*rien à publier\*\*/)[0];
    order.reduce((from, label) => { const at = line.indexOf(`**${label}**`, from); assert.ok(at >= from, label); return at; }, 0);
  });

  it('« Vérifier un chiffre » est supprimé et remplacé par « Comment lire un état »', () => {
    assert.doesNotMatch(compteurs, /Vérifier un chiffre|recompter à la main|Sera publié/);
    assert.match(compteurs, /^## Comment lire un état$/m);
  });

  it('cloisonnement : aucun libellé de compteur hors de ce fichier', () => {
    const counters = /\d (publiés?|publiées?|à appliquer|exclus?|exclues?|désactivés?|rien à publier|ignorées?)\b|Chargement des compteurs|Compteurs indisponibles|équipements? non lus?/;
    assert.doesNotMatch(index, counters);
    assert.doesNotMatch(changelogBeta, counters);
  });
});

describe('25.1 / AC23 — index.md décrit le détail réorganisé (Story 25.4 : dans la vue de travail)', () => {
  it('contrôle segmenté, menu « ⋯ », encart de cause, « Appliquer » conditionnel', () => {
    assert.match(index, /« Automatique », « Toujours », « Jamais »/);
    assert.match(index, /Le menu « ⋯ »/);
    assert.match(index, /Les encarts de cause/);
    assert.match(index, /seulement quand l'état est « À appliquer »/);
    assert.match(index, /Ouvrir les types génériques/);
    assert.match(index, /Un seul équipement est affiché à la fois/);
    assert.match(index, /sans autre barre de défilement dans le détail/);
  });

  it('les sections renommées existent ; la page principale n’annonce plus de recréation', () => {
    for (const heading of ['### Les badges de synthèse', '### Les causes de blocage', '### Réglages en attente et Appliquer',
      '### Les actions de publication', '#### Quand un bouton est grisé', '### Relire Jeedom']) {
      assert.ok(index.includes('\n' + heading + '\n'), heading);
    }
    assert.doesNotMatch(index, /Supprimer puis recréer|puis recréer/);
    assert.match(index, /Supprimer de Home Assistant…/);
    assert.match(index, /Rien n'est recréé automatiquement/);
  });

  it('les motifs de grisé cités sont ceux du code', () => {
    const reasons = ['Aucun réglage de publication à retirer.', 'Déjà publiée : « Toujours » n’aurait pas d’effet.',
      'Équipement non publié dans Home Assistant : rien à supprimer.', 'Aucun équipement à publier dans cette pièce.'];
    const source = fs.readFileSync('desktop/js/jeedom2ha_mapping_override.js', 'utf8');
    for (const reason of reasons) {
      assert.ok(index.includes(reason), reason);
      assert.ok(source.includes(reason), reason + ' (code)');
    }
  });
});

describe('25.1 / AC23 — changelog_beta.md', () => {
  it('une entrée annonce la story, avec les renommages (historique : les anciens mots y sont permis)', () => {
    assert.match(changelogBeta, /# 2026-10-18 — Un seul état par équipement, mots unifiés et fenêtre de pièce réorganisée/);
    assert.match(changelogBeta, /« Bridge » devient « Démon »/);
    assert.match(changelogBeta, /Aucune modification du démon/);
  });

  it('aucun nom réel d’équipement, de pièce, de scénario ou de personne (CC-48) : identifiants génériques seulement', () => {
    const entry = changelogBeta.split('---')[1];
    assert.doesNotMatch(entry, /\b(salon|cuisine|chambre|garage|Alexandre|Dupont)\b/i);
  });
});
