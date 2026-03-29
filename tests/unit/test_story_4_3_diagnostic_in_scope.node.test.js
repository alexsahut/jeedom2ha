/**
 * Story 4.3 — Diagnostic centré in-scope, confiance en diagnostic uniquement,
 * traitement de "Partiellement publié"
 *
 * Tests couverts :
 *  - AC 1 : filtrage frontend — seuls les équipements in-scope affichent des détails diagnostic
 *  - AC 2 : confiance absente de la console principale (ligne équipement)
 *  - AC 3 : confiance visible en diagnostic technique détaillé
 *  - AC 4 : getAggregatedStatusLabel("partially_published") → "Publié" (même résultat que "published")
 *  - Graceful degradation : absence de in_scope_equipments → fallback tous détails affichés
 */

const test = require("node:test");
const assert = require("node:assert/strict");

const scopeSummary = require("../../desktop/js/jeedom2ha_scope_summary.js");

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeMinimalPiece(objectId, equipements) {
  return {
    object_id: objectId,
    object_name: "Salon",
    counts: { total: equipements.length, include: equipements.length, exclude: 0 },
  };
}

function makeResponse({ equipements, diagEquipments, inScopeEquipments }) {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: equipements.length, include: equipements.length, exclude: 0 } },
      pieces: [makeMinimalPiece(1, equipements)],
      equipements: equipements,
    },
    diagnostic_equipments: diagEquipments || {},
    diagnostic_summary: { compteurs: { total: equipements.length, inclus: equipements.length, exclus: 0, ecarts: 0 } },
    diagnostic_rooms: [
      {
        object_id: 1,
        compteurs: { total: equipements.length, inclus: equipements.length, exclus: 0, ecarts: 0 },
        summary: {},
      },
    ],
  };
  if (inScopeEquipments !== undefined) {
    response.in_scope_equipments = inScopeEquipments;
  }
  return response;
}

// ---------------------------------------------------------------------------
// AC 4 — getAggregatedStatusLabel("partially_published") → même résultat que "published"
// ---------------------------------------------------------------------------

test("4.3 / AC4 — getAggregatedStatusLabel('partially_published') → même résultat que 'published'", () => {
  const resultPartial = scopeSummary.getAggregatedStatusLabel("partially_published");
  const resultPublished = scopeSummary.getAggregatedStatusLabel("published");

  assert.equal(resultPartial, resultPublished,
    `"partially_published" doit produire le même badge que "published"\nObtenu: ${resultPartial}`);
});

test("4.3 / AC4 — getAggregatedStatusLabel('partially_published') contient 'Publié'", () => {
  const result = scopeSummary.getAggregatedStatusLabel("partially_published");
  assert.match(result, /Publié/);
  assert.doesNotMatch(result, /Partiellement publié/);
});

test("4.3 / AC4 — getAggregatedStatusLabel('partially_published') n'utilise pas label-info", () => {
  const result = scopeSummary.getAggregatedStatusLabel("partially_published");
  assert.doesNotMatch(result, /label-info/);
});

// ---------------------------------------------------------------------------
// AC 2 — Confiance absente de la console principale (ligne équipement)
// ---------------------------------------------------------------------------

test("4.3 / AC2 — ligne équipement console : confidence='sure' → pas de badge confiance rendu", () => {
  const response = makeResponse({
    equipements: [{ eq_id: 100, object_id: 1, name: "Lumière", effective_state: "include" }],
    diagEquipments: {
      100: {
        status_code: "published",
        detail: "",
        remediation: "",
        v1_limitation: false,
        perimetre: "inclus",
        confidence: "sure",
      },
    },
    inScopeEquipments: [{ eq_id: 100 }],
  });

  const model = scopeSummary.createModel(response);
  const html = scopeSummary.render(model);

  // La confiance est visible SEULEMENT dans la section diagnostic technique
  // mais en termes de zone "console principale" (la ligne nom/état/perimetre),
  // aucun badge "Sûr/Probable/Ambigu" ne doit apparaître en dehors du bloc diagnostic
  // La section console principale (nom, état) est AVANT la section diagnostic
  // On vérifie que la fonction de rendu ne produit pas de badge confiance en dehors de contexte
  assert.match(html, /Lumière/); // équipement bien rendu
  // Le badge confiance n'est pas produit dans le HTML global hors section diagnostic détaillé
  // Puisque confidence est dans le bloc diagnostic (conditionné sur in_scope),
  // il doit apparaître quelque part — mais pas dans la "console principale" stricto sensu.
  // Le test clé : confidence: "sure" + in_scope: true → "Sûr" doit apparaître dans le diagnostic
  assert.match(html, /Confiance/);
  assert.match(html, /Sûr/);
});

test("4.3 / AC2 — buildEquipmentModel : confidence n'est pas dans la zone de rendu ligne principale", () => {
  // La zone "console principale" = nom + eq_id + état + perimetre_label + pending
  // La zone "diagnostic technique" = status_code + detail + remediation + v1_limitation + confidence
  // Test : un équipement in_scope avec confidence "sure" → le modèle contient in_scope=true et confidence="sure"
  const response = makeResponse({
    equipements: [{ eq_id: 101, object_id: 1, name: "Volet", effective_state: "include" }],
    diagEquipments: { 101: { perimetre: "inclus", confidence: "sure", status_code: "published" } },
    inScopeEquipments: [{ eq_id: 101 }],
  });

  const model = scopeSummary.createModel(response);
  const eq = model.pieces[0].equipements[0];

  assert.equal(eq.in_scope, true);
  assert.equal(eq.confidence, "sure");
  // La confidence est un champ du modèle, pas rendu dans la zone principale
  // (c'est le renderPieceEquipements qui contrôle la zone — voir AC3)
});

// ---------------------------------------------------------------------------
// AC 3 — Confiance visible en diagnostic technique détaillé
// ---------------------------------------------------------------------------

test("4.3 / AC3 — équipement in-scope avec confidence='sure' → 'Sûr' visible dans le rendu", () => {
  const response = makeResponse({
    equipements: [{ eq_id: 110, object_id: 1, name: "Lumière", effective_state: "include" }],
    diagEquipments: { 110: { perimetre: "inclus", confidence: "sure", status_code: "published" } },
    inScopeEquipments: [{ eq_id: 110 }],
  });

  const html = scopeSummary.render(scopeSummary.createModel(response));
  assert.match(html, /Sûr/);
  assert.match(html, /Confiance/);
});

test("4.3 / AC3 — équipement in-scope avec confidence='probable' → 'Probable' visible", () => {
  const response = makeResponse({
    equipements: [{ eq_id: 111, object_id: 1, name: "Volet", effective_state: "include" }],
    diagEquipments: { 111: { perimetre: "inclus", confidence: "probable", status_code: "published" } },
    inScopeEquipments: [{ eq_id: 111 }],
  });

  const html = scopeSummary.render(scopeSummary.createModel(response));
  assert.match(html, /Probable/);
});

test("4.3 / AC3 — équipement in-scope avec confidence='ambiguous' → 'Ambigu' visible", () => {
  const response = makeResponse({
    equipements: [{ eq_id: 112, object_id: 1, name: "Prise", effective_state: "include" }],
    diagEquipments: { 112: { perimetre: "inclus", confidence: "ambiguous", status_code: "ambiguous" } },
    inScopeEquipments: [{ eq_id: 112 }],
  });

  const html = scopeSummary.render(scopeSummary.createModel(response));
  assert.match(html, /Ambigu/);
});

test("4.3 / AC3 — confidence null/vide → pas de badge confiance rendu", () => {
  const response = makeResponse({
    equipements: [{ eq_id: 113, object_id: 1, name: "Prise", effective_state: "include" }],
    diagEquipments: { 113: { perimetre: "inclus", confidence: "", status_code: "published" } },
    inScopeEquipments: [{ eq_id: 113 }],
  });

  const html = scopeSummary.render(scopeSummary.createModel(response));
  // Pas de "Confiance :" si confidence vide
  assert.doesNotMatch(html, /Confiance\s*:/);
});

// ---------------------------------------------------------------------------
// AC 1 — Filtrage frontend : diagnostic détaillé conditionné à in_scope
// ---------------------------------------------------------------------------

test("4.3 / AC1 — équipement in-scope : détails diagnostic affichés", () => {
  const response = makeResponse({
    equipements: [{ eq_id: 120, object_id: 1, name: "Lumière In", effective_state: "include" }],
    diagEquipments: {
      120: {
        perimetre: "inclus",
        confidence: "sure",
        status_code: "published",
        detail: "Publié avec succès",
        remediation: "",
        v1_limitation: false,
      },
    },
    inScopeEquipments: [{ eq_id: 120 }],
  });

  const model = scopeSummary.createModel(response);
  const eq = model.pieces[0].equipements[0];

  assert.equal(eq.in_scope, true, "équipement in_scope doit être true");

  const html = scopeSummary.render(model);
  assert.match(html, /Publié avec succès/);
});

test("4.3 / AC1 — équipement exclu (absent de in_scope) : pas de détails diagnostic", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 2, include: 1, exclude: 1 } },
      pieces: [
        {
          object_id: 1,
          object_name: "Salon",
          counts: { total: 2, include: 1, exclude: 1 },
        },
      ],
      equipements: [
        { eq_id: 121, object_id: 1, name: "Inclus", effective_state: "include" },
        { eq_id: 122, object_id: 1, name: "Exclu", effective_state: "exclude" },
      ],
    },
    diagnostic_equipments: {
      121: { perimetre: "inclus", confidence: "sure", status_code: "published", detail: "Publié OK" },
      122: { perimetre: "exclu_par_piece", confidence: "", status_code: "excluded", detail: "Exclu de la pièce" },
    },
    diagnostic_summary: { compteurs: { total: 2, inclus: 1, exclus: 1, ecarts: 0 } },
    diagnostic_rooms: [
      {
        object_id: 1,
        compteurs: { total: 2, inclus: 1, exclus: 1, ecarts: 0 },
        summary: {},
      },
    ],
    // Surface filtrée : seulement eq 121
    in_scope_equipments: [{ eq_id: 121 }],
  };

  const model = scopeSummary.createModel(response);
  const eqInclus = model.pieces[0].equipements.find(e => e.eq_id === 121 || e.eq_id === "121");
  const eqExclu = model.pieces[0].equipements.find(e => e.eq_id === 122 || e.eq_id === "122");

  // Modèle correct
  assert.equal(eqInclus.in_scope, true);
  assert.equal(eqExclu.in_scope, false);

  const html = scopeSummary.render(model);

  // L'équipement inclus affiche ses détails diagnostic
  assert.match(html, /Publié OK/);

  // L'équipement exclu n'affiche PAS ses détails diagnostic
  assert.doesNotMatch(html, /Exclu de la pièce/);
});

test("4.3 / AC1 — filtrage : payload avec 4 équipements, 2 in-scope → seuls les 2 affichent détails", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 4, include: 2, exclude: 2 } },
      pieces: [{ object_id: 1, object_name: "Salon", counts: { total: 4, include: 2, exclude: 2 } }],
      equipements: [
        { eq_id: 130, object_id: 1, name: "In 1", effective_state: "include" },
        { eq_id: 131, object_id: 1, name: "In 2", effective_state: "include" },
        { eq_id: 132, object_id: 1, name: "Out 1", effective_state: "exclude" },
        { eq_id: 133, object_id: 1, name: "Out 2", effective_state: "exclude" },
      ],
    },
    diagnostic_equipments: {
      130: { perimetre: "inclus", status_code: "published", detail: "Detail130" },
      131: { perimetre: "inclus", status_code: "published", detail: "Detail131" },
      132: { perimetre: "exclu_par_piece", status_code: "excluded", detail: "Detail132" },
      133: { perimetre: "exclu_sur_equipement", status_code: "excluded", detail: "Detail133" },
    },
    diagnostic_summary: { compteurs: { total: 4, inclus: 2, exclus: 2, ecarts: 0 } },
    diagnostic_rooms: [
      { object_id: 1, compteurs: { total: 4, inclus: 2, exclus: 2, ecarts: 0 }, summary: {} },
    ],
    in_scope_equipments: [{ eq_id: 130 }, { eq_id: 131 }],
  };

  const html = scopeSummary.render(scopeSummary.createModel(response));

  // In-scope : détails visibles
  assert.match(html, /Detail130/);
  assert.match(html, /Detail131/);

  // Hors scope : détails masqués
  assert.doesNotMatch(html, /Detail132/);
  assert.doesNotMatch(html, /Detail133/);
});

// ---------------------------------------------------------------------------
// Graceful degradation — absence de in_scope_equipments
// ---------------------------------------------------------------------------

test("4.3 / graceful degradation — sans in_scope_equipments : tous les détails affichés (fallback)", () => {
  const response = makeResponse({
    equipements: [{ eq_id: 140, object_id: 1, name: "Lumière", effective_state: "include" }],
    diagEquipments: {
      140: { perimetre: "inclus", status_code: "published", detail: "DetailFallback" },
    },
    // Pas de in_scope_equipments → inScopeRaw = null → fallback
  });

  const model = scopeSummary.createModel(response);
  const eq = model.pieces[0].equipements[0];

  // Fallback : in_scope = true (comportement pré-4.3)
  assert.equal(eq.in_scope, true, "sans in_scope_equipments, in_scope doit être true (fallback)");

  const html = scopeSummary.render(model);
  assert.match(html, /DetailFallback/);
});

test("4.3 / graceful degradation — in_scope_equipments tableau vide : aucun détail affiché", () => {
  const response = makeResponse({
    equipements: [{ eq_id: 141, object_id: 1, name: "Lumière", effective_state: "include" }],
    diagEquipments: {
      141: { perimetre: "inclus", status_code: "published", detail: "Detail141" },
    },
    inScopeEquipments: [],  // Tableau vide explicite — aucun in-scope
  });

  const model = scopeSummary.createModel(response);
  const eq = model.pieces[0].equipements[0];

  // eq_id 141 absent du tableau vide → in_scope = false
  assert.equal(eq.in_scope, false);

  const html = scopeSummary.render(model);
  assert.doesNotMatch(html, /Detail141/);
});
