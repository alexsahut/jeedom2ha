// ARTEFACT — Story 25.4 (AC26) : un mot = une notion dans la vue de travail. Extension de test_story_25_1_glossaire et
// test_story_25_3_glossaire au nouveau fichier JS et aux ajouts de desktop/php : libellés nouveaux via {{…}} (aucun fichier
// core/i18n), aucune étiquette terminée par un point, pluriels accordés par le code, aucun terme interdit, plus de « modale » ni
// de « fenêtre de pièce » dans les libellés visibles. Données fictives (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const { startBig, openCard, phpAvailable } = require('./helpers/workview_harness');
const { plain } = require('./helpers/page_b_harness');
const { tree, ok, READY } = require('./helpers/ui_harness');

const root = path.join(__dirname, '..', '..');
const maybe = phpAvailable ? it : it.skip;
const word = (w) => new RegExp('(?<![\\p{L}\\p{N}_])' + w + '(?![\\p{L}\\p{N}_])', 'iu');
const FORBIDDEN = ['override', 'bridge', 'prête', 'prêtes', 'prêt', 'prêts', 'bloquante', 'bloquantes', 'rescanner', 'modale', 'modal'];
const source = fs.readFileSync(path.join(root, 'desktop/js/jeedom2ha_workview.js'), 'utf8');

function labels(code) {
  return [...code.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '').matchAll(/\{\{([^}]*)\}\}/g)].map((m) => m[1]);
}

describe('25.4 / AC26 — libellés de la vue', () => {
  it('les libellés exigés par la story passent par {{…}} et aucun fichier core/i18n n’existe', () => {
    const found = labels(source);
    for (const label of ['Toutes les pièces', 'Page principale', 'Pièces', 'Masquer les pièces', 'Rechercher une pièce ou un équipement', 'À traiter dans cette pièce',
      'Rien à traiter dans cette pièce', 'Aucun résultat', 'Sélectionnez une pièce ou un équipement', 'Pièces et équipements', 'Indicateurs de la pièce',
      "Fil d'Ariane", 'Replier', 'Déplier', 'Appliquer', 'Ouvrir les types génériques']) {
      assert.ok(found.includes(label), label);
    }
    assert.equal(fs.existsSync(path.join(root, 'core', 'i18n')), false);
  });

  it('aucun libellé de la vue ne se termine par un point ; aucun terme interdit ; plus de « modale » ni de « fenêtre de pièce »', () => {
    // Messages (phrases) conservés de 25.1 : la phrase de réassurance Homebridge se termine par un point, comme avant.
    const SENTENCES = ['Aucun impact Homebridge : cet écran ne modifie que la sortie Home Assistant de jeedom2ha.'];
    for (const label of labels(source)) {
      if (!SENTENCES.includes(label)) assert.doesNotMatch(label, /\.$/, label);
      for (const forbidden of FORBIDDEN) assert.doesNotMatch(label, word(forbidden), `« ${label} » contient « ${forbidden} »`);
      assert.doesNotMatch(label, /fenêtre (de|d'une|de la) pièce|\p{L}\(s\)|Sera publié/iu, label);
    }
    const php = fs.readFileSync(path.join(root, 'desktop/php/jeedom2ha.php'), 'utf8');
    assert.doesNotMatch(php.replace(/<!--[\s\S]*?-->/g, ''), /modale|fenêtre de pièce/i);
  });

  maybe('rendu : les mots d’état viennent de la table de 25.1 ; aucune étiquette de bouton, de puce ou de KPI ne se termine par un point', () => {
    const ui = startBig({ rooms: 3, equipments: 40, seed: 17, unread: 2 });
    openCard(ui, 10);
    for (const el of ui.$('.j2ha-wv-tree .j2ha-state-text').list) assert.ok(Object.values(M.EQUIPMENT_STATE_LABELS).includes(plain(ui.$(el).text()).trim()));
    for (const selector of ['.j2ha-wv-chip', '.j2ha-wv-kpi', '.j2ha-wv-back', '.j2ha-wv-widen', '.j2ha-wv-drawer-toggle', '.j2ha-room-republish', '.j2ha-wv-todo-apply', '.j2ha-mark', '.j2ha-wv-todo-title']) {
      ui.$('.j2ha-wv ' + selector).list.forEach((el) => assert.doesNotMatch(plain(ui.$(el).text()).trim(), /\.$/, selector));
    }
    const rendered = plain(ui.$('#j2ha_workView').text());
    for (const forbidden of FORBIDDEN) assert.doesNotMatch(rendered, word(forbidden), forbidden);
    assert.doesNotMatch(rendered, /\p{L}\(s\)/u);
  });

  maybe('pluriels accordés par le code : « 1 bloquée » / « 2 bloquées », « 1 équipement non lu » / « 2 équipements non lus », jamais « (s) »', () => {
    const ui = startBig({ rooms: 3, equipments: 40, seed: 17, unread: 2 });
    openCard(ui, 10);
    const texts = ui.$('.j2ha-wv .j2ha-mark, .j2ha-wv .j2ha-wv-kpi, .j2ha-wv .j2ha-wv-kpi-note, .j2ha-wv .j2ha-wv-chip').list.map((el) => plain(ui.$(el).text()).trim());
    for (const text of texts) {
      const n = Number(text.split(' ')[0]);
      if (!Number.isFinite(n)) continue;
      if (n === 1) assert.doesNotMatch(text, /(publiés|bloqués|bloquées|non lus|équipements non lus)$/, text);
      if (n > 1) assert.doesNotMatch(text, /(publié|bloqué|bloquée|non lu|équipement non lu)$/, text);
    }
    const detail = startBig({ rooms: 3, equipments: 40, seed: 17 });
    detail.openRoomWith(10, [ok(tree(1000, [READY]))], { states: false });
  });

  it('le glossaire de 25.1 reste la seule table de libellés d’état : la vue n’en définit aucune', () => {
    assert.doesNotMatch(source, /EQUIPMENT_STATE_LABELS\s*=|'Rien à publier'|"Rien à publier"/);
    for (const label of Object.values(M.EQUIPMENT_STATE_LABELS)) assert.ok(!labels(source).includes(label), label + ' redéfini dans la vue');
  });
});
