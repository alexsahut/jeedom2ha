// ARTEFACT — Story 22.2 : compteurs fondés sur la présence dans HA (AC1, AC2), portée des actions
// et masquage des doublons (AC3), libellé « Supprimer de Home Assistant » (AC4), sélecteur
// « Override HA » désactivé sur une commande portée par deux entités (AC5), bandeau rafraîchi après
// un échec (AC7). Exécute le VRAI code de l'interface sur un faux DOM ; identifiants génériques
// uniquement (CC-48).
'use strict';

const fs = require('node:fs');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const { createUi, tree, ok, READY, DISABLED, BRIDGE_UP, view } = require('./helpers/ui_harness');

const REFUSED = view('ambiguous_skipped', false, false);
const ROOM = { object_id: 7, object_name: 'Zone', equipments: [
  { eq_id: 1, eq_name: 'Eq 1', enabled: true },
  { eq_id: 2, eq_name: 'Eq 2', enabled: true },
] };

function openRoomWith(trees) {
  const ui = createUi([ROOM]);
  ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
  ui.openRoom(7);
  trees.forEach((t) => ui.respond('getMappingOverrides', t));
  return ui;
}

const entity = (type, ids, extra) => Object.assign({
  ha_entity_type: type, command_ids: ids, decision: READY, publication_override: null,
  override_command_id: ids[0], override_pending: false, present_in_ha: true,
}, extra || {});

const plain = (text) => text.replace(/\{\{|\}\}/g, '');
const labelsOf = (ui, selector) => ui.$(selector).list.map((el) => ui.$(el).text());

describe('22.2 / AC2 — compteurs de l’équipement déplié', () => {
  it('chaque équipement déplié affiche ses commandes publiées / en attente / non prises en charge', () => {
    const t = tree(1, [READY, READY, REFUSED], { present: true });
    t.commands[2].published_in_ha = false;
    t.entities = [entity('light', [100, 101], { override_pending: true })];
    const ui = openRoomWith([ok(t), ok(tree(2, [DISABLED], { present: false }))]);
    assert.deepEqual(labelsOf(ui, '.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-counter'), [
      '2 commandes publiées dans Home Assistant',
      '2 commandes en attente d’application',
      '1 commande non prise en charge',
    ]);
    // La pièce garde ses compteurs propres, en plus.
    assert.equal(ui.$('.j2ha-room-counter').length, 8);
  });

  it('un équipement désactivé le dit dans sa ligne ; une lecture en échec la vide', () => {
    const ui = openRoomWith([ok(tree(1, [READY], { present: true })), ok(tree(2, [DISABLED], { present: false }))]);
    assert.ok(labelsOf(ui, '.j2ha-eq-panel[data-eq-id="2"] .j2ha-eq-counter').includes('équipement désactivé dans Jeedom'));
    ui.click('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-republish');
    ui.respond('executeHaAction', { state: 'ok', result: null });
    ui.fail('getMappingOverrides');
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-counter').length, 0, 'plus de compteur sur un arbre périmé');
  });

  it('démon plus ancien (champ absent) : présence dite inconnue, rien n’est compté publié', () => {
    const old = tree(1, [READY], { sync: { override_pending: false } });
    const ui = openRoomWith([ok(old), ok(tree(2, [READY]))]);
    assert.match(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-counter-line').text(), /présence dans Home Assistant inconnue/);
    assert.ok(labelsOf(ui, '.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-counter').includes('0 commande publiée dans Home Assistant'));
  });
});

describe('22.2 / AC3 — portée des actions et masquage des doublons', () => {
  const buttonLabels = (ui, scope) => ui.$(scope + ' .j2ha-publication-actions button').list.map((b) => ui.$(b).text());

  it('équipement à une seule entité : actions d’équipement nommées, actions d’entité masquées', () => {
    const t = tree(1, [READY], { entities: [entity('light', [100])] });
    const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
    assert.deepEqual(buttonLabels(ui, '.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-actions').map(plain), [
      'Exclure l’équipement', 'Forcer l’équipement', 'Revenir au mode automatique (équipement entier)',
    ]);
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-entity-row button').length, 0, 'aucun doublon sur la ligne d’entité');
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-entity-row').length, 1, 'la ligne d’entité reste affichée');
  });

  it('équipement multi-entités : chaque entité garde ses actions, libellées « cette entité »', () => {
    const t = tree(1, [READY, READY], { entities: [entity('switch', [100]), entity('sensor', [101])] });
    const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
    const rows = ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-entity-row').list;
    assert.equal(rows.length, 2);
    for (const row of rows) {
      const labels = ui.$(row).find('button').list.map((b) => ui.$(b).text());
      assert.equal(labels.length, 3);
      assert.ok(labels.every((l) => /cette entité/.test(plain(l))), labels.join(' | '));
      assert.deepEqual(labels.map(plain), ['Exclure cette entité', 'Forcer cette entité', 'Revenir au mode automatique (cette entité)']);
    }
  });

  it('une exclusion ou un forçage posé sur la commande de l’entité garde ses actions (non équivalent)', () => {
    for (const policy of ['exclude_command', 'force_publish']) {
      const t = tree(1, [READY], { entities: [entity('light', [100], { publication_override: policy })] });
      const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
      assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-entity-row button').length, 3, policy);
    }
  });

  it('un veto ou un forçage posé sur l’équipement : les actions d’entité (inertes) sont masquées', () => {
    const veto = tree(1, [READY], { entities: [entity('light', [100], { publication_override: 'exclude_eqlogic' })] });
    const forced = tree(1, [READY], { entities: [entity('light', [100], { publication_override: 'force_publish' })] });
    forced.equipment_publication_override = 'force_publish';
    for (const t of [veto, forced]) {
      const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
      assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-entity-row button').length, 0);
      assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-actions .j2ha-publication-actions button').length, 3);
    }
  });

  it('mêmes routes : les boutons d’équipement et d’entité n’ont pas changé de requête', () => {
    // Rien de publié : « Exclure » part sans confirmation, la requête est directement observable.
    const t = tree(1, [REFUSED, REFUSED], { decision: REFUSED, entities: [
      entity('switch', [100], { decision: REFUSED }), entity('sensor', [101], { decision: REFUSED })] });
    const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
    const eqButton = ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-actions .j2ha-publication-actions button').list[0];
    eqButton.handlers.click.call(eqButton);
    const call = ui.pending('savePublicationOverride')[0];
    assert.deepEqual([call.data.eqId, call.data.publicationPolicy, call.data.cmdId], [1, 'exclude', undefined]);
    call.respond({ state: 'ok', result: null });
    const entityButton = ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-entity-row button').list[0];
    entityButton.handlers.click.call(entityButton);
    const entityCall = ui.pending('savePublicationOverride')[0];
    assert.deepEqual([entityCall.data.eqId, entityCall.data.publicationPolicy, entityCall.data.cmdId], [1, 'exclude', 100]);
  });

  it('entityActionsDuplicateEquipment : cas stricts (pur)', () => {
    const one = (e) => ({ jeedom_eq_id: 1, entities: [e] });
    assert.equal(M.entityActionsDuplicateEquipment(one(entity('light', [1])), entity('light', [1])), true);
    assert.equal(M.entityActionsDuplicateEquipment({ jeedom_eq_id: 1, entities: [] }, null), false);
    const two = { jeedom_eq_id: 1, entities: [entity('light', [1]), entity('sensor', [2])] };
    assert.equal(M.entityActionsDuplicateEquipment(two, two.entities[0]), false);
    const cmdLevel = entity('light', [1], { publication_override: 'exclude_command' });
    assert.equal(M.entityActionsDuplicateEquipment(one(cmdLevel), cmdLevel), false);
  });
});

describe('22.2 / AC4 — « Supprimer de Home Assistant »', () => {
  const sources = ['desktop/js/jeedom2ha.js', 'desktop/js/jeedom2ha_mapping_surface.js',
    'desktop/js/jeedom2ha_mapping_override.js', 'desktop/php/jeedom2ha.php'].map((f) => [f, fs.readFileSync(f, 'utf8')]);

  it('aucun libellé de l’interface ne promet encore une recréation', () => {
    for (const [file, text] of sources) {
      assert.doesNotMatch(text, /puis recréer|Supprimer puis|fa-recycle/, file);
    }
  });

  it('boutons équipement et pièce, confirmations : libellé fidèle et rappel que « Republier » remet', () => {
    const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate').text(), '{{Supprimer de Home Assistant}}');
    assert.equal(ui.$('.j2ha-room-recreate').text().trim(), '{{Supprimer la pièce de Home Assistant}}');
    for (const selector of ['.j2ha-room-recreate', '.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate']) {
      ui.click(selector);
      const { options } = ui.lastConfirmation();
      assert.match(options.message, /Rien n.est recréé automatiquement/);
      assert.match(options.message, /« Republier »/);
      assert.equal(options.buttons.confirm.className, 'btn-danger');
      options.buttons.cancel.callback();
    }
  });

  it('le comportement du démon est inchangé : même intention « supprimer », aucune publication enchaînée', () => {
    const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    ui.click('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate');
    ui.lastConfirmation().options.buttons.confirm.callback();
    const call = ui.pending('executeHaAction')[0];
    assert.deepEqual([call.data.intention, call.data.portee, call.data.selection], ['supprimer', 'equipement', '[1]']);
    ui.respond('executeHaAction', { state: 'ok', result: { payload: { resultat: 'succes', message: 'Fait.' } } });
    assert.equal(ui.calls.filter((c) => c.action === 'executeHaAction').length, 1, 'aucune seconde action (pas de republication)');
  });
});

describe('22.2 / AC5 (CC-58) — sélecteur « Override HA » d’une commande portée par deux entités', () => {
  // Forme « 579 » : la commande d’état 105 est portée par le principal (refusé) et par un secondaire (publié).
  function tree579() {
    const t = tree(1, [READY, READY], { entities: [
      entity('switch', [105], { decision: REFUSED, present_in_ha: false }),
      entity('binary_sensor', [105], { present_in_ha: true }),
      entity('sensor', [106]),
    ] });
    t.commands = [
      { jeedom_cmd_id: 105, cmd_name: 'Etat', covered: true, diagnostic: READY, published_in_ha: true },
      { jeedom_cmd_id: 106, cmd_name: 'Puissance', covered: true, diagnostic: READY, published_in_ha: true },
    ];
    return t;
  }

  it('désactivé avec explication sur la commande partagée ; actif sur la commande d’une seule entité', () => {
    const ui = openRoomWith([ok(tree579()), ok(tree(2, [READY]))]);
    const shared = ui.$('.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="105"] select');
    assert.equal(shared.prop('disabled'), true);
    assert.match(shared.attr('title'), /portée par deux entités/);
    assert.match(shared.attr('title'), /entité principale/);
    const own = ui.$('.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="106"] select');
    assert.notEqual(own.prop('disabled'), true);
  });

  it('aucun aperçu ni enregistrement n’est émis depuis le sélecteur désactivé', () => {
    const ui = openRoomWith([ok(tree579()), ok(tree(2, [READY]))]);
    const shared = ui.$('.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="105"] select').list[0];
    assert.equal(shared.handlers.change, undefined);
    assert.equal(ui.pending('previewMappingOverride').length + ui.pending('saveMappingOverride').length, 0);
  });

  it('le retrait d’un override existant reste possible (lien ↺)', () => {
    const t = tree579();
    t.commands[0].override_applied = true;
    t.commands[0].effective_ha = 'binary_sensor';
    const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="105"] .mo-revert-cmd').length, 1);
  });

  it('pur : sans arbre d’entités, comportement d’avant 22.2', () => {
    assert.equal(M.getOverrideSelectorState({ jeedom_cmd_id: 105, diagnostic: READY, covered: true }).active, true);
    assert.equal(M.countEntitiesCarryingCommand([{ command_ids: [105] }, { command_ids: [105, 1] }], 105), 2);
  });
});

describe('22.2 / AC7 (P3 de 20-3) — bandeau de santé relu après un échec de « Republier »', () => {
  const bridgeCalls = (ui) => ui.calls.filter((c) => c.action === 'getBridgeStatus').length;

  it('« Republier » d’un équipement : échec du démon, réponse refusée ou réseau tombé → bandeau relu', () => {
    for (const outcome of [
      { kind: 'respond', body: { state: 'ok', result: { payload: { resultat: 'echec', message: 'Échec.' } } } },
      { kind: 'respond', body: { state: 'ok', result: { status: 'error', message: 'Refusé' } } },
      { kind: 'fail' },
    ]) {
      const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
      const before = bridgeCalls(ui);
      ui.click('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-republish');
      if (outcome.kind === 'fail') ui.fail('executeHaAction'); else ui.respond('executeHaAction', outcome.body);
      assert.equal(bridgeCalls(ui), before + 1, JSON.stringify(outcome));
    }
  });

  it('action de pièce en échec réseau : bandeau relu', () => {
    const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    const before = bridgeCalls(ui);
    ui.click('.j2ha-room-republish');
    ui.lastConfirmation().options.buttons.confirm.callback();
    ui.fail('executeHaAction');
    assert.equal(bridgeCalls(ui), before + 1);
  });

  it('succès : le bandeau n’est relu qu’une fois', () => {
    const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    const before = bridgeCalls(ui);
    ui.click('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-republish');
    ui.respond('executeHaAction', { state: 'ok', result: { payload: { resultat: 'succes', message: 'Fait.' } } });
    assert.equal(bridgeCalls(ui), before + 1);
  });
});

describe('22.2 — fausse DOM : le texte analysé depuis du HTML est décodé comme dans un navigateur', () => {
  it('.text() rend le texte d’origine, jamais son échappement', () => {
    const { createDom } = require('./helpers/fake_dom');
    const dom = createDom();
    assert.equal(dom.$('<span>').text('a < b').html(), 'a &lt; b');
    const el = dom.$('<p></p>').html('x &lt;b&gt; &amp; y');
    assert.equal(el.text(), 'x <b> & y');
  });
});

describe('22.2 / CC-60 — cause lisible d’un type refusé sur la forme « 380 » (liste non filtrée dans cette story)', () => {
  // Vue `overridden` rendue par le démon pour `sensor`/`binary_sensor` sur une commande d'état d'un
  // cover orphelin : projection invalide (`ha_missing_state_topic`), publication `ambiguous_skipped`.
  const refusedByProjection = {
    ha_entity_type: 'sensor', confidence: 'ambiguous', reason_code: 'state_orphan',
    projection_validity: { is_valid: false, reason_code: 'ha_missing_state_topic', missing_capabilities: ['has_state'], missing_fields: ['state_topic'] },
    should_publish: false, publication_reason: 'ambiguous_skipped',
  };

  it('la cause affichée reste « précisez les types génériques dans Jeedom »', () => {
    assert.equal(M.buildPublishCellLabel(refusedByProjection),
      'Ne sera pas publié — type Home Assistant ambigu — précisez les types génériques dans Jeedom');
  });

  it('AC6 en attente de décision : la liste « Override HA » n’est pas modifiée par cette story', () => {
    assert.deepEqual(M.getHaEntityTypeOptions(), [
      'alarm_control_panel', 'binary_sensor', 'button', 'climate', 'cover', 'light', 'sensor', 'switch',
    ]);
  });
});
