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
 *
 * Relecture indépendante PR #210 (point P2, reprise X5d) : les entités et l'état
 * des boutons ne sont connus qu'après la lecture `getMappingOverrides` (requête
 * réseau vers la box) — ce parcours les lisait dès le dépliage ou dès l'apparition
 * de l'écriture au journal, avant que la relecture et le nouveau rendu n'aient eu
 * lieu. Il échouerait par une fenêtre de course contre la vraie page. On attend
 * maintenant l'arrivée de la première ligne d'entité (bornée), puis la séquence
 * ordonnée du journal (écriture puis relecture `getMappingOverrides`), puis l'état
 * DOM attendu des boutons, avant toute assertion.
 */

export const name = 'exclusion-publication-non-publiee';
export const declaredEquipments = { '287': { commands: [] } };
export const declaredBascules = [];
export const declaredPublicationOverrides = { '287': { commands: [] } };

/** Attend une séquence ordonnée d'entrées de l'intercepteur, sans délai implicite. */
async function waitForJournal(journalEntries, start, expected) {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    const entries = journalEntries().slice(start);
    let cursor = 0;
    for (const entry of entries) {
      const next = expected[cursor];
      if (next && entry.action === next.action && entry.verdict === next.verdict) {
        cursor += 1;
      }
    }
    if (cursor === expected.length) return;
    await new Promise((resolve) => setTimeout(resolve, 25));
  }
  throw new Error('journal-attendu-absent');
}

/** Attend que le bouton d'action d'équipement portant ce libellé ait l'état `disabled` attendu. */
async function waitForActionButtonState(page, eqId, label, expectedDisabled) {
  await page.waitForFunction(({ eqId, label, expectedDisabled }) => {
    const panel = document.querySelector(`.j2ha-eq-panel[data-eq-id="${eqId}"]`);
    if (!panel) return false;
    const buttons = panel.querySelectorAll('.j2ha-eq-actions button');
    const button = Array.from(buttons).find((candidate) => candidate.textContent.trim() === label);
    return Boolean(button) && button.disabled === expectedDisabled;
  }, { eqId, label, expectedDisabled });
}

/** Attend l'étape nommée, journalise son libellé avant exécution pour un rapport diagnosticable. */
async function waitAtStep(helpers, index, label, operation) {
  helpers.record(`etape_${index}`, label);
  try {
    return await operation();
  } catch (error) {
    const message = error instanceof Error ? error.message.split(/\r?\n/, 1)[0] : String(error);
    throw new Error(`etape ${label} : ${message}`);
  }
}

/** Ferme la modale de pièce sans clic par coordonnées : le bouton de fermeture peut se
 * retrouver hors de la zone visible selon le défilement de la page sous-jacente. */
async function closeRoomModal(modal) {
  await modal.locator('.bootbox-close-button').dispatchEvent('click');
  await modal.waitFor({ state: 'hidden' });
}

// Story 20-2 (point 4) : l'eq 287 n'est désigné que par son id, jamais par un
// nom de pièce. On tente d'abord directement la carte de son objet connu
// (id d'objet 25) ; à défaut on referme et on retombe sur le parcours de
// toutes les cartes, en refermant chaque modale sans résultat avant de
// passer à la suivante.
async function findEquipmentPanel(page, helpers, eqId) {
  const modal = page.locator('.modal-j2ha-room');
  const knownCard = page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="25"]');
  if (await knownCard.count() > 0) {
    const panel = await waitAtStep(helpers, 1, 'ouverture-piece-connue', async () => {
      await knownCard.click();
      await modal.waitFor({ state: 'visible' });
      return modal.locator(`.j2ha-eq-panel[data-eq-id="${eqId}"]`);
    });
    if (await panel.count() > 0) {
      return panel;
    }
    await waitAtStep(helpers, 2, 'fermeture-piece-connue', () => closeRoomModal(modal));
  }

  const roomCards = page.locator('#j2ha_roomCards .j2ha-room-card');
  const roomCount = await roomCards.count();
  for (let i = 0; i < roomCount; i += 1) {
    await waitAtStep(helpers, `3_${i}`, `ouverture-piece-${i}`, async () => {
      await roomCards.nth(i).click();
      await modal.waitFor({ state: 'visible' });
    });
    const panel = modal.locator(`.j2ha-eq-panel[data-eq-id="${eqId}"]`);
    if (await panel.count() > 0) {
      return panel;
    }
    await waitAtStep(helpers, `4_${i}`, `fermeture-piece-${i}`, () => closeRoomModal(modal));
  }
  throw new Error('eq-introuvable');
}

export async function run(page, { helpers }) {
  const panel = await findEquipmentPanel(page, helpers, '287');
  await waitAtStep(helpers, 5, 'depliage', async () => {
    await panel.locator('.j2ha-eq-toggle').click();
    await panel.locator('.panel-collapse').waitFor({ state: 'visible' });
  });

  // Point P2 (reprise X5d) : les entités n'arrivent qu'après la relecture
  // `getMappingOverrides` déclenchée par le dépliage — attendre la première ligne
  // (délai borné) avant de compter, pour ne pas lire un arbre encore vide.
  await panel.locator('.j2ha-entity-row').first().waitFor({ state: 'attached', timeout: 10_000 }).catch(() => {});

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
  await waitAtStep(helpers, 6, 'exclure', () => excludeButton.click());
  await waitAtStep(helpers, 7, 'journal-exclusion', () => waitForJournal(helpers.journalEntries, start, [
    { action: 'savePublicationOverride', verdict: 'simulee' },
  ]));
  // Point 4 : la modale de pièce est elle-même une bootbox, donc le contrôle ne peut pas
  // être « aucune bootbox visible » — l'absence de confirmation se lit dans l'absence du
  // bouton « Confirmer » (confirmPublicationDialog). Placé après l'apparition de
  // l'écriture au journal (reprise X5d), pour ne pas lire trop tôt.
  if (await page.getByRole('button', { name: 'Confirmer', exact: true }).isVisible().catch(() => false)) {
    throw new Error('modale-confirmation-inattendue');
  }

  // Après la pose simulée : le rechargement de l'équipement relit l'arbre dérivé
  // (`getMappingOverrides`, verdict `lecture-derivee`) avant tout nouveau rendu des
  // boutons (reprise X5d) — attendre cette relecture, puis l'état DOM lui-même,
  // plutôt que l'apparition seule de l'écriture au journal.
  await waitAtStep(helpers, 8, 'journal-relecture-exclusion', () => waitForJournal(helpers.journalEntries, start, [
    { action: 'savePublicationOverride', verdict: 'simulee' },
    { action: 'getMappingOverrides', verdict: 'lecture-derivee' },
  ]));
  // Après la pose simulée et la relecture déclenchée par le rechargement de
  // l'équipement : « Exclure » devient sans effet (déjà exclu), « Revenir au
  // mode automatique » devient le seul moyen de retirer l'exclusion (point 3).
  await waitAtStep(helpers, 9, 'etat-boutons-apres-exclusion', async () => {
    await waitForActionButtonState(page, '287', 'Exclure', true);
    await waitForActionButtonState(page, '287', 'Revenir au mode automatique', false);
  });

  const afterSave = helpers.journalEntries().length;
  await waitAtStep(helpers, 10, 'revenir-au-mode-automatique', () => revertButton.click());
  // Après le retrait : relecture `getMappingOverrides` sans simulation active
  // (verdict `read`, l'exclusion a été purgée par `revertPublicationOverride`) avant
  // que « Exclure » ne redevienne actif (reprise X5d).
  await waitAtStep(helpers, 11, 'journal-retrait', () => waitForJournal(helpers.journalEntries, afterSave, [
    { action: 'revertPublicationOverride', verdict: 'simulee' },
    { action: 'getMappingOverrides', verdict: 'read' },
  ]));
  // Après le retrait : « Exclure » redevient actif.
  await waitAtStep(helpers, 12, 'etat-bouton-final', () => waitForActionButtonState(page, '287', 'Exclure', false));
}
