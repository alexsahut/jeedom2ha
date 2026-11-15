/* Story 16.8 / 25.1 / 25.4 — Surface de mapping HA : détail d'un équipement et actions de pièce.
 *
 * Navigation (25.4) : page plugin -> vue de travail maître-détail (jeedom2ha_workview.js) -> détail de
 * l'équipement sélectionné : état unique, réglage de publication et tableau des commandes regroupé par
 * entité. La fenêtre de pièce et son accordéon n'existent plus ; ce module expose `window.Jeedom2haSurface`
 * (voir la fin du fichier) que la vue appelle. Les fonctions d'écriture sont DÉPLACÉES telles quelles, pas
 * réécrites (AC8).
 *
 * Ce contrôleur ne réinvente aucune logique métier : il réutilise strictement le
 * module pur Jeedom2haMappingOverride (état diagnostic, auto-validation, synthèse
 * de publication) et les 4 routes backend existantes (16.5/16.6). Le point d'entrée
 * remplace l'onglet inatteignable de la 16.5 (0 eqLogic jeedom2ha sur la box).
 * D10 : le generic_type natif Jeedom n'est jamais écrit ici. */
(function () {
  var M = window.Jeedom2haMappingOverride;
  if (!M || typeof $ === 'undefined') {
    return;
  }

  var AJAX_URL = 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php';
  var DEBOUNCE_MS = 400;

  // État volatil de la surface courante (un seul équipement affiché à la fois, dans la vue de travail).
  // `current` : l'équipement sélectionné { eqId, $panel } ; `reads` : lectures d'arbre en vol, par eqId.
  var ctx = { reassurance: M.initReassuranceState(), timers: {}, xhr: {}, trees: {}, treeErrors: {}, room: null, current: null, reads: {}, raw: {},
    typePanel: null, typeToast: null };

  // La vue de travail dit si la pièce est toujours affichée (retour d'une action, R1-D de 20.3).
  var host = { isRoomShown: function () { return false; } };

  // --- Tableau des commandes (16.8, 25.1, front v2) : colonnes
  //     Commande | Dans Home Assistant | Rôle dans Jeedom | Type HA, regroupées par entité.
  //     Les commandes ignorées ne sont pas des lignes : elles sont repliées sous le tableau. ---

  // Q5 (décision 2026-10-18) : écran « Types d'équipement » du core Jeedom, ouvert sans rien écrire (D10).
  var GENERIC_TYPES_URL = 'index.php?v=d&p=types';
  // Story 25.7 (Q4) : page de configuration du plugin, où se règle « Plugins exclus » ; ouverture seule, aucune écriture.
  var PLUGIN_CONFIG_URL = 'index.php?v=d&p=plugin&id=jeedom2ha';
  var CELL_CLASSES = 'j2ha-diag-ready j2ha-diag-todo j2ha-diag-blocking j2ha-diag-unknown j2ha-diag-uncovered '
    + 'j2ha-diag-excluded j2ha-diag-disabled';

  function haTypeOfRow(row, entities) {
    var list = Array.isArray(entities) ? entities : [];
    for (var i = 0; i < list.length; i++) {
      if (list[i] && Array.isArray(list[i].command_ids) && list[i].command_ids.indexOf(row.jeedom_cmd_id) !== -1
        && list[i].ha_entity_type) {
        return list[i].ha_entity_type;
      }
    }
    var d = M.readDiagnosticView(row.diagnostic);
    return row.effective_ha || (d && d.ha_entity_type) || row.attendu_ha || null;
  }

  function iconTextCell($cell, cssClass, icon, text) {
    $cell.removeClass(CELL_CLASSES).addClass(cssClass).empty();
    if (icon) {
      $cell.append($('<i class="fas"></i>').addClass(icon)).append(document.createTextNode(' '));
    }
    $cell.append($('<span></span>').text(text));
  }

  // Cellule « Dans Home Assistant » d'une ligne du tableau (catégorie D2). Une commande bloquée ne
  // répète pas sa cause : elle est dite une fois dans l'encart de l'équipement (AC14).
  function renderHaCell($cell, row, category, entities) {
    var type = haTypeOfRow(row, entities);
    if (category === 'published') {
      iconTextCell($cell, 'j2ha-diag-ready', 'fa-check-circle', '{{Publiée}} → ' + M.formatHaDomain(type));
    } else if (category === 'to_apply') {
      iconTextCell($cell, 'j2ha-diag-todo', 'fa-clock', '{{À appliquer}} → ' + M.formatHaDomain(type));
    } else if (category === 'blocked') {
      iconTextCell($cell, 'j2ha-diag-blocking', 'fa-exclamation-triangle', '{{Bloquée}}');
      var code = M.resolveCauseCode(row.diagnostic);
      if (code && !M.REASON_LABELS[code]) {
        $cell.attr('title', code);
      }
    } else if (category === 'excluded') {
      iconTextCell($cell, 'j2ha-diag-excluded', 'fa-eye-slash', '{{Exclue}}');
      $cell.attr('title', M.buildExcludedLabel(row.diagnostic));
    } else if (category === 'disabled') {
      iconTextCell($cell, 'j2ha-diag-disabled', null, '—');
      $cell.attr('title', M.buildDisabledLabel(row.diagnostic));
    } else {
      iconTextCell($cell, 'j2ha-diag-unknown', null, '—');
    }
  }

  function maybeShowReassurance(isBlocking) {
    if (M.shouldShowReassurance(ctx.reassurance, isBlocking)) {
      ctx.reassurance = M.markReassuranceShown(ctx.reassurance);
      $('#j2haSurface_reassurance').show();
    }
  }

  // Colonne « Type HA » : lien discret « auto » / « Personnalisé : Lumière (light) » (front v2, Lot 5). Le clic ouvre le
  // panneau « Corriger le type » (E5) sous la ligne : choix, aperçu, puis « Enregistrer et publier ». Rien n'est écrit au
  // clic ni au choix (fin de l'enregistrement automatique après 400 ms). Jamais proposé quand le réglage est indisponible.
  function renderTypeCell(eqId, row, entities, $haCell) {
    var cmdId = row.jeedom_cmd_id;
    var $td = $('<td class="mo-td-override"></td>');
    var selectorState = M.getOverrideSelectorState(row, entities);
    var forced = row.override_applied;
    // Front v2 (Lot 9a) : « Automatique » (le mot du réglage), plus « auto » qu'on ne devinait pas cliquable.
    // Front v3 (Lot 2) : le libellé est suivi d'un crayon (modifiable, sans phrase).
    var linkText = forced ? '{{Personnalisé :}} ' + M.formatHaDomain(row.effective_ha) : '{{Automatique}}';
    var $revertError = $('<span class="mo-revert-error text-danger"></span>').hide();

    if (!selectorState.active) {
      $td.append($('<span class="j2ha-type-link j2ha-type-unavailable" aria-disabled="true"></span>')
        .attr('title', selectorState.reason).text(linkText));
    } else {
      var $link = $('<a class="j2ha-type-link cursor" role="button" tabindex="0"></a>')
        .attr('title', '{{Changer le type}}').attr('aria-expanded', 'false').text(linkText)
        .append($('<i class="fas fa-pen j2ha-type-pen" aria-hidden="true"></i>'));
      if (forced) {
        $link.addClass('j2ha-type-forced');
      }
      var openPanel = function () {
        openTypePanel({ eqId: eqId, cmdIds: [cmdId], origin: $link });
      };
      $link.on('click', function (event) {
        if (event && event.preventDefault) event.preventDefault();
        openPanel();
      });
      $link.on('keydown', function (event) {
        if (event && (event.key === 'Enter' || event.key === ' ')) {
          if (event.preventDefault) event.preventDefault();
          openPanel();
        }
      });
      $td.append($link);
    }
    if (forced) {
      // Story 20-2 (P1, relecture indépendante PR #210) : ce lien ne porte que sur le type de cette seule
      // commande (route TYPE, 16-8) — jamais sur les réglages de publication de toute l'entité.
      // Reprise X5d (P3) : en cas d'échec, on réaffiche une cause lisible dans `$revertError` et on
      // réattache le gestionnaire pour permettre un nouvel essai.
      var $revertLink = $('<a class="mo-revert-cmd cursor" role="button" tabindex="0"></a>')
        .attr('title', '{{Revenir au type automatique}}').attr('aria-label', '{{Revenir au type automatique}}')
        .append('<i class="fas fa-undo"></i>');
      $td.append($revertLink).append($revertError);
      var attachRevertHandler = function () {
        var run = function () {
          clearRequestError($revertError);
          $revertLink.prop('disabled', true);
          revertCommand(eqId, cmdId, $revertLink, $revertError, attachRevertHandler);
        };
        $revertLink.one('click', run);
        $revertLink.off('keydown');
        onActivationKey($revertLink, function () { if (!$revertLink.prop('disabled')) run(); });
      };
      attachRevertHandler();
    }
    return $td;
  }

  // Éléments `role=button` non natifs : Entrée et Espace valent un clic.
  function onActivationKey($el, handler) {
    $el.on('keydown', function (event) {
      var key = event && event.key;
      if (key === 'Enter' || key === ' ' || key === 'Spacebar') {
        if (event.preventDefault) event.preventDefault();
        handler();
      }
    });
  }

  function renderCommandRow(eqId, row, entities) {
    var cmdId = row.jeedom_cmd_id;
    var category = M.classifyCommandCategory(row);
    var $tr = $('<tr class="mapping-override-cmd"></tr>').attr('data-cmd-id', cmdId).addClass('j2ha-cat-' + category);

    $tr.append($('<td class="mo-td-name"></td>').text(row.cmd_name || ('#' + cmdId)));

    var $haCell = $('<td class="mo-td-diag mo-diag-cell"></td>');
    renderHaCell($haCell, row, category, entities);
    $tr.append($haCell);

    // Rôle dans Jeedom (front v2, Lot 2) : libellé français du type générique, code en infobulle ; vide → « non renseigné »
    // en orange. Lecture seule (D10, jamais écrit).
    $tr.append($('<td class="mo-td-generic"></td>').append(buildRoleCell(row.generic_type)));

    $tr.append(renderTypeCell(eqId, row, entities, $haCell));
    return $tr;
  }

  // Front v2 (Lot 2) : modules purs du côté Home Assistant et du lexique, chargés juste avant ce fichier. Absents (gabarit
  // partiel, extrait chargé seul) : la fiche garde son rendu de 25.1, sans les deux côtés ni les conseils.
  function haSide() {
    var hs = typeof window !== 'undefined' ? window.Jeedom2haHaSide : null;
    return hs && typeof hs.describeHaSide === 'function' ? hs : null;
  }

  function lexicon() {
    var lx = typeof window !== 'undefined' ? window.Jeedom2haLexique : null;
    return lx && typeof lx.causeSheet === 'function' ? lx : null;
  }

  function buildRoleCell(genericType) {
    var $value = $('<span class="mo-native-value" aria-readonly="true"></span>');
    var lx = lexicon();
    var role = lx ? lx.genericTypeLabel(genericType) : null;
    if (role) {
      $value.text(role.label).attr('title', role.code);
    } else if (genericType) {
      $value.text(genericType);
    } else {
      $value.addClass('j2ha-v2-role-missing').text('{{non renseigné}}')
        .attr('title', '{{Aucun type générique : Jeedom ne dit pas à quoi sert cette commande}}');
    }
    return $value;
  }

  // Aperçu d'un type (lecture seule, rien n'est enregistré) : même corps qu'avant (`previewMappingOverride`, eqId, cmdId,
  // haEntityType). Une seule requête en vol par commande ; une requête remplacée ou annulée (fermeture) ne rappelle rien.
  // `done(error, data)` : `error` = message lisible (réseau ou refus), `data` = corps ajax.
  // Front v2 (Lot 9a, revue #397) : `policy` (facultatif) ajoute `publicationPolicy` à l'aperçu — la route d'aperçu du démon
  // accepte le type ET le réglage de publication ensemble (lecture seule). Sans `policy`, corps inchangé.
  function runDryRun(eqId, cmdId, type, done, policy) {
    if (ctx.xhr[cmdId] && typeof ctx.xhr[cmdId].abort === 'function') {
      ctx.xhr[cmdId].abort();
    }
    // Jeton de la requête en vol : posé AVANT l'appel, il rend muette une réponse remplacée ou annulée.
    var slot = { cancelled: false, request: null };
    slot.abort = function () {
      slot.cancelled = true;
      if (slot.request && typeof slot.request.abort === 'function') slot.request.abort();
    };
    ctx.xhr[cmdId] = slot;
    slot.request = $.ajax({
      type: 'POST',
      url: AJAX_URL,
      data: policy ? { action: 'previewMappingOverride', eqId: eqId, cmdId: cmdId, haEntityType: type, publicationPolicy: policy }
        : { action: 'previewMappingOverride', eqId: eqId, cmdId: cmdId, haEntityType: type },
      dataType: 'json',
      success: function (data) {
        if (slot.cancelled) return;
        done(M.readPublicationRequestError(data), data);
      },
      error: function () {
        if (slot.cancelled) return;
        done('{{Le démon ne répond pas.}}', null);
      },
      complete: function () {
        if (ctx.xhr[cmdId] === slot) ctx.xhr[cmdId] = null;
      },
    });
  }

  // Écriture du type d'une commande, seulement sur « Enregistrer et publier » (front v2, Lot 5) : même corps qu'avant
  // (`saveMappingOverride`, eqId, cmdId, haEntityType). `done(error)` : `null` si le démon a enregistré.
  function saveOverride(eqId, cmdId, type, done) {
    $.ajax({
      type: 'POST',
      url: AJAX_URL,
      data: { action: 'saveMappingOverride', eqId: eqId, cmdId: cmdId, haEntityType: type },
      dataType: 'json',
      success: function (resp) {
        done(M.readPublicationRequestError(resp));
      },
      error: function () {
        done('{{Le démon ne répond pas.}}');
      },
    });
  }

  // `$link`/`$errorSlot`/`onFailure` : reprise X5d (P3) — en cas d'échec, réaffiche une cause
  // lisible et réattache le gestionnaire de clic (`onFailure`) plutôt que de laisser le lien
  // inerte ; en cas de succès, recharge l'équipement comme avant la correction.
  function revertCommand(eqId, cmdId, $link, $errorSlot, onFailure) {
    $.ajax({
      type: 'POST',
      url: AJAX_URL,
      data: { action: 'revertMappingOverride', eqId: eqId, cmdId: cmdId },
      dataType: 'json',
      success: function (resp) {
        var error = M.readPublicationRequestError(resp);
        if (error) {
          showRequestError($errorSlot, error);
          if ($link) $link.prop('disabled', false);
          if (onFailure) onFailure();
          return;
        }
        reloadEquipment(eqId);
      },
      error: function () {
        showRequestError($errorSlot, '{{Le démon ne répond pas.}}');
        if ($link) $link.prop('disabled', false);
        if (onFailure) onFailure();
      },
    });
  }

  // Story 20-2 (P1, relecture indépendante PR #210) : affichage/effacement de l'erreur lisible
  // d'une requête de publication, dans le slot dédié posé à côté des boutons d'action.
  function showRequestError($errorSlot, message) {
    if (!$errorSlot || $errorSlot.length === 0) return;
    $errorSlot.text(message).show();
  }

  function clearRequestError($errorSlot) {
    if (!$errorSlot || $errorSlot.length === 0) return;
    $errorSlot.empty().hide();
  }

  // Story 20-2 (P2, revue ClaudeBox X4 point 5) : désactiver TOUT le groupe de boutons
  // pendant une requête est correct (éviter un double clic), mais les réactiver en bloc à
  // la fin ne l'est pas — un bouton déjà grisé pour sa propre cause (ex. « Forcer » déjà
  // publiée, ou hérité d'une exclusion d'équipement, point 4) redevenait cliquable après
  // n'importe quelle requête voisine. On capture l'état `disabled` de chaque bouton avant
  // de tout griser, puis on restaure cet état exact plutôt qu'un `false` générique.
  function disableButtons($buttons) {
    $buttons.each(function () {
      var $button = $(this);
      if ($button.data('j2haPrevDisabled') === undefined) {
        $button.data('j2haPrevDisabled', $button.prop('disabled'));
      }
      $button.prop('disabled', true);
    });
  }

  function restoreButtons($buttons) {
    $buttons.each(function () {
      var $button = $(this);
      var prevDisabled = $button.data('j2haPrevDisabled');
      $button.prop('disabled', prevDisabled === true);
      $button.removeData('j2haPrevDisabled');
    });
  }

  function publicationRequest(eqId, cmdId, policy, $buttons, $errorSlot) {
    disableButtons($buttons);
    clearRequestError($errorSlot);
    var data = { action: 'savePublicationOverride', eqId: eqId, publicationPolicy: policy };
    if (cmdId !== null) data.cmdId = cmdId;
    $.ajax({ type: 'POST', url: AJAX_URL, data: data, dataType: 'json' })
      .always(function () { restoreButtons($buttons); })
      .done(function (resp) {
        var error = M.readPublicationRequestError(resp);
        if (error) { showRequestError($errorSlot, error); return; }
        reloadEquipment(eqId);
      })
      .fail(function () { showRequestError($errorSlot, '{{Le démon ne répond pas.}}'); });
  }

  function revertPublication(eqId, cmdId, $buttons, $errorSlot) {
    disableButtons($buttons);
    clearRequestError($errorSlot);
    var data = { action: 'revertPublicationOverride', eqId: eqId };
    if (cmdId !== null) data.cmdId = cmdId;
    $.ajax({ type: 'POST', url: AJAX_URL, data: data, dataType: 'json' })
      .always(function () { restoreButtons($buttons); })
      .done(function (resp) {
        var error = M.readPublicationRequestError(resp);
        if (error) { showRequestError($errorSlot, error); return; }
        reloadEquipment(eqId);
      })
      .fail(function () { showRequestError($errorSlot, '{{Le démon ne répond pas.}}'); });
  }

  // Story 20-2 (P1, relecture ClaudeBox) : `window.confirm` bloque le navigateur piloté
  // (Playwright ferme les boîtes natives par défaut), ce qui empêche la preuve au clic réel.
  // Modale Bootbox du plugin (même pattern que confirmHaPublishAction, jeedom2ha.js) :
  // fermeture par la croix, Échap ou « Annuler » appellent toutes `onEscape`/`cancel`, qui
  // libère l'état d'attente ; seul « Confirmer » déclenche l'action.
  // `options.disableConfirm` : cause lisible désactivant le bouton Confirmer (AC3 — aperçu
  // de forçage refusé). `content` : chaîne (fallback window.confirm) ou noeud jQuery/DOM
  // construit avec .text() pour les valeurs non fiables (noms de commande Jeedom).
  function confirmPublicationDialog(content, onConfirm, onCancel, options) {
    var opts = options || {};
    var settled = false;
    function cancel() {
      if (settled) return;
      settled = true;
      if (onCancel) onCancel();
    }
    function confirm() {
      if (settled || opts.disableConfirm) return;
      settled = true;
      onConfirm();
    }
    if (typeof bootbox === 'undefined' || !bootbox || typeof bootbox.dialog !== 'function') {
      var text = typeof content === 'string' ? content : '{{Confirmer cette action ?}}';
      if (!opts.disableConfirm && window.confirm(text)) { confirm(); } else { cancel(); }
      return;
    }
    var dialog = bootbox.dialog({
      message: typeof content === 'string' ? '<div>' + content + '</div>' : content,
      onEscape: cancel,
      buttons: {
        cancel: { label: '{{Annuler}}', className: 'btn-default', callback: cancel },
        confirm: { label: '{{Confirmer}}', className: 'btn-primary', callback: confirm },
      },
    });
    if (opts.disableConfirm) {
      dialog.find('[data-bb-handler="confirm"]').prop('disabled', true).attr('title', opts.disableConfirm);
    }
    // Story 20-2 (P2, revue ClaudeBox X4 point 5) : filet de sécurité repris de
    // confirmHaPublishAction (jeedom2ha.js, PR #209) — toute fermeture de la modale non
    // couverte par un bouton (croix, clic sur le fond) doit aussi libérer les boutons
    // grisés ; `cancel()` est idempotent via `settled`, donc sûr même après Confirmer/Annuler.
    if (dialog && typeof dialog.on === 'function') {
      dialog.on('hidden.bs.modal', cancel);
    }
  }

  // Story 20-2 (P2, AC3) : contenu DOM de l'aperçu de forçage — type, validité, commandes
  // qui recevront les ordres (noms lus dans `commands[]`, jamais injectés en HTML brut :
  // les noms de commande sont du texte libre Jeedom, donc potentiellement non fiable).
  function buildForcePreviewContent(state) {
    var $wrap = $('<div></div>');
    $wrap.append($('<p></p>').text('{{Type HA : }}' + (state.ha_entity_type || '{{aucun}}')));
    $wrap.append($('<p></p>').text(state.is_valid
      ? '{{Ce type peut être publié.}}' : '{{Ce type ne peut pas être publié.}}'));
    $wrap.append($('<p></p>').text(state.command_names.length
      ? '{{Commandes qui recevront les ordres : }}' + state.command_names.join(', ')
      : '{{Aucune commande ne recevra d’ordre.}}'));
    if (state.can_confirm) {
      $wrap.append($('<p></p>').text('{{« Toujours » publie cette entité dans Home Assistant.}}'));
    } else {
      $wrap.append($('<p class="text-danger"></p>')
        .text('{{« Toujours » serait refusé : }}' + (state.refusal_reason || '')));
    }
    return $wrap;
  }

  // Story 20-2 (P2, relecture indépendante PR #210) : contenu DOM de la confirmation
  // d'exclusion d'équipement — liste les entités (type + commandes) qui quitteraient Home
  // Assistant, lues dans l'arbre déjà reçu (jamais recalculées ici). Noms de commande en
  // texte libre Jeedom : toujours injectés via .text(), jamais en HTML brut.
  // Story 20-2 (P2, relecture indépendante PR #210) : contenu DOM de l'aperçu de forçage
  // d'ÉQUIPEMENT — une ligne par entité (`view.entities`, champ additif démon AC3), jamais
  // seulement l'entité principale. Même garantie que buildForcePreviewContent : noms de
  // commande en texte libre Jeedom, toujours injectés via .text().
  function buildEquipmentForcePreviewContent(state) {
    var $wrap = $('<div></div>');
    $wrap.append($('<p></p>').text('{{Entités concernées par « Toujours » : }}'));
    var $ul = $('<ul></ul>');
    state.items.forEach(function (item) {
      $ul.append($('<li></li>').text(
        (item.ha_entity_type || '{{Entité HA}}') + ' — ' + item.status_label
        + ' (' + (item.command_names.length ? item.command_names.join(', ') : '{{aucune commande}}') + ')'
      ));
    });
    $wrap.append($ul);
    if (state.can_confirm) {
      $wrap.append($('<p></p>').text('{{« Toujours » publie au moins une entité dans Home Assistant.}}'));
    } else {
      $wrap.append($('<p class="text-danger"></p>').text('{{« Toujours » serait refusé : }}' + (state.refusal_reason || '')));
    }
    return $wrap;
  }

  function buildEquipmentExcludeContent(entities, commands) {
    var leaving = M.entitiesLeavingHomeAssistant(entities, commands);
    var $wrap = $('<div></div>');
    $wrap.append($('<p></p>').text('{{Régler cet équipement sur « Jamais » (exclu de Home Assistant) ?}}'));
    if (leaving.length) {
      $wrap.append($('<p></p>').text('{{Entités qui quitteront Home Assistant : }}'));
      var $ul = $('<ul></ul>');
      leaving.forEach(function (entity) {
        $ul.append($('<li></li>').text((entity.ha_entity_type || '{{Entité HA}}') + ' — ' + entity.command_names.join(', ')));
      });
      $wrap.append($ul);
    }
    return $wrap;
  }

  // Aperçu « Toujours » d'un équipement dont toutes les entités prévues sont déjà publiées : rien ne change maintenant.
  function keepsPublished(state) {
    return !!state && state.can_confirm === false && Array.isArray(state.items) && state.items.length > 0
      && state.items.every(function (item) { return item.already_published === true; });
  }

  function requestPublication(eqId, target, equipment, policy, $buttons, commands, $errorSlot, entities) {
    var cmdId = equipment ? null : target.override_command_id;
    function save() { publicationRequest(eqId, cmdId, policy, $buttons, $errorSlot); }
    function release() { restoreButtons($buttons); }
    if (policy === 'exclude') {
      // Story 20-2 (P2, relecture indépendante PR #210) : à la portée équipement, une
      // entité secondaire publiée doit elle aussi déclencher la confirmation (AC5) —
      // `shouldConfirmPublication` ne regardait que l'entité principale.
      var confirmNeeded = equipment
        ? M.shouldConfirmEquipmentExclude(target.decision || target, entities)
        : M.shouldConfirmPublication(policy, target.decision || target);
      if (!confirmNeeded) {
        save();
        return;
      }
      disableButtons($buttons);
      var excludeContent = equipment
        ? buildEquipmentExcludeContent(entities, commands)
        : '{{Régler cette entité sur « Jamais » (exclue de Home Assistant) ?}}';
      confirmPublicationDialog(excludeContent, save, release);
      return;
    }
    // AC3 : l'aperçu vient du démon et précède toute écriture de forçage.
    disableButtons($buttons);
    clearRequestError($errorSlot);
    // Revue ClaudeBox X4 point 1 : ne jamais envoyer `cmdId` à la portée équipement — jQuery
    // sérialise sinon `null` en `cmdId=` (chaîne vide), que le relais PHP devait auparavant
    // retomber à 0 (d'où le rejet démon 400 systématique sur un forçage d'équipement).
    var previewData = { action: 'previewMappingOverride', eqId: eqId, publicationPolicy: 'force_publish' };
    if (cmdId !== null) previewData.cmdId = cmdId;
    $.ajax({ type: 'POST', url: AJAX_URL, data: previewData, dataType: 'json' })
      .done(function (data) {
        // Story 20-2 (P2, revue ClaudeBox X4 point 6) : le relais PHP lit le corps de la
        // réponse démon quel que soit son code HTTP (400/404/409 inclus) — une requête
        // d'aperçu refusée arrive donc ici en `.done()`, jamais en `.fail()`. Sans cette
        // vérification, `readPreviewOverridden` renvoyait null et masquait la vraie cause
        // démon derrière un message générique, sans jamais griser/restaurer les boutons.
        var requestError = M.readPublicationRequestError(data);
        if (requestError) {
          release();
          showRequestError($errorSlot, requestError);
          return;
        }
        var payload = data && data.result ? data.result : data;
        var view = M.readPreviewOverridden(payload);
        // Relecture indépendante PR #210 (point 3) : à la portée équipement, le forçage vaut
        // pour TOUTES les entités du mapping (`view.entities`, champ additif démon AC3) —
        // `forcePreviewState`/`buildForcePreviewContent` ne couvrent que l'entité principale.
        // Reprise X5d (P3) : `entities` (dernier paramètre de requestPublication, l'arbre déjà
        // reçu) permet à equipmentForcePreviewState de distinguer une entité déjà publiée
        // (aucun changement dû à CE forçage) d'une entité qui le deviendrait réellement.
        var state = equipment ? M.equipmentForcePreviewState(view, commands, entities) : M.forcePreviewState(view, commands);
        var content = equipment ? buildEquipmentForcePreviewContent(state) : buildForcePreviewContent(state);
        // Front v3 (Lot 2, revue Codex #400) : « Toujours » n'est plus grisé sur un équipement déjà entièrement publié. Rien ne
        // change maintenant (`equipmentForcePreviewState` refuse faute de changement), mais le réglage a un effet plus tard : il
        // garde l'équipement publié si le plugin hésite. La confirmation est alors permise, avec un aperçu d'une ligne, et
        // enregistre « Toujours » par la même requête (`savePublicationOverride`, force_publish).
        if (equipment && keepsPublished(state)) {
          state = Object.assign({}, state, { can_confirm: true, refusal_reason: null });
          content = $('<p class="j2ha-eq-force-keep"></p>').text('{{Rien ne change maintenant · restera publié si le plugin hésite plus tard}}');
        }
        var dialogOptions = state.can_confirm ? null
          : { disableConfirm: state.refusal_reason || '{{« Toujours » serait refusé dans l’état actuel.}}' };
        confirmPublicationDialog(content, save, release, dialogOptions);
      })
      .fail(function () {
        release();
        showRequestError($errorSlot, '{{Aperçu indisponible — le démon ne répond pas.}}');
      });
  }

  // « Appliquer » / « Republier » d'un équipement : même route (executeHaAction publier/equipement),
  // même rechargement. Le bouton est réservé pendant l'appel (R1-C). Un résultat `echec` ou
  // `succes_partiel` du démon (HTTP 200) est affiché comme pour les actions de pièce (R2-4).
  function applyEquipment(eqId, $button, $errorSlot) {
    if (eqId === null || eqId === undefined || $button.prop('disabled')) {
      return;
    }
    var room = ctx.room;
    var reservation = setHaActionPendingState($button, '{{En cours...}}');
    clearRequestError($errorSlot);
    $.ajax({ type: 'POST', url: AJAX_URL, data: { action: 'executeHaAction', intention: 'publier',
      portee: 'equipement', selection: JSON.stringify([eqId]) }, dataType: 'json' })
      .always(function () {
        restoreHaActionPendingState($button, reservation);
        // Story 22.2 (Q8 A, P3 de 20-3) : le bandeau de santé est relu quelle que soit l'issue
        // (succès, échec ou réponse refusée) — une opération ratée change le dernier résultat affiché.
        refreshBridgeStatus();
        if (typeof notifyStatesChanged === 'function') notifyStatesChanged();
      })
      .done(function (resp) {
        var error = M.readPublicationRequestError(resp);
        if (error) { showRequestError($errorSlot, error); return; }
        var payload = resp && resp.result && typeof resp.result === 'object' ? resp.result.payload : null;
        if (payload && typeof payload === 'object') {
          showActionFeedback(room, buildHaActionUserMessage(payload), getHaActionAlertLevel(payload));
          if (shouldRefreshPublishedScopeAfterHaAction(payload)) {
            reloadEquipment(eqId);
          }
          return;
        }
        reloadEquipment(eqId);
      })
      .fail(function () { showRequestError($errorSlot, '{{Le démon ne répond pas.}}'); });
  }

  // Un état = un mot + une icône + une teinte (la couleur ne porte jamais seule le sens).
  var STATE_ICONS = {
    published: 'fa-check-circle',
    to_apply: 'fa-clock',
    blocked: 'fa-exclamation-triangle',
    excluded: 'fa-eye-slash',
    disabled: 'fa-pause-circle',
    nothing_to_publish: 'fa-minus-circle',
  };

  function stateWord(state) {
    return $('<span class="j2ha-state-word"></span>').addClass('j2ha-state-' + state)
      .append($('<i class="fas"></i>').addClass(STATE_ICONS[state]))
      .append($('<span class="j2ha-state-text"></span>').text(' ' + M.EQUIPMENT_STATE_LABELS[state]));
  }

  // Ligne de l'équipement déplié : son état (le même mot que le badge) puis ses commandes
  // « 3 publiées · 1 bloquée · 5 ignorées », lues dans son propre arbre.
  // { eq_id: enabled } lu dans `j2haRoomsTree` : « Désactivé » prime sur « Exclu » (R3).
  function roomEnabledById() {
    var map = {};
    ((ctx.room && ctx.room.equipments) || []).forEach(function (eq) {
      map[eq.eq_id] = eq.enabled;
    });
    return map;
  }

  function roomEqTypeById() {
    var map = {};
    ((ctx.room && ctx.room.equipments) || []).forEach(function (eq) {
      map[eq.eq_id] = eq.eq_type || '';
    });
    return map;
  }

  // Story 25.7 (AC4) : la cause d'exclusion, dite UNE fois, sous le badge. Neutre (gris), jamais un état de plus ; absente
  // pour tout état autre que « Exclu » (y compris « Désactivé »). Le lien d'action n'écrit rien (Q4).
  function renderExclusion($panel, tree) {
    var $host = $panel.find('.j2ha-eq-exclusion').first().empty();
    var eqId = tree.jeedom_eq_id;
    var cause = M.exclusionCauseOf(tree, roomEnabledById()[eqId]);
    // `tree` est ici l'entrée agrégée (champ additif de la route 25.2, via `refreshEquipmentState`).
    if (!cause && tree.homekit_kept_in_excluded_room === true) {
      // Story 24.4 (R1) : la cause de « non écarté » est dite, jamais un septième état.
      $host.append($('<div class="j2ha-notice j2ha-notice-neutral j2ha-eq-homekit-kept" role="status"></div>')
        .append($('<i class="fas fa-home" aria-hidden="true"></i>'))
        .append($('<span class="j2ha-notice-text"></span>').text(' ' + '{{Exposé à HomeKit : non écarté par sa pièce}}')));
      return;
    }
    if (!cause) {
      return;
    }
    var eqType = roomEqTypeById()[eqId];
    var name = M.exclusionPluginName(eqType, window.j2haPluginNames);
    var $notice = $('<div class="j2ha-notice j2ha-notice-neutral" role="status"></div>');
    $notice.append($('<i class="fas fa-eye-slash" aria-hidden="true"></i>'));
    // Front v3 (Lot 3) : la phrase de mapping_override.js (ajouts seuls) renvoyait à « Plugins exclus » de la configuration, qui
    // ne règle plus ce qui est publié. Elle est traduite à l'affichage : libellé court + ⓘ, et le bouton mène au panneau
    // « Choisir ce qui est publié », sur le plugin (ou la pièce) en cause.
    var shown = cause.kind === 'plugin'
      ? '{{Plugin exclu}}' + (name ? ' : ' + name : '')
      : M.exclusionCauseText(cause, name, 'sentence');
    $notice.append($('<span class="j2ha-notice-text"></span>').text(' ' + shown));
    if (cause.kind === 'plugin') {
      var tip = '{{Les équipements de ce plugin ne sont pas publiés. À rétablir dans « Choisir ce qui est publié », par plugin.}}';
      $notice.append(document.createTextNode(' ')).append(typeInfo(tip, 'choisir-ce-qui-est-publié'));
      $notice.append(choosePublishedButton({ mode: 'plugin', plugin: eqType || '' }, 'j2ha-open-plugin-config'));
    } else if (cause.kind === 'piece') {
      $notice.append(choosePublishedButton({ mode: 'room', roomId: roomIdOfEquipment(eqId) }, 'j2ha-open-room-choose'));
    }
    $host.append($notice);
  }

  function renderEquipmentCounters($panel, tree) {
    var $host = $panel.find('.j2ha-eq-counters').first().empty();
    if (!tree) {
      return;
    }
    // Front v2 (Lot 2) : le mot d'état n'est plus répété ici (doublon « Publié / Publié ») ; il est dit une fois, par le
    // badge de l'en-tête (qui porte aussi la classe `j2ha-eq-head-state`).
    var labels = M.buildEquipmentCounterLabels(tree, roomEnabledById()[tree.jeedom_eq_id]);
    var $line = $('<div class="j2ha-eq-counter-line"></div>');
    labels.items.forEach(function (item) {
      $line.append($('<span class="j2ha-eq-counter"></span>').text(item));
    });
    if (labels.presence_unknown) {
      $line.append($('<span class="text-muted j2ha-room-counter-unread"></span>').text(labels.presence_unknown));
    }
    $host.append($line);
  }

  // --- Story 20.3 (Q2=A) — actions ciblées déplacées dans la surface ---
  // Mêmes routes (executeHaAction) et mêmes confirmations fortes que l'ancienne synthèse ;
  // les noms (texte libre Jeedom) sont échappés avant d'entrer dans le HTML de la confirmation.

  function escapeHtml(value) {
    return $('<span></span>').text(String(value)).html();
  }

  // R1-B : grise (avec infobulle) un bouton dont l'action n'a pas de sens dans l'état lu de
  // l'arbre. `data-ha-state-blocked` empêche applyHAGating de le réactiver avec le pont.
  function setStateGate($button, allowed, reason) {
    if (allowed) {
      $button.removeAttr('data-ha-state-blocked').removeAttr('title');
    } else {
      $button.attr('data-ha-state-blocked', '1').attr('title', reason || '').prop('disabled', true);
    }
  }

  function reapplyBridgeGating() {
    if (typeof applyHAGating === 'function') {
      applyHAGating(window.jeedom2haLastBridgeStatus || null);
    }
  }

  // Gating d'état des actions de pièce, lu dans les entrées agrégées de la pièce (copie unique de la page B) :
  // aucune lecture, aucune décision recalculée (`M.roomActionState`, R2-3 : actives tant que tout n'est pas lu).
  function refreshRoomGating(room, entries) {
    var $republish = $('.j2ha-wv .j2ha-room-republish').first();
    var $recreate = $('.j2ha-wv .j2ha-room-recreate').first();
    if (!room || ($republish.length === 0 && $recreate.length === 0)) {
      return;
    }
    var list = Array.isArray(entries) ? entries : [];
    var state = M.roomActionState(list, room.equipments.length, list.length);
    if ($republish.length > 0) setStateGate($republish, state.can_republish, state.republish_reason);
    if ($recreate.length > 0) setStateGate($recreate, state.can_recreate, state.recreate_reason);
    reapplyBridgeGating();
  }

  function isRoomOpen(room) {
    return !!room && host.isRoomShown(room.object_id) === true;
  }

  function showRoomFeedback(message, level) {
    var $slot = $('.j2ha-wv .j2ha-room-feedback').first();
    if ($slot.length === 0) {
      return;
    }
    $slot.empty().append($('<div class="alert" role="status"></div>')
      .addClass('alert-' + level).text(message)).show();
  }

  // R1-D : le résultat d'une action est rendu dans le détail de la vue seulement si cette pièce y est
  // toujours affichée ; sinon (autre pièce ou vue refermée), dans la zone d'alerte de la page.
  function showActionFeedback(room, message, level) {
    if (isRoomOpen(room)) {
      showRoomFeedback(message, level);
      return;
    }
    // `showAlert` rend du HTML (jeeDialog.toast) et le message cite des noms libres : échappé (R2-2).
    $('#div_alert').showAlert({ message: escapeHtml(message), level: level });
  }

  // Story 25.4 : les états de la vue suivent la relecture de la page B ; seul l'arbre de l'équipement sélectionné
  // de cette pièce est relu après une action de pièce (D2).
  function reloadRoom(room) {
    if (!isRoomOpen(room) || !ctx.current) {
      return;
    }
    var eqId = ctx.current.eqId;
    if (room.equipments.some(function (eq) { return eq.eq_id === eqId; })) {
      reloadEquipment(eqId);
    }
  }

  function hasValidSelection(selection) {
    return Array.isArray(selection) && selection.length > 0 && selection.every(function (id) {
      return typeof id === 'number' && isFinite(id);
    });
  }

  // `room` est capturée au lancement de l'action (jamais relue dans ctx au retour).
  function runHaAction(room, intention, portee, selection, $button, pendingLabel, reservation, onSuccess) {
    if (!hasValidSelection(selection)) {
      showActionFeedback(room, '{{Action impossible : identifiant introuvable.}}', 'danger');
      if (reservation) restoreHaActionPendingState($button, reservation);
      return;
    }
    var pendingState = reservation || setHaActionPendingState($button, pendingLabel);
    if (reservation) {
      updateHaActionPendingLabel($button, pendingLabel);
    }
    executeHaAction(intention, portee, selection, {
      onSuccess: function (payload) {
        showActionFeedback(room, buildHaActionUserMessage(payload), getHaActionAlertLevel(payload));
        if (shouldRefreshPublishedScopeAfterHaAction(payload) && onSuccess) {
          onSuccess();
        }
        refreshBridgeStatus();
        notifyOverview();
      },
      onError: function (message) {
        showActionFeedback(room, message, 'danger');
        // Story 22.2 (Q8 A, P3 de 20-3) : une action de pièce en échec rafraîchit aussi le bandeau.
        refreshBridgeStatus();
        notifyOverview();
      },
      onComplete: function () {
        restoreHaActionPendingState($button, pendingState);
      },
    });
  }

  // --- Menu d'actions secondaires « ⋯ » (25.1, AC12) ---
  // « Republier » puis, séparé par un trait, « Supprimer de Home Assistant… » (rouge dans le menu
  // seulement). Fermeture : Échap, clic extérieur, choix d'une entrée.
  var openMenu = null;

  function closeMenu() {
    if (!openMenu) {
      return;
    }
    openMenu.removeClass('j2ha-menu-open').find('.j2ha-menu-toggle').attr('aria-expanded', 'false');
    openMenu = null;
  }

  $(document).on('click', function (event) {
    if (openMenu && $(event && event.target).closest('.j2ha-menu-wrap').length === 0) {
      closeMenu();
    }
  });

  function enabledMenuItems($menu) {
    var items = [];
    $menu.find('.j2ha-menu-item').each(function (index, el) {
      if (!$(el).prop('disabled')) {
        items.push(el);
      }
    });
    return items;
  }

  function buildMenu(label, entries) {
    var $wrap = $('<span class="j2ha-menu-wrap"></span>');
    var $toggle = $('<button type="button" class="btn btn-default btn-xs j2ha-menu-toggle" aria-haspopup="menu"></button>')
      .attr('aria-expanded', 'false').attr('aria-label', label).attr('title', label)
      .append('<i class="fas fa-ellipsis-h"></i>');
    var $menu = $('<ul class="j2ha-menu" role="menu"></ul>');
    var buttons = {};
    entries.forEach(function (entry) {
      if (entry.separator) {
        $menu.append('<li class="j2ha-menu-sep" role="separator"></li>');
        return;
      }
      // Front v2 (Lot 2) : une entrée `href` est un lien d'ouverture (aucune écriture, jamais soumise au gating du pont).
      var $button = entry.href
        ? $('<a class="j2ha-menu-item" role="menuitem" target="_blank" rel="noopener"></a>').attr('href', entry.href)
        : $('<button type="button" class="j2ha-menu-item" role="menuitem"></button>');
      // Front v3 (Lot 2) : une entrée sans écriture (« Détails techniques ») n'a pas d'action HA, donc pas de gating.
      if (!entry.href && entry.haAction) $button.attr('data-ha-action', entry.haAction);
      $button.addClass(entry.className || '')
        .append($('<i class="fas"></i>').addClass(entry.icon))
        .append(document.createTextNode(entry.label));
      $button.on('click', function (event) {
        if (event && event.stopPropagation) event.stopPropagation();
        closeMenu();
        if (entry.onClick) entry.onClick($button);
      });
      buttons[entry.key] = $button;
      $menu.append($('<li role="none"></li>').append($button));
    });
    function open() {
      closeMenu();
      $wrap.addClass('j2ha-menu-open');
      $toggle.attr('aria-expanded', 'true');
      openMenu = $wrap;
      var first = enabledMenuItems($menu)[0];
      if (first) {
        $(first).focus();
      }
    }
    $toggle.on('click', function (event) {
      if (event && event.stopPropagation) event.stopPropagation();
      if (openMenu && openMenu.get(0) === $wrap.get(0)) {
        closeMenu();
      } else {
        open();
      }
    });
    function onKey(event) {
      var key = event && event.key;
      if (key === 'Escape') {
        closeMenu();
        $toggle.focus();
        return;
      }
      if (key !== 'ArrowDown' && key !== 'ArrowUp') {
        return;
      }
      if (event.preventDefault) event.preventDefault();
      if (!$wrap.hasClass('j2ha-menu-open')) {
        open();
        return;
      }
      var items = enabledMenuItems($menu);
      if (items.length === 0) {
        return;
      }
      var at = items.indexOf(event.target);
      var next = key === 'ArrowDown' ? (at + 1) % items.length : (at <= 0 ? items.length - 1 : at - 1);
      $(items[next]).focus();
    }
    $toggle.on('keydown', onKey);
    $menu.on('keydown', onKey);
    $wrap.append($toggle).append($menu);
    return { $wrap: $wrap, $toggle: $toggle, $menu: $menu, buttons: buttons };
  }

  // Story 22.2 (Q5 A, CC-55) : « Supprimer de Home Assistant… » retire seulement ; rien n'est recréé
  // ensuite. « Republier » remet l'équipement (ou le prochain relevé de Jeedom s'il est publiable).
  var DELETE_WARNING = '<br><br><strong>{{Attention}}</strong> : {{l\'historique, les tableaux de bord, les automatisations et l\'identifiant liés à ces entités peuvent être impactés.}}'
    + '<br>{{Rien n\'est recréé automatiquement : utilisez « Republier » pour remettre dans Home Assistant ce qui a été supprimé.}}';

  function equipmentDeleteHandler(eqId, eqName) {
    return function ($button) {
      if ($button.prop('disabled')) {
        return;
      }
      var room = ctx.room;
      var reservation = setHaActionPendingState($button, '{{Confirmation en cours…}}');
      confirmHaSupprimerAction(
        '{{Supprimer de Home Assistant}}',
        '{{Supprimer}} "' + escapeHtml(eqName) + '" {{de Home Assistant.}}' + DELETE_WARNING,
        '{{Supprimer 1 équipement}}',
        function () {
          runHaAction(room, 'supprimer', 'equipement', [eqId], $button, '{{Suppression...}}', reservation, function () {
            if (isRoomOpen(room)) reloadEquipment(eqId);
          });
        },
        function () {
          restoreHaActionPendingState($button, reservation);
        }
      );
    };
  }

  // Story 25.8 : élément qui reprend le focus quand la confirmation d'exclusion se referme. Résolu à l'instant du besoin (le
  // détail de la pièce est redessiné après une écriture réussie) : le bouton de l'encart « Pièce exclue » s'il vient de là,
  // sinon le bouton « ⋯ » des actions de la pièce.
  function roomActionsFocus(origin) {
    return function () {
      if (origin === 'notice') {
        var $notice = $('.j2ha-wv .j2ha-wv-room-excluded .j2ha-room-exclude').first();
        if ($notice.length > 0) return $notice;
      }
      return $('.j2ha-wv .j2ha-room-actions .j2ha-menu-toggle').first();
    };
  }

  // Story 25.8 (AC7) : encart neutre du détail d'une pièce exclue, avec « Ne plus exclure la pièce… » (jamais pour « Sans pièce »).
  function buildRoomExcludedNotice(room) {
    if (!room || room.object_id <= 0 || room.excluded !== true) {
      return null;
    }
    var $notice = $('<div class="j2ha-notice j2ha-notice-neutral j2ha-wv-room-excluded" role="status"></div>');
    $notice.append($('<i class="fas fa-eye-slash" aria-hidden="true"></i>'));
    $notice.append($('<span class="j2ha-notice-text"></span>').text(' {{Pièce exclue : ses équipements ne sont pas publiés dans Home Assistant.}}'));
    var $button = $('<button type="button" class="btn btn-default btn-sm j2ha-room-exclude" data-ha-action="exclure-piece"></button>')
      .text('{{Ne plus exclure la pièce…}}');
    $button.on('click', function () {
      if ($button.prop('disabled')) {
        return;
      }
      if (typeof requestRoomExclusion === 'function') {
        requestRoomExclusion(room.object_id, room.object_name, false, $button, roomActionsFocus('notice'));
      }
    });
    $notice.append($button);
    return $notice;
  }

  function buildRoomActions(room) {
    var $wrap = $('<div class="j2ha-room-actions"></div>');
    // La convention daemon object_id=0 (« Sans pièce ») n'est pas une pièce adressable par la
    // portée `piece` (le démon la refuse) : actions de pièce indisponibles, actions par
    // équipement conservées.
    if (room.object_id <= 0) {
      $wrap.append($('<span class="text-muted"></span>')
        .text('{{Republication et suppression de pièce indisponibles pour les équipements sans pièce : utilisez les actions de chaque équipement.}}'));
      return $wrap;
    }
    // Story 25.4 (AC14) : « Republier la pièce » est un bouton du détail ; « Supprimer de Home Assistant… » reste
    // dans le menu « ⋯ » (rouge dans le menu seulement). Mêmes écritures qu'en 25.1 (executeHaAction publier /
    // supprimer, portée `piece`), mêmes confirmations, mêmes réservations de bouton.
    var $republishButton = $('<button type="button" class="btn btn-default btn-sm j2ha-room-republish" data-ha-action="republier"></button>')
      .append($('<i class="fas fa-upload"></i>')).append(document.createTextNode('{{Republier la pièce}}'));
    var onRepublish = function ($republish) {
      if ($republish.prop('disabled')) {
        return;
      }
      var reservation = setHaActionPendingState($republish, '{{Confirmation en cours…}}');
      confirmHaPublishAction(
        '{{Republier la pièce}}',
        escapeHtml(room.object_name) + ' — {{republier les équipements inclus de cette pièce. Confirmer ?}}',
        '{{Republier}}',
        function () {
          runHaAction(room, 'publier', 'piece', [room.object_id], $republish, '{{En cours...}}', reservation, function () {
            reloadRoom(room);
          });
        },
        function () {
          restoreHaActionPendingState($republish, reservation);
        }
      );
    };
    $republishButton.on('click', function () { onRepublish($republishButton); });
    // Story 25.8 (AC7) : l'exclusion de la pièce est la première entrée du menu, AVANT le séparateur et « Supprimer de Home
    // Assistant… ». Elle ne dépend d'aucun état d'équipement : seul le gating du pont (data-ha-action) la grise.
    var roomExcluded = room.excluded === true;
    var menu = buildMenu('{{Autres actions}}', [
      {
        key: 'exclusion', className: 'j2ha-room-exclude', icon: 'fa-eye-slash', haAction: 'exclure-piece',
        label: roomExcluded ? '{{Ne plus exclure la pièce…}}' : '{{Exclure la pièce…}}',
        onClick: function ($item) {
          if (typeof requestRoomExclusion === 'function') {
            requestRoomExclusion(room.object_id, room.object_name, !roomExcluded, $item, roomActionsFocus('toggle'));
          }
        },
      },
      { separator: true },
      {
        key: 'recreate', className: 'j2ha-room-recreate j2ha-menu-danger', icon: 'fa-trash',
        label: '{{Supprimer de Home Assistant…}}', haAction: 'supprimer',
        onClick: function ($recreate) {
          if ($recreate.prop('disabled')) {
            return;
          }
          var reservation = setHaActionPendingState($recreate, '{{Confirmation en cours…}}');
          confirmHaSupprimerAction(
            '{{Supprimer de Home Assistant}}',
            '{{Supprimer}} "' + escapeHtml(room.object_name) + '" {{de Home Assistant : tous les équipements publiés de cette pièce.}}' + DELETE_WARNING,
            '{{Supprimer la pièce}}',
            function () {
              runHaAction(room, 'supprimer', 'piece', [room.object_id], $recreate, '{{Suppression...}}', reservation, function () {
                reloadRoom(room);
              });
            },
            function () {
              restoreHaActionPendingState($recreate, reservation);
            }
          );
        },
      },
    ]);
    // Actifs par défaut (R2-3) : grisés seulement quand toutes les lectures ont abouti sans erreur
    // et qu'aucun équipement ne justifie l'action (voir refreshRoomGating).
    $wrap.append($republishButton);
    $wrap.append(menu.$wrap);
    return $wrap;
  }

  // --- État unique de l'équipement (25.1) : badge, encarts de cause, ligne des ignorées ---

  var ALL_STATE_CLASSES = M.EQUIPMENT_STATES.map(function (state) { return 'j2ha-state-' + state; }).join(' ');

  // Le même mot que les compteurs de la pièce et que la ligne de l'équipement déplié :
  // tous lisent `M.resolveEquipmentState` (aucune règle d'état n'est écrite ici).
  function renderSummary($panel, tree) {
    var resolved = M.resolveEquipmentState(tree, roomEnabledById()[tree.jeedom_eq_id]);
    $panel.removeClass(ALL_STATE_CLASSES).addClass('j2ha-state-' + resolved.state);

    var $badge = $panel.find('.j2ha-eq-publish-badge').first();
    $badge.removeClass(ALL_STATE_CLASSES).addClass('j2ha-state-' + resolved.state);
    $badge.empty()
      .append($('<i class="fas"></i>').addClass(STATE_ICONS[resolved.state]))
      .append($('<span class="j2ha-state-text"></span>').text(' ' + M.EQUIPMENT_STATE_LABELS[resolved.state]));

    // Front v3 (Lot 2) : « N bloquées » n'est plus répété dans l'en-tête ; une mention sur un équipement publié reste dite par
    // l'icône et son info-bulle (le décompte est sur la ligne 2, « n commandes : … »).
    var $mention = $panel.find('.j2ha-eq-blocked-mention').first().empty();
    if (resolved.blocked_mention > 0) {
      var mentionText = resolved.blocked_mention + ' ' + (resolved.blocked_mention > 1 ? 'bloquées' : 'bloquée');
      $mention.append(infoTip($('<i class="fas fa-exclamation-triangle" role="img"></i>').attr('title', mentionText).attr('aria-label', mentionText)));
    }
    renderMentions($panel, tree.jeedom_eq_id, resolved.state);
    return resolved;
  }

  function scrollToCommand($panel, cmdId) {
    var $target = $panel.find('tr.mapping-override-cmd[data-cmd-id="' + cmdId + '"]');
    if ($target.length > 0) {
      // Le seul défilement est celui de la fenêtre (AC16) ; `scroll-margin-top` (CSS) réserve la place
      // de l'en-tête collant.
      var node = $target.get(0);
      if (node && typeof node.scrollIntoView === 'function') {
        node.scrollIntoView({ block: 'center' });
      }
      $target.addClass('j2ha-diag-target-highlight');
      setTimeout(function () { $target.removeClass('j2ha-diag-target-highlight'); }, 2000);
    }
  }

  // --- Front v2 (Lot 2) : fiche de cause, conseils, les deux côtés ---

  // Équipement de la pièce courante ({ eq_id, eq_name, eq_type, enabled }) lu dans `j2haRoomsTree`, ou null.
  function roomEquipment(eqId) {
    var list = (ctx.room && ctx.room.equipments) || [];
    for (var i = 0; i < list.length; i++) {
      if (list[i] && list[i].eq_id === eqId) return list[i];
    }
    return null;
  }

  // Page de l'équipement dans Jeedom (ouverture seule) : connue seulement si le plugin source l'est.
  function equipmentUrl(eqId) {
    var eq = roomEquipment(eqId);
    var type = eq && typeof eq.eq_type === 'string' ? eq.eq_type : '';
    if (!type || !/^[A-Za-z0-9_-]+$/.test(type)) return null;
    return 'index.php?v=d&m=' + type + '&p=' + type + '&id=' + encodeURIComponent(String(eqId));
  }

  // Lien « En savoir plus » : la documentation déjà liée par la page (« Aide »), jamais une adresse construite ici.
  // Front v3 (Lot 5) : le lien « Aide » est l'icône ? de la barre d'état (`.j2ha-v3-help`) depuis le Lot 1 ; l'ancienne ligne
  // d'aide (`.j2ha-help-line`) n'existe plus, le lien ne s'affichait donc jamais. Il vise la section des causes de la doc.
  var HELP_ANCHOR = '#les-causes-de-blocage';
  function helpUrl() {
    var href = $('.j2ha-v3-help').first().attr('href');
    if (typeof href !== 'string' || href.indexOf('https://') !== 0) href = $('.j2ha-help-line a').first().attr('href');
    if (typeof href !== 'string' || href.indexOf('https://') !== 0) return null;
    return href.indexOf('#') < 0 ? href + HELP_ANCHOR : href;
  }

  function pluginNameOf(eqId) {
    var eq = roomEquipment(eqId);
    return M.exclusionPluginName(eq ? eq.eq_type : '', window.j2haPluginNames);
  }

  // --- Front v2 (Lot 5) : panneau « Corriger le type » (écran E5) ---
  // Sous la ligne de la commande : choix (types possibles, types impossibles grisés avec leur raison), aperçu avant / après
  // en entités (lecture seule), puis un seul geste « Enregistrer et publier » = `saveMappingOverride` (ou
  // `revertMappingOverride` pour « Automatique ») puis publication de l'équipement (`executeHaAction` publier / equipement,
  // la fonction de la page, avec son délai client). Rien n'est écrit avant ce clic. Après : bandeau « … · Annuler » pendant
  // 10 s, qui rétablit le réglage précédent puis republie. Les corps des requêtes sont ceux d'avant (contrat 25.4).
  var TYPE_TOAST_MS = 10000;
  var typePanelSeq = 0;

  function typePanelModule() {
    var tp = typeof window !== 'undefined' ? window.Jeedom2haTypePanel : null;
    return tp && typeof tp.buildChoices === 'function' && typeof tp.buildDiff === 'function' ? tp : null;
  }

  function equipmentName(eqId) {
    var raw = ctx.raw[eqId];
    if (raw && typeof raw.eq_name === 'string' && raw.eq_name) return raw.eq_name;
    var tree = ctx.trees[eqId];
    if (tree && tree.eq_name) return tree.eq_name;
    var eq = roomEquipment(eqId);
    return eq && eq.eq_name ? eq.eq_name : '#' + eqId;
  }

  // Première commande de `cmdIds` dont le type peut être réglé ici (sinon le panneau n'est pas proposé).
  function typePanelTarget(eqId, cmdIds) {
    var tree = ctx.trees[eqId];
    if (!tree) return null;
    for (var i = 0; i < cmdIds.length; i++) {
      for (var k = 0; k < tree.commands.length; k++) {
        var row = tree.commands[k];
        if (row.jeedom_cmd_id === cmdIds[i] && M.getOverrideSelectorState(row, tree.entities).active) return row;
      }
    }
    return null;
  }

  function revertType(eqId, cmdId, done) {
    $.ajax({
      type: 'POST',
      url: AJAX_URL,
      data: { action: 'revertMappingOverride', eqId: eqId, cmdId: cmdId },
      dataType: 'json',
      success: function (resp) { done(M.readPublicationRequestError(resp)); },
      error: function () { done('{{Le démon ne répond pas.}}'); },
    });
  }

  // Publication de l'équipement après un réglage : la fonction de la page (`executeHaAction`, délai client inclus) ;
  // repli, si elle manque, sur la même requête que « Republier ». `done({ ok, message, level })`.
  function publishAfterType(eqId, done) {
    var settle = function (payload) {
      done({ ok: shouldRefreshPublishedScopeAfterHaAction(payload), message: buildHaActionUserMessage(payload),
        level: getHaActionAlertLevel(payload) });
    };
    if (typeof executeHaAction === 'function') {
      executeHaAction('publier', 'equipement', [eqId], {
        onSuccess: settle,
        onError: function (message) { done({ ok: false, message: message, level: 'danger' }); },
      });
      return;
    }
    $.ajax({ type: 'POST', url: AJAX_URL, data: { action: 'executeHaAction', intention: 'publier', portee: 'equipement',
      selection: JSON.stringify([eqId]) }, dataType: 'json' })
      .done(function (resp) {
        var error = M.readPublicationRequestError(resp);
        var payload = resp && resp.result && typeof resp.result === 'object' ? resp.result.payload : null;
        if (error || !payload || typeof payload !== 'object') {
          done({ ok: false, message: error || '{{Réponse incomplète du démon.}}', level: 'danger' });
          return;
        }
        settle(payload);
      })
      .fail(function () { done({ ok: false, message: '{{Le démon ne répond pas.}}', level: 'danger' }); });
  }

  function clearTypeToast() {
    var toast = ctx.typeToast;
    ctx.typeToast = null;
    if (!toast) return;
    if (toast.timer) clearTimeout(toast.timer);
    toast.$el.remove();
  }

  // Bandeau de résultat dans l'en-tête de l'équipement (collant, annoncé par aria-live). `undo` : action « Annuler ».
  function showTypeToast(eqId, text, warn, undo) {
    // Revue Codex (#393) : une réponse qui concerne un équipement qui n'est plus affiché ne touche pas au bandeau courant.
    if (!isCurrent(eqId)) return;
    clearTypeToast();
    var $toast = $('<div class="j2ha-v2-toast j2ha-v2-type-toast" role="status" aria-live="polite" tabindex="-1"></div>');
    if (warn) $toast.addClass('is-warn');
    $toast.append($('<span class="j2ha-v2-type-toast-text"></span>').text(text));
    if (undo) {
      var $undo = $('<button type="button" class="j2ha-v2-type-undo"></button>').text('{{Annuler}}');
      $undo.on('click', function () { undo($toast, $undo); });
      $toast.append($undo);
    }
    ctx.current.$panel.find('.j2ha-eq-head').first().append($toast);
    var toast = { $el: $toast, timer: null };
    toast.timer = setTimeout(function () { if (ctx.typeToast === toast) clearTypeToast(); }, TYPE_TOAST_MS);
    ctx.typeToast = toast;
    $toast.focus();
  }

  // Réglage puis publication (« Enregistrer et publier » et « Annuler » du bandeau). `type` null = automatique.
  // `done(error, outcome)` : `error` = l'écriture a échoué (rien n'a été publié) ; sinon `outcome` de la publication.
  function writeTypeThenPublish(eqId, cmdId, type, done) {
    var afterWrite = function (error) {
      if (error) { done(error, null); return; }
      publishAfterType(eqId, function (outcome) {
        refreshBridgeStatus();
        reloadEquipment(eqId);
        done(null, outcome);
      });
    };
    if (type) saveOverride(eqId, cmdId, type, afterWrite);
    else revertType(eqId, cmdId, afterWrite);
  }

  function publicationProblem(outcome) {
    return '{{Réglage enregistré, mais la publication n’a pas abouti :}} ' + outcome.message
      + ' {{Utilisez « Republier » pour réessayer.}}';
  }

  function undoType(eqId, cmdId, previous) {
    return function ($toast, $undo) {
      if ($undo.prop('disabled')) return;
      $undo.prop('disabled', true);
      if (ctx.typeToast && ctx.typeToast.timer) { clearTimeout(ctx.typeToast.timer); ctx.typeToast.timer = null; }
      $toast.find('.j2ha-v2-type-toast-text').first().text('{{Retour au réglage précédent…}}');
      writeTypeThenPublish(eqId, cmdId, previous, function (error, outcome) {
        if (error) {
          showTypeToast(eqId, '{{Le réglage précédent n’a pas pu être rétabli :}} ' + error, true, null);
          return;
        }
        showTypeToast(eqId, outcome.ok ? '{{Réglage précédent rétabli.}}' : publicationProblem(outcome), !outcome.ok, null);
      });
    };
  }

  function closeTypePanel(restoreFocus) {
    var state = ctx.typePanel;
    if (!state) return;
    ctx.typePanel = null;
    if (state.timer) clearTimeout(state.timer);
    var inFlight = ctx.xhr[state.cmdId];
    if (inFlight && typeof inFlight.abort === 'function') inFlight.abort();
    ctx.xhr[state.cmdId] = null;
    // Front v3 (Lot 3, revue Codex) : l'arrière-plan redevient actif, l'écoute d'Échap au niveau du document est retirée.
    if (state.$inert) state.$inert.removeAttr('inert');
    $(document).off('keydown.j2haTypeModal');
    state.$row.remove();
    if (state.$origin && state.$origin.length) {
      state.$origin.attr('aria-expanded', 'false');
      if (restoreFocus) state.$origin.focus();
    }
  }

  function typeLine(tp, line) {
    var $line = $('<div class="j2ha-v2-type-line"></div>');
    $line.append($('<span class="j2ha-v2-entity-type"></span>').text(line.label));
    var caps = tp.capabilityText(line);
    if (caps) $line.append(document.createTextNode(' · ' + caps));
    if (line.entity_id) $line.append(document.createTextNode(' · ')).append($('<code></code>').text(line.entity_id));
    return $line;
  }

  function renderTypeDiff(tp, $preview, diff, onPublishAnyway) {
    $preview.empty();
    var $grid = $('<div class="j2ha-v2-diff"></div>');
    var $before = $('<div class="is-before"></div>').append($('<strong></strong>').text('{{Avant}}'))
      .append($('<div class="j2ha-v2-type-headline"></div>').text(diff.before.headline));
    if (diff.before.empty) $before.append($('<div class="j2ha-v2-small j2ha-v2-muted"></div>').text('{{Rien dans Home Assistant}}'));
    diff.before.published.forEach(function (line) { $before.append(typeLine(tp, line)); });
    var $after = $('<div></div>').append($('<strong></strong>').text('{{Après}}'));
    if (diff.publishable) {
      $after.addClass('is-after').append($('<div class="j2ha-v2-type-headline"></div>').text(diff.after.headline));
      diff.after.published.forEach(function (line) { $after.append(typeLine(tp, line)); });
    } else {
      $after.addClass('is-refused').append($('<div class="j2ha-v2-type-refusal"></div>')
        .text('{{Ce choix ne peut pas être publié :}} ' + diff.refusal + '.'));
    }
    $grid.append($before).append($after);
    $preview.append($grid);
    // Front v2 (Lot 9a, point 9) : refus dû à la CONFIANCE (le plugin hésite, ou le nom contredit les types) : changer le type
    // ne le lèvera pas. La phrase et le bouton mènent à « Publier quand même » au lieu d'un « Enregistrer » grisé muet.
    if (!diff.publishable && diff.publishAnyway && onPublishAnyway) {
      var $anyway = $('<button type="button" class="btn btn-primary btn-xs j2ha-v2-type-anyway"></button>').text('{{Publier quand même}}');
      $anyway.on('click', function () { onPublishAnyway(); });
      // Front v3 (Lot 3) : une ligne ; l'explication passe dans l'info-bulle ⓘ.
      $preview.append($('<div class="j2ha-v2-alert is-info j2ha-v2-type-anyway-box"></div>')
        .append(document.createTextNode('{{Le type seul ne suffit pas}} '))
        .append(typeInfo('{{Le plugin ne publie pas de lui-même un équipement dont il doute ou dont le nom contredit les types. « Publier quand même » garde le type choisi et ajoute le réglage « Toujours » : l’aperçu se met à jour, rien n’est enregistré avant votre validation.}}'))
        .append(document.createTextNode(' ')).append($anyway));
    }
    // Front v3 (Lot 3) : changement d'identifiant = étiquette « ID modifié » + ⓘ (la conséquence est dans l'info-bulle).
    diff.changes.forEach(function (c) {
      $preview.append($('<div class="j2ha-v2-type-idchange"></div>')
        .append($('<span class="j2ha-v2-lbl is-warn j2ha-v3-type-idlabel"></span>').text('{{ID modifié}}')).append(document.createTextNode(' '))
        .append(typeInfo('{{Les automatisations et tableaux de bord Home Assistant qui utilisent l’ancien identifiant seront à reprendre.}}'))
        .append(document.createTextNode(' ')).append($('<code></code>').text(c.from))
        .append(document.createTextNode(' → ')).append($('<code></code>').text(c.to)));
    });
    diff.removed.forEach(function (id) {
      $preview.append($('<div class="j2ha-v2-type-idchange"></div>')
        .append($('<span class="j2ha-v2-lbl is-warn j2ha-v3-type-idlabel"></span>').text('{{Entité retirée}}')).append(document.createTextNode(' '))
        .append(typeInfo('{{Cette entité sera retirée de Home Assistant.}}'))
        .append(document.createTextNode(' ')).append($('<code></code>').text(id)));
    });
  }

  // Tab / Maj+Tab : le focus reste dans la fenêtre « Corriger le type » (premier ↔ dernier élément atteignable).
  function trapTypeFocus(state, event) {
    var root = state.$row && state.$row.get ? state.$row.get(0) : null;
    if (!root || typeof root.querySelectorAll !== 'function') return;
    var nodes = Array.prototype.slice.call(root.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'))
      .filter(function (el) { return el.offsetParent !== null || el.getClientRects().length > 0; });
    if (!nodes.length) return;
    var first = nodes[0];
    var last = nodes[nodes.length - 1];
    var active = typeof document !== 'undefined' ? document.activeElement : null;
    // Front v3 (Lot 6) : la bulle d'aide ouverte depuis la fenêtre (posée sur body) fait partie de la fenêtre pour le clavier.
    if (active && active.closest && active.closest('.j2ha-info-pop')) return;
    var inside = !!active && root.contains(active);
    if (event.shiftKey && (!inside || active === first)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && (!inside || active === last)) {
      event.preventDefault();
      first.focus();
    }
  }

  // Front v3 (Lot 3) : bouton « Choisir ce qui est publié » ouvrant le panneau de la page (fonction de jeedom2ha.js), positionné
  // sur un plugin ou une pièce ; repli, si la page ne l'expose pas, sur la configuration (lien ↗ vers le panneau).
  function choosePublishedButton(opts, cls) {
    var open = typeof window !== 'undefined' && typeof window.openChoosePublished === 'function' ? window.openChoosePublished
      : (typeof openChoosePublished === 'function' ? openChoosePublished : null);
    if (!open) {
      return $('<a class="btn btn-default btn-xs" target="_blank" rel="noopener"></a>').addClass(cls).attr('href', PLUGIN_CONFIG_URL)
        .append($('<i class="fas fa-check-square" aria-hidden="true"></i>')).append(document.createTextNode(' {{Choisir ce qui est publié}}'));
    }
    var $b = $('<button type="button" class="btn btn-default btn-xs"></button>').addClass(cls)
      .attr('title', '{{Ouvrir le panneau « Choisir ce qui est publié »}}')
      .append($('<i class="fas fa-check-square" aria-hidden="true"></i>')).append(document.createTextNode(' {{Choisir ce qui est publié}}'));
    $b.on('click', function () { open(opts || {}); });
    return $b;
  }

  function roomIdOfEquipment(eqId) {
    var rooms = (typeof window !== 'undefined' && window.j2haRoomsTree) || [];
    for (var i = 0; i < rooms.length; i++) {
      var eqs = rooms[i] && rooms[i].equipments ? rooms[i].equipments : [];
      for (var k = 0; k < eqs.length; k++) if (eqs[k].eq_id === eqId) return rooms[i].object_id;
    }
    return null;
  }

  // ⓘ : bouton d'aide (front v3, Lot 6) : la bulle s'ouvre au clic, au toucher ou au clavier (jeedom2ha_infotip.js, chargé
  // avant ce fichier). `doc` : ancre « En savoir plus » de la documentation (par défaut, « Corriger le type »).
  function infoTipApi() { return window.Jeedom2haInfoTip || null; }
  function typeInfo(text, doc, cls) {
    var T = infoTipApi();
    if (!T) return $('<span class="j2ha-info j2ha-v3-info"></span>').addClass(cls || '').attr('data-j2ha-tip', text).attr('title', text);
    return T.button($, text, { cls: cls || 'j2ha-v3-info', doc: doc === undefined ? 'corriger-le-type' : doc });
  }
  // Pastille ou marque purement informative : focusable, cliquable, même bulle ; son `title` reste en complément.
  function infoTip($el) { var T = infoTipApi(); return T ? T.attach($el) : $el; }

  // Choix possibles en boutons radio (« Automatique » et le choix courant toujours visibles) ; types refusés par le démon
  // repliés sous une seule ligne dépliable, noms seulement (la raison est la même pour tous : dite une fois).
  var refusedSeq = 0;
  function buildTypeChoices(tp, state, choices) {
    var $fieldset = $('<fieldset class="j2ha-v2-type-choices"></fieldset>');
    $fieldset.append($('<legend class="j2ha-v2-type-legend"></legend>').text('{{Dans Home Assistant, cette entité est :}}'));
    var name = 'j2haType_' + state.seq;
    state.enabledInputs = [];
    var refused = [];
    choices.forEach(function (choice) {
      if (choice.disabled) {
        refused.push(choice);
        return;
      }
      var $label = $('<label class="j2ha-v2-radio"></label>');
      var $input = $('<input type="radio">').attr('name', name).attr('value', choice.value)
        .attr('data-type', choice.value === '' ? 'auto' : choice.value);
      if (choice.checked) $input.prop('checked', true);
      state.enabledInputs.push($input);
      var $text = $('<span class="j2ha-v2-type-choice"></span>').text(choice.value === '' ? '{{Automatique}}' : choice.label);
      if (choice.hint) $text.append($('<span class="j2ha-v2-small j2ha-v2-muted"></span>').text(' — ' + choice.hint));
      $input.on('change', function () { chooseType(tp, state, choice.value); });
      $label.append($input).append($text);
      $fieldset.append($label);
    });
    if (refused.length > 0) {
      refusedSeq += 1;
      var listId = 'j2haTypeRefused_' + refusedSeq;
      var $list = $('<ul class="j2ha-v2-type-refused-list j2ha-v2-small j2ha-v2-muted"></ul>').attr('id', listId).hide();
      refused.forEach(function (choice) {
        $list.append($('<li></li>').attr('data-type', choice.value).text(choice.label));
      });
      var $toggle = $('<button type="button" class="j2ha-v2-type-refused-toggle j2ha-v2-small" aria-expanded="false"></button>')
        .attr('aria-controls', listId).text('{{Types impossibles pour cet équipement}} (' + refused.length + ') ▸');
      $toggle.on('click', function () {
        var open = $toggle.attr('aria-expanded') === 'true';
        $toggle.attr('aria-expanded', open ? 'false' : 'true')
          .text('{{Types impossibles pour cet équipement}} (' + refused.length + ') ' + (open ? '▸' : '▾'));
        if (open) $list.hide(); else $list.show();
      });
      $fieldset.append($('<div class="j2ha-v2-type-refused"></div>').append($toggle).append($list));
    }
    return $fieldset;
  }

  // Revue Codex (#393) : pendant l'enregistrement, les choix sont figés (le choix affiché reste celui qui est écrit).
  function setTypeChoicesLocked(state, locked) {
    state.enabledInputs.forEach(function ($input) { $input.prop('disabled', locked); });
  }

  function setTypeSaveEnabled(state, enabled) {
    state.$save.prop('disabled', !enabled);
    if (enabled) state.$save.removeAttr('aria-disabled'); else state.$save.attr('aria-disabled', 'true');
  }

  // Un choix ne fait QU'un aperçu (lecture) : jamais d'écriture ici.
  function chooseType(tp, state, value) {
    if (ctx.typePanel !== state || state.busy) return;
    if (state.timer) { clearTimeout(state.timer); state.timer = null; }
    var inFlight = ctx.xhr[state.cmdId];
    if (inFlight && typeof inFlight.abort === 'function') inFlight.abort();
    state.choice = value;
    state.$error.text('').hide();
    setTypeSaveEnabled(state, false);
    if (state.$save) setTypeAnyway(state, false);
    if (value === (state.current || '')) {
      state.$preview.empty().append($('<div class="j2ha-v2-small"></div>').text('{{C’est le réglage actuel : rien ne change.}}'));
      return;
    }
    if (value === '') {
      state.$preview.empty().append($('<div class="j2ha-v2-type-auto"></div>')
        .text('{{Après : le plugin choisira seul}}').attr('title', '{{Comme si aucun réglage n’avait été fait.}}'));
      setTypeSaveEnabled(state, true);
      return;
    }
    state.$preview.empty().append($('<div class="j2ha-v2-small j2ha-v2-muted"></div>')
      .append('<i class="fas fa-spinner fa-spin" aria-hidden="true"></i>').append(document.createTextNode(' {{Calcul de l’aperçu…}}')));
    state.timer = setTimeout(function () {
      state.timer = null;
      runDryRun(state.eqId, state.cmdId, value, function (error, data) {
        if (ctx.typePanel !== state || state.choice !== value) return;
        if (error) {
          state.$preview.empty();
          state.$error.text('{{L’aperçu n’a pas pu être calculé :}} ' + error).show();
          return;
        }
        var diff = tp.buildDiff(data);
        renderTypeDiff(tp, state.$preview, diff, function () { previewTypeAnyway(tp, state, value); });
        maybeShowReassurance(!diff.publishable);
        setTypeSaveEnabled(state, diff.publishable);
      });
    }, DEBOUNCE_MS);
  }

  // Front v2 (Lot 9a, revue #397) : « Publier quand même » DANS le panneau garde le type choisi : aperçu du type ET de
  // « Toujours » ensemble (lecture seule) ; publiable → « Enregistrer et publier quand même » enregistrera les deux.
  function setTypeAnyway(state, on) {
    state.anyway = on === true;
    state.$save.text(state.anyway ? '{{Enregistrer et publier quand même}}' : '{{Enregistrer et publier}}');
  }

  function previewTypeAnyway(tp, state, value) {
    if (ctx.typePanel !== state || state.busy || state.choice !== value) return;
    state.$error.text('').hide();
    setTypeSaveEnabled(state, false);
    state.$preview.empty().append($('<div class="j2ha-v2-small j2ha-v2-muted"></div>')
      .append('<i class="fas fa-spinner fa-spin" aria-hidden="true"></i>').append(document.createTextNode(' {{Calcul de l’aperçu…}}')));
    runDryRun(state.eqId, state.cmdId, value, function (error, data) {
      if (ctx.typePanel !== state || state.choice !== value) return;
      if (error) {
        state.$preview.empty();
        state.$error.text('{{L’aperçu n’a pas pu être calculé :}} ' + error).show();
        return;
      }
      var diff = tp.buildDiff(data);
      renderTypeDiff(tp, state.$preview, diff, null);
      if (diff.publishable) {
        state.$preview.prepend($('<div class="j2ha-v2-alert is-info j2ha-v2-type-anyway-on"></div>')
          .text('{{Aperçu : type choisi + « Toujours »}} ')
          .append(typeInfo('{{Les deux seront enregistrés ensemble, puis l’équipement sera publié.}}')));
        setTypeAnyway(state, true);
      }
      setTypeSaveEnabled(state, diff.publishable);
    }, 'force_publish');
  }

  // Type PUIS « Toujours » (même portée que l'aperçu : la commande du panneau), puis publication comme « Enregistrer et
  // publier ». Corps inchangés : `saveMappingOverride`, puis `savePublicationOverride` (eqId, cmdId, force_publish).
  function writeTypeForceThenPublish(eqId, cmdId, type, done) {
    saveOverride(eqId, cmdId, type, function (error) {
      if (error) { done(error, null, false); return; }
      $.ajax({ type: 'POST', url: AJAX_URL, data: { action: 'savePublicationOverride', eqId: eqId, publicationPolicy: 'force_publish', cmdId: cmdId }, dataType: 'json' })
        .done(function (resp) {
          var refused = M.readPublicationRequestError(resp);
          if (refused) { reloadEquipment(eqId); done(refused, null, true); return; }
          publishAfterType(eqId, function (outcome) {
            refreshBridgeStatus();
            reloadEquipment(eqId);
            done(null, outcome, true);
          });
        })
        .fail(function () { reloadEquipment(eqId); done('{{Le démon ne répond pas.}}', null, true); });
    });
  }

  // Front v3 (Lot 7, revue Codex #406) : réglage de publication porté par la commande ELLE-MÊME avant l'écriture (champ additif
  // `publication_override_own` de l'arbre, présent seulement s'il est posé). null = aucun.
  function ownPublicationOf(eqId, cmdId) {
    var raw = ctx.raw[eqId];
    var rows = raw && Array.isArray(raw.commands) ? raw.commands : [];
    for (var i = 0; i < rows.length; i++) {
      if (rows[i] && rows[i].jeedom_cmd_id === cmdId) {
        var own = rows[i].publication_override_own;
        return own === 'exclude' || own === 'force_publish' ? own : null;
      }
    }
    return null;
  }

  // « Annuler » du bandeau après « Publier quand même » : rétablit EXACTEMENT le réglage de publication de la commande du
  // panneau (Front v3, Lot 7) — retiré seul (`scope: 'command'`) s'il n'existait pas, réécrit s'il valait « Jamais », laissé
  // s'il valait déjà « Toujours » —, puis rétablit le type précédent et republie (chemin de l'annulation existante). Le retour
  // canonique (sans `scope`) purgeait les réglages de TOUTES les commandes de l'entité (une correction de type sœur comprise).
  function undoTypeAnyway(eqId, cmdId, previous, previousPublication) {
    var undoTypeOnly = undoType(eqId, cmdId, previous);
    return function ($toast, $undo) {
      if ($undo.prop('disabled')) return;
      $undo.prop('disabled', true);
      if (ctx.typeToast && ctx.typeToast.timer) { clearTimeout(ctx.typeToast.timer); ctx.typeToast.timer = null; }
      $toast.find('.j2ha-v2-type-toast-text').first().text('{{Retour au réglage précédent…}}');
      if (previousPublication === 'force_publish') {
        $undo.prop('disabled', false);
        undoTypeOnly($toast, $undo);
        return;
      }
      var data = previousPublication === 'exclude'
        ? { action: 'savePublicationOverride', eqId: eqId, publicationPolicy: 'exclude', cmdId: cmdId }
        : { action: 'revertPublicationOverride', eqId: eqId, cmdId: cmdId, scope: 'command' };
      $.ajax({ type: 'POST', url: AJAX_URL, data: data, dataType: 'json' })
        .done(function (resp) {
          var error = M.readPublicationRequestError(resp);
          if (error) { showTypeToast(eqId, '{{Le réglage précédent n’a pas pu être rétabli :}} ' + error, true, null); return; }
          $undo.prop('disabled', false);
          undoTypeOnly($toast, $undo);
        })
        .fail(function () { showTypeToast(eqId, '{{Le réglage précédent n’a pas pu être rétabli :}} {{Le démon ne répond pas.}}', true, null); });
    };
  }

  function saveTypeChoice(tp, state) {
    if (ctx.typePanel !== state || state.busy || state.$save.prop('disabled') || state.choice === undefined) return;
    state.busy = true;
    var type = state.choice || null;
    var previous = state.current;
    var previousPublication = ownPublicationOf(state.eqId, state.cmdId);
    var name = equipmentName(state.eqId);
    state.$error.text('').hide();
    state.$cancel.prop('disabled', true);
    setTypeChoicesLocked(state, true);
    state.$save.prop('disabled', true).html('<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> {{Enregistrement…}}');
    if (state.anyway && type) {
      writeTypeForceThenPublish(state.eqId, state.cmdId, type, function (error, outcome, typeSaved) {
        if (error && !typeSaved) {
          if (ctx.typePanel !== state) return;
          state.busy = false;
          setTypeChoicesLocked(state, false);
          state.$cancel.prop('disabled', false);
          state.$save.prop('disabled', false).text('{{Enregistrer et publier quand même}}');
          state.$error.text('{{Le réglage n’a pas été enregistré :}} ' + error).show();
          return;
        }
        if (ctx.typePanel === state) closeTypePanel(false);
        if (error) {
          // Type enregistré, « Toujours » refusé : on le dit, et l'annulation rétablit le type précédent.
          showTypeToast(state.eqId, '{{Type enregistré, mais « Toujours » a été refusé :}} ' + error, true, undoType(state.eqId, state.cmdId, previous));
          return;
        }
        var undoBoth = undoTypeAnyway(state.eqId, state.cmdId, previous, previousPublication);
        if (outcome.ok) showTypeToast(state.eqId, tp.resultMessage(name, type), false, undoBoth);
        else showTypeToast(state.eqId, publicationProblem(outcome), true, undoBoth);
      });
      return;
    }
    writeTypeThenPublish(state.eqId, state.cmdId, type, function (error, outcome) {
      if (error) {
        if (ctx.typePanel !== state) return;
        state.busy = false;
        setTypeChoicesLocked(state, false);
        state.$cancel.prop('disabled', false);
        state.$save.prop('disabled', false).text('{{Enregistrer et publier}}');
        state.$error.text('{{Le réglage n’a pas été enregistré :}} ' + error).show();
        return;
      }
      // Revue Codex (#393) : ne ferme que le panneau qui a lancé l'opération (un autre a pu être ouvert entre-temps).
      if (ctx.typePanel === state) closeTypePanel(false);
      var undo = undoType(state.eqId, state.cmdId, previous);
      if (outcome.ok) showTypeToast(state.eqId, tp.resultMessage(name, type), false, undo);
      else showTypeToast(state.eqId, publicationProblem(outcome), true, undo);
    });
  }

  /** Ouvre le panneau sous la ligne de la première commande réglable de `cmdIds` ; rend `true` s'il est ouvert. */
  function openTypePanel(options) {
    var o = options || {};
    var tp = typePanelModule();
    var eqId = o.eqId;
    if (!tp || !isCurrent(eqId)) return false;
    var row = typePanelTarget(eqId, Array.isArray(o.cmdIds) ? o.cmdIds : []);
    if (!row) return false;
    var cmdId = row.jeedom_cmd_id;
    var $panel = ctx.current.$panel;
    var $tr = $panel.find('tr.mapping-override-cmd[data-cmd-id="' + cmdId + '"]').first();
    if (!$tr.length) return false;
    if (ctx.typePanel && ctx.typePanel.eqId === eqId && ctx.typePanel.cmdId === cmdId) {
      closeTypePanel(true);
      return true;
    }
    closeTypePanel(false);
    typePanelSeq += 1;
    var $origin = o.origin && o.origin.length ? o.origin : $tr.find('a.j2ha-type-link').first();
    var built = tp.buildChoices(row);
    var titleId = 'j2haTypeTitle_' + typePanelSeq;
    var state = { eqId: eqId, cmdId: cmdId, seq: typePanelSeq, current: built.current, choice: undefined, timer: null, busy: false,
      $origin: $origin };

    // Front v3 (Lot 3) : le panneau s'ouvre en fenêtre posée sur `body` (plus sous la ligne de la commande) : l'en-tête collant
    // de la fiche ne peut plus passer dessus ni transparaître. Rôle « dialog », Échap et clic sur le fond referment.
    var $box = $('<div class="j2ha-v2 j2ha-v2-panel j2ha-v2-type-panel" role="dialog" aria-modal="true"></div>').attr('aria-labelledby', titleId);
    // Front v2 (Lot 9a, regard neuf v2) : le choix vaut pour toute l'ENTITÉ Home Assistant, pas pour une commande : le titre
    // nomme l'entité et la ligne suivante liste les commandes qu'elle regroupe.
    var scope = typeof tp.scopeOf === 'function'
      ? tp.scopeOf(ctx.trees[eqId], ctx.raw[eqId], cmdId, equipmentName(eqId))
      : { name: equipmentName(eqId), commands: [], known: false };
    var $title = $('<h4 class="j2ha-v2-type-title" tabindex="-1"></h4>').attr('id', titleId)
      .text('{{Type dans Home Assistant de}} « ' + (scope.name || equipmentName(eqId)) + ' »');
    // Front v3 (Lot 3) : le bandeau bleu « Le plus durable… » devient un lien icône « Types génériques » dans le coin du titre.
    var waysTip = '{{Le plus durable est de corriger les types génériques dans Jeedom. Ici, vous réglez seulement ce que voit Home Assistant.}}';
    $box.append($('<div class="j2ha-v3-type-head"></div>').append($title)
      .append($('<a class="j2ha-open-generic-types j2ha-v3-type-generic" target="_blank" rel="noopener"></a>').attr('href', GENERIC_TYPES_URL)
        .attr('title', waysTip).attr('aria-label', '{{Types génériques}}')
        .append($('<i class="fas fa-tags" aria-hidden="true"></i>')).append(document.createTextNode(' {{Types génériques}}'))));
    var scopeText = scope.known && scope.commands.length > 0
      ? '{{Pour :}} ' + scope.commands.join(', ')
      : '{{Pour toute l’entité de cet équipement}}';
    $box.append($('<div class="j2ha-v2-small j2ha-v2-muted j2ha-v2-type-cmd j2ha-v2-type-scope"></div>').text(scopeText)
      .attr('title', '{{Le type se règle pour toute l’entité Home Assistant, pas pour une commande seule.}}'));
    $box.append(buildTypeChoices(tp, state, built.choices));
    state.$preview = $('<div class="j2ha-v2-type-preview" aria-live="polite"></div>');
    $box.append(state.$preview);
    state.$error = $('<div class="j2ha-v2-type-error text-danger" role="alert"></div>').hide();
    $box.append(state.$error);
    state.$cancel = $('<button type="button" class="btn btn-default btn-sm j2ha-v2-type-cancel"></button>').text('{{Annuler}}');
    state.$save = $('<button type="button" class="btn btn-success btn-sm j2ha-v2-type-save"></button>').text('{{Enregistrer et publier}}')
      .attr('title', '{{Rien n’est enregistré avant ce clic}}');
    setTypeSaveEnabled(state, false);
    state.$cancel.on('click', function () { if (!state.busy) closeTypePanel(true); });
    state.$save.on('click', function () { saveTypeChoice(tp, state); });
    $box.append($('<div class="j2ha-v2-foot"></div>').append(state.$cancel).append(state.$save));
    // Front v3 (Lot 3, revue Codex) : fenêtre modale au clavier. Tab / Maj+Tab bouclent dans la fenêtre ; Échap la ferme
    // quel que soit l'élément qui a le focus (écoute au niveau du document) ; le focus revient au déclencheur.
    $box.on('keydown', function (event) {
      if (event && event.key === 'Tab') trapTypeFocus(state, event);
      if (event && event.key === 'Escape' && !state.busy && ctx.typePanel === state) {
        if (event.preventDefault) event.preventDefault();
        if (event.stopPropagation) event.stopPropagation();
        closeTypePanel(true);
      }
    });
    $(document).off('keydown.j2haTypeModal').on('keydown.j2haTypeModal', function (event) {
      if (!event || event.key !== 'Escape' || ctx.typePanel !== state || state.busy) return;
      if (event.preventDefault) event.preventDefault();
      closeTypePanel(true);
    });

    var $backdrop = $('<div class="j2ha-v3-type-backdrop" aria-hidden="true"></div>');
    $backdrop.on('click', function () { if (!state.busy && ctx.typePanel === state) closeTypePanel(true); });
    state.$row = $('<div class="j2ha-v3-type-modal"></div>').attr('data-type-panel-for', cmdId).attr('data-eq-id', String(eqId))
      .append($backdrop).append($('<div class="j2ha-v3-type-dialog"></div>').append($box));
    $(document.body).append(state.$row);
    // Arrière-plan inerte pendant l'ouverture (souris, clavier, lecteurs d'écran) ; seuls les éléments rendus inertes ici
    // sont rétablis à la fermeture.
    state.$inert = $(document.body).children().not('.j2ha-v3-type-modal').not('[inert]').not('script').attr('inert', '');
    ctx.typePanel = state;
    $origin.attr('aria-expanded', 'true');
    var $checked = $box.find('input[data-type="' + (state.current || 'auto') + '"]').first();
    // Front v3 (Lot 2) : ouvert depuis la flèche ▾ de « Publier en <type> » : le type est choisi et l'aperçu « type + Toujours »
    // du Lot 9a est lancé tout de suite (lecture seule ; rien n'est écrit avant « Enregistrer et publier quand même »).
    var $anyway = typeof o.anyway === 'string' && o.anyway ? $box.find('input[data-type="' + o.anyway + '"]').first() : $();
    if ($anyway.length) {
      $anyway.prop('checked', true).focus();
      state.choice = o.anyway;
      previewTypeAnyway(tp, state, o.anyway);
      return true;
    }
    if ($checked.length) $checked.focus(); else $title.focus();
    return true;
  }

  // « Corriger le type… » d'une fiche de cause (Lot 2) : le panneau de la première commande réglable, ligne amenée à l'écran.
  function openTypeCorrection($panel, eqId, cmdIds, $origin) {
    var row = typePanelTarget(eqId, cmdIds);
    if (!row) return;
    scrollToCommand($panel, row.jeedom_cmd_id);
    openTypePanel({ eqId: eqId, cmdIds: [row.jeedom_cmd_id], origin: $origin });
  }

  // Le type est-il réglable pour au moins une de ces commandes (sinon « Corriger le type… » n'est pas offert) ?
  function canCorrectType(tree, cmdIds) {
    return tree.commands.some(function (row) {
      return cmdIds.indexOf(row.jeedom_cmd_id) !== -1 && M.getOverrideSelectorState(row, tree.entities).active;
    });
  }

  // --- Front v3 (Lot 2) : bande de cause sur UNE ligne ---
  // Libellé de 4 mots au plus (inventaire critique.md 2.6), ⓘ dont l'info-bulle porte le « quoi » et le « pourquoi » du
  // lexique, au plus deux actions, « En savoir plus ». Le « comment faire » et le décompte « N commandes bloquées : … » passent
  // dans « Détails techniques » (menu ⋯). Les écritures sont celles d'avant (aucune nouvelle route, aucun corps changé).
  var SHORT_CAUSE_LABELS = {
    ambiguous_skipped: '{{Type incertain}}',
    duplicate_generic_types: '{{Type en double}}',
    conflicting_generic_types: '{{Types incompatibles}}',
    switch_state_orphan: '{{État sans ordre}}',
    switch_pairing_ambiguous: '{{Ordres On/Off en double}}',
    probable_skipped: '{{Type pas assez sûr}}',
    low_confidence: '{{Type pas assez sûr}}',
    no_generic_type_configured: '{{Sans type générique}}',
    no_mapping: '{{Appareil non reconnu}}',
    skipped_no_mapping_candidate: '{{Aucun type possible}}',
    no_projection_possible: '{{Commandes inutilisables}}',
    ha_missing_command_topic: '{{Aucun ordre}}',
    ha_missing_state_topic: '{{Pas d’état}}',
    discovery_publish_failed: '{{Envoi échoué}}',
    ha_missing_required_option: '{{Info manquante}}',
    ha_missing_temperature_command_topic: '{{Pas de consigne}}',
    local_availability_publish_failed: '{{Disponibilité non envoyée}}',
    binary_state_without_orders: '{{Ouverture en lecture seule}}',
    speed_not_carried: '{{Vitesse non reprise}}',
  };

  // Libellé court d'une cause (bande) : le nom contredit les types → « Nom « lampe » ≠ type « prise » » si le démon ou l'arbre
  // donnent les deux mots, sinon « Nom ≠ type » ; conseil multiprise → « 3 sorties pilotables ».
  function shortCauseLabel(code, context) {
    var c = context || {};
    if (code === 'name_heuristic_rejection' || code === 'name_type_mismatch') {
      return c.name_word && c.type_word ? '{{Nom}} « ' + c.name_word + ' » ≠ {{type}} « ' + c.type_word + ' »' : '{{Nom ≠ type}}';
    }
    if (code === 'actions_not_linked_to_state') {
      return typeof c.count === 'number' && c.count > 0
        ? c.count + ' ' + (c.count > 1 ? '{{sorties pilotables}}' : '{{sortie pilotable}}') : '{{Sorties pilotables}}';
    }
    return Object.prototype.hasOwnProperty.call(SHORT_CAUSE_LABELS, code) ? SHORT_CAUSE_LABELS[code] : '{{Cause inconnue}}';
  }

  function lowerFirst(text) {
    return typeof text === 'string' && text ? text.charAt(0).toLowerCase() + text.slice(1) : text;
  }

  // Type que publierait « Toujours » pour ces commandes : celui de leur entité (décision du démon), sinon celui de l'équipement,
  // sinon le type écarté par le nom. Jamais deviné : sans type connu, null (le bouton dit alors « Publier quand même »).
  function anywayTypeOf(eqId, tree, cmdIds) {
    var ids = Array.isArray(cmdIds) ? cmdIds : [];
    var list = (tree && tree.entities) || [];
    for (var i = 0; i < list.length; i++) {
      var e = list[i];
      var own = Array.isArray(e.command_ids) && e.command_ids.some(function (id) { return ids.indexOf(id) !== -1; });
      if (own && e.ha_entity_type) return e.ha_entity_type;
    }
    var raw = ctx.raw[eqId];
    var decision = raw && raw.equipment_decision && typeof raw.equipment_decision === 'object' ? raw.equipment_decision : null;
    if (decision && typeof decision.ha_entity_type === 'string' && decision.ha_entity_type) return decision.ha_entity_type;
    var hs = haSide();
    var rejection = hs && raw && typeof hs.rejectionContext === 'function' ? hs.rejectionContext(raw) : null;
    return rejection ? rejection.ha_entity_type : null;
  }

  function publishInLabel(type) {
    return type ? '{{Publier en}} ' + lowerFirst(M.translateHaDomain(type).label) : '{{Publier quand même}}';
  }

  // Autres types plausibles pour la flèche ▾ : ceux que le démon accepte pour cette entité (`override_types_allowed`, via le
  // panneau « Corriger le type »), hors « Automatique » et hors le type du bouton principal.
  function plausibleTypes(eqId, cmdIds, mainType) {
    var tp = typePanelModule();
    var row = typePanelTarget(eqId, cmdIds || []);
    if (!tp || !row) return { row: null, types: [] };
    var types = tp.buildChoices(row).choices.filter(function (choice) {
      return !choice.disabled && choice.value !== '' && choice.value !== mainType;
    }).map(function (choice) { return choice.value; });
    return { row: row, types: types };
  }

  // Split button « Publier en <type> ▾ ». Le bouton principal est « Publier quand même » du Lot 9a de la v2 (segment
  // « Toujours », aperçu du démon puis confirmation, puis « Appliquer ») ; chaque type de la flèche ouvre le panneau « Corriger
  // le type » sur ce type avec « Toujours » (aperçu des deux, « Enregistrer et publier quand même », puis « Annuler » 10 s).
  function buildPublishSplit($panel, eqId, tree, cmdIds, $errorSlot) {
    var mainType = anywayTypeOf(eqId, tree, cmdIds);
    var $split = $('<span class="btn-group j2ha-eq-split"></span>');
    var $main = $('<button type="button" class="btn btn-primary btn-xs j2ha-v2-publish-anyway"></button>')
      .text(publishInLabel(mainType)).attr('title', '{{Réglage « Toujours », aperçu puis confirmation}}');
    $main.on('click', function () { publishAnyway($panel, $errorSlot); });
    $split.append($main);
    var others = plausibleTypes(eqId, cmdIds, mainType);
    if (!others.types.length) return $split;
    var $toggle = $('<button type="button" class="btn btn-primary btn-xs j2ha-eq-split-toggle" aria-haspopup="menu" aria-expanded="false"></button>')
      .attr('aria-label', '{{Autres types}}').attr('title', '{{Autres types}}').append($('<i class="fas fa-caret-down" aria-hidden="true"></i>'));
    var $menu = $('<ul class="j2ha-eq-split-menu" role="menu"></ul>');
    others.types.forEach(function (type) {
      var $item = $('<button type="button" class="j2ha-eq-split-item" role="menuitem"></button>').attr('data-type', type)
        .text(publishInLabel(type));
      $item.on('click', function () {
        closeSplit();
        scrollToCommand($panel, others.row.jeedom_cmd_id);
        openTypePanel({ eqId: eqId, cmdIds: [others.row.jeedom_cmd_id], origin: $toggle, anyway: type });
      });
      $menu.append($('<li role="none"></li>').append($item));
    });
    function closeSplit() {
      $split.removeClass('open j2ha-split-open');
      $toggle.attr('aria-expanded', 'false');
    }
    $toggle.on('click', function (event) {
      if (event && event.stopPropagation) event.stopPropagation();
      var open = $split.hasClass('j2ha-split-open');
      if (open) { closeSplit(); return; }
      $split.addClass('j2ha-split-open');
      $toggle.attr('aria-expanded', 'true');
      $menu.find('.j2ha-eq-split-item').first().focus();
    });
    $menu.on('keydown', function (event) {
      var key = event && event.key;
      var items = $menu.find('.j2ha-eq-split-item').get();
      var at = items.indexOf(event.target);
      if (key === 'Escape') { closeSplit(); $toggle.focus(); return; }
      if (key !== 'ArrowDown' && key !== 'ArrowUp') return;
      if (event.preventDefault) event.preventDefault();
      $(items[key === 'ArrowDown' ? (at + 1) % items.length : (at <= 0 ? items.length - 1 : at - 1)]).focus();
    });
    $split.on('focusout', function () {
      setTimeout(function () { if (!$.contains($split.get(0), document.activeElement)) closeSplit(); }, 0);
    });
    $split.append($toggle).append($menu);
    return $split;
  }

  // Actions de la bande (au plus deux, dans l'ordre du lexique ; une action impossible ici n'est pas affichée).
  function buildBandActions($panel, eqId, tree, sheet, cmdIds, $errorSlot) {
    var out = [];
    sheet.actions.forEach(function (action) {
      var act = action && typeof action === 'object' ? action.key : action;
      if (out.length >= 2) return;
      if (act === 'publish_anyway') {
        out.push(buildPublishSplit($panel, eqId, tree, cmdIds, $errorSlot));
      } else if (act === 'generic_types') {
        out.push($('<a class="btn btn-default btn-xs j2ha-open-generic-types" target="_blank" rel="noopener"></a>')
          .attr('href', GENERIC_TYPES_URL).attr('title', '{{Ouvrir les types génériques}}')
          .append($('<i class="fas fa-external-link-alt" aria-hidden="true"></i>')).append(document.createTextNode(' {{Types génériques}}')));
      } else if (act === 'equipment') {
        var url = equipmentUrl(eqId);
        if (url) {
          out.push($('<a class="btn btn-default btn-xs j2ha-v2-open-equipment" target="_blank" rel="noopener"></a>').attr('href', url)
            .append($('<i class="fas fa-external-link-alt" aria-hidden="true"></i>')).append(document.createTextNode(' {{Ouvrir dans Jeedom}}')));
        }
      } else if (act === 'plugin_config') {
        // Front v3 (Lot 3) : plugin exclu, réglage « En cas de doute » : tout se règle dans le panneau « Choisir ce qui est
        // publié » (la configuration ne règle plus ce qui est publié). Plugin exclu : ouvert « Par plugin », plugin en évidence.
        var sheetCode = sheet && sheet.code ? sheet.code : '';
        var plugin = sheetCode === 'excluded_plugin' ? (roomEqTypeById()[eqId] || '') : null;
        out.push(choosePublishedButton(plugin !== null ? { mode: 'plugin', plugin: plugin } : {}, 'j2ha-v2-open-plugin-config'));
      } else if (act === 'correct_type') {
        if (canCorrectType(tree, cmdIds)) {
          var $correct = $('<button type="button" class="btn btn-default btn-xs j2ha-v2-correct-type"></button>')
            .append($('<i class="fas fa-pen" aria-hidden="true"></i>')).append(document.createTextNode(' {{Changer le type}}'));
          $correct.on('click', function () { openTypeCorrection($panel, eqId, cmdIds, $correct); });
          out.push($correct);
        }
      } else if (act === 'rename') {
        var renameUrl = equipmentUrl(eqId);
        if (renameUrl) {
          out.push($('<a class="btn btn-default btn-xs j2ha-v2-rename" target="_blank" rel="noopener"></a>').attr('href', renameUrl)
            .attr('title', '{{Renommer l’équipement dans Jeedom, puis Relire Jeedom}}')
            .append($('<i class="fas fa-external-link-alt" aria-hidden="true"></i>')).append(document.createTextNode(' {{Renommer}}')));
        }
      } else if (act === 'republish') {
        var $republish = $('<button type="button" class="btn btn-default btn-xs j2ha-v2-republish" data-ha-action="republier"></button>')
          .text('{{Republier}}');
        $republish.on('click', function () { applyEquipment(eqId, $republish, $errorSlot); });
        out.push($republish);
      }
    });
    return out;
  }

  // Front v2 (Lot 9a, point 9) : déclenche le segment « Toujours » de l'équipement (en-tête de la fiche). Indisponible (déjà
  // « Toujours », pièce exclue, type invalide…) : sa raison est dite à la place, jamais un clic muet.
  function publishAnyway($panel, $errorSlot) {
    var $always = $panel.find('.j2ha-eq-controls .j2ha-seg-always').first();
    if (!$always.length) {
      showRequestError($errorSlot, '{{« Publier quand même » est indisponible pour cet équipement.}}');
      return false;
    }
    if ($always.hasClass('j2ha-seg-active')) {
      showRequestError($errorSlot, '{{L’équipement est déjà sur « Toujours » : cliquez sur « Appliquer ».}}');
      return false;
    }
    if ($always.prop('disabled')) {
      showRequestError($errorSlot, '{{« Publier quand même » est indisponible :}} ' + ($always.attr('title') || ''));
      return false;
    }
    $always.trigger('click');
    return true;
  }

  // Une bande : { advice, cmdIds, techLines, extra ($ ajouté après les actions) }.
  function buildCauseBand($panel, eqId, tree, sheet, label, options) {
    var o = options || {};
    var $band = o.advice
      ? $('<div class="j2ha-v2 j2ha-v2-cause is-advice j2ha-eq-band j2ha-eq-advice-sheet" role="status"></div>')
      : $('<div class="j2ha-notice j2ha-notice-warn j2ha-v2 j2ha-v2-cause j2ha-eq-band" role="status"></div>');
    $band.attr('data-cause-code', sheet.code || '');
    $band.append($('<span class="j2ha-eq-band-what j2ha-v2-cause-title"></span>')
      .append($('<i class="fas" aria-hidden="true"></i>').addClass(o.advice ? 'fa-lightbulb' : 'fa-exclamation-triangle'))
      .append(document.createTextNode(' ' + label)));
    var why = [sheet.quoi, sheet.pourquoi].filter(function (t) { return typeof t === 'string' && t; }).join(' ');
    if (why) {
      // Front v3 (Lot 6) : ⓘ cliquable ; « En savoir plus » de la bande vise déjà la section des causes.
      $band.append(typeInfo(why, null, 'j2ha-eq-band-info'));
    }
    $band.append($('<span class="j2ha-eq-band-spacer"></span>'));
    var $error = $('<div class="j2ha-publication-error text-danger j2ha-eq-band-error"></div>').hide();
    var $acts = $('<span class="j2ha-v2-acts j2ha-eq-band-acts"></span>');
    buildBandActions($panel, eqId, tree, sheet, o.cmdIds || [], $error).forEach(function ($a) { $acts.append($a); });
    if (o.extra) $acts.append(o.extra);
    var help = helpUrl();
    if (help) {
      $acts.append($('<a class="j2ha-v2-link j2ha-v2-small j2ha-v2-help" target="_blank" rel="noopener"></a>')
        .attr('href', help).text('{{En savoir plus}}'));
    }
    $band.append($acts).append($error);
    return $band;
  }

  // Lignes techniques d'une cause (menu ⋯ › « Détails techniques ») : libellé du lexique, comment faire, décompte, code.
  function causeTechLines(sheet, options) {
    var o = options || {};
    var lines = [];
    if (sheet.quoi) lines.push(sheet.quoi);
    if (sheet.aide) lines.push('{{Comment faire :}} ' + sheet.aide);
    if (o.countLine) lines.push(o.countLine);
    lines.push('{{Code}} : ' + (sheet.code || '—'));
    if (o.cmdIds && o.cmdIds.length) lines.push('{{Commandes}} : ' + o.cmdIds.map(function (id) { return '#' + id; }).join(', '));
    // Front v2 (Lot 9a, point 8) : le libellé d'origine reste lisible quand l'écran l'a traduit en mots d'utilisateur.
    if (o.originalLine && o.originalLine !== o.countLine) lines.push('{{Libellé d’origine}} : ' + o.originalLine);
    return lines;
  }

  // AC14 (25.1) puis front v3 : la cause d'un blocage est dite UNE fois par cause distincte, en une bande d'une ligne ; le lien
  // vers l'écran des types génériques n'ouvre que la page (le type natif n'est jamais écrit, D10). L'ancre vers la première
  // commande bloquée n'a de sens que si toutes les commandes ne le sont pas. Sans lexique : l'encart de 25.1.
  function renderNotices($panel, tree) {
    var $host = $panel.find('.j2ha-eq-notices').first().empty();
    var groups = M.groupBlockedCauses(tree);
    var summary = M.summarizePublication(tree);
    var lx = lexicon();
    var eqId = tree.jeedom_eq_id;
    var tech = [];
    groups.forEach(function (group, index) {
      var $anchor = null;
      if (index === 0 && summary.first_blocking_cmd_id !== null && !M.allCommandsBlocked(tree)) {
        $anchor = $('<a class="cursor j2ha-goto-blocking" role="button" tabindex="0"></a>')
          .attr('title', '{{Voir la première commande bloquée}}').attr('aria-label', '{{Voir la première commande bloquée}}')
          .append('<i class="fas fa-arrow-down" aria-hidden="true"></i>');
        $anchor.on('click', function () { scrollToCommand($panel, summary.first_blocking_cmd_id); });
        onActivationKey($anchor, function () { scrollToCommand($panel, summary.first_blocking_cmd_id); });
      }
      if (lx) {
        var context = { count: group.count, plugin_name: pluginNameOf(eqId) };
        var hs = haSide();
        var words = hs && ctx.raw[eqId] ? hs.nameTypeWords(ctx.raw[eqId], tree.eq_name) : null;
        if (words) {
          context.name_word = words.name_word;
          context.type_word = words.type_word;
        }
        var sheet = lx.causeSheet(group.code, context);
        // Front v2 (Lot 9a) : la ligne de décompte nomme le mot et le type écarté quand le démon les fournit.
        var rejection = hs && typeof hs.rejectionContext === 'function' && ctx.raw[eqId] ? hs.rejectionContext(ctx.raw[eqId]) : null;
        var countLine = typeof lx.causeLine === 'function' ? lx.causeLine(group, rejection) : M.buildCauseNoticeText(group);
        var $band = buildCauseBand($panel, eqId, tree, sheet, shortCauseLabel(group.code, context),
          { cmdIds: group.command_ids, extra: $anchor });
        if (group.raw_code) $band.find('.j2ha-eq-band-what').first().attr('title', group.raw_code);
        $host.append($band);
        tech = tech.concat(causeTechLines(sheet, { countLine: countLine, originalLine: M.buildCauseNoticeText(group), cmdIds: group.command_ids }));
        return;
      }
      var $notice = $('<div class="j2ha-notice j2ha-notice-warn" role="status"></div>');
      $notice.append($('<i class="fas fa-exclamation-triangle"></i>'));
      var $text = $('<span class="j2ha-notice-text"></span>').text(' ' + M.buildCauseNoticeText(group));
      if (group.raw_code) {
        $text.attr('title', group.raw_code);
      }
      $notice.append($text);
      if (group.generic_types_link) {
        $notice.append($('<a class="btn btn-default btn-xs j2ha-open-generic-types" target="_blank" rel="noopener"></a>')
          .attr('href', GENERIC_TYPES_URL).text('{{Ouvrir les types génériques}}'));
      }
      if ($anchor) $notice.append($anchor);
      $host.append($notice);
    });
    setTechSection($panel, 'cause', tech);
  }

  // Conseils visibles : seulement pour un équipement publié (ou à appliquer) ; « le nom dit… » n'est pas répété s'il est
  // déjà la cause d'un blocage affichée par une fiche.
  function visibleHints(eqId, state) {
    var hs = haSide();
    var raw = ctx.raw[eqId];
    if (!hs || !lexicon() || !raw || (state !== 'published' && state !== 'to_apply')) return [];
    var tree = ctx.trees[eqId];
    var blockedCodes = tree ? M.groupBlockedCauses(tree).map(function (g) { return g.code; }) : [];
    return hs.computeHints(raw).filter(function (hint) {
      return !(hint.code === 'name_type_mismatch' && blockedCodes.indexOf('name_heuristic_rejection') !== -1);
    });
  }

  function renderAdvice($panel, eqId, state) {
    var $host = $panel.find('.j2ha-eq-advice').first().empty();
    var lx = lexicon();
    var tree = ctx.trees[eqId];
    var tech = [];
    if (!lx || !tree) { setTechSection($panel, 'advice', tech); return; }
    visibleHints(eqId, state).forEach(function (hint) {
      var context = { count: hint.count, plugin_name: pluginNameOf(eqId) };
      if (hint.code === 'name_type_mismatch') {
        var words = haSide().nameTypeWords(ctx.raw[eqId], tree.eq_name);
        if (words) {
          context.name_word = words.name_word;
          context.type_word = words.type_word;
        }
      }
      var sheet = lx.causeSheet(hint.code, context);
      $host.append(buildCauseBand($panel, eqId, tree, sheet, shortCauseLabel(hint.code, context), { advice: true, cmdIds: hint.cmd_ids }));
      tech = tech.concat(causeTechLines(sheet, { cmdIds: hint.cmd_ids }));
    });
    setTechSection($panel, 'advice', tech);
  }

  // Front v3 (Lot 2) : l'en-tête ne porte plus la capacité ni la mention « Conseil » : « Pilotable » / « Lecture seule » est dit
  // par entité dans le bloc « Dans Home Assistant », le conseil par sa bande. Le conteneur reste (vide) pour les autres lots.
  function renderMentions($panel) {
    $panel.find('.j2ha-eq-mentions').first().empty();
  }

  function copyText(value, $button) {
    var clipboard = window.navigator && window.navigator.clipboard;
    if (!clipboard || typeof clipboard.writeText !== 'function') {
      return;
    }
    try {
      clipboard.writeText(value).then(function () { $button.text('{{Copié}}'); }, function () {});
    } catch (e) {
      // Presse-papiers refusé par le navigateur : l'identifiant reste lisible et sélectionnable.
    }
  }

  // Info-bulle du « Rien » du bloc « Dans Home Assistant », selon l'état unique (jamais recalculé ici).
  var HA_SIDE_EMPTY = {
    blocked: '{{Rien n’est publié pour l’instant.}}',
    excluded: '{{Rien n’est publié : l’équipement est exclu.}}',
    disabled: '{{Rien n’est publié : l’équipement est désactivé dans Jeedom.}}',
    nothing_to_publish: '{{Aucune commande n’a d’équivalent dans Home Assistant.}}',
    to_apply: '{{Les entités apparaîtront ici une fois le réglage appliqué.}}',
    published: '{{Publié dans Home Assistant.}}',
  };

  // Icône FA5 (cœur) du type d'une entité ; repli neutre.
  var HA_TYPE_ICONS = {
    light: 'fa-lightbulb', switch: 'fa-toggle-on', binary_sensor: 'fa-dot-circle', sensor: 'fa-tachometer-alt',
    cover: 'fa-bars', climate: 'fa-thermometer-half', button: 'fa-hand-pointer', fan: 'fa-fan', lock: 'fa-lock',
    valve: 'fa-tint', alarm_control_panel: 'fa-shield-alt', number: 'fa-sliders-h', select: 'fa-list', scene: 'fa-play-circle',
  };
  var HA_ENTITY_VISIBLE = 3;

  // Une ligne par entité (32 px) : icône du type, libellé (et nom), Pilotable ou Lecture seule, identifiant avec copier.
  function describeEntityLine(d, preview) {
    var $line = $('<div class="j2ha-eq-ha-entity"></div>');
    if (preview) $line.addClass('is-preview');
    $line.append($('<i class="fas j2ha-eq-ha-icon" aria-hidden="true"></i>').addClass(HA_TYPE_ICONS[d.ha_type] || 'fa-cube'));
    var $label = $('<span class="j2ha-eq-ha-label"></span>').append($('<span class="j2ha-v2-entity-type"></span>')
      .text(M.translateHaDomain(d.ha_type).label));
    if (d.name && !preview) {
      $label.append(document.createTextNode(' · ')).append($('<span class="j2ha-free-name"></span>').text(d.name));
    }
    if (preview) $label.append($('<small class="j2ha-eq-ha-preview"></small>').text(' {{(aperçu)}}'));
    if (d.ha_type) $label.attr('title', d.ha_type + (d.command_names.length ? ' — ' + d.command_names.join(', ') : ''));
    $line.append($label);
    if (d.controllable === true) {
      // « lire l'état » n'est pas un geste de pilotage : les verbes vont dans l'info-bulle.
      var verbs = d.verbs.filter(function (v) { return v !== 'lire l’état'; });
      $line.append($('<span class="j2ha-v2-lbl is-plain j2ha-eq-capacity"></span>').attr('title', verbs.join(', '))
        .append($('<i class="fas fa-sliders-h" aria-hidden="true"></i>')).append(document.createTextNode(' {{Pilotable}}')));
    } else if (d.controllable === false) {
      $line.append($('<span class="j2ha-v2-lbl is-plain j2ha-eq-capacity"></span>')
        .append($('<i class="fas fa-eye" aria-hidden="true"></i>')).append(document.createTextNode(' {{Lecture seule}}')));
    }
    if (d.entity_id) {
      var $id = $('<span class="j2ha-v2-entity-id"></span>');
      $id.append($('<code class="j2ha-eq-entity-id"></code>').text(d.entity_id)
        .attr('title', '{{Home Assistant peut ajuster cet identifiant ; vous pouvez le renommer là-bas.}}'));
      if (!preview) {
        var $copy = $('<button type="button" class="j2ha-v2-link j2ha-v2-copy"></button>')
          .attr('aria-label', '{{Copier l’identifiant}}').attr('title', '{{Copier l’identifiant}}')
          .append($('<i class="fas fa-copy" aria-hidden="true"></i>'));
        $copy.on('click', function () { copyText(d.entity_id, $copy); });
        $id.append($copy);
      }
      $line.append($id);
    }
    return $line;
  }

  function entitiesCount(n) {
    return n + ' ' + (n > 1 ? '{{entités}}' : '{{entité}}');
  }

  // Front v3 (Lot 2) : ligne 2 de l'en-tête (plugin · n commandes · ↗ Jeedom · Home Assistant) et bloc « Dans Home Assistant »
  // (une ligne par entité, sans cadre ni phrase, repli au-delà de 3 entités). Un équipement bloqué montre « Rien » et l'aperçu
  // de ce que publierait « Toujours ». L'identifiant n'est affiché que s'il vient du démon (Lot 3) : jamais deviné.
  function renderSides($panel, eqId, state) {
    var $host = $panel.find('.j2ha-eq-sides').first().empty();
    var hs = haSide();
    var raw = ctx.raw[eqId];
    var tree = ctx.trees[eqId];
    if (!hs || !lexicon() || !raw || !tree) return;
    var eq = roomEquipment(eqId);
    var name = tree.eq_name || (eq && eq.eq_name) || ('#' + eqId);
    var jeedom = hs.describeJeedomSide(raw);
    var side = hs.describeHaSide(raw);
    var showEntities = (state === 'published' || state === 'to_apply') && side.entities.length > 0;

    // Ligne 2 de l'en-tête.
    var facts = [];
    var plugin = pluginNameOf(eqId);
    if (plugin) facts.push(plugin);
    facts.push(jeedom.command_count + ' ' + (jeedom.command_count > 1 ? '{{commandes}}' : '{{commande}}'));
    var $facts = $panel.find('.j2ha-eq-meta-facts').first().text(facts.join(' · '));
    if (jeedom.breakdown) $facts.attr('title', jeedom.breakdown); else $facts.removeAttr('title');
    var $links = $panel.find('.j2ha-eq-meta-links').first().empty();
    var url = equipmentUrl(eqId);
    if (url) {
      $links.append($('<a class="j2ha-v2-link j2ha-eq-meta-link j2ha-eq-open-jeedom" target="_blank" rel="noopener"></a>').attr('href', url)
        .attr('title', '{{Ouvrir l’équipement dans Jeedom}}')
        .append($('<i class="fas fa-external-link-alt" aria-hidden="true"></i>')).append(document.createTextNode(' Jeedom')));
    }
    if (showEntities) {
      var where = '{{Dans Home Assistant : Paramètres › Appareils et services › MQTT, puis l’appareil}} « ' + name + ' »';
      $links.append(infoTip($('<span class="j2ha-eq-meta-link j2ha-v2-where-toggle" tabindex="0" role="img"></span>').attr('title', where)
        .attr('aria-label', where).append($('<i class="fas fa-question-circle" aria-hidden="true"></i>'))
        .append(document.createTextNode(' Home Assistant'))));
    }

    // Bloc « Dans Home Assistant ».
    var $ha = $('<section class="j2ha-eq-ha j2ha-eq-side-ha"></section>');
    var $title = $('<h4 class="j2ha-eq-ha-title"></h4>').text('{{Dans Home Assistant}}');
    $ha.append($title);
    if (showEntities) {
      $title.append($('<span class="j2ha-eq-ha-count"></span>').text(entitiesCount(side.entities.length)));
      var $rest = $('<div class="j2ha-eq-ha-more" id="j2haHaMore_' + eqId + '"></div>');
      side.entities.forEach(function (d, i) {
        (i < HA_ENTITY_VISIBLE ? $ha : $rest).append(describeEntityLine(d, false));
      });
      if ($rest.children().length) {
        var hidden = $rest.children().length;
        $rest.hide();
        var $more = $('<button type="button" class="j2ha-v2-link j2ha-eq-ha-toggle" aria-expanded="false"></button>')
          .attr('aria-controls', 'j2haHaMore_' + eqId).text('+ ' + hidden + ' ' + (hidden > 1 ? '{{autres}}' : '{{autre}}'));
        $more.on('click', function () {
          var open = $more.attr('aria-expanded') === 'true';
          $more.attr('aria-expanded', open ? 'false' : 'true').text(open ? '+ ' + hidden + ' ' + (hidden > 1 ? '{{autres}}' : '{{autre}}') : '{{Réduire}}');
          if (open) $rest.hide(); else $rest.show();
        });
        $ha.append($rest).append($more);
      }
    } else {
      $title.append($('<span class="j2ha-v2-lbl is-off j2ha-eq-ha-empty"></span>').attr('title', HA_SIDE_EMPTY[state] || '')
        .append($('<i class="fas fa-ban" aria-hidden="true"></i>')).append(document.createTextNode(' {{Rien}}')));
      if (state === 'blocked' && typeof hs.describePreview === 'function') {
        hs.describePreview(raw).forEach(function (d) {
          $ha.append(describeEntityLine(d, true).attr('title', '{{Aperçu si vous publiez quand même}}'));
        });
      }
    }
    $host.append($ha);

    var techLines = ['{{Équipement Jeedom}} #' + eqId];
    if (jeedom.breakdown) techLines.push(jeedom.breakdown);
    side.entities.forEach(function (d) {
      if (d.unique_id) techLines.push((d.ha_type || '—') + ' : ' + d.unique_id);
    });
    setTechSection($panel, 'ha', techLines);
  }

  // « Détails techniques » de la fiche (menu ⋯) : sections cause, conseil, Home Assistant ; replié par défaut.
  function setTechSection($panel, key, lines) {
    var sections = $panel.data('j2haTech') || {};
    sections[key] = lines || [];
    $panel.data('j2haTech', sections);
    var $host = $panel.find('.j2ha-eq-tech').first();
    var $content = $host.find('.j2ha-v2-tech').first();
    if (!$content.length) {
      $content = $('<div class="j2ha-v2-tech j2ha-v2-small j2ha-v2-muted" role="region"></div>')
        .attr('id', 'j2haEqTech_' + $panel.attr('data-eq-id')).attr('aria-label', '{{Détails techniques}}').hide();
      $panel.data('j2haTechOpen', false);
      $host.append($content);
    }
    $content.empty();
    ['ha', 'cause', 'advice'].forEach(function (k) {
      (sections[k] || []).forEach(function (line) { $content.append($('<div></div>').text(line)); });
    });
  }

  function toggleEquipmentTech($panel) {
    var $content = $panel.find('.j2ha-eq-tech .j2ha-v2-tech').first();
    if (!$content.length) return;
    var open = $panel.data('j2haTechOpen') === true;
    $panel.data('j2haTechOpen', !open);
    if (open) {
      $content.hide();
      return;
    }
    $content.show();
    var node = $content.get(0);
    if (node && typeof node.scrollIntoView === 'function') node.scrollIntoView({ block: 'nearest' });
  }

  // AC15 : les commandes sans équivalent HA ne sont pas des lignes du tableau mais une ligne repliée,
  // dépliable au clic et au clavier.
  function renderIgnored($host, eqId, tree) {
    var summary = M.buildIgnoredSummary(tree);
    if (summary.count === 0) {
      return;
    }
    var listId = 'j2haIgnored_' + eqId;
    var $wrap = $('<div class="j2ha-ignored"></div>');
    var $toggle = $('<button type="button" class="j2ha-ignored-toggle" aria-expanded="false"></button>')
      .attr('aria-controls', listId)
      .append($('<i class="fas fa-caret-right"></i>'))
      .append($('<span class="j2ha-ignored-summary"></span>').text(' ' + summary.text));
    var $list = $('<ul class="j2ha-ignored-list"></ul>').attr('id', listId);
    summary.items.forEach(function (item) {
      var $li = $('<li></li>').append($('<span class="j2ha-free-name"></span>').text(item.name));
      if (item.not_supported_by_plugin) {
        $li.append(document.createTextNode(' — {{non pris en charge par le plugin}}'));
      }
      $list.append($li);
    });
    $toggle.on('click', function () {
      var open = $wrap.hasClass('j2ha-open');
      $wrap.toggleClass('j2ha-open', !open);
      $toggle.attr('aria-expanded', open ? 'false' : 'true');
      $toggle.find('i').first().toggleClass('fa-caret-right', open).toggleClass('fa-caret-down', !open);
    });
    $wrap.append($toggle).append($list);
    $host.append($wrap);
  }

  // --- Réglage de publication : contrôle segmenté Automatique | Toujours | Jamais (25.1, AC10) ---
  // Mêmes routes d'écriture qu'avant (exclure / forcer / revenir) ; le contrôle montre la position
  // courante (jamais déduite de boutons grisés).

  // Front v3 (Lot 2) : une icône par position et une info-bulle d'une phrase (plus de phrase sous le contrôle). Les mots restent
  // ceux du glossaire 25.1 (« Automatique », « Toujours », « Jamais »).
  var SEGMENTS = [
    { key: 'auto', label: '{{Automatique}}', icon: 'fa-magic', help: '{{Le plugin décide}}' },
    { key: 'always', label: '{{Toujours}}', icon: 'fa-thumbtack', help: '{{Publier même si le plugin hésite, maintenant ou plus tard}}' },
    { key: 'never', label: '{{Jamais}}', icon: 'fa-eye-slash', help: '{{Ne jamais publier}}' },
  ];

  function activeSegmentOf(policy) {
    if (policy === 'exclude_eqlogic' || policy === 'exclude_command') return 'never';
    if (policy === 'force_publish') return 'always';
    return 'auto';
  }

  // `state` : M.publicationActionState ; les segments non actifs indisponibles portent leur cause.
  function buildSegmented(ariaLabel, active, state, onSelect, compact, alwaysOpen) {
    var $group = $('<div class="j2ha-seg" role="radiogroup"></div>').attr('aria-label', ariaLabel);
    if (compact) {
      $group.addClass('j2ha-seg-compact');
    }
    // Front v2 (Lot 9a, point 8) : raisons dites en mots d'utilisateur (« commande clé », « projection » traduits à l'affichage).
    var lxw = lexicon();
    var words = function (text) { return lxw && typeof lxw.userWords === 'function' && typeof text === 'string' ? lxw.userWords(text) : text; };
    var availability = {
      auto: { allowed: state.can_revert, reason: words(state.revert_reason) },
      always: { allowed: state.can_force, reason: words(state.force_reason) },
      never: { allowed: state.can_exclude, reason: words(state.exclude_reason) },
    };
    var buttons = [];
    SEGMENTS.forEach(function (segment) {
      var isActive = segment.key === active;
      var $button = $('<button type="button" class="j2ha-seg-btn" role="radio"></button>')
        .addClass('j2ha-seg-' + segment.key).attr('data-value', segment.key)
        .attr('aria-checked', isActive ? 'true' : 'false').attr('tabindex', isActive ? '0' : '-1');
      if (compact) {
        $button.text(segment.label);
      } else {
        $button.attr('title', segment.help)
          .append($('<i class="fas j2ha-seg-icon" aria-hidden="true" style="margin-right:4px"></i>').addClass(segment.icon))
          .append(document.createTextNode(segment.label));
      }
      if (isActive) {
        $button.addClass('j2ha-seg-active');
      }
      // Le segment actif n'écrit jamais : le retour en automatique de tout l'équipement est dans le menu
      // « ⋯ » (« Tout remettre en automatique… »), avec confirmation.
      var usable = !isActive && availability[segment.key].allowed;
      // Front v3 (Lot 2) : « Toujours » de l'ÉQUIPEMENT n'est pas grisé. Sur un équipement publié, il le protège d'une décision
      // future du plugin (le démon accepte le réglage) ; si le démon le refuse, l'aperçu (lecture seule, avant toute écriture) le
      // dit et la confirmation reste désactivée — même chemin qu'avant. Seules exceptions, où il n'aurait aucun effet : un
      // équipement non éligible (`alwaysOpen` faux) et une pièce exclue, qui prime (25.8, D1 : `applyRoomExclusionPrecedence`).
      if (alwaysOpen && segment.key === 'always') usable = !isActive;
      if (!isActive && !usable) {
        $button.prop('disabled', true).addClass('j2ha-seg-disabled').attr('aria-disabled', 'true')
          .attr('title', availability[segment.key].reason || '{{Cette action est sans effet dans l’état courant.}}');
      }
      $button.on('click', function () {
        if ($button.prop('disabled') || isActive) {
          return;
        }
        onSelect(segment.key, $group.find('button'));
      });
      $button.on('keydown', function (event) {
        var key = event && event.key;
        var at = buttons.indexOf($button.get(0));
        var next = -1;
        // Une position indisponible (bouton désactivé) ne peut pas recevoir le focus : on la saute.
        function enabledFrom(from, step) {
          for (var i = 1; i <= buttons.length; i++) {
            var index = (from + step * i + buttons.length * 2) % buttons.length;
            if (!$(buttons[index]).prop('disabled')) return index;
          }
          return -1;
        }
        if (key === 'ArrowRight' || key === 'ArrowDown') next = enabledFrom(at, 1);
        else if (key === 'ArrowLeft' || key === 'ArrowUp') next = enabledFrom(at, -1);
        else if (key === 'Home') next = enabledFrom(-1, 1);
        else if (key === 'End') next = enabledFrom(buttons.length, -1);
        else return;
        if (event.preventDefault) event.preventDefault();
        if (next < 0) {
          return;
        }
        // Roving tabindex : seule la position courante est dans l'ordre de tabulation, les flèches
        // déplacent le focus sans écrire ; Espace / Entrée valident (clic natif du bouton).
        buttons.forEach(function (el) { $(el).attr('tabindex', el === buttons[next] ? '0' : '-1'); });
        $(buttons[next]).focus();
      });
      $group.append($('<span class="j2ha-seg-item"></span>').attr('title', $button.attr('title') || '').append($button));
      buttons.push($button.get(0));
    });
    return $group;
  }

  // Branche le contrôle segmenté d'une cible (équipement ou entité) sur les écritures existantes.
  function buildPublicationControl(eqId, target, equipment, commands, entities, $error, compact) {
    var state = M.publicationActionState(target, equipment);
    var active = activeSegmentOf(target.publication_override || null);
    var ariaLabel = equipment ? '{{Publication dans Home Assistant}}' : '{{Publication de cette entité}}';
    return buildSegmented(ariaLabel, active, state, function (key, $buttons) {
      if (key === 'auto') {
        revertPublication(eqId, equipment ? null : target.override_command_id, $buttons, $error);
      } else {
        requestPublication(eqId, target, equipment, key === 'never' ? 'exclude' : 'force_publish', $buttons, commands, $error, entities);
      }
    }, compact, equipment === true && !compact && target.eligible !== false);
  }

  // Story 20-2 (P2, relecture ClaudeBox AC7) : une entité dont le réglage n'est pas encore appliqué
  // porte l'état « À appliquer » (jamais pour un équipement jamais synchronisé, voir D1).
  function entityIsPendingForDisplay(tree, entity) {
    return M.shouldShowEntityPendingBadge(entity) && tree.sync_status.synced_should_publish !== null;
  }

  // --- Chargement paresseux d'un équipement (un GET par équipement déplié) ---

  // R1-B/E : un arbre illisible (relais en erreur, 404 démon, `jeedom_eq_id` absent) ne propose
  // aucune action et est purgé du cache pour ne jamais servir une donnée périmée.
  function markTreeError($panel, eqId, message) {
    if (eqId !== null && eqId !== undefined && !isNaN(eqId)) {
      delete ctx.trees[eqId];
      ctx.treeErrors[eqId] = true;
    }
    $panel.removeClass(ALL_STATE_CLASSES);
    $panel.find('.j2ha-eq-controls').first().empty();
    $panel.find('.j2ha-eq-cmdlist').first().empty();
    $panel.find('.j2ha-eq-notices').first().empty();
    $panel.find('.j2ha-eq-exclusion').first().empty();
    $panel.find('.j2ha-eq-counters').first().empty();
    $panel.find('.j2ha-eq-blocked-mention').first().empty();
    $panel.find('.j2ha-eq-publish-badge').first().empty();
    $panel.find('.j2ha-eq-mentions').first().empty();
    $panel.find('.j2ha-eq-sides').first().empty();
    $panel.find('.j2ha-eq-advice').first().empty();
    $panel.find('.j2ha-eq-meta-facts').first().empty();
    $panel.find('.j2ha-eq-meta-links').first().empty();
    $panel.find('.j2ha-eq-tech').first().empty();
    $panel.removeData('j2haTech');
    $panel.find('.j2ha-eq-status').first().text(message);
    // Front v2 (Lot 2) : une lecture en échec propose de réessayer (même lecture, rien n'est écrit).
    var $retry = $panel.find('.j2ha-eq-retry').first().empty();
    if (eqId !== null && eqId !== undefined && !isNaN(eqId)) {
      delete ctx.raw[eqId];
      var $button = $('<button type="button" class="btn btn-default btn-xs j2ha-v2-retry"></button>').text('{{Réessayer}}');
      $button.on('click', function () { loadEquipment(eqId); });
      $retry.append($button);
    }
  }

  // Groupes du tableau : une entité = un groupe (ses commandes, dans l'ordre de l'entité). Une commande
  // portée par plusieurs entités n'apparaît que dans la première. Les commandes ignorées en sont exclues
  // (ligne repliée) ; celles qu'aucune entité ne porte forment le groupe « sans entité ».
  function groupCommandRows(tree) {
    var rows = tree.commands.filter(function (row) { return M.classifyCommandCategory(row) !== 'ignored'; });
    var placed = {};
    var groups = tree.entities.map(function (entity) {
      var members = [];
      (entity.command_ids || []).forEach(function (id) {
        rows.forEach(function (row) {
          if (row.jeedom_cmd_id === id && !placed[id]) {
            placed[id] = true;
            members.push(row);
          }
        });
      });
      return { entity: entity, rows: members };
    });
    var rest = rows.filter(function (row) { return !placed[row.jeedom_cmd_id]; });
    return { groups: groups, rest: rest };
  }

  // En-tête de groupe (équipement à plusieurs entités) : domaine traduit + terme technique en petit,
  // effectif, état « À appliquer » de l'entité, contrôle segmenté compact.
  function renderGroupHead(eqId, tree, group) {
    var entity = group.entity;
    var domain = M.translateHaDomain(entity.ha_entity_type);
    var $td = $('<td class="j2ha-group-cell" colspan="4"></td>');
    var $name = $('<span class="j2ha-group-name"></span>').append($('<strong></strong>').text(domain.label));
    if (domain.technical) {
      $name.append(document.createTextNode(' ')).append($('<small class="j2ha-tech"></small>').text(domain.technical));
    }
    $td.append($name);
    $td.append($('<span class="j2ha-group-count text-muted"></span>')
      .text(' ' + group.rows.length + ' ' + (group.rows.length > 1 ? '{{commandes}}' : '{{commande}}')));
    if (entityIsPendingForDisplay(tree, entity)) {
      $td.append($('<span class="j2ha-chip j2ha-chip-to_apply j2ha-entity-pending"></span>')
        .append($('<i class="fas fa-clock"></i>')).append(document.createTextNode(' {{À appliquer}}')));
    }
    var $error = $('<div class="j2ha-publication-error text-danger"></div>').hide();
    $td.append(buildPublicationControl(eqId, entity, false, tree.commands, undefined, $error, true));
    $td.append($error);
    return $('<tr class="j2ha-group-head"></tr>').attr('data-entity-type', entity.ha_entity_type || '').append($td);
  }

  function renderCommandTable($list, eqId, tree) {
    var $table = $('<table class="table table-condensed j2ha-cmd-table"></table>');
    var $thead = $('<thead></thead>');
    $thead.append($('<tr></tr>')
      .append($('<th class="mo-th-name"></th>').text('{{Commande}}'))
      .append($('<th class="mo-th-diag"></th>').text('{{Dans Home Assistant}}'))
      .append($('<th class="mo-th-generic"></th>').text('{{Rôle dans Jeedom}}'))
      .append($('<th class="mo-th-override"></th>').text('{{Type HA}}')));
    $table.append($thead);
    var $tbody = $('<tbody></tbody>');
    var grouped = groupCommandRows(tree);
    // L'en-tête de groupe n'existe que s'il porte une information : plusieurs entités, ou une entité
    // unique dont le réglage de publication (posé sur sa commande) n'est pas celui de l'équipement.
    var withHeads = tree.entities.length > 1
      || (tree.entities.length === 1 && !M.entityActionsDuplicateEquipment(tree, tree.entities[0]));
    grouped.groups.forEach(function (group) {
      if (withHeads) {
        $tbody.append(renderGroupHead(eqId, tree, group));
      }
      group.rows.forEach(function (row) { $tbody.append(renderCommandRow(eqId, row, tree.entities)); });
    });
    if (grouped.rest.length > 0) {
      if (withHeads) {
        $tbody.append($('<tr class="j2ha-group-head"></tr>').append(
          $('<td class="j2ha-group-cell" colspan="4"></td>').append($('<strong></strong>').text('{{Sans entité Home Assistant}}'))));
      }
      grouped.rest.forEach(function (row) { $tbody.append(renderCommandRow(eqId, row, tree.entities)); });
    }
    $table.append($tbody);
    $list.append($table);
  }

  // « Tout remettre en automatique… » : même route que l'ancien clic sur « Automatique » actif
  // (revertPublicationOverride sans commande), désormais derrière une confirmation qui liste ce qui
  // sera retiré : exclusions, forçages, types Home Assistant imposés.
  function revertAllHandler(eqId, normalized, $button, $error) {
    if ($button.prop('disabled')) {
      return;
    }
    var entities = normalized.entities || [];
    var exclusions = entities.filter(function (e) { return e.publication_override === 'exclude_eqlogic' || e.publication_override === 'exclude_command'; }).length;
    var forcings = entities.filter(function (e) { return e.publication_override === 'force_publish'; }).length;
    var types = normalized.commands.filter(function (c) { return c.override_applied; }).length;
    var eqOverride = normalized.equipment_publication_override || null;
    var $content = $('<div></div>');
    $content.append($('<p></p>').text('{{Tout remettre en automatique : les réglages manuels de cet équipement seront retirés.}}'));
    var $list = $('<ul></ul>');
    if (eqOverride === 'exclude') $list.append($('<li></li>').text('{{Exclusion de l’équipement}}'));
    if (eqOverride === 'force_publish') $list.append($('<li></li>').text('{{Forçage de l’équipement}}'));
    if (exclusions > 0) $list.append($('<li></li>').text('{{Exclusions d’entités}} : ' + exclusions));
    if (forcings > 0) $list.append($('<li></li>').text('{{Forçages d’entités}} : ' + forcings));
    if (types > 0) $list.append($('<li></li>').text('{{Types Home Assistant imposés}} : ' + types));
    $content.append($list);
    var reservation = setHaActionPendingState($button, '{{Confirmation en cours…}}');
    confirmPublicationDialog($content, function () {
      restoreHaActionPendingState($button, reservation);
      revertPublication(eqId, null, $button, $error);
    }, function () {
      restoreHaActionPendingState($button, reservation);
    });
  }

  // Story 25.8 (D1, Q10) : une pièce exclue prime sur « Toujours ». Les segments grisés « Toujours » / « Jamais » d'un équipement
  // exclu PAR SA PIÈCE le disent (cause lue par `exclusionCauseOf`, 25.7) ; `publicationActionState` (25.1) n'est pas modifié et un
  // réglage « Toujours » déjà posé reste la position courante (aucune écriture ici).
  var ROOM_PRECEDENCE_REASON = '{{Pièce exclue : elle prime sur ce réglage.}}';

  function applyRoomExclusionPrecedence($group, tree, eqId) {
    var cause = M.exclusionCauseOf(tree, roomEnabledById()[eqId]);
    if (!cause || cause.kind !== 'piece') {
      return;
    }
    $group.find('.j2ha-seg-btn').each(function (_i, el) {
      var $button = $(el);
      var key = $button.attr('data-value');
      // Front v3 (Lot 2) : « Toujours », qui n'est plus grisé d'office, l'est ici : la pièce exclue prime, il serait sans effet.
      if (key === 'always' && !$button.hasClass('j2ha-seg-active') && !$button.hasClass('j2ha-seg-disabled')) {
        $button.prop('disabled', true).addClass('j2ha-seg-disabled').attr('aria-disabled', 'true');
      }
      if ((key === 'always' || key === 'never') && $button.hasClass('j2ha-seg-disabled')) {
        $button.attr('title', ROOM_PRECEDENCE_REASON);
        $button.closest('.j2ha-seg-item').attr('title', ROOM_PRECEDENCE_REASON);
      }
    });
  }

  // En-tête collant de l'équipement déplié : réglage de publication (contrôle segmenté), « Appliquer »
  // seulement quand un réglage attend, menu « ⋯ » (Republier, Supprimer de Home Assistant…).
  function renderControls($panel, eqId, normalized, resolved) {
    var $host = $panel.find('.j2ha-eq-controls').first().empty();
    // X6b (P2, relecture indépendante PR #215) : la cible équipement est construite par
    // `equipmentPublicationTarget` (lit `eligible` + `equipment_publication_override` de l'arbre, en
    // plus du veto porté par les entités/commandes).
    var $error = $('<div class="j2ha-publication-error text-danger"></div>').hide();
    var target = M.equipmentPublicationTarget(normalized);
    // Front v3 (Lot 2) : ni libellé « Publication dans Home Assistant » (nom accessible du groupe), ni phrase d'aide sous le
    // contrôle : chaque segment porte son info-bulle.
    var $publicationControl = buildPublicationControl(eqId, target, true, normalized.commands, normalized.entities, $error, false);
    applyRoomExclusionPrecedence($publicationControl, normalized, eqId);
    $host.append($publicationControl);
    var actionState = M.equipmentActionState(normalized);
    var eqName = normalized.eq_name || $panel.find('.j2ha-eq-name').first().text();
    if (resolved.state === 'to_apply') {
      // Même route que « Republier » (executeHaAction publier/equipement), même rechargement.
      var $apply = $('<button type="button" class="btn btn-primary btn-xs j2ha-eq-apply" data-ha-action="republier"></button>')
        .text('{{Appliquer}}');
      $apply.on('click', function () { applyEquipment(eqId, $apply, $error); });
      $host.append($apply);
    }
    var menu = buildMenu('{{Autres actions}}', [
      {
        key: 'republish', className: 'j2ha-eq-republish', icon: 'fa-upload', label: '{{Republier}}', haAction: 'republier',
        onClick: function ($button) { applyEquipment(eqId, $button, $error); },
      },
      {
        key: 'revert', className: 'j2ha-eq-revert-all', icon: 'fa-undo', label: '{{Tout remettre en automatique…}}',
        haAction: 'revert', onClick: function ($button) { revertAllHandler(eqId, normalized, $button, $error); },
      },
    ].concat(equipmentUrl(eqId) ? [{
      key: 'open', className: 'j2ha-v2-open-equipment', icon: 'fa-external-link-alt',
      label: '{{Ouvrir l’équipement dans Jeedom}}', href: equipmentUrl(eqId),
    }] : []).concat([
      // Front v3 (Lot 2) : « Détails techniques » (codes, identifiants, décomptes d'origine) passe dans le menu ⋯.
      {
        key: 'tech', className: 'j2ha-eq-tech-toggle', icon: 'fa-code', label: '{{Détails techniques}}',
        onClick: function () { toggleEquipmentTech($panel); },
      },
      { separator: true },
      {
        key: 'recreate', className: 'j2ha-eq-recreate j2ha-menu-danger', icon: 'fa-trash',
        label: '{{Supprimer de Home Assistant…}}', haAction: 'supprimer', onClick: equipmentDeleteHandler(eqId, eqName),
      },
    ]));
    // Un réglage en attente reste applicable (y compris une exclusion à appliquer) ; hors de ce cas,
    // un équipement désactivé ou exclu n'a rien à republier.
    setStateGate(menu.buttons.republish, resolved.state === 'to_apply' || actionState.can_republish, actionState.republish_reason);
    setStateGate(menu.buttons.recreate, actionState.can_recreate, actionState.recreate_reason);
    var revertState = M.publicationActionState(target, true);
    setStateGate(menu.buttons.revert, revertState.can_revert, revertState.revert_reason);
    $host.append(menu.$wrap);
    $host.append($error);
    // Les boutons viennent d'être ajoutés après l'ouverture de la vue : ils suivent le même gating
    // que les boutons globaux (pont indisponible, relecture en cours), sinon ils resteraient actifs.
    reapplyBridgeGating();
  }

  function renderEquipmentTree($panel, tree) {
    var normalized = M.normalizeTree(tree);
    var eqId = normalized.jeedom_eq_id;
    if (eqId === null || eqId === undefined) {
      markTreeError($panel, parseInt($panel.attr('data-eq-id'), 10),
        '{{Impossible de lire la configuration de cet équipement.}}');
      return;
    }
    // Front v2 (Lot 5) : le tableau est redessiné, le panneau « Corriger le type » ouvert sous une ligne est fermé.
    closeTypePanel(false);
    var $list = $panel.find('.j2ha-eq-cmdlist').first().empty();

    ctx.trees[eqId] = normalized;
    // Arbre brut gardé par référence (aucune copie) : champs additifs du démon lus par le côté Home Assistant.
    ctx.raw[eqId] = tree;
    delete ctx.treeErrors[eqId];
    $panel.find('.j2ha-eq-retry').first().empty();

    var resolved = renderSummary($panel, normalized);
    renderExclusion($panel, normalized);
    renderEquipmentCounters($panel, normalized);
    renderSides($panel, eqId, resolved.state);
    renderNotices($panel, normalized);
    renderAdvice($panel, eqId, resolved.state);
    renderControls($panel, eqId, normalized, resolved);

    if (!normalized.mapped && normalized.commands.length === 0) {
      $list.append($('<div class="text-muted j2ha-empty"></div>')
        .text('{{Aucune commande à configurer pour cet équipement.}}'));
      return;
    }

    renderCommandTable($list, eqId, normalized);
    renderIgnored($list, eqId, normalized);
  }

  function isCurrent(eqId) {
    return !!ctx.current && ctx.current.eqId === eqId;
  }

  // UNIQUE site de lecture d'un arbre unitaire (Story 25.4, AC6, D3) : appelée à la SÉLECTION d'un équipement et
  // après une écriture sur lui, jamais pour remplir l'arbre ni à la sélection d'une pièce. Une lecture en vol pour
  // le même équipement n'est pas doublée (`again` : une écriture a eu lieu pendant la lecture, une relecture suit) ;
  // une réponse qui arrive après que la sélection a changé est ignorée, sans erreur et sans toucher l'affichage.
  function loadEquipment(eqId, again) {
    if (!isCurrent(eqId)) {
      return;
    }
    ctx.current.$panel.find('.j2ha-eq-status').first().text('{{Chargement…}}');
    if (ctx.reads[eqId]) {
      if (again) {
        ctx.reads[eqId].again = true;
      }
      return;
    }
    var slot = { again: false };
    ctx.reads[eqId] = slot;
    // Rend `true` si une relecture suit (l'écriture est postérieure à cette lecture) : rien n'est alors rendu.
    function settle() {
      delete ctx.reads[eqId];
      if (slot.again && isCurrent(eqId)) {
        loadEquipment(eqId);
        return true;
      }
      return false;
    }
    $.ajax({
      type: 'POST',
      url: AJAX_URL,
      data: { action: 'getMappingOverrides', eqId: eqId },
      dataType: 'json',
      success: function (data) {
        if (settle() || !isCurrent(eqId)) {
          return;
        }
        var $panel = ctx.current.$panel;
        var $status = $panel.find('.j2ha-eq-status').first();
        var result = data && data.result ? data.result : data;
        var payload = result && result.payload ? result.payload : result;
        var failed = (data && data.state && data.state !== 'ok')
          || !M.equipmentActionState(payload).readable
          || Number(M.normalizeTree(payload).jeedom_eq_id) !== Number(eqId);
        if (failed) {
          markTreeError($panel, eqId, '{{Impossible de lire la configuration de cet équipement.}}');
          return;
        }
        $status.text('');
        renderEquipmentTree($panel, payload);
      },
      error: function () {
        if (settle() || !isCurrent(eqId)) {
          return;
        }
        markTreeError(ctx.current.$panel, eqId, '{{Impossible de charger la configuration HA (démon indisponible).}}');
      },
    });
  }

  // Story 25.3 (AC6, Q7) : une écriture terminée peut avoir changé les chiffres de la page derrière la vue ;
  // la relecture (sans refresh, coalescée) est portée par la page principale, ici on la signale seulement.
  function notifyOverview() {
    if (typeof notifyStatesChanged === 'function') {
      notifyStatesChanged();
    }
  }

  function reloadEquipment(eqId) {
    notifyOverview();
    if (isCurrent(eqId)) {
      loadEquipment(eqId, true);
    }
  }

  // --- Détail d'un équipement (Story 25.4) : le panneau remplace l'ancien accordéon de la fenêtre de pièce ---

  // En-tête collant (titre, badge d'état, mention des bloquées, contrôles) puis corps : état de chargement,
  // compteurs, encart de cause, tableau des commandes. Mêmes classes qu'en 25.1 (tests, gate, scrollToCommand),
  // sans accordéon : `.j2ha-eq-toggle` et `.panel-collapse` n'existent plus.
  function buildEquipmentPanel(eq) {
    var $panel = $('<div class="j2ha-eq-panel j2ha-eq-open"></div>').attr('data-eq-id', eq.eq_id);
    if (!eq.enabled) {
      $panel.addClass('j2ha-eq-disabled');
    }
    var $head = $('<div class="j2ha-eq-head"></div>');
    var $title = $('<h3 class="j2ha-eq-title j2ha-wv-title" tabindex="-1"></h3>');
    $title.append($('<span class="j2ha-eq-name j2ha-free-name"></span>').text(eq.eq_name || ('#' + eq.eq_id)));
    if (!eq.enabled) {
      // Front v3 (Lot 2) : « désactivé dans Jeedom » devient une icône, le mot passe en info-bulle et en nom accessible.
      $title.append(infoTip($('<span class="j2ha-eq-off" role="img"></span>').attr('title', '{{désactivé dans Jeedom}}')
        .attr('aria-label', '{{désactivé dans Jeedom}}').append($('<i class="fas fa-power-off" aria-hidden="true"></i>'))));
    }
    // Un seul badge d'état (front v2) : il est aussi « l'état de l'en-tête » (`j2ha-eq-head-state`). Front v3 (Lot 2) : le mot
    // « désactivé dans Jeedom » et le décompte des bloquées ne sont plus des textes de l'en-tête (le badge dit l'état).
    $title.append($('<span class="j2ha-eq-publish-badge j2ha-badge j2ha-eq-head-state"></span>'));
    $title.append($('<span class="j2ha-eq-blocked-mention"></span>'));
    $title.append($('<span class="j2ha-v2 j2ha-v2-mentions j2ha-eq-mentions"></span>'));
    // Front v3 (Lot 2) : en-tête sur deux lignes. Ligne 1 : nom, badge, Auto / Toujours / Jamais, ⋯ à droite. Ligne 2 :
    // plugin · n commandes · ↗ Jeedom · Home Assistant (rempli à la lecture de l'arbre).
    $head.append($('<div class="j2ha-eq-line1"></div>').append($title).append($('<div class="j2ha-eq-controls"></div>')));
    $head.append($('<div class="j2ha-eq-meta"></div>').append($('<span class="j2ha-eq-meta-facts"></span>'))
      .append($('<span class="j2ha-eq-counters text-muted" role="status"></span>')).append($('<span class="j2ha-eq-meta-links"></span>')));
    var $body = $('<div class="j2ha-eq-body"></div>');
    $body.append($('<div class="j2ha-eq-status text-muted"></div>'));
    $body.append($('<div class="j2ha-eq-retry"></div>'));
    $body.append($('<div class="j2ha-eq-exclusion"></div>'));
    // Ordre front v3 : bande de cause (une ligne), conseil, « Dans Home Assistant » (une ligne par entité), puis le tableau.
    $body.append($('<div class="j2ha-eq-notices"></div>'));
    $body.append($('<div class="j2ha-eq-advice"></div>'));
    $body.append($('<div class="j2ha-eq-sides"></div>'));
    $body.append($('<div class="j2ha-eq-cmdlist"></div>'));
    $body.append($('<div class="j2ha-eq-tech"></div>'));
    $panel.append($head).append($body);
    return $panel;
  }

  function clearEquipment() {
    closeMenu();
    // Front v2 (Lot 5) : panneau « Corriger le type » fermé (minuteur et aperçu en vol annulés), bandeau retiré.
    closeTypePanel(false);
    clearTypeToast();
    Object.keys(ctx.timers).forEach(function (cmdId) {
      if (ctx.timers[cmdId]) clearTimeout(ctx.timers[cmdId]);
    });
    Object.keys(ctx.xhr).forEach(function (cmdId) {
      if (ctx.xhr[cmdId] && typeof ctx.xhr[cmdId].abort === 'function') ctx.xhr[cmdId].abort();
    });
    ctx.timers = {};
    ctx.xhr = {};
    ctx.trees = {};
    ctx.raw = {};
    ctx.treeErrors = {};
    ctx.current = null;
  }

  // Affiche le détail de l'équipement `eq` ({ eq_id, eq_name, enabled }) de la pièce `room` dans `$host` et lit son
  // arbre unitaire (une lecture, D3). Rend le panneau.
  function openEquipment($host, room, eq) {
    clearEquipment();
    ctx.room = room;
    var $panel = buildEquipmentPanel(eq);
    ctx.current = { eqId: eq.eq_id, $panel: $panel };
    $host.empty().append($panel);
    loadEquipment(eq.eq_id);
    return $panel;
  }

  // Les états suivent la relecture de la page B (jamais un recalcul local) : badge, mention et compteurs de l'équipement
  // affiché sont relus dans l'entrée agrégée (mêmes fonctions que l'arbre unitaire, parité prouvée en 25.2).
  function refreshEquipmentState(entry) {
    if (!ctx.current || !entry || entry.jeedom_eq_id !== ctx.current.eqId || !ctx.trees[ctx.current.eqId]) {
      return;
    }
    var resolved = renderSummary(ctx.current.$panel, entry);
    renderExclusion(ctx.current.$panel, entry);
    renderEquipmentCounters(ctx.current.$panel, entry);
    renderSides(ctx.current.$panel, ctx.current.eqId, resolved.state);
    renderAdvice(ctx.current.$panel, ctx.current.eqId, resolved.state);
  }

  // Réassurance Homebridge : réinitialisée à l'entrée dans la vue.
  function resetSession() {
    ctx.reassurance = M.initReassuranceState();
    $('#j2haSurface_reassurance').hide();
  }

  window.Jeedom2haSurface = {
    openEquipment: openEquipment,
    clearEquipment: clearEquipment,
    refreshEquipmentState: refreshEquipmentState,
    refreshRoomGating: refreshRoomGating,
    buildRoomActions: buildRoomActions,
    buildRoomExcludedNotice: buildRoomExcludedNotice,
    applyEquipment: applyEquipment,
    stateWord: stateWord,
    resetSession: resetSession,
    setRoom: function (room) { ctx.room = room; },
    setHost: function (next) { host = next; },
    genericTypesUrl: GENERIC_TYPES_URL,
    // Front v2 (Lot 5) : point d'entrée du panneau « Corriger le type », appelé par `Jeedom2haTypePanel.open`.
    openTypePanel: openTypePanel,
  };
})();
