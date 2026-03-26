(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
    return;
  }
  root.Jeedom2haScopeSummary = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  function isFiniteNumber(value) {
    return typeof value === 'number' && Number.isFinite(value);
  }

  function readCount(counts, key) {
    if (!counts || typeof counts !== 'object') {
      return null;
    }
    return isFiniteNumber(counts[key]) ? counts[key] : null;
  }

  function readString(value, fallback) {
    if (typeof value === 'string' && value.trim() !== '') {
      return value;
    }
    return fallback;
  }

  function readBoolean(value, fallback) {
    if (typeof value === 'boolean') {
      return value;
    }
    return fallback;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Story 3.4 — Task 5 : mapper statuts agrégés backend → badge UI (status_code canonique)
  // Pure présentation — aucune logique métier. La source de vérité reste aggregation.py.
  function getAggregatedStatusLabel(statusCode) {
    var s = (typeof statusCode === 'string') ? statusCode : '';
    if (s === 'published')           return '<span class="label label-success">Publié</span>';
    if (s === 'excluded')            return '<span class="label" style="background-color:#999;color:#fff;">Exclu</span>';
    if (s === 'ambiguous')           return '<span class="label label-warning">Ambigu</span>';
    if (s === 'not_supported')       return '<span class="label label-default" style="background-color:#666!important;">Non supporté</span>';
    if (s === 'infra_incident')      return '<span class="label label-danger">Incident infrastructure</span>';
    if (s === 'partially_published') return '<span class="label label-info">Partiellement publié</span>';
    if (s === 'empty')               return '<span class="label label-default">Vide</span>';
    return '';
  }

  // Story 3.4 — Compteurs compacts counts_by_status (lecture seule depuis backend)
  function renderCountsByStatus(counts) {
    if (!counts || typeof counts !== 'object') { return ''; }
    var order = ['published', 'partially_published', 'ambiguous', 'excluded', 'not_supported', 'infra_incident'];
    var labels = {
      'published': 'Publié', 'partially_published': 'Partiel',
      'ambiguous': 'Ambigu', 'excluded': 'Exclu',
      'not_supported': 'Non sup.', 'infra_incident': 'Infra'
    };
    var parts = [];
    for (var s = 0; s < order.length; s++) {
      var code = order[s];
      var count = counts[code];
      if (isFiniteNumber(count) && count > 0) {
        parts.push('<span style="font-size:0.8em;margin-left:4px;color:#555;">' + escapeHtml(labels[code] || code) + ':&nbsp;' + count + '</span>');
      }
    }
    return parts.join('');
  }

  function buildCounts(rawCounts) {
    return {
      total: readCount(rawCounts, 'total'),
      include: readCount(rawCounts, 'include'),
      exclude: readCount(rawCounts, 'exclude'),
      exceptions: readCount(rawCounts, 'exceptions'),
    };
  }

  function buildDecisionSourceLabel(decisionSource, isException) {
    if (decisionSource === 'piece') {
      return 'Hérite de la pièce';
    }
    if (decisionSource === 'exception_equipement' && isException === true) {
      return 'Exception locale';
    }
    return '';
  }

  // Story 3.4 — equipDiag : données diagnostic backend pour cet équipement (null si absent)
  function buildEquipmentModel(entry, equipDiag) {
    var diag = (equipDiag && typeof equipDiag === 'object') ? equipDiag : {};
    return {
      eq_id: entry.eq_id,
      name: readString(entry.name, ''),
      effective_state: readString(entry.effective_state, ''),
      decision_source_label: buildDecisionSourceLabel(
        readString(entry.decision_source, ''),
        readBoolean(entry.is_exception, false)
      ),
      has_pending_home_assistant_changes: readBoolean(entry.has_pending_home_assistant_changes, false),
      // Story 3.4 — contrat métier backend (lecture seule — source : taxonomy.py + _DIAGNOSTIC_MESSAGES)
      status_code:   readString(diag.status_code, ''),
      detail:        readString(diag.detail, ''),
      remediation:   readString(diag.remediation, ''),
      v1_limitation: readBoolean(diag.v1_limitation, false),
    };
  }

  function toDisplayCount(value) {
    if (isFiniteNumber(value)) {
      return String(value);
    }
    return '&mdash;';
  }

  function createModel(response) {
    var safeResponse = (response && typeof response === 'object') ? response : {};
    if (safeResponse.status !== 'ok' || !safeResponse.published_scope || typeof safeResponse.published_scope !== 'object') {
      return {
        has_contract: false,
        message: readString(
          safeResponse.message,
          "Aucune synthèse backend disponible. Lancez d'abord une synchronisation."
        ),
      };
    }

    var scope = safeResponse.published_scope;
    var globalSection = (scope.global && typeof scope.global === 'object') ? scope.global : {};
    var pieces = Array.isArray(scope.pieces) ? scope.pieces : [];
    var equipements = Array.isArray(scope.equipements) ? scope.equipements : [];

    // Story 3.4 — données diagnostic (soft : absent si daemon indisponible)
    var diagEquipments = (safeResponse.diagnostic_equipments && typeof safeResponse.diagnostic_equipments === 'object')
      ? safeResponse.diagnostic_equipments : {};
    var diagRooms = Array.isArray(safeResponse.diagnostic_rooms) ? safeResponse.diagnostic_rooms : [];
    var diagSummary = (safeResponse.diagnostic_summary && typeof safeResponse.diagnostic_summary === 'object')
      ? safeResponse.diagnostic_summary : null;

    // Index rooms diagnostic par object_id pour lookup O(1)
    var diagRoomByObjectId = {};
    for (var r = 0; r < diagRooms.length; r++) {
      var dr = diagRooms[r];
      if (dr && typeof dr === 'object') {
        // Normalise object_id : le scope utilise 0 pour "Aucun", le diagnostic utilise null
        var roomObjId = (dr.object_id != null) ? dr.object_id : 0;
        diagRoomByObjectId[String(roomObjId)] = (dr.summary && typeof dr.summary === 'object') ? dr.summary : null;
      }
    }

    var normalizedPieces = [];
    var piecesByObjectId = {};

    for (var i = 0; i < pieces.length; i++) {
      var piece = pieces[i];
      if (!piece || typeof piece !== 'object') {
        continue;
      }
      var normalizedPiece = {
        object_id: piece.object_id,
        object_name: readString(piece.object_name, 'Aucune pièce'),
        counts: buildCounts(piece.counts),
        has_pending_home_assistant_changes: readBoolean(piece.has_pending_home_assistant_changes, false),
        equipements: [],
        // Story 3.4 — agrégation backend par pièce (null si daemon absent)
        diagnostic_summary: diagRoomByObjectId[String(piece.object_id)] || null,
      };
      normalizedPieces.push(normalizedPiece);
      piecesByObjectId[String(piece.object_id)] = normalizedPiece;
    }

    for (var j = 0; j < equipements.length; j++) {
      var equipement = equipements[j];
      if (!equipement || typeof equipement !== 'object') {
        continue;
      }

      var pieceModel = piecesByObjectId[String(equipement.object_id)];
      if (!pieceModel) {
        continue;
      }

      // Story 3.4 — lookup données diagnostic par eq_id (clés numériques JSON → prop string en JS)
      var eqDiag = diagEquipments[equipement.eq_id] || diagEquipments[String(equipement.eq_id)] || null;
      pieceModel.equipements.push(buildEquipmentModel(equipement, eqDiag));
    }

    return {
      has_contract: true,
      global_counts: buildCounts(globalSection.counts),
      global_pending: readBoolean(globalSection.has_pending_home_assistant_changes, false),
      pieces: normalizedPieces,
      // Story 3.4 — agrégation backend globale (null si daemon absent)
      diagnostic_summary: diagSummary,
    };
  }

  function renderStat(title, value) {
    var html = '<div class="col-xs-6 col-sm-3" style="margin-bottom:8px;">';
    html += '<div class="well well-sm" style="margin-bottom:0;">';
    html += '<div style="font-size:0.85em;color:#666;">' + escapeHtml(title) + '</div>';
    html += '<div style="font-size:1.35em;font-weight:600;line-height:1.2;">' + toDisplayCount(value) + '</div>';
    html += '</div></div>';
    return html;
  }

  function renderEquipmentState(state) {
    var normalizedState = readString(state, '');
    if (normalizedState === 'include') {
      return '<span class="label label-success">' + escapeHtml(normalizedState) + '</span>';
    }
    if (normalizedState === 'exclude') {
      return '<span class="label" style="background-color:#999;color:#fff;">' + escapeHtml(normalizedState) + '</span>';
    }
    return '<span class="label label-default">' + escapeHtml(normalizedState || 'inconnu') + '</span>';
  }

  function renderPieceEquipements(piece) {
    var equipements = Array.isArray(piece.equipements) ? piece.equipements : [];
    var html = '<div><strong>{{Équipements}}</strong></div>';

    if (equipements.length === 0) {
      html += '<div class="text-muted" style="margin-top:6px;"><em>{{Aucun équipement visible dans cette pièce côté contrat backend}}</em></div>';
      return html;
    }

    html += '<ul class="list-unstyled" style="margin:8px 0 0 0;">';
    for (var i = 0; i < equipements.length; i++) {
      var equipement = equipements[i];
      html += '<li style="padding:6px 0;' + (i > 0 ? 'border-top:1px solid #eee;' : '') + '">';
      if (equipement.name !== '') {
        html += '<span style="font-weight:bold;margin-right:8px;">' + escapeHtml(equipement.name) + '</span>';
        html += '<span style="font-size:0.9em;color:#777;">(#' + escapeHtml(equipement.eq_id) + ')</span>';
      } else {
        html += '<span class="label label-info">#' + escapeHtml(equipement.eq_id) + '</span>';
      }
      html += '<span style="margin-left:8px;">' + renderEquipmentState(equipement.effective_state) + '</span>';
      if (equipement.decision_source_label !== '') {
        var isException = equipement.decision_source_label === 'Exception locale';
        var decisionLabelClass = isException ? 'label label-info' : 'label';
        var decisionLabelStyle = isException ? 'margin-left:8px;' : 'margin-left:8px;background-color:#777;color:#fff;';
        html += '<span class="' + decisionLabelClass + '" style="' + decisionLabelStyle + '">' + escapeHtml(equipement.decision_source_label) + '</span>';
      }
      if (equipement.has_pending_home_assistant_changes === true) {
        html += '<span class="label label-warning" style="margin-left:8px;">Changements à appliquer</span>';
      }
      // Story 3.4 — Task 2 : contrat métier backend (lecture seule)
      // Dimension 1 : badge statut HA (status_code canonique → getAggregatedStatusLabel)
      if (equipement.status_code !== '') {
        html += '<span style="margin-left:8px;">' + getAggregatedStatusLabel(equipement.status_code) + '</span>';
      }
      // Dimension 2 : raison principale (detail tel quel depuis backend — jamais reformulé)
      if (equipement.detail !== '') {
        html += '<div style="margin-top:4px;font-size:0.9em;color:#555;margin-left:4px;">' + escapeHtml(equipement.detail) + '</div>';
      }
      // Dimension 3 : action recommandée (remediation tel quel depuis backend, si non vide)
      if (equipement.remediation !== '') {
        html += '<div style="margin-top:2px;font-size:0.9em;color:#888;margin-left:4px;"><em>Action recommandée</em> : ' + escapeHtml(equipement.remediation) + '</div>';
      }
      // Dimension 4 : limitation Home Assistant explicite (v1_limitation=true)
      if (equipement.v1_limitation === true) {
        html += '<div style="margin-top:4px;margin-left:4px;"><span class="label label-default">Limitation Home Assistant</span></div>';
      }
      html += '</li>';
    }
    html += '</ul>';
    return html;
  }

  function render(model) {
    if (!model || model.has_contract !== true) {
      var message = readString(model && model.message, "Aucune synthèse backend disponible. Lancez d'abord une synchronisation.");
      return '<div class="alert alert-info" style="margin-bottom:0;">' + escapeHtml(message) + '</div>';
    }

    var html = '';
    html += '<div class="row">';
    html += renderStat('Total', model.global_counts.total);
    html += renderStat('Inclus', model.global_counts.include);
    html += renderStat('Exclus', model.global_counts.exclude);
    html += renderStat('Exceptions', model.global_counts.exceptions);
    html += '</div>';
    if (model.global_pending === true) {
      html += '<div style="margin-bottom:8px;"><span class="label label-warning">Changements à appliquer</span></div>';
    }

    // Story 3.4 — Task 3 : agrégation backend globale (primary_aggregated_status + counts)
    if (model.diagnostic_summary && model.diagnostic_summary.primary_aggregated_status) {
      html += '<div style="margin-bottom:8px;">';
      html += '<strong>Statut global HA</strong> ';
      html += getAggregatedStatusLabel(model.diagnostic_summary.primary_aggregated_status);
      html += renderCountsByStatus(model.diagnostic_summary.counts_by_status);
      html += '</div>';
    }

    html += '<div class="table-responsive" style="margin-top:10px;">';
    html += '<table class="table table-condensed table-bordered" id="table_scopeSummaryPieces">';
    html += '<thead><tr>';
    html += '<th>{{Pièce}}</th>';
    html += '<th style="width:90px;">{{Total}}</th>';
    html += '<th style="width:90px;">{{Inclus}}</th>';
    html += '<th style="width:90px;">{{Exclus}}</th>';
    html += '<th style="width:110px;">{{Exceptions}}</th>';
    html += '</tr></thead><tbody>';

    if (model.pieces.length === 0) {
      html += '<tr><td colspan="5" class="text-center"><em>{{Aucune pièce disponible dans le contrat backend}}</em></td></tr>';
    } else {
      for (var i = 0; i < model.pieces.length; i++) {
        var piece = model.pieces[i];
        var pieceIdAttr = escapeHtml(String(piece.object_id));
        html += '<tr class="j2ha-piece-summary" data-piece-id="' + pieceIdAttr + '" style="cursor:pointer;">';
        html += '<td>';
        html += '<span class="j2ha-toggle-icon" style="margin-right:6px;font-size:0.8em;color:#888;">&#9654;</span>';
        html += escapeHtml(piece.object_name);
        if (piece.has_pending_home_assistant_changes === true) {
          html += ' <span class="label label-warning">Changements à appliquer</span>';
        }
        // Story 3.4 — primary_aggregated_status depuis backend (priorité sur la déduction locale)
        if (piece.diagnostic_summary && piece.diagnostic_summary.primary_aggregated_status) {
          html += ' ' + getAggregatedStatusLabel(piece.diagnostic_summary.primary_aggregated_status);
          html += renderCountsByStatus(piece.diagnostic_summary.counts_by_status);
        } else if (piece.counts.total > 0 && piece.counts.exclude === piece.counts.total) {
          // Fallback scope-only : badge local quand aucune donnée diagnostic disponible
          html += ' <span class="label" style="background-color:#999;color:#fff;">Exclue</span>';
        }
        html += '</td>';
        html += '<td>' + toDisplayCount(piece.counts.total) + '</td>';
        html += '<td>' + toDisplayCount(piece.counts.include) + '</td>';
        html += '<td>' + toDisplayCount(piece.counts.exclude) + '</td>';
        html += '<td>' + toDisplayCount(piece.counts.exceptions) + '</td>';
        html += '</tr>';
        html += '<tr class="j2ha-piece-detail" data-piece-id="' + pieceIdAttr + '" style="display:none;">';
        html += '<td colspan="5">' + renderPieceEquipements(piece) + '</td>';
        html += '</tr>';
      }
    }

    html += '</tbody></table></div>';
    return html;
  }

  return {
    createModel: createModel,
    render: render,
    getAggregatedStatusLabel: getAggregatedStatusLabel,
  };
}));
