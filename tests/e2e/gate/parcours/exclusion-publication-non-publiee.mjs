/** Story 20-2 : exclusion simulée puis retrait, sur un eq id non publié.
 *
 * Revue ClaudeBox X4 (point 2) : la surface ne demande confirmation (modale
 * Bootbox) que pour une entité DÉJÀ PUBLIÉE (`shouldConfirmPublication`) — un
 * clic sur « Confirmer » après « Exclure » sur un équipement non publié
 * n'a donc jamais de modale à cliquer et bloquait ce parcours jusqu'à
 * l'échéance. Ce parcours vérifie maintenant explicitement l'absence de
 * modale, puis l'état des boutons (point 3) avant et après le retrait.
 */

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

  // Précondition : un équipement sans aucune entité ne peut rien prouver sur
  // les boutons de publication (ils resteraient dans leur état par défaut,
  // quel que soit le bug recherché) — échec explicite plutôt qu'une attente
  // muette sur un bouton qui n'existera jamais dans l'état attendu.
  const entityRowCount = await panel.locator('.j2ha-entity-row').count();
  if (entityRowCount < 1) {
    throw new Error('eq-sans-entite');
  }

  const actions = panel.locator('.j2ha-eq-actions');
  const excludeButton = actions.getByRole('button', { name: 'Exclure', exact: true });
  const revertButton = actions.getByRole('button', { name: 'Revenir au mode automatique', exact: true });

  const start = helpers.journalEntries().length;
  // Équipement non publié : aucune confirmation attendue (shouldConfirmPublication
  // n'exige une modale que pour une entité déjà publiée) — un clic direct suffit.
  await excludeButton.click();
  if (await page.locator('.bootbox').isVisible().catch(() => false)) {
    throw new Error('modale-confirmation-inattendue');
  }
  await waitForWrite(helpers.journalEntries, start, 'savePublicationOverride');
  const saved = writesSince(helpers.journalEntries, start);
  if (!saved.some((entry) => entry.action === 'savePublicationOverride' && entry.verdict === 'simulee')) {
    throw new Error('exclusion-publication-non-simulee');
  }

  // Après la pose simulée et la relecture déclenchée par le rechargement de
  // l'équipement : « Exclure » devient sans effet (déjà exclu), « Revenir au
  // mode automatique » devient le seul moyen de retirer l'exclusion (point 3).
  await panel.locator('.panel-collapse').waitFor({ state: 'visible' });
  await excludeButton.waitFor({ state: 'attached' });
  if (!(await excludeButton.isDisabled())) {
    throw new Error('exclure-equipement-toujours-actif-apres-exclusion');
  }
  if (await revertButton.isDisabled()) {
    throw new Error('revenir-mode-automatique-inactif-apres-exclusion');
  }

  const afterSave = helpers.journalEntries().length;
  await revertButton.click();
  await waitForWrite(helpers.journalEntries, afterSave, 'revertPublicationOverride');
  const reverted = writesSince(helpers.journalEntries, afterSave);
  if (!reverted.some((entry) => entry.action === 'revertPublicationOverride' && entry.verdict === 'simulee')) {
    throw new Error('retour-publication-non-simule');
  }

  // Après le retrait : « Exclure » redevient actif.
  await panel.locator('.panel-collapse').waitFor({ state: 'visible' });
  if (await excludeButton.isDisabled()) {
    throw new Error('exclure-equipement-toujours-inactif-apres-retrait');
  }
}
