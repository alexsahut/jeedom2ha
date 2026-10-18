// ARTEFACT — Story 25.1 (AC5, AC6, AC13, AC14, AC15) : catégories de commande (D2/D3), compteurs de
// l'équipement et de la pièce, cause dite une fois, commandes ignorées repliées, domaines HA traduits.
// Logique pure du module ; identifiants génériques uniquement (CC-48).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const { view, READY, EXCLUDED, DISABLED } = require('./helpers/ui_harness');

const blockedView = (code) => view(code || 'no_generic_type_configured', false, false);
const IGNORED = view('command_not_covered', false, false);

function cmd(id, diagnostic, published, name) {
  return { jeedom_cmd_id: id, cmd_name: name || ('Commande ' + id), diagnostic, covered: true, published_in_ha: published === undefined ? false : published };
}

function eq(id, commands, sync, extra) {
  return Object.assign({
    jeedom_eq_id: id, eq_name: 'Équipement ' + id, mapped: true, eligible: true, equipment_decision: null,
    entities: [],
    sync_status: Object.assign({ synced_should_publish: true, current_should_publish: true, override_pending: false, published_in_ha: false }, sync || {}),
    commands,
  }, extra || {});
}

describe('25.1 / AC5 — partition D3 des codes de cause', () => {
  const ignored = ['command_not_covered', 'no_supported_generic_type', 'ha_component_not_in_product_scope'];
  const blocked = ['ambiguous_skipped', 'name_heuristic_rejection', 'duplicate_generic_types', 'conflicting_generic_types',
    'switch_state_orphan', 'probable_skipped', 'low_confidence', 'no_generic_type_configured', 'no_mapping',
    'skipped_no_mapping_candidate', 'ha_missing_command_topic', 'ha_missing_state_topic', 'discovery_publish_failed',
    'no_projection_possible'];
  const state = ['disabled_eqlogic', 'excluded_eqlogic', 'excluded_plugin', 'excluded_object', 'publication_excluded_eqlogic',
    'publication_excluded_command', 'publication_forced', 'sure_mapping'];

  it('chaque code de REASON_LABELS appartient à exactement une catégorie (échoue si un code est ajouté sans catégorie)', () => {
    const categories = M.COMMAND_CAUSE_CATEGORIES;
    for (const code of Object.keys(M.REASON_LABELS)) {
      const owners = Object.keys(categories).filter((name) => categories[name].includes(code));
      assert.equal(owners.length, 1, code + ' → ' + owners.join(','));
    }
    for (const name of Object.keys(categories)) {
      for (const code of categories[name]) assert.ok(code in M.REASON_LABELS, code + ' absent de REASON_LABELS');
    }
  });

  it('la partition est celle de D3 (décision Q3)', () => {
    assert.deepEqual([...M.COMMAND_CAUSE_CATEGORIES.ignored].sort(), [...ignored].sort());
    assert.deepEqual([...M.COMMAND_CAUSE_CATEGORIES.blocked].sort(), [...blocked].sort());
    assert.deepEqual([...M.COMMAND_CAUSE_CATEGORIES.state].sort(), [...state].sort());
    assert.deepEqual(M.COMMAND_CAUSE_CATEGORIES.equipment_state, ['no_commands']);
  });

  it('ha_component_not_in_product_scope → Ignorée ; no_projection_possible → Bloquée ; code inconnu → Bloquée', () => {
    assert.equal(M.classifyCommandCategory(cmd(1, view('ha_component_not_in_product_scope', false, false))), 'ignored');
    assert.equal(M.classifyCommandCategory(cmd(1, blockedView('no_projection_possible'))), 'blocked');
    assert.equal(M.classifyCommandCategory(cmd(1, blockedView('code_futur_inconnu'))), 'blocked');
    assert.equal(M.categoryOfCause('code_futur_inconnu'), 'blocked');
  });

  it('une commande dans HA est Publiée quel que soit son diagnostic ; exclue/désactivée gardent leur catégorie', () => {
    assert.equal(M.classifyCommandCategory(cmd(1, blockedView(), true)), 'published');
    assert.equal(M.classifyCommandCategory(cmd(1, EXCLUDED)), 'excluded');
    assert.equal(M.classifyCommandCategory(cmd(1, DISABLED)), 'disabled');
    assert.equal(M.classifyCommandCategory(cmd(1, READY)), 'to_apply');
  });

  it('une commande non couverte sans diagnostic est Ignorée', () => {
    assert.equal(M.classifyCommandCategory({ jeedom_cmd_id: 1, covered: false, diagnostic: null, published_in_ha: false }), 'ignored');
  });
});

describe('25.1 / AC5 — compteurs de commandes d’un équipement', () => {
  const tree = eq(1, [
    cmd(1, READY, true), cmd(2, READY, true), cmd(3, READY, true), cmd(4, blockedView()),
    cmd(5, IGNORED), cmd(6, IGNORED), cmd(7, IGNORED), cmd(8, IGNORED), cmd(9, IGNORED),
  ], { published_in_ha: true });

  it('« 3 publiées · 1 bloquée · 5 ignorées » : zéros masqués, pluriels accordés', () => {
    const labels = M.buildEquipmentCounterLabels(tree);
    assert.deepEqual(labels.items, ['3 publiées', '1 bloquée', '5 ignorées']);
    assert.equal(labels.text, '3 publiées · 1 bloquée · 5 ignorées');
  });

  it('le compteur de défauts de l’équipement vaut 1 : les ignorées n’y comptent pas', () => {
    const counters = M.summarizeEquipmentCounters(tree);
    assert.equal(counters.defects, 1);
    assert.equal(counters.commands.ignored, 5);
    assert.equal(counters.state, 'published');
    assert.equal(counters.blocked_mention, 1);
  });

  it('un équipement dont toutes les commandes sont ignorées est « Rien à publier », sans défaut', () => {
    const none = eq(2, [cmd(1, IGNORED), cmd(2, IGNORED)], { current_should_publish: false });
    const counters = M.summarizeEquipmentCounters(none);
    assert.equal(counters.state, 'nothing_to_publish');
    assert.equal(counters.defects, 0);
    const room = M.summarizeRoom([none, tree], 2);
    assert.equal(room.defects, 1, 'seule la commande bloquée de l’autre équipement compte');
  });

  it('pas de singulier forcé : un pluriel n’affiche jamais « (s) »', () => {
    const labels = M.buildEquipmentCounterLabels(eq(3, [cmd(1, READY, true)], { published_in_ha: true }));
    assert.deepEqual(labels.items, ['1 publiée']);
    for (const text of labels.items) assert.doesNotMatch(text, /\(s\)/);
  });

  it('une commande prête mais pas encore dans HA se dit « à appliquer » ; exclue se dit « exclue »', () => {
    const labels = M.buildEquipmentCounterLabels(eq(4, [cmd(1, READY), cmd(2, EXCLUDED), cmd(3, EXCLUDED)]));
    assert.deepEqual(labels.items, ['1 à appliquer', '2 exclues']);
  });

  it('présence inconnue (démon plus ancien) : dite, jamais comptée publiée', () => {
    const old = eq(5, [cmd(1, READY, null)], { published_in_ha: null, current_should_publish: null });
    const labels = M.buildEquipmentCounterLabels(old);
    assert.match(labels.presence_unknown, /présence dans Home Assistant inconnue/);
    assert.equal(M.summarizeEquipmentCounters(old).commands.published, 0);
  });
});

describe('25.1 / AC6 — compteurs de la pièce par état d’équipement', () => {
  function fourteen() {
    const list = [];
    for (let i = 0; i < 9; i += 1) list.push(eq(100 + i, [cmd(1, READY, true)], { published_in_ha: true }));
    for (let i = 0; i < 2; i += 1) list.push(eq(200 + i, [cmd(1, READY)], { published_in_ha: false }));
    list.push(eq(300, [cmd(1, blockedView())], { current_should_publish: false }));
    list.push(eq(400, [cmd(1, EXCLUDED)], {}, { equipment_decision: EXCLUDED }));
    list.push(eq(500, [cmd(1, DISABLED)], {}, { equipment_decision: DISABLED }));
    return list;
  }

  it('un chiffre et un mot court par état non nul, dans l’ordre Publié, À appliquer, Bloqué, Exclu, Désactivé, Rien à publier', () => {
    const labels = M.buildRoomCounterLabels(M.summarizeRoom(fourteen(), 14));
    assert.deepEqual(labels.items.map((i) => i.text), ['9 publiés', '2 à appliquer', '1 bloqué', '1 exclu', '1 désactivé']);
    assert.deepEqual(labels.items.map((i) => i.state), ['published', 'to_apply', 'blocked', 'excluded', 'disabled']);
    assert.ok(labels.items.every((i) => !/^0 /.test(i.text)), 'aucun « 0 … » affiché');
  });

  it('aucun compteur de commandes au niveau de la pièce (Q4)', () => {
    const summary = M.summarizeRoom(fourteen(), 14);
    assert.equal(Object.keys(summary).some((k) => /^commands_/.test(k)), false);
    assert.equal('commands' in M.buildRoomCounterLabels(summary), false);
  });

  it('la somme des états égale le nombre d’équipements lus, sans reste ni double compte (3 pièces)', () => {
    const rooms = [
      fourteen(),
      [eq(1, [cmd(1, IGNORED)], { current_should_publish: false }), eq(2, [], {}, { equipment_decision: view('no_commands', false, false) })],
      [eq(3, [cmd(1, READY, true), cmd(2, blockedView())], { published_in_ha: true }, { entities: [{ ha_entity_type: 'light', command_ids: [1], override_pending: true, decision: READY }] }),
        eq(4, [cmd(1, DISABLED), cmd(2, EXCLUDED)]), eq(5, [cmd(1, READY, null)], { published_in_ha: null, current_should_publish: null })],
    ];
    for (const trees of rooms) {
      const summary = M.summarizeRoom(trees, trees.length);
      const sum = Object.values(summary.by_state).reduce((a, b) => a + b, 0);
      assert.equal(sum, trees.length);
      assert.equal(summary.equipments_read, trees.length);
    }
  });

  it('« N équipements non lus » et la présence inconnue sont conservés, au glossaire', () => {
    const old = eq(9, [cmd(1, READY, null)], { published_in_ha: null, current_should_publish: null });
    const labels = M.buildRoomCounterLabels(M.summarizeRoom([old], 3));
    assert.equal(labels.unread, '2 équipements non lus');
    assert.match(labels.presence_unknown, /présence dans Home Assistant est inconnue \(démon plus ancien\)/);
    const one = M.buildRoomCounterLabels(M.summarizeRoom([old], 2));
    assert.equal(one.unread, '1 équipement non lu');
  });
});

describe('25.1 / AC14 — la cause est dite une fois', () => {
  it('11 commandes bloquées pour la même cause : un seul groupe, son texte et le lien vers les types génériques', () => {
    const commands = [];
    for (let i = 1; i <= 11; i += 1) commands.push(cmd(i, blockedView('no_generic_type_configured')));
    const groups = M.groupBlockedCauses(eq(1, commands));
    assert.equal(groups.length, 1);
    assert.equal(groups[0].count, 11);
    assert.equal(M.buildCauseNoticeText(groups[0]), '11 commandes bloquées : types génériques non configurés dans Jeedom');
    assert.equal(groups[0].generic_types_link, true);
  });

  it('causes différentes : un groupe par cause distincte, jamais un par commande', () => {
    const groups = M.groupBlockedCauses(eq(1, [
      cmd(1, blockedView('no_generic_type_configured')), cmd(2, blockedView('no_generic_type_configured')),
      cmd(3, blockedView('ha_missing_state_topic')), cmd(4, READY), cmd(5, IGNORED),
    ]));
    assert.equal(groups.length, 2);
    assert.deepEqual(groups.map((g) => g.count), [2, 1]);
    assert.equal(groups[1].generic_types_link, false);
    assert.equal(M.buildCauseNoticeText(groups[1]), '1 commande bloquée : pas de retour d’état exploitable');
  });

  it('code inconnu : groupe présent, code brut conservé pour l’infobulle', () => {
    const groups = M.groupBlockedCauses(eq(1, [cmd(1, blockedView('code_futur_inconnu'))]));
    assert.equal(groups.length, 1);
    assert.equal(groups[0].raw_code, 'code_futur_inconnu');
  });

  it('première commande bloquée : exposée pour l’ancre, absente quand toutes les commandes sont bloquées', () => {
    const mixed = M.summarizePublication(eq(1, [cmd(1, READY, true), cmd(2, blockedView())]));
    assert.equal(mixed.first_blocking_cmd_id, 2);
    assert.equal(M.allCommandsBlocked(eq(1, [cmd(1, blockedView()), cmd(2, blockedView())])), true);
    assert.equal(M.allCommandsBlocked(eq(1, [cmd(1, blockedView()), cmd(2, READY)])), false);
    assert.equal(M.allCommandsBlocked(eq(1, [])), false);
  });
});

describe('25.1 / AC15 — commandes ignorées repliées', () => {
  const names = ['Pinguer nœud', 'Soigner nœud', 'Réveiller nœud', 'Statut radio', 'Version'];
  const ignoredCmds = names.map((n, i) => cmd(10 + i, IGNORED, false, n));

  it('« 5 commandes ignorées, sans équivalent dans Home Assistant : » + 3 noms puis « … »', () => {
    const summary = M.buildIgnoredSummary(eq(1, ignoredCmds));
    assert.equal(summary.count, 5);
    assert.equal(summary.text, '5 commandes ignorées, sans équivalent dans Home Assistant : Pinguer nœud, Soigner nœud, Réveiller nœud…');
    assert.deepEqual(summary.items.map((i) => i.name), names);
  });

  it('jusqu’à 3 noms : pas d’ellipse ; aucune ignorée : pas de ligne', () => {
    assert.equal(M.buildIgnoredSummary(eq(1, ignoredCmds.slice(0, 3))).text,
      '3 commandes ignorées, sans équivalent dans Home Assistant : Pinguer nœud, Soigner nœud, Réveiller nœud');
    assert.equal(M.buildIgnoredSummary(eq(1, [cmd(1, READY)])).count, 0);
    assert.equal(M.buildIgnoredSummary(eq(1, ignoredCmds.slice(0, 1))).text,
      '1 commande ignorée, sans équivalent dans Home Assistant : Pinguer nœud');
  });

  it('ha_component_not_in_product_scope porte la mention « non pris en charge par le plugin »', () => {
    const scope = cmd(20, view('ha_component_not_in_product_scope', false, false), false, 'Mode spécial');
    const summary = M.buildIgnoredSummary(eq(1, [scope, ignoredCmds[0]]));
    assert.match(summary.text, /non pris en charge par le plugin/);
    assert.equal(summary.items.find((i) => i.name === 'Mode spécial').not_supported_by_plugin, true);
    assert.equal(summary.items.find((i) => i.name === 'Pinguer nœud').not_supported_by_plugin, false);
    assert.doesNotMatch(M.buildIgnoredSummary(eq(1, ignoredCmds)).text, /non pris en charge par le plugin/);
  });
});

describe('25.1 / AC8 — domaine HA traduit, terme technique en petit', () => {
  it('table de traduction testée pour les huit types', () => {
    const expected = {
      light: 'Lumière', switch: 'Interrupteur', sensor: 'Capteur', binary_sensor: 'Capteur binaire',
      cover: 'Volet', climate: 'Thermostat', button: 'Bouton', alarm_control_panel: 'Alarme',
    };
    for (const [type, label] of Object.entries(expected)) {
      assert.deepEqual(M.translateHaDomain(type), { label, technical: type });
    }
  });

  it('type inconnu ou absent : le terme technique seul / un libellé neutre', () => {
    assert.deepEqual(M.translateHaDomain('fan'), { label: 'fan', technical: '' });
    assert.deepEqual(M.translateHaDomain(null), { label: 'Entité Home Assistant', technical: '' });
  });
});
