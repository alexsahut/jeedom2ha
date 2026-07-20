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
  var ctx = { reassurance: M.initReassuranceState(), timers: {}, xhr: {} };

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

  function renderDiagnosticCell($cell, view) {
    var state = M.diagnosticState(view);
    var msg = M.buildPublishCellLabel(view);
    $cell.removeClass('j2ha-diag-ready j2ha-diag-blocking j2ha-diag-unknown');
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
    $tdOverride.append($select);
    var $spinner = $('<span class="mo-spinner" style="display:none;"><i class="fas fa-spinner fa-spin"></i></span>');
    $tdOverride.append($spinner);
    if (row.override_applied) {
      $tdOverride.append($('<a class="mo-revert-cmd cursor" title="{{Revenir au mode automatique}}"><i class="fas fa-undo"></i></a>'));
    }
    $tr.append($tdOverride);

    // Colonne 4 : diagnostic — « ce qui sera publié » / « ne sera pas publié + raison ».
    var $diagCell = $('<td class="mo-td-diag mo-diag-cell"></td>');
    renderDiagnosticCell($diagCell, row.diagnostic);
    $tr.append($diagCell);

    // Débounce dry-run instantané + auto-validation (logique 16.5 inchangée).
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

    $tr.find('.mo-revert-cmd').on('click', function () {
      revertCommand(eqId, cmdId);
    });

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
        var view = M.readPreviewOverridden(data && data.result ? data.result : data);
        renderDiagnosticCell($diagCell, view);
        maybeShowReassurance(M.isBlockingDiagnostic(view));
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

  function revertCommand(eqId, cmdId) {
    $.ajax({
      type: 'POST',
      url: AJAX_URL,
      data: { action: 'revertMappingOverride', eqId: eqId, cmdId: cmdId },
      dataType: 'json',
      success: function () {
        reloadEquipment(eqId);
      },
    });
  }

  function revertEquipment(eqId) {
    $.ajax({
      type: 'POST',
      url: AJAX_URL,
      data: { action: 'revertMappingOverride', eqId: eqId },
      dataType: 'json',
      success: function () {
        reloadEquipment(eqId);
      },
    });
  }

  // --- Synthèse de publication par équipement (Bloc C) ---

  function renderSummary($panel, tree) {
    var summary = M.summarizePublication(tree);
    var state = M.publicationSummaryState(summary);
    var label = M.buildPublicationSummaryLabel(summary);

    var $badge = $panel.find('.j2ha-eq-publish-badge').first();
    $badge.removeClass('j2ha-publish-ok j2ha-publish-partial j2ha-publish-blocked j2ha-publish-empty');
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

  // --- Chargement paresseux d'un équipement (un GET par équipement déplié) ---

  function renderEquipmentTree($panel, tree) {
    var normalized = M.normalizeTree(tree);
    var eqId = normalized.jeedom_eq_id;
    var $list = $panel.find('.j2ha-eq-cmdlist').first().empty();
    var $actions = $panel.find('.j2ha-eq-actions').first().empty();

    if (!normalized.mapped && normalized.commands.length === 0) {
      $list.append($('<div class="text-muted" style="padding:8px;"></div>')
        .text('{{Aucune commande à configurer pour cet équipement.}}'));
      renderSummary($panel, normalized);
      return;
    }

    var hasOverride = false;
    for (var k = 0; k < normalized.commands.length; k++) {
      if (normalized.commands[k].override_applied) {
        hasOverride = true;
        break;
      }
    }
    if (hasOverride) {
      var $revertEq = $('<a class="mo-revert-eq cursor btn btn-default btn-xs"><i class="fas fa-undo"></i> ' +
        '{{Revenir au mode automatique (tout l’équipement)}}</a>');
      $revertEq.on('click', function () {
        revertEquipment(eqId);
      });
      $actions.append($revertEq);
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
        $toggle.append($('<span class="text-muted"></span>').text(' {{(désactivé)}}'));
      }
      $toggle.append($('<span class="j2ha-eq-publish-badge label"></span>'));
      $head.append($('<h4 class="panel-title"></h4>').append($toggle));
      $panel.append($head);

      var $collapse = $('<div class="panel-collapse collapse" role="tabpanel"></div>')
        .attr('id', panelId)
        .attr('aria-labelledby', headId);
      var $body = $('<div class="panel-body"></div>');
      $body.append($('<div class="j2ha-eq-status text-muted"></div>'));
      $body.append($('<div class="j2ha-eq-blocking-anchor" style="margin:4px 0;"></div>'));
      $body.append($('<div class="j2ha-eq-actions" style="margin:4px 0;"></div>'));
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

    var $content = buildRoomModalHtml(room);

    bootbox.dialog({
      title: '<i class="fas fa-house-signal"></i> ' + $('<span>').text(room.object_name).html(),
      message: $content,
      size: 'large',
      className: 'modal-j2ha-room',
      onEscape: true,
      backdrop: true,
    });
    $('.modal-j2ha-room .modal-dialog').css('width', '90%').css('max-width', '1100px');

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
