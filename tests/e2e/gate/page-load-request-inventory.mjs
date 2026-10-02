#!/usr/bin/env node
/**
 * Story 20.0 (Task 1) — relevé des requêtes émises au chargement de la page du plugin.
 *
 * Script de reconnaissance, pas encore le gate complet (Tasks 2-4) : il ouvre un seul
 * contexte Chromium headless, refuse toute requête par défaut, n'autorise que les GET
 * statiques, la page de connexion et la page du plugin, fait un seul essai de connexion,
 * puis journalise le verdict de chaque requête observée pendant le chargement. Sert à
 * établir, avec des faits d'exécution (pas seulement la lecture du code), la liste des
 * couples (point d'entrée, action) que Task 1 doit inscrire explicitement comme lectures
 * nécessaires (AC1).
 *
 * NE PAS EXÉCUTER sans relecture de ClaudeBox au préalable (règle de l'unité 20-0).
 *
 * Exécution prévue (hors de ce tour) : Playwright est installé hors du dépôt, dans
 * /home/asahut/.openclaw/tools/jeedom2ha-gate (node_modules, Chromium en cache). Lancer
 * ce script suppose donc de résoudre le module 'playwright' depuis cet emplacement
 * externe (par ex. NODE_PATH=/home/asahut/.openclaw/tools/jeedom2ha-gate/node_modules
 * node tests/e2e/gate/page-load-request-inventory.mjs), wiring laissé à la Task 2
 * (« Mettre en place Playwright contre une page du plugin »).
 *
 * Aucune capture, trace, HAR ni état de session n'est écrite sur disque : le journal va
 * uniquement sur stdout, à rediriger par l'appelant s'il veut le conserver.
 */

import { chromium } from 'playwright';
import { statSync, readFileSync } from 'node:fs';

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

/** Extrait uniquement la valeur du paramètre 'action' (query string ou corps urlencoded),
 * jamais le reste du corps ou des paramètres (identifiants, cmdId, selection, etc.). */
function extractAction(request, url) {
  const qsAction = url.searchParams.get('action');
  if (qsAction) return qsAction;
  if (request.method() === 'POST') {
    const postData = request.postData();
    if (postData) {
      try {
        const params = new URLSearchParams(postData);
        const action = params.get('action');
        if (action) return action;
      } catch {
        // corps non urlencoded : jamais journalisé tel quel, action reste absente.
      }
    }
  }
  return null;
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

function logLine(method, resourceType, pathname, action, verdict) {
  const ts = new Date().toISOString();
  const actionPart = action ? `action=${action}` : 'action=-';
  console.log(`${ts} ${method} ${resourceType} ${pathname} ${actionPart} verdict=${verdict}`);
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
      const action = extractAction(request, url);
      const method = request.method();
      const resourceType = request.resourceType();

      let allowed = false;
      if (isAllowedStatic(request, url)) {
        allowed = true;
      } else if (isLoginPageDocument(request, url)) {
        allowed = true;
      } else if (isPluginPageDocument(request, url)) {
        allowed = true;
      }

      if (allowed) {
        logLine(method, resourceType, pathname, action, 'autorisee');
        await route.continue();
        return;
      }

      logLine(method, resourceType, pathname, action, 'bloquee');
      blocked.set(`${pathname}|${action ?? ''}`, { pathname, action });
      await route.abort('blockedbyclient');
    });

    const page = await context.newPage();

    // 1. GET de la page de connexion (autorisée par l'intercepteur ci-dessus).
    await page.goto(`${ORIGIN}${LOGIN_PAGE_PATH}`, { waitUntil: 'load' });

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

    let loginOk = false;
    if (loginResponse.ok()) {
      try {
        const body = await loginResponse.json();
        loginOk = body && body.state === 'ok';
      } catch {
        loginOk = false;
      }
    }

    if (!loginOk) {
      console.log('Connexion refusée ou réponse inattendue — arrêt immédiat, aucune autre requête.');
      return;
    }

    // 3. GET de la page du plugin (autorisée), puis attente bornée pour laisser le
    // chargement émettre ses requêtes (toutes journalisées par l'intercepteur).
    await page.goto(`${ORIGIN}${PLUGIN_PAGE_PATH}?v=d&m=jeedom2ha&p=jeedom2ha`, { waitUntil: 'load' });
    await page.waitForTimeout(PAGE_LOAD_WAIT_MS);
  } finally {
    await context.close();
    await browser.close();
  }

  console.log('--- Requêtes bloquées, dédoublonnées (point d\'entrée, action) ---');
  for (const { pathname, action } of blocked.values()) {
    console.log(`${pathname} action=${action ?? '-'}`);
  }
}

main().catch((err) => {
  console.error(err.message || String(err));
  process.exitCode = 1;
});
