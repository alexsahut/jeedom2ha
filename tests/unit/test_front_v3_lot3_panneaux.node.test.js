// Front v3 — Lot 3 : panneaux et configuration, vérifiés en VRAI Chromium (helpers/workview_browser.js), clair ET sombre,
// 1280 et 760 px, et sur le module pur.
//  (1) « Corriger le type » s'ouvre en fenêtre posée sur `body` : aucun élément de l'en-tête collant de la fiche
//      (.j2ha-eq-head) n'est visible à travers la fenêtre ni ne la recouvre (relevé point par point, elementFromPoint).
//  (2) « Choisir ce qui est publié » : aucune phrase d'introduction, règle d'héritage en ⓘ, « En cas de doute » dans l'en-tête,
//      cases à trois états (indeterminate) et compteur n/m ; le réglage « En cas de doute » est un changement comme un autre
//      (écrit par la même route, rétabli par « Annuler »).
//  (3) Guide : une ligne par étape, sans phrase ; un guide réellement terminé ne s'ouvre plus de lui-même.
//  (4) « Vérifier l'installation » : sans introduction, [Vu] / [Pas vu], [⬇ Diagnostic] avec « Pseudonymiser ».
// Ignoré sans Playwright / jQuery / PHP pour les parties navigateur. Données fictives (CC-48).
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { withRealView } = require('./helpers/workview_browser');
const { DEMO } = require('./helpers/front_v2_demo_trees');
const X = require('../../desktop/js/jeedom2ha_exclusions.js');
const G = require('../../desktop/js/jeedom2ha_guide.js');

const plain = (text) => String(text).replace(/\{\{|\}\}/g, '').replace(/\s+/g, ' ').trim();

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
const CORE_LIGHT = ':root { --bg-color: 245, 245, 245; --txt-color: #333; }';

function options(theme, width, extra) {
  return Object.assign({ scene: SCENE, equipments: { 231: TREES[231], 200: TREES[200] },
    treeFor: (id) => ({ state: 'ok', result: { status: 'ok', payload: TREES[id] } }),
    hash: '#j2ha-vue=piece:9;eq:231', width, height: 700 }, theme === 'Light' ? { extraCss: CORE_LIGHT } : {}, extra || {});
}

async function setTheme(page, theme) {
  await page.evaluate((th) => document.body.setAttribute('data-theme', 'core2019_' + th), theme);
}

for (const theme of ['Light', 'Dark']) {
  for (const width of [1280, 760]) {
    test(`Lot 3 (1) — « Corriger le type » en fenêtre sur body, rien de l'en-tête collant au-dessus ni à travers (${theme}, ${width} px)`, async (t) => {
      await withRealView(t, options(theme, width), async (page, ctx) => {
        await setTheme(page, theme);
        const P = '.j2ha-eq-panel[data-eq-id="231"]';
        await page.locator(`${P} .j2ha-cmd-table`).waitFor();
        // L'en-tête collant est collé en haut : on fait défiler la fiche jusqu'au tableau des commandes.
        await page.locator(`${P} tr[data-cmd-id="2311"]`).scrollIntoViewIfNeeded();
        await page.evaluate(() => window.scrollBy(0, 220));
        await page.locator(`${P} tr[data-cmd-id="2311"] .j2ha-type-link`).click();
        const box = page.locator('body > .j2ha-v3-type-modal[data-type-panel-for="2311"] .j2ha-v2-type-panel');
        await box.waitFor();
        const m = await page.evaluate(() => {
          const panel = document.querySelector('.j2ha-v3-type-modal .j2ha-v2-type-panel');
          const r = panel.getBoundingClientRect();
          const heads = [...document.querySelectorAll('.j2ha-eq-head')];
          const pts = [];
          for (let x = r.left + 4; x < r.right - 4; x += Math.max(8, (r.width - 8) / 24)) {
            for (let y = Math.max(r.top + 4, 0); y < Math.min(r.bottom - 4, window.innerHeight); y += 12) pts.push([x, y]);
          }
          let outside = 0;
          let fromHead = 0;
          pts.forEach(([x, y]) => {
            const at = document.elementFromPoint(x, y);
            if (!at || !panel.contains(at)) outside += 1;
            if (at && heads.some((h) => h.contains(at))) fromHead += 1;
          });
          const head = heads[0] ? heads[0].getBoundingClientRect() : null;
          return {
            parentIsBody: panel.closest('.j2ha-v3-type-modal').parentElement === document.body,
            bg: getComputedStyle(panel).backgroundColor, points: pts.length, outside, fromHead,
            role: panel.getAttribute('role'), modal: panel.getAttribute('aria-modal'),
            headUnder: !!head && head.bottom > r.top && head.top < r.bottom,
            ways: document.querySelectorAll('.j2ha-v2-type-ways, .j2ha-v2-type-note').length,
            overflowX: document.documentElement.scrollWidth > window.innerWidth + 1,
          };
        });
        assert.ok(m.parentIsBody, 'fenêtre ajoutée à body');
        assert.equal(m.role, 'dialog');
        assert.equal(m.modal, 'true');
        assert.match(m.bg, /^rgb\(\d+, \d+, \d+\)$/, `fond opaque (${m.bg})`);
        assert.ok(m.points > 40, `relevé suffisant (${m.points} points)`);
        assert.equal(m.fromHead, 0, 'aucun point de la fenêtre ne montre l’en-tête collant');
        assert.equal(m.outside, 0, 'rien ne recouvre la fenêtre');
        assert.equal(m.ways, 0, 'plus de bandeau bleu ni de phrase d’aperçu');
        assert.equal(m.overflowX, false, 'aucun défilement horizontal');
        assert.match(plain(await box.locator('.j2ha-v2-type-scope').innerText()), /^Pour : /);
        assert.equal(plain(await box.locator('.j2ha-open-generic-types').innerText()), 'Types génériques');
        // Échap referme, le focus revient au lien.
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('.j2ha-v3-type-modal').count(), 0);
        assert.deepEqual(ctx.errors, []);
      });
    });
  }
}

// --- (2) « Choisir ce qui est publié » : module pur ---

function model(policy) {
  const rooms = [{ object_id: 1, object_name: 'Buanderie', father_id: 0, excluded: false, equipments: [
    { eq_id: 1, eq_name: 'Lave-linge', enabled: true, eq_type: 'virtual' },
    { eq_id: 2, eq_name: 'Prise Désactivée', enabled: false, eq_type: 'virtual' },
  ] }];
  const m = X.buildModel(rooms, { kind: 'ok', view: { stale: false, equipments: {} } }, 'zwave', { virtual: 'Virtuel' });
  m.base.policy = policy;
  return m;
}

test('Lot 3 (2) — « En cas de doute » : un changement compté, écrit par saveFilteringConfig, rétabli par « Annuler »', () => {
  const m = model('sure_probable');
  const c = X.emptyChanges();
  c.policy = 'sure_only';
  const d = X.diff(m, c);
  assert.equal(d.changes, 1);
  assert.equal(d.policy, 'sure_only');
  assert.equal(plain(X.footText(d)), '1 changement · En cas de doute : Ne pas publier');
  assert.deepEqual(X.applyButton(d), { label: '{{Appliquer}}', danger: true, disabled: false }, 'des entités peuvent partir : rouge');
  assert.deepEqual(X.writesFor(m, c, 'sure_probable').map((w) => w.data), [
    { action: 'saveFilteringConfig', excludedPlugins: 'zwave', confidencePolicy: 'sure_only' }]);
  assert.deepEqual(X.inverseWrites(m, c, 'sure_only').map((w) => w.data), [
    { action: 'saveFilteringConfig', excludedPlugins: 'zwave', confidencePolicy: 'sure_probable' }], 'valeur d’origine rendue');
  assert.match(plain(X.resultText(d)), /En cas de doute : Ne pas publier/);
  // Revenir à la valeur d'origine efface le changement.
  const back = X.emptyChanges();
  back.policy = 'sure_probable';
  assert.equal(X.diff(m, back).changes, 0);
  assert.deepEqual(X.writesFor(m, back, 'sure_probable'), []);
  // Retour à « Publier » : bouton vert.
  const m2 = model('sure_only');
  const up = X.emptyChanges();
  up.policy = 'sure_probable';
  assert.equal(X.applyButton(X.diff(m2, up)).danger, false);
});

test('Lot 3 (2) réel — panneau sans phrase : ⓘ, « En cas de doute » dans l’en-tête, cases à trois états, n/m', async (t) => {
  for (const theme of ['Light', 'Dark']) {
    await withRealView(t, Object.assign(options(theme, 1280), { hash: '' }), async (page, ctx) => {
      await setTheme(page, theme);
      await page.waitForFunction(() => (document.querySelector('#j2ha_houseNumber')?.textContent ?? '').trim() !== '');
      await page.evaluate(() => window.jQuery('#bt_j2haChoosePublished').trigger('click'));
      const panel = page.locator('.bootbox .j2ha-v2-excl');
      await panel.waitFor();
      assert.equal(await panel.locator('p').count(), 0, 'aucun paragraphe');
      // Garde levée (front v3, Lot 6) : le texte de ⓘ est dans `data-j2ha-tip` (bulle au clic), plus dans `title` ; même assertion.
      assert.match(await panel.locator('.j2ha-v2-excl-rule').getAttribute('data-j2ha-tip'), /ni lui-même, ni par sa pièce, ni par son plugin/);
      const head = panel.locator('.j2ha-v3-excl-head');
      assert.equal(plain(await head.locator('.j2ha-v3-excl-doubt-label').innerText()), 'En cas de doute');
      assert.equal(await head.locator('.j2ha-v3-excl-doubt button[data-policy="sure_probable"]').getAttribute('aria-pressed'), 'true');
      const counts = await panel.locator('.j2ha-v2-excl-count').allInnerTexts();
      assert.ok(counts.length > 0 && counts.every((c) => /^\d+\/\d+$/.test(c.trim())), counts.join(','));
      // Une pièce à moitié exclue : case mixte (indeterminate) ; « Ne pas publier » en cas de doute : un changement, bouton rouge.
      const group = panel.locator('.j2ha-v2-excl-group[data-kind="room"][data-id="9"]');
      await group.locator('.j2ha-v2-excl-twisty').click();
      await panel.locator('.j2ha-v2-excl-eq[data-eq-id="231"] .j2ha-v2-excl-cb').uncheck();
      const mixed = await panel.locator('.j2ha-v2-excl-group[data-kind="room"][data-id="9"] .j2ha-v2-excl-cb')
        .evaluate((cb) => ({ indeterminate: cb.indeterminate, aria: cb.getAttribute('aria-checked') }));
      assert.deepEqual(mixed, { indeterminate: true, aria: 'mixed' });
      assert.equal(plain(await panel.locator('.j2ha-v2-excl-group[data-kind="room"][data-id="9"] .j2ha-v2-excl-count').innerText()), '1/2');
      await head.locator('.j2ha-v3-excl-doubt button[data-policy="sure_only"]').click();
      assert.match(plain(await panel.locator('.j2ha-v2-excl-sum').innerText()), /2 changements .*En cas de doute : Ne pas publier/);
      assert.equal(await panel.locator('.j2ha-v2-excl-apply').evaluate((b) => b.classList.contains('btn-danger')), true);
      await panel.locator('.j2ha-v2-excl-cancel').click();
      assert.deepEqual(ctx.journal.filter((e) => ['saveFilteringConfig', 'scanTopology', 'savePublicationOverride'].includes(e.action)), [], 'Annuler n’écrit rien');
      assert.deepEqual(ctx.errors, []);
    });
  }
});

// --- (3) Guide ---

test('Lot 3 (3) — un guide réellement terminé ne s’ouvre plus de lui-même (pur)', () => {
  assert.equal(G.STORAGE_KEYS.finished, 'jeedom2ha.guide.finished');
  const NEVER = { kind: 'never_synced' };
  assert.equal(G.shouldShow({ daemon: false }, NEVER, {}, {}), true, 'premier lancement : affiché');
  assert.equal(G.shouldShow({ daemon: false }, NEVER, { finished: true }, {}), false, 'terminé : jamais seul');
  assert.equal(G.readLocal({ getItem: (k) => (k === 'jeedom2ha.guide.finished' ? '1' : null) }).finished, true);
});

for (const theme of ['Light', 'Dark']) {
  for (const width of [1280, 760]) {
    test(`Lot 3 (3) réel — guide : une ligne par étape, sans phrase, ⓘ par étape ; terminé → mémorisé (${theme}, ${width} px)`, async (t) => {
      await withRealView(t, options(theme, width, { hash: '' }), async (page, ctx) => {
        await setTheme(page, theme);
        await page.evaluate(() => { window.localStorage.clear(); window.jQuery('#bt_j2haOpenGuide').trigger('click'); });
        await page.locator('#j2ha_v2_guide .j2ha-v2-step').first().waitFor();
        const m = await page.$$eval('#j2ha_v2_guide .j2ha-v2-step', (steps) => steps.map((s) => ({
          h: Math.round(s.getBoundingClientRect().height), ps: s.querySelectorAll('p').length,
          info: !!s.querySelector('button.j2ha-info.j2ha-v3-info[data-j2ha-tip]'), title: s.querySelector('.j2ha-v2-step-title').childNodes[0].textContent.trim(),
        })));
        assert.equal(m.length, 4);
        assert.deepEqual(m.map((s) => s.title), ['1. Connecter le broker', '2. Vérifier Home Assistant', '3. Choisir ce qui est publié', '4. Publier les équipements']);
        assert.ok(m.every((s) => s.ps === 0 && s.info), 'aucun paragraphe, une ⓘ par étape');
        const limit = width >= 1280 ? 56 : 110;
        assert.ok(m.every((s) => s.h <= limit), `hauteur d'une ligne (${m.map((s) => s.h).join(', ')} px, max ${limit})`);
        assert.doesNotMatch(await page.locator('#j2ha_v2_guide').innerText(), /rouvrable par|Le même broker que celui|Terminez l'étape/);
        // Banc : démon, broker et publication observés ; « Je l'ai vu » → les quatre étapes « Fait » → guide terminé, mémorisé.
        await page.locator('#j2ha_v2_guide .j2ha-v2-step[data-step="ha"] .j2ha-v2-guide-verify').click();
        const finished = await page.evaluate(() => window.localStorage.getItem('jeedom2ha.guide.finished'));
        assert.equal(finished, '1');
        assert.deepEqual(ctx.errors, []);
      });
    });
  }
}

// --- (4) Vérifier l'installation ---

for (const theme of ['Light', 'Dark']) {
  test(`Lot 3 (4) réel — « Vérifier l’installation » : sans introduction, [Vu] / [Pas vu], [⬇ Diagnostic] + « Pseudonymiser » (${theme})`, async (t) => {
    await withRealView(t, options(theme, 760, { hash: '' }), async (page, ctx) => {
      await setTheme(page, theme);
      await page.evaluate(() => { window.localStorage.clear(); window.jQuery('#bt_j2haCheckInstall').trigger('click'); });
      const box = page.locator('.bootbox .j2ha-v2-checkbox');
      await box.waitFor();
      assert.equal(await box.locator('.j2ha-v2-check-intro, p').count(), 0, 'aucune phrase');
      assert.equal(plain(await box.locator('#bt_exportDiagnostic').innerText()), 'Diagnostic');
      assert.equal(await box.locator('#bt_exportDiagnostic .fa-download').count(), 1);
      assert.equal(plain(await box.locator('label.j2ha-export-label').innerText()), 'Pseudonymiser');
      assert.equal(await box.locator('#cb_pseudonymize').count(), 1);
      // Un seul style par rôle : les liens sont tous .j2ha-v2-link, les boutons d'action tous btn-default.
      const links = await box.locator('a').evaluateAll((as) => as.map((a) => a.classList.contains('j2ha-v2-link')));
      assert.ok(links.length >= 3 && links.every(Boolean), 'liens : un seul style');
      assert.equal(await box.locator('.j2ha-v2-check .btn-primary, .j2ha-v2-check .btn-link').count(), 0);
      // Le banc ne fournit pas le champ `ha` : pas de contrôle Home Assistant ; on vérifie [Vu] / [Pas vu] avec un démon qui le fournit.
      assert.deepEqual(ctx.errors, []);
    });
  });
}

test('Lot 3 (4) — [Vu] / [Pas vu] pour Home Assistant (faux DOM, code réel)', () => {
  const { startGuide } = require('./helpers/guide_harness');
  const ui = startGuide();
  ui.guide.onStatus({ daemon: true, broker: { state: 'connected' }, ha: { birth_seen_at: null }, derniere_synchro_terminee: '2026-11-13T20:00:00',
    derniere_operation_resultat: { intention: 'sync', resultat: 'succes' } });
  ui.guide.openCheck();
  const modal = ui.$(ui.dom.dialogs[0].modal);
  const row = modal.find('.j2ha-v2-check[data-check="ha"]');
  assert.equal(plain(row.find('.j2ha-v2-check-haseen').text()), 'Vu');
  assert.equal(plain(row.find('.j2ha-v2-check-hahelp').text()), 'Pas vu');
  // Garde levée (front v3, Lot 6) : le texte de ⓘ est dans `data-j2ha-tip` (bulle au clic), plus dans `title` ; même assertion.
  assert.match(plain(row.find('.j2ha-v3-check-info').attr('data-j2ha-tip')), /Home Assistant se signale sur le broker/);
});

// --- Revue Codex (#403, P2) : clavier dans la fenêtre « Corriger le type » ---

for (const theme of ['Light', 'Dark']) {
  test(`Lot 3 (5) réel — fenêtre modale au clavier : focus initial dedans, Tab / Maj+Tab bouclent, fond inerte, Échap partout, focus rendu (${theme})`, async (t) => {
    await withRealView(t, options(theme, 1280), async (page, ctx) => {
      await setTheme(page, theme);
      const P = '.j2ha-eq-panel[data-eq-id="231"]';
      await page.locator(`${P} .j2ha-cmd-table`).waitFor();
      const link = page.locator(`${P} tr[data-cmd-id="2311"] .j2ha-type-link`);
      await link.focus();
      await page.keyboard.press('Enter');
      await page.locator('.j2ha-v3-type-modal .j2ha-v2-type-panel').waitFor();
      const inside = () => page.evaluate(() => !!document.activeElement && !!document.activeElement.closest('.j2ha-v3-type-modal'));
      assert.equal(await inside(), true, 'focus initial dans la fenêtre');
      const inert = await page.evaluate(() => [...document.body.children].filter((el) => !el.classList.contains('j2ha-v3-type-modal') && el.tagName !== 'SCRIPT')
        .every((el) => el.inert === true));
      assert.equal(inert, true, 'arrière-plan inerte');
      for (let i = 0; i < 25; i += 1) { await page.keyboard.press('Tab'); assert.equal(await inside(), true, `Tab n° ${i + 1}`); }
      for (let i = 0; i < 25; i += 1) { await page.keyboard.press('Shift+Tab'); assert.equal(await inside(), true, `Maj+Tab n° ${i + 1}`); }
      // Échap avec le focus sorti par un script (body) : la fenêtre se ferme quand même.
      await page.evaluate(() => document.activeElement.blur());
      await page.keyboard.press('Escape');
      assert.equal(await page.locator('.j2ha-v3-type-modal').count(), 0);
      const after = await page.evaluate(() => ({
        focused: document.activeElement && document.activeElement.classList.contains('j2ha-type-link')
          && document.activeElement.closest('tr').getAttribute('data-cmd-id'),
        inert: [...document.body.children].some((el) => el.inert === true),
      }));
      assert.equal(after.focused, '2311', 'focus rendu au déclencheur');
      assert.equal(after.inert, false, 'arrière-plan rendu actif');
      assert.deepEqual(ctx.errors, []);
    });
  });
}

// --- Cause « Plugin exclu » : le bouton mène au panneau, par plugin, le plugin en évidence ---

function excluded(id, reason) {
  const diag = { ha_entity_type: null, publication_reason: reason, reason_code: null, should_publish: false,
    projection_validity: { is_valid: false, missing_capabilities: [], missing_fields: [], reason_code: reason } };
  return { jeedom_eq_id: id, commands: [{ jeedom_cmd_id: id * 10, covered: false, diagnostic: diag, published_in_ha: false }], entities: [],
    equipment_decision: diag, sync_status: { published_in_ha: false, synced_should_publish: false, current_should_publish: false } };
}

for (const theme of ['Light', 'Dark']) {
  test(`Lot 3 (6) réel — « Plugin exclu » → « Choisir ce qui est publié », par plugin, plugin en évidence ; pièce exclue → panneau sur la pièce (${theme})`, async (t) => {
    const scene = Object.assign({}, SCENE, { eqlogics: { 9: [{ id: 401, name: 'Eq plugin', type: 'plugin_alpha' }, { id: 402, name: 'Eq pièce', type: 'plugin_beta' }] },
      plugin_names: { plugin_alpha: 'Alpha', plugin_beta: 'Beta' } });
    const equipments = { 401: excluded(401, 'excluded_plugin'), 402: excluded(402, 'excluded_object') };
    await withRealView(t, Object.assign(options(theme, 1280), { scene, equipments, treeFor: (id) => ({ state: 'ok', result: { status: 'ok', payload: equipments[id] } }),
      hash: '#j2ha-vue=piece:9;eq:401' }), async (page, ctx) => {
      await setTheme(page, theme);
      const notice = page.locator('.j2ha-eq-panel[data-eq-id="401"] .j2ha-eq-exclusion .j2ha-notice');
      await notice.waitFor();
      assert.equal(plain(await notice.locator('.j2ha-notice-text').innerText()), 'Plugin exclu : Alpha');
      assert.doesNotMatch(await notice.innerText(), /configuration du plugin/);
      await notice.locator('.j2ha-open-plugin-config').click();
      const panel = page.locator('.bootbox .j2ha-v2-excl');
      await panel.waitFor();
      assert.equal(await panel.locator('.j2ha-v2-excl-mode button[data-mode="plugin"]').getAttribute('aria-pressed'), 'true');
      const target = panel.locator('.j2ha-v3-excl-target');
      assert.equal(await target.count(), 1);
      assert.equal(await target.getAttribute('data-id'), 'plugin_alpha');
      assert.equal(await target.getAttribute('aria-expanded'), 'true');
      assert.equal(await page.evaluate(() => document.activeElement && document.activeElement.closest('.j2ha-v3-excl-target') !== null), true, 'focus sur la case du plugin');
      await panel.locator('.j2ha-v2-excl-cancel').click();
      await page.evaluate(() => { window.location.hash = '#j2ha-vue=piece:9;eq:402'; });
      const room = page.locator('.j2ha-eq-panel[data-eq-id="402"] .j2ha-eq-exclusion .j2ha-open-room-choose');
      await room.waitFor();
      await room.click();
      await panel.waitFor();
      assert.equal(await panel.locator('.j2ha-v2-excl-group[data-kind="room"][data-id="9"]').getAttribute('aria-expanded'), 'true');
      assert.equal(await panel.locator('.j2ha-v3-excl-target[data-kind="room"][data-id="9"]').count(), 1);
      assert.deepEqual(ctx.journal.filter((e) => ['saveFilteringConfig', 'scanTopology', 'saveRoomExclusion'].includes(e.action)), [], 'aucune écriture');
      assert.deepEqual(ctx.errors, []);
    });
  });
}
