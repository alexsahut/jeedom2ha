// tests/e2e/captures/lib/config.mjs
/** Story 23.2 — lecture du `.env` des comptes `j2ha-captures` (D3), hors dépôt, sans jamais journaliser une valeur.
 *
 * Noms de clés : ceux de l'outillage du gate 20-0 pour Jeedom (JEEDOM_USER, JEEDOM_PASSWORD) ; les autres sont
 * proposés ici et À CONFIRMER avec clawbox (qui a créé le `.env`) : JEEDOM_URL, HA_URL, HA_USER, HA_PASSWORD.
 * `JEEDOM_DEMO_TARGET=demo` est exigé comme pour `populate_demo.py` (garde-fou : jamais la box de production).
 */

import path from 'node:path';

export const REQUIRED_KEYS = Object.freeze([
  'JEEDOM_URL', 'JEEDOM_USER', 'JEEDOM_PASSWORD', 'HA_URL', 'HA_USER', 'HA_PASSWORD', 'JEEDOM_DEMO_TARGET',
]);

export function parseEnvText(raw) {
  const values = {};
  for (const line of String(raw).split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const index = trimmed.indexOf('=');
    if (index <= 0) continue;
    const key = trimmed.slice(0, index).replace(/^export\s+/, '').trim();
    values[key] = trimmed.slice(index + 1).trim().replace(/^(['"])(.*)\1$/, '$2');
  }
  return values;
}

/** Valide la configuration ; les erreurs ne citent que des NOMS de clés, jamais de valeurs. */
export function validateConfig(values) {
  const missing = REQUIRED_KEYS.filter((key) => !values[key]);
  if (missing.length) throw new Error(`cles-manquantes: ${missing.join(', ')}`);
  if (values.JEEDOM_DEMO_TARGET !== 'demo') throw new Error('cible-non-confirmee-demo');
  for (const key of ['JEEDOM_URL', 'HA_URL']) {
    let url;
    try { url = new URL(values[key]); } catch { throw new Error(`url-invalide: ${key}`); }
    if (!['http:', 'https:'].includes(url.protocol)) throw new Error(`url-invalide: ${key}`);
  }
  const origins = {
    jeedom: new URL(values.JEEDOM_URL).origin,
    homeAssistant: new URL(values.HA_URL).origin,
  };
  // Valeurs à ne jamais laisser apparaître dans une capture, un journal ou le manifeste.
  const secrets = [
    values.JEEDOM_USER, values.JEEDOM_PASSWORD, values.HA_USER, values.HA_PASSWORD,
    new URL(values.JEEDOM_URL).host, new URL(values.HA_URL).host,
  ].filter((value, index, all) => value && all.indexOf(value) === index);
  return {
    jeedom: { origin: origins.jeedom, user: values.JEEDOM_USER, password: values.JEEDOM_PASSWORD },
    homeAssistant: { origin: origins.homeAssistant, user: values.HA_USER, password: values.HA_PASSWORD },
    secrets,
  };
}

/** Refuse un `.env` situé dans le dépôt (CC-48), comme `populate_demo.py`. */
export function assertEnvOutsideRepo(envFile, repoRoot) {
  const relative = path.relative(path.resolve(repoRoot), path.resolve(envFile));
  if (relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative))) {
    throw new Error('env-dans-le-depot');
  }
}

/** Remplace toute valeur secrète dans un texte destiné à un journal. */
export function redact(text, secrets) {
  let out = String(text);
  for (const secret of secrets) if (secret) out = out.split(secret).join('«masqué»');
  return out;
}
