/**
 * Story 4.2 — Vocabulaire d'exclusion par source : disparition du concept exception
 *
 * Tests dédiés :
 *  - buildPerimetreLabel : table de correspondance perimetre → libellé UI
 *  - invariant no-exception : aucun terme interdit dans le HTML rendu
 *  - compteurs canoniques : Écarts depuis contrat diagnostics 4.1, pas de Exceptions
 *  - graceful degradation : daemon down → Écarts = —, pas de terme interdit
 *  - badge style uniforme : gris neutre pour toutes les sources d'exclusion
 *
 * ACs couverts : AC 1, AC 2, AC 3, AC 4, AC 5, AC 6, AC 7, AC 8
 */

const test = require("node:test");
const assert = require("node:assert/strict");

const scopeSummary = require("../../desktop/js/jeedom2ha_scope_summary.js");

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeMinimalResponse(perimetre) {
  return {
    status: "ok",
    published_scope: {
      global: { counts: { total: 1, include: 1, exclude: 0 } },
      pieces: [{ object_id: 1, object_name: "Salon", counts: { total: 1, include: 1, exclude: 0 } }],
      equipements: [{ eq_id: 100, object_id: 1, effective_state: "include" }],
    },
    diagnostic_equipments: {
      100: { perimetre: perimetre },
    },
    diagnostic_summary: { compteurs: { total: 1, inclus: 1, exclus: 0, ecarts: 0 } },
    diagnostic_rooms: [
      {
        object_id: 1,
        compteurs: { total: 1, inclus: 1, exclus: 0, ecarts: 0 },
        summary: { primary_aggregated_status: "published", counts_by_status: {} },
      },
    ],
  };
}

function renderWithPerimetre(perimetre) {
  return scopeSummary.render(scopeSummary.createModel(makeMinimalResponse(perimetre)));
}

// ---------------------------------------------------------------------------
// AC 1, 2, 3, 4 — 5.1 : test unitaire buildPerimetreLabel (via render)
// ---------------------------------------------------------------------------

test("4.2 / AC1 — buildPerimetreLabel : exclu_par_piece → 'Exclu par la pièce'", () => {
  assert.equal(scopeSummary.buildPerimetreLabel("exclu_par_piece"), "Exclu par la pi\u00e8ce");
  const html = renderWithPerimetre("exclu_par_piece");
  assert.match(html, /Exclu par la pi\u00e8ce/);
});

test("4.2 / AC3 — buildPerimetreLabel : exclu_par_plugin → 'Exclu par le plugin'", () => {
  assert.equal(scopeSummary.buildPerimetreLabel("exclu_par_plugin"), "Exclu par le plugin");
  const html = renderWithPerimetre("exclu_par_plugin");
  assert.match(html, /Exclu par le plugin/);
});

test("4.2 / AC2 — buildPerimetreLabel : exclu_sur_equipement → 'Exclu sur cet équipement'", () => {
  assert.equal(scopeSummary.buildPerimetreLabel("exclu_sur_equipement"), "Exclu sur cet \u00e9quipement");
  const html = renderWithPerimetre("exclu_sur_equipement");
  assert.match(html, /Exclu sur cet \u00e9quipement/);
});

test("4.2 / AC4 — buildPerimetreLabel : inclus → '' (pas de badge)", () => {
  assert.equal(scopeSummary.buildPerimetreLabel("inclus"), "");
  const html = renderWithPerimetre("inclus");
  assert.doesNotMatch(html, /Exclu par/);
  assert.doesNotMatch(html, /Exclu sur/);
});

test("4.2 / AC4 — buildPerimetreLabel : '' → '' (fallback sécuritaire)", () => {
  assert.equal(scopeSummary.buildPerimetreLabel(""), "");
  assert.equal(scopeSummary.buildPerimetreLabel("unknown_value"), "");
});

// ---------------------------------------------------------------------------
// AC 5 — 5.2 : invariant no-exception (famille exception/héritage absente du HTML)
// ---------------------------------------------------------------------------

test("4.2 / AC5 — invariant no-exception : aucun terme interdit dans le HTML rendu", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 4, include: 2, exclude: 2 } },
      pieces: [{ object_id: 1, object_name: "Salon", counts: { total: 4, include: 2, exclude: 2 } }],
      equipements: [
        { eq_id: 10, object_id: 1, effective_state: "exclude" },
        { eq_id: 11, object_id: 1, effective_state: "exclude" },
        { eq_id: 12, object_id: 1, effective_state: "include" },
        { eq_id: 13, object_id: 1, effective_state: "include" },
      ],
    },
    diagnostic_equipments: {
      10: { perimetre: "exclu_par_piece" },
      11: { perimetre: "exclu_sur_equipement" },
      12: { perimetre: "inclus" },
      13: { perimetre: "inclus" },
    },
    diagnostic_summary: { compteurs: { total: 4, inclus: 2, exclus: 2, ecarts: 1 } },
    diagnostic_rooms: [
      {
        object_id: 1,
        compteurs: { total: 4, inclus: 2, exclus: 2, ecarts: 1 },
        summary: { primary_aggregated_status: "published", counts_by_status: {} },
      },
    ],
  };

  const html = scopeSummary.render(scopeSummary.createModel(response));

  // Termes interdits — AC5
  assert.doesNotMatch(html, /H\u00e9rite de la pi\u00e8ce/);
  assert.doesNotMatch(html, /Exception locale/);
  assert.doesNotMatch(html, /Exceptions/);
  assert.doesNotMatch(html, /is_exception/);
  assert.doesNotMatch(html, /decision_source/);

  // Termes attendus présents
  assert.match(html, /Exclu par la pi\u00e8ce/);
  assert.match(html, /Exclu sur cet \u00e9quipement/);
});

// ---------------------------------------------------------------------------
// AC 6 — 5.3 : compteurs canoniques (Écarts depuis diagnostics, pas Exceptions)
// ---------------------------------------------------------------------------

test("4.2 / AC6 — compteurs canoniques : Écarts présent, Exceptions absent", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 5, include: 3, exclude: 2 } },
      pieces: [{ object_id: 1, object_name: "Salon", counts: { total: 5, include: 3, exclude: 2 } }],
      equipements: [{ eq_id: 1, object_id: 1, effective_state: "include" }],
    },
    diagnostic_summary: { compteurs: { total: 5, inclus: 3, exclus: 2, ecarts: 1 } },
    diagnostic_rooms: [
      {
        object_id: 1,
        compteurs: { total: 5, inclus: 3, exclus: 2, ecarts: 1 },
        summary: {},
      },
    ],
    diagnostic_equipments: {},
  };

  const model = scopeSummary.createModel(response);
  // Compteurs depuis diagnostics
  assert.equal(model.global_counts.total, 5);
  assert.equal(model.global_counts.inclus, 3);
  assert.equal(model.global_counts.exclus, 2);
  assert.equal(model.global_counts.ecarts, 1);
  // Compteurs pièce
  assert.equal(model.pieces[0].counts.inclus, 3);
  assert.equal(model.pieces[0].counts.exclus, 2);
  assert.equal(model.pieces[0].counts.ecarts, 1);

  const html = scopeSummary.render(model);
  // En-tête colonne Écarts présent
  assert.match(html, /\{\{Écarts\}\}/);
  // Pas de Exceptions
  assert.doesNotMatch(html, /[Ee]xceptions/);
  assert.doesNotMatch(html, /\{\{Exceptions\}\}/);
});

// ---------------------------------------------------------------------------
// AC 7 — 5.4 : graceful degradation (daemon down)
// ---------------------------------------------------------------------------

test("4.2 / AC7 — daemon down : Écarts affiche —, pas de terme interdit, Total/Inclus/Exclus depuis fallback", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 3, include: 2, exclude: 1 } },
      pieces: [{ object_id: 1, object_name: "Cuisine", counts: { total: 3, include: 2, exclude: 1 } }],
      equipements: [
        { eq_id: 10, object_id: 1, effective_state: "include" },
      ],
    },
    // Pas de diagnostic_summary / diagnostic_rooms / diagnostic_equipments
  };

  const model = scopeSummary.createModel(response);
  // Fallback : ecarts null → toDisplayCount retourne &mdash;
  assert.equal(model.global_counts.total, 3);
  assert.equal(model.global_counts.inclus, 2);
  assert.equal(model.global_counts.exclus, 1);
  assert.equal(model.global_counts.ecarts, null);

  const html = scopeSummary.render(model);
  // Écarts affiche — (mdash)
  assert.match(html, /&mdash;/);
  // Pas de terme interdit
  assert.doesNotMatch(html, /H\u00e9rite de la pi\u00e8ce/);
  assert.doesNotMatch(html, /Exception locale/);
  assert.doesNotMatch(html, /Exceptions/);
  assert.doesNotMatch(html, /is_exception/);
  assert.doesNotMatch(html, /decision_source/);
  // Pas de badge perimetre sans diagnostic
  assert.doesNotMatch(html, /Exclu par la/);
  assert.doesNotMatch(html, /Exclu sur cet/);
});

// ---------------------------------------------------------------------------
// AC 1-3 — 5.5 : badge style uniforme (gris neutre, pas de label-info conditionnel)
// ---------------------------------------------------------------------------

test("4.2 / AC1-3 — style badge uniforme : exclu_par_piece et exclu_sur_equipement utilisent le même style gris", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 2, include: 0, exclude: 2 } },
      pieces: [{ object_id: 1, object_name: "Salon", counts: { total: 2, include: 0, exclude: 2 } }],
      equipements: [
        { eq_id: 71, object_id: 1, effective_state: "exclude" },
        { eq_id: 72, object_id: 1, effective_state: "exclude" },
      ],
    },
    diagnostic_equipments: {
      71: { perimetre: "exclu_par_piece" },
      72: { perimetre: "exclu_sur_equipement" },
    },
    diagnostic_summary: { compteurs: { total: 2, inclus: 0, exclus: 2, ecarts: 0 } },
    diagnostic_rooms: [
      {
        object_id: 1,
        compteurs: { total: 2, inclus: 0, exclus: 2, ecarts: 0 },
        summary: {},
      },
    ],
  };

  const html = scopeSummary.render(scopeSummary.createModel(response));

  // Les deux badges sont présents
  assert.match(html, /Exclu par la pi\u00e8ce/);
  assert.match(html, /Exclu sur cet \u00e9quipement/);

  // Aucun label-info pour les badges perimetre
  assert.doesNotMatch(html, /label-info[^>]*>Exclu par la pi\u00e8ce/);
  assert.doesNotMatch(html, /label-info[^>]*>Exclu sur cet/);

  // Les deux utilisent le style gris neutre
  const greyBadgeCount = (html.match(/background-color:#777;color:#fff/g) || []).length;
  assert.ok(greyBadgeCount >= 2, "Les deux badges source d'exclusion doivent utiliser background-color:#777");
});
