'use strict';

/* Aide de test (audit UX du 2026-10-19) : règles du CSS du cœur Jeedom qui touchent la surface du plugin, plus une scène
 * fictive aux noms longs.
 *
 * PROVENANCE : Jeedom core 4.6.1, desktop/css/desktop.main.css et deprecated.main.css (thème Core 2021), relevés sur la box.
 * Sélecteurs et déclarations RECOPIÉS TELS QU'ON LES CONNAÎT (seuls les commentaires sont retirés). Ce n'est PAS une copie
 * intégrale du fichier du cœur : seulement les règles qui ont mordu la surface du plugin sur la box.
 * LICENCE : le cœur Jeedom est un logiciel libre sous licence GNU GPL (https://github.com/jeedom/core). Ce fichier sert
 * uniquement aux tests ; il n'est PAS dans le paquet Market (`exclude tests/` du manifeste, contrôlé par
 * tests/test_market_package.py).
 *
 * Depuis la PR test(ui) « charger par défaut les règles du cœur », workview_browser.withRealView injecte CORE_CSS AVANT le
 * CSS du plugin dès que l'appelant ne fournit pas son propre CSS (désactivable par `coreCss: false`). Sans ces règles, le
 * harnais ne voyait pas les défauts propres à la box : icône de carte à 38 px, carte de 130 × 130 px en overflow:hidden
 * (jauge rognée), `.btn:not(.cmdName)` qui donne un fond de bouton à tout `.btn-link`, bouton `confirm` de bootbox forcé en
 * vert, bordures supprimées dans les conteneurs de cartes, cases à cocher en position absolue.
 * Données fictives (CC-48) : aucun nom de la maison réelle. */

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const ROOT = path.join(__dirname, '..', '..', '..');

/** Variables du thème sombre de la box (relevées sur Jeedom 4.6.1) dont dépendent les règles ci-dessous. */
const CORE_VARS = `
:root { --border-radius: 4px; --btn-default-color: #3a3a3a; --linkHoverLight-color: #e0e0e0; --link-color: #94ca02; --txt-color: #e0e0e0; --bg-color: 25, 25, 25; --form-bg-color: #2c2c2c; --al-success-color: rgb(50, 130, 60); --al-warning-color: rgb(195, 125, 40); --al-danger-color: rgb(185, 58, 62); --sc-lightTxt-color: rgb(230, 230, 230); }
`;

/** Extrait de desktop.main.css et deprecated.main.css (cœur Jeedom 4.6.1) — sélecteurs et déclarations recopiés tels quels. */
const CORE_RULES = `
.btn:not(.cmdName), .btn:not(.cmdName):active, .btn:not(.cmdName).active { color: var(--linkHoverLight-color) !important; background-color: var(--btn-default-color) !important; }
.btn { font-size: 12px; border: none; padding: 7px 8px; height: 32px; line-height: 18px; }
.btn, input, select, textarea, .label, .label-sm, .input-group-addon, .market, button, pre { border-radius: var(--border-radius) !important; }
div[class*="ListContainer"], div.eqLogicThumbnailContainer { display: flex !important; flex-wrap: wrap; flex-direction: row; }
div[class*="ListContainer"] > div.cursor { width : 130px !important; font-size: 14px !important; position: relative; }
div[class*="ListContainer"]:not(.batteryListContainer):not(.alertListContainer) div.cursor, .eqLogicDisplayCard div.cursor { margin-bottom: 5px !important; padding: 5px !important; }
.eqLogicDisplayCard, .eqLogicThumbnailContainer div, .interactDisplayCard, div[class*="ListContainer"]:not(.batteryListContainer):not(.alertListContainer) div, .scenarioDisplayCard, .widgetDisplayCard, .pluginDisplayCard { text-align: center; border: none !important; background: transparent !important; padding-top: 0px !important; }
div[class*="ListContainer"] div[class*="DisplayCard"], div.eqLogicThumbnailContainer div[class*="DisplayCard"] { flex: 0 0 auto; }
.objectDisplayCard i { font-size: 38px !important; }
div[class*="DisplayCard"] { height: 130px !important; overflow: hidden; }
div.pluginDisplayCard, div.objectDisplayCard { height: 130px; min-height: 130px !important; }
div.objectDisplayCard > i { display: inline-block; height: 42px !important; }
div[class*="DisplayCard"] .name { top: 5px !important; position: relative; display: block !important; font-family: "Roboto"; font-size: 12px; font-weight: 700; line-height: 14px !important; }
div.objectDisplayCard .name { display: inline-block; padding: 4px 12px; border-radius: var(--border-radius) !important; }
input[type=checkbox] { position: relative; margin: 0 1rem 0 0; cursor: pointer; min-height : 0px !important; vertical-align: middle; }
.checkbox input[type=checkbox], .checkbox-inline input[type=checkbox], .radio input[type=radio], .radio-inline input[type=radio] { position: absolute; margin-top: 6px !important; margin-left: -20px; }
.modal-footer .btn.bootbox-accept { background-color: var(--al-success-color) !important; }
.modal-footer .btn.bootbox-cancel { background-color: var(--al-warning-color) !important; }
.btn.btn-danger { color: var(--sc-lightTxt-color) !important; background-color: var(--al-danger-color) !important; }
`;

/** Bootstrap 3 (embarqué par le cœur) : marges des cases à cocher. */
const BOOTSTRAP_RULES = `
.checkbox { position: relative; display: block; margin-top: 10px; margin-bottom: 10px; }
.checkbox label { min-height: 20px; padding-left: 20px; margin-bottom: 0; font-weight: 400; cursor: pointer; }
.checkbox + .checkbox { margin-top: -5px; }
.help-block { display: block; margin-top: 5px; margin-bottom: 10px; }
`;

const CORE_CSS = CORE_VARS + CORE_RULES + BOOTSTRAP_RULES;

/** CSS complet de la page du plugin : cœur d'abord (le plugin est chargé après lui sur la box), puis le CSS du plugin. */
function pageCss() {
  return CORE_CSS + fs.readFileSync(path.join(ROOT, 'desktop/css/jeedom2ha.css'), 'utf8');
}

function diag(reason) {
  return { confidence: null, ha_entity_type: null, publication_reason: reason, reason_code: null, should_publish: false,
    projection_validity: { is_valid: false, missing_capabilities: [], missing_fields: [], reason_code: reason } };
}

/** Entrée agrégée d'un équipement exclu (même forme que les tests de 25.7). */
function excludedEntry(id, reason) {
  return { jeedom_eq_id: id, commands: [{ jeedom_cmd_id: id * 10, covered: false, diagnostic: diag(reason), published_in_ha: false }], entities: [],
    equipment_decision: diag(reason), sync_status: { published_in_ha: false, synced_should_publish: false, current_should_publish: false } };
}

/** Scène fictive aux noms longs : une pièce dont le nom tient sur deux lignes, une pièce de travail avec causes d'exclusion. */
const UX_SCENE = {
  objects: [
    { id: 1, name: 'Logis démo', father_id: null, display: {} },
    { id: 2, name: 'Niveau démo', father_id: 1, display: { icon: '<i class="fas fa-bed"></i>' } },
    { id: 3, name: 'Chambre d\'amis Nord', father_id: 2, display: { icon: '<i class="fas fa-bed"></i>' } },
    { id: 4, name: 'Atelier', father_id: 2, display: { icon: '<i class="fas fa-couch"></i>' } },
    { id: 5, name: 'Remise démo', father_id: 1, display: { icon: '<i class="fas fa-door-open"></i>' } },
  ],
  eqlogics: {
    3: [{ id: 301, name: 'Lampe de chevet' }, { id: 302, name: 'Volet' }],
    4: [{ id: 401, name: 'Prise établi' }, { id: 402, name: 'Détecteur' }],
    5: [
      { id: 501, name: 'Ouverture porte de la remise', type: 'plugin_alpha' },
      { id: 502, name: 'Éclairage' },
      { id: 503, name: 'Robot aspirateur rangé dans la remise', type: 'plugin_alpha', enabled: false },
      { id: 504, name: 'Température' },
      { id: 505, name: 'Porte vers le cellier', type: 'plugin_beta' },
      { id: 506, name: 'Prise congélateur' },
    ],
  },
  plugin_names: { plugin_alpha: 'Passerelle Alpha', plugin_beta: 'Bêta Sécurité Maison' },
  doc: 'https://doc.example.test/plugin',
};

/** États de la scène : publiés (fixture 25.2) sauf les exclus par plugin et le désactivé. */
function uxEquipments(rooms, equipmentsFor) {
  const out = equipmentsFor(rooms);
  out['501'] = excludedEntry(501, 'excluded_plugin');
  out['503'] = excludedEntry(503, 'excluded_object');
  out['505'] = excludedEntry(505, 'excluded_plugin');
  return out;
}

/** 42 plugins fictifs, dont 6 exclus (ordre de la box : la liste est triée par nom affiché). */
function configFixture() {
  const names = {};
  const types = [];
  for (let i = 1; i <= 42; i++) {
    const id = 'plugin_' + String(i).padStart(2, '0');
    names[id] = 'Plugin fictif ' + String(i).padStart(2, '0');
    types.push(id);
  }
  return { eq_types: types.concat(['jeedom2ha']), plugin_names: names,
    config: { excludedPlugins: 'plugin_07,plugin_15,plugin_23,plugin_31,plugin_38,plugin_41', excludedObjects: '5' } };
}

/** Rendu de plugin_info/configuration.php avec un faux cœur (même méthode que test_story_25_9_configuration). */
function renderConfiguration(fixture) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'j2ha-cfg-'));
  const plugin = path.join(tmp, 'plugins', 'jeedom2ha');
  for (const dir of ['plugin_info', 'core/php', 'desktop/php']) fs.mkdirSync(path.join(plugin, dir), { recursive: true });
  fs.mkdirSync(path.join(tmp, 'core', 'php'), { recursive: true });
  fs.copyFileSync(path.join(ROOT, 'plugin_info/configuration.php'), path.join(plugin, 'plugin_info/configuration.php'));
  for (const file of fs.readdirSync(path.join(ROOT, 'core/php')).filter((f) => f.endsWith('.php'))) fs.copyFileSync(path.join(ROOT, 'core/php', file), path.join(plugin, 'core/php', file));
  fs.copyFileSync(path.join(ROOT, 'desktop/php/jeedom2ha_overview_helpers.php'), path.join(plugin, 'desktop/php/jeedom2ha_overview_helpers.php'));
  fs.writeFileSync(path.join(tmp, 'fixture.json'), JSON.stringify(fixture));
  fs.writeFileSync(path.join(tmp, 'core', 'php', 'core.inc.php'), `<?php
$GLOBALS['j2ha_fixture'] = json_decode(file_get_contents(${JSON.stringify(path.join(tmp, 'fixture.json'))}), true);
class J2haFakeEq { private $t; public function __construct($t) { $this->t = $t; } public function getEqType_name() { return $this->t; } }
class eqLogic { public static function all() { return array_map(function ($t) { return new J2haFakeEq($t); }, $GLOBALS['j2ha_fixture']['eq_types']); } }
class J2haFakePlugin { private $id; public function __construct($id) { $this->id = $id; } public function getName() { $n = $GLOBALS['j2ha_fixture']['plugin_names']; if (!isset($n[$this->id])) { throw new Exception('introuvable'); } return $n[$this->id]; } }
class plugin { public static function byId($id) { return new J2haFakePlugin($id); } }
class config { public static function byKey($key, $plugin = 'core', $default = '') { $c = $GLOBALS['j2ha_fixture']['config']; return array_key_exists($key, $c) ? $c[$key] : $default; } }
function isConnect($right = '') { return true; }
function include_file() {}
`);
  try {
    return execFileSync('php', [path.join(plugin, 'plugin_info/configuration.php')], { encoding: 'utf8' });
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

module.exports = { CORE_CSS, pageCss, UX_SCENE, uxEquipments, excludedEntry, configFixture, renderConfiguration };
