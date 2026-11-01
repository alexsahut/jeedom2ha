/** Story 20-2 : exclusion simulée puis retrait, sur un eq id non publié.
 *
 * Story 24.11 : l'équipement est choisi à l'exécution (premier éligible, jamais l'eq 287) puis déclaré
 * par `helpers.declareTarget` avant toute écriture ; les mentions de l'eq 287 ci-dessous sont historiques.
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

// Story 25.1 : le réglage de publication est un contrôle segmenté « Automatique | Toujours | Jamais »
// (il remplace « Exclure », « Forcer » et « Revenir au mode automatique »). L'équipement cible n'a
// qu'une entité : pas d'en-tête de groupe, seul le contrôle d'équipement existe. Les positions sont des
// radios ; la position active porte `aria-checked="true"`.
const EXCLUDE_LABEL = 'Jamais';
const REVERT_LABEL = 'Automatique';
// Story 24.11 : la cible n'est plus figée (l'eq 287 porte depuis le 19/10 un réglage posé à la main). Le
// parcours la choisit à l'exécution, en lecture seule, puis la déclare par `helpers.declareTarget` AVANT
// toute écriture ; le lanceur refuse un id portant un réglage dans le témoin « avant ». Les déclarations
// statiques restent donc vides.
export const dynamicTarget = true;
export const declaredEquipments = {};
export const declaredBascules = [];
export const declaredPublicationOverrides = {};
// Exclusion permanente : l'eq 287 n'est jamais retenu, même sans réglage (consigne du mainteneur).
export const EXCLUDED_TARGETS = ['287'];
// « Ligne non publiée » : seuls ces mots d'état de l'arbre sont retenus. « Publié » et « À appliquer » sont
// écartés (une exclusion y demanderait confirmation), comme « Exclu » et « Désactivé » (réglage indisponible
// ou déjà neutralisé ailleurs) : le parcours ne prouverait rien de fiable sur ces lignes.
const ELIGIBLE_STATES = ['blocked', 'nothing_to_publish'];

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

/** Attend que la position du contrôle segmenté d'équipement portant ce libellé ait l'état attendu
 * (`checked` : position courante ; `disabled` : position indisponible). */
async function waitForSegmentState(page, eqId, label, expected) {
  await page.waitForFunction(({ eqId, label, expected }) => {
    const panel = document.querySelector(`.j2ha-eq-panel[data-eq-id="${eqId}"]`);
    if (!panel) return false;
    const segments = panel.querySelectorAll('.j2ha-eq-controls .j2ha-seg-btn');
    const segment = Array.from(segments).find((candidate) => candidate.textContent.trim() === label);
    return Boolean(segment) && segment.disabled === expected.disabled
      && (segment.getAttribute('aria-checked') === 'true') === expected.checked;
  }, { eqId, label, expected });
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

/** Story 25.4 : « fermer la fenêtre de pièce » = revenir à la page principale par un VRAI clic sur « Toutes les pièces »
 * (contrôle d'actionnabilité de Playwright ; plus de dispatchEvent). */
async function closeRoomModal(view) {
  await view.locator('.j2ha-wv-back').click();
  await view.waitFor({ state: 'hidden' });
}

/** Story 24.11 : mot d'état de la ligne d'arbre (classe `j2ha-state-<état>`), ou null. */
async function rowState(item) {
  return item.evaluate((node) => {
    if (node.classList.contains('j2ha-wv-eq-disabled')) return null;
    const word = node.querySelector(':scope > .j2ha-wv-row .j2ha-state-word');
    if (!word) return null;
    const match = Array.from(word.classList).find((name) => name.startsWith('j2ha-state-') && name !== 'j2ha-state-word');
    return match ? match.slice('j2ha-state-'.length) : null;
  });
}

/** Story 24.11 : vrai si le détail affiché remplit toutes les conditions (lecture seule, aucune écriture). */
async function panelEligible(panel) {
  await panel.waitFor({ state: 'visible', timeout: 10_000 });
  await panel.locator('.j2ha-eq-controls .j2ha-seg-btn').first().waitFor({ state: 'attached', timeout: 10_000 });
  const automatic = await panel.locator('.j2ha-eq-controls .j2ha-seg-btn').evaluateAll((nodes, label) => nodes.some(
    (node) => node.textContent.trim() === label && node.getAttribute('aria-checked') === 'true',
  ), REVERT_LABEL);
  if (!automatic) return false;
  if (await panel.locator('.j2ha-group-head').count() !== 0) return false;
  return await panel.locator('tr.mapping-override-cmd').count() >= 1;
}

/**
 * Story 24.11 : examine, dans la vue ouverte, les lignes d'équipement pas encore vues, dans l'ordre de l'arbre.
 * Un candidat est sélectionné par un vrai clic (relecture `getMappingOverrides`, lecture autorisée) ; rien
 * n'est écrit. Rend l'id de la première cible éligible, ou null.
 */
async function scanOpenView(page, view, seen) {
  const items = view.locator('.j2ha-wv-eq[data-eq-id]');
  const count = await items.count();
  for (let i = 0; i < count; i += 1) {
    const item = items.nth(i);
    const eqId = await item.getAttribute('data-eq-id');
    if (!eqId || !/^[0-9]+$/.test(eqId) || seen.has(eqId)) continue;
    seen.add(eqId);
    if (EXCLUDED_TARGETS.includes(eqId)) continue;
    if (!ELIGIBLE_STATES.includes(await rowState(item))) continue;
    await item.locator('.j2ha-wv-row').click();
    const panel = page.locator(`#j2ha_workView .j2ha-eq-panel[data-eq-id="${eqId}"]`);
    if (await panelEligible(panel).catch(() => false)) return eqId;
  }
  return null;
}

// Story 20-2 (point 4) : l'équipement n'est désigné que par son id, jamais par un nom de pièce.
// Story 24.11 : la cible est la PREMIÈRE ligne éligible. On examine d'abord la carte de l'objet
// historiquement connu (id d'objet 25) ; à défaut on revient à la page et on parcourt toutes les cartes,
// en revenant à la page après chaque pièce sans résultat avant de passer à la suivante (les lignes déjà
// examinées ne le sont pas deux fois). Story 25.4 : la pièce s'ouvre dans la vue de travail ; l'équipement
// est une ligne de l'arbre. Aucune cible : échec explicite `aucune-cible-eligible`.
async function findTarget(page, helpers) {
  const view = page.locator('#j2ha_workView');
  const seen = new Set();
  const knownCard = page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="25"]');
  if (await knownCard.count() > 0) {
    const eqId = await waitAtStep(helpers, 1, 'ouverture-piece-connue', async () => {
      await knownCard.click();
      await view.waitFor({ state: 'visible' });
      return scanOpenView(page, view, seen);
    });
    if (eqId) return eqId;
    await waitAtStep(helpers, 2, 'fermeture-piece-connue', () => closeRoomModal(view));
  }

  const roomCards = page.locator('#j2ha_roomCards .j2ha-room-card');
  const roomCount = await roomCards.count();
  for (let i = 0; i < roomCount; i += 1) {
    const eqId = await waitAtStep(helpers, `3_${i}`, `ouverture-piece-${i}`, async () => {
      await roomCards.nth(i).click();
      await view.waitFor({ state: 'visible' });
      return scanOpenView(page, view, seen);
    });
    if (eqId) return eqId;
    await waitAtStep(helpers, `4_${i}`, `fermeture-piece-${i}`, () => closeRoomModal(view));
  }
  throw new Error('aucune-cible-eligible');
}

export async function run(page, { helpers }) {
  const eqId = await findTarget(page, helpers);
  // Déclaration AVANT toute écriture : sans elle, la politique refuse l'exclusion simulée.
  helpers.declareTarget(eqId);
  const row = page.locator(`#j2ha_workView .j2ha-wv-eq[data-eq-id="${eqId}"]`);
  if (await row.count() === 0) throw new Error('eq-introuvable');
  const panel = page.locator(`#j2ha_workView .j2ha-eq-panel[data-eq-id="${eqId}"]`);
  // « depliage » : sélection de l'équipement dans l'arbre (clic réel) ; son détail est déjà déplié.
  await waitAtStep(helpers, 5, 'depliage', async () => {
    await row.locator('.j2ha-wv-row').click();
    await panel.waitFor({ state: 'visible' });
  });

  // Point P2 (reprise X5d) : le contrôle de publication n'est rendu qu'après la relecture
  // `getMappingOverrides` déclenchée par le dépliage — attendre sa présence (délai borné) avant de
  // compter, pour ne pas lire un arbre encore vide.
  await panel.locator('.j2ha-eq-controls .j2ha-seg-btn').first().waitFor({ state: 'attached', timeout: 10_000 }).catch(() => {});

  // Précondition : un équipement sans aucune entité ni commande ne peut rien prouver sur le réglage de
  // publication (il resterait dans sa position par défaut, quel que soit le bug recherché) — échec
  // explicite plutôt qu'une attente muette sur une position qui n'existera jamais dans l'état attendu.
  // Story 25.1 : une entité unique n'a plus de ligne dédiée ; on exige donc au moins une commande
  // rendue dans le tableau (donc un arbre lu avec son mapping).
  const commandRowCount = await panel.locator('tr.mapping-override-cmd').count();
  if (commandRowCount < 1) {
    throw new Error('eq-sans-entite');
  }

  // Story 22.2 / 25.1 (AC3) : équipement à une seule entité — aucun en-tête de groupe (donc aucun
  // contrôle d'entité en doublon), les trois positions du contrôle d'équipement, compteurs de
  // l'équipement lus (zéros masqués).
  if (await panel.locator('.j2ha-group-head').count() !== 0) throw new Error('eq-cible-plusieurs-entites');
  if (await panel.locator('.j2ha-group-head button').count() !== 0) throw new Error('actions-entite-doublons-visibles');
  helpers.record('actions_entite_masquees', true);
  await waitAtStep(helpers, '6a', 'compteurs-equipement', () => panel.locator('.j2ha-eq-counter').first().waitFor({ state: 'visible' }));
  const counterTexts = await panel.locator('.j2ha-eq-counter').evaluateAll((nodes) => nodes.map((node) => (node.textContent ?? '').trim()));
  if (counterTexts.length < 1 || !counterTexts.every((text) => /^\d+ (publiées?|à appliquer|bloquées?|ignorées?|exclues?)$/.test(text))) {
    throw new Error('compteurs-eq-cible-illisibles');
  }
  counterTexts.forEach((text, index) => helpers.record(`eq_cible_compteur_${index + 1}`, text));

  const controls = panel.locator('.j2ha-eq-controls');
  // La modale de pièce de Jeedom reste `aria-hidden="true"` une fois ouverte,
  // donc un `getByRole` par défaut n'y trouve rien : `includeHidden: true` est
  // nécessaire pour la localisation ; `click()` continue d'exiger la visibilité réelle.
  const excludeButton = controls.getByRole('radio', { name: EXCLUDE_LABEL, exact: true, includeHidden: true });
  const revertButton = controls.getByRole('radio', { name: REVERT_LABEL, exact: true, includeHidden: true });

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
  // La modale de confirmation est aussi une bootbox `aria-hidden="true"` : un
  // `getByRole` ne la verrait jamais, rendant ce garde-fou inopérant — un
  // locator CSS voit les boutons visibles même sous un ancêtre `aria-hidden`.
  if (await page.locator('.bootbox button:visible', { hasText: /^\s*Confirmer\s*$/ }).count() > 0) {
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
  // l'équipement : « Jamais » devient la position courante (déjà exclu), « Automatique »
  // reste le moyen de retirer l'exclusion (point 3).
  await waitAtStep(helpers, 9, 'etat-boutons-apres-exclusion', async () => {
    await waitForSegmentState(page, eqId, EXCLUDE_LABEL, { checked: true, disabled: false });
    await waitForSegmentState(page, eqId, REVERT_LABEL, { checked: false, disabled: false });
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
  // Après le retrait : « Jamais » n'est plus la position courante mais redevient choisissable.
  await waitAtStep(helpers, 12, 'etat-bouton-final', async () => {
    await waitForSegmentState(page, eqId, EXCLUDE_LABEL, { checked: false, disabled: false });
    await waitForSegmentState(page, eqId, REVERT_LABEL, { checked: true, disabled: false });
  });
}
