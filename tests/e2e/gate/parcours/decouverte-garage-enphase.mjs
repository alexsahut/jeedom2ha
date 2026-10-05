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
      'j2ha-diag-excluded',
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
    if (diagnostic?.classList.contains('j2ha-diag-excluded')) state = 'exclue';
    if (diagnostic?.classList.contains('j2ha-diag-unknown')) state = 'inconnue';
    return { id: row.getAttribute('data-cmd-id'), state };
  }));
}

/** Attend puis lit les états de badge de tous les équipements déjà présents dans la modale. */
async function readEquipmentBadgeStates(page, modal) {
  await page.waitForFunction(() => {
    const panels = [...document.querySelectorAll('.modal-j2ha-room .j2ha-eq-panel')];
    const states = [
      'j2ha-publish-ok',
      'j2ha-publish-partial',
      'j2ha-publish-blocked',
      'j2ha-publish-excluded',
      'j2ha-publish-empty',
    ];
    return panels.length > 0 && panels.every((item) => {
      const badge = item.querySelector('.j2ha-eq-publish-badge');
      return badge && states.some((state) => badge.classList.contains(state));
    });
  });
  return modal.locator('.j2ha-eq-panel').evaluateAll((panels) => panels.map((item) => {
    const badge = item.querySelector('.j2ha-eq-publish-badge');
    let state = 'inconnu';
    if (badge?.classList.contains('j2ha-publish-ok')) state = 'publie';
    if (badge?.classList.contains('j2ha-publish-partial')) state = 'partiel';
    if (badge?.classList.contains('j2ha-publish-blocked')) state = 'bloque';
    if (badge?.classList.contains('j2ha-publish-excluded')) state = 'exclu';
    if (badge?.classList.contains('j2ha-publish-empty')) state = 'vide';
    return { id: item.getAttribute('data-eq-id'), state };
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

/** Consigne au plus trente noms d'équipement de la modale pour diagnostiquer un sélecteur absent. */
async function recordEquipmentNames(modal, helpers) {
  const names = await modal.locator('.j2ha-eq-name').allTextContents();
  for (const [index, name] of names.slice(0, 30).entries()) {
    try {
      helpers.record(`eq_nom_${index + 1}`, name.trim());
    } catch {
      // Les noms refusés par le contrat de rapport sont volontairement ignorés.
    }
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
    has: page.locator('.j2ha-eq-name', { hasText: /^\s*Enphase\s*$/ }),
  });
  try {
    await waitAtStep(helpers, 3, 'panneau-enphase', () => panel.waitFor({ state: 'visible' }));
  } catch (error) {
    await recordEquipmentNames(modal, helpers);
    throw error;
  }

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
  for (const equipment of await readEquipmentBadgeStates(page, modal)) {
    if (!/^\d+$/.test(equipment.id ?? '')) throw new Error('eqid-badge-illisible');
    helpers.record(`eq_${equipment.id}_badge`, equipment.state);
  }
}
