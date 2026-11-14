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
// Front v2 / Lot 4 (E8) — présence d'un plugin du cœur, LECTURE SEULE : plugin::byId lève une exception si le plugin n'est pas
// installé ; installé mais inactif ou état illisible = absent ici (le bouton ou la phrase qui en dépend n'est simplement pas affiché).
$j2haPluginActive = function ($pluginId) {
  try {
    $candidate = plugin::byId($pluginId);
    if (!is_object($candidate) || !method_exists($candidate, 'isActive')) {
      return false;
    }
    return intval($candidate->isActive()) === 1;
  } catch (Throwable $e) {
    return false;
  }
};
$j2haHasMqttManager = $j2haPluginActive('mqtt2');
$j2haHasHomekit = $j2haPluginActive('homebridge');
?>

<p id="p_j2haBackTop" style="margin-bottom:12px;">
  <a href="index.php?v=d&amp;m=jeedom2ha&amp;p=jeedom2ha"><i class="fas fa-arrow-left"></i> {{Retour à la page du plugin}}</a>
</p>

<!-- Bandeau d'auto-détection MQTT -->
<div class="alert" id="div_mqtt_autodetect_status" style="display:none;"></div>

<form class="form-horizontal">
  <fieldset>
    <legend><i class="fas fa-network-wired"></i> {{Connexion au broker MQTT}}</legend>
    <p class="help-block" id="p_mqttBrokerIntro">{{Indiquez le broker que Home Assistant utilise déjà : le broker MQTT est le serveur de messages que Home Assistant écoute aussi.}}</p>
    <p class="help-block" id="p_mqttOneInstance"><i class="fas fa-exclamation-triangle"></i> <strong>{{Une seule installation jeedom2ha par broker MQTT.}}</strong> {{Une deuxième installation branchée sur ce broker (box de test, sauvegarde restaurée ailleurs) retirerait les boutons de scénario de celle-ci, et inversement.}}</p>
    <p class="help-block" id="p_mqttSaveHint">{{Pour ce bloc, utilisez le bouton « Tester, enregistrer et redémarrer le démon » ci-dessous : le démon ne lit ces réglages qu'à son démarrage.}}</p>

    <?php if ($j2haHasMqttManager) { ?>
    <div class="form-group">
      <div class="col-md-offset-4 col-md-6">
        <button type="button" class="btn btn-info btn-sm" id="bt_importMqttManager">
          <i class="fas fa-download"></i> {{Récupérer depuis MQTT Manager}}
        </button>
        <p class="help-block">{{Remplace les réglages ci-dessous par ceux de MQTT Manager et les enregistre aussitôt. Une confirmation est demandée avant.}}</p>
      </div>
    </div>
    <?php } ?>

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
      <div class="col-md-offset-4 col-md-6">
        <button type="button" class="btn btn-primary" id="bt_mqttTestSaveRestart">
          <i class="fas fa-check"></i> {{Tester, enregistrer et redémarrer le démon}}
        </button>
        &nbsp;
        <a href="#" id="bt_testMqttConnection">{{Tester seulement}}</a>
        <ul id="ul_mqttGuidedSteps" class="list-unstyled" style="margin-top:10px;display:none;" aria-live="polite">
          <li data-step="test" data-state="pending"><i class="far fa-circle"></i> {{Connexion testée}}</li>
          <li data-step="save" data-state="pending"><i class="far fa-circle"></i> {{Réglages enregistrés}}</li>
          <li data-step="restart" data-state="pending"><i class="far fa-circle"></i> {{Démon redémarré}}</li>
        </ul>
        <div id="div_mqttTestResult" role="status" style="margin-top:6px;display:none;">
          <strong id="span_mqttTestResult"></strong>
          <span id="span_mqttTestRemedy" class="text-muted"></span>
        </div>
        <div id="div_mqttGuidedFallback" style="margin-top:6px;display:none;">
          <span id="span_mqttGuidedFallback"></span>
          <button type="button" class="btn btn-default btn-xs" id="bt_mqttGoToDaemon"><i class="fas fa-arrow-up"></i> {{Aller au bloc Démon}}</button>
        </div>
        <div id="div_mqttNoDaemon" style="margin-top:6px;display:none;">
          <a href="#" id="lnk_mqttSaveRestartWithoutTest">{{Enregistrer et redémarrer le démon sans tester}}</a>
        </div>
      </div>
    </div>
  </fieldset>
</form>

<form class="form-horizontal">
  <fieldset>
    <legend><i class="fas fa-filter"></i> {{Ce qui est publié}}</legend>

    <div class="form-group">
      <label class="col-md-4 control-label" id="lbl_excludedPlugins">{{Plugins exclus}}
        <sup><i class="fas fa-question-circle tooltips" title="{{Les équipements des plugins cochés ne sont pas publiés dans Home Assistant.}}"></i></sup>
      </label>
      <div class="col-md-6">
        <?php /* Champ porteur masqué : lu par « Sauvegarder » du cœur et par « Enregistrer et relire Jeedom » ; tenu à jour par les cases (JS ci-dessous). */ ?>
        <input type="hidden" class="configKey" data-l1key="excludedPlugins" value="<?php echo jeedom2ha_html_attr($j2haExcludedPluginsValue); ?>"/>
        <?php echo jeedom2ha_render_excluded_plugins_checklist($j2haPluginList); ?>
      </div>
    </div>

    <div class="form-group">
      <div class="col-md-offset-4 col-md-6">
        <p class="form-control-static">
          {{Pièces exclues : elles se règlent depuis la page du plugin (menu « ⋯ » d'une carte de pièce, ou détail de la pièce).}}
          {{Le panneau « Choisir ce qui est publié… » de la page du plugin règle aussi, au même endroit, les plugins, les pièces et les équipements.}}
          <a href="index.php?v=d&amp;m=jeedom2ha&amp;p=jeedom2ha">{{Ouvrir la page du plugin}}</a>
        </p>
        <?php if ($j2haHasHomekit) { ?>
        <p class="help-block" id="p_homekitRoomNote">{{Pièces exclues : sauf équipements exposés à HomeKit (actifs), qui restent publiés. L'exclusion de l'équipement lui-même est toujours respectée.}}</p>
        <?php } ?>
        <?php if ($j2haExcludedRoomsCount > 0) { ?>
        <p class="help-block"><?php echo (int) $j2haExcludedRoomsCount . ' ' . ($j2haExcludedRoomsCount > 1 ? '{{pièces exclues}}' : '{{pièce exclue}}'); ?></p>
        <?php } ?>
      </div>
    </div>

    <div class="form-group">
      <label class="col-md-4 control-label">{{En cas de doute sur un équipement}}
        <sup><i class="fas fa-question-circle tooltips" title="{{Que faire d'un équipement que le plugin ne reconnaît pas avec certitude}}"></i></sup>
      </label>
      <div class="col-md-6">
        <select class="configKey form-control" data-l1key="confidencePolicy">
          <option value="sure_probable">{{Publier quand même (recommandé)}}</option>
          <option value="sure_only">{{Ne publier que les équipements reconnus avec certitude}}</option>
        </select>
        <p class="help-block">{{Ce réglage ne concerne que les équipements reconnus avec un léger doute. Un équipement dont le nom contredit ses types Jeedom n'est pas un doute : il reste bloqué, et sa fiche dit comment faire.}}</p>
      </div>
    </div>

    <div class="form-group">
      <div class="col-md-offset-4 col-md-6">
        <button type="button" id="bt_applyAndRescan" class="btn btn-primary">
          <i class="fas fa-sync"></i> {{Enregistrer et relire Jeedom}}
        </button>
        <span id="span_rescanResult" class="label" style="display:none; margin-left:10px;"></span>
        <p class="help-block">{{Enregistre les plugins exclus et le réglage ci-dessus, puis relit Jeedom. N'enregistre pas la connexion au broker.}}</p>
        <p class="help-block" id="p_coreSaveHint">{{Le bouton « Sauvegarder » de Jeedom enregistre aussi ce bloc mais ne relit pas Jeedom : préférez le bouton bleu de chaque bloc.}}</p>
      </div>
    </div>
  </fieldset>
</form>

<details id="details_j2haAdvanced" style="margin-bottom:12px;">
  <summary>{{Avancé}}</summary>
  <p style="margin-top:8px;">
    <a href="#" id="lnk_resetMqttForm"><i class="fas fa-times"></i> {{Réinitialiser le formulaire}}</a>
    <span class="text-muted">{{Vide les champs du broker sur cette page, sans rien enregistrer.}}</span>
  </p>
</details>

<p class="help-block" id="p_cron5Note"><i class="fas fa-info-circle"></i> {{Dans le bloc « Fonctionnalités » de Jeedom, ne décochez pas cron5 : il maintient la publication à jour.}} {{Toutes les 5 minutes, il republie ce qui a changé sans relecture de votre part (scénario ou équipement activé ou désactivé, exclusion) ; décoché, ces changements attendent un « Relire Jeedom ».}}</p>

<p id="p_j2haBackBottom">
  <a href="index.php?v=d&amp;m=jeedom2ha&amp;p=jeedom2ha"><i class="fas fa-arrow-left"></i> {{Retour à la page du plugin}}</a>
</p>

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

/* j2ha-mqtt-test-messages:begin */
// Front v2 / Lot 4 (E8) — message en clair et remède par `error_code` du test de connexion (codes déjà renvoyés par le démon,
// /action/mqtt_test). Aucun texte ne reprend une valeur saisie : ni l'hôte, ni l'utilisateur, ni le mot de passe.
var J2HA_MQTT_TEST_MESSAGES = {
  host_unreachable: ['{{Ce nom ou cette adresse ne répond pas.}}', '{{Vérifiez l\'adresse du broker.}}'],
  port_refused: ['{{Le broker refuse la connexion sur ce port.}}', '{{1883 en général, 8883 avec TLS.}}'],
  auth_failed: ['{{Identifiant ou mot de passe refusé.}}', '{{Vérifiez l\'utilisateur MQTT créé pour Jeedom.}}'],
  tls_error: ['{{La connexion chiffrée a échoué.}}', '{{Décochez « Vérifier le certificat » pour un certificat auto-signé.}}'],
  timeout: ['{{Le broker n\'a pas répondu à temps.}}', '{{Vérifiez le réseau et le pare-feu.}}'],
  missing_host: ['{{Adresse manquante}}', ''],
  invalid_port: ['{{Port invalide}}', '']
};

// Contrôle local avant tout appel : mêmes règles que le démon (hôte non vide, port entier 1-65535 ; vide = 1883).
function j2haCheckMqttForm(host, port) {
  if (String(host || '').trim() === '') {
    return 'missing_host';
  }
  var raw = String(port === undefined || port === null ? '' : port).trim();
  if (raw === '') {
    return null;
  }
  if (!/^[0-9]+$/.test(raw) || Number(raw) < 1 || Number(raw) > 65535) {
    return 'invalid_port';
  }
  return null;
}

// Réponse ajax de testMqttConnection → { kind: 'ok' | 'failed' | 'no_daemon', code, message, remedy }.
function j2haDescribeMqttTest(data) {
  if (!data || data.state !== 'ok') {
    return { kind: 'no_daemon', code: null, message: '{{Le démon ne répond pas : le test de connexion passe par lui.}}', remedy: '{{Démarrez le démon ci-dessus, ou enregistrez sans tester.}}' };
  }
  var r = data.result || {};
  if (r.status === 'ok') {
    return { kind: 'ok', code: null, message: '{{Connexion réussie.}}', remedy: '' };
  }
  var known = Object.prototype.hasOwnProperty.call(J2HA_MQTT_TEST_MESSAGES, r.error_code) ? J2HA_MQTT_TEST_MESSAGES[r.error_code] : null;
  if (known) {
    return { kind: 'failed', code: r.error_code, message: known[0], remedy: known[1] };
  }
  return { kind: 'failed', code: r.error_code || 'unknown_error', message: '{{La connexion au broker a échoué.}}', remedy: (typeof r.message === 'string' && r.message) || '{{Consultez le journal du démon.}}' };
}

function j2haLocalMqttCheck(code) {
  return { kind: 'failed', code: code, message: J2HA_MQTT_TEST_MESSAGES[code][0], remedy: J2HA_MQTT_TEST_MESSAGES[code][1] };
}

// « Relecture terminée : N équipements publiés » (singulier pour 0 et 1).
function j2haRereadDoneLabel(published) {
  return '{{Relecture terminée}} : ' + published + ' ' + (published > 1 ? '{{équipements publiés}}' : '{{équipement publié}}');
}
// Valeurs enregistrées par la chaîne guidée : port vide → 1883, comme pour le test (sinon le démon lirait intval('') = 0).
// Copie superficielle : l'instantané d'origine n'est pas modifié.
function j2haNormalizeMqttConfiguration(configuration) {
  var out = {};
  Object.keys(configuration || {}).forEach(function(key) { out[key] = configuration[key]; });
  if (out.mqttPort === undefined || out.mqttPort === null || String(out.mqttPort).trim() === '') {
    out.mqttPort = '1883';
  }
  return out;
}
/* j2ha-mqtt-test-messages:end */

// Confirmation : même boîte que la page du plugin (bootbox du cœur), repli sur la confirmation du navigateur.
function j2haConfirm(title, message, confirmLabel, onConfirm) {
  if (typeof bootbox !== 'undefined' && bootbox && typeof bootbox.dialog === 'function') {
    bootbox.dialog({
      title: title,
      message: $('<p>').text(message),
      buttons: {
        cancel: { label: '{{Annuler}}', className: 'btn-default' },
        confirm: { label: confirmLabel, className: 'btn-primary', callback: function() { onConfirm(); } }
      }
    });
    return;
  }
  if (window.confirm(message)) onConfirm();
}

// Valeurs du broker lues dans le formulaire. Le mot de passe saisi part seulement dans la requête de test (comme avant) :
// jamais affiché, jamais écrit dans la console ni dans un message.
function j2haMqttFormParams() {
  return {
    action: 'testMqttConnection',
    host:       $('.configKey[data-l1key=mqttHost]').val(),
    port:       $('.configKey[data-l1key=mqttPort]').val() || '1883',
    user:       $('.configKey[data-l1key=mqttUser]').val(),
    password:   $('#in_mqttPassword').val(), // On envoie ce qui est saisi (peut être vide : le secret stocké est utilisé)
    tls:        $('.configKey[data-l1key=mqttTls]').is(':checked') ? '1' : '0',
    tls_verify: $('.configKey[data-l1key=mqttTlsVerify]').is(':checked') ? '1' : '0'
  };
}

function j2haShowMqttOutcome(outcome) {
  var $result = $('#span_mqttTestResult');
  $result.removeClass('text-success text-danger text-warning')
    .addClass(outcome.kind === 'ok' ? 'text-success' : (outcome.kind === 'no_daemon' ? 'text-warning' : 'text-danger'))
    .text(outcome.message);
  $('#span_mqttTestRemedy').text(outcome.remedy ? ' ' + outcome.remedy : '');
  $('#div_mqttTestResult').attr('data-code', outcome.code || '').show();
  $('#div_mqttNoDaemon').toggle(outcome.kind === 'no_daemon');
}

// Test seul : testMqttConnection existant, aucune écriture. `snapshot` (facultatif) : valeurs figées au clic de la chaîne guidée.
function j2haTestMqtt(onOutcome, snapshot) {
  var params = snapshot ? snapshot.test : j2haMqttFormParams();
  var rawPort = snapshot ? snapshot.rawPort : $('.configKey[data-l1key=mqttPort]').val();
  var localCode = j2haCheckMqttForm(params.host, rawPort);
  if (localCode) {
    onOutcome(j2haLocalMqttCheck(localCode));
    return;
  }
  $.ajax({
    type: 'POST',
    url: 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    data: params,
    dataType: 'json',
    success: function(data) {
      onOutcome(j2haDescribeMqttTest(data));
    },
    error: function(request, status) {
      if (status === 'timeout') {
        onOutcome({ kind: 'failed', code: 'ajax_timeout', message: '{{Délai d\'attente dépassé (timeout AJAX)}}', remedy: '' });
        return;
      }
      // HTTP status code visible pour diagnostic (ex: HTTP 401, HTTP 500, HTTP 0)
      onOutcome({ kind: 'failed', code: 'ajax_error', message: '{{Erreur de communication avec Jeedom}} (HTTP ' + request.status + ' / ' + status + ')', remedy: '' });
    }
  });
}

// ---- Front v2 / Lot 4 : « Tester, enregistrer et redémarrer le démon » ----
// Même enchaînement que le bouton ▶ du bloc Démon du cœur (Jeedom 4.4 et 4.5, desktop/modal/plugin.deamon.php, .bt_startDeamon) :
// enregistrement de la configuration du plugin, puis jeedom.plugin.deamonStart({id, forceRestart: 1}), puis rafraîchissement
// du bloc Démon. L'enregistrement passe par jeedom.config.save avec les valeurs `.configKey` du conteneur de configuration,
// exactement comme jeeFrontEnd.plugin.savePluginConfig (desktop/js/plugin.js), mais avec un retour d'erreur pour arrêter la
// chaîne. Aucune action ajax du plugin n'est ajoutée. API absente ou en échec : repli « Redémarrez le démon ci-dessus ».
var J2HA_PLUGIN_ID = 'jeedom2ha';
var J2HA_STEP_ICONS = {
  pending: 'far fa-circle',
  running: 'fas fa-spinner fa-spin',
  done: 'fas fa-check-circle text-success',
  failed: 'fas fa-times-circle text-danger',
  skipped: 'fas fa-minus-circle text-muted'
};

function j2haSetStep(step, state) {
  $('#ul_mqttGuidedSteps li[data-step=' + step + ']').attr('data-state', state)
    .find('i').first().attr('class', J2HA_STEP_ICONS[state] || J2HA_STEP_ICONS.pending);
}

function j2haShowDaemonFallback(message) {
  $('#span_mqttGuidedFallback').text(message);
  $('#div_mqttGuidedFallback').show();
}

function j2haScrollToDaemon() {
  var daemon = document.getElementById('div_plugin_deamon');
  if (daemon && typeof daemon.scrollIntoView === 'function') {
    daemon.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }
  window.scrollTo(0, 0);
}

function j2haRefreshDaemonBlock() {
  try {
    if (typeof jeeFrontEnd !== 'undefined' && jeeFrontEnd && jeeFrontEnd.md_pluginDaemon && typeof jeeFrontEnd.md_pluginDaemon.refreshDeamonInfo === 'function') {
      jeeFrontEnd.md_pluginDaemon.refreshDeamonInfo();
    }
  } catch (e) { /* le bloc Démon se rafraîchit seul toutes les 5 s */ }
}

// Instantané pris au clic, AVANT de verrouiller les champs : le même relevé sert au test et à l'enregistrement, si bien qu'un
// test réussi sur un broker ne peut pas enregistrer un autre broker saisi entre-temps. `configuration` = valeurs `.configKey`
// lues comme le cœur (getJeeValues), dont l'hôte, le port (normalisé) et l'utilisateur sont ceux envoyés au test.
function j2haSnapshotMqttSettings() {
  var test = j2haMqttFormParams();
  var rawPort = $('.configKey[data-l1key=mqttPort]').val();
  var container = document.getElementById('div_plugin_configuration');
  var configuration = null;
  if (container && typeof container.getJeeValues === 'function') {
    configuration = j2haNormalizeMqttConfiguration(container.getJeeValues('.configKey')[0]);
    configuration.mqttHost = test.host;
    configuration.mqttUser = test.user;
    test.port = configuration.mqttPort;
  }
  return { test: test, rawPort: rawPort, configuration: configuration };
}

// Verrou des réglages du broker pendant la chaîne (levé à la fin, succès ou échec).
var j2haGuidedBusy = false;
function j2haLockMqttForm(locked) {
  j2haGuidedBusy = locked;
  $('.configKey[data-l1key^=mqtt], #in_mqttPassword, #bt_importMqttManager, #bt_mqttTestSaveRestart').prop('disabled', locked);
  $('#bt_testMqttConnection, #lnk_resetMqttForm, #lnk_mqttSaveRestartWithoutTest')
    .toggleClass('disabled', locked).attr('aria-disabled', locked ? 'true' : 'false').css('pointer-events', locked ? 'none' : '');
}

function j2haSavePluginConfig(snapshot, onSaved, onFailed) {
  if (!snapshot.configuration || typeof jeedom === 'undefined' || !jeedom.config || typeof jeedom.config.save !== 'function') {
    onFailed(null);
    return;
  }
  jeedom.config.save({
    configuration: snapshot.configuration,
    plugin: J2HA_PLUGIN_ID,
    error: function(error) { onFailed(error && error.message ? String(error.message) : null); },
    success: function() {
      if (typeof jeeFrontEnd !== 'undefined' && jeeFrontEnd) {
        jeeFrontEnd.modifyWithoutSave = false;
      }
      onSaved();
    }
  });
}

function j2haRestartDaemon(onDone, onFailed) {
  if (typeof jeedom === 'undefined' || !jeedom.plugin || typeof jeedom.plugin.deamonStart !== 'function') {
    onFailed(null);
    return;
  }
  jeedom.plugin.deamonStart({
    id: J2HA_PLUGIN_ID,
    forceRestart: 1,
    error: function(error) {
      j2haRefreshDaemonBlock();
      onFailed(error && error.message ? String(error.message) : null);
    },
    success: function() {
      j2haRefreshDaemonBlock();
      onDone();
    }
  });
}

function j2haRunGuidedConnection(skipTest) {
  if (j2haGuidedBusy || $('#bt_mqttTestSaveRestart').prop('disabled')) return;
  var snapshot = j2haSnapshotMqttSettings();
  j2haLockMqttForm(true);
  $('#div_mqttGuidedFallback, #div_mqttNoDaemon').hide();
  ['test', 'save', 'restart'].forEach(function(step) { j2haSetStep(step, 'pending'); });
  $('#ul_mqttGuidedSteps').show();
  var finish = function() { j2haLockMqttForm(false); };

  var restart = function() {
    j2haSetStep('restart', 'running');
    j2haRestartDaemon(function() {
      j2haSetStep('restart', 'done');
      $('#span_mqttTestResult').removeClass('text-danger text-warning').addClass('text-success')
        .text('{{Le démon a redémarré avec ces réglages.}}');
      $('#span_mqttTestRemedy').text(' ' + '{{La page du plugin affiche « MQTT Connecté » dans quelques secondes.}}');
      $('#div_mqttTestResult').attr('data-code', '').show();
      finish();
    }, function(reason) {
      j2haSetStep('restart', 'failed');
      j2haShowDaemonFallback((reason ? reason + ' — ' : '') + '{{Réglages enregistrés. Redémarrez le démon ci-dessus.}}');
      finish();
    });
  };

  var save = function() {
    j2haSetStep('save', 'running');
    j2haSavePluginConfig(snapshot, function() {
      j2haSetStep('save', 'done');
      // Le mot de passe saisi est maintenant enregistré : il quitte le formulaire.
      if ($('#in_mqttPassword').val() !== '') {
        $('#in_mqttPassword').val('').removeClass('configKey');
        $('#span_mqttPasswordStatus').show();
      }
      restart();
    }, function(reason) {
      j2haSetStep('save', 'failed');
      j2haShowDaemonFallback((reason ? reason + ' — ' : '') + '{{Enregistrez avec « Sauvegarder », puis redémarrez le démon ci-dessus.}}');
      finish();
    });
  };

  if (skipTest) {
    j2haSetStep('test', 'skipped');
    save();
    return;
  }
  j2haSetStep('test', 'running');
  j2haTestMqtt(function(outcome) {
    j2haShowMqttOutcome(outcome);
    if (outcome.kind !== 'ok') {
      // Rien n'est enregistré ni redémarré quand le test échoue.
      j2haSetStep('test', 'failed');
      finish();
      return;
    }
    j2haSetStep('test', 'done');
    save();
  }, snapshot);
}

$(function() {
  // ---- Plugins exclus : le champ porteur masqué (configKey) suit les cases (Q3) ----
  // « Sauvegarder » du cœur et « Enregistrer et relire Jeedom » écrivent donc la même clé au même format. Le cœur remplit les `configKey` après le
  // chargement de la page : les cases, rendues cochées côté serveur depuis la même valeur, sont remises à jour après ce remplissage
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
          .html('<i class="fas fa-user-cog"></i> {{Broker déjà configuré : les réglages enregistrés sont affichés ci-dessous.}}')
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

  // ---- Import forcé depuis MQTT Manager (bouton rendu seulement si MQTT Manager est installé et actif) ----
  // forceMqttManagerImport enregistre aussitôt côté serveur : confirmation avant d'écraser les réglages.
  $('#bt_importMqttManager').on('click', function() {
    if (j2haGuidedBusy) return;
    var $btn = $(this);
    j2haConfirm(
      '{{Récupérer depuis MQTT Manager}}',
      '{{Remplacer l\'adresse, le port, l\'utilisateur, le mot de passe et le réglage TLS par ceux de MQTT Manager ? Ils sont enregistrés tout de suite ; le démon les utilisera après son redémarrage.}}',
      '{{Remplacer}}',
      function() { j2haImportMqttManager($btn); }
    );
  });

  function j2haImportMqttManager($btn) {
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
            .text(data.result || '{{Erreur de communication}}')
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
            .html('<i class="fas fa-check-circle"></i> {{Configuration importée depuis MQTT Manager et enregistrée. Cliquez sur « Tester, enregistrer et redémarrer le démon » pour l\'utiliser.}}')
            .show();
        } else {
          $status.removeClass().addClass('alert alert-warning')
            .text(r.message)
            .show();
        }
      },
      error: function(request) {
        $btn.prop('disabled', false);
        $status.removeClass().addClass('alert alert-warning')
          .text('{{Erreur de communication}} (HTTP ' + request.status + ')')
          .show();
      }
    });
  }

  // ---- Réinitialiser le formulaire (front uniquement, sans sauvegarder) ----
  $('#lnk_resetMqttForm').on('click', function(e) {
    e.preventDefault();
    if (j2haGuidedBusy) return;
    $('.configKey[data-l1key=mqttHost]').val('');
    $('.configKey[data-l1key=mqttPort]').val('');
    $('.configKey[data-l1key=mqttUser]').val('');
    $('#in_mqttPassword').val('').removeClass('configKey');
    $('.configKey[data-l1key=mqttTls]').prop('checked', false);
    $('.configKey[data-l1key=mqttTlsVerify]').prop('checked', false);
    $('#span_mqttPasswordStatus').hide();
    $('#div_mqtt_autodetect_status').hide();
  });

  // ---- « Enregistrer et relire Jeedom » : confirmation, puis save → relecture chaînée (Story 4.3) ----
  // JS inline dans configuration.php — NE PAS déplacer dans desktop/js/jeedom2ha.js
  $('#bt_applyAndRescan').on('click', function() {
    var $btn = $(this);
    if ($btn.prop('disabled')) return;
    j2haConfirm(
      '{{Relire Jeedom}}',
      '{{Une relecture complète peut publier ou retirer des entités Home Assistant et applique les réglages enregistrés. Confirmer ?}}',
      '{{Relire}}',
      function() { j2haSaveAndReread($btn); }
    );
  });

  function j2haSaveAndReread($btn) {
    var $status = $('#span_rescanResult');
    $btn.prop('disabled', true);
    $status.removeClass('label-success label-danger label-warning')
           .text('{{Enregistrement en cours…}}').show();

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
                 .text(saveData.result || '{{Erreur lors de l\'enregistrement}}');
          return;
        }
        // Étape 2 : relire Jeedom avec la configuration fraîchement enregistrée
        $status.text('{{Relecture en cours…}}');
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
                     .text(scanData.result || '{{Erreur lors de la relecture}}');
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
            $status.addClass('label-success').text(j2haRereadDoneLabel(published));
          },
          error: function() {
            $btn.prop('disabled', false);
            $status.addClass('label-danger').text('{{Erreur de communication pendant la relecture}}');
          }
        });
      },
      error: function() {
        $btn.prop('disabled', false);
        $status.addClass('label-danger').text('{{Erreur de communication pendant l\'enregistrement}}');
      }
    });
  }

  // ---- Connexion au broker : bouton guidé, « Tester seulement », repli ----
  $('#bt_mqttTestSaveRestart').on('click', function() {
    j2haRunGuidedConnection(false);
  });
  $('#lnk_mqttSaveRestartWithoutTest').on('click', function(e) {
    e.preventDefault();
    if (j2haGuidedBusy) return;
    j2haConfirm(
      '{{Enregistrer sans tester}}',
      '{{Le démon ne répond pas, la connexion ne peut donc pas être testée. Enregistrer ces réglages et redémarrer le démon quand même ?}}',
      '{{Enregistrer et redémarrer}}',
      function() { j2haRunGuidedConnection(true); }
    );
  });
  $('#bt_mqttGoToDaemon').on('click', function() {
    j2haScrollToDaemon();
  });
  $('#bt_testMqttConnection').on('click', function(e) {
    e.preventDefault();
    var $link = $(this);
    if (j2haGuidedBusy || $link.attr('data-busy') === '1') return;
    $link.attr('data-busy', '1');
    $('#ul_mqttGuidedSteps, #div_mqttGuidedFallback').hide();
    $('#span_mqttTestResult').removeClass('text-success text-danger text-warning').text('{{Test en cours...}}');
    $('#span_mqttTestRemedy').text('');
    $('#div_mqttTestResult').show();
    j2haTestMqtt(function(outcome) {
      $link.attr('data-busy', '0');
      j2haShowMqttOutcome(outcome);
    });
  });
});
</script>
