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

  // Story 22.2 (R2, AC6) — types proposés dans le sélecteur d'une commande : ceux que le démon dit
  // pouvoir aboutir, dans l'ordre de la liste d'interface ; un type DÉJÀ posé sur la commande reste
  // affiché (pour pouvoir revenir au mode automatique). Champ absent : liste complète d'avant.
  function getOverrideTypeOptions(row) {
    var r = normalizeCommandRow(row);
    if (r.override_types_allowed === null) {
      return HA_ENTITY_TYPE_OPTIONS.slice();
    }
    var options = HA_ENTITY_TYPE_OPTIONS.filter(function (t) { return r.override_types_allowed.indexOf(t) !== -1; });
    var current = r.override_applied ? r.effective_ha : null;
    if (current && options.indexOf(current) === -1) {
      options.push(current);
    }
    return options;
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
      // Story 22.2 (Q1 A) : commande portée par au moins une entité présente dans HA (champ
      // additif du démon) ; null = démon plus ancien (présence inconnue, jamais déduite).
      published_in_ha: typeof r.published_in_ha === 'boolean' ? r.published_in_ha : null,
      // Story 22.2 (R2, AC6) : types « Override HA » dont la projection est valide (champ additif du
      // démon). null = champ absent (démon plus ancien, ou commande non évaluable) : liste complète.
      override_types_allowed: Array.isArray(r.override_types_allowed)
        ? r.override_types_allowed.filter(function (t) { return typeof t === 'string'; }) : null,
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
      // R2-1 : présence réelle dans HA (champ additif du démon) ; null = démon plus ancien.
      published_in_ha: typeof s.published_in_ha === 'boolean' ? s.published_in_ha : null,
    };
  }

  function normalizeTree(payload) {
    var p = payload || {};
    var commands = Array.isArray(p.commands) ? p.commands : [];
    return {
      jeedom_eq_id: p.jeedom_eq_id != null ? p.jeedom_eq_id : null,
      eq_name: typeof p.eq_name === 'string' ? p.eq_name : '',
      mapped: p.mapped === true,
      // X6b (P2, relecture indépendante PR #215) : `eligible` et
      // `equipment_publication_override` sont deux champs additifs du démon (reprise AC8).
      // Un démon plus ancien ne les envoie pas : `eligible` retombe alors sur `true`
      // (comportement inchangé, jamais plus restrictif qu'avant), et l'override d'équipement
      // reste lu uniquement via les entités/commandes comme avant.
      eligible: p.eligible !== false,
      equipment_publication_override: p.equipment_publication_override === 'exclude'
        || p.equipment_publication_override === 'force_publish'
        ? p.equipment_publication_override : null,
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
          // absente), rendant « Jamais » actif et « Automatique » grisé sur
          // une entité pourtant déjà exclue.
          publication_override: e.publication_override === 'exclude_eqlogic'
            || e.publication_override === 'exclude_command'
            || e.publication_override === 'force_publish'
            ? e.publication_override : null,
          reason_details: e.reason_details && typeof e.reason_details === 'object' ? e.reason_details : {},
          override_command_id: Number.isInteger(e.override_command_id) ? e.override_command_id : null,
          override_pending: e.override_pending === true,
          // Story 22.2 (Q1 A) : présence réelle de cette entité dans HA (champ additif du démon).
          present_in_ha: typeof e.present_in_ha === 'boolean' ? e.present_in_ha : null,
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
    // X6b (P2, relecture indépendante PR #215) : un équipement INÉLIGIBLE (ex. eq 588-591,
    // `excluded_plugin`) n'a ni entité ni commande — `evaluate_equipment` refuse déjà toute
    // exclusion pour lui, donc « Jamais »/« Toujours » n'auraient aucun effet. Seule la portée
    // équipement est concernée (jamais l'entité, qui a sa propre éligibilité portée par
    // `decision`/`projection_validity`). « Automatique » reste actif si un
    // override d'équipement est déjà posé (AC1/AC6) — sinon il s'appliquerait en silence si
    // l'équipement redevenait éligible, sans que l'utilisateur puisse jamais le retirer.
    if (equipment === true && t.eligible === false) {
      var ineligibleOverride = t.has_publication_override === true;
      var ineligibleReason = 'Équipement non éligible : l’action serait sans effet.';
      var ineligibleRevertReason = ineligibleOverride ? null : 'Aucun réglage de publication à retirer.';
      return {
        can_exclude: false, can_force: false, can_revert: ineligibleOverride,
        exclude_reason: ineligibleReason, force_reason: ineligibleReason, revert_reason: ineligibleRevertReason,
        reason: ineligibleReason,
      };
    }
    // Story 20-2 (P2, revue ClaudeBox X4 point 4) : une entité qui hérite du veto
    // d'équipement ('exclude_eqlogic' sur une cible entité, pas la cible équipement elle-même)
    // n'a NI « Toujours » NI « Automatique » qui aient un sens à sa propre
    // portée — l'override vit sur l'équipement, pas sur cette commande. Les deux boutons
    // renvoient vers l'équipement plutôt que de tenter une action sans effet ou trompeuse.
    var inheritedEqExclusion = !equipment && policy === 'exclude_eqlogic';
    var pv = decision.projection_validity || {};
    var excludeReason = excluded ? 'Déjà réglé sur « Jamais ».' : null;
    if (inheritedEqExclusion) {
      var inheritedReason = 'Exclusion posée sur l’équipement : la retirer depuis l’équipement.';
      return {
        can_exclude: false, can_force: false, can_revert: false,
        exclude_reason: excludeReason, force_reason: inheritedReason, revert_reason: inheritedReason,
        reason: excludeReason || inheritedReason,
      };
    }
    var forceReason = null;
    if (forced) {
      forceReason = 'Déjà réglé sur « Toujours ».';
    } else if (decision.should_publish === true) {
      forceReason = 'Déjà publiée : « Toujours » n’aurait pas d’effet.';
    } else if (!decision.ha_entity_type) {
      forceReason = 'Aucun type Home Assistant identifié pour cette entité.';
    } else if (HA_ENTITY_TYPE_OPTIONS.indexOf(decision.ha_entity_type) === -1) {
      forceReason = 'Type HA hors périmètre de ce plugin.';
    } else if (pv.is_valid === false) {
      forceReason = 'Projection invalide pour ce type HA.';
    }
    var revertReason = (policy === null && t.has_publication_override !== true)
      ? 'Aucun réglage de publication à retirer.' : null;
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

  // X6b (P2, relecture indépendante PR #215) : construit la cible équipement passée à
  // `publicationActionState`, en lisant `eligible` et `equipment_publication_override` (tree
  // déjà normalisé) en plus du veto porté par les entités/commandes — remplace la construction
  // inline historique (surface) qui ignorait les deux champs additifs et laissait « Jamais »
  // actif sans effet sur un équipement inéligible, et « Revenir » grisé sans recours.
  function equipmentPublicationTarget(tree) {
    var t = tree || {};
    var entities = Array.isArray(t.entities) ? t.entities : [];
    var commands = Array.isArray(t.commands) ? t.commands : [];
    var eqExcludedViaEntity = entities.some(function (entity) {
      return entity.publication_override === 'exclude_eqlogic';
    });
    var hasTypeOverride = commands.some(function (cmd) { return cmd.override_applied; });
    var hasEntityPublicationOverride = entities.some(function (entity) {
      return entity.publication_override !== null;
    });
    var equipmentOverride = t.equipment_publication_override || null;
    var policy = null;
    if (eqExcludedViaEntity || equipmentOverride === 'exclude') {
      policy = 'exclude_eqlogic';
    } else if (equipmentOverride === 'force_publish') {
      policy = 'force_publish';
    }
    return {
      decision: t.equipment_decision,
      eligible: t.eligible !== false,
      publication_override: policy,
      has_publication_override: hasEntityPublicationOverride || hasTypeOverride || equipmentOverride !== null,
    };
  }

  function shouldConfirmPublication(policy, decision) {
    return policy === 'exclude' && decision && decision.should_publish === true;
  }

  // Story 20-2 (P2, relecture indépendante PR #210) : `shouldConfirmPublication` ne regarde
  // que la décision de l'équipement (entité principale) — un équipement dont l'entité
  // principale est non publiée mais dont une entité secondaire l'est (ex. capteurs de
  // conso) s'excluait donc sans confirmation. À la portée équipement, confirmer dès que
  // l'équipement OU au moins une entité (principale ou secondaire, `entities[]` de l'arbre
  // déjà reçu) est publiée.
  function shouldConfirmEquipmentExclude(equipmentDecision, entities) {
    if (equipmentDecision && equipmentDecision.should_publish === true) {
      return true;
    }
    return (Array.isArray(entities) ? entities : []).some(function (entity) {
      return entity && entity.decision && entity.decision.should_publish === true;
    });
  }

  // Liste des entités (principale et secondaires) qui quitteraient Home Assistant si
  // l'exclusion d'équipement était confirmée — pour l'affichage dans la modale (AC5).
  // Lecture pure de l'arbre déjà reçu, aucune décision recalculée ici.
  function entitiesLeavingHomeAssistant(entities, commands) {
    return (Array.isArray(entities) ? entities : [])
      .filter(function (entity) {
        return entity && entity.decision && entity.decision.should_publish === true;
      })
      .map(function (entity) {
        return {
          ha_entity_type: entity.ha_entity_type,
          command_names: resolveCommandNames(commands, entity.command_ids),
        };
      });
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

  // Deux listes de command_ids désignent la même entité seulement si elles portent
  // exactement le même ENSEMBLE d'identifiants (ordre indifférent) — un simple recoupement
  // partiel (ex. une commande d'action partagée entre entité principale et secondaire)
  // ne suffit pas et désignerait la mauvaise entité.
  function sameCommandIdSet(idsA, idsB) {
    if (idsA.length !== idsB.length) return false;
    return idsA.every(function (id) { return idsB.indexOf(id) !== -1; });
  }

  // Trouve, dans l'arbre déjà reçu (jamais recalculé ici), l'entité courante correspondant
  // à une entité de l'aperçu. Le démon rend les entités de l'arbre et de l'aperçu dans le
  // même ordre (principale, puis secondaires) avec les mêmes command_ids par entité — on
  // associe donc d'abord par ensemble de command_ids identique (robuste même si l'ordre
  // diffère), puis, à défaut, par même position avec le même ha_entity_type (seul repère
  // fiable quand deux entités partagent une commande d'action et n'ont donc pas de command_ids
  // strictement égaux). Une entité qui ne correspond sur aucun des deux critères est traitée
  // comme absente de l'arbre (non publiée), comme aujourd'hui.
  function findCurrentEntity(currentEntities, commandIds, index, haEntityType) {
    var ids = Array.isArray(commandIds) ? commandIds : [];
    var pool = Array.isArray(currentEntities) ? currentEntities : [];
    if (ids.length > 0) {
      for (var i = 0; i < pool.length; i++) {
        var currentIds = Array.isArray(pool[i].command_ids) ? pool[i].command_ids : [];
        if (sameCommandIdSet(ids, currentIds)) {
          return pool[i];
        }
      }
    }
    if (typeof index === 'number' && pool[index] && pool[index].ha_entity_type === haEntityType) {
      return pool[index];
    }
    return null;
  }

  // Story 20-2 (P2, relecture indépendante PR #210 ; reprise X5d, P3) : à la portée
  // équipement, le forçage s'étend à TOUTES les entités (`entities[]`, champ additif de
  // l'aperçu démon). Une entité DÉJÀ publiée (lue dans `currentEntities`, l'arbre déjà
  // reçu) et qui le resterait après forçage n'est pas un changement dû à CETTE action —
  // « Confirmer » ne doit s'activer que si au moins une entité PASSE de non publiée à
  // publiée. Chaque entité est donc classée « déjà publiée », « sera publiée » (ce
  // changement) ou « ne sera pas publiée : cause » (buildPublishCellLabel, même libellé
  // que la colonne diagnostic de l'arbre).
  function equipmentForcePreviewEntities(view, commands, currentEntities) {
    var entities = (view && Array.isArray(view.entities)) ? view.entities : [];
    return entities.map(function (entity, index) {
      var current = findCurrentEntity(currentEntities, entity.command_ids, index, entity.ha_entity_type);
      var alreadyPublished = !!(current && current.decision && current.decision.should_publish === true);
      var willPublish = isReadyDiagnostic(entity.decision);
      return {
        ha_entity_type: entity.ha_entity_type,
        command_names: resolveCommandNames(commands, entity.command_ids),
        already_published: alreadyPublished,
        changes: !alreadyPublished && willPublish,
        status_label: alreadyPublished ? 'Déjà publiée dans Home Assistant.'
          : (willPublish ? 'À appliquer dans Home Assistant.' : buildPublishCellLabel(entity.decision)),
      };
    });
  }

  function equipmentForcePreviewState(view, commands, currentEntities) {
    var items = equipmentForcePreviewEntities(view, commands, currentEntities);
    var canConfirm = items.some(function (item) { return item.changes; });
    return {
      items: items,
      can_confirm: canConfirm,
      refusal_reason: canConfirm
        ? null : 'Aucune entité ne changerait d’état : déjà publiées ou toujours non publiées.',
    };
  }

  // Story 19.3 (AC6) — l'accordéon pièce doit afficher un badge quand l'état courant
  // (overrides actifs) diverge de la dernière décision synchronisée vers Home Assistant.
  function shouldShowOverridePendingBadge(tree) {
    return normalizeTree(tree).sync_status.override_pending === true;
  }

  // Story 20-2 (P2, relecture ClaudeBox AC7) : badge « pas encore appliqué » par entité
  // (miroir du badge équipement existant, porté par `sync_status`) — une entité dont
  // l'override n'a pas encore été republié vers Home Assistant.
  function shouldShowEntityPendingBadge(entity) {
    return !!(entity && entity.override_pending === true);
  }

  // Story 20-2 (P2, relecture ClaudeBox) : lit une réponse AJAX `savePublicationOverride` /
  // `revertPublicationOverride` / `previewMappingOverride` / `executeHaAction` et renvoie un
  // message d'erreur lisible, ou `null` si la requête a réellement réussi. Le relais PHP
  // (`jeedom2ha::callDaemon`) lit le corps de la réponse daemon quel que soit son code HTTP
  // (y compris 409) : une erreur daemon (ex. commande partagée sans entité propre) remonte
  // donc avec `data.state === 'ok'` mais `data.result.status === 'error'` — jamais comme un
  // échec réseau jQuery. Ne JAMAIS recharger l'équipement sur ce chemin.
  function readPublicationRequestError(data) {
    if (!data || data.state !== 'ok') {
      var top = data && typeof data.result === 'string' && data.result;
      return top || 'La requête a échoué — réponse du serveur inattendue.';
    }
    var result = data.result;
    if (result && typeof result === 'object' && result.status === 'error') {
      return (typeof result.message === 'string' && result.message)
        ? result.message : 'La requête a été refusée par le démon.';
    }
    return null;
  }

  // AC5 — état vide explicite : jamais un champ vide silencieux.
  function buildEmptyStateLabel(row) {
    var r = normalizeCommandRow(row);
    var attendu = r.effective_ha || r.attendu_ha;
    if (!attendu) {
      return 'Aucun type imposé — aucun type HA automatique pour cette commande.';
    }
    return 'Aucun type imposé — type HA automatique : ' + attendu + '.';
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
    return 'Ignorée → sans équivalent dans Home Assistant';
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
      var t = d.ha_entity_type ? formatHaDomain(d.ha_entity_type) : 'ce type';
      return 'Publiable en ' + t + ' : type Home Assistant validé.';
    }
    if (!d.is_valid && d.missing_capabilities.length > 0) {
      var caps = d.missing_capabilities.join(', ');
      return (d.missing_capabilities.length > 1 ? 'Capacités manquantes' : 'Capacité manquante') + ' pour ce type HA : ' + caps + '.';
    }
    if (!d.is_valid && d.missing_fields.length > 0) {
      var fields = d.missing_fields.join(', ');
      return (d.missing_fields.length > 1 ? 'Champs requis manquants' : 'Champ requis manquant') + ' pour ce type HA : ' + fields + '.';
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
    ambiguous_skipped: 'type Home Assistant ambigu — précisez les types génériques dans Jeedom',
    name_heuristic_rejection: 'un mot du nom de l’équipement écarte ce type',
    duplicate_generic_types: 'types génériques en double',
    switch_state_orphan: 'état sans ordre On/Off — rien à piloter ; choisissez le type binary_sensor dans « Type HA », puis « Toujours »',
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
    no_mapping: 'aucun type Home Assistant identifié pour cette commande',
    skipped_no_mapping_candidate: 'aucun type Home Assistant candidat à valider',
    ha_component_not_in_product_scope: 'non pris en charge par le plugin',
    sure_mapping: 'type Home Assistant identifié — publication normale',
    publication_excluded_eqlogic: 'exclu manuellement (équipement)',
    publication_excluded_command: 'exclu manuellement (commande)',
    publication_forced: 'publication forcée manuellement',
    // Story 19.3 (AC1/AC7) — le branchement sur evaluate_equipment() fait aussi remonter
    // les raisons d'inéligibilité amont (Story 4.3) jusqu'au diagnostic par commande,
    // là où la surface ignorait jusqu'ici ces cas (CC-03).
    command_not_covered: 'sans équivalent dans Home Assistant',
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

  // Priorité : cause de décision > cause de validité > symptôme brut.
  // `ambiguous_skipped` est le résultat de publication générique ; la cause précise
  // est portée par le mapping dans `reason_code` et doit donc passer avant lui.
  function causeCandidates(d) {
    var preciseAmbiguity = ['name_heuristic_rejection', 'duplicate_generic_types', 'switch_state_orphan'];
    return d.publication_reason === 'ambiguous_skipped' && preciseAmbiguity.indexOf(d.reason_code) !== -1
      ? [d.reason_code, d.publication_reason, d.validity_reason_code]
      : [d.publication_reason, d.reason_code, d.validity_reason_code];
  }

  // Story 16.8 — raison de blocage concise pour la cellule diagnostic du tableau.
  function buildBlockingReason(view) {
    var d = readDiagnosticView(view);
    if (d === null) {
      return '';
    }
    var candidates = causeCandidates(d);
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

  // Story 16.8 / 25.1 — libellé compact de la colonne « Dans Home Assistant » d'un diagnostic (aperçu
  // d'un type imposé). Prêt : « À appliquer → Lumière (light) ». Bloqué : « Bloquée → <cause> ».
  function buildPublishCellLabel(view) {
    var state = diagnosticState(view);
    if (state === 'ready') {
      var d = readDiagnosticView(view);
      return 'À appliquer → ' + formatHaDomain(d && d.ha_entity_type);
    }
    if (state === 'blocking') {
      var reason = buildBlockingReason(view);
      return reason ? 'Bloquée → ' + reason : 'Bloquée';
    }
    return '—';
  }

  function isExcludedDiagnostic(view) {
    var d = readDiagnosticView(view);
    return d !== null && EXCLUDED_PUBLICATION_REASONS.indexOf(d.publication_reason) !== -1;
  }

  function buildExcludedLabel(view) {
    var d = readDiagnosticView(view);
    return 'Exclue → ' + REASON_LABELS[d.publication_reason];
  }

  // Story 20.1 : un équipement désactivé est un état neutre, distinct d'une
  // exclusion et d'un blocage actionnable. Le démon reste la seule source.
  function isDisabledDiagnostic(view) {
    var d = readDiagnosticView(view);
    return d !== null && d.publication_reason === 'disabled_eqlogic';
  }

  function buildDisabledLabel(view) {
    return isDisabledDiagnostic(view) ? 'Équipement désactivé dans Jeedom' : '—';
  }

  // Story 22.2 (CC-58, Q6 C) — nombre d'entités de l'arbre qui portent cette commande
  // (lecture de `entities[].command_ids`, aucune décision recalculée).
  function countEntitiesCarryingCommand(entities, cmdId) {
    return (Array.isArray(entities) ? entities : []).filter(function (entity) {
      return entity && Array.isArray(entity.command_ids) && entity.command_ids.indexOf(cmdId) !== -1;
    }).length;
  }

  var SHARED_COMMAND_SELECTOR_REASON = 'Cette commande est portée par plusieurs entités : le type Home Assistant choisi '
    + 'ne s’appliquerait qu’à l’entité principale de l’équipement. Réglage indisponible ici.';

  var NO_TYPE_SELECTOR_REASON = 'Aucun type Home Assistant ne peut aboutir pour cette commande en l’état : '
    + 'précisez les types génériques dans Jeedom.';

  // `entities` (optionnel, arbre déjà normalisé) : sans lui, comportement d'avant 22.2.
  function getOverrideSelectorState(row, entities) {
    var r = normalizeCommandRow(row);
    if (isExcludedDiagnostic(r.diagnostic)) {
      return { active: false, reason: 'Commande exclue de Jeedom2HA : son type HA ne peut pas être réglé ici.' };
    }
    if (isDisabledDiagnostic(r.diagnostic)) {
      return { active: false, reason: 'Équipement désactivé dans Jeedom : son type HA ne peut pas être réglé ici.' };
    }
    if (r.covered === false && shouldShowUncoveredLabel(r.diagnostic)) {
      return { active: false, reason: 'Aucun type Home Assistant ne couvre cette commande : son type HA ne peut pas être réglé ici.' };
    }
    if (r.jeedom_cmd_id !== null && countEntitiesCarryingCommand(entities, r.jeedom_cmd_id) > 1) {
      return { active: false, reason: SHARED_COMMAND_SELECTOR_REASON };
    }
    // Story 22.2 (R2, AC6) : aucun type ne peut aboutir. Un type déjà posé garde le sélecteur actif
    // (retour au mode automatique).
    if (r.override_types_allowed !== null && getOverrideTypeOptions(r).length === 0) {
      return { active: false, reason: NO_TYPE_SELECTOR_REASON };
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
      // Story 25.7 (Q1 A) : identifiant du plugin de l'équipement, champ ADDITIF de `j2haRoomsTree` (absent : chaîne vide).
      eq_type: typeof e.eq_type === 'string' ? e.eq_type : '',
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

  // --- Story 25.1 — catégories de commande (D2/D3) et état unique d'équipement (D1) ---
  // Agrégation strictement front à partir des diagnostics et de la présence déjà portés par le GET
  // arbre : aucune décision n'est recalculée. Un seul état par équipement, lu par le badge, les
  // compteurs et le tableau (`resolveEquipmentState`).

  // D3 — partition des codes de cause (REASON_LABELS). « Ignorée » : aucun équivalent HA, rien à faire
  // pour l'utilisateur ; « Bloquée » : corrigeable ; « state » : codes d'état (ni l'une ni l'autre) ;
  // `no_commands` est un état d'équipement. Tout code inconnu (démon plus récent) est Bloqué.
  var COMMAND_CAUSE_CATEGORIES = {
    ignored: ['command_not_covered', 'no_supported_generic_type', 'ha_component_not_in_product_scope'],
    blocked: [
      'ambiguous_skipped', 'name_heuristic_rejection', 'duplicate_generic_types', 'conflicting_generic_types',
      'switch_state_orphan', 'probable_skipped', 'low_confidence', 'no_generic_type_configured', 'no_mapping',
      'skipped_no_mapping_candidate', 'ha_missing_command_topic', 'ha_missing_state_topic', 'discovery_publish_failed',
      'no_projection_possible',
    ],
    state: [
      'disabled_eqlogic', 'excluded_eqlogic', 'excluded_plugin', 'excluded_object', 'publication_excluded_eqlogic',
      'publication_excluded_command', 'publication_forced', 'sure_mapping',
    ],
    equipment_state: ['no_commands'],
  };

  function categoryOfCause(code) {
    var names = Object.keys(COMMAND_CAUSE_CATEGORIES);
    for (var i = 0; i < names.length; i++) {
      if (COMMAND_CAUSE_CATEGORIES[names[i]].indexOf(code) !== -1) {
        return names[i];
      }
    }
    return 'blocked';
  }

  // Code de cause retenu pour une vue : même priorité que le libellé (cause de décision avant le
  // symptôme de projection) ; un code connu l'emporte sur un code brut inconnu.
  function resolveCauseCode(view) {
    var d = readDiagnosticView(view);
    if (d === null) {
      return null;
    }
    var candidates = causeCandidates(d);
    for (var i = 0; i < candidates.length; i++) {
      if (candidates[i] && REASON_LABELS[candidates[i]]) {
        return candidates[i];
      }
    }
    for (var j = 0; j < candidates.length; j++) {
      if (candidates[j]) {
        return candidates[j];
      }
    }
    return null;
  }

  // Catégorie D2 d'une ligne de commande : 'published' | 'to_apply' | 'blocked' | 'ignored' |
  // 'excluded' | 'disabled' | 'unknown'. « Publiée » = présente dans HA (jamais déduite du diagnostic).
  function classifyCommandCategory(row) {
    var r = row || {};
    if (r.published_in_ha === true) {
      return 'published';
    }
    var view = r.diagnostic != null ? r.diagnostic : null;
    if (isExcludedDiagnostic(view)) {
      return 'excluded';
    }
    if (isDisabledDiagnostic(view)) {
      return 'disabled';
    }
    if (r.covered === false && shouldShowUncoveredLabel(view)) {
      return 'ignored';
    }
    var state = diagnosticState(view);
    if (state === 'ready') {
      return 'to_apply';
    }
    if (state === 'blocking') {
      return categoryOfCause(resolveCauseCode(view)) === 'ignored' ? 'ignored' : 'blocked';
    }
    return 'unknown';
  }

  // Story 16.8 : classe un diagnostic de commande (conservé pour les appelants historiques) ;
  // « uncovered » = commande non couverte, désormais la catégorie « Ignorée ».
  function isUncoveredDiagnostic(view) {
    var d = readDiagnosticView(view);
    return d !== null && d.publication_reason === 'command_not_covered';
  }

  function classifyCommandRow(row) {
    if (isUncoveredDiagnostic(row.diagnostic)) return 'uncovered';
    if (isExcludedDiagnostic(row.diagnostic)) return 'excluded';
    if (isDisabledDiagnostic(row.diagnostic)) return 'disabled';
    return diagnosticState(row.diagnostic);
  }

  // Lecture des catégories d'un arbre normalisé : base commune de l'état, des compteurs et du tableau.
  function analyzeEquipment(t) {
    var counts = { published: 0, to_apply: 0, blocked: 0, ignored: 0, excluded: 0, disabled: 0, unknown: 0 };
    var ready = 0;
    var presenceUnknown = 0;
    var firstBlockedCmdId = null;
    for (var i = 0; i < t.commands.length; i++) {
      var row = t.commands[i];
      var category = classifyCommandCategory(row);
      counts[category] += 1;
      if (isReadyDiagnostic(row.diagnostic)) {
        ready += 1;
      }
      if (row.published_in_ha === null) {
        presenceUnknown += 1;
      }
      if (category === 'blocked' && firstBlockedCmdId === null) {
        firstBlockedCmdId = row.jeedom_cmd_id;
      }
    }
    // « Désactivé » / « Exclu » (D1 : R3 avant R4) s'appliquent dès que `equipment_decision` (lecture pure
    // du démon) le dit, quelles que soient les commandes (story 20-2, AC8). Par les commandes : toutes
    // les commandes doivent être désactivées ou exclues (D1 R4 : « toutes les commandes exclues »).
    var allOff = t.commands.length > 0 && counts.excluded + counts.disabled === t.commands.length;
    return {
      counts: counts,
      ready: ready,
      blocked: counts.blocked,
      presence_unknown: presenceUnknown,
      first_blocked_cmd_id: firstBlockedCmdId,
      disabled: isDisabledDiagnostic(t.equipment_decision) || (allOff && counts.disabled > 0),
      excluded: isExcludedDiagnostic(t.equipment_decision) || (allOff && counts.excluded > 0),
    };
  }

  function entityIsPending(entity) {
    return !!entity && entity.override_pending === true;
  }

  // D1 — état unique d'un équipement. Pure : ne mute pas l'arbre, aucun DOM, aucune E/S. Règles
  // évaluées dans l'ordre, la première qui s'applique l'emporte. `enabled` (arbre PHP `j2haRoomsTree`) est
  // un paramètre explicite : `false` fait prévaloir « Désactivé » sur « Exclu » (R3), quelle que soit
  // `equipment_decision` ; `undefined`/`null` = inconnu, l'état ne dépend alors que de l'arbre.
  function resolveEquipmentState(tree, enabled) {
    var t = normalizeTree(tree);
    var a = analyzeEquipment(t);
    var sync = t.sync_status;
    var presence = sync.published_in_ha;
    // Jamais synchronisé (`synced_should_publish` null) : le démon marque alors `override_pending`
    // faute de décision appliquée, ce qui n'est pas un réglage posé par l'utilisateur.
    var neverSynced = sync.synced_should_publish === null;
    var pending = !neverSynced && (sync.override_pending === true || t.entities.some(entityIsPending));
    var state;
    if (pending) {
      state = 'to_apply';
    } else if (presence === true) {
      state = 'published';
    } else if (a.disabled || enabled === false) {
      state = 'disabled';
    } else if (a.excluded) {
      state = 'excluded';
    } else if (presence === false && a.ready > 0 && sync.current_should_publish === true) {
      state = 'to_apply';
    } else if (presence === null && a.ready > 0 && sync.current_should_publish !== false) {
      state = 'to_apply';
    } else if (a.blocked > 0) {
      state = 'blocked';
    } else {
      state = 'nothing_to_publish';
    }
    return {
      state: state,
      blocked_mention: (state === 'published' || state === 'to_apply') ? a.blocked : 0,
    };
  }

  function summarizePublication(tree) {
    var t = normalizeTree(tree);
    var a = analyzeEquipment(t);
    var excluded = a.counts.excluded;
    var disabled = a.counts.disabled;
    // Story 20-2 (AC8, X6) : sans commande, `equipment_decision` est la seule source (voir analyzeEquipment).
    if (t.commands.length === 0) {
      disabled = isDisabledDiagnostic(t.equipment_decision) ? 1 : 0;
      excluded = disabled === 0 && isExcludedDiagnostic(t.equipment_decision) ? 1 : 0;
    }
    return {
      total: t.commands.length,
      ready_count: a.ready,
      blocking_count: a.blocked,
      unknown_count: a.counts.unknown,
      uncovered_count: a.counts.ignored,
      excluded_count: excluded,
      disabled_count: disabled,
      will_publish: a.ready > 0,
      first_blocking_cmd_id: a.first_blocked_cmd_id,
    };
  }

  // AC3.4 — commandes bloquées détectées au GET initial, plafonnées (auto-ouverture).
  function collectBlockingCommandIds(tree, cap) {
    var t = normalizeTree(tree);
    var limit = (typeof cap === 'number' && cap > 0) ? cap : 4;
    var ids = [];
    for (var i = 0; i < t.commands.length && ids.length < limit; i++) {
      if (classifyCommandCategory(t.commands[i]) === 'blocked') {
        ids.push(t.commands[i].jeedom_cmd_id);
      }
    }
    return ids;
  }

  // Story 25.1 (AC14) — la cause d'un blocage est dite une fois : un groupe par cause distincte, jamais
  // un par commande. `generic_types_link` : le blocage se corrige dans les types génériques de Jeedom.
  var GENERIC_TYPE_CAUSES = [
    'no_generic_type_configured', 'ambiguous_skipped', 'duplicate_generic_types', 'conflicting_generic_types',
  ];

  function groupBlockedCauses(tree) {
    var t = normalizeTree(tree);
    var groups = [];
    var byLabel = {};
    for (var i = 0; i < t.commands.length; i++) {
      var row = t.commands[i];
      if (classifyCommandCategory(row) !== 'blocked') {
        continue;
      }
      var code = resolveCauseCode(row.diagnostic);
      var label = buildBlockingReason(row.diagnostic) || code || 'cause non précisée';
      if (!byLabel[label]) {
        byLabel[label] = {
          code: code,
          label: label,
          count: 0,
          command_ids: [],
          generic_types_link: GENERIC_TYPE_CAUSES.indexOf(code) !== -1,
          raw_code: code && !REASON_LABELS[code] ? code : null,
        };
        groups.push(byLabel[label]);
      }
      byLabel[label].count += 1;
      byLabel[label].command_ids.push(row.jeedom_cmd_id);
    }
    return groups;
  }

  function buildCauseNoticeText(group) {
    return pluralize(group.count, 'commande bloquée', 'commandes bloquées') + ' : ' + group.label;
  }

  function allCommandsBlocked(tree) {
    var t = normalizeTree(tree);
    return t.commands.length > 0 && t.commands.every(function (row) {
      return classifyCommandCategory(row) === 'blocked';
    });
  }

  // Story 25.1 (AC15) — commandes ignorées : repliées sur une ligne, jamais comptées comme défaut.
  var IGNORED_NAMES_SHOWN = 3;
  var NOT_SUPPORTED_BY_PLUGIN = 'non pris en charge par le plugin';

  function joinNames(names) {
    return names.slice(0, IGNORED_NAMES_SHOWN).join(', ') + (names.length > IGNORED_NAMES_SHOWN ? '…' : '');
  }

  function buildIgnoredSummary(tree) {
    var t = normalizeTree(tree);
    var items = [];
    for (var i = 0; i < t.commands.length; i++) {
      var row = t.commands[i];
      if (classifyCommandCategory(row) !== 'ignored') {
        continue;
      }
      var code = resolveCauseCode(row.diagnostic);
      items.push({
        cmd_id: row.jeedom_cmd_id,
        name: row.cmd_name || ('#' + row.jeedom_cmd_id),
        code: code,
        not_supported_by_plugin: code === 'ha_component_not_in_product_scope',
      });
    }
    var text = '';
    if (items.length > 0) {
      text = pluralize(items.length, 'commande ignorée', 'commandes ignorées')
        + ', sans équivalent dans Home Assistant : ' + joinNames(items.map(function (item) { return item.name; }));
      var notSupported = items.filter(function (item) { return item.not_supported_by_plugin; });
      if (notSupported.length > 0) {
        text += ' — ' + NOT_SUPPORTED_BY_PLUGIN + ' : ' + joinNames(notSupported.map(function (item) { return item.name; }));
      }
    }
    return { count: items.length, text: text, items: items };
  }

  // Story 25.1 (AC8, AC13) — domaine HA dit en français, terme technique en petit à côté.
  var HA_DOMAIN_LABELS = {
    alarm_control_panel: 'Alarme',
    binary_sensor: 'Capteur binaire',
    button: 'Bouton',
    climate: 'Thermostat',
    cover: 'Volet',
    light: 'Lumière',
    sensor: 'Capteur',
    switch: 'Interrupteur',
  };

  function translateHaDomain(type) {
    if (typeof type !== 'string' || !type) {
      return { label: 'Entité Home Assistant', technical: '' };
    }
    if (HA_DOMAIN_LABELS[type]) {
      return { label: HA_DOMAIN_LABELS[type], technical: type };
    }
    return { label: type, technical: '' };
  }

  function formatHaDomain(type) {
    var d = translateHaDomain(type);
    return d.technical ? d.label + ' (' + d.technical + ')' : d.label;
  }

  // --- Compteurs de l'équipement et de la pièce (25.1, AC5, AC6) ---
  // Dénombrement pur des arbres déjà lus par la surface : l'état d'un équipement vient uniquement de
  // `resolveEquipmentState` ; les ignorées ne comptent jamais comme défaut.

  var EQUIPMENT_STATES = ['published', 'to_apply', 'blocked', 'excluded', 'disabled', 'nothing_to_publish'];
  var EQUIPMENT_STATE_LABELS = {
    published: 'Publié',
    to_apply: 'À appliquer',
    blocked: 'Bloqué',
    excluded: 'Exclu',
    disabled: 'Désactivé',
    nothing_to_publish: 'Rien à publier',
  };

  // Compteurs d'UN équipement (arbre brut ou normalisé) : base de la ligne de l'équipement déplié et
  // de l'agrégat de la pièce.
  function summarizeEquipmentCounters(tree, enabled) {
    var t = normalizeTree(tree);
    var resolved = resolveEquipmentState(t, enabled);
    var a = analyzeEquipment(t);
    return {
      state: resolved.state,
      blocked_mention: resolved.blocked_mention,
      defects: a.counts.blocked,
      presence_unknown: t.sync_status.published_in_ha === null,
      commands: {
        published: a.counts.published,
        to_apply: a.counts.to_apply,
        blocked: a.counts.blocked,
        ignored: a.counts.ignored,
        excluded: a.counts.excluded,
        presence_unknown: a.presence_unknown,
      },
    };
  }

  // `trees` : arbres normalisés ou bruts des équipements dont la lecture a abouti ;
  // `totalEquipments` : nombre d'équipements de la pièce (pour signaler les lectures manquantes).
  // `enabledById` : { eq_id: boolean } issu de `j2haRoomsTree` (optionnel).
  function summarizeRoom(trees, totalEquipments, enabledById) {
    var list = Array.isArray(trees) ? trees : [];
    var out = {
      equipments_total: typeof totalEquipments === 'number' ? totalEquipments : list.length,
      equipments_read: list.length,
      equipments_presence_unknown: 0,
      defects: 0,
      by_state: {},
    };
    EQUIPMENT_STATES.forEach(function (state) { out.by_state[state] = 0; });
    for (var i = 0; i < list.length; i++) {
      var eqId = list[i] && list[i].jeedom_eq_id;
      var enabled = enabledById && eqId != null ? enabledById[eqId] : undefined;
      var counters = summarizeEquipmentCounters(list[i], enabled);
      out.by_state[counters.state] += 1;
      out.defects += counters.defects;
      if (counters.presence_unknown) out.equipments_presence_unknown += 1;
    }
    return out;
  }

  // Story 25.3 (AC2) — agrégat de la maison : somme des résumés de pièce, jamais un second calcul d'état.
  function summarizeHouse(roomSummaries) {
    var list = Array.isArray(roomSummaries) ? roomSummaries : [];
    var out = { equipments_total: 0, equipments_read: 0, equipments_presence_unknown: 0, defects: 0, by_state: {} };
    EQUIPMENT_STATES.forEach(function (state) { out.by_state[state] = 0; });
    list.forEach(function (room) {
      if (!room) return;
      out.equipments_total += room.equipments_total || 0;
      out.equipments_read += room.equipments_read || 0;
      out.equipments_presence_unknown += room.equipments_presence_unknown || 0;
      out.defects += room.defects || 0;
      EQUIPMENT_STATES.forEach(function (state) { out.by_state[state] += (room.by_state && room.by_state[state]) || 0; });
    });
    return out;
  }

  // --- Story 25.7 — cause d'exclusion d'un équipement (D1) et ventilation par pièce (D2) ---
  // Ajouts PURS : aucune règle d'état n'est écrite ici (`resolveEquipmentState` décide de l'état « Exclu »), la cause est
  // une MENTION à côté de ce mot, jamais un septième état. Une seule cause par équipement : celle de la décision
  // d'équipement, sinon celle des commandes si elle est la même pour toutes ; jamais de cause inventée ni cumulée.
  var EXCLUSION_KIND_OF = {
    excluded_plugin: 'plugin',
    excluded_object: 'piece',
    excluded_eqlogic: 'individuelle',
    publication_excluded_eqlogic: 'individuelle',
    publication_excluded_command: 'individuelle',
  };

  /**
   * @param {object} tree entrée agrégée (page B) OU arbre unitaire (détail) : même forme, parité prouvée en 25.2.
   * @param {boolean|undefined} enabled `enabled` de `j2haRoomsTree` (`false` : « Désactivé » prime, aucune cause).
   * @returns {{kind: string, code: string}|null}
   */
  function exclusionCauseOf(tree, enabled) {
    if (!tree || typeof tree !== 'object') return null;
    if (resolveEquipmentState(tree, enabled).state !== 'excluded') return null;
    var t = normalizeTree(tree);
    var decision = readDiagnosticView(t.equipment_decision);
    if (decision && Object.prototype.hasOwnProperty.call(EXCLUSION_KIND_OF, decision.publication_reason)) {
      return { kind: EXCLUSION_KIND_OF[decision.publication_reason], code: decision.publication_reason };
    }
    var reasons = [];
    t.commands.forEach(function (row) {
      var d = readDiagnosticView(row.diagnostic);
      if (d && Object.prototype.hasOwnProperty.call(EXCLUSION_KIND_OF, d.publication_reason) && reasons.indexOf(d.publication_reason) === -1) {
        reasons.push(d.publication_reason);
      }
    });
    return reasons.length === 1 ? { kind: EXCLUSION_KIND_OF[reasons[0]], code: reasons[0] } : null;
  }

  // Nom affiché du plugin : table de la page (`j2haPluginNames`), repli sur l'identifiant, sinon chaîne vide.
  function exclusionPluginName(pluginType, names) {
    var type = typeof pluginType === 'string' ? pluginType : '';
    var table = names && typeof names === 'object' ? names : {};
    var name = type !== '' && Object.prototype.hasOwnProperty.call(table, type) && typeof table[type] === 'string' ? table[type].trim() : '';
    return name !== '' ? name : type;
  }

  /**
   * Libellé d'une cause : `form` 'short' (ligne d'arbre, carte) ou 'sentence' (détail d'équipement). Le nom du plugin est
   * un texte (jamais du HTML) ; sans nom : « son plugin ». Chaîne vide pour une cause nulle ou inconnue.
   */
  function exclusionCauseText(cause, pluginName, form) {
    if (!cause || typeof cause !== 'object') return '';
    var name = typeof pluginName === 'string' ? pluginName.trim() : '';
    var sentence = form === 'sentence';
    if (cause.kind === 'plugin') {
      var who = name !== '' ? '{{par le plugin}} ' + name : '{{par son plugin}}';
      return sentence ? '{{Exclu}} ' + who + ' ({{configuration du plugin, « Plugins exclus »}})' : who;
    }
    if (cause.kind === 'piece') return sentence ? '{{Exclu par la pièce : toute la pièce est exclue}}' : '{{par la pièce}}';
    if (cause.kind === 'individuelle') {
      if (!sentence) return '{{individuelle}}';
      if (cause.code === 'publication_excluded_command') return '{{Exclusion individuelle : « Jamais » sur ses entités}}';
      if (cause.code === 'excluded_eqlogic') return "{{Exclusion individuelle : réglage de l'équipement dans Jeedom}}";
      return '{{Exclusion individuelle : réglage « Jamais »}}';
    }
    return '';
  }

  /**
   * D2 — ventilation des exclus d'une pièce. `items` : [{ cause, eq_type }] des équipements lus dont l'état est « Exclu ».
   * `autre` = exclus dont la cause est indéterminable (Q6). Plugins triés par identifiant (ordre déterministe).
   */
  function exclusionBreakdown(items) {
    var list = Array.isArray(items) ? items : [];
    var out = { excluded: 0, plugin: [], piece: 0, individuelle: 0, autre: 0 };
    var byType = {};
    list.forEach(function (item) {
      out.excluded += 1;
      var cause = item && item.cause;
      if (!cause) { out.autre += 1; return; }
      if (cause.kind === 'plugin') {
        var type = typeof item.eq_type === 'string' ? item.eq_type : '';
        if (!Object.prototype.hasOwnProperty.call(byType, type)) {
          byType[type] = { eq_type: type, count: 0 };
          out.plugin.push(byType[type]);
        }
        byType[type].count += 1;
      } else if (cause.kind === 'piece') {
        out.piece += 1;
      } else if (cause.kind === 'individuelle') {
        out.individuelle += 1;
      } else {
        out.autre += 1;
      }
    });
    out.plugin.sort(function (a, b) { return a.eq_type < b.eq_type ? -1 : a.eq_type > b.eq_type ? 1 : 0; });
    return out;
  }

  /** « 2 par le plugin Alpha, 1 par la pièce, 1 individuelle, 1 autre » : zéros omis, pluriels accordés ici. */
  function exclusionBreakdownText(breakdown, names) {
    var b = breakdown || {};
    var parts = [];
    (b.plugin || []).forEach(function (p) {
      var name = exclusionPluginName(p.eq_type, names);
      parts.push(p.count + ' ' + (name !== '' ? '{{par le plugin}} ' + name : '{{par son plugin}}'));
    });
    if (b.piece > 0) parts.push(b.piece + ' {{par la pièce}}');
    if (b.individuelle > 0) parts.push(b.individuelle + ' ' + (b.individuelle > 1 ? '{{individuelles}}' : '{{individuelle}}'));
    if (b.autre > 0) parts.push(b.autre + ' {{autre}}');
    return parts.join(', ');
  }

  function pluralize(count, singular, plural) {
    return count + ' ' + (count > 1 ? plural : singular);
  }

  var ROOM_STATE_WORDS = {
    published: ['publié', 'publiés'],
    to_apply: ['à appliquer', 'à appliquer'],
    blocked: ['bloqué', 'bloqués'],
    excluded: ['exclu', 'exclus'],
    disabled: ['désactivé', 'désactivés'],
    nothing_to_publish: ['rien à publier', 'rien à publier'],
  };

  // Ligne de compteurs de la pièce : un chiffre et un mot court par état non nul, dans l'ordre des états.
  function buildRoomCounterLabels(summary) {
    var s = summary || {};
    var byState = s.by_state || {};
    function n(key) { return typeof s[key] === 'number' ? s[key] : 0; }
    var items = [];
    EQUIPMENT_STATES.forEach(function (state) {
      var count = typeof byState[state] === 'number' ? byState[state] : 0;
      if (count > 0) {
        items.push({ state: state, count: count, text: pluralize(count, ROOM_STATE_WORDS[state][0], ROOM_STATE_WORDS[state][1]) });
      }
    });
    return {
      items: items,
      unread: n('equipments_total') > n('equipments_read')
        ? pluralize(n('equipments_total') - n('equipments_read'), 'équipement non lu', 'équipements non lus')
        : '',
      presence_unknown: n('equipments_presence_unknown') > 0
        ? pluralize(n('equipments_presence_unknown'), 'équipement dont la présence dans Home Assistant est inconnue (démon plus ancien)',
          'équipements dont la présence dans Home Assistant est inconnue (démon plus ancien)')
        : '',
    };
  }

  // Ligne de commandes d'un équipement déplié : « 3 publiées · 1 bloquée · 5 ignorées » (zéros masqués).
  function buildEquipmentCounterLabels(tree, enabled) {
    var counters = summarizeEquipmentCounters(tree, enabled);
    var c = counters.commands;
    var items = [];
    [
      [c.published, 'publiée', 'publiées'],
      [c.to_apply, 'à appliquer', 'à appliquer'],
      [c.blocked, 'bloquée', 'bloquées'],
      [c.ignored, 'ignorée', 'ignorées'],
      [c.excluded, 'exclue', 'exclues'],
    ].forEach(function (entry) {
      if (entry[0] > 0) {
        items.push(pluralize(entry[0], entry[1], entry[2]));
      }
    });
    return {
      items: items,
      text: items.join(' · '),
      presence_unknown: c.presence_unknown > 0 || counters.presence_unknown
        ? 'présence dans Home Assistant inconnue (démon plus ancien)' : '',
    };
  }

  // --- Story 22.2 (Q4 B, CC-51) — portée des actions : équipement entier / cette entité ---
  // Les actions d'entité ne sont masquées que dans les cas STRICTEMENT équivalents à celles de
  // l'équipement (Task 0 b de la story 22.2) : équipement à UNE seule entité, et aucune exclusion ou
  // forçage posé au niveau de la commande de cette entité. Tout autre cas garde ses actions d'entité :
  //   - plusieurs entités : chaque entité a sa propre portée (« Revenir » d'une entité ne touche que
  //     ses commandes, celui de l'équipement touche toutes les commandes et l'entrée d'équipement) ;
  //   - `exclude_command` : exclusion posée sur la commande de l'entité ; « Exclure » de l'équipement
  //     poserait une seconde exclusion au niveau équipement plutôt que d'agir sur celle-ci ;
  //   - `force_publish` sans forçage au niveau équipement : forçage posé sur la commande, même raison.
  // `exclude_eqlogic` (veto posé sur l'équipement) et `force_publish` posé sur l'équipement rendent les
  // actions d'entité inertes (« retirer depuis l'équipement ») : on les masque.
  function entityActionsDuplicateEquipment(tree, entity) {
    var t = normalizeTree(tree);
    if (!entity || t.entities.length !== 1) {
      return false;
    }
    var policy = entity.publication_override || null;
    if (policy === null || policy === 'exclude_eqlogic') {
      return true;
    }
    return policy === 'force_publish' && t.equipment_publication_override === 'force_publish';
  }

  // R1-B (story 20.3) — gating d'état des actions déplacées (Republier, Supprimer de Home Assistant).
  // Lecture pure de l'arbre déjà chargé : aucune décision recalculée, aucune route. Référence de
  // comportement : l'ancienne synthèse (« Republier » seulement si inclus, « Supprimer » seulement
  // si publié). R2-1 : « publié dans HA » = `sync_status.published_in_ha` (présence réelle, calculée
  // par le démon comme pour les actions ; couvre principal refusé / secondaires publiés et
  // dépublication différée). `synced_should_publish` ne décrit que le principal et n'est PAS utilisé.
  // Champ absent (démon plus ancien) : l'action reste active, le démon ignore les équipements sans objet.
  // Un arbre illisible (relais en erreur, 404 démon, `jeedom_eq_id` absent) ne propose aucune action.
  var ACTION_REASONS = {
    treeUnavailable: 'Configuration illisible : action indisponible.',
    republishDisabled: 'Équipement désactivé dans Jeedom : rien à republier.',
    republishExcluded: 'Équipement exclu : rien à republier.',
    recreateNotPublished: 'Équipement non publié dans Home Assistant : rien à supprimer.',
    roomNothingToPublish: 'Aucun équipement à publier dans cette pièce.',
    roomNothingPublished: 'Aucun équipement publié dans cette pièce.',
  };

  function isReadableTree(tree) {
    return !!tree && typeof tree === 'object' && normalizeTree(tree).jeedom_eq_id != null;
  }

  function equipmentActionState(tree) {
    if (!isReadableTree(tree)) {
      return { readable: false, can_republish: false, can_recreate: false,
        republish_reason: ACTION_REASONS.treeUnavailable, recreate_reason: ACTION_REASONS.treeUnavailable };
    }
    var normalized = normalizeTree(tree);
    var flags = analyzeEquipment(normalized);
    var republishReason = '';
    if (flags.excluded) republishReason = ACTION_REASONS.republishExcluded;
    if (flags.disabled) republishReason = ACTION_REASONS.republishDisabled;
    var notPublished = normalized.sync_status.published_in_ha === false;
    return {
      readable: true,
      can_republish: republishReason === '',
      can_recreate: !notPublished,
      republish_reason: republishReason,
      recreate_reason: notPublished ? ACTION_REASONS.recreateNotPublished : '',
    };
  }

  // R2-3 — `trees` : arbres lus et valides de la pièce ; `settledCount` : arbres lus + arbres en
  // erreur. Une action de pièce n'est grisée que si TOUTES les lectures ont abouti sans erreur et
  // qu'aucun équipement ne la justifie ; pendant la lecture, ou si une lecture a échoué, elle reste
  // active (le démon ignore les équipements sans objet).
  function roomActionState(trees, totalEquipments, settledCount) {
    var list = Array.isArray(trees) ? trees : [];
    var canRepublish = false;
    var canRecreate = false;
    for (var i = 0; i < list.length; i++) {
      var state = equipmentActionState(list[i]);
      if (state.can_republish) canRepublish = true;
      if (state.can_recreate) canRecreate = true;
    }
    var settled = typeof settledCount === 'number' ? settledCount : list.length;
    var complete = typeof totalEquipments === 'number' && settled >= totalEquipments;
    var failedReads = settled - list.length;
    var conclusive = complete && failedReads <= 0;
    return {
      complete: complete,
      conclusive: conclusive,
      can_republish: canRepublish || !conclusive,
      can_recreate: canRecreate || !conclusive,
      republish_reason: canRepublish || !conclusive ? '' : ACTION_REASONS.roomNothingToPublish,
      recreate_reason: canRecreate || !conclusive ? '' : ACTION_REASONS.roomNothingPublished,
    };
  }

  // Story 5.4 (déplacé en 20.3 hors de l'ancien module de synthèse) — normalisation du
  // résultat de la dernière opération pour le bandeau de santé. Lecture seule du contrat
  // backend (`derniere_operation_resultat`), aucune décision recalculée.
  function readOperationSnapshot(raw) {
    var VALID_RESULTATS = { succes: true, partiel: true, echec: true, aucun: true };
    var empty = { resultat: 'aucun', intention: null, portee: null, message: null, volume: null, timestamp: null };
    if (raw === null || raw === undefined) return empty;
    if (typeof raw === 'string') {
      return Object.assign({}, empty, { resultat: VALID_RESULTATS[raw] ? raw : 'aucun' });
    }
    if (typeof raw !== 'object') return empty;
    var resultat = (typeof raw.resultat === 'string' && VALID_RESULTATS[raw.resultat]) ? raw.resultat : 'aucun';
    return {
      resultat: resultat,
      intention: typeof raw.intention === 'string' ? raw.intention : null,
      portee: typeof raw.portee === 'string' ? raw.portee : null,
      message: (typeof raw.message === 'string' && raw.message !== '') ? raw.message : null,
      volume: (typeof raw.volume === 'number' && Number.isFinite(raw.volume)) ? raw.volume : null,
      timestamp: typeof raw.timestamp === 'string' ? raw.timestamp : null,
    };
  }

  var api = {
    HA_ENTITY_TYPE_OPTIONS: HA_ENTITY_TYPE_OPTIONS,
    getHaEntityTypeOptions: getHaEntityTypeOptions,
    getOverrideTypeOptions: getOverrideTypeOptions,
    normalizeCommandRow: normalizeCommandRow,
    normalizeTree: normalizeTree,
    resolveCommandNames: resolveCommandNames,
    entityCommandsLabel: entityCommandsLabel,
    publicationActionState: publicationActionState,
    equipmentPublicationTarget: equipmentPublicationTarget,
    shouldConfirmPublication: shouldConfirmPublication,
    shouldConfirmEquipmentExclude: shouldConfirmEquipmentExclude,
    entitiesLeavingHomeAssistant: entitiesLeavingHomeAssistant,
    forcePreviewState: forcePreviewState,
    equipmentForcePreviewState: equipmentForcePreviewState,
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
    summarizeRoom: summarizeRoom,
    summarizeHouse: summarizeHouse,
    summarizeEquipmentCounters: summarizeEquipmentCounters,
    buildEquipmentCounterLabels: buildEquipmentCounterLabels,
    entityActionsDuplicateEquipment: entityActionsDuplicateEquipment,
    countEntitiesCarryingCommand: countEntitiesCarryingCommand,
    classifyCommandRow: classifyCommandRow,
    readOperationSnapshot: readOperationSnapshot,
    equipmentActionState: equipmentActionState,
    roomActionState: roomActionState,
    buildRoomCounterLabels: buildRoomCounterLabels,
    normalizeRoomsTree: normalizeRoomsTree,
    summarizePublication: summarizePublication,
    resolveEquipmentState: resolveEquipmentState,
    classifyCommandCategory: classifyCommandCategory,
    categoryOfCause: categoryOfCause,
    resolveCauseCode: resolveCauseCode,
    COMMAND_CAUSE_CATEGORIES: COMMAND_CAUSE_CATEGORIES,
    REASON_LABELS: REASON_LABELS,
    EQUIPMENT_STATES: EQUIPMENT_STATES,
    EQUIPMENT_STATE_LABELS: EQUIPMENT_STATE_LABELS,
    exclusionCauseOf: exclusionCauseOf,
    exclusionCauseText: exclusionCauseText,
    exclusionPluginName: exclusionPluginName,
    exclusionBreakdown: exclusionBreakdown,
    exclusionBreakdownText: exclusionBreakdownText,
    groupBlockedCauses: groupBlockedCauses,
    buildCauseNoticeText: buildCauseNoticeText,
    allCommandsBlocked: allCommandsBlocked,
    buildIgnoredSummary: buildIgnoredSummary,
    translateHaDomain: translateHaDomain,
    formatHaDomain: formatHaDomain,
    HA_DOMAIN_LABELS: HA_DOMAIN_LABELS,
    shouldShowOverridePendingBadge: shouldShowOverridePendingBadge,
    shouldShowEntityPendingBadge: shouldShowEntityPendingBadge,
    readPublicationRequestError: readPublicationRequestError,
  };

  return api;
}));
