// ARTEFACT — Story 5.7 : harmonisation badge « Suppr. » pièce et équipement.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const Jeedom2haScopeSummary = require('../../desktop/js/jeedom2ha_scope_summary.js');

// ---------------------------------------------------------------------------
// AC 1 + AC 2 — shortLabel : source de vérité unique "Supprimer" → "Suppr."
// ---------------------------------------------------------------------------

describe('5.7 / AC1+AC2 — shortLabel : transformation "Supprimer" → "Suppr."', () => {
  it('shortLabel("Supprimer de Home Assistant") retourne "Suppr."', () => {
    // Via renderActionButtons — shortLabel n'est pas exporté directement
    const actions = {
      publier: { label: 'Créer dans Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'aucune' },
      supprimer: { label: 'Supprimer de Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'forte' },
    };
    const html = Jeedom2haScopeSummary.renderActionButtons(actions, 1);
    assert.ok(html.includes('>Suppr.<'), 'shortLabel("Supprimer de Home Assistant") doit produire "Suppr."');
    assert.ok(!html.includes('>Supprimer<'), '"Supprimer" long ne doit plus apparaître');
  });

  it('non-régression : "Créer dans Home Assistant" → "Créer"', () => {
    const actions = {
      publier: { label: 'Créer dans Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'aucune' },
      supprimer: { label: 'Supprimer de Home Assistant', disponible: false, raison_indisponibilite: null, niveau_confirmation: 'forte' },
    };
    const html = Jeedom2haScopeSummary.renderActionButtons(actions, 2);
    assert.ok(html.includes('>Créer<'), 'shortLabel("Créer dans Home Assistant") doit produire "Créer"');
  });

  it('non-régression : "Republier dans Home Assistant" → "Republier"', () => {
    const actions = {
      publier: { label: 'Republier dans Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'aucune' },
      supprimer: { label: 'Supprimer de Home Assistant', disponible: false, raison_indisponibilite: null, niveau_confirmation: 'forte' },
    };
    const html = Jeedom2haScopeSummary.renderActionButtons(actions, 3);
    assert.ok(html.includes('>Republier<'), 'shortLabel("Republier dans Home Assistant") doit produire "Republier"');
  });
});

// ---------------------------------------------------------------------------
// AC 1 + AC 3 — renderActionButtons : badge Supprimer équipement
// ---------------------------------------------------------------------------

describe('5.7 / AC1+AC3 — renderActionButtons : badge Supprimer équipement nominal', () => {
  it('libellé "Suppr.", tooltip, classe btn-danger présents (état nominal)', () => {
    const actions = {
      publier: { label: 'Créer dans Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'aucune' },
      supprimer: { label: 'Supprimer de Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'forte' },
    };
    const html = Jeedom2haScopeSummary.renderActionButtons(actions, 10);
    assert.ok(html.includes('>Suppr.<'), 'Libellé court "Suppr." attendu');
    assert.ok(html.includes('title="Supprimer de Home Assistant"'), 'Tooltip attendu sur badge Supprimer');
    assert.ok(html.includes('btn-danger'), 'Classe btn-danger attendue');
    assert.ok(html.includes('j2ha-action-ha-btn'), 'Classe de délégation équipement conservée');
  });
});

// ---------------------------------------------------------------------------
// AC 6 — renderActionButtons : badge Supprimer masqué quand disponible=false
// ---------------------------------------------------------------------------

describe('5.7 / AC6 — renderActionButtons : Supprimer masqué quand disponible=false (non-régression Story 5.3)', () => {
  it('data-ha-action="supprimer" absent quand supprimer.disponible = false', () => {
    const actions = {
      publier: { label: 'Créer dans Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'aucune' },
      supprimer: { label: 'Supprimer de Home Assistant', disponible: false, raison_indisponibilite: null, niveau_confirmation: 'forte' },
    };
    const html = Jeedom2haScopeSummary.renderActionButtons(actions, 11);
    assert.ok(!html.includes('data-ha-action="supprimer"'), 'Badge Supprimer ne doit pas être rendu quand disponible=false');
  });
});

// ---------------------------------------------------------------------------
// AC 2 + AC 4 — renderPieceActionButtons : badge Supprimer pièce
// ---------------------------------------------------------------------------

describe('5.7 / AC2+AC4 — renderPieceActionButtons : badge Supprimer pièce nominal', () => {
  it('libellé "Suppr.", tooltip, classe btn-danger présents (counts.publies > 0)', () => {
    const piece = {
      object_id: 42,
      object_name: 'Salon',
      counts: { total: 5, exclus: 0, inclus: 4, publies: 3, ecarts: 0 },
    };
    const html = Jeedom2haScopeSummary.renderPieceActionButtons(piece);
    assert.ok(html.includes('>Suppr.<'), 'Libellé court "Suppr." attendu sur badge pièce');
    assert.ok(html.includes('title="Supprimer de Home Assistant"'), 'Tooltip attendu sur badge pièce');
    assert.ok(html.includes('btn-danger'), 'Classe btn-danger attendue sur badge pièce');
    assert.ok(html.includes('j2ha-piece-action-btn'), 'Classe de délégation pièce conservée');
    assert.ok(!html.includes('j2ha-action-ha-btn'), 'Classe de délégation équipement ne doit pas être présente sur badge pièce');
  });

  it('badge Supprimer absent quand counts.publies = 0', () => {
    const piece = {
      object_id: 43,
      object_name: 'Cuisine',
      counts: { total: 3, exclus: 0, inclus: 3, publies: 0, ecarts: 0 },
    };
    const html = Jeedom2haScopeSummary.renderPieceActionButtons(piece);
    assert.ok(!html.includes('data-ha-action="supprimer"'), 'Badge Supprimer ne doit pas être rendu quand publies=0');
  });
});

// ---------------------------------------------------------------------------
// AC 5 — Homogénéité Bootstrap pièce ↔ équipement
// ---------------------------------------------------------------------------

describe('5.7 / AC5 — Homogénéité visuelle Bootstrap pièce et équipement', () => {
  it('les deux badges portent exactement btn btn-xs btn-danger', () => {
    const actions = {
      publier: { label: 'Créer dans Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'aucune' },
      supprimer: { label: 'Supprimer de Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'forte' },
    };
    const htmlEq = Jeedom2haScopeSummary.renderActionButtons(actions, 20);
    const piece = {
      object_id: 50,
      object_name: 'Bureau',
      counts: { total: 2, exclus: 0, inclus: 2, publies: 1, ecarts: 0 },
    };
    const htmlPiece = Jeedom2haScopeSummary.renderPieceActionButtons(piece);

    // Extraire le bouton supprimer de chaque HTML
    const btnEqMatch = htmlEq.match(/<button[^>]*data-ha-action="supprimer"[^>]*>/);
    const btnPieceMatch = htmlPiece.match(/<button[^>]*data-ha-action="supprimer"[^>]*>/);

    assert.ok(btnEqMatch, 'Bouton Supprimer équipement doit être présent');
    assert.ok(btnPieceMatch, 'Bouton Supprimer pièce doit être présent');

    const btnEq = btnEqMatch[0];
    const btnPiece = btnPieceMatch[0];

    assert.ok(btnEq.includes('btn-xs'), 'btn-xs attendu sur badge équipement');
    assert.ok(btnEq.includes('btn-danger'), 'btn-danger attendu sur badge équipement');
    assert.ok(btnPiece.includes('btn-xs'), 'btn-xs attendu sur badge pièce');
    assert.ok(btnPiece.includes('btn-danger'), 'btn-danger attendu sur badge pièce');

    // Vérifier absence de classes de taille ou couleur différentes
    assert.ok(!btnEq.includes('btn-sm'), 'btn-sm ne doit pas être présent sur badge équipement');
    assert.ok(!btnEq.includes('btn-lg'), 'btn-lg ne doit pas être présent sur badge équipement');
    assert.ok(!btnEq.includes('btn-warning'), 'btn-warning ne doit pas être présent sur badge équipement');
    assert.ok(!btnPiece.includes('btn-sm'), 'btn-sm ne doit pas être présent sur badge pièce');
    assert.ok(!btnPiece.includes('btn-lg'), 'btn-lg ne doit pas être présent sur badge pièce');
    assert.ok(!btnPiece.includes('btn-warning'), 'btn-warning ne doit pas être présent sur badge pièce');
  });
});
