/** Parcours de référence : bascule simulée puis retour réel au mode automatique. */

export const name = 'reference-bascule-eq-380';
export const declaredEquipments = {
  '380': { commands: ['2971', '2968', '2969', '2970'] },
};
export const declaredPublicationOverrides = {};

// La seule commande bloquante de l'équipement 380 est la cible de l'ancre.
export const declaredBascules = [
  { eqId: '380', cmdId: '2971', haEntityType: 'binary_sensor' },
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

async function openEq380(page, helpers) {
  const room = page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="4"]');
  await atStep(helpers, 1, 'carte-piece-4', () => room.click());
  const modal = page.locator('.modal-j2ha-room');
  await atStep(helpers, 2, 'modale', () => modal.waitFor({ state: 'visible' }));
  const panel = modal.locator('.j2ha-eq-panel[data-eq-id="380"]');
  await atStep(helpers, 3, 'panneau-eq-380', () => panel.waitFor({ state: 'visible' }));
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
  if (cmdId !== '2971') throw new Error('cmd-cible-inattendue');
  return { target: panel.locator(`tr.mapping-override-cmd[data-cmd-id="${cmdId}"]`), cmdId };
}

async function diagnosticState(row) {
  return row.locator('.mo-diag-cell').evaluate((cell) => {
    if (cell.classList.contains('j2ha-diag-ready')) return 'prete';
    if (cell.classList.contains('j2ha-diag-blocking')) return 'bloquante';
    if (cell.classList.contains('j2ha-diag-uncovered')) return 'non-couverte';
    if (cell.classList.contains('j2ha-diag-excluded')) return 'exclue';
    if (cell.classList.contains('j2ha-diag-unknown')) return 'inconnue';
    return 'inconnu';
  });
}

async function summary(panel) {
  return (await panel.locator('.j2ha-eq-publish-badge').innerText()).trim();
}

/** Story 22.2 (AC2) : compteurs de l'équipement déplié (texte rendu, identifiants seulement). */
async function counters(panel) {
  return panel.locator('.j2ha-eq-counter').evaluateAll((nodes) => nodes.map((node) => (node.textContent ?? '').trim()));
}

function writesSince(journalEntries, start) {
  return journalEntries().slice(start).filter((entry) => ['saveMappingOverride', 'revertMappingOverride'].includes(entry.action));
}

/** Attend une séquence ordonnée d'entrées de l'intercepteur, sans délai implicite. */
async function waitForJournal(journalEntries, start, expected) {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    const entries = journalEntries().slice(start);
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

export async function run(page, { helpers }) {
  const panel = await openEq380(page, helpers);
  const initialSummary = await atStep(helpers, 7, 'synthese-initiale', () => summary(panel));
  helpers.record('synthese_initiale', initialSummary);

  const initialCounters = await atStep(helpers, '7a', 'compteurs-initiaux', () => counters(panel));
  if (initialCounters.length < 3 || !initialCounters.slice(0, 3).every((text) => /^\d+ commandes? /.test(text))) {
    throw new Error('compteurs-eq-380-illisibles');
  }
  initialCounters.forEach((text, index) => helpers.record(`compteur_initial_${index + 1}`, text));

  const { target, cmdId } = await atStep(helpers, 8, 'premiere-bloquante', () => waitForTarget(page, panel));
  helpers.record('cmd_cible_id', Number(cmdId));
  helpers.record('cmd_cible_initial', await diagnosticState(target));

  const journalA = helpers.journalEntries().length;
  await atStep(helpers, 9, 'apercu-reel-bloquant', async () => {
    await target.locator('select').selectOption('sensor');
    await waitForJournal(helpers.journalEntries, journalA, [
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
  // Story 22.2 (CC-60) : le type refusé garde sa cause lisible — la voie normale est de préciser
  // les types génériques dans Jeedom (la liste « Override HA » n'est pas filtrée dans cette story).
  const causeA = (await target.locator('.mo-diag-cell').innerText()).trim();
  if (!/précisez les types génériques dans Jeedom/.test(causeA)) throw new Error('cause-refus-illisible');
  helpers.record('etape_a_cause', causeA);
  if (writesSince(helpers.journalEntries, journalA).length !== 0) throw new Error('ecriture-apres-apercu-reel');
  helpers.record('etape_a_cellule', stateA);
  helpers.record('etape_a_ecriture', false);
  helpers.record('etape_a_entrees_journal', helpers.journalEntries().length - journalA);

  const journalB = helpers.journalEntries().length;
  await atStep(helpers, 10, 'bascule-simulee', async () => {
    await target.locator('select').selectOption('binary_sensor');
    await waitForJournal(helpers.journalEntries, journalB, [
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
  helpers.record('etape_b_synthese', summaryB);
  if (stateB !== 'prete') throw new Error('bascule-simulee-non-prete');
  if (!/^Sera publié dans Home Assistant : \d+ commande\(s\) prête\(s\)\.$/.test(summaryB)) {
    throw new Error('synthese-bascule-encore-bloquante');
  }
  helpers.record('etape_b_cellule', stateB);
  helpers.record('etape_b_entrees_journal', helpers.journalEntries().length - journalB);

  const journalC = helpers.journalEntries().length;
  await atStep(helpers, 11, 'retour-automatique', async () => {
    await target.locator('.mo-revert-cmd').click();
    await waitForJournal(helpers.journalEntries, journalC, [
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
  helpers.record('etape_c_synthese', summaryC);
  if (stateC !== 'bloquante' || summaryC !== initialSummary) throw new Error('retour-automatique-incomplet');
  // Story 22.2 : le retour au mode automatique restitue aussi les compteurs de l'équipement.
  const finalCounters = await atStep(helpers, '11a', 'compteurs-finaux', () => counters(panel));
  if (JSON.stringify(finalCounters) !== JSON.stringify(initialCounters)) throw new Error('compteurs-non-restitues');
  helpers.record('compteurs_restitues', true);
  helpers.record('etape_c_cellule', stateC);
  helpers.record('etape_c_entrees_journal', helpers.journalEntries().length - journalC);
}
