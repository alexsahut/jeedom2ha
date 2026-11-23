// ARTEFACT — Story 12.4 (FR49, CC-64, AC6) : bloc « Alarme » de plugin_info/configuration.php. Champ « Code de désarmement »
// (mot de passe, jamais rechargé dans la page, enregistré seulement s'il est saisi), statut « Code déjà configuré », case
// « Retirer le code ». Vrai code sur vm, puis en VRAI Chromium sur la page rendue (faux cœur Jeedom). Valeurs fictives (CC-48).
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
const SENTINEL = 'ENC-sentinelle-12-4';

function block(name) {
  const start = config.indexOf(`/* ${name}:begin */`);
  const end = config.indexOf(`/* ${name}:end */`);
  assert.ok(start !== -1 && end > start, `bloc ${name} introuvable`);
  return config.slice(start, end);
}

test('12.4 — j2haAlarmCodeIsSaved : saisi et non retiré seulement', () => {
  const ctx = {};
  vm.runInNewContext(block('j2ha-alarm-code'), ctx);
  const f = ctx.j2haAlarmCodeIsSaved;
  assert.equal(f('1234', false), true);
  assert.equal(f('', false), false, 'vide : le code actuel est gardé');
  assert.equal(f('   ', false), false);
  assert.equal(f(undefined, false), false);
  assert.equal(f(null, false), false);
  assert.equal(f('1234', true), false, '« Retirer le code » coché : le champ n\'est jamais enregistré');
  // Revue de 12.4 : seul un code de 4 à 8 chiffres est enregistré (espaces de début et de fin retirés).
  assert.equal(f('  1234 ', false), true);
  assert.equal(f('12345678', false), true);
  for (const bad of ['123', '123456789', '12a4', '12 34', '-1234', '1234.5', 'abcd', '١٢٣٤', '1234\n5']) {
    assert.equal(f(bad, false), false, `refusé : ${JSON.stringify(bad)}`);
  }
});

test('12.4 revue — j2haAlarmCodeIsValid / IsRejected : 4 à 8 chiffres, message seulement pour une saisie refusée', () => {
  const ctx = {};
  vm.runInNewContext(block('j2ha-alarm-code'), ctx);
  assert.equal(ctx.j2haAlarmCodeIsValid('0000'), true);
  assert.equal(ctx.j2haAlarmCodeIsValid(' 00000000\t'), true);
  assert.equal(ctx.j2haAlarmCodeIsValid('000'), false);
  assert.equal(ctx.j2haAlarmCodeIsValid(null), false);
  assert.equal(ctx.j2haAlarmCodeIsRejected('', false), false, 'vide : pas de message (le code actuel est gardé)');
  assert.equal(ctx.j2haAlarmCodeIsRejected('   ', false), false);
  assert.equal(ctx.j2haAlarmCodeIsRejected('12a4', false), true);
  assert.equal(ctx.j2haAlarmCodeIsRejected('12a4', true), false, '« Retirer le code » coché : le champ est ignoré');
  assert.equal(ctx.j2haAlarmCodeIsRejected('1234', false), false);
});

test('12.4 revue — j2haAlarmCodeRestartNotice : avis de redémarrage pour chaque changement en attente', () => {
  const ctx = {};
  vm.runInNewContext(block('j2ha-alarm-code'), ctx);
  const n = ctx.j2haAlarmCodeRestartNotice;
  assert.equal(n('2468', false, false), 'first', 'premier code : désarmable sans code jusqu\'au redémarrage');
  assert.equal(n('2468', false, true), 'change');
  assert.equal(n('', true, true), 'clear');
  assert.equal(n('', true, false), '', 'rien à retirer');
  assert.equal(n('', false, true), '', 'aucun changement');
  assert.equal(n('24a8', false, false), '', 'code refusé : rien ne sera enregistré');
});

test('12.4 — source : champ mot de passe sans configKey, case configKey, info-bulle et ancre de doc', () => {
  assert.match(config, /<input type="password" class="form-control" data-l1key="alarmDisarmCode" id="in_alarmDisarmCode"/);
  assert.doesNotMatch(config, /class="[^"]*configKey[^"]*" data-l1key="alarmDisarmCode"/);
  assert.match(config, /<input type="checkbox" class="configKey" data-l1key="alarmDisarmCodeClear" id="cb_alarmDisarmCodeClear"\/>/);
  assert.match(config, /data-j2ha-doc="alarmes"/);
  // Seule la présence d'un code est lue côté serveur ; sa valeur n'est jamais écrite dans la page.
  assert.match(config, /\$j2haAlarmCodeSet = \(string\) config::byKey\('alarmDisarmCode', 'jeedom2ha', ''\) !== '';/);
  assert.doesNotMatch(config, /echo[^;]*config::byKey\('alarmDisarmCode'/);
  assert.doesNotMatch(block('j2ha-alarm-code'), /console\.\w+\(/);
  // Revue de 12.4 : les trois avis de redémarrage, dont celui qui dit que l'alarme reste désarmable sans code.
  assert.match(config, /data-j2ha-alarm-restart="first"[^>]*>[\s\S]*?Sans redémarrage, l'alarme reste désarmable sans code\./);
  assert.match(config, /data-j2ha-alarm-restart="change"[^>]*>[\s\S]*?Sans redémarrage, l'ancien code reste demandé\./);
  assert.match(config, /data-j2ha-alarm-restart="clear"[^>]*>[\s\S]*?Sans redémarrage, le code reste demandé pour désarmer\./);
  assert.match(config, /id="span_alarmDisarmCodeInvalid"[^>]*>[\s\S]*?4 à 8 chiffres/);
});

// --- Vrai Chromium sur la page rendue (faux cœur Jeedom) ---

const JQUERY = [process.env.JEEDOM2HA_JQUERY, '/usr/share/javascript/jquery/jquery.min.js', '/usr/share/javascript/jquery/jquery.js']
  .filter(Boolean).find((file) => fs.existsSync(file));
let phpAvailable = true;
try { execFileSync('php', ['-v'], { stdio: 'ignore' }); } catch { phpAvailable = false; }

function renderConfiguration(fixture) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'j2ha-cfg-alarm-'));
  const plugin = path.join(tmp, 'plugins', 'jeedom2ha');
  for (const dir of ['plugin_info', 'core/php', 'desktop/php']) fs.mkdirSync(path.join(plugin, dir), { recursive: true });
  fs.mkdirSync(path.join(tmp, 'core', 'php'), { recursive: true });
  fs.copyFileSync(path.join(root, 'plugin_info/configuration.php'), path.join(plugin, 'plugin_info/configuration.php'));
  for (const file of fs.readdirSync(path.join(root, 'core/php')).filter((f) => f.endsWith('.php'))) fs.copyFileSync(path.join(root, 'core/php', file), path.join(plugin, 'core/php', file));
  fs.writeFileSync(path.join(tmp, 'fixture.json'), JSON.stringify(fixture));
  fs.writeFileSync(path.join(tmp, 'core', 'php', 'core.inc.php'), `<?php
$GLOBALS['j2ha_fixture'] = json_decode(file_get_contents(${JSON.stringify(path.join(tmp, 'fixture.json'))}), true);
class J2haFakePlugin { public function isActive() { return 0; } public function getName() { return 'x'; } public function getDocumentation() { return ''; } }
class plugin { public static function byId($id) { return new J2haFakePlugin(); } }
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

async function withPage(t, fixture, fn) {
  if (!phpAvailable || !JQUERY) { t.skip('PHP ou jQuery indisponible'); return; }
  let playwright;
  try {
    const { pathToFileURL } = require('node:url');
    const { loadPlaywright } = await import(pathToFileURL(path.join(root, 'tests/e2e/gate/lib/playwright.mjs')).href);
    playwright = loadPlaywright();
  } catch { t.skip('Playwright indisponible'); return; }
  const html = renderConfiguration(fixture);
  const page0 = '<!doctype html><html><head><meta charset="utf-8"><script src="/assets/jquery.js"></script></head><body><div id="div_plugin_configuration">'
    + html.replace(/\{\{([^}]*)\}\}/g, '$1') + '</div></body></html>';
  const browser = await playwright.chromium.launch({ headless: true });
  try {
    const page = await (await browser.newContext()).newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.route('http://cfg.test/**', async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname === '/') { await route.fulfill({ contentType: 'text/html', body: page0 }); return; }
      if (url.pathname === '/assets/jquery.js') { await route.fulfill({ contentType: 'application/javascript', body: fs.readFileSync(JQUERY, 'utf8') }); return; }
      await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ state: 'ok', result: { source: 'none', has_password: false } }) });
    });
    await page.goto('http://cfg.test/');
    await fn(page, html);
    assert.deepEqual(errors, []);
  } finally {
    await browser.close();
  }
}

test('12.4 réel — sans code enregistré : pas de statut ni de case « Retirer » ; la saisie seule devient configKey', async (t) => {
  await withPage(t, { config: {} }, async (page) => {
    assert.equal(await page.locator('#span_alarmDisarmCodeStatus').isVisible(), false);
    assert.equal(await page.locator('#div_alarmDisarmCodeClear').isVisible(), false);
    const field = page.locator('#in_alarmDisarmCode');
    assert.equal(await field.getAttribute('type'), 'password');
    assert.equal(await field.inputValue(), '');
    assert.equal(await page.locator('.configKey[data-l1key=alarmDisarmCode]').count(), 0);
    await field.fill('2468');
    assert.equal(await page.locator('.configKey[data-l1key=alarmDisarmCode]').count(), 1);
    await field.fill('');
    assert.equal(await page.locator('.configKey[data-l1key=alarmDisarmCode]').count(), 0, 'vide : le code actuel est gardé');
  });
});

test('12.4 réel — code enregistré : statut affiché, valeur jamais dans la page, « Retirer le code » vide et désactive le champ', async (t) => {
  await withPage(t, { config: { alarmDisarmCode: SENTINEL } }, async (page, html) => {
    assert.ok(!html.includes(SENTINEL), 'le code chiffré n\'entre jamais dans le HTML');
    assert.equal(await page.locator('#span_alarmDisarmCodeStatus').isVisible(), true);
    assert.equal(await page.locator('#div_alarmDisarmCodeClear').isVisible(), true);
    await page.locator('#in_alarmDisarmCode').fill('1357');
    await page.locator('#cb_alarmDisarmCodeClear').check();
    assert.equal(await page.locator('#in_alarmDisarmCode').inputValue(), '');
    assert.equal(await page.locator('#in_alarmDisarmCode').isDisabled(), true);
    assert.equal(await page.locator('.configKey[data-l1key=alarmDisarmCode]').count(), 0);
    await page.locator('#cb_alarmDisarmCodeClear').uncheck();
    assert.equal(await page.locator('#in_alarmDisarmCode').isDisabled(), false);
  });
});

test('12.4 revue réel — code non numérique : message clair, jamais enregistré, pas d\'avis de redémarrage', async (t) => {
  await withPage(t, { config: {} }, async (page) => {
    const field = page.locator('#in_alarmDisarmCode');
    assert.equal(await field.getAttribute('inputmode'), 'numeric');
    await field.fill('12ab');
    assert.equal(await page.locator('#span_alarmDisarmCodeInvalid').isVisible(), true);
    assert.equal(await page.locator('.configKey[data-l1key=alarmDisarmCode]').count(), 0, 'code refusé : pas enregistré');
    assert.equal(await page.locator('#div_alarmDisarmCodeRestart').isVisible(), false);
    await field.fill('123');
    assert.equal(await page.locator('#span_alarmDisarmCodeInvalid').isVisible(), true, 'trop court');
    await field.fill(' 1234 ');
    assert.equal(await page.locator('#span_alarmDisarmCodeInvalid').isVisible(), false);
    assert.equal(await page.locator('.configKey[data-l1key=alarmDisarmCode]').count(), 1);
  });
});

test('12.4 revue réel — premier code : redémarrage requis, l\'alarme reste désarmable sans code d\'ici là', async (t) => {
  await withPage(t, { config: {} }, async (page) => {
    assert.equal(await page.locator('#div_alarmDisarmCodeRestart').isVisible(), false);
    await page.locator('#in_alarmDisarmCode').fill('2468');
    assert.equal(await page.locator('#div_alarmDisarmCodeRestart').isVisible(), true);
    const visible = page.locator('[data-j2ha-alarm-restart]:visible');
    assert.equal(await visible.count(), 1);
    assert.equal(await visible.getAttribute('data-j2ha-alarm-restart'), 'first');
    assert.match(await visible.innerText(), /redémarrez le démon/);
    assert.match(await visible.innerText(), /l'alarme reste désarmable sans code/);
    await page.locator('#in_alarmDisarmCode').fill('');
    assert.equal(await page.locator('#div_alarmDisarmCodeRestart').isVisible(), false);
  });
});

test('12.4 revue réel — code enregistré : changement et retrait annoncent chacun le redémarrage', async (t) => {
  await withPage(t, { config: { alarmDisarmCode: SENTINEL } }, async (page) => {
    await page.locator('#in_alarmDisarmCode').fill('1357');
    assert.equal(await page.locator('[data-j2ha-alarm-restart]:visible').getAttribute('data-j2ha-alarm-restart'), 'change');
    await page.locator('#cb_alarmDisarmCodeClear').check();
    assert.equal(await page.locator('[data-j2ha-alarm-restart]:visible').getAttribute('data-j2ha-alarm-restart'), 'clear');
    assert.match(await page.locator('[data-j2ha-alarm-restart]:visible').innerText(), /le code reste demandé pour désarmer/);
    await page.locator('#cb_alarmDisarmCodeClear').uncheck();
    assert.equal(await page.locator('#div_alarmDisarmCodeRestart').isVisible(), false);
  });
});

test('12.4 revue réel — après « enregistrer et redémarrer », le code quitte le formulaire et l\'avis disparaît', async (t) => {
  await withPage(t, { config: {} }, async (page) => {
    await page.locator('#in_alarmDisarmCode').fill('2468');
    await page.evaluate(() => window.j2haAlarmCodeAfterSave());
    assert.equal(await page.locator('#in_alarmDisarmCode').inputValue(), '');
    assert.equal(await page.locator('#span_alarmDisarmCodeStatus').isVisible(), true);
    assert.equal(await page.locator('#div_alarmDisarmCodeRestart').isVisible(), false);
    await page.locator('#in_alarmDisarmCode').fill('1357');
    assert.equal(await page.locator('[data-j2ha-alarm-restart]:visible').getAttribute('data-j2ha-alarm-restart'), 'change');
    // Un code refusé n'est pas enregistré : il reste dans le champ avec son message.
    await page.locator('#in_alarmDisarmCode').fill('13a7');
    await page.evaluate(() => window.j2haAlarmCodeAfterSave());
    assert.equal(await page.locator('#in_alarmDisarmCode').inputValue(), '13a7');
    assert.equal(await page.locator('#span_alarmDisarmCodeInvalid').isVisible(), true);
  });
});
