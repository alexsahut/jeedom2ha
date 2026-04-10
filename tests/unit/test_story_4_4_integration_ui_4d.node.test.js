const test = require("node:test");
const assert = require("node:assert/strict");

const scopeSummary = require("../../desktop/js/jeedom2ha_scope_summary.js");

function makeResponse(overrides = {}) {
  const base = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 3, include: 2, exclude: 1 } },
      pieces: [
        {
          object_id: 1,
          object_name: "Salon",
          counts: { total: 3, include: 2, exclude: 1 },
        },
      ],
      equipements: [
        { eq_id: 101, object_id: 1, name: "Lampe principale" },
        { eq_id: 102, object_id: 1, name: "Prise TV" },
        { eq_id: 103, object_id: 1, name: "Volet fenêtre" },
      ],
    },
    diagnostic_summary: {
      compteurs: { total: 3, inclus: 2, exclus: 1, ecarts: 1 },
    },
    diagnostic_rooms: [
      {
        object_id: 1,
        compteurs: { total: 3, inclus: 2, exclus: 1, ecarts: 1 },
      },
    ],
    diagnostic_equipments: {
      101: {
        perimetre: "inclus",
        statut: "non_publie",
        status_code: "published",
        reason_code: "sure",
        publies: 0,
        ecart: true,
        cause_label: "Aucun mapping compatible",
      },
      102: {
        perimetre: "inclus",
        statut: "publie",
        status_code: "not_supported",
        reason_code: "no_supported_generic_type",
        publies: 1,
        ecart: false,
      },
      103: {
        perimetre: "exclu_par_piece",
        statut: "non_publie",
        status_code: "excluded",
        reason_code: "excluded_object",
        publies: 0,
        ecart: false,
      },
    },
    home_signals: {
      global: { publies: 2, statut: "Partiellement publiee" },
      pieces: [
        { object_id: 1, publies: 2, statut: "Partiellement publiee" },
      ],
    },
  };

  return Object.assign({}, base, overrides);
}

test("4.4 non-regression: createModel conserve le contrat 4D équipement tel quel", () => {
  const model = scopeSummary.createModel(makeResponse());
  const eq = model.pieces[0].equipements[0];

  assert.equal(eq.perimetre, "inclus");
  assert.equal(eq.statut, "non_publie");
  assert.equal(eq.ecart, true);

  // Contradiction volontaire status_code vs statut:
  // le frontend doit conserver `statut` tel que fourni par le contrat 4D.
  assert.equal(eq.statut, "non_publie");
  assert.notEqual(eq.statut, "publie");
});

test("4.4 non-regression: pas de diagnostic inline dans la home", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  assert.doesNotMatch(html, /Console principale/);
  assert.doesNotMatch(html, /Diagnostic utilisateur/);
  assert.doesNotMatch(html, /Diagnostic technique détaillé/);
  assert.doesNotMatch(html, /Confiance|reason_code|matched_commands|unmatched_commands/);
});

test("4.4 non-regression: badge Ecart équipement cliquable uniquement si ecart=true", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  assert.match(html, /j2ha-ecart-clickable[^>]*data-eq-id="101"/);

  // Aucun badge cliquable pour eq 102 / 103 (ecart=false)
  assert.doesNotMatch(html, /j2ha-ecart-clickable[^>]*data-eq-id="102"/);
  assert.doesNotMatch(html, /j2ha-ecart-clickable[^>]*data-eq-id="103"/);
});

test("4.4 non-regression: les exclus restent visibles dans la hiérarchie home", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  assert.match(html, /Volet fenêtre/);
  assert.match(html, /Exclu par la pièce/);
});
