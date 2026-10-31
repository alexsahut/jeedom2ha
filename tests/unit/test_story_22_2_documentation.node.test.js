// ARTEFACT — Story 22.2 (AC4, AC9) : la page des compteurs est réécrite (plus de bandeau
// d'obsolescence), garde ses emplacements de capture, et les libellés de compteur et d'action
// décrits dans la documentation sont ceux que rend l'interface.
'use strict';

const fs = require('node:fs');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

const compteurs = fs.readFileSync('docs/fr_FR/compteurs.md', 'utf8');
const index = fs.readFileSync('docs/fr_FR/index.md', 'utf8');
const changelogBeta = fs.readFileSync('docs/fr_FR/changelog_beta.md', 'utf8');

describe('22.2 / AC9 — docs/fr_FR/compteurs.md', () => {
  it('bloc isolé conservé, bandeau d’obsolescence retiré', () => {
    assert.match(compteurs, /COMPTEURS:DEBUT/);
    assert.match(compteurs, /<!-- COMPTEURS:FIN -->\s*$/);
    assert.doesNotMatch(compteurs, /tels qu'ils fonctionnent aujourd'hui|avant la story compteurs|doit évoluer dans une prochaine version/);
  });

  it('emplacements de captures conservés', () => {
    assert.match(compteurs, /<!-- CAPTURE-A-PRENDRE: compteurs du détail de pièce -->/);
  });

  it('décrit la notion « publié = présent dans Home Assistant » et chaque état rendu par l’interface (25.1 : un état unique)', () => {
    // 25.1 : les trois chiffres de 22.2 (publiés / en attente / non pris en charge) sont remplacés par un
    // état unique ; la ligne de la pièce compte un mot par état, la sémantique « présent dans HA » demeure.
    const states = Object.values(M.EQUIPMENT_STATE_LABELS);
    assert.equal(states.length, 6);
    states.forEach((label) => assert.ok(compteurs.includes(`**${label}**`), label));
    const room = M.buildRoomCounterLabels({ equipments_total: 6, equipments_read: 6,
      by_state: { published: 1, to_apply: 1, blocked: 1, excluded: 1, disabled: 1, nothing_to_publish: 1 } });
    assert.equal(room.items.length, 6);
    room.items.forEach((item) => {
      const word = item.text.replace(/^\d+ /, '');
      assert.ok(compteurs.includes(`**${word}**`) || compteurs.includes(word), word);
    });
    assert.match(compteurs, /présent dans Home Assistant/);
    assert.match(compteurs, /au moins une/);
  });

  it('cloisonnement : aucun libellé de compteur hors de ce fichier', () => {
    const forbidden = /[0-9N] (équipements? (publiés?|exclus?|désactivés?|à corriger|non lus?)|commandes? (prêtes?|bloquantes?|non couvertes?))|Chargement des compteurs|Compteurs indisponibles|à corriger/;
    assert.doesNotMatch(index, forbidden);
    assert.doesNotMatch(changelogBeta, forbidden);
  });
});

describe('22.2 / AC4 — « Supprimer de Home Assistant » dans la documentation', () => {
  it('la page principale n’annonce plus de recréation', () => {
    assert.doesNotMatch(index, /Supprimer puis recréer|puis recréer/);
    assert.match(index, /Supprimer de Home Assistant/);
    // 25.1 : « Supprimer la pièce de Home Assistant » devient « Supprimer de Home Assistant… » dans le menu de la pièce.
    assert.match(index, /Supprimer de Home Assistant…/);
    assert.match(index, /Rien n'est recréé automatiquement/);
  });

  it('le journal de la version beta annonce le renommage', () => {
    assert.match(changelogBeta, /2026-10-12 — Compteurs fondés sur la présence dans Home Assistant/);
  });
});
