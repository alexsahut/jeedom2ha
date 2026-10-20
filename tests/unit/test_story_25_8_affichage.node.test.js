// ARTEFACT — Story 25.8 (AC7, AC12, AC13) : affichage de l'exclusion de pièce. Détail de pièce : entrée « Exclure la pièce… » du menu
// « ⋯ » avant le séparateur, encart neutre « Pièce exclue » avec « Ne plus exclure la pièce… » ; « Sans pièce » n'a ni l'un ni l'autre.
// Carte et ligne d'arbre : « Pièce exclue » remplace seulement le ratio, jauge et repères conservés, « N pas encore retirés » tant que la
// copie des états montre des équipements non exclus. D1 : « Toujours » reste la position courante d'un équipement d'une pièce exclue,
// grisé avec l'infobulle « Pièce exclue : elle prime sur ce réglage. », sans modifier `publicationActionState`. Vrai code sur faux DOM.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const { startWorkview, openCard, openCardWide, phpAvailable } = require('./helpers/workview_harness');
const { plain } = require('./helpers/page_b_harness');

const maybe = phpAvailable ? it : it.skip;

const SCENE = {
  objects: [
    { id: 2, name: 'Pièce fictive A', father_id: null, display: {} },
    { id: 3, name: 'Pièce fictive B', father_id: null, display: {} },
  ],
  eqlogics: {
    2: [{ id: 201, name: 'Eq 201', type: 'plugin_alpha' }, { id: 202, name: 'Eq 202', type: 'plugin_alpha' }],
    3: [{ id: 301, name: 'Eq 301', type: 'plugin_alpha' }, { id: 302, name: 'Eq 302', type: 'plugin_alpha', enabled: false }],
    null: [{ id: 901, name: 'Eq sans pièce', type: 'plugin_alpha' }],
  },
  plugin_names: { plugin_alpha: 'Alpha' },
  config: { excludedObjects: '3' },
};
const diag = (reason, publish) => ({ confidence: null, ha_entity_type: null, publication_reason: reason, reason_code: null, should_publish: publish,
  projection_validity: { is_valid: publish, missing_capabilities: [], missing_fields: [], reason_code: publish ? null : reason } });
const published = (id) => ({
  jeedom_eq_id: id, equipment_decision: diag('sure_mapping', true),
  entities: [{ override_pending: false, present_in_ha: true }],
  commands: [{ jeedom_cmd_id: id * 10, covered: true, diagnostic: diag('sure_mapping', true), published_in_ha: true }],
  sync_status: { published_in_ha: true, synced_should_publish: true, current_should_publish: true, override_pending: false },
});
const excludedBy = (id, reason) => ({
  jeedom_eq_id: id, equipment_decision: diag(reason, false), entities: [],
  commands: [{ jeedom_cmd_id: id * 10, covered: false, diagnostic: diag(reason, false), published_in_ha: false }],
  sync_status: { published_in_ha: false, synced_should_publish: false, current_should_publish: false, override_pending: false },
});
const disabledEntry = (id) => Object.assign(excludedBy(id, 'disabled_eqlogic'), {});
const treeBody = (entry, extra) => ({ state: 'ok', result: { status: 'ok', payload: Object.assign({ eq_name: 'Eq', mapped: false, eligible: false }, entry, extra || {}) } });

// Pièce 3 exclue dans la configuration : 301 déjà retiré, 302 désactivé ; pièce 2 : deux équipements publiés.
const EQUIPMENTS = { 201: published(201), 202: published(202), 301: excludedBy(301, 'excluded_object'), 302: disabledEntry(302), 901: published(901) };
const start = (extra) => startWorkview(Object.assign({ scene: SCENE, equipments: EQUIPMENTS, pluginNames: { plugin_alpha: 'Alpha' } }, extra || {}));
const CARD = (id) => `#j2ha_roomCards .j2ha-room-card[data-object_id="${id}"]`;

describe('25.8 / AC7 — détail de pièce', () => {
  maybe('pièce non exclue : l\'entrée « Exclure la pièce… » précède le séparateur et « Supprimer de Home Assistant… »', () => {
    const ui = start();
    openCard(ui, 2);
    const items = ui.$('.j2ha-wv .j2ha-room-actions .j2ha-menu').children().list;
    assert.equal(items.length, 3, 'entrée, séparateur, suppression');
    assert.ok(ui.dom.wrap([items[0]]).find('.j2ha-room-exclude').length === 1, 'exclusion en premier');
    assert.equal(items[1].attrs.role, 'separator');
    assert.ok(ui.dom.wrap([items[2]]).find('.j2ha-room-recreate').length === 1, 'suppression en dernier');
    assert.equal(plain(ui.$('.j2ha-wv .j2ha-room-actions .j2ha-room-exclude').text()), 'Exclure la pièce…');
    assert.equal(ui.$('.j2ha-wv .j2ha-room-actions .j2ha-room-exclude').attr('data-ha-action'), 'exclure-piece');
    assert.equal(ui.$('.j2ha-wv .j2ha-wv-room-excluded').length, 0, 'pas d\'encart');
  });

  maybe('pièce exclue : entrée « Ne plus exclure la pièce… », encart neutre et bouton associé', () => {
    const ui = start();
    openCard(ui, 3);
    assert.equal(plain(ui.$('.j2ha-wv .j2ha-room-actions .j2ha-menu .j2ha-room-exclude').text()), 'Ne plus exclure la pièce…');
    const notice = ui.$('.j2ha-wv .j2ha-wv-room-excluded');
    assert.equal(notice.length, 1);
    assert.equal(notice.attr('role'), 'status');
    assert.ok(notice.hasClass('j2ha-notice') && notice.hasClass('j2ha-notice-neutral'));
    assert.equal(plain(notice.find('.j2ha-notice-text').text()).trim(), 'Pièce exclue : ses équipements ne sont pas publiés dans Home Assistant.');
    assert.equal(notice.find('.fa-eye-slash').length, 1);
    const button = notice.find('.j2ha-room-exclude');
    assert.equal(button.length, 1);
    assert.equal(plain(button.text()).trim(), 'Ne plus exclure la pièce…');
    assert.equal(button.attr('data-ha-action'), 'exclure-piece');
  });

  maybe('« Sans pièce » n\'a ni l\'entrée ni l\'encart', () => {
    const ui = start();
    openCard(ui, 0);
    assert.equal(ui.$('.j2ha-wv .j2ha-room-exclude').length, 0);
    assert.equal(ui.$('.j2ha-wv .j2ha-wv-room-excluded').length, 0);
  });

  maybe('l\'entrée du détail et le bouton de l\'encart ouvrent la confirmation ; Annuler rend le focus au déclencheur', () => {
    const ui = start();
    ui.bridgeUp();
    openCard(ui, 2);
    ui.click('.j2ha-wv .j2ha-room-actions .j2ha-room-exclude');
    const dlg = ui.lastConfirmation();
    assert.ok(plain(dlg.options.title).startsWith('Exclure la pièce « Pièce fictive A »'));
    assert.ok(plain(dlg.options.message).includes('2 entités seront retirées de Home Assistant.'));
    dlg.options.buttons.cancel.callback();
    dlg.close();
    assert.equal(ui.dom.focused, ui.$('.j2ha-wv .j2ha-room-actions .j2ha-menu-toggle').list[0], 'focus rendu au bouton « ⋯ » du détail');
    const excluded = start();
    excluded.bridgeUp();
    openCard(excluded, 3);
    excluded.click('.j2ha-wv .j2ha-wv-room-excluded .j2ha-room-exclude');
    const dlg2 = excluded.lastConfirmation();
    assert.ok(plain(dlg2.options.title).startsWith('Ne plus exclure la pièce « Pièce fictive B »'));
    dlg2.options.buttons.cancel.callback();
    dlg2.close();
    assert.equal(excluded.dom.focused, excluded.$('.j2ha-wv .j2ha-wv-room-excluded .j2ha-room-exclude').list[0], 'focus rendu au bouton de l\'encart');
  });

  maybe('après une écriture réussie, le détail de la pièce ouverte se met à jour (encart et libellé) sans rechargement', () => {
    const ui = start();
    ui.bridgeUp();
    openCard(ui, 2);
    ui.click('.j2ha-wv .j2ha-room-actions .j2ha-room-exclude');
    const dlg = ui.lastConfirmation();
    dlg.options.buttons.confirm.callback();
    dlg.close();
    ui.respond('saveRoomExclusion', { state: 'ok', result: { object_id: 2, excluded: true, changed: true, excluded_objects: [2, 3] } });
    assert.equal(ui.$('.j2ha-wv .j2ha-wv-room-excluded').length, 1, 'encart apparu');
    assert.equal(plain(ui.$('.j2ha-wv .j2ha-room-actions .j2ha-menu .j2ha-room-exclude').text()), 'Ne plus exclure la pièce…');
  });
});

describe('25.8 / AC12 — carte et ligne d\'arbre « Pièce exclue »', () => {
  maybe('la carte remplace le ratio par « Pièce exclue » (icône, mot visible), conserve jauge et repères ; le nom accessible commence par « Nom, pièce exclue »', () => {
    const ui = start();
    const card = ui.$(CARD(3));
    const line = card.find('.j2ha-room-excluded-line');
    assert.equal(line.length, 1);
    assert.equal(plain(line.text()).trim(), 'Pièce exclue');
    assert.equal(line.find('.fa-eye-slash').length, 1);
    assert.equal(card.find('.j2ha-room-ratio').length, 1, 'une seule ligne de ratio : elle est remplacée');
    assert.ok(!/ \/ /.test(plain(card.find('.j2ha-room-ratio').text())), 'plus de « n / t publiés »');
    assert.equal(card.find('.j2ha-gauge-card').length, 1, 'jauge conservée');
    assert.ok(plain(card.find('.j2ha-room-marks').text()).includes('1 exclu'), 'repère « N exclus » conservé');
    assert.ok(plain(card.attr('aria-label')).startsWith('Pièce fictive B, pièce exclue'));
    assert.ok(card.hasClass('j2ha-room-excluded'));
    assert.equal(plain(ui.$(CARD(2)).find('.j2ha-room-ratio').text()), '2 / 2 publiés', 'une pièce non exclue garde son ratio');
  });

  maybe('« N pas encore retirés » tant que la copie des états montre des équipements non exclus ; disparaît à la relecture', () => {
    const ui = start({ equipments: Object.assign({}, EQUIPMENTS, { 301: published(301) }) });
    assert.equal(plain(ui.$(`${CARD(3)} .j2ha-room-notyet`).text()).trim(), '· 1 pas encore retiré');
    ui.page.reader.load();
    ui.respond('getEquipmentStates', { state: 'ok', result: { status: 'ok', payload: { schema_version: 1, available: true, meta: { action_in_progress: false }, equipments: EQUIPMENTS, unread: [] } } });
    assert.equal(ui.$(`${CARD(3)} .j2ha-room-notyet`).length, 0, 'plus aucun équipement à retirer');
    const plural = start({ scene: Object.assign({}, SCENE, { config: { excludedObjects: '2' } }) });
    assert.equal(plain(plural.$(`${CARD(2)} .j2ha-room-notyet`).text()).trim(), '· 2 pas encore retirés');
  });

  maybe('la carte dit « Pièce exclue » même si les états ne sont pas lus (écriture déjà enregistrée)', () => {
    const ui = start({ states: false });
    assert.equal(plain(ui.$(`${CARD(3)} .j2ha-room-excluded-line`).text()).trim(), 'Pièce exclue');
    assert.ok(plain(ui.$(CARD(3)).attr('aria-label')).startsWith('Pièce fictive B, pièce exclue'));
  });

  maybe('la ligne de la pièce dans l\'arbre porte « Pièce exclue » à la place du ratio', () => {
    const ui = start();
    openCardWide(ui, 2);
    const excludedRow = ui.$('.j2ha-wv .j2ha-wv-room[data-object_id="3"] .j2ha-wv-row');
    assert.equal(plain(excludedRow.find('.j2ha-wv-excluded').text()).trim(), 'Pièce exclue');
    assert.equal(excludedRow.find('.j2ha-wv-ratio').length, 0, 'plus de ratio');
    const plainRow = ui.$('.j2ha-wv .j2ha-wv-room[data-object_id="2"] .j2ha-wv-row');
    assert.equal(plain(plainRow.find('.j2ha-wv-ratio').text()), '2 / 2');
    assert.equal(plainRow.find('.j2ha-wv-excluded').length, 0);
  });
});

describe('25.8 / AC13 — D1 : la pièce exclue prime sur « Toujours »', () => {
  const REASON = 'Pièce exclue : elle prime sur ce réglage.';

  maybe('équipement exclu par la pièce, réglé « Automatique » : « Toujours » et « Jamais » grisés avec l\'infobulle de D1', () => {
    const ui = start();
    openCard(ui, 3);
    ui.selectEquipment(301, treeBody(EQUIPMENTS[301]));
    assert.equal(plain(ui.$('.j2ha-eq-panel .j2ha-eq-publish-badge').text()).trim(), 'Exclu');
    assert.ok(plain(ui.$('.j2ha-eq-exclusion .j2ha-notice-text').text()).includes('Exclu par la pièce'));
    for (const key of ['always', 'never']) {
      const button = ui.$(`.j2ha-eq-controls .j2ha-seg-${key}`);
      assert.equal(button.attr('aria-disabled'), 'true', key + ' grisé');
      assert.equal(plain(button.attr('title')), REASON, key);
    }
  });

  maybe('« Toujours » déjà posé reste la position courante (aucune écriture), « Jamais » grisé avec l\'infobulle de D1', () => {
    const ui = start();
    openCard(ui, 3);
    ui.selectEquipment(301, treeBody(EQUIPMENTS[301], { equipment_publication_override: 'force_publish', has_publication_override: true }));
    const always = ui.$('.j2ha-eq-controls .j2ha-seg-always');
    assert.equal(always.attr('aria-checked'), 'true', 'position courante');
    assert.ok(always.hasClass('j2ha-seg-active'));
    assert.equal(plain(ui.$('.j2ha-eq-controls .j2ha-seg-never').attr('title')), REASON);
    assert.equal(ui.count('savePublicationOverride'), 0);
    assert.equal(ui.count('revertPublicationOverride'), 0);
    assert.equal(ui.count('executeHaAction'), 0);
  });

  maybe('une exclusion par le plugin garde l\'infobulle historique (« Équipement non éligible… »)', () => {
    const scene = Object.assign({}, SCENE, { config: { excludedObjects: '3' } });
    const ui = startWorkview({ scene, equipments: Object.assign({}, EQUIPMENTS, { 201: excludedBy(201, 'excluded_plugin') }), pluginNames: { plugin_alpha: 'Alpha' } });
    openCard(ui, 2);
    ui.selectEquipment(201, treeBody(excludedBy(201, 'excluded_plugin')));
    assert.equal(plain(ui.$('.j2ha-eq-controls .j2ha-seg-never').attr('title')), 'Équipement non éligible : l’action serait sans effet.');
  });

  it('publicationActionState (25.1) n\'est pas modifié : le texte historique des segments grisés est inchangé', () => {
    const state = M.publicationActionState({ eligible: false }, true);
    assert.equal(state.force_reason, 'Équipement non éligible : l’action serait sans effet.');
    assert.equal(state.exclude_reason, 'Équipement non éligible : l’action serait sans effet.');
    assert.equal(state.can_force, false);
    assert.equal(state.can_exclude, false);
  });
});
