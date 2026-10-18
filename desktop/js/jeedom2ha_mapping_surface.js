/* Story 16.8 / 25.1 — Surface de mapping HA par pièce (modèle Homebridge).
 *
 * Navigation : page plugin -> cartes pièces -> modale par pièce -> accordéon
 * équipements (un seul déplié) -> état unique, réglage de publication et tableau
 * des commandes regroupé par entité.
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

  // État volatil de la surface courante (une modale pièce ouverte à la fois).
  var ctx = { reassurance: M.initReassuranceState(), timers: {}, xhr: {}, trees: {}, treeErrors: {}, room: null };

  function normalizedRooms() {
    return M.normalizeRoomsTree(window.j2haRoomsTree || []);
  }

  function findRoom(objectId) {
    var rooms = normalizedRooms();
    for (var i = 0; i < rooms.length; i++) {
      if (rooms[i].object_id === objectId) {
        return rooms[i];
      }
    }
    return null;
  }

  // --- Tableau des commandes (16.8, 25.1) : colonnes
  //     Commande | Dans Home Assistant | Type Jeedom | Type HA, regroupées par entité.
  //     Les commandes ignorées ne sont pas des lignes : elles sont repliées sous le tableau. ---

  // `row` : la ligne de commande (types proposés filtrés par le démon, AC6) ; sans lui, liste complète.
  function buildOptions(selected, row) {
    var opts = row ? M.getOverrideTypeOptions(row) : M.getHaEntityTypeOptions();
    var $sel = $('<select class="form-control input-sm mapping-override-select"></select>');
    $sel.attr('aria-label', '{{Type HA}}');
    $sel.append($('<option value="">{{auto}}</option>'));
    for (var i = 0; i < opts.length; i++) {
      var $o = $('<option></option>').attr('value', opts[i]).text(opts[i]);
      if (opts[i] === selected) {
        $o.prop('selected', true);
      }
      $sel.append($o);
    }
    return $sel;
  }

  // Q5 (décision 2026-10-18) : écran « Types d'équipement » du core Jeedom, ouvert sans rien écrire (D10).
  var GENERIC_TYPES_URL = 'index.php?v=d&p=types';
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

  // Aperçu d'un type imposé (dry-run, 16.8) : « À appliquer → Capteur (sensor) », « Bloquée → cause »,
  // ou « Ignorée → … » ; jamais une cellule vide.
  // AC12 « jamais vide » : commande non couverte par un mapping → état factuel dédié.
  // Story 19.3 (P1, relecture ClaudeBox PR #176 tour 2) : `covered:false` ne signifie PAS
  // systématiquement « aucun mapping ne couvre cette commande » — une exclusion/inéligibilité
  // amont (I1/I4) porte aussi `covered:false` avec un VRAI diagnostic à afficher. Le libellé
  // générique ne sort que si `shouldShowUncoveredLabel` confirme l'absence de cause réelle.
  function renderPreviewCell($cell, view, covered) {
    if (covered === false && M.shouldShowUncoveredLabel(view)) {
      iconTextCell($cell, 'j2ha-diag-uncovered', 'fa-ban', M.buildUncoveredLabel());
      return;
    }
    if (M.isExcludedDiagnostic(view)) {
      iconTextCell($cell, 'j2ha-diag-excluded', 'fa-eye-slash', M.buildExcludedLabel(view));
      return;
    }
    if (M.isDisabledDiagnostic(view)) {
      iconTextCell($cell, 'j2ha-diag-disabled', 'fa-pause-circle', M.buildDisabledLabel(view));
      return;
    }
    var state = M.diagnosticState(view);
    var msg = M.buildPublishCellLabel(view);
    if (state === 'ready') {
      iconTextCell($cell, 'j2ha-diag-todo', 'fa-clock', msg);
    } else if (state === 'blocking') {
      iconTextCell($cell, 'j2ha-diag-blocking', 'fa-exclamation-triangle', msg);
    } else {
      iconTextCell($cell, 'j2ha-diag-unknown', null, msg);
    }
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

  // Colonne « Type HA » : lien discret « auto » / « imposé (sensor) ». Le sélecteur n'existe qu'après
  // un clic sur le lien (jamais rendu en permanence, jamais proposé quand le réglage est indisponible).
  function renderTypeCell(eqId, row, entities, $haCell) {
    var cmdId = row.jeedom_cmd_id;
    var $td = $('<td class="mo-td-override"></td>');
    var selectorState = M.getOverrideSelectorState(row, entities);
    var forced = row.override_applied;
    var linkText = forced ? '{{imposé}} (' + (row.effective_ha || '') + ')' : '{{auto}}';
    var $revertError = $('<span class="mo-revert-error text-danger"></span>').hide();

    if (!selectorState.active) {
      $td.append($('<span class="j2ha-type-link j2ha-type-unavailable" aria-disabled="true"></span>')
        .attr('title', selectorState.reason).text(linkText));
    } else {
      var $link = $('<a class="j2ha-type-link cursor" role="button" tabindex="0"></a>')
        .attr('title', '{{Choisir le type HA de cette commande}}').text(linkText);
      if (forced) {
        $link.addClass('j2ha-type-forced');
      }
      var $spinner = $('<span class="mo-spinner"><i class="fas fa-spinner fa-spin"></i></span>').hide();
      var opened = false;
      var openSelector = function () {
        if (opened) {
          return;
        }
        opened = true;
        var $select = buildOptions(forced ? row.effective_ha : '', row);
        $link.hide();
        $td.append($select);
        $select.on('change', function () {
          var type = $(this).val();
          if (ctx.timers[cmdId]) {
            clearTimeout(ctx.timers[cmdId]);
          }
          if (!type) {
            revertCommand(eqId, cmdId);
            return;
          }
          ctx.timers[cmdId] = setTimeout(function () {
            runDryRun(eqId, cmdId, type, $haCell, $spinner);
          }, DEBOUNCE_MS);
        });
        $select.on('keydown', function (event) {
          if (event && event.key === 'Escape') {
            $select.remove();
            $link.show();
            opened = false;
          }
        });
        $select.focus();
      };
      $link.on('click', function (event) {
        if (event && event.preventDefault) event.preventDefault();
        openSelector();
      });
      $link.on('keydown', function (event) {
        if (event && (event.key === 'Enter' || event.key === ' ')) {
          if (event.preventDefault) event.preventDefault();
          openSelector();
        }
      });
      $td.append($link).append($spinner);
    }
    if (forced) {
      // Story 20-2 (P1, relecture indépendante PR #210) : ce lien ne porte que sur le type de cette seule
      // commande (route TYPE, 16-8) — jamais sur les réglages de publication de toute l'entité.
      // Reprise X5d (P3) : en cas d'échec, on réaffiche une cause lisible dans `$revertError` et on
      // réattache le gestionnaire pour permettre un nouvel essai.
      var $revertLink = $('<a class="mo-revert-cmd cursor" role="button" tabindex="0"></a>')
        .attr('title', '{{Retirer le type imposé}}').attr('aria-label', '{{Retirer le type imposé}}')
        .append('<i class="fas fa-undo"></i>');
      $td.append($revertLink).append($revertError);
      var attachRevertHandler = function () {
        $revertLink.one('click', function () {
          clearRequestError($revertError);
          $revertLink.prop('disabled', true);
          revertCommand(eqId, cmdId, $revertLink, $revertError, attachRevertHandler);
        });
      };
      attachRevertHandler();
    }
    return $td;
  }

  function renderCommandRow(eqId, row, entities) {
    var cmdId = row.jeedom_cmd_id;
    var category = M.classifyCommandCategory(row);
    var $tr = $('<tr class="mapping-override-cmd"></tr>').attr('data-cmd-id', cmdId).addClass('j2ha-cat-' + category);

    $tr.append($('<td class="mo-td-name"></td>').text(row.cmd_name || ('#' + cmdId)));

    var $haCell = $('<td class="mo-td-diag mo-diag-cell"></td>');
    renderHaCell($haCell, row, category, entities);
    $tr.append($haCell);

    // generic_type natif Jeedom, lecture seule (D10, jamais écrit).
    $tr.append($('<td class="mo-td-generic"></td>')
      .append($('<span class="mo-native-value" aria-readonly="true"></span>').text(row.generic_type || '—')));

    $tr.append(renderTypeCell(eqId, row, entities, $haCell));
    return $tr;
  }

  function runDryRun(eqId, cmdId, type, $diagCell, $spinner) {
    if (ctx.xhr[cmdId]) {
      ctx.xhr[cmdId].abort();
    }
    $spinner.show();
    ctx.xhr[cmdId] = $.ajax({
      type: 'POST',
      url: AJAX_URL,
      data: { action: 'previewMappingOverride', eqId: eqId, cmdId: cmdId, haEntityType: type },
      dataType: 'json',
      success: function (data) {
        var result = data && data.result ? data.result : data;
        var covered = M.readPreviewCovered(result);
        // Commande non couverte : aucun mapping à projeter. On affiche l'état factuel et on
        // NE persiste PAS (un override sur une commande non couverte est un no-op qui, après
        // reload, laisse la cellule vide — la cause exacte du #871).
        // Story 19.3 (P1) : on transmet la vue `auto` (raison réelle éventuelle — exclusion,
        // inéligibilité amont) plutôt que `null`, pour que `renderPreviewCell` puisse
        // distinguer « vraiment non couverte » d'une cause amont à afficher (I4).
        if (!covered) {
          renderPreviewCell($diagCell, M.readPreviewAuto(result), false);
          return;
        }
        var view = M.readPreviewOverridden(result);
        renderPreviewCell($diagCell, view, true);
        maybeShowReassurance(M.isBlockingDiagnostic(view) && !M.isExcludedDiagnostic(view));
        if (M.shouldAutoValidate(view)) {
          saveOverride(eqId, cmdId, type);
        }
      },
      complete: function () {
        $spinner.hide();
        ctx.xhr[cmdId] = null;
      },
    });
  }

  function saveOverride(eqId, cmdId, type) {
    $.ajax({
      type: 'POST',
      url: AJAX_URL,
      data: { action: 'saveMappingOverride', eqId: eqId, cmdId: cmdId, haEntityType: type },
      dataType: 'json',
      success: function () {
        reloadEquipment(eqId);
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
      ? '{{Projection valide pour ce type.}}' : '{{Projection invalide pour ce type.}}'));
    $wrap.append($('<p></p>').text(state.command_names.length
      ? '{{Commandes qui recevront les ordres : }}' + state.command_names.join(', ')
      : '{{Aucune commande ne recevra d’ordre.}}'));
    if (state.can_confirm) {
      $wrap.append($('<p></p>').text('{{Cette entité sera publiée dans Home Assistant.}}'));
    } else {
      $wrap.append($('<p class="text-danger"></p>')
        .text('{{Le forçage serait refusé : }}' + (state.refusal_reason || '')));
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
    $wrap.append($('<p></p>').text('{{Entités concernées par ce forçage : }}'));
    var $ul = $('<ul></ul>');
    state.items.forEach(function (item) {
      $ul.append($('<li></li>').text(
        (item.ha_entity_type || '{{Entité HA}}') + ' — ' + item.status_label
        + ' (' + (item.command_names.length ? item.command_names.join(', ') : '{{aucune commande}}') + ')'
      ));
    });
    $wrap.append($ul);
    if (state.can_confirm) {
      $wrap.append($('<p></p>').text('{{Au moins une entité sera publiée dans Home Assistant.}}'));
    } else {
      $wrap.append($('<p class="text-danger"></p>').text('{{Le forçage serait refusé : }}' + (state.refusal_reason || '')));
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
        var dialogOptions = state.can_confirm ? null
          : { disableConfirm: state.refusal_reason || '{{Le forçage serait refusé dans l’état actuel.}}' };
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

  // --- Story 20.3 (Q1=A) — compteurs de la pièce ouverte ---
  // Lus uniquement dans les arbres déjà chargés pour cette pièce (aucune autre lecture) ;
  // le dénombrement vit dans le module pur (M.summarizeRoom), jamais de décision recalculée.

  function roomEquipmentCount() {
    return ctx.room ? ctx.room.equipments.length : 0;
  }

  function readRoomTrees() {
    var trees = [];
    var errors = 0;
    if (!ctx.room) {
      return { trees: trees, errors: errors };
    }
    for (var i = 0; i < ctx.room.equipments.length; i++) {
      var eqId = ctx.room.equipments[i].eq_id;
      if (ctx.trees[eqId]) {
        trees.push(ctx.trees[eqId]);
      } else if (ctx.treeErrors[eqId]) {
        errors += 1;
      }
    }
    return { trees: trees, errors: errors };
  }

  function renderRoomCounters() {
    var $host = $('.modal-j2ha-room .j2ha-room-counters').first();
    if ($host.length === 0 || !ctx.room) {
      return;
    }
    var read = readRoomTrees();
    var trees = read.trees;
    $host.empty();
    if (trees.length === 0) {
      // R1-E : si plus aucune lecture ne peut aboutir, un message d'erreur remplace le chargement.
      if (read.errors >= roomEquipmentCount() && read.errors > 0) {
        $host.text('{{Compteurs indisponibles : la configuration des équipements de cette pièce n’a pas pu être lue.}}');
      } else {
        $host.text('{{Chargement des compteurs…}}');
      }
      return;
    }
    var labels = M.buildRoomCounterLabels(M.summarizeRoom(trees, ctx.room.equipments.length));
    var $line = $('<div class="j2ha-room-counter-line"></div>');
    labels.items.forEach(function (item) {
      $line.append($('<span class="j2ha-chip j2ha-room-counter"></span>')
        .addClass('j2ha-chip-' + item.state).attr('data-state', item.state)
        .append($('<i class="fas"></i>').addClass(STATE_ICONS[item.state]))
        .append(document.createTextNode(' ' + item.text)));
    });
    [labels.unread, labels.presence_unknown].forEach(function (text) {
      if (text) {
        $line.append($('<span class="text-muted j2ha-room-counter-unread"></span>').text(text));
      }
    });
    $host.append($line);
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
  function renderEquipmentCounters($panel, tree) {
    var $host = $panel.find('.j2ha-eq-counters').first().empty();
    if (!tree) {
      return;
    }
    var resolved = M.resolveEquipmentState(tree);
    var labels = M.buildEquipmentCounterLabels(tree);
    var $line = $('<div class="j2ha-eq-counter-line"></div>');
    $line.append(stateWord(resolved.state).addClass('j2ha-eq-head-state'));
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

  function updateRoomActionsGating() {
    var $republish = $('.modal-j2ha-room .j2ha-room-republish').first();
    var $recreate = $('.modal-j2ha-room .j2ha-room-recreate').first();
    if (!ctx.room || ($republish.length === 0 && $recreate.length === 0)) {
      return;
    }
    var read = readRoomTrees();
    var state = M.roomActionState(read.trees, roomEquipmentCount(), read.trees.length + read.errors);
    if ($republish.length > 0) setStateGate($republish, state.can_republish, state.republish_reason);
    if ($recreate.length > 0) setStateGate($recreate, state.can_recreate, state.recreate_reason);
    reapplyBridgeGating();
  }

  function refreshRoomView() {
    renderRoomCounters();
    updateRoomActionsGating();
  }

  function isRoomOpen(room) {
    return !!room && !!ctx.room && ctx.room.object_id === room.object_id
      && $('.modal-j2ha-room .j2ha-room-surface').length > 0;
  }

  function showRoomFeedback(message, level) {
    var $slot = $('.modal-j2ha-room .j2ha-room-feedback').first();
    if ($slot.length === 0) {
      return;
    }
    $slot.empty().append($('<div class="alert" role="status"></div>')
      .addClass('alert-' + level).text(message)).show();
  }

  // R1-D : le résultat d'une action est rendu dans la modale seulement si cette pièce y est
  // toujours ouverte ; sinon (modale fermée, autre pièce ouverte), dans la zone d'alerte de la page.
  function showActionFeedback(room, message, level) {
    if (isRoomOpen(room)) {
      showRoomFeedback(message, level);
      return;
    }
    // `showAlert` rend du HTML (jeeDialog.toast) et le message cite des noms libres : échappé (R2-2).
    $('#div_alert').showAlert({ message: escapeHtml(message), level: level });
  }

  function reloadRoom(room) {
    if (!isRoomOpen(room)) {
      return;
    }
    room.equipments.forEach(function (eq) { reloadEquipment(eq.eq_id); });
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
      },
      onError: function (message) {
        showActionFeedback(room, message, 'danger');
        // Story 22.2 (Q8 A, P3 de 20-3) : une action de pièce en échec rafraîchit aussi le bandeau.
        refreshBridgeStatus();
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
      var $button = $('<button type="button" class="j2ha-menu-item" role="menuitem"></button>')
        .addClass(entry.className || '').attr('data-ha-action', entry.haAction)
        .append($('<i class="fas"></i>').addClass(entry.icon))
        .append(document.createTextNode(entry.label));
      $button.on('click', function (event) {
        if (event && event.stopPropagation) event.stopPropagation();
        closeMenu();
        entry.onClick($button);
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
  var DELETE_WARNING = '<br><br><strong>{{Attention}}</strong> : {{l\'historique, les dashboards, les automatisations et l\'entity_id liés à ces entités peuvent être impactés.}}'
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
    var menu = buildMenu('{{Autres actions}}', [
      {
        key: 'republish', className: 'j2ha-room-republish', icon: 'fa-upload', label: '{{Republier}}', haAction: 'republier',
        onClick: function ($republish) {
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
    // et qu'aucun équipement ne justifie l'action (voir updateRoomActionsGating).
    $wrap.append(menu.$wrap);
    return $wrap;
  }

  // --- État unique de l'équipement (25.1) : badge, encarts de cause, ligne des ignorées ---

  var ALL_STATE_CLASSES = M.EQUIPMENT_STATES.map(function (state) { return 'j2ha-state-' + state; }).join(' ');

  // Le même mot que les compteurs de la pièce et que la ligne de l'équipement déplié :
  // tous lisent `M.resolveEquipmentState` (aucune règle d'état n'est écrite ici).
  function renderSummary($panel, tree) {
    var resolved = M.resolveEquipmentState(tree);
    $panel.removeClass(ALL_STATE_CLASSES).addClass('j2ha-state-' + resolved.state);

    var $badge = $panel.find('.j2ha-eq-publish-badge').first();
    $badge.removeClass(ALL_STATE_CLASSES).addClass('j2ha-state-' + resolved.state);
    $badge.empty()
      .append($('<i class="fas"></i>').addClass(STATE_ICONS[resolved.state]))
      .append($('<span class="j2ha-state-text"></span>').text(' ' + M.EQUIPMENT_STATE_LABELS[resolved.state]));

    var $mention = $panel.find('.j2ha-eq-blocked-mention').first().empty();
    if (resolved.blocked_mention > 0) {
      $mention.append($('<i class="fas fa-exclamation-triangle"></i>'))
        .append($('<span></span>').text(' ' + resolved.blocked_mention + ' '
          + (resolved.blocked_mention > 1 ? 'bloquées' : 'bloquée')));
    }
    return resolved;
  }

  function scrollToCommand($panel, cmdId) {
    var $target = $panel.find('tr.mapping-override-cmd[data-cmd-id="' + cmdId + '"]');
    if ($target.length > 0) {
      var $scroll = $target.closest('.j2ha-eq-cmdlist');
      if ($scroll.length > 0) {
        var top = $target.position() ? $target.position().top : 0;
        $scroll.scrollTop($scroll.scrollTop() + top - 10);
      }
      $target.addClass('j2ha-diag-target-highlight');
      setTimeout(function () { $target.removeClass('j2ha-diag-target-highlight'); }, 2000);
    }
  }

  // AC14 : la cause d'un blocage est dite UNE fois par cause distincte, avec le nombre de commandes
  // concernées et, quand le blocage se corrige dans Jeedom, le lien vers l'écran des types génériques
  // (ouverture seule : le type natif n'est jamais écrit, D10). L'ancre vers la première commande
  // bloquée n'a de sens que si toutes les commandes ne le sont pas.
  function renderNotices($panel, tree) {
    var $host = $panel.find('.j2ha-eq-notices').first().empty();
    var groups = M.groupBlockedCauses(tree);
    var summary = M.summarizePublication(tree);
    groups.forEach(function (group, index) {
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
      if (index === 0 && summary.first_blocking_cmd_id !== null && !M.allCommandsBlocked(tree)) {
        var $anchor = $('<a class="cursor j2ha-goto-blocking" role="button" tabindex="0"></a>')
          .append('<i class="fas fa-arrow-down"></i>')
          .append(document.createTextNode('{{Voir la première commande bloquée}}'));
        $anchor.on('click', function () { scrollToCommand($panel, summary.first_blocking_cmd_id); });
        $notice.append($anchor);
      }
      $host.append($notice);
    });
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

  var SEGMENTS = [
    { key: 'auto', label: '{{Automatique}}' },
    { key: 'always', label: '{{Toujours}}' },
    { key: 'never', label: '{{Jamais}}' },
  ];

  function activeSegmentOf(policy) {
    if (policy === 'exclude_eqlogic' || policy === 'exclude_command') return 'never';
    if (policy === 'force_publish') return 'always';
    return 'auto';
  }

  // `state` : M.publicationActionState ; les segments non actifs indisponibles portent leur cause.
  function buildSegmented(ariaLabel, active, state, onSelect, compact) {
    var $group = $('<div class="j2ha-seg" role="radiogroup"></div>').attr('aria-label', ariaLabel);
    if (compact) {
      $group.addClass('j2ha-seg-compact');
    }
    var availability = {
      auto: { allowed: state.can_revert, reason: state.revert_reason },
      always: { allowed: state.can_force, reason: state.force_reason },
      never: { allowed: state.can_exclude, reason: state.exclude_reason },
    };
    var buttons = [];
    SEGMENTS.forEach(function (segment) {
      var isActive = segment.key === active;
      var $button = $('<button type="button" class="j2ha-seg-btn" role="radio"></button>')
        .addClass('j2ha-seg-' + segment.key).attr('data-value', segment.key)
        .attr('aria-checked', isActive ? 'true' : 'false').attr('tabindex', isActive ? '0' : '-1')
        .text(segment.label);
      if (isActive) {
        $button.addClass('j2ha-seg-active');
      }
      // Le segment actif reste actif ; « Automatique » actif reste utilisable s'il y a des types HA
      // imposés à retirer (même route : retour au mode automatique de tout l'équipement).
      var usable = isActive ? (segment.key === 'auto' && availability.auto.allowed) : availability[segment.key].allowed;
      if (!isActive && !usable) {
        $button.prop('disabled', true).addClass('j2ha-seg-disabled').attr('aria-disabled', 'true')
          .attr('title', availability[segment.key].reason || '{{Cette action est sans effet dans l’état courant.}}');
      }
      if (isActive && usable) {
        $button.attr('title', '{{Retire aussi les types Home Assistant imposés sur les commandes.}}');
      }
      $button.on('click', function () {
        if ($button.prop('disabled') || (isActive && !usable)) {
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
    }, compact);
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
    $panel.find('.j2ha-eq-counters').first().empty();
    $panel.find('.j2ha-eq-blocked-mention').first().empty();
    $panel.find('.j2ha-eq-publish-badge').first().empty();
    $panel.find('.j2ha-eq-status').first().text(message);
    refreshRoomView();
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
      .append($('<th class="mo-th-generic"></th>').text('{{Type Jeedom}}'))
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

  // En-tête collant de l'équipement déplié : réglage de publication (contrôle segmenté), « Appliquer »
  // seulement quand un réglage attend, menu « ⋯ » (Republier, Supprimer de Home Assistant…).
  function renderControls($panel, eqId, normalized, resolved) {
    var $host = $panel.find('.j2ha-eq-controls').first().empty();
    // X6b (P2, relecture indépendante PR #215) : la cible équipement est construite par
    // `equipmentPublicationTarget` (lit `eligible` + `equipment_publication_override` de l'arbre, en
    // plus du veto porté par les entités/commandes).
    var $error = $('<div class="j2ha-publication-error text-danger"></div>').hide();
    var target = M.equipmentPublicationTarget(normalized);
    $host.append($('<span class="j2ha-control-label"></span>').text('{{Publication dans Home Assistant}}'));
    $host.append(buildPublicationControl(eqId, target, true, normalized.commands, normalized.entities, $error, false));
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
      { separator: true },
      {
        key: 'recreate', className: 'j2ha-eq-recreate j2ha-menu-danger', icon: 'fa-trash',
        label: '{{Supprimer de Home Assistant…}}', haAction: 'supprimer', onClick: equipmentDeleteHandler(eqId, eqName),
      },
    ]);
    // Un réglage en attente reste applicable (y compris une exclusion à appliquer) ; hors de ce cas,
    // un équipement désactivé ou exclu n'a rien à republier.
    setStateGate(menu.buttons.republish, resolved.state === 'to_apply' || actionState.can_republish, actionState.republish_reason);
    setStateGate(menu.buttons.recreate, actionState.can_recreate, actionState.recreate_reason);
    $host.append(menu.$wrap);
    $host.append($error);
    // Les boutons viennent d'être ajoutés après l'ouverture de la modale : ils suivent le même gating
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
    var $list = $panel.find('.j2ha-eq-cmdlist').first().empty();

    ctx.trees[eqId] = normalized;
    delete ctx.treeErrors[eqId];
    refreshRoomView();

    var resolved = renderSummary($panel, normalized);
    renderEquipmentCounters($panel, normalized);
    renderNotices($panel, normalized);
    renderControls($panel, eqId, normalized, resolved);

    if (!normalized.mapped && normalized.commands.length === 0) {
      $list.append($('<div class="text-muted j2ha-empty"></div>')
        .text('{{Aucune commande à configurer pour cet équipement.}}'));
      return;
    }

    renderCommandTable($list, eqId, normalized);
    renderIgnored($list, eqId, normalized);
  }

  function roomHasEquipment(eqId) {
    return !!ctx.room && ctx.room.equipments.some(function (eq) { return eq.eq_id === eqId; });
  }

  function loadEquipment($panel, eqId) {
    var $status = $panel.find('.j2ha-eq-status').first();
    $status.text('{{Chargement…}}');
    $.ajax({
      type: 'POST',
      url: AJAX_URL,
      data: { action: 'getMappingOverrides', eqId: eqId },
      dataType: 'json',
      success: function (data) {
        // Réponse tardive d'une pièce refermée : ignorée (elle ne doit pas toucher le cache d'une autre pièce).
        if (!roomHasEquipment(eqId)) {
          return;
        }
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
        if (!roomHasEquipment(eqId)) {
          return;
        }
        markTreeError($panel, eqId, '{{Impossible de charger la configuration HA (daemon indisponible).}}');
      },
    });
  }

  function reloadEquipment(eqId) {
    var $panel = $('.j2ha-eq-panel[data-eq-id="' + eqId + '"]');
    if ($panel.length > 0) {
      $panel.data('loaded', true);
      loadEquipment($panel, eqId);
    }
  }

  // --- Modale par pièce : accordéon des équipements (un seul déplié à la fois, 25.1 AC16) ---

  function setPanelOpen($panel, open) {
    $panel.toggleClass('j2ha-eq-open', open);
    $panel.find('.panel-collapse').first().toggleClass('in', open);
    $panel.find('.j2ha-eq-toggle').first().attr('aria-expanded', open ? 'true' : 'false');
  }

  // Déplier un équipement replie celui qui l'était : le défilement est celui de la fenêtre seule.
  function togglePanel($panel) {
    var open = $panel.hasClass('j2ha-eq-open');
    if (!open) {
      $panel.closest('.j2ha-eq-accordion').find('.j2ha-eq-panel').each(function (index, el) {
        if (el !== $panel.get(0)) {
          setPanelOpen($(el), false);
        }
      });
    }
    setPanelOpen($panel, !open);
    // Garde-fou : un panneau jamais chargé (ex. échec réseau initial) l'est à la première ouverture.
    if (!open && !$panel.data('loaded')) {
      $panel.data('loaded', true);
      loadEquipment($panel, parseInt($panel.attr('data-eq-id'), 10));
    }
  }

  function buildRoomModalHtml(room) {
    var $wrap = $('<div class="j2ha-room-surface"></div>');
    $wrap.append($('<div id="j2haSurface_reassurance" class="alert alert-warning" role="status" aria-live="polite">' +
      '<i class="fas fa-shield-alt"></i> {{Aucun impact Homebridge : cet écran ne modifie que la sortie Home Assistant de jeedom2ha.}}</div>').hide());

    var $head = $('<div class="j2ha-room-head"></div>');
    $head.append($('<div class="j2ha-room-counters text-muted" role="status" aria-live="polite"></div>'));
    $head.append(buildRoomActions(room));
    $wrap.append($head);
    $wrap.append($('<div class="j2ha-room-feedback" role="status"></div>').hide());

    var $accordion = $('<div class="panel-group j2ha-eq-accordion"></div>');
    for (var i = 0; i < room.equipments.length; i++) {
      var eq = room.equipments[i];
      var panelId = 'j2haEqBody_' + room.object_id + '_' + eq.eq_id;
      var headId = 'j2haEqHead_' + room.object_id + '_' + eq.eq_id;

      var $panel = $('<div class="panel panel-default j2ha-eq-panel"></div>')
        .attr('data-eq-id', eq.eq_id);
      if (!eq.enabled) {
        $panel.addClass('j2ha-eq-disabled');
      }

      var $head = $('<div class="panel-heading j2ha-eq-head"></div>').attr('id', headId);
      var $toggle = $('<a class="j2ha-eq-toggle" role="button"></a>')
        .attr('href', '#' + panelId)
        .attr('aria-expanded', 'false')
        .attr('aria-controls', panelId);
      $toggle.append($('<span class="j2ha-eq-name"></span>').text(eq.eq_name || ('#' + eq.eq_id)));
      if (!eq.enabled) {
        $toggle.append($('<span class="text-muted"></span>').text(' {{(désactivé dans Jeedom)}}'));
      }
      $toggle.append($('<span class="j2ha-eq-publish-badge j2ha-badge"></span>'));
      $toggle.append($('<span class="j2ha-eq-blocked-mention"></span>'));
      $toggle.on('click', (function ($p) {
        return function (event) {
          if (event && event.preventDefault) event.preventDefault();
          togglePanel($p);
        };
      }($panel)));
      $head.append($('<h4 class="panel-title"></h4>').append($toggle));
      $head.append($('<div class="j2ha-eq-controls"></div>'));
      $panel.append($head);

      var $collapse = $('<div class="panel-collapse collapse"></div>')
        .attr('id', panelId)
        .attr('aria-labelledby', headId);
      var $body = $('<div class="panel-body"></div>');
      $body.append($('<div class="j2ha-eq-status text-muted"></div>'));
      $body.append($('<div class="j2ha-eq-counters text-muted" role="status"></div>'));
      $body.append($('<div class="j2ha-eq-notices"></div>'));
      $body.append($('<div class="j2ha-eq-cmdlist"></div>'));
      $collapse.append($body);
      $panel.append($collapse);
      $accordion.append($panel);
    }
    $wrap.append($accordion);
    return $wrap;
  }

  function openRoom(objectId) {
    var room = findRoom(objectId);
    if (!room) {
      return;
    }
    // Réinitialise l'état réassurance par pièce (une fois par ouverture).
    ctx.reassurance = M.initReassuranceState();
    ctx.timers = {};
    ctx.xhr = {};
    ctx.trees = {};
    ctx.treeErrors = {};
    ctx.room = room;

    var $content = buildRoomModalHtml(room);

    bootbox.dialog({
      // « Sans pièce » est un libellé statique ; le nom d'une vraie pièce est un nom libre.
      title: '<i class="fas fa-home"></i> ' + (room.object_id > 0
        ? '<span class="j2ha-free-name">' + escapeHtml(room.object_name) + '</span>'
        : escapeHtml(room.object_name)),
      message: $content,
      size: 'large',
      className: 'modal-j2ha-room',
      onEscape: true,
      backdrop: true,
    });
    renderRoomCounters();
    // Les boutons d'action créés après le chargement de la page suivent le même gating que
    // les boutons globaux (pont indisponible, rescan en cours).
    if (typeof applyHAGating === 'function') {
      applyHAGating(window.jeedom2haLastBridgeStatus || null);
    }

    // Synthèse de publication immédiate (AC9) : on charge le diagnostic de chaque
    // équipement de la pièce dès l'ouverture pour que son état (badge et compteurs
    // de la pièce) soit visible sans déplier l'accordéon. La lazyness reste au
    // niveau page/pièce (AC5) : jamais les 290 équipements, seulement ceux de la
    // pièce ouverte (une poignée), et le fetch n'a lieu qu'après ouverture.
    $content.find('.j2ha-eq-panel').each(function () {
      var $panel = $(this);
      $panel.data('loaded', true);
      loadEquipment($panel, parseInt($panel.attr('data-eq-id'), 10));
    });
  }

  // Point d'entrée appelé par l'onclick inline des cartes pièce (pattern Homebridge éprouvé :
  // objectDisplayCard + onclick, jamais eqLogicDisplayCard que le core Jeedom hijacke sur la page plugin).
  window.j2haOpenRoom = function (objectId) {
    var id = parseInt(objectId, 10);
    if (!isNaN(id)) {
      openRoom(id);
    }
  };
})();
