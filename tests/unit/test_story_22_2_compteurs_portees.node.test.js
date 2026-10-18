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

describe('22.2 / AC2 (25.1) — état et compteurs de l’équipement déplié', () => {
  const stateOf = (ui, id) => ui.$(`.j2ha-eq-panel[data-eq-id="${id}"] .j2ha-eq-head-state`).text().trim();

  it('chaque équipement déplié affiche son état puis ses commandes publiées / bloquées', () => {
    const t = tree(1, [READY, READY, REFUSED], { present: true });
    t.entities = [entity('light', [100, 101], { override_pending: true })];
    const ui = openRoomWith([ok(t), ok(tree(2, [DISABLED], { present: false }))]);
    assert.equal(stateOf(ui, 1), 'À appliquer', 'le réglage de l’entité attend d’être appliqué');
    assert.deepEqual(labelsOf(ui, '.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-counter'), ['2 publiées', '1 bloquée']);
    // La pièce garde ses compteurs propres, par état d’équipement : un chiffre et un mot.
    assert.deepEqual(ui.$('.j2ha-room-counter').list.map((el) => ui.$(el).text().trim()), ['1 à appliquer', '1 désactivé']);
  });

  it('un équipement désactivé le dit dans sa ligne ; une lecture en échec la vide', () => {
    const ui = openRoomWith([ok(tree(1, [READY], { present: true })), ok(tree(2, [DISABLED], { present: false }))]);
    assert.equal(stateOf(ui, 2), 'Désactivé');
    ui.click('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-republish');
    ui.respond('executeHaAction', { state: 'ok', result: null });
    ui.fail('getMappingOverrides');
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-counter').length, 0, 'plus de compteur sur un arbre périmé');
    assert.equal(stateOf(ui, 1), '', 'ni d’état périmé');
  });

  it('démon plus ancien (champ absent) : présence dite inconnue, rien n’est compté publié', () => {
    const old = tree(1, [READY], { sync: { override_pending: false } });
    const ui = openRoomWith([ok(old), ok(tree(2, [READY]))]);
    assert.match(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-counter-line').text(), /présence dans Home Assistant inconnue/);
    assert.ok(!labelsOf(ui, '.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-counter').some((text) => /publiée/.test(text)));
    assert.equal(stateOf(ui, 1), 'À appliquer', 'jamais « Publié » (R6)');
  });
});

describe('22.2 / AC3 (25.1) — portée du réglage de publication et masquage des doublons', () => {
  const segments = (ui, scope) => ui.$(scope + ' .j2ha-seg-btn').list.map((b) => plain(ui.$(b).text()));
  const active = (ui, scope) => ui.$(scope + ' .j2ha-seg-active').list.map((b) => b.attrs['data-value']);
  const EQUIPMENT = '.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-controls';
  const GROUPS = '.j2ha-eq-panel[data-eq-id="1"] .j2ha-group-head';

  it('équipement à une seule entité : un seul contrôle (équipement), aucun en-tête de groupe en doublon', () => {
    const t = tree(1, [READY], { entities: [entity('light', [100])] });
    const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
    assert.deepEqual(segments(ui, EQUIPMENT), ['Automatique', 'Toujours', 'Jamais']);
    assert.deepEqual(active(ui, EQUIPMENT), ['auto']);
    assert.equal(ui.$(GROUPS).length, 0, 'l’en-tête de groupe n’est pas rendu');
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-group-head .j2ha-seg-btn').length, 0);
  });

  it('équipement multi-entités : chaque entité a son contrôle compact, dans son en-tête de groupe', () => {
    const t = tree(1, [READY, READY], { entities: [entity('switch', [100]), entity('sensor', [101])] });
    const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
    const heads = ui.$(GROUPS).list;
    assert.equal(heads.length, 2);
    for (const head of heads) {
      const labels = ui.$(head).find('.j2ha-seg-btn').list.map((b) => plain(ui.$(b).text()));
      assert.deepEqual(labels, ['Automatique', 'Toujours', 'Jamais']);
      assert.ok(ui.$(head).find('.j2ha-seg-compact').length === 1);
    }
    assert.equal(ui.$(EQUIPMENT + ' .j2ha-seg-btn').length, 3, 'et le contrôle de l’équipement reste unique');
  });

  it('une exclusion ou un forçage posé sur la commande de l’entité garde son contrôle (non équivalent)', () => {
    const expected = { exclude_command: 'never', force_publish: 'always' };
    for (const policy of ['exclude_command', 'force_publish']) {
      const t = tree(1, [READY], { entities: [entity('light', [100], { publication_override: policy })] });
      const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
      assert.equal(ui.$(GROUPS).length, 1, policy);
      assert.deepEqual(active(ui, GROUPS), [expected[policy]], policy);
    }
  });

  it('un veto ou un forçage posé sur l’équipement : le contrôle d’entité (inerte) est masqué, celui de l’équipement le montre', () => {
    const veto = tree(1, [READY], { entities: [entity('light', [100], { publication_override: 'exclude_eqlogic' })] });
    const forced = tree(1, [READY], { entities: [entity('light', [100], { publication_override: 'force_publish' })] });
    forced.equipment_publication_override = 'force_publish';
    for (const [t, value] of [[veto, 'never'], [forced, 'always']]) {
      const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
      assert.equal(ui.$(GROUPS).length, 0);
      assert.deepEqual(active(ui, EQUIPMENT), [value]);
    }
  });

  it('segment actif : exclu → « Jamais », forcé → « Toujours », sinon « Automatique » (équipement)', () => {
    const excluded = tree(1, [READY]);
    excluded.equipment_publication_override = 'exclude';
    const forced = tree(1, [READY]);
    forced.equipment_publication_override = 'force_publish';
    for (const [t, value] of [[excluded, 'never'], [forced, 'always'], [tree(1, [READY]), 'auto']]) {
      const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
      assert.deepEqual(active(ui, EQUIPMENT), [value]);
    }
  });

  it('mêmes routes : les segments d’équipement et d’entité n’ont pas changé de requête', () => {
    // Rien de publié : « Jamais » part sans confirmation, la requête est directement observable.
    const t = tree(1, [REFUSED, REFUSED], { decision: REFUSED, entities: [
      entity('switch', [100], { decision: REFUSED }), entity('sensor', [101], { decision: REFUSED })] });
    const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
    const eqSegment = ui.$(EQUIPMENT + ' .j2ha-seg-never').list[0];
    eqSegment.handlers.click.call(eqSegment);
    const call = ui.pending('savePublicationOverride')[0];
    assert.deepEqual([call.data.eqId, call.data.publicationPolicy, call.data.cmdId], [1, 'exclude', undefined]);
    call.respond({ state: 'ok', result: null });
    const entitySegment = ui.$(GROUPS + ' .j2ha-seg-never').list[0];
    entitySegment.handlers.click.call(entitySegment);
    const entityCall = ui.pending('savePublicationOverride')[0];
    assert.deepEqual([entityCall.data.eqId, entityCall.data.publicationPolicy, entityCall.data.cmdId], [1, 'exclude', 100]);
    entityCall.respond({ state: 'ok', result: null });
    // « Automatique » : même route de retrait qu'avant, portée équipement (sans cmdId) puis entité (cmdId).
    const forcedTree = tree(1, [REFUSED], { decision: REFUSED, entities: [entity('switch', [100], { decision: REFUSED, publication_override: 'exclude_command' })] });
    const ui2 = openRoomWith([ok(forcedTree), ok(tree(2, [READY]))]);
    const revert = ui2.$(GROUPS + ' .j2ha-seg-auto').list[0];
    revert.handlers.click.call(revert);
    const revertCall = ui2.pending('revertPublicationOverride')[0];
    assert.deepEqual([revertCall.data.eqId, revertCall.data.cmdId], [1, 100]);
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
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate').text(), '{{Supprimer de Home Assistant…}}');
    assert.equal(ui.$('.j2ha-room-recreate').text().trim(), '{{Supprimer de Home Assistant…}}');
    for (const selector of ['.j2ha-room-recreate', '.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-recreate']) {
      ui.click(selector);
      const { options } = ui.lastConfirmation();
      assert.match(options.message, /Rien n.est recréé automatiquement/);
      assert.match(options.message, /« Republier »/);
      assert.equal(options.buttons.confirm.className, 'btn-danger');
      assert.doesNotMatch(options.message, /Supprimer de Home Assistant…/, 'la confirmation ne répète pas l’ellipse du menu');
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

describe('22.2 / AC5 (CC-58) — réglage « Type HA » d’une commande portée par deux entités', () => {
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

  const typeLink = (ui, cmdId) => ui.$(`.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="${cmdId}"] .j2ha-type-link`);

  it('indisponible avec explication sur la commande partagée ; ouvrable sur la commande d’une seule entité', () => {
    const ui = openRoomWith([ok(tree579()), ok(tree(2, [READY]))]);
    const shared = typeLink(ui, 105);
    assert.ok(shared.hasClass('j2ha-type-unavailable'));
    assert.equal(shared.attr('aria-disabled'), 'true');
    // Formulation toujours vraie, y compris quand l'entité principale est elle-même publiée.
    assert.equal(shared.attr('title'), 'Cette commande est portée par plusieurs entités : le type Home Assistant choisi ne s’appliquerait qu’à l’entité principale de l’équipement. Réglage indisponible ici.');
    assert.doesNotMatch(shared.attr('title'), /celle qui est publiée/);
    const own = typeLink(ui, 106);
    assert.ok(!own.hasClass('j2ha-type-unavailable'));
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="106"] select').length, 0, 'le sélecteur n’est pas rendu en permanence');
    ui.click('.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="106"] .j2ha-type-link');
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="106"] select').length, 1, 'ouvert par le lien');
  });

  it('R1 : indisponible aussi quand l’entité principale est elle-même publiée, avec la même explication', () => {
    const t = tree(1, [READY], { entities: [
      entity('switch', [105], { present_in_ha: true }),
      entity('binary_sensor', [105], { present_in_ha: true }),
    ] });
    t.commands = [{ jeedom_cmd_id: 105, cmd_name: 'Etat', covered: true, diagnostic: READY, published_in_ha: true }];
    const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
    const shared = typeLink(ui, 105);
    assert.ok(shared.hasClass('j2ha-type-unavailable'));
    assert.match(shared.attr('title'), /portée par plusieurs entités/);
    assert.doesNotMatch(shared.attr('title'), /pas à celle qui est publiée/);
  });

  it('aucun aperçu ni enregistrement n’est émis depuis le réglage indisponible', () => {
    const ui = openRoomWith([ok(tree579()), ok(tree(2, [READY]))]);
    const shared = typeLink(ui, 105).list[0];
    assert.equal(shared.handlers.click, undefined);
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="105"] select').length, 0);
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

describe('22.2 / CC-60 — cause lisible d’un type refusé sur la forme « 380 »', () => {
  // Vue `overridden` rendue par le démon pour `sensor`/`binary_sensor` sur une commande d'état d'un
  // cover orphelin : projection invalide (`ha_missing_state_topic`), publication `ambiguous_skipped`.
  const refusedByProjection = {
    ha_entity_type: 'sensor', confidence: 'ambiguous', reason_code: 'state_orphan',
    projection_validity: { is_valid: false, reason_code: 'ha_missing_state_topic', missing_capabilities: ['has_state'], missing_fields: ['state_topic'] },
    should_publish: false, publication_reason: 'ambiguous_skipped',
  };

  it('la cause affichée reste « précisez les types génériques dans Jeedom »', () => {
    assert.equal(M.buildPublishCellLabel(refusedByProjection),
      'Bloquée → type Home Assistant ambigu — précisez les types génériques dans Jeedom');
  });

  it('la liste complète de l’interface reste celle du registre (le filtre est fait par le démon)', () => {
    assert.deepEqual(M.getHaEntityTypeOptions(), [
      'alarm_control_panel', 'binary_sensor', 'button', 'climate', 'cover', 'light', 'sensor', 'switch',
    ]);
  });
});

describe('22.2 / AC7 — actions globales du bandeau (relecture Codex)', () => {
  const fs = require('node:fs');
  it('« Republier » et « Supprimer » globaux relisent le bandeau aussi en cas d’erreur', () => {
    const home = fs.readFileSync('desktop/js/jeedom2ha.js', 'utf8');
    for (const fn of ['triggerPublierAction', 'triggerSupprimerAction']) {
      const body = home.match(new RegExp('function ' + fn + '[\\s\\S]*?\\n\\}'))[0];
      const onError = body.match(/onError: function\(message\) \{[\s\S]*?\n    \},/)[0];
      assert.match(onError, /refreshBridgeStatus\(\)/, fn);
    }
  });

  it('exécution réelle : erreur réseau de « Republier dans Home Assistant » → bandeau relu', () => {
    const ui = openRoomWith([ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    const before = ui.calls.filter((c) => c.action === 'getBridgeStatus').length;
    ui.click('.j2ha-ha-action[data-ha-action="republier"]');
    ui.lastConfirmation().options.buttons.confirm.callback();
    ui.fail('executeHaAction');
    assert.equal(ui.calls.filter((c) => c.action === 'getBridgeStatus').length, before + 1);
  });
});

describe('22.2 R2 / AC6 — liste « Type HA » filtrée par le démon', () => {
  const FULL = ['alarm_control_panel', 'binary_sensor', 'button', 'climate', 'cover', 'light', 'sensor', 'switch'];
  const row = (extra) => Object.assign({
    jeedom_cmd_id: 2971, cmd_name: 'Etat', covered: true, diagnostic: REFUSED, generic_type: 'FLAP_STATE',
  }, extra || {});
  // Le sélecteur n'existe qu'après un clic sur le lien « auto » / « imposé (…) » de la commande.
  const optionValues = (ui, cmdId) => {
    ui.click(`.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="${cmdId}"] .j2ha-type-link`);
    return ui.$(`.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="${cmdId}"] option`).list.map((o) => o.attrs.value);
  };

  it('pur : seuls les types annoncés sont proposés, dans l’ordre de la liste d’interface', () => {
    assert.deepEqual(M.getOverrideTypeOptions(row({ override_types_allowed: ['sensor', 'cover', 'light'] })), ['cover', 'light', 'sensor']);
    assert.deepEqual(M.getOverrideTypeOptions(row({ override_types_allowed: ['cover'] })), ['cover']);
  });

  it('pur : champ absent (démon plus ancien) → liste complète d’avant', () => {
    assert.deepEqual(M.getOverrideTypeOptions(row()), FULL);
    assert.equal(M.getOverrideSelectorState(row()).active, true);
  });

  it('pur : un type déjà posé reste affiché même s’il ne peut plus aboutir', () => {
    const r = row({ override_types_allowed: ['cover'], override_applied: true, effective_ha: 'sensor' });
    assert.deepEqual(M.getOverrideTypeOptions(r), ['cover', 'sensor']);
    assert.equal(M.getOverrideSelectorState(r).active, true);
  });

  it('pur : aucun type → sélecteur désactivé, explication qui renvoie à Jeedom ; actif si un type est posé', () => {
    const none = M.getOverrideSelectorState(row({ override_types_allowed: [] }));
    assert.equal(none.active, false);
    assert.match(none.reason, /précisez les types génériques dans Jeedom/);
    const posed = M.getOverrideSelectorState(row({ override_types_allowed: [], override_applied: true, effective_ha: 'sensor' }));
    assert.equal(posed.active, true);
  });

  it('rendu : le sélecteur de la commande 2971 ne propose ni sensor ni binary_sensor, mais « auto » et cover', () => {
    const t = tree(1, [REFUSED, READY]);
    t.commands[0] = row({ jeedom_cmd_id: 100, override_types_allowed: ['cover'] });
    t.commands[1].override_types_allowed = FULL.slice();
    const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
    assert.deepEqual(optionValues(ui, 100), ['', 'cover']);
    assert.deepEqual(optionValues(ui, 101), ['', ...FULL]);
    assert.notEqual(ui.$('.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="100"] select').prop('disabled'), true);
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="100"] option').list[0].children[0].text, '{{auto}}');
  });

  it('rendu : liste vide → réglage indisponible avec l’explication ; champ absent → liste d’avant', () => {
    const t = tree(1, [REFUSED, REFUSED]);
    t.commands[0].override_types_allowed = [];
    const ui = openRoomWith([ok(t), ok(tree(2, [READY]))]);
    const disabled = ui.$('.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="100"] .j2ha-type-link');
    assert.ok(disabled.hasClass('j2ha-type-unavailable'));
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="1"] tr[data-cmd-id="100"] select').length, 0);
    assert.match(disabled.attr('title'), /précisez les types génériques dans Jeedom/);
    assert.deepEqual(optionValues(ui, 101), ['', ...FULL]);
  });
});
