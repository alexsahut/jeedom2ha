/**
 * Story 20.0 (Incrément B1b) — Tests JS : simulation des écritures d'override (simulate.mjs).
 *
 * Module testé : tests/e2e/gate/lib/simulate.mjs (ESM pur, sans Playwright ni réseau).
 * Chargé via import() dynamique avec un chemin absolu construit depuis __dirname,
 * car ce fichier de test reste CommonJS (convention du runner `node --test`, Node 20) —
 * même schéma que test_story_20_0_gate_policy.node.test.js.
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const SIMULATE_PATH = path.join(__dirname, '..', 'e2e', 'gate', 'lib', 'simulate.mjs');

async function loadSimulate() {
  return import(pathToFileURL(SIMULATE_PATH).href);
}

// --- Fixtures : formes réelles, contrat `_decision_view` (design B1a, section 1) ---

function sampleOverridden({ isValid = false, shouldPublish = false } = {}) {
  return {
    ha_entity_type: 'switch',
    confidence: 0.8,
    reason_code: 'override_user',
    projection_validity: {
      is_valid: isValid,
      reason_code: isValid ? null : 'missing_capability',
      missing_capabilities: isValid ? [] : ['on_off'],
      missing_fields: [],
    },
    should_publish: shouldPublish,
    publication_reason: shouldPublish ? null : 'projection_invalid',
  };
}

function sampleAuto() {
  return {
    ha_entity_type: 'light',
    confidence: 0.6,
    reason_code: 'auto',
    projection_validity: { is_valid: true, reason_code: null, missing_capabilities: [], missing_fields: [] },
    should_publish: true,
    publication_reason: null,
  };
}

// Forme réelle confirmée par relecture ClaudeBox (commit 698588c) :
// `jeedom2ha::callDaemon` rend tel quel le JSON du démon, qui enveloppe sa réponse dans
// `payload` même pour previewMappingOverride (`http_server.py:2726-2849`) — comme pour
// getMappingOverrides/saveMappingOverride/revertMappingOverride.
function previewResponse({ covered = true, overridden = sampleOverridden(), status = 'ok' } = {}) {
  return {
    state: 'ok',
    result: {
      status,
      payload: {
        mapped: true,
        covered,
        auto: sampleAuto(),
        overridden,
        native_generic_types: ['LIGHT'],
        support_export: true,
      },
    },
  };
}

function commandRow(overrides) {
  return {
    jeedom_cmd_id: 2,
    cmd_name: 'Etat',
    generic_type: 'LIGHT_STATE',
    coverable: true,
    covered: true,
    attendu_ha: 'light',
    effective_ha: 'light',
    override_applied: false,
    ...overrides,
  };
}

function realTreeResponse({ eqId = 1, commands = [commandRow()], syncStatus } = {}) {
  return {
    state: 'ok',
    result: {
      status: 'ok',
      payload: {
        jeedom_eq_id: eqId,
        eq_name: 'Salon',
        mapped: true,
        sync_status: syncStatus || {
          synced_should_publish: true,
          current_should_publish: true,
          override_pending: false,
        },
        commands,
      },
    },
  };
}

function realEntityTreeResponse({ eqId = 1, entities } = {}) {
  return {
    state: 'ok',
    result: {
      status: 'ok',
      payload: {
        jeedom_eq_id: eqId,
        eq_name: 'Salon',
        mapped: true,
        equipment_decision: { ha_entity_type: 'light', should_publish: true },
        entities: entities || [
          { ha_entity_type: 'light', command_ids: [21, 22], publication_override: null, override_command_id: 21 },
          { ha_entity_type: 'switch', command_ids: [23], publication_override: null, override_command_id: 23 },
        ],
        sync_status: { synced_should_publish: true, current_should_publish: true, override_pending: false },
      },
    },
  };
}

test('story 20-0 — simulation des écritures d\'override (simulate.mjs)', async (t) => {
  const {
    createState,
    buildEmptyChangesResponse,
    recordPreview,
    simulatePreviewBascule,
    recordSave,
    buildSaveResponse,
    recordRevert,
    buildRevertResponse,
    hasActiveSimulation,
    deriveOverrideTree,
    recordPublicationSave,
    buildPublicationSaveResponse,
    recordPublicationRevert,
    buildPublicationRevertResponse,
    hasActivePublicationSimulation,
    derivePublicationOverrideTree,
  } = await loadSimulate();

  await t.test('changes simulé : datetime numérique et liste vide', () => {
    const response = buildEmptyChangesResponse(1_728_000_000.123);
    assert.deepEqual(response, {
      state: 'ok',
      result: { datetime: 1_728_000_000.123, result: [] },
    });
    assert.throws(() => buildEmptyChangesResponse('1_728_000_000'));
  });

  await t.test('enregistrement puis relecture dérivée', () => {
    const state = createState();
    const preview = previewResponse({ overridden: sampleOverridden({ isValid: true, shouldPublish: true }) });

    recordPreview(state, { eqId: '1', cmdId: '2', type: 'switch', response: preview });
    recordSave(state, { eqId: '1', cmdId: '2', type: 'switch' });

    const real = realTreeResponse();
    const derived = deriveOverrideTree(state, '1', real);
    const row = derived.result.payload.commands[0];

    assert.equal(row.override_applied, true);
    assert.equal(row.override_source, 'user');
    assert.equal(row.effective_ha, 'switch');
    assert.deepEqual(row.diagnostic, preview.result.payload.overridden);

    // Champs de lecture pure inchangés (D10).
    assert.equal(row.attendu_ha, 'light');
    assert.equal(row.cmd_name, 'Etat');
    assert.equal(row.generic_type, 'LIGHT_STATE');
    assert.equal(row.coverable, true);

    const saveResp = buildSaveResponse({ eqId: '1', cmdId: '2', type: 'switch' });
    assert.deepEqual(saveResp, {
      state: 'ok',
      result: {
        status: 'ok',
        payload: { jeedom_eq_id: 1, jeedom_cmd_id: 2, ha_entity_type: 'switch', override_applied: true },
      },
    });
  });

  await t.test('retour d\'une commande, puis de l\'équipement entier', () => {
    const state = createState();
    const readyOverridden = sampleOverridden({ isValid: true, shouldPublish: true });

    for (const cmdId of ['2', '3']) {
      recordPreview(state, { eqId: '1', cmdId, type: 'switch', response: previewResponse({ overridden: readyOverridden }) });
      recordSave(state, { eqId: '1', cmdId, type: 'switch' });
    }

    const real = realTreeResponse({ commands: [commandRow({ jeedom_cmd_id: 2 }), commandRow({ jeedom_cmd_id: 3 })] });

    const revertCmd = recordRevert(state, { eqId: '1', cmdId: '2' });
    assert.deepEqual(revertCmd, { eqId: '1', cmdId: '2', scope: 'command', removed: true, removedCommands: ['2'] });
    assert.equal(hasActiveSimulation(state, '1'), true);

    const afterCmdRevert = deriveOverrideTree(state, '1', real);
    assert.equal(afterCmdRevert.result.payload.commands[0].override_applied, false);
    assert.equal(afterCmdRevert.result.payload.commands[1].override_applied, true);

    const revertEq = recordRevert(state, { eqId: '1', cmdId: null });
    assert.deepEqual(revertEq, { eqId: '1', cmdId: null, scope: 'equipment', removed: true, removedCommands: ['3'] });
    assert.equal(hasActiveSimulation(state, '1'), false);

    const afterEqRevert = deriveOverrideTree(state, '1', real);
    assert.deepEqual(afterEqRevert, real);

    const revertCmdResp = buildRevertResponse(revertCmd);
    assert.deepEqual(revertCmdResp, {
      state: 'ok',
      result: { status: 'ok', payload: { jeedom_eq_id: 1, scope: 'command', removed: true, removed_commands: [2] } },
    });

    const revertEqResp = buildRevertResponse(revertEq);
    assert.deepEqual(revertEqResp, {
      state: 'ok',
      result: { status: 'ok', payload: { jeedom_eq_id: 1, scope: 'equipment', removed: true, removed_commands: [3] } },
    });
  });

  await t.test('plus aucune simulation : hasActiveSimulation faux', () => {
    const state = createState();
    recordPreview(state, { eqId: '1', cmdId: '2', type: 'switch', response: previewResponse() });
    recordSave(state, { eqId: '1', cmdId: '2', type: 'switch' });
    assert.equal(hasActiveSimulation(state, '1'), true);

    recordRevert(state, { eqId: '1', cmdId: '2' });
    assert.equal(hasActiveSimulation(state, '1'), false);

    // Revert sur un équipement déjà vide : no-op explicite, pas d'exception.
    const empty = recordRevert(state, { eqId: '1', cmdId: null });
    assert.deepEqual(empty, { eqId: '1', cmdId: null, scope: 'equipment', removed: false, removedCommands: [] });
  });

  await t.test('sync_status inchangé, même avec une simulation en vigueur', () => {
    const state = createState();
    const syncStatus = { synced_should_publish: true, current_should_publish: false, override_pending: true };

    recordPreview(state, {
      eqId: '1',
      cmdId: '2',
      type: 'switch',
      response: previewResponse({ overridden: sampleOverridden({ isValid: true, shouldPublish: true }) }),
    });
    recordSave(state, { eqId: '1', cmdId: '2', type: 'switch' });

    const real = realTreeResponse({ syncStatus });
    const derived = deriveOverrideTree(state, '1', real);

    assert.deepEqual(derived.result.payload.sync_status, syncStatus);
  });

  await t.test('aucune mutation des réponses réelles passées en argument', () => {
    const state = createState();
    const preview = previewResponse();
    const previewSnapshot = structuredClone(preview);

    recordPreview(state, { eqId: '1', cmdId: '2', type: 'switch', response: preview });
    assert.deepEqual(preview, previewSnapshot);

    recordSave(state, { eqId: '1', cmdId: '2', type: 'switch' });

    const real = realTreeResponse();
    const realSnapshot = structuredClone(real);
    deriveOverrideTree(state, '1', real);
    assert.deepEqual(real, realSnapshot);

    const basculeInput = previewResponse();
    const basculeSnapshot = structuredClone(basculeInput);
    simulatePreviewBascule(basculeInput);
    assert.deepEqual(basculeInput, basculeSnapshot);
  });

  await t.test('bascule : seuls les 2 booléens changent', () => {
    const base = previewResponse({ overridden: sampleOverridden({ isValid: false, shouldPublish: false }) });
    const bascule = simulatePreviewBascule(base);

    assert.equal(bascule.result.payload.overridden.projection_validity.is_valid, true);
    assert.equal(bascule.result.payload.overridden.should_publish, true);

    const expected = structuredClone(base);
    expected.result.payload.overridden.projection_validity.is_valid = true;
    expected.result.payload.overridden.should_publish = true;
    assert.deepEqual(bascule, expected);
  });

  await t.test('erreur : enregistrement sans aperçu mémorisé', () => {
    const state = createState();
    assert.throws(() => recordSave(state, { eqId: '1', cmdId: '2', type: 'switch' }));
  });

  await t.test('erreur : aperçu non exploitable (non couvert) -> enregistrement sans aperçu', () => {
    const state = createState();
    recordPreview(state, { eqId: '1', cmdId: '2', type: 'switch', response: previewResponse({ covered: false }) });
    assert.throws(() => recordSave(state, { eqId: '1', cmdId: '2', type: 'switch' }));
  });

  await t.test('un aperçu inexploitable efface le type précédent et bloque sa sauvegarde', async () => {
    const state = createState();
    const ctx = {
      origin: 'https://box.test',
      loginAttempts: 0,
      declaredEquipments: { '1': { commands: ['2'] } },
      lastPreviewType: state.lastPreviewType,
    };
    recordPreview(state, { eqId: '1', cmdId: '2', type: 'binary_sensor', response: previewResponse() });
    assert.equal(state.lastPreviewType['1:2'], 'binary_sensor');

    assert.equal(
      recordPreview(state, { eqId: '1', cmdId: '2', type: 'sensor', response: previewResponse({ covered: false }) }),
      false,
    );
    assert.equal(state.lastPreviewType['1:2'], undefined);
    assert.equal(state.previews['1:2'], undefined);
    assert.throws(() => recordSave(state, { eqId: '1', cmdId: '2', type: 'binary_sensor' }));

    const { classifyRequest } = await import(pathToFileURL(path.join(__dirname, '..', 'e2e', 'gate', 'lib', 'policy.mjs')).href);
    const decision = classifyRequest({
      method: 'POST',
      url: 'https://box.test/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
      resourceType: 'fetch',
      postData: 'action=saveMappingOverride&eqId=1&cmdId=2&haEntityType=binary_sensor',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
    }, ctx);
    assert.equal(decision.verdict, 'block-fail');
  });

  await t.test('un type vide ou non chaîne efface aussi tout aperçu précédent', () => {
    const state = createState();
    recordPreview(state, { eqId: '1', cmdId: '2', type: 'switch', response: previewResponse() });
    assert.equal(recordPreview(state, { eqId: '1', cmdId: '2', type: '', response: previewResponse() }), false);
    assert.equal(state.previews['1:2'], undefined);
    assert.equal(recordPreview(state, { eqId: '1', cmdId: '2', type: null, response: previewResponse() }), false);
    assert.equal(state.lastPreviewType['1:2'], undefined);
  });

  await t.test('erreur : type différent de l\'aperçu mémorisé', () => {
    const state = createState();
    recordPreview(state, { eqId: '1', cmdId: '2', type: 'switch', response: previewResponse() });
    assert.throws(() => recordSave(state, { eqId: '1', cmdId: '2', type: 'light' }));
  });

  await t.test('erreur : bascule sur une commande non couverte', () => {
    assert.throws(() => simulatePreviewBascule(previewResponse({ covered: false })));
  });

  await t.test('erreur : bascule sans overridden', () => {
    assert.throws(() => simulatePreviewBascule(previewResponse({ overridden: null })));
  });

  await t.test('forme fautive (sans payload intermédiaire) -> non mémorisée, bascule impossible', () => {
    const state = createState();
    // Ancienne forme erronée (bogue corrigé après relecture ClaudeBox, commit 698588c) :
    // `overridden`/`covered` directement sous `result`, sans `payload` intermédiaire.
    const faultyResponse = {
      state: 'ok',
      result: {
        mapped: true,
        covered: true,
        auto: sampleAuto(),
        overridden: sampleOverridden({ isValid: true, shouldPublish: true }),
        native_generic_types: ['LIGHT'],
      },
    };

    const recorded = recordPreview(state, { eqId: '1', cmdId: '2', type: 'switch', response: faultyResponse });
    assert.equal(recorded, false);
    assert.throws(() => recordSave(state, { eqId: '1', cmdId: '2', type: 'switch' }));
    assert.throws(() => simulatePreviewBascule(faultyResponse));
  });

  await t.test('erreur : commande simulée absente de l\'arbre réel', () => {
    const state = createState();
    recordPreview(state, { eqId: '1', cmdId: '99', type: 'switch', response: previewResponse() });
    recordSave(state, { eqId: '1', cmdId: '99', type: 'switch' });

    assert.throws(() => deriveOverrideTree(state, '1', realTreeResponse()));
  });

  // --- Story 20-2 (point 7) : simulation des écritures de publication, visible à la relecture.

  await t.test('exclusion équipement simulée : toutes les entités portent exclude_eqlogic', () => {
    const state = createState();
    recordPublicationSave(state, { eqId: '1', cmdId: null, policy: 'exclude' });
    assert.equal(hasActivePublicationSimulation(state, '1'), true);

    const real = realEntityTreeResponse();
    const derived = derivePublicationOverrideTree(state, '1', real);
    assert.equal(derived.result.payload.entities[0].publication_override, 'exclude_eqlogic');
    assert.equal(derived.result.payload.entities[1].publication_override, 'exclude_eqlogic');
    // equipment_decision/sync_status jamais recalculés (mêmes garde-fous que deriveOverrideTree).
    assert.deepEqual(derived.result.payload.equipment_decision, real.result.payload.equipment_decision);

    const saveResp = buildPublicationSaveResponse({ eqId: '1', cmdId: null, policy: 'exclude' });
    assert.deepEqual(saveResp, {
      state: 'ok',
      result: { status: 'ok', payload: { jeedom_eq_id: 1, jeedom_cmd_id: null, publication_policy: 'exclude', override_applied: true } },
    });
  });

  await t.test('forçage d\'une seule entité simulé : seule l\'entité ciblée change', () => {
    const state = createState();
    recordPublicationSave(state, { eqId: '1', cmdId: '23', policy: 'force_publish' });

    const real = realEntityTreeResponse();
    const derived = derivePublicationOverrideTree(state, '1', real);
    assert.equal(derived.result.payload.entities[0].publication_override, null);
    assert.equal(derived.result.payload.entities[1].publication_override, 'force_publish');
  });

  await t.test('exclusion d\'une commande simulée : exclude_command, pas exclude_eqlogic', () => {
    const state = createState();
    recordPublicationSave(state, { eqId: '1', cmdId: '21', policy: 'exclude' });

    const derived = derivePublicationOverrideTree(state, '1', realEntityTreeResponse());
    assert.equal(derived.result.payload.entities[0].publication_override, 'exclude_command');
    assert.equal(derived.result.payload.entities[1].publication_override, null);
  });

  await t.test('retour d\'une entité, puis de l\'équipement entier', () => {
    const state = createState();
    recordPublicationSave(state, { eqId: '1', cmdId: '21', policy: 'exclude' });
    recordPublicationSave(state, { eqId: '1', cmdId: '23', policy: 'force_publish' });

    const revertEntity = recordPublicationRevert(state, { eqId: '1', cmdId: '21' });
    assert.deepEqual(revertEntity, { eqId: '1', cmdId: '21', scope: 'command', removed: true });
    assert.equal(hasActivePublicationSimulation(state, '1'), true);

    const afterEntityRevert = derivePublicationOverrideTree(state, '1', realEntityTreeResponse());
    assert.equal(afterEntityRevert.result.payload.entities[0].publication_override, null);
    assert.equal(afterEntityRevert.result.payload.entities[1].publication_override, 'force_publish');

    const revertEquipment = recordPublicationRevert(state, { eqId: '1', cmdId: null });
    assert.deepEqual(revertEquipment, { eqId: '1', cmdId: null, scope: 'equipment', removed: true });
    assert.equal(hasActivePublicationSimulation(state, '1'), false);

    const afterEqRevert = derivePublicationOverrideTree(state, '1', realEntityTreeResponse());
    assert.deepEqual(afterEqRevert, realEntityTreeResponse());

    const revertResp = buildPublicationRevertResponse(revertEquipment);
    assert.deepEqual(revertResp, {
      state: 'ok',
      result: { status: 'ok', payload: { jeedom_eq_id: 1, scope: 'equipment', removed: true } },
    });
  });

  // Revue ClaudeBox X4 (point 8) : même ordre de précédence que le démon
  // (resolve_publication_override, overrides.py l.540-581) — un veto d'équipement l'emporte
  // TOUJOURS sur un override de commande, qui l'emporte à son tour sur un forçage
  // d'équipement par défaut. L'ancien code appliquait l'override d'équipement (y compris un
  // simple forçage) en premier et écrasait l'exclusion propre d'une commande.
  await t.test('précédence : exclusion d\'équipement l\'emporte sur un forçage de commande', () => {
    const state = createState();
    recordPublicationSave(state, { eqId: '1', cmdId: '23', policy: 'force_publish' });
    recordPublicationSave(state, { eqId: '1', cmdId: null, policy: 'exclude' });

    const derived = derivePublicationOverrideTree(state, '1', realEntityTreeResponse());
    assert.equal(derived.result.payload.entities[0].publication_override, 'exclude_eqlogic');
    assert.equal(derived.result.payload.entities[1].publication_override, 'exclude_eqlogic');
  });

  await t.test('précédence : l\'exclusion propre d\'une commande l\'emporte sur le forçage d\'équipement par défaut', () => {
    const state = createState();
    recordPublicationSave(state, { eqId: '1', cmdId: null, policy: 'force_publish' });
    recordPublicationSave(state, { eqId: '1', cmdId: '21', policy: 'exclude' });

    const derived = derivePublicationOverrideTree(state, '1', realEntityTreeResponse());
    assert.equal(derived.result.payload.entities[0].publication_override, 'exclude_command');
    // Aucun override propre sur la seconde entité : le forçage d'équipement par défaut s'applique.
    assert.equal(derived.result.payload.entities[1].publication_override, 'force_publish');
  });

  await t.test('aucune simulation de publication : réponse réelle inchangée', () => {
    const state = createState();
    const real = realEntityTreeResponse();
    const realSnapshot = structuredClone(real);
    assert.deepEqual(derivePublicationOverrideTree(state, '1', real), real);
    assert.deepEqual(real, realSnapshot);
    assert.equal(hasActivePublicationSimulation(state, '1'), false);

    // Revert sur un équipement déjà vide : no-op explicite.
    assert.deepEqual(
      recordPublicationRevert(state, { eqId: '1', cmdId: null }),
      { eqId: '1', cmdId: null, scope: 'equipment', removed: false },
    );
  });

  await t.test('réponse sans entities[] : dérivation sans effet, pas d\'exception', () => {
    const state = createState();
    recordPublicationSave(state, { eqId: '1', cmdId: null, policy: 'exclude' });
    const real = realTreeResponse();
    assert.deepEqual(derivePublicationOverrideTree(state, '1', real), real);
  });
});
