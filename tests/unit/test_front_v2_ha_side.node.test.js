// Front v2 — Lot 2 : côté Home Assistant de la fiche équipement (jeedom2ha_ha_side.js) et rendu de la fiche par le VRAI code
// de la surface. Fixtures : les cinq arbres de la démo (multiprise, portail, ventilateur, lampe typée prise, sans type) et une
// lumière publiée, AVEC et SANS les champs additifs du démon (Lot 3). Données fictives (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const HS = require('../../desktop/js/jeedom2ha_ha_side.js');
const { createUi, BRIDGE_UP } = require('./helpers/ui_harness');
const { DEMO, demoRoom } = require('./helpers/front_v2_demo_trees');

const plain = (text) => text.replace(/\{\{|\}\}/g, '');
const BOTH = [['avec les champs du démon', true], ['sans les champs du démon (repli)', false]];

describe('Lot 2 — describeEntity / describeHaSide : priorité au démon, repli prudent', () => {
  it('multiprise : trois capteurs binaires en lecture seule ; identifiant seulement s’il vient du démon', () => {
    for (const [label, withDaemon] of BOTH) {
      const side = HS.describeHaSide(DEMO.multiprise(withDaemon));
      assert.equal(side.entities.length, 3, label);
      assert.equal(side.mention, 'read_only', label);
      side.entities.forEach((d) => {
        assert.equal(d.type_label, 'Capteur binaire (binary_sensor)');
        assert.equal(d.controllable, false);
        assert.deepEqual(d.verbs, ['lire l’état']);
      });
      if (withDaemon) {
        assert.equal(side.entities[0].entity_id, 'binary_sensor.jeedom2ha_142_871');
        assert.equal(side.entities[0].name, 'Sortie 1');
        assert.equal(side.entities[0].source, 'demon');
      } else {
        assert.ok(side.entities.every((d) => d.entity_id === null && d.unique_id === null), 'jamais d’identifiant deviné');
        assert.equal(side.entities[0].source, 'repli');
      }
    }
  });

  it('ventilateur et lumière : pilotables (allumer, éteindre)', () => {
    for (const [label, withDaemon] of BOTH) {
      for (const make of [DEMO.ventilateur, DEMO.lumiere]) {
        const side = HS.describeHaSide(make(withDaemon));
        assert.equal(side.mention, 'controllable', label);
        assert.deepEqual(side.verbs, ['allumer', 'éteindre'], label);
      }
    }
  });

  it('le champ du démon l’emporte sur le repli (ha_controllable, ha_capabilities)', () => {
    const d = HS.describeEntity({ ha_entity_type: 'switch', command_ids: [1], ha_controllable: false, ha_capabilities: ['read'] },
      [{ jeedom_cmd_id: 1, generic_type: 'ENERGY_ON' }]);
    assert.equal(d.controllable, false);
    assert.deepEqual(d.verbs, ['lire l’état']);
    const cover = HS.describeEntity({ ha_entity_type: 'cover', command_ids: [1, 2, 3, 4] }, [
      { jeedom_cmd_id: 1, generic_type: 'FLAP_UP' }, { jeedom_cmd_id: 2, generic_type: 'FLAP_DOWN' },
      { jeedom_cmd_id: 3, generic_type: 'FLAP_STOP' }, { jeedom_cmd_id: 4, generic_type: 'FLAP_SLIDER' }]);
    assert.deepEqual(cover.verbs, ['ouvrir', 'fermer', 'arrêter', 'régler la position']);
  });

  it('repli aligné sur les mappers : une capacité exige son ordre (revue PR #390, fil 4569956454)', () => {
    const light = (generics, types) => HS.describeEntity({ ha_entity_type: 'light', command_ids: generics.map((_, i) => i + 1) },
      generics.map((g, i) => ({ jeedom_cmd_id: i + 1, generic_type: g, cmd_type: types ? types[i] : undefined })));
    // LIGHT_BRIGHTNESS (retour d'état) sans LIGHT_SLIDER : aucun réglage de luminosité publié (LightMapper._detect_brightness).
    assert.deepEqual(light(['LIGHT_STATE', 'LIGHT_ON', 'LIGHT_OFF', 'LIGHT_BRIGHTNESS']).verbs, ['allumer', 'éteindre']);
    assert.deepEqual(light(['LIGHT_ON', 'LIGHT_OFF', 'LIGHT_SLIDER']).verbs, ['allumer', 'éteindre', 'régler la luminosité']);
    // Une commande dite « info » par le démon n'ouvre aucune capacité.
    assert.deepEqual(light(['LIGHT_ON', 'LIGHT_SLIDER'], ['action', 'info']).capabilities, ['on_off']);
    // Ordres de portail reconnus par CoverMapper (GB_*), pas de capacité d'inclinaison inventée.
    const gate = HS.describeEntity({ ha_entity_type: 'cover', command_ids: [1, 2] },
      [{ jeedom_cmd_id: 1, generic_type: 'GB_OPEN' }, { jeedom_cmd_id: 2, generic_type: 'GB_CLOSE' }]);
    assert.deepEqual(gate.capabilities, ['open_close']);
    // Types génériques d'une autre famille que le type publié : ignorés.
    const sw = HS.describeEntity({ ha_entity_type: 'switch', command_ids: [1] }, [{ jeedom_cmd_id: 1, generic_type: 'LIGHT_SLIDER' }]);
    assert.deepEqual(sw.capabilities, ['on_off'], 'défaut du type, jamais « luminosité » sur un interrupteur');
  });

  it('type inconnu sans champ du démon : capacité inconnue (null), aucune mention', () => {
    const t = { entities: [{ ha_entity_type: 'futur', command_ids: [1], present_in_ha: true }], commands: [{ jeedom_cmd_id: 1 }] };
    const side = HS.describeHaSide(t);
    assert.equal(side.entities[0].controllable, null);
    assert.equal(side.mention, null);
  });

  it('équipement bloqué : aucune entité côté Home Assistant', () => {
    for (const [label, withDaemon] of BOTH) {
      assert.equal(HS.describeHaSide(DEMO.lampePrise(withDaemon)).entities.length, 0, label);
      assert.equal(HS.describeHaSide(DEMO.sansType(withDaemon)).entities.length, 0, label);
    }
  });

  it('côté Jeedom : nombre de commandes et répartition', () => {
    assert.deepEqual(HS.describeJeedomSide(DEMO.multiprise(true)), { command_count: 9, breakdown: '3 états, 3 ordres On, 3 ordres Off' });
    assert.deepEqual(HS.describeJeedomSide(DEMO.sansType(true)), { command_count: 2, breakdown: '' });
  });
});

describe('Lot 2 — computeHints : les conseils, du démon ou par heuristique', () => {
  const codes = (tree) => HS.computeHints(tree).map((h) => h.code);

  it('les cinq arbres de la démo, avec et sans le démon : mêmes conseils (sauf « le nom dit… », porté par la fiche de cause)', () => {
    for (const [label, withDaemon] of BOTH) {
      assert.deepEqual(codes(DEMO.multiprise(withDaemon)), ['actions_not_linked_to_state'], label);
      assert.deepEqual(codes(DEMO.portail(withDaemon)), ['binary_state_without_orders'], label);
      assert.deepEqual(codes(DEMO.ventilateur(withDaemon)), ['speed_not_carried'], label);
      assert.deepEqual(codes(DEMO.sansType(withDaemon)), [], label);
      assert.deepEqual(codes(DEMO.lumiere(withDaemon)), [], label);
    }
    assert.deepEqual(codes(DEMO.lampePrise(true)), ['name_type_mismatch']);
    assert.deepEqual(codes(DEMO.lampePrise(false)), []);
  });

  it('multiprise : 3 sorties, avec et sans le démon', () => {
    for (const [label, withDaemon] of BOTH) {
      assert.equal(HS.computeHints(DEMO.multiprise(withDaemon))[0].count, 3, label);
    }
  });

  it('le démon fait foi : `hints: []` désactive le repli', () => {
    const t = DEMO.multiprise(false);
    t.hints = [];
    assert.deepEqual(HS.computeHints(t), []);
  });

  it('heuristiques prudentes : au moindre indice manquant, aucun conseil', () => {
    // Multiprise dont les ordres sont reliés à leur état (champ du démon) : rien.
    const linked = DEMO.multiprise(true);
    delete linked.hints;
    linked.commands.forEach((c) => { if (c.cmd_type === 'action') c.linked_state_cmd_id = 871; });
    assert.deepEqual(codes(linked), []);
    // Capteur binaire d'une autre nature (présence) + ordres SWITCH_ON / SWITCH_OFF sans SWITCH_STATE : rien
    // (revue PR #390, fil 4569956460 : SwitchMapper._group_switch_cmds exige un trio de la même famille).
    const presence = {
      entities: [{ ha_entity_type: 'binary_sensor', command_ids: [1], present_in_ha: true }],
      commands: [{ jeedom_cmd_id: 1, generic_type: 'PRESENCE' }, { jeedom_cmd_id: 2, generic_type: 'SWITCH_ON' }, { jeedom_cmd_id: 3, generic_type: 'SWITCH_OFF' }],
    };
    assert.deepEqual(codes(presence), []);
    // Famille différente entre l'état et les ordres (ENERGY_STATE + SWITCH_ON / OFF) : rien.
    const mixed = DEMO.multiprise(false);
    mixed.commands.forEach((c) => { if (c.generic_type === 'SWITCH_STATE') c.generic_type = 'ENERGY_STATE'; });
    assert.deepEqual(codes(mixed), []);
    // Portail avec un ordre GB_TOGGLE (ordre réel du mapper) : rien.
    const toggle = DEMO.portail(false);
    toggle.commands.push({ jeedom_cmd_id: 1504, cmd_name: 'Bascule', generic_type: 'GB_TOGGLE' });
    assert.deepEqual(codes(toggle), []);
    // Ordres On sans ordres Off : rien.
    const onlyOn = DEMO.multiprise(false);
    onlyOn.commands = onlyOn.commands.filter((c) => c.generic_type !== 'SWITCH_OFF');
    assert.deepEqual(codes(onlyOn), []);
    // Portail avec un ordre Ouvrir typé : rien (le texte « sans ordres Ouvrir et Fermer » serait faux).
    const withOrder = DEMO.portail(false);
    withOrder.commands.push({ jeedom_cmd_id: 1503, cmd_name: 'Ouvrir', generic_type: 'BARRIER_OPEN' });
    assert.deepEqual(codes(withOrder), []);
    // Ventilateur publié en ventilateur : rien.
    const asFan = DEMO.ventilateur(false);
    asFan.entities.push({ ha_entity_type: 'fan', command_ids: [1604], present_in_ha: true });
    assert.deepEqual(codes(asFan), []);
    // Arbre vide ou illisible : rien, sans erreur.
    assert.deepEqual(HS.computeHints(null), []);
    assert.deepEqual(HS.computeHints({}), []);
  });

  it('« le nom dit … , les types disent … » : mots du démon, sinon du nom ; jamais devinés si ambigus', () => {
    assert.deepEqual(HS.nameTypeWords(DEMO.lampePrise(true)), { name_word: 'lampe', type_word: 'prise' });
    assert.deepEqual(HS.nameTypeWords(DEMO.lampePrise(false)), { name_word: 'lampe', type_word: 'prise' }, 'reason_details.matched_keyword');
    const noDetails = DEMO.lampePrise(false);
    noDetails.entities[0].reason_details = {};
    assert.deepEqual(HS.nameTypeWords(noDetails, 'Lampe Chevet'), { name_word: 'lampe', type_word: 'prise' }, 'repli sur le nom');
    assert.equal(HS.nameTypeWords(noDetails, 'Chevet'), null, 'aucun mot reconnu : phrase générale');
    assert.equal(HS.nameTypeWords(noDetails, 'Lampe spot'), null, 'deux mots : pas de choix au hasard');
  });

  it('module pur : aucune source de catégorie recopiée, aucune sérialisation', () => {
    const src = fs.readFileSync(path.join(__dirname, '..', '..', 'desktop/js/jeedom2ha_ha_side.js'), 'utf8');
    assert.doesNotMatch(src, /COMMAND_CAUSE_CATEGORIES|categoryOfCause|resolveEquipmentState|JSON\.stringify/);
  });
});

/** Ouvre la fiche de `tree` dans la vue de travail (pièce fictive « Bureau », plugin fictif « Virtuel »). */
function openFiche(tree) {
  const ui = createUi([demoRoom()], { pluginNames: { virtual: 'Virtuel' } });
  ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
  ui.openRoomWith(9, [{ state: 'ok', result: { payload: tree } }]);
  const P = `.j2ha-eq-panel[data-eq-id="${tree.jeedom_eq_id}"] `;
  const text = (selector) => plain(ui.$(P + selector).text()).replace(/\s+/g, ' ').trim();
  return { ui, P, text };
}

// Garde levée (front v3, Lot 2) : la fiche est refaite (en-tête sur deux lignes, bande de cause d'une ligne, bloc « Dans Home
// Assistant » d'une ligne par entité, « Détails techniques » dans le menu ⋯). Les cinq constats de la démo restent vérifiés, sur
// le nouveau rendu : la phrase longue de chaque cause passe dans l'info-bulle ⓘ, le « comment faire » dans « Détails techniques ».
describe('Lot 2 — fiche rendue : acceptation sur les cinq constats de la démo', () => {
  const info = (ui, P, scope) => plain(ui.$(P + scope + ' .j2ha-eq-band-info').attr('title') || '');
  const tech = (ui, P) => plain(ui.$(P + '.j2ha-eq-tech').text()).replace(/\s+/g, ' ');

  it('1. multiprise : « Publié », 3 capteurs binaires en lecture seule, conseil « 3 sorties pilotables » avec le remède du champ « Valeur »', () => {
    for (const [label, withDaemon] of BOTH) {
      const { ui, P, text } = openFiche(DEMO.multiprise(withDaemon));
      assert.equal(text('.j2ha-eq-publish-badge'), 'Publié', label + ' : un seul badge, mot d’état inchangé');
      assert.equal(ui.$(P + '.j2ha-eq-ha-entity').length, 3, label);
      assert.ok(ui.$(P + '.j2ha-eq-ha-entity').list.every((el) => plain(ui.$(el).text()).includes('Capteur binaire')), label);
      assert.ok(ui.$(P + '.j2ha-eq-ha-entity .j2ha-eq-capacity').list.every((el) => plain(ui.$(el).text()).trim() === 'Lecture seule'), label);
      assert.equal(text('.j2ha-eq-ha-count'), '3 entités', label);
      assert.equal(text('.j2ha-eq-advice .j2ha-eq-band-what'), '3 sorties pilotables', label);
      assert.match(info(ui, P, '.j2ha-eq-advice'), /3 sorties pourraient être pilotables\./, label);
      assert.match(tech(ui, P), /champ « Valeur »/, label);
      assert.equal(ui.$(P + '.j2ha-eq-advice .j2ha-v2-open-equipment').attr('href'), 'index.php?v=d&m=virtual&p=virtual&id=142', label);
      assert.equal(ui.$(P + '.j2ha-eq-entity-id').length, withDaemon ? 3 : 0, label + ' : identifiant seulement du démon');
    }
  });

  it('2. portail : conseil « Ouverture en lecture seule » avec « Types génériques »', () => {
    for (const [label, withDaemon] of BOTH) {
      const { ui, P, text } = openFiche(DEMO.portail(withDaemon));
      assert.equal(text('.j2ha-eq-advice .j2ha-eq-band-what'), 'Ouverture en lecture seule', label);
      assert.match(info(ui, P, '.j2ha-eq-advice'), /Publié comme capteur d’ouverture\./, label);
      assert.equal(ui.$(P + '.j2ha-eq-advice .j2ha-open-generic-types').attr('href'), 'index.php?v=d&p=types', label);
    }
  });

  it('3. ventilateur : « Pilotable » (verbes en info-bulle), conseil sur la vitesse, sans bouton', () => {
    for (const [label, withDaemon] of BOTH) {
      const { ui, P, text } = openFiche(DEMO.ventilateur(withDaemon));
      assert.equal(text('.j2ha-eq-capacity'), 'Pilotable', label);
      assert.equal(ui.$(P + '.j2ha-eq-capacity').attr('title'), 'allumer, éteindre', label);
      assert.equal(text('.j2ha-eq-advice .j2ha-eq-band-what'), 'Vitesse non reprise', label);
      assert.match(info(ui, P, '.j2ha-eq-advice'), /La vitesse n’est pas reprise\./, label);
      assert.equal(ui.$(P + '.j2ha-eq-advice .btn').length, 0, label + ' : aucune action');
    }
  });

  // Front v2 (Lot 5) : « Corriger le type… » ouvre désormais le panneau E5 (plus le sélecteur de la cellule).
  // Front v2 (Lot 9a, point 9) puis front v3 (Lot 2) : pour ce blocage par le nom, la bande propose « Publier en interrupteur ▾ »
  // (« Publier quand même », type dit) et « Renommer » ; le panneau de type reste ouvrable par la colonne « Type HA ».
  it('4. lampe typée prise : « Bloqué », bande « Nom « lampe » ≠ type « prise » », « Publier en interrupteur », aperçu, panneau par la colonne', () => {
    for (const [label, withDaemon] of BOTH) {
      const { ui, P, text } = openFiche(DEMO.lampePrise(withDaemon));
      assert.equal(text('.j2ha-eq-publish-badge'), 'Bloqué', label);
      assert.equal(ui.$(P + '.j2ha-eq-notices .j2ha-notice').length, 1, label);
      assert.equal(text('.j2ha-eq-notices .j2ha-eq-band-what'), 'Nom « lampe » ≠ type « prise »', label);
      assert.match(info(ui, P, '.j2ha-eq-notices'), /Non publié : le nom dit « lampe », les types Jeedom disent « prise »\./, label);
      assert.equal(ui.$(P + '.j2ha-eq-advice').text(), '', label + ' : le conseil « nom ≠ type » n’est pas répété');
      assert.equal(text('.j2ha-eq-ha-empty'), 'Rien', label);
      assert.equal(ui.$(P + '.j2ha-eq-ha-entity.is-preview').length, 1, label + ' : aperçu de ce que publierait « Toujours »');
      assert.match(text('.j2ha-eq-ha-entity.is-preview'), /Interrupteur \(aperçu\)/, label);
      assert.equal(ui.$('.j2ha-v3-type-modal .j2ha-v2-type-panel').length, 0);
      assert.equal(ui.$(P + '.j2ha-eq-notices .j2ha-v2-correct-type').length, 0, label + ' : « Changer le type » ne débloquerait pas');
      assert.equal(plain(ui.$(P + '.j2ha-eq-notices .j2ha-v2-publish-anyway').text()), 'Publier en interrupteur', label);
      assert.equal(plain(ui.$(P + '.j2ha-eq-notices .j2ha-v2-rename').text()).trim(), 'Renommer', label);
      assert.equal(plain(ui.$(P + '.j2ha-eq-notices .j2ha-v2-rename').attr('title')), 'Renommer l’équipement dans Jeedom, puis Relire Jeedom', label);
      assert.equal(ui.$(P + '.j2ha-eq-notices .j2ha-v2-rename').attr('href'), 'index.php?v=d&m=virtual&p=virtual&id=231', label);
      ui.click(P + 'tr[data-cmd-id="2311"] .j2ha-type-link');
      assert.equal(ui.$('.j2ha-v3-type-modal[data-type-panel-for="2311"] .j2ha-v2-type-panel').length, 1, label + ' : le panneau est ouvert pour la première commande (front v3, Lot 3 : fenêtre posée sur body)');
      assert.ok(ui.calls.every((c) => ['getBridgeStatus', 'getEquipmentStates', 'getMappingOverrides'].includes(c.action)), 'rien n’est écrit');
    }
  });

  it('5. équipement sans type : bande « Sans type générique », phrase des types génériques en info-bulle, « Types génériques »', () => {
    for (const [label, withDaemon] of BOTH) {
      const { ui, P, text } = openFiche(DEMO.sansType(withDaemon));
      assert.equal(text('.j2ha-eq-notices .j2ha-eq-band-what'), 'Sans type générique', label);
      assert.match(info(ui, P, '.j2ha-eq-notices'), /Jeedom ne sait pas à quoi servent ces commandes/, label);
      assert.match(info(ui, P, '.j2ha-eq-notices'), /« Lumière État », « Lumière Bouton On »/, label);
      assert.equal(plain(ui.$(P + '.j2ha-eq-notices .j2ha-open-generic-types').text()).trim(), 'Types génériques', label);
      assert.deepEqual(ui.$(P + '.mo-native-value').list.map((el) => plain(ui.$(el).text())), ['non renseigné', 'non renseigné'], label);
      assert.ok(ui.$(P + '.j2ha-v2-role-missing').length === 2, label + ' : en orange');
    }
  });

  it('6. lumière publiée : « Pilotable » (allumer, éteindre en info-bulle) et, avec le démon, son identifiant copiable', () => {
    for (const [label, withDaemon] of BOTH) {
      const { ui, P, text } = openFiche(DEMO.lumiere(withDaemon));
      assert.equal(text('.j2ha-eq-capacity'), 'Pilotable', label);
      assert.equal(ui.$(P + '.j2ha-eq-capacity').attr('title'), 'allumer, éteindre', label);
      assert.equal(ui.$(P + '.j2ha-eq-advice .j2ha-eq-band').length, 0, label);
      if (withDaemon) {
        assert.equal(text('.j2ha-eq-entity-id'), 'light.jeedom2ha_eq_200');
        assert.equal(ui.$(P + '.j2ha-v2-copy').attr('aria-label'), '{{Copier l’identifiant}}');
      } else {
        assert.equal(ui.$(P + '.j2ha-eq-entity-id').length, 0);
      }
    }
  });
});

describe('Lot 2 — fiche rendue : en-tête, bloc Home Assistant, tableau, réglage, erreurs', () => {
  it('ligne 2 de l’en-tête : plugin · n commandes (répartition en info-bulle) · ↗ Jeedom · Home Assistant (où le trouver en info-bulle)', () => {
    const { ui, P, text } = openFiche(DEMO.multiprise(true));
    assert.equal(text('.j2ha-eq-meta-facts'), 'Virtuel · 9 commandes');
    assert.equal(ui.$(P + '.j2ha-eq-meta-facts').attr('title'), '3 états, 3 ordres On, 3 ordres Off');
    assert.equal(ui.$(P + '.j2ha-eq-open-jeedom').attr('href'), 'index.php?v=d&m=virtual&p=virtual&id=142');
    assert.match(plain(ui.$(P + '.j2ha-v2-where-toggle').attr('title')), /Paramètres › Appareils et services › MQTT, puis l’appareil « Multiprise Bureau »/);
    assert.equal(text('.j2ha-eq-ha-title').replace(/3 entités$/, '').trim(), 'Dans Home Assistant');
    assert.match(plain(ui.$(P + '.j2ha-eq-entity-id').attr('title')), /Home Assistant peut ajuster cet identifiant/);
  });

  it('« Détails techniques » : replié par défaut, ouvert par le menu ⋯ (numéro Jeedom, identifiants uniques, code de la cause)', () => {
    const { ui, P } = openFiche(DEMO.multiprise(true));
    const content = ui.$(P + '.j2ha-eq-tech .j2ha-v2-tech');
    assert.equal(content.list[0].visible, false);
    assert.match(plain(content.text()), /Équipement Jeedom #142/);
    assert.match(plain(content.text()), /jeedom2ha_142_871/);
    ui.click(P + '.j2ha-eq-tech-toggle');
    assert.equal(content.list[0].visible, true);
  });

  it('au-delà de 3 entités : 3 lignes visibles, « + n autres » déplie le reste', () => {
    const tree = DEMO.multiprise(true);
    const extra = JSON.parse(JSON.stringify(tree.entities[2]));
    extra.command_ids = [874]; extra.ha_default_entity_id = 'binary_sensor.jeedom2ha_142_874'; extra.ha_name = 'Sortie 4';
    tree.entities.push(extra);
    tree.commands.push(Object.assign({}, tree.commands[0], { jeedom_cmd_id: 874, cmd_name: 'État 4' }));
    const { ui, P, text } = openFiche(tree);
    assert.equal(text('.j2ha-eq-ha-count'), '4 entités');
    assert.equal(ui.$(P + '.j2ha-eq-ha-more').list[0].visible, false);
    assert.equal(ui.$(P + '.j2ha-eq-ha-more .j2ha-eq-ha-entity').length, 1);
    assert.equal(text('.j2ha-eq-ha-toggle'), '+ 1 autre');
    ui.click(P + '.j2ha-eq-ha-toggle');
    assert.equal(ui.$(P + '.j2ha-eq-ha-more').list[0].visible, true);
    assert.equal(ui.$(P + '.j2ha-eq-ha-toggle').attr('aria-expanded'), 'true');
  });

  it('colonne « Rôle dans Jeedom » : libellé français, code en infobulle', () => {
    const { ui, P } = openFiche(DEMO.lumiere(true));
    const cells = ui.$(P + '.mo-native-value').list;
    assert.deepEqual(cells.map((el) => plain(ui.$(el).text())), ['Lumière État', 'Lumière Bouton On', 'Lumière Bouton Off']);
    assert.deepEqual(cells.map((el) => el.attrs.title), ['LIGHT_STATE', 'LIGHT_ON', 'LIGHT_OFF']);
  });

  it('réglage segmenté : plus de phrase sous le contrôle, une info-bulle par position ; « Toujours » jamais grisé', () => {
    const { ui, P } = openFiche(DEMO.lumiere(true));
    assert.equal(ui.$(P + '.j2ha-eq-seg-help').length, 0);
    const seg = (key) => ui.$(P + '.j2ha-eq-controls .j2ha-seg-' + key);
    assert.equal(plain(seg('auto').attr('title')), 'Le plugin décide');
    assert.equal(plain(seg('always').attr('title')), 'Publier même si le plugin hésite, maintenant ou plus tard');
    assert.equal(plain(seg('never').attr('title')), 'Ne jamais publier');
    assert.notEqual(seg('always').prop('disabled'), true, 'équipement publié : « Toujours » reste une vraie action');
  });

  it('menu « ⋯ » : « Ouvrir l’équipement dans Jeedom » (lien, sans gating), « Détails techniques », puis la suppression', () => {
    const { ui, P } = openFiche(DEMO.lumiere(true));
    const entries = ui.$(P + '.j2ha-menu li').list.map((li) => plain(ui.$(li).text()));
    assert.deepEqual(entries, ['Republier', 'Tout remettre en automatique…', 'Ouvrir l’équipement dans Jeedom', 'Détails techniques', '', 'Supprimer de Home Assistant…']);
    const link = ui.$(P + '.j2ha-menu a.j2ha-menu-item');
    assert.equal(link.attr('href'), 'index.php?v=d&m=virtual&p=virtual&id=200');
    assert.equal(link.attr('data-ha-action'), undefined);
    assert.equal(ui.$(P + '.j2ha-eq-tech-toggle').attr('data-ha-action'), undefined, '« Détails techniques » n’écrit rien : jamais grisé');
  });

  it('lecture impossible : message existant et « Réessayer » (même lecture) ; aucune donnée périmée', () => {
    const tree = DEMO.multiprise(true);
    const ui = createUi([demoRoom()], { pluginNames: { virtual: 'Virtuel' } });
    ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
    ui.loadStates({ 142: tree });
    ui.openRoom(9);
    ui.selectEquipment(142);
    ui.fail('getMappingOverrides');
    const P = '.j2ha-eq-panel[data-eq-id="142"] ';
    assert.match(ui.$(P + '.j2ha-eq-status').text(), /démon indisponible/);
    assert.equal(ui.$(P + '.j2ha-eq-sides').text(), '');
    assert.equal(ui.$(P + '.j2ha-eq-meta-facts').text(), '');
    assert.equal(ui.$(P + '.j2ha-eq-mentions').text(), '');
    ui.click(P + '.j2ha-v2-retry');
    ui.respond('getMappingOverrides', { state: 'ok', result: { payload: tree } });
    assert.equal(ui.$(P + '.j2ha-v2-retry').length, 0);
    assert.equal(plain(ui.$(P + '.j2ha-eq-capacity').first().text()).trim(), 'Lecture seule');
  });

  it('parité du mot d’état : le badge reste le seul mot d’état ; capacité et conseil sont hors du badge', () => {
    for (const make of Object.values(DEMO)) {
      const tree = make(true);
      const { ui, P, text } = openFiche(tree);
      const word = M.EQUIPMENT_STATE_LABELS[M.resolveEquipmentState(tree, true).state];
      assert.equal(text('.j2ha-eq-publish-badge'), word, tree.eq_name);
      assert.equal(ui.$(P + '.j2ha-eq-publish-badge .j2ha-eq-capacity').length, 0);
      assert.equal(ui.$(P + '.j2ha-state-text').length, 1, tree.eq_name + ' : plus de doublon « Publié / Publié »');
    }
  });
});
