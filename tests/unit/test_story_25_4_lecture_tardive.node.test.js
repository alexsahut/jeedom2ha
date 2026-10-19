// ARTEFACT — Story 25.4 (AC6, AC7 partiel, D3) : les arbres unitaires (`getMappingOverrides`) ne sont lus qu'à la
// SÉLECTION d'un équipement : un appel exactement, relu à chaque sélection (Q9), une réponse tardive d'une sélection
// abandonnée est ignorée sans erreur. Vrai code sur faux DOM ; identifiants et données fictifs (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { startBig, openCardWide, phpAvailable } = require('./helpers/workview_harness');
const { tree, ok, READY, view } = require('./helpers/ui_harness');

const BLOCKED_VIEW = view('no_generic_type_configured', false, false);

const maybe = phpAvailable ? it : it.skip;
const root = path.join(__dirname, '..', '..');
const stripComments = (source) => source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

function eqIdsOf(ui, objectId) {
  return ui.$(`.j2ha-wv-room[data-object_id="${objectId}"] .j2ha-wv-eq`).list.map((el) => Number(el.attrs['data-eq-id']));
}

describe('25.4 / AC6 — zéro lecture d’arbre tant qu’aucun équipement n’est sélectionné', () => {
  maybe('≥ 3 pièces, ≥ 40 équipements : ouvrir, choisir une pièce, déplier, filtrer, chercher → 0 appel', () => {
    const ui = startBig({ rooms: 4, equipments: 44, seed: 11 });
    openCardWide(ui, 10);
    ui.click('.j2ha-wv-room[data-object_id="11"] .j2ha-wv-row');
    ui.click('.j2ha-wv-room[data-object_id="12"] .j2ha-wv-toggle');
    ui.click('.j2ha-wv-room[data-object_id="13"] .j2ha-wv-toggle');
    ui.click('.j2ha-wv-chips .j2ha-chip-filter[data-filter="blocked"]');
    const search = ui.$('.j2ha-wv-search').list[0];
    search.props.value = 'eq';
    search.handlers.input.call(search, { target: search });
    ui.advance(400);
    assert.equal(ui.count('getMappingOverrides'), 0);
  });

  maybe('100 équipements : l’ouverture de n’importe quelle pièce ne lit aucun arbre (plus de préchargement par équipement)', () => {
    const ui = startBig({ rooms: 5, equipments: 100, seed: 5 });
    for (const id of [10, 11, 12, 13, 14]) openCardWide(ui, id);
    assert.equal(ui.count('getMappingOverrides'), 0);
  });

  it('un seul site d’appel de getMappingOverrides, hors de toute boucle sur les pièces ou les équipements ; plus de préchargement', () => {
    const surface = stripComments(fs.readFileSync(path.join(root, 'desktop/js/jeedom2ha_mapping_surface.js'), 'utf8'));
    const sites = surface.match(/action:\s*'getMappingOverrides'/g) || [];
    assert.equal(sites.length, 1, 'une seule fonction de lecture');
    for (const file of fs.readdirSync(path.join(root, 'desktop/js')).filter((f) => f.endsWith('.js'))) {
      const code = stripComments(fs.readFileSync(path.join(root, 'desktop/js', file), 'utf8'));
      assert.doesNotMatch(code, /\.j2ha-eq-panel'\)\.each/, file);
      if (file !== 'jeedom2ha_mapping_surface.js') assert.doesNotMatch(code, /getMappingOverrides/, file);
    }
    // Le site est dans `loadEquipment` ; aucune boucle (`for`, `forEach`, `.each`) ne l'encadre.
    const start = surface.indexOf('function loadEquipment');
    const fn = surface.slice(start, surface.indexOf('\n  }\n', start));
    assert.match(fn, /getMappingOverrides/);
    assert.doesNotMatch(fn, /\bfor\s*\(|\.forEach\(|\.each\(/);
  });
});

describe('25.4 / AC6 — une sélection = une lecture', () => {
  maybe('sélectionner un équipement émet exactement un appel avec son eqId ; resélectionner le rafraîchit (Q9)', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 2 });
    openCardWide(ui, 10);
    const [first, second] = eqIdsOf(ui, 10);
    ui.selectEquipment(first);
    assert.equal(ui.count('getMappingOverrides'), 1);
    assert.equal(ui.pending('getMappingOverrides')[0].data.eqId, first);
    ui.respond('getMappingOverrides', ok(tree(first, [READY])));
    assert.equal(ui.$(`.j2ha-eq-panel[data-eq-id="${first}"] .j2ha-cmd-table`).length, 1, 'tableau des commandes rendu');
    ui.selectEquipment(second, ok(tree(second, [READY])));
    ui.selectEquipment(first, ok(tree(first, [READY])));
    assert.equal(ui.count('getMappingOverrides'), 3, 'chaque sélection relit l’arbre, sans cache');
  });

  maybe('sélection d’une pièce : aucun appel ; sélection du même équipement pendant sa lecture : pas de doublon', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 2 });
    openCardWide(ui, 10);
    const [first] = eqIdsOf(ui, 10);
    ui.click('.j2ha-wv-room[data-object_id="11"] .j2ha-wv-row');
    assert.equal(ui.count('getMappingOverrides'), 0);
    ui.click('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-row');
    ui.selectEquipment(first);
    ui.selectEquipment(first);
    assert.equal(ui.count('getMappingOverrides'), 1, 'une lecture en vol pour le même équipement n’est pas doublée');
    ui.respond('getMappingOverrides', ok(tree(first, [READY])));
    assert.equal(ui.$(`.j2ha-eq-panel[data-eq-id="${first}"] .j2ha-cmd-table`).length, 1);
  });

  maybe('A puis B rapidement : deux appels, seule la réponse de B est rendue ; celle de A, tardive, est ignorée sans erreur', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 2 });
    openCardWide(ui, 10);
    const [a, b] = eqIdsOf(ui, 10);
    ui.selectEquipment(a);
    ui.selectEquipment(b);
    assert.equal(ui.count('getMappingOverrides'), 2);
    const lateA = ui.pending('getMappingOverrides').find((c) => c.data.eqId === a);
    const answerB = ui.pending('getMappingOverrides').find((c) => c.data.eqId === b);
    answerB.respond(ok(tree(b, [READY])));
    assert.equal(ui.$(`.j2ha-eq-panel[data-eq-id="${b}"] .j2ha-cmd-table`).length, 1);
    const before = ui.text('.j2ha-wv-detail');
    lateA.respond(ok(tree(a, [BLOCKED_VIEW])));
    assert.equal(ui.$(`.j2ha-eq-panel[data-eq-id="${a}"]`).length, 0, 'la réponse tardive de A n’est pas rendue');
    assert.equal(ui.text('.j2ha-wv-detail'), before, 'l’affichage courant n’est pas touché');
    // Échec tardif de A : ignoré aussi.
    ui.selectEquipment(a);
    ui.selectEquipment(b);
    ui.pending('getMappingOverrides').find((c) => c.data.eqId === a).fail();
    assert.equal(ui.$(`.j2ha-eq-panel[data-eq-id="${b}"] .j2ha-eq-status`).length, 1);
    assert.doesNotMatch(ui.text(`.j2ha-eq-panel[data-eq-id="${b}"] .j2ha-eq-status`), /Impossible/);
  });

  maybe('quitter la vue annule les lectures en vol : aucune écriture dans un DOM détaché, aucune erreur', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 2 });
    openCardWide(ui, 10);
    const [a] = eqIdsOf(ui, 10);
    ui.selectEquipment(a);
    ui.click('.j2ha-wv-back');
    assert.doesNotThrow(() => ui.respond('getMappingOverrides', ok(tree(a, [READY]))));
    assert.equal(ui.$(`.j2ha-eq-panel[data-eq-id="${a}"]`).length, 0);
  });
});
