// tests/e2e/gate/lib/simulate.mjs
/**
 * Story 20.0 (Incrément B1b) — simulation des écritures d'override, en fonctions pures.
 *
 * Aucun import de Playwright ni de module réseau Node : ce module dérive des réponses déjà
 * observées (response/realResponse, fournies par l'appelant) à partir d'un état explicite
 * (state), lui aussi fourni par l'appelant — jamais d'E/S, jamais de mutation des objets
 * reçus en argument. Les écritures d'override ne sont jamais transmises au démon (policy.mjs,
 * verdict "simulate") : l'arbre réel ne contient donc jamais de simulation. « Annuler » une
 * simulation revient simplement à ne plus l'appliquer à la lecture dérivée.
 *
 * Contrats de réponse réels repris de `/tmp/jeedom2ha-200-simulation-design.md` (incrément
 * B1a) et corrigés après relecture ClaudeBox (commit 698588c) : `previewMappingOverride`
 * passe par `jeedom2ha::callDaemon`, qui rend tel quel le JSON du démon
 * (`core/class/jeedom2ha.class.php:551-556`, `return $data`). L'enveloppe ajax::success
 * `{"state":"ok","result":...}` a donc TOUJOURS un `payload` intermédiaire dans `result`,
 * identique pour les 4 actions :
 *   - previewMappingOverride : result = {"status":"ok","payload":{mapped, covered, auto,
 *     overridden, native_generic_types, ...}} (`http_server.py:2726-2849`).
 *   - getMappingOverrides / saveMappingOverride / revertMappingOverride : result =
 *     {"status":"ok","payload":{...}} — pour getMappingOverrides, payload = {jeedom_eq_id,
 *     eq_name, mapped, sync_status, commands[]} (confirmé par
 *     jeedom2ha_mapping_surface.js:329, `result.payload ? result.payload : result`, et par
 *     `readPreviewOverridden`/`readPreviewCovered` de `jeedom2ha_mapping_override.js:120-135`,
 *     qui font `p = payload.payload ? payload.payload : payload`).
 *
 * state = { previews, simulations, lastPreviewType }, créé par createState() :
 *   - previews[`${eqId}:${cmdId}`] = { type, overridden } — dernier aperçu exploitable.
 *   - simulations[`${eqId}:${cmdId}`] = { eqId, cmdId, type, diagnostic } — simulations en
 *     vigueur (une écriture "sauvegardée" simulée, jamais transmise au démon).
 *   - lastPreviewType : même forme que ctx.lastPreviewType de policy.mjs — à propager tel
 *     quel dans le ctx de classifyRequest pour que saveMappingOverride soit autorisée.
 */

function key(eqId, cmdId) {
  return `${eqId}:${cmdId}`;
}

function hasOwnSafe(obj, k) {
  return typeof obj === 'object' && obj !== null && Object.hasOwn(obj, k);
}

export function createState() {
  return {
    previews: Object.create(null),
    simulations: Object.create(null),
    lastPreviewType: Object.create(null),
  };
}

/** Construit la réponse AJAX vide du long-polling du cœur Jeedom, sans E/S. */
export function buildEmptyChangesResponse(datetime) {
  if (typeof datetime !== 'number' || !Number.isFinite(datetime)) {
    throw new Error('changes-datetime-invalide');
  }
  return { state: 'ok', result: { datetime, result: [] } };
}

function readPayload(result) {
  if (!result || result.status !== 'ok') return null;
  const payload = result.payload;
  if (!payload || typeof payload !== 'object') return null;
  return payload;
}

// recordPreview : mémorise le type proposé et la vue `overridden` d'un aperçu réel
// exploitable (AC2), et tient à jour lastPreviewType (lu par policy.mjs). N'enregistre rien
// si l'aperçu n'est pas exploitable (enveloppe en échec, `payload` absent/invalide, commande
// non couverte, overridden nul) : recordSave échouera alors explicitement, comme pour tout
// aperçu jamais obtenu.
export function recordPreview(state, { eqId, cmdId, type, response }) {
  const k = key(eqId, cmdId);
  // Chaque aperçu remplace intégralement le précédent pour ce couple. Un aperçu
  // inexploitable ne doit jamais autoriser l'enregistrement d'un type périmé.
  delete state.previews[k];
  delete state.lastPreviewType[k];

  if (typeof type !== 'string' || type.trim().length === 0) return false;
  if (!response || response.state !== 'ok') return false;
  const payload = readPayload(response.result);
  if (!payload || payload.covered !== true || payload.overridden == null) return false;

  state.previews[k] = { type, overridden: structuredClone(payload.overridden) };
  state.lastPreviewType[k] = type;
  return true;
}

// simulatePreviewBascule (section 4 de la conception) : copie profonde de realResponse
// (enveloppe previewMappingOverride) avec uniquement les 2 booléens forcés à « prêt », dans
// `result.payload.overridden`. ha_entity_type/confidence/reason_code reflètent déjà le type
// proposé par le moteur réel et n'ont pas besoin d'être changés — inventer davantage serait
// une donnée non prouvée.
export function simulatePreviewBascule(realResponse) {
  const payload = readPayload(realResponse && realResponse.result);
  if (!payload) {
    throw new Error('simulatePreviewBascule: payload absent ou invalide, bascule impossible');
  }
  if (payload.covered !== true) {
    throw new Error('simulatePreviewBascule: aperçu non couvert, bascule impossible');
  }
  if (payload.overridden == null) {
    throw new Error('simulatePreviewBascule: overridden absent, bascule impossible');
  }

  const copy = structuredClone(realResponse);
  copy.result.payload.overridden.projection_validity.is_valid = true;
  copy.result.payload.overridden.should_publish = true;
  return copy;
}

// recordSave : exige un aperçu mémorisé du même type (AC2) — sinon erreur explicite, jamais
// une simulation silencieuse. La vue overridden de cet aperçu devient le diagnostic de la
// simulation active : seule vue de décision authentiquement calculée par le moteur pour ce
// couple eqId/cmdId/type (section 3 de la conception).
export function recordSave(state, { eqId, cmdId, type }) {
  const k = key(eqId, cmdId);
  const preview = state.previews[k];
  if (!preview) {
    throw new Error(`recordSave: aucun aperçu mémorisé pour ${k}`);
  }
  if (preview.type !== type) {
    throw new Error(`recordSave: type "${type}" différent de l'aperçu mémorisé ("${preview.type}") pour ${k}`);
  }

  state.simulations[k] = { eqId, cmdId, type, diagnostic: structuredClone(preview.overridden) };
}

export function buildSaveResponse({ eqId, cmdId, type }) {
  return {
    state: 'ok',
    result: {
      status: 'ok',
      payload: {
        jeedom_eq_id: Number(eqId),
        jeedom_cmd_id: Number(cmdId),
        ha_entity_type: type,
        override_applied: true,
      },
    },
  };
}

// recordRevert : retire la ou les simulations ciblées (jamais transmis au démon — annuler
// revient à ne plus appliquer). cmdId absent/vide => équipement entier : dès qu'aucune
// commande de l'équipement ne porte plus de simulation, la relecture dérivée redevient
// l'arbre réel intégral (section 3 de la conception, dernier paragraphe).
export function recordRevert(state, { eqId, cmdId }) {
  if (cmdId) {
    const k = key(eqId, cmdId);
    const removed = hasOwnSafe(state.simulations, k);
    if (removed) delete state.simulations[k];
    return { eqId, cmdId, scope: 'command', removed, removedCommands: removed ? [cmdId] : [] };
  }

  const removedCommands = [];
  for (const k of Object.keys(state.simulations)) {
    const sim = state.simulations[k];
    if (sim.eqId === eqId) {
      removedCommands.push(sim.cmdId);
      delete state.simulations[k];
    }
  }
  return { eqId, cmdId: null, scope: 'equipment', removed: removedCommands.length > 0, removedCommands };
}

export function buildRevertResponse({ eqId, scope, removed, removedCommands }) {
  return {
    state: 'ok',
    result: {
      status: 'ok',
      payload: {
        jeedom_eq_id: Number(eqId),
        scope,
        removed,
        removed_commands: removedCommands.map(Number),
      },
    },
  };
}

export function hasActiveSimulation(state, eqId) {
  return Object.values(state.simulations).some((sim) => sim.eqId === eqId);
}

// deriveOverrideTree (section 3 de la conception) : copie profonde du dernier arbre réel
// observé, transformée UNIQUEMENT sur les commandes qui portent une simulation en vigueur
// pour cet équipement. sync_status n'est JAMAIS recalculé (arbitrage ClaudeBox 2026-10-02) :
// current_should_publish est une décision d'équipement du démon (mapped and
// equipment_decision.should_publish and scope_included), pas une agrégation « au moins une
// commande prête » — une telle agrégation inventerait une donnée que le gate ne peut pas
// prouver. Le badge « pas encore republié » n'est donc pas prouvé par le gate.
export function deriveOverrideTree(state, eqId, realResponse) {
  const copy = structuredClone(realResponse);
  const commands = copy.result.payload.commands;

  for (const k of Object.keys(state.simulations)) {
    const sim = state.simulations[k];
    if (sim.eqId !== eqId) continue;

    const row = commands.find((c) => String(c.jeedom_cmd_id) === String(sim.cmdId));
    if (!row) {
      throw new Error(`deriveOverrideTree: commande simulée ${sim.cmdId} absente de l'arbre réel (eqId=${eqId})`);
    }

    row.override_applied = true;
    row.override_source = 'user';
    row.effective_ha = sim.type;
    row.diagnostic = structuredClone(sim.diagnostic);
  }

  return copy;
}
