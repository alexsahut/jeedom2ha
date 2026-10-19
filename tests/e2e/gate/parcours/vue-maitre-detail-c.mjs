/** Story 25.4 : la vue de travail maître-détail (C), en lecture seule.
 *
 * Aucune écriture : aucun clic ne confirme une action destructrice (la confirmation est annulée). La politique
 * d'interception du gate n'est pas modifiée : `getEquipmentStates` et `getMappingOverrides` y sont déjà des lectures ;
 * les exigences propres à la vue (zéro lecture à l'ouverture, une lecture à la sélection, état d'URL, disposition) sont
 * portées par ce parcours, qui compte lui-même les requêtes du plugin après son démarrage. Vrais clics Playwright
 * (contrôle d'actionnabilité : ce qui est caché, recouvert ou réduit à 2 px fait échouer le parcours).
 *
 * Assertions (étiquettes d'erreur distinctes) : (1) ouvrir la vue depuis une carte n'émet aucune lecture ; (2) l'arbre
 * contient toutes les pièces de la page B et ses repères somment aux nombres de la page B ; (3) la recherche et chaque
 * puce non vide filtrent sans requête du plugin, les effectifs égalent le nombre de lignes ; (4) sélectionner un
 * équipement émet UNE lecture d'arbre et rend le tableau des commandes, la pastille de l'arbre égale le badge du détail ;
 * (6) le lien profond rouvre la même sélection avec un getEquipmentStates et un getMappingOverrides ; (7) à deux largeurs
 * de viewport, `data-j2ha-layout` vaut `split` puis `compact`, aucun défilement horizontal dans le détail, le tiroir
 * « Pièces » s'ouvre et se ferme, sans requête ; (8) le bouton « Précédent » remonte équipement → pièce → page principale ;
 * (9) ouvrir le menu « ⋯ » de pièce puis annuler la confirmation de suppression n'émet aucune écriture.
 *
 * Story 25.6 : une carte ouvre la vue sur la PIÈCE SEULE (`data-j2ha-scope="piece"`). L'étape 2 vérifie d'abord cette portée
 * (`portee-piece-seule` : une seule pièce dans l'arbre, ses repères égaux à ceux de la carte, `seule:1` dans l'URL), puis
 * active « Toutes les pièces » sans requête du plugin (`requete-pendant-elargissement`) et exécute SANS CHANGEMENT les
 * assertions existantes (toutes les pièces de la page, mêmes repères). Étapes 3 à 9 inchangées dans leurs exigences.
 *
 * Story 25.7 : l'étape 10 (`cause-exclusion`, lecture seule) vérifie, dans l'arbre élargi filtré sur « exclus et autres »,
 * que chaque ligne « Exclu » porte une mention de cause de la forme du glossaire (ou aucune), qu'aucune ligne « Désactivé »
 * n'en porte, et que la somme des repères « N exclus » des cartes égale le nombre de lignes « Exclu » ; zéro requête du plugin.
 *
 * L'assertion (5) (réponse tardive d'une sélection abandonnée, jamais rendue) n'est PAS portée par ce parcours : l'interception
 * du gate ne retarde pas une réponse à la demande et n'est pas modifiée pour cela. Elle est prouvée en vrai Chromium par
 * `tests/unit/test_story_25_4_navigateur_reel.node.test.js` (réseau factice retardé), report consigné au Dev Agent Record.
 */

export const name = 'vue-maitre-detail-c';
export const declaredEquipments = {};
export const declaredBascules = [];
export const declaredRescan = false;

const WRITE_ACTIONS = ['executeHaAction', 'exportDiagnostic', 'scanTopology', 'saveMappingOverride', 'savePublicationOverride', 'revertPublicationOverride', 'revertMappingOverride'];

async function atStep(helpers, index, label, operation) {
  helpers.record(`etape_${index}`, label);
  try {
    return await operation();
  } catch (error) {
    const message = error instanceof Error ? error.message.split(/\r?\n/, 1)[0] : String(error);
    throw new Error(`etape ${label} : ${message}`);
  }
}

const reads = (helpers, action) => helpers.journalEntries().filter((entry) => entry.action === action).length;

// Seules les requêtes du plugin comptent : le cœur Jeedom (événements, santé) peut interroger la box sans lien avec la vue.
const pluginCalls = (helpers) => helpers.journalEntries()
  .filter((entry) => ['fetch', 'xhr'].includes(entry.resourceType) && String(entry.path ?? '').startsWith('/plugins/jeedom2ha/core/ajax/'))
  .length;

const VIEW = '#j2ha_workView';

/** Relève, AVANT l'ouverture de la vue, les cartes de la page principale (la grille est masquée ensuite). */
async function readCards(page) {
  return page.locator('#j2ha_roomCards .j2ha-room-card').evaluateAll((cards) => cards.map((card) => ({
    id: card.getAttribute('data-object_id'),
    ratio: (card.querySelector('.j2ha-room-ratio')?.textContent ?? '').replace(/ publiés?$/, '').trim(),
    excluded: Number(((card.querySelector('.j2ha-room-marks .j2ha-mark-excluded')?.textContent ?? '').match(/^\d+/) ?? ['0'])[0]),
    // Les repères « non lus » (25.3) et « N exclus » (25.7) n'ont pas d'équivalent dans les repères de l'arbre.
    marks: [...card.querySelectorAll('.j2ha-room-marks .j2ha-mark')].map((mark) => (mark.textContent ?? '').trim()).filter((text) => !/non lus?$|exclus?$/.test(text)),
  })));
}

/** (1) Ouvrir la vue depuis une carte n'émet aucune lecture (ni état ni arbre). */
async function checkOpen(page, helpers) {
  const states = reads(helpers, 'getEquipmentStates');
  const trees = reads(helpers, 'getMappingOverrides');
  const calls = pluginCalls(helpers);
  await page.locator('#j2ha_roomCards .j2ha-room-card').first().click();
  await page.locator(VIEW).waitFor({ state: 'visible' });
  if (reads(helpers, 'getEquipmentStates') !== states || reads(helpers, 'getMappingOverrides') !== trees || pluginCalls(helpers) !== calls) {
    throw new Error('lecture-a-l-ouverture');
  }
  helpers.record('lectures_a_l_ouverture', 0);
}

/**
 * (2, Story 25.6) Depuis une carte : l'arbre ne contient QUE la pièce de la carte cliquée, ses repères égalent ceux de la
 * carte, l'URL porte `seule:1` ; puis « Toutes les pièces » élargit sans aucune requête du plugin.
 */
async function checkScopeAndWiden(page, helpers, cards) {
  const opened = cards[0];
  const scope = await page.locator(VIEW).getAttribute('data-j2ha-scope');
  const rooms = await page.locator(`${VIEW} .j2ha-wv-tree .j2ha-wv-room`).evaluateAll((nodes) => nodes.map((room) => ({
    id: room.getAttribute('data-object_id'),
    ratio: (room.querySelector('.j2ha-wv-ratio')?.textContent ?? '').trim(),
    marks: [...room.querySelectorAll(':scope > .j2ha-wv-row .j2ha-wv-room-marks .j2ha-mark')].map((mark) => (mark.textContent ?? '').trim()),
  })));
  const hash = await page.evaluate(() => window.location.hash);
  if (scope !== 'piece' || rooms.length !== 1 || rooms[0].id !== opened.id || !/;seule:1$/.test(hash)) throw new Error('portee-piece-seule');
  if (rooms[0].ratio !== opened.ratio || JSON.stringify(rooms[0].marks) !== JSON.stringify(opened.marks)) throw new Error('portee-piece-seule');
  helpers.record('portee_ouverture', 'piece');
  helpers.record('pieces_arbre_portee_piece', rooms.length);
  const before = pluginCalls(helpers);
  await page.locator(`${VIEW} .j2ha-wv-widen`).click();
  await page.waitForFunction((selector) => document.querySelector(selector)?.getAttribute('data-j2ha-scope') === 'toutes', VIEW, { timeout: 5000 })
    .catch(() => { throw new Error('portee-piece-seule'); });
  if (pluginCalls(helpers) !== before) throw new Error('requete-pendant-elargissement');
  helpers.record('requetes_pendant_elargissement', 0);
}

/** (2) L'arbre contient toutes les pièces de la page B ; ses repères somment aux nombres de la page B. */
async function checkTree(page, helpers, cards) {
  const tree = await page.locator(`${VIEW} .j2ha-wv-room`).evaluateAll((rooms) => rooms.map((room) => ({
    id: room.getAttribute('data-object_id'),
    ratio: (room.querySelector('.j2ha-wv-ratio')?.textContent ?? '').trim(),
    marks: [...room.querySelectorAll(':scope > .j2ha-wv-row .j2ha-wv-room-marks .j2ha-mark')].map((mark) => (mark.textContent ?? '').trim()),
  })));
  const same = (a, b) => JSON.stringify([...a].sort()) === JSON.stringify([...b].sort());
  if (!same(tree.map((room) => room.id), cards.map((card) => card.id))) throw new Error('arbre-pieces-differentes-de-la-page');
  for (const card of cards) {
    const room = tree.find((item) => item.id === card.id);
    if (!room || room.ratio !== card.ratio || JSON.stringify(room.marks) !== JSON.stringify(card.marks)) {
      throw new Error('reperes-arbre-differents-de-la-page');
    }
  }
  const sum = (selector) => page.locator(`${VIEW} ${selector}`).evaluateAll((nodes) => nodes.reduce((n, node) => n + Number((node.textContent ?? '').replace(/[^0-9].*$/, '') || 0), 0));
  helpers.record('pieces_arbre', tree.length);
  helpers.record('reperes_bloques', await sum('.j2ha-wv-room-marks .j2ha-mark-blocked'));
}

/** (3) La recherche et chaque puce non vide filtrent sans requête du plugin ; les effectifs égalent le nombre de lignes. */
async function checkFilters(page, helpers) {
  const before = pluginCalls(helpers);
  const chips = page.locator(`${VIEW} .j2ha-wv-chips .j2ha-chip-filter:not([disabled])`);
  const count = await chips.count();
  if (count === 0) throw new Error('aucune-puce-active');
  for (let index = 0; index < count; index += 1) {
    const chip = chips.nth(index);
    const announced = Number(((await chip.textContent()) ?? '').replace(/[^0-9].*$/, '').trim());
    await chip.click();
    const rows = await page.locator(`${VIEW} .j2ha-wv-tree .j2ha-wv-eq`).count();
    if (rows !== announced) throw new Error('lignes-filtre-differentes-du-nombre');
    await chip.click();
  }
  // Recherche : les deux premiers caractères du nom de la première pièce (jamais enregistrés).
  const query = ((await page.locator(`${VIEW} .j2ha-wv-room .j2ha-wv-name`).first().innerText()) ?? '').trim().slice(0, 2);
  const search = page.locator(`${VIEW} .j2ha-wv-search`);
  await search.fill(query);
  await page.waitForTimeout(400);
  if ((await page.locator(`${VIEW} .j2ha-wv-room`).count()) < 1) throw new Error('recherche-sans-resultat');
  await search.fill('');
  await page.waitForTimeout(400);
  if (pluginCalls(helpers) !== before) throw new Error('requete-pendant-filtre');
  helpers.record('puces_controlees', count);
  helpers.record('requetes_pendant_filtres', 0);
}

/** (4) Sélectionner un équipement : UNE lecture d'arbre, tableau des commandes, pastille de l'arbre = badge du détail. */
async function checkSelection(page, helpers) {
  const before = reads(helpers, 'getMappingOverrides');
  const row = page.locator(`${VIEW} .j2ha-wv-eq`).first();
  const eqId = await row.getAttribute('data-eq-id');
  const treeWord = ((await row.locator('.j2ha-state-word').first().innerText()) ?? '').trim();
  const started = Date.now();
  await row.locator('.j2ha-wv-row').click();
  const panel = page.locator(`${VIEW} .j2ha-eq-panel[data-eq-id="${eqId}"]`);
  await panel.locator('.j2ha-cmd-table').waitFor({ state: 'visible' });
  // Chronométrage du chargement d'un équipement sélectionné (valeur seulement, aucun seuil) : réserve de 25.3.
  helpers.record('temps_chargement_eq_selectionne_ms', Date.now() - started);
  if (reads(helpers, 'getMappingOverrides') - before !== 1) throw new Error('selection-lecture-arbre-inattendue');
  const badge = ((await panel.locator('.j2ha-eq-publish-badge').innerText()) ?? '').trim();
  if (treeWord && badge !== treeWord) throw new Error('pastille-arbre-differente-du-badge');
  helpers.record('eq_id_selectionne', Number(eqId));
  helpers.record('lectures_arbre_selection', 1);
  return eqId;
}

/** (6) Lien profond : recharger la page avec l'état d'URL rouvre la même sélection (1 + 1 lectures). */
async function checkDeepLink(page, helpers, eqId) {
  const hash = await page.evaluate(() => window.location.hash);
  if (!/^#j2ha-vue=piece:\d+;eq:\d+/.test(hash)) throw new Error('lien-profond-selection-perdue');
  const states = reads(helpers, 'getEquipmentStates');
  const trees = reads(helpers, 'getMappingOverrides');
  await page.reload();
  await page.locator(`${VIEW} .j2ha-eq-panel[data-eq-id="${eqId}"] .j2ha-cmd-table`).waitFor({ state: 'visible', timeout: 30_000 }).catch(() => {
    throw new Error('lien-profond-selection-perdue');
  });
  // Les deux lectures du rechargement partent en parallèle : l'arbre unitaire (≈ 70 ms) peut être rendu avant que la
  // lecture des états (≈ 300 ms) n'arrive au journal. Attente bornée de l'une ET l'autre, puis égalité stricte (pas plus).
  const deadline = Date.now() + 15_000;
  while ((reads(helpers, 'getEquipmentStates') - states < 1 || reads(helpers, 'getMappingOverrides') - trees < 1) && Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  await new Promise((resolve) => setTimeout(resolve, 1000));
  if (reads(helpers, 'getEquipmentStates') - states !== 1 || reads(helpers, 'getMappingOverrides') - trees !== 1) {
    throw new Error('lien-profond-lectures');
  }
  helpers.record('lien_profond_lectures_etat', 1);
  helpers.record('lien_profond_lectures_arbre', 1);
}

/** (7) Disposition : `split` au-dessus du seuil, `compact` en dessous ; pas de défilement horizontal ; tiroir « Pièces ». */
async function checkLayout(page, helpers) {
  const threshold = await page.evaluate(() => window.Jeedom2haWorkview?.LAYOUT_SPLIT_MIN_WIDTH);
  if (!Number.isInteger(threshold)) throw new Error('disposition-inattendue');
  const before = pluginCalls(helpers);
  const original = page.viewportSize() ?? { width: 1280, height: 800 };
  // La disposition suit matchMedia (événement asynchrone après le redimensionnement) : attente bornée de la valeur attendue.
  const waitLayout = (expected) => page.waitForFunction(([selector, value]) => document.querySelector(selector)?.getAttribute('data-j2ha-layout') === value, [VIEW, expected], { timeout: 5000 })
    .catch(() => { throw new Error('disposition-inattendue'); });
  const overflow = () => page.locator(`${VIEW} .j2ha-wv-detail`).evaluate((node) => node.scrollWidth - node.clientWidth);
  try {
    await page.setViewportSize({ width: threshold + 200, height: 900 });
    await waitLayout('split');
    helpers.record('largeur_fenetre_large', await page.evaluate(() => window.innerWidth));
    if ((await overflow()) > 1) throw new Error('defilement-horizontal-detail');
    await page.setViewportSize({ width: threshold - 200, height: 900 });
    await waitLayout('compact');
    helpers.record('largeur_fenetre_etroite', await page.evaluate(() => window.innerWidth));
    if ((await overflow()) > 1) throw new Error('defilement-horizontal-detail');
    const toggle = page.locator(`${VIEW} .j2ha-wv-drawer-toggle`);
    await toggle.click();
    if ((await toggle.getAttribute('aria-expanded')) !== 'true' || !(await page.locator(`${VIEW} .j2ha-wv-nav`).isVisible())) throw new Error('tiroir-pieces-inoperant');
    await toggle.click();
    if ((await toggle.getAttribute('aria-expanded')) !== 'false' || (await page.locator(`${VIEW} .j2ha-wv-nav`).isVisible())) throw new Error('tiroir-pieces-inoperant');
    if (pluginCalls(helpers) !== before) throw new Error('requete-pendant-changement-de-disposition');
  } finally {
    await page.setViewportSize(original);
  }
  helpers.record('requetes_pendant_disposition', 0);
}

/** (8) « Précédent » remonte équipement → pièce → page principale. */
async function checkBack(page, helpers) {
  await page.goBack();
  await page.locator(`${VIEW} .j2ha-eq-panel`).waitFor({ state: 'detached', timeout: 10_000 }).catch(() => { throw new Error('precedent-ne-remonte-pas'); });
  if (!(await page.locator(VIEW).isVisible())) throw new Error('precedent-ne-remonte-pas');
  await page.goBack();
  await page.locator(VIEW).waitFor({ state: 'hidden', timeout: 10_000 }).catch(() => { throw new Error('precedent-ne-remonte-pas'); });
  if (!(await page.locator('#j2ha_roomCards').isVisible())) throw new Error('precedent-ne-remonte-pas');
  helpers.record('precedent_niveaux', 2);
}

/** (10, Story 25.7) Cause d'exclusion : mentions de l'arbre conformes au glossaire, jamais sur un « Désactivé », somme des cartes = lignes « Exclu ». */
async function checkExclusionCause(page, helpers, cards) {
  const before = pluginCalls(helpers);
  if ((await page.locator(VIEW).getAttribute('data-j2ha-scope')) === 'piece') await page.locator(`${VIEW} .j2ha-wv-widen`).click();
  const chip = page.locator(`${VIEW} .j2ha-wv-chips .j2ha-chip-filter[data-filter="other"]`);
  const usable = (await chip.count()) > 0 && !(await chip.isDisabled());
  if (usable) await chip.click();
  const rows = await page.locator(`${VIEW} .j2ha-wv-tree .j2ha-wv-eq`).evaluateAll((items) => items.map((item) => ({
    state: (item.querySelector('.j2ha-state-word')?.textContent ?? '').trim(),
    cause: item.querySelector('.j2ha-wv-cause') ? (item.querySelector('.j2ha-wv-cause').textContent ?? '').trim() : null,
  })));
  const FORM = /^(par le plugin .+|par son plugin|par la pièce|individuelle)$/;
  const excluded = rows.filter((row) => row.state === 'Exclu');
  if (excluded.some((row) => row.cause !== null && !FORM.test(row.cause))) throw new Error('cause-exclusion-hors-glossaire');
  if (rows.some((row) => row.state !== 'Exclu' && row.cause !== null)) throw new Error('cause-sur-desactive');
  const fromCards = cards.reduce((n, card) => n + card.excluded, 0);
  if (fromCards !== excluded.length) throw new Error('exclus-carte-differents-de-l-arbre');
  if (usable) await chip.click();
  if (pluginCalls(helpers) !== before) throw new Error('requete-pendant-cause-exclusion');
  const count = (re) => excluded.filter((row) => row.cause !== null && re.test(row.cause)).length;
  helpers.record('exclus_par_plugin', count(/^par (le|son) plugin/));
  helpers.record('exclus_par_piece', count(/^par la pièce$/));
  helpers.record('exclus_individuels', count(/^individuelle$/));
  helpers.record('exclus_sans_cause', excluded.filter((row) => row.cause === null).length);
}

/** (9) Le menu « ⋯ » de pièce, puis l'annulation de la confirmation de suppression : aucune écriture. */
async function checkRoomMenu(page, helpers) {
  await page.locator('#j2ha_roomCards .j2ha-room-card').first().click();
  await page.locator(VIEW).waitFor({ state: 'visible' });
  const toggle = page.locator(`${VIEW} .j2ha-menu-toggle`);
  await toggle.click();
  const danger = page.locator(`${VIEW} .j2ha-room-recreate`);
  if (await danger.isDisabled()) {
    helpers.record('supprimer_piece_grise', true);
  } else {
    await danger.click();
    const confirmation = page.locator('.bootbox .btn-danger');
    await confirmation.waitFor({ state: 'visible' });
    await page.locator('.bootbox .btn-default').filter({ hasText: /^Annuler$/ }).first().click();
    await confirmation.waitFor({ state: 'hidden' });
    helpers.record('supprimer_piece_grise', false);
  }
  const writes = helpers.journalEntries().filter((entry) => WRITE_ACTIONS.includes(entry.action)).length;
  if (writes !== 0) throw new Error('ecriture-emise-par-le-menu-de-piece');
  helpers.record('ecritures_menu_piece', writes);
}

export async function run(page, { helpers }) {
  await page.locator('#j2ha_houseNumber').waitFor({ state: 'attached' });
  await page.waitForFunction(() => (document.querySelector('#j2ha_houseNumber')?.textContent ?? '').trim() !== '');
  const cards = await readCards(page);
  await atStep(helpers, 1, 'ouverture-sans-lecture', () => checkOpen(page, helpers));
  await atStep(helpers, 2, 'arbre-et-reperes', async () => {
    await checkScopeAndWiden(page, helpers, cards);
    await checkTree(page, helpers, cards);
  });
  await atStep(helpers, 3, 'recherche-et-filtres', () => checkFilters(page, helpers));
  const eqId = await atStep(helpers, 4, 'selection-un-arbre', () => checkSelection(page, helpers));
  await atStep(helpers, 6, 'lien-profond', () => checkDeepLink(page, helpers, eqId));
  await atStep(helpers, 7, 'disposition', () => checkLayout(page, helpers));
  await atStep(helpers, 8, 'precedent', () => checkBack(page, helpers));
  await atStep(helpers, 9, 'menu-de-piece', () => checkRoomMenu(page, helpers));
  await atStep(helpers, 10, 'cause-exclusion', () => checkExclusionCause(page, helpers, cards));
}
