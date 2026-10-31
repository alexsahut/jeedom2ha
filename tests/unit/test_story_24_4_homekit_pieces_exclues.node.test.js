// ARTEFACT — Story 24.4 (R1 PR #335) : une pièce exclue qui contient un équipement relevé par l'exposition HomeKit ne dit pas
// « pas encore retiré » (faux, permanent) mais « N gardé(s) (HomeKit) » ; la confirmation d'exclusion n'annonce pas les entités
// d'un équipement qui sera relevé. Champs additifs de la route agrégée : homekit_kept_in_excluded_room, homekit_exposed_effective,
// scope_inherit. Vrai code sur faux DOM ; identifiants fictifs (CC-48).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const O = require('../../desktop/js/jeedom2ha_overview.js');
const { startWorkview, phpAvailable } = require('./helpers/workview_harness');
const { plain } = require('./helpers/page_b_harness');

const maybe = phpAvailable ? it : it.skip;

const SCENE = {
  objects: [{ id: 3, name: 'Pièce fictive B', father_id: null, display: {} }],
  eqlogics: { 3: [{ id: 301, name: 'Eq 301', type: 'plugin_alpha' }, { id: 302, name: 'Eq 302', type: 'plugin_alpha' }] },
  plugin_names: { plugin_alpha: 'Alpha' },
  config: { excludedObjects: '3' },
};
const diag = (reason, publish) => ({ confidence: null, ha_entity_type: null, publication_reason: reason, reason_code: null, should_publish: publish,
  projection_validity: { is_valid: publish, missing_capabilities: [], missing_fields: [], reason_code: publish ? null : reason } });
const published = (id, extra) => Object.assign({
  jeedom_eq_id: id, equipment_decision: diag('sure_mapping', true),
  entities: [{ override_pending: false, present_in_ha: true }],
  commands: [{ jeedom_cmd_id: id * 10, covered: true, diagnostic: diag('sure_mapping', true), published_in_ha: true }],
  sync_status: { published_in_ha: true, synced_should_publish: true, current_should_publish: true, override_pending: false },
}, extra || {});
const removed = (id) => ({
  jeedom_eq_id: id, equipment_decision: diag('excluded_object', false), entities: [],
  commands: [{ jeedom_cmd_id: id * 10, covered: false, diagnostic: diag('excluded_object', false), published_in_ha: false }],
  sync_status: { published_in_ha: false, synced_should_publish: false, current_should_publish: false, override_pending: false },
});
// 301 relevé par HomeKit (reste publié), 302 retiré par la pièce.
const EQUIPMENTS = { 301: published(301, { homekit_kept_in_excluded_room: true, homekit_exposed_effective: true, scope_inherit: true }), 302: removed(302) };
const CARD = '#j2ha_roomCards .j2ha-room-card[data-object_id="3"]';

describe('24.4 R1 — carte d\'une pièce exclue', () => {
  it('computeOverview : la ligne relevée est marquée, jamais comptée comme à retirer', () => {
    const rooms = [{ object_id: 3, object_name: 'Pièce fictive B', excluded: true, equipments: [{ eq_id: 301, enabled: true }, { eq_id: 302, enabled: true }] }];
    const o = O.computeOverview(rooms, EQUIPMENTS);
    const rows = o.rooms[0].equipments;
    assert.equal(rows[0].homekit_kept, true);
    assert.equal(rows[1].homekit_kept, false);
  });

  maybe('un équipement relevé : aucun « pas encore retiré », mention « 1 gardé (HomeKit) »', () => {
    const ui = startWorkview({ scene: SCENE, equipments: EQUIPMENTS, pluginNames: { plugin_alpha: 'Alpha' } });
    assert.equal(ui.$(`${CARD} .j2ha-room-notyet`).length, 0, 'pas de faux « pas encore retiré »');
    assert.equal(plain(ui.$(`${CARD} .j2ha-room-homekit-kept`).text()).trim(), '· 1 gardé (HomeKit)');
    assert.ok(!/pas encore retir/.test(plain(ui.$(CARD).text())));
  });

  maybe('sans équipement relevé : « pas encore retiré » inchangé, aucune mention HomeKit', () => {
    const eq = { 301: published(301), 302: removed(302) };
    const ui = startWorkview({ scene: SCENE, equipments: eq, pluginNames: { plugin_alpha: 'Alpha' } });
    assert.equal(plain(ui.$(`${CARD} .j2ha-room-notyet`).text()).trim(), '· 1 pas encore retiré');
    assert.equal(ui.$(`${CARD} .j2ha-room-homekit-kept`).length, 0);
  });
});

describe('24.4 R1 — impact de la confirmation d\'exclusion', () => {
  const ROOMS = [{ object_id: 2, object_name: 'Pièce fictive', equipments: [{ eq_id: 201, enabled: true }, { eq_id: 202, enabled: true }, { eq_id: 203, enabled: false }, { eq_id: 204, enabled: true }] }];
  const ent = () => ({ override_pending: false, present_in_ha: true });
  const snap = (equipments) => ({ kind: 'ok', view: { stale: false, equipments, overview: { counts: { to_apply: 0 } } } });

  it('les entités d\'un équipement actif, exposé HomeKit et d\'état `inherit` ne sont pas comptées', () => {
    const impact = O.roomExclusionImpact(snap({
      201: { jeedom_eq_id: 201, entities: [ent(), ent()], homekit_exposed_effective: true, scope_inherit: true },
      202: { jeedom_eq_id: 202, entities: [ent()], homekit_exposed_effective: false, scope_inherit: true },
      203: { jeedom_eq_id: 203, entities: [ent()], homekit_exposed_effective: true, scope_inherit: true },
      204: { jeedom_eq_id: 204, entities: [ent()], homekit_exposed_effective: true, scope_inherit: false },
    }), ROOMS, 2);
    // 201 ignoré ; 202 (non exposé), 203 (désactivé) et 204 (état d'équipement explicite) comptés.
    assert.equal(impact.entities, 3);
  });

  it('un démon plus ancien (champs absents) : comportement inchangé', () => {
    const impact = O.roomExclusionImpact(snap({ 201: { jeedom_eq_id: 201, entities: [ent(), ent()] } }), ROOMS, 2);
    assert.equal(impact.entities, 2);
  });
});

describe('24.4 R1 — détail d\'équipement', () => {
  it('la cause « exposé à HomeKit : non écarté par sa pièce » est dite quand le champ additif est vrai (aucune exclusion)', () => {
    const src = require('node:fs').readFileSync(require('node:path').join(__dirname, '../../desktop/js/jeedom2ha_mapping_surface.js'), 'utf8');
    assert.match(src, /!cause && tree\.homekit_kept_in_excluded_room === true/);
    assert.ok(src.includes('{{Exposé à HomeKit : non écarté par sa pièce}}'));
  });
});
