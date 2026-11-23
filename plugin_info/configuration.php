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

// Front v3 (Lot 3) : la page ne règle plus ce qui est publié (plugins, pièces, équipements, « En cas de doute ») : une seule
// source, le panneau « Choisir ce qui est publié » de la page du plugin, qui lit et écrit les mêmes clés (`excludedPlugins`,
// `confidencePolicy`, par la route de filtrage du plugin). Plus aucun champ `configKey` de ces clés ici : « Sauvegarder » du cœur ne
// peut plus les écraser.
// cron5 : la tâche planifiée du cœur (« Fonctionnalités ») ; l'avertissement n'est rendu que si elle est décochée.
$j2haCron5Enabled = true;
try {
  $j2haCron5Enabled = intval(config::byKey('functionality::cron5::enable', 'jeedom2ha', 1)) !== 0;
} catch (Throwable $e) {
  $j2haCron5Enabled = true;
}
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
// FR49 (CC-64) — un code de désarmement est-il enregistré ? Seule sa présence est lue : le code (chiffré) n'entre jamais dans le DOM.
$j2haAlarmCodeSet = false;
try {
  $j2haAlarmCodeSet = (string) config::byKey('alarmDisarmCode', 'jeedom2ha', '') !== '';
} catch (Throwable $e) {
  $j2haAlarmCodeSet = false;
}
// Front v3 (Lot 6) : adresse de la documentation du plugin, base des liens « En savoir plus » des info-bulles ⓘ (vide = pas de lien).
$j2haDocUrl = '';
try {
  $j2haSelf = plugin::byId('jeedom2ha');
  if (is_object($j2haSelf) && method_exists($j2haSelf, 'getDocumentation')) {
    $j2haDocUrl = (string) $j2haSelf->getDocumentation();
  }
} catch (Throwable $e) {
  $j2haDocUrl = '';
}
// Info-bulles ⓘ : le composant partagé de la page du plugin (aucune dépendance au cœur) et ses couleurs --j2ha-*.
include_file('desktop', 'jeedom2ha', 'css', 'jeedom2ha');
include_file('desktop', 'jeedom2ha_v2', 'css', 'jeedom2ha');
include_file('desktop', 'jeedom2ha_infotip', 'js', 'jeedom2ha');
?>

<p id="p_j2haBackTop" style="margin-bottom:12px;" data-j2ha-doc-base="<?php echo htmlspecialchars($j2haDocUrl, ENT_QUOTES, 'UTF-8'); ?>">
  <a href="index.php?v=d&amp;m=jeedom2ha&amp;p=jeedom2ha"><i class="fas fa-arrow-left"></i> {{Retour à la page du plugin}}</a>
</p>

<!-- Bandeau d'auto-détection MQTT -->
<div class="alert" id="div_mqtt_autodetect_status" style="display:none;"></div>

<form class="form-horizontal">
  <fieldset>
    <!-- Front v3 (Lot 3) : aucune phrase permanente ; les explications passent en info-bulles ⓘ. -->
    <legend><i class="fas fa-network-wired"></i> {{Connexion au broker MQTT}}
      <sup><button type="button" class="j2ha-info j2ha-v3-info" id="i_mqttBrokerIntro" data-j2ha-tip="{{Indiquez le broker que Home Assistant utilise déjà : le broker MQTT est le serveur de messages que Home Assistant écoute aussi. Le démon ne lit ces réglages qu'à son démarrage.}}" aria-label="{{Aide}} : {{Le broker que Home Assistant utilise déjà}}" aria-expanded="false" data-j2ha-doc="connexion-au-broker-mqtt"><i class="fas fa-info-circle" aria-hidden="true"></i></button></sup>
    </legend>
    <p class="text-warning" id="p_mqttOneInstance"><i class="fas fa-exclamation-triangle"></i> {{Une seule installation jeedom2ha par broker MQTT.}}
      <button type="button" class="j2ha-info j2ha-v3-info" data-j2ha-tip="{{Une deuxième installation branchée sur ce broker (box de test, sauvegarde restaurée ailleurs) retirerait les boutons de scénario de celle-ci, et inversement.}}" aria-label="{{Aide}} : {{Conséquence d'une deuxième installation}}" aria-expanded="false" data-j2ha-doc="connexion-au-broker-mqtt"><i class="fas fa-info-circle" aria-hidden="true"></i></button></p>

    <?php if ($j2haHasMqttManager) { ?>
    <div class="form-group">
      <div class="col-md-offset-4 col-md-6">
        <button type="button" class="btn btn-default btn-sm" id="bt_importMqttManager" title="{{Remplace les réglages ci-dessous par ceux de MQTT Manager et les enregistre aussitôt. Une confirmation est demandée avant.}}">
          <i class="fas fa-download"></i> {{Récupérer depuis MQTT Manager}}
        </button>
      </div>
    </div>
    <?php } ?>

    <div class="form-group">
      <label class="col-md-4 control-label">{{Hôte MQTT}}
        <sup><button type="button" class="j2ha-info j2ha-v3-info" data-j2ha-tip="{{Adresse IP ou nom d'hôte du broker MQTT}}" aria-label="{{Aide}} : {{Hôte MQTT}}" aria-expanded="false" data-j2ha-doc="connexion-au-broker-mqtt"><i class="fas fa-info-circle" aria-hidden="true"></i></button></sup>
      </label>
      <div class="col-md-4">
        <input class="configKey form-control" data-l1key="mqttHost" placeholder="ex: 192.168.1.10"/>
      </div>
    </div>

    <div class="form-group">
      <label class="col-md-4 control-label">{{Port MQTT}}
        <sup><button type="button" class="j2ha-info j2ha-v3-info" data-j2ha-tip="{{Port du broker MQTT (1883 par défaut, 8883 pour TLS)}}" aria-label="{{Aide}} : {{Port MQTT}}" aria-expanded="false" data-j2ha-doc="connexion-au-broker-mqtt"><i class="fas fa-info-circle" aria-hidden="true"></i></button></sup>
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
        <sup><button type="button" class="j2ha-info j2ha-v3-info" data-j2ha-tip="{{Activer le chiffrement TLS pour la connexion au broker}}" aria-label="{{Aide}} : {{Activer TLS}}" aria-expanded="false" data-j2ha-doc="connexion-au-broker-mqtt"><i class="fas fa-info-circle" aria-hidden="true"></i></button></sup>
      </label>
      <div class="col-md-4">
        <input type="checkbox" class="configKey" data-l1key="mqttTls"/>
      </div>
    </div>

    <div class="form-group">
      <label class="col-md-4 control-label">{{Vérifier le certificat}}
        <sup><button type="button" class="j2ha-info j2ha-v3-info" data-j2ha-tip="{{Valider le certificat du broker. Décocher pour les certificats auto-signés.}}" aria-label="{{Aide}} : {{Vérifier le certificat}}" aria-expanded="false" data-j2ha-doc="connexion-au-broker-mqtt"><i class="fas fa-info-circle" aria-hidden="true"></i></button></sup>
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

<!-- story/system-health : appareil « Santé de Jeedom » (lecture seule), désactivé par défaut. Enregistré par « Sauvegarder » du cœur. -->
<form class="form-horizontal" id="form_j2haSystemHealth">
  <fieldset>
    <legend><i class="fas fa-heartbeat"></i> {{Santé de Jeedom}}
      <sup><button type="button" class="j2ha-info j2ha-v3-info" id="i_systemHealth" data-j2ha-tip="{{Publie dans Home Assistant un appareil « Santé de Jeedom », en lecture seule : l'état du démon de chaque plugin qui en a un, les nombres de démons en service et arrêtés, le nombre de mises à jour disponibles, le nombre de messages (jamais leur texte) et la version du cœur. Relevé toutes les 5 minutes par cron5. Décocher retire l'appareil de Home Assistant.}}" aria-label="{{Aide}} : {{Santé de Jeedom}}" aria-expanded="false" data-j2ha-doc="santé-de-jeedom"><i class="fas fa-info-circle" aria-hidden="true"></i></button></sup>
    </legend>
    <div class="form-group">
      <label class="col-md-4 control-label" for="cb_publishSystemHealth">{{Publier la santé de Jeedom}}</label>
      <div class="col-md-4">
        <input type="checkbox" class="configKey" data-l1key="publishSystemHealth" id="cb_publishSystemHealth"/>
      </div>
    </div>
  </fieldset>
</form>

<!-- FR49 (CC-64) : code de désarmement de l'alarme. Champ mot de passe : enregistré chiffré, jamais rechargé dans la page ;
     le démon le lit à son démarrage. -->
<form class="form-horizontal" id="form_j2haAlarmCode">
  <fieldset>
    <legend><i class="fas fa-shield-alt"></i> {{Alarme}}
      <sup><button type="button" class="j2ha-info j2ha-v3-info" id="i_alarmDisarmCode" data-j2ha-tip="{{Avec un code (4 à 8 chiffres), Home Assistant le demande pour désarmer l'alarme ; l'armement reste libre. Sans code, désarmer n'en demande pas. Le code est enregistré chiffré et le démon ne le lit qu'à son démarrage : redémarrez le démon après l'avoir enregistré ou retiré.}}" aria-label="{{Aide}} : {{Code de désarmement}}" aria-expanded="false" data-j2ha-doc="alarmes"><i class="fas fa-info-circle" aria-hidden="true"></i></button></sup>
    </legend>
    <div class="form-group">
      <label class="col-md-4 control-label" for="in_alarmDisarmCode">{{Code de désarmement}}</label>
      <div class="col-md-4">
        <input type="password" class="form-control" data-l1key="alarmDisarmCode" id="in_alarmDisarmCode"
               autocomplete="new-password" inputmode="numeric" maxlength="16" placeholder="{{4 à 8 chiffres — vide pour conserver l'actuel}}"/>
        <small id="span_alarmDisarmCodeInvalid" class="text-warning" style="display:none;">
          <i class="fas fa-exclamation-triangle"></i> {{Code refusé : 4 à 8 chiffres (0 à 9), sans lettre ni symbole. Il ne sera pas enregistré.}}
        </small>
        <small id="span_alarmDisarmCodeStatus" class="text-success"<?php echo $j2haAlarmCodeSet ? '' : ' style="display:none;"'; ?>>
          <i class="fas fa-lock"></i> {{Code déjà configuré}}
        </small>
      </div>
    </div>
    <div class="form-group" id="div_alarmDisarmCodeClear"<?php echo $j2haAlarmCodeSet ? '' : ' style="display:none;"'; ?>>
      <label class="col-md-4 control-label" for="cb_alarmDisarmCodeClear">{{Retirer le code}}</label>
      <div class="col-md-4">
        <input type="checkbox" class="configKey" data-l1key="alarmDisarmCodeClear" id="cb_alarmDisarmCodeClear"/>
      </div>
    </div>
    <!-- Revue de 12.4 : le démon ne lit le code qu'à son démarrage (corps de /action/mqtt_connect). -->
    <div class="form-group" id="div_alarmDisarmCodeRestart" style="display:none;">
      <div class="col-md-offset-4 col-md-8">
        <span class="text-warning" data-j2ha-alarm-restart="first" style="display:none;">
          <i class="fas fa-redo"></i> <strong>{{Redémarrage du démon requis.}}</strong> {{Après l'enregistrement, redémarrez le démon : le code ne s'applique qu'à son démarrage. Sans redémarrage, l'alarme reste désarmable sans code.}}
        </span>
        <span class="text-warning" data-j2ha-alarm-restart="change" style="display:none;">
          <i class="fas fa-redo"></i> <strong>{{Redémarrage du démon requis.}}</strong> {{Après l'enregistrement, redémarrez le démon : le nouveau code ne s'applique qu'à son démarrage. Sans redémarrage, l'ancien code reste demandé.}}
        </span>
        <span class="text-warning" data-j2ha-alarm-restart="clear" style="display:none;">
          <i class="fas fa-redo"></i> <strong>{{Redémarrage du démon requis.}}</strong> {{Après l'enregistrement, redémarrez le démon : le retrait du code ne s'applique qu'à son démarrage. Sans redémarrage, le code reste demandé pour désarmer.}}
        </span>
      </div>
    </div>
  </fieldset>
</form>

<!-- Front v3 (Lot 3) : ce qui est publié se choisit dans un seul panneau, sur la page du plugin. -->
<p id="p_j2haChoosePublished">
  <a href="index.php?v=d&amp;m=jeedom2ha&amp;p=jeedom2ha#j2ha-choisir" id="lnk_j2haChoosePublished"><i class="fas fa-check-square"></i> {{Choisir ce qui est publié}} <i class="fas fa-external-link-alt"></i></a>
  <button type="button" class="j2ha-info j2ha-v3-info" data-j2ha-tip="{{Plugins, pièces, équipements et réglage « En cas de doute » : sur la page du plugin.}}" aria-label="{{Aide}} : {{Plugins, pièces, équipements et réglage « En cas de doute »}}" aria-expanded="false" data-j2ha-doc="ce-qui-est-publié-avancé"><i class="fas fa-info-circle" aria-hidden="true"></i></button>
</p>

<details id="details_j2haAdvanced" style="margin-bottom:12px;">
  <summary>{{Avancé}}</summary>
  <p style="margin-top:8px;">
    <a href="#" id="lnk_resetMqttForm" title="{{Vide les champs du broker sur cette page, sans rien enregistrer.}}"><i class="fas fa-times"></i> {{Réinitialiser le formulaire}}</a>
  </p>
</details>

<?php /* Front v3 (Lot 3) : avertissement d'une ligne, rendu seulement si cron5 est décoché (et suivi en direct par le JS). */ ?>
<p class="text-warning" id="p_cron5Note"<?php echo $j2haCron5Enabled ? ' style="display:none;"' : ''; ?>><i class="fas fa-exclamation-triangle"></i> {{cron5 désactivé : mises à jour manuelles}}
  <button type="button" class="j2ha-info j2ha-v3-info" data-j2ha-tip="{{Toutes les 5 minutes, cron5 republie ce qui a changé sans relecture de votre part (scénario ou équipement activé ou désactivé, exclusion) ; décoché, ces changements attendent un « Relire Jeedom ». Il se coche dans le bloc « Fonctionnalités » de Jeedom.}}" aria-label="{{Aide}} : {{Rôle de cron5}}" aria-expanded="false" data-j2ha-doc="configuration"><i class="fas fa-info-circle" aria-hidden="true"></i></button></p>

<p id="p_j2haBackBottom">
  <a href="index.php?v=d&amp;m=jeedom2ha&amp;p=jeedom2ha"><i class="fas fa-arrow-left"></i> {{Retour à la page du plugin}}</a>
</p>

<script>
// JS inline dans configuration.php — NE PAS déplacer dans desktop/js/jeedom2ha.js
// Ce fichier n'est pas chargé sur la vue de configuration plugin.

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

/* j2ha-alarm-code:begin */
// FR49 (CC-64) — le champ du code n'est enregistré (classe configKey) que s'il est saisi, valable et que « Retirer le code »
// n'est pas coché : une saisie vide garde le code actuel, comme le mot de passe MQTT. Le code n'est jamais affiché, ni écrit
// dans la console. Revue de 12.4 : 4 à 8 chiffres, espaces de début et de fin retirés (même règle que le PHP).
function j2haAlarmCodeText(value) {
  return String(value === undefined || value === null ? '' : value).trim();
}
function j2haAlarmCodeIsValid(value) {
  return /^[0-9]{4,8}$/.test(j2haAlarmCodeText(value));
}
function j2haAlarmCodeIsSaved(value, clearChecked) {
  return !clearChecked && j2haAlarmCodeIsValid(value);
}
// Saisie non vide mais refusée (message affiché, rien n'est enregistré).
function j2haAlarmCodeIsRejected(value, clearChecked) {
  return !clearChecked && j2haAlarmCodeText(value) !== '' && !j2haAlarmCodeIsValid(value);
}
// Avis « redémarrage du démon requis » d'un changement en attente : 'first' (premier code), 'change' (nouveau code),
// 'clear' (retrait), '' (aucun changement à enregistrer).
function j2haAlarmCodeRestartNotice(value, clearChecked, codeAlreadySet) {
  if (clearChecked) {
    return codeAlreadySet ? 'clear' : '';
  }
  if (!j2haAlarmCodeIsValid(value)) {
    return '';
  }
  return codeAlreadySet ? 'change' : 'first';
}
/* j2ha-alarm-code:end */

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
      // Story 12.4 — de même pour le code de désarmement de l'alarme, enregistré avec les autres réglages (s'il est valable :
      // un code refusé n'est pas enregistré et reste affiché avec son message). Le démon redémarre juste après : l'avis
      // « redémarrage requis » disparaît.
      if (typeof window.j2haAlarmCodeAfterSave === 'function') {
        window.j2haAlarmCodeAfterSave();
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
  // ---- Front v3 (Lot 3) : avertissement cron5, seulement si la case « cron5 » des Fonctionnalités du cœur est décochée ----
  // Rendu côté serveur au chargement ; suivi ici quand l'utilisateur coche ou décoche la case sur cette même page.
  $(document).on('change', '[data-l1key="functionality::cron5::enable"]', function() {
    $('#p_cron5Note').toggle(!$(this).is(':checked'));
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

  // ---- FR49 (CC-64) : code de désarmement de l'alarme ----
  var j2haAlarmCodeAlreadySet = <?php echo $j2haAlarmCodeSet ? 'true' : 'false'; ?>;
  function j2haSyncAlarmCodeField() {
    var clear = $('#cb_alarmDisarmCodeClear').is(':checked');
    var $code = $('#in_alarmDisarmCode');
    if (clear) {
      $code.val('');
    }
    $code.prop('disabled', clear).toggleClass('configKey', j2haAlarmCodeIsSaved($code.val(), clear));
    $('#span_alarmDisarmCodeInvalid').toggle(j2haAlarmCodeIsRejected($code.val(), clear));
    // Revue de 12.4 : le démon ne lit le code qu'à son démarrage ; l'avis dit quoi faire et ce qui vaut d'ici là.
    var notice = j2haAlarmCodeRestartNotice($code.val(), clear, j2haAlarmCodeAlreadySet);
    $('[data-j2ha-alarm-restart]').each(function() {
      $(this).toggle($(this).attr('data-j2ha-alarm-restart') === notice);
    });
    $('#div_alarmDisarmCodeRestart').toggle(notice !== '');
  }
  // Après « Tester, enregistrer et redémarrer le démon » : le code enregistré quitte le formulaire, le retrait est acquis.
  window.j2haAlarmCodeAfterSave = function() {
    var $code = $('#in_alarmDisarmCode');
    if ($code.hasClass('configKey')) {
      $code.val('').removeClass('configKey');
      j2haAlarmCodeAlreadySet = true;
      $('#span_alarmDisarmCodeStatus, #div_alarmDisarmCodeClear').show();
    } else if ($('#cb_alarmDisarmCodeClear').is(':checked')) {
      $('#cb_alarmDisarmCodeClear').prop('checked', false);
      j2haAlarmCodeAlreadySet = false;
      $('#span_alarmDisarmCodeStatus, #div_alarmDisarmCodeClear').hide();
    }
    j2haSyncAlarmCodeField();
  };
  $('#in_alarmDisarmCode').on('input keyup change', j2haSyncAlarmCodeField);
  $('#cb_alarmDisarmCodeClear').on('change', j2haSyncAlarmCodeField);

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
