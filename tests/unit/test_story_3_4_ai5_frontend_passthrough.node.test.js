/**
 * Story 3.4 — Filet de sécurité AI-5 : passthrough frontend sans transformation métier
 *
 * Ces tests prouvent que les données backend arrivent dans le HTML rendu
 * par createModel()+render() sans transformation, recalcul ni recomposition.
 *
 * ACs couverts : AC 1, AC 2, AC 3, AC 4, AC 6
 * Invariant : le frontend consomme, le backend calcule.
 */

const test = require("node:test");
const assert = require("node:assert/strict");

const scopeSummary = require("../../desktop/js/jeedom2ha_scope_summary.js");

// ---------------------------------------------------------------------------
// Payload de référence avec données diagnostic complètes
// ---------------------------------------------------------------------------

function makeResponse(overrides) {
  const base = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 3, include: 1, exclude: 1 } },
      pieces: [
        {
          object_id: 5,
          object_name: "Salon",
          counts: { total: 3, include: 1, exclude: 1 },
        },
      ],
      equipements: [
        { eq_id: 42, object_id: 5, name: "Lampe Salon", effective_state: "include" },
        { eq_id: 43, object_id: 5, name: "Volet Salon", effective_state: "exclude" },
        { eq_id: 44, object_id: 5, name: "Thermostat Salon", effective_state: "include" },
      ],
    },
    diagnostic_summary: {
      primary_aggregated_status: "ambiguous",
      total_equipments: 3,
      counts_by_status: { published: 1, ambiguous: 1, excluded: 1, not_supported: 0, infra_incident: 0 },
      counts_by_reason: { sure: 1, ambiguous_skipped: 1, excluded_eqlogic: 1 },
    },
    diagnostic_rooms: [
      {
        object_id: 5,
        summary: {
          primary_aggregated_status: "partially_published",
          total_equipments: 3,
          counts_by_status: { published: 1, ambiguous: 1, excluded: 1, not_supported: 0, infra_incident: 0 },
          counts_by_reason: { sure: 1, ambiguous_skipped: 1, excluded_eqlogic: 1 },
        },
      },
    ],
    diagnostic_equipments: {
      42: {
        status_code: "published",
        reason_code: "sure",
        detail: "",
        remediation: "",
        v1_limitation: false,
      },
      43: {
        status_code: "excluded",
        reason_code: "excluded_eqlogic",
        detail: "Équipement exclu manuellement du périmètre.",
        remediation: "Modifiez le périmètre dans la configuration du plugin.",
        v1_limitation: false,
      },
      44: {
        status_code: "not_supported",
        reason_code: "no_supported_generic_type",
        detail: "Ce type d'équipement n'est pas pris en charge vers Home Assistant dans cette version.",
        remediation: "Vérifiez la configuration des types génériques.",
        v1_limitation: true,
      },
    },
  };
  return Object.assign({}, base, overrides);
}

// ---------------------------------------------------------------------------
// AI-5.1 — Le statut global primary_aggregated_status est affiché depuis le backend
// ---------------------------------------------------------------------------

test("AI-5.1: primary_aggregated_status global 'ambiguous' apparaît dans le HTML rendu sans recalcul", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));
  // La valeur exacte du backend ('ambiguous') est reflétée dans le badge
  assert.match(html, /Ambigu/, "Le statut global ambiguous doit apparaître comme 'Ambigu'");
  assert.match(html, /Statut global HA/, "La section Statut global HA doit être présente");
});

// ---------------------------------------------------------------------------
// AI-5.2 — Les counts_by_status globaux sont affichés depuis le backend
// ---------------------------------------------------------------------------

test("AI-5.2: counts_by_status globaux (published:1, ambiguous:1, excluded:1) apparaissent dans le HTML", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));
  // Les compteurs doivent apparaître sous forme de chips compacts
  assert.match(html, /Publié:&nbsp;1/, "Compteur published:1 doit être visible");
  assert.match(html, /Ambigu:&nbsp;1/, "Compteur ambiguous:1 doit être visible");
  assert.match(html, /Exclu:&nbsp;1/, "Compteur excluded:1 doit être visible");
});

// ---------------------------------------------------------------------------
// AI-5.3 — primary_aggregated_status par pièce vient du backend, pas d'un recalcul
// ---------------------------------------------------------------------------

test("AI-5.3: primary_aggregated_status de la pièce 'partially_published' (transformé en Publié) sans recalcul local", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));
  // Le badge de la pièce est absorbé en Publié (Story 4.3)
  assert.match(html, /Publié/, "Badge partially_published de la pièce doit être affiché comme Publié");
  // Et ne pas utiliser l'ancien badge local 'Exclue' (qui n'est plus pertinent ici)
  const summaryRowMatch = html.match(/<tr class="j2ha-piece-summary"[^>]*>[\s\S]*?<\/tr>/);
  assert.ok(summaryRowMatch, "Ligne synthèse pièce doit exister");
  assert.ok(!summaryRowMatch[0].includes("Exclue"), "Le badge local 'Exclue' ne doit pas être utilisé quand le backend fournit primary_aggregated_status");
});

// ---------------------------------------------------------------------------
// AI-5.4 — Le detail backend est affiché tel quel comme raison principale
// ---------------------------------------------------------------------------

test("AI-5.4: detail backend de l'équipement exclu apparaît tel quel dans le HTML", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));
  // Le texte exact du backend doit apparaître — sans reformulation JS
  assert.match(
    html,
    /Équipement exclu manuellement du périmètre\./,
    "Le detail backend doit apparaître tel quel"
  );
});

// ---------------------------------------------------------------------------
// AI-5.5 — La remediation backend est affichée telle quelle si non vide
// ---------------------------------------------------------------------------

test("AI-5.5: remediation backend apparaît comme action recommandée si non vide", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));
  assert.match(html, /Action recommandée/, "Libellé 'Action recommandée' doit apparaître");
  assert.match(
    html,
    /Modifiez le périmètre dans la configuration du plugin\./,
    "La remediation backend doit apparaître telle quelle"
  );
});

// ---------------------------------------------------------------------------
// AI-5.6 — Limitation Home Assistant explicite quand v1_limitation=true
// ---------------------------------------------------------------------------

test("AI-5.6: 'Limitation Home Assistant' apparaît explicitement quand v1_limitation=true", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));
  assert.match(html, /Limitation Home Assistant/, "Le badge 'Limitation Home Assistant' doit apparaître pour v1_limitation=true");
});

// ---------------------------------------------------------------------------
// AI-5.7 — Pas de "Limitation Home Assistant" quand v1_limitation=false
// ---------------------------------------------------------------------------

test("AI-5.7: pas de 'Limitation Home Assistant' quand v1_limitation=false pour tous les équipements", () => {
  const response = makeResponse();
  // Forcer v1_limitation=false partout
  response.diagnostic_equipments[42].v1_limitation = false;
  response.diagnostic_equipments[43].v1_limitation = false;
  response.diagnostic_equipments[44].v1_limitation = false;
  const html = scopeSummary.render(scopeSummary.createModel(response));
  assert.doesNotMatch(html, /Limitation Home Assistant/, "Aucune limitation HA ne doit apparaître quand v1_limitation=false");
});

// ---------------------------------------------------------------------------
// AI-5.8 — Pas de remediation affichée si le champ est vide
// ---------------------------------------------------------------------------

test("AI-5.8: 'Action recommandée' n'apparaît pas quand remediation est vide", () => {
  const response = makeResponse();
  // Effacer toutes les remédiations
  response.diagnostic_equipments[42].remediation = "";
  response.diagnostic_equipments[43].remediation = "";
  response.diagnostic_equipments[44].remediation = "";
  const html = scopeSummary.render(scopeSummary.createModel(response));
  assert.doesNotMatch(html, /Action recommandée/, "Libellé 'Action recommandée' ne doit pas apparaître si remediation vide");
});

// ---------------------------------------------------------------------------
// AI-5.9 — Badge statut par équipement depuis status_code (pas depuis label français)
// ---------------------------------------------------------------------------

test("AI-5.9: badge statut équipement déterminé depuis status_code canonique ('not_supported' → Non supporté)", () => {
  const html = scopeSummary.render(scopeSummary.createModel(makeResponse()));
  // eq 44 a status_code='not_supported' → doit afficher 'Non supporté' (pas 'Non publié' ni autre)
  assert.match(html, /Non supporté/, "Status code 'not_supported' doit afficher 'Non supporté'");
  // Guardrail rouge : 'not_supported' ne doit jamais être rouge
  assert.doesNotMatch(html, /label-danger[^>]*>Non supporté/, "'Non supporté' ne doit pas utiliser label-danger (rouge réservé infra)");
});

// ---------------------------------------------------------------------------
// AI-5.10 — Dégradation gracieuse : sans données diagnostic, la vue scope reste affichée
// ---------------------------------------------------------------------------

test("AI-5.10: sans données diagnostic, la vue scope-only s'affiche normalement sans erreur", () => {
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 2, include: 2, exclude: 0 } },
      pieces: [{ object_id: 1, object_name: "Cuisine", counts: { total: 2, include: 2, exclude: 0 } }],
      equipements: [
        { eq_id: 10, object_id: 1, effective_state: "include" },
      ],
    },
    // Pas de diagnostic_summary / diagnostic_rooms / diagnostic_equipments
  };
  const model = scopeSummary.createModel(response);
  assert.equal(model.has_contract, true);
  assert.equal(model.diagnostic_summary, null, "diagnostic_summary doit être null si absent du payload");
  const html = scopeSummary.render(model);
  assert.match(html, /Cuisine/, "La pièce doit apparaître");
  assert.doesNotMatch(html, /Statut global HA/, "Pas de section HA sans données diagnostic");
  assert.doesNotMatch(html, /Limitation Home Assistant/, "Pas de limitation HA sans données diagnostic");
  assert.doesNotMatch(html, /Action recommandée/, "Pas d'action recommandée sans données diagnostic");
});

// ---------------------------------------------------------------------------
// AI-5.11 — getAggregatedStatusLabel : mapping des 7 codes sans logique métier
// ---------------------------------------------------------------------------

test("AI-5.11: getAggregatedStatusLabel — tous les codes canoniques mappent vers les bons badges", () => {
  const fn = scopeSummary.getAggregatedStatusLabel;

  assert.match(fn("published"),           /label-success/);
  assert.match(fn("published"),           /Publié/);

  assert.match(fn("excluded"),            /background-color:#999/);
  assert.match(fn("excluded"),            /Exclu/);
  assert.doesNotMatch(fn("excluded"),     /label-danger/);

  assert.match(fn("ambiguous"),           /label-warning/);
  assert.match(fn("ambiguous"),           /Ambigu/);
  assert.doesNotMatch(fn("ambiguous"),    /label-danger/);

  assert.match(fn("not_supported"),       /background-color:#666/);
  assert.match(fn("not_supported"),       /Non supporté/);
  assert.doesNotMatch(fn("not_supported"), /label-danger/);

  assert.match(fn("infra_incident"),      /label-danger/);
  assert.match(fn("infra_incident"),      /Incident infrastructure/);

  assert.match(fn("partially_published"), /label-success/);
  assert.match(fn("partially_published"), /Publié/);
  assert.doesNotMatch(fn("partially_published"), /label-info/);

  assert.match(fn("empty"),              /Vide/);

  // Code inconnu → chaîne vide (pas de crash, pas de badge inventé)
  assert.equal(fn("unknown_code"), "");
  assert.equal(fn(""), "");
});

// ---------------------------------------------------------------------------
// AI-5.12 — Pièce avec object_id: null reçoit son diagnostic_summary backend
// ---------------------------------------------------------------------------

test("AI-5.12: pièce 'Aucun' (scope object_id:0, diag object_id:null) reçoit son badge diagnostic", () => {
  // Contrat terrain réel : le scope retourne object_id:0 pour "Aucun",
  // le diagnostic retourne object_id:null pour la même pièce.
  const response = {
    status: "ok",
    published_scope: {
      global: { counts: { total: 5, include: 2, exclude: 3 } },
      pieces: [
        { object_id: 0, object_name: "Aucun", counts: { total: 3, include: 1, exclude: 2 } },
        { object_id: 10, object_name: "Salon", counts: { total: 2, include: 1, exclude: 1 } },
      ],
      equipements: [
        { eq_id: 1, object_id: 0, effective_state: "exclude" },
        { eq_id: 2, object_id: 10, effective_state: "include" },
      ],
    },
    diagnostic_summary: {
      primary_aggregated_status: "not_supported",
      total_equipments: 5,
      counts_by_status: { published: 2, excluded: 3, ambiguous: 0, not_supported: 0, infra_incident: 0 },
    },
    diagnostic_rooms: [
      {
        object_id: null,
        summary: {
          primary_aggregated_status: "not_supported",
          total_equipments: 3,
          counts_by_status: { published: 0, excluded: 2, ambiguous: 0, not_supported: 1, infra_incident: 0 },
        },
      },
      {
        object_id: 10,
        summary: {
          primary_aggregated_status: "partially_published",
          total_equipments: 2,
          counts_by_status: { published: 1, excluded: 1, ambiguous: 0, not_supported: 0, infra_incident: 0 },
        },
      },
    ],
    diagnostic_equipments: {},
  };

  const model = scopeSummary.createModel(response);

  // La pièce "Aucun" (scope object_id:0 ↔ diag object_id:null) doit recevoir son diagnostic_summary
  assert.ok(model.pieces[0].diagnostic_summary, "La pièce Aucun doit avoir un diagnostic_summary malgré le décalage 0/null");
  assert.equal(model.pieces[0].diagnostic_summary.primary_aggregated_status, "not_supported");
  assert.equal(model.pieces[0].diagnostic_summary.counts_by_status.not_supported, 1);

  // La pièce Salon (object_id: 10) doit aussi recevoir le sien (non-régression)
  assert.ok(model.pieces[1].diagnostic_summary, "La pièce object_id:10 doit avoir un diagnostic_summary");
  assert.equal(model.pieces[1].diagnostic_summary.primary_aggregated_status, "partially_published");

  // Le HTML doit contenir le badge de la pièce "Aucun"
  const html = scopeSummary.render(model);
  assert.match(html, /Non supporté/, "Le badge 'Non supporté' doit apparaître pour la pièce Aucun");
  assert.match(html, /Publié/, "Le badge 'Partiellement publié' doit être absorbé en 'Publié' pour Salon");

  // Vérifier que le badge est bien dans la ligne synthèse de la pièce "Aucun"
  const summaryRows = html.match(/<tr class="j2ha-piece-summary"[^>]*>[\s\S]*?<\/tr>/g);
  assert.ok(summaryRows && summaryRows.length >= 2, "Au moins 2 lignes synthèse pièce");
  // La première pièce (Aucun) doit avoir le badge Non supporté
  assert.ok(summaryRows[0].includes("Non supporté"), "La ligne synthèse 'Aucun' doit contenir le badge 'Non supporté'");
  // Elle ne doit PAS utiliser le fallback "Exclue" quand le diagnostic est disponible
  assert.ok(!summaryRows[0].includes("Exclue"), "Le badge local 'Exclue' ne doit pas apparaître quand le diagnostic backend est fourni");
});
