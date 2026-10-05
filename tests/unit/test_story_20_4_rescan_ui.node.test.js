'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');

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

test('20.4: annulation ne lance aucune requête et la configuration emploie le même succès', () => {
  assert.match(source, /else if \(typeof onCancel === 'function'\) onCancel\(\);/);
  assert.match(config, /r\.status !== 'ok' \|\| r\.operation_result !== 'succes'/);
});
