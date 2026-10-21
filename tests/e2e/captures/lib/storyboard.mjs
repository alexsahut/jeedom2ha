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
  commandsEquipmentIndex: 3,
  haLight: 'Lumière Salon',
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

/** Storyboard vidéo : durées de pause (ms) par étape, en plus des temps de chargement réels. */
export const VIDEO_STEPS = Object.freeze([
  { id: 'plugins', label: 'Page Plugins : le plugin installé', holdMs: 4000 },
  { id: 'dependances', label: 'Configuration : dépendances OK et démon OK', holdMs: 6000 },
  { id: 'relire', label: 'Page principale puis « Relire Jeedom »', holdMs: 8000 },
  { id: 'piece', label: 'Ouverture d’une pièce', holdMs: 6000 },
  { id: 'equipement', label: 'Ouverture d’un équipement', holdMs: 6000 },
  { id: 'ha-appareils', label: 'Home Assistant : mêmes équipements, mêmes pièces', holdMs: 9000 },
  { id: 'ha-pilotage', label: 'Pilotage d’une lumière depuis Home Assistant', holdMs: 8000 },
  { id: 'retour', label: 'Retour d’état dans Jeedom', holdMs: 8000 },
]);

/** Borne basse sur la durée prévue (pauses seules) : doit rester très en dessous de VIDEO_MAX_SECONDS. */
export function plannedHoldSeconds(steps = VIDEO_STEPS) {
  return steps.reduce((total, step) => total + step.holdMs, 0) / 1000;
}
