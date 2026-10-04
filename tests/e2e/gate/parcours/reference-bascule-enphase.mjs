/** Parcours de référence : bascule simulée puis retour réel au mode automatique. */

export const name = 'reference-bascule-enphase';
export const declaredEquipments = {
  '579': { commands: ['5689', '5368', '5369', '5494', '5695', '5493'] },
};

// La première bloquante est désignée dynamiquement par la synthèse. Les deux
// candidats sont donc déclarés statiquement, mais un seul est utilisé à l'exécution.
export const declaredBascules = [
  { eqId: '579', cmdId: '5368', haEntityType: 'binary_sensor' },
  { eqId: '579', cmdId: '5369', haEntityType: 'binary_sensor' },
];

async function atStep(helpers, index, label, operation) {
  helpers.record(`etape_${index}`, label);
  try {
    return await operation();
  } catch (error) {
    const message = error instanceof Error ? error.message.split(/\r?\n/, 1)[0] : String(error);
    throw new Error(`etape ${label} : ${message}`);
  }
}

async function openEnphase(page, helpers) {
  const room = page.locator('#j2ha_roomCards .j2ha-room-card').filter({
    has: page.locator('.name', { hasText: /^Garage$/ }),
  });
  await atStep(helpers, 1, 'carte-garage', () => room.click());
  const modal = page.locator('.modal-j2ha-room');
  await atStep(helpers, 2, 'modale', () => modal.waitFor({ state: 'visible' }));
  const panel = modal.locator('.j2ha-eq-panel').filter({
    has: page.locator('.j2ha-eq-name', { hasText: /^\s*Enphase\s*$/ }),
  });
  await atStep(helpers, 3, 'panneau-enphase', () => panel.waitFor({ state: 'visible' }));
  await atStep(helpers, 4, 'depliage', async () => {
    await panel.locator('.j2ha-eq-toggle').click();
    await panel.locator('.panel-collapse').waitFor({ state: 'visible' });
  });
  await atStep(helpers, 5, 'table', () => panel.locator('.j2ha-cmd-table').waitFor({ state: 'visible' }));
  await atStep(helpers, 6, 'ancre-bloquante', () => panel.locator('.j2ha-goto-blocking').waitFor({ state: 'visible' }));
  return panel;
}

async function waitForTarget(page, panel) {
  await panel.locator('.j2ha-goto-blocking').click();
  const targetHandle = await page.waitForFunction(() => {
    const targets = document.querySelectorAll('tr.mapping-override-cmd.j2ha-diag-target-highlight');
    return targets.length === 1 ? targets[0].getAttribute('data-cmd-id') : null;
  });
  const cmdId = await targetHandle.jsonValue();
  await targetHandle.dispose();
  if (!['5368', '5369'].includes(cmdId ?? '')) throw new Error('cmd-cible-inattendue');
  return { target: panel.locator(`tr.mapping-override-cmd[data-cmd-id="${cmdId}"]`), cmdId };
}

async function diagnosticState(row) {
  return row.locator('.mo-diag-cell').evaluate((cell) => {
    if (cell.classList.contains('j2ha-diag-ready')) return 'prete';
    if (cell.classList.contains('j2ha-diag-blocking')) return 'bloquante';
    if (cell.classList.contains('j2ha-diag-uncovered')) return 'non-couverte';
    if (cell.classList.contains('j2ha-diag-unknown')) return 'inconnue';
    return 'inconnu';
  });
}

async function summary(panel) {
  return (await panel.locator('.j2ha-eq-publish-badge').innerText()).trim();
}

function writesSince(journal, start) {
  return journal.entries.slice(start).filter((entry) => ['saveMappingOverride', 'revertMappingOverride'].includes(entry.action));
}

/** Attend une séquence ordonnée d'entrées de l'intercepteur, sans délai implicite. */
async function waitForJournal(journal, start, expected) {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    const entries = journal.entries.slice(start);
    const matched = [];
    let cursor = 0;
    for (const entry of entries) {
      const next = expected[cursor];
      if (next && entry.action === next.action && entry.verdict === next.verdict) {
        matched.push(entry);
        cursor += 1;
      }
    }
    if (cursor === expected.length) return { entries, matched };
    await new Promise((resolve) => setTimeout(resolve, 25));
  }
  throw new Error('journal-attendu-absent');
}

export async function run(page, { helpers, journal }) {
  const panel = await openEnphase(page, helpers);
  const initialSummary = await atStep(helpers, 7, 'synthese-initiale', () => summary(panel));
  helpers.record('synthese_initiale', initialSummary);

  const { target, cmdId } = await atStep(helpers, 8, 'premiere-bloquante', () => waitForTarget(page, panel));
  helpers.record('cmd_cible_id', Number(cmdId));
  helpers.record('cmd_cible_initial', await diagnosticState(target));

  const journalA = journal.entries.length;
  await atStep(helpers, 9, 'apercu-reel-bloquant', async () => {
    await target.locator('select').selectOption('sensor');
    await waitForJournal(journal, journalA, [
      { action: 'previewMappingOverride', verdict: 'lecture-reelle' },
    ]);
    await page.waitForFunction((id) => {
      const row = document.querySelector(`tr.mapping-override-cmd[data-cmd-id="${id}"]`);
      return row?.querySelector('.mo-diag-cell')?.classList.contains('j2ha-diag-blocking')
        && row.querySelector('.mo-spinner')?.getAttribute('style')?.includes('display: none');
    }, cmdId);
  });
  const stateA = await diagnosticState(target);
  if (stateA !== 'bloquante') throw new Error('apercu-reel-non-bloquant');
  if (writesSince(journal, journalA).length !== 0) throw new Error('ecriture-apres-apercu-reel');
  helpers.record('etape_a_cellule', stateA);
  helpers.record('etape_a_ecriture', false);
  helpers.record('etape_a_entrees_journal', journal.entries.length - journalA);

  const journalB = journal.entries.length;
  await atStep(helpers, 10, 'bascule-simulee', async () => {
    await target.locator('select').selectOption('binary_sensor');
    await waitForJournal(journal, journalB, [
      { action: 'previewMappingOverride', verdict: 'apercu-simule' },
      { action: 'saveMappingOverride', verdict: 'simulee' },
      { action: 'getMappingOverrides', verdict: 'lecture-derivee' },
    ]);
    await page.waitForFunction((id) => {
      const row = document.querySelector(`tr.mapping-override-cmd[data-cmd-id="${id}"]`);
      return row?.querySelector('.mo-diag-cell')?.classList.contains('j2ha-diag-ready')
        && Boolean(row.querySelector('.mo-revert-cmd'));
    }, cmdId);
  });
  const stateB = await diagnosticState(target);
  const summaryB = await summary(panel);
  if (stateB !== 'prete') throw new Error('bascule-simulee-non-prete');
  if (!/0\s+bloquante\(s\)/.test(summaryB)) throw new Error('synthese-bascule-encore-bloquante');
  helpers.record('etape_b_cellule', stateB);
  helpers.record('etape_b_synthese', summaryB);
  helpers.record('etape_b_entrees_journal', journal.entries.length - journalB);

  const journalC = journal.entries.length;
  await atStep(helpers, 11, 'retour-automatique', async () => {
    await target.locator('.mo-revert-cmd').click();
    await waitForJournal(journal, journalC, [
      { action: 'revertMappingOverride', verdict: 'simulee' },
      { action: 'getMappingOverrides', verdict: 'read' },
    ]);
    await page.waitForFunction((id) => {
      const row = document.querySelector(`tr.mapping-override-cmd[data-cmd-id="${id}"]`);
      return row?.querySelector('.mo-diag-cell')?.classList.contains('j2ha-diag-blocking')
        && !row.querySelector('.mo-revert-cmd');
    }, cmdId);
  });
  const stateC = await diagnosticState(target);
  const summaryC = await summary(panel);
  if (stateC !== 'bloquante' || summaryC !== initialSummary) throw new Error('retour-automatique-incomplet');
  helpers.record('etape_c_cellule', stateC);
  helpers.record('etape_c_synthese', summaryC);
  helpers.record('etape_c_entrees_journal', journal.entries.length - journalC);
}
