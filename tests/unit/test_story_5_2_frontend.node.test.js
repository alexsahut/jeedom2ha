'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Jeedom2haScopeSummary = require('../../desktop/js/jeedom2ha_scope_summary.js');

function makeScopeResponse(pieceIncludedCount) {
  return {
    status: 'ok',
    published_scope: {
      global: { counts: { total: 2, include: 2, exclude: 0 } },
      pieces: [
        { object_id: 1, object_name: 'Salon', counts: { total: 2, include: pieceIncludedCount, exclude: 0 } },
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
        statut: 'non_publie',
        ecart: true,
        cause_label: 'Non publié',
        cause_action: 'Republier',
        status_code: 'not_published',
        reason_code: 'sure',
        detail: '',
        remediation: '',
        v1_limitation: false,
        confidence: 'sure',
        matched_commands: [],
        unmatched_commands: [],
        actions_ha: {
          publier: { label: 'Créer dans Home Assistant', disponible: true, raison_indisponibilite: null, niveau_confirmation: 'aucune' },
          supprimer: { label: 'Supprimer de Home Assistant', disponible: false, raison_indisponibilite: 'Aucune entité publiée', niveau_confirmation: 'forte' },
        },
      },
    },
    diagnostic_rooms: [],
    diagnostic_summary: { compteurs: { total: 2, inclus: 2, exclus: 0, ecarts: 1 } },
    in_scope_equipments: [{ eq_id: 10 }, { eq_id: 11 }],
    home_signals: {
      global: { publies: 1, statut: 'Partiellement publiee' },
      pieces: [{ object_id: 1, perimetre: 'Incluse', publies: 1, statut: 'Partiellement publiee' }],
    },
  };
}

function readHomeJs() {
  const jsPath = path.resolve(__dirname, '../../desktop/js/jeedom2ha.js');
  return fs.readFileSync(jsPath, 'utf8');
}

test('5.2 / frontend — ligne pièce rend un bouton Republier contextualisé en colonne Actions', () => {
  const html = Jeedom2haScopeSummary.render(Jeedom2haScopeSummary.createModel(makeScopeResponse(2)));
  const pieceRow = html.match(/<tr class="[^"]*j2ha-row-piece[^"]*"[\s\S]*?<\/tr>/);

  assert.ok(pieceRow, 'Ligne pièce absente');
  assert.match(pieceRow[0], /j2ha-piece-action-btn/);
  assert.match(pieceRow[0], /data-portee="piece"/);
  assert.match(pieceRow[0], /data-piece-id="1"/);
  assert.match(pieceRow[0], /data-piece-name="Salon"/);
  assert.match(pieceRow[0], /data-piece-equipements-inclus="2"/);
  assert.match(pieceRow[0], />Republier<\/button>/);
});

test('5.2 / frontend — ligne pièce sans inclus ne rend pas de bouton local', () => {
  const html = Jeedom2haScopeSummary.render(Jeedom2haScopeSummary.createModel(makeScopeResponse(0)));
  const pieceRow = html.match(/<tr class="[^"]*j2ha-row-piece[^"]*"[\s\S]*?<\/tr>/);

  assert.ok(pieceRow, 'Ligne pièce absente');
  assert.doesNotMatch(pieceRow[0], /j2ha-piece-action-btn/);
});

test('5.2 / frontend — click équipement sans modale, appel direct sur portée equipement', () => {
  const js = readHomeJs();
  const handler = js.match(/\$\('#div_scopeSummaryContent'\)\.on\('click', '\.j2ha-action-ha-btn\[data-ha-action="publier"\]', function\(event\) \{[\s\S]*?\n  \}\);/);

  assert.ok(handler, 'Handler équipement absent');
  assert.doesNotMatch(handler[0], /confirmHaPublishAction/);
  assert.match(handler[0], /triggerPublierAction\(\$button, 'equipement', \[eqId\]\)/);
});

test('5.2 / frontend — click pièce avec confirmation légère et compteur backend', () => {
  const js = readHomeJs();
  const handler = js.match(/\$\('#div_scopeSummaryContent'\)\.on\('click', '\.j2ha-piece-action-btn\[data-ha-action="publier"\]', function\(event\) \{[\s\S]*?\n  \}\);/);

  assert.ok(handler, 'Handler pièce absent');
  assert.match(handler[0], /confirmHaPublishAction/);
  assert.match(handler[0], /data-piece-equipements-inclus/);
  assert.match(handler[0], /pieceName \+ ' — ' \+ includedCount/);
  assert.match(handler[0], /triggerPublierAction\(\$button, 'piece', \[pieceId\]\)/);
});

test('5.2 / frontend — click global avec confirmation explicite et portée global', () => {
  const js = readHomeJs();
  const handler = js.match(/\$\('\.j2ha-ha-action\[data-ha-action="republier"\]'\)\.on\('click', function\(event\) \{[\s\S]*?\n  \}\);/);

  assert.ok(handler, 'Handler global absent');
  assert.match(handler[0], /confirmHaPublishAction/);
  assert.match(handler[0], /data-scope-count/);
  assert.match(handler[0], /triggerPublierAction\(\$button, 'global', \['all'\]\)/);
});

test('5.2 / frontend — état pending : bouton disabled et spinner affiché', () => {
  const js = readHomeJs();

  assert.match(js, /function setHaActionPendingState\(\$button, pendingLabel\)/);
  assert.match(js, /\.prop\('disabled', true\)/);
  assert.match(js, /fa-spinner fa-spin/);
});

test('5.2 / frontend — feedback lit le message backend et inclut le périmètre impacté', () => {
  const js = readHomeJs();

  assert.match(js, /function buildHaActionUserMessage\(payload\)/);
  assert.match(js, /payload\.perimetre_impacte/);
  assert.match(js, /showAlert\(\{/);
});

test('5.2 / frontend — refresh déclenché pour succes et succes_partiel, pas pour echec', () => {
  const js = readHomeJs();

  assert.match(js, /payload\.resultat === 'succes' \|\| payload\.resultat === 'succes_partiel'/);
  assert.match(js, /var preserveNavState = true;/);
  assert.match(js, /refreshPublishedScopeSummary\(preserveNavState\)/);
});
