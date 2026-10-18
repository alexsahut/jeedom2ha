/* SPDX-License-Identifier: AGPL-3.0-or-later
 * This file is part of Jeedom2HA.
 *
 * Jeedom2HA is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Jeedom2HA is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with Jeedom2HA. If not, see <https://www.gnu.org/licenses/>.
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

      // 1. Démon
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
      var _opObj = Jeedom2haMappingOverride.readOperationSnapshot(r.derniere_operation_resultat);
      switch (_opObj.resultat) {
        case 'succes':
          $op.removeClass().addClass('label label-success').text('{{Succès}}');
          break;
        case 'partiel':
          // Problème de configuration -> NON ROUGE (Warning orange)
          $op.removeClass().addClass('label label-warning').addClass('j2ha-op-warn').text('{{Partiel}}');
          break;
        case 'echec':
          // Problème de configuration complet -> NON ROUGE (Warning orange)
          $op.removeClass().addClass('label label-warning').addClass('j2ha-op-warn').text('{{Échec}}');
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
  // R1-C : un bouton dont l'action est en cours (`data-ha-pending`) garde son état tant que
  // l'action n'est pas terminée ; un bouton grisé par l'état de l'arbre (`data-ha-state-blocked`,
  // R1-B) n'est jamais réactivé par la seule santé du pont.
  var $haActions = $('[data-ha-action]').not('[data-ha-pending="1"]');
  if (window.jeedom2haRescanInProgress === true) {
    $haActions.prop('disabled', true);
    return;
  }
  var available = r ? isHABridgeAvailable(r) : false;
  var $reason = $('#div_haGatingReason');

  if (available) {
    $haActions.not('[data-ha-state-blocked="1"]').prop('disabled', false).removeClass('j2ha-ha-gated');
    $haActions.filter('[data-ha-state-blocked="1"]').removeClass('j2ha-ha-gated');
    $reason.hide();
  } else {
    $haActions.prop('disabled', true).addClass('j2ha-ha-gated');
    var reason = '{{Démon ou MQTT indisponible — actions Home Assistant bloquées.}}';
    if (r && !r.daemon) {
      reason = '{{Daemon arrêté — actions Home Assistant bloquées.}}';
    } else if (r) {
      reason = '{{MQTT déconnecté — actions Home Assistant bloquées.}}';
    }
    $reason.text(reason).show();
  }
}

function confirmTopologyRescan(onConfirm, onCancel) {
  confirmHaPublishAction(
    '{{Relire Jeedom}}',
    '{{Une relecture complète peut publier ou retirer des entités Home Assistant et applique les réglages enregistrés. Confirmer ?}}',
    '{{Relire}}',
    onConfirm,
    onCancel
  );
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
  $button.attr('data-ha-pending', '1');
  $button.prop('disabled', true);
  $button.html('<i class="fas fa-spinner fa-spin"></i> ' + pendingLabel);
  return snapshot;
}

// Le bouton est déjà réservé (confirmation ouverte) : seul le libellé change quand l'action part.
function updateHaActionPendingLabel($button, pendingLabel) {
  $button.html('<i class="fas fa-spinner fa-spin"></i> ' + pendingLabel);
}

function restoreHaActionPendingState($button, snapshot) {
  if (!$button || $button.length === 0) {
    return;
  }
  if (snapshot && typeof snapshot.html === 'string') {
    $button.html(snapshot.html);
  }
  $button.prop('disabled', snapshot && snapshot.disabled === true);
  $button.removeAttr('data-ha-pending');
  // Le bouton reprend l'état du pont : il a pu changer pendant l'action.
  if (typeof applyHAGating === 'function') {
    applyHAGating(window.jeedom2haLastBridgeStatus || null);
  }
  // Un bouton grisé par l'état de l'arbre (R1-B) le reste, quel que soit le snapshot.
  if ($button.attr('data-ha-state-blocked') === '1') {
    $button.prop('disabled', true);
  }
}

function showHaActionFeedback(payload) {
  $('#div_alert').showAlert({
    message: buildHaActionUserMessage(payload),
    level: getHaActionAlertLevel(payload),
  });
}

function releaseTopologyRescanReservation($button, snapshot, owner) {
  if (window.jeedom2haRescanOwner !== owner) {
    return;
  }
  window.jeedom2haRescanOwner = null;
  window.jeedom2haRescanInProgress = false;
  restoreHaActionPendingState($button, snapshot);
  applyHAGating(window.jeedom2haLastBridgeStatus || null);
}

function confirmHaPublishAction(title, message, confirmLabel, onConfirm, onCancel, confirmClass) {
  if (typeof bootbox !== 'undefined' && bootbox && typeof bootbox.dialog === 'function') {
    var confirmed = false;
    var cancelled = false;
    var cancelConfirmation = function() {
      if (confirmed || cancelled) {
        return;
      }
      cancelled = true;
      if (typeof onCancel === 'function') {
        onCancel();
      }
    };
    var dialog = bootbox.dialog({
      title: title,
      message: '<div>' + message + '</div>',
      onEscape: typeof onCancel === 'function' ? cancelConfirmation : undefined,
      buttons: {
        cancel: {
          label: '{{Annuler}}',
          className: 'btn-default',
          callback: cancelConfirmation,
        },
        confirm: {
          label: confirmLabel,
          className: confirmClass || 'btn-primary',
          callback: function() {
            confirmed = true;
            onConfirm();
          },
        },
      },
    });
    if (typeof onCancel === 'function' && dialog && typeof dialog.on === 'function') {
      dialog.on('hidden.bs.modal', cancelConfirmation);
    }
    return;
  }
  if (window.confirm(message)) onConfirm();
  else if (typeof onCancel === 'function') onCancel();
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
    // Story 19.6 (AC2) — délai fixe, indépendant de N, au-dessus du pire des deux
    // chemins du relais PHP (voir desktop/js/jeedom2ha_action_budget.js, CLIENT_TIMEOUT_MS).
    // Repli à 90000 si le module n'est pas chargé (revue de code, corrections bloc C).
    timeout: (typeof Jeedom2haActionBudget !== 'undefined' && Jeedom2haActionBudget.CLIENT_TIMEOUT_MS)
      || 90000,
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

function triggerTopologyRescan($button, snapshot, owner) {
  if (window.jeedom2haRescanOwner !== owner) return;
  $button.html('<i class="fas fa-spinner fa-spin"></i> {{Relecture en cours…}}');
  $('[data-ha-action]').not('[data-ha-pending="1"]').prop('disabled', true);
  $.ajax({
    type: 'POST', url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    data: {action: 'scanTopology'}, dataType: 'json',
    timeout: (typeof Jeedom2haActionBudget !== 'undefined' && Jeedom2haActionBudget.CLIENT_TIMEOUT_MS) || 90000,
    success: function(data) {
      var result = data && data.result;
      if (data.state !== 'ok') {
        $('#div_alert').showAlert({message: (typeof result === 'string' && result) || '{{Une opération est déjà en cours ou la relecture a échoué.}}', level: 'danger'});
        return;
      }
      if (result && result.status === 'ok') {
        if (result.operation_result === 'succes') {
          $('#div_alert').showAlert({message: result.operation_message || '{{Synchronisation terminée.}}', level: 'success'});
        } else if (result.operation_result === 'echec') {
          $('#div_alert').showAlert({message: result.operation_message || '{{Synchronisation échouée.}}', level: 'danger'});
        } else if (typeof result.operation_result === 'string') {
          $('#div_alert').showAlert({message: result.operation_message || '{{Synchronisation terminée avec avertissements.}}', level: 'warning'});
        } else {
          $('#div_alert').showAlert({message: '{{Résultat inconnu, relire Dernière opération.}}', level: 'warning'});
        }
        refreshBridgeStatus();
        return;
      }
      $('#div_alert').showAlert({message: (result && (result.message || result.operation_message)) || '{{Une opération est déjà en cours ou la relecture a échoué.}}', level: 'danger'});
      if (result && typeof result.operation_result === 'string') {
        refreshBridgeStatus();
      }
    },
    error: function() {
      $('#div_alert').showAlert({message: '{{Erreur de communication : relire Dernière synchro avant de relancer.}}', level: 'danger'});
    },
    complete: function() {
      releaseTopologyRescanReservation($button, snapshot, owner);
    },
  });
}

function triggerPublierAction($button, portee, selection, reservation) {
  var pendingState = reservation || setHaActionPendingState($button, '{{En cours...}}');
  if (reservation) {
    updateHaActionPendingLabel($button, '{{En cours...}}');
  }
  executeHaAction('publier', portee, selection, {
    onSuccess: function(payload) {
      showHaActionFeedback(payload);
      refreshBridgeStatus();
    },
    onError: function(message) {
      $('#div_alert').showAlert({message: message, level: 'danger'});
      // Story 22.2 (Q8 A) : un échec change aussi le dernier résultat affiché par le bandeau.
      refreshBridgeStatus();
    },
    onComplete: function() {
      restoreHaActionPendingState($button, pendingState);
    },
  });
}

function triggerSupprimerAction($button, portee, selection, reservation) {
  var pendingState = reservation || setHaActionPendingState($button, '{{Suppression...}}');
  if (reservation) {
    updateHaActionPendingLabel($button, '{{Suppression...}}');
  }
  executeHaAction('supprimer', portee, selection, {
    onSuccess: function(payload) {
      showHaActionFeedback(payload);
      refreshBridgeStatus();
    },
    onError: function(message) {
      $('#div_alert').showAlert({message: message, level: 'danger'});
      // Story 22.2 (Q8 A) : un échec change aussi le dernier résultat affiché par le bandeau.
      refreshBridgeStatus();
    },
    onComplete: function() {
      restoreHaActionPendingState($button, pendingState);
    },
  });
}

// Confirmation forte (bouton rouge) ; `onCancel` libère le bouton réservé à l'ouverture (R1-C).
function confirmHaSupprimerAction(title, message, confirmLabel, onConfirm, onCancel) {
  confirmHaPublishAction(title, message, confirmLabel, onConfirm, onCancel, 'btn-danger');
}

$(function() {
  // Refresh MQTT badge on page load (no auto-refresh)
  refreshBridgeStatus();

  $('#bt_rescanTopology').on('click', function() {
    var $button = $(this);
    if ($button.prop('disabled') || window.jeedom2haRescanInProgress === true) return;
    var snapshot = setHaActionPendingState($button, '{{Confirmation en cours…}}');
    var owner = {};
    window.jeedom2haRescanInProgress = true;
    window.jeedom2haRescanOwner = owner;
    confirmTopologyRescan(function() {
      triggerTopologyRescan($button, snapshot, owner);
    }, function() {
      releaseTopologyRescanReservation($button, snapshot, owner);
    });
  });

  // Story 20.3 (Q2b=A) — boutons globaux : confirmations sans nombre (aucune synthèse ne
  // fournit de décompte, et l'interface ne recalcule jamais une décision).
  $('.j2ha-ha-action[data-ha-action="republier"]').on('click', function(event) {
    event.preventDefault();
    var $button = $(this);
    if ($button.prop('disabled')) {
      return;
    }
    // R1-C : le bouton est réservé dès l'ouverture de la confirmation (pas deux boîtes).
    var reservation = setHaActionPendingState($button, '{{Confirmation en cours…}}');
    confirmHaPublishAction(
      '{{Republier dans Home Assistant}}',
      '{{Republier tous les équipements inclus ?}}',
      '{{Republier}}',
      function() {
        triggerPublierAction($button, 'global', ['all'], reservation);
      },
      function() {
        restoreHaActionPendingState($button, reservation);
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
    var reservation = setHaActionPendingState($button, '{{Confirmation en cours…}}');
    confirmHaSupprimerAction(
      '{{Supprimer de Home Assistant}}',
      '{{Supprimer de Home Assistant tout le parc publié ?}}'
        + '<br><br><strong>{{Attention}}</strong> : {{l\'historique, les dashboards, les automatisations et l\'entity_id liés à ces entités peuvent être impactés.}}'
        + '<br>{{Rien n\'est recréé automatiquement : utilisez « Republier » pour remettre les équipements dans Home Assistant.}}',
      '{{Supprimer}}',
      function() {
        triggerSupprimerAction($button, 'global', ['all'], reservation);
      },
      function() {
        restoreHaActionPendingState($button, reservation);
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
      timeout:  (typeof Jeedom2haActionBudget !== 'undefined' && Jeedom2haActionBudget.CLIENT_TIMEOUT_MS) || 90000,
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
