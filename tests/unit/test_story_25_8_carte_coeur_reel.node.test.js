// ARTEFACT — Correctif 25.8 (retour d'Alex sur la box, Jeedom 4.6.1) en VRAI Chromium, AVEC les règles du cœur qui
// s'appliquent à la carte : `.objectDisplayCard i { font-size: 38px !important }`, carte de 130 × 130 px en overflow:hidden.
// Sans elles (harnais nu), l'œil barré et le « ⋯ » à 38 px et le menu rogné par la carte étaient invisibles en test.
// Données fictives (CC-48). Ignoré sans Playwright / jQuery / PHP.
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView } = require('./helpers/workview_browser');
const { SCENE } = require('./helpers/page_b_harness');

// Extrait des règles de desktop.main.css (Jeedom core 4.4+) qui touchent la carte de pièce, recopiées telles quelles.
const CORE_STUB = `
div[class*="ListContainer"] { display: flex !important; flex-wrap: wrap; flex-direction: row; }
div[class*="ListContainer"] > div.cursor { width: 130px !important; font-size: 14px !important; position: relative; }
div[class*="ListContainer"]:not(.batteryListContainer):not(.alertListContainer) div.cursor { margin-bottom: 5px !important; padding: 5px !important; }
.objectDisplayCard i { font-size: 38px !important; }
div[class*="DisplayCard"] { height: 130px !important; overflow: hidden; }
div.objectDisplayCard { height: 130px; min-height: 130px !important; text-align: center; }
div.objectDisplayCard > i { display: inline-block; height: 42px !important; }
`;
const css = CORE_STUB + fs.readFileSync(path.join(__dirname, '..', '..', 'desktop/css/jeedom2ha.css'), 'utf8');
const scene = Object.assign({}, SCENE, { config: { excludedObjects: '3' } });
const CARD = (id) => `#j2ha_roomCards .j2ha-room-card[data-object_id="${id}"]`;

test('correctif 25.8 réel — seule l\'icône de pièce garde 38 px ; « ⋯ » et œil barré à la taille du texte', async (t) => {
  await withRealView(t, { css, scene, width: 1280, height: 800 }, async (page) => {
    const m = await page.evaluate((sel) => {
      const card = document.querySelector(sel);
      const px = (el) => parseFloat(getComputedStyle(el).fontSize);
      return {
        room: px(card.querySelector('.j2ha-room-icon')),
        toggle: px(card.querySelector('.j2ha-room-menu-toggle i')),
        item: px(card.querySelector('.j2ha-room-menu-list i')),
        eye: px(card.querySelector('.j2ha-room-excluded-line i')),
        lineHeight: card.querySelector('.j2ha-room-excluded-line').getBoundingClientRect().height,
      };
    }, CARD(3));
    assert.equal(m.room, 38, 'icône de pièce (cœur)');
    assert.ok(m.toggle <= 16, `« ⋯ » à ${m.toggle}px`);
    assert.ok(m.item <= 14, `icône de l'entrée à ${m.item}px`);
    assert.ok(m.eye <= 14, `œil barré à ${m.eye}px`);
    assert.ok(m.lineHeight <= 34, `ligne « Pièce exclue » haute de ${m.lineHeight}px (au plus deux lignes de texte)`);
    const toggle = await page.locator(`${CARD(3)} .j2ha-room-menu-toggle`).boundingBox();
    assert.ok(toggle.width >= 44 && toggle.height >= 44, 'cible tactile conservée');
  });
});

test('correctif 25.8 réel — menu ouvert entier : ni rogné par la carte, ni hors de la fenêtre (1re carte d\'une rangée comprise)', async (t) => {
  await withRealView(t, { css, scene, width: 1280, height: 800 }, async (page) => {
    for (const id of [2, 4, 5]) {
      await page.locator(`${CARD(id)} .j2ha-room-menu-toggle`).click();
      const r = await page.evaluate((sel) => {
        const ul = document.querySelector(sel + ' .j2ha-room-menu-list');
        const b = ul.getBoundingClientRect();
        // Un point rogné (overflow de la carte) ne renvoie pas l'entrée du menu.
        const hit = (x) => { const el = document.elementFromPoint(x, b.top + b.height / 2); return !!el && ul.contains(el); };
        return { left: b.left, right: b.right, vw: innerWidth, hitLeft: hit(b.left + 4), hitRight: hit(b.right - 4) };
      }, CARD(id));
      assert.ok(r.left >= 0 && r.right <= r.vw, `carte ${id} : menu dans la fenêtre (${r.left}–${r.right})`);
      assert.ok(r.hitLeft && r.hitRight, `carte ${id} : menu visible d'un bord à l'autre`);
      await page.keyboard.press('Escape');
      assert.equal(await page.locator(`${CARD(id)}.j2ha-room-menu-shown`).count(), 0, 'la carte reprend son rognage à la fermeture');
    }
  });
});
