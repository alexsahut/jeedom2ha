// Front v3 — Lot 2 : pièce et fiche équipement, vérifiées en VRAI Chromium (helpers/workview_browser.js), thèmes clair ET
// sombre, à 1280 px et 760 px. Quatre cas : un équipement publié, un équipement bloqué (le nom contredit le type), une
// multiprise à trois entités, un équipement exclu. Plus le module pur `describePreview` (aperçu d'un équipement bloqué).
// Ignoré sans Playwright / jQuery / PHP. Données fictives (CC-48).
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView, read } = require('./helpers/workview_browser');
const { DEMO } = require('./helpers/front_v2_demo_trees');
const { FIXTURE, clone } = require('./helpers/page_b_harness');
const HS = require('../../desktop/js/jeedom2ha_ha_side.js');

const SCENE = {
  objects: [
    { id: 1, name: 'Maison', father_id: null, display: {} },
    { id: 2, name: 'Rez-de-chaussée', father_id: 1, display: {} },
    { id: 9, name: 'Bureau', father_id: 2, display: {} },
  ],
  eqlogics: { 9: [
    { id: 142, name: 'Multiprise Bureau', type: 'zwave' }, { id: 231, name: 'Lampe Chevet', type: 'zwave' },
    { id: 200, name: 'Plafonnier Séjour', type: 'zwave' }, { id: 170, name: 'Radiateur bureau' },
  ] },
  plugin_names: { zwave: 'Z-Wave' },
  doc: 'https://doc.example.test/plugin',
};
const excluded = () => {
  const t = clone(FIXTURE['110'].tree);
  t.jeedom_eq_id = 170;
  t.eq_name = 'Radiateur bureau';
  return t;
};
const TREES = { 142: DEMO.multiprise(true), 231: DEMO.lampePrise(true), 200: DEMO.lumiere(true), 170: excluded() };
const EQUIPMENTS = { 142: TREES[142], 231: TREES[231], 200: TREES[200], 170: Object.assign(clone(FIXTURE['110'].aggregated), { jeedom_eq_id: 170 }) };
const V2_CSS = read('desktop/css/jeedom2ha_v2.css');
const CORE_LIGHT = ':root { --bg-color: 245, 245, 245; --txt-color: #333; }';

function options(eq, theme, width) {
  return { scene: SCENE, equipments: EQUIPMENTS, treeFor: (id) => ({ state: 'ok', result: { status: 'ok', payload: TREES[id] } }),
    hash: `#j2ha-vue=piece:9;eq:${eq}`, width, height: 900, extraCss: V2_CSS + (theme === 'Light' ? CORE_LIGHT : '') };
}

async function ready(page, theme, eq) {
  await page.evaluate((th) => document.body.setAttribute('data-theme', 'core2019_' + th), theme);
  await page.locator(`.j2ha-eq-panel[data-eq-id="${eq}"] .j2ha-cmd-table`).waitFor();
}

const P = (eq) => `.j2ha-eq-panel[data-eq-id="${eq}"]`;

// Mesures communes : en-tête sur deux lignes, ⋯ en bout de ligne 1, aucun débordement horizontal.
async function layout(page, eq) {
  return page.evaluate((sel) => {
    const panel = document.querySelector(sel);
    const r = (el) => el.getBoundingClientRect();
    const head = panel.querySelector('.j2ha-eq-head');
    const line1 = panel.querySelector('.j2ha-eq-line1');
    const toggle = panel.querySelector('.j2ha-eq-controls .j2ha-menu-toggle');
    const meta = panel.querySelector('.j2ha-eq-meta');
    const detail = panel.closest('.j2ha-wv-detail');
    return {
      overflow: document.documentElement.scrollWidth - window.innerWidth,
      detailOverflow: detail.scrollWidth - detail.clientWidth,
      toggleRight: r(toggle).right, line1Right: r(line1).right, toggleIsLast: !toggle.closest('.j2ha-menu-wrap').nextElementSibling
        || toggle.closest('.j2ha-menu-wrap').nextElementSibling.classList.contains('j2ha-publication-error'),
      metaBelow: r(meta).top >= r(line1).bottom - 1, metaInHead: head.contains(meta),
    };
  }, P(eq));
}

for (const theme of ['Light', 'Dark']) {
  for (const width of [1280, 760]) {
    test(`Lot 2 — équipement publié : en-tête sur deux lignes, ⋯ à droite, menu ancré right:0 et visible (232 px) (${theme}, ${width} px)`, async (t) => {
      await withRealView(t, options(200, theme, width), async (page, ctx) => {
        await ready(page, theme, 200);
        const m = await layout(page, 200);
        assert.ok(m.overflow <= 0 && m.detailOverflow <= 1, `aucun défilement horizontal (${m.overflow}, ${m.detailOverflow})`);
        assert.ok(m.toggleIsLast, '⋯ est le dernier contrôle de la ligne 1');
        assert.ok(Math.abs(m.toggleRight - m.line1Right) <= 2, `⋯ aligné à droite (${m.toggleRight} / ${m.line1Right})`);
        assert.ok(m.metaBelow && m.metaInHead, 'ligne 2 sous la ligne 1, dans l’en-tête collant');
        assert.equal((await page.locator(`${P(200)} .j2ha-eq-meta-facts`).innerText()).trim(), 'Z-Wave · 3 commandes');
        // « Toujours » n'est pas grisé sur un équipement publié ; son info-bulle dit ce qu'il fait.
        const always = page.locator(`${P(200)} .j2ha-eq-controls .j2ha-seg-always`);
        assert.equal(await always.isDisabled(), false);
        assert.equal(await always.getAttribute('title'), 'Publier même si le plugin hésite, maintenant ou plus tard');
        // Bloc « Dans Home Assistant » : une ligne (≤ 40 px) avec l'identifiant et le bouton copier.
        const rows = await page.locator(`${P(200)} .j2ha-eq-ha-entity`).evaluateAll((n) => n.map((e) => Math.round(e.getBoundingClientRect().height)));
        assert.equal(rows.length, 1);
        if (width >= 1280) assert.ok(rows[0] <= 40, `ligne d’entité ${rows[0]} px`);
        assert.equal((await page.locator(`${P(200)} .j2ha-eq-entity-id`).innerText()).trim(), 'light.jeedom2ha_eq_200');
        assert.equal(await page.locator(`${P(200)} .j2ha-v2-copy`).getAttribute('aria-label'), 'Copier l’identifiant');
        // Menu ⋯ : ancrage générique right:0, entièrement visible dans le panneau de détail, entrées atteignables.
        await page.locator(`${P(200)} .j2ha-eq-controls .j2ha-menu-toggle`).click();
        const menu = await page.locator(`${P(200)} .j2ha-eq-controls .j2ha-menu-wrap.j2ha-menu-open .j2ha-menu`).evaluate((el) => {
          const r = el.getBoundingClientRect();
          const d = el.closest('.j2ha-wv-detail').getBoundingClientRect();
          const items = [...el.querySelectorAll('.j2ha-menu-item')];
          const hit = (it) => { const b = it.getBoundingClientRect(); const at = document.elementFromPoint(b.left + 12, b.top + b.height / 2); return !!at && (at === it || it.contains(at)); };
          return { right: getComputedStyle(el).right, width: Math.round(r.width), visible: Math.round(Math.min(r.right, d.right) - Math.max(r.left, d.left)),
            items: items.map((i) => i.textContent.trim()), clickable: items.filter(hit).length };
        });
        assert.equal(menu.right, '0px');
        assert.ok(menu.width >= 200, `largeur du menu (${menu.width} px)`);
        assert.equal(menu.visible, menu.width, `menu entièrement visible (${menu.visible}/${menu.width} px)`);
        assert.ok(menu.items.includes('Détails techniques'));
        assert.equal(menu.clickable, menu.items.length);
        assert.deepEqual(ctx.errors, []);
      });
    });

    test(`Lot 2 — équipement bloqué : bande d’une ligne, « Publier en interrupteur ▾ », aperçu, aucune écriture (${theme}, ${width} px)`, async (t) => {
      await withRealView(t, options(231, theme, width), async (page, ctx) => {
        await ready(page, theme, 231);
        const m = await layout(page, 231);
        assert.ok(m.overflow <= 0 && m.detailOverflow <= 1, 'aucun défilement horizontal');
        const band = page.locator(`${P(231)} .j2ha-eq-notices .j2ha-eq-band`);
        assert.equal(await band.count(), 1);
        assert.equal((await band.locator('.j2ha-eq-band-what').innerText()).trim(), 'Nom « lampe » ≠ type « prise »');
        if (width >= 1280) {
          const h = await band.evaluate((el) => el.getBoundingClientRect().height);
          assert.ok(h <= 56, `bande sur une ligne (${h} px)`);
        }
        const info = await band.locator('.j2ha-eq-band-info').getAttribute('title');
        assert.match(info, /le nom dit « lampe », les types Jeedom disent « prise »/);
        assert.equal((await band.locator('.j2ha-v2-publish-anyway').innerText()).trim(), 'Publier en interrupteur');
        // Bloc HA : « Rien », puis l'aperçu de ce que publierait « Toujours ».
        assert.equal((await page.locator(`${P(231)} .j2ha-eq-ha-empty`).innerText()).trim(), 'Rien');
        assert.match(await page.locator(`${P(231)} .j2ha-eq-ha-entity.is-preview`).innerText(), /Interrupteur\s*\(aperçu\)/);
        // La flèche ▾ propose les autres types acceptés par le démon ; un choix ouvre le panneau avec l'aperçu « type + Toujours ».
        await band.locator('.j2ha-eq-split-toggle').click();
        const items = await band.locator('.j2ha-eq-split-item').allInnerTexts();
        assert.ok(items.length >= 1 && items.every((x) => /^Publier en /.test(x.trim())), items.join(' | '));
        assert.ok(!items.some((x) => x.trim() === 'Publier en interrupteur'), 'le type du bouton principal n’est pas répété');
        const visible = await band.locator('.j2ha-eq-split-menu').evaluate((el) => {
          const r = el.getBoundingClientRect(); const d = el.closest('.j2ha-wv-detail').getBoundingClientRect();
          return r.left >= d.left - 1 && r.right <= d.right + 1 && r.width > 0;
        });
        assert.ok(visible, 'menu de la flèche entièrement visible');
        const type = await band.locator('.j2ha-eq-split-item').first().getAttribute('data-type');
        await band.locator('.j2ha-eq-split-item').first().click();
        await page.locator(`${P(231)} .j2ha-v2-type-panel`).waitFor();
        assert.equal(await page.locator(`${P(231)} .j2ha-v2-type-panel input[data-type="${type}"]`).isChecked(), true);
        await page.waitForFunction(() => true);
        const previews = ctx.bodies.filter((b) => /action=previewMappingOverride/.test(b));
        assert.ok(previews.some((b) => b.includes('publicationPolicy=force_publish') && b.includes('haEntityType=' + type)), 'aperçu type + Toujours');
        assert.ok(!ctx.journal.some((e) => ['saveMappingOverride', 'savePublicationOverride', 'executeHaAction'].includes(e.action)), 'aucune écriture');
        assert.deepEqual(ctx.errors, []);
      });
    });

    test(`Lot 2 — multiprise : trois lignes d’entité « Lecture seule » avec identifiant, conseil d’une ligne (${theme}, ${width} px)`, async (t) => {
      await withRealView(t, options(142, theme, width), async (page, ctx) => {
        await ready(page, theme, 142);
        const m = await layout(page, 142);
        assert.ok(m.overflow <= 0 && m.detailOverflow <= 1, 'aucun défilement horizontal');
        assert.equal((await page.locator(`${P(142)} .j2ha-eq-ha-count`).innerText()).trim(), '3 entités');
        const lines = page.locator(`${P(142)} .j2ha-eq-ha-entity`);
        assert.equal(await lines.count(), 3);
        for (let i = 0; i < 3; i += 1) {
          assert.match(await lines.nth(i).innerText(), /Capteur binaire · Sortie \d[\s\S]*Lecture seule[\s\S]*binary_sensor\.jeedom2ha_142_87\d/);
        }
        assert.equal(await page.locator(`${P(142)} .j2ha-eq-ha-toggle`).count(), 0, 'trois entités : rien de replié');
        assert.equal((await page.locator(`${P(142)} .j2ha-eq-advice .j2ha-eq-band-what`).innerText()).trim(), '3 sorties pilotables');
        assert.deepEqual(ctx.errors, []);
      });
    });

    test(`Lot 2 — équipement exclu : « Rien », cause d’exclusion en info-bulle de l’arbre (${theme}, ${width} px)`, async (t) => {
      await withRealView(t, options(170, theme, width), async (page, ctx) => {
        await ready(page, theme, 170);
        const m = await layout(page, 170);
        assert.ok(m.overflow <= 0 && m.detailOverflow <= 1, 'aucun défilement horizontal');
        assert.equal((await page.locator(`${P(170)} .j2ha-eq-publish-badge`).innerText()).trim(), 'Exclu');
        assert.equal((await page.locator(`${P(170)} .j2ha-eq-ha-empty`).innerText()).trim(), 'Rien');
        assert.equal(await page.locator(`${P(170)} .j2ha-eq-ha-entity`).count(), 0);
        // Cet exclu (ancien mécanisme `excluded_eqlogic`) est NON ÉLIGIBLE : « Toujours » n'aurait aucun effet, c'est la seule
        // exception (avec la pièce exclue) où il reste grisé, sa raison en info-bulle.
        const always = page.locator(`${P(170)} .j2ha-eq-controls .j2ha-seg-always`);
        if (TREES[170].eligible === false) {
          assert.equal(await always.isDisabled(), true);
          assert.match(await always.getAttribute('title'), /non éligible/);
        } else {
          assert.equal(await always.isDisabled(), false);
        }
        // L'arbre : icône d'état seule, mot et cause en info-bulle et nom accessible.
        const icon = page.locator('.j2ha-wv-eq[data-eq-id="170"] .j2ha-wv-state-icon');
        assert.equal((await icon.innerText()).trim(), '');
        assert.match(await icon.getAttribute('aria-label'), /^Exclu · /);
        assert.equal(await icon.getAttribute('title'), await icon.getAttribute('aria-label'));
        assert.deepEqual(ctx.errors, []);
      });
    });
  }
}

test('Lot 2 — fil d’Ariane cliquable dans la barre : Maison › Rez-de-chaussée › Bureau ; la pièce ramène au détail de la pièce', async (t) => {
  await withRealView(t, options(231, 'Light', 1280), async (page, ctx) => {
    await ready(page, 'Light', 231);
    const crumb = (await page.locator('.j2ha-wv-bar .j2ha-wv-crumb').innerText()).replace(/\s+/g, ' ').trim();
    assert.equal(crumb, 'Maison › Rez-de-chaussée › Bureau');
    assert.equal(await page.locator('.j2ha-wv-bar').getByText('Page principale').count(), 0);
    await page.locator('.j2ha-wv-crumb .j2ha-wv-crumb-room').click();
    await page.locator('.j2ha-wv-roomhead').waitFor();
    assert.equal(await page.locator('.j2ha-wv-crumb-current').getAttribute('aria-current'), 'page');
    await page.locator('.j2ha-wv-crumb .j2ha-wv-back').click();
    await page.locator('#j2ha_workView').waitFor({ state: 'hidden' });
    assert.deepEqual(ctx.errors, []);
  });
});

test('Lot 2 — recherche : l’arbre de toute la maison est filtré, le volet de droite dit « n résultats »', async (t) => {
  await withRealView(t, options(231, 'Dark', 1280), async (page, ctx) => {
    await ready(page, 'Dark', 231);
    await page.locator('.j2ha-wv-search').fill('multi');
    await page.locator('.j2ha-wv-results-title').waitFor();
    assert.equal((await page.locator('.j2ha-wv-results-title').innerText()).trim(), '1 résultat');
    assert.equal(await page.locator('.j2ha-wv-pane').isVisible(), false);
    await page.locator('.j2ha-wv-results .j2ha-wv-result').first().click();
    await page.locator(`${P(142)} .j2ha-cmd-table`).waitFor();
    assert.equal(await page.locator('.j2ha-wv-results').isVisible(), false);
    assert.deepEqual(ctx.errors, []);
  });
});

test('Lot 2 — describePreview : entités évaluées mais absentes de Home Assistant, jamais un identifiant deviné', () => {
  const blocked = HS.describePreview(DEMO.lampePrise(true));
  assert.equal(blocked.length, 1);
  assert.equal(blocked[0].ha_type, 'switch');
  assert.equal(blocked[0].entity_id, 'switch.jeedom2ha_eq_231');
  assert.equal(blocked[0].controllable, true);
  const fallback = HS.describePreview(DEMO.lampePrise(false));
  assert.equal(fallback.length, 1);
  assert.equal(fallback[0].entity_id, null, 'sans le démon : pas d’identifiant');
  assert.deepEqual(HS.describePreview(DEMO.lumiere(true)), [], 'publié : rien à prévoir');
  assert.deepEqual(HS.describePreview(DEMO.sansType(true)), [], 'sans type : rien');
  assert.deepEqual(HS.describePreview(null), []);
});
