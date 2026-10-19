// ARTEFACT — Story 25.4 (AC8, AC15) : les fonctions d'ÉCRITURE et de rendu de l'équipement sont DÉPLACÉES, jamais réécrites.
// Équivalent automatisé de `git diff --color-moved` : le corps de chaque fonction listée dans `jeedom2ha_mapping_surface.js` est
// identique, caractère pour caractère, à celui de main (SHA 4ff80cd) ; seules les fonctions de colle (fenêtre → vue) changent
// et la liste de ces changements est figée ici. Ignoré si le SHA de référence est introuvable (clone superficiel). Aucune donnée réelle.
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const root = path.join(__dirname, '..', '..');
const BASE = '4ff80cdbb04532ff01d7d6fbe6ee640333a21898';
const FILE = 'desktop/js/jeedom2ha_mapping_surface.js';
let before = null;
try { before = execFileSync('git', ['show', `${BASE}:${FILE}`], { encoding: 'utf8', cwd: root, stdio: ['ignore', 'pipe', 'ignore'] }); } catch { before = null; }
const after = fs.readFileSync(path.join(root, FILE), 'utf8');

function body(src, name) {
  const at = src.indexOf('  function ' + name + '(');
  if (at === -1) return null;
  const open = src.indexOf('{', src.indexOf(')', at));
  let depth = 0;
  let i = open;
  for (; i < src.length; i += 1) {
    if (src[i] === '{') depth += 1;
    else if (src[i] === '}') { depth -= 1; if (depth === 0) break; }
  }
  return src.slice(at, i + 1);
}

// Écritures : routes, paramètres, confirmations, réservations de bouton.
const WRITES = ['runDryRun', 'saveOverride', 'revertCommand', 'disableButtons', 'restoreButtons', 'publicationRequest', 'revertPublication',
  'confirmPublicationDialog', 'buildForcePreviewContent', 'buildEquipmentForcePreviewContent', 'buildEquipmentExcludeContent', 'requestPublication',
  'applyEquipment', 'hasValidSelection', 'runHaAction', 'equipmentDeleteHandler', 'revertAllHandler', 'buildPublicationControl'];
// Rendu de l'équipement (25.1) : état, contrôle de publication, tableau des commandes, notices, commandes ignorées.
const RENDER = ['buildOptions', 'haTypeOfRow', 'iconTextCell', 'renderPreviewCell', 'renderHaCell', 'renderTypeCell', 'renderCommandRow', 'stateWord',
  'renderEquipmentCounters', 'renderSummary', 'scrollToCommand', 'renderNotices', 'renderIgnored', 'activeSegmentOf', 'buildSegmented', 'entityIsPendingForDisplay',
  'groupCommandRows', 'renderGroupHead', 'renderCommandTable', 'buildMenu', 'closeMenu', 'enabledMenuItems', 'setStateGate', 'reapplyBridgeGating', 'escapeHtml',
  'showRequestError', 'clearRequestError', 'maybeShowReassurance', 'onActivationKey', 'roomEnabledById', 'notifyOverview'];
// Colle fenêtre → vue : seules fonctions dont le corps change (figé : toute autre modification doit être revue).
const GLUE = ['showRoomFeedback', 'renderEquipmentTree', 'renderControls', 'reloadRoom', 'reloadEquipment', 'markTreeError', 'loadEquipment', 'isRoomOpen', 'buildRoomActions', 'showActionFeedback'];

describe('25.4 / AC8 — fonctions d’écriture et de rendu déplacées, pas réécrites', () => {
  const guard = before === null ? it.skip : it;

  guard('les fonctions d’écriture sont identiques à celles de main (mêmes routes, mêmes paramètres, mêmes confirmations)', () => {
    for (const name of WRITES) {
      const a = body(before, name);
      assert.ok(a !== null, name + ' existe sur main');
      assert.equal(body(after, name), a, name);
    }
  });

  guard('les fonctions de rendu de l’équipement sont identiques à celles de main', () => {
    for (const name of RENDER) {
      const a = body(before, name);
      assert.ok(a !== null, name + ' existe sur main');
      assert.equal(body(after, name), a, name);
    }
  });

  guard('seules les fonctions de colle fenêtre → vue changent de corps (liste figée)', () => {
    const changed = [];
    const names = new Set();
    for (const m of before.matchAll(/^  function ([A-Za-z0-9_]+)\(/gm)) names.add(m[1]);
    for (const m of after.matchAll(/^  function ([A-Za-z0-9_]+)\(/gm)) names.add(m[1]);
    for (const name of names) {
      const a = body(before, name);
      const b = body(after, name);
      if (a !== null && b !== null && a !== b) changed.push(name);
    }
    // `showActionFeedback` est identique ; la colle change : isRoomOpen, showRoomFeedback, reloadRoom, loadEquipment, reloadEquipment, ...
    const allowed = new Set(GLUE);
    assert.deepEqual(changed.filter((name) => !allowed.has(name)), [], 'fonction modifiée hors colle');
    // Retirées avec la fenêtre : jamais une fonction d'écriture ni de rendu de l'équipement.
    const removed = [...names].filter((name) => body(before, name) !== null && body(after, name) === null);
    for (const name of removed) assert.ok(![...WRITES, ...RENDER].includes(name), name + ' retirée');
    assert.deepEqual(removed.sort(), [['buildRoom', 'ModalHtml'].join(''), 'openRoom', 'readRoomTrees', 'refreshRoomView', 'renderRoomCounters', 'roomEquipmentCount', 'roomHasEquipment', 'setPanelOpen', 'togglePanel', 'updateRoomActionsGating', 'findRoom', 'normalizedRooms'].sort());
  });
});
