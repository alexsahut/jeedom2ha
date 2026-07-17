// ARTEFACT — Story 16.5 : tests JS purs de l'onglet override (triptyque, dry-run, réassurance).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');

// Vue diagnostic verte (projetable + publiable) — contrat _preview_mapping_view.
function readyView(type) {
  return {
    ha_entity_type: type || 'light',
    reason_code: 'ok',
    projection_validity: { is_valid: true, reason_code: null, missing_capabilities: [], missing_fields: [] },
    should_publish: true,
    publication_reason: 'sure',
  };
}

// Vue diagnostic bloquante (capacité manquante).
function blockingView(type) {
  return {
    ha_entity_type: type || 'cover',
    reason_code: 'projection_invalid',
    projection_validity: {
      is_valid: false,
      reason_code: 'missing_capability',
      missing_capabilities: ['position'],
      missing_fields: [],
    },
    should_publish: false,
    publication_reason: 'projection_invalid',
  };
}

// ---------------------------------------------------------------------------
// Options de type HA (AC7 — colonne override)
// ---------------------------------------------------------------------------

describe('16.5 — options de type HA', () => {
  it('expose exactement les 8 types supportés par le moteur, triés', () => {
    assert.deepStrictEqual(M.getHaEntityTypeOptions(), [
      'alarm_control_panel', 'binary_sensor', 'button', 'climate',
      'cover', 'light', 'sensor', 'switch',
    ]);
  });

  it('getHaEntityTypeOptions retourne une copie (pas la référence interne)', () => {
    const a = M.getHaEntityTypeOptions();
    a.push('poubelle');
    assert.strictEqual(M.getHaEntityTypeOptions().length, 8);
  });
});

// ---------------------------------------------------------------------------
// Normalisation de l'arbre (AC3 ordre natif, AC4 triptyque, D11 override_source)
// ---------------------------------------------------------------------------

describe('16.5 / AC3-AC4 — normalizeTree', () => {
  it('préserve l’ordre natif des commandes sans tri', () => {
    const tree = M.normalizeTree({
      jeedom_eq_id: 200, eq_name: 'Lampe', mapped: true,
      commands: [
        { jeedom_cmd_id: 3, cmd_name: 'C', generic_type: 'LIGHT_STATE', coverable: true, attendu_ha: 'light', effective_ha: 'light', override_applied: false },
        { jeedom_cmd_id: 1, cmd_name: 'A', generic_type: 'LIGHT_SLIDER', coverable: true, attendu_ha: 'light', effective_ha: 'light', override_applied: false },
      ],
    });
    assert.deepStrictEqual(tree.commands.map((c) => c.jeedom_cmd_id), [3, 1]);
  });

  it('override_source présent seulement quand override_applied=true (D11)', () => {
    const applied = M.normalizeCommandRow({ jeedom_cmd_id: 1, override_applied: true, override_source: 'user' });
    assert.strictEqual(applied.override_source, 'user');
    const auto = M.normalizeCommandRow({ jeedom_cmd_id: 2, override_applied: false, override_source: 'user' });
    assert.strictEqual(auto.override_source, null);
  });

  it('generic_type natif lu tel quel, jamais inventé (D10 lecture seule)', () => {
    const row = M.normalizeCommandRow({ jeedom_cmd_id: 1, generic_type: 'LIGHT_STATE' });
    assert.strictEqual(row.generic_type, 'LIGHT_STATE');
    const noType = M.normalizeCommandRow({ jeedom_cmd_id: 2, generic_type: '' });
    assert.strictEqual(noType.generic_type, null);
  });

  it('payload vide → structure sûre', () => {
    const tree = M.normalizeTree(null);
    assert.strictEqual(tree.mapped, false);
    assert.deepStrictEqual(tree.commands, []);
  });
});

// ---------------------------------------------------------------------------
// AC5 — état vide explicite
// ---------------------------------------------------------------------------

describe('16.5 / AC5 — état vide', () => {
  it('affiche l’attendu par défaut, jamais un champ vide silencieux', () => {
    const label = M.buildEmptyStateLabel({ jeedom_cmd_id: 1, attendu_ha: 'sensor', override_applied: false });
    assert.match(label, /Aucun override configuré/);
    assert.match(label, /sensor/);
  });

  it('sans attendu → message explicite « aucun type par défaut »', () => {
    const label = M.buildEmptyStateLabel({ jeedom_cmd_id: 1, override_applied: false });
    assert.match(label, /aucun type HA par défaut/);
  });
});

// ---------------------------------------------------------------------------
// AC8/AC9/AC12 — diagnostic dry-run : état, auto-validation, message actionnable
// ---------------------------------------------------------------------------

describe('16.5 / AC8-AC9 — état diagnostic', () => {
  it('vue verte → ready + auto-validation', () => {
    assert.strictEqual(M.diagnosticState(readyView()), 'ready');
    assert.strictEqual(M.isReadyDiagnostic(readyView()), true);
    assert.strictEqual(M.shouldAutoValidate(readyView()), true);
  });

  it('vue bloquante → blocking + PAS d’auto-validation', () => {
    assert.strictEqual(M.diagnosticState(blockingView()), 'blocking');
    assert.strictEqual(M.isBlockingDiagnostic(blockingView()), true);
    assert.strictEqual(M.shouldAutoValidate(blockingView()), false);
  });

  it('should_publish=false malgré projection valide → blocking (pas d’auto-save)', () => {
    const v = readyView();
    v.should_publish = false;
    v.publication_reason = 'excluded_by_policy';
    assert.strictEqual(M.isBlockingDiagnostic(v), true);
    assert.strictEqual(M.shouldAutoValidate(v), false);
  });

  it('vue absente → unknown (ni ready ni blocking)', () => {
    assert.strictEqual(M.diagnosticState(null), 'unknown');
    assert.strictEqual(M.isReadyDiagnostic(null), false);
    assert.strictEqual(M.isBlockingDiagnostic(null), false);
  });

  it('readPreviewOverridden extrait la vue overridée de la réponse preview', () => {
    const resp = { status: 'ok', payload: { jeedom_eq_id: 200, mapped: true, auto: readyView(), overridden: blockingView() } };
    const v = M.readPreviewOverridden(resp);
    assert.strictEqual(v.is_valid, false);
    assert.strictEqual(M.diagnosticState(resp.payload.overridden), 'blocking');
  });
});

describe('16.5 / AC12 — message actionnable, jamais une erreur réseau', () => {
  it('vert → détail de ce qui a été validé', () => {
    const msg = M.buildDiagnosticMessage(readyView('light'));
    assert.match(msg, /Prêt/);
    assert.match(msg, /light/);
  });

  it('capacité manquante → message factuel actionnable', () => {
    const msg = M.buildDiagnosticMessage(blockingView());
    assert.match(msg, /Capacité\(s\) manquante\(s\)/);
    assert.match(msg, /position/);
  });

  it('champ manquant → message factuel', () => {
    const v = blockingView();
    v.projection_validity.missing_capabilities = [];
    v.projection_validity.missing_fields = ['unit_of_measurement'];
    assert.match(M.buildDiagnosticMessage(v), /Champ\(s\) requis manquant\(s\)/);
  });

  it('refus publication sans capacité manquante → code de raison affiché', () => {
    const v = readyView();
    v.should_publish = false;
    v.publication_reason = 'excluded_by_policy';
    const reasons = M.collectRefusalReasons(v);
    assert.deepStrictEqual(reasons, ['excluded_by_policy']);
    assert.match(M.buildDiagnosticMessage(v), /excluded_by_policy/);
  });

  it('collectRefusalReasons vide quand la vue est verte', () => {
    assert.deepStrictEqual(M.collectRefusalReasons(readyView()), []);
  });
});

// ---------------------------------------------------------------------------
// AC14 — réassurance « aucun impact Homebridge » une seule fois par équipement
// ---------------------------------------------------------------------------

describe('16.5 / AC14 — bandeau réassurance', () => {
  it('affiché au premier blocage, puis plus jamais pour l’équipement', () => {
    let state = M.initReassuranceState();
    assert.strictEqual(M.shouldShowReassurance(state, true), true);
    state = M.markReassuranceShown(state);
    assert.strictEqual(M.shouldShowReassurance(state, true), false);
  });

  it('jamais affiché quand aucun blocage', () => {
    const state = M.initReassuranceState();
    assert.strictEqual(M.shouldShowReassurance(state, false), false);
  });
});

// ---------------------------------------------------------------------------
// AC3.4 — auto-ouverture des commandes bloquantes plafonnée
// ---------------------------------------------------------------------------

describe('16.5 / AC3.4 — commandes bloquantes plafonnées', () => {
  function treeWith(nBlocking) {
    const commands = [];
    for (let i = 0; i < nBlocking; i++) {
      commands.push({ jeedom_cmd_id: 100 + i, diagnostic: blockingView() });
    }
    commands.push({ jeedom_cmd_id: 999, diagnostic: readyView() });
    return { jeedom_eq_id: 1, mapped: true, commands };
  }

  it('ne retient que les commandes bloquantes', () => {
    const ids = M.collectBlockingCommandIds(treeWith(2), 4);
    assert.deepStrictEqual(ids, [100, 101]);
  });

  it('plafonne à la limite fournie', () => {
    const ids = M.collectBlockingCommandIds(treeWith(10), 3);
    assert.strictEqual(ids.length, 3);
  });

  it('défaut = 4 si aucune limite valide', () => {
    const ids = M.collectBlockingCommandIds(treeWith(10));
    assert.strictEqual(ids.length, 4);
  });
});
