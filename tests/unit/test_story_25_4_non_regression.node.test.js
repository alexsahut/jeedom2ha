// ARTEFACT — Story 25.4 (AC4, AC15, AC31, AC32) : non-régression. Aucune modification du démon, des routes, du relais ni des
// artefacts figés ; `jeedom2ha_mapping_override.js` n'a que des ajouts ; la vue n'ajoute ni copie ni re-sérialisation des
// états ; parité d'état entre l'arbre (entrée agrégée) et le détail (arbre unitaire), y compris après une relecture ; le calcul
// de l'arbre, des KPI et des filtres sur 292 équipements est mesuré (sans seuil inventé). Données fictives (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const O = require('../../desktop/js/jeedom2ha_overview.js');
const W = require('../../desktop/js/jeedom2ha_workview.js');
const { diffAgainstBase, removedLines } = require('./helpers/git_base');
const { FIXTURE, phpAvailable, SCENE, clone } = require('./helpers/page_b_harness');
const { startWorkview, openCard } = require('./helpers/workview_harness');
const { makeScene } = require('./helpers/big_scene');
const { ok } = require('./helpers/ui_harness');

const root = path.join(__dirname, '..', '..');
const maybe = phpAvailable ? it : it.skip;
const stripComments = (source) => source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

describe('25.4 / AC31 — le démon, les routes et les artefacts figés ne changent pas', () => {
  // Stories 25.8 et 25.9 (adaptation par ajout) : seules ces lignes existantes ont été remplacées — la liste blanche de la route agrégée
  // gagne `present_in_ha` (25.8, Q1 B) et `saveFilteringConfig` n'écrit plus la clé des pièces exclues (25.9, AC6). Tout autre
  // retrait dans ces fichiers fait échouer le garde.
  const REPLACED_BY_25_8_25_9 = [
    '"entities": [{"override_pending": e["override_pending"]} for e in tree["entities"]],',
    'equipment_decision, entities[{override_pending}], commands[{jeedom_cmd_id, covered,',
    'assert all(set(e) == {"override_pending"} for e in entry["entities"])', // test de la liste blanche de 25.2, mis à jour avec elle
    "$excludedPlugins  = init('excludedPlugins', '');",
    "$excludedObjects  = init('excludedObjects', '');",
    "$confidencePolicy = init('confidencePolicy', 'sure_probable');",
    '// Validation : valeurs autorisées uniquement',
    "if (!in_array($confidencePolicy, ['sure_only', 'sure_probable'])) {",
    "$confidencePolicy = 'sure_probable';",
    '}',
    "config::save('excludedPlugins',  $excludedPlugins,  'jeedom2ha');",
    "config::save('excludedObjects',  $excludedObjects,  'jeedom2ha');",
    "config::save('confidencePolicy', $confidencePolicy, 'jeedom2ha');",
    "log::add('jeedom2ha', 'info', '[CONFIG] saveFilteringConfig: excludedPlugins=\"'",
    '. $excludedPlugins . \'" excludedObjects="\' . $excludedObjects',
    '. \'" confidencePolicy="\' . $confidencePolicy . \'"\');',
  ];

  it('git diff --stat sur core/class/ et les scripts de déploiement : vide', () => {
    const diff = diffAgainstBase(['--stat'], [
      'core/class/', 'scripts/deploy-to-box.sh', 'scripts/parity-snapshot.sh', 'scripts/deploy-inventory-diff.sh',
    ]);
    if (diff !== null) assert.equal(diff, '');
  });

  it('resources/daemon/, core/ajax/, lib/policy.mjs : aucune ligne existante retirée, hors les remplacements de 25.8 et 25.9', () => {
    const diff = diffAgainstBase(['-U0'], ['resources/daemon/', 'core/ajax/', 'tests/e2e/gate/lib/policy.mjs']);
    if (diff === null) return;
    const unexpected = removedLines(diff).map((line) => line.slice(1).trim()).filter((line) => !REPLACED_BY_25_8_25_9.includes(line));
    assert.deepEqual(unexpected, []);
  });

  it('aucun fichier core/i18n n’est créé', () => {
    assert.equal(fs.existsSync(path.join(root, 'core', 'i18n')), false);
  });

  it('jeedom2ha_mapping_override.js : aucune ligne modifiée ni retirée (seuls des ajouts sont admis)', () => {
    const diff = diffAgainstBase(['-U0'], ['desktop/js/jeedom2ha_mapping_override.js']);
    if (diff !== null) assert.deepEqual(removedLines(diff), []);
  });

  it('la partition des causes n’est dupliquée nulle part (COMMAND_CAUSE_CATEGORIES / categoryOfCause hors du module pur)', () => {
    for (const file of fs.readdirSync(path.join(root, 'desktop/js')).filter((f) => f.endsWith('.js') && f !== 'jeedom2ha_mapping_override.js')) {
      assert.doesNotMatch(fs.readFileSync(path.join(root, 'desktop/js', file), 'utf8'), /COMMAND_CAUSE_CATEGORIES|categoryOfCause/, file);
    }
  });
});

describe('25.4 / AC32 — aucune copie ni re-sérialisation des états', () => {
  it('aucun JSON.stringify ni copie profonde des états (payload.equipments, agrégats) dans la page B et dans la vue', () => {
    for (const file of ['jeedom2ha_overview.js', 'jeedom2ha_workview.js']) {
      const code = stripComments(fs.readFileSync(path.join(root, 'desktop/js', file), 'utf8'));
      assert.doesNotMatch(code, /structuredClone/, file);
      // Le seul JSON.* de la vue est le repli de session de l'état d'URL (pièce, équipement, filtre), jamais les états.
      for (const call of code.match(/JSON\.(stringify|parse)\([^)]*\)/g) || []) {
        assert.doesNotMatch(call, /equipments|payload|entries|overview|snapshot|valid/, file + ' : ' + call);
      }
    }
  });

  it('la liste blanche et le budget de la route : le seul changement est l\'ajout de `present_in_ha` aux entités (Story 25.8, Q1 B)', () => {
    const diff = diffAgainstBase(['-U0'], ['resources/daemon/transport/http_server.py']);
    if (diff === null) return;
    const removed = removedLines(diff).map((line) => line.slice(1).trim());
    if (diff === '') {
      // Base déjà porteuse de 25.8 (CI de `main` après la fusion de #309) : le diff est vide, on vérifie l'état final.
      const source = fs.readFileSync(path.join(root, 'resources/daemon/transport/http_server.py'), 'utf8');
      assert.ok(source.includes('{"override_pending": e["override_pending"], "present_in_ha": e["present_in_ha"]}'));
      assert.doesNotMatch(diff, /BUDGET|1_500_000|1500000/);
      return;
    }
    assert.deepEqual(removed, [
      '"entities": [{"override_pending": e["override_pending"]} for e in tree["entities"]],',
      'equipment_decision, entities[{override_pending}], commands[{jeedom_cmd_id, covered,',
    ]);
    assert.ok(diff.includes('"present_in_ha": e["present_in_ha"]'));
    assert.doesNotMatch(diff, /BUDGET|1_500_000|1500000/);
  });

  it('292 équipements de la forme la plus lourde : calcul de l’arbre, des KPI et des filtres mesuré (consigné, sans seuil)', (t) => {
    const big = makeScene({ rooms: 12, equipments: 292, seed: 25, longNames: true, grouped: true, unread: 5 });
    const rooms = W.decorateRooms(big.scene.objects ? [] : []);
    void rooms;
    const raw = [];
    Object.entries(big.scene.eqlogics).forEach(([key, list]) => {
      const id = key === 'null' ? 0 : Number(key);
      const object = big.scene.objects.find((o) => o.id === id);
      raw.push({ object_id: id, object_name: object ? object.name : 'Sans pièce', equipments: list.map((e) => ({ eq_id: e.id, eq_name: e.name, enabled: e.enabled })) });
    });
    const decorated = W.decorateRooms(raw);
    const timeOf = (fn) => { const t0 = process.hrtime.bigint(); fn(); return Number(process.hrtime.bigint() - t0) / 1e6; };
    let overview;
    const computeMs = timeOf(() => { overview = O.computeOverview(raw, big.equipments); });
    const treeMs = timeOf(() => { W.buildTreeModel({ rooms: decorated, groups: null, overview, filter: null, search: '', expanded: Object.fromEntries(decorated.map((r) => [r.object_id, true])), selectedRoom: null, selectedEq: null }); });
    const filterMs = timeOf(() => { ['published', 'blocked', 'to_apply', 'other', 'unread'].forEach((f) => W.buildTreeModel({ rooms: decorated, groups: null, overview, filter: f, search: 'eq', expanded: {}, selectedRoom: null, selectedEq: null })); });
    const kpiMs = timeOf(() => { overview.rooms.forEach((r) => { M.buildRoomCounterLabels(r.summary); W.buildTreatList(r, big.equipments, decorated.find((d) => d.object_id === r.object_id)); }); });
    t.diagnostic(`292 équipements — états + agrégats : ${computeMs.toFixed(1)} ms ; arbre complet : ${treeMs.toFixed(1)} ms ; 5 filtres + recherche : ${filterMs.toFixed(1)} ms ; KPI + « À traiter » : ${kpiMs.toFixed(1)} ms`);
    for (const ms of [computeMs, treeMs, filterMs, kpiMs]) assert.ok(Number.isFinite(ms));
    assert.equal(overview.total, 292);
  });
});

describe('25.4 / AC15 — parité d’état entre l’arbre (entrée agrégée) et le détail (arbre unitaire)', () => {
  maybe('pour chaque équipement du corpus de 25.2 : le mot d’état de la ligne d’arbre égale le badge du détail, avant et après une relecture', () => {
    const ids = Object.keys(FIXTURE);
    const objects = [{ id: 10, name: 'Zone fictive', father_id: null, display: {} }];
    const eqlogics = { 10: ids.map((id) => ({ id: Number(id), name: 'Eq ' + id, enabled: FIXTURE[id].enabled !== false })) };
    const equipments = {};
    ids.forEach((id) => { equipments[id] = clone(FIXTURE[id].aggregated); });
    const ui = startWorkview({ scene: { objects, eqlogics, doc: 'https://doc.example.test/plugin' }, equipments });
    openCard(ui, 10);
    for (const id of ids) {
      ui.selectEquipment(Number(id), ok(clone(FIXTURE[id].tree)));
      const treeWord = ui.text(`.j2ha-wv-eq[data-eq-id="${id}"] .j2ha-state-word`).trim();
      const badge = ui.text(`.j2ha-eq-panel[data-eq-id="${id}"] .j2ha-eq-publish-badge`).trim();
      assert.equal(treeWord, badge, 'équipement ' + id);
      assert.equal(treeWord, M.EQUIPMENT_STATE_LABELS[M.resolveEquipmentState(equipments[id], FIXTURE[id].enabled !== false).state]);
      // Relecture simulée : un nouveau rendu de B rafraîchit le badge depuis l'entrée agrégée (mêmes fonctions).
      ui.page.render();
      assert.equal(ui.text(`.j2ha-eq-panel[data-eq-id="${id}"] .j2ha-eq-publish-badge`).trim(), treeWord, 'après relecture ' + id);
    }
  });

  maybe('« À traiter » : les causes de la liste (entrée agrégée) sont celles de l’encart du détail (arbre unitaire)', () => {
    const ids = Object.keys(FIXTURE).filter((id) => M.groupBlockedCauses(FIXTURE[id].tree).length > 0);
    assert.ok(ids.length >= 1, 'le corpus contient un équipement bloqué');
    for (const id of ids) {
      assert.deepEqual(
        M.groupBlockedCauses(FIXTURE[id].aggregated).map((g) => [g.code, g.label, g.count]),
        M.groupBlockedCauses(FIXTURE[id].tree).map((g) => [g.code, g.label, g.count]),
        'équipement ' + id,
      );
    }
  });

  it('SCENE reste exploitable par la vue (sanity)', () => {
    assert.ok(SCENE.objects.length > 0);
  });
});
