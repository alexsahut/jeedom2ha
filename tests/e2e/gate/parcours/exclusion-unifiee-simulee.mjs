/** Front v2 (Lot 6) : « Choisir ce qui est publié… » — exclusion d'un plugin depuis la page du plugin, écritures SIMULÉES (à lancer
 * après fusion, contre la box, avec le GO d'Alexandre).
 *
 * Précondition sur la box : `excludedPlugins` vide et `confidencePolicy` = sure_probable au lancement. Sinon les valeurs envoyées ne
 * sont pas celles déclarées et la politique BLOQUE l'écriture (le parcours échoue, rien n'est transmis). Le plugin de test est
 * `virtual` (identifiant technique, présent sur la plupart des installations) ; il doit compter au moins un équipement.
 *
 * La politique du gate SIMULE `saveFilteringConfig` pour les seules valeurs déclarées (`declaredFilteringConfig` : application puis
 * annulation) et `scanTopology` (`declaredRescan`) : aucune écriture réelle n'est transmise à la box. Vrais clics Playwright.
 *
 * Assertions (étiquettes d'erreur distinctes) : (1) le bouton « Choisir ce qui est publié… » est visible et ouvre le panneau, avec la
 * règle de priorité et le bouton d'application inactif tant que rien ne change, sans aucune écriture (`panneau-absent`) ; (2) « Par
 * plugin », décocher le plugin : le pied annonce un nombre entier d'entités, repris sur le bouton rouge si des entités partent ;
 * enregistré par `record('entites_annoncees', N)` (`pied-sans-nombre`) ; (3) « Annuler » ferme sans écrire
 * (`ecriture-apres-annulation`) ; (4) appliquer émet exactement `saveFilteringConfig` (simulée) puis `scanTopology` (simulée), puis une
 * lecture `getEquipmentStates` (`sequence-exclusion-inattendue`) ; (5) le bandeau de résultat porte « Annuler »
 * (`bandeau-sans-annulation`) ; (6) « Annuler » du bandeau émet `saveFilteringConfig` (valeur d'origine, simulée) puis `scanTopology`
 * (simulée) (`annulation-inattendue`) ; (7) aucune écriture autre que les déclarées n'a été émise (`ecriture-non-declaree-transmise`).
 */

export const name = 'exclusion-unifiee-simulee';
export const declaredEquipments = {};
export const declaredBascules = [];
export const declaredRescan = true;
export const declaredFilteringConfig = { excludedPlugins: ['virtual', ''], confidencePolicy: 'sure_probable' };

const PLUGIN = 'virtual';
const PANEL = '.bootbox .j2ha-v2-excl';
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

async function openPanel(page) {
  const button = page.locator('#bt_j2haChoosePublished');
  await button.waitFor({ state: 'visible' });
  await button.click();
  await page.locator(PANEL).waitFor({ state: 'visible' });
}

async function uncheckPlugin(page) {
  await page.locator(`${PANEL} .j2ha-v2-excl-mode [data-mode="plugin"]`).click();
  const box = page.locator(`${PANEL} .j2ha-v2-excl-group[data-kind="plugin"][data-id="${PLUGIN}"] .j2ha-v2-excl-cb`);
  await box.waitFor({ state: 'visible' });
  await box.uncheck();
}

/** Attend l'écriture `scanTopology` puis une lecture des états qui la suit ; rend les entrées émises depuis `start`. */
async function settle(helpers, start) {
  const deadline = Date.now() + 8_000;
  while (Date.now() < deadline) {
    const since = entries(helpers).slice(start);
    const scanAt = since.findIndex((entry) => entry.action === 'scanTopology');
    if (scanAt >= 0 && since.some((entry, index) => index > scanAt && entry.action === 'getEquipmentStates')) return since;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  return entries(helpers).slice(start);
}

function checkSequence(since, label) {
  const order = since.filter((entry) => WRITE_ACTIONS.includes(entry.action)).map((entry) => `${entry.action}:${entry.verdict}`);
  if (order.join(',') !== 'saveFilteringConfig:simulee,scanTopology:simulee') throw new Error(label);
  const scanAt = since.findIndex((entry) => entry.action === 'scanTopology');
  const reads = since.filter((entry, index) => index > scanAt && entry.action === 'getEquipmentStates');
  if (reads.length !== 1) throw new Error(label);
}

export async function run(page, { helpers }) {
  await page.waitForFunction(() => (document.querySelector('#j2ha_houseNumber')?.textContent ?? '').trim() !== '');
  const origin = entries(helpers).length;

  // (1) Le panneau s'ouvre depuis la page ; rien n'est écrit à l'ouverture.
  await atStep(helpers, 1, 'panneau-absent', async () => {
    await openPanel(page);
    const rule = (await page.locator(`${PANEL} .j2ha-v2-excl-rule`).innerText()).replace(/\s+/g, ' ');
    if (!/ni lui-même, ni par sa pièce, ni par son plugin/.test(rule)) throw new Error('panneau-absent');
    if (!(await page.locator(`${PANEL} .j2ha-v2-excl-apply`).isDisabled())) throw new Error('panneau-absent');
    if (writesSince(helpers, origin).length > 0) throw new Error('panneau-absent');
  });

  // (2) Pied chiffré en direct, bouton chiffré.
  const announced = await atStep(helpers, 2, 'pied-sans-nombre', async () => {
    await uncheckPlugin(page);
    const foot = (await page.locator(`${PANEL} .j2ha-v2-excl-sum`).innerText()).replace(/\s+/g, ' ');
    const label = (await page.locator(`${PANEL} .j2ha-v2-excl-apply`).innerText()).replace(/\s+/g, ' ').trim();
    const removed = /\((\d+) entités?\)/.exec(foot);
    if (removed) {
      if (label !== `Appliquer — retirer ${removed[1]} ${Number(removed[1]) > 1 ? 'entités' : 'entité'}`) throw new Error('pied-sans-nombre');
      return Number(removed[1]);
    }
    if (/aucune entité publiée/.test(foot)) return 0;
    throw new Error('pied-sans-nombre');
  });
  helpers.record('entites_annoncees', announced);

  // (3) Annuler ferme sans écrire.
  await atStep(helpers, 3, 'ecriture-apres-annulation', async () => {
    await page.locator(`${PANEL} .j2ha-v2-excl-cancel`).click();
    await page.locator(PANEL).waitFor({ state: 'detached' });
    if (writesSince(helpers, origin).length > 0) throw new Error('ecriture-apres-annulation');
  });

  // (4) Appliquer : une écriture, une seule relecture, puis une lecture des états.
  const start = entries(helpers).length;
  await atStep(helpers, 4, 'sequence-exclusion-inattendue', async () => {
    await openPanel(page);
    await uncheckPlugin(page);
    await page.locator(`${PANEL} .j2ha-v2-excl-apply`).click();
    checkSequence(await settle(helpers, start), 'sequence-exclusion-inattendue');
  });

  // (5) Bandeau de résultat avec « Annuler ».
  await atStep(helpers, 5, 'bandeau-sans-annulation', async () => {
    await page.locator('#j2ha_v2_toast .j2ha-v2-excl-undo').waitFor({ state: 'visible', timeout: 8_000 });
  });

  // (6) Annuler : écriture inverse (valeur d'origine), puis une relecture.
  const undoStart = entries(helpers).length;
  await atStep(helpers, 6, 'annulation-inattendue', async () => {
    await page.locator('#j2ha_v2_toast .j2ha-v2-excl-undo').click();
    checkSequence(await settle(helpers, undoStart), 'annulation-inattendue');
  });

  // (7) Seules les écritures déclarées ont été émises (toute autre aurait été bloquée et consignée en échec).
  await atStep(helpers, 7, 'ecriture-non-declaree-transmise', async () => {
    const writes = entries(helpers).filter((entry) => WRITE_ACTIONS.includes(entry.action));
    if (writes.length !== 4 || writes.some((entry) => entry.verdict !== 'simulee')) throw new Error('ecriture-non-declaree-transmise');
  });
}
