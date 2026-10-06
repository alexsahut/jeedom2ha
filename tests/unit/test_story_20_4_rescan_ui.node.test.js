'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('desktop/js/jeedom2ha.js', 'utf8');
const config = fs.readFileSync('plugin_info/configuration.php', 'utf8');

test('20.4: le rescan garde le bouton dès la confirmation et ignore un second clic', () => {
  assert.match(source, /window\.jeedom2haRescanInProgress = true;/);
  assert.match(source, /\$button\.prop\('disabled'\) \|\| window\.jeedom2haRescanInProgress === true/);
  assert.match(source, /window\.jeedom2haRescanOwner = owner;/);
  assert.match(source, /window\.jeedom2haRescanOwner !== owner/);
});

test('20.4: applyHAGating ne réactive pas les actions pendant le rescan', () => {
  assert.match(source, /if \(window\.jeedom2haRescanInProgress === true\) \{\s*\$\('\[data-ha-action\]'\)\.prop\('disabled', true\);/);
});

test('20.4: les résultats UI distinguent succes, partiel, echec et champ absent', () => {
  assert.match(source, /operation_result === 'succes'/);
  assert.match(source, /operation_result === 'echec'[\s\S]*level: 'danger'/);
  assert.match(source, /typeof result\.operation_result === 'string'[\s\S]*level: 'warning'/);
  assert.match(source, /Résultat inconnu, relire Dernière opération/);
  assert.match(source, /Une opération est déjà en cours ou le rescan a échoué/);
  assert.match(source, /Erreur de communication : relire Dernière synchro/);
});

test('20.4: une erreur terminale du démon affiche operation_message et rafraîchit la santé', () => {
  assert.match(source, /\(result && \(result\.message \|\| result\.operation_message\)\) \|\| '\{\{Une opération est déjà en cours ou le rescan a échoué\.\}\}'/);
  assert.match(source, /if \(result && typeof result\.operation_result === 'string'\) \{\s*refreshBridgeStatus\(\);\s*\}/);
});

test('20.4: annulation ne lance aucune requête et la configuration emploie le même succès', () => {
  assert.match(source, /else if \(typeof onCancel === 'function'\) onCancel\(\);/);
  assert.match(config, /r\.status !== 'ok' \|\| r\.operation_result !== 'succes'/);
});

test('20.4: la page de configuration affiche aussi le message du 409 en priorité', () => {
  assert.match(config, /\$status\.addClass\('label-warning'\)\.text\(r\.message \|\| r\.operation_message \|\| '\{\{Résultat inconnu, relire Dernière opération\}\}'\);/);
});

test('20.4: le rescan a un délai de 20s et affiche le résultat chaîne du démon injoignable', () => {
  assert.match(source, /data: \{action: 'scanTopology'\}, dataType: 'json', timeout: 20000,/);
  assert.match(source, /if \(data\.state !== 'ok'\) \{\s*\$\('#div_alert'\)\.showAlert\(\{message: \(typeof result === 'string' && result\) \|\| '\{\{Une opération est déjà en cours ou le rescan a échoué\.\}\}', level: 'danger'\}\);\s*return;\s*\}/);
});

function loadConfirmationHarness() {
  const start = source.indexOf('function confirmHaPublishAction');
  const end = source.indexOf('function executeHaAction', start);
  const handlers = {};
  let options;
  const sandbox = {
    bootbox: {
      dialog(dialogOptions) {
        options = dialogOptions;
        return {
          on(event, callback) {
            handlers[event] = callback;
          },
        };
      },
    },
    window: {confirm: () => false},
  };
  vm.runInNewContext(source.slice(start, end), sandbox);
  return {
    confirm: sandbox.confirmHaPublishAction,
    get options() { return options; },
    handlers,
  };
}

function reservation() {
  return {inProgress: true, button: 'Confirmation en cours…', requests: 0};
}

test('20.4: croix, Échap et Annuler libèrent une réservation de confirmation sans requête', () => {
  for (const close of ['hidden.bs.modal', 'onEscape', 'cancel']) {
    const harness = loadConfirmationHarness();
    const state = reservation();
    harness.confirm('titre', 'message', 'Rescanner', () => { state.requests += 1; }, () => {
      state.inProgress = false;
      state.button = 'Rescanner la topologie Jeedom';
    });
    if (close === 'cancel') {
      harness.options.buttons.cancel.callback();
    } else if (close === 'onEscape') {
      harness.options.onEscape();
    } else {
      harness.handlers[close]();
    }
    assert.equal(state.inProgress, false, close);
    assert.equal(state.button, 'Rescanner la topologie Jeedom', close);
    assert.equal(state.requests, 0, close);
  }
});

test('20.4: fermeture après confirmation ne libère pas le rescan avant la fin de requête', () => {
  const harness = loadConfirmationHarness();
  const state = reservation();
  harness.confirm('titre', 'message', 'Rescanner', () => { state.requests += 1; }, () => {
    state.inProgress = false;
    state.button = 'Rescanner la topologie Jeedom';
  });
  harness.options.buttons.confirm.callback();
  harness.handlers['hidden.bs.modal']();
  harness.options.onEscape();
  assert.equal(state.inProgress, true);
  assert.equal(state.button, 'Confirmation en cours…');
  assert.equal(state.requests, 1);
});

test('20.4: les autres confirmations restent sans gestionnaire de fermeture', () => {
  const harness = loadConfirmationHarness();
  let confirms = 0;
  harness.confirm('titre', 'message', 'Republier', () => { confirms += 1; });
  assert.equal(harness.options.onEscape, undefined);
  assert.equal(harness.handlers['hidden.bs.modal'], undefined);
  harness.options.buttons.cancel.callback();
  assert.equal(confirms, 0);
  harness.options.buttons.confirm.callback();
  assert.equal(confirms, 1);
});

test('20.4: la libération de réservation ne touche que son propriétaire', () => {
  assert.match(source, /function releaseTopologyRescanReservation[\s\S]*window\.jeedom2haRescanOwner !== owner/);
  assert.match(source, /releaseTopologyRescanReservation\(\$button, snapshot, owner\);/);
});
