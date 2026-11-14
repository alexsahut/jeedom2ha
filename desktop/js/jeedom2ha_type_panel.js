// Front v2 — Lot 5 : panneau « Corriger le type » (écran E5), partie pure.
//
// Ce module ne fait AUCUNE requête et ne touche pas au DOM : il calcule ce que le panneau affiche (choix possibles et
// impossibles, aperçu avant / après en entités, message de résultat) à partir de la ligne de commande de l'arbre du démon
// et de la réponse de l'aperçu (`previewMappingOverride`, lecture seule). Le rendu, les requêtes, les minuteurs et
// l'annulation vivent dans la surface (jeedom2ha_mapping_surface.js, `openTypePanel`), qui l'appelle.
//
// Règles :
// - les types proposés sont ceux que le démon annonce (`override_types_allowed`), jamais une liste devinée ici ; les autres
//   restent visibles, grisés, avec leur raison (un choix absurde est impossible plutôt que refusé après coup) ;
// - champs du Lot 3 absents (`entities_before` / `entities_after`) : repli sur les vues `auto` / `overridden` de l'aperçu ;
// - aucun identifiant deviné : un identifiant n'est montré que s'il vient du démon.
//
// Chargeable sous node (module.exports) comme dans la page (globale `Jeedom2haTypePanel`).
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory(
      function () { return require('./jeedom2ha_mapping_override.js'); },
      function () { return require('./jeedom2ha_lexique.js'); },
      function () { return null; }
    );
    return;
  }
  root.Jeedom2haTypePanel = factory(
    function () { return root.Jeedom2haMappingOverride; },
    function () { return root.Jeedom2haLexique || null; },
    function () { return root.Jeedom2haSurface || null; }
  );
}(typeof globalThis !== 'undefined' ? globalThis : this, function (mapping, lexicon, surface) {
  'use strict';

  // Nom commun de chaque type, pour les phrases (« 1 lumière », « … est maintenant une lumière »).
  var TYPE_NOUNS = {
    alarm_control_panel: { article: 'une', one: 'alarme', many: 'alarmes' },
    binary_sensor: { article: 'un', one: 'capteur binaire', many: 'capteurs binaires' },
    button: { article: 'un', one: 'bouton', many: 'boutons' },
    climate: { article: 'un', one: 'thermostat', many: 'thermostats' },
    cover: { article: 'un', one: 'volet', many: 'volets' },
    light: { article: 'une', one: 'lumière', many: 'lumières' },
    lock: { article: 'une', one: 'serrure', many: 'serrures' },
    sensor: { article: 'un', one: 'capteur', many: 'capteurs' },
    switch: { article: 'un', one: 'interrupteur', many: 'interrupteurs' },
    valve: { article: 'une', one: 'vanne', many: 'vannes' },
  };

  // Pourquoi un type n'est pas possible pour cette commande : ce que le registre du démon exige pour ce type
  // (validation/ha_component_registry.py). Le démon dit QUE le type est impossible ; ce texte dit ce qui manque.
  var IMPOSSIBLE_REASONS = {
    alarm_control_panel: 'il faut l’état de l’alarme et des ordres pour l’armer ou la désarmer',
    binary_sensor: 'il faut une commande d’état à lire',
    button: 'il faut un ordre à déclencher',
    climate: 'il manque l’ordre qui règle la consigne de température',
    cover: 'il manque les ordres Monter et Descendre (ou Ouvrir et Fermer)',
    light: 'il manque les ordres Allumer et Éteindre',
    lock: 'il faut l’état de la serrure et un ordre Verrouiller ou Déverrouiller',
    sensor: 'il faut une commande d’état à lire',
    switch: 'il manque les ordres Allumer et Éteindre',
    valve: 'il faut l’état de la vanne et les ordres Ouvrir et Fermer',
  };
  var BUTTON_ON_STATE_REASON = 'une commande d’état ne peut pas devenir un bouton';
  var DEFAULT_IMPOSSIBLE_REASON = 'le plugin ne peut pas publier cette commande sous ce type';

  function M() {
    return mapping();
  }

  function lx() {
    var l = lexicon();
    return l && typeof l.haTypeLabel === 'function' ? l : null;
  }

  function isObject(value) {
    return !!value && typeof value === 'object';
  }

  function plural(n, one, many) {
    return n > 1 ? many : one;
  }

  /** « Lumière (light) » : libellé d'un type HA, partout. */
  function typeLabel(type) {
    var l = lx();
    if (l) return l.haTypeLabel(type);
    return M().formatHaDomain(type);
  }

  /** « Personnalisé : Lumière (light) » ou « auto » : texte du lien de la colonne « Type HA ». */
  function cellLabel(row) {
    var r = row || {};
    return r.override_applied === true ? 'Personnalisé : ' + typeLabel(r.effective_ha) : 'auto';
  }

  /** Raison d'un type impossible (sans le préfixe « impossible : »). `cmdType` : 'info' | 'action' | null (Lot 3). */
  function impossibleReason(type, cmdType) {
    if (type === 'button' && cmdType === 'info') return BUTTON_ON_STATE_REASON;
    return Object.prototype.hasOwnProperty.call(IMPOSSIBLE_REASONS, type) ? IMPOSSIBLE_REASONS[type] : DEFAULT_IMPOSSIBLE_REASON;
  }

  // Ce que le plugin fait aujourd'hui de cette commande sans réglage : « non publié », « Lumière (light) », ou rien si inconnu.
  function autoToday(row) {
    var r = row || {};
    if (r.override_applied === true) return null;
    var category = M().classifyCommandCategory(r);
    var view = M().readDiagnosticView(r.diagnostic);
    var type = (view && view.ha_entity_type) || r.effective_ha || r.attendu_ha || null;
    if (category === 'published' && type) return typeLabel(type);
    if (category === 'to_apply' && type) return typeLabel(type) + ', pas encore publié';
    if (category === 'blocked') return 'non publié';
    return null;
  }

  /**
   * Choix du panneau pour une ligne de commande de l'arbre (forme `commands[]`, normalisée ou brute).
   * `options.cmdType` : type Jeedom de la commande (champ additif du Lot 3), pour une raison plus précise.
   * Rend { current, choices: [{ value, label, hint, disabled, reason, checked }] } — `value` = '' pour « Automatique ».
   * Ordre : Automatique, puis les types possibles (ordre de la liste d'interface), puis les types impossibles.
   */
  function buildChoices(row, options) {
    var o = options || {};
    var r = M().normalizeCommandRow(row);
    var current = r.override_applied && r.effective_ha ? r.effective_ha : null;
    var allowed = M().getOverrideTypeOptions(r);
    var all = M().getHaEntityTypeOptions();
    var cmdType = o.cmdType === 'info' || o.cmdType === 'action' ? o.cmdType : null;
    var today = autoToday(r);
    var choices = [{
      value: '',
      label: 'Automatique',
      hint: today ? 'laisser le plugin décider (aujourd’hui : ' + today + ')' : 'laisser le plugin décider',
      disabled: false,
      reason: null,
      checked: current === null,
    }];
    allowed.forEach(function (type) {
      choices.push({ value: type, label: typeLabel(type), hint: null, disabled: false, reason: null, checked: type === current });
    });
    all.forEach(function (type) {
      if (allowed.indexOf(type) !== -1) return;
      choices.push({
        value: type, label: typeLabel(type), hint: null, disabled: true, reason: impossibleReason(type, cmdType), checked: false,
      });
    });
    return { current: current, choices: choices };
  }

  // --- Aperçu ---

  function readPayload(response) {
    var p = isObject(response) && isObject(response.result) ? response.result : response;
    p = isObject(p) && isObject(p.payload) ? p.payload : p;
    return isObject(p) ? p : null;
  }

  function verbsOf(capabilities) {
    var l = lx();
    if (!l || !Array.isArray(capabilities)) return [];
    return l.capabilityVerbs(capabilities.filter(function (c) { return c !== 'read'; }));
  }

  // Une entité de l'aperçu (forme du Lot 3) → ligne affichable. `will_publish` faux : pas dans Home Assistant.
  function entityLine(e) {
    var controllable = e.ha_controllable === true ? true : (e.ha_controllable === false ? false : null);
    return {
      type: typeof e.ha_entity_type === 'string' ? e.ha_entity_type : null,
      label: typeLabel(e.ha_entity_type),
      entity_id: typeof e.ha_default_entity_id === 'string' && e.ha_default_entity_id ? e.ha_default_entity_id : null,
      unique_id: typeof e.ha_unique_id === 'string' && e.ha_unique_id ? e.ha_unique_id : null,
      controllable: controllable,
      verbs: controllable === true ? verbsOf(e.ha_capabilities) : [],
      publish: e.will_publish === true,
    };
  }

  // Repli sans le Lot 3 : une vue de décision (`auto` / `overridden`) → au plus une ligne, sans identifiant.
  function viewLine(view) {
    var d = M().readDiagnosticView(view);
    if (d === null || !d.ha_entity_type) return null;
    return {
      type: d.ha_entity_type, label: typeLabel(d.ha_entity_type), entity_id: null, unique_id: null,
      controllable: null, verbs: [], publish: M().isReadyDiagnostic(view),
    };
  }

  // Côté de l'aperçu : seules les entités publiées existent dans Home Assistant.
  function side(lines) {
    var published = lines.filter(function (line) { return line && line.publish; });
    var counts = {};
    var order = [];
    published.forEach(function (line) {
      var key = line.type || '';
      if (!Object.prototype.hasOwnProperty.call(counts, key)) { counts[key] = 0; order.push(key); }
      counts[key] += 1;
    });
    var parts = order.map(function (type) {
      var noun = TYPE_NOUNS[type];
      var n = counts[type];
      if (!noun) return n + ' ' + plural(n, 'entité', 'entités') + ' ' + typeLabel(type);
      return n + ' ' + plural(n, noun.one, noun.many);
    });
    return {
      published: published,
      headline: published.length === 0 ? 'Non publié' : parts.join(', '),
      empty: published.length === 0,
    };
  }

  function refusalText(view) {
    var d = M().readDiagnosticView(view);
    if (d === null) return 'le plugin n’a pas pu évaluer ce choix';
    var label = M().buildBlockingReason(view);
    if (!label) {
      var l = lx();
      var code = d.publication_reason || d.validity_reason_code || d.reason_code;
      var sheet = l && code && typeof l.causeSheet === 'function' ? l.causeSheet(code) : null;
      label = sheet && sheet.known ? sheet.quoi : '';
    }
    return label || 'le plugin refuse ce type pour cette commande';
  }

  /**
   * Aperçu avant / après à partir de la réponse de `previewMappingOverride` (corps ajax complet ou `payload`).
   * Rend { ok, publishable, refusal, before, after, changes, removed, source } :
   * - `publishable` : vrai seulement si la vue « après » de la commande est publiable (même règle que l'ancien
   *   enregistrement automatique, `shouldAutoValidate`) ; sinon `refusal` dit pourquoi en clair ;
   * - `before` / `after` : { headline, published: [ligne], empty } ;
   * - `changes` : identifiants qui changent ({ from, to }), `removed` : identifiants qui disparaissent ;
   * - `source` : 'entities' (Lot 3) ou 'views' (repli).
   */
  function buildDiff(response) {
    var p = readPayload(response);
    if (p === null) {
      return { ok: false, publishable: false, refusal: 'réponse du plugin illisible', before: side([]), after: side([]), changes: [], removed: [], source: null };
    }
    var covered = p.covered !== false;
    var over = covered && isObject(p.overridden) ? p.overridden : null;
    var withEntities = Array.isArray(p.entities_before);
    var beforeLines = withEntities
      ? p.entities_before.filter(isObject).map(entityLine)
      : [viewLine(p.auto)].filter(Boolean);
    var afterLines;
    if (Array.isArray(p.entities_after)) afterLines = p.entities_after.filter(isObject).map(entityLine);
    else if (over) afterLines = [viewLine(over)].filter(Boolean);
    else afterLines = beforeLines.slice();
    var publishable = covered && over !== null && M().shouldAutoValidate(over);
    var refusal = null;
    if (!covered) refusal = 'cette commande n’a pas d’équivalent dans Home Assistant';
    else if (!publishable) refusal = refusalText(over);
    var changes = [];
    var removed = [];
    (Array.isArray(p.entity_id_changes) ? p.entity_id_changes : []).forEach(function (c) {
      if (!isObject(c)) return;
      var from = typeof c.from === 'string' && c.from ? c.from : null;
      var to = typeof c.to === 'string' && c.to ? c.to : null;
      if (from && to && from !== to) changes.push({ from: from, to: to });
      else if (from && !to) removed.push(from);
    });
    return {
      ok: true,
      publishable: publishable,
      refusal: refusal,
      before: side(beforeLines),
      after: side(publishable ? afterLines : []),
      changes: publishable ? changes : [],
      removed: publishable ? removed : [],
      source: withEntities ? 'entities' : 'views',
    };
  }

  /** Mention de capacité d'une ligne : « pilotable (allumer, éteindre) », « lecture seule », ou '' si inconnue. */
  function capabilityText(line) {
    if (!line || line.controllable === null) return '';
    if (line.controllable === false) return 'lecture seule';
    return line.verbs.length ? 'pilotable (' + line.verbs.join(', ') + ')' : 'pilotable';
  }

  /** Bandeau de résultat après « Enregistrer et publier ». `type` null = retour en automatique. */
  function resultMessage(eqName, type) {
    var name = eqName || 'L’équipement';
    if (!type) return name + ' : le type est revenu en automatique.';
    var noun = TYPE_NOUNS[type];
    return noun
      ? name + ' est maintenant ' + noun.article + ' ' + noun.one + ' dans Home Assistant.'
      : name + ' est maintenant publié comme ' + typeLabel(type) + ' dans Home Assistant.';
  }

  /**
   * Ouvre le panneau (point d'entrée appelé par « Corriger le type… », Lot 2) : { eqId, cmdIds, $panel }.
   * Le rendu est fait par la surface ; rend `true` si le panneau a été ouvert.
   */
  function open(options) {
    var s = surface();
    if (!s || typeof s.openTypePanel !== 'function') return false;
    return s.openTypePanel(options || {}) === true;
  }

  return {
    version: 2,
    TYPE_NOUNS: TYPE_NOUNS,
    typeLabel: typeLabel,
    cellLabel: cellLabel,
    impossibleReason: impossibleReason,
    buildChoices: buildChoices,
    buildDiff: buildDiff,
    capabilityText: capabilityText,
    resultMessage: resultMessage,
    open: open,
  };
}));
