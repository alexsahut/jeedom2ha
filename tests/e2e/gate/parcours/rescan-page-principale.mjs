/** Story 20.4 : clic confirmé, rescan déclaré et retour simulé (à lancer après fusion). */

export const name = 'rescan-page-principale';
export const declaredEquipments = {};
export const declaredBascules = [];
export const declaredRescan = true;

export async function run(page, { helpers }) {
  const button = page.locator('#bt_rescanTopology');
  await button.waitFor({ state: 'visible' });
  await button.click();
  helpers.record('confirmation_ouverte', true);
  const confirm = page.locator('.bootbox .btn-primary').filter({ hasText: /^Rescanner$/ }).first();
  await confirm.click();
  await page.waitForFunction(() => document.querySelector('#div_alert')?.textContent?.includes('Synchronisation terminée.'));
  helpers.record('retour_rescan', 'succes-simule');
}
