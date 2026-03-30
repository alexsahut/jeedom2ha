const test = require("node:test");
const assert = require("node:assert/strict");

const scopeSummary = require("../../desktop/js/jeedom2ha_scope_summary.js");

function makeResponse(overrides = {}) {
  const base = {
    status: "ok",
    published_scope: {
      global: {
        counts: { total: 4, include: 3, exclude: 1 },
      },
      pieces: [
        {
          object_id: 1,
          object_name: "Salon",
          counts: { total: 3, include: 2, exclude: 1 },
        },
        {
          object_id: 2,
          object_name: "Cuisine",
          counts: { total: 1, include: 1, exclude: 0 },
        },
      ],
      equipements: [
        { eq_id: 101, object_id: 1, name: "Lampe principale" },
        { eq_id: 102, object_id: 1, name: "Prise TV" },
        { eq_id: 103, object_id: 1, name: "Volet fenêtre" },
        { eq_id: 201, object_id: 2, name: "Four" },
      ],
    },
    diagnostic_summary: {
      compteurs: { total: 4, inclus: 3, exclus: 1, ecarts: 2 },
    },
    diagnostic_rooms: [
      {
        object_id: 1,
        compteurs: { total: 3, inclus: 2, exclus: 1, ecarts: 2 },
      },
      {
        object_id: 2,
        compteurs: { total: 1, inclus: 1, exclus: 0, ecarts: 0 },
      },
    ],
    diagnostic_equipments: {
      101: {
        perimetre: "inclus",
        statut: "non_publie",
        publies: 0,
        ecart: true,
        cause_label: "Aucun mapping compatible",
      },
      102: {
        perimetre: "inclus",
        statut: "publie",
        publies: 1,
        ecart: false,
      },
      103: {
        perimetre: "exclu_par_piece",
        statut: "non_publie",
        publies: 0,
        ecart: false,
      },
      201: {
        perimetre: "inclus",
        statut: "publie",
        publies: 1,
        ecart: false,
      },
    },
    home_signals: {
      global: { publies: 99, statut: "Partiellement publiee" },
      pieces: [
        { object_id: 1, publies: 42, statut: "Publiee" },
        { object_id: 2, publies: 0, statut: "Non publiee" },
      ],
    },
  };

  return Object.assign({}, base, overrides);
}

test("createModel lit Publies + Statut pièce depuis la source contractuelle relay", () => {
  const model = scopeSummary.createModel(makeResponse());

  assert.equal(model.has_contract, true);
  assert.equal(model.global.counts.publies, 99);

  assert.equal(model.pieces.length, 2);
  assert.equal(model.pieces[0].status_room, "Publiee");
  assert.equal(model.pieces[0].counts.publies, 42);
  assert.equal(model.pieces[1].status_room, "Non publiee");
  assert.equal(model.pieces[1].counts.publies, 0);
});

test("render expose les colonnes exactes dans l'ordre contractuel", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  assert.match(
    html,
    /<th>Nom<\/th>\s*<th>Perimetre<\/th>\s*<th>Statut<\/th>\s*<th>Ecart<\/th>\s*<th>Total<\/th>\s*<th>Exclus<\/th>\s*<th>Inclus<\/th>\s*<th>Publies<\/th>\s*<th>Ecarts<\/th>/
  );
});

test("render initial: seule la ligne Parc global est visible", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  const globalRow = html.match(/<tr class="j2ha-row-global[\s\S]*?<\/tr>/);
  assert.ok(globalRow, "La ligne globale doit exister");
  assert.doesNotMatch(globalRow[0], /display:none/);

  const pieceRows = html.match(/<tr class="j2ha-row-piece[\s\S]*?<\/tr>/g) || [];
  assert.ok(pieceRows.length >= 1, "Au moins une ligne pièce doit exister");
  pieceRows.forEach((rowHtml) => assert.match(rowHtml, /display:none/));

  const eqRows = html.match(/<tr class="j2ha-row-equipement[\s\S]*?<\/tr>/g) || [];
  assert.ok(eqRows.length >= 1, "Au moins une ligne équipement doit exister");
  eqRows.forEach((rowHtml) => assert.match(rowHtml, /display:none/));
});

test("render: aucune surface diagnostic inline ni signaux interdits", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  assert.doesNotMatch(html, /Console principale|Diagnostic utilisateur|Diagnostic technique détaillé/);
  assert.doesNotMatch(html, /Confiance|reason_code|matched_commands|unmatched_commands|Action recommandée/);
});

test("render: les équipements exclus restent visibles en home", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));

  assert.match(html, /Volet fenêtre/);
  assert.match(html, /Exclu par la pièce/);
});

test("render: statut pièce hors domaine contractuel => état neutre, sans valeur locale inventée", () => {
  const response = makeResponse();
  response.home_signals.pieces[0].statut = "Surprenant";

  const html = scopeSummary.render(scopeSummary.createModel(response));
  const salonRow = html.match(/data-piece-id="1"[\s\S]*?<\/tr>/);

  assert.ok(salonRow, "La ligne pièce Salon doit exister");
  assert.doesNotMatch(salonRow[0], /Surprenant/);
  assert.match(salonRow[0], /&mdash;/);
});
