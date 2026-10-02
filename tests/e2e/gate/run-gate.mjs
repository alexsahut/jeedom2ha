#!/usr/bin/env node
/** Story 20.0 B3c — lanceur du gate. Ne pas exécuter sans relecture ClaudeBox. */
import { execFile } from 'node:child_process';
import { mkdir, readFile, rm, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { loadPlaywright } from './lib/playwright.mjs';
import { installInterceptor } from './lib/interceptor.mjs';
import { createState } from './lib/simulate.mjs';
import { assertNoOverrideOn, compareWitness, countWindow, takeWitness } from './lib/box-witness.mjs';

const ORIGIN = 'https://domobox.famille-sahut.fr';
const PLUGIN = '/index.php?v=d&m=jeedom2ha&p=jeedom2ha';
const CREDENTIALS = process.env.JEEDOM2HA_GATE_CREDENTIALS || '/home/asahut/.config/jeedom2ha-gate/jeedom.env';
const CONFIG_KEYS = ['excludedPlugins', 'excludedObjects', 'confidencePolicy', 'mqttHost', 'mqttPort', 'mqttUser', 'mqttTls', 'mqttPassword'];

function child(file, args = []) { return new Promise((resolve, reject) => execFile(process.execPath, [file, ...args], { encoding: 'utf8' }, (e, out, err) => e ? reject(new Error(`processus-echec: ${e.message}`)) : resolve({ out, err }))); }
function args() { const a = process.argv.slice(2); const get = (n) => a[a.indexOf(n) + 1]; if (!get('--parcours') || !get('--report')) throw new Error('usage: --parcours <module> --report <dossier>'); return { parcours: get('--parcours'), report: get('--report') }; }
function parseEnv(raw) { const v = {}; for (const l of raw.split(/\r?\n/)) { const i = l.indexOf('='); if (i > 0 && !l.startsWith('#')) v[l.slice(0, i).trim()] = l.slice(i + 1).trim().replace(/^['"]|['"]$/g, ''); } if (!v.JEEDOM_USER || !v.JEEDOM_PASSWORD) throw new Error('identifiants-incomplets'); return { username: v.JEEDOM_USER, password: v.JEEDOM_PASSWORD, values: [v.JEEDOM_USER, v.JEEDOM_PASSWORD] }; }
async function credentials() { const s = await stat(CREDENTIALS); if ((s.mode & 0o777) !== 0o600) throw new Error('droits-identifiants-non-600'); return parseEnv(await readFile(CREDENTIALS, 'utf8')); }
function hash(value) { return createHash('sha256').update(JSON.stringify(value)).digest('hex'); }
function boxStart(clock) { const d = new Date(clock.replace(' ', 'T') + 'Z'); d.setUTCSeconds(d.getUTCSeconds() - 90); return d.toISOString().slice(0, 19).replace('T', ' '); }
function summary(journal) { return Object.fromEntries(journal.entries.reduce((m, e) => m.set(e.verdict, (m.get(e.verdict) || 0) + 1), new Map())); }
export function artifactsContain(values, texts) { return values.some((v) => v && texts.some((t) => t.includes(v))); }
async function sanitize(reportDir, secrets) { const files = ['gate-report.md', 'gate-report.json'].map((f) => path.join(reportDir, f)); const texts = await Promise.all(files.map((f) => readFile(f, 'utf8'))); if (artifactsContain(secrets, texts)) { await Promise.all(files.map((f) => rm(f, { force: true }))); throw new Error('ac4-fuite-rapport'); } }
async function probe(request) { const bridge = await request.post(`${ORIGIN}/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php`, { form: { action: 'getBridgeStatus' } }); const b = await bridge.json(); const config = {}; for (const key of CONFIG_KEYS) { const r = await request.post(`${ORIGIN}/core/ajax/config.ajax.php`, { form: { action: 'getKey', plugin: 'jeedom2ha', key } }); config[key] = (await r.json()).result; } return { bridge: { daemon: b.result?.payload?.daemon, derniere_synchro_terminee: b.result?.payload?.derniere_synchro_terminee, derniere_operation_resultat: b.result?.payload?.derniere_operation_resultat }, configHash: hash(config) }; }
function expectedUrl(page) { const u = new URL(page.url()); return u.origin === ORIGIN && u.pathname === '/index.php' && u.searchParams.get('v') === 'd' && u.searchParams.get('m') === 'jeedom2ha' && u.searchParams.get('p') === 'jeedom2ha'; }
function redirects(response) { let request = response?.request()?.redirectedFrom(); while (request) { if (new URL(request.url()).origin !== ORIGIN) return false; request = request.redirectedFrom(); } return true; }
async function report(dir, data, secrets) { await mkdir(dir, { recursive: true }); const activity = data.differences.length || data.window.daemonErrors || data.window.pluginErrors || Object.values(data.window.daemon).some(Boolean); const checks = { ac3_1_interception: !data.journal.failed, ac3_2_box: !activity, ac3_3_console: data.consoleErrors.length === 0, ac3_4_logs: !activity, ac3_5_report: true }; const payload = { verdict: Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL', checks, differences: data.differences, window: data.window, interceptor: { verdicts: summary(data.journal), failures: data.journal.failures, simulated: data.journal.entries.filter((e) => e.verdict === 'simulee') }, note: 'badge « pas encore appliqué » non prouvé par le gate' }; const md = `# Gate report\n\nVerdict: **${payload.verdict}**\n\n${activity ? 'activité sur la box pendant le parcours : parcours non concluant\n\n' : ''}${Object.entries(checks).map(([k,v]) => `- ${k}: ${v ? 'PASS' : 'FAIL'}`).join('\n')}\n\n${payload.note}\n`; await writeFile(path.join(dir, 'gate-report.json'), JSON.stringify(payload, null, 2)); await writeFile(path.join(dir, 'gate-report.md'), md); await sanitize(dir, secrets); return payload; }
async function main() {
  const { parcours: modulePath, report: reportDir } = args();
  await child(path.join(path.dirname(new URL(import.meta.url).pathname), 'interceptor-selftest.mjs')); // AC1 avant tout contact box
  const creds = await credentials();
  const parcours = await import(pathToFileURL(path.resolve(modulePath)).href);
  if (!parcours.name || !parcours.declaredEquipments || !Array.isArray(parcours.declaredBascules) || typeof parcours.run !== 'function') throw new Error('parcours-invalide');
  const before = await takeWitness(); if (!before.readable || !['info','debug'].includes(before.daemon.logLevel)) throw new Error('temoin-avant-invalide'); assertNoOverrideOn(before, Object.keys(parcours.declaredEquipments));
  const { chromium } = loadPlaywright(); let browser; const journal = { entries: [], failed: false, failures: [] }; const consoleErrors = [];
  try { browser = await chromium.launch({ headless: true }); const context = await browser.newContext({ serviceWorkers: 'block' }); const simState = createState(); const ctx = { origin: ORIGIN, loginAttempts: 0, declaredEquipments: parcours.declaredEquipments, lastPreviewType: simState.lastPreviewType }; await installInterceptor(context, { ctx, simState, journal, declaredBascules: parcours.declaredBascules }); ctx.loginAttempts = 1; const login = await context.request.post(`${ORIGIN}/core/ajax/user.ajax.php`, { form: { action: 'login', username: creds.username, password: creds.password } }); if (!login.ok()) throw new Error('connexion-echouee'); const probeBefore = await probe(context.request); const page = await context.newPage(); page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); }); page.on('pageerror', (e) => consoleErrors.push(e.message)); const navigation = await page.goto(`${ORIGIN}${PLUGIN}`, { waitUntil: 'load' }); if (!expectedUrl(page) || !redirects(navigation)) throw new Error('navigation-finale-invalide'); await parcours.run(page, { journal, simState, ctx }); for (const p of context.pages()) await p.close(); const last = journal.entries.at(-1)?.timestamp; const wait = last ? Math.max(0, 90_000 - (Date.now() - Date.parse(last))) : 90_000; await new Promise((r) => setTimeout(r, wait)); const probeAfter = await probe(context.request); const after = await takeWitness(); const window = await countWindow(before.clock, after.clock); const differences = [...compareWitness(before, after), ...(hash(probeBefore) === hash(probeAfter) ? [] : ['sondes-differentes'])]; const result = await report(reportDir, { differences, window, journal, consoleErrors }, [...creds.values]); if (result.verdict !== 'PASS') process.exitCode = 1; await context.close(); } finally { if (browser) await browser.close(); }
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((e) => { console.error(e.message); process.exitCode = 1; });
}
