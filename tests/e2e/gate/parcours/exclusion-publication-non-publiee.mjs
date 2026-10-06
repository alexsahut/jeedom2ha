/** Story 20-2 : exclusion simulée puis retrait, sur un eq id non publié. */

export const name = 'exclusion-publication-non-publiee';
export const declaredEquipments = { '287': { commands: [] } };
export const declaredBascules = [];
export const declaredPublicationOverrides = { '287': { commands: [] } };

function writesSince(entries, start) {
  return entries().slice(start).filter((entry) =>
    ['savePublicationOverride', 'revertPublicationOverride'].includes(entry.action));
}

async function waitForWrite(entries, start, action) {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (writesSince(entries, start).some((entry) => entry.action === action && entry.verdict === 'simulee')) return;
    await new Promise((resolve) => setTimeout(resolve, 25));
  }
  throw new Error('ecriture-simulee-absente');
}

export async function run(page, { helpers }) {
  const panel = page.locator('.j2ha-eq-panel[data-eq-id="287"]');
  await panel.locator('.j2ha-eq-toggle').click();
  await panel.locator('.panel-collapse').waitFor({ state: 'visible' });
  const actions = panel.locator('.j2ha-eq-actions');
  const start = helpers.journalEntries().length;
  await actions.getByRole('button', { name: 'Exclure', exact: true }).click();
  await page.getByRole('button', { name: 'Confirmer', exact: true }).click();
  await waitForWrite(helpers.journalEntries, start, 'savePublicationOverride');
  const saved = writesSince(helpers.journalEntries, start);
  if (!saved.some((entry) => entry.action === 'savePublicationOverride' && entry.verdict === 'simulee')) {
    throw new Error('exclusion-publication-non-simulee');
  }
  const afterSave = helpers.journalEntries().length;
  await actions.getByRole('button', { name: 'Revenir au mode automatique', exact: true }).click();
  await waitForWrite(helpers.journalEntries, afterSave, 'revertPublicationOverride');
  const reverted = writesSince(helpers.journalEntries, afterSave);
  if (!reverted.some((entry) => entry.action === 'revertPublicationOverride' && entry.verdict === 'simulee')) {
    throw new Error('retour-publication-non-simule');
  }
}
