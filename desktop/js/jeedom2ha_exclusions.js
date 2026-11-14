// Front v2 — Lot 6 : exclusion unifiée (E6) et confirmations chiffrées (E9).
//
// Partie PURE (testée sous node) : modèle des trois portées d'exclusion, effet réel de chaque équipement, différence chiffrée
// d'un lot de changements, écritures à envoyer (routes et paramètres EXISTANTS, corps inchangés), écritures inverses (annuler)
// et textes des confirmations. Partie navigateur : le panneau « Choisir ce qui est publié… » (rendu, cases, pied en direct).
// Les écritures elles-mêmes, la réservation des actions et l'unique relecture sont dans jeedom2ha.js.
//
// Règle de priorité (celle de l'extraction du plugin, core/class/jeedom2ha.class.php « eqlogic > plugin > object », puis du
// démon : models/topology.py assess_eligibility, models/decide_publication.py) :
//   1. ancien réglage d'équipement `jeedom2ha_excluded` (aucun écran ne l'écrit : affiché, jamais modifié ici) ;
//   2. plugin exclu (`excludedPlugins`) ;
//   3. pièce exclue (`excludedObjects`), SAUF un équipement actif exposé à HomeKit (exception 24.4, même règle que la
//      confirmation d'exclusion de pièce de jeedom2ha_overview.js) ; la pièce ne s'applique qu'à SES équipements : ses
//      sous-pièces ne sont pas entraînées ; « Sans pièce » (identifiant 0) n'est jamais excluable ;
//   4. réglage « Jamais » de l'équipement (`savePublicationOverride` exclude), évalué après l'éligibilité.
// Un réglage « Jamais » masqué par un plugin ou une pièce exclus n'est pas visible dans la lecture agrégée : il est alors
// supposé absent (la relecture qui suit l'application dit la vérité).
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory(require('./jeedom2ha_mapping_override.js'));
    return;
  }
  root.Jeedom2haExclusions = factory(root.Jeedom2haMappingOverride);
}(typeof globalThis !== 'undefined' ? globalThis : this, function (M) {
  'use strict';

  var has = function (obj, key) { return !!obj && Object.prototype.hasOwnProperty.call(obj, key); };

  function plural(n, one, many) { return n + ' ' + (n > 1 ? many : one); }
  function eqWord(n) { return plural(n, '{{équipement}}', '{{équipements}}'); }
  function entWord(n) { return plural(n, '{{entité}}', '{{entités}}'); }

  // --- Lecture des réglages ---

  /** `excludedPlugins` (CSV) lu avec la règle de l'extraction : `trim`, doublons et vides retirés, ordre conservé. */
  function parsePluginList(csv) {
    var out = [];
    String(csv === undefined || csv === null ? '' : csv).split(',').forEach(function (token) {
      var id = token.trim();
      if (id !== '' && out.indexOf(id) === -1) out.push(id);
    });
    return out;
  }

  /** Nouvelle valeur de `excludedPlugins` : l'ordre existant est gardé (y compris les plugins absents de la page), les ajouts
   * vont à la fin. */
  function serializePluginList(baseCsv, changes) {
    var list = parsePluginList(baseCsv);
    Object.keys(changes || {}).forEach(function (id) {
      var at = list.indexOf(id);
      if (changes[id] === true && at === -1) list.push(id);
      if (changes[id] === false && at !== -1) list.splice(at, 1);
    });
    return list.join(',');
  }

  function decisionReason(entry) {
    var d = M && typeof M.readDiagnosticView === 'function' ? M.readDiagnosticView(entry && entry.equipment_decision) : null;
    return d ? d.publication_reason : null;
  }

  function commandReasons(entry) {
    var out = [];
    (entry && Array.isArray(entry.commands) ? entry.commands : []).forEach(function (row) {
      var d = M && typeof M.readDiagnosticView === 'function' ? M.readDiagnosticView(row && row.diagnostic) : null;
      if (d && d.publication_reason && out.indexOf(d.publication_reason) === -1) out.push(d.publication_reason);
    });
    return out;
  }

  /**
   * Réglage propre de l'équipement, lu dans l'entrée agrégée (aucune lecture de plus) :
   * { own: 'legacy' | 'never' | 'always' | 'auto', known: boolean } ; `known` est faux quand une exclusion de plugin ou de pièce
   * masque le réglage, ou quand l'équipement n'a pas été lu.
   */
  function ownPolicyOf(entry) {
    if (!entry || typeof entry !== 'object') return { own: 'auto', known: false };
    var reason = decisionReason(entry);
    var cmds = commandReasons(entry);
    var only = function (code) { return reason === code || (reason === null && cmds.length === 1 && cmds[0] === code); };
    if (only('excluded_eqlogic')) return { own: 'legacy', known: true };
    if (only('publication_excluded_eqlogic')) return { own: 'never', known: true };
    if (only('excluded_plugin') || only('excluded_object')) return { own: 'auto', known: false };
    if (reason === 'publication_forced' || cmds.indexOf('publication_forced') !== -1) return { own: 'always', known: true };
    return { own: 'auto', known: true };
  }

  /** Exception HomeKit (24.4) : un équipement actif, exposé à HomeKit, sans règle propre de périmètre, reste publié malgré sa
   * pièce exclue. Même règle que `roomExclusionImpact` (jeedom2ha_overview.js). */
  function homekitKept(entry, enabled) {
    if (enabled === false || !entry || typeof entry !== 'object') return false;
    return entry.homekit_kept_in_excluded_room === true || (entry.homekit_exposed_effective === true && entry.scope_inherit === true);
  }

  function readView(snapshot) {
    var view = snapshot && snapshot.view;
    var equipments = view && view.equipments && typeof view.equipments === 'object' ? view.equipments : null;
    return {
      equipments: equipments,
      known: !!(snapshot && snapshot.kind === 'ok' && view && view.stale !== true && equipments),
      overview: view && view.overview ? view.overview : null,
    };
  }

  // --- Modèle ---

  /**
   * @param {Array} roomsTree `j2haRoomsTree` ; @param {object} snapshot `page.snapshot()` ; @param {string} excludedPlugins CSV
   * @param {object} pluginNames `j2haPluginNames`
   */
  function buildModel(roomsTree, snapshot, excludedPlugins, pluginNames) {
    var names = pluginNames && typeof pluginNames === 'object' ? pluginNames : {};
    var view = readView(snapshot);
    var excludedList = parsePluginList(excludedPlugins);
    var model = {
      known: view.known, rooms: [], plugins: [], eqs: {}, order: [],
      base: { pluginsCsv: String(excludedPlugins === undefined || excludedPlugins === null ? '' : excludedPlugins), plugins: {}, rooms: {} },
    };
    var rooms = Array.isArray(roomsTree) ? roomsTree : [];
    var fathers = {};
    rooms.forEach(function (room) { if (room && room.father_id) fathers[room.father_id] = true; });
    var pluginIndex = {};
    rooms.forEach(function (room) {
      if (!room) return;
      var id = Number(room.object_id) || 0;
      var node = {
        id: id, name: String(room.object_name === undefined ? '' : room.object_name), excludable: id > 0,
        excluded: id > 0 && room.excluded === true, hasChildren: id > 0 && fathers[id] === true, eqIds: [],
      };
      model.base.rooms[id] = node.excluded;
      (Array.isArray(room.equipments) ? room.equipments : []).forEach(function (eq) {
        var eqId = Number(eq.eq_id);
        var entry = view.equipments && has(view.equipments, String(eqId)) ? view.equipments[String(eqId)] : null;
        var policy = ownPolicyOf(entry);
        var present = 0;
        var unknown = 0;
        (entry && Array.isArray(entry.entities) ? entry.entities : []).forEach(function (e) {
          if (e && e.present_in_ha === true) present += 1;
          else if (!e || typeof e.present_in_ha !== 'boolean') unknown += 1;
        });
        var plugin = typeof eq.eq_type === 'string' ? eq.eq_type : '';
        var state = entry && M && typeof M.resolveEquipmentState === 'function' ? M.resolveEquipmentState(entry, eq.enabled).state : null;
        model.eqs[eqId] = {
          id: eqId, name: String(eq.eq_name === undefined ? '' : eq.eq_name), roomId: id, plugin: plugin, enabled: eq.enabled,
          read: !!entry, own: policy.own, ownKnown: policy.known, homekit: homekitKept(entry, eq.enabled),
          present: present, unknownPresence: unknown, state: state,
        };
        model.order.push(eqId);
        node.eqIds.push(eqId);
        if (!has(pluginIndex, plugin)) {
          pluginIndex[plugin] = {
            id: plugin, name: plugin === '' ? '' : String(has(names, plugin) && names[plugin] ? names[plugin] : plugin),
            excludable: plugin !== '', excluded: plugin !== '' && excludedList.indexOf(plugin) !== -1, eqIds: [],
          };
          model.plugins.push(pluginIndex[plugin]);
          model.base.plugins[plugin] = pluginIndex[plugin].excluded;
        }
        pluginIndex[plugin].eqIds.push(eqId);
      });
      model.rooms.push(node);
    });
    model.plugins.sort(function (a, b) {
      if (a.id === '' || b.id === '') return a.id === '' ? 1 : -1;
      return a.name.localeCompare(b.name);
    });
    return model;
  }

  function emptyChanges() { return { plugins: {}, rooms: {}, eqs: {} }; }

  function pluginExcluded(model, changes, plugin) {
    if (plugin === '') return false;
    if (changes && has(changes.plugins, plugin)) return changes.plugins[plugin] === true;
    return model.base.plugins[plugin] === true;
  }
  function roomExcluded(model, changes, roomId) {
    if (!(roomId > 0)) return false;
    if (changes && has(changes.rooms, roomId)) return changes.rooms[roomId] === true;
    return model.base.rooms[roomId] === true;
  }
  /** Réglage propre après changements : 'never' (exclu lui-même) ou le réglage d'origine. */
  function ownAfter(model, changes, eq) {
    if (changes && has(changes.eqs, eq.id)) return changes.eqs[eq.id] === 'exclude' ? 'never' : (eq.own === 'never' ? 'auto' : eq.own);
    return eq.own;
  }

  /**
   * Effet réel d'un équipement, avant (`changes` absent) ou après les changements :
   * { excluded, reason: 'legacy' | 'plugin' | 'room' | 'self' | null, homekit: boolean (relevé de sa pièce exclue) }.
   */
  function effectOf(model, eqId, changes) {
    var eq = model.eqs[eqId];
    if (!eq) return { excluded: false, reason: null, homekit: false };
    if (eq.own === 'legacy') return { excluded: true, reason: 'legacy', homekit: false };
    if (pluginExcluded(model, changes, eq.plugin)) return { excluded: true, reason: 'plugin', homekit: false };
    var inRoom = roomExcluded(model, changes, eq.roomId);
    if (inRoom && !eq.homekit) return { excluded: true, reason: 'room', homekit: false };
    if (ownAfter(model, changes, eq) === 'never') return { excluded: true, reason: 'self', homekit: inRoom };
    return { excluded: false, reason: null, homekit: inRoom };
  }

  function roomOf(model, id) { return model.rooms.filter(function (r) { return r.id === id; })[0] || null; }
  function pluginOf(model, id) { return model.plugins.filter(function (p) { return p.id === id; })[0] || null; }

  /** Raison effective en clair : « Exclu : pièce Garage exclue », « Reste publié : exposé à HomeKit »… (chaîne vide sinon). */
  function reasonText(model, eqId, changes) {
    var eq = model.eqs[eqId];
    var effect = effectOf(model, eqId, changes);
    if (effect.reason === 'legacy') return '{{Exclu (ancien réglage)}}';
    if (effect.reason === 'plugin') {
      var p = pluginOf(model, eq.plugin);
      return '{{Exclu : plugin}} ' + (p ? p.name : eq.plugin) + ' {{exclu}}';
    }
    if (effect.reason === 'room') {
      var r = roomOf(model, eq.roomId);
      return '{{Exclu : pièce}} ' + (r ? r.name : '') + ' {{exclue}}';
    }
    if (effect.reason === 'self') return '{{Exclu : réglage « Jamais » de l\'équipement}}';
    if (effect.homekit) return '{{Reste publié : exposé à HomeKit}}';
    if (eq && eq.enabled === false) return '{{Désactivé dans Jeedom : jamais publié}}';
    return '';
  }

  /** Nombre de changements réellement en attente (un retour à l'état d'origine n'en est pas un). */
  function changeCount(model, changes) {
    var c = normalize(model, changes);
    return Object.keys(c.plugins).length + Object.keys(c.rooms).length + Object.keys(c.eqs).length;
  }

  /** Retire les changements qui reviennent à l'état d'origine (la case recochée efface son changement). */
  function normalize(model, changes) {
    var out = emptyChanges();
    // Seules les portées excluables comptent : jamais « Sans pièce » (0), jamais un plugin inconnu, jamais l'ancien réglage.
    Object.keys(changes.plugins || {}).forEach(function (id) {
      var p = pluginOf(model, id);
      if (p && p.excludable && changes.plugins[id] !== (model.base.plugins[id] === true)) out.plugins[id] = changes.plugins[id];
    });
    Object.keys(changes.rooms || {}).forEach(function (id) {
      var r = roomOf(model, Number(id));
      if (r && r.excludable && changes.rooms[id] !== (model.base.rooms[id] === true)) out.rooms[id] = changes.rooms[id];
    });
    Object.keys(changes.eqs || {}).forEach(function (id) {
      var eq = model.eqs[id];
      if (eq && eq.own !== 'legacy' && (changes.eqs[id] === 'exclude') !== (eq.own === 'never')) out.eqs[id] = changes.eqs[id];
    });
    return out;
  }

  /**
   * Différence chiffrée : équipements qui passent de publié à exclu (`removed`, avec les entités PRÉSENTES dans Home Assistant),
   * équipements qui ne sont plus exclus (`returned`). `entitiesKnown` est faux sans lecture valide.
   */
  function diff(model, changes) {
    var c = normalize(model, changes || emptyChanges());
    var out = {
      changes: changeCount(model, c), excluded: [], returned: [], removedEquipments: 0, removedEntities: 0,
      unknownEntities: 0, unread: 0, entitiesKnown: model.known,
    };
    model.order.forEach(function (id) {
      var before = effectOf(model, id, null);
      var after = effectOf(model, id, c);
      var eq = model.eqs[id];
      if (!before.excluded && after.excluded) {
        out.excluded.push(id);
        if (!eq.read) { out.unread += 1; return; }
        if (eq.present > 0) { out.removedEquipments += 1; out.removedEntities += eq.present; }
        out.unknownEntities += eq.unknownPresence;
      } else if (before.excluded && !after.excluded) {
        out.returned.push(id);
      }
    });
    // Revue Codex (#394, P2) : un équipement concerné non lu, ou dont la présence d'entités est inconnue, rend le nombre
    // d'entités INCONNU ; la confirmation reste alors destructive (rouge) et le dit.
    if (out.unread > 0 || out.unknownEntities > 0) out.entitiesKnown = false;
    out.undoBlocked = undoBlockers(model, c);
    return out;
  }

  /**
   * Équipements passés à « Jamais » dont l'annulation automatique ne rétablirait pas EXACTEMENT l'état d'avant (revue Codex
   * #394, P2) : un « Toujours » lu (sa portée réelle, équipement ou commande, n'est pas donnée par la lecture agrégée) ou un
   * réglage propre illisible (équipement non lu). Ils sont annoncés avant d'appliquer et laissés hors de « Annuler ».
   */
  function undoBlockers(model, changes) {
    var out = [];
    Object.keys(changes.eqs || {}).forEach(function (id) {
      var eq = model.eqs[id];
      if (eq && changes.eqs[id] === 'exclude' && (eq.own === 'always' || !eq.ownKnown)) out.push(eq.id);
    });
    return out.sort(function (a, b) { return a - b; });
  }

  /** Écritures à envoyer, dans l'ordre : plugins (une écriture), pièces, équipements. Paramètres EXACTS des routes existantes. */
  function writesFor(model, changes, confidencePolicy) {
    var c = normalize(model, changes || emptyChanges());
    var writes = [];
    if (Object.keys(c.plugins).length > 0) {
      writes.push({
        kind: 'plugins',
        data: {
          action: 'saveFilteringConfig',
          excludedPlugins: serializePluginList(model.base.pluginsCsv, c.plugins),
          confidencePolicy: confidencePolicy === 'sure_only' ? 'sure_only' : 'sure_probable',
        },
      });
    }
    Object.keys(c.rooms).map(Number).sort(function (a, b) { return a - b; }).forEach(function (id) {
      writes.push({ kind: 'room', id: id, data: { action: 'saveRoomExclusion', objectId: String(id), excluded: c.rooms[id] ? '1' : '0' } });
    });
    Object.keys(c.eqs).map(Number).sort(function (a, b) { return a - b; }).forEach(function (id) {
      if (c.eqs[id] === 'exclude') {
        writes.push({ kind: 'eq', id: id, data: { action: 'savePublicationOverride', eqId: id, publicationPolicy: 'exclude' } });
      } else {
        // Revue Codex (#394, P1) : `scope: 'equipment'` ne retire que le réglage « Jamais » de l'équipement ; sans lui, la
        // route purge aussi les réglages des commandes (types HA corrigés). Nouveau cas, corps existants inchangés.
        writes.push({ kind: 'eq', id: id, data: { action: 'revertPublicationOverride', eqId: id, scope: 'equipment' } });
      }
    });
    return writes;
  }

  /** Écritures inverses (« Annuler » du bandeau) : la valeur d'origine de `excludedPlugins` est rendue telle quelle ; une
   * exclusion d'équipement retire seulement le « Jamais » posé (`scope: 'equipment'`, réglages des commandes intacts). Les
   * équipements de `undoBlockers` (« Toujours » de portée inconnue, réglage illisible) ne sont PAS rejoués : annoncés. */
  function inverseWrites(model, changes, confidencePolicy) {
    var c = normalize(model, changes || emptyChanges());
    var writes = [];
    if (Object.keys(c.plugins).length > 0) {
      writes.push({ kind: 'plugins', data: { action: 'saveFilteringConfig', excludedPlugins: model.base.pluginsCsv, confidencePolicy: confidencePolicy === 'sure_only' ? 'sure_only' : 'sure_probable' } });
    }
    Object.keys(c.rooms).map(Number).sort(function (a, b) { return a - b; }).forEach(function (id) {
      writes.push({ kind: 'room', id: id, data: { action: 'saveRoomExclusion', objectId: String(id), excluded: c.rooms[id] ? '0' : '1' } });
    });
    Object.keys(c.eqs).map(Number).sort(function (a, b) { return a - b; }).forEach(function (id) {
      var eq = model.eqs[id];
      if (c.eqs[id] === 'include') {
        writes.push({ kind: 'eq', id: id, data: { action: 'savePublicationOverride', eqId: id, publicationPolicy: 'exclude' } });
      } else if (eq.own !== 'always' && eq.ownKnown) {
        writes.push({ kind: 'eq', id: id, data: { action: 'revertPublicationOverride', eqId: id, scope: 'equipment' } });
      }
    });
    return writes;
  }

  // --- Textes du pied et des boutons (E6) ---

  function footText(d) {
    if (d.changes === 0) return '';
    var parts = [plural(d.changes, '{{changement}}', '{{changements}}')];
    if (d.excluded.length > 0) {
      if (!d.entitiesKnown) {
        parts.push(eqWord(d.excluded.length) + ' ' + (d.excluded.length > 1 ? '{{seront exclus}}' : '{{sera exclu}}') + ' {{(nombre d\'entités inconnu pour l\'instant)}}');
      } else if (d.removedEquipments > 0) {
        parts.push(eqWord(d.removedEquipments) + ' ' + (d.removedEquipments > 1 ? '{{seront retirés de Home Assistant}}' : '{{sera retiré de Home Assistant}}') + ' (' + entWord(d.removedEntities) + ')');
        if (d.excluded.length > d.removedEquipments) {
          var rest = d.excluded.length - d.removedEquipments;
          parts.push(eqWord(rest) + ' ' + (rest > 1 ? '{{non publiés seront exclus}}' : '{{non publié sera exclu}}'));
        }
      } else {
        parts.push(eqWord(d.excluded.length) + ' ' + (d.excluded.length > 1 ? '{{seront exclus (aucune entité publiée)}}' : '{{sera exclu (aucune entité publiée)}}'));
      }
    }
    if (d.returned.length > 0) parts.push(d.returned.length + ' ' + (d.returned.length > 1 ? '{{ne seront plus exclus}}' : '{{ne sera plus exclu}}'));
    if (d.undoBlocked && d.undoBlocked.length > 0) parts.push(undoBlockedText(d.undoBlocked.length));
    return parts.join(' · ');
  }

  /** Annonce (pied et bandeau) des équipements que « Annuler » ne rétablira pas. */
  function undoBlockedText(n) {
    return eqWord(n) + ' ' + (n > 1 ? '{{à rétablir depuis leur fiche si besoin : « Annuler » ne reprend pas leur réglage précédent}}' : '{{à rétablir depuis sa fiche si besoin : « Annuler » ne reprend pas son réglage précédent}}');
  }

  /** Bouton d'application : rouge dès qu'une entité part, vert sinon. { label, danger, disabled } */
  function applyButton(d) {
    if (d.changes === 0) return { label: '{{Appliquer}}', danger: false, disabled: true };
    if (d.excluded.length > 0 && !d.entitiesKnown) return { label: '{{Appliquer — exclure}} ' + eqWord(d.excluded.length), danger: true, disabled: false };
    if (d.removedEntities > 0) return { label: '{{Appliquer — retirer}} ' + entWord(d.removedEntities), danger: true, disabled: false };
    if (d.returned.length > 0 && d.excluded.length === 0) return { label: '{{Appliquer — publier}} ' + eqWord(d.returned.length), danger: false, disabled: false };
    return { label: '{{Appliquer}}', danger: false, disabled: false };
  }

  /** Bandeau de résultat : « 7 équipements exclus » / « 2 équipements ne sont plus exclus ». */
  function resultText(d) {
    var parts = [];
    if (d.excluded.length > 0) parts.push(eqWord(d.excluded.length) + ' ' + (d.excluded.length > 1 ? '{{exclus}}' : '{{exclu}}'));
    if (d.returned.length > 0) parts.push(eqWord(d.returned.length) + ' ' + (d.returned.length > 1 ? '{{ne sont plus exclus}}' : '{{n\'est plus exclu}}'));
    return parts.length ? parts.join(' · ') : '{{Réglages enregistrés}}';
  }

  // --- Confirmations chiffrées (E9) : nombres lus dans la copie des états déjà en mémoire, jamais une requête ---

  /** Équipements publiés et entités présentes dans Home Assistant (toute la maison, ou une pièce). */
  function presence(snapshot, roomsTree, roomId) {
    var view = readView(snapshot);
    var out = { known: view.known, equipments: 0, entities: 0, published: 0 };
    if (!view.known) return out;
    var ids = null;
    if (roomId !== undefined && roomId !== null) {
      ids = {};
      (Array.isArray(roomsTree) ? roomsTree : []).forEach(function (room) {
        if (room && room.object_id === roomId) (room.equipments || []).forEach(function (eq) { ids[String(eq.eq_id)] = true; });
      });
    }
    Object.keys(view.equipments).forEach(function (key) {
      if (ids && !ids[key]) return;
      var entry = view.equipments[key];
      var n = 0;
      (entry && Array.isArray(entry.entities) ? entry.entities : []).forEach(function (e) { if (e && e.present_in_ha === true) n += 1; });
      if (n > 0) { out.equipments += 1; out.entities += n; }
      if (entry && entry.sync_status && entry.sync_status.published_in_ha === true) out.published += 1;
    });
    if (!ids && view.overview && view.overview.counts && typeof view.overview.counts.published === 'number') out.published = view.overview.counts.published;
    return out;
  }

  function pendingCount(snapshot) {
    var view = readView(snapshot);
    return view.known && view.overview && view.overview.counts ? (view.overview.counts.to_apply || 0) : null;
  }

  var UNKNOWN_LINE = '{{Nombre d\'entités inconnu pour l\'instant : la lecture des états n\'est pas disponible.}}';

  /** « Supprimer tout de Home Assistant » : { title, lines[], confirmLabel } (lignes en texte brut, échappées au rendu). */
  function deleteAllDialog(snapshot) {
    var p = presence(snapshot);
    var lines = [];
    if (!p.known) lines.push(UNKNOWN_LINE);
    else if (p.entities === 0) lines.push('{{Aucune entité n\'est publiée dans Home Assistant pour l\'instant.}}');
    else lines.push(eqWord(p.equipments) + ' (' + entWord(p.entities) + ') ' + (p.equipments > 1 ? '{{seront retirés de Home Assistant.}}' : '{{sera retiré de Home Assistant.}}'));
    lines.push('{{L\'historique, les tableaux de bord et les automatisations qui les utilisent seront touchés.}}');
    lines.push('{{Rien n\'est recréé automatiquement : utilisez « Republier tout » pour les remettre. Cette action ne s\'annule pas.}}');
    return {
      title: '{{Supprimer tout de Home Assistant}}', lines: lines,
      confirmLabel: p.known && p.entities > 0 ? '{{Supprimer}} ' + entWord(p.entities) : '{{Supprimer tout}}',
    };
  }

  /** « Republier tout » : bouton chiffré par le nombre d'équipements publiés. */
  function republishAllDialog(snapshot) {
    var p = presence(snapshot);
    var lines = [];
    if (p.known) lines.push('{{Renvoie les}} ' + eqWord(p.published) + ' ' + (p.published > 1 ? '{{publiés}}' : '{{publié}}') + ' {{à Home Assistant, sans relire Jeedom.}}');
    else lines.push('{{Renvoie les équipements publiés à Home Assistant, sans relire Jeedom.}}');
    lines.push('{{Utile si Home Assistant a perdu ses appareils.}}');
    var pending = pendingCount(snapshot);
    if (pending > 0) lines.push(plural(pending, '{{réglage en attente sera aussi appliqué.}}', '{{réglages en attente seront aussi appliqués.}}'));
    return { title: '{{Republier tout}}', lines: lines, confirmLabel: p.known ? '{{Republier}} ' + eqWord(p.published) : '{{Republier tout}}' };
  }

  /** « Republier la pièce » (menu de carte). */
  function republishRoomDialog(snapshot, roomsTree, roomId, roomName) {
    var p = presence(snapshot, roomsTree, roomId);
    var lines = [];
    if (p.known) lines.push('{{Renvoie les}} ' + eqWord(p.published) + ' ' + (p.published > 1 ? '{{publiés}}' : '{{publié}}') + ' {{de cette pièce à Home Assistant, sans relire Jeedom.}}');
    else lines.push('{{Renvoie les équipements publiés de cette pièce à Home Assistant, sans relire Jeedom.}}');
    return { title: '{{Republier la pièce}} « ' + String(roomName === undefined ? '' : roomName) + ' »', lines: lines, confirmLabel: p.known ? '{{Republier}} ' + eqWord(p.published) : '{{Republier la pièce}}' };
  }

  /** « Relire Jeedom » : annonce les réglages en attente (règle 5 : effets globaux annoncés). */
  function rescanDialog(snapshot) {
    var lines = ['{{Le plugin relit vos équipements et met Home Assistant à jour.}}'];
    var pending = pendingCount(snapshot);
    if (pending > 0) lines.push('{{D\'après la dernière lecture :}} ' + plural(pending, '{{réglage en attente sera appliqué.}}', '{{réglages en attente seront appliqués.}}'));
    lines.push('{{Rien n\'est supprimé sans que vous l\'ayez exclu.}}');
    return { title: '{{Relire Jeedom}}', lines: lines, confirmLabel: '{{Relire Jeedom}}' };
  }

  // --- Panneau (navigateur) ---

  var STATE_CLASS = { published: 'is-ok', to_apply: 'is-todo', blocked: 'is-warn', excluded: 'is-off', disabled: 'is-off', nothing_to_publish: 'is-off' };

  /**
   * @param {object} env { $, bootbox, rooms, snapshot(), excludedPlugins(), pluginNames, apply(writes, info) }
   *   `apply` reçoit les écritures et { model, changes, diff } ; il rend false si une opération est déjà en cours.
   */
  function createPanel(env) {
    var $ = env.$;

    function open(opts) {
      var o = opts || {};
      var model = buildModel(env.rooms(), env.snapshot(), env.excludedPlugins(), env.pluginNames);
      var changes = emptyChanges();
      var mode = o.mode === 'plugin' ? 'plugin' : 'room';
      var expanded = {};
      if (o.roomId !== undefined && o.roomId !== null) expanded['room:' + o.roomId] = true;
      if (o.eqId !== undefined && o.eqId !== null && model.eqs[o.eqId]) expanded['room:' + model.eqs[o.eqId].roomId] = true;

      var $root = $('<div class="j2ha-v2 j2ha-v2-excl"></div>');
      $root.append($('<p class="j2ha-v2-small"></p>').text('{{Tout est publié par défaut. Décochez ce que vous ne voulez pas voir dans Home Assistant.}}'));
      var $seg = $('<div class="j2ha-v2-seg j2ha-v2-excl-mode" role="group"></div>').attr('aria-label', '{{Regrouper}}');
      var $byRoom = $('<button type="button" data-mode="room"></button>').text('{{Par pièce}}');
      var $byPlugin = $('<button type="button" data-mode="plugin"></button>').text('{{Par plugin}}');
      $seg.append($byRoom).append($byPlugin);
      $root.append($seg);
      $root.append($('<p class="j2ha-v2-small j2ha-v2-muted j2ha-v2-excl-rule"></p>').text('{{Un équipement est publié s\'il n\'est exclu ni lui-même, ni par sa pièce, ni par son plugin.}}'));
      if (!model.known) $root.append($('<div class="j2ha-v2-alert is-warn j2ha-v2-excl-unknown"></div>').text(UNKNOWN_LINE));
      var $tree = $('<div class="j2ha-v2-tree j2ha-v2-excl-tree" role="tree"></div>');
      $root.append($tree);
      var $sum = $('<span class="j2ha-v2-grow j2ha-v2-excl-sum" role="status" aria-live="polite"></span>');
      var $cancel = $('<button type="button" class="btn btn-default btn-sm j2ha-v2-excl-cancel"></button>').text('{{Annuler}}');
      var $apply = $('<button type="button" class="btn btn-sm j2ha-v2-excl-apply"></button>');
      $root.append($('<div class="j2ha-v2-foot"></div>').append($sum).append($cancel).append($apply));

      var dialog = env.bootbox.dialog({
        title: '{{Choisir ce qui est publié dans Home Assistant}}', message: $root, onEscape: true, backdrop: true, size: 'large',
        className: 'j2ha-v2-excl-dialog',
      });
      function close() { if (dialog && typeof dialog.modal === 'function') dialog.modal('hide'); else if (dialog && typeof dialog.remove === 'function') dialog.remove(); }

      function setRoom(id, excluded) { changes.rooms[id] = excluded; changes = normalize(model, changes); }
      function setPlugin(id, excluded) { changes.plugins[id] = excluded; changes = normalize(model, changes); }
      function setEq(id, excluded) { changes.eqs[id] = excluded ? 'exclude' : 'include'; changes = normalize(model, changes); }

      function checkbox(checked, mixed, disabled, label) {
        var $cb = $('<input type="checkbox" class="j2ha-v2-excl-cb">').attr('aria-label', label);
        $cb.prop('checked', !!checked);
        $cb.prop('indeterminate', !!mixed);
        $cb.attr('aria-checked', mixed ? 'mixed' : (checked ? 'true' : 'false'));
        if (disabled) $cb.prop('disabled', true);
        return $cb;
      }

      function eqLine(id, level) {
        var eq = model.eqs[id];
        var before = effectOf(model, id, null);
        var after = effectOf(model, id, changes);
        var masked = after.reason === 'plugin' || after.reason === 'room' || after.reason === 'legacy';
        var $n = $('<div class="j2ha-v2-tree-node j2ha-v2-excl-eq" role="treeitem"></div>').addClass(level).attr('data-eq-id', String(id));
        var $cb = checkbox(!after.excluded, false, masked, '{{Publier}} ' + eq.name);
        if (!masked) $cb.on('change', function () { setEq(id, !$cb.prop('checked')); render(); });
        $n.append($cb);
        $n.append($('<span class="j2ha-free-name"></span>').toggleClass('j2ha-v2-muted', after.excluded).text(eq.name));
        if (eq.state && M && M.EQUIPMENT_STATE_LABELS) {
          $n.append($('<span class="j2ha-v2-lbl"></span>').addClass(STATE_CLASS[eq.state] || 'is-off').text(M.EQUIPMENT_STATE_LABELS[eq.state] || ''));
        } else if (!eq.read) {
          $n.append($('<span class="j2ha-v2-lbl is-off"></span>').text('{{Non lu}}'));
        }
        var why = reasonText(model, id, changes);
        if (why) $n.append($('<span class="j2ha-v2-small j2ha-v2-muted j2ha-v2-excl-why"></span>').text(why));
        if (!before.excluded && after.excluded) {
          $n.addClass('j2ha-v2-changed');
          $n.append($('<span class="j2ha-v2-small j2ha-v2-excl-change"></span>').text('→ {{sera exclu}}' + (eq.present > 0 ? ' · ' + entWord(eq.present) + ' ' + (eq.present > 1 ? '{{retirées}}' : '{{retirée}}') : '')));
        } else if (before.excluded && !after.excluded) {
          $n.addClass('j2ha-v2-changed');
          $n.append($('<span class="j2ha-v2-small j2ha-v2-excl-change"></span>').text('→ {{ne sera plus exclu}}'));
        }
        return $n;
      }

      function groupLine(kind, node) {
        var key = kind + ':' + node.id;
        var excludedAfter = kind === 'room' ? roomExcluded(model, changes, node.id) : pluginExcluded(model, changes, node.id);
        var excludedBefore = kind === 'room' ? model.base.rooms[node.id] === true : model.base.plugins[node.id] === true;
        var count = node.eqIds.length;
        var publishedAfter = node.eqIds.filter(function (id) { return !effectOf(model, id, changes).excluded; }).length;
        var mixed = !excludedAfter && publishedAfter < count;
        var label = kind === 'room' ? node.name : (node.id === '' ? '{{Plugin inconnu}}' : node.name);
        var $n = $('<div class="j2ha-v2-tree-node j2ha-v2-excl-group" role="treeitem"></div>').attr('data-kind', kind).attr('data-id', String(node.id));
        var isOpen = expanded[key] === true;
        $n.attr('aria-expanded', isOpen ? 'true' : 'false');
        var $twisty = $('<button type="button" class="j2ha-v2-excl-twisty"></button>')
          .attr('aria-expanded', isOpen ? 'true' : 'false').attr('aria-label', (isOpen ? '{{Replier}} ' : '{{Déplier}} ') + label)
          .append($('<span aria-hidden="true"></span>').text(isOpen ? '▾' : '▸'));
        $twisty.on('click', function () { expanded[key] = !isOpen; render(); });
        $n.append($twisty);
        var $cb = checkbox(!excludedAfter, mixed, !node.excludable, (kind === 'room' ? '{{Publier la pièce}} ' : '{{Publier le plugin}} ') + label);
        if (node.excludable) {
          $cb.on('change', function () {
            if (kind === 'room') setRoom(node.id, !excludedAfter); else setPlugin(node.id, !excludedAfter);
            render();
          });
        }
        $n.append($cb);
        $n.append($('<b class="j2ha-free-name"></b>').text(label));
        if (excludedAfter) $n.append($('<span class="j2ha-v2-lbl is-off"></span>').text(kind === 'room' ? '{{Exclue}}' : '{{Exclu}}'));
        // Front v2 (Lot 9a, regard neuf v2) : « non exclu » ne veut pas dire « publié » : les désactivés dans Jeedom sont dits.
        var disabledKept = node.eqIds.filter(function (id) { return !effectOf(model, id, changes).excluded && model.eqs[id].enabled === false; }).length;
        $n.append($('<span class="j2ha-v2-small j2ha-v2-muted j2ha-v2-excl-count"></span>').text(eqWord(count) + ' · ' + publishedAfter + ' ' + (publishedAfter > 1 ? '{{non exclus}}' : '{{non exclu}}')
          + (disabledKept > 0 ? ' ' + (disabledKept > 1 ? '{{dont}} ' + disabledKept + ' {{désactivés dans Jeedom}}' : '{{dont 1 désactivé dans Jeedom}}') : '')));
        // Par plugin : la ligne dit LESQUELS sont exclus (sans avoir à déplier un plugin de quarante équipements).
        if (kind === 'plugin' && !excludedAfter) {
          var excludedNames = node.eqIds.filter(function (id) { return effectOf(model, id, changes).excluded; }).map(function (id) { return model.eqs[id].name; });
          if (excludedNames.length > 0) {
            var shown = excludedNames.slice(0, 3).join(', ') + (excludedNames.length > 3 ? ' {{et}} ' + (excludedNames.length - 3) + ' {{autres}}' : '');
            $n.append($('<span class="j2ha-v2-small j2ha-v2-muted j2ha-v2-excl-names"></span>').text((excludedNames.length > 1 ? '{{Exclus :}} ' : '{{Exclu :}} ') + shown));
          }
        }
        if (kind === 'room' && !node.excludable) $n.append($('<span class="j2ha-v2-small j2ha-v2-muted"></span>').text('{{Sans pièce ne peut pas être exclue en bloc}}'));
        if (kind === 'room' && node.hasChildren) $n.append($('<span class="j2ha-v2-small j2ha-v2-muted"></span>').text('{{Exclure une pièce n\'exclut pas ses sous-pièces}}'));
        if (excludedAfter !== excludedBefore) {
          var local = diff(model, (function () { var c = emptyChanges(); if (kind === 'room') c.rooms[node.id] = excludedAfter; else c.plugins[node.id] = excludedAfter; return c; })());
          var text = excludedAfter
            ? '→ ' + (kind === 'room' ? '{{sera exclue}}' : '{{sera exclu}}') + ' · ' + eqWord(local.excluded.length) + (local.entitiesKnown ? ', ' + entWord(local.removedEntities) + ' ' + (local.removedEntities > 1 ? '{{retirées}}' : '{{retirée}}') : '')
            : '→ ' + (kind === 'room' ? '{{ne sera plus exclue}}' : '{{ne sera plus exclu}}') + ' · ' + eqWord(local.returned.length);
          $n.addClass('j2ha-v2-changed');
          $n.append($('<span class="j2ha-v2-small j2ha-v2-excl-change"></span>').text(text));
        }
        var $wrap = $('<div class="j2ha-v2-excl-node"></div>').append($n);
        if (isOpen) node.eqIds.forEach(function (id) { $wrap.append(eqLine(id, 'is-l2')); });
        return $wrap;
      }

      function render() {
        $byRoom.toggleClass('is-on', mode === 'room').attr('aria-pressed', mode === 'room' ? 'true' : 'false');
        $byPlugin.toggleClass('is-on', mode === 'plugin').attr('aria-pressed', mode === 'plugin' ? 'true' : 'false');
        $tree.empty();
        (mode === 'room' ? model.rooms : model.plugins).forEach(function (node) { $tree.append(groupLine(mode, node)); });
        var d = diff(model, changes);
        var text = footText(d);
        if (!text) {
          var nothing = model.order.every(function (id) { return !effectOf(model, id, null).excluded; });
          text = nothing ? '{{Rien n\'est exclu : tout ce que le plugin reconnaît est publié.}}' : '{{Aucun changement.}}';
        }
        $sum.text(text);
        var b = applyButton(d);
        $apply.text(b.label).toggleClass('btn-danger', b.danger).toggleClass('btn-success', !b.danger).prop('disabled', b.disabled);
      }

      $byRoom.on('click', function () { mode = 'room'; render(); });
      $byPlugin.on('click', function () { mode = 'plugin'; render(); });
      $cancel.on('click', function () { close(); });
      $apply.on('click', function () {
        var d = diff(model, changes);
        if (d.changes === 0) return;
        var writes = writesFor(model, changes, env.confidencePolicy ? env.confidencePolicy() : 'sure_probable');
        if (env.apply(writes, { model: model, changes: changes, diff: d }) !== false) close();
      });
      render();
      if (o.eqId !== undefined && o.eqId !== null) {
        var $target = $tree.find('.j2ha-v2-excl-eq[data-eq-id="' + o.eqId + '"] .j2ha-v2-excl-cb');
        if ($target.length) $target.focus();
      } else if (o.roomId !== undefined && o.roomId !== null) {
        var $room = $tree.find('.j2ha-v2-excl-group[data-kind="room"][data-id="' + o.roomId + '"] .j2ha-v2-excl-cb');
        if ($room.length) $room.focus();
      }
      return { dialog: dialog, model: model, changes: function () { return changes; }, render: render, root: $root };
    }

    return { open: open };
  }

  return {
    version: 2,
    parsePluginList: parsePluginList,
    serializePluginList: serializePluginList,
    ownPolicyOf: ownPolicyOf,
    homekitKept: homekitKept,
    buildModel: buildModel,
    emptyChanges: emptyChanges,
    normalize: normalize,
    effectOf: effectOf,
    reasonText: reasonText,
    diff: diff,
    writesFor: writesFor,
    inverseWrites: inverseWrites,
    undoBlockers: undoBlockers,
    undoBlockedText: undoBlockedText,
    footText: footText,
    applyButton: applyButton,
    resultText: resultText,
    presence: presence,
    deleteAllDialog: deleteAllDialog,
    republishAllDialog: republishAllDialog,
    republishRoomDialog: republishRoomDialog,
    rescanDialog: rescanDialog,
    createPanel: createPanel,
  };
}));
