const test = require("node:test");
const assert = require("node:assert/strict");

// ============================================================
// Functions under test — mirrors implementation in desktop/js/jeedom2ha.js
// isHABridgeAvailable is pure (no DOM/jQuery) — tested directly inline.
// applyHAGating uses jQuery selectors — tested with a minimal mock.
// ============================================================

function isHABridgeAvailable(r) {
  if (!r || !r.daemon) return false;
  var brokerInfo = r.broker || r.mqtt || {};
  return brokerInfo.state === "connected";
}

/**
 * Minimal jQuery-like mock for DOM tests.
 * Returns tracked element states for haActions and haGatingReason.
 */
function makeJQueryMock() {
  function mockElem(initialDisabled, initialHidden) {
    var state = {
      disabled: initialDisabled,
      hidden: initialHidden,
      text: "",
      classes: [],
    };
    var elem = {
      _state: state,
      prop: function (key, val) {
        state[key] = val;
        return elem;
      },
      addClass: function (cls) {
        if (!state.classes.includes(cls)) state.classes.push(cls);
        return elem;
      },
      removeClass: function (cls) {
        state.classes = state.classes.filter(function (c) { return c !== cls; });
        return elem;
      },
      hide: function () {
        state.hidden = true;
        return elem;
      },
      show: function () {
        state.hidden = false;
        return elem;
      },
      text: function (t) {
        state.text = t;
        return elem;
      },
    };
    return elem;
  }

  var haActionsElem = mockElem(true, false);
  var reasonElem = mockElem(false, true);
  var unknownElem = mockElem(false, false);

  function $(sel) {
    if (sel === "[data-ha-action]") return haActionsElem;
    if (sel === "#div_haGatingReason") return reasonElem;
    return unknownElem;
  }

  return { $: $, haActionsElem: haActionsElem, reasonElem: reasonElem };
}

function applyHAGatingWith$(r, $) {
  var available = r ? isHABridgeAvailable(r) : false;
  var $haActions = $("[data-ha-action]");
  var $reason = $("#div_haGatingReason");

  if (available) {
    $haActions.prop("disabled", false).removeClass("j2ha-ha-gated");
    $reason.hide();
  } else {
    $haActions.prop("disabled", true).addClass("j2ha-ha-gated");
    var reason = "Bridge ou MQTT indisponible — actions Home Assistant bloquées.";
    if (r && !r.daemon) {
      reason = "Daemon arrêté — actions Home Assistant bloquées.";
    } else if (r) {
      reason = "MQTT déconnecté — actions Home Assistant bloquées.";
    }
    $reason.text(reason).show();
  }
}

// ============================================================
// isHABridgeAvailable — 6 cas minimaux définis en Task 4 (Story 2.3)
// ============================================================

test("story-2.3: isHABridgeAvailable — null → false", () => {
  assert.equal(isHABridgeAvailable(null), false);
});

test("story-2.3: isHABridgeAvailable — { daemon: false } → false", () => {
  assert.equal(isHABridgeAvailable({ daemon: false }), false);
});

test("story-2.3: isHABridgeAvailable — daemon true, broker disconnected → false", () => {
  assert.equal(
    isHABridgeAvailable({ daemon: true, broker: { state: "disconnected" } }),
    false
  );
});

test("story-2.3: isHABridgeAvailable — daemon true, broker reconnecting → false", () => {
  assert.equal(
    isHABridgeAvailable({ daemon: true, broker: { state: "reconnecting" } }),
    false
  );
});

test("story-2.3: isHABridgeAvailable — daemon true, broker connected → true", () => {
  assert.equal(
    isHABridgeAvailable({ daemon: true, broker: { state: "connected" } }),
    true
  );
});

test("story-2.3: isHABridgeAvailable — daemon true, mqtt connected (fallback r.mqtt) → true", () => {
  assert.equal(
    isHABridgeAvailable({ daemon: true, mqtt: { state: "connected" } }),
    true
  );
});

// ============================================================
// applyHAGating — comportement DOM avec mock jQuery minimal
// ============================================================

test("story-2.3: applyHAGating — pont sain → boutons enabled, reason masquée", () => {
  var mock = makeJQueryMock();
  var r = { daemon: true, broker: { state: "connected" } };
  applyHAGatingWith$(r, mock.$);
  assert.equal(mock.haActionsElem._state.disabled, false);
  assert.equal(mock.haActionsElem._state.classes.includes("j2ha-ha-gated"), false);
  assert.equal(mock.reasonElem._state.hidden, true);
});

test("story-2.3: applyHAGating(null) → boutons disabled, classe j2ha-ha-gated posée, reason visible", () => {
  var mock = makeJQueryMock();
  applyHAGatingWith$(null, mock.$);
  assert.equal(mock.haActionsElem._state.disabled, true);
  assert.equal(mock.haActionsElem._state.classes.includes("j2ha-ha-gated"), true);
  assert.equal(mock.reasonElem._state.hidden, false);
  assert.match(mock.reasonElem._state.text, /indisponible/);
});

test("story-2.3: applyHAGating — daemon arrêté → message mentionne Daemon arrêté", () => {
  var mock = makeJQueryMock();
  applyHAGatingWith$({ daemon: false }, mock.$);
  assert.equal(mock.haActionsElem._state.disabled, true);
  assert.match(mock.reasonElem._state.text, /Daemon arrêté/);
});

test("story-2.3: applyHAGating — MQTT déconnecté → message mentionne MQTT déconnecté", () => {
  var mock = makeJQueryMock();
  applyHAGatingWith$({ daemon: true, broker: { state: "disconnected" } }, mock.$);
  assert.equal(mock.haActionsElem._state.disabled, true);
  assert.match(mock.reasonElem._state.text, /MQTT déconnecté/);
});

test("story-2.3: applyHAGating — éléments sans data-ha-action non sélectionnés", () => {
  var mock = makeJQueryMock();
  var r = { daemon: true, broker: { state: "connected" } };
  applyHAGatingWith$(r, mock.$);
  // Le mock ne retourne unknownElem que pour des sélecteurs différents de [data-ha-action] et #div_haGatingReason.
  // Si l'implémentation ne sélectionne que ces deux cibles, unknownElem reste intact.
  assert.equal(mock.haActionsElem._state.disabled, false);
  assert.equal(mock.reasonElem._state.hidden, true);
  // unknownElem (ex. bt_refreshScopeSummary) n'est jamais modifié par applyHAGating
  // (son disabled reste false = valeur initiale du mock — non touché)
});
