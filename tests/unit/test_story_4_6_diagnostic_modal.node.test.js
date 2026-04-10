/**
 * Story 4.6 — Diagnostic modal in-scope et ouverture ciblée depuis la home.
 *
 * Invariants testés :
 * - I14 : diagnostic filtré in-scope (perimetre === 'inclus' uniquement)
 * - I15 : Confiance visible uniquement dans le diagnostic (home inchangée)
 * - I17 : pas d'interprétation frontend du contrat métier
 * - Colonnes exactes et ordonnées : Piece | Nom | Ecart | Statut | Confiance | Raison
 * - Aucun équipement exclu dans la liste diagnostic standard
 * - Ciblage AC 6 : findTargetEquipmentIndex trouvé => index >= 0
 * - Fallback AC 7 : target absente => -1 sans erreur
 * - Ecart badge AC 2 : lecture stricte du champ ecart backend
 */

const test = require('node:test');
const assert = require('node:assert/strict');

const helpers = require('../../desktop/js/jeedom2ha_diagnostic_helpers.js');

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeEquipments() {
  return [
    { eq_id: 10, name: 'Lampe TV',          object_name: 'Salon',   perimetre: 'inclus',            ecart: false },
    { eq_id: 11, name: 'Volet baie',         object_name: 'Salon',   perimetre: 'inclus',            ecart: true  },
    { eq_id: 12, name: 'Radiateur déco',     object_name: 'Salon',   perimetre: 'exclu_par_piece',   ecart: false },
    { eq_id: 13, name: 'Sonde terrasse',     object_name: 'Ext',     perimetre: 'inclus',            ecart: false },
    { eq_id: 14, name: 'Prise exclue',       object_name: 'Cuisine', perimetre: 'exclu_sur_equipement', ecart: false },
    { eq_id: 15, name: 'Plugin exclu',       object_name: 'Cuisine', perimetre: 'exclu_par_plugin',  ecart: false },
  ];
}

// ---------------------------------------------------------------------------
// AC 5 — filterInScopeEquipments
// ---------------------------------------------------------------------------

test('4.6 / AC5 — filterInScopeEquipments retourne uniquement les inclus', () => {
  const eqs = makeEquipments();
  const result = helpers.filterInScopeEquipments(eqs);

  assert.equal(result.length, 3);
  for (const eq of result) {
    assert.equal(eq.perimetre, 'inclus');
  }
});

test('4.6 / AC5 — filterInScopeEquipments exclut toutes les variantes exclu_*', () => {
  const eqs = makeEquipments();
  const result = helpers.filterInScopeEquipments(eqs);
  const ids = result.map(e => e.eq_id);

  assert.ok(!ids.includes(12), 'exclu_par_piece doit être absent');
  assert.ok(!ids.includes(14), 'exclu_sur_equipement doit être absent');
  assert.ok(!ids.includes(15), 'exclu_par_plugin doit être absent');
});

test('4.6 / AC5 — filterInScopeEquipments sur liste vide', () => {
  assert.deepEqual(helpers.filterInScopeEquipments([]), []);
});

test('4.6 / AC5 — filterInScopeEquipments sur entrée non-tableau', () => {
  assert.deepEqual(helpers.filterInScopeEquipments(null), []);
  assert.deepEqual(helpers.filterInScopeEquipments(undefined), []);
  assert.deepEqual(helpers.filterInScopeEquipments('string'), []);
});

// ---------------------------------------------------------------------------
// AC 2 — getDiagnosticColumns : ordre et contenu exact
// ---------------------------------------------------------------------------

test('4.6 / AC2 — getDiagnosticColumns retourne 6 colonnes exactes et ordonnées', () => {
  const cols = helpers.getDiagnosticColumns();
  assert.deepEqual(cols, ['Piece', 'Nom', 'Ecart', 'Statut', 'Confiance', 'Raison']);
});

test('4.6 / AC2 — getDiagnosticColumns : Confiance absente de la home (invariant structure)', () => {
  const cols = helpers.getDiagnosticColumns();
  assert.ok(cols.includes('Confiance'), 'Confiance doit être dans le diagnostic');
  // Raison (lisible) doit aussi être présente, pas reason_code
  assert.ok(cols.includes('Raison'), 'Raison doit être dans le diagnostic');
  assert.ok(!cols.includes('reason_code'), 'reason_code interne ne doit pas apparaître dans les colonnes');
});

test('4.6 / AC2 — getDiagnosticColumns : Ecart est la 3e colonne (avant Statut)', () => {
  const cols = helpers.getDiagnosticColumns();
  const idxEcart = cols.indexOf('Ecart');
  const idxStatut = cols.indexOf('Statut');
  assert.ok(idxEcart !== -1, 'Ecart doit exister');
  assert.ok(idxStatut !== -1, 'Statut doit exister');
  assert.ok(idxEcart < idxStatut, 'Ecart doit précéder Statut');
});

test('4.6 / AC2 — getDiagnosticColumns : pas de colonnes home (Perimetre / Total / Exclus / Inclus / Publies / Ecarts)', () => {
  const cols = helpers.getDiagnosticColumns();
  const homeCols = ['Perimetre', 'Total', 'Exclus', 'Inclus', 'Publies', 'Ecarts'];
  for (const c of homeCols) {
    assert.ok(!cols.includes(c), `${c} ne doit pas apparaître dans le diagnostic`);
  }
});

// ---------------------------------------------------------------------------
// AC 2 — getEcartBadgeHtml : lecture stricte du champ ecart backend
// ---------------------------------------------------------------------------

test('4.6 / AC2 — getEcartBadgeHtml(true) = badge warning Ecart', () => {
  const html = helpers.getEcartBadgeHtml(true);
  assert.match(html, /label-warning/);
  assert.match(html, /Ecart/);
});

test('4.6 / AC2 — getEcartBadgeHtml(false) = badge success Aligne', () => {
  const html = helpers.getEcartBadgeHtml(false);
  assert.match(html, /label-success/);
  assert.match(html, /Aligne/);
});

test('4.6 / AC2 — getEcartBadgeHtml(null) = badge neutre', () => {
  const html = helpers.getEcartBadgeHtml(null);
  assert.match(html, /label-default/);
  assert.doesNotMatch(html, /label-warning/);
  assert.doesNotMatch(html, /label-success/);
});

test('4.6 / AC2 — getEcartBadgeHtml : aucun recalcul — lecture stricte du boolean backend', () => {
  // Vérifier que seul boolean true/false est interprété, rien d'autre
  assert.match(helpers.getEcartBadgeHtml(true), /label-warning/);
  assert.match(helpers.getEcartBadgeHtml(false), /label-success/);
  // Valeurs edge cases → badge neutre uniquement
  assert.match(helpers.getEcartBadgeHtml(undefined), /label-default/);
  assert.match(helpers.getEcartBadgeHtml('true'), /label-default/);
  assert.match(helpers.getEcartBadgeHtml(1), /label-default/);
});

// ---------------------------------------------------------------------------
// AC 6 / AC 7 — findTargetEquipmentIndex
// ---------------------------------------------------------------------------

test('4.6 / AC6 — findTargetEquipmentIndex : cible trouvée → index >= 0', () => {
  const eqs = makeEquipments();
  const inScope = helpers.filterInScopeEquipments(eqs);
  // eq_id 11 est in-scope (Volet baie, ecart: true)
  const idx = helpers.findTargetEquipmentIndex(inScope, 11);
  assert.ok(idx >= 0, 'La cible in-scope doit être trouvée');
  assert.equal(inScope[idx].eq_id, 11);
});

test('4.6 / AC7 — findTargetEquipmentIndex : cible absente → -1, pas d\'erreur', () => {
  const eqs = makeEquipments();
  const inScope = helpers.filterInScopeEquipments(eqs);
  // eq_id 12 est exclu, donc absent de inScope
  const idx = helpers.findTargetEquipmentIndex(inScope, 12);
  assert.equal(idx, -1, 'Un équipement exclu ne doit pas être trouvé dans inScope');
});

test('4.6 / AC7 — findTargetEquipmentIndex : eq_id inexistant → -1', () => {
  const eqs = makeEquipments();
  const inScope = helpers.filterInScopeEquipments(eqs);
  const idx = helpers.findTargetEquipmentIndex(inScope, 9999);
  assert.equal(idx, -1);
});

test('4.6 / AC7 — findTargetEquipmentIndex : entrées invalides → -1 sans erreur', () => {
  assert.equal(helpers.findTargetEquipmentIndex(null, 10), -1);
  assert.equal(helpers.findTargetEquipmentIndex([], 10), -1);
  assert.equal(helpers.findTargetEquipmentIndex([{ eq_id: 10 }], null), -1);
});

test('4.6 / AC7 — findTargetEquipmentIndex : accepte eq_id en string ou number', () => {
  const list = [{ eq_id: 42 }, { eq_id: 43 }];
  assert.equal(helpers.findTargetEquipmentIndex(list, '42'), 0);
  assert.equal(helpers.findTargetEquipmentIndex(list, 43), 1);
});

// ---------------------------------------------------------------------------
// Invariant — les exclus ne peuvent jamais apparaître dans la liste in-scope
// ---------------------------------------------------------------------------

test('4.6 — invariant : un équipement exclu par pièce reste absent du diagnostic standard', () => {
  const eqs = [
    { eq_id: 1, perimetre: 'inclus' },
    { eq_id: 2, perimetre: 'exclu_par_piece' },
  ];
  const inScope = helpers.filterInScopeEquipments(eqs);
  const ids = inScope.map(e => e.eq_id);
  assert.ok(ids.includes(1));
  assert.ok(!ids.includes(2));
});

test('4.6 — invariant : le diagnostic standard ne doit pas recréer les colonnes de la home', () => {
  // Les colonnes home ne doivent PAS être dans le diagnostic
  const diagCols = helpers.getDiagnosticColumns().join(',');
  assert.ok(!diagCols.includes('Total'), 'Total est home-only');
  assert.ok(!diagCols.includes('Inclus'), 'Inclus est home-only');
  assert.ok(!diagCols.includes('Exclus'), 'Exclus est home-only');
  assert.ok(!diagCols.includes('Publies'), 'Publies est home-only');
});
