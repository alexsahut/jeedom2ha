// ARTEFACT — Story 25.4 (AC5) : la vue C n'ajoute AUCUNE lecture de `getEquipmentStates`. Elle lit la copie en
// mémoire de la page B ; seules les relectures déclenchées (fin d'action, retour d'onglet, « Actualiser ») passent par
// le lecteur de 25.3 (une relecture = un appel sans `refresh`, coalescée). Vrai code sur faux DOM ; données fictives.
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { startWorkview, startBig, openCardWide, phpAvailable } = require('./helpers/workview_harness');
const { okBody } = require('./helpers/page_b_harness');

const maybe = phpAvailable ? it : it.skip;
const js = (file) => fs.readFileSync(path.join(__dirname, '..', '..', 'desktop', 'js', file), 'utf8');
const stripComments = (source) => source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

describe('25.4 / AC5 — navigation sans lecture d’état', () => {
  maybe('ouvrir, naviguer, filtrer, chercher, replier le panneau, revenir, rouvrir : zéro getEquipmentStates', () => {
    const ui = startBig({ rooms: 4, equipments: 44, seed: 7 });
    assert.deepEqual(ui.reads(), { states: 1, trees: 0 }, 'une seule lecture d’état au chargement de la page B');
    openCardWide(ui, 10);
    ui.click('.j2ha-wv-room[data-object_id="11"] .j2ha-wv-row');
    ui.click('.j2ha-wv-room[data-object_id="12"] .j2ha-wv-toggle');
    ui.click('.j2ha-wv-chips .j2ha-chip-filter[data-filter="published"]');
    ui.click('.j2ha-wv-chips .j2ha-chip-filter[data-filter="published"]');
    const search = ui.$('.j2ha-wv-search').list[0];
    search.props.value = 'pièce 1';
    search.handlers.input.call(search, { target: search });
    ui.advance(400);
    ui.click('.j2ha-wv-drawer-toggle');
    ui.click('.j2ha-wv-back');
    openCardWide(ui, 12);
    assert.equal(ui.count('getEquipmentStates'), 1, 'aucune lecture d’état supplémentaire');
    assert.equal(ui.calls.filter((c) => String(c.data.refresh || '') !== '').length, 0, 'aucun paramètre refresh');
    assert.equal(ui.count('getMappingOverrides'), 0, 'aucun arbre lu sans sélection d’équipement');
  });

  maybe('une relecture déclenchée (fin d’action) = un appel sans refresh, coalescé ; la vue suit sans perdre la sélection', () => {
    const ui = startBig({ rooms: 3, equipments: 20, seed: 3 });
    openCardWide(ui, 10);
    const eqId = ui.$('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq').list[0].attrs['data-eq-id'];
    ui.sandbox.window.j2haNotifyStatesChanged = ui.sandbox.window.j2haNotifyStatesChanged || (() => ui.page.reader.trigger());
    ui.page.reader.trigger();
    ui.page.reader.trigger();
    ui.page.reader.trigger();
    ui.advance(500);
    assert.equal(ui.count('getEquipmentStates'), 2, 'trois signaux coalescés en une relecture');
    assert.equal(ui.pending('getEquipmentStates')[0].data.refresh, undefined, 'sans refresh');
    ui.selectEquipment(eqId);
    ui.respond('getEquipmentStates', okBody(ui.equipments));
    assert.equal(ui.$(`.j2ha-wv-eq[data-eq-id="${eqId}"]`).attr('aria-selected'), 'true', 'sélection conservée après la relecture');
  });

  maybe('« Actualiser » de la page B est le seul appelant de refresh=1', () => {
    const ui = startBig({ rooms: 3, equipments: 20, seed: 3 });
    ui.page.reader.refresh();
    assert.equal(ui.pending('getEquipmentStates')[0].data.refresh, '1');
    for (const file of ['jeedom2ha_workview.js', 'jeedom2ha_mapping_surface.js']) {
      assert.doesNotMatch(stripComments(js(file)), /refresh\s*[:=]\s*['"1t]|\.refresh\(/, file + ' ne pose jamais refresh');
    }
  });

  it('un seul site d’appel de la route agrégée dans le code : jeedom2ha_overview.js', () => {
    const sites = fs.readdirSync(path.join(__dirname, '..', '..', 'desktop', 'js'))
      .filter((f) => f.endsWith('.js'))
      .filter((f) => /getEquipmentStates/.test(stripComments(js(f))));
    assert.deepEqual(sites, ['jeedom2ha_overview.js']);
    const page = fs.readFileSync(path.join(__dirname, '..', '..', 'desktop', 'php', 'jeedom2ha.php'), 'utf8');
    assert.doesNotMatch(stripComments(page), /getEquipmentStates/);
  });
});

describe('25.4 / AC5 — états de lecture dégradés : mêmes mentions que la page B', () => {
  maybe('jamais synchronisé : la vue s’ouvre, l’arbre est rendu sans état, la mention de B est visible, ni NaN ni « non lu »', () => {
    const ui = startWorkview({ states: false });
    ui.respond('getEquipmentStates', { state: 'ok', result: { status: 'ok', payload: { schema_version: 1, available: false, equipments: {}, unread: [] } } });
    openCardWide(ui, 3);
    const status = ui.text('.j2ha-wv-read-status');
    assert.equal(status, "Aucune synchronisation n'a encore eu lieu");
    assert.equal(ui.$('.j2ha-wv-read-status').attr('role'), 'status');
    const view = ui.text('#j2ha_workView');
    assert.doesNotMatch(view, /NaN|undefined|null/);
    assert.doesNotMatch(view, /non lus?/);
    assert.equal(ui.$('.j2ha-wv-eq').length > 0, true, 'arbre rendu depuis la liste Jeedom');
    assert.equal(ui.$('.j2ha-wv-eq .j2ha-state-word').length, 0, 'aucune pastille d’état');
    ui.selectEquipment(102);
    assert.equal(ui.count('getMappingOverrides'), 1, 'le détail reste utilisable (arbre unitaire)');
  });

  maybe('lecture en erreur : « Chiffres indisponibles » ; opération en cours : « Mise à jour en cours… » (les libellés de B)', () => {
    const ui = startWorkview({ states: false });
    ui.respond('getEquipmentStates', { state: 'error', result: 'x' });
    openCardWide(ui, 3);
    assert.equal(ui.text('.j2ha-wv-read-status'), 'Chiffres indisponibles');
    const busy = startWorkview({ states: false });
    busy.respond('getEquipmentStates', { state: 'ok', result: { status: 'ok', payload: { schema_version: 1, available: false, reason: 'action_in_progress', equipments: {}, unread: [] } } });
    openCardWide(busy, 3);
    assert.equal(busy.text('.j2ha-wv-read-status'), 'Mise à jour en cours…');
  });
});
