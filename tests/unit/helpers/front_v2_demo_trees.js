'use strict';

/* Front v2 (Lot 2) — les cinq arbres de la démo (forme brute de `GET /system/mapping_overrides/{eq}`), plus une lumière
 * publiée, chacun AVEC ou SANS les champs additifs du démon (Lot 3 : `entities[].ha_*`, `commands[].cmd_type`,
 * `commands[].linked_state_cmd_id`, `hints`). Données fictives (CC-48) : noms, identifiants et plugins inventés. */

function diag(reason, opts) {
  const o = opts || {};
  const valid = o.valid === true;
  return {
    ha_entity_type: o.type || null,
    projection_validity: { is_valid: valid, reason_code: valid ? null : (o.validity || reason), missing_capabilities: [], missing_fields: [] },
    should_publish: o.publish === true,
    publication_reason: reason,
    reason_code: o.code || null,
  };
}

const ready = (type) => diag('sure', { valid: true, publish: true, type, code: 'sure_mapping' });
const ignored = () => diag('command_not_covered', {});

function cmd(id, name, generic, diagnostic, extra, daemon) {
  const row = Object.assign({ jeedom_cmd_id: id, cmd_name: name, generic_type: generic, diagnostic, covered: true }, extra || {});
  if (daemon) Object.assign(row, daemon);
  return row;
}

function present(should) {
  return { synced_should_publish: should, current_should_publish: should, override_pending: false, published_in_ha: should };
}

function strip(tree, withDaemon) {
  if (withDaemon) return tree;
  delete tree.hints;
  tree.entities.forEach((e) => Object.keys(e).filter((k) => k.indexOf('ha_') === 0 && k !== 'ha_entity_type').forEach((k) => delete e[k]));
  tree.commands.forEach((c) => { delete c.cmd_type; delete c.cmd_sub_type; delete c.linked_state_cmd_id; });
  return tree;
}

/** Multiprise : trois sorties, ordres On / Off non reliés à leur état → trois capteurs binaires en lecture seule. */
function multiprise(withDaemon) {
  const id = 142;
  const commands = [];
  const entities = [];
  for (let i = 1; i <= 3; i += 1) {
    const state = 870 + i;
    commands.push(cmd(state, 'État ' + i, 'SWITCH_STATE', ready('binary_sensor'), { published_in_ha: true },
      { cmd_type: 'info', cmd_sub_type: 'binary', linked_state_cmd_id: null }));
    entities.push({
      ha_entity_type: 'binary_sensor', command_ids: [state], decision: ready('binary_sensor'), publication_override: null,
      override_command_id: state, override_pending: false, present_in_ha: true,
      ha_unique_id: 'jeedom2ha_' + id + '_' + state, ha_default_entity_id: 'binary_sensor.jeedom2ha_' + id + '_' + state,
      ha_name: 'Sortie ' + i, ha_device_name: 'Multiprise Bureau', ha_device_class: null, ha_unit: null,
      ha_controllable: false, ha_capabilities: ['read'],
    });
  }
  const actions = [];
  for (let i = 1; i <= 3; i += 1) {
    actions.push(cmd(880 + i, 'On ' + i, 'SWITCH_ON', ignored(), { published_in_ha: false, covered: false },
      { cmd_type: 'action', cmd_sub_type: 'other', linked_state_cmd_id: null }));
    actions.push(cmd(890 + i, 'Off ' + i, 'SWITCH_OFF', ignored(), { published_in_ha: false, covered: false },
      { cmd_type: 'action', cmd_sub_type: 'other', linked_state_cmd_id: null }));
  }
  return strip({
    jeedom_eq_id: id, eq_name: 'Multiprise Bureau', mapped: true, eligible: true, equipment_decision: ready('binary_sensor'),
    entities, commands: commands.concat(actions), sync_status: present(true),
    hints: [{ code: 'actions_not_linked_to_state', cmd_ids: actions.map((c) => c.jeedom_cmd_id), details: { count: 3 } }],
  }, withDaemon);
}

/** Portail : un état binaire typé « Portail État », aucun ordre typé → capteur binaire. */
function portail(withDaemon) {
  const id = 150;
  return strip({
    jeedom_eq_id: id, eq_name: 'Portail', mapped: true, eligible: true, equipment_decision: ready('binary_sensor'),
    entities: [{
      ha_entity_type: 'binary_sensor', command_ids: [1501], decision: ready('binary_sensor'), publication_override: null,
      override_command_id: 1501, override_pending: false, present_in_ha: true,
      ha_unique_id: 'jeedom2ha_150_1501', ha_default_entity_id: 'binary_sensor.jeedom2ha_150_1501', ha_name: 'Portail',
      ha_device_class: 'opening', ha_controllable: false, ha_capabilities: ['read'],
    }],
    commands: [
      cmd(1501, 'État', 'BARRIER_STATE', ready('binary_sensor'), { published_in_ha: true }, { cmd_type: 'info', cmd_sub_type: 'binary', linked_state_cmd_id: null }),
      cmd(1502, 'Impulsion', null, ignored(), { published_in_ha: false, covered: false }, { cmd_type: 'action', cmd_sub_type: 'other', linked_state_cmd_id: null }),
    ],
    sync_status: present(true),
    hints: [{ code: 'binary_state_without_orders', cmd_ids: [1501], details: {} }],
  }, withDaemon);
}

/** Ventilateur : marche / arrêt publiés en interrupteur, la vitesse est perdue. */
function ventilateur(withDaemon) {
  const id = 160;
  return strip({
    jeedom_eq_id: id, eq_name: 'Ventilateur Chambre', mapped: true, eligible: true, equipment_decision: ready('switch'),
    entities: [{
      ha_entity_type: 'switch', command_ids: [1601, 1602, 1603], decision: ready('switch'), publication_override: null,
      override_command_id: 1601, override_pending: false, present_in_ha: true,
      ha_unique_id: 'jeedom2ha_eq_160', ha_default_entity_id: 'switch.jeedom2ha_eq_160', ha_name: 'Ventilateur Chambre',
      ha_controllable: true, ha_capabilities: ['on_off'],
    }],
    commands: [
      cmd(1601, 'État', 'ENERGY_STATE', ready('switch'), { published_in_ha: true }, { cmd_type: 'info', linked_state_cmd_id: null }),
      cmd(1602, 'On', 'ENERGY_ON', ready('switch'), { published_in_ha: true }, { cmd_type: 'action', linked_state_cmd_id: 1601 }),
      cmd(1603, 'Off', 'ENERGY_OFF', ready('switch'), { published_in_ha: true }, { cmd_type: 'action', linked_state_cmd_id: 1601 }),
      cmd(1604, 'Vitesse', 'FAN_SPEED', ignored(), { published_in_ha: false, covered: false }, { cmd_type: 'action', linked_state_cmd_id: null }),
      cmd(1605, 'Vitesse état', 'FAN_SPEED_STATE', ignored(), { published_in_ha: false, covered: false }, { cmd_type: 'info', linked_state_cmd_id: null }),
    ],
    sync_status: present(true),
    hints: [{ code: 'speed_not_carried', cmd_ids: [1604, 1605], details: {} }],
  }, withDaemon);
}

/** Lampe typée « prise » : le nom dit lampe, les types disent prise → ambigu, non publié. */
function lampePrise(withDaemon) {
  const id = 231;
  const blocked = () => diag('ambiguous_skipped', { code: 'name_heuristic_rejection', type: 'switch', validity: 'ha_missing_command_topic' });
  return strip({
    jeedom_eq_id: id, eq_name: 'Lampe Chevet', mapped: true, eligible: true, equipment_decision: blocked(),
    entities: [{
      ha_entity_type: 'switch', command_ids: [2311, 2312, 2313], decision: blocked(), publication_override: null,
      override_command_id: 2311, override_pending: false, present_in_ha: false,
      reason_details: { available_types: ['ENERGY_STATE', 'ENERGY_ON', 'ENERGY_OFF'], matched_keyword: 'lampe' },
      ha_unique_id: 'jeedom2ha_eq_231', ha_default_entity_id: 'switch.jeedom2ha_eq_231', ha_name: 'Lampe Chevet',
      ha_controllable: true, ha_capabilities: ['on_off'],
    }],
    commands: [
      cmd(2311, 'État', 'ENERGY_STATE', blocked(), { published_in_ha: false, attendu_ha: 'switch' }, { cmd_type: 'info', linked_state_cmd_id: null }),
      cmd(2312, 'On', 'ENERGY_ON', blocked(), { published_in_ha: false, attendu_ha: 'switch' }, { cmd_type: 'action', linked_state_cmd_id: 2311 }),
      cmd(2313, 'Off', 'ENERGY_OFF', blocked(), { published_in_ha: false, attendu_ha: 'switch' }, { cmd_type: 'action', linked_state_cmd_id: 2311 }),
    ],
    sync_status: present(false),
    hints: [{ code: 'name_type_mismatch', cmd_ids: [2311, 2312, 2313], details: { name_word: 'lampe', type_word: 'prise' } }],
  }, withDaemon);
}

/** Équipement sans type générique : Jeedom ne dit pas à quoi servent ses commandes. */
function sansType(withDaemon) {
  const id = 300;
  const blocked = () => diag('no_generic_type_configured', {});
  return strip({
    jeedom_eq_id: id, eq_name: 'Capteur Atelier', mapped: false, eligible: true, equipment_decision: blocked(),
    entities: [],
    commands: [
      cmd(3001, 'Valeur', null, blocked(), { published_in_ha: false, covered: false }, { cmd_type: 'info', linked_state_cmd_id: null }),
      cmd(3002, 'Batterie', null, blocked(), { published_in_ha: false, covered: false }, { cmd_type: 'info', linked_state_cmd_id: null }),
    ],
    sync_status: present(false),
    hints: [],
  }, withDaemon);
}

/** Une lumière publiée : pilotable (allumer, éteindre), identifiant fourni par le démon. */
function lumiere(withDaemon) {
  const id = 200;
  return strip({
    jeedom_eq_id: id, eq_name: 'Plafonnier Séjour', mapped: true, eligible: true, equipment_decision: ready('light'),
    entities: [{
      ha_entity_type: 'light', command_ids: [2001, 2002, 2003], decision: ready('light'), publication_override: null,
      override_command_id: 2001, override_pending: false, present_in_ha: true,
      ha_unique_id: 'jeedom2ha_eq_200', ha_default_entity_id: 'light.jeedom2ha_eq_200', ha_name: 'Plafonnier Séjour',
      ha_controllable: true, ha_capabilities: ['on_off'],
    }],
    commands: [
      cmd(2001, 'État', 'LIGHT_STATE', ready('light'), { published_in_ha: true }, { cmd_type: 'info', linked_state_cmd_id: null }),
      cmd(2002, 'On', 'LIGHT_ON', ready('light'), { published_in_ha: true }, { cmd_type: 'action', linked_state_cmd_id: 2001 }),
      cmd(2003, 'Off', 'LIGHT_OFF', ready('light'), { published_in_ha: true }, { cmd_type: 'action', linked_state_cmd_id: 2001 }),
    ],
    sync_status: present(true),
    hints: [],
  }, withDaemon);
}

const DEMO = { multiprise, portail, ventilateur, lampePrise, sansType, lumiere };

/** Pièce fictive « Bureau » contenant les six équipements (plugin fictif « virtual » → « Virtuel »). */
function demoRoom() {
  return {
    object_id: 9, object_name: 'Bureau',
    equipments: Object.values(DEMO).map((make) => {
      const t = make(true);
      return { eq_id: t.jeedom_eq_id, eq_name: t.eq_name, eq_type: 'virtual', enabled: true };
    }),
  };
}

module.exports = { DEMO, demoRoom, diag };
