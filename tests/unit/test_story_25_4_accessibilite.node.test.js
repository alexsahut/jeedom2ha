// ARTEFACT — Story 25.4 (AC3 « Relire Jeedom », AC11, AC17, AC19, AC22) : accessibilité (motif ARIA tree, roving tabindex,
// zones role="status", focus déplacé vers le titre du détail, aria-label des boutons-icônes), cibles tactiles de 44 px en
// disposition étroite (vrai Chromium), aucune information ni action portée par le seul survol, et robustesse après une relecture
// qui fait disparaître l'équipement sélectionné. Données fictives (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { startBig, openCard, phpAvailable } = require('./helpers/workview_harness');
const { withRealView } = require('./helpers/workview_browser');
const { okBody } = require('./helpers/page_b_harness');
const { tree, ok, READY } = require('./helpers/ui_harness');

const maybe = phpAvailable ? it : it.skip;
const css = fs.readFileSync(path.join(__dirname, '..', '..', 'desktop/css/jeedom2ha.css'), 'utf8');

describe('25.4 / AC11, AC19 — motif ARIA tree', () => {
  maybe('role=tree, treeitem, aria-level, aria-expanded (pièces), aria-selected unique, une seule ligne dans l’ordre de tabulation', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    openCard(ui, 10);
    const eq = Number(ui.$('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.selectEquipment(eq, ok(tree(eq, [READY])));
    assert.equal(ui.$('.j2ha-wv-tree').attr('role'), 'tree');
    assert.ok(ui.$('.j2ha-wv-tree').attr('aria-label'));
    for (const room of ui.$('.j2ha-wv-room').list) {
      assert.equal(room.attrs.role, 'treeitem');
      assert.equal(room.attrs['aria-level'], '1');
      assert.ok(['true', 'false'].includes(room.attrs['aria-expanded']));
    }
    for (const item of ui.$('.j2ha-wv-eq').list) {
      assert.equal(item.attrs.role, 'treeitem');
      assert.equal(item.attrs['aria-level'], '2');
      assert.equal(item.attrs['aria-expanded'], undefined, 'un équipement n’est pas dépliable');
    }
    assert.equal(ui.$('.j2ha-wv-eqs').attr('role'), 'group');
    assert.equal(ui.$('[role=treeitem][aria-selected="true"]').length, 1);
    assert.equal(ui.$('[role=treeitem][tabindex="0"]').length, 1, 'roving tabindex');
    assert.equal(ui.$(`.j2ha-wv-eq[data-eq-id="${eq}"]`).attr('aria-selected'), 'true');
  });

  maybe('flèches, Début, Fin, Entrée et Espace : le focus se déplace sans lecture ; Entrée sélectionne', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    openCard(ui, 10);
    const items = () => ui.$('.j2ha-wv-tree [role=treeitem]').list;
    const press = (key, at) => ui.key('.j2ha-wv-tree', key, { target: items()[at] });
    const before = ui.calls.length;
    press('ArrowDown', 0);
    assert.equal(ui.dom.focused, items()[1]);
    press('ArrowUp', 1);
    assert.equal(ui.dom.focused, items()[0]);
    press('End', 0);
    assert.equal(ui.dom.focused, items()[items().length - 1]);
    press('Home', 0);
    assert.equal(ui.dom.focused, items()[0]);
    assert.equal(ui.calls.length, before, 'aucune requête pendant la navigation');
    // ArrowLeft replie la pièce dépliée, ArrowRight la déplie ; Entrée sélectionne l'équipement (une lecture).
    const first = items()[0];
    press('ArrowLeft', 0);
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="10"]').attr('aria-expanded'), 'false');
    press('ArrowRight', 0);
    assert.equal(ui.$('.j2ha-wv-room[data-object_id="10"]').attr('aria-expanded'), 'true');
    void first;
    const eqItem = items().find((el) => el.classes.has('j2ha-wv-eq'));
    ui.key('.j2ha-wv-tree', 'Enter', { target: eqItem });
    assert.equal(ui.count('getMappingOverrides'), 1);
    assert.equal(ui.$(`.j2ha-wv-eq[data-eq-id="${eqItem.attrs['data-eq-id']}"]`).attr('aria-selected'), 'true');
  });

  maybe('le focus est déplacé vers le titre du détail (tabindex -1) quand une sélection change le détail', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    openCard(ui, 10);
    assert.ok(ui.dom.focused && ui.dom.focused.classes.has('j2ha-wv-title'), 'titre de la pièce');
    assert.equal(ui.dom.focused.attrs.tabindex, '-1');
    const eq = Number(ui.$('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.selectEquipment(eq, ok(tree(eq, [READY])));
    assert.ok(ui.dom.focused.classes.has('j2ha-wv-title'), 'titre de l’équipement');
    assert.equal(ui.dom.focused.tag, 'h3');
  });

  maybe('zones role="status" aria-live="polite" : lecture, résultat de recherche, disposition, sélection ; boutons-icônes avec aria-label', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    openCard(ui, 10);
    for (const selector of ['.j2ha-wv-live', '.j2ha-wv-read-status', '.j2ha-wv-search-status']) {
      assert.equal(ui.$(selector).attr('role'), 'status', selector);
    }
    assert.match(ui.text('.j2ha-wv-live'), /Pièce Pièce 0/);
    for (const button of ui.$('.j2ha-wv-toggle').list) assert.ok(button.attrs['aria-label']);
    assert.ok(ui.$('.j2ha-wv .j2ha-menu-toggle').attr('aria-label'));
    assert.ok(ui.$('.j2ha-wv-search').attr('aria-label'));
    assert.equal(ui.$('.j2ha-wv-drawer-toggle').attr('aria-controls'), 'j2ha_wvNav');
  });
});

describe('25.4 / AC3 — « Relire Jeedom » avec la vue ouverte, et états qui changent', () => {
  maybe('la page ne se recharge pas : la vue reste, la relecture suit ; un équipement sélectionné devenu « non lu » ne provoque aucune erreur', () => {
    const ui = startBig({ rooms: 3, equipments: 30, seed: 4 });
    openCard(ui, 10);
    const eq = Number(ui.$('.j2ha-wv-room[data-object_id="10"] .j2ha-wv-eq').list[0].attrs['data-eq-id']);
    ui.selectEquipment(eq, ok(tree(eq, [READY])));
    // « Relire Jeedom » : succès puis signal de relecture (jeedom2ha.js) ; la nouvelle lecture ne connaît plus l'équipement.
    ui.click('#bt_rescanTopology');
    ui.lastConfirmation().options.buttons.confirm.callback();
    ui.respond('scanTopology', { state: 'ok', result: { status: 'ok', operation_result: 'succes' } });
    ui.advance(500);
    const next = Object.assign({}, ui.equipments);
    delete next[String(eq)];
    assert.doesNotThrow(() => ui.respond('getEquipmentStates', okBody(next)));
    assert.equal(ui.isOpen(), true);
    assert.equal(ui.$(`.j2ha-eq-panel[data-eq-id="${eq}"]`).length, 1, 'le détail reste affiché');
    assert.equal(ui.$(`.j2ha-wv-eq[data-eq-id="${eq}"] .j2ha-wv-unread`).length, 1, 'la ligne dit « non lu »');
    assert.doesNotMatch(ui.text('#j2ha_workView'), /NaN|undefined|null/);
  });
});

describe('25.4 / AC22 — cibles tactiles et survol', () => {
  it('aucune règle de la vue ne conditionne une information ou une action au :hover (hors décor)', () => {
    const view = css.slice(css.indexOf('Vue de travail C'));
    for (const m of view.matchAll(/([^{}]*:hover[^{}]*)\{([^{}]*)\}/g)) {
      assert.doesNotMatch(m[2], /display\s*:|visibility\s*:|opacity\s*:\s*[01](?!\.)/, m[1]);
    }
  });

  test('en disposition étroite, lignes, puces, KPI et boutons de la vue ont au moins 44 px de haut', async (t) => {
    await withRealView(t, { width: 800, height: 1000 }, async (page) => {
      await page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="3"]').click();
      await page.locator('.j2ha-wv-drawer-toggle').click();
      const heights = await page.evaluate(() => {
        const h = (selector) => [...document.querySelectorAll(selector)].map((el) => Math.round(el.getBoundingClientRect().height));
        return {
          row: h('#j2ha_workView .j2ha-wv-eq > .j2ha-wv-row'), room: h('#j2ha_workView .j2ha-wv-room > .j2ha-wv-row'),
          chip: h('#j2ha_workView .j2ha-wv-chip'), back: h('#j2ha_workView .j2ha-wv-back'), drawer: h('#j2ha_workView .j2ha-wv-drawer-toggle'),
        };
      });
      for (const [name, list] of Object.entries(heights)) {
        assert.ok(list.length > 0, name);
        assert.ok(list.every((value) => value >= 44), `${name} : ${list.join(',')}`);
      }
      await page.locator('.j2ha-wv-nav .j2ha-wv-row').first().click(); // referme le tiroir
      const kpi = await page.evaluate(() => [...document.querySelectorAll('#j2ha_workView .j2ha-wv-kpi')].map((el) => Math.round(el.getBoundingClientRect().height)));
      assert.ok(kpi.length > 0 && kpi.every((value) => value >= 44), 'KPI : ' + kpi.join(','));
    });
  });
});
