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
    /<th>Nom<\/th>\s*<th>Perimetre<\/th>\s*<th>Statut<\/th>\s*<th>Ecart<\/th>\s*<th>Actions<\/th>\s*<th>Total<\/th>\s*<th>Exclus<\/th>\s*<th>Inclus<\/th>\s*<th>Publies<\/th>\s*<th>Ecarts<\/th>/
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

test("createModel: matched_commands passthrough state_class/unit_of_measurement quand fournis (Story 15.1)", () => {
  const response = makeResponse();
  response.diagnostic_equipments = {
    101: {
      matched_commands: [
        { cmd_id: 9001, cmd_name: "Puissance", generic_type: "POWER", state_class: "measurement", unit_of_measurement: "W" },
      ],
      unmatched_commands: [],
    },
  };

  const model = scopeSummary.createModel(response);
  const equip = model.pieces[0].equipements.find((e) => e.eq_id === 101);

  assert.equal(equip.matched_commands.length, 1);
  assert.equal(equip.matched_commands[0].state_class, "measurement");
  assert.equal(equip.matched_commands[0].unit_of_measurement, "W");
});

test("createModel: matched_commands sans state_class => aucune clé Energy inventée (Story 15.1)", () => {
  const response = makeResponse();
  response.diagnostic_equipments = {
    102: {
      matched_commands: [
        { cmd_id: 9002, cmd_name: "Etat prise", generic_type: "ENERGY_STATE" },
      ],
      unmatched_commands: [],
    },
  };

  const model = scopeSummary.createModel(response);
  const equip = model.pieces[0].equipements.find((e) => e.eq_id === 102);

  assert.equal(equip.matched_commands.length, 1);
  assert.equal(Object.prototype.hasOwnProperty.call(equip.matched_commands[0], "state_class"), false);
  assert.equal(Object.prototype.hasOwnProperty.call(equip.matched_commands[0], "unit_of_measurement"), false);
});

test("createModel: matched_commands passthrough streaming quand fourni (Story 15.2)", () => {
  const response = makeResponse();
  response.diagnostic_equipments = {
    101: {
      matched_commands: [
        { cmd_id: 9003, cmd_name: "Temperature", generic_type: "TEMP", streaming: true },
      ],
      unmatched_commands: [],
    },
  };

  const model = scopeSummary.createModel(response);
  const equip = model.pieces[0].equipements.find((e) => e.eq_id === 101);

  assert.equal(equip.matched_commands.length, 1);
  assert.equal(equip.matched_commands[0].streaming, true);
});

test("createModel: matched_commands sans streaming => aucune clé inventée (Story 15.2)", () => {
  const response = makeResponse();
  response.diagnostic_equipments = {
    102: {
      matched_commands: [
        { cmd_id: 9004, cmd_name: "Etat prise", generic_type: "ENERGY_STATE" },
      ],
      unmatched_commands: [],
    },
  };

  const model = scopeSummary.createModel(response);
  const equip = model.pieces[0].equipements.find((e) => e.eq_id === 102);

  assert.equal(equip.matched_commands.length, 1);
  assert.equal(Object.prototype.hasOwnProperty.call(equip.matched_commands[0], "streaming"), false);
});

test("createModel: expose streaming_actif/streaming_cibles_count globaux (Story 15.2)", () => {
  const response = makeResponse();
  response.diagnostic_summary = Object.assign({}, response.diagnostic_summary, {
    streaming_actif: true,
    streaming_cibles_count: 5,
  });

  const model = scopeSummary.createModel(response);

  assert.equal(model.global.streaming_actif, true);
  assert.equal(model.global.streaming_cibles_count, 5);
});

test("createModel: streaming_actif/streaming_cibles_count par défaut sans state_synchronizer (Story 15.2)", () => {
  const model = scopeSummary.createModel(makeResponse());

  assert.equal(model.global.streaming_actif, false);
  assert.equal(model.global.streaming_cibles_count, 0);
});

test("createModel: fan_switch_parity passthrough quand fourni (Story 15.3)", () => {
  const response = makeResponse();
  response.diagnostic_equipments = {
    101: {
      fan_switch_parity: true,
    },
  };

  const model = scopeSummary.createModel(response);
  const equip = model.pieces[0].equipements.find((e) => e.eq_id === 101);

  assert.equal(equip.fan_switch_parity, true);
});

test("createModel: fan_switch_parity absent => valeur par défaut false, aucune valeur inventée (Story 15.3)", () => {
  const response = makeResponse();
  response.diagnostic_equipments = {
    102: {
      statut: "publie",
    },
  };

  const model = scopeSummary.createModel(response);
  const equip = model.pieces[0].equipements.find((e) => e.eq_id === 102);

  assert.equal(equip.fan_switch_parity, false);
});
