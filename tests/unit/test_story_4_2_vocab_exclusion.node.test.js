/**
 * Story 4.2 — Vocabulaire d'exclusion par source (réaligné contrat home 4.5)
 *
 * Invariants conservés:
 * - mapping périmètre backend -> libellé UI stable
 * - disparition du vocabulaire "exception"
 * - compteurs canoniques backend conservés
 * - dégradation contrôlée sans diagnostic
 */

const test = require("node:test");
const assert = require("node:assert/strict");

const scopeSummary = require("../../desktop/js/jeedom2ha_scope_summary.js");

function makeResponse(overrides = {}) {
  const base = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 4, include: 2, exclude: 2 } },
      pieces: [{ object_id: 1, object_name: "Salon", counts: { total: 4, include: 2, exclude: 2 } }],
      equipements: [
        { eq_id: 10, object_id: 1, name: "Lampe" },
        { eq_id: 11, object_id: 1, name: "Volet" },
        { eq_id: 12, object_id: 1, name: "Prise" },
        { eq_id: 13, object_id: 1, name: "Capteur" },
      ],
    },
    diagnostic_summary: { compteurs: { total: 4, inclus: 2, exclus: 2, ecarts: 1 } },
    diagnostic_rooms: [{ object_id: 1, compteurs: { total: 4, inclus: 2, exclus: 2, ecarts: 1 } }],
    diagnostic_equipments: {
      10: { perimetre: "exclu_par_piece", statut: "non_publie", ecart: false, publies: 0 },
      11: { perimetre: "exclu_sur_equipement", statut: "non_publie", ecart: false, publies: 0 },
      12: { perimetre: "exclu_par_plugin", statut: "non_publie", ecart: true, publies: 0, cause_label: "Plugin exclu" },
      13: { perimetre: "inclus", statut: "publie", ecart: false, publies: 1 },
    },
  };

  return Object.assign({}, base, overrides);
}

test("4.2 — buildPerimetreLabel garde la table de correspondance attendue", () => {
  assert.equal(scopeSummary.buildPerimetreLabel("exclu_par_piece"), "Exclu par la pièce");
  assert.equal(scopeSummary.buildPerimetreLabel("exclu_par_plugin"), "Exclu par le plugin");
  assert.equal(scopeSummary.buildPerimetreLabel("exclu_sur_equipement"), "Exclu sur cet équipement");
  assert.equal(scopeSummary.buildPerimetreLabel("inclus"), "Inclus");
  assert.equal(scopeSummary.buildPerimetreLabel("unknown_value"), "");
});

test("4.2 — le rendu n'expose aucun vocabulaire legacy exception/héritage", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  assert.match(html, /Exclu par la pièce/);
  assert.match(html, /Exclu sur cet équipement/);
  assert.match(html, /Exclu par le plugin/);

  assert.doesNotMatch(html, /Hérite de la pièce|Exception locale|Exceptions|is_exception|decision_source/);
});

test("4.2 — les compteurs canoniques restent lus depuis le backend diagnostic", () => {
  const response = makeResponse({
    published_scope: {
      global: { counts: { total: 99, include: 98, exclude: 1 } },
      pieces: [{ object_id: 1, object_name: "Salon", counts: { total: 99, include: 98, exclude: 1 } }],
      equipements: [{ eq_id: 10, object_id: 1, name: "Lampe" }],
    },
    diagnostic_summary: { compteurs: { total: 4, inclus: 2, exclus: 2, ecarts: 1 } },
    diagnostic_rooms: [{ object_id: 1, compteurs: { total: 4, inclus: 2, exclus: 2, ecarts: 1 } }],
    diagnostic_equipments: { 10: { perimetre: "exclu_par_piece", statut: "non_publie", ecart: true, publies: 0 } },
  });

  const model = scopeSummary.createModel(response);
  assert.equal(model.global.counts.total, 4);
  assert.equal(model.global.counts.inclus, 2);
  assert.equal(model.global.counts.exclus, 2);
  assert.equal(model.global.counts.ecarts, 1);
  assert.equal(model.pieces[0].counts.total, 4);
  assert.equal(model.pieces[0].counts.inclus, 2);
  assert.equal(model.pieces[0].counts.exclus, 2);
  assert.equal(model.pieces[0].counts.ecarts, 1);
});

test("4.2 — le tableau conserve la colonne Ecarts et n'introduit jamais Exceptions", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));
  assert.match(html, /<th>Ecarts<\/th>/);
  assert.doesNotMatch(html, /Exceptions/);
});

test("4.2 — daemon down: fallback scope conservé, ecarts neutre, aucun terme interdit", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 3, include: 2, exclude: 1 } },
      pieces: [{ object_id: 1, object_name: "Cuisine", counts: { total: 3, include: 2, exclude: 1 } }],
      equipements: [{ eq_id: 10, object_id: 1, name: "Lampe" }],
    },
  };

  const model = scopeSummary.createModel(response);
  assert.equal(model.global.counts.total, 3);
  assert.equal(model.global.counts.inclus, 2);
  assert.equal(model.global.counts.exclus, 1);
  assert.equal(model.global.counts.ecarts, null);

  const html = scopeSummary.render(model);
  assert.match(html, /&mdash;/);
  assert.doesNotMatch(html, /Hérite de la pièce|Exception locale|Exceptions|is_exception|decision_source/);
});

test("4.2 — les sources d'exclusion gardent un style gris uniforme en home", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));
  assert.match(html, /Exclu par la pièce/);
  assert.match(html, /Exclu sur cet équipement/);

  const greyBadgeCount = (html.match(/background-color:#777;color:#fff/g) || []).length;
  assert.ok(greyBadgeCount >= 2);
});
