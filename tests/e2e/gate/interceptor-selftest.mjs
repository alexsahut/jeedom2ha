#!/usr/bin/env node
/**
 * Story 20.0 (incrément B2b) — auto-test local de l'intercepteur (AC1).
 *
 * Ce script ne contacte jamais la box : le seul serveur est créé sur 127.0.0.1
 * avec un port éphémère. Il est volontairement séparé du relevé terrain et doit
 * être lancé explicitement, après relecture, avec `node interceptor-selftest.mjs`.
 */

import http from 'node:http';
import { loadPlaywright } from './lib/playwright.mjs';
import { installInterceptor } from './lib/interceptor.mjs';
import { createState } from './lib/simulate.mjs';

const PLUGIN_AJAX = '/plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php';

function json(state, result) {
  return JSON.stringify({ state, result: { status: 'ok', payload: result } });
}

function previewPayload() {
  return {
    mapped: true,
    covered: true,
    auto: { ha_entity_type: 'light', should_publish: true },
    overridden: {
      ha_entity_type: 'switch',
      projection_validity: { is_valid: false, reason_code: 'missing_capability' },
      should_publish: false,
    },
  };
}

function mappingPayload() {
  return {
    jeedom_eq_id: 1,
    eq_name: 'Local',
    mapped: true,
    sync_status: { synced_should_publish: false, current_should_publish: false, override_pending: false },
    commands: [
      {
        jeedom_cmd_id: 2,
        cmd_name: 'Etat',
        effective_ha: 'light',
        override_applied: false,
      },
    ],
  };
}

function pageHtml(origin) {
  const endpoint = `${origin}${PLUGIN_AJAX}`;
  const websocket = origin.replace('http://', 'ws://') + '/socket';
  return `<!doctype html><meta charset="utf-8"><title>gate selftest</title>
<script>
(() => {
  const endpoint = ${JSON.stringify(endpoint)};
  const websocket = ${JSON.stringify(websocket)};
  const form = (action, fields = {}) => new URLSearchParams({ action, ...fields }).toString();
  const post = async (action, fields = {}) => {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: form(action, fields),
    });
    return response.json();
  };
  const attempted = (promise) => Promise.resolve(promise).then(() => false, () => true);
  const xhr = () => new Promise((resolve) => {
    const request = new XMLHttpRequest();
    request.addEventListener('loadend', () => resolve(true));
    request.open('POST', endpoint);
    request.setRequestHeader('content-type', 'application/x-www-form-urlencoded');
    request.send(form('scanTopology'));
  });
  const image = () => new Promise((resolve) => {
    const node = new Image();
    node.onload = node.onerror = () => resolve(true);
    node.src = endpoint + '?action=scanTopology';
  });
  const frame = () => new Promise((resolve) => {
    const node = document.createElement('iframe');
    node.addEventListener('load', () => setTimeout(resolve, 25), { once: true });
    node.srcdoc = '<form method="post" action="' + endpoint + '"><input name="action" value="saveFilteringConfig"></form><script>document.forms[0].submit()<\\/script>';
    document.body.append(node);
  });
  const socket = () => new Promise((resolve) => {
    const ws = new WebSocket(websocket);
    ws.onerror = ws.onclose = () => resolve(true);
    setTimeout(resolve, 250);
  });

  window.__selftest = (async () => {
    const forbidden = [];
    for (const action of ['scanTopology', 'executeHaAction', 'saveFilteringConfig', 'forceMqttManagerImport', 'testMqttConnection']) {
      forbidden.push(await attempted(post(action)));
    }
    forbidden.push(await attempted(post('saveMappingOverride', { eqId: '9', cmdId: '2', haEntityType: 'switch' })));
    forbidden.push(await attempted(post('revertMappingOverride', { eqId: '9', cmdId: '2' })));
    forbidden.push(await attempted(fetch(endpoint + '?action=scanTopology')));
    forbidden.push(await xhr());
    forbidden.push(navigator.sendBeacon(endpoint, form('executeHaAction')));
    await frame();
    await image();
    forbidden.push(await attempted(fetch('/core/api/jeeApi.php', { method: 'POST', body: 'action=write' })));
    forbidden.push(await attempted(fetch(endpoint, { method: 'POST', body: 'action=getBridgeStatus&action=scanTopology' })));
    window.open(endpoint + '?action=executeHaAction', '_blank', 'noopener');
    await new Promise((resolve) => setTimeout(resolve, 25));
    await socket();
    const serviceWorkerBlocked = await attempted(navigator.serviceWorker.register('/selftest-sw.js'));
    forbidden.push(await attempted(fetch('/core/ajax/user.ajax.php', { method: 'POST', body: 'action=login' })));

    const preview = await post('previewMappingOverride', { eqId: '1', cmdId: '2', haEntityType: 'switch' });
    const saved = await post('saveMappingOverride', { eqId: '1', cmdId: '2', haEntityType: 'switch' });
    const derived = await post('getMappingOverrides', { eqId: '1' });
    const reverted = await post('revertMappingOverride', { eqId: '1', cmdId: '2' });
    const real = await post('getMappingOverrides', { eqId: '1' });
    const bascule = await post('previewMappingOverride', { eqId: '1', cmdId: '2', haEntityType: 'light' });

    return { forbidden, serviceWorkerBlocked, preview, saved, derived, reverted, real, bascule };
  })();
})();
</script>`;
}

function makeServer() {
  const requests = [];
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://127.0.0.1');
    let body = '';
    req.setEncoding('utf8');
    req.on('data', (chunk) => { body += chunk; });
    req.on('end', () => {
      const params = new URLSearchParams(body);
      const action = url.searchParams.get('action') ?? params.get('action');
      requests.push({ method: req.method, path: url.pathname, action });

      if (url.pathname === '/index.php' && url.searchParams.get('v') === 'd') {
        const content = pageHtml(`http://${req.headers.host}`);
        res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'content-length': Buffer.byteLength(content) });
        res.end(content);
        return;
      }

      let content;
      if (url.pathname === PLUGIN_AJAX && action === 'previewMappingOverride') {
        content = json('ok', previewPayload());
      } else if (url.pathname === PLUGIN_AJAX && action === 'getMappingOverrides') {
        content = json('ok', mappingPayload());
      } else if (url.pathname === PLUGIN_AJAX && action === 'getBridgeStatus') {
        content = json('ok', { connected: true });
      } else {
        content = json('error', { message: 'requete inattendue' });
      }
      res.writeHead(200, { 'content-type': 'application/json', 'content-length': Buffer.byteLength(content) });
      res.end(content);
    });
  });
  // Un upgrade ne doit jamais être atteint : routeWebSocket() ferme sans se connecter.
  // Le consigner le rend visible si cette garantie régressait.
  server.on('upgrade', (req, socket) => {
    requests.push({ method: 'WEBSOCKET', path: new URL(req.url, 'http://127.0.0.1').pathname, action: null });
    socket.destroy();
  });
  return { server, requests };
}

function listen(server) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      server.off('error', reject);
      resolve(server.address().port);
    });
  });
}

function close(server) {
  return new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
}

function report(label, condition, failures) {
  console.log(`${condition ? 'PASS' : 'FAIL'} ${label}`);
  if (!condition) failures.push(label);
}

async function main() {
  const { chromium } = loadPlaywright();
  const { server, requests } = makeServer();
  const failures = [];
  let browser;

  try {
    const port = await listen(server);
    const origin = `http://127.0.0.1:${port}`;
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ serviceWorkers: 'block' });
    const simState = createState();
    const journal = { entries: [], failed: false, failures: [] };
    const ctx = {
      origin,
      loginAttempts: 0,
      declaredEquipments: { '1': { commands: ['2'] } },
      lastPreviewType: simState.lastPreviewType,
    };

    await installInterceptor(context, {
      ctx,
      simState,
      journal,
      declaredBascules: [{ eqId: '1', cmdId: '2', haEntityType: 'light' }],
    });

    const page = await context.newPage();
    await page.goto(`${origin}/index.php?v=d&m=jeedom2ha&p=jeedom2ha`, { waitUntil: 'load' });
    const results = await page.evaluate(() => window.__selftest);

    const forbiddenActions = new Set([
      'scanTopology', 'executeHaAction', 'saveFilteringConfig', 'forceMqttManagerImport', 'testMqttConnection',
      'saveMappingOverride', 'revertMappingOverride', 'login',
    ]);
    const serverReceivedForbidden = requests.some(
      (request) => forbiddenActions.has(request.action) || request.path === '/core/api/jeeApi.php' || request.path === '/socket'
    );
    report('aucune ecriture, effet de bord, connexion, core API ou WebSocket n atteint le serveur', !serverReceivedForbidden, failures);
    report('les lectures du flux ont atteint le serveur',
      requests.filter((request) => request.action === 'previewMappingOverride').length === 2
        && requests.filter((request) => request.action === 'getMappingOverrides').length === 2,
      failures);
    report('toutes les tentatives HTTP interdites sont bloquees', results.forbidden.every(Boolean), failures);
    report('service worker bloque', results.serviceWorkerBlocked, failures);
    report('journal en echec avec une entree par tentative interdite', journal.failed && journal.failures.length >= 18, failures);

    const derivedRow = results.derived.result.payload.commands[0];
    report('relecture derivee : override, type et diagnostic simules',
      derivedRow.override_applied === true
        && derivedRow.effective_ha === 'switch'
        && derivedRow.diagnostic?.projection_validity?.is_valid === false,
      failures);
    report('relecture apres retour : arbre reel', results.real.result.payload.commands[0].override_applied === false, failures);
    report('apercu de bascule declaree pret',
      results.bascule.result.payload.overridden.projection_validity.is_valid === true
        && results.bascule.result.payload.overridden.should_publish === true,
      failures);
    report('reponses fulfill JSON lisibles malgre content-length reel',
      results.preview.state === 'ok'
        && results.saved.result.payload.override_applied === true
        && results.reverted.result.payload.scope === 'command'
        && results.derived.state === 'ok'
        && results.real.state === 'ok'
        && results.bascule.state === 'ok',
      failures);

    console.log(`${failures.length === 0 ? 'PASS' : 'FAIL'} bilan (${failures.length} echec(s))`);
    process.exitCode = failures.length === 0 ? 0 : 1;
    await context.close();
  } finally {
    if (browser) await browser.close();
    await close(server);
  }
}

main().catch((error) => {
  console.error(`FAIL exception: ${error.message}`);
  process.exitCode = 1;
});
