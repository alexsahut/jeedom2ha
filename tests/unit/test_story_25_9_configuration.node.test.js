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

// Garde levée (front v3, Lot 3) : la liste à cocher des plugins, le réglage « En cas de doute » et « Enregistrer et relire
// Jeedom » quittent la configuration (une seule source : le panneau « Choisir ce qui est publié » de la page du plugin, qui écrit
// les MÊMES clés par la MÊME route, `saveFilteringConfig`). Les tests de la valeur D2 écrite par les cases (ordre, ajout en fin,
// verbatim) sont remplacés par la garde inverse : la configuration n'écrit plus ces clés, ni par sa propre requête, ni par
// « Sauvegarder » du cœur (aucun champ `configKey` de ces clés). La valeur D2 reste couverte côté panneau
// (test_front_v2_exclusions : serializePluginList, inverseWrites).
test('front v3 (Lot 3) — la configuration ne règle plus ce qui est publié : une seule source, le panneau', () => {
  assert.doesNotMatch(config, /data-l1key="?(excludedPlugins|confidencePolicy|excludedObjects)/);
  assert.doesNotMatch(config, /saveFilteringConfig|scanTopology|j2haComputeExcludedPlugins|bt_applyAndRescan/);
  assert.match(config, /href="index\.php\?v=d&amp;m=jeedom2ha&amp;p=jeedom2ha#j2ha-choisir"[^>]*>.*\{\{Choisir ce qui est publié\}\} <i class="fas fa-external-link-alt"><\/i><\/a>/);
  const panel = fs.readFileSync(path.join(root, 'desktop/js/jeedom2ha_exclusions.js'), 'utf8');
  assert.match(panel, /action: 'saveFilteringConfig',\s*excludedPlugins: serializePluginList\(model\.base\.pluginsCsv, c\.plugins\),\s*confidencePolicy: cleanPolicy\(c\.policy \|\| confidencePolicy\),/);
  const home = fs.readFileSync(path.join(root, 'desktop/js/jeedom2ha.js'), 'utf8');
  assert.match(home, /window\.location\.hash === '#j2ha-choisir'/);
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
class J2haFakePlugin { private $id; public function __construct($id) { $this->id = $id; } public function isActive() { $a = isset($GLOBALS['j2ha_fixture']['active_plugins']) ? $GLOBALS['j2ha_fixture']['active_plugins'] : array(); return in_array($this->id, $a, true) ? 1 : 0; } public function getName() { $n = $GLOBALS['j2ha_fixture']['plugin_names']; if (!isset($n[$this->id])) { throw new Exception('introuvable'); } return $n[$this->id]; } }
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

async function withConfigurationPage(t, fixture, fn, options = {}) {
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
    const dialogs = [];
    // Pas de bootbox dans le banc : la confirmation passe par window.confirm. Acceptée par défaut, refusable par option.
    page.on('dialog', async (dialog) => {
      dialogs.push(dialog.message());
      if (options.dismissDialogs) await dialog.dismiss(); else await dialog.accept();
    });
    if (options.initScript) await page.addInitScript(options.initScript);
    await page.route('http://cfg.test/**', async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname === '/') { await route.fulfill({ contentType: 'text/html', body: page0 }); return; }
      if (url.pathname === '/assets/jquery.js') { await route.fulfill({ contentType: 'application/javascript', body: fs.readFileSync(JQUERY, 'utf8') }); return; }
      if (url.pathname.endsWith('/jeedom2ha.ajax.php')) {
        const params = new URLSearchParams(route.request().postData() || '');
        requests.push(Object.fromEntries(params.entries()));
        const action = params.get('action');
        if (action === 'testMqttConnection' && options.mqttDelayMs) await new Promise((resolve) => setTimeout(resolve, options.mqttDelayMs));
        let body = { state: 'error', result: 'inattendu' };
        if (action === 'getMqttConfig') body = { state: 'ok', result: { source: 'none', has_password: false } };
        else if (action === 'saveFilteringConfig') body = { state: 'ok', result: { saved: true } };
        else if (action === 'scanTopology') body = { state: 'ok', result: { status: 'ok', operation_result: 'succes', payload: { mapping_summary: { light_published: 2 } } } };
        else if (action === 'testMqttConnection') body = options.mqttTest || { state: 'ok', result: { status: 'ok', error_code: null, message: 'Connexion réussie' } };
        else if (action === 'forceMqttManagerImport') body = { state: 'ok', result: { status: 'ok', host: 'broker.test', port: 1883, user: 'jeedom', tls: false, has_password: true } };
        await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
        return;
      }
      await route.fulfill({ status: 404, body: '' });
    });
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto('http://cfg.test/');
    await fn(page, { requests, errors, dialogs });
  } finally {
    await browser.close();
  }
}

// Garde levée (front v3, Lot 3) : la liste à cocher, le renvoi des pièces et leur nombre quittent la page (voir plus haut).
test('front v3 (Lot 3) réel — aucune case de plugin ; lien « Choisir ce qui est publié ↗ » ; « Sauvegarder » du cœur ne lit plus ces clés', async (t) => {
  await withConfigurationPage(t, FIXTURE, async (page, ctx) => {
    assert.equal(await page.locator('#div_excludedPluginsList, input.j2ha-excluded-plugin, #bt_applyAndRescan').count(), 0);
    assert.equal(await page.locator('.configKey[data-l1key=excludedPlugins], .configKey[data-l1key=confidencePolicy], .configKey[data-l1key=excludedObjects]').count(), 0);
    const link = page.locator('#lnk_j2haChoosePublished');
    assert.equal((await link.innerText()).trim(), 'Choisir ce qui est publié');
    assert.equal(await link.getAttribute('href'), 'index.php?v=d&m=jeedom2ha&p=jeedom2ha#j2ha-choisir');
    assert.match(await page.locator('#p_j2haChoosePublished .fa-info-circle').getAttribute('title'), /En cas de doute/);
    const keys = await page.evaluate(() => [...document.querySelectorAll('#div_plugin_configuration .configKey')].map((el) => el.getAttribute('data-l1key')));
    assert.ok(keys.every((k) => /^mqtt/.test(k)), keys.join(','));
    assert.deepEqual(ctx.requests.map((r) => r.action), ['getMqttConfig']);
    assert.deepEqual(ctx.errors, []);
  });
});

test('front v3 (Lot 3) réel — avertissement cron5 d\'une ligne, seulement si cron5 est décoché', async (t) => {
  await withConfigurationPage(t, FIXTURE, async (page) => {
    assert.equal(await page.locator('#p_cron5Note').isVisible(), false, 'cron5 actif (défaut) : rien');
  });
  const off = Object.assign({}, FIXTURE, { config: Object.assign({}, FIXTURE.config, { 'functionality::cron5::enable': 0 }) });
  await withConfigurationPage(t, off, async (page) => {
    const note = page.locator('#p_cron5Note');
    assert.equal(await note.isVisible(), true);
    assert.equal((await note.innerText()).trim(), 'cron5 désactivé : mises à jour manuelles');
    assert.match(await note.locator('.fa-info-circle').getAttribute('title'), /Toutes les 5 minutes/);
    // La case du cœur (bloc « Fonctionnalités ») recochée sur la même page : l'avertissement disparaît.
    await page.evaluate(() => {
      $('body').append('<input type="checkbox" class="configKey" data-l1key="functionality::cron5::enable">');
      $('[data-l1key="functionality::cron5::enable"]').prop('checked', true).trigger('change');
    });
    assert.equal(await note.isVisible(), false);
  });
});

// --- Front v2 / Lot 4 (E8) : connexion guidée, messages par code, confirmations, glossaire ---

function loadMessages() {
  const begin = config.indexOf('/* j2ha-mqtt-test-messages:begin */');
  const end = config.indexOf('/* j2ha-mqtt-test-messages:end */');
  assert.ok(begin > 0 && end > begin, 'bloc balisé des messages présent');
  const sandbox = {};
  vm.runInNewContext(config.slice(begin, end), sandbox);
  const strip = (v) => (typeof v === 'string' ? v.replace(/\{\{([^}]*)\}\}/g, '$1').replace(/\\'/g, "'") : v);
  return {
    describe: (data) => { const o = sandbox.j2haDescribeMqttTest(data); return { kind: o.kind, code: o.code, message: strip(o.message), remedy: strip(o.remedy) }; },
    check: (h, p) => sandbox.j2haCheckMqttForm(h, p),
    normalize: (c) => sandbox.j2haNormalizeMqttConfiguration(c),
  };
}

test('Lot 4 / E8 — un message et un remède par error_code du test de connexion', () => {
  const m = loadMessages();
  const table = {
    host_unreachable: ['Ce nom ou cette adresse ne répond pas.', "Vérifiez l'adresse du broker."],
    port_refused: ['Le broker refuse la connexion sur ce port.', '1883 en général, 8883 avec TLS.'],
    auth_failed: ['Identifiant ou mot de passe refusé.', "Vérifiez l'utilisateur MQTT créé pour Jeedom."],
    tls_error: ['La connexion chiffrée a échoué.', 'Décochez « Vérifier le certificat » pour un certificat auto-signé.'],
    timeout: ["Le broker n'a pas répondu à temps.", 'Vérifiez le réseau et le pare-feu.'],
    missing_host: ['Adresse manquante', ''],
    invalid_port: ['Port invalide', ''],
  };
  for (const [code, [message, remedy]] of Object.entries(table)) {
    const out = m.describe({ state: 'ok', result: { status: 'error', error_code: code, message: 'texte brut du démon' } });
    assert.deepEqual(out, { kind: 'failed', code, message, remedy }, code);
  }
  assert.deepEqual(m.describe({ state: 'ok', result: { status: 'ok', error_code: null } }), { kind: 'ok', code: null, message: 'Connexion réussie.', remedy: '' });
  const unknown = m.describe({ state: 'ok', result: { status: 'error', error_code: 'unknown_error', message: 'Broker refusé (code 3)' } });
  assert.equal(unknown.message, 'La connexion au broker a échoué.');
  assert.equal(unknown.remedy, 'Broker refusé (code 3)');
  assert.equal(m.describe({ state: 'ok', result: { status: 'error', error_code: 'toString' } }).message, 'La connexion au broker a échoué.', 'pas de clé héritée');
  assert.equal(m.describe({ state: 'error', result: 'Le démon ne répond pas' }).kind, 'no_daemon');
  assert.equal(m.describe(null).kind, 'no_daemon');
});

// Garde levée (front v3, Lot 3) : le libellé de fin de relecture part avec « Enregistrer et relire Jeedom ».
test('Lot 4 / E8 — contrôle local du formulaire (mêmes règles que le démon)', () => {
  const m = loadMessages();
  assert.equal(m.check('', '1883'), 'missing_host');
  assert.equal(m.check('   ', ''), 'missing_host');
  assert.equal(m.check('broker.test', ''), null);
  assert.equal(m.check('broker.test', '8883'), null);
  for (const bad of ['0', '65536', 'abc', '-1', '18.83']) assert.equal(m.check('broker.test', bad), 'invalid_port', bad);
});

test('Lot 4 / E8 — le mot de passe n\'est jamais affiché, journalisé ni recopié', () => {
  const script = config.slice(config.indexOf('<script>'));
  assert.doesNotMatch(script, /console\.(log|info|warn|error|debug)/);
  // La valeur saisie n'est lue qu'à deux endroits : la requête de test et le test « champ non vide ».
  const reads = [...script.matchAll(/\$\('#in_mqttPassword'\)\.val\(\)/g)].length;
  const sent = (script.match(/password:\s+\$\('#in_mqttPassword'\)\.val\(\),/g) || []).length;
  const emptiness = (script.match(/\$\('#in_mqttPassword'\)\.val\(\) !== ''/g) || []).length;
  assert.equal(sent, 1);
  assert.equal(reads, sent + emptiness);
  assert.doesNotMatch(script, /\.(text|html|append)\([^)]*(password|in_mqttPassword)/i);
});

test('Lot 4 / glossaire — plus de « rescanner » ni de « Rescan » dans les textes de la page ; identifiants DOM conservés', () => {
  const texts = [...config.matchAll(/\{\{([^}]*)\}\}/g)].map((m) => m[1]).join('\n');
  assert.doesNotMatch(texts, /rescan|synchro/i);
  // Garde levée (front v3, Lot 3) : « Enregistrer et relire Jeedom » et « En cas de doute » quittent la page (panneau « Choisir… »).
  assert.match(texts, /Tester, enregistrer et redémarrer le démon/);
});

test('Lot 4 / E8 — chaîne du cœur : jeedom.config.save puis jeedom.plugin.deamonStart({forceRestart: 1}) ; aucune action ajax ajoutée', () => {
  assert.match(config, /jeedom\.config\.save\(\{\s*configuration: snapshot\.configuration,\s*plugin: J2HA_PLUGIN_ID,/);
  assert.match(config, /configuration = j2haNormalizeMqttConfiguration\(container\.getJeeValues\('\.configKey'\)\[0\]\);/);
  assert.match(config, /jeedom\.plugin\.deamonStart\(\{\s*id: J2HA_PLUGIN_ID,\s*forceRestart: 1,/);
  const actions = [...new Set([...config.matchAll(/action:\s*'([A-Za-z]+)'/g)].map((m) => m[1]))].sort();
  // Garde levée (front v3, Lot 3) : saveFilteringConfig et scanTopology quittent la page (panneau « Choisir… » de la page du plugin).
  assert.deepEqual(actions, ['forceMqttManagerImport', 'getMqttConfig', 'testMqttConnection']);
});

// Faux cœur JS : getJeeValues (domUtils 4.4+), jeedom.config.save, jeedom.plugin.deamonStart, bloc Démon. Les appels sont consignés.
const FAKE_CORE_JS = (mode) => `
  window.__core = { saves: [], starts: [], refreshes: 0 };
  Element.prototype.getJeeValues = function (selector) {
    const values = {};
    this.querySelectorAll(selector).forEach((el) => { values[el.getAttribute('data-l1key')] = el.type === 'checkbox' ? (el.checked ? '1' : '0') : el.value; });
    return [values];
  };
  window.jeeFrontEnd = { modifyWithoutSave: true, md_pluginDaemon: { refreshDeamonInfo() { window.__core.refreshes += 1; } } };
  window.jeedom = {
    config: { save(p) { window.__core.saves.push({ plugin: p.plugin, configuration: p.configuration }); setTimeout(() => (${JSON.stringify(mode)} === 'save_error' ? p.error({ message: 'Erreur fictive du cœur' }) : p.success()), 10); } },
    plugin: { deamonStart(p) { window.__core.starts.push({ id: p.id, forceRestart: p.forceRestart }); setTimeout(() => (${JSON.stringify(mode)} === 'start_error' ? p.error({ message: 'Démarrage refusé' }) : p.success()), 10); } },
  };
`;
const MQTT_FIXTURE = Object.assign({}, FIXTURE, { config: Object.assign({}, FIXTURE.config, { mqttHost: '' }) });
const steps = (page) => page.locator('#ul_mqttGuidedSteps li').evaluateAll((items) => items.map((li) => `${li.dataset.step}:${li.dataset.state}`));
const fill = async (page) => {
  await page.locator('.configKey[data-l1key=mqttHost]').fill('broker.test');
  await page.locator('.configKey[data-l1key=mqttUser]').fill('jeedom');
  await page.locator('#in_mqttPassword').fill('secret-fictif-42');
};

test('Lot 4 réel — mauvais mot de passe : message « Identifiant ou mot de passe refusé. », rien enregistré, démon non redémarré', async (t) => {
  await withConfigurationPage(t, MQTT_FIXTURE, async (page, ctx) => {
    await fill(page);
    await page.locator('#bt_mqttTestSaveRestart').click();
    await page.waitForFunction(() => document.querySelector('#ul_mqttGuidedSteps li[data-step=test]').dataset.state === 'failed');
    assert.equal(await page.locator('#span_mqttTestResult').innerText(), 'Identifiant ou mot de passe refusé.');
    assert.match(await page.locator('#span_mqttTestRemedy').innerText(), /Vérifiez l'utilisateur MQTT créé pour Jeedom\./);
    assert.deepEqual(await steps(page), ['test:failed', 'save:pending', 'restart:pending']);
    const core = await page.evaluate(() => window.__core);
    assert.deepEqual(core.saves, [], 'rien n\'est enregistré');
    assert.deepEqual(core.starts, [], 'le démon n\'est pas redémarré');
    assert.ok(!(await page.locator('body').innerText()).includes('secret-fictif-42'), 'mot de passe jamais affiché');
    assert.equal(await page.locator('#bt_mqttTestSaveRestart').isDisabled(), false);
    assert.deepEqual(ctx.errors, []);
  }, { initScript: FAKE_CORE_JS('ok'), mqttTest: { state: 'ok', result: { status: 'error', error_code: 'auth_failed', message: 'Authentification refusée' } } });
});

test('Lot 4 réel — bons réglages : les trois coches s\'allument, enregistrement par le cœur puis redémarrage forcé', async (t) => {
  await withConfigurationPage(t, MQTT_FIXTURE, async (page, ctx) => {
    await fill(page);
    await page.locator('#bt_mqttTestSaveRestart').click();
    await page.waitForFunction(() => document.querySelector('#ul_mqttGuidedSteps li[data-step=restart]').dataset.state === 'done');
    assert.deepEqual(await steps(page), ['test:done', 'save:done', 'restart:done']);
    const core = await page.evaluate(() => window.__core);
    assert.equal(core.saves.length, 1);
    assert.equal(core.saves[0].plugin, 'jeedom2ha');
    assert.equal(core.saves[0].configuration.mqttHost, 'broker.test');
    assert.equal(core.saves[0].configuration.mqttPassword, 'secret-fictif-42', 'le mot de passe saisi part avec la sauvegarde du cœur');
    assert.deepEqual(core.starts, [{ id: 'jeedom2ha', forceRestart: 1 }]);
    assert.ok(core.refreshes >= 1, 'bloc Démon rafraîchi');
    assert.equal(await page.evaluate(() => window.jeeFrontEnd.modifyWithoutSave), false);
    assert.equal(await page.locator('#in_mqttPassword').inputValue(), '', 'le mot de passe quitte le formulaire une fois enregistré');
    assert.match(await page.locator('#div_mqttTestResult').innerText(), /MQTT Connecté/);
    const test = ctx.requests.find((r) => r.action === 'testMqttConnection');
    assert.equal(test.host, 'broker.test');
    assert.deepEqual(ctx.requests.map((r) => r.action).filter((a) => a !== 'getMqttConfig'), ['testMqttConnection'], 'aucune autre action du plugin');
    assert.ok(!(await page.locator('body').innerText()).includes('secret-fictif-42'));
    assert.deepEqual(ctx.errors, []);
  }, { initScript: FAKE_CORE_JS('ok') });
});

test('Lot 4 réel — repli : API du cœur absente ou redémarrage en échec → « Redémarrez le démon ci-dessus » et bouton vers le bloc Démon', async (t) => {
  await withConfigurationPage(t, MQTT_FIXTURE, async (page, ctx) => {
    await fill(page);
    await page.locator('#bt_mqttTestSaveRestart').click();
    await page.waitForFunction(() => document.querySelector('#ul_mqttGuidedSteps li[data-step=save]').dataset.state === 'failed');
    assert.match(await page.locator('#div_mqttGuidedFallback').innerText(), /redémarrez le démon ci-dessus/);
    await page.locator('#bt_mqttGoToDaemon').click();
    assert.deepEqual(ctx.errors, []);
  });
  await withConfigurationPage(t, MQTT_FIXTURE, async (page, ctx) => {
    await fill(page);
    await page.locator('#bt_mqttTestSaveRestart').click();
    await page.waitForFunction(() => document.querySelector('#ul_mqttGuidedSteps li[data-step=restart]').dataset.state === 'failed');
    assert.deepEqual(await steps(page), ['test:done', 'save:done', 'restart:failed']);
    assert.match(await page.locator('#div_mqttGuidedFallback').innerText(), /Réglages enregistrés\. Redémarrez le démon ci-dessus\./);
    assert.equal(await page.locator('#bt_mqttGoToDaemon').isVisible(), true);
    assert.deepEqual(ctx.errors, []);
  }, { initScript: FAKE_CORE_JS('start_error') });
});

test('Lot 4 réel — démon injoignable : le test le dit, « Enregistrer et redémarrer sans tester » demande confirmation', async (t) => {
  await withConfigurationPage(t, MQTT_FIXTURE, async (page, ctx) => {
    await fill(page);
    await page.locator('#bt_mqttTestSaveRestart').click();
    await page.locator('#lnk_mqttSaveRestartWithoutTest').waitFor({ state: 'visible' });
    assert.match(await page.locator('#span_mqttTestResult').innerText(), /Le démon ne répond pas/);
    assert.deepEqual((await page.evaluate(() => window.__core)).saves, []);
    await page.locator('#lnk_mqttSaveRestartWithoutTest').click();
    await page.waitForFunction(() => document.querySelector('#ul_mqttGuidedSteps li[data-step=restart]').dataset.state === 'done');
    assert.deepEqual(await steps(page), ['test:skipped', 'save:done', 'restart:done']);
    assert.equal(ctx.dialogs.length, 1);
    assert.deepEqual(ctx.errors, []);
  }, { initScript: FAKE_CORE_JS('ok'), mqttTest: { state: 'error', result: 'Le démon ne répond pas' } });
});

test('Lot 4 réel — hôte vide : « Adresse manquante » sans appel au démon', async (t) => {
  await withConfigurationPage(t, MQTT_FIXTURE, async (page, ctx) => {
    await page.locator('#bt_testMqttConnection').click();
    assert.equal(await page.locator('#span_mqttTestResult').innerText(), 'Adresse manquante');
    assert.equal(ctx.requests.filter((r) => r.action === 'testMqttConnection').length, 0);
  }, { initScript: FAKE_CORE_JS('ok') });
});

// Garde levée (front v3, Lot 3) : « Enregistrer et relire Jeedom » n'existe plus sur cette page.
test('Lot 4 réel — « Récupérer depuis MQTT Manager » : absent sans le plugin ; avec lui, confirmation avant d\'écraser', async (t) => {
  await withConfigurationPage(t, FIXTURE, async (page) => {
    assert.equal(await page.locator('#bt_importMqttManager').count(), 0);
  });
  const withManager = Object.assign({}, FIXTURE, { active_plugins: ['mqtt2'] });
  await withConfigurationPage(t, withManager, async (page, ctx) => {
    await page.locator('#bt_importMqttManager').click();
    assert.match(ctx.dialogs[0], /Remplacer l'adresse, le port, l'utilisateur, le mot de passe et le réglage TLS par ceux de MQTT Manager/);
    assert.equal(ctx.requests.filter((r) => r.action === 'forceMqttManagerImport').length, 0, 'annuler n\'écrase rien');
  }, { dismissDialogs: true });
  await withConfigurationPage(t, withManager, async (page, ctx) => {
    await page.locator('#bt_importMqttManager').click();
    await page.waitForFunction(() => document.querySelector('#div_mqtt_autodetect_status').classList.contains('alert-success'));
    assert.equal(ctx.requests.filter((r) => r.action === 'forceMqttManagerImport').length, 1);
    assert.equal(await page.locator('.configKey[data-l1key=mqttHost]').inputValue(), 'broker.test');
  });
});

// Garde levée (front v3, Lot 3) : zéro phrase permanente. L'intro du broker passe en info-bulle ⓘ du titre ; « Une seule
// installation par broker » devient un avertissement d'une ligne (sa conséquence en ⓘ) ; la phrase HomeKit des pièces exclues
// part avec le bloc « Ce qui est publié » (le panneau dit « Reste publié : exposé à HomeKit » équipement par équipement).
test('Lot 4 réel — en-tête, retour à la page du plugin, avertissement d\'une ligne, aucune phrase permanente', async (t) => {
  for (const fixture of [FIXTURE, Object.assign({}, FIXTURE, { active_plugins: ['homebridge', 'mqtt2'] })]) {
    await withConfigurationPage(t, fixture, async (page) => {
      const text = (await page.locator('#div_plugin_configuration').innerText()).replace(/\s+/g, ' ');
      assert.doesNotMatch(text, /Indiquez le broker que Home Assistant utilise déjà/);
      assert.match(await page.locator('#i_mqttBrokerIntro').getAttribute('title'), /Indiquez le broker que Home Assistant utilise déjà/);
      assert.equal((await page.locator('#p_mqttOneInstance').innerText()).trim(), 'Une seule installation jeedom2ha par broker MQTT.');
      assert.match(await page.locator('#p_mqttOneInstance .fa-info-circle').getAttribute('title'), /retirerait les boutons de scénario/);
      assert.match(text, /Tester, enregistrer et redémarrer le démon/);
      assert.match(text, /Tester seulement/);
      assert.equal(await page.locator('#p_j2haBackTop a, #p_j2haBackBottom a').count(), 2);
      assert.equal(await page.locator('#p_homekitRoomNote, #p_mqttSaveHint, #p_mqttBrokerIntro, .help-block:not(#span_mqttPasswordStatus)').count(), 0, 'aucune phrase d\'aide');
      assert.equal(await page.locator('.btn-primary').count(), 1, 'un bouton principal (bloc du broker)');
      assert.doesNotMatch(text, /rescan/i);
    });
  }
});

test('Lot 4 / revue — port vide enregistré à 1883 (comme le test), instantané non modifié', () => {
  const m = loadMessages();
  for (const empty of ['', '   ', undefined, null]) {
    const input = { mqttHost: 'broker.test', mqttPort: empty, mqttUser: 'jeedom' };
    const out = m.normalize(input);
    assert.equal(out.mqttPort, '1883', JSON.stringify(empty));
    assert.equal(input.mqttPort, empty, 'copie : l\'entrée n\'est pas modifiée');
  }
  assert.equal(m.normalize({ mqttPort: '8883' }).mqttPort, '8883');
  assert.equal(m.normalize({}).mqttPort, '1883');
});

test('Lot 4 / revue réel — port laissé vide : testé ET enregistré à 1883', async (t) => {
  await withConfigurationPage(t, MQTT_FIXTURE, async (page, ctx) => {
    await fill(page);
    assert.equal(await page.locator('.configKey[data-l1key=mqttPort]').inputValue(), '');
    await page.locator('#bt_mqttTestSaveRestart').click();
    await page.waitForFunction(() => document.querySelector('#ul_mqttGuidedSteps li[data-step=restart]').dataset.state === 'done');
    const core = await page.evaluate(() => window.__core);
    assert.equal(core.saves[0].configuration.mqttPort, '1883');
    assert.equal(ctx.requests.find((r) => r.action === 'testMqttConnection').port, '1883');
  }, { initScript: FAKE_CORE_JS('ok') });
});

test('Lot 4 / revue réel — réglages figés au clic : le broker testé est celui enregistré ; champs verrouillés pendant la chaîne puis rendus', async (t) => {
  const locked = (page) => page.evaluate(() => ({
    host: document.querySelector('.configKey[data-l1key=mqttHost]').disabled,
    port: document.querySelector('.configKey[data-l1key=mqttPort]').disabled,
    password: document.querySelector('#in_mqttPassword').disabled,
    tls: document.querySelector('.configKey[data-l1key=mqttTls]').disabled,
    main: document.querySelector('#bt_mqttTestSaveRestart').disabled,
    testOnly: document.querySelector('#bt_testMqttConnection').getAttribute('aria-disabled'),
    reset: document.querySelector('#lnk_resetMqttForm').getAttribute('aria-disabled'),
  }));
  for (const mqttTest of [undefined, { state: 'ok', result: { status: 'error', error_code: 'auth_failed', message: 'x' } }]) {
    await withConfigurationPage(t, MQTT_FIXTURE, async (page, ctx) => {
      await fill(page);
      await page.locator('#bt_mqttTestSaveRestart').click();
      assert.deepEqual(await locked(page), { host: true, port: true, password: true, tls: true, main: true, testOnly: 'true', reset: 'true' });
      // Modification pendant la chaîne (script ou extension) : sans effet sur ce qui est testé et enregistré.
      await page.evaluate(() => { $('.configKey[data-l1key=mqttHost]').val('broker-b.test'); $('.configKey[data-l1key=mqttUser]').val('autre'); });
      // « Tester seulement » et la réinitialisation sont inopérants pendant la chaîne.
      await page.evaluate(() => { $('#bt_testMqttConnection').trigger('click'); $('#lnk_resetMqttForm').trigger('click'); });
      await page.waitForFunction(() => {
        const s = [...document.querySelectorAll('#ul_mqttGuidedSteps li')].map((li) => li.dataset.state);
        return s[2] === 'done' || s[0] === 'failed';
      });
      const tests = ctx.requests.filter((r) => r.action === 'testMqttConnection');
      assert.equal(tests.length, 1, 'un seul test : « Tester seulement » ignoré');
      assert.equal(tests[0].host, 'broker.test');
      assert.equal(tests[0].user, 'jeedom');
      const core = await page.evaluate(() => window.__core);
      if (mqttTest) {
        assert.deepEqual(core.saves, [], 'test en échec : rien enregistré');
      } else {
        assert.equal(core.saves[0].configuration.mqttHost, 'broker.test', 'le broker enregistré est le broker testé');
        assert.equal(core.saves[0].configuration.mqttUser, 'jeedom');
      }
      assert.deepEqual(await locked(page), { host: false, port: false, password: false, tls: false, main: false, testOnly: 'false', reset: 'false' });
      assert.deepEqual(ctx.errors, []);
    }, { initScript: FAKE_CORE_JS('ok'), mqttDelayMs: 400, mqttTest });
  }
});
