const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const scopeSummary = require("../../desktop/js/jeedom2ha_scope_summary.js");

function makeResponse() {
  return {
    status: "ok",
    published_scope: {
      global: {
        counts: { total: 3, include: 2, exclude: 1 },
      },
      pieces: [
        {
          object_id: 1,
          object_name: "Salon",
          counts: { total: 2, include: 1, exclude: 1 },
        },
        {
          object_id: 2,
          object_name: "Cuisine",
          counts: { total: 1, include: 1, exclude: 0 },
        },
      ],
      equipements: [
        { eq_id: 101, object_id: 1, name: "Lampe principale" },
        { eq_id: 102, object_id: 1, name: "Volet fenêtre" },
        { eq_id: 201, object_id: 2, name: "Prise Four" },
      ],
    },
    diagnostic_summary: {
      compteurs: { total: 3, inclus: 2, exclus: 1, ecarts: 1 },
    },
    diagnostic_rooms: [
      {
        object_id: 1,
        compteurs: { total: 2, inclus: 1, exclus: 1, ecarts: 1 },
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
        perimetre: "exclu_par_piece",
        statut: "publie",
        publies: 1,
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
      global: { publies: 12, statut: "Partiellement publiee" },
      pieces: [
        { object_id: 1, perimetre: "Incluse", publies: 7, statut: "Partiellement publiee" },
        { object_id: 2, perimetre: "Incluse", publies: 5, statut: "Publiee" },
      ],
    },
  };
}

function render(response) {
  return scopeSummary.render(scopeSummary.createModel(response));
}

function extractPieceRow(html, pieceId) {
  const re = new RegExp(
    `<tr class="[^"]*j2ha-row-piece[^"]*"[^>]*data-piece-id="${pieceId}"[\\s\\S]*?<\\/tr>`
  );
  return html.match(re);
}

test("4.5 / AC1+AC2: vue initiale limitée à Parc global + colonnes exactes", () => {
  const html = render(makeResponse());

  assert.match(
    html,
    /<th>Nom<\/th>\s*<th>Perimetre<\/th>\s*<th>Statut<\/th>\s*<th>Ecart<\/th>\s*<th>Total<\/th>\s*<th>Exclus<\/th>\s*<th>Inclus<\/th>\s*<th>Publies<\/th>\s*<th>Ecarts<\/th>/
  );

  const globalRow = html.match(/<tr class="j2ha-row-global[\s\S]*?<\/tr>/);
  assert.ok(globalRow);
  assert.doesNotMatch(globalRow[0], /display:none/);

  const pieceRows = html.match(/<tr class="[^"]*j2ha-row-piece[^"]*"[\s\S]*?<\/tr>/g) || [];
  pieceRows.forEach((rowHtml) => assert.match(rowHtml, /display:none/));
});

test("4.5 / AC3: badge Perimetre pièce contractuel + 3 badges fixes sur la ligne pièce", () => {
  const response = makeResponse();
  response.home_signals.pieces[0].perimetre = "Incluse";
  response.home_signals.pieces[1].perimetre = "Exclue";

  const html = render(response);
  const salonRow = extractPieceRow(html, 1);
  const cuisineRow = extractPieceRow(html, 2);

  assert.ok(salonRow, "La ligne pièce Salon doit exister");
  assert.ok(cuisineRow, "La ligne pièce Cuisine doit exister");
  assert.match(salonRow[0], /<td><span class="label label-success">Incluse<\/span><\/td>/);
  assert.match(cuisineRow[0], /<td><span class="label label-default[^"]*"[^>]*>Exclue<\/span><\/td>/);

  const salonBadges = salonRow[0].match(/<td><span class="label[^"]*"[^>]*>[^<]+<\/span><\/td>/g) || [];
  assert.equal(salonBadges.length, 3, "La ligne pièce doit garder exactement 3 badges fixes");
});

test("4.5 / P0: perimetre pièce explicite malgré les compteurs", () => {
  const response = makeResponse();
  response.published_scope.pieces[0].counts.include = 0;
  response.published_scope.pieces[0].counts.exclude = 2;
  response.home_signals.pieces[0].perimetre = "Incluse";

  const html = render(response);
  const salonRow = extractPieceRow(html, 1);

  assert.ok(salonRow, "La ligne pièce Salon doit exister");
  assert.match(salonRow[0], /<td><span class="label label-success">Incluse<\/span><\/td>/);
  assert.doesNotMatch(salonRow[0], /Exclue/);
});

test("4.5 / AC4: le Statut pièce est affiché tel que fourni (3 valeurs contractuelles)", () => {
  const response = makeResponse();
  response.home_signals.pieces = [
    { object_id: 1, perimetre: "Incluse", publies: 1, statut: "Publiee" },
    { object_id: 2, perimetre: "Incluse", publies: 1, statut: "Partiellement publiee" },
  ];
  response.published_scope.pieces.push({
    object_id: 3,
    object_name: "Bureau",
    counts: { total: 1, include: 1, exclude: 0 },
  });
  response.published_scope.equipements.push({ eq_id: 301, object_id: 3, name: "Prise Bureau" });
  response.diagnostic_rooms.push({ object_id: 3, compteurs: { total: 1, inclus: 1, exclus: 0, ecarts: 0 } });
  response.diagnostic_equipments[301] = { perimetre: "inclus", statut: "publie", publies: 1, ecart: false };
  response.home_signals.pieces.push({ object_id: 3, perimetre: "Incluse", publies: 0, statut: "Non publiee" });

  const html = render(response);
  assert.match(html, />Publiee<\/span>/);
  assert.match(html, />Partiellement publiee<\/span>/);
  assert.match(html, />Non publiee<\/span>/);
});

test("4.5 / AC4: le frontend ne recompose pas le Statut pièce depuis les équipements", () => {
  const response = makeResponse();

  // Contradiction volontaire: les équipements laisseraient penser 'Publiee',
  // mais le signal contractuel impose 'Non publiee'.
  response.diagnostic_equipments[101].statut = "publie";
  response.diagnostic_equipments[101].publies = 1;
  response.diagnostic_equipments[101].ecart = false;
  response.home_signals.pieces[0].statut = "Non publiee";

  const html = render(response);
  const salonRow = extractPieceRow(html, 1);

  assert.ok(salonRow, "La ligne pièce Salon doit exister");
  assert.match(salonRow[0], /Non publiee/);
  assert.doesNotMatch(salonRow[0], /Publiee/);
});

test("4.5 / AC5: Publies affiché depuis la source contractuelle, sans recalcul JS", () => {
  const response = makeResponse();

  // Contradiction volontaire: la somme naive des équipements ne vaut pas 7.
  response.home_signals.pieces[0].publies = 7;

  const html = render(response);
  const salonRow = extractPieceRow(html, 1);

  assert.ok(salonRow);
  assert.match(salonRow[0], />7<\/td>/);
});

test("4.5 / AC6: signal manquant => état neutre, pas de fallback métier local", () => {
  const response = makeResponse();
  response.home_signals.pieces[0].publies = null;
  response.home_signals.pieces[0].statut = "";

  const html = render(response);
  const salonRow = extractPieceRow(html, 1);

  assert.ok(salonRow);
  assert.match(salonRow[0], /&mdash;/);
});

test("4.5 / AC4: aucune valeur non contractuelle locale de Statut pièce", () => {
  const response = makeResponse();
  response.home_signals.pieces[0].statut = "Invente";

  const html = render(response);
  const salonRow = extractPieceRow(html, 1);

  assert.ok(salonRow);
  assert.doesNotMatch(salonRow[0], /Invente/);
  assert.match(salonRow[0], /&mdash;/);
});

test("4.5 / AC8+AC9: badge Ecart cliquable seulement si ecart=true et porte eq_id", () => {
  const html = render(makeResponse());

  assert.match(html, /j2ha-ecart-clickable[^>]*data-eq-id="101"/);
  assert.match(html, /j2ha-ecart-affordance/);
  assert.match(html, /Voir le diagnostic pour le detail/);

  assert.doesNotMatch(html, /j2ha-ecart-clickable[^>]*data-eq-id="102"/);
  assert.doesNotMatch(html, /j2ha-ecart-clickable[^>]*data-eq-id="201"/);
});

test("4.5 / AC3+AC7+AC10: pas de diagnostic inline, exclus visibles", () => {
  const html = render(makeResponse());

  assert.match(html, /Volet fenêtre/);
  assert.match(html, /Exclu par la pièce/);

  assert.doesNotMatch(html, /Console principale|Diagnostic utilisateur|Diagnostic technique détaillé/);
  assert.doesNotMatch(html, /Confiance|reason_code|matched_commands|unmatched_commands|Action recommandée|Changements à appliquer/);
});

test("4.5 / P1.1: badge Contrat backend et aide résiduelle supprimés", () => {
  const phpPath = path.resolve(__dirname, "../../desktop/php/jeedom2ha.php");
  const php = fs.readFileSync(phpPath, "utf8");

  assert.doesNotMatch(php, /Contrat backend/);
  assert.doesNotMatch(php, /Cette synth[eè]se décrit le périmètre local/);
});

test("4.5 / P1.2: auto-refresh périodique supprimé pour la synthèse home", () => {
  const jsPath = path.resolve(__dirname, "../../desktop/js/jeedom2ha.js");
  const js = fs.readFileSync(jsPath, "utf8");

  assert.doesNotMatch(js, /setInterval\([\s\S]*refreshBridgeStatus/);
  assert.doesNotMatch(js, /refreshPublishedScopeSummary\(true\)/);
});

test("4.5 / P1.3: badge Ecart cliquable sans soulignement et affordance légère", () => {
  const html = render(makeResponse());
  assert.match(html, /j2ha-ecart-affordance/);
  assert.doesNotMatch(html, /text-decoration:underline/);

  const cssPath = path.resolve(__dirname, "../../desktop/css/jeedom2ha.css");
  const css = fs.readFileSync(cssPath, "utf8");
  assert.match(css, /\.j2ha-ecart-affordance/);
  assert.match(css, /cursor:\s*pointer/);
  assert.match(css, /:hover/);
});

test("4.5 / P1.4+P1.5: badges gris harmonisés + aligné/alignée en vert", () => {
  const response = makeResponse();
  response.diagnostic_rooms[0].compteurs.ecarts = 0;
  response.diagnostic_rooms[1].compteurs.ecarts = 0;
  response.home_signals.pieces[0].statut = "Non publiee";

  const html = render(response);
  const salonRow = extractPieceRow(html, 1);

  assert.ok(salonRow);
  assert.match(salonRow[0], /label-success">Alignée<\/span>/);
  assert.match(salonRow[0], /j2ha-muted-badge[^>]*>Non publiee<\/span>/);
  assert.match(html, /label-success">Aligné<\/span>/);
});

test("4.5 / P1.6: décalage horizontal réduit au dépliage", () => {
  const html = render(makeResponse());

  assert.match(html, /width:24px/);
  assert.doesNotMatch(html, /width:32px/);
});

test("4.5 / P2.1+P2.2: rendu binaire lisible sur lignes équipement", () => {
  const html = render(makeResponse());
  const equipRows = html.match(/<tr class="[^"]*j2ha-row-equipement[^"]*"[\s\S]*?<\/tr>/g) || [];

  assert.ok(equipRows.length > 0);
  equipRows.forEach((rowHtml) => {
    assert.match(rowHtml, /j2ha-binary-cell/);
    assert.doesNotMatch(rowHtml, />0<\/td>/);
    assert.doesNotMatch(rowHtml, />1<\/td>/);
  });
  assert.match(html, /&#10003;/);
});
