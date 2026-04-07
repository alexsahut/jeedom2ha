'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Jeedom2haScopeSummary = require('../../desktop/js/jeedom2ha_scope_summary.js');

function makeScopeResponse() {
  return {
    status: 'ok',
    published_scope: {
      global: { counts: { total: 2, include: 2, exclude: 0 } },
      pieces: [
        { object_id: 1, object_name: 'Salon', counts: { total: 2, include: 2, exclude: 0 } },
      ],
      equipements: [
        { eq_id: 10, object_id: 1, name: 'Lampe Salon', effective_state: 'include' },
        { eq_id: 11, object_id: 1, name: 'Prise Salon', effective_state: 'include' },
      ],
    },
    diagnostic_equipments: {
      10: {
        perimetre: 'inclus',
        statut: 'publie',
        ecart: false,
        cause_label: '',
        cause_action: '',
        status_code: 'published',
        reason_code: 'sure',
        detail: '',
        remediation: '',
        v1_limitation: false,
        confidence: 'sure',
        matched_commands: [],
        unmatched_commands: [],
        actions_ha: {
          publier: { label: 'Republier dans Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'aucune' },
          supprimer: { label: 'Supprimer de Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'forte' },
        },
      },
      11: {
        perimetre: 'inclus',
        statut: 'publie',
        ecart: false,
        cause_label: '',
        cause_action: '',
        status_code: 'published',
        reason_code: 'sure',
        detail: '',
        remediation: '',
        v1_limitation: false,
        confidence: 'sure',
        matched_commands: [],
        unmatched_commands: [],
        actions_ha: {
          publier: { label: 'Republier dans Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'aucune' },
          supprimer: { label: 'Supprimer de Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'forte' },
        },
      },
    },
    diagnostic_rooms: [],
    diagnostic_summary: { compteurs: { total: 2, inclus: 2, exclus: 0, ecarts: 0 } },
    in_scope_equipments: [{ eq_id: 10 }, { eq_id: 11 }],
    home_signals: {
      global: { publies: 2, statut: 'Publiee' },
      pieces: [{ object_id: 1, perimetre: 'Incluse', publies: 2, statut: 'Publiee' }],
    },
  };
}

function readHomeJs() {
  const jsPath = path.resolve(__dirname, '../../desktop/js/jeedom2ha.js');
  return fs.readFileSync(jsPath, 'utf8');
}

// --- Équipement ---

test('5.3 / frontend — bouton Supprimer équipement rendu avec btn-danger et data-ha-action', () => {
  const html = Jeedom2haScopeSummary.render(Jeedom2haScopeSummary.createModel(makeScopeResponse()));
  assert.match(html, /btn-danger/);
  assert.match(html, /data-ha-action="supprimer"/);
  assert.match(html, /data-eq-id="10"/);
});

test('5.3 / frontend — bouton Supprimer NON rendu quand disponible=false (pas de cohabitation Créer+Supprimer)', () => {
  var response = makeScopeResponse();
  // eq 11: non publié → supprimer.disponible = false
  response.diagnostic_equipments[11].actions_ha.supprimer.disponible = false;
  response.diagnostic_equipments[11].actions_ha.publier.label = 'Créer dans Home Assistant';
  const html = Jeedom2haScopeSummary.render(Jeedom2haScopeSummary.createModel(response));
  // Find eq 11 row
  const eqRows = html.match(/<tr class="[^"]*j2ha-row-equipement[^"]*"[\s\S]*?<\/tr>/g);
  assert.ok(eqRows && eqRows.length >= 2, 'Lignes équipement absentes');
  const eq11Row = eqRows.find(r => r.includes('data-eq-id="11"'));
  assert.ok(eq11Row, 'Ligne eq 11 absente');
  // Créer is present
  assert.match(eq11Row, /btn-success/);
  // Supprimer is NOT present
  assert.doesNotMatch(eq11Row, /data-ha-action="supprimer"/);
});

test('5.3 / frontend — click équipement supprimer avec confirmation forte', () => {
  const js = readHomeJs();
  const handler = js.match(/\$\('#div_scopeSummaryContent'\)\.on\('click', '\.j2ha-action-ha-btn\[data-ha-action="supprimer"\]', function\(event\) \{[\s\S]*?\n  \}\);/);

  assert.ok(handler, 'Handler équipement supprimer absent');
  assert.match(handler[0], /confirmHaSupprimerAction/);
  assert.match(handler[0], /triggerSupprimerAction\(\$button, 'equipement', \[eqId\]\)/);
  assert.match(handler[0], /Attention/);
  assert.match(handler[0], /historique/);
  assert.match(handler[0], /dashboards/);
  assert.match(handler[0], /automatisations/);
  assert.match(handler[0], /entity_id/);
});

// --- Pièce ---

test('5.3 / frontend — ligne pièce utilise conteneur j2ha-actions-ha pour flex layout', () => {
  const html = Jeedom2haScopeSummary.render(Jeedom2haScopeSummary.createModel(makeScopeResponse()));
  const pieceRow = html.match(/<tr class="[^"]*j2ha-row-piece[^"]*"[\s\S]*?<\/tr>/);
  assert.ok(pieceRow, 'Ligne pièce absente');
  assert.match(pieceRow[0], /j2ha-actions-ha/);
});

test('5.3 / frontend — ligne pièce rend un bouton Supprimer btn-danger', () => {
  const html = Jeedom2haScopeSummary.render(Jeedom2haScopeSummary.createModel(makeScopeResponse()));
  const pieceRow = html.match(/<tr class="[^"]*j2ha-row-piece[^"]*"[\s\S]*?<\/tr>/);

  assert.ok(pieceRow, 'Ligne pièce absente');
  assert.match(pieceRow[0], /btn-danger/);
  assert.match(pieceRow[0], /data-ha-action="supprimer"/);
  assert.match(pieceRow[0], /data-piece-publies="2"/);
  assert.match(pieceRow[0], />Suppr\.<\/button>/);
});

test('5.3 / frontend — ligne pièce sans publiés ne rend pas de bouton Supprimer', () => {
  var response = makeScopeResponse();
  response.home_signals.pieces[0].publies = 0;
  const html = Jeedom2haScopeSummary.render(Jeedom2haScopeSummary.createModel(response));
  const pieceRow = html.match(/<tr class="[^"]*j2ha-row-piece[^"]*"[\s\S]*?<\/tr>/);

  assert.ok(pieceRow, 'Ligne pièce absente');
  assert.doesNotMatch(pieceRow[0], /data-ha-action="supprimer"/);
});

test('5.3 / frontend — click pièce supprimer avec confirmation forte', () => {
  const js = readHomeJs();
  const handler = js.match(/\$\('#div_scopeSummaryContent'\)\.on\('click', '\.j2ha-piece-action-btn\[data-ha-action="supprimer"\]', function\(event\) \{[\s\S]*?\n  \}\);/);

  assert.ok(handler, 'Handler pièce supprimer absent');
  assert.match(handler[0], /confirmHaSupprimerAction/);
  assert.match(handler[0], /data-piece-publies/);
  assert.match(handler[0], /triggerSupprimerAction\(\$button, 'piece', \[pieceId\]\)/);
  assert.match(handler[0], /Attention/);
  assert.match(handler[0], /entity_id/);
});

// --- Global ---

test('5.3 / frontend — click global supprimer avec confirmation forte', () => {
  const js = readHomeJs();
  const handler = js.match(/\$\('\.j2ha-ha-action\[data-ha-action="supprimer-recreer"\]'\)\.on\('click', function\(event\) \{[\s\S]*?\n  \}\);/);

  assert.ok(handler, 'Handler global supprimer absent');
  assert.match(handler[0], /confirmHaSupprimerAction/);
  assert.match(handler[0], /data-scope-publies/);
  assert.match(handler[0], /triggerSupprimerAction\(\$button, 'global', \['all'\]\)/);
  assert.match(handler[0], /Attention/);
  assert.match(handler[0], /historique/);
  assert.match(handler[0], /entity_id/);
});

// --- triggerSupprimerAction ---

test('5.3 / frontend — triggerSupprimerAction existe et appelle executeHaAction avec supprimer', () => {
  const js = readHomeJs();

  assert.match(js, /function triggerSupprimerAction\(\$button, portee, selection\)/);
  assert.match(js, /executeHaAction\('supprimer', portee, selection/);
  assert.match(js, /Suppression\.\.\./);
});

// --- confirmHaSupprimerAction ---

test('5.3 / frontend — confirmHaSupprimerAction existe avec btn-danger', () => {
  const js = readHomeJs();

  assert.match(js, /function confirmHaSupprimerAction\(title, message, confirmLabel, onConfirm\)/);
  assert.match(js, /className: 'btn-danger'/);
});

// --- Refresh après succès ---

test('5.3 / frontend — triggerSupprimerAction déclenche refresh sur succes et succes_partiel', () => {
  const js = readHomeJs();
  const fn = js.match(/function triggerSupprimerAction[\s\S]*?\n\}/);

  assert.ok(fn, 'triggerSupprimerAction absent');
  assert.match(fn[0], /shouldRefreshPublishedScopeAfterHaAction\(payload\)/);
  assert.match(fn[0], /refreshPublishedScopeSummary\(preserveNavState\)/);
});

// --- Global scope publies ---

test('5.3 / frontend — renderPublishedScopeSummary affecte data-scope-publies au bouton global', () => {
  const js = readHomeJs();

  assert.match(js, /data-scope-publies/);
  assert.match(js, /\.attr\('data-scope-publies'/);
});
