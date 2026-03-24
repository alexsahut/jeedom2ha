/* This file is part of Jeedom.
*
* Jeedom is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* Jeedom is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with Jeedom. If not, see <http://www.gnu.org/licenses/>.
*/

/* Statut du pont MQTT — badge distinct du badge daemon natif Jeedom */
function refreshBridgeStatus() {
  $.ajax({
    type: 'POST',
    url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    data: {action: 'getBridgeStatus'},
    dataType: 'json',
    success: function(data) {
      if (data.state !== 'ok') {
        $('#span_mqttStatus').removeClass().addClass('label label-danger').text('{{Erreur Jeedom}}');
        return;
      }
      var r = data.result;
      var $badge = $('#span_mqttStatus');
      var $broker = $('#span_mqttBroker');
      if (!r.daemon) {
        $badge.removeClass().addClass('label label-default').text('{{Démon arrêté}}');
        $broker.text('');
        return;
      }
      var mqtt = r.mqtt || {};
      switch (mqtt.state) {
        case 'connected':
          $badge.removeClass().addClass('label label-success').text('{{MQTT Connecté}}');
          break;
        case 'reconnecting':
          $badge.removeClass().addClass('label label-warning').text('{{MQTT Reconnexion...}}');
          break;
        case 'connecting':
          $badge.removeClass().addClass('label label-warning').text('{{MQTT Connexion...}}');
          break;
        case 'disconnected':
          $badge.removeClass().addClass('label label-warning').text('{{MQTT Déconnecté}}');
          break;
        default:
          $badge.removeClass().addClass('label label-default').text('{{MQTT Non configuré}}');
      }
      $broker.text(mqtt.broker || '');
    },
    error: function() {
      $('#span_mqttStatus').removeClass().addClass('label label-danger').text('{{Erreur de communication}}');
    }
  });
}

function _captureNavState() {
  var expanded = [];
  $('#div_scopeSummaryContent .j2ha-piece-detail:visible').each(function() {
    expanded.push($(this).data('piece-id'));
  });
  return {
    expandedPieceIds: expanded,
    scrollTop: $(window).scrollTop(),
  };
}

function _restoreNavState(navState) {
  if (!navState || !navState.expandedPieceIds) { return; }
  for (var i = 0; i < navState.expandedPieceIds.length; i++) {
    var pieceId = navState.expandedPieceIds[i];
    var $detail = $('#div_scopeSummaryContent .j2ha-piece-detail[data-piece-id="' + pieceId + '"]');
    if ($detail.length) {
      $detail.show();
      $('#div_scopeSummaryContent .j2ha-piece-summary[data-piece-id="' + pieceId + '"]')
        .find('.j2ha-toggle-icon').html('&#9660;');
    }
  }
  $(window).scrollTop(navState.scrollTop);
}

function renderPublishedScopeSummary(result, navState) {
  if (typeof Jeedom2haScopeSummary === 'undefined' || !Jeedom2haScopeSummary) {
    $('#div_scopeSummaryContent').html('<div class="alert alert-danger" style="margin-bottom:0;">{{Module de synthèse indisponible côté UI}}</div>');
    return;
  }

  var model = Jeedom2haScopeSummary.createModel(result || {});
  $('#div_scopeSummaryContent').html(Jeedom2haScopeSummary.render(model));
  _restoreNavState(navState || null);
}

function refreshPublishedScopeSummary(preserveNavState) {
  var navState = preserveNavState ? _captureNavState() : null;
  if (!preserveNavState) {
    $('#div_scopeSummaryContent').html('<div class="text-muted">{{Chargement de la synthèse backend...}}</div>');
  }
  $.ajax({
    type: 'POST',
    url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    data: {action: 'getPublishedScopeForConsole'},
    dataType: 'json',
    timeout: 15000,
    success: function(data) {
      if (data.state !== 'ok') {
        renderPublishedScopeSummary({
          status: 'unavailable',
          message: '{{Impossible de lire la synthèse backend}}',
        }, null);
        return;
      }
      renderPublishedScopeSummary(data.result || {
        status: 'unavailable',
        message: "{{Contrat published_scope indisponible : lancez d'abord une synchronisation.}}",
      }, navState);
    },
    error: function() {
      renderPublishedScopeSummary({
        status: 'unavailable',
        message: '{{Erreur de communication avec le backend}}',
      }, null);
    }
  });
}

$(function() {
  // Refresh MQTT badge on page load and every 30s when visible
  refreshBridgeStatus();
  setInterval(function() {
    if ($('#div_bridgeStatus').is(':visible')) {
      refreshBridgeStatus();
    }
  }, 5000);

  // Story 1.2 — lecture stricte du contrat published_scope (aucun recalcul métier local)
  // Story 1.5 — toggle accordéon des pièces (délégation sur le conteneur persistant)
  $('#div_scopeSummaryContent').on('click', '.j2ha-piece-summary', function() {
    var pieceId = $(this).data('piece-id');
    var $detail = $('#div_scopeSummaryContent .j2ha-piece-detail[data-piece-id="' + pieceId + '"]');
    var $icon = $(this).find('.j2ha-toggle-icon');
    if ($detail.is(':visible')) {
      $detail.hide();
      $icon.html('&#9654;');
    } else {
      $detail.show();
      $icon.html('&#9660;');
    }
  });

  refreshPublishedScopeSummary();
  setInterval(function() {
    if ($('#div_scopeSummary').is(':visible')) {
      refreshPublishedScopeSummary(true); // Story 1.5 — préserve l'état de navigation
    }
  }, 10000);

  $('#bt_refreshScopeSummary').on('click', function() {
    refreshPublishedScopeSummary(); // rafraîchissement manuel : repart de l'état initial
  });

  // Export diagnostic support — Story 4.4
  $('#bt_exportDiagnostic').on('click', function () {
    var $btn    = $(this);
    var $status = $('#span_exportResult');
    $btn.prop('disabled', true);
    $status.removeClass('label-success label-danger').addClass('label').text('{{Export en cours...}}').show();

    $.ajax({
      type:     'POST',
      url:      'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
      data:     {
        action:       'exportDiagnostic',
        pseudonymize: $('#cb_pseudonymize').is(':checked') ? '1' : '0'
      },
      dataType: 'json',
      timeout:  30000,
      success: function (data) {
        $btn.prop('disabled', false);
        if (data.state !== 'ok') {
          $status.removeClass('label').addClass('label label-danger').text(data.result || '{{Erreur export}}');
          return;
        }
        var json   = JSON.stringify(data.result, null, 2);
        var blob   = new Blob([json], {type: 'application/json'});
        var url    = URL.createObjectURL(blob);
        var today  = new Date().toISOString().slice(0, 10);
        var anchor = document.createElement('a');
        anchor.href     = url;
        anchor.download = 'jeedom2ha-diagnostic-' + today + '.json';
        anchor.click();
        URL.revokeObjectURL(url);
        $status.removeClass('label').addClass('label label-success').text('{{Diagnostic téléchargé}}');
      },
      error: function () {
        $btn.prop('disabled', false);
        $status.removeClass('label').addClass('label label-danger').text('{{Erreur de communication}}');
      }
    });
  });
});

/* Permet la réorganisation des commandes dans l'équipement */
$("#table_cmd").sortable({
  axis: "y",
  cursor: "move",
  items: ".cmd",
  placeholder: "ui-state-highlight",
  tolerance: "intersect",
  forcePlaceholderSize: true
})

/* Fonction permettant l'affichage des commandes dans l'équipement */
function addCmdToTable(_cmd) {
  if (!isset(_cmd)) {
    var _cmd = { configuration: {} }
  }
  if (!isset(_cmd.configuration)) {
    _cmd.configuration = {}
  }
  var tr = '<tr class="cmd" data-cmd_id="' + init(_cmd.id) + '">'
  tr += '<td class="hidden-xs">'
  tr += '<span class="cmdAttr" data-l1key="id"></span>'
  tr += '</td>'
  tr += '<td>'
  tr += '<div class="input-group">'
  tr += '<input class="cmdAttr form-control input-sm roundedLeft" data-l1key="name" placeholder="{{Nom de la commande}}">'
  tr += '<span class="input-group-btn"><a class="cmdAction btn btn-sm btn-default" data-l1key="chooseIcon" title="{{Choisir une icône}}"><i class="fas fa-icons"></i></a></span>'
  tr += '<span class="cmdAttr input-group-addon roundedRight" data-l1key="display" data-l2key="icon" style="font-size:19px;padding:0 5px 0 0!important;"></span>'
  tr += '</div>'
  tr += '<select class="cmdAttr form-control input-sm" data-l1key="value" style="display:none;margin-top:5px;" title="{{Commande info liée}}">'
  tr += '<option value="">{{Aucune}}</option>'
  tr += '</select>'
  tr += '</td>'
  tr += '<td>'
  tr += '<span class="type" type="' + init(_cmd.type) + '">' + jeedom.cmd.availableType() + '</span>'
  tr += '<span class="subType" subType="' + init(_cmd.subType) + '"></span>'
  tr += '</td>'
  tr += '<td>'
  tr += '<label class="checkbox-inline"><input type="checkbox" class="cmdAttr" data-l1key="isVisible" checked/>{{Afficher}}</label> '
  tr += '<label class="checkbox-inline"><input type="checkbox" class="cmdAttr" data-l1key="isHistorized" checked/>{{Historiser}}</label> '
  tr += '<label class="checkbox-inline"><input type="checkbox" class="cmdAttr" data-l1key="display" data-l2key="invertBinary"/>{{Inverser}}</label> '
  tr += '<div style="margin-top:7px;">'
  tr += '<input class="tooltips cmdAttr form-control input-sm" data-l1key="configuration" data-l2key="minValue" placeholder="{{Min}}" title="{{Min}}" style="width:30%;max-width:80px;display:inline-block;margin-right:2px;">'
  tr += '<input class="tooltips cmdAttr form-control input-sm" data-l1key="configuration" data-l2key="maxValue" placeholder="{{Max}}" title="{{Max}}" style="width:30%;max-width:80px;display:inline-block;margin-right:2px;">'
  tr += '<input class="tooltips cmdAttr form-control input-sm" data-l1key="unite" placeholder="Unité" title="{{Unité}}" style="width:30%;max-width:80px;display:inline-block;margin-right:2px;">'
  tr += '</div>'
  tr += '</td>'
  tr += '<td>';
  tr += '<span class="cmdAttr" data-l1key="htmlstate"></span>';
  tr += '</td>';
  tr += '<td>'
  if (is_numeric(_cmd.id)) {
    tr += '<a class="btn btn-default btn-xs cmdAction" data-action="configure"><i class="fas fa-cogs"></i></a> '
    tr += '<a class="btn btn-default btn-xs cmdAction" data-action="test"><i class="fas fa-rss"></i> {{Tester}}</a>'
  }
  tr += '<i class="fas fa-minus-circle pull-right cmdAction cursor" data-action="remove" title="{{Supprimer la commande}}"></i></td>'
  tr += '</tr>'
  $('#table_cmd tbody').append(tr)
  var tr = $('#table_cmd tbody tr').last()
  jeedom.eqLogic.buildSelectCmd({
    id: $('.eqLogicAttr[data-l1key=id]').value(),
    filter: { type: 'info' },
    error: function (error) {
      $('#div_alert').showAlert({ message: error.message, level: 'danger' })
    },
    success: function (result) {
      tr.find('.cmdAttr[data-l1key=value]').append(result)
      tr.setValues(_cmd, '.cmdAttr')
      jeedom.cmd.changeType(tr, init(_cmd.subType))
    }
  })
}

$('.eqLogicAction[data-action=diagnostic]').on('click', function() {
  $.ajax({
    type: 'POST',
    url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    data: {action: 'getDiagnostics'},
    dataType: 'json',
    error: function(request, status, error) {
      handleAjaxError(request, status, error);
    },
    success: function(data) {
      if (data.state != 'ok') {
        $('#div_alert').showAlert({message: data.result, level: 'danger'});
        return;
      }
      
      var equipments = [];
      if (data.result && data.result.payload && data.result.payload.equipments) {
        equipments = data.result.payload.equipments;
      }

      if (equipments.length === 0) {
        bootbox.alert("{{Aucune donnée de couverture disponible. Le diagnostic nécessite qu'une synchronisation ait eu lieu.}}");
        return;
      }
      
      var reasonLabels = {
        'sure': 'Mapping identifié avec certitude (partiel)',
        'probable': 'Mapping probable détecté',
        'ambiguous_skipped': 'Ambiguïté détectée (plusieurs types possibles)',
        'no_mapping': 'Aucun mapping compatible trouvé',
        'no_commands': 'Équipement sans commandes exploitables',
        'no_supported_generic_type': 'Type générique non supporté',
        'disabled_eqlogic': 'Équipement désactivé dans Jeedom',
        'excluded_by_user': 'Exclu manuellement par l\'utilisateur',
        'low_confidence': 'Confiance trop faible pour publication'
      };

      var getStatusLabel = function(status) {
        if (status === 'Publié') return '<span class="label label-success">' + status + '</span>';
        if (status === 'Exclu') return '<span class="label label-default">' + status + '</span>';
        if (status === 'Partiellement publié') return '<span class="label label-info">' + status + '</span>';
        if (status === 'Non publié') return '<span class="label label-warning">' + status + '</span>';
        return '<span class="label label-default">' + status + '</span>';
      };

      var getConfidenceLabel = function(conf) {
        if (conf === 'Sûr') return '<span class="label label-success">' + conf + '</span>';
        if (conf === 'Probable') return '<span class="label label-info">' + conf + '</span>';
        if (conf === 'Ambigu') return '<span class="label label-warning">' + conf + '</span>';
        return '<span class="label" style="background-color:#777!important;color:#fff!important;">' + conf + '</span>';
      };

      // AC4 — Reason codes de typage → lien contextualisé vers #commandtab
      var commandTabReasonCodes = {
        'no_generic_type_configured': true,  // taxonomie fermée AC2
        'ambiguous_skipped': true,
        'no_supported_generic_type': true    // rétro-compat ancien backend
      };

      // AC3 — Accordéon homogène en 5 sections fixes pour TOUS les équipements
      var buildDetailRow = function(eq) {
        var tr = eq.traceability || {};
        var observedCmds = tr.observed_commands || [];
        var typingTrace = tr.typing_trace || [];
        var dt = tr.decision_trace || {};
        var pt = tr.publication_trace || {};

        var closedReason = dt.reason_code || '';
        var isPublished = (eq.status === 'Publié' || eq.status === 'Partiellement publié');
        // AC4: lien #commandtab pour causes de typage (taxonomie fermée ou legacy)
        var linkToCommandTab = commandTabReasonCodes[closedReason] || commandTabReasonCodes[eq.reason_code];

        // Use !important on TR and TD to resist Jeedom/Bootstrap hover overrides
        var html = '<tr class="diag-detail-row" style="display:none;background:transparent!important;">';
        html += '<td colspan="5" style="background:transparent!important;padding:12px 20px;border-top:none;">';

        // --- Section 1 : Commandes observées ---
        html += '<div style="margin-bottom:10px;"><strong>{{Commandes observées}}</strong>';
        if (observedCmds.length > 0) {
          html += '<ul style="margin:4px 0 0 16px;">';
          for (var i = 0; i < observedCmds.length; i++) {
            var oc = observedCmds[i];
            var gt = oc.generic_type
              ? '<span style="background-color:#e8e8e8;color:#333;padding:1px 4px;border-radius:3px;font-size:0.85em;font-family:monospace;border:1px solid #ccc;">' + oc.generic_type + '</span>'
              : '<em style="color:#aaa;">{{Aucun type}}</em>';
            html += '<li><span style="font-weight:600;font-family:monospace;">' + oc.name + '</span> <span style="color:#aaa;font-size:0.8em;">(#' + oc.id + ')</span> \u2192 ' + gt + '</li>';
          }
          html += '</ul>';
        } else {
          html += ' <span style="color:#aaa;font-style:italic;">{{Aucune commande observée}}</span>';
        }
        html += '</div>';

        // --- Section 2 : Typage Jeedom (configured_type vs used_type — AC1) ---
        html += '<div style="margin-bottom:10px;"><strong>{{Typage Jeedom}}</strong>';
        if (typingTrace.length > 0) {
          html += '<ul style="margin:4px 0 0 16px;">';
          for (var j = 0; j < typingTrace.length; j++) {
            var tt = typingTrace[j];
            html += '<li style="color:#2f7d32;"><i class="fas fa-check-circle" style="margin-right:5px;font-size:0.9em;"></i>';
            html += ' <span style="font-family:monospace;font-size:0.9em;">' + tt.logical_role + '</span>';
            html += ' <span style="color:#aaa;font-size:0.8em;">(#' + tt.command_id + ')</span>';
            // Afficher configured_type → used_type (distincts si déviation heuristique)
            var confType = tt.configured_type || '<em style="color:#aaa;">{{—}}</em>';
            var usedType = tt.used_type || '<em style="color:#aaa;">{{—}}</em>';
            if (tt.configured_type && tt.used_type && tt.configured_type !== tt.used_type) {
              html += ' \u2014 <span style="color:#888;font-size:0.8em;">{{configuré}}</span> <span style="background-color:#fff3e0;color:#e65100;padding:1px 4px;border-radius:3px;font-size:0.85em;font-family:monospace;border:1px solid #ffe0b2;">' + confType + '</span>';
              html += ' \u2192 <span style="color:#888;font-size:0.8em;">{{utilisé}}</span> <span style="background-color:#e8f5e9;color:#2e7d32;padding:1px 4px;border-radius:3px;font-size:0.85em;font-family:monospace;border:1px solid #c8e6c9;">' + usedType + '</span>';
            } else {
              html += ' \u2014 <span style="background-color:#e8f5e9;color:#2e7d32;padding:1px 4px;border-radius:3px;font-size:0.85em;font-family:monospace;border:1px solid #c8e6c9;">' + usedType + '</span>';
            }
            html += '</li>';
          }
          html += '</ul>';
        }
        if (eq.unmatched_commands && eq.unmatched_commands.length > 0) {
          html += '<ul style="margin:4px 0 0 16px;">';
          for (var k = 0; k < eq.unmatched_commands.length; k++) {
            var uc = eq.unmatched_commands[k];
            var ucGt = uc.generic_type ? uc.generic_type : '{{Aucun}}';
            html += '<li style="color:#d32f2f;"><i class="fas fa-exclamation-circle" style="margin-right:5px;font-size:0.9em;"></i>';
            html += ' <span style="font-family:monospace;font-size:0.9em;">' + uc.cmd_name + '</span>';
            html += ' <span style="color:#aaa;font-size:0.8em;">(#' + uc.cmd_id + ')</span>';
            html += ' \u2014 <em>{{non mappé}}</em> : <span style="background-color:#ffebee;color:#c62828;padding:1px 4px;border-radius:3px;font-size:0.85em;font-family:monospace;border:1px solid #ffcdd2;">' + ucGt + '</span></li>';
          }
          html += '</ul>';
        }
        if (typingTrace.length === 0 && (!eq.unmatched_commands || eq.unmatched_commands.length === 0)) {
          html += ' <span style="color:#aaa;font-style:italic;">{{Aucun typage appliqué}}</span>';
        }
        if (eq.detected_generic_types && eq.detected_generic_types.length > 0) {
          html += '<div style="margin-top:4px;"><em>{{Types détectés}}&nbsp;: </em>';
          for (var g = 0; g < eq.detected_generic_types.length; g++) {
            if (g > 0) html += ', ';
            html += '<span style="background-color:#e8e8e8;color:#333;padding:1px 4px;border-radius:3px;font-size:0.85em;font-family:monospace;border:1px solid #ccc;">' + eq.detected_generic_types[g] + '</span>';
          }
          html += '</div>';
        }
        html += '</div>';

        // --- Section 3 : Logique de décision (decision_trace sémantique) ---
        html += '<div style="margin-bottom:10px;"><strong>{{Logique de décision}}</strong>';
        // Type HA détecté + confiance (depuis decision_trace)
        var entityTypeLabels = {
          'light': '{{Lumière}}', 'cover': '{{Ouvrant}}', 'switch': '{{Prise / Switch}}',
          'sensor': '{{Capteur}}', 'binary_sensor': '{{Capteur binaire}}'
        };
        var closedConfLabels = {
          'sure': '{{Sûr}}', 'probable': '{{Probable}}', 'ambiguous': '{{Ambigu}}', 'ignore': '{{Ignoré}}'
        };
        if (dt.ha_entity_type) {
          var typeLabel = entityTypeLabels[dt.ha_entity_type] || dt.ha_entity_type;
          html += '<div style="margin-top:4px;font-size:0.9em;">';
          html += '<span style="color:#555;">{{Type HA}}&nbsp;: </span><strong>' + typeLabel + '</strong>';
          if (dt.confidence && dt.confidence !== 'ignore') {
            var confLabel = closedConfLabels[dt.confidence] || dt.confidence;
            html += ' <span style="color:#aaa;margin-left:8px;">\u2014 {{confiance}}&nbsp;: ' + confLabel + '</span>';
          }
          html += '</div>';
        }
        // Cause métier (detail) ou message de succès
        if (eq.detail) {
          html += '<div style="margin-top:4px;color:#555;">' + eq.detail + '</div>';
        } else if (isPublished) {
          html += '<div style="margin-top:4px;color:#2f7d32;">{{Mapping réussi \u2014 équipement éligible et publié.}}</div>';
        }
        if (eq.v1_limitation) {
          html += '<div style="margin-top:6px;"><span class="label label-default">{{Hors périmètre V1}}</span>';
          html += ' <small style="margin-left:6px;color:#888;">{{Ce type d\'équipement n\'est pas encore supporté dans cette version.}}</small></div>';
        }
        html += '</div>';

        // --- Section 4 : Résultat de publication ---
        html += '<div style="margin-bottom:10px;"><strong>{{Résultat de publication}}</strong> ';
        var pubResult = pt.last_discovery_publish_result || 'not_attempted';
        if (pubResult === 'success') {
          html += '<span class="label label-success">{{Succès}}</span>';
        } else if (pubResult === 'failed') {
          html += '<span class="label label-danger">{{Échec}}</span>';
        } else {
          html += '<span class="label label-default">{{Non tenté}}</span>';
        }
        html += '</div>';

        // --- Section 5 : Action recommandée ---
        html += '<div><strong>{{Action recommandée}}</strong>';
        if (eq.status === 'Publié' && (!eq.unmatched_commands || eq.unmatched_commands.length === 0)) {
          html += '<div style="margin-top:4px;color:#2f7d32;"><i class="fas fa-check-circle" style="margin-right:5px;"></i>{{Aucune action requise. L\'équipement est correctement exposé.}}</div>';
        } else if (eq.remediation) {
          html += '<div style="margin-top:4px;">' + eq.remediation + '</div>';
          if (eq.eq_type_name) {
            var href = linkToCommandTab
              ? 'index.php?v=d&m=' + eq.eq_type_name + '&p=' + eq.eq_type_name + '&id=' + eq.eq_id + '#commandtab'
              : 'index.php?v=d&m=' + eq.eq_type_name + '&p=' + eq.eq_type_name + '&id=' + eq.eq_id;
            html += '<div style="margin-top:6px;"><a href="' + href + '" target="_blank" class="btn btn-xs btn-default">';
            html += '<i class="fas fa-external-link-alt"></i> {{Configurer dans Jeedom}}</a></div>';
          }
        } else {
          html += '<div style="margin-top:4px;color:#aaa;font-style:italic;">{{Aucune action disponible.}}</div>';
        }
        html += '</div>';

        html += '</td></tr>';
        return html;
      };

      var renderTable = function(filterText) {
        filterText = (filterText || '').toLowerCase();

        // Group by object_name and filter
        var byObject = {};
        var matchCount = 0;
        for (var i = 0; i < equipments.length; i++) {
          var eq = equipments[i];
          var objName = eq.object_name || "Aucun";

          if (filterText !== '') {
             var searchStr = (objName + ' ' + eq.name + ' ' + eq.status + ' ' + (reasonLabels[eq.reason_code] || '')).toLowerCase();
             if (searchStr.indexOf(filterText) === -1) continue;
          }

          if (!byObject[objName]) {
            byObject[objName] = [];
          }
          byObject[objName].push(eq);
          matchCount++;
        }

        var html = '<table class="table table-bordered table-condensed" id="table_diagnostic" style="width:100%;table-layout:auto;">';
        html += '<thead><tr><th>{{Objet/Pièce}}</th><th>{{Equipement}}</th><th style="width:120px;">{{Statut}}</th><th style="width:100px;">{{Confiance}}</th><th>{{Raison : Explication}}</th></tr></thead>';
        html += '<tbody>';

        var objects = Object.keys(byObject).sort();
        for (var objIdx = 0; objIdx < objects.length; objIdx++) {
          var objName = objects[objIdx];
          var eqs = byObject[objName];

          for (var eqIdx = 0; eqIdx < eqs.length; eqIdx++) {
            var eq = eqs[eqIdx];
            var reasonDescription = reasonLabels[eq.reason_code] || 'Code inconnu';
            // AC3 — accordéon disponible pour TOUS les équipements (y compris Publié)
            var chevron = '<i class="fas fa-chevron-right diag-chevron" style="margin-right:6px;font-size:0.8em;color:#aaa;transition:transform 0.15s;"></i>';

            // Encode enriched data as JSON in data attribute (inclut traceability AC1)
            var detailData = JSON.stringify({
              eq_id: eq.eq_id,
              eq_type_name: eq.eq_type_name || '',
              detail: eq.detail || '',
              remediation: eq.remediation || '',
              v1_limitation: eq.v1_limitation || false,
              unmatched_commands: eq.unmatched_commands || [],
              matched_commands: eq.matched_commands || [],
              detected_generic_types: eq.detected_generic_types || [],
              reason_code: eq.reason_code,
              status: eq.status,
              traceability: eq.traceability || {}
            });

            html += '<tr class="diag-expandable" style="cursor:pointer;" data-detail=\'' + detailData.replace(/'/g, '&#39;') + '\'>';
            html += '<td style="vertical-align:middle;"><strong>' + objName + '</strong></td>';
            html += '<td style="white-space:nowrap;">' + chevron + eq.name + '</td>';
            html += '<td>' + getStatusLabel(eq.status) + '</td>';
            html += '<td>' + getConfidenceLabel(eq.confidence) + '</td>';
            html += '<td><span style="color:#888;font-family:monospace;font-size:0.9em;">' + eq.reason_code + '</span> : <span style="font-size:0.9em;">' + reasonDescription + '</span></td>';
            html += '</tr>';

            html += buildDetailRow(eq);
          }
        }

        if (matchCount === 0) {
           html += '<tr><td colspan="5" class="text-center"><i>{{Aucun résultat pour cette recherche}}</i></td></tr>';
        }

        html += '</tbody></table>';
        return html;
      };

      var bindAccordion = function(container) {
        $(container).off('click', '.diag-expandable').on('click', '.diag-expandable', function() {
          var $row = $(this);
          var $detail = $row.next('.diag-detail-row');
          var isOpen = $detail.is(':visible');

          // Close all open detail rows
          $(container).find('.diag-detail-row:visible').hide();
          $(container).find('.diag-chevron').css('transform', '');

          if (!isOpen) {
            $detail.show();
            $row.find('.diag-chevron').css('transform', 'rotate(90deg)');
          }
        });
      };

      var modalHtml = '<div style="margin-bottom:10px;">';
      modalHtml += '<div class="input-group">';
      modalHtml += '<span class="input-group-addon"><i class="fas fa-search"></i></span>';
      modalHtml += '<input type="text" id="in_searchDiagnostic" class="form-control" placeholder="{{Filtrer par équipement, pièce, statut ou raison...}}">';
      modalHtml += '</div>';
      modalHtml += '</div>';
      modalHtml += '<div id="div_diagnosticTable" style="max-height:calc(100vh - 250px);overflow-y:auto;">' + renderTable() + '</div>';

      bootbox.dialog({
        title: "{{Diagnostic de Couverture}}",
        message: modalHtml,
        size: "large",
        className: "modal-diagnostic",
        onEscape: true,
        backdrop: true
      });

      // Force modal width for large screens
      $('.modal-diagnostic .modal-dialog').css('width', '90%').css('max-width', '1200px');

      // Bind accordion on initial render
      bindAccordion('#div_diagnosticTable');

      $('#in_searchDiagnostic').off('keyup').on('keyup', function() {
         var val = $(this).val();
         $('#div_diagnosticTable').html(renderTable(val));
         // Re-bind accordion after re-render
         bindAccordion('#div_diagnosticTable');
      });    }
  });
});
