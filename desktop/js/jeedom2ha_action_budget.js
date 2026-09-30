(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
    return;
  }
  root.Jeedom2haActionBudget = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  // Story 19.6 (AC1, AC2) — mêmes valeurs que core/php/jeedom2ha_action_budget.php,
  // croisées avec tests/fixtures/action_budget_constants.json par les deux suites de test.
  var R = 60;
  var RESERVE_S = 5;
  var STATUS_TIMEOUT_S = 3;
  var CLICK_READ_DEADLINE_S = 10;
  var REALIGN_TIMEOUT_S = 3;

  // AC2 — pire des deux chemins de la requête PHP (secondes) :
  // chemin qui aboutit  : statut + lecture au clic + R + réalignement
  // chemin en échec     : statut + lecture au clic + R + second statut de diagnostic
  function worstPathMs() {
    var success = STATUS_TIMEOUT_S + CLICK_READ_DEADLINE_S + R + REALIGN_TIMEOUT_S;
    var failure = STATUS_TIMEOUT_S + CLICK_READ_DEADLINE_S + R + STATUS_TIMEOUT_S;
    return Math.max(success, failure) * 1000;
  }

  // Délai fixe du client (desktop/js/jeedom2ha.js), au-dessus du pire chemin, sous
  // le `Timeout 300` d'Apache.
  var CLIENT_TIMEOUT_MS = 90000;

  return {
    R: R,
    RESERVE_S: RESERVE_S,
    STATUS_TIMEOUT_S: STATUS_TIMEOUT_S,
    CLICK_READ_DEADLINE_S: CLICK_READ_DEADLINE_S,
    REALIGN_TIMEOUT_S: REALIGN_TIMEOUT_S,
    worstPathMs: worstPathMs,
    CLIENT_TIMEOUT_MS: CLIENT_TIMEOUT_MS,
  };
}));
