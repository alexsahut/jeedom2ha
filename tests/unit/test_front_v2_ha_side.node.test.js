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

describe('Lot 2 — fiche rendue : acceptation sur les cinq constats de la démo', () => {
  it('1. multiprise : « Publié · Lecture seule », 3 capteurs binaires, conseil « 3 sorties… » avec le remède du champ « Valeur »', () => {
    for (const [label, withDaemon] of BOTH) {
      const { ui, P, text } = openFiche(DEMO.multiprise(withDaemon));
      assert.equal(text('.j2ha-eq-publish-badge'), 'Publié', label + ' : un seul badge, mot d’état inchangé');
      assert.equal(text('.j2ha-eq-capacity'), 'Lecture seule', label);
      assert.equal(text('.j2ha-eq-advice-mention'), 'Conseil', label);
      assert.equal(ui.$(P + '.j2ha-eq-ha-entity').length, 3, label);
      assert.ok(ui.$(P + '.j2ha-eq-ha-entity').list.every((el) => plain(ui.$(el).text()).includes('Capteur binaire (binary_sensor)')), label);
      assert.match(text('.j2ha-eq-advice'), /3 sorties pourraient être pilotables\./, label);
      assert.match(text('.j2ha-eq-advice'), /champ « Valeur »/, label);
      assert.equal(ui.$(P + '.j2ha-eq-advice .j2ha-v2-open-equipment').attr('href'), 'index.php?v=d&m=virtual&p=virtual&id=142', label);
      assert.equal(ui.$(P + '.j2ha-eq-entity-id').length, withDaemon ? 3 : 0, label + ' : identifiant seulement du démon');
    }
  });

  it('2. portail : conseil « Publié comme capteur d’ouverture » avec « Ouvrir les types génériques »', () => {
    for (const [label, withDaemon] of BOTH) {
      const { ui, P, text } = openFiche(DEMO.portail(withDaemon));
      assert.match(text('.j2ha-eq-advice'), /Publié comme capteur d’ouverture\./, label);
      assert.equal(ui.$(P + '.j2ha-eq-advice .j2ha-open-generic-types').attr('href'), 'index.php?v=d&p=types', label);
    }
  });

  it('3. ventilateur : « Pilotable (allumer, éteindre) », conseil sur la vitesse, sans bouton', () => {
    for (const [label, withDaemon] of BOTH) {
      const { ui, P, text } = openFiche(DEMO.ventilateur(withDaemon));
      assert.equal(text('.j2ha-eq-capacity'), 'Pilotable (allumer, éteindre)', label);
      assert.match(text('.j2ha-eq-advice'), /La vitesse n’est pas reprise\./, label);
      assert.equal(ui.$(P + '.j2ha-eq-advice .btn').length, 0, label + ' : aucune action');
    }
  });

  // Front v2 (Lot 5) : « Corriger le type… » ouvre désormais le panneau E5 (plus le sélecteur de la cellule).
  // Garde levée (front v2, Lot 9a, point 9) : pour ce blocage par le nom, la fiche propose « Publier quand même » et
  // « Renommer l’équipement dans Jeedom, puis Relire Jeedom » ; le panneau de type reste ouvrable par la colonne « Type HA ».
  it('4. lampe typée prise : « Bloqué », fiche « le nom dit « lampe »… », « Publier quand même », panneau par la colonne', () => {
    for (const [label, withDaemon] of BOTH) {
      const { ui, P, text } = openFiche(DEMO.lampePrise(withDaemon));
      assert.equal(text('.j2ha-eq-publish-badge'), 'Bloqué', label);
      assert.equal(ui.$(P + '.j2ha-eq-capacity').length, 0, label + ' : pas de capacité pour un équipement non publié');
      assert.equal(ui.$(P + '.j2ha-eq-notices .j2ha-notice').length, 1, label);
      assert.match(text('.j2ha-eq-notices'), /Non publié : le nom dit « lampe », les types Jeedom disent « prise »\./, label);
      assert.equal(ui.$(P + '.j2ha-eq-advice').text(), '', label + ' : le conseil « nom ≠ type » n’est pas répété');
      assert.equal(ui.$(P + '.j2ha-v2-type-panel').length, 0);
      assert.equal(ui.$(P + '.j2ha-eq-notices .j2ha-v2-correct-type').length, 0, label + ' : « Corriger le type… » ne débloquerait pas');
      assert.equal(plain(ui.$(P + '.j2ha-eq-notices .j2ha-v2-publish-anyway').text()), 'Publier quand même', label);
      assert.equal(plain(ui.$(P + '.j2ha-eq-notices .j2ha-v2-rename').text()), 'Renommer l’équipement dans Jeedom, puis Relire Jeedom', label);
      assert.equal(ui.$(P + '.j2ha-eq-notices .j2ha-v2-rename').attr('href'), 'index.php?v=d&m=virtual&p=virtual&id=231', label);
      ui.click(P + 'tr[data-cmd-id="2311"] .j2ha-type-link');
      assert.equal(ui.$(P + 'tr[data-type-panel-for="2311"] .j2ha-v2-type-panel').length, 1, label + ' : le panneau est ouvert sous la première commande');
      assert.ok(ui.calls.every((c) => ['getBridgeStatus', 'getEquipmentStates', 'getMappingOverrides'].includes(c.action)), 'rien n’est écrit');
    }
  });

  it('5. équipement sans type : fiche avec la phrase des types génériques et « Ouvrir les types génériques »', () => {
    for (const [label, withDaemon] of BOTH) {
      const { ui, P, text } = openFiche(DEMO.sansType(withDaemon));
      assert.match(text('.j2ha-eq-notices'), /Jeedom ne sait pas à quoi servent ces commandes/, label);
      assert.match(text('.j2ha-eq-notices'), /« Lumière État », « Lumière Bouton On »/, label);
      assert.equal(plain(ui.$(P + '.j2ha-eq-notices .j2ha-open-generic-types').text()), 'Ouvrir les types génériques', label);
      assert.deepEqual(ui.$(P + '.mo-native-value').list.map((el) => plain(ui.$(el).text())), ['non renseigné', 'non renseigné'], label);
      assert.ok(ui.$(P + '.j2ha-v2-role-missing').length === 2, label + ' : en orange');
    }
  });

  it('6. lumière publiée : « Pilotable (allumer, éteindre) » et, avec le démon, son identifiant copiable', () => {
    for (const [label, withDaemon] of BOTH) {
      const { ui, P, text } = openFiche(DEMO.lumiere(withDaemon));
      assert.equal(text('.j2ha-eq-capacity'), 'Pilotable (allumer, éteindre)', label);
      assert.equal(ui.$(P + '.j2ha-eq-advice-mention').length, 0, label);
      if (withDaemon) {
        assert.equal(text('.j2ha-eq-entity-id'), 'light.jeedom2ha_eq_200');
        assert.equal(ui.$(P + '.j2ha-v2-copy').attr('aria-label'), '{{Copier l’identifiant}}');
      } else {
        assert.equal(ui.$(P + '.j2ha-eq-entity-id').length, 0);
      }
    }
  });
});

describe('Lot 2 — fiche rendue : bandeau, tableau, réglage, erreurs', () => {
  it('bandeau deux côtés : Jeedom (plugin, pièce, commandes, lien) → Home Assistant', () => {
    const { ui, P, text } = openFiche(DEMO.multiprise(true));
    assert.match(text('.j2ha-eq-side-jeedom'), /Multiprise Bureau/);
    assert.match(text('.j2ha-eq-side-jeedom'), /Plugin Virtuel · pièce Bureau · 9 commandes/);
    assert.match(text('.j2ha-eq-side-jeedom'), /3 états, 3 ordres On, 3 ordres Off/);
    assert.match(text('.j2ha-eq-side-ha'), /3 entités, en lecture seule/);
    assert.match(text('.j2ha-eq-side-ha'), /Home Assistant peut ajuster cet identifiant/);
    assert.equal(ui.$(P + '.j2ha-v2-arrow').attr('aria-hidden'), 'true');
  });

  it('« Détails techniques » et « Où le trouver » repliés par défaut, dépliés au clic (aria-expanded)', () => {
    const { ui, P } = openFiche(DEMO.multiprise(true));
    const toggle = ui.$(P + '.j2ha-eq-side-ha .j2ha-v2-tech-toggle');
    assert.equal(toggle.attr('aria-expanded'), 'false');
    const content = ui.$('#' + toggle.attr('aria-controls'));
    assert.equal(content.list[0].visible, false);
    ui.click(P + '.j2ha-eq-side-ha .j2ha-v2-tech-toggle');
    assert.equal(ui.$(P + '.j2ha-eq-side-ha .j2ha-v2-tech-toggle').attr('aria-expanded'), 'true');
    assert.equal(content.list[0].visible, true);
    assert.equal(ui.$(P + '.j2ha-v2-where-toggle').attr('aria-expanded'), 'false');
  });

  it('colonne « Rôle dans Jeedom » : libellé français, code en infobulle', () => {
    const { ui, P } = openFiche(DEMO.lumiere(true));
    const cells = ui.$(P + '.mo-native-value').list;
    assert.deepEqual(cells.map((el) => plain(ui.$(el).text())), ['Lumière État', 'Lumière Bouton On', 'Lumière Bouton Off']);
    assert.deepEqual(cells.map((el) => el.attrs.title), ['LIGHT_STATE', 'LIGHT_ON', 'LIGHT_OFF']);
  });

  it('ligne d’explication sous le contrôle segmenté, selon la position active', () => {
    const { text } = openFiche(DEMO.lumiere(true));
    assert.equal(text('.j2ha-eq-seg-help'), 'Automatique : le plugin décide (ici : publié).');
    const forced = DEMO.lumiere(true);
    forced.entities[0].publication_override = 'force_publish';
    forced.equipment_publication_override = 'force_publish';
    assert.equal(openFiche(forced).text('.j2ha-eq-seg-help'), 'Toujours : publier même si le plugin hésite.');
  });

  it('menu « ⋯ » : « Ouvrir l’équipement dans Jeedom » (lien, sans gating), entre « Tout remettre… » et la suppression', () => {
    const { ui, P } = openFiche(DEMO.lumiere(true));
    const entries = ui.$(P + '.j2ha-menu li').list.map((li) => plain(ui.$(li).text()));
    assert.deepEqual(entries, ['Republier', 'Tout remettre en automatique…', 'Ouvrir l’équipement dans Jeedom', '', 'Supprimer de Home Assistant…']);
    const link = ui.$(P + '.j2ha-menu a.j2ha-menu-item');
    assert.equal(link.attr('href'), 'index.php?v=d&m=virtual&p=virtual&id=200');
    assert.equal(link.attr('data-ha-action'), undefined);
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
    assert.equal(ui.$(P + '.j2ha-eq-mentions').text(), '');
    ui.click(P + '.j2ha-v2-retry');
    ui.respond('getMappingOverrides', { state: 'ok', result: { payload: tree } });
    assert.equal(ui.$(P + '.j2ha-v2-retry').length, 0);
    assert.equal(plain(ui.$(P + '.j2ha-eq-capacity').text()), 'Lecture seule');
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
