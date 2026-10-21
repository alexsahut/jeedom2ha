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
