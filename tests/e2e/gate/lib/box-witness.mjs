// tests/e2e/gate/lib/box-witness.mjs
/**
 * Story 20.0 (B3a) — témoin SSH strictement en lecture seule (AC2/AC3).
 * Les commandes distantes sont closes et construites ici seulement. `run` est
 * injectable afin que les tests unitaires n'ouvrent jamais de connexion SSH.
 */

import { execFile } from 'node:child_process';

const SSH_TARGET = process.env.JEEDOM2HA_GATE_SSH || 'asahut@192.168.1.21';
const OVERRIDES = '/var/www/html/plugins/jeedom2ha/data/ha_overrides.json';
const DAEMON_LOG = '/var/www/html/log/jeedom2ha_daemon';
const PLUGIN_LOG = '/var/www/html/log/jeedom2ha';
const PID_PATTERN = '[j]eedom2ha/.*resources/daemon/main\\.py';
const TIME_RE = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;
const PID_RE = /^[0-9]+$/;

export const AC3_MARKERS = [
  '[OVERRIDES] Override HA sauvegardé via UI',
  '[OVERRIDES] Retour mode auto via UI',
  '[TOPOLOGY] Received sync request',
  '[ACTION] intention=',
  '[DISCOVERY]',
  '[MQTT] Testing connection',
];

function lines(value) {
  return String(value).trim().split(/\r?\n/).filter(Boolean);
}

function quote(value) {
  return `'${value.replaceAll("'", "'\\''")}'`;
}

export function validPid(value) {
  return PID_RE.test(String(value));
}

export function validBoxTime(value) {
  return TIME_RE.test(String(value));
}

export function parsePid(stdout) {
  const ids = lines(stdout);
  if (ids.length !== 1 || !validPid(ids[0])) throw new Error('pid-daemon-illisible');
  return ids[0];
}

export function parseNumber(stdout, label) {
  const value = String(stdout).trim();
  if (!/^\d+$/.test(value)) throw new Error(`${label}-illisible`);
  return Number(value);
}

export function parseOverrides(content) {
  if (content === null) return { present: false, json: null };
  let json;
  try {
    json = JSON.parse(content);
  } catch {
    throw new Error('overrides-json-illisible');
  }
  if (!json || typeof json !== 'object' || Array.isArray(json)) throw new Error('overrides-json-invalide');
  if (!Number.isInteger(json.schema_version) || ![1, 2].includes(json.schema_version)) {
    throw new Error('overrides-schema-invalide');
  }
  if (!json.overrides || typeof json.overrides !== 'object' || Array.isArray(json.overrides)) {
    throw new Error('overrides-commandes-invalides');
  }
  if (json.schema_version === 2 && (!json.equipment_overrides || typeof json.equipment_overrides !== 'object' || Array.isArray(json.equipment_overrides))) {
    throw new Error('overrides-equipements-invalides');
  }
  return { present: true, json };
}

export function assertNoOverrideOn(witness, eqIds) {
  const overrides = witness?.overrides;
  if (!overrides || !overrides.present || !overrides.json) return [];
  const wanted = new Set(eqIds.map(String));
  const command = overrides.json.overrides || {};
  const equipment = overrides.json.equipment_overrides || {}; // v1: absence = aucun override équipement.
  const found = [];
  for (const key of Object.keys(command)) {
    const [eqId, cmdId, ...rest] = key.split(':');
    if (rest.length === 0 && wanted.has(eqId) && /^\d+$/.test(eqId) && /^\d+$/.test(cmdId)) found.push(`commande:${key}`);
  }
  for (const eqId of Object.keys(equipment)) {
    if (wanted.has(eqId) && /^\d+$/.test(eqId)) found.push(`equipement:${eqId}`);
  }
  if (found.length) throw new Error(`override-declare: ${found.join(', ')}`);
  return [];
}

export function compareWitness(before, after) {
  const differences = [];
  if (!before?.readable || !after?.readable) differences.push('temoin-illisible');
  for (const side of [before, after]) {
    if (side?.daemon?.logLevel !== 'info' && side?.daemon?.logLevel !== 'debug') differences.push('niveau-journal-invalide');
  }
  for (const field of ['sha256', 'mtime', 'content']) {
    if (before?.overrides?.[field] !== after?.overrides?.[field]) differences.push(`overrides-${field}`);
  }
  if (before?.daemon?.pid !== after?.daemon?.pid) differences.push('daemon-pid');
  if (before?.daemon?.startedAt !== after?.daemon?.startedAt) differences.push('daemon-demarrage');
  for (const name of ['daemon', 'plugin']) {
    const oldLog = before?.logs?.[name];
    const newLog = after?.logs?.[name];
    if (!oldLog || !newLog) { differences.push(`journal-${name}-illisible`); continue; }
    if (newLog.size < oldLog.size) differences.push(`journal-${name}-troncature-taille`);
    if (newLog.firstTimestamp !== oldLog.firstTimestamp) differences.push(`journal-${name}-troncature-horodatage`);
  }
  return [...new Set(differences)];
}

export function remoteWindowCommand(path, marker, start, end) {
  if (!validBoxTime(start) || !validBoxTime(end)) throw new Error('bornes-horloge-invalides');
  return `awk '$0 ~ /^\\[[0-9-]+ [0-9:]+\\]/ { t=substr($0,2,19); if (t >= "${start}" && t <= "${end}") print }' ${quote(path)} | grep -cF ${quote(marker)} || true`;
}

export function runRemote(command) {
  return new Promise((resolve, reject) => {
    execFile('ssh', ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', SSH_TARGET, command], { encoding: 'utf8' }, (error, stdout, stderr) => {
      if (error) reject(new Error(`ssh-echec: ${error.message}`));
      else resolve(stdout);
    });
  });
}

async function optionalFile(run, command) {
  const output = await run(command);
  return output.trim() === '__ABSENT__' ? null : output.trim();
}

async function takeLog(run, path) {
  return {
    size: parseNumber(await run(`stat -c %s ${quote(path)}`), 'taille-journal'),
    firstTimestamp: (await run(`grep -m1 -o '^\\[[0-9-]* [0-9:]*\\]' ${quote(path)} || true`)).trim() || null,
  };
}

export async function takeWitness({ run = runRemote } = {}) {
  const witness = { readable: true, errors: [], overrides: {}, daemon: {}, logs: {} };
  try {
    const sha256 = await optionalFile(run, `if [ -e ${quote(OVERRIDES)} ]; then sha256sum ${quote(OVERRIDES)} | awk '{print $1}'; else printf '__ABSENT__\\n'; fi`);
    const mtime = await optionalFile(run, `if [ -e ${quote(OVERRIDES)} ]; then stat -c %y ${quote(OVERRIDES)}; else printf '__ABSENT__\\n'; fi`);
    const content = await optionalFile(run, `if [ -e ${quote(OVERRIDES)} ]; then cat ${quote(OVERRIDES)}; else printf '__ABSENT__\\n'; fi`);
    witness.overrides = { sha256, mtime, content, ...parseOverrides(content) };
    const pid = parsePid(await run(`pgrep -u www-data -f ${quote(PID_PATTERN)}`));
    witness.daemon.pid = pid;
    witness.daemon.startedAt = (await run(`ps -o lstart= -p ${pid}`)).trim();
    witness.daemon.logLevel = (await run(`ps -o args= -p ${pid} | grep -o -- '--loglevel[= ][^ ]*'`)).trim().replace(/^--loglevel[= ]/, '');
    witness.clock = (await run("date '+%Y-%m-%d %H:%M:%S'")).trim();
    if (!validBoxTime(witness.clock)) throw new Error('horloge-box-illisible');
    witness.logs.daemon = await takeLog(run, DAEMON_LOG);
    witness.logs.plugin = await takeLog(run, PLUGIN_LOG);
  } catch (error) {
    witness.readable = false;
    witness.errors.push(error.message);
  }
  return witness;
}

export async function countWindow(start, end, { run = runRemote } = {}) {
  if (!validBoxTime(start) || !validBoxTime(end) || start > end) throw new Error('bornes-horloge-invalides');
  const daemon = {};
  for (const marker of AC3_MARKERS) daemon[marker] = parseNumber(await run(remoteWindowCommand(DAEMON_LOG, marker, start, end)), 'compteur-daemon');
  return {
    daemon,
    daemonErrors: parseNumber(await run(remoteWindowCommand(DAEMON_LOG, 'ERROR', start, end)), 'compteur-erreurs-daemon'),
    pluginErrors: parseNumber(await run(remoteWindowCommand(PLUGIN_LOG, 'ERROR', start, end)), 'compteur-erreurs-plugin'),
  };
}
