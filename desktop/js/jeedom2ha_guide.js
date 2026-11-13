// Front v2 — Lot 0 (socle) : module vide exposant `window.Jeedom2haGuide`.
// Démarrage guidé et explication de la barre d'état (rempli par le Lot 1).
// Module pur : chargeable sous node (module.exports) comme dans la page (globale).
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
    return;
  }
  root.Jeedom2haGuide = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  return {
    version: 1,
  };
}));
