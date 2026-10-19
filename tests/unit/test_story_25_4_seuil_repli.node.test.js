// ARTEFACT — Story 25.4 (AC9, AC20 à AC22, Q3, Q12) : le seuil de repli est UNE constante JS reprise à l'identique par
// la media query CSS ; la disposition (`data-j2ha-layout`) suit matchMedia avec repli `resize` ; passer d'une
// disposition à l'autre conserve sélection, filtre, recherche et n'émet aucune requête ; tiroir « Pièces » ; hauteur
// mesurée à l'exécution. Vrai code sur faux DOM / faux navigateur ; données fictives (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const W = require('../../desktop/js/jeedom2ha_workview.js');
const { startBig, openCard, phpAvailable } = require('./helpers/workview_harness');
const { tree, ok, READY } = require('./helpers/ui_harness');

const maybe = phpAvailable ? it : it.skip;
const css = fs.readFileSync(path.join(__dirname, '..', '..', 'desktop', 'css', 'jeedom2ha.css'), 'utf8');

/** Valeurs `min-width` des media queries qui portent des règles de la vue (`.j2ha-wv`). */
function viewMediaThresholds(source) {
  const out = [];
  const re = /@media\s*\(min-width:\s*([0-9.]+)px\)\s*\{/g;
  let m;
  while ((m = re.exec(source))) {
    let depth = 1;
    let i = re.lastIndex;
    while (i < source.length && depth > 0) {
      if (source[i] === '{') depth += 1;
      else if (source[i] === '}') depth -= 1;
      i += 1;
    }
    if (/\.j2ha-wv/.test(source.slice(re.lastIndex, i))) out.push(Number(m[1]));
  }
  return out;
}

describe('25.4 / AC21 — une constante, un seul endroit', () => {
  it('la constante JS est exportée ; la media query CSS reprend la même valeur (le test échoue si elles divergent)', () => {
    assert.equal(typeof W.LAYOUT_SPLIT_MIN_WIDTH, 'number');
    assert.ok(Number.isInteger(W.LAYOUT_SPLIT_MIN_WIDTH) && W.LAYOUT_SPLIT_MIN_WIDTH >= 600);
    const thresholds = viewMediaThresholds(css);
    assert.ok(thresholds.length >= 1, 'la disposition large est déclarée par une media query');
    thresholds.forEach((value) => assert.equal(value, W.LAYOUT_SPLIT_MIN_WIDTH));
  });

  it('la constante n’est définie qu’une fois dans le JS de la vue', () => {
    const source = fs.readFileSync(path.join(__dirname, '..', '..', 'desktop', 'js', 'jeedom2ha_workview.js'), 'utf8');
    const definitions = source.match(/LAYOUT_SPLIT_MIN_WIDTH\s*=\s*\d+/g) || [];
    assert.equal(definitions.length, 1);
    assert.doesNotMatch(source.replace(/LAYOUT_SPLIT_MIN_WIDTH\s*=\s*\d+/, ''), /\b1024\b/);
  });
});

describe('25.4 / AC21, AC22 — disposition et tiroir', () => {
  const layout = (ui) => ui.$('#j2ha_workView').attr('data-j2ha-layout');

  maybe('data-j2ha-layout vaut « split » à partir du seuil, « compact » en dessous', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6, window: { width: 1280 } });
    openCard(ui, 10);
    assert.equal(layout(ui), 'split');
    ui.win.setSize(W.LAYOUT_SPLIT_MIN_WIDTH - 1, 800);
    assert.equal(layout(ui), 'compact');
    ui.win.setSize(W.LAYOUT_SPLIT_MIN_WIDTH, 800);
    assert.equal(layout(ui), 'split');
  });

  maybe('sans matchMedia : repli sur resize', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6, window: { width: 1280, noMatchMedia: true } });
    openCard(ui, 10);
    assert.equal(layout(ui), 'split');
    ui.win.setSize(700, 900);
    assert.equal(layout(ui), 'compact');
  });

  maybe('changer de disposition (rotation) conserve sélection, filtre, recherche ; aucune requête', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6, window: { width: 1280, height: 800 } });
    openCard(ui, 10);
    const eq = Number(ui.$('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.selectEquipment(eq, ok(tree(eq, [READY])));
    ui.click('.j2ha-wv-chips .j2ha-chip-filter[data-filter="published"]');
    const input = ui.$('.j2ha-wv-search').list[0];
    input.props.value = 'eq';
    input.handlers.input.call(input, { target: input });
    ui.advance(400);
    const before = ui.calls.length;
    ui.win.rotate();
    assert.equal(layout(ui), 'compact');
    assert.equal(ui.calls.length, before);
    assert.equal(ui.$(`.j2ha-eq-panel[data-eq-id="${eq}"]`).length, 1);
    assert.equal(ui.page.filter(), 'published');
    assert.equal(ui.$('.j2ha-wv-search').list[0].props.value, 'eq');
    ui.win.rotate();
    assert.equal(layout(ui), 'split');
    assert.equal(ui.calls.length, before);
  });

  maybe('compact : bouton « Pièces » (aria-expanded, aria-controls), replié si une sélection existe, ouvert sinon ; sélectionner referme', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6, window: { width: 800, height: 1000 } });
    ui.openRoom(10);
    const toggle = ui.$('.j2ha-wv-drawer-toggle');
    const nav = ui.$('.j2ha-wv-nav');
    assert.equal(toggle.length, 1);
    assert.equal(toggle.attr('aria-controls'), nav.attr('id'));
    assert.equal(toggle.attr('aria-expanded'), 'false', 'une sélection existe : replié par défaut');
    ui.click('.j2ha-wv-drawer-toggle');
    assert.equal(toggle.attr('aria-expanded'), 'true');
    assert.ok(nav.hasClass('j2ha-wv-nav-open'));
    ui.click('.j2ha-wv-room[data-object_id="11"] .j2ha-wv-row');
    assert.equal(toggle.attr('aria-expanded'), 'false', 'sélectionner referme le tiroir');
    assert.ok(!nav.hasClass('j2ha-wv-nav-open'));
    const none = startBig({ rooms: 3, equipments: 30, seed: 6, window: { width: 800 } });
    none.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="published"]'); // ouverture par un filtre : aucune sélection
    assert.equal(none.$('.j2ha-wv-drawer-toggle').attr('aria-expanded'), 'true', 'aucune sélection : le panneau est ouvert');
  });

  maybe('le changement de disposition est annoncé dans une zone role="status" aria-live="polite"', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6, window: { width: 1280 } });
    openCard(ui, 10);
    ui.win.setSize(700, 900);
    const live = ui.$('.j2ha-wv-live');
    assert.equal(live.attr('role'), 'status');
    assert.equal(live.attr('aria-live'), 'polite');
    assert.match(live.text(), /./);
  });
});

describe('25.4 / AC9, Q12 — hauteur mesurée à l’exécution', () => {
  maybe('hauteur = fenêtre − décalage haut mesuré, minimum 480 px ; recalculée sur resize et orientationchange', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 6, window: { width: 1280, height: 900 }, offsetTop: 150 });
    openCard(ui, 10);
    assert.equal(ui.wv.height(), 750);
    ui.win.setSize(1280, 500);
    assert.equal(ui.wv.height(), 480, 'hauteur minimale utile');
    ui.win.setSize(1280, 1000);
    assert.equal(ui.wv.height(), 850);
    ui.win.rotate();
    assert.equal(ui.wv.height(), Math.max(480, ui.win.innerHeight - 150));
  });

  it('CSS : dvh avec repli vh, sticky avec repli, aucune hauteur de maquette figée à 640 px', () => {
    assert.match(css, /--j2ha-wv-height/);
    assert.match(css, /100vh[\s\S]{0,200}100dvh|100dvh[\s\S]{0,200}100vh/);
    assert.doesNotMatch(css, /\.j2ha-wv[^{]*\{[^}]*height:\s*640px/);
  });
});
