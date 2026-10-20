/** Contrôle négatif (Story 25.8) : une écriture `saveRoomExclusion` sur une pièce NON déclarée doit arrêter le gate.
 *
 * Ce parcours déclare la pièce 4 mais provoque une écriture sur la pièce 3 depuis la page : la politique la bloque (block-fail,
 * `exclusion-piece-non-declaree`), l'intercepteur la consigne en échec et le gate échoue, comme attendu. Même rôle que
 * `controle-ecriture-non-declaree` pour les réglages. Aucune écriture n'atteint la box.
 */

export const name = 'controle-exclusion-piece-non-declaree';
export const declaredEquipments = {};
export const declaredBascules = [];
export const declaredRescan = true;
export const declaredRoomExclusions = { '4': { excluded: '1' } };

export async function run(page, { helpers }) {
  await page.waitForFunction(() => (document.querySelector('#j2ha_houseNumber')?.textContent ?? '').trim() !== '');
  helpers.record('ecriture_non_declaree_provoquee', true);
  await page.evaluate(() => window.fetch(
    'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php',
    { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: 'action=saveRoomExclusion&objectId=3&excluded=1' },
  ).catch(() => null));
}
