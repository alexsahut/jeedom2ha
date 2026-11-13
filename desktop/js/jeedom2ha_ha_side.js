// Front v2 — Lot 2 : côté Home Assistant de la fiche équipement, `window.Jeedom2haHaSide`.
// Ce que devient l'équipement dans Home Assistant (type en français, nom, identifiant, pilotable ou lecture seule,
// verbes de capacité) et les conseils quand il est publié mais dégradé.
// Module pur : aucun DOM, aucune E/S ; il lit l'arbre BRUT de `GET /system/mapping_overrides/{eq}` (les champs additifs
// du démon `entities[].ha_*`, `commands[].cmd_type`, `commands[].linked_state_cmd_id`, `hints` sont facultatifs).
// Priorité aux champs du démon ; sans eux, repli prudent : en cas de doute, aucun conseil, et jamais d'identifiant deviné.
// L'état de l'équipement n'est jamais calculé ici (source unique : jeedom2ha_mapping_override.js).
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory(function () { return require('./jeedom2ha_lexique.js'); });
    return;
  }
  root.Jeedom2haHaSide = factory(function () { return root.Jeedom2haLexique; });
}(typeof globalThis !== 'undefined' ? globalThis : this, function (lexicon) {
  'use strict';

  // Lexique résolu à l'usage (il est chargé juste avant ce module dans la page).
  var L = {
    haTypeLabel: function (type) { return lexicon().haTypeLabel(type); },
    capabilityVerbs: function (caps) { return lexicon().capabilityVerbs(caps); },
    plural: function (n, one, many) { return n > 1 ? many : one; },
  };

  var READ_ONLY_TYPES = ['sensor', 'binary_sensor'];
  var CONTROLLABLE_TYPES = ['light', 'switch', 'fan', 'cover', 'climate', 'lock', 'valve', 'button', 'number', 'select',
    'alarm_control_panel', 'scene'];
  // Capacité par défaut d'un type pilotable quand aucun type générique ne la précise (le démon ne publie ces types
  // qu'avec leurs ordres).
  var DEFAULT_CAPABILITIES = {
    light: ['on_off'], switch: ['on_off'], fan: ['on_off'], cover: ['open_close'], valve: ['open_close'],
    climate: ['temperature'], lock: ['lock'], button: ['press'], scene: ['press'], number: ['position'], select: ['mode'],
  };
  var KNOWN_CAPABILITIES = ['on_off', 'brightness', 'position', 'tilt', 'stop', 'temperature', 'mode', 'press', 'lock',
    'open_close', 'read'];

  function isObject(value) {
    return !!value && typeof value === 'object' && !Array.isArray(value);
  }

  function text(value) {
    return typeof value === 'string' && value.trim() !== '' ? value.trim() : null;
  }

  function commandsById(commands) {
    var map = {};
    (Array.isArray(commands) ? commands : []).forEach(function (cmd) {
      if (isObject(cmd) && cmd.jeedom_cmd_id != null) {
        map[cmd.jeedom_cmd_id] = cmd;
      }
    });
    return map;
  }

  function genericOf(cmd) {
    return cmd && typeof cmd.generic_type === 'string' ? cmd.generic_type : '';
  }

  // Capacités déduites des types génériques des commandes d'une entité (repli sans `ha_capabilities`). Alignées sur les
  // mappers du démon (resources/daemon/mapping/*.py) : une capacité n'est retenue que si l'ORDRE qui la porte existe
  // (commande action), jamais sur le seul retour d'état. Ex. : la luminosité exige `LIGHT_SLIDER` (`_detect_brightness`),
  // `LIGHT_BRIGHTNESS` seul (info) ne publie aucun réglage. Une commande dite `info` par le démon n'ouvre aucune capacité.
  var ORDER_CAPABILITIES = {
    light: [['on_off', /^LIGHT_(ON|OFF)$/], ['brightness', /^LIGHT_SLIDER$/]],
    switch: [['on_off', /^(ENERGY|SWITCH|FAN)_(ON|OFF)$/]],
    fan: [['on_off', /^FAN_(ON|OFF)$/]],
    cover: [['open_close', /^(FLAP_(UP|DOWN)|FLAP_BSO_(UP|DOWN)|GB_(OPEN|CLOSE|TOGGLE))$/], ['stop', /^FLAP_STOP$/],
      ['position', /^FLAP_SLIDER$/]],
    climate: [['temperature', /^THERMOSTAT_SET_SETPOINT$/], ['mode', /^THERMOSTAT_SET_MODE$/]],
    lock: [['lock', /^LOCK_(OPEN|CLOSE)$/]],
    valve: [['open_close', /^(IRRIG|FAUCET|VALVE)_(ON|OFF)$/]],
  };

  function capabilitiesFromOrders(type, members) {
    var rules = ORDER_CAPABILITIES[type] || [];
    var orders = members.filter(function (cmd) { return cmd.cmd_type !== 'info'; }).map(genericOf).filter(Boolean);
    var caps = [];
    rules.forEach(function (rule) {
      if (orders.some(function (g) { return rule[1].test(g); }) && caps.indexOf(rule[0]) === -1) caps.push(rule[0]);
    });
    return caps;
  }

  /**
   * Une entité, dite pour un humain : { ha_type, type_label, name, command_names, controllable (true / false / null),
   * capabilities, verbs, entity_id, unique_id, device_class, unit, source ('demon' | 'repli') }.
   * `entity_id` n'est rempli que si le démon le fournit (`ha_default_entity_id`) : jamais deviné.
   */
  function describeEntity(entity, commands) {
    var e = isObject(entity) ? entity : {};
    var type = text(e.ha_entity_type);
    var byId = commandsById(commands);
    var ids = Array.isArray(e.command_ids) ? e.command_ids : [];
    var members = ids.map(function (id) { return byId[id]; }).filter(Boolean);
    var fromDaemon = typeof e.ha_controllable === 'boolean' || Array.isArray(e.ha_capabilities);

    var controllable = null;
    if (typeof e.ha_controllable === 'boolean') {
      controllable = e.ha_controllable;
    } else if (READ_ONLY_TYPES.indexOf(type) !== -1) {
      controllable = false;
    } else if (CONTROLLABLE_TYPES.indexOf(type) !== -1) {
      controllable = true;
    }

    var capabilities;
    if (Array.isArray(e.ha_capabilities)) {
      capabilities = e.ha_capabilities.filter(function (c) { return KNOWN_CAPABILITIES.indexOf(c) !== -1; });
    } else if (controllable === false) {
      capabilities = ['read'];
    } else {
      capabilities = capabilitiesFromOrders(type, members);
      if (controllable === true && capabilities.length === 0 && DEFAULT_CAPABILITIES[type]) {
        capabilities = DEFAULT_CAPABILITIES[type].slice();
      }
      if (READ_ONLY_TYPES.indexOf(type) !== -1) {
        capabilities = ['read'];
      }
    }
    if (controllable === false) {
      capabilities = capabilities.filter(function (c) { return c === 'read'; });
      if (capabilities.length === 0) capabilities = ['read'];
    }

    return {
      ha_type: type,
      type_label: L.haTypeLabel(type),
      name: text(e.ha_name),
      device_name: text(e.ha_device_name),
      command_names: members.map(function (cmd) { return text(cmd.cmd_name) || ('#' + cmd.jeedom_cmd_id); }),
      controllable: controllable,
      capabilities: capabilities,
      verbs: L.capabilityVerbs(capabilities),
      entity_id: text(e.ha_default_entity_id),
      unique_id: text(e.ha_unique_id),
      device_class: text(e.ha_device_class),
      unit: text(e.ha_unit),
      source: fromDaemon ? 'demon' : 'repli',
    };
  }

  // Une entité est dans Home Assistant si le démon le dit (`present_in_ha`), sinon si sa décision la publie.
  function entityInHa(entity) {
    if (!isObject(entity)) return false;
    if (typeof entity.present_in_ha === 'boolean') return entity.present_in_ha;
    return isObject(entity.decision) && entity.decision.should_publish === true;
  }

  /**
   * Côté Home Assistant d'un arbre : { entities: [describeEntity…] (entités publiées), mention: 'controllable' |
   * 'read_only' | null, verbs (verbes des entités pilotables) }. `mention` est null s'il n'y a aucune entité ou si la
   * capacité n'est pas connue : rien n'est alors affiché.
   */
  function describeHaSide(tree) {
    var t = isObject(tree) ? tree : {};
    var commands = Array.isArray(t.commands) ? t.commands : [];
    var entities = (Array.isArray(t.entities) ? t.entities : []).filter(entityInHa)
      .map(function (entity) { return describeEntity(entity, commands); });
    var controllable = entities.filter(function (d) { return d.controllable === true; });
    var readOnly = entities.filter(function (d) { return d.controllable === false; });
    var mention = null;
    if (controllable.length > 0) mention = 'controllable';
    else if (entities.length > 0 && readOnly.length === entities.length) mention = 'read_only';
    var verbs = [];
    controllable.forEach(function (d) {
      d.verbs.forEach(function (v) { if (verbs.indexOf(v) === -1 && v !== 'lire l’état') verbs.push(v); });
    });
    return { entities: entities, mention: mention, verbs: verbs };
  }

  /** Côté Jeedom : nombre de commandes et répartition « 3 états, 3 ordres On, 3 ordres Off » (vide si non typé). */
  function describeJeedomSide(tree) {
    var commands = isObject(tree) && Array.isArray(tree.commands) ? tree.commands : [];
    var counts = { state: 0, on: 0, off: 0, other: 0 };
    commands.forEach(function (cmd) {
      var g = genericOf(cmd);
      if (/_STATE(_BOOL)?$/.test(g)) counts.state += 1;
      else if (/_ON$/.test(g)) counts.on += 1;
      else if (/_OFF$/.test(g)) counts.off += 1;
      else counts.other += 1;
    });
    var parts = [];
    if (counts.state + counts.on + counts.off > 0) {
      if (counts.state) parts.push(counts.state + ' ' + L.plural(counts.state, 'état', 'états'));
      if (counts.on) parts.push(counts.on + ' ' + L.plural(counts.on, 'ordre On', 'ordres On'));
      if (counts.off) parts.push(counts.off + ' ' + L.plural(counts.off, 'ordre Off', 'ordres Off'));
      if (counts.other) parts.push(counts.other + ' ' + L.plural(counts.other, 'autre', 'autres'));
    }
    return { command_count: commands.length, breakdown: parts.join(', ') };
  }

  // --- Conseils ---

  function hintFromDaemon(raw, commands) {
    if (!isObject(raw) || typeof raw.code !== 'string' || !raw.code) return null;
    var ids = Array.isArray(raw.cmd_ids) ? raw.cmd_ids.filter(function (id) { return typeof id === 'number'; }) : [];
    var details = isObject(raw.details) ? raw.details : {};
    var count = typeof details.count === 'number' ? details.count : null;
    if (count === null && raw.code === 'actions_not_linked_to_state') {
      var byId = commandsById(commands);
      var on = ids.filter(function (id) { return /_ON$/.test(genericOf(byId[id])); }).length;
      count = on > 0 ? on : ids.length;
    }
    return { code: raw.code, cmd_ids: ids, details: details, count: count, source: 'demon' };
  }

  // Repli sans `hints` : trois heuristiques étroites, chacune exige tous ses indices ; au moindre doute, rien.
  function heuristicHints(t) {
    var commands = Array.isArray(t.commands) ? t.commands : [];
    var entities = (Array.isArray(t.entities) ? t.entities : []).filter(entityInHa);
    var byId = commandsById(commands);
    var covered = {};
    entities.concat(Array.isArray(t.entities) ? t.entities : []).forEach(function (e) {
      (Array.isArray(e.command_ids) ? e.command_ids : []).forEach(function (id) { covered[id] = true; });
    });
    var hints = [];
    var typed = function (re) { return commands.filter(function (cmd) { return re.test(genericOf(cmd)); }); };
    var notLinked = function (cmd) { return cmd.linked_state_cmd_id === undefined || cmd.linked_state_cmd_id === null; };

    // Multiprise : sorties en capteur binaire, ordres On / Off présents mais portés par aucune entité. Comme
    // `SwitchMapper._group_switch_cmds`, un trio se forme dans UNE famille (SWITCH ou FAN) : la sortie lue doit porter
    // l'état de la même famille que les ordres (SWITCH_STATE pour SWITCH_ON / SWITCH_OFF). Un capteur binaire d'une autre
    // nature (présence, ouverture…) ne compte jamais.
    var outletCmdIds = [];
    var outlets = 0;
    ['SWITCH', 'FAN'].forEach(function (family) {
      var outputs = entities.filter(function (e) {
        return e.ha_entity_type === 'binary_sensor' && Array.isArray(e.command_ids) && e.command_ids.length > 0
          && e.command_ids.some(function (id) { return genericOf(byId[id]) === family + '_STATE'; });
      });
      var orphan = function (suffix) {
        return commands.filter(function (cmd) {
          return genericOf(cmd) === family + '_' + suffix && !covered[cmd.jeedom_cmd_id] && notLinked(cmd);
        });
      };
      var ons = orphan('ON');
      var offs = orphan('OFF');
      if (outputs.length > 0 && ons.length > 0 && offs.length > 0) {
        outlets += Math.min(outputs.length, ons.length, offs.length);
        ons.concat(offs).forEach(function (cmd) { outletCmdIds.push(cmd.jeedom_cmd_id); });
      }
    });
    if (outlets > 0) {
      hints.push({ code: 'actions_not_linked_to_state', cmd_ids: outletCmdIds, details: {}, count: outlets, source: 'repli' });
    }

    // Portail ou garage : état binaire publié en capteur binaire, sans aucun ordre Ouvrir / Fermer typé.
    var barrierStates = [];
    entities.forEach(function (e) {
      if (e.ha_entity_type !== 'binary_sensor') return;
      (Array.isArray(e.command_ids) ? e.command_ids : []).forEach(function (id) {
        if (/^(BARRIER|GARAGE)_STATE$/.test(genericOf(byId[id]))) barrierStates.push(id);
      });
    });
    // Ordres reconnus par `CoverMapper` pour un portail ou un garage : GB_OPEN, GB_CLOSE, GB_TOGGLE.
    if (barrierStates.length > 0 && typed(/^(GB_(OPEN|CLOSE|TOGGLE)|(BARRIER|GARAGE)_(OPEN|CLOSE))$/).length === 0) {
      hints.push({ code: 'binary_state_without_orders', cmd_ids: barrierStates, details: {}, count: null, source: 'repli' });
    }

    // Ventilateur : commandes de vitesse présentes, publié en interrupteur.
    var speeds = typed(/^FAN_SPEED/);
    var asSwitch = entities.some(function (e) { return e.ha_entity_type === 'switch'; });
    var asFan = entities.some(function (e) { return e.ha_entity_type === 'fan'; });
    if (speeds.length > 0 && asSwitch && !asFan) {
      hints.push({
        code: 'speed_not_carried', cmd_ids: speeds.map(function (cmd) { return cmd.jeedom_cmd_id; }),
        details: {}, count: null, source: 'repli',
      });
    }
    return hints;
  }

  /**
   * Conseils d'un arbre brut : [{ code, cmd_ids, details, count, source }]. Si le démon envoie `hints` (même vide), il
   * fait foi ; sinon, repli par heuristique sur l'arbre.
   */
  function computeHints(tree) {
    var t = isObject(tree) ? tree : {};
    if (Array.isArray(t.hints)) {
      return t.hints.map(function (raw) { return hintFromDaemon(raw, t.commands); }).filter(Boolean);
    }
    return heuristicHints(t);
  }

  // --- « Le nom dit X, les types Jeedom disent Y » ---

  var FAMILY_WORDS = { ENERGY: 'prise', LIGHT: 'lumière', SWITCH: 'interrupteur', FLAP: 'volet', FAN: 'ventilateur', BARRIER: 'portail', GARAGE: 'garage' };
  var NAME_WORDS = {
    lampe: 'LIGHT', lumière: 'LIGHT', lumiere: 'LIGHT', lustre: 'LIGHT', spot: 'LIGHT', applique: 'LIGHT', ampoule: 'LIGHT',
    éclairage: 'LIGHT', plafonnier: 'LIGHT', prise: 'ENERGY', volet: 'FLAP', store: 'FLAP', portail: 'BARRIER',
    ventilateur: 'FAN', ventilo: 'FAN',
  };

  function typeFamily(commands) {
    var families = {};
    (Array.isArray(commands) ? commands : []).forEach(function (cmd) {
      var m = /^(ENERGY|LIGHT|SWITCH|FLAP|FAN|BARRIER|GARAGE)_/.exec(genericOf(cmd));
      if (m) families[m[1]] = true;
    });
    var keys = Object.keys(families);
    return keys.length === 1 ? keys[0] : null;
  }

  function matchedKeyword(t) {
    var sources = [];
    (Array.isArray(t.entities) ? t.entities : []).forEach(function (e) { if (isObject(e)) sources.push(e.reason_details); });
    if (isObject(t.equipment_decision)) sources.push(t.equipment_decision.reason_details);
    (Array.isArray(t.hints) ? t.hints : []).forEach(function (h) {
      if (isObject(h) && h.code === 'name_type_mismatch') sources.push(h.details);
    });
    for (var i = 0; i < sources.length; i++) {
      var s = sources[i];
      if (isObject(s)) {
        var word = text(s.name_word) || text(s.matched_keyword);
        if (word) return word;
      }
    }
    return null;
  }

  /**
   * Mots de la fiche « le nom dit … , les types Jeedom disent … » : { name_word, type_word } ou null si l'un manque
   * (la fiche dit alors la phrase générale, sans deviner).
   */
  function nameTypeWords(tree, eqName) {
    var t = isObject(tree) ? tree : {};
    var family = typeFamily(t.commands);
    var typeWord = family ? FAMILY_WORDS[family] : null;
    if (!typeWord) return null;
    var nameWord = matchedKeyword(t);
    if (!nameWord) {
      var name = (text(eqName) || text(t.eq_name) || '').toLowerCase();
      var found = Object.keys(NAME_WORDS).filter(function (w) {
        return new RegExp('(^|[^\\p{L}])' + w + '([^\\p{L}]|$)', 'u').test(name) && NAME_WORDS[w] !== family;
      });
      nameWord = found.length === 1 ? found[0] : null;
    }
    if (!nameWord) return null;
    return { name_word: nameWord, type_word: typeWord };
  }

  return {
    version: 2,
    describeEntity: describeEntity,
    describeHaSide: describeHaSide,
    describeJeedomSide: describeJeedomSide,
    computeHints: computeHints,
    nameTypeWords: nameTypeWords,
  };
}));
