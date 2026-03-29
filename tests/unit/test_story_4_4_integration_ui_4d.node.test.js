const test = require("node:test");
const assert = require("node:assert/strict");

const scopeSummary = require("../../desktop/js/jeedom2ha_scope_summary.js");

function makeResponse(overrides) {
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
        { eq_id: 101, object_id: 1, name: "Lampe principale", effective_state: "include" },
        { eq_id: 102, object_id: 1, name: "Prise TV", effective_state: "include" },
        { eq_id: 103, object_id: 1, name: "Volet fenêtre", effective_state: "exclude" },
      ],
    },
    diagnostic_summary: {
      compteurs: { total: 3, inclus: 2, exclus: 1, ecarts: 1 },
      primary_aggregated_status: "ambiguous",
      counts_by_status: { ambiguous: 1, excluded: 1, published: 1 },
    },
    diagnostic_rooms: [
      {
        object_id: 1,
        compteurs: { total: 3, inclus: 2, exclus: 1, ecarts: 1 },
        summary: {
          primary_aggregated_status: "partially_published",
          counts_by_status: { partially_published: 1, excluded: 1, ambiguous: 1 },
        },
      },
    ],
    diagnostic_equipments: {
      101: {
        perimetre: "inclus",
        statut: "non_publie",
        ecart: true,
        cause_label: "Aucun mapping compatible",
        cause_action: "Vérifier les types génériques",
        // Contradiction volontaire pour prouver l'absence de recalcul frontend
        status_code: "published",
        reason_code: "sure",
        confidence: "sure",
        detail: "Analyse pipeline: mapping manquant",
        remediation: "Corriger la configuration",
        matched_commands: [
          { cmd_id: 501, cmd_name: "OnOff", generic_type: "LIGHT_STATE" },
        ],
        unmatched_commands: [
          { cmd_id: 502, cmd_name: "Dimmer", generic_type: "BRIGHTNESS" },
        ],
      },
      102: {
        perimetre: "inclus",
        statut: "publie",
        ecart: false,
        cause_label: "CauseShouldNotAppear",
        cause_action: "ActionShouldNotAppear",
        // Contradiction volontaire pour prouver l'absence de recalcul frontend
        status_code: "not_supported",
        reason_code: "no_supported_generic_type",
        confidence: "probable",
        detail: "Détail technique 102",
        matched_commands: [],
        unmatched_commands: [],
      },
      103: {
        perimetre: "exclu_par_piece",
        statut: "non_publie",
        ecart: false,
        cause_label: "Exclu via règle pièce",
        cause_action: "Aucune",
        status_code: "excluded",
        reason_code: "excluded_by_object",
      },
    },
    in_scope_equipments: [{ eq_id: 101 }, { eq_id: 102 }],
  };

  return Object.assign({}, base, overrides || {});
}

test("4.4 / AC1+AC4 — createModel expose explicitement le contrat 4D sans dérivation locale", () => {
  const model = scopeSummary.createModel(makeResponse());
  const eq = model.pieces[0].equipements[0];

  assert.equal(eq.perimetre, "inclus");
  assert.equal(eq.statut, "non_publie");
  assert.equal(eq.ecart, true);
  assert.equal(eq.cause_label, "Aucun mapping compatible");
  assert.equal(eq.cause_action, "Vérifier les types génériques");

  // Contradiction volontaire status_code vs statut : l'UI doit garder statut backend 4D tel quel
  assert.equal(eq.status_code, "published");
  assert.equal(eq.statut, "non_publie");
});

test("4.4 / AC1+AC8 — rendu avec 3 surfaces distinctes pour un équipement in-scope", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  assert.match(html, /Console principale/);
  assert.match(html, /Diagnostic utilisateur/);
  assert.match(html, /Diagnostic technique détaillé/);

  // Le statut affiché suit la 4D (non_publie), pas le status_code contradictoire
  assert.match(html, /Lampe principale/);
  assert.match(html, /Non publié/);
});

test("4.4 / AC5+AC6 — cause affichée seulement quand ecart=true", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  assert.match(html, /Aucun mapping compatible/);
  assert.match(html, /Vérifier les types génériques/);

  // Cause absente pour eq 102 (ecart=false)
  assert.doesNotMatch(html, /CauseShouldNotAppear/);
  assert.doesNotMatch(html, /ActionShouldNotAppear/);
});

test("4.4 / AC2+AC8 — équipement exclu visible en console, sans diagnostic détaillé in-scope", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  const voletBlock = html.match(/Volet fenêtre[\s\S]*?<\/li>/);
  assert.ok(voletBlock, "Le bloc HTML de l'équipement exclu doit exister");

  assert.match(voletBlock[0], /Exclu par la pièce/);
  assert.doesNotMatch(voletBlock[0], /Diagnostic utilisateur/);
  assert.doesNotMatch(voletBlock[0], /Diagnostic technique détaillé/);
});

test("4.4 / AC3 — compteurs canoniques Total/Inclus/Exclus/Écarts sans compteur Exceptions", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  assert.match(html, /\{\{Total\}\}/);
  assert.match(html, /\{\{Inclus\}\}/);
  assert.match(html, /\{\{Exclus\}\}/);
  assert.match(html, /\{\{Écarts\}\}/);

  assert.doesNotMatch(html, /Exceptions/);
});

test("4.4 / AC8 — confiance absente console principale, visible seulement en diagnostic technique", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  assert.match(html, /Confiance/);

  const consoleBlock = html.match(/Console principale[\s\S]*?Diagnostic utilisateur/);
  assert.ok(consoleBlock, "Le bloc console principale doit exister");
  assert.doesNotMatch(consoleBlock[0], /Confiance/);
});

test("4.4 / AC8 — matched_commands/unmatched_commands visibles uniquement en diagnostic technique détaillé", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));
  const lampeBlock = html.match(/Lampe principale[\s\S]*?<\/details><\/li>/);
  assert.ok(lampeBlock, "Le bloc HTML de l'équipement in-scope doit exister");

  assert.match(lampeBlock[0], /Diagnostic technique détaillé/);
  assert.match(lampeBlock[0], /Couverture commandes/);
  assert.match(lampeBlock[0], /matched_commands/);
  assert.match(lampeBlock[0], /unmatched_commands/);
  assert.match(lampeBlock[0], /OnOff/);
  assert.match(lampeBlock[0], /Dimmer/);

  const consoleBlock = lampeBlock[0].match(/Console principale[\s\S]*?Diagnostic utilisateur/);
  assert.ok(consoleBlock, "Le bloc console principale doit exister");
  assert.doesNotMatch(consoleBlock[0], /Couverture commandes|matched_commands|unmatched_commands|OnOff|Dimmer/);

  const userDiagnosticBlock = lampeBlock[0].match(/Diagnostic utilisateur[\s\S]*?Diagnostic technique détaillé/);
  assert.ok(userDiagnosticBlock, "Le bloc diagnostic utilisateur doit exister");
  assert.doesNotMatch(userDiagnosticBlock[0], /Couverture commandes|matched_commands|unmatched_commands|OnOff|Dimmer/);
});

test("4.4 / AC9 — passthrough d'un wording backend modifié pour cause_label", () => {
  const response = makeResponse();
  response.diagnostic_equipments[101].cause_label = "Backend wording modifié sans reformulation locale";

  const html = scopeSummary.render(scopeSummary.createModel(response));
  assert.match(html, /Backend wording modifié sans reformulation locale/);
});
