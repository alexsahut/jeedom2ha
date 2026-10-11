#!/usr/bin/env node
/**
 * Story 20.0 (Task 1) — relevé des requêtes émises au chargement de la page du plugin.
 *
 * Script de reconnaissance, pas encore le gate complet (Tasks 2-4) : il ouvre un seul
 * contexte Chromium headless, refuse toute requête par défaut (HTTP et WebSocket),
 * n'autorise que les GET statiques, la page de connexion, la page du plugin, et une
 * liste fermée de lectures POST (même origine, chemin et action en correspondance
 * exacte — voir ALLOWED_READS, validée par ClaudeBox le 2026-10-02 après le premier
 * relevé) ; une action présente plus d'une fois (URL et/ou corps) est jugée ambiguë et
 * bloquée, même si l'une des valeurs est par ailleurs autorisée. Fait un seul essai de
 * connexion, puis journalise le verdict de chaque requête observée pendant le
 * chargement, et le décompte final par verdict. Sert à établir, avec des faits
 * d'exécution (pas seulement la lecture du code), la liste des couples (point d'entrée,
 * action) que Task 1 doit inscrire explicitement comme lectures nécessaires (AC1).
 *
 * NE PAS EXÉCUTER sans relecture de ClaudeBox au préalable (règle de l'unité 20-0).
 *
 * Résolution de Playwright : installé hors du dépôt, dans le dossier outils
 * (JEEDOM2HA_GATE_TOOLS, par défaut /home/asahut/.openclaw/tools/jeedom2ha-gate). En
 * ESM, Node ignore NODE_PATH : le module est donc chargé par createRequire(), ancré sur
 * le package.json de ce dossier (vérifié sur Node 22 et Playwright 1.63.0, qui fournit
 * context.routeWebSocket).
 *
 * Aucune capture, trace, HAR ni état de session n'est écrite sur disque : le journal va
 * uniquement sur stdout, à rediriger par l'appelant s'il veut le conserver.
 */

import { createRequire } from 'node:module';
import path from 'node:path';
import { statSync, readFileSync } from 'node:fs';

const GATE_TOOLS_DIR = process.env.JEEDOM2HA_GATE_TOOLS || '/home/asahut/.openclaw/tools/jeedom2ha-gate';

function loadPlaywright() {
  const toolsPackageJson = path.join(GATE_TOOLS_DIR, 'package.json');
  const requireFromTools = createRequire(toolsPackageJson);
  try {
    return requireFromTools('playwright');
  } catch (err) {
    throw new Error(
      `Playwright introuvable depuis ${GATE_TOOLS_DIR} (résolu via ${toolsPackageJson}) : ${err.message}`
    );
  }
}

let chromium;
try {
  ({ chromium } = loadPlaywright());
} catch (err) {
  console.error(err.message);
  process.exit(1);
}

const ORIGIN = 'https://domobox.famille-sahut.fr';
const LOGIN_PAGE_PATH = '/index.php';
const PLUGIN_PAGE_PATH = '/index.php';
const PLUGIN_PAGE_QUERY = { v: 'd', m: 'jeedom2ha', p: 'jeedom2ha' };
const LOGIN_AJAX_PATH = '/core/ajax/user.ajax.php';

// Aucun setInterval / rafraîchissement périodique trouvé dans desktop/js (grep du
// 2026-10-02) : les requêtes du chargement de page sont attendues en quelques secondes.
// 10 s de marge absorbe un éventuel enchaînement déclenché par une erreur (requête
// bloquée dont le handler JS retente), sans allonger inutilement le relevé.
const PAGE_LOAD_WAIT_MS = 10_000;

const REQUIRED_CRED_KEYS = ['JEEDOM_USER', 'JEEDOM_PASSWORD'];

function loadCredentials() {
  const credPath = process.env.JEEDOM2HA_GATE_CREDENTIALS
    || '/home/asahut/.config/jeedom2ha-gate/jeedom.env';

  let stat;
  try {
    stat = statSync(credPath);
  } catch {
    throw new Error(`Fichier d'identifiants introuvable : ${credPath} — arrêt.`);
  }

  const mode = stat.mode & 0o777;
  if (mode !== 0o600) {
    throw new Error(
      `Fichier d'identifiants ${credPath} : droits ${mode.toString(8)} au lieu de 600 — arrêt.`
    );
  }

  const raw = readFileSync(credPath, 'utf8');
  const values = {};
  for (const line of raw.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    values[key] = value;
  }

  const missing = REQUIRED_CRED_KEYS.filter((key) => !values[key]);
  if (missing.length > 0) {
    throw new Error(
      `Fichier d'identifiants ${credPath} : clé(s) manquante(s) ${missing.join(', ')} — arrêt.`
    );
  }

  return { username: values.JEEDOM_USER, password: values.JEEDOM_PASSWORD };
}

/** Relève toutes les occurrences du paramètre 'action' (query string, puis corps
 * urlencoded) — jamais le reste du corps ou des paramètres (identifiants, cmdId,
 * selection, etc.). Plusieurs occurrences (même emplacement dupliqué, ou présentes à la
 * fois dans l'URL et dans le corps) rendent l'action ambiguë : voir resolveAction(). */
function collectActionOccurrences(request, url) {
  const occurrences = [...url.searchParams.getAll('action')];
  if (request.method() === 'POST') {
    const postData = request.postData();
    if (postData) {
      try {
        const params = new URLSearchParams(postData);
        occurrences.push(...params.getAll('action'));
      } catch {
        // corps non urlencoded : aucune valeur 'action' exploitable depuis le corps.
      }
    }
  }
  return occurrences;
}

/** Résout l'action à partir des occurrences relevées : une seule occurrence -> cette
 * valeur ; zéro -> null ; plus d'une (duplication, ou URL + corps à la fois) -> ambiguë,
 * jamais résolue à une valeur (même si l'une des occurrences est par ailleurs
 * autorisée), et jamais journalisée telle quelle. */
function resolveAction(request, url) {
  const occurrences = collectActionOccurrences(request, url);
  if (occurrences.length === 0) return { action: null, ambiguous: false };
  if (occurrences.length === 1) return { action: occurrences[0], ambiguous: false };
  return { action: null, ambiguous: true };
}

function isAllowedStatic(request, url) {
  if (request.method() !== 'GET') return false;
  if (url.origin !== ORIGIN) return false;
  return ['script', 'stylesheet', 'image', 'font'].includes(request.resourceType());
}

function isLoginPageDocument(request, url) {
  return (
    request.method() === 'GET' &&
    url.origin === ORIGIN &&
    request.resourceType() === 'document' &&
    url.pathname === LOGIN_PAGE_PATH &&
    [...url.searchParams.keys()].length === 0
  );
}

function isPluginPageDocument(request, url) {
  if (
    request.method() !== 'GET' ||
    url.origin !== ORIGIN ||
    request.resourceType() !== 'document' ||
    url.pathname !== PLUGIN_PAGE_PATH
  ) {
    return false;
  }
  return Object.entries(PLUGIN_PAGE_QUERY).every(([key, value]) => url.searchParams.get(key) === value);
}

/* Lectures autorisées (Task 1, seconde itération — validées par ClaudeBox le 2026-10-02 ; story 20.3 :
 * `getDiagnostics` et `getPublishedScopeForConsole` retirées, l'interface ne les émet plus au chargement —
 * toute réapparition de l'une d'elles est donc relevée « bloquée » dans ce relevé) :
 * POST seulement, même origine, correspondance exacte du chemin ET de la valeur
 * d'action (pas de préfixe, pas de motif). `exportDiagnostic` reste délibérément absent
 * (hors liste, donc bloqué). `event.ajax.php action=changes` est une attente longue du
 * cœur Jeedom (long-polling) : voir la note Task 1 de la story sur la fermeture du
 * contexte avant le témoin final. */
const ALLOWED_READS = [
  {
    pathname: '/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
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

function isAllowedRead(request, url, action, ambiguous) {
  if (ambiguous) return false;
  if (action === null) return false;
  if (request.method() !== 'POST') return false;
  if (url.origin !== ORIGIN) return false;
  return ALLOWED_READS.some(
    (entry) => entry.pathname === url.pathname && entry.actions.includes(action)
  );
}

const verdictCounts = new Map();

function logLine(method, resourceType, pathname, action, verdict) {
  const ts = new Date().toISOString();
  const actionPart = action ? `action=${action}` : 'action=-';
  console.log(`${ts} ${method} ${resourceType} ${pathname} ${actionPart} verdict=${verdict}`);
  verdictCounts.set(verdict, (verdictCounts.get(verdict) ?? 0) + 1);
}

/** Compte les sauts d'une chaîne de redirection en remontant redirectedFrom(). Playwright
 * n'appelle context.route que pour la toute première URL de la chaîne : les cibles de
 * redirection ne sont pas interceptées, seulement reconstituées ici après coup. */
function countRedirects(request) {
  let count = 0;
  let current = request.redirectedFrom();
  while (current) {
    count++;
    current = current.redirectedFrom();
  }
  return count;
}

function logDoc(label, response) {
  if (!response) {
    console.log(`DOC ${label} reponse=absente`);
    return;
  }
  const url = new URL(response.url());
  const redirects = countRedirects(response.request());
  console.log(`DOC ${label} http=${response.status()} chemin=${url.pathname} redirections=${redirects}`);
}

async function main() {
  const credentials = loadCredentials();

  const blocked = new Map(); // clé "pathname|action" dédoublonnée -> {pathname, action}

  const browser = await chromium.launch({ headless: true });
  // Un seul contexte, service workers bloqués (AC1). Pas de recordHar/recordVideo,
  // pas de storageState persisté : rien n'est écrit sur disque par ce contexte.
  const context = await browser.newContext({ serviceWorkers: 'block' });

  try {
    await context.route('**/*', async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      const pathname = url.pathname;
      const { action, ambiguous } = resolveAction(request, url);
      const method = request.method();
      const resourceType = request.resourceType();

      if (ambiguous) {
        logLine(method, resourceType, pathname, null, 'bloquee-ambigue');
        blocked.set(`${pathname}|`, { pathname, action: null });
        await route.abort('blockedbyclient');
        return;
      }

      let allowed = false;
      let verdict = 'bloquee';
      if (isAllowedStatic(request, url)) {
        allowed = true;
        verdict = 'autorisee';
      } else if (isLoginPageDocument(request, url)) {
        allowed = true;
        verdict = 'autorisee';
      } else if (isPluginPageDocument(request, url)) {
        allowed = true;
        verdict = 'autorisee';
      } else if (isAllowedRead(request, url, action, ambiguous)) {
        allowed = true;
        verdict = 'lecture';
      }

      if (allowed) {
        logLine(method, resourceType, pathname, action, verdict);
        await route.continue();
        return;
      }

      logLine(method, resourceType, pathname, action, 'bloquee');
      blocked.set(`${pathname}|${action ?? ''}`, { pathname, action });
      await route.abort('blockedbyclient');
    });

    // context.route n'intercepte pas les WebSockets (API séparée). Refus par défaut ici :
    // jamais de connectToServer() (donc jamais connecté au serveur réel), fermeture
    // immédiate de la connexion côté page.
    await context.routeWebSocket(/.*/, (ws) => {
      const wsUrl = new URL(ws.url());
      logLine('WS', 'websocket', wsUrl.pathname, null, 'bloquee');
      blocked.set(`${wsUrl.pathname}|`, { pathname: wsUrl.pathname, action: null });
      ws.close({ code: 1000, reason: 'blocked by gate' });
    });

    const page = await context.newPage();

    // 1. GET de la page de connexion (autorisée par l'intercepteur ci-dessus).
    const loginPageResponse = await page.goto(`${ORIGIN}${LOGIN_PAGE_PATH}`, { waitUntil: 'load' });
    logDoc('page-connexion', loginPageResponse);

    // 2. Connexion — un seul essai, via context.request plutôt que le formulaire de la
    // page : ses sélecteurs DOM réels n'ont pas pu être vérifiés sans exécuter le script
    // contre la box, interdit ce tour (relecture ClaudeBox d'abord). context.request
    // partage les cookies du contexte (la session ouverte par le GET ci-dessus), mais ne
    // passe PAS par context.route : cette requête est donc émise puis journalisée ici
    // explicitement, en un seul appel maîtrisé par le script (pas de resoumission ni de
    // relance JS hors de notre contrôle), avec exactement les champs prescrits.
    const loginUrl = `${ORIGIN}${LOGIN_AJAX_PATH}`;
    logLine('POST', 'xhr', LOGIN_AJAX_PATH, 'login', 'authentification');
    const loginResponse = await context.request.post(loginUrl, {
      form: {
        action: 'login',
        username: credentials.username,
        password: credentials.password,
        twoFactorCode: '',
        storeConnection: '0',
      },
    });

    let state = 'inconnu';
    if (loginResponse.ok()) {
      try {
        const body = await loginResponse.json();
        if (body && typeof body.state === 'string') {
          state = body.state;
        }
      } catch {
        state = 'reponse-non-json';
      }
    }
    // Jamais le corps : seuls le code HTTP et le champ 'state' (ok/error) sont journalisés.
    console.log(`DOC authentification http=${loginResponse.status()} state=${state}`);

    if (state !== 'ok') {
      console.log('Connexion refusée ou réponse inattendue — arrêt immédiat, aucune autre requête.');
      return;
    }

    // 3. GET de la page du plugin (autorisée par l'intercepteur).
    const pluginPageResponse = await page.goto(
      `${ORIGIN}${PLUGIN_PAGE_PATH}?v=d&m=jeedom2ha&p=jeedom2ha`,
      { waitUntil: 'load' }
    );
    logDoc('page-plugin', pluginPageResponse);

    const finalUrl = new URL(pluginPageResponse.url());
    const reachedPluginPage = Object.entries(PLUGIN_PAGE_QUERY).every(
      ([key, value]) => finalUrl.searchParams.get(key) === value
    );
    if (!reachedPluginPage) {
      // Une chaîne de redirection a pu mener ailleurs (ex. retour à la page de connexion,
      // session refusée après coup) : les cibles de redirection ne sont pas interceptées
      // par context.route, donc ce contrôle après coup est la seule garantie ici.
      console.log('page du plugin non atteinte');
      return;
    }

    // Attente bornée pour laisser le chargement émettre ses requêtes (toutes
    // journalisées par l'intercepteur HTTP/WebSocket ci-dessus).
    await page.waitForTimeout(PAGE_LOAD_WAIT_MS);
  } finally {
    await context.close();
    await browser.close();
  }

  console.log('--- Requêtes bloquées, dédoublonnées (point d\'entrée, action) ---');
  for (const { pathname, action } of blocked.values()) {
    console.log(`${pathname} action=${action ?? '-'}`);
  }

  console.log('--- Décompte des requêtes par verdict ---');
  for (const [verdict, count] of verdictCounts) {
    console.log(`${verdict}: ${count}`);
  }
}

main().catch((err) => {
  console.error(err.message || String(err));
  process.exitCode = 1;
});
