/**
 * Story 4.3 — Diagnostic in-scope (réaligné au contrat home 4.5)
 *
 * Invariants encore valides:
 * - getAggregatedStatusLabel("partially_published") reste absorbé sur "Publié"
 * - la home n'expose pas de diagnostic inline
 * - la home reste une surface de synthèse même si le payload contient des champs techniques
 */

const test = require("node:test");
const assert = require("node:assert/strict");

const scopeSummary = require("../../desktop/js/jeedom2ha_scope_summary.js");

function makeResponse(overrides = {}) {
  const base = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 2, include: 1, exclude: 1 } },
      pieces: [{ object_id: 1, object_name: "Salon", counts: { total: 2, include: 1, exclude: 1 } }],
      equipements: [
        { eq_id: 120, object_id: 1, name: "Lumière In" },
        { eq_id: 121, object_id: 1, name: "Volet Out" },
      ],
    },
    diagnostic_summary: { compteurs: { total: 2, inclus: 1, exclus: 1, ecarts: 1 } },
    diagnostic_rooms: [{ object_id: 1, compteurs: { total: 2, inclus: 1, exclus: 1, ecarts: 1 } }],
    diagnostic_equipments: {
      120: {
        perimetre: "inclus",
        statut: "non_publie",
        ecart: true,
        publies: 0,
        cause_label: "Mapping manquant",
        status_code: "ambiguous",
        reason_code: "ambiguous_skipped",
        detail: "Detail interne",
        remediation: "Action interne",
        confidence: "sure",
      },
      121: {
        perimetre: "exclu_par_piece",
        statut: "non_publie",
        ecart: false,
        publies: 0,
        detail: "Detail exclu",
        confidence: "probable",
      },
    },
    in_scope_equipments: [{ eq_id: 120 }],
  };

  return Object.assign({}, base, overrides);
}

test("4.3 / AC4 — getAggregatedStatusLabel('partially_published') == 'published'", () => {
  const resultPartial = scopeSummary.getAggregatedStatusLabel("partially_published");
  const resultPublished = scopeSummary.getAggregatedStatusLabel("published");

  assert.equal(resultPartial, resultPublished);
  assert.match(resultPartial, /Publié/);
  assert.doesNotMatch(resultPartial, /Partiellement publié|label-info/);
});

test("4.3 — la home n'affiche plus aucun champ diagnostic inline", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  assert.doesNotMatch(html, /Console principale|Diagnostic utilisateur|Diagnostic technique détaillé/);
  assert.doesNotMatch(html, /Confiance|status_code|reason_code|Detail interne|Action interne|Detail exclu/);
});

test("4.3 — le payload in_scope ne réintroduit pas de rendu diagnostic inline", () => {
  const withScope = makeResponse({ in_scope_equipments: [{ eq_id: 120 }] });
  const withoutScope = makeResponse({ in_scope_equipments: [] });

  const htmlWithScope = scopeSummary.render(scopeSummary.createModel(withScope));
  const htmlWithoutScope = scopeSummary.render(scopeSummary.createModel(withoutScope));

  assert.doesNotMatch(htmlWithScope, /Diagnostic utilisateur|Confiance|status_code|reason_code|Detail interne/);
  assert.doesNotMatch(htmlWithoutScope, /Diagnostic utilisateur|Confiance|status_code|reason_code|Detail interne/);
});

test("4.3 — le badge Ecart porte la cause courte et le point d'entrée diagnostic", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  assert.match(html, /j2ha-ecart-clickable[^>]*data-eq-id="120"/);
  assert.match(html, /Mapping manquant \| Voir le diagnostic pour le detail/);
  assert.doesNotMatch(html, /j2ha-ecart-clickable[^>]*data-eq-id="121"/);
});

test("4.3 — les exclus restent visibles en home sans exposition du détail diagnostic", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  assert.match(html, /Volet Out/);
  assert.match(html, /Exclu par la pièce/);
  assert.doesNotMatch(html, /Detail exclu|Confiance|reason_code|status_code/);
});
