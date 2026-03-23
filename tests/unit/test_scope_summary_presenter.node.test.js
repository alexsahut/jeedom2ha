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
        { eq_id: 98, object_id: 12, effective_state: "exclude", decision_source: "piece", is_exception: false },
        { eq_id: 99, object_id: 12, effective_state: "include", decision_source: "exception_equipement", is_exception: true },
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
  assert.equal(model.pieces[0].equipements.length, 2);
  assert.deepEqual(model.pieces[0].equipements[0], {
    eq_id: 98,
    effective_state: "exclude",
    decision_source_label: "Hérite de la pièce",
    has_pending_home_assistant_changes: false,
  });
  assert.deepEqual(model.pieces[0].equipements[1], {
    eq_id: 99,
    effective_state: "include",
    decision_source_label: "Exception locale",
    has_pending_home_assistant_changes: false,
  });
});

test("scope summary presenter renders backend-first equipment details without extra taxonomy", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 3, include: 2, exclude: 1, exceptions: 1 } },
      pieces: [{ object_id: 1, object_name: "Cuisine", counts: { total: 3, include: 2, exclude: 1, exceptions: 1 } }],
      equipements: [
        { eq_id: 41, object_id: 1, effective_state: "exclude", decision_source: "piece", is_exception: false },
        { eq_id: 42, object_id: 1, effective_state: "include", decision_source: "exception_equipement", is_exception: true },
        { eq_id: 43, object_id: 1, effective_state: "include", decision_source: "equipement", is_exception: false },
      ],
    },
  };

  const html = scopeSummary.render(scopeSummary.createModel(response));

  assert.match(html, /#41/);
  assert.match(html, />exclude<\/span>/);
  assert.match(html, /Hérite de la pièce/);
  assert.match(html, /Exception locale/);
  assert.equal((html.match(/Hérite de la pièce/g) || []).length, 1);
  assert.equal((html.match(/Exception locale/g) || []).length, 1);
  assert.doesNotMatch(html, /Règle locale/);
  assert.doesNotMatch(html, /Action recommandée/);
  assert.doesNotMatch(html, /Home Assistant/);
});

test("scope summary presenter refresh fully replaces rendered data with latest backend payload", () => {
  const firstResponse = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 3, include: 3, exclude: 0, exceptions: 0 } },
      pieces: [{ object_id: 1, object_name: "Cuisine", counts: { total: 3, include: 3, exclude: 0, exceptions: 0 } }],
      equipements: [
        { eq_id: 51, object_id: 1, effective_state: "include", decision_source: "piece", is_exception: false },
      ],
    },
  };
  const refreshedResponse = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 3, include: 1, exclude: 2, exceptions: 1 } },
      pieces: [{ object_id: 1, object_name: "Cuisine", counts: { total: 3, include: 1, exclude: 2, exceptions: 1 } }],
      equipements: [
        { eq_id: 52, object_id: 1, effective_state: "exclude", decision_source: "exception_equipement", is_exception: true },
      ],
    },
  };

  const firstHtml = scopeSummary.render(scopeSummary.createModel(firstResponse));
  const refreshedHtml = scopeSummary.render(scopeSummary.createModel(refreshedResponse));

  assert.match(firstHtml, />3<\/td>/);
  assert.match(refreshedHtml, />1<\/td>/);
  assert.match(refreshedHtml, />2<\/td>/);
  assert.match(firstHtml, /#51/);
  assert.match(refreshedHtml, /#52/);
  assert.match(refreshedHtml, /Exception locale/);
  assert.doesNotMatch(refreshedHtml, /#51/);
});

// --- Story 1.4 tests ---

test("story-1.4: createModel extrait has_pending_home_assistant_changes aux trois niveaux", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: {
        counts: { total: 2, include: 1, exclude: 1, exceptions: 0 },
        has_pending_home_assistant_changes: true,
      },
      pieces: [
        {
          object_id: 10,
          object_name: "Salon",
          counts: { total: 2, include: 1, exclude: 1, exceptions: 0 },
          has_pending_home_assistant_changes: true,
        },
      ],
      equipements: [
        { eq_id: 101, object_id: 10, effective_state: "include", decision_source: "piece", is_exception: false, has_pending_home_assistant_changes: true },
        { eq_id: 102, object_id: 10, effective_state: "exclude", decision_source: "piece", is_exception: false, has_pending_home_assistant_changes: false },
      ],
    },
  };

  const model = scopeSummary.createModel(response);
  assert.equal(model.has_contract, true);
  assert.equal(model.global_pending, true);
  assert.equal(model.pieces[0].has_pending_home_assistant_changes, true);
  assert.equal(model.pieces[0].equipements[0].has_pending_home_assistant_changes, true);
  assert.equal(model.pieces[0].equipements[1].has_pending_home_assistant_changes, false);
});

test("story-1.4: render affiche Changements à appliquer aux trois niveaux quand flag est true", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: {
        counts: { total: 1, include: 1, exclude: 0, exceptions: 0 },
        has_pending_home_assistant_changes: true,
      },
      pieces: [
        {
          object_id: 20,
          object_name: "Cuisine",
          counts: { total: 1, include: 1, exclude: 0, exceptions: 0 },
          has_pending_home_assistant_changes: true,
        },
      ],
      equipements: [
        { eq_id: 201, object_id: 20, effective_state: "include", decision_source: "piece", is_exception: false, has_pending_home_assistant_changes: true },
      ],
    },
  };

  const html = scopeSummary.render(scopeSummary.createModel(response));
  assert.equal((html.match(/Changements à appliquer/g) || []).length, 3);
});

test("story-1.4: cas mixte - libellé uniquement sur l'équipement pending et la pièce, pas sur l'équipement non-pending", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: {
        counts: { total: 2, include: 1, exclude: 1, exceptions: 0 },
        has_pending_home_assistant_changes: true,
      },
      pieces: [
        {
          object_id: 30,
          object_name: "Chambre",
          counts: { total: 2, include: 1, exclude: 1, exceptions: 0 },
          has_pending_home_assistant_changes: true,
        },
      ],
      equipements: [
        { eq_id: 301, object_id: 30, effective_state: "include", decision_source: "piece", is_exception: false, has_pending_home_assistant_changes: true },
        { eq_id: 302, object_id: 30, effective_state: "exclude", decision_source: "piece", is_exception: false, has_pending_home_assistant_changes: false },
      ],
    },
  };

  const model = scopeSummary.createModel(response);
  assert.equal(model.pieces[0].equipements[0].has_pending_home_assistant_changes, true);
  assert.equal(model.pieces[0].equipements[1].has_pending_home_assistant_changes, false);

  const html = scopeSummary.render(model);
  // global (1) + pièce (1) + eq 301 (1) = 3 occurrences ; eq 302 n'en a pas
  assert.equal((html.match(/Changements à appliquer/g) || []).length, 3);
  assert.match(html, /#301/);
  assert.match(html, /#302/);
});

test("story-1.4: sans pending partout - aucun libellé Changements à appliquer affiché", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: {
        counts: { total: 2, include: 2, exclude: 0, exceptions: 0 },
        has_pending_home_assistant_changes: false,
      },
      pieces: [
        {
          object_id: 40,
          object_name: "Bureau",
          counts: { total: 2, include: 2, exclude: 0, exceptions: 0 },
          has_pending_home_assistant_changes: false,
        },
      ],
      equipements: [
        { eq_id: 401, object_id: 40, effective_state: "include", decision_source: "piece", is_exception: false, has_pending_home_assistant_changes: false },
        { eq_id: 402, object_id: 40, effective_state: "include", decision_source: "piece", is_exception: false, has_pending_home_assistant_changes: false },
      ],
    },
  };

  const html = scopeSummary.render(scopeSummary.createModel(response));
  assert.doesNotMatch(html, /Changements à appliquer/);
});

test("story-1.4: has_contract false - aucun libellé Changements à appliquer et aucune erreur", () => {
  const response = { status: "error", message: "Pas de sync effectuée" };
  const model = scopeSummary.createModel(response);
  assert.equal(model.has_contract, false);
  const html = scopeSummary.render(model);
  assert.doesNotMatch(html, /Changements à appliquer/);
  assert.match(html, /Pas de sync effectuée/);
});
