/* Story 4.6+ — Helpers purs du diagnostic modal (in-scope, colonnes, ciblage, libellés visibles).
 * Séparé pour testabilité. Aucune logique métier : passthrough strict du contrat backend
 * avec fallback legacy borné quand les champs enrichis ne sont pas disponibles.
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

  // Story 4.2 — La raison visible doit d'abord refléter cause_label.
  // Fallback legacy borné sur le mapping JS local uniquement si cause_label est absent.
  function getDiagnosticReasonLabel(eq, legacyReasonLabels) {
    if (eq && typeof eq.cause_label === 'string' && eq.cause_label !== '') {
      return eq.cause_label;
    }
    if (
      eq
      && legacyReasonLabels
      && typeof eq.reason_code === 'string'
      && typeof legacyReasonLabels[eq.reason_code] === 'string'
      && legacyReasonLabels[eq.reason_code] !== ''
    ) {
      return legacyReasonLabels[eq.reason_code];
    }
    return '';
  }

  // Story 4.2 — cause_action prime sur remediation et ne doit pas déclencher
  // de CTA de configuration générique qui contredirait la lecture visible.
  function resolveDiagnosticAction(eq) {
    if (eq && typeof eq.cause_action === 'string' && eq.cause_action !== '') {
      return {
        text: eq.cause_action,
        source: 'cause_action',
        showConfigLink: false,
      };
    }
    if (eq && typeof eq.remediation === 'string' && eq.remediation !== '') {
      return {
        text: eq.remediation,
        source: 'remediation',
        showConfigLink: true,
      };
    }
    return {
      text: '',
      source: 'none',
      showConfigLink: false,
    };
  }

  return {
    filterInScopeEquipments: filterInScopeEquipments,
    getDiagnosticColumns: getDiagnosticColumns,
    getEcartBadgeHtml: getEcartBadgeHtml,
    findTargetEquipmentIndex: findTargetEquipmentIndex,
    getDiagnosticReasonLabel: getDiagnosticReasonLabel,
    resolveDiagnosticAction: resolveDiagnosticAction,
  };
}));
