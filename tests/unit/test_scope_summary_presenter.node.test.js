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
    name: "",
    effective_state: "exclude",
    decision_source_label: "Hérite de la pièce",
    has_pending_home_assistant_changes: false,
  });
  assert.deepEqual(model.pieces[0].equipements[1], {
    eq_id: 99,
    name: "",
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

// --- Story 1.5 tests ---

test("story-1.5: render génère une structure accordéon avec lignes de détail masquées par défaut", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 2, include: 1, exclude: 1, exceptions: 0 } },
      pieces: [
        { object_id: 10, object_name: "Salon", counts: { total: 2, include: 1, exclude: 1, exceptions: 0 } },
      ],
      equipements: [
        { eq_id: 101, object_id: 10, effective_state: "include", decision_source: "piece", is_exception: false },
      ],
    },
  };

  const html = scopeSummary.render(scopeSummary.createModel(response));

  // Ligne synthèse cliquable avec identifiant de pièce
  assert.match(html, /class="j2ha-piece-summary"/);
  assert.match(html, /data-piece-id="10"/);
  // Indicateur de toggle présent dans la ligne synthèse
  assert.match(html, /j2ha-toggle-icon/);
  // Ligne de détail masquée par défaut
  assert.match(html, /class="j2ha-piece-detail"/);
  assert.match(html, /display:none/);
  // Nom de la pièce présent dans la synthèse
  assert.match(html, /Salon/);
});

test("story-1.5: Changements à appliquer reste visible dans la ligne synthèse même quand la pièce est repliée", () => {
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

  // Le badge pièce doit être dans la ligne synthèse (j2ha-piece-summary), pas uniquement dans la ligne de détail masquée
  const summaryRowMatch = html.match(/<tr class="j2ha-piece-summary"[^>]*>[\s\S]*?<\/tr>/);
  assert.ok(summaryRowMatch, "La ligne synthèse j2ha-piece-summary doit être présente");
  assert.ok(
    summaryRowMatch[0].includes("Changements à appliquer"),
    "Le badge Changements à appliquer doit être dans la ligne synthèse visible"
  );
});

test("story-1.5: badge exclude a un style inactif sans couleur rouge", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 1, include: 0, exclude: 1, exceptions: 0 } },
      pieces: [{ object_id: 5, object_name: "Chambre", counts: { total: 1, include: 0, exclude: 1, exceptions: 0 } }],
      equipements: [
        { eq_id: 55, object_id: 5, effective_state: "exclude", decision_source: "piece", is_exception: false },
      ],
    },
  };

  const html = scopeSummary.render(scopeSummary.createModel(response));

  // Badge exclude présent
  assert.match(html, />exclude<\/span>/);
  // Communique un état inactif (fond gris explicite, visible en thème sombre)
  assert.match(html, /background-color:#999/);
  // N'utilise pas la couleur rouge réservée aux incidents d'infrastructure
  assert.doesNotMatch(html, /label-danger/);
  // N'utilise pas le vert réservé à include
  const includeCount = (html.match(/label-success/g) || []).length;
  assert.equal(includeCount, 0, "label-success ne doit pas apparaître pour exclude");
  // N'utilise pas l'orange déjà réservé à Changements à appliquer
  assert.doesNotMatch(html, /label-warning/);
});

test("story-1.5: badge Exception locale visuellement distinct de Hérite de la pièce", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 2, include: 1, exclude: 1, exceptions: 1 } },
      pieces: [{ object_id: 7, object_name: "Bureau", counts: { total: 2, include: 1, exclude: 1, exceptions: 1 } }],
      equipements: [
        { eq_id: 71, object_id: 7, effective_state: "exclude", decision_source: "piece", is_exception: false },
        { eq_id: 72, object_id: 7, effective_state: "include", decision_source: "exception_equipement", is_exception: true },
      ],
    },
  };

  const html = scopeSummary.render(scopeSummary.createModel(response));

  // Les deux libellés sont présents
  assert.match(html, /Hérite de la pièce/);
  assert.match(html, /Exception locale/);
  // Exception locale utilise label-info (bleu informatif)
  assert.match(html, /label-info[^>]*>Exception locale<\/span>/);
  // Hérite de la pièce n'utilise pas label-info et a un fond gris explicite
  assert.doesNotMatch(html, /label-info[^>]*>Hérite de la pièce<\/span>/);
  assert.match(html, /background-color:#777[^>]*>Hérite de la pièce<\/span>/);
});

test("story-1.5: badge Exclue sur la ligne synthèse quand la pièce est entièrement exclue", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 2, include: 0, exclude: 2, exceptions: 0 } },
      pieces: [{ object_id: 8, object_name: "Garage", counts: { total: 2, include: 0, exclude: 2, exceptions: 0 } }],
      equipements: [
        { eq_id: 81, object_id: 8, effective_state: "exclude", decision_source: "piece", is_exception: false },
        { eq_id: 82, object_id: 8, effective_state: "exclude", decision_source: "piece", is_exception: false },
      ],
    },
  };

  const html = scopeSummary.render(scopeSummary.createModel(response));

  // Le badge Exclue doit être dans la ligne synthèse
  const summaryRowMatch = html.match(/<tr class="j2ha-piece-summary"[^>]*>[\s\S]*?<\/tr>/);
  assert.ok(summaryRowMatch, "La ligne synthèse j2ha-piece-summary doit être présente");
  assert.ok(
    summaryRowMatch[0].includes("Exclue"),
    "Le badge Exclue doit apparaître dans la ligne synthèse quand tous les équipements sont exclus"
  );
  // Le badge utilise le style inactif (fond gris explicite)
  assert.match(html, /background-color:#999[^>]*>Exclue<\/span>/);
});

test("story-1.5: pas de badge Exclue sur la ligne synthèse quand la pièce est mixte", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 3, include: 2, exclude: 1, exceptions: 0 } },
      pieces: [{ object_id: 9, object_name: "Terrasse", counts: { total: 3, include: 2, exclude: 1, exceptions: 0 } }],
      equipements: [
        { eq_id: 91, object_id: 9, effective_state: "include", decision_source: "piece", is_exception: false },
        { eq_id: 92, object_id: 9, effective_state: "exclude", decision_source: "piece", is_exception: false },
        { eq_id: 93, object_id: 9, effective_state: "include", decision_source: "piece", is_exception: false },
      ],
    },
  };

  const html = scopeSummary.render(scopeSummary.createModel(response));

  // Le badge Exclue NE doit PAS apparaître pour une pièce mixte
  const summaryRowMatch = html.match(/<tr class="j2ha-piece-summary"[^>]*>[\s\S]*?<\/tr>/);
  assert.ok(summaryRowMatch, "La ligne synthèse j2ha-piece-summary doit être présente");
  assert.ok(
    !summaryRowMatch[0].includes("Exclue"),
    "Le badge Exclue ne doit PAS apparaître quand la pièce contient des inclus"
  );
});

// --- Story 1.7 tests ---

test("story-1.7: render correctly displays name and eq_id fallback", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 2, include: 2, exclude: 0, exceptions: 0 } },
      pieces: [{ object_id: 1, object_name: "Cuisine", counts: { total: 2, include: 2, exclude: 0, exceptions: 0 } }],
      equipements: [
        { eq_id: 41, name: "Prise Four", object_id: 1, effective_state: "include", decision_source: "piece", is_exception: false },
        { eq_id: 42, name: "", object_id: 1, effective_state: "include", decision_source: "piece", is_exception: false },
        { eq_id: 43, object_id: 1, effective_state: "include", decision_source: "piece", is_exception: false },
      ],
    },
  };

  const model = scopeSummary.createModel(response);
  assert.equal(model.pieces[0].equipements[0].name, "Prise Four");
  assert.equal(model.pieces[0].equipements[1].name, "");
  assert.equal(model.pieces[0].equipements[2].name, "");

  const html = scopeSummary.render(model);

  // Avec nom: Prise Four en gras, et (#41) en grisé
  assert.match(html, /font-weight:bold[^>]*>Prise Four<\/span>/);
  assert.match(html, /font-size:0.9em[^>]*>\(\#41\)<\/span>/);
  // label-info badge doit être absent
  assert.doesNotMatch(html, /label-info[^>]*>\#41<\/span>/);

  // Sans nom (fallback): seulement le badge label-info pour #42 et #43
  assert.match(html, /label-info[^>]*>\#42<\/span>/);
  assert.match(html, /label-info[^>]*>\#43<\/span>/);
});
