const test = require("node:test");
const assert = require("node:assert/strict");

const scopeSummary = require("../../desktop/js/jeedom2ha_scope_summary.js");

test("scope summary presenter keeps backend counts unchanged for mixed include/exclude/exception payload", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: {
        counts: {
          total: 7,
          include: 4,
          exclude: 3,
          exceptions: 2,
        },
      },
      pieces: [
        {
          object_id: 12,
          object_name: "Salon",
          counts: {
            total: 5,
            include: 2,
            exclude: 3,
            exceptions: 2,
          },
        },
      ],
      equipements: [
        { eq_id: 99, effective_state: "include" },
      ],
    },
  };

  const model = scopeSummary.createModel(response);
  assert.equal(model.has_contract, true);
  assert.equal(model.global_counts.total, 7);
  assert.equal(model.global_counts.include, 4);
  assert.equal(model.global_counts.exclude, 3);
  assert.equal(model.global_counts.exceptions, 2);

  assert.equal(model.pieces.length, 1);
  assert.equal(model.pieces[0].object_id, 12);
  assert.equal(model.pieces[0].object_name, "Salon");
  assert.equal(model.pieces[0].counts.total, 5);
  assert.equal(model.pieces[0].counts.include, 2);
  assert.equal(model.pieces[0].counts.exclude, 3);
  assert.equal(model.pieces[0].counts.exceptions, 2);
});

test("scope summary presenter refresh fully replaces rendered data with latest backend payload", () => {
  const firstResponse = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 3, include: 3, exclude: 0, exceptions: 0 } },
      pieces: [{ object_id: 1, object_name: "Cuisine", counts: { total: 3, include: 3, exclude: 0, exceptions: 0 } }],
    },
  };
  const refreshedResponse = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 3, include: 1, exclude: 2, exceptions: 1 } },
      pieces: [{ object_id: 1, object_name: "Cuisine", counts: { total: 3, include: 1, exclude: 2, exceptions: 1 } }],
    },
  };

  const firstHtml = scopeSummary.render(scopeSummary.createModel(firstResponse));
  const refreshedHtml = scopeSummary.render(scopeSummary.createModel(refreshedResponse));

  assert.match(firstHtml, />3<\/td>/);
  assert.match(refreshedHtml, />1<\/td>/);
  assert.match(refreshedHtml, />2<\/td>/);
  assert.doesNotMatch(refreshedHtml, />0<\/td>\s*<\/tr>/);
});
