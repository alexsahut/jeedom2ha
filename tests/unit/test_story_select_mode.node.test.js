// ARTEFACT — story/select-mode : « Corriger le type » propose « Mode (état) » sur une info et « Mode (commande) » sur une
// action quand le démon le dit (`override_types_allowed` contient `select`, `mode_role`), y compris sur une commande que
// rien ne couvre encore ; ailleurs, le rôle n'est pas montré. Doc mot pour mot. Identifiants fictifs (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const P = require('../../desktop/js/jeedom2ha_type_panel.js');

const uncovered = { publication_reason: 'command_not_covered', should_publish: false, reason_code: null };

function row(extra) {
  return Object.assign({ jeedom_cmd_id: 44, cmd_name: 'Programme', generic_type: null, covered: false,
    diagnostic: uncovered, override_applied: false }, extra);
}

describe('story/select-mode — rôles « Mode » dans « Corriger le type »', () => {
  it('une commande non couverte devient réglable quand le démon propose le rôle', () => {
    assert.equal(M.getOverrideSelectorState(row({ override_types_allowed: ['select'], mode_role: 'state' }), []).active, true);
    assert.equal(M.getOverrideSelectorState(row({}), []).active, false, 'sans proposition : comportement d’avant');
    assert.equal(M.getOverrideSelectorState(row({ override_types_allowed: ['sensor'] }), []).active, false);
  });

  it('« Mode (état) » pour une info, « Mode (commande) » pour une action', () => {
    const state = P.buildChoices(row({ override_types_allowed: ['select'], mode_role: 'state' }));
    const offered = state.choices.filter((c) => !c.disabled && c.value);
    assert.deepEqual(offered.map((c) => [c.value, c.label]), [['select', 'Mode (état)']]);
    const command = P.buildChoices(row({ jeedom_cmd_id: 45, override_types_allowed: ['select'], mode_role: 'command' }));
    assert.deepEqual(command.choices.filter((c) => !c.disabled && c.value).map((c) => c.label), ['Mode (commande)']);
  });

  it('le rôle n’est jamais montré, même grisé, là où le démon ne le propose pas', () => {
    const choices = P.buildChoices(row({ covered: true, override_types_allowed: ['switch', 'sensor'] })).choices;
    assert.ok(!choices.some((c) => c.value === 'select'));
  });

  it('réglage posé : « Personnalisé : Mode (état) »', () => {
    assert.equal(P.cellLabel({ override_applied: true, effective_ha: 'select', mode_role: 'state' }), 'Personnalisé : Mode (état)');
    assert.equal(P.cellLabel({ override_applied: true, effective_ha: 'light' }), 'Personnalisé : Lumière (light)');
  });

  it('la documentation et le changelog reprennent les libellés de l’écran', () => {
    const root = path.resolve(__dirname, '../..');
    for (const file of ['docs/fr_FR/index.md', 'docs/fr_FR/changelog_beta.md']) {
      const text = fs.readFileSync(path.join(root, file), 'utf8');
      assert.ok(text.includes('« Mode (état) »') && text.includes('« Mode (commande) »'), file);
      assert.match(text, /types génériques de Jeedom/, file);
    }
  });
});
