// Front v2 — Lot 0 (socle) : module vide exposant `window.Jeedom2haLexique`.
// Lexique : traduction en mots simples des termes et causes affichés (rempli par le Lot 2).
// Module pur : chargeable sous node (module.exports) comme dans la page (globale).
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
    return;
  }
  root.Jeedom2haLexique = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  return {
    version: 1,
  };
}));
