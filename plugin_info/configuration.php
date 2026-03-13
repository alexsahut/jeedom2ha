<?php
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

require_once dirname(__FILE__) . '/../../../core/php/core.inc.php';
include_file('core', 'authentification', 'php');
if (!isConnect()) {
  include_file('desktop', '404', 'php');
  die();
}
?>

<!-- Bandeau d'auto-détection MQTT -->
<div class="alert" id="div_mqtt_autodetect_status" style="display:none;"></div>

<form class="form-horizontal">
  <fieldset>
    <legend><i class="fas fa-network-wired"></i> {{Configuration MQTT}}</legend>

    <div class="form-group">
      <label class="col-md-4 control-label">{{Hôte MQTT}}
        <sup><i class="fas fa-question-circle tooltips" title="{{Adresse IP ou nom d'hôte du broker MQTT}}"></i></sup>
      </label>
      <div class="col-md-4">
        <input class="configKey form-control" data-l1key="mqttHost" placeholder="ex: 192.168.1.10"/>
      </div>
    </div>

    <div class="form-group">
      <label class="col-md-4 control-label">{{Port MQTT}}
        <sup><i class="fas fa-question-circle tooltips" title="{{Port du broker MQTT (1883 par défaut, 8883 pour TLS)}}"></i></sup>
      </label>
      <div class="col-md-4">
        <input type="number" class="configKey form-control" data-l1key="mqttPort" placeholder="1883"/>
      </div>
    </div>

    <div class="form-group">
      <label class="col-md-4 control-label">{{Utilisateur MQTT}}</label>
      <div class="col-md-4">
        <input class="configKey form-control" data-l1key="mqttUser" autocomplete="username"/>
      </div>
    </div>

    <div class="form-group">
      <label class="col-md-4 control-label">{{Mot de passe MQTT}}</label>
      <div class="col-md-4">
        <input type="password" class="form-control" data-l1key="mqttPassword" id="in_mqttPassword"
               autocomplete="current-password" placeholder="{{Laisser vide pour conserver l'actuel}}"/>
        <span id="span_mqttPasswordStatus" class="help-block" style="display:none; color: #2ecc71;">
          <i class="fas fa-lock"></i> {{Mot de passe déjà configuré}}
        </span>
      </div>
    </div>

    <div class="form-group">
      <label class="col-md-4 control-label">{{Activer TLS}}
        <sup><i class="fas fa-question-circle tooltips" title="{{Activer le chiffrement TLS pour la connexion au broker}}"></i></sup>
      </label>
      <div class="col-md-4">
        <input type="checkbox" class="configKey" data-l1key="mqttTls"/>
      </div>
    </div>

    <div class="form-group">
      <label class="col-md-4 control-label">{{Vérifier le certificat}}
        <sup><i class="fas fa-question-circle tooltips" title="{{Valider le certificat du broker. Décocher pour les certificats auto-signés.}}"></i></sup>
      </label>
      <div class="col-md-4">
        <input type="checkbox" class="configKey" data-l1key="mqttTlsVerify" checked/>
      </div>
    </div>

    <div class="form-group">
      <div class="col-md-offset-4 col-md-4">
        <button type="button" class="btn btn-default" id="bt_testMqttConnection">
          <i class="fas fa-plug"></i> {{Tester la connexion}}
        </button>
        <span id="span_mqttTestResult" style="margin-left:10px;display:none;"></span>
      </div>
    </div>
  </fieldset>
</form>

<script>
// JS inline dans configuration.php — NE PAS déplacer dans desktop/js/jeedom2ha.js
// Ce fichier n'est pas chargé sur la vue de configuration plugin.

$(function() {
  // ---- Auto-détection MQTT Manager au chargement ----
  $.ajax({
    type: 'POST',
    url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    data: {action: 'getMqttConfig'},
    dataType: 'json',
    error: function() { /* Best-effort — l'absence de résultat ne bloque pas le formulaire manuel */ },
    success: function(data) {
      if (data.state !== 'ok') return;
      var result = data.result;

      // Affichage de l'indicateur "Déjà configuré"
      if (result.has_password) {
        $('#span_mqttPasswordStatus').show();
      } else {
        $('#span_mqttPasswordStatus').hide();
      }

      if (result.source === 'mqtt2') {
        // Pré-remplir les champs vides depuis MQTT Manager
        if ($('.configKey[data-l1key=mqttHost]').val() === '') {
          $('.configKey[data-l1key=mqttHost]').val(result.host);
          $('.configKey[data-l1key=mqttPort]').val(result.port);
          $('.configKey[data-l1key=mqttUser]').val(result.user);
        }
        // Sécurité : le mot de passe n'est JAMAIS chargé dans le DOM (result.password est inexistant)
        $('#div_mqtt_autodetect_status')
          .removeClass().addClass('alert alert-info')
          .html('<i class="fas fa-check-circle"></i> {{MQTT Manager détecté — configuration pré-remplie}}')
          .show();
      } else if (result.source === 'manual') {
        // Sécurité : le mot de passe n'est JAMAIS chargé dans le DOM
        $('#div_mqtt_autodetect_status')
          .removeClass().addClass('alert alert-info')
          .html('<i class="fas fa-user-cog"></i> {{Configuration manuelle}}')
          .show();
      } else if (result.source === 'none') {
        // Pas de config manuelle stockée — afficher le guidage
        if ($('.configKey[data-l1key=mqttHost]').val() === '') {
          $('#div_mqtt_autodetect_status')
            .removeClass().addClass('alert alert-warning')
            .html('<i class="fas fa-exclamation-triangle"></i> {{Aucun broker MQTT détecté. Installez MQTT Manager ou saisissez les paramètres manuellement ci-dessous.}}')
            .show();
        }
      }
    }
  });

  // ---- Gestion de la sauvegarde du mot de passe ----
  // On ajoute configKey seulement si le champ n'est pas vide pour éviter d'écraser le secret par du vide
  $('#in_mqttPassword').on('keyup change', function() {
    if ($(this).val() !== '') {
      $(this).addClass('configKey');
    } else {
      $(this).removeClass('configKey');
    }
  });

  // ---- Test de connexion MQTT ----
  $('#bt_testMqttConnection').on('click', function() {
    var $btn = $(this);
    var $result = $('#span_mqttTestResult');
    $btn.prop('disabled', true);
    $result.removeClass('label-success label-danger label-warning label')
      .text('{{Test en cours...}}').show();
    $.ajax({
      type: 'POST',
      url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
      data: {
        action: 'testMqttConnection',
        host:       $('.configKey[data-l1key=mqttHost]').val(),
        port:       $('.configKey[data-l1key=mqttPort]').val() || '1883',
        user:       $('.configKey[data-l1key=mqttUser]').val(),
        password:   $('#in_mqttPassword').val(), // On envoie ce qui est saisi (peut être vide)
        tls:        $('.configKey[data-l1key=mqttTls]').is(':checked') ? '1' : '0',
        tls_verify: $('.configKey[data-l1key=mqttTlsVerify]').is(':checked') ? '1' : '0'
      },
      dataType: 'json',
      success: function(data) {
        $btn.prop('disabled', false);
        if (data.state !== 'ok') {
          $result.addClass('label label-danger')
            .text(data.result || '{{Le démon ne répond pas}}').show();
          return;
        }
        var r = data.result;
        if (r.status === 'ok') {
          $result.addClass('label label-success').text(r.message).show();
        } else {
          $result.addClass('label label-danger').text(r.message).show();
        }
      },
      error: function(request, status, error) {
        $btn.prop('disabled', false);
        // HTTP status code visible pour diagnostic (ex: HTTP 401, HTTP 500, HTTP 0)
        var httpCode = request.status;
        var msg;
        if (status === 'timeout') {
          msg = '{{Délai d\'attente dépassé (timeout AJAX)}}';
        } else {
          msg = '{{Erreur de communication avec Jeedom}} (HTTP ' + httpCode + ' / ' + status + ')';
        }
        $result.addClass('label label-danger').text(msg).show();
      }
    });
  });
});
</script>
