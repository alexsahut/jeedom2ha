// tests/e2e/gate/lib/policy.mjs
/**
 * Story 20.0 (Tasks 2-3) — politique d'interception, en fonction pure.
 *
 * Aucun import de Playwright ni de module réseau Node : ce module ne fait que classifier
 * une requête déjà observée (req) selon l'état du parcours (ctx), fournis par
 * l'appelant. Les classes globales URL/URLSearchParams du runtime JS sont utilisées,
 * pas d'E/S.
 *
 * req = { method, url, resourceType, postData, headers } — toutes des chaînes (postData peut
 * être null/undefined si absent); `headers['content-type']` est requis pour tout corps
 * vers une route AJAX/API. ctx = état du parcours tenu par l'appelant :
 *   - ctx.origin : origine autorisée pour ce parcours (défaut DEFAULT_ORIGIN) — permet de
 *     pointer l'intercepteur vers un serveur de test local sans changer la politique.
 *   - ctx.loginAttempts : nombre de tentatives de connexion déjà émises par ce parcours.
 *   - ctx.declaredEquipments : { [eqId]: { commands: [cmdId, ...] } } — équipements et
 *     commandes déclarés par le parcours (AC2).
 *   - ctx.declaredRescan : true seulement si le parcours déclare le rescan (AC7).
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

// Lectures inscrites en Task 1 (4 du plugin depuis la story 20.3, qui retire getDiagnostics et getPublishedScopeForConsole, 2 du cœur) — voir la story, section
// « Mécanisme d'interception des écritures ».
export const ALLOWED_READS = [
  {
    pathname: PLUGIN_AJAX_PATH,
    actions: [
      'getMqttConfig',
      'getBridgeStatus',
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
const OVERRIDE_WRITE_ACTIONS = ['saveMappingOverride', 'revertMappingOverride', 'savePublicationOverride', 'revertPublicationOverride'];

const PARAMETER_NAME = /^[A-Za-z][A-Za-z0-9_]*$/;
const STATIC_EXTENSIONS = /\.(?:js|css|png|jpg|jpeg|gif|svg|ico|woff2?|ttf|eot|map)$/i;
const GET_RESOURCE_PATH = '/core/php/getResource.php';
// include_file() du cœur Jeedom ajoute `lang` à l'URL; getResource.php lit file/md5.
const GET_RESOURCE_KEYS = new Set(['file', 'md5', 'lang']);

function protectedPath(path) {
  return path.endsWith('.ajax.php') || path.startsWith('/core/api/');
}

function contentType(req) {
  const headers = req.headers && typeof req.headers === 'object' ? req.headers : {};
  const value = headers['content-type'] ?? headers['Content-Type'] ?? req.contentType;
  return typeof value === 'string' ? value.split(';', 1)[0].trim().toLowerCase() : '';
}

function validatedParams(url, req) {
  const pairs = [...url.searchParams.entries()];
  const hasBody = typeof req.postData === 'string' && req.postData.length > 0;
  if (hasBody) {
    if (protectedPath(url.pathname) && contentType(req) !== 'application/x-www-form-urlencoded') return null;
    pairs.push(...new URLSearchParams(req.postData).entries());
  }

  const params = Object.create(null);
  for (const [key, value] of pairs) {
    if (!PARAMETER_NAME.test(key) || Object.hasOwn(params, key)) return null;
    params[key] = value;
  }
  return params;
}

function isStaticResource(req, url, params) {
  if (req.method !== 'GET') return false;
  if (!['script', 'stylesheet', 'image', 'font'].includes(req.resourceType)) return false;
  if (Object.hasOwn(params, 'action')) return false;
  if (url.pathname.includes('/ajax/')) return false;
  if (url.pathname.startsWith('/core/api/')) return false;
  if (url.pathname === GET_RESOURCE_PATH) {
    if (!['script', 'stylesheet'].includes(req.resourceType)) return false;
    if (!Object.keys(params).every((key) => GET_RESOURCE_KEYS.has(key))) return false;
    return typeof params.file === 'string'
      && /\.(?:js|css)$/i.test(params.file)
      && !params.file.includes('..')
      && (params.md5 === undefined || /^[0-9a-f]{32}$/.test(params.md5))
      && (params.lang === undefined || /^[a-z]{2}_[A-Z]{2}$/.test(params.lang));
  }
  return STATIC_EXTENSIONS.test(url.pathname);
}

function isLoginPageDocument(req, url, params) {
  return (
    req.method === 'GET' &&
    req.resourceType === 'document' &&
    url.pathname === LOGIN_PAGE_PATH &&
    Object.keys(params).length === 0
  );
}

function isPluginPageDocument(req, url, params) {
  if (req.method !== 'GET' || req.resourceType !== 'document' || url.pathname !== PLUGIN_PAGE_PATH) {
    return false;
  }
  return (
    Object.keys(params).length === Object.keys(PLUGIN_PAGE_QUERY).length &&
    Object.entries(PLUGIN_PAGE_QUERY).every(([key, value]) => params[key] === value)
  );
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

// Les paramètres sont déjà décodés, validés et uniques par `validatedParams`.
function readOverrideParams(params) {
  if (!params) return null;
  const eqId = params.eqId;
  const cmdId = params.cmdId ?? null;
  const haEntityType = params.haEntityType ?? null;

  if (!eqId || !isDigitsOnly(eqId)) return null;
  if (cmdId !== null && cmdId !== '' && !isDigitsOnly(cmdId)) return null;

  return { eqId, cmdId, haEntityType };
}

function validateOverrideWrite(action, params, ctx) {
  const override = readOverrideParams(params);
  if (!override) return false;
  if (!ctx || typeof ctx !== 'object') return false;

  const declaredEquipments = ctx.declaredEquipments;
  if (!hasOwnSafe(declaredEquipments, override.eqId)) return false;
  const declared = declaredEquipments[override.eqId];
  if (!declared || !Array.isArray(declared.commands)) return false;

  if (action === 'saveMappingOverride') {
    if (!override.cmdId || !declared.commands.includes(override.cmdId)) return false;
    const lastPreviewType = ctx.lastPreviewType;
    const key = `${override.eqId}:${override.cmdId}`;
    if (!hasOwnSafe(lastPreviewType, key)) return false;
    return override.haEntityType === lastPreviewType[key];
  }

  // revertMappingOverride : cmdId absent/vide (équipement entier), ou commande déclarée.
  if (!override.cmdId) return true;
  return declared.commands.includes(override.cmdId);
}

function validatePublicationWrite(action, params, ctx) {
  const override = readOverrideParams(params);
  if (!override || !ctx || typeof ctx !== 'object') return false;
  const declared = ctx.declaredPublicationOverrides;
  if (!hasOwnSafe(declared, override.eqId)) return false;
  const target = declared[override.eqId];
  if (!target || !Array.isArray(target.commands)) return false;
  if (override.cmdId && !target.commands.includes(override.cmdId)) return false;
  if (action === 'savePublicationOverride') {
    return (params.publicationPolicy === 'exclude' || params.publicationPolicy === 'force_publish');
  }
  return params.publicationPolicy === undefined;
}

function validateDeclaredRescan(req, ctx) {
  return req.method === 'POST' && ctx && ctx.declaredRescan === true;
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

    if (url.pathname.includes('//') || /%2f|%5c/i.test(url.pathname)) {
      return { verdict: 'block-fail', reason: 'chemin-non-canonique', action: null };
    }

    const params = validatedParams(url, req);
    if (!params) return { verdict: 'block-fail', reason: 'parametres-invalides', action: null };
    const action = params.action ?? null;

    if (isStaticResource(req, url, params)) {
      return { verdict: 'static', reason: 'ressource-statique', action: null, params };
    }

    if (isLoginPageDocument(req, url, params)) {
      return { verdict: 'document', reason: 'page-connexion', action: null, params };
    }

    if (isPluginPageDocument(req, url, params)) {
      return { verdict: 'document', reason: 'page-plugin', action: null, params };
    }

    if (req.method === 'POST' && url.pathname === LOGIN_AJAX_PATH && action === LOGIN_ACTION) {
      if (!ctx || typeof ctx !== 'object') {
        return { verdict: 'block-fail', reason: 'ctx-invalide', action };
      }
      if ((ctx.loginAttempts ?? 0) >= 1) {
        return { verdict: 'block-fail', reason: 'second-essai-connexion', action };
      }
      return { verdict: 'auth', reason: 'connexion', action, params };
    }

    if (req.method === 'POST' && action !== null && findAllowedRead(url, action)) {
      return { verdict: 'read', reason: 'lecture-autorisee', action, params };
    }

    // Effets de bord et écritures d'override : rejetés quelle que soit la méthode HTTP,
    // dès lors que le chemin et l'action correspondent — un GET ne doit pas leur échapper.
    if (url.pathname === PLUGIN_AJAX_PATH && action === 'scanTopology') {
      if (validateDeclaredRescan(req, ctx)) {
        return { verdict: 'simulate', reason: 'rescan-declare', action, params };
      }
      return { verdict: 'block-fail', reason: 'effet-de-bord', action };
    }

    if (url.pathname === PLUGIN_AJAX_PATH && SIDE_EFFECT_ACTIONS.includes(action)) {
      return { verdict: 'block-fail', reason: 'effet-de-bord', action };
    }

    if (url.pathname === PLUGIN_AJAX_PATH && OVERRIDE_WRITE_ACTIONS.includes(action)) {
      const allowed = action === 'savePublicationOverride' || action === 'revertPublicationOverride'
        ? validatePublicationWrite(action, params, ctx)
        : validateOverrideWrite(action, params, ctx);
      if (req.method === 'POST' && allowed) {
        return { verdict: 'simulate', reason: 'ecriture-override-declaree', action, params };
      }
      return { verdict: 'block-fail', reason: 'ecriture-override-non-declaree', action };
    }

    return { verdict: 'block', reason: 'non-inscrit', action };
  } catch {
    return { verdict: 'block-fail', reason: 'exception-politique', action: null };
  }
}
