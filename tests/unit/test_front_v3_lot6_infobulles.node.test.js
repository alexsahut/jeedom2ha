// Front v3 — Lot 6 : info-bulles ⓘ qui fonctionnent (desktop/js/jeedom2ha_infotip.js), vérifiées en VRAI Chromium
// (helpers/workview_browser.js et la page de configuration rendue par PHP), clair ET sombre, 1280 et 760 px :
//  - un clic (ou un toucher) ouvre une bulle posée sur body qui affiche le bon texte ; second clic, Échap, clic ailleurs la ferment ;
//  - clavier : Entrée / Espace ouvrent, Échap ferme et rend le focus ; une seule bulle à la fois ; survol de 300 ms ;
//  - la bulle reste dans le viewport (760 px, bord d'écran) et passe au-dessus de la fenêtre « Corriger le type » ;
//  - inventaire : plus aucune `fa-info-circle` hors du composant `button.j2ha-info` (sources et rendu).
// `J2HA_LOT6_SHOTS=<dossier>` enregistre des captures d'une bulle ouverte. Ignoré sans Playwright / jQuery / PHP. Données fictives.
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { withRealView, read, gate, JQUERY } = require('./helpers/workview_browser');
const { DEMO } = require('./helpers/front_v2_demo_trees');
const { phpAvailable } = require('./helpers/page_b_harness');
const T = require('../../desktop/js/jeedom2ha_infotip.js');

const ROOT = path.join(__dirname, '..', '..');
const SHOTS = process.env.J2HA_LOT6_SHOTS || '';
const CORE_LIGHT = ':root { --bg-color: 245, 245, 245; --txt-color: #333; }';
const slug = (title) => title.toLowerCase().replace(/[^\p{L}\p{N}\s-]/gu, '').replace(/\s/g, '-');
const DOC_ANCHORS = read('docs/fr_FR/index.md').split('\n').filter((l) => /^#{1,6} /.test(l)).map((l) => slug(l.replace(/^#+ /, '')));

const SCENE = {
  objects: [{ id: 1, name: 'Maison', father_id: null, display: {} }, { id: 9, name: 'Bureau', father_id: 1, display: {} }],
  eqlogics: { 9: [{ id: 231, name: 'Lampe Chevet' }, { id: 200, name: 'Plafonnier Séjour' }] },
  doc: 'https://doc.example.test/plugin',
};
function lampe() {
  const t = DEMO.lampePrise(true);
  t.commands.forEach((c) => { c.override_types_allowed = ['light', 'switch']; });
  return t;
}
const TREES = { 231: lampe(), 200: DEMO.lumiere(true) };
// Aperçu du démon : la lampe passe en lumière, son identifiant change (« ID modifié » + ⓘ dans la fenêtre).
const PREVIEW = { state: 'ok', result: { status: 'ok', payload: {
  jeedom_eq_id: 231, mapped: true, covered: true, auto: lampe().equipment_decision,
  overridden: { ha_entity_type: 'light', projection_validity: { is_valid: true, reason_code: null, missing_capabilities: [], missing_fields: [] }, should_publish: true, publication_reason: 'sure', confidence: 'sure', reason_code: 'sure_mapping' },
  entities_before: [{ ha_entity_type: 'switch', ha_unique_id: 'jeedom2ha_eq_231', ha_name: 'Lampe Chevet', ha_default_entity_id: 'switch.jeedom2ha_eq_231', ha_controllable: true, ha_capabilities: ['on_off'], will_publish: true, reason: 'sure' }],
  entities_after: [{ ha_entity_type: 'light', ha_unique_id: 'jeedom2ha_eq_231', ha_name: 'Lampe Chevet', ha_default_entity_id: 'light.jeedom2ha_eq_231', ha_controllable: true, ha_capabilities: ['on_off', 'read'], will_publish: true, reason: 'sure' }],
  entity_id_changes: [{ from: 'switch.jeedom2ha_eq_231', to: 'light.jeedom2ha_eq_231' }],
} } };

function options(theme, width, extra) {
  return Object.assign({ scene: SCENE, equipments: { 231: TREES[231], 200: TREES[200] },
    treeFor: (id) => ({ state: 'ok', result: { status: 'ok', payload: TREES[id] } }),
    respond: (action) => (action === 'previewMappingOverride' ? PREVIEW : undefined),
    width, height: 760 }, theme === 'Light' ? { extraCss: CORE_LIGHT } : {}, extra || {});
}

async function setTheme(page, theme) {
  await page.evaluate((th) => document.body.setAttribute('data-theme', 'core2019_' + th), theme);
}

/** État de la (seule) bulle : texte, lien, position par rapport au viewport, élément visible en son centre, couleurs. */
function popState(page) {
  return page.evaluate(() => {
    const pops = [...document.querySelectorAll('.j2ha-info-pop')];
    if (!pops.length) return { count: 0 };
    const pop = pops[0];
    const r = pop.getBoundingClientRect();
    const at = document.elementFromPoint(r.left + r.width / 2, r.top + Math.min(r.height / 2, 10));
    const trigger = document.querySelector('[aria-describedby="' + pop.id + '"]');
    const cs = getComputedStyle(pop);
    const more = pop.querySelector('a');
    return {
      count: pops.length, parentIsBody: pop.parentElement === document.body,
      text: pop.querySelector('.j2ha-info-pop-text').textContent, more: more ? more.getAttribute('href') : null,
      left: r.left, right: r.right, top: r.top, bottom: r.bottom, vw: document.documentElement.clientWidth, vh: document.documentElement.clientHeight,
      onTop: !!at && pop.contains(at), role: pop.getAttribute('role'),
      expanded: trigger ? trigger.getAttribute('aria-expanded') : null, triggerId: trigger ? trigger.id : null,
      bg: cs.backgroundColor, color: cs.color,
    };
  });
}

function assertInViewport(s, label) {
  assert.ok(s.left >= 0 && s.top >= 0 && s.right <= s.vw && s.bottom <= s.vh, `${label} : bulle dans le viewport (${Math.round(s.left)},${Math.round(s.top)} → ${Math.round(s.right)},${Math.round(s.bottom)} / ${s.vw}×${s.vh})`);
}

async function shot(page, name) {
  if (!SHOTS) return;
  fs.mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, name + '.png') });
}

// --- Module pur ---------------------------------------------------------------------------------------------------------

test('Lot 6 — composant : ⓘ = vrai <button>, nom accessible « Aide : … », texte en data-j2ha-tip, ancre de doc existante', () => {
  const calls = [];
  const fake$ = (html) => {
    const el = { html, attrs: {}, classes: [], children: [] };
    const api = {
      el,
      attr(k, v) { if (v === undefined) return el.attrs[k]; el.attrs[k] = v; calls.push(k); return api; },
      addClass(c) { el.classes.push(c); return api; },
      append(x) { el.children.push(x); return api; },
    };
    return api;
  };
  const b = T.button(fake$, 'Texte d’aide', { doc: 'la-barre-détat', cls: 'x-y' });
  assert.match(b.el.html, /^<button type="button" class="j2ha-info j2ha-v3-info">/);
  assert.equal(b.el.attrs['data-j2ha-tip'], 'Texte d’aide');
  assert.equal(b.el.attrs['aria-label'], '{{Aide}} : Texte d’aide');
  assert.equal(b.el.attrs['aria-expanded'], 'false');
  assert.equal(b.el.attrs.title, undefined, 'pas de title : le cœur ne l’intercepte pas, le navigateur ne double pas la bulle');
  assert.ok(b.el.classes.includes('x-y'));
  assert.equal(T.HOVER_OPEN_MS, 300);
  // Toute ancre « En savoir plus » citée par le code existe dans docs/fr_FR/index.md.
  const sources = ['desktop/js/jeedom2ha_exclusions.js', 'desktop/js/jeedom2ha_guide.js', 'desktop/js/jeedom2ha_mapping_surface.js',
    'desktop/js/jeedom2ha_overview.js', 'desktop/php/jeedom2ha.php', 'plugin_info/configuration.php'].map(read).join('\n');
  const cited = new Set([...sources.matchAll(/(?:data-j2ha-doc="|doc: ')([^"']+)/g)].map((m) => m[1]));
  for (const m of read('desktop/js/jeedom2ha_guide.js').matchAll(/var doc = [^;]*\? '([a-zà-ü-]+)' : '([a-zà-ü-]+)'/g)) { cited.add(m[1]); cited.add(m[2]); }
  for (const m of sources.matchAll(/typeInfo\(\w+, '([a-zà-ü-]+)'\)/g)) cited.add(m[1]);
  cited.add('corriger-le-type');
  assert.ok(cited.size >= 6, [...cited].join(', '));
  for (const anchor of cited) assert.ok(DOC_ANCHORS.includes(anchor), `ancre « ${anchor} » absente de index.md`);
});

// --- Inventaire ---------------------------------------------------------------------------------------------------------

test('Lot 6 — inventaire des sources : aucune fa-info-circle hors du composant button.j2ha-info', () => {
  const files = [...fs.readdirSync(path.join(ROOT, 'desktop/js')).map((f) => 'desktop/js/' + f),
    ...fs.readdirSync(path.join(ROOT, 'desktop/php')).map((f) => 'desktop/php/' + f), 'plugin_info/configuration.php'];
  const offenders = [];
  for (const file of files) {
    if (file === 'desktop/js/jeedom2ha_infotip.js') continue;
    read(file).split('\n').forEach((line, i) => {
      if (!line.includes('fa-info-circle')) return;
      if (/^\s*(\/\/|\*|\/\*)/.test(line)) return;
      // Seule forme admise hors du composant : le bouton j2ha-info écrit en dur dans un gabarit PHP.
      if (/\.php$/.test(file) && /<button type="button" class="j2ha-info j2ha-v3-info"[^>]*data-j2ha-tip="[^"]+"[^>]*aria-label="\{\{Aide\}\} : [^"]+"[^>]*><i class="fas fa-info-circle" aria-hidden="true"><\/i><\/button>/.test(line)) return;
      offenders.push(`${file}:${i + 1}`);
    });
    // Plus d'aide confiée aux tooltips du cœur (classe `tooltips`) ni d'icône d'aide « ? » en dur dans un gabarit.
    if (/\.php$/.test(file) && file !== 'desktop/php/jeedom2ha.php') {
      assert.doesNotMatch(read(file), /class="[^"]*\btooltips\b/, file);
      assert.doesNotMatch(read(file), /fa-question-circle/, file);
    }
  }
  assert.deepEqual(offenders, [], 'fa-info-circle hors composant');
});

for (const theme of ['Light', 'Dark']) {
  for (const width of [1280, 760]) {
    const tag = `${theme}, ${width} px`;

    test(`Lot 6 réel — page maison : pastilles de la barre d'état au clic, second clic, clic ailleurs, une seule bulle (${tag})`, async (t) => {
      await withRealView(t, options(theme, width), async (page, ctx) => {
        await setTheme(page, theme);
        await page.waitForFunction(() => /Démon : /.test(document.querySelector('#span_healthBridge').getAttribute('title') || ''));
        assert.equal((await popState(page)).count, 0);
        await page.locator('#span_healthBridge').click();
        let s = await popState(page);
        assert.equal(s.count, 1);
        assert.match(s.text, /^Démon : /);
        assert.ok(s.parentIsBody && s.onTop, 'posée sur body, visible');
        assert.equal(s.role, 'tooltip');
        assert.equal(s.expanded, 'true');
        assert.equal(s.more, 'https://doc.example.test/plugin#la-barre-détat');
        assert.notEqual(s.bg, 'rgba(0, 0, 0, 0)', 'fond opaque');
        assert.notEqual(s.bg, s.color, 'texte lisible');
        assertInViewport(s, 'Démon');
        // Le `title` est mis de côté pendant l'ouverture (pas d'info-bulle du navigateur en double), puis rendu.
        assert.equal(await page.locator('#span_healthBridge').getAttribute('title'), null);
        await shot(page, `maison-${theme}-${width}`);
        // Second clic : fermée.
        await page.locator('#span_healthBridge').click();
        assert.equal((await popState(page)).count, 0);
        assert.match(await page.locator('#span_healthBridge').getAttribute('title'), /^Démon : /);
        assert.equal(await page.locator('#span_healthBridge').getAttribute('aria-expanded'), 'false');
        // Une seule bulle : ouvrir MQTT ferme Démon.
        await page.locator('#span_healthBridge').click();
        await page.locator('#span_healthMqtt').click();
        s = await popState(page);
        assert.equal(s.count, 1);
        assert.match(s.text, /^MQTT : /);
        assert.equal(await page.locator('#span_healthBridge').getAttribute('aria-expanded'), 'false');
        // Clic ailleurs : fermée.
        await page.locator('#j2ha_houseNumber').click();
        assert.equal((await popState(page)).count, 0);
        // Une info-bulle de pastille ne déclenche pas l'action d'un parent, et n'écrit rien.
        assert.ok(!ctx.journal.some((e) => ['scanTopology', 'executeHaAction', 'saveFilteringConfig'].includes(e.action)));
        assert.deepEqual(ctx.errors, []);
      });
    });

    test(`Lot 6 réel — clavier et survol : Entrée / Espace ouvrent, Échap ferme et rend le focus ; 300 ms de survol (${tag})`, async (t) => {
      await withRealView(t, options(theme, width, { hash: '#j2ha-vue=piece:9;eq:231' }), async (page, ctx) => {
        await setTheme(page, theme);
        const P = '.j2ha-eq-panel[data-eq-id="231"]';
        await page.locator(`${P} .j2ha-cmd-table`).waitFor();
        // Pastille (role="button") : Tab l'atteint (tabindex 0), Entrée ouvre, Échap ferme et rend le focus, Espace rouvre.
        await page.locator('#span_healthMqtt').focus();
        await page.keyboard.press('Enter');
        assert.match((await popState(page)).text, /^MQTT : /);
        await page.keyboard.press('Escape');
        assert.equal((await popState(page)).count, 0);
        assert.equal(await page.evaluate(() => document.activeElement.id), 'span_healthMqtt');
        await page.keyboard.press(' ');
        assert.match((await popState(page)).text, /^MQTT : /);
        await page.keyboard.press('Escape');
        // ⓘ de la bande de cause : un vrai bouton, Tab l'atteint depuis l'élément qui le précède.
        const info = page.locator(`${P} .j2ha-eq-band button.j2ha-info`);
        assert.match(await info.getAttribute('aria-label'), /^Aide : Non publié : le nom dit « lampe »/);
        await info.evaluate((el) => { const prev = el.previousElementSibling; prev.setAttribute('tabindex', '-1'); prev.focus(); });
        await page.keyboard.press('Tab');
        assert.equal(await page.evaluate(() => document.activeElement.classList.contains('j2ha-info')), true, 'Tab atteint ⓘ');
        await page.keyboard.press('Enter');
        let s = await popState(page);
        assert.match(s.text, /le nom dit « lampe », les types Jeedom disent « prise »/);
        assertInViewport(s, 'bande');
        await shot(page, `fiche-${theme}-${width}`);
        // Échap ferme la bulle SEULEMENT (la fiche reste ouverte) et rend le focus à ⓘ.
        await page.keyboard.press('Escape');
        assert.equal((await popState(page)).count, 0);
        assert.equal(await page.evaluate(() => document.activeElement.classList.contains('j2ha-info')), true);
        assert.equal(await page.locator(P).count(), 1, 'la fiche reste ouverte');
        // Survol à la souris : ouverte après ~300 ms, fermée en sortant ; le clic l'épingle.
        const box = await info.boundingBox();
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        assert.equal((await popState(page)).count, 0, 'pas avant 300 ms');
        await page.waitForTimeout(450);
        assert.equal((await popState(page)).count, 1, 'ouverte au survol');
        await page.mouse.move(2, 2);
        await page.waitForTimeout(300);
        assert.equal((await popState(page)).count, 0, 'fermée à la sortie');
        await info.click();
        await page.mouse.move(2, 2);
        await page.waitForTimeout(300);
        assert.equal((await popState(page)).count, 1, 'épinglée par le clic');
        await info.click();
        assert.equal((await popState(page)).count, 0);
        assert.deepEqual(ctx.errors, []);
      });
    });

    test(`Lot 6 réel — chaque aide visible s'ouvre dans le viewport (page maison et fiche) ; aucune fa-info-circle hors composant (${tag})`, async (t) => {
      await withRealView(t, options(theme, width, { hash: '#j2ha-vue=piece:9;eq:231' }), async (page, ctx) => {
        await setTheme(page, theme);
        await page.locator('.j2ha-eq-panel[data-eq-id="231"] .j2ha-cmd-table').waitFor();
        const count = await page.locator('.j2ha-info, .j2ha-tip').count();
        let checked = 0;
        for (let i = 0; i < count; i += 1) {
          const el = page.locator('.j2ha-info, .j2ha-tip').nth(i);
          if (!(await el.isVisible())) continue;
          await el.scrollIntoViewIfNeeded();
          await el.click();
          const s = await popState(page);
          const label = await el.evaluate((n) => n.className);
          if (s.count === 0) { assert.equal(await el.getAttribute('data-j2ha-tip') || await el.getAttribute('title') || '', '', `${label} : texte vide seulement`); continue; }
          assert.equal(s.count, 1, label);
          assert.ok(s.text.length > 0, label);
          assertInViewport(s, label);
          await page.keyboard.press('Escape');
          checked += 1;
        }
        assert.ok(checked >= 5, `aides vérifiées : ${checked}`);
        const stray = await page.evaluate(() => [...document.querySelectorAll('.fa-info-circle')].filter((i) => !i.closest('button.j2ha-info')).map((i) => i.parentElement.className));
        assert.deepEqual(stray, []);
        assert.deepEqual(ctx.errors, []);
      });
    });

    test(`Lot 6 réel — fenêtre « Corriger le type » : la bulle de « ID modifié » passe au-dessus ; Échap ferme la bulle, puis la fenêtre (${tag})`, async (t) => {
      await withRealView(t, options(theme, width, { hash: '#j2ha-vue=piece:9;eq:231' }), async (page, ctx) => {
        await setTheme(page, theme);
        const P = '.j2ha-eq-panel[data-eq-id="231"]';
        await page.locator(`${P} .j2ha-cmd-table`).waitFor();
        await page.locator(`${P} tr[data-cmd-id="2311"] .j2ha-type-link`).click();
        await page.locator('body > .j2ha-v3-type-modal .j2ha-v2-type-panel').waitFor();
        await page.locator('.j2ha-v3-type-modal input[data-type="light"]').check();
        const info = page.locator('.j2ha-v3-type-modal .j2ha-v2-type-idchange button.j2ha-info');
        await info.waitFor();
        await info.click();
        const s = await popState(page);
        assert.equal(s.count, 1);
        assert.match(s.text, /automatisations et tableaux de bord Home Assistant qui utilisent l’ancien identifiant/);
        assert.ok(s.onTop, 'la bulle est au-dessus de la fenêtre modale');
        assert.equal(s.more, 'https://doc.example.test/plugin#corriger-le-type');
        assertInViewport(s, 'fenêtre');
        assert.equal(await page.evaluate(() => document.querySelector('.j2ha-info-pop').closest('[inert]')), null, 'bulle non inerte');
        await shot(page, `fenetre-${theme}-${width}`);
        await page.keyboard.press('Escape');
        assert.equal((await popState(page)).count, 0);
        assert.equal(await page.locator('.j2ha-v3-type-modal').count(), 1, 'Échap ferme d’abord la bulle, pas la fenêtre');
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('.j2ha-v3-type-modal').count(), 0, 'second Échap : la fenêtre se ferme');
        assert.ok(!ctx.journal.some((e) => ['saveMappingOverride', 'savePublicationOverride', 'executeHaAction'].includes(e.action)), 'aucune écriture');
        assert.deepEqual(ctx.errors, []);
      });
    });

    test(`Lot 6 réel — « Choisir ce qui est publié » : ⓘ au clic au-dessus de la boîte, sans déplier la ligne (${tag})`, async (t) => {
      await withRealView(t, options(theme, width), async (page, ctx) => {
        await setTheme(page, theme);
        const card = '#j2ha_roomCards .j2ha-room-card[data-object_id="9"]';
        await page.locator(`${card} .j2ha-menu-toggle`).click();
        await page.locator(`${card} .j2ha-room-choose`).click();
        await page.locator('.bootbox .j2ha-v2-excl').waitFor({ state: 'visible' });
        await page.locator('.bootbox .j2ha-v2-excl-rule').click();
        const s = await popState(page);
        assert.match(s.text, /ni lui-même, ni par sa pièce, ni par son plugin/);
        assert.ok(s.onTop);
        assert.equal(s.more, 'https://doc.example.test/plugin#choisir-ce-qui-est-publié');
        assertInViewport(s, 'panneau');
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('.bootbox .j2ha-v2-excl').count(), 1, 'Échap ferme la bulle, pas la boîte');
        const stray = await page.evaluate(() => [...document.querySelectorAll('.fa-info-circle')].filter((i) => !i.closest('button.j2ha-info')).length);
        assert.equal(stray, 0);
        assert.deepEqual(ctx.errors, []);
      });
    });
  }
}

// --- Configuration du plugin (page rendue par PHP, faux cœur minimal, VRAI composant et VRAIES feuilles de style) ----------

function renderConfiguration() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'j2ha-cfg6-'));
  const plugin = path.join(tmp, 'plugins', 'jeedom2ha');
  for (const dir of ['plugin_info', 'core/php', 'desktop/php']) fs.mkdirSync(path.join(plugin, dir), { recursive: true });
  fs.mkdirSync(path.join(tmp, 'core', 'php'), { recursive: true });
  fs.copyFileSync(path.join(ROOT, 'plugin_info/configuration.php'), path.join(plugin, 'plugin_info/configuration.php'));
  fs.writeFileSync(path.join(tmp, 'core', 'php', 'core.inc.php'), `<?php
class J2haFakePlugin { private $id; public function __construct($id) { $this->id = $id; } public function isActive() { return 0; } public function getDocumentation() { return 'https://doc.example.test/plugin'; } }
class plugin { public static function byId($id) { return new J2haFakePlugin($id); } }
class config { public static function byKey($key, $plugin = 'core', $default = '') { return $key === 'functionality::cron5::enable' ? 0 : $default; } }
function isConnect($right = '') { return true; }
function include_file() {}
`);
  try {
    return execFileSync('php', [path.join(plugin, 'plugin_info/configuration.php')], { encoding: 'utf8' });
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

for (const theme of ['Light', 'Dark']) {
  for (const width of [1280, 760]) {
    test(`Lot 6 réel — configuration : ⓘ du broker et de cron5 au clic, clavier, viewport, lien vers la doc (${theme}, ${width} px)`, async (t) => {
      if (!phpAvailable || !JQUERY) { t.skip('PHP ou jQuery indisponible'); return; }
      let playwright;
      try {
        const { loadPlaywright } = await import(gate('lib', 'playwright.mjs'));
        playwright = loadPlaywright();
      } catch { t.skip('Playwright indisponible'); return; }
      const strip = (s) => s.replace(/\{\{([^}]*)\}\}/g, '$1');
      // Comme sur la box : les include_file de configuration.php chargent les deux feuilles du plugin et le composant.
      const html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>'
        + read('desktop/css/jeedom2ha.css') + read('desktop/css/jeedom2ha_v2.css') + (theme === 'Light' ? CORE_LIGHT : 'body { background: rgb(25, 25, 25); color: #ddd; }')
        + '</style><script src="/assets/jquery.js"></script><script src="/assets/infotip.js"></script></head>'
        + `<body data-theme="core2019_${theme}"><div id="div_plugin_configuration" style="padding: 10px">` + strip(renderConfiguration()) + '</div></body></html>';
      const browser = await playwright.chromium.launch({ headless: true });
      try {
        const page = await (await browser.newContext({ viewport: { width, height: 700 } })).newPage();
        const errors = [];
        page.on('pageerror', (e) => errors.push(e.message));
        await page.route('http://cfg.test/**', async (route) => {
          const url = new URL(route.request().url());
          if (url.pathname === '/') { await route.fulfill({ contentType: 'text/html', body: html }); return; }
          if (url.pathname === '/assets/jquery.js') { await route.fulfill({ contentType: 'application/javascript', body: fs.readFileSync(JQUERY, 'utf8') }); return; }
          if (url.pathname === '/assets/infotip.js') { await route.fulfill({ contentType: 'application/javascript', body: strip(read('desktop/js/jeedom2ha_infotip.js')) }); return; }
          if (url.pathname.endsWith('/jeedom2ha.ajax.php')) { await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ state: 'ok', result: { source: 'none', has_password: false } }) }); return; }
          await route.fulfill({ status: 404, body: '' });
        });
        await page.goto('http://cfg.test/');
        const intro = page.locator('#i_mqttBrokerIntro');
        assert.equal(await intro.evaluate((el) => el.tagName), 'BUTTON');
        assert.equal(await intro.getAttribute('aria-label'), 'Aide : Le broker que Home Assistant utilise déjà');
        await intro.click();
        let s = await popState(page);
        assert.match(s.text, /^Indiquez le broker que Home Assistant utilise déjà/);
        assert.equal(s.more, 'https://doc.example.test/plugin#connexion-au-broker-mqtt');
        assert.notEqual(s.bg, 'rgba(0, 0, 0, 0)');
        assertInViewport(s, 'broker');
        await shot(page, `configuration-${theme}-${width}`);
        await page.locator('#p_j2haBackTop').click();
        assert.equal((await popState(page)).count, 0, 'clic ailleurs');
        // Clavier : Tab depuis le champ « Hôte MQTT »… on part de l'ⓘ de l'hôte, Entrée ouvre, Tab passe au lien, Échap rend le focus.
        const host = page.locator('.form-group:has([data-l1key=mqttHost]) button.j2ha-info');
        await host.focus();
        await page.keyboard.press('Enter');
        s = await popState(page);
        assert.equal(s.text, "Adresse IP ou nom d'hôte du broker MQTT");
        await page.keyboard.press('Tab');
        assert.equal(await page.evaluate(() => document.activeElement.classList.contains('j2ha-info-more')), true, 'Tab : « En savoir plus »');
        await page.keyboard.press('Escape');
        assert.equal((await popState(page)).count, 0);
        assert.equal(await page.evaluate(() => document.activeElement.closest('.form-group').querySelector('[data-l1key=mqttHost]') !== null), true, 'focus rendu à ⓘ');
        // cron5 décoché : l'avertissement et son ⓘ, au bord droit à 760 px.
        await page.locator('#p_cron5Note button.j2ha-info').click();
        s = await popState(page);
        assert.match(s.text, /^Toutes les 5 minutes, cron5 republie/);
        assertInViewport(s, 'cron5');
        const stray = await page.evaluate(() => [...document.querySelectorAll('.fa-info-circle, .fa-question-circle')].filter((i) => !i.closest('button.j2ha-info')).length);
        assert.equal(stray, 0, 'toutes les aides de la configuration sont des ⓘ cliquables');
        assert.deepEqual(errors, []);
      } finally {
        await browser.close();
      }
    });
  }
}
