// ARTEFACT — Story 20.3, correctifs de revue R1 (A à F, G) : exécute le VRAI code de l'interface
// (jeedom2ha.js + jeedom2ha_mapping_surface.js) sur un faux DOM. Seuls le DOM, le réseau et bootbox
// sont factices : setHaActionPendingState, restoreHaActionPendingState, buildHaActionUserMessage,
// confirmHaSupprimerAction, applyHAGating, renderRoomCounters sont ceux de la
// production. Données d'exemple génériques uniquement.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { createUi, tree, ok, READY, EXCLUDED, DISABLED, BRIDGE_UP, view } = require('./helpers/ui_harness');

const ROOM = {
  object_id: 7,
  object_name: 'Pièce <b>"A"</b>',
  equipments: [
    { eq_id: 1, eq_name: 'Équipement <i>1</i>', enabled: true },
    { eq_id: 2, eq_name: 'Équipement 2', enabled: true },
  ],
};
const OTHER_ROOM = { object_id: 8, object_name: 'Pièce B', equipments: [{ eq_id: 3, eq_name: 'Équipement 3', enabled: true }] };
const NO_ROOM = { object_id: 0, object_name: 'Sans pièce', equipments: [{ eq_id: 9, eq_name: 'Équipement 9', enabled: true }] };
const UNSYNCED = { synced_should_publish: false, current_should_publish: true, override_pending: false, published_in_ha: false };
const NEVER_SYNCED = { synced_should_publish: null, current_should_publish: true, override_pending: false, published_in_ha: false };
// R2-1 : principal refusé mais secondaire publié => dans HA malgré `synced_should_publish` false.
const SECONDARY_PUBLISHED = { synced_should_publish: false, current_should_publish: false, override_pending: false, published_in_ha: true };
const OLD_DAEMON = { synced_should_publish: false, current_should_publish: true, override_pending: false };
const PENDING_ENTITY = [{ ha_entity_type: 'light', command_ids: [100], decision: null, override_pending: true }];

/** Ouvre la vue sur la pièce A (pont non encore signalé) : les arbres `trees` servent d'entrées agrégées (KPI, gating
 * de pièce) ; l'équipement 1 est sélectionné et son arbre lu, sauf `select: null` (détail de pièce). `trees` : corps
 * `ok(tree(...))` ou corps d'échec ; null = rien de chargé. */
function openRoomWith(trees, rooms, options) {
  const ui = createUi(rooms || [ROOM, OTHER_ROOM, NO_ROOM]);
  ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
  const o = options || {};
  if (!trees) {
    ui.openRoom(7);
    if (o.select !== null) ui.selectEquipment(o.select === undefined ? 1 : o.select);
    return ui;
  }
  ui.trees = {};
  const entries = {};
  trees.forEach((body, index) => {
    const payload = body && body.result && body.result.payload;
    const id = payload && payload.jeedom_eq_id != null ? payload.jeedom_eq_id : null;
    if (id !== null && body.state === 'ok' && id === index + 1) entries[String(id)] = payload;
  });
  ui.loadStates(entries);
  ui.openRoom(7);
  ui.treeBodies = trees;
  if (o.select !== null) ui.selectEquipment(o.select === undefined ? 1 : o.select, trees[(o.select === undefined ? 1 : o.select) - 1]);
  return ui;
}

/** Détail de la pièce A (aucun équipement sélectionné) avec ses boutons de pièce gatés (état des entrées, puis pont). */
function openRoomLevel(trees) {
  const ui = openRoomWith(trees, null, { select: null });
  ui.page.render();
  ui.bridgeUp();
  return ui;
}

/** Revient au détail de la pièce ; les boutons de pièce suivent ensuite le gating habituel : état des entrées agrégées
 * (rendu suivant de la page B, `refreshRoomGating`) puis état du pont (`applyHAGating`). */
function showRoom(ui) {
  ui.showRoom();
  ui.page.render();
  ui.bridgeUp();
}

/** Affiche l'équipement `eqId` (un seul détail à la fois) avec le corps déjà fourni à `openRoomWith`. */
function showEq(ui, eqId) {
  ui.selectEquipment(eqId, ui.treeBodies[eqId - 1]);
}

const ACTION_OK = { state: 'ok', result: { payload: { resultat: 'succes', message: 'Fait.', perimetre_impacte: { nom: 'Périmètre X' } } } };

describe('R1-A — publication ciblée d’un équipement toujours présente (AC4, Q2=A ; 25.1 AC11, AC12)', () => {
  it('équipement publié sans réglage en attente : « Republier » dans le menu « ⋯ », ni « Appliquer » visible', () => {
    const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    const buttons = ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-republish');
    assert.equal(buttons.length, 1);
    assert.equal(buttons.text(), '{{Republier}}');
    assert.equal(buttons.closest('.j2ha-menu-wrap').length, 1, 'dans le menu « ⋯ », plus un bouton de premier niveau');
    assert.equal(buttons.prop('disabled'), false);
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-apply').length, 0, '« Appliquer » absent du DOM');
  });

  it('réglage en attente : « Appliquer » apparaît (un seul), « Republier » reste dans le menu', () => {
    const ui = openRoomWith([ok(tree(1, [READY], { entities: PENDING_ENTITY })), ok(tree(2, [READY]))]);
    const buttons = ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-apply');
    assert.equal(buttons.length, 1);
    assert.equal(buttons.text(), '{{Appliquer}}');
    assert.equal(buttons.prop('disabled'), false);
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-republish').length, 1);
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="2"] .j2ha-eq-apply').length, 0);
  });

  it('même route executeHaAction publier/equipement et même rechargement, par « Appliquer » comme par « Republier »', () => {
    for (const [entities, selector] of [[[], '.j2ha-eq-republish'], [PENDING_ENTITY, '.j2ha-eq-apply']]) {
      const ui = openRoomWith([ok(tree(1, [READY], { entities })), ok(tree(2, [READY]))]);
      ui.click('.j2ha-eq-panel[data-eq-id="1"] ' + selector);
      const call = ui.pending('executeHaAction')[0];
      assert.deepEqual(
        [call.data.intention, call.data.portee, call.data.selection],
        ['publier', 'equipement', JSON.stringify([1])]
      );
      ui.respond('executeHaAction', { state: 'ok', result: null });
      assert.equal(ui.pending('getMappingOverrides').length, 1, 'l’arbre de l’équipement est relu');
      assert.equal(ui.pending('getMappingOverrides')[0].data.eqId, 1);
    }
  });
});

describe('R1-B — gating d’état des actions par équipement', () => {
  it('« Supprimer de Home Assistant » grisé avec infobulle si l’équipement n’est pas publié dans HA (non synchronisé ou jamais synchronisé)', () => {
    for (const sync of [UNSYNCED, NEVER_SYNCED]) {
      const ui = openRoomWith([ok(tree(1, [READY], { sync })), ok(tree(2, [READY]))]);
      const unpublished = ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate');
      assert.equal(unpublished.prop('disabled'), true);
      assert.match(unpublished.attr('title'), /non publié/);
      showEq(ui, 2); // un seul détail à la fois (vue C)
      const published = ui.$('.j2ha-eq-panel[data-eq-id="2"] .j2ha-eq-recreate');
      assert.equal(published.prop('disabled'), false, 'un équipement publié garde l’action');
    }
  });

  it('R2-1 — principal refusé mais secondaire publié (published_in_ha) : « Supprimer de Home Assistant » reste actif, équipement et pièce', () => {
    const ui = openRoomWith([ok(tree(1, [READY], { sync: SECONDARY_PUBLISHED })), ok(tree(2, [READY], { sync: UNSYNCED }))]);
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate').prop('disabled'), false);
    showEq(ui, 2);
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="2"] .j2ha-eq-recreate').prop('disabled'), true);
    showRoom(ui);
    assert.equal(ui.$('.j2ha-room-recreate').prop('disabled'), false);
  });

  it('R2-1 — champ absent (démon plus ancien) : « Supprimer de Home Assistant » reste actif', () => {
    const ui = openRoomWith([ok(tree(1, [READY], { sync: OLD_DAEMON })), ok(tree(2, [READY], { sync: OLD_DAEMON }))]);
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate').prop('disabled'), false);
    showRoom(ui);
    assert.equal(ui.$('.j2ha-room-recreate').prop('disabled'), false);
  });

  it('« Republier » grisé pour un équipement désactivé ou exclu, actif sinon', () => {
    const ui = openRoomWith([ok(tree(1, [DISABLED])), ok(tree(2, [EXCLUDED]))]);
    for (const id of [1, 2]) {
      if (id === 2) showEq(ui, 2);
      const button = ui.$(`.j2ha-eq-panel[data-eq-id="${id}"] .j2ha-eq-republish`);
      assert.equal(button.prop('disabled'), true, 'équipement ' + id);
      assert.ok(button.attr('title'));
    }
    const active = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    assert.equal(active.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-republish').prop('disabled'), false);
  });

  it('un réglage en attente reste applicable même sur un équipement exclu (R1 avant R4)', () => {
    const ui = openRoomWith([ok(tree(1, [EXCLUDED], { entities: PENDING_ENTITY })), ok(tree(2, [READY]))]);
    const button = ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-apply');
    assert.equal(button.text(), '{{Appliquer}}');
    assert.equal(button.prop('disabled'), false);
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-republish').prop('disabled'), false);
  });

  it('l’état de l’arbre n’est pas réactivé par un nouveau statut de pont disponible', () => {
    const ui = openRoomWith([ok(tree(1, [READY], { sync: UNSYNCED })), ok(tree(2, [READY]))]);
    ui.bridgeUp();
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate').prop('disabled'), true);
    showEq(ui, 2);
    ui.bridgeUp();
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="2"] .j2ha-eq-recreate').prop('disabled'), false);
  });

  it('pont indisponible : toutes les actions sont grisées', () => {
    const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    ui.sandbox.applyHAGating({ daemon: false });
    for (const sel of ['.j2ha-eq-republish', '.j2ha-eq-recreate']) {
      assert.ok(ui.$(sel).length > 0, sel);
      ui.$(sel).list.forEach((b) => assert.equal(b.props.disabled, true, sel));
    }
    showRoom(ui);
    ui.sandbox.applyHAGating({ daemon: false });
    for (const sel of ['.j2ha-room-republish', '.j2ha-room-recreate']) {
      assert.ok(ui.$(sel).length > 0, sel);
      ui.$(sel).list.forEach((b) => assert.equal(b.props.disabled, true, sel));
    }
  });
});

describe('R1-B — gating d’état des actions de pièce', () => {
  // Vue C : le gating de pièce est lu dans les entrées AGRÉGÉES de la pièce (copie de la page B), sans lecture d'arbre ;
  // un équipement absent de la copie (« non lu ») équivaut à l'ancienne lecture encore attendue ou en échec.
  const UNREAD = { state: 'error', result: 'non lu' };

  it('R2-3 — états pas encore lus : les actions de pièce restent actives (le démon ignore les équipements sans objet)', () => {
    const ui = openRoomWith(null, null, { select: null });
    showRoom(ui);
    for (const sel of ['.j2ha-room-republish', '.j2ha-room-recreate']) {
      assert.equal(ui.$(sel).prop('disabled'), false, sel);
      assert.equal(ui.$(sel).attr('title'), undefined, sel);
    }
    const partial = openRoomWith([ok(tree(1, [EXCLUDED])), UNREAD], null, { select: null });
    showRoom(partial);
    assert.equal(partial.$('.j2ha-room-republish').prop('disabled'), false, 'lecture encore incomplète');
    assert.equal(partial.count('getMappingOverrides'), 0, 'aucune lecture d’arbre pour le gating de pièce');
  });

  it('R2-3 — un équipement non lu ne conclut jamais à « rien à faire » : boutons actifs, sans infobulle « aucun équipement »', () => {
    const ui = openRoomWith([ok(tree(1, [EXCLUDED], { sync: UNSYNCED })), UNREAD], null, { select: null });
    showRoom(ui);
    for (const sel of ['.j2ha-room-republish', '.j2ha-room-recreate']) {
      assert.equal(ui.$(sel).prop('disabled'), false, sel);
      assert.equal(ui.$(sel).attr('title'), undefined, sel);
    }
  });

  it('« Republier la pièce » actif dès qu’un équipement est à publier ; « Supprimer… la pièce » dès qu’un est publié', () => {
    const ui = openRoomWith([ok(tree(1, [READY], { sync: UNSYNCED })), UNREAD], null, { select: null });
    showRoom(ui);
    assert.equal(ui.$('.j2ha-room-republish').prop('disabled'), false);
    assert.equal(ui.$('.j2ha-room-recreate').prop('disabled'), false, 'lecture encore incomplète');
    const full = openRoomWith([ok(tree(1, [READY], { sync: UNSYNCED })), ok(tree(2, [READY], { sync: UNSYNCED }))], null, { select: null });
    showRoom(full);
    assert.equal(full.$('.j2ha-room-recreate').prop('disabled'), true, 'tout lu, aucun publié');
    assert.match(full.$('.j2ha-room-recreate').attr('title'), /Aucun équipement publié/);
  });

  it('tous les équipements lus : aucun équipement à publier => « Republier la pièce » grisé', () => {
    const ui = openRoomWith([ok(tree(1, [EXCLUDED])), ok(tree(2, [DISABLED]))], null, { select: null });
    showRoom(ui);
    assert.equal(ui.$('.j2ha-room-republish').prop('disabled'), true);
    assert.match(ui.$('.j2ha-room-republish').attr('title'), /Aucun équipement à publier/);
  });

  it('tous les équipements lus : aucun équipement publié => « Supprimer la pièce de Home Assistant » grisé', () => {
    const ui = openRoomWith([ok(tree(1, [READY], { sync: UNSYNCED })), ok(tree(2, [READY], { sync: NEVER_SYNCED }))], null, { select: null });
    showRoom(ui);
    assert.equal(ui.$('.j2ha-room-recreate').prop('disabled'), true);
    assert.match(ui.$('.j2ha-room-recreate').attr('title'), /Aucun équipement publié/);
    assert.equal(ui.$('.j2ha-room-republish').prop('disabled'), false);
  });

  it('« Sans pièce » : aucune action de pièce, les actions par équipement restent', () => {
    const ui = createUi([NO_ROOM]);
    ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
    ui.openRoom(0);
    assert.equal(ui.$('.j2ha-room-republish').length + ui.$('.j2ha-room-recreate').length, 0);
    ui.selectEquipment(9, ok(tree(9, [READY])));
    assert.equal(ui.$('.j2ha-room-republish').length + ui.$('.j2ha-room-recreate').length, 0);
    assert.equal(ui.$('.j2ha-eq-recreate').length, 1);
  });
});

describe('R1-B/E — arbre en erreur : aucune action, jamais [null]', () => {
  const FAILURES = {
    'relais en erreur (state error)': { state: 'error', result: 'Le démon ne répond pas' },
    '404 démon (corps sans jeedom_eq_id)': { state: 'ok', result: { status: 'error', message: 'Équipement inconnu' } },
    'jeedom_eq_id absent': ok({ eq_name: 'X', entities: [], commands: [] }),
    'jeedom_eq_id d’un autre équipement': ok(tree(99, [READY])),
  };
  for (const [label, body] of Object.entries(FAILURES)) {
    it(label, () => {
      const ui = openRoomWith([body, ok(tree(2, [READY]))]);
      const panel = '.j2ha-eq-panel[data-eq-id="1"] ';
      assert.equal(ui.$(panel + '.j2ha-eq-republish').length, 0);
      assert.equal(ui.$(panel + '.j2ha-eq-recreate').length, 0);
      assert.match(ui.$(panel + '.j2ha-eq-status').text(), /Impossible/);
      assert.equal(ui.pending('executeHaAction').length, 0);
    });
  }

  it('échec réseau (démon indisponible) : même résultat', () => {
    const ui = openRoomWith(null);
    ui.fail('getMappingOverrides');
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate').length, 0);
    assert.match(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-status').text(), /démon indisponible/);
  });

  it('une pièce dont l’identifiant n’est pas un nombre n’est jamais lue ni adressée (pas de [null])', () => {
    const bad = createUi([{ object_id: 'x', object_name: 'Z', equipments: [{ eq_id: 5, eq_name: 'E', enabled: true }] }]);
    bad.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
    bad.openRoom('x');
    assert.equal(bad.pending('getMappingOverrides').length, 0, 'pièce inconnue : rien n’est lu');
    assert.equal(bad.pending('executeHaAction').length, 0);
  });
});

describe('R1-C — action en cours : réservation du bouton (applyHAGating, double clic)', () => {
  it('applyHAGating ne réactive pas un bouton dont l’action est en cours', () => {
    const ui = openRoomLevel([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    ui.click('.j2ha-room-republish');
    ui.lastConfirmation().options.buttons.confirm.callback();
    const button = ui.$('.j2ha-room-republish');
    assert.equal(button.attr('data-ha-pending'), '1');
    ui.bridgeUp(); // ex. un getBridgeStatus qui revient pendant l'action
    assert.equal(button.prop('disabled'), true, 'toujours grisé pendant l’action');
    assert.match(button.html(), /fa-spin/);
    ui.respond('executeHaAction', ACTION_OK);
    assert.equal(button.attr('data-ha-pending'), undefined);
    assert.equal(button.prop('disabled'), false, 'réactivé à la fin, état du pont');
  });

  it('le bouton est réservé dès l’ouverture de la confirmation : un second clic n’ouvre pas une seconde boîte', () => {
    const ui = openRoomLevel([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    ui.click('.j2ha-room-recreate');
    const button = ui.$('.j2ha-room-recreate');
    assert.equal(button.attr('data-ha-pending'), '1');
    assert.equal(button.prop('disabled'), true);
    ui.click('.j2ha-room-recreate');
    assert.equal(ui.dom.dialogs.filter((d) => d.options.buttons).length, 1);
  });

  it('annuler la confirmation libère le bouton (libellé et état d’origine) ; Échap/fermeture aussi', () => {
    const ui = openRoomLevel([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    const before = ui.$('.j2ha-room-republish').html();
    ui.click('.j2ha-room-republish');
    ui.lastConfirmation().options.buttons.cancel.callback();
    const button = ui.$('.j2ha-room-republish');
    assert.equal(button.attr('data-ha-pending'), undefined);
    assert.equal(button.prop('disabled'), false);
    assert.equal(button.html(), before);
    assert.equal(ui.pending('executeHaAction').length, 0, 'aucune écriture');

    ui.click('.j2ha-room-republish');
    ui.lastConfirmation().close();
    assert.equal(ui.$('.j2ha-room-republish').prop('disabled'), false);
  });

  it('un équipement : même réservation (supprimer de Home Assistant) et libération à l’annulation', () => {
    const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    ui.click('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate');
    const button = ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate');
    assert.equal(button.attr('data-ha-pending'), '1');
    ui.lastConfirmation().options.buttons.cancel.callback();
    assert.equal(button.prop('disabled'), false);
  });

  it('un bouton grisé par l’état de l’arbre le reste après une annulation', () => {
    const ui = openRoomWith([ok(tree(1, [READY], { sync: UNSYNCED })), ok(tree(2, [READY]))]);
    const button = ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate');
    ui.click('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate');
    assert.equal(ui.dom.dialogs.filter((d) => d.options.buttons).length, 0, 'bouton grisé : aucune confirmation');
    assert.equal(button.prop('disabled'), true);
  });

  it('boutons globaux : réservés à l’ouverture de la confirmation, libérés à l’annulation', () => {
    const ui = openRoomWith(null);
    ui.click('.j2ha-ha-action[data-ha-action="republier"]');
    const button = ui.$('.j2ha-ha-action[data-ha-action="republier"]');
    assert.equal(button.attr('data-ha-pending'), '1');
    ui.click('.j2ha-ha-action[data-ha-action="republier"]');
    assert.equal(ui.dom.dialogs.filter((d) => d.options.buttons).length, 1, 'une seule boîte');
    ui.lastConfirmation().options.buttons.cancel.callback();
    assert.equal(button.attr('data-ha-pending'), undefined);
    assert.equal(button.prop('disabled'), false);
  });

  it('rescan en cours : applyHAGating grise tout sauf ce qui est déjà en cours, sans l’exclure du gating', () => {
    const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    ui.sandbox.window.jeedom2haRescanInProgress = true;
    ui.sandbox.applyHAGating(BRIDGE_UP);
    assert.equal(ui.$('.j2ha-eq-recreate').first().prop('disabled'), true);
    ui.showRoom();
    ui.sandbox.applyHAGating(BRIDGE_UP);
    assert.equal(ui.$('.j2ha-room-republish').prop('disabled'), true);
    ui.sandbox.window.jeedom2haRescanInProgress = false;
    ui.sandbox.applyHAGating(BRIDGE_UP);
    assert.equal(ui.$('.j2ha-room-republish').prop('disabled'), false);
  });
});

describe('R1-D — retour d’une action de pièce (pièce capturée au lancement)', () => {
  function launchRoomRepublish() {
    const ui = openRoomLevel([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    ui.click('.j2ha-room-republish');
    ui.lastConfirmation().options.buttons.confirm.callback();
    return ui;
  }

  it('détail de la pièce toujours affiché : résultat dans le détail, aucune lecture d’arbre (les états suivent la page B)', () => {
    const ui = launchRoomRepublish();
    ui.respond('executeHaAction', ACTION_OK);
    assert.match(ui.$('.j2ha-wv .j2ha-room-feedback').text(), /Périmètre X — Fait\./);
    assert.equal(ui.dom.alerts.length, 0);
    assert.equal(ui.pending('getMappingOverrides').length, 0, 'aucun équipement sélectionné : rien à relire');
  });

  it('un équipement de la pièce sélectionné pendant l’action : au retour, son arbre — et lui seul — est relu (D2)', () => {
    const ui = launchRoomRepublish();
    ui.selectEquipment(1, ok(tree(1, [READY])));
    ui.respond('executeHaAction', ACTION_OK);
    assert.match(ui.$('.j2ha-wv .j2ha-room-feedback').text(), /Périmètre X — Fait\./, 'la pièce est toujours affichée');
    assert.deepEqual(ui.pending('getMappingOverrides').map((c) => c.data.eqId), [1]);
  });

  it('vue refermée avant le retour : résultat dans la zone d’alerte de la page, aucun rechargement', () => {
    const ui = launchRoomRepublish();
    ui.click('.j2ha-wv-back');
    ui.respond('executeHaAction', ACTION_OK);
    assert.equal(ui.dom.alerts.length, 1);
    assert.equal(ui.dom.alerts[0].level, 'success');
    assert.match(ui.dom.alerts[0].message, /Périmètre X — Fait\./);
    assert.equal(ui.pending('getMappingOverrides').length, 0);
  });

  it('une autre pièce affichée au retour : alerte de page, rien dans le détail de l’autre pièce, aucune relecture', () => {
    const ui = launchRoomRepublish();
    ui.openRoom(8);
    ui.selectEquipment(3, ok(tree(3, [READY])));
    ui.respond('executeHaAction', ACTION_OK);
    assert.equal(ui.dom.alerts.length, 1);
    assert.equal(ui.$('.j2ha-wv .j2ha-room-feedback').text(), '', 'rien dans le détail de l’autre pièce');
    assert.equal(ui.pending('getMappingOverrides').length, 0, 'ni la pièce A ni la pièce B ne sont relues');
  });

  it('erreur à l’appel : message en danger au bon endroit et bouton libéré', () => {
    const ui = launchRoomRepublish();
    ui.fail('executeHaAction');
    assert.match(ui.$('.j2ha-wv .j2ha-room-feedback').text(), /Erreur de communication/);
    assert.equal(ui.$('.j2ha-room-republish').prop('disabled'), false);
    assert.equal(ui.pending('getMappingOverrides').length, 0, 'un échec ne recharge rien');
  });

  it('résultat d’échec du démon : aucun rechargement ; message en danger dans le détail', () => {
    const ui = launchRoomRepublish();
    ui.respond('executeHaAction', { state: 'ok', result: { payload: { resultat: 'echec', message: 'Refusé' } } });
    assert.equal(ui.pending('getMappingOverrides').length, 0);
    assert.match(ui.$('.j2ha-room-feedback').text(), /Refusé/);
    assert.ok(ui.$('.j2ha-room-feedback .alert-danger').length === 1);
  });
});

describe('R1-E — KPI de pièce (entrées agrégées) et détail d’équipement : lecture en échec, état périmé purgé', () => {
  const UNREAD = { state: 'error', result: 'non lu' };

  it('états pas encore lus : aucun KPI, aucune lecture d’arbre', () => {
    const ui = openRoomWith(null, null, { select: null });
    assert.equal(ui.$('.j2ha-wv-kpis .j2ha-room-counter').length, 0);
    assert.equal(ui.pending('getMappingOverrides').length, 0);
  });

  it('équipement non lu : KPI avec le nombre d’équipements non lus, jamais « Chargement des compteurs… » sans fin', () => {
    const ui = openRoomWith([ok(tree(1, [READY, READY])), UNREAD], null, { select: null });
    const text = ui.$('.j2ha-wv-kpis').text();
    assert.match(text, /1 publié/);
    assert.doesNotMatch(text, /commande/, 'plus de compteur de commandes au niveau de la pièce (Q4)');
    assert.match(text, /1 équipement non lu/);
    assert.doesNotMatch(text, /Chargement/);
  });

  it('une lecture d’arbre en échec : détail vidé (plus d’action sur un arbre périmé), KPI inchangés (copie de la page B)', () => {
    const ui = openRoomWith([ok(tree(1, [READY, READY])), ok(tree(2, [READY]))]);
    ui.click('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-republish');
    ui.respond('executeHaAction', { state: 'ok', result: null });
    ui.fail('getMappingOverrides'); // la relecture de l'équipement 1 échoue
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate').length, 0, 'plus d’action sur un arbre périmé');
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-counter').length, 0, 'ni de compteur périmé');
    ui.showRoom();
    assert.match(ui.$('.j2ha-wv-kpis').text(), /2 publiés/, 'les KPI viennent des états, pas de l’arbre unitaire');
  });

  it('une réponse tardive d’un équipement abandonné ne touche pas la pièce affichée', () => {
    const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]); // lecture de 1 déjà répondue
    ui.selectEquipment(1); // relecture de 1 en attente
    ui.openRoom(8);
    ui.respond('getMappingOverrides', ok(tree(1, [READY])));
    assert.equal(ui.$('.j2ha-eq-panel').length, 0);
    assert.match(ui.$('.j2ha-wv-title').text(), /Pièce B/);
  });
});

describe('R1-F/G — confirmation forte (couverture 5.2/5.3) et état d’attente', () => {
  it('« Supprimer de Home Assistant… » (équipement et pièce) : rouge dans le menu seulement, jamais un bouton rouge plein', () => {
    const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    assert.ok(ui.$('.j2ha-eq-recreate').length > 0);
    ui.$('.j2ha-eq-recreate').list.forEach((b) => assert.ok(b.classes.has('j2ha-menu-danger')));
    assert.equal(ui.$('.j2ha-wv .btn-danger').length, 0, 'aucun bouton rouge plein avant la confirmation (équipement)');
    ui.showRoom();
    assert.ok(ui.$('.j2ha-room-recreate').hasClass('j2ha-menu-danger'));
    assert.equal(ui.$('.j2ha-room-recreate').text(), '{{Supprimer de Home Assistant…}}');
    assert.equal(ui.$('.j2ha-room-recreate').closest('.j2ha-menu-wrap').length, 1);
    assert.equal(ui.$('.j2ha-wv .btn-danger').length, 0, 'aucun bouton rouge plein avant la confirmation (pièce)');
  });

  it('la confirmation de suppression a un bouton rouge, un bouton Annuler et la mise en garde forte', () => {
    const ui = openRoomLevel([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    ui.click('.j2ha-room-recreate');
    const { options } = ui.lastConfirmation();
    assert.equal(options.buttons.confirm.className, 'btn-danger');
    assert.equal(options.buttons.cancel.className, 'btn-default');
    for (const word of ['Attention', 'historique', 'dashboards', 'automatisations', 'entity_id']) {
      assert.ok(options.message.includes(word), word);
    }
  });

  it('la confirmation de republication garde le bouton principal (pas rouge)', () => {
    const ui = openRoomLevel([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    ui.click('.j2ha-room-republish');
    assert.equal(ui.lastConfirmation().options.buttons.confirm.className, 'btn-primary');
  });

  it('boutons globaux : suppression en rouge, mise en garde forte, sans nombre', () => {
    const ui = openRoomWith(null);
    ui.click('.j2ha-ha-action[data-ha-action="supprimer-recreer"]');
    const { options } = ui.lastConfirmation();
    assert.equal(options.buttons.confirm.className, 'btn-danger');
    assert.match(options.message, /Supprimer de Home Assistant tout le parc publié \?/);
    assert.doesNotMatch(options.message, /\d/);
    options.buttons.confirm.callback();
    const call = ui.pending('executeHaAction')[0];
    assert.deepEqual([call.data.intention, call.data.portee, call.data.selection], ['supprimer', 'global', '["all"]']);
  });

  it('noms échappés dans la confirmation de pièce et d’équipement ; routes et périmètre corrects', () => {
    const ui = openRoomWith([ok(tree(1, [READY], { name: 'Équipement <i>1</i>' })), ok(tree(2, [READY]))], null, { select: null });
    ui.page.render();
    ui.bridgeUp();
    ui.click('.j2ha-room-republish');
    assert.match(ui.lastConfirmation().options.message, /Pièce &lt;b&gt;/);
    assert.doesNotMatch(ui.lastConfirmation().options.message, /<b>/);
    ui.lastConfirmation().options.buttons.cancel.callback();

    ui.click('.j2ha-room-recreate');
    ui.lastConfirmation().options.buttons.confirm.callback();
    assert.deepEqual(
      [ui.pending('executeHaAction')[0].data.intention, ui.pending('executeHaAction')[0].data.portee, ui.pending('executeHaAction')[0].data.selection],
      ['supprimer', 'piece', JSON.stringify([7])]
    );
    ui.respond('executeHaAction', ACTION_OK);

    showEq(ui, 1);
    ui.click('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate');
    assert.match(ui.lastConfirmation().options.message, /Équipement &lt;i&gt;1&lt;\/i&gt;/);
    assert.match(ui.lastConfirmation().options.buttons.confirm.label, /Supprimer 1 équipement/);
    ui.lastConfirmation().options.buttons.confirm.callback();
    const call = ui.pending('executeHaAction')[0];
    assert.deepEqual([call.data.intention, call.data.portee, call.data.selection], ['supprimer', 'equipement', JSON.stringify([1])]);
  });

  it('message de retour : périmètre affecté devant le message du démon', () => {
    const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    assert.equal(ui.sandbox.buildHaActionUserMessage({ message: 'Fait.', perimetre_impacte: { nom: 'Périmètre X' } }), 'Périmètre X — Fait.');
    assert.equal(ui.sandbox.buildHaActionUserMessage({ message: 'Fait.' }), 'Fait.');
    assert.equal(ui.sandbox.buildHaActionUserMessage({}), '{{Action Home Assistant exécutée.}}');
    assert.equal(ui.sandbox.buildHaActionUserMessage(null), '{{Action Home Assistant exécutée.}}');
  });

  it('état d’attente : libellé animé pendant l’action, état d’origine restauré ensuite', () => {
    const ui = openRoomLevel([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    const button = ui.$('.j2ha-room-recreate');
    const before = button.html();
    ui.click('.j2ha-room-recreate');
    assert.match(button.html(), /Confirmation en cours/);
    ui.lastConfirmation().options.buttons.confirm.callback();
    assert.match(button.html(), /fa-spin/);
    assert.match(button.html(), /Suppression\.\.\./);
    ui.respond('executeHaAction', ACTION_OK);
    assert.equal(button.html(), before);
  });

  it('setHaActionPendingState / restoreHaActionPendingState : snapshot, marqueur d’attente, bouton grisé par l’arbre conservé', () => {
    const ui = openRoomWith(null);
    const $button = ui.$('.j2ha-ha-action[data-ha-action="republier"]');
    const snapshot = ui.sandbox.setHaActionPendingState($button, 'Attente');
    assert.equal($button.attr('data-ha-pending'), '1');
    assert.equal($button.prop('disabled'), true);
    ui.sandbox.restoreHaActionPendingState($button, snapshot);
    assert.equal($button.attr('data-ha-pending'), undefined);
    // Un bouton grisé par l'état de l'arbre le reste, même avec un snapshot « actif ».
    $button.attr('data-ha-state-blocked', '1');
    ui.sandbox.restoreHaActionPendingState($button, { html: 'x', disabled: false });
    assert.equal($button.prop('disabled'), true);
  });
});

describe('G — rendu du détail de pièce et d’équipement de la vue C (ex-fenêtre de pièce)', () => {
  it('structure du détail de pièce : réassurance, KPI, actions, zone de retour, « À traiter » ; un seul détail d’équipement à la fois', () => {
    const ui = openRoomWith(null, null, { select: null });
    assert.equal(ui.$('.j2ha-wv #j2haSurface_reassurance').length, 1);
    assert.equal(ui.$('.j2ha-wv-kpis').length, 1);
    assert.equal(ui.$('.j2ha-room-actions').length, 1);
    assert.equal(ui.$('.j2ha-wv .j2ha-room-feedback').length, 1);
    assert.equal(ui.$('.j2ha-wv-todo').length, 1);
    assert.equal(ui.dom.dialogs.filter((d) => !d.options.buttons).length, 0, 'plus de fenêtre de pièce');
    assert.equal(ui.$('.j2ha-room-surface, .j2ha-eq-accordion').length, 0, 'plus d’accordéon');
    assert.deepEqual(ui.$('.j2ha-wv-eq').list.map((p) => p.attrs['data-eq-id']), ['1', '2'], 'équipements de la pièce, dans l’ordre, dans l’arbre');
    assert.equal(ui.$('.j2ha-eq-panel').length, 0, 'aucun détail d’équipement sans sélection (aucune lecture)');
  });

  it('nom d’équipement et de pièce rendus en texte (jamais en HTML) ; équipement désactivé marqué', () => {
    const ui = createUi([{ object_id: 7, object_name: 'Pièce <b>x</b>', equipments: [{ eq_id: 1, eq_name: '<i>Nom</i>', enabled: false }] }]);
    ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
    ui.openRoom(7);
    assert.equal(ui.$('.j2ha-wv-title .j2ha-free-name').text(), 'Pièce <b>x</b>');
    assert.equal(ui.$('.j2ha-wv-title b').length, 0);
    ui.selectEquipment(1, ok(tree(1, [READY])));
    assert.equal(ui.$('.j2ha-eq-name').text(), '<i>Nom</i>');
    assert.equal(ui.$('.j2ha-eq-name i').length, 0);
    assert.ok(ui.$('.j2ha-eq-panel').hasClass('j2ha-eq-disabled'));
    assert.match(ui.$('.j2ha-eq-panel').text(), /désactivé dans Jeedom/);
  });

  it('KPI de pièce : un chiffre et un mot par état non nul, issus du dénombrement des entrées agrégées', () => {
    const ui = openRoomWith([ok(tree(1, [READY, READY])), ok(tree(2, [EXCLUDED], { present: false }))], null, { select: null });
    const labels = ui.$('.j2ha-room-counter').list.map((el) => ui.$(el).text().trim());
    assert.deepEqual(labels, ['1 publié', '1 exclu']);
  });
});

describe('R2-2 / R2-4 — retour d’une action hors du détail de la pièce et par équipement', () => {
  const NAMED = { state: 'ok', result: { payload: { resultat: 'succes', message: 'Fait.', perimetre_impacte: { nom: '<img src=x onerror=1>' } } } };

  it('R2-2 — le message est échappé avant la zone d’alerte de la page (rendu HTML par le cœur)', () => {
    const ui = openRoomLevel([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    ui.click('.j2ha-room-republish');
    ui.lastConfirmation().options.buttons.confirm.callback();
    ui.click('.j2ha-wv-back'); // la pièce n'est plus affichée : zone d'alerte de la page
    ui.respond('executeHaAction', NAMED);
    assert.equal(ui.dom.alerts.length, 1);
    assert.doesNotMatch(ui.dom.alerts[0].message, /<img/);
    assert.match(ui.dom.alerts[0].message, /&lt;img/);
  });

  it('R2-4 — « Republier » d’un équipement : échec du démon affiché en danger, aucun rechargement', () => {
    const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    ui.click('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-republish');
    ui.respond('executeHaAction', { state: 'ok', result: { payload: { resultat: 'echec', message: 'Refusé' } } });
    assert.match(ui.$('.j2ha-room-feedback .alert-danger').text(), /Refusé/);
    assert.equal(ui.pending('getMappingOverrides').length, 0);
  });

  it('R2-4 — succès partiel : avertissement, équipement relu et bandeau de santé rafraîchi', () => {
    const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    ui.click('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-republish');
    ui.respond('executeHaAction', { state: 'ok', result: { payload: { resultat: 'succes_partiel', message: 'Partiel' } } });
    assert.ok(ui.$('.j2ha-room-feedback .alert-warning').length === 1);
    assert.equal(ui.pending('getMappingOverrides')[0].data.eqId, 1);
    assert.equal(ui.pending('getBridgeStatus').length, 1);
  });

  it('R2-4 — succès : message du périmètre dans le détail, relecture et bandeau', () => {
    const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    ui.click('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-republish');
    ui.respond('executeHaAction', ACTION_OK);
    assert.match(ui.$('.j2ha-room-feedback').text(), /Périmètre X — Fait\./);
    assert.equal(ui.pending('getMappingOverrides').length, 1);
    assert.equal(ui.pending('getBridgeStatus').length, 1);
  });
});

describe('R2-6 — libellés statiques de la vue (gate) : seuls les noms libres sont marqués', () => {
  it('groupes d’entités : libellés statiques (domaine traduit), noms de commande marqués comme libres', () => {
    const entities = [{ ha_entity_type: 'light', command_ids: [100, 101], decision: null, override_pending: false },
      { ha_entity_type: 'switch', command_ids: [], decision: null, override_pending: false }];
    const t = tree(1, [READY, READY, view('command_not_covered', false, false)], { entities });
    const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
    const heads = ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-group-head').list.map((el) => ui.$(el).find('.j2ha-group-name').text());
    assert.deepEqual(heads, ['Lumière light', 'Interrupteur switch']);
    const names = ui.$('.j2ha-eq-panel[data-eq-id="1"] .mo-td-name').list.map((el) => ui.$(el).text());
    assert.deepEqual(names, ['Commande 0', 'Commande 1']);
    // Les commandes ignorées sont repliées sous le tableau ; leur nom est un nom libre marqué.
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-ignored-list .j2ha-free-name').text(), 'Commande 2');
  });

  it('titre du détail de pièce : nom de pièce marqué, « Sans pièce » reste un libellé statique', () => {
    const ui = openRoomWith(null, null, { select: null });
    const name = ui.$('.j2ha-wv-title .j2ha-free-name');
    assert.equal(name.length, 1);
    // Le vrai jQuery rend le texte d'origine (entités décodées), jamais une balise : le nom reste du texte.
    assert.equal(name.text(), 'Pièce <b>"A"</b>', 'nom rendu comme texte, pas comme balise');
    assert.equal(name.find('b').length, 0);
    const noRoom = createUi([NO_ROOM]);
    noRoom.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
    noRoom.openRoom(0);
    assert.equal(noRoom.$('.j2ha-wv-title .j2ha-free-name').length, 0);
    assert.match(noRoom.$('.j2ha-wv-title').text(), /Sans pièce/);
  });
});
