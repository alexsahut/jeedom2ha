// Front v2 — Lot 2 : lexique de la fiche équipement (jeedom2ha_lexique.js). Une fiche « quoi / pourquoi / actions / aide »
// pour chaque code de REASON_LABELS, les trois raisons sans libellé et les quatre conseils ; repli « Cause non répertoriée » ;
// aucun terme interdit ; pas de point final dans les étiquettes d'action ; libellés français des types génériques.
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const L = require('../../desktop/js/jeedom2ha_lexique.js');

const UNLABELLED = ['ha_missing_required_option', 'ha_missing_temperature_command_topic', 'local_availability_publish_failed'];
const HINTS = ['actions_not_linked_to_state', 'binary_state_without_orders', 'speed_not_carried', 'name_type_mismatch'];
const word = (w) => new RegExp('(?<![\\p{L}\\p{N}_])' + w + '(?![\\p{L}\\p{N}_])', 'iu');
const FORBIDDEN = ['override', 'bridge', 'prête', 'prêtes', 'prêt', 'prêts', 'bloquante', 'bloquantes', 'rescanner', 'modale',
  'forcer', 'forçage', 'synchro', 'synchronisation', 'rescan'];

function texts(sheet) {
  return [sheet.quoi, sheet.pourquoi, sheet.aide].concat(sheet.actions.map((a) => a.label));
}

describe('Lot 2 — une fiche pour chaque cause', () => {
  const codes = Object.keys(M.REASON_LABELS).concat(UNLABELLED, HINTS);

  it('chaque code de REASON_LABELS, les trois raisons sans libellé et les quatre conseils ont une fiche connue', () => {
    assert.ok(Object.keys(M.REASON_LABELS).length >= 25);
    for (const code of codes) {
      const sheet = L.causeSheet(code, { count: 2 });
      assert.equal(sheet.known, true, code);
      assert.equal(sheet.code, code);
      assert.ok(sheet.quoi && sheet.quoi.length > 5, code + ' : quoi');
      assert.ok(sheet.pourquoi && sheet.pourquoi.length > 5, code + ' : pourquoi');
      assert.ok(Array.isArray(sheet.actions), code);
      sheet.actions.forEach((a) => assert.equal(a.label, L.ACTIONS[a.key], code + ' : action ' + a.key));
    }
  });

  it('code inconnu (démon plus récent) : « Cause non répertoriée », le code reste disponible pour les détails', () => {
    const sheet = L.causeSheet('cause_future_inconnue');
    assert.equal(sheet.known, false);
    assert.equal(sheet.quoi, 'Cause non répertoriée.');
    assert.equal(sheet.code, 'cause_future_inconnue');
    assert.deepEqual(sheet.actions, []);
    assert.equal(L.causeSheet(null).code, null);
  });

  it('aucun terme interdit, aucun « (s) », aucun pluriel en parenthèses dans les fiches', () => {
    for (const code of codes.concat(['inconnu'])) {
      for (const t of texts(L.causeSheet(code, { count: 3, name_word: 'lampe', type_word: 'prise', plugin_name: 'Virtuel' }))) {
        for (const f of FORBIDDEN) assert.doesNotMatch(t, word(f), `${code} : « ${t} » contient « ${f} »`);
        assert.doesNotMatch(t, /\p{L}\(s\)|commande\(s\)/iu, code + ' : ' + t);
      }
    }
  });

  it('pas de point final dans les étiquettes d’action ; jamais d’étiquette vide', () => {
    for (const label of Object.values(L.ACTIONS)) {
      assert.ok(label.trim().length > 0);
      assert.doesNotMatch(label, /\.$/, label);
    }
  });

  it('textes exacts de la spécification (E4) pour les cinq constats de la démo', () => {
    assert.equal(L.causeSheet('no_generic_type_configured').quoi, 'Non publié : Jeedom ne sait pas à quoi servent ces commandes.');
    assert.match(L.causeSheet('no_generic_type_configured').pourquoi, /« type générique » qui dit son rôle \(par exemple « Lumière État », « Lumière Bouton On »\)/);
    assert.deepEqual(L.causeSheet('no_generic_type_configured').actions.map((a) => a.label), ['Ouvrir les types génériques']);

    const mismatch = L.causeSheet('name_heuristic_rejection', { name_word: 'lampe', type_word: 'prise' });
    assert.equal(mismatch.quoi, 'Non publié : le nom dit « lampe », les types Jeedom disent « prise ».');
    // Garde levée (front v2, Lot 9a, regard neuf v2) : « Le plugin ne tranche pas à votre place » contredisait le réglage
    // « En cas de doute : Publier quand même » ; la fiche dit maintenant que c'est une contradiction, non publiée même ainsi.
    assert.equal(mismatch.pourquoi, 'Ce n’est pas un doute mais une contradiction : le réglage « En cas de doute sur un équipement » de la configuration ne s’y applique pas, et le plugin ne publie pas cet équipement de lui-même.');
    assert.equal(L.causeSheet('name_type_mismatch', { name_word: 'lampe', type_word: 'prise' }).pourquoi, 'Le plugin ne tranche pas à votre place.', 'conseil (équipement publié) inchangé');
    // Garde levée (front v2, Lot 9a, point 9) : « Corriger le type… » ne lève pas ce blocage (le démon garde la confiance
    // « ambiguë » quand le type change) : « Publier quand même » (réglage « Toujours ») et « Renommer… » à la place.
    assert.deepEqual(mismatch.actions.map((a) => a.key), ['publish_anyway', 'rename']);
    // Sans les deux mots, la phrase générale (jamais un mot deviné).
    assert.match(L.causeSheet('name_heuristic_rejection', {}).quoi, /ne disent pas la même chose/);
    assert.deepEqual(L.causeSheet('name_type_mismatch', { name_word: 'lampe', type_word: 'prise' }).quoi, mismatch.quoi);

    const outlets = L.causeSheet('actions_not_linked_to_state', { count: 3 });
    assert.equal(outlets.quoi, '3 sorties pourraient être pilotables.');
    assert.match(outlets.pourquoi, /Les ordres On et Off existent, mais Jeedom ne dit pas à quel état chacun correspond/);
    assert.match(outlets.aide, /champ « Valeur »/);
    assert.match(outlets.aide, /Relire Jeedom/);
    assert.deepEqual(outlets.actions.map((a) => a.label), ['Ouvrir l’équipement dans Jeedom']);
    assert.equal(L.causeSheet('actions_not_linked_to_state', { count: 1 }).quoi, 'Cet équipement pourrait être pilotable.');

    assert.equal(L.causeSheet('binary_state_without_orders').quoi, 'Publié comme capteur d’ouverture.');
    assert.deepEqual(L.causeSheet('binary_state_without_orders').actions.map((a) => a.key), ['generic_types']);

    const speed = L.causeSheet('speed_not_carried');
    assert.equal(speed.quoi, 'La vitesse n’est pas reprise.');
    assert.deepEqual(speed.actions, [], 'aucune action : limite dite honnêtement');
  });

  it('REASON_LABELS reste intact (bloc littéral, libellés courts) : le lexique ne le redéfinit pas', () => {
    const src = fs.readFileSync(path.join(__dirname, '..', '..', 'desktop/js/jeedom2ha_lexique.js'), 'utf8');
    assert.doesNotMatch(src, /REASON_LABELS\s*=|COMMAND_CAUSE_CATEGORIES|categoryOfCause|JSON\.stringify/);
    assert.match(fs.readFileSync(path.join(__dirname, '..', '..', 'desktop/js/jeedom2ha_mapping_override.js'), 'utf8'), /var REASON_LABELS = \{/);
  });
});

describe('Lot 2 — types génériques et types Home Assistant en français', () => {
  it('libellé français du type générique, code conservé pour l’infobulle ; code inconnu → le code ; vide → null', () => {
    assert.deepEqual(L.genericTypeLabel('LIGHT_STATE'), { label: 'Lumière État', code: 'LIGHT_STATE' });
    assert.deepEqual(L.genericTypeLabel('SWITCH_ON'), { label: 'Interrupteur Bouton On', code: 'SWITCH_ON' });
    assert.deepEqual(L.genericTypeLabel('ENERGY_STATE'), { label: 'Prise État', code: 'ENERGY_STATE' });
    assert.deepEqual(L.genericTypeLabel('BARRIER_STATE'), { label: 'Portail État', code: 'BARRIER_STATE' });
    assert.deepEqual(L.genericTypeLabel('TYPE_FUTUR'), { label: 'TYPE_FUTUR', code: 'TYPE_FUTUR' });
    assert.equal(L.genericTypeLabel(null), null);
    assert.equal(L.genericTypeLabel(''), null);
  });

  it('types Home Assistant : « Lumière (light) », mêmes mots que la table de 25.1 pour les types qu’elle connaît', () => {
    assert.equal(L.haTypeLabel('binary_sensor'), 'Capteur binaire (binary_sensor)');
    assert.equal(L.haTypeLabel('valve'), 'Vanne (valve)');
    assert.equal(L.haTypeLabel('lock'), 'Serrure (lock)');
    assert.equal(L.haTypeLabel(''), 'Entité Home Assistant');
    for (const type of ['alarm_control_panel', 'binary_sensor', 'button', 'climate', 'cover', 'light', 'sensor', 'switch']) {
      assert.equal(L.haTypeLabel(type), M.formatHaDomain(type), type);
    }
  });

  it('capacités dites en verbes, dans un ordre stable', () => {
    assert.deepEqual(L.capabilityVerbs(['on_off']), ['allumer', 'éteindre']);
    assert.deepEqual(L.capabilityVerbs(['position', 'stop', 'open_close']), ['ouvrir', 'fermer', 'arrêter', 'régler la position']);
    assert.deepEqual(L.capabilityVerbs(['inconnue']), []);
  });
});
