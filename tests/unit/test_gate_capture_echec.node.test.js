'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { pathToFileURL } = require('node:url');

const root = path.join(__dirname, '..', '..');
const runner = () => import(pathToFileURL(path.join(root, 'tests', 'e2e', 'gate', 'run-gate.mjs')).href);

function fakePage({ fails = false } = {}) {
  const calls = [];
  return {
    calls,
    async screenshot(options) {
      calls.push(options);
      if (fails) throw new Error('page-fermee');
    },
  };
}

test('capture d\'échec — aucune capture sans JEEDOM2HA_GATE_SCREENSHOT_DIR', async () => {
  const { captureFailureScreenshot } = await runner();
  const page = fakePage();
  assert.equal(await captureFailureScreenshot(page, { dir: undefined }), null);
  assert.equal(await captureFailureScreenshot(page, { dir: '' }), null);
  assert.deepEqual(page.calls, []);
});

test('capture d\'échec — failure.png pleine page dans le dossier indiqué, hors du dépôt', async () => {
  const { captureFailureScreenshot } = await runner();
  const page = fakePage();
  const dir = path.join(os.tmpdir(), 'j2ha-gate-capture');
  const file = await captureFailureScreenshot(page, { dir, repoRoot: root });
  assert.equal(file, path.join(dir, 'failure.png'));
  assert.equal(page.calls.length, 1);
  assert.equal(page.calls[0].path, file);
  assert.equal(page.calls[0].fullPage, true);
});

test('capture d\'échec — un dossier dans le dépôt est refusé', async () => {
  const { captureFailureScreenshot } = await runner();
  for (const dir of [root, path.join(root, 'tests', 'e2e', 'gate', 'captures')]) {
    const page = fakePage();
    assert.equal(await captureFailureScreenshot(page, { dir, repoRoot: root }), null);
    assert.deepEqual(page.calls, []);
  }
});

test('capture d\'échec — sans page ou si la capture échoue, rien n\'est levé', async () => {
  const { captureFailureScreenshot } = await runner();
  const dir = path.join(os.tmpdir(), 'j2ha-gate-capture');
  assert.equal(await captureFailureScreenshot(undefined, { dir, repoRoot: root }), null);
  assert.equal(await captureFailureScreenshot(fakePage({ fails: true }), { dir, repoRoot: root }), null);
});

test('capture d\'échec — un dossier extérieur qui est un lien vers le dépôt est refusé', async () => {
  const { captureFailureScreenshot } = await runner();
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'j2ha-gate-lien-'));
  try {
    const link = path.join(base, 'vers-depot');
    fs.symlinkSync(root, link, 'dir');
    for (const dir of [link, path.join(link, 'captures-absentes')]) {
      const page = fakePage();
      assert.equal(await captureFailureScreenshot(page, { dir, repoRoot: root }), null);
      assert.deepEqual(page.calls, []);
    }
    assert.equal(fs.existsSync(path.join(root, 'captures-absentes')), false);
  } finally {
    fs.rmSync(base, { recursive: true, force: true });
  }
});

test('capture d\'échec — un failure.png qui est un lien symbolique est refusé', async () => {
  const { captureFailureScreenshot } = await runner();
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'j2ha-gate-png-'));
  try {
    fs.symlinkSync(path.join(base, 'ailleurs.png'), path.join(base, 'failure.png'));
    const page = fakePage();
    assert.equal(await captureFailureScreenshot(page, { dir: base, repoRoot: root }), null);
    assert.deepEqual(page.calls, []);
  } finally {
    fs.rmSync(base, { recursive: true, force: true });
  }
});

test('capture d\'échec — le dossier absent est créé hors du dépôt', async () => {
  const { captureFailureScreenshot } = await runner();
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'j2ha-gate-neuf-'));
  try {
    const dir = path.join(base, 'a', 'b');
    const page = fakePage();
    assert.equal(await captureFailureScreenshot(page, { dir, repoRoot: root }), path.join(dir, 'failure.png'));
    assert.equal(fs.statSync(dir).isDirectory(), true);
  } finally {
    fs.rmSync(base, { recursive: true, force: true });
  }
});

test('capture d\'échec — déclenchée aussi par un FAIL sans exception visible avant fermeture', async () => {
  const { failureVisibleBeforeSeal } = await runner();
  const ok = { failure: undefined, consoleErrors: [], journal: { failed: false } };
  assert.equal(failureVisibleBeforeSeal(ok), false);
  assert.equal(failureVisibleBeforeSeal({ ...ok, failure: new Error('x') }), true);
  assert.equal(failureVisibleBeforeSeal({ ...ok, consoleErrors: ['erreur'] }), true);
  assert.equal(failureVisibleBeforeSeal({ ...ok, journal: { failed: true } }), true);
});

test('capture d\'échec — un seul point d\'appel dans le lanceur', () => {
  const source = fs.readFileSync(path.join(root, 'tests', 'e2e', 'gate', 'run-gate.mjs'), 'utf8');
  assert.equal(source.match(/await captureFailureScreenshot\(/g).length, 1);
});
