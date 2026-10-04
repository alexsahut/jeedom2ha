/** Parcours de découverte lecture seule : Garage puis équipement Enphase. */

export const name = 'decouverte-garage-enphase';
export const declaredEquipments = {};
export const declaredBascules = [];

/** Attend le rendu complet des diagnostics factuels de toutes les commandes de l'équipement. */
async function waitForDiagnostics(page, eqId) {
  await page.waitForFunction((targetId) => {
    const panels = [...document.querySelectorAll('.modal-j2ha-room .j2ha-eq-panel')];
    const panel = panels.find((item) => item.getAttribute('data-eq-id') === targetId);
    const rows = panel ? [...panel.querySelectorAll('tr.mapping-override-cmd')] : [];
    const states = [
      'j2ha-diag-ready',
      'j2ha-diag-blocking',
      'j2ha-diag-uncovered',
      'j2ha-diag-unknown',
    ];
    return rows.length > 0 && rows.every((row) => {
      const diagnostic = row.querySelector('.mo-diag-cell');
      return diagnostic && states.some((state) => diagnostic.classList.contains(state));
    });
  }, eqId);
}

/** Lit les seuls identifiants et états diagnostics autorisés depuis les lignes déjà rendues. */
async function readCommandStates(panel) {
  return panel.locator('tr.mapping-override-cmd').evaluateAll((rows) => rows.map((row) => {
    const diagnostic = row.querySelector('.mo-diag-cell');
    let state = 'inconnu';
    if (diagnostic?.classList.contains('j2ha-diag-ready')) state = 'prete';
    if (diagnostic?.classList.contains('j2ha-diag-blocking')) state = 'bloquante';
    if (diagnostic?.classList.contains('j2ha-diag-uncovered')) state = 'non-couverte';
    if (diagnostic?.classList.contains('j2ha-diag-unknown')) state = 'inconnue';
    return { id: row.getAttribute('data-cmd-id'), state };
  }));
}

/** Consigne une étape avant son attente et préfixe toute erreur avec son nom. */
async function waitAtStep(helpers, index, label, operation) {
  helpers.record(`etape_${index}`, label);
  try {
    return await operation();
  } catch (error) {
    const message = error instanceof Error ? error.message.split(/\r?\n/, 1)[0] : String(error);
    throw new Error(`etape ${label} : ${message}`);
  }
}

/** Ouvre Garage, déplie Enphase et consigne les constats DOM non sensibles. */
export async function run(page, { helpers }) {
  const roomCard = page.locator('#j2ha_roomCards .j2ha-room-card').filter({
    has: page.locator('.name', { hasText: /^Garage$/ }),
  });
  await waitAtStep(helpers, 1, 'carte-garage', () => roomCard.click());

  const modal = page.locator('.modal-j2ha-room');
  await waitAtStep(helpers, 2, 'modale', () => modal.waitFor({ state: 'visible' }));
  const panel = modal.locator('.j2ha-eq-panel').filter({
    has: modal.locator('.j2ha-eq-name', { hasText: /^Enphase$/ }),
  });
  await waitAtStep(helpers, 3, 'panneau-enphase', () => panel.waitFor({ state: 'visible' }));

  const eqId = await panel.getAttribute('data-eq-id');
  if (!/^\d+$/.test(eqId ?? '')) throw new Error('eqid-enphase-illisible');
  await waitAtStep(helpers, 4, 'depliage', async () => {
    await panel.locator('.j2ha-eq-toggle').click();
    await panel.locator('.panel-collapse').waitFor({ state: 'visible' });
  });
  await waitAtStep(helpers, 5, 'table', () => {
    return panel.locator('.j2ha-cmd-table').waitFor({ state: 'visible' });
  });
  await waitAtStep(helpers, 6, 'diagnostics', () => waitForDiagnostics(page, eqId));

  helpers.record('eq_id', Number(eqId));
  for (const command of await readCommandStates(panel)) {
    if (!/^\d+$/.test(command.id ?? '')) throw new Error('cmdid-enphase-illisible');
    helpers.record(`cmd_${command.id}_id`, Number(command.id));
    helpers.record(`cmd_${command.id}_etat`, command.state);
  }
  const summary = (await panel.locator('.j2ha-eq-publish-badge').innerText()).trim();
  if (!summary) throw new Error('synthese-enphase-illisible');
  helpers.record('synthese', summary);
}
