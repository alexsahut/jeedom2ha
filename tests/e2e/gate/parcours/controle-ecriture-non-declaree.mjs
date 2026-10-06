/** Contrôle négatif : une écriture sans aperçu doit arrêter le gate. */

export const name = 'controle-ecriture-non-declaree';
export const declaredEquipments = {
  '579': { commands: ['5689', '5368', '5369', '5494', '5695', '5493'] },
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

async function openTarget(page, helpers) {
  const room = page.locator('#j2ha_roomCards .j2ha-room-card').filter({
    has: page.locator('.name', { hasText: /^Garage$/ }),
  });
  await atStep(helpers, 1, 'carte-garage', () => room.click());
  const modal = page.locator('.modal-j2ha-room');
  await atStep(helpers, 2, 'modale', () => modal.waitFor({ state: 'visible' }));
  const panel = modal.locator('.j2ha-eq-panel').filter({
    has: page.locator('.j2ha-eq-name', { hasText: /^\s*Enphase\s*$/ }),
  });
  await atStep(helpers, 3, 'panneau-enphase', () => panel.waitFor({ state: 'visible' }));
  await atStep(helpers, 4, 'depliage', async () => {
    await panel.locator('.j2ha-eq-toggle').click();
    await panel.locator('.panel-collapse').waitFor({ state: 'visible' });
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
  if (!['5368', '5369'].includes(cmdId ?? '')) throw new Error('cmd-cible-inattendue');
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
          action: 'saveMappingOverride', eqId: '579', cmdId: id, haEntityType: 'binary_sensor',
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
