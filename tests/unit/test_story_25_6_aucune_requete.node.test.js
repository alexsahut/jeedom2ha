// ARTEFACT — Story 25.6 (AC6) : la portée est un filtre d'affichage sur des données déjà en mémoire. Ouvrir depuis une
// carte, élargir, chercher, filtrer, revenir, rouvrir une autre carte, « Précédent » / « Suivant » : zéro getEquipmentStates
// et zéro getMappingOverrides (hors sélection explicite d'un équipement : une lecture par sélection, 25.4 D3).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { startBig, openCard, phpAvailable } = require('./helpers/workview_harness');

const maybe = phpAvailable ? it : it.skip;
const js = (file) => fs.readFileSync(path.join(__dirname, '..', '..', 'desktop', 'js', file), 'utf8');

describe('25.6 / AC6 — zéro requête', () => {
  maybe('parcours complet de navigation sans aucune lecture réseau', () => {
    const ui = startBig({ rooms: 4, equipments: 44, seed: 7 });
    const before = ui.calls.length;
    openCard(ui, 10);
    ui.click('.j2ha-wv-chips .j2ha-chip-filter[data-filter="published"]');
    ui.click('.j2ha-wv-chips .j2ha-chip-filter[data-filter="published"]');
    const search = ui.$('.j2ha-wv-search').list[0];
    search.props.value = 'eq';
    search.handlers.input.call(search, { target: search });
    ui.advance(400);
    ui.click('.j2ha-wv-widen');
    ui.click('.j2ha-wv-room[data-object_id="11"] .j2ha-wv-row');
    ui.win.history.back();
    ui.win.history.forward();
    ui.click('.j2ha-wv-back');
    openCard(ui, 12);
    ui.click('.j2ha-wv-widen');
    ui.click('.j2ha-wv-back');
    assert.equal(ui.calls.length, before, 'aucune requête du tout');
    assert.equal(ui.count('getEquipmentStates'), 1, 'la seule lecture est celle du chargement de la page B');
    assert.equal(ui.count('getMappingOverrides'), 0);
  });

  maybe('sélectionner un équipement en portée pièce : une seule lecture d’arbre', () => {
    const ui = startBig({ rooms: 4, equipments: 44, seed: 7 });
    openCard(ui, 10);
    const before = ui.reads();
    const eq = Number(ui.$('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.click(`.j2ha-wv-eq[data-eq-id="${eq}"] .j2ha-wv-row`);
    assert.equal(ui.reads().trees - before.trees, 1);
    assert.equal(ui.reads().states - before.states, 0);
  });

  it('les sites d’appel de desktop/js sont inchangés : la vue C (hors commentaires) ne nomme aucune de ces deux routes', () => {
    const strip = (source) => source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
    assert.doesNotMatch(strip(js('jeedom2ha_workview.js')), /getEquipmentStates|getMappingOverrides/);
    assert.doesNotMatch(strip(js('jeedom2ha_overview.js')), /getMappingOverrides/);
    assert.equal((strip(js('jeedom2ha_overview.js')).match(/getEquipmentStates/g) || []).length, 1, 'un seul site de lecture des états (page B)');
  });
});
