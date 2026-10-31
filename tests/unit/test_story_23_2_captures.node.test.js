'use strict';
// Story 23.2 — outillage de captures : logique pure (pas de navigateur, pas de box, pas de secret réel).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const ROOT = path.resolve(__dirname, '..', '..');
const load = (rel) => import(pathToFileURL(path.join(ROOT, 'tests/e2e/captures', rel)).href);

const ENV = [
  'JEEDOM_URL=http://demo-jeedom.invalid',
  'JEEDOM_USER=j2ha-captures',
  'JEEDOM_PASSWORD=fake-password-jeedom',
  'HA_URL=http://demo-ha.invalid:8123',
  'HA_USER=j2ha-captures',
  'HA_PASSWORD=fake-password-ha',
  'JEEDOM_DEMO_TARGET=demo',
].join('\n');

test('storyboard : 8 lignes + capture HA, marqueurs présents dans la documentation, vidéo ≤ 2 min', async () => {
  const sb = await load('lib/storyboard.mjs');
  assert.deepEqual(sb.VIEWPORT, { width: 1280, height: 720 });
  assert.equal(sb.COLOR_SCHEME, 'light');
  assert.equal(sb.LOCALE, 'fr-FR');
  assert.deepEqual(sb.SHOTS.map((s) => s.id), [1, 2, 3, 4, 5, 6, 7, 8, 9]);
  assert.equal(new Set([...sb.SHOTS, ...sb.EXTRA_SHOTS].map((s) => s.file)).size, sb.SHOTS.length + sb.EXTRA_SHOTS.length);
  for (const shot of sb.SHOTS.filter((s) => s.marker)) {
    const doc = fs.readFileSync(path.join(ROOT, 'docs/fr_FR', shot.doc), 'utf8');
    assert.ok(doc.includes(`<!-- CAPTURE-A-PRENDRE: ${shot.marker} -->`), `marqueur absent : ${shot.marker}`);
  }
  assert.ok(sb.plannedHoldSeconds() > 0 && sb.plannedHoldSeconds() <= sb.VIDEO_MAX_SECONDS - 30);
  assert.equal(sb.VIDEO_MAX_SECONDS, 120);
});

test('démo : les noms du storyboard existent dans populate_demo.py (D2)', async () => {
  const sb = await load('lib/storyboard.mjs');
  const demo = fs.readFileSync(path.join(ROOT, 'scripts/demo/populate_demo.py'), 'utf8');
  for (const name of [sb.DEMO.searchRoom, sb.DEMO.blockedRoom, sb.DEMO.excludedRoom,
    sb.DEMO.blockedEquipment, sb.DEMO.publishedEquipment, sb.DEMO.haLight]) {
    assert.ok(demo.includes(`"${name}"`), `absent de la démo : ${name}`);
  }
});

test('config : lecture valide, secrets recensés, aucune valeur dans les erreurs', async () => {
  const cfg = await load('lib/config.mjs');
  const parsed = cfg.validateConfig(cfg.parseEnvText(ENV));
  assert.equal(parsed.jeedom.origin, 'http://demo-jeedom.invalid');
  assert.ok(parsed.secrets.includes('fake-password-ha') && parsed.secrets.includes('demo-ha.invalid:8123'));
  assert.throws(() => cfg.validateConfig(cfg.parseEnvText(ENV.replace('JEEDOM_DEMO_TARGET=demo', ''))), /cles-manquantes: JEEDOM_DEMO_TARGET/);
  assert.throws(() => cfg.validateConfig(cfg.parseEnvText(ENV.replace('=demo', '=prod'))), /cible-non-confirmee-demo/);
  assert.throws(() => cfg.validateConfig(cfg.parseEnvText(ENV.replace('http://demo-ha', 'ftp://demo-ha'))), (e) => /url-invalide: HA_URL/.test(e.message) && !e.message.includes('demo-ha'));
  assert.equal(cfg.redact('connexion fake-password-ha ok', parsed.secrets), 'connexion «masqué» ok');
});

test('config : .env dans le dépôt refusé, hors dépôt accepté', async () => {
  const cfg = await load('lib/config.mjs');
  assert.throws(() => cfg.assertEnvOutsideRepo(path.join(ROOT, 'tests/x.env'), ROOT), /env-dans-le-depot/);
  assert.doesNotThrow(() => cfg.assertEnvOutsideRepo('/etc/j2ha-captures.env', ROOT));
});

test('CC-48 : fuites détectées sans citer de valeur', async () => {
  const s = await load('lib/safety.mjs');
  assert.deepEqual(s.findLeaks('Lumière Salon — Publié — 4.6.1'), []);
  assert.deepEqual(s.findLeaks('broker 192.168.1.10'), ['adresse-ip']);
  assert.ok(s.findLeaks('http://demo-jeedom.invalid/x').includes('url'));
  assert.ok(s.findLeaks('maison.lan').includes('nom-hote-local'));
  assert.ok(s.findLeaks('clé 0123456789abcdef0123456789abcdef').includes('jeton-long'));
  assert.deepEqual(s.findLeaks('mot de passe fake-password-ha', ['fake-password-ha']), ['secret-configure']);
});

test('D1 : thème clair prouvé par le fond effectif, échec fermé sinon', async () => {
  const s = await load('lib/safety.mjs');
  assert.equal(s.isLightBackground('rgb(255, 255, 255)'), true);
  assert.equal(s.isLightBackground('rgb(244, 245, 247)'), true);
  assert.equal(s.isLightBackground('rgb(30, 30, 30)'), false);
  assert.equal(s.isLightBackground('rgba(0, 0, 0, 0)'), false);
  assert.equal(s.isLightBackground(''), false);
  assert.equal(s.isLightBackground('var(--bg)'), false);
});

test('manifeste : version, date, viewport, empreintes ; aucun secret', async () => {
  const s = await load('lib/safety.mjs');
  const files = [{ id: 1, file: 'page-principale.png', sha256: s.sha256(Buffer.from('x')), bytes: 1 }];
  const m = s.buildManifest({ pluginVersion: '1.2.0', sourceCommit: 'abc1234', date: '2026-10-21', files, command: 'node run' });
  assert.deepEqual(m.viewport, { width: 1280, height: 720 });
  assert.equal(m.plugin_version, '1.2.0');
  assert.equal(m.generated_on, '2026-10-21');
  assert.equal(m.theme, 'light');
  assert.doesNotThrow(() => s.assertManifestClean(m, ['fake-password-ha']));
  assert.throws(() => s.assertManifestClean({ ...m, regenerate: 'avec fake-password-ha' }, ['fake-password-ha']), /manifeste-non-propre/);
  assert.throws(() => s.buildManifest({ date: '2026-10-21', files, command: 'x' }), /version-plugin-manquante/);
});

test('plan hors-ligne : aucune connexion, aucun navigateur', async () => {
  const run = await load('run-captures.mjs');
  const plan = run.buildPlan({ only: null, skipHa: false });
  assert.equal(plan.shots.length, 10);
  assert.equal(plan.video.max_seconds, 120);
  assert.equal(run.buildPlan({ only: 'video', skipHa: false }).shots.length, 0);
  assert.equal(run.buildPlan({ only: 'shots', skipHa: true }).video, null);
});

test('--skip-ha : clés HA facultatives, étapes vidéo HA retirées', async () => {
  const cfg = await load('lib/config.mjs');
  const sb = await load('lib/storyboard.mjs');
  const run = await load('run-captures.mjs');
  const jeedomOnly = ENV.split('\n').filter((line) => !line.startsWith('HA_')).join('\n');
  assert.throws(() => cfg.validateConfig(cfg.parseEnvText(jeedomOnly)), /cles-manquantes: HA_URL, HA_USER, HA_PASSWORD/);
  const parsed = cfg.validateConfig(cfg.parseEnvText(jeedomOnly), { requireHa: false });
  assert.equal(parsed.homeAssistant, null);
  assert.ok(!parsed.secrets.some((s) => s.includes('demo-ha')));
  const ids = sb.videoSteps({ skipHa: true }).map((s) => s.id);
  assert.deepEqual(ids, ['plugins', 'dependances', 'relire', 'piece', 'equipement']);
  assert.equal(sb.videoSteps({}).length, sb.VIDEO_STEPS.length);
  const plan = run.buildPlan({ only: 'video', skipHa: true });
  assert.equal(plan.video.steps.length, 5);
});

test('manifeste : une régénération partielle conserve la section précédente avec sa propre date', async () => {
  const s = await load('lib/safety.mjs');
  const files = [{ id: 1, file: 'a.png', sha256: 'x', bytes: 1 }];
  const first = s.buildManifest({ pluginVersion: '1.2.0', sourceCommit: 'aaa', date: '2026-10-21', files, command: 'c' });
  const videoOnly = s.mergeManifest(first, s.buildManifest({
    pluginVersion: '1.3.0', sourceCommit: 'bbb', date: '2026-10-22', files: [], command: 'c', video: { file: 'v.webm', seconds: 90 },
  }));
  assert.deepEqual(videoOnly.files, files);
  assert.equal(videoOnly.files_generated.plugin_version, '1.2.0');
  assert.equal(videoOnly.video.generated.generated_on, '2026-10-22');
  assert.equal(videoOnly.plugin_version, '1.3.0');
  const shotsOnly = s.mergeManifest(videoOnly, s.buildManifest({ pluginVersion: '1.4.0', date: '2026-10-23', files, command: 'c' }));
  assert.equal(shotsOnly.video.generated.generated_on, '2026-10-22');
  assert.equal(s.mergeManifest(null, first).files.length, 1);
});

test('CC-48 : le masquage du broker est injecté dès la création des pages (avant tout rendu enregistré)', () => {
  const src = fs.readFileSync(path.join(ROOT, 'tests/e2e/captures/run-captures.mjs'), 'utf8');
  assert.ok(/addInitScript\([\s\S]*?MASK_CSS/.test(src));
  for (const hidden of ['mqttHost', 'mqttUser', 'in_mqttPassword', 'span_healthMqttBroker']) assert.ok(src.includes(hidden), hidden);
  // la confirmation de « Relire Jeedom » est cliquée et la requête scanTopology attendue
  assert.ok(src.includes('data-bb-handler="confirm"') && src.includes('scanTopology'));
});

test('23.2 — les noms de clés du .env créé par clawbox sont acceptés comme alias', async () => {
  const cfg = await load('lib/config.mjs');
  const clawboxEnv = [
    'JEEDOM_BASE_URL=http://demo-jeedom.invalid',
    'JEEDOM_USERNAME=j2ha-captures',
    'JEEDOM_PASSWORD=fake-password-jeedom',
    'HOME_ASSISTANT_BASE_URL=http://demo-ha.invalid:8123',
    'HOME_ASSISTANT_USERNAME=j2ha-captures',
    'HOME_ASSISTANT_PASSWORD=fake-password-ha',
    'JEEDOM_DEMO_TARGET=demo',
  ].join('\n');
  const out = cfg.validateConfig(cfg.parseEnvText(clawboxEnv));
  assert.equal(out.jeedom.origin, 'http://demo-jeedom.invalid');
  assert.equal(out.jeedom.user, 'j2ha-captures');
  assert.equal(out.homeAssistant.origin, 'http://demo-ha.invalid:8123');
  assert.equal(out.homeAssistant.password, 'fake-password-ha');
  assert.ok(out.secrets.includes('fake-password-ha'));
  // Sans le garde-fou de cible, refus (le fichier de clawbox doit recevoir la ligne JEEDOM_DEMO_TARGET=demo).
  assert.throws(() => cfg.validateConfig(cfg.parseEnvText(clawboxEnv.replace('JEEDOM_DEMO_TARGET=demo', ''))),
    /cles-manquantes: JEEDOM_DEMO_TARGET/);
  // Une clé canonique présente mais vide l'emporte sur l'alias : refus, jamais de repli silencieux sur l'ancienne cible.
  assert.throws(() => cfg.validateConfig(cfg.parseEnvText(clawboxEnv + '\nJEEDOM_URL=')), /cles-manquantes: JEEDOM_URL/);
});

test('23.2 — connexion Jeedom : bouton du cœur 4.6.1 (#bt_login_validate), jamais #bt_login', () => {
  const src = fs.readFileSync(path.join(ROOT, 'tests/e2e/captures/run-captures.mjs'), 'utf8');
  assert.match(src, /JEEDOM_LOGIN_BUTTON = '#bt_login_validate'/);
  assert.doesNotMatch(src, /'#bt_login'/);
  assert.match(src, /jeedom-changement-mot-de-passe-exige/);
});


test('23.2 — page de connexion Jeedom : masquage CC-48 oui, gel des animations non (sinon la connexion n\'aboutit pas)', () => {
  const src = fs.readFileSync(path.join(ROOT, 'tests/e2e/captures/run-captures.mjs'), 'utf8');
  assert.match(src, /JEEDOM_LOGIN_FORM = '#in_login_username'/);
  assert.match(src, /document\.querySelector\(loginSelector\) \? mask : `\$\{freeze\}\$\{mask\}`/);
  assert.match(src, /\{ freeze: FREEZE_CSS, mask: MASK_CSS, loginSelector: JEEDOM_LOGIN_FORM \}/);
  assert.doesNotMatch(src, /css: `\$\{FREEZE_CSS\}\$\{MASK_CSS\}`/);
});
