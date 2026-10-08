/* Story 16.8 — Surface de mapping HA par pièce (modèle Homebridge).
 *
 * Navigation : page plugin -> cartes pièces -> modale par pièce -> accordéon
 * équipements -> triptyque + diagnostic par commande + synthèse « sera publié ».
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
  var ctx = { reassurance: M.initReassuranceState(), timers: {}, xhr: {}, trees: {}, room: null };

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

  // --- Tableau des commandes (16.8) : une ligne par commande, colonnes
  //     Commande | generic_type | Override HA | Diagnostic. Plus d'accordéon par
  //     commande : toute l'info utile est directement sur la ligne. ---

  function buildOptions(selected) {
    var opts = M.getHaEntityTypeOptions();
    var $sel = $('<select class="form-control input-sm mapping-override-select"></select>');
    $sel.append($('<option value="">{{— mode automatique —}}</option>'));
    for (var i = 0; i < opts.length; i++) {
      var $o = $('<option></option>').attr('value', opts[i]).text(opts[i]);
      if (opts[i] === selected) {
        $o.prop('selected', true);
      }
      $sel.append($o);
    }
    return $sel;
  }

  function renderDiagnosticCell($cell, view, covered) {
    $cell.removeClass('j2ha-diag-ready j2ha-diag-blocking j2ha-diag-unknown j2ha-diag-uncovered j2ha-diag-excluded j2ha-diag-disabled');
    // AC12 « jamais vide » : commande non couverte par un mapping → état factuel dédié,
    // jamais un flash vert trompeur ni une cellule vide (cf. #871 température sur DAAF).
    // Story 19.3 (P1, relecture ClaudeBox PR #176 tour 2) : `covered:false` ne signifie PAS
    // systématiquement « aucun mapping ne couvre cette commande » — une exclusion/inéligibilité
    // amont (I1/I4) porte aussi `covered:false` avec un VRAI diagnostic à afficher. Le libellé
    // générique ne sort que si `shouldShowUncoveredLabel` confirme l'absence de cause réelle.
    if (covered === false && M.shouldShowUncoveredLabel(view)) {
      $cell.addClass('j2ha-diag-uncovered').html('<i class="fas fa-ban"></i> ');
      $cell.append($('<span></span>').text(M.buildUncoveredLabel()));
      return;
    }
    if (M.isExcludedDiagnostic(view)) {
      $cell.addClass('j2ha-diag-excluded').html('<i class="fas fa-eye-slash"></i> ');
      $cell.append($('<span></span>').text(M.buildExcludedLabel(view)));
      return;
    }
    if (M.isDisabledDiagnostic(view)) {
      $cell.addClass('j2ha-diag-disabled').html('<i class="fas fa-pause-circle"></i> ');
      $cell.append($('<span></span>').text(M.buildDisabledLabel(view)));
      return;
    }
    var state = M.diagnosticState(view);
    var msg = M.buildPublishCellLabel(view);
    if (state === 'ready') {
      $cell.addClass('j2ha-diag-ready').html('<i class="fas fa-check-circle"></i> ');
    } else if (state === 'blocking') {
      $cell.addClass('j2ha-diag-blocking').html('<i class="fas fa-exclamation-triangle"></i> ');
    } else {
      $cell.addClass('j2ha-diag-unknown').empty();
    }
    $cell.append($('<span></span>').text(msg));
  }

  function maybeShowReassurance(isBlocking) {
    if (M.shouldShowReassurance(ctx.reassurance, isBlocking)) {
      ctx.reassurance = M.markReassuranceShown(ctx.reassurance);
      $('#j2haSurface_reassurance').show();
    }
  }

  function renderCommandRow(eqId, row) {
    var cmdId = row.jeedom_cmd_id;
    var $tr = $('<tr class="mapping-override-cmd"></tr>').attr('data-cmd-id', cmdId);

    // Colonne 1 : nom de commande.
    $tr.append($('<td class="mo-td-name"></td>').text(row.cmd_name || ('#' + cmdId)));

    // Colonne 2 : generic_type natif Jeedom, lecture seule (D10, jamais écrit).
    $tr.append($('<td class="mo-td-generic"></td>')
      .append($('<span class="mo-native-value" aria-readonly="true"></span>').text(row.generic_type || '—')));

    // Colonne 3 : override HA — menu déroulant inline + spinner + retour auto.
    var $tdOverride = $('<td class="mo-td-override"></td>');
    var $select = buildOptions(row.override_applied ? row.effective_ha : '');
    var selectorState = M.getOverrideSelectorState(row);
    if (!selectorState.active) {
      $select.prop('disabled', true).attr('title', selectorState.reason);
      $tdOverride.attr('title', selectorState.reason);
    }
    $tdOverride.append($select);
    var $spinner = $('<span class="mo-spinner" style="display:none;"><i class="fas fa-spinner fa-spin"></i></span>');
    $tdOverride.append($spinner);
    var $revertError = $('<span class="mo-revert-error text-danger" style="display:none;margin-left:6px;"></span>');
    if (row.override_applied) {
      $tdOverride.append($('<a class="mo-revert-cmd cursor" title="{{Revenir au type automatique}}"><i class="fas fa-undo"></i></a>'));
      $tdOverride.append($revertError);
    }
    $tr.append($tdOverride);

    // Colonne 4 : diagnostic — « ce qui sera publié » / « ne sera pas publié + raison ».
    var $diagCell = $('<td class="mo-td-diag mo-diag-cell"></td>');
    renderDiagnosticCell($diagCell, row.diagnostic, row.covered);
    $tr.append($diagCell);

    // Débounce dry-run instantané + auto-validation (logique 16.5 inchangée).
    if (selectorState.active) {
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
          runDryRun(eqId, cmdId, type, $diagCell, $spinner);
        }, DEBOUNCE_MS);
      });
    }

    // Story 20-2 (P1, relecture indépendante PR #210) : ce lien ne porte que sur l'override de
    // TYPE de cette seule commande (route TYPE, 16-8) — jamais sur l'override de publication de
    // toute l'entité. `revertPublication` (revertPublicationOverride) retirerait exclusion et
    // forçage de l'entité entière sans confirmation, ce que ce lien ne doit jamais faire (AC5).
    // Reprise X5d (P3, relecture indépendante PR #210) : en cas d'échec (démon en erreur ou
    // requête réseau), le lien restait inerte pour le reste de la session (`.off('click')` sans
    // jamais être réattaché). On réaffiche une cause lisible dans `$revertError` et on réattache
    // le gestionnaire pour permettre un nouvel essai ; en cas de succès, on recharge l'équipement
    // comme avant.
    var $revertLink = $tr.find('.mo-revert-cmd');
    function attachRevertHandler() {
      $revertLink.one('click', function () {
        clearRequestError($revertError);
        $revertLink.prop('disabled', true);
        revertCommand(eqId, cmdId, $revertLink, $revertError, attachRevertHandler);
      });
    }
    attachRevertHandler();

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
        // inéligibilité amont) plutôt que `null`, pour que `renderDiagnosticCell` puisse
        // distinguer « vraiment non couverte » d'une cause amont à afficher (I4).
        if (!covered) {
          renderDiagnosticCell($diagCell, M.readPreviewAuto(result), false);
          return;
        }
        var view = M.readPreviewOverridden(result);
        renderDiagnosticCell($diagCell, view, true);
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
    $wrap.append($('<p></p>').text('{{Exclure cet équipement de Home Assistant ?}}'));
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
        : '{{Exclure cette entité de Home Assistant ?}}';
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

  function applyEquipment(eqId, $button, $errorSlot) {
    $button.prop('disabled', true);
    clearRequestError($errorSlot);
    $.ajax({ type: 'POST', url: AJAX_URL, data: { action: 'executeHaAction', intention: 'publier',
      portee: 'equipement', selection: JSON.stringify([eqId]) }, dataType: 'json' })
      .always(function () { $button.prop('disabled', false); })
      .done(function (resp) {
        var error = M.readPublicationRequestError(resp);
        if (error) { showRequestError($errorSlot, error); return; }
        reloadEquipment(eqId);
      })
      .fail(function () { showRequestError($errorSlot, '{{Le démon ne répond pas.}}'); });
  }

  // --- Story 20.3 (Q1=A) — compteurs de la pièce ouverte ---
  // Lus uniquement dans les arbres déjà chargés pour cette pièce (aucune autre lecture) ;
  // le dénombrement vit dans le module pur (M.summarizeRoom), jamais de décision recalculée.

  function renderRoomCounters() {
    var $host = $('.modal-j2ha-room .j2ha-room-counters').first();
    if ($host.length === 0 || !ctx.room) {
      return;
    }
    var trees = [];
    for (var i = 0; i < ctx.room.equipments.length; i++) {
      var tree = ctx.trees[ctx.room.equipments[i].eq_id];
      if (tree) {
        trees.push(tree);
      }
    }
    $host.empty();
    if (trees.length === 0) {
      $host.text('{{Chargement des compteurs…}}');
      return;
    }
    var labels = M.buildRoomCounterLabels(M.summarizeRoom(trees, ctx.room.equipments.length));
    function line(items, extra) {
      var $line = $('<div class="j2ha-room-counter-line"></div>');
      items.forEach(function (item) {
        $line.append($('<span class="label label-default j2ha-room-counter"></span>').text(item));
      });
      if (extra) {
        $line.append($('<span class="text-muted j2ha-room-counter-unread"></span>').text(extra));
      }
      return $line;
    }
    $host.append(line(labels.equipments, labels.unread));
    $host.append(line(labels.commands));
  }

  // --- Story 20.3 (Q2=A) — actions ciblées déplacées dans la surface ---
  // Mêmes routes (executeHaAction) et mêmes confirmations fortes que l'ancienne synthèse ;
  // les noms (texte libre Jeedom) sont échappés avant d'entrer dans le HTML de la confirmation.

  function escapeHtml(value) {
    return $('<span></span>').text(String(value)).html();
  }

  function showRoomFeedback(message, level) {
    var $slot = $('.modal-j2ha-room .j2ha-room-feedback').first();
    if ($slot.length === 0) {
      return;
    }
    $slot.empty().append($('<div class="alert" role="status"></div>')
      .addClass('alert-' + level).text(message)).show();
  }

  function reloadRoom() {
    if (!ctx.room) {
      return;
    }
    ctx.room.equipments.forEach(function (eq) { reloadEquipment(eq.eq_id); });
  }

  function runHaAction(intention, portee, selection, $button, pendingLabel, onSuccess) {
    var pendingState = setHaActionPendingState($button, pendingLabel);
    executeHaAction(intention, portee, selection, {
      onSuccess: function (payload) {
        showRoomFeedback(buildHaActionUserMessage(payload), getHaActionAlertLevel(payload));
        if (shouldRefreshPublishedScopeAfterHaAction(payload) && onSuccess) {
          onSuccess();
        }
        refreshBridgeStatus();
      },
      onError: function (message) {
        showRoomFeedback(message, 'danger');
      },
      onComplete: function () {
        restoreHaActionPendingState($button, pendingState);
      },
    });
  }

  var RECREATE_WARNING = '<br><br><strong>{{Attention}}</strong> : {{l\'historique, les dashboards, les automatisations et l\'entity_id liés à ces entités peuvent être impactés.}}';

  function appendEquipmentRecreateButton($host, eqId, eqName) {
    var $button = $('<button type="button" class="btn btn-default btn-xs j2ha-eq-recreate" data-ha-action="supprimer"></button>')
      .text('{{Supprimer puis recréer}}');
    $button.on('click', function () {
      if ($button.prop('disabled')) {
        return;
      }
      confirmHaSupprimerAction(
        '{{Supprimer puis recréer dans Home Assistant}}',
        '{{Supprimer}} "' + escapeHtml(eqName) + '" {{de Home Assistant.}}' + RECREATE_WARNING,
        '{{Supprimer 1 équipement}}',
        function () {
          runHaAction('supprimer', 'equipement', [eqId], $button, '{{Suppression...}}', function () {
            reloadEquipment(eqId);
          });
        }
      );
    });
    $host.append($button);
  }

  function buildRoomActions(room) {
    var $wrap = $('<div class="j2ha-room-actions" style="margin:6px 0;"></div>');
    // La convention daemon object_id=0 (« Sans pièce ») n'est pas une pièce adressable par la
    // portée `piece` (le démon la refuse) : actions de pièce indisponibles, actions par
    // équipement conservées.
    if (room.object_id <= 0) {
      $wrap.append($('<span class="text-muted"></span>')
        .text('{{Republication et suppression de pièce indisponibles pour les équipements sans pièce : utilisez les actions de chaque équipement.}}'));
      return $wrap;
    }
    var $republish = $('<button type="button" class="btn btn-default btn-sm j2ha-room-republish" data-ha-action="republier"></button>')
      .append('<i class="fas fa-upload"></i> ').append(document.createTextNode('{{Republier la pièce}}'));
    $republish.on('click', function () {
      if ($republish.prop('disabled')) {
        return;
      }
      confirmHaPublishAction(
        '{{Republier la pièce}}',
        escapeHtml(room.object_name) + ' — {{republier les équipements inclus de cette pièce. Confirmer ?}}',
        '{{Republier}}',
        function () {
          runHaAction('publier', 'piece', [room.object_id], $republish, '{{En cours...}}', reloadRoom);
        }
      );
    });
    var $recreate = $('<button type="button" class="btn btn-default btn-sm j2ha-room-recreate" data-ha-action="supprimer" style="margin-left:8px;"></button>')
      .append('<i class="fas fa-recycle"></i> ').append(document.createTextNode('{{Supprimer puis recréer la pièce}}'));
    $recreate.on('click', function () {
      if ($recreate.prop('disabled')) {
        return;
      }
      confirmHaSupprimerAction(
        '{{Supprimer puis recréer dans Home Assistant}}',
        '{{Supprimer}} "' + escapeHtml(room.object_name) + '" {{de Home Assistant : tous les équipements publiés de cette pièce.}}' + RECREATE_WARNING,
        '{{Supprimer la pièce}}',
        function () {
          runHaAction('supprimer', 'piece', [room.object_id], $recreate, '{{Suppression...}}', reloadRoom);
        }
      );
    });
    $wrap.append($republish).append($recreate);
    return $wrap;
  }

  // --- Synthèse de publication par équipement (Bloc C) ---

  function renderSummary($panel, tree) {
    var summary = M.summarizePublication(tree);
    var state = M.publicationSummaryState(summary);
    var label = M.buildPublicationSummaryLabel(summary);

    var $badge = $panel.find('.j2ha-eq-publish-badge').first();
    $badge.removeClass('j2ha-publish-ok j2ha-publish-partial j2ha-publish-blocked j2ha-publish-empty j2ha-publish-excluded j2ha-publish-disabled');
    var icon;
    if (state === 'publish') {
      $badge.addClass('j2ha-publish-ok');
      icon = 'fa-check-circle';
    } else if (state === 'partial') {
      $badge.addClass('j2ha-publish-partial');
      icon = 'fa-adjust';
    } else if (state === 'blocked') {
      $badge.addClass('j2ha-publish-blocked');
      icon = 'fa-exclamation-triangle';
    } else if (state === 'excluded') {
      $badge.addClass('j2ha-publish-excluded');
      icon = 'fa-eye-slash';
    } else if (state === 'disabled') {
      $badge.addClass('j2ha-publish-disabled');
      icon = 'fa-pause-circle';
    } else {
      $badge.addClass('j2ha-publish-empty');
      icon = 'fa-minus-circle';
    }
    $badge.empty()
      .append($('<i class="fas"></i>').addClass(icon))
      .append($('<span></span>').text(' ' + label));

    // Ancre vers la première commande bloquante (AC10).
    var $anchorHost = $panel.find('.j2ha-eq-blocking-anchor').first().empty();
    if (summary.first_blocking_cmd_id !== null) {
      var $anchor = $('<a class="cursor j2ha-goto-blocking"><i class="fas fa-arrow-down"></i> {{Voir la première commande bloquante}}</a>');
      $anchor.on('click', function () {
        var $target = $panel.find('tr.mapping-override-cmd[data-cmd-id="' + summary.first_blocking_cmd_id + '"]');
        if ($target.length > 0) {
          var $scroll = $target.closest('.j2ha-eq-cmdlist');
          if ($scroll.length > 0) {
            var top = $target.position() ? $target.position().top : 0;
            $scroll.scrollTop($scroll.scrollTop() + top - 10);
          }
          $target.addClass('j2ha-diag-target-highlight');
          setTimeout(function () { $target.removeClass('j2ha-diag-target-highlight'); }, 2000);
        }
      });
      $anchorHost.append($anchor);
    }
  }

  // Story 19.3 (AC6) — badge « override en attente » : signale que la dernière
  // publication synchronisée (MQTT) ne reflète pas encore l'état courant des overrides
  // (l'utilisateur doit resynchroniser). Purement informatif, ne bloque aucune action.
  function renderSyncBadge($panel, tree) {
    var $badge = $panel.find('.j2ha-eq-sync-badge').first().empty();
    if (!M.shouldShowOverridePendingBadge(tree)) {
      return;
    }
    $badge.append($('<span class="label label-warning"></span>')
      .append($('<i class="fas fa-clock"></i> '))
      .append(document.createTextNode('{{Override en attente — pas encore republié vers Home Assistant}}')));
  }

  // Renvoie le slot d'erreur créé, pour que l'appelant (ex. le bouton « Appliquer »
  // équipement) puisse y afficher ses propres erreurs dans le même emplacement visuel.
  // `entities` (Story 20-2, P2, relecture indépendante PR #210) : l'arbre complet des
  // entités, utilisé uniquement à la portée équipement pour la confirmation d'exclusion
  // (AC5) — ignoré à la portée entité.
  function appendPublicationActions($host, eqId, target, equipment, commands, entities) {
    var state = M.publicationActionState(target, equipment);
    var $group = $('<span class="j2ha-publication-actions" style="margin-left:6px;"></span>');
    var $error = $('<div class="j2ha-publication-error text-danger" style="display:none;margin-top:4px;"></div>');
    // Story 20-2 (P2, relecture ClaudeBox) : chaque bouton grisé porte SA cause propre
    // (déjà publiée, déjà forcée, projection invalide, type hors périmètre, pas de mapping,
    // pas de commande clé) — plus de tooltip générique partagé entre boutons.
    function button(label, policy, enabled, reason) {
      var $button = $('<button type="button" class="btn btn-default btn-xs"></button>').text(label);
      if (!enabled) $button.prop('disabled', true).attr('title', reason || '{{Cette action est sans effet dans l’état courant.}}');
      $button.on('click', function () { requestPublication(eqId, target, equipment, policy, $group.find('button'), commands, $error, entities); });
      $group.append($button);
    }
    button('{{Exclure}}', 'exclude', state.can_exclude, state.exclude_reason);
    button('{{Forcer}}', 'force_publish', state.can_force, state.force_reason);
    var $revert = $('<button type="button" class="btn btn-default btn-xs"></button>').text('{{Revenir au mode automatique}}');
    if (!state.can_revert) $revert.prop('disabled', true).attr('title', state.revert_reason || '{{Aucun override de publication à retirer.}}');
    $revert.on('click', function () { revertPublication(eqId, equipment ? null : target.override_command_id, $group.find('button'), $error); });
    $group.append($revert);
    $host.append($group);
    $host.append($error);
    return $error;
  }

  // Story 20-2 (P2, relecture ClaudeBox AC7) : badge « pas encore appliqué » par entité,
  // miroir du badge équipement (renderSyncBadge) mais lu sur `entity.override_pending`.
  function appendEntityPendingBadge($row, entity) {
    if (!M.shouldShowEntityPendingBadge(entity)) {
      return;
    }
    $row.append($('<span class="label label-warning" style="margin-left:6px;"></span>')
      .append($('<i class="fas fa-clock"></i> '))
      .append(document.createTextNode('{{pas encore appliqué}}')));
  }

  function renderEntities($panel, tree) {
    var $host = $panel.find('.j2ha-eq-entities').first().empty();
    for (var i = 0; i < tree.entities.length; i++) {
      var entity = tree.entities[i];
      var $row = $('<div class="j2ha-entity-row"></div>');
      $row.append($('<strong></strong>').text(entity.ha_entity_type || '{{Entité HA}}'));
      $row.append(document.createTextNode(' — ' + M.entityCommandsLabel(entity, tree.commands)));
      appendEntityPendingBadge($row, entity);
      appendPublicationActions($row, tree.jeedom_eq_id, entity, false, tree.commands);
      $host.append($row);
    }
  }

  // --- Chargement paresseux d'un équipement (un GET par équipement déplié) ---

  function renderEquipmentTree($panel, tree) {
    var normalized = M.normalizeTree(tree);
    var eqId = normalized.jeedom_eq_id;
    var $list = $panel.find('.j2ha-eq-cmdlist').first().empty();
    var $actions = $panel.find('.j2ha-eq-actions').first().empty();

    ctx.trees[eqId] = normalized;
    renderRoomCounters();

    renderSyncBadge($panel, normalized);
    renderEntities($panel, normalized);

    // X6b (P2, relecture indépendante PR #215) : la cible équipement est construite par
    // `equipmentPublicationTarget` (lit `eligible` + `equipment_publication_override` de
    // l'arbre, en plus du veto porté par les entités/commandes) — remplace la construction
    // inline qui ignorait les deux champs additifs du démon sur un équipement inéligible ou
    // sans entité (AC1/AC6).
    //
    // Fusion des deux boutons « Revenir au mode automatique » de l'équipement (le lien CC-19
    // historique, affiché sur un override de type, et celui des actions de publication) :
    // un seul bouton, actif s'il existe un override de type OU de publication. Il appelle
    // `revertPublicationOverride` sans `cmdId` — cette route purge déjà les deux catégories
    // d'override pour tout l'équipement (`_handle_publication_override_revert`, CC-19).
    var $equipmentError = appendPublicationActions($actions, eqId, M.equipmentPublicationTarget(normalized),
      true, normalized.commands, normalized.entities);
    if (normalized.entities.some(function (entity) { return entity.override_pending; })) {
      var $apply = $('<button type="button" class="btn btn-warning btn-xs" style="margin-left:6px;">{{Appliquer}}</button>');
      $apply.on('click', function () { applyEquipment(eqId, $apply, $equipmentError); });
      $actions.append($apply);
    }
    appendEquipmentRecreateButton($actions, eqId, normalized.eq_name || $panel.find('.j2ha-eq-name').first().text());

    if (!normalized.mapped && normalized.commands.length === 0) {
      $list.append($('<div class="text-muted" style="padding:8px;"></div>')
        .text('{{Aucune commande à configurer pour cet équipement.}}'));
      renderSummary($panel, normalized);
      return;
    }

    var $table = $('<table class="table table-condensed j2ha-cmd-table"></table>');
    var $thead = $('<thead></thead>');
    $thead.append($('<tr></tr>')
      .append($('<th class="mo-th-name"></th>').text('{{Commande}}'))
      .append($('<th class="mo-th-generic"></th>').text('generic_type'))
      .append($('<th class="mo-th-override"></th>').text('{{Override HA}}'))
      .append($('<th class="mo-th-diag"></th>').text('{{Diagnostic}}')));
    $table.append($thead);
    var $tbody = $('<tbody></tbody>');
    for (var i = 0; i < normalized.commands.length; i++) {
      $tbody.append(renderCommandRow(eqId, normalized.commands[i]));
    }
    $table.append($tbody);
    $list.append($table);

    renderSummary($panel, normalized);
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
        $status.text('');
        var result = data && data.result ? data.result : data;
        renderEquipmentTree($panel, result && result.payload ? result.payload : result);
      },
      error: function () {
        $status.text('{{Impossible de charger la configuration HA (daemon indisponible).}}');
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

  // --- Modale par pièce : accordéon des équipements ---

  function buildRoomModalHtml(room) {
    var $wrap = $('<div class="j2ha-room-surface"></div>');
    $wrap.append($('<div id="j2haSurface_reassurance" class="alert alert-warning" role="status" aria-live="polite" style="display:none;">' +
      '<i class="fas fa-shield-alt"></i> {{Aucun impact Homebridge : cet écran ne modifie que la sortie Home Assistant de jeedom2ha.}}</div>'));

    $wrap.append($('<div class="j2ha-room-counters text-muted" role="status" aria-live="polite" style="margin:6px 0;"></div>'));
    $wrap.append(buildRoomActions(room));
    $wrap.append($('<div class="j2ha-room-feedback" role="status" style="display:none;margin:6px 0;"></div>'));

    var $accordion = $('<div class="panel-group j2ha-eq-accordion" role="tablist" aria-multiselectable="true"></div>');
    for (var i = 0; i < room.equipments.length; i++) {
      var eq = room.equipments[i];
      var panelId = 'j2haEqBody_' + room.object_id + '_' + eq.eq_id;
      var headId = 'j2haEqHead_' + room.object_id + '_' + eq.eq_id;

      var $panel = $('<div class="panel panel-default j2ha-eq-panel"></div>')
        .attr('data-eq-id', eq.eq_id);
      if (!eq.enabled) {
        $panel.addClass('j2ha-eq-disabled');
      }

      var $head = $('<div class="panel-heading" role="tab"></div>').attr('id', headId);
      var $toggle = $('<a class="j2ha-eq-toggle" role="button" data-toggle="collapse"></a>')
        .attr('href', '#' + panelId)
        .attr('aria-expanded', 'false')
        .attr('aria-controls', panelId);
      $toggle.append($('<span class="j2ha-eq-name"></span>').text(eq.eq_name || ('#' + eq.eq_id)));
      if (!eq.enabled) {
        $toggle.append($('<span class="text-muted"></span>').text(' {{(désactivé dans Jeedom)}}'));
      }
      $toggle.append($('<span class="j2ha-eq-publish-badge label"></span>'));
      $head.append($('<h4 class="panel-title"></h4>').append($toggle));
      $panel.append($head);

      var $collapse = $('<div class="panel-collapse collapse" role="tabpanel"></div>')
        .attr('id', panelId)
        .attr('aria-labelledby', headId);
      var $body = $('<div class="panel-body"></div>');
      $body.append($('<div class="j2ha-eq-status text-muted"></div>'));
      $body.append($('<div class="j2ha-eq-sync-badge" style="margin:4px 0;"></div>'));
      $body.append($('<div class="j2ha-eq-blocking-anchor" style="margin:4px 0;"></div>'));
      $body.append($('<div class="j2ha-eq-actions" style="margin:4px 0;"></div>'));
      $body.append($('<div class="j2ha-eq-entities" style="margin:4px 0;"></div>'));
      $body.append($('<div class="j2ha-eq-cmdlist panel-group" role="tablist" aria-multiselectable="true" style="max-height:calc(100vh - 320px); overflow-y:auto;"></div>'));
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
    ctx.room = room;

    var $content = buildRoomModalHtml(room);

    bootbox.dialog({
      title: '<i class="fas fa-home"></i> ' + $('<span>').text(room.object_name).html(),
      message: $content,
      size: 'large',
      className: 'modal-j2ha-room',
      onEscape: true,
      backdrop: true,
    });
    $('.modal-j2ha-room .modal-dialog').css('width', '90%').css('max-width', '1100px');
    renderRoomCounters();
    // Les boutons d'action créés après le chargement de la page suivent le même gating que
    // les boutons globaux (pont indisponible, rescan en cours).
    if (typeof applyHAGating === 'function') {
      applyHAGating(window.jeedom2haLastBridgeStatus || null);
    }

    // Garde-fou dépliage : si un panneau n'a pas encore été chargé (ex. échec
    // réseau initial), on le charge à la première ouverture.
    $content.on('shown.bs.collapse', '.j2ha-eq-panel > .panel-collapse', function () {
      var $panel = $(this).closest('.j2ha-eq-panel');
      if ($panel.data('loaded')) {
        return;
      }
      $panel.data('loaded', true);
      loadEquipment($panel, parseInt($panel.attr('data-eq-id'), 10));
    });

    // Synthèse de publication immédiate (AC9) : on charge le diagnostic de chaque
    // équipement de la pièce dès l'ouverture pour que le badge « sera / ne sera
    // pas publié » soit visible sans déplier l'accordéon. La lazyness reste au
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
