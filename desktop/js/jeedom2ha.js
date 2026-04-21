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

/* Statut du pont MQTT et santé globale (Story 2.2) */
function refreshBridgeStatus() {
  $.ajax({
    type: 'POST',
    url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    data: {action: 'getBridgeStatus'},
    dataType: 'json',
    success: function(data) {
      if (data.state !== 'ok') {
        window.jeedom2haLastBridgeStatus = null;
        $('#span_healthBridge').removeClass().addClass('label label-danger').text('{{Erreur Jeedom}}');
        $('#span_healthMqtt').removeClass().addClass('label label-default').text('{{Inconnu}}');
        applyHAGating(null);
        return;
      }
      var r = data.result;
      window.jeedom2haLastBridgeStatus = r;
      var $bridge = $('#span_healthBridge');
      var $mqtt = $('#span_healthMqtt');
      var $broker = $('#span_healthMqttBroker');
      var $sync = $('#span_healthSync');
      var $op = $('#span_healthOp');
      var $opMsg = $('#span_healthOpMsg');

      // 1. Bridge (Démon)
      if (!r.daemon) {
        // Incident d'infrastructure -> ROUGE
        $bridge.removeClass().addClass('label label-danger').text('{{Arrêté}}');
        $mqtt.removeClass().addClass('label label-default').text('{{Inconnu}}');
        $broker.text('');
        $sync.text('{{Inconnue}}');
        $op.removeClass().addClass('label label-default').text('{{Inconnue}}');
        $opMsg.text('');
        applyHAGating(r);
        return;
      } else {
        $bridge.removeClass().addClass('label label-success').text('{{Actif}}');
      }

      // 2. MQTT
      var brokerInfo = r.broker || r.mqtt || {};
      switch (brokerInfo.state) {
        case 'connected':
          $mqtt.removeClass().addClass('label label-success').text('{{Connecté}}');
          break;
        case 'reconnecting':
          $mqtt.removeClass().addClass('label label-warning').text('{{Reconnexion...}}');
          break;
        case 'connecting':
          $mqtt.removeClass().addClass('label label-warning').text('{{Connexion...}}');
          break;
        case 'disconnected':
          // Incident d'infrastructure -> ROUGE absolument (Guardrail Story 2.2)
          $mqtt.removeClass().addClass('label label-danger').text('{{Déconnecté}}');
          break;
        default:
          $mqtt.removeClass().addClass('label label-default').text('{{Non configuré}}');
      }
      $broker.text(brokerInfo.broker || '');

      // 3. Dernière synchro
      if (r.derniere_synchro_terminee) {
        var d = new Date(r.derniere_synchro_terminee);
        var dateStr = ('0' + d.getDate()).slice(-2) + '/' + ('0' + (d.getMonth() + 1)).slice(-2) + ' ' + ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2) + ':' + ('0' + d.getSeconds()).slice(-2);
        $sync.text(dateStr);
      } else {
        $sync.text('{{Jamais}}');
      }

      // 4. Dernière opération
      var _opObj = Jeedom2haScopeSummary.readOperationSnapshot(r.derniere_operation_resultat);
      switch (_opObj.resultat) {
        case 'succes':
          $op.removeClass().addClass('label label-success').text('{{Succès}}');
          break;
        case 'partiel':
          // Problème de configuration -> NON ROUGE (Warning orange)
          $op.removeClass().addClass('label label-warning').text('{{Partiel}}').css('background-color', '#e67e22');
          break;
        case 'echec':
          // Problème de configuration complet -> NON ROUGE (Warning orange)
          $op.removeClass().addClass('label label-warning').text('{{Échec}}').css('background-color', '#e67e22');
          break;
        case 'aucun':
          $op.removeClass().addClass('label label-default').text('{{Aucune}}');
          break;
        default:
          $op.removeClass().addClass('label label-default').text('{{' + _opObj.resultat + '}}');
      }
      $opMsg.text(_opObj.message || '');
      applyHAGating(r);
    },
    error: function() {
      window.jeedom2haLastBridgeStatus = null;
      $('#span_healthBridge').removeClass().addClass('label label-danger').text('{{Erreur de communication}}');
      $('#span_healthMqtt').removeClass().addClass('label label-default').text('{{Inconnu}}');
      applyHAGating(null);
    }
  });
}

/* Gating des actions Home Assistant selon la santé du pont (Story 2.3) */

/**
 * Retourne true si le pont est opérationnel pour des actions HA.
 * Source unique : payload r de /system/status (Story 2.1 contrat).
 * @param {Object} r - data.result de l'appel getBridgeStatus
 */
function isHABridgeAvailable(r) {
  if (!r || !r.daemon) return false;
  var brokerInfo = r.broker || r.mqtt || {};
  return brokerInfo.state === 'connected';
}

/**
 * Applique ou lève le gating sur tous les éléments [data-ha-action].
 * Ne touche PAS aux éléments locaux de périmètre.
 * @param {Object} r - data.result de l'appel getBridgeStatus (peut être null si erreur)
 */
function applyHAGating(r) {
  var available = r ? isHABridgeAvailable(r) : false;
  var $haActions = $('[data-ha-action]');
  var $reason = $('#div_haGatingReason');

  if (available) {
    $haActions.prop('disabled', false).removeClass('j2ha-ha-gated');
    $reason.hide();
  } else {
    $haActions.prop('disabled', true).addClass('j2ha-ha-gated');
    var reason = '{{Bridge ou MQTT indisponible — actions Home Assistant bloquées.}}';
    if (r && !r.daemon) {
      reason = '{{Daemon arrêté — actions Home Assistant bloquées.}}';
    } else if (r) {
      reason = '{{MQTT déconnecté — actions Home Assistant bloquées.}}';
    }
    $reason.text(reason).show();
  }
}

function _captureNavState() {
  var expandedNodeIds = [];
  $('#div_scopeSummaryContent .j2ha-row-toggle[data-expanded="true"]').each(function() {
    var nodeId = $(this).attr('data-node-id');
    if (typeof nodeId === 'string' && nodeId !== '') {
      expandedNodeIds.push(nodeId);
    }
  });
  return {
    expandedNodeIds: expandedNodeIds,
    scrollTop: $(window).scrollTop(),
  };
}

function _setScopeSummaryToggleVisual($row, expanded) {
  var icon = expanded ? '&#9660;' : '&#9654;';
  $row.attr('data-expanded', expanded ? 'true' : 'false');
  $row.find('.j2ha-toggle-icon').first().html(icon);
}

function _toggleScopeSummaryHierarchyRow($row, forceExpanded) {
  if (!$row || $row.length === 0) {
    return;
  }
  var nodeType = $row.attr('data-node-type');
  var isExpanded = ($row.attr('data-expanded') === 'true');
  var expanded = (typeof forceExpanded === 'boolean') ? forceExpanded : !isExpanded;

  if (nodeType === 'global') {
    _setScopeSummaryToggleVisual($row, expanded);
    var $pieceRows = $('#div_scopeSummaryContent .j2ha-child-of-global');
    if (expanded) {
      $pieceRows.show();
      return;
    }
    $pieceRows.hide();
    $('#div_scopeSummaryContent .j2ha-row-equipement').hide();
    $('#div_scopeSummaryContent .j2ha-row-toggle[data-node-type="piece"]').each(function() {
      _setScopeSummaryToggleVisual($(this), false);
    });
    return;
  }

  if (nodeType === 'piece') {
    var pieceId = $row.attr('data-piece-id');
    if (typeof pieceId !== 'string' || pieceId === '') {
      return;
    }
    _setScopeSummaryToggleVisual($row, expanded);
    var selector = '.j2ha-child-of-piece-' + pieceId;
    if (expanded) {
      $('#div_scopeSummaryContent ' + selector).show();
    } else {
      $('#div_scopeSummaryContent ' + selector).hide();
    }
  }
}

function _restoreNavState(navState) {
  if (!navState || !Array.isArray(navState.expandedNodeIds)) {
    return;
  }

  var expandedByNodeId = {};
  for (var i = 0; i < navState.expandedNodeIds.length; i++) {
    expandedByNodeId[String(navState.expandedNodeIds[i])] = true;
  }

  if (expandedByNodeId.global === true) {
    _toggleScopeSummaryHierarchyRow(
      $('#div_scopeSummaryContent .j2ha-row-toggle[data-node-id="global"]').first(),
      true
    );
  }

  $('#div_scopeSummaryContent .j2ha-row-toggle[data-node-type="piece"]').each(function() {
    var nodeId = $(this).attr('data-node-id');
    if (expandedByNodeId[String(nodeId)] === true) {
      _toggleScopeSummaryHierarchyRow($(this), true);
    }
  });

  if (typeof navState.scrollTop === 'number' && Number.isFinite(navState.scrollTop)) {
    $(window).scrollTop(navState.scrollTop);
  }
}

function _readHaActionCount(value) {
  var count = parseInt(value, 10);
  if (Number.isFinite(count) && count >= 0) {
    return count;
  }
  return 0;
}

function buildHaActionUserMessage(payload) {
  var message = (payload && typeof payload.message === 'string' && payload.message !== '')
    ? payload.message
    : '{{Action Home Assistant exécutée.}}';
  var impactedName = payload && payload.perimetre_impacte && typeof payload.perimetre_impacte.nom === 'string'
    ? payload.perimetre_impacte.nom
    : '';
  return impactedName !== '' ? (impactedName + ' — ' + message) : message;
}

function getHaActionAlertLevel(payload) {
  var resultat = payload && typeof payload.resultat === 'string' ? payload.resultat : '';
  if (resultat === 'succes') {
    return 'success';
  }
  if (resultat === 'succes_partiel') {
    return 'warning';
  }
  return 'danger';
}

function shouldRefreshPublishedScopeAfterHaAction(payload) {
  if (!payload || typeof payload.resultat !== 'string') {
    return false;
  }
  return payload.resultat === 'succes' || payload.resultat === 'succes_partiel';
}

function setHaActionPendingState($button, pendingLabel) {
  var snapshot = {
    html: $button.html(),
    disabled: $button.prop('disabled') === true,
  };
  $button.prop('disabled', true);
  $button.html('<i class="fas fa-spinner fa-spin"></i> ' + pendingLabel);
  return snapshot;
}

function restoreHaActionPendingState($button, snapshot) {
  if (!$button || $button.length === 0) {
    return;
  }
  if (snapshot && typeof snapshot.html === 'string') {
    $button.html(snapshot.html);
  }
  $button.prop('disabled', snapshot && snapshot.disabled === true);
}

function showHaActionFeedback(payload) {
  $('#div_alert').showAlert({
    message: buildHaActionUserMessage(payload),
    level: getHaActionAlertLevel(payload),
  });
}

function confirmHaPublishAction(title, message, confirmLabel, onConfirm) {
  if (typeof bootbox !== 'undefined' && bootbox && typeof bootbox.dialog === 'function') {
    bootbox.dialog({
      title: title,
      message: '<div>' + message + '</div>',
      buttons: {
        cancel: {
          label: '{{Annuler}}',
          className: 'btn-default',
        },
        confirm: {
          label: confirmLabel,
          className: 'btn-primary',
          callback: function() {
            onConfirm();
          },
        },
      },
    });
    return;
  }
  if (window.confirm(message)) {
    onConfirm();
  }
}

function executeHaAction(intention, portee, selection, handlers) {
  $.ajax({
    type: 'POST',
    url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    data: {
      action: 'executeHaAction',
      intention: intention,
      portee: portee,
      selection: JSON.stringify(selection || []),
    },
    dataType: 'json',
    timeout: 20000,
    success: function(data) {
      if (data.state !== 'ok') {
        if (handlers && typeof handlers.onError === 'function') {
          handlers.onError(data.result || '{{Impossible d\'exécuter l\'action Home Assistant.}}');
        }
        return;
      }
      var daemonResult = (data && data.result && typeof data.result === 'object') ? data.result : {};
      var payload = (daemonResult && daemonResult.payload && typeof daemonResult.payload === 'object')
        ? daemonResult.payload
        : null;
      if (!payload) {
        if (handlers && typeof handlers.onError === 'function') {
          handlers.onError('{{Réponse backend incomplète pour l\'action Home Assistant.}}');
        }
        return;
      }
      if (handlers && typeof handlers.onSuccess === 'function') {
        handlers.onSuccess(payload, daemonResult);
      }
    },
    error: function(request, status, error) {
      var message = '{{Erreur de communication avec le backend Home Assistant.}}';
      if (handlers && typeof handlers.onError === 'function') {
        handlers.onError(message);
      }
    },
    complete: function() {
      if (handlers && typeof handlers.onComplete === 'function') {
        handlers.onComplete();
      }
    },
  });
}

function triggerPublierAction($button, portee, selection) {
  var pendingState = setHaActionPendingState($button, '{{En cours...}}');
  executeHaAction('publier', portee, selection, {
    onSuccess: function(payload) {
      showHaActionFeedback(payload);
      if (shouldRefreshPublishedScopeAfterHaAction(payload)) {
        var preserveNavState = true;
        refreshPublishedScopeSummary(preserveNavState);
      }
      refreshBridgeStatus();
    },
    onError: function(message) {
      $('#div_alert').showAlert({message: message, level: 'danger'});
    },
    onComplete: function() {
      restoreHaActionPendingState($button, pendingState);
    },
  });
}

function triggerSupprimerAction($button, portee, selection) {
  var pendingState = setHaActionPendingState($button, '{{Suppression...}}');
  executeHaAction('supprimer', portee, selection, {
    onSuccess: function(payload) {
      showHaActionFeedback(payload);
      if (shouldRefreshPublishedScopeAfterHaAction(payload)) {
        var preserveNavState = true;
        refreshPublishedScopeSummary(preserveNavState);
      }
      refreshBridgeStatus();
    },
    onError: function(message) {
      $('#div_alert').showAlert({message: message, level: 'danger'});
    },
    onComplete: function() {
      restoreHaActionPendingState($button, pendingState);
    },
  });
}

function confirmHaSupprimerAction(title, message, confirmLabel, onConfirm) {
  if (typeof bootbox !== 'undefined' && bootbox && typeof bootbox.dialog === 'function') {
    bootbox.dialog({
      title: title,
      message: '<div>' + message + '</div>',
      buttons: {
        cancel: {
          label: '{{Annuler}}',
          className: 'btn-default',
        },
        confirm: {
          label: confirmLabel,
          className: 'btn-danger',
          callback: function() {
            onConfirm();
          },
        },
      },
    });
    return;
  }
  if (window.confirm(message)) {
    onConfirm();
  }
}

function renderPublishedScopeSummary(result, navState) {
  if (typeof Jeedom2haScopeSummary === 'undefined' || !Jeedom2haScopeSummary) {
    $('#div_scopeSummaryContent').html('<div class="alert alert-danger" style="margin-bottom:0;">{{Module de synthèse indisponible côté UI}}</div>');
    return;
  }

  var model = Jeedom2haScopeSummary.createModel(result || {});
  $('#div_scopeSummaryContent').html(Jeedom2haScopeSummary.render(model));
  var includedCount = (model && model.has_contract === true && model.global && model.global.counts)
    ? _readHaActionCount(model.global.counts.inclus)
    : 0;
  $('.j2ha-ha-action[data-ha-action="republier"]').attr('data-scope-count', String(includedCount));
  var publiesCount = (model && model.has_contract === true && model.global && model.global.counts)
    ? _readHaActionCount(model.global.counts.publies)
    : 0;
  $('.j2ha-ha-action[data-ha-action="supprimer-recreer"]').attr('data-scope-publies', String(publiesCount));
  _restoreNavState(navState || null);
  applyHAGating(window.jeedom2haLastBridgeStatus || null);
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
  // Refresh MQTT badge on page load (no auto-refresh)
  refreshBridgeStatus();

  // Story 4.5 — tableau hiérarchique unique (global -> pièce -> équipement)
  $('#div_scopeSummaryContent').on('click', '.j2ha-row-toggle', function() {
    _toggleScopeSummaryHierarchyRow($(this));
  });

  // Story 4.5 — badge Écart équipement = point d'entrée diagnostic unique (eq_id stable).
  $('#div_scopeSummaryContent').on('click', '.j2ha-ecart-clickable', function(event) {
    event.preventDefault();
    event.stopPropagation();
    var eqId = parseInt($(this).attr('data-eq-id'), 10);
    if (!Number.isFinite(eqId) || eqId <= 0) {
      return;
    }
    var request = {
      eq_id: eqId,
      source: 'home-ecart-badge',
      timestamp: Date.now(),
    };
    window.jeedom2haHomeDiagnosticTarget = request;
    $(document).trigger('jeedom2ha:diagnostic-open-request', request);
    $('.eqLogicAction[data-action=diagnostic]').first().trigger('click');
  });

  $('#div_scopeSummaryContent').on('keydown', '.j2ha-ecart-clickable', function(event) {
    if (event.key !== 'Enter' && event.key !== ' ') {
      return;
    }
    event.preventDefault();
    $(this).trigger('click');
  });

  $('#div_scopeSummaryContent').on('click', '.j2ha-action-ha-btn[data-ha-action="publier"]', function(event) {
    event.preventDefault();
    event.stopPropagation();
    var $button = $(this);
    if ($button.prop('disabled')) {
      return;
    }
    var eqId = parseInt($button.attr('data-eq-id'), 10);
    if (!Number.isFinite(eqId) || eqId <= 0) {
      return;
    }
    triggerPublierAction($button, 'equipement', [eqId]);
  });

  // Story 5.3 — Click handler équipement Supprimer avec confirmation forte
  $('#div_scopeSummaryContent').on('click', '.j2ha-action-ha-btn[data-ha-action="supprimer"]', function(event) {
    event.preventDefault();
    event.stopPropagation();
    var $button = $(this);
    if ($button.prop('disabled')) {
      return;
    }
    var eqId = parseInt($button.attr('data-eq-id'), 10);
    if (!Number.isFinite(eqId) || eqId <= 0) {
      return;
    }
    var eqName = $button.closest('tr').find('td:first').text().trim() || '{{Équipement}}';
    confirmHaSupprimerAction(
      '{{Supprimer puis recréer dans Home Assistant}}',
      '{{Supprimer}} "' + eqName + '" {{de Home Assistant.}}'
        + '<br><br><strong>{{Attention}}</strong> : {{l\'historique, les dashboards, les automatisations et l\'entity_id liés à cette entité peuvent être impactés.}}',
      '{{Supprimer 1 équipement}}',
      function() {
        triggerSupprimerAction($button, 'equipement', [eqId]);
      }
    );
  });

  $('#div_scopeSummaryContent').on('click', '.j2ha-piece-action-btn[data-ha-action="publier"]', function(event) {
    event.preventDefault();
    event.stopPropagation();
    var $button = $(this);
    if ($button.prop('disabled')) {
      return;
    }
    var pieceId = parseInt($button.attr('data-piece-id'), 10);
    if (!Number.isFinite(pieceId) || pieceId <= 0) {
      return;
    }
    var pieceName = $button.attr('data-piece-name') || '{{Pièce}}';
    var includedCount = _readHaActionCount($button.attr('data-piece-equipements-inclus'));
    confirmHaPublishAction(
      '{{Republier la pièce}}',
      pieceName + ' — ' + includedCount + ' {{équipements inclus. Confirmer ?}}',
      '{{Republier}} ' + includedCount + ' {{équipements}}',
      function() {
        triggerPublierAction($button, 'piece', [pieceId]);
      }
    );
  });

  // Story 5.3 — Click handler pièce Supprimer avec confirmation forte
  $('#div_scopeSummaryContent').on('click', '.j2ha-piece-action-btn[data-ha-action="supprimer"]', function(event) {
    event.preventDefault();
    event.stopPropagation();
    var $button = $(this);
    if ($button.prop('disabled')) {
      return;
    }
    var pieceId = parseInt($button.attr('data-piece-id'), 10);
    if (!Number.isFinite(pieceId) || pieceId <= 0) {
      return;
    }
    var pieceName = $button.attr('data-piece-name') || '{{Pièce}}';
    var publiesCount = _readHaActionCount($button.attr('data-piece-publies'));
    confirmHaSupprimerAction(
      '{{Supprimer puis recréer dans Home Assistant}}',
      '{{Supprimer}} "' + pieceName + '" — ' + publiesCount + ' {{équipement(s) publié(s).}}'
        + '<br><br><strong>{{Attention}}</strong> : {{l\'historique, les dashboards, les automatisations et l\'entity_id liés à ces entités peuvent être impactés.}}',
      '{{Supprimer}} ' + publiesCount + ' {{équipements}}',
      function() {
        triggerSupprimerAction($button, 'piece', [pieceId]);
      }
    );
  });

  refreshPublishedScopeSummary();

  $('#bt_refreshScopeSummary').on('click', function() {
    refreshPublishedScopeSummary(); // rafraîchissement manuel : repart de l'état initial
  });

  $('.j2ha-ha-action[data-ha-action="republier"]').on('click', function(event) {
    event.preventDefault();
    var $button = $(this);
    if ($button.prop('disabled')) {
      return;
    }
    var includedCount = _readHaActionCount($button.attr('data-scope-count'));
    confirmHaPublishAction(
      '{{Republier dans Home Assistant}}',
      '{{Republier dans Home Assistant}} — ' + includedCount + ' {{équipements inclus. Confirmer ?}}',
      '{{Republier}} ' + includedCount + ' {{équipements}}',
      function() {
        triggerPublierAction($button, 'global', ['all']);
      }
    );
  });

  // Story 5.3 — Click handler global Supprimer avec confirmation forte
  $('.j2ha-ha-action[data-ha-action="supprimer-recreer"]').on('click', function(event) {
    event.preventDefault();
    var $button = $(this);
    if ($button.prop('disabled')) {
      return;
    }
    var publiesCount = _readHaActionCount($button.attr('data-scope-publies'));
    confirmHaSupprimerAction(
      '{{Supprimer puis recréer dans Home Assistant}}',
      '{{Supprimer puis recréer dans Home Assistant}} — ' + publiesCount + ' {{équipement(s) publié(s).}}'
        + '<br><br><strong>{{Attention}}</strong> : {{l\'historique, les dashboards, les automatisations et l\'entity_id liés à ces entités peuvent être impactés.}}',
      '{{Supprimer}} ' + publiesCount + ' {{équipements}}',
      function() {
        triggerSupprimerAction($button, 'global', ['all']);
      }
    );
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
        // Codes de publication (état publié partiel)
        'sure': 'Mapping identifié avec certitude (partiel)',
        'probable': 'Mapping probable détecté',
        // Couverture / scope
        'ambiguous_skipped': 'Ambiguïté détectée (plusieurs types possibles)',
        'no_mapping': 'Aucun mapping compatible trouvé',
        'no_supported_generic_type': 'Type générique non supporté',
        'no_generic_type_configured': 'Types génériques non configurés sur les commandes',
        'probable_skipped': 'Confiance probable — politique de publication "sûr uniquement"',
        // Configuration (décision utilisateur ou état Jeedom)
        'no_commands': 'Équipement sans commandes exploitables',
        'disabled_eqlogic': 'Équipement désactivé dans Jeedom',
        'disabled': 'Équipement désactivé dans Jeedom',
        'excluded_eqlogic': 'Exclu manuellement de la publication',
        'excluded_by_user': 'Exclu manuellement par l\'utilisateur',
        'excluded_plugin': 'Plugin source exclu de la publication',
        'excluded_object': 'Pièce exclue de la publication',
        'low_confidence': 'Confiance insuffisante pour la politique active',
        'ha_component_not_in_product_scope': 'Composant Home Assistant non ouvert dans ce cycle',
        // Infrastructure (pannes publiables — réservé au bandeau global et au résultat de publication)
        'discovery_publish_failed': 'Échec de publication MQTT (infrastructure)',
        'local_availability_publish_failed': 'Échec de publication de la disponibilité (infrastructure)'
      };

      var getDiagnosticReasonLabel = (typeof Jeedom2haDiagnosticHelpers !== 'undefined'
        && Jeedom2haDiagnosticHelpers
        && typeof Jeedom2haDiagnosticHelpers.getDiagnosticReasonLabel === 'function')
        ? function(eq) { return Jeedom2haDiagnosticHelpers.getDiagnosticReasonLabel(eq, reasonLabels); }
        : function(eq) {
            if (eq && typeof eq.cause_label === 'string' && eq.cause_label !== '') {
              return eq.cause_label;
            }
            return (eq && eq.reason_code) ? (reasonLabels[eq.reason_code] || '') : '';
          };

      var resolveDiagnosticAction = (typeof Jeedom2haDiagnosticHelpers !== 'undefined'
        && Jeedom2haDiagnosticHelpers
        && typeof Jeedom2haDiagnosticHelpers.resolveDiagnosticAction === 'function')
        ? function(eq) { return Jeedom2haDiagnosticHelpers.resolveDiagnosticAction(eq); }
        : function(eq) {
            if (eq && typeof eq.cause_action === 'string' && eq.cause_action !== '') {
              return { text: eq.cause_action, source: 'cause_action', showConfigLink: false };
            }
            if (eq && typeof eq.remediation === 'string' && eq.remediation !== '') {
              return { text: eq.remediation, source: 'remediation', showConfigLink: true };
            }
            return { text: '', source: 'none', showConfigLink: false };
          };

      var getStatusLabel = function(status) {
        if (status === 'Publié') return '<span class="label label-success">' + status + '</span>';
        if (status === 'Exclu') return '<span class="label label-default">' + status + '</span>';
        if (status === 'Ambigu') return '<span class="label label-warning">' + status + '</span>';
        if (status === 'Non supporté') return '<span class="label label-default" style="background-color:#666!important;">' + status + '</span>';
        if (status === 'Incident infrastructure') return '<span class="label label-danger">' + status + '</span>';
        return '<span class="label label-default">' + status + '</span>';
      };

      var getConfidenceLabel = function(conf) {
        if (conf === 'Sûr') return '<span class="label label-success">' + conf + '</span>';
        if (conf === 'Probable') return '<span class="label label-info">' + conf + '</span>';
        if (conf === 'Ambigu') return '<span class="label label-warning">' + conf + '</span>';
        return '<span class="label" style="background-color:#777!important;color:#fff!important;">' + conf + '</span>';
      };

      // Story 4.6 — AC 2 : badge Écart du diagnostic (lecture stricte backend).
      var getEcartBadge = (typeof Jeedom2haDiagnosticHelpers !== 'undefined'
        && Jeedom2haDiagnosticHelpers
        && typeof Jeedom2haDiagnosticHelpers.getEcartBadgeHtml === 'function')
        ? function(ecart) { return Jeedom2haDiagnosticHelpers.getEcartBadgeHtml(ecart); }
        : function(ecart) {
            if (ecart === true) return '<span class="label label-warning">Ecart</span>';
            if (ecart === false) return '<span class="label label-success">Aligne</span>';
            return '<span class="label label-default">&mdash;</span>';
          };

      // Story 6.1 — AC2 / I7 : source canonique centralisée de la cause (avec fallback sûr).
      var getCanonicalDiagnosticCause = (typeof Jeedom2haDiagnosticHelpers !== 'undefined'
        && Jeedom2haDiagnosticHelpers
        && typeof Jeedom2haDiagnosticHelpers.getCanonicalDiagnosticCause === 'function')
        ? function(eq) { return Jeedom2haDiagnosticHelpers.getCanonicalDiagnosticCause(eq); }
        : function(eq) {
            var tr = (eq && eq.traceability) ? eq.traceability : {};
            var dt = tr.decision_trace || {};
            return dt.reason_code || '';
          };

      // AC4 — Reason codes de typage → lien contextualisé vers #commandtab
      var commandTabReasonCodes = {
        'no_generic_type_configured': true,  // taxonomie fermée AC2
        'ambiguous_skipped': true,
        'no_supported_generic_type': true    // rétro-compat ancien backend
      };

      // AC3 — Accordéon homogène en 5 sections fixes pour TOUS les équipements
      // Story 6.1 — Labels canoniques des étapes du pipeline (lecture backend uniquement).
      var PIPELINE_STEP_LABELS = {
        1: '{{Éligibilité}}',
        2: '{{Mapping}}',
        3: '{{Validation HA}}',
        4: '{{Décision}}',
        5: '{{Publication}}'
      };

      var buildDetailRow = function(eq) {
        var tr = eq.traceability || {};
        var observedCmds = tr.observed_commands || [];
        var typingTrace = tr.typing_trace || [];
        var dt = tr.decision_trace || {};
        var pt = tr.publication_trace || {};

        // Story 6.1 — Étape visible fournie par le backend (lecture stricte — jamais déduite localement).
        var pipelineStep = typeof eq.pipeline_step_visible === 'number' ? eq.pipeline_step_visible : null;

        var closedReason = dt.reason_code || '';
        var isPublished = (eq.status === 'Publié');
        // AC4: lien #commandtab pour causes de typage (taxonomie fermée ou legacy)
        var linkToCommandTab = commandTabReasonCodes[closedReason] || commandTabReasonCodes[eq.reason_code];

        // Use !important on TR and TD to resist Jeedom/Bootstrap hover overrides
        var html = '<tr class="diag-detail-row" style="display:none;background:transparent!important;">';
        html += '<td colspan="6" style="background:transparent!important;padding:12px 20px;border-top:none;">';

        // --- Story 6.1 : Étape pipeline ---
        if (pipelineStep !== null) {
          html += '<div style="margin-bottom:12px;padding:8px 10px;background:#f8f9fa;border-radius:4px;border:1px solid #e9ecef;">';
          html += '<strong style="font-size:0.9em;">{{Étape pipeline}}</strong>';
          html += '<div style="margin-top:6px;display:flex;align-items:center;flex-wrap:wrap;gap:0;">';
          for (var step = 1; step <= 5; step++) {
            var stepLabel = PIPELINE_STEP_LABELS[step] || String(step);
            var isActive = (step === pipelineStep);
            var bg = isActive ? '#0066cc' : '#e9ecef';
            var color = isActive ? '#fff' : '#888';
            var fw = isActive ? '600' : '400';
            var border = isActive ? '1px solid #0055b3' : '1px solid #ced4da';
            html += '<span style="background:' + bg + ';color:' + color + ';font-weight:' + fw + ';border:' + border + ';padding:2px 8px;font-size:0.8em;border-radius:3px;">' + step + ' — ' + stepLabel + '</span>';
            if (step < 5) {
              html += '<span style="color:#ccc;margin:0 2px;font-size:0.8em;">\u2192</span>';
            }
          }
          html += '</div>';
          html += '</div>';
        }

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
          html += '<div style="margin-top:6px;"><span class="label label-default">{{Hors périmètre V1 — Home Assistant}}</span>';
          html += ' <small style="margin-left:6px;color:#888;">{{Ce type d\'équipement n\'est pas encore couvert vers Home Assistant dans cette version.}}</small></div>';
        }
        html += '</div>';

        // --- Section 4 : Résultat de publication ---
        // Story 6.1 AC4 — step 5 failed : deux blocs séparés Décision pipeline / Résultat technique.
        var pubResult = pt.last_discovery_publish_result || 'not_attempted';
        var isStep5Failed = (typeof Jeedom2haDiagnosticHelpers !== 'undefined'
          && Jeedom2haDiagnosticHelpers
          && typeof Jeedom2haDiagnosticHelpers.isStep5Failed === 'function')
          ? Jeedom2haDiagnosticHelpers.isStep5Failed(pipelineStep, pubResult)
          : (pipelineStep === 5 && pubResult === 'failed');

        if (isStep5Failed) {
          // Bloc A — Décision pipeline (cause canonique = décision positive)
          html += '<div style="margin-bottom:6px;padding:8px 10px;background:#e8f5e9;border-radius:4px;border:1px solid #c8e6c9;">';
          html += '<strong style="font-size:0.9em;color:#2e7d32;">{{Décision pipeline}}</strong> ';
          html += '<span class="label label-success">{{Publiée}}</span>';
          // I7 — cause canonique centralisée dans le helper (fallback local sûr si helper indisponible).
          var canonicalReason = getCanonicalDiagnosticCause(eq);
          if (canonicalReason) {
            html += '<div style="margin-top:4px;font-size:0.85em;color:#555;">{{Cause canonique}}&nbsp;: <span style="font-family:monospace;">' + canonicalReason + '</span></div>';
          }
          html += '</div>';
          // Bloc B — Résultat technique (échec MQTT étape 5)
          html += '<div style="margin-bottom:10px;padding:8px 10px;background:#ffeaea;border-radius:4px;border:1px solid #ffcdd2;">';
          html += '<strong style="font-size:0.9em;color:#c62828;">{{Résultat technique}}</strong> ';
          html += '<span class="label label-danger">{{Échec}}</span>';
          var techCode = pt.technical_reason_code || '';
          if (techCode) {
            html += '<div style="margin-top:4px;font-size:0.85em;color:#555;">{{Code technique}}&nbsp;: <span style="font-family:monospace;">' + techCode + '</span></div>';
          }
          html += '</div>';
        } else {
          html += '<div style="margin-bottom:10px;"><strong>{{Résultat de publication}}</strong> ';
          if (pubResult === 'success') {
            html += '<span class="label label-success">{{Succès}}</span>';
          } else if (pubResult === 'failed') {
            html += '<span class="label label-danger">{{Échec}}</span>';
          } else {
            html += '<span class="label label-default">{{Non tenté}}</span>';
          }
          html += '</div>';
        }

        // --- Section 5 : Action recommandée ---
        html += '<div><strong>{{Action recommandée}}</strong>';
        if (eq.status === 'Publié' && (!eq.unmatched_commands || eq.unmatched_commands.length === 0)) {
          html += '<div style="margin-top:4px;color:#2f7d32;"><i class="fas fa-check-circle" style="margin-right:5px;"></i>{{Aucune action requise. L\'équipement est correctement exposé.}}</div>';
        } else {
          var resolvedAction = resolveDiagnosticAction(eq);
          if (resolvedAction.text) {
            html += '<div style="margin-top:4px;">' + resolvedAction.text + '</div>';
          }
          if (resolvedAction.showConfigLink && eq.eq_type_name) {
            var href = linkToCommandTab
              ? 'index.php?v=d&m=' + eq.eq_type_name + '&p=' + eq.eq_type_name + '&id=' + eq.eq_id + '#commandtab'
              : 'index.php?v=d&m=' + eq.eq_type_name + '&p=' + eq.eq_type_name + '&id=' + eq.eq_id;
            html += '<div style="margin-top:6px;"><a href="' + href + '" target="_blank" class="btn btn-xs btn-default">';
            html += '<i class="fas fa-external-link-alt"></i> {{Configurer dans Jeedom}}</a></div>';
          } else if (!resolvedAction.text) {
            html += '<div style="margin-top:4px;color:#aaa;font-style:italic;">{{Aucune action disponible.}}</div>';
          }
        }
        html += '</div>';

        html += '</td></tr>';
        return html;
      };

      var renderTable = function(filterText) {
        filterText = (filterText || '').toLowerCase();

        // Story 4.6 — AC 5 : in-scope only.
        // Le diagnostic standard n'affiche que les équipements inclus dans le périmètre.
        // Les exclus restent absents par design de la vue diagnostic standard.
        var inScopeEquipments = equipments.filter(function(eq) {
          return (eq.perimetre || '') === 'inclus';
        });

        // Group by object_name and apply user filter
        var byObject = {};
        var matchCount = 0;
        for (var i = 0; i < inScopeEquipments.length; i++) {
          var eq = inScopeEquipments[i];
          var objName = eq.object_name || "Aucun";

          if (filterText !== '') {
             var searchStr = (objName + ' ' + eq.name + ' ' + eq.status + ' ' + getDiagnosticReasonLabel(eq)).toLowerCase();
             if (searchStr.indexOf(filterText) === -1) continue;
          }

          if (!byObject[objName]) {
            byObject[objName] = [];
          }
          byObject[objName].push(eq);
          matchCount++;
        }

        // Story 4.6 — AC 2 : 6 colonnes exactes et ordonnées : Piece | Nom | Ecart | Statut | Confiance | Raison.
        var html = '<table class="table table-bordered table-condensed" id="table_diagnostic" style="width:100%;table-layout:auto;">';
        html += '<thead><tr><th>{{Piece}}</th><th>{{Nom}}</th><th style="width:80px;">{{Ecart}}</th><th style="width:120px;">{{Statut}}</th><th style="width:100px;">{{Confiance}}</th><th>{{Raison}}</th></tr></thead>';
        html += '<tbody>';

        var objects = Object.keys(byObject).sort();
        for (var objIdx = 0; objIdx < objects.length; objIdx++) {
          var objName = objects[objIdx];
          var eqs = byObject[objName];

          for (var eqIdx = 0; eqIdx < eqs.length; eqIdx++) {
            var eq = eqs[eqIdx];
            var reasonDescription = getDiagnosticReasonLabel(eq);
            // Accordéon disponible pour TOUS les équipements in-scope (y compris Publié)
            var chevron = '<i class="fas fa-chevron-right diag-chevron" style="margin-right:6px;font-size:0.8em;color:#aaa;transition:transform 0.15s;"></i>';

            // Encode enriched data as JSON in data attribute (inclut traceability)
            var detailData = JSON.stringify({
              eq_id: eq.eq_id,
              eq_type_name: eq.eq_type_name || '',
              detail: eq.detail || '',
              remediation: eq.remediation || '',
              cause_label: eq.cause_label || '',
              cause_action: eq.cause_action || '',
              v1_limitation: eq.v1_limitation || false,
              unmatched_commands: eq.unmatched_commands || [],
              matched_commands: eq.matched_commands || [],
              detected_generic_types: eq.detected_generic_types || [],
              reason_code: eq.reason_code,
              status: eq.status,
              traceability: eq.traceability || {}
            });

            // Story 4.6 — AC 6 : data-eq-id sur chaque ligne pour le ciblage depuis la home.
            html += '<tr class="diag-expandable" style="cursor:pointer;" data-eq-id="' + eq.eq_id + '" data-detail=\'' + detailData.replace(/'/g, '&#39;') + '\'>';
            html += '<td style="vertical-align:middle;"><strong>' + objName + '</strong></td>';
            html += '<td style="white-space:nowrap;">' + chevron + eq.name + '</td>';
            // Story 4.6 — AC 2 : colonne Écart (nouvelle, avant Statut).
            html += '<td>' + getEcartBadge(eq.ecart) + '</td>';
            var partialSuffix = '';
            if (eq.status === 'Publié' && eq.unmatched_commands && eq.unmatched_commands.length > 0) {
              partialSuffix = ' <span class="text-muted" style="font-size:0.85em">(partiel)</span>';
            }
            html += '<td>' + getStatusLabel(eq.status) + partialSuffix + '</td>';
            html += '<td>' + getConfidenceLabel(eq.confidence) + '</td>';
            // Story 4.6 — AC 2 : Raison lisible (pas de reason_code interne exposé).
            html += '<td><span style="font-size:0.9em;">' + reasonDescription + '</span></td>';
            html += '</tr>';

            html += buildDetailRow(eq);
          }
        }

        if (matchCount === 0) {
           html += '<tr><td colspan="6" class="text-center"><i>{{Aucun résultat pour cette recherche}}</i></td></tr>';
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

      // Story 4.6 — AC 6 / AC 7 : ouverture ciblée depuis la home via badge Écart.
      // Si window.jeedom2haHomeDiagnosticTarget est présent, cibler l'équipement correspondant.
      var homeTarget = window.jeedom2haHomeDiagnosticTarget || null;
      window.jeedom2haHomeDiagnosticTarget = null; // consommer la cible une seule fois
      if (homeTarget && homeTarget.eq_id) {
        var targetEqId = String(homeTarget.eq_id);
        setTimeout(function() {
          var $container = $('#div_diagnosticTable');
          var $targetRow = $container.find('.diag-expandable[data-eq-id="' + targetEqId + '"]');
          if ($targetRow.length > 0) {
            // Scroll vers la ligne
            var rowTop = $targetRow.position() ? $targetRow.position().top : 0;
            var scrollPos = $container.scrollTop() + rowTop - 40;
            $container.scrollTop(Math.max(0, scrollPos));
            // Déplier la ligne (utilise l'accordéon existant)
            $targetRow.trigger('click');
            // Mise en évidence visuelle temporaire
            $targetRow.addClass('j2ha-diag-target-highlight');
            setTimeout(function() {
              $targetRow.removeClass('j2ha-diag-target-highlight');
            }, 2500);
          }
          // AC 7 : si la cible n'est pas trouvée, la modal reste ouverte en mode général sans erreur.
        }, 150);
      }

      $('#in_searchDiagnostic').off('keyup').on('keyup', function() {
         var val = $(this).val();
         $('#div_diagnosticTable').html(renderTable(val));
         // Re-bind accordion after re-render
         bindAccordion('#div_diagnosticTable');
      });    }
  });
});
