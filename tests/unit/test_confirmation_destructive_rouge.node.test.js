'use strict';
// Preuve terrain 25.8 (2026-10-19) : sur la box, le bouton « Exclure la pièce » (btn-danger) s'affichait vert. Le thème du cœur
// force `.modal-footer .btn.bootbox-accept` en vert avec `!important`. Une confirmation destructive retire la classe
// `bootbox-accept` de son bouton : le rouge btn-danger du thème s'applique, sans CSS ajouté.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const src = fs.readFileSync(path.join(__dirname, '..', '..', 'desktop/js/jeedom2ha.js'), 'utf8');
const body = src.slice(src.indexOf('function confirmHaPublishAction'), src.indexOf('function executeHaAction'));

function run(confirmClass) {
  const removed = [];
  const found = [];
  const dialog = {
    on() {},
    find(sel) { found.push(sel); return { removeClass(c) { removed.push(c); return this; } }; },
  };
  const ctx = { bootbox: { dialog: (opts) => { ctx.opts = opts; return dialog; } }, window: {} };
  vm.createContext(ctx);
  vm.runInContext(body + '\nconfirmHaPublishAction("t","m","Go",function(){},function(){},' + JSON.stringify(confirmClass) + ');', ctx);
  return { removed, found, opts: ctx.opts };
}

test('confirmation destructive : la classe bootbox-accept est retirée du bouton btn-danger', () => {
  const r = run('btn-danger');
  assert.equal(r.opts.buttons.confirm.className, 'btn-danger');
  assert.deepEqual(r.found, ['.modal-footer .btn-danger.bootbox-accept']);
  assert.deepEqual(r.removed, ['bootbox-accept']);
});

test('confirmation non destructive : rien n\'est retiré (couleur du thème inchangée)', () => {
  const r = run('btn-primary');
  assert.deepEqual(r.removed, []);
});
