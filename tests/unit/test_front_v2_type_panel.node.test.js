// Front v2 — Lot 5 : « Corriger le type » avec aperçu, annulation et garde-fous (écran E5).
// Module pur (jeedom2ha_type_panel.js) et VRAI code de la surface sur le faux DOM (ui_harness) : un choix ne fait qu'un aperçu,
// « Enregistrer et publier » enchaîne l'enregistrement et la publication de l'équipement (corps inchangés), le bandeau
// « … · Annuler » rétablit le réglage précédent, les erreurs réseau sont dites, le minuteur est annulé à la fermeture.
// Politique du gate : seule la publication d'un équipement DÉCLARÉ est simulée. Données fictives (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const TP = require('../../desktop/js/jeedom2ha_type_panel.js');
const { createUi, BRIDGE_UP } = require('./helpers/ui_harness');
const { ACTION_OK } = require('./helpers/write_scenarios');
const { DEMO, demoRoom, diag } = require('./helpers/front_v2_demo_trees');

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const plain = (text) => String(text).replace(/\{\{|\}\}/g, '').replace(/\s+/g, ' ').trim();
const READY_LIGHT = diag('sure', { valid: true, publish: true, type: 'light', code: 'sure_mapping' });

/** Lampe typée « prise » (démo du Lot 2) avec la liste des types que le démon accepte pour chaque commande. */
function lampe(allowed) {
  const t = DEMO.lampePrise(true);
  t.commands.forEach((c) => { c.override_types_allowed = (allowed || ['light', 'switch']).slice(); });
  return t;
}

/** Même lampe, bloquée cette fois par « un état sans ordre On / Off » (cause qui garde « Corriger le type… »). */
function orphan() {
  const t = lampe();
  const d = () => diag('ambiguous_skipped', { code: 'switch_state_orphan', type: 'switch', validity: 'ha_missing_command_topic' });
  t.commands.forEach((c) => { c.diagnostic = d(); });
  t.entities[0].decision = d();
  t.equipment_decision = d();
  t.hints = [];
  return t;
}

/** Avant PUBLIÉ (un interrupteur et un capteur dans Home Assistant), pour les cas de changement d'identifiant. */
const PUBLISHED_BEFORE = [
  { ha_entity_type: 'switch', ha_unique_id: 'jeedom2ha_eq_231', ha_default_entity_id: 'switch.jeedom2ha_eq_231',
    ha_controllable: true, ha_capabilities: ['on_off'], will_publish: true, reason: 'sure' },
  { ha_entity_type: 'sensor', ha_unique_id: 'jeedom2ha_231_9', ha_default_entity_id: 'sensor.jeedom2ha_231_9',
    ha_controllable: false, ha_capabilities: ['read'], will_publish: true, reason: 'sure' },
];
const ID_CHANGES = [{ from: 'switch.jeedom2ha_eq_231', to: 'light.jeedom2ha_eq_231' }, { from: 'sensor.jeedom2ha_231_9', to: null }];

/** Réponse d'aperçu du démon (Lot 3) pour la lampe passée en lumière. */
function previewLight(extra) {
  return { state: 'ok', result: { status: 'ok', payload: Object.assign({
    jeedom_eq_id: 231, mapped: true, covered: true,
    auto: lampe().equipment_decision,
    overridden: READY_LIGHT,
    entities_before: [{ ha_entity_type: 'switch', ha_unique_id: 'jeedom2ha_eq_231', ha_name: 'Lampe Chevet',
      ha_default_entity_id: 'switch.jeedom2ha_eq_231', ha_controllable: true, ha_capabilities: ['on_off'], will_publish: false, reason: 'ambiguous_skipped' }],
    entities_after: [{ ha_entity_type: 'light', ha_unique_id: 'jeedom2ha_eq_231', ha_name: 'Lampe Chevet',
      ha_default_entity_id: 'light.jeedom2ha_eq_231', ha_controllable: true, ha_capabilities: ['on_off', 'read'], will_publish: true, reason: 'sure' }],
    entity_id_changes: [{ from: null, to: 'light.jeedom2ha_eq_231' }],
  }, extra || {}) } };
}

function openFiche(tree) {
  const ui = createUi([demoRoom()], { pluginNames: { virtual: 'Virtuel' } });
  ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
  ui.openRoomWith(9, [{ state: 'ok', result: { payload: tree } }]);
  const P = `.j2ha-eq-panel[data-eq-id="${tree.jeedom_eq_id}"] `;
  const text = (selector) => plain(ui.$(P + selector).text());
  const panel = (cmdId) => `${P}tr[data-type-panel-for="${cmdId}"] `;
  const choose = (cmdId, type) => ui.$(`${panel(cmdId)}input[data-type="${type}"]`).trigger('change');
  const done = () => ui.win.Jeedom2haSurface.clearEquipment();
  return { ui, P, text, panel, choose, done };
}

const WRITES = ['saveMappingOverride', 'revertMappingOverride', 'savePublicationOverride', 'revertPublicationOverride', 'executeHaAction'];
const writes = (ui) => ui.calls.filter((c) => WRITES.includes(c.action));

describe('Lot 5 — module pur : choix possibles et impossibles', () => {
  it('serrure et vanne entrent dans la liste (ajouts seuls) avec leur libellé français', () => {
    assert.ok(M.getHaEntityTypeOptions().includes('lock') && M.getHaEntityTypeOptions().includes('valve'));
    assert.equal(M.formatHaDomain('lock'), 'Serrure (lock)');
    assert.equal(M.formatHaDomain('valve'), 'Vanne (valve)');
    assert.equal(TP.typeLabel('light'), 'Lumière (light)');
  });

  it('types annoncés par le démon proposés, les autres visibles et grisés avec leur raison', () => {
    const row = lampe().commands[0];
    const { current, choices } = TP.buildChoices(row);
    assert.equal(current, null);
    assert.deepEqual(choices.filter((c) => !c.disabled).map((c) => c.value), ['', 'light', 'switch']);
    assert.equal(choices[0].label, 'Automatique');
    assert.match(choices[0].hint, /aujourd’hui : non publié/);
    assert.ok(choices[0].checked);
    // Revue du Lot 5 : le démon dit QUE le type est refusé, pas POURQUOI. Aucune raison devinée : une seule phrase vraie
    // pour tous (jamais « il faut une commande d'état » sur une commande d'état, par exemple).
    for (const type of ['button', 'cover', 'binary_sensor', 'sensor']) {
      const c = choices.find((x) => x.value === type);
      assert.equal(c.disabled, true, type);
      assert.equal(c.reason, 'non proposé par le plugin pour cette commande', type);
    }
    assert.equal(choices.length, 1 + M.getHaEntityTypeOptions().length, 'tous les types restent visibles');
    // Ordre : Automatique, possibles, puis impossibles.
    const firstDisabled = choices.findIndex((c) => c.disabled);
    assert.ok(choices.slice(firstDisabled).every((c) => c.disabled));
  });

  it('démon plus ancien (champ absent) : liste complète, rien de grisé', () => {
    const row = DEMO.lampePrise(false).commands[0];
    assert.ok(TP.buildChoices(row).choices.every((c) => !c.disabled));
  });

  // Garde levée (front v2, Lot 9a, regard neuf v2) : « auto » ne se devinait pas cliquable ; le lien dit « Automatique ».
  it('type déjà personnalisé : coché, et proposé même s’il n’est plus annoncé', () => {
    const row = Object.assign(lampe(['switch']).commands[0], { override_applied: true, effective_ha: 'light' });
    const built = TP.buildChoices(row);
    assert.equal(built.current, 'light');
    assert.ok(built.choices.find((c) => c.value === 'light').checked);
    assert.equal(built.choices.find((c) => c.value === 'light').disabled, false);
    assert.equal(TP.cellLabel(row), 'Personnalisé : Lumière (light)');
    assert.equal(TP.cellLabel({ override_applied: false }), 'Automatique');
  });

  it('vanne et serrure proposées quand le démon les autorise', () => {
    const row = { jeedom_cmd_id: 1, diagnostic: READY_LIGHT, covered: true, override_types_allowed: ['lock', 'valve'] };
    const offered = TP.buildChoices(row).choices.filter((c) => !c.disabled).map((c) => c.label);
    assert.deepEqual(offered, ['Automatique', 'Serrure (lock)', 'Vanne (valve)']);
  });
});

describe('Lot 5 — module pur : aperçu avant / après', () => {
  it('lampe : « Avant : Non publié · Après : 1 lumière, pilotable (allumer, éteindre) » avec l’identifiant du démon', () => {
    const diff = TP.buildDiff(previewLight());
    assert.equal(diff.source, 'entities');
    assert.equal(diff.publishable, true);
    assert.equal(diff.before.headline, 'Non publié');
    assert.equal(diff.after.headline, '1 lumière');
    assert.equal(TP.capabilityText(diff.after.published[0]), 'pilotable (allumer, éteindre)');
    assert.equal(diff.after.published[0].entity_id, 'light.jeedom2ha_eq_231');
    assert.deepEqual(diff.changes, [], 'une entité qui apparaît n’est pas un changement d’identifiant');
  });

  it('avant publié : identifiant qui change et entité qui disparaît sont signalés', () => {
    const diff = TP.buildDiff(previewLight({ entities_before: PUBLISHED_BEFORE, entity_id_changes: ID_CHANGES }));
    assert.equal(diff.before.headline, '1 interrupteur, 1 capteur');
    assert.deepEqual(diff.changes, [{ from: 'switch.jeedom2ha_eq_231', to: 'light.jeedom2ha_eq_231' }]);
    assert.deepEqual(diff.removed, ['sensor.jeedom2ha_231_9']);
  });

  it('avant NON publié : aucun changement d’identifiant signalé, même si le démon en liste un', () => {
    const diff = TP.buildDiff(previewLight({ entity_id_changes: ID_CHANGES }));
    assert.equal(diff.before.headline, 'Non publié');
    assert.deepEqual(diff.changes, []);
    assert.deepEqual(diff.removed, []);
  });

  it('repli sans entités « avant » (démon plus ancien) : aucun changement d’identifiant signalé', () => {
    const p = previewLight({ entity_id_changes: ID_CHANGES });
    delete p.result.payload.entities_before;
    assert.deepEqual(TP.buildDiff(p).changes, []);
  });

  it('choix non publiable : refus dit en clair, rien d’annoncé « après »', () => {
    const refused = diag('ambiguous_skipped', { type: 'cover', code: 'name_heuristic_rejection' });
    const diff = TP.buildDiff(previewLight({ overridden: refused }));
    assert.equal(diff.publishable, false);
    assert.match(diff.refusal, /un mot du nom de l’équipement écarte ce type/);
    assert.equal(diff.after.published.length, 0);
  });

  it('commande non couverte : jamais publiable', () => {
    const diff = TP.buildDiff({ state: 'ok', result: { payload: { covered: false, overridden: null, auto: null, entities_before: [], entities_after: null } } });
    assert.equal(diff.publishable, false);
    assert.match(diff.refusal, /pas d’équivalent dans Home Assistant/);
  });

  it('repli sans le Lot 3 : vues auto / overridden, sans identifiant deviné', () => {
    const p = previewLight();
    ['entities_before', 'entities_after', 'entity_id_changes'].forEach((k) => delete p.result.payload[k]);
    const diff = TP.buildDiff(p);
    assert.equal(diff.source, 'views');
    assert.equal(diff.before.headline, 'Non publié');
    assert.equal(diff.after.headline, '1 lumière');
    assert.equal(diff.after.published[0].entity_id, null);
    assert.equal(TP.capabilityText(diff.after.published[0]), '');
  });

  it('message du bandeau', () => {
    assert.equal(TP.resultMessage('Lampe Chevet', 'light'), 'Lampe Chevet est maintenant une lumière dans Home Assistant.');
    assert.equal(TP.resultMessage('Vanne Jardin', 'valve'), 'Vanne Jardin est maintenant une vanne dans Home Assistant.');
    assert.equal(TP.resultMessage('Lampe Chevet', null), 'Lampe Chevet : le type est revenu en automatique.');
  });

  it('point d’entrée du Lot 2 : open({ eqId, cmdIds, $panel }) délègue à la surface de la page', () => {
    const src = fs.readFileSync(path.join(__dirname, '..', '..', 'desktop/js/jeedom2ha_type_panel.js'), 'utf8');
    const seen = [];
    const root = { Jeedom2haMappingOverride: M, Jeedom2haSurface: { openTypePanel: (o) => { seen.push(o); return true; } } };
    new Function('globalThis', 'module', src)(root, undefined);
    assert.equal(root.Jeedom2haTypePanel.open({ eqId: 231, cmdIds: [2311], $panel: null }), true);
    assert.deepEqual(seen, [{ eqId: 231, cmdIds: [2311], $panel: null }]);
    assert.doesNotMatch(src, /JSON\.stringify|\$\.ajax|COMMAND_CAUSE_CATEGORIES|categoryOfCause/);
  });
});

describe('Lot 5 — surface : choix → aperçu → « Enregistrer et publier »', () => {
  it('acceptation 1 : la cellule ouvre le panneau, le choix fait un aperçu, rien n’est écrit avant le clic final', async () => {
    const { ui, P, panel, choose, done } = openFiche(lampe());
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    const box = ui.$(`${panel(2311)}.j2ha-v2-type-panel`);
    assert.equal(box.length, 1);
    // Garde levée (front v2, Lot 9a, regard neuf v2) : le choix vaut pour toute l'ENTITÉ, pas pour la commande « État » :
    // le titre nomme l'entité, la ligne suivante liste ses commandes, les types refusés sont « impossibles pour cet équipement ».
    assert.equal(plain(box.find('.j2ha-v2-type-title').text()), 'Type dans Home Assistant de « Lampe Chevet »');
    assert.equal(plain(box.find('.j2ha-v2-type-scope').text()), 'Ce choix vaut pour les commandes : État, On, Off');
    assert.equal(plain(box.find('.j2ha-v2-type-legend').text()), 'Dans Home Assistant, cette entité est :');
    assert.match(plain(box.text()), /Le plus durable est de corriger les types génériques dans Jeedom/);
    const offered = box.find('input').list.filter((i) => i.props.disabled !== true).map((i) => i.attrs['data-type']);
    assert.deepEqual(offered, ['auto', 'light', 'switch']);
    // Types refusés : repliés sous une ligne unique, noms seulement (revue du Lot 5).
    const toggle = box.find('.j2ha-v2-type-refused-toggle');
    assert.equal(plain(toggle.text()), 'Types impossibles pour cet équipement (8) ▸');
    assert.equal(toggle.attr('aria-expanded'), 'false');
    const list = box.find('.j2ha-v2-type-refused-list');
    assert.equal(list.list[0].visible, false, 'replié par défaut');
    assert.equal(box.find('input[data-type="button"]').length, 0, 'un type refusé n’est pas un choix');
    ui.click(`${panel(2311)}.j2ha-v2-type-refused-toggle`);
    assert.equal(toggle.attr('aria-expanded'), 'true');
    assert.equal(list.list[0].visible, true);
    assert.equal(plain(toggle.text()), 'Types impossibles pour cet équipement (8) ▾');
    assert.deepEqual(list.find('li').list.map((li) => plain(ui.$(li).text())), [
      'Alarme (alarm_control_panel)', 'Capteur binaire (binary_sensor)', 'Bouton (button)', 'Thermostat (climate)',
      'Volet (cover)', 'Serrure (lock)', 'Capteur (sensor)', 'Vanne (valve)']);
    assert.equal((plain(box.text()).match(/impossibles pour cet équipement/g) || []).length, 1, 'la phrase n’est dite qu’une fois');
    assert.doesNotMatch(plain(box.text()), /il faut une commande d’état|impossible :/, 'aucune raison devinée');
    assert.equal(ui.$(`${panel(2311)}.j2ha-v2-type-save`).prop('disabled'), true);

    choose(2311, 'light');
    assert.equal(ui.pending('previewMappingOverride').length, 0, 'aperçu après le délai, pas à chaque flèche');
    await sleep(450);
    const preview = ui.pending('previewMappingOverride')[0];
    assert.deepEqual({ ...preview.data }, { action: 'previewMappingOverride', eqId: 231, cmdId: 2311, haEntityType: 'light' });
    preview.respond(previewLight());
    const diffText = plain(ui.$(`${panel(2311)}.j2ha-v2-diff`).text());
    assert.match(diffText, /Avant\s*Non publié\s*Rien dans Home Assistant/);
    assert.match(diffText, /Après\s*1 lumière\s*Lumière \(light\) · pilotable \(allumer, éteindre\) · light\.jeedom2ha_eq_231/);
    assert.equal(ui.$(`${panel(2311)}.j2ha-v2-type-save`).prop('disabled'), false);
    assert.deepEqual(writes(ui), [], 'rien n’est écrit tant que l’on n’a pas validé');

    // Fermer : rien n'est écrit, la fiche reste « Bloqué ».
    ui.click(`${panel(2311)}.j2ha-v2-type-cancel`);
    assert.equal(ui.$(`${P}.j2ha-v2-type-panel`).length, 0);
    assert.deepEqual(writes(ui), []);
    assert.equal(plain(ui.$(`${P}.j2ha-eq-publish-badge`).text()), 'Bloqué');
    done();
  });

  it('acceptation 2 : « Enregistrer et publier » enchaîne enregistrement et publication, puis « Annuler » rétablit', async () => {
    const { ui, P, panel, choose, done } = openFiche(lampe());
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    choose(2311, 'light');
    await sleep(450);
    ui.respond('previewMappingOverride', previewLight());
    ui.click(`${panel(2311)}.j2ha-v2-type-save`);
    assert.equal(ui.$(`${panel(2311)}.j2ha-v2-type-save`).prop('disabled'), true, 'bouton réservé pendant l’opération');
    const save = ui.respond('saveMappingOverride', { state: 'ok', result: { status: 'ok', payload: {} } });
    assert.deepEqual({ ...save.data }, { action: 'saveMappingOverride', eqId: 231, cmdId: 2311, haEntityType: 'light' });
    const publish = ui.pending('executeHaAction')[0];
    assert.deepEqual({ ...publish.data }, { action: 'executeHaAction', intention: 'publier', portee: 'equipement', selection: '[231]' });
    assert.ok(publish.options.timeout > 0, 'délai client de la page (executeHaAction)');
    publish.respond(ACTION_OK);
    assert.equal(ui.$(`${P}.j2ha-v2-type-panel`).length, 0, 'panneau fermé');
    const toast = ui.$(`${P}.j2ha-eq-head .j2ha-v2-type-toast`);
    assert.equal(toast.length, 1);
    assert.equal(toast.attr('aria-live'), 'polite');
    assert.match(plain(toast.text()), /^Lampe Chevet est maintenant une lumière dans Home Assistant\.\s*Annuler$/);
    assert.equal(ui.pending('getMappingOverrides').length, 1, 'la fiche est relue');
    assert.equal(writes(ui).map((c) => c.action).join(','), 'saveMappingOverride,executeHaAction');

    // « Annuler » : retour en automatique (le réglage précédent) puis publication.
    ui.click(`${P}.j2ha-v2-type-undo`);
    const revert = ui.respond('revertMappingOverride', { state: 'ok', result: { status: 'ok' } });
    assert.deepEqual({ ...revert.data }, { action: 'revertMappingOverride', eqId: 231, cmdId: 2311 });
    ui.respond('executeHaAction', ACTION_OK);
    assert.match(plain(ui.$(`${P}.j2ha-v2-type-toast`).text()), /Réglage précédent rétabli\./);
    assert.equal(ui.$(`${P}.j2ha-v2-type-undo`).length, 0, 'pas d’annulation de l’annulation');
    done();
  });

  it('« Annuler » d’un type déjà personnalisé remet ce type (saveMappingOverride), pas l’automatique', async () => {
    const t = lampe();
    Object.assign(t.commands[0], { override_applied: true, effective_ha: 'switch' });
    const { ui, P, panel, choose, done } = openFiche(t);
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    assert.equal(ui.$(`${panel(2311)}input[data-type="switch"]`).prop('checked'), true);
    choose(2311, 'light');
    await sleep(450);
    ui.respond('previewMappingOverride', previewLight());
    ui.click(`${panel(2311)}.j2ha-v2-type-save`);
    ui.respond('saveMappingOverride', { state: 'ok', result: { status: 'ok' } });
    ui.respond('executeHaAction', ACTION_OK);
    ui.click(`${P}.j2ha-v2-type-undo`);
    assert.deepEqual({ ...ui.pending('saveMappingOverride')[0].data }, { action: 'saveMappingOverride', eqId: 231, cmdId: 2311, haEntityType: 'switch' });
    done();
  });

  it('« Automatique » sur un type personnalisé : revertMappingOverride puis publication, sans aperçu', () => {
    const t = lampe();
    Object.assign(t.commands[0], { override_applied: true, effective_ha: 'light' });
    const { ui, P, panel, choose, done } = openFiche(t);
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    choose(2311, 'auto');
    assert.match(plain(ui.$(`${panel(2311)}.j2ha-v2-type-preview`).text()), /le plugin choisira seul/);
    ui.click(`${panel(2311)}.j2ha-v2-type-save`);
    ui.respond('revertMappingOverride', { state: 'ok', result: { status: 'ok' } });
    ui.respond('executeHaAction', ACTION_OK);
    assert.match(plain(ui.$(`${P}.j2ha-v2-type-toast`).text()), /le type est revenu en automatique/);
    assert.equal(ui.count('previewMappingOverride'), 0);
    done();
  });

  it('choix non publiable : bouton désactivé, raison affichée', async () => {
    const { ui, P, panel, choose, done } = openFiche(lampe());
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    choose(2311, 'switch');
    await sleep(450);
    ui.respond('previewMappingOverride', previewLight({ overridden: lampe().equipment_decision, entities_after: lampe().entities.map(() => ({ ha_entity_type: 'switch', will_publish: false })) }));
    assert.match(plain(ui.$(`${panel(2311)}.j2ha-v2-type-refusal`).text()), /^Ce choix ne peut pas être publié : un mot du nom de l’équipement écarte ce type\.$/);
    assert.equal(ui.$(`${panel(2311)}.j2ha-v2-type-save`).prop('disabled'), true);
    done();
  });

  it('identifiant qui change (avant publié) : avertissement sur les automatisations à reprendre', async () => {
    const { ui, P, panel, choose, done } = openFiche(lampe());
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    choose(2311, 'light');
    await sleep(450);
    ui.respond('previewMappingOverride', previewLight({ entities_before: PUBLISHED_BEFORE.slice(0, 1), entity_id_changes: ID_CHANGES.slice(0, 1) }));
    assert.match(plain(ui.$(`${panel(2311)}.j2ha-v2-type-idchange`).text()),
      /^Attention : l’identifiant passe de switch\.jeedom2ha_eq_231 à light\.jeedom2ha_eq_231\. Les automatisations et tableaux de bord Home Assistant qui utilisent l’ancien seront à reprendre\.$/);
    done();
  });

  it('avant non publié : pas d’avertissement d’identifiant à l’écran', async () => {
    const { ui, P, panel, choose, done } = openFiche(lampe());
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    choose(2311, 'light');
    await sleep(450);
    ui.respond('previewMappingOverride', previewLight({ entity_id_changes: ID_CHANGES }));
    assert.match(plain(ui.$(`${panel(2311)}.j2ha-v2-diff`).text()), /Avant\s*Non publié/);
    assert.equal(ui.$(`${panel(2311)}.j2ha-v2-type-idchange`).length, 0);
    done();
  });
});

describe('Lot 5 — surface : erreurs, minuteur, clavier, point d’entrée', () => {
  it('acceptation 5 : coupure réseau à l’aperçu puis à l’enregistrement → message visible, rien n’est publié', async () => {
    const { ui, P, panel, choose, done } = openFiche(lampe());
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    choose(2311, 'light');
    await sleep(450);
    ui.fail('previewMappingOverride');
    assert.match(plain(ui.$(`${panel(2311)}.j2ha-v2-type-error`).text()), /L’aperçu n’a pas pu être calculé : Le démon ne répond pas\./);
    choose(2311, 'switch');
    choose(2311, 'light');
    await sleep(450);
    ui.respond('previewMappingOverride', previewLight());
    ui.click(`${panel(2311)}.j2ha-v2-type-save`);
    ui.fail('saveMappingOverride');
    assert.match(plain(ui.$(`${panel(2311)}.j2ha-v2-type-error`).text()), /Le réglage n’a pas été enregistré : Le démon ne répond pas\./);
    assert.equal(ui.$(`${panel(2311)}.j2ha-v2-type-save`).prop('disabled'), false, 'nouvel essai possible');
    assert.equal(ui.count('executeHaAction'), 0);
    done();
  });

  it('refus du démon à l’enregistrement (HTTP 200, status error) : message, panneau ouvert', async () => {
    const { ui, P, panel, choose, done } = openFiche(lampe());
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    choose(2311, 'light');
    await sleep(450);
    ui.respond('previewMappingOverride', previewLight());
    ui.click(`${panel(2311)}.j2ha-v2-type-save`);
    ui.respond('saveMappingOverride', { state: 'ok', result: { status: 'error', message: 'Commande partagée sans entité propre' } });
    assert.match(plain(ui.$(`${panel(2311)}.j2ha-v2-type-error`).text()), /Commande partagée sans entité propre/);
    done();
  });

  it('publication en échec après un enregistrement réussi : bandeau d’avertissement, « Annuler » reste offert', async () => {
    const { ui, P, panel, choose, done } = openFiche(lampe());
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    choose(2311, 'light');
    await sleep(450);
    ui.respond('previewMappingOverride', previewLight());
    ui.click(`${panel(2311)}.j2ha-v2-type-save`);
    ui.respond('saveMappingOverride', { state: 'ok', result: { status: 'ok' } });
    ui.fail('executeHaAction');
    const toast = ui.$(`${P}.j2ha-v2-type-toast`);
    assert.ok(toast.hasClass('is-warn'));
    assert.match(plain(toast.text()), /Réglage enregistré, mais la publication n’a pas abouti/);
    assert.equal(ui.$(`${P}.j2ha-v2-type-undo`).length, 1);
    done();
  });

  it('revue Codex : choix figés pendant l’enregistrement, rendus après un échec ; le nouvel essai écrit le choix affiché', async () => {
    const { ui, P, panel, choose, done } = openFiche(lampe());
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    choose(2311, 'light');
    await sleep(450);
    ui.respond('previewMappingOverride', previewLight());
    ui.click(`${panel(2311)}.j2ha-v2-type-save`);
    for (const type of ['auto', 'light', 'switch']) assert.equal(ui.$(`${panel(2311)}input[data-type="${type}"]`).prop('disabled'), true, type);
    ui.fail('saveMappingOverride');
    for (const type of ['auto', 'light', 'switch']) assert.equal(ui.$(`${panel(2311)}input[data-type="${type}"]`).prop('disabled'), false, type);
    assert.equal(ui.$(`${panel(2311)}input[data-type="button"]`).length, 0, 'un type refusé n’est jamais un choix');
    ui.click(`${panel(2311)}.j2ha-v2-type-save`);
    assert.equal(ui.pending('saveMappingOverride')[0].data.haEntityType, 'light');
    done();
  });

  it('revue Codex : la réponse d’un enregistrement sur A ne ferme ni le panneau ni le bandeau de B', async () => {
    const other = DEMO.lampePrise(true);
    other.jeedom_eq_id = 200;
    other.eq_name = 'Plafonnier Séjour';
    other.commands.forEach((c, i) => { c.jeedom_cmd_id = 2001 + i; c.override_types_allowed = ['light', 'switch']; });
    other.entities[0].command_ids = [2001, 2002, 2003];
    other.entities[0].override_command_id = 2001;
    const ui = createUi([demoRoom()], { pluginNames: { virtual: 'Virtuel' } });
    ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
    ui.openRoomWith(9, [{ state: 'ok', result: { payload: lampe() } }, { state: 'ok', result: { payload: other } }]);
    ui.click('.j2ha-eq-panel[data-eq-id="231"] tr[data-cmd-id="2311"] .j2ha-type-link');
    ui.$('tr[data-type-panel-for="2311"] input[data-type="light"]').trigger('change');
    await sleep(450);
    ui.respond('previewMappingOverride', previewLight());
    ui.click('tr[data-type-panel-for="2311"] .j2ha-v2-type-save');
    ui.show(200);
    ui.click('.j2ha-eq-panel[data-eq-id="200"] tr[data-cmd-id="2001"] .j2ha-type-link');
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="200"] .j2ha-v2-type-panel').length, 1);
    ui.respond('saveMappingOverride', { state: 'ok', result: { status: 'ok' } });
    ui.respond('executeHaAction', ACTION_OK);
    assert.equal(ui.$('.j2ha-eq-panel[data-eq-id="200"] .j2ha-v2-type-panel').length, 1, 'le panneau de B reste ouvert');
    assert.equal(ui.$('.j2ha-v2-type-toast').length, 0, 'aucun bandeau de A sur B');
    ui.win.Jeedom2haSurface.clearEquipment();
  });

  it('minuteur annulé à la fermeture : aucun aperçu ne part après « Annuler » ou Échap', async () => {
    const { ui, P, panel, choose, done } = openFiche(lampe());
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    choose(2311, 'light');
    ui.click(`${panel(2311)}.j2ha-v2-type-cancel`);
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    choose(2311, 'switch');
    ui.key(`${panel(2311)}.j2ha-v2-type-panel`, 'Escape');
    assert.equal(ui.$(`${P}.j2ha-v2-type-panel`).length, 0);
    await sleep(450);
    assert.equal(ui.count('previewMappingOverride'), 0);
    done();
  });

  it('aperçu en vol puis fermeture : la réponse tardive ne rouvre rien', async () => {
    const { ui, P, panel, choose, done } = openFiche(lampe());
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    choose(2311, 'light');
    await sleep(450);
    ui.click(`${panel(2311)}.j2ha-v2-type-cancel`);
    ui.respond('previewMappingOverride', previewLight());
    assert.equal(ui.$(`${P}.j2ha-v2-type-panel`).length, 0);
    assert.equal(ui.$(`${P}.j2ha-v2-diff`).length, 0);
    done();
  });

  it('un seul panneau à la fois ; un second clic sur le même lien le referme', () => {
    const { ui, P, done } = openFiche(lampe());
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    ui.click(`${P}tr[data-cmd-id="2312"] .j2ha-type-link`);
    assert.equal(ui.$(`${P}.j2ha-v2-type-panel`).length, 1);
    assert.equal(ui.$(`${P}tr[data-type-panel-for="2312"]`).length, 1);
    assert.equal(ui.$(`${P}tr[data-cmd-id="2312"] .j2ha-type-link`).attr('aria-expanded'), 'true');
    ui.click(`${P}tr[data-cmd-id="2312"] .j2ha-type-link`);
    assert.equal(ui.$(`${P}.j2ha-v2-type-panel`).length, 0);
    assert.equal(ui.$(`${P}tr[data-cmd-id="2312"] .j2ha-type-link`).attr('aria-expanded'), 'false');
    done();
  });

  // Garde levée (front v2, Lot 9a, point 9) : la lampe bloquée par son nom ne propose plus « Corriger le type… » (le type ne
  // lève pas ce blocage) ; la cause « état sans ordre » le garde (premier pas avant « Publier quand même »).
  it('« Corriger le type… » de la fiche de cause ouvre le panneau via la surface (point d’entrée du Lot 2)', () => {
    const { ui, P, done } = openFiche(orphan());
    ui.click(`${P}.j2ha-v2-correct-type`);
    assert.equal(ui.$(`${P}tr[data-type-panel-for="2311"] .j2ha-v2-type-panel`).length, 1);
    ui.win.Jeedom2haSurface.clearEquipment();
    assert.equal(ui.win.Jeedom2haSurface.openTypePanel({ eqId: 231, cmdIds: [2311] }), false, 'équipement fermé : rien');
    done();
  });

  it('acceptation 3 : sur une commande d’état, « Bouton (button) » refusé par le démon est listé sous « Autres types, non proposés… »', () => {
    const { ui, P, panel, done } = openFiche(lampe());
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    assert.equal(ui.$(`${panel(2311)}input[data-type="button"]`).length, 0);
    assert.equal(plain(ui.$(`${panel(2311)}.j2ha-v2-type-refused-list li[data-type="button"]`).text()), 'Bouton (button)');
    done();
  });

  it('choix courant toujours visible, même s’il n’est plus annoncé ; aucun type refusé : pas de ligne repliée', () => {
    const t = lampe(['switch']);
    Object.assign(t.commands[0], { override_applied: true, effective_ha: 'light' });
    const { ui, P, panel, done } = openFiche(t);
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    assert.equal(ui.$(`${panel(2311)}input[data-type="light"]`).prop('checked'), true);
    assert.equal(ui.$(`${panel(2311)}input[data-type="auto"]`).length, 1);
    assert.match(plain(ui.$(`${panel(2311)}.j2ha-v2-type-refused-toggle`).text()), /\(8\)/);
    ui.win.Jeedom2haSurface.clearEquipment();
    const full = openFiche(DEMO.lampePrise(true));
    full.ui.click(`${full.P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    assert.equal(full.ui.$(`${full.panel(2311)}.j2ha-v2-type-refused`).length, 0, 'démon sans liste : tout est proposé');
    full.done();
    done();
  });

  it('acceptation 4 : vanne proposée quand le démon l’autorise', () => {
    const t = lampe(['switch', 'valve']);
    const { ui, P, panel, done } = openFiche(t);
    ui.click(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`);
    assert.equal(ui.$(`${panel(2311)}input[data-type="valve"]`).prop('disabled'), undefined);
    assert.match(plain(ui.$(`${panel(2311)}.j2ha-v2-type-choices`).text()), /Vanne \(valve\)/);
    done();
  });

  it('libellé de la cellule : « Personnalisé : Lumière (light) »', () => {
    const t = lampe();
    Object.assign(t.commands[0], { override_applied: true, effective_ha: 'light' });
    const { ui, P, done } = openFiche(t);
    assert.equal(plain(ui.$(`${P}tr[data-cmd-id="2311"] .j2ha-type-link`).text()), 'Personnalisé : Lumière (light)');
    done();
  });

  it('textes : marqueurs {{…}} sur une seule ligne dans les fichiers du lot', () => {
    for (const file of ['desktop/js/jeedom2ha_type_panel.js', 'desktop/js/jeedom2ha_mapping_surface.js']) {
      const src = fs.readFileSync(path.join(__dirname, '..', '..', file), 'utf8');
      assert.doesNotMatch(src.replace(/\{\{[^}\n]*\}\}/g, ''), /\{\{|\}\}/, file);
    }
  });
});

describe('Lot 5 — gate : seule la publication d’un équipement déclaré est simulée', () => {
  const ORIGIN = 'https://box.test';
  const req = (body) => ({ method: 'POST', url: `${ORIGIN}/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php`, resourceType: 'xhr',
    headers: { 'content-type': 'application/x-www-form-urlencoded' }, postData: body });
  const ctx = (extra) => Object.assign({ origin: ORIGIN, declaredEquipments: {}, declaredPublicationOverrides: {} }, extra || {});
  const BODY = 'action=executeHaAction&intention=publier&portee=equipement&selection=%5B380%5D';

  it('déclarée : simulée ; non déclarée, autre portée, autre intention ou paramètre en plus : refusée', async () => {
    const { classifyRequest } = await import('../e2e/gate/lib/policy.mjs');
    const declared = ctx({ declaredEquipmentPublications: { 380: true } });
    assert.equal(classifyRequest(req(BODY), declared).verdict, 'simulate');
    assert.equal(classifyRequest(req(BODY), ctx()).verdict, 'block-fail');
    assert.equal(classifyRequest(req(BODY.replace('380', '381')), declared).verdict, 'block-fail');
    assert.equal(classifyRequest(req(BODY.replace('portee=equipement', 'portee=piece')), declared).verdict, 'block-fail');
    assert.equal(classifyRequest(req(BODY.replace('intention=publier', 'intention=supprimer')), declared).verdict, 'block-fail');
    assert.equal(classifyRequest(req(BODY + '&x=1'), declared).verdict, 'block-fail');
    assert.equal(classifyRequest(req(BODY.replace('%5B380%5D', '%5B380%2C381%5D')), declared).verdict, 'block-fail');
    assert.equal(classifyRequest(Object.assign(req(BODY), { method: 'GET' }), declared).verdict, 'block-fail');
  });

  it('réponse simulée : un succès du démon, rien n’est transmis', async () => {
    const { buildEquipmentPublicationResponse } = await import('../e2e/gate/lib/simulate.mjs');
    assert.equal(buildEquipmentPublicationResponse().result.payload.resultat, 'succes');
  });

  it('le parcours 380 déclare sa seule publication simulée', async () => {
    const parcours = await import('../e2e/gate/parcours/reference-bascule-eq-380.mjs');
    assert.deepEqual(parcours.declaredEquipmentPublications, { 380: true });
  });
});

// --- Vrai Chromium (Playwright), vrai jQuery, vrais scripts et CSS : le panneau s'insère sous la ligne, les radios
// déclenchent l'aperçu, « Enregistrer et publier » passe par `executeHaAction` de la page. Ignoré sans Playwright / PHP.
// `J2HA_LOT5_SHOTS=<dossier>` : dépose des captures (aperçu, bandeau, thème sombre) pour la recette.
describe('Lot 5 — vrai navigateur', () => {
  const { withRealView, read } = require('./helpers/workview_browser');
  const SHOTS = process.env.J2HA_LOT5_SHOTS || null;
  const shot = async (locator, name) => {
    if (!SHOTS) return;
    // En bas de la fenêtre : l'en-tête collant de l'équipement ne recouvre pas l'élément capturé.
    await locator.evaluate((el) => el.scrollIntoView({ block: 'end' }));
    await locator.screenshot({ path: path.join(SHOTS, name) });
  };
  // Captures seulement : l'extrait du cœur chargé par le harnais porte les variables du thème sombre ; on pose le fond et le
  // texte du thème voulu pour que la capture ressemble à la page (aucune assertion ne dépend de ces deux règles).
  const THEME_CSS = {
    Light: ':root { --txt-color: #333; } body { background: #f5f5f5; }',
    Dark: 'body { background: #1e1e1e; }',
  };

  function realTree(eqId) {
    const t = lampe();
    t.jeedom_eq_id = eqId;
    return { state: 'ok', result: { status: 'ok', payload: t } };
  }

  function gateFor(eqId, writesSeen) {
    return {
      isWrite: (action) => ['previewMappingOverride', 'saveMappingOverride', 'revertMappingOverride', 'executeHaAction'].includes(action),
      handleWrite: (action, request) => {
        writesSeen.push({ action, body: request.postData });
        if (action === 'previewMappingOverride') {
          const body = previewLight({ jeedom_eq_id: eqId });
          return { verdict: 'simulee', body };
        }
        if (action === 'executeHaAction') return { verdict: 'simulee', body: ACTION_OK };
        return { verdict: 'simulee', body: { state: 'ok', result: { status: 'ok', payload: {} } } };
      },
    };
  }

  for (const theme of ['Light', 'Dark']) {
    it(`choix → aperçu → « Enregistrer et publier » → bandeau (thème ${theme})`, async (t) => {
      const seen = [];
      const extraCss = read('desktop/css/jeedom2ha_v2.css') + THEME_CSS[theme];
      await withRealView(t, { hash: '#j2ha-vue=piece:3;eq:102', treeFor: realTree, gate: gateFor(102, seen), extraCss, width: 1280, height: 1400 },
        async (page, ctx) => {
          if (theme === 'Dark') await page.evaluate(() => document.body.setAttribute('data-theme', 'core2019_Dark'));
          const P = '.j2ha-eq-panel[data-eq-id="102"]';
          await page.locator(`${P} .j2ha-cmd-table`).waitFor({ state: 'visible' });
          await page.locator(`${P} tr[data-cmd-id="2311"] .j2ha-type-link`).click();
          const box = page.locator(`${P} tr.j2ha-v2-type-row[data-type-panel-for="2311"] .j2ha-v2-type-panel`);
          await box.waitFor({ state: 'visible' });
          assert.equal(await page.evaluate(() => document.activeElement && document.activeElement.getAttribute('data-type')), 'auto', 'focus sur le choix actuel');
          assert.equal(await box.locator('input[data-type="button"]').count(), 0);
          assert.equal(await box.locator('.j2ha-v2-type-refused-list').isVisible(), false);
          await box.locator('.j2ha-v2-type-refused-toggle').click();
          assert.equal(await box.locator('.j2ha-v2-type-refused-list').isVisible(), true);
          await box.locator('.j2ha-v2-type-refused-toggle').click();
          await box.locator('input[data-type="light"]').check();
          await box.locator('.j2ha-v2-diff').waitFor({ state: 'visible' });
          await page.waitForFunction(() => !document.querySelector('.j2ha-v2-type-save').disabled);
          assert.deepEqual(seen.map((w) => w.action), ['previewMappingOverride'], 'aperçu seul, rien d’écrit');
          await shot(box, `lot5-apercu-${theme.toLowerCase()}.png`);
          // Pas de défilement horizontal dans le détail.
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
          await box.locator('.j2ha-v2-type-save').click();
          const toast = page.locator(`${P} .j2ha-v2-type-toast`);
          await toast.waitFor({ state: 'visible' });
          assert.match(await toast.innerText(), /Lampe Chevet est maintenant une lumière dans Home Assistant\./);
          assert.deepEqual(seen.map((w) => w.action), ['previewMappingOverride', 'saveMappingOverride', 'executeHaAction']);
          assert.equal(seen[1].body, 'action=saveMappingOverride&eqId=102&cmdId=2311&haEntityType=light');
          assert.match(decodeURIComponent(seen[2].body), /intention=publier&portee=equipement&selection=\[102\]/);
          await shot(page.locator(`${P} .j2ha-eq-head`), `lot5-bandeau-${theme.toLowerCase()}.png`);
          assert.deepEqual(ctx.errors, []);
        });
    });
  }

  it('Échap ferme le panneau et rend le focus au lien', async (t) => {
    await withRealView(t, { hash: '#j2ha-vue=piece:3;eq:102', treeFor: realTree, gate: gateFor(102, []) }, async (page, ctx) => {
      const P = '.j2ha-eq-panel[data-eq-id="102"]';
      await page.locator(`${P} .j2ha-cmd-table`).waitFor({ state: 'visible' });
      await page.locator(`${P} tr[data-cmd-id="2312"] .j2ha-type-link`).click();
      await page.keyboard.press('Escape');
      assert.equal(await page.locator(`${P} .j2ha-v2-type-panel`).count(), 0);
      assert.equal(await page.evaluate(() => document.activeElement.closest('tr').getAttribute('data-cmd-id')), '2312');
      assert.deepEqual(ctx.errors, []);
    });
  });
});
