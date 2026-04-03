/* Story 4.6 — Helpers purs du diagnostic modal (in-scope, colonnes, ciblage).
 * Séparé pour testabilité. Aucune logique métier : passthrough strict du contrat backend.
 * Ce module ne contient AUCUN calcul ou recombination des valeurs backend.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
    return;
  }
  root.Jeedom2haDiagnosticHelpers = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  // Story 4.6 — AC 5 : filtre in-scope strict.
  // Seuls les équipements avec perimetre === 'inclus' apparaissent dans le diagnostic standard.
  function filterInScopeEquipments(equipments) {
    if (!Array.isArray(equipments)) {
      return [];
    }
    return equipments.filter(function (eq) {
      return eq && (eq.perimetre || '') === 'inclus';
    });
  }

  // Story 4.6 — AC 2 : colonnes exactes et ordonnées du diagnostic.
  var DIAGNOSTIC_COLUMNS = ['Piece', 'Nom', 'Ecart', 'Statut', 'Confiance', 'Raison'];

  function getDiagnosticColumns() {
    return DIAGNOSTIC_COLUMNS.slice();
  }

  // Story 4.6 — AC 2 : badge Écart dans le diagnostic (lecture stricte backend).
  // ecart === true  → badge warning
  // ecart === false → badge success
  // autre           → badge neutre
  function getEcartBadgeHtml(ecart) {
    if (ecart === true) {
      return '<span class="label label-warning">Ecart</span>';
    }
    if (ecart === false) {
      return '<span class="label label-success">Aligne</span>';
    }
    return '<span class="label label-default">&mdash;</span>';
  }

  // Story 4.6 — AC 6 / AC 7 : ciblage d'un équipement dans la liste in-scope.
  // Retourne l'index dans inScopeEquipments (tableau ordonné) ou -1 si absent.
  // Fallback propre AC 7 : -1 sans erreur JS.
  function findTargetEquipmentIndex(inScopeEquipments, targetEqId) {
    if (!Array.isArray(inScopeEquipments) || targetEqId == null) {
      return -1;
    }
    var id = String(targetEqId);
    for (var i = 0; i < inScopeEquipments.length; i++) {
      var eq = inScopeEquipments[i];
      if (eq && String(eq.eq_id != null ? eq.eq_id : '') === id) {
        return i;
      }
    }
    return -1;
  }

  return {
    filterInScopeEquipments: filterInScopeEquipments,
    getDiagnosticColumns: getDiagnosticColumns,
    getEcartBadgeHtml: getEcartBadgeHtml,
    findTargetEquipmentIndex: findTargetEquipmentIndex,
  };
}));
