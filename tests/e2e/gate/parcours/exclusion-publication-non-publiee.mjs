/** Story 20-2 : exclusion simulée puis retrait, sur un eq id non publié.
 *
 * Revue ClaudeBox X4 (point 2) : la surface ne demande confirmation (modale
 * Bootbox) que pour une entité DÉJÀ PUBLIÉE (`shouldConfirmPublication`) — un
 * clic sur « Confirmer » après « Exclure » sur un équipement non publié
 * n'a donc jamais de modale à cliquer et bloquait ce parcours jusqu'à
 * l'échéance. Ce parcours vérifie maintenant explicitement l'absence de
 * modale, puis l'état des boutons (point 3) avant et après le retrait.
 *
 * Revue indépendante PR #210 (point 4) : les panneaux `.j2ha-eq-panel`
 * n'existent que DANS la modale de pièce (`openRoom`) — ce parcours cherchait
 * le panneau de l'eq 287 directement sur la page, sans jamais l'ouvrir. Et la
 * modale de pièce elle-même est une bootbox : le contrôle « aucune `.bootbox`
 * visible » aurait toujours échoué puisqu'une bootbox (la modale de pièce)
 * est déjà ouverte à ce moment. On ne connaît pas le nom de la pièce de l'eq
 * 287 : on parcourt donc les cartes de pièce une à une jusqu'à trouver le
 * panneau, et on vérifie l'absence de confirmation par l'absence du bouton
 * « Confirmer » plutôt que par l'absence de toute bootbox.
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

// Story 20-2 (point 4) : l'eq 287 n'est désigné que par son id, jamais par un
// nom de pièce — on ouvre chaque carte de pièce jusqu'à trouver son panneau,
// en refermant la modale des pièces sans résultat avant de passer à la suivante.
async function findEquipmentPanel(page, eqId) {
  const modal = page.locator('.modal-j2ha-room');
  const roomCards = page.locator('#j2ha_roomCards .j2ha-room-card');
  const roomCount = await roomCards.count();
  for (let i = 0; i < roomCount; i += 1) {
    await roomCards.nth(i).click();
    await modal.waitFor({ state: 'visible' });
    const panel = modal.locator(`.j2ha-eq-panel[data-eq-id="${eqId}"]`);
    if (await panel.count() > 0) {
      return panel;
    }
    await page.keyboard.press('Escape');
    await modal.waitFor({ state: 'hidden' });
  }
  throw new Error('eq-introuvable');
}

export async function run(page, { helpers }) {
  const panel = await findEquipmentPanel(page, '287');
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
  // Point 4 : la modale de pièce est elle-même une bootbox, donc le contrôle ne peut pas
  // être « aucune bootbox visible » — l'absence de confirmation se lit dans l'absence du
  // bouton « Confirmer » (confirmPublicationDialog) après le clic sur « Exclure ».
  if (await page.getByRole('button', { name: 'Confirmer', exact: true }).isVisible().catch(() => false)) {
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
