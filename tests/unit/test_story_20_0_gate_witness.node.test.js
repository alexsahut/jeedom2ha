'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const MODULE = path.join(__dirname, '..', 'e2e', 'gate', 'lib', 'box-witness.mjs');
const load = () => import(pathToFileURL(MODULE).href);

function witness(overrides = { sha256: 'a', mtime: '2026-10-02 10:00:00.000000000 +0000', content: '{}', present: false, json: null }) {
  return { readable: true, overrides, daemon: { pid: '42', startedAt: 'Wed Oct  2 10:00:00 2026', logLevel: 'info' }, logs: { daemon: { size: 10, firstTimestamp: '[2026-10-02 10:00:00]' }, plugin: { size: 20, firstTimestamp: '[2026-10-02 10:00:00]' } } };
}

test('story 20-0 — témoin box pur et injectable', async (t) => {
  const m = await load();
  await t.test('validation stricte PID et bornes', () => {
    assert.equal(m.validPid('123'), true); assert.equal(m.validPid('12;id'), false);
    assert.equal(m.validBoxTime('2026-10-02 10:00:00'), true); assert.equal(m.validBoxTime('2026-10-02; id'), false);
    assert.throws(() => m.remoteWindowCommand('/x', 'ERROR', -1, 10));
    assert.throws(() => m.remoteWindowCommand('/x', 'ERROR', 11, 10));
    assert.match(m.remoteWindowCommand('/x', 'ERROR', 10, 42), /tail -c \+11/);
  });
  await t.test('parse le schéma v1/v2 et refuse un JSON invalide', () => {
    assert.equal(m.parseOverrides(null).present, false);
    assert.equal(m.parseOverrides('{"schema_version":1,"overrides":{}}').json.equipment_overrides, undefined);
    assert.equal(m.parseOverrides('{"schema_version":2,"overrides":{},"equipment_overrides":{}}').present, true);
    assert.throws(() => m.parseOverrides('{')); assert.throws(() => m.parseOverrides('{"schema_version":2,"overrides":{}}'));
  });
  await t.test('refuse les overrides de commande et équipement déclarés', () => {
    const w = witness({ present: true, json: { schema_version: 2, overrides: { '1:2': {} }, equipment_overrides: { '3': {} } } });
    assert.throws(() => m.assertNoOverrideOn(w, ['1']));
    assert.throws(() => m.assertNoOverrideOn(w, ['3']));
    assert.doesNotThrow(() => m.assertNoOverrideOn(w, ['9']));
  });
  await t.test('compare tout écart AC2/AC3', () => {
    const before = witness(); const after = witness();
    after.overrides = { ...after.overrides, sha256: 'b', mtime: 'other', content: 'other' }; after.daemon = { ...after.daemon, pid: '43', startedAt: 'other', logLevel: 'warning' };
    after.logs.daemon = { size: 9, firstTimestamp: '[2026-10-02 10:01:00]' };
    const diffs = m.compareWitness(before, after);
    assert.ok(diffs.includes('overrides-sha256')); assert.ok(diffs.includes('overrides-mtime')); assert.ok(diffs.includes('overrides-content')); assert.ok(diffs.includes('daemon-pid')); assert.ok(diffs.includes('daemon-demarrage'));
    assert.ok(diffs.includes('niveau-journal-invalide')); assert.ok(diffs.includes('journal-daemon-troncature-taille'));
    assert.ok(diffs.includes('journal-daemon-troncature-horodatage'));
    const nullTimestamp = witness(); nullTimestamp.logs.plugin.firstTimestamp = null;
    assert.ok(m.compareWitness(witness(), nullTimestamp).includes('journal-plugin-illisible'));
    const unreadable = witness(); unreadable.readable = false;
    assert.ok(m.compareWitness(witness(), unreadable).includes('temoin-illisible'));
  });
  await t.test('takeWitness et countWindow utilisent uniquement l exécuteur injecté', async () => {
    const seen = [];
    const run = async (command) => { seen.push(command); if (command.startsWith('pgrep')) return '42\n'; if (command.startsWith('ps -o lstart')) return 'Wed Oct  2 10:00:00 2026\n'; if (command.startsWith('ps -o args')) return '--loglevel info\n'; if (command.startsWith('date')) return '2026-10-02 10:00:00\n'; if (command.includes('stat -c %s')) return '10\n'; if (command.includes('grep -m1')) return '[2026-10-02 10:00:00]\n'; if (command.includes('sha256sum') || command.includes('stat -c %y') || command.includes('cat ')) return '__ABSENT__\n'; return '0\n'; };
    const taken = await m.takeWitness({ run }); const after = { ...taken, logs: { daemon: { ...taken.logs.daemon, size: 20 }, plugin: { ...taken.logs.plugin, size: 30 } } }; const counts = await m.countWindow(taken, after, { run });
    assert.equal(taken.readable, true); assert.equal(taken.overrides.present, false); assert.equal(counts.daemonErrors, 0); assert.equal(counts.pluginErrors, 0); assert.ok(seen.every((command) => typeof command === 'string')); assert.ok(seen.some((command) => command.includes('[ -r')));
    const doublePid = await m.takeWitness({ run: async (command) => command.startsWith('pgrep') ? '1\n2\n' : run(command) });
    assert.equal(doublePid.readable, false);
    const emptyTimestamp = await m.takeWitness({ run: async (command) => command.includes('grep -m1') ? '' : run(command) });
    assert.equal(emptyTimestamp.readable, false);
  });

  await t.test('countWindow compte les octets ajoutés, y compris sans horodatage', async () => {
    const before = witness(); const after = witness(); after.logs.daemon.size = 17; after.logs.plugin.size = 29;
    const commands = [];
    await m.countWindow(before, after, { run: async (command) => { commands.push(command); return '0\n'; } });
    assert.ok(commands.every((command) => command.includes('tail -c +')));
    assert.ok(commands.every((command) => command.includes('| head -c ')));
    after.logs.daemon.size = 9;
    await assert.rejects(() => m.countWindow(before, after, { run: async () => '0\n' }), /bornes-journal-invalides/);
  });
});
