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
import { assertManifestClean, buildManifest, findLeaks, isLightBackground, mergeManifest, sha256 } from './lib/safety.mjs';
import {
  COLOR_SCHEME, DEMO, EXTRA_SHOTS, LOCALE, MANIFEST_FILE, SHOTS, TIMEZONE, VIDEO_FILE, VIDEO_MAX_SECONDS,
  VIEWPORT, plannedHoldSeconds, videoSteps,
} from './lib/storyboard.mjs';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const PLUGIN_PATH = '/index.php?v=d&m=jeedom2ha&p=jeedom2ha';
const PLUGIN_CONFIG_PATH = '/index.php?v=d&p=plugin&id=jeedom2ha';
const PLUGINS_PATH = '/index.php?v=d&p=plugin';
const WV = '#j2ha_workView';
const STEP_TIMEOUT_MS = 30_000;
const RESCAN_TIMEOUT_MS = 90_000;
export const JEEDOM_LOGIN_FORM = '#in_login_username';
export const HA_LOGIN_FORM = 'input[name="username"]';
export const HA_APP = 'home-assistant';
export const JEEDOM_LOGIN_BUTTON = '#bt_login_validate';
const FREEZE_CSS = '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}';
// CC-48 : injecté dès la création de chaque page (captures ET vidéo), donc actif avant le premier rendu : les champs du
// broker, leurs indications et la note « broker » de la barre d'état ne sont jamais dessinés, donc jamais enregistrés.
const MASK_CSS = [
  '.configKey[data-l1key="mqttHost"],.configKey[data-l1key="mqttPort"],.configKey[data-l1key="mqttUser"],',
  '#in_mqttPassword{color:transparent!important;text-shadow:none!important;-webkit-text-security:none}',
  '.configKey[data-l1key^="mqtt"]::placeholder,#in_mqttPassword::placeholder{color:transparent!important}',
  '#span_healthMqttBroker{visibility:hidden!important}',
].join('');

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
    video: args.only === 'shots' ? null : {
      file: VIDEO_FILE, max_seconds: VIDEO_MAX_SECONDS, hold_seconds: plannedHoldSeconds(videoSteps(args)),
      steps: videoSteps(args).map((s) => s.label),
    },
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
async function newContext(browser, videoDir, cfg) {
  const options = {
    viewport: VIEWPORT, locale: LOCALE, timezoneId: TIMEZONE, colorScheme: COLOR_SCHEME, reducedMotion: 'reduce',
    deviceScaleFactor: 1, serviceWorkers: 'block',
  };
  if (videoDir) options.recordVideo = { dir: videoDir, size: VIEWPORT };
  const context = await browser.newContext(options);
  context.setDefaultTimeout(STEP_TIMEOUT_MS);
  await context.addInitScript(({ freeze, mask, loginSelector }) => {
    const apply = () => {
      const style = document.createElement('style');
      // Cœur Jeedom 4.6.1 : geler les animations sur la page de connexion empêche la connexion d'aboutir (constaté sur la
      // VM 122 le 2026-10-31). Le gel ne s'applique donc pas à cette page ; le masquage CC-48, lui, s'applique partout.
      style.textContent = document.querySelector(loginSelector) ? mask : `${freeze}${mask}`;
      (document.head || document.documentElement).appendChild(style);
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', apply); else apply();
  }, { freeze: FREEZE_CSS, mask: MASK_CSS, loginSelector: JEEDOM_LOGIN_FORM });
  if (cfg.homeAssistant) {
    // Home Assistant mémorise son thème côté navigateur : on le fixe en clair avant le premier chargement de son origine.
    // NON DÉMONTRÉ : le contrôle `assertLightTheme` reste le garde-fou si la clé change ou si le profil l'écrase.
    await context.addInitScript(({ origin }) => {
      if (location.origin !== origin) return;
      try { localStorage.setItem('selectedTheme', JSON.stringify({ dark: false })); } catch { /* stockage indisponible */ }
    }, { origin: cfg.homeAssistant.origin });
  }
  return context;
}


export const JEEDOM_PASSWORD_CHANGE = '#in_change_password';

async function loginJeedom(page, cfg) {
  await page.goto(`${cfg.jeedom.origin}/index.php?v=d`, { waitUntil: 'domcontentloaded' });
  const user = page.locator(JEEDOM_LOGIN_FORM);
  if (await user.count()) {
    await user.fill(cfg.jeedom.user);
    await page.locator('#in_login_password').fill(cfg.jeedom.password);
    // Cœur Jeedom 4.6.1 (desktop/php/connection.php) : le bouton est `#bt_login_validate`.
    await page.locator(JEEDOM_LOGIN_BUTTON).click();
    // Première connexion d'un compte : le cœur peut imposer un changement de mot de passe. On attend l'un ou l'autre
    // (connecté, ou formulaire de changement visible) avant de décider : échec fermé, explicite.
    const connected = page.locator('#bt_getHelp, #bt_getHelpTop, .navbar').first();
    const passwordChange = page.locator(JEEDOM_PASSWORD_CHANGE);
    await Promise.race([
      connected.waitFor({ state: 'attached' }),
      passwordChange.waitFor({ state: 'visible' }),
    ]);
    if (await passwordChange.isVisible()) throw new Error('jeedom-changement-mot-de-passe-exige');
  }
  await page.locator('#bt_getHelp, #bt_getHelpTop, .navbar').first().waitFor({ state: 'attached' });
  await forceJeedomLightTheme(page, cfg);
}

async function loginHomeAssistant(page, cfg) {
  await page.goto(cfg.homeAssistant.origin, { waitUntil: 'domcontentloaded' });
  // HA rend son formulaire de connexion après le chargement (redirection JS vers /auth/authorize) : un `count()` immédiat
  // vaut 0 et sautait la connexion (VM 122, 2026-10-31). On attend donc l'un ou l'autre : formulaire, ou application.
  const user = page.locator(HA_LOGIN_FORM);
  const app = page.locator(HA_APP);
  await Promise.race([
    user.waitFor({ state: 'visible' }),
    app.waitFor({ state: 'attached' }),
  ]).catch(() => {});
  if (await user.isVisible()) {
    await user.fill(cfg.homeAssistant.user);
    const password = page.locator('input[name="password"]');
    await password.fill(cfg.homeAssistant.password);
    // Entrée plutôt qu'un bouton : son libellé dépend de la langue (« Se connecter » en français).
    await password.press('Enter');
  }
  await app.waitFor({ state: 'attached' });
}

/**
 * (D1) Thème clair indépendant du compte : en plus de `colorScheme: light`, choisit « clair » dans le profil Jeedom si le
 * compte est réglé autrement. NON DÉMONTRÉ (sélecteurs du profil Jeedom) : `assertLightTheme` reste le garde-fou fermé,
 * contrôlé à chaque écran de la vidéo comme de chaque capture.
 */
async function forceJeedomLightTheme(page, cfg) {
  await page.goto(`${cfg.jeedom.origin}/index.php?v=d&p=profils`, { waitUntil: 'domcontentloaded' });
  const select = page.locator('select').filter({ has: page.locator('option', { hasText: /light|clair/i }) }).first();
  if (!(await select.count())) return;
  const light = select.locator('option', { hasText: /light|clair/i }).first();
  if (await light.evaluate((option) => option.selected)) return;
  await select.selectOption({ label: ((await light.textContent()) ?? '').trim() });
  await page.locator('#bt_saveProfils, .bt_saveProfils').first().click();
  await settle(page);
  await page.reload({ waitUntil: 'domcontentloaded' });
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
  // `clip` : un locator (gros plan), 'fullPage' (page entière), ou rien (fenêtre 1280×720).
  const buffer = clip === 'fullPage'
    ? await page.screenshot({ animations: 'disabled', fullPage: true })
    : clip ? await clip.screenshot({ animations: 'disabled' }) : await page.screenshot({ animations: 'disabled' });
  const file = path.join(outDir, shot.file);
  await writeFile(file, buffer);
  files.push({ id: shot.id, file: shot.file, sha256: sha256(buffer), bytes: buffer.length });
}

/** Captures 1 à 8 (Jeedom) selon le storyboard, puis la capture Home Assistant. */
async function runShots(browser, cfg, args, files) {
  const context = await newContext(browser, null, cfg);
  const page = await context.newPage();
  const byId = Object.fromEntries([...SHOTS, ...EXTRA_SHOTS].map((s) => [String(s.id), s]));
  try {
    await atStep('connexion Jeedom', () => loginJeedom(page, cfg));
    await atStep('1 page principale', async () => {
      await openPluginPage(page, cfg);
      // Relecture du 2026-10-31 : à 720 px de haut, la grille s'arrêtait au rez-de-chaussée (« Étage » absent).
      await saveShot(page, args.out, byId[1], cfg.secrets, files, 'fullPage');
    });
    await atStep('2 cartes de pièce', async () => {
      // Une carte seule ne mesure que 130×180 px (relecture du 2026-10-31) : le gros plan prend toute la grille,
      // groupée par étage, où « Bureau » (1 bloqué) et « Garage » (1 exclu) sont visibles.
      await saveShot(page, args.out, byId[2], cfg.secrets, files, page.locator('#j2ha_roomCards'));
      const garage = page.locator('#j2ha_roomCards .j2ha-room-card').filter({ hasText: DEMO.excludedRoom }).first();
      await saveShot(page, args.out, byId['2b'], cfg.secrets, files, garage);
    });
    await atStep('3 vue de travail', async () => {
      await openRoom(page, DEMO.searchRoom);
      await page.locator(`${WV} .j2ha-wv-widen`).click().catch(() => {});
      await page.locator(`${WV} .j2ha-wv-search`).fill(DEMO.searchRoom);
      await page.locator(`${WV} .j2ha-wv-room`).first().waitFor({ state: 'visible' });
      const rows = page.locator(`${WV} .j2ha-wv-eq`);
      // Un autre équipement que celui de la capture 4 (les deux images étaient identiques le 2026-10-31).
      await selectEquipment(page, rows.nth(DEMO.workViewEquipmentIndex));
      await saveShot(page, args.out, byId[3], cfg.secrets, files);
    });
    await atStep('4 détail d’un équipement', async () => {
      const row = page.locator(`${WV} .j2ha-wv-eq`).filter({ hasText: DEMO.publishedEquipment }).first();
      await selectEquipment(page, row);
      await page.locator(`${WV} .j2ha-eq-panel .j2ha-eq-controls`).waitFor({ state: 'visible' });
      // Gros plan sur le détail, pour se distinguer de la vue de travail (capture 3).
      await saveShot(page, args.out, byId[4], cfg.secrets, files, page.locator(`${WV} .j2ha-eq-panel`));
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
  const context = await newContext(browser, args.videoOut, cfg);
  const page = await context.newPage();
  const steps = videoSteps(args);
  // Thème clair vérifié à chaque écran filmé, pas seulement au premier ; la pause suit le storyboard vidéo.
  const hold = async (id) => {
    await assertLightTheme(page);
    await page.waitForTimeout(steps.find((s) => s.id === id).holdMs);
  };
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
      // « Relire Jeedom » ouvre une confirmation : sans clic sur « Relire », aucune relecture n'a lieu.
      const confirm = page.locator('.bootbox button[data-bb-handler="confirm"], .bootbox .btn.bootbox-accept').first();
      await confirm.waitFor({ state: 'visible' });
      const scan = page.waitForResponse((r) => r.url().includes('/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php')
        && (r.request().postData() ?? '').includes('scanTopology'), { timeout: RESCAN_TIMEOUT_MS });
      await confirm.click();
      await scan;
      await page.locator('#div_alert .alert').first().waitFor({ state: 'visible', timeout: RESCAN_TIMEOUT_MS });
      await page.locator('#bt_rescanTopology:not([disabled])').waitFor({ state: 'visible', timeout: RESCAN_TIMEOUT_MS });
      await settle(page);
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
    if (!args.skipHa) {
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
    }
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
  const cfg = validateConfig(parseEnvText(await readFile(args.envFile, 'utf8')), { requireHa: !args.skipHa });
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
  if (files.length || video) {
    // Aussi pour `--only video` : la vidéo régénérée ne laisse jamais un manifeste périmé ou absent.
    await mkdir(args.out, { recursive: true });
    const manifestPath = path.join(args.out, MANIFEST_FILE);
    const previous = await readFile(manifestPath, 'utf8').then(JSON.parse, () => null);
    const manifest = mergeManifest(previous, buildManifest({
      pluginVersion: info.pluginVersion, sourceCommit: gitValue(['rev-parse', '--short', 'HEAD']),
      date: new Date().toISOString().slice(0, 10), files, command: regenerateCommand(), video,
    }));
    assertManifestClean(manifest, cfg.secrets);
    await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  }
  process.stdout.write(`captures: ${files.length} fichier(s)${video ? `, vidéo ${video.seconds} s` : ''} — relecture CC-48 et concordance (Task 5) à faire\n`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).catch((error) => {
    process.stderr.write(`erreur : ${error.message}\n`);
    process.exit(1);
  });
}
