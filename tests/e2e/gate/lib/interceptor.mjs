// tests/e2e/gate/lib/interceptor.mjs
/**
 * Story 20.0 (incrément B2a) — intercepteur Playwright à refus par défaut.
 *
 * L'appelant crée le BrowserContext avec `serviceWorkers: 'block'`, effectue la
 * connexion avant cette installation, puis fournit un journal vide :
 * `{ entries: [], failed: false, failures: [] }`. Ce module ne crée ni
 * navigateur ni connexion et ne contient aucun témoin de la box.
 */

import { classifyRequest } from './policy.mjs';
import {
  buildRevertResponse,
  buildSaveResponse,
  buildEmptyChangesResponse,
  buildPublicationRevertResponse,
  buildPublicationSaveResponse,
  deriveOverrideTree,
  derivePublicationOverrideTree,
  hasActiveSimulation,
  hasActivePublicationSimulation,
  recordPreview,
  recordPublicationRevert,
  recordPublicationSave,
  recordRevert,
  recordSave,
  simulatePreviewBascule,
} from './simulate.mjs';

const EVENT_CHANGES_PATH = '/core/ajax/event.ajax.php';
const EVENT_CHANGES_DELAY_MS = 5_000;

/** Budget d'action du plugin (60 s) plus marge : le lanceur attend plus longtemps
 * que ce délai avant de déclarer une requête en cours comme bloquée (run-gate.mjs). */
export const ROUTE_FETCH_TIMEOUT_MS = 70_000;

function requestDetails(request) {
  return {
    method: request.method(),
    url: request.url(),
    resourceType: request.resourceType(),
    postData: request.postData(),
    headers: request.headers(),
  };
}

function pathname(url) {
  try {
    return new URL(url).pathname;
  } catch {
    return null;
  }
}

export function requestKeys({ url, postData }) {
  const keys = new Set();
  try {
    for (const [key] of new URL(url).searchParams) keys.add(key);
  } catch {
    // Une URL illisible n'ajoute aucun nom; le verdict reste le refus strict.
  }
  if (typeof postData === 'string') for (const [key] of new URLSearchParams(postData)) keys.add(key);
  return [...keys].sort().slice(0, 10);
}

export function appendEntry(journal, { method, resourceType, url, postData, action, verdict, reason }) {
  const entry = {
    timestamp: new Date().toISOString(),
    method,
    resourceType,
    path: pathname(url),
    action: action ?? null,
    verdict,
    reason,
  };
  if (verdict === 'block' || verdict === 'block-fail') entry.keys = requestKeys({ url, postData });
  journal.entries.push(entry);
  return entry;
}

function fail(journal, entry) {
  journal.failed = true;
  journal.failures.push(entry);
}

/** Suit les seules requêtes réellement transmises, pour la fenêtre de calme AC3. */
async function forward(journal, operation) {
  journal.inFlight = (journal.inFlight ?? 0) + 1;
  journal.lastSentAt = new Date().toISOString();
  try {
    return await operation();
  } finally {
    journal.inFlight -= 1;
  }
}

function isDeclaredBascule(declaredBascules, { eqId, cmdId, haEntityType }) {
  if (!Array.isArray(declaredBascules)) return false;
  return declaredBascules.some(
    (item) =>
      item &&
      String(item.eqId) === eqId &&
      String(item.cmdId) === cmdId &&
      String(item.haEntityType) === haEntityType
  );
}

async function fulfillJson(route, response, body) {
  await route.fulfill({ response, json: body });
}

function buildRescanResponse() {
  return {
    state: 'ok',
    result: {
      status: 'ok', operation_result: 'succes',
      operation_message: 'Synchronisation terminée.',
      payload: { mapping_summary: { equipments_published: 0 } },
    },
  };
}

/** Attend le délai déterministe du long-polling sans ajouter de dépendance réseau. */
function wait(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

/** Indique si le navigateur a fermé la page à l'origine d'une route. */
function pageClosed(route) {
  try {
    return route.request().frame().page().isClosed();
  } catch {
    return true;
  }
}

/** Une lecture AJAX ne doit jamais suivre une redirection, même interne. */
export function isRedirectResponse(status, headers = {}) {
  if ([301, 302, 303, 307, 308].includes(status)) return true;
  return typeof headers === 'object'
    && headers !== null
    && Object.keys(headers).some((name) => name.toLowerCase() === 'location');
}

/** Récupère une lecture sans suivre de redirection, puis la sert au navigateur. */
async function fetchRead(route, journal, req, decision) {
  const response = await forward(journal, () => route.fetch({ maxRedirects: 0, timeout: ROUTE_FETCH_TIMEOUT_MS }));
  if (!isRedirectResponse(response.status(), response.headers())) return response;

  const entry = appendEntry(journal, {
    ...req,
    ...decision,
    verdict: 'redirection-non-autorisee',
    reason: 'redirection-non-autorisee',
  });
  fail(journal, entry);
  try {
    await route.abort();
  } catch {
    // Le refus est déjà consigné ; une page fermée ne doit pas masquer ce constat.
  }
  return null;
}

/**
 * Installe l'intercepteur sur le contexte déjà créé par le lanceur.
 *
 * `declaredBascules` est une liste fermée de `{ eqId, cmdId, haEntityType }`.
 * Les valeurs sont comparées comme chaînes, car elles proviennent du corps URL-encodé.
 */
export async function installInterceptor(context, { ctx, simState, journal, declaredBascules }) {
  await context.route('**/*', async (route) => {
    // Posé avant tout await : waitForQuietWindow() compte la fenêtre de calme depuis
    // cette interception, pas depuis la dernière réponse effectivement transmise.
    journal.lastInterceptedAt = Date.now();
    let req;
    let decision;

    try {
      req = requestDetails(route.request());
      decision = classifyRequest(req, ctx);

      if (decision.verdict === 'static' || decision.verdict === 'document') {
        // route.continue() laisserait le navigateur suivre une redirection sans
        // repasser par ce gestionnaire : on récupère la réponse nous-mêmes, comme
        // pour les lectures AJAX, afin de refuser toute redirection avant de servir.
        const response = await fetchRead(route, journal, req, decision);
        if (!response) return;
        await route.fulfill({ response });
        appendEntry(journal, { ...req, ...decision });
        return;
      }

      if (decision.verdict === 'auth') {
        // Le lanceur seul s'authentifie via context.request, avant toute page.
        // Une page ne doit jamais porter les identifiants ni ouvrir une connexion.
        const entry = appendEntry(journal, {
          ...req,
          ...decision,
          reason: 'connexion-par-la-page-interdite',
        });
        fail(journal, entry);
        await route.abort();
        return;
      }

      if (decision.verdict === 'read') {
        const params = decision.params;

        if (decision.action === 'changes' && new URL(req.url).pathname === EVENT_CHANGES_PATH) {
          // Enregistrée dès l'interception : si la page ferme pendant les 5 s
          // d'attente, l'horodatage doit refléter ce long-polling, pas une
          // requête antérieure, sous peine de raccourcir waitForQuietWindow().
          appendEntry(journal, { ...req, ...decision, verdict: 'lecture-simulee' });
          await wait(EVENT_CHANGES_DELAY_MS);
          if (pageClosed(route)) {
            // La page a fermé pendant l'attente : la réponse n'est jamais servie, mais
            // ce n'est pas un échec du gate, seulement une fin de parcours anticipée.
            appendEntry(journal, {
              ...req,
              ...decision,
              verdict: 'lecture-simulee-annulee',
              reason: 'page-fermee-avant-reponse',
            });
            return;
          }
          try {
            await route.fulfill({ json: buildEmptyChangesResponse(Date.now() / 1_000) });
          } catch (error) {
            if (pageClosed(route)) {
              appendEntry(journal, {
                ...req,
                ...decision,
                verdict: 'lecture-simulee-annulee',
                reason: 'page-fermee-avant-reponse',
              });
              return;
            }
            throw error;
          }
          return;
        }

        if (
          decision.action === 'getMappingOverrides'
          && (hasActiveSimulation(simState, params.eqId) || hasActivePublicationSimulation(simState, params.eqId))
        ) {
          const response = await fetchRead(route, journal, req, decision);
          if (!response) return;
          let served = await response.json();
          if (hasActiveSimulation(simState, params.eqId)) served = deriveOverrideTree(simState, params.eqId, served);
          if (hasActivePublicationSimulation(simState, params.eqId)) {
            served = derivePublicationOverrideTree(simState, params.eqId, served);
          }
          await fulfillJson(route, response, served);
          appendEntry(journal, { ...req, ...decision, verdict: 'lecture-derivee' });
          return;
        }

        if (decision.action === 'previewMappingOverride') {
          const response = await fetchRead(route, journal, req, decision);
          if (!response) return;
          const realResponse = await response.json();
          const declared = isDeclaredBascule(declaredBascules, params);
          const served = declared ? simulatePreviewBascule(realResponse) : realResponse;

          // Un aperçu réel non exploitable n'est pas une écriture ni une erreur de
          // transport : recordPreview ne l'enregistre pas, et un enregistrement
          // ultérieur échouera explicitement dans recordSave. Une bascule déclarée
          // impossible, elle, lève déjà dans simulatePreviewBascule et atteint catch.
          recordPreview(simState, { eqId: params.eqId, cmdId: params.cmdId, type: params.haEntityType, response: served });
          ctx.lastPreviewType = simState.lastPreviewType;
          await fulfillJson(route, response, served);
          appendEntry(journal, {
            ...req,
            ...decision,
            verdict: declared ? 'apercu-simule' : 'lecture-reelle',
          });
          return;
        }

        const response = await fetchRead(route, journal, req, decision);
        if (!response) return;
        await route.fulfill({ response });
        appendEntry(journal, { ...req, ...decision });
        return;
      }

      if (decision.verdict === 'simulate') {
        const params = decision.params;
        let response;
        if (decision.action === 'scanTopology') {
          response = buildRescanResponse();
        } else if (decision.action === 'savePublicationOverride') {
          recordPublicationSave(simState, { eqId: params.eqId, cmdId: params.cmdId, policy: params.publicationPolicy });
          response = buildPublicationSaveResponse({ eqId: params.eqId, cmdId: params.cmdId, policy: params.publicationPolicy });
        } else if (decision.action === 'revertPublicationOverride') {
          const revert = recordPublicationRevert(simState, { eqId: params.eqId, cmdId: params.cmdId });
          response = buildPublicationRevertResponse(revert);
        } else if (decision.action === 'saveMappingOverride') {
          recordSave(simState, { eqId: params.eqId, cmdId: params.cmdId, type: params.haEntityType });
          response = buildSaveResponse({ eqId: params.eqId, cmdId: params.cmdId, type: params.haEntityType });
        } else {
          const revert = recordRevert(simState, { eqId: params.eqId, cmdId: params.cmdId });
          response = buildRevertResponse(revert);
        }
        await route.fulfill({ json: response });
        appendEntry(journal, { ...req, ...decision, verdict: 'simulee' });
        return;
      }

      const entry = appendEntry(journal, { ...req, ...decision });
      fail(journal, entry);
      await route.abort();
    } catch {
      try {
        await route.abort();
      } catch {
        // Le refus est déjà tenté ; l'échec reste impérativement consigné ci-dessous.
      }
      const entry = appendEntry(journal, {
        method: req?.method ?? null,
        resourceType: req?.resourceType ?? null,
        url: req?.url ?? null,
        action: decision?.action ?? null,
        verdict: 'exception-intercepteur',
        reason: 'exception-intercepteur',
      });
      fail(journal, entry);
    }
  });

  await context.routeWebSocket(/.*/, async (route) => {
    journal.lastInterceptedAt = Date.now();
    const entry = appendEntry(journal, {
      method: 'WEBSOCKET',
      resourceType: 'websocket',
      url: route.url(),
      action: null,
      verdict: 'websocket-bloque',
      reason: 'websocket-interdit',
    });
    fail(journal, entry);
    await route.close();
  });
}
