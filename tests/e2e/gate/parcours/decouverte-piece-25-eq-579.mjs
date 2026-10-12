/** Parcours de découverte lecture seule : pièce 25 puis équipement 579 (étendu en 20.3 :
 * absence de la synthèse et de la modale Diagnostic, chaînes interdites, compteurs de la pièce). */

export const name = 'decouverte-piece-25-eq-579';
export const declaredEquipments = {};
export const declaredPublicationOverrides = {};
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
      'j2ha-diag-disabled',
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
    if (diagnostic?.classList.contains('j2ha-diag-disabled')) state = 'desactive';
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
      'j2ha-publish-disabled',
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
    if (badge?.classList.contains('j2ha-publish-disabled')) state = 'desactive';
    return { id: item.getAttribute('data-eq-id'), state };
  }));
}

// Story 20.3 (AC6, AC10) : chaînes interdites dans le texte rendu (gabarit Jeedom et jargon
// d'infrastructure). Les motifs sont repris de la table validée par Alexandre le 2026-10-08.
const FORBIDDEN_TEXT = [
  /mapping/i, /Template/i, /Mes templates/, /Paramètre n°1/, /Paramètres spécifiques/,
  /Écart/, /Ecart/, /Confiance/, /\beq_id\b/, /\breason_code\b/, /Parc global/,
  /Synthèse du périmètre/, /Diagnostic de Couverture/, /Parité FAN/, /generic_type/,
];

// Story 20.3 (R1-H) : noms libres saisis par l'utilisateur (pièces, équipements, commandes) et retours
// d'action qui les citent. Ils sont exclus du gate : seuls les libellés statiques (titres, entêtes,
// boutons, badges) sont contrôlés.
const FREE_TEXT_SELECTOR = '.j2ha-free-name, .j2ha-eq-name, .mo-td-name, .j2ha-room-feedback';

/** Lit le texte statique rendu d'un conteneur (jamais les scripts ni les noms libres) et renvoie les rangs des motifs interdits trouvés. */
async function forbiddenTextRanks(page, selector) {
  const text = await page.locator(selector).first().evaluate((node, freeSelector) => {
    const clone = node.cloneNode(true);
    clone.querySelectorAll(freeSelector).forEach((item) => item.remove());
    return clone.textContent ?? '';
  }, FREE_TEXT_SELECTOR);
  const ranks = [];
  FORBIDDEN_TEXT.forEach((pattern, rank) => { if (pattern.test(text)) ranks.push(rank + 1); });
  return ranks;
}

/** Story 20.3 (AC1, AC2, AC10) : la synthèse et l'action Diagnostic n'existent plus dans le DOM. */
async function checkRemovedElements(page, helpers) {
  const dom = await page.evaluate(() => ({
    synthese: Boolean(document.querySelector('#div_scopeSummary')),
    boutonSynthese: Boolean(document.querySelector('#bt_refreshScopeSummary')),
    parcGlobal: (document.querySelector('.eqLogicThumbnailDisplay')?.textContent ?? '').includes('Parc global'),
    actionDiagnostic: Boolean(document.querySelector('[data-action="diagnostic"]')),
    exportSupport: Boolean(document.querySelector('#bt_exportDiagnostic')),
  }));
  if (dom.synthese) throw new Error('synthese-presente');
  if (dom.boutonSynthese) throw new Error('bouton-synthese-present');
  if (dom.parcGlobal) throw new Error('parc-global-present');
  if (dom.actionDiagnostic) throw new Error('action-diagnostic-presente');
  if (!dom.exportSupport) throw new Error('export-support-absent');
  helpers.record('absence_synthese', true);
  helpers.record('absence_action_diagnostic', true);
  helpers.record('export_support_present', true);
  const loadRequests = helpers.journalEntries().filter((entry) => (
    entry.action === 'getPublishedScopeForConsole' || entry.action === 'getDiagnostics'
  )).length;
  if (loadRequests !== 0) throw new Error('lecture-synthese-ou-diagnostic');
  helpers.record('lectures_synthese_diagnostic', loadRequests);
}

/** Relève les compteurs de la pièce ouverte : 5 d'équipements (publiés, en attente, non pris en
 * charge, exclus, désactivés) puis 3 de commandes (publiées, en attente, non prises en charge). */
async function readRoomCounters(modal, helpers, prefix) {
  const counters = await modal.locator('.j2ha-room-counter').evaluateAll((nodes) => nodes.map((node) => (node.textContent ?? '').trim()));
  if (counters.length !== 8) throw new Error('compteurs-piece-incomplets');
  counters.forEach((text, index) => {
    if (!/^\d+ (équipements?|commandes?) /.test(text)) throw new Error('compteur-piece-illisible');
    helpers.record(`${prefix}_compteur_${index + 1}`, text);
  });
}

/** Story 22.2 (AC2, AC3, AC5) : équipement 579 (plusieurs entités, commande 5369 portée par plusieurs
 * entités). Lecture seule : aucun clic sur une action, aucun choix dans un sélecteur. */
async function checkMultiEntityEquipment(panel, helpers) {
  await panel.locator('.j2ha-eq-counter').first().waitFor({ state: 'visible' });
  const counters = await panel.locator('.j2ha-eq-counter').evaluateAll((nodes) => nodes.map((node) => (node.textContent ?? '').trim()));
  if (counters.length < 3 || !counters.slice(0, 3).every((text) => /^\d+ commandes? /.test(text))) {
    throw new Error('compteurs-eq-579-illisibles');
  }
  counters.forEach((text, index) => helpers.record(`eq_579_compteur_${index + 1}`, text));
  // Plusieurs entités : chaque ligne garde ses trois actions, libellées « cette entité ».
  const rows = await panel.locator('.j2ha-entity-row').evaluateAll((nodes) => nodes.map((node) => (
    [...node.querySelectorAll('button')].map((button) => (button.textContent ?? '').trim())
  )));
  if (rows.length < 2) throw new Error('eq-579-moins-de-deux-entites');
  rows.forEach((labels, index) => {
    if (labels.length !== 3 || !labels.every((label) => /cette entité/.test(label))) throw new Error('actions-entite-579-inattendues');
    helpers.record(`eq_579_entite_${index + 1}_actions`, labels.length);
  });
  const equipmentLabels = await panel.locator('.j2ha-eq-actions .j2ha-publication-actions button')
    .evaluateAll((nodes) => nodes.map((node) => (node.textContent ?? '').trim()));
  if (!equipmentLabels.every((label) => /équipement/.test(label)) || equipmentLabels.length !== 3) {
    throw new Error('actions-equipement-579-inattendues');
  }
  helpers.record('eq_579_actions_equipement', equipmentLabels.length);
  // Commande 5369 : portée par plusieurs entités, sélecteur « Override HA » désactivé et expliqué (CC-58).
  const shared = panel.locator('tr.mapping-override-cmd[data-cmd-id="5369"] select');
  if (await shared.count() !== 1) throw new Error('cmd-5369-absente');
  if (!(await shared.isDisabled())) throw new Error('selecteur-5369-actif');
  const title = (await shared.getAttribute('title')) ?? '';
  if (!/portée par plusieurs entités/.test(title)) throw new Error('selecteur-5369-sans-explication');
  helpers.record('selecteur_5369_desactive', true);
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

/** Ouvre la pièce 25, déplie l'équipement 579 et consigne les constats DOM non sensibles. */
export async function run(page, { helpers }) {
  const managementOrder = await page.locator('.eqLogicThumbnailContainer').evaluateAll((nodes) => {
    const actions = nodes.find((node) => node.querySelector('[data-action="gotoPluginConf"]'));
    const surface = document.querySelector('#j2ha_roomCards');
    const banner = document.querySelector('#div_bridgeHealthBanner');
    return {
      beforeSurface: Boolean(actions && surface && (actions.compareDocumentPosition(surface) & Node.DOCUMENT_POSITION_FOLLOWING)),
      beforeBanner: Boolean(actions && banner && (actions.compareDocumentPosition(banner) & Node.DOCUMENT_POSITION_FOLLOWING)),
    };
  });
  if (!managementOrder.beforeSurface) throw new Error('gestion-apres-surface');
  if (!managementOrder.beforeBanner) throw new Error('gestion-apres-bandeau');
  helpers.record('gestion_avant_surface', true);
  helpers.record('gestion_avant_bandeau', true);
  await waitAtStep(helpers, 0, 'elements-retires', () => checkRemovedElements(page, helpers));
  const pageRanks = await forbiddenTextRanks(page, '.eqLogicThumbnailDisplay');
  const editRanks = await forbiddenTextRanks(page, '.eqLogic');
  if (pageRanks.length || editRanks.length) throw new Error(`chaine-interdite-page-${[...pageRanks, ...editRanks].join('-')}`);
  helpers.record('chaines_interdites_page', 0);
  const journalBeforeRoom = helpers.journalEntries().filter((entry) => entry.action === 'getMappingOverrides').length;
  if (journalBeforeRoom !== 0) throw new Error('lecture-mapping-avant-piece');
  helpers.record('mapping_avant_piece', 0);
  const unassigned = page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="0"]');
  const unassignedCount = await unassigned.count();
  if (unassignedCount > 1) throw new Error('cartes-sans-piece-dupliquees');
  helpers.record('sans_piece_presente', unassignedCount === 1);
  if (unassignedCount === 1) {
    const countText = await unassigned.locator('.text-muted').innerText();
    const count = Number(countText.replace(/[^0-9]/g, ''));
    if (!Number.isInteger(count) || count < 1) throw new Error('compte-sans-piece-illisible');
    helpers.record('sans_piece_equipements', count);
  }
  const roomCard = page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="25"]');
  await waitAtStep(helpers, 1, 'carte-piece-25', () => roomCard.click());

  const modal = page.locator('.modal-j2ha-room');
  await waitAtStep(helpers, 2, 'modale', () => modal.waitFor({ state: 'visible' }));
  const panel = modal.locator('.j2ha-eq-panel[data-eq-id="579"]');
  await waitAtStep(helpers, 3, 'panneau-eq-579', () => panel.waitFor({ state: 'visible' }));

  const eqId = await panel.getAttribute('data-eq-id');
  if (!/^\d+$/.test(eqId ?? '')) throw new Error('eqid-eq-579-illisible');
  await waitAtStep(helpers, 4, 'depliage', async () => {
    await panel.locator('.j2ha-eq-toggle').click();
    await panel.locator('.panel-collapse').waitFor({ state: 'visible' });
  });
  await waitAtStep(helpers, 5, 'table', () => {
    return panel.locator('.j2ha-cmd-table').waitFor({ state: 'visible' });
  });
  await waitAtStep(helpers, 6, 'diagnostics', () => waitForDiagnostics(page, eqId));

  helpers.record('eq_id', Number(eqId));
  await waitAtStep(helpers, '6a', 'multi-entites-eq-579', () => checkMultiEntityEquipment(panel, helpers));
  for (const command of await readCommandStates(panel)) {
    if (!/^\d+$/.test(command.id ?? '')) throw new Error('cmdid-eq-579-illisible');
    helpers.record(`cmd_${command.id}_id`, Number(command.id));
    helpers.record(`cmd_${command.id}_etat`, command.state);
  }
  const summary = (await panel.locator('.j2ha-eq-publish-badge').innerText()).trim();
  if (!summary) throw new Error('synthese-eq-579-illisible');
  helpers.record('synthese', summary);
  for (const equipment of await readEquipmentBadgeStates(page, modal)) {
    if (!/^\d+$/.test(equipment.id ?? '')) throw new Error('eqid-badge-illisible');
    helpers.record(`eq_${equipment.id}_badge`, equipment.state);
  }
  const disabledPanel = modal.locator('.j2ha-eq-panel[data-eq-id="514"]');
  await waitAtStep(helpers, 7, 'diagnostics-eq-514', () => waitForDiagnostics(page, '514'));
  const disabledBadge = (await disabledPanel.locator('.j2ha-eq-publish-badge').innerText()).trim();
  if (!disabledBadge || !(await disabledPanel.locator('.j2ha-eq-publish-badge').evaluate((badge) => badge.classList.contains('j2ha-publish-disabled')))) {
    throw new Error('badge-eq-514-non-desactive');
  }
  for (const command of await readCommandStates(disabledPanel)) {
    if (command.state !== 'desactive') throw new Error('cellule-eq-514-non-desactive');
    helpers.record(`eq_514_cmd_${command.id}_etat`, command.state);
  }

  // Story 20.3 : compteurs de la pièce ouverte, chaînes interdites dans la modale, actions déplacées présentes
  // (jamais cliquées par le gate : le clic réel est une preuve terrain séparée, avec GO d'Alexandre).
  await waitAtStep(helpers, 8, 'compteurs-piece-25', () => readRoomCounters(modal, helpers, 'piece_25'));
  const roomRanks = await forbiddenTextRanks(page, '.modal-j2ha-room');
  if (roomRanks.length) throw new Error(`chaine-interdite-piece-${roomRanks.join('-')}`);
  helpers.record('chaines_interdites_piece', 0);
  const actionsPresent = await modal.evaluate((node) => ({
    republish: node.querySelectorAll('.j2ha-room-republish').length,
    recreate: node.querySelectorAll('.j2ha-room-recreate').length,
    perEquipment: node.querySelectorAll('.j2ha-eq-recreate').length,
  }));
  if (actionsPresent.republish !== 1 || actionsPresent.recreate !== 1 || actionsPresent.perEquipment < 1) {
    throw new Error('actions-deplacees-absentes');
  }
  helpers.record('actions_piece_presentes', true);

  // « Sans pièce » (quand la carte existe) : compteurs lus, aucune action de pièce.
  if (unassignedCount === 1) {
    await page.keyboard.press('Escape');
    await waitAtStep(helpers, 9, 'fermeture-piece-25', () => modal.waitFor({ state: 'detached' }));
    await waitAtStep(helpers, 10, 'carte-sans-piece', () => unassigned.click());
    const unassignedModal = page.locator('.modal-j2ha-room');
    await waitAtStep(helpers, 11, 'modale-sans-piece', () => unassignedModal.waitFor({ state: 'visible' }));
    await waitAtStep(helpers, 12, 'compteurs-sans-piece', async () => {
      await unassignedModal.locator('.j2ha-room-counter').first().waitFor({ state: 'visible' });
      await page.waitForFunction(() => {
        const panels = [...document.querySelectorAll('.modal-j2ha-room .j2ha-eq-panel')];
        return panels.length > 0 && panels.every((item) => {
          const badge = item.querySelector('.j2ha-eq-publish-badge');
          return badge && badge.textContent.trim() !== '';
        });
      });
      await readRoomCounters(unassignedModal, helpers, 'sans_piece');
    });
    const unassignedRanks = await forbiddenTextRanks(page, '.modal-j2ha-room');
    if (unassignedRanks.length) throw new Error(`chaine-interdite-sans-piece-${unassignedRanks.join('-')}`);
    const roomActions = await unassignedModal.locator('.j2ha-room-republish, .j2ha-room-recreate').count();
    if (roomActions !== 0) throw new Error('actions-piece-sans-piece');
    helpers.record('sans_piece_sans_action_piece', true);
  }
}
