// Front v2 — Lot 0 (socle) : module vide exposant `window.Jeedom2haTypePanel`.
// Panneau de correction du type avec aperçu (rempli par le Lot 5).
// Module pur : chargeable sous node (module.exports) comme dans la page (globale).
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
    return;
  }
  root.Jeedom2haTypePanel = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  return {
    version: 1,
  };
}));
