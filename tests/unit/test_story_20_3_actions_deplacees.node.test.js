// ARTEFACT — Story 20.3 (AC4, Q2=A, Q2b=A) : « Republier la pièce » et « Supprimer de Home Assistant » (ex. « Supprimer puis recréer », renommé en 22.2)
// (pièce et équipement) vivent dans la modale de pièce, sur les routes existantes (executeHaAction)
// avec les confirmations fortes ; les boutons globaux n'affichent plus de nombre.
// Le comportement des actions est exercé sur le VRAI code dans
// test_story_20_3_r1_ui_reelle.node.test.js (R1-G : plus aucun faux des fonctions d'état/confirmation) ;
// ce fichier garde les contrôles de source des textes décidés et du câblage du gating.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');

const surface = fs.readFileSync('desktop/js/jeedom2ha_mapping_surface.js', 'utf8');
const home = fs.readFileSync('desktop/js/jeedom2ha.js', 'utf8');

describe('20.3 / Q2b=A — boutons globaux sans nombre', () => {
  it('les confirmations globales ne lisent plus data-scope-count / data-scope-publies', () => {
    assert.doesNotMatch(home, /data-scope-count|data-scope-publies|_readHaActionCount/);
  });

  it('textes décidés : « Republier tous les équipements inclus ? » et « Supprimer de Home Assistant tout le parc publié ? » avec la mise en garde forte', () => {
    assert.match(home, /\{\{Republier tous les équipements inclus \?\}\}/);
    const del = home.match(/\$\('\.j2ha-ha-action\[data-ha-action="supprimer-recreer"\]'\)[\s\S]*?\n  \}\);/);
    assert.ok(del, 'gestionnaire global supprimer absent');
    assert.match(del[0], /\{\{Supprimer de Home Assistant tout le parc publié \?\}\}/);
    for (const word of ['Attention', 'historique', 'dashboards', 'automatisations', 'entity_id']) {
      assert.ok(del[0].includes(word), word);
    }
    // Story 22.2 (Q5 A, CC-55) : le libellé promet ce que fait l'action ; « Republier » remet.
    assert.match(del[0], /Rien n\\'est recréé automatiquement/);
    assert.match(del[0], /« Republier »/);
    assert.doesNotMatch(del[0], /recréer/);
    assert.match(del[0], /triggerSupprimerAction\(\$button, 'global', \['all'\], reservation\)/);
    assert.match(home, /triggerPublierAction\(\$button, 'global', \['all'\], reservation\)/);
  });
});

describe('20.3 / AC4 — gating indépendant d’un rendu de synthèse', () => {
  it('applyHAGating ne lit aucun élément de synthèse et les boutons de la surface suivent le gating', () => {
    const gating = home.match(/function applyHAGating[\s\S]*?\n\}/)[0];
    assert.doesNotMatch(gating, /scopeSummary/);
    // Story 25.1 : les entrées du menu « ⋯ » portent `data-ha-action` (posé par buildMenu).
    assert.match(surface, /\.attr\('data-ha-action', entry\.haAction\)/);
    assert.match(surface, /haAction: 'republier'/);
    assert.match(surface, /haAction: 'supprimer'/);
    assert.match(surface, /applyHAGating\(window\.jeedom2haLastBridgeStatus \|\| null\)/);
  });

  it('le bouton « Supprimer de Home Assistant » ajouté après le chargement de l’arbre est soumis au gating', () => {
    const render = surface.match(/function renderControls[\s\S]*?\n  function renderEquipmentTree/)[0];
    const afterButton = render.slice(render.indexOf('buildMenu('));
    assert.match(afterButton, /reapplyBridgeGating\(\)/);
    assert.match(surface, /function reapplyBridgeGating[\s\S]*?applyHAGating\(window\.jeedom2haLastBridgeStatus \|\| null\)/);
  });

  it('les triggers globaux ne rafraîchissent plus de synthèse', () => {
    const publier = home.match(/function triggerPublierAction[\s\S]*?\n\}/)[0];
    const supprimer = home.match(/function triggerSupprimerAction[\s\S]*?\n\}/)[0];
    assert.doesNotMatch(publier + supprimer, /refreshPublishedScopeSummary|preserveNavState/);
    assert.match(publier, /executeHaAction\('publier'/);
    assert.match(supprimer, /executeHaAction\('supprimer'/);
  });
});
