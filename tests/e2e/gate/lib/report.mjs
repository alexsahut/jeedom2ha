// Fonctions pures du rapport du gate Story 20.0 : aucune E/S ni dépendance Playwright.

import { createHash } from 'node:crypto';
import { AC3_MARKERS } from './box-witness.mjs';

export const CONFIG_KEYS = [
  'excludedPlugins', 'excludedObjects', 'confidencePolicy', 'mqttHost',
  'mqttPort', 'mqttUser', 'mqttTls', 'mqttPassword',
];

/** Lit les deux identifiants requis sans jamais les afficher. */
export function parseCredentials(raw) {
  const values = {};
  for (const line of String(raw).split(/\r?\n/)) {
    const index = line.indexOf('=');
    if (index > 0 && !line.startsWith('#')) {
      values[line.slice(0, index).trim()] = line.slice(index + 1).trim().replace(/^['"]|['"]$/g, '');
    }
  }
  if (!values.JEEDOM_USER || !values.JEEDOM_PASSWORD) throw new Error('identifiants-incomplets');
  return {
    username: values.JEEDOM_USER,
    password: values.JEEDOM_PASSWORD,
    values: [values.JEEDOM_USER, values.JEEDOM_PASSWORD],
  };
}

/** Extrait le témoin du bridge et rejette toute réponse AJAX incomplète. */
export function extractBridgeStatus(response) {
  const result = response?.result;
  if (response?.state !== 'ok' || result?.daemon !== true) {
    throw new Error('sonde-bridge-illisible');
  }
  if (!Object.hasOwn(result, 'derniere_synchro_terminee')) {
    throw new Error('sonde-bridge-illisible');
  }
  if (!Object.hasOwn(result, 'derniere_operation_resultat')) {
    throw new Error('sonde-bridge-illisible');
  }
  const operation = result.derniere_operation_resultat;
  if (!operation || typeof operation !== 'object' || Array.isArray(operation)) {
    throw new Error('sonde-bridge-illisible');
  }
  if (typeof operation.timestamp !== 'string' || !operation.timestamp) {
    throw new Error('sonde-bridge-illisible');
  }
  return {
    daemon: result.daemon,
    derniere_synchro_terminee: result.derniere_synchro_terminee,
    derniere_operation_timestamp: operation.timestamp,
  };
}

/** Extrait les huit valeurs de configuration, seulement si chaque réponse est saine. */
export function extractConfigValues(responses) {
  const values = {};
  for (const key of CONFIG_KEYS) {
    const response = responses?.[key];
    if (response?.state !== 'ok' || !Object.hasOwn(response, 'result')) {
      throw new Error(`sonde-config-illisible:${key}`);
    }
    values[key] = response.result;
  }
  return values;
}

/** Produit une empreinte stable sans conserver ni révéler les valeurs de configuration. */
export function hashValue(value) {
  return createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

/** Compare les deux sondes HTTP et donne un nom précis à chaque différence. */
export function compareProbes(before, after) {
  const differences = [];
  if (JSON.stringify(before?.bridge) !== JSON.stringify(after?.bridge)) differences.push('bridge-different');
  if (before?.configHash !== after?.configHash) differences.push('empreinte-config-differente');
  return differences;
}

/** Résume les verdicts de l'intercepteur sans ajouter de données sensibles. */
export function summarizeJournal(journal) {
  return Object.fromEntries((journal?.entries ?? []).reduce((counts, entry) => {
    counts.set(entry.verdict, (counts.get(entry.verdict) ?? 0) + 1);
    return counts;
  }, new Map()));
}

/** Vérifie les cinq contrôles AC3 et la condition d'activité box. */
export function calculateChecks({ journal, witnessDifferences, probeDifferences, window, consoleErrors, failure }) {
  // Une fenêtre illisible (SSH en échec, journal tronqué) laisse window à {} ou
  // à un objet partiel : les huit compteurs (les marqueurs AC3_MARKERS plus
  // daemonErrors et pluginErrors) doivent tous être présents et numériques,
  // sans quoi l'absence ne doit jamais se lire comme « aucune activité ».
  const windowReadable = typeof window?.daemon === 'object' && window.daemon !== null
    && AC3_MARKERS.every((marker) => typeof window.daemon[marker] === 'number')
    && typeof window?.daemonErrors === 'number' && typeof window?.pluginErrors === 'number';
  const markerCount = windowReadable && Object.values(window.daemon).some(Boolean);
  const logActivity = markerCount || Boolean(window?.daemonErrors) || Boolean(window?.pluginErrors);
  const boxChanged = witnessDifferences.length > 0 || probeDifferences.length > 0;
  const checks = {
    ac3_1_interception: !journal?.failed,
    ac3_2_box: !boxChanged,
    ac3_3_console: consoleErrors.length === 0,
    ac3_4_logs: windowReadable && !logActivity,
    ac3_5_report: true,
  };
  // Une fenêtre illisible ne prouve aucun calme : elle doit aussi déclencher la
  // ligne d'activité, pas seulement faire échouer ac3_4_logs en silence.
  return { checks, activity: boxChanged || logActivity || !windowReadable };
}

/** Remplace une query string entière afin qu'une URL ne divulgue jamais une apikey. */
export function sanitizeUrl(value) {
  return String(value).replace(/\?[^\s]*/g, '?…');
}

/** Assainit chaque message console, y compris les URLs intégrées dans une erreur. */
export function sanitizeConsoleErrors(errors) {
  return (errors ?? []).map((error) => sanitizeUrl(error));
}

/** Réduit une erreur externe à une seule ligne sûre pour le rapport. */
export function sanitizeReason(error) {
  const firstLine = String(error?.message ?? error ?? '').split(/\r?\n/, 1)[0];
  return sanitizeUrl(firstLine).slice(0, 300);
}

/** Valide une observation déclarée par un parcours avant son ajout au rapport. */
export function normalizeParcoursRecord(key, value) {
  if (typeof key !== 'string' || !/^[a-z][a-z0-9_-]{0,79}$/.test(key)) {
    throw new Error('parcours-record-cle-invalide');
  }
  if (typeof value === 'number' && Number.isFinite(value)) return [key, value];
  if (typeof value === 'boolean') return [key, value];
  if (typeof value === 'string' && value.length <= 80 && !/[?=]/.test(value)) {
    return [key, value];
  }
  throw new Error('parcours-record-valeur-invalide');
}

/** Étiquette les seules valeurs qui ne doivent jamais apparaître dans les rapports AC4. */
export function ac4Values(credentials, configValues) {
  const candidates = [
    { categorie: 'identifiant', valeur: credentials?.[0] },
    { categorie: 'mot-de-passe', valeur: credentials?.[1] },
    { categorie: 'config-mqttPassword', valeur: configValues?.mqttPassword },
  ];
  return candidates.filter(({ valeur }) => typeof valeur === 'string' && valeur.length > 0);
}

/** Retourne les catégories de valeurs AC4 présentes, sans jamais retourner les valeurs. */
export function artifactsContain(values, texts) {
  return [...new Set((values ?? [])
    .filter(({ valeur }) => {
      if (!valeur) return false;
      const forms = [valeur, JSON.stringify(valeur).slice(1, -1), encodeURIComponent(valeur)];
      return (texts ?? []).some((text) => forms.some((form) => String(text).includes(form)));
    })
    .map(({ categorie }) => categorie))];
}
