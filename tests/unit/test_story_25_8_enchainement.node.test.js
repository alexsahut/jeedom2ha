// ARTEFACT — Story 25.8 (AC9, AC10, AC11, AC16) : l'exclusion d'une pièce enchaîne, dans cet ordre, `saveRoomExclusion` (une),
// `scanTopology` (une, par le chemin de « Relire Jeedom ») puis une lecture `getEquipmentStates` sans refresh ; aucune autre écriture.
// Une erreur de la route n'entraîne aucune relecture ; un échec de la relecture laisse l'exclusion enregistrée et invite à relancer
// « Relire Jeedom » ; les réservations sont libérées dans tous les cas. Vrai code sur faux DOM ; identifiants fictifs (CC-48).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { startWorkview, phpAvailable } = require('./helpers/workview_harness');
const { plain, okBody } = require('./helpers/page_b_harness');

const maybe = phpAvailable ? it : it.skip;

const SCENE = {
  objects: [{ id: 2, name: 'Pièce fictive A', father_id: null, display: {} }, { id: 3, name: 'Pièce fictive B', father_id: null, display: {} }],
  eqlogics: { 2: [{ id: 201, name: 'Eq 201' }, { id: 202, name: 'Eq 202' }], 3: [{ id: 301, name: 'Eq 301' }] },
  config: { excludedObjects: '' },
};
const diag = (reason, publish) => ({ confidence: null, ha_entity_type: null, publication_reason: reason, reason_code: null, should_publish: publish,
  projection_validity: { is_valid: publish, missing_capabilities: [], missing_fields: [], reason_code: publish ? null : reason } });
const published = (id) => ({
  jeedom_eq_id: id, equipment_decision: diag('sure_mapping', true),
  entities: [{ override_pending: false, present_in_ha: true }],
  commands: [{ jeedom_cmd_id: id * 10, covered: true, diagnostic: diag('sure_mapping', true), published_in_ha: true }],
  sync_status: { published_in_ha: true, synced_should_publish: true, current_should_publish: true, override_pending: false },
});
const excludedEntry = (id) => ({
  jeedom_eq_id: id, equipment_decision: diag('excluded_object', false), entities: [],
  commands: [{ jeedom_cmd_id: id * 10, covered: false, diagnostic: diag('excluded_object', false), published_in_ha: false }],
  sync_status: { published_in_ha: false, synced_should_publish: false, current_should_publish: false, override_pending: false },
});
const EQUIPMENTS = { 201: published(201), 202: published(202), 301: published(301) };

const SAVE_OK = (ids, changed) => ({ state: 'ok', result: { object_id: 2, excluded: true, changed: changed !== false, excluded_objects: ids } });
const SCAN_OK = { state: 'ok', result: { status: 'ok', operation_result: 'succes', operation_message: 'Synchronisation terminée.' } };
const ITEM = (id) => `#j2ha_roomCards .j2ha-room-card[data-object_id="${id}"] .j2ha-room-exclude`;
const WRITES = ['saveRoomExclusion', 'scanTopology', 'executeHaAction', 'savePublicationOverride', 'saveMappingOverride', 'revertMappingOverride', 'revertPublicationOverride', 'saveFilteringConfig'];

function start(options) {
  const ui = startWorkview(Object.assign({ scene: SCENE, equipments: EQUIPMENTS }, options || {}));
  ui.bridgeUp();
  return ui;
}

/** Ouvre la confirmation d'exclusion de la pièce `id` puis clique sur le bouton de confirmation. */
function confirmExclusion(ui, id) {
  ui.click(ITEM(id));
  const dlg = ui.lastConfirmation();
  dlg.options.buttons.confirm.callback();
  dlg.close();
  return dlg;
}
const actions = (ui) => ui.calls.map((c) => c.action);
const alertTexts = (ui) => ui.dom.alerts.map((a) => plain(a.message));
// Les objets du faux navigateur viennent d'un autre contexte `vm` : comparés après copie JSON.
const json = (value) => JSON.parse(JSON.stringify(value));

describe('25.8 / AC9 — enchaînement écriture → relecture → lecture des états', () => {
  maybe('ordre exact : saveRoomExclusion, scanTopology, puis une lecture getEquipmentStates sans refresh ; aucune autre écriture', () => {
    const ui = start();
    const from = ui.calls.length;
    confirmExclusion(ui, 2);
    assert.deepEqual(json(actions(ui).slice(from)), ['saveRoomExclusion'], 'une écriture, rien d\'autre tant qu\'elle n\'a pas répondu');
    ui.respond('saveRoomExclusion', SAVE_OK([2]));
    assert.deepEqual(json(actions(ui).slice(from)), ['saveRoomExclusion', 'scanTopology']);
    ui.respond('scanTopology', SCAN_OK);
    ui.advance(600);
    assert.equal(ui.count('getEquipmentStates'), 2, 'une lecture des états de plus (celle du chargement + celle de la fin d\'action)');
    ui.respond('getEquipmentStates', okBody(EQUIPMENTS));
    const after = ui.calls.slice(from);
    const writes = after.filter((c) => WRITES.includes(c.action)).map((c) => c.action);
    assert.deepEqual(writes, ['saveRoomExclusion', 'scanTopology']);
    assert.equal(after.filter((c) => c.action === 'getEquipmentStates').length, 1);
    assert.deepEqual(json(after.find((c) => c.action === 'saveRoomExclusion').data), { action: 'saveRoomExclusion', objectId: '2', excluded: '1' });
    assert.ok(after.findIndex((c) => c.action === 'getEquipmentStates') > after.findIndex((c) => c.action === 'scanTopology'));
    assert.equal(after.find((c) => c.action === 'getEquipmentStates').data.refresh, undefined, 'jamais refresh=1');
  });

  maybe('« ne plus exclure » écrit excluded=0 et suit la même séquence', () => {
    const ui = start({ scene: Object.assign({}, SCENE, { config: { excludedObjects: '2' } }) });
    const from = ui.calls.length;
    confirmExclusion(ui, 2);
    assert.deepEqual(json(ui.calls[from].data), { action: 'saveRoomExclusion', objectId: '2', excluded: '0' });
    ui.respond('saveRoomExclusion', { state: 'ok', result: { object_id: 2, excluded: false, changed: true, excluded_objects: [] } });
    assert.equal(ui.pending('scanTopology').length, 1);
  });

  maybe('la relecture est celle de « Relire Jeedom » : mêmes url, type, corps, délai client et messages de résultat', () => {
    const viaRescanButton = start();
    viaRescanButton.click('#bt_rescanTopology');
    viaRescanButton.lastConfirmation().options.buttons.confirm.callback();
    const reference = viaRescanButton.pending('scanTopology')[0].options;

    const ui = start();
    confirmExclusion(ui, 2);
    ui.respond('saveRoomExclusion', SAVE_OK([2]));
    const chained = ui.pending('scanTopology')[0].options;
    for (const key of ['type', 'url', 'dataType', 'timeout']) assert.deepEqual(json(chained[key]), json(reference[key]), key);
    assert.deepEqual(json(chained.data), json(reference.data));
    assert.deepEqual(json(chained.data), { action: 'scanTopology' });
    ui.respond('scanTopology', SCAN_OK);
    assert.ok(alertTexts(ui).includes('Synchronisation terminée.'), 'message de « Relire Jeedom »');
  });

  maybe('les drapeaux « pièce exclue » sont remplacés pour TOUTES les pièces depuis excluded_objects, sans recharger la page', () => {
    const ui = start();
    assert.equal(ui.page.isRoomExcluded(2), false);
    confirmExclusion(ui, 2);
    ui.respond('saveRoomExclusion', SAVE_OK([2, 3]));
    assert.equal(ui.page.isRoomExcluded(2), true);
    assert.equal(ui.page.isRoomExcluded(3), true, 'écriture concurrente d\'un autre onglet reflétée');
    assert.ok(ui.text('#j2ha_roomCards .j2ha-room-card[data-object_id="2"] .j2ha-room-state').includes('Pièce exclue'));
    assert.equal(ui.$(ITEM(2)).attr('data-excluded'), '1');
    assert.equal(plain(ui.$(`${ITEM(2)} .j2ha-room-exclude-label`).text()), 'Ne plus exclure la pièce…');
  });

  maybe('fin de relecture : refreshBridgeStatus puis relecture des états ; « Relire Jeedom » rendu', () => {
    const ui = start();
    confirmExclusion(ui, 2);
    ui.respond('saveRoomExclusion', SAVE_OK([2]));
    const bridgeBefore = ui.count('getBridgeStatus');
    ui.respond('scanTopology', SCAN_OK);
    assert.equal(ui.count('getBridgeStatus'), bridgeBefore + 1, 'refreshBridgeStatus à la fin');
    assert.equal(ui.sandbox.window.jeedom2haRescanInProgress, false);
    ui.respond('getBridgeStatus', { state: 'ok', result: { daemon: true, broker: { state: 'connected' }, derniere_operation_resultat: 'aucun' } });
    assert.equal(ui.isDisabled('#bt_rescanTopology'), false);
    assert.equal(ui.isDisabled(ITEM(2)), false);
  });
});

describe('25.8 / AC10 — échecs', () => {
  maybe('erreur de la route : aucune relecture, aucun drapeau changé, message, réservations libérées', () => {
    const ui = start();
    confirmExclusion(ui, 2);
    ui.respond('saveRoomExclusion', { state: 'error', result: 'Pièce introuvable' });
    assert.equal(ui.count('scanTopology'), 0);
    assert.equal(ui.page.isRoomExcluded(2), false);
    assert.ok(alertTexts(ui).includes('Pièce introuvable'));
    assert.equal(ui.sandbox.window.jeedom2haRescanInProgress, false);
    assert.equal(ui.isDisabled('#bt_rescanTopology'), false);
  });

  maybe('réponse sans excluded_objects : traitée comme une erreur, aucune relecture', () => {
    const ui = start();
    confirmExclusion(ui, 2);
    ui.respond('saveRoomExclusion', { state: 'ok', result: { changed: true } });
    assert.equal(ui.count('scanTopology'), 0);
    assert.equal(ui.page.isRoomExcluded(2), false);
    assert.equal(ui.sandbox.window.jeedom2haRescanInProgress, false);
  });

  maybe('échec réseau (ou délai client dépassé) de la route : aucune relecture, vérification de l\'état invitée', () => {
    const ui = start();
    confirmExclusion(ui, 2);
    ui.fail('saveRoomExclusion');
    assert.equal(ui.count('scanTopology'), 0);
    assert.equal(ui.page.isRoomExcluded(2), false);
    assert.ok(alertTexts(ui).some((t) => t.includes("n'a pas pu être confirmée")));
    assert.equal(ui.sandbox.window.jeedom2haRescanInProgress, false);
    const save = ui.calls.find((c) => c.action === 'saveRoomExclusion');
    assert.equal(save.options.timeout, 20000, 'délai client borné');
  });

  maybe('relecture refusée (opération déjà en cours) : l\'exclusion reste enregistrée, message + invitation à relancer', () => {
    const ui = start();
    confirmExclusion(ui, 2);
    ui.respond('saveRoomExclusion', SAVE_OK([2]));
    ui.respond('scanTopology', { state: 'error', result: 'Une opération est déjà en cours' });
    assert.equal(ui.page.isRoomExcluded(2), true, 'drapeau à jour');
    assert.ok(ui.text('#j2ha_roomCards .j2ha-room-card[data-object_id="2"] .j2ha-room-state').includes('Pièce exclue'));
    const alerts = alertTexts(ui);
    assert.ok(alerts.includes('Une opération est déjà en cours'));
    assert.ok(alerts.includes('Relancez « Relire Jeedom » pour retirer les entités.'));
    assert.equal(ui.sandbox.window.jeedom2haRescanInProgress, false);
    ui.advance(600);
    assert.equal(ui.count('getEquipmentStates'), 2, 'notifyStatesChanged après la relecture tentée');
  });

  maybe('relecture en échec (réseau, ou échec du démon) : même invitation', () => {
    const network = start();
    confirmExclusion(network, 2);
    network.respond('saveRoomExclusion', SAVE_OK([2]));
    network.fail('scanTopology');
    assert.ok(alertTexts(network).includes('Relancez « Relire Jeedom » pour retirer les entités.'));
    assert.equal(network.page.isRoomExcluded(2), true);
    const daemon = start();
    confirmExclusion(daemon, 2);
    daemon.respond('saveRoomExclusion', SAVE_OK([2]));
    daemon.respond('scanTopology', { state: 'ok', result: { status: 'ok', operation_result: 'echec', operation_message: 'Synchronisation échouée.' } });
    assert.ok(alertTexts(daemon).includes('Synchronisation échouée.'));
    assert.ok(alertTexts(daemon).includes('Relancez « Relire Jeedom » pour retirer les entités.'));
  });

  maybe('relecture réussie ou partielle : aucune invitation à relancer', () => {
    const ui = start();
    confirmExclusion(ui, 2);
    ui.respond('saveRoomExclusion', SAVE_OK([2]));
    ui.respond('scanTopology', { state: 'ok', result: { status: 'ok', operation_result: 'partiel', operation_message: 'Terminée avec avertissements.' } });
    assert.ok(!alertTexts(ui).some((t) => t.includes('Relancez')));
  });
});

describe('25.8 / AC11 — réservation et disponibilité', () => {
  maybe('pendant la confirmation, l\'écriture et la relecture : « Relire Jeedom » et l\'exclusion de toutes les pièces sont réservées, avec infobulle', () => {
    const ui = start();
    assert.equal(ui.isDisabled(ITEM(3)), false, 'actives hors opération');
    ui.click(ITEM(2));
    assert.equal(ui.isDisabled('#bt_rescanTopology'), true);
    assert.equal(ui.isDisabled(ITEM(2)), true);
    assert.equal(ui.isDisabled(ITEM(3)), true, 'les autres pièces aussi');
    assert.equal(plain(ui.$(ITEM(3)).attr('title')), 'Une opération est déjà en cours.');
    ui.lastConfirmation().options.buttons.confirm.callback();
    assert.equal(ui.isDisabled(ITEM(3)), true);
    ui.respond('saveRoomExclusion', SAVE_OK([2]));
    assert.equal(ui.isDisabled(ITEM(3)), true, 'pendant la relecture');
    ui.respond('scanTopology', SCAN_OK);
    assert.equal(ui.isDisabled(ITEM(3)), false, 'redevenue active à la fin');
    assert.equal(ui.$(ITEM(3)).attr('title'), undefined);
  });

  maybe('un second clic pendant l\'opération n\'ouvre rien et n\'écrit rien (pas de double envoi)', () => {
    const ui = start();
    ui.click(ITEM(2));
    const dialogs = ui.dom.dialogs.length;
    ui.dom.$(ITEM(3)).list[0].props.disabled = false; // même un bouton forcé actif ne passe pas : la réservation fait foi
    ui.click(ITEM(3));
    assert.equal(ui.dom.dialogs.length, dialogs, 'une seule confirmation à la fois');
    assert.equal(ui.count('saveRoomExclusion'), 0);
  });

  maybe('gating de la barre de santé (démon arrêté, MQTT déconnecté) : entrées grisées avec la raison existante', () => {
    const ui = start();
    ui.sandbox.window.jeedom2haLastBridgeStatus = { daemon: false };
    ui.sandbox.applyHAGating({ daemon: false });
    assert.equal(ui.isDisabled(ITEM(2)), true);
    assert.equal(plain(ui.$(ITEM(2)).attr('title')), 'Démon arrêté — actions Home Assistant bloquées.');
    ui.sandbox.applyHAGating({ daemon: true, broker: { state: 'disconnected' } });
    assert.equal(plain(ui.$(ITEM(2)).attr('title')), 'MQTT déconnecté — actions Home Assistant bloquées.');
    ui.bridgeUp();
    assert.equal(ui.isDisabled(ITEM(2)), false);
    assert.equal(ui.$(ITEM(2)).attr('title'), undefined);
  });
});

describe('25.8 / AC16 — idempotence côté interface', () => {
  maybe('rejouer sur une pièce déjà exclue : la route répond changed=false, la relecture est relancée quand même', () => {
    const ui = start({ scene: Object.assign({}, SCENE, { config: { excludedObjects: '2' } }), equipments: Object.assign({}, EQUIPMENTS, { 201: excludedEntry(201), 202: excludedEntry(202) }) });
    // la pièce est exclue : « Ne plus exclure » puis ré-exclure
    confirmExclusion(ui, 2);
    ui.respond('saveRoomExclusion', { state: 'ok', result: { object_id: 2, excluded: false, changed: true, excluded_objects: [] } });
    ui.respond('scanTopology', SCAN_OK);
    confirmExclusion(ui, 2);
    ui.respond('saveRoomExclusion', SAVE_OK([2]));
    ui.respond('scanTopology', SCAN_OK);
    // rejouer l'exclusion déjà posée côté serveur (autre onglet) : changed=false
    ui.page.setExcludedObjects([]);
    confirmExclusion(ui, 2);
    ui.respond('saveRoomExclusion', SAVE_OK([2], false));
    assert.equal(ui.pending('scanTopology').length, 1, 'la relecture est relancée même sans changement');
  });
});
