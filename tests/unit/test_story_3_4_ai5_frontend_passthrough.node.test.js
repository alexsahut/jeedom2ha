/**
 * Story 3.4 — Filet de sécurité AI-5 (réaligné home 4.5)
 *
 * Invariants conservés:
 * - frontend en lecture des signaux backend/relay encore contractuels
 * - pas de logique métier implicite côté JS
 * - pas de réintroduction de rendu diagnostic inline dans la home
 */

const test = require("node:test");
const assert = require("node:assert/strict");

const scopeSummary = require("../../desktop/js/jeedom2ha_scope_summary.js");

function makeResponse(overrides = {}) {
  const base = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 3, include: 1, exclude: 2 } },
      pieces: [{ object_id: 5, object_name: "Salon", counts: { total: 3, include: 1, exclude: 2 } }],
      equipements: [
        { eq_id: 42, object_id: 5, name: "Lampe Salon" },
        { eq_id: 43, object_id: 5, name: "Volet Salon" },
        { eq_id: 44, object_id: 5, name: "Thermostat Salon" },
      ],
    },
    diagnostic_summary: { compteurs: { total: 3, inclus: 1, exclus: 2, ecarts: 1 } },
    diagnostic_rooms: [{ object_id: 5, compteurs: { total: 3, inclus: 1, exclus: 2, ecarts: 1 } }],
    diagnostic_equipments: {
      42: {
        perimetre: "inclus",
        statut: "non_publie",
        ecart: true,
        cause_label: "Aucun mapping compatible",
        publies: 0,
        status_code: "ambiguous",
        reason_code: "ambiguous_skipped",
        detail: "Detail technique",
        remediation: "Remediation technique",
        confidence: "sure",
      },
      43: {
        perimetre: "exclu_par_piece",
        statut: "non_publie",
        ecart: false,
        publies: 0,
        status_code: "excluded",
      },
      44: {
        perimetre: "exclu_sur_equipement",
        statut: "publie",
        ecart: false,
        publies: 1,
        status_code: "not_supported",
      },
    },
    home_signals: {
      global: { publies: 2, statut: "Partiellement publiee" },
      pieces: [{ object_id: 5, publies: 2, statut: "Partiellement publiee" }],
    },
  };

  return Object.assign({}, base, overrides);
}

test("AI-5.1 — les compteurs globaux viennent des compteurs diagnostic (pas du scope brut)", () => {
  const response = makeResponse({
    published_scope: {
      global: { counts: { total: 99, include: 88, exclude: 11 } },
      pieces: [{ object_id: 5, object_name: "Salon", counts: { total: 99, include: 88, exclude: 11 } }],
      equipements: [{ eq_id: 42, object_id: 5, name: "Lampe Salon" }],
    },
    diagnostic_summary: { compteurs: { total: 3, inclus: 1, exclus: 2, ecarts: 1 } },
    diagnostic_rooms: [{ object_id: 5, compteurs: { total: 3, inclus: 1, exclus: 2, ecarts: 1 } }],
    diagnostic_equipments: {
      42: { perimetre: "inclus", statut: "non_publie", ecart: true, cause_label: "Aucun mapping compatible", publies: 0 },
    },
    home_signals: { global: { publies: 0, statut: "Non publiee" }, pieces: [{ object_id: 5, publies: 0, statut: "Non publiee" }] },
  });

  const model = scopeSummary.createModel(response);
  assert.equal(model.global.counts.total, 3);
  assert.equal(model.global.counts.inclus, 1);
  assert.equal(model.global.counts.exclus, 2);
  assert.equal(model.global.counts.ecarts, 1);
});

test("AI-5.2 — les champs périmètre/statut/écart équipement restent en passthrough backend", () => {
  const model = scopeSummary.createModel(makeResponse());
  const eq42 = model.pieces[0].equipements.find((eq) => eq.eq_id === 42);
  const eq43 = model.pieces[0].equipements.find((eq) => eq.eq_id === 43);
  const eq44 = model.pieces[0].equipements.find((eq) => eq.eq_id === 44);

  assert.equal(eq42.perimetre, "inclus");
  assert.equal(eq42.statut, "non_publie");
  assert.equal(eq42.ecart, true);
  assert.equal(eq42.counts.publies, 0);

  assert.equal(eq43.perimetre, "exclu_par_piece");
  assert.equal(eq44.perimetre, "exclu_sur_equipement");
});

test("AI-5.3 — la home n'expose aucun détail diagnostic technique inline", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  assert.doesNotMatch(html, /Console principale|Diagnostic utilisateur|Diagnostic technique détaillé/);
  assert.doesNotMatch(html, /status_code|reason_code|Detail technique|Remediation technique|Confiance|matched_commands|unmatched_commands/);
  assert.doesNotMatch(html, /Action recommandée|Limitation Home Assistant/);
});

test("AI-5.4 — les signaux relay home (Publies + Statut pièce) sont consommés tels quels", () => {
  const response = makeResponse({
    home_signals: {
      global: { publies: 7, statut: "Non publiee" },
      pieces: [{ object_id: 5, publies: 7, statut: "Publiee" }],
    },
    diagnostic_equipments: {
      42: { perimetre: "inclus", statut: "publie", ecart: false, publies: 1 },
      43: { perimetre: "inclus", statut: "publie", ecart: false, publies: 1 },
      44: { perimetre: "inclus", statut: "publie", ecart: false, publies: 1 },
    },
  });

  const model = scopeSummary.createModel(response);
  assert.equal(model.global.counts.publies, 7);
  assert.equal(model.pieces[0].counts.publies, 7);
  assert.equal(model.pieces[0].status_room, "Publiee");
});

test("AI-5.5 — getAggregatedStatusLabel garde les mappings canoniques sans badge inventé", () => {
  const fn = scopeSummary.getAggregatedStatusLabel;

  assert.match(fn("published"), /Publié/);
  assert.match(fn("excluded"), /Exclu/);
  assert.match(fn("ambiguous"), /Ambigu/);
  assert.match(fn("not_supported"), /Non supporté/);
  assert.match(fn("infra_incident"), /Incident infrastructure/);
  assert.match(fn("partially_published"), /Publié/);
  assert.equal(fn("unknown_code"), "");
});

test("AI-5.6 — dégradation gracieuse: sans diagnostic, la home reste rendable", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 2, include: 2, exclude: 0 } },
      pieces: [{ object_id: 1, object_name: "Cuisine", counts: { total: 2, include: 2, exclude: 0 } }],
      equipements: [{ eq_id: 10, object_id: 1, name: "Lumière" }],
    },
  };

  const model = scopeSummary.createModel(response);
  assert.equal(model.has_contract, true);
  assert.equal(model.global.counts.total, 2);
  assert.equal(model.pieces[0].counts.total, 2);

  const html = scopeSummary.render(model);
  assert.match(html, /Cuisine/);
  assert.doesNotMatch(html, /Diagnostic utilisateur|Confiance|Action recommandée|Limitation Home Assistant/);
});

test("AI-5.7 — pièce object_id:0 lit les compteurs diag object_id:null (fallback 0/null conservé)", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 5, include: 2, exclude: 3 } },
      pieces: [
        { object_id: 0, object_name: "Aucun", counts: { total: 3, include: 1, exclude: 2 } },
        { object_id: 10, object_name: "Salon", counts: { total: 2, include: 1, exclude: 1 } },
      ],
      equipements: [
        { eq_id: 1, object_id: 0, name: "Eq Aucun" },
        { eq_id: 2, object_id: 10, name: "Eq Salon" },
      ],
    },
    diagnostic_summary: { compteurs: { total: 5, inclus: 2, exclus: 3, ecarts: 0 } },
    diagnostic_rooms: [
      { object_id: null, compteurs: { total: 3, inclus: 1, exclus: 2, ecarts: 0 } },
      { object_id: 10, compteurs: { total: 2, inclus: 1, exclus: 1, ecarts: 0 } },
    ],
    diagnostic_equipments: {
      1: { perimetre: "exclu_par_piece", statut: "non_publie", ecart: false, publies: 0 },
      2: { perimetre: "inclus", statut: "publie", ecart: false, publies: 1 },
    },
    home_signals: {
      global: { publies: 1, statut: "Partiellement publiee" },
      pieces: [
        { object_id: 0, publies: 0, statut: "Non publiee" },
        { object_id: 10, publies: 1, statut: "Publiee" },
      ],
    },
  };

  const model = scopeSummary.createModel(response);
  assert.equal(model.pieces[0].object_id, 0);
  assert.equal(model.pieces[0].counts.total, 3);
  assert.equal(model.pieces[0].counts.inclus, 1);
  assert.equal(model.pieces[0].counts.exclus, 2);
  assert.equal(model.pieces[0].status_room, "Non publiee");
});
