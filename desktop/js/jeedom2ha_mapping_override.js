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
      // CC-37 : le backend porte `covered` sur chaque ligne de l'arbre GET (voir
      // `http_server.py`), mais cette normalisation ne le recopiait pas — renderCommandRow
      // lisait `row.covered === undefined`, jamais `=== false`, donc renderDiagnosticCell
      // retombait sur diagnosticState() (= 'blocking' pour command_not_covered) au lieu du
      // libellé « non couverte ». `null` si absent (démon plus ancien) préserve ce comportement.
      covered: typeof r.covered === 'boolean' ? r.covered : null,
      attendu_ha: typeof r.attendu_ha === 'string' && r.attendu_ha ? r.attendu_ha : null,
      effective_ha: typeof r.effective_ha === 'string' && r.effective_ha ? r.effective_ha : null,
      override_applied: overrideApplied,
      // D11 : override_source n'existe que quand override_applied === true.
      override_source: overrideApplied && typeof r.override_source === 'string' ? r.override_source : null,
      diagnostic: r.diagnostic != null ? r.diagnostic : null,
    };
  }

  // Story 19.3 (AC6) — état sync vs override courant : distingue la dernière décision
  // synchronisée (`app["publications"]`, MQTT) de l'état courant recalculé avec les
  // overrides actifs. `override_pending` signale un override qui n'a pas encore été
  // republié (l'utilisateur doit resynchroniser pour que Home Assistant reflète le
  // changement).
  function normalizeSyncStatus(raw) {
    var s = raw || {};
    return {
      synced_should_publish: typeof s.synced_should_publish === 'boolean' ? s.synced_should_publish : null,
      current_should_publish: typeof s.current_should_publish === 'boolean' ? s.current_should_publish : null,
      override_pending: s.override_pending === true,
    };
  }

  function normalizeTree(payload) {
    var p = payload || {};
    var commands = Array.isArray(p.commands) ? p.commands : [];
    return {
      jeedom_eq_id: p.jeedom_eq_id != null ? p.jeedom_eq_id : null,
      eq_name: typeof p.eq_name === 'string' ? p.eq_name : '',
      mapped: p.mapped === true,
      equipment_decision: p.equipment_decision || null,
      entities: (Array.isArray(p.entities) ? p.entities : []).map(function (entity) {
        var e = entity || {};
        return {
          ha_entity_type: typeof e.ha_entity_type === 'string' ? e.ha_entity_type : null,
          command_ids: Array.isArray(e.command_ids) ? e.command_ids.slice() : [],
          decision: e.decision || null,
          // Story 20-2 (P1, relecture ClaudeBox) : le démon résout un override de publication
          // en 'exclude_eqlogic', 'exclude_command' ou 'force_publish' (jamais le littéral
          // 'exclude' — celui-ci n'existe que côté action demandée par l'utilisateur). Garder
          // les 3 valeurs réelles ici : les aplatir vers 'exclude'/'force_publish' faisait
          // disparaître toute exclusion à la lecture (publicationActionState la voyait comme
          // absente), rendant « Exclure » actif et « Revenir au mode automatique » grisé sur
          // une entité pourtant déjà exclue.
          publication_override: e.publication_override === 'exclude_eqlogic'
            || e.publication_override === 'exclude_command'
            || e.publication_override === 'force_publish'
            ? e.publication_override : null,
          reason_details: e.reason_details && typeof e.reason_details === 'object' ? e.reason_details : {},
          override_command_id: Number.isInteger(e.override_command_id) ? e.override_command_id : null,
          override_pending: e.override_pending === true,
        };
      }),
      // Ordre natif préservé strictement (AC3 : pas de tri/regroupement front).
      commands: commands.map(normalizeCommandRow),
      sync_status: normalizeSyncStatus(p.sync_status),
    };
  }

  // Story 20-2 (P2, relecture ClaudeBox) : résout les identifiants de commande en noms
  // lus dans `commands[]` (ordre natif GET arbre), sans aucun appel réseau supplémentaire.
  // Identifiant introuvable (commande hors arbre courant) : fallback `#id`, jamais vide.
  function resolveCommandNames(commands, commandIds) {
    var cmds = Array.isArray(commands) ? commands : [];
    var ids = Array.isArray(commandIds) ? commandIds : [];
    return ids.map(function (id) {
      for (var i = 0; i < cmds.length; i++) {
        if (cmds[i] && cmds[i].jeedom_cmd_id === id && typeof cmds[i].cmd_name === 'string' && cmds[i].cmd_name) {
          return cmds[i].cmd_name;
        }
      }
      return '#' + id;
    });
  }

  // Story 20-2 : données d'action lues telles quelles dans l'arbre, sans inférence sur
  // les commandes ni recalcul de décision côté client. `commands` (arbre GET) est
  // optionnel : sans lui, fallback sur les identifiants bruts (rétro-compat).
  function entityCommandsLabel(entity, commands) {
    var ids = entity && Array.isArray(entity.command_ids) ? entity.command_ids : [];
    if (!ids.length) {
      return 'Aucune commande regroupée';
    }
    return 'Commandes : ' + resolveCommandNames(commands, ids).join(', ');
  }

  // Story 20-2 (P2, relecture ClaudeBox) : chaque bouton porte sa propre cause de
  // désactivation (pas une cause générique partagée), lue uniquement dans l'arbre déjà
  // reçu — aucune décision n'est recalculée côté client.
  function publicationActionState(target, equipment) {
    var t = target || {};
    var decision = t.decision || t;
    var hasKey = equipment === true || Number.isInteger(t.override_command_id);
    var policy = t.publication_override || null;
    // Story 20-2 (P1) : les deux valeurs d'exclusion résolues par le démon désignent toutes
    // deux une entité déjà exclue, qu'elle le soit via l'équipement ou via sa commande.
    var excluded = policy === 'exclude_eqlogic' || policy === 'exclude_command';
    var forced = policy === 'force_publish';
    if (!hasKey) {
      var noKeyReason = 'Aucune commande clé propre à cette entité.';
      return {
        can_exclude: false, can_force: false, can_revert: false,
        exclude_reason: noKeyReason, force_reason: noKeyReason, revert_reason: noKeyReason,
        reason: noKeyReason,
      };
    }
    var pv = decision.projection_validity || {};
    var excludeReason = excluded ? 'Entité déjà exclue de Home Assistant.' : null;
    var forceReason = null;
    if (forced) {
      forceReason = 'Publication déjà forcée sur cette entité.';
    } else if (decision.should_publish === true) {
      forceReason = 'Déjà publiée : forcer n’a pas d’effet.';
    } else if (!decision.ha_entity_type) {
      forceReason = 'Aucun mapping trouvé pour cette entité.';
    } else if (HA_ENTITY_TYPE_OPTIONS.indexOf(decision.ha_entity_type) === -1) {
      forceReason = 'Type HA hors périmètre de ce plugin.';
    } else if (pv.is_valid === false) {
      forceReason = 'Projection invalide pour ce type HA.';
    }
    var revertReason = (policy === null && t.has_publication_override !== true)
      ? 'Aucun override de publication à retirer.' : null;
    return {
      can_exclude: !excluded,
      can_force: forceReason === null,
      can_revert: revertReason === null,
      exclude_reason: excludeReason,
      force_reason: forceReason,
      revert_reason: revertReason,
      // Rétro-compat : première cause non nulle, pour les appelants n'ayant pas encore
      // adopté les champs par bouton.
      reason: excludeReason || forceReason || revertReason,
    };
  }

  function shouldConfirmPublication(policy, decision) {
    return policy === 'exclude' && decision && decision.should_publish === true;
  }

  // Story 20-2 (P2, relecture ClaudeBox AC3) : contenu de l'aperçu de forçage, lu
  // strictement dans la réponse du démon (`previewMappingOverride`) — type, validité de
  // projection, et commandes qui recevront les ordres (`view.command_ids`, uniquement
  // peuplé par le démon quand `proposed_policy === 'force_publish'`). Si le forçage serait
  // refusé (projection invalide ou publication toujours non déclenchée), `can_confirm` est
  // faux et `refusal_reason` porte la cause lisible — à l'appelant de désactiver la
  // confirmation en conséquence.
  function forcePreviewState(view, commands) {
    var d = readDiagnosticView(view);
    var ids = (view && Array.isArray(view.command_ids)) ? view.command_ids : [];
    var commandNames = resolveCommandNames(commands, ids);
    if (d === null) {
      return {
        ha_entity_type: null, is_valid: false, will_publish: false, command_names: commandNames,
        can_confirm: false, refusal_reason: 'Aperçu indisponible — réponse du démon inattendue.',
      };
    }
    var canConfirm = d.is_valid && d.should_publish;
    return {
      ha_entity_type: d.ha_entity_type,
      is_valid: d.is_valid,
      will_publish: d.should_publish,
      command_names: commandNames,
      can_confirm: canConfirm,
      refusal_reason: canConfirm ? null : buildBlockingReason(view),
    };
  }

  // Story 19.3 (AC6) — l'accordéon pièce doit afficher un badge quand l'état courant
  // (overrides actifs) diverge de la dernière décision synchronisée vers Home Assistant.
  function shouldShowOverridePendingBadge(tree) {
    return normalizeTree(tree).sync_status.override_pending === true;
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

  // Extrait la vue overridée BRUTE d'une réponse de preview (dry-run).
  // Renvoie l'objet `overridden` tel quel (mêmes clés que le contrat backend / que
  // `row.diagnostic` du GET arbre), directement consommable par diagnosticState /
  // buildPublishCellLabel / shouldAutoValidate — qui appliquent readDiagnosticView
  // eux-mêmes. Ne JAMAIS pré-aplatir ici : un double readDiagnosticView perdrait
  // `projection_validity` (→ is_valid=false → toujours « ne sera pas publié », #869).
  function readPreviewOverridden(payload) {
    var p = (payload && payload.payload) ? payload.payload : payload;
    if (!p || typeof p !== 'object' || !p.overridden || typeof p.overridden !== 'object') {
      return null;
    }
    return p.overridden;
  }

  // Story 16.8 — couverture d'une commande : le backend répond `covered:false` quand la
  // commande ciblée n'est couverte NI par le mapping primaire NI par un capteur secondaire.
  // Défaut `true` (rétro-compat : un backend antérieur sans le champ signifie « couvert »).
  function readPreviewCovered(payload) {
    var p = (payload && payload.payload) ? payload.payload : payload;
    if (!p || typeof p !== 'object') {
      return true;
    }
    return p.covered !== false;
  }

  // Story 16.8 (AC12 « jamais vide ») — libellé de la cellule diagnostic pour une commande
  // non couverte : elle n'a aucun mapping à projeter, donc rien ne sera publié. Message
  // factuel (jamais vide, jamais un flash vert trompeur, jamais un code HTTP).
  function buildUncoveredLabel() {
    return 'Ne sera pas publié — commande non couverte par un mapping';
  }

  // Story 19.3 (P1, relecture ClaudeBox PR #176 tour 2) — décide si `covered:false` doit
  // afficher le libellé générique « non couverte » (buildUncoveredLabel) ou le VRAI
  // diagnostic (buildPublishCellLabel). Avant ce correctif, `covered:false` masquait
  // systématiquement la cause réelle : une commande exclue/désactivée en amont (I1/I4)
  // affichait « non couverte par un mapping », un mensonge sur la vraie raison. Le seul
  // cas où le générique reste correct est l'absence de diagnostic (`view === null`) ou
  // `publication_reason === 'command_not_covered'` — un `CommandDecision` explicite
  // signalant qu'AUCUN mapping (primaire ni secondaire) ne couvre cette commande.
  function shouldShowUncoveredLabel(view) {
    var d = readDiagnosticView(view);
    if (d === null) {
      return true;
    }
    return d.publication_reason === 'command_not_covered';
  }

  // Story 19.3 (P1) — extrait la vue `auto` BRUTE d'une réponse de preview (dry-run), miroir
  // de `readPreviewOverridden` pour la branche `!covered` (Story 19.3, correction relecture
  // ClaudeBox PR #176 tour 2) : avant ce correctif, l'appelant ignorait `payload.auto` sur
  // une commande non couverte et rendait la cellule avec `view=null`, perdant tout
  // diagnostic réel (raison d'inéligibilité amont) au profit du libellé générique.
  function readPreviewAuto(payload) {
    var p = (payload && payload.payload) ? payload.payload : payload;
    if (!p || typeof p !== 'object' || !p.auto || typeof p.auto !== 'object') {
      return null;
    }
    return p.auto;
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
    name_heuristic_rejection: 'un mot du nom de l’équipement écarte ce type',
    duplicate_generic_types: 'types génériques en double',
    switch_state_orphan: 'état sans ordre On/Off',
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
    // Story 19.3 (AC4) — raisons exposées par le branchement sur evaluate_equipment().
    no_mapping: 'aucun mapping trouvé pour cette commande',
    skipped_no_mapping_candidate: 'aucun candidat de mapping à valider',
    ha_component_not_in_product_scope: 'type HA non ouvert par ce plugin',
    sure_mapping: 'mapping direct — publication normale',
    publication_excluded_eqlogic: 'exclu manuellement (équipement)',
    publication_excluded_command: 'exclu manuellement (commande)',
    publication_forced: 'publication forcée manuellement',
    // Story 19.3 (AC1/AC7) — le branchement sur evaluate_equipment() fait aussi remonter
    // les raisons d'inéligibilité amont (Story 4.3) jusqu'au diagnostic par commande,
    // là où la surface ignorait jusqu'ici ces cas (CC-03).
    command_not_covered: 'commande non couverte par ce mapping',
    excluded_eqlogic: 'exclu de Jeedom2HA (équipement dans la liste d’exclusions)',
    excluded_plugin: 'exclu de Jeedom2HA (plugin source dans la liste d’exclusions)',
    excluded_object: 'exclu de Jeedom2HA (pièce dans la liste d’exclusions)',
    no_commands: 'aucune commande configurée dans Jeedom',
  };

  // CC-38 : une exclusion volontaire est un état produit distinct, pas une erreur à corriger.
  // Elle doit rester visible dans la synthèse sans déclencher badge bloquant ni ancre.
  var EXCLUDED_PUBLICATION_REASONS = [
    'excluded_eqlogic',
    'excluded_plugin',
    'excluded_object',
    'publication_excluded_eqlogic',
    'publication_excluded_command',
  ];

  // Story 16.8 — raison de blocage concise pour la cellule diagnostic du tableau.
  function buildBlockingReason(view) {
    var d = readDiagnosticView(view);
    if (d === null) {
      return '';
    }
    // Priorité : cause de décision > cause de validité > symptôme brut.
    // `ambiguous_skipped` est le résultat de publication générique ; la cause précise
    // est portée par le mapping dans `reason_code` et doit donc passer avant lui.
    var preciseAmbiguity = ['name_heuristic_rejection', 'duplicate_generic_types', 'switch_state_orphan'];
    var candidates = d.publication_reason === 'ambiguous_skipped' && preciseAmbiguity.indexOf(d.reason_code) !== -1
      ? [d.reason_code, d.publication_reason, d.validity_reason_code]
      : [d.publication_reason, d.reason_code, d.validity_reason_code];
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

  function isExcludedDiagnostic(view) {
    var d = readDiagnosticView(view);
    return d !== null && EXCLUDED_PUBLICATION_REASONS.indexOf(d.publication_reason) !== -1;
  }

  function buildExcludedLabel(view) {
    var d = readDiagnosticView(view);
    return 'Ne sera pas publié — ' + REASON_LABELS[d.publication_reason];
  }

  // Story 20.1 : un équipement désactivé est un état neutre, distinct d'une
  // exclusion et d'un blocage actionnable. Le démon reste la seule source.
  function isDisabledDiagnostic(view) {
    var d = readDiagnosticView(view);
    return d !== null && d.publication_reason === 'disabled_eqlogic';
  }

  function buildDisabledLabel(view) {
    return isDisabledDiagnostic(view) ? 'Ne sera pas publié — équipement désactivé dans Jeedom' : '—';
  }

  function getOverrideSelectorState(row) {
    var r = normalizeCommandRow(row);
    if (isExcludedDiagnostic(r.diagnostic)) {
      return { active: false, reason: 'Commande exclue de Jeedom2HA : son type HA ne peut pas être réglé ici.' };
    }
    if (isDisabledDiagnostic(r.diagnostic)) {
      return { active: false, reason: 'Équipement désactivé dans Jeedom : son type HA ne peut pas être réglé ici.' };
    }
    if (r.covered === false && shouldShowUncoveredLabel(r.diagnostic)) {
      return { active: false, reason: 'Aucun mapping ne couvre cette commande : son type HA ne peut pas être réglé ici.' };
    }
    return { active: true, reason: null };
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

  // Story 16.8 (AC9/AC10, parcours navigateur du 2026-10-01) — une commande non couverte
  // par le mapping (`publication_reason === 'command_not_covered'`, décision propre à la
  // commande) n'est ni prête ni bloquante : elle n'est simplement pas projetée, et rien
  // n'est à corriger sur elle. Elle est comptée à part et ne reçoit jamais l'ancre
  // « première commande bloquante ». Avant ce correctif, « Rafraichir » de l'eq 391 faisait
  // afficher « Partiellement publié » à un équipement bel et bien publié.
  function isUncoveredDiagnostic(view) {
    var d = readDiagnosticView(view);
    return d !== null && d.publication_reason === 'command_not_covered';
  }

  function summarizePublication(tree) {
    var t = normalizeTree(tree);
    var ready = 0;
    var blocking = 0;
    var unknown = 0;
    var uncovered = 0;
    var excluded = 0;
    var disabled = 0;
    var firstBlockingCmdId = null;
    for (var i = 0; i < t.commands.length; i++) {
      var row = t.commands[i];
      if (isUncoveredDiagnostic(row.diagnostic)) {
        uncovered += 1;
        continue;
      }
      if (isExcludedDiagnostic(row.diagnostic)) {
        excluded += 1;
        continue;
      }
      if (isDisabledDiagnostic(row.diagnostic)) {
        disabled += 1;
        continue;
      }
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
      uncovered_count: uncovered,
      excluded_count: excluded,
      disabled_count: disabled,
      will_publish: ready > 0,
      first_blocking_cmd_id: firstBlockingCmdId,
    };
  }

  // Libellé factuel « sera publié / ne sera pas publié » + compte prêtes/bloquantes (AC9/AC10).
  function buildPublicationSummaryLabel(summary) {
    var s = summary || {};
    var ready = s.ready_count || 0;
    var blocking = s.blocking_count || 0;
    var excluded = s.excluded_count || 0;
    var disabled = s.disabled_count || 0;
    if (ready === 0 && blocking === 0 && excluded > 0) {
      return 'Exclu : ne sera pas publié dans Home Assistant.';
    }
    if (ready === 0 && blocking === 0 && disabled > 0) {
      return 'Désactivé dans Jeedom : ne sera pas publié dans Home Assistant.';
    }
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
    var excluded = s.excluded_count || 0;
    var disabled = s.disabled_count || 0;
    if (ready === 0 && blocking === 0 && excluded > 0) {
      return 'excluded';
    }
    if (ready === 0 && blocking === 0 && disabled > 0) {
      return 'disabled';
    }
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
      if (isUncoveredDiagnostic(row.diagnostic) || isExcludedDiagnostic(row.diagnostic) || isDisabledDiagnostic(row.diagnostic)) {
        continue;
      }
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
    resolveCommandNames: resolveCommandNames,
    entityCommandsLabel: entityCommandsLabel,
    publicationActionState: publicationActionState,
    shouldConfirmPublication: shouldConfirmPublication,
    forcePreviewState: forcePreviewState,
    buildEmptyStateLabel: buildEmptyStateLabel,
    readDiagnosticView: readDiagnosticView,
    readPreviewOverridden: readPreviewOverridden,
    readPreviewAuto: readPreviewAuto,
    readPreviewCovered: readPreviewCovered,
    buildUncoveredLabel: buildUncoveredLabel,
    shouldShowUncoveredLabel: shouldShowUncoveredLabel,
    diagnosticState: diagnosticState,
    isReadyDiagnostic: isReadyDiagnostic,
    isBlockingDiagnostic: isBlockingDiagnostic,
    shouldAutoValidate: shouldAutoValidate,
    collectRefusalReasons: collectRefusalReasons,
    buildDiagnosticMessage: buildDiagnosticMessage,
    buildBlockingReason: buildBlockingReason,
    buildPublishCellLabel: buildPublishCellLabel,
    isExcludedDiagnostic: isExcludedDiagnostic,
    buildExcludedLabel: buildExcludedLabel,
    isDisabledDiagnostic: isDisabledDiagnostic,
    buildDisabledLabel: buildDisabledLabel,
    getOverrideSelectorState: getOverrideSelectorState,
    initReassuranceState: initReassuranceState,
    shouldShowReassurance: shouldShowReassurance,
    markReassuranceShown: markReassuranceShown,
    collectBlockingCommandIds: collectBlockingCommandIds,
    normalizeRoomsTree: normalizeRoomsTree,
    summarizePublication: summarizePublication,
    buildPublicationSummaryLabel: buildPublicationSummaryLabel,
    publicationSummaryState: publicationSummaryState,
    shouldShowOverridePendingBadge: shouldShowOverridePendingBadge,
  };

  return api;
}));
