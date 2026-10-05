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
const EVENT_AJAX = '/core/ajax/event.ajax.php';
const REDIRECT_PNG = '/redirect.png';

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
  const changesEndpoint = ${JSON.stringify(`${origin}/core/ajax/event.ajax.php`)};
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
  const redirect = () => new Promise((resolve) => {
    const node = new Image();
    node.onload = node.onerror = () => resolve(true);
    node.src = ${JSON.stringify(REDIRECT_PNG)};
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
    for (const action of ['scanTopology', 'executeHaAction', 'saveFilteringConfig', 'forceMqttManagerImport', 'testMqttConnection']) {
      await attempted(post(action));
    }
    await attempted(post('saveMappingOverride', { eqId: '9', cmdId: '2', haEntityType: 'switch' }));
    await attempted(post('revertMappingOverride', { eqId: '9', cmdId: '2' }));
    await attempted(post('savePublicationOverride', { eqId: '9', publicationPolicy: 'exclude' }));
    await attempted(post('revertPublicationOverride', { eqId: '9' }));
    await attempted(fetch(endpoint + '?action=scanTopology'));
    await xhr();
    navigator.sendBeacon(endpoint, form('executeHaAction'));
    await frame();
    await image();
    await redirect();
    await attempted(fetch('/core/api/jeeApi.php', {
      method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: 'action=write',
    }));
    await attempted(fetch(endpoint, { method: 'POST', body: 'action=getBridgeStatus&action=scanTopology' }));
    window.open(endpoint + '?action=executeHaAction', '_blank', 'noopener');
    await new Promise((resolve) => setTimeout(resolve, 25));
    await socket();
    const serviceWorkerRegistration = await navigator.serviceWorker.register('/selftest-sw.js');
    await new Promise((resolve) => setTimeout(resolve, 500));
    const serviceWorkerRegistrations = await navigator.serviceWorker.getRegistrations();
    await attempted(fetch('/core/ajax/user.ajax.php', {
      method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: 'action=login',
    }));
    const changes = await fetch(changesEndpoint, {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: 'action=changes&datetime=0',
    }).then((response) => response.json());

    const preview = await post('previewMappingOverride', { eqId: '1', cmdId: '2', haEntityType: 'switch' });
    const saved = await post('saveMappingOverride', { eqId: '1', cmdId: '2', haEntityType: 'switch' });
    const derived = await post('getMappingOverrides', { eqId: '1' });
    const reverted = await post('revertMappingOverride', { eqId: '1', cmdId: '2' });
    const publicationSaved = await post('savePublicationOverride', { eqId: '1', publicationPolicy: 'exclude' });
    const publicationReverted = await post('revertPublicationOverride', { eqId: '1' });
    const real = await post('getMappingOverrides', { eqId: '1' });
    const bascule = await post('previewMappingOverride', { eqId: '1', cmdId: '2', haEntityType: 'light' });

    return {
      serviceWorkerRegistrationIsUndefined: serviceWorkerRegistration === undefined,
      serviceWorkerRegistrationsCount: serviceWorkerRegistrations.length,
      changes,
      preview,
      saved,
      derived,
      reverted,
      publicationSaved,
      publicationReverted,
      real,
      bascule,
    };
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
      const actions = [...url.searchParams.getAll('action'), ...params.getAll('action')];
      const action = actions.length === 1 ? actions[0] : null;
      requests.push({ method: req.method, path: url.pathname, actions });

      if (url.pathname === '/index.php' && url.searchParams.get('v') === 'd') {
        const content = pageHtml(`http://${req.headers.host}`);
        res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'content-length': Buffer.byteLength(content) });
        res.end(content);
        return;
      }

      // Ressource statique qui redirige vers une action interdite : si l'intercepteur
      // suivait cette redirection (le fetch interne ou un route.continue()), la cible
      // l'atteindrait directement.
      if (url.pathname === REDIRECT_PNG) {
        res.writeHead(302, { location: `${PLUGIN_AJAX}?action=scanTopology` });
        res.end();
        return;
      }

      // Document (page de connexion, zéro paramètre) qui redirige vers la même action
      // interdite : même garantie que REDIRECT_PNG, mais pour une navigation.
      if (url.pathname === '/index.php' && url.searchParams.size === 0) {
        res.writeHead(302, { location: `${PLUGIN_AJAX}?action=scanTopology` });
        res.end();
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
    requests.push({ method: 'WEBSOCKET', path: new URL(req.url, 'http://127.0.0.1').pathname, actions: [] });
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
  server.closeAllConnections();
  return new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
}

function report(label, condition, failures) {
  console.log(`${condition ? 'PASS' : 'FAIL'} ${label}`);
  if (!condition) failures.push(label);
}

function takeMatchingFailure(failures, expected) {
  const index = failures.findIndex(
    (entry) => entry.path === expected.path && entry.action === expected.action && entry.verdict === expected.verdict
      && (expected.reason === undefined || entry.reason === expected.reason)
  );
  return index === -1 ? null : failures.splice(index, 1)[0];
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
      declaredPublicationOverrides: { '1': { commands: [] } },
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

    // Document (page de connexion) qui redirige vers la même action interdite que
    // REDIRECT_PNG : la navigation doit échouer puisque l'intercepteur abandonne la
    // route avant tout fulfill, sans jamais joindre le serveur sur la cible.
    const redirectPage = await context.newPage();
    await redirectPage.goto(`${origin}/index.php`, { waitUntil: 'load' }).catch(() => {});
    await redirectPage.close();

    // Les éléments sans réponse attendue (beacon, popup, iframe, WebSocket) peuvent
    // encore être en file après evaluate(). La fermeture du contexte annule tout ce
    // qui resterait avant que le serveur et le journal soient inspectés.
    await page.waitForTimeout(1_500);
    await context.close();

    const forbiddenActions = new Set([
      'scanTopology', 'executeHaAction', 'saveFilteringConfig', 'forceMqttManagerImport', 'testMqttConnection',
      'saveMappingOverride', 'revertMappingOverride', 'login',
      'savePublicationOverride', 'revertPublicationOverride',
    ]);
    const serverReceivedForbidden = requests.some(
      (request) =>
        request.actions.some((action) => forbiddenActions.has(action))
        || request.actions.length > 1
        || request.path === '/core/api/jeeApi.php'
        || request.path === '/socket'
    );
    report('aucune ecriture, effet de bord, connexion, core API ou WebSocket n atteint le serveur', !serverReceivedForbidden, failures);
    report('les lectures du flux ont atteint le serveur',
      requests.filter((request) => request.actions.length === 1 && request.actions[0] === 'previewMappingOverride').length === 2
        && requests.filter((request) => request.actions.length === 1 && request.actions[0] === 'getMappingOverrides').length === 2,
      failures);
    report('service worker : register retourne undefined', results.serviceWorkerRegistrationIsUndefined, failures);
    report('service worker : aucune inscription apres 500 ms', results.serviceWorkerRegistrationsCount === 0, failures);
    report('service worker : script jamais recu par le serveur',
      !requests.some((request) => request.path === '/selftest-sw.js'),
      failures);
    report('changes est simule : serveur non atteint et liste vide recue par la page',
      !requests.some((request) => request.path === EVENT_AJAX && request.actions.includes('changes'))
        && results.changes.state === 'ok'
        && Array.isArray(results.changes.result.result)
        && results.changes.result.result.length === 0
        && typeof results.changes.result.datetime === 'number',
      failures);
    report('journal : changes marque lecture-simulee',
      journal.entries.some(
        (entry) => entry.path === EVENT_AJAX && entry.action === 'changes' && entry.verdict === 'lecture-simulee',
      ),
      failures);
    report('redirection depuis une ressource statique ou un document : cible jamais atteinte par le serveur',
      !requests.some((request) => request.path === PLUGIN_AJAX && request.method === 'GET' && request.actions.includes('scanTopology')),
      failures);

    const expectedFailures = [
      ...['scanTopology', 'executeHaAction', 'saveFilteringConfig', 'forceMqttManagerImport', 'testMqttConnection', 'saveMappingOverride', 'revertMappingOverride', 'savePublicationOverride', 'revertPublicationOverride']
        .map((action) => ({ path: PLUGIN_AJAX, action, verdict: 'block-fail' })),
      { path: PLUGIN_AJAX, action: 'scanTopology', verdict: 'block-fail' },
      { path: PLUGIN_AJAX, action: 'scanTopology', verdict: 'block-fail' },
      // sendBeacon() impose text/plain : le refus survient avant l'extraction de l'action.
      { path: PLUGIN_AJAX, action: null, verdict: 'block-fail' },
      { path: PLUGIN_AJAX, action: 'saveFilteringConfig', verdict: 'block-fail' },
      { path: PLUGIN_AJAX, action: 'scanTopology', verdict: 'block-fail' },
      { path: '/core/api/jeeApi.php', action: 'write', verdict: 'block' },
      { path: PLUGIN_AJAX, action: null, verdict: 'block-fail' },
      { path: PLUGIN_AJAX, action: 'executeHaAction', verdict: 'block-fail' },
      { path: '/socket', action: null, verdict: 'websocket-bloque' },
      { path: '/core/ajax/user.ajax.php', action: 'login', verdict: 'auth', reason: 'connexion-par-la-page-interdite' },
      { path: REDIRECT_PNG, action: null, verdict: 'redirection-non-autorisee', reason: 'redirection-non-autorisee' },
      { path: '/index.php', action: null, verdict: 'redirection-non-autorisee', reason: 'redirection-non-autorisee' },
    ];
    const remainingFailures = [...journal.failures];
    for (const expected of expectedFailures) {
      report(
        `journal : ${expected.path} action=${expected.action ?? '-'} verdict=${expected.verdict}`,
        takeMatchingFailure(remainingFailures, expected) !== null,
        failures
      );
    }
    report('journal marque le gate en echec', journal.failed, failures);
    for (const extra of remainingFailures) {
      console.log(`EXTRA ${extra.path} action=${extra.action ?? '-'} verdict=${extra.verdict}`);
    }

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
    report('publication declaree : exclusion puis retrait simules',
      results.publicationSaved?.result?.payload?.publication_policy === 'exclude'
        && results.publicationReverted?.result?.payload?.scope === 'equipment'
        && journal.entries.some((entry) => entry.action === 'savePublicationOverride' && entry.verdict === 'simulee')
        && journal.entries.some((entry) => entry.action === 'revertPublicationOverride' && entry.verdict === 'simulee'),
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
  } finally {
    if (browser) await browser.close();
    await close(server);
  }
}

main().catch((error) => {
  console.error(`FAIL exception: ${error.message}`);
  process.exitCode = 1;
});
