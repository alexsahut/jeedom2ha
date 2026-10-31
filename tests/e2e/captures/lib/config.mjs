// tests/e2e/captures/lib/config.mjs
/** Story 23.2 — lecture du `.env` des comptes `j2ha-captures` (D3), hors dépôt, sans jamais journaliser une valeur.
 *
 * Noms de clés canoniques : JEEDOM_URL, JEEDOM_USER, JEEDOM_PASSWORD, HA_URL, HA_USER, HA_PASSWORD.
 * Le `.env` créé par clawbox le 2026-10-21 emploie d'autres noms (JEEDOM_BASE_URL, JEEDOM_USERNAME,
 * HOME_ASSISTANT_BASE_URL, HOME_ASSISTANT_USERNAME, HOME_ASSISTANT_PASSWORD) : ils sont acceptés comme alias
 * (`KEY_ALIASES`) ; une clé canonique présente l'emporte sur son alias.
 * `JEEDOM_DEMO_TARGET=demo` est exigé comme pour `populate_demo.py` (garde-fou : jamais la box de production) ;
 * il n'est pas secret et s'ajoute au `.env` par une ligne.
 */

import path from 'node:path';

export const JEEDOM_KEYS = Object.freeze(['JEEDOM_URL', 'JEEDOM_USER', 'JEEDOM_PASSWORD', 'JEEDOM_DEMO_TARGET']);
export const HA_KEYS = Object.freeze(['HA_URL', 'HA_USER', 'HA_PASSWORD']);
export const REQUIRED_KEYS = Object.freeze([...JEEDOM_KEYS, ...HA_KEYS]);

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

/** Alias acceptés (noms du `.env` créé par clawbox) → nom canonique. */
export const KEY_ALIASES = Object.freeze({
  JEEDOM_BASE_URL: 'JEEDOM_URL',
  JEEDOM_USERNAME: 'JEEDOM_USER',
  HOME_ASSISTANT_BASE_URL: 'HA_URL',
  HOME_ASSISTANT_USERNAME: 'HA_USER',
  HOME_ASSISTANT_PASSWORD: 'HA_PASSWORD',
});

/** Ramène les alias à leur nom canonique ; une clé canonique présente l'emporte, même vide (la validation la rejette alors). */
export function normalizeKeys(values) {
  const out = { ...values };
  for (const [alias, canonical] of Object.entries(KEY_ALIASES)) {
    if (!Object.prototype.hasOwnProperty.call(out, canonical) && alias in out) out[canonical] = out[alias];
    delete out[alias];
  }
  return out;
}

/** Valide la configuration ; les erreurs ne citent que des NOMS de clés, jamais de valeurs. */
export function validateConfig(rawValues, { requireHa = true } = {}) {
  const values = normalizeKeys(rawValues);
  const missing = (requireHa ? REQUIRED_KEYS : JEEDOM_KEYS).filter((key) => !values[key]);
  if (missing.length) throw new Error(`cles-manquantes: ${missing.join(', ')}`);
  if (values.JEEDOM_DEMO_TARGET !== 'demo') throw new Error('cible-non-confirmee-demo');
  for (const key of requireHa ? ['JEEDOM_URL', 'HA_URL'] : ['JEEDOM_URL']) {
    let url;
    try { url = new URL(values[key]); } catch { throw new Error(`url-invalide: ${key}`); }
    if (!['http:', 'https:'].includes(url.protocol)) throw new Error(`url-invalide: ${key}`);
  }
  const origins = {
    jeedom: new URL(values.JEEDOM_URL).origin,
    homeAssistant: requireHa ? new URL(values.HA_URL).origin : null,
  };
  // Valeurs à ne jamais laisser apparaître dans une capture, un journal ou le manifeste.
  const secrets = [
    values.JEEDOM_USER, values.JEEDOM_PASSWORD, values.HA_USER, values.HA_PASSWORD,
    new URL(values.JEEDOM_URL).host, requireHa ? new URL(values.HA_URL).host : null,
  ].filter((value, index, all) => value && all.indexOf(value) === index);
  return {
    jeedom: { origin: origins.jeedom, user: values.JEEDOM_USER, password: values.JEEDOM_PASSWORD },
    homeAssistant: requireHa ? { origin: origins.homeAssistant, user: values.HA_USER, password: values.HA_PASSWORD } : null,
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
