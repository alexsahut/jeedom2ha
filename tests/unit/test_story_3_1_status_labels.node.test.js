/**
 * Story 3.1 — Tests JS de l'affichage des statuts et du rendu partiel.
 *
 * AI-3 guard — couche 2 (comportement réel).
 * Ces tests valident que getStatusLabel() retourne les bons résultats pour chaque statut
 * de la taxonomie Story 3.1, et que le rendu (partiel) est géré au call site.
 *
 * ACs couverts : AC 1, AC 2, AC 4 (couche comportement)
 *
 * Pattern : node:test natif (identique à Story 2.3 / 2.4).
 * Les fonctions pures sont recopiées depuis desktop/js/jeedom2ha.js (sans dépendances jQuery).
 */

const test = require("node:test");
const assert = require("node:assert/strict");

// ============================================================
// Fonctions sous test — copies exactes de desktop/js/jeedom2ha.js
// getStatusLabel — Story 3.1 : taxonomie principale à 5 statuts
// ============================================================

var getStatusLabel = function(status) {
  if (status === 'Publié') return '<span class="label label-success">' + status + '</span>';
  if (status === 'Exclu') return '<span class="label label-default">' + status + '</span>';
  if (status === 'Ambigu') return '<span class="label label-warning">' + status + '</span>';
  if (status === 'Non supporté') return '<span class="label label-default" style="background-color:#666!important;">' + status + '</span>';
  if (status === 'Incident infrastructure') return '<span class="label label-danger">' + status + '</span>';
  return '<span class="label label-default">' + status + '</span>';
};

// Call site du renderer — logique de suffixe partiel (depuis renderTable/buildDetailRow)
function getPartialSuffix(eq) {
  if (eq.status === 'Publié' && eq.unmatched_commands && eq.unmatched_commands.length > 0) {
    return ' <span class="text-muted" style="font-size:0.85em">(partiel)</span>';
  }
  return '';
}

// Rendu complet d'une cellule statut (call site)
function renderStatusCell(eq) {
  return getStatusLabel(eq.status) + getPartialSuffix(eq);
}

// ============================================================
// 6.2 — getStatusLabel("Publié") → label-success + texte "Publié"
// ============================================================

test("story-3.1: getStatusLabel('Publié') → contient label-success et le texte Publié", () => {
  const html = getStatusLabel("Publié");
  assert.match(html, /label-success/);
  assert.ok(html.includes("Publié"), `Doit contenir le texte 'Publié'. Got: ${html}`);
});

// ============================================================
// 6.3 — getStatusLabel("Exclu") → label-default + texte "Exclu"
// ============================================================

test("story-3.1: getStatusLabel('Exclu') → contient label-default et le texte Exclu", () => {
  const html = getStatusLabel("Exclu");
  assert.match(html, /label-default/);
  assert.ok(html.includes("Exclu"), `Doit contenir le texte 'Exclu'. Got: ${html}`);
});

// ============================================================
// 6.4 — getStatusLabel("Ambigu") → label-warning + texte "Ambigu"
// ============================================================

test("story-3.1: getStatusLabel('Ambigu') → contient label-warning et le texte Ambigu", () => {
  const html = getStatusLabel("Ambigu");
  assert.match(html, /label-warning/);
  assert.ok(html.includes("Ambigu"), `Doit contenir le texte 'Ambigu'. Got: ${html}`);
});

// ============================================================
// 6.5 — getStatusLabel("Non supporté") → label-default, pas label-danger
// ============================================================

test("story-3.1: getStatusLabel('Non supporté') → contient label-default, pas label-danger, texte Non supporté", () => {
  const html = getStatusLabel("Non supporté");
  assert.match(html, /label-default/);
  assert.doesNotMatch(html, /label-danger/);
  assert.ok(html.includes("Non supporté"), `Doit contenir le texte 'Non supporté'. Got: ${html}`);
});

// ============================================================
// 6.6 — getStatusLabel("Incident infrastructure") → label-danger
// ============================================================

test("story-3.1: getStatusLabel('Incident infrastructure') → contient label-danger et le texte Incident infrastructure", () => {
  const html = getStatusLabel("Incident infrastructure");
  assert.match(html, /label-danger/);
  assert.ok(html.includes("Incident infrastructure"), `Doit contenir le texte 'Incident infrastructure'. Got: ${html}`);
});

// ============================================================
// 6.7 — Pureté de getStatusLabel : ne contient pas "(partiel)"
// ============================================================

test("story-3.1: getStatusLabel est pure — getStatusLabel('Publié') ne contient pas 'partiel'", () => {
  const html = getStatusLabel("Publié");
  assert.doesNotMatch(html, /partiel/i, `getStatusLabel ne doit pas gérer le suffixe partiel. Got: ${html}`);
});

// ============================================================
// 6.8 — Call site : status="Publié", unmatched_commands=[] → pas de "(partiel)"
// ============================================================

test("story-3.1: renderStatusCell — Publié sans unmatched_commands → pas de (partiel)", () => {
  const eq = { status: "Publié", unmatched_commands: [] };
  const html = renderStatusCell(eq);
  assert.doesNotMatch(html, /partiel/i, `Ne doit pas contenir '(partiel)' quand unmatched_commands est vide. Got: ${html}`);
  assert.match(html, /Publié/);
});

// ============================================================
// 6.9 — Call site : status="Publié", unmatched_commands=[{cmd_id: 1}] → contient "(partiel)"
// ============================================================

test("story-3.1: renderStatusCell — Publié avec unmatched_commands → contient (partiel)", () => {
  const eq = { status: "Publié", unmatched_commands: [{ cmd_id: 1 }] };
  const html = renderStatusCell(eq);
  assert.ok(html.includes("(partiel)"), `Doit contenir '(partiel)'. Got: ${html}`);
  assert.match(html, /Publié/);
  assert.match(html, /text-muted/);
});

// ============================================================
// 6.10 — Négatif : "Partiellement publié" tombe dans le fallback neutre
// Ne doit pas produire label-success, label-warning, label-danger
// ============================================================

test("story-3.1: getStatusLabel('Partiellement publié') → fallback neutre (pas de code nominal)", () => {
  const html = getStatusLabel("Partiellement publié");
  // Tombe dans le default fallback
  assert.match(html, /label-default/);
  // N'est PAS un code intentionnel
  assert.doesNotMatch(html, /label-success/);
  assert.doesNotMatch(html, /label-warning/);
  assert.doesNotMatch(html, /label-danger/);
  assert.doesNotMatch(html, /label-info/);
});

// ============================================================
// 6.11 — Négatif : "Non publié" tombe aussi dans le fallback
// ============================================================

test("story-3.1: getStatusLabel('Non publié') → fallback neutre (pas de code nominal)", () => {
  const html = getStatusLabel("Non publié");
  assert.match(html, /label-default/);
  assert.doesNotMatch(html, /label-success/);
  assert.doesNotMatch(html, /label-warning/);
  assert.doesNotMatch(html, /label-danger/);
  assert.doesNotMatch(html, /label-info/);
});

// ============================================================
// Bonus — Règle visuelle héritée de Story 2.4 :
// rouge (label-danger) réservé à l'infrastructure (Story 3.1)
// ============================================================

test("story-3.1: seul 'Incident infrastructure' utilise label-danger (rouge réservé infra)", () => {
  const nonInfraStatuses = ["Publié", "Exclu", "Ambigu", "Non supporté"];
  for (const s of nonInfraStatuses) {
    const html = getStatusLabel(s);
    assert.doesNotMatch(html, /label-danger/, `${s} ne doit pas utiliser label-danger. Got: ${html}`);
  }
  const infraHtml = getStatusLabel("Incident infrastructure");
  assert.match(infraHtml, /label-danger/);
});

// ============================================================
// Bonus — unmatched_commands undefined → pas de crash, pas de (partiel)
// ============================================================

test("story-3.1: renderStatusCell — unmatched_commands absent → pas de (partiel), pas de crash", () => {
  const eq = { status: "Publié" }; // pas de champ unmatched_commands
  const html = renderStatusCell(eq);
  assert.doesNotMatch(html, /partiel/i);
});

test("story-3.1: renderStatusCell — status non-Publié avec unmatched_commands → pas de (partiel)", () => {
  // Le suffixe partiel ne s'applique QUE pour status === 'Publié'
  const eq = { status: "Non supporté", unmatched_commands: [{ cmd_id: 1 }] };
  const html = renderStatusCell(eq);
  assert.doesNotMatch(html, /partiel/i);
});
