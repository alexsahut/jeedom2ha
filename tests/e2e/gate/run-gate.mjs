#!/usr/bin/env node
/** Story 20.0 — lanceur du gate. Ne pas exécuter sans relecture ClaudeBox. */

import { execFile } from 'node:child_process';
import { mkdir, readFile, rm, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { assertNoOverrideOn, compareWitness, countWindow, takeWitness } from './lib/box-witness.mjs';
import { installInterceptor } from './lib/interceptor.mjs';
import { loadPlaywright } from './lib/playwright.mjs';
import {
  ac4Values,
  artifactsContain,
  calculateChecks,
  compareProbes,
  CONFIG_KEYS,
  extractBridgeStatus,
  extractConfigValues,
  hashValue,
  parseCredentials,
  sanitizeConsoleErrors,
  sanitizeReason,
  summarizeJournal,
  normalizeParcoursRecord,
} from './lib/report.mjs';
import { createState } from './lib/simulate.mjs';

const ORIGIN = 'https://domobox.famille-sahut.fr';
const PLUGIN = '/index.php?v=d&m=jeedom2ha&p=jeedom2ha';
const CREDENTIALS = process.env.JEEDOM2HA_GATE_CREDENTIALS
  || '/home/asahut/.config/jeedom2ha-gate/jeedom.env';

/** Lance le self-test isolé avant tout contact avec la box. */
function runChild(file) {
  return new Promise((resolve, reject) => {
    execFile(process.execPath, [file], { encoding: 'utf8' }, (error) => {
      if (error) reject(new Error(`processus-echec: ${error.message}`));
      else resolve();
    });
  });
}

/** Lit les deux paramètres obligatoires du lanceur. */
function parseArgs() {
  const values = process.argv.slice(2);
  const get = (name) => values[values.indexOf(name) + 1];
  if (!get('--parcours') || !get('--report')) {
    throw new Error('usage: --parcours <module> --report <dossier>');
  }
  return { parcours: get('--parcours'), report: get('--report') };
}

/** Lit le fichier protégé d'identifiants sans exposer son contenu. */
async function readCredentials() {
  const details = await stat(CREDENTIALS);
  if ((details.mode & 0o777) !== 0o600) throw new Error('droits-identifiants-non-600');
  return parseCredentials(await readFile(CREDENTIALS, 'utf8'));
}

/** Envoie une sonde AJAX et exige une réponse JSON exploitable. */
async function jsonPost(request, url, form) {
  const response = await request.post(url, { form });
  return response.json();
}

/** Relève le bridge et les huit clés, bornés strictement à la lecture seule. */
async function probe(request) {
  const bridgeResponse = await jsonPost(
    request,
    `${ORIGIN}/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php`,
    { action: 'getBridgeStatus' },
  );
  const configResponses = {};
  for (const key of CONFIG_KEYS) {
    configResponses[key] = await jsonPost(
      request,
      `${ORIGIN}/core/ajax/config.ajax.php`,
      { action: 'getKey', plugin: 'jeedom2ha', key },
    );
  }
  const configValues = extractConfigValues(configResponses);
  return {
    bridge: extractBridgeStatus(bridgeResponse),
    configHash: hashValue(configValues),
    configValues,
  };
}

/** Vérifie que la navigation est restée exactement sur la page plugin attendue. */
function expectedUrl(page) {
  const url = new URL(page.url());
  return url.origin === ORIGIN
    && url.pathname === '/index.php'
    && url.searchParams.get('v') === 'd'
    && url.searchParams.get('m') === 'jeedom2ha'
    && url.searchParams.get('p') === 'jeedom2ha';
}

/** Vérifie les origines de toute la chaîne de redirections. */
function redirectsStayOnOrigin(response) {
  let request = response?.request()?.redirectedFrom();
  while (request) {
    if (new URL(request.url()).origin !== ORIGIN) return false;
    request = request.redirectedFrom();
  }
  return true;
}

/** Ferme toutes les pages, y compris les popups ouvertes par le parcours. */
async function closePages(context) {
  if (!context) return;
  await Promise.all(context.pages().map((page) => page.close().catch(() => undefined)));
}

/** Attend 90 secondes après la dernière requête enregistrée par l'intercepteur. */
async function waitForQuietWindow(journal) {
  const last = journal.entries.at(-1)?.timestamp;
  const delay = last ? Math.max(0, 90_000 - (Date.now() - Date.parse(last))) : 90_000;
  await new Promise((resolve) => setTimeout(resolve, delay));
}

/** Crée le collecteur borné des constats DOM transmis par le parcours. */
function createRecorder(parcours) {
  return (key, value) => {
    const [safeKey, safeValue] = normalizeParcoursRecord(key, value);
    if (Object.hasOwn(parcours, safeKey)) throw new Error('parcours-record-cle-dupliquee');
    parcours[safeKey] = safeValue;
  };
}

/** Supprime les rapports si un contrôle AC4 détecte une valeur en clair. */
export async function enforceAc4(reportDir, values) {
  const files = ['gate-report.md', 'gate-report.json'].map((name) => path.join(reportDir, name));
  const texts = await Promise.all(files.map((file) => readFile(file, 'utf8')));
  const categories = artifactsContain(values, texts);
  if (categories.length === 0) return;
  await Promise.all(files.map((file) => rm(file, { force: true })));
  await writeFile(path.join(reportDir, 'gate-report-ac4.txt'), `FAIL ac4\n${categories.join('\n')}\n`);
  throw new Error(`ac4-fuite-rapport:${categories.join(',')}`);
}

/** Écrit le rapport final, y compris lorsqu'un parcours a échoué après le témoin initial. */
async function writeReport(reportDir, data, secrets) {
  const { checks, activity } = calculateChecks(data);
  const payload = {
    verdict: !data.failure && Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL',
    checks,
    differences: [...data.witnessDifferences, ...data.probeDifferences],
    window: data.window,
    interceptor: {
      verdicts: summarizeJournal(data.journal),
      failures: data.journal.failures,
      simulated: data.journal.entries.filter(
        (entry) => ['simulee', 'lecture-simulee', 'apercu-simule', 'lecture-derivee'].includes(entry.verdict),
      ),
    },
    console: { count: data.consoleErrors.length, messages: sanitizeConsoleErrors(data.consoleErrors) },
    parcours: data.parcours,
    reason: data.failure ? sanitizeReason(data.failure) : null,
    note: 'badge « pas encore appliqué » non prouvé par le gate',
  };
  const lines = Object.entries(checks).map(([name, pass]) => `- ${name}: ${pass ? 'PASS' : 'FAIL'}`);
  const markdown = [
    '# Gate report',
    '',
    `Verdict: **${payload.verdict}**`,
    '',
    ...(activity ? ['activité sur la box pendant le parcours : parcours non concluant', ''] : []),
    ...lines,
    ...(payload.reason ? ['', `Raison: ${payload.reason}`] : []),
    '',
    payload.note,
    '',
  ].join('\n');
  await mkdir(reportDir, { recursive: true });
  await writeFile(path.join(reportDir, 'gate-report.json'), JSON.stringify(payload, null, 2));
  await writeFile(path.join(reportDir, 'gate-report.md'), markdown);
  await enforceAc4(reportDir, secrets);
  return payload;
}

/** Exécute le parcours puis garantit le témoin final et un rapport après témoin initial. */
async function main() {
  const { parcours: modulePath, report: reportDir } = parseArgs();
  const ownDirectory = path.dirname(fileURLToPath(import.meta.url));
  await runChild(path.join(ownDirectory, 'interceptor-selftest.mjs'));
  const credentials = await readCredentials();
  const parcours = await import(pathToFileURL(path.resolve(modulePath)).href);
  if (!parcours.name || !parcours.declaredEquipments || !Array.isArray(parcours.declaredBascules)) {
    throw new Error('parcours-invalide');
  }
  if (typeof parcours.run !== 'function') throw new Error('parcours-invalide');

  const before = await takeWitness();
  if (!before.readable || !['info', 'debug'].includes(before.daemon.logLevel)) {
    throw new Error('temoin-avant-invalide');
  }
  assertNoOverrideOn(before, Object.keys(parcours.declaredEquipments));

  const journal = { entries: [], failed: false, failures: [] };
  const consoleErrors = [];
  const data = {
    journal,
    consoleErrors,
    witnessDifferences: [],
    probeDifferences: [],
    parcours: {},
    window: {},
  };
  let browser;
  let context;
  let failure;
  let probeBefore;
  let probeAfter;
  try {
    const { chromium } = loadPlaywright();
    browser = await chromium.launch({ headless: true });
    context = await browser.newContext({ serviceWorkers: 'block' });
    const simState = createState();
    const ctx = {
      origin: ORIGIN,
      loginAttempts: 0,
      declaredEquipments: parcours.declaredEquipments,
      lastPreviewType: simState.lastPreviewType,
    };
    await installInterceptor(context, { ctx, simState, journal, declaredBascules: parcours.declaredBascules });
    ctx.loginAttempts = 1;
    const login = await jsonPost(context.request, `${ORIGIN}/core/ajax/user.ajax.php`, {
      action: 'login',
      username: credentials.username,
      password: credentials.password,
      twoFactorCode: '',
      storeConnection: '0',
    });
    if (login?.state !== 'ok') throw new Error('connexion-echouee');
    probeBefore = await probe(context.request);
    const page = await context.newPage();
    page.on('console', (message) => {
      if (message.type() === 'error') consoleErrors.push(message.text());
    });
    page.on('pageerror', (error) => consoleErrors.push(error.message));
    const navigation = await page.goto(`${ORIGIN}${PLUGIN}`, { waitUntil: 'load' });
    if (!expectedUrl(page) || !redirectsStayOnOrigin(navigation)) {
      throw new Error('navigation-finale-invalide');
    }
    await parcours.run(page, {
      journal,
      simState,
      ctx,
      helpers: { record: createRecorder(data.parcours) },
    });
  } catch (error) {
    failure = error instanceof Error ? error : new Error(String(error));
  } finally {
    await closePages(context);
    await waitForQuietWindow(journal);
    try {
      if (context) probeAfter = await probe(context.request);
    } catch (error) {
      failure ??= error instanceof Error ? error : new Error(String(error));
    }
    const after = await takeWitness();
    data.witnessDifferences = compareWitness(before, after);
    data.probeDifferences = probeBefore && probeAfter
      ? compareProbes(probeBefore, probeAfter)
      : ['sondes-illisibles'];
    try {
      data.window = await countWindow(before.clock, after.clock);
    } catch (error) {
      failure ??= error instanceof Error ? error : new Error(String(error));
    }
    data.failure = failure;
    const configValues = probeBefore?.configValues ?? probeAfter?.configValues ?? {};
    try {
      const result = await writeReport(reportDir, data, ac4Values(credentials.values, configValues));
      if (result.verdict !== 'PASS') process.exitCode = 1;
    } finally {
      await context?.close().catch(() => undefined);
      await browser?.close().catch(() => undefined);
    }
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
