/**
 * Story 2.4 — Tests de séparation visuelle stable entre signal d'infrastructure et raison métier.
 *
 * ACs couverts :
 *   AC1 — incident infra séparé de la raison métier (séparation visuelle bandeau / équipement)
 *   AC2 — aucun code visuel infra (rouge / label-danger) pour un problème de configuration
 *   AC3 — qualification du type de blocage en première lecture (labels lisibles)
 *
 * Stratégie : dupliquer les fonctions pures testables depuis desktop/js/jeedom2ha.js
 * (même pattern que test_ha_gating.node.test.js).
 */

const test = require("node:test");
const assert = require("node:assert/strict");

// ============================================================
// Fonctions sous test — copies exactes de desktop/js/jeedom2ha.js
// Ces fonctions sont définies ici pour rester testables en Node.js (sans jQuery).
// ============================================================

// AC2 : getStatusLabel — codes couleur des statuts d'équipement (Story 3.1 : taxonomie à 5 statuts)
function getStatusLabel(status) {
  if (status === "Publié")
    return '<span class="label label-success">' + status + "</span>";
  if (status === "Exclu")
    return '<span class="label label-default">' + status + "</span>";
  if (status === "Ambigu")
    return '<span class="label label-warning">' + status + "</span>";
  if (status === "Non supporté")
    return '<span class="label label-default" style="background-color:#666!important;">' + status + "</span>";
  if (status === "Incident infrastructure")
    return '<span class="label label-danger">' + status + "</span>";
  return '<span class="label label-default">' + status + "</span>";
}

// AC3 : reasonLabels — copie du mapping corrigé (Story 2.4 — Task 2.2)
var reasonLabels = {
  // Codes de publication (état publié partiel)
  sure: "Mapping identifié avec certitude (partiel)",
  probable: "Mapping probable détecté",
  // Couverture / scope
  ambiguous_skipped: "Ambiguïté détectée (plusieurs types possibles)",
  no_mapping: "Aucun mapping compatible trouvé",
  no_supported_generic_type: "Type générique non supporté",
  no_generic_type_configured: "Types génériques non configurés sur les commandes",
  probable_skipped: 'Confiance probable — politique de publication "sûr uniquement"',
  // Configuration (décision utilisateur ou état Jeedom)
  no_commands: "Équipement sans commandes exploitables",
  disabled_eqlogic: "Équipement désactivé dans Jeedom",
  disabled: "Équipement désactivé dans Jeedom",
  excluded_eqlogic: "Exclu manuellement de la publication",
  excluded_by_user: "Exclu manuellement par l'utilisateur",
  excluded_plugin: "Plugin source exclu de la publication",
  excluded_object: "Pièce exclue de la publication",
  low_confidence: "Confiance trop faible pour publication",
  // Infrastructure — réservé au bandeau global et au résultat de publication
  discovery_publish_failed: "Échec de publication MQTT (infrastructure)",
  local_availability_publish_failed:
    "Échec de publication de la disponibilité (infrastructure)",
};

// Code couleur du résultat de publication (depuis buildDetailRow)
function getPubResultLabel(pubResult) {
  if (pubResult === "success")
    return '<span class="label label-success">Succès</span>';
  if (pubResult === "failed")
    return '<span class="label label-danger">Échec</span>';
  return '<span class="label label-default">Non tenté</span>';
}

// ============================================================
// AC2 — getStatusLabel : rouge (label-danger) réservé à l'infrastructure
// Les raisons métier (config, couverture, scope) n'utilisent PAS label-danger
// ============================================================

test("story-2.4: getStatusLabel — 'Non publié' (statut legacy) tombe en label-default (non rouge)", () => {
  // Story 3.1 : 'Non publié' n'est plus un statut nominal — tombe dans le fallback label-default.
  // L'essentiel : pas de label-danger (rouge).
  const html = getStatusLabel("Non publié");
  assert.match(html, /label-default/);
  assert.doesNotMatch(html, /label-danger/);
});

test("story-2.4: getStatusLabel — 'Exclu' utilise label-default (gris, non rouge)", () => {
  const html = getStatusLabel("Exclu");
  assert.match(html, /label-default/);
  assert.doesNotMatch(html, /label-danger/);
});

test("story-2.4: getStatusLabel — 'Partiellement publié' (statut legacy) tombe en label-default (non rouge)", () => {
  // Story 3.1 : 'Partiellement publié' n'est plus un statut nominal — tombe dans le fallback label-default.
  // L'essentiel : pas de label-danger (rouge).
  const html = getStatusLabel("Partiellement publié");
  assert.match(html, /label-default/);
  assert.doesNotMatch(html, /label-danger/);
});

test("story-2.4: getStatusLabel — 'Publié' utilise label-success (vert)", () => {
  const html = getStatusLabel("Publié");
  assert.match(html, /label-success/);
  assert.doesNotMatch(html, /label-danger/);
});

test("story-2.4: getStatusLabel — statut inconnu utilise label-default (non rouge)", () => {
  const html = getStatusLabel("état_inconnu_quelconque");
  assert.match(html, /label-default/);
  assert.doesNotMatch(html, /label-danger/);
});

// ============================================================
// AC2 — getPubResultLabel : label-danger uniquement pour publication_failed (infra)
// ============================================================

test("story-2.4: getPubResultLabel — 'failed' (infra) utilise label-danger (rouge)", () => {
  const html = getPubResultLabel("failed");
  assert.match(html, /label-danger/);
});

test("story-2.4: getPubResultLabel — 'success' utilise label-success, non rouge", () => {
  const html = getPubResultLabel("success");
  assert.match(html, /label-success/);
  assert.doesNotMatch(html, /label-danger/);
});

test("story-2.4: getPubResultLabel — 'not_attempted' utilise label-default (non rouge)", () => {
  const html = getPubResultLabel("not_attempted");
  assert.match(html, /label-default/);
  assert.doesNotMatch(html, /label-danger/);
});

// ============================================================
// AC3 — reasonLabels couvre les codes infrastructure clairement distincts
// ============================================================

test("story-2.4: reasonLabels — discovery_publish_failed a un label lisible mentionnant l'infra", () => {
  const label = reasonLabels["discovery_publish_failed"];
  assert.ok(label, "discovery_publish_failed doit avoir un label non vide");
  assert.notEqual(label, undefined);
  // Le label doit mentionner explicitement le contexte infrastructure (MQTT / infrastructure)
  const lowerLabel = label.toLowerCase();
  assert.ok(
    lowerLabel.includes("mqtt") || lowerLabel.includes("infrastructure"),
    `Label pour discovery_publish_failed devrait mentionner mqtt ou infrastructure. Got: "${label}"`
  );
});

test("story-2.4: reasonLabels — local_availability_publish_failed a un label lisible", () => {
  const label = reasonLabels["local_availability_publish_failed"];
  assert.ok(label, "local_availability_publish_failed doit avoir un label non vide");
  assert.notEqual(label, undefined);
});

// ============================================================
// AC3 — reasonLabels couvre les codes config/couverture/scope (ne sont PAS des codes infra)
// ============================================================

const CONFIG_CODES = [
  "excluded_eqlogic",
  "excluded_plugin",
  "excluded_object",
  "disabled_eqlogic",
  "no_commands",
];
const COVERAGE_CODES = [
  "ambiguous_skipped",
  "no_supported_generic_type",
  "no_mapping",
  "probable_skipped",
];

for (const code of CONFIG_CODES) {
  test(
    `story-2.4: reasonLabels — code config '${code}' a un label non vide distinct de 'Code inconnu'`,
    () => {
      const label = reasonLabels[code];
      assert.ok(
        label && label.trim() !== "",
        `reasonLabels['${code}'] doit être défini et non vide. Got: ${JSON.stringify(label)}`
      );
    }
  );
}

for (const code of COVERAGE_CODES) {
  test(
    `story-2.4: reasonLabels — code couverture '${code}' a un label non vide`,
    () => {
      const label = reasonLabels[code];
      assert.ok(
        label && label.trim() !== "",
        `reasonLabels['${code}'] doit être défini et non vide. Got: ${JSON.stringify(label)}`
      );
    }
  );
}

// ============================================================
// AC1 — Séparation visuelle : les codes config n'utilisent pas label-danger
// (via getStatusLabel qui map les statuts Jeedom)
// ============================================================

test("story-2.4: scénario AC1 mixte — statut infra (failed) rouge, statut config (Non publié) non rouge", () => {
  // Simulation d'un rendu côte à côte : bandeau infra vs raison équipement
  const infraResult = getPubResultLabel("failed"); // publication impossible = MQTT down
  const equipmentReason = getStatusLabel("Non publié"); // raison config = ambiguous_skipped

  // Le signal infra (résultat publication) utilise le rouge
  assert.match(infraResult, /label-danger/);

  // La raison équipement (config/couverture) ne l'utilise PAS
  assert.doesNotMatch(equipmentReason, /label-danger/);

  // Les deux sont visuellement distincts
  assert.notEqual(
    infraResult.match(/label-[a-z]+/)?.[0],
    equipmentReason.match(/label-[a-z]+/)?.[0],
    "Les classes CSS du signal infra et de la raison équipement doivent être différentes"
  );
});

test("story-2.4: scénario AC2 — configuration seule (exclusion) → aucun rouge", () => {
  // Infrastructure saine → bandeau vert
  // Équipement exclu → pas de rouge
  const statusLabel = getStatusLabel("Exclu");
  const pubResult = getPubResultLabel("not_attempted"); // pas de tentative = config exclue

  assert.doesNotMatch(statusLabel, /label-danger/);
  assert.doesNotMatch(pubResult, /label-danger/);
});

test("story-2.4: scénario AC3 — qualification rapide : le reason_code + label permet de distinguer infra vs config", () => {
  // Pour le support consultantla console, chaque reason_code a un label parlant
  const infraLabel = reasonLabels["discovery_publish_failed"];
  const configLabel1 = reasonLabels["excluded_eqlogic"];
  const configLabel2 = reasonLabels["ambiguous_skipped"];
  const coverageLabel = reasonLabels["no_supported_generic_type"];

  // Tous sont définis
  assert.ok(infraLabel);
  assert.ok(configLabel1);
  assert.ok(configLabel2);
  assert.ok(coverageLabel);

  // Le label infra mentionne une cause technique (MQTT / infrastructure)
  assert.ok(
    infraLabel.toLowerCase().includes("mqtt") ||
      infraLabel.toLowerCase().includes("infrastructure")
  );

  // Les labels config ne mentionnent pas d'infrastructure
  assert.ok(!configLabel1.toLowerCase().includes("mqtt"));
  assert.ok(!configLabel1.toLowerCase().includes("infrastructure"));
  assert.ok(!configLabel2.toLowerCase().includes("mqtt"));
  assert.ok(!coverageLabel.toLowerCase().includes("mqtt"));
});
