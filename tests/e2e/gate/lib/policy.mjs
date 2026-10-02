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
 *   - ctx.origin : origine autorisée pour ce parcours (défaut DEFAULT_ORIGIN) — permet de
 *     pointer l'intercepteur vers un serveur de test local sans changer la politique.
 *   - ctx.loginAttempts : nombre de tentatives de connexion déjà émises par ce parcours.
 *   - ctx.declaredEquipments : { [eqId]: { commands: [cmdId, ...] } } — équipements et
 *     commandes déclarés par le parcours (AC2).
 *   - ctx.lastPreviewType : { [`${eqId}:${cmdId}`]: haEntityType } — dernier type
 *     prévisualisé par previewMappingOverride pour ce couple, exigé identique par
 *     saveMappingOverride (AC2).
 */

// Origine autorisée par défaut ; surchargée par ctx.origin (intercepteur à venir,
// par exemple pour pointer vers un serveur de test local).
export const DEFAULT_ORIGIN = 'https://domobox.famille-sahut.fr';

function resolveOrigin(ctx) {
  if (ctx && typeof ctx === 'object' && typeof ctx.origin === 'string' && ctx.origin) {
    return ctx.origin;
  }
  return DEFAULT_ORIGIN;
}

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

// Clé jamais résolue via le prototype (constructor, __proto__, ...) : évite une valeur
// héritée ou une TypeError sur ctx.declaredEquipments[eqId]/ctx.lastPreviewType[clé].
function hasOwnSafe(obj, key) {
  return typeof obj === 'object' && obj !== null && Object.hasOwn(obj, key);
}

function isDigitsOnly(value) {
  return /^[0-9]+$/.test(value);
}

const OVERRIDE_PARAM_NAMES = ['eqId', 'cmdId', 'haEntityType'];

// init() PHP lit l'URL avant le corps : pour ne jamais laisser l'URL influencer une
// écriture d'override, eqId/cmdId/haEntityType doivent être absents de l'URL, apparaître
// au plus une fois dans le corps, et eqId (et cmdId s'il est présent et non vide) doivent
// être des chiffres seuls — sinon la requête est structurellement invalide.
function readOverrideParams(url, postParams) {
  if (OVERRIDE_PARAM_NAMES.some((name) => url.searchParams.has(name))) return null;
  if (!postParams) return null;
  if (OVERRIDE_PARAM_NAMES.some((name) => postParams.getAll(name).length > 1)) return null;

  const eqId = postParams.get('eqId');
  const cmdId = postParams.get('cmdId');
  const haEntityType = postParams.get('haEntityType');

  if (!eqId || !isDigitsOnly(eqId)) return null;
  if (cmdId !== null && cmdId !== '' && !isDigitsOnly(cmdId)) return null;

  return { eqId, cmdId, haEntityType };
}

function validateOverrideWrite(action, url, postParams, ctx) {
  const params = readOverrideParams(url, postParams);
  if (!params) return false;
  if (!ctx || typeof ctx !== 'object') return false;

  const declaredEquipments = ctx.declaredEquipments;
  if (!hasOwnSafe(declaredEquipments, params.eqId)) return false;
  const declared = declaredEquipments[params.eqId];
  if (!declared || !Array.isArray(declared.commands)) return false;

  if (action === 'saveMappingOverride') {
    if (!params.cmdId || !declared.commands.includes(params.cmdId)) return false;
    const lastPreviewType = ctx.lastPreviewType;
    const key = `${params.eqId}:${params.cmdId}`;
    if (!hasOwnSafe(lastPreviewType, key)) return false;
    return params.haEntityType === lastPreviewType[key];
  }

  // revertMappingOverride : cmdId absent/vide (équipement entier), ou commande déclarée.
  if (!params.cmdId) return true;
  return declared.commands.includes(params.cmdId);
}

export function classifyRequest(req, ctx) {
  try {
    let url;
    try {
      url = new URL(req.url);
    } catch {
      return { verdict: 'block-fail', reason: 'url-illisible', action: null };
    }

    if (url.origin !== resolveOrigin(ctx)) {
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
      if (!ctx || typeof ctx !== 'object') {
        return { verdict: 'block-fail', reason: 'ctx-invalide', action };
      }
      if ((ctx.loginAttempts ?? 0) >= 1) {
        return { verdict: 'block-fail', reason: 'second-essai-connexion', action };
      }
      return { verdict: 'auth', reason: 'connexion', action };
    }

    if (req.method === 'POST' && action !== null && findAllowedRead(url, action)) {
      return { verdict: 'read', reason: 'lecture-autorisee', action };
    }

    // Effets de bord et écritures d'override : rejetés quelle que soit la méthode HTTP,
    // dès lors que le chemin et l'action correspondent — un GET ne doit pas leur échapper.
    if (url.pathname === PLUGIN_AJAX_PATH && SIDE_EFFECT_ACTIONS.includes(action)) {
      return { verdict: 'block-fail', reason: 'effet-de-bord', action };
    }

    if (url.pathname === PLUGIN_AJAX_PATH && OVERRIDE_WRITE_ACTIONS.includes(action)) {
      if (validateOverrideWrite(action, url, postParams, ctx)) {
        return { verdict: 'simulate', reason: 'ecriture-override-declaree', action };
      }
      return { verdict: 'block-fail', reason: 'ecriture-override-non-declaree', action };
    }

    return { verdict: 'block', reason: 'non-inscrit', action };
  } catch {
    return { verdict: 'block-fail', reason: 'exception-politique', action: null };
  }
}
