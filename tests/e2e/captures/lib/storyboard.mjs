// tests/e2e/captures/lib/storyboard.mjs
/** Story 23.2 — storyboard figé (ClaudeBox + Alexandre, 2026-10-21) sous forme de données.
 *
 * Source de vérité : `_bmad-output/implementation-artifacts/23-2-captures-et-video-de-promotion-rejouables.md`.
 * Les sélecteurs des parcours (run-captures.mjs) viennent du DOM du plugin et du gate 20-0 ;
 * ils sont NON DÉMONTRÉS sur la VM de démo tant que la passe terrain n'a pas eu lieu.
 */

export const VIEWPORT = Object.freeze({ width: 1280, height: 720 });
export const LOCALE = 'fr-FR';
export const TIMEZONE = 'Europe/Paris';
export const COLOR_SCHEME = 'light';
export const VIDEO_MAX_SECONDS = 120;
export const VIDEO_FILE = 'jeedom2ha-presentation.webm';
export const MANIFEST_FILE = 'captures-manifest.json';

/** Pièce, équipements et recherche utilisés par le parcours (démo synthétique 23.1/23.2 uniquement). */
export const DEMO = Object.freeze({
  searchRoom: 'Salon',
  blockedRoom: 'Bureau',
  blockedEquipment: 'Équipement Libre Bureau',
  excludedRoom: 'Garage',
  publishedEquipment: 'Lumière Salon',
  // « équipement 4 » du storyboard : 4e équipement de l'arbre filtré sur « Salon » (Climat Salon).
  // Lecture à valider par ClaudeBox lors de la Task 5.
  // Relecture du 2026-10-31 : « Climat Salon » (4e) n'a qu'une commande publiée ; « Lampe Variable Salon » (2e) en montre
  // davantage (état, on/off, luminosité).
  commandsEquipmentIndex: 1,
  // Capture 3 : « Volet Salon » (3e), distinct de la capture 4 (« Lumière Salon ») et de la capture 5.
  workViewEquipmentIndex: 2,
  haLight: 'Lumière Salon',
  // Filtre de la liste des appareils HA (capture 9) : fabricant « Jeedom (virtual) » de la démo.
  haDeviceFilter: 'Jeedom',
});

/** Lignes 1 à 8 du storyboard, plus la capture Home Assistant. `marker` = marqueur de la doc à remplacer. */
export const SHOTS = Object.freeze([
  { id: 1, file: 'page-principale.png', app: 'jeedom', doc: 'index.md', marker: 'page principale du plugin' },
  { id: 2, file: 'cartes-de-piece.png', app: 'jeedom', doc: 'index.md', marker: 'cartes de pièce' },
  { id: 3, file: 'vue-de-travail.png', app: 'jeedom', doc: 'index.md', marker: 'vue de travail' },
  { id: 4, file: 'detail-equipement.png', app: 'jeedom', doc: 'index.md', marker: "détail d'un équipement" },
  { id: 5, file: 'tableau-des-commandes.png', app: 'jeedom', doc: 'index.md', marker: 'tableau des commandes' },
  { id: 6, file: 'compteurs-detail-piece.png', app: 'jeedom', doc: 'compteurs.md', marker: 'compteurs du détail de pièce' },
  { id: 7, file: 'compteurs-equipement-deplie.png', app: 'jeedom', doc: 'compteurs.md',
    marker: "ligne de compteurs d'un équipement déplié" },
  { id: 8, file: 'configuration.png', app: 'jeedom', doc: 'index.md', marker: 'page de configuration' },
  { id: 9, file: 'home-assistant-appareils.png', app: 'homeassistant', doc: null, marker: null },
]);

/** Capture complémentaire de la ligne 2 (Garage, 1 exclu) ; ne remplace aucun marqueur. */
export const EXTRA_SHOTS = Object.freeze([
  { id: '2b', file: 'cartes-de-piece-garage.png', app: 'jeedom', doc: null, marker: null },
]);

/** Storyboard vidéo : durées de pause (ms) par étape, en plus des temps de chargement réels. `caption` = sous-titre
 * incrusté pendant la pause (demande d'Alexandre du 2026-11-01 : sans texte, « on ne comprend rien »).
 * Ramenées de 55 à 43,5 s le 2026-10-31 : le premier enregistrement complet (VM 122) atteignait 120 s, la limite. */
export const HA_VIDEO_STEP_IDS = Object.freeze(['ha-appareils', 'ha-pilotage', 'retour']);

export const VIDEO_STEPS = Object.freeze([
  { id: 'plugins', label: 'Page Plugins : le plugin installé', holdMs: 3500,
    caption: 'Le plugin jeedom2ha s’installe comme n’importe quel plugin Jeedom.' },
  { id: 'dependances', label: 'Configuration : dépendances OK et démon OK', holdMs: 5000,
    caption: 'Dépendances installées, démon actif : le pont MQTT vers Home Assistant est prêt.' },
  { id: 'relire', label: 'Page principale puis « Relire Jeedom »', holdMs: 6000,
    caption: '« Relire Jeedom » : le plugin lit vos pièces, équipements et commandes, et publie ce qui peut l’être.' },
  { id: 'piece', label: 'Ouverture d’une pièce', holdMs: 5000,
    caption: 'Chaque pièce montre ce qui est publié dans Home Assistant, et pourquoi le reste ne l’est pas.' },
  { id: 'equipement', label: 'Ouverture d’un équipement', holdMs: 5000,
    caption: 'Pour chaque équipement : ses commandes Jeedom et leur équivalent dans Home Assistant.' },
  { id: 'ha-appareils', label: 'Home Assistant : mêmes équipements, mêmes pièces', holdMs: 7000,
    caption: 'Dans Home Assistant : les mêmes équipements, rangés dans les mêmes pièces, sans rien ressaisir.' },
  { id: 'ha-pilotage', label: 'Pilotage d’une lumière depuis Home Assistant', holdMs: 6000,
    caption: 'On pilote une lumière depuis Home Assistant…' },
  { id: 'retour', label: 'Retour d’état dans Jeedom', holdMs: 6000,
    caption: '… et Jeedom suit : la commande passe par Jeedom, l’état revient dans le plugin.' },
]);

/** Borne basse sur la durée prévue (pauses seules) : doit rester très en dessous de VIDEO_MAX_SECONDS. */
/** Étapes vidéo retenues ; `--skip-ha` retire Home Assistant et le retour d'état qui en dépend. */
export function videoSteps({ skipHa = false } = {}) {
  return skipHa ? VIDEO_STEPS.filter((step) => !HA_VIDEO_STEP_IDS.includes(step.id)) : VIDEO_STEPS;
}

export function plannedHoldSeconds(steps = VIDEO_STEPS) {
  return steps.reduce((total, step) => total + step.holdMs, 0) / 1000;
}
