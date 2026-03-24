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

  function buildEquipmentModel(entry) {
    return {
      eq_id: entry.eq_id,
      effective_state: readString(entry.effective_state, ''),
      decision_source_label: buildDecisionSourceLabel(
        readString(entry.decision_source, ''),
        readBoolean(entry.is_exception, false)
      ),
      has_pending_home_assistant_changes: readBoolean(entry.has_pending_home_assistant_changes, false),
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

      pieceModel.equipements.push(buildEquipmentModel(equipement));
    }

    return {
      has_contract: true,
      global_counts: buildCounts(globalSection.counts),
      global_pending: readBoolean(globalSection.has_pending_home_assistant_changes, false),
      pieces: normalizedPieces,
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
      html += '<span class="label label-info">#' + escapeHtml(equipement.eq_id) + '</span>';
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
        if (piece.counts.total > 0 && piece.counts.exclude === piece.counts.total) {
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
  };
}));
