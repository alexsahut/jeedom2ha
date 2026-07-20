/* Story 16.5 — Logique pure de l'onglet « HA / jeedom2ha » (triptyque override par commande).
 *
 * Aucune logique métier réinventée : lecture stricte du contrat backend
 * (GET /system/mapping_overrides/{eq_id} + POST /system/overrides/preview) avec
 * fallbacks bornés. Le `generic_type` natif est traité en lecture seule (D10) — ce
 * module ne l'écrit jamais. Séparé du contrôleur navigateur pour testabilité node.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
    return;
  }
  root.Jeedom2haMappingOverride = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  // Types HA proposables dans la colonne override (alignés sur les mappers du moteur).
  var HA_ENTITY_TYPE_OPTIONS = [
    'alarm_control_panel',
    'binary_sensor',
    'button',
    'climate',
    'cover',
    'light',
    'sensor',
    'switch',
  ];

  function getHaEntityTypeOptions() {
    return HA_ENTITY_TYPE_OPTIONS.slice();
  }

  // --- Normalisation de l'arbre GET (une ligne par commande, ordre natif Jeedom) ---

  function normalizeCommandRow(row) {
    var r = row || {};
    var overrideApplied = r.override_applied === true;
    return {
      jeedom_cmd_id: r.jeedom_cmd_id != null ? r.jeedom_cmd_id : null,
      cmd_name: typeof r.cmd_name === 'string' ? r.cmd_name : '',
      generic_type: typeof r.generic_type === 'string' && r.generic_type ? r.generic_type : null,
      coverable: r.coverable === true,
      attendu_ha: typeof r.attendu_ha === 'string' && r.attendu_ha ? r.attendu_ha : null,
      effective_ha: typeof r.effective_ha === 'string' && r.effective_ha ? r.effective_ha : null,
      override_applied: overrideApplied,
      // D11 : override_source n'existe que quand override_applied === true.
      override_source: overrideApplied && typeof r.override_source === 'string' ? r.override_source : null,
      diagnostic: r.diagnostic != null ? r.diagnostic : null,
    };
  }

  function normalizeTree(payload) {
    var p = payload || {};
    var commands = Array.isArray(p.commands) ? p.commands : [];
    return {
      jeedom_eq_id: p.jeedom_eq_id != null ? p.jeedom_eq_id : null,
      eq_name: typeof p.eq_name === 'string' ? p.eq_name : '',
      mapped: p.mapped === true,
      // Ordre natif préservé strictement (AC3 : pas de tri/regroupement front).
      commands: commands.map(normalizeCommandRow),
    };
  }

  // AC5 — état vide explicite : jamais un champ vide silencieux.
  function buildEmptyStateLabel(row) {
    var r = normalizeCommandRow(row);
    var attendu = r.effective_ha || r.attendu_ha;
    if (!attendu) {
      return 'Aucun override configuré — aucun type HA par défaut pour cette commande.';
    }
    return 'Aucun override configuré — voici ce qui sera utilisé par défaut : ' + attendu + '.';
  }

  // --- Lecture stricte d'une vue diagnostic (contrat _preview_mapping_view) ---

  function readDiagnosticView(view) {
    if (!view || typeof view !== 'object') {
      return null;
    }
    var pv = view.projection_validity || {};
    return {
      ha_entity_type: typeof view.ha_entity_type === 'string' ? view.ha_entity_type : null,
      reason_code: typeof view.reason_code === 'string' ? view.reason_code : null,
      is_valid: pv.is_valid === true,
      validity_reason_code: typeof pv.reason_code === 'string' ? pv.reason_code : null,
      missing_capabilities: Array.isArray(pv.missing_capabilities) ? pv.missing_capabilities.slice() : [],
      missing_fields: Array.isArray(pv.missing_fields) ? pv.missing_fields.slice() : [],
      should_publish: view.should_publish === true,
      publication_reason: typeof view.publication_reason === 'string' ? view.publication_reason : null,
    };
  }

  // Extrait la vue overridée d'une réponse de preview (dry-run).
  function readPreviewOverridden(payload) {
    var p = (payload && payload.payload) ? payload.payload : payload;
    if (!p || typeof p !== 'object') {
      return null;
    }
    return readDiagnosticView(p.overridden);
  }

  // État diagnostic : 'ready' (vert franc), 'blocking' (neutre actionnable), 'unknown'.
  function diagnosticState(view) {
    var d = readDiagnosticView(view);
    if (d === null) {
      return 'unknown';
    }
    return (d.is_valid && d.should_publish) ? 'ready' : 'blocking';
  }

  function isReadyDiagnostic(view) {
    return diagnosticState(view) === 'ready';
  }

  function isBlockingDiagnostic(view) {
    return diagnosticState(view) === 'blocking';
  }

  // AC9 — auto-validation : on ne persiste QUE quand le dry-run passe au vert franc.
  function shouldAutoValidate(overriddenView) {
    return isReadyDiagnostic(overriddenView);
  }

  // Raisons de refus, dédupliquées, pour un affichage actionnable (jamais une erreur réseau).
  function collectRefusalReasons(view) {
    var d = readDiagnosticView(view);
    if (d === null || (d.is_valid && d.should_publish)) {
      return [];
    }
    var reasons = [];
    function push(code) {
      if (code && reasons.indexOf(code) === -1) {
        reasons.push(code);
      }
    }
    if (!d.is_valid) {
      push(d.validity_reason_code);
    }
    if (!d.should_publish) {
      push(d.publication_reason);
    }
    return reasons;
  }

  // AC8 — message diagnostic. Vert : détail de ce qui a été validé. Bloquant : message
  // factuel actionnable (jamais rouge alarmant, jamais un code HTTP).
  function buildDiagnosticMessage(view) {
    var d = readDiagnosticView(view);
    if (d === null) {
      return '';
    }
    if (d.is_valid && d.should_publish) {
      var t = d.ha_entity_type || 'ce type';
      return 'Prêt : projetable en ' + t + ', publication Home Assistant validée.';
    }
    if (!d.is_valid && d.missing_capabilities.length > 0) {
      var caps = d.missing_capabilities.join(', ');
      return 'Capacité(s) manquante(s) pour ce type HA : ' + caps + '.';
    }
    if (!d.is_valid && d.missing_fields.length > 0) {
      var fields = d.missing_fields.join(', ');
      return 'Champ(s) requis manquant(s) pour ce type HA : ' + fields + '.';
    }
    var codes = collectRefusalReasons(view);
    if (codes.length > 0) {
      return 'Non projetable en l’état : ' + codes.join(', ') + '.';
    }
    return 'Non projetable en l’état pour ce type HA.';
  }

  // Story 16.8 — traduction des codes de refus backend en cause actionnable et lisible.
  // On surface la cause de décision (publication_reason / reason_code) AVANT le symptôme
  // de projection (command_topic manquant) : ex. un équipement « ambiguous_skipped » a
  // aussi command_topic manquant, mais la vraie action est de lever l'ambiguïté, pas de
  // chercher un topic. Libellés courts alignés sur les messages produit du daemon.
  var REASON_LABELS = {
    ambiguous_skipped: 'mapping ambigu — précisez les types génériques dans Jeedom',
    conflicting_generic_types: 'types génériques en conflit — précisez-les dans Jeedom',
    probable_skipped: 'confiance « probable » exclue par la politique « sûr uniquement »',
    disabled_eqlogic: 'équipement désactivé dans Jeedom',
    no_supported_generic_type: 'type non couvert par la V1 du plugin',
    no_generic_type_configured: 'types génériques non configurés dans Jeedom',
    no_projection_possible: 'aucune commande Info/Action exploitable',
    ha_missing_command_topic: 'commande non pilotable (pas d’ordre On/Off)',
    ha_missing_state_topic: 'pas de retour d’état exploitable',
    discovery_publish_failed: 'échec de publication MQTT au dernier sync',
    low_confidence: 'confiance insuffisante pour la politique active',
  };

  // Story 16.8 — raison de blocage concise pour la cellule diagnostic du tableau.
  function buildBlockingReason(view) {
    var d = readDiagnosticView(view);
    if (d === null) {
      return '';
    }
    // Priorité : cause de décision > cause de validité > symptôme brut.
    var candidates = [d.publication_reason, d.reason_code, d.validity_reason_code];
    for (var i = 0; i < candidates.length; i++) {
      var code = candidates[i];
      if (code && REASON_LABELS[code]) {
        return REASON_LABELS[code];
      }
    }
    if (d.missing_fields.length > 0) {
      return d.missing_fields.join(', ') + ' manquant';
    }
    if (d.missing_capabilities.length > 0) {
      return d.missing_capabilities.join(', ') + ' manquant';
    }
    var codes = collectRefusalReasons(view);
    return codes.length > 0 ? codes.join(', ') : '';
  }

  // Story 16.8 — libellé compact de la colonne diagnostic : « ce qui sera publié ».
  // Vert : « Sera publié : <type HA> ». Bloquant : « Ne sera pas publié — <raison> ».
  function buildPublishCellLabel(view) {
    var state = diagnosticState(view);
    if (state === 'ready') {
      var d = readDiagnosticView(view);
      return 'Sera publié : ' + ((d && d.ha_entity_type) || 'ce type');
    }
    if (state === 'blocking') {
      var reason = buildBlockingReason(view);
      return reason ? 'Ne sera pas publié — ' + reason : 'Ne sera pas publié';
    }
    return '—';
  }

  // --- AC14 — bandeau « aucun impact Homebridge » : une seule fois par équipement ---

  function initReassuranceState() {
    return { reassurance_shown: false };
  }

  function shouldShowReassurance(state, isBlocking) {
    if (!isBlocking) {
      return false;
    }
    var s = state || {};
    return s.reassurance_shown !== true;
  }

  function markReassuranceShown(state) {
    var s = state || {};
    return { reassurance_shown: true, _prev: s.reassurance_shown === true };
  }

  // --- Story 16.8 — Surface par pièce : normalisation de l'arbre pièce -> équipement ---

  function normalizeRoomEquipment(eq) {
    var e = eq || {};
    var id = e.eq_id != null ? parseInt(e.eq_id, 10) : NaN;
    return {
      eq_id: isNaN(id) ? null : id,
      eq_name: typeof e.eq_name === 'string' ? e.eq_name : '',
      enabled: e.enabled === true,
    };
  }

  function normalizeRoom(room) {
    var r = room || {};
    var oid = r.object_id != null ? parseInt(r.object_id, 10) : NaN;
    var eqs = Array.isArray(r.equipments) ? r.equipments : [];
    return {
      object_id: isNaN(oid) ? null : oid,
      object_name: typeof r.object_name === 'string' ? r.object_name : '',
      parent_number: typeof r.parent_number === 'number' ? r.parent_number : 0,
      // Équipements avec id valide uniquement ; ordre natif Jeedom préservé.
      equipments: eqs.map(normalizeRoomEquipment).filter(function (e) { return e.eq_id !== null; }),
    };
  }

  // Ordre natif préservé ; pièces sans équipement exploitable écartées (rien de cliquable à vide).
  function normalizeRoomsTree(payload) {
    var arr = Array.isArray(payload) ? payload : [];
    return arr.map(normalizeRoom).filter(function (r) {
      return r.object_id !== null && r.equipments.length > 0;
    });
  }

  // --- Story 16.8 / Bloc C — synthèse de publication par équipement ---
  // Agrégation strictement front à partir des diagnostics par commande déjà portés
  // par le GET arbre. « sera publié » = au moins une commande projetable+publiable.

  function summarizePublication(tree) {
    var t = normalizeTree(tree);
    var ready = 0;
    var blocking = 0;
    var unknown = 0;
    var firstBlockingCmdId = null;
    for (var i = 0; i < t.commands.length; i++) {
      var row = t.commands[i];
      var state = diagnosticState(row.diagnostic);
      if (state === 'ready') {
        ready += 1;
      } else if (state === 'blocking') {
        blocking += 1;
        if (firstBlockingCmdId === null) {
          firstBlockingCmdId = row.jeedom_cmd_id;
        }
      } else {
        unknown += 1;
      }
    }
    return {
      total: t.commands.length,
      ready_count: ready,
      blocking_count: blocking,
      unknown_count: unknown,
      will_publish: ready > 0,
      first_blocking_cmd_id: firstBlockingCmdId,
    };
  }

  // Libellé factuel « sera publié / ne sera pas publié » + compte prêtes/bloquantes (AC9/AC10).
  function buildPublicationSummaryLabel(summary) {
    var s = summary || {};
    var ready = s.ready_count || 0;
    var blocking = s.blocking_count || 0;
    if (ready === 0 && blocking === 0) {
      return 'Aucune commande projetable en Home Assistant pour cet équipement.';
    }
    if (s.will_publish && blocking === 0) {
      return 'Sera publié dans Home Assistant : ' + ready + ' commande(s) prête(s).';
    }
    if (s.will_publish && blocking > 0) {
      return 'Partiellement publié : ' + ready + ' prête(s), ' + blocking + ' bloquante(s).';
    }
    return 'Ne sera pas publié dans Home Assistant : ' + blocking + ' commande(s) bloquante(s).';
  }

  // État de synthèse pour le badge : 'publish', 'partial', 'blocked' (actionnable), 'empty'.
  function publicationSummaryState(summary) {
    var s = summary || {};
    var ready = s.ready_count || 0;
    var blocking = s.blocking_count || 0;
    if (ready === 0 && blocking === 0) {
      return 'empty';
    }
    if (ready > 0 && blocking === 0) {
      return 'publish';
    }
    if (ready > 0 && blocking > 0) {
      return 'partial';
    }
    return 'blocked';
  }

  // AC3.4 — commandes bloquantes détectées au GET initial, plafonnées (auto-ouverture).
  function collectBlockingCommandIds(tree, cap) {
    var t = normalizeTree(tree);
    var limit = (typeof cap === 'number' && cap > 0) ? cap : 4;
    var ids = [];
    for (var i = 0; i < t.commands.length && ids.length < limit; i++) {
      var row = t.commands[i];
      if (row.diagnostic != null && isBlockingDiagnostic(row.diagnostic)) {
        ids.push(row.jeedom_cmd_id);
      }
    }
    return ids;
  }

  var api = {
    HA_ENTITY_TYPE_OPTIONS: HA_ENTITY_TYPE_OPTIONS,
    getHaEntityTypeOptions: getHaEntityTypeOptions,
    normalizeCommandRow: normalizeCommandRow,
    normalizeTree: normalizeTree,
    buildEmptyStateLabel: buildEmptyStateLabel,
    readDiagnosticView: readDiagnosticView,
    readPreviewOverridden: readPreviewOverridden,
    diagnosticState: diagnosticState,
    isReadyDiagnostic: isReadyDiagnostic,
    isBlockingDiagnostic: isBlockingDiagnostic,
    shouldAutoValidate: shouldAutoValidate,
    collectRefusalReasons: collectRefusalReasons,
    buildDiagnosticMessage: buildDiagnosticMessage,
    buildBlockingReason: buildBlockingReason,
    buildPublishCellLabel: buildPublishCellLabel,
    initReassuranceState: initReassuranceState,
    shouldShowReassurance: shouldShowReassurance,
    markReassuranceShown: markReassuranceShown,
    collectBlockingCommandIds: collectBlockingCommandIds,
    normalizeRoomsTree: normalizeRoomsTree,
    summarizePublication: summarizePublication,
    buildPublicationSummaryLabel: buildPublicationSummaryLabel,
    publicationSummaryState: publicationSummaryState,
  };

  return api;
}));
