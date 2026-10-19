// ARTEFACT — Story 25.9 (AC2, AC4, AC5, AC7) : JS en ligne de plugin_info/configuration.php. La valeur de `excludedPlugins` écrite par la
// liste à cocher (D2) : ordre conservé, ajout en fin, retrait de toutes les occurrences, verbatim si rien ne change ; « Appliquer et
// rescanner » n'envoie plus excludedObjects ; budgets et messages inchangés. Vrai code sur vm, puis en VRAI Chromium sur la page rendue
// (faux cœur Jeedom). Plugins fictifs (CC-48).
'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const test = require('node:test');
const assert = require('node:assert/strict');

const root = path.join(__dirname, '..', '..');
const config = fs.readFileSync(path.join(root, 'plugin_info/configuration.php'), 'utf8');

function loadCompute() {
  const begin = config.indexOf('/* j2ha-excluded-plugins:begin */');
  const end = config.indexOf('/* j2ha-excluded-plugins:end */');
  assert.ok(begin > 0 && end > begin, 'bloc balisé présent');
  const sandbox = {};
  vm.runInNewContext(config.slice(begin, end), sandbox);
  return (...args) => sandbox.j2haComputeExcludedPlugins(...args);
}

test('25.9 / AC2 — valeur écrite : ordre conservé, ajout en fin, retrait', () => {
  const compute = loadCompute();
  // Cas de l'AC : plugin_beta et plugin_gone exclus ; on coche plugin_alpha et on décoche plugin_beta.
  assert.equal(compute('plugin_beta,plugin_gone', ['plugin_beta', 'plugin_gone'], ['plugin_gone', 'plugin_alpha']), 'plugin_gone,plugin_alpha');
  // Décocher un plugin absent de Jeedom le retire.
  assert.equal(compute('plugin_beta,plugin_gone', ['plugin_beta', 'plugin_gone'], ['plugin_beta']), 'plugin_beta');
  // Ajouts en fin, dans l'ordre des cases cochées.
  assert.equal(compute('plugin_beta', ['plugin_beta'], ['plugin_beta', 'plugin_alpha', 'plugin_gamma']), 'plugin_beta,plugin_alpha,plugin_gamma');
  // Liste vide : chaîne vide ; premier ajout sur une liste vide.
  assert.equal(compute('plugin_beta', ['plugin_beta'], []), '');
  assert.equal(compute('', [], ['plugin_alpha']), 'plugin_alpha');
  // Les identifiants déjà présents gardent leur ordre, les espaces des autres jetons sont normalisés à l'écriture seulement.
  assert.equal(compute(' plugin_c , plugin_a ,plugin_b', ['plugin_c', 'plugin_a', 'plugin_b'], ['plugin_c', 'plugin_b']), 'plugin_c,plugin_b');
  // Toutes les occurrences d'un identifiant décoché sont retirées.
  assert.equal(compute('plugin_a,plugin_b,plugin_a', ['plugin_a', 'plugin_b'], ['plugin_b']), 'plugin_b');
  // Un jeton inconnu des cases (donnée héritée) est conservé.
  assert.equal(compute('plugin_a,0,plugin_b', ['plugin_a', 'plugin_b'], ['plugin_a', 'plugin_b', 'plugin_c']), 'plugin_a,0,plugin_b,plugin_c');
});

test('25.9 / AC2 — ne rien toucher renvoie la valeur chargée IDENTIQUE, verbatim (aucune normalisation, Q4)', () => {
  const compute = loadCompute();
  for (const value of ['', 'plugin_beta,plugin_gone', ' plugin_beta , plugin_gone ', 'plugin_a,,plugin_a', 'plugin_b,plugin_a']) {
    const ids = value.split(',').map((t) => t.trim()).filter((t) => t !== '');
    const unique = [...new Set(ids)];
    assert.equal(compute(value, unique, unique.slice().reverse()), value, JSON.stringify(value));
  }
});

test('25.9 / AC7 — « Appliquer et rescanner » : exactement action, excludedPlugins, confidencePolicy ; budgets et messages inchangés', () => {
  assert.doesNotMatch(config, /excludedObjects/);
  const save = config.match(/data: \{\s*action:\s*'saveFilteringConfig',([\s\S]*?)\},\s*dataType: 'json',\s*timeout: 10000,/);
  assert.ok(save, 'bloc de sauvegarde');
  const keys = [...('action' + save[0]).matchAll(/^\s*(action|excludedPlugins|excludedObjects|confidencePolicy):/gm)].map((m) => m[1]);
  assert.deepEqual(keys, ['action', 'excludedPlugins', 'confidencePolicy']);
  assert.match(config, /excludedPlugins:\s+j2haExcludedPluginsValue\(\),/);
  assert.match(config, /confidencePolicy: \$\('\.configKey\[data-l1key=confidencePolicy\]'\)\.val\(\)/);
  assert.match(config, /data: \{action: 'scanTopology'\},\s*dataType: 'json',\s*timeout: 90000,/);
  assert.match(config, /r\.status !== 'ok' \|\| r\.operation_result !== 'succes'/);
  assert.match(config, /\{\{Appliqué & Rescan terminé\}\}/);
});

test('25.9 / AC4 — le JS reste EN LIGNE dans configuration.php (jamais dans desktop/js)', () => {
  assert.match(config, /NE PAS déplacer dans desktop\/js\/jeedom2ha\.js/);
  assert.doesNotMatch(fs.readFileSync(path.join(root, 'desktop/js/jeedom2ha.js'), 'utf8'), /j2haComputeExcludedPlugins|j2haExcludedPluginsValue/);
});

// --- Vrai Chromium sur la page rendue (faux cœur Jeedom) ---

const JQUERY = [process.env.JEEDOM2HA_JQUERY, '/usr/share/javascript/jquery/jquery.min.js', '/usr/share/javascript/jquery/jquery.js']
  .filter(Boolean).find((file) => fs.existsSync(file));
let phpAvailable = true;
try { execFileSync('php', ['-v'], { stdio: 'ignore' }); } catch { phpAvailable = false; }

function renderConfiguration(fixture) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'j2ha-cfg-'));
  const plugin = path.join(tmp, 'plugins', 'jeedom2ha');
  for (const dir of ['plugin_info', 'core/php', 'desktop/php']) fs.mkdirSync(path.join(plugin, dir), { recursive: true });
  fs.mkdirSync(path.join(tmp, 'core', 'php'), { recursive: true });
  fs.copyFileSync(path.join(root, 'plugin_info/configuration.php'), path.join(plugin, 'plugin_info/configuration.php'));
  for (const file of fs.readdirSync(path.join(root, 'core/php')).filter((f) => f.endsWith('.php'))) fs.copyFileSync(path.join(root, 'core/php', file), path.join(plugin, 'core/php', file));
  fs.copyFileSync(path.join(root, 'desktop/php/jeedom2ha_overview_helpers.php'), path.join(plugin, 'desktop/php/jeedom2ha_overview_helpers.php'));
  fs.writeFileSync(path.join(tmp, 'fixture.json'), JSON.stringify(fixture));
  fs.writeFileSync(path.join(tmp, 'core', 'php', 'core.inc.php'), `<?php
$GLOBALS['j2ha_fixture'] = json_decode(file_get_contents(${JSON.stringify(path.join(tmp, 'fixture.json'))}), true);
class J2haFakeEq { private $t; public function __construct($t) { $this->t = $t; } public function getEqType_name() { return $this->t; } }
class eqLogic { public static function all() { return array_map(function ($t) { return new J2haFakeEq($t); }, $GLOBALS['j2ha_fixture']['eq_types']); } }
class J2haFakePlugin { private $id; public function __construct($id) { $this->id = $id; } public function getName() { $n = $GLOBALS['j2ha_fixture']['plugin_names']; if (!isset($n[$this->id])) { throw new Exception('introuvable'); } return $n[$this->id]; } }
class plugin { public static function byId($id) { return new J2haFakePlugin($id); } }
class config { public static function byKey($key, $plugin = 'core', $default = '') { $c = $GLOBALS['j2ha_fixture']['config']; return array_key_exists($key, $c) ? $c[$key] : $default; } }
function isConnect($right = '') { return true; }
function include_file() {}
`);
  try {
    return execFileSync('php', [path.join(plugin, 'plugin_info/configuration.php')], { encoding: 'utf8' });
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

const FIXTURE = {
  eq_types: ['plugin_alpha', 'plugin_beta', 'plugin_gamma', 'jeedom2ha'],
  plugin_names: { plugin_alpha: 'Alpha', plugin_beta: 'Beta', plugin_gamma: 'Gamma' },
  config: { excludedPlugins: 'plugin_beta,plugin_gone', excludedObjects: '5,12' },
};

async function withConfigurationPage(t, fixture, fn) {
  if (!phpAvailable || !JQUERY) { t.skip('PHP ou jQuery indisponible'); return; }
  let playwright;
  try {
    const { pathToFileURL } = require('node:url');
    const { loadPlaywright } = await import(pathToFileURL(path.join(root, 'tests/e2e/gate/lib/playwright.mjs')).href);
    playwright = loadPlaywright();
  } catch { t.skip('Playwright indisponible'); return; }
  // jQuery est chargé AVANT le HTML de la page : le script en ligne de configuration.php s'exécute à l'analyse.
  const page0 = '<!doctype html><html><head><meta charset="utf-8"><script src="/assets/jquery.js"></script></head><body><div id="div_plugin_configuration">'
    + renderConfiguration(fixture).replace(/\{\{([^}]*)\}\}/g, '$1') + '</div></body></html>';
  const browser = await playwright.chromium.launch({ headless: true });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    const requests = [];
    const errors = [];
    await page.route('http://cfg.test/**', async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname === '/') { await route.fulfill({ contentType: 'text/html', body: page0 }); return; }
      if (url.pathname === '/assets/jquery.js') { await route.fulfill({ contentType: 'application/javascript', body: fs.readFileSync(JQUERY, 'utf8') }); return; }
      if (url.pathname.endsWith('/jeedom2ha.ajax.php')) {
        const params = new URLSearchParams(route.request().postData() || '');
        requests.push(Object.fromEntries(params.entries()));
        const action = params.get('action');
        let body = { state: 'error', result: 'inattendu' };
        if (action === 'getMqttConfig') body = { state: 'ok', result: { source: 'none', has_password: false } };
        else if (action === 'saveFilteringConfig') body = { state: 'ok', result: { saved: true } };
        else if (action === 'scanTopology') body = { state: 'ok', result: { status: 'ok', operation_result: 'succes', payload: { mapping_summary: { light_published: 2 } } } };
        await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
        return;
      }
      await route.fulfill({ status: 404, body: '' });
    });
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto('http://cfg.test/');
    await fn(page, { requests, errors });
  } finally {
    await browser.close();
  }
}

test('25.9 réel — la liste reflète excludedPlugins ; cocher / décocher puis « Appliquer » envoie la valeur D2 sans excludedObjects', async (t) => {
  await withConfigurationPage(t, FIXTURE, async (page, ctx) => {
    const state = () => page.locator('#div_excludedPluginsList input.j2ha-excluded-plugin').evaluateAll((boxes) => boxes.map((b) => `${b.value}:${b.checked}`));
    assert.deepEqual(await state(), ['plugin_alpha:false', 'plugin_beta:true', 'plugin_gamma:false', 'plugin_gone:true']);
    assert.equal(await page.locator('.configKey[data-l1key=excludedPlugins]').inputValue(), 'plugin_beta,plugin_gone', 'champ porteur = valeur chargée');
    assert.equal(await page.locator('.configKey[data-l1key=excludedObjects]').count(), 0, 'plus de champ des pièces');
    await page.locator('input[value="plugin_alpha"]').check();
    await page.locator('input[value="plugin_beta"]').uncheck();
    assert.equal(await page.locator('.configKey[data-l1key=excludedPlugins]').inputValue(), 'plugin_gone,plugin_alpha', '« Sauvegarder » du cœur lit la même valeur');
    await page.locator('#bt_applyAndRescan').click();
    await page.waitForFunction(() => /Rescan terminé/.test(document.querySelector('#span_rescanResult').textContent));
    const save = ctx.requests.find((r) => r.action === 'saveFilteringConfig');
    assert.deepEqual(Object.keys(save).sort(), ['action', 'confidencePolicy', 'excludedPlugins']);
    assert.equal(save.excludedPlugins, 'plugin_gone,plugin_alpha');
    assert.ok(!('excludedObjects' in save));
    assert.deepEqual(ctx.requests.map((r) => r.action).filter((a) => a !== 'getMqttConfig'), ['saveFilteringConfig', 'scanTopology']);
    assert.deepEqual(ctx.errors, []);
  });
});

test('25.9 réel — rien de touché : « Appliquer » renvoie la valeur chargée identique, espaces compris', async (t) => {
  const fixture = Object.assign({}, FIXTURE, { config: { excludedPlugins: ' plugin_beta , plugin_gone ', excludedObjects: '5' } });
  await withConfigurationPage(t, fixture, async (page, ctx) => {
    await page.locator('#bt_applyAndRescan').click();
    await page.waitForFunction(() => /Rescan terminé/.test(document.querySelector('#span_rescanResult').textContent));
    assert.equal(ctx.requests.find((r) => r.action === 'saveFilteringConfig').excludedPlugins, ' plugin_beta , plugin_gone ');
  });
});

test('25.9 réel — décocher un plugin absent de Jeedom le retire ; le cœur qui remplit le champ resynchronise les cases', async (t) => {
  await withConfigurationPage(t, FIXTURE, async (page, ctx) => {
    await page.locator('input[value="plugin_gone"]').uncheck();
    await page.locator('#bt_applyAndRescan').click();
    await page.waitForFunction(() => /Rescan terminé/.test(document.querySelector('#span_rescanResult').textContent));
    assert.equal(ctx.requests.find((r) => r.action === 'saveFilteringConfig').excludedPlugins, 'plugin_beta');
  });
  await withConfigurationPage(t, FIXTURE, async (page) => {
    // Le cœur remplit les `configKey` après le chargement : la valeur chargée devient la référence et les cases la suivent.
    await page.evaluate(() => { $('.configKey[data-l1key=excludedPlugins]').val('plugin_alpha').trigger('change'); });
    const state = await page.locator('#div_excludedPluginsList input.j2ha-excluded-plugin').evaluateAll((boxes) => boxes.map((b) => `${b.value}:${b.checked}`));
    assert.deepEqual(state, ['plugin_alpha:true', 'plugin_beta:false', 'plugin_gamma:false', 'plugin_gone:false']);
    assert.equal(await page.locator('.configKey[data-l1key=excludedPlugins]').inputValue(), 'plugin_alpha');
  });
});

test('25.9 réel — le renvoi vers la page du plugin et le nombre de pièces exclues sont rendus, sans nom de pièce', async (t) => {
  await withConfigurationPage(t, FIXTURE, async (page) => {
    const text = (await page.locator('#div_plugin_configuration').innerText()).replace(/\s+/g, ' ');
    assert.match(text, /Pièces exclues : elles se règlent depuis la page du plugin \(menu « ⋯ » d'une carte de pièce, ou détail de la pièce\)\./);
    assert.match(text, /2 pièces exclues/);
    assert.equal(await page.locator('a[href="index.php?v=d&m=jeedom2ha&p=jeedom2ha"]').count(), 1);
    assert.equal(await page.locator('[role=group][aria-labelledby=lbl_excludedPlugins]').count(), 1);
    assert.match(text, /\(absent de Jeedom\)/);
    assert.match(text, /Les équipements des plugins cochés ne sont pas publiés dans Home Assistant\./);
  });
});
