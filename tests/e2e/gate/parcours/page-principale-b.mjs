/** Story 25.3 : page principale B en lecture seule (barre de santé, jauge maison filtrante, cartes, menu « ⋯ »).
 *
 * Story 25.4 : la fenêtre de pièce est remplacée par la vue de travail C. Un clic sur une puce ouvre la vue avec ce filtre
 * (l'étape 4 contrôle les mêmes exigences dans la vue, mêmes étiquettes d'erreur) ; l'étape 7 vérifie que la carte ouvre la
 * vue (lignes d'arbre > 0), sans lecture d'état supplémentaire et sans lecture d'arbre avant sélection. Vrais clics.
 *
 * Aucune écriture : aucun clic ne confirme une action destructrice (la confirmation est annulée), la boîte du
 * diagnostic est fermée sans télécharger. La politique d'interception du gate n'est pas modifiée :
 * `getEquipmentStates` y est déjà inscrit comme lecture. Elle ne distingue pas `refresh=1` ; l'assertion (5) est
 * donc portée par ce parcours, qui observe lui-même les corps des requêtes émises après son démarrage.
 */

export const name = 'page-principale-b';
export const declaredEquipments = {};
export const declaredBascules = [];
export const declaredRescan = false;

async function atStep(helpers, index, label, operation) {
  helpers.record(`etape_${index}`, label);
  try {
    return await operation();
  } catch (error) {
    const message = error instanceof Error ? error.message.split(/\r?\n/, 1)[0] : String(error);
    throw new Error(`etape ${label} : ${message}`);
  }
}

const WRITE_ACTIONS = ['executeHaAction', 'exportDiagnostic', 'scanTopology', 'saveMappingOverride', 'savePublicationOverride'];

function reads(helpers, action) {
  return helpers.journalEntries().filter((entry) => entry.action === action).length;
}

/** (1) Au chargement : une lecture d'état, aucune lecture par équipement. */
async function checkLoad(page, helpers) {
  await page.locator('#j2ha_houseNumber').waitFor({ state: 'attached' });
  await page.waitForFunction(() => (document.querySelector('#j2ha_houseNumber')?.textContent ?? '').trim() !== '');
  const states = reads(helpers, 'getEquipmentStates');
  const perEquipment = reads(helpers, 'getMappingOverrides');
  if (states !== 1) throw new Error('lectures-etat-au-chargement');
  if (perEquipment !== 0) throw new Error('lecture-par-equipement-au-chargement');
  helpers.record('lectures_etat_chargement', states);
  helpers.record('lectures_par_equipement_chargement', perEquipment);
}

/** (2) Le bandeau bleu a disparu, la ligne d'aide existe. */
async function checkNoBanner(page, helpers) {
  const dom = await page.evaluate(() => ({
    bandeau: document.querySelectorAll('.alert.alert-info.j2ha-surface-intro').length,
    aide: document.querySelectorAll('.j2ha-help-line a').length,
    barre: document.querySelectorAll('#div_bridgeHealthBanner').length,
  }));
  if (dom.bandeau !== 0) throw new Error('bandeau-bleu-present');
  if (dom.aide !== 1) throw new Error('ligne-aide-absente');
  if (dom.barre !== 1) throw new Error('barre-sante-absente');
  helpers.record('bandeau_bleu_absent', true);
}

/** (3) La jauge maison somme à M et chaque carte somme à son total. */
async function checkGauges(page, helpers) {
  const sums = await page.evaluate(() => {
    const grow = (el) => Number(el.style.flexGrow || '0');
    const houseSegments = [...document.querySelectorAll('#j2ha_houseGauge .j2ha-seg')].map(grow);
    const cards = [...document.querySelectorAll('#j2ha_roomCards .j2ha-room-card')].map((card) => ({
      total: Number((card.querySelector('.j2ha-room-count')?.textContent ?? '').replace(/[^0-9]/g, '')),
      segments: [...card.querySelectorAll('.j2ha-seg')].map(grow),
    }));
    return { houseSegments, cards };
  });
  const houseSum = sums.houseSegments.reduce((n, v) => n + v, 0);
  const total = sums.cards.reduce((n, card) => n + card.total, 0);
  if (houseSum !== total) throw new Error('jauge-maison-somme');
  for (const card of sums.cards) {
    if (card.segments.reduce((n, v) => n + v, 0) !== card.total) throw new Error('jauge-carte-somme');
  }
  helpers.record('equipements_total', total);
  helpers.record('cartes_controlees', sums.cards.length);
}

/** (4) Chaque puce non vide filtre sans requête réseau ; le nombre de lignes égale le nombre annoncé.
 * Story 25.4 : la puce de la page B ouvre la vue de travail avec ce filtre ; les lignes sont celles de l'arbre de la vue,
 * la puce pressée est celle de la vue, un second clic retire le filtre ; « Toutes les pièces » ramène à la page. */
async function checkFilters(page, helpers) {
  // Seules les requêtes du plugin comptent : le cœur Jeedom (événements, santé) peut interroger la box
  // pendant la boucle sans lien avec les filtres (constat du gate du 2026-10-19).
  const pluginCalls = () => helpers.journalEntries()
    .filter((entry) => ['fetch', 'xhr'].includes(entry.resourceType) && String(entry.path ?? '').startsWith('/plugins/jeedom2ha/core/ajax/'))
    .length;
  const before = pluginCalls();
  const chips = page.locator('#j2ha_houseChips .j2ha-chip-filter:not([disabled])');
  const count = await chips.count();
  if (count === 0) throw new Error('aucune-puce-active');
  for (let index = 0; index < count; index += 1) {
    const chip = chips.nth(index);
    const key = await chip.getAttribute('data-filter');
    const announced = Number(((await chip.textContent()) ?? '').replace(/[^0-9].*$/, '').trim());
    await chip.click();
    await page.locator('#j2ha_workView').waitFor({ state: 'visible' });
    const viewChip = page.locator(`#j2ha_workView .j2ha-wv-chips .j2ha-chip-filter[data-filter="${key}"]`);
    const rows = await page.locator('#j2ha_workView .j2ha-wv-tree .j2ha-wv-eq').count();
    if (rows !== announced) throw new Error('lignes-filtre-differentes-du-nombre');
    if ((await viewChip.getAttribute('aria-pressed')) !== 'true') throw new Error('puce-non-pressee');
    await viewChip.click();
    if ((await viewChip.getAttribute('aria-pressed')) !== 'false' || (await page.locator('#j2ha_filterList .j2ha-frow').count()) !== 0) {
      throw new Error('filtre-non-retire');
    }
    await page.locator('#j2ha_workView .j2ha-wv-back').click();
    await page.locator('#j2ha_houseChips').waitFor({ state: 'visible' });
  }
  if (pluginCalls() !== before) throw new Error('requete-pendant-filtre');
  helpers.record('puces_controlees', count);
  helpers.record('requetes_pendant_filtres', 0);
}

/** (5) « Actualiser » : une seule lecture d'état avec refresh=1, la seule de la session. */
async function checkRefresh(page, helpers) {
  const bodies = [];
  page.on('request', (observed) => {
    const body = observed.postData() ?? '';
    if (body.includes('action=getEquipmentStates')) bodies.push(body);
  });
  const before = reads(helpers, 'getEquipmentStates');
  await page.locator('#bt_refreshStates').click();
  const deadline = Date.now() + 30_000;
  while (reads(helpers, 'getEquipmentStates') < before + 1 && Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 25));
  }
  if (reads(helpers, 'getEquipmentStates') !== before + 1) throw new Error('lecture-actualiser-absente');
  await page.waitForFunction(() => document.querySelector('#bt_refreshStates')?.disabled === false);
  const refreshed = bodies.filter((body) => /(^|&)refresh=1(&|$)/.test(body)).length;
  if (refreshed !== 1) throw new Error('refresh-un-seul-attendu');
  if (bodies.length !== 1) throw new Error('lectures-etat-supplementaires');
  helpers.record('refresh_emis', refreshed);
}

/** (6) Le menu « ⋯ » : deux entrées dans l'ordre ; fermer la boîte et la confirmation n'écrit rien. */
async function checkMenu(page, helpers) {
  const toggle = page.locator('#j2ha_moreMenu .j2ha-menu-toggle');
  await toggle.click();
  if ((await toggle.getAttribute('aria-expanded')) !== 'true') throw new Error('menu-non-ouvert');
  const items = await page.locator('#j2ha_moreMenu .j2ha-menu-item').evaluateAll((nodes) => nodes.map((node) => (node.textContent ?? '').trim()));
  if (items.length !== 2 || items[0] !== 'Télécharger le diagnostic…' || items[1] !== 'Supprimer tout de Home Assistant…') {
    throw new Error('entrees-menu-inattendues');
  }
  await page.locator('#bt_openDiagnostic').click();
  const dialog = page.locator('.bootbox').filter({ has: page.locator('#cb_pseudonymize') });
  await dialog.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => { throw new Error('boite-diagnostic-absente'); });
  // Fermeture par un VRAI clic sur « Fermer » (contrôles d'actionnabilité de Playwright : un bouton masqué,
  // recouvert ou écrasé par une règle CSS fait échouer le parcours). Échap dépend du focus posé par Bootstrap
  // en fin d'animation et n'est pas exigé par la story.
  const close = dialog.locator('.btn-default').filter({ hasText: /^Fermer$/ }).first();
  await close.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => { throw new Error('bouton-fermer-absent'); });
  await close.click({ timeout: 10_000 }).catch(() => { throw new Error('bouton-fermer-non-cliquable'); });
  await dialog.waitFor({ state: 'hidden', timeout: 10_000 }).catch(() => { throw new Error('boite-diagnostic-non-fermee'); });
  const dangerous = page.locator('#j2ha_moreMenu .j2ha-menu-danger');
  if (await dangerous.isDisabled()) {
    helpers.record('supprimer_tout_grise', true);
  } else {
    await toggle.click();
    await dangerous.click();
    const confirmation = page.locator('.bootbox .btn-danger');
    await confirmation.waitFor({ state: 'visible' });
    await page.locator('.bootbox .btn-default').filter({ hasText: /^Annuler$/ }).first().click();
    await confirmation.waitFor({ state: 'hidden' });
    helpers.record('supprimer_tout_grise', false);
  }
  const writes = helpers.journalEntries().filter((entry) => WRITE_ACTIONS.includes(entry.action)).length;
  if (writes !== 0) throw new Error('ecriture-emise');
  helpers.record('ecritures_menu', writes);
}

/** (7) Non-régression de l'ouverture : une carte ouvre la vue de travail (Story 25.4, plus de fenêtre de pièce) ; l'ouverture
 * ne lit ni état ni arbre (AC28 : aucun getEquipmentStates supplémentaire, zéro getMappingOverrides avant sélection). */
async function checkRoomWindow(page, helpers) {
  const statesBefore = reads(helpers, 'getEquipmentStates');
  const card = page.locator('#j2ha_roomCards .j2ha-room-card').first();
  await card.click();
  await page.locator('#j2ha_workView').waitFor({ state: 'visible' });
  const panels = await page.locator('#j2ha_workView .j2ha-wv-tree .j2ha-wv-eq').count();
  if (panels === 0) throw new Error('fenetre-piece-vide');
  if (reads(helpers, 'getEquipmentStates') !== statesBefore) throw new Error('lecture-etat-supplementaire-a-l-ouverture');
  if (reads(helpers, 'getMappingOverrides') !== 0) throw new Error('lecture-arbre-avant-selection');
  helpers.record('equipements_fenetre_piece', panels);
}

export async function run(page, { helpers }) {
  await atStep(helpers, 1, 'chargement', () => checkLoad(page, helpers));
  await atStep(helpers, 2, 'bandeau-absent', () => checkNoBanner(page, helpers));
  await atStep(helpers, 3, 'jauges', () => checkGauges(page, helpers));
  await atStep(helpers, 4, 'filtres', () => checkFilters(page, helpers));
  await atStep(helpers, 5, 'actualiser', () => checkRefresh(page, helpers));
  await atStep(helpers, 6, 'menu', () => checkMenu(page, helpers));
  await atStep(helpers, 7, 'fenetre-piece', () => checkRoomWindow(page, helpers));
}
