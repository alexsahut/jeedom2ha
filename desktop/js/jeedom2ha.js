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
  // Story 25.8 : compteur d'appels, pour qu'une fin de relecture enchaînée ne relise pas deux fois la santé du pont.
  window.jeedom2haBridgeRefreshes = (window.jeedom2haBridgeRefreshes || 0) + 1;
  // Front v2 (Lot 1) : le rafraîchissement périodique ne relance pas une lecture tant que la précédente n'est pas revenue.
  window.jeedom2haBridgeInflight = true;
  $.ajax({
    type: 'POST',
    url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    data: {action: 'getBridgeStatus'},
    dataType: 'json',
    complete: function() {
      window.jeedom2haBridgeInflight = false;
    },
    success: function(data) {
      if (data.state !== 'ok') {
        window.jeedom2haLastBridgeStatus = null;
        $('#span_healthBridge').removeClass().addClass('label label-danger').text('{{Erreur Jeedom}}');
        $('#span_healthMqtt').removeClass().addClass('label label-default').text('{{Inconnu}}');
        renderHaHealth(null);
        applyHAGating(null);
        notifyGuideStatus(null);
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
        $op.closest('.j2ha-health-item').show();
        renderHaHealth(r);
        applyHAGating(r);
        notifyGuideStatus(r);
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

      // 3. Dernière relecture (front v2, Lot 1 : date courte, et résultat fusionné quand la dernière opération est la relecture)
      var _fusion = relectureFusionOf(r);
      if (r.derniere_synchro_terminee) {
        $sync.text(_fusion.text);
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
      $opMsg.text(relectureMessage(_opObj.message, ''));
      // « Dernière opération » reste dans le DOM ; elle est masquée quand elle répète « Dernière relecture ».
      if (_fusion.fused) {
        $op.closest('.j2ha-health-item').hide();
      } else {
        $op.closest('.j2ha-health-item').show();
      }
      renderHaHealth(r);
      applyHAGating(r);
      notifyGuideStatus(r);
    },
    error: function() {
      window.jeedom2haLastBridgeStatus = null;
      $('#span_healthBridge').removeClass().addClass('label label-danger').text('{{Erreur de communication}}');
      $('#span_healthMqtt').removeClass().addClass('label label-default').text('{{Inconnu}}');
      renderHaHealth(null);
      applyHAGating(null);
      notifyGuideStatus(null);
    }
  });
}

/* Front v2 (Lot 1) — glossaire 3.2 : « relecture » à la place des messages « synchronisation » du démon (textes du démon
 * inchangés ; seul l'affichage les traduit). Un message inconnu est affiché tel quel. */
var J2HA_RELECTURE_MESSAGES = {
  'Synchronisation terminée.': '{{Relecture terminée.}}',
  'Synchronisation terminée avec avertissements.': '{{Relecture terminée avec avertissements.}}',
  'Synchronisation échouée.': '{{Relecture échouée.}}',
  'Synchronisation échouée — erreur inattendue.': '{{Relecture échouée : erreur inattendue.}}',
};

function relectureMessage(message, fallback) {
  if (typeof message === 'string' && message !== '') {
    return Object.prototype.hasOwnProperty.call(J2HA_RELECTURE_MESSAGES, message) ? J2HA_RELECTURE_MESSAGES[message] : message;
  }
  return fallback;
}

/* Date de « Dernière relecture » et fusion avec « Dernière opération » (module du guide ; repli : date seule). */
function relectureFusionOf(r) {
  if (typeof Jeedom2haGuide !== 'undefined' && Jeedom2haGuide && typeof Jeedom2haGuide.relectureFusion === 'function') {
    return Jeedom2haGuide.relectureFusion(r);
  }
  var d = new Date(r && r.derniere_synchro_terminee);
  if (!r || !r.derniere_synchro_terminee || isNaN(d.getTime())) return {text: '', fused: false};
  var dateStr = ('0' + d.getDate()).slice(-2) + '/' + ('0' + (d.getMonth() + 1)).slice(-2) + ' ' + ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
  return {text: dateStr, fused: false};
}

/* Item « Home Assistant » de la barre d'état (E0) : visible seulement si le démon fournit `ha.birth_seen_at` (Lot 3). */
function renderHaHealth(r) {
  var $item = $('#div_healthHa');
  if ($item.length === 0) return;
  var bar = (typeof Jeedom2haGuide !== 'undefined' && Jeedom2haGuide && typeof Jeedom2haGuide.haBarItem === 'function')
    ? Jeedom2haGuide.haBarItem(r)
    : {visible: false};
  if (!bar.visible) {
    $item.hide();
    return;
  }
  // Front v2 (Lot 6, retour de démo) : « Vu à HH:MM » en vert ; sinon « Non confirmé » en gris (état neutre, jamais une alerte :
  // Home Assistant qui tourne déjà ne se signale pas de nouveau), avec l'explication en infobulle.
  $('#span_healthHa').removeClass().addClass('label j2ha-health-value ' + (bar.seen ? 'label-success' : 'label-default')).text(bar.text)
    .attr('title', bar.seen ? '' : Jeedom2haGuide.HA_TOOLTIP);
  if (bar.seen) $('#span_healthHa').removeAttr('title');
  $item.show();
}

/* Le guide de démarrage suit l'état du pont (instance créée au chargement de la page, absente sinon). */
function notifyGuideStatus(r) {
  if (typeof window !== 'undefined' && window.Jeedom2haGuideInstance && typeof window.Jeedom2haGuideInstance.onStatus === 'function') {
    window.Jeedom2haGuideInstance.onStatus(r);
  }
}

/* Story 25.3 (AC6) : une action terminée (succès ou échec) peut avoir changé les états ; la page principale
 * relit alors les chiffres (sans refresh, coalescée) — voir jeedom2ha_overview.js. Sans effet si la page B est absente. */
function notifyStatesChanged() {
  if (typeof window !== 'undefined' && typeof window.j2haNotifyStatesChanged === 'function') {
    window.j2haNotifyStatesChanged();
  }
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
    syncRoomExclusionHints('{{Une opération est déjà en cours.}}');
    return;
  }
  var available = r ? isHABridgeAvailable(r) : false;
  var $reason = $('#div_haGatingReason');

  if (available) {
    $haActions.not('[data-ha-state-blocked="1"]').prop('disabled', false).removeClass('j2ha-ha-gated');
    $haActions.filter('[data-ha-state-blocked="1"]').removeClass('j2ha-ha-gated');
    $reason.hide();
    syncRoomExclusionHints('');
  } else {
    $haActions.prop('disabled', true).addClass('j2ha-ha-gated');
    var reason = '{{Démon ou MQTT indisponible — actions Home Assistant bloquées.}}';
    if (r && !r.daemon) {
      reason = '{{Démon arrêté — actions Home Assistant bloquées.}}';
    } else if (r) {
      reason = '{{MQTT déconnecté — actions Home Assistant bloquées.}}';
    }
    $reason.text(reason).show();
    syncRoomExclusionHints(reason);
  }
}

/* Story 25.8 (AC11) : les entrées « Exclure la pièce… » suivent le gating des actions Home Assistant ; grisées, elles disent pourquoi
 * (relecture en cours, ou la raison du gating du pont), comme « Relire Jeedom ». */
function syncRoomExclusionHints(reason) {
  $('.j2ha-room-exclude').each(function() {
    var $item = $(this);
    if ($item.prop('disabled') && reason) {
      $item.attr('title', reason);
    } else {
      $item.removeAttr('title');
    }
  });
}

function confirmTopologyRescan(onConfirm, onCancel) {
  // Front v2 (Lot 6, E9) : le texte annonce les réglages en attente lus dans la copie des états en mémoire (aucune requête).
  var dlg = j2haExclusionsModule() ? j2haExclusionsModule().rescanDialog(j2haPageSnapshot()) : {
    title: '{{Relire Jeedom}}',
    lines: ['{{Le plugin relit vos équipements et met Home Assistant à jour.}}', '{{Rien n\'est supprimé sans que vous l\'ayez exclu.}}'],
    confirmLabel: '{{Relire Jeedom}}',
  };
  confirmHaPublishAction(escapeRoomExclusionText(dlg.title), j2haDialogMessage(dlg.lines), dlg.confirmLabel, onConfirm, onCancel);
}

/* Front v2 (Lot 6) — module de l'exclusion unifiée et des confirmations chiffrées (jeedom2ha_exclusions.js), absent = repli. */
function j2haExclusionsModule() {
  if (typeof window !== 'undefined' && window.Jeedom2haExclusions) return window.Jeedom2haExclusions;
  return typeof Jeedom2haExclusions !== 'undefined' ? Jeedom2haExclusions : null;
}

/* Copie des états déjà en mémoire (page du plugin) : les confirmations y lisent leurs nombres, sans requête de plus. */
function j2haPageSnapshot() {
  var page = typeof window !== 'undefined' ? window.Jeedom2haOverviewPage : null;
  return page && typeof page.snapshot === 'function' ? page.snapshot() : null;
}

/* Lignes de texte brut (noms libres compris) rendues en paragraphes échappés. */
function j2haDialogMessage(lines) {
  return (lines || []).map(function(line) {
    return '<p>' + escapeRoomExclusionText(line) + '</p>';
  }).join('');
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
    // Preuve terrain 25.8 (AC8) : le thème du cœur force `.modal-footer .btn.bootbox-accept` en vert (`!important`), quelle que
    // soit la classe btn-*. Une confirmation qui retire de Home Assistant garde le rouge du thème : on retire au bouton la seule
    // classe `bootbox-accept` (aucun CSS ajouté, aucun composant du cœur restylé, la clé `confirm` et son rappel inchangés).
    if (confirmClass === 'btn-danger' && dialog && typeof dialog.find === 'function') {
      dialog.find('.modal-footer .btn-danger.bootbox-accept').removeClass('bootbox-accept');
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

function triggerTopologyRescan($button, snapshot, owner, chain) {
  if (window.jeedom2haRescanOwner !== owner) return;
  // Story 25.8 : `chain` (facultatif) = { onComplete(failed) } — relecture enchaînée après une exclusion de pièce, même chemin.
  var outcome = {failed: false};
  $button.html('<i class="fas fa-spinner fa-spin"></i> {{Relecture en cours…}}');
  $('[data-ha-action]').not('[data-ha-pending="1"]').prop('disabled', true);
  $.ajax({
    type: 'POST', url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    data: {action: 'scanTopology'}, dataType: 'json',
    timeout: (typeof Jeedom2haActionBudget !== 'undefined' && Jeedom2haActionBudget.CLIENT_TIMEOUT_MS) || 90000,
    success: function(data) {
      var result = data && data.result;
      outcome.failed = !(data && data.state === 'ok' && result && result.status === 'ok' && result.operation_result !== 'echec');
      if (data.state !== 'ok') {
        $('#div_alert').showAlert({message: (typeof result === 'string' && result) || '{{Une opération est déjà en cours ou la relecture a échoué.}}', level: 'danger'});
        return;
      }
      if (result && result.status === 'ok') {
        if (result.operation_result === 'succes') {
          $('#div_alert').showAlert({message: relectureMessage(result.operation_message, '{{Relecture terminée.}}'), level: 'success'});
        } else if (result.operation_result === 'echec') {
          $('#div_alert').showAlert({message: relectureMessage(result.operation_message, '{{Relecture échouée.}}'), level: 'danger'});
        } else if (typeof result.operation_result === 'string') {
          $('#div_alert').showAlert({message: relectureMessage(result.operation_message, '{{Relecture terminée avec avertissements.}}'), level: 'warning'});
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
      outcome.failed = true;
      $('#div_alert').showAlert({message: '{{Erreur de communication : vérifiez « Dernière relecture » avant de relancer.}}', level: 'danger'});
    },
    complete: function() {
      releaseTopologyRescanReservation($button, snapshot, owner);
      notifyStatesChanged();
      if (chain && typeof chain.onComplete === 'function') {
        chain.onComplete(outcome.failed);
      }
    },
  });
}

/* Story 25.8 (D3, D4) — exclusion d'une pièce depuis la surface (carte de la page principale, détail de pièce) :
 *   1. confirmation chiffrée (annuler n'écrit rien) ; 2. `saveRoomExclusion` (échec : message, AUCUNE relecture) ;
 *   3. drapeaux « pièce exclue » mis à jour en mémoire depuis `excluded_objects` ; 4. relecture EXPLICITE par le chemin de
 *   « Relire Jeedom » (`triggerTopologyRescan` : même réservation, même budget client, mêmes messages), sans sa confirmation ;
 *   5. fin de relecture (succès ou échec) : `refreshBridgeStatus()` et relecture des états.
 * Pendant 1 à 5, « Relire Jeedom » et toutes les entrées [data-ha-action] (dont l'exclusion des autres pièces) sont réservées. */
function escapeRoomExclusionText(value) {
  return $('<span></span>').text(String(value)).html();
}

function requestRoomExclusion(roomId, roomName, excluded, $trigger, $returnFocus) {
  var page = window.Jeedom2haOverviewPage;
  var $rescan = $('#bt_rescanTopology');
  if (!page || typeof page.exclusionDialog !== 'function' || $rescan.length === 0) return;
  if (window.jeedom2haRescanInProgress === true || ($trigger && $trigger.prop('disabled'))) return;
  var snapshot = setHaActionPendingState($rescan, '{{Confirmation en cours…}}');
  var owner = {};
  window.jeedom2haRescanInProgress = true;
  window.jeedom2haRescanOwner = owner;
  applyHAGating(window.jeedom2haLastBridgeStatus || null);
  var giveBackFocus = function() {
    // `$returnFocus` peut être une fonction : le détail d'une pièce est redessiné après une écriture réussie.
    var $target = typeof $returnFocus === 'function' ? $returnFocus() : $returnFocus;
    if ($target && $target.length) {
      $target.focus();
    }
  };
  var dialog = page.exclusionDialog(roomId, roomName, excluded);
  var message = dialog.lines.map(function(line) {
    return '<p>' + escapeRoomExclusionText(line) + '</p>';
  }).join('');
  confirmHaPublishAction(
    escapeRoomExclusionText(dialog.title),
    message,
    dialog.confirmLabel,
    function() {
      updateHaActionPendingLabel($rescan, '{{Enregistrement…}}');
      var failSave = function(text) {
        $('#div_alert').showAlert({message: text, level: 'danger'});
        releaseTopologyRescanReservation($rescan, snapshot, owner);
        giveBackFocus();
      };
      $.ajax({
        type: 'POST', url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
        data: {action: 'saveRoomExclusion', objectId: String(roomId), excluded: excluded ? '1' : '0'}, dataType: 'json',
        timeout: 20000,
        success: function(data) {
          var result = data && data.state === 'ok' ? data.result : null;
          if (!result || !Array.isArray(result.excluded_objects)) {
            failSave((data && typeof data.result === 'string' && data.result) || '{{L\'exclusion de la pièce n\'a pas été enregistrée.}}');
            return;
          }
          page.setExcludedObjects(result.excluded_objects);
          var refreshesBefore = window.jeedom2haBridgeRefreshes || 0;
          triggerTopologyRescan($rescan, snapshot, owner, {
            onComplete: function(failed) {
              if (failed) {
                $('#div_alert').showAlert({message: '{{Relancez « Relire Jeedom » pour retirer les entités.}}', level: 'warning'});
              }
              // La relecture relit déjà la santé du pont dans la plupart des issues ; sinon, c'est fait ici (une seule fois).
              if ((window.jeedom2haBridgeRefreshes || 0) === refreshesBefore) {
                refreshBridgeStatus();
              }
              giveBackFocus();
            },
          });
        },
        error: function() {
          failSave('{{Erreur de communication : l\'exclusion de la pièce n\'a pas pu être confirmée. Vérifiez l\'état de la pièce avant de recommencer.}}');
        },
      });
    },
    function() {
      releaseTopologyRescanReservation($rescan, snapshot, owner);
      giveBackFocus();
    },
    dialog.danger ? 'btn-danger' : 'btn-primary'
  );
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
      notifyStatesChanged();
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
      notifyStatesChanged();
    },
  });
}

/* Front v2 (Lot 1) — étape 4 du guide : « Publier dans Home Assistant » = la relecture existante (scanTopology), même
 * réservation que « Relire Jeedom », même budget client, mêmes messages, SANS la confirmation qui parle de retirer des
 * entités : le guide ne propose ce bouton que tant que rien n'a encore été publié. `onDone(failed)` à la fin.
 * Retourne false si une opération est déjà en cours (rien n'est envoyé). */
function publishFromGuide(onDone) {
  var $rescan = $('#bt_rescanTopology');
  if ($rescan.length === 0 || window.jeedom2haRescanInProgress === true) return false;
  var snapshot = setHaActionPendingState($rescan, '{{Relecture en cours…}}');
  var owner = {};
  window.jeedom2haRescanInProgress = true;
  window.jeedom2haRescanOwner = owner;
  triggerTopologyRescan($rescan, snapshot, owner, {
    onComplete: function(failed) {
      if (typeof onDone === 'function') onDone(failed);
    },
  });
  return true;
}

/* Front v2 (Lot 1) — barre d'état relue toutes les 30 s tant que l'onglet est visible (lecture getBridgeStatus seule).
 * S'arrête seul quand la page du plugin n'est plus affichée (navigation Jeedom sans rechargement). */
var J2HA_BRIDGE_REFRESH_MS = 30000;
function startBridgeStatusAutoRefresh() {
  if (typeof window === 'undefined' || typeof window.setInterval !== 'function') return;
  if (window.jeedom2haBridgeTimer) window.clearInterval(window.jeedom2haBridgeTimer);
  window.jeedom2haBridgeTimer = window.setInterval(function() {
    if ($('#span_healthBridge').length === 0) {
      window.clearInterval(window.jeedom2haBridgeTimer);
      window.jeedom2haBridgeTimer = null;
      return;
    }
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
    if (window.jeedom2haBridgeInflight === true) return;
    refreshBridgeStatus();
  }, J2HA_BRIDGE_REFRESH_MS);
}

/* Front v2 (Lot 1) — démarrage guidé (E1), « Vérifier l'installation… » (E7), ligne d'aide et nouvelles entrées du menu. */
function setupGuide() {
  $('#j2ha_v2_helpline').html('<strong>{{Relire Jeedom}}</strong> : {{j\'ai changé quelque chose dans Jeedom.}} <strong>{{Republier tout}}</strong> : {{Home Assistant a perdu ses appareils.}}');
  if (typeof Jeedom2haGuide === 'undefined' || !Jeedom2haGuide || typeof Jeedom2haGuide.createGuide !== 'function') return;
  if ($('#j2ha_v2_guide').length === 0) return;
  var storage = null;
  try { storage = window.localStorage; } catch (e) { storage = null; }
  var openConfig = function() {
    var $conf = $('.eqLogicAction[data-action="gotoPluginConf"]').first();
    if ($conf.length) $conf.trigger('click');
  };
  var guide = Jeedom2haGuide.createGuide({
    $: $,
    bootbox: typeof bootbox !== 'undefined' ? bootbox : null,
    storage: storage,
    rooms: window.j2haRoomsTree || [],
    // Une vue de travail ouverte par l'adresse (#j2ha-vue=…) n'est jamais recouverte par le guide.
    canAutoShow: function() {
      return !(window.location && typeof window.location.hash === 'string' && window.location.hash.indexOf('j2ha-vue=') !== -1);
    },
    actions: {
      openConfig: openConfig,
      openChoose: function() {
        var $choose = $('#bt_j2haChoosePublished');
        if ($choose.length && !$choose.prop('hidden')) $choose.trigger('click');
        else openConfig();
      },
      openFilter: function(key) {
        var view = window.Jeedom2haWorkviewInstance;
        if (view && typeof view.open === 'function' && view.open({filter: key}) !== false) return;
        var page = window.Jeedom2haOverviewPage;
        if (page && typeof page.setFilterExact === 'function') page.setFilterExact(key);
      },
      publish: publishFromGuide,
      rescan: function() { $('#bt_rescanTopology').trigger('click'); },
    },
  });
  window.Jeedom2haGuideInstance = guide;
  var page = window.Jeedom2haOverviewPage;
  if (page && typeof page.subscribe === 'function' && typeof page.snapshot === 'function') {
    page.subscribe(function() { guide.onSnapshot(page.snapshot()); });
    guide.onSnapshot(page.snapshot());
  }
  if (window.jeedom2haLastBridgeStatus !== undefined) guide.onStatus(window.jeedom2haLastBridgeStatus);
  $('#bt_j2haOpenGuide').on('click', function() { guide.open(); });
  $('#bt_j2haCheckInstall').on('click', function() { guide.openCheck(); });
}

/* Front v2 (Lot 6, E6) — « Choisir ce qui est publié… » : exécution d'un lot de changements d'exclusion.
 * Écritures EXISTANTES, corps inchangés, une à la fois et dans l'ordre (`saveFilteringConfig` avec la `confidencePolicy` courante,
 * `saveRoomExclusion`, `savePublicationOverride` / `revertPublicationOverride`), puis UNE seule relecture par le chemin de
 * « Relire Jeedom » (`triggerTopologyRescan` : même réservation, même budget client, mêmes messages). Une écriture refusée arrête
 * le lot : message chiffré, AUCUNE relecture (comme l'exclusion d'une pièce). `isUndo` : écritures inverses du bandeau « Annuler ».
 * Retourne false si rien n'est envoyé (opération en cours, pont indisponible). */
var J2HA_EXCLUSION_TOAST_MS = 10000;

function j2haExclusionWriteError(write, data) {
  if (!data || data.state !== 'ok') {
    return (data && typeof data.result === 'string' && data.result) || '{{Le changement n\'a pas été enregistré.}}';
  }
  if (write.kind === 'plugins') {
    return data.result && data.result.saved === true ? null : '{{Les plugins exclus n\'ont pas été enregistrés.}}';
  }
  if (write.kind === 'room') {
    return data.result && Array.isArray(data.result.excluded_objects) ? null : '{{L\'exclusion de la pièce n\'a pas été enregistrée.}}';
  }
  var M = (typeof window !== 'undefined' && window.Jeedom2haMappingOverride) || (typeof Jeedom2haMappingOverride !== 'undefined' ? Jeedom2haMappingOverride : null);
  return M && typeof M.readPublicationRequestError === 'function' ? M.readPublicationRequestError(data) : null;
}

function applyExclusionChanges(writes, info, isUndo) {
  var $rescan = $('#bt_rescanTopology');
  if (!writes || writes.length === 0 || $rescan.length === 0) return false;
  if (window.jeedom2haRescanInProgress === true) {
    $('#div_alert').showAlert({message: '{{Une opération est déjà en cours : réessayez dans un instant.}}', level: 'warning'});
    return false;
  }
  if (!isHABridgeAvailable(window.jeedom2haLastBridgeStatus || null)) {
    $('#div_alert').showAlert({message: '{{Démon ou MQTT indisponible : les changements ne peuvent pas être appliqués maintenant.}}', level: 'warning'});
    return false;
  }
  var snapshot = setHaActionPendingState($rescan, '{{Enregistrement…}}');
  var owner = {};
  window.jeedom2haRescanInProgress = true;
  window.jeedom2haRescanOwner = owner;
  applyHAGating(window.jeedom2haLastBridgeStatus || null);
  var page = window.Jeedom2haOverviewPage;
  var done = 0;
  var excludedObjects = null;
  var syncRooms = function() {
    if (excludedObjects && page && typeof page.setExcludedObjects === 'function') page.setExcludedObjects(excludedObjects);
  };
  var fail = function(text) {
    syncRooms();
    var counted = done + ' {{sur}} ' + writes.length + ' ' + (writes.length > 1 ? '{{changements enregistrés.}}' : '{{changement enregistré.}}');
    $('#div_alert').showAlert({message: text + ' ' + counted + ' ' + '{{Rien n\'a été relu : vérifiez vos choix, puis lancez « Relire Jeedom ».}}', level: 'danger'});
    releaseTopologyRescanReservation($rescan, snapshot, owner);
    notifyStatesChanged();
  };
  var finish = function() {
    syncRooms();
    var refreshesBefore = window.jeedom2haBridgeRefreshes || 0;
    triggerTopologyRescan($rescan, snapshot, owner, {
      onComplete: function(failed) {
        if (failed) {
          $('#div_alert').showAlert({message: '{{Changements enregistrés, mais la relecture a échoué : relancez « Relire Jeedom ».}}', level: 'warning'});
        } else {
          showExclusionToast(info, isUndo);
        }
        if ((window.jeedom2haBridgeRefreshes || 0) === refreshesBefore) refreshBridgeStatus();
      },
    });
  };
  var next = function() {
    if (done === writes.length) { finish(); return; }
    var write = writes[done];
    $.ajax({
      type: 'POST', url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php', data: write.data, dataType: 'json', timeout: 20000,
      success: function(data) {
        var error = j2haExclusionWriteError(write, data);
        if (error) { fail(error); return; }
        if (write.kind === 'room') excludedObjects = data.result.excluded_objects;
        if (write.kind === 'plugins') window.j2haExcludedPlugins = write.data.excludedPlugins;
        done += 1;
        next();
      },
      error: function() {
        fail('{{Erreur de communication : le changement n\'a pas pu être confirmé.}}');
      },
    });
  };
  next();
  return true;
}

/* Bandeau de résultat (règle 3 : « Annuler » pendant 10 s). L'annulation rejoue les écritures inverses, puis une relecture. */
function showExclusionToast(info, isUndo) {
  var X = j2haExclusionsModule();
  var $toast = $('#j2ha_v2_toast');
  if (!X || $toast.length === 0 || !info) return;
  if (window.jeedom2haExclusionToastTimer) window.clearTimeout(window.jeedom2haExclusionToastTimer);
  $toast.empty();
  var text = isUndo ? '{{Changement annulé.}}' : X.resultText(info.diff) + '.';
  // Revue Codex (#394) : les équipements que « Annuler » ne rétablirait pas exactement sont nommés par leur nombre.
  var blocked = info.diff && info.diff.undoBlocked ? info.diff.undoBlocked.length : 0;
  var note = !isUndo && blocked > 0 ? ' ' + X.undoBlockedText(blocked) + '.' : '';
  $toast.append($('<span></span>').text('✔ ' + text + ' ' + '{{Home Assistant est à jour.}}' + note));
  var policy = window.j2haConfidencePolicy || 'sure_probable';
  var inverse = isUndo ? [] : X.inverseWrites(info.model, info.changes, policy);
  if (inverse.length > 0) {
    var $undo = $('<button type="button" class="j2ha-v2-excl-undo"></button>').text('{{Annuler}}');
    $undo.on('click', function() {
      if (applyExclusionChanges(inverse, info, true) !== false) {
        window.clearTimeout(window.jeedom2haExclusionToastTimer);
        $toast.empty();
      }
    });
    $toast.append($undo);
  }
  window.jeedom2haExclusionToastTimer = window.setTimeout(function() { $toast.empty(); }, J2HA_EXCLUSION_TOAST_MS);
}

/* Ouvre le panneau (une seule instance), positionné sur une pièce ou un équipement si demandé. */
function openChoosePublished(opts) {
  var X = j2haExclusionsModule();
  if (!X || typeof X.createPanel !== 'function' || typeof bootbox === 'undefined') return false;
  if (!window.Jeedom2haExclusionsPanel) {
    window.Jeedom2haExclusionsPanel = X.createPanel({
      $: $,
      bootbox: bootbox,
      rooms: function() { return window.j2haRoomsTree || []; },
      snapshot: j2haPageSnapshot,
      excludedPlugins: function() { return window.j2haExcludedPlugins || ''; },
      confidencePolicy: function() { return window.j2haConfidencePolicy || 'sure_probable'; },
      pluginNames: window.j2haPluginNames || {},
      apply: function(writes, info) { return applyExclusionChanges(writes, info, false); },
    });
  }
  return window.Jeedom2haExclusionsPanel.open(opts || {});
}

/* Points d'ouverture : bouton de la page, entrée du menu « ⋯ » de la barre d'état, menu « ⋯ » d'une carte (avec « Republier la
 * pièce », confirmation chiffrée, même route que la vue de la pièce). */
function setupChoosePublished() {
  var $choose = $('#bt_j2haChoosePublished');
  $choose.prop('hidden', false).removeAttr('hidden');
  $choose.on('click', function() { openChoosePublished({}); });
  var $sep = $('#j2ha_moreMenu .j2ha-menu-sep').first();
  if ($sep.length && typeof $sep.before === 'function' && $('#bt_j2haChooseMenu').length === 0) {
    var $item = $('<button type="button" id="bt_j2haChooseMenu" class="j2ha-menu-item" role="menuitem"></button>')
      .append('<i class="fas fa-check-square"></i>').append($('<span></span>').text('{{Choisir ce qui est publié…}}'));
    $item.on('click', function() {
      // Le menu se referme par son propre bouton (même chemin qu'un second clic sur « ⋯ »).
      var $wrap = $item.closest('.j2ha-menu-wrap');
      if ($wrap.hasClass('j2ha-menu-open')) $wrap.find('.j2ha-menu-toggle').first().trigger('click');
      openChoosePublished({});
    });
    $sep.before($('<li role="none"></li>').append($item));
  }
  var cardOf = function(el) { return $(el).closest('.j2ha-room-card'); };
  var roomIdOf = function(el) { return parseInt(cardOf(el).attr('data-object_id'), 10); };
  var roomNameOf = function(id) {
    var room = (window.j2haRoomsTree || []).filter(function(r) { return r && r.object_id === id; })[0];
    return room ? String(room.object_name) : '';
  };
  $('#j2ha_roomCards .j2ha-room-choose').on('click', function(event) {
    if (event && event.stopPropagation) event.stopPropagation();
    openChoosePublished({roomId: roomIdOf(this)});
  });
  $('#j2ha_roomCards .j2ha-card-republish').on('click', function(event) {
    if (event && event.stopPropagation) event.stopPropagation();
    var $button = $(this);
    if ($button.prop('disabled')) return;
    var id = roomIdOf(this);
    var X = j2haExclusionsModule();
    var dlg = X ? X.republishRoomDialog(j2haPageSnapshot(), window.j2haRoomsTree || [], id, roomNameOf(id)) : {
      title: '{{Republier la pièce}}', lines: ['{{Renvoie les équipements publiés de cette pièce à Home Assistant, sans relire Jeedom.}}'], confirmLabel: '{{Republier la pièce}}',
    };
    var reservation = setHaActionPendingState($button, '{{Confirmation en cours…}}');
    var $toggle = cardOf(this).find('.j2ha-menu-toggle').first();
    confirmHaPublishAction(
      escapeRoomExclusionText(dlg.title),
      j2haDialogMessage(dlg.lines),
      dlg.confirmLabel,
      function() { triggerPublierAction($button, 'piece', [id], reservation); },
      function() {
        restoreHaActionPendingState($button, reservation);
        if ($toggle.length) $toggle.focus();
      }
    );
  });
}

// Confirmation forte (bouton rouge) ; `onCancel` libère le bouton réservé à l'ouverture (R1-C).
function confirmHaSupprimerAction(title, message, confirmLabel, onConfirm, onCancel) {
  confirmHaPublishAction(title, message, confirmLabel, onConfirm, onCancel, 'btn-danger');
}

$(function() {
  // Barre d'état lue au chargement, puis toutes les 30 s tant que l'onglet est visible (front v2, Lot 1).
  refreshBridgeStatus();
  startBridgeStatusAutoRefresh();
  setupGuide();
  setupChoosePublished();

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
    // Front v2 (Lot 6, E9) : bouton chiffré par le nombre d'équipements publiés (copie des états en mémoire, aucune requête).
    var dlg = j2haExclusionsModule() ? j2haExclusionsModule().republishAllDialog(j2haPageSnapshot()) : {
      title: '{{Republier tout}}', lines: ['{{Renvoie les équipements publiés à Home Assistant, sans relire Jeedom.}}'], confirmLabel: '{{Republier tout}}',
    };
    confirmHaPublishAction(
      escapeRoomExclusionText(dlg.title),
      j2haDialogMessage(dlg.lines),
      dlg.confirmLabel,
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
    // Front v2 (Lot 6, E9) : équipements et entités présents dans Home Assistant comptés depuis la copie des états en mémoire ;
    // bouton rouge « Supprimer N entités ». L'identifiant `data-ha-action="supprimer-recreer"` est conservé (gate).
    var dlg = j2haExclusionsModule() ? j2haExclusionsModule().deleteAllDialog(j2haPageSnapshot()) : {
      title: '{{Supprimer tout de Home Assistant}}',
      lines: ['{{Nombre d\'entités inconnu pour l\'instant : la lecture des états n\'est pas disponible.}}', '{{L\'historique, les tableaux de bord et les automatisations qui les utilisent seront touchés.}}', '{{Rien n\'est recréé automatiquement : utilisez « Republier tout » pour les remettre. Cette action ne s\'annule pas.}}'],
      confirmLabel: '{{Supprimer tout}}',
    };
    confirmHaSupprimerAction(
      escapeRoomExclusionText(dlg.title),
      j2haDialogMessage(dlg.lines),
      dlg.confirmLabel,
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

  // Export de décision — Story 24.2 (lecture seule : identifiants seulement, aucun nom)
  $('#bt_exportDecision').on('click', function () {
    var $btn    = $(this);
    var $status = $('#span_decisionExportResult');
    $btn.prop('disabled', true);
    $status.removeClass('label-success label-danger').addClass('label').text('{{Export en cours…}}').show();

    $.ajax({
      type:     'POST',
      url:      'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
      data:     { action: 'getDecisionExport' },
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
        anchor.download = 'jeedom2ha-decision-export-' + today + '.json';
        anchor.click();
        URL.revokeObjectURL(url);
        $status.removeClass('label').addClass('label label-success').text('{{Export de décision téléchargé}}');
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
