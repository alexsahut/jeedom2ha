// ARTEFACT — Story 5.1 : tests JS ciblés — consommation actions_ha en lecture seule.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const Jeedom2haScopeSummary = require('../../desktop/js/jeedom2ha_scope_summary.js');

// ---------------------------------------------------------------------------
// AC 6 — Frontend affiche actions_ha strictement depuis le backend
// ---------------------------------------------------------------------------

describe('5.1 / AC6 — readActionsHa : lecture stricte du signal backend', () => {
  it('retourne null si actions_ha absent', () => {
    assert.strictEqual(Jeedom2haScopeSummary.readActionsHa(null), null);
    assert.strictEqual(Jeedom2haScopeSummary.readActionsHa(undefined), null);
    assert.strictEqual(Jeedom2haScopeSummary.readActionsHa(42), null);
  });

  it('retourne null si shape invalide (publier manquant)', () => {
    assert.strictEqual(Jeedom2haScopeSummary.readActionsHa({ supprimer: { label: 'x', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'forte' } }), null);
  });

  it('lit correctement un signal complet', () => {
    const raw = {
      publier: { label: 'Créer dans Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'aucune' },
      supprimer: { label: 'Supprimer de Home Assistant', disponible: false, raison_indisponibilite: 'Aucune entité', niveau_confirmation: 'forte' },
    };
    const result = Jeedom2haScopeSummary.readActionsHa(raw);
    assert.notStrictEqual(result, null);
    assert.strictEqual(result.publier.label, 'Créer dans Home Assistant');
    assert.strictEqual(result.publier.disponible, true);
    assert.strictEqual(result.publier.raison_indisponibilite, null);
    assert.strictEqual(result.supprimer.disponible, false);
    assert.strictEqual(result.supprimer.raison_indisponibilite, 'Aucune entité');
  });

  it('disponible non boolean → false', () => {
    const raw = {
      publier: { label: 'Créer', disponible: 'oui', raison_indisponibilite: null, niveau_confirmation: 'aucune' },
      supprimer: { label: 'Supprimer', disponible: 1, raison_indisponibilite: null, niveau_confirmation: 'forte' },
    };
    const result = Jeedom2haScopeSummary.readActionsHa(raw);
    assert.strictEqual(result.publier.disponible, false);
    assert.strictEqual(result.supprimer.disponible, false);
  });
});

// ---------------------------------------------------------------------------
// AC 6 — renderActionButtons : aucun recalcul
// ---------------------------------------------------------------------------

describe('5.1 / AC6 — renderActionButtons : rendu strictement depuis actions_ha', () => {
  it('retourne vide si actions_ha null', () => {
    const html = Jeedom2haScopeSummary.renderActionButtons(null, 42);
    assert.strictEqual(html, '');
  });

  it('rend les boutons avec les labels du backend', () => {
    const actions = {
      publier: { label: 'Créer dans Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'aucune' },
      supprimer: { label: 'Supprimer de Home Assistant', disponible: false, raison_indisponibilite: 'Aucune entité publiée', niveau_confirmation: 'forte' },
    };
    const html = Jeedom2haScopeSummary.renderActionButtons(actions, 42);
    assert.ok(html.includes('Créer dans Home Assistant'));
    assert.ok(html.includes('Supprimer de Home Assistant'));
    // Publier actif (pas de disabled)
    assert.ok(!html.includes('data-ha-action="publier" disabled') || !html.includes('data-ha-action=\"publier\" disabled'));
    // Supprimer grisé (disabled)
    assert.ok(html.includes('disabled'));
    assert.ok(html.includes('Aucune entité publiée'));
  });

  it('rend les boutons Republier quand publié', () => {
    const actions = {
      publier: { label: 'Republier dans Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'aucune' },
      supprimer: { label: 'Supprimer de Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'forte' },
    };
    const html = Jeedom2haScopeSummary.renderActionButtons(actions, 42);
    assert.ok(html.includes('Republier dans Home Assistant'));
    // Les deux cliquables (pas de disabled sur publier ni supprimer label)
    const publierMatch = html.match(/data-ha-action="publier"[^>]*>/);
    assert.ok(publierMatch);
    assert.ok(!publierMatch[0].includes('disabled'));
  });
});

// ---------------------------------------------------------------------------
// AC 6 — createModel intègre actions_ha dans le modèle équipement
// ---------------------------------------------------------------------------

describe('5.1 / AC6 — createModel transporte actions_ha', () => {
  function makeResponse(actionsHa) {
    return {
      status: 'ok',
      published_scope: {
        global: { counts: { total: 1, include: 1, exclude: 0 } },
        pieces: [{ object_id: 1, object_name: 'Salon', counts: { total: 1, include: 1, exclude: 0 } }],
        equipements: [{ eq_id: 42, object_id: 1, name: 'Lumière', effective_state: 'published' }],
      },
      diagnostic_equipments: {
        42: {
          perimetre: 'inclus',
          statut: 'publie',
          ecart: false,
          cause_code: '',
          cause_label: '',
          cause_action: '',
          status_code: 'published',
          reason_code: 'sure',
          detail: '',
          remediation: '',
          v1_limitation: false,
          confidence: 'sure',
          matched_commands: [],
          unmatched_commands: [],
          actions_ha: actionsHa,
        },
      },
      diagnostic_rooms: [],
      diagnostic_summary: { compteurs: { total: 1, inclus: 1, exclus: 0, ecarts: 0 } },
      in_scope_equipments: [{ eq_id: 42 }],
      home_signals: { global: { publies: 1, statut: 'Publiee' }, pieces: [] },
    };
  }

  it('actions_ha présent → transporté dans le modèle', () => {
    const actionsHa = {
      publier: { label: 'Republier dans Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'aucune' },
      supprimer: { label: 'Supprimer de Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'forte' },
    };
    const model = Jeedom2haScopeSummary.createModel(makeResponse(actionsHa));
    assert.strictEqual(model.has_contract, true);
    const eq = model.pieces[0].equipements[0];
    assert.notStrictEqual(eq.actions_ha, null);
    assert.strictEqual(eq.actions_ha.publier.label, 'Republier dans Home Assistant');
  });

  it('actions_ha absent → null dans le modèle (neutre)', () => {
    const model = Jeedom2haScopeSummary.createModel(makeResponse(null));
    assert.strictEqual(model.has_contract, true);
    const eq = model.pieces[0].equipements[0];
    assert.strictEqual(eq.actions_ha, null);
  });

  it('actions_ha absent → pas de pseudo-contrat local', () => {
    const model = Jeedom2haScopeSummary.createModel(makeResponse(undefined));
    const eq = model.pieces[0].equipements[0];
    // Le frontend ne reconstitue pas de signal à partir d'autres champs
    assert.strictEqual(eq.actions_ha, null);
  });
});

// ---------------------------------------------------------------------------
// Invariant I17 — Frontend en lecture seule
// ---------------------------------------------------------------------------

describe('5.1 — Invariant I17 : aucun recalcul frontend de est_publie_ha ou du label', () => {
  it('readActionsHa ne modifie pas les valeurs du backend', () => {
    const raw = {
      publier: { label: 'Créer dans Home Assistant', disponible: false, raison_indisponibilite: 'Pont indisponible', niveau_confirmation: 'aucune' },
      supprimer: { label: 'Supprimer de Home Assistant', disponible: false, raison_indisponibilite: 'Pont indisponible', niveau_confirmation: 'forte' },
    };
    const result = Jeedom2haScopeSummary.readActionsHa(raw);
    // La fonction ne transforme pas les valeurs
    assert.strictEqual(result.publier.label, raw.publier.label);
    assert.strictEqual(result.publier.disponible, raw.publier.disponible);
    assert.strictEqual(result.supprimer.raison_indisponibilite, raw.supprimer.raison_indisponibilite);
  });
});
