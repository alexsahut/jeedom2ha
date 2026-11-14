// Front v3 — Lot 0 : correctifs vérifiés en VRAI Chromium (helpers/workview_browser.js), thèmes clair ET sombre.
//  (1) En-tête collant de la fiche opaque : `--bg-color` du cœur est un TRIPLET (« 25, 25, 25 »), pas une couleur ; la
//      règle `var(--bg-color, …)` donnait un fond transparent et le texte défilait dessous (panneau « Corriger le type »).
//  (2) Menu ⋯ de l'équipement rogné : ancré à droite sur un bouton placé à gauche, il sortait du panneau de détail
//      (overflow-x: hidden) ; 35 px visibles sur 232.
//  (3) Guide « fail-closed » : sans signal de Home Assistant, l'étape 2 est « À vérifier » avec son bouton, jamais « Fait ».
// Chaque test échoue sur le code d'avant le correctif. Ignoré sans Playwright / jQuery / PHP. Données fictives (CC-48).
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView, read } = require('./helpers/workview_browser');
const { DEMO } = require('./helpers/front_v2_demo_trees');

const SCENE = {
  objects: [{ id: 1, name: 'Maison', father_id: null, display: {} }, { id: 9, name: 'Bureau', father_id: 1, display: {} }],
  eqlogics: { 9: [{ id: 231, name: 'Lampe Chevet' }, { id: 200, name: 'Plafonnier Séjour' }] },
  doc: 'https://doc.example.test/plugin',
};
const TREES = { 231: DEMO.lampePrise(true), 200: DEMO.lumiere(true) };
const P = '.j2ha-eq-panel[data-eq-id="231"]';
// Thème clair du cœur : --bg-color en triplet, comme le relevé sombre de core_css_reel.js (« 25, 25, 25 »).
const CORE_LIGHT = ':root { --bg-color: 245, 245, 245; --txt-color: #333; }';

// La page charge jeedom2ha.css PUIS jeedom2ha_v2.css (jeedom2ha.php) ; withRealView ne charge le second que par extraCss.
const V2_CSS = read('desktop/css/jeedom2ha_v2.css');

function options(extra, width) {
  const e = Object.assign({}, extra || {});
  e.extraCss = V2_CSS + (e.extraCss || '');
  return Object.assign({ scene: SCENE, equipments: { 231: TREES[231], 200: TREES[200] },
    treeFor: (id) => ({ state: 'ok', result: { status: 'ok', payload: TREES[id] } }),
    hash: '#j2ha-vue=piece:9;eq:231', width: width || 1280, height: 760 }, e);
}

async function setTheme(page, theme) {
  await page.evaluate((th) => document.body.setAttribute('data-theme', 'core2019_' + th), theme);
}

const opaque = (css) => /^rgb\(\d+, \d+, \d+\)$/.test(css);

const CASES = [
  // Cœur Jeedom 4.6 : --bg-color défini (triplet) → la couleur de la page du cœur.
  { name: 'cœur 4.6, clair', theme: 'Light', extra: { extraCss: CORE_LIGHT }, expected: 'rgb(245, 245, 245)' },
  { name: 'cœur 4.6, sombre', theme: 'Dark', extra: {}, expected: 'rgb(25, 25, 25)' },
  // Jeedom 4.4 : --bg-color absent → repli --j2ha-page-rgb du thème.
  { name: 'sans --bg-color, clair', theme: 'Light', extra: { coreCss: false }, expected: 'rgb(255, 255, 255)' },
  { name: 'sans --bg-color, sombre', theme: 'Dark', extra: { coreCss: false }, expected: 'rgb(42, 42, 42)' },
];

for (const c of CASES) {
  test(`Lot 0 (1) — en-tête collant de la fiche opaque (${c.name})`, async (t) => {
    await withRealView(t, options(c.extra), async (page, ctx) => {
      await setTheme(page, c.theme);
      await page.locator(`${P} .j2ha-cmd-table`).waitFor();
      const bg = await page.locator(`${P} .j2ha-eq-head`).evaluate((el) => getComputedStyle(el).backgroundColor);
      assert.ok(opaque(bg), `fond calculé de .j2ha-eq-head opaque (${bg})`);
      assert.equal(bg, c.expected);
      assert.deepEqual(ctx.errors, []);
    });
  });
}

for (const [theme, width] of [['Light', 1280], ['Dark', 1280], ['Light', 980], ['Dark', 1440]]) {
  test(`Lot 0 (2) — menu ⋯ de l'équipement entièrement visible ; menu de la barre d'état toujours ancré à droite (${theme}, ${width} px)`, async (t) => {
    await withRealView(t, options(theme === 'Light' ? { extraCss: CORE_LIGHT } : {}, width), async (page, ctx) => {
      await setTheme(page, theme);
      await page.locator(`${P} .j2ha-cmd-table`).waitFor();
      const toggle = page.locator(`${P} .j2ha-eq-controls .j2ha-menu-toggle`).first();
      await toggle.click();
      const m = await page.locator(`${P} .j2ha-eq-controls .j2ha-menu-wrap.j2ha-menu-open .j2ha-menu`).first().evaluate((menu) => {
        const r = menu.getBoundingClientRect();
        const d = menu.closest('.j2ha-wv-detail').getBoundingClientRect();
        const items = [...menu.querySelectorAll('.j2ha-menu-item')];
        const hit = (el) => {
          const b = el.getBoundingClientRect();
          const at = document.elementFromPoint(b.left + 12, b.top + b.height / 2);
          return !!at && (at === el || el.contains(at));
        };
        return { width: Math.round(r.width), visible: Math.round(Math.min(r.right, d.right) - Math.max(r.left, d.left)),
          items: items.length, clickable: items.filter(hit).length };
      });
      assert.ok(m.width >= 200, `largeur du menu (${m.width} px)`);
      assert.equal(m.visible, m.width, `menu entièrement visible dans le panneau (${m.visible}/${m.width} px)`);
      assert.ok(m.items >= 3);
      assert.equal(m.clickable, m.items, 'chaque entrée est atteignable (pas sous un autre élément)');
      // La règle générique n'est pas touchée : le menu de la barre d'état reste ancré à droite.
      const right = await page.locator('#j2ha_moreMenu .j2ha-menu').first().evaluate((el) => getComputedStyle(el).right);
      assert.equal(right, '0px');
      assert.deepEqual(ctx.errors, []);
    });
  });
}

for (const theme of ['Light', 'Dark']) {
  test(`Lot 0 (3) — guide rouvert, Home Assistant non confirmé : étape 2 « À vérifier » avec son bouton (${theme})`, async (t) => {
    await withRealView(t, options(theme === 'Light' ? { extraCss: CORE_LIGHT } : {}), async (page, ctx) => {
      await setTheme(page, theme);
      // Banc : démon et broker en marche, aucun champ `ha` (pas de signal de Home Assistant), équipements publiés.
      await page.evaluate(() => { window.localStorage.clear(); window.jQuery('#bt_j2haOpenGuide').trigger('click'); });
      await page.locator('#j2ha_v2_guide .j2ha-v2-step').first().waitFor();
      const labels = () => page.$$eval('#j2ha_v2_guide .j2ha-v2-step .j2ha-v2-lbl', (n) => n.map((e) => e.textContent.trim()));
      assert.deepEqual(await labels(), ['Fait', 'À vérifier', 'Fait', 'Fait']);
      const text = await page.locator('#j2ha_v2_guide').innerText();
      assert.doesNotMatch(text, /Réputée|À faire/);
      const verify = page.locator('#j2ha_v2_guide .j2ha-v2-step[data-step="ha"] .j2ha-v2-guide-verify');
      assert.equal(await verify.count(), 1);
      assert.ok(await verify.isVisible());
      assert.ok(await verify.isEnabled());
      await verify.click();
      assert.deepEqual(await labels(), ['Fait', 'Fait (vu par vous)', 'Fait', 'Fait']);
      assert.deepEqual(ctx.errors, []);
    });
  });
}

// Lot 0 (4) : aucune autre variable « triplet » du cœur mal lue. Dans le cœur Jeedom, --bg-color et --bg-modal-color sont
// des triplets R, G, B (core_css_reel.js : « --bg-color: 25, 25, 25 ») ; --txt-color, --link-color, --logo-primary-color sont
// des couleurs complètes. Un triplet ne se lit que dans rgb()/rgba(), sinon la déclaration est invalide à l'exécution.
test('Lot 0 (4) — les variables triplets du cœur ne sont lues que dans rgb()/rgba()', () => {
  for (const file of ['desktop/css/jeedom2ha.css', 'desktop/css/jeedom2ha_v2.css']) {
    const css = read(file).replace(/\/\*[\s\S]*?\*\//g, '');
    const uses = [...css.matchAll(/(.{0,5})var\(--(bg-color|bg-modal-color)\b/g)];
    for (const m of uses) assert.match(m[1], /rgba?\($/, `${file} : var(--${m[2]}) hors de rgb() (« ${m[0]} »)`);
  }
  assert.ok(/rgb\(var\(--bg-color, var\(--j2ha-page-rgb\)\)\)/.test(read('desktop/css/jeedom2ha.css')));
});
