// ARTEFACT — Audit UX du 2026-10-19 (captures de la box, Jeedom 4.6.1, avant la recette 25.5). En VRAI Chromium, AVEC les
// règles du cœur Jeedom qui touchent la surface (helpers/core_css_reel.js : carte 130 × 130 px en overflow:hidden, `.btn` à fond
// de bouton, cases à cocher de Bootstrap). Chaque test échoue sur le CSS d'avant le correctif. Données fictives (CC-48).
// Ignoré sans Playwright / jQuery / PHP.
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView, treeBody, JQUERY, phpAvailable, gate } = require('./helpers/workview_browser');
const { equipmentsFor, renderPhp } = require('./helpers/page_b_harness');
const H = require('./helpers/core_css_reel');

const CARD = (id) => `#j2ha_roomCards .j2ha-room-card[data-object_id="${id}"]`;
const EXCLUDED = ['501', '503', '505'];

function sceneOptions(width) {
  if (!phpAvailable) return null;
  const rooms = renderPhp(H.UX_SCENE).vars.j2haRoomsTree;
  const equipments = H.uxEquipments(rooms, equipmentsFor);
  const treeFor = (id) => (EXCLUDED.includes(String(id))
    ? { state: 'ok', result: { status: 'ok', payload: Object.assign({ eq_name: 'Eq', mapped: false, eligible: true }, equipments[String(id)]) } }
    : treeBody(id));
  return { css: H.pageCss(), scene: H.UX_SCENE, equipments, treeFor, width, height: 800 };
}

for (const width of [980, 1440]) {
  // Garde levée (front v3, Lot 1) : la tuile garde une hauteur fixe de 72 px ; un nom long tient sur UNE ligne, coupé par une
  // ellipse, le nom entier en info-bulle. Le reste de l'audit (liseré et repères entiers, liserés alignés) est inchangé.
  test(`audit UX réel ${width} px — tuile au nom long : une ligne (ellipse au besoin), liseré et repères entiers, liserés alignés sur la rangée`, async (t) => {
    const options = sceneOptions(width);
    if (!options) { t.skip('PHP indisponible'); return; }
    await withRealView(t, options, async (page) => {
      const m = await page.evaluate(([long, short]) => {
        const box = (el) => el.getBoundingClientRect();
        const card = (sel) => document.querySelector(sel);
        const visible = (el) => {
          const b = box(el);
          const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
          return !!hit && (hit === el || el.contains(hit) || hit.contains(el));
        };
        const gaugeOf = (sel) => card(sel).querySelector('.j2ha-gauge');
        return {
          nameHeight: box(card(long).querySelector('.name')).height,
          nameEllipsis: getComputedStyle(card(long).querySelector('.name')).textOverflow,
          nameTitle: card(long).querySelector('.name').getAttribute('title'),
          nameText: card(long).querySelector('.name').textContent,
          gaugeInside: box(gaugeOf(long)).bottom <= box(card(long)).bottom,
          gaugeVisible: visible(gaugeOf(long)),
          gaugeTops: [box(gaugeOf(long)).top, box(gaugeOf(short)).top],
          marks: [...document.querySelectorAll('#j2ha_roomCards .j2ha-room-card .j2ha-room-marks .j2ha-mark')].map((el) => ({
            text: el.textContent, height: box(el).height, inside: box(el).bottom <= box(el.closest('.j2ha-room-card')).bottom })),
        };
      }, [CARD(3), CARD(4)]);
      assert.ok(m.nameHeight <= 20, `le nom long tient sur une ligne (${m.nameHeight}px)`);
      assert.equal(m.nameEllipsis, 'ellipsis', 'un nom trop long est coupé par une ellipse');
      assert.equal(m.nameTitle, m.nameText, 'le nom entier en info-bulle');
      assert.ok(m.gaugeInside && m.gaugeVisible, 'la jauge de la carte au nom long est dans la carte et visible');
      assert.ok(Math.abs(m.gaugeTops[0] - m.gaugeTops[1]) <= 1, `jauges de la rangée alignées (${m.gaugeTops.join(' / ')})`);
      assert.ok(m.marks.length > 0, 'la scène a des repères');
      for (const mark of m.marks) {
        assert.ok(mark.inside, `repère « ${mark.text} » dans la carte`);
        assert.ok(mark.height <= 20, `repère « ${mark.text} » sur une seule ligne (${mark.height}px)`);
      }
    });
  });

  // Garde levée (front v3, Lot 2) : l'arbre n'affiche plus que l'icône d'état ; la cause d'exclusion et « désactivé dans
  // Jeedom » sont ENTIÈRES dans l'info-bulle et le nom accessible de l'icône. Le nom de l'équipement garde toute la ligne.
  test(`audit UX réel ${width} px — vue C : icône d'état, cause d'exclusion et « désactivé dans Jeedom » entières en info-bulle`, async (t) => {
    const options = sceneOptions(width);
    if (!options) { t.skip('PHP indisponible'); return; }
    await withRealView(t, options, async (page) => {
      await page.locator(`${CARD(5)}`).click();
      await page.locator('.j2ha-wv-eq[data-eq-id="501"]').waitFor();
      const m = await page.evaluate(() => {
        const lineOf = (eqId) => {
          const row = document.querySelector(`.j2ha-wv-eq[data-eq-id="${eqId}"] > .j2ha-wv-row`);
          const icon = row.querySelector('.j2ha-wv-state-icon');
          const name = row.querySelector('.j2ha-wv-name');
          return { label: icon.getAttribute('aria-label'), title: icon.getAttribute('title'), text: icon.textContent.trim(),
            iconWidth: icon.getBoundingClientRect().width, rowHeight: row.getBoundingClientRect().height,
            nameTruncated: name.scrollWidth > name.clientWidth + 1 };
        };
        return { nav: document.querySelector('.j2ha-wv-nav').getBoundingClientRect().width, cause: [lineOf(501), lineOf(505)], off: lineOf(503) };
      });
      for (const line of m.cause.concat([m.off])) {
        assert.equal(line.text, '', 'aucun mot affiché');
        assert.equal(line.title, line.label);
        assert.ok(line.iconWidth <= 24, `icône seule (${line.iconWidth}px)`);
        assert.ok(line.rowHeight <= 44, `ligne d'une hauteur (${line.rowHeight}px)`);
      }
      assert.match(m.cause[1].label, /^Exclu · par le plugin Bêta Sécurité Maison$/);
      assert.match(m.off.label, /désactivé dans Jeedom/);
      if (width >= 1440) assert.ok(m.nav >= 400, `arbre élargi en grand écran (${m.nav}px)`);
      // Disposition large : le bouton du tiroir « Pièces » reste masqué (aucune règle ajoutée ne le réaffiche).
      assert.equal(await page.locator('.j2ha-wv-drawer-toggle').isVisible(), false, 'tiroir masqué en disposition large');
    });
  });
}

test('audit UX réel — fil d\'Ariane : la pièce cliquable est un lien (pas de fond de bouton du cœur), clavier conservé', async (t) => {
  const options = sceneOptions(1440);
  if (!options) { t.skip('PHP indisponible'); return; }
  await withRealView(t, options, async (page) => {
    await page.locator(`${CARD(5)}`).click();
    await page.locator('.j2ha-wv-eq[data-eq-id="502"] > .j2ha-wv-row').click();
    const link = page.locator('.j2ha-wv-crumb .j2ha-wv-crumb-room');
    await link.waitFor();
    const s = await link.evaluate((el) => ({ tag: el.tagName, btn: el.classList.contains('btn'), bg: getComputedStyle(el).backgroundColor, deco: getComputedStyle(el).textDecorationLine }));
    assert.equal(s.tag, 'BUTTON', 'reste un bouton natif (clavier, lecteur d\'écran)');
    assert.equal(s.btn, false, 'aucune classe .btn du cœur');
    assert.equal(s.bg, 'rgba(0, 0, 0, 0)', 'aucun fond');
    assert.equal(s.deco, 'underline', 'se lit comme un lien');
    await link.focus();
    await page.keyboard.press('Enter');
    await page.locator('.j2ha-wv-roomhead').waitFor();
  });
});

// Garde levée (front v3, Lot 3) : la liste des 42 plugins quitte la configuration (une seule source : le panneau « Choisir ce qui
// est publié » de la page du plugin). Même scène de 42 plugins : la page tient sans défilement interne ni liste, aucune phrase.
test('audit UX réel — configuration (42 plugins) : plus de liste ni de phrase, un lien vers « Choisir ce qui est publié »', async (t) => {
  if (!phpAvailable || !JQUERY) { t.skip('PHP ou jQuery indisponible'); return; }
  let playwright;
  try {
    const { loadPlaywright } = await import(gate('lib', 'playwright.mjs'));
    playwright = loadPlaywright();
  } catch { t.skip('Playwright indisponible'); return; }
  const html = H.renderConfiguration(H.configFixture()).replace(/\{\{([^}]*)\}\}/g, '$1');
  const browser = await playwright.chromium.launch({ headless: true });
  try {
    const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
    await page.route('http://cfg.test/**', async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname === '/') {
        await route.fulfill({ contentType: 'text/html', body: `<!doctype html><html><head><meta charset="utf-8"><style>${H.CORE_CSS}.col-md-6{width:50%;float:left}</style>`
          + `<script src="/jq.js"></script></head><body><div id="div_plugin_configuration">${html}</div></body></html>` });
        return;
      }
      if (url.pathname === '/jq.js') { await route.fulfill({ contentType: 'application/javascript', body: fs.readFileSync(JQUERY, 'utf8') }); return; }
      await route.fulfill({ contentType: 'application/json', body: '{"state":"ok","result":{}}' });
    });
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto('http://cfg.test/');
    const m = await page.evaluate(() => ({
      lists: document.querySelectorAll('#div_excludedPluginsList, input.j2ha-excluded-plugin').length,
      helps: document.querySelectorAll('.help-block:not(#span_mqttPasswordStatus)').length,
      link: (document.querySelector('#lnk_j2haChoosePublished') || {}).textContent || '',
      hscroll: document.documentElement.scrollWidth > window.innerWidth + 1,
    }));
    assert.equal(m.lists, 0);
    assert.equal(m.helps, 0, 'aucune phrase d’aide permanente');
    assert.match(m.link, /Choisir ce qui est publié/);
    assert.equal(m.hscroll, false, 'aucun défilement horizontal');
    assert.deepEqual(errors, []);
  } finally {
    await browser.close();
  }
});

test('audit UX — le CSS ajouté respecte la palette (aucune couleur littérale) et la portée du plugin', () => {
  const css = fs.readFileSync(path.join(__dirname, '..', '..', 'desktop/css/jeedom2ha.css'), 'utf8');
  const start = css.indexOf('Audit UX du 2026-10-19');
  const block = css.slice(css.indexOf('*/', start) + 2);
  assert.ok(block.length > 100, 'bloc de l\'audit présent');
  assert.doesNotMatch(block.replace(/\/\*[\s\S]*?\*\//g, ''), /#[0-9a-f]{3,8}\b|rgba?\(/i);
  for (const selector of block.replace(/\/\*[\s\S]*?\*\//g, '').match(/[^{}]+(?=\{)/g).map((s) => s.trim()).filter((s) => !s.startsWith('@'))) {
    for (const one of selector.split(',').map((s) => s.trim())) assert.match(one, /^\.j2ha-(wv|room-groups)[\s.-]/, one);
  }
});
