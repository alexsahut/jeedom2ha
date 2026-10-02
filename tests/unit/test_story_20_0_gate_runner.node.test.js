'use strict';
const test = require('node:test'); const assert = require('node:assert/strict'); const path = require('node:path'); const { pathToFileURL } = require('node:url');
const mod = () => import(pathToFileURL(path.join(__dirname, '..', 'e2e', 'gate', 'run-gate.mjs')).href);
test('story 20-0 — contrôle AC4 des artefacts', async () => { const { artifactsContain } = await mod(); assert.equal(artifactsContain(['faux-secret', 'config-privee'], ['rapport sans valeur']), false); assert.equal(artifactsContain(['faux-secret'], ['rapport faux-secret']), true); });
