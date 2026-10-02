// tests/e2e/gate/lib/policy.mjs
/**
 * Story 20.0 (Tasks 2-3) — politique d'interception, en fonction pure.
 *
 * Aucun import de Playwright ni de module réseau Node : ce module ne fait que classifier
 * une requête déjà observée (req) selon l'état du parcours (ctx), fournis par
 * l'appelant. Les classes globales URL/URLSearchParams du runtime JS sont utilisées,
 * pas d'E/S.
 *
 * req = { method, url, resourceType, postData } — toutes des chaînes (postData peut
 * être null/undefined si absent). ctx = état du parcours tenu par l'appelant :
 *   - ctx.loginAttempts : nombre de tentatives de connexion déjà émises par ce parcours.
 *   - ctx.declaredEquipments : { [eqId]: { commands: [cmdId, ...] } } — équipements et
 *     commandes déclarés par le parcours (AC2).
 *   - ctx.lastPreviewType : { [`${eqId}:${cmdId}`]: haEntityType } — dernier type
 *     prévisualisé par previewMappingOverride pour ce couple, exigé identique par
 *     saveMappingOverride (AC2).
 */

const ORIGIN = 'https://domobox.famille-sahut.fr';

const LOGIN_PAGE_PATH = '/index.php';
const PLUGIN_PAGE_PATH = '/index.php';
const PLUGIN_PAGE_QUERY = { v: 'd', m: 'jeedom2ha', p: 'jeedom2ha' };
const LOGIN_AJAX_PATH = '/core/ajax/user.ajax.php';
const LOGIN_ACTION = 'login';

const PLUGIN_AJAX_PATH = '/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php';

// Lectures inscrites en Task 1 (6 du plugin, 2 du cœur) — voir la story, section
// « Mécanisme d'interception des écritures ».
export const ALLOWED_READS = [
  {
    pathname: PLUGIN_AJAX_PATH,
    actions: [
      'getMqttConfig',
      'getBridgeStatus',
      'getDiagnostics',
      'getPublishedScopeForConsole',
      'getMappingOverrides',
      'previewMappingOverride',
    ],
  },
  { pathname: '/core/ajax/eqLogic.ajax.php', actions: ['listByType'] },
  { pathname: '/core/ajax/event.ajax.php', actions: ['changes'] },
];

// Effets de bord du plugin, jamais transmis (section « Mécanisme d'interception »).
const SIDE_EFFECT_ACTIONS = [
  'scanTopology',
  'executeHaAction',
  'saveFilteringConfig',
  'forceMqttManagerImport',
  'testMqttConnection',
];

// Paramètres de core/ajax/jeedom2ha.ajax.php:877-920 (previewMappingOverride,
// saveMappingOverride, revertMappingOverride) : eqId, cmdId, haEntityType.
const OVERRIDE_WRITE_ACTIONS = ['saveMappingOverride', 'revertMappingOverride'];

function collectActionOccurrences(url, postParams) {
  const occurrences = [...url.searchParams.getAll('action')];
  if (postParams) {
    occurrences.push(...postParams.getAll('action'));
  }
  return occurrences;
}

function parsePostParams(req) {
  if (req.method !== 'POST' || !req.postData) return null;
  try {
    return new URLSearchParams(req.postData);
  } catch {
    return null; // corps illisible : jamais exploité, jamais une autorisation.
  }
}

function isStaticResource(req, url, actionOccurrences) {
  if (req.method !== 'GET') return false;
  if (!['script', 'stylesheet', 'image', 'font'].includes(req.resourceType)) return false;
  if (actionOccurrences.length > 0) return false;
  if (url.pathname.includes('/ajax/')) return false;
  if (url.pathname.startsWith('/core/api/')) return false;
  return true;
}

function isLoginPageDocument(req, url) {
  return (
    req.method === 'GET' &&
    req.resourceType === 'document' &&
    url.pathname === LOGIN_PAGE_PATH &&
    [...url.searchParams.keys()].length === 0
  );
}

function isPluginPageDocument(req, url) {
  if (req.method !== 'GET' || req.resourceType !== 'document' || url.pathname !== PLUGIN_PAGE_PATH) {
    return false;
  }
  return Object.entries(PLUGIN_PAGE_QUERY).every(([key, value]) => url.searchParams.get(key) === value);
}

function findAllowedRead(url, action) {
  return ALLOWED_READS.some((entry) => entry.pathname === url.pathname && entry.actions.includes(action));
}

function validateOverrideWrite(action, params, ctx) {
  const eqId = params.get('eqId');
  const cmdId = params.get('cmdId');
  const haEntityType = params.get('haEntityType');

  if (!eqId) return false;
  const declared = ctx.declaredEquipments && ctx.declaredEquipments[eqId];
  if (!declared) return false;

  if (action === 'saveMappingOverride') {
    if (!cmdId || !declared.commands.includes(cmdId)) return false;
    const expectedType = ctx.lastPreviewType && ctx.lastPreviewType[`${eqId}:${cmdId}`];
    return haEntityType === expectedType;
  }

  // revertMappingOverride : cmdId absent (équipement entier), ou commande déclarée.
  if (!cmdId) return true;
  return declared.commands.includes(cmdId);
}

export function classifyRequest(req, ctx) {
  const url = new URL(req.url);

  if (url.origin !== ORIGIN) {
    return { verdict: 'block', reason: 'origine-differente', action: null };
  }

  const postParams = parsePostParams(req);
  const actionOccurrences = collectActionOccurrences(url, postParams);

  if (actionOccurrences.length > 1) {
    return { verdict: 'block-fail', reason: 'action-ambigue', action: null };
  }

  const action = actionOccurrences[0] ?? null;

  if (isStaticResource(req, url, actionOccurrences)) {
    return { verdict: 'static', reason: 'ressource-statique', action: null };
  }

  if (isLoginPageDocument(req, url)) {
    return { verdict: 'document', reason: 'page-connexion', action: null };
  }

  if (isPluginPageDocument(req, url)) {
    return { verdict: 'document', reason: 'page-plugin', action: null };
  }

  if (req.method === 'POST' && url.pathname === LOGIN_AJAX_PATH && action === LOGIN_ACTION) {
    if ((ctx.loginAttempts ?? 0) >= 1) {
      return { verdict: 'block-fail', reason: 'second-essai-connexion', action };
    }
    return { verdict: 'auth', reason: 'connexion', action };
  }

  if (req.method === 'POST' && action !== null && findAllowedRead(url, action)) {
    return { verdict: 'read', reason: 'lecture-autorisee', action };
  }

  if (req.method === 'POST' && url.pathname === PLUGIN_AJAX_PATH && SIDE_EFFECT_ACTIONS.includes(action)) {
    return { verdict: 'block-fail', reason: 'effet-de-bord', action };
  }

  if (req.method === 'POST' && url.pathname === PLUGIN_AJAX_PATH && OVERRIDE_WRITE_ACTIONS.includes(action)) {
    if (postParams && validateOverrideWrite(action, postParams, ctx)) {
      return { verdict: 'simulate', reason: 'ecriture-override-declaree', action };
    }
    return { verdict: 'block-fail', reason: 'ecriture-override-non-declaree', action };
  }

  return { verdict: 'block', reason: 'non-inscrit', action };
}
