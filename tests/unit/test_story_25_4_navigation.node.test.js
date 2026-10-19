// ARTEFACT — Story 25.4 (D2, AC1, AC3, AC9, AC10, AC16, AC17) : la table des événements de navigation avec, pour chacun,
// le nombre de lectures réseau attendu ; page principale restaurée ; barre de santé conservée ; retour d'une
// action dans la bonne pièce. Vrai code sur faux DOM ; données fictives (CC-48).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { startWorkview, startBig, openCard, phpAvailable } = require('./helpers/workview_harness');
const { tree, ok, READY, view } = require('./helpers/ui_harness');

const maybe = phpAvailable ? it : it.skip;
const entity = (type, ids, extra) => Object.assign({
  ha_entity_type: type, command_ids: ids, decision: READY, publication_override: null,
  override_command_id: ids[0], override_pending: false, present_in_ha: true,
}, extra || {});
const ACTION_OK = { state: 'ok', result: { payload: { resultat: 'succes', message: 'Fait.', perimetre_impacte: { nom: 'Périmètre X' } } } };

function delta(ui, run) {
  const before = ui.reads();
  run();
  const after = ui.reads();
  return { states: after.states - before.states, trees: after.trees - before.trees };
}

describe('25.4 / D2, AC10 — chaque événement et ses lectures réseau', () => {
  const rows = [
    ['clic sur une carte de pièce', (ui) => openCard(ui, 10), { states: 0, trees: 0 }],
    ['clic sur une puce du bloc maison', (ui) => ui.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="published"]'), { states: 0, trees: 0 }],
    ['clic sur un segment de la jauge maison', (ui) => ui.click('#j2ha_houseGauge .j2ha-seg-published'), { states: 0, trees: 0 }],
    ['clic sur une ligne de la liste filtrée', (ui) => {
      ui.page.setFilter('published');
      ui.click('#j2ha_filterList .j2ha-frow-btn');
    }, { states: 0, trees: 1 }],
    ['sélection d’une pièce dans l’arbre', (ui) => { openCard(ui, 10); ui.click('.j2ha-wv-room[data-object_id="11"] .j2ha-wv-row'); }, { states: 0, trees: 0 }],
    ['dépliage d’une pièce', (ui) => { openCard(ui, 10); ui.click('.j2ha-wv-room[data-object_id="12"] .j2ha-wv-toggle'); }, { states: 0, trees: 0 }],
    ['sélection d’un équipement dans l’arbre', (ui) => { openCard(ui, 10); ui.click('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq .j2ha-wv-row'); }, { states: 0, trees: 1 }],
    ['retour à la page principale', (ui) => { openCard(ui, 10); ui.click('.j2ha-wv-back'); }, { states: 0, trees: 0 }],
  ];
  for (const [name, run, expected] of rows) {
    maybe(name, () => {
      const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
      const got = delta(ui, () => run(ui));
      assert.deepEqual(got, expected, name);
      assert.equal(ui.isOpen(), name !== 'retour à la page principale');
    });
  }

  maybe('fin d’action sur l’équipement sélectionné : une relecture des états (sans refresh) et une relecture de son arbre', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    openCard(ui, 10);
    const eqId = Number(ui.$('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.selectEquipment(eqId, ok(tree(eqId, [READY], { entities: [entity('light', [eqId * 100], { override_pending: true })] })));
    const got = delta(ui, () => {
      ui.click(`.j2ha-eq-panel[data-eq-id="${eqId}"] .j2ha-eq-apply`);
      ui.respond('executeHaAction', ACTION_OK);
      ui.advance(500);
    });
    assert.deepEqual(got, { states: 1, trees: 1 });
    assert.equal(ui.pending('getEquipmentStates')[0].data.refresh, undefined);
  });

  maybe('fin d’action en échec : mêmes relectures (quelle que soit l’issue) et le bandeau de santé est relu', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    openCard(ui, 10);
    const before = ui.count('getBridgeStatus');
    ui.click('.j2ha-room-republish');
    ui.lastConfirmation().options.buttons.confirm.callback();
    ui.fail('executeHaAction');
    ui.advance(500);
    assert.equal(ui.count('getEquipmentStates'), 2);
    assert.equal(ui.count('getBridgeStatus'), before + 1);
    assert.match(ui.text('.j2ha-wv .j2ha-room-feedback'), /./);
  });
});

describe('25.4 / AC1, AC3, AC9, AC17 — coquille, restauration de la page principale, barre de santé', () => {
  maybe('aucune modale à l’ouverture ; la barre de santé reste visible, jauge / liste / cartes sont masquées puis restaurées', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    const dialogsBefore = ui.dom.dialogs.length;
    ui.page.setFilter('blocked');
    ui.win.scrollY = 640;
    openCard(ui, 11);
    assert.equal(ui.dom.dialogs.length, dialogsBefore, 'aucune bootbox de pièce');
    assert.equal(ui.$('.modal').length, 0);
    assert.equal(ui.visible('#div_bridgeHealthBanner'), true);
    assert.equal(ui.visible('#j2ha_mainView'), false, 'jauge, liste filtrée et cartes masquées');
    assert.equal(ui.visible('#j2ha_workView'), true);
    assert.equal(ui.$('#j2ha_roomCards .j2ha-room-card').length, 3, 'non détruites');
    ui.click('.j2ha-wv-back');
    assert.equal(ui.visible('#j2ha_mainView'), true);
    assert.equal(ui.visible('#j2ha_workView'), false);
    assert.equal(ui.page.filter(), 'blocked', 'filtre global conservé');
    assert.equal(ui.win.scrolls[ui.win.scrolls.length - 1], 640, 'position de défilement restaurée');
    assert.equal(ui.reads().states, 1, 'sans requête');
  });

  maybe('le gating et les boutons globaux de la barre restent opérants avec la vue ouverte', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    openCard(ui, 10);
    ui.bridgeUp();
    assert.equal(ui.$('.j2ha-ha-action[data-ha-action="republier"]').first().prop('disabled'), false);
    assert.equal(ui.$('.j2ha-room-republish').prop('disabled'), false, 'les actions de la vue suivent le même gating');
    ui.click('.j2ha-ha-action[data-ha-action="republier"]');
    assert.ok(ui.lastConfirmation(), 'confirmation forte de « Republier tout » intacte');
  });

  maybe('Échap : ferme le menu « ⋯ » ouvert puis ne fait rien d’autre (pas de sortie de la vue)', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    openCard(ui, 10);
    ui.click('.j2ha-wv .j2ha-menu-toggle');
    assert.ok(ui.$('.j2ha-wv .j2ha-menu-wrap').hasClass('j2ha-menu-open'));
    ui.key('.j2ha-wv .j2ha-menu-toggle', 'Escape');
    assert.ok(!ui.$('.j2ha-wv .j2ha-menu-wrap').hasClass('j2ha-menu-open'));
    ui.key('.j2ha-wv-tree', 'Escape');
    ui.key('.j2ha-wv-search', 'Escape');
    assert.equal(ui.isOpen(), true, 'Échap ne quitte jamais la vue');
  });

  maybe('la pièce « Sans pièce » est dans l’arbre ; ses actions de pièce sont indisponibles, le texte explicatif est conservé', () => {
    const ui = startWorkview();
    openCard(ui, 0);
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="0"]').length, 1);
    assert.equal(ui.$('.j2ha-room-republish, .j2ha-room-recreate').length, 0);
    assert.match(ui.text('.j2ha-wv-detail'), /Republication et suppression de pièce indisponibles/);
    ui.selectEquipment(111);
    assert.equal(ui.count('getMappingOverrides'), 1, 'les actions par équipement sont conservées');
  });
});

describe('25.4 / AC3, AC14 — gating des actions de pièce dès l’affichage du détail', () => {
  maybe('pont indisponible : « Republier la pièce » et « Supprimer… » sont grisés dès l’ouverture, sans attendre un rendu de B', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4, bridge: false });
    openCard(ui, 10);
    assert.equal(ui.$('.j2ha-room-republish').prop('disabled'), true);
    assert.equal(ui.$('.j2ha-room-recreate').prop('disabled'), true);
    assert.equal(ui.$('.j2ha-wv-todo-apply').length === 0 || ui.$('.j2ha-wv-todo-apply').first().prop('disabled') === true, true);
  });

  maybe('aucun équipement à republier dans la pièce (tout désactivé ou exclu) : « Republier » grisé avec sa cause, lu dans les entrées agrégées', () => {
    const { FIXTURE, clone } = require('./helpers/page_b_harness');
    const scene = { objects: [{ id: 10, name: 'Zone fictive', father_id: null, display: {} }], eqlogics: { 10: [{ id: 1, name: 'Eq 1', enabled: false }, { id: 2, name: 'Eq 2', enabled: true }] }, doc: 'https://doc.example.test/plugin' };
    const equipments = { 1: Object.assign(clone(FIXTURE['104'].aggregated), { jeedom_eq_id: 1 }), 2: Object.assign(clone(FIXTURE['110'].aggregated), { jeedom_eq_id: 2 }) };
    const ui = startWorkview({ scene, equipments });
    openCard(ui, 10);
    const button = ui.$('.j2ha-room-republish');
    assert.equal(button.prop('disabled'), true);
    assert.equal(button.attr('data-ha-state-blocked'), '1');
    assert.equal(button.attr('title'), 'Aucun équipement à publier dans cette pièce.');
    assert.equal(ui.count('getMappingOverrides'), 0);
  });
});

describe('25.4 / AC16 — retour d’une action : la bonne pièce, jamais une autre', () => {
  maybe('pièce toujours affichée : résultat dans le détail ; pièce quittée : dans la zone d’alerte de la page', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    openCard(ui, 10);
    ui.click('.j2ha-room-republish');
    ui.lastConfirmation().options.buttons.confirm.callback();
    ui.respond('executeHaAction', ACTION_OK);
    assert.match(ui.text('.j2ha-wv .j2ha-room-feedback'), /Périmètre X — Fait\./);
    assert.equal(ui.dom.alerts.length, 0);

    openCard(ui, 10);
    ui.click('.j2ha-room-republish');
    ui.lastConfirmation().options.buttons.confirm.callback();
    ui.click('.j2ha-wv-room[data-object_id="11"] .j2ha-wv-row');
    ui.respond('executeHaAction', ACTION_OK);
    assert.equal(ui.dom.alerts.length, 1, 'zone d’alerte de la page');
    assert.match(ui.dom.alerts[0].message, /Périmètre X — Fait\./);
    assert.equal(ui.text('.j2ha-wv .j2ha-room-feedback'), '', 'rien dans le détail de l’autre pièce');
  });

  maybe('le bouton qui lance l’action est réservé pendant l’appel (pas de double envoi)', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    openCard(ui, 10);
    ui.click('.j2ha-room-republish');
    ui.lastConfirmation().options.buttons.confirm.callback();
    assert.equal(ui.$('.j2ha-room-republish').attr('data-ha-pending'), '1');
    assert.equal(ui.$('.j2ha-room-republish').prop('disabled'), true);
    ui.click('.j2ha-room-republish');
    assert.equal(ui.pending('executeHaAction').length, 1);
  });
});

describe('25.4 / AC4 — pas d’erreur quand l’état disparaît', () => {
  maybe('un équipement sélectionné qui disparaît de la liste après relecture : retour à la sélection de sa pièce, sans erreur', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    openCard(ui, 10);
    const eqId = Number(ui.$('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.selectEquipment(eqId, ok(tree(eqId, [READY])));
    const withoutRoom10 = ui.rooms.filter((r) => r.object_id !== 10);
    assert.doesNotThrow(() => ui.wv.reconcile(withoutRoom10));
    assert.equal(ui.isOpen(), true);
    assert.equal(ui.$('.j2ha-eq-panel').length, 0);
    assert.match(ui.text('.j2ha-wv-detail'), /Sélectionnez une pièce ou un équipement/);
  });
});

void view;
void startWorkview;
