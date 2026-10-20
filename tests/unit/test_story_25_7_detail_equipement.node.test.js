// ARTEFACT — Story 25.7 (AC4, AC6) : le détail d'un équipement « Exclu » dit la cause UNE fois, sous le badge (encart neutre,
// role="status", icône fa-eye-slash), avec l'endroit où agir (texte, et lien vers la configuration du plugin pour une cause de
// plugin, sans aucune écriture) ; rien pour un équipement désactivé ni pour un autre état ; nom du plugin échappé. Vrai code
// sur faux DOM ; plugins fictifs (CC-48).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { startWorkview, openCard, phpAvailable } = require('./helpers/workview_harness');
const { plain } = require('./helpers/page_b_harness');

const maybe = phpAvailable ? it : it.skip;

function diag(reason) {
  return { confidence: null, ha_entity_type: null, publication_reason: reason, reason_code: null, should_publish: false,
    projection_validity: { is_valid: false, missing_capabilities: [], missing_fields: [], reason_code: reason } };
}
function excluded(id, reason) {
  return { jeedom_eq_id: id, commands: [{ jeedom_cmd_id: id * 10, covered: false, diagnostic: diag(reason), published_in_ha: false }], entities: [],
    equipment_decision: diag(reason), sync_status: { published_in_ha: false, synced_should_publish: false, current_should_publish: false } };
}
const treeBody = (entry) => ({ state: 'ok', result: { status: 'ok', payload: Object.assign({ eq_name: 'Eq', mapped: false, eligible: true }, entry) } });

const SCENE = {
  objects: [{ id: 2, name: 'Pièce fictive', father_id: null, display: {} }],
  eqlogics: { 2: [
    { id: 201, name: 'Eq plugin', type: 'plugin_alpha' }, { id: 202, name: 'Eq pièce', type: 'plugin_alpha' },
    { id: 203, name: 'Eq jamais', type: 'plugin_alpha' }, { id: 204, name: 'Eq inconnu', type: 'plugin_gone' },
    { id: 205, name: 'Eq désactivé', type: 'plugin_alpha', enabled: false }, { id: 206, name: 'Eq <b>HTML</b>', type: 'plugin_html' },
  ] },
  plugin_names: { plugin_alpha: 'Alpha', plugin_html: '<img src=x onerror=alert(1)>' },
  doc: 'https://doc.example.test/plugin',
};
const ENTRIES = {
  201: excluded(201, 'excluded_plugin'), 202: excluded(202, 'excluded_object'), 203: excluded(203, 'publication_excluded_eqlogic'),
  204: excluded(204, 'excluded_plugin'), 205: excluded(205, 'excluded_object'), 206: excluded(206, 'excluded_plugin'),
};

function open(eqId) {
  const ui = startWorkview({ scene: SCENE, equipments: ENTRIES });
  openCard(ui, 2);
  ui.selectEquipment(eqId, treeBody(ENTRIES[eqId]));
  return ui;
}

describe('25.7 / AC4 — encart de cause du détail d\'équipement', () => {
  maybe('par le plugin : phrase avec le nom affiché, encart neutre en role="status", lien de configuration (ouverture seule)', () => {
    const ui = open(201);
    const notice = ui.$('.j2ha-eq-exclusion .j2ha-notice');
    assert.equal(notice.length, 1, 'un seul encart de cause');
    assert.equal(notice.attr('role'), 'status');
    assert.ok(notice.hasClass('j2ha-notice-neutral'));
    assert.equal(ui.$('.j2ha-eq-exclusion .fa-eye-slash').length, 1);
    assert.equal(plain(ui.$('.j2ha-eq-exclusion .j2ha-notice-text').text()).trim(), 'Exclu par le plugin Alpha (configuration du plugin, « Plugins exclus »)');
    const link = ui.$('.j2ha-eq-exclusion .j2ha-open-plugin-config');
    assert.equal(link.length, 1);
    assert.equal(link.attr('href'), 'index.php?v=d&p=plugin&id=jeedom2ha');
    assert.equal(link.attr('rel'), 'noopener');
    assert.equal(plain(ui.$('.j2ha-eq-panel .j2ha-eq-publish-badge').text()).trim(), 'Exclu', 'le mot d\'état reste « Exclu »');
    assert.equal(ui.count('executeHaAction'), 0, 'aucune écriture');
  });

  maybe('par la pièce, individuelle : phrases de D1, pas de lien', () => {
    const room = open(202);
    assert.equal(plain(room.$('.j2ha-eq-exclusion .j2ha-notice-text').text()).trim(), 'Exclu par la pièce : toute la pièce est exclue');
    assert.equal(room.$('.j2ha-eq-exclusion .j2ha-open-plugin-config').length, 0);
    const never = open(203);
    assert.equal(plain(never.$('.j2ha-eq-exclusion .j2ha-notice-text').text()).trim(), 'Exclusion individuelle : réglage « Jamais »');
    assert.equal(never.$('.j2ha-eq-exclusion .j2ha-notice').length, 1);
  });

  maybe('plugin inconnu de la page : l\'identifiant (repli) ; nom vide impossible côté page, « son plugin » côté fonction', () => {
    const ui = open(204);
    assert.equal(plain(ui.$('.j2ha-eq-exclusion .j2ha-notice-text').text()).trim(), 'Exclu par le plugin plugin_gone (configuration du plugin, « Plugins exclus »)');
  });

  maybe('équipement désactivé : aucun encart ; état « Désactivé »', () => {
    const ui = open(205);
    assert.equal(ui.$('.j2ha-eq-exclusion .j2ha-notice').length, 0);
    assert.equal(plain(ui.$('.j2ha-eq-panel .j2ha-eq-publish-badge').text()).trim(), 'Désactivé');
  });

  maybe('nom de plugin hostile : inséré comme texte (.text()), jamais interprété en HTML', () => {
    const ui = open(206);
    const html = ui.$('.j2ha-eq-exclusion .j2ha-notice-text');
    assert.match(plain(html.text()), /<img src=x onerror=alert\(1\)>/);
    assert.equal(ui.$('.j2ha-eq-exclusion img').length, 0);
  });

  maybe('la relecture des états met l\'encart à jour sans relire l\'arbre (parité agrégé / unitaire)', () => {
    const ui = open(201);
    const reads = ui.reads();
    ui.page.reader.trigger();
    ui.advance(500);
    ui.respond('getEquipmentStates', { state: 'ok', result: { status: 'ok', payload: { schema_version: 1, available: true, meta: { action_in_progress: false },
      equipments: Object.assign({}, ENTRIES, { 201: excluded(201, 'excluded_object') }), unread: [] } } });
    assert.equal(plain(ui.$('.j2ha-eq-exclusion .j2ha-notice-text').text()).trim(), 'Exclu par la pièce : toute la pièce est exclue');
    assert.equal(ui.$('.j2ha-eq-exclusion .j2ha-notice').length, 1);
    assert.equal(ui.reads().trees, reads.trees, 'aucune relecture d\'arbre');
  });

  maybe('les lignes d\'arbre portent la mention courte de la cause, nom du plugin compris', () => {
    const ui = startWorkview({ scene: SCENE, equipments: ENTRIES });
    openCard(ui, 2);
    const mention = (eqId) => plain(ui.$(`.j2ha-wv-eq[data-eq-id="${eqId}"] .j2ha-wv-cause`).text()).trim();
    assert.equal(mention(201), 'par le plugin Alpha');
    assert.equal(mention(202), 'par la pièce');
    assert.equal(mention(203), 'individuelle');
    assert.equal(mention(204), 'par le plugin plugin_gone');
    assert.equal(ui.$('.j2ha-wv-eq[data-eq-id="205"] .j2ha-wv-cause').length, 0, 'un désactivé n\'a jamais de mention');
    const exclusion = plain(ui.$('.j2ha-wv-exclusion').text()).trim();
    assert.match(exclusion, /^Exclus : /);
    assert.match(exclusion, /par le plugin Alpha/);
  });
});
