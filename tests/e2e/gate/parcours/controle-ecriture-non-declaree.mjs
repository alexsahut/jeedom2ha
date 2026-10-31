/** Contrôle négatif : une écriture sans aperçu doit arrêter le gate. */

export const name = 'controle-ecriture-non-declaree';
export const declaredEquipments = {
  '380': { commands: ['2971', '2968', '2969', '2970'] },
};
export const declaredPublicationOverrides = {};
export const declaredBascules = [];

async function atStep(helpers, index, label, operation) {
  helpers.record(`etape_${index}`, label);
  try {
    return await operation();
  } catch (error) {
    const message = error instanceof Error ? error.message.split(/\r?\n/, 1)[0] : String(error);
    throw new Error(`etape ${label} : ${message}`);
  }
}

// Story 25.4 : ouverture par la vue de travail C (sélection dans l'arbre, vrais clics) ; mêmes étapes et mêmes exigences.
async function openTarget(page, helpers) {
  const room = page.locator('#j2ha_roomCards .j2ha-room-card[data-object_id="4"]');
  await atStep(helpers, 1, 'carte-piece-4', () => room.click());
  const view = page.locator('#j2ha_workView');
  await atStep(helpers, 2, 'modale', () => view.waitFor({ state: 'visible' }));
  const row = view.locator('.j2ha-wv-eq[data-eq-id="380"]');
  const panel = view.locator('.j2ha-eq-panel[data-eq-id="380"]');
  await atStep(helpers, 3, 'panneau-eq-380', () => row.waitFor({ state: 'visible' }));
  await atStep(helpers, 4, 'depliage', async () => {
    await row.locator('.j2ha-wv-row').click();
    await panel.locator('.j2ha-cmd-table').waitFor({ state: 'visible' });
  });
  await atStep(helpers, 5, 'ancre-bloquante', () => panel.locator('.j2ha-goto-blocking').waitFor({ state: 'visible' }));
  await atStep(helpers, 6, 'premiere-bloquante', async () => {
    await panel.locator('.j2ha-goto-blocking').click();
    await page.waitForFunction(() => document.querySelectorAll(
      'tr.mapping-override-cmd.j2ha-diag-target-highlight',
    ).length === 1);
  });
  const highlighted = panel.locator('tr.mapping-override-cmd.j2ha-diag-target-highlight');
  const cmdId = await highlighted.getAttribute('data-cmd-id');
  if (cmdId !== '2971') throw new Error('cmd-cible-inattendue');
  return cmdId;
}

export async function run(page, { helpers }) {
  const cmdId = await openTarget(page, helpers);
  helpers.record('cmd_cible_id', Number(cmdId));
  const failed = await atStep(helpers, 7, 'ecriture-sans-apercu', () => page.evaluate(async (id) => {
    try {
      await fetch('plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' },
        body: new URLSearchParams({
          action: 'saveMappingOverride', eqId: '380', cmdId: id, haEntityType: 'binary_sensor',
        }),
      });
      return false;
    } catch {
      return true;
    }
  }, cmdId));
  helpers.record('requete_page_echouee', failed);
  if (!failed) throw new Error('ecriture-non-declaree-non-bloquee');
}
