#!/usr/bin/env node
/** Story 23.2 — captures et vidéo de promotion rejouables, sur la démo synthétique 23.1/23.2 uniquement.
 *
 * Usage (poste de ClaudeBox/clawcode ayant accès à la VM de démo ; jamais depuis le cloud) :
 *   node tests/e2e/captures/run-captures.mjs --plan                                # plan hors-ligne, aucun navigateur
 *   node tests/e2e/captures/run-captures.mjs --env-file <chemin-hors-depot> --out docs/fr_FR/images --video-out <dossier>
 *   options : --only shots|video   --skip-ha
 *
 * Réutilise du gate 20-0 la résolution de Playwright hors dépôt (`tests/e2e/gate/lib/playwright.mjs`). Le gate lui-même
 * (intercepteur en lecture seule) n'est PAS utilisé ici : « Relire Jeedom » et le pilotage d'une lumière depuis Home
 * Assistant sont des écritures voulues, permises uniquement par les comptes dédiés `j2ha-captures` (D3) sur la démo.
 *
 * Déterminisme : viewport 1280×720, fr-FR, fuseau fixe, thème clair forcé (colorScheme + contrôle du fond effectif,
 * échec fermé), animations coupées, attente des rafraîchissements par sélecteur (jamais par durée seule),
 * contrôle CC-48 du texte visible avant chaque capture. Aucun identifiant n'est écrit ni journalisé.
 *
 * Les sélecteurs sont NON DÉMONTRÉS sur la VM : la première exécution terrain peut exiger des ajustements
 * (et c'est à ce moment seulement que les marqueurs CAPTURE-A-PRENDRE pourront être remplacés).
 */

import { execFileSync } from 'node:child_process';
import { mkdir, readFile, rename, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadPlaywright } from '../gate/lib/playwright.mjs';
import { assertEnvOutsideRepo, parseEnvText, redact, validateConfig } from './lib/config.mjs';
import { assertManifestClean, buildManifest, findLeaks, isLightBackground, sha256 } from './lib/safety.mjs';
import {
  COLOR_SCHEME, DEMO, EXTRA_SHOTS, LOCALE, MANIFEST_FILE, SHOTS, TIMEZONE, VIDEO_FILE, VIDEO_MAX_SECONDS,
  VIDEO_STEPS, VIEWPORT, plannedHoldSeconds,
} from './lib/storyboard.mjs';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const PLUGIN_PATH = '/index.php?v=d&m=jeedom2ha&p=jeedom2ha';
const PLUGIN_CONFIG_PATH = '/index.php?v=d&p=plugin&id=jeedom2ha';
const PLUGINS_PATH = '/index.php?v=d&p=plugin';
const WV = '#j2ha_workView';
const STEP_TIMEOUT_MS = 30_000;
const FREEZE_CSS = '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}';

function parseArgs(argv) {
  const args = { only: null, skipHa: false, plan: false, out: path.join(REPO_ROOT, 'docs/fr_FR/images'), videoOut: null, envFile: null };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--plan') args.plan = true;
    else if (arg === '--skip-ha') args.skipHa = true;
    else if (arg === '--only') args.only = argv[++i];
    else if (arg === '--env-file') args.envFile = argv[++i];
    else if (arg === '--out') args.out = path.resolve(argv[++i]);
    else if (arg === '--video-out') args.videoOut = path.resolve(argv[++i]);
    else throw new Error(`option-inconnue: ${arg}`);
  }
  if (args.only && !['shots', 'video'].includes(args.only)) throw new Error('option-only-invalide');
  return args;
}

export function buildPlan(args) {
  const shots = [...SHOTS, ...EXTRA_SHOTS].filter((s) => !(args.skipHa && s.app === 'homeassistant'));
  return {
    viewport: VIEWPORT, locale: LOCALE, theme: COLOR_SCHEME,
    shots: args.only === 'video' ? [] : shots.map((s) => ({ id: s.id, file: s.file, marker: s.marker })),
    video: args.only === 'shots' ? null : { file: VIDEO_FILE, max_seconds: VIDEO_MAX_SECONDS, hold_seconds: plannedHoldSeconds(), steps: VIDEO_STEPS.map((s) => s.label) },
  };
}

function regenerateCommand() {
  return 'node tests/e2e/captures/run-captures.mjs --env-file <chemin-hors-depot> --out docs/fr_FR/images --video-out <dossier>';
}

async function atStep(label, operation) {
  try {
    return await operation();
  } catch (error) {
    const message = error instanceof Error ? error.message.split(/\r?\n/, 1)[0] : String(error);
    throw new Error(`etape ${label} : ${message}`);
  }
}

/** Contexte déterministe : taille, langue, fuseau, thème clair, mouvements réduits ; vidéo si demandée. */
async function newContext(browser, videoDir) {
  const options = {
    viewport: VIEWPORT, locale: LOCALE, timezoneId: TIMEZONE, colorScheme: COLOR_SCHEME, reducedMotion: 'reduce',
    deviceScaleFactor: 1, serviceWorkers: 'block',
  };
  if (videoDir) options.recordVideo = { dir: videoDir, size: VIEWPORT };
  const context = await browser.newContext(options);
  context.setDefaultTimeout(STEP_TIMEOUT_MS);
  await context.addInitScript(({ css }) => {
    const apply = () => {
      const style = document.createElement('style');
      style.textContent = css;
      (document.head || document.documentElement).appendChild(style);
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', apply); else apply();
  }, { css: FREEZE_CSS });
  return context;
}

async function loginJeedom(page, cfg) {
  await page.goto(`${cfg.jeedom.origin}/index.php?v=d`, { waitUntil: 'domcontentloaded' });
  const user = page.locator('#in_login_username');
  if (await user.count()) {
    await user.fill(cfg.jeedom.user);
    await page.locator('#in_login_password').fill(cfg.jeedom.password);
    await page.locator('#bt_login').click();
  }
  await page.locator('#bt_getHelp, #bt_getHelpTop, .navbar').first().waitFor({ state: 'attached' });
}

async function loginHomeAssistant(page, cfg) {
  await page.goto(cfg.homeAssistant.origin, { waitUntil: 'domcontentloaded' });
  const user = page.locator('input[name="username"]');
  if (await user.count()) {
    await user.fill(cfg.homeAssistant.user);
    await page.locator('input[name="password"]').fill(cfg.homeAssistant.password);
    await page.locator('mwc-button, ha-button, button').filter({ hasText: /connexion|log in|sign in/i }).first().click();
  }
  await page.locator('home-assistant').waitFor({ state: 'attached' });
}

/** (D1) Thème clair prouvé : le fond effectif de la page doit être clair, sinon on n'enregistre rien. */
async function assertLightTheme(page) {
  const color = await page.evaluate(() => {
    for (const node of [document.querySelector('#div_pageContainer'), document.body, document.documentElement]) {
      if (!node) continue;
      const value = getComputedStyle(node).backgroundColor;
      if (value && !/rgba\(0, 0, 0, 0\)|transparent/.test(value)) return value;
    }
    return '';
  });
  if (!isLightBackground(color)) throw new Error('theme-clair-non-obtenu');
}

/** CC-48 : masque les champs du broker puis refuse toute fuite visible (IP, nom d'hôte, URL, jeton, identifiants). */
async function scrubAndAssertClean(page, secrets) {
  await page.evaluate(() => {
    for (const key of ['mqttHost', 'mqttPort', 'mqttUser', 'mqttPassword']) {
      document.querySelectorAll(`[data-l1key="${key}"]`).forEach((input) => { input.value = ''; });
    }
  });
  const visible = await page.evaluate(() => {
    const values = [...document.querySelectorAll('input, textarea')].map((i) => (i.type === 'password' ? '' : i.value));
    return `${document.body.innerText}\n${values.join('\n')}`;
  });
  const findings = findLeaks(visible, secrets);
  if (findings.length) throw new Error(`fuite-cc48: ${findings.join(', ')}`);
}

async function settle(page) {
  await page.waitForLoadState('networkidle', { timeout: STEP_TIMEOUT_MS }).catch(() => {});
}

async function openPluginPage(page, cfg) {
  await page.goto(`${cfg.jeedom.origin}${PLUGIN_PATH}`, { waitUntil: 'domcontentloaded' });
  await page.locator('#j2ha_houseNumber').waitFor({ state: 'attached' });
  await page.waitForFunction(() => (document.querySelector('#j2ha_houseNumber')?.textContent ?? '').trim() !== '');
  await page.locator('#j2ha_roomCards .j2ha-room-card').first().waitFor({ state: 'visible' });
  await page.locator('#bt_rescanTopology').waitFor({ state: 'visible' });
  await settle(page);
}

async function openRoom(page, name) {
  await page.locator('#j2ha_roomCards .j2ha-room-card').filter({ hasText: name }).first().click();
  await page.locator(WV).waitFor({ state: 'visible' });
  await page.locator(`${WV} .j2ha-wv-eq`).first().waitFor({ state: 'visible' });
  await settle(page);
}

async function selectEquipment(page, locator) {
  await locator.locator('.j2ha-wv-row').click();
  await page.locator(`${WV} .j2ha-eq-panel .j2ha-eq-counters`).waitFor({ state: 'visible' });
  await page.locator(`${WV} .j2ha-eq-panel .j2ha-cmd-table`).waitFor({ state: 'visible' });
  await settle(page);
}

async function saveShot(page, outDir, shot, secrets, files, clip) {
  await assertLightTheme(page);
  await scrubAndAssertClean(page, secrets);
  const buffer = clip ? await clip.screenshot({ animations: 'disabled' }) : await page.screenshot({ animations: 'disabled' });
  const file = path.join(outDir, shot.file);
  await writeFile(file, buffer);
  files.push({ id: shot.id, file: shot.file, sha256: sha256(buffer), bytes: buffer.length });
}

/** Captures 1 à 8 (Jeedom) selon le storyboard, puis la capture Home Assistant. */
async function runShots(browser, cfg, args, files) {
  const context = await newContext(browser, null);
  const page = await context.newPage();
  const byId = Object.fromEntries([...SHOTS, ...EXTRA_SHOTS].map((s) => [String(s.id), s]));
  try {
    await atStep('connexion Jeedom', () => loginJeedom(page, cfg));
    await atStep('1 page principale', async () => {
      await openPluginPage(page, cfg);
      await saveShot(page, args.out, byId[1], cfg.secrets, files);
    });
    await atStep('2 cartes de pièce', async () => {
      const card = page.locator('#j2ha_roomCards .j2ha-room-card').filter({ hasText: DEMO.blockedRoom }).first();
      await saveShot(page, args.out, byId[2], cfg.secrets, files, card);
      const garage = page.locator('#j2ha_roomCards .j2ha-room-card').filter({ hasText: DEMO.excludedRoom }).first();
      await saveShot(page, args.out, byId['2b'], cfg.secrets, files, garage);
    });
    await atStep('3 vue de travail', async () => {
      await openRoom(page, DEMO.searchRoom);
      await page.locator(`${WV} .j2ha-wv-widen`).click().catch(() => {});
      await page.locator(`${WV} .j2ha-wv-search`).fill(DEMO.searchRoom);
      await page.locator(`${WV} .j2ha-wv-room`).first().waitFor({ state: 'visible' });
      const rows = page.locator(`${WV} .j2ha-wv-eq`);
      await selectEquipment(page, rows.first());
      await saveShot(page, args.out, byId[3], cfg.secrets, files);
    });
    await atStep('4 détail d’un équipement', async () => {
      const row = page.locator(`${WV} .j2ha-wv-eq`).filter({ hasText: DEMO.publishedEquipment }).first();
      await selectEquipment(page, row);
      await page.locator(`${WV} .j2ha-eq-panel .j2ha-eq-controls`).waitFor({ state: 'visible' });
      await saveShot(page, args.out, byId[4], cfg.secrets, files);
    });
    await atStep('5 tableau des commandes', async () => {
      await selectEquipment(page, page.locator(`${WV} .j2ha-wv-eq`).nth(DEMO.commandsEquipmentIndex));
      await page.locator(`${WV} .j2ha-eq-panel .j2ha-cmd-table`).scrollIntoViewIfNeeded();
      await saveShot(page, args.out, byId[5], cfg.secrets, files);
    });
    await atStep('6 compteurs du détail de pièce', async () => {
      await openPluginPage(page, cfg);
      await openRoom(page, DEMO.blockedRoom);
      await saveShot(page, args.out, byId[6], cfg.secrets, files);
    });
    await atStep('7 ligne de compteurs d’un équipement déplié', async () => {
      const row = page.locator(`${WV} .j2ha-wv-eq`).filter({ hasText: DEMO.blockedEquipment }).first();
      await selectEquipment(page, row);
      await saveShot(page, args.out, byId[7], cfg.secrets, files);
    });
    await atStep('8 configuration', async () => {
      await page.goto(`${cfg.jeedom.origin}${PLUGIN_CONFIG_PATH}`, { waitUntil: 'domcontentloaded' });
      const excluded = page.locator('#lbl_excludedPlugins');
      await excluded.waitFor({ state: 'visible' });
      await excluded.scrollIntoViewIfNeeded();
      await settle(page);
      await saveShot(page, args.out, byId[8], cfg.secrets, files);
    });
    if (!args.skipHa) {
      await atStep('9 Home Assistant', async () => {
        await loginHomeAssistant(page, cfg);
        await page.goto(`${cfg.homeAssistant.origin}/config/devices/dashboard`, { waitUntil: 'domcontentloaded' });
        await page.getByText(DEMO.haLight).first().waitFor({ state: 'visible' });
        await settle(page);
        await saveShot(page, args.out, byId[9], cfg.secrets, files);
      });
    }
  } finally {
    await context.close();
  }
}

/** Vidéo : un seul contexte enregistré, étapes du storyboard vidéo, durée contrôlée (≤ 2 min). */
async function runVideo(browser, cfg, args) {
  await mkdir(args.videoOut, { recursive: true });
  const context = await newContext(browser, args.videoOut);
  const page = await context.newPage();
  const hold = (id) => page.waitForTimeout(VIDEO_STEPS.find((s) => s.id === id).holdMs);
  const started = Date.now();
  let video;
  try {
    video = page.video();
    await atStep('vidéo : connexion', () => loginJeedom(page, cfg));
    await atStep('vidéo : plugins', async () => {
      await page.goto(`${cfg.jeedom.origin}${PLUGINS_PATH}`, { waitUntil: 'domcontentloaded' });
      await settle(page);
      await assertLightTheme(page);
      await hold('plugins');
    });
    await atStep('vidéo : dépendances et démon', async () => {
      await page.goto(`${cfg.jeedom.origin}${PLUGIN_CONFIG_PATH}`, { waitUntil: 'domcontentloaded' });
      await settle(page);
      await scrubAndAssertClean(page, cfg.secrets);
      await hold('dependances');
    });
    await atStep('vidéo : relire Jeedom', async () => {
      await openPluginPage(page, cfg);
      await page.locator('#bt_rescanTopology').click();
      await settle(page);
      await page.locator('#j2ha_houseNumber').waitFor({ state: 'visible' });
      await hold('relire');
    });
    await atStep('vidéo : pièce', async () => {
      await openRoom(page, DEMO.searchRoom);
      await hold('piece');
    });
    await atStep('vidéo : équipement', async () => {
      await selectEquipment(page, page.locator(`${WV} .j2ha-wv-eq`).filter({ hasText: DEMO.publishedEquipment }).first());
      await hold('equipement');
    });
    await atStep('vidéo : Home Assistant appareils', async () => {
      await loginHomeAssistant(page, cfg);
      await page.goto(`${cfg.homeAssistant.origin}/config/devices/dashboard`, { waitUntil: 'domcontentloaded' });
      await page.getByText(DEMO.haLight).first().waitFor({ state: 'visible' });
      await hold('ha-appareils');
    });
    await atStep('vidéo : pilotage Home Assistant', async () => {
      await page.getByText(DEMO.haLight).first().click();
      const toggle = page.getByRole('switch').first();
      await toggle.waitFor({ state: 'visible' });
      await toggle.click();
      await hold('ha-pilotage');
    });
    await atStep('vidéo : retour d’état dans Jeedom', async () => {
      await openPluginPage(page, cfg);
      await openRoom(page, DEMO.searchRoom);
      await hold('retour');
    });
  } finally {
    await context.close(); // finalise le fichier vidéo
  }
  const seconds = (Date.now() - started) / 1000;
  if (seconds > VIDEO_MAX_SECONDS) throw new Error(`video-trop-longue: ${Math.round(seconds)} s > ${VIDEO_MAX_SECONDS} s`);
  const target = path.join(args.videoOut, VIDEO_FILE);
  await rename(await video.path(), target);
  const info = await stat(target);
  return { file: VIDEO_FILE, seconds: Math.round(seconds), bytes: info.size, versioned: false };
}

function gitValue(args) {
  try { return execFileSync('git', args, { cwd: REPO_ROOT, encoding: 'utf8' }).trim(); } catch { return null; }
}

export async function main(argv) {
  const args = parseArgs(argv);
  if (args.plan) {
    process.stdout.write(`${JSON.stringify(buildPlan(args), null, 2)}\n`);
    return;
  }
  if (!args.envFile) throw new Error('env-file-requis');
  assertEnvOutsideRepo(args.envFile, REPO_ROOT);
  const cfg = validateConfig(parseEnvText(await readFile(args.envFile, 'utf8')));
  if (args.only !== 'shots' && !args.videoOut) throw new Error('video-out-requis');
  const info = JSON.parse(await readFile(path.join(REPO_ROOT, 'plugin_info/info.json'), 'utf8'));
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch();
  const files = [];
  let video = null;
  try {
    if (args.only !== 'video') {
      await mkdir(args.out, { recursive: true });
      await runShots(browser, cfg, args, files);
    }
    if (args.only !== 'shots') video = await runVideo(browser, cfg, args);
  } catch (error) {
    throw new Error(redact(error instanceof Error ? error.message : String(error), cfg.secrets));
  } finally {
    await browser.close();
  }
  if (files.length) {
    const manifest = buildManifest({
      pluginVersion: info.pluginVersion, sourceCommit: gitValue(['rev-parse', '--short', 'HEAD']),
      date: new Date().toISOString().slice(0, 10), files, command: regenerateCommand(), video,
    });
    assertManifestClean(manifest, cfg.secrets);
    await writeFile(path.join(args.out, MANIFEST_FILE), `${JSON.stringify(manifest, null, 2)}\n`);
  }
  process.stdout.write(`captures: ${files.length} fichier(s)${video ? `, vidéo ${video.seconds} s` : ''} — relecture CC-48 et concordance (Task 5) à faire\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).catch((error) => {
    process.stderr.write(`erreur : ${error.message}\n`);
    process.exit(1);
  });
}
