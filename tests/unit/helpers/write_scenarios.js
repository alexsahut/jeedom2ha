'use strict';

/* Story 25.4 (AC8, Task 1.1) — scénarios d'ÉCRITURE de l'écran d'équipement et de pièce, rejoués sur l'interface
 * réelle (faux DOM) pour relever le corps sérialisé (clés triées) de chaque requête d'écriture.
 *
 * Les scénarios ne connaissent pas la manière d'atteindre le détail d'un équipement : l'appelant fournit
 * `open(rooms, objectId, trees)` qui rend une interface avec le détail de l'équipement 1 (pièce 7) affiché et son
 * arbre lu. Sur `main` (fenêtre de pièce) c'est l'ouverture de la modale ; sur la vue C c'est la sélection de
 * l'équipement. La référence `tests/fixtures/story_25_4_corps_ecriture.json` a été relevée sur `main` AVANT la
 * story (`capture_story_25_4_references.js`) ; le test de contrat (`test_story_25_4_contrat_ecriture`) rejoue ces
 * scénarios sur la vue C et exige des corps identiques. Identifiants fictifs (CC-48). */

const { tree, ok, READY, view } = require('./ui_harness');

const BLOCKED = view('no_generic_type_configured', false, false);
const REFUSED = view('ambiguous_skipped', false, false);
const EXCLUDED = view('publication_excluded_eqlogic', false, false);

const ROOMS = [{ object_id: 7, object_name: 'Zone', equipments: [{ eq_id: 1, eq_name: 'Eq 1', enabled: true }] }];

const WRITE_ACTIONS = [
  'previewMappingOverride', 'saveMappingOverride', 'revertMappingOverride',
  'savePublicationOverride', 'revertPublicationOverride', 'executeHaAction',
];

const entity = (type, ids, extra) => Object.assign({
  ha_entity_type: type, command_ids: ids, decision: READY, publication_override: null,
  override_command_id: ids[0], override_pending: false, present_in_ha: true,
}, extra || {});

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const EQ = '.j2ha-eq-panel[data-eq-id="1"]';
const ACTION_OK = { state: 'ok', result: { payload: { resultat: 'succes', message: 'Fait.', perimetre_impacte: { nom: 'Périmètre X' } } } };
const PREVIEW_READY = { state: 'ok', result: { payload: { covered: true, overridden: {
  ha_entity_type: 'cover', projection_validity: { is_valid: true }, should_publish: true, publication_reason: 'sure',
  command_ids: [100], entities: [{ ha_entity_type: 'cover', command_ids: [100], decision: READY }],
} } } };

/** Corps sérialisé, clés triées : `cle=valeur` joints par `&` (ce que jQuery enverrait pour des valeurs simples). */
function serialize(data) {
  return Object.keys(data).sort().map((key) => `${key}=${String(data[key])}`).join('&');
}

function writesOf(ui) {
  return ui.calls.filter((call) => WRITE_ACTIONS.includes(call.action)).map((call) => ({ action: call.action, body: serialize(call.data) }));
}

const SCENARIOS = [
  {
    name: 'type-impose-apercu-puis-enregistrement',
    async run(open) {
      const ui = open(ROOMS, 7, [ok(tree(1, [BLOCKED], { present: false }))]);
      ui.click(`${EQ} tr[data-cmd-id="100"] .j2ha-type-link`);
      const select = ui.$(`${EQ} tr[data-cmd-id="100"] select`).list[0];
      select.props.value = 'cover';
      select.handlers.change.call(select);
      await sleep(450);
      ui.respond('previewMappingOverride', PREVIEW_READY);
      return writesOf(ui);
    },
  },
  {
    name: 'retour-type-commande',
    async run(open) {
      const t = tree(1, [READY], { present: true });
      t.commands[0].override_applied = true;
      t.commands[0].effective_ha = 'light';
      const ui = open(ROOMS, 7, [ok(t)]);
      ui.click(`${EQ} .mo-revert-cmd`);
      return writesOf(ui);
    },
  },
  {
    name: 'toujours-equipement-apercu-puis-confirmation',
    async run(open) {
      const t = tree(1, [BLOCKED], { decision: view('no_generic_type_configured', true, false), present: false });
      const ui = open(ROOMS, 7, [ok(t)]);
      ui.click(`${EQ} .j2ha-eq-controls .j2ha-seg-always`);
      ui.respond('previewMappingOverride', { state: 'ok', result: { payload: { overridden: {
        ha_entity_type: 'light', projection_validity: { is_valid: true }, should_publish: true, command_ids: [100],
        entities: [{ ha_entity_type: 'light', command_ids: [100], decision: READY }],
      } } } });
      ui.lastConfirmation().options.buttons.confirm.callback();
      return writesOf(ui);
    },
  },
  {
    name: 'jamais-equipement-publie-avec-confirmation',
    async run(open) {
      const ui = open(ROOMS, 7, [ok(tree(1, [READY], { present: true, entities: [entity('light', [100])] }))]);
      ui.click(`${EQ} .j2ha-eq-controls .j2ha-seg-never`);
      ui.lastConfirmation().options.buttons.confirm.callback();
      return writesOf(ui);
    },
  },
  {
    name: 'jamais-equipement-non-publie-sans-confirmation',
    async run(open) {
      const ui = open(ROOMS, 7, [ok(tree(1, [BLOCKED], { decision: BLOCKED, present: false }))]);
      ui.click(`${EQ} .j2ha-eq-controls .j2ha-seg-never`);
      return writesOf(ui);
    },
  },
  {
    name: 'automatique-equipement',
    async run(open) {
      const t = tree(1, [BLOCKED], { decision: EXCLUDED, present: false });
      t.equipment_publication_override = 'exclude';
      const ui = open(ROOMS, 7, [ok(t)]);
      ui.click(`${EQ} .j2ha-eq-controls .j2ha-seg-auto`);
      return writesOf(ui);
    },
  },
  {
    name: 'tout-remettre-en-automatique',
    async run(open) {
      const t = tree(1, [READY], { present: true });
      t.equipment_publication_override = 'exclude';
      const ui = open(ROOMS, 7, [ok(t)]);
      ui.click(`${EQ} .j2ha-eq-revert-all`);
      ui.lastConfirmation().options.buttons.confirm.callback();
      return writesOf(ui);
    },
  },
  {
    name: 'jamais-entite',
    async run(open) {
      const t = tree(1, [REFUSED, REFUSED], { decision: REFUSED, entities: [
        entity('switch', [100], { decision: REFUSED }), entity('sensor', [101], { decision: REFUSED })] });
      const ui = open(ROOMS, 7, [ok(t)]);
      ui.click(`${EQ} .j2ha-group-head .j2ha-seg-never`);
      return writesOf(ui);
    },
  },
  {
    name: 'automatique-entite',
    async run(open) {
      const t = tree(1, [REFUSED], { decision: REFUSED, entities: [
        entity('switch', [100], { decision: REFUSED, publication_override: 'exclude_command' })] });
      const ui = open(ROOMS, 7, [ok(t)]);
      ui.click(`${EQ} .j2ha-group-head .j2ha-seg-auto`);
      return writesOf(ui);
    },
  },
  {
    name: 'appliquer-equipement',
    async run(open) {
      const t = tree(1, [READY], { entities: [entity('light', [100], { override_pending: true })] });
      const ui = open(ROOMS, 7, [ok(t)]);
      ui.click(`${EQ} .j2ha-eq-apply`);
      return writesOf(ui);
    },
  },
  {
    name: 'republier-equipement-menu',
    async run(open) {
      const ui = open(ROOMS, 7, [ok(tree(1, [READY], { present: true }))]);
      ui.click(`${EQ} .j2ha-eq-republish`);
      return writesOf(ui);
    },
  },
  {
    name: 'supprimer-equipement',
    async run(open) {
      const ui = open(ROOMS, 7, [ok(tree(1, [READY], { present: true }))]);
      ui.click(`${EQ} .j2ha-eq-recreate`);
      ui.lastConfirmation().options.buttons.confirm.callback();
      return writesOf(ui);
    },
  },
  {
    name: 'republier-piece',
    async run(open) {
      const ui = open(ROOMS, 7, [ok(tree(1, [READY], { present: true }))]);
      ui.click('.j2ha-room-republish');
      ui.lastConfirmation().options.buttons.confirm.callback();
      return writesOf(ui);
    },
  },
  {
    name: 'supprimer-piece',
    async run(open) {
      const ui = open(ROOMS, 7, [ok(tree(1, [READY], { present: true }))]);
      ui.click('.j2ha-room-recreate');
      ui.lastConfirmation().options.buttons.confirm.callback();
      return writesOf(ui);
    },
  },
];

/** Rejoue tous les scénarios ; rend `{ nom: [{ action, body }] }`. */
async function runAll(open) {
  const out = {};
  for (const scenario of SCENARIOS) {
    out[scenario.name] = await scenario.run(open);
  }
  return out;
}

module.exports = { SCENARIOS, ROOMS, WRITE_ACTIONS, ACTION_OK, serialize, runAll };
