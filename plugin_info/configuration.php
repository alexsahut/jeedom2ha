<?php
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

require_once dirname(__FILE__) . '/../../../core/php/core.inc.php';
include_file('core', 'authentification', 'php');
if (!isConnect()) {
  include_file('desktop', '404', 'php');
  die();
}

// Story 25.9 — « Plugins exclus » : liste à cocher des plugins qui ont au moins un équipement (hors jeedom2ha), noms affichés lus
// dans le cœur (repli sur l'identifiant). Aides pures partagées avec la page principale (25.7) : réutilisées sans modification.
require_once dirname(__FILE__) . '/../desktop/php/jeedom2ha_overview_helpers.php';
require_once dirname(__FILE__) . '/../core/php/jeedom2ha_excluded_plugins.php';
$j2haPresentPlugins = array();
foreach (eqLogic::all() as $j2haEq) {
  $j2haPluginId = j2ha_plugin_id($j2haEq->getEqType_name());
  if ($j2haPluginId !== '' && $j2haPluginId !== 'jeedom2ha') {
    $j2haPresentPlugins[$j2haPluginId] = true;
  }
}
$j2haPluginNames = j2ha_plugin_names(array_keys($j2haPresentPlugins), function ($pluginId) {
  return plugin::byId($pluginId)->getName();
});
$j2haExcludedPluginsValue = (string) config::byKey('excludedPlugins', 'jeedom2ha', '');
$j2haPluginList = jeedom2ha_build_excluded_plugins_list($j2haPluginNames, $j2haExcludedPluginsValue);
$j2haExcludedRoomsCount = jeedom2ha_excluded_rooms_count();
?>

<!-- Bandeau d'auto-détection MQTT -->
<div class="alert" id="div_mqtt_autodetect_status" style="display:none;"></div>

<!-- Actions d'import / reset -->
<div style="margin-bottom:12px;">
  <button type="button" class="btn btn-info btn-sm" id="bt_importMqttManager">
    <i class="fas fa-download"></i> {{Récupérer depuis MQTT Manager}}
  </button>
  &nbsp;
  <a href="#" id="lnk_resetMqttForm" style="font-size:0.85em; color: #999;">
    <i class="fas fa-times"></i> {{Réinitialiser le formulaire}}
  </a>
</div>

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
        <input type="checkbox" class="configKey" data-l1key="mqttTlsVerify"/>
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

<form class="form-horizontal">
  <fieldset>
    <legend><i class="fas fa-filter"></i> {{Filtrage &amp; Publication}}</legend>

    <div class="form-group">
      <label class="col-md-4 control-label" id="lbl_excludedPlugins">{{Plugins exclus}}
        <sup><i class="fas fa-question-circle tooltips" title="{{Les équipements des plugins cochés ne sont pas publiés dans Home Assistant.}}"></i></sup>
      </label>
      <div class="col-md-6">
        <?php /* Champ porteur masqué : lu par « Sauvegarder » du cœur et par « Appliquer… » ; tenu à jour par les cases (JS ci-dessous). */ ?>
        <input type="hidden" class="configKey" data-l1key="excludedPlugins" value="<?php echo jeedom2ha_html_attr($j2haExcludedPluginsValue); ?>"/>
        <?php echo jeedom2ha_render_excluded_plugins_checklist($j2haPluginList); ?>
      </div>
    </div>

    <div class="form-group">
      <div class="col-md-offset-4 col-md-6">
        <p class="form-control-static">
          {{Pièces exclues : elles se règlent depuis la page du plugin (menu « ⋯ » d'une carte de pièce, ou détail de la pièce).}}
          <a href="index.php?v=d&amp;m=jeedom2ha&amp;p=jeedom2ha">{{Ouvrir la page du plugin}}</a>
        </p>
        <p class="help-block">{{Pièces exclues : sauf équipements exposés à HomeKit (actifs), qui restent publiés. L'exclusion de l'équipement lui-même est toujours respectée.}}</p>
        <?php if ($j2haExcludedRoomsCount > 0) { ?>
        <p class="help-block"><?php echo (int) $j2haExcludedRoomsCount . ' ' . ($j2haExcludedRoomsCount > 1 ? '{{pièces exclues}}' : '{{pièce exclue}}'); ?></p>
        <?php } ?>
      </div>
    </div>

    <div class="form-group">
      <label class="col-md-4 control-label">{{Politique de publication}}
        <sup><i class="fas fa-question-circle tooltips" title="{{Niveau de confiance minimum pour publier un équipement}}"></i></sup>
      </label>
      <div class="col-md-4">
        <select class="configKey form-control" data-l1key="confidencePolicy">
          <option value="sure_probable">{{Publier les équipements sûrs et probables (recommandé)}}</option>
          <option value="sure_only">{{Publier uniquement les équipements sûrs}}</option>
        </select>
      </div>
    </div>

    <div class="form-group">
      <div class="col-md-offset-4 col-md-4">
        <button type="button" id="bt_applyAndRescan" class="btn btn-primary">
          <i class="fas fa-sync"></i> {{Appliquer les filtres et rescanner}}
        </button>
        <span id="span_rescanResult" class="label" style="display:none; margin-left:10px;"></span>
      </div>
    </div>
  </fieldset>
</form>

<script>
// JS inline dans configuration.php — NE PAS déplacer dans desktop/js/jeedom2ha.js
// Ce fichier n'est pas chargé sur la vue de configuration plugin.

/* j2ha-excluded-plugins:begin */
// Story 25.9 (D2) — valeur de `excludedPlugins` écrite par les cases à cocher : MÊME clé, MÊME format (CSV d'identifiants).
// Rien n'a changé : la valeur chargée est rendue VERBATIM (aucune normalisation, Q4). Sinon : les identifiants déjà présents gardent
// leur ordre, un identifiant coché en plus est ajouté EN FIN, un identifiant décoché est retiré (toutes ses occurrences) ; joints par
// « , » sans espace ; liste vide = chaîne vide.
function j2haComputeExcludedPlugins(initialCsv, initiallyChecked, nowChecked) {
  var before = initiallyChecked.slice().sort().join('\n');
  var after = nowChecked.slice().sort().join('\n');
  if (before === after) {
    return initialCsv;
  }
  var tokens = String(initialCsv).split(',').map(function(token) { return token.trim(); }).filter(function(token) { return token !== ''; });
  var kept = tokens.filter(function(token) { return initiallyChecked.indexOf(token) === -1 || nowChecked.indexOf(token) !== -1; });
  nowChecked.forEach(function(id) {
    if (initiallyChecked.indexOf(id) === -1 && kept.indexOf(id) === -1) {
      kept.push(id);
    }
  });
  return kept.join(',');
}
/* j2ha-excluded-plugins:end */

// Valeur courante : lue dans les cases (jamais dans le champ porteur, que le cœur remplit de façon asynchrone).
function j2haExcludedPluginsValue() {
  var initialChecked = [];
  var nowChecked = [];
  $('#div_excludedPluginsList input.j2ha-excluded-plugin').each(function() {
    var $box = $(this);
    if ($box.attr('data-initial') === '1') {
      initialChecked.push($box.val());
    }
    if ($box.is(':checked')) {
      nowChecked.push($box.val());
    }
  });
  var $carrier = $('.configKey[data-l1key=excludedPlugins]');
  return j2haComputeExcludedPlugins($carrier.attr('value') || '', initialChecked, nowChecked);
}

// Résumé des plugins cochés, au-dessus de la liste (même texte que le rendu PHP) : ce qui est coché reste visible sans défiler.
function j2haRefreshExcludedPluginsSummary() {
  var names = [];
  $('#div_excludedPluginsList input.j2ha-excluded-plugin:checked').each(function() {
    names.push($(this).closest('label').find('span').first().text());
  });
  $('#p_excludedPluginsSummary').text(names.length === 0 ? '{{Aucun plugin coché.}}' : '{{Plugins cochés}} (' + names.length + ') : ' + names.join(', ') + '.');
}

$(function() {
  // ---- Plugins exclus : le champ porteur masqué (configKey) suit les cases (Q3) ----
  // « Sauvegarder » du cœur et « Appliquer… » écrivent donc la même clé au même format. Le cœur remplit les `configKey` après le
  // chargement de la page : les cases, rendues cochées côté serveur depuis la même valeur, sont resynchronisées après ce remplissage
  // (événement change du champ porteur) sans jamais perdre un identifiant de la valeur chargée.
  var $excludedPlugins = $('.configKey[data-l1key=excludedPlugins]');
  $('#div_excludedPluginsList').on('change', 'input.j2ha-excluded-plugin', function() {
    $excludedPlugins.val(j2haExcludedPluginsValue());
    j2haRefreshExcludedPluginsSummary();
  });
  $excludedPlugins.on('change', function() {
    // La valeur remplie par le cœur devient la valeur de référence (« chargée ») : cases, état initial et valeur d'origine.
    var loaded = String($(this).val() || '');
    var wanted = loaded.split(',').map(function(token) { return token.trim(); });
    $(this).attr('value', loaded);
    $('#div_excludedPluginsList input.j2ha-excluded-plugin').each(function() {
      var isExcluded = wanted.indexOf($(this).val()) !== -1;
      $(this).prop('checked', isExcluded).attr('data-initial', isExcluded ? '1' : '0');
    });
    j2haRefreshExcludedPluginsSummary();
  });

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
          if (result.tls) {
            $('.configKey[data-l1key=mqttTls]').prop('checked', true);
          }
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

  // ---- Import forcé depuis MQTT Manager ----
  $('#bt_importMqttManager').on('click', function() {
    var $btn = $(this);
    var $status = $('#div_mqtt_autodetect_status');
    $btn.prop('disabled', true);
    $status.removeClass()
      .addClass('alert alert-info')
      .html('<i class="fas fa-spinner fa-spin"></i> {{Import en cours...}}')
      .show();
    $.ajax({
      type: 'POST',
      url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
      data: {action: 'forceMqttManagerImport'},
      dataType: 'json',
      success: function(data) {
        $btn.prop('disabled', false);
        if (data.state !== 'ok') {
          $status.removeClass().addClass('alert alert-warning')
            .html('<i class="fas fa-exclamation-triangle"></i> ' + (data.result || '{{Erreur de communication}}'))
            .show();
          return;
        }
        var r = data.result;
        if (r.status === 'ok') {
          $('.configKey[data-l1key=mqttHost]').val(r.host);
          $('.configKey[data-l1key=mqttPort]').val(r.port);
          $('.configKey[data-l1key=mqttUser]').val(r.user);
          $('.configKey[data-l1key=mqttTls]').prop('checked', r.tls === true);
          if (r.has_password) {
            $('#span_mqttPasswordStatus').show();
            $('#in_mqttPassword').val('').removeClass('configKey');
          }
          $status.removeClass().addClass('alert alert-success')
            .html('<i class="fas fa-check-circle"></i> {{Configuration importée depuis MQTT Manager}}')
            .show();
        } else {
          $status.removeClass().addClass('alert alert-warning')
            .html('<i class="fas fa-exclamation-triangle"></i> ' + r.message)
            .show();
        }
      },
      error: function(request) {
        $btn.prop('disabled', false);
        $status.removeClass().addClass('alert alert-warning')
          .html('<i class="fas fa-exclamation-triangle"></i> {{Erreur de communication}} (HTTP ' + request.status + ')')
          .show();
      }
    });
  });

  // ---- Réinitialiser le formulaire (front uniquement, sans sauvegarder) ----
  $('#lnk_resetMqttForm').on('click', function(e) {
    e.preventDefault();
    $('.configKey[data-l1key=mqttHost]').val('');
    $('.configKey[data-l1key=mqttPort]').val('');
    $('.configKey[data-l1key=mqttUser]').val('');
    $('#in_mqttPassword').val('').removeClass('configKey');
    $('.configKey[data-l1key=mqttTls]').prop('checked', false);
    $('.configKey[data-l1key=mqttTlsVerify]').prop('checked', false);
    $('#span_mqttPasswordStatus').hide();
    $('#div_mqtt_autodetect_status').hide();
  });

  // ---- Appliquer et Rescanner : save → scan chaîné (Story 4.3) ----
  // JS inline dans configuration.php — NE PAS déplacer dans desktop/js/jeedom2ha.js
  $('#bt_applyAndRescan').on('click', function() {
    var $btn = $(this);
    var $status = $('#span_rescanResult');
    $btn.prop('disabled', true);
    $status.removeClass('label-success label-danger label-warning')
           .text('{{Sauvegarde en cours...}}').show();

    // Étape 1 : sauvegarder les champs de filtrage explicitement
    $.ajax({
      type: 'POST',
      url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
      data: {
        action:           'saveFilteringConfig',
        excludedPlugins:  j2haExcludedPluginsValue(),
        confidencePolicy: $('.configKey[data-l1key=confidencePolicy]').val()
      },
      dataType: 'json',
      timeout: 10000,
      success: function(saveData) {
        if (saveData.state !== 'ok') {
          $btn.prop('disabled', false);
          $status.addClass('label-danger')
                 .text(saveData.result || '{{Erreur lors de la sauvegarde}}');
          return;
        }
        // Étape 2 : lancer le rescan avec la config fraîchement sauvegardée
        $status.text('{{Rescan en cours...}}');
        $.ajax({
          type: 'POST',
          url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
          data: {action: 'scanTopology'},
          dataType: 'json',
          timeout: 90000, // Story A1 : > budget relais R=60 s + sonde (cf. jeedom2ha_action_budget.js)
          success: function(scanData) {
            $btn.prop('disabled', false);
            if (scanData.state !== 'ok') {
              $status.addClass('label-danger')
                     .text(scanData.result || '{{Erreur lors du rescan}}');
              return;
            }
            var r = scanData.result || {};
            if (r.status !== 'ok' || r.operation_result !== 'succes') {
              $status.addClass('label-warning').text(r.message || r.operation_message || '{{Résultat inconnu, relire Dernière opération}}');
              return;
            }
            var summary = (r.payload && r.payload.mapping_summary) ? r.payload.mapping_summary : {};
            var published = Object.keys(summary).reduce(function(total, key) {
              if (!key.endsWith('_published')) {
                return total;
              }
              var numericValue = Number(summary[key]);
              return isFinite(numericValue) ? total + numericValue : total;
            }, 0);
            $status.addClass('label-success')
                   .text('{{Appliqué & Rescan terminé}} — ' + published + ' {{équipement(s) publié(s)}}');
          },
          error: function() {
            $btn.prop('disabled', false);
            $status.addClass('label-danger').text('{{Erreur de communication lors du rescan}}');
          }
        });
      },
      error: function() {
        $btn.prop('disabled', false);
        $status.addClass('label-danger').text('{{Erreur de communication lors de la sauvegarde}}');
      }
    });
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
