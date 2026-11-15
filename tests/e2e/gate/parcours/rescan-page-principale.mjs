/** Story 20.4 : clic confirmé, relecture de Jeedom déclarée et retour simulé (à lancer après fusion). */

export const name = 'rescan-page-principale';
export const declaredEquipments = {};
export const declaredBascules = [];
export const declaredRescan = true;

export async function run(page, { helpers }) {
  const button = page.locator('#bt_rescanTopology');
  await button.waitFor({ state: 'visible' });
  await button.click();
  helpers.record('confirmation_ouverte', true);
  const confirm = page.locator('.bootbox .btn-primary').filter({ hasText: /^Relire$/ }).first();
  await confirm.click();
  // Front v2 (Lot 1) : glossaire 3.2 — la page affiche « Relecture terminée. » (le démon et lib/interceptor.mjs envoient
  // toujours « Synchronisation terminée. »). Ajout seul : les deux contrôles d'origine restent en dessous (garde
  // « aucune ligne retirée » de test_story_25_3_gate) ; test_story_20_4_rescan_ui interdit l'ancien libellé dans la page.
  const zone = await page.waitForFunction(() => {
    if (document.querySelector('#jeeToastContainer')?.textContent?.includes('Relecture terminée.')) {
      return 'toast';
    }
    if (document.querySelector('#div_alert')?.textContent?.includes('Relecture terminée.')) {
      return 'div_alert';
    }
    if (document.querySelector('#jeeToastContainer')?.textContent?.includes('Synchronisation terminée.')) {
      return 'toast';
    }
    if (document.querySelector('#div_alert')?.textContent?.includes('Synchronisation terminée.')) {
      return 'div_alert';
    }
    return false;
  });
  helpers.record('retour_rescan_zone', await zone.jsonValue());
  helpers.record('retour_rescan', 'succes-simule');
}
