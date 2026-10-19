// ARTEFACT — Story 25.3 (AC10, AC14) : un mot = une notion sur la page B. Extension de test_story_25_1_glossaire au
// squelette PHP rendu et au nouveau fichier JS : aucun terme interdit dans les textes rendus (infobulles et
// aria-label compris), mots d'état de 25.1, pluriels accordés, aucune étiquette terminée par un point.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const { SCENE, plain, phpAvailable, renderPhp, mainPart, startPage } = require('./helpers/page_b_harness');

const maybe = phpAvailable ? it : it.skip;
const word = (w) => new RegExp('(?<![\\p{L}\\p{N}_])' + w + '(?![\\p{L}\\p{N}_])', 'iu');
const FORBIDDEN = ['override', 'bridge', 'prête', 'prêtes', 'prêt', 'prêts', 'bloquante', 'bloquantes', 'rescanner'];

function texts(ui) {
  const out = [];
  const walk = (el) => {
    ['aria-label', 'title'].forEach((a) => { if (el.attrs && el.attrs[a]) out.push(plain(el.attrs[a])); });
    el.children.forEach((c) => { if (c.children) walk(c); else if (c.text && c.text.trim()) out.push(plain(c.text).trim()); });
  };
  ui.dom.body.children.filter((c) => c.children).forEach(walk);
  return out;
}

describe('25.3 / AC14 — glossaire de la page B', () => {
  maybe('aucun terme interdit dans le squelette rendu ni dans les textes rendus par le JS, filtre actif compris', () => {
    const ui = startPage();
    ui.page.setFilter('published');
    const found = [];
    for (const text of texts(ui).concat(plain(mainPart(renderPhp(SCENE).html).replace(/<[^>]*>/g, ' ')).split('\n'))) {
      for (const f of FORBIDDEN) if (word(f).test(text)) found.push(`« ${text} » contient « ${f} »`);
      assert.doesNotMatch(text, /Sera publié|\p{L}\(s\)/u, text);
    }
    assert.deepEqual(found, []);
  });

  maybe('les mots d’état de la liste filtrée sont ceux de 25.1 (une seule table de libellés)', () => {
    const ui = startPage();
    const seen = new Set();
    for (const key of ['published', 'blocked', 'to_apply', 'other']) {
      ui.page.setFilter(key);
      ui.$('#j2ha_filterList .j2ha-state-text').list.forEach((el) => seen.add(plain(ui.$(el).text()).trim()));
      ui.page.setFilter(null);
    }
    assert.ok(seen.size > 0);
    const labels = Object.values(M.EQUIPMENT_STATE_LABELS);
    seen.forEach((label) => assert.ok(labels.includes(label), label));
  });

  maybe('aucune étiquette de bouton, de puce ou de repère ne se termine par un point', () => {
    const ui = startPage();
    for (const selector of ['.j2ha-chip-filter', '.j2ha-mark', '#bt_refreshStates', '#bt_clearFilter', '.j2ha-menu-item', '.j2ha-health-actions .btn', '.j2ha-room-ratio']) {
      ui.$(selector).list.forEach((el) => assert.doesNotMatch(plain(ui.$(el).text()).trim(), /\.$/, selector));
    }
  });

  maybe('pluriels accordés par le code : « 1 non lu », « 2 non lus », « N bloqués », jamais « non lu(s) »', () => {
    const ui = startPage();
    assert.equal(plain(ui.$('#j2ha_houseChips .j2ha-chip-filter[data-filter="unread"]').text()).trim(), '1 non lu');
    ui.$('.j2ha-chip-filter, .j2ha-mark, .j2ha-room-ratio').list.forEach((el) => {
      const text = plain(ui.$(el).text());
      assert.doesNotMatch(text, /\(s\)/, text);
      assert.doesNotMatch(text, /\b1 (publiés|bloqués|non lus)\b|\b[2-9] (publié|bloqué|non lu)\b/, text);
    });
  });
});
