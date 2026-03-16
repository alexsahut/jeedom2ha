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

$(function() {
  // Refresh MQTT badge on page load and every 30s when visible
  refreshBridgeStatus();
  setInterval(function() {
    if ($('#div_bridgeStatus').is(':visible')) {
      refreshBridgeStatus();
    }
  }, 5000);
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
        'sure': 'Mapping identifié avec certitude',
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
        if (status === 'Exclu') return '<span class="label label-danger">' + status + '</span>';
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
        
        var html = '<table class="table table-bordered table-condensed table-hover" id="table_diagnostic" style="width:100%;table-layout:auto;">';
        html += '<thead><tr><th>{{Objet/Pièce}}</th><th>{{Equipement}}</th><th style="width:120px;">{{Statut}}</th><th style="width:100px;">{{Confiance}}</th><th>{{Raison : Explication}}</th></tr></thead>';
        html += '<tbody>';
        
        var objects = Object.keys(byObject).sort();
        for (var objIdx = 0; objIdx < objects.length; objIdx++) {
          var objName = objects[objIdx];
          var eqs = byObject[objName];
          
          for (var eqIdx = 0; eqIdx < eqs.length; eqIdx++) {
            var eq = eqs[eqIdx];
            var reasonDescription = reasonLabels[eq.reason_code] || 'Code inconnu';
            html += '<tr>';
            if (eqIdx === 0) {
              html += '<td rowspan="' + eqs.length + '" style="vertical-align:middle;"><strong>' + objName + '</strong></td>';
            }
            html += '<td style="white-space:nowrap;">' + eq.name + '</td>';
            html += '<td>' + getStatusLabel(eq.status) + '</td>';
            html += '<td>' + getConfidenceLabel(eq.confidence) + '</td>';
            html += '<td><span style="color:#888;font-family:monospace;font-size:0.9em;">' + eq.reason_code + '</span> : <span style="font-size:0.9em;">' + reasonDescription + '</span></td>';
            html += '</tr>';
          }
        }
        
        if (matchCount === 0) {
           html += '<tr><td colspan="5" class="text-center"><i>{{Aucun résultat pour cette recherche}}</i></td></tr>';
        }
        
        html += '</tbody></table>';
        return html;
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
      
      $('#in_searchDiagnostic').off('keyup').on('keyup', function() {
         var val = $(this).val();
         $('#div_diagnosticTable').html(renderTable(val));
      });    }
  });
});

