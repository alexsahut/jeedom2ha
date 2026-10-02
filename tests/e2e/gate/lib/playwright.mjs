// tests/e2e/gate/lib/playwright.mjs
/** Résolution de Playwright hors dépôt, commune aux outils du gate. */

import { createRequire } from 'node:module';
import path from 'node:path';

const GATE_TOOLS_DIR = process.env.JEEDOM2HA_GATE_TOOLS || '/home/asahut/.openclaw/tools/jeedom2ha-gate';

export function loadPlaywright() {
  const toolsPackageJson = path.join(GATE_TOOLS_DIR, 'package.json');
  const requireFromTools = createRequire(toolsPackageJson);
  try {
    return requireFromTools('playwright');
  } catch (err) {
    throw new Error(
      `Playwright introuvable depuis ${GATE_TOOLS_DIR} (résolu via ${toolsPackageJson}) : ${err.message}`
    );
  }
}
