/** Story 25.8 : exclusion d'une pièce depuis la surface, écriture SIMULÉE (à lancer après fusion, contre la box).
 *
 * Une pièce de test est déclarée (`declaredRoomExclusions`, identifiant technique choisi par ClaudeBox avec le GO d'Alexandre ;
 * valeur par défaut = la pièce 4, comme `controle-ecriture-non-declaree`) ainsi que la relecture (`declaredRescan`). La politique du
 * gate SIMULE `saveRoomExclusion` (réponse de la forme de la route, ids dérivés de `excludedObjects` lu en lecture seule) et
 * `scanTopology` : aucune écriture réelle n'est transmise à la box. Vrais clics Playwright.
 *
 * Assertions (étiquettes d'erreur distinctes) : (1) ouvrir le menu « ⋯ » d'une carte, à la souris puis au clavier, n'ouvre pas la
 * vue C et n'émet aucune requête du plugin (`menu-carte-ouvre-la-piece`) ; (2) la confirmation affiche un nombre entier
 * d'entités, enregistré par `record('entites_annoncees', N)` (`confirmation-sans-nombre`) ; (3) Annuler n'émet aucune écriture
 * (`ecriture-apres-annulation`) ; (4) Confirmer émet exactement `saveRoomExclusion` (simulée) puis `scanTopology` (simulée) puis
 * une lecture `getEquipmentStates`, dans cet ordre, sans autre écriture (`sequence-exclusion-inattendue`) ; (5) la carte affiche
 * « Pièce exclue » (`carte-non-marquee-exclue`) ; (6) le détail de la pièce (vue C) porte l'encart « Pièce exclue » et l'entrée
 * du menu « ⋯ » avant le séparateur, qui ouvre la confirmation « Ne plus exclure » ; annuler n'écrit rien
 * (`detail-piece-exclusion-absente`) ; (7) la carte « Sans pièce », si elle existe, n'a pas de menu (`sans-piece-excluable`) ;
 * (8) aucune écriture `saveRoomExclusion` autre que la seule écriture déclarée n'a été émise : toute autre serait BLOQUÉE par la
 * politique et consignée en échec (`exclusion-non-declaree-transmise`). Le contrôle négatif qui PROVOQUE une écriture sur une autre
 * pièce (et fait échouer le gate comme attendu) est `controle-exclusion-piece-non-declaree`.
 */

export const name = 'exclusion-piece-simulee';
export const declaredEquipments = {};
export const declaredBascules = [];
export const declaredRescan = true;
export const declaredRoomExclusions = { '4': { excluded: '1' } };

const ROOM = '4';
const CARD = `#j2ha_roomCards .j2ha-room-card[data-object_id="${ROOM}"]`;
const WRITE_ACTIONS = ['executeHaAction', 'exportDiagnostic', 'scanTopology', 'saveMappingOverride', 'savePublicationOverride',
  'revertPublicationOverride', 'revertMappingOverride', 'saveRoomExclusion', 'saveFilteringConfig'];

async function atStep(helpers, index, label, operation) {
  helpers.record(`etape_${index}`, label);
  try {
    return await operation();
  } catch (error) {
    const message = error instanceof Error ? error.message.split(/\r?\n/, 1)[0] : String(error);
    throw new Error(`etape ${label} : ${message}`);
  }
}

const entries = (helpers) => helpers.journalEntries();
const writesSince = (helpers, start) => entries(helpers).slice(start).filter((entry) => WRITE_ACTIONS.includes(entry.action));
// Seules les requêtes du plugin comptent : le cœur Jeedom (événements, santé) peut interroger la box sans lien avec la vue.
const pluginCalls = (helpers) => entries(helpers)
  .filter((entry) => ['fetch', 'xhr'].includes(entry.resourceType) && String(entry.path ?? '').startsWith('/plugins/jeedom2ha/core/ajax/'))
  .length;

/** Attend que l'entrée d'exclusion de la pièce soit active (le gating du pont est levé) ; ouvre le menu de la carte. */
async function openCardMenu(page) {
  await page.locator(CARD).waitFor({ state: 'visible' });
  await page.locator(`${CARD} .j2ha-menu-toggle`).click();
  await page.waitForFunction((selector) => {
    const item = document.querySelector(`${selector} .j2ha-room-exclude`);
    return !!item && !item.disabled;
  }, CARD);
}

/** (1) Le menu de la carte n'ouvre pas la pièce : souris puis clavier, aucune requête du plugin, fragment d'URL inchangé. */
async function checkMenuDoesNotOpenRoom(page, helpers) {
  const calls = pluginCalls(helpers);
  const hash = await page.evaluate(() => window.location.hash);
  await page.locator(CARD).waitFor({ state: 'visible' });
  // Souris, puis Entrée et Espace sur le bouton « ⋯ » : chaque ouverture est refermée par Échap avant la touche suivante (le
  // focus passe sur la première entrée du menu à l'ouverture, Échap le rend au bouton), jamais d'activation de l'entrée.
  await page.locator(`${CARD} .j2ha-menu-toggle`).click();
  await page.keyboard.press('Escape');
  await page.keyboard.press('Enter');
  await page.keyboard.press('Escape');
  await page.keyboard.press('Space');
  await page.keyboard.press('Escape');
  const opened = await page.evaluate(() => {
    const view = document.querySelector('#j2ha_workView');
    return !!view && getComputedStyle(view).display !== 'none';
  });
  if (opened || pluginCalls(helpers) !== calls || (await page.evaluate(() => window.location.hash)) !== hash) {
    throw new Error('menu-carte-ouvre-la-piece');
  }
}

/** Nombre d'entités annoncé par la confirmation (entier), ou échec si la phrase n'en porte pas. */
async function announcedEntities(page) {
  const body = (await page.locator('.bootbox .bootbox-body, .bootbox .modal-body').first().innerText()).replace(/\s+/g, ' ');
  const match = /(\d+) entités? (?:seront|sera) retirées?/.exec(body);
  if (match) return Number(match[1]);
  if (/Aucune entité n'est publiée dans cette pièce/.test(body)) return 0;
  throw new Error('confirmation-sans-nombre');
}

const cancelButton = (page) => page.locator('.bootbox .btn-default').filter({ hasText: /^Annuler$/ }).first();

export async function run(page, { helpers }) {
  await page.waitForFunction(() => (document.querySelector('#j2ha_houseNumber')?.textContent ?? '').trim() !== '');

  await atStep(helpers, 1, 'menu-carte-ouvre-la-piece', () => checkMenuDoesNotOpenRoom(page, helpers));

  // (2) La confirmation chiffrée s'ouvre depuis le menu de la carte ; aucune écriture avant le clic de confirmation.
  const beforeConfirm = entries(helpers).length;
  const announced = await atStep(helpers, 2, 'confirmation-sans-nombre', async () => {
    await openCardMenu(page);
    await page.locator(`${CARD} .j2ha-room-exclude`).click();
    await page.locator('.bootbox').first().waitFor({ state: 'visible' });
    if (writesSince(helpers, beforeConfirm).length > 0) throw new Error('ecriture-avant-confirmation');
    const count = await announcedEntities(page);
    if (!Number.isInteger(count) || count < 0) throw new Error('confirmation-sans-nombre');
    return count;
  });
  helpers.record('entites_annoncees', announced);

  // (3) Annuler n'émet aucune écriture et ferme la confirmation.
  await atStep(helpers, 3, 'ecriture-apres-annulation', async () => {
    await cancelButton(page).click();
    await page.locator('.bootbox').first().waitFor({ state: 'detached' });
    if (writesSince(helpers, beforeConfirm).length > 0) throw new Error('ecriture-apres-annulation');
  });

  // (4) Confirmer : saveRoomExclusion (simulée), scanTopology (simulée), puis UNE lecture getEquipmentStates, dans cet ordre.
  const start = entries(helpers).length;
  await atStep(helpers, 4, 'sequence-exclusion-inattendue', async () => {
    await openCardMenu(page);
    await page.locator(`${CARD} .j2ha-room-exclude`).click();
    await page.locator('.bootbox .btn-danger').first().click();
    const deadline = Date.now() + 8_000;
    while (Date.now() < deadline) {
      const since = entries(helpers).slice(start);
      if (since.some((entry) => entry.action === 'scanTopology') && since.some((entry, index) => entry.action === 'getEquipmentStates'
        && since.findIndex((other) => other.action === 'scanTopology') < index)) break;
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    const since = entries(helpers).slice(start);
    const writes = since.filter((entry) => WRITE_ACTIONS.includes(entry.action));
    const order = writes.map((entry) => `${entry.action}:${entry.verdict}`);
    if (order.join(',') !== 'saveRoomExclusion:simulee,scanTopology:simulee') throw new Error('sequence-exclusion-inattendue');
    const reads = since.filter((entry) => entry.action === 'getEquipmentStates');
    const scanAt = since.findIndex((entry) => entry.action === 'scanTopology');
    if (reads.length !== 1 || since.indexOf(reads[0]) < scanAt) throw new Error('sequence-exclusion-inattendue');
  });

  // (5) La carte affiche « Pièce exclue » à la place du ratio.
  await atStep(helpers, 5, 'carte-non-marquee-exclue', async () => {
    const card = page.locator(CARD);
    await page.waitForFunction(() => /Pièce exclue/.test(document.querySelector('#j2ha_roomCards .j2ha-room-card[data-object_id="4"] .j2ha-room-state')?.textContent ?? ''), null, { timeout: 3_000 })
      .catch(() => { throw new Error('carte-non-marquee-exclue'); });
    const text = (await card.locator('.j2ha-room-state').innerText()).replace(/\s+/g, ' ');
    const label = (await card.getAttribute('aria-label')) ?? '';
    const name = (await card.locator('.name').first().innerText()).trim();
    if (!/Pièce exclue/.test(text) || !label.startsWith(`${name}, pièce exclue`)) throw new Error('carte-non-marquee-exclue');
  });

  // (7) « Sans pièce », si elle existe, n'a pas de menu : elle n'est jamais excluable.
  await atStep(helpers, 7, 'sans-piece-excluable', async () => {
    const card = page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="0"]');
    if ((await card.count()) === 0) {
      helpers.record('sans_piece', 'absente');
      return;
    }
    if ((await card.locator('.j2ha-room-menu, .j2ha-room-exclude').count()) !== 0) throw new Error('sans-piece-excluable');
    helpers.record('sans_piece', 'sans-menu');
  });

  // (6) Détail de la pièce (vue C) : encart « Pièce exclue » et entrée du menu avant le séparateur ; annuler n'écrit rien.
  await atStep(helpers, 6, 'detail-piece-exclusion-absente', async () => {
    await page.locator(CARD).click();
    const view = page.locator('#j2ha_workView');
    await view.waitFor({ state: 'visible' });
    await view.locator('.j2ha-wv-room-excluded').waitFor({ state: 'visible' });
    const notice = (await view.locator('.j2ha-wv-room-excluded').innerText()).replace(/\s+/g, ' ');
    if (!/Pièce exclue : ses équipements ne sont pas publiés dans Home Assistant\./.test(notice)) throw new Error('detail-piece-exclusion-absente');
    const order = await view.locator('.j2ha-room-actions .j2ha-menu > li').evaluateAll((items) => items.map((item) => (
      item.getAttribute('role') === 'separator' ? 'sep' : (item.querySelector('.j2ha-room-exclude') ? 'exclusion' : 'autre'))));
    if (order[0] !== 'exclusion' || order.indexOf('sep') !== 1) throw new Error('detail-piece-exclusion-absente');
    const beforeDetail = entries(helpers).length;
    await view.locator('.j2ha-wv-room-excluded .j2ha-room-exclude').click();
    await page.locator('.bootbox').first().waitFor({ state: 'visible' });
    const title = (await page.locator('.bootbox .modal-title').first().innerText()).replace(/\s+/g, ' ');
    if (!/^Ne plus exclure la pièce/.test(title)) throw new Error('detail-piece-exclusion-absente');
    await cancelButton(page).click();
    await page.locator('.bootbox').first().waitFor({ state: 'detached' });
    if (writesSince(helpers, beforeDetail).length > 0) throw new Error('detail-piece-exclusion-absente');
  });

  // (8) Une seule écriture d'exclusion a été émise : la déclarée (toute autre aurait été bloquée et consignée en échec).
  await atStep(helpers, 8, 'exclusion-non-declaree-transmise', async () => {
    const exclusions = entries(helpers).filter((entry) => entry.action === 'saveRoomExclusion');
    if (exclusions.length !== 1 || exclusions[0].verdict !== 'simulee') throw new Error('exclusion-non-declaree-transmise');
  });
}
