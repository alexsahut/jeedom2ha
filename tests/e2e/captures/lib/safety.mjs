// tests/e2e/captures/lib/safety.mjs
/** Story 23.2 — contrôles CC-48, thème clair (D1) et manifeste. Fonctions pures, testées sans navigateur. */

import { createHash } from 'node:crypto';
import { VIEWPORT, LOCALE, COLOR_SCHEME } from './storyboard.mjs';

const IPV4 = /\b(?:\d{1,3}\.){3}\d{1,3}\b/;
const LOCAL_HOST = /\b[a-z0-9-]+\.(?:local|lan|home|internal)\b/i;
const URL_WITH_HOST = /\bhttps?:\/\/[^\s"'<>]+/i;
const LONG_TOKEN = /\b[0-9a-zA-Z]{32,}\b/;

/** Retourne la liste (sans valeur) des raisons pour lesquelles un texte visible ne doit pas être publié. */
export function findLeaks(text, secrets = []) {
  const findings = [];
  const source = String(text);
  if (IPV4.test(source)) findings.push('adresse-ip');
  if (LOCAL_HOST.test(source)) findings.push('nom-hote-local');
  if (URL_WITH_HOST.test(source)) findings.push('url');
  if (LONG_TOKEN.test(source)) findings.push('jeton-long');
  if (secrets.some((secret) => secret && source.includes(secret))) findings.push('secret-configure');
  return findings;
}

/** Luminance relative (0..1) d'une couleur `rgb()`/`rgba()` de `getComputedStyle`. `null` si illisible ou transparente. */
export function luminance(color) {
  const match = /^rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)(?:[,\s/]+([\d.]+))?\s*\)$/.exec(String(color).trim());
  if (!match) return null;
  if (match[4] !== undefined && Number(match[4]) === 0) return null;
  const [r, g, b] = [match[1], match[2], match[3]].map((v) => {
    const c = Number(v) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Thème clair prouvé par le fond effectif de la page (D1) ; un fond illisible est refusé (échec fermé). */
export function isLightBackground(color, threshold = 0.6) {
  const value = luminance(color);
  return value !== null && value >= threshold;
}

export function sha256(buffer) {
  return createHash('sha256').update(buffer).digest('hex');
}

/** Manifeste versionné : version du plugin, date, viewport, fichiers (empreintes). Aucune URL, aucun identifiant. */
export function buildManifest({ pluginVersion, sourceCommit, date, files, command, video }) {
  if (!pluginVersion) throw new Error('version-plugin-manquante');
  const manifest = {
    schema: 1,
    plugin_version: pluginVersion,
    source_commit: sourceCommit || null,
    generated_on: date,
    viewport: { width: VIEWPORT.width, height: VIEWPORT.height },
    locale: LOCALE,
    theme: COLOR_SCHEME,
    data: 'démo synthétique 23.1/23.2 (CC-48)',
    regenerate: command,
    files: files.map(({ file, id, sha256: digest, bytes }) => ({ id, file, sha256: digest, bytes })),
  };
  if (video) manifest.video = video;
  return manifest;
}

/**
 * Fusionne le manifeste précédent : une régénération partielle (`--only shots|video`) ne laisse jamais une section
 * périmée sans date ni version. Chaque section porte ses propres métadonnées ; les fichiers repris restent ceux
 * de l'exécution précédente, avec leur manifeste d'origine pour la version et la date.
 */
export function mergeManifest(previous, next) {
  const merged = { ...next };
  const old = previous && typeof previous === 'object' ? previous : {};
  const origin = { plugin_version: old.plugin_version, source_commit: old.source_commit, generated_on: old.generated_on };
  if (!next.files.length && Array.isArray(old.files) && old.files.length) {
    merged.files = old.files;
    merged.files_generated = origin;
  }
  if (!next.video && old.video) {
    merged.video = { ...old.video, generated: old.video.generated || origin };
  } else if (next.video) {
    merged.video = { ...next.video, generated: { plugin_version: next.plugin_version, source_commit: next.source_commit, generated_on: next.generated_on } };
  }
  return merged;
}

/** Garde finale : le manifeste sérialisé ne doit contenir ni fuite ni secret. */
export function assertManifestClean(manifest, secrets) {
  const findings = findLeaks(JSON.stringify(manifest), secrets).filter((f) => f !== 'jeton-long');
  if (findings.length) throw new Error(`manifeste-non-propre: ${findings.join(', ')}`);
}
